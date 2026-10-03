#!/usr/bin/env python3
"""
avisos_programados.py · «Avisos automáticos» del chat de la app (3-oct-2026).

Encargo de Tomás: «tenemos uno de que la gente tiene que imputar las horas, y otros de mover los semáforos y demás; que en el
chat de la app estén todas y lo dejemos todo bien». Sí a avisos automáticos en el chat de la app.

Qué hace:
  · Lee las reglas de data/avisos_programados/reglas.json (qué, a quién, cuándo, condición, texto, botón y escalado) y, para
    cada una, mira la hora de CADA persona (su zona de personas.json, la de Mi perfil) y el dato de la app: avisa SOLO a quien
    le hace falta (no a quien ya imputó o ya puso el semáforo) y una sola vez (clave única por regla, persona y día).
  · Publica en los canales de avisos de la app (avisos.py · canal_mensajes, imborrable). NUNCA escribe en ClickUp, Desk, GHL
    ni en ninguna herramienta: lo que sustituye de ClickUp queda como recomendación para Tomás (data/avisos_programados/
    inventario.json y ../54_AUTOMATIZACIONES_INVENTARIO.md).
  · Si se ignora: pasado el plazo de la regla, si el dato dice que sigue sin hacerse, avisa a quien sube (su jefa, Mili o
    Tomás), una vez.
  · Cada jefa ve y cambia las reglas de su departamento (activar, hora, umbrales, horas del escalado); Mili y Tomás, todas.
    Los cambios se guardan en avisos_prog_cambios (imborrable) y en el rastro. En «ver como», solo lectura.
  · Permisos: un recordatorio personal solo lo ven la persona y su jefa (ver = {"personas": [...]}, avisos.py); lo de dinero va
    a canales que solo ven quienes lo pueden ver y sin importes (P.sin_importes encima); nunca sueldos ni datos de leads.

Rutas:  GET  /api/avisos_programados                 reglas que puede ver (con «puede_editar»), envíos de la semana
        GET  /api/avisos_programados/vista_previa?id= lo que mandaría AHORA esa regla (sin publicar; quien la puede editar)
        POST /api/avisos_programados/cambiar          {id, campo: activa|hora|umbral.<clave>|escalado_horas, valor}
        POST /api/avisos_programados/hecho            {regla, objetivo, dia}  «Ya lo he hecho» (para el escalado)
        POST /api/avisos_programados/ejecutar         (Mili y Tomás) pasa el reloj ahora
Reloj:  un hilo del servidor cada 2 minutos (RO_AVISOS_SIN_BUCLE lo apaga). RO_RELOJ=AAAA-MM-DDTHH:MM (hora de Madrid) lo
        fija en pruebas. Sin servidor:  python3 avisos_programados.py --simular [--reloj 2026-10-05T09:00]  (no publica nada)
"""
import json
import os
import re
import sys
import threading
import time
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

AQUI = Path(__file__).resolve().parent
DATA = AQUI / "data"
CARPETA = DATA / "avisos_programados"
MADRID = ZoneInfo("Europe/Madrid")
UTC = ZoneInfo("UTC")
DIAS = ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]
DIA_TXT = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
DIA_LARGO = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MES_TXT = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
MES_LARGO = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
RX_HORA = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
TODOS = {"direccion", "operaciones"}          # Tomás y Mili: todas las reglas
CLICKUP_HORAS = "https://app.clickup.com/90152357276/timesheets"

S = P = A = None                              # servir, permisos y avisos, al enganchar

TABLAS_SQL = """
CREATE TABLE IF NOT EXISTS avisos_prog_cambios (
  n INTEGER PRIMARY KEY AUTOINCREMENT, regla_id TEXT NOT NULL, campo TEXT NOT NULL, valor TEXT, antes TEXT,
  quien TEXT NOT NULL, hora TEXT NOT NULL DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS avisos_prog_hechos (
  n INTEGER PRIMARY KEY AUTOINCREMENT, clave TEXT NOT NULL, quien TEXT NOT NULL, hora TEXT NOT NULL DEFAULT (datetime('now')));
CREATE INDEX IF NOT EXISTS avisos_prog_hechos_clave ON avisos_prog_hechos (clave);
CREATE TRIGGER IF NOT EXISTS avisos_prog_cambios_sin_update BEFORE UPDATE ON avisos_prog_cambios BEGIN SELECT RAISE(ABORT, 'Un cambio de regla no se cambia'); END;
CREATE TRIGGER IF NOT EXISTS avisos_prog_cambios_sin_delete BEFORE DELETE ON avisos_prog_cambios BEGIN SELECT RAISE(ABORT, 'Un cambio de regla no se borra'); END;
CREATE TRIGGER IF NOT EXISTS avisos_prog_hechos_sin_update BEFORE UPDATE ON avisos_prog_hechos BEGIN SELECT RAISE(ABORT, 'Un «hecho» no se cambia'); END;
CREATE TRIGGER IF NOT EXISTS avisos_prog_hechos_sin_delete BEFORE DELETE ON avisos_prog_hechos BEGIN SELECT RAISE(ABORT, 'Un «hecho» no se borra'); END;
"""


# =================================================================== reloj y fechas
def ahora():
    """Hora de Madrid (sin zona). RO_RELOJ (o RO_AVISOS_AHORA) la fija en pruebas."""
    v = os.environ.get("RO_RELOJ") or os.environ.get("RO_AVISOS_AHORA")
    if v:
        return datetime.fromisoformat(v.replace("T", " ")[:16])
    return datetime.now(MADRID).replace(tzinfo=None, second=0, microsecond=0)


def zona_de(z):
    try:
        return ZoneInfo(z or "Europe/Madrid")
    except Exception:
        return MADRID


def en_zona(zona, t=None):
    return (t or ahora()).replace(tzinfo=MADRID).astimezone(zona_de(zona)).replace(tzinfo=None)


def a_utc_txt(t_madrid):
    return t_madrid.replace(tzinfo=MADRID).astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")


def de_utc(txt):
    try:
        return datetime.fromisoformat(str(txt)[:19]).replace(tzinfo=UTC).astimezone(MADRID).replace(tzinfo=None)
    except ValueError:
        return None


def laborable(d):
    return d.weekday() < 5


def lab_anterior(d):
    d = d - timedelta(days=1)
    while not laborable(d):
        d -= timedelta(days=1)
    return d


def lab_siguiente(d):
    d = d + timedelta(days=1)
    while not laborable(d):
        d += timedelta(days=1)
    return d


def ultimos_laborables_mes(d, n):
    """El n-ésimo laborable contando desde el final del mes de d (n=1 = el último)."""
    sig = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    x, k = sig - timedelta(days=1), 0
    while True:
        if laborable(x):
            k += 1
            if k >= n:
                return x
        x -= timedelta(days=1)


def dia_txt(d):
    return f"{DIA_TXT[d.weekday()]} {d.day}-{MES_TXT[d.month - 1]}"


def saludo(local):
    return "Buenos días" if local.hour < 14 else "Buenas tardes"


def plural(n, uno, varios):
    return f"{n} {uno if n == 1 else varios}"


def lunes_de(d):
    return d - timedelta(days=d.weekday())


def hora_mas(h, horas):
    hh, mm = (int(x) for x in h.split(":"))
    t = hh * 60 + mm + int(horas * 60)
    return f"{min(t, 24 * 60 - 1) // 60:02d}:{min(t, 24 * 60 - 1) % 60:02d}"


def leer_json(ruta, defecto=None):
    try:
        return json.loads(Path(ruta).read_text())
    except (OSError, ValueError):
        return defecto


# =================================================================== reglas (fichero + cambios de la base)
def ruta_reglas():
    return Path(os.environ.get("RO_AVISOS_PROG_REGLAS") or CARPETA / "reglas.json")


def reglas_base():
    return (leer_json(ruta_reglas(), {}) or {}).get("reglas") or []


def cambios(con, regla_id=None):
    sql = "SELECT * FROM avisos_prog_cambios" + (" WHERE regla_id=?" if regla_id else "") + " ORDER BY n"
    return [dict(r) for r in con.execute(sql, (regla_id,) if regla_id else ())]


def efectivas(con):
    """Las reglas tal como mandan ahora: el fichero y, encima, el último cambio de cada campo."""
    out = []
    por = {}
    for c in cambios(con):
        por.setdefault(c["regla_id"], []).append(c)
    for r in reglas_base():
        r = json.loads(json.dumps(r))
        r.setdefault("umbrales", {})
        r.setdefault("cuando", {})
        r.setdefault("escalado", {})
        for c in por.get(r["id"], []):
            v = json.loads(c["valor"]) if c["valor"] is not None else None
            if c["campo"] == "activa":
                r["activa"] = bool(v)
            elif c["campo"] == "hora":
                r["cuando"]["hora"] = v
            elif c["campo"] == "escalado_horas":
                r["escalado"]["tras_horas"] = v
            elif c["campo"].startswith("umbral.") and c["campo"][7:] in r["umbrales"]:
                r["umbrales"][c["campo"][7:]]["valor"] = v
        r["cambios"] = [{"campo": c["campo"], "valor": json.loads(c["valor"]) if c["valor"] else None,
                         "antes": json.loads(c["antes"]) if c["antes"] else None, "quien": c["quien"],
                         "hora": (c["hora"] or "").replace(" ", "T") + "Z"} for c in por.get(r["id"], [])][-12:][::-1]
        out.append(r)
    return out


def umbral(r, k, defecto=None):
    return ((r.get("umbrales") or {}).get(k) or {}).get("valor", defecto)


# =================================================================== datos de la app (solo lectura)
def personas():
    if S and S.E.crudo:
        return S.E.crudo["personas"]
    return leer_json(DATA / "personas.json", []) or []


def persona(pid):
    return next((p for p in personas() if p.get("id") == pid), None)


def activa(p):
    return bool(p and p.get("activo") and (p.get("estado") or "activo") == "activo")


def corto(pid):
    p = persona(pid)
    return (p.get("alias") or p.get("nombre")) if p else (pid or "alguien")


def departamentos():
    ruta = Path(os.environ.get("RO_DEPARTAMENTOS") or DATA / "departamentos.json")
    return (leer_json(ruta, {}) or {}).get("departamentos") or {}


def deps_de(p):
    if A:
        return A.deps_de(p)
    return []


def canal_de_persona(p):
    """El canal de avisos de su departamento (el primero del orden de avisos.py)."""
    if set(p.get("puestos") or []) & TODOS:
        return "avisos-direccion"
    d = deps_de(p)
    return f"avisos-{d[0]}" if d else "avisos-direccion"


def jefe_de(p):
    j = p.get("jefe")
    return j if j and activa(persona(j)) else "mili"


def clientes():
    if S and S.E.crudo:
        return S.E.crudo.get("clientes") or []
    return leer_json(DATA / "clientes.json", []) or []


def nombre_cliente(cid):
    return next((c.get("nombre") for c in clientes() if c.get("id") == cid), cid)


def verdad_clientes():
    return (leer_json(DATA / "verdad" / "clientes.json", {}) or {}).get("clientes") or []


def ve_cliente(p, cid):
    if not (P and S):
        return True
    return P.ver(p, {"tipo": "cliente_detalle", "cliente_id": cid}, P.contexto(p, S.E.crudo))["ok"]


def semaforos_de_la_semana(con, lunes):
    """{cliente_id} con semáforo puesto desde el lunes (00:00 de Madrid) de esa semana: tabla acciones (tipo semaforo_semanal)."""
    desde = a_utc_txt(datetime.combine(lunes, datetime.min.time()))
    hasta = a_utc_txt(datetime.combine(lunes + timedelta(days=7), datetime.min.time()))
    try:
        filas = con.execute("SELECT DISTINCT cliente_id FROM acciones WHERE tipo='semaforo_semanal' AND cliente_id IS NOT NULL "
                            "AND creada >= ? AND creada < ?", (desde, hasta)).fetchall()
    except Exception:
        return set()
    return {r[0] for r in filas}


def hecho(con, clave):
    return bool(con.execute("SELECT 1 FROM avisos_prog_hechos WHERE clave=?", (clave,)).fetchone())


# =================================================================== cuándo toca
def toca(r, local):
    """¿Es su momento? Día de la semana de la regla y entre su hora y el final de su ventana (por si el servidor estaba parado)."""
    c = r.get("cuando") or {}
    if DIAS[local.weekday()] not in (c.get("dias") or DIAS[:5]):
        return False
    h = c.get("hora") or "09:00"
    hm = local.strftime("%H:%M")
    return h <= hm < hora_mas(h, c.get("ventana_h", 6))


def texto_cuando(r):
    c = r.get("cuando") or {}
    dias = c.get("dias") or DIAS[:5]
    if dias == DIAS[:5]:
        d = "De lunes a viernes"
    elif len(dias) == 1:
        d = f"Cada {DIA_LARGO[DIAS.index(dias[0])]}"
    else:
        d = "Los " + ", ".join(DIA_LARGO[DIAS.index(x)] for x in dias)
    extra = {"informe": " de los días cercanos al límite del informe",
             "cierre": f" del {umbral(r, 'laborables_antes_fin', 3)}.º laborable antes de fin de mes"}.get(r.get("tipo"), "")
    zona = "en la hora de cada persona" if c.get("zona") == "persona" else "hora de Madrid"
    if umbral(r, "dia_mes"):
        return f"El día {umbral(r, 'dia_mes')} de cada mes (o el laborable siguiente), a las {c.get('hora') or '09:00'} ({zona})"
    return f"{d}{extra}, a las {c.get('hora') or '09:00'} ({zona})"


# =================================================================== generadores: qué mandaría cada regla ahora
# Cada uno devuelve envíos: {clave, canal, texto, menciones, dueno, vence, ver, botones, objetivo, dia, escalar}
# y sigue(r, datos, con) → ¿sigue sin hacerse? (para el escalado).

def gen_horas(r, t, con):
    doc = leer_json(DATA / "horas" / "horas.json", {}) or {}
    excl = set(r.get("excluir_puestos") or [])
    minimas = float(umbral(r, "horas_minimas", 0) or 0)
    out, sin_dato = [], []
    for x in doc.get("personas") or []:
        p = persona(x.get("persona_id"))
        if not activa(p) or set(p.get("puestos") or []) & excl or p.get("imputa_horas") == "no":
            continue
        local = en_zona(p.get("zona"), t)
        if not toca(r, local):
            continue
        dia = local.date()
        ayer = lab_anterior(dia)
        mes = next((m for m in x.get("meses") or [] if m.get("mes") == ayer.isoformat()[:7]), None)
        if not mes or mes.get("antes_de_imputar"):
            continue
        cubierto = str(x.get("ayer_fecha") or "") >= ayer.isoformat() or ayer.isoformat() in (mes.get("fechas_sin_imputar") or [])
        if not cubierto:
            sin_dato.append(p["id"])
            continue
        horas = x.get("ayer") if x.get("ayer_fecha") == ayer.isoformat() else None
        cero = ayer.isoformat() in (mes.get("fechas_sin_imputar") or []) or horas == 0
        poco = horas is not None and 0 < horas < minimas
        if not (cero or poco):
            continue
        jefe = jefe_de(p)
        nom = p.get("alias") or p["nombre"]
        cuanto = "no imputaste horas" if cero else f"solo imputaste {str(round(horas, 1)).replace('.', ',')} h"
        texto = r["texto"].format(nombre=nom, dia=dia_txt(ayer), cuanto=cuanto, saludo=saludo(local))
        out.append({"clave": f"prog:{r['id']}:{p['id']}:{ayer.isoformat()}", "canal": canal_de_persona(p), "texto": texto,
                    "menciones": [p["id"]], "dueno": p["id"], "vence": f"{dia.isoformat()}T18:00", "ver": {"personas": sorted({p["id"], jefe})},
                    "botones": [{"texto": "Imputar", "url": CLICKUP_HORAS}, {"texto": "Ver mis horas", "ir": "#/horas"}],
                    "objetivo": p["id"], "dia": ayer.isoformat(), "escalar_a": jefe,
                    "texto_escalado": f"{nom} sigue sin imputar lo del {dia_txt(ayer)} aunque se le recordó."})
    return out, {"sin_dato": sin_dato}


def sigue_horas(r, d, con):
    doc = leer_json(DATA / "horas" / "horas.json", {}) or {}
    x = next((x for x in doc.get("personas") or [] if x.get("persona_id") == d.get("objetivo")), None)
    if not x:
        return False
    mes = next((m for m in x.get("meses") or [] if m.get("mes") == str(d.get("dia"))[:7]), None) or {}
    return d.get("dia") in (mes.get("fechas_sin_imputar") or [])


def _accounts_y_clientes(r):
    excl = set(r.get("excluir_puestos") or [])
    por = {}
    for c in verdad_clientes():
        acc = c.get("account")
        p = persona(acc)
        if not acc or not activa(p) or set(p.get("puestos") or []) & excl:
            continue
        por.setdefault(acc, []).append(c["cliente_id"])
    return por


def gen_semaforo(r, t, con):
    out = []
    for acc, cids in sorted(_accounts_y_clientes(r).items()):
        p = persona(acc)
        local = en_zona(p.get("zona"), t)
        if not toca(r, local):
            continue
        lunes = lunes_de(local.date())
        puestos = semaforos_de_la_semana(con, lunes)
        faltan = [c for c in cids if c not in puestos and ve_cliente(p, c)]
        if not faltan:
            continue
        jefe = departamentos().get("accounts", {}).get("jefe") or jefe_de(p)
        nom = p.get("alias") or p["nombre"]
        nombres = sorted(nombre_cliente(c) for c in faltan)
        lista = ", ".join(nombres[:8]) + (f" y {len(nombres) - 8} más" if len(nombres) > 8 else "")
        texto = r["texto"].format(nombre=nom, n=len(faltan), clientes=lista, plural="s" if len(faltan) != 1 else "",
                                  falta="faltan" if len(faltan) != 1 else "falta",
                                  semana=dia_txt(lunes))
        orden = sorted(faltan, key=lambda c: nombre_cliente(c))
        out.append({"clave": f"prog:{r['id']}:{acc}:{lunes.isoformat()}", "canal": "avisos-accounts", "texto": texto,
                    "menciones": [acc], "dueno": acc, "vence": f"{local.date().isoformat()}T13:00", "ver": {"personas": sorted({acc, jefe})},
                    "botones": [{"texto": f"Semáforo de {nombre_cliente(c)[:24]}", "ir": f"#/ficha/{c}?semaforo=1"} for c in orden[:4]],
                    "objetivo": acc, "dia": lunes.isoformat(), "faltan": orden, "escalar_a": jefe,
                    "texto_escalado": f"{nom} sigue sin el semáforo de esta semana en {len(faltan)} cliente{'s' if len(faltan) != 1 else ''}."})
    return out, {}


def sigue_semaforo(r, d, con):
    puestos = semaforos_de_la_semana(con, date.fromisoformat(d["dia"]))
    return any(c not in puestos for c in d.get("faltan") or [])


def _ciclo_informes():
    doc = leer_json(DATA / "informes" / "informes.json", {}) or {}
    return doc, ((doc.get("_meta") or {}).get("ciclo") or {})


PENDIENTE_INFORME = {"en_curso", "sin_tarea", "atrasado", "pendiente"}


def gen_informe(r, t, con):
    doc, ciclo = _ciclo_informes()
    mes, limite = ciclo.get("mes"), ciclo.get("limite")
    if not mes or not limite:
        return [], {"sin_dato": ["informes"]}
    lim = date.fromisoformat(limite)
    antes = int(umbral(r, "laborables_antes", 2) or 2)
    aviso = lim
    for _ in range(antes):
        aviso = lab_anterior(aviso)
    por = {}
    for f in doc.get("filas") or []:
        if f.get("mes") == mes and f.get("estado") in PENDIENTE_INFORME and f.get("account_id"):
            por.setdefault(f["account_id"], []).append(f)
    out = []
    excl = set(r.get("excluir_puestos") or [])
    for acc, filas in sorted(por.items()):
        p = persona(acc)
        if not activa(p) or set(p.get("puestos") or []) & excl:
            continue
        local = en_zona(p.get("zona"), t)
        hoy = local.date()
        etapa = "antes" if hoy == aviso else "limite" if hoy == lim else None
        if not etapa or not toca(r, local):
            continue
        filas = [f for f in filas if ve_cliente(p, f.get("cliente_id"))]
        if not filas:
            continue
        nom = p.get("alias") or p["nombre"]
        nombres = sorted(f.get("cliente") or nombre_cliente(f.get("cliente_id")) for f in filas)
        m = int(mes[5:7])
        texto = r["texto"].format(nombre=nom, n=len(filas), plural="s" if len(filas) != 1 else "", mes=MES_LARGO[m - 1],
                                  falta="faltan" if len(filas) != 1 else "falta",
                                  clientes=", ".join(nombres[:8]) + (f" y {len(nombres) - 8} más" if len(nombres) > 8 else ""),
                                  limite=dia_txt(lim), cuando="hoy" if etapa == "limite" else f"el {dia_txt(lim)}")
        jefe = departamentos().get("accounts", {}).get("jefe") or jefe_de(p)
        out.append({"clave": f"prog:{r['id']}:{acc}:{mes}:{etapa}", "canal": "avisos-accounts", "texto": texto,
                    "menciones": [acc], "dueno": acc, "vence": f"{limite}T23:00", "ver": {"personas": sorted({acc, jefe})},
                    "botones": [{"texto": "Abrir mis informes", "ir": "#/informes-mensuales"}],
                    "objetivo": acc, "dia": hoy.isoformat(), "mes": mes, "ids": [f.get("id") for f in filas],
                    "escalar_a": jefe if etapa == "limite" else None,
                    "texto_escalado": f"Pasó el límite y a {nom} le siguen faltando informes de {MES_LARGO[m - 1]}."})
    return out, {}


def sigue_informe(r, d, con):
    doc, _ = _ciclo_informes()
    ids = set(d.get("ids") or [])
    return any(f.get("id") in ids and f.get("estado") in PENDIENTE_INFORME for f in doc.get("filas") or [])


def gen_cierre(r, t, con):
    dueno = r.get("a_quien_persona") or "sofia"
    p = persona(dueno)
    if not activa(p):
        return [], {}
    local = en_zona(p.get("zona"), t)
    n = int(umbral(r, "laborables_antes_fin", 3) or 3)
    if local.date() != ultimos_laborables_mes(local.date(), n) or not toca(r, local):
        return [], {}
    sig = (local.date().replace(day=28) + timedelta(days=4)).replace(day=1)
    mes_act = local.date().isoformat()[:7]
    nuevos = leer_json(DATA / "nuevos" / "nuevos.json", {}) or {}
    altas = [x for x in nuevos.get("altas") or [] if str(x.get("alta") or x.get("firma") or "")[:7] == mes_act]
    previstas = [x for x in nuevos.get("previstas") or [] if str(x.get("alta_prevista") or "")[:7] <= sig.isoformat()[:7]]
    cuadre = leer_json(DATA / "finanzas" / "cuadre_facturacion.json", {}) or {}
    difs = len(cuadre.get("airtable_diferencias") or [])
    incong = len(cuadre.get("incongruencias") or [])
    ultimo = ultimos_laborables_mes(local.date(), 1)
    resumen = "; ".join([
        plural(len(altas), "cliente dado de alta", "clientes dados de alta") + ((": " + ", ".join(sorted(x.get("nombre") or "" for x in altas)[:8])) if altas else ""),
        plural(len(previstas), "alta prevista sin firmar", "altas previstas sin firmar"),
        plural(difs, "diferencia entre Airtable y Holded", "diferencias entre Airtable y Holded"),
        plural(incong, "incongruencia abierta en el cuadre", "incongruencias abiertas en el cuadre")])
    texto = r["texto"].format(nombre=p.get("alias") or p["nombre"], mes=MES_LARGO[sig.month - 1], ultimo=dia_txt(ultimo), resumen=resumen)
    clave = f"prog:{r['id']}:{dueno}:{mes_act}"
    return [{"clave": clave, "canal": "avisos-administracion", "texto": texto, "menciones": [dueno], "dueno": dueno,
             "vence": f"{ultimo.isoformat()}T18:00", "ver": {"puestos": ["administracion", "direccion"]},
             "botones": [{"texto": "Abrir el cuadre", "ir": "#/finanzas"},
                         {"texto": "Ya lo he hecho", "ir": f"#/avisos-automaticos/hecho/{r['id']}/{dueno}/{mes_act}"}],
             "objetivo": dueno, "dia": mes_act, "escalar_a": r.get("escalar_a_persona") or "tomas",
             "texto_escalado": f"El cierre de facturación de {MES_LARGO[sig.month - 1]} sigue sin marcarse como hecho."}], {}


def sigue_cierre(r, d, con):
    return not hecho(con, d.get("clave_base") or "")


def gen_publicidad(r, t, con):
    local = en_zona("Europe/Madrid", t)
    if not toca(r, local):
        return [], {}
    cap = leer_json(DATA / "captacion" / "captacion.json", {}) or {}
    ritmo_max = float(umbral(r, "ritmo_pct", 110) or 110)
    silencio = int(umbral(r, "dias_silencio", 4) or 4)
    deprisa, sin_gasto, caros = [], [], []
    for c in cap.get("clientes") or []:
        tr = (c.get("equipo") or {}).get("trafficker")
        pa = c.get("presupuesto_ads") or {}
        if local.day > silencio and pa.get("pct_mes") and pa.get("pct_consumido") is not None:
            ritmo = 100 * pa["pct_consumido"] / pa["pct_mes"]
            if ritmo >= ritmo_max:
                deprisa.append((ritmo, c, tr))
        if c.get("meta_activa") and (c.get("gasto") or {}).get("ayer") == 0:
            sin_gasto.append((c, tr))
        if c.get("severidad") == "critico" and any(m.get("clase_id") == "paid" for m in c.get("motivos") or []):
            caros.append((c, tr))
    if not (deprisa or sin_gasto or caros):
        return [], {}
    partes = []
    menc = set()
    if deprisa:
        deprisa.sort(key=lambda x: -x[0])
        partes.append(f"{len(deprisa)} cuenta{'s' if len(deprisa) != 1 else ''} gasta{'n' if len(deprisa) != 1 else ''} más deprisa de lo previsto: " +
                      "; ".join(f"{c['nombre']} (va al {round(rt)} % del ritmo{', lo lleva ' + corto(tr) if tr else ''})" for rt, c, tr in deprisa[:6]))
        menc |= {tr for _, _, tr in deprisa if tr}
    if sin_gasto:
        partes.append(f"{len(sin_gasto)} con la campaña activa y sin gasto ayer: " + ", ".join(c["nombre"] for c, _ in sin_gasto[:6]))
        menc |= {tr for _, tr in sin_gasto if tr}
    if caros:
        partes.append(f"{len(caros)} en rojo por coste: " + ", ".join(c["nombre"] for c, _ in caros[:6]))
        menc |= {tr for _, tr in caros if tr}
    texto = r["texto"].format(dia=dia_txt(local.date()), saludo=saludo(local)) + "\n" + "\n".join(f"• {x}" for x in partes)
    menc = sorted(m for m in menc if activa(persona(m)))
    return [{"clave": f"prog:{r['id']}:canal:{local.date().isoformat()}", "canal": "avisos-publicidad", "texto": texto, "menciones": menc,
             "dueno": departamentos().get("publicidad", {}).get("jefe"), "vence": None, "ver": {"puestos": ["trafficker", "jefa_publicidad", "direccion", "operaciones"]},
             "botones": [{"texto": "Abrir Captación", "ir": "#/captacion"}], "objetivo": "canal", "dia": local.date().isoformat(), "escalar_a": None}], {}


def gen_semanal(r, t, con):
    local = en_zona("Europe/Madrid", t)
    if not toca(r, local):
        return [], {}
    lunes = lunes_de(local.date())
    al = (leer_json(DATA / "alertas" / "alertas.json", {}) or {}).get("alertas") or []
    abiertas = [a for a in al if (a.get("estado") or "nueva") in ("nueva", "vista", "reabierta", "lo_tengo")]
    graves = [a for a in abiertas if a.get("gravedad") in ("critica", "critico", "rojo", "alta")]
    por_dep = {}
    for a in abiertas:
        por_dep[a.get("departamento")] = por_dep.get(a.get("departamento"), 0) + 1
    top = ", ".join(f"{(A.NOMBRE_DEP if A else {}).get(d, d)} {n}" for d, n in sorted(por_dep.items(), key=lambda x: -x[1])[:4])
    accs = _accounts_y_clientes({"excluir_puestos": ["direccion"]})
    total_cli = sum(len(v) for v in accs.values())
    puestos = semaforos_de_la_semana(con, lunes)
    con_sem = sum(1 for v in accs.values() for c in v if c in puestos)
    horas = leer_json(DATA / "horas" / "horas.json", {}) or {}
    sin_imp = [x for x in horas.get("personas") or [] if (x.get("semana") or 0) == 0 and activa(persona(x.get("persona_id")))]
    _, ciclo = _ciclo_informes()
    doc_inf, _ = _ciclo_informes()
    pend_inf = sum(1 for f in doc_inf.get("filas") or [] if f.get("mes") == ciclo.get("mes") and f.get("estado") in PENDIENTE_INFORME)
    nuevos = leer_json(DATA / "nuevos" / "nuevos.json", {}) or {}
    firmados = [x for x in nuevos.get("altas") or [] if str(x.get("firma") or x.get("alta") or "")[:10] >= lunes.isoformat()]
    desde = a_utc_txt(datetime.combine(lunes, datetime.min.time()))
    env = con.execute("SELECT count(*) FROM canal_mensajes WHERE clave LIKE 'prog:%' AND creado >= ?", (desde,)).fetchone()[0]
    esc = con.execute("SELECT count(*) FROM canal_mensajes WHERE clave LIKE 'prog_esc:%' AND creado >= ?", (desde,)).fetchone()[0]
    lineas = [f"• Alertas abiertas: {len(abiertas)} ({len(graves)} graves). Más en {top or '—'}.",
              f"• Semáforo del lunes: {con_sem} de {total_cli} clientes con semáforo esta semana.",
              f"• Horas: {len(sin_imp)} persona{'s' if len(sin_imp) != 1 else ''} sin ninguna hora imputada esta semana.",
              f"• Informes de {MES_LARGO[int(ciclo['mes'][5:7]) - 1] if ciclo.get('mes') else 'este mes'}: {pend_inf} sin enviar" + (f" (límite {dia_txt(date.fromisoformat(ciclo['limite']))})." if ciclo.get("limite") else "."),
              f"• Clientes firmados esta semana: {len(firmados)}" + (": " + ", ".join(x.get('nombre') or '' for x in firmados[:6]) if firmados else "") + ".",
              f"• Avisos automáticos: {env} enviados y {esc} escalados esta semana."]
    texto = r["texto"].format(semana=dia_txt(lunes)) + "\n" + "\n".join(lineas)
    return [{"clave": f"prog:{r['id']}:canal:{lunes.isoformat()}", "canal": "avisos-direccion", "texto": texto, "menciones": ["tomas", "mili"],
             "dueno": "tomas", "vence": None, "ver": {"puestos": ["direccion", "operaciones"]},
             "botones": [{"texto": "Abrir el panel de dirección", "ir": "#/panel-direccion"}, {"texto": "Ver alertas", "ir": "#/alertas"}],
             "objetivo": "canal", "dia": lunes.isoformat(), "escalar_a": None}], {}


def gen_fijo(r, t, con):
    """Un recordatorio fijo (lo que alguien mandaba a mano cada semana): a un canal, a su hora de Madrid, con mención por puesto."""
    local = en_zona(r.get("cuando", {}).get("zona_fija") or "Europe/Madrid", t)
    if not toca(r, local):
        return [], {}
    dm = umbral(r, "dia_mes") or (r.get("cuando") or {}).get("dia_mes")
    if dm:                                   # mensual: ese día (o el laborable siguiente si cae en fin de semana)
        d = local.date().replace(day=min(int(dm), 28))
        while not laborable(d):
            d += timedelta(days=1)
        if local.date() != d:
            return [], {}
    puestos = set(r.get("mencionar_puestos") or [])
    menc = sorted(p["id"] for p in personas() if activa(p) and set(p.get("puestos") or []) & puestos)[:12]
    return [{"clave": f"prog:{r['id']}:canal:{local.date().isoformat()}", "canal": r.get("canal") or "general",
             "texto": r["texto"].format(dia=dia_txt(local.date())), "menciones": menc, "dueno": None, "vence": None,
             "ver": {"puestos": sorted(puestos | TODOS)} if puestos and r.get("solo_mencionados") else None,
             "botones": [b for b in r.get("botones") or [] if str(b.get("ir") or "").startswith("#/")][:3],
             "objetivo": "canal", "dia": local.date().isoformat(), "escalar_a": None}], {}


def gen_semaforo_resumen(r, t, con):
    """Lunes por la tarde: cómo va el semáforo de la semana, por account (cuántos faltan), en #avisos-accounts."""
    local = en_zona("Europe/Madrid", t)
    if not toca(r, local):
        return [], {}
    lunes = lunes_de(local.date())
    puestos = semaforos_de_la_semana(con, lunes)
    accs = _accounts_y_clientes(r)
    total = sum(len(v) for v in accs.values())
    hechos = sum(1 for v in accs.values() for c in v if c in puestos)
    faltan = sorted(((acc, sum(1 for c in v if c not in puestos)) for acc, v in accs.items()), key=lambda x: -x[1])
    faltan = [(a, n) for a, n in faltan if n]
    if not faltan:
        texto = r["texto"].format(semana=dia_txt(lunes), hechos=hechos, total=total) + " Todos al día."
    else:
        texto = r["texto"].format(semana=dia_txt(lunes), hechos=hechos, total=total) + " Faltan: " + \
            ", ".join(f"{corto(a)} {n}" for a, n in faltan) + "."
    return [{"clave": f"prog:{r['id']}:canal:{lunes.isoformat()}", "canal": "avisos-accounts", "texto": texto,
             "menciones": [a for a, _ in faltan], "dueno": departamentos().get("accounts", {}).get("jefe"), "vence": None,
             "ver": {"puestos": ["account", "operaciones", "direccion", "proyectos"]},
             "botones": [{"texto": "Ver Mis clientes", "ir": "#/ficha"}], "objetivo": "canal", "dia": lunes.isoformat(), "escalar_a": None}], {}


def gen_arranque(r, t, con):
    """Lunes y viernes: cómo va el arranque de los clientes nuevos (fuera de plazo y sin tareas), para Agus y el equipo de altas."""
    local = en_zona("Europe/Madrid", t)
    if not toca(r, local):
        return [], {}
    nuevos = leer_json(DATA / "nuevos" / "nuevos.json", {}) or {}
    altas = nuevos.get("altas") or []
    if not altas:
        return [], {}
    fuera = [x for x in altas if (x.get("plazo") or {}).get("estado") == "rojo"]
    res = nuevos.get("resumen") or {}
    dueno = departamentos().get("altas", {}).get("dueno_fijo") or "agustina"
    partes = [plural(len(altas), "alta en marcha", "altas en marcha"),
              plural(len(fuera), "fuera de plazo", "fuera de plazo") + ((": " + ", ".join(x.get("nombre") or "" for x in fuera[:6])) if fuera else "")]
    if res.get("sin_tareas_48h"):
        partes.append(plural(res["sin_tareas_48h"], "sin tareas a las 48 h", "sin tareas a las 48 h"))
    if res.get("tareas_vencidas"):
        partes.append(plural(res["tareas_vencidas"], "tarea de arranque vencida", "tareas de arranque vencidas"))
    texto = r["texto"].format(dia=dia_txt(local.date())) + " " + "; ".join(partes) + "."
    return [{"clave": f"prog:{r['id']}:canal:{local.date().isoformat()}", "canal": "avisos-altas", "texto": texto,
             "menciones": [dueno], "dueno": dueno, "vence": None, "ver": None,
             "botones": [{"texto": "Abrir Clientes nuevos", "ir": "#/clientes-nuevos"}], "objetivo": "canal", "dia": local.date().isoformat(),
             "escalar_a": None}], {}


def gen_produccion(r, t, con):
    """Lunes: a cada persona de producción y redes con tareas vencidas, su número y el botón a su cola (sin nombres de cliente)."""
    doc = leer_json(DATA / "produccion" / "produccion.json", {}) or {}
    tope = int(umbral(r, "vencidas_min", 3) or 3)
    out = []
    excl = set(r.get("excluir_puestos") or [])
    for x in doc.get("personas") or []:
        p = persona(x.get("persona_id") or x.get("id"))
        n = x.get("vencidas") or 0
        if not activa(p) or n < tope or set(p.get("puestos") or []) & excl:
            continue
        local = en_zona(p.get("zona"), t)
        if not toca(r, local):
            continue
        jefe = jefe_de(p)
        nom = p.get("alias") or p["nombre"]
        out.append({"clave": f"prog:{r['id']}:{p['id']}:{lunes_de(local.date()).isoformat()}", "canal": canal_de_persona(p),
                    "texto": r["texto"].format(nombre=nom, n=n), "menciones": [p["id"]], "dueno": p["id"], "vence": None,
                    "ver": {"personas": sorted({p["id"], jefe})}, "botones": [{"texto": "Abrir mi cola", "ir": "#/produccion"}],
                    "objetivo": p["id"], "dia": local.date().isoformat(), "escalar_a": None})
    return out, {}


GENERADORES = {"horas": (gen_horas, sigue_horas), "semaforo": (gen_semaforo, sigue_semaforo), "informe": (gen_informe, sigue_informe),
               "cierre": (gen_cierre, sigue_cierre), "publicidad": (gen_publicidad, None), "semanal": (gen_semanal, None),
               "fijo": (gen_fijo, None), "produccion": (gen_produccion, None), "semaforo_resumen": (gen_semaforo_resumen, None),
               "arranque": (gen_arranque, None)}


# =================================================================== motor
_CANDADO = threading.Lock()


def calcular(r, t, con):
    g = GENERADORES.get(r.get("tipo"))
    if not g:
        return [], {"error": "tipo desconocido"}
    try:
        return g[0](r, t, con)
    except Exception as e:                        # una regla rota no tumba las demás
        traceback.print_exc()
        return [], {"error": str(e)[:200]}


def _publicar(con, e, r):
    datos = {"icono": r.get("icono") or "campana", "botones": e.get("botones") or [], "regla": r["id"], "objetivo": e.get("objetivo"),
             "dia": e.get("dia"), "programado": True}
    for k in ("faltan", "ids", "mes", "escalar_a", "texto_escalado"):
        if e.get(k):
            datos[k] = e[k]
    ir = next((b["ir"] for b in e.get("botones") or [] if b.get("ir")), None)
    if ir:
        datos["ir"] = ir
    texto = S.limpiar_texto(e["texto"], 1800) if hasattr(S, "limpiar_texto") else e["texto"][:1800]
    return A.publicar(con, e["canal"], "evento", texto, e["clave"], menciones=e.get("menciones") or [], dueno_id=e.get("dueno"),
                      vence=e.get("vence"), ver=e.get("ver"), datos=datos)


def escalar(con, r, t):
    """Lo publicado hace más de «tras_horas» que sigue sin hacerse (según el dato) y sin «Ya lo he hecho»: aviso a quien sube."""
    esc = r.get("escalado") or {}
    horas = esc.get("tras_horas") or 0
    sigue = (GENERADORES.get(r.get("tipo")) or (None, None))[1]
    if not horas or not sigue:
        return 0
    n = 0
    limite = a_utc_txt(t - timedelta(hours=float(horas)))
    hace8 = a_utc_txt(t - timedelta(days=8))
    filas = con.execute("SELECT * FROM canal_mensajes WHERE clave LIKE ? AND creado <= ? AND creado >= ? AND hilo_de IS NULL",
                        (f"prog:{r['id']}:%", limite, hace8)).fetchall()
    for m in filas:
        if con.execute("SELECT 1 FROM canal_mensajes WHERE clave=?", ("prog_esc:" + m["clave"],)).fetchone():
            continue
        d = json.loads(m["datos"] or "{}")
        d["clave_base"] = m["clave"]
        if hecho(con, m["clave"]):
            continue
        try:
            if not sigue(r, d, con):
                continue
        except Exception:
            traceback.print_exc()
            continue
        a_quien = (json.loads(m["menciones"] or "[]") or [None])[0]
        sube = d.get("escalar_a") or esc.get("a") or "mili"
        if sube == a_quien:
            sube = jefe_de(persona(a_quien) or {}) if a_quien else "tomas"
        p_sube = persona(sube)
        if not activa(p_sube):
            continue
        texto_base = (d.get("texto_escalado") or r.get("texto_escalado") or "Sigue sin hacerse.")
        texto = f"{texto_base} Se avisó hace {int(horas)} h. @{corto(sube)}, ¿lo miras?"
        ver_padre = json.loads(m["ver"] or "null")
        mio = A.Vista(p_sube, p_sube, con)
        if m["canal_id"] in mio.canales and mio.ve_fila(m):
            mid = A.publicar(con, m["canal_id"], "evento", texto, "prog_esc:" + m["clave"], hilo_de=m["id"], menciones=[sube], dueno_id=sube,
                             datos={"icono": "flag", "regla": r["id"], "escalado": True})
        else:     # quien sube no ve ese canal: aviso suelto en el suyo, solo para él
            mid = A.publicar(con, canal_de_persona(p_sube), "evento", texto, "prog_esc:" + m["clave"], menciones=[sube], dueno_id=sube,
                             ver={"personas": [sube]} if (ver_padre or {}).get("personas") else ver_padre,
                             datos={"icono": "flag", "regla": r["id"], "escalado": True, "ir": d.get("ir")})
        n += 1 if mid else 0
    return n


def ejecutar(forzar_regla=None, simular=False, t=None):
    """Una vuelta del reloj. simular=True no publica: devuelve lo que mandaría."""
    t = t or ahora()
    resumen = {"hora": t.strftime("%Y-%m-%d %H:%M"), "publicados": 0, "escalados": 0, "reglas": {}}
    with _CANDADO, S.conectar() as con:
        for r in efectivas(con):
            if forzar_regla and r["id"] != forzar_regla:
                continue
            if not r.get("activa") and not simular:
                continue
            envios, extra = calcular(r, t, con)
            info = {"envios": len(envios), **extra}
            if simular:
                info["detalle"] = envios
            else:
                for e in envios:
                    if _publicar(con, e, r):
                        resumen["publicados"] += 1
                resumen["escalados"] += escalar(con, r, t)
            resumen["reglas"][r["id"]] = info
    if not simular and (resumen["publicados"] or resumen["escalados"]):
        S.registrar("sistema", "avisos-automaticos", "avisos_programados", None,
                    {"publicados": resumen["publicados"], "escalados": resumen["escalados"], "hora": resumen["hora"]})
    return resumen


def bucle():
    time.sleep(5)
    while True:
        try:
            if S.E.crudo:
                ejecutar()
        except Exception:
            traceback.print_exc()
        time.sleep(120)


# =================================================================== permisos de la pantalla
def puede_editar(p, r):
    pu = P.puestos_de(p) if P else set(p.get("puestos") or [])
    if pu & TODOS:
        return True
    conf = departamentos().get(r.get("departamento")) or {}
    return p["id"] in (conf.get("jefe"), conf.get("dueno_fijo"))


def le_llega(p, r):
    """¿Esta regla le manda algo a esta persona (o a su canal)?"""
    pu = set(p.get("puestos") or [])
    tipo = r.get("tipo")
    if tipo == "horas":
        return p.get("imputa_horas") != "no" and not pu & set(r.get("excluir_puestos") or [])
    if tipo in ("semaforo", "informe"):
        return "account" in pu and not pu & set(r.get("excluir_puestos") or [])
    if tipo == "cierre":
        return p["id"] == (r.get("a_quien_persona") or "sofia")
    if tipo == "publicidad":
        return bool(pu & {"trafficker", "jefa_publicidad"})
    if tipo == "semanal":
        return bool(pu & TODOS)
    if tipo == "produccion":
        return not pu & (set(r.get("excluir_puestos") or []) | {"setters"})
    if tipo == "fijo":
        return r.get("canal") == "general" or bool(pu & set(r.get("mencionar_puestos") or []))
    if tipo == "semaforo_resumen":
        return "account" in pu
    if tipo == "arranque":
        return "altas" in deps_de(p) and not pu & TODOS
    return False


def a_json(r, p, con, como):
    edita = puede_editar(p, r) and not como
    desde = a_utc_txt(datetime.combine(lunes_de(ahora().date()), datetime.min.time()))
    env = con.execute("SELECT count(*) FROM canal_mensajes WHERE clave LIKE ? AND creado >= ?", (f"prog:{r['id']}:%", desde)).fetchone()[0]
    esc = con.execute("SELECT count(*) FROM canal_mensajes WHERE clave LIKE ? AND creado >= ?", (f"prog_esc:prog:{r['id']}:%", desde)).fetchone()[0]
    ult = con.execute("SELECT creado FROM canal_mensajes WHERE clave LIKE ? ORDER BY id DESC LIMIT 1", (f"prog:{r['id']}:%",)).fetchone()
    ver_todo = puede_editar(p, r)
    esc_c = r.get("escalado") or {}
    return {"id": r["id"], "nombre": r.get("nombre"), "departamento": r.get("departamento"),
            "departamento_nombre": (A.NOMBRE_DEP if A else {}).get(r.get("departamento"), r.get("departamento")),
            "icono": r.get("icono") or "campana", "activa": bool(r.get("activa")), "que_hace": r.get("que_hace"),
            "a_quien": r.get("a_quien_texto"), "condicion": r.get("condicion_texto"), "canal": r.get("canal_texto"),
            "cuando": texto_cuando(r), "hora": (r.get("cuando") or {}).get("hora"), "zona": (r.get("cuando") or {}).get("zona"),
            "boton": r.get("boton_texto"), "ejemplo": r.get("ejemplo"),
            "escalado": {"tras_horas": esc_c.get("tras_horas") or 0, "texto": esc_c.get("texto"), "editable": esc_c.get("editable", True)},
            "umbrales": [{"clave": k, **v} for k, v in (r.get("umbrales") or {}).items()],
            "sustituye": r.get("sustituye") or [], "apagar_en_origen": r.get("apagar_en_origen"),
            "mejora": r.get("mejora"), "puede_editar": edita, "le_llega": le_llega(p, r),
            "envios_semana": env if ver_todo else None, "escalados_semana": esc if ver_todo else None,
            "ultimo_envio": (ult[0].replace(" ", "T") + "Z") if (ult and ver_todo) else None,
            "cambios": r.get("cambios") if ver_todo else []}


def visibles_para(p, reglas):
    return [r for r in reglas if puede_editar(p, r) or le_llega(p, r)]


def inventario_para(p):
    if not (set(p.get("puestos") or []) & TODOS):
        return None
    doc = leer_json(CARPETA / "inventario.json", None)
    if not doc:
        return None
    filas = doc.get("filas") if isinstance(doc, dict) else doc
    return {"filas": [{k: x.get(k) for k in ("id", "que", "canal", "frecuencia", "hora", "quien", "automatico", "regla_app", "apagar_en_origen", "veces_90d")}
                      for x in filas or []][:200], "generado": doc.get("generado") if isinstance(doc, dict) else None,
            "pendientes": (leer_json(ruta_reglas(), {}) or {}).get("no_se_hace_aun") or []}


# =================================================================== rutas
def _vista_previa_texto(e, p):
    """Lo que vería quien mira la vista previa: tapado e importes fuera según su puesto."""
    pu = P.puestos_de(p)
    quitar = P.importes_a_quitar(bool(pu & {"direccion", "operaciones", "proyectos", "administracion", "finanzas_direccion"}),
                                 bool(pu & {"direccion", "operaciones", "jefa_publicidad"}))
    return {"canal": e.get("canal"), "texto": P.sin_importes(A.tapar(e["texto"]) if A else e["texto"], quitar),
            "menciones": [corto(x) for x in e.get("menciones") or []], "botones": [b.get("texto") for b in e.get("botones") or []],
            "para": corto(e.get("objetivo")) if e.get("objetivo") not in (None, "canal") else "el canal",
            "escala_a": corto(e.get("escalar_a")) if e.get("escalar_a") else None}


def get(h, ruta, q, real, persona_):
    uno = lambda k: (q.get(k) or [None])[0]
    como = real["id"] != persona_["id"]
    with S.conectar() as con:
        reglas = efectivas(con)
        if ruta == "/api/avisos_programados":
            vis = visibles_para(persona_, reglas)
            if como:     # lo que ven LAS DOS
                ids_real = {r["id"] for r in visibles_para(real, reglas)}
                vis = [r for r in vis if r["id"] in ids_real]
            t = ahora()
            return h.responder(200, {"reglas": [a_json(r, persona_, con, como) for r in vis], "solo_lectura": como,
                                     "puede_ejecutar": bool(P.puestos_de(real) & TODOS) and not como,
                                     "ahora": t.strftime("%Y-%m-%dT%H:%M"), "inventario": None if como else inventario_para(persona_),
                                     "departamentos": [{"id": d, "nombre": n} for d, n, _ in (A.DEPARTAMENTOS if A else [])]})
        if ruta == "/api/avisos_programados/vista_previa":
            r = next((x for x in reglas if x["id"] == uno("id")), None)
            if not r or not puede_editar(persona_, r):
                S.registrar_agrupado(real["id"], "avisos-automaticos", "denegado", str(uno("id"))[:60], {"motivo": "vista previa ajena"},
                                     como=persona_["id"] if como else None)
                return h.responder(403, {"error": "Esa regla no es de tu departamento."})
            # «Cómo quedaría»: la regla como si fuera su hora en cada persona hoy (o el día que le toca).
            envios, extra = calcular_ejemplo(r, con)
            return h.responder(200, {"id": r["id"], "envios": [_vista_previa_texto(e, persona_) for e in envios[:12]], "total": len(envios),
                                     "sin_dato": [corto(x) for x in extra.get("sin_dato") or [] if persona(x)], "error": extra.get("error"),
                                     "cuando": extra.get("cuando")})
    return h.responder(404, {"error": "No existe esa ruta de avisos automáticos."})


def calcular_ejemplo(r, con):
    """La regla en su próximo momento (hoy o el siguiente día que le toca, a su hora): para enseñar cómo quedaría."""
    base = ahora()
    hh, mm = (int(x) for x in ((r.get("cuando") or {}).get("hora") or "09:00").split(":"))
    for k in range(0, 40):
        d = base.date() + timedelta(days=k)
        t = datetime.combine(d, datetime.min.time()).replace(hour=hh, minute=mm) + timedelta(minutes=1)
        if (r.get("cuando") or {}).get("zona") == "persona":      # su hora en la zona de cada uno: probamos varias horas de Madrid
            envios, extra = [], {}
            vistos = set()
            for dh in (0, 3, 5, 6, 7, 8, 9):
                e, x = calcular(r, t + timedelta(hours=dh), con)
                for y in e:
                    if y["clave"] not in vistos:
                        vistos.add(y["clave"])
                        envios.append(y)
                extra.setdefault("sin_dato", [])
                extra["sin_dato"] = sorted(set(extra["sin_dato"]) | set(x.get("sin_dato") or []))
        else:
            envios, extra = calcular(r, t, con)
        if envios or extra.get("sin_dato") or extra.get("error") or k == 39:
            extra["cuando"] = f"{DIA_LARGO[d.weekday()]} {d.day} de {MES_LARGO[d.month - 1]}"
            return envios, extra
    return [], {}


def post(h, ruta, real, persona_, b):
    if real["id"] != persona_["id"]:
        return h.responder(403, {"error": "Estás en «ver como»: es solo lectura. No se cambia nada."})
    p = real
    if ruta == "/api/avisos_programados/ejecutar":
        if not P.puestos_de(p) & TODOS:
            return h.responder(403, {"error": "Solo Mili y Tomás pasan el reloj a mano."})
        res = ejecutar()
        S.registrar(p["id"], "avisos-automaticos", "avisos_programados_ejecutar", None, {"publicados": res["publicados"], "escalados": res["escalados"]})
        return h.responder(200, {"ok": True, **{k: res[k] for k in ("hora", "publicados", "escalados")}})
    if ruta == "/api/avisos_programados/hecho":
        regla, obj, dia = (str(b.get(k) or "")[:60] for k in ("regla", "objetivo", "dia"))
        if not re.fullmatch(r"[\w\-]+", regla) or not re.fullmatch(r"[\w\-]+", obj) or not re.fullmatch(r"[\d\-]{7,10}", dia):
            return h.responder(400, {"error": "Aviso no válido."})
        clave = f"prog:{regla}:{obj}:{dia}"
        with S.conectar() as con:
            m = con.execute("SELECT * FROM canal_mensajes WHERE clave=?", (clave,)).fetchone()
            r = next((x for x in efectivas(con) if x["id"] == regla), None)
            if not m or not r:
                return h.responder(404, {"error": "Ese aviso no existe."})
            if p["id"] != obj and not puede_editar(p, r):
                S.registrar_agrupado(p["id"], "avisos-automaticos", "denegado", clave[:80], {"motivo": "hecho ajeno"})
                return h.responder(403, {"error": "Ese aviso es de otra persona."})
            if hecho(con, clave):
                return h.responder(200, {"ok": True, "ya": True})
            con.execute("INSERT INTO avisos_prog_hechos (clave, quien, hora) VALUES (?,?,?)", (clave, p["id"], a_utc_txt(ahora())))
            A.publicar(con, m["canal_id"], "evento", f"{corto(p['id'])}: hecho.", f"prog_hecho:{clave}", quien=p["id"], hilo_de=m["id"],
                       datos={"icono": "ok"})
        S.registrar(p["id"], "avisos-automaticos", "aviso_programado_hecho", clave, {"regla": regla})
        return h.responder(200, {"ok": True})
    if ruta == "/api/avisos_programados/cambiar":
        rid, campo, valor = str(b.get("id") or ""), str(b.get("campo") or ""), b.get("valor")
        with S.conectar() as con:
            r = next((x for x in efectivas(con) if x["id"] == rid), None)
            if not r:
                return h.responder(404, {"error": "Esa regla no existe."})
            if not puede_editar(p, r):
                S.registrar_agrupado(p["id"], "avisos-automaticos", "denegado", rid[:60], {"motivo": "cambiar regla ajena", "campo": campo[:40]})
                return h.responder(403, {"error": "Esta regla la cambian la jefa de su departamento, Mili o Tomás."})
            if campo == "activa":
                if not isinstance(valor, bool):
                    return h.responder(400, {"error": "Activa va como sí o no."})
                antes = bool(r.get("activa"))
            elif campo == "hora":
                if not isinstance(valor, str) or not RX_HORA.match(valor):
                    return h.responder(400, {"error": "La hora va como 09:30."})
                antes = (r.get("cuando") or {}).get("hora")
            elif campo == "escalado_horas":
                if not (r.get("escalado") or {}).get("editable", True) or isinstance(valor, bool) or not isinstance(valor, (int, float)) or not (0 <= valor <= 168):
                    return h.responder(400, {"error": "El escalado va en horas, de 0 (sin escalado) a 168."})
                valor = int(valor)
                antes = (r.get("escalado") or {}).get("tras_horas") or 0
            elif campo.startswith("umbral.") and campo[7:] in (r.get("umbrales") or {}):
                u = r["umbrales"][campo[7:]]
                if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not (u.get("min", 0) <= valor <= u.get("max", 10 ** 6)):
                    return h.responder(400, {"error": f"{u.get('texto', 'El umbral')}: entre {u.get('min', 0)} y {u.get('max')}."})
                antes = u.get("valor")
            else:
                return h.responder(400, {"error": "Ese campo no se cambia desde aquí."})
            if antes == valor:
                return h.responder(400, {"error": "Ya estaba así."})
            con.execute("INSERT INTO avisos_prog_cambios (regla_id, campo, valor, antes, quien, hora) VALUES (?,?,?,?,?,?)",
                        (rid, campo, json.dumps(valor), json.dumps(antes), p["id"], a_utc_txt(ahora())))
            nueva = next(x for x in efectivas(con) if x["id"] == rid)
            out = a_json(nueva, p, con, False)
        S.registrar(p["id"], "avisos-automaticos", "aviso_programado_cambio", rid, {"campo": campo, "antes": antes, "valor": valor})
        return h.responder(200, {"ok": True, "regla": out})
    return h.responder(404, {"error": "No existe esa ruta de avisos automáticos."})


# =================================================================== enganche a servir.py
def enganchar(Manejador, servir):
    """Envuelve _api_get y api_post (como avisos.py). Sin este fichero, nada cambia."""
    global S, P, A
    S, P = servir, servir.P
    A = sys.modules.get("avisos")
    if A is None:
        import avisos as A_  # noqa: E402
        A = A_
    with S.conectar() as con:
        con.executescript(TABLAS_SQL)
    get_orig, post_orig = Manejador._api_get, Manejador.api_post

    def _api_get(self, ruta, q, real, persona_):
        if ruta == "/api/avisos_programados" or ruta.startswith("/api/avisos_programados/"):
            if S.E.nucleo_bloqueado:
                return self.responder(503, {"error": "La puerta de secretos ha encontrado algo en los datos."})
            return get(self, ruta, q, real, persona_)
        return get_orig(self, ruta, q, real, persona_)

    def api_post(self, ruta, real, persona_, b):
        if ruta.startswith("/api/avisos_programados/"):
            return post(self, ruta, real, persona_, b)
        return post_orig(self, ruta, real, persona_, b)

    Manejador._api_get = _api_get
    Manejador.api_post = api_post
    if not os.environ.get("RO_AVISOS_SIN_BUCLE"):
        threading.Thread(target=bucle, daemon=True).start()


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv or len(sys.argv) == 1:
        print(__doc__.strip())
        sys.exit(0)
    if "--reloj" in sys.argv:
        os.environ["RO_RELOJ"] = sys.argv[sys.argv.index("--reloj") + 1]
    if "--simular" in sys.argv:
        # Sin servidor: carga servir.py como módulo (no arranca nada) para leer personas y la base, y simula una vuelta.
        os.environ.setdefault("RO_AVISOS_SIN_BUCLE", "1")
        sys.path.insert(0, str(AQUI))
        import servir as SV  # noqa: E402
        if not SV.E.crudo:
            SV.E.cargar() if hasattr(SV.E, "cargar") else None
        S, P = SV, SV.P
        import avisos as A_  # noqa: E402
        A_.S, A_.P = SV, SV.P
        A = A_
        with S.conectar() as con:
            con.executescript(TABLAS_SQL)
        res = ejecutar(simular=True)
        for rid, info in res["reglas"].items():
            print(f"— {rid}: {info['envios']} aviso(s)" + (f" · sin dato: {', '.join(info.get('sin_dato') or [])}" if info.get("sin_dato") else ""))
            for e in info.get("detalle") or []:
                print(f"    [{e['canal']}] {e['texto'][:160]}")
