#!/usr/bin/env python3
"""migracion/pruebas_L-26.py · L-26: todo por `ctx`/API y saneado del panel con lista blanca.

Uso: python3 migracion/pruebas_L-26.py [--puerto 8771]
  (1) `fetch(` en `modulos/*.js` solo en piezas comunes (`_*.js`, y ahí solo comentarios o ninguno).
  (2) `panel_direccion.js` no pide `reglas_permisos.json`; `/api/sesion` trae `almacenes_privados` (solo nombres,
      sin contenido) y `app.js` expone `ctx.almacenesPrivados`.
  (3) `parsear()` con lista blanca (navegador, `pruebas_L-26.mjs`).
  (4) las acciones de ventas llevan `modulo`: `app.js` lo añade siempre en `ctx.accion`.
Sale 0 si pasa. Sin datos reales en la salida.
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys
import urllib.request

RAIZ = pathlib.Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--puerto", type=int, default=8771)
a = ap.parse_args()
fallos, n = [], 0


def ok(c, t):
    global n
    n += 1
    if not c:
        fallos.append(t)


# (1)
for f in sorted((RAIZ / "modulos").glob("*.js")):
    for i, l in enumerate(f.read_text().splitlines(), 1):
        if re.search(r"\bfetch\(", l) and not l.lstrip().startswith(("*", "//", "/*")) and "fetch('data/…')" not in l:
            ok(f.name.startswith("_") and False, f"fetch( en modulos/{f.name}:{i}")
ok(True, "")
# (2)
pd = (RAIZ / "modulos" / "panel_direccion.js").read_text()
ok("reglas_permisos.json" not in re.sub(r"//.*", "", pd), "panel_direccion.js sigue pidiendo reglas_permisos.json")
ok("ctx.almacenesPrivados" in pd, "panel_direccion.js no usa ctx.almacenesPrivados")
ok("almacenesPrivados:" in (RAIZ / "app.js").read_text(), "app.js no expone ctx.almacenesPrivados")
try:
    elegir = json.load(urllib.request.urlopen(f"http://127.0.0.1:{a.puerto}/api/elegir", timeout=30))
    dir_ = next(p for p in elegir["personas"] if "direccion" in p.get("puestos", []) and p.get("estado", "activo") == "activo")
    rq = urllib.request.Request(f"http://127.0.0.1:{a.puerto}/api/sesion", headers={"X-RO-App": "1", "X-RO-Yo": dir_["id"]})
    s = json.load(urllib.request.urlopen(rq, timeout=60))
    al = s.get("almacenes_privados")
    ok(isinstance(al, list) and all(isinstance(x, str) for x in al), "/api/sesion no trae almacenes_privados como lista de nombres")
    ok(any(x.startswith("sueldos/") for x in (al or [])), "almacenes_privados no declara sueldos/")
    ok(not any(k in json.dumps(al) for k in ("tipo", "modulos", "dueno")), "almacenes_privados trae algo más que nombres")
except Exception as e:  # noqa: BLE001
    ok(False, f"/api/sesion: {type(e).__name__}")
# (3)
r = subprocess.run(["node", "migracion/pruebas_L-26.mjs", "--base", f"http://127.0.0.1:{a.puerto}"], cwd=RAIZ, capture_output=True, text=True, check=False)
print(r.stdout.strip())
ok(r.returncode == 0, "navegador: saneado de parsear()")
# (4)
ap_js = (RAIZ / "app.js").read_text()
ok("cuerpo: { modulo, ...a }" in ap_js, "ctx.accion no añade `modulo` siempre")

print(f"{'✘' if fallos else '✔'} L-26: {n} comprobaciones" + ("".join(" · " + x for x in fallos if x)))
sys.exit(1 if fallos else 0)
