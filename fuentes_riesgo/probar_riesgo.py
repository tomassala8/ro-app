#!/usr/bin/env python3
"""fuentes_riesgo/probar_riesgo.py · pruebas del semáforo en tres ejes y del riesgo de baja (4-oct-2026).

Todo con clientes INVENTADOS (los datos reales viven fuera del repo). Sin red, sin servidor y sin IA.
  1. Cada eje por separado: resultados (objetivo, CPL, salud, arranque), silencio (7/14/30 días, otros canales,
     reunión agendada) y quejas (abierta, reciente, amenaza de baja).
  2. Cada combinación de Tomás da su patrón, su nivel y una ficha que EXISTE en el cerebro riesgo_baja.
  3. La tubería entera: data/ inventado en una carpeta temporal → riesgo_baja.json (con cliente_id en cada fila,
     persona_id en cada cartera y la escala de la D-41).
  4. La marca «se ha quejado esta semana» viaja por objetivos.py.

  python3 fuentes_riesgo/probar_riesgo.py
"""
import json
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(APP / "fuentes_objetivos"))
import riesgo_baja as RB  # noqa: E402

HOY = date(2026, 10, 5)
FALLOS = []


def ok(cond, que):
    print(("  ok   " if cond else "  FALLA ") + que)
    if not cond:
        FALLOS.append(que)


def d(n):
    return (HOY - timedelta(days=n)).isoformat()


BIEN = {"objetivo_leads_mes": 30, "leads_ritmo_mes": 32, "objetivo_cpl": 40, "cpl": 35}
MAL = {"objetivo_leads_mes": 30, "leads_ritmo_mes": 12, "objetivo_cpl": 40, "cpl": 70}
RESPONDE = {"ult_saliente": d(3), "ult_entrante": d(2), "tiene_entrante_desk": True}
CALLADO = {"ult_saliente": d(9), "ult_entrante": d(20), "tiene_entrante_desk": True}
QUEJA = [{"origen": "correo", "fecha": d(1), "texto": "Problema con los leads", "abierta": True}]


def cli(res, con, qs=(), **extra):
    return {"cliente_id": "inventado", "nombre": "Despacho Inventado", "resultados": res, "contacto": con, "quejas": list(qs), **extra}


print("1. Ejes")
R = RB.eje_resultados(BIEN)
ok(R["color"] == "verde", "resultados en objetivo → verde")
ok(RB.eje_resultados(MAL)["color"] == "rojo", "leads al 40 % y CPL 1,75× → rojo")
ok(RB.eje_resultados({"objetivo_leads_mes": 30, "leads_ritmo_mes": 22})["color"] == "ambar", "leads al 73 % → ámbar")
ok(RB.eje_resultados({"objetivo_cpl": 40, "cpl": 50})["color"] == "ambar", "CPL 1,25× → ámbar (igual que la ficha)")
ok(RB.eje_resultados({"gasto_14d": 300, "leads_14d": 0})["color"] == "rojo", "gasta sin leads en 14 días → rojo aunque no haya objetivo")
r = RB.eje_resultados({"salud": 45})
ok(r["color"] == "ambar" and r["confianza"] == "provisional", "sin objetivo: salud 45 → ámbar provisional")
r = RB.eje_resultados({**MAL, "dias_desde_alta": 20})
ok(r["color"] == "ambar" and r["arranque"], "en arranque (día 20) el rojo baja a ámbar")
ok(RB.eje_resultados({})["color"] == "gris", "sin nada → gris")

ok(RB.eje_silencio(RESPONDE, HOY)["color"] == "verde", "nos contestó después de nuestro correo → verde")
s = RB.eje_silencio({"ult_saliente": d(7), "ult_entrante": d(10), "tiene_entrante_desk": True}, HOY)
ok(s["color"] == "ambar" and s["dias_esperando"] == 7, "7 días sin responder a nuestro último correo → ámbar (Tomás)")
ok(RB.eje_silencio({"ult_saliente": d(15), "ult_entrante": d(16)}, HOY)["color"] == "rojo", "15 días → rojo")
ok(RB.eje_silencio({"ult_saliente": d(9), "ult_llamada_contestada": d(2)}, HOY)["color"] == "verde",
   "no contesta correos pero cogió el teléfono hace 2 días → verde")
ok(RB.eje_silencio({"ult_saliente": d(9), "ult_entrante_abierto": d(1)}, HOY)["color"] == "verde",
   "nos escribió ayer (correo pendiente nuestro) → él no está callado")
s = RB.eje_silencio({"ult_saliente": d(2), "ult_reunion": d(40)}, HOY)
ok(s["color"] == "rojo", "40 días sin ninguna respuesta suya → rojo aunque el correo sea reciente")
s = RB.eje_silencio({"ult_saliente": d(16), "ult_entrante": d(20), "prox_reunion": (HOY + timedelta(days=3)).isoformat()}, HOY)
ok(s["color"] == "ambar" and s["reunion_agendada"], "rojo con reunión agendada → ámbar")
ok(RB.eje_silencio({"ult_saliente": d(9)}, HOY)["confianza"] == "parcial", "sin último correo entrante de Desk → confianza parcial")

ok(RB.eje_quejas([], HOY)["color"] == "verde", "sin quejas → verde")
ok(RB.eje_quejas([], HOY, fuentes_ok=False)["color"] == "gris", "sin Desk ni semáforo → gris")
ok(RB.eje_quejas(QUEJA, HOY)["color"] == "rojo", "queja abierta → rojo")
q = RB.eje_quejas([{"origen": "semáforo del lunes", "fecha": d(12), "abierta": False}], HOY)
ok(q["color"] == "ambar", "queja de hace 12 días ya cerrada → ámbar (periodo amarillo)")
ok(RB.eje_quejas([{"fecha": d(45), "abierta": False}], HOY)["color"] == "verde", "queja de hace 45 días → verde")
q = RB.eje_quejas([{"origen": "correo", "fecha": d(1), "texto": "Queremos revisar el contrato y darnos de baja", "abierta": True}], HOY)
ok(q["amenaza_baja"], "«darnos de baja» → amenaza de baja")

print("2. Combinaciones (los ejemplos de Tomás y el resto)")
fichas = {s["id"] for s in json.loads((APP / "fuentes_consejos/cerebros/riesgo_baja.json").read_text())["situaciones"]}
CASOS = [
    ("todo bien", cli(BIEN, RESPONDE), "sano", "bajo"),
    ("buenos resultados pero se queja (Tomás)", cli(BIEN, RESPONDE, QUEJA), "queja_con_resultados", "alto"),
    ("malos resultados pero responde y feliz (Tomás)", cli(MAL, RESPONDE), "paciente_sin_resultados", "vigilar"),
    ("resultados flojos (ámbar) pero contento", cli({"objetivo_leads_mes": 30, "leads_ritmo_mes": 22}, RESPONDE), "paciente_sin_resultados", "vigilar"),
    ("buenos resultados y 9 días sin contestar", cli(BIEN, CALLADO), "silencio_con_resultados", "vigilar"),
    ("sin resultados y sin contestar", cli(MAL, CALLADO), "desenganche", "alto"),
    ("sin resultados y queja", cli(MAL, RESPONDE, QUEJA), "insatisfecho_declarado", "critico"),
    ("se quejó y se calló", cli(BIEN, CALLADO, [{"origen": "semáforo del lunes", "fecha": d(10), "abierta": False}]), "queja_y_silencio", "critico"),
    ("los tres mal", cli(MAL, CALLADO, QUEJA), "los_tres_mal", "critico"),
    ("sin datos", cli({}, {}, quejas_fuentes_ok=False), "sin_datos", "vigilar"),
    ("queja sin dato de resultados", cli({}, RESPONDE, QUEJA), "solo_queja", "alto"),
]
for nombre, entrada, patron, nivel in CASOS:
    f = RB.calcular(entrada, HOY)
    ok(f["patron"] == patron and f["nivel"] == nivel, f"{nombre} → {f['patron']} · {f['nivel']} (esperado {patron} · {nivel})")
    ok(f["ficha"] in fichas, f"   su ficha {f['ficha']} existe en el cerebro")
ok({p[1] for p in RB.PATRONES.values()} <= fichas, "todas las fichas de PATRONES existen")
f = RB.calcular(cli(BIEN, RESPONDE, [{"origen": "correo", "fecha": d(1), "texto": "Nos planteamos una paradita", "abierta": True}]), HOY)
ok(f["nivel"] == "critico", "amenaza de baja sube a crítico aunque los resultados vayan bien")
f = RB.calcular(cli(MAL, CALLADO, semaforo_account={"color": "verde", "semana": d(0)}), HOY)
ok(bool(f["discrepancia"]), "semáforo del lunes en verde con riesgo alto → discrepancia")
f = RB.calcular(cli(BIEN, RESPONDE, semaforo_account={"color": "rojo"}), HOY)
ok(bool(f["discrepancia"]), "account en rojo y datos en verde → discrepancia (que apunte el motivo)")

print("3. Tubería con data/ inventado")
with tempfile.TemporaryDirectory() as t:
    D = Path(t)
    (D / "clientes").mkdir()
    (D / "objetivos").mkdir()
    (D / "bandeja").mkdir()
    (D / "verdad").mkdir()

    def fichero(cid, nombre, meta=None, desk=None, extra=None, libro="Activo"):
        fu = {"cartera": {"estado": "bien", "datos": {"account": "Persona A", "riesgo_panel": 30}},
              "desk": {"estado": "bien", "datos": desk or {}}, **(extra or {})}
        if meta:
            fu["meta"] = {"estado": "bien", "datos": meta}
        (D / "clientes" / f"{cid}.json").write_text(json.dumps({"id": cid, "nombre": nombre, "activo_libro": libro, "fuentes": fu}))

    fichero("uno", "Uno Asesores", meta={"leads": {"14d": 15}, "cpl": {"14d": 35}, "gasto": {"14d": 525}},
            desk={"ult_correo_saliente": d(3), "ult_correo_entrante": d(1)})
    fichero("dos", "Dos Abogados", meta={"leads": {"14d": 0}, "cpl": {"14d": None}, "gasto": {"14d": 400}},
            desk={"ult_correo_saliente": d(10), "ult_correo_entrante": d(25)})
    fichero("tres", "Tres Gestoría", desk={"ult_correo_saliente": d(2)},
            extra={"zadarma": {"estado": "bien", "datos": {"octubre": {"ultima_contestada": d(1)}}}})
    fichero("baja", "Ya Baja", libro="Baja")
    (D / "objetivos/objetivos.json").write_text(json.dumps({"clientes": [
        {"cliente_id": "uno", "objetivo": {"leads_mes": 30, "coste_lead": 40}, "semaforo": {"color": "verde", "semana": d(0)},
         "semanas": [{"semana": d(0), "color": "verde", "queja": True, "nota": "Se quejó en la llamada del trato"}]},
        {"cliente_id": "dos", "objetivo": {"leads_mes": 20}, "semaforo": {"color": "verde", "semana": d(0)}, "semanas": []}]}))
    (D / "bandeja/bandeja.json").write_text(json.dumps({"correos": [
        {"cliente_id": "tres", "asunto": "Sin leads esta semana", "queja": True, "auto": False, "desde": d(1) + " 10:00", "url": "https://desk.example/1"}]}))
    (D / "verdad/clientes.json").write_text(json.dumps({"comun": [{"cliente_id": c, "account": "persona_a"} for c in ("uno", "dos", "tres")]}))
    RB.DATA, RB.SALIDA = D, D / "riesgo" / "riesgo_baja.json"
    out = RB.generar(HOY)
    por = {f["cliente_id"]: f for f in out["clientes"]}
    ok(set(por) == {"uno", "dos", "tres"}, "solo clientes activos (la baja no sale)")
    ok(por["uno"]["patron"] == "queja_con_resultados", f"uno: en objetivo + queja marcada por el account → {por['uno']['patron']}")
    ok(por["dos"]["patron"] == "desenganche" and por["dos"]["nivel"] == "alto" and por["dos"]["discrepancia"], f"dos: gasta sin leads + 10 días callado → {por['dos']['patron']} · {por['dos']['nivel']}, y el lunes decía verde")
    ok(por["tres"]["semaforo"]["quejas"] == "rojo" and por["tres"]["semaforo"]["silencio"] == "verde",
       "tres: correo «Sin leads» → queja; nos escribió ayer → no está callado")
    ok(all(f.get("cliente_id") for f in out["clientes"]), "cada fila lleva cliente_id (el servidor recorta por cliente)")
    c = out["carteras"][0]
    ok(c["persona_id"] == "persona_a" and all(x.get("cliente_id") for x in c["en_riesgo"]), "la cartera lleva persona_id y cliente_id en cada cliente")
    ok(c["estado"] == "vigilar" and len(c["en_riesgo"]) == 3, f"3 clientes en riesgo alto o crítico → «vigilar» (escala D-41): {c['estado']}")
    ok(RB.SALIDA.exists() and json.loads(RB.SALIDA.read_text())["formato"] == 1, "escribe riesgo_baja.json")

print("4. La marca de queja en objetivos.py")
import objetivos as OB  # noqa: E402
n = OB.normalizar({"id": 1, "tipo": OB.TIPO_SEMAFORO, "cliente_id": "uno", "creada": "2026-10-05 08:00:00",
                   "vista_previa": json.dumps({"color": "ambar", "nota": "Se quejó", "queja": True})})
ok(n.get("queja") is True, "normalizar() conserva queja")
red = OB.reducir([n])
ok(red["uno"]["semaforo"]["queja"] is True and red["uno"]["semanas"][0]["queja"] is True, "reducir() la lleva al semáforo y al historial")
n2 = OB.normalizar({"id": 2, "tipo": OB.TIPO_SEMAFORO, "cliente_id": "uno", "creada": "2026-10-05 08:00:00",
                    "vista_previa": json.dumps({"color": "verde", "queja": "sí"})})
ok(n2.get("queja") is False, "solo true cuenta como queja (no textos)")
js = (APP / "modulos/objetivos_comun.js").read_text()
ok("out.queja = vp.queja === true" in js and "queja: !!f.queja" in js, "objetivos_comun.js repite la misma regla")

print(f"\n{'FALLA' if FALLOS else 'OK'} ({len(FALLOS)} fallos)")
sys.exit(1 if FALLOS else 0)
