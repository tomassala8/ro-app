#!/usr/bin/env python3
"""migracion/pruebas_L-37.py · L-37: la campana («Avisos y menciones») y el contador de «Alertas» no se confunden.

Uso: python3 migracion/pruebas_L-37.py [--puerto 8771]
Lanza `pruebas_L-37.mjs` (navegador, solo lectura, dirección y account en `#/mi-dia`). Sale 0 si pasa.
"""
import argparse
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--puerto", type=int, default=8771)
a = ap.parse_args()
r = subprocess.run(["node", "migracion/pruebas_L-37.mjs", "--base", f"http://127.0.0.1:{a.puerto}"], cwd=RAIZ, check=False)
sys.exit(r.returncode)
