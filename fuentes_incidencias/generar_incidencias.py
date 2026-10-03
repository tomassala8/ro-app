#!/usr/bin/env python3
"""
generar_incidencias.py · M14 «Incidencias y control de Operaciones» (E2 del plan v2; puntos 7 y 9 de Mili, M5).

Escribe data/incidencias/incidencias.json (SOLO LECTURA de herramientas externas; nada se escribe fuera):

  · incidencias   detecciones automáticas del día con su causa PROPUESTA (regla R13):
                  - Desk: correo de cliente > 48 h con agente (ejecución) · ticket de cliente sin agente > 4 h
                    (configuración) · tickets abiertos a nombre de un agente desactivado (configuración) ·
                    departamentos que la llave no puede leer (sistema).  ← data/bandeja/bandeja.json (Desk en vivo
                    de esta tarde, no se vuelve a pedir) + agentes de Desk en vivo (zh.py).
                  - Zadarma: llamada perdida sin devolver > 24 h (ejecución) · entrantes que no llegan a ninguna
                    extensión o van a una que no existe (configuración) · extensiones sin registrar (configuración) ·
                    ← zadarma_crudo.json del panel (hoy 06:20) + estado de cada extensión en vivo (zd.py).
                  - Alarmas de cliente en rojo con más de 48 h (por la primera vez vista o por el rastro escrito
                    de Mili en ClickUp) ← data/alarmas.json + fuentes_incidencias/rastro_operaciones.json.
                  Cada una con su historia previa (avisos, reiteraciones, escalados) y la prueba enlazada.
  · incongruencias  ClickUp ↔ Desk ↔ CRM (panel v27 + cruce en vivo: account de la app ≠ agente de Desk).
  · accesos       quién ya no está y sigue con acceso (Desk, CRM, ClickUp, Zadarma) frente a personas.json.
  · traspasos     traspasos de cartera con fecha, prueba, revisión a 14 días y estado en cada herramienta.
  · vistos        quién vio primero cada cliente en rojo (Mili frente a Tomás o Coti), del rastro escrito.
  · mapa_calor    accounts × reglas (panel v27, «Quién falla en qué»).
  · control       mapa de control por persona (panel v27, v7.control + planificación).

Filas con cliente_id → el servidor solo las da a quien ve ese cliente. Filas sin cliente llevan persona_id
(la persona afectada, o «mili» para lo de sistema) → solo Operaciones, su jefe, RRHH y dirección.
Sin teléfonos, correos, sueldos ni claves. Pasa escaner_secretos.py antes de escribir.

Uso:  python3 fuentes_incidencias/generar_incidencias.py   [--sin-vivo]   (sin-vivo: no llama a Desk/Zadarma/ClickUp)
"""
import datetime as dt
import hashlib
import json
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
DATA = APP / "data"
SALIDA = DATA / "incidencias" / "incidencias.json"
ESTADO = AQUI / "primera_vez.json"
sys.path.insert(1, str(Path(__file__).resolve().parents[1]))  # C5: rutas y secretos en config.py
import config  # noqa: E402
PANEL = config.PANEL_BUILD
HERR = config.HERRAMIENTAS
SIN_VIVO = "--sin-vivo" in sys.argv

AHORA = dt.datetime.now()
HOY = AHORA.date()


def leer(p, defecto=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return defecto


def norm(t):
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]+", " ", t).split()


def uid(*partes):
    return "i-" + hashlib.sha1("|".join(map(str, partes)).encode()).hexdigest()[:10]


def fecha_de(t):
    if not t:
        return None
    t = str(t).replace("T", " ")
    for f in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d-%m-%Y %H:%M"):
        try:
            return dt.datetime.strptime(t[:len(dt.datetime(2000, 1, 1).strftime(f))], f)
        except ValueError:
            continue
    return None


def mas_dias_laborables(d, n):
    while n > 0:
        d += dt.timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


# ------------------------------------------------------------------ base de la app
_p = leer(DATA / "personas.json", [])
PERSONAS = _p if isinstance(_p, list) else _p.get("personas", [])
P_ID = {p["id"]: p for p in PERSONAS}
_c = leer(DATA / "clientes.json", [])
CLIENTES = _c if isinstance(_c, list) else _c.get("clientes", [])
C_ID = {c["id"]: c for c in CLIENTES}
_a = leer(DATA / "alarmas.json", [])
ALARMAS = _a if isinstance(_a, list) else _a.get("alarmas", [])
_s = leer(DATA / "asignaciones.json", [])
ASIG = _s if isinstance(_s, list) else _s.get("asignaciones", [])


def persona_por_nombre(nombre):
    """Nombre libre (Desk, ClickUp, panel) → id de personas.json. Prudente: no adivina con un solo apellido."""
    t = norm(nombre)
    if not t:
        return None
    for p in PERSONAS:
        if norm(p["nombre"]) == t or any(norm(a) == t for a in p.get("alias_todos") or []):
            return p["id"]
    if len(t) >= 2:
        for p in PERSONAS:
            n = norm(p["nombre"])
            if len(n) >= 2 and n[0] == t[0] and n[1] == t[1]:
                return p["id"]
        return None
    cand = [p["id"] for p in PERSONAS if norm(p["nombre"])[:1] == t[:1]]
    return cand[0] if len(cand) == 1 else None


def nombre_p(pid):
    p = P_ID.get(pid)
    return (p.get("alias_todos") or [None])[0] if p and p.get("alias_todos") and len(p["alias_todos"][0]) <= 8 else (p["nombre"] if p else None)


def cliente_por_nombre(nombre):
    t = " ".join(norm(nombre))
    if not t:
        return None
    for c in CLIENTES:
        if " ".join(norm(c["nombre"])) == t:
            return c["id"]
    for c in CLIENTES:
        n = " ".join(norm(c["nombre"]))
        if n and (n.startswith(t) or t.startswith(n)) and min(len(n), len(t)) >= 4:
            return c["id"]
    return None


def account_de(cid):
    c = C_ID.get(cid) or {}
    return c.get("responsable_id")


FUENTES = {}
ESTADO_PREV = leer(ESTADO, {}) or {}
PRIMERA = ESTADO_PREV.get("primera_vez", {})


def primera_vez(clave, fecha):
    """Recuerda el primer día en que se vio una detección (para «abierta desde» y el corte de 48 h)."""
    f = PRIMERA.get(clave)
    if not f or (fecha and fecha < f):
        PRIMERA[clave] = fecha
    return PRIMERA[clave]


# ------------------------------------------------------------------ rastro escrito (historia previa)
RASTRO = leer(AQUI / "rastro_operaciones.json", {})
CANAL = RASTRO.get("_meta", {}).get("canales", {})
NOMBRE_CANAL = RASTRO.get("_meta", {}).get("nombres_canal", {})


def enlace_evento(e):
    if e.get("tarea"):
        return e["tarea"]
    if e.get("canal") and CANAL.get(e["canal"]):
        base = f"https://app.clickup.com/90152357276/chat/r/{CANAL[e['canal']]}"
        return f"{base}/t/{e['msg']}" if e.get("msg") else base
    return None


HIST = defaultdict(list)
for e in RASTRO.get("eventos", []):
    HIST[e["cliente_id"]].append({
        "fecha": e["fecha"], "paso": e["paso"], "quien": e["quien"], "a": e.get("a"),
        "por": ("Tarea de ClickUp" if e.get("tarea") else f"ClickUp · {NOMBRE_CANAL.get(e.get('canal'), e.get('canal'))}") if (e.get("tarea") or e.get("canal")) else "Cartera de ClickUp",
        "texto": e["texto"], "enlace": enlace_evento(e), "origen": "rastro ClickUp",
    })
for v in HIST.values():
    v.sort(key=lambda x: x["fecha"])
FUENTES["rastro"] = {"fuente": "Rastro escrito de Mili en ClickUp", "hora": "2026-10-02 10:00", "estado": "bien",
                     "nota": "14-sep → 2-oct, leído por API y resumido a mano (rastro_mili.md)"}

INCIDENCIAS = []


def nueva(**k):
    k.setdefault("historia", [])
    k.setdefault("gravedad", "rojo")
    INCIDENCIAS.append(k)
    return k


# ------------------------------------------------------------------ Desk (bandeja de esta tarde)
BDJ = leer(DATA / "bandeja" / "bandeja.json", {}) or {}
fd = (BDJ.get("fuentes") or {}).get("desk") or {}
FUENTES["desk"] = {"fuente": "Zoho Desk", "hora": fd.get("hora"), "estado": fd.get("estado", "sin datos"), "nota": fd.get("nota")}
correos = [x for x in BDJ.get("correos", []) if x.get("cliente_id") and not x.get("auto")]
URL_DESK = "https://desk.zoho.eu/support/rankingonline836/ShowHomePage.do#Cases"

# Agentes de Desk en vivo (nombre y estado; nada más)
AGENTES_DESK = {}
if not SIN_VIVO:
    try:
        sys.path.insert(0, str(HERR / "zoho"))
        import zh  # noqa: E402
        tk, api = zh.acceso()
        oid = str(zh.get(tk, "https://desk.zoho.eu/api/v1/organizations")["data"][0]["id"])
        AGENTE_ID = {}
        for x in zh.get(tk, "https://desk.zoho.eu/api/v1/agents?limit=200", orgId=oid).get("data", []):
            nn = x.get("name") or f"{x.get('firstName', '')} {x.get('lastName', '')}".strip()
            AGENTES_DESK[nn] = x.get("status")
            AGENTE_ID[nn] = x.get("id")
        USUARIOS_CRM = {u.get("full_name"): u.get("status") for u in zh.get(tk, api + "/crm/v6/users?type=AllUsers&per_page=200").get("users", [])}
        FUENTES["desk_agentes"] = {"fuente": "Zoho Desk · agentes", "hora": AHORA.strftime("%Y-%m-%d %H:%M"), "estado": "bien", "nota": f"{len(AGENTES_DESK)} agentes"}
        FUENTES["crm_usuarios"] = {"fuente": "Zoho CRM · usuarios", "hora": AHORA.strftime("%Y-%m-%d %H:%M"), "estado": "bien", "nota": f"{len(USUARIOS_CRM)} usuarios"}
    except Exception as e:  # plan B: sin agentes en vivo
        USUARIOS_CRM = {}
        FUENTES["desk_agentes"] = {"fuente": "Zoho Desk · agentes", "hora": None, "estado": "error", "nota": str(e)[:120]}
else:
    USUARIOS_CRM = {}
desactivado = {n for n, s in AGENTES_DESK.items() if s and s != "ACTIVE"}
ABIERTOS_AGENTE = {}


def abiertos_en_desk(nombre):
    """Tickets abiertos (cualquier departamento legible) de un agente, contados en vivo. None si no se puede."""
    if SIN_VIVO or nombre not in globals().get("AGENTE_ID", {}):
        return None
    if nombre in ABIERTOS_AGENTE:
        return ABIERTOS_AGENTE[nombre]
    import urllib.request as ur
    n = 0
    try:
        for i in range(1, 2000, 100):
            req = ur.Request(f"https://desk.zoho.eu/api/v1/tickets?assignee={AGENTE_ID[nombre]}&from={i}&limit=100",
                             headers={"Authorization": "Zoho-oauthtoken " + tk, "orgId": oid})
            b = ur.urlopen(req, timeout=60).read()
            d = json.loads(b).get("data", []) if b else []
            n += sum(1 for t in d if t.get("status") not in ("Cerrado", "Closed"))
            if len(d) < 100:
                break
    except Exception:
        return None
    ABIERTOS_AGENTE[nombre] = n
    return n

por_cli_48 = defaultdict(list)
por_cli_sin = defaultdict(list)
por_agente_baja = defaultdict(list)
for x in correos:
    if x.get("asignado_id") or x.get("asignado"):
        ag = x.get("asignado") or ""
        pid_ag = persona_por_nombre(ag)
        de_baja = ag in desactivado or (pid_ag and P_ID.get(pid_ag, {}).get("estado") == "baja") or (ag and not pid_ag)
        if de_baja:
            por_agente_baja[ag].append(x)
        elif x["horas"] > 48:
            por_cli_48[x["cliente_id"]].append(x)
    elif x["horas"] > 4:
        por_cli_sin[x["cliente_id"]].append(x)


def antiguedad(horas):
    """V2 (40_A B5): «5 h» hasta 48 h; luego en días («478 h» → «20 días»), como fechas.antiguedad() de la app."""
    h = round(horas or 0)
    return f"{h} h" if h <= 48 else f"{round(h / 24)} días"


def plural(n, uno, varios):
    return f"{n} {uno if n == 1 else varios}"


def resumen_tickets(xs):
    xs = sorted(xs, key=lambda t: -t["horas"])
    return [{"numero": t["numero"], "asunto": (t.get("asunto") or "")[:90], "horas": round(t["horas"]), "desde": t.get("desde"),
             "agente": t.get("asignado"), "url": t.get("url"), "queja": bool(t.get("queja"))} for t in xs[:6]]


for cid, xs in por_cli_48.items():
    xs.sort(key=lambda t: -t["horas"])
    viejo = xs[0]
    agentes = Counter(t.get("asignado") for t in xs).most_common()
    det = (fecha_de(viejo.get("desde")) or AHORA) + dt.timedelta(hours=48)
    acc = account_de(cid)
    nueva(id=uid("desk48", cid), origen="desk", regla="desk_48", titulo="Correo del cliente sin respuesta > 48 h",
          # V2 (barrido v1): sin el número de ticket en el texto (va en «tickets» y en la prueba, que la pantalla enlaza)
          texto=f"{plural(len(xs), 'correo', 'correos')} de {C_ID[cid]['nombre']} con agente y sin contestar; el más antiguo lleva {antiguedad(viejo['horas'])} (agente {viejo.get('asignado')}).",
          cliente_id=cid, cliente=C_ID[cid]["nombre"], responsable_id=acc or persona_por_nombre(agentes[0][0]),
          detectada=primera_vez(f"desk48|{cid}", det.strftime("%Y-%m-%d")),
          donde="contacto_cliente", por_que="ejecucion", por_que_motivo="Hay agente asignado y el correo no se contesta: la regla la incumple una persona.",
          gravedad="rojo", queja=any(t.get("queja") for t in xs), prueba=viejo.get("url"),
          numeros={"correos": len(xs), "dias_mas_antiguo": round(viejo["horas"] / 24), "agentes": [a for a, _ in agentes]},
          tickets=resumen_tickets(xs), fuente="desk", umbral="D-29: verde < 24 h · ámbar 24-48 h · rojo > 48 h")

for cid, xs in por_cli_sin.items():
    xs.sort(key=lambda t: -t["horas"])
    viejo = xs[0]
    det = (fecha_de(viejo.get("desde")) or AHORA) + dt.timedelta(hours=4)
    nueva(id=uid("desksin", cid), origen="desk", regla="desk_sin_agente", titulo="Ticket de cliente sin agente > 4 h",
          texto=f"{plural(len(xs), 'ticket', 'tickets')} de {C_ID[cid]['nombre']} sin agente; el más antiguo lleva {antiguedad(viejo['horas'])}. Nadie lo va a contestar hasta que se asigne.",
          cliente_id=cid, cliente=C_ID[cid]["nombre"], responsable_id="mili",
          detectada=primera_vez(f"desksin|{cid}", det.strftime("%Y-%m-%d")),
          donde="contacto_cliente", por_que="configuracion", por_que_motivo="El ticket entra sin regla de asignación: falla la configuración de Desk, no una persona.",
          gravedad="rojo" if viejo["horas"] > 48 else "ambar", prueba=viejo.get("url"),
          numeros={"tickets": len(xs), "horas_mas_antiguo": round(viejo["horas"])}, tickets=resumen_tickets(xs), fuente="desk",
          umbral="M5 de Mili: sin agente más de 4 h laborables")

for ag, xs in por_agente_baja.items():
    pid = persona_por_nombre(ag)
    clis = Counter(t["cliente_id"] for t in xs)
    total = abiertos_en_desk(ag)
    nueva(id=uid("deskbaja", ag), origen="desk", regla="desk_agente_baja", titulo="Tickets abiertos a nombre de alguien que ya no está",
          texto=f"{len(xs)} ticket(s) de cliente siguen asignados a {ag} ({'desactivado en Desk' if ag in desactivado else 'no está en el equipo'}) en {len(clis)} cliente(s): {', '.join(C_ID[c]['nombre'] for c, _ in clis.most_common(6))}.{f' En total tiene {total} tickets sin cerrar en Desk.' if total else ''}",
          cliente_id=None, cliente=None, persona_id=pid, afectado=ag, responsable_id="mili",
          detectada=primera_vez(f"deskbaja|{ag}", HOY.isoformat()),
          donde="contacto_cliente", por_que="configuracion", por_que_motivo="El agente está desactivado pero sus tickets no se reasignaron: nadie los ve en su bandeja.",
          gravedad="rojo", prueba=sorted(xs, key=lambda t: -t["horas"])[0].get("url"),
          numeros={"tickets": len(xs), "clientes": len(clis), "sin_cerrar_en_desk": total}, clientes_afectados=[c for c, _ in clis.most_common()],
          tickets=resumen_tickets(xs), fuente="desk", umbral="Cualquier ticket abierto de un agente desactivado")

deps = BDJ.get("departamentos", [])
ilegibles = [d["nombre"] for d in deps if d.get("activo") and not d.get("legible")]
if ilegibles:
    nueva(id=uid("deskdeps"), origen="desk", regla="desk_departamentos", titulo="Departamentos de Desk que la app no puede leer",
          texto=f"La llave de lectura ve {len(deps)} departamentos, pero {len(ilegibles)} activos dan «sin permiso»: {', '.join(ilegibles)}. Sus tickets no entran en la bandeja ni en estas comprobaciones (tampoco el «departamento equivocado»).",
          cliente_id=None, persona_id=None, responsable_id="tomas", detectada=primera_vez("deskdeps", HOY.isoformat()),
          donde="integracion", por_que="sistema", por_que_motivo="Permiso del agente de la llave de lectura: lo arregla Tomás haciéndolo miembro de esos departamentos.",
          gravedad="ambar", prueba=URL_DESK, numeros={"departamentos": len(deps), "ilegibles": len(ilegibles)}, fuente="desk",
          umbral="Toda fuente que no se puede leer es una incidencia de sistema")

# ------------------------------------------------------------------ Zadarma
Z = leer(PANEL / "zadarma_crudo.json", {}) or {}
zm = Z.get("_meta", {})
FUENTES["zadarma"] = {"fuente": "Zadarma", "hora": (zm.get("generado") or "").replace("T", " ")[:16], "estado": "bien" if Z else "sin datos",
                      "nota": "llamadas de septiembre y octubre del panel v27"}
LL = [x for k in ("septiembre", "octubre") for x in (Z.get(k) or {}).get("llamadas", [])]
EXT = [str(n) for n in (Z.get("extensiones") or {}).get("numbers", [])]
entr = [x for x in LL if x.get("sentido") == "entrante"]
sin_destino = [x for x in entr if not x.get("extension") and x.get("estado") != "contestada"]
if sin_destino:
    ult = max(x["inicio"] for x in sin_destino)
    nueva(id=uid("zsindest"), origen="zadarma", regla="zadarma_sin_destino", titulo="Llamadas entrantes que no llegan a ninguna extensión",
          texto=f"{len(sin_destino)} llamadas entrantes desde el 1-sep no sonaron en ninguna extensión ({sum(1 for x in sin_destino if x['estado'] == 'sin respuesta')} sin respuesta, {sum(1 for x in sin_destino if x['estado'] == 'fallida')} fallidas). La última, el {ult[8:10]}-{ult[5:7]} a las {ult[11:16]}. Puede ser fuera de horario sin buzón o un desvío roto.",
          cliente_id=None, persona_id=None, responsable_id="mili", detectada=primera_vez("zsindest", min(x["inicio"] for x in sin_destino)[:10]),
          donde="contacto_cliente", por_que="configuracion", por_que_motivo="El número entra en la centralita y no tiene destino: horario, buzón o desvío.",
          gravedad="rojo", prueba="https://my.zadarma.com/mypbx/", numeros={"llamadas": len(sin_destino), "ultima": ult}, fuente="zadarma",
          umbral="Ninguna llamada entrante sin destino")
fantasma = [x for x in entr if x.get("extension") and x["extension"] not in EXT and x["extension"] != "8500"]
if fantasma:
    ex = sorted({x["extension"] for x in fantasma})
    nueva(id=uid("zfantasma"), origen="zadarma", regla="zadarma_ext_inexistente", titulo="Desvío a una extensión que no existe",
          texto=f"{len(fantasma)} llamadas entrantes fueron a la(s) extensión(es) {', '.join(ex)}, que no están entre las {len(EXT)} de la centralita (100 a 113); {sum(1 for x in fantasma if x['estado'] != 'contestada')} no se contestaron.",
          cliente_id=None, persona_id=None, responsable_id="mili", detectada=primera_vez("zfantasma", min(x["inicio"] for x in fantasma)[:10]),
          donde="contacto_cliente", por_que="configuracion", por_que_motivo="Hay una regla de la centralita que manda llamadas a un destino que no existe.",
          gravedad="ambar", prueba="https://my.zadarma.com/mypbx/", numeros={"llamadas": len(fantasma), "extensiones": ex}, fuente="zadarma",
          umbral="Ninguna llamada a un destino inexistente")

quien_ext = {}
for x in LL:
    m = re.match(r"(.+?) \((\d+)\)", x.get("quien") or "")
    if m:
        quien_ext[m.group(2)] = m.group(1)
uso_ext = Counter(x.get("extension") for x in LL if x.get("extension"))
ESTADO_EXT = {}
if not SIN_VIVO and EXT:
    try:
        sys.path.insert(0, str(HERR / "zadarma"))
        import zd  # noqa: E402
        for n in EXT:
            try:
                ESTADO_EXT[n] = zd.get(f"/v1/pbx/internal/{n}/status/").get("is_online")
            except Exception as e:  # una extensión que falla no para el resto
                ESTADO_EXT[n] = f"error: {str(e)[:60]}"
            time.sleep(0.6)
        FUENTES["zadarma_ext"] = {"fuente": "Zadarma · extensiones", "hora": AHORA.strftime("%Y-%m-%d %H:%M"), "estado": "bien", "nota": f"{len(EXT)} extensiones"}
    except Exception as e:
        FUENTES["zadarma_ext"] = {"fuente": "Zadarma · extensiones", "hora": None, "estado": "error", "nota": str(e)[:120]}
EXTENSIONES = []
for n in EXT:
    nombre = quien_ext.get(n)
    pid = persona_por_nombre(nombre) if nombre else None
    EXTENSIONES.append({"extension": n, "nombre": nombre, "persona_id_ext": pid, "en_linea": ESTADO_EXT.get(n), "llamadas_32d": uso_ext.get(n, 0)})
fuera = [e for e in EXTENSIONES if e["en_linea"] == "false" and e["llamadas_32d"] == 0]
if fuera:
    nueva(id=uid("zoffline"), origen="zadarma", regla="zadarma_ext_sin_registrar", titulo="Extensiones sin registrar y sin uso",
          texto=f"{len(fuera)} extensiones están desconectadas ahora y no han tenido ninguna llamada desde el 1-sep: {', '.join(e['extension'] + (' (' + e['nombre'] + ')' if e['nombre'] else '') for e in fuera)}. O se dan de baja o se asignan; si alguien desvía a ellas, la llamada se pierde.",
          cliente_id=None, persona_id=None, responsable_id="mili", detectada=primera_vez("zoffline", HOY.isoformat()),
          donde="contacto_cliente", por_que="configuracion", por_que_motivo="La API de Zadarma solo dice si la extensión está conectada; el resto (desvíos, horarios) va en la revisión mensual a mano.",
          gravedad="ambar", prueba="https://my.zadarma.com/mypbx/", numeros={"extensiones": len(fuera)}, fuente="zadarma",
          umbral="Revisión mensual de la centralita (M5 de Mili)")

for x in BDJ.get("llamadas", []):
    pid = x.get("cliente_id")
    nueva(id=uid("zperdida", x["id"]), origen="zadarma", regla="zadarma_perdida", titulo="Llamada perdida sin devolver > 24 h",
          texto=f"{x.get('llamadas', 1)} llamada(s) entrante(s) del número {x.get('numero_oculto')} sin contestar ni devolver; la última, {x.get('ultima')}. {'Es de ' + x['cliente'] + '.' if x.get('cliente') else 'No es de ningún cliente conocido: puede ser un lead o un proveedor.'}",
          cliente_id=pid, cliente=x.get("cliente"), persona_id=None, responsable_id=account_de(pid) if pid else "mili",
          detectada=primera_vez(f"zperdida|{x['id']}", (x.get("primera") or x.get("ultima") or "")[:10]),
          donde="contacto_cliente", por_que="ejecucion", por_que_motivo="Nadie devolvió la llamada: la regla la incumple una persona.",
          gravedad=x.get("gravedad", "rojo"), prueba="https://my.zadarma.com/mystatistics/", numeros={"llamadas": x.get("llamadas"), "horas": round(x.get("horas") or 0)},
          fuente="zadarma", umbral="M5 de Mili: devolver en menos de 24 h")

# ------------------------------------------------------------------ alarmas de cliente > 48 h
DONDE_TIPO = {
    "Sin responder": "contacto_cliente", "Sin correo esta semana": "contacto_cliente", "Sin reunión en septiembre": "contacto_cliente",
    "Semáforo sin rellenar": "contacto_cliente", "Semáforo en rojo": "despacho", "Revisión del account >48 h": "produccion",
    "Bloqueo sin resolver": "produccion", "Bloqueo callado más de 5 días": "produccion", "Trabajo no planificado": "produccion", "Rompe el semanal": "produccion",
    "Informes de septiembre pendientes": "produccion", "Cliente nuevo fuera de plazo": "produccion", "Cliente nuevo sin onboarding": "produccion",
    "Cliente nuevo sin account": "produccion", "Gasto sin leads": "publicidad", "Coste por lead alto": "publicidad",
}
PRIO = ["Semáforo en rojo", "Sin responder", "Cliente nuevo fuera de plazo", "Cliente nuevo sin account", "Bloqueo sin resolver", "Bloqueo callado más de 5 días",
        "Sin reunión en septiembre", "Revisión del account >48 h", "Semáforo sin rellenar", "Gasto sin leads", "Coste por lead alto",
        "Cliente nuevo sin onboarding", "Sin correo esta semana", "Informes de septiembre pendientes", "Trabajo no planificado", "Rompe el semanal"]
rojas_cli = defaultdict(list)
for a in ALARMAS:
    if a.get("ambito") == "cliente" and a.get("gravedad") == "rojo" and a.get("cliente_id"):
        rojas_cli[a["cliente_id"]].append(a)
        primera_vez(f"alarma|{a['cliente_id']}|{a['tipo']}", a.get("desde") or HOY.isoformat())
corte = (HOY - dt.timedelta(days=2)).isoformat()
for cid in sorted(set(rojas_cli) | set(HIST)):
    hist = [e for e in HIST.get(cid, [])]
    al = sorted(rojas_cli.get(cid, []), key=lambda a: PRIO.index(a["tipo"]) if a["tipo"] in PRIO else 99)
    desde_alarma = min((PRIMERA.get(f"alarma|{cid}|{a['tipo']}") or HOY.isoformat() for a in al), default=None)
    desde_rastro = hist[0]["fecha"][:10] if hist else None
    desde = min(x for x in (desde_alarma, desde_rastro) if x) if (desde_alarma or desde_rastro) else None
    if not desde or desde > corte or cid not in C_ID:
        continue
    c = C_ID[cid]
    avisos = [e for e in hist if e["quien"] in ("mili", "tomas", "constanza") and e["paso"] in ("avisada", "reiterada", "escalada", "accion")]
    con_aviso_mili = any(e["quien"] == "mili" and e["paso"] in ("avisada", "reiterada", "escalada", "accion") for e in hist)
    if al:
        regla = al[0]["tipo"]
        texto = "; ".join(dict.fromkeys(f"{a['tipo']}: {a['texto']}" for a in al[:3]))
        estado_ini = None
    else:
        resp = [e for e in hist if e["paso"] == "respuesta"]
        if not resp:
            continue
        regla = "Cliente en rojo (rastro)"
        texto = f"Escalado en el rastro de ClickUp y sin alarma roja hoy: {resp[-1]['texto']}"
        estado_ini = {"paso": "resuelta", "fecha": resp[-1]["fecha"], "prueba": resp[-1]["enlace"], "texto": resp[-1]["texto"]}
    nueva(id=uid("alarma", cid), origen="alarma", regla=regla, titulo=f"Cliente en rojo más de 48 h · {regla}",
          texto=texto, cliente_id=cid, cliente=c["nombre"], responsable_id=c.get("responsable_id"),
          detectada=desde, donde=DONDE_TIPO.get(regla, "despacho"),
          por_que="ejecucion" if con_aviso_mili else "gestion_operaciones",
          por_que_motivo=("Operaciones avisó por escrito y sigue igual: propuesta «ejecución de una persona»." if con_aviso_mili
                          else "No hay ninguna prueba de aviso de Operaciones: por la regla R13 cuenta como «gestión de Operaciones»."),
          gravedad="rojo", prueba=al[0].get("enlace") if al else (hist[-1]["enlace"] if hist else None),
          numeros={"alarmas_rojas": len(al), "avisos_escritos": len(avisos), "motivos": [a["tipo"] for a in al]},
          historia=hist, estado_inicial=estado_ini, fuente="panel", umbral="E2: toda alarma de más de 48 h entra sola")

# ------------------------------------------------------------------ incongruencias
D = leer(PANEL / "datos.json", {}) or {}
FUENTES["panel"] = {"fuente": "Panel de operaciones v27", "hora": dt.datetime.strptime(D["generado"], "%d-%m-%Y %H:%M").strftime("%Y-%m-%d %H:%M") if D.get("generado") else None,
                    "estado": "bien" if D else "sin datos", "nota": "ClickUp, Desk, Sign, Meta y CRM cruzados por el panel de Mili"}
HERRAMIENTAS_TIPO = {
    "Firmado en Zoho Sign y sin ficha en la Cartera de ClickUp": ["sign", "clickup"], "Cuenta con actividad en Desk que no está en la Cartera": ["desk", "clickup"],
    "Cliente activo sin cuota: sin horas pautadas": ["clickup"], "Tareas abiertas asignadas a personas que ya no están": ["clickup"],
    "Cliente activo sin cuenta en Desk": ["clickup", "desk"], "Cliente activo sin carpeta de trabajo en ClickUp": ["clickup"],
    "El account de ClickUp no es quien lleva sus tickets en Desk": ["clickup", "desk"], "Cliente activo sin account asignado en ClickUp": ["clickup", "crm"],
    "En offboarding pero con carpeta en «Clientes mensuales»": ["clickup"], "Outreach sin fuente automática": ["hojas"],
    "Cuota sacada de facturación, falta en la Cartera de ClickUp": ["airtable", "clickup"], "Baja pero sigue activo en la Cartera de ClickUp": ["holded", "clickup"],
    "En la Cartera y sin carpeta de trabajo": ["clickup"], "Tareas sin persona asignada": ["clickup"], "Tareas sin estimación de horas": ["clickup"], "Windsor": ["windsor"],
}
OPCIONES = {
    "El account de ClickUp no es quien lleva sus tickets en Desk": ["Reasignar los tickets en Desk al account", "El account es el de Desk: cambiar asignaciones", "No aplica"],
    "Tareas abiertas asignadas a personas que ya no están": ["Reasignar a su sustituto", "Cerrar las tareas", "No aplica"],
    "Baja pero sigue activo en la Cartera de ClickUp": ["Pasar a «baja» en ClickUp", "No es baja: corregir facturación", "No aplica"],
}
INCONG = []
vistos_inc = set()
for i in D.get("incongruencias", []):
    cid = cliente_por_nombre(i.get("cliente"))
    pid = persona_por_nombre(i.get("cliente")) if i["tipo"] == "Tareas abiertas asignadas a personas que ya no están" else None
    clave = (i["tipo"], cid or i.get("cliente"))
    vistos_inc.add(clave)
    INCONG.append({"id": uid("inc", i["tipo"], i.get("cliente")), "tipo": i["tipo"], "cliente_id": cid, "cliente": i.get("cliente"),
                   "persona_id": None if cid else pid, "detalle": i.get("detalle"), "decide": i.get("decide") or "Mili",
                   "herramientas": HERRAMIENTAS_TIPO.get(i["tipo"], ["clickup"]), "opciones": OPCIONES.get(i["tipo"], ["Corregido", "No aplica"]),
                   "origen": "panel v27"})
# Cruce en vivo: account de la app (asignaciones) ≠ agente que lleva sus tickets abiertos en Desk
por_cli_ag = defaultdict(Counter)
for x in correos:
    if x.get("asignado"):
        por_cli_ag[x["cliente_id"]][x["asignado"]] += 1
for cid, cnt in por_cli_ag.items():
    acc = account_de(cid)
    ag, n = cnt.most_common(1)[0]
    pid_ag = persona_por_nombre(ag)
    if acc and pid_ag != acc and not (acc == "tomas"):
        tipo = "El account de la app no es quien lleva sus tickets en Desk"
        if ("El account de ClickUp no es quien lleva sus tickets en Desk", cid) in vistos_inc:
            continue
        INCONG.append({"id": uid("inc", tipo, cid), "tipo": tipo, "cliente_id": cid, "cliente": C_ID[cid]["nombre"], "persona_id": None,
                       "detalle": f"App (asignaciones): {nombre_p(acc) or acc} · Desk: {ag} lleva {n} de {sum(cnt.values())} {'ticket abierto' if sum(cnt.values()) == 1 else 'tickets abiertos'}{' (desactivado en Desk)' if ag in desactivado else ''}.",
                       "decide": "Mili", "herramientas": ["app", "desk"], "opciones": OPCIONES["El account de ClickUp no es quien lleva sus tickets en Desk"],
                       "origen": "cruce en vivo (Desk de hoy + asignaciones)"})

# ------------------------------------------------------------------ accesos de quien ya no está
ACCESOS = []
estado_app = {p["id"]: p.get("estado") for p in PERSONAS}


def fila_acceso(nombre, herramienta, estado_h, que_hacer, prueba=None):
    pid = persona_por_nombre(nombre)
    ACCESOS.append({"id": uid("acc", herramienta, nombre), "persona": nombre, "persona_ref": pid, "estado_app": estado_app.get(pid, "no está en personas"),
                    "herramienta": herramienta, "estado_herramienta": estado_h, "que_hacer": que_hacer, "prueba": prueba,
                    "persona_id": pid if pid and estado_app.get(pid) != "activo" else None})


for n, s in AGENTES_DESK.items():
    pid = persona_por_nombre(n)
    abiertos = len(por_agente_baja.get(n, []))
    if s == "ACTIVE" and (not pid or estado_app.get(pid) in ("baja", "dudoso")):
        fila_acceso(n, "Zoho Desk", "activo", "Cuenta activa que no es de una persona del equipo: comprobar quién la usa y dejarla con nombre propio o desactivarla." if not pid else "Desactivar el agente.", URL_DESK)
    elif s != "ACTIVE" and abiertos:
        fila_acceso(n, "Zoho Desk", "desactivado con tickets", f"Desactivado, pero con {abiertos} ticket(s) de cliente abiertos a su nombre: reasignarlos.", URL_DESK)
for n, s in USUARIOS_CRM.items():
    pid = persona_por_nombre(n)
    if s == "active" and (not pid or estado_app.get(pid) in ("baja", "dudoso")):
        fila_acceso(n, "Zoho CRM", "activo", "Usuario activo que no está en el equipo: desactivar.")
CU_MIEMBROS = []
if not SIN_VIVO:
    try:
        sys.path.insert(0, str(HERR / "clickup_api"))
        import cu  # noqa: E402
        CU_MIEMBROS = [m.get("user", {}).get("username") for m in cu.get(f"/team/{cu.TEAM}").get("team", {}).get("members", [])]
        FUENTES["clickup_miembros"] = {"fuente": "ClickUp · miembros", "hora": AHORA.strftime("%Y-%m-%d %H:%M"), "estado": "bien", "nota": f"{len(CU_MIEMBROS)} miembros"}
    except Exception as e:
        FUENTES["clickup_miembros"] = {"fuente": "ClickUp · miembros", "hora": None, "estado": "error", "nota": str(e)[:120]}
for n in CU_MIEMBROS:
    pid = persona_por_nombre(n)
    if not pid or estado_app.get(pid) in ("baja", "dudoso"):
        fila_acceso(n, "ClickUp", "miembro", "Miembro del espacio de trabajo que no está activo en el equipo: quitarlo.")
for e in EXTENSIONES:
    if e["nombre"] and (not e["persona_id_ext"] or estado_app.get(e["persona_id_ext"]) in ("baja", "dudoso")):
        crm = next((s for nn, s in USUARIOS_CRM.items() if norm(nn)[:1] == norm(e["nombre"].split("-")[-1])[:1]), None)
        fila_acceso(e["nombre"], "Zadarma", f"extensión {e['extension']} ({'conectada' if e['en_linea'] == 'true' else 'desconectada'})",
                    "Extensión a nombre de alguien que no está en el equipo" + (f" (en el CRM figura desactivada)" if crm == "disabled" else "") + ": darla de baja o renombrarla.",
                    "https://my.zadarma.com/mypbx/")
# Personas de baja que todavía aparecen en el panel o en ClickUp
for p in PERSONAS:
    if p.get("estado") == "baja":
        en_cu = any(persona_por_nombre(n) == p["id"] for n in CU_MIEMBROS)
        en_desk = next((s for n, s in AGENTES_DESK.items() if persona_por_nombre(n) == p["id"]), None)
        en_panel = any(persona_por_nombre(x.get("nombre")) == p["id"] for x in (D.get("v7", {}).get("personas") or []))
        if en_panel and not en_cu:
            fila_acceso(p["nombre"], "Panel de operaciones", "en la lista de horas", "Ya no es miembro de ClickUp, pero el panel la sigue contando en «horas» (0 h): quitarla de la lista.")
        if not en_cu and not (en_desk == "ACTIVE"):
            ACCESOS.append({"id": uid("accok", p["id"]), "persona": p["nombre"], "persona_ref": p["id"], "estado_app": "baja", "herramienta": "ClickUp y Desk",
                            "estado_herramienta": "sin acceso", "que_hacer": None, "ok": True, "persona_id": p["id"]})

# ------------------------------------------------------------------ traspasos de cartera
TRASPASOS = []
for t in RASTRO.get("traspasos", []):
    cid = t["cliente_id"]
    hoy_app = account_de(cid)
    ag = por_cli_ag.get(cid)
    ag_top = ag.most_common(1)[0][0] if ag else None
    duda = next((a.get("duda") for a in ASIG if a["cliente_id"] == cid and a["silla"] == "account" and a.get("duda")), None)
    fecha = t.get("fecha")
    TRASPASOS.append({
        "id": uid("tras", cid, t["de"], t["a"]), "cliente_id": cid, "cliente": C_ID.get(cid, {}).get("nombre", cid), "silla": t["silla"],
        "de_id": t["de"], "de": nombre_p(t["de"]) or t["de"], "a_id": t["a"], "a": nombre_p(t["a"]) or t["a"],
        "fecha": fecha, "abierto": t.get("abierto"), "revision": (dt.date.fromisoformat(fecha) + dt.timedelta(days=14)).isoformat() if fecha else None,
        "prueba": t.get("prueba"), "fuente": t.get("fuente"),
        "estado_app": "hecho" if hoy_app == t["a"] else f"sigue con {nombre_p(hoy_app) or hoy_app or 'nadie'}",
        "estado_desk": None if not ag_top else ("hecho" if persona_por_nombre(ag_top) == t["a"] else f"tickets con {ag_top}"),
        "estado_crm": ("pendiente: " + duda) if duda and "CRM" in duda else "sin dato",
    })

# ------------------------------------------------------------------ quién vio primero
VISTOS = []
for cid, hist in HIST.items():
    marcas = [e for e in hist if e["quien"] in ("mili", "tomas", "constanza") and e["paso"] != "respuesta"]
    if not marcas:
        continue
    p = marcas[0]
    m = next((e for e in marcas if e["quien"] == "mili"), None)
    t = next((e for e in marcas if e["quien"] == "tomas"), None)
    VISTOS.append({"cliente_id": cid, "persona_id": "mili", "cliente": C_ID.get(cid, {}).get("nombre", cid), "primero": p["quien"], "primero_fecha": p["fecha"], "primero_enlace": p["enlace"],
                   "mili_fecha": m["fecha"] if m else None, "tomas_fecha": t["fecha"] if t else None,
                   "avisos_mili": sum(1 for e in marcas if e["quien"] == "mili"), "en_rojo_hoy": bool(rojas_cli.get(cid))})
for cid in (RASTRO.get("sin_aviso_escrito") or {}).get("clientes", []):
    if not any(v["cliente_id"] == cid for v in VISTOS):
        VISTOS.append({"cliente_id": cid, "persona_id": "mili", "cliente": C_ID.get(cid, {}).get("nombre", cid), "primero": None, "primero_fecha": None, "primero_enlace": None,
                       "mili_fecha": None, "tomas_fecha": None, "avisos_mili": 0, "en_rojo_hoy": bool(rojas_cli.get(cid))})

# ------------------------------------------------------------------ mapa de calor y mapa de control (panel v27)
REGLAS_CALOR = [
    {"k": "resp", "t": "Sin responder", "s": "+48 h", "tipos": ["Sin responder"]},
    {"k": "sem", "t": "Semáforo", "s": "sin rellenar", "tipos": ["Semáforo sin rellenar"]},
    {"k": "rojo", "t": "Semáforo", "s": "en rojo", "tipos": ["Semáforo en rojo"]},
    {"k": "reu", "t": "Sin reunión", "s": "en septiembre", "tipos": ["Sin reunión en septiembre"]},
    {"k": "mail", "t": "Sin correo", "s": "esta semana", "tipos": ["Sin correo esta semana"]},
    {"k": "rev", "t": "Revisión", "s": "tareas +48 h", "tipos": ["Revisión del account >48 h"], "rojo_desde": 6},
    {"k": "new", "t": "Nuevos", "s": "fuera de plazo", "tipos": ["Cliente nuevo fuera de plazo", "Cliente nuevo sin onboarding"]},
]
panel_cli = D.get("clientes", [])
CALOR = []
for a in D.get("accounts", []):
    sin = a["nombre"].startswith("sin ")
    pid = None if sin else persona_por_nombre(a["nombre"])
    rojo = sum(1 for c in panel_cli if c.get("account") == a["nombre"] and c.get("semaforo") in ("crítico", "grave"))
    CALOR.append({"persona_id": pid or "mili", "persona_ref": pid, "nombre": nombre_p(pid) if pid else a["nombre"], "nombre_completo": a["nombre"],
                  "proyectos": a.get("proyectos"), "alarmas_rojas": a.get("rojas"),
                  "valores": {"resp": a.get("pend48"), "sem": a.get("semaforo_sin"), "rojo": rojo, "reu": a.get("sin_reunion"),
                              "mail": a.get("sin_correo"), "rev": a.get("revision48"), "new": a.get("nuevos_tarde")}})
V7 = D.get("v7", {})
PLAN = V7.get("planificacion") or {}
CONTROL = []
for x in V7.get("control", []):
    pid = persona_por_nombre(x["persona"])
    k = next((n for n in PLAN if not n.startswith("_") and n.split(" ")[0].lower() == x["persona"].split(" ")[0].lower()), None)
    rompe = PLAN[k]["semana"]["rompen"] if k and isinstance(PLAN.get(k), dict) and PLAN[k].get("semana") else None
    CONTROL.append({"persona_id": pid or "mili", "persona_ref": pid, "nombre": nombre_p(pid) if pid else x["persona"], "clientes": x.get("clientes"),
                    "imputa": x.get("imputa"), "revisa": x.get("revisa"), "llama": x.get("llama"), "contesta": x.get("contesta"),
                    "reune": x.get("reune"), "abandonados": x.get("abandonados") or [], "planifica": rompe, "reuniones_tarde": x.get("reuniones_tarde")})

# R13 · contesta / revisa / se reúne con las DEFINICIONES ÚNICAS (las mismas que Mi día, Bandeja, Producción y Reuniones):
#   contesta = Bandeja por cliente (data/bandeja/por_cliente.json) sobre los clientes que la persona ve (cartera del servidor);
#   revisa   = Producción: revisiones[] con revisa == "account" y account_id == persona (mas48 = más de 48 h);
#   reune    = Reuniones: clientes[] del account (o de su cartera), sin exentos ni «no aplica»; «sin reunión» = la verdad única
#              (verdad/clientes → sin_reunion_mes_pasado) y, si falta, estado == "sin_reunion".
# El panel v27 se queda solo para imputa, llama, contacto semanal, abandonados y planifica.
import permisos as P  # noqa: E402
BJ_CLI = {c["cliente_id"]: c for c in (leer(DATA / "bandeja" / "por_cliente.json", {}) or {}).get("clientes", [])}
PROD = leer(DATA / "produccion" / "produccion.json", {}) or {}
REU = leer(DATA / "reuniones" / "reuniones.json", {}) or {}
VERDAD_CLI = {c["cliente_id"]: c for c in (leer(DATA / "verdad" / "clientes.json", {}) or {}).get("clientes", [])}
CRUDO_P = {"asignaciones": ASIG, "personas": PERSONAS}
P_ID = {p["id"]: p for p in PERSONAS}


def control_unico(pid):
    p = P_ID.get(pid)
    cartera = set(P.contexto(p, CRUDO_P)["cartera_ids"]) if p else set()
    cli_bj = [BJ_CLI[c] for c in sorted(cartera) if c in BJ_CLI]
    contesta = {"mas48": sum(int(c.get("mas_48") or 0) for c in cli_bj), "correos": sum(int(c.get("sin_contestar") or 0) for c in cli_bj),
                "clientes_mas48": sum(1 for c in cli_bj if c.get("mas_48")), "fuente": "bandeja/por_cliente"}
    rev = [x for x in PROD.get("revisiones", []) if x.get("account_id") == pid and x.get("revisa") == "account"]
    revisa = {"mas48": sum(1 for x in rev if x.get("mas48")), "total": len(rev), "fuente": "produccion/revisiones"}
    reu = [c for c in REU.get("clientes", []) if (c.get("account_id") == pid or c.get("cliente_id") in cartera) and c.get("estado") not in ("exento", "no_aplica")]

    def sin_r(c):
        v = VERDAD_CLI.get(c["cliente_id"])
        return v["sin_reunion_mes_pasado"] if v and v.get("sin_reunion_mes_pasado") is not None else c.get("estado") == "sin_reunion"
    return contesta, revisa, {"sin_reunion": sum(1 for c in reu if sin_r(c)), "clientes": len(reu), "fuente": "reuniones + verdad/clientes"}


for x in CONTROL:
    if not x.get("persona_ref"):
        continue
    contesta, revisa, reune = control_unico(x["persona_ref"])
    x["panel_v27"] = {"contesta": x.get("contesta"), "revisa": x.get("revisa"), "reune": x.get("reune")}   # lo que decía el panel, por si se compara
    x["contesta"], x["revisa"] = contesta, revisa
    x["reune"] = {**reune, "sin_correo_sem": (x.get("reune") or {}).get("sin_correo_sem")}
CONTROL_REGLA = {
    "contesta": "Correos sin contestar de más de 48 h de tus clientes, con la regla de la Bandeja (sin automáticos ni ruido).",
    "revisa": "Revisiones del account de más de 48 h, con la regla de Producción.",
    "reune": f"Clientes sin la reunión de {REU.get('_meta', {}).get('mes_pasado', 'el mes pasado')}, con la regla de Reuniones y la verdad única.",
    "mes_pasado": REU.get("_meta", {}).get("mes_pasado"),
}

# ------------------------------------------------------------------ salida
# Un cliente en rojo por «Sin responder» que además tiene la detección de Desk > 48 h: una sola incidencia
# (la de la alarma, que trae la historia), con los tickets de Desk dentro.
por_cli_desk = {i["cliente_id"]: i for i in INCIDENCIAS if i["regla"] == "desk_48"}
quitar = set()
for i in INCIDENCIAS:
    if i["origen"] == "alarma" and "Sin responder" in (i.get("numeros") or {}).get("motivos", []) and i["cliente_id"] in por_cli_desk:
        d48 = por_cli_desk[i["cliente_id"]]
        i["tickets"] = d48.get("tickets")
        i["numeros"]["correos_48h"] = d48["numeros"]["correos"]
        quitar.add(d48["id"])
INCIDENCIAS[:] = [i for i in INCIDENCIAS if i["id"] not in quitar]
INCIDENCIAS.sort(key=lambda i: (i["gravedad"] != "rojo", i.get("detectada") or "9999"))
salida = {
    "formato": 1, "generado": AHORA.strftime("%Y-%m-%d %H:%M"), "hoy": HOY.isoformat(), "fuentes": FUENTES,
    "causas": {
        "donde": {"publicidad": "Publicidad", "despacho": "Despacho (el cliente)", "integracion": "Integración", "produccion": "Producción", "contacto_cliente": "Contacto con el cliente"},
        "por_que": {"sistema": "Sistema", "configuracion": "Configuración", "ejecucion": "Ejecución de una persona", "gestion_operaciones": "Gestión de Operaciones"},
        "regla": "R13 del plan v2 (auditoría C-04, D-37): la marca quien escala y Tomás la puede cambiar. Sin prueba de aviso, cuenta como gestión de Operaciones (idea D13).",
    },
    "relojes": {"vuelve_arriba_h": 48, "escalado_coti_h": 24, "escalado_tomas_h": 48},
    "no_medible": [
        "Ticket en un departamento equivocado: la llave solo lee 1 de los 30 departamentos de Desk (los demás dan «sin permiso»).",
        "Desvíos, horarios y buzones de Zadarma: la API no los da. Van en la revisión mensual a mano.",
        "Lo que se habla por WhatsApp o desde el correo personal no deja prueba en la app.",
    ],
    "revision_mensual_zadarma": [
        "Cada extensión tiene nombre de una persona activa del equipo",
        "Ninguna extensión de alguien que ya no está",
        "El número principal tiene horario y buzón fuera de horario",
        "Ningún desvío a un número personal o desconocido",
        "Las entrantes sin respuesta del mes tienen destino",
        "Grabación activada en las extensiones de clientes",
    ],
    "incidencias": INCIDENCIAS, "incongruencias": INCONG, "accesos": ACCESOS, "traspasos": TRASPASOS, "vistos": VISTOS,
    "extensiones": [{k: v for k, v in e.items() if k != "persona_id_ext"} | {"persona_ref": e["persona_id_ext"]} for e in EXTENSIONES],
    "reglas_calor": REGLAS_CALOR, "mapa_calor": CALOR, "control": CONTROL, "control_regla": CONTROL_REGLA,
}

sys.path.insert(0, str(APP))
import escaner_secretos as E  # noqa: E402
SALIDA.parent.mkdir(parents=True, exist_ok=True)
tmp = SALIDA.with_suffix(".tmp.json")
tmp.write_text(json.dumps(salida, ensure_ascii=False, indent=1))
hall = E.escanear_fichero(tmp)
if hall:
    print("La puerta de secretos encuentra algo; no se escribe:", hall[:5])
    tmp.unlink()
    sys.exit(1)
tmp.replace(SALIDA)
ESTADO.write_text(json.dumps({"actualizado": AHORA.isoformat(timespec="minutes"), "primera_vez": PRIMERA}, ensure_ascii=False, indent=1))
print(f"incidencias {len(INCIDENCIAS)} · incongruencias {len(INCONG)} · accesos {len(ACCESOS)} · traspasos {len(TRASPASOS)} · vistos {len(VISTOS)} · calor {len(CALOR)} · control {len(CONTROL)}")
print(Counter(i["regla"] for i in INCIDENCIAS).most_common())
