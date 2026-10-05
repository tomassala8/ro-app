#!/usr/bin/env python3
"""migracion/pruebas_L-19.py · L-19: «hoy», el mes y la semana salen de ctx.hoy / ctx.fechas (Madrid), no del reloj del navegador.

Uso: python3 migracion/pruebas_L-19.py [--solo-estatica] [--base http://127.0.0.1:8771]
(1) Estática, sin servidor: en `modulos/*.js`, `permisos.js`, `ayudas.js`, `carcasa.js`, `app.js` están prohibidos
    `new Date().toISOString().slice(`, `new Date().getMonth()/getDate()/getFullYear()/getDay()`, `toLocaleDateString(` y
    `toLocaleTimeString(` sin `timeZone`, y una variable `hoy` que sea `new Date()`.
(2) Excepciones: lista de abajo, cada una con `fichero:trozo` y el motivo. Un uso nuevo que no esté en la lista falla.
(3) Navegador (si hay `--base` y no `--solo-estatica`): `pruebas_L-19.mjs` con el reloj en el límite de mes
    (31-oct 23:30 UTC = 1-nov en Madrid) en tres husos: el mes en curso tiene que ser noviembre en los tres.
Sale 0 si pasa. Sin datos reales.
"""
import argparse
import pathlib
import re
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--solo-estatica", action="store_true")
ap.add_argument("--base", default=None)
a = ap.parse_args()

PROHIBIDOS = [
    (re.compile(r"new Date\(\)\.toISOString\(\)\.slice\("), "new Date().toISOString().slice(… (UTC, no Madrid)"),
    (re.compile(r"new Date\(\)\.get(Month|Date|FullYear|Day)\(\)"), "new Date().get…() (zona del navegador)"),
    (re.compile(r"new Date\(\)\.toLocale(Date|Time)String\((?![^)]*timeZone)"), "toLocale…String sin timeZone"),
    (re.compile(r"\bhoy\s*=\s*new Date\(\)\s*[;,)]"), "variable «hoy» = new Date() (reloj del navegador)"),
]

# fichero → [(trozo de la línea, motivo)]. Un uso legítimo lleva aquí su motivo; no se amplía para que pase.
EXCEPCIONES = {
    "modulos/objetivos_comun.js": [("lunesDeHoy", "horaMadrid() convierte ese UTC a Madrid antes de sacar el lunes: ya es el lunes de Madrid")],
    "modulos/ficha.js": [("horaSeg", "solo pinta la hora de reloj de quien mira, con «segundos» de refresco: no decide ningún día")],
    "modulos/incidencias.js": [("creada: new Date().toISOString()", "«creada» de la base es UTC sin zona por convención (igual que horaMadrid): se guarda en UTC y se enseña en Madrid")],
    "modulos/mi_trabajo.js": [("toLocaleTimeString('es-ES')", "texto de la nota de una anotación local: hora de reloj de quien la hace, no decide un día")],
}

fallos = []
vistos = []
ficheros = sorted((RAIZ / "modulos").glob("*.js")) + [RAIZ / f for f in ("permisos.js", "ayudas.js", "carcasa.js", "app.js")]
for f in ficheros:
    if not f.exists():
        continue
    rel = f.relative_to(RAIZ).as_posix()
    for n, linea in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        for rx, que in PROHIBIDOS:
            if not rx.search(linea):
                continue
            ok = [m for t, m in EXCEPCIONES.get(rel, []) if t in linea]
            if ok:
                vistos.append(f"{rel}:{n} (excepción: {ok[0]})")
            else:
                fallos.append(f"{rel}:{n}: {que}  ·  {linea.strip()[:110]}")

print(f"  · excepciones usadas: {len(vistos)}")
for v in vistos:
    print(f"    - {v}")
print(f"  {'✔' if not fallos else '✘'} estática: {len(fallos)} usos de la zona del navegador fuera de la lista")
for x in fallos:
    print(f"    - {x}")

if a.base and not a.solo_estatica:
    r = subprocess.run(["node", str(RAIZ / "migracion" / "pruebas_L-19.mjs"), "--base", a.base], cwd=RAIZ)
    if r.returncode != 0:
        fallos.append("navegador: pruebas_L-19.mjs con el reloj en el límite de mes no sale 0")

if fallos:
    print(f"✘ L-19: {len(fallos)} fallos")
    sys.exit(1)
print("✔ L-19")
