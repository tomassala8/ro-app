#!/usr/bin/env python3
"""migracion/pruebas_L-04.py · L-04: el recorte por clave no distingue mayúsculas y va por tramos separados por «_».

Uso: python3 migracion/pruebas_L-04.py
Importa `servir` en un proceso aparte con una COPIA de `local.db.antes` (nunca `local.db`) y con `data/` solo en lectura.
(1) Persona sin cuota, cobros ni inversión (puesto produccion): de una fila con `Cuota`, `importe`, `facturado_mes`,
    `cobrado`, `Gasto`, `CPL`, `email`, `movil`, `nombre_lead`, `dni`, `iban`, `mrr`, `precio_mes`, `tarifa`, `fee`,
    `whatsapp`, `facturacion` solo quedan `hotel`, `cuota_horas` y `presupuesto` (en los datos es la fase del embudo, no dinero).
(2) Dirección (ve cuota, cobros e inversión): las cifras que hoy ve siguen; los datos de lead siguen fuera.
(3) Escáner: un IBAN inventado da hallazgo; fechas, puertos y «ES» sueltos no (el DNI no se añade: ver NOTAS_NOCHE.md).
Sale 0 si pasa. Sin datos reales.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parents[1]
TMP = pathlib.Path.home() / "RO_MIGRACION" / "tmp"
ANTES = pathlib.Path.home() / "RO_MIGRACION" / "local.db.antes"
TMP.mkdir(parents=True, exist_ok=True)

HIJO = r'''
import json, sys, tempfile, pathlib
sys.path.insert(0, sys.argv[1])
import servir as S
import escaner_secretos as ESC
S.E.cargar()
P = S.P
fallos = []
fila = {"Cuota": 1, "importe": 2, "facturado_mes": 3, "cobrado": 4, "Gasto": 5, "CPL": 6, "email": "a@ejemplo.test",
        "movil": "600000000", "nombre_lead": "x", "dni": "00000000T", "iban": "ES00", "hotel": "sí", "cuota_horas": 10,
        "mrr": 7, "precio_mes": 8, "tarifa": 9, "fee": 10, "whatsapp": "1", "facturacion": 11, "presupuesto": 12,
        "anidado": {"IMPORTE": 1, "Email": "b@ejemplo.test", "lista": [{"Tarifa": 2, "ok": True}]}}
def quedan(puestos):
    persona = {"id": "p_l04", "puestos": puestos, "estado": "activo"}
    cp = P.contexto(persona, S.E.crudo)
    return S.recortar_doc(fila, S.quitar_para(persona, cp, None)), persona, cp
salida, _, _ = quedan(["produccion"])
if set(salida) - {"anidado"} != {"hotel", "cuota_horas", "presupuesto"}:
    fallos.append("sin cuota ni inversión quedan: " + ",".join(sorted(set(salida) - {"anidado"})))
if salida.get("anidado") != {"lista": [{"ok": True}]}:
    fallos.append("el recorte anidado no quita IMPORTE/Email/Tarifa: " + json.dumps(salida.get("anidado")))
salida, persona, cp = quedan(["direccion"])
for k in ("movil", "nombre_lead", "dni", "iban", "whatsapp", "email"):
    if k in salida: fallos.append(f"dirección ve el dato de lead «{k}»")
for tipo, claves in (("cuota", ["Cuota", "importe", "fee", "mrr", "precio_mes", "tarifa"]), ("cobros", ["facturado_mes", "cobrado", "facturacion"]), ("inversion", ["Gasto", "CPL"])):
    if P.ver(persona, {"tipo": tipo, "cliente_id": None}, cp)["ok"]:
        for k in claves:
            if k not in salida: fallos.append(f"dirección ve «{tipo}» y pierde «{k}»")
for k in ("hotel", "cuota_horas", "presupuesto"):
    if k not in salida: fallos.append(f"dirección pierde «{k}»")
def hallazgos(texto):
    d = pathlib.Path(tempfile.mkdtemp()); f = d / "x.txt"; f.write_text(texto)
    return [h["tipo"] for h in ESC.escanear_fichero(f)]
if "iban" not in hallazgos("cuenta ES9121000418450200051332"): fallos.append("el escáner no ve un IBAN")
if "iban" not in hallazgos("cuenta ES91 2100 0418 4502 0005 1332"): fallos.append("el escáner no ve un IBAN con espacios")
for limpio in ("2026-10-05", "puerto 8770", "ES", "ES91", "id ES12345", "x ES9121000418450200051332abc"):
    if hallazgos(limpio): fallos.append(f"falso positivo del escáner: «{limpio}»")
print(json.dumps(fallos))
'''

fallos = []
if not ANTES.exists():
    print("✘ L-04: falta ~/RO_MIGRACION/local.db.antes")
    sys.exit(1)
tmp = pathlib.Path(tempfile.mkdtemp(prefix="l04_", dir=TMP))
try:
    copia = tmp / "l04.db"
    shutil.copy(ANTES, copia)
    copia.chmod(0o644)
    entorno = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
    entorno.update({"RO_DB": str(copia), "RO_SIN_LLAVES": "1", "RO_RELOJ": "2026-10-05T07:30"})
    p = subprocess.run([sys.executable, "-c", HIJO, str(RAIZ)], capture_output=True, text=True, env=entorno, cwd=tmp)
    if p.returncode != 0:
        fallos.append("el proceso de prueba falló: " + (p.stderr or "")[-300:].replace("\n", " | "))
    else:
        try:
            fallos += json.loads(p.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            fallos.append("salida inesperada del proceso de prueba")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(("✔ " if not fallos else "✘ ") + "L-04: " + ("todo bien" if not fallos else " · ".join(fallos)))
sys.exit(1 if fallos else 0)
