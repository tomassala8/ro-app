#!/usr/bin/env python3
"""despliegue/pruebas_solidez_N-06.py · N-06: Paneles. Último dato bueno por cliente y fuente; «rota» solo si nunca hubo dato.

Uso:  python3 despliegue/pruebas_solidez_N-06.py
Sin red ni llaves: la lectura de la fuente (`ga`) es una función falsa; la base es un SQLite temporal (RO_DB); la caché y las
salidas van a una carpeta temporal (nunca se toca `fuentes_paneles/_cache` ni `data/paneles`).
(1) Lectura buena: estado «bien».
(2) La API devuelve `_error` en la 2.ª: la ficha lleva `ga4.estado == 'dato_viejo'` con `desde`, con la serie de la 1.ª; la caché
    conserva el último bueno (con `_viejo`).
(3) La lectura lanza una excepción: lo mismo.
(4) Cliente que nunca tuvo dato y falla: «rota».
(5) Base vacía pero caché de ficheros de ayer: la caché vale como dato viejo (no se pisa con el error).
(6) `modulos/paneles.js` pinta la frescura como «viejo» con `dato_viejo`.
Sale 0 si pasa; si no, 1.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
os.environ.pop("DATABASE_URL", None)
tmpdb = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
tmpdb.close()
os.environ["RO_DB"] = tmpdb.name
os.environ["RO_SIN_LLAVES"] = "1"
sys.path.insert(0, str(RAIZ))
sys.argv = [sys.argv[0], "--cache"]
fallos = []


def ok(t):
    print(f"  ✔ {t}")


def mal(t):
    print(f"  ✘ {t}")
    fallos.append(t)


try:
    from fuentes_paneles import generar_paneles as P

    carpeta = Path(tempfile.mkdtemp(prefix="n06_"))
    P.CACHE = carpeta / "_cache"
    P.SALIDA = carpeta / "data" / "paneles"

    def cliente(cid):
        return {"id": cid, "nombre": "Cliente " + cid, "web": "https://ejemplo.test", "ga4": "properties/1", "ga4_nombre": "GA falso"}

    def lectura_ok():
        return {"leido": "2026-10-05 06:00", "propiedad": "properties/1", "serie": [["2026-10-01", 10], ["2026-10-02", 12]], "serie_canal": {}, "periodos": {"30d": {"sesiones": 22}}, "errores": []}

    def error():
        return {"_error": 403, "_msg": "sin permiso (doble)", "leido": "2026-10-06 06:00"}

    def explota():
        raise ConnectionError("sin red (doble)")

    def ficha(cid):
        P.construir([cliente(cid)])
        idx = json.loads((P.SALIDA / "indice.json").read_text())
        return idx["filas"][0]["fuentes"]["ga4"]

    def cache(cid):
        return json.loads((P.CACHE / "ga" / f"{cid}.json").read_text())

    # (1)
    P.lectura_fuente("ga", "cli_a", lectura_ok)
    f = ficha("cli_a")
    if f["estado"] == "bien" and "desde" not in f:
        ok("lectura buena: estado bien")
    else:
        mal(f"lectura buena: {f}")
    # (2)
    P.lectura_fuente("ga", "cli_a", error)
    f, c = ficha("cli_a"), cache("cli_a")
    if f["estado"] == "dato_viejo" and f.get("desde") and c.get("_viejo") and c["serie"] == lectura_ok()["serie"] and not c.get("_error"):
        ok("_error de la API: dato_viejo con desde, y la caché conserva la serie buena")
    else:
        mal(f"_error: ficha={f} caché_viejo={c.get('_viejo')} error={c.get('_error')}")
    # (3)
    P.lectura_fuente("ga", "cli_a", explota)
    f, c = ficha("cli_a"), cache("cli_a")
    if f["estado"] == "dato_viejo" and c["serie"] == lectura_ok()["serie"]:
        ok("excepción de la lectura: dato_viejo con la misma serie")
    else:
        mal(f"excepción: {f}")
    # (4)
    P.lectura_fuente("ga", "cli_nuevo", error)
    f = ficha("cli_nuevo")
    if f["estado"] == "rota":
        ok("nunca hubo dato y falla: rota")
    else:
        mal(f"cli_nuevo: {f}")
    # (5)
    (P.CACHE / "ga").mkdir(parents=True, exist_ok=True)
    (P.CACHE / "ga" / "cli_ayer.json").write_text(json.dumps(lectura_ok()))
    P.lectura_fuente("ga", "cli_ayer", error)
    f, c = ficha("cli_ayer"), cache("cli_ayer")
    if f["estado"] == "dato_viejo" and c["serie"] == lectura_ok()["serie"]:
        ok("base vacía y caché de ayer: la caché vale como dato viejo")
    else:
        mal(f"caché de ayer: {f}")
    # (6)
    js = (RAIZ / "modulos" / "paneles.js").read_text(encoding="utf-8")
    if "dato_viejo" in js and "estado: 'viejo'" in js:
        ok("paneles.js pinta la frescura como viejo con dato_viejo")
    else:
        mal("paneles.js no distingue dato_viejo")
finally:
    Path(tmpdb.name).unlink(missing_ok=True)

if fallos:
    print(f"\n✘ N-06: {len(fallos)} fallo(s)")
    sys.exit(1)
print("\n✔ N-06")
