#!/usr/bin/env python3
"""migracion/pruebas_N-24.py · N-24: las rutas de Operaciones que escribió Astra solo para SQLite funcionan sobre Postgres.

Qué comprueba, por cada módulo (registros 269, control 272, feedback 273, anomalías 276, notas 281, prioridades 300,
pedidos de account, decisiones durables 382):
  1. Sin guarda: ninguna línea `if DATABASE_URL … raise …(503)` queda en el módulo.
  2. La MISMA secuencia de peticiones (lectura, escritura, repetición, cambio de contenido, lectura) por el manejador
     de la ruta (`enganchar`) da lo mismo con SQLite (la app de hoy) que con Postgres (`despliegue/base.py`, base de
     pruebas ro_esc): mismo estado, mismo cuerpo (sin horas ni números de fila) y, con Postgres, nunca 503.
  3. Escribe lo mismo: el número de filas de su tabla es igual en las dos bases.
Usa los fixtures de las pruebas que ya existen (`probar_*_NNN.py`, solo se importan) y datos inventados.
Solo escribe en ro_esc (base de pruebas). Sale 0 si pasa.

Uso: python3 migracion/pruebas_N-24.py [--solo registros_269,feedback_273]
"""
import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import traceback
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(1, str(RAIZ / "despliegue"))
URL_ESC = "postgresql://ro:ro@127.0.0.1:5432/ro_esc"

ap = argparse.ArgumentParser()
ap.add_argument("--solo", default="")
a = ap.parse_args()

os.environ["RO_PILOTO_LECTURA"] = "no"
os.environ["DATABASE_URL"] = ""
os.environ["PGDATABASE_URL"] = ""

fallos = []


def exige(cond, texto):
    if not cond:
        fallos.append(texto)
    return cond


def u(n):
    """UUID v4 fijo: las dos bases reciben exactamente las mismas intenciones."""
    return str(uuid.UUID(int=(n & ((1 << 60) - 1)) | (4 << 76) | (2 << 62)))


class Servidor:
    """El servidor mínimo que `enganchar` necesita: responder(código, cuerpo) devuelve lo que se habría enviado."""

    def responder(self, codigo, doc):
        return codigo, doc

    def _api_get(self, ruta, q, real, vista):
        return 404, {"error": "otra ruta"}

    def api_post(self, ruta, real, vista, b):
        return 404, {"error": "otra ruta"}


TS = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:\d{2}|Z)?")
VOLATIL = {"registrado_en", "hora", "creado", "creada", "fecha_registro", "guardado_en", "respondida"}


UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def normal(x, vistos=None):
    """Sin horas ni números de fila; los UUID que el módulo inventa (objetos) por orden de aparición."""
    vistos = {} if vistos is None else vistos
    if isinstance(x, dict):
        return {k: normal(v, vistos) for k, v in x.items() if k not in VOLATIL}
    if isinstance(x, (list, tuple)):
        return [normal(v, vistos) for v in x]
    if isinstance(x, str):
        x = TS.sub("<hora>", x)
        return UUID_RE.sub(lambda m: m.group(0) if m.group(0).startswith("00000000-") else "<uuid%d>" % vistos.setdefault(m.group(0), len(vistos) + 1), x)
    return x


def diferencia(x, y, ruta=""):
    """La primera diferencia entre dos cuerpos, legible."""
    if type(x) is not type(y):
        return f"{ruta}: {type(x).__name__} {json.dumps(x, ensure_ascii=False)[:60]} ≠ {type(y).__name__} {json.dumps(y, ensure_ascii=False)[:60]}"
    if isinstance(x, dict):
        for k in sorted(set(x) | set(y)):
            if k not in x or k not in y or x[k] != y[k]:
                return diferencia(x.get(k), y.get(k), f"{ruta}/{k}") if k in x and k in y else f"{ruta}/{k}: solo en " + ("SQLite" if k in x else "Postgres")
    if isinstance(x, list):
        if len(x) != len(y):
            return f"{ruta}: {len(x)} elementos ≠ {len(y)}"
        for i, (p, q) in enumerate(zip(x, y)):
            if p != q:
                return diferencia(p, q, f"{ruta}[{i}]")
    return f"{ruta}: {json.dumps(x, ensure_ascii=False)[:80]} ≠ {json.dumps(y, ensure_ascii=False)[:80]}"


def sin_guarda(fichero):
    """True si el módulo ya no se niega con 503 por haber DATABASE_URL."""
    texto = (RAIZ / fichero).read_text(encoding="utf-8")
    for linea in texto.splitlines():
        if "DATABASE_URL" in linea and "503" in linea and "raise" in linea:
            return False
    return True


# ---------------------------------------------------------------- escenarios: (módulo, fichero, clase de fixture, tabla)
# Cada escenario recibe `t` (el fixture ya montado) y `llamar(metodo, q_o_cuerpo, rid, vid, persona=None)`.
def esc_registros(t, M, llamar):
    import probar_operaciones_registros_269 as X
    r = M.RUTA
    return [
        llamar("GET", {}, "a", "a"),
        llamar("POST", X.cuerpo("manana", intencion_id=u(1)), "a", "a"),
        llamar("POST", X.cuerpo("manana", intencion_id=u(1)), "a", "a"),
        llamar("POST", X.cuerpo("manana", intencion_id=u(1), nota="otra"), "a", "a"),
        llamar("POST", X.cuerpo("cierre", intencion_id=u(2)), "a", "a"),
        llamar("POST", {"tipo": "avisado", "persona_id": "a", "revision": 0, "intencion_id": u(3)}, "mili", "mili"),
        llamar("GET", {}, "a", "a"),
        llamar("GET", {}, "b", "b"),
    ], r


def esc_control(t, M, llamar):
    import probar_control_operaciones_272 as X
    ids = []
    sal = [llamar("GET", {}, "a", "a"),
           llamar("POST", X.crear(cliente_id="own", intencion_id=u(10)), "a", "a"),
           llamar("POST", X.crear(cliente_id="own", intencion_id=u(10)), "a", "a"),
           llamar("POST", X.crear(cliente_id="foreign", intencion_id=u(11)), "a", "a"),
           llamar("GET", {}, "a", "a")]
    doc = sal[-1][1]
    obj = ((doc or {}).get("registros") or [{}])[0].get("objeto")
    if obj:
        sal.append(llamar("POST", {"tipo": "encargo", "operacion": "actualizar", "objeto": obj, "revision": 1,
                                   "intencion_id": u(12), "hecho": True, "prueba": "Revisión sintética realizada"}, "a", "a"))
        sal.append(llamar("GET", {}, "a", "a"))
    exige(bool(obj), "control 272: el encargo creado no aparece en la lectura")
    return sal, M.RUTA


def esc_feedback(t, M, llamar):
    import probar_operaciones_feedback_273 as X
    cuerpo = lambda **kw: X.body(**{"intencion_id": u(20), **kw})
    q = {"cliente_id": ["c"]}
    return [llamar("GET", q, "a", "a"),
            llamar("POST", cuerpo(), "a", "a"),
            llamar("POST", cuerpo(), "a", "a"),
            llamar("POST", cuerpo(nota="Cambio"), "a", "a"),
            llamar("POST", cuerpo(estado="conseguida", revision=1, intencion_id=u(21), nota="El cliente dijo que sí"), "a", "a"),
            llamar("GET", q, "a", "a"),
            llamar("GET", q, "ops", "ops")], M.RUTA


def esc_anomalias(t, M, llamar):
    origen = M.resolver(t.S, "mili", "mili", "entry_1", True)
    cuerpo = lambda **kw: {"anomalia_id": "entry_1", "decision": "correcto", "revision": 0, "intencion_id": u(30),
                           "huella_origen": origen["huella_origen"], **kw}
    q = {"id": ["entry_1"]}
    return [llamar("GET", q, "mili", "mili"),
            llamar("POST", cuerpo(), "mili", "mili"),
            llamar("POST", cuerpo(), "mili", "mili"),
            llamar("POST", cuerpo(decision="error"), "mili", "mili"),
            llamar("GET", q, "mili", "mili")], M.RUTA


def esc_notas(t, M, llamar):
    import probar_notas_equipo_281 as X
    cuerpo = lambda **kw: {"persona_id": "a", "periodo": "2026-10", "nota": 7, "prueba": "Hecho sintético observable",
                           "accion_propuesta": "formar", "revision": 0, "intencion_id": u(40), **kw}
    q = {"persona_id": ["a"]}
    return [llamar("GET", q, "mili", "mili"),
            llamar("POST", cuerpo(), "mili", "mili"),
            llamar("POST", cuerpo(), "mili", "mili"),
            llamar("POST", cuerpo(nota=8), "mili", "mili"),
            llamar("POST", cuerpo(revision=1, nota=None, accion_propuesta=None, prueba="Se retira la valoración previa",
                                  intencion_id=u(41)), "mili", "mili"),
            llamar("GET", q, "mili", "mili")], M.RUTA


def esc_prioridades(t, M, llamar):
    ref = M.referencias(t.S, "ops", "ops")["exacta"]["fuente_revision"]
    cuerpo = lambda **kw: {"prioridad_id": "exacta", "fuente_revision": ref, "dia": "2026-10-03", "revision": 0,
                           "estado": "empujado", "nota": "Contacto declarado", "intencion_id": u(50), **kw}
    return [llamar("GET", {}, "ops", "ops"),
            llamar("POST", cuerpo(), "ops", "ops"),
            llamar("POST", cuerpo(), "ops", "ops"),
            llamar("POST", cuerpo(nota="Distinta"), "ops", "ops"),
            llamar("GET", {}, "ops", "ops"),
            llamar("GET", {}, "otro", "otro")], M.RUTA


def esc_pedidos(t, M, llamar):
    o, tr = M.capacidad(t.S, "o", "o", "c", "responder_correo", "t")
    cuerpo = lambda **kw: {"cliente_id": "c", "tipo": "responder_correo", "referencia_id": "t", "estado": "pedido",
                           "revision": 0, "revision_fuente": tr, "intencion_id": u(60), **kw}
    q = {"cliente_id": ["c"]}
    return [llamar("GET", q, "o", "o"),
            llamar("POST", cuerpo(), "o", "o"),
            llamar("POST", cuerpo(), "o", "o"),
            llamar("POST", cuerpo(estado="anulado"), "o", "o"),
            llamar("GET", q, "o", "o"),
            llamar("GET", {}, "o", "o") if False else llamar("GET", q, "a", "a")], M.RUTA


def esc_decisiones(t, M, llamar):
    import probar_decisiones_durables_382 as X
    p_tomas = {"id": "tomas", "estado": "activo", "puestos": ["direccion"]}
    nueva = X.Pruebas382.nueva
    n = lambda key, **kw: {**nueva(None, key=key), **kw}
    sal = [llamar("GET", {}, "tomas", "tomas", p_tomas),
           llamar("POST", n(u(70)), "tomas", "tomas", p_tomas),
           llamar("POST", n(u(70)), "tomas", "tomas", p_tomas),
           llamar("POST", n(u(70), titulo="Otro texto"), "tomas", "tomas", p_tomas),
           llamar("GET", {}, "tomas", "tomas", p_tomas)]
    doc = sal[-1][1] or {}
    fila = next(iter(doc.get("decisiones") or doc.get("registros") or doc.get("filas") or []), None)
    if isinstance(fila, dict) and fila.get("id") is not None:
        sal.append(llamar("POST", {"operacion": "responder", "intencion_id": u(71), "id": fila["id"],
                                   "revision": fila.get("revision", 1), "decision": "Aprobar la recomendación",
                                   "motivo": None, "delegada_en": None}, "tomas", "tomas", p_tomas))
        sal.append(llamar("GET", {}, "tomas", "tomas", p_tomas))
    return sal, M.RUTA


# nombre: (fichero, módulo, fixture (módulo de prueba, clase, método), tabla, escenario)
MODULOS = {
    "registros_269": ("operaciones_registros_269.py", "operaciones_registros_269", ("probar_operaciones_registros_269", "Registros", "test_replay_y_conflicto_mismo_uuid"), "operaciones_registros_269", esc_registros),
    "control_272": ("operaciones_registros_272.py", "operaciones_registros_272", ("probar_control_operaciones_272", "Control", "test_cliente_act_duplicado_persona_revocada"), "operaciones_control_272", esc_control),
    "feedback_273": ("operaciones_feedback_273.py", "operaciones_feedback_273", ("probar_operaciones_feedback_273", "Feedback", "test_pedido_no_conseguido_y_reinicio"), "operaciones_feedback_273", esc_feedback),
    "anomalias_276": ("operaciones_anomalias_276.py", "operaciones_anomalias_276", ("probar_anomalias_276", "Anomalias", "test_correcto_durable_recibo_sin_modificar_fuente"), "operaciones_anomalias_276", esc_anomalias),
    "notas_281": ("operaciones_notas_equipo_281.py", "operaciones_notas_equipo_281", ("probar_notas_equipo_281", "Notas", "test_durable_autor_periodo_no_kpi_no_decision_laboral"), "operaciones_notas_equipo_281", esc_notas),
    "prioridades_300": ("operaciones_prioridades_300.py", "operaciones_prioridades_300", ("probar_operaciones_prioridades_300", "Prioridades", "test_durable_restart_declaracion_no_ejecucion"), "operaciones_prioridades_300", esc_prioridades),
    "pedidos_account": ("operaciones_pedidos_account.py", "operaciones_pedidos_account", ("probar_pedidos_account_294", "Test", "test_store_replay"), "operaciones_pedidos_account", esc_pedidos),
    "decisiones_382": ("decisiones_durables_382.py", "decisiones_durables_382", ("probar_decisiones_durables_382", "Pruebas382", "test_nueva_replay_durable"), "decisiones", esc_decisiones),
}


def montar(fixture, backend):
    """Un fixture nuevo con su base: SQLite temporal (la app de hoy) o ro_esc (Postgres por despliegue/base.py)."""
    modulo, clase, metodo = fixture
    cls = getattr(__import__(modulo), clase)
    t = cls(metodo)
    t.setUp()
    if backend == "sqlite":
        os.environ["DATABASE_URL"] = ""
        return t
    import base as BASE
    os.environ["DATABASE_URL"] = URL_ESC
    t.S.conectar = BASE.conectar
    t.con = BASE.conectar
    if hasattr(t, "path"):
        t.S.DB = t.path     # lo que haya: en Postgres no debe usarse
    return t


def conectar_de(t, backend):
    if backend == "pg":
        import base as BASE
        return BASE.conectar()
    if hasattr(t, "db"):
        c = sqlite3.connect(t.db, timeout=10)
    elif hasattr(t, "temp"):
        c = sqlite3.connect(Path(t.temp.name) / "test.sqlite3", timeout=10)
    else:
        c = sqlite3.connect(t.path, timeout=10)
    c.row_factory = sqlite3.Row
    return c


def correr(nombre, backend):
    fichero, modulo, fixture, tabla, escenario = MODULOS[nombre]
    M = __import__(modulo)
    t = montar(fixture, backend)
    if backend == "sqlite":
        t.S.conectar = lambda: conectar_de(t, "sqlite")
        if not hasattr(t.S, "DB"):
            t.S.DB = Path(getattr(t, "db", None) or (Path(t.temp.name) / "test.sqlite3" if hasattr(t, "temp") else t.path))
    S = t.S
    H = type("H", (Servidor,), {})
    M.enganchar(H, S)
    h = H()

    def llamar(metodo, datos, rid, vid, persona=None):
        real = dict(persona or {"id": rid})
        vista = dict(persona or {"id": vid})
        real["id"], vista["id"] = rid, vid
        try:
            if metodo == "GET":
                return h._api_get(M.RUTA, datos, real, vista)
            return h.api_post(M.RUTA, real, vista, datos)
        except Exception as e:      # un fallo del módulo es un resultado más, y se compara
            return "EXC", {"error": type(e).__name__ + ": " + str(e)[:200]}

    try:
        sal, _ruta = escenario(t, M, llamar)
        n = None
        c = conectar_de(t, backend)
        try:
            n = c.execute(f"SELECT COUNT(*) FROM {getattr(M, 'TABLA', None) or tabla}").fetchone()[0]
        except Exception:
            n = "sin tabla"
        finally:
            c.close()
        return [(s, normal(d)) for s, d in sal], n
    finally:
        try:
            t.tearDown()
        except Exception:
            pass
        os.environ["DATABASE_URL"] = ""


def base_limpia():
    r = subprocess.run([sys.executable, "migracion/contrato_escritura.py", "base-limpia", "ro_esc"], cwd=RAIZ, check=False)
    return r.returncode == 0


def main():
    elegidos = [x for x in (a.solo.split(",") if a.solo else MODULOS) if x]
    for nombre in elegidos:
        exige(nombre in MODULOS, f"{nombre}: módulo desconocido")
    elegidos = [x for x in elegidos if x in MODULOS]
    if not base_limpia():
        print("✘ N-24: base-limpia ro_esc no sale 0")
        return 1
    for nombre in elegidos:
        fichero = MODULOS[nombre][0]
        exige(sin_guarda(fichero), f"{nombre}: {fichero} aún se niega con 503 si hay DATABASE_URL")
        try:
            lite, n_lite = correr(nombre, "sqlite")
            pg, n_pg = correr(nombre, "pg")
        except Exception:
            exige(False, f"{nombre}: se rompe · " + traceback.format_exc().strip().splitlines()[-1])
            continue
        exige(len(lite) == len(pg), f"{nombre}: distinto número de respuestas")
        for i, (x, y) in enumerate(zip(lite, pg)):
            exige(y[0] != 503, f"{nombre} paso {i}: Postgres responde 503 · {json.dumps(y[1], ensure_ascii=False)[:120]}")
            exige(x == y, f"{nombre} paso {i}: SQLite {x[0]} ≠ Postgres {y[0]} · " + diferencia(x[1], y[1]))
        exige(n_lite == n_pg, f"{nombre}: filas escritas SQLite {n_lite} ≠ Postgres {n_pg}")
        exige(any(s == 200 for s, _ in pg), f"{nombre}: ninguna respuesta 200 con Postgres")
        print(f"  {nombre}: {len(pg)} peticiones · estados SQLite {[s for s, _ in lite]} · Postgres {[s for s, _ in pg]} · filas {n_lite}/{n_pg}")
    print(("✔ N-24: las rutas de Operaciones responden y escriben igual sobre Postgres" if not fallos
           else "✘ N-24: " + " · ".join(fallos)))
    return 1 if fallos else 0


sys.exit(main())
