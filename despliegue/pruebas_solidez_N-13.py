#!/usr/bin/env python3
"""despliegue/pruebas_solidez_N-13.py · N-13: un JSON roto da 400 y un cuerpo enorme da 413, nunca 500.

Uso: python3 despliegue/pruebas_solidez_N-13.py [--puerto 8771] [--web 3000]
Lectura: los POST no llegan a escribir (el cuerpo se rechaza antes de la ruta). Por el legado y, si se pide, por la web.
Sale 0 si pasa. Sin datos reales en la salida.
"""
import argparse
import http.client
import json
import sys

ap = argparse.ArgumentParser()
ap.add_argument("--puerto", type=int, default=8771)
ap.add_argument("--web", type=int, default=0)
a = ap.parse_args()
fallos, n = [], 0


def ok(c, t):
    global n
    n += 1
    if not c:
        fallos.append(t)


def pedir(puerto, metodo, ruta, cuerpo=None, cabeceras=None):
    c = http.client.HTTPConnection("127.0.0.1", puerto, timeout=30)
    h = {"X-RO-App": "1", "X-RO-Yo": "tomas", "Origin": f"http://127.0.0.1:{puerto}"}
    h.update(cabeceras or {})
    try:
        c.request(metodo, ruta, body=cuerpo, headers=h)
        r = c.getresponse()
        txt = r.read().decode("utf-8", "replace")
        try:
            datos = json.loads(txt)
        except ValueError:
            datos = None
        return r.status, datos, txt
    except (ConnectionError, OSError) as e:      # el servidor cortó antes de leer el cuerpo
        return 0, None, str(e)
    finally:
        c.close()


JSON = {"Content-Type": "application/json"}
for nombre, puerto in [("legado", a.puerto)] + ([("web", a.web)] if a.web else []):
    s, d, t = pedir(puerto, "POST", "/api/preferencias", b"{roto", JSON)
    ok(s == 400 and (d or {}).get("error") == "JSON no válido", f"{nombre}: JSON roto → {s} {t[:60]!r} (esperaba 400 «JSON no válido»)")
    s, d, t = pedir(puerto, "POST", "/api/preferencias", b"\xff\xfe\x00{", JSON)
    ok(s == 400, f"{nombre}: bytes no UTF-8 → {s} (esperaba 400)")
    s, d, t = pedir(puerto, "POST", "/api/preferencias", b"a" * 250_000, JSON)
    ok(s in (413, 0) and s != 500, f"{nombre}: 250 000 bytes → {s} (esperaba 413)")
    if nombre == "legado":
        ok(s == 413 and (d or {}).get("error") == "Petición demasiado grande", f"{nombre}: 250 000 bytes → {s} {t[:60]!r} (esperaba 413 «Petición demasiado grande»)")
    s, d, t = pedir(puerto, "POST", "/api/preferencias", None, {**JSON, "Content-Length": "abc"})
    ok(s < 500 and s != 0 or nombre == "web", f"{nombre}: Content-Length no numérico → {s} (esperaba < 500)")
    s, d, t = pedir(puerto, "POST", "/api/preferencias", None, JSON)
    ok(s < 500 and s != 0, f"{nombre}: sin cuerpo → {s} (esperaba < 500)")
    s, d, t = pedir(puerto, "GET", "/api/sesion?yo=tomas")
    ok(s == 200, f"{nombre}: tras los cuerpos raros /api/sesion → {s} (esperaba 200)")

print(f"{'✘' if fallos else '✔'} N-13: {n} comprobaciones" + (" · " + " · ".join(fallos) if fallos else ""))
sys.exit(1 if fallos else 0)
