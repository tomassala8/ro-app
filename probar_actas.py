#!/usr/bin/env python3
"""Prueba de actas sobre una copia temporal de local.db, sin servidor ni tráfico de red."""
import hashlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import sys
import tempfile

AQUI = Path(__file__).resolve().parent


def probar():
    original = AQUI / "local.db"
    antes = hashlib.sha256(original.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="ro-actas-") as tmp:
        db = Path(tmp) / "copia.db"
        with sqlite3.connect(f"file:{original}?mode=ro", uri=True) as fuente, sqlite3.connect(db) as destino:
            fuente.backup(destino)
        os.environ["RO_DB"] = str(db)
        os.environ.pop("DATABASE_URL", None)
        def no_red(*_a, **_k):
            raise AssertionError("La prueba no permite tráfico de red")
        socket.socket.connect = no_red
        socket.create_connection = no_red
        sys.path.insert(0, str(AQUI))
        import servir as S
        import actas
        import sincronia as sinc
        # Datos reales de permisos; no arranca el servidor, no escanea ni reescribe fuentes.
        S.E.crudo = {n: json.loads((AQUI / "data" / f"{n}.json").read_text()) for n in S.NUCLEO}
        S.E.modulos = S.P.cargar_modulos()
        S.E.nucleo_bloqueado = False
        S.iniciar_base()
        real = S.E.persona("lucia")
        cp = S.P.contexto(real, S.E.crudo)
        cid = next(c["id"] for c in S.E.crudo["clientes"] if S.P.ver(real, {"tipo": "cliente_detalle", "cliente_id": c["id"]}, cp)["ok"]
                   and S.lleva_cliente(real, c["id"], cp))
        h = object.__new__(S.Manejador)
        h.responder = lambda codigo, datos: (codigo, datos)
        payload = {"clave": "acta_prueba_001", "cliente_id": cid, "fecha": S.hoy(), "notas": "Reunión de prueba local",
                   "acuerdos": [{"texto": f"Acuerdo local {i}", "quien": real["id"], "vence": None} for i in range(3)]}
        clave, cliente, huella, acciones = actas.validar(h, S, real, real, payload)
        tablas = ("acciones", "sinc_cambios", "sinc_pasos", "registro", "registro_huellas", "actas_lotes", "actas_claves")
        def cuentas():
            with S.conectar() as con:
                return {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in tablas}
        base = cuentas()
        for notas_vacias in ("", "   "):
            codigo, _r = h.api_post("/api/ficha/acta", real, real, {**payload, "clave": "acta_lote_vacio", "notas": notas_vacias, "acuerdos": []})
            assert codigo == 400, "Un lote sin notas ni acuerdos consiguió guardarse"
            assert cuentas() == base, "El rechazo vacío escribió acciones, colas, rastro o recibos"
        def fallo_segundo(i, _aid):
            if i == 2:  # acta=0, primer acuerdo=1, segundo=2
                raise RuntimeError("Fallo de prueba en el segundo acuerdo")
        # Incluso con canal marcado como real, este endpoint crea la copia con modo simulado.
        sinc.canal_real = lambda _canal: True
        sinc._tras_accion = no_red
        try:
            actas.guardar(S, sinc, real, clave, cliente, huella, acciones, tras_insertar=fallo_segundo)
            raise AssertionError("No se inyectó el fallo")
        except RuntimeError as e:
            assert "segundo acuerdo" in str(e)
        assert cuentas() == base, "Quedó un acta, tarea, rastro o recibo parcial"
        codigo, respuesta = h.api_post("/api/ficha/acta", real, real, payload)
        assert codigo == 200, respuesta
        assert len(respuesta["tareas"]) == 3 and respuesta["simulado"]
        hechas = cuentas()
        assert hechas["acciones"] - base["acciones"] == 4
        assert hechas["sinc_cambios"] - base["sinc_cambios"] == 3
        assert hechas["registro"] - base["registro"] == 1
        assert hechas["registro_huellas"] - base["registro_huellas"] == 1
        with S.conectar() as con:
            nuevo_rastro = con.execute("SELECT max(id) FROM registro").fetchone()[0]
        assert S.verificar_rastro(nuevo_rastro)[0], "El acta rompió la cadena del rastro"
        codigo, repetida = h.api_post("/api/ficha/acta", real, real, payload)
        assert codigo == 200 and repetida["repetida"] and repetida["id"] == respuesta["id"]
        assert repetida["tareas"] == respuesta["tareas"] and cuentas() == hechas
        # Reintento tras perder la clave del navegador: mismo contenido, mismas acciones.
        alias = {**payload, "clave": "acta_prueba_otra_clave"}
        codigo, repetida = h.api_post("/api/ficha/acta", real, real, alias)
        assert codigo == 200 and repetida["id"] == respuesta["id"]
        assert cuentas()["acciones"] == hechas["acciones"]
        for clave_usada in (payload["clave"], alias["clave"]):
            codigo, _r = h.api_post("/api/ficha/acta", real, real, {**payload, "clave": clave_usada, "notas": "Contenido cambiado"})
            assert codigo == 409
        cuenta_antes_rechazos = cuentas()["acciones"]
        codigo, _r = h.api_post("/api/ficha/acta", real, S.E.persona("tomas"), payload)
        assert codigo == 403, "Ver como consiguió guardar"
        setter = next(p for p in S.E.crudo["personas"] if "setters" in p.get("puestos", []))
        codigo, _r = h.api_post("/api/ficha/acta", setter, setter, {**payload, "clave": "setter_sin_permiso"})
        assert codigo == 403, "Una persona sin permiso consiguió guardar"
        codigo, _r = h.api_post("/api/ficha/acta", real, real, {**payload, "clave": "cliente_inexistente", "cliente_id": "no-existe"})
        assert codigo == 403
        codigo, _r = h.api_post("/api/ficha/acta", real, real, {**payload, "clave": "asignado_invalido", "acuerdos": [{"texto": "Tarea", "quien": "no-existe"}]})
        assert codigo == 400
        ajeno = next(p for p in S.E.crudo["personas"] if p["id"] != real["id"] and p.get("estado", "activo") == "activo"
                     and not S.lleva_cliente(p, cid, S.P.contexto(p, S.E.crudo)))
        codigo, _r = h.api_post("/api/ficha/acta", real, real, {**payload, "clave": "asignado_ajeno", "acuerdos": [{"texto": "Tarea", "quien": ajeno["id"]}]})
        assert codigo == 403, "El endpoint aceptó asignar una persona ajena al cliente"
        ajeno_cid = next(c["id"] for c in S.E.crudo["clientes"] if not S.P.ver(real, {"tipo": "cliente_detalle", "cliente_id": c["id"]}, cp)["ok"])
        codigo, _r = h.api_post("/api/ficha/acta", real, real, {**payload, "clave": "cliente_ajeno", "cliente_id": ajeno_cid})
        assert codigo == 403, "El endpoint aceptó un cliente real fuera de sus permisos"
        # Dos solicitudes coincidentes usan conexiones diferentes; no duplica ni siquiera en concurrencia.
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as piscina:
            simultaneas = list(piscina.map(lambda _x: h.api_post("/api/ficha/acta", real, real, payload), range(2)))
        assert all(cod == 200 and r["id"] == respuesta["id"] and r["tareas"] == respuesta["tareas"] for cod, r in simultaneas)
        assert cuentas()["acciones"] == cuenta_antes_rechazos
        with S.conectar() as con:
            modos = [r[0] for r in con.execute("SELECT modo FROM sinc_cambios WHERE accion_id IN (?,?,?)", respuesta["tareas"])]
            assert modos == ["simulado"] * 3
            tareas = [json.loads(r[0]) for r in con.execute("SELECT vista_previa FROM acciones WHERE id IN (?,?,?)", respuesta["tareas"])]
            assert all(x["acta"] == respuesta["id"] and x["asignado"] == real["id"] for x in tareas)
        assert hashlib.sha256(original.read_bytes()).hexdigest() == antes, "Cambió la base original"
    print("OK: segundo acuerdo falla sin filas parciales; reintentos persistentes sin duplicar; conflicto de clave; permisos, ver como y asignado; 3 copias simuladas aunque canal real; base original intacta; red prohibida.")


if __name__ == "__main__":
    probar()
