#!/usr/bin/env python3
"""migracion/pruebas_L-05.py · L-05: un account no recibe ficheros de módulo de un cliente que no lleva.

Uso: python3 migracion/pruebas_L-05.py --puerto 8771        (solo lectura; también vale 8770 y 3000)
Un account A (puesto account, sin dirección, con «solo su cartera») y un cliente ajeno C (de la lista de dirección que no
está en la cartera de A). Para cada familia de ficheros por cliente (`paneles/<fuente>/<cid>`, `informe/c_*/<cid>`):
  (1) A pide el fichero de C → 403 o 404, nunca 200, y el cuerpo no trae el id de C en un `cliente_id`;
  (2) A pide el de un cliente SUYO → 200 (no es un 403 general);
  (3) estática: `fnmatch` en servir.py solo por segmentos (`zip(segmentos, …)`), nunca sobre la ruta entera.
Sale 0 si pasa. Sin datos reales en la salida.
"""
import argparse
import http.client
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--puerto", type=int, default=8771)
a = ap.parse_args()
fallos = []
probadas = 0


def exige(c, t):
    if not c:
        fallos.append(t)


def pedir(ruta, yo):
    c = http.client.HTTPConnection("127.0.0.1", a.puerto, timeout=60)
    c.request("GET", ruta, headers={"X-RO-App": "1", "X-RO-Yo": yo, "Accept": "application/json"})
    r = c.getresponse()
    cuerpo = r.read()
    c.close()
    try:
        return r.status, json.loads(cuerpo or b"null"), cuerpo
    except ValueError:
        return r.status, None, cuerpo


s, elegir, _ = pedir("/api/elegir", "tomas")
exige(s == 200, f"elegir {s}")
personas = (elegir or {}).get("personas") or []
direccion = next((p["id"] for p in personas if "direccion" in (p.get("puestos") or [])), None)
exige(bool(direccion), "falta una persona de dirección")
cuenta = None
for p in personas:
    puestos = p.get("puestos") or []
    if "account" in puestos and "direccion" not in puestos and p.get("estado", "activo") == "activo":
        s, ses, _ = pedir("/api/sesion", p["id"])
        d = (ses or {}).get("datos") or {}
        if s == 200 and d.get("soloSuCartera") and d.get("carteraIds"):
            cuenta, cartera = p["id"], set(d["carteraIds"])
            break
exige(bool(cuenta), "no hay un account con cartera propia")
if direccion and cuenta:
    s, ses, _ = pedir("/api/sesion", direccion)
    todos = [c["id"] for c in ((ses or {}).get("datos") or {}).get("clientes", []) if isinstance(c, dict) and c.get("id")]
    ajenos = [c for c in todos if c not in cartera]
    suyos = [c for c in todos if c in cartera]
    exige(bool(ajenos) and bool(suyos), "falta un cliente ajeno o uno suyo")
    # familias de ficheros por cliente que existen en data/ (se leen solo los nombres)
    data = RAIZ / "data"
    familias = []
    for carpeta in sorted((data / "paneles").glob("*")):
        if carpeta.is_dir():
            familias.append(f"paneles/{carpeta.name}/{{cid}}")
    for carpeta in sorted((data / "informe").glob("c_*"))[:1]:
        familias.append(f"informe/{carpeta.name}/{{cid}}")
    for fam in familias:
        base = fam.replace("{cid}", "")
        ajeno = next((c for c in ajenos if (data / (base + c + ".json")).exists()), None)
        suyo = next((c for c in suyos if (data / (base + c + ".json")).exists()), None)
        if ajeno:
            s, cuerpo, crudo = pedir("/api/modulo/" + fam.format(cid=ajeno), cuenta)
            probadas += 1
            exige(s in (403, 404), f"{fam}: un cliente ajeno devuelve {s}")
            exige(s != 200 or ajeno.encode() not in crudo, f"{fam}: el cuerpo trae un cliente ajeno")
        if suyo:
            s, _, _ = pedir("/api/modulo/" + fam.format(cid=suyo), cuenta)
            exige(s == 200, f"{fam}: su propio cliente devuelve {s}")
    exige(probadas > 0, "ninguna familia de ficheros por cliente con un cliente ajeno para probar")

fuente = (RAIZ / "servir.py").read_text(encoding="utf-8")
for n, linea in enumerate(fuente.splitlines(), 1):
    if re.search(r"fnmatch(case)?\(", linea) and "zip(" not in linea and "segmentos" not in linea and "import" not in linea:
        # permitido solo si el patrón y la ruta llegan ya troceados
        exige(False, f"servir.py:{n} usa fnmatch sobre la ruta entera")

print(("✔ " if not fallos else "✘ ") + "L-05: " + (f"todo bien ({probadas} familias de ficheros por cliente probadas)" if not fallos else " · ".join(fallos)))
sys.exit(1 if fallos else 0)
