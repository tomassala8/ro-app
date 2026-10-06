#!/usr/bin/env python3
"""migracion/pruebas_L-41.py · L-41: cada llave que falta sale una vez y sin órdenes de terminal.

Uso: python3 migracion/pruebas_L-41.py [--puerto 8771]
Lanza `pruebas_L-41.mjs` (navegador, solo lectura: dirección en Mi día, Conexiones y Alertas). Sale 0 si pasa.
"""
import argparse
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--puerto", type=int, default=8771)
ap.add_argument("--volcar", action="store_true")
a = ap.parse_args()
orden = ["node", "migracion/pruebas_L-41.mjs", "--base", f"http://127.0.0.1:{a.puerto}"] + (["--volcar"] if a.volcar else [])
r = subprocess.run(orden, cwd=RAIZ, check=False)
sys.exit(r.returncode)
