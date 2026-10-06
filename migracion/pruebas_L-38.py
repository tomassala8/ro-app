#!/usr/bin/env python3
"""migracion/pruebas_L-38.py · L-38: textos de pantalla sin códigos internos, y «Fase 2» solo para dirección.

Uso: python3 migracion/pruebas_L-38.py [--puerto 8771]
     python3 migracion/pruebas_L-38.py --guardar-antes --puerto 8770   (graba `modulos_puestos` de la app de hoy, solo la primera vez)
Casos:
  (1) estática: en `modulos/indice.js`, dentro de cada `resumen:`, ni códigos de obra (W1, D-09, E0…), ni «101 firmadas»,
      ni nombres de personas (los `alias`/`nombre` de /api/elegir). Lista blanca de un solo elemento: M365.
  (2) `modulos_puestos`: en `indice.js`, todo lo que no es el `resumen` queda idéntico al de HEAD (permisos.py lo lee con
      expresiones regulares); y `/api/sesion › modulos_puestos` de los 21 puestos, igual que el fichero grabado si existe.
  (3) navegador (solo lectura): un account no ve «Fase 2» en la Bandeja ni en el pie de los indicadores; dirección sí.
Sale 0 si pasa. Solo recuentos en la salida.
"""
import argparse
import http.client
import json
import pathlib
import re
import subprocess
import sys
import unicodedata

RAIZ = pathlib.Path(__file__).resolve().parents[1]
TMP = pathlib.Path.home() / "RO_MIGRACION" / "tmp"
ANTES = TMP / "l38_antes.json"

ap = argparse.ArgumentParser()
ap.add_argument("--puerto", type=int, default=8771)
ap.add_argument("--guardar-antes", action="store_true")
a = ap.parse_args()
fallos = []
hechos = 0


def exige(cond, texto):
    global hechos
    hechos += 1
    if not cond:
        fallos.append(texto)


def pedir(ruta, yo=None):
    c = http.client.HTTPConnection("127.0.0.1", a.puerto, timeout=90)
    cab = {"X-RO-App": "1", "Accept": "application/json"}
    if yo:
        cab["X-RO-Yo"] = yo
    c.request("GET", ruta, headers=cab)
    r = c.getresponse()
    datos = r.read()
    c.close()
    try:
        return r.status, json.loads(datos or b"null")
    except ValueError:
        return r.status, None


def plano(t):
    return unicodedata.normalize("NFD", t).encode("ascii", "ignore").decode().lower()


# ------------------------------------------------------------------ (1) estática
indice = (RAIZ / "modulos" / "indice.js").read_text(encoding="utf-8")
RE_RESUMEN = re.compile(r"resumen:\s*'((?:[^'\\]|\\.)*)'")
resumenes = RE_RESUMEN.findall(indice)
exige(len(resumenes) >= 40, f"se leen pocos resumen: ({len(resumenes)})")
RE_CODIGO = re.compile(r"\b[WDGCEMPBI]-?\d{1,3}\b")
for t in resumenes:
    for m in RE_CODIGO.finditer(t):
        if m.group(0) != "M365":
            exige(False, f"código de obra «{m.group(0)}» en un resumen")
    exige("101 firmadas" not in t, "«101 firmadas» fijo en un resumen")
    exige(not re.search(r"\bE0\b", t), "«E0» en un resumen")
    exige(not re.search(r"fase 2", t, re.I), "«fase 2» en un resumen")

s, elegir = pedir("/api/elegir")
exige(s == 200 and isinstance(elegir, dict), f"/api/elegir → {s}")
personas = (elegir or {}).get("personas") or []
nombres = set()
for p in personas:
    for k in ("alias", "nombre"):
        v = (p.get(k) or "").strip()
        if len(v) >= 3:
            nombres.add(plano(v))
            nombres.add(plano(v.split()[0]))
nombres = {n for n in nombres if len(n) >= 3}
for t in resumenes:
    for n in nombres:
        if re.search(rf"\b{re.escape(n)}\b", plano(t)):
            exige(False, f"nombre «{n}» en un resumen: {t[:50]}")
exige(len(nombres) >= 10, f"se leen pocos nombres ({len(nombres)})")

# ------------------------------------------------------------------ (2) lo que lee permisos.py no cambia
def sin_resumen(texto):
    return RE_RESUMEN.sub("resumen: ''", texto)


try:
    head = subprocess.run(["git", "show", "HEAD:modulos/indice.js"], cwd=RAIZ, capture_output=True, text=True, check=True).stdout
    exige(sin_resumen(head) == sin_resumen(indice), "indice.js cambia algo más que los resumen: respecto a HEAD")
except subprocess.CalledProcessError:
    exige(False, "no se pudo leer indice.js de HEAD")

s, ses = pedir("/api/sesion", "tomas")
exige(s == 200 and isinstance(ses, dict), f"/api/sesion → {s}")
mp = (ses or {}).get("modulos_puestos")
exige(isinstance(mp, dict) and len(mp) >= 21, f"modulos_puestos de {len(mp or {})} puestos, no de 21 o más")
if a.guardar_antes:
    TMP.mkdir(parents=True, exist_ok=True)
    if not ANTES.exists():
        ANTES.write_text(json.dumps(mp, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        print("l38_antes.json grabado")
elif ANTES.exists():
    exige(json.loads(ANTES.read_text(encoding="utf-8")) == json.loads(json.dumps(mp)), "modulos_puestos distinto del grabado antes")

# ------------------------------------------------------------------ (3) navegador
r = subprocess.run(["node", "migracion/pruebas_L-38.mjs", "--base", f"http://127.0.0.1:{a.puerto}"], cwd=RAIZ, capture_output=True, text=True)
salida = (r.stdout or "").strip().splitlines()
print(salida[-1] if salida else r.stderr[-300:])
exige(r.returncode == 0, "la prueba del navegador falla")

print(f"{'✘' if fallos else '✔'} L-38: {hechos} comprobaciones" + (" · " + " · ".join(sorted(set(fallos))) if fallos else ""))
sys.exit(1 if fallos else 0)
