#!/usr/bin/env python3
"""despliegue/pruebas_solidez_N-05.py · N-05: Hostinger. Un error de la API = el último dato bueno con aviso; sin dato nunca sale 0.

Uso:  python3 despliegue/pruebas_solidez_N-05.py
Sin red ni llaves: `hg` es un doble; la base es un SQLite temporal (RO_DB); salidas y caché van a una carpeta temporal.
`generar_hostinger.main()` se ejecuta contra esa carpeta (nunca se toca `data/` ni `fuentes_hostinger/_cache`).
(1) 1.ª vuelta buena: estado «conectado», 2 VPS, alertas, sale 0.
(2) 2.ª vuelta con error de la API: mismos VPS y alertas, estado «dato_viejo» con `dato_viejo_desde`, NO «sin_conectar»; sale 0.
(3) Nunca hubo dato (base y caché vacías) y la API falla: estado «sin_dato», sin VPS inventados, y el proceso sale con 2.
(4) Primera vuelta con la API caída pero con la caché de ficheros de ayer: dato viejo, sale 0.
(5) Sin token (`SinClave`): sigue siendo «sin_conectar» (no es un fallo de la API) y sale 0.
Sale 0 si pasa; si no, 1.
"""
import json
import os
import sys
import tempfile
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
os.environ.pop("DATABASE_URL", None)
tmpdb = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
tmpdb.close()
os.environ["RO_DB"] = tmpdb.name
os.environ["RO_SIN_LLAVES"] = "1"
sys.path.insert(0, str(RAIZ))
fallos = []


def ok(t):
    print(f"  ✔ {t}")


def mal(t):
    print(f"  ✘ {t}")
    fallos.append(t)


def vaciar_bd():
    from fuentes import lectura as L
    con = L.conectar()
    try:
        with con:
            con.execute("DELETE FROM fuente_lectura")
    finally:
        con.close()


try:
    estado = {"modo": "bien"}

    class SinClave(Exception):
        pass

    class HostingerError(Exception):
        pass

    hg = types.ModuleType("hg")
    hg.SinClave, hg.HostingerError = SinClave, HostingerError

    def volcar(ssl=False):
        if estado["modo"] == "sin_clave":
            raise SinClave("no hay token (doble)")
        if estado["modo"] == "caida":
            raise HostingerError("timeout (doble)")
        d = G.simulado()
        d.pop("_simulado", None)
        return d
    hg.volcar = volcar
    sys.modules["hg"] = hg

    from fuentes_hostinger import generar_hostinger as G

    carpeta = Path(tempfile.mkdtemp(prefix="n05_"))
    (carpeta / "data" / "clientes").mkdir(parents=True)
    G.APP = str(carpeta)
    G.SALIDA = str(carpeta / "data" / "hostinger" / "hostinger.json")
    G.CUENTA = str(carpeta / "data" / "hostinger" / "cuenta.json")
    G.CACHE = str(carpeta / "cache" / "volcado.json")

    def vuelta():
        sys.argv = ["generar_hostinger.py"]
        try:
            G.main()
            rc = 0
        except SystemExit as e:
            rc = e.code if isinstance(e.code, int) else 1
        web = json.loads(Path(G.SALIDA).read_text())
        cuenta = json.loads(Path(G.CUENTA).read_text())
        return rc, web, cuenta

    # (1)
    rc, web, cuenta = vuelta()
    n_vps, n_al = len(cuenta["vps"]), len(web["alertas"]) + len(cuenta["alertas"])
    if rc == 0 and web["_meta"]["estado"] == "conectado" and n_vps == 2 and n_al > 0:
        ok(f"1.ª vuelta: conectado, {n_vps} VPS, {n_al} alertas, sale 0")
    else:
        mal(f"1.ª vuelta: rc={rc} estado={web['_meta']['estado']} vps={n_vps} alertas={n_al}")
    # (2)
    estado["modo"] = "caida"
    rc, web, cuenta = vuelta()
    if rc == 0 and web["_meta"]["estado"] == "dato_viejo" and web["_meta"].get("dato_viejo_desde") \
            and len(cuenta["vps"]) == n_vps and len(web["alertas"]) + len(cuenta["alertas"]) == n_al:
        ok("API caída: mismos VPS y alertas, estado dato_viejo con dato_viejo_desde, sale 0")
    else:
        mal(f"API caída: rc={rc} estado={web['_meta']['estado']} vps={len(cuenta['vps'])} alertas={len(web['alertas']) + len(cuenta['alertas'])}")
    # (3)
    vaciar_bd()
    Path(G.CACHE).unlink(missing_ok=True)
    rc, web, cuenta = vuelta()
    if rc == 2 and web["_meta"]["estado"] == "sin_dato" and cuenta["vps"] == [] and web["_meta"]["estado"] != "sin_conectar":
        ok("nunca hubo dato y la API falla: sin_dato, sin VPS inventados, sale 2")
    else:
        mal(f"sin_dato: rc={rc} estado={web['_meta']['estado']} vps={len(cuenta['vps'])}")
    # (4)
    estado["modo"] = "bien"
    vuelta()                      # deja la caché de ficheros
    vaciar_bd()                   # y la base vacía, como la primera noche
    estado["modo"] = "caida"
    rc, web, cuenta = vuelta()
    if rc == 0 and web["_meta"]["estado"] == "dato_viejo" and len(cuenta["vps"]) == n_vps:
        ok("base vacía y API caída: se usa la caché de ficheros como dato viejo")
    else:
        mal(f"caché de ficheros: rc={rc} estado={web['_meta']['estado']} vps={len(cuenta['vps'])}")
    # (5)
    estado["modo"] = "sin_clave"
    rc, web, cuenta = vuelta()
    if rc == 0 and web["_meta"]["estado"] == "sin_conectar":
        ok("sin token: sigue siendo sin_conectar y sale 0")
    else:
        mal(f"sin token: rc={rc} estado={web['_meta']['estado']}")
finally:
    Path(tmpdb.name).unlink(missing_ok=True)

if fallos:
    print(f"\n✘ N-05: {len(fallos)} fallo(s)")
    sys.exit(1)
print("\n✔ N-05")
