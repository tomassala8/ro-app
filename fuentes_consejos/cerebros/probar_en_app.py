#!/usr/bin/env python3
"""fuentes_consejos/cerebros/probar_en_app.py · los cerebros DENTRO de ia.py, sin servidor ni datos (4-oct-2026).

Comprueba con un servir.py de mentira: cada consejo lleva su ficha (y la de un tipo sin ficha no rompe nada); la ficha de
una alerta del cliente llega al copiloto sin guiones; /api/ia/cerebro busca y abre fichas, la reserva por puesto se
cumple (una setter no abre fichas de dirección ni de personas que no sean suyas) y, sin clave, el POST devuelve la ficha
tal cual, sin llamar a la IA. Con una IA simulada: lo prudente pasa; una cifra inventada o un precio, no.

  python3 fuentes_consejos/cerebros/probar_en_app.py
"""
import re
import sys
import types
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(APP))
import ia  # noqa: E402

FALLOS = []


def ok(cond, que):
    print(("  ✓ " if cond else "  ✗ ") + que)
    if not cond:
        FALLOS.append(que)


# --- servir.py de mentira: lo justo que tocan estas funciones
S = types.SimpleNamespace()
S.ESC = types.SimpleNamespace(PATRONES=[("correo", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"))])
S.P = types.SimpleNamespace(ver=lambda persona, que, cp: {"ok": que.get("cliente_id") in persona.get("clientes", [])})
ia.S = S
ia.estado_para = lambda persona: {"conectada": False, "motivo": "IA sin conectar", "modelo": None}
ia.verdad_para = lambda persona, cp, cid: {"id": cid, "nombre": "Cliente de prueba", "gravedad": "atencion"}

SETTER = {"id": "setter_ana", "nombre": "Ana", "puestos": ["setters"], "clientes": []}
ACCOUNT = {"id": "acc_x", "nombre": "X", "puestos": ["account"], "clientes": ["c1"]}
TOMAS = {"id": "tomas", "nombre": "Tomás", "puestos": ["direccion"], "clientes": ["c1"]}

print("1. Ficha en cada consejo")
c = ia._con_ficha(ACCOUNT, {"id": "al:1", "tipo": "acc_correos", "que": "Contesta"})
ok(c.get("ficha", {}).get("area") == "account" and c["ficha"].get("hoy"), "acc_correos → ficha de account con «hoy»")
c = ia._con_ficha(ACCOUNT, {"id": "x", "tipo": "tipo_que_no_existe"})
ok("ficha" not in c, "un tipo sin ficha sale igual, sin ficha")
c = ia._con_ficha(SETTER, {"id": "y", "tipo": "dir_decision"})
ok(not c.get("ficha") or c["ficha"]["area"] not in ("direccion", "personas_admin"), "una setter no recibe ficha reservada de dirección")

print("2. Copiloto")
fs = ia._fichas_cliente(ACCOUNT, [{"tipo": "acc_correos"}, {"tipo": "acc_correos"}, {"tipo": "web_caida"}, {"tipo": "seo_rojo"}, {"tipo": "pub_critico"}])
ok(len(fs) == 3, "como mucho 3 fichas y sin repetir")
ok(all("guiones" not in f for f in fs), "sin guiones (ahorra tokens)")
ok(sum(ia.CB.tokens_aprox(f) for f in fs) < 3500, "las 3 fichas juntas < 3.500 tokens")

print("3. GET /api/ia/cerebro")
r = ia.cerebro_get(SETTER, {"q": ["los leads no se presentan a las citas"]})
ok(r["ok"] and r["fichas"] and r["fichas"][0]["area"] in ("setters", "crm", "publicidad"), "buscar por texto da la ficha del área")
r = ia.cerebro_get(SETTER, {"q": ["salida de una persona del equipo despido"]})
ok(all(f["area"] not in ("direccion", "personas_admin") or "setters" in ia.CB.ficha(f["id"]).get("puestos", []) for f in r["fichas"]),
   "la búsqueda de una setter no trae fichas reservadas ajenas")
try:
    ia.cerebro_get(SETTER, {"id": ["personas_admin_salida_de_persona"]})
    ok(False, "una setter no abre la ficha de salida de una persona")
except ia.Denegado:
    ok(True, "una setter no abre la ficha de salida de una persona")
r = ia.cerebro_get(TOMAS, {"id": ["personas_admin_salida_de_persona"]})
ok(r["ok"] and r["ficha"]["id"] == "personas_admin_salida_de_persona", "dirección sí la abre")
r = ia.cerebro_get(ACCOUNT, {"tipo": ["acc_correos"]})
ok(r["fichas"] and r["fichas"][0]["id"].startswith("account_"), "por tipo de consejo")
try:
    ia.cerebro_get(ACCOUNT, {"id": ["../../etc/passwd"]})
    ok(False, "un id raro se rechaza")
except ia.Denegado:
    ok(True, "un id raro se rechaza")

print("4. POST /api/ia/cerebro")
r = ia.cerebro_post(ACCOUNT, ACCOUNT, {}, {"id": "account_correo_sin_responder", "cliente": "c1"})
ok(r["origen"] == "reglas" and r["ficha"]["id"] == "account_correo_sin_responder", "sin clave: la ficha tal cual, sin IA")
try:
    ia.cerebro_post(ACCOUNT, ACCOUNT, {}, {"id": "account_correo_sin_responder", "cliente": "c9"})
    ok(False, "un cliente ajeno se rechaza")
except ia.Denegado:
    ok(True, "un cliente ajeno se rechaza")

ia.estado_para = lambda persona: {"conectada": True, "motivo": None, "modelo": "simulado"}
ia.llamar = lambda *a, **k: ({"resumen": "El correo lleva días sin respuesta.", "pasos": [{"que": "Responde hoy con un acuse.", "porque": "La ficha lo pide."}],
                              "mensaje": "", "escalar": ""}, "simulado")
r = ia.cerebro_post(ACCOUNT, ACCOUNT, {}, {"id": "account_correo_sin_responder", "cliente": "c1"})
ok(r["origen"] == "vivo" and r["pasos"], "con IA: lo prudente pasa")
ia.llamar = lambda *a, **k: ({"resumen": "Ofrécele un 20 % de descuento.", "pasos": [], "mensaje": "", "escalar": ""}, "simulado")
r = ia.cerebro_post(ACCOUNT, ACCOUNT, {}, {"id": "account_correo_sin_responder", "cliente": "c1"})
ok(r["origen"] == "reglas", "con IA: un descuento o una cifra inventada no pasa; queda la ficha")
r = ia.cerebro_post(TOMAS, ACCOUNT, {}, {"id": "account_correo_sin_responder", "cliente": "c1"})
ok(r["origen"] == "reglas", "en «ver como» no se genera nada")

print("FALLA" if FALLOS else "OK", f"({len(FALLOS)} fallos)")
sys.exit(1 if FALLOS else 0)
