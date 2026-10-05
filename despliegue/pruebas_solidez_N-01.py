#!/usr/bin/env python3
"""despliegue/pruebas_solidez_N-01.py · N-01: toda lectura de API se guarda en la base propia (fuentes/lectura.py).

Uso:  python3 despliegue/pruebas_solidez_N-01.py [--con-lectores]
(1) `fuentes/probar_lectura.py` sobre SQLite temporal (RO_DB en ~/RO_MIGRACION/tmp/n01.db, se borra al acabar) sale 0.
(2) Lo mismo contra Postgres (`--pg`, base ro_esc) sale 0 y no deja filas `prueba_lectura%` en `fuente_lectura`.
(3) La vista `fuente_ultimo_bueno` se puede leer en Postgres.
(4) Los cinco lectores (seo, redes, crm, hostinger, paneles) importan `fuentes.lectura`. Solo cuenta con `--con-lectores`
    (se activa cuando N-02…N-06 están hechas); sin la opción, avisa.
Sin red ni llaves: la API es falsa. Sale 0 si pasa; si no, 1. Sin Postgres levantado, el punto (2)-(3) falla (no se salta).
"""
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PG = os.environ.get("RO_N01_PG", "postgresql://ro:ro@127.0.0.1:5432/ro_esc")
CON_LECTORES = "--con-lectores" in sys.argv
fallos = []


def ok(txt):
    print(f"  ✔ {txt}")


def mal(txt):
    print(f"  ✘ {txt}")
    fallos.append(txt)


def correr(args, env_extra=None, quitar=()):
    env = {k: v for k, v in os.environ.items() if k not in quitar}
    env.update(env_extra or {})
    return subprocess.run(args, cwd=RAIZ, env=env, capture_output=True, text=True, timeout=240)


def cola(r):
    return ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-6:]


# (1) SQLite temporal
tmp = Path.home() / "RO_MIGRACION" / "tmp"
tmp.mkdir(parents=True, exist_ok=True)
db = tmp / "n01.db"
db.unlink(missing_ok=True)
try:
    r = correr([sys.executable, "fuentes/probar_lectura.py"], {"RO_DB": str(db)}, quitar=("DATABASE_URL",))
    if r.returncode == 0:
        ok("probar_lectura.py sobre SQLite sale 0")
    else:
        mal("probar_lectura.py sobre SQLite no sale 0: " + " | ".join(cola(r)))
finally:
    db.unlink(missing_ok=True)

# (2) Postgres
r = correr([sys.executable, "fuentes/probar_lectura.py", "--pg"], {"DATABASE_URL": PG})
if r.returncode == 0:
    ok("probar_lectura.py --pg sobre Postgres sale 0")
else:
    mal("probar_lectura.py --pg no sale 0: " + " | ".join(cola(r)))


def psql(sql):
    return subprocess.run(["psql", PG, "-tAc", sql], capture_output=True, text=True, timeout=60)


q = psql("select count(*) from fuente_lectura where fuente like 'prueba_lectura%'")
if q.returncode == 0 and q.stdout.strip() == "0":
    ok("no deja filas de prueba en fuente_lectura")
else:
    mal(f"fuente_lectura: filas de prueba o error ({q.stdout.strip() or q.stderr.strip()[:120]})")

# (3) la vista
q = psql("select count(*) from fuente_ultimo_bueno")
if q.returncode == 0:
    ok("la vista fuente_ultimo_bueno se lee")
else:
    mal("fuente_ultimo_bueno no se puede leer: " + q.stderr.strip()[:160])

# (4) los lectores
lectores = ["fuentes_seo/generar_seo.py", "fuentes_redes/generar_redes.py", "fuentes_crm/generar_crm.py",
            "fuentes_hostinger/generar_hostinger.py", "fuentes_paneles/generar_paneles.py"]
sin = []
for f in lectores:
    p = RAIZ / f
    if not p.exists() or "fuentes.lectura" not in p.read_text(encoding="utf-8", errors="replace"):
        sin.append(f)
if not sin:
    ok("los cinco lectores usan fuentes.lectura")
elif CON_LECTORES:
    mal("lectores sin fuentes.lectura: " + ", ".join(sin))
else:
    print("  · aviso: aún no usan fuentes.lectura (N-02…N-06): " + ", ".join(sin))

if fallos:
    print(f"\n✘ N-01: {len(fallos)} fallo(s)")
    sys.exit(1)
print("\n✔ N-01")
