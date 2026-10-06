#!/usr/bin/env python3
"""migracion/pruebas_L-49.py · L-49: ninguna ruta duplicada ni sin dueño; el service worker no cachea módulos.

Uso: python3 migracion/pruebas_L-49.py [--sin-nest] [--inventario]
Solo lectura de ficheros del repo (no arranca nada, no escribe). Sale 0 si pasa. Sin datos reales en la salida.
  (1) `migracion/inventario/rutas_api.json`: sin (método, ruta) repetidos; cada ruta exacta tiene en `servir.py`
      una rama por método (ni más ni menos); cada prefijo tiene su `startswith` en `servir.py`.
  (2) `v2/apps/api/src/legado/rutas-en-nest.ts`: ninguna ruta dos veces; con `pnpm … rutas-declaradas` en verde
      (se salta con --sin-nest).
  (3) `sw.js`: solo guarda navegaciones a «/» o «/index.html»; no cachea `modulos/*.js` ni la API.
  (4) inventario para la fase 6 (con --inventario; no falla por esto): módulos > 100 KB y funciones exportadas sin uso.
"""
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter

RAIZ = pathlib.Path(__file__).resolve().parents[1]
fallos = []
n = 0


def ok(cond, texto):
    global n
    n += 1
    if not cond:
        fallos.append(texto)


servir = (RAIZ / "servir.py").read_text(encoding="utf-8")
rutas = json.loads((RAIZ / "migracion/inventario/rutas_api.json").read_text(encoding="utf-8"))

# (1) rutas de la app de hoy
cuenta = Counter((r["metodo"], r["ruta"]) for r in rutas)
ok(not [k for k, v in cuenta.items() if v > 1], f"(1) entradas repetidas en el inventario: {[k for k, v in cuenta.items() if v > 1]}")
por_ruta = Counter(r["ruta"] for r in rutas if not r["prefijo"])
for ruta, metodos in sorted(por_ruta.items()):
    # `ruta == "/x"` o `ruta in ("/x", …)`: cada ocurrencia es una rama; debe haber una por método
    # (si la ruta va en una tupla, un `ruta == "/x"` dentro de esa rama es un reparto interno, no otra rama)
    en_tupla = len(re.findall(r'ruta in \([^)]*"%s"[^)]*\)' % re.escape(ruta), servir))
    ramas = en_tupla or len(re.findall(r'ruta == "%s"' % re.escape(ruta), servir))
    ok(ramas == metodos, f"(1) {ruta}: {ramas} ramas en servir.py para {metodos} método(s)")
for r in rutas:
    if r["prefijo"]:
        ok(re.search(r'startswith\("%s' % re.escape(r["ruta"]), servir) is not None, f"(1) prefijo {r['ruta']} sin startswith en servir.py")

# (2) Nest
nest = (RAIZ / "v2/apps/api/src/legado/rutas-en-nest.ts").read_text(encoding="utf-8")
lista = re.findall(r"\[\s*'(GET|POST|PUT|PATCH|DELETE)'\s*,\s*(/[^\n]*/)\s*\]", nest)
ok(len(lista) == len(set(lista)), f"(2) rutas repetidas en rutas-en-nest.ts: {[k for k, v in Counter(lista).items() if v > 1]}")
if "--sin-nest" not in sys.argv:
    r = subprocess.run("pnpm --filter @ro/api test -- rutas-declaradas", shell=True, cwd=RAIZ / "v2", capture_output=True, text=True)
    ok(r.returncode == 0, f"(2) rutas-declaradas rojo (rc={r.returncode}): {(r.stdout + r.stderr)[-300:]}")

# (3) service worker
sw = (RAIZ / "sw.js").read_text(encoding="utf-8")
ok("r.mode !== 'navigate'" in sw and "r.method !== 'GET'" in sw, "(3) sw.js debe ignorar lo que no sea una navegación GET")
ok("u.pathname !== '/' && u.pathname !== '/index.html'" in sw, "(3) sw.js debe limitarse a «/» y «/index.html»")
ok(not re.search(r"modulos/|/api/|\.js['\"]", re.sub(r"//[^\n]*", "", sw)), "(3) sw.js nombra módulos, API o ficheros .js en su código")

# (4) inventario para la fase 6
if "--inventario" in sys.argv:
    grandes = sorted(((p.stat().st_size // 1024, p.name) for p in (RAIZ / "modulos").glob("*.js") if p.stat().st_size > 100 * 1024), reverse=True)
    print("Módulos > 100 KB:", ", ".join(f"{nombre} {kb} KB" for kb, nombre in grandes))
    fuentes = [RAIZ / "app.js", RAIZ / "componentes.js", *sorted((RAIZ / "modulos").glob("*.js"))]
    textos = {p: p.read_text(encoding="utf-8", errors="replace") for p in fuentes}
    todo = "\n".join(textos.values())
    sin_uso = []
    for p, t in textos.items():
        for nombre in set(re.findall(r"export (?:async )?function (\w+)", t)):
            if len(re.findall(r"\b%s\b" % re.escape(nombre), todo)) == 1:
                sin_uso.append(f"{p.name}:{nombre}")
    print(f"Funciones exportadas sin uso en app.js, componentes.js y modulos/ ({len(sin_uso)}):", ", ".join(sorted(sin_uso)))

print(f"{'✘' if fallos else '✔'} L-49: {n} comprobaciones" + (" · " + " · ".join(fallos) if fallos else ""))
sys.exit(1 if fallos else 0)
