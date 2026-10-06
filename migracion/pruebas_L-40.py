#!/usr/bin/env python3
"""migracion/pruebas_L-40.py · L-40: «Más» en el menú de escritorio para los 21 puestos.

Uso: python3 migracion/pruebas_L-40.py [--puerto 8771]
Lanza `pruebas_L-40.mjs` (navegador, solo lectura, una persona por puesto). Sale 0 si pasa.
"""
import argparse
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--puerto", type=int, default=8771)
ap.add_argument("--grabar", action="store_true", help="guarda el total de pantallas del menú por puesto (antes del cambio)")
a = ap.parse_args()
orden = ["node", "migracion/pruebas_L-40.mjs", "--base", f"http://127.0.0.1:{a.puerto}"] + (["--grabar"] if a.grabar else [])
r = subprocess.run(orden, cwd=RAIZ, check=False)
sys.exit(r.returncode)
