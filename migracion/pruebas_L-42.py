#!/usr/bin/env python3
"""migracion/pruebas_L-42.py · L-42: el Asistente IA dice el número y la fecha del dato, no «40 correos» ni «2-oct» fijos.

Uso: python3 migracion/pruebas_L-42.py [--puerto 8771] [--volcar]
Lanza `pruebas_L-42.mjs` (navegador, solo lectura, dirección en `#/asistente-ia`). Sale 0 si pasa.
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
orden = ["node", "migracion/pruebas_L-42.mjs", "--base", f"http://127.0.0.1:{a.puerto}"] + (["--volcar"] if a.volcar else [])
sys.exit(subprocess.run(orden, cwd=RAIZ, check=False).returncode)
