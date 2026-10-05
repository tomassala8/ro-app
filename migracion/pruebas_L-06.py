#!/usr/bin/env python3
"""migracion/pruebas_L-06.py · L-06: la captura de una opinión solo la ve quien la hizo y solo si ve esa pantalla.

Uso: python3 migracion/pruebas_L-06.py --puerto 8781        (escribe opiniones: solo en ro_esc)
(1) Dirección (D) manda una opinión desde `#/panel-direccion` con captura (JPEG mínimo inventado): operaciones (O)
    pide `GET /api/opiniones/captura?id=` → 403; D → 200 con la imagen; O con `X-RO-Como: D` → 403.
(2) O manda otra desde `#/mi-dia`: O la ve (200). Que dirección también la vea no se exige (hoy: solo el autor).
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
LOG = pathlib.Path.home() / "RO_MIGRACION" / "logs" / "esc_l06.log"

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



def persona_con(puesto, excluir=()):
    status, data = pedir("GET", "/api/elegir")
    for p in (data.get("personas") or []):
        if puesto in (p.get("puestos") or []) and p["id"] not in excluir:
            return p["id"]
    return None


CAPTURA = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////2Q=="


def opinar(yo, ruta, texto):
    s, r = pedir("POST", "/api/opinion", {"tipo": "fallo", "prioridad": "gris", "texto": texto, "ruta": ruta, "pantalla": ruta[2:],
                                          "captura": CAPTURA}, **{"X-RO-Yo": yo})
    exige(s == 200 and r.get("id"), f"opinión de {ruta} {s}")
    return r.get("id")


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
                oid = opinar(d, "#/panel-direccion", "prueba L-06 dirección")
                s, _ = pedir("GET", f"/api/opiniones/captura?id={oid}", **{"X-RO-Yo": o})
                exige(s == 403, f"operaciones pide la captura del panel de dirección → {s} (debe ser 403)")
                s, r = pedir("GET", f"/api/opiniones/captura?id={oid}", **{"X-RO-Yo": d})
                exige(s == 200 and "captura" in json.dumps(r), f"la autora no recibe su captura → {s}")
                s, _ = pedir("GET", f"/api/opiniones/captura?id={oid}", **{"X-RO-Yo": o, "X-RO-Como": d})
                exige(s == 403, f"operaciones «ver como» dirección recibe la captura → {s} (debe ser 403)")
                oid2 = opinar(o, "#/mi-dia", "prueba L-06 operaciones")
                s, _ = pedir("GET", f"/api/opiniones/captura?id={oid2}", **{"X-RO-Yo": o})
                exige(s == 200, f"el autor no ve su captura de mi-dia → {s}")
finally:
    soltar()

print(("✔ " if not fallos else "✘ ") + "L-06: " + ("todo bien" if not fallos else " · ".join(fallos)))
sys.exit(1 if fallos else 0)
