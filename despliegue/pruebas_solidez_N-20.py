#!/usr/bin/env python3
"""despliegue/pruebas_solidez_N-20.py · N-20: los interruptores de ClickUp y de envíos viven en la base, con rastro.

Uso: python3 despliegue/pruebas_solidez_N-20.py      (rehace ro_esc, que es solo de pruebas; no toca local.db ni ro_app)
Con DATABASE_URL de ro_esc, ficheros de interruptor temporales y SIN las variables RO_CLICKUP_REAL ni RO_ENVIOS_REALES
(si alguna está puesta, la prueba aborta: nunca activa nada real):
(1) la tabla `interruptor` existe y, sin filas, manda el fichero (como antes);
(2) `poner_interruptor("clickup_real", True, …)` deja su fila y su rastro en `registro`; `interruptor()` lo ve como
    «fichero activo» pero NO «real» (falta la variable de entorno) y el rastro sigue siendo verificable;
(3) un fichero que dice `clickup_real: false` (lo que pasa cuando la nube reemplaza `data/`) no cambia lo que se lee;
(4) solo enciende quien manda; apagar lo puede hacer cualquiera con su motivo, y apagar gana a un fichero encendido;
(5) lo mismo para los envíos (`envios_reales` y `canal_desk`): fila, rastro, nunca real sin variable de entorno;
(6) nombres y valores raros se rechazan sin dejar fila.
Sin red, sin llaves, sin datos reales.
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

for var in ("RO_CLICKUP_REAL", "RO_ENVIOS_REALES"):
    if os.environ.get(var):
        print(f"✘ N-20: {var} está puesta; esta prueba no se ejecuta con envíos o ClickUp reales a mano")
        sys.exit(1)

RAIZ = pathlib.Path(__file__).resolve().parents[1]
URL = "postgresql://ro:ro" + "@127.0.0.1:5432/ro_esc"   # partida: el escáner de secretos la leería como un correo
fallos = []


def exige(cond, texto):
    if not cond:
        fallos.append(texto)


def consulta(sql, args=()):
    import psycopg
    with psycopg.connect(URL, autocommit=True) as con:
        cur = con.execute(sql, args)
        try:
            return cur.fetchall()
        except Exception:
            return []


limpia = subprocess.run([sys.executable, "migracion/contrato_escritura.py", "base-limpia", "ro_esc"], cwd=RAIZ, check=False,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
exige(limpia.returncode == 0, f"base-limpia ro_esc rc={limpia.returncode}")
if limpia.returncode == 0:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="ro_n20_"))
    f_sinc, f_env = tmp / "sinc.json", tmp / "envios.json"
    os.environ.update(DATABASE_URL=URL, RO_DB=str(tmp / "no_debe_existir.db"), RO_SIN_LLAVES="1", RO_AVISOS_SIN_BUCLE="1",
                      RO_SINC_INTERRUPTOR=str(f_sinc), RO_ENVIOS_INTERRUPTOR=str(f_env), RO_ESTADO_DIR=str(tmp / "estado"))
    sys.path.insert(0, str(RAIZ))
    import sincronia as SI  # noqa: E402
    import envios as EN  # noqa: E402

    def sin_cache():
        SI._INT_BASE.update(t=0.0, filas=None)
        EN._INT_BASE.update(t=0.0, filas=None)

    def filas(nombre):
        return consulta("SELECT valor, quien, motivo FROM interruptor WHERE nombre = %s ORDER BY id", (nombre,))

    def rastro(accion):
        return consulta("SELECT quien, coleccion, clave, motivo FROM registro WHERE accion = %s ORDER BY id", (accion,))

    # (1) tabla y fichero de respaldo
    exige(consulta("SELECT count(*) FROM interruptor")[0][0] == 0, "(1) la tabla interruptor no existe o no está vacía")
    f_sinc.write_text(json.dumps({"clickup_real": True, "activado_por": "tomas", "chat_puente": "simulacion"}))
    sin_cache()
    st = SI.interruptor()
    exige(st["fichero"] is True and st["reales"] is False and st["chat_puente"] == "simulacion", f"(1) sin filas no manda el fichero: {st['fichero']} {st['chat_puente']}")

    # (3) la nube reemplaza el fichero: ya no dice nada, y la base sigue mandando
    SI.poner_interruptor("clickup_real", True, "tomas", "prueba N-20")
    f_sinc.write_text(json.dumps({"clickup_real": False}))
    sin_cache()
    st = SI.interruptor()
    exige(st["fichero"] is True and st["activado_por"] == "tomas", f"(3) un fichero «apagado» ha cambiado lo que se lee: {st['fichero']} {st['activado_por']}")
    exige(st["reales"] is False and st["entorno"] is False and st["canales"] == {"clickup": False, "chat": False}, f"(2) sin variable de entorno no puede ser real: {st['canales']}")
    f_sinc.unlink()
    sin_cache()
    exige(SI.interruptor()["fichero"] is True, "(3) sin fichero, la base no basta para verlo activo")

    # (2) fila y rastro
    f = filas("clickup_real")
    exige(f == [("true", "tomas", "prueba N-20")], f"(2) fila de clickup_real: {f}")
    r = rastro("interruptor_clickup_real")
    exige(len(r) == 1 and r[0][1] == "interruptor" and r[0][2] == "clickup_real" and r[0][3] == "prueba N-20", f"(2) rastro de clickup_real: {r}")

    # (4) apagar gana; solo enciende quien manda; el puente de chat tiene sus valores
    for mal, args in (("encender sin ser quien manda", ("clickup_real", True, "alguien_de_prueba", "no debería")),
                      ("nombre desconocido", ("otro_interruptor", True, "tomas", "x")),
                      ("puente con valor raro", ("chat_puente", "si", "tomas", "x")),
                      ("sin motivo", ("clickup_real", False, "tomas", " "))):
        try:
            SI.poner_interruptor(*args)
            fallos.append(f"(4/6) {mal}: no se ha rechazado")
        except (PermissionError, ValueError):
            pass
    exige(len(filas("clickup_real")) == 1 and not filas("otro_interruptor") and not filas("chat_puente"), "(4/6) un cambio rechazado dejó fila")
    SI.poner_interruptor("clickup_real", False, "alguien_de_prueba", "apagado de prueba")
    f_sinc.write_text(json.dumps({"clickup_real": True, "activado_por": "tomas"}))
    sin_cache()
    st = SI.interruptor()
    exige(st["fichero"] is False and st["activado_por"] == "alguien_de_prueba", f"(4) apagar en la base no gana a un fichero encendido: {st['fichero']}")
    SI.poner_interruptor("chat_puente", "simulacion", "tomas", "puente de prueba")
    sin_cache()
    exige(SI.interruptor()["chat_puente"] == "simulacion", "(4) el puente de chat no se lee de la base")

    # (5) envíos
    f_env.write_text(json.dumps({"envios_reales": False, "canales": {"desk": False}}))
    sin_cache()
    exige(EN.interruptor()["fichero"] is False and EN.interruptor()["reales"] is False, "(5) arranque de envíos no está apagado")
    EN.poner_interruptor("envios_reales", True, "tomas", "prueba N-20 envíos")
    EN.poner_interruptor("canal_desk", True, "tomas", "prueba N-20 canal")
    f_env.write_text("{}")           # la nube reemplaza el fichero
    sin_cache()
    st = EN.interruptor()
    exige(st["fichero"] is True and st["entorno"] is False and st["reales"] is False and st["canales"]["desk"] is False,
          f"(5) los envíos no se leen de la base o salen reales sin variable: {st['fichero']} {st['entorno']} {st['canales']}")
    exige(filas("envios_reales") == [("true", "tomas", "prueba N-20 envíos")] and len(filas("canal_desk")) == 1, "(5) filas de envíos")
    exige(len(rastro("interruptor_envios_reales")) == 1 and len(rastro("interruptor_canal_desk")) == 1, "(5) rastro de envíos")
    for args in (("envios_reales", True, "alguien_de_prueba", "no"), ("canal_inexistente", True, "tomas", "x"), ("envios_reales", "si", "tomas", "x")):
        try:
            EN.poner_interruptor(*args)
            fallos.append(f"(5/6) envíos: {args[0]}/{args[2]} no se ha rechazado")
        except (PermissionError, ValueError):
            pass
    exige(len(filas("envios_reales")) == 1 and not filas("canal_inexistente"), "(5/6) un cambio de envíos rechazado dejó fila")
    EN.poner_interruptor("envios_reales", False, "alguien_de_prueba", "apagado de prueba")
    sin_cache()
    exige(EN.interruptor()["fichero"] is False and EN.interruptor()["canales"]["desk"] is False, "(5) apagar envíos en la base no se nota")

    # el rastro encadenado sigue entero
    v = consulta("SELECT count(*) FROM registro r LEFT JOIN registro_huellas h ON h.id = r.id WHERE r.coleccion = 'interruptor' AND h.id IS NULL")[0][0]
    exige(v == 0, f"(2) filas de rastro sin huella: {v}")
    exige(not pathlib.Path(os.environ["RO_DB"]).exists(), "se abrió una SQLite en vez de la base de Postgres")
    exige(not (RAIZ / "despliegue" / "local.db").exists(), "se ha creado despliegue/local.db")

print(("✔ " if not fallos else "✘ ") + "N-20: " + ("todo bien" if not fallos else " · ".join(fallos)))
sys.exit(1 if fallos else 0)
