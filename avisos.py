#!/usr/bin/env python3
"""
avisos.py · carril N15 «Canales de avisos, grupos y alertas automáticas» (2-oct-2026).

Encargo de Tomás: «en ClickUp tenemos los canales de avisos y demás, grupos, alertas automáticas: que eso también exista».
Se engancha a servir.py como ia.py y altas_personas.py (envuelve _api_get y api_post). Sin este fichero, nada cambia.

Qué hay:
  1. Canales de AVISOS por departamento (#avisos-web … #avisos-dirección) que se llenan solos con el motor de alertas
     (N4, data/alertas/alertas.json) y con eventos del sistema: cliente firmado (data/nuevos), alta de persona, fuente
     caída (data/fuentes.json), informe enviado (data/informes) y, en #general, cumpleaños y aniversarios. Cada aviso
     lleva dueño, plazo y mención automática al dueño; si pasa el plazo sin «Lo tengo», un aviso en su hilo menciona a quien
     sube. «Lo tengo» y «Resuelta» escriben la MISMA acción que la pantalla de Alertas (tabla acciones, módulo «alertas»):
     la alerta cambia de verdad, para el escalado y la comprueba el dato siguiente.
  2. GRUPOS de la app: uno por equipo (#equipo-<departamento>), uno por cliente (solo quien lo lleva y quien puede abrir el
     cliente) y grupos propios. Lo escrito queda en la base de la app (canal_mensajes, imborrable) y NUNCA sale a ClickUp
     ni a ningún sitio. El espejo de ClickUp se lee aparte (/api/canales/clickup), solo lectura y por páginas de 50.
  3. CAMPANA: no leídos, menciones, avisos para ti y el resumen diario a la hora de cada persona (zona de personas.json).
     Preferencias: canales silenciados y hora del resumen.
  4. PERMISOS: cada uno ve los canales de su departamento y los que le añaden; un aviso solo llega a quien tiene esa alerta
     en su fichero de alertas (las suyas; las del departamento si es jefe; Mili y Tomás, todas); lo de un cliente, solo a
     quien puede abrir ese cliente; importes fuera a quien no los ve (P.sin_importes); contraseñas tapadas (tapar() del
     generador del chat), sin correos ni teléfonos, y los sueldos no se escriben. «Ver como»: lo que ven LAS DOS personas y
     nada se escribe. Cada mensaje escrito deja su fila en el rastro.

Rutas:  GET  /api/canales · /api/canales/canal?id=&antes= · /api/canales/campana · /api/canales/buscar?q= · /api/canales/clickup?canal=&antes=
        POST /api/canales/mensaje · /api/canales/leido · /api/canales/estado · /api/canales/preferencias · /api/canales/grupo ·
             /api/canales/miembro · /api/canales/campana_vista
Pruebas: RO_AVISOS_AHORA=«AAAA-MM-DD HH:MM» (hora de Madrid) simula el reloj para el resumen diario.
"""
import json
import os
import re
import sys
import threading
import time
import traceback
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

AQUI = Path(__file__).resolve().parent
DATA = AQUI / "data"
sys.path.insert(0, str(AQUI / "fuentes_chat_equipo"))
from tapado import limpiar, tapar  # noqa: E402

S = P = None                     # servir y permisos, al enganchar
MADRID = ZoneInfo("Europe/Madrid")
UTC = ZoneInfo("UTC")
POR_PAGINA = 50
HORA_RESUMEN = "08:30"

DEPARTAMENTOS = [   # orden del menú: el de alertas (N4)
    ("web", "Web", "mundo_web"), ("seo", "SEO", "globe"), ("crm", "CRM", "base"), ("publicidad", "Publicidad", "megafono"),
    ("redes", "Redes", "heart"), ("accounts", "Accounts", "cli"), ("altas", "Altas", "rocket"),
    ("administracion", "Administración", "euro"), ("rrhh", "RRHH", "eq"), ("direccion", "Dirección", "flag"),
]
NOMBRE_DEP = {d: n for d, n, _ in DEPARTAMENTOS}
ICONO_DEP = {d: i for d, _, i in DEPARTAMENTOS}
# Puesto → departamentos cuyos canales ve (avisos y equipo). Dirección y operaciones, todos.
DEP_DE_PUESTO = {
    "direccion": ["direccion"], "finanzas_direccion": ["direccion"], "proyectos": ["direccion"],
    "operaciones": ["direccion", "accounts", "altas"], "administracion": ["administracion"], "rrhh": ["rrhh"],
    "account": ["accounts"], "tecnico_altas": ["altas"], "trafficker": ["publicidad"], "jefa_publicidad": ["publicidad"],
    "especialista_ghl": ["crm"], "jefa_crm": ["crm"], "outreach": ["crm"], "jefa_seo": ["seo", "web"], "seo": ["seo"],
    "ficha_google": ["seo"], "web": ["web"], "redes": ["redes"], "produccion": ["redes"],
}
TODOS_LOS_AVISOS = {"direccion", "operaciones"}
QUIEN_ANADE = {"direccion", "operaciones"}          # además del jefe del departamento
ESTADOS_ABIERTOS = {"nueva", "vista", "reabierta"}
DE_ACCION = {"alerta_vista": "vista", "alerta_lo_tengo": "lo_tengo", "alerta_resuelta": "resuelta",
             "alerta_no_aplica": "no_aplica", "alerta_reabrir": "nueva"}
RX_SUELDO = re.compile(r"(?i)\b(sueld\w*|salari\w*|n[oó]min\w*|bruto anual|neto mensual|retribuci\w*)\b[^\n]{0,60}?\d")
# R16 (N2): el filtro de sueldos ya no se salta con otras palabras. Fuerte = palabra de sueldo y una cifra (en número o en
# letra) cerca; «1.800 € brutos» al revés; y, débil, el nombre de una persona del equipo con un importe y «al mes»,
# «subida», «paga»… (si el mensaje no habla de un cliente, que entonces es su cuota).
_CIFRA = r"(?:\d|\b(?:mil|cien|ciento|\w+cient[oa]s|veinte|treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa)\b)"
RX_SUELDO_FUERTE = re.compile(r"(?i)\b(sueld\w*|salari\w*|n[oó]min\w*|retribu\w*|brut[oa]s?|net[oa]s?|finiquit\w*|pagas?\s+extras?|"
                              r"cobra|cobrar|cobrará|cobraría|cobraba|cobran|cobrando|cobre|cobren|subida\s+salarial|plus\s+de)\b[^\n]{0,60}?" + _CIFRA)
RX_SUELDO_DETRAS = re.compile(r"(?i)\d[\d.,]*\s*(?:k\s*)?(?:€|euros?|eur)\s*(?:/\s*mes\s*)?(?:brut|net)\w*")
RX_SUELDO_DEBIL = re.compile(r"(?i)(/\s*mes|al mes|mensual\w*|al año|anual\w*|subida|aumento|paga\b|pagar[aá]?\b|gana\b|ganar[aá]?\b)")
RX_HORA = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

TABLAS_SQL = """
CREATE TABLE IF NOT EXISTS canal_grupos (
  id TEXT PRIMARY KEY, nombre TEXT NOT NULL, cliente_id TEXT, creado_por TEXT NOT NULL,
  creado TEXT NOT NULL DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS canal_miembros (
  n INTEGER PRIMARY KEY AUTOINCREMENT, canal_id TEXT NOT NULL, persona_id TEXT NOT NULL,
  operacion TEXT NOT NULL CHECK (operacion IN ('anadir','quitar')), quien TEXT NOT NULL,
  hora TEXT NOT NULL DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS canal_mensajes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, canal_id TEXT NOT NULL,
  tipo TEXT NOT NULL CHECK (tipo IN ('mensaje','aviso','evento')), quien TEXT, texto TEXT NOT NULL, hilo_de INTEGER,
  menciones TEXT, clave TEXT UNIQUE, alerta_id TEXT, cliente_id TEXT, dueno_id TEXT, vence TEXT, ver TEXT, datos TEXT,
  creado TEXT NOT NULL DEFAULT (datetime('now')));
CREATE INDEX IF NOT EXISTS canal_mensajes_canal ON canal_mensajes (canal_id, id);
CREATE TABLE IF NOT EXISTS canal_leidos (
  persona_id TEXT NOT NULL, canal_id TEXT NOT NULL, ultimo_id INTEGER NOT NULL, hora TEXT NOT NULL,
  PRIMARY KEY (persona_id, canal_id));
CREATE TABLE IF NOT EXISTS canal_preferencias (
  persona_id TEXT PRIMARY KEY, silenciados TEXT, hora_resumen TEXT, actualizado TEXT);
CREATE TABLE IF NOT EXISTS canal_resumenes (
  persona_id TEXT NOT NULL, dia TEXT NOT NULL, titulo TEXT, texto TEXT, datos TEXT,
  creado TEXT NOT NULL DEFAULT (datetime('now')), PRIMARY KEY (persona_id, dia));
CREATE TABLE IF NOT EXISTS canal_campana (
  persona_id TEXT PRIMARY KEY, hasta_id INTEGER NOT NULL DEFAULT 0, resumen_visto TEXT, hora TEXT);
CREATE TRIGGER IF NOT EXISTS canal_mensajes_sin_update BEFORE UPDATE ON canal_mensajes BEGIN SELECT RAISE(ABORT, 'Un mensaje no se cambia'); END;
CREATE TRIGGER IF NOT EXISTS canal_mensajes_sin_delete BEFORE DELETE ON canal_mensajes BEGIN SELECT RAISE(ABORT, 'Un mensaje no se borra'); END;
CREATE TRIGGER IF NOT EXISTS canal_miembros_sin_update BEFORE UPDATE ON canal_miembros BEGIN SELECT RAISE(ABORT, 'El historial de miembros no se cambia'); END;
CREATE TRIGGER IF NOT EXISTS canal_miembros_sin_delete BEFORE DELETE ON canal_miembros BEGIN SELECT RAISE(ABORT, 'El historial de miembros no se borra'); END;
CREATE TRIGGER IF NOT EXISTS canal_grupos_sin_delete BEFORE DELETE ON canal_grupos BEGIN SELECT RAISE(ABORT, 'Un grupo no se borra'); END;
CREATE TRIGGER IF NOT EXISTS canal_resumenes_sin_delete BEFORE DELETE ON canal_resumenes BEGIN SELECT RAISE(ABORT, 'Un resumen no se borra'); END;
"""


# =================================================================== reloj y utilidades
def ahora_local():
    """Hora de Madrid (naive). RO_AVISOS_AHORA la fija para pruebas."""
    v = os.environ.get("RO_AVISOS_AHORA")
    if v:
        return datetime.fromisoformat(v)
    return datetime.now(MADRID).replace(tzinfo=None, microsecond=0)


def ahora_utc_txt():
    return ahora_local().replace(tzinfo=MADRID).astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")


def utc_a_local(txt, zona=MADRID):
    try:
        return datetime.fromisoformat(str(txt)[:19]).replace(tzinfo=UTC).astimezone(zona).replace(tzinfo=None)
    except ValueError:
        return None


def fecha_local(s):
    """«2026-10-02 15:43», «2026-10-02», «2026-10-02T07:16:00Z» → datetime de Madrid (naive) o None."""
    if not s:
        return None
    s = str(s).strip()
    try:
        if s.endswith("Z") or "+" in s[10:]:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(MADRID).replace(tzinfo=None)
        return datetime.fromisoformat(s.replace("T", " ")[:16] if len(s) > 10 else s)
    except ValueError:
        return None


def norm(t):
    return "".join(c for c in unicodedata.normalize("NFD", str(t or "").lower()) if unicodedata.category(c) != "Mn")


_CACHE = {}


def _nombres_equipo():
    out = set()
    for p in (S.E.crudo.get("personas") if S else []) or []:
        for forma in (p.get("alias"), (p.get("nombre") or "").split(" ")[0]):
            n = norm(forma or "")
            if len(n) >= 3:
                out.add(n)
    return out


def _clientes_nombrados(t):
    tn = norm(t)
    return any(len(norm(c.get("nombre") or "")) >= 4 and re.search(r"\b" + re.escape(norm(c["nombre"])) + r"\b", tn)
               for c in (S.E.crudo.get("clientes") if S else []) or [])


def habla_de_sueldo(t):
    """R16 (N2): ¿este texto dice lo que cobra alguien? Mejor rechazar de más que de menos."""
    t = str(t or "")
    if RX_SUELDO.search(t) or RX_SUELDO_FUERTE.search(t) or RX_SUELDO_DETRAS.search(t):
        return True
    if not (P and P.RE_IMPORTE.search(t)) or not RX_SUELDO_DEBIL.search(t):
        return False
    tn = norm(t)
    return any(re.search(r"\b" + re.escape(n) + r"\b", tn) for n in _nombres_equipo()) and not _clientes_nombrados(t)


def ve_sueldos(p):
    return bool(P and P.ver(p, {"tipo": "sueldos"}, P.contexto(p, S.E.crudo))["ok"])


def texto_para(V, texto, cliente_id):
    """Lo que ve V de un texto guardado: contraseñas tapadas, importes que no ve fuera y, si habla de lo que cobra
    alguien (mensajes de antes del filtro), sin cifras para quien no ve sueldos."""
    sueldo = habla_de_sueldo(texto)
    if sueldo and V.sueldos:                 # dirección y RRHH: lo que cobra alguien, con su cifra
        return tapar(texto)
    t = P.sin_importes(tapar(texto), V.quitar(cliente_id))
    if sueldo:
        t = P.sin_importes(t)
        t = re.sub(r"(?i)\b(?:(?:mil|cien|ciento|\w+cient[oa]s|veinti\w+|treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa|y|un|dos|tres|cuatro|cinco|seis|siete|ocho|nueve)\s+)+(?:euros?)?", "[cifra] ", t)
        t = re.sub(r"\d[\d.,]*", "[cifra]", t)
    return t


def leer_json(ruta, defecto=None):
    """JSON con caché por fecha de cambio (los ficheros de datos se regeneran en caliente)."""
    try:
        mt = ruta.stat().st_mtime
    except OSError:
        return defecto
    c = _CACHE.get(str(ruta))
    if c and c[0] == mt:
        return c[1]
    try:
        doc = json.loads(ruta.read_text())
    except (OSError, ValueError):
        return c[1] if c else defecto
    _CACHE[str(ruta)] = (mt, doc)
    return doc


def personas():
    return S.E.crudo["personas"]


def persona(pid):
    return S.E.persona(pid)


def activas():
    return [p for p in personas() if p.get("activo") and (p.get("estado") or "activo") == "activo"]


def corto(pid):
    p = persona(pid) if pid else None
    return (p.get("alias") or p.get("nombre")) if p else "alguien"


def nombre_cliente(cid):
    c = next((c for c in S.E.crudo["clientes"] if c["id"] == cid), None)
    return c["nombre"] if c else cid


def departamentos_json():
    ruta = Path(os.environ.get("RO_DEPARTAMENTOS") or DATA / "departamentos.json")
    return (leer_json(ruta, {}) or {}).get("departamentos") or {}


# =================================================================== quién está en qué canal
def deps_de(p):
    """Departamentos de una persona: por puesto, más los que dirige o de los que es dueña fija (departamentos.json)."""
    pu = set(p.get("puestos") or [])
    if pu & TODOS_LOS_AVISOS:
        return [d for d, _, _ in DEPARTAMENTOS]
    out = {d for x in pu for d in DEP_DE_PUESTO.get(x, [])}
    for d, conf in departamentos_json().items():
        if p["id"] in (conf.get("jefe"), conf.get("dueno_fijo")):
            out.add(d)
    return [d for d, _, _ in DEPARTAMENTOS if d in out]


def puede_anadir(p, c):
    """R16 (N3): quién añade gente a un canal. RRHH y Dirección (equipo y avisos): solo Tomás (dirección) y, en RRHH,
    Cecilia (RRHH). El resto de equipos y avisos: su jefe, operaciones o dirección. Clientes y grupos propios: sus
    miembros (con la comprobación de cliente aparte)."""
    pu = set(p.get("puestos") or [])
    dep = c.get("departamento")
    if c["tipo"] in ("equipo", "avisos"):
        if dep == "direccion":
            return "direccion" in pu
        if dep == "rrhh":
            return bool(pu & {"direccion", "rrhh"})
        return es_jefe_de(p, dep)
    return c["tipo"] in ("cliente", "propio")


def es_jefe_de(p, dep):
    conf = departamentos_json().get(dep) or {}
    return p["id"] == conf.get("jefe") or bool(set(p.get("puestos") or []) & QUIEN_ANADE)


def anadidos(con):
    """{canal_id: set(personas)} según el historial de miembros (añadir / quitar, en orden)."""
    out = {}
    for r in con.execute("SELECT canal_id, persona_id, operacion FROM canal_miembros ORDER BY n"):
        s = out.setdefault(r["canal_id"], set())
        (s.add if r["operacion"] == "anadir" else s.discard)(r["persona_id"])
    return out


def grupos_propios(con):
    return {r["id"]: dict(r) for r in con.execute("SELECT * FROM canal_grupos ORDER BY creado")}


def puede_abrir_cliente(p, cid):
    cp = P.contexto(p, S.E.crudo)
    return P.ver(p, {"tipo": "cliente_detalle", "cliente_id": cid}, cp)["ok"]


def canales_de(p, con, extra=None):
    """Canales de una persona (sin «ver como»): {id: meta}. extra = (anadidos, grupos, clientes_con_mensajes) ya leídos."""
    ana, grupos, con_msgs = extra or (anadidos(con), grupos_propios(con), clientes_con_mensajes(con))
    pid = p["id"]
    deps = deps_de(p)
    out = {"general": {"id": "general", "tipo": "general", "nombre": "general", "por_que": "Todo el equipo",
                       "descripcion": "Todo el equipo: bienvenidas, clientes nuevos, cumpleaños y aniversarios"}}
    for d, nombre, _ in DEPARTAMENTOS:
        for tipo, cid in (("avisos", f"avisos-{d}"), ("equipo", f"equipo-{d}")):
            por = "Tu departamento" if d in deps else ("Te han añadido" if pid in ana.get(cid, ()) else None)
            if not por:
                continue
            out[cid] = {"id": cid, "tipo": tipo, "departamento": d, "nombre": f"{'avisos' if tipo == 'avisos' else 'equipo'}-{norm(nombre)}",
                        "titulo": f"#{tipo}-{nombre.lower()}" if tipo == "avisos" else f"Equipo de {nombre}", "por_que": por,
                        "descripcion": (f"Avisos automáticos de {nombre}: alertas con dueño y plazo, y eventos del sistema"
                                        if tipo == "avisos" else f"Grupo del equipo de {nombre}: se escribe aquí y queda en la app")}
    cp = P.contexto(p, S.E.crudo)
    cartera = cp.get("cartera_ids") or set()
    todo = bool(set(p.get("puestos") or []) & TODOS_LOS_AVISOS)
    for c in S.E.crudo["clientes"]:
        cid = c["id"]
        gid = f"cliente-{cid}"
        dentro = cid in cartera or pid in ana.get(gid, ()) or todo
        if dentro and P.ver(p, {"tipo": "cliente_detalle", "cliente_id": cid}, cp)["ok"]:
            out[gid] = {"id": gid, "tipo": "cliente", "cliente_id": cid, "nombre": c["nombre"], "titulo": c["nombre"],
                        "por_que": "Llevas este cliente" if cid in cartera else ("Te han añadido" if pid in ana.get(gid, ()) else "Dirección"),
                        "con_mensajes": cid in con_msgs,
                        "descripcion": f"Grupo del cliente {c['nombre']}: solo quien lo lleva y quien puede abrir el cliente"}
    for gid, g in grupos.items():
        if pid in ana.get(gid, ()):
            if g.get("cliente_id") and not P.ver(p, {"tipo": "cliente_detalle", "cliente_id": g["cliente_id"]}, cp)["ok"]:
                continue
            out[gid] = {"id": gid, "tipo": "propio", "cliente_id": g.get("cliente_id"), "nombre": g["nombre"], "titulo": g["nombre"],
                        "por_que": "Te han añadido" if g["creado_por"] != pid else "Lo creaste tú",
                        "descripcion": f"Grupo creado por {corto(g['creado_por'])}"}
    for c in out.values():
        c.setdefault("titulo", f"#{c['nombre']}")
    return out


def clientes_con_mensajes(con):
    return {r["canal_id"][8:] for r in con.execute("SELECT DISTINCT canal_id FROM canal_mensajes WHERE canal_id LIKE 'cliente-%'")}


def miembros_de(canal_id, con):
    extra = (anadidos(con), grupos_propios(con), clientes_con_mensajes(con))
    return [p["id"] for p in activas() if canal_id in canales_de(p, con, extra)]


# =================================================================== lo que ve quien mira (con «ver como»)
def ids_alertas(pid):
    """Las alertas de una persona: las de su fichero de N4 (las suyas; su departamento si es jefe; Mili y Tomás, todas)."""
    doc = leer_json(DATA / "alertas" / f"p_{pid}.json", {}) or {}
    return {a["id"] for a in doc.get("alertas") or []}


def alertas_por_id():
    doc = leer_json(DATA / "alertas" / "alertas.json", {}) or {}
    return {a["id"]: a for a in doc.get("alertas") or []}, doc.get("generado")


class Vista:
    """Lo que puede ver «persona» (y, en «ver como», también «real»): canales, alertas, clientes e importes."""

    def __init__(self, persona_, real, con):
        self.p, self.real, self.con = persona_, real, con
        self.como = persona_["id"] != real["id"]
        self.cp = P.contexto(persona_, S.E.crudo)
        extra = (anadidos(con), grupos_propios(con), clientes_con_mensajes(con))
        self.canales = canales_de(persona_, con, extra)
        self.alertas = ids_alertas(persona_["id"])
        if self.como:   # lo que ven LAS DOS
            suyos = canales_de(real, con, extra)
            self.canales = {k: v for k, v in self.canales.items() if k in suyos}
            self.alertas &= ids_alertas(real["id"])
        self._cli, self._quitar = {}, {}
        self.todas, self.generado = alertas_por_id()
        self.estados = estados_alertas(con, self.generado)
        self.pref = preferencias(persona_["id"], con)
        self.sueldos = ve_sueldos(persona_) and (not self.como or ve_sueldos(real))

    def cliente(self, cid):
        if cid not in self._cli:
            self._cli[cid] = P.ver(self.p, {"tipo": "cliente_detalle", "cliente_id": cid}, self.cp)["ok"]
        return self._cli[cid]

    def quitar(self, cid):
        """Qué importes no ve en un texto (de un cliente o general)."""
        if cid not in self._quitar:
            if cid:
                vc = P.ver(self.p, {"tipo": "cuota", "cliente_id": cid}, self.cp)["ok"]
                vi = P.ver(self.p, {"tipo": "inversion", "cliente_id": cid}, self.cp)["ok"]
            else:
                pu = P.puestos_de(self.p)
                vc = bool(pu & {"direccion", "operaciones", "proyectos", "administracion", "finanzas_direccion"})
                vi = bool(pu & {"direccion", "operaciones", "jefa_publicidad"})
            self._quitar[cid] = P.importes_a_quitar(vc, vi)
        return self._quitar[cid]

    def ve_fila(self, r, padres=None):
        """¿Ve este mensaje? El canal ya está mirado. Las respuestas heredan lo del mensaje de arriba."""
        if r["hilo_de"]:
            padre = (padres or {}).get(r["hilo_de"])
            if padre is None:
                padre = self.con.execute("SELECT * FROM canal_mensajes WHERE id=?", (r["hilo_de"],)).fetchone()
            return bool(padre) and padre["canal_id"] == r["canal_id"] and self.ve_fila(padre)
        if r["cliente_id"] and not self.cliente(r["cliente_id"]):
            return False
        ver = json.loads(r["ver"] or "{}")
        if "alerta" in ver:
            return ver["alerta"] in self.alertas
        if "puestos" in ver:
            return bool(P.puestos_de(self.p) & set(ver["puestos"]))
        return True


def estados_alertas(con, generado):
    """Último estado de cada alerta en la cola (las mismas acciones que la pantalla de Alertas)."""
    out = {}
    gen = fecha_local(generado)
    for r in con.execute("SELECT objeto, tipo, quien, creada, texto FROM acciones WHERE modulo='alertas' ORDER BY id"):
        if r["tipo"] not in DE_ACCION:
            continue
        hora = utc_a_local(r["creada"])
        out[r["objeto"]] = {"estado": DE_ACCION[r["tipo"]], "quien": r["quien"], "hora": hora.strftime("%Y-%m-%d %H:%M") if hora else None,
                            "vivo": bool(hora and (not gen or hora > gen))}
    return out


def preferencias(pid, con):
    r = con.execute("SELECT * FROM canal_preferencias WHERE persona_id=?", (pid,)).fetchone()
    p = persona(pid) or {}
    return {"silenciados": json.loads(r["silenciados"] or "[]") if r else [],
            "hora_resumen": (r["hora_resumen"] if r and r["hora_resumen"] else HORA_RESUMEN), "zona": p.get("zona") or "Europe/Madrid"}


# =================================================================== mensajes hacia fuera
def aviso_de(r, V):
    """La tarjeta de un aviso con su alerta de AHORA: dueño, plazo, estado y botones."""
    a = V.todas.get(r["alerta_id"])
    datos = json.loads(r["datos"] or "{}")
    if not a:
        return {"alerta_id": r["alerta_id"], "titulo": datos.get("titulo"), "gravedad": datos.get("gravedad"), "estado": "cerrada",
                "estado_texto": "Ya no sale en el dato: cerrada", "dueno_id": r["dueno_id"], "responsable_id": r["dueno_id"],
                "vence": r["vence"], "vencida": False, "puede": [], "abrir": [], "ir": None}
    e = V.estados.get(a["id"])
    estado = e["estado"] if e and e["vivo"] else a.get("estado") or "nueva"
    por = (e or {}).get("quien") if e and e["vivo"] else (a.get("estado_por") or {}).get("quien")
    vence = fecha_local(a.get("vence"))
    vencida = bool(vence and ahora_local() >= vence and estado in ESTADOS_ABIERTOS)
    resp = a.get("responsable_ahora") or a.get("dueno_id")
    if estado == "lo_tengo" and por:     # quien dijo «Lo tengo» es quien la lleva hasta el dato siguiente
        resp = por
    puede = [] if V.como else (["lo_tengo", "resuelta"] if estado in ESTADOS_ABIERTOS else ["resuelta"] if estado == "lo_tengo" else [])
    quitar = V.quitar(a.get("cliente_id"))
    textos = {"nueva": "Nadie la ha cogido", "vista": "Vista", "lo_tengo": f"Lo tiene {corto(por)}" if por else "Alguien la tiene",
              "resuelta": "Marcada resuelta: se comprueba con el dato siguiente", "reabierta": "Se marcó resuelta y el dato dice que sigue",
              "no_aplica": "No aplica (con motivo)"}
    return {"alerta_id": a["id"], "titulo": P.sin_importes(a.get("titulo"), quitar), "gravedad": a.get("gravedad"), "estado": estado,
            "estado_texto": textos.get(estado, estado), "estado_por": por, "dueno_id": a.get("dueno_id"), "responsable_id": resp,
            "vence": a.get("vence"), "vencida": vencida, "plazo_h": a.get("plazo_h"),
            "escalado": P.sin_importes((a.get("escalado") or {}).get("texto"), quitar),
            "detalle": [sin_codigos(P.sin_importes(tapar(x), quitar)) for x in (a.get("detalle") or [])[:4]],
            "abrir": [{"texto": x.get("texto"), "url": P.enlace_seguro(x.get("url"))} for x in (a.get("abrir") or []) if P.enlace_seguro(x.get("url"))][:2],
            "ir": a.get("ir") if str(a.get("ir") or "").startswith("#/") else None, "puede": puede,
            "cliente": a.get("cliente"), "comprueba": a.get("comprueba")}


RX_TICKET = re.compile(r"\s*\((?:RO|ro)-\d+\)")   # el número de ticket de Desk: se llega con «Abrir la prueba»


def sin_codigos(t):
    return RX_TICKET.sub("", t) if isinstance(t, str) else t


def fila_a_json(r, V, padres=None):
    menc = json.loads(r["menciones"] or "[]")
    out = {"id": r["id"], "canal_id": r["canal_id"], "tipo": r["tipo"], "quien": r["quien"], "hilo_de": r["hilo_de"],
           "hora": (r["creado"] or "").replace(" ", "T") + "Z", "menciones": menc, "te_menciona": V.p["id"] in menc,
           "texto": sin_codigos(texto_para(V, r["texto"], r["cliente_id"])), "cliente_id": r["cliente_id"]}
    if r["tipo"] == "aviso" and r["alerta_id"]:
        out["aviso"] = aviso_de(r, V)
    datos = json.loads(r["datos"] or "{}")
    if datos.get("icono"):
        out["icono"] = datos["icono"]
    if datos.get("ir") and str(datos["ir"]).startswith("#/"):
        out["ir"] = datos["ir"]
    if r["tipo"] == "evento" and r["dueno_id"]:
        out["dueno_id"], out["vence"] = r["dueno_id"], r["vence"]
    return out


def visibles(V, canal_ids=None, desde_id=0):
    """Mensajes que ve, de sus canales (o de los pedidos), en orden."""
    ids = [c for c in (canal_ids or V.canales.keys()) if c in V.canales]
    if not ids:
        return []
    marcas = ",".join("?" * len(ids))
    filas = V.con.execute(f"SELECT * FROM canal_mensajes WHERE canal_id IN ({marcas}) AND id > ? ORDER BY id", (*ids, desde_id)).fetchall()
    por_id = {r["id"]: r for r in filas}
    return [r for r in filas if V.ve_fila(r, por_id)]


def leidos(pid, con):
    return {r["canal_id"]: r["ultimo_id"] for r in con.execute("SELECT canal_id, ultimo_id FROM canal_leidos WHERE persona_id=?", (pid,))}


def resumen_canales(V, filas=None):
    """Para la lista: no leídos, menciones, último mensaje y avisos abiertos por canal."""
    filas = visibles(V) if filas is None else filas
    lei = leidos(V.p["id"], V.con)
    hace48 = (ahora_local() - timedelta(hours=48)).replace(tzinfo=MADRID).astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")
    silenciados = set(V.pref["silenciados"])
    out = {}
    for cid, c in V.canales.items():
        out[cid] = {**c, "no_leidos": 0, "menciones": 0, "abiertos": 0, "mios": 0, "ultimo": None, "silenciado": cid in silenciados,
                    "puede_escribir": not V.como, "solo_hilos": c["tipo"] == "avisos",
                    "puede_anadir": (not V.como) and puede_anadir(V.real, c)}
    for r in filas:
        c = out.get(r["canal_id"])
        if not c:
            continue
        nuevo = r["quien"] != V.p["id"] and (r["id"] > lei[r["canal_id"]] if r["canal_id"] in lei else r["creado"] >= hace48)
        if nuevo:
            c["no_leidos"] += 1
            if V.p["id"] in json.loads(r["menciones"] or "[]"):
                c["menciones"] += 1
        if not r["hilo_de"]:
            c["ultimo"] = {"id": r["id"], "quien": r["quien"], "hora": r["creado"].replace(" ", "T") + "Z",
                           "texto": sin_codigos(texto_para(V, r["texto"], r["cliente_id"]))[:90]}
        if r["tipo"] == "aviso" and r["alerta_id"] in V.todas:
            av = aviso_de(r, V)
            if av["estado"] in ESTADOS_ABIERTOS or av["estado"] == "lo_tengo":
                c["abiertos"] += 1
                if av["responsable_id"] == V.p["id"]:
                    c["mios"] += 1
    return out


def campana(V, filas=None, lista=None):
    filas = visibles(V) if filas is None else filas
    lista = lista or resumen_canales(V, filas)
    lei = leidos(V.p["id"], V.con)
    r0 = V.con.execute("SELECT * FROM canal_campana WHERE persona_id=?", (V.p["id"],)).fetchone()
    vista_hasta = r0["hasta_id"] if r0 else 0
    items = []
    for r in filas:
        if r["quien"] == V.p["id"] or r["canal_id"] not in lista:
            continue
        menc = V.p["id"] in json.loads(r["menciones"] or "[]")
        if not menc:
            continue
        sin_leer = r["id"] > lei.get(r["canal_id"], 0)
        c = lista[r["canal_id"]]
        tipo = "aviso" if r["tipo"] == "aviso" else ("escalado" if str(r["clave"] or "").startswith("escalado:")
                                                    else "evento" if r["tipo"] == "evento" else "mencion")
        if tipo == "aviso":
            av = aviso_de(r, V)
            if av["estado"] not in ESTADOS_ABIERTOS or av["responsable_id"] != V.p["id"]:
                continue
        items.append({"id": r["id"], "tipo": tipo, "canal_id": r["canal_id"], "canal": c["titulo"], "quien": r["quien"],
                      "texto": sin_codigos(P.sin_importes(tapar(r["texto"]), V.quitar(r["cliente_id"])))[:140], "hora": r["creado"].replace(" ", "T") + "Z",
                      "nueva": r["id"] > vista_hasta, "sin_leer": sin_leer, "hilo_de": r["hilo_de"]})
    items.sort(key=lambda x: x["id"], reverse=True)
    dia = ahora_en(V.pref["zona"]).date().isoformat()
    res = V.con.execute("SELECT * FROM canal_resumenes WHERE persona_id=? AND dia=?", (V.p["id"], dia)).fetchone()
    resumen = None
    if res:
        resumen = {"dia": res["dia"], "titulo": res["titulo"], "texto": P.sin_importes(res["texto"], V.quitar(None)),
                   "hora": res["creado"].replace(" ", "T") + "Z", "nuevo": not (r0 and r0["resumen_visto"] == res["dia"])}
    no_leidos = sum(c["no_leidos"] for c in lista.values() if not c["silenciado"])
    menciones = sum(1 for x in items if x["sin_leer"] and x["tipo"] != "aviso")
    para_ti = sum(1 for x in items if x["tipo"] == "aviso")
    nuevas = sum(1 for x in items if x["nueva"]) + (1 if resumen and resumen["nuevo"] else 0)
    return {"no_leidos": no_leidos, "menciones": menciones, "avisos_para_ti": para_ti, "nuevas": nuevas,
            "hasta_id": max([r["id"] for r in filas], default=0), "items": items[:20], "resumen": resumen,
            "solo_lectura": V.como}


def ahora_en(zona):
    try:
        z = ZoneInfo(zona or "Europe/Madrid")
    except Exception:
        z = MADRID
    return ahora_local().replace(tzinfo=MADRID).astimezone(z).replace(tzinfo=None)


# =================================================================== sincronizar: alertas y eventos → avisos
_SYNC = {"t": 0.0, "candado": threading.Lock()}


def publicar(con, canal_id, tipo, texto, clave, *, quien=None, hilo_de=None, menciones=(), alerta_id=None, cliente_id=None,
             dueno_id=None, vence=None, ver=None, datos=None):
    if clave and con.execute("SELECT 1 FROM canal_mensajes WHERE clave=?", (clave,)).fetchone():
        return None
    cur = con.execute("INSERT INTO canal_mensajes (canal_id, tipo, quien, texto, hilo_de, menciones, clave, alerta_id, cliente_id, dueno_id, vence, ver, datos, creado) "
                      "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (canal_id, tipo, quien, texto, hilo_de, json.dumps(list(menciones)), clave, alerta_id, cliente_id, dueno_id, vence,
                       json.dumps(ver) if ver is not None else None, json.dumps(datos, ensure_ascii=False) if datos else None, ahora_utc_txt()))
    return cur.lastrowid


def sincronizar(forzar=False):
    """Alertas de N4 y eventos del sistema → mensajes de los canales. Idempotente (cada aviso tiene su clave)."""
    if not forzar and time.time() - _SYNC["t"] < 30:
        return 0
    with _SYNC["candado"]:
        if not forzar and time.time() - _SYNC["t"] < 30:
            return 0
        _SYNC["t"] = time.time()
        n = 0
        with S.conectar() as con:
            n += _sync_alertas(con)
            n += _sync_eventos(con)
        if n:
            S.registrar("sistema", "chat-equipo", "avisos_publicados", None, {"n": n})
        return n


def _sync_alertas(con):
    todas, _ = alertas_por_id()
    n = 0
    for a in todas.values():
        dep = a.get("departamento")
        if dep not in NOMBRE_DEP:
            continue
        clave = f"alerta:{a['id']}:{a.get('detectada') or a.get('desde') or ''}"
        dueno = a.get("dueno_id")
        texto = f"{a.get('titulo') or 'Alerta'}. {a.get('motivo') or ''}".strip()
        mid = publicar(con, f"avisos-{dep}", "aviso", texto, clave, menciones=[dueno] if dueno else [], alerta_id=a["id"],
                       cliente_id=a.get("cliente_id"), dueno_id=dueno, vence=a.get("vence"), ver={"alerta": a["id"]},
                       datos={"titulo": a.get("titulo"), "gravedad": a.get("gravedad"), "departamento": dep})
        n += 1 if mid else 0
        esc = a.get("escalado") or {}
        if esc.get("nivel"):
            padre = con.execute("SELECT id FROM canal_mensajes WHERE clave=?", (clave,)).fetchone()
            if padre:
                quien_sube = esc.get("a_id")
                t = f"Pasó el plazo sin «Lo tengo»: sube a {corto(quien_sube)}."
                n += 1 if publicar(con, f"avisos-{dep}", "evento", t, f"escalado:{clave}:{esc['nivel']}", hilo_de=padre["id"],
                                   menciones=[quien_sube] if quien_sube else [], alerta_id=a["id"], cliente_id=a.get("cliente_id"),
                                   dueno_id=quien_sube, vence=a.get("vence"), datos={"icono": "flag"}) else 0
    return n


def _sync_eventos(con):
    hoy = ahora_local().date()
    n = 0
    # Cliente firmado (data/nuevos): en #avisos-altas (con dueño y plazo de encendido) y en #general.
    nuevos = leer_json(DATA / "nuevos" / "nuevos.json", {}) or {}
    for x in nuevos.get("altas") or []:
        f = fecha_local(x.get("firma") or x.get("alta"))
        if not f or (hoy - f.date()).days > 14 or f.date() > hoy:
            continue
        cid, nom = x.get("cliente_id"), x.get("nombre") or x.get("cliente_id")
        dueno = (x.get("dueno") or {}).get("id")
        acc = (x.get("account") or {}).get("id")
        plazo = (x.get("plazo") or {}).get("objetivo")
        t = f"Cliente firmado: {nom} ({f:%d-%m}). Lleva el alta {corto(dueno) if dueno else 'sin dueño'}" + \
            (f"; account, {corto(acc)}" if acc else "; sin account asignado") + (f". Encender antes del {plazo[8:10]}-{plazo[5:7]}." if plazo else ".")
        n += 1 if publicar(con, "avisos-altas", "evento", t, f"firma:{cid}", menciones=[p for p in (dueno, acc) if p],
                           dueno_id=dueno, vence=plazo, datos={"icono": "rocket", "ir": "#/clientes-nuevos"}) else 0
        n += 1 if publicar(con, "general", "evento", f"Nuevo cliente: {nom}. Bienvenido a RO.", f"firma_general:{cid}",
                           datos={"icono": "rocket"}) else 0
    # Alta de persona: entra en los últimos 14 días (o la dieron de alta en Ajustes).
    for p in personas():
        fi = fecha_local(p.get("fecha_ingreso"))
        if not p.get("activo") or not fi or not (0 <= (hoy - fi.date()).days <= 14):
            continue
        puesto = ", ".join(x.replace("_", " ") for x in (p.get("puestos") or [])[:2])
        n += 1 if publicar(con, "general", "evento", f"Damos la bienvenida a {p.get('alias') or p['nombre']}, que entra en {puesto or 'el equipo'}.",
                           f"alta_persona_general:{p['id']}", datos={"icono": "persona"}) else 0
        n += 1 if publicar(con, "avisos-rrhh", "evento", f"Alta de persona: {p.get('alias') or p['nombre']} ({puesto}) desde el {fi:%d-%m}. Accesos y tareas de alta en Ajustes.",
                           f"alta_persona:{p['id']}", dueno_id="cecilia", menciones=["cecilia"], ver={"puestos": ["direccion", "operaciones", "rrhh"]},
                           datos={"icono": "persona", "ir": "#/ajustes"}) else 0
    # Fuente caída (data/fuentes.json): en #avisos-dirección, una vez al día.
    for x in (leer_json(DATA / "fuentes.json", {}) or {}).get("fuentes") or []:
        if x.get("estado") != "rota":
            continue
        t = f"Fuente caída: {x.get('nombre') or x['id']} no responde. Los datos que salen de ahí no se actualizan."
        n += 1 if publicar(con, "avisos-direccion", "evento", t, f"fuente:{x['id']}:{hoy.isoformat()}", dueno_id="tomas", menciones=["tomas"],
                           ver={"puestos": ["direccion", "operaciones"]}, datos={"icono": "alert", "ir": "#/ajustes"}) else 0
    # Informe enviado (data/informes): en #avisos-accounts, solo a quien puede abrir ese cliente.
    for x in (leer_json(DATA / "informes" / "informes.json", {}) or {}).get("filas") or []:
        if x.get("estado") != "enviado":
            continue
        f = fecha_local(x.get("enviado"))
        if not f or (hoy - f.date()).days > 7:
            continue
        mes = str(x.get("mes") or "")
        t = f"Informe de {mes[5:7]}-{mes[:4]} enviado a {x.get('cliente')}" + (f" por {corto(x.get('account_id'))}" if x.get("account_id") else "") + "."
        n += 1 if publicar(con, "avisos-accounts", "evento", t, f"informe:{x.get('id')}", cliente_id=x.get("cliente_id"),
                           datos={"icono": "doc", "ir": "#/informes-mensuales"}) else 0
    # Cumpleaños y aniversarios de entrada (el mismo día), en #general.
    md = f"{hoy:%m-%d}"
    for p in activas():
        nom = p.get("alias") or p["nombre"]
        if p.get("cumple_dia_mes") == md:
            n += 1 if publicar(con, "general", "evento", f"Hoy es el cumpleaños de {nom}. ¡Felicidades!", f"cumple:{p['id']}:{hoy.year}",
                               menciones=[p["id"]], datos={"icono": "heart"}) else 0
        fi = fecha_local(p.get("fecha_ingreso"))
        if fi and f"{fi:%m-%d}" == md and fi.year < hoy.year:
            anos = hoy.year - fi.year
            n += 1 if publicar(con, "general", "evento", f"Hoy {nom} cumple {anos} {'año' if anos == 1 else 'años'} en RO. ¡Gracias!",
                               f"aniversario:{p['id']}:{hoy.year}", menciones=[p["id"]], datos={"icono": "heart"}) else 0
    return n


# =================================================================== resumen diario por persona, a su hora
def resumen_para(p, con):
    V = Vista(p, p, con)
    filas = visibles(V)
    lista = resumen_canales(V, filas)
    camp = campana(V, filas, lista)
    mios = []
    for r in filas:
        if r["tipo"] == "aviso" and r["alerta_id"] in V.todas:
            av = aviso_de(r, V)
            if av["responsable_id"] == p["id"] and av["estado"] in ESTADOS_ABIERTOS | {"lo_tengo"}:
                mios.append((av, r))
    ahora = ahora_local()
    vencidas = [a for a, _ in mios if a["vencida"]]
    hoy = [a for a, _ in mios if not a["vencida"] and fecha_local(a["vence"]) and fecha_local(a["vence"]).date() == ahora.date()]
    nom = p.get("alias") or p["nombre"]
    partes = []
    if mios:
        partes.append(f"{len(mios)} {'aviso tuyo abierto' if len(mios) == 1 else 'avisos tuyos abiertos'}"
                      + (f" ({len(vencidas)} con el plazo pasado)" if vencidas else ""))
    if camp["menciones"]:
        partes.append(f"{camp['menciones']} {'mención' if camp['menciones'] == 1 else 'menciones'} sin leer")
    if camp["no_leidos"]:
        partes.append(f"{camp['no_leidos']} mensajes sin leer en tus canales")
    titulo = f"Buenos días, {nom}: " + (", ".join(partes) if partes else "nada pendiente en tus canales") + "."
    orden = sorted(mios, key=lambda x: (not x[0]["vencida"], x[0]["vence"] or "9999"))
    lineas = [f"• {a['titulo']}: {r['texto'][len(str(a['titulo'] or '')) + 2:][:110] if str(r['texto']).startswith(str(a['titulo'] or '')) else r['texto'][:110]}"
              + (" (plazo pasado)" if a["vencida"] else f" (vence el {a['vence'][8:10]}-{a['vence'][5:7]})" if a.get("vence") else "")
              for a, r in orden[:5]]
    if len(orden) > 5:
        lineas.append(f"…y {len(orden) - 5} más en tus canales de avisos.")
    texto = sin_codigos("\n".join([titulo, *lineas]))
    return titulo, texto, {"mios": len(mios), "vencidos": len(vencidas), "vencen_hoy": len(hoy), "menciones": camp["menciones"],
                           "no_leidos": camp["no_leidos"]}


def generar_resumenes():
    """A cada persona, su resumen del día cuando en SU zona pasa su hora (por defecto 08:30). Uno al día."""
    hechos = 0
    with S.conectar() as con:
        for p in activas():
            pref = preferencias(p["id"], con)
            local = ahora_en(pref["zona"])
            if local.strftime("%H:%M") < pref["hora_resumen"]:
                continue
            dia = local.date().isoformat()
            if con.execute("SELECT 1 FROM canal_resumenes WHERE persona_id=? AND dia=?", (p["id"], dia)).fetchone():
                continue
            titulo, texto, datos = resumen_para(p, con)
            con.execute("INSERT INTO canal_resumenes (persona_id, dia, titulo, texto, datos, creado) VALUES (?,?,?,?,?,?)",
                        (p["id"], dia, titulo, texto, json.dumps(datos), ahora_utc_txt()))
            hechos += 1
    if hechos:
        S.registrar("sistema", "chat-equipo", "resumen_diario", None, {"personas": hechos})
    return hechos


_RES = {"t": 0.0}


def resumenes_si_toca():
    """Además del bucle de 5 minutos: al pedir la campana, si hace más de un minuto (o se acaba de cambiar una hora)."""
    if time.time() - _RES["t"] < 60:
        return
    _RES["t"] = time.time()
    try:
        generar_resumenes()
    except Exception:
        traceback.print_exc()


def bucle():
    while True:
        try:
            if S.E.crudo:
                sincronizar()
                generar_resumenes()
        except Exception:
            traceback.print_exc()
        time.sleep(300)


# =================================================================== menciones en lo que se escribe
def menciones_en(texto):
    """@Nombre → ids de personas activas (alias, nombre o nombre completo; sin tildes)."""
    out = []
    t = norm(texto)
    for p in activas():
        for forma in {p.get("alias"), p.get("nombre"), (p.get("nombre") or "").split(" ")[0]}:
            if forma and re.search(r"@" + re.escape(norm(forma)) + r"(?![\w])", t):
                out.append(p["id"])
                break
    return out


# =================================================================== rutas
def get(h, ruta, q, real, persona_):
    uno = lambda k: (q.get(k) or [None])[0]
    if real["id"] != persona_["id"] and ruta in ("/api/canales/canal", "/api/canales/buscar"):
        S.apuntar_lectura_ver_como(real, persona_, f"{ruta}?{uno('id') or uno('q') or ''}")
    if ruta == "/api/canales/clickup":
        return get_clickup(h, real, persona_, uno("canal"), uno("antes"))
    sincronizar()
    resumenes_si_toca()
    with S.conectar() as con:
        V = Vista(persona_, real, con)
        if ruta == "/api/canales":
            filas = visibles(V)
            lista = resumen_canales(V, filas)
            return h.responder(200, {"yo": persona_["id"], "solo_lectura": V.como, "canales": list(lista.values()),
                                     "preferencias": V.pref, "campana": campana(V, filas, lista),
                                     "departamentos": [{"id": d, "nombre": n, "icono": i} for d, n, i in DEPARTAMENTOS],
                                     "generado_alertas": V.generado})
        if ruta == "/api/canales/campana":
            return h.responder(200, campana(V))
        if ruta == "/api/canales/canal":
            cid = uno("id")
            if cid not in V.canales:
                S.registrar_agrupado(real["id"], "chat-equipo", "denegado", str(cid)[:80], {"motivo": "canal ajeno"}, como=persona_["id"] if V.como else None)
                return h.responder(403, {"error": "Ese canal no es tuyo."})
            filas = visibles(V, [cid])
            raiz = [r for r in filas if not r["hilo_de"]]
            antes = int(uno("antes") or 0)
            if antes:
                raiz = [r for r in raiz if r["id"] < antes]
            pagina = raiz[-POR_PAGINA:]
            ids = {r["id"] for r in pagina}
            resp = [r for r in filas if r["hilo_de"] in ids]
            lei = leidos(persona_["id"], con).get(cid, 0)
            mie = miembros_de(cid, con)
            return h.responder(200, {"canal": resumen_canales(V, filas)[cid], "mensajes": [fila_a_json(r, V) for r in pagina + resp],
                                     "hay_mas": len(raiz) > len(pagina), "leido_hasta": lei, "miembros": mie})
        if ruta == "/api/canales/buscar":
            texto = norm(uno("q") or "").strip()
            if len(texto) < 2:
                return h.responder(200, {"resultados": []})
            res = [fila_a_json(r, V) for r in visibles(V) if texto in norm(r["texto"])]
            res = [x for x in res if texto in norm(x["texto"])][-80:][::-1]
            cu = buscar_clickup(real, persona_, texto)
            return h.responder(200, {"resultados": res, "clickup": cu})
    return h.responder(404, {"error": "No existe esa ruta de avisos."})


def _indice_clickup(pid):
    return leer_json(DATA / "chat_equipo" / f"p_{pid}.json", {}) or {}


def get_clickup(h, real, persona_, canal, antes):
    """Mensajes de un canal del espejo de ClickUp, 50 por página, solo si es miembro según SU índice.
    En «ver como» no se abre el chat de otra persona (ni Mili ni Tomás), igual que su fichero (ronda 11, X1)."""
    if real["id"] != persona_["id"]:
        return h.responder(403, {"error": "En «ver como» no se abre el chat de ClickUp de otra persona."})
    ind = _indice_clickup(persona_["id"])
    if not canal or not any(c.get("id") == canal for c in ind.get("canales") or []):
        S.registrar_agrupado(real["id"], "chat-equipo", "denegado", str(canal)[:80], {"motivo": "canal de ClickUp ajeno"})
        return h.responder(403, {"error": "Ese canal no es tuyo."})
    if not re.fullmatch(r"[\w\-]+", canal):
        return h.responder(400, {"error": "Canal no válido."})
    doc = leer_json(DATA / "chat_equipo" / "_privado" / f"c_{canal}.json", {}) or {}
    msgs = doc.get("mensajes") or []
    if antes:
        i = next((k for k, m in enumerate(msgs) if str(m.get("id")) == str(antes)), len(msgs))
        msgs = msgs[:i]
    pagina = msgs[-POR_PAGINA:]
    return h.responder(200, {"canal_id": canal, "mensajes": pagina, "hay_mas": len(msgs) > len(pagina), "generado": doc.get("generado")})


def buscar_clickup(real, persona_, texto):
    if real["id"] != persona_["id"]:
        return []
    out = []
    for c in _indice_clickup(persona_["id"]).get("canales") or []:
        doc = leer_json(DATA / "chat_equipo" / "_privado" / f"c_{c['id']}.json", {}) or {}
        for m in doc.get("mensajes") or []:
            for x in [m, *(m.get("respuestas") or [])]:
                if texto in norm(x.get("texto")) or texto in norm(x.get("autor")):
                    out.append({"canal_id": c["id"], "canal": c.get("nombre"), "tipo_canal": c.get("tipo"), "hilo_de": m["id"] if x is not m else None,
                                **{k: x.get(k) for k in ("id", "autor", "autor_pid", "fecha", "texto", "menciones")}})
    out.sort(key=lambda x: x.get("fecha") or "", reverse=True)
    return out[:80]


def post(h, ruta, real, persona_, b):
    if real["id"] != persona_["id"]:
        return h.responder(403, {"error": "Estás en «ver como»: es solo lectura. No se escribe nada."})
    rastro = []
    with S.conectar() as con:
        codigo, obj = _post(ruta, real, b, con, rastro)
    # El rastro, cuando la base ya está libre (registrar abre su propia conexión con BEGIN IMMEDIATE).
    for tipo, args in rastro:
        (S.registrar_agrupado if tipo == "agrupado" else S.registrar)(*args)
    return h.responder(codigo, obj)


def fin(codigo, obj):
    return codigo, obj


def _post(ruta, p, b, con, rastro):
    V = Vista(p, p, con)
    if ruta == "/api/canales/mensaje":
        cid = str(b.get("canal_id") or "")
        if cid not in V.canales:
            rastro.append(("agrupado", (p["id"], "chat-equipo", "denegado", cid[:80], {"motivo": "escribir en canal ajeno"})))
            return fin(403, {"error": "Ese canal no es tuyo."})
        crudo = str(b.get("texto") or "").strip()
        if not crudo:
            return fin(400, {"error": "El mensaje está vacío."})
        if len(crudo) > 2000:
            return fin(400, {"error": "Demasiado largo (máximo 2.000 caracteres)."})
        if habla_de_sueldo(crudo):
            rastro.append(("agrupado", (p["id"], "chat-equipo", "denegado", cid[:80], {"motivo": "sueldo en un canal"})))
            return fin(400, {"error": "Los sueldos no se escriben en los canales: solo dirección y RRHH los ven, en su sitio."})
        hilo = b.get("hilo_de")
        padre = None
        if hilo:
            padre = con.execute("SELECT * FROM canal_mensajes WHERE id=?", (int(hilo),)).fetchone()
            if not padre or padre["canal_id"] != cid or padre["hilo_de"] or not V.ve_fila(padre):
                return fin(403, {"error": "Ese mensaje no está en tu canal."})
        if V.canales[cid]["tipo"] == "avisos" and not padre:
            return fin(400, {"error": "En los canales de avisos se comenta en el hilo de cada aviso."})
        texto = S.limpiar_texto(crudo) if hasattr(S, "limpiar_texto") else limpiar(crudo)
        menc = menciones_en(texto)
        dentro = set(miembros_de(cid, con))
        no_ven = [m for m in menc if m not in dentro]
        cli = (padre["cliente_id"] if padre else None) or V.canales[cid].get("cliente_id")
        mid = publicar(con, cid, "mensaje", texto, None, quien=p["id"], hilo_de=padre["id"] if padre else None, menciones=menc,
                       cliente_id=cli, alerta_id=padre["alerta_id"] if padre else None)
        fila = con.execute("SELECT * FROM canal_mensajes WHERE id=?", (mid,)).fetchone()
        con.execute("INSERT INTO canal_leidos (persona_id, canal_id, ultimo_id, hora) VALUES (?,?,?,?) "
                    "ON CONFLICT(persona_id, canal_id) DO UPDATE SET ultimo_id=excluded.ultimo_id, hora=excluded.hora",
                    (p["id"], cid, mid, ahora_utc_txt()))
        out = fila_a_json(fila, V)
        rastro.append(("registrar", (p["id"], "chat-equipo", "canal_mensaje", cid, {"mensaje_id": out["id"], "menciones": out["menciones"],
                                                                               "hilo_de": out["hilo_de"], "largo": len(out["texto"])})))
        return fin(200, {"ok": True, "mensaje": out, "no_lo_veran": [corto(x) for x in no_ven]})
    elif ruta == "/api/canales/leido":
        cid = str(b.get("canal_id") or "")
        if cid not in V.canales:
            return fin(403, {"error": "Ese canal no es tuyo."})
        hasta = int(b.get("hasta_id") or 0)
        maximo = con.execute("SELECT coalesce(max(id),0) FROM canal_mensajes WHERE canal_id=?", (cid,)).fetchone()[0]
        hasta = min(hasta, maximo)
        con.execute("INSERT INTO canal_leidos (persona_id, canal_id, ultimo_id, hora) VALUES (?,?,?,?) "
                    "ON CONFLICT(persona_id, canal_id) DO UPDATE SET ultimo_id=max(canal_leidos.ultimo_id, excluded.ultimo_id), hora=excluded.hora",
                    (p["id"], cid, hasta, ahora_utc_txt()))
        return fin(200, {"ok": True, "hasta_id": hasta})
    elif ruta == "/api/canales/campana_vista":
        dia = ahora_en(V.pref["zona"]).date().isoformat()
        hasta = int(b.get("hasta_id") or 0)
        con.execute("INSERT INTO canal_campana (persona_id, hasta_id, resumen_visto, hora) VALUES (?,?,?,?) "
                    "ON CONFLICT(persona_id) DO UPDATE SET hasta_id=max(canal_campana.hasta_id, excluded.hasta_id), resumen_visto=excluded.resumen_visto, hora=excluded.hora",
                    (p["id"], hasta, dia, ahora_utc_txt()))
        return fin(200, {"ok": True})
    elif ruta == "/api/canales/estado":
        estado = b.get("estado")
        if estado not in ("lo_tengo", "resuelta"):
            return fin(400, {"error": "Solo «Lo tengo» o «Resuelta»."})
        r = con.execute("SELECT * FROM canal_mensajes WHERE id=?", (int(b.get("mensaje_id") or 0),)).fetchone()
        if not r or r["tipo"] != "aviso" or r["canal_id"] not in V.canales or not V.ve_fila(r):
            return fin(403, {"error": "Ese aviso no es de los tuyos."})
        if not S.ve_alguno(p, ["alertas"]):
            return fin(403, {"error": "Tu puesto no gestiona alertas."})
        a = V.todas.get(r["alerta_id"])
        if not a:
            return fin(409, {"error": "Esa alerta ya no sale en el dato: está cerrada."})
        av = aviso_de(r, V)
        if estado not in av["puede"]:
            return fin(409, {"error": f"Ya está «{av['estado_texto']}»."})
        tipo = "alerta_lo_tengo" if estado == "lo_tengo" else "alerta_resuelta"
        t = f"{'Lo tengo' if estado == 'lo_tengo' else 'Resuelta'}: {a.get('motivo') or a.get('titulo')}"
        cur = con.execute("INSERT INTO acciones (quien, herramienta, tipo, objeto, cliente_id, modulo, texto, vista_previa, estado, detalle) "
                          "VALUES (?,?,?,?,?,?,?,?, 'simulada', ?)",
                          (p["id"], "app", tipo, a["id"], a.get("cliente_id"), "alertas", t,
                           json.dumps({"alerta": a["id"], "departamento": a.get("departamento"), "motivo": a.get("motivo"), "estado": estado,
                                       "desde": "canal de avisos", "mensaje_id": r["id"]}, ensure_ascii=False),
                           "Desde el canal de avisos (N15): la misma acción que la pantalla de Alertas."))
        aid = cur.lastrowid
        publicar(con, r["canal_id"], "evento", f"{corto(p['id'])}: {'lo tengo' if estado == 'lo_tengo' else 'resuelta (se comprueba con el dato siguiente)'}.",
                 None, quien=p["id"], hilo_de=r["id"], alerta_id=a["id"], cliente_id=r["cliente_id"],
                 datos={"icono": "ok" if estado == "resuelta" else "check"})
        rastro.append(("registrar", (p["id"], "chat-equipo", f"aviso_{estado}", a["id"], {"mensaje_id": r["id"], "accion_id": aid})))
        V2 = Vista(p, p, con)
        return fin(200, {"ok": True, "accion_id": aid, "aviso": aviso_de(r, V2)})
    elif ruta == "/api/canales/preferencias":
        sil = [x for x in (b.get("silenciados") or []) if isinstance(x, str) and x in V.canales][:200]
        hora = str(b.get("hora_resumen") or HORA_RESUMEN)
        if not RX_HORA.match(hora):
            return fin(400, {"error": "La hora va como 08:30."})
        con.execute("INSERT INTO canal_preferencias (persona_id, silenciados, hora_resumen, actualizado) VALUES (?,?,?,?) "
                    "ON CONFLICT(persona_id) DO UPDATE SET silenciados=excluded.silenciados, hora_resumen=excluded.hora_resumen, actualizado=excluded.actualizado",
                    (p["id"], json.dumps(sil), hora, ahora_utc_txt()))
        rastro.append(("registrar", (p["id"], "chat-equipo", "preferencias_avisos", None, {"silenciados": sil, "hora_resumen": hora})))
        _RES["t"] = 0.0      # la hora nueva cuenta ya
        return fin(200, {"ok": True, "preferencias": preferencias(p["id"], con)})
    elif ruta == "/api/canales/grupo":
        nombre = limpiar(str(b.get("nombre") or "").strip(), 60)
        if len(nombre) < 2:
            return fin(400, {"error": "Ponle un nombre al grupo."})
        cli = b.get("cliente_id") or None
        if cli and not V.cliente(cli):
            return fin(403, {"error": "No puedes abrir ese cliente."})
        ids = [x for x in dict.fromkeys(b.get("miembros") or []) if isinstance(x, str)][:30]
        fuera = [x for x in ids if not (persona(x) and persona(x).get("activo"))]
        if fuera:
            return fin(400, {"error": "Hay personas que no están en la app."})
        if cli:
            sin = [x for x in ids if not puede_abrir_cliente(persona(x), cli)]
            if sin:
                return fin(400, {"error": f"{', '.join(corto(x) for x in sin)} no puede abrir ese cliente: no entra en el grupo."})
        gid = f"g-{int(time.time() * 1000):x}"
        con.execute("INSERT INTO canal_grupos (id, nombre, cliente_id, creado_por, creado) VALUES (?,?,?,?,?)", (gid, nombre, cli, p["id"], ahora_utc_txt()))
        for x in [p["id"], *[i for i in ids if i != p["id"]]]:
            con.execute("INSERT INTO canal_miembros (canal_id, persona_id, operacion, quien, hora) VALUES (?,?,?,?,?)", (gid, x, "anadir", p["id"], ahora_utc_txt()))
        publicar(con, gid, "evento", f"{corto(p['id'])} ha creado el grupo «{nombre}».", None, quien=p["id"], cliente_id=cli, datos={"icono": "eq"})
        rastro.append(("registrar", (p["id"], "chat-equipo", "grupo_crear", gid, {"nombre": nombre, "miembros": ids, "cliente_id": cli})))
        return fin(200, {"ok": True, "id": gid})
    elif ruta == "/api/canales/miembro":
        cid, otro = str(b.get("canal_id") or ""), persona(str(b.get("persona_id") or ""))
        c = V.canales.get(cid)
        if not c:
            return fin(403, {"error": "Ese canal no es tuyo."})
        if not otro or not otro.get("activo"):
            return fin(400, {"error": "Esa persona no está en la app."})
        if c["tipo"] == "general":
            return fin(400, {"error": "En #general ya está todo el equipo."})
        if not puede_anadir(p, c):
            rastro.append(("agrupado", (p["id"], "chat-equipo", "denegado", cid[:80], {"motivo": "añadir sin permiso", "persona": otro["id"]})))
            if c.get("departamento") in ("rrhh", "direccion"):
                return fin(403, {"error": "A RRHH y Dirección añade solo Tomás (y Cecilia en RRHH)."})
            return fin(403, {"error": "A este grupo añade su jefe, Mili o Tomás."})
        if c.get("cliente_id") and not puede_abrir_cliente(otro, c["cliente_id"]):
            return fin(400, {"error": f"{corto(otro['id'])} no puede abrir ese cliente: no entra en el grupo."})
        con.execute("INSERT INTO canal_miembros (canal_id, persona_id, operacion, quien, hora) VALUES (?,?,?,?,?)", (cid, otro["id"], "anadir", p["id"], ahora_utc_txt()))
        publicar(con, cid, "evento", f"{corto(p['id'])} ha añadido a {corto(otro['id'])}.", None, quien=p["id"], menciones=[otro["id"]],
                 cliente_id=c.get("cliente_id"), datos={"icono": "persona"})
        rastro.append(("registrar", (p["id"], "chat-equipo", "canal_anadir", cid, {"persona": otro["id"]})))
        return fin(200, {"ok": True})
    else:
        return fin(404, {"error": "No existe esa ruta de avisos."})


# =================================================================== enganche a servir.py
def enganchar(Manejador, servir):
    """Envuelve _api_get y api_post (como ia.py y altas_personas.py). Sin este fichero, nada cambia."""
    global S, P
    S, P = servir, servir.P
    with S.conectar() as con:
        con.executescript(TABLAS_SQL)
    get_orig, post_orig = Manejador._api_get, Manejador.api_post

    def _api_get(self, ruta, q, real, persona_):
        if ruta == "/api/canales" or ruta.startswith("/api/canales/"):
            if S.E.nucleo_bloqueado:
                return self.responder(503, {"error": "La puerta de secretos ha encontrado algo en los datos."})
            return get(self, ruta, q, real, persona_)
        return get_orig(self, ruta, q, real, persona_)

    def api_post(self, ruta, real, persona_, b):
        if ruta.startswith("/api/canales/"):
            return post(self, ruta, real, persona_, b)
        return post_orig(self, ruta, real, persona_, b)

    Manejador._api_get = _api_get
    Manejador.api_post = api_post
    if not os.environ.get("RO_AVISOS_SIN_BUCLE"):
        threading.Thread(target=bucle, daemon=True).start()
