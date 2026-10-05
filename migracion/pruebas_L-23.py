#!/usr/bin/env python3
"""migracion/pruebas_L-23.py · L-23: «Avisar al equipo» está activo en la ficha de un cliente con equipo.

Uso: python3 migracion/pruebas_L-23.py [--puerto 8771]
Lanza `pruebas_L-23.mjs` (navegador, solo lectura): accounts con clientes suyos con equipo → botón `[data-avisar]` y
ninguno apagado; cliente suyo sin equipo → apagado. Sale 0 si pasa. Sin datos reales en la salida.
"""
import argparse
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--puerto", type=int, default=8771)
a = ap.parse_args()
r = subprocess.run(["node", "migracion/pruebas_L-23.mjs", "--base", f"http://127.0.0.1:{a.puerto}"], cwd=RAIZ, check=False)
sys.exit(r.returncode)
