#!/usr/bin/env python3
"""migracion/pruebas_L-20.py · L-20: el año y el mes de los generadores salen de hoy (Madrid), no de un 2026 fijo.

Uso: python3 migracion/pruebas_L-20.py [--base http://127.0.0.1:8771]
(1) Sin servidor, con RO_RELOJ (un proceso por reloj): `fuentes.comun.fecha("02-10 07:00")` sin año usa el año de hoy;
    `generar_informes.mes_de_texto` también; `CLAVE_MES` trae el mes en curso y el anterior; `ultimos_meses(3)` acaba hoy.
    Con el reloj del 5-oct-2026 todo da lo mismo que antes (2026, jul…oct, ago-sep-oct): el texto de hoy no cambia.
(2) Con `--base`: `pruebas_L-20.mjs` (navegador, hoy = 3-nov y 5-oct: los rótulos de «mes anterior» siguen a hoy).
Los rótulos de datos con su propio periodo (clave `sep`/`octubre`, «muestra de septiembre», «Cierre de septiembre») no se tocan.
Sale 0 si pasa. Sin datos reales.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--base", default=None)
a = ap.parse_args()
fallos = []

CODIGO = r"""
import json, sys
sys.path.insert(0, 'fuentes'); sys.path.insert(0, 'fuentes_informes')
import comun, generar_informes as g
print(json.dumps({
  'anio_fecha': comun.fecha('02-10 07:00').year,
  'anio_fecha_explicito': comun.fecha('02-10 07:00', anio=2020).year,
  'mes_texto': g.mes_de_texto('informe de septiembre'),
  'mes_texto_explicito': g.mes_de_texto('informe de septiembre', anio=2020),
  'claves': g.CLAVE_MES,
  'ultimos3': g.ultimos_meses(3),
  'ciclo': g.mes_anterior(__import__('datetime').date(2026, 10, 5)),
}))
"""


def con_reloj(reloj):
    env = {**os.environ, "RO_RELOJ": reloj}
    env.pop("DATABASE_URL", None)
    r = subprocess.run([sys.executable, "-c", CODIGO], cwd=RAIZ, env=env, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        fallos.append(f"{reloj}: no arranca ({r.stderr.strip().splitlines()[-1] if r.stderr.strip() else r.returncode})")
        return None
    return json.loads(r.stdout.strip().splitlines()[-1])


def exige(cond, texto):
    if not cond:
        fallos.append(texto)


hoy = con_reloj("2026-10-05T07:30")
if hoy:
    exige(hoy["anio_fecha"] == 2026, f"2026-10-05: fecha() da {hoy['anio_fecha']}, debía dar 2026")
    exige(hoy["mes_texto"] == "2026-09", f"2026-10-05: mes_de_texto da {hoy['mes_texto']}, debía dar 2026-09")
    exige(hoy["claves"] == {"2026-07": "jul", "2026-08": "ago", "2026-09": "sep", "2026-10": "oct"}, f"2026-10-05: CLAVE_MES cambió: {hoy['claves']}")
    exige(hoy["ultimos3"] == ["2026-08", "2026-09", "2026-10"], f"2026-10-05: ultimos_meses(3) = {hoy['ultimos3']}")
    exige(hoy["anio_fecha_explicito"] == 2020 and hoy["mes_texto_explicito"] == "2020-09", "el año explícito ya no se respeta")
nov = con_reloj("2026-11-03T09:00")
if nov:
    exige(nov["anio_fecha"] == 2026, "2026-11-03: fecha() sin año debía dar 2026")
    exige("2026-11" in nov["claves"] and "2026-10" in nov["claves"], f"2026-11-03: CLAVE_MES sin el mes en curso y el anterior: {list(nov['claves'])}")
    exige(nov["claves"].get("2026-11") == "nov", "2026-11-03: la clave de noviembre no es «nov»")
    exige(nov["ultimos3"] == ["2026-09", "2026-10", "2026-11"], f"2026-11-03: ultimos_meses(3) = {nov['ultimos3']}")
ene = con_reloj("2027-01-05T09:00")
if ene:
    exige(ene["anio_fecha"] == 2027, f"2027-01-05: fecha() da {ene['anio_fecha']}, debía dar 2027")
    exige(ene["mes_texto"] == "2027-09", f"2027-01-05: mes_de_texto da {ene['mes_texto']}, debía dar 2027-09")
    exige(ene["ultimos3"] == ["2026-11", "2026-12", "2027-01"], f"2027-01-05: ultimos_meses(3) = {ene['ultimos3']}")
    exige(list(ene["claves"]) == ["2026-10", "2026-11", "2026-12", "2027-01"], f"2027-01-05: CLAVE_MES = {list(ene['claves'])}")
print(f"  {'✔' if not fallos else '✘'} Python con tres relojes (5-oct-2026, 3-nov-2026, 5-ene-2027)")

if a.base:
    r = subprocess.run(["node", str(RAIZ / "migracion" / "pruebas_L-20.mjs"), "--base", a.base], cwd=RAIZ)
    if r.returncode != 0:
        fallos.append("navegador: pruebas_L-20.mjs no sale 0")

if fallos:
    print(f"✘ L-20: {len(fallos)} fallos")
    for f in fallos:
        print(f"  - {f}")
    sys.exit(1)
print("✔ L-20")
