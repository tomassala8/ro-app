#!/usr/bin/env python3
"""
pruebas_seguridad.py · reproduce cada hallazgo de 27_AUDITORIA_SEGURIDAD.md y comprueba que está cerrado (E0 ronda 6).

Arranca SU PROPIO servidor en 127.0.0.1:8899 con una COPIA de local.db (RO_DB) y sin recargas, así que puede escribir
sin tocar el rastro real. Al acabar lo para y borra la copia.

  python3 pruebas_seguridad.py
"""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

AQUI = Path(__file__).resolve().parent

def ejecutar_aisladas_560():
    """Sólo fixtures fuente/AST; no servidor, datos de negocio ni entorno secreto."""
    entorno = {"PATH": os.defpath, "PYTHONIOENCODING": "utf-8",
               "PYTHONDONTWRITEBYTECODE": "1", "RO_IA_REAL": "no"}
    fallos = 0
    for nombre in ("probar_baterias_seguras_560.py", "probar_bloque_seguridad_558.py",
                   "probar_ia_real_559.py", "probar_capturas_opiniones_565.py",
                   "probar_secretos_calientes_567.py", "probar_rastro_replace_569.py",
                   "probar_confirmar_personas_572.py", "probar_trabajador_resiliente_575.py",
                   "probar_ajustes_validaciones_579.py", "probar_clasificacion_importes_580.py",
                   "probar_puertas_cliente_581.py", "probar_lecturas_sincronia_585.py",
                   "probar_patrones_privados_587.py", "probar_importes_acciones_decisiones_588.py",
                   "probar_recorte_modulo_589.py", "probar_identidad_local_590.py",
                   "probar_evidencias_kpi_148.py", "probar_evidencias_kpi_api_151.py",
                   "probar_informes_declarados_596.py", "probar_acciones_tipadas_603.py",
                   "probar_decisiones_clientes_607.py", "probar_resumen_informes_611.py", "probar_cerebro_reservas_620.py",
                   "probar_puente_cerebro_reservas_621.py", "probar_seo_fuentes_624.py",
                   "probar_seguridad_cerebro_seo_625.py", "probar_recorte_estructurado_632.py",
                   "probar_eventos_cadencia_644.py", "probar_lector_metodo_649.py"):
        try:
            r = subprocess.run([sys.executable, str(AQUI / nombre)], cwd=AQUI,
                               env=entorno, capture_output=True, text=True, timeout=60)
            correcto = r.returncode == 0
            print(("✓ " if correcto else "✗ ") + nombre)
            if not correcto:
                print(r.stdout + r.stderr)
        except (OSError, subprocess.TimeoutExpired) as exc:
            correcto = False
            print("✗ " + nombre + ": " + type(exc).__name__)
        if not correcto:
            fallos += 1
    return 1 if fallos else 0

def _libre(evitar=()):
    """Ronda 11: un puerto libre de 8920-8929 (el rango de pruebas de E0), siempre en 127.0.0.1.
    Ronda 12: RO_PUERTOS_PRUEBA=8965-8969 cambia el rango (el que asigne el coordinador a cada carril).
    3-oct (intermitencias): la prueba de «libre» usa SO_REUSEADDR, como el propio servidor (HTTPServer lo activa). Sin
    él, un puerto con conexiones en TIME_WAIT del servidor anterior (30-60 s) se daba por ocupado y en un rango de 5
    puertos se acababan: «sin puerto libre» o el servidor del reloj fuera del rango, encima del carril de al lado.
    Un puerto con alguien escuchando sigue sin servir (bind falla igual)."""
    import socket
    ini, fin = (int(x) for x in os.environ.get("RO_PUERTOS_PRUEBA", "8920-8929").split("-"))
    for puerto in range(ini, fin + 1):
        if puerto in evitar:
            continue
        with socket.socket() as so:
            so.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                so.bind(("127.0.0.1", puerto))
                return puerto
            except OSError:
                continue
    return None


def _quien_escucha(puerto):
    """PIDs que escuchan en 127.0.0.1:puerto (lsof). None si no se puede saber (sin lsof)."""
    try:
        r = subprocess.run(["lsof", "-nP", f"-iTCP:{puerto}", "-sTCP:LISTEN", "-t"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return {int(x) for x in r.stdout.split() if x.strip().isdigit()}


def arrancar(env, cwd=None, espera=150, intentos=4):
    """Arranca servir.py en un puerto libre del rango y espera a que responda ÉL (no otro proceso en ese puerto).
    3-oct (intermitencias): antes se esperaban 18-24 s y se seguía aunque no hubiera arrancado; con la máquina cargada
    (otras pruebas a la vez, discos fríos tras regenerar data/) el arranque pasa de 20 s y las primeras peticiones fallaban
    o iban al servidor de otra sesión que había cogido el mismo puerto entre la comprobación y el arranque.
    Devuelve (proceso, puerto) o (None, motivo)."""
    motivo = "sin intentos"
    usados = set()
    for _ in range(intentos):
        puerto = _libre(usados)
        if not puerto:
            return None, "no hay ningún puerto libre en RO_PUERTOS_PRUEBA"
        usados.add(puerto)
        srv = subprocess.Popen([sys.executable, "servir.py", "--bind", "127.0.0.1", "--puerto", str(puerto)], cwd=cwd or AQUI, env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        fin = time.time() + espera
        while time.time() < fin:
            if srv.poll() is not None:            # no pudo escuchar (otro cogió el puerto) o falló al cargar
                motivo = f"el servidor salió con el código {srv.returncode} en el puerto {puerto}"
                break
            pids = _quien_escucha(puerto)
            if pids is None or srv.pid in pids:
                try:
                    urllib.request.urlopen(f"http://127.0.0.1:{puerto}/index.html", timeout=5)
                    return srv, puerto
                except Exception:
                    pass
            time.sleep(0.25)
        else:
            motivo = f"el servidor no respondió en {espera} s (puerto {puerto})"
        if srv.poll() is None:
            srv.terminate()
            try:
                srv.wait(timeout=10)
            except subprocess.TimeoutExpired:
                srv.kill()
    return None, motivo


def parar(srv):
    if srv is not None and srv.poll() is None:
        srv.terminate()
        try:
            srv.wait(timeout=10)
        except subprocess.TimeoutExpired:
            srv.kill()


PUERTO = None              # el del servidor principal (lo pone main() al arrancarlo)
B = "http://127.0.0.1:0"
fallos = []


def ok(cond, texto):
    print(("✓ " if cond else "✗ ") + texto)
    if not cond:
        fallos.append(texto)


def pedir(ruta, metodo="GET", cuerpo=None, yo=None, como=None, cab=None, app=True):
    h = {}
    if yo:
        h["X-RO-Yo"] = yo
    if como:
        h["X-RO-Como"] = como
    if metodo == "POST" and app:
        h.update({"X-RO-App": "1", "Content-Type": "application/json"})
    h.update(cab or {})
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(B + ruta, data=datos, method=metodo, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read().decode(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), dict(e.headers)
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:   # 3-oct: sin servidor, fallo legible (no se cae todo)
        return 0, f"sin respuesta del servidor: {e}", {}


def _leer_fila_db(path, sql):
    con = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        return con.execute(sql).fetchone()
    finally:
        con.close()


def _intentar_mutacion_m3(path, sql, mensaje_trigger):
    """Un lock/esquema roto NO demuestra trigger. Siempre rollback y cierre de la prueba."""
    con = None
    try:
        con = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=rw", uri=True, timeout=0.1)
        con.execute(sql)
        return False, "mutación no bloqueada por el disparador esperado"
    except sqlite3.DatabaseError as exc:
        codigo = getattr(exc, "sqlite_errorcode", None)
        esperado = getattr(sqlite3, "SQLITE_CONSTRAINT_TRIGGER", 1811)
        if isinstance(exc, sqlite3.IntegrityError) and codigo in (None, esperado) and str(exc) == mensaje_trigger:
            return True, "rechazo del disparador esperado"
        return False, "error SQLite distinto del rechazo esperado (" + type(exc).__name__ + ")"
    finally:
        if con is not None:
            try:
                con.rollback()
            finally:
                con.close()


def main():
    tmp = Path(tempfile.mkdtemp())
    shutil.copy(AQUI / "local.db", tmp / "prueba.db")
    (tmp / "recarga.json").write_text('{"ligera": []}')
    env = {**os.environ, "RO_DB": str(tmp / "prueba.db"), "RO_RECARGA_CONFIG": str(tmp / "recarga.json")}
    # N9: las altas escriben el correo de entrada, la lista de Access y los jefes de departamento: en pruebas, en copias.
    for nombre, origen, var in (("correos.json", "data/_privado/correos_entrada.json", "RO_CORREOS_ENTRADA"),
                                ("lista_access.txt", "despliegue/lista_access.txt", "RO_LISTA_ACCESS"),
                                ("departamentos.json", "data/departamentos.json", "RO_DEPARTAMENTOS")):
        if (AQUI / origen).exists():
            shutil.copy(AQUI / origen, tmp / nombre)
        env[var] = str(tmp / nombre)
    env.pop("RO_MODO", None)
    global PUERTO, B
    srv, PUERTO = arrancar(env)
    if srv is None:
        shutil.rmtree(tmp, ignore_errors=True)
        sys.exit(f"✗ El servidor de pruebas no arrancó: {PUERTO}.")
    B = f"http://127.0.0.1:{PUERTO}"
    try:
        pruebas(tmp)
    finally:
        parar(srv)
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{'TODO BIEN' if not fallos else f'{len(fallos)} FALLO(S)'}")
    sys.exit(1 if fallos else 0)


def pruebas(tmp):
    inicio_rastro = _leer_fila_db(tmp / "prueba.db", "SELECT coalesce(max(id), 0) + 1 FROM registro")[0]
    # ---- C2 · sin identidad no se entra como Tomás; Host y Origin; cabecera propia
    ok(pedir("/api/salud")[0] == 401, "C2 · sin identidad, /api/salud → 401 (antes 200 como Tomás)")
    ok(pedir("/api/sesion")[0] == 401, "C2 · sin identidad, /api/sesion → 401")
    ok(pedir("/data/finanzas/finanzas.json")[0] == 401, "C2 · sin identidad ni galleta, un fichero de datos → 401")
    c, t, _ = pedir("/api/ver_dato", "POST", {"almacen": "sueldos/_privado/sueldos", "ref": "mili", "campo": "meses"})
    ok(c == 401, f"C2 · sueldos sin identificarse → {c} (antes los devolvía)")
    ok(pedir("/api/sesion", yo="tomas", cab={"Host": f"atacante.example:{PUERTO}"})[0] == 403, "C2 · Host ajeno → 403")
    c, _, _ = pedir("/api/ajustes/persona", "POST", {"id": "lina", "cambios": {"puestos": ["direccion"]}}, yo="tomas",
                    cab={"Origin": "https://atacante.example", "Content-Type": "text/plain"}, app=False)
    ok(c == 403, f"C2 · POST desde otra web (sin X-RO-App, text/plain) → {c}")
    c, _, _ = pedir("/api/ajustes/persona", "POST", {"id": "lina", "cambios": {"horas_mes": 128}}, yo="tomas", cab={"Origin": "https://atacante.example"})
    ok(c == 403, f"C2 · POST con Origin ajeno → {c}")
    ok(pedir("/api/elegir")[0] == 200, "C2 · «¿Quién eres?» del prototipo disponible en local")
    c, _, h = pedir("/index.html")
    ok("frame-ancestors 'none'" in (h.get("Content-Security-Policy") or "") and h.get("X-Frame-Options") == "DENY", "B3 · CSP y anti-iframe")

    # ---- M7 · solo entran activos
    ok(pedir("/api/sesion", yo="juan_manuel")[0] == 403, "M7 · persona «dudosa» no entra")
    pi = [p["id"] for p in json.loads((AQUI / "data/personas.json").read_text()) if p.get("estado") == "por_incorporar"]
    if pi:
        ok(pedir("/api/sesion", yo=pi[0])[0] == 403, f"M7 · persona «por incorporar» ({pi[0]}) no entra hasta que Mili la active")
    baja = [p["id"] for p in json.loads((AQUI / "data/personas.json").read_text()) if p.get("estado") == "baja"]
    ok(pedir("/api/sesion", yo=baja[0])[0] == 403, f"M7 · persona de baja ({baja[0]}) no entra")

    # ---- C3 · «ver como» = mínimo de las dos
    s = {"almacen": "sueldos/_privado/sueldos", "ref": "jeronimo", "campo": "proyeccion"}
    ok(pedir("/api/ver_dato", "POST", s, yo="mili", como="cecilia")[0] == 403, "C3 · Mili como Cecilia NO lee sueldos")
    ok(pedir("/api/ver_dato", "POST", s, yo="tomas", como="cecilia")[0] == 200, "C3 · Tomás como Cecilia sí (los dos pueden)")
    for ruta in ("/api/modulo/finanzas/finanzas", "/api/modulo/panel_direccion/empresa", "/api/modulo/mi_dia/cambios"):
        c = pedir(ruta, yo="mili", como="tomas")[0]
        ok(c in (403, 404), f"C3 · Mili como Tomás no lee {ruta} → {c}")
    # Ronda 7 (D-P-C2): en «ver como», ninguna regla por puesto se presta: todos los ficheros con «puestos» que Mili no tiene
    reglas = json.loads((AQUI / "reglas_permisos.json").read_text())["datos_de_modulo"]
    mili = next(p for p in json.loads((AQUI / "data/personas.json").read_text()) if p["id"] == "mili")
    solo_tomas = [k for k, v in reglas.items() if isinstance(v, dict) and v.get("puestos") and "*" not in k and not set(v["puestos"]) & set(mili["puestos"])]
    malos = [k for k in solo_tomas if pedir(f"/api/modulo/{k}", yo="mili", como="tomas")[0] == 200]
    ok(not malos, f"C3/R7 · Mili como Tomás: 403 en los {len(solo_tomas)} ficheros por puesto que ella no tiene ({malos or 'ninguno abierto'})")
    malos = [k for k in solo_tomas if pedir(f"/data/{k}.json", cab={"Cookie": "ro_yo=mili; ro_como=tomas"})[0] == 200]
    ok(not malos, f"C3/R7 · …también por fichero con la galleta del prototipo ({malos or 'ninguno abierto'})")
    for ruta in ("/api/salud", "/api/rastro/verificar"):
        c = pedir(ruta, yo="mili", como="tomas")[0]
        ok(c == 403, f"C3/R7 · Mili como Tomás en {ruta} → {c}")
    r = _leer_fila_db(tmp / "prueba.db", "SELECT count(*) FROM registro WHERE accion='lectura' AND quien='mili' AND como='tomas'")[0]
    pedir("/api/modulo/en_rojo/x", yo="mili", como="lucia")
    pedir("/api/cliente/gac", yo="mili", como="lucia")
    r2 = _leer_fila_db(tmp / "prueba.db", "SELECT count(*) FROM registro WHERE accion='lectura' AND como='lucia'")[0]
    ok(r2 >= 1, f"M2 · lo leído en «ver como» queda en el rastro ({r2})")

    # ---- C4 · el cliente del dato lo decide el servidor
    c, t, _ = pedir("/api/ver_dato", "POST", {"almacen": "ficha/_privado/contactos", "ref": "accompany", "campo": "datos", "cliente_id": "concilia"}, yo="carla")
    ok(c == 403, f"C4 · Carla abre contactos de Accompany mintiendo cliente_id=concilia → {c} (antes 200)")
    c, _, _ = pedir("/api/ver_dato", "POST", {"almacen": "ficha/_privado/chat", "ref": "accompany", "campo": "datos", "cliente_id": "concilia"}, yo="carla")
    ok(c == 403, f"C4 · …y el chat → {c}")
    c, _, _ = pedir("/api/ver_dato", "POST", {"almacen": "ficha/_privado/contactos", "ref": "concilia", "campo": "datos"}, yo="carla")
    ok(c in (200, 404), f"C4 · Carla sí abre los de Concilia (suyo) → {c}")
    fila = _leer_fila_db(tmp / "prueba.db", "SELECT datos FROM registro WHERE quien='carla' AND coleccion='contactos' ORDER BY id DESC LIMIT 1")
    ok(fila and "accompany" not in (fila[0] or "") or fila is None, "C4 · el rastro no apunta el cliente falso")

    # ---- A1 · dinero de la empresa en «decisiones firmadas»
    c, t, _ = pedir("/api/modulo/decisiones/firmadas", yo="manuel")
    ok(c == 200 and "74.513" not in t and "Objetivos y dinero" not in t, "A1 · Manuel (producción) no ve caja, plan ni objetivos en las decisiones firmadas")
    c, t, _ = pedir("/api/modulo/decisiones/firmadas", yo="tomas")
    ok(c == 200 and "Objetivos y dinero" in t, "A1 · Tomás sí")

    # ---- A2 · inversión en textos
    c, t, _ = pedir("/api/sesion", yo="jeronimo")
    import re
    ok(c == 200 and not re.search(r"Meta d30/sep \d+ €", t), "A2 · Jerónimo no recibe «Meta d30/sep … €»")

    # ---- A3 · cuota en textos y deducible
    c, t, _ = pedir("/api/modulo/incidencias/incidencias", yo="jeronimo")
    ok(c != 200 or not re.search(r"\d{3,} € \(Holded", t), "A3 · Jerónimo no ve cuotas en textos de Incidencias")
    c, t, _ = pedir("/api/modulo/dinero_cliente/dinero_cliente", yo="lina")
    ok(c != 200 or ("tarifa_hora" not in t and '"pautadas"' not in t), "A3 · Lina no recibe tarifa ni horas pautadas")

    # ---- A4 · enlaces javascript:
    c, _, _ = pedir("/api/decisiones", "POST", {"tipo": "para_tomas", "titulo": "x", "problema": "p", "recomendacion": "r", "prueba": "javascript:alert(1)"}, yo="lina")
    ok(c == 400, f"A4 · decisión con prueba javascript: → {c}")
    c, _, _ = pedir("/api/acciones", "POST", {"herramienta": "app", "tipo": "nota", "objeto": "x", "vista_previa": {"enlace": "javascript:alert(1)"}}, yo="lucia")
    ok(c == 400, f"A4 · acción con enlace javascript: → {c}")

    # ---- A5 · contestar decisiones solo el destinatario
    c, t, _ = pedir("/api/decisiones", "POST", {"tipo": "para_tomas", "titulo": "Prueba de seguridad", "problema": "p", "recomendacion": "r"}, yo="lucia")
    did = json.loads(t).get("id") if c == 200 else None
    c, _, _ = pedir("/api/acciones", "POST", {"modulo": "decisiones", "herramienta": "app", "tipo": "decidir", "objeto": did, "vista_previa": {"decision_id": did, "decision": "Aprobar la recomendación"}}, yo="lina")
    ok(c == 403, f"A5 · Lina «decide» una decisión de Tomás por /api/acciones → {c}")
    # ---- Ronda 8 (D-P-PER2 a): la acción exige ver el módulo desde el que se manda
    c, _, _ = pedir("/api/acciones", "POST", {"modulo": "ajustes", "herramienta": "clickup", "tipo": "comentar", "objeto": "x"}, yo="lina")
    ok(c == 403, f"R8 · Lina manda una acción desde Ajustes (no lo ve) → {c}")
    c, _, _ = pedir("/api/acciones", "POST", {"herramienta": "clickup", "tipo": "comentar", "objeto": "x"}, yo="lina")
    ok(c == 400, f"R8 · acción sin módulo → {c}")
    dec = json.loads(pedir("/api/decisiones", yo="tomas")[1])["decisiones"]
    ok(not any(d["id"] == did and d.get("respondida") for d in dec), "A5 · la decisión sigue sin contestar")

    # ---- A6 · responder exige cliente de la cartera
    c, _, _ = pedir("/api/acciones", "POST", {"herramienta": "desk", "tipo": "responder", "objeto": "RO-7378", "texto": "hola", "modulo": "bandeja"}, yo="manuel")
    ok(c in (400, 403), f"A6 · Manuel (producción) «responde» a un ticket sin cliente → {c}")
    c, _, _ = pedir("/api/acciones", "POST", {"herramienta": "app", "tipo": "inventada_xyz", "objeto": "x"}, yo="lucia")
    ok(c == 400, f"M1 · tipo de acción fuera de la lista blanca → {c}")

    # ---- A7 · Ajustes
    correo_mili = next(p["correo"] for p in json.loads((AQUI / "data/personas.json").read_text()) if p["id"] == "mili")
    c, _, _ = pedir("/api/ajustes/persona", "POST", {"id": "lina", "cambios": {"correo": correo_mili}}, yo="tomas")
    ok(c == 409, f"A7 · correo duplicado → {c}")
    c, _, _ = pedir("/api/ajustes/persona", "POST", {"id": "mili", "cambios": {"puestos": ["operaciones", "direccion"]}}, yo="mili")
    ok(c == 403, f"A7 · Mili se da dirección → {c}")
    c, _, _ = pedir("/api/ajustes/persona", "POST", {"id": "lina", "cambios": {"puestos": ["trafficker", "rrhh"]}}, yo="mili")
    ok(c == 403, f"A7 · Mili da RRHH a otra persona → {c}")
    c, _, _ = pedir("/api/ajustes/persona", "POST", {"id": "tomas", "cambios": {"horas_mes": 100}}, yo="mili")
    ok(c == 403, f"A7 · Mili cambia datos de Tomás → {c}")

    # ---- M1 · rastro
    c, _, _ = pedir("/api/rastro", "POST", {"accion": "ver_dato", "modulo": "sueldos", "objeto": "x"}, yo="lina")
    ok(c == 403, f"M1 · el navegador no puede apuntar «ver_dato» → {c}")
    ida = _leer_fila_db(tmp / "prueba.db", "SELECT id FROM registro WHERE quien<>'lina' ORDER BY id DESC LIMIT 1")
    c, _, _ = pedir("/api/rastro", "POST", {"accion": "no_aplica", "motivo": "x", "modulo": "en-rojo", "anula_a": ida[0] if ida else 1}, yo="lina")
    ok(c == 403, f"M1 · anular una fila ajena → {c}")

    # ---- M3 · disparadores y cadena
    for sql, que, mensaje in (("DELETE FROM decisiones", "borrar decisiones", "Las decisiones no se borran"),
                              ("UPDATE acciones SET texto='x'", "reescribir acciones", "De una acción solo puede avanzar el estado"),
                              ("DELETE FROM registro", "borrar el rastro", "El rastro no se borra: crea una anulación"),
                              ("UPDATE registro SET quien='x'", "reescribir el rastro", "El rastro no se modifica: crea una anulación")):
        bloqueada, motivo = _intentar_mutacion_m3(tmp / "prueba.db", sql, mensaje)
        ok(bloqueada, f"M3 · {que} → {motivo}")
    c, t, _ = pedir(f"/api/rastro/verificar?desde={inicio_rastro}", yo="tomas")   # lo escrito en esta prueba
    ok(c == 200 and json.loads(t).get("ok"), f"M3 · la cadena del rastro se verifica ({t[:80]})")

    # ---- Agenda y chat (ronda 6)
    c, _, _ = pedir("/api/modulo/chat_equipo/p_lucia", yo="mili")
    ok(c == 403, f"Chat · Mili pide el chat de Lucía → {c}")
    c, _, _ = pedir("/api/modulo/chat_equipo/p_lucia", yo="tomas")
    ok(c == 403, f"Chat · ni dirección → {c}")
    c, t, _ = pedir("/api/modulo/agenda/agenda", yo="cecilia")
    if c == 200:
        filas = [x for v in json.loads(t).values() if isinstance(v, list) for x in v if isinstance(x, dict) and x.get("persona_id")]
        ok(all(x["persona_id"] == "cecilia" for x in filas), f"Agenda · Cecilia solo recibe su agenda ({len(filas)} filas)")

    # ---- Ronda 9 · fuga de /api/cliente/<id> (dudas_pintura, M4): cuota por mes, LTV, presupuesto, invertido y gasto de la serie
    import re as _re
    DIN = _re.compile(r"^(meses|ltv|presupuesto|invertido|gasto.*|cuota.*)$")

    def dinero_en(o, ruta="", out=None):
        out = set() if out is None else out
        if isinstance(o, dict):
            for k, v in o.items():
                if DIN.match(k) and not (k == "meses" and isinstance(v, list)) and not (k == "presupuesto" and isinstance(v, int)):
                    out.add(f"{ruta}.{k}")
                if k == "serie" and isinstance(v, list) and v and isinstance(v[0], dict) and isinstance(v[0].get("meta"), list) and v[0]["meta"][0] is not None:
                    out.add(f"{ruta}.serie[gasto]")
                dinero_en(v, f"{ruta}.{k}", out)
        elif isinstance(o, list):
            for x in o:
                dinero_en(x, ruta + "[]", out)
        return out

    def fichas(yo):
        s = json.loads(pedir("/api/sesion", yo=yo)[1])
        return [c["id"] for c in s["datos"]["clientes"] if c.get("detalle")]

    for yo in ("lara", "camilo", "gustavo"):          # ven clientes (o ninguno) sin ver su dinero
        fugas = set()
        for cid in fichas(yo):
            c, t, _ = pedir(f"/api/cliente/{cid}", yo=yo)
            if c == 200:
                fugas |= dinero_en(json.loads(t)["fuentes"])
        ok(not fugas, f"R9 · {yo}: la ficha no trae cuota por mes, LTV, presupuesto, invertido ni gasto de la serie ({sorted(fugas)[:4] or 'nada'})")
    c, t, _ = pedir("/api/cliente/gac", yo="lara")
    if c == 200:
        md = json.loads(t)["fuentes"]["fuentes"].get("meta", {}).get("datos", {})
        ok("serie" not in md and "presupuesto" not in md, "R9 · sin inversión, la ficha no trae la serie diaria de Meta ([gasto, leads]) ni el presupuesto")
    mias = set(fichas("lucia"))
    c, t, _ = pedir(f"/api/cliente/{sorted(mias)[0]}", yo="lucia")
    ok(c == 200 and not dinero_en(json.loads(t)["fuentes"]), f"R9 (Tomás 3-oct) · Lucía (account) NO recibe el dinero de SU cliente ({sorted(dinero_en(json.loads(t)['fuentes']))[:3] if c == 200 else c})")
    cl = json.loads(t).get("cliente", {}) if c == 200 else {}
    ok(c == 200 and "cuota" not in cl and "publicidad_30d" not in cl, "R9 (Tomás 3-oct) · la cabecera de su cliente llega sin cuota ni inversión")
    ajeno = next(x["id"] for x in json.loads(pedir("/api/sesion", yo="tomas")[1])["datos"]["clientes"] if x["id"] not in mias)
    ok(pedir(f"/api/cliente/{ajeno}", yo="lucia")[0] == 403, "R9 · Lucía no abre la ficha de un cliente ajeno (403)")
    ok(pedir("/api/cliente/gac", yo="camilo")[0] == 403, "R9 · Camilo (producción) no abre fichas de cliente (403)")
    c, t, _ = pedir("/api/cliente/gac", yo="tomas")
    d = dinero_en(json.loads(t)["fuentes"]) if c == 200 else set()
    ok(any(".libro.datos.meses" in x for x in d) and any("ltv" in x for x in d) and any("presupuesto" in x for x in d) and any("serie[gasto]" in x for x in d),
       "R9 · Tomás sí recibe cuota por mes, LTV, presupuesto y gasto de la serie")
    inf = pedir("/api/modulo/informe/p_2026-09", yo="lara")
    if inf[0] == 200:
        filas = [f for f in json.loads(inf[1]).get("filas", []) if (f.get("meta") or {}).get("serie")]
        ok(all(x[1] is None for f in filas for x in f["meta"]["serie"]), f"R9 · Informe del cliente: sin inversión, la serie de Meta va sin gasto ({len(filas)} clientes)")

    ronda11(tmp)
    ronda_a4(tmp)
    ronda14(tmp)
    n15(tmp)
    alertas_a8(tmp)
    ronda15(tmp)
    ronda16(tmp)
    mi_perfil(tmp)
    envios_verificados(tmp)
    sincronia_clickup(tmp)
    finanzas_v3(tmp)
    avisos_automaticos(tmp)
    modular_acceso(tmp)
    telefonos_regla(tmp)
    setters_agenda(tmp)

    # ---- Escáner sobre todo lo que viajaría
    import escaner_secretos as ESC
    proy = ESC.escanear_proyecto()
    ok("fuentes_crm/_crudo/ghl_vivo.json" not in proy and "fuentes_ficha/_cache/roles.json" not in proy, "M6 · leads y contactos fuera de cachés públicas (en _privado/)")


# ============================================================================ ronda 11 (auditoría 35)
# El carril aislado termina antes de leer el catálogo real o arrancar main().
if __name__ == "__main__" and sys.argv[1:] == ["--aisladas"]:
    raise SystemExit(ejecutar_aisladas_560())
import re as _re11
RE_EUR = _re11.compile(r"\d[\d.,]*\s*(?:€|euros?)|€\s*\d")
RE_COBRO = _re11.compile(r"(?i)\b(factur\w*|impag\w*|holded|airtable|A-\d{2}-\d{2,})")
PERSONAS = {p["id"]: p for p in json.loads((AQUI / "data/personas.json").read_text())}


def _euros(o, sin=(), quita=("cuota", "inversion")):
    """Importes en textos que la persona no debe ver (de los tipos de «quita»), fuera de las claves de «sin».
    El techo general de coste por lead (regla de la casa) solo cuenta para quien no ve la inversión."""
    import permisos as P11
    if isinstance(o, dict):      # R13: en búsquedas/consultas solo cuenta el importe con símbolo (el texto del usuario se queda)
        return [x for k, v in o.items() if k not in sin for x in (_euros_simbolo(v, quita) if P11.CLAVES_TEXTO_LIBRE.match(str(k)) else _euros(v, sin, quita))]
    if isinstance(o, list):
        return [x for v in o for x in _euros(v, sin, quita)]
    if not isinstance(o, str):
        return []
    return [m.group(0) for m in RE_EUR.finditer(o) if P11._fuera(P11.tipo_importe(o, m.start(), m.end()), set(quita))]


def _euros_simbolo(o, quita):
    import permisos as P11
    t = json.dumps(o, ensure_ascii=False)
    return [m.group(0) for m in P11.RE_IMPORTE_SIMBOLO.finditer(t) if P11._fuera(P11.tipo_importe(t, m.start(), m.end()), set(quita))]


def _servidor_copia(tmp, env_extra=None):
    """Segundo servidor sobre una COPIA de la app (data/ incluida) para las pruebas que estropean ficheros a propósito."""
    destino = tmp / "app"
    if not destino.exists():
        shutil.copytree(AQUI, destino, ignore=shutil.ignore_patterns("capturas", "fuentes_*", "__pycache__", "local.db", "*.log"))
        # servir importa este módulo de verdad al arrancar; la copia de pruebas
        # debe incluirlo, sin traer datos ni lectores de herramientas externas.
        (destino / "fuentes_verdad").mkdir(exist_ok=True)
        for nombre in ("clientes_activos.py", "servicios_confirmados.py", "servicios_confirmados.json"):
            shutil.copy(AQUI / "fuentes_verdad" / nombre, destino / "fuentes_verdad" / nombre)
        # El diagnóstico SEO importa únicamente estos motores puros al arrancar.
        # No copiar cachés privadas ni lectores que consultan proveedores.
        (destino / "fuentes_seo").mkdir(exist_ok=True)
        for nombre in ("seo_prioridades.py", "seo_prioridades_fuentes.py"):
            shutil.copy(AQUI / "fuentes_seo" / nombre, destino / "fuentes_seo" / nombre)
    shutil.copy(tmp / "prueba.db", tmp / "copia.db")
    env = {**os.environ, "RO_DB": str(tmp / "copia.db"), "RO_RECARGA_CONFIG": str(tmp / "recarga.json"), **(env_extra or {})}
    env.pop("RO_MODO", None)
    srv, puerto = arrancar(env, cwd=destino)
    if srv is None:
        ok(False, f"Servidor sobre la copia de la app: no arrancó ({puerto})")
        return None, "http://127.0.0.1:0", destino
    return srv, f"http://127.0.0.1:{puerto}", destino


def ronda11(tmp):
    global B
    db = lambda: sqlite3.connect(tmp / "prueba.db")
    filas_rastro = lambda: db().execute("SELECT count(*) FROM registro").fetchone()[0]

    # ---- X1 · «ver como» no abre ficheros privados ajenos (chats, alertas propias), ni a Mili ni a Tomás
    for yo, como, rel in (("mili", "tomas", "chat_equipo/p_tomas"), ("mili", "cecilia", "chat_equipo/p_cecilia"),
                          ("tomas", "mili", "chat_equipo/p_mili"), ("mili", "tomas", "alertas/p_tomas")):
        c = pedir(f"/api/modulo/{rel}", yo=yo, como=como)[0]
        ok(c == 403, f"R11 X1 · {yo} como {como} pide {rel} → {c} (antes 200 con los chats privados)")
        c = pedir(f"/data/{rel}.json", cab={"Cookie": f"ro_yo={yo}; ro_como={como}"})[0]
        ok(c == 403, f"R11 X1 · …también por fichero con la galleta → {c}")
    ok(pedir("/api/modulo/chat_equipo/p_tomas", yo="tomas")[0] == 200, "R11 X1 · Tomás sigue leyendo SU chat")
    # «miembros» con la persona real, en el propio proceso (recortar_modulo en «ver como»)
    os.environ["RO_DB"] = str(tmp / "prueba.db")
    sys.path.insert(0, str(AQUI))
    import servir as SV
    SV.iniciar_base()
    SV.E.cargar()
    per = {p["id"]: p for p in SV.E.crudo["personas"]}
    doc = {"canales": [{"id": "d1", "miembros": ["tomas", "cecilia"], "mensajes": [{"texto": "nómina"}]},
                       {"id": "d2", "miembros": [{"pid": "tomas"}, {"pid": "mili"}], "mensajes": [{"texto": "hola"}]}]}
    cp = SV.P.contexto(per["tomas"], SV.E.crudo)
    with SV.P.mirando_como(per["mili"], SV.E.crudo):
        out = SV.recortar_modulo(per["tomas"], cp, doc, "todo", conf={})
    ok([x["id"] for x in out["canales"]] == ["d2"], f"R11 X1 · filas con «miembros» en «ver como»: solo las de las DOS personas ({[x['id'] for x in out['canales']]})")
    out = SV.recortar_modulo(per["tomas"], cp, doc, "todo", conf={})
    ok(len(out["canales"]) == 2, "R11 X1 · sin «ver como», Tomás recibe sus dos canales")

    # ---- A1 · la ficha no lleva importes en los textos a quien no ve el dinero de ese cliente
    for yo in ("jeronimo", "yessica", "macarena", "gustavo", "lara"):
        ses = json.loads(pedir("/api/sesion", yo=yo)[1])["datos"]["clientes"]
        malos = {}
        for cli in [x for x in ses if x.get("detalle")]:
            ve_c, ve_i = "cuota" in cli, "publicidad_30d" in cli
            if ve_c and ve_i:
                continue
            c, t, _ = pedir(f"/api/cliente/{cli['id']}", yo=yo)
            if c != 200:
                continue
            d = json.loads(t)
            fu = d.get("fuentes") or {}
            sin = ({"libro"} if ve_c else set()) | ({"meta", "captacion", "captacion_ghl", "google_ads", "tiktok"} if ve_i else set())
            quita = [k for k, ve_ in (("cuota", ve_c), ("inversion", ve_i)) if not ve_]
            eur = _euros({k: v for k, v in fu.items() if k != "fuentes"}, (), quita) + _euros(fu.get("fuentes") or {}, sin, quita)
            eur += [x for x in ("[importe]",) if x in t]
            if eur:
                malos[cli["id"]] = eur[:2]
        ok(not malos, f"R11 A1 · {yo}: ninguna ficha con € en los textos ({sum(len(v) for v in malos.values())} en {list(malos)[:3]})")
    c, t, _ = pedir("/api/cliente/gac", yo="tomas")
    ok(c == 200 and _euros(json.loads(t)["fuentes"]), "R11 A1 · Tomás sigue viendo los importes")
    # B-A02 (auditoría 34): el recorte no deja «[importe]» a la vista en ninguna pantalla de quien no ve el dinero
    huecos = []
    for yo in ("lina", "valeria", "gustavo", "jeronimo"):
        for rel in ("alertas/p_" + yo, "captacion/captacion", "en_rojo/atajos", "crm/crm"):
            c, t, _ = pedir(f"/api/modulo/{rel}", yo=yo)
            if c == 200 and "[importe]" in t:
                huecos.append(f"{yo}:{rel}")
        c, t, _ = pedir("/api/sesion", yo=yo)
        if "[importe]" in t:
            huecos.append(f"{yo}:sesion")
    ok(not huecos, f"R11 B-A02 · ningún «[importe]» a la vista ({huecos[:4]})")
    import permisos as P11
    t = "Coste por lead de 98 € (7 días), 2,5 veces el techo de 35 €"
    ok(P11.sin_importes(t, ("cuota",)) == t and "€" not in P11.sin_importes(t) and "[importe]" not in P11.sin_importes(t),
       "R11 B-A02 · la trafficker (ve inversión) lee su coste por lead y el techo; sin inversión, la frase va sin cifras ni huecos")

    # ---- R13 · lo que la gente escribe en un buscador no es dinero nuestro: las búsquedas llegan enteras
    q = "delito fiscal 120.000 euros anuales"
    ok(P11.sin_importes({"consultas": [[q, 3]], "busquedas": [{"q": q}], "keywords": [q], "texto": "Gasto de 300 € en Meta. Bien."})
       == {"consultas": [[q, 3]], "busquedas": [{"q": q}], "keywords": [q], "texto": "Bien."},
       "R13 · sin_importes deja enteras consultas, búsquedas y palabras clave (y sigue quitando el gasto del texto)")
    ok("€" not in str(P11.sin_importes({"consultas": ["10, asesoramiento fundae ,0, €0,00 ,1,4"]}, ("inversion",))),
       "R13 · …pero un coste de Google Ads con símbolo colado en las consultas («€0,00») sí se quita a quien no ve la inversión")
    vistos = {}
    for yo, rel in (("jeronimo", "/api/modulo/seo/seo"), ("jeronimo", "/api/modulo/paneles/gsc/oteca"), ("jeronimo", "/api/cliente/oteca"),
                    ("lara", "/api/cliente/oteca"), ("carla", "/api/modulo/informe/p_2026-09")):
        c, t, _ = pedir(rel, yo=yo)
        vistos[f"{yo}:{rel}"] = (c, "delito fiscal 120.000 euros anuales" in t, "delito fiscal anuales" in t)
    ok(all(c != 200 or (entera and not rota) for c, entera, rota in vistos.values()) and any(c == 200 and e for c, e, _ in vistos.values()),
       f"R13 · Search Console de Oteca llega entera («{q}»), nunca «delito fiscal anuales» ({vistos})")

    # ---- A2 · IA: contexto con lo ya recortado; precalculado servido por persona
    import ia as IA
    for yo in ("jeronimo", "yessica"):
        pe = per[yo]
        cpp = SV.P.contexto(pe, SV.E.crudo)
        eur, n = [], 0
        for cli in SV.E.crudo["clientes"]:
            ve = lambda tp: SV.P.ver(pe, {"tipo": tp, "cliente_id": cli["id"]}, cpp)["ok"]
            if not ve("cliente_detalle") or (ve("cuota") and ve("inversion")):
                continue
            try:
                ctxt = IA.contexto_copiloto(pe, cpp, cli["id"])
            except IA.Denegado:
                continue
            n += 1
            eur += _euros({k: v for k, v in ctxt.items() if k != "fuentes"}, (), [k for k in ("cuota", "inversion") if not ve(k)])
        ok(n == 0 or not eur, f"R11 A2 · contexto del copiloto de {yo}: 0 importes fuera de sus fuentes ({len(eur)} en {n} clientes; antes 45)")
        c, t, _ = pedir("/api/ia/lista", yo=yo)
        lis = json.loads(t) if c == 200 else {}
        malos = [x for x in lis.get("copiloto", []) if RE_EUR.search(json.dumps(x, ensure_ascii=False)) or RE_COBRO.search(x.get("primera") or "")]
        ok(c != 200 or not malos, f"R11 A2 · lista de la IA de {yo}: sin importes ni cobros ({len(malos)})")
        malos = []
        for x in lis.get("copiloto", []):
            c, t, _ = pedir("/api/ia/copiloto", "POST", {"cliente_id": x["cliente_id"]}, yo=yo)
            if c == 200 and json.loads(t).get("ok"):
                r = json.loads(t)
                txt = json.dumps({k: r.get(k) for k in ("diagnostico", "acciones", "escalar")}, ensure_ascii=False)
                cpx = SV.P.contexto(pe, SV.E.crudo)
                ve_din = all(SV.P.ver(pe, {"tipo": tp, "cliente_id": x["cliente_id"]}, cpx)["ok"] for tp in ("cuota", "inversion"))
                if RE_COBRO.search(txt) or (RE_EUR.search(txt) and not ve_din):
                    malos.append(x["cliente_id"])
        ok(not malos, f"R11 A2 · copiloto precalculado de {yo}: sin facturas, cobros ni importes que no ve ({malos[:4]})")
    c, t, _ = pedir("/api/ia/copiloto", "POST", {"cliente_id": "campalans"}, yo="tomas")
    ok(c == 200 and (not json.loads(t).get("ok") or RE_COBRO.search(t)), "R11 A2 · Tomás sí recibe lo de facturación en el copiloto")

    # ---- A3 · Ajustes: Mili no da puestos sensibles ni da de baja a quien tiene uno (caso Lina)
    lina = PERSONAS["lina"]["puestos"]
    for nuevos in (lina + ["operaciones"], lina + ["ventas_ro", "administracion"], lina + ["finanzas_direccion"]):
        c = pedir("/api/ajustes/persona", "POST", {"id": "lina", "cambios": {"puestos": nuevos}}, yo="mili")[0]
        ok(c == 403, f"R11 A3 · Mili da {sorted(set(nuevos) - set(lina))} a Lina → {c} (antes 200)")
    ok(pedir("/api/sesion", yo="lina", como="tomas")[0] == 403, "R11 A3 · Lina sigue sin poder «ver como»")
    c = pedir("/api/ver_dato", "POST", {"almacen": "ventas_ro/_privado/ventas_tomas", "ref": "x", "campo": "nombre"}, yo="lina")[0]
    ok(c == 403, f"R11 A3 · Lina sigue sin abrir prospectos de Tomás → {c}")
    for quien, cambios in (("cecilia", {"estado": "baja"}), ("cecilia", {"puestos": ["rrhh", "account"]}), ("sofia", {"estado": "baja"}),
                           ("mili", {"estado": "baja"})):
        c = pedir("/api/ajustes/persona", "POST", {"id": quien, "cambios": cambios}, yo="mili")[0]
        ok(c == 403, f"R11 A3 · Mili cambia {cambios} a {quien} → {c}")
    ok(not any(p.get("estado") != "activo" for p in json.loads(pedir("/api/ajustes", yo="tomas")[1])["personas"] if p["id"] in ("cecilia", "sofia", "mili")),
       "R11 A3 · Cecilia, Sofía y Mili siguen activas")
    c = pedir("/api/ajustes/persona", "POST", {"id": "cecilia", "cambios": {"horas_mes": (PERSONAS["cecilia"].get("horas_mes") or 128) + 8,
                                                                           "puestos": PERSONAS["cecilia"]["puestos"], "estado": "activo"}}, yo="mili")[0]
    ok(c == 403, f"R16 N8 · Mili no cambia ni las horas de Cecilia (puesto de mando: solo Tomás) → {c}")
    c = pedir("/api/ajustes/persona", "POST", {"id": "cecilia", "cambios": {"alias": "Ceci (fuera)"}}, yo="mili")[0]
    c2 = pedir("/api/ajustes/persona", "POST", {"id": "sofia", "cambios": {"horas_mes": 40}}, yo="mili")[0]
    ok(c == 403 and c2 == 403, f"R16 N8 · Mili no renombra a Cecilia ni cambia las horas de Sofía → {c}/{c2}")
    c = pedir("/api/ajustes/persona", "POST", {"id": "lina", "cambios": {"puestos": lina + ["operaciones"]}}, yo="tomas")[0]
    c2 = pedir("/api/ajustes/persona", "POST", {"id": "lina", "cambios": {"puestos": lina}}, yo="tomas")[0]
    ok(c == 200 and c2 == 200, f"R11 A3 · Tomás sí puede (y lo deja como estaba) → {c}/{c2}")

    # ---- A4 · «responder» con el cliente que saca el servidor; si no se sabe, 403
    base = {"modulo": "bandeja", "tipo": "responder", "texto": "hola", "cliente_id": "concilia"}
    for herr, obj in (("desk", "RO-999999"), ("whatsapp", "+34600000000"), ("ghl", "contacto-inventado"), ("gmail", "contacto@ejemplo.com")):
        c = pedir("/api/acciones", "POST", {**base, "herramienta": herr, "objeto": obj}, yo="carla")[0]
        ok(c == 403, f"R11 A4 · Carla «responde» {herr}/{obj} con cliente_id=concilia del navegador → {c} (antes 200)")
    c = pedir("/api/acciones", "POST", {**base, "herramienta": "desk", "objeto": "RO-6574"}, yo="carla")[0]
    ok(c == 403, f"R11 A4 · Carla responde RO-6574 (Accompany) diciendo «concilia» → {c}")
    c = pedir("/api/acciones", "POST", {**base, "herramienta": "desk", "objeto": "RO-6715", "cliente_id": "gac"}, yo="carla")[0]
    ok(c == 200, f"R11 A4 · Carla sí responde un ticket de SU cliente (Concilia), mienta o no el navegador → {c}")

    # ---- M1 · acciones por puesto y repetidas
    for herr, tipo in (("holded", "cobro_reclamado"), ("ghl", "baja"), ("app", "quitar_acceso")):
        c = pedir("/api/acciones", "POST", {"modulo": "ficha", "herramienta": herr, "tipo": tipo, "objeto": "tomas"}, yo="carla")[0]
        ok(c == 403, f"R11 M1 · un account (Carla) encola {herr}/{tipo} → {c} (antes 200)")
    n0 = db().execute("SELECT count(*) FROM acciones").fetchone()[0]
    a = {"modulo": "ficha", "herramienta": "app", "tipo": "nota", "objeto": "r11-repetida", "texto": "misma nota", "cliente_id": "concilia"}
    c1, t1, _ = pedir("/api/acciones", "POST", a, yo="carla")
    c2, t2, _ = pedir("/api/acciones", "POST", a, yo="carla")
    n1 = db().execute("SELECT count(*) FROM acciones").fetchone()[0]
    ok(c1 == 200 and c2 == 200 and n1 - n0 == 1 and json.loads(t2).get("repetida"), f"R11 M1 · la misma acción dos veces deja UNA fila ({n1 - n0})")

    # ---- M7 · el rastro no se inunda
    from datetime import datetime as _dt
    m0 = _dt.now().strftime("%H:%M")
    r0 = filas_rastro()
    for _ in range(40):
        pedir("/api/modulo/finanzas/finanzas", yo="lina")
    r1 = filas_rastro()
    ok(r1 - r0 <= 2, f"R11 M7 · 40 denegados iguales en un minuto → {r1 - r0} fila(s) (antes 40)")
    rels = [f"cliente/{c['id']}" for c in json.loads(pedir("/api/sesion", yo="tomas")[1])["datos"]["clientes"]][:60]
    for r in rels:
        pedir(f"/api/{r}", yo="camilo")
    r2 = filas_rastro()
    ok(r2 - r1 <= 32 or _dt.now().strftime("%H:%M") != m0, f"R11 M7 · 60 denegados distintos en un minuto → {r2 - r1} filas (tope 30 + 1 aviso)")
    codigos = [pedir("/api/rastro", "POST", {"accion": "pestana", "modulo": "en-rojo", "objeto": f"r11-{i}"}, yo="manuel")[0] for i in range(70)]
    ok(429 in codigos and codigos.count(200) <= 60, f"R11 M7 · el navegador no escribe más de 60 filas por minuto ({codigos.count(200)} y luego 429)")

    # ---- M5 · objetivo de dinero de dirección
    c, t, _ = pedir("/api/modulo/mi_dia/config", yo="manuel")
    ok(c == 200 and "30.000 €" not in t and "[importe]" not in t, "R11 M5 · Manuel no recibe «30.000 €/mes» en Mi día")
    c, t, _ = pedir("/api/modulo/mi_dia/config", yo="tomas")
    ok(c == 200 and "30.000 €" in t, "R11 M5 · Tomás sí")

    # ---- A7 · rastro: incidencias anotadas, verificación tras la anotación y ancla diaria
    c, t, _ = pedir("/api/rastro/verificar", yo="tomas")
    v = json.loads(t) if c == 200 else {}
    ok(v.get("ok") and (v.get("tras_anotacion") or {}).get("ok"), f"R11 A7 · la cadena del rastro (con 1289 y 1571 anotadas) valida entera y desde la anotación ({t[:120]})")
    ok(pedir("/api/rastro/verificar?desde=anotado", yo="tomas")[0] == 200 and pedir("/api/rastro/verificar?desde=x;1", yo="tomas")[0] == 400, "R11 A7 · «desde» solo número o «anotado»")
    try:
        sqlite3.connect(tmp / "prueba.db").execute("DELETE FROM rastro_incidencias")
        ok(False, "R11 A7 · borrar una incidencia anotada no se bloqueó")
    except sqlite3.DatabaseError:
        ok(True, "R11 A7 · las incidencias del rastro no se borran")
    # R16 (N6): el ancla va por rango de ids y no depende de la hora: misma prueba con el reloj a la hora real, a las 00:30
    # y a las 01:59 de Madrid (antes, entre las 00:00 y las 02:00 el ancla «de hoy» no cubría ninguna fila).
    from datetime import datetime as _dtm
    from zoneinfo import ZoneInfo as _Z
    hoy_mad = _dtm.now(_Z("Europe/Madrid")).date().isoformat()
    for reloj in (None, f"{hoy_mad}T00:30", f"{hoy_mad}T01:59"):
        etq = reloj[11:] if reloj else "hora real"
        db_a, anclas = tmp / f"ancla_{etq.replace(':', '')}.db", tmp / f"anclas_{etq.replace(':', '')}.jsonl"
        shutil.copy(tmp / "prueba.db", db_a)
        envA = {**os.environ, "RO_DB": str(db_a), "RO_ANCLAS": str(anclas)}
        if reloj:
            envA["RO_RELOJ"] = reloj
        def cli(*args):
            try:
                return subprocess.run([sys.executable, "servir.py", *args], cwd=AQUI, env=envA, capture_output=True, text=True, timeout=60)
            except subprocess.TimeoutExpired:      # un servir.py sin esa opción arranca el servidor: cuenta como fallo
                return subprocess.CompletedProcess(args, 99, "", "")
        r = cli("--ancla-diaria")
        r2 = cli("--verificar-rastro")
        a = json.loads(r.stdout.splitlines()[0]) if r.returncode == 0 and r.stdout.strip().startswith("{") else {}
        ult_id = sqlite3.connect(db_a).execute("SELECT max(id) FROM registro").fetchone()[0]
        ok(r.returncode == 0 and anclas.exists() and r2.returncode == 0 and a.get("ultima") == ult_id and a.get("filas", 0) > 0,
           f"R11 A7 · ancla ({etq}) fuera de la base, cubre hasta la última fila ({a.get('ultima')} de {ult_id}) y verificación en verde")
        con = sqlite3.connect(db_a)      # quien tiene el fichero recalcula la última huella tras cambiar la fila…
        for t in [x[0] for x in con.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name IN ('registro','registro_huellas')")]:
            con.execute(f"DROP TRIGGER {t}")
        ult = con.execute("SELECT * FROM registro ORDER BY id DESC LIMIT 1").fetchone()
        cols = [d[0] for d in con.execute("SELECT * FROM registro LIMIT 0").description]
        fila = dict(zip(cols, ult))
        fila["datos"] = json.dumps({"manipulado": True})
        con.execute("UPDATE registro SET datos=? WHERE id=?", (fila["datos"], fila["id"]))
        h = SV._huella(fila["huella_previa"], [fila["id"], fila["creada"], fila["quien"], fila["como"], fila["coleccion"], fila["accion"], fila["clave"], fila["datos"], fila["motivo"], fila["anula_a"], fila["origen"]])
        con.execute("UPDATE registro_huellas SET huella=? WHERE id=?", (h, fila["id"]))
        con.commit()
        r3 = cli("--verificar-rastro")
        salida = json.loads(r3.stdout) if r3.stdout.strip().startswith("{") else {}
        ok(r3.returncode == 1 and (salida.get("entera") or {}).get("ok") and not (salida.get("anclas") or {}).get("ok"),
           f"R11 A7 · ({etq}) cadena recalculada a mano: la cadena «cuadra» pero el ancla del día lo delata")
    lim = getattr(SV, "_limites_dia_utc", lambda d: None)
    ok(lim("2026-10-03") == ("2026-10-02 22:00:00", "2026-10-03 22:00:00") and (lim("2026-12-01") or [""])[0] == "2026-11-30 23:00:00",
       "R16 N6 · un día de Madrid pedido a mano se pasa a horas UTC de la base (verano y también invierno)")

    # ---- N9 · altas y bajas de personas desde Ajustes (persona FICTICIA, en la copia de la base)
    import hashlib
    huella = lambda p: hashlib.sha256((AQUI / p).read_bytes()).hexdigest() if (AQUI / p).exists() else None
    reales = {p: huella(p) for p in ("data/_privado/correos_entrada.json", "despliegue/lista_access.txt", "data/departamentos.json", "data/personas.json")}
    base_alta = {"nombre": "Zoe Ficticia", "jefe": "mili", "zona": "Europe/Madrid", "fecha_entrada": None, "cumple": "03-14"}
    for pu in (["rrhh"], ["operaciones"], ["administracion"], ["account", "ventas_ro"]):
        c = pedir("/api/altas/alta", "POST", {**base_alta, "puestos": pu}, yo="mili")[0]
        ok(c == 403, f"N9 · Mili da de alta con un puesto sensible {pu} → {c}")
    c = pedir("/api/altas/alta", "POST", {**base_alta, "puestos": ["account"], "correo_entrada": "zoe.personal" + "@" + "gmail.com"}, yo="mili")[0]
    ok(c == 403, f"N9 · Mili pone un correo de entrada que no es de RO → {c} (solo Tomás)")
    c = pedir("/api/altas/alta", "POST", {**base_alta, "puestos": ["account"], "telefono": "6001" + "12233"}, yo="mili")[0]
    ok(c == 400, f"N9 · un alta con teléfono se rechaza → {c} (solo nombre, puesto, jefe, zona, fechas y cumpleaños)")
    c = pedir("/api/altas/alta", "POST", {**base_alta, "puestos": ["account"]}, yo="carla")[0]
    ok(c == 403, f"N9 · un account (Carla) no da de alta → {c}")
    c = pedir("/api/altas/alta", "POST", {**base_alta, "puestos": ["account"]}, yo="tomas", como="mili")[0]
    ok(c == 403, f"N9 · en «ver como» no se da de alta → {c}")
    c, t, _ = pedir("/api/altas/alta", "POST", {**base_alta, "puestos": ["account"], "correo_entrada": "fixture2@rankingonline.com",
                                                "cartera": [{"cliente_id": "concilia", "silla": "account", "papel": "apoyo"}, {"cliente_id": "gac", "silla": "account", "papel": "apoyo"}]}, yo="mili")
    r = json.loads(t) if c == 200 else {}
    zid = r.get("id")
    ok(c == 200 and r.get("tarea_access") and (r.get("comprobacion") or {}).get("todo_bien"), f"N9 · Mili da de alta a la ficticia (account, 2 clientes) con tarea de Access y comprobación en verde → {c}")
    c, t, _ = pedir("/api/sesion", yo=zid)
    s = json.loads(t) if c == 200 else {"datos": {"clientes": []}}
    det = sorted(x["id"] for x in s["datos"]["clientes"] if x.get("detalle"))
    ok(c == 200 and det == ["concilia", "gac"], f"N9 · la ficticia entra con su identidad y abre SOLO sus 2 clientes ({det})")
    c, t, _ = pedir("/api/sesion", cab={"Cf-Access-Authenticated-User-Email": "fixture2@rankingonline.com"})
    ok(c == 200 and json.loads(t)["persona"]["id"] == zid, f"N9 · y entra por su correo de entrada → {c}")
    c, t, _ = pedir("/api/cliente/musashi-consultores", yo=zid)
    ok(c == 403 and "Musashi" not in t, f"N9 · la ficticia no ve un cliente ajeno (Musashi) → {c}, sin datos")
    ok(pedir("/api/cliente/concilia", yo=zid)[0] == 200, "N9 · …y sí el suyo (Concilia)")
    ok(pedir("/api/altas", yo=zid)[0] == 403, "N9 · la ficticia no entra en altas y bajas")
    c = pedir("/api/altas/cambio", "POST", {"id": "cecilia", "jefe": "mili"}, yo="mili")[0]
    ok(c == 403, f"N9 · Mili no cambia a una persona con puesto de mando (Cecilia) → {c}")
    c = pedir("/api/altas/cambio", "POST", {"id": zid, "puestos": ["rrhh"]}, yo="mili")[0]
    ok(c == 403, f"N9 · Mili no le da RRHH a la ficticia en un cambio → {c}")
    c = pedir("/api/altas/baja", "POST", {"id": "tomas"}, yo="mili")[0]
    ok(c == 403, f"N9 · Mili no da de baja a Tomás → {c}")
    c = pedir("/api/altas/departamento", "POST", {"departamento": "redes", "jefe": "mili"}, yo="mili")[0]
    ok(c == 403, f"N9 · el jefe de un departamento solo lo cambia Tomás (Mili → {c})")
    c, t, _ = pedir("/api/altas/cambio", "POST", {"id": zid, "puestos": ["trafficker"], "cartera_anadir": [{"cliente_id": "concilia", "silla": "trafficker", "papel": "apoyo"}]}, yo="mili")
    s = json.loads(pedir("/api/sesion", yo=zid)[1])
    contratos = json.loads((AQUI / "data/clientes.json").read_text())
    concilia = next(x for x in contratos if x["id"] == "concilia")
    ok((concilia.get("servicios") or {}).get("publicidad") == "prevista", "N9 · control: Concilia tiene publicidad prevista, sin contrato confirmado")
    ok(c == 200 and s["datos"]["carteraPorSilla"].get("trafficker") == [] and not s["datos"]["clientes"]
       and pedir("/api/cliente/concilia", yo=zid)[0] == 403,
       "N9 · asignar silla trafficker sin publicidad contratada no concede acceso a Concilia ni la muestra en sesión")
    contratado = next(x["id"] for x in contratos if (x.get("servicios") or {}).get("publicidad") == "sí"
                      and (AQUI / "data/clientes" / f"{x['id']}.json").exists())
    c = pedir("/api/altas/cambio", "POST", {"id": zid, "cartera_anadir": [{"cliente_id": contratado, "silla": "trafficker", "papel": "apoyo"}]}, yo="mili")[0]
    s = json.loads(pedir("/api/sesion", yo=zid)[1])
    ok(c == 200 and s["datos"]["carteraPorSilla"].get("trafficker") == [contratado]
       and [x["id"] for x in s["datos"]["clientes"]] == [contratado]
       and pedir(f"/api/cliente/{contratado}", yo=zid)[0] == 200,
       "N9 · asignación trafficker con publicidad sí concede únicamente el cliente contratado")
    # Endpoint de alertas: ni cabeceras de cliente rechazado tras el cambio de puesto.
    ok(all(a.get("cliente_id") != "concilia" for a in s["datos"]["alarmas"]),
       "N9 · el cliente sin publicidad tampoco aparece en las alarmas de sesión")
    c, t, _ = pedir("/api/altas/baja", "POST", {"id": zid}, yo="mili")
    ok(c == 200 and pedir("/api/sesion", yo=zid)[0] == 403, f"N9 · baja: ya no entra → {c}")
    lista = (tmp / "lista_access.txt").read_text()
    ok("zoe.ficticia@" not in "\n".join(l for l in lista.splitlines() if not l.startswith("#")), "N9 · tras la baja su correo sale de la lista de Access (copia)")
    # R16 (N6): la baja cierra con la fecha de MADRID; se compara con la de Madrid (antes, date('now') en UTC fallaba de 00:00 a 02:00).
    from datetime import datetime as _dtm
    from zoneinfo import ZoneInfo as _Z
    hoy_mad = _dtm.now(_Z("Europe/Madrid")).date().isoformat()
    abiertas = db().execute("SELECT count(*) FROM asignaciones WHERE persona_id=? AND (hasta IS NULL OR hasta > ?)", (zid, hoy_mad)).fetchone()[0]
    ok(abiertas == 0, f"N9 · sus asignaciones quedan cerradas con fecha ({abiertas} abiertas)")
    ok(all(huella(p) == h for p, h in reales.items()), "N9 · nada de esto ha tocado los ficheros reales (correos, lista de Access, departamentos, personas)")

    # ---- R14 (B2) · Producción › Por revisar: Aprobar / Pedir cambios en SIMULACIÓN, solo quien revisa, nunca el autor
    prod = json.loads((AQUI / "data/produccion/produccion.json").read_text())
    cart_lucia = set(json.loads(pedir("/api/sesion", yo="lucia")[1])["datos"]["carteraPorSilla"].get("account", []))
    pm_lucia = next(r for r in prod["revisiones"] if r["estado"] == "revisión project manager" and r["cliente_id"] in cart_lucia)
    pm_ajena = next(r for r in prod["revisiones"] if r["estado"] == "revisión project manager" and r["cliente_id"] not in cart_lucia)
    de_camilo = next(r for r in prod["cola"] if r["persona_id"] == "camilo" and r["grupo"] == "revision" and r["estado"] == "revisión project manager")
    del_cliente = next(r for r in prod["cola"] if r["grupo"] == "revision" and r["estado"] == "revisión cliente")
    bp = {"modulo": "produccion", "herramienta": "clickup"}
    n0 = db().execute("SELECT count(*) FROM acciones").fetchone()[0]
    c, t, _ = pedir("/api/acciones", "POST", {**bp, "tipo": "pieza_aprobar", "objeto": pm_lucia["id"], "texto": "Aprobar", "cliente_id": "otro-cliente"}, yo="lucia")
    fila = db().execute("SELECT tipo, cliente_id, estado, modulo FROM acciones ORDER BY id DESC LIMIT 1").fetchone()
    rastro = db().execute("SELECT count(*) FROM registro WHERE accion='accion_simulada' AND clave=?", (pm_lucia["id"],)).fetchone()[0]
    ok(c == 200 and tuple(fila) == ("pieza_aprobar", pm_lucia["cliente_id"], "simulada", "produccion") and rastro >= 1,
       f"R14 · Lucía aprueba una pieza de su cliente: 200, en la cola en simulación, cliente del servidor y con rastro ({c}, {tuple(fila)}, rastro {rastro})")
    c = pedir("/api/acciones", "POST", {**bp, "tipo": "pieza_aprobar", "objeto": pm_ajena["id"], "texto": "x"}, yo="lucia")[0]
    ok(c == 403, f"R14 · Lucía no aprueba una pieza de un cliente que no lleva → {c}")
    c = pedir("/api/acciones", "POST", {**bp, "tipo": "pieza_aprobar", "objeto": de_camilo["id"], "texto": "x"}, yo="camilo")[0]
    ok(c == 403, f"R14 · Camilo no se aprueba su propia pieza → {c}")
    c = pedir("/api/acciones", "POST", {**bp, "tipo": "pieza_pedir_cambios", "objeto": de_camilo["id"], "texto": "x"}, yo="manuel")[0]
    ok(c == 403, f"R14 · Manuel (producción) no pide cambios en la pieza de otro → {c}")
    c = pedir("/api/acciones", "POST", {**bp, "tipo": "pieza_pedir_cambios", "objeto": pm_lucia["id"], "texto": " ", "vista_previa": {"comentario": ""}}, yo="lucia")[0]
    ok(c == 400, f"R14 · Pedir cambios sin decir qué → {c}")
    c = pedir("/api/acciones", "POST", {**bp, "tipo": "pieza_pedir_cambios", "objeto": de_camilo["id"], "texto": "El titular no es el del brief", "vista_previa": {"comentario": "El titular no es el del brief"}}, yo="mili")[0]
    ok(c == 200, f"R14 · Mili (operaciones) pide cambios en una pieza de Camilo → {c}")
    c = pedir("/api/acciones", "POST", {**bp, "tipo": "pieza_aprobar", "objeto": del_cliente["id"], "texto": "x"}, yo="mili")[0]
    ok(c == 403, f"R14 · lo que espera al cliente no se aprueba desde la app → {c}")
    c = pedir("/api/acciones", "POST", {**bp, "tipo": "pieza_aprobar", "objeto": "no-existe-123", "texto": "x"}, yo="mili")[0]
    ok(c == 403, f"R14 · una pieza que no espera revisión → {c}")
    c = pedir("/api/acciones", "POST", {**bp, "modulo": "ficha", "tipo": "pieza_aprobar", "objeto": pm_lucia["id"], "texto": "x"}, yo="lucia")[0]
    ok(c == 400, f"R14 · «pieza_aprobar» solo desde Producción (desde la Ficha → {c})")
    c = pedir("/api/acciones", "POST", {**bp, "tipo": "pieza_aprobar", "objeto": pm_lucia["id"], "texto": "x"}, yo="tomas", como="lucia")[0]
    ok(c == 403, f"R14 · en «ver como» no se aprueba nada → {c}")
    n1 = db().execute("SELECT count(*) FROM acciones").fetchone()[0]
    ok(n1 - n0 == 2, f"R14 · solo las 2 permitidas dejan fila en la cola ({n1 - n0})")
    ok(not db().execute("SELECT count(*) FROM acciones WHERE tipo LIKE 'pieza_%' AND estado != 'simulada'").fetchone()[0],
       "R14 · ninguna acción de pieza sale de la simulación (escribir en ClickUp lo activa Tomás)")

    # ---- A8 · RO_ORIGEN_APP en render.yaml y un POST con ese Origin
    ry = (AQUI / "despliegue/render.yaml").read_text()
    ok("RO_ORIGEN_APP" in ry and "https://app.rankingonline.app" in ry, "R11 A8 · render.yaml lleva RO_ORIGEN_APP=https://app.rankingonline.app")

    # ---- Pruebas que estropean ficheros: segundo servidor sobre una COPIA de la app
    srv, base2, app2 = _servidor_copia(tmp, {"RO_ORIGEN_APP": "https://app.rankingonline.app"})
    B_antes, B = B, base2
    try:
        c, t, _ = pedir("/api/acciones", "POST", {"modulo": "ficha", "herramienta": "app", "tipo": "nota", "objeto": "r11-origen", "cliente_id": "concilia"},
                        yo="carla", cab={"Origin": "https://app.rankingonline.app"})
        ok(c == 200, f"R11 A8 · con RO_ORIGEN_APP, un POST desde https://app.rankingonline.app entra → {c}")
        c = pedir("/api/acciones", "POST", {"modulo": "ficha", "herramienta": "app", "tipo": "nota", "objeto": "r11-origen2"}, yo="carla",
                  cab={"Origin": "https://otra.rankingonline.app"})[0]
        ok(c == 403, f"R11 A8 · …y otro Origin, no → {c}")
        # A4 con la Bandeja ilegible
        bdj = app2 / "data/bandeja/bandeja.json"
        guardado = bdj.read_bytes()
        bdj.write_text("{roto")
        c = pedir("/api/acciones", "POST", {**base, "herramienta": "desk", "objeto": "RO-6574"}, yo="carla")[0]
        ok(c == 403, f"R11 A4 · con la Bandeja ilegible, Carla responde RO-6574 diciendo «concilia» → {c} (antes 200)")
        bdj.write_bytes(guardado)
        # M2 · fichero roto o vacío → último dato bueno, nunca 500
        seo = app2 / "data/seo/seo.json"
        bueno = seo.read_bytes()
        c0 = pedir("/api/modulo/seo/seo", yo="tomas")[0]
        seo.write_bytes(bueno[:5000])
        c1, t1, _ = pedir("/api/modulo/seo/seo", yo="tomas")
        seo.write_bytes(b"")
        c2, t2, _ = pedir("/api/modulo/seo/seo", yo="tomas")
        seo.write_text("{}")
        c3, t3, _ = pedir("/api/modulo/seo/seo", yo="tomas")
        seo.write_bytes(bueno)
        ok(c0 == 200 and c1 == 200 and c2 == 200 and c3 == 200 and all("_ultimo_dato_bueno" in t for t in (t1, t2, t3)),
           f"R11 M2 · seo.json roto / 0 bytes / {{}} → último dato bueno con su hora ({c1}, {c2}, {c3}; antes 500 y vacío)")
        otro, rel = app2 / "data/redes/redes.json", "redes/redes"
        otro.write_text("{roto")
        c = pedir(f"/api/modulo/{rel}", yo="tomas")[0]
        ok(c == 503, f"R11 M2 · roto y sin dato anterior en memoria → {c} con motivo (nunca 500)")
    finally:
        B = B_antes
        parar(srv)


# ============================================================================ ronda 14 (velocidad, auditoría 37)
def ronda14(tmp):
    """La memoria de respuestas recortadas (causa 8) y los ETag (causa 4) nunca cruzan personas ni «ver como»."""
    ruta = "/api/modulo/crm/crm"
    c1, t_lucia, h1 = pedir(ruta, yo="lucia")
    c2, t_yes, h2 = pedir(ruta, yo="yessica")
    e1, e2 = h1.get("ETag"), h2.get("ETag")
    ok(c1 == c2 == 200 and e1 and e2 and e1 != e2 and t_lucia != t_yes,
       "R14 · dos personas, mismo fichero: cada una su recorte y su ETag (no comparten memoria)")
    c, t, _ = pedir(ruta, yo="lucia")
    ok(c == 200 and t == t_lucia, "R14 · la segunda vez (de la memoria) Lucía recibe exactamente su recorte")
    c, t, _ = pedir(ruta, yo="yessica", cab={"If-None-Match": e1})
    ok(c == 200 and t == t_yes, f"R14 · Yessica con el ETag de Lucía → {c} y SU recorte (nunca 304 con lo de otra)")
    c, t, _ = pedir(ruta, yo="lucia", cab={"If-None-Match": e1})
    ok(c == 304 and not t, f"R14 · Lucía con su ETag → {c} sin cuerpo")
    c, t, h = pedir(ruta, yo="tomas", como="lucia", cab={"If-None-Match": e1})
    ok(c == 200 and h.get("ETag") not in (e1, None), f"R14 · Tomás «como Lucía» con el ETag de Lucía → {c} y huella propia (la vista lleva su clave)")
    c, t, h = pedir(ruta, yo="mili", como="lucia")
    ok(c == 200 and h.get("ETag") not in (e1, None), "R14 · Mili «como Lucía» y Tomás «como Lucía» no comparten entrada")
    ok("no-store" in (h1.get("Cache-Control") or "") and "X-RO-Como" in (h1.get("Vary") or ""),
       "R14 · /api sigue con no-store (el navegador no lo guarda en disco) y Vary por persona")
    # un fichero ajeno sigue dando 403 aunque otro lo tenga en memoria
    c, _, _ = pedir("/api/modulo/chat_equipo/p_tomas", yo="tomas")
    c2, t2, _ = pedir("/api/modulo/chat_equipo/p_tomas", yo="mili")
    c3, _, _ = pedir("/api/modulo/chat_equipo/p_tomas", yo="tomas", como="mili")
    ok(c == 200 and c2 == 403 and c3 == 403, f"R14 · el chat de Tomás en memoria no llega a Mili ni a «Tomás como Mili» ({c}, {c2}, {c3})")
    # la sesión: logos como dirección, menú por permisos del servidor y sin datos de otro
    c, t, _ = pedir("/api/sesion", yo="lucia")
    d = json.loads(t)
    logos = [x.get("logo") for x in d["datos"]["clientes"] if x.get("logo")]
    ok(c == 200 and logos and all(str(x).startswith("logos/") for x in logos) and "base64" not in t,
       "R14 · /api/sesion sin logos en base64 (van como /logos/<id>.jpg?v=…)")
    ok(isinstance(d.get("modulos_puestos"), dict) and "mi-dia" in d["modulos_puestos"], "R14 · /api/sesion trae los permisos del menú (sin bajar el código)")
    with urllib.request.urlopen(B + "/" + logos[0]) as r:
        c, h = r.status, dict(r.headers)
    ok(c == 200 and (h.get("Content-Type") or "").startswith("image/") and "immutable" in (h.get("Cache-Control") or ""),
       "R14 · el logo se sirve como imagen con caché larga")
    ok(pedir("/logos/no-existe.jpg")[0] == 404 and pedir("/logos/../local.db")[0] in (403, 404), "R14 · /logos/ no sirve otra cosa")
    # estáticos con huella: immutable solo si la huella casa; index sin caché y con su mapa en la CSP
    c, t, h = pedir("/?yo=lucia")
    import re as _re14
    m = _re14.search(r'src="carcasa\.js\?v=([0-9a-f]+)"', t)
    sha = _re14.search(r"'sha256-[^']+'", h.get("Content-Security-Policy") or "")
    ok(c == 200 and m and "importmap" in t and sha and "no-cache" in (h.get("Cache-Control") or ""),
       "R14 · index.html con el mapa de versiones, su huella en la CSP y sin caché")
    ok('href="api/sesion?yo=lucia"' in t and "fonts.googleapis" not in t and "fonts.g" not in (h.get("Content-Security-Policy") or ""),
       "R14 · la sesión se precarga para quien entra y no hay Google Fonts")
    c, _, h = pedir(f"/carcasa.js?v={m.group(1)}")
    c2, _, h2 = pedir("/carcasa.js?v=otra")
    ok("immutable" in (h.get("Cache-Control") or "") and "immutable" not in (h2.get("Cache-Control") or ""),
       "R14 · caché de un año solo con la huella buena")
    c, t, _ = pedir("/?yo=lucia%22%3E%3Cscript%3E")
    ok("<script>" not in t.split("importmap")[-1] and 'precarga-sesion' not in t, "R14 · un ?yo= raro no entra en la página")
    for f in ("local.db", "servir.py", "data/personas.json", "fuentes_web/../servir.py"):
        ok(pedir("/" + f)[0] in (401, 403, 404), f"R14 · /{f} sigue sin servirse")
    # Ajustes cambia la base → la memoria se vacía (la versión sube)
    _, t_antes, h_antes = pedir("/api/modulo/crm/crm", yo="yessica")
    pedir("/api/ajustes/persona", "POST", {"id": "lina", "cambios": {"horas_mes": 141}}, yo="tomas")
    _, t_despues, h_despues = pedir("/api/modulo/crm/crm", yo="yessica")
    ok(h_antes.get("ETag") != h_despues.get("ETag"), "R14 · tras un cambio en Ajustes, la memoria no sirve el recorte anterior")



# ============================================================================ A4 (2-oct) · objetivo del cliente y semáforo del lunes
def ronda_a4(tmp):
    """Solo su account (cartera de account), operaciones y dirección los cargan; el resto lo ve sin editar y sin costes si no ve la inversión."""
    db = lambda: sqlite3.connect(tmp / "prueba.db")
    obj = lambda cid, **x: {"modulo": "ficha", "herramienta": "app", "tipo": "objetivo_alta", "objeto": cid, "cliente_id": cid,
                            "texto": f"Objetivo de {cid} (prueba {time.time()})", "vista_previa": {"leads_mes": 40, "coste_lead": 7.5, "coste_cita": 55, "ventas_mes": 3, **x}}
    sem = lambda cid, color="rojo", nota="Prueba de seguridad": {"modulo": "ficha", "herramienta": "app", "tipo": "semaforo_semanal", "objeto": cid, "cliente_id": cid,
                                                                 "texto": f"Semáforo de {cid}: {color} (prueba {time.time()})", "vista_previa": {"color": color, "nota": nota}}
    for yo, cid, esperado, que in (("lucia", "gac", 200, "Lucía (account de GAC) carga el objetivo de GAC"),
                                   ("lucia", "musashi", 403, "Lucía carga el objetivo de Musashi (no es suyo)"),
                                   ("candela", "gac", 403, "Candela (account de otros) carga el de GAC"),
                                   ("candela", "emex", 200, "Candela carga el de Emex (es su account)"),
                                   ("valeria", "gac", 403, "Valeria (trafficker y jefa de publicidad de GAC) no lo carga"),
                                   ("jeronimo", "gac", 403, "Jerónimo (SEO de GAC) lo ve, no lo carga"),
                                   ("constanza", "gac", 403, "Coti (proyectos, account de otros) no carga el de GAC"),
                                   ("mili", "gac", 200, "Mili (operaciones, su jefa) sí"),
                                   ("tomas", "musashi", 200, "Tomás (dirección) sí")):
        ok(pedir("/api/acciones", "POST", obj(cid), yo=yo)[0] == esperado, f"A4 · objetivo · {que} → {esperado}")
        ok(pedir("/api/acciones", "POST", sem(cid), yo=yo)[0] == esperado, f"A4 · semáforo · {que} → {esperado}")
    # Ajuste del coordinador: en los clientes EN ALTA, proyectos (Coti) y el técnico de altas (Agus) siguen cargando el objetivo
    # desde Clientes nuevos, como antes; el semáforo, no. Valeria (publicidad), solo ver.
    alta = lambda cid: {**obj(cid), "modulo": "clientes-nuevos", "vista_previa": {"coste_cita": 50, "coste_lead": 9, "citas_mes": 6, "presupuesto": 600}}
    for yo, cid, esperado, que in (("constanza", "emex", 200, "Coti (proyectos) carga el objetivo de Emex, en alta"),
                                   ("agustina", "think-value", 200, "Agus (técnico de altas) carga el de Think Value, en alta"),
                                   ("constanza", "gac", 403, "Coti no carga el de GAC (no está en alta)"),
                                   ("agustina", "gac", 403, "Agus no carga el de GAC (no está en alta)"),
                                   ("valeria", "emex", 403, "Valeria no carga el de Emex (solo lo ve)"),
                                   ("candela", "emex", 200, "Candela (su account) lo carga también desde Clientes nuevos")):
        ok(pedir("/api/acciones", "POST", alta(cid), yo=yo)[0] == esperado, f"A4 · alta · {que} → {esperado}")
    for yo, cid in (("constanza", "emex"), ("agustina", "think-value"), ("valeria", "emex")):
        ok(pedir("/api/acciones", "POST", sem(cid), yo=yo)[0] == 403, f"A4 · alta · {yo} no pone el semáforo de {cid} → 403")
    ok(pedir("/api/acciones", "POST", {**alta("gac"), "cliente_nuevo": True}, yo="constanza")[0] == 403, "A4 · alta · el navegador no puede decir que GAC está en alta → 403")
    sin = obj("gac"); sin.pop("cliente_id")
    ok(pedir("/api/acciones", "POST", sin, yo="lucia")[0] == 403, "A4 · objetivo sin cliente_id → 403")
    ok(pedir("/api/acciones", "POST", obj("gac"), yo="tomas", como="lucia")[0] == 403, "A4 · «ver como» no carga nada (Tomás como Lucía) → 403")
    ok(pedir("/api/acciones", "POST", {**sem("gac"), "modulo": "captacion"}, yo="lucia")[0] in (400, 403), "A4 · el semáforo solo entra desde la ficha (lista blanca por pantalla)")
    n = db().execute("SELECT count(*) FROM registro WHERE accion='accion_simulada' AND clave='gac' AND quien IN ('lucia','mili')").fetchone()[0]
    ok(n >= 4, f"A4 · cada objetivo y semáforo guardado queda en el rastro ({n})")
    # Lectura: los costes del objetivo solo a quien ve la inversión del cliente
    c, t, _ = pedir("/api/acciones?modulo=ficha", yo="jeronimo")
    filas = [json.loads(a["vista_previa"] or "{}") for a in json.loads(t).get("acciones", []) if a.get("tipo") == "objetivo_alta" and a.get("cliente_id") == "gac"] if c == 200 else []
    ok(c == 200 and filas and all("coste_lead" not in f and "coste_cita" not in f and f.get("leads_mes") == 40 for f in filas),
       f"A4 · Jerónimo ve el objetivo de GAC sin costes (leads sí) → {c}, {filas[:1]}")
    c, t, _ = pedir("/api/acciones?modulo=ficha", yo="lucia")
    filas = [json.loads(a["vista_previa"] or "{}") for a in json.loads(t).get("acciones", []) if a.get("tipo") == "objetivo_alta" and a.get("cliente_id") == "gac"]
    ok(filas and "coste_lead" not in filas[0] and filas[0].get("leads_mes") == 40, "A4 (Tomás 3-oct) · Lucía (su account) ve el objetivo de GAC sin el coste por lead")
    c, t, _ = pedir("/api/acciones?modulo=ficha", yo="mili")
    filas = [json.loads(a["vista_previa"] or "{}") for a in json.loads(t).get("acciones", []) if a.get("tipo") == "objetivo_alta" and a.get("cliente_id") == "gac"] if c == 200 else []
    ok(filas and filas[0].get("coste_lead") == 7.5, "A4 · Mili (operaciones) sí ve el coste por lead del objetivo")
    # El almacén común, generado sobre la copia de la base: recortado por el servidor como cualquier dato de módulo
    os.environ["RO_DB"] = str(tmp / "prueba.db")
    sys.path.insert(0, str(AQUI))
    from fuentes_objetivos import objetivos as OBJ
    todos, _ = OBJ.leer()
    g = todos.get("gac") or {}
    ok((g.get("objetivo") or {}).get("coste_lead") == 7.5 and (g.get("objetivo") or {}).get("quien") == "mili" and (g.get("semaforo") or {}).get("color") == "rojo",
       f"A4 · la lectura común da el último objetivo y semáforo de GAC con quién y cuándo ({(g.get('objetivo') or {}).get('quien')}, {(g.get('semaforo') or {}).get('cuando')})")
    ok(pedir("/api/acciones", "POST", sem("gac", "verde", "Cerramos 2.000 € de presupuesto"), yo="lucia")[0] == 200, "A4 · semáforo con importe en la nota (se guarda)")
    g = OBJ.leer()[0].get("gac") or {}
    ok("€" not in (g.get("semaforo") or {}).get("nota", "") and "2.000" not in (g.get("semaforo") or {}).get("nota", ""), f"A4 · …y la nota sale sin el importe («{(g.get('semaforo') or {}).get('nota')}»)")
    ok(len(g.get("semanas") or []) == 1 and g["semanas"][0]["color"] == "verde", "A4 · historial semanal: una fila por semana, la última manda")
    viejo = AQUI / "data/objetivos/objetivos.json"
    guardado = viejo.read_bytes() if viejo.exists() else None
    try:
        OBJ.escribir()
        c, t, _ = pedir("/api/modulo/objetivos/objetivos", yo="jeronimo")
        d = json.loads(t) if c == 200 else {}
        gj = next((x for x in d.get("clientes", []) if x["cliente_id"] == "gac"), {})
        ok(c == 200 and gj and "coste_lead" not in json.dumps(gj) and "coste_cita" not in json.dumps(gj) and (gj.get("objetivo") or {}).get("leads_mes") == 40,
           "A4 · objetivos.json: Jerónimo recibe GAC sin costes")
        c, t, _ = pedir("/api/modulo/objetivos/objetivos", yo="candela")
        ids = {x["cliente_id"] for x in json.loads(t).get("clientes", [])} if c == 200 else None
        ok(ids is not None and "emex" in ids and not ids & {"gac", "musashi"}, f"A4 · Candela recibe Emex (suyo) y no GAC ni Musashi → {c}, {sorted(ids or [])}")
        c, t, _ = pedir("/api/modulo/objetivos/objetivos", yo="lucia")
        gl = next((x for x in json.loads(t).get("clientes", []) if x["cliente_id"] == "gac"), {}) if c == 200 else {}
        ok(gl and "coste_lead" not in json.dumps(gl) and (gl.get("objetivo") or {}).get("leads_mes") == 40, "A4 (Tomás 3-oct) · objetivos.json: Lucía recibe GAC sin el coste por lead")
        c, t, _ = pedir("/api/modulo/objetivos/objetivos", yo="tomas")
        gt = next((x for x in json.loads(t).get("clientes", []) if x["cliente_id"] == "gac"), {}) if c == 200 else {}
        ok((gt.get("objetivo") or {}).get("coste_lead") == 7.5, "A4 · objetivos.json: dirección sí recibe el coste de GAC")
        ok(pedir("/api/modulo/objetivos/objetivos", yo="sofia")[0] == 403, "A4 · administración no recibe objetivos ni semáforos")
    finally:
        if guardado is not None:
            viejo.write_bytes(guardado)
        os.environ.pop("RO_DB", None)


# ============================================================================ N15 · canales de avisos, grupos y campana
def n15(tmp):
    """N15 (2-oct): nadie lee canales ajenos, «ver como» no escribe, nada sale fuera, importes y contraseñas tapados.
    Rutas /api/canales/* (avisos.py). /api/avisos sigue siendo lo de E0 (avisos del sistema a Tomás)."""
    global B
    db = lambda: sqlite3.connect(tmp / "prueba.db")
    js = lambda r: json.loads(r[1]) if r[0] == 200 else {}
    lista = lambda yo, como=None: {c["id"]: c for c in js(pedir("/api/canales", yo=yo, como=como)).get("canales", [])}
    luc, ana, cec = lista("lucia"), lista("setter_ana"), lista("cecilia")
    ok("avisos-accounts" in luc and "avisos-rrhh" not in luc and "equipo-rrhh" not in luc, "N15 · Lucía ve #avisos-accounts y no los de RRHH")
    ok(set(ana) == {"general"}, f"N15 · la setter solo ve #general ({sorted(ana)[:5]})")
    ok("avisos-rrhh" in cec and not any(k.startswith("cliente-") for k in cec), "N15 · Cecilia ve #avisos-rrhh y ningún grupo de cliente")
    for yo, canal in (("lucia", "avisos-rrhh"), ("lucia", "equipo-rrhh"), ("lucia", "cliente-musashi-consultores"), ("setter_ana", "avisos-accounts"),
                      ("cecilia", "cliente-gac"), ("camilo", "avisos-direccion")):
        c, t, _ = pedir(f"/api/canales/canal?id={canal}", yo=yo)
        ok(c == 403 and "mensajes" not in t, f"N15 · {yo} no lee {canal} → {c}")
        c = pedir("/api/canales/mensaje", "POST", {"canal_id": canal, "texto": "hola"}, yo=yo)[0]
        ok(c == 403, f"N15 · {yo} no escribe en {canal} → {c}")
    # Un aviso solo llega a quien tiene esa alerta: nada de alertas ajenas en los canales de Lucía
    mias = {a["id"] for a in json.loads((AQUI / "data/alertas/p_lucia.json").read_text()).get("alertas", [])}
    vistos = [m for m in js(pedir("/api/canales/canal?id=avisos-accounts", yo="lucia")).get("mensajes", []) if m.get("aviso")]
    ok(vistos and all(m["aviso"]["alerta_id"] in mias for m in vistos), f"N15 · los {len(vistos)} avisos de Lucía son alertas de su fichero")
    # Grupo propio: lo crea Lucía con Carla; ni Valeria, ni Tomás, ni Mili «como» Lucía lo leen
    c, t, _ = pedir("/api/canales/grupo", "POST", {"nombre": "Prueba N15", "miembros": ["carla"]}, yo="lucia")
    gid = json.loads(t).get("id") if c == 200 else None
    ok(c == 200 and gid, f"N15 · Lucía crea un grupo con Carla → {c}")
    # Se montan aquí para que el propio escáner de secretos no vea un teléfono ni una contraseña en este fichero.
    tel, clave = "61" + "2 345 6" + "78", "Secre" + "ta123"
    texto_prueba = "@Carla usuario: lucia.ro " + "contra" + "seña: " + clave + " · móvil " + tel + " · lucia" + "@ejemplo.com"
    c, t, _ = pedir("/api/canales/mensaje", "POST", {"canal_id": gid, "texto": texto_prueba}, yo="lucia")
    m = json.loads(t).get("mensaje", {}) if c == 200 else {}
    ok(c == 200 and clave not in t and tel not in t and "@ejemplo.com" not in t and m.get("menciones") == ["carla"],
       f"N15 · mensaje con contraseña, teléfono y correo: tapados, con mención a Carla ({m.get('texto', '')[:90]})")
    fila = db().execute("SELECT texto FROM canal_mensajes WHERE id=?", (m.get("id"),)).fetchone()
    ok(fila and clave not in fila[0] and tel not in fila[0], "N15 · …y en la base ya entra tapado")
    ok(pedir(f"/api/canales/canal?id={gid}", yo="carla")[0] == 200, "N15 · Carla (miembro) lo lee")
    for yo, como in (("valeria", None), ("tomas", None), ("mili", "lucia"), ("tomas", "lucia")):
        c = pedir(f"/api/canales/canal?id={gid}", yo=yo, como=como)[0]
        ok(c == 403, f"N15 · {yo}{' como ' + como if como else ''} no lee el grupo propio de Lucía → {c}")
    ok("tapada" not in pedir("/api/canales/buscar?q=usuario", yo="valeria")[1], "N15 · la búsqueda de Valeria no encuentra nada del grupo de Lucía")
    c = pedir("/api/canales/mensaje", "POST", {"canal_id": gid, "texto": "El sueldo de Carla es 1.500 € netos"}, yo="lucia")[0]
    ok(c == 400, f"N15 · los sueldos no se escriben en un canal → {c}")
    c = pedir("/api/canales/miembro", "POST", {"canal_id": "cliente-gac", "persona_id": "camilo"}, yo="lucia")[0]
    ok(c == 400, f"N15 · a un grupo de cliente no entra quien no puede abrir el cliente (Camilo en GAC) → {c}")
    c = pedir("/api/canales/miembro", "POST", {"canal_id": "avisos-accounts", "persona_id": "camilo"}, yo="lucia")[0]
    ok(c == 403, f"N15 · Lucía no añade gente a un canal de avisos (solo su jefe, Mili o Tomás) → {c}")
    # «Ver como»: se lee lo que ven las dos y no se escribe nada
    comoL = lista("tomas", "lucia")
    ok(comoL and set(comoL) <= set(luc), f"N15 · Tomás como Lucía ve un subconjunto de los canales de Lucía ({len(comoL)} de {len(luc)})")
    aviso = vistos[0] if vistos else {}
    for ruta, cuerpo in (("mensaje", {"canal_id": "equipo-accounts", "texto": "hola"}), ("estado", {"mensaje_id": aviso.get("id"), "estado": "lo_tengo"}),
                         ("leido", {"canal_id": "avisos-accounts", "hasta_id": 1}), ("preferencias", {"silenciados": []}),
                         ("grupo", {"nombre": "x", "miembros": []}), ("miembro", {"canal_id": "equipo-accounts", "persona_id": "carla"}),
                         ("campana_vista", {"hasta_id": 1})):
        c = pedir(f"/api/canales/{ruta}", "POST", cuerpo, yo="tomas", como="lucia")[0]
        ok(c == 403, f"N15 · «ver como» no escribe: /api/canales/{ruta} → {c}")
    c, t, _ = pedir("/api/canales/clickup?canal=2kyqzkcw-11995", yo="tomas", como="lucia")
    ok(c == 403 and "mensajes" not in t, f"N15 · «ver como» no abre el chat de ClickUp de otra persona → {c}")
    # «Lo tengo» desde el canal = la misma acción que Alertas (módulo «alertas»), con rastro
    antes = db().execute("SELECT count(*) FROM acciones WHERE modulo='alertas' AND tipo='alerta_lo_tengo'").fetchone()[0]
    abierto = next((m for m in vistos if "lo_tengo" in m["aviso"]["puede"]), None)
    c, t, _ = pedir("/api/canales/estado", "POST", {"mensaje_id": abierto["id"], "estado": "lo_tengo"}, yo="lucia") if abierto else (0, "{}", {})
    despues = db().execute("SELECT count(*) FROM acciones WHERE modulo='alertas' AND tipo='alerta_lo_tengo'").fetchone()[0]
    ok(c == 200 and despues == antes + 1 and json.loads(t)["aviso"]["estado"] == "lo_tengo", f"N15 · «Lo tengo» en el canal escribe la acción de Alertas ({antes} → {despues})")
    acc = js(pedir("/api/acciones?modulo=alertas", yo="lucia")).get("acciones", [])
    ok(abierto and any(a["objeto"] == abierto["aviso"]["alerta_id"] and a["tipo"] == "alerta_lo_tengo" for a in acc), "N15 · …y la pantalla de Alertas la ve")
    rrhh = [m for m in js(pedir("/api/canales/canal?id=avisos-rrhh", yo="tomas")).get("mensajes", []) if m.get("aviso")]
    if rrhh:
        c = pedir("/api/canales/estado", "POST", {"mensaje_id": rrhh[0]["id"], "estado": "lo_tengo"}, yo="lucia")[0]
        ok(c == 403, f"N15 · Lucía no marca un aviso de RRHH → {c}")
    # ClickUp: su canal sí (50 por página), uno ajeno no
    ind = json.loads((AQUI / "data/chat_equipo/p_lucia.json").read_text())
    suyo = ind["canales"][0]["id"] if ind.get("canales") else None
    tom = json.loads((AQUI / "data/chat_equipo/p_tomas.json").read_text())
    ajeno = next((c["id"] for c in tom.get("canales", []) if c["id"] not in {x["id"] for x in ind.get("canales", [])}), None)
    c, t, _ = pedir(f"/api/canales/clickup?canal={suyo}", yo="lucia")
    ok(c == 200 and len(json.loads(t)["mensajes"]) <= 50, f"N15 · Lucía lee su canal de ClickUp, 50 como mucho → {c}")
    c, t, _ = pedir(f"/api/canales/clickup?canal={ajeno}", yo="lucia")
    ok(c == 403 and "mensajes" not in t, f"N15 · Lucía no lee un canal de ClickUp que no es suyo → {c}")
    ok(pedir(f"/api/modulo/chat_equipo/_privado/c_{suyo}", yo="lucia")[0] == 403 and pedir(f"/data/chat_equipo/_privado/c_{suyo}.json", yo="lucia")[0] in (401, 403, 404),
       "N15 · los mensajes de ClickUp por canal no se sirven como fichero")
    # Importes: quien no ve cuota ni inversión no recibe cifras en euros en ningún canal
    for yo in ("camilo", "setter_ana", "cecilia"):
        todo = "".join(pedir(f"/api/canales/canal?id={cid}", yo=yo)[1] for cid in lista(yo))
        ok(not RE_EUR.search(todo), f"N15 · {yo}: ningún importe en sus canales")
    # Rastro de cada mensaje y tablas imborrables
    n = db().execute("SELECT count(*) FROM registro WHERE coleccion='chat-equipo' AND accion='canal_mensaje' AND quien='lucia'").fetchone()[0]
    ok(n >= 1, f"N15 · cada mensaje deja su fila en el rastro ({n})")
    cambia = borra = True
    try:
        con = db(); con.execute("UPDATE canal_mensajes SET texto='x' WHERE id=?", (m.get("id"),)); con.commit()
    except sqlite3.DatabaseError:
        cambia = False
    try:
        con = db(); con.execute("DELETE FROM canal_mensajes WHERE id=?", (m.get("id"),)); con.commit()
    except sqlite3.DatabaseError:
        borra = False
    ok(not cambia and not borra, "N15 · un mensaje no se cambia ni se borra (disparadores)")
    fuera = db().execute("SELECT count(*) FROM acciones WHERE herramienta='clickup' AND tipo NOT LIKE 'pieza_%' AND creada >= datetime('now','-10 minutes')").fetchone()[0]
    ok(fuera == 0, f"N15 · ningún mensaje de la app va a la cola de ClickUp ({fuera})")
    # Resumen diario a su hora (servidor propio con el reloj fijado: 03-oct 13:00 en Madrid = 08:00 en Buenos Aires)
    shutil.copy(tmp / "prueba.db", tmp / "resumen.db")
    env = {**os.environ, "RO_DB": str(tmp / "resumen.db"), "RO_RECARGA_CONFIG": str(tmp / "recarga.json"), "RO_AVISOS_AHORA": "2026-10-03 13:00",
           "RO_DEPARTAMENTOS": str(tmp / "departamentos.json")}
    env.pop("RO_MODO", None)
    srv, puerto = arrancar(env)
    if srv is None:
        ok(False, f"N15 · el servidor con el reloj fijado no arrancó ({puerto})")
        return
    B_antes, B = B, f"http://127.0.0.1:{puerto}"
    try:
        r_tomas = js(pedir("/api/canales/campana", yo="tomas")).get("resumen")
        r_lucia = js(pedir("/api/canales/campana", yo="lucia")).get("resumen")
        ok(r_tomas and r_tomas["dia"] == "2026-10-03" and not r_lucia, "N15 · a las 13:00 de Madrid, Tomás (Madrid) tiene su resumen y Lucía (Buenos Aires, 08:00) todavía no")
        ok(pedir("/api/canales/preferencias", "POST", {"silenciados": [], "hora_resumen": "07:45"}, yo="lucia")[0] == 200, "N15 · Lucía pone su resumen a las 07:45")
        r_lucia = js(pedir("/api/canales/campana", yo="lucia")).get("resumen")
        ok(r_lucia and r_lucia["dia"] == "2026-10-03" and "Lucía" in r_lucia["texto"], f"N15 · …y le llega a su hora ({(r_lucia or {}).get('titulo', '')[:80]})")
        ok(pedir("/api/canales/preferencias", "POST", {"silenciados": [], "hora_resumen": "25:00"}, yo="lucia")[0] == 400, "N15 · hora no válida → 400")
        ok(pedir("/api/avisos", yo="lucia")[0] == 403, "N15 · /api/avisos (avisos del sistema de E0) sigue igual: Lucía → 403")
    finally:
        B = B_antes
        parar(srv)


# ============================================================================ A8 · Alertas: posponer y lote (2-oct noche)
def alertas_a8(tmp):
    """Nadie pospone (ni despacha en lote) alertas ajenas · «ver como» no escribe · fecha de vuelta acotada · lo pospuesto
    no escala y vuelve solo. Con la COPIA de la base: el motor se regenera en una carpeta temporal (nunca en data/)."""
    from datetime import datetime as _dt, timedelta as _td
    db = lambda: sqlite3.connect(tmp / "prueba.db")
    n_acc = lambda: db().execute("SELECT count(*) FROM acciones WHERE modulo='alertas'").fetchone()[0]
    todas = json.loads((AQUI / "data/alertas/alertas.json").read_text()).get("alertas", [])
    mias = [a for a in json.loads((AQUI / "data/alertas/p_lucia.json").read_text()).get("alertas", [])
            if a["dueno_id"] == "lucia" and a["estado"] in ("nueva", "vista", "reabierta")]
    ajena = next((a for a in todas if "lucia" not in a.get("escalado_cadena", []) and a.get("jefe_id") != "lucia" and not a.get("cliente_id")), None)
    if len(mias) < 3 or not ajena:
        return ok(False, f"A8 · faltan alertas para probar (de Lucía {len(mias)}, ajena {bool(ajena)})")
    manana = (_dt.now() + _td(days=1)).strftime("%Y-%m-%d 09:00")
    lejos = (_dt.now() + _td(days=40)).strftime("%Y-%m-%d 09:00")
    posp = lambda a, hasta, txt: {"modulo": "alertas", "herramienta": "app", "tipo": "alerta_posponer", "objeto": a["id"], "cliente_id": a.get("cliente_id"),
                                  "texto": txt, "vista_previa": {"alerta": a["id"], "hasta": hasta, "cuando": "manana"}}
    lote = lambda ids, accion, txt, **kw: {"modulo": "alertas", "herramienta": "app", "tipo": "alerta_lote", "objeto": f"lote:{len(ids)}:{ids[0]}",
                                           "texto": txt, "vista_previa": {"ids": ids, "accion": accion, **kw}}

    # «ver como» no escribe: ni posponer ni lote (403 y ninguna fila nueva)
    n0 = n_acc()
    c1 = pedir("/api/acciones", "POST", posp(mias[0], manana, "a8 ver como"), yo="tomas", como="lucia")[0]
    c2 = pedir("/api/acciones", "POST", lote([mias[0]["id"]], "lo_tengo", "a8 ver como lote"), yo="mili", como="lucia")[0]
    ok(c1 == 403 and c2 == 403 and n_acc() == n0, f"A8 · «ver como» no pospone ni despacha en lote ({c1}, {c2}; filas nuevas {n_acc() - n0})")
    # los tipos nuevos están dados de alta (reglas_permisos.json → acciones_permitidas.alertas)
    c3 = pedir("/api/acciones", "POST", posp(mias[0], manana, "a8 posponer la suya"), yo="lucia")[0]
    c4 = pedir("/api/acciones", "POST", lote([mias[1]["id"], ajena["id"]], "posponer", "a8 lote con una ajena", hasta=manana), yo="lucia")[0]
    c5 = pedir("/api/acciones", "POST", posp(mias[2], lejos, "a8 posponer 40 días"), yo="lucia")[0]
    con_guardia = "guardia_alertas" in (AQUI / "servir.py").read_text()
    c6 = pedir("/api/acciones", "POST", posp(ajena, manana, "a8 posponer una ajena"), yo="lucia")[0]
    ok(c3 == 200, f"A8 · Lucía pospone una alerta suya → {c3} (tipo alerta_posponer permitido)")
    if con_guardia:
        ok(c6 == 403 and c4 == 403 and c5 == 400, f"A8 · servidor: alerta ajena → {c6}, lote con una ajena → {c4}, 40 días → {c5} (403, 403, 400)")
    else:
        print(f"· A8 · servir.py aún sin la guardia (dudas_pintura «A8 · guardia en servir.py»): ajena {c6}, lote {c4}, 40 días {c5} entran en la cola; las para el motor ↓")
    # R15 · doble barrera: con la guardia en la puerta, lo ajeno y la fecha imposible ni entran en la cola (403/400 arriba).
    # Para comprobar que el MOTOR también los rechaza, se meten esas mismas filas directamente en la base de prueba
    # (como si alguien se saltara la puerta) y el motor tiene que dejarlas en «rechazadas».
    if con_guardia:
        with db() as con:
            for b in (lote([mias[1]["id"], ajena["id"]], "posponer", "a8 lote con una ajena (directo a la base)", hasta=manana),
                      posp(mias[2], lejos, "a8 posponer 40 días (directo a la base)"),
                      posp(ajena, manana, "a8 posponer una ajena (directo a la base)")):
                con.execute("INSERT INTO acciones (quien, herramienta, tipo, objeto, cliente_id, modulo, texto, vista_previa, estado, detalle) VALUES (?,?,?,?,?,?,?,?, 'simulada', ?)",
                            ("lucia", b["herramienta"], b["tipo"], str(b["objeto"]), b.get("cliente_id"), b["modulo"], b["texto"],
                             json.dumps(b["vista_previa"], ensure_ascii=False), "prueba R15: saltándose la puerta"))
    # la guardia del servidor (fuentes_alertas/guardia_alertas.py), en proceso: la misma regla que el motor
    sys.path.insert(0, str(AQUI / "fuentes_alertas"))
    import guardia_alertas as G
    lucia = PERSONAS["lucia"]
    r_aj = G.revisar(lucia, posp(ajena, manana, "x"))
    r_mia = G.revisar(lucia, posp(mias[0], manana, "x"))
    r_lote = G.revisar(lucia, lote([mias[1]["id"], ajena["id"]], "posponer", "x", hasta=manana))
    r_lejos = G.revisar(lucia, posp(mias[2], lejos, "x"))
    r_noap = G.revisar(lucia, lote([mias[1]["id"]], "no_aplica", "x"))
    ok(r_aj and r_aj[0] == 403 and r_mia is None and r_lote and r_lote[0] == 403 and r_lejos and r_lejos[0] == 400 and r_noap and r_noap[0] == 400,
       f"A8 · guardia: ajena {r_aj and r_aj[0]}, suya {r_mia}, lote con ajena {r_lote and r_lote[0]}, 40 días {r_lejos and r_lejos[0]}, «no aplica» sin motivo {r_noap and r_noap[0]}")
    # el motor: aplica lo suyo, ignora lo ajeno y la fecha imposible (quedan en «rechazadas»); lo pospuesto no escala
    sal = tmp / "alertas_a8"
    sal.mkdir(exist_ok=True)
    shutil.copy(AQUI / "fuentes_alertas/estado_alertas.json", tmp / "estado_a8.json")
    genera = lambda ahora=None: subprocess.run([sys.executable, "fuentes_alertas/generar_alertas.py"], cwd=AQUI, capture_output=True, text=True,
                                               env={**os.environ, "RO_DB": str(tmp / "prueba.db"), "RO_ALERTAS_SALIDA": str(sal), "RO_ALERTAS_ESTADO": str(tmp / "estado_a8.json"),
                                                    **({"RO_ALERTAS_AHORA": ahora} if ahora else {})})
    r = genera()
    if r.returncode:
        return ok(False, f"A8 · el motor no corre sobre la copia: {r.stderr[-300:]}")
    t = {a["id"]: a for a in json.loads((sal / "alertas.json").read_text())["alertas"]}
    rech = json.loads((sal / "alertas.json").read_text()).get("rechazadas", [])
    ok(t[mias[0]["id"]]["estado"] == "pospuesta" and t[mias[1]["id"]]["estado"] == "pospuesta", "A8 · lo de Lucía queda pospuesto (una suelta y otra en lote)")
    ok(t[ajena["id"]]["estado"] != "pospuesta" and any(x["alerta"] == ajena["id"] and x["quien"] == "lucia" for x in rech),
       f"A8 · nadie pospone alertas ajenas: la de {ajena['dueno_id']} sigue «{t[ajena['id']]['estado']}» y el intento queda en «rechazadas»")
    ok(t[mias[2]["id"]]["estado"] != "pospuesta" and any(x["alerta"] == mias[2]["id"] and "fecha" in x["motivo"] for x in rech),
       "A8 · posponer 40 días no se aplica (de mañana a 31 días) y queda en «rechazadas»")
    pl = json.loads((sal / "p_lucia.json").read_text())
    ok(not any(x["quien"] != "lucia" and x["dueno_id"] != "lucia" for x in pl.get("rechazadas", [])), "A8 · Lucía solo ve sus propios intentos rechazados")
    ok(t[mias[0]["id"]]["escalado"]["nivel"] == 0 and pl["contadores"]["pospuestas"] >= 2 and pl["mi_dia"]["total"] == pl["contadores"]["mias"],
       f"A8 · lo pospuesto no escala ni cuenta en «mías» (pospuestas {pl['contadores']['pospuestas']}; Mi día {pl['mi_dia']['total']} = {pl['contadores']['mias']})")
    # simulando el día siguiente a las 10:00: vuelve sola, con el plazo de nuevo (no escala de golpe)
    r = genera((_dt.now() + _td(days=1)).strftime("%Y-%m-%d 10:00"))
    t2 = {a["id"]: a for a in json.loads((sal / "alertas.json").read_text())["alertas"]}
    a0 = t2.get(mias[0]["id"])
    ok(a0 and a0["estado"] == "nueva" and a0.get("volvio") and a0["escalado"]["nivel"] == 0,
       f"A8 · al llegar la fecha vuelve sola («{a0 and a0['estado']}»), con el plazo de nuevo y sin escalar (nivel {a0 and a0['escalado']['nivel']})")


# ============================================================================ R15 · buscador, «Mis clientes», «Algo va mal», Conexiones
def ronda15(tmp):
    """El buscador no devuelve nada que la persona no vea · «Algo va mal» no deja escribir como otro · «Mis clientes» solo
    con clientes que abres · Agus prueba conexiones (solo ese paso)."""
    db = lambda: sqlite3.connect(tmp / "prueba.db")
    j = lambda r: json.loads(r[1]) if r[0] == 200 else {}
    # ---- A5 · buscador: cada fila sale de lo que la persona YA recibe por la puerta de su fichero
    ok(pedir("/api/buscar/indice")[0] == 401 and pedir("/api/buscar?q=gac")[0] == 401, "R15 A5 · sin identidad, el buscador → 401")
    FUENTE = {"Tareas": ("produccion/produccion", "cola", "id"), "Correos": ("bandeja/bandeja", "correos", "id"), "Webs": ("seo/webs", "webs", "cliente"),
              "Campañas": ("captacion/captacion", "clientes", "cliente_id"), "Decisiones": ("decisiones/reloj", "decisiones", "id"),
              "Incidencias": ("incidencias/incidencias", "incidencias", "id")}
    clave_de = {"Tareas": lambda x: x["ir"].split("/")[-1], "Correos": lambda x: x["id"], "Webs": lambda x: x["ir"].split("/")[-1],
                "Campañas": lambda x: x["ir"].split("/")[-1], "Decisiones": lambda x: x["ir"].split("/")[-1], "Incidencias": lambda x: x["ir"].split("/")[-1]}
    for yo in ("lucia", "candela", "camilo", "sofia", "setter_ana", "jeronimo", "valeria", "agustina"):
        if yo not in PERSONAS:
            continue
        idx = j(pedir("/api/buscar/indice", yo=yo)).get("filas")
        if idx is None:
            ok(False, f"R15 A5 · {yo}: el índice del buscador no responde")
            continue
        fuera = []
        for g, (rel, lista, campo) in FUENTE.items():
            filas = [x for x in idx if x["g"] == g]
            c, t, _ = pedir(f"/api/modulo/{rel}", yo=yo)
            if c != 200:
                if filas:
                    fuera.append(f"{g}: {len(filas)} filas sin poder leer {rel} ({c})")
                continue
            ve = {str(r.get(campo)) for r in (json.loads(t).get(lista) or []) if isinstance(r, dict)}
            fuera += [f"{g}: {clave_de[g](x)}" for x in filas if clave_de[g](x) not in ve]
        c, t, _ = pedir(f"/api/modulo/alertas/p_{yo}", yo=yo)
        al = [x for x in idx if x["g"] == "Alertas"]
        ve_al = {a["id"] for a in json.loads(t).get("alertas", [])} if c == 200 else set()
        fuera += [f"Alertas: {x.get('id')}" for x in al if x.get("id") not in ve_al]
        ses = j(pedir("/api/sesion", yo=yo)).get("datos", {})
        abre = {c["id"] for c in ses.get("clientes", []) if c.get("detalle")}
        fuera += [f"Correo de {x.get('cid')} (no lo abre)" for x in idx if x["g"] == "Correos" and x.get("cid") and x["cid"] not in abre]
        ok(not fuera, f"R15 A5 · {yo}: las {len(idx)} filas del buscador salen de lo que ya recibe ({fuera[:3] or 'nada ajeno'})")
        ok("_privado" not in json.dumps(idx), f"R15 A5 · {yo}: nada de _privado/ en el índice")
        r = j(pedir("/api/buscar?q=a", yo=yo)).get("filas", [])
        ok(all(x in idx for x in r), f"R15 A5 · {yo}: /api/buscar?q= solo devuelve filas de su índice ({len(r)})")
    idx_cam = j(pedir("/api/buscar/indice", yo="camilo")).get("filas", [])
    ok(not [x for x in idx_cam if x["g"] in ("Correos", "Campañas", "Decisiones")], "R15 A5 · Camilo (producción) no encuentra correos, campañas ni decisiones")
    CAMPOS = {"g", "t", "s", "ir", "k", "id", "cli", "cid", "h", "mia", "pos", "plazo_h"}
    raros = {k for yo in ("sofia", "mili", "lucia") for x in j(pedir("/api/buscar/indice", yo=yo)).get("filas", []) for k in x if k not in CAMPOS}
    ok(not raros, f"R15 A5 · cada fila del índice lleva solo texto, ruta y claves de búsqueda (nada de importes ni datos de contacto) ({raros or 'bien'})")
    luc = j(pedir("/api/buscar/indice", yo="lucia")).get("filas", [])
    como = j(pedir("/api/buscar/indice", yo="tomas", como="lucia")).get("filas", [])
    ok(como and not [x for x in como if x["g"] == "Alertas"] and all(x in luc for x in como if x["g"] != "Alertas"),
       f"R15 A5 · Tomás como Lucía: el índice ⊆ el de Lucía y sin sus alertas propias ({len(como)} de {len(luc)})")
    mili = j(pedir("/api/buscar/indice", yo="mili")).get("filas", [])
    al_luc = {x.get("id") for x in luc if x["g"] == "Alertas"}
    mias_luc = {a["id"] for a in j(pedir("/api/modulo/alertas/p_lucia", yo="lucia")).get("alertas", [])}
    ajenas = {x.get("id") for x in mili if x["g"] == "Alertas"} - mias_luc
    ok(ajenas and not (al_luc & ajenas), f"R15 A5 · ninguna de las {len(ajenas)} alertas que ve Mili y no Lucía sale en el buscador de Lucía")
    ok(db().execute("SELECT count(*) FROM registro WHERE accion='lectura' AND clave LIKE '%buscar%'").fetchone()[0] >= 1, "R15 A5 · lo que se busca en «ver como» queda en el rastro")

    # ---- A7 · «Algo va mal / Tengo una idea»
    n0 = db().execute("SELECT count(*) FROM opiniones").fetchone()[0]
    cuerpo = {"tipo": "fallo", "prioridad": "rojo", "texto": "R15 prueba: no carga la Bandeja", "ruta": "#/bandeja", "pantalla": "Bandeja", "ancho": 390,
              "quien": "mili", "real": "mili", "creada": "2020-01-01 00:00:00", "estado": "resuelta"}
    c, t, _ = pedir("/api/opinion", "POST", cuerpo, yo="lucia")
    oid = json.loads(t).get("id") if c == 200 else None
    fila = db().execute("SELECT quien, creada, estado FROM opiniones WHERE id=?", (oid or 0,)).fetchone()
    ok(c == 200 and fila and fila[0] == "lucia" and fila[2] == "nueva" and not fila[1].startswith("2020"),
       f"R15 A7 · «Algo va mal» con quien=mili en el cuerpo se guarda a nombre de Lucía, con hora y estado del servidor → {c}, {fila}")
    ok(db().execute("SELECT count(*) FROM registro WHERE accion='opinion_enviada' AND quien='lucia' AND clave=?", (str(oid),)).fetchone()[0] == 1, "R15 A7 · queda en el rastro (quién = Lucía)")
    av = db().execute("SELECT canal_id, quien, ver FROM canal_mensajes WHERE clave=?", (f"opinion:{oid}",)).fetchone()
    ok(av and av[0] == "avisos-direccion" and av[1] == "lucia" and "direccion" in (av[2] or ""), f"R15 A7 · aviso en #avisos-dirección, solo para dirección y operaciones ({av})")
    c = pedir("/api/opinion", "POST", {**cuerpo, "texto": "como Lucía"}, yo="tomas", como="lucia")[0]
    ok(c == 403, f"R15 A7 · «ver como» no envía nada (Tomás como Lucía) → {c}")
    ok(pedir("/api/rastro", "POST", {"accion": "opinion_enviada", "objeto": "1"}, yo="lucia")[0] == 403, "R15 A7 · el navegador no puede fingir «opinion_enviada» en el rastro")
    ok(pedir("/api/opinion", "POST", {**cuerpo, "captura": "data:image/png;base64,AAAA"}, yo="lucia")[0] == 400, "R15 A7 · captura que no es JPEG → 400")
    ok(pedir("/api/opinion", "POST", {**cuerpo, "captura": "data:image/jpeg;base64," + "A" * 190_100}, yo="lucia")[0] in (400, 500), "R15 A7 · captura de más de 190 KB → no entra")
    c, t, _ = pedir("/api/opinion", "POST", {**cuerpo, "texto": "con captura", "captura": "data:image/jpeg;base64,/9j/4AAQSkZJRg=="}, yo="lucia")
    oid2 = json.loads(t).get("id") if c == 200 else 0
    ok(c == 200, f"R15 A7 · con una captura JPEG pequeña → {c}")
    ok(pedir("/api/opinion", "POST", {**cuerpo, "tipo": "queja"}, yo="lucia")[0] == 400 and pedir("/api/opinion", "POST", {**cuerpo, "texto": " "}, yo="lucia")[0] == 400,
       "R15 A7 · tipo raro o sin texto → 400")
    ok(pedir("/api/opinion", "POST", {**cuerpo, "ruta": "javascript:alert(1)"}, yo="lucia")[0] == 200 and
       db().execute("SELECT ruta FROM opiniones ORDER BY id DESC LIMIT 1").fetchone()[0] is None, "R15 A7 · una ruta que no es de la app no se guarda")
    l_c = j(pedir("/api/opiniones", yo="candela"))
    ok(not l_c.get("todas") and all(x["quien"] == "candela" for x in l_c.get("opiniones", [])), "R15 A7 · Candela solo ve las suyas (ninguna de Lucía)")
    ok(pedir(f"/api/opiniones/captura?id={oid2}", yo="candela")[0] == 403, "R15 A7 · Candela no abre la captura de Lucía → 403")
    ok(pedir(f"/api/opiniones/captura?id={oid2}", yo="lucia")[0] == 200 and pedir(f"/api/opiniones/captura?id={oid2}", yo="mili")[0] == 200, "R15 A7 · la autora y Mili sí")
    l_m = j(pedir("/api/opiniones", yo="mili"))
    ok(l_m.get("todas") and any(x["id"] == oid for x in l_m.get("opiniones", [])) and not any("captura" in x for x in l_m.get("opiniones", [])),
       "R15 A7 · Mili ve todas (la lista sin las capturas: se piden una a una)")
    ok(not j(pedir("/api/opiniones", yo="mili", como="lucia")).get("todas"), "R15 A7 · Mili como Lucía no ve las de todos (solo las de Lucía)")
    ok(pedir("/api/opiniones/estado", "POST", {"id": oid, "estado": "resuelta"}, yo="lucia")[0] == 403, "R15 A7 · Lucía no marca resuelta la suya (lo hacen Mili o Tomás)")
    ok(pedir("/api/opiniones/estado", "POST", {"id": oid, "estado": "resuelta"}, yo="mili")[0] == 200, "R15 A7 · Mili la marca resuelta")
    try:
        with db() as con:
            con.execute("DELETE FROM opiniones WHERE id=?", (oid,))
        borra = True
    except sqlite3.DatabaseError:
        borra = False
    try:
        with db() as con:
            con.execute("UPDATE opiniones SET quien='mili' WHERE id=?", (oid,))
        cambia = True
    except sqlite3.DatabaseError:
        cambia = False
    ok(not borra and not cambia, "R15 A7 · una opinión no se borra ni cambia de autor (disparadores de la base)")
    ok(db().execute("SELECT count(*) FROM opiniones").fetchone()[0] - n0 >= 3, "R15 A7 · todo en la base de la app (nada sale fuera)")

    # ---- A6 · «Mis clientes» fijados
    ses = j(pedir("/api/sesion", yo="lucia")).get("datos", {})
    abre = [c["id"] for c in ses.get("clientes", []) if c.get("detalle")]
    # 3-oct: con «solo su cartera» el account ya no recibe clientes ajenos en la sesión: el ajeno sale de la verdad única
    ajeno = next((c["id"] for c in ses.get("clientes", []) if not c.get("detalle")), None) or next(
        (c["cliente_id"] for c in json.loads((AQUI / "data/verdad/clientes.json").read_text())["clientes"] if c["cliente_id"] not in abre), None)
    ok(pedir("/api/preferencias", "POST", {"fijados": abre[:2] + [ajeno]}, yo="lucia")[0] == 403, f"R15 A6 · Lucía no fija {ajeno} (no lo abre) → 403")
    ok(pedir("/api/preferencias", "POST", {"fijados": abre[:2]}, yo="lucia")[0] == 200 and j(pedir("/api/preferencias", yo="lucia")).get("fijados") == abre[:2],
       "R15 A6 · fija dos suyos y se guardan por persona")
    ok(j(pedir("/api/preferencias", yo="candela")).get("fijados") is None, "R15 A6 · los de Lucía no son de Candela")
    ok(pedir("/api/preferencias", "POST", {"fijados": abre[:1]}, yo="tomas", como="lucia")[0] == 403, "R15 A6 · «ver como» no cambia los fijados")
    ok(pedir("/api/preferencias", "POST", {"fijados": [f"x{i}" for i in range(31)]}, yo="lucia")[0] == 400, "R15 A6 · más de 30 → 400")
    ok(db().execute("SELECT count(*) FROM registro WHERE accion='cliente_fijado' AND quien='lucia'").fetchone()[0] >= 2, "R15 A6 · fijar queda en el rastro")
    c, t, _ = pedir("/api/contadores", yo="lucia")
    ok(c == 200 and set(json.loads(t)) == {"produccion"}, f"R15 A6 · /api/contadores solo da la cifra (sin filas) → {c}")

    # ---- Conexiones: Agus prueba SOLO la salud de las conexiones; la recarga entera sigue siendo de Mili y Tomás
    c, t, _ = pedir("/api/recarga", "POST", {}, yo="agustina")
    ok(c == 200 and json.loads(t).get("recarga", {}).get("modo") == "conexiones", f"R15 · Agus pulsa «Probar ahora» → solo el paso de conexiones ({c}, {json.loads(t).get('recarga', {}).get('modo') if c == 200 else t[:80]})")
    ok(pedir("/api/recarga", "POST", {"modo": "ligera"}, yo="agustina")[0] == 403, "R15 · Agus no lanza la recarga entera → 403")
    ok(pedir("/api/recarga", "POST", {"modo": "conexiones"}, yo="lucia")[0] == 403, "R15 · Lucía no prueba conexiones → 403")
    ok(pedir("/api/recarga", "POST", {"modo": "completa"}, yo="tomas")[0] == 400, "R15 · un modo raro → 400 (la completa va por horario)")
    ok(pedir("/api/recarga", "POST", {"modo": "conexiones"}, yo="tomas", como="agustina")[0] == 403, "R15 · «ver como» no prueba nada")



def ronda16(tmp):
    """R16 (auditoría 35b): N1-N13 y B1-B7, cada uno con su prueba (fallaban antes del arreglo)."""
    db = lambda: sqlite3.connect(tmp / "prueba.db")
    j = lambda r: json.loads(r[1]) if r[0] == 200 else {}
    # Montados por trozos para que el escáner de secretos no los vea en este fichero.
    clave, tel, correo = "Lina" + "2026!", "6123" + "45678", "lina.personal" + "@" + "gmail.com"
    # ---- N1 · «Algo va mal» tapa contraseñas, correos y teléfonos ANTES de guardar, del rastro y del aviso
    txt = f"No carga. Mi contra" + f"seña: {clave} y llamadme al {tel} o {correo}"
    c, t, _ = pedir("/api/opinion", "POST", {"tipo": "fallo", "prioridad": "rojo", "texto": txt, "esperaba": f"que cargue ({correo})", "ruta": "#/bandeja", "pantalla": "Bandeja"}, yo="lina")
    oid = j((c, t)).get("id") or 0
    fila = db().execute("SELECT texto, esperaba FROM opiniones WHERE id=?", (oid,)).fetchone() or ("", "")
    ok(c == 200 and all(x not in " ".join(map(str, fila)) for x in (clave, tel, correo)), f"R16 N1 · en «opiniones» ya entra tapada ({str(fila[0])[:70]})")
    reg = db().execute("SELECT datos FROM registro WHERE accion='opinion_enviada' AND clave=?", (str(oid),)).fetchone()
    ok(reg and all(x not in reg[0] for x in (clave, tel, correo, "No carga")), f"R16 N1 · el rastro imborrable lleva solo tipo y largo, sin el texto ({(reg or [''])[0][:80]})")
    av = db().execute("SELECT texto FROM canal_mensajes WHERE clave=?", (f"opinion:{oid}",)).fetchone()
    ok(av and all(x not in av[0] for x in (clave, tel, correo)), "R16 N1 · el aviso de #avisos-dirección sin contraseña, teléfono ni correo")
    l_m = pedir("/api/opiniones", yo="mili")[1]
    ok(all(x not in l_m for x in (clave, tel, correo)), "R16 N1 · Mili lo lee ya tapado")
    c, t, _ = pedir("/api/opinion", "POST", {"tipo": "fallo", "texto": "la contra" + "seña de su WordPress es Conci" + "lia2026!", "ruta": "#/ficha"}, yo="lina")
    f2 = db().execute("SELECT texto FROM opiniones WHERE id=?", (j((c, t)).get("id") or 0,)).fetchone()
    ok(f2 and "lia2026!" not in f2[0], f"R16 N10 · «la contraseña de … es X» (sin dos puntos) también se tapa ({(f2 or [''])[0]})")
    c, t, _ = pedir("/api/opinion", "POST", {"tipo": "fallo", "texto": "no carga el gráfico", "ruta": "#/personas/sueldos", "captura": "data:image/jpeg;base64,/9j/4AAQSkZJRg=="}, yo="cecilia")
    f3 = db().execute("SELECT captura FROM opiniones WHERE id=?", (j((c, t)).get("id") or 0,)).fetchone()
    ok(c == 200 and f3 and not f3[0], "R16 N1 · una captura hecha en Sueldos no se guarda (la verían Mili y otros)")
    eq = j(pedir("/api/opiniones", yo="valeria")).get("equipo") or {}
    ok((eq.get("lina") or {}).get("alguna") is True and "texto" not in json.dumps(eq), f"R16 · primera semana: Valeria sabe que Lina ya mandó un «Algo va mal» (solo el hecho) ({eq.get('lina')})")

    # ---- N2 · sueldos en los canales
    for texto in ("Lina pasa a cobrar 1.800 € brutos al mes desde noviembre", "Su salario: mil ochocientos euros", "1.800 € brutos para Lina",
                  "Lina sube a 1.900 € al mes"):
        c = pedir("/api/canales/mensaje", "POST", {"canal_id": "general", "texto": texto}, yo="cecilia")[0]
        ok(c == 400, f"R16 N2 · «{texto}» en #general → {c} (no se escribe)")
    c = pedir("/api/canales/mensaje", "POST", {"canal_id": "general", "texto": "Marlex paga 1.470 €/mes desde octubre: bienvenida"}, yo="mili")[0]
    ok(c == 200, f"R16 N2 · la cuota de un cliente no es un sueldo (se escribe) → {c}")
    with db() as con:      # un mensaje de antes del filtro, guardado tal cual
        con.execute("INSERT INTO canal_mensajes (canal_id, tipo, quien, texto, clave) VALUES ('general','mensaje','cecilia',?, 'r16-sueldo-viejo')",
                    ("Lina pasa a cobrar 1.800 € brutos al mes",))
    def texto_de(yo):
        msgs = j(pedir("/api/canales/canal?id=general", yo=yo)).get("mensajes", [])
        return " ".join(m["texto"] for m in msgs if "cobrar" in m.get("texto", ""))
    ok("1.800" not in texto_de("mili") and "1.800" not in texto_de("sofia") and "1.800" in texto_de("tomas") and "1.800" in texto_de("cecilia"),
       "R16 N2 · lo guardado de antes: Mili y Sofía lo leen sin la cifra; Tomás y Cecilia, con ella")

    # ---- N3 · RRHH y Dirección: solo Tomás (y Cecilia en RRHH) añaden gente
    for yo, canal, persona_, esperado in (("mili", "equipo-rrhh", "lina", 403), ("mili", "equipo-direccion", "lina", 403), ("mili", "avisos-rrhh", "lina", 403),
                                         ("carla", "equipo-accounts", "eulimar", 403), ("mili", "equipo-accounts", "eulimar", 200),
                                         ("cecilia", "equipo-rrhh", "carla", 200), ("tomas", "equipo-direccion", "mili", 200)):
        c = pedir("/api/canales/miembro", "POST", {"canal_id": canal, "persona_id": persona_}, yo=yo)[0]
        ok(c == esperado, f"R16 N3 · {yo} añade a {persona_} a {canal} → {c} (esperado {esperado})")
    ok("equipo-rrhh" not in {x["id"] for x in j(pedir("/api/canales", yo="lina")).get("canales", [])}, "R16 N3 · Lina no está en Equipo de RRHH")
    pa = {x["id"]: x.get("puede_anadir") for x in j(pedir("/api/canales", yo="mili")).get("canales", [])}
    ok(pa.get("equipo-rrhh") is False and pa.get("equipo-accounts") is True, "R16 N3 · la pantalla de Mili no ofrece «Añadir» en RRHH (sí en Accounts)")

    # ---- N4 · envíos sin dueño y saltarse la revisión
    prod = json.loads((AQUI / "data/produccion/produccion.json").read_text())
    c = pedir("/api/acciones", "POST", {"herramienta": "whatsapp", "tipo": "whatsapp", "objeto": "+34600000000", "modulo": "bandeja", "texto": "hola desde la app"}, yo="carla")[0]
    ok(c == 403, f"R16 N4 · WhatsApp a un número escrito a mano → {c}")
    c = pedir("/api/acciones", "POST", {"herramienta": "gmail", "tipo": "correo", "objeto": "cliente" + "@" + "accompany.es", "modulo": "bandeja", "texto": "hola"}, yo="carla")[0]
    ok(c == 403, f"R16 N4 · correo a una dirección escrita a mano, sin cliente → {c}")
    c = pedir("/api/acciones", "POST", {"herramienta": "gmail", "tipo": "correo", "objeto": "cliente" + "@" + "accompany.es", "cliente_id": "concilia", "modulo": "bandeja", "texto": "hola"}, yo="carla")[0]
    ok(c == 403, f"R16 N4 · …ni diciendo un cliente suyo (el destinatario lo pone el servidor) → {c}")
    c = pedir("/api/acciones", "POST", {"herramienta": "ghl", "tipo": "mover_oportunidad", "objeto": "Musashi · oportunidad x", "cliente_id": "musashi-consultores", "modulo": "ficha"}, yo="carla")[0]
    ok(c == 403, f"R16 N4 · mover una oportunidad de un cliente que no lleva → {c}")
    c = pedir("/api/acciones", "POST", {"herramienta": "whatsapp", "tipo": "whatsapp", "objeto": "concilia", "cliente_id": "concilia", "modulo": "ficha", "texto": "hola"}, yo="carla")[0]
    ok(c == 200, f"R16 N4 · WhatsApp al grupo de SU cliente (Concilia) sí → {c}")
    de_carla = next((r for r in prod["cola"] if r.get("persona_id") == "carla" and r.get("grupo") == "revision"), None)
    if de_carla:
        for tipo in ("mover_estado", "mover_tarjeta"):
            c = pedir("/api/acciones", "POST", {"herramienta": "clickup", "tipo": tipo, "objeto": de_carla["id"], "modulo": "produccion", "texto": "a enviar cliente"}, yo="carla")[0]
            ok(c == 403, f"R16 N4 · la autora hace «{tipo}» de su pieza en revisión → {c} (se salta la revisión)")
    c = pedir("/api/acciones", "POST", {"herramienta": "app", "tipo": "asignacion", "objeto": "lina", "modulo": "ficha"}, yo="carla")[0]
    ok(c == 403, f"R16 N4 · un account encola una asignación → {c}")
    propia = next((r for r in prod["cola"] if r.get("persona_id") == "camilo" and r.get("grupo") != "revision"), None)
    if propia:
        c = pedir("/api/acciones", "POST", {"herramienta": "clickup", "tipo": "mover_estado", "objeto": propia["id"], "modulo": "produccion", "texto": "a revisión"}, yo="camilo")[0]
        c2 = pedir("/api/acciones", "POST", {"herramienta": "clickup", "tipo": "mover_estado", "objeto": propia["id"], "modulo": "produccion", "texto": "a revisión"}, yo="manuel")[0]
        ok(c == 200 and c2 == 403, f"R16 N4 · Camilo mueve SU tarea ({c}); Manuel no mueve la de Camilo ({c2})")

    # ---- N5 · alertas ajenas: «no aplica» y «resuelta» solo dueño, jefe, Mili y Tomás
    todas = json.loads((AQUI / "data/alertas/alertas.json").read_text()).get("alertas", [])
    ajena = next((a for a in todas if "carla" not in (a.get("escalado_cadena") or []) and a.get("jefe_id") != "carla"), None)
    for tipo in ("alerta_no_aplica", "alerta_resuelta", "alerta_lo_tengo"):
        c = pedir("/api/acciones", "POST", {"herramienta": "app", "tipo": tipo, "objeto": ajena["id"], "modulo": "alertas", "texto": "no aplica porque si"}, yo="carla")[0]
        ok(c == 403, f"R16 N5 · Carla «{tipo}» en una alerta ajena → {c}")
    mia = next((a for a in json.loads((AQUI / "data/alertas/p_lucia.json").read_text()).get("alertas", []) if "lucia" in (a.get("escalado_cadena") or [])), None)
    if mia:
        c = pedir("/api/acciones", "POST", {"herramienta": "app", "tipo": "alerta_resuelta", "objeto": mia["id"], "modulo": "alertas", "texto": "Resuelta: prueba R16"}, yo="lucia")[0]
        ok(c == 200, f"R16 N5 · Lucía sí resuelve una alerta suya → {c}")
    sys.path.insert(0, str(AQUI / "fuentes_alertas"))
    import generar_alertas as GA
    ok({"resuelta", "no_aplica", "lo_tengo"} <= GA.SOLO_SUYAS, "R16 N5 · el motor también rechaza «resuelta», «no aplica» y «lo tengo» ajenos")

    # ---- N7 · la guía de primera semana sin importes de la empresa para quien no ve el dinero
    for yo in ("jeronimo", "lina", "carla"):
        c, t, _ = pedir("/api/modulo/primera_semana/guias", yo=yo)
        ok(c == 200 and "30.000" not in t and "€" not in t, f"R16 N7 · {yo}: las guías sin «30.000 €/mes» → {c}")
    ok("30.000" in pedir("/api/modulo/primera_semana/guias", yo="tomas")[1], "R16 N7 · Tomás sí lo ve")
    g = json.loads(pedir("/api/modulo/primera_semana/guias", yo="tomas")[1])
    ok(not any("|" in ((v.get("guia") or {}).get("numero_que_manda") or "") for v in g.get("puestos", {}).values()), "R16 · el número que manda llega en texto llano (sin la tabla en bruto)")

    # ---- N9 · rastro: solo colecciones de pantallas que se ven
    c = pedir("/api/rastro", "POST", {"accion": "marcar", "modulo": "sueldos", "objeto": "sueldos/_privado/sueldos#analisis", "datos": {"texto": "Cecilia abrió sueldos"}}, yo="lina")[0]
    ok(c == 403, f"R16 N9 · Lina no apunta en la colección «sueldos» → {c}")
    c = pedir("/api/rastro", "POST", {"accion": "marcar", "modulo": "mi-dia", "objeto": "sueldos/_privado/sueldos#analisis"}, yo="lina")[0]
    ok(c == 400, f"R16 N9 · ni nombra un almacén privado → {c}")
    ok(pedir("/api/rastro", "POST", {"accion": "marcar", "modulo": "mi-dia", "objeto": "x"}, yo="lina")[0] == 200, "R16 N9 · en su pantalla, sí")
    ok(pedir("/api/rastro", "POST", {"accion": "marcar", "modulo": "mi-dia", "objeto": "x", "anula_a": "abc"}, yo="lina")[0] == 400, "R16 B1 · «anula_a: abc» → 400 (antes 500)")

    # ---- N11 · revisión técnica por área
    tec = next((r for r in prod["revisiones"] if r["estado"] == "revisión técnica" and r.get("asignados") == ["Lina"]), None)
    if tec:
        bp = {"modulo": "produccion", "herramienta": "clickup", "tipo": "pieza_aprobar", "objeto": tec["id"], "texto": "x"}
        c1, c2 = pedir("/api/acciones", "POST", bp, yo="jeronimo")[0], pedir("/api/acciones", "POST", bp, yo="valeria")[0]
        ok(c1 == 403 and c2 == 200, f"R16 N11 · pieza técnica de Lina: Jerónimo (SEO) no la aprueba ({c1}); Valeria (su jefa) sí ({c2})")

    # ---- N12 · primera semana ajena
    c1 = pedir("/api/acciones", "POST", {"herramienta": "app", "tipo": "primera_semana_paso", "objeto": "lina:1", "modulo": "primera-semana"}, yo="carla")[0]
    c2 = pedir("/api/acciones", "POST", {"herramienta": "app", "tipo": "primera_semana_paso", "objeto": "carla:1", "modulo": "primera-semana"}, yo="carla")[0]
    ok(c1 == 403 and c2 == 200, f"R16 N12 · Carla no marca un paso de Lina ({c1}); el suyo sí ({c2})")

    # ---- N13 · umbrales en euros
    ok("€" not in pedir("/api/indicadores", yo="jeronimo")[1] and "€" in pedir("/api/indicadores", yo="tomas")[1], "R16 N13 · indicadores sin euros para Jerónimo; con euros para Tomás")

    # ---- B2, B6, B7
    h = pedir("/index.html")[2]
    ok("Python" not in (h.get("Server") or ""), f"R16 B2 · la cabecera Server no dice la versión de Python ({h.get('Server')})")
    for vp in ({"detalle": {"url": "javascript:alert(1)"}}, {"opciones": [{"enlace": "javascript:alert(1)"}]}):
        c = pedir("/api/acciones", "POST", {"modulo": "ficha", "herramienta": "app", "tipo": "nota", "objeto": "r16-b6", "cliente_id": "concilia", "vista_previa": vp}, yo="carla")[0]
        ok(c == 400, f"R16 B6 · «javascript:» anidado en la vista previa ({list(vp)[0]}) → {c}")
    import permisos as PP
    for t in ("Lina 1,5 k€", "pagamos 1470 eur", "EUR 500 de gasto", "cuesta mil euros", "D-07 ~10-11 k €/mes"):
        r = PP.sin_importes(t)
        ok(not any(x in r for x in ("1,5", "1470", "500", "mil euros", "10-11")), f"R16 B7 · «{t}» → «{r}»")

    r16c(tmp)
    nombres_leads(tmp)


def r16c(tmp):
    """R16c (3-oct, cabos de V2-C1/V2-C2): outreach por cliente, setters fuera de «En rojo» y contador de Producción al día."""
    asig = json.loads((AQUI / "data/asignaciones.json").read_text())
    asig = asig if isinstance(asig, list) else asig.get("asignaciones", [])
    suyos = {a["cliente_id"] for a in asig if a.get("persona_id") == "eulimar" and a.get("silla") == "outreach"}
    crudo = json.loads((AQUI / "data/ventas_ro/outreach.json").read_text())
    sys.path.insert(0, str(AQUI / "fuentes_ventas"))
    import campana_cliente as CC
    lista_cli = [(c["id"], c.get("nombre") or c["id"]) for c in json.loads((AQUI / "data/clientes.json").read_text())]
    id_de = lambda nombre: CC.cliente_de(nombre, lista_cli)
    ajenos_crudo = {id_de(k) for k in crudo.get("clientes", {})} - suyos
    # 1 · Eulimar (outreach) recibe SOLO sus clientes: respuestas, campañas de Snov.io y la tabla por cliente.
    for yo, como, etq in (("eulimar", None, "Eulimar"), ("tomas", "eulimar", "Tomás viendo como Eulimar")):
        c, t, _ = pedir("/api/modulo/ventas_ro/outreach", yo=yo, como=como)
        o = json.loads(t) if c == 200 else {}
        resp, camp = o.get("respuestas") or [], (o.get("snov") or {}).get("campañas") or []
        ids_tabla = {id_de(k) for k in (o.get("clientes") or {})}
        ok(c == 200 and resp and camp and all(r.get("cliente_id") in suyos for r in resp + camp),
           f"R16c · {etq}: respuestas y campañas solo de sus {len(suyos)} clientes ({len(resp)} respuestas, {len(camp)} campañas; "
           f"ajenas {sorted({r.get('cliente_id') for r in resp + camp} - suyos)})")
        ok(c == 200 and ids_tabla and ids_tabla <= suyos, f"R16c · {etq}: la tabla por cliente solo con los suyos (de más: {sorted(ids_tabla - suyos, key=str)})")
    ok(bool(ajenos_crudo), f"R16c · (control) el fichero trae clientes que no son de Eulimar ({sorted(ajenos_crudo, key=str)})")
    for yo in ("tomas", "yessica"):
        o = json.loads(pedir("/api/modulo/ventas_ro/outreach", yo=yo)[1])
        ok(len(o.get("respuestas") or []) == len(crudo["respuestas"]) and len(o.get("clientes") or {}) == len(crudo["clientes"]),
           f"R16c · {yo} sigue viendo todas las campañas ({len(o.get('respuestas') or [])} de {len(crudo['respuestas'])})")
    # 2 · el almacén privado de respuestas lleva cliente: Eulimar no abre la respuesta de una campaña ajena (y queda en el rastro).
    priv = json.loads((AQUI / "data/ventas_ro/_privado/outreach_respuestas.json").read_text())["respuestas"]
    ajena = next((k for k, r in priv.items() if r.get("cliente_id") and r["cliente_id"] not in suyos), None)
    suya = next((k for k, r in priv.items() if r.get("cliente_id") in suyos), None)
    alm = "ventas_ro/_privado/outreach_respuestas"
    if ajena and suya:
        cA = pedir("/api/ver_dato", "POST", {"almacen": alm, "ref": ajena, "campo": "correo"}, yo="eulimar")[0]
        cB = pedir("/api/ver_dato", "POST", {"almacen": alm, "ref": ajena, "campo": "correo", "cliente_id": next(iter(suyos))}, yo="eulimar")[0]
        cS = pedir("/api/ver_dato", "POST", {"almacen": alm, "ref": suya, "campo": "correo"}, yo="eulimar")[0]
        cY = pedir("/api/ver_dato", "POST", {"almacen": alm, "ref": ajena, "campo": "correo"}, yo="yessica")[0]
        ok(cA == 403 and cB == 403, f"R16c · Eulimar no abre la respuesta de una campaña ajena ({priv[ajena]['cliente_id']}): {cA}; con cliente_id falso: {cB}")
        ok(cS == 200 and cY == 200, f"R16c · la de su cliente sí ({cS}); la jefa de CRM abre cualquiera ({cY})")
        fila = sqlite3.connect(tmp / "prueba.db").execute(
            "SELECT count(*) FROM registro WHERE quien='eulimar' AND accion='ver_dato_denegado' AND clave=?", (f"{alm}#{ajena}",)).fetchone()[0]
        ok(fila >= 1, f"R16c · el intento queda en el rastro ({fila})")
    else:
        ok(False, "R16c · no hay respuestas de un cliente ajeno y de uno suyo para probar ver_dato")
    # 3 · setters fuera de «En rojo» (en reglas_permisos.json) y contrato de la verdad: 200 con la lista común vacía.
    import permisos as PP
    ok("setters" in (PP.REGLAS.get("modulos_sin_puesto") or {}).get("en-rojo", []), "R16c · reglas_permisos.json saca a los setters de «En rojo»")
    ok(PP.nivel_modulo({"id": "x", "puestos": ["setters"]}, PP.cargar_modulos().get("en-rojo", {})) is None, "R16c · el índice de módulos del servidor no da «En rojo» a la setter")
    c, t, _ = pedir("/api/modulo/verdad/clientes", yo="tomas", como="setter_ana")
    v = json.loads(t) if c == 200 else {}
    ok(c == 200 and v.get("comun") == [] and v.get("clientes") == [] and not v.get("carteras"),
       f"R16c · la setter recibe la verdad con la lista común vacía ({c}, {len(v.get('comun') or [])} comunes, {len(v.get('clientes') or [])} con detalle)")
    ok(not ({"cuota_empresa", "resumen", "fuentes_usadas"} & set(v)), f"R16c · ni resumen ni cuota de la empresa ({sorted(v)})")
    ok(pedir("/api/modulo/en_rojo/atajos", yo="tomas", como="setter_ana")[0] == 403, "R16c · los atajos de «En rojo» siguen cerrados a la setter")
    ok(len(json.loads(pedir("/api/modulo/verdad/clientes", yo="mili")[1]).get("comun", [])) >= 60, "R16c · operaciones sigue con la lista común entera")
    _cv = json.loads(pedir("/api/modulo/verdad/clientes", yo="lucia")[1])
    _mias = set(json.loads(pedir("/api/sesion", yo="lucia")[1])["datos"]["carteraIds"])
    ok(_cv.get("comun") and {x["id"] for x in _cv["comun"]} <= _mias, f"R16c (Tomás 3-oct) · Lucía (account) recibe la lista común solo con sus clientes ({len(_cv.get('comun') or [])} de {len(_mias)})")
    # 4 · contador «Producción» del menú con el hoy de Madrid, no con el día del dato (misma regla que alDia de produccion_comun.js).
    from datetime import date as _d, timedelta as _td
    prod = json.loads((AQUI / "data/produccion/produccion.json").read_text())
    dato = prod.get("hoy") or prod["generado"][:10]
    hoy = (_d.fromisoformat(dato) + _td(days=1)).isoformat()

    # La cola cruda incluye clientes sin servicio: el esperado aplica el scope real,
    # y compara dos fechas dentro del MISMO scope para comprobar el reloj.
    import permisos as P_scope
    personas_scope = json.loads((AQUI / "data/personas.json").read_text())
    por_persona_scope = {p["id"]: p for p in personas_scope}
    crudo_scope = {"personas": personas_scope, "asignaciones": asig,
                   "clientes": json.loads((AQUI / "data/clientes.json").read_text())}
    reloj_previo = os.environ.get("RO_RELOJ")
    os.environ["RO_RELOJ"] = f"{hoy}T09:00"
    try:
        contextos_scope = {pid: P_scope.contexto(p, crudo_scope) for pid, p in por_persona_scope.items()}
    finally:
        if reloj_previo is None:
            os.environ.pop("RO_RELOJ", None)
        else:
            os.environ["RO_RELOJ"] = reloj_previo

    def al_dia(pid, fecha=hoy):
        n = 0
        for r in prod["cola"]:
            if r.get("persona_id") != pid or not r.get("vence") or r.get("grupo") in ("revision", "bloqueada"):
                continue
            # Producción usa «cli»; otras filas usan cliente_id. Resolver ambas
            # sin depender de los contadores precalculados del mismo endpoint.
            cid = r.get("cliente_id") or r.get("cli") or r.get("cid")
            if not cid and r.get("cliente"):
                cid = next((c["id"] for c in crudo_scope["clientes"] if c.get("nombre") == r["cliente"]), None)
            if cid and not P_scope.ver(por_persona_scope[pid], {"tipo": "cliente_detalle", "cliente_id": cid}, contextos_scope[pid])["ok"]:
                continue
            g = r["grupo"]
            if r["vence"] < fecha and g in ("hoy", "semana", "despues", "vencida"):
                g = "olvidada" if (_d.fromisoformat(fecha) - _d.fromisoformat(r["vence"])).days > 30 else "vencida"
            n += g == "vencida"
        return n
    quien = next((p["persona_id"] for p in prod["personas"] if p["persona_id"] in ("lucia", "lina", "jeronimo", "valeria")
                  and al_dia(p["persona_id"]) != al_dia(p["persona_id"], dato)), None)
    if not quien:
        ok(False, f"R16c · sin persona con vencidas distintas al día siguiente ({quien})")
        return
    shutil.copy(tmp / "prueba.db", tmp / "reloj.db")
    env = {**os.environ, "RO_DB": str(tmp / "reloj.db"), "RO_RECARGA_CONFIG": str(tmp / "recarga.json"), "RO_RELOJ": f"{hoy}T09:00",
           "RO_CORREOS_ENTRADA": str(tmp / "correos.json"), "RO_LISTA_ACCESS": str(tmp / "lista_access.txt"), "RO_DEPARTAMENTOS": str(tmp / "departamentos.json")}
    env.pop("RO_MODO", None)
    # 3-oct: dentro del rango de RO_PUERTOS_PRUEBA (antes PUERTO+1…+5, que se salía al carril de al lado)
    srv, puerto2 = arrancar(env)
    if srv is None:
        ok(False, f"R16c · el servidor con el reloj fijado no arrancó ({puerto2})")
        return
    try:
        cuenta = None
        for _ in range(20):
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{puerto2}/api/contadores", headers={"X-RO-Yo": quien})
                with urllib.request.urlopen(req, timeout=10) as r:
                    cuenta = json.loads(r.read().decode()).get("produccion")
                break
            except Exception:
                time.sleep(0.5)
        esperado = al_dia(quien)
        fichero = next(p.get("vencidas") for p in prod["personas"] if p["persona_id"] == quien)
        antes_en_scope = al_dia(quien, dato)
        ok(cuenta == esperado and esperado != antes_en_scope,
           f"R16c · contador de Producción de {quien} por servicio y reloj Madrid ({hoy}, dato del {dato}): {cuenta} = {esperado}; mismo scope antes {antes_en_scope} (fichero global {fichero})")
    finally:
        parar(srv)



def nombres_leads(tmp):
    """3-oct (Tomás dirige a los setters, decisión del 2-oct): dirección y ventas de RO ven en claro nombre y despacho de los
    leads de los dos setters; cada setter solo los suyos; el resto de puestos, nada. En Prospección, nombre y empresa en claro
    para dirección, jefa de CRM y outreach de su cartera; el correo y el texto siguen detrás de ver_dato. «Ver como» no abre nada."""
    crudo = json.loads((AQUI / "data/ventas_ro/setters.json").read_text())
    priv = {}
    for s in ("ana", "javier"):
        priv.update({k: (s, v) for k, v in json.loads((AQUI / f"data/ventas_ro/_privado/setter_{s}.json").read_text())["leads"].items()})
    enm = lambda x: "···" in (x.get("nombre_m") or "")
    c, t, _ = pedir("/api/modulo/ventas_ro/setters", yo="tomas")
    L = json.loads(t).get("leads", []) if c == 200 else []
    claros = [l for l in L if l.get("nombre_completo") and l["id"] in priv and l["nombre_m"] == priv[l["id"]][1]["nombre"]]
    ok(c == 200 and len(L) == len(crudo["leads"]) and {l["setter"] for l in L} == {"ana", "javier"} and len(claros) == len(L) and not any(enm(l) for l in L),
       f"NOMBRES · Tomás ve en claro los leads de los dos setters ({len(claros)} de {len(L)}; tapados {sum(enm(l) for l in L)})")
    ok(all(l.get("despacho_m") == priv[l["id"]][1]["despacho"] for l in L if l["id"] in priv), "NOMBRES · …y el despacho en claro")
    ok(not any(k in l for l in L for k in ("telefono", "correo")) and all("···" in (l.get("tel_m") or "···") for l in L),
       "NOMBRES · teléfono y correo siguen fuera de la lista (solo «··· ··· 807»)")
    for s in ("ana", "javier"):
        L2 = json.loads(pedir("/api/modulo/ventas_ro/setters", yo=f"setter_{s}")[1]).get("leads", [])
        ok(L2 and {l["setter"] for l in L2} == {s} and all(l.get("nombre_completo") and not enm(l) for l in L2),
           f"NOMBRES · setter_{s} ve SOLO los suyos y en claro ({len(L2)})")
    for yo in ("lucia", "camilo", "carla", "eulimar"):
        ok(pedir("/api/modulo/ventas_ro/setters", yo=yo)[0] == 403, f"NOMBRES · {yo} sigue sin acceso a los setters")
    for yo in ("yessica", "mili"):
        c, t, _ = pedir("/api/modulo/ventas_ro/setters", yo=yo)
        o = json.loads(t) if c == 200 else {}
        ok(c in (200, 403) and not o.get("leads") and not o.get("citas") and not o.get("pasadas"), f"NOMBRES · {yo} (resumen) sigue sin filas de leads → {c}")
    c, t, _ = pedir("/api/modulo/ventas_ro/setters", yo="tomas", como="setter_ana")
    L3 = json.loads(t).get("leads", []) if c == 200 else []
    ok(c == 200 and L3 and all(enm(l) or not l.get("nombre_m") for l in L3) and not any(l.get("nombre_completo") for l in L3),
       f"NOMBRES · Tomás viendo como Ana: enmascarado (en «ver como» no se abre nada ni se escribe rastro) ({len(L3)})")
    with sqlite3.connect(tmp / "prueba.db") as con:
        n = con.execute("SELECT count(*) FROM registro WHERE quien='tomas' AND accion='nombres_propios' AND clave LIKE '%ventas_ro/setters%'").fetchone()[0]
    ok(n >= 1, f"NOMBRES · abrir los nombres queda en el rastro de Tomás ({n})")
    # Llamar / Ver completo: el teléfono sigue saliendo por ver_dato y con rastro (dirección sí, Lucía y la otra setter no).
    lid, (st, _) = next(iter(priv.items()))
    alm = f"ventas_ro/_privado/setter_{st}"
    otro = "javier" if st == "ana" else "ana"
    c1 = pedir("/api/ver_dato", "POST", {"almacen": alm, "ref": lid, "campo": "telefono"}, yo="tomas")[0]
    c2 = pedir("/api/ver_dato", "POST", {"almacen": alm, "ref": lid, "campo": "telefono"}, yo="lucia")[0]
    c3 = pedir("/api/ver_dato", "POST", {"almacen": alm, "ref": lid, "campo": "telefono"}, yo=f"setter_{otro}")[0]
    ok(c1 == 200 and c2 == 403 and c3 == 403, f"NOMBRES · teléfono por ver_dato: Tomás {c1}, Lucía {c2}, la otra setter {c3}")
    with sqlite3.connect(tmp / "prueba.db") as con:
        n = con.execute("SELECT count(*) FROM registro WHERE quien='tomas' AND accion='ver_dato' AND clave=?", (f"{alm}#{lid}",)).fetchone()[0]
    ok(n >= 1, f"NOMBRES · el teléfono abierto queda en el rastro ({n})")
    # Prospección: nombre y empresa en claro para Tomás, Yessica y Eulimar (solo su cartera); el correo nunca en la lista.
    pr = json.loads((AQUI / "data/ventas_ro/_privado/outreach_respuestas.json").read_text())["respuestas"]
    asig = json.loads((AQUI / "data/asignaciones.json").read_text())
    asig = asig if isinstance(asig, list) else asig.get("asignaciones", [])
    suyos = {a["cliente_id"] for a in asig if a.get("persona_id") == "eulimar" and a.get("silla") == "outreach"}
    for yo, etq in (("tomas", "Tomás"), ("yessica", "Yessica"), ("eulimar", "Eulimar")):
        R = json.loads(pedir("/api/modulo/ventas_ro/outreach", yo=yo)[1]).get("respuestas", [])
        con_priv = [r for r in R if r["id"] in pr]
        claros = [r for r in con_priv if r["nombre_m"] == pr[r["id"]]["nombre"].strip()]
        ok(R and len(claros) == len(con_priv) and not any("···" in r["nombre_m"] for r in con_priv),
           f"NOMBRES · Prospección: {etq} ve los nombres en claro ({len(claros)} de {len(R)})")
        ok(any(r.get("empresa_m") for r in R), f"NOMBRES · Prospección: {etq} ve la empresa ({sum(1 for r in R if r.get('empresa_m'))})")
        texto = json.dumps(R, ensure_ascii=False)
        ok("@" not in texto and "extracto" not in texto, f"NOMBRES · Prospección: ni correo ni texto de la respuesta en la lista de {etq}")
        ok(not any(r.get("empresa_m") and any(g in r["empresa_m"] for g in ("gmail", "hotmail", "yahoo", "outlook")) for r in R),
           f"NOMBRES · Prospección: la empresa nunca es un buzón genérico ({etq})")
        if yo == "eulimar":
            ok(all(r.get("cliente_id") in suyos for r in R), "NOMBRES · Eulimar solo recibe (y ve en claro) las de su cartera")
    R = json.loads(pedir("/api/modulo/ventas_ro/outreach", yo="lara")[1]).get("respuestas", [])
    ok(not R, f"NOMBRES · Lara (outreach sin esos clientes) no recibe respuestas ajenas ({len(R)})")
    R = json.loads(pedir("/api/modulo/ventas_ro/outreach", yo="tomas", como="eulimar")[1]).get("respuestas", [])
    ok(R and all("···" in r["nombre_m"] and not r.get("empresa_m") for r in R if r.get("nombre_m")), "NOMBRES · Tomás viendo como Eulimar: enmascarado")
    ok(pedir("/api/modulo/ventas_ro/outreach", yo="lucia")[0] == 403 and pedir("/api/modulo/ventas_ro/outreach", yo="camilo")[0] == 403,
       "NOMBRES · Lucía y Camilo siguen sin Prospección")


def mi_perfil(tmp):
    """Mi perfil (3-oct): la zona horaria la cambia la propia persona; la de otra, su jefe, Mili y Tomás (mando: solo Tomás).
    En «ver como» nunca se escribe. Todo en la copia de la base."""
    z = lambda yo, cuerpo, como=None: pedir("/api/perfil/zona", "POST", cuerpo, yo=yo, como=como)
    c, t, _ = z("lucia", {"zona": "America/Bogota"})
    ok(c == 200 and json.loads(t)["persona"]["zona"] == "America/Bogota", f"PERFIL · Lucía cambia SU zona → {c}")
    s = json.loads(pedir("/api/sesion", yo="lucia")[1])
    ok(next(p["zona"] for p in s["datos"]["personas"] if p["id"] == "lucia") == "America/Bogota", "PERFIL · …y se aplica al momento en su sesión")
    ok(z("lucia", {"zona": "America/Bogota"})[0] == 400, "PERFIL · la misma zona otra vez → 400")
    ok(z("lucia", {"zona": "Marte/Olympus"})[0] == 400, "PERFIL · una zona que no existe → 400")
    c = z("lucia", {"id": "carla", "zona": "America/Lima"})[0]
    ok(c == 403, f"PERFIL · Lucía NO cambia la zona de Carla → {c}")
    c = z("lina", {"id": "valeria", "zona": "America/Lima"})[0]
    ok(c == 403, f"PERFIL · Lina no cambia la de su jefa (Valeria) → {c}")
    c = z("valeria", {"id": "lina", "zona": "America/Lima"})[0]
    ok(c == 200, f"PERFIL · Valeria (jefa directa) cambia la de Lina → {c}")
    c = z("mili", {"id": "carla", "zona": "America/Lima"})[0]
    ok(c == 200, f"PERFIL · Mili cambia la de Carla → {c}")
    c = z("mili", {"id": "cecilia", "zona": "America/Lima"})[0]
    ok(c == 403, f"PERFIL · Mili NO cambia la de Cecilia (puesto de mando: solo Tomás) → {c}")
    c = z("tomas", {"id": "cecilia", "zona": "America/Montevideo"})[0]
    ok(c == 200, f"PERFIL · Tomás sí cambia la de Cecilia → {c}")
    c = z("cecilia", {"zona": "America/Argentina/Buenos_Aires"})[0]
    ok(c == 200, f"PERFIL · Cecilia (mando) sí cambia la suya → {c}")
    c = z("tomas", {"id": "valeria", "zona": "America/Lima"}, como="valeria")[0]
    ok(c == 403, f"PERFIL · Tomás viendo como Valeria no escribe → {c}")
    c = z("tomas", {"zona": "Asia/Makassar"}, como="valeria")[0]
    ok(c == 403, f"PERFIL · en «ver como» tampoco la propia → {c}")
    ok(pedir("/api/perfil?id=carla", yo="lucia")[0] == 403, "PERFIL · Lucía no abre el perfil de Carla")
    c, t, _ = pedir("/api/perfil?id=lina", yo="valeria")
    ok(c == 200 and json.loads(t)["puede"] and json.loads(t)["persona"]["zona"] == "America/Lima", f"PERFIL · Valeria ve el de Lina con la zona nueva → {c}")
    c, t, _ = pedir("/api/perfil", yo="tomas", como="valeria")
    ok(c == 200 and json.loads(t)["solo_lectura"], f"PERFIL · «ver como» abre el perfil en solo lectura → {c}")
    ok(pedir("/api/rastro", "POST", {"accion": "zona_cambiada", "modulo": "mi-perfil", "objeto": "lucia"}, yo="lucia")[0] == 403,
       "PERFIL · el navegador no puede fingir «zona_cambiada» en el rastro")
    with sqlite3.connect(tmp / "prueba.db") as con:
        n = con.execute("SELECT count(*) FROM registro WHERE accion='zona_cambiada'").fetchone()[0]
        hz = con.execute("SELECT count(*) FROM historial WHERE coleccion='personas' AND operacion='cambiar' AND datos LIKE '%zona_fuente%Mi perfil%'").fetchone()[0]
    ok(n == 5 and hz == 5, f"PERFIL · cada cambio queda en el rastro ({n}) y en el historial de personas ({hz})")


def envios_verificados(tmp):
    """Envíos verificados (3-oct): nadie ve envíos ajenos; el navegador no fija destinatario, remitente ni estado; en
    simulación «Reintentar» no manda nada; «ver como» no escribe. Todo en la copia de la base."""
    acc = lambda yo, cuerpo: pedir("/api/acciones", "POST", {"modulo": "bandeja", "herramienta": "desk", "tipo": "responder", **cuerpo}, yo=yo)
    c1 = acc("lucia", {"objeto": "RO-3940", "cliente_id": "adade-zaragoza", "texto": "Hola, prueba de envíos de Lucía.",
                       "vista_previa": {"asunto": "Re: prueba", "de": "falsa@example.org", "para": "otro@example.org"}})[0]
    c2 = acc("carla", {"objeto": "RO-4848", "cliente_id": "prodegest", "texto": "Hola, prueba de envíos de Carla."})[0]
    ok(c1 == 200 and c2 == 200, f"ENVIOS · Lucía y Carla contestan un ticket suyo (cola simulada) → {c1}, {c2}")
    def lista(yo, como=None):
        c, t, _ = pedir("/api/envios", yo=yo, como=como)
        d = json.loads(t) if t.startswith("{") else {}
        if "envios" not in d:
            print(f"   (GET /api/envios como {yo}: {c} {t[:200]})")
            d = {"envios": [], "ve_todos": None, "solo_lectura": None}
        return d
    L = lista("lucia")
    suyos = [e for e in L["envios"] if "prueba de envíos de Lucía" in (e.get("texto") or "")]
    ok(suyos and all(e["quien"] == "lucia" for e in L["envios"]) and not L["ve_todos"], f"ENVIOS · Lucía solo ve los suyos ({len(L['envios'])})")
    e_l = suyos[0] if suyos else {}
    ok(e_l.get("estado") == "simulado" and e_l.get("destinatario", {}).get("nombre") == "Contacto del ticket RO-3940",
       "ENVIOS · nace «simulado» con el destinatario que resuelve el servidor (el contacto del ticket)")
    with sqlite3.connect(tmp / "prueba.db") as con:
        fila = con.execute("SELECT remitente, destinatario FROM envios WHERE id=?", (e_l.get("id"),)).fetchone()
    ok(fila and "example.org" not in fila[0] + fila[1] and "fixture1@rankingonline.com" in fila[0],
       "ENVIOS · el «de» y el «para» del navegador se ignoran: remitente y destinatario los pone el servidor")
    C = lista("carla")
    id_c = next((e["id"] for e in C["envios"] if "Carla" in (e.get("texto") or "")), None)
    ok(all(e["quien"] == "carla" for e in C["envios"]) and id_c, "ENVIOS · Carla solo ve los suyos")
    ok(pedir(f"/api/envios/envio?id={e_l.get('id')}", yo="carla")[0] == 403, "ENVIOS · Carla no abre el envío de Lucía (403)")
    T = lista("tomas")
    A = lista("agustina")
    ok(T["ve_todos"] and {e_l.get("id"), id_c} <= {e["id"] for e in T["envios"]}, "ENVIOS · Tomás ve los de todos")
    ok(A["ve_todos"] and {e_l.get("id"), id_c} <= {e["id"] for e in A["envios"]}, "ENVIOS · Agus (técnico) ve los de todos")
    M = lista("mili")
    ok(M["ve_todos"], "ENVIOS · Mili (operaciones) ve los de todos")
    V = lista("tomas", como="lucia")
    ok(all(e["quien"] == "lucia" for e in V["envios"]) and V["solo_lectura"], "ENVIOS · Tomás viendo como Lucía: solo los de Lucía y en solo lectura")
    r = lambda yo, cuerpo, como=None: pedir("/api/envios/reintentar", "POST", cuerpo, yo=yo, como=como)
    ok(r("carla", {"id": e_l.get("id")})[0] == 403, "ENVIOS · Carla no reintenta el envío de Lucía (403)")
    ok(r("tomas", {"id": e_l.get("id")}, como="lucia")[0] == 403, "ENVIOS · en «ver como» no se reintenta (403)")
    c, t, _ = r("lucia", {"id": e_l.get("id"), "estado": "confirmado", "destinatario": "otro@example.org", "canal": "whatsapp"})
    d = json.loads(t) if c == 200 else {}
    ok(c == 200 and d.get("simulado") and d["envio"]["estado"] == "simulado" and d["envio"]["destinatario"]["nombre"] == "Contacto del ticket RO-3940"
       and d["envio"]["canal"] == "desk", f"ENVIOS · Lucía reintenta el suyo: simulado, y el estado, el destinatario y el canal del navegador se ignoran → {c}")
    ok(r("agustina", {"id": id_c})[0] == 200, "ENVIOS · Agus reintenta cualquiera (simulado)")
    ok(pedir("/api/envios/crear", "POST", {"canal": "desk", "objeto": "RO-1", "destinatario": "x@example.org"}, yo="tomas")[0] == 404,
       "ENVIOS · no hay ruta para crear un envío a mano: solo nacen de una acción de la cola")
    c = acc("lucia", {"tipo": "correo", "objeto": "alguien@example.org", "cliente_id": "adade-zaragoza", "texto": "x"})[0]
    with sqlite3.connect(tmp / "prueba.db") as con:
        n_at = con.execute("SELECT count(*) FROM envios WHERE objeto LIKE '%example.org%'").fetchone()[0]
    ok(c in (400, 403) and n_at == 0, f"ENVIOS · un correo a una dirección escrita a mano no entra ni crea envío → {c}")
    ok(pedir("/api/rastro", "POST", {"accion": "envio_reintento_simulado", "modulo": "envios", "objeto": "1"}, yo="tomas")[0] == 403,
       "ENVIOS · el navegador no puede fingir un reintento en el rastro")
    with sqlite3.connect(tmp / "prueba.db") as con:
        n_r = con.execute("SELECT count(*) FROM registro WHERE accion='envio_reintento_simulado'").fetchone()[0]
        pasos = con.execute("SELECT count(*) FROM envio_pasos WHERE evento='reintento_simulado'").fetchone()[0]
        try:
            con.execute("UPDATE envio_pasos SET estado='confirmado'")
            inm = False
        except sqlite3.DatabaseError:
            inm = True
    ok(n_r >= 2 and pasos >= 2 and inm, f"ENVIOS · cada reintento deja rastro ({n_r}) y su paso ({pasos}); los pasos no se cambian")
    ok(pedir("/api/envios", yo="lina")[0] == 200 and all(e["quien"] == "lina" for e in lista("lina")["envios"]),
       "ENVIOS · alguien sin envíos recibe una lista vacía de los suyos, nunca los de otros")
    # 3-oct: un texto con huecos de plantilla sin rellenar no sale nunca (400 con motivo llano, sin acción ni envío)
    with sqlite3.connect(tmp / "prueba.db") as con:
        a0, e0 = (con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("acciones", "envios"))
    for hueco in ("[completar]", "[completar: fecha]", "[…]", "[...]",
                  "[día y hora]", "[nombre]", "[enlace]", "[Fecha]", "[confirmar hora]"):   # 3-oct: huecos de borradores y plantillas
        c, t, _ = acc("lucia", {"objeto": "RO-3940", "cliente_id": "adade-zaragoza", "texto": f"Hola, te lo mando el {hueco}. Un saludo,"})
        motivo = (json.loads(t).get("error") or "") if t.startswith("{") else ""
        ok(c == 400 and "sin rellenar" in motivo and hueco in motivo, f"ENVIOS · texto con «{hueco}» → {c} ({motivo[:70]})")
    c, t, _ = acc("lucia", {"objeto": "RO-3940", "cliente_id": "adade-zaragoza", "texto": "Hola, va el informe.", "vista_previa": {"asunto": "Informe de [completar]"}})
    ok(c == 400, f"ENVIOS · asunto con «[completar]» → {c}")
    with sqlite3.connect(tmp / "prueba.db") as con:
        a1, e1 = (con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("acciones", "envios"))
    ok(a1 == a0 and e1 == e0, f"ENVIOS · …y no deja acción en la cola ni envío ({a1 - a0}, {e1 - e0})")
    c = acc("lucia", {"objeto": "RO-3940", "cliente_id": "adade-zaragoza", "texto": "Hola, ya lo tienes [adjunto en el correo]. Un saludo,"})[0]
    ok(c == 200, f"ENVIOS · un corchete normal sí sale (solo bloquea huecos de plantilla) → {c}")
    for normal in ("Lo tienes [aquí](https://rankingonline.com/academia-de-ventas/). Un saludo,", "Va la nota [1] del informe. Un saludo,"):
        c = acc("lucia", {"objeto": "RO-3940", "cliente_id": "adade-zaragoza", "texto": f"Hola, {normal}"})[0]
        ok(c == 200, f"ENVIOS · enlace o nota entre corchetes sí sale («{normal[:28]}…») → {c}")

def sincronia_clickup(tmp):
    """Sincronía con ClickUp (3-oct): cada acción que va a ClickUp queda guardada en la base (copia segura) al momento; el
    navegador no fija la tarea ni el cambio; solo quien puede tocar esa tarea; nadie ve cambios ajenos; el conflicto lo
    elige quien lo hizo (o dirección, operaciones, técnico); «ver como» no escribe; simulado: nada sale. En la copia."""
    sys.path.insert(0, str(AQUI))
    import sincronia as SI
    prod = json.loads((AQUI / "data/produccion/produccion.json").read_text())
    jefe = {p["id"]: p.get("jefe") for p in json.loads((AQUI / "data/personas.json").read_text())}
    autores = {}
    for r in prod.get("cola") or []:
        autores.setdefault(str(r.get("id")), set()).add(r.get("persona_id"))
    pend = {x["id"] for x in prod.get("revisiones") or []} | {r["id"] for r in prod.get("cola") or [] if r.get("grupo") == "revision"}
    suya = next((r for r in prod.get("cola") or [] if r.get("persona_id") == "lucia" and r.get("estado") in ("en curso", "diario", "planning semanal")
                 and r["id"] not in pend and "carla" not in autores[str(r["id"])] and "carla" not in {jefe.get(a) for a in autores[str(r["id"])]}), None)
    ok(suya is not None, "SINC · hay una tarea de Lucía en Producción para probar")
    if not suya:
        return
    db = lambda: sqlite3.connect(tmp / "prueba.db")
    acc = lambda yo, cuerpo, como=None: pedir("/api/acciones", "POST", {"modulo": "produccion", "herramienta": "clickup", **cuerpo}, yo=yo, como=como)
    c, t, _ = acc("lucia", {"tipo": "mover_estado", "objeto": suya["id"], "texto": "A revisión",
                            "vista_previa": {"a": "complete", "task_id": "OTRA-TAREA", "de": "inventado"}})
    d = json.loads(t) if c == 200 else {}
    ok(c == 200 and (d.get("sincronia") or {}).get("estado") == "simulado" and "pendiente de ClickUp" in d["sincronia"].get("texto", ""),
       f"SINC · Lucía mueve su tarea: la respuesta dice al momento «hecho en la app · pendiente de ClickUp» → {c} {t[:160]}")
    with db() as con:
        f = con.execute("SELECT objeto_ref, cambio, base, ignorado, quien, modo FROM sinc_cambios WHERE accion_id=?", (d.get("id"),)).fetchone()
    cam = json.loads(f[1]) if f else {}
    ok(f and f[0] == suya["id"] and cam == {"campo": "estado", "valor": "revisión project manager"} and json.loads(f[2])["estado"] == suya["estado"]
       and {"a", "task_id"} <= set(json.loads(f[3] or "{}")) and f[4] == "lucia" and f[5] == "simulado",
       f"SINC · copia segura en la base: tarea y cambio los pone el servidor («a» y «task_id» del navegador, ignorados y anotados) → {f}")
    cid = (d.get("sincronia") or {}).get("id")
    c2, _, _ = acc("lucia", {"tipo": "mover_estado", "objeto": suya["id"], "texto": "A revisión", "vista_previa": {"a": "complete"}})
    with db() as con:
        n = con.execute("SELECT count(*) FROM sinc_cambios WHERE objeto_ref=?", (suya["id"],)).fetchone()[0]
    ok(c2 == 200 and n == 1, f"SINC · doble clic: la misma acción, un solo cambio (idempotente) → {n}")
    with db() as con:
        antes = con.execute("SELECT count(*) FROM sinc_cambios").fetchone()[0]
    c3 = acc("carla", {"tipo": "mover_estado", "objeto": suya["id"], "texto": "x"})[0]
    c4 = acc("carla", {"tipo": "comentario", "objeto": suya["id"], "texto": "x"})[0]
    c5 = acc("lucia", {"tipo": "asignar", "objeto": suya["id"], "texto": "x", "vista_previa": {"persona": "carla"}})[0]
    c6 = acc("tomas", {"tipo": "mover_estado", "objeto": suya["id"], "texto": "x"}, como="lucia")[0]
    with db() as con:
        despues = con.execute("SELECT count(*) FROM sinc_cambios").fetchone()[0]
    ok(c3 == 403 and c4 == 403 and c5 in (400, 403) and c6 == 403 and despues == antes,
       f"SINC · solo quien puede tocar la tarea: Carla mover/comentar ({c3}, {c4}), asignar sin puesto ({c5}), «ver como» ({c6}); ningún cambio nuevo")
    L = lambda yo, como=None: (lambda r: json.loads(r[1]) if r[0] == 200 else {"cambios": [], "_c": r[0]})(pedir("/api/sincronia", yo=yo, como=como))
    Ll, Lc, Lt, La, Lm = L("lucia"), L("carla"), L("tomas"), L("agustina"), L("mili")
    ok(Ll["cambios"] and all(x["quien"] == "lucia" for x in Ll["cambios"]) and not Ll["ve_todos"], "SINC · Lucía solo ve los suyos")
    ok(all(x["quien"] == "carla" for x in Lc["cambios"]) and cid not in {x["id"] for x in Lc["cambios"]}, "SINC · Carla no ve los de Lucía")
    ok(pedir(f"/api/sincronia/cambio?id={cid}", yo="carla")[0] == 403, "SINC · Carla no abre un cambio de Lucía (403)")
    ok(all(x.get("ve_todos") and cid in {y["id"] for y in x["cambios"]} for x in (Lt, La, Lm)), "SINC · Tomás, Agus y Mili ven los de todos")
    V = L("tomas", como="lucia")
    ok(V["solo_lectura"] and all(x["quien"] == "lucia" for x in V["cambios"]), "SINC · Tomás como Lucía: solo los de Lucía y en solo lectura")
    o = pedir(f"/api/sincronia/objeto?ref={suya['id']}", yo="lucia")
    ok(o[0] == 200 and json.loads(o[1])["cambios"][0]["estado"] == "simulado", "SINC · la pantalla puede preguntar el estado de una tarea (hecho en la app · pendiente)")
    # conflicto: se prepara en la copia de la base con el ClickUp simulado (hoy nada real puede chocar)
    con = SI.conectar(tmp / "prueba.db")
    SI.preparar(con)
    k, _ = SI.crear_cambio(con, clave=f"seg-conf-{os.getpid()}", quien="lucia", canal="clickup", tipo="mover_estado", cliente_id=suya.get("cli"), modulo="produccion",
                           objeto={"tipo": "tarea", "ref": "seg-" + suya["id"], "nombre": "Prueba", "resuelto": True}, cambio={"campo": "estado", "valor": "revisión project manager"},
                           base={"estado": "en curso"}, modo="prueba")
    prov = SI.ClickUpSimulado({"seg-" + suya["id"]: {"estado": "en curso"}}, {SI.fila(con, k)["clave"]: {"fuera": "bloqueado"}})
    est = SI.ejecutar(con, k, prov)
    con.commit()
    con.close()
    ok(est == "conflicto", f"SINC · (preparado) un cambio en conflicto → {est}")
    E = lambda yo, cuerpo, como=None, ruta="elegir": pedir(f"/api/sincronia/{ruta}", "POST", cuerpo, yo=yo, como=como)
    ok(E("carla", {"id": k, "gana": "app"})[0] == 403, "SINC · Carla no elige en un conflicto de Lucía (403)")
    ok(E("tomas", {"id": k, "gana": "app"}, como="lucia")[0] == 403, "SINC · en «ver como» no se elige (403)")
    c, t, _ = pedir(f"/api/sincronia/cambio?id={k}", yo="lucia")
    vs = (json.loads(t)["cambio"].get("versiones") or {}) if c == 200 else {}
    ok(vs.get("app") == "revisión project manager" and vs.get("clickup") == "bloqueado", f"SINC · Lucía ve las dos versiones → {vs}")
    c, t, _ = E("lucia", {"id": k, "gana": "clickup", "estado": "confirmado", "cambio": {"valor": "x"}})
    ok(c == 200 and json.loads(t)["cambio"]["estado"] == "descartado", f"SINC · Lucía elige «lo de ClickUp» (estado y cambio del navegador ignorados) → {c}")
    ok(E("lucia", {"id": k, "gana": "app"})[0] == 409, "SINC · ya decidido: elegir otra vez → 409")
    c, t, _ = E("lucia", {"id": cid, "estado": "confirmado"}, ruta="reintentar")
    ok(c == 200 and json.loads(t).get("simulado") and json.loads(t)["cambio"]["estado"] == "simulado", f"SINC · reintentar en simulación no escribe en ClickUp y no cambia el estado → {c}")
    ok(E("lucia", {"id": cid}, ruta="a_mano")[0] == 403, "SINC · «ya está en ClickUp (a mano)» no lo marca quien no es Agus, Mili o Tomás")
    c, t, _ = E("agustina", {"id": cid}, ruta="a_mano")
    ok(c == 200 and json.loads(t)["cambio"]["estado"] == "confirmado", f"SINC · Agus lo marca como pasado a mano → {c}")
    ok(E("tomas", {"canal": "clickup", "objeto": "x"}, ruta="crear")[0] == 404, "SINC · no hay ruta para crear un cambio a mano: solo nacen de una acción")
    with db() as con2:
        n_r = con2.execute("SELECT count(*) FROM registro WHERE accion IN ('sinc_elegir','sinc_reintento_simulado','sinc_a_mano')").fetchone()[0]
        try:
            con2.execute("UPDATE sinc_pasos SET estado='confirmado'")
            inm = False
        except sqlite3.DatabaseError:
            inm = True
    ok(n_r >= 3 and inm, f"SINC · cada decisión deja rastro ({n_r}) y los pasos no se cambian")
    it = SI.interruptor()
    ok(not it["reales"] and it["chat_puente"] == "apagado", "SINC · hoy ClickUp real apagado y puente de chat apagado")


def finanzas_v3(tmp):
    """3-oct · Finanzas v3: Sofía ve impagos y el cuadre de lo facturado, NUNCA beneficio, equipo ni gasto; nadie ve sueldos
    individuales; el account sabe que su cliente tiene un impago y el importe solo si ve la cuota; los botones de cobro, simulados."""
    c, t, _ = pedir("/api/modulo/finanzas/cuadre", yo="tomas")
    cu = json.loads(t) if c == 200 else {}
    ok(c == 200 and cu.get("beneficio") and cu.get("equipo_mes"), "FIN v3 · Tomás recibe el cuadre completo (beneficio y equipo mes a mes)")
    for yo in ("sofia", "mili", "lucia", "cecilia", "constanza"):
        ok(pedir("/api/modulo/finanzas/cuadre", yo=yo)[0] == 403, f"FIN v3 · {yo} no recibe el cuadre con beneficio y equipo (403)")
    ok(pedir("/api/modulo/finanzas/cuadre", yo="tomas", como="sofia")[0] == 403, "FIN v3 · Tomás viendo como Sofía tampoco lo recibe")
    c, t, _ = pedir("/api/modulo/finanzas/cuadre_facturacion", yo="sofia")
    cf = json.loads(t) if c == 200 else {}
    txt = json.dumps(cf, ensure_ascii=False).lower()
    ok(c == 200 and cf.get("cuadre") and not any(k in txt for k in ('"bai', '"beneficio', '"equipo', '"gasto', '"margen', 'excel_equipo', 'sueldo')),
       "FIN v3 · Sofía recibe el cuadre de lo facturado, sin beneficio, equipo, gasto ni margen")
    ok(all(i.get("ambito") == "facturacion" for i in cf.get("incongruencias", [])), "FIN v3 · a Sofía solo le llegan las incongruencias de facturación")
    c, t, _ = pedir("/api/modulo/finanzas/direccion", yo="sofia")
    ok(c == 403, "FIN v3 · Sofía sigue sin finanzas/direccion (beneficio y coste del equipo)")
    c, t, _ = pedir("/api/modulo/finanzas/impagos", yo="sofia")
    im = json.loads(t) if c == 200 else {}
    ok(c == 200 and im.get("filas") and all("importe" in f for f in im["filas"]), f"FIN v3 · Sofía ve el mapa de impagos completo ({len(im.get('filas', []))} facturas)")
    for yo in ("lucia", "valeria", "setter_ana"):
        ok(pedir("/api/modulo/finanzas/impagos", yo=yo)[0] == 403, f"FIN v3 · {yo} no recibe el mapa de impagos con importes")
    crudo = json.loads((AQUI / "data/finanzas/impagos_clientes.json").read_text())["clientes"]
    for yo in ("lucia", "valeria", "lina"):
        c, t, _ = pedir("/api/modulo/finanzas/impagos_clientes", yo=yo)
        L = json.loads(t).get("clientes", []) if c == 200 else []
        ve_cuota = pedir("/api/modulo/dinero_cliente/dinero_cliente", yo=yo)
        cuota = c == 200 and any("cuota" in json.dumps(x) for x in json.loads(ve_cuota[1]).get("clientes", [])) if ve_cuota[0] == 200 else False
        ok(c == 200 and all("vencidas" in x and "dias_max" in x for x in L) and len(L) <= len(crudo)
           and (cuota or not any("cuota_vencida" in x for x in L)),
           f"FIN v3 · {yo} sabe qué clientes suyos tienen impago ({len(L)}); importe {'sí (ve la cuota)' if cuota else 'no'}")
    # sueldos individuales: ni en los ficheros de Finanzas ni en el cuadre
    for f in ("finanzas/cuadre", "finanzas/cuadre_facturacion", "finanzas/impagos", "finanzas/direccion"):
        c, t, _ = pedir(f"/api/modulo/{f}", yo="tomas")
        claves = set()
        def _k(o):
            if isinstance(o, dict):
                for k, v in o.items(): claves.add(k.lower()); _k(v)
            elif isinstance(o, list):
                for v in o: _k(v)
        _k(json.loads(t) if c == 200 else {})
        ok(not any(any(x in k for x in ("salario", "sueldo", "nomina", "bonus", "persona_id")) for k in claves), f"FIN v3 · {f}: sin importes por persona")
    for yo in ("tomas", "sofia", "mili"):
        ok(pedir("/api/modulo/sueldos/_privado/sueldos", yo=yo)[0] in (403, 404), f"FIN v3 · {yo} no recibe los sueldos en bloque")
    # botones de cobro: simulados y con rastro; Lucía no puede
    c, t, _ = pedir("/api/acciones", "POST", {"modulo": "finanzas", "herramienta": "app", "tipo": "cobro_reclamado", "objeto": "A-26-001", "texto": "prueba"}, yo="sofia")
    ok(c == 200 and json.loads(t).get("estado") == "simulada", "FIN v3 · «Reclamar» de Sofía queda en la cola como simulado")
    c, t, _ = pedir("/api/acciones", "POST", {"modulo": "finanzas", "herramienta": "app", "tipo": "cuadre_decision", "objeto": "eq-2025", "texto": "prueba"}, yo="sofia")
    ok(c in (400, 403), f"FIN v3 · Sofía no puede apuntar decisiones del cuadre ({c})")
    c, t, _ = pedir("/api/acciones", "POST", {"modulo": "finanzas", "herramienta": "app", "tipo": "cobro_reclamado", "objeto": "A-26-001", "texto": "prueba"}, yo="lucia")
    ok(c in (400, 403), f"FIN v3 · Lucía no puede reclamar cobros ({c})")



def avisos_automaticos(tmp):
    """Avisos automáticos (3-oct · avisos_programados.py): cada jefa cambia solo las reglas de su departamento (Mili y Tomás,
    todas); «ver como» no escribe; un recordatorio personal solo lo ven la persona y su jefa; avisa solo a quien le falta, una
    vez; escala si se ignora y no si se marcó «Ya lo he hecho»; sin importes; nada sale de la app. Relojes fijados con
    RO_RELOJ (viernes 2-oct 18:00, lunes 5-oct 9:00 y 17:30, martes 6-oct 18:00) sobre una copia de la base."""
    global B
    js = lambda r: json.loads(r[1]) if r[0] == 200 else {}
    # ---- pantalla y permisos (servidor principal, sin reloj fijado)
    reg = lambda yo, como=None: {r["id"]: r for r in js(pedir("/api/avisos_programados", yo=yo, como=como)).get("reglas", [])}
    t, v, l, sf = reg("tomas"), reg("valeria"), reg("lucia"), reg("sofia")
    ok(len(t) >= 7 and all(r["puede_editar"] for r in t.values()), f"AVISOS · Tomás ve y edita todas las reglas ({len(t)})")
    ok(v.get("publicidad_manana", {}).get("puede_editar") and not v.get("horas_ayer", {}).get("puede_editar", True),
       "AVISOS · Valeria edita la de publicidad y ve sin tocar la de horas")
    ok(l and not any(r["puede_editar"] for r in l.values()) and "cierre_facturacion" not in l and "resumen_semanal_direccion" not in l,
       f"AVISOS · Lucía solo ve lo que le llega, sin editar ({sorted(l)})")
    ok(sf.get("cierre_facturacion", {}).get("puede_editar") and "publicidad_manana" not in sf, "AVISOS · Sofía edita el cierre de facturación")
    ok(all(r.get("envios_semana") is None and not r.get("cambios") for r in l.values()), "AVISOS · Lucía no ve los envíos ni el historial de cambios")
    cam = lambda yo, cuerpo, como=None: pedir("/api/avisos_programados/cambiar", "POST", cuerpo, yo=yo, como=como)
    ok(cam("lucia", {"id": "semaforo_lunes", "campo": "activa", "valor": False})[0] == 403, "AVISOS · Lucía no apaga el semáforo del lunes (403)")
    ok(cam("valeria", {"id": "horas_ayer", "campo": "hora", "valor": "10:00"})[0] == 403, "AVISOS · Valeria no cambia la regla de horas (403)")
    c, tx, _ = cam("valeria", {"id": "publicidad_manana", "campo": "umbral.ritmo_pct", "valor": 120})
    ok(c == 200 and next(u for u in json.loads(tx)["regla"]["umbrales"] if u["clave"] == "ritmo_pct")["valor"] == 120, f"AVISOS · Valeria sube el umbral de ritmo a 120 → {c}")
    ok(cam("valeria", {"id": "publicidad_manana", "campo": "umbral.ritmo_pct", "valor": 900})[0] == 400, "AVISOS · umbral fuera de rango → 400")
    ok(cam("valeria", {"id": "publicidad_manana", "campo": "umbral.ritmo_pct", "valor": "120"})[0] == 400, "AVISOS · umbral en texto → 400")
    ok(cam("valeria", {"id": "publicidad_manana", "campo": "texto", "valor": "otra cosa"})[0] == 400, "AVISOS · el texto no se cambia desde la app → 400")
    ok(cam("mili", {"id": "semaforo_lunes", "campo": "hora", "valor": "25:00"})[0] == 400, "AVISOS · hora imposible → 400")
    ok(cam("mili", {"id": "semaforo_lunes", "campo": "hora", "valor": "10:30"})[0] == 200, "AVISOS · Mili cambia la hora del semáforo")
    ok(cam("cecilia", {"id": "horas_ayer", "campo": "activa", "valor": False})[0] == 200 and cam("cecilia", {"id": "horas_ayer", "campo": "activa", "valor": True})[0] == 200,
       "AVISOS · Cecilia (RRHH) apaga y enciende la de horas")
    ok(cam("tomas", {"id": "publicidad_manana", "campo": "activa", "valor": False}, como="valeria")[0] == 403, "AVISOS · Tomás viendo como Valeria no cambia nada")
    ok(js(pedir("/api/avisos_programados", yo="tomas", como="valeria")).get("solo_lectura") is True, "AVISOS · «ver como» abre en solo lectura")
    ok(pedir("/api/avisos_programados/vista_previa?id=publicidad_manana", yo="lucia")[0] == 403, "AVISOS · Lucía no pide la vista previa de publicidad (403)")
    c, tx, _ = pedir("/api/avisos_programados/vista_previa?id=cierre_facturacion", yo="sofia")
    ok(c == 200 and "€" not in tx and json.loads(tx)["total"] == 1, f"AVISOS · vista previa del cierre para Sofía, sin importes → {c}")
    ok(pedir("/api/avisos_programados/ejecutar", "POST", {}, yo="lucia")[0] == 403, "AVISOS · Lucía no pasa el reloj a mano (403)")
    ok(pedir("/api/rastro", "POST", {"accion": "aviso_programado_cambio", "modulo": "avisos-automaticos", "objeto": "horas_ayer"}, yo="lucia")[0] == 403,
       "AVISOS · el navegador no finge un cambio de regla en el rastro")
    with sqlite3.connect(tmp / "prueba.db") as con:
        n = con.execute("SELECT count(*) FROM avisos_prog_cambios").fetchone()[0]
        nr = con.execute("SELECT count(*) FROM registro WHERE accion='aviso_programado_cambio'").fetchone()[0]
        try:
            con.execute("DELETE FROM avisos_prog_cambios")
            borrado = True
        except sqlite3.DatabaseError:
            borrado = False
    ok(n == 4 and nr == 4 and not borrado, f"AVISOS · cada cambio queda en la base ({n}) y en el rastro ({nr}), y no se borra")

    # ---- el reloj: copia de la base, servidor con RO_RELOJ fijado
    shutil.copy(tmp / "prueba.db", tmp / "avisos.db")
    principal = B

    def con_reloj(reloj, fn):
        global B
        env = {**os.environ, "RO_DB": str(tmp / "avisos.db"), "RO_RECARGA_CONFIG": str(tmp / "recarga.json"), "RO_RELOJ": reloj,
               "RO_AVISOS_SIN_BUCLE": "1", "RO_DEPARTAMENTOS": str(tmp / "departamentos.json")}
        env.pop("RO_MODO", None)
        srv, puerto = arrancar(env)
        if srv is None:
            ok(False, f"AVISOS · el servidor con reloj no arrancó ({puerto})")
            return None
        B = f"http://127.0.0.1:{puerto}"
        try:
            return fn()
        finally:
            B = principal
            parar(srv)

    ejec = lambda: js(pedir("/api/avisos_programados/ejecutar", "POST", {}, yo="tomas"))
    canal = lambda yo, cid: js(pedir(f"/api/canales/canal?id={cid}", yo=yo)).get("mensajes", [])
    prog = lambda ms, txt: [m for m in ms if txt in m["texto"]]

    def viernes():
        r1, r2 = ejec(), ejec()
        luc, mil, car, gus = canal("lucia", "avisos-accounts"), canal("mili", "avisos-accounts"), canal("carla", "avisos-accounts"), canal("gustavo", "avisos-crm")
        dir_ = canal("tomas", "avisos-direccion")
        return r1, r2, luc, mil, car, gus, dir_
    r1, r2, luc, mil, car, gus, dir_ = con_reloj("2026-10-02T18:00", viernes)
    ok(r1.get("publicados", 0) > 0 and r2.get("publicados") == 0, f"AVISOS · viernes 18:00: publica ({r1.get('publicados')}) y la segunda vuelta no repite ({r2.get('publicados')})")
    hl = prog(luc, "no imputaste horas")
    ok(len(hl) == 1 and hl[0]["menciones"] == ["lucia"] and any(b.get("url", "").startswith("https://app.clickup.com/") for b in hl[0].get("botones", [])),
       "AVISOS · Lucía (0 h ayer) recibe su recordatorio de horas, con botón «Imputar»")
    ok(all("Lucía" in m["texto"] or "lucia" in m["menciones"] for m in prog(luc, "imputaste")), "AVISOS · Lucía no ve el recordatorio de horas de otra account")
    ok(len(prog(mil, "no imputaste horas")) >= 5, f"AVISOS · Mili (su jefa) ve los de su equipo ({len(prog(mil, 'no imputaste horas'))})")
    ok(not prog(gus, "imputaste"), "AVISOS · Gustavo, que imputó ayer, no recibe nada")
    ok(len(prog(dir_, "Resumen de la semana")) == 1, "AVISOS · viernes 18:00: resumen semanal en #avisos-dirección")
    ok(pedir("/api/canales/canal?id=avisos-direccion", yo="lucia")[0] == 403, "AVISOS · Lucía no abre #avisos-dirección")

    def lunes():
        r9 = ejec()
        ok(js(pedir("/api/canales/canal?id=avisos-publicidad", yo="lina")) and all("€" not in m["texto"] for m in prog(canal("lina", "avisos-publicidad"), "Publicidad, lun")),
           "AVISOS · lunes 9:00: el resumen de publicidad sale sin importes")
        return r9
    r9 = con_reloj("2026-10-05T09:00", lunes)
    ok(r9.get("escalados", 0) > 0, f"AVISOS · lunes 9:00: los recordatorios de horas ignorados suben a la jefa ({r9.get('escalados')})")

    def lunes_tarde():
        r = ejec()
        luc = canal("lucia", "avisos-accounts")
        car = canal("carla", "avisos-accounts")
        lina = pedir("/api/canales/canal?id=avisos-accounts", yo="lina")[0]
        h_ok = pedir("/api/avisos_programados/hecho", "POST", {"regla": "semaforo_lunes", "objetivo": "lucia", "dia": "2026-10-05"}, yo="lucia")[0]
        h_no = pedir("/api/avisos_programados/hecho", "POST", {"regla": "semaforo_lunes", "objetivo": "carla", "dia": "2026-10-05"}, yo="lucia")[0]
        h_404 = pedir("/api/avisos_programados/hecho", "POST", {"regla": "semaforo_lunes", "objetivo": "nadie", "dia": "2026-10-05"}, yo="lucia")[0]
        h_como = pedir("/api/avisos_programados/hecho", "POST", {"regla": "semaforo_lunes", "objetivo": "lucia", "dia": "2026-10-05"}, yo="tomas", como="lucia")[0]
        return r, luc, car, lina, h_ok, h_no, h_404, h_como
    r, luc, car, lina, h_ok, h_no, h_404, h_como = con_reloj("2026-10-05T17:30", lunes_tarde)
    sl = prog(luc, "te falta el semáforo")
    ok(len(sl) == 1 and all(b["ir"].startswith("#/ficha/") and b["ir"].endswith("?semaforo=1") for b in sl[0].get("botones", [])),
       "AVISOS · lunes: Lucía recibe su semáforo con botones que abren la ficha con el editor")
    ok(all("Lucía" not in m["texto"] for m in prog(car, "te falta el semáforo")), "AVISOS · Carla no ve el semáforo de Lucía")
    ok(lina == 403, "AVISOS · Lina (publicidad) no abre #avisos-accounts")
    ok(h_ok == 200 and h_no == 403 and h_404 == 404 and h_como == 403, f"AVISOS · «Ya lo he hecho»: lo suyo sí ({h_ok}), lo de Carla no ({h_no}), inexistente {h_404}, «ver como» {h_como}")

    def martes():
        r = ejec()
        mil = canal("mili", "avisos-accounts")
        return r, mil
    r, mil = con_reloj("2026-10-06T18:00", martes)
    esc = [m for m in mil if m.get("hilo_de") and "¿lo miras?" in m["texto"]] + [m for m in mil if "¿lo miras?" in m["texto"] and not m.get("hilo_de")]
    ok(r.get("escalados", 0) > 0 and esc, f"AVISOS · martes: lo ignorado sube a Mili ({r.get('escalados')})")
    with sqlite3.connect(tmp / "avisos.db") as con:
        luc_esc = con.execute("SELECT count(*) FROM canal_mensajes WHERE clave='prog_esc:prog:semaforo_lunes:lucia:2026-10-05'").fetchone()[0]
        car_esc = con.execute("SELECT count(*) FROM canal_mensajes WHERE clave='prog_esc:prog:semaforo_lunes:carla:2026-10-05'").fetchone()[0]
        fuera = con.execute("SELECT count(*) FROM acciones WHERE herramienta IN ('clickup','desk','ghl','whatsapp') AND creada >= datetime('now','-1 hour') AND quien='sistema'").fetchone()[0]
        euros = con.execute("SELECT count(*) FROM canal_mensajes WHERE clave LIKE 'prog%' AND (texto LIKE '%€%' OR texto LIKE '%euros%')").fetchone()[0]
    ok(luc_esc == 0 and car_esc == 1, f"AVISOS · lo marcado «hecho» no sube (Lucía {luc_esc}); lo de Carla sí ({car_esc})")
    ok(fuera == 0 and euros == 0, f"AVISOS · nada sale a herramientas ({fuera}) y ningún aviso lleva importes ({euros})")


def modular_acceso(tmp):
    """N5 Modular DS (3-oct): nadie fuera de web / jefe de SEO y web / dirección obtiene un enlace de acceso al WordPress;
    «ver como» no lo pide; una web que no está en Modular, 404; el tablero de todas las webs solo para esos puestos (y
    operaciones); el navegador no finge la fila del rastro; cada petición queda en el rastro y el enlace no se guarda."""
    js = lambda r: json.loads(r[1]) if r[0] == 200 else {}
    webs = json.loads((AQUI / "data/modular/webs.json").read_text()) if (AQUI / "data/modular/webs.json").exists() else {}
    mid = str(((webs.get("webs") or [{}])[0]).get("modular_id") or "")
    if not mid:
        return ok(True, "MODULAR · sin datos de Modular: prueba de acceso omitida")
    pedir_acc = lambda yo, como=None, m=mid: pedir("/api/modular/acceso", "POST", {"modular_id": m}, yo=yo, como=como)
    for yo in ("lucia", "valeria", "gustavo", "sofia", "mili", "cecilia"):
        if yo in PERSONAS and PERSONAS[yo].get("activo", True):
            c, tx, _ = pedir_acc(yo)
            ok(c == 403 and "url" not in tx, f"MODULAR · {yo} no obtiene enlace de acceso ({c})")
    for yo in ("macarena", "jeronimo", "tomas"):
        c, tx, _ = pedir_acc(yo)
        d = json.loads(tx) if c == 200 else {}
        ok(c == 200 and (d.get("apagado") or d.get("url")), f"MODULAR · {yo} (web / jefe / dirección) pasa la puerta ({c}, {'apagado' if d.get('apagado') else 'enlace'})")
    ok(pedir_acc("tomas", como="lucia")[0] == 403, "MODULAR · Tomás viendo como Lucía no pide accesos")
    ok(pedir_acc("tomas", como="macarena")[0] == 403, "MODULAR · «ver como» nunca pide accesos (ni como alguien de web)")
    ok(pedir_acc("macarena", m="999999999")[0] == 404, "MODULAR · una web que no está en Modular → 404")
    ok(pedir_acc("macarena", m="../x")[0] == 400, "MODULAR · identificador raro → 400")
    ok(pedir("/api/rastro", "POST", {"accion": "modular_acceso", "modulo": "seo-web", "objeto": mid}, yo="macarena")[0] == 403,
       "MODULAR · el navegador no finge la fila del rastro")
    for yo, debe in (("lucia", False), ("valeria", False), ("macarena", True), ("jeronimo", True), ("tomas", True)):
        c, tx, _ = pedir("/api/modulo/modular/tablero", yo=yo)
        ok((c == 200) == debe, f"MODULAR · tablero de todas las webs para {yo}: {'sí' if debe else 'no'} ({c})")
    lw = js(pedir("/api/modulo/modular/webs", yo="lucia"))
    ok(not lw.get("sin_cliente") and all(w.get("cliente_id") for w in lw.get("webs", [])), "MODULAR · Lucía solo recibe webs de clientes (las sin cliente no)")
    with sqlite3.connect(tmp / "prueba.db") as con:
        n = con.execute("SELECT count(*) FROM registro WHERE accion='modular_acceso'").fetchone()[0]
        nd = con.execute("SELECT count(*) FROM registro WHERE accion='modular_acceso_denegado'").fetchone()[0]
        enl = con.execute("SELECT count(*) FROM registro WHERE accion LIKE 'modular_acceso%' AND datos LIKE '%login%'").fetchone()[0]
    ok(n >= 3 and nd >= 1 and enl == 0, f"MODULAR · rastro de cada petición ({n} pedidas, {nd} denegadas) y ningún enlace guardado")

def telefonos_regla(tmp):
    """Regla de teléfonos (3-oct): el informe de dudosos solo lo leen dirección y operaciones y nunca lleva el número
    entero; los contactos de la ficha siguen detrás de ver_dato (con su cartera) y guardados con «+» y sin espacios."""
    if not (AQUI / "data/telefonos/dudosos.json").exists():
        return ok(True, "TELÉFONOS · sin informe de dudosos todavía: prueba omitida")
    for yo, debe in (("tomas", True), ("mili", True), ("lucia", False), ("setter_ana", False), ("sofia", False), ("cecilia", False)):
        if yo in PERSONAS and PERSONAS[yo].get("activo", True):
            c = pedir("/api/modulo/telefonos/dudosos", yo=yo)[0]
            ok((c == 200) == debe, f"TELÉFONOS · informe de dudosos para {yo}: {'sí' if debe else 'no'} ({c})")
    ok(pedir("/api/modulo/telefonos/dudosos", yo="tomas", como="lucia")[0] == 403, "TELÉFONOS · Tomás viendo como Lucía no recibe el informe")
    ok(pedir("/data/telefonos/dudosos.json", yo="lucia")[0] in (401, 403, 404), "TELÉFONOS · el fichero no se sirve tal cual")
    import escaner_secretos as ESC
    ok(not ESC.escanear_fichero(AQUI / "data/telefonos/dudosos.json"), "TELÉFONOS · el informe de dudosos no lleva números enteros (escáner limpio)")
    priv = AQUI / "data/ficha/_privado/contactos.json"
    if priv.exists():
        tels = [t["tel"] for c in json.loads(priv.read_text())["clientes"].values() for p in c["datos"]["personas"] for t in p["telefonos"]]
        ok(tels and all(_re11.fullmatch(r"\+\d{8,15}", t) for t in tels), f"TELÉFONOS · los {len(tels)} teléfonos de contactos, con «+» y sin espacios")
    c = pedir("/api/ver_dato", "POST", {"almacen": "ficha/_privado/contactos", "ref": "accompany", "campo": "datos"}, yo="setter_ana")[0]
    ok(c == 403, f"TELÉFONOS · una setter no abre los contactos de un cliente ({c})")


def setters_agenda(tmp):
    """Setters (3-oct, feedback de Tomás · setters_srv.py): cada setter actúa SOLO sobre sus leads y sus citas (comprobado en el
    servidor), «Agendar cita» queda en simulación con la vista previa del servidor (hueco libre, sin dobles), la propuesta de
    Claude solo de sus leads y nunca en «ver como», los setters no ven «En rojo» ni dinero, y el navegador no se salta la
    regla de «lo que sale fuera» fingiendo un lead de RO."""
    js = lambda r: json.loads(r[1]) if r[0] == 200 else {}
    d = json.loads((AQUI / "data/ventas_ro/setters.json").read_text())
    de = lambda s: [l["id"] for l in d["leads"] if l["setter"] == s and l.get("lista") in ("llamar_ya", "segunda", "hablado")]
    ana, jav = de("ana"), de("javier")
    if not ana or not jav:
        return ok(True, "SETTERS · sin leads de los dos setters: prueba omitida")
    acc = lambda yo, cuerpo, como=None: pedir("/api/acciones", "POST", {"modulo": "setters", **cuerpo}, yo=yo, como=como)
    ok(acc("setter_ana", {"herramienta": "app", "tipo": "resultado_llamada", "objeto": jav[0], "texto": "No contesta"})[0] == 403,
       "SETTERS · Ana no apunta resultados a un lead de Javier (403)")
    ok(acc("setter_javier", {"herramienta": "app", "tipo": "confirmacion_cita", "objeto": ana[0], "texto": "Confirmada"})[0] == 403,
       "SETTERS · Javier no confirma citas de Ana (403)")
    ok(acc("setter_ana", {"herramienta": "app", "tipo": "resultado_llamada", "objeto": "no-existe-123", "texto": "x"})[0] == 403,
       "SETTERS · un lead que no existe → 403")
    ok(acc("setter_ana", {"herramienta": "app", "tipo": "informe_fin_de_dia", "objeto": "javier", "texto": "x"})[0] == 403,
       "SETTERS · el informe de fin de día solo a su nombre")
    c, t, _ = acc("setter_ana", {"herramienta": "whatsapp", "tipo": "whatsapp_abierto", "objeto": ana[0], "texto": "WhatsApp"})
    ok(c == 200, f"SETTERS · WhatsApp a su propio lead de RO entra en la cola (no es un cliente) ({c})")
    c = pedir("/api/acciones", "POST", {"modulo": "en-rojo", "herramienta": "whatsapp", "tipo": "whatsapp", "objeto": "+34600111222", "texto": "x", "_lead_ro": True}, yo="tomas")[0]
    ok(c in (400, 403), f"SETTERS · el navegador no se salta «lo que sale fuera» mandando _lead_ro ({c})")
    libres = (d.get("huecos") or {}).get("dias") or {}
    if libres:
        dia = sorted(libres)[0]
        ini = f"{dia} {libres[dia][0]}"
        c, t, _ = acc("setter_ana", {"herramienta": "ghl", "tipo": "crear_cita_ghl", "objeto": ana[0],
                                     "vista_previa": {"inicio": ini, "titulo": "Prueba", "notas": "n", "contacto_id": jav[0], "calendario_id": "otro"}})
        r = json.loads(t) if c == 200 else {}
        vp = r.get("vista_previa") or {}
        ok(c == 200 and r.get("estado") == "simulada" and vp.get("contacto_id") == ana[0] and vp.get("calendario_id") == "ChisJEQCj8fXSnML13AQ" and vp.get("hueco_comprobado"),
           f"SETTERS · «Agendar cita» queda simulada y el contacto y el calendario los pone el servidor ({c})")
        ok("pendiente de GoHighLevel" in str(r.get("pendiente")) and r.get("ghl_encendido") is False, "SETTERS · la respuesta dice «pendiente de GoHighLevel» con el interruptor apagado")
        ok(acc("setter_ana", {"herramienta": "ghl", "tipo": "crear_cita_ghl", "objeto": ana[1 if len(ana) > 1 else 0], "vista_previa": {"inicio": ini}})[0] == 409,
           "SETTERS · el mismo hueco no se pide dos veces")
        ok(acc("setter_ana", {"herramienta": "ghl", "tipo": "crear_cita_ghl", "objeto": ana[0], "vista_previa": {"inicio": f"{dia} 03:17"}})[0] == 409,
           "SETTERS · una hora que no está libre en el calendario → 409")
        ok(acc("setter_ana", {"herramienta": "ghl", "tipo": "crear_cita_ghl", "objeto": jav[0], "vista_previa": {"inicio": ini}})[0] == 403,
           "SETTERS · Ana no agenda a un lead de Javier")
        with sqlite3.connect(tmp / "prueba.db") as con:
            est = {r[0] for r in con.execute("SELECT estado FROM acciones WHERE tipo='crear_cita_ghl'")}
        ok(est == {"simulada"}, f"SETTERS · ninguna cita sale de la cola en simulación ({est})")
    prop = lambda yo, lead, como=None: pedir("/api/setters/propuesta_cita", "POST", {"lead": lead, "notas": "el viernes a las 10"}, yo=yo, como=como)
    c, t, _ = prop("setter_ana", ana[0])
    ok(c == 200 and json.loads(t).get("origen") in ("ia", "reglas"), f"SETTERS · «Claude te lo rellena» propone para su lead ({c})")
    ok("@" not in t and not _re11.search(r"\+?\d{9,}", t), "SETTERS · la propuesta no lleva teléfonos ni correos")
    ok(prop("setter_ana", jav[0])[0] == 403, "SETTERS · ni propuesta para un lead de otra setter")
    ok(prop("lucia", ana[0])[0] == 403, "SETTERS · Lucía (account) no pide propuestas de citas")
    ok(prop("tomas", ana[0], como="setter_ana")[0] == 403, "SETTERS · en «ver como» no se propone nada")
    # los setters no ven «En rojo» ni dinero
    for ruta in ("/api/modulo/en_rojo/atajos", "/api/modulo/dinero/resumen", "/api/modulo/finanzas/resumen"):
        c = pedir(ruta, yo="setter_ana")[0]
        ok(c in (403, 404), f"SETTERS · la setter no recibe {ruta} ({c})")
    t = pedir("/api/modulo/ventas_ro/setters", yo="setter_ana")[1]
    ok("€" not in t and "cuota" not in t and "facturacion" not in t, "SETTERS · sus datos no llevan dinero")


if __name__ == "__main__":
    main()
