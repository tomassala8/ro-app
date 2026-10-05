#!/usr/bin/env python3
"""migracion/pruebas_L-02.py · L-02: «ver como» no lee el rastro ni las acciones personales de la persona vista.

Uso: python3 migracion/pruebas_L-02.py --puerto 8781            (crea una decisión: solo en ro_esc)
     python3 migracion/pruebas_L-02.py --puerto 3000 --solo-lectura   (la app nueva por el proxy; no escribe)
(1) Dirección (D) sube una decisión de prueba (solo en 8781) y su rastro no está vacío.
(2) Otra persona (O) con `X-RO-Como: D`: GET /api/rastro → 200, ninguna fila con quien == D, todas con quien == O y
    como == D; `acciones == []`. GET /api/acciones sin ?modulo= → 200 {modulo: null, acciones: []}. Sin 403.
(3) O, sin «ver como»: su rastro lleva una fila de la inspección (como == D).
Sale 0 si pasa. Sin datos reales en el código.
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
LOG = pathlib.Path.home() / "RO_MIGRACION" / "logs" / "esc_l02.log"

ap = argparse.ArgumentParser()
ap.add_argument("--puerto", type=int, default=8781)
ap.add_argument("--solo-lectura", action="store_true")
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



def comprobar(direccion):
    # candidatos a O: todos menos D, con operaciones primero
    status, data = pedir("GET", "/api/elegir")
    personas = [p for p in (data.get("personas") or []) if p.get("id") and p["id"] != direccion]
    personas.sort(key=lambda p: 0 if "operaciones" in (p.get("puestos") or []) else 1)
    otra = None
    for p in personas:
        s, d = pedir("GET", "/api/rastro", **{"X-RO-Yo": p["id"], "X-RO-Como": direccion})
        if s == 200:
            otra = p["id"]
            break
    exige(bool(otra), "ninguna persona puede ver como dirección y recibir 200 en /api/rastro (¿403?)")
    if not otra:
        return
    s, d = pedir("GET", "/api/rastro", **{"X-RO-Yo": otra, "X-RO-Como": direccion})
    exige(s == 200, f"rastro en ver como {s}")
    filas = d.get("registro") or []
    ajenas = [f for f in filas if f.get("quien") == direccion]
    exige(not ajenas, f"rastro en ver como trae {len(ajenas)} filas de la persona vista")
    mal = [f for f in filas if not (f.get("quien") == otra and f.get("como") == direccion)]
    exige(not mal, f"rastro en ver como trae {len(mal)} filas que no son de esta inspección")
    exige((d.get("acciones") or []) == [], "rastro en ver como trae acciones personales")
    exige(d.get("todo") is False, "rastro en ver como dice todo=true")
    s, d = pedir("GET", "/api/acciones", **{"X-RO-Yo": otra, "X-RO-Como": direccion})
    exige(s == 200, f"acciones en ver como {s}")
    exige(d.get("modulo") is None and d.get("acciones") == [], "acciones sin módulo en ver como no vienen vacías")
    s, d = pedir("GET", "/api/rastro", **{"X-RO-Yo": otra})
    exige(s == 200, f"rastro propio {s}")
    sigue = [f for f in (d.get("registro") or []) if f.get("quien") == otra and f.get("como") == direccion]
    exige(bool(sigue), "no queda rastro de la inspección en el rastro de quien mira")


def persona_dir():
    d = persona_de("direccion")
    exige(bool(d), "falta una persona de dirección")
    return d


proc = None
try:
    if a.solo_lectura:
        d = persona_dir()
        if d:
            comprobar(d)
    else:
        exige(a.puerto == 8781, "esta prueba escribe: solo en el 8781 (usa --solo-lectura en otro puerto)")
        if a.puerto == 8781:
            limpia = subprocess.run([sys.executable, "migracion/contrato_escritura.py", "base-limpia", "ro_esc"], cwd=RAIZ, check=False)
            exige(limpia.returncode == 0, f"base-limpia ro_esc rc={limpia.returncode}")
            if limpia.returncode == 0:
                soltar()
                proc = arrancar()
                exige(esperar_elegir(60), "8781 no arranca")
                d = persona_dir() if not fallos else None
                if d:
                    s, r = pedir("POST", "/api/decisiones", {"tipo": "para_tomas", "titulo": "prueba L-02", "problema": "prueba L-02", "recomendacion": "ninguna"}, **{"X-RO-Yo": d})
                    exige(s == 200, f"decisión de dirección {s}")
                    s, r = pedir("GET", "/api/rastro", **{"X-RO-Yo": d})
                    exige(s == 200 and any(f.get("quien") == d for f in (r.get("registro") or [])), "dirección no ve su propio rastro (la prueba sería vacía)")
                    comprobar(d)
finally:
    if not a.solo_lectura:
        soltar()

print(("✔ " if not fallos else "✘ ") + "L-02: " + ("todo bien" if not fallos else " · ".join(fallos)))
sys.exit(1 if fallos else 0)
