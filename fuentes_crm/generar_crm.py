#!/usr/bin/env python3
"""fuentes_crm/generar_crm.py · M7 «Salud del CRM» (E5, parte CRM). SOLO LECTURA.

Junta, por subcuenta de GoHighLevel (las 66 de la agencia):
  · 20_FASE2_CAPTACION/captacion.json  → embudo a 90 días, estancados 72 h y leads de Meta (no se rehace)
  · GHL en vivo (~/RO_HERRAMIENTAS/ghl_agencia/app.py, app privada «Panel RO lectura subcuentas»):
      - leads de los últimos 30 días (contactos con origen formulario, Facebook, calendario…; los manuales aparte)
      - por cada lead, su conversación: primer intento de una persona (llamada o mensaje a mano),
        primer mensaje automático, intentos en 72 h, WhatsApp/SMS fallidos
      - citas de los calendarios (90 días atrás y 30 adelante): agendadas, celebradas, no presentadas,
        sin estado, canceladas, asistencia
      - flujos: la app NO tiene workflows.readonly → se comprueba (401) y se deja el enlace a la pestaña
  · data/asignaciones.json (silla crm y account), data/personas.json, data/nuevos/nuevos.json (altas)

Escribe data/crm/crm.json (sin datos personales de leads) y data/crm/_privado/leads.json
(nombre, teléfono y correo de cada lead: solo con /api/ver_dato, y queda en el rastro, D-88).

Uso:  python3 generar_crm.py                 # en vivo (gasta ~1 renovación de la llave y ~700 lecturas)
      python3 generar_crm.py --sin-vivo      # solo captacion.json (sin velocidad ni citas a 90 días)
La llave de la app rota en cada renovación: app.acceso() la guarda sola en el llavero (no se imprime).
"""
import json, os, sys, time, hashlib, statistics, urllib.request, urllib.parse, urllib.error, datetime as dt
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
DATA = APP / "data"
RAIZ = APP.parent
SALIDA = DATA / "crm"
sys.path.insert(1, str(Path(__file__).resolve().parents[1]))  # C5: rutas y secretos en config.py
import config  # noqa: E402
sys.path.insert(0, str(config.HERRAMIENTAS / "ghl_agencia"))

import zoneinfo, re
MAD = zoneinfo.ZoneInfo("Europe/Madrid")          # todo en hora de Madrid (regla 4 de la ronda)
HOY = dt.datetime.now(MAD)
AHORA_MS = int(HOY.timestamp() * 1000)


def inicio_dia(n):
    """ms del comienzo (00:00 de Madrid) del día de hace n días. Ventanas de días naturales cerrados, sin hoy."""
    d = HOY.date() - dt.timedelta(days=n)
    return int(dt.datetime.combine(d, dt.time(0), MAD).timestamp() * 1000)


HOY0_MS = inicio_dia(0)

# «Lead que llega» (una sola definición, igual que Captación): contacto nuevo cuyo origen es un formulario o un
# anuncio. Fuera: los creados a mano o importados, los de prueba o demostración y los de otros negocios.
MEDIOS_LEAD = {"form", "facebook", "instagram", "survey", "calendar", "whatsapp", "paid", "cpc", "ads", "tiktok", "google", "linkedin"}
MEDIOS_NO = {"manual", "csv_import", "import", "other", "api", "sin origen"}
RX_PRUEBA = re.compile(r"(no es un lead real|ejemplo demo|\bprueba\b|\btest\b|dummy)", re.I)
RX_NO_LEAD = re.compile(r"(candidatura|curso|cliente ro|reuni[oó]n|zoho bookings|creado por claude)", re.I)
RX_LANDING = re.compile(r"(landing|formulario|form\b|agendar|web|bofu|home|captura|contacto|cont[aá]ctanos|lead magnet|gu[ií]a)", re.I)
RX_CORREO_PRUEBA = re.compile(r"(^test|^prueba|@example\.|@test\.|@mail-tester\.|@mailinator\.|\+test@)", re.I)
EXCLUSIONES = json.loads((AQUI / "exclusiones.json").read_text()) if (AQUI / "exclusiones.json").exists() else {}


def clasificar(lead, sid):
    """(es_lead, motivo). motivo = por qué no cuenta: otro_negocio, prueba, manual, importado, no_lead, sin_origen."""
    medio = (lead.get("medio") or "").strip()
    fuente = lead.get("fuente") or ""
    texto = f"{medio} {fuente}"
    tags = " ".join(lead.get("tags") or [])
    exc = EXCLUSIONES.get(sid, {})
    if any(x.lower() in texto.lower() or x.lower() in tags.lower() for x in exc.get("origen_contiene", [])):
        return False, "otro_negocio"
    if RX_PRUEBA.search(texto) or RX_PRUEBA.search(tags) or RX_CORREO_PRUEBA.search(((lead.get("privado") or {}).get("correo") or "").strip()):
        return False, "prueba"
    if lead.get("manual"):
        return False, "manual"
    if medio.lower() in ("csv_import", "import"):
        return False, "importado"
    if RX_NO_LEAD.search(texto):
        return False, "no_lead"
    if medio.lower() in MEDIOS_LEAD or RX_LANDING.search(medio):
        return True, None
    return False, "sin_origen"
VENTANA_LEADS = 30
GHL_WEB = "https://app.gohighlevel.com/v2/location"

COMUNICACION = {"TYPE_CALL", "TYPE_SMS", "TYPE_CUSTOM_SMS", "TYPE_WHATSAPP", "TYPE_EMAIL", "TYPE_FACEBOOK",
                "TYPE_INSTAGRAM", "TYPE_GMB", "TYPE_LIVE_CHAT", "TYPE_CUSTOM_EMAIL", "TYPE_CUSTOM_PROVIDER_SMS",
                "TYPE_CUSTOM_PROVIDER_EMAIL", "TYPE_CUSTOM_CALL", "TYPE_IVR_CALL"}
AUTOMATICO = {"workflow", "campaign", "bulk_actions", "bulk_action", "automation", "trigger"}
PRUEBA = ("dummy", "eliminar", "prueba", "snapshot", "snapshoot")
INTERNA = ("ranking online",)


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def leer(p, defecto=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return defecto


def iso_ms(s):
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return int(s)
    try:
        return int(dt.datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp() * 1000)
    except Exception:
        return None


def ms_iso(ms):
    return dt.datetime.fromtimestamp(ms / 1000, MAD).strftime("%Y-%m-%d %H:%M") if ms else None


def pct(a, b):
    return round(a * 100 / b, 1) if b else None


def ref_de(*partes):
    return hashlib.sha1("·".join(map(str, partes)).encode()).hexdigest()[:12]


# ------------------------------------------------------------------ GHL (lectura)
class GHL:
    def __init__(self):
        import app  # ~/RO_HERRAMIENTAS/ghl_agencia/app.py
        self.app = app
        cache = os.environ.get("CRM_TOKEN_CACHE")
        c = leer(cache) if cache else None
        if c and time.time() - c.get("t", 0) < 18 * 3600:
            self.tk, self.co = c["tk"], c["co"]
        else:
            self.tk, est = app.acceso()          # rota la llave y la guarda en el llavero
            self.co = est["companyId"]
        self.llamadas = 0

    def subcuentas(self):
        return self.app.subcuentas(self.tk, self.co)

    def req(self, loc, metodo, ruta, cuerpo=None, **q):
        lt = self.app.token_sub(self.tk, self.co, loc)
        url = self.app.API + ruta + ("?" + urllib.parse.urlencode(q) if q else "")
        for intento in range(5):
            r = urllib.request.Request(url, data=json.dumps(cuerpo).encode() if cuerpo is not None else None, method=metodo,
                                       headers={"Authorization": "Bearer " + lt, "Version": "2021-07-28", "Accept": "application/json",
                                                "Content-Type": "application/json", "User-Agent": "panel-ro/1.0"})
            try:
                self.llamadas += 1
                return json.load(urllib.request.urlopen(r, timeout=60))
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(2 + 2 * intento)
                    continue
                return {"_error": e.code, "_msg": e.read().decode()[:200]}
            except Exception as e:  # red
                time.sleep(2 + 2 * intento)
                err = str(e)
        return {"_error": "red", "_msg": err if 'err' in dir() else "sin respuesta"}


def leer_subcuenta(g, loc):
    """Leads 30 días + su conversación, citas 90/30 días y prueba de flujos. Nada se escribe."""
    out = {"leads": [], "citas": [], "calendarios": [], "flujos": None, "errores": []}
    desde = dt.datetime.fromtimestamp(inicio_dia(VENTANA_LEADS + 1) / 1000, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tot = g.req(loc, "POST", "/contacts/search", {"locationId": loc, "pageLimit": 1})
    out["contactos_total"] = tot.get("total") if "_error" not in tot else None
    contactos, pagina = [], 1
    while pagina <= 3:
        r = g.req(loc, "POST", "/contacts/search", {"locationId": loc, "pageLimit": 100, "page": pagina,
                  "filters": [{"field": "dateAdded", "operator": "range", "value": {"gte": desde}}],
                  "sort": [{"field": "dateAdded", "direction": "desc"}]})
        if "_error" in r:
            out["errores"].append(f"contactos {r['_error']}")
            break
        cs = r.get("contacts", [])
        contactos += cs
        if len(cs) < 100:
            break
        pagina += 1

    # citas: calendarios y eventos (90 días atrás, 30 adelante)
    cals = g.req(loc, "GET", "/calendars/", locationId=loc)
    if "_error" in cals:
        out["errores"].append(f"calendarios {cals['_error']}")
    t0 = AHORA_MS - 90 * 864e5
    t1 = AHORA_MS + 30 * 864e5
    for cal in cals.get("calendars", []) or []:
        out["calendarios"].append({"id": cal.get("id"), "nombre": cal.get("name"), "activo": cal.get("isActive", True)})
        e = g.req(loc, "GET", "/calendars/events", locationId=loc, calendarId=cal["id"], startTime=int(t0), endTime=int(t1))
        if "_error" in e:
            out["errores"].append(f"eventos {e['_error']}")
            continue
        for ev in e.get("events", []) or []:
            if ev.get("deleted"):
                continue
            out["citas"].append({"id": ev.get("id"), "calendario": cal.get("name"), "inicio": iso_ms(ev.get("startTime")),
                                 "estado": (ev.get("appointmentStatus") or ev.get("appoinmentStatus") or "sin_estado").lower(),
                                 "contacto": ev.get("contactId"), "creada": iso_ms(ev.get("dateAdded"))})
    con_cita = {c["contacto"] for c in out["citas"] if c["contacto"]}

    # leads: solo los que no se crearon a mano en el CRM
    for c in contactos[:150]:
        medio = ((c.get("attributionSource") or {}).get("medium") or "").lower() or None
        manual = medio == "manual" or ((c.get("attributionSource") or {}).get("sessionSource") == "CRM UI")
        creado = iso_ms(c.get("dateAdded"))
        lead = {"contacto": c.get("id"), "creado": creado, "medio": medio or (c.get("source") or "sin origen"),
                "fuente": c.get("source"), "manual": manual, "cita": c.get("id") in con_cita, "tags": c.get("tags") or [],
                "privado": {"nombre": " ".join(x for x in [c.get("firstName"), c.get("lastName")] if x) or c.get("contactName"),
                            "telefono": c.get("phone"), "correo": c.get("email")}}
        lead["es_lead"], lead["descartado"] = clasificar(lead, loc)
        if lead["es_lead"]:
            cv = g.req(loc, "GET", "/conversations/search", locationId=loc, contactId=c.get("id"), limit=5)
            msgs = []
            for conv in (cv.get("conversations") or [])[:2]:
                m = g.req(loc, "GET", f"/conversations/{conv['id']}/messages", limit=100)
                msgs += (m.get("messages") or {}).get("messages", []) or []
            com = [x for x in msgs if x.get("messageType") in COMUNICACION]
            sal = sorted([x for x in com if x.get("direction") == "outbound" or (x.get("messageType") == "TYPE_CALL" and x.get("direction") != "inbound")],
                         key=lambda x: iso_ms(x.get("dateAdded")) or 0)
            humanos = [x for x in sal if (x.get("source") or "").lower() not in AUTOMATICO]
            autos = [x for x in sal if (x.get("source") or "").lower() in AUTOMATICO]
            t_h = iso_ms(humanos[0].get("dateAdded")) if humanos else None
            t_a = iso_ms(autos[0].get("dateAdded")) if autos else None
            lim72 = (creado or 0) + 72 * 3600e3
            wa = [x for x in sal if x.get("messageType") == "TYPE_WHATSAPP"]
            sms = [x for x in sal if x.get("messageType") in ("TYPE_SMS", "TYPE_CUSTOM_SMS", "TYPE_CUSTOM_PROVIDER_SMS")]
            lead.update({
                "humano_min": round((t_h - creado) / 60000) if t_h and creado else None,
                "auto_min": round((t_a - creado) / 60000) if t_a and creado else None,
                "intentos": len(humanos),
                "intentos_72h": sum(1 for x in humanos if (iso_ms(x.get("dateAdded")) or 0) <= lim72),
                "llamadas": sum(1 for x in humanos if "CALL" in (x.get("messageType") or "")),
                "respondio": any(x.get("direction") == "inbound" for x in com),
                "wa_env": len(wa), "wa_fallo": sum(1 for x in wa if (x.get("status") or "").lower() in ("failed", "undelivered")),
                "sms_env": len(sms), "sms_fallo": sum(1 for x in sms if (x.get("status") or "").lower() in ("failed", "undelivered")),
                "mail_env": sum(1 for x in sal if x.get("messageType") == "TYPE_EMAIL"),
                "mail_fallo": sum(1 for x in sal if x.get("messageType") == "TYPE_EMAIL" and (x.get("status") or "").lower() in ("failed", "bounced", "undelivered")),
            })
        out["leads"].append(lead)

    etapas = {}
    pl = g.req(loc, "GET", "/opportunities/pipelines", locationId=loc)
    for p_ in pl.get("pipelines", []) or []:
        for st in p_.get("stages", []) or []:
            etapas[st.get("id")] = {"etapa": st.get("name"), "embudo": p_.get("name")}
    opps, pagina = [], 1
    while pagina <= 3:
        r = g.req(loc, "GET", "/opportunities/search", location_id=loc, status="open", limit=100, page=pagina)
        if "_error" in r:
            out["errores"].append(f"oportunidades {r['_error']}")
            break
        lo = r.get("opportunities", []) or []
        opps += lo
        if len(lo) < 100:
            break
        pagina += 1
    out["oportunidades"] = [{"id": o.get("id"), "contacto": o.get("contactId"), "creada": iso_ms(o.get("createdAt") or o.get("dateAdded")),
                             "ultimo_cambio": iso_ms(o.get("lastStageChangeAt") or o.get("lastStatusChangeAt") or o.get("updatedAt")),
                             **(etapas.get(o.get("pipelineStageId")) or {"etapa": None, "embudo": None})} for o in opps]
    f = g.req(loc, "GET", "/workflows/", locationId=loc)
    out["flujos"] = {"leido": "_error" not in f, "error": f.get("_error"), "n": len(f.get("workflows", []) or []) if "_error" not in f else None,
                     "lista": [{"nombre": w.get("name"), "estado": w.get("status")} for w in (f.get("workflows") or [])] if "_error" not in f else []}
    return out


# ------------------------------------------------------------------ resumen por subcuenta
def resumen_citas(citas, dias=30):
    # días naturales cerrados en hora de Madrid (sin hoy), igual que Meta y Captación
    pasadas = [c for c in citas if c["inicio"] and inicio_dia(dias) <= c["inicio"] < HOY0_MS]
    sh = sum(1 for c in pasadas if c["estado"] == "showed")
    ns = sum(1 for c in pasadas if c["estado"] == "noshow")
    se = [c for c in pasadas if c["estado"] in ("confirmed", "new", "booked", "sin_estado")]
    ca = sum(1 for c in pasadas if c["estado"] in ("cancelled", "invalid"))
    fut = [c for c in citas if c["inicio"] and c["inicio"] > AHORA_MS and c["estado"] not in ("cancelled", "invalid")]
    ult = max((c["inicio"] for c in citas if c["inicio"] and c["inicio"] <= AHORA_MS and c["estado"] not in ("cancelled", "invalid")), default=None)
    return {"agendadas": len(pasadas) - ca, "celebradas": sh, "no_presentadas": ns, "sin_estado": len(se), "canceladas": ca,
            "asistencia_pct": pct(sh, sh + ns), "asistencia_si_sin_estado_no_vino": pct(sh, sh + ns + len(se)),
            "sin_estado_max_h": round(max((AHORA_MS - c["inicio"]) / 3600e3 for c in se)) if se else 0,
            "futuras": len(fut), "ultima": ms_iso(ult)[:10] if ult else None,
            "dias_sin_cita": round((AHORA_MS - ult) / 864e5) if ult else None}


def main():
    vivo = "--sin-vivo" not in sys.argv and "--desde-crudo" not in sys.argv
    cap = leer(RAIZ / "20_FASE2_CAPTACION" / "captacion.json", {})
    VER = {c["cliente_id"]: c for c in (leer(DATA / "verdad" / "clientes.json", {}) or {}).get("clientes", [])}   # verdad única (ronda 5)
    emp = (leer(DATA / "emparejamientos.json", {}) or {}).get("clientes", {})
    personas = {p["id"]: p for p in leer(DATA / "personas.json", [])}
    asig = leer(DATA / "asignaciones.json", [])
    nuevos = leer(DATA / "nuevos" / "nuevos.json", {}) or {}
    idx = (leer(DATA / "indice_clientes.json", {}) or {}).get("clientes", [])
    nombres_app = {c["id"]: c["nombre"] for c in idx}
    activo_libro = {c["id"]: c.get("activo_libro") for c in idx}

    # subcuenta → cliente de la app
    sub_cli = {}
    for cid, v in emp.items():
        for k in ("ghl", "captacion_ghl"):
            sid = (v.get(k) or {}).get("id")
            if sid:
                sub_cli.setdefault(sid, cid)
    capid_app = {}
    for c in idx:
        f = leer(DATA / "clientes" / f"{c['id']}.json", {}) or {}
        cap_id = (f.get("ids") or {}).get("captacion")
        if cap_id:
            capid_app[cap_id] = c["id"]
    cap_por_sub = {}
    for c in cap.get("clientes", []):
        sid = (c.get("ghl_subcuenta") or {}).get("id")
        if sid:
            cap_por_sub[sid] = c
            if capid_app.get(c["id"]):
                sub_cli.setdefault(sid, capid_app[c["id"]])
    for sid, g in (cap.get("ghl_subcuentas_sin_cliente_meta") or {}).items():
        cap_por_sub.setdefault(sid, {"ghl": g, "nombre": g.get("nombre")})

    silla = {}
    for a in asig:
        if a.get("hasta"):
            continue
        silla.setdefault((a["cliente_id"], a["silla"]), []).append(a)
    def persona_de(cid, s):
        fs = silla.get((cid, s)) or []
        fs = sorted(fs, key=lambda a: (not a.get("principal", True), a.get("suplencia", False)))
        if not fs:
            return None
        p = personas.get(fs[0]["persona_id"], {})
        return {"id": fs[0]["persona_id"], "nombre": p.get("alias") or p.get("nombre") or fs[0]["persona_id"], "confianza": fs[0].get("confianza")}

    g = GHL() if vivo else None
    subs = g.subcuentas() if g else [{"id": k, "name": (v.get("nombre") or (v.get("ghl") or {}).get("nombre"))} for k, v in cap_por_sub.items()]
    log(f"subcuentas: {len(subs)}")
    vivo_por = {}
    if g:
        def uno(s):
            try:
                return s["id"], leer_subcuenta(g, s["id"])
            except Exception as e:
                return s["id"], {"leads": [], "citas": [], "calendarios": [], "flujos": None, "errores": [f"excepción {type(e).__name__}"]}
        with ThreadPoolExecutor(5) as ex:
            for i, (sid, r) in enumerate(ex.map(uno, subs)):
                vivo_por[sid] = r
                if i % 10 == 0:
                    log(f"  {i + 1}/{len(subs)} · llamadas {g.llamadas}")

    crudo = AQUI / "_privado" / "ghl_vivo.json"   # ronda 6 (M6): correos y teléfonos de leads, solo en _privado/
    if g:
        crudo.parent.mkdir(exist_ok=True)
        crudo.write_text(json.dumps({"hora": HOY.strftime("%Y-%m-%d %H:%M"), "llamadas": g.llamadas, "subs": subs, "vivo": vivo_por}, ensure_ascii=False))
        hora_vivo, llamadas = HOY.strftime("%Y-%m-%d %H:%M"), g.llamadas
    elif "--desde-crudo" in sys.argv and crudo.exists():
        c = leer(crudo); subs, vivo_por = c["subs"], c["vivo"]
        hora_vivo, llamadas = c.get("hora"), c.get("llamadas", 0)
    else:
        hora_vivo, llamadas = None, 0
    filas, leads_pub, citas_pub, paradas_pub, privado = [], [], [], [], {"leads": {}}
    flujos_scope = None
    for s in subs:
        sid, nombre_sub = s["id"], (s.get("name") or "").strip()
        nl = nombre_sub.lower()
        cid = sub_cli.get(sid)
        tipo = "prueba" if any(x in nl for x in PRUEBA) else "interna" if any(nl.startswith(x) for x in INTERNA) else ("cliente" if cid else "sin_cliente")
        cp = cap_por_sub.get(sid) or {}
        emb = ((cp.get("ghl") or {}).get("embudo")) or {}
        meta = cp.get("meta") if isinstance(cp.get("meta"), dict) else {}
        leads_meta_7d = (meta.get("leads") or {}).get("7d")
        leads_meta_30d = (meta.get("leads") or {}).get("mes_anterior")
        v = vivo_por.get(sid) or {}
        exc = EXCLUSIONES.get(sid, {})
        if v and exc.get("calendario_contiene"):
            fuera = [x.lower() for x in exc["calendario_contiene"]]
            v = {**v, "citas": [c for c in v.get("citas", []) if not any(x in (c.get("calendario") or "").lower() for x in fuera)],
                 "calendarios": [c for c in v.get("calendarios", []) if not any(x in (c.get("nombre") or "").lower() for x in fuera)],
                 "calendarios_ajenos": [c.get("nombre") for c in v.get("calendarios", []) if any(x in (c.get("nombre") or "").lower() for x in fuera)]}
        for x in v.get("leads", []):
            if "es_lead" not in x:
                x["es_lead"], x["descartado"] = clasificar(x, sid)
        L = v.get("leads", [])
        ini30 = inicio_dia(VENTANA_LEADS)
        en30 = [x for x in L if x["creado"] and ini30 <= x["creado"] < HOY0_MS]
        auto = [x for x in en30 if x.get("es_lead")]
        descartados = {}
        for x in en30:
            if not x.get("es_lead"):
                descartados[x.get("descartado") or "sin_origen"] = descartados.get(x.get("descartado") or "sin_origen", 0) + 1
        total_contactos = v.get("contactos_total")
        sin_uso = bool(v) and total_contactos is not None and total_contactos < 5
        hace24 = AHORA_MS - 24 * 3600e3
        hace72 = AHORA_MS - 72 * 3600e3
        sin_tocar = [x for x in auto if x["creado"] and x["creado"] <= hace24 and not x.get("intentos") and not x["cita"]]
        juzg = [x for x in auto if x["creado"] and x["creado"] <= hace24]
        en1h = [x for x in juzg if x.get("humano_min") is not None and x["humano_min"] <= 60]
        juzg72 = [x for x in auto if x["creado"] and x["creado"] <= hace72]
        cuatro = [x for x in juzg72 if (x.get("intentos_72h") or 0) >= 4]
        auto_ok = [x for x in auto if x.get("auto_min") is not None and x["auto_min"] <= 5]
        tiempos = [x["humano_min"] for x in auto if x.get("humano_min") is not None]
        wa_env = sum(x.get("wa_env", 0) for x in auto)
        wa_fallo = sum(x.get("wa_fallo", 0) for x in auto)
        sms_env = sum(x.get("sms_env", 0) for x in auto)
        sms_fallo = sum(x.get("sms_fallo", 0) for x in auto)
        mail_env = sum(x.get("mail_env", 0) for x in auto)
        mail_fallo = sum(x.get("mail_fallo", 0) for x in auto)
        leads_ghl_7d = (None if sin_uso else sum(1 for x in auto if x["creado"] >= inicio_dia(7))) if v else None   # 7 días naturales cerrados
        opps = v.get("oportunidades") or []
        opps30 = [o for o in opps if o.get("creada") and o["creada"] >= ini30]
        paradas = [o for o in opps30 if (o.get("ultimo_cambio") or o.get("creada") or AHORA_MS) <= AHORA_MS - 72 * 3600e3]
        citas = v.get("citas") if v else None
        c30 = resumen_citas(citas, 30) if citas is not None else None
        c90 = resumen_citas(citas, 90) if citas is not None else None
        c14 = resumen_citas(citas, 14) if citas is not None else None
        if flujos_scope is None and v.get("flujos"):
            flujos_scope = v["flujos"]
        vc = VER.get(cid) or {}
        meta_activa = bool(vc.get("campana_activa")) if vc else bool(cp.get("meta_activa"))
        encendida = tipo in ("cliente", "sin_cliente") and not sin_uso and (meta_activa or len(auto) >= 3)

        # motivos (umbrales firmados del catálogo: especialista_ghl.*, D-45)
        mot = []
        def M(nivel, clave, texto):
            mot.append({"nivel": nivel, "clave": clave, "texto": texto})
        if sin_uso:
            M("info", "sin_uso", f"La subcuenta tiene {total_contactos} contacto{'s' if total_contactos != 1 else ''} en toda su historia: el cliente no usa GoHighLevel. Confirmar si el servicio de CRM está contratado")
        # misma regla que la verdad única: ≥ 10 leads de Meta en 7 días; grave si llega menos de la mitad, leve si menos del 80 %
        elif leads_meta_7d and leads_meta_7d >= 10 and leads_ghl_7d is not None and leads_ghl_7d / leads_meta_7d < 0.8:
            M("rojo" if leads_ghl_7d / leads_meta_7d < 0.5 else "ambar", "integracion",
              f"Meta dio {int(leads_meta_7d)} leads en 7 días y a GoHighLevel llegaron {leads_ghl_7d}: revisar la conexión del formulario")
        if sin_tocar:
            M("rojo", "sin_tocar", f"{len(sin_tocar)} lead{'s' if len(sin_tocar) != 1 else ''} de más de 24 h sin ningún intento apuntado en GHL")
        if c14:
            if c14["sin_estado"] > 5 or (c14["sin_estado"] and c14["sin_estado_max_h"] > 48):
                M("rojo", "sin_estado", f"{c14['sin_estado']} cita{'s' if c14['sin_estado'] != 1 else ''} de los últimos 14 días sin marcar si vino (la más antigua, hace {c14['sin_estado_max_h'] // 24} días)")
            elif c14["sin_estado"]:
                M("ambar", "sin_estado", f"{c14['sin_estado']} citas pasadas sin marcar (menos de 48 h)")
        if c30:
            a = c30["asistencia_pct"]
            if a is not None and (c30["celebradas"] + c30["no_presentadas"]) >= 3:
                if a < 60:
                    M("rojo", "asistencia", f"Asistencia del {a:.0f} % (umbral 75 %)")
                elif a < 75:
                    M("ambar", "asistencia", f"Asistencia del {a:.0f} % (umbral 75 %)")
        if encendida and c90 and c90["agendadas"] == 0 and c90["futuras"] == 0 and len(auto) >= 5:
            agenda_fuera = any(re.search(r"(agendar|demo|cita|reuni|booking)", f"{x.get('medio')} {x.get('fuente')}", re.I) for x in auto)
            if agenda_fuera:
                M("info", "citas_fuera", f"Los leads piden cita con un formulario y el calendario de GoHighLevel está vacío: las citas se reservan fuera. No se pueden medir aquí")
            else:
                M("rojo", "sin_citas", f"{len(auto)} leads en 30 días y ninguna cita en 90 días: el despacho no los convierte en reunión")
        if len(opps30) >= 3 and len(paradas) * 2 >= len(opps30):
            M("ambar", "estancados", f"{len(paradas)} de {len(opps30)} oportunidades del último mes llevan más de 72 h sin moverse")
        if wa_env >= 5 and wa_fallo * 100 / wa_env > 10:
            M("rojo", "whatsapp", f"WhatsApp: {wa_fallo} de {wa_env} mensajes fallidos ({wa_fallo * 100 / wa_env:.0f} %)")
        elif wa_env >= 5 and wa_fallo * 100 / wa_env >= 2:
            M("ambar", "whatsapp", f"WhatsApp: {wa_fallo} de {wa_env} mensajes fallidos")
        if encendida and len(auto) >= 3 and not auto_ok and not wa_env and not sms_env and not mail_env:
            M("ambar", "sin_automatico", "Entran leads y no sale ningún mensaje automático: revisar el flujo de bienvenida")
        if juzg and len(juzg) >= 3:
            p1 = len(en1h) * 100 / len(juzg)
            if p1 < 40:
                M("ambar", "velocidad", f"Solo {len(en1h)} de {len(juzg)} leads con un primer intento en menos de 1 h (garantía: 70 %)")
        if tipo in ("prueba", "interna"):
            estado = "gris"
        elif not encendida and not mot:
            estado = "gris"
        elif sin_uso:
            estado = "gris"
        elif any(m["nivel"] == "rojo" for m in mot):
            estado = "rojo"
        elif any(m["nivel"] == "ambar" for m in mot):
            estado = "ambar"
        else:
            estado = "verde"

        esp = persona_de(cid, "crm") if cid else None
        acc = {"id": vc.get("account")} if vc.get("account") else None   # account = verdad única
        fila = {
            "sub_id": sid, "nombre": nombre_app if (nombre_app := nombres_app.get(cid)) else nombre_sub, "nombre_sub": nombre_sub,
            "tipo": tipo, "activo_libro": activo_libro.get(cid), "especialista_id": esp["id"] if esp else None,
            "especialista_confianza": esp["confianza"] if esp else None, "account_id": acc["id"] if acc else None,
            "contactos_total": total_contactos, "sin_uso": sin_uso, "descartados_30d": descartados,
            "calendarios_ajenos": v.get("calendarios_ajenos") or [],
            "encendida": encendida, "meta_activa": meta_activa,
            "leads_meta_7d": leads_meta_7d, "leads_meta_sep": leads_meta_30d, "leads_ghl_7d": leads_ghl_7d,
            "leads_30d": len(auto) if v else emb.get("cohorte_30d"), "leads_manuales_30d": sum(1 for x in L if x["manual"]),
            "sin_tocar_24h": len(sin_tocar) if v else None,
            "velocidad": {"juzgables": len(juzg), "en_1h": len(en1h), "pct_1h": pct(len(en1h), len(juzg)),
                          "juzgables_72h": len(juzg72), "cuatro_en_72h": len(cuatro), "pct_4en72": pct(len(cuatro), len(juzg72)),
                          "mediana_min": round(statistics.median(tiempos)) if tiempos else None,
                          "con_intento": sum(1 for x in auto if x.get("intentos")), "intentos_medios": round(sum(x.get("intentos", 0) for x in auto) / len(auto), 1) if auto else None,
                          "auto_5min": len(auto_ok), "respondieron": sum(1 for x in auto if x.get("respondio"))} if v else None,
            "citas_14d": c14, "citas_30d": c30, "citas_90d": c90, "calendarios": len(v.get("calendarios", [])) if v else (cp.get("ghl") or {}).get("calendarios"),
            "embudo": {"cohorte_30d": len(opps30) if v else emb.get("cohorte_30d"), "estancados_72h": len(paradas) if v else emb.get("estancados_72h"),
                       "pct_estancado": pct(len(paradas), len(opps30)) if v else emb.get("pct_estancado"),
                       "horas_max_parado": emb.get("horas_max_parado"), "funnel": emb.get("funnel")} if emb else None,
            "whatsapp": {"enviados": wa_env, "fallidos": wa_fallo, "pct_fallo": pct(wa_fallo, wa_env), "numero": "no medible"},
            "sms": {"enviados": sms_env, "fallidos": sms_fallo},
            "correo": {"enviados": mail_env, "fallidos": mail_fallo, "pct_fallo": pct(mail_fallo, mail_env)},
            "flujos": {"medible": False, "motivo": "Falta un permiso de GoHighLevel para leer los flujos (responde 401). Los errores de flujo («Needs Review») no salen por la API ni con ese permiso."},
            "estado": estado, "motivos": mot, "errores_lectura": v.get("errores", []) if v else [],
            "enlaces": {"ghl": f"{GHL_WEB}/{sid}/dashboard", "flujos": f"{GHL_WEB}/{sid}/automation/workflows",
                        "calendarios": f"{GHL_WEB}/{sid}/calendars/view", "oportunidades": f"{GHL_WEB}/{sid}/opportunities/list",
                        "conversaciones": f"{GHL_WEB}/{sid}/conversations/conversations", "whatsapp": f"{GHL_WEB}/{sid}/settings/whatsapp",
                        "contactos": f"{GHL_WEB}/{sid}/contacts/smart_list/All"},
        }
        if cid:
            fila["cliente_id"] = cid
        filas.append(fila)

        for x in (sin_tocar if tipo in ("cliente", "sin_cliente") else []):
            ref = ref_de(sid, x["contacto"])
            privado["leads"][ref] = {"datos": x["privado"], "cliente_id": cid}
            fl = {"ref": ref, "sub_id": sid, "subcuenta": fila["nombre"], "creado": ms_iso(x["creado"]),
                  "horas": round((AHORA_MS - x["creado"]) / 3600e3), "medio": x["medio"], "automatico": x.get("auto_min") is not None,
                  "respondio": x.get("respondio"), "enlace": f"{GHL_WEB}/{sid}/contacts/detail/{x['contacto']}",
                  "especialista_id": fila["especialista_id"]}
            if cid:
                fl["cliente_id"] = cid
            leads_pub.append(fl)
        for c in ((citas or []) if tipo in ("cliente", "sin_cliente") else []):
            if c["inicio"] and inicio_dia(14) <= c["inicio"] < HOY0_MS and c["estado"] in ("confirmed", "new", "booked", "sin_estado"):
                ref = ref_de(sid, c["id"])
                if c.get("contacto"):
                    lead = next((x for x in L if x["contacto"] == c["contacto"]), None)
                    if lead:
                        privado["leads"][ref] = {"datos": lead["privado"], "cliente_id": cid}
                fc = {"ref": ref, "sub_id": sid, "subcuenta": fila["nombre"], "inicio": ms_iso(c["inicio"]), "calendario": c["calendario"],
                      "horas": round((AHORA_MS - c["inicio"]) / 3600e3), "estado_ghl": c["estado"], "datos": ref in privado["leads"],
                      "enlace": f"{GHL_WEB}/{sid}/calendars/view", "especialista_id": fila["especialista_id"]}
                if c.get("contacto"):
                    fc["enlace_contacto"] = f"{GHL_WEB}/{sid}/contacts/detail/{c['contacto']}"
                if cid:
                    fc["cliente_id"] = cid
                citas_pub.append(fc)
        for o in (paradas if tipo in ("cliente", "sin_cliente") else []):
            fo = {"ref": ref_de(sid, o["id"]), "sub_id": sid, "subcuenta": fila["nombre"], "etapa": o.get("etapa"), "embudo_nombre": o.get("embudo"),
                  "creada": ms_iso(o.get("creada")), "horas": round((AHORA_MS - (o.get("ultimo_cambio") or o.get("creada"))) / 3600e3),
                  "enlace": f"{GHL_WEB}/{sid}/contacts/detail/{o['contacto']}" if o.get("contacto") else f"{GHL_WEB}/{sid}/opportunities/list",
                  "especialista_id": fila["especialista_id"]}
            if cid:
                fo["cliente_id"] = cid
            paradas_pub.append(fo)

    # especialistas (carga y salud de su cartera de subcuentas). Clave «id», no «persona_id» (no son horas).
    esp = {}
    for a in asig:
        if a.get("silla") == "crm" and not a.get("hasta"):
            esp.setdefault(a["persona_id"], set()).add(a["cliente_id"])
    especialistas = []
    for pid, clis in sorted(esp.items()):
        mias = [f for f in filas if f.get("cliente_id") in clis]
        p = personas.get(pid, {})
        especialistas.append({"id": pid, "clientes": len(clis), "subcuentas": len(mias),
                              "encendidas": sum(1 for f in mias if f["encendida"]),
                              "verde": sum(1 for f in mias if f["estado"] == "verde"), "ambar": sum(1 for f in mias if f["estado"] == "ambar"),
                              "rojo": sum(1 for f in mias if f["estado"] == "rojo"), "gris": sum(1 for f in mias if f["estado"] == "gris"),
                              "sin_tocar": sum(f["sin_tocar_24h"] or 0 for f in mias),
                              "sin_estado": sum((f["citas_14d"] or {}).get("sin_estado", 0) for f in mias), "tope": 16,
                              "sin_subcuenta": sorted(nombres_app.get(c, c) for c in clis if c not in {f.get("cliente_id") for f in filas})})
    sin_esp = [f["nombre"] for f in filas if f["tipo"] == "cliente" and not f["especialista_id"] and f["encendida"]]

    # montajes de altas (enlaza con «Clientes nuevos»): casillas de CRM por alta
    sub_de_cli = {f["cliente_id"]: f for f in filas if f.get("cliente_id")}
    montajes = []
    for a in nuevos.get("altas", []):
        f = sub_de_cli.get(a["cliente_id"])
        cas = [
            {"id": "subcuenta", "texto": "Subcuenta creada desde el snapshot", "estado": "verde" if f else "rojo",
             "detalle": f"«{f['nombre_sub']}»" if f else "No hay subcuenta de GHL emparejada con este cliente", "medible": "hoy"},
            {"id": "calendario", "texto": "Calendario de citas", "estado": ("verde" if f["calendarios"] else "rojo") if f else "gris",
             "detalle": f"{f['calendarios']} calendario(s)" if f else "—", "medible": "hoy"},
            {"id": "pipeline", "texto": "Embudo de oportunidades", "estado": ("verde" if (f.get("embudo") or {}).get("funnel") else "ambar") if f else "gris",
             "detalle": "Con etapas" if f and (f.get("embudo") or {}).get("funnel") else "Sin oportunidades en 90 días", "medible": "hoy"},
            {"id": "lead_entra", "texto": "Entra el primer lead de Meta", "estado": ("verde" if (f["leads_30d"] or 0) > 0 else "gris") if f else "gris",
             "detalle": f"{f['leads_30d']} leads en 30 días" if f else "—", "medible": "hoy"},
            {"id": "flujos", "texto": "Flujos validados", "estado": "gris", "detalle": "Todavía no se mide: falta un permiso de GoHighLevel", "medible": "no"},
            {"id": "whatsapp", "texto": "WhatsApp conectado", "estado": "gris", "detalle": "No medible por API: se mira en Ajustes › WhatsApp de la subcuenta", "medible": "no"},
            {"id": "prueba", "texto": "Prueba del circuito en menos de 1 h", "estado": "gris", "detalle": "Falta el contacto de prueba automático (permiso de GoHighLevel)", "medible": "no"},
            {"id": "formacion", "texto": "Formación al despacho dada", "estado": "gris", "detalle": "Se marca a mano (casilla de la app)", "medible": "no"},
        ]
        montajes.append({"cliente_id": a["cliente_id"], "nombre": a["nombre"], "dia": a.get("dia"), "alta": a.get("alta"),
                         "crm": (a.get("crm") or {}).get("nombre"), "sub_id": f["sub_id"] if f else None,
                         "enlace": f["enlaces"]["ghl"] if f else None, "casillas": cas,
                         "listas": sum(1 for c in cas if c["estado"] == "verde"), "medibles": sum(1 for c in cas if c["medible"] == "hoy")})

    cli = [f for f in filas if f["tipo"] in ("cliente", "sin_cliente")]
    enc = [f for f in cli if f["encendida"]]
    tot_c30 = {k: sum((f["citas_30d"] or {}).get(k, 0) for f in cli) for k in ("agendadas", "celebradas", "no_presentadas", "sin_estado", "canceladas", "futuras")}
    tot_c14 = {k: sum((f["citas_14d"] or {}).get(k, 0) for f in cli) for k in ("agendadas", "celebradas", "no_presentadas", "sin_estado")}
    juzg_tot = sum((f["velocidad"] or {}).get("juzgables", 0) for f in cli)
    en1h_tot = sum((f["velocidad"] or {}).get("en_1h", 0) for f in cli)
    despachos_vel = [f for f in cli if (f["velocidad"] or {}).get("juzgables", 0) >= 3]
    cumplen = [f for f in despachos_vel if (f["velocidad"]["pct_1h"] or 0) >= 70 and (f["velocidad"]["pct_4en72"] or 0) >= 70]
    resumen = {
        "subcuentas": len(filas), "de_clientes": len(cli), "pruebas_e_internas": len(filas) - len(cli), "encendidas": len(enc),
        "verde": sum(1 for f in enc if f["estado"] == "verde"), "ambar": sum(1 for f in enc if f["estado"] == "ambar"),
        "rojo": sum(1 for f in enc if f["estado"] == "rojo"),
        "pct_verde": pct(sum(1 for f in enc if f["estado"] == "verde"), len(enc)),
        "leads_30d": sum(f["leads_30d"] or 0 for f in cli), "sin_tocar_24h": sum(f["sin_tocar_24h"] or 0 for f in cli),
        "velocidad_pct_1h": pct(en1h_tot, juzg_tot), "velocidad_juzgables": juzg_tot,
        "despachos_cumplen_garantia": len(cumplen), "despachos_juzgables_garantia": len(despachos_vel),
        "citas_30d": tot_c30, "citas_14d": tot_c14, "asistencia_pct": pct(tot_c30["celebradas"], tot_c30["celebradas"] + tot_c30["no_presentadas"]),
        "estancados_72h": sum((f["embudo"] or {}).get("estancados_72h") or 0 for f in cli),
        "whatsapp": {"enviados": sum(f["whatsapp"]["enviados"] for f in cli), "fallidos": sum(f["whatsapp"]["fallidos"] for f in cli)},
        "integracion_rota": [f["nombre"] for f in cli if any(m["clave"] == "integracion" for m in f["motivos"])],
        "encendidas_sin_especialista": sin_esp,
    }

    hallazgos = []
    def H(cid, titulo, texto, estado, prueba=None):
        f = next((x for x in filas if x.get("cliente_id") == cid), None)
        h = {"titulo": titulo, "texto": texto, "estado": estado, "prueba": prueba or (f["enlaces"]["ghl"] if f else None)}
        if cid:
            h["cliente_id"] = cid
        hallazgos.append(h)
    for f in cli:
        for m in f["motivos"]:
            if m["clave"] == "integracion":
                H(f.get("cliente_id"), f"{f['nombre']}: los leads de Meta no llegan a GoHighLevel", m["texto"] + ". Revisar la conexión del formulario de Meta con la subcuenta (Agus).", m["nivel"], f["enlaces"]["contactos"])
            if m["clave"] == "sin_uso" and f["meta_activa"]:
                H(f.get("cliente_id"), f"{f['nombre']}: subcuenta sin usar", m["texto"] + ". Los leads de Meta van a otro sitio (no es una conexión rota).", "ambar", f["enlaces"]["contactos"])
            if m["clave"] == "sin_estado" and (f["citas_14d"] or {}).get("sin_estado", 0) >= 5:
                H(f.get("cliente_id"), f"{f['nombre']}: {f['citas_14d']['sin_estado']} citas sin estado en 14 días", m["texto"] + ". Sin marcar, la asistencia no se puede medir.", "rojo", f["enlaces"]["calendarios"])
            if m["clave"] == "sin_citas":
                H(f.get("cliente_id"), f"{f['nombre']}: sin citas en 90 días", m["texto"] + ".", "rojo", f["enlaces"]["calendarios"])
    if tot_c30["celebradas"] == 0 and tot_c30["agendadas"]:
        hallazgos.append({"titulo": "Ningún despacho marca «se presentó»", "estado": "ambar",
                          "texto": f"En 30 días hay {tot_c30['agendadas']} citas pasadas y 0 marcadas como celebradas: la asistencia (el número que manda del especialista) no se puede calcular en ninguna subcuenta."})

    fuentes = {
        "ghl": {"fuente": "GoHighLevel · 66 subcuentas (app privada, lectura)", "hora": hora_vivo,
                "estado": "bien" if hora_vivo else "dato_viejo", "llamadas": llamadas,
                "permisos": "contacts, opportunities, calendars, calendars/events, conversations, conversations/message, users, locations (solo lectura)"},
        "captacion": {"fuente": "captacion.json (embudo 90 días y Meta)", "hora": cap.get("generado"), "estado": "bien"},
        "asignaciones": {"fuente": "Asignaciones fase 0 (silla CRM)", "hora": None, "estado": "bien", "nota": "Borrador de fase 0; las confirma Mili"},
        "nuevos": {"fuente": "Clientes nuevos (altas)", "hora": nuevos.get("generado"), "estado": "bien" if nuevos else "sin_conectar"},
        "flujos": {"fuente": "Flujos de GHL", "estado": "sin_conectar", "nota": (flujos_scope or {}).get("error") and f"GoHighLevel responde {flujos_scope['error']}: falta el permiso de lectura de flujos"},
    }
    salida = {"formato": 1, "modulo": "salud-crm", "generado": HOY.strftime("%Y-%m-%d %H:%M"), "hoy": HOY.strftime("%Y-%m-%d"),
              "ventanas": {"leads": f"30 días naturales cerrados en hora de Madrid ({dt.datetime.fromtimestamp(inicio_dia(30)/1000, MAD).strftime('%d-%m')} a {dt.datetime.fromtimestamp(inicio_dia(1)/1000, MAD).strftime('%d-%m')}); «7 días» = {dt.datetime.fromtimestamp(inicio_dia(7)/1000, MAD).strftime('%d-%m')} a {dt.datetime.fromtimestamp(inicio_dia(1)/1000, MAD).strftime('%d-%m')}, igual que Meta y Captación",
                           "citas": "14 y 30 días naturales cerrados (y 90 para «sin citas»); próximas, 30 días", "estancados": "oportunidades abiertas del último mes sin cambiar de etapa en 72 h"},
              "reglas": {
                  "lead": "Lead que llega = contacto nuevo cuyo origen es un formulario o un anuncio (formulario, Facebook, Instagram, landing, calendario o WhatsApp). No cuentan: los creados a mano, los importados, los de prueba o demostración (origen, etiqueta o correo de prueba) ni los de otros negocios de la misma subcuenta (lista de exclusiones).",
                  "intento": "Llamada o mensaje que sale de GoHighLevel hecho por una persona (no por un flujo ni una campaña). Las llamadas del despacho desde su móvil no constan: por eso es «a medias».",
                  "verde_crm": "0 leads sin tocar > 24 h, citas marcadas (≤ 5 sin estado y ninguna > 48 h), asistencia ≥ 75 % cuando hay 3 o más citas marcadas, WhatsApp fallido ≤ 10 % y los leads de Meta llegan a GoHighLevel. Los flujos con error no se pueden leer todavía.",
                  "encendida": "Campaña de Meta activa o 3 o más leads en 30 días.",
                  "umbrales": {"asistencia": "≥ 75 / 60-74 / < 60 %", "sin_estado": "0 / 1-5 / > 5 o alguna > 48 h", "sin_tocar": "0 / — / ≥ 1",
                               "velocidad": "≥ 70 % en < 1 h y 4 intentos en 72 h / 40-69 % / < 40 % (garantía 1-sep)", "whatsapp": "< 2 / 2-10 / > 10 %",
                               "pct_verde": "≥ 80 / 60-79 / < 60 % (propuesta)", "carga": "≤ 16 subcuentas por especialista",
                               "rojos_especialista": "≤ 2 / 3-4 / ≥ 5"}},
              "fuentes": fuentes, "resumen": resumen, "subcuentas": filas, "leads_sin_tocar": sorted(leads_pub, key=lambda x: -x["horas"]),
              "citas_sin_estado": sorted(citas_pub, key=lambda x: -x["horas"]),
              "oportunidades_paradas": sorted(paradas_pub, key=lambda x: -x["horas"]), "especialistas": especialistas, "montajes": montajes,
              "hallazgos": hallazgos, "correo_ro": {"rebote_pct": 2.4, "fecha": "2026-10-01", "fuente": "Auditoría de entregabilidad del 1-oct (subcuenta de RO)",
                                                    "nota": "En las subcuentas de los clientes GHL no da el rebote por la API de conversaciones; aquí solo los correos marcados como fallidos."}}
    aplicar_asignaciones(salida)      # R12: especialista y account de la verdad única, con su nombre
    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "_privado").mkdir(exist_ok=True)
    tmp = SALIDA / "crm.json.tmp"
    tmp.write_text(json.dumps(salida, ensure_ascii=False, indent=1))
    tmp.replace(SALIDA / "crm.json")
    # Regla común de teléfonos (3-oct, telefono.py): «+34…» sin espacios; lo que no cuadra no se guarda y va a
    # data/telefonos/dudosos.json (apartado «crm», por cliente y sin el número entero).
    from telefono import limpiar as limpiar_tel, Dudosos
    dud_tel = Dudosos("crm")
    nombre_de_cli = {f.get("cliente_id"): f.get("nombre") for f in filas if f.get("cliente_id")}
    for p_ in privado["leads"].values():
        d_ = dict(p_.get("datos") or {})
        r_ = limpiar_tel(d_.get("telefono"))
        if r_["motivo"] == "dudoso":
            dud_tel.anotar(p_.get("cliente_id"), d_.get("telefono"), r_["aviso"], "Lead en la subcuenta de GoHighLevel del cliente (Salud del CRM)", nombre_de_cli.get(p_.get("cliente_id")))
        d_["telefono"] = r_["telefono"]
        if r_["extension"]:
            d_["extension"] = r_["extension"]
        p_["datos"] = d_
    dud_tel.guardar()
    tmp = SALIDA / "_privado" / "leads.json.tmp"
    tmp.write_text(json.dumps({"_meta": {"que": "Datos de contacto de los leads sin tocar y de las citas sin estado. Solo con /api/ver_dato (D-88).", "generado": salida["generado"]}, **privado}, ensure_ascii=False))
    tmp.replace(SALIDA / "_privado" / "leads.json")
    log(f"hecho: {len(filas)} subcuentas · {resumen['encendidas']} encendidas · verde {resumen['pct_verde']} % · "
        f"sin tocar {resumen['sin_tocar_24h']} · citas sin estado 14 d {tot_c14['sin_estado']} · llamadas {g.llamadas if g else 0}")


def aplicar_asignaciones(salida):
    """R12 (B-C03) · quién lleva cada subcuenta sale de la verdad única (asignaciones vigentes, sin bajas), y la fila
    lleva el NOMBRE del especialista además del id: Mi día de Yessica leía «especialista» (que no existía) y pintaba
    «sin especialista» en Innova Scala, Consulting F y Ecom Advisory, que son de Gustavo. Sin llamadas a GoHighLevel."""
    # Se lee lo que deja el paso «base» (build_data.py, que corre antes que este): asignaciones vigentes ya sin bajas
    # y el account de cada cliente. Es la misma regla que la verdad única (que se genera después con estos ficheros).
    hoy = dt.date.today().isoformat()
    ver = {}
    for c in leer(DATA / "clientes.json", []) or []:
        ver[c["id"]] = {"account": c.get("responsable_id"), "equipo": {"crm": []}}
    for a in leer(DATA / "asignaciones.json", []) or []:
        if a.get("silla") == "crm" and a.get("cliente_id") in ver and (not a.get("desde") or a["desde"] <= hoy) \
                and (not a.get("hasta") or a["hasta"] >= hoy):
            ver[a["cliente_id"]]["equipo"]["crm"].append({"persona_id": a["persona_id"], "principal": a.get("principal", True),
                                                          "suplencia": bool(a.get("suplencia"))})
    for v in ver.values():
        v["equipo"]["crm"].sort(key=lambda x: (not x["principal"], x["suplencia"]))
    personas = {p["id"]: p for p in leer(DATA / "personas.json", [])}
    nombres_app = {c["id"]: c["nombre"] for c in ((leer(DATA / "indice_clientes.json", {}) or {}).get("clientes", []))}
    nom = lambda pid: (personas.get(pid) or {}).get("alias") or (personas.get(pid) or {}).get("nombre") or pid
    filas = salida.get("subcuentas", [])
    for f in filas:
        v = ver.get(f.get("cliente_id")) or {}
        eq = (v.get("equipo") or {}).get("crm") or []
        e = next((x for x in eq if x.get("principal") and not x.get("suplencia")), eq[0] if eq else None)
        if f.get("cliente_id") and v:
            f["especialista_id"] = e["persona_id"] if e else None
            f["account_id"] = v.get("account")
            if not e:
                f["especialista_confianza"] = None
        f["especialista"] = nom(f["especialista_id"]) if f.get("especialista_id") else None
        f["account"] = nom(f["account_id"]) if f.get("account_id") else None
    for lista in ("leads_sin_tocar", "citas_sin_estado", "oportunidades_paradas"):
        for x in salida.get(lista, []):
            f = next((y for y in filas if y.get("cliente_id") and y.get("cliente_id") == x.get("cliente_id")), None)
            if f and "especialista_id" in x:
                x["especialista_id"] = f["especialista_id"]
    esp = {}
    for cid, v in ver.items():
        for x in ((v.get("equipo") or {}).get("crm") or []):
            if x.get("principal") and not x.get("suplencia"):
                esp.setdefault(x["persona_id"], set()).add(cid)
    previos = {e["id"]: e for e in salida.get("especialistas", [])}
    especialistas = []
    for pid, clis in sorted(esp.items()):
        mias = [f for f in filas if f.get("cliente_id") in clis]
        especialistas.append({**(previos.get(pid) or {}), "id": pid, "nombre": nom(pid), "clientes": len(clis), "subcuentas": len(mias),
                              "encendidas": sum(1 for f in mias if f.get("encendida")),
                              "verde": sum(1 for f in mias if f.get("estado") == "verde"), "ambar": sum(1 for f in mias if f.get("estado") == "ambar"),
                              "rojo": sum(1 for f in mias if f.get("estado") == "rojo"), "gris": sum(1 for f in mias if f.get("estado") == "gris"),
                              "sin_tocar": sum(f.get("sin_tocar_24h") or 0 for f in mias),
                              "sin_estado": sum((f.get("citas_14d") or {}).get("sin_estado", 0) for f in mias), "tope": 16,
                              "sin_subcuenta": sorted(nombres_app.get(c, c) for c in clis if c not in {f.get("cliente_id") for f in filas})})
    salida["especialistas"] = especialistas
    if isinstance(salida.get("resumen"), dict):
        salida["resumen"]["encendidas_sin_especialista"] = [f["nombre"] for f in filas if f.get("tipo") == "cliente" and not f.get("especialista_id") and f.get("encendida")]
    fu = (salida.get("fuentes") or {}).get("asignaciones")
    if isinstance(fu, dict):
        fu.update({"fuente": "Verdad única (asignaciones vigentes, silla CRM principal)", "estado": "bien",
                   "nota": "R12: quién lleva cada subcuenta lo deciden las asignaciones; GoHighLevel no decide dueños."})
    return salida


def solo_asignaciones():
    """--solo-asignaciones: reaplica quién lleva qué sobre el crm.json existente (sin leer GoHighLevel)."""
    f = SALIDA / "crm.json"
    salida = json.loads(f.read_text())
    aplicar_asignaciones(salida)
    tmp = SALIDA / "crm.json.tmp"
    tmp.write_text(json.dumps(salida, ensure_ascii=False, indent=1))
    tmp.replace(f)
    print(f"crm.json: asignaciones reaplicadas · {len(salida.get('especialistas', []))} especialistas · "
          f"encendidas sin especialista {len((salida.get('resumen') or {}).get('encendidas_sin_especialista') or [])}")


if __name__ == "__main__":
    solo_asignaciones() if "--solo-asignaciones" in sys.argv else main()
