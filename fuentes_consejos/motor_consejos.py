#!/usr/bin/env python3
"""fuentes_consejos/motor_consejos.py · N12 · «Qué haría yo hoy aquí» por pantalla y persona (2-oct-2026).

Motor de REGLAS deterministas: funciona sin clave de Anthropic. No lee ficheros por su cuenta: recibe los datos YA
recortados para esa persona (los pide ia.leer_como() por la misma puerta que /api/modulo/*) y devuelve candidatos.
Quien sirve (ia.consejo) vuelve a filtrar cada candidato por permisos y se queda con 1 a 3 por pantalla.

Fuentes que usa (todas opcionales; si falta una, esa regla calla):
  · alertas      data/alertas/p_<persona>.json   (motor N4: dueño, motivo, plazo, fuente, enlace a la prueba)
  · verdad       data/verdad/clientes.json        (bloqueo callado, fuga de integración)
  · fuentes      data/fuentes.json + data/conexiones/salud.json si existe (dato viejo, caída, último dato bueno)
  · conexiones   data/ajustes/conexiones.json     (solo si la persona ve Ajustes)
  · setters      data/ventas_ro/setters.json      (solo su fila: recuento y citas propias, sin nombres ni teléfonos)
  · catalogo     indicadores.json de sus puestos  (umbral firmado que respalda el consejo)

Forma de un candidato (lo que viaja al navegador, ya filtrado):
  { id, tipo, pantallas[], cliente_id, cliente, que, porque, cifra, umbral, fuente{texto,url}, ir, quien, cuando,
    gravedad, orden, personal, requiere[], accion{tipo,objeto,texto}|None, origen: "reglas" }
"""
import os
import re
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
    _MADRID = ZoneInfo("Europe/Madrid")
except Exception:                       # sin tzdata: la hora del equipo (mejor que nada)
    _MADRID = None


def ahora_madrid():
    """V2-F: «ahora» en hora de Madrid y sin zona, la misma vara que servir.hoy() y ctx.hoy (permisos.ahora_madrid).
    RO_RELOJ=«AAAA-MM-DDTHH:MM» lo fija en las pruebas. Nunca datetime.now() a secas (zona del Mac, Tomás en Bali)."""
    fijo = os.environ.get("RO_RELOJ")
    if fijo:
        try:
            return datetime.fromisoformat(fijo.replace(" ", "T"))
        except ValueError:
            pass
    return datetime.now(_MADRID).replace(tzinfo=None) if _MADRID else datetime.now()

GRAV = {"alta": 300, "media": 200, "baja": 100}

# Pantalla en la que vive cada alerta (además de la de su módulo de origen), y las que nunca llevan consejo.
SIN_CONSEJO = {"asistente-ia", "componentes", "indicadores", "alertas"}   # la IA ya es la pantalla, o es la lista de alertas
CON_CLIENTE = {"ficha", "en-rojo", "captacion", "seo-web", "redes", "clientes-nuevos", "informe-cliente", "paneles", "dinero-cliente"}

# tipo de alerta → (qué hacer, etiqueta de la cifra o None, sufijo de indicador del catálogo o None, verbo del botón)
TIPOS = {
    "acc_correos": ("Contesta hoy el correo más antiguo de {cliente}", "correos sin contestar", None),
    "acc_sin_agente": ("Asigna hoy un agente al ticket de {cliente} en Desk", None, None),
    "acc_critico": ("Llama hoy a {cliente}: es un cliente crítico", None, None),
    "acc_informe": ("Envía desde Desk el informe mensual de {cliente}", None, "informe_mensual"),
    "acc_sin_reunion": ("Agenda esta semana una reunión con {cliente}", None, "reunion"),
    "acc_llamadas": ("Devuelve hoy las llamadas perdidas", "llamadas perdidas", None),
    "acc_config": ("Corrige la configuración de Desk o Zadarma que deja llamadas sin atender", None, None),
    "alta_fuera_plazo": ("Enciende la campaña de {cliente} o escala hoy el motivo", "días desde la firma", "encendid"),
    "alta_sin_lista": ("Crea hoy la lista de arranque de {cliente} en ClickUp", None, None),
    "adm_sin_alta": ("Da de alta a {cliente} en facturación", None, "altas_en_facturacion"),
    "adm_impago": ("Reclama hoy la factura vencida de {cliente}", "días vencida", "dias_de_cobro"),
    "dir_decision": ("Toma la decisión pendiente: {titulo}", None, None),
    "dir_sin_account": ("Asigna un account a {cliente}", None, "huecos_en_accounts"),
    "crm_sin_tocar": ("Llama hoy a los leads sin tocar de {cliente}", "leads sin tocar", "leads_sin_tocar"),
    "crm_sin_usar": ("Decide si la subcuenta de {cliente} se usa o se archiva", None, None),
    "crm_citas_sin_estado": ("Marca en GoHighLevel si vinieron a las citas de {cliente}", "citas sin estado", "citas_sin_estado"),
    "crm_whatsapp": ("Revisa hoy el WhatsApp de {cliente} en GoHighLevel", "WhatsApp fallidos", "whatsapp_fallido"),
    "pub_critico": ("Revisa hoy la campaña de {cliente}: el coste por lead se ha disparado", None, "coste_por_lead_frente"),
    "pub_atencion": ("Revisa la campaña de {cliente} en Meta", None, "coste_por_lead_frente"),
    "seo_rojo": ("Revisa hoy las palabras de {cliente} que salen del top 10", None, "palabras_clave_clave_fuera"),
    "seo_ambar": ("Comprueba en Google las palabras a vigilar de {cliente} antes de tocar nada", None, None),
    "web_caida": ("Levanta hoy la web de {cliente}", None, None),
    "web_spam": ("Limpia hoy la web de {cliente}: tiene enlaces de spam", None, None),
    "web_lenta": ("Mira por qué tarda en cargar la web de {cliente}", None, None),
    "web_certificado": ("Renueva el certificado de la web de {cliente} antes de que caduque", "días para caducar", None),
    "web_medicion": ("Arregla la medición de Analytics de {cliente}", None, None),
    "redes_hueco": ("Programa esta semana las publicaciones de {cliente}", None, None),
    "redes_fallida": ("Vuelve a publicar lo que falló de {cliente} y pide que reconecte la red", "publicaciones fallidas", None),
    "rrhh_alerta": ("Habla esta semana con {persona}: está en alerta", None, None),
    "rrhh_aniversario": ("Felicita a {persona} por su aniversario en RO", None, None),
    "rrhh_no_imputa": ("Recuérdale a {persona} que impute las horas de ayer", None, "imputacion"),
}

# fuente de datos (data/fuentes.json → id) → nombre llano, dueño y expresiones con las que se reconoce en un texto.
# El orden importa: lo específico primero (para «Qué hacer» en estados vacíos y «Sin dato»).
FUENTES = [
    ("seranking", "SE Ranking", "Jerónimo", [r"SE\s?Ranking", r"posiciones"]),
    ("gsc", "Search Console", "Agus", [r"Search Console"]),
    ("ga4", "Google Analytics", "Agus", [r"Analytics", r"\bGA4\b"]),
    # V2-B: el dueño de una conexión es el de Ajustes › Conexiones (duenoConexion): la clave la pone Tomás
    ("google_ads", "Google Ads", "Tomás", [r"Google Ads", r"Windsor"]),
    ("tiktok", "TikTok Ads", "Tomás", [r"TikTok"]),
    ("meta", "Meta", "Tomás", [r"\bMeta\b", r"Facebook"]),
    ("captacion_ghl", "Embudo de GoHighLevel", "Agus", [r"embudo de GoHighLevel"]),
    ("ghl", "GoHighLevel", "Agus", [r"GoHighLevel", r"\bGHL\b", r"subcuenta"]),
    ("metricool", "Metricool", "Tomás", [r"Metricool", r"publicaciones programadas"]),
    ("snov", "Snov.io", "Yessica", [r"Snov", r"correo en fr[ií]o"]),
    ("outreach", "Outreach", "Yessica", [r"outreach", r"prospecci[oó]n"]),
    ("zadarma", "Zadarma", "Tomás", [r"Zadarma", r"llamadas"]),
    ("desk", "Zoho Desk", "Tomás", [r"\bDesk\b", r"correos? (de cliente|sin contestar)"]),
    ("reuniones", "Reuniones (CRM y Fathom)", "Mili", [r"Fathom", r"reuni[oó]n(es)? con (el|los|sus|tus) clientes?"]),
    ("informes", "Informes mensuales", "Mili", [r"informes? mensual"]),
    ("horas", "Horas de ClickUp", "Mili", [r"imputad", r"horas (de|en) ClickUp"]),
    ("tareas", "Tareas de ClickUp", "Mili", [r"tareas (de|en) ClickUp", r"\bClickUp\b"]),
    ("arranque", "Arranque de clientes nuevos", "Mili", [r"onboarding", r"arranque"]),
    ("alarmas", "Alarmas del panel de Mili", "Mili", [r"alarmas"]),
    ("cartera", "Cartera de ClickUp", "Mili", [r"cartera"]),
    ("zoom", "Zoom", "Tomás", [r"\bZoom\b", r"grabaci[oó]n"]),
    ("chat", "Canal de ClickUp del cliente", "Mili", [r"canal de ClickUp"]),
]
FUENTE = {f[0]: f for f in FUENTES}
# conexión de Ajustes que alimenta cada fuente (para el dueño real si Ajustes lo dice)
CONEXION_DE = {"meta": "meta", "ghl": "ghl_agencia", "captacion_ghl": "ghl_agencia", "ga4": "google", "gsc": "google",
               "google_ads": "windsor", "tiktok": "windsor", "seranking": "seranking", "metricool": "metricool", "snov": "snov",
               "zadarma": "zadarma", "desk": "zoho", "zoom": "zoom"}
# pantalla → fuentes de las que vive (para avisar en el consejo si alguna está caída o vieja)
FUENTES_DE_PANTALLA = {
    # R14: Producción ya no lleva este aviso: su sello único de frescura dice la hora de cada fuente y quién la pone al día
    # (antes salían «Ojo con las cifras… hace 12 h» y, debajo, «Datos al día»).
    "bandeja": ["desk", "zadarma"], "horas": ["horas"], "informes-mensuales": ["informes"],
    "reuniones": ["reuniones"], "captacion": ["meta", "captacion_ghl", "google_ads", "tiktok"], "salud-crm": ["ghl", "captacion_ghl"],
    "seo-web": ["gsc", "ga4", "seranking"], "redes": ["metricool"], "prospeccion": ["outreach", "snov"],
    "en-rojo": ["cartera", "alarmas"], "clientes-nuevos": ["arranque"], "paneles": ["ga4", "gsc", "meta", "ghl", "metricool"],
    "ficha": ["desk", "meta", "ghl", "ga4", "gsc", "metricool", "tareas"], "informe-cliente": ["meta", "ghl", "ga4", "gsc", "metricool"],
}
MALOS = {"rota", "sin_conectar", "dato_viejo", "caida", "a_cero"}
# V2 (V2-C1): UN dueño por conexión, el mismo que Ajustes › Conexiones (duenoConexion en modulos/ajustes_conexiones.js):
# las claves las pega Tomás (solo él tiene las cuentas de administrador) y Agus comprueba después que llegan los datos.
DUENOS_CONEXION = {"google_ads": "pegar la clave de Google Ads", "tiktok": "pegar la clave de Windsor (trae Google Ads y TikTok)",
                   "windsor": "pegar la clave de Windsor (trae Google Ads y TikTok)", "seranking": "pegar la clave de proyectos de SE Ranking",
                   "modular": "pegar la clave de Modular DS", "anthropic": "pegar la clave de la IA (Anthropic)"}


def dueno_conexion(fid):
    q = DUENOS_CONEXION.get(fid)
    return ("Tomás", f"lo hace Tomás: {q}; después Agus comprueba que llegan los datos") if q else (None, None)

# V2-B · fuente de la que vive cada tipo de consejo: si está caída o en duda, el consejo lo dice (y el aviso suelto de
# «Ojo con las cifras…» deja de ocupar un sitio: va al sello de frescura del bloque).
FUENTE_DE_TIPO = {"acc_correos": "desk", "acc_sin_agente": "desk", "crm_sin_tocar": "ghl", "crm_sin_usar": "ghl",
                  "crm_citas_sin_estado": "ghl", "crm_whatsapp": "ghl", "pub_critico": "meta", "pub_atencion": "meta",
                  "fuga_integracion": "meta", "seo_rojo": "seranking", "seo_ambar": "seranking", "redes_hueco": "metricool",
                  "redes_fallida": "metricool", "bloqueo_callado": "tareas", "rrhh_no_imputa": "horas",
                  "prod_devuelta": "tareas", "prod_vencida": "tareas", "prod_hoy": "tareas", "prod_revision": "tareas",
                  "outreach_clasificar": "outreach"}

# Etiquetas de cifra en singular (B2: nunca «1 citas», «1 leads»).
SINGULAR = {"correos sin contestar": "correo sin contestar", "llamadas perdidas": "llamada perdida",
            "días desde la firma": "día desde la firma", "días vencida": "día vencida", "leads sin tocar": "lead sin tocar",
            "citas sin estado": "cita sin estado", "WhatsApp fallidos": "WhatsApp fallido",
            "días para caducar": "día para caducar", "publicaciones fallidas": "publicación fallida"}
DIAS_SEM = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
DIAS_CORTO = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def pl(n, uno, varios):
    """«1 correo» / «3 correos» (B2)."""
    return f"{n} {uno if n == 1 else varios}"


def _cifra(n, etiqueta):
    n = int(n) if isinstance(n, float) and n.is_integer() else n
    return f"{n} {SINGULAR.get(etiqueta, etiqueta) if n == 1 else etiqueta}"


def _hm(t):
    """«2026-10-02 18:05» → «18:05» si es hoy; «1-oct, 09:38» si no (44 §2.3)."""
    if not t:
        return None
    try:
        d = datetime.fromisoformat(str(t).replace("Z", "").replace(" UTC", "")[:19])
    except ValueError:
        return str(t)[:16]
    if d.date() == ahora_madrid().date():
        return d.strftime("%H:%M")
    meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    return f"{d.day}-{meses[d.month - 1]}, {d.strftime('%H:%M')}"


def _dia(d, ahora):
    """«hoy», «ayer», «el vie 2-oct» o «el 15-sep» (B2: sin minutos raros; 44 §2.3)."""
    dd = (ahora.date() - d.date()).days
    if dd == 0:
        return "hoy"
    if dd == 1:
        return "ayer"
    if 0 < dd < 7:
        return f"el {DIAS_CORTO[d.weekday()]} {d.day}-{MESES[d.month - 1]}"
    return f"el {d.day}-{MESES[d.month - 1]}"


def _rel(d, ahora):
    """Día relativo con la regla de fechas.relativo (componentes.js): «hoy», «ayer», «mañana», «el vie 2-oct» (±6 días) o «28-sep»."""
    n = (ahora.date() - d.date()).days
    if n == 0:
        return "hoy"
    if n == 1:
        return "ayer"
    if n == -1:
        return "mañana"
    if abs(n) <= 6:
        return f"el {DIAS_CORTO[d.weekday()]} {d.day}-{MESES[d.month - 1]}"
    return f"{d.day}-{MESES[d.month - 1]}" + (f"-{d.year}" if d.year != ahora.year else "")


def vencida_txt(dv, ahora):
    """Lo que ya venció (su DÍA es anterior a hoy): «Vencida ayer» · «Vencida hace 3 días». Igual que «Vencida hace N días»
    de Mi día y Producción (fechas.vencida: lo que vence hoy NO está vencido)."""
    n = (ahora.date() - dv.date()).days
    return "Vencida ayer" if n == 1 else f"Vencida hace {n} días"


def plazo_txt(dv, ahora, con_hora=True):
    """V2-F: plazo con la MISMA regla que fechas.plazo (componentes.js): día relativo y, si trae hora, la hora en punto
    siguiente («17:53» → «18:00»). «Vence hoy a las 18:00» · «Vence mañana a las 10:00» · «Vence el lun 5 a las 9:00» ·
    «Vence el 28-sep». Si su día ya pasó: «Vencida hace N días». Sin salto al lunes: la fecha es la misma en toda la app."""
    if dv.date() < ahora.date():
        return vencida_txt(dv, ahora)
    rel = _rel(dv, ahora)
    hh = None
    if con_hora:
        hh = min(23, dv.hour + (1 if dv.minute or dv.second else 0))
    if hh is None or rel[0].isdigit():
        return f"Vence el {rel}" if rel[0].isdigit() else f"Vence {rel}"
    return f"Vence {rel} a las {hh}:00"


def _cuando(a, ahora):
    v = a.get("vence")
    if not v:
        return "Esta semana" if a.get("gravedad") != "alta" else "Hoy"
    try:
        dv = datetime.fromisoformat(str(v).replace("Z", "")[:19])
    except ValueError:
        return f"Vence el {v}"
    return plazo_txt(dv, ahora, con_hora=bool(re.search(r"[ T]\d\d:\d\d", str(v))))


def _orden(a, ahora):
    s = GRAV.get(a.get("gravedad"), 100)
    try:
        dv = datetime.fromisoformat(str(a["vence"]).replace("Z", "")[:19]).date() if a.get("vence") else None
        if dv and dv < ahora.date():          # vencida = su día es anterior a hoy (fechas.vencida)
            s += 60
        elif dv and dv == ahora.date():
            s += 30
    except ValueError:
        pass
    if a.get("estado") == "lo_tengo":
        s -= 150          # ya tiene dueño: baja, no desaparece
    if isinstance(a.get("cifra"), (int, float)):
        s += min(int(a["cifra"]), 40)
    return s


def _umbral(catalogo, sufijo):
    if not sufijo or not catalogo:
        return None
    ind = next((i for i in catalogo if sufijo in (i.get("id") or "") and i.get("umbral")), None)
    if not ind:
        return None
    nombre = re.sub(r"\b(\w+)( \1\b)+", r"\1", ind.get("nombre") or "", flags=re.I)   # «clave clave» → «clave»
    return f"{nombre} · {niveles(ind.get('umbral'))}"


def niveles(umbral):
    """«≤ 15 / 16-60 / > 60» → «bien ≤ 15 · vigilar 16-60 · crítico > 60» (glosario 44 §2.1: Crítico / Vigilar / Bien).
    Un tramo «—» no existe y no sale. Si no son tres tramos, el texto tal cual."""
    t = str(umbral or "").strip()
    partes = [x.strip() for x in t.split(" / ")]
    if len(partes) != 3:
        return t
    baja = lambda x: x[0].lower() + x[1:] if len(x) > 1 and x[0].isupper() and x[1].islower() else x   # «Día 10» → «día 10»
    return " · ".join(f"{n} {baja(x)}" for n, x in zip(("bien", "vigilar", "crítico"), partes) if x and x != "—")


def _primer_enlace(a):
    for x in a.get("abrir") or []:
        if x.get("url"):
            return x["url"]
    return None


def _pantallas_de_alerta(a):
    ps = []
    ir = (a.get("ir") or "").lstrip("#/").split("/")[0]
    for p in (a.get("modulo_origen"), ir):
        if p and p not in ps:
            ps.append(p)
    if a.get("cliente_id") and "ficha" not in ps:
        ps.append("ficha")
    if a.get("tipo") == "acc_critico" and "en-rojo" not in ps:
        ps.append("en-rojo")
    ps.append("mi-dia")
    return [p for p in ps if p not in SIN_CONSEJO]


# Lo que va en «Lo primero hoy» no se repite en el consejo de Mi día, salvo lo que manda en el puesto: la decisión con
# reloj de dirección y el cliente crítico del account (A2/A3: el consejo n.º 1 tiene que ser eso, no las horas).
SIEMPRE_EN_MI_DIA = {"dir_decision", "acc_critico"}


def _es_nuevo(v):
    """Alta de menos de 90 días según la verdad única (M9: nunca proponer archivar su subcuenta)."""
    if not v:
        return False
    if v.get("nuevo"):
        return True
    try:
        return int(v.get("dia_alta")) < 90
    except (TypeError, ValueError):
        return False


def de_alertas(persona, alertas_doc, catalogo, nombre, ahora, verdad_idx=None):
    """Una alerta abierta = un candidato. Lo que Mi día ya enseña en «Lo primero hoy» no se repite en Mi día (salvo las
    decisiones con reloj de dirección: son lo primero que Tomás tiene que hacer y el consejo las ordena por plazo)."""
    out = []
    if not alertas_doc:
        return out
    verdad_idx = verdad_idx or {}
    es_dir = "direccion" in (persona.get("puestos") or [])
    primeras = {x.get("id") for x in (alertas_doc.get("mi_dia") or {}).get("primeras") or []}
    for a in (alertas_doc.get("alertas") or []) + (alertas_doc.get("avisos") or []):
        if a.get("estado") in ("resuelta", "no_aplica", "pospuesta"):     # A8: lo pospuesto vuelve solo en su fecha
            continue
        tipo = a.get("tipo")
        v = verdad_idx.get(a.get("cliente_id")) if a.get("cliente_id") else None
        if tipo == "crm_sin_usar" and _es_nuevo(v):          # M9: una subcuenta de un alta no se archiva antes del día 90
            continue
        que, etiqueta, sufijo = TIPOS.get(tipo, ("Revisa: {titulo}", None, None))
        propia = a.get("persona_id") and a.get("persona_id") == persona["id"]
        resp = resp_alerta = a.get("responsable_ahora") or a.get("dueno_id")
        porque = a.get("motivo") or a.get("titulo")
        orden = _orden(a, ahora)
        gravedad = a.get("gravedad") or "media"
        if tipo == "rrhh_no_imputa" and propia:
            # A2/M4: las horas son solo un aviso: nunca el primer consejo si hay cualquier otra cosa
            que, orden, gravedad = "Imputa en ClickUp las horas de ayer", 20, "baja"
            porque = re.sub(r"^\S+ no imputó", "No imputaste", porque or "")       # B4: «Tú», no en tercera persona
        if tipo in ("pub_critico", "pub_atencion"):
            que = _que_captacion(a, tipo)
        if tipo == "acc_critico" and v and v.get("gravedad") != "critico":
            que = "Llama hoy a {cliente}"                     # nunca contradecir la verdad única (A1: una sola vara de rojo)
        if tipo == "dir_decision":
            que = f"Contesta la decisión con reloj: {(a.get('motivo') or a.get('titulo') or '').rstrip('.')}"[:120]
            rec = next((d for d in a.get("detalle") or [] if str(d).startswith("Recomendación")), None)
            porque = rec or porque
            orden += 120 if a.get("vence") else 60
        if tipo == "adm_impago" and es_dir and any("decide Tomás" in str(d) for d in a.get("detalle") or []):
            # A3: a dirección le toca decidir el impago largo (más de 60 días), no reclamarlo (eso es de Sofía)
            resp, que = persona["id"], f"Decide qué hacer con el impago de {a.get('cliente') or 'el cliente'}"
            porque = f"{porque} A partir de 60 días lo decides tú (rectificativa, burofax o seguir esperando)."
        sin_cli = None if a.get("cliente") else (str(a.get("motivo") or "").split(":")[0].strip() if ":" in str(a.get("motivo") or "")[:60] else None)
        que = que.format(cliente=a.get("cliente") or sin_cli or "el cliente", titulo=(a.get("titulo") or "").rstrip("."),
                         persona=a.get("persona") or _persona_de_motivo(a.get("motivo")) or "esa persona").replace(" de el ", " del ")
        quien = "Tú" if resp == persona["id"] else (nombre(resp) or "Su dueño")
        cifra = None
        if etiqueta and isinstance(a.get("cifra"), (int, float)):
            cifra = _cifra(a["cifra"], etiqueta)
        pantallas = _pantallas_de_alerta(a)
        if a.get("id") in primeras and tipo not in SIEMPRE_EN_MI_DIA:
            pantallas = [p for p in pantallas if p != "mi-dia"]
        out.append({
            "id": f"al:{a.get('id')}", "tipo": tipo, "pantallas": pantallas,
            "cliente_id": a.get("cliente_id"), "cliente": a.get("cliente"),
            # B6: la etiqueta de persona solo en las de RRHH (antes «AyG Asesores» salía como «persona»)
            "etiqueta": None if a.get("cliente") else (a.get("persona") or _persona_de_motivo(a.get("motivo")) if str(tipo).startswith("rrhh") else sin_cli),
            "que": que, "porque": porque, "cifra": cifra,
            "umbral": _umbral(catalogo, sufijo),
            "fuente": {"texto": a.get("fuente") or "Alertas del departamento", "url": _primer_enlace(a)},
            # A2: «Ir» al objeto (el correo, la ficha en su pestaña, la subcuenta…) con su verbo y una pantalla de respaldo
            "ir": a.get("ir"), "ir_texto": a.get("ir_texto"), "ir_alt": a.get("ir_alt"),
            "quien": quien, "dueno": resp, "cuando": _cuando(a, ahora), "gravedad": gravedad,
            "orden": orden, "personal": bool(a.get("persona_id")), "requiere": [m for m in [a.get("modulo_origen")] if m],
            "grav_cliente": (v or {}).get("gravedad"),
            "accion": {"tipo": "alerta_lo_tengo", "objeto": a.get("id"), "texto": "Lo tengo", "estado": a.get("estado")}
            if a.get("estado") != "lo_tengo" and resp_alerta == persona["id"] and not a.get("aviso") else None,
            "origen": "reglas",
        })
    return out


def _que_captacion(a, tipo):
    """Captación: el qué depende de lo que dice el motivo (coste, gasto, citas…), no solo del tipo."""
    m = (a.get("motivo") or "").lower()
    hoy = "hoy " if tipo == "pub_critico" else ""
    if "coste por lead" in m or "techo" in m:
        return f"Revisa {hoy}la campaña de {{cliente}}: el coste por lead pasa del techo"
    if "no gastó" in m or "sin saldo" in m or "parad" in m:
        return "Mira hoy por qué la campaña de {cliente} no gastó ayer"
    if "cita" in m:
        return f"Revisa {hoy}con el despacho cómo trabaja los leads de {{cliente}}"
    if "sin leads" in m or "0 leads" in m:
        return f"Revisa {hoy}por qué {{cliente}} no recibe leads"
    return f"Revisa {hoy}la captación de {{cliente}}"


def _persona_de_motivo(m):
    x = re.match(r"^([A-ZÁÉÍÓÚÑ][\wáéíóúñ]+)\s", m or "")
    return x.group(1) if x else None


def de_verdad(persona, verdad_doc, ve_equipo, nombre, ahora):
    """Reglas sobre la verdad única: bloqueo callado (tarea parada > 5 días) y fuga de integración Meta → GoHighLevel."""
    out = []
    for c in (verdad_doc or {}).get("clientes") or []:
        cid = c.get("cliente_id")
        if not cid or not ve_equipo(c):
            continue
        b = c.get("bloqueos") or {}
        if c.get("bloqueo_callado") and b.get("tareas"):
            dias = int(float(b.get("dias_max") or 0))
            out.append({
                "id": f"vd:bloqueo:{cid}", "tipo": "bloqueo_callado", "pantallas": ["produccion", "ficha", "en-rojo"],
                "cliente_id": cid, "cliente": c.get("nombre"),
                "que": f"Desbloquea la tarea parada de {c.get('nombre')}",
                "porque": f"{b['tareas']} {'tarea bloqueada' if b['tareas'] == 1 else 'tareas bloqueadas'} en ClickUp; la más antigua lleva {dias} días sin moverse (más de 5 días es un bloqueo callado).",
                "cifra": f"{dias} días parada", "umbral": None,
                "fuente": {"texto": "Verdad única del cliente (ClickUp)", "url": None},
                # R15a (A2): con el id de la tarea más antigua, el «Ir» llega a su fila en Producción; sin él, a la ficha
                "ir": f"#/produccion/tarea/{b['tarea_id']}" if b.get("tarea_id") else f"#/ficha/{cid}/trabajo",
                "ir_texto": "Abrir la tarea parada" if b.get("tarea_id") else "Ver sus tareas", "ir_alt": f"#/ficha/{cid}/trabajo",
                "quien": "Tú" if c.get("account") == persona["id"] else (nombre(c.get("account")) or "Su account"),
                "dueno": c.get("account"), "grav_cliente": c.get("gravedad"),
                "cuando": "Hoy" if dias > 20 else "Esta semana", "gravedad": "alta" if dias > 20 else "media",
                "orden": (250 if dias > 20 else 180) + min(dias, 40), "personal": False, "requiere": [], "accion": None, "origen": "reglas",
            })
        if c.get("gravedad") == "critico" and c.get("account") == persona["id"]:
            # A2: al account, sus clientes críticos van antes que cualquier otra cosa (la vara es la de la verdad única)
            mot = "; ".join(c.get("motivos") or []) or "La verdad única lo marca como crítico"
            out.append({
                "id": f"vd:critico:{cid}", "tipo": "critico_cliente", "pantallas": ["mi-dia", "ficha", "en-rojo"],
                "cliente_id": cid, "cliente": c.get("nombre"),
                "que": f"Llama hoy a {c.get('nombre')}: es un cliente crítico",
                "porque": f"{mot.rstrip('.')}. Antes de hablar, mira en su ficha qué ha pasado y qué le vas a proponer.",
                "cifra": None, "umbral": "Crítico: la regla de gravedad de la verdad única (la misma en toda la app)",
                "fuente": {"texto": "Verdad única del cliente", "url": None},
                "ir": f"#/ficha/{cid}/resumen", "ir_texto": "Abrir su ficha", "quien": "Tú", "dueno": persona["id"],
                "grav_cliente": "critico", "cuando": "Hoy", "gravedad": "alta", "orden": 345, "personal": False,
                "requiere": [], "accion": None, "origen": "reglas",
            })
        fuga = c.get("fuga_integracion")
        if fuga:
            out.append({
                "id": f"vd:fuga:{cid}", "tipo": "fuga_integracion", "pantallas": ["captacion", "salud-crm", "ficha", "mi-dia"],
                "cliente_id": cid, "cliente": c.get("nombre"),
                "que": f"Revisa hoy la conexión de Meta con GoHighLevel de {c.get('nombre')}",
                "porque": f"En 7 días entraron {c.get('leads_meta_7d')} leads en Meta y solo {c.get('leads_ghl_7d')} llegaron a GoHighLevel: los demás nadie los llama.",
                "cifra": f"{(c.get('leads_meta_7d') or 0) - (c.get('leads_ghl_7d') or 0)} leads sin llegar", "umbral": "Fuga grave: menos de la mitad llega (con 10 o más en 7 días)",
                "fuente": {"texto": "Verdad única (Meta y GoHighLevel)", "url": None}, "ir": f"#/captacion/{cid}", "ir_texto": "Ver su captación",
                "quien": "Tú" if c.get("account") == persona["id"] else (nombre(c.get("account")) or "Su account"),
                "dueno": c.get("account"), "grav_cliente": c.get("gravedad"),
                "cuando": "Hoy", "gravedad": "alta" if fuga == "grave" else "media",
                "orden": 320 if fuga == "grave" else 210, "personal": False, "requiere": [], "accion": None, "origen": "reglas",
            })
    return out


def tabla_fuentes(fuentes_doc, salud_doc, conexiones_doc, ahora):
    """Estado de cada fuente para «Qué hacer»: nombre, estado, hora del último dato bueno, desde cuándo cae, quién lo
    revisa y el paso en lenguaje llano. Sin rutas, llaves ni nombres de fichero."""
    por_id = {f.get("id"): f for f in (fuentes_doc or {}).get("fuentes") or [] if isinstance(f, dict)}
    salud = {}
    for s in (salud_doc or {}).get("fuentes", salud_doc if isinstance(salud_doc, list) else []) or []:
        if isinstance(s, dict) and (s.get("id") or s.get("fuente")):
            salud[s.get("id") or s.get("fuente")] = s
    conex = {c.get("id"): c for c in (conexiones_doc or {}).get("conexiones") or [] if isinstance(c, dict)}
    out = []
    for fid, nombre_f, quien_def, alias in FUENTES:
        f, s = por_id.get(fid) or {}, salud.get(fid) or {}
        if not f and not s:
            continue
        c = conex.get(CONEXION_DE.get(fid)) or {}
        quien = (s.get("quien") or c.get("quien") or quien_def).replace("Jessi", "Yessica")
        estado = s.get("estado") or ("caida" if f.get("caida") else f.get("estado")) or "bien"
        hora = s.get("ultimo_bueno") or f.get("hora")
        desde = s.get("desde") or (f.get("caida") or {}).get("desde")
        hb, hd = _hm(hora), _hm(desde)
        dq, dtexto = dueno_conexion(fid)
        if dq and estado in ("rota", "sin_conectar"):
            quien = dq                                     # una clave que falta o falla: la pone Tomás (no «lo conecta Agus»)
        if dtexto and estado == "sin_conectar":
            paso = f"{nombre_f} sin conectar · {dtexto} · mientras, se usa una muestra manual"
        elif dtexto and estado == "rota":
            paso = f"{nombre_f} no responde (la clave falla) · {dtexto} · mientras, cifras de las {hb}"
        elif estado == "caida":
            paso = f"{nombre_f} caído{f' desde las {hd}' if hd else ''} · lo revisa {quien} · mientras, cifras de las {hb}"
        elif estado == "rota":
            paso = f"{nombre_f} no responde (la clave falla) · lo revisa {quien} · mientras, cifras de las {hb}"
        elif estado == "sin_conectar":
            paso = f"{nombre_f} sin conectar · lo conecta {quien} · mientras, se usa una muestra manual"
        elif estado == "dato_viejo":
            edad = f.get("edad_h")
            paso = f"{nombre_f}: dato de las {hb}{f' (hace {round(edad)} h)' if edad else ''} · lo pone al día {quien} con «Actualizar ahora»"
        elif estado == "a_cero":
            paso = f"{nombre_f} conectada pero sin actividad · mira en {nombre_f} si de verdad no hay movimiento y avisa a {quien}"
        else:
            paso = f"{nombre_f} funciona (dato de las {hb}): si aquí falta, el hueco está en el origen · avisa a {quien}"
        out.append({"id": fid, "nombre": nombre_f, "estado": estado, "ultimo_bueno": hb, "desde": hd, "quien": quien,
                    "paso": s.get("paso") or paso, "alias": alias})
    return out


def de_fuentes(tabla, ve_pantalla):
    """Una pantalla que vive de una fuente caída o vieja lleva su aviso (una sola línea por pantalla)."""
    out = []
    malas = {t["id"]: t for t in tabla if t["estado"] in MALOS}
    for pant, fids in FUENTES_DE_PANTALLA.items():
        if not ve_pantalla(pant):
            continue
        xs = [malas[f] for f in fids if f in malas]
        if not xs:
            continue
        graves = [x for x in xs if x["estado"] in ("caida", "rota")]
        lider = (graves or xs)[0]
        nombres = ", ".join(x["nombre"] for x in xs)
        out.append({
            "id": f"fu:{pant}", "tipo": "fuente", "pantallas": [pant], "cliente_id": None, "cliente": None,
            "que": f"Ojo con las cifras de {lider['nombre']}" if len(xs) == 1 else f"Ojo con las cifras de {len(xs)} fuentes de esta pantalla",
            "porque": " · ".join(x["paso"] for x in xs[:3]),
            "cifra": None, "umbral": None, "fuente": {"texto": f"Estado de las fuentes ({nombres})", "url": None},
            "ir": ("#/ajustes/avisos" if lider["estado"] == "dato_viejo" else "#/ajustes/conexiones") if ve_pantalla("ajustes") else None,
            "ir_texto": "Ver la fuente en Ajustes", "quien": lider["quien"],
            "cuando": "Antes de decidir con estas cifras", "gravedad": "media" if graves else "baja",
            "orden": 190 if graves else 90, "personal": False, "requiere": [], "accion": None, "origen": "reglas",
        })
    return out


def marcar_fuentes(xs, tabla):
    """V2-B (M1, M8): el aviso de una fuente caída o en duda va DENTRO del consejo que vive de ella (no ocupa un sitio).
    SEO con SE Ranking roto: el consejo pasa a «compruébalo en Google antes de tocar nada»."""
    malas = {t["id"]: t for t in tabla if t["estado"] in MALOS}
    for c in xs:
        f = malas.get(FUENTE_DE_TIPO.get(c.get("tipo")))
        if not f:
            continue
        if f["estado"] not in ("rota", "caida", "a_cero"):
            continue                 # un dato de hace unas horas no cambia la decisión: va solo al sello de frescura
        c["dato_en_duda"] = f["paso"]
        if c["tipo"] in ("seo_rojo", "seo_ambar"):
            c["que"] = f"Comprueba en Google las palabras de {c.get('cliente') or 'este cliente'} antes de tocar nada"
            c["porque"] = f"{f['nombre']} está en duda ({f['paso'].split(' · ')[0]}): la caída puede ser suya, no de la web. {c.get('porque') or ''}".strip()
            c["gravedad"] = "media"
        elif f["estado"] in ("caida", "rota"):
            c["porque"] = f"{(c.get('porque') or '').rstrip('.')}. Ojo: {f['paso']}."


def de_conexiones(persona, conexiones_doc, alias_persona):
    """Ajustes: conexiones con aviso o sin clave. En Ajustes para quien la ve; en Mi día solo para su dueño."""
    out = []
    for c in (conexiones_doc or {}).get("conexiones") or []:
        est = c.get("estado")
        if est in (None, "bien"):
            continue
        quien = (c.get("quien") or "").replace("Jessi", "Yessica")
        dq, dtexto = dueno_conexion(c.get("id"))
        if dq and est in ("sin_clave", "aviso"):
            quien = dq                                     # misma regla que Ajustes › Conexiones
        mio = quien and quien == alias_persona
        que = {"sin_clave": f"Pon la clave de {c.get('nombre')}", "aviso": f"Revisa la conexión de {c.get('nombre')}"}.get(est, f"Revisa la conexión de {c.get('nombre')}")
        out.append({
            "id": f"cx:{c.get('id')}", "tipo": "conexion", "pantallas": ["ajustes"] + (["mi-dia"] if mio else []),
            "cliente_id": None, "cliente": None, "que": que,
            "porque": (f"Falta la clave: hasta que esté, {c.get('nombre')} no da datos a la app.{(' ' + dtexto[0].upper() + dtexto[1:] + '.') if dtexto else ''}" if est == "sin_clave"
                       else (c.get("detalle_vivo") or c.get("renovacion") or "Tiene un aviso en la última comprobación.").split(". ")[0][:220]),
            "etiqueta": c.get("nombre"),
            "cifra": f"caduca en {c['dias_para_caducar']} días" if c.get("dias_para_caducar") is not None and c["dias_para_caducar"] < 30 else None,
            "umbral": None, "fuente": {"texto": "Ajustes › Conexiones y caducidad", "url": (c.get("renovar") or {}).get("url")},
            "ir": "#/ajustes/conexiones", "ir_texto": "Abrir la conexión", "quien": "Tú" if mio else (quien or "Tomás"),
            "dueno": persona["id"] if mio else None, "dueno_alias": quien or "Tomás", "cuando": "Esta semana",
            "gravedad": "media", "orden": 160 if est == "aviso" else 140, "personal": False, "requiere": ["ajustes"], "accion": None, "origen": "reglas",
        })
    return out


def de_setters(persona, setters_doc):
    """Setters: solo su fila (recuento) y sus citas, contadas. Nunca un nombre ni un teléfono de lead."""
    out = []
    if not setters_doc:
        return out
    clave = next((s.get("clave") for s in setters_doc.get("setters") or [] if (s.get("alias") or "").lower() == (persona.get("alias") or "").lower()), None)
    if not clave:
        return out
    fila = next((r for r in setters_doc.get("recuento") or [] if r.get("quien") == clave), None)
    if fila and fila.get("llamar_ya"):
        out.append({
            "id": f"st:llamar:{clave}", "tipo": "setter_llamar", "pantallas": ["setters"], "cliente_id": None, "cliente": None,
            "que": f"Llama ya a {pl(fila['llamar_ya'], 'lead', 'leads')} de tu lista, el más nuevo primero",
            "porque": "Primero los que tienen teléfono y, dentro, el más nuevo: el primer intento en menos de 5 minutos es el que más citas agenda.",
            "cifra": f"{fila['llamar_ya']} por llamar", "pestana": {"sesion": "setters.pestana", "id": "llamar", "texto": "Llamar ya"}, "umbral": "Bien con 2 citas agendadas al día o más",
            "fuente": {"texto": "Mi día del setter (GoHighLevel)", "url": (setters_doc.get("enlaces") or {}).get("ghl_oportunidades")},
            "ir": "#/setters", "ir_texto": f"Ver {'el lead' if fila['llamar_ya'] == 1 else 'los ' + str(fila['llamar_ya'])} por llamar", "quien": "Tú", "dueno": persona["id"], "cuando": "Hoy", "gravedad": "alta", "orden": 330, "personal": True,
            "requiere": ["setters"], "accion": None, "origen": "reglas",
        })
    sin_conf = [c for c in setters_doc.get("citas") or [] if c.get("setter") == clave and not c.get("confirmada_tel")]
    if sin_conf:
        dias = sorted({re.sub(r"^el\s+", "", c.get("dia")) for c in sin_conf if c.get("dia")})
        out.append({
            "id": f"st:citas:{clave}", "tipo": "setter_citas", "pantallas": ["setters"], "cliente_id": None, "cliente": None,
            "que": f"Confirma por teléfono {'tu cita' if len(sin_conf) == 1 else f'tus {len(sin_conf)} citas'}{(' del ' + ' y el '.join(dias)) if dias else ''}",
            "pestana": {"sesion": "setters.pestana", "id": "citas", "texto": "Confirmar"},
            "porque": "Una cita confirmada por teléfono el día antes falla mucho menos que una que solo tiene el correo automático.",
            "cifra": f"{len(sin_conf)} sin confirmar", "umbral": "Bien desde el 80 % de asistencia; vigilar del 70 al 79 %",
            "fuente": {"texto": "Calendario de GoHighLevel", "url": (setters_doc.get("enlaces") or {}).get("ghl_calendario")},
            "ir": "#/setters", "ir_texto": "Ver la cita por confirmar" if len(sin_conf) == 1 else f"Ver las {len(sin_conf)} citas por confirmar", "quien": "Tú", "dueno": persona["id"], "cuando": "Hoy", "gravedad": "media", "orden": 260, "personal": True,
            "requiere": ["setters"], "accion": None, "origen": "reglas",
        })
    if any("xtensi" in (a or "") for a in setters_doc.get("avisos") or []):
        out.append({
            "id": f"st:ext:{clave}", "tipo": "setter_extension", "pantallas": ["setters"], "cliente_id": None, "cliente": None,
            "que": "Pide a Tomás que confirme tu extensión de Zadarma",
            "porque": "Sin extensión confirmada, tus llamadas salen «sin dato» en el marcador y no cuentan.",
            "cifra": None, "umbral": None, "fuente": {"texto": "Zadarma (centralita)", "url": (setters_doc.get("enlaces") or {}).get("zadarma_centralita")},
            "ir": "#/setters", "quien": "Tú", "dueno": persona["id"], "cuando": "Esta semana", "gravedad": "baja", "orden": 120, "personal": True,
            "requiere": ["setters"], "accion": None, "origen": "reglas",
        })
    return out


def _fecha(t):
    try:
        return datetime.fromisoformat(str(t).replace("Z", "")[:19])
    except (TypeError, ValueError):
        return None


def _base(id_, tipo, pantallas, que, porque, **k):
    c = {"id": id_, "tipo": tipo, "pantallas": pantallas, "cliente_id": None, "cliente": None, "que": que, "porque": porque,
         "cifra": None, "umbral": None, "fuente": {"texto": "La app", "url": None}, "ir": None, "ir_texto": None, "quien": "Tú",
         "dueno": None, "cuando": "Hoy", "gravedad": "media", "orden": 200, "personal": False, "requiere": [], "accion": None,
         "origen": "reglas"}
    c.update(k)
    return c


def de_visto(persona, verdad_doc, vistos, ve_equipo):
    """Proyectos (Coti): los críticos de la verdad única que aún no tienen su «Visto» en En rojo (A3: lo suyo, no redes)."""
    if "proyectos" not in (persona.get("puestos") or []):
        return []
    out = []
    for c in (verdad_doc or {}).get("clientes") or []:
        cid = c.get("cliente_id")
        if c.get("gravedad") != "critico" or not cid or cid in (vistos or set()):
            continue
        out.append(_base(f"vd:visto:{cid}", "visto_critico", ["mi-dia", "en-rojo"],
                         f"Da tu «Visto» al plan de {c.get('nombre')}: es un cliente crítico",
                         f"{'; '.join(c.get('motivos') or ['Cliente crítico']).rstrip('.')}. Antes de que su account hable con el cliente, tu «Visto» con números y plan.",
                         cliente_id=cid, cliente=c.get("nombre"), dueno=persona["id"], grav_cliente="critico",
                         umbral="Crítico: la regla de gravedad de la verdad única", fuente={"texto": "Verdad única y En rojo", "url": None},
                         ir=f"#/en-rojo/{cid}", ir_texto="Abrir y marcar «Visto»", gravedad="alta", orden=335, requiere=["en-rojo"]))
    return out


def de_produccion(persona, prod_doc, ahora):
    """Producción: su cola (devuelta sin tocar, vencida más antigua, para hoy) y, al account, la revisión que más espera."""
    out = []
    if not prod_doc:
        return out
    yo = persona["id"]
    # nada de sueldos, nóminas ni claves en un consejo (aunque la tarea sea de RRHH y quien la lleva pueda verlas)
    sensible = re.compile(r"(?i)salari|sueldo|n[oó]mina|retribuci|contrase|password|credencial|\bclaves?\b")
    cola = [r for r in prod_doc.get("cola") or [] if r.get("persona_id") == yo and not sensible.search(r.get("tarea") or "")]
    pant = ["produccion", "mi-dia"]
    ir = lambda r: f"#/produccion/tarea/{r['id']}"
    def nom(r):
        return r.get("cliente") if r.get("cli") else None          # tareas internas: sin cliente (C17)
    for r in sorted([r for r in cola if r.get("devuelta") and r.get("grupo") != "revision"], key=lambda r: -(r.get("dias_estado") or 0)):
        out.append(_base(f"pr:dev:{r['id']}", "prod_devuelta", pant, f"Corrige la pieza que te devolvieron: «{r['tarea'][:70]}»",
                         f"Te la devolvieron con cambios{(' (' + nom(r) + ')') if nom(r) else ''} y sigue sin moverse. Lo devuelto va antes que lo nuevo.",
                         cliente=nom(r), etiqueta=None if nom(r) else r["tarea"][:40], dueno=yo, ir=ir(r), ir_texto="Abrir la pieza",
                         fuente={"texto": "Tareas de ClickUp (Producción)", "url": None}, gravedad="alta", orden=300, requiere=["produccion"]))
    venc = sorted([r for r in cola if r.get("grupo") == "vencida"], key=lambda r: r.get("vence") or "")
    for r in venc:
        d = _fecha(r.get("vence"))
        dias = (ahora.date() - d.date()).days if d else None
        out.append(_base(f"pr:venc:{r['id']}", "prod_vencida", pant, f"Entrega hoy «{r['tarea'][:70]}»",
                         f"Venció {_dia(d, ahora) if d else 'hace días'}{(' · ' + nom(r)) if nom(r) else ''}. Si no puedes, avisa hoy con una fecha nueva.",
                         cliente=nom(r), etiqueta=None if nom(r) else r["tarea"][:40], dueno=yo, cifra=pl(dias, "día vencida", "días vencida") if dias else None,
                         ir=ir(r), ir_texto="Abrir la pieza", fuente={"texto": "Tareas de ClickUp (Producción)", "url": None},
                         cuando=vencida_txt(d, ahora) if d and dias and dias > 0 else "Hoy",
                         gravedad="alta", orden=270 + min(dias or 0, 30), requiere=["produccion"]))
    for r in [r for r in cola if r.get("grupo") == "hoy"]:
        out.append(_base(f"pr:hoy:{r['id']}", "prod_hoy", pant, f"Termina hoy «{r['tarea'][:70]}»",
                         f"Vence hoy{(' · ' + nom(r)) if nom(r) else ''}.", cliente=nom(r), etiqueta=None if nom(r) else r["tarea"][:40],
                         dueno=yo, ir=ir(r), ir_texto="Abrir la pieza", fuente={"texto": "Tareas de ClickUp (Producción)", "url": None},
                         cuando="Vence hoy", orden=215, requiere=["produccion"]))
    revs = sorted([r for r in prod_doc.get("revisiones") or [] if r.get("account_id") == yo and r.get("revisa") == "account"
                   and not sensible.search(r.get("tarea") or "")
                   and r.get("mas48") and (r.get("dias") or 0) <= 30], key=lambda r: -(r.get("dias") or 0))
    for r in revs:
        dias = int(r.get("dias") or 0)
        out.append(_base(f"pr:rev:{r['id']}", "prod_revision", pant, f"Revisa la pieza que más espera: «{r['tarea'][:60]}»",
                         f"Lleva {pl(dias, 'día', 'días')} esperando tu revisión. Más de 48 h parada retrasa la entrega al cliente.",
                         cliente_id=r.get("cliente_id"), dueno=yo, cifra=pl(dias, "día esperando", "días esperando"),
                         umbral="Revisión del account: antes de 48 h", ir=ir(r), ir_texto="Abrir la pieza",
                         fuente={"texto": "Tareas de ClickUp (Producción › Por revisar)", "url": None},
                         gravedad="media", orden=190 + min(dias, 30), requiere=["produccion"]))
    return out


def de_outreach(persona, out_doc, hechas, ahora):
    """Outreach: respuestas por clasificar (la más antigua primero) y positivas sin dueño de más de 4 h."""
    if not out_doc or not (set(persona.get("puestos") or []) & {"outreach"}):
        return []
    clasif, asign = hechas or (set(), set())
    resp = [r for r in out_doc.get("respuestas") or [] if r.get("id")]
    sin = sorted([r for r in resp if r.get("clase") in (None, "", "sin clasificar") and r["id"] not in clasif], key=lambda r: r.get("fecha") or "")
    out = []
    if sin:
        r0 = sin[0]
        d = _fecha(r0.get("fecha"))
        out.append(_base("or:clasificar", "outreach_clasificar", ["prospeccion", "mi-dia"],
                         "Clasifica " + ("la respuesta sin clasificar" if len(sin) == 1 else f"las {len(sin)} respuestas sin clasificar, la más antigua primero"),
                         f"La más antigua llegó {_dia(d, ahora) if d else 'hace días'} ({r0.get('campana') or 'sin campaña'}). Clasificada, la positiva pasa a su dueño en el día; sin clasificar, se enfría.",
                         dueno=persona["id"], cifra=pl(len(sin), "sin clasificar", "sin clasificar"),
                         umbral="Respuesta positiva: con dueño antes de 4 h", ir="#/prospeccion", ir_texto="Ver las respuestas sin clasificar",
                         pestana={"sesion": "prospeccion.pestana", "id": r0.get("frente") or "clientes",
                                  "texto": "Campañas de RO" if r0.get("frente") == "ro" else "Campañas de clientes"},
                         fuente={"texto": "Snov.io y hoja de outreach", "url": None}, gravedad="alta" if len(sin) > 20 else "media",
                         orden=300 + min(len(sin), 40), requiere=["prospeccion"]))
    pos = [r for r in resp if r.get("clase") == "positiva" and not r.get("dueno") and r["id"] not in asign
           and _fecha(r.get("fecha")) and (ahora - _fecha(r["fecha"])).total_seconds() > 4 * 3600]
    if pos:
        out.append(_base("or:positiva", "outreach_positiva", ["prospeccion", "mi-dia"],
                         f"Pon dueño hoy a {'la respuesta positiva' if len(pos) == 1 else f'las {len(pos)} respuestas positivas'} que esperan más de 4 h",
                         "Una respuesta positiva sin nadie que la llame en el día se pierde.", dueno=persona["id"],
                         cifra=pl(len(pos), "positiva sin dueño", "positivas sin dueño"), ir="#/prospeccion", ir_texto="Ver las respuestas positivas",
                         fuente={"texto": "Snov.io y hoja de outreach", "url": None}, gravedad="alta", orden=340, requiere=["prospeccion"]))
    return out


def _nombre_lead(x):
    n = (x.get("nombre_m") or "").split("·")[0].strip()
    return n if x.get("nombre_completo") and n and "···" not in n else None


def de_ventas(persona, v_doc, ahora):
    """Ventas de RO (quien vende): reunión pasada sin resultado, contrato enviado sin firmar y propuesta sin abrir (72 h)."""
    if not v_doc or "ventas_ro" not in (persona.get("puestos") or []):
        return []
    out, pant = [], ["ventas-ro", "mi-dia"]
    hoy_p = {"sesion": "ventas-ro.pestana", "id": "hoy", "texto": "Hoy"}
    for x in v_doc.get("hoy") or []:
        if not x.get("pasada") or x.get("resultado") not in (None, "", "sin_marcar"):
            continue
        d = _fecha(x.get("cuando"))
        n = _nombre_lead(x)
        out.append(_base(f"vt:marcar:{x.get('id')}", "ventas_sin_marcar", pant,
                         f"Marca cómo fue la reunión con {n or 'el lead'}",
                         f"Fue {_dia(d, ahora) if d else ''}{(' a las ' + d.strftime('%H:%M')) if d else ''} y sigue sin resultado: sin marcar, la asistencia y el coste por cita salen mal.",
                         etiqueta=n, dueno=persona["id"], ir="#/ventas-ro", ir_texto="Ver las reuniones sin marcar", pestana=hoy_p,
                         fuente={"texto": "GoHighLevel (Ventas de RO)", "url": x.get("ghl")}, gravedad="media", orden=285))
    for x in sorted([c for c in v_doc.get("contratos") or [] if (c.get("dias") or 0) >= 3], key=lambda c: -(c.get("dias") or 0)):
        n = _nombre_lead(x)
        out.append(_base(f"vt:contrato:{x.get('id')}", "ventas_contrato", pant,
                         f"Llama hoy a {n or 'quien tiene el contrato'}: el contrato lleva {pl(x['dias'], 'día', 'días')} sin firmar",
                         "Un contrato enviado y sin firmar a los 3 días se enfría: una llamada corta para resolver la duda que lo frena.",
                         etiqueta=n, dueno=persona["id"], cifra=pl(x["dias"], "día sin firmar", "días sin firmar"), ir="#/ventas-ro",
                         ir_texto="Ver las firmas pendientes", pestana=hoy_p, fuente={"texto": "GoHighLevel (Contrato enviado)", "url": x.get("ghl")},
                         gravedad="alta", orden=300 + min(x["dias"], 20)))
    for x in sorted([c for c in v_doc.get("propuestas") or [] if not c.get("abierta") and (c.get("dias") or 0) >= 3], key=lambda c: -(c.get("dias") or 0)):
        n = _nombre_lead(x)
        out.append(_base(f"vt:propuesta:{x.get('id')}", "ventas_propuesta", pant,
                         f"Llama a {n or 'quien tiene la propuesta'}: no ha abierto la propuesta en {pl(x['dias'], 'día', 'días')}",
                         "Una propuesta sin abrir a las 72 h casi nunca se firma sola: llama y pregunta si le llegó.",
                         etiqueta=n, dueno=persona["id"], cifra=pl(x["dias"], "día sin abrir", "días sin abrir"),
                         umbral="Propuesta: abierta antes de 72 h", ir="#/ventas-ro", ir_texto="Ver las propuestas sin abrir", pestana=hoy_p,
                         fuente={"texto": "GoHighLevel (Propuesta enviada)", "url": x.get("ghl")}, gravedad="media",
                         orden=250 + min(x["dias"], 20)))
    return out


def candidatos(persona, datos, nombre, ve_pantalla, ve_equipo, ahora=None):
    """Todos los candidatos de una persona (sin cortar a 3; eso lo hace quien sirve, pantalla a pantalla)."""
    ahora = ahora or ahora_madrid()
    tabla = tabla_fuentes(datos.get("fuentes"), datos.get("salud"), datos.get("conexiones"), ahora)
    vidx = {c.get("cliente_id"): c for c in (datos.get("verdad") or {}).get("clientes") or [] if c.get("cliente_id")}
    xs = (de_alertas(persona, datos.get("alertas"), datos.get("catalogo"), nombre, ahora, vidx)
          + de_verdad(persona, datos.get("verdad"), ve_equipo, nombre, ahora)
          + de_fuentes(tabla, ve_pantalla)
          + de_conexiones(persona, datos.get("conexiones"), persona.get("alias"))
          + de_setters(persona, datos.get("setters"))
          + de_produccion(persona, datos.get("produccion"), ahora)
          + de_ventas(persona, datos.get("ventas"), ahora))
    # el crítico de la alerta del account y el de la verdad única son lo mismo: se queda la alerta (lleva «Lo tengo»)
    con_alerta = {c.get("cliente_id") for c in xs if c.get("tipo") == "acc_critico"}
    xs = [c for c in xs if not (c.get("tipo") == "critico_cliente" and c.get("cliente_id") in con_alerta)]
    marcar_fuentes(xs, tabla)
    for c in xs:          # A2: si quien mira no ve la pantalla del objeto, «Ir» va a la de respaldo (o no sale)
        mod = lambda r: (r or "").removeprefix("#/").split("/")[0]
        if c.get("ir") and not ve_pantalla(mod(c["ir"])):
            c["ir"], c["ir_texto"] = (c.get("ir_alt"), None) if c.get("ir_alt") and ve_pantalla(mod(c["ir_alt"])) else (None, None)
        c.pop("ir_alt", None)
        if not c.get("ir"):
            c["ir_texto"] = None
    xs.sort(key=lambda c: -c["orden"])
    return xs, tabla


COSA_DE_TIPO = {"conexion": ("conexión", "conexiones"), "dir_decision": ("decisión", "decisiones"),
                "ventas_sin_marcar": ("reunión", "reuniones"), "ventas_contrato": ("contrato", "contratos"),
                "ventas_propuesta": ("propuesta", "propuestas"), "acc_llamadas": ("aviso", "avisos"), "acc_config": ("aviso", "avisos")}


def _cosa(c):
    """B6: el sustantivo de «Lo mismo en N … más» según lo que se agrupa (antes, todo lo que no era cliente eran «personas»)."""
    t = c.get("tipo") or ""
    if t in COSA_DE_TIPO:
        return COSA_DE_TIPO[t]
    if t.startswith("prod_"):
        return ("pieza", "piezas")
    if c.get("cliente_id") or (c.get("cliente") and not t.startswith("rrhh")):
        return ("cliente", "clientes")
    if t.startswith("rrhh"):
        return ("persona", "personas")
    return ("caso", "casos")


def retrasos(tabla, pantalla, ve_fuente=lambda f: True):
    """Fuentes caídas, viejas o sin conectar de las que vive esta pantalla (para el sello del bloque, no un consejo)."""
    malas = {t["id"]: t for t in tabla or [] if t.get("estado") in MALOS}
    return [{k: malas[f].get(k) for k in ("id", "nombre", "estado", "ultimo_bueno", "quien", "paso")}
            for f in FUENTES_DE_PANTALLA.get(pantalla, []) if f in malas and ve_fuente(f)]


def elegir(cands, pantalla, cliente_id=None, maximo=3):
    """Los de esta pantalla (y de este cliente si lo hay), agrupados por tipo: el más grave de cada tipo y «y N más»."""
    # V2-B (M1): el aviso de fuentes ya no ocupa un consejo: va al sello del bloque (retrasos()) o dentro del consejo afectado
    xs = [c for c in cands if pantalla in c.get("pantallas", []) and c.get("tipo") != "fuente"]
    if cliente_id:
        xs = [c for c in xs if c.get("cliente_id") == cliente_id]
    xs.sort(key=lambda c: -c["orden"])
    grupos, orden = {}, []
    for c in xs:
        k = c["tipo"]
        if k not in grupos:
            grupos[k] = [c]
            orden.append(k)
        else:
            grupos[k].append(c)
    out = []
    for k in orden[:maximo]:
        g = grupos[k]
        c = dict(g[0])
        if len(g) > 1 and str(k).startswith("prod_"):
            # piezas de la cola: no se mezclan nombres de clientes y de tareas; basta cuántas más hay
            c["mas"] = len(g) - 1
            c["porque"] = f"{c['porque'].rstrip('.')}. Y {pl(len(g) - 1, 'pieza más', 'piezas más')} así en tu cola."
        elif len(g) > 1:
            primero = c.get("cliente") or c.get("etiqueta")
            otros = []
            for x in g[1:]:
                n = x.get("cliente") or x.get("etiqueta")
                if n and n != primero and n not in otros:
                    otros.append(n)
            c["mas"] = len(otros) or len(g) - 1
            if otros:
                g = [g[0]] + [None] * len(otros)       # «N más» = nombres distintos, no filas
                lista = ", ".join(otros[:3]) + (f" y {len(otros) - 3} más" if len(otros) > 3 else "")
                cosa = _cosa(g[0])
                c["porque"] = f"{c['porque'].rstrip('.')}. Lo mismo en {len(g) - 1} {cosa[0] if len(g) == 2 else cosa[1]} más: {lista}."
            elif not primero:
                c["porque"] = f"{c['porque'].rstrip('.')}. Y {len(g) - 1} más del mismo tipo."
        out.append(c)
    return out
