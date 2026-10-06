#!/usr/bin/env python3
"""migracion/pruebas_L-43.py · L-43: quien no ve la cuota ve «Horas por cliente», no «Dinero por cliente».

Uso: python3 migracion/pruebas_L-43.py [--puerto 8771] [--volcar]
Lanza `pruebas_L-43.mjs` (navegador, solo lectura: trafficker, account, jefa de publicidad, proyectos+account y dirección). Sale 0 si pasa.
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
orden = ["node", "migracion/pruebas_L-43.mjs", "--base", f"http://127.0.0.1:{a.puerto}"] + (["--volcar"] if a.volcar else [])
sys.exit(subprocess.run(orden, cwd=RAIZ, check=False).returncode)
