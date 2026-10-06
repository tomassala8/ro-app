#!/usr/bin/env python3
"""migracion/pruebas_L-09.py · L-09: la clave de una setter es un dato de la persona (`clave_setter`), no el prefijo del id.

Uso: python3 migracion/pruebas_L-09.py [--puerto 8781]
(1) Estática (sin servidor, solo lee el código): `servir.py`, `setters_srv.py` y `altas_personas.py` no usan el prefijo del id; `permisos.py` (`clave_setter_de`) y
    `generar_ventas_ro.py` solo en una línea con `# L-09: respaldo`; ningún id, clave o alias de las setters de hoy (los saca de `data/personas.json` en SOLO LECTURA)
    aparece como literal entre comillas en `servir.py`, `setters_srv.py`, `altas_personas.py` ni `generar_ventas_ro.py`.
(2) Dinámica, SOLO en el 8781 que lanza esta misma prueba (base `ro_esc`, correos y lista de Access desviados a
    `~/RO_MIGRACION/tmp/`, recargas sin pasos): `POST /api/altas/alta` de una setter inventada SIN correo de entrada.
    La alta no escribe nada en `data/` (vive en el historial de la base). La nueva setter tiene `clave_setter`, su sesión
    trae el puesto `setters`, abre SU almacén (`ventas_ro/_privado/setter_<clave>`: 200 o 404, nunca 403) y NO el de otra
    (403). Las setters de hoy siguen abriendo el suyo (200) y no el de la otra (403). Dirección abre cualquiera.
Sin datos reales en el código. Sale 0 si pasa.
"""
import argparse
import http.client
import json
import os
import pathlib
import re
import subprocess
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parents[1]
TMP = pathlib.Path.home() / "RO_MIGRACION" / "tmp"
LOG = pathlib.Path.home() / "RO_MIGRACION" / "logs" / "esc_l09.log"

ap = argparse.ArgumentParser()
ap.add_argument("--puerto", type=int, default=8781)
a = ap.parse_args()

fallos = []


def exige(cond, texto):
    if not cond:
        fallos.append(texto)


# ------------------------------------------------------------------------------------------------ (1) estática
def lineas(nombre):
    return (RAIZ / nombre).read_text(encoding="utf-8").splitlines()


PREFIJO = re.compile(r"""startswith\((["'])setter_\1\)""")
for fichero, permite_con_marca in (("servir.py", False), ("permisos.py", True), ("setters_srv.py", False), ("fuentes_ventas/generar_ventas_ro.py", True), ("altas_personas.py", False)):
    for n, l in enumerate(lineas(fichero), 1):
        if PREFIJO.search(l):
            if not permite_con_marca:
                exige(False, f"{fichero}:{n} usa el prefijo del id (solo vale la línea de respaldo de permisos.py)")
            else:
                exige("L-09: respaldo" in l, f"{fichero}:{n} usa el prefijo del id sin la marca «L-09: respaldo»")

try:
    personas = json.loads((RAIZ / "data" / "personas.json").read_text(encoding="utf-8"))
    personas = personas.get("personas") if isinstance(personas, dict) else personas
except (OSError, ValueError):
    personas = []
nombres = set()
for p in personas or []:
    if "setters" in (p.get("puestos") or []):
        for v in (p.get("id"), p.get("alias"), p.get("clave_setter"), str(p.get("id") or "").removeprefix("setter_")):
            if v and len(v) >= 3:
                nombres.add(v.lower())
exige(bool(nombres), "no hay setters en data/personas.json para comprobar los literales")
for fichero in ("servir.py", "setters_srv.py", "altas_personas.py", "fuentes_ventas/generar_ventas_ro.py"):
    for n, l in enumerate(lineas(fichero), 1):
        if l.lstrip().startswith("#"):
            continue
        for m in re.finditer(r"""(["'])([^"'\n]{3,40})\1""", l):
            if m.group(2).strip().lower() in nombres:
                exige(False, f"{fichero}:{n} lleva un nombre de setter escrito como literal")

# persona y alta: la alta de un puesto «setters» trae su clave (lectura del código, sin ejecutar nada)
alta = "\n".join(lineas("altas_personas.py"))
exige('persona_nueva["clave_setter"]' in alta, "altas_personas.py no pone clave_setter en la persona nueva")
exige('"clave_setter"' in "\n".join(lineas("build_data.py")), "build_data.py no rellena clave_setter a las setters que ya existen")

if a.puerto != 8781:
    print(("✔ " if not fallos else "✘ ") + "L-09: " + ("solo análisis estático (este puerto no escribe)" if not fallos else " · ".join(fallos)))
    sys.exit(1 if fallos else 0)


# ------------------------------------------------------------------------------------------------ (2) dinámica
def pedir(metodo, ruta, cuerpo=None, **cab):
    c = http.client.HTTPConnection("127.0.0.1", a.puerto, timeout=60)
    cab = {"X-RO-App": "1", "Origin": "http://127.0.0.1:3000", "Accept": "application/json", **cab}
    if cuerpo is not None:
        cab["Content-Type"] = "application/json"
    c.request(metodo, ruta, body=json.dumps(cuerpo) if cuerpo is not None else None, headers=cab)
    r = c.getresponse()
    datos = r.read()
    c.close()
    try:
        return r.status, json.loads(datos or b"null")
    except ValueError:
        return r.status, {}


def soltar():
    subprocess.run(["bash", "-lc", "kill $(lsof -t -iTCP@127.0.0.1:8781 -sTCP:LISTEN) 2>/dev/null; sleep 1"], check=False)


def arrancar():
    TMP.mkdir(parents=True, exist_ok=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    (TMP / "recarga_l09.json").write_text('{"ligera": []}\n', encoding="utf-8")
    (TMP / "correos_entrada_l09.json").write_text("{}\n", encoding="utf-8")
    (TMP / "lista_access_l09.txt").write_text("", encoding="utf-8")
    entorno = os.environ.copy()
    entorno.update({
        "DATABASE_URL": "postgresql://ro:ro@127.0.0.1:5432/ro_esc",
        "RO_RELOJ": "2026-10-05T07:30",
        "RO_SIN_LLAVES": "1",
        "RO_AVISOS_SIN_BUCLE": "1",
        "RO_ORIGEN_APP": "http://127.0.0.1:3000",
        "RO_RECARGA_CONFIG": str(TMP / "recarga_l09.json"),
        "RO_CORREOS_ENTRADA": str(TMP / "correos_entrada_l09.json"),
        "RO_LISTA_ACCESS": str(TMP / "lista_access_l09.txt"),
    })
    return subprocess.Popen([sys.executable, "servir.py", "--bind", "127.0.0.1", "--puerto", "8781"], cwd=RAIZ, env=entorno,
                            stdout=open(LOG, "ab"), stderr=subprocess.STDOUT, start_new_session=True)


def esperar_elegir(segundos=60):
    limite = time.time() + segundos
    while time.time() < limite:
        try:
            if pedir("GET", "/api/elegir")[0] == 200:
                return True
        except OSError:
            pass
        time.sleep(0.4)
    return False


def entorno_ok(proc):
    r = subprocess.run(["ps", "eww", "-p", str(proc.pid)], capture_output=True, text=True, check=False).stdout
    return all(f"{k}=" + str(TMP / v) in r for k, v in (("RO_RECARGA_CONFIG", "recarga_l09.json"),
                                                         ("RO_CORREOS_ENTRADA", "correos_entrada_l09.json"),
                                                         ("RO_LISTA_ACCESS", "lista_access_l09.txt")))


def ver(quien, clave):
    return pedir("POST", "/api/ver_dato", {"almacen": f"ventas_ro/_privado/setter_{clave}", "ref": "sin-fila", "campo": "telefono"},
                 **{"X-RO-Yo": quien})


proc = None
try:
    limpia = subprocess.run([sys.executable, "migracion/contrato_escritura.py", "base-limpia", "ro_esc"], cwd=RAIZ, check=False)
    exige(limpia.returncode == 0, f"base-limpia ro_esc rc={limpia.returncode}")
    if limpia.returncode != 0:
        print("✘ L-09: " + " · ".join(fallos))
        sys.exit(1)
    # marca de los ficheros de data/ antes: la prueba no puede cambiar ninguno
    antes = {str(f): f.stat().st_mtime_ns for f in (RAIZ / "data").rglob("*") if f.is_file()}
    soltar()
    proc = arrancar()
    exige(esperar_elegir(60), "8781 no arranca")
    exige(entorno_ok(proc), "el 8781 no lleva las tres variables de entorno propias (correos, lista de Access y recargas)")
    if fallos:
        print("✘ L-09: " + " · ".join(fallos))
        sys.exit(1)
    _, el = pedir("GET", "/api/elegir")
    gente = (el or {}).get("personas") or []
    direccion = next((p["id"] for p in gente if "direccion" in (p.get("puestos") or [])), None)
    setters_hoy = [p["id"] for p in gente if "setters" in (p.get("puestos") or [])]
    exige(bool(direccion), "falta una persona de dirección")
    exige(len(setters_hoy) >= 2, "faltan setters de hoy en /api/elegir")
    if fallos:
        print("✘ L-09: " + " · ".join(fallos))
        sys.exit(1)

    # las setters de hoy: su sesión, lo suyo y no lo de la otra
    claves_hoy = {}
    for sid in setters_hoy:
        st, ses = pedir("GET", "/api/sesion", **{"X-RO-Yo": sid})
        exige(st == 200, f"sesión de {sid} (de hoy): {st}")
        claves_hoy[sid] = sid[len("setter_"):] if sid.startswith("setter_") else sid  # solo para armar el nombre del almacén de la prueba
    s1, s2 = setters_hoy[0], setters_hoy[1]
    st, _ = ver(s1, claves_hoy[s1])
    exige(st == 200, f"una setter de hoy abre su almacén: {st}")
    st, _ = ver(s1, claves_hoy[s2])
    exige(st == 403, f"una setter de hoy NO abre el de otra: {st}")
    st, _ = ver(direccion, claves_hoy[s2])
    exige(st in (200, 404), f"dirección abre el de una setter: {st}")

    # la setter nueva, dada de alta por la ruta de Ajustes y sin correo de entrada
    cuerpo = {"nombre": "Prueba Ele Nueve", "puestos": ["setters"], "jefe": direccion, "zona": "Europe/Madrid", "fecha_entrada": "2026-10-01"}
    st, r = pedir("POST", "/api/altas/alta", cuerpo, **{"X-RO-Yo": direccion})
    exige(st == 200 and (r or {}).get("ok"), f"alta de la setter nueva: {st} {(r or {}).get('error')}")
    nueva = (r or {}).get("id")
    exige(bool(nueva), "el alta no devuelve el id")
    if nueva:
        st, aj = pedir("GET", "/api/ajustes", **{"X-RO-Yo": direccion})
        fila = next((p for p in (aj or {}).get("personas") or [] if p.get("id") == nueva), None)
        exige(st == 200 and bool(fila), "la persona nueva no sale en Ajustes")
        clave = (fila or {}).get("clave_setter")
        exige(bool(clave), "la persona nueva no tiene clave_setter")
        exige(clave not in claves_hoy.values(), "la clave nueva repite la de una setter de hoy")
        st, ses = pedir("GET", "/api/sesion", **{"X-RO-Yo": nueva})
        exige(st == 200, f"sesión de la setter nueva: {st}")
        quien = (ses or {}).get("persona") or {}
        exige(quien.get("id") == nueva and "setters" in (quien.get("puestos") or []), "la sesión de la setter nueva no es suya o no trae el puesto setters")
        exige("setters" in (((ses or {}).get("modulos_puestos") or {}).get("setters") or {}) or "setters" in json.dumps((ses or {}).get("modulos_puestos") or {}),
              "modulos_puestos no conoce la pantalla de setters")
        if clave:
            st, _ = ver(nueva, clave)
            exige(st in (200, 404), f"la setter nueva abre SU almacén (200 o 404, nunca 403): {st}")
            st, _ = ver(nueva, claves_hoy[s1])
            exige(st == 403, f"la setter nueva NO abre el de una setter de hoy: {st}")
            st, _ = ver(s1, clave)
            exige(st == 403, f"una setter de hoy NO abre el de la nueva: {st}")
            st, _ = ver(direccion, clave)
            exige(st in (200, 404), f"dirección abre el de la nueva: {st}")
        # una segunda alta con el mismo nombre no repite clave
        cuerpo2 = {**cuerpo, "fecha_entrada": "2026-10-02"}
        st, r2 = pedir("POST", "/api/altas/alta", cuerpo2, **{"X-RO-Yo": direccion, "Idempotency-Key": "l09-segunda"})
        otra = (r2 or {}).get("id")
        if st == 200 and otra and otra != nueva:
            _, aj2 = pedir("GET", "/api/ajustes", **{"X-RO-Yo": direccion})
            f2 = next((p for p in (aj2 or {}).get("personas") or [] if p.get("id") == otra), None)
            exige(bool(f2) and f2.get("clave_setter") and f2.get("clave_setter") != clave, "la clave de la segunda alta repite la de la primera")

    despues = {str(f): f.stat().st_mtime_ns for f in (RAIZ / "data").rglob("*") if f.is_file()}
    cambiados = [k for k in despues if antes.get(k) != despues[k]]
    exige(not cambiados, f"la prueba ha cambiado {len(cambiados)} fichero(s) de data/")
finally:
    soltar()

print(("✔ " if not fallos else "✘ ") + "L-09" + ("" if not fallos else ": " + " · ".join(fallos)))
sys.exit(1 if fallos else 0)
