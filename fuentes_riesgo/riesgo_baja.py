#!/usr/bin/env python3
"""fuentes_riesgo/riesgo_baja.py · Semáforo del cliente en TRES EJES y riesgo de baja (4-oct-2026). Sin red y sin IA.

Petición de Tomás (4-oct): que el semáforo del cliente distinga tres cosas, porque una sola no basta para ver una baja:
  · RESULTADOS  — ¿le estamos dando lo que espera? (leads, coste por lead y citas contra su objetivo; si no, la salud).
  · SILENCIO    — la RELACIÓN: ¿nos contesta, viene y está cálido? (días desde nuestro último correo sin que él responda
                  por ningún canal; si asiste a las reuniones; y la calidez en la reunión, que marca el account cada lunes).
                  En la pantalla se llama «Relación». Los resultados NO entran aquí: un cliente puede no decir nada malo
                  en la reunión y no estar recibiendo nada (Tomás, 4-oct).
  · QUEJAS      — ¿se está quejando? (correo de queja abierto, incidencia con queja, rojo a mano, o el account lo marca).
Buenos resultados con quejas, o malos resultados con un cliente que responde contento, son situaciones distintas y piden
cosas distintas. La COMBINACIÓN de los tres ejes da un patrón con nombre y un nivel de riesgo de baja, y cada patrón
apunta a su ficha del cerebro `fuentes_consejos/cerebros/riesgo_baja.json` (qué significa y qué hacer hoy).

Lee lo que ya deja la tubería (nada nuevo que conectar para empezar):
  · data/clientes/<id>.json        cartera (semáforo de ClickUp, nuevo, rojo a mano, salud del panel), meta (leads, CPL),
                                   captacion_ghl (citas), desk (último correo nuestro), zadarma (última llamada contestada),
                                   reuniones (última y próxima), arranque (fecha de alta)
  · data/objetivos/objetivos.json  objetivo del cliente y semáforo del lunes (con la marca «se ha quejado esta semana»)
  · data/bandeja/bandeja.json      correos del cliente sin contestar (su fecha cuenta como respuesta; la marca de queja)
  · data/incidencias/incidencias.json  incidencias con queja
  · data/diagnosticos/diagnosticos.json  dónde se cae el embudo (veredicto_embudo, PR #3), como causa probable si los
                                   resultados están en ámbar o rojo; si no existe, se ignora
  · data/agenda/agenda.json        reuniones con el cliente de los últimos 14 días: «noshow» (Bookings, GHL), «showed» o
                                   grabación de Zoom pegada (celebrada); las que no constan como celebradas
Escribe data/riesgo/riesgo_baja.json: una fila por cliente (con cliente_id: el servidor solo la manda a quien ve ese
cliente) y un resumen por account con la escala de la D-41 (≤ 2 bien · 3-4 vigilar · ≥ 5 crítico).

Lo que FALTA en los datos (está dicho en cada fila como «confianza»):
  · Silencio: de Desk solo llega la fecha de NUESTRO último correo y los correos del cliente que siguen abiertos. Falta la
    fecha del último correo del cliente en tickets ya cerrados → campo `desk.ult_correo_entrante` (ver LEEME.md). Mientras
    no llegue, el silencio usa llamadas contestadas y reuniones, y sale con confianza «parcial».
  · Quejas: hoy solo se detectan por el ASUNTO del correo (expresión del panel). El texto del correo, las reuniones
    (Fathom) y WhatsApp no se miran. Por eso el account puede marcar «se ha quejado esta semana» en el semáforo del lunes.

  python3 fuentes_riesgo/riesgo_baja.py                 # escribe data/riesgo/riesgo_baja.json
  python3 fuentes_riesgo/riesgo_baja.py --cliente gac   # enseña un cliente, sin escribir
"""
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
DATA = APP / "data"
SALIDA = DATA / "riesgo" / "riesgo_baja.json"

# Umbrales firmados por Tomás el 4-oct-2026: silencio 7 días ámbar y 14 rojo, verde desde el 90 % del objetivo y
# 30 días de ámbar tras una queja. El resto sigue la propuesta del mismo día. Todos aquí, para cambiarlos en un solo sitio.
UMBRALES = {
    "silencio_ambar_dias": 7,        # Tomás: «no responde desde hace, por ejemplo, siete días a nuestro último mail»
    "silencio_rojo_dias": 14,        # dos semanas esperando: ya no es despiste
    "sin_contacto_rojo_dias": 30,    # ia.py y consejero-account-ro: «30 días sin reunión o contacto, bandera»
    "objetivo_verde": 0.9,           # leads o citas al ritmo del mes ≥ 90 % del objetivo
    "objetivo_ambar": 0.6,           # 60-90 % ámbar · < 60 % rojo
    "cpl_ambar": 1.3,                # coste por lead hasta 1,3 × el objetivo, ámbar (igual que la ficha)
    "salud_verde": 60, "salud_ambar": 40,   # igual que el chip de salud de la ficha
    "arranque_dias": 60,             # en los primeros 60 días los resultados no ponen rojo (sí ámbar)
    "queja_reciente_dias": 30,       # tras una queja hay «periodo amarillo»: no se vuelve directo a verde
    "reuniones_dias": 30,            # ventana para contar las reuniones a las que no vino
    "no_asiste_rojo": 2,             # 1 reunión sin presentarse o cancelada sin reagendar → ámbar · 2 o más → rojo
    "sin_constancia_ambar": 2,       # 2 reuniones pasadas sin constancia de que se celebraran → ámbar
    "tono_semanas": 4,               # calidez: se miran las últimas 4 semanas del semáforo del lunes
    "frio_rojo": 2,                  # frío 1 vez → ámbar · 2 o más → rojo
    "cartera": (2, 4),               # escala de la D-41: ≤ 2 bien · 3-4 vigilar · ≥ 5 crítico
}
FIRMADO = True    # Tomás firmó los umbrales principales el 4-oct-2026

COLORES = ("verde", "ambar", "rojo", "gris")
PESO = {"verde": 0, "gris": 0, "ambar": 1, "rojo": 2}
NIVELES = ("bajo", "vigilar", "alto", "critico")
NIVEL_TXT = {"bajo": "Bajo", "vigilar": "Vigilar", "alto": "Alto", "critico": "Crítico"}
# Amenaza de baja en el texto: pasa la queja a crítico (misma familia que la expresión _QUEJA del panel, más estrecha)
RE_AMENAZA = re.compile(r"\bbaja\b|cancel|rescind|dejar de trabajar|no renov|otra agencia|parad[ia]ta|pausar|"
                        r"revisar el contrato|fin del contrato|terminar (?:el|la) (?:contrato|colaboraci)", re.I)
RE_QUEJA = re.compile(r"sin leads|urgente|queja|molest|reclam|no funciona|problema|error|insatisf|decepcion|"
                      r"no estoy content|no veo resultados|pago demasiado|esto no funciona", re.I)


# ------------------------------------------------------------------------------------------------ utilidades
def _fecha(v):
    if not v:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    try:
        return date.fromisoformat(str(v).strip()[:10])
    except ValueError:
        return None


def _dias(desde, hoy):
    d = _fecha(desde)
    return None if d is None else (hoy - d).days


def _num(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if x != x else x


def _ventana(d, *claves):
    """meta.leads puede venir como {"14d": n, "mes": n, …} o como número suelto. Devuelve el primero que haya."""
    if isinstance(d, dict):
        for k in claves:
            if _num(d.get(k)) is not None:
                return _num(d.get(k))
        return None
    return _num(d)


def _peor(colores):
    medidos = [c for c in colores if c in ("verde", "ambar", "rojo")]
    return max(medidos, key=lambda c: PESO[c]) if medidos else "gris"


# ------------------------------------------------------------------------------------------------ los tres ejes
def eje_resultados(r, hoy=None):
    """r: {objetivo_leads_mes, leads_ritmo_mes, objetivo_cpl, cpl, objetivo_citas_mes, citas_ritmo_mes,
           gasto_14d, leads_14d, salud, dias_desde_alta}. Devuelve {color, motivos, medido, confianza}."""
    U = UMBRALES
    colores, motivos, medido = [], [], []

    def ratio_mas_es_mejor(nombre, valor, objetivo):
        if valor is None or not objetivo:
            return
        x = valor / objetivo
        c = "verde" if x >= U["objetivo_verde"] else "ambar" if x >= U["objetivo_ambar"] else "rojo"
        colores.append(c)
        medido.append(nombre)
        if c != "verde":
            motivos.append(f"{nombre} al {round(x * 100)} % del objetivo ({round(valor)} de {round(objetivo)} al mes)")

    ratio_mas_es_mejor("Leads", _num(r.get("leads_ritmo_mes")), _num(r.get("objetivo_leads_mes")))
    ratio_mas_es_mejor("Citas", _num(r.get("citas_ritmo_mes")), _num(r.get("objetivo_citas_mes")))
    cpl, obj_cpl = _num(r.get("cpl")), _num(r.get("objetivo_cpl"))
    if cpl is not None and obj_cpl:
        x = cpl / obj_cpl
        c = "verde" if x <= 1.0 else "ambar" if x <= U["cpl_ambar"] else "rojo"
        colores.append(c)
        medido.append("Coste por lead")
        if c != "verde":
            motivos.append(f"Coste por lead {round(x * 100)} % del objetivo")
    gasto, leads14 = _num(r.get("gasto_14d")), _num(r.get("leads_14d"))
    if gasto and gasto > 0 and leads14 == 0:
        colores.append("rojo")
        medido.append("Leads")
        motivos.append("Gasta en publicidad y no ha entrado ningún lead en 14 días")
    confianza = "medido"
    if not colores:
        salud = _num(r.get("salud"))
        if salud is not None:
            c = "verde" if salud >= U["salud_verde"] else "ambar" if salud >= U["salud_ambar"] else "rojo"
            colores.append(c)
            medido.append("Salud")
            confianza = "provisional"
            if c != "verde":
                motivos.append(f"Salud {round(salud)} (provisional, sin objetivo cargado)")
    color = _peor(colores)
    alta = _num(r.get("dias_desde_alta"))
    arranque = alta is not None and alta < U["arranque_dias"]
    if arranque and color == "rojo" and not (gasto and leads14 == 0):
        color = "ambar"
        motivos.append(f"En arranque (día {int(alta)}): todavía no pone rojo")
    if color == "gris":
        confianza = "sin_dato"
        motivos.append("Sin objetivo cargado ni salud: no se puede juzgar")
    # Dónde se cae el embudo (diagnósticos de calidad, PR #3): leads malos ≠ despacho que no atiende ≠ no vienen.
    ve = r.get("veredicto_embudo") or {}
    causa = None
    if color in ("ambar", "rojo") and ve.get("veredicto") not in (None, "sin_dato", "embudo_sano"):
        causa = {"veredicto": ve["veredicto"], "frase": ve.get("frase")}
        if ve.get("frase"):
            motivos.append(f"Causa probable: {ve['frase']}")
    return {"color": color, "motivos": motivos, "medido": sorted(set(medido)), "confianza": confianza, "arranque": arranque,
            "causa_probable": causa}


def eje_silencio(c, hoy):
    """c: {ult_saliente, ult_entrante, ult_entrante_abierto, ult_llamada_contestada, ult_reunion, prox_reunion,
           tiene_entrante_desk(bool), reuniones_pasadas[{fecha, estado: asistio|no_asistio|cancelo_sin_reagendar|sin_constancia}],
           tonos[{semana, tono: calido|normal|frio}] (lo marca el account en el semáforo del lunes)}. «Silencio» es el del CLIENTE: si él escribió y nosotros no, no está callado."""
    U = UMBRALES
    respuestas = [(_fecha(c.get(k)), nom) for k, nom in (("ult_entrante", "correo"), ("ult_entrante_abierto", "correo"),
                                                        ("ult_llamada_contestada", "llamada"), ("ult_reunion", "reunión"))]
    respuestas = [(f, n) for f, n in respuestas if f and f <= hoy]
    ult_resp, canal = max(respuestas) if respuestas else (None, None)
    salida = _fecha(c.get("ult_saliente"))
    prox = _fecha(c.get("prox_reunion"))
    reunion_agendada = bool(prox and prox >= hoy)
    esperando = (hoy - salida).days if salida and (not ult_resp or ult_resp < salida) else 0
    sin_contacto = (hoy - ult_resp).days if ult_resp else None
    motivos = []
    if salida is None and ult_resp is None:
        color = "gris"
        motivos.append("Sin fechas de correo, llamada ni reunión")
    else:
        color = "verde"
        if esperando >= U["silencio_rojo_dias"]:
            color = "rojo"
        elif esperando >= U["silencio_ambar_dias"]:
            color = "ambar"
        if esperando >= U["silencio_ambar_dias"]:
            motivos.append(f"{esperando} días sin responder a nuestro último correo")
        if sin_contacto is not None and sin_contacto >= U["sin_contacto_rojo_dias"]:
            color = "rojo"
            motivos.append(f"{sin_contacto} días sin ninguna respuesta suya (correo, llamada o reunión)")
    # Asistencia a reuniones (Tomás, 4-oct): no presentarse es la señal 2 del código semafórico (cancelar sin reagendar).
    ventana = [r for r in c.get("reuniones_pasadas") or []
               if (_dias(r.get("fecha"), hoy) is not None and 0 <= _dias(r.get("fecha"), hoy) <= U["reuniones_dias"])]
    no_vino = sorted(r["fecha"][:10] for r in ventana if r.get("estado") == "no_asistio")
    cancelo = sorted(r["fecha"][:10] for r in ventana if r.get("estado") == "cancelo_sin_reagendar")
    dudosas = sorted(r["fecha"][:10] for r in ventana if r.get("estado") == "sin_constancia")
    vino = sum(1 for r in ventana if r.get("estado") == "asistio")
    if no_vino or cancelo:     # faltar y cancelar sin reagendar cuentan igual: 1 → ámbar · 2 o más → rojo
        c_asist = "rojo" if len(no_vino) + len(cancelo) >= U["no_asiste_rojo"] else "ambar"
        if no_vino:
            motivos.append(f"No se presentó a {len(no_vino)} reunión{'es' if len(no_vino) > 1 else ''} ({', '.join(no_vino)})")
        if cancelo:
            motivos.append(f"Canceló {len(cancelo)} reunión{'es' if len(cancelo) > 1 else ''} sin reagendar ({', '.join(cancelo)})")
    elif len(dudosas) >= U["sin_constancia_ambar"]:
        c_asist = "ambar"
        motivos.append(f"{len(dudosas)} reuniones agendadas sin constancia de que se celebraran ({', '.join(dudosas)})")
    else:
        c_asist = "verde" if ventana else None
        if dudosas:
            motivos.append(f"La reunión del {dudosas[0]} no consta como celebrada")
    if c_asist:
        if color == "gris":
            motivos = [m for m in motivos if not m.startswith("Sin fechas")]
        color = c_asist if color == "gris" else _peor([color, c_asist])
    # Calidez (Tomás, 4-oct): cómo estuvo en la reunión o la llamada. Solo lo sabe el account: lo marca cada lunes.
    tonos = [t for t in c.get("tonos") or [] if _dias(t.get("semana"), hoy) is not None
             and 0 <= _dias(t.get("semana"), hoy) < 7 * U["tono_semanas"]]
    frios = sorted(t["semana"] for t in tonos if t.get("tono") == "frio")
    if frios:
        c_tono = "rojo" if len(frios) >= U["frio_rojo"] else "ambar"
        motivos.append(f"Frío en la reunión {len(frios)} semana{'s' if len(frios) > 1 else ''} de las últimas {U['tono_semanas']}")
        if color == "gris":
            motivos = [m for m in motivos if not m.startswith("Sin fechas")]
        color = c_tono if color == "gris" else _peor([color, c_tono])
    if color == "rojo" and reunion_agendada and not no_vino and not cancelo and not frios:     # si falta a las reuniones, tenerla agendada no calma
        color = "ambar"
        motivos.append(f"Tiene reunión el {prox.isoformat()}: baja a ámbar")
    confianza = "medido" if c.get("tiene_entrante_desk") else "parcial"
    return {"color": color, "motivos": motivos, "dias_esperando": esperando or 0, "dias_sin_respuesta": sin_contacto,
            "ultima_respuesta": ult_resp.isoformat() if ult_resp else None, "canal_ultima_respuesta": canal,
            "ultimo_nuestro": salida.isoformat() if salida else None, "reunion_agendada": reunion_agendada,
            "reuniones": {"asistio": vino, "no_asistio": len(no_vino), "cancelo_sin_reagendar": len(cancelo), "sin_constancia": len(dudosas)},
            "tono": tonos[0]["tono"] if tonos else None, "semanas_frio": len(frios),
            "confianza": confianza}


def eje_quejas(qs, hoy, fuentes_ok=True):
    """qs: [{origen, fecha, texto, abierta}]. Abierta → rojo; amenaza de baja → rojo con «amenaza»;
    cerrada en los últimos 30 días → ámbar (después de rojo siempre hay amarillo); nada → verde."""
    U = UMBRALES
    abiertas, recientes, amenaza = [], [], False
    for q in qs or []:
        d = _dias(q.get("fecha"), hoy)
        if q.get("abierta"):
            abiertas.append(q)
        elif d is not None and d <= U["queja_reciente_dias"]:
            recientes.append(q)
        else:
            continue
        if q.get("amenaza_baja") or RE_AMENAZA.search(str(q.get("texto") or "")):
            amenaza = True
    motivos = []
    if abiertas:
        color = "rojo"
        motivos.append(f"{len(abiertas)} queja{'s' if len(abiertas) > 1 else ''} abierta{'s' if len(abiertas) > 1 else ''} "
                       f"({', '.join(sorted({q.get('origen') or '?' for q in abiertas}))})")
    elif recientes:
        color = "ambar"
        motivos.append(f"Se quejó hace {min(_dias(q.get('fecha'), hoy) for q in recientes)} días: periodo amarillo")
    else:
        color = "verde" if fuentes_ok else "gris"
        if not fuentes_ok:
            motivos.append("Sin Desk ni semáforo del lunes: no se puede saber si se queja")
    if amenaza:
        color = "rojo"
        motivos.append("Habla de baja, pausa o contrato")
    return {"color": color, "motivos": motivos, "abiertas": len(abiertas), "recientes": len(recientes), "amenaza_baja": amenaza,
            "detalle": [{k: q.get(k) for k in ("origen", "fecha", "texto", "abierta", "url")} for q in (abiertas + recientes)[:5]],
            "confianza": "parcial"}   # hoy solo asunto del correo + marca del account (ver cabecera)


# ------------------------------------------------------------------------------------------------ la combinación
# Cada patrón: nivel de riesgo, ficha del cerebro riesgo_baja y una lectura de una línea para el account.
PATRONES = {
    "sano": ("bajo", "rb_sano_mantener", "Resultados, respuesta y tono bien: mantener el ritmo y pedir referidos cuando toque."),
    "los_tres_mal": ("critico", "rb_los_tres_ejes_mal", "Malos resultados, se queja y no contesta o no viene a las reuniones: baja casi decidida, hoy con Coti y Tomás."),
    "queja_y_silencio": ("critico", "rb_queja_y_silencio", "Se quejó y luego se ha callado o falta a las reuniones: está decidiendo sin nosotros. Llamar hoy."),
    "insatisfecho_declarado": ("alto", "rb_sin_resultados_y_queja", "Sin resultados y lo dice: la queja tiene base. Plan con datos antes de hablar."),
    "desenganche": ("alto", "rb_sin_resultados_y_silencio", "Sin resultados y sin contestar o sin venir a las reuniones: se está desenganchando en silencio."),
    "queja_con_resultados": ("alto", "rb_queja_con_resultados", "Los números van bien pero se queja: el problema es el servicio, el trato o la expectativa."),
    "silencio_con_resultados": ("vigilar", "rb_silencio_con_resultados", "Los números van bien pero no contesta o no viene a las reuniones: puede estar contento o desconectado. Llamar."),
    "paciente_sin_resultados": ("vigilar", "rb_sin_resultados_pero_contento", "No llegan los resultados aunque en la reunión no diga nada malo: muchos se callan y lo sueltan de golpe. Cuéntaselo tú antes."),
    "solo_queja": ("alto", "rb_queja_con_resultados", "Se queja y no hay dato de resultados para contrastar: escúchale y carga el objetivo."),
    "solo_silencio": ("vigilar", "rb_silencio_con_resultados", "No contesta o no viene y no hay dato de resultados: llamar y cargar el objetivo."),
    "sin_datos": ("vigilar", "rb_sin_datos_para_juzgar", "Faltan datos para juzgar al cliente: el riesgo no se ve, no es que no exista."),
}
ORDEN_NIVEL = {n: i for i, n in enumerate(NIVELES)}


def combinar(R, S, Q):
    """Tres ejes → {patron, nivel, puntos, ficha, lectura}. Un eje en gris no cuenta como bueno ni como malo."""
    r, s, q = R["color"], S["color"], Q["color"]
    mal = lambda c: c in ("ambar", "rojo")
    rojo_en = [n for n, c in (("resultados", r), ("silencio", s), ("quejas", q)) if c == "rojo"]
    if mal(r) and mal(s) and mal(q):
        p = "los_tres_mal"
    elif mal(q) and mal(s):
        p = "queja_y_silencio"
    elif mal(r) and mal(q):
        p = "insatisfecho_declarado"
    elif mal(r) and mal(s):
        p = "desenganche"
    elif mal(q):
        p = "queja_con_resultados" if r == "verde" else "solo_queja"
    elif mal(s):
        p = "silencio_con_resultados" if r == "verde" else "solo_silencio"
    elif mal(r):
        p = "paciente_sin_resultados"
    elif "gris" in (r, s, q) and [r, s, q].count("gris") >= 2:
        p = "sin_datos"
    else:
        p = "sano"
    nivel, ficha, lectura = PATRONES[p]
    # Ajustes por intensidad: dos ejes en rojo suben un escalón; queja solo en ámbar (ya cerrada) baja a vigilar; silencio
    # en rojo con buenos resultados sube a alto; sin resultados medidos en rojo sube a alto aunque el cliente no se queje.
    if p in ("insatisfecho_declarado", "desenganche") and len(rojo_en) >= 2:
        nivel = "critico"
    if p == "queja_con_resultados" and q == "ambar":
        nivel = "vigilar"
    if p == "silencio_con_resultados" and s == "rojo":
        nivel = "alto"
    if p == "paciente_sin_resultados" and r == "rojo" and R.get("confianza") == "medido" and not R.get("arranque"):
        nivel = "alto"      # Tomás: «el cliente se calla y luego de golpe lo dice»
    if Q.get("amenaza_baja"):
        nivel = "critico"
    puntos = PESO[r] + PESO[s] + (3 if q == "rojo" else PESO[q]) + (2 if Q.get("amenaza_baja") else 0)
    return {"patron": p, "nivel": nivel, "nivel_txt": NIVEL_TXT[nivel], "puntos": puntos, "ficha": ficha, "lectura": lectura,
            "ejes_en_rojo": rojo_en}


def calcular(entrada, hoy=None):
    """entrada normalizada de UN cliente → fila de riesgo_baja.json. Es la función que prueban probar_riesgo.py."""
    hoy = _fecha(hoy) or date.today()
    R = eje_resultados(entrada.get("resultados") or {}, hoy)
    S = eje_silencio(entrada.get("contacto") or {}, hoy)
    Q = eje_quejas(entrada.get("quejas") or [], hoy, entrada.get("quejas_fuentes_ok", True))
    comb = combinar(R, S, Q)
    sem = entrada.get("semaforo_account") or {}
    discrepancia = None
    if sem.get("color") == "verde" and R["color"] in ("ambar", "rojo") and R["confianza"] == "medido":
        # Tomás, 4-oct: el account pone verde porque en la reunión el cliente no dice nada malo, pero no hay resultados;
        # muchos se callan y luego lo sueltan de golpe. Los resultados se juzgan con datos, no con el tono de la reunión.
        discrepancia = (f"El semáforo del lunes dice verde y los resultados están en {'rojo' if R['color'] == 'rojo' else 'ámbar'}: "
                        "que no se queje en la reunión no quiere decir que esté bien")
    elif sem.get("color") == "verde" and comb["nivel"] in ("alto", "critico"):
        discrepancia = f"El semáforo del lunes dice verde y los tres ejes dicen riesgo {comb['nivel_txt'].lower()}"
    elif sem.get("color") == "rojo" and comb["nivel"] == "bajo":
        discrepancia = "El account lo tiene en rojo y los datos no lo ven: apunta el motivo en la nota (los datos no lo saben todo)"
    confianza = "baja" if [R["color"], S["color"], Q["color"]].count("gris") >= 2 or R["confianza"] == "sin_dato" else \
        "media" if S["confianza"] == "parcial" or R["confianza"] == "provisional" else "alta"
    return {
        "cliente_id": entrada.get("cliente_id"), "cliente": entrada.get("nombre"),
        "account_id": entrada.get("account_id"), "account": entrada.get("account"),
        "ejes": {"resultados": R, "silencio": S, "quejas": Q},
        "semaforo": {"resultados": R["color"], "silencio": S["color"], "quejas": Q["color"]},
        **comb,
        "semaforo_account": {k: sem.get(k) for k in ("color", "semana", "nota")} if sem else None,
        "discrepancia": discrepancia,
        "confianza": confianza,
    }


# ------------------------------------------------------------------------------------------------ de la tubería a la entrada
def _j(p, por_defecto=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return por_defecto


def _datos(doc, fuente):
    b = ((doc or {}).get("fuentes") or {}).get(fuente) or {}
    return b.get("datos") or {}, b.get("estado")


def _ritmo_mes(ventanas, hoy):
    """Leads o citas al ritmo de un mes: 14 días × 30/14; si no, lo que va de mes prorrateado; si no, el mes anterior."""
    v14 = _ventana(ventanas, "14d")
    if v14 is not None:
        return v14 * 30 / 14
    mes = _ventana(ventanas, "mes")
    if mes is not None and hoy.day >= 7:
        return mes * 30 / hoy.day
    return _ventana(ventanas, "mes_anterior")


def reuniones_de(cid, eventos, historial, hoy, canceladas=None):
    """Reuniones con el cliente ya pasadas, de la agenda: asistió (showed, grabación de Zoom pegada o la reunión consta en
    el historial de Reuniones ese día), no asistió (noshow) o sin constancia. Las canceladas (lista aparte de la agenda)
    cuentan como «canceló sin reagendar» si después no hay otra reunión con ese cliente, pasada o futura."""
    celebradas = {str(h.get("fecha") or "")[:10] for h in historial or []}
    suyas = [e for e in eventos or [] if e.get("tipo") == "cliente" and e.get("cliente_ref") == cid and e.get("inicio")]
    por_dia = {}     # la misma reunión sale una vez por cada persona de RO que la tiene en su agenda: una por día
    for e in suyas:
        dia = str(e["inicio"])[:10]
        if _fecha(dia) is None or _fecha(dia) >= hoy:      # hoy aún puede celebrarse
            continue
        est = str(e.get("estado_cita") or "").lower()
        if est == "showed" or e.get("celebrada") or dia in celebradas:
            estado = "asistio"
        elif est == "noshow":
            estado = "no_asistio"
        else:
            estado = "sin_constancia"
        previo = por_dia.get(dia)
        if not previo or ORDEN_ASISTENCIA[estado] < ORDEN_ASISTENCIA[previo["estado"]]:   # manda lo celebrado
            por_dia[dia] = {"fecha": dia, "estado": estado, "fuente": e.get("fuente")}
    for e in canceladas or []:
        if e.get("cliente_ref") != cid or _fecha(str(e.get("inicio") or "")[:10]) is None:
            continue
        dia = str(e["inicio"])[:10]
        if any(str(x["inicio"])[:10] >= dia for x in suyas):      # la reagendó (o ya tenía otra): no es señal
            continue
        fecha = min(_fecha(dia), hoy).isoformat()                  # una cancelada de la semana que viene ya cuenta hoy
        if fecha not in por_dia:
            por_dia[fecha] = {"fecha": fecha, "estado": "cancelo_sin_reagendar", "fuente": e.get("fuente")}
    return sorted(por_dia.values(), key=lambda r: r["fecha"])


ORDEN_ASISTENCIA = {"asistio": 0, "no_asistio": 1, "cancelo_sin_reagendar": 2, "sin_constancia": 3}


def entrada_de(doc, obj, correos, incidencias, hoy, account_id=None, eventos=None, diag=None, canceladas=None):
    """Fichero de cliente + objetivos + bandeja + incidencias → entrada normalizada para calcular()."""
    cid = doc.get("id")
    cart, _ = _datos(doc, "cartera")
    meta, _ = _datos(doc, "meta")
    ghl, _ = _datos(doc, "captacion_ghl")
    desk, est_desk = _datos(doc, "desk")
    zad, _ = _datos(doc, "zadarma")
    reu, _ = _datos(doc, "reuniones")
    arr, _ = _datos(doc, "arranque")
    o = (obj or {}).get("objetivo") or {}
    sem = (obj or {}).get("semaforo") or {}
    alta = _fecha(arr.get("alta"))
    res = {
        "objetivo_leads_mes": o.get("leads_mes"), "leads_ritmo_mes": _ritmo_mes(meta.get("leads"), hoy),
        "objetivo_cpl": o.get("coste_lead") or (meta.get("objetivo") if isinstance(meta.get("objetivo"), (int, float)) else None),
        "cpl": _ventana(meta.get("cpl"), "14d", "mes", "35d"),
        "objetivo_citas_mes": o.get("citas_mes"), "citas_ritmo_mes": _ritmo_mes(ghl.get("citas"), hoy),
        "gasto_14d": _ventana(meta.get("gasto"), "14d"), "leads_14d": _ventana(meta.get("leads"), "14d"),
        "salud": None if cart.get("riesgo_panel") is None else max(0, 100 - (_num(cart.get("riesgo_panel")) or 0)),
        "dias_desde_alta": (hoy - alta).days if alta else None,
        "veredicto_embudo": (diag or {}).get("veredicto_embudo"),
    }
    mios = [c for c in correos if c.get("cliente_id") == cid and not c.get("auto")]
    zl = [((zad.get(m) or {}).get("ultima_contestada")) for m in ("octubre", "septiembre")]
    con = {
        "ult_saliente": desk.get("ult_correo_saliente"),
        "ult_entrante": desk.get("ult_correo_entrante"),          # todavía no lo trae nadie: ver LEEME.md
        "ult_entrante_abierto": max((c.get("desde") or "" for c in mios), default=None) or
                                max(((t.get("desde") or "") for t in desk.get("sin_contestar") or []), default=None) or None,
        "ult_llamada_contestada": max((x for x in zl if x), default=None),
        "ult_reunion": reu.get("ult_reunion"), "prox_reunion": reu.get("prox_reunion"),
        "tiene_entrante_desk": bool(desk.get("ult_correo_entrante")),
        "reuniones_pasadas": reuniones_de(cid, eventos, reu.get("historial"), hoy, canceladas),
        "tonos": sorted([{"semana": s.get("semana"), "tono": s.get("tono")} for s in (obj or {}).get("semanas") or [] if s.get("tono")],
                        key=lambda t: t["semana"] or "", reverse=True),
    }
    qs = []
    for c in mios:
        if c.get("queja"):
            qs.append({"origen": "correo", "fecha": c.get("desde"), "texto": c.get("asunto"), "abierta": True, "url": c.get("url")})
    for i in incidencias:
        if i.get("cliente_id") == cid and i.get("queja") and i.get("estado") not in ("cerrada", "resuelta"):
            qs.append({"origen": "incidencia", "fecha": i.get("detectada"), "texto": i.get("titulo"), "abierta": True, "url": i.get("prueba")})
    rm = cart.get("rojo_manual") or {}
    if rm:
        qs.append({"origen": "rojo a mano", "fecha": None, "texto": rm.get("motivo"), "abierta": True})
    for s in (obj or {}).get("semanas") or []:
        if s.get("queja"):
            dias = _dias(s.get("semana"), hoy)
            qs.append({"origen": "semáforo del lunes", "fecha": s.get("semana"), "texto": s.get("nota"),
                       "abierta": dias is not None and dias < 7})     # marcada esta semana: abierta
    return {
        "cliente_id": cid, "nombre": doc.get("nombre"), "account": cart.get("account"), "account_id": account_id,
        "resultados": res, "contacto": con, "quejas": qs,
        "quejas_fuentes_ok": est_desk not in (None, "sin_conectar", "rota") or bool(sem),
        "semaforo_account": sem or None,
    }


def resumen_cartera(filas):
    """Por account: cuántos clientes en riesgo alto o crítico, con la escala de la D-41. La fila lleva persona_id (el
    servidor la deja a quien puede ver a esa persona) y cada cliente de «en_riesgo» lleva cliente_id (solo los que ve)."""
    bien, vigilar = UMBRALES["cartera"]
    por = {}
    for f in filas:
        if not f.get("account_id"):
            continue
        a = por.setdefault(f["account_id"], {"persona_id": f["account_id"], "account": f.get("account"), "clientes": 0,
                                             "por_nivel": {n: 0 for n in NIVELES}, "en_riesgo": []})
        a["clientes"] += 1
        a["por_nivel"][f["nivel"]] += 1
        if f["nivel"] in ("alto", "critico"):
            a["en_riesgo"].append({"cliente_id": f["cliente_id"], "cliente": f.get("cliente"), "nivel": f["nivel"]})
    for a in por.values():
        n = len(a["en_riesgo"])
        a["estado"] = "bien" if n <= bien else "vigilar" if n <= vigilar else "critico"
    return sorted(por.values(), key=lambda a: -len(a["en_riesgo"]))


def generar(hoy=None, escribir=True):
    hoy = _fecha(hoy) or date.today()
    objetivos = {c["cliente_id"]: c for c in (_j(DATA / "objetivos/objetivos.json", {}) or {}).get("clientes", [])}
    accounts = {c.get("cliente_id"): c.get("account") for c in (_j(DATA / "verdad/clientes.json", {}) or {}).get("comun", [])}
    agenda = _j(DATA / "agenda/agenda.json", {}) or {}
    eventos, canceladas = agenda.get("eventos", []) or [], agenda.get("canceladas", []) or []
    diags = {c.get("cliente_id"): c for c in (_j(DATA / "diagnosticos/diagnosticos.json", {}) or {}).get("clientes", []) or []}
    correos = (_j(DATA / "bandeja/bandeja.json", {}) or {}).get("correos", []) or []
    inc_doc = _j(DATA / "incidencias/incidencias.json", {}) or {}
    incidencias = [x for v in inc_doc.values() if isinstance(v, list) for x in v if isinstance(x, dict)] \
        if isinstance(inc_doc, dict) else []
    filas = []
    for p in sorted((DATA / "clientes").glob("*.json")):
        doc = _j(p)
        if not doc or doc.get("activo_libro") not in (None, "Activo"):
            continue
        filas.append(calcular(entrada_de(doc, objetivos.get(doc.get("id")), correos, incidencias, hoy, accounts.get(doc.get("id")), eventos, diags.get(doc.get("id")), canceladas), hoy))
    filas.sort(key=lambda f: (-ORDEN_NIVEL[f["nivel"]], -f["puntos"], f.get("cliente") or ""))
    out = {
        "formato": 1, "generado": datetime.now().strftime("%Y-%m-%d %H:%M"), "hoy": hoy.isoformat(),
        "umbrales": {**{k: v for k, v in UMBRALES.items() if k != "cartera"}, "cartera": list(UMBRALES["cartera"]),
                     "firmado": FIRMADO, "nota": "Firmados por Tomás el 4-oct-2026 (silencio 7/14, verde 90 %, queja 30 días); el resto, propuesta del mismo día"},
        "resumen": {n: sum(1 for f in filas if f["nivel"] == n) for n in NIVELES} |
                   {"clientes": len(filas), "discrepancias": sum(1 for f in filas if f["discrepancia"])},
        "carteras": resumen_cartera(filas),
        "clientes": filas,
    }
    if escribir:
        SALIDA.parent.mkdir(parents=True, exist_ok=True)
        tmp = SALIDA.with_suffix(".tmp.json")
        tmp.write_text(json.dumps(out, ensure_ascii=False, indent=1))
        tmp.replace(SALIDA)
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--cliente" in args:
        cid = args[args.index("--cliente") + 1]
        d = generar(escribir=False)
        print(json.dumps(next((f for f in d["clientes"] if f["cliente_id"] == cid), None), ensure_ascii=False, indent=1))
    else:
        d = generar()
        r = d["resumen"]
        print(f"riesgo_baja.json: {r['clientes']} clientes · crítico {r['critico']} · alto {r['alto']} · vigilar {r['vigilar']} "
              f"· bajo {r['bajo']} · {r['discrepancias']} con el semáforo del lunes en contra")
