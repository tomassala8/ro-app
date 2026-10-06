#!/usr/bin/env python3
"""migracion/pruebas_L-24.py · L-24: entrar sin acceso o con la app caída da un mensaje claro, sin nombres ni órdenes.

Uso: python3 migracion/pruebas_L-24.py [--puerto 8771]
Lanza `pruebas_L-24.mjs` (navegador, solo lectura): persona desconocida → «No tienes acceso» (o el selector), API caída →
«La app no responde»; sin «Cargando…», sin texto técnico y sin nombres de persona. Sale 0 si pasa.
"""
import argparse
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--puerto", type=int, default=8771)
a = ap.parse_args()
r = subprocess.run(["node", "migracion/pruebas_L-24.mjs", "--base", f"http://127.0.0.1:{a.puerto}"], cwd=RAIZ, check=False)
sys.exit(r.returncode)
