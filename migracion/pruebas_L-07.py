#!/usr/bin/env python3
"""migracion/pruebas_L-07.py · L-07: HEAD y OPTIONS no cuelan datos ni ficheros.

Uso: python3 migracion/pruebas_L-07.py --puerto 8771        (solo lectura; vale 8771 y 3000)
HEAD a `/data/_privado/x.json`, `/local.db`, `/api/sesion` y `/` → 405, sin cuerpo, sin `Last-Modified`, con
`Content-Length` 0 si lo lleva. OPTIONS a `/api/sesion` → 405 (o 501 por el servidor de Python), nunca 200.
Sale 0 si pasa. Sin datos.
"""
import argparse
import http.client
import sys

ap = argparse.ArgumentParser()
ap.add_argument("--puerto", type=int, default=8771)
a = ap.parse_args()
fallos = []


def pedir(metodo, ruta):
    c = http.client.HTTPConnection("127.0.0.1", a.puerto, timeout=30)
    c.request(metodo, ruta, headers={"X-RO-App": "1", "X-RO-Yo": "tomas", "Accept": "application/json"})
    r = c.getresponse()
    cuerpo = r.read()
    cab = {k.lower(): v for k, v in r.getheaders()}
    c.close()
    return r.status, cab, cuerpo


for ruta in ("/data/_privado/x.json", "/local.db", "/api/sesion", "/"):
    s, cab, cuerpo = pedir("HEAD", ruta)
    if s != 405:
        fallos.append(f"HEAD {ruta} → {s} (debe ser 405)")
    if cuerpo:
        fallos.append(f"HEAD {ruta} trae cuerpo")
    if "last-modified" in cab:
        fallos.append(f"HEAD {ruta} enseña Last-Modified")
    if cab.get("content-length", "0") not in ("0", ""):
        fallos.append(f"HEAD {ruta} con Content-Length {cab['content-length']}")
s, cab, cuerpo = pedir("OPTIONS", "/api/sesion")
if s not in (405, 501):
    fallos.append(f"OPTIONS /api/sesion → {s} (debe ser 405 o 501)")
if b"datos" in cuerpo:
    fallos.append("OPTIONS /api/sesion devuelve datos")
print(("✔ " if not fallos else "✘ ") + f"L-07 (puerto {a.puerto}): " + ("todo bien" if not fallos else " · ".join(fallos)))
sys.exit(1 if fallos else 0)
