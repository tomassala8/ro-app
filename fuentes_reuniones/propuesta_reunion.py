#!/usr/bin/env python3
"""
fuentes_reuniones/propuesta_reunion.py · «Proponer fecha» con correo ya redactado (3-oct-2026). Se engancha a servir.py como
fuentes_gbp/servidor_gbp.py (envuelve _api_get y api_post). Sin este fichero, nada cambia.

Tomás (3-oct): «al pulsar "proponer fecha" no sale ningún correo base». Ahora sale SIEMPRE un correo de propuesta en la voz
de RO, con la firma de quien lo manda, 2-3 huecos reales, el motivo según el tipo de reunión y el enlace de agenda si existe.
Por reglas (cerebro_respuestas/cerebro.py → redactar_propuesta_reunion y calidad_propuesta): no necesita clave de IA y nunca
deja huecos sin rellenar.

  POST /api/reuniones/propuesta {cliente_id, tipo?, otros?: n}     → borrador {asunto, cuerpo, huecos, calidad, firma, objeto…}
       · tipo: seguimiento_mensual (por defecto) · revision_informe · arranque (por defecto si es alta nueva) ·
         revision_trimestral · campana
       · otros: 0 = los primeros huecos libres; 1, 2… = los siguientes (botón «Otros huecos»)
  POST /api/reuniones/propuesta/calidad {cliente_id, asunto, cuerpo} → nota de calidad del texto retocado (nunca guarda nada)

ENVIAR no pasa por aquí: la pantalla deja la acción {herramienta: desk, tipo: correo} en la cola y envios.py hace el resto
(simulado hoy, con su verificación; rechaza en el servidor cualquier hueco sin rellenar).

Huecos: de la agenda de quien firma (data/agenda/agenda.json: CRM, Calendar, GHL, Bookings y Zoom, en hora de Madrid) con 15
minutos de margen; si la app no tiene su agenda, huecos razonables en su horario. Siempre dentro de SU jornada (9:00-18:00 en
su zona) y de la del cliente en España (9:30-13:30 y 15:30-18:30, hora peninsular), en días laborables (sin festivos
nacionales) y desde el siguiente día laborable. Se escriben en hora peninsular; la pantalla enseña también la suya.
Enlace de agenda: fuentes_reuniones/enlaces_agenda.json (persona → enlace). Firma: la pone Desk si la persona la tiene ahí
(data/bandeja/bandeja.json → firmas); si no, va en el texto.
Rastro: reunion_propuesta_borrador (solo servidor).
"""
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
sys.path.insert(0, str(APP / "fuentes_ia" / "cerebro_respuestas"))
import cerebro as CB  # noqa: E402

MADRID = ZoneInfo("Europe/Madrid")
MODULOS = ("reuniones", "ficha", "mi-dia")
ENLACES = AQUI / "enlaces_agenda.json"
FESTIVOS = {"2026-10-12", "2026-11-02", "2026-12-07", "2026-12-08", "2026-12-25", "2027-01-01", "2027-01-06"}   # nacionales (y traslados generales)
VENTANAS_CLIENTE = ((9 * 60 + 30, 13 * 60 + 30), (15 * 60 + 30, 18 * 60 + 30))                                   # minutos, hora peninsular
PREFERIDAS = ["10:00", "11:30", "16:00", "12:30", "17:00", "09:30", "16:30", "11:00", "15:30", "17:30", "12:00", "10:30"]
RX_CID = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")


def _leer(p, defecto=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return defecto


def _mes(d):
    return CB.MESES[d.month - 1]


def laborables(desde, n):
    d, out = desde, []
    while len(out) < n:
        if d.weekday() < 5 and str(d) not in FESTIVOS:
            out.append(d)
        d += timedelta(days=1)
    return out


def ocupado(eventos, ini, fin):
    for e in eventos:
        if e["todo"] and e["ini"].date() <= ini.date() <= e["fin"].date():
            return True
        if e["ini"] - timedelta(minutes=15) < fin and ini < e["fin"] + timedelta(minutes=15):
            return True
    return False


def buscar_huecos(persona_id, zona, minutos=30, otros=0, ahora=None):
    """3 huecos en días distintos. Devuelve (huecos [{inicio, texto, suya}], de_agenda: bool)."""
    ahora = ahora or datetime.now(MADRID)
    z = ZoneInfo(zona or "Europe/Madrid")
    ag = _leer(APP / "data" / "agenda" / "agenda.json", {}) or {}
    evs = []
    for e in ag.get("eventos") or []:
        if e.get("persona_id") != persona_id:
            continue
        try:
            i = datetime.strptime(e["inicio"][:16], "%Y-%m-%d %H:%M").replace(tzinfo=MADRID)
            f = datetime.strptime((e.get("fin") or e["inicio"])[:16], "%Y-%m-%d %H:%M").replace(tzinfo=MADRID)
        except Exception:
            continue
        evs.append({"ini": i, "fin": max(f, i + timedelta(minutes=30)), "todo": bool(e.get("todo_el_dia"))})
    de_agenda = bool(evs)
    jor = (ag.get("_meta") or {}).get("jornada") or {"inicio": "09:00", "fin": "18:00"}
    j0 = int(jor["inicio"][:2]) * 60 + int(jor["inicio"][3:5])
    j1 = int(jor["fin"][:2]) * 60 + int(jor["fin"][3:5])
    dias = laborables(ahora.date() + timedelta(days=1), 12 + 3 * otros)
    out = []
    for k, d in enumerate(dias):
        if len(out) >= 3 + 3 * otros:
            break
        validas = []
        for hm in PREFERIDAS:
            ini = datetime(d.year, d.month, d.day, int(hm[:2]), int(hm[3:]), tzinfo=MADRID)
            fin = ini + timedelta(minutes=minutos)
            m0, m1 = ini.hour * 60 + ini.minute, fin.hour * 60 + fin.minute
            if not any(a <= m0 and m1 <= b for a, b in VENTANAS_CLIENTE):
                continue
            li, lf = ini.astimezone(z), fin.astimezone(z)                 # su jornada, en su zona
            if li.date() != lf.date() or not (j0 <= li.hour * 60 + li.minute and lf.hour * 60 + lf.minute <= j1):
                continue
            validas.append((ini, fin, li))
        if not validas:
            continue
        r = k % len(validas)                                            # que no salgan los tres a la misma hora
        for ini, fin, li in validas[r:] + validas[:r]:
            if ocupado(evs, ini, fin):
                continue
            out.append({"inicio": ini.strftime("%Y-%m-%d %H:%M"), "texto": CB.texto_hueco(ini.strftime("%Y-%m-%d %H:%M")),
                        "suya": None if z.key == "Europe/Madrid" else f"{li:%H:%M} en tu hora"})
            break
    return out[3 * otros:3 * otros + 3], de_agenda


def contacto_y_ticket(cid):
    """Nombre de pila del contacto (último correo que nos escribió) y el ticket más reciente del cliente en Desk."""
    h = _leer(APP / "data" / "bandeja" / "hilos.json", {}) or {}
    mejor, nombre = None, None
    for x in h.get("hilos") or []:
        if x.get("cliente_id") != cid:
            continue
        ms = x.get("mensajes") or []
        ult = max((m.get("fecha") or "" for m in ms), default="")
        if not mejor or ult > mejor[0]:
            mejor = (ult, x.get("numero"))
        for m in ms:
            if m.get("direccion") == "entrante" and m.get("de") and (not nombre or (m.get("fecha") or "") > nombre[0]):
                nombre = (m.get("fecha") or "", m["de"])
    pila = None
    if nombre:
        t = re.sub(r"[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ' -]", " ", nombre[1]).split()
        if t and 2 <= len(t[0]) <= 20 and not re.search(r"(?i)info|admin|gestor|asesor|despacho|consult|noreply|contab|soporte|support|equipo|marketing|oficina|recepci|laboral|fiscal|hola|contacto|direcci|bufete|abogad|clientes|web", t[0]):
            pila = t[0].capitalize()
    return pila, (mejor or (None, None))[1]


def firma_de(S, persona):
    p = S.E.persona(persona["id"]) if hasattr(S.E, "persona") else persona
    p = p or persona
    puestos = {x["id"]: x["nombre"] for x in S.P.REGLAS.get("puestos") or []}
    puesto = p.get("rol") or puestos.get(p.get("puesto_principal")) or ""
    if persona["id"] == "tomas":
        puesto = ""
    firmas = ((_leer(APP / "data" / "bandeja" / "bandeja.json", {}) or {}).get("firmas")) or {}
    return {"nombre": p.get("nombre") or persona["id"], "puesto": puesto, "en_texto": not firmas.get(persona["id"]),
            "texto": "La firma la pone Desk al enviar" if firmas.get(persona["id"]) else "Tu firma no está en Desk: va escrita al final del correo"}


def tipo_por_defecto(cid):
    c = _leer(APP / "data" / "clientes" / f"{cid}.json", {}) or {}
    cart = ((c.get("fuentes") or {}).get("cartera") or {}).get("datos") or {}
    return "arranque" if cart.get("nuevo") else "seguimiento_mensual", bool(cart.get("nuevo"))


def borrador(S, persona, cid, tipo=None, otros=0):
    ahora = datetime.now(MADRID)
    cli = next((c for c in S.E.crudo.get("clientes", []) if c.get("id") == cid), {}) or {}
    defecto, nuevo = tipo_por_defecto(cid)
    tipo = tipo if tipo in CB.MOTIVOS_REUNION else defecto
    mot = CB.MOTIVOS_REUNION[tipo]
    p = (S.E.persona(persona["id"]) if hasattr(S.E, "persona") else None) or persona
    huecos, de_agenda = buscar_huecos(persona["id"], p.get("zona"), mot["min"], max(0, min(int(otros or 0), 4)), ahora)
    enlace = ((_leer(ENLACES, {}) or {}).get("enlaces") or {}).get(persona["id"]) or None
    contacto, ticket = contacto_y_ticket(cid)
    firma = firma_de(S, persona)
    mes_ant = (ahora.replace(day=1) - timedelta(days=1))
    d = CB.redactar_propuesta_reunion({"tipo": tipo, "cliente": cli.get("nombre") or cid, "contacto": contacto, "huecos": [x["inicio"] for x in huecos],
                                       "mes": _mes(ahora), "mes_ant": _mes(mes_ant), "enlace": enlace, "firma": firma, "cliente_nuevo": nuevo})
    otros_cli = [c.get("nombre") for c in S.E.crudo.get("clientes", []) if c.get("id") != cid and c.get("nombre")]
    cal = CB.calidad_propuesta(d["cuerpo"], d["asunto"], {"enlace": enlace, "firma": firma}, otros_cli)
    zona = p.get("zona") or "Europe/Madrid"
    return {**d, "cliente_id": cid, "cliente": cli.get("nombre") or cid, "contacto": contacto, "huecos": huecos, "calidad": cal,
            "firma": firma, "enlace": enlace, "objeto": ticket or f"reunion:{cid}:{ahora:%Y-%m}", "ticket": ticket,
            "tipos": [{"id": k, "nombre": v["nombre"], "minutos": v["min"]} for k, v in CB.MOTIVOS_REUNION.items()],
            "fuente_huecos": ("Huecos libres de tu agenda (CRM, Calendar, GoHighLevel, Bookings y Zoom), con 15 min de margen" if de_agenda else
                              "La app no tiene tu agenda: huecos razonables en tu horario. Mira tu calendario antes de enviar"),
            "zona": zona, "otra_zona": zona != "Europe/Madrid", "origen": "reglas (sin IA)",
            "para": f"Contacto del ticket {ticket} de {cli.get('nombre') or cid} en Desk" if ticket else f"Contacto principal de {cli.get('nombre') or cid} (lo pone el servidor al enviar)"}


def enganchar(Manejador, servir):
    S = servir
    get_orig, post_orig = Manejador._api_get, Manejador.api_post

    def puede(persona, cid):
        if not S.ve_alguno(persona, list(MODULOS)):
            return False
        cp = S.P.contexto(persona, S.E.crudo)
        return S.P.ver(persona, {"tipo": "cliente_detalle", "cliente_id": cid}, cp)["ok"]

    def api_post(self, ruta, real, persona, b):
        if ruta not in ("/api/reuniones/propuesta", "/api/reuniones/propuesta/calidad"):
            return post_orig(self, ruta, real, persona, b)
        b = b or {}
        cid = str(b.get("cliente_id") or "")
        if not RX_CID.match(cid):
            return self.responder(400, {"error": "Falta el cliente."})
        if not puede(persona, cid):
            return self.responder(403, {"error": "No puedes escribir a este cliente desde tu puesto."})
        como = persona["id"] if real["id"] != persona["id"] else None
        if ruta == "/api/reuniones/propuesta":
            try:
                r = borrador(S, persona, cid, str(b.get("tipo") or "") or None, b.get("otros") or 0)
            except Exception as e:  # nunca un 500 mudo: el motivo en llano
                return self.responder(500, {"error": f"No he podido preparar el correo ({type(e).__name__})."})
            S.registrar_agrupado(real["id"], "reuniones", "reunion_propuesta_borrador", cid,
                                 {"tipo": r["motivo"], "huecos": len(r["huecos"]), "nota": r["calidad"]["nota"]}, como=como)
            return self.responder(200, r)
        texto = str(b.get("cuerpo") or "")[:8000]
        asunto = str(b.get("asunto") or "")[:300]
        enlace = ((_leer(ENLACES, {}) or {}).get("enlaces") or {}).get(persona["id"]) or None
        otros_cli = [c.get("nombre") for c in S.E.crudo.get("clientes", []) if c.get("id") != cid and c.get("nombre")]
        return self.responder(200, CB.calidad_propuesta(texto, asunto, {"enlace": enlace, "firma": firma_de(S, persona)}, otros_cli))

    Manejador.api_post = api_post
