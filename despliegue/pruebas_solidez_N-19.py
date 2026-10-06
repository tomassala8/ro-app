#!/usr/bin/env python3
"""despliegue/pruebas_solidez_N-19.py · N-19: «crear tarea» sin lista de ClickUp se dice en llano; «otro» no rompe.

Uso: python3 despliegue/pruebas_solidez_N-19.py        (SQLite temporal, ClickUp simulado en memoria: sin red, sin llaves)
Sobre una base temporal y con `ClickUpSimulado` (nunca el proveedor real):
(1) una acción `pedir_movil` se traduce a «crear tarea» con una lista sin resolver;
(2) en simulación nace con el aviso «Sin lista de ClickUp para este cliente…» en su primer paso;
(3) con ClickUp real simulado por la prueba, `ejecutar` la deja en `fallido` con ese motivo (nunca el genérico «sin lista
    resuelta» ni «error») y publica el aviso a Agus con el mismo texto;
(4) un tipo «otro» (`fechas_dn`) sigue fallido «no soportado» con su texto de siempre;
(5) el proveedor real, ante un objeto «lista» o «otro», lanza «no soportado» (no «destinatario: sin lista resuelta»).
No toca `local.db`, `data/` ni la red. Sin datos reales en la salida.
"""
import json
import os
import pathlib
import sqlite3
import sys
import tempfile

os.environ["RO_SIN_LLAVES"] = "1"
RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
import sincronia as SI  # noqa: E402

fallos, n = [], 0


def ok(c, t):
    global n
    n += 1
    if not c:
        fallos.append(t)


SI._cliente_nombre = lambda cid: f"Cliente de prueba {cid}" if cid else None     # no se abre data/clientes.json
SI._persona = lambda pid: {"id": pid, "alias": pid, "puestos": []}
with tempfile.TemporaryDirectory(prefix="n19_") as t:
    con = sqlite3.connect(str(pathlib.Path(t) / "n19.db"))
    con.row_factory = sqlite3.Row
    SI.preparar(con)
    con.execute("CREATE TABLE canal_mensajes (id INTEGER PRIMARY KEY AUTOINCREMENT, canal_id TEXT, tipo TEXT, quien TEXT, texto TEXT, menciones TEXT, "
                "clave TEXT UNIQUE, cliente_id TEXT, dueno_id TEXT, ver TEXT, datos TEXT, creado TEXT)")

    def accion(tipo, objeto):
        return {"tipo": tipo, "objeto": objeto, "texto": "Pedir un móvil de contacto", "vista_previa": json.dumps({"tarea": "Pedir móvil"}), "cliente_id": "c_n19"}

    def nuevo(tipo, objeto, clave, modo):
        canal, obj, cambio, base, ign = SI.traducir(accion(tipo, objeto))
        cid, _ = SI.crear_cambio(con, clave=clave, quien="persona_n19", canal=canal, tipo=tipo, objeto=obj, cambio=cambio, base=base,
                                 cliente_id="c_n19", modo=modo, ignorado=ign)
        return cid, obj, cambio

    # (1) y (2) simulación
    SI.canal_real = lambda canal: False
    cid, obj, cambio = nuevo("pedir_movil", "c_n19", "n19_sim", "simulado")
    ok(cambio.get("campo") == "crear_tarea" and obj.get("resuelto") is False, f"(1) pedir_movil no sale como crear tarea sin resolver: {cambio} {obj}")
    primero = SI.pasos_de(con, cid)[0]
    ok(str(primero["motivo"]).startswith("Hecho en la app") and "Sin lista de ClickUp para" in str(primero["motivo"]), f"(2) la simulación no avisa de la lista: {primero['motivo']!r}")

    # (3) ClickUp «real» (el interruptor lo finge la prueba; el proveedor es el simulado en memoria)
    SI.canal_real = lambda canal: True
    cid, obj, cambio = nuevo("pedir_movil", "c_n19", "n19_real", "real")
    r = SI.ejecutar(con, cid, SI.ClickUpSimulado())
    ultimo = [p for p in SI.pasos_de(con, cid) if p["evento"] != "aviso"][-1]
    ok(r == "fallido" and ultimo["estado"] == "fallido", f"(3) esperaba fallido y salió {r}/{ultimo['estado']}")
    ok(str(ultimo["motivo"]).startswith("Sin lista de ClickUp para"), f"(3) motivo: {ultimo['motivo']!r}")
    ok("sin lista resuelta" not in json.dumps(dict(ultimo), ensure_ascii=False).lower(), "(3) aparece el genérico «sin lista resuelta»")
    avisos = [x["texto"] for x in con.execute("SELECT texto FROM canal_mensajes")]
    ok(any("Sin lista de ClickUp para" in x for x in avisos), f"(3) el aviso a Agus no trae el texto claro: {avisos[:1]}")

    # (4) un tipo «otro»
    cid, obj, cambio = nuevo("fechas_dn", "x_n19", "n19_otro", "real")
    r = SI.ejecutar(con, cid, SI.ClickUpSimulado())
    ultimo = [p for p in SI.pasos_de(con, cid) if p["evento"] != "aviso"][-1]
    ok(r == "fallido" and ultimo["motivo"] == SI.LLANO["no_soportado"], f"(4) «otro» no sale «no soportado»: {r} {ultimo['motivo']!r}")

    # (5) el proveedor real, solo en memoria y antes de cualquier llamada de red
    prov = SI.ProveedorClickUp()
    for tipo_obj in ("lista", "otro"):
        c = {"objeto": json.dumps({"tipo": tipo_obj, "ref": "x", "resuelto": False}), "clave": "n19_clave", "quien": "persona_n19", "cambio": json.dumps({"campo": "crear_tarea"})}
        for metodo in (prov.leer, prov.aplicar):
            try:
                metodo(c)
                ok(False, f"(5) {metodo.__name__} con «{tipo_obj}» no lanzó")
            except SI.ErrorSinc as e:
                ok(e.tipo == "no_soportado", f"(5) {metodo.__name__} con «{tipo_obj}» lanza {e.tipo}")
    con.close()

ok("sin lista resuelta" not in (RAIZ / "sincronia.py").read_text(encoding="utf-8"), "(5) sincronia.py sigue con el texto genérico «sin lista resuelta»")
print(f"{'✘' if fallos else '✔'} N-19: {n} comprobaciones" + (" · " + " · ".join(fallos) if fallos else ""))
sys.exit(1 if fallos else 0)
