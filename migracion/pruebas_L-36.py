#!/usr/bin/env python3
"""migracion/pruebas_L-36.py · L-36: «Reabrir» (Gasto de IA) no rompe en «ver como» ni cuando la ruta falla.

Uso: python3 migracion/pruebas_L-36.py [--puerto 8771]
Lanza `pruebas_L-36.mjs` (navegador, solo lectura: la ruta de escritura se simula en el navegador y no llega al servidor).
Sale 0 si pasa. Sin datos reales en la salida.
"""
import argparse
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--puerto", type=int, default=8771)
a = ap.parse_args()
r = subprocess.run(["node", "migracion/pruebas_L-36.mjs", "--base", f"http://127.0.0.1:{a.puerto}"], cwd=RAIZ, check=False)
sys.exit(r.returncode)
