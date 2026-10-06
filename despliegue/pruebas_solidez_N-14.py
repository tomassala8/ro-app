#!/usr/bin/env python3
"""despliegue/pruebas_solidez_N-14.py · N-14: todas las llaves salen de `config.secreto()`; el chat del equipo no muere al importar.

Uso: python3 despliegue/pruebas_solidez_N-14.py       (sin red, sin llavero: pone RO_SIN_LLAVES=1 ella misma y aborta si no está)
(1) ningún fichero de `fuentes*` ni `despliegue` (salvo `config.py`) llama a `security find-generic-password`;
(2) con RO_SIN_LLAVES=1 y `subprocess` saboteado (si algo toca el llavero, salta): `hay_clave`, `_token`, `_clave`,
    `PSI_CLAVE` devuelven vacío sin tocar el llavero; el chat del equipo, en una copia temporal (sin `data/` real),
    termina limpio («Sin llaves esta noche») y sin traceback; `config.secreto` con una carpeta de claves falsa
    devuelve None y, con `obligatorio`, sale;
(3) los tres generadores que no se pueden importar sin ejecutarse (dinero, outreach, comprobar) leen por `secreto()`.
El orden carpeta → variable → .env → llavero NO se comprueba esta noche (necesita la barrera abierta): prueba de día.
Sin datos reales en la salida.
"""
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

os.environ["RO_SIN_LLAVES"] = "1"      # la barrera de la noche: no se quita, ni «solo en la prueba»
if os.environ.get("RO_SIN_LLAVES") != "1":
    sys.exit("N-14: sin RO_SIN_LLAVES=1 no se ejecuta")
RAIZ = pathlib.Path(__file__).resolve().parents[1]
fallos, n = [], 0


def ok(c, t):
    global n
    n += 1
    if not c:
        fallos.append(t)


# (1) ni una llamada al llavero fuera de config.py
patron = re.compile(r"find-generic-password")
permitidos = {"despliegue/pruebas_noche.py", "despliegue/pruebas_solidez_N-14.py"}        # el llavero de mentira de la noche (juez) y esta prueba
sueltas = []
for carpeta in sorted(p for p in RAIZ.iterdir() if p.is_dir() and (p.name.startswith("fuentes") or p.name == "despliegue")):
    for f in carpeta.rglob("*.py"):
        rel = f.relative_to(RAIZ).as_posix()
        if "__pycache__" in rel or rel in permitidos:
            continue
        for i, linea in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if patron.search(linea) and "add-generic-password" not in linea:
                sueltas.append(f"{rel}:{i}")
ok(not sueltas, "(1) llamadas al llavero fuera de config.py: " + ", ".join(sueltas))

# (2) con el llavero saboteado
SABOTAJE = """
import subprocess, sys
class Llavero(BaseException): pass
def _no(*a, **k): raise Llavero('N-14: llavero')
subprocess.check_output = subprocess.run = subprocess.Popen = _no
sys.path[:0] = [{raiz!r}, {raiz!r} + '/fuentes', {raiz!r} + '/fuentes_paneles', {raiz!r} + '/fuentes_modular']
"""
CASOS = [
    ("f_windsor.hay_clave", "import f_windsor; r = f_windsor.hay_clave(); sys.exit(0 if r is False else 3)"),
    ("f_meta_directo._token", "import f_meta_directo; r = f_meta_directo._token(); sys.exit(0 if not r else 3)"),
    ("acceso._clave", "import acceso; r = acceso._clave(); sys.exit(0 if not r else 3)"),
    ("generar_paneles.PSI_CLAVE", "import generar_paneles as G; r = G.PSI_CLAVE(); sys.exit(0 if not r else 3)"),
]
entorno = dict(os.environ, RO_SIN_LLAVES="1", PYTHONDONTWRITEBYTECODE="1")
for nombre, codigo in CASOS:
    r = subprocess.run([sys.executable, "-c", SABOTAJE.format(raiz=str(RAIZ)) + codigo], cwd=RAIZ, env=entorno, capture_output=True, text=True)
    ok(r.returncode == 0, f"(2) {nombre}: rc={r.returncode} {(r.stderr or r.stdout).strip()[-160:]}")

with tempfile.TemporaryDirectory(prefix="n14_") as t:
    t = pathlib.Path(t)
    shutil.copytree(RAIZ / "fuentes_chat_equipo", t / "fuentes_chat_equipo", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(RAIZ / "config.py", t / "config.py")
    (t / "data").mkdir()
    (t / "data" / "personas.json").write_text("[]", encoding="utf-8")
    (t / "data" / "clientes.json").write_text("[]", encoding="utf-8")
    cod = SABOTAJE.format(raiz=str(t)) + "import runpy; runpy.run_path(%r, run_name='generar_chat_equipo')" % str(t / "fuentes_chat_equipo" / "generar_chat_equipo.py")
    r = subprocess.run([sys.executable, "-c", cod], cwd=t, env=entorno, capture_output=True, text=True)
    salida = r.stdout + r.stderr
    ok("Traceback" not in salida and "Llavero" not in salida and "CalledProcessError" not in salida,
       f"(2) chat del equipo importado: {salida.strip()[-200:]}")
    ok("Sin llaves esta noche" in salida, f"(2) chat del equipo: sin el aviso de «Sin llaves esta noche»: {salida.strip()[-120:]}")
    ok(not (t / "data" / "chat_equipo").exists(), "(2) chat del equipo escribió datos sin llave")

    carpeta = t / "claves"
    carpeta.mkdir()
    (carpeta / "clickup_api_token").write_text("falsa_n14\n", encoding="utf-8")
    cod = ("import sys, os; sys.path.insert(0, %r); import config as C\n"
           "assert C.secreto('clickup_api_token') is None\n"
           "try:\n    C.secreto('clickup_api_token', obligatorio=True)\nexcept SystemExit:\n    sys.exit(0)\nsys.exit(5)\n") % str(RAIZ)
    r = subprocess.run([sys.executable, "-c", cod], cwd=t, env=dict(entorno, RO_SECRETOS_DIR=str(carpeta)), capture_output=True, text=True)
    ok(r.returncode == 0, f"(2) config.secreto con una carpeta falsa: rc={r.returncode} {r.stderr.strip()[-160:]}")

# (3) los generadores que se ejecutan al importarse
leer = lambda ruta: (RAIZ / ruta).read_text(encoding="utf-8")
ok("_cfg.secreto('airtable_token')" in leer("fuentes_dinero/generar_dinero.py"), "(3) generar_dinero no lee airtable_token por secreto()")
ok("config.secreto('anthropic_api_key')" in leer("fuentes_ventas/generar_outreach.py"), "(3) generar_outreach no lee anthropic_api_key por secreto()")
ok('_cfg.secreto("meta_token")' in leer("fuentes/comprobar.py"), "(3) comprobar no lee meta_token por secreto()")

print(f"{'✘' if fallos else '✔'} N-14: {n} comprobaciones" + (" · " + " · ".join(fallos) if fallos else ""))
sys.exit(1 if fallos else 0)
