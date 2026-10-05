#!/usr/bin/env python3
"""migracion/pruebas_L-32.py · L-32: sin account en la verdad única, la ficha dice «sin account · para confirmar» (no pinta el de la Cartera).

Uso: python3 migracion/pruebas_L-32.py [--puerto 8771]
(1) Estática: en `ficha.js` ningún `responsable || 'sin account'` fuera de `quienLleva` (la verdad manda; la Cartera solo de respaldo).
(2) Navegador: `pruebas_L-32.mjs` (verdad real con un cliente puesto sin account; no toca datos).
Sale 0 si pasa. Sin datos reales.
"""
import argparse
import pathlib
import re
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--puerto", type=int, default=8771)
a = ap.parse_args()
fallos = []

js = (RAIZ / "modulos" / "ficha.js").read_text(encoding="utf-8").splitlines()
dentro = False
for i, linea in enumerate(js, 1):
    if linea.startswith("function quienLleva"):
        dentro = True
    elif dentro and linea.startswith("}"):
        dentro = False
        continue
    if not dentro and re.search(r"responsable\s*\|\|\s*'sin account'", linea):
        fallos.append(f"ficha.js:{i}: respaldo a la Cartera fuera de quienLleva: {linea.strip()[:90]}")
print(f"  {'✔' if not fallos else '✘'} estática: el respaldo a la Cartera solo vive en quienLleva")

r = subprocess.run(["node", str(RAIZ / "migracion" / "pruebas_L-32.mjs"), "--base", f"http://127.0.0.1:{a.puerto}"], cwd=RAIZ)
if r.returncode != 0:
    fallos.append("navegador: pruebas_L-32.mjs no sale 0")
if fallos:
    print(f"✘ L-32: {len(fallos)} fallos")
    for f in fallos:
        print(f"  - {f}")
    sys.exit(1)
print("✔ L-32")
