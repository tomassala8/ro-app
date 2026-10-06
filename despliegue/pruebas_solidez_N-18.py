#!/usr/bin/env python3
"""despliegue/pruebas_solidez_N-18.py · N-18: el vigía corre solo en la nube (cron `ro-vigia` cada 10 min).

Uso: python3 despliegue/pruebas_solidez_N-18.py       (solo lee ficheros)
(1) `despliegue/render.yaml` tiene el cron `ro-vigia` (`*/10 * * * *`, `entrada.sh vigia`, con ro-base, ro-comun, ro-vigilancia y ro-llaves);
(2) `despliegue/entrada.sh` tiene la rama `vigia)` que ejecuta `despliegue/vigia.py` una sola vez (sin --bucle);
(3) el estado del vigía (`data/vigia/episodios.json`) sobrevive entre vueltas de un cron: el disco de un cron de Render
    arranca de cero (publicacion.py, cabecera), así que sin esto cada vuelta repetiría el aviso de «ha dejado de funcionar».
Sale 0 si pasa, 1 si falla. PENDIENTE esta noche (ver NOTAS «F5.10 · N-18»): no está en las baterías.
"""
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
fallos, n = [], 0


def ok(c, t):
    global n
    n += 1
    if not c:
        fallos.append(t)


render = (RAIZ / "despliegue/render.yaml").read_text(encoding="utf-8")
m = re.search(r"^\s*-\s+type:\s*cron\s*\n\s*name:\s*ro-vigia\b.*?(?=^\s*-\s+type:|\Z)", render, re.S | re.M)
bloque = m.group(0) if m else ""
ok(bool(bloque), "(1) render.yaml no tiene el cron ro-vigia")
ok('schedule: "*/10 * * * *"' in bloque and "entrada.sh vigia" in bloque, "(1) ro-vigia sin su horario o su orden")
ok(all(f"fromGroup: {g}" in bloque for g in ("ro-base", "ro-comun", "ro-vigilancia", "ro-llaves")), "(1) ro-vigia sin alguno de sus grupos")
entrada = (RAIZ / "despliegue/entrada.sh").read_text(encoding="utf-8")
ok(re.search(r"^\s*vigia\)\s+.*vigia\.py(?!.*--bucle)", entrada, re.M) is not None, "(2) entrada.sh sin la rama vigia) de una sola vuelta")
vigia = (RAIZ / "despliegue/vigia.py").read_text(encoding="utf-8")
publicacion = (RAIZ / "despliegue/publicacion.py").read_text(encoding="utf-8")
ok("vigia" in publicacion or "episodios" in vigia and "datos_fichero" in vigia, "(3) el estado del vigía no sobrevive entre vueltas de un cron (disco efímero)")

print(f"{'✘' if fallos else '✔'} N-18: {n} comprobaciones" + (" · " + " · ".join(fallos) if fallos else ""))
sys.exit(1 if fallos else 0)
