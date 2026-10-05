#!/usr/bin/env python3
"""migracion/pruebas_L-22.py · L-22: la hora de pared de `servir.py` y de `ia.py` es la de Madrid aunque el proceso corra con TZ=UTC.

Uso: python3 migracion/pruebas_L-22.py
(1) Estática: ningún `datetime.now()` sin zona fuera de `ahora()` (servir.py) y `_ahora()` (ia.py).
(2) `ia._ahora()` con TZ=UTC: difiere de la hora de Madrid en menos de 2 minutos (si saliera UTC, 1 h o 2 h).
(3) Servidor propio en 8782 (ro_esc, TZ=UTC, SIN RO_RELOJ): `POST /api/opinion` devuelve `hora` (la de `ahora()`): en Madrid, y dos
    POST con 2 s de por medio dan horas distintas (el reloj no se congela).
La hora de la base (`creada` del rastro) sigue en UTC por diseño (R16 N6): no se mira aquí ni cambia.
Sale 0 si pasa. Escribe solo en ro_esc (8782). Sin datos reales ni llaves.
"""
import ast
import http.client
import json
import os
import pathlib
import subprocess
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

RAIZ = pathlib.Path(__file__).resolve().parents[1]
TMP = pathlib.Path.home() / "RO_MIGRACION" / "tmp"
LOG = pathlib.Path.home() / "RO_MIGRACION" / "logs" / "esc_l22.log"
PUERTO = 8782
MADRID = ZoneInfo("Europe/Madrid")
fallos = []


def exige(cond, texto):
    if not cond:
        fallos.append(texto)


def madrid_ahora():
    return datetime.now(MADRID).replace(tzinfo=None)


def cerca(texto_hora, que):
    """¿La hora escrita (sin zona) está a menos de 2 minutos de la de Madrid?"""
    try:
        h = datetime.fromisoformat(str(texto_hora).replace(" ", "T"))
    except ValueError:
        fallos.append(f"{que}: hora ilegible «{texto_hora}»")
        return
    dif = abs((madrid_ahora() - h).total_seconds())
    exige(dif < 120, f"{que}: «{texto_hora}» difiere {int(dif)} s de la hora de Madrid (¿UTC?)")


# (1) Estática
for fichero, permitida in (("servir.py", "ahora"), ("ia.py", "_ahora")):
    arbol = ast.parse((RAIZ / fichero).read_text(encoding="utf-8"))
    padres = {}
    for nodo in ast.walk(arbol):
        for hijo in ast.iter_child_nodes(nodo):
            padres[hijo] = nodo
    for nodo in ast.walk(arbol):
        if not (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute) and nodo.func.attr == "now"
                and isinstance(nodo.func.value, ast.Name) and nodo.func.value.id == "datetime" and not nodo.args and not nodo.keywords):
            continue
        p = nodo
        while p in padres and not isinstance(p, ast.FunctionDef):
            p = padres[p]
        dentro = p.name if isinstance(p, ast.FunctionDef) else None
        exige(dentro == permitida, f"{fichero}:{nodo.lineno}: datetime.now() sin zona fuera de {permitida}()")
print(f"  {'✔' if not fallos else '✘'} estática: sin datetime.now() sin zona fuera de ahora()/_ahora()")

# (2) ia._ahora() con TZ=UTC
entorno_utc = {**os.environ, "TZ": "UTC"}
entorno_utc.pop("RO_RELOJ", None)
entorno_utc.pop("DATABASE_URL", None)
r = subprocess.run([sys.executable, "-c", "import ia; print(ia._ahora().isoformat())"], cwd=RAIZ, env=entorno_utc,
                   capture_output=True, text=True, timeout=120)
if r.returncode != 0:
    fallos.append(f"ia no se importa: {(r.stderr.strip().splitlines() or [r.returncode])[-1]}")
else:
    cerca(r.stdout.strip().splitlines()[-1], "ia._ahora() con TZ=UTC")


# (3) Servidor propio
def pedir(metodo, ruta, cuerpo=None, **cab):
    c = http.client.HTTPConnection("127.0.0.1", PUERTO, timeout=60)
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
    subprocess.run(["bash", "-lc", f"kill $(lsof -t -iTCP@127.0.0.1:{PUERTO} -sTCP:LISTEN) 2>/dev/null; sleep 1"], check=False)


def arrancar():
    TMP.mkdir(parents=True, exist_ok=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    (TMP / "recarga_esc.json").write_text('{"ligera": []}\n', encoding="utf-8")
    (TMP / "correos_entrada_esc.json").write_text("{}\n", encoding="utf-8")
    (TMP / "lista_access_esc.txt").write_text("", encoding="utf-8")
    entorno = os.environ.copy()
    entorno.pop("RO_RELOJ", None)
    entorno.update({
        "TZ": "UTC",
        "DATABASE_URL": "postgresql://ro:ro@127.0.0.1:5432/ro_esc",
        "RO_SIN_LLAVES": "1",
        "RO_AVISOS_SIN_BUCLE": "1",
        "RO_ORIGEN_APP": "http://127.0.0.1:3000",
        "RO_RECARGA_CONFIG": str(TMP / "recarga_esc.json"),
        "RO_CORREOS_ENTRADA": str(TMP / "correos_entrada_esc.json"),
        "RO_LISTA_ACCESS": str(TMP / "lista_access_esc.txt"),
    })
    return subprocess.Popen([sys.executable, "servir.py", "--bind", "127.0.0.1", "--puerto", str(PUERTO)], cwd=RAIZ, env=entorno,
                            stdout=open(LOG, "ab"), stderr=subprocess.STDOUT, start_new_session=True)


def esperar(segundos=60):
    limite = time.time() + segundos
    while time.time() < limite:
        try:
            if pedir("GET", "/api/elegir")[0] == 200:
                return True
        except OSError:
            pass
        time.sleep(0.4)
    return False


proc = None
try:
    limpia = subprocess.run([sys.executable, "migracion/contrato_escritura.py", "base-limpia", "ro_esc"], cwd=RAIZ, check=False)
    exige(limpia.returncode == 0, f"base-limpia ro_esc rc={limpia.returncode}")
    if limpia.returncode == 0:
        soltar()
        proc = arrancar()
        if not esperar(60):
            fallos.append(f"{PUERTO} no arranca")
        else:
            _, elegir = pedir("GET", "/api/elegir")
            direccion = next((p["id"] for p in elegir.get("personas") or [] if "direccion" in (p.get("puestos") or [])), None)
            exige(bool(direccion), "falta una persona de dirección")
            if direccion:
                horas = []
                for i in range(2):
                    st, d = pedir("POST", "/api/opinion", {"tipo": "idea", "prioridad": "gris", "texto": f"prueba de hora L-22 número {i}"}, **{"X-RO-Yo": direccion})
                    exige(st == 200 and d.get("hora"), f"opinión {i}: {st} {d}")
                    if st == 200 and d.get("hora"):
                        horas.append(d["hora"])
                        cerca(d["hora"], f"/api/opinion con TZ=UTC (hora {i})")
                    if i == 0:
                        time.sleep(2.2)
                if len(horas) == 2:
                    exige(horas[0] != horas[1], f"el reloj parece congelado: {horas}")
finally:
    soltar()

print(("✔ " if not fallos else "✘ ") + "L-22: " + ("las horas salen en Madrid con TZ=UTC" if not fallos else " · ".join(fallos)))
sys.exit(1 if fallos else 0)
