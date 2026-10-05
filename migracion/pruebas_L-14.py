#!/usr/bin/env python3
"""migracion/pruebas_L-14.py · L-14: el rastro, el historial y las huellas no se cambian ni se vacían (SQLite y Postgres).

Uso: python3 migracion/pruebas_L-14.py        (escribe solo en ro_esc y en una copia temporal de local.db.antes)
(1) SQLite: sobre una copia, `INSERT OR REPLACE` de una fila existente de `registro` falla con `recursive_triggers` ON y OFF;
    UPDATE y DELETE fallan; el recuento no cambia.
(2) Postgres (`ro_esc`, tras `base-limpia`): UPDATE, DELETE, TRUNCATE y un INSERT de id existente fallan en `registro`,
    `registro_huellas` e `historial` (UPDATE/DELETE solo si hay filas); el recuento no cambia.
(3) La migración de permisos de L-14 existe (REVOKE sobre las tres tablas).
Sale 0 si pasa. Sin datos reales.
"""
import pathlib
import shutil
import sqlite3
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
TMP = pathlib.Path.home() / "RO_MIGRACION" / "tmp"
ANTES = pathlib.Path.home() / "RO_MIGRACION" / "local.db.antes"
URL = "postgresql://ro:ro@127.0.0.1:5432/ro_esc"
fallos = []


def exige(c, t):
    if not c:
        fallos.append(t)


# (1) SQLite
TMP.mkdir(parents=True, exist_ok=True)
copia = TMP / "l14.db"
shutil.copy(ANTES, copia)
copia.chmod(0o644)
# el esquema con sus disparadores lo crea `iniciar_base()` de servir.py, igual que al arrancar la app
entorno = {k: v for k, v in __import__("os").environ.items() if k != "DATABASE_URL"}
entorno.update({"RO_DB": str(copia), "RO_SIN_LLAVES": "1"})
iniciar = subprocess.run([sys.executable, "-c", "import servir; servir.iniciar_base()"], cwd=RAIZ, env=entorno, capture_output=True, text=True)
exige(iniciar.returncode == 0, "no pude abrir la copia con conectar(): " + iniciar.stderr[-120:].replace("\n", " | "))
try:
    for recursivos in ("ON", "OFF"):
        con = sqlite3.connect(copia)
        con.execute(f"PRAGMA recursive_triggers = {recursivos}")
        n0 = con.execute("SELECT count(*) FROM registro").fetchone()[0]
        for sql, nombre in (
            ("INSERT OR REPLACE INTO registro SELECT * FROM registro WHERE id=(SELECT min(id) FROM registro)", "INSERT OR REPLACE"),
            ("UPDATE registro SET id=id WHERE id=(SELECT min(id) FROM registro)", "UPDATE"),
            ("DELETE FROM registro WHERE id=(SELECT min(id) FROM registro)", "DELETE"),
        ):
            try:
                con.execute(sql)
                con.commit()
                fallos.append(f"SQLite ({recursivos}): {nombre} sobre registro NO falla")
            except sqlite3.Error:
                con.rollback()
        n1 = con.execute("SELECT count(*) FROM registro").fetchone()[0]
        exige(n0 == n1 and n0 > 0, f"SQLite ({recursivos}): el recuento cambió {n0} → {n1}")
        con.close()
finally:
    copia.unlink(missing_ok=True)

# (2) Postgres
limpia = subprocess.run([sys.executable, "migracion/contrato_escritura.py", "base-limpia", "ro_esc"], cwd=RAIZ, capture_output=True, text=True)
exige(limpia.returncode == 0, f"base-limpia ro_esc rc={limpia.returncode}")
psql = shutil.which("psql")
exige(bool(psql), "falta psql")


def sql(orden):
    p = subprocess.run([psql, URL, "-v", "ON_ERROR_STOP=1", "-tAc", orden], capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


if limpia.returncode == 0 and psql:
    for tabla in ("registro", "registro_huellas", "historial"):
        rc, n0 = sql(f"SELECT count(*) FROM {tabla}")
        exige(rc == 0, f"no puedo contar {tabla}")
        con_filas = rc == 0 and n0.isdigit() and int(n0) > 0
        pruebas = [("TRUNCATE", f"TRUNCATE {tabla}")]
        if con_filas:
            pruebas += [
                ("UPDATE", f"UPDATE {tabla} SET id=id WHERE id=(SELECT min(id) FROM {tabla})"),
                ("DELETE", f"DELETE FROM {tabla} WHERE id=(SELECT min(id) FROM {tabla})"),
                ("INSERT de id existente", f"INSERT INTO {tabla} SELECT * FROM {tabla} WHERE id=(SELECT min(id) FROM {tabla})"),
            ]
        for nombre, orden in pruebas:
            rc, salida = sql(orden)
            exige(rc != 0, f"Postgres: {nombre} sobre {tabla} NO falla ({salida[:60]})")
        rc, n1 = sql(f"SELECT count(*) FROM {tabla}")
        exige(n0 == n1, f"Postgres: el recuento de {tabla} cambió {n0} → {n1}")

# (3) migración de permisos
carpetas = sorted((RAIZ / "v2/packages/db/prisma/migrations").glob("*l14*"))
exige(bool(carpetas), "falta la migración l14_revoke_rastro")
for c in carpetas:
    texto = (c / "migration.sql").read_text(encoding="utf-8").upper()
    exige("REVOKE UPDATE, DELETE, TRUNCATE" in texto and all(t.upper() in texto for t in ("registro", "historial", "registro_huellas")), "la migración no revoca sobre las tres tablas")

print(("✔ " if not fallos else "✘ ") + "L-14: " + ("todo bien" if not fallos else " · ".join(fallos)))
sys.exit(1 if fallos else 0)
