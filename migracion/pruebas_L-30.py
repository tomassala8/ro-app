#!/usr/bin/env python3
"""migracion/pruebas_L-30.py · L-30: «clientes bien» de Mi día sale de una sola regla (la gravedad de la verdad única).

Uso: python3 migracion/pruebas_L-30.py [--puerto 8771]
(1) Estática: `mi_dia_bloques.js` no decide «bien» por un umbral de salud (`salud >= 60` y parecidos) y la cuenta de «bien» sale de `grav`.
(2) Navegador (`pruebas_L-30.mjs`): todas las cifras «N bien» de Mi día coinciden para dirección y para un account.
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

js = (RAIZ / "modulos" / "mi_dia_bloques.js").read_text(encoding="utf-8")
for i, linea in enumerate(js.splitlines(), 1):
    if re.search(r"salud\w*\s*(>=|>|<=|<)\s*(60|40)\b", linea):
        fallos.append(f"mi_dia_bloques.js:{i}: umbral de salud 60/40 escrito a mano: {linea.strip()[:100]}")
cuentas = re.findall(r"n\('bien'\)", js)
if len(cuentas) != 1:
    fallos.append(f"se esperaba una sola cuenta n('bien') por gravedad y hay {len(cuentas)}")
print(f"  {'✔' if not fallos else '✘'} estática: sin umbral de salud y una sola cuenta de «bien» por gravedad")

r = subprocess.run(["node", str(RAIZ / "migracion" / "pruebas_L-30.mjs"), "--base", f"http://127.0.0.1:{a.puerto}"], cwd=RAIZ)
if r.returncode != 0:
    fallos.append("navegador: pruebas_L-30.mjs no sale 0")

if fallos:
    print(f"✘ L-30: {len(fallos)} fallos")
    for f in fallos:
        print(f"  - {f}")
    sys.exit(1)
print("✔ L-30")
