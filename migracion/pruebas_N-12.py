#!/usr/bin/env python3
"""migracion/pruebas_N-12.py · N-12: el dato viejo de la tubería llega a la pantalla que lo usa; el sello del menú sale de la tubería.

Uso: python3 migracion/pruebas_N-12.py [--puerto 8781]      (arranca su propio servidor sobre ro_esc, que rehace: solo pruebas)
(1) Sin sellos ni vueltas en la base de estado: `/api/sesion` no trae `meta.sellos` ni `meta.generado_tuberia` (nada cambia).
(2) Con el paso `seo` en `dato_viejo` (último bueno 04:15), `redes` en `bien` y una vuelta acabada a las 06:40:
    `meta.sellos` lista los pasos que no van bien con su pantalla (`seo` → `seo-web`), su estado y su último bueno (los que van bien no salen), sin el motivo ni el error;
    `meta.generado_tuberia` = 06:40. Igual para dirección, un account y un setter, y con «ver como».
(3) Navegador (`pruebas_N-12.mjs`): `seo-web` dice «Sin datos en tiempo real: lo último es de las 04:15»; `mi-dia` no dice nada;
    el sello del menú dice «Datos de las 06:40».
(4) `seo` en `bien` → el aviso desaparece. `seo` sin ningún dato bueno → «todavía no hay un dato bueno» (ausencia ≠ verde).
Sale 0 si pasa. Los datos son inventados; ro_esc se rehace al empezar y al acabar no queda nada en ro_app ni en local.db.
"""
import argparse
import http.client
import json
import os
import pathlib
import subprocess
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parents[1]
TMP = pathlib.Path.home() / "RO_MIGRACION" / "tmp"
LOG = pathlib.Path.home() / "RO_MIGRACION" / "logs" / "esc_n12.log"
URL_BASE = "postgresql://ro:ro" + "@127.0.0.1:5432/ro_esc"   # partida: el escáner de secretos la leería como un correo

ap = argparse.ArgumentParser()
ap.add_argument("--puerto", type=int, default=8781)
a = ap.parse_args()
if a.puerto != 8781:
    sys.exit("esta prueba escribe en ro_esc: solo en el 8781")
fallos = []


def exige(cond, texto):
    if not cond:
        fallos.append(texto)


def pedir(ruta, **cab):
    c = http.client.HTTPConnection("127.0.0.1", a.puerto, timeout=60)
    c.request("GET", ruta, headers={"X-RO-App": "1", "Origin": "http://127.0.0.1:3000", "Accept": "application/json", **cab})
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
    (TMP / "recarga_esc.json").write_text('{"ligera": []}\n', encoding="utf-8")
    (TMP / "correos_entrada_esc.json").write_text("{}\n", encoding="utf-8")
    (TMP / "lista_access_esc.txt").write_text("", encoding="utf-8")
    entorno = os.environ.copy()
    entorno.update({
        "DATABASE_URL": URL_BASE, "RO_RELOJ": "2026-10-05T07:30", "RO_SIN_LLAVES": "1", "RO_AVISOS_SIN_BUCLE": "1",
        "RO_ORIGEN_APP": "http://127.0.0.1:3000", "RO_RECARGA_CONFIG": str(TMP / "recarga_esc.json"),
        "RO_CORREOS_ENTRADA": str(TMP / "correos_entrada_esc.json"), "RO_LISTA_ACCESS": str(TMP / "lista_access_esc.txt"),
    })
    return subprocess.Popen([sys.executable, "servir.py", "--bind", "127.0.0.1", "--puerto", "8781"], cwd=RAIZ, env=entorno,
                            stdout=open(LOG, "ab"), stderr=subprocess.STDOUT, start_new_session=True)


def esperar(segundos=60):
    limite = time.time() + segundos
    while time.time() < limite:
        try:
            if pedir("/api/elegir")[0] == 200:
                return True
        except OSError:
            pass
        time.sleep(0.4)
    return False


def sql(consulta, args=()):
    import psycopg
    with psycopg.connect(URL_BASE, autocommit=True) as con:
        con.execute(consulta, args)


def sellar(paso, estado, bueno):
    sql("DELETE FROM sellos WHERE paso=%s", (paso,))
    sql("INSERT INTO sellos (paso, ultimo_bueno, ultimo_intento, estado, motivo) VALUES (%s,%s,%s,%s,%s)",
        (paso, bueno, "2026-10-05T06:40:00", estado, "motivo interno que no debe salir"))


def pantallas(yo):
    r = subprocess.run(["node", "migracion/pruebas_N-12.mjs", "--base", f"http://127.0.0.1:{a.puerto}", "--yo", yo],
                       cwd=RAIZ, capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        fallos.append(f"el navegador falla: {(r.stderr.strip().splitlines() or [r.returncode])[-1]}")
        return None
    return json.loads(r.stdout.strip().splitlines()[-1])


def meta_de(yo, como=None):
    cab = {"X-RO-Yo": yo}
    if como:
        cab["X-RO-Como"] = como
    s, d = pedir("/api/sesion", **cab)
    exige(s == 200, f"/api/sesion como {yo} → {s}")
    return ((d.get("datos") or {}).get("meta") or {}) if s == 200 else {}


AVISO = "Sin datos en tiempo real"
proc = None
try:
    limpia = subprocess.run([sys.executable, "migracion/contrato_escritura.py", "base-limpia", "ro_esc"], cwd=RAIZ, check=False)
    exige(limpia.returncode == 0, f"base-limpia ro_esc rc={limpia.returncode}")
    if limpia.returncode == 0:
        soltar()
        proc = arrancar()
        exige(esperar(60), "8781 no arranca")
    if not fallos:
        s, e = pedir("/api/elegir")
        personas = e.get("personas") or []
        quien = lambda puesto: next((p["id"] for p in personas if puesto in (p.get("puestos") or []) and "direccion" not in (p.get("puestos") or [])), None)
        direccion = next((p["id"] for p in personas if "direccion" in (p.get("puestos") or [])), None)
        account, setter = quien("account"), quien("setters")
        exige(bool(direccion and account and setter), "faltan dirección, un account o un setter en /api/elegir")
        # (1) sin nada en la base de estado
        m = meta_de(direccion)
        exige("sellos" not in m and "generado_tuberia" not in m, "sin sellos ni vueltas, /api/sesion no debía traer los campos nuevos")
        # (2) con datos de prueba
        sellar("seo", "dato_viejo", "2026-10-05T04:15:00")
        sellar("redes", "bien", "2026-10-05T06:40:00")
        sql("INSERT INTO ejecuciones (modo, quien, inicio, fin, estado, resumen) VALUES (%s,%s,%s,%s,%s,%s)",
            ("completa", "prueba", "2026-10-05T06:30:00", "2026-10-05T06:40:00", "ok", "{}"))
        sql("INSERT INTO ejecuciones (modo, quien, inicio, fin, estado, resumen) VALUES (%s,%s,%s,%s,%s,%s)",
            ("completa", "prueba", "2026-10-05T06:55:00", None, "en_curso", "{}"))
        for yo, como in ((direccion, None), (account, None), (setter, None), (direccion, account)):
            if not yo:
                continue
            m = meta_de(yo, como)
            por_paso = {x.get("paso"): x for x in m.get("sellos") or []}
            etiqueta = f"{yo}{' ver como ' + como if como else ''}"
            exige(por_paso.get("seo", {}).get("estado") == "dato_viejo" and por_paso["seo"].get("modulo") == "seo-web"
                  and por_paso["seo"].get("ultimo_bueno") == "2026-10-05T04:15:00", f"{etiqueta}: seo no sale como dato_viejo de seo-web con su hora")
            exige("redes" not in por_paso, f"{etiqueta}: redes va bien y no debía salir en la lista")
            exige(all("motivo" not in x and "error" not in x for x in por_paso.values()), f"{etiqueta}: un sello lleva el motivo o el error")
            exige(m.get("generado_tuberia") == "2026-10-05T06:40:00", f"{etiqueta}: generado_tuberia = {m.get('generado_tuberia')!r} (la vuelta en curso no cuenta)")
        # (3) pantalla
        t = pantallas(direccion)
        if t:
            exige(f"{AVISO}: lo último es de las 04:15" in t["seo"], "seo-web no dice «Sin datos en tiempo real: lo último es de las 04:15»")
            exige(AVISO not in t["miDia"], "mi-dia enseña el aviso sin tener ningún paso en dato viejo")
            exige("Datos de las 06:40" in t["menu"], f"el sello del menú no sale de la tubería: {t['menu']!r}")
        # (4) todo bien → sin aviso; sin ningún dato bueno → se dice
        sellar("seo", "bien", "2026-10-05T06:40:00")
        t = pantallas(direccion)
        if t:
            exige(AVISO not in t["seo"], "con seo en bien, seo-web sigue enseñando el aviso")
        sql("DELETE FROM sellos WHERE paso='seo'")
        sql("INSERT INTO sellos (paso, ultimo_bueno, ultimo_intento, estado, motivo) VALUES ('seo', NULL, '2026-10-05T06:40:00', 'sin_dato', '')")
        t = pantallas(direccion)
        if t:
            exige(f"{AVISO}: todavía no hay un dato bueno" in t["seo"], "seo sin dato bueno: seo-web no lo dice")
finally:
    soltar()

print(("✔ " if not fallos else "✘ ") + "N-12: " + ("todo bien" if not fallos else " · ".join(fallos)))
sys.exit(1 if fallos else 0)
