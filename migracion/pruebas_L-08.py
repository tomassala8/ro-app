#!/usr/bin/env python3
"""migracion/pruebas_L-08.py · L-08: toda lectura en «ver como» deja rastro y ningún GET escribe.

Uso: python3 migracion/pruebas_L-08.py --puerto 8781        (escribe rastro: solo en ro_esc)
(1) Operaciones (O) con `X-RO-Como: D` lee `/api/decisiones`, `/api/indicadores` y `/api/avisos` (200); después, O sin
    «ver como» ve en `/api/rastro` filas `coleccion == ver_como`, `accion == lectura`, `como == D` con clave `/api/…`
    (una por familia de ruta como mínimo).
(2) `GET /api/sincronia` (D y O «ver como» D) no cambia el número de filas de `sinc_cambios` ni `sinc_pasos` en ro_esc;
    y, estática, `_get` de `sincronia.py` no contiene INSERT/UPDATE/DELETE/CREATE ni llama a `sincronizar`/`paso(`.
Sale 0 si pasa. Sin datos reales.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
import http.client

RAIZ = pathlib.Path(__file__).resolve().parents[1]
TMP = pathlib.Path.home() / "RO_MIGRACION" / "tmp"
LOG = pathlib.Path.home() / "RO_MIGRACION" / "logs" / "esc_l08.log"

ap = argparse.ArgumentParser()
ap.add_argument("--puerto", type=int, default=8781)
a = ap.parse_args()

fallos = []


def exige(cond, texto):
    if not cond:
        fallos.append(texto)


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


def persona_de(puestos):
    status, data = pedir("GET", "/api/elegir")
    exige(status == 200, f"elegir {status}")
    if status != 200:
        return None
    for p in data.get("personas") or []:
        if puestos in (p.get("puestos") or []):
            return p["id"]
    return None


def soltar():
    subprocess.run(
        ["bash", "-lc", "kill $(lsof -t -iTCP@127.0.0.1:8781 -sTCP:LISTEN) 2>/dev/null; sleep 1"],
        check=False,
    )


def arrancar():
    TMP.mkdir(parents=True, exist_ok=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    (TMP / "recarga_esc.json").write_text('{"ligera": []}\n', encoding="utf-8")
    (TMP / "correos_entrada_esc.json").write_text("{}\n", encoding="utf-8")
    (TMP / "lista_access_esc.txt").write_text("", encoding="utf-8")
    entorno = os.environ.copy()
    entorno.update({
        "DATABASE_URL": "postgresql://ro:ro@127.0.0.1:5432/ro_esc",
        "RO_RELOJ": "2026-10-05T07:30",
        "RO_SIN_LLAVES": "1",
        "RO_AVISOS_SIN_BUCLE": "1",
        "RO_ORIGEN_APP": "http://127.0.0.1:3000",
        "RO_RECARGA_CONFIG": str(TMP / "recarga_esc.json"),
        "RO_CORREOS_ENTRADA": str(TMP / "correos_entrada_esc.json"),
        "RO_LISTA_ACCESS": str(TMP / "lista_access_esc.txt"),
    })
    log = open(LOG, "ab")
    return subprocess.Popen(
        [sys.executable, "servir.py", "--bind", "127.0.0.1", "--puerto", "8781"],
        cwd=RAIZ,
        env=entorno,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )


def esperar_elegir(segundos=60):
    limite = time.time() + segundos
    while time.time() < limite:
        try:
            status, _ = pedir("GET", "/api/elegir")
            if status == 200:
                return True
        except OSError:
            pass
        time.sleep(0.4)
    return False



import ast
import shutil


def persona_con(puesto, excluir=()):
    status, data = pedir("GET", "/api/elegir")
    for p in (data.get("personas") or []):
        if puesto in (p.get("puestos") or []) and p["id"] not in excluir:
            return p["id"]
    return None


def cuenta_sinc():
    psql = shutil.which("psql")
    if not psql:
        return None
    p = subprocess.run([psql, "postgresql://ro:ro@127.0.0.1:5432/ro_esc", "-tAc",
                        "select (select count(*) from sinc_cambios) || '/' || (select count(*) from sinc_pasos)"],
                       capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else None


# (2, estática) _get de sincronia.py no escribe
arbol = ast.parse((RAIZ / "sincronia.py").read_text(encoding="utf-8"))
fn = next((n for n in ast.walk(arbol) if isinstance(n, ast.FunctionDef) and n.name == "_get"), None)
exige(fn is not None, "no encuentro _get en sincronia.py")
if fn is not None:
    for n in ast.walk(fn):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and any(w in n.value.upper() for w in ("INSERT ", "UPDATE ", "DELETE ", "CREATE ")):
            exige(False, "_get de sincronia.py lleva SQL que escribe: " + n.value[:40])
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("sincronizar", "paso"):
            exige(False, f"_get de sincronia.py llama a {n.func.id}()")

proc = None
try:
    limpia = subprocess.run([sys.executable, "migracion/contrato_escritura.py", "base-limpia", "ro_esc"], cwd=RAIZ, check=False)
    exige(limpia.returncode == 0, f"base-limpia ro_esc rc={limpia.returncode}")
    if limpia.returncode == 0:
        soltar()
        proc = arrancar()
        exige(esperar_elegir(60), "8781 no arranca")
        if not fallos:
            d = persona_con("direccion")
            o = persona_con("operaciones", excluir=(d,))
            exige(bool(d) and bool(o), "faltan personas de dirección u operaciones")
            if d and o:
                rutas = ["/api/decisiones", "/api/indicadores", "/api/avisos"]
                for r in rutas:
                    s, _ = pedir("GET", r, **{"X-RO-Yo": o, "X-RO-Como": d})
                    exige(s == 200, f"{r} en «ver como» → {s}")
                s, rastro = pedir("GET", "/api/rastro", **{"X-RO-Yo": o})
                exige(s == 200, f"rastro propio {s}")
                filas = [f for f in (rastro.get("registro") or []) if f.get("coleccion") == "ver_como" and f.get("accion") == "lectura" and f.get("como") == d]
                claves = " ".join(str(f.get("clave")) for f in filas)
                # el rastro guarda la FAMILIA de la ruta (nunca segmentos dinámicos); las que no están en la lista, como «otra»
                esperadas = {"/api/decisiones": "/api/decisiones", "/api/indicadores": "/api/otra", "/api/avisos": "/api/avisos"}
                for r, familia in esperadas.items():
                    exige(familia in claves.split(), f"no queda rastro de la lectura de {r} en «ver como» (familia {familia}; claves: {claves[:160]})")
                antes = cuenta_sinc()
                for yo, como in ((d, None), (o, d)):
                    cab_ = {"X-RO-Yo": yo, **({"X-RO-Como": como} if como else {})}
                    s, _ = pedir("GET", "/api/sincronia", **cab_)
                    exige(s in (200, 403, 503), f"/api/sincronia → {s}")
                despues = cuenta_sinc()
                if antes is None:
                    print("aviso: sin psql, no se cuentan las filas de sinc_*")
                exige(antes == despues, f"GET /api/sincronia cambia las filas de sinc_*: {antes} → {despues}")
finally:
    soltar()

print(("✔ " if not fallos else "✘ ") + "L-08: " + ("todo bien" if not fallos else " · ".join(fallos)))
sys.exit(1 if fallos else 0)
