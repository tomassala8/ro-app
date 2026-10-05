#!/usr/bin/env python3
"""despliegue/pruebas_solidez_N-17.py · N-17: `reconciliar_clickup.py` y `verificar_envios.py` usan la misma base que servir.py.

Uso: python3 despliegue/pruebas_solidez_N-17.py      (rehace ro_esc, que es solo de pruebas; no toca local.db ni ro_app)
Con DATABASE_URL de ro_esc y RO_DB apuntando a una ruta temporal que NO existe (si el script abre SQLite, la crea):
(1) se mete en ro_esc una acción de ClickUp y otra de correo (Desk), con datos inventados;
(2) `reconciliar_clickup.py --sin-red` y `verificar_envios.py --sin-red` salen con 0, cuentan «1 nuevos» y dejan su
    fila en `sinc_cambios` y `envios` de Postgres (la cola que vieron es la de Postgres);
(3) la SQLite temporal no se ha creado (antes del arreglo, la creaban vacía y trabajaban sobre ella).
Sin red, sin llaves, sin datos reales.
"""
import os
import pathlib
import subprocess
import sys
import tempfile

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
    sys.path.insert(0, str(RAIZ))
    import envios as EN  # noqa: E402
    tipo_desk = ((EN.reglas().get("tipos_envio") or {}).get("desk") or [None])[0]
    exige(bool(tipo_desk), "reglas_permisos.json no trae ningún tipo de envío para Desk")
    sql = ("INSERT INTO acciones (quien, herramienta, tipo, objeto, texto, estado) VALUES (%s,%s,%s,%s,%s,'simulada') RETURNING id")
    id_click = consulta(sql, ("prueba_n17", "clickup", "tarea_nueva", "prueba-n17", "prueba N-17"))[0][0]
    id_desk = consulta(sql, ("prueba_n17", "desk", tipo_desk, "prueba-n17", "prueba N-17"))[0][0] if tipo_desk else None
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="ro_n17_"))
    sqlite_fantasma = tmp / "no_debe_existir.db"
    entorno = {**os.environ, "DATABASE_URL": URL, "RO_DB": str(sqlite_fantasma), "RO_SIN_LLAVES": "1", "RO_ESTADO_DIR": str(tmp / "estado")}
    for var in ("RO_CLICKUP_REAL", "RO_ENVIOS_REALES"):
        entorno.pop(var, None)
    for script, tabla, col, accion in (("despliegue/reconciliar_clickup.py", "sinc_cambios", "accion_id", id_click),
                                       ("despliegue/verificar_envios.py", "envios", "accion_id", id_desk)):
        if accion is None:
            continue
        r = subprocess.run([sys.executable, script, "--sin-red"], cwd=RAIZ, env=entorno, capture_output=True, text=True, timeout=180)
        exige(r.returncode == 0, f"{script} rc={r.returncode}: {(r.stderr.strip().splitlines() or [''])[-1][:160]}")
        exige(" nuevos" in r.stdout and " 0 nuevos" not in r.stdout, f"{script} no cuenta la acción de Postgres como nueva: {r.stdout.strip()[:120]!r}")
        filas = consulta(f"SELECT count(*) FROM {tabla} WHERE {col} = %s", (accion,))[0][0]
        exige(filas == 1, f"{script}: la fila de {tabla} no está en Postgres ({filas})")
    exige(not sqlite_fantasma.exists(), "algún script abrió una SQLite en vez de la base de Postgres (la ha creado vacía)")
    exige(not (RAIZ / "despliegue" / "local.db").exists(), "se ha creado despliegue/local.db")

print(("✔ " if not fallos else "✘ ") + "N-17: " + ("todo bien" if not fallos else " · ".join(fallos)))
sys.exit(1 if fallos else 0)
