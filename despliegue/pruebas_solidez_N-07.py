#!/usr/bin/env python3
"""despliegue/pruebas_solidez_N-07.py · N-07: la tubería copia y restaura también _cache y _crudo (los privados no).

Uso:  python3 despliegue/pruebas_solidez_N-07.py
Sobre una carpeta temporal (nunca `data/` ni cachés reales). Dos escenarios con `guardar_instantanea` / `restaurar`:
(1) `fuentes_x/_cache/a.json` = {"v": 1}; el paso la pisa con {} y falla → al restaurar vuelve a {"v": 1}. Igual con `_crudo/`.
(2) Un fichero nuevo a medias en `_cache` se borra al restaurar.
(3) La regla de secretos NO se relaja: una caché con un correo queda `sin_copia` (y se apunta en `sin_restaurar`); lo de `_privado/`
    tampoco se copia ni se borra.
(4) La carpeta de instantáneas está fuera del repo y la tubería la crea en 0700.
Sale 0 si pasa; si no, 1.
"""
import json
import os
import re
import stat
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "despliegue"))
fallos = []


def ok(t):
    print(f"  ✔ {t}")


def mal(t):
    print(f"  ✘ {t}")
    fallos.append(t)


import tuberia as T  # noqa: E402

base = Path(tempfile.mkdtemp(prefix="n07_datos_"))
destino = Path(tempfile.mkdtemp(prefix="n07_instantanea_"))
os.chmod(destino, 0o700)
x = base / "fuentes_x"
(x / "_cache").mkdir(parents=True)
(x / "_crudo").mkdir()
(x / "_privado").mkdir()
a, cr, sec, priv = x / "_cache" / "a.json", x / "_crudo" / "r.json", x / "_cache" / "c.json", x / "_privado" / "b.json"
a.write_text(json.dumps({"v": 1}))
cr.write_text(json.dumps({"crudo": [1, 2, 3]}))
sec.write_text(json.dumps({"lead": "persona@ejemplo.test"}))     # dato personal ficticio
priv.write_text(json.dumps({"x": "privado"}))
salidas = [str(x)]

man = T.guardar_instantanea("p", salidas, destino)
if man.get(str(a)) not in (None, "sin_copia") and man.get(str(cr)) not in (None, "sin_copia"):
    ok("_cache y _crudo entran en la instantánea")
else:
    mal(f"_cache/_crudo sin copia: {man.get(str(a))} {man.get(str(cr))}")
if man.get(str(sec)) == "sin_copia":
    ok("una caché con un correo sigue sin copiarse (regla de secretos intacta)")
else:
    mal("una caché con correo se copió a la instantánea")
if man.get(str(priv)) == "sin_copia":
    ok("_privado/ no se copia")
else:
    mal("_privado/ se copió")

# el paso pisa la caché y el crudo, deja un fichero a medias y toca _privado
a.write_text("{}")
cr.write_text("{}")
nuevo_cache, nuevo_priv = x / "_cache" / "nuevo.json", x / "_privado" / "nuevo.json"
nuevo_cache.write_text("{")
nuevo_priv.write_text("{}")
sin = T.restaurar("p", salidas, destino, man)
if json.loads(a.read_text()) == {"v": 1} and json.loads(cr.read_text()) == {"crudo": [1, 2, 3]}:
    ok("restaurar devuelve la caché y el crudo a como estaban")
else:
    mal(f"no se restauró: a={a.read_text()} crudo={cr.read_text()}")
if not nuevo_cache.exists():
    ok("el fichero nuevo a medias en _cache se borra")
else:
    mal("el fichero nuevo en _cache sigue ahí")
if nuevo_priv.exists() and str(nuevo_priv) in sin and str(priv) in sin and str(sec) in sin:
    ok("lo de _privado/ y lo marcado por el escáner no se toca y se apunta en sin_restaurar")
else:
    mal(f"sin_restaurar: {sorted(Path(s).name for s in sin)}")

# (4)
modo = stat.S_IMODE(destino.stat().st_mode)
fuera = not str(destino.resolve()).startswith(str(RAIZ.resolve()))
src = (RAIZ / "despliegue" / "tuberia.py").read_text(encoding="utf-8")
if modo == 0o700 and fuera and re.search(r"os\.chmod\(instantaneas,\s*0o700\)", src) and "mkdtemp(prefix=f\"ro_instantanea_" in src:
    ok("la instantánea va a una carpeta temporal 0700 fuera del repo")
else:
    mal(f"carpeta de instantáneas: modo={oct(modo)} fuera={fuera}")

if fallos:
    print(f"\n✘ N-07: {len(fallos)} fallo(s)")
    sys.exit(1)
print("\n✔ N-07")
