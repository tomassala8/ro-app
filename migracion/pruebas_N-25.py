#!/usr/bin/env python3
"""migracion/pruebas_N-25.py · N-25: el caso 8.2 de permisos-regresion no ejecuta escrituras reales.

Uso: python3 migracion/pruebas_N-25.py
Solo lee el spec (no llama a ningún servidor, no escribe). Falla si:
  (1) falta la constante NO_SE_LLAMAN o no tiene su comentario con el porqué;
  (2) alguna ruta POST del inventario que NO_SE_LLAMAN excluye pasaría al bucle de 8.2 (se simula el filtro);
  (3) el bucle de 8.2 no corta (`break`) en el primer POST que no es 403, o no salta las rutas de NO_SE_LLAMAN;
  (4) falta el caso 8.2b que comprueba la guarda sin llamar a las rutas.
Sale 0 si pasa. Sin datos reales.
"""
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
SPEC = RAIZ / "v2/apps/api/test/permisos-regresion.e2e-spec.ts"
INV = RAIZ / "migracion/inventario/rutas_api.json"
OBLIGATORIOS = ["recarga", "alta", "envio", "correo", "publicar", "tuberia", "importar", "sincron", "exportar", "llave"]

fallos = []
t = SPEC.read_text(encoding="utf-8")

m = re.search(r"/\*\*(?:(?!\*/).)*?\*/\s*const NO_SE_LLAMAN = \[(.*?)\];", t, re.S)
if not m:
    fallos.append("falta `const NO_SE_LLAMAN` con su comentario /** … */ delante")
    trozos = []
else:
    trozos = re.findall(r"'([^']+)'", m.group(1))
    if not re.search(r"escritura real", m.group(0)):
        fallos.append("el comentario de NO_SE_LLAMAN no explica por qué (falta «escritura real»)")
    for o in OBLIGATORIOS:
        if o not in trozos:
            fallos.append(f"NO_SE_LLAMAN no incluye «{o}»")
    for o in ("/api/recarga", "/api/altas/"):
        if o not in trozos:
            fallos.append(f"NO_SE_LLAMAN no incluye «{o}»")

posts = [r["ruta"] for r in json.loads(INV.read_text(encoding="utf-8")) if r["metodo"] == "POST"]
excluidas = [r for r in posts if any(x in r.lower() for x in trozos)]
if "/api/recarga" not in excluidas:
    fallos.append("/api/recarga no queda excluida del bucle de 8.2")

# El cuerpo del caso 8.2: desde `it('8.2 ` hasta `it('8.2b`.
c = re.search(r"it\('8\.2 .*?(?=it\('8\.2b)", t, re.S)
if not c:
    fallos.append("no encuentro el caso 8.2 (o falta el 8.2b detrás)")
else:
    cuerpo = c.group(0)
    if "noSeLlama(ruta)" not in cuerpo or not re.search(r"if \(noSeLlama\(ruta\)\) continue;", cuerpo):
        fallos.append("el bucle de 8.2 no salta las rutas de NO_SE_LLAMAN")
    pedidas = re.findall(r"pedir\('POST'", cuerpo)
    if len(pedidas) != 1:
        fallos.append(f"8.2 debe tener un único POST dentro del bucle (tiene {len(pedidas)})")
    if cuerpo.index("noSeLlama(ruta)") > cuerpo.index("pedir('POST'"):
        fallos.append("el filtro de NO_SE_LLAMAN va DESPUÉS del POST")
    # tras la comprobación de «no bloqueada» tiene que haber un break
    if not re.search(r"if \(!bloqueada\) \{[^}]*break;", cuerpo, re.S):
        fallos.append("el bucle de 8.2 no corta (`break`) al primer POST que no es 403")
    if "noBloqueadas.push" in cuerpo:
        fallos.append("8.2 sigue acumulando todas las rutas (`noBloqueadas.push`): una escritura por ruta")
    if re.search(r"/api/recarga|/api/altas", cuerpo):
        fallos.append("8.2 nombra a mano una ruta de NO_SE_LLAMAN")

if "it('8.2b" not in t:
    fallos.append("falta el caso 8.2b (guarda global sin llamar a las rutas)")
else:
    b = t[t.index("it('8.2b"):]
    b = b[: b.index("\n  it(", 10)] if "\n  it(" in b[10:] else b
    if "pedir(" in b:
        fallos.append("8.2b llama a una ruta con `pedir(`: no debe")
    if "permisos.guard.ts" not in b or "servir.py" not in b:
        fallos.append("8.2b no lee la guarda de Nest y la de servir.py")

if fallos:
    for f in fallos:
        print("✘ N-25 ·", f)
    sys.exit(1)
print(f"✔ N-25 · {len(trozos)} trozos en NO_SE_LLAMAN, {len(excluidas)} de {len(posts)} rutas POST excluidas del bucle; 8.2 corta al primer fallo")
