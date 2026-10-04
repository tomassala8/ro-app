#!/usr/bin/env python3
"""
setters_srv.py · Setters (3-oct-2026, feedback de Tomás en ../58_FEEDBACK_TOMAS_03OCT.md). Se engancha a servir.py como
envios.py o sincronia.py (envuelve api_post). Sin este fichero, nada cambia salvo que «Agendar cita» no se puede guardar.

1. CADA SETTER SOLO SUS LEADS Y SUS CITAS, comprobado AQUÍ (no en el navegador): toda acción de la pantalla «setters»
   (resultado de una llamada, confirmar una cita, llamar, WhatsApp, agendar) tiene que ser sobre un lead o una cita que
   data/ventas_ro/setters.json da a ESA setter. Dirección y ventas de RO, que dirigen a los setters, sobre los de los dos.
   El informe de fin de día, solo a su nombre. Si no, 403 y fila en el rastro.
2. LOS LEADS DE RO NO SON CLIENTES DE LA AGENCIA: la regla «lo que sale fuera necesita un cliente que lleves» (servir.py,
   acciones_con_efecto_fuera) no encaja con un lead de la subcuenta de RO. Cuando el lead es de la setter (comprobado en 1),
   este fichero marca la acción como «lead de RO» y servir.py deja pasar WhatsApp / GoHighLevel sin cliente. El navegador
   no puede marcarla: cualquier «_lead_ro» que mande se borra antes.
3. «AGENDAR CITA» (tipo crear_cita_ghl, herramienta ghl): la vista previa la pone el SERVIDOR (calendario de 45 min de Tomás,
   contacto = el lead, inicio y fin en hora de Madrid, subcuenta de RO, enlace a la ficha). El hueco tiene que estar entre
   los libres del calendario (setters.json → huecos, leídos de GoHighLevel en solo lectura); a mano solo si no hay huecos
   leídos, y queda marcado «sin comprobar». Nunca dos citas pedidas a la misma hora. Hoy queda en la cola como «simulada»:
   NO se crea nada en GoHighLevel (el canal ghl de data/envios/interruptor.json está apagado y no hay despachador de citas).
4. «CLAUDE TE LO RELLENA» (POST /api/setters/propuesta_cita {lead, notas}): propone hueco, título y notas a partir de las
   notas de la llamada. Con IA (ia.py, control de gasto de ia_gasto.py, tarea «otra») o, sin ella, por reglas (día y hora
   que se mencionan en las notas). Siempre revisable: la setter lo ve en el formulario y decide. Nunca en «ver como».
   Al modelo no viajan teléfonos ni correos (ia.limpiar) ni el apellido del lead.
"""
import json
import re
import threading
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

AQUI = Path(__file__).resolve().parent
SETTERS_JSON = AQUI / "data" / "ventas_ro" / "setters.json"
PRIV = AQUI / "data" / "ventas_ro" / "_privado"
INTERRUPTOR_ENVIOS = AQUI / "data" / "envios" / "interruptor.json"
MAD = ZoneInfo("Europe/Madrid")
CAL45 = "ChisJEQCj8fXSnML13AQ"
DIRIGEN = {"direccion", "ventas_ro"}
LEAD_RO = "_lead_ro"
TIPO_CITA = "crear_cita_ghl"
TEXTO_PENDIENTE = "Guardada en la app · pendiente de GoHighLevel (simulación: no se ha creado nada)"

S = None
P = None
_CACHE = {"clave": None, "d": None}
_CANDADO = threading.Lock()


# ----------------------------------------------------------------------- datos
def datos():
    """setters.json leído una vez por versión (fecha + tamaño)."""
    try:
        st = SETTERS_JSON.stat()
    except OSError:
        return {}
    clave = (st.st_mtime_ns, st.st_size)
    with _CANDADO:
        if _CACHE["clave"] != clave:
            try:
                _CACHE["d"] = json.loads(SETTERS_JSON.read_text(encoding="utf-8"))
            except Exception:
                _CACHE["d"] = {}
            _CACHE["clave"] = clave
        return _CACHE["d"] or {}


def dueno(objeto):
    """Setter («ana» / «javier») de un lead o una cita por su id de contacto (o id de cita). None si no es de ninguno."""
    o = str(objeto or "")
    if not o:
        return None
    d = datos()
    for lista in ("leads", "citas", "pasadas"):
        for x in d.get(lista) or []:
            if o in (x.get("id"), x.get("cita_id")) and x.get("setter") in ("ana", "javier"):
                return x["setter"]
    return None


def mi_setter(persona):
    pid = str((persona or {}).get("id") or "")
    if "setters" not in P.puestos_de(persona):
        return None
    return pid.replace("setter_", "") if pid.startswith("setter_") else None


def puede(persona, real, objeto):
    """¿Puede esta persona (y la real, en «ver como») actuar sobre este lead? Sus leads, o los de los dos si dirige."""
    s = dueno(objeto)
    if not s:
        return False
    for p in (persona, real):
        if not p:
            continue
        if P.puestos_de(p) & DIRIGEN:
            continue
        if mi_setter(p) != s:
            return False
    return True


def lead_de(objeto):
    o = str(objeto or "")
    d = datos()
    for lista in ("leads", "citas", "pasadas"):
        for x in d.get(lista) or []:
            if o == x.get("id"):
                return x
    return None


def privado(setter, lead_id):
    try:
        return (json.loads((PRIV / f"setter_{setter}.json").read_text(encoding="utf-8")).get("leads") or {}).get(lead_id) or {}
    except Exception:
        return {}


def huecos():
    return (datos().get("huecos") or {}).get("dias") or {}


def ghl_encendido():
    try:
        i = json.loads(INTERRUPTOR_ENVIOS.read_text(encoding="utf-8"))
        return bool(i.get("envios_reales") and (i.get("canales") or {}).get("ghl") and i.get("activado_por") == "tomas")
    except Exception:
        return False


# ----------------------------------------------------------------------- agendar
RX_INICIO = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")


def limpio(t, n):
    return re.sub(r"[\x00-\x1f<>]", " ", str(t or "")).strip()[:n]


def validar_cita(persona, b):
    """Devuelve (vista_previa del servidor, None) o (None, (código, error))."""
    vp = b.get("vista_previa") if isinstance(b.get("vista_previa"), dict) else {}
    if str(b.get("herramienta") or "") != "ghl":
        return None, (400, "Agendar una cita va a GoHighLevel (herramienta ghl).")
    inicio = str(vp.get("inicio") or "").strip()
    if not RX_INICIO.match(inicio):
        return None, (400, "Falta el día y la hora de la cita (AAAA-MM-DD HH:MM, hora de Madrid).")
    try:
        t = datetime.strptime(inicio, "%Y-%m-%d %H:%M").replace(tzinfo=MAD)
    except ValueError:
        return None, (400, "Ese día o esa hora no existen.")
    ahora = datetime.now(MAD)
    if t < ahora + timedelta(minutes=30):
        return None, (400, "La cita tiene que ser como pronto dentro de 30 minutos.")
    if t > ahora + timedelta(days=60):
        return None, (400, "Más de 60 días vista: mejor que reserve él desde la web.")
    libres = huecos()
    dia, hora = inicio[:10], inicio[11:]
    comprobado = False
    if libres:
        if hora not in (libres.get(dia) or []):
            return None, (409, "Esa hora ya no está libre en el calendario de Tomás. Elige uno de los huecos de la lista.")
        comprobado = True
    with S.conectar() as con:
        ya = con.execute("SELECT count(*) FROM acciones WHERE tipo=? AND estado='simulada' AND vista_previa LIKE ?",
                         (TIPO_CITA, f'%"inicio": "{inicio}"%')).fetchone()[0]
    if ya:
        return None, (409, "Ese hueco ya está pedido para otro lead. Elige otro.")
    lead = lead_de(b.get("objeto")) or {}
    # «Reagendar» una cita que ya existe: solo la cita de ESTE lead (la lista de citas del servidor), nunca otra.
    reagenda = str(vp.get("reagenda") or "")
    if reagenda and not any(c.get("cita_id") == reagenda and c.get("id") == str(b.get("objeto")) for c in datos().get("citas") or []):
        return None, (403, "Esa cita no es de este lead.")
    d = datos()
    loc = d.get("ubicacion_ghl") or ""
    fin = (t + timedelta(minutes=45)).strftime("%Y-%m-%d %H:%M")
    return {
        "que": "Mover la cita en GoHighLevel" if reagenda else "Crear cita en GoHighLevel",
        "reagenda_cita_id": reagenda or None,
        "estado": "simulada",
        "calendario": "Reunión de 45 min", "calendario_id": CAL45, "con": "Tomás",
        "subcuenta": loc, "contacto_id": str(b.get("objeto")),
        "inicio": inicio, "fin": fin, "zona": "Europe/Madrid",
        "titulo": limpio(vp.get("titulo"), 140) or "Reunión de 45 min con Tomás",
        "notas": limpio(vp.get("notas"), 1500),
        "hueco_comprobado": comprobado,
        "aviso": None if comprobado else "Hora puesta a mano: sin huecos leídos de GoHighLevel, compruébala en el calendario antes de crearla.",
        "ayuda_ia": vp.get("ayuda_ia") if vp.get("ayuda_ia") in ("ia", "reglas") else None,
        "pedida_por": persona["id"],
        "interruptor": "GoHighLevel apagado: no se crea nada hasta que Tomás lo active" if not ghl_encendido() else "GoHighLevel encendido, pero aún no hay despachador de citas: se crea a mano",
        "enlace_ghl": lead.get("ghl"),
    }, None


# ----------------------------------------------------------------------- propuesta («Claude te lo rellena»)
DIAS = {"lunes": 0, "martes": 1, "miércoles": 2, "jueves": 3, "viernes": 4}
SISTEMA = ("Eres el ayudante de una setter de Ranking Online (agencia de marketing para asesorías y despachos en España). "
           "Con las notas de su llamada y los huecos LIBRES del calendario de 45 minutos de Tomás, elige el hueco que mejor "
           "encaja con lo que dijo el lead (día, mañana o tarde, hora) y redacta un título corto y unas notas para Tomás "
           "(3-5 líneas, español de España, sin inventar nada que no esté en las notas). Si las notas no dicen nada del día, "
           "el primer hueco libre. Solo puedes elegir horas de la lista. Responde solo con el JSON pedido.")
ESQUEMA = {"type": "object", "additionalProperties": False, "required": ["dia", "hora", "titulo", "notas", "porque"],
           "properties": {"dia": {"type": "string"}, "hora": {"type": "string"}, "titulo": {"type": "string"},
                          "notas": {"type": "string"}, "porque": {"type": "string"}}}


def _sin_acentos(t):
    return t.lower().translate(str.maketrans("áéíóúüñ", "aeiouun"))


def por_reglas(notas, libres, ahora=None):
    """Elige hueco por lo que dicen las notas: «el martes», «mañana», «pasado mañana», «por la tarde», «a las 10»."""
    ahora = ahora or datetime.now(MAD)
    n = _sin_acentos(notas or "")
    hoy = ahora.date()
    dias_ok = None
    porque = []
    if "pasado manana" in n:
        dias_ok = {(hoy + timedelta(days=2)).isoformat()}; porque.append("pasado mañana")
    elif re.search(r"\bmanana\b", n.replace("por la manana", "").replace("de la manana", "")):
        dias_ok = {(hoy + timedelta(days=1)).isoformat()}; porque.append("mañana")
    for nombre, wd in DIAS.items():
        if re.search(rf"\b{_sin_acentos(nombre)}\b", n):
            delta = (wd - hoy.weekday()) % 7 or 7
            dias_ok = (dias_ok or set()) | {(hoy + timedelta(days=delta)).isoformat()}
            porque.append(f"el {nombre}")
            break
    franja = None
    if "por la tarde" in n or re.search(r"\btarde\b", n):
        franja = (15, 21); porque.append("por la tarde")
    elif "por la manana" in n or "temprano" in n:
        franja = (8, 14); porque.append("por la mañana")
    m = re.search(r"\ba las (\d{1,2})(?:[:.h](\d{2}))?", n) or re.search(r"\b(\d{1,2})[:h](\d{2})\b", n)
    hora_pedida = None
    if m:
        hh = int(m.group(1)); mm = int(m.group(2) or 0)
        if franja == (15, 21) and hh < 12:
            hh += 12
        if 7 <= hh <= 21:
            hora_pedida = hh * 60 + mm; porque.append(f"a las {hh}:{mm:02d}")
    cands = [(d, h) for d in sorted(libres) for h in libres[d]]
    if dias_ok:
        c2 = [x for x in cands if x[0] in dias_ok]
        cands = c2 or cands
        if not c2:
            porque.append("(ese día no hay hueco: el primero libre)")
    if franja:
        c2 = [x for x in cands if franja[0] <= int(x[1][:2]) < franja[1]]
        if c2:
            cands = c2
        else:
            porque.append("(no hay hueco en esa franja: el más cercano)")
    if hora_pedida is not None and cands:
        dia0 = cands[0][0]
        mismos = [x for x in cands if x[0] == dia0]
        cands = sorted(mismos, key=lambda x: abs(int(x[1][:2]) * 60 + int(x[1][3:]) - hora_pedida)) + [x for x in cands if x[0] != dia0]
    if not cands:
        return None, None, "No hay huecos libres leídos: pon día y hora a mano."
    d, h = cands[0]
    return d, h, ("Lo pidió " + ", ".join(porque)) if porque else "Las notas no dicen día: el primer hueco libre."


def propuesta(real, persona, b):
    lead_id = str(b.get("lead") or "")[:40]
    notas = str(b.get("notas") or "")[:2000]
    if not re.fullmatch(r"[\w\-]+", lead_id):
        return 400, {"error": "Falta el lead."}
    if real["id"] != persona["id"]:
        return 403, {"error": "En «ver como» no se propone nada."}
    if not puede(persona, real, lead_id):
        S.registrar_agrupado(real["id"], "setters", "denegado", lead_id, {"motivo": "propuesta de cita de un lead ajeno"})
        return 403, {"error": "Ese lead no es tuyo."}
    setter = dueno(lead_id)
    pv = privado(setter, lead_id)
    nombre = (pv.get("nombre") or "").split(" ")[0].strip().title()
    despacho = (pv.get("despacho") or "").strip()
    libres = huecos()
    d, h, porque = por_reglas(notas, libres)
    titulo = "Reunión de 45 min con Tomás" + (f" · {nombre}" if nombre else "") + (f" · {despacho}" if despacho else "")
    texto = (f"Notas de la llamada de la setter: {notas.strip()}" if notas.strip() else "Agendada por la setter tras la llamada.")
    salida = {"dia": d, "hora": h, "titulo": titulo, "notas": texto, "porque": porque, "origen": "reglas", "modelo": None}
    IA = S.__dict__.get("IA")
    aviso = None
    if IA is not None and libres:
        try:
            if IA.estado().get("conectada"):
                IA.G.fijar_peticion(real, persona, lead_id)
                try:
                    ctx = IA.limpiar({"hoy": datetime.now(MAD).strftime("%Y-%m-%d (%A)"), "lead": {"nombre": nombre, "despacho": despacho},
                                      "notas_de_la_llamada": notas, "huecos_libres_madrid": libres})
                    r = IA.llamar(SISTEMA, ctx, ESQUEMA, effort="low", tarea="otra")
                    o, modelo = (r if isinstance(r, tuple) else (r, None))
                    if isinstance(o, dict) and o.get("hora") in (libres.get(o.get("dia")) or []):
                        salida = {"dia": o["dia"], "hora": o["hora"], "titulo": limpio(o.get("titulo"), 140) or titulo,
                                  "notas": limpio(o.get("notas"), 1500) or texto, "porque": limpio(o.get("porque"), 300),
                                  "origen": "ia", "modelo": modelo}
                    else:
                        aviso = "La IA propuso una hora que no está libre: se queda la propuesta por reglas."
                finally:
                    IA.G.soltar_peticion()
        except Exception as e:  # sin clave, tope de gasto o error: reglas, con el motivo en llano
            aviso = f"Sin IA ahora ({str(e)[:120]}): propuesta por reglas."
    salida["aviso"] = aviso
    S.registrar(real["id"], "setters", "propuesta_cita", lead_id, {"origen": salida["origen"], "dia": salida["dia"], "hora": salida["hora"]})
    return 200, salida


# ----------------------------------------------------------------------- enganche
def guardia(real, persona, b):
    """None si la acción de la pantalla de setters puede seguir; (código, error) si no. Marca _lead_ro si procede."""
    b.pop(LEAD_RO, None)
    if str(b.get("modulo") or "") != "setters":
        return None
    tipo = str(b.get("tipo") or "")
    objeto = str(b.get("objeto") or "")
    if tipo == "informe_fin_de_dia":
        ms = mi_setter(real)
        if ms and objeto not in (ms, real["id"]):
            return 403, "El informe de fin de día va a tu nombre."
        return None
    if not puede(persona, real, objeto):
        S.registrar_agrupado(real["id"], "setters", "denegado", objeto[:60], {"motivo": "lead o cita de otra setter (o que no existe)", "tipo": tipo})
        return 403, "Ese lead no es tuyo: cada setter solo trabaja sus leads y sus citas."
    if tipo == TIPO_CITA:
        vp, err = validar_cita(persona, b)
        if err:
            return err
        b["vista_previa"] = vp
        b["texto"] = f"{vp['que']} · {vp['inicio'][8:10]}/{vp['inicio'][5:7]} a las {vp['inicio'][11:]} (Madrid) · 45 min con Tomás"
    if str(b.get("herramienta") or "") in ("ghl", "whatsapp", "zadarma"):
        b[LEAD_RO] = True              # lead de la subcuenta de RO, de esta setter: no es un cliente de la agencia
    return None


def enganchar(Manejador, servir):
    global S, P
    S, P = servir, servir.P
    post_orig = Manejador.api_post

    def api_post(self, ruta, real, persona_, b):
        if ruta == "/api/setters/propuesta_cita":
            if not S.ve_alguno(persona_, ["setters"]):
                return self.responder(403, {"error": "Esta pantalla no es de tu puesto."})
            c, o = propuesta(real, persona_, b or {})
            return self.responder(c, o)
        if ruta == "/api/acciones" and isinstance(b, dict):
            g = guardia(real, persona_, b)
            if g:
                return self.responder(g[0], {"error": g[1]})
            if b.get("tipo") == TIPO_CITA:
                orig = self.responder

                def responder(codigo, obj, *a, **k):
                    if codigo == 200 and isinstance(obj, dict):
                        obj = {**obj, "pendiente": TEXTO_PENDIENTE, "ghl_encendido": ghl_encendido()}
                    return orig(codigo, obj, *a, **k)
                self.responder = responder
                try:
                    return post_orig(self, ruta, real, persona_, b)
                finally:
                    self.responder = orig
        return post_orig(self, ruta, real, persona_, b)

    Manejador.api_post = api_post
