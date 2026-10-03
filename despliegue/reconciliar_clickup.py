#!/usr/bin/env python3
"""despliegue/reconciliar_clickup.py · el reconciliador de ClickUp (3-oct-2026, sincronía con herramientas).

Encargo de Tomás: «asegurarnos de que todos los cambios que hace el equipo dentro de la plataforma impactan en ClickUp,
pero también se guardan como copia por si no llegaran a impactar; y lo mismo con el chat». La lógica está en sincronia.py;
esto es lo que corre:

  · como PASO DE LA TUBERÍA (paso «reconciliar_clickup» de pasos.json, tras «verificar_envios»), en cada vuelta:
      1. sincroniza: cada acción de la cola que va a ClickUp tiene su cambio guardado en la base (clave única);
      2. con ClickUp ACTIVO (interruptor de Tomás + RO_CLICKUP_REAL=si + llave del usuario de servicio): reencola lo que
         cayó por la llave si ya vale, despacha los pendientes (orden por tarea, sin duplicar) y relee en ClickUp (SOLO
         LECTURA) que cada cambio enviado está; si ClickUp tiene otro valor más nuevo, «conflicto» y aviso con las dos
         versiones; si ClickUp no responde, sigue pendiente, aviso y reintento;
      3. el INFORME DIARIO «cambios sin reflejar» (más de X horas) en #avisos-altas para Agus y Mili, una vez al día
         desde las 08:30 (hora de Madrid). Copia en despliegue/estado/sincronia_ultima.json.
    Con ClickUp apagado (HOY) solo sincroniza, cuenta y publica el informe: no se llama a ClickUp.
  · PRUEBA DE EXTREMO A EXTREMO con un ClickUp SIMULADO (nunca el real), sobre una COPIA de la base en una carpeta
    temporal: confirmado, caído y reintento sin duplicar, corte a medias sin duplicar, agotado, conflicto (antes y después
    de escribir) y elección, llave caducada y reencolado, orden por tarea, «no aparece», simulación, guarda de escritura
    con ClickUp apagado, informe diario y puente de chat (ida, vuelta, editado y borrado).  --prueba-e2e  (la usa
    pruebas_noche.py --solo-solidez)

Uso:
  python3 despliegue/reconciliar_clickup.py                 vuelta normal (sobre RO_DB o local.db)
  python3 despliegue/reconciliar_clickup.py --sin-red       solo sincroniza, cuenta y el informe (la vuelta «cruda»)
  python3 despliegue/reconciliar_clickup.py --informe       publica el informe de hoy aunque no sea la hora
  python3 despliegue/reconciliar_clickup.py --prueba-e2e [--json]
Código de salida: 0 si ha podido hacer la vuelta (un cambio fallido NO tumba la tubería: avisa); 1 si falla la prueba e2e.
"""
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
sys.path.insert(0, str(APP))
import sincronia as SI  # noqa: E402

ARGS = sys.argv[1:]
ESTADO = Path(os.environ.get("RO_ESTADO_DIR") or AQUI / "estado")


def vuelta_normal():
    sin_red = "--sin-red" in ARGS
    it = SI.interruptor()
    with SI.conectar() as con:
        SI.preparar(con)
        if sin_red or not it["reales"]:
            nuevos = SI.sincronizar(con)
            hechos = {"nuevos": len(nuevos), "reencolados": [], "despachados": [], "verificados": [], "chat_importados": 0}
        else:
            hechos = SI.vuelta(con)
        inf = SI.publicar_informe(con, forzar="--informe" in ARGS)
        resumen = SI.sin_reflejar(con, horas=0)
        con.commit()
    por = {}
    for c in resumen["cambios"]:
        por[c["estado"]] = por.get(c["estado"], 0) + 1
    out = {"modo": it["texto"], "reales": it["reales"], "chat_puente": it["chat_puente"], "vuelta": hechos,
           "informe": {k: v for k, v in (inf.get("informe") or {}).items() if k != "cambios"} | {"publicado": inf["publicado"], "motivo": inf.get("motivo")},
           "sin_terminar": por}
    ESTADO.mkdir(parents=True, exist_ok=True)
    (ESTADO / "sincronia_ultima.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"Sincronía ClickUp · {it['texto']} · {hechos['nuevos']} nuevos · sin terminar: "
          + (" · ".join(f"{k} {v}" for k, v in por.items()) or "ninguno") + f" · informe: {'publicado' if inf['publicado'] else inf.get('motivo')}")
    for d in hechos["despachados"]:
        print(f"  cambio {d['id']}: {d['de']} → {d['a']}")
    return 0


# ============================================================================ prueba de extremo a extremo (simulada)
def prueba_e2e():
    tmp = Path(tempfile.mkdtemp(prefix="ro_sinc_e2e_"))
    os.chmod(tmp, 0o700)
    casos = []
    env_antes = {k: os.environ.get(k) for k in ("RO_SINC_PUENTE_MODO", "RO_SINC_PUENTE", "RO_CLICKUP_REAL", "RO_SINC_INTERRUPTOR")}

    def caso(nombre, ok, detalle=None):
        casos.append({"caso": nombre, "ok": bool(ok), "detalle": None if ok else str(detalle)[:400]})
        if "--json" not in ARGS:
            print(f"  {'✔' if ok else '✘'} {nombre}" + ("" if ok else f" · {str(detalle)[:400]}"))

    origen = SI.ruta_db()
    db = tmp / "e2e.db"
    try:
        os.environ.pop("RO_CLICKUP_REAL", None)
        (tmp / "interruptor.json").write_text(json.dumps({"clickup_real": False, "chat_puente": "apagado"}))
        os.environ["RO_SINC_INTERRUPTOR"] = str(tmp / "interruptor.json")
        SI.INTERRUPTOR = tmp / "interruptor.json"
        if origen.exists():
            with sqlite3.connect(str(origen)) as src, sqlite3.connect(str(db)) as dst:
                src.backup(dst)
        con = SI.conectar(db)
        SI.preparar(con)
        if not con.execute("SELECT 1 FROM sqlite_master WHERE name='canal_mensajes'").fetchone():
            con.executescript("CREATE TABLE canal_mensajes (id INTEGER PRIMARY KEY AUTOINCREMENT, canal_id TEXT NOT NULL, tipo TEXT NOT NULL, quien TEXT, "
                              "texto TEXT NOT NULL, hilo_de INTEGER, menciones TEXT, clave TEXT UNIQUE, alerta_id TEXT, cliente_id TEXT, dueno_id TEXT, "
                              "vence TEXT, ver TEXT, datos TEXT, creado TEXT NOT NULL DEFAULT (datetime('now')));")
        n = [0]
        pid = os.getpid()

        def nuevo(campo="estado", valor="revisión project manager", ref=None, base="en curso", modo="prueba", quien="lucia", texto=None):
            n[0] += 1
            ref = ref or f"t{n[0]}"
            cambio = {"campo": campo}
            if campo == "estado":
                cambio["valor"] = valor
            if texto:
                cambio["texto" if campo != "estado" else "comentario"] = texto
            cid, _ = SI.crear_cambio(con, clave=f"e2e-{n[0]}-{pid}", quien=quien, canal="clickup", tipo="mover_estado", cliente_id="gac", modulo="produccion",
                                     objeto={"tipo": "tarea", "ref": ref, "nombre": f"Tarea {ref}", "resuelto": True}, cambio=cambio,
                                     base={"estado": base} if base else None, modo=modo)
            return cid, ref

        def pasos(cid):
            return [(p["estado"], p["evento"]) for p in SI.pasos_de(con, cid)]

        def est(cid):
            return SI.estado_actual(con, cid)["estado"]

        def avisos(cid):
            return [dict(r) for r in con.execute("SELECT canal_id, menciones, texto FROM canal_mensajes WHERE clave LIKE ?", (f"sinc:{cid}:%",))]

        def aplicados(prov, clave_pref=None):
            return [x for x in prov.llamadas if x[0] == "aplicar" and (clave_pref is None or x[1] == clave_pref)]

        def tareas(*refs, estado="en curso"):
            return {r: {"estado": estado, "actualizado": SI.ahora_utc() - timedelta(hours=1)} for r in refs}

        ahora = SI.ahora_utc()

        # 1 · confirmado
        c1, r1 = nuevo()
        prov = SI.ClickUpSimulado(tareas(r1))
        e = SI.ejecutar(con, c1, prov)
        ps = SI.pasos_de(con, c1)
        caso("E2E 1 · pendiente → enviado → confirmado, con la hora de cada paso",
             e == "confirmado" and [p["estado"] for p in ps] == ["pendiente", "enviado", "confirmado"] and all(p["hora"] for p in ps), pasos(c1))
        caso("E2E 1 · una sola escritura en ClickUp y el estado de la tarea es el de la app",
             len(aplicados(prov)) == 1 and prov.tareas[r1]["estado"] == "revisión project manager" and not avisos(c1), (prov.llamadas, avisos(c1)))
        clave1 = SI.fila(con, c1)["clave"]
        caso("E2E 1 · idempotencia: crear otra vez el mismo cambio (misma clave) devuelve el mismo id",
             SI.crear_cambio(con, clave=clave1, quien="lucia", canal="clickup", tipo="mover_estado", objeto={"tipo": "tarea", "ref": r1}, cambio={"campo": "estado", "valor": "x"})[0] == c1)

        # 2 · caído → pendiente con aviso → reintento a su hora → confirmado, sin duplicar
        c2, r2 = nuevo(campo="comentario", base=None, texto="Falta el logo en alta.")
        prov = SI.ClickUpSimulado(tareas(r2))
        prov.caida = True
        e = SI.ejecutar(con, c2, prov, ahora=ahora)
        a2 = avisos(c2)
        caso("E2E 2 · ClickUp caído → sigue «pendiente» con reintento programado y aviso a Agus",
             e == "pendiente" and ("pendiente", "reintento_programado") in pasos(c2) and a2 and "agustina" in json.loads(a2[0]["menciones"]), (pasos(c2), a2))
        caso("E2E 2 · el aviso va en llano y sin el texto del comentario", a2 and all("logo" not in a["texto"] for a in a2), a2)
        prov.caida = False
        SI.despachar(con, prov, ahora=ahora)
        caso("E2E 2 · el despachador respeta la espera (no reintenta antes de su hora)", est(c2) == "pendiente" and not aplicados(prov), prov.llamadas)
        SI.despachar(con, prov, ahora=ahora + timedelta(minutes=2))
        comentarios = prov.tareas[r2].get("comentarios") or []
        caso("E2E 2 · a su hora, ClickUp responde → «confirmado» con UN solo comentario (sin duplicar)",
             est(c2) == "confirmado" and len(comentarios) == 1 and len(aplicados(prov)) == 1, (pasos(c2), comentarios))
        n_av = len(avisos(c2))
        SI.avisar(con, c2, "caida", solo_agus=True)
        caso("E2E 2 · el aviso de caída no se repite (uno por cambio)", len(avisos(c2)) == n_av, avisos(c2))

        # 3 · corte a medias: el comentario entró pero la respuesta se perdió → al reintentar lo encuentra (marca) y no lo repite
        c3, r3 = nuevo(campo="comentario", base=None, texto="¿Lo pides tú?")
        prov = SI.ClickUpSimulado(tareas(r3), {SI.fila(con, c3)["clave"]: {"aplicar": ["red_pero_aplicado"]}})
        SI.ejecutar(con, c3, prov, ahora=ahora)
        SI.despachar(con, prov, ahora=ahora + timedelta(minutes=2))
        caso("E2E 3 · corte DESPUÉS de escribir: al reintentar lo encuentra («ya_estaba») y NO lo escribe otra vez",
             est(c3) == "confirmado" and ("enviado", "ya_estaba") in pasos(c3) and len(prov.tareas[r3].get("comentarios") or []) == 1
             and len(aplicados(prov)) == 1, (pasos(c3), prov.llamadas))

        # 4 · agotado: caído en todos los intentos → «fallido», seguro de reintentar, sin escribir nada
        c4, r4 = nuevo()
        prov = SI.ClickUpSimulado(tareas(r4))
        prov.caida = True
        t = ahora
        for _ in range(SI.conf()["reintentos_max"] + 1):
            SI.despachar(con, prov, ahora=t)
            t += timedelta(hours=5)
        ult = SI.estado_actual(con, c4)
        caso("E2E 4 · ClickUp caído en todos los intentos → «fallido · agotado» (seguro de reintentar) con aviso",
             ult["estado"] == "fallido" and ult["evento"] == "agotado" and SI.detalle_de(ult).get("seguro_reintentar") and avisos(c4)
             and prov.tareas[r4]["estado"] == "en curso", pasos(c4))

        # 5 · conflicto ANTES de escribir: alguien cambió la tarea en ClickUp después de la acción → no se pisa
        c5, r5 = nuevo(base="en curso")
        prov = SI.ClickUpSimulado(tareas(r5), {SI.fila(con, c5)["clave"]: {"fuera": "bloqueado", "fuera_cuando": "antes"}})
        e = SI.ejecutar(con, c5, prov)
        a5 = avisos(c5)
        caso("E2E 5 · ClickUp tiene otro valor más nuevo → «conflicto» SIN escribir en ClickUp",
             e == "conflicto" and not aplicados(prov) and prov.tareas[r5]["estado"] == "bloqueado", (pasos(c5), prov.llamadas))
        caso("E2E 5 · aviso a la persona (Lucía) y a Agus con las dos versiones",
             a5 and {"lucia", "agustina"} <= set(json.loads(a5[0]["menciones"])) and "revisión project manager" in a5[0]["texto"] and "bloqueado" in a5[0]["texto"], a5)
        r = SI.elegir(con, c5, "lucia", "clickup")
        caso("E2E 5 · elegir «lo de ClickUp» → «descartado» y ClickUp intacto", r["ok"] and est(c5) == "descartado" and prov.tareas[r5]["estado"] == "bloqueado", pasos(c5))
        caso("E2E 5 · un cambio que no está en conflicto no se puede «elegir»", SI.elegir(con, c1, "lucia", "app")["codigo"] == 409)

        # 6 · conflicto DESPUÉS de escribir (entre la escritura y la comprobación) → elegir «lo de la app» → vuelve y gana
        c6, r6 = nuevo(base="en curso")
        prov = SI.ClickUpSimulado(tareas(r6), {SI.fila(con, c6)["clave"]: {"fuera": "bloqueado", "fuera_cuando": "despues"}})
        e = SI.ejecutar(con, c6, prov)
        caso("E2E 6 · alguien lo cambia en ClickUp justo después → al comprobar, «conflicto»", e == "conflicto", pasos(c6))
        r = SI.elegir(con, c6, "agustina", "app")
        SI.despachar(con, prov)
        caso("E2E 6 · elegir «lo de la app» → vuelve a la cola, se escribe y queda «confirmado» (sin volver a saltar el conflicto)",
             r["ok"] and est(c6) == "confirmado" and prov.tareas[r6]["estado"] == "revisión project manager", pasos(c6))

        # 7 · llave caducada → «fallido» sin reintentos en bucle, la vuelta se para; vuelve a valer → reencolado → confirmado
        c7, r7 = nuevo()
        c7b, r7b = nuevo()
        prov = SI.ClickUpSimulado(tareas(r7, r7b))
        prov.llave_mala = True
        SI.despachar(con, prov)
        u7 = SI.estado_actual(con, c7)
        caso("E2E 7 · llave caducada → «fallido · llave» al primer intento, sin reintento programado, aviso solo a Agus",
             u7["estado"] == "fallido" and u7["evento"] == "llave" and ("pendiente", "reintento_programado") not in pasos(c7)
             and avisos(c7) and "lucia" not in json.loads(avisos(c7)[0]["menciones"]), (pasos(c7), avisos(c7)))
        caso("E2E 7 · con la llave caída la vuelta se para: el siguiente cambio ni se intenta", est(c7b) == "pendiente"
             and not [x for x in prov.llamadas if x[1] == SI.fila(con, c7b)["clave"]], prov.llamadas)
        prov.llave_mala = False
        re = SI.reencolar_tras_llave(con, prov)
        SI.despachar(con, prov)
        caso("E2E 7 · la llave vuelve a valer → lo caído por llave vuelve a la cola solo y queda «confirmado»",
             c7 in re and est(c7) == "confirmado" and est(c7b) == "confirmado", (pasos(c7), pasos(c7b)))

        # 8 · orden por objeto: el segundo cambio de la MISMA tarea espera al primero
        c8a, r8 = nuevo(valor="revisión project manager")
        c8b, _ = nuevo(campo="comentario", ref=r8, base=None, texto="Listo para revisar")
        prov = SI.ClickUpSimulado(tareas(r8), {SI.fila(con, c8a)["clave"]: {"aplicar": ["caida", "ok"]}})
        SI.despachar(con, prov, ahora=ahora)
        caso("E2E 8 · el primero cae (pendiente) y el segundo de la misma tarea ESPERA sin salir",
             est(c8a) == "pendiente" and est(c8b) == "pendiente" and ("pendiente", "espera") in pasos(c8b)
             and not [x for x in prov.llamadas if x[1] == SI.fila(con, c8b)["clave"]], (pasos(c8a), pasos(c8b)))
        SI.despachar(con, prov, ahora=ahora + timedelta(minutes=2))
        orden = [x[1] for x in aplicados(prov) if x[1] in (SI.fila(con, c8a)["clave"], SI.fila(con, c8b)["clave"])]
        caso("E2E 8 · luego salen en orden (primero el estado, después el comentario) y los dos confirmados",
             est(c8a) == "confirmado" and est(c8b) == "confirmado" and orden[-2:] == [SI.fila(con, c8a)["clave"], SI.fila(con, c8b)["clave"]], (orden, prov.llamadas))

        # 9 · «dice que sí pero no está» → enviado; pasada la gracia → fallido (seguro: la marca evita duplicar)
        c9, r9 = nuevo()
        prov = SI.ClickUpSimulado(tareas(r9), {SI.fila(con, c9)["clave"]: {"perdido": True}})
        e = SI.ejecutar(con, c9, prov)
        e2 = SI.verificar(con, c9, prov, ahora=SI.ahora_utc() + timedelta(minutes=SI.conf()["gracia_min"] + 1))
        caso("E2E 9 · aceptado pero no está al releer: «enviado» y, pasada la gracia, «fallido · no aparece» con aviso",
             e == "enviado" and e2 == "fallido" and ("fallido", "no_aparece") in pasos(c9) and avisos(c9), pasos(c9))

        # 10 · simulación: «Reintentar» solo deja constancia; ClickUp no se llama
        c10, _ = nuevo(modo="simulado")
        prov = SI.ClickUpSimulado()
        r = SI.reintentar(con, c10, "agustina")
        caso("E2E 10 · en simulación nace «simulado» y «Reintentar» deja «reintento_simulado» sin llamar a ClickUp",
             pasos(c10)[0] == ("simulado", "creado") and r.get("simulado") and ("simulado", "reintento_simulado") in pasos(c10) and not prov.llamadas, (r, pasos(c10)))
        caso("E2E 10 · el despachador nunca toca un cambio simulado", not [d for d in SI.despachar(con, prov) if d["id"] == c10] and not prov.llamadas)

        # 11 · guarda: proveedor real con ClickUp apagado no escribe; y la escritura de verdad se corta antes de la llave
        class Real(SI.ClickUpSimulado):
            real = True
        c11, r11 = nuevo(modo="real")
        prov = Real(tareas(r11))
        e = SI.ejecutar(con, c11, prov)
        caso("E2E 11 · proveedor real con ClickUp apagado → «fallido · apagado» sin escribir", e == "fallido" and not aplicados(prov), (pasos(c11), prov.llamadas))
        P = SI.ProveedorClickUp()
        P.token = lambda: (_ for _ in ()).throw(AssertionError("no debía pedir la llave"))
        try:
            P.pide("PUT", "/task/x", {"status": "complete"})
            guarda = False
        except SI.ErrorSinc as x:
            guarda = x.tipo == "apagado"
        caso("E2E 11 · ClickUp real: cualquier escritura con el interruptor apagado se corta ANTES de pedir la llave (sin red)", guarda)

        # 12 · traducción en el servidor: el navegador no fija el destino ni la tarea
        d = SI._produccion()
        t_mov = next((x for x in d.get("cola") or [] if x.get("estado") in ("en curso", "diario", "planning semanal")), None)
        t_rev = next((x for x in d.get("revisiones") or [] if x.get("estado") in (SI._reglas_piezas().get("por_estado") or {})), None)
        if t_mov:
            fila_a = {"tipo": "mover_estado", "objeto": t_mov["id"], "texto": "x", "quien": "lucia", "cliente_id": t_mov.get("cli"),
                      "vista_previa": json.dumps({"a": "complete", "task_id": "OTRA", "de": "inventado"})}
            canal, obj, cam, base, ign = SI.traducir(fila_a)
            caso("E2E 12 · «mover» a un estado no permitido → el servidor pone el destino permitido; task_id y «a» del navegador se ignoran",
                 cam == {"campo": "estado", "valor": "revisión project manager"} and obj["ref"] == t_mov["id"] and {"a", "task_id"} <= set(ign)
                 and base["estado"] == t_mov["estado"], (cam, obj, ign, base))
        if t_rev:
            fila_b = {"tipo": "pieza_aprobar", "objeto": t_rev["id"], "texto": "x", "quien": "tomas", "cliente_id": t_rev.get("cliente_id"),
                      "vista_previa": json.dumps({"a": "complete"})}
            _c, _o, cam, base, _i = SI.traducir(fila_b)
            esperado = SI._reglas_piezas()["por_estado"][t_rev["estado"]]["a"]
            caso("E2E 12 · «aprobar» una pieza: el destino sale de revision_piezas, no del navegador", cam["valor"] == esperado, (cam, esperado))

        # 13 · informe diario «cambios sin reflejar»
        inf = SI.sin_reflejar(con, ahora=SI.ahora_utc() + timedelta(hours=10), horas=4)
        ids = {x["id"] for x in inf["cambios"]}
        caso("E2E 13 · el informe lleva lo no reflejado de más de X horas (conflicto, fallido, simulado) y no lo confirmado",
             {c4, c9, c10} <= ids and c1 not in ids and c5 not in ids and inf["cambios"][0]["estado"] in ("conflicto", "fallido"), [(x["id"], x["estado"]) for x in inf["cambios"]][:12])
        hora_inf = SI.ahora_utc().replace(hour=10, minute=0) + timedelta(days=2)
        p1 = SI.publicar_informe(con, ahora=hora_inf)
        p2 = SI.publicar_informe(con, ahora=hora_inf + timedelta(hours=1))
        fila_inf = con.execute("SELECT texto, menciones, canal_id FROM canal_mensajes WHERE clave=?", (f"sinc_informe:{SI.madrid(hora_inf):%Y-%m-%d}",)).fetchone()
        caso("E2E 13 · el informe sale una vez al día en #avisos-altas mencionando a Agus y Mili, en llano",
             p1["publicado"] and not p2["publicado"] and fila_inf and fila_inf[2] == "avisos-altas" and {"agustina", "mili"} <= set(json.loads(fila_inf[1]))
             and "no están en ClickUp" in fila_inf[0].replace("NO están", "no están"), (p1.get("motivo"), p2.get("motivo"), fila_inf and fila_inf[0][:200]))

        # 14 · imborrables
        inm = True
        for sql in ("UPDATE sinc_pasos SET estado='confirmado' WHERE cambio_id=%d" % c4, "DELETE FROM sinc_cambios WHERE id=%d" % c4,
                    "UPDATE sinc_cambios SET cambio='{}' WHERE id=%d" % c4):
            try:
                con.execute(sql)
                inm = False
            except sqlite3.DatabaseError:
                pass
        caso("E2E 14 · cambios y pasos imborrables (disparadores)", inm)

        # 15 · puente de chat (opción b) · apagado no hace nada; en simulación/prueba: ida, vuelta, editado y borrado
        msg = con.execute("INSERT INTO canal_mensajes (canal_id, tipo, quien, texto, creado) VALUES ('g-prueba', 'mensaje', 'lucia', 'Hola equipo', datetime('now'))").lastrowid
        fila_m = con.execute("SELECT * FROM canal_mensajes WHERE id=?", (msg,)).fetchone()
        caso("E2E 15 · puente de chat APAGADO (hoy): un mensaje de la app no entra en la cola", SI.encolar_chat(con, fila_m, "g-prueba") is None)
        (tmp / "puente.json").write_text(json.dumps({"canales": {"g-prueba": "cu-canal-1"}}))
        os.environ["RO_SINC_PUENTE"] = str(tmp / "puente.json")
        SI.PUENTE = tmp / "puente.json"
        os.environ["RO_SINC_PUENTE_MODO"] = "simulacion"
        cm = SI.encolar_chat(con, fila_m, "g-prueba")
        cm2 = SI.encolar_chat(con, fila_m, "g-prueba")
        caso("E2E 15 · puente en simulación: el mensaje queda copiado en la cola («simulado»), una sola vez",
             cm and cm == cm2 and est(cm) == "simulado" and SI.fila(con, cm)["canal"] == "chat", (cm, cm2))
        cid_p, _ = SI.crear_cambio(con, clave=f"e2e-chat-{pid}", quien="lucia", canal="chat", tipo="chat_mensaje", modo="prueba",
                                   objeto={"tipo": "canal", "ref": "cu-canal-1", "nombre": "Chat", "resuelto": True}, cambio={"campo": "mensaje", "texto": "Hola desde la app"})
        prov = SI.ClickUpSimulado()
        prov.caida = True
        SI.ejecutar(con, cid_p, prov, ahora=ahora)
        prov.caida = False
        SI.despachar(con, prov, ahora=ahora + timedelta(minutes=2))
        caso("E2E 15 · ida: con ClickUp caído el mensaje espera y luego entra UNA vez (confirmado por su marca)",
             est(cid_p) == "confirmado" and len(prov.canales.get("cu-canal-1", [])) == 1, (pasos(cid_p), prov.canales))
        prov.canales["cu-canal-1"].append({"id": "ext1", "texto": "Respuesta de Carla en ClickUp", "autor": "carla", "fecha": ahora})
        n1 = SI.importar_chat(con, prov)
        n2 = SI.importar_chat(con, prov)
        dentro = con.execute("SELECT texto FROM canal_mensajes WHERE canal_id='g-prueba' AND clave='cu:ext1'").fetchone()
        propio = con.execute("SELECT count(*) FROM canal_mensajes WHERE canal_id='g-prueba' AND texto LIKE '%Hola desde la app%' AND clave LIKE 'cu:%'").fetchone()[0]
        caso("E2E 15 · vuelta: lo escrito en ClickUp entra en el grupo de la app una vez; lo nuestro no vuelve",
             n1 == 1 and n2 == 0 and dentro and propio == 0, (n1, n2, dentro, propio))
        prov.canales["cu-canal-1"][-1].update(texto="Respuesta corregida", editado="2026-10-03T10:00")
        SI.importar_chat(con, prov)
        prov.canales["cu-canal-1"].pop()
        SI.importar_chat(con, prov)
        notas = [r[0] for r in con.execute("SELECT texto FROM canal_mensajes WHERE clave LIKE 'cu:ext1:%' ORDER BY id")]
        orig = con.execute("SELECT texto FROM canal_mensajes WHERE clave='cu:ext1'").fetchone()[0]
        caso("E2E 15 · editado en ClickUp → nota con el texto nuevo; borrado → nota; el original se conserva en la app",
             any("Editado en ClickUp" in x for x in notas) and any("Borrado en ClickUp" in x for x in notas) and "Respuesta de Carla" in orig, (notas, orig))
        con.close()
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        caso("E2E sin excepciones", False, f"{type(e).__name__}: {e}")
    finally:
        for k, v in env_antes.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        SI.INTERRUPTOR = Path(os.environ.get("RO_SINC_INTERRUPTOR") or SI.CARPETA / "interruptor.json")
        SI.PUENTE = Path(os.environ.get("RO_SINC_PUENTE") or SI.CARPETA / "puente_chat.json")
        shutil.rmtree(tmp, ignore_errors=True)
    malos = [c for c in casos if not c["ok"]]
    if "--json" in ARGS:
        print(json.dumps({"casos": casos, "fallos": len(malos)}, ensure_ascii=False))
    else:
        print(f"{'✔' if not malos else '✘'} Prueba de extremo a extremo (ClickUp simulado): {len(casos) - len(malos)} de {len(casos)} casos bien")
    return 0 if not malos else 1


def main():
    if "--prueba-e2e" in ARGS:
        return prueba_e2e()
    return vuelta_normal()


if __name__ == "__main__":
    sys.exit(main())
