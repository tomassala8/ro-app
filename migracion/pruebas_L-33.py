#!/usr/bin/env python3
"""migracion/pruebas_L-33.py · L-33: el tile de reunión de la ficha sigue la verdad única («sin reunión el mes pasado»), no 30/35 días.

Uso: python3 migracion/pruebas_L-33.py [--puerto 8771]
(1) Estática: en `ficha.js` el `semaforo(rd.dias_sin_reunion` de 30/35 días solo de respaldo, tras `estadoReunionVerdad`.
(2) Navegador: `pruebas_L-33.mjs` (ficha y En rojo con el mismo color; no toca datos).
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
for i, linea in enumerate(js, 1):
    # El umbral 30/35 días solo vale de respaldo, detrás de la verdad: `estReu !== null ? … :` o `estadoReunionVerdad(F) ?? …`.
    previo = " ".join(js[max(0, i - 3):i])
    if re.search(r"semaforo\(\s*rd\.dias_sin_reunion", linea) and not re.search(r"estReu\s*!==\s*null|estadoReunionVerdad\(F\)", previo):
        fallos.append(f"ficha.js:{i}: el color de la reunión sale del umbral 30/35 días: {linea.strip()[:90]}")
print(f"  {'✔' if not fallos else '✘'} estática: el umbral de 30/35 días solo queda de respaldo detrás de la verdad")

r = subprocess.run(["node", str(RAIZ / "migracion" / "pruebas_L-33.mjs"), "--base", f"http://127.0.0.1:{a.puerto}"], cwd=RAIZ)
if r.returncode != 0:
    fallos.append("navegador: pruebas_L-33.mjs no sale 0")
if fallos:
    print(f"✘ L-33: {len(fallos)} fallos")
    for f in fallos:
        print(f"  - {f}")
    sys.exit(1)
print("✔ L-33")
