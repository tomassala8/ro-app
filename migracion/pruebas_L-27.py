#!/usr/bin/env python3
"""migracion/pruebas_L-27.py · L-27: ninguna ruta del Mac fuera de `config.py` en la tubería.

Uso: python3 migracion/pruebas_L-27.py
  (1) estática: ni `Path.home()`, ni `expanduser("~…")`, ni «/Users/» en los `.py` (salvo `config.py`, `migracion/`, los
      jueces `pruebas_*.py` / `despliegue/pruebas_*.py` y los `probar_*.py`/`planning_*.py` de la entrega, que son pruebas
      con rutas de su autor).
  (2) cada fichero tocado importa `config`.
  (3) dinámica, sin red ni llaves (solo módulos con `__main__`: `generar_dinero.py` y `generar_cuadre.py` se ejecutan al importar y NO se importan): con `RO_HOME=/tmp/…` varios módulos se importan y sus rutas cuelgan de esa raíz
      (prueba que `config.py` manda; en el Mac `RO_HOME` no existe y la ruta es la misma de siempre).
Sale 0 si pasa. Sin datos reales en la salida.
"""
import os
import pathlib
import re
import subprocess
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parents[1]
RX = re.compile(r"Path\.home\(\)|expanduser\(\s*f?['\"]~|/Users/")
EXCLUIDOS = ("migracion/", "node_modules/", "v2/", ".git/")
fallos, n = [], 0


def ok(c, t):
    global n
    n += 1
    if not c:
        fallos.append(t)


def es_py_a_revisar(rel):
    nombre = pathlib.PurePath(rel).name
    return (rel.endswith(".py") and not rel.startswith(EXCLUIDOS) and rel != "config.py"
            and not nombre.startswith(("pruebas_", "probar_", "planning_")))


ficheros = subprocess.run(["git", "ls-files", "*.py"], cwd=RAIZ, capture_output=True, text=True, check=True).stdout.split()
tocados = []
for rel in ficheros:
    if not es_py_a_revisar(rel):
        continue
    p = RAIZ / rel
    if not p.exists():
        continue
    for i, l in enumerate(p.read_text(errors="replace").splitlines(), 1):
        if RX.search(l):
            ok(False, f"{rel}:{i}")
    if "L-27" in p.read_text(errors="replace"):
        tocados.append(rel)
ok(True, "")
for rel in tocados:
    t = (RAIZ / rel).read_text()
    ok(bool(re.search(r"^\s*import config( as _cfg)?\b", t, re.M)), f"{rel} no importa config")

raiz_falsa = tempfile.mkdtemp(prefix="ro_l27_")
prog = r"""
import importlib, sys, pathlib
sys.path.insert(0, '.')
fals = pathlib.Path(sys.argv[1])
casos = [
  ('fuentes_equipo.generar_equipo', ['PLANTILLA', 'SALARIOS', 'CORREOS']),
  ('fuentes_mi_dia.generar_mi_dia', ['ROL_MILI']),
  ('fuentes_sueldos.generar_sueldos', ['ORIGEN']),
  ('fuentes_panel_direccion.generar_panel_direccion', ['ENTREGA']),
  ('fuentes_verdad.clientes_activos', ['LIBRO']),
  ('fuentes_ficha.agenda_md', ['MD']),
  ('fuentes_produccion.generar_marca', ['DESCARGAS']),
  ('fuentes_modular.generar_modular', ['HERR']),
  ('fuentes.comun', ['HOME']),
]
mal = []
for mod, nombres in casos:
    try:
        m = importlib.import_module(mod)
    except SystemExit:
        mal.append(mod + ' sale al importar'); continue
    except Exception as e:
        mal.append(f'{mod}: {type(e).__name__}'); continue
    for nom in nombres:
        v = getattr(m, nom, None)
        if v is None or not str(v).startswith(str(fals)):
            mal.append(f'{mod}.{nom} no cuelga de RO_HOME')
print('\n'.join(mal))
"""
env = {**os.environ, "RO_HOME": raiz_falsa, "RO_SIN_LLAVES": "1"}
for k in ("RO_CRUDOS", "RO_HERRAMIENTAS"):
    env.pop(k, None)
r = subprocess.run([sys.executable, "-c", prog, raiz_falsa], cwd=RAIZ, env=env, capture_output=True, text=True, check=False)
ok(r.returncode == 0, f"importar con RO_HOME falló (rc={r.returncode}): {r.stderr.strip()[-200:]}")
for l in r.stdout.strip().splitlines():
    ok(False, l)
print(f"{'✘' if fallos else '✔'} L-27: {n} comprobaciones" + "".join(" · " + x for x in fallos if x))
sys.exit(1 if fallos else 0)
