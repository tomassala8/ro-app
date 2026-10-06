#!/usr/bin/env python3
"""migracion/pruebas_L-48.py · L-48: la documentación no contradice el código (estática, sin servidor).

Uso: python3 migracion/pruebas_L-48.py
Comprueba afirmaciones concretas que se pueden verificar leyendo ficheros (no reescribe ni juzga el estilo):
  1. `LEEME.md` nombra `tuberia_avisos` (el nombre de F2.1) y no habla de una «tabla avisos» de la tubería.
  2. Toda ruta `/api/…` citada en `LEEME.md` existe: en `migracion/inventario/rutas_api.json` (exacta o con prefijo) o
     escrita en algún `.py` del servidor de la raíz.
  3. Todo `modulos/*.js` citado en `LEEME.md` existe.
  4. El docstring de `servir.py` no dice «sin do_HEAD», ni «solo tres rutas dejan rastro», ni «Sin nada: Tomás»
     (sin identidad el servidor da 401, `servir.py › _quien`), y el de `permisos.py` no cita rutas que ya no existen.
  5. `modulos/indice.js › envios`: el resumen no promete envíos reales mientras `envios.py` esté en simulación.
  6. `LEEME.md` tiene una sección «Fechas».
Sale 0 si pasa.
"""
import glob
import json
import os
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
os.chdir(RAIZ)
fallos, n = [], 0


def ok(cond, txt):
    global n
    n += 1
    if not cond:
        fallos.append(txt)


def leer(ruta):
    return (RAIZ / ruta).read_text(encoding="utf-8", errors="ignore")


leeme = leer("LEEME.md")

# 1 · tuberia_avisos
ok("tuberia_avisos" in leeme, "(1) LEEME.md no nombra `tuberia_avisos`")
ok(not re.search(r"tabla `?avisos`?\b", leeme, re.I) or re.search(r"tabla `?avisos`?[^.\n]*(app|E0|persona)", leeme, re.I),
   "(1) LEEME.md habla de una «tabla avisos» sin decir de cuál")

# 2 · rutas citadas
inv = json.loads(leer("migracion/inventario/rutas_api.json"))
exactas = {r["ruta"] for r in inv if not r.get("prefijo")}
prefijos = [r["ruta"] for r in inv if r.get("prefijo") and r["ruta"] != "/api/"]   # «/api/» a secas lo cubriría todo
servidor = "".join(
    pathlib.Path(f).read_text(encoding="utf-8", errors="ignore")
    for f in glob.glob("*.py") if not f.startswith(("pruebas_", "probar_")))
citadas = set()
for m in re.finditer(r"/api/[A-Za-z0-9_/<>{}.-]*", leeme):
    c = re.sub(r"/<[^>]+>", "", m.group(0).rstrip(".-/"))
    if len(c) > len("/api/"):
        citadas.add(c)
sin_dueno = sorted(c for c in citadas if not (c in exactas or any(c.startswith(p) for p in prefijos) or c in servidor))
ok(len(citadas) >= 20, f"(2) la prueba solo vio {len(citadas)} rutas citadas: algo cambió en LEEME.md")
ok(not sin_dueno, f"(2) rutas de LEEME.md que no existen: {', '.join(sin_dueno[:6])}")

# 3 · módulos citados
faltan = sorted(m for m in set(re.findall(r"modulos/([A-Za-z0-9_]+\.js)", leeme)) if not (RAIZ / "modulos" / m).exists())
ok(not faltan, f"(3) módulos de LEEME.md que no existen: {', '.join(faltan[:6])}")

# 4 · docstrings
def docstring(ruta, hasta=60):
    return "\n".join(leer(ruta).splitlines()[:hasta])


doc_servir = docstring("servir.py")
doc_permisos = docstring("permisos.py", 35)
for frase in ("sin do_HEAD", "solo tres rutas dejan rastro", "Sin nada: Tomás"):
    ok(frase.lower() not in doc_servir.lower(), f"(4) el docstring de servir.py dice «{frase}»")
for m in re.finditer(r"/api/[A-Za-z0-9_/]+", doc_permisos):
    ruta = m.group(0)
    ok(ruta in exactas or any(ruta.startswith(p) for p in prefijos) or ruta in servidor.replace(doc_permisos, ""),
       f"(4) el docstring de permisos.py cita {ruta}, que ya no existe")
ok("do_HEAD" in leer("servir.py"), "(4) servir.py ya no tiene do_HEAD (la prueba L-07 debería haberlo visto)")

# 5 · envíos
indice = leer("modulos/indice.js")
m = re.search(r"id: 'envios'.*?resumen: '([^']*)'", indice, re.S)
ok(bool(m), "(5) no se encuentra la entrada `envios` en indice.js")
if m:
    envios_py = leer("envios.py")
    simulacion = "interruptor" in envios_py.lower() and "simula" in envios_py.lower()
    ok(simulacion, "(5) envios.py ya no habla de simulación ni de interruptor: revisa el resumen de `envios`")
    ok(not re.search(r"se envía|manda el correo", m.group(1), re.I), "(5) el resumen de `envios` promete envíos reales")
    ok("simulación" in m.group(1).lower(), "(5) el resumen de `envios` no dice que hoy es una simulación")

# 6 · sección Fechas
ok(re.search(r"^#{1,4} .*Fechas", leeme, re.M) is not None, "(6) LEEME.md no tiene una sección «Fechas»")

print(f"{'✘' if fallos else '✔'} L-48: {n} comprobaciones" + (" · " + " · ".join(fallos) if fallos else ""))
sys.exit(1 if fallos else 0)
