#!/usr/bin/env python3
"""migracion/pruebas_L-29.py · L-29: el estado de alertas vive en data/alertas/_estado, fuera del repo.

Uso: python3 migracion/pruebas_L-29.py     (sin red; solo escribe en ~/RO_MIGRACION/tmp)
  (1) `fuentes_alertas/estado_alertas.json` no está en git y sigue en .gitignore.
  (2) `despliegue/pasos.json` ya no lo nombra como salida del paso `alertas` (la carpeta `data/alertas` la cubre).
  (3) la ruta por defecto cae dentro de `data/alertas/_estado/` (`ESTADO` de `generar_alertas.py` sin variables).
  (4) migración: sin estado nuevo y con el viejo, `main()` hereda «desde» y cerradas; después escribe solo en el nuevo y
      el viejo queda como estaba (copia de la base y carpetas temporales: nunca `data/` ni `local.db`).
Sale 0 si pasa. Sin datos reales en la salida.
"""
import hashlib
import importlib
import json
import os
import pathlib
import shutil
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
TMP = pathlib.Path.home() / "RO_MIGRACION" / "tmp" / "l29"
fallos, n = [], 0


def ok(c, t):
    global n
    n += 1
    if not c:
        fallos.append(t)


git = lambda *a: subprocess.run(["git", *a], cwd=RAIZ, capture_output=True, text=True, check=False)
ok(git("ls-files", "fuentes_alertas/estado_alertas.json").stdout.strip() == "", "estado_alertas.json está en git")
ok("fuentes_alertas/estado_alertas.json" in (RAIZ / ".gitignore").read_text(), "falta en .gitignore")
ok(git("check-ignore", "fuentes_alertas/estado_alertas.json").returncode == 0, "git no lo ignora")
ok("fuentes_alertas/estado_alertas.json" not in (RAIZ / "despliegue" / "pasos.json").read_text(), "pasos.json aún lo nombra")
ok("data/alertas" in (RAIZ / "despliegue" / "pasos.json").read_text(), "pasos.json perdió data/alertas")

shutil.rmtree(TMP, ignore_errors=True)
(TMP / "sal").mkdir(parents=True)
base = pathlib.Path.home() / "RO_MIGRACION" / "local.db.antes"
if not base.exists():
    print("✘ L-29: falta ~/RO_MIGRACION/local.db.antes (copia de la base de la F1.3)")
    sys.exit(1)
shutil.copy(base, TMP / "base.db")
os.environ.update({"RO_DB": str(TMP / "base.db"), "RO_ALERTAS_SALIDA": str(TMP / "sal"), "RO_ALERTAS_AHORA": "2026-10-05 07:30", "RO_SIN_LLAVES": "1"})
os.environ.pop("RO_ALERTAS_ESTADO", None)
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "fuentes_alertas"))
G = importlib.import_module("generar_alertas")
ok(G.ESTADO == G.DATA / "alertas" / "_estado" / "estado_alertas.json", "ESTADO por defecto no cuelga de data/alertas/_estado")
ok(G.ESTADO.parent.parent == G.SALIDA or str(G.ESTADO).startswith(str(G.DATA)), "ESTADO fuera de data/")

antiguo = TMP / "viejo" / "estado_alertas.json"
antiguo.parent.mkdir()
real = RAIZ / "fuentes_alertas" / "estado_alertas.json"   # el estado de hoy se copia a la carpeta temporal (solo lectura)
antiguo.write_text(real.read_text() if real.exists() else json.dumps({"_cerradas": []}))
marca = "L29-marca"
d0 = json.loads(antiguo.read_text())
d0["_prueba_l29"] = marca
antiguo.write_text(json.dumps(d0))
h0 = hashlib.sha256(antiguo.read_bytes()).hexdigest()
G.ESTADO, G.ESTADO_ANTIGUO = TMP / "nuevo" / "_estado" / "estado_alertas.json", antiguo   # nunca el de data/
sys.argv = ["generar_alertas.py"]
try:
    G.main()
except SystemExit as e:
    ok(not e.code, f"main() salió con {e.code}")
except Exception as e:  # noqa: BLE001
    ok(False, f"main() falló: {type(e).__name__}: {e}")
ok(G.ESTADO.exists(), "no escribió el estado nuevo")
if G.ESTADO.exists():
    nuevo = json.loads(G.ESTADO.read_text())
    ok(nuevo.get("_prueba_l29") == marca, "el estado nuevo no heredó lo del viejo")
ok(hashlib.sha256(antiguo.read_bytes()).hexdigest() == h0, "el estado viejo cambió: debe quedarse como estaba")
ok(".json" not in git("status", "--porcelain", "fuentes_alertas/").stdout, "git ve algún .json de fuentes_alertas/ cambiado o nuevo")
print(f"{'✘' if fallos else '✔'} L-29: {n} comprobaciones" + "".join(" · " + x for x in fallos))
sys.exit(1 if fallos else 0)
