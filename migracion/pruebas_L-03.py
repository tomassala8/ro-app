#!/usr/bin/env python3
"""migracion/pruebas_L-03.py · L-03: la puerta de secretos mira cada fichero cuando cambia, no solo al arrancar.

Uso: python3 migracion/pruebas_L-03.py
No toca `data/` ni `local.db`: importa `servir.py` en un proceso aparte con `RO_DB` temporal y `AQUI` apuntando a una raíz
temporal en `~/RO_MIGRACION/tmp/l03_*`. Comprueba, con el servidor «arrancado» (el módulo ya cargado):
  (1) un fichero limpio se lee;
  (2) tras reescribirlo con un correo y un teléfono de ejemplo (`@ejemplo.test`), la lectura lanza `DatoSecreto` (el
      camino de `/api/modulo/*` lo responde 503) y el fichero queda en `E.bloqueados` sin servir su contenido;
  (3) al dejarlo limpio otra vez, se vuelve a servir y se levanta el bloqueo;
  (4) la marca de caché evita re-escanear sin cambios (misma lectura dos veces = 1 escaneo);
  (5) `/api/modulo/*` convierte `DatoRoto`/`DatoSecreto` en 503 con el texto del error (estático).
Sale 0 si pasa. Sin datos reales.
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parents[1]
TMP = pathlib.Path.home() / "RO_MIGRACION" / "tmp"
TMP.mkdir(parents=True, exist_ok=True)

HIJO = r'''
import json, os, pathlib, sys, time
sys.path.insert(0, sys.argv[1])
import servir as S
raiz = pathlib.Path(sys.argv[2])
S.AQUI = raiz
f = raiz / "data" / "agenda" / "prueba_l03.json"
f.parent.mkdir(parents=True, exist_ok=True)
rel = "data/agenda/prueba_l03.json"
fallos = []
def exige(c, t):
    if not c: fallos.append(t)
f.write_text(json.dumps({"filas": [{"nota": "limpia"}]}))
obj = S.leer_json_bueno(f)[0]
exige(obj == {"filas": [{"nota": "limpia"}]}, "el fichero limpio no se lee")
exige(rel not in S.E.bloqueados, "el fichero limpio sale bloqueado")
# (4) sin cambios no se vuelve a escanear
llamadas = []
original = S.ESC.escanear_fichero
S.ESC.escanear_fichero = lambda *a, **k: (llamadas.append(1), original(*a, **k))[1]
S.leer_json_bueno(f); S.leer_json_bueno(f)
exige(len(llamadas) == 0, f"escanea {len(llamadas)} veces sin cambios en el fichero")
# (2) cambia con el servidor en marcha
f.write_text(json.dumps({"filas": [{"correo": "persona@ejemplo.test", "telefono": "+34 600 000 000"}]}))
t = time.time() + 5
os.utime(f, (t, t))
try:
    r = S.leer_json_bueno(f)
    exige(False, "un fichero con correo y teléfono se sirvió: " + ("ejemplo.test" in json.dumps(r)).__str__())
except S.DatoSecreto as e:
    exige("secretos" in str(e), "el error de DatoSecreto no habla de la puerta de secretos")
exige(rel in S.E.bloqueados, "el fichero con hallazgos no queda en E.bloqueados")
exige(len(llamadas) >= 1, "no se escaneó al cambiar el fichero")
# se vuelve a pedir: sigue sin servirse
try:
    S.leer_json_bueno(f)
    exige(False, "segunda lectura del fichero con hallazgos: se sirvió")
except S.DatoSecreto:
    pass
# (3) limpio otra vez
f.write_text(json.dumps({"filas": [{"nota": "otra vez limpia"}]}))
t += 5
os.utime(f, (t, t))
obj = S.leer_json_bueno(f)[0]
exige(obj == {"filas": [{"nota": "otra vez limpia"}]}, "al limpiarlo no se vuelve a servir")
exige(rel not in S.E.bloqueados, "al limpiarlo sigue en E.bloqueados")
print(json.dumps(fallos))
'''

fallos = []
tmp = pathlib.Path(tempfile.mkdtemp(prefix="l03_", dir=TMP))
try:
    entorno = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
    entorno.update({"RO_DB": str(tmp / "x.db"), "RO_SIN_LLAVES": "1"})
    p = subprocess.run([sys.executable, "-c", HIJO, str(RAIZ), str(tmp / "raiz")], capture_output=True, text=True, env=entorno, cwd=tmp)
    if p.returncode != 0:
        fallos.append("el proceso de prueba falló: " + (p.stderr or "")[-300:].replace("\n", " | "))
    else:
        try:
            fallos += json.loads(p.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            fallos.append("salida inesperada del proceso de prueba")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

fuente = (RAIZ / "servir.py").read_text(encoding="utf-8")
m = re.search(r"doc_mod, aviso_dato = leer_json_bueno\(fichero\)\n\s+except DatoRoto as e:\n\s+return self\.responder\(503, \{\"error\": str\(e\)\}\)", fuente)
if not m:
    fallos.append("/api/modulo/* no convierte DatoRoto/DatoSecreto en 503")
if "class DatoSecreto(DatoRoto)" not in fuente:
    fallos.append("DatoSecreto ya no es un DatoRoto: /api/modulo/* dejaría de responder 503")

print(("✔ " if not fallos else "✘ ") + "L-03: " + ("todo bien" if not fallos else " · ".join(fallos)))
sys.exit(1 if fallos else 0)
