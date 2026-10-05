#!/usr/bin/env python3
"""migracion/pruebas_L-21.py · L-21: el hilo de recargas (`trabajador_recargas`) sobrevive a una excepción.

Uso: python3 migracion/pruebas_L-21.py --puerto 8781
(1) Estática con `ast`: el `while True` interior de `trabajador_recargas` tiene un `Try` cuyo cuerpo llama a
    `subprocess.run` y cuyos manejadores capturan `Exception` (y el hilo no termina).
(2) Dinámica, SOLO en el 8781 que lanza esta misma prueba con `RO_RECARGA_CONFIG` propio (fuera del repo, sin pasos):
    una recarga con la configuración rota termina en `con_fallos` y la SIGUIENTE se atiende (`ok`/`con_fallos`, no
    `pendiente`). Nunca hace `POST /api/recarga` a un servidor sin esa variable: lanzaría la tubería entera sobre `data/`.
Escribe solo en ro_esc. Sale 0 si pasa. Sin datos reales en el código.
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
LOG = pathlib.Path.home() / "RO_MIGRACION" / "logs" / "esc_l21.log"
CFG = TMP / "recarga_esc.json"

ap = argparse.ArgumentParser()
ap.add_argument("--puerto", type=int, default=8781)
a = ap.parse_args()

fallos = []


def exige(cond, texto):
    if not cond:
        fallos.append(texto)


def hilo_sobrevive():
    """True si cada vuelta del trabajador va en try/except Exception con la ejecución dentro."""
    arbol = ast.parse((RAIZ / "servir.py").read_text(encoding="utf-8"))
    for f in ast.walk(arbol):
        if not isinstance(f, ast.FunctionDef) or f.name != "trabajador_recargas":
            continue
        for w in ast.walk(f):
            if not isinstance(w, ast.While):
                continue
            for t in ast.walk(w):
                if not isinstance(t, ast.Try):
                    continue
                llama_run = any(isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "run" for b in t.body for n in ast.walk(b))
                captura = any(isinstance(h.type, ast.Name) and h.type.id == "Exception" for h in t.handlers)
                if llama_run and captura:
                    return True
    return False


exige(hilo_sobrevive(), "trabajador_recargas: la vuelta con subprocess.run no va en un try/except Exception")

if a.puerto != 8781:
    print(("✔ " if not fallos else "✘ ") + "L-21: " + ("solo análisis (este puerto no escribe)" if not fallos else " · ".join(fallos)))
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


def entorno_ok(proc):
    """La variable de la configuración propia está de verdad en el proceso (si no, la recarga correría sobre data/ real)."""
    r = subprocess.run(["ps", "eww", "-p", str(proc.pid)], capture_output=True, text=True, check=False)
    return "RO_RECARGA_CONFIG=" + str(CFG) in r.stdout


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


def persona_de(puesto):
    status, data = pedir("GET", "/api/elegir")
    for p in (data or {}).get("personas") or []:
        if puesto in (p.get("puestos") or []):
            return p["id"]
    return None


proc = None
try:
    limpia = subprocess.run([sys.executable, "migracion/contrato_escritura.py", "base-limpia", "ro_esc"], cwd=RAIZ, check=False)
    exige(limpia.returncode == 0, f"base-limpia ro_esc rc={limpia.returncode}")
    if limpia.returncode != 0:
        print("✘ L-21: " + " · ".join(fallos))
        sys.exit(1)
    soltar()
    proc = arrancar()
    exige(esperar_elegir(60), "8781 no arranca")
    exige(entorno_ok(proc), "el 8781 no lleva RO_RECARGA_CONFIG: no se lanza ninguna recarga")
    if fallos:
        print("✘ L-21: " + " · ".join(fallos))
        sys.exit(1)
    cab = {"X-RO-Yo": persona_de("direccion") or ""}
    exige(bool(cab["X-RO-Yo"]), "falta una persona de dirección")
    # (a) configuración rota: la recarga falla en la fase «configuracion», antes de subprocess.run
    CFG.write_text("{", encoding="utf-8")
    status, r1 = pedir("POST", "/api/recarga", {"modo": "ligera"}, **cab)
    exige(status == 200, f"recarga 1: {status}")
    id1 = ((r1 or {}).get("recarga") or {}).get("id")
    time.sleep(3)
    # (b) configuración válida y sin pasos: la siguiente recarga se atiende
    CFG.write_text('{"ligera": []}\n', encoding="utf-8")
    status, r2 = pedir("POST", "/api/recarga", {"modo": "ligera"}, **cab)
    exige(status == 200, f"recarga 2: {status}")
    id2 = ((r2 or {}).get("recarga") or {}).get("id")
    exige(bool(id1) and bool(id2) and id1 != id2, f"recarga 2 no es una fila nueva ({id1}, {id2})")
    fila1 = fila2 = None
    limite = time.time() + 90
    while time.time() < limite:
        status, g = pedir("GET", "/api/recarga", **cab)
        filas = {str(x.get("id")): x for x in ((g or {}).get("recargas") or [])}
        fila1, fila2 = filas.get(str(id1)), filas.get(str(id2))
        if fila2 and fila2.get("estado") in ("ok", "con_fallos"):
            break
        time.sleep(1)
    exige(bool(fila2) and fila2.get("estado") in ("ok", "con_fallos"), f"la siguiente recarga no se atendió: {fila2 and fila2.get('estado')}")
    exige(bool(fila1) and fila1.get("estado") in ("con_fallos", "error"), f"la recarga rota no terminó: {fila1 and fila1.get('estado')}")
finally:
    try:
        CFG.write_text('{"ligera": []}\n', encoding="utf-8")
    except OSError:
        pass
    soltar()

print(("✔ " if not fallos else "✘ ") + "L-21: " + ("el hilo de recargas sobrevive a una excepción" if not fallos else " · ".join(fallos)))
sys.exit(1 if fallos else 0)
