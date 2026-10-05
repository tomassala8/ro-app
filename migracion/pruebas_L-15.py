#!/usr/bin/env python3
"""migracion/pruebas_L-15.py · L-15: la IA real exige dos llaves (RO_IA_REAL=si e interruptor firmado), no basta la clave.

Uso: python3 migracion/pruebas_L-15.py        (sin servidor ni red; la clave es una cadena inventada)
(1) Con `ANTHROPIC_API_KEY` falsa y sin `RO_IA_REAL`: `ia_real_559.autorizada()` es falso, `ia.clave()` devuelve None y el
    gasto está en modo «reglas».
(2) Con `RO_IA_REAL=si` pero sin interruptor, con uno de otra persona, con `ia_real` falso o con JSON repetido: sigue falso.
(3) Control: con `RO_IA_REAL=si` y un interruptor `{ia_real: true, activado_por: "tomas"}` en una carpeta temporal: verdadero.
(4) Estática: `ia.py` y `ia_gasto.py` consultan `IA_REAL.autorizada()`.
Sale 0 si pasa. Nunca se hace una petición ni se leen llaves reales.
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parents[1]
TMP = pathlib.Path.home() / "RO_MIGRACION" / "tmp"
TMP.mkdir(parents=True, exist_ok=True)

HIJO = r'''
import json, os, pathlib, sys
sys.path.insert(0, sys.argv[1])
carpeta = pathlib.Path(sys.argv[2])
import ia_real_559 as R
fallos = []
interruptor = carpeta / "interruptor.json"
R.INTERRUPTOR = interruptor
os.environ.pop("RO_IA_REAL", None)
interruptor.write_text(json.dumps({"ia_real": True, "activado_por": "tomas"}))
if R.autorizada(): fallos.append("sin RO_IA_REAL, con interruptor firmado: autorizada")
import ia
if ia.clave() is not None: fallos.append("sin RO_IA_REAL, ia.clave() devuelve la clave")
os.environ["RO_IA_REAL"] = "si"
interruptor.unlink()
if R.autorizada(): fallos.append("RO_IA_REAL=si sin interruptor: autorizada")
for nombre, contenido in (("de otra persona", {"ia_real": True, "activado_por": "alguien"}), ("ia_real falso", {"ia_real": False, "activado_por": "tomas"}), ("sin firma", {"ia_real": True})):
    interruptor.write_text(json.dumps(contenido))
    if R.autorizada(): fallos.append(f"interruptor {nombre}: autorizada")
interruptor.write_text('{"ia_real": false, "ia_real": true, "activado_por": "tomas"}')
if R.autorizada(): fallos.append("interruptor con clave repetida: autorizada")
interruptor.write_text(json.dumps({"ia_real": True, "activado_por": "tomas"}))
if not R.autorizada(): fallos.append("control: las dos llaves no autorizan")
os.environ.pop("RO_IA_REAL")
import ia_gasto as G
if G.estado().get("modo") != "reglas" if hasattr(G, "estado") else False: fallos.append("ia_gasto no está en modo reglas sin RO_IA_REAL")
print(json.dumps(fallos))
'''

fallos = []
tmp = pathlib.Path(tempfile.mkdtemp(prefix="l15_", dir=TMP))
try:
    entorno = {k: v for k, v in os.environ.items() if k not in ("DATABASE_URL", "RO_IA_REAL")}
    entorno.update({"ANTHROPIC_API_KEY": "clave_falsa_l15", "RO_SIN_LLAVES": "1", "RO_DB": str(tmp / "x.db")})
    p = subprocess.run([sys.executable, "-c", HIJO, str(RAIZ), str(tmp)], capture_output=True, text=True, env=entorno, cwd=tmp, timeout=120)
    if p.returncode != 0:
        fallos.append("el proceso de prueba falló: " + p.stderr[-300:].replace("\n", " | "))
    else:
        fallos += json.loads(p.stdout.strip().splitlines()[-1])
finally:
    for f in tmp.glob("*"):
        f.unlink(missing_ok=True)
    tmp.rmdir()

for nombre in ("ia.py", "ia_gasto.py"):
    if "IA_REAL.autorizada()" not in (RAIZ / nombre).read_text(encoding="utf-8"):
        fallos.append(f"{nombre} no consulta IA_REAL.autorizada()")

print(("✔ " if not fallos else "✘ ") + "L-15: " + ("todo bien" if not fallos else " · ".join(fallos)))
sys.exit(1 if fallos else 0)
