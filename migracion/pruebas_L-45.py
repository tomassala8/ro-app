#!/usr/bin/env python3
"""migracion/pruebas_L-45.py · L-45: nombres de puesto coherentes y filtros de Decisiones sin nombres de persona.

Uso: python3 migracion/pruebas_L-45.py [--puerto 8771] [--volcar]
  (1) `reglas_permisos.json › puestos[].nombre`: los que empiezan por «Jef» usan la misma forma: «Jefatura de …» (Duda 23); solo
      cambia el texto: los `id` y la matriz no se tocan (se comparan con `git show HEAD:` salvo el nombre).
  (2) `modulos/decisiones.js`: `TIPO_TXT` y los chips de filtro no nombran a ninguna persona (alias de `/api/elegir`).
  (3) navegador (`pruebas_L-45.mjs`): en `#/decisiones` el chip «Para proyectos» solo sale a quien tiene alguna decisión de ese tipo;
      y `#vercomo-sel` no repite ningún `value`. Solo lectura.
Sale 0 si pasa.
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
ap.add_argument("--volcar", action="store_true")
a = ap.parse_args()
fallos, n = [], 0


def exige(c, t):
    global n
    n += 1
    if not c:
        fallos.append(t)


# (1) nombres de las jefaturas
reglas = json.loads((RAIZ / "reglas_permisos.json").read_text(encoding="utf-8"))
puestos = reglas.get("puestos") or {}
lista = list(puestos.items()) if isinstance(puestos, dict) else [(p.get("id"), p) for p in puestos]
jefes = {k: (v.get("nombre") or "") for k, v in lista if re.match(r"Jef", v.get("nombre") or "")}
exige(len(jefes) >= 3, f"debería haber 3 jefaturas con nombre y hay {len(jefes)}")
for k, nombre in jefes.items():
    exige(nombre.startswith("Jefatura de "), f"puesto {k}: «{nombre}» no empieza por «Jefatura de »")
if a.volcar:
    print("jefaturas:", jefes)
try:
    antes = json.loads(subprocess.run(["git", "show", "HEAD:reglas_permisos.json"], cwd=RAIZ, capture_output=True, text=True, check=True).stdout)


    def sin_nombres(o):
        if isinstance(o, dict):
            return {k: sin_nombres(v) for k, v in o.items() if not (k == "nombre" and isinstance(v, str) and v.startswith(("Jef",)))}
        if isinstance(o, list):
            return [sin_nombres(x) for x in o]
        return o


    ahora_sin = sin_nombres(reglas)
    antes_sin = sin_nombres(antes)
    exige(ahora_sin == antes_sin, "reglas_permisos.json cambia algo más que el nombre de las tres jefaturas (respecto a HEAD)")
except Exception as e:  # noqa: BLE001
    exige(False, f"no se pudo comparar con HEAD: {e}")

# (2) decisiones.js sin nombres de persona
elegir = json.load(urllib.request.urlopen(f"http://127.0.0.1:{a.puerto}/api/elegir", timeout=20))
alias = {str(p.get("alias") or "").strip() for p in elegir.get("personas", [])} | {str(p.get("nombre") or "").split(" ")[0] for p in elegir.get("personas", [])}
alias = {x for x in alias if len(x) >= 3}
src = (RAIZ / "modulos" / "decisiones.js").read_text(encoding="utf-8")
zonas = [l for l in src.splitlines() if l.startswith("const TIPO_TXT") or re.search(r"valor: 'para_(tomas|coti)'", l) or "TIPO_TXT[d.tipo] ||" in l]
exige(len(zonas) >= 4, f"no encuentro las líneas de TIPO_TXT y de los chips ({len(zonas)})")
for l in zonas:
    for nombre in sorted(alias):
        if re.search(rf"(?<![\wáéíóúñ]){re.escape(nombre)}(?![\wáéíóúñ])", l):
            exige(False, f"decisiones.js nombra a «{nombre}»: {l.strip()[:90]}")
exige("Para dirección · 48 h" in src and "Para proyectos · 24 h" in src, "TIPO_TXT no dice «Para dirección · 48 h» y «Para proyectos · 24 h»")

# (3) navegador
cmd = ["node", "migracion/pruebas_L-45.mjs", "--base", f"http://127.0.0.1:{a.puerto}"] + (["--volcar"] if a.volcar else [])
r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True, check=False)
print(r.stdout.strip()[-1200:])
exige(r.returncode == 0, "la parte de navegador falla")

print(f"{'✘' if fallos else '✔'} L-45: {n} comprobaciones{(' · ' + ' · '.join(fallos)) if fallos else ''}")
sys.exit(1 if fallos else 0)
