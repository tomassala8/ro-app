#!/usr/bin/env python3
"""migracion/pruebas_L-17.py · L-17: en modo local, una cabecera de Access sin sello no acredita identidad.

Uso: python3 migracion/pruebas_L-17.py --puerto 8771 [--web 3000]        (solo lectura)
(1) `GET /api/sesion` con `Cf-Access-Authenticated-User-Email` y sin `X-RO-Yo` ni `?yo=`: 401, nunca 200.
(2) Con `X-RO-Yo` de dirección y `X-Forwarded-For` de documentación: 200 (no se rechaza `X-Forwarded-*`, lo ponen Next y Nest).
(3) Lo mismo de (1) por la web (3000), si responde; si no, se anota y se sigue.
(4) Estática: `_quien` y `host_ok` de `servir.py` siguen exigiendo `peer[0]` en 127.0.0.1/::1 (dos líneas hoy).
La prueba N9 de `pruebas_seguridad.py` (juez) la cambia Tomás de día. Sale 0 si pasa. Sin datos reales.
"""
import argparse
import http.client
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--puerto", type=int, default=8771)
ap.add_argument("--web", type=int, default=3000)
a = ap.parse_args()
fallos = []
notas = []


def exige(cond, texto):
    if not cond:
        fallos.append(texto)


def pedir(puerto, ruta, **cab):
    c = http.client.HTTPConnection("127.0.0.1", puerto, timeout=60)
    cab = {"X-RO-App": "1", "Origin": "http://127.0.0.1:3000", "Accept": "application/json", **cab}
    c.request("GET", ruta, headers=cab)
    r = c.getresponse()
    datos = r.read()
    c.close()
    try:
        return r.status, json.loads(datos or b"null")
    except ValueError:
        return r.status, {}


ACCESS = {"Cf-Access-Authenticated-User-Email": "persona@ejemplo.test"}
s, d = pedir(a.puerto, "/api/elegir")
exige(s == 200, f"elegir {s}")
direccion = next((p["id"] for p in (d or {}).get("personas") or [] if "direccion" in (p.get("puestos") or [])), None)
exige(direccion is not None, "no hay ninguna persona de dirección para el control")

s, _ = pedir(a.puerto, "/api/sesion", **ACCESS)
exige(s == 401, f"legado: Access sin sello y sin X-RO-Yo da {s}, no 401")
s, _ = pedir(a.puerto, "/api/sesion?yo=" + "nadie_l17", **ACCESS)
exige(s in (401, 403), f"legado: Access sin sello con ?yo= inexistente da {s}")
if direccion:
    s, _ = pedir(a.puerto, "/api/sesion", **{"X-RO-Yo": direccion, "X-Forwarded-For": "203.0.113.9", **ACCESS})
    exige(s == 200, f"legado: X-RO-Yo válido con X-Forwarded-For da {s}, no 200")

try:
    s, _ = pedir(a.web, "/api/sesion", **ACCESS)
    exige(s == 401, f"web: Access sin sello y sin X-RO-Yo da {s}, no 401")
except OSError:
    notas.append(f"web {a.web} sin responder: no se prueba")

texto = (RAIZ / "servir.py").read_text(encoding="utf-8")
exige("if not servidor and (not isinstance(peer, (tuple, list)) or not peer or peer[0] not in ('127.0.0.1', '::1')):" in texto,
      "servir.py › _quien: ya no exige peer local cuando no hay Access")
exige(texto.count("peer[0] not in ('127.0.0.1', '::1')") >= 2, "servir.py: falta la comprobación de peer local de host_ok")

print(("✔ " if not fallos else "✘ ") + "L-17: " + ("todo bien" if not fallos else " · ".join(fallos)) + (" (" + "; ".join(notas) + ")" if notas else ""))
sys.exit(1 if fallos else 0)
