#!/usr/bin/env python3
"""migracion/pruebas_L-12.py · L-12: los importes de los textos de decisiones y acciones se recortan según quien mira.

Uso: python3 migracion/pruebas_L-12.py --puerto 8781        (escribe una decisión y una acción de prueba: solo en ro_esc)
(1) Unitaria: `permisos.sin_importes("Cuota de 300 € al mes y gasto en Meta de 500 €", …)` sin inversión conserva 300 y quita 500;
    sin cuota, al revés.
(2) De punta a punta: dirección sube una decisión con «Cuota 300 € al mes · gasto en Meta 500 €» y una acción con ese texto;
    administración (ve cuota, no inversión) ve el 300 y NO el 500; un account no ve ninguno; dirección ve los dos.
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
LOG = pathlib.Path.home() / "RO_MIGRACION" / "logs" / "esc_l12.log"

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



import shutil
import tempfile

HIJO = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
import permisos as P
t = "Cuota de 300 € al mes y gasto en Meta de 500 €"
fallos = []
try:
    a = P.sin_importes(t, P.importes_a_quitar(False, True))   # sin cuota, con inversión
    b = P.sin_importes(t, P.importes_a_quitar(True, False))   # con cuota, sin inversión
except Exception as e:
    print(json.dumps(["permisos.sin_importes/importes_a_quitar no responden: %s" % type(e).__name__])); sys.exit(0)
if "500" not in a or "300" in a: fallos.append("sin cuota: debía quedar el gasto y no la cuota: " + a)
if "300" not in b or "500" in b: fallos.append("sin inversión: debía quedar la cuota y no el gasto: " + b)
print(json.dumps(fallos))
'''
tmp = pathlib.Path(tempfile.mkdtemp(prefix="l12_", dir=TMP))
try:
    entorno = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
    entorno.update({"RO_DB": str(tmp / "x.db"), "RO_SIN_LLAVES": "1"})
    p = subprocess.run([sys.executable, "-c", HIJO, str(RAIZ)], capture_output=True, text=True, env=entorno, cwd=tmp)
    if p.returncode != 0:
        fallos.append("la parte unitaria falló: " + p.stderr[-200:].replace("\n", " | "))
    else:
        fallos += json.loads(p.stdout.strip().splitlines()[-1])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

TEXTO = "Cuota 300 € al mes · gasto en Meta 500 €"


def hay(r, n):
    return n in json.dumps(r, ensure_ascii=False)


comprobadas = []
proc = None
try:
    limpia = subprocess.run([sys.executable, "migracion/contrato_escritura.py", "base-limpia", "ro_esc"], cwd=RAIZ, check=False)
    exige(limpia.returncode == 0, f"base-limpia ro_esc rc={limpia.returncode}")
    if limpia.returncode == 0:
        soltar()
        proc = arrancar()
        exige(esperar_elegir(60), "8781 no arranca")
        if not fallos:
            s, elegir = pedir("GET", "/api/elegir")
            ps = elegir.get("personas") or []
            d = next((p["id"] for p in ps if "direccion" in (p.get("puestos") or [])), None)
            m = next((p["id"] for p in ps if (p.get("puestos") or []) == ["administracion"]), None)
            ac = next((p["id"] for p in ps if (p.get("puestos") or []) == ["account"]), None)
            exige(bool(d and m and ac), "faltan dirección, administración o un account")
            if d and m and ac:
                s, r = pedir("POST", "/api/decisiones", {"tipo": "para_tomas", "titulo": "prueba L-12 " + TEXTO, "problema": TEXTO, "recomendacion": "ninguna"}, **{"X-RO-Yo": d})
                exige(s == 200, f"decisión de dirección {s}")
                s, r = pedir("POST", "/api/acciones", {"tipo": "nota", "herramienta": "app", "modulo": "mi-dia", "objeto": "prueba-l12", "texto": TEXTO}, **{"X-RO-Yo": d})
                accion_ok = s == 200
                for quien, ve300, ve500 in ((d, True, True), (m, True, False), (ac, False, False)):
                    s, dec = pedir("GET", "/api/decisiones", **{"X-RO-Yo": quien})
                    if s == 200:
                        txt = json.dumps(dec, ensure_ascii=False)
                        if "prueba L-12" in txt:
                            comprobadas.append(f"decisión/{quien}")
                            exige(("300" in txt.split("prueba L-12", 1)[1][:200]) == ve300 or ve300 is False and "300 €" not in txt, f"decisión: {quien} ve la cuota → {'300 €' in txt} (debía ser {ve300})")
                            exige(("500 €" in txt) == ve500, f"decisión: {quien} ve el gasto → {'500 €' in txt} (debía ser {ve500})")
                        else:
                            exige(quien != d, f"decisión: {quien} no ve la decisión de prueba (no se puede comprobar)")
                    if accion_ok:
                        s, ac_ = pedir("GET", "/api/acciones?modulo=mi-dia", **{"X-RO-Yo": quien})
                        if s == 200 and hay(ac_, "prueba-l12"):
                            comprobadas.append(f"acción/{quien}")
                            exige(hay(ac_, "500 €") == ve500, f"acción: {quien} ve el gasto → {hay(ac_, '500 €')} (debía ser {ve500})")
                            exige(hay(ac_, "300 €") == ve300, f"acción: {quien} ve la cuota → {hay(ac_, '300 €')} (debía ser {ve300})")
finally:
    soltar()

print(("✔ " if not fallos else "✘ ") + "L-12: " + (f"todo bien ({len(comprobadas)} lecturas comprobadas: {', '.join(comprobadas)})" if not fallos else " · ".join(fallos)))
sys.exit(1 if fallos else 0)
