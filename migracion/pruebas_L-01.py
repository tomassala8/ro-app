#!/usr/bin/env python3
"""migracion/pruebas_L-01.py · L-01: aplicar_ajustes no asigna una variable local «hoy».

Uso: python3 migracion/pruebas_L-01.py --puerto 8781
Sale 0 si pasa. Escribe solo en ro_esc (8781). Sin datos reales en el código.
"""
import argparse
import ast
import json
import os
import pathlib
import subprocess
import sys
import time
import http.client

RAIZ = pathlib.Path(__file__).resolve().parents[1]
TMP = pathlib.Path.home() / "RO_MIGRACION" / "tmp"
LOG = pathlib.Path.home() / "RO_MIGRACION" / "logs" / "esc_l01.log"

ap = argparse.ArgumentParser()
ap.add_argument("--puerto", type=int, default=8781)
a = ap.parse_args()

fallos = []


def exige(cond, texto):
    if not cond:
        fallos.append(texto)


def sombrea_hoy():
    arbol = ast.parse((RAIZ / "servir.py").read_text(encoding="utf-8"))
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.FunctionDef) or nodo.name != "aplicar_ajustes":
            continue
        for sub in ast.walk(nodo):
            if isinstance(sub, ast.Name) and sub.id == "hoy" and isinstance(sub.ctx, ast.Store):
                return True
    return False


exige(not sombrea_hoy(), "aplicar_ajustes asigna una variable local 'hoy'")

if a.puerto != 8781:
    print(("✔ " if not fallos else "✘ ") + "L-01: " + ("solo análisis (este puerto no escribe)" if not fallos else " · ".join(fallos)))
    sys.exit(1 if fallos else 0)


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


proc = None
try:
    limpia = subprocess.run(
        [sys.executable, "migracion/contrato_escritura.py", "base-limpia", "ro_esc"],
        cwd=RAIZ,
        check=False,
    )
    exige(limpia.returncode == 0, f"base-limpia ro_esc rc={limpia.returncode}")
    if limpia.returncode != 0:
        print("✘ L-01: " + " · ".join(fallos))
        sys.exit(1)
    soltar()
    proc = arrancar()
    exige(esperar_elegir(60), "8781 no arranca")
    if fallos:
        print("✘ L-01: " + " · ".join(fallos))
        sys.exit(1)
    direccion = persona_de("direccion")
    exige(bool(direccion), "falta una persona de dirección")
    if not direccion:
        print("✘ L-01: " + " · ".join(fallos))
        sys.exit(1)
    cab = {"X-RO-Yo": direccion}
    status, ajustes = pedir("GET", "/api/ajustes", **cab)
    exige(status == 200, f"ajustes {status}")
    dudas = [d for d in (ajustes.get("para_confirmar") or []) if isinstance(d, dict) and d.get("id")]
    persona = next((d for d in dudas if d.get("tipo") == "persona" and d.get("persona_id")), None)
    asignacion = next((d for d in dudas if d.get("tipo") == "asignacion" and d.get("cliente_id") and d.get("silla")), None)
    duda = persona or asignacion or (dudas[0] if dudas else None)
    if duda and duda.get("tipo") == "persona":
        resp = {"tipo": "persona", "duda": duda["id"], "persona_id": duda["persona_id"], "cambios": {"estado": "activo"}}
    elif duda and duda.get("tipo") == "asignacion":
        resp = {
            "tipo": "asignacion",
            "duda": duda["id"],
            "cliente_id": duda["cliente_id"],
            "silla": duda["silla"],
            "persona_id": duda.get("persona_propuesta") or duda.get("persona_id"),
            "accion": "confirmar",
        }
    elif duda:
        resp = {"tipo": "nota", "duda": duda["id"], "nota": "prueba L-01"}
    else:
        resp = None
    if resp:
        status, _ = pedir("POST", "/api/ajustes/confirmar", {"respuesta": resp}, **cab)
        exige(status == 200, f"confirmar {status}")
    else:
        print("sin dudas en para_confirmar: solo el análisis y el reinicio")
    status, _ = pedir("GET", "/api/sesion", **cab)
    exige(status == 200, f"sesion {status}")
    soltar()
    proc = arrancar()
    exige(esperar_elegir(60), "8781 no vuelve a arrancar tras confirmar")
finally:
    soltar()

print(("✔ " if not fallos else "✘ ") + "L-01: " + ("todo bien" if not fallos else " · ".join(fallos)))
sys.exit(1 if fallos else 0)
