#!/usr/bin/env python3
"""migracion/pruebas_L-11.py · L-11: una acción no se encola sobre un cliente ajeno por el campo `objeto`.

Uso: python3 migracion/pruebas_L-11.py --puerto 8781        (puede escribir una acción de prueba: solo en ro_esc)
Un account A (puesto account solo, con cartera propia), un cliente ajeno C y uno suyo S:
  (1) `POST /api/acciones` herramienta `app`, tipo `traspaso`, módulo `ficha`, `objeto` = C, sin `cliente_id` → 403;
  (2) lo mismo con `cliente_id` = C → 403;
  (3) tipo `decision_nueva` con `objeto` `*` → 400;
  (4) herramienta `desk`, tipo `responder`, ticket inventado → 400 o 403;
  (5) control: el mismo cuerpo de (1) con `objeto` = S → 200 (no es un 403 general).
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
LOG = pathlib.Path.home() / "RO_MIGRACION" / "logs" / "esc_l11.log"

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



def cuerpo_accion(**kw):
    base = {"tipo": "traspaso", "herramienta": "app", "modulo": "ficha", "texto": "prueba L-11"}
    base.update(kw)
    return base


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
            cuenta = None
            for p in elegir.get("personas") or []:
                if set(p.get("puestos") or []) == {"account"}:
                    s, ses = pedir("GET", "/api/sesion", **{"X-RO-Yo": p["id"]})
                    d = (ses or {}).get("datos") or {}
                    if s == 200 and d.get("soloSuCartera") and d.get("carteraIds"):
                        cuenta, cartera = p["id"], set(d["carteraIds"])
                        break
            exige(bool(cuenta), "no hay un account con cartera propia")
            if cuenta:
                s, ses = pedir("GET", "/api/sesion", **{"X-RO-Yo": "tomas"})
                todos = [c["id"] for c in ((ses or {}).get("datos") or {}).get("clientes", []) if isinstance(c, dict) and c.get("id")]
                ajeno = next((c for c in todos if c not in cartera), None)
                suyo = next((c for c in todos if c in cartera), None)
                exige(bool(ajeno) and bool(suyo), "falta un cliente ajeno o uno suyo")
                cab_ = {"X-RO-Yo": cuenta}
                if ajeno and suyo:
                    s, r = pedir("POST", "/api/acciones", cuerpo_accion(objeto=ajeno), **cab_)
                    exige(s == 403, f"traspaso con objeto = cliente ajeno → {s} (debe ser 403)")
                    for tipo_ in ("nota", "comentario", "avisar"):
                        s, r = pedir("POST", "/api/acciones", cuerpo_accion(tipo=tipo_, objeto=ajeno), **cab_)
                        s_suyo, _r = pedir("POST", "/api/acciones", cuerpo_accion(tipo=tipo_, objeto=suyo), **cab_)
                        exige(s_suyo == 200, f"control: {tipo_} sobre un cliente suyo → {s_suyo} (debe ser 200)")
                        exige(s == 403, f"{tipo_} con objeto = cliente ajeno → {s} (debe ser 400 o 403)")
                    s, r = pedir("POST", "/api/acciones", cuerpo_accion(objeto=ajeno, cliente_id=ajeno), **cab_)
                    exige(s == 403, f"traspaso con cliente_id ajeno → {s} (debe ser 403)")
                    s, r = pedir("POST", "/api/acciones", cuerpo_accion(tipo="decision_nueva", objeto="*"), **cab_)
                    exige(s == 400, f"decision_nueva sobre * → {s} (debe ser 400)")
                    s, r = pedir("POST", "/api/acciones", {"tipo": "responder", "herramienta": "desk", "modulo": "ficha", "objeto": "t_inexistente_l11", "texto": "prueba L-11"}, **cab_)
                    exige(s in (400, 403), f"responder a un ticket inventado → {s} (debe ser 400 o 403)")
                    s, r = pedir("GET", "/api/acciones?modulo=ficha", **cab_)
                    exige(s == 200 and ajeno not in json.dumps(r), "la lista de acciones de ficha trae el cliente ajeno")
                    s, r = pedir("POST", "/api/acciones", cuerpo_accion(objeto=suyo), **cab_)
                    exige(s == 200, f"control: traspaso sobre un cliente suyo → {s} (debe ser 200)")
finally:
    soltar()

print(("✔ " if not fallos else "✘ ") + "L-11: " + ("todo bien" if not fallos else " · ".join(fallos)))
sys.exit(1 if fallos else 0)
