#!/usr/bin/env python3
"""migracion/pruebas_L-13.py · L-13: Ajustes valida lo que escribe (asignaciones, estado, correo, «Para confirmar»).

Uso: python3 migracion/pruebas_L-13.py --puerto 8781        (escribe: solo en ro_esc)
Con dirección D como actor y una persona P activa (account) distinta:
  (1) `POST /api/ajustes/asignacion`: fecha `hasta` no ISO → 400; silla inexistente → 400; persona inventada → 400;
      cuerpo válido → 200 (control).
  (2) `POST /api/ajustes/persona` (cuerpo `{id, cambios}`): `estado: baja` → 400; Guardar normal (`estado: activo`) → 200; `correo` nuevo → 400 o 403.
  (3) `POST /api/ajustes/confirmar`: duda inexistente → 400; `tipo: persona` con `cambios.puestos` → 400.
Sale 0 si pasa. Cada rechazo lleva `error`. Sin datos reales.
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
LOG = pathlib.Path.home() / "RO_MIGRACION" / "logs" / "esc_l13.log"

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
            pers = next((p for p in ps if (p.get("puestos") or []) == ["account"]), None)
            exige(bool(d and pers), "faltan dirección o un account")
            if d and pers:
                P = pers["id"]
                h = {"X-RO-Yo": d}
                s, ses = pedir("GET", "/api/sesion", **h)
                cl = [c["id"] for c in ((ses or {}).get("datos") or {}).get("clientes", []) if isinstance(c, dict) and c.get("id")]
                exige(bool(cl), "sin clientes")
                cid = cl[0] if cl else "x"

                def asig(**kw):
                    b = {"operacion": "crear", "persona_id": P, "cliente_id": cid, "silla": "account", "desde": "2026-10-05"}
                    b.update(kw)
                    return pedir("POST", "/api/ajustes/asignacion", b, **h)

                for nombre, kw in (("hasta no ISO", {"hasta": "31/12/2026"}), ("silla inexistente", {"silla": "inexistente"}), ("persona inventada", {"persona_id": "p_l13_no_existe"})):
                    s, r = asig(**kw)
                    exige(s == 400 and "error" in (r or {}), f"asignación con {nombre} → {s} (debe ser 400 con error)")
                for cid_ in cl[:15]:
                    cid = cid_
                    s, r = asig()
                    if s == 200:
                        break
                exige(s == 200, f"control: asignación válida → {s} (debe ser 200)")

                s, r = pedir("POST", "/api/ajustes/persona", {"id": P, "cambios": {"estado": "baja"}}, **h)
                exige(s == 400 and "error" in (r or {}), f"estado baja por Ajustes → {s} (debe ser 400 con error)")
                s, r = pedir("POST", "/api/ajustes/persona", {"id": P, "cambios": {"estado": "activo"}}, **h)
                exige(s == 200, f"Guardar normal (estado activo) → {s} (debe ser 200)")
                s, r = pedir("POST", "/api/ajustes/persona", {"id": P, "cambios": {"estado": "activo", "correo": "otra@rankingonline.com"}}, **h)
                exige(s in (400, 403), f"correo nuevo por Ajustes → {s} (debe ser 400 o 403)")

                s, r = pedir("POST", "/api/ajustes/confirmar", {"respuesta": {"tipo": "persona", "duda": "duda_inexistente_l13", "persona_id": P, "cambios": {"estado": "activo"}}}, **h)
                exige(s == 400 and "error" in (r or {}), f"confirmar una duda inexistente → {s} (debe ser 400 con error)")
                s, aj = pedir("GET", "/api/ajustes", **h)
                dudas = [x for x in ((aj or {}).get("para_confirmar") or []) if isinstance(x, dict) and x.get("tipo") == "persona" and x.get("persona_id") and x.get("id")]
                if dudas:
                    s, r = pedir("POST", "/api/ajustes/confirmar", {"respuesta": {"tipo": "persona", "duda": dudas[0]["id"], "persona_id": dudas[0]["persona_id"], "cambios": {"puestos": ["direccion"]}}}, **h)
                    exige(s == 400, f"confirmar con cambios.puestos → {s} (debe ser 400)")
                else:
                    print("aviso: sin dudas de persona en para_confirmar: se salta confirmar con puestos")
finally:
    soltar()

print(("✔ " if not fallos else "✘ ") + "L-13: " + ("todo bien" if not fallos else " · ".join(fallos)))
sys.exit(1 if fallos else 0)
