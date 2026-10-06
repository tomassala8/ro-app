#!/usr/bin/env python3
"""
generar_alertas.py · motor único de alertas por departamento (carril N4, 2-oct-2026).

NO RECALCULA NADA. Lee lo que ya calcula cada módulo (data/*/…json, la verdad única) y lo convierte en alertas con:
departamento · dueño (la silla del cliente en asignaciones, o el jefe del departamento si no hay) · motivo en una frase ·
desde cuándo · plazo según su regla · gravedad · «Abrir en …» (herramienta) · «Ir» (pantalla de la app) · escalado
(dueño → jefe del departamento → Mili; si el dueño ya es Mili, sube a Tomás).

Estados (nueva · vista · lo tengo · resuelta · no aplica) = acciones del módulo «alertas» en local.db (cola simulada, con
rastro). Se leen aquí en SOLO LECTURA para: parar el escalado con «Lo tengo», comprobar «Resuelta» con el dato
siguiente (si la alerta sigue en el dato nuevo → «reabierta»; si ya no sale → «comprobada») y hacer el resumen diario.

Escribe:
  data/alertas/alertas.json   todas (solo dirección y operaciones, reglas_permisos.json → datos_de_modulo)
  data/alertas/p_<id>.json    las de cada persona (solo_propio): las suyas, las de su departamento si es jefe; Mili y
                              Tomás todas. Lleva su «resumen diario» (texto listo para notificación) y el bloque
                              «mi_dia» que lee Mi día.
  data/alertas/_estado/estado_alertas.json   (L-29; antes fuentes_alertas/) primera vez vista de cada alerta (para «desde» y escalado) y cerradas (no se sirve)

Dinero: solo en claves que el servidor recorta (gasto_*, impagado_*); los textos van sin importes. Leads: solo recuentos,
nunca nombres, teléfonos ni enlaces a un contacto. Uso:  python3 fuentes_alertas/generar_alertas.py
"""
import json
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

AQUI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AQUI))
import permisos as P  # noqa: E402
import escalado as ESC  # noqa: E402  (3-oct: orden de escalado oficial, data/escalado.json)

DATA = AQUI / "data"
# Pruebas (fuentes_alertas/probar_alertas.py): RO_DB = copia de la base, RO_ALERTAS_SALIDA/_ESTADO = carpeta temporal,
# RO_ALERTAS_AHORA = «AAAA-MM-DD HH:MM» para simular que pasa el tiempo (escalado). Sin variables: lo de siempre.
SALIDA = Path(os.environ.get("RO_ALERTAS_SALIDA") or DATA / "alertas")
# L-29: el estado vive con los datos (data/alertas/_estado/), no en el repo. Antes: fuentes_alertas/estado_alertas.json.
ESTADO_ANTIGUO = Path(__file__).resolve().parent / "estado_alertas.json"
ESTADO = Path(os.environ.get("RO_ALERTAS_ESTADO") or DATA / "alertas" / "_estado" / "estado_alertas.json")
DB = Path(os.environ.get("RO_DB") or AQUI / "local.db")
# A8 (2-oct noche): alertas de la salud de conexiones (despliegue/salud_conexiones.py → «alertas», formato N4).
SALUD = Path(os.environ.get("RO_ALERTAS_SALUD") or DATA / "conexiones" / "salud.json")
POSPONER_MAX_DIAS = 31          # «Posponer» como mucho un mes; más allá, «No aplica» con motivo
MADRID = ZoneInfo("Europe/Madrid")
AHORA = (datetime.fromisoformat(os.environ["RO_ALERTAS_AHORA"]) if os.environ.get("RO_ALERTAS_AHORA")
         else datetime.now(MADRID).replace(tzinfo=None, second=0, microsecond=0))
HOY = AHORA.date()
FMT = "%Y-%m-%d %H:%M"


def leer(rel):
    try:
        return json.loads((DATA / f"{rel}.json").read_text())
    except Exception:
        return None


def fecha(s):
    """«2026-09-18», «2026-09-18 12:30», «2026-10-04T07:16:00Z» → datetime local (naive) o None."""
    if not s:
        return None
    s = str(s)
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s[:-1]).replace(tzinfo=ZoneInfo("UTC")).astimezone(MADRID).replace(tzinfo=None)
        if len(s) == 10:
            return datetime.fromisoformat(s + " 09:00")
        return datetime.fromisoformat(s[:16].replace("T", " "))
    except Exception:
        return None


def f2s(d):
    return d.strftime(FMT) if d else None


def pl(n, uno, varios=None):
    return f"{n} {uno if n == 1 else (varios or uno + 's')}"


def plurales(t):
    """«1 ticket(s)» → «1 ticket», «3 ticket(s)» → «3 tickets» (textos que vienen de otros módulos)."""
    if not isinstance(t, str):
        return t
    t = re.sub(r"\b1 (\w+)\(s\)", r"1 \1", t)
    t = re.sub(r"(\d+) (\w+)\(s\)", r"\1 \2s", t)
    return t.replace("(s)", "s")


def miles(n):
    return f"{n:,}".replace(",", ".")


# =================================================================== departamentos y reglas
DEPTOS = {
    "web": {"nombre": "Web", "jefe": "jeronimo", "silla": "web", "icono": "mundo_web", "jefe_origen": "jefatura de SEO, web incluida (reglas_permisos.json → jefe_de_puesto)"},
    "seo": {"nombre": "SEO", "jefe": "jeronimo", "silla": "seo", "icono": "globe", "jefe_origen": "jefatura de SEO"},
    "crm": {"nombre": "CRM", "jefe": "yessica", "silla": "crm", "icono": "base", "jefe_origen": "jefa de CRM y outreach"},
    "publicidad": {"nombre": "Publicidad", "jefe": "valeria", "silla": "trafficker", "icono": "target", "jefe_origen": "jefa de publicidad"},
    "redes": {"nombre": "Redes", "jefe": "constanza", "silla": "redes", "icono": "heart", "jefe_origen": "no hay jefa de redes: sube a Coti (D-61)"},
    "accounts": {"nombre": "Accounts", "jefe": "mili", "silla": "account", "icono": "persona", "jefe_origen": "dirección de operaciones"},
    "altas": {"nombre": "Altas", "jefe": "mili", "dueno_fijo": "agustina", "icono": "rocket", "jefe_origen": "Agus es dueña de las altas hasta el día 90; su jefa es Mili"},
    "administracion": {"nombre": "Administración", "jefe": "tomas", "dueno_fijo": "sofia", "icono": "euro", "jefe_origen": "Sofía cobra; decide Tomás"},
    "rrhh": {"nombre": "RRHH", "jefe": "tomas", "dueno_fijo": "cecilia", "icono": "eq", "jefe_origen": "Cecilia (RRHH) y Tomás"},
    "direccion": {"nombre": "Dirección", "jefe": "tomas", "dueno_fijo": "tomas", "icono": "flag", "jefe_origen": "Tomás (48 h) y Coti (24 h)"},
    # A8: conexiones técnicas (las de la llave de Tomás van a «direccion»); el dueño lo pone la salud de conexiones.
    "conexiones": {"nombre": "Conexiones", "jefe": "mili", "icono": "plug", "jefe_origen": "salud de conexiones: el dueño de la llave; sube a su jefe y a Tomás"},
}
# N9 (altas): el jefe de cada departamento lo manda data/departamentos.json (Ajustes › Altas y bajas › Departamentos,
# solo Tomás). DEPTOS queda como respaldo si el fichero falta o está roto; el icono sigue aquí.
try:
    _DEP_AJ = json.loads((AQUI / "data" / "departamentos.json").read_text()).get("departamentos") or {}
except Exception:
    _DEP_AJ = {}
for _d, _x in DEPTOS.items():
    _a = _DEP_AJ.get(_d) or {}
    if _a.get("jefe"):
        _x["jefe"] = _a["jefe"]
        if _a.get("jefe_origen"):
            _x["jefe_origen"] = _a["jefe_origen"]
    if _a.get("pendiente"):
        _x["pendiente"] = _a["pendiente"]
ORDEN_DEP = list(DEPTOS)

# plazo_h: horas desde que la app la ve por primera vez hasta que vence. Pasado el plazo sin «Lo tengo» → jefe; pasado
# otro plazo igual → Mili. gravedad: alta (rojo, actúa) · media (ámbar, vigila) · baja (gris, aviso).
REGLAS = [
    # web
    {"id": "web_caida", "dep": "web", "titulo": "Web caída", "gravedad": "alta", "plazo_h": 4, "modulo": "seo-web", "ir": "seo-web",
     "regla": "La portada no responde desde la IP de RO (código, https o dominio).", "comprueba": "La siguiente comprobación del monitor responde 200.", "fuente": "Monitor de webs (SEO, ficha y webs)"},
    {"id": "web_spam", "dep": "web", "titulo": "Enlaces de spam en la web", "gravedad": "alta", "plazo_h": 24, "modulo": "seo-web", "ir": "seo-web",
     "regla": "Palabras de apuestas o casinos inyectadas en la portada (web hackeada).", "comprueba": "La portada deja de tener esas palabras en la siguiente comprobación.", "fuente": "Monitor de webs"},
    {"id": "web_certificado", "dep": "web", "titulo": "Certificado que caduca", "gravedad": "media", "plazo_h": 72, "modulo": "seo-web", "ir": "seo-web",
     "regla": "El certificado de seguridad caduca en 30 días o menos (alta si quedan 7 o menos).", "comprueba": "La fecha de caducidad pasa a más de 30 días.", "fuente": "Monitor de webs"},
    {"id": "web_lenta", "dep": "web", "titulo": "Web lenta", "gravedad": "baja", "plazo_h": 168, "modulo": "seo-web", "ir": "seo-web",
     "regla": "La portada tarda más de 5 s en servirse (la velocidad real llega con PageSpeed).", "comprueba": "Baja de 5 s en la siguiente comprobación.", "fuente": "Monitor de webs"},
    {"id": "web_medicion", "dep": "web", "titulo": "Fallo de medición de Analytics", "gravedad": "media", "plazo_h": 72, "modulo": "seo-web", "ir": "seo-web",
     "regla": "La propiedad de Analytics no mide (banner de cookies, etiqueta o propiedad equivocada).", "comprueba": "Vuelven las sesiones en Analytics.", "fuente": "Revisión de Analytics del 2-oct (monitor de webs)"},
    # Modular DS (N5, fuentes_modular/generar_modular.py → data/modular/webs.json › alertas): cuatro reglas, dueño = persona de web del cliente
    {"id": "modular_caida", "dep": "web", "titulo": "Web caída (Modular)", "gravedad": "alta", "plazo_h": 4, "modulo": "seo-web", "ir": "seo-web/webs/{cid}",
     "regla": "El monitor de Modular DS da la web por caída. Alta si tampoco responde desde la IP de RO; media si desde RO responde (monitor de Modular mal apuntado o bloqueo).", "comprueba": "Modular la vuelve a ver arriba en la siguiente lectura (cada hora).", "fuente": "Modular DS (gestor de webs)"},
    {"id": "modular_copia", "dep": "web", "titulo": "Copia de seguridad atrasada (Modular)", "gravedad": "media", "plazo_h": 24, "modulo": "seo-web", "ir": "seo-web/webs/{cid}",
     "regla": "La última copia buena tiene más de 2 días (alta desde 7 días o si no hay ninguna).", "comprueba": "Modular tiene una copia buena de menos de 2 días.", "fuente": "Modular DS (gestor de webs)"},
    {"id": "modular_vulnerabilidad", "dep": "web", "titulo": "Vulnerabilidad crítica en la web (Modular)", "gravedad": "alta", "plazo_h": 24, "modulo": "seo-web", "ir": "seo-web/webs/{cid}",
     "regla": "Modular DS ve al menos una vulnerabilidad de gravedad crítica en WordPress, un plugin o un tema.", "comprueba": "Modular deja de verla (componente actualizado o quitado).", "fuente": "Modular DS (gestor de webs)"},
    {"id": "modular_certificado", "dep": "web", "titulo": "Certificado a punto de caducar (Modular)", "gravedad": "media", "plazo_h": 72, "modulo": "seo-web", "ir": "seo-web/webs/{cid}",
     "regla": "El certificado que vigila Modular caduca en menos de 15 días (alta con 3 o menos). Si Modular no lo vigila, avisa el monitor de RO (regla «Certificado que caduca»).", "comprueba": "La fecha de caducidad pasa de 14 días.", "fuente": "Modular DS (gestor de webs)"},
    {"id": "web_hosting", "dep": "web", "titulo": "Incidencia del hosting (Hostinger)", "gravedad": "media", "plazo_h": 24, "modulo": "seo-web", "ir": "seo-web",
     "regla": "Hostinger avisa de web suspendida, certificado caducado o a punto de caducar (14 días; 3 = alta) o dominio del cliente que caduca (30 días; 7 = alta).", "comprueba": "La siguiente lectura de Hostinger deja de avisarlo.", "fuente": "Hostinger (API, solo lectura)"},
    # SEO
    {"id": "seo_rojo", "dep": "seo", "titulo": "Posiciones fuera del top 10 o caída de clics", "gravedad": "alta", "plazo_h": 72, "modulo": "seo-web", "ir": "seo-web/{cid}",
     "regla": "Una palabra del informe sale del top 10 (confirmado dos días) o los clics caen semana contra semana.", "comprueba": "El semáforo SEO del cliente deja de estar en rojo.", "fuente": "SEO (SE Ranking y Search Console)"},
    {"id": "seo_ambar", "dep": "seo", "titulo": "SEO a vigilar", "gravedad": "media", "plazo_h": 168, "modulo": "seo-web", "ir": "seo-web/{cid}",
     "regla": "Palabras que no aparecen en la comprobación, ninguna en el top 10 o clics a la baja.", "comprueba": "El semáforo SEO pasa a verde.", "fuente": "SEO (SE Ranking y Search Console)"},
    # Ficha de Google (Google Business Profile · fuentes_gbp/generar_gbp.py → data/gbp/gbp.json › alertas). Dueño: SEO/ficha de
    # Google del cliente (silla «seo»); copia al account del cliente (campo «copia_a»: la ve y le llega, sin ser dueño).
    {"id": "gbp_resena", "dep": "seo", "titulo": "Reseña de 1-3 estrellas sin responder (ficha de Google)", "gravedad": "alta", "plazo_h": 24, "modulo": "seo-web", "ir": "seo-web/{cid}",
     "regla": "Reseña de 1, 2 o 3 estrellas de los últimos 60 días sin respuesta del despacho. Alta pasadas 24 h; media antes.", "comprueba": "La siguiente lectura de Google trae la reseña respondida.", "fuente": "Google Business Profile (API, solo lectura)"},
    {"id": "gbp_caida", "dep": "seo", "titulo": "Caída de llamadas o rutas desde la ficha de Google", "gravedad": "media", "plazo_h": 72, "modulo": "seo-web", "ir": "seo-web/{cid}",
     "regla": "Llamadas o rutas desde la ficha caen más de un 30 % semana contra semana (alta desde un 60 %), con al menos 8 la semana anterior.", "comprueba": "La semana siguiente vuelve a menos de un 30 % de caída.", "fuente": "Google Business Profile (API, solo lectura)"},
    {"id": "gbp_perfil", "dep": "seo", "titulo": "Ficha de Google suspendida, sin control o cambiada por Google", "gravedad": "alta", "plazo_h": 24, "modulo": "seo-web", "ir": "seo-web/{cid}",
     "regla": "Google da la ficha por suspendida o deshabilitada (alta), sin control del negocio, marcada como cerrada, o ha cambiado datos por su cuenta (media).", "comprueba": "La siguiente lectura de Google la da en regla y sin cambios suyos.", "fuente": "Google Business Profile (API, solo lectura)"},
    # CRM
    {"id": "crm_sin_tocar", "dep": "crm", "titulo": "Leads sin tocar más de 24 h", "gravedad": "alta", "plazo_h": 24, "modulo": "salud-crm", "ir": "salud-crm/{sub}",
     "regla": "Leads de formulario o anuncio sin ningún intento apuntado en GoHighLevel pasadas 24 h.", "comprueba": "El recuento de leads sin tocar del cliente baja a 0.", "fuente": "Salud del CRM (GoHighLevel)"},
    {"id": "crm_citas_sin_estado", "dep": "crm", "titulo": "Citas sin estado", "gravedad": "media", "plazo_h": 48, "modulo": "salud-crm", "ir": "salud-crm/{sub}",
     "regla": "Citas de los últimos 14 días sin marcar si el lead vino.", "comprueba": "Las citas quedan marcadas (se presentó / no se presentó).", "fuente": "Salud del CRM"},
    {"id": "crm_sin_usar", "dep": "crm", "titulo": "Subcuenta sin usar", "gravedad": "baja", "plazo_h": 168, "modulo": "salud-crm", "ir": "salud-crm/{sub}",
     "regla": "La subcuenta de GoHighLevel de un cliente activo no tiene uso (sin contactos ni leads).", "comprueba": "Entran contactos o leads en la subcuenta.", "fuente": "Salud del CRM"},
    {"id": "crm_whatsapp", "dep": "crm", "titulo": "WhatsApp que falla", "gravedad": "media", "plazo_h": 48, "modulo": "salud-crm", "ir": "salud-crm/{sub}",
     "regla": "Más del 10 % de los WhatsApp salientes de la subcuenta fallan.", "comprueba": "Los fallidos bajan del 10 %.", "fuente": "Salud del CRM"},
    # publicidad
    {"id": "pub_critico", "dep": "publicidad", "titulo": "Captación en crítico", "gravedad": "alta", "plazo_h": 24, "modulo": "captacion", "ir": "captacion/{cid}",
     "regla": "Coste por lead disparado, gasto sin leads, cuenta parada o pago pendiente (reglas de la Torre de control).", "comprueba": "La Torre deja de marcarlo en crítico.", "fuente": "Captación (Meta + GoHighLevel)"},
    {"id": "pub_atencion", "dep": "publicidad", "titulo": "Captación a vigilar", "gravedad": "media", "plazo_h": 48, "modulo": "captacion", "ir": "captacion/{cid}",
     "regla": "Coste por lead o por cita por encima del techo, 7 días sin leads con gasto o campañas paradas ayer.", "comprueba": "La Torre lo pasa a «bien».", "fuente": "Captación"},
    {"id": "pub_cuenta", "dep": "publicidad", "titulo": "Cuenta publicitaria parada", "gravedad": "alta", "plazo_h": 4, "modulo": "captacion", "ir": "captacion/{cid}",
     "regla": "La cuenta de Meta no está activa (pago pendiente, desactivada o en revisión).", "comprueba": "La cuenta vuelve a «activa».", "fuente": "Captación (Meta)"},
    # redes
    {"id": "redes_hueco", "dep": "redes", "titulo": "Hueco en los próximos 7 días", "gravedad": "media", "plazo_h": 48, "modulo": "redes", "ir": "redes/{cid}",
     "regla": "4 días seguidos o más sin nada programado dentro de los próximos 7 días.", "comprueba": "Metricool tiene piezas programadas en esos días.", "fuente": "Redes (Metricool)"},
    {"id": "redes_fallida", "dep": "redes", "titulo": "Publicación fallida o red desconectada", "gravedad": "media", "plazo_h": 48, "modulo": "redes", "ir": "redes/{cid}",
     "regla": "Metricool no pudo publicar (red desconectada o sesión caducada) en los últimos 30 días.", "comprueba": "La siguiente publicación sale sin error.", "fuente": "Redes (Metricool)"},
    # accounts
    {"id": "acc_critico", "dep": "accounts", "titulo": "Cliente en crítico", "gravedad": "alta", "plazo_h": 24, "modulo": "en-rojo", "ir": "en-rojo/{cid}",
     "regla": "La verdad única lo marca en crítico (fuga, alta sin encender, correos muy viejos con riesgo o gasto sin leads).", "comprueba": "El cliente deja de estar en crítico.", "fuente": "En rojo (verdad única)"},
    {"id": "acc_correos", "dep": "accounts", "titulo": "Correos sin contestar más de 48 h", "gravedad": "alta", "plazo_h": 24, "modulo": "bandeja", "ir": "bandeja",
     "regla": "Correos del cliente en Desk sin respuesta más de 48 h laborables (D-29).", "comprueba": "La Bandeja no tiene correos de más de 48 h del cliente.", "fuente": "Bandeja (Zoho Desk)"},
    {"id": "acc_llamadas", "dep": "accounts", "titulo": "Llamada sin devolver", "gravedad": "media", "plazo_h": 24, "modulo": "bandeja", "ir": "bandeja",
     "regla": "Entrantes perdidas de los últimos 5 días laborables sin ninguna contestada después.", "comprueba": "Hay una llamada contestada con ese número.", "fuente": "Bandeja (Zadarma)"},
    {"id": "acc_sin_reunion", "dep": "accounts", "titulo": "Sin reunión el mes pasado", "gravedad": "media", "plazo_h": 120, "modulo": "reuniones", "ir": "reuniones",
     "regla": "Ninguna reunión con el cliente el mes pasado en CRM, Fathom ni Zoom (salvo exentos).", "comprueba": "Aparece una reunión este mes.", "fuente": "Reuniones (verdad única)"},
    {"id": "acc_informe", "dep": "accounts", "titulo": "Informe mensual sin enviar el día 6", "gravedad": "alta", "plazo_h": 24, "modulo": "informes-mensuales", "ir": "informes-mensuales",
     "regla": "El informe del mes no ha salido desde Desk el día 5 incluido (D-09: el 6, rojo y aviso a Mili).", "comprueba": "Sale el correo del informe en Desk.", "fuente": "Informes mensuales (ClickUp + Desk)"},
    {"id": "acc_sin_agente", "dep": "accounts", "titulo": "Ticket sin agente", "gravedad": "alta", "plazo_h": 4, "modulo": "incidencias", "ir": "incidencias",
     "regla": "Ticket de cliente en Desk sin agente más de 4 h: nadie lo ve.", "comprueba": "El ticket tiene agente.", "fuente": "Incidencias (Desk)"},
    {"id": "acc_config", "dep": "accounts", "titulo": "Fallo de configuración de Desk o Zadarma", "gravedad": "media", "plazo_h": 48, "modulo": "incidencias", "ir": "incidencias",
     "regla": "Tickets a nombre de alguien que ya no está, llamadas que no llegan a nadie o desvíos a extensiones inexistentes.", "comprueba": "La siguiente lectura de Desk o Zadarma no lo encuentra.", "fuente": "Incidencias (Desk y Zadarma)"},
    # altas
    {"id": "alta_fuera_plazo", "dep": "altas", "titulo": "Alta fuera del día 12", "gravedad": "alta", "plazo_h": 24, "modulo": "clientes-nuevos", "ir": "clientes-nuevos/{cid}",
     "regla": "La campaña no se encendió el día 12 desde el alta del contrato (objetivo, día 10).", "comprueba": "Campaña encendida (si fue tarde, queda como «encendida tarde» hasta cerrar el mes).", "fuente": "Clientes nuevos"},
    {"id": "alta_sin_lista", "dep": "altas", "titulo": "Alta sin lista de arranque a las 48 h de la firma", "gravedad": "alta", "plazo_h": 24, "modulo": "clientes-nuevos", "ir": "clientes-nuevos/{cid}",
     "regla": "Sin lista «Onboarding —» en ClickUp pasadas 48 h desde la firma.", "comprueba": "Aparece la lista en ClickUp.", "fuente": "Clientes nuevos (ClickUp)"},
    # administración
    {"id": "adm_impago", "dep": "administracion", "titulo": "Factura vencida sin cobrar", "gravedad": "media", "plazo_h": 72, "modulo": "finanzas", "ir": "finanzas",
     "regla": "Factura vencida en Holded (alta si pasa de 30 días; a los 60 decide Tomás).", "comprueba": "Holded la marca cobrada.", "fuente": "Finanzas (Holded)"},
    {"id": "adm_sepa", "dep": "administracion", "titulo": "Recibo SEPA devuelto", "gravedad": "alta", "plazo_h": 48, "modulo": "finanzas", "ir": "finanzas",
     "regla": "El banco devuelve el cargo de la remesa SEPA.", "comprueba": "Se cobra por otra vía o en la remesa siguiente.", "fuente": "Finanzas (Holded y banco)"},
    {"id": "adm_sin_alta", "dep": "administracion", "titulo": "Firmado sin alta en facturación", "gravedad": "alta", "plazo_h": 48, "modulo": "finanzas", "ir": "finanzas",
     "regla": "Contrato firmado que todavía no tiene su línea en el Airtable de facturación.", "comprueba": "Aparece su línea en Airtable.", "fuente": "Finanzas (Sign + Airtable)"},
    # RRHH
    {"id": "rrhh_alerta", "dep": "rrhh", "titulo": "Persona en alerta", "gravedad": "media", "plazo_h": 168, "modulo": "personas", "ir": "personas",
     "regla": "Motivos del panel de operaciones (imputación, tareas arrastradas, correos o revisiones viejas). Número de Cecilia: en alerta sin plan en 7 días.", "comprueba": "La persona sale de la lista de alerta.", "fuente": "Personas (panel de operaciones v7)"},
    # Horas imputadas = solo AVISO (regla de Tomás, 2-oct): sin plazo, sin semáforo rojo y sin escalado; no cuenta como alerta.
    {"id": "rrhh_no_imputa", "dep": "rrhh", "titulo": "No imputó horas ayer", "gravedad": "baja", "plazo_h": None, "aviso": True, "modulo": "horas", "ir": "horas",
     "regla": "Aviso, no alerta: 0 h imputadas el último día laborable (verdad única del equipo). Las horas no escalan ni ponen nada en rojo.", "comprueba": "Hay horas de ese día en ClickUp.", "fuente": "Horas (ClickUp)"},
    {"id": "rrhh_cumple", "dep": "rrhh", "titulo": "Cumpleaños", "gravedad": "baja", "plazo_h": None, "modulo": "personas", "ir": "personas",
     "regla": "Aviso a Cecilia y a Tomás 7 días antes y el mismo día.", "comprueba": "Pasa el día.", "fuente": "Personas (fecha de cumpleaños)"},
    {"id": "rrhh_aniversario", "dep": "rrhh", "titulo": "Aniversario de entrada", "gravedad": "baja", "plazo_h": None, "modulo": "personas", "ir": "personas",
     "regla": "Aviso a Cecilia y a Tomás 7 días antes y el mismo día.", "comprueba": "Pasa el día.", "fuente": "Personas (fecha de entrada)"},
    # dirección
    {"id": "dir_decision", "dep": "direccion", "titulo": "Decisión con reloj", "gravedad": "alta", "plazo_h": None, "modulo": "decisiones", "ir": "decisiones",
     "regla": "Decisión pendiente: 48 h para Tomás, 24 h para Coti.", "comprueba": "Tiene respuesta.", "fuente": "Decisiones y rastro"},
    {"id": "dir_sin_account", "dep": "direccion", "titulo": "Cliente sin account", "gravedad": "media", "plazo_h": 48, "modulo": "ajustes", "ir": "ajustes",
     "regla": "El cliente no tiene account principal vigente en asignaciones.", "comprueba": "Tiene account en Ajustes › Asignaciones.", "fuente": "Verdad única (asignaciones)"},
    {"id": "hosting_cuenta", "dep": "direccion", "titulo": "Renovación o dominio de RO en Hostinger", "gravedad": "media", "plazo_h": 72, "modulo": "ajustes", "ir": "ajustes/conexiones/hostinger",
     "regla": "Suscripción de Hostinger que vence en 30 días sin renovación automática (7 = alta), o dominio o web de la cuenta sin cliente caducado, suspendido o a punto de caducar.", "comprueba": "La siguiente lectura de Hostinger deja de avisarlo (la app no renueva nada).", "fuente": "Hostinger (API, solo lectura)"},
    {"id": "hosting_vps", "dep": "conexiones", "titulo": "Servidor (VPS) de Hostinger con problemas", "gravedad": "alta", "plazo_h": 4, "modulo": "ajustes", "ir": "ajustes/conexiones/hostinger",
     "regla": "VPS parado o con error, CPU media de la última hora ≥ 80 % (95 = alta), memoria ≥ 92 %, disco ≥ 80 % (90 = alta), copia de más de 8 días (15 = alta), operación fallida en 48 h o malware. Incluye el VPS del gestor de contraseñas: la app solo lo lee.", "comprueba": "La siguiente lectura de Hostinger lo da en verde.", "fuente": "Hostinger (API, solo lectura)"},
    # conexiones (A8): las manda ya hechas la salud de conexiones (N11) en el formato de N4; aquí no se recalcula nada
    {"id": "conexion_caida", "dep": "conexiones", "titulo": "Conexión caída o a punto de caducar", "gravedad": "alta", "plazo_h": 4, "modulo": "ajustes", "ir": "ajustes/conexiones",
     "regla": "Una conexión que la app usa está en rojo, o su llave caduca en 21 días o menos (salud de conexiones).", "comprueba": "La siguiente prueba de la conexión sale en verde.", "fuente": "Salud de conexiones (Ajustes)"},
]
REGLA = {r["id"]: r for r in REGLAS}
NO_MEDIBLE = [
    {"dep": "web", "que": "Formulario roto", "porque": "Ninguna fuente prueba hoy los formularios de cada web. Llega con el monitor externo y el gestor de webs Modular DS.", "quien": "Jerónimo"},
    {"dep": "web", "que": "Velocidad real (PageSpeed)", "porque": "Falta la clave gratuita de la API de PageSpeed: hoy solo se mide el tiempo de servir la portada.", "quien": "Tomás"},
    {"dep": "seo", "que": "Páginas sin indexar", "porque": "Search Console no da la cobertura por API con la llave actual; se mira en Search Console.", "quien": "Jerónimo"},
    {"dep": "crm", "que": "Flujos con error", "porque": "GoHighLevel responde 401 a la lectura de flujos y los «Needs Review» no salen por la API.", "quien": "Yessica"},
]


# =================================================================== datos base
PERSONAS = leer("personas") or []
ASIG = leer("asignaciones") or []
CLIENTES_CONTRATO = leer("clientes") or []
PER = {p["id"]: p for p in PERSONAS}
VERDAD = leer("verdad/clientes") or {"clientes": [], "comun": [], "resumen": {}}
VC = {c["cliente_id"]: c for c in VERDAD.get("clientes", [])}
NOMBRE_CLI = {c["id"]: c["nombre"] for c in VERDAD.get("comun", [])}
ATAJOS = {f["cliente_id"]: {a["k"]: a["url"] for a in f.get("atajos", [])} for f in (leer("en_rojo/atajos") or {}).get("filas", [])}
NOMBRE_ATAJO = {"desk": "Desk", "clickup": "ClickUp", "ghl": "GoHighLevel", "meta": "Meta", "drive": "Drive", "analytics": "Analytics", "searchConsole": "Search Console"}


def corto(pid):
    p = PER.get(pid)
    return (p.get("alias") or p["nombre"].split()[0]) if p else pid


def dueno_de(dep, cid=None, propuesto=None):
    """Dueño = persona asignada a la silla de ese departamento en el cliente (asignaciones, vía verdad única), o el jefe."""
    d = DEPTOS[dep]
    if propuesto and PER.get(propuesto, {}).get("activo"):
        return propuesto, "dueño fijo del departamento"
    if d.get("dueno_fijo"):
        return d["dueno_fijo"], "dueño fijo del departamento"
    if cid and d.get("silla"):
        if d["silla"] == "account" and VC.get(cid, {}).get("account"):
            return VC[cid]["account"], "account del cliente (asignaciones)"
        eq = (VC.get(cid, {}).get("equipo") or {}).get(d["silla"]) or []
        eq = sorted([e for e in eq if PER.get(e["persona_id"], {}).get("activo")], key=lambda x: not x.get("principal"))
        # Solo vale quien puede abrir ese cliente con sus permisos (una silla que su puesto no tiene no le da cartera).
        ok = [e for e in eq if puede_abrir(e["persona_id"], cid)]
        if ok:
            return ok[0]["persona_id"], f"silla «{d['silla']}» del cliente (asignaciones)"
        if eq:
            return d["jefe"], f"jefe del departamento ({corto(eq[0]['persona_id'])} está en la silla «{d['silla']}» pero su puesto no abre el cliente)"
    return d["jefe"], "jefe del departamento (no hay nadie asignado a esa silla)"


_CTX = {}


def puede_abrir(pid, cid):
    p = PER.get(pid)
    if not p:
        return False
    if pid not in _CTX:
        _CTX[pid] = P.contexto(p, {"asignaciones": ASIG, "personas": PERSONAS, "clientes": CLIENTES_CONTRATO})
    return P.ver(p, {"tipo": "cliente_detalle", "cliente_id": cid}, _CTX[pid])["ok"]


def cadena_escalado(dep, dueno):
    """3-oct · orden de escalado oficial (data/escalado.json → escalado.py): dueño → responsable del área → Mili → Tomás.
    Dinero y RRHH (su responsable ya es Tomás) quedan dueño → Tomás. Antes se cortaba en 3 y Tomás no llegaba nunca
    cuando el jefe no era Mili (CRM, publicidad, SEO, web, redes)."""
    return [x for x in ESC.cadena_alertas(dep, dueno, DEPTOS[dep]["jefe"]) if x][:4]


def abrir(cid, k, url=None, texto=None):
    u = url or (ATAJOS.get(cid, {}).get(k) if cid else None)
    if not u:
        return None
    return {"herramienta": k, "texto": texto or f"Abrir en {NOMBRE_ATAJO.get(k, k)}", "url": u}


ALERTAS = []
AVISOS = []          # reglas con "aviso": True (horas imputadas): se enseñan, pero no cuentan, no vencen y no escalan
FUENTES = []
COHERENCIA = []


def alerta(regla, clave, motivo, *, cid=None, desde=None, gravedad=None, abrir_en=None, ir=None, cifra=None,
           detalle=None, dueno=None, extra=None, persona_ref=None, plazo_h=None, vence=None, sub=None):
    r = REGLA[regla]
    dep = r["dep"]
    d_id, d_origen = dueno_de(dep, cid, dueno)
    a = {
        "id": f"{regla}:{clave}",
        "tipo": regla, "departamento": dep, "titulo": r["titulo"], "motivo": plurales(motivo),
        "cliente_id": cid, "cliente": NOMBRE_CLI.get(cid) if cid else None,
        "dueno_id": d_id, "dueno_origen": d_origen, "jefe_id": DEPTOS[dep]["jefe"],
        "escalado_cadena": cadena_escalado(dep, d_id),
        "desde": f2s(desde) if isinstance(desde, datetime) else desde,
        "plazo_h": plazo_h if plazo_h is not None else r["plazo_h"], "vence": vence,
        "gravedad": gravedad or r["gravedad"], "cifra": cifra, "detalle": [plurales(x) for x in (detalle or []) if x][:6],
        "abrir": [x for x in (abrir_en or []) if x][:3],
        "ir": "#/" + (ir or r["ir"]).replace("{cid}", cid or "").replace("{sub}", sub or "").rstrip("/"),
        "modulo_origen": r["modulo"], "fuente": r["fuente"], "comprueba": r["comprueba"],
    }
    if persona_ref:
        a["persona_id"] = persona_ref          # el servidor la recorta con la regla de personas (horas_persona)
        a["persona"] = corto(persona_ref)
    if extra:
        a.update(extra)
    if r.get("aviso"):
        a.update({"aviso": True, "plazo_h": None, "vence": None, "escalado_cadena": [d_id], "estado": "aviso",
                  "escalado": {"nivel": 0, "a_id": d_id, "texto": None}, "responsable_ahora": d_id})
        AVISOS.append(a)
        return a
    ALERTAS.append(a)
    return a


def fuente(nombre, rel, doc, filas, hora=None):
    FUENTES.append({"modulo": nombre, "fichero": f"data/{rel}.json", "leido": bool(doc), "alertas": filas,
                    "generado": hora or (doc or {}).get("generado") or ((doc or {}).get("_meta") or {}).get("generado")})


def coherencia(que, modulo, cifra_modulo, cifra_alertas, nota=""):
    COHERENCIA.append({"que": que, "modulo": modulo, "cifra_modulo": cifra_modulo, "cifra_alertas": cifra_alertas,
                       "ok": cifra_modulo == cifra_alertas, "nota": nota})


def n_tipo(*tipos):
    return sum(1 for a in ALERTAS if a["tipo"] in tipos)


def suma_cifra(*tipos):
    return sum(a.get("cifra") or 0 for a in ALERTAS if a["tipo"] in tipos)


# =================================================================== 1 · webs (SEO, ficha y webs)
def de_webs():
    doc = leer("seo/webs")
    antes = len(ALERTAS)
    if not doc:
        return fuente("SEO, ficha y webs · monitor", "seo/webs", None, 0)
    certs = lentas = caidas = spam = 0
    for w in doc.get("webs", []):
        cid = w.get("cliente") if w.get("cliente") in NOMBRE_CLI else None
        clave = w.get("cliente") or w.get("url")
        nombre = w.get("nombre") or NOMBRE_CLI.get(cid) or clave
        comp = w.get("comprobacion") or {}
        hora = fecha(comp.get("hora"))
        ab = [{"herramienta": "web", "texto": "Abrir la web", "url": w["url"]}] if w.get("url") else []
        mot = w.get("motivo") or ""
        if w.get("estado") == "rojo" and mot.startswith("No responde"):
            caidas += 1
            alerta("web_caida", clave, f"La web de {nombre} no responde: {mot.split(': ', 1)[-1]}.", cid=cid, desde=hora, abrir_en=ab,
                   detalle=[f"Comprobado a las {hora:%H:%M} desde la IP de RO" if hora else None, comp.get("error") and "Error técnico guardado en el monitor"],
                   extra={"web": w.get("url")})
        elif w.get("estado") == "rojo" and "spam" in mot.lower():
            spam += 1
            alerta("web_spam", clave, f"La portada de {nombre} tiene enlaces de spam ({mot.split(': ', 1)[-1]}).", cid=cid, desde=hora, abrir_en=ab,
                   detalle=["Web posiblemente hackeada: limpiar, cambiar accesos y pedir revisión en Search Console"], extra={"web": w.get("url")})
        cd = comp.get("cert_dias")
        if isinstance(cd, int) and cd <= 30:
            certs += 1
            alerta("web_certificado", clave, f"El certificado de {nombre} caduca en {cd} días ({comp.get('cert_caduca')}).", cid=cid, desde=hora,
                   gravedad="alta" if cd <= 7 else "media", abrir_en=ab, cifra=cd, extra={"web": w.get("url")})
        if mot.startswith("Respuesta lenta"):
            lentas += 1
            alerta("web_lenta", clave, f"La portada de {nombre} tarda {mot.split(': ', 1)[-1].split(' en ')[0]} en servirse.", cid=cid, desde=hora,
                   abrir_en=ab, detalle=["Medido desde RO; la puntuación real llega con PageSpeed"], extra={"web": w.get("url")})
        for i, av in enumerate(x for x in (w.get("avisos") or []) if x.get("tipo") == "medicion"):
            alerta("web_medicion", f"{clave}:{i}", f"{nombre}: {av.get('titulo', 'fallo de medición')}.", cid=cid, desde=hora,
                   abrir_en=[abrir(cid, "analytics")] if cid else [], detalle=[av.get("texto"), av.get("que_hacer") and f"Qué hacer: {av['que_hacer']}"])
    r = doc.get("resumen", {})
    coherencia("Webs en rojo (caídas + spam)", "SEO, ficha y webs", r.get("rojo"), caidas + spam)
    coherencia("Certificados que caducan en 30 días", "SEO, ficha y webs", r.get("cert_30"), certs)
    coherencia("Avisos de medición de Analytics", "SEO, ficha y webs", r.get("avisos_medicion"), n_tipo("web_medicion"))
    ambar_mod = sum(1 for w in doc.get("webs", []) if w.get("estado") == "ambar")
    ambar_alertas = sum(1 for w in doc.get("webs", []) if w.get("estado") == "ambar" and ((w.get("motivo") or "").startswith("Respuesta lenta") or (w.get("motivo") or "").startswith("El certificado")))
    coherencia("Webs en ámbar (certificado o lenta)", "SEO, ficha y webs", r.get("ambar", ambar_mod), ambar_alertas)
    fuente("SEO, ficha y webs · monitor", "seo/webs", doc, len(ALERTAS) - antes, (doc.get("_meta") or {}).get("generado"))


def de_modular():
    """Carril N5 (Modular DS): fuentes_modular/generar_modular.py → data/modular/webs.json › «alertas» (formato de FORMATO.md).
    Entran cuatro: caída (web_caida), copia de más de 2 días o ninguna (copia_atrasada, copia_nunca), vulnerabilidad CRÍTICA
    (vulnerabilidad en rojo) y certificado de menos de 15 días (certificado). El resto (actualizaciones, salud, enlaces) se
    trabaja desde el tablero de Webs, sin alerta. Dueño: la persona de web del cliente (silla «web»); sin cliente o sin
    persona, el jefe del departamento de web. Van a #avisos-web por avisos.py, como todas las del departamento."""
    doc = leer("modular/webs")
    if not doc or (doc.get("_meta") or {}).get("estado") != "conectado":
        nota = ((doc or {}).get("_meta") or {}).get("que_hacer") or "Esperando data/modular/webs.json (fuentes_modular/generar_modular.py)."
        return FUENTES.append({"modulo": "Modular DS (gestor de webs)", "fichero": "data/modular/webs.json", "leido": bool(doc), "alertas": 0,
                               "generado": ((doc or {}).get("_meta") or {}).get("generado"), "nota": f"Modular sin conectar: {nota}"})
    antes = len(ALERTAS)
    nombre_web = {str(w.get("modular_id")): (w.get("cliente") or w.get("nombre") or w.get("dominio")) for w in (doc.get("webs") or []) + (doc.get("sin_cliente") or [])}
    regla_de = {"web_caida": "modular_caida", "copia_nunca": "modular_copia", "copia_atrasada": "modular_copia", "certificado": "modular_certificado"}
    esperadas = 0
    for x in doc.get("alertas") or []:
        regla = regla_de.get(x.get("regla"))
        if x.get("regla") == "vulnerabilidad" and x.get("gravedad") == "rojo":
            regla = "modular_vulnerabilidad"
        if not regla:
            continue
        esperadas += 1
        mid = str(x.get("id") or "").split(":")[-1]
        cid = x.get("cliente_id") if x.get("cliente_id") in NOMBRE_CLI else None
        quien = NOMBRE_CLI.get(cid) or nombre_web.get(mid) or x.get("web")
        alerta(regla, f"{cid or x.get('web') or mid}", f"{quien}: {x.get('titulo', 'aviso de Modular')} · {x.get('texto') or ''}".strip(" ·"),
               cid=cid, desde=fecha(x.get("desde")) or fecha(x.get("detectado")),
               gravedad={"rojo": "alta", "ambar": "media"}.get(x.get("gravedad")),
               abrir_en=[{"herramienta": "modular", "texto": "Abrir en Modular DS", "url": x.get("fuente_enlace") or "https://app.modulards.com/"}],
               ir=f"seo-web/webs/{cid}" if cid else "seo-web/webs",
               detalle=[x.get("que_hacer") and f"Qué hacer: {x['que_hacer']}", f"Web: {x.get('web')}" if x.get("web") else None],
               extra={"web": x.get("web"), "modular_id": mid or None})
    coherencia("Alertas de Modular DS (caída, copia > 2 días, vulnerabilidad crítica, certificado < 15 días)", "Modular DS (gestor de webs)",
               esperadas, len(ALERTAS) - antes)
    return fuente("Modular DS (gestor de webs)", "modular/webs", doc, len(ALERTAS) - antes)


def de_hostinger():
    """Hostinger (fuentes_hostinger/generar_hostinger.py → data/hostinger/hostinger.json · «alertas», formato N4).
    Web de cliente → departamento web (persona de web del cliente) · VPS → Conexiones (Agus, técnico) · renovaciones y
    dominios sin cliente → Dirección (Tomás). Sin token: ninguna alerta y la fuente dice «sin clave»."""
    try:   # pruebas: RO_ALERTAS_HOSTINGER = fichero simulado (generar_hostinger.py --simulado --salida …)
        doc = json.loads(Path(os.environ["RO_ALERTAS_HOSTINGER"]).read_text()) if os.environ.get("RO_ALERTAS_HOSTINGER") else leer("hostinger/hostinger")
    except Exception:
        doc = None
    try:   # VPS y renovaciones viven aparte (cuenta.json, solo dirección, operaciones y técnico)
        rc = (os.environ["RO_ALERTAS_HOSTINGER"].removesuffix(".json") + "_cuenta.json") if os.environ.get("RO_ALERTAS_HOSTINGER") else None
        cta = json.loads(Path(rc).read_text()) if rc else leer("hostinger/cuenta")
    except Exception:
        cta = None
    if doc and cta:
        doc = {**doc, "alertas": (doc.get("alertas") or []) + (cta.get("alertas") or [])}
    if doc and (doc.get("_meta") or {}).get("estado") == "simulado" and os.environ.get("RO_ALERTAS_HOSTINGER"):
        doc["_meta"]["estado"] = "conectado"
    antes = len(ALERTAS)
    if not doc or (doc.get("_meta") or {}).get("estado") != "conectado":
        nota = (doc or {}).get("_meta", {}).get("que_hacer") or "Esperando data/hostinger/hostinger.json."
        return FUENTES.append({"modulo": "Hostinger (hosting, VPS y dominios)", "fichero": "data/hostinger/hostinger.json", "leido": bool(doc),
                               "alertas": 0, "generado": (doc or {}).get("_meta", {}).get("generado"), "nota": "Sin clave · " + nota})
    xs = [x for x in doc.get("alertas") or [] if isinstance(x, dict) and x.get("id")]
    grav = {"rojo": "alta", "ambar": "media"}
    for x in xs:
        cid = x.get("cliente_id") if x.get("cliente_id") in NOMBRE_CLI else None
        det = [x.get("titulo"), x.get("que_hacer") and f"Qué hacer: {x['que_hacer']}"]
        ab = [{"herramienta": "hostinger", "texto": "Abrir hPanel", "url": x.get("fuente_enlace") or "https://hpanel.hostinger.com/"}]
        if x.get("departamento") == "web" and cid:
            alerta("web_hosting", f"{cid}:{x.get('regla')}:{x.get('objeto')}", x.get("texto") or "Hostinger avisa de un problema.", cid=cid,
                   desde=fecha(x.get("desde")), gravedad=grav.get(x.get("gravedad")), abrir_en=ab, detalle=det, cifra=x.get("cifra"),
                   extra={"web": x.get("objeto")})
        elif x.get("departamento") == "conexiones":
            alerta("hosting_vps", f"{x.get('regla')}:{x.get('objeto')}", x.get("texto") or "Hostinger avisa de un problema en un VPS.",
                   desde=fecha(x.get("desde")), gravedad=grav.get(x.get("gravedad")), abrir_en=ab, detalle=det, cifra=x.get("cifra"),
                   dueno="agustina")
        else:
            alerta("hosting_cuenta", f"{x.get('regla')}:{x.get('objeto')}", x.get("texto") or "Hostinger avisa de algo de la cuenta.",
                   desde=fecha(x.get("desde")), gravedad=grav.get(x.get("gravedad")), abrir_en=ab, detalle=det, cifra=x.get("cifra"))
    coherencia("Incidencias de Hostinger", "Hostinger (hosting, VPS y dominios)", len(xs), len(ALERTAS) - antes)
    fuente("Hostinger (hosting, VPS y dominios)", "hostinger/hostinger", doc, len(ALERTAS) - antes)


def de_gbp():
    """Ficha de Google (fuentes_gbp/generar_gbp.py → data/gbp/gbp.json · «alertas», formato N4). Dueño: SEO/ficha de Google
    del cliente; copia al account («copia_a»). Sin aprobación de Google: ninguna alerta y la fuente dice «pendiente»."""
    try:   # pruebas: RO_ALERTAS_GBP = fichero simulado (generar_gbp.py --simulado --salida …)
        doc = json.loads(Path(os.environ["RO_ALERTAS_GBP"]).read_text()) if os.environ.get("RO_ALERTAS_GBP") else leer("gbp/gbp")
    except Exception:
        doc = None
    est = ((doc or {}).get("_meta") or {}).get("estado")
    if est == "simulado" and os.environ.get("RO_ALERTAS_GBP"):
        est = "conectado"
    if est != "conectado":
        nota = ((doc or {}).get("_meta") or {}).get("texto") or "Esperando data/gbp/gbp.json (fuentes_gbp/generar_gbp.py)."
        return FUENTES.append({"modulo": "Ficha de Google (Business Profile)", "fichero": "data/gbp/gbp.json", "leido": bool(doc), "alertas": 0,
                               "generado": ((doc or {}).get("_meta") or {}).get("generado"), "nota": nota})
    antes = len(ALERTAS)
    regla_de = {"resena_mala": "gbp_resena", "caida_llamadas": "gbp_caida", "caida_rutas": "gbp_caida",
                "perfil_suspendido": "gbp_perfil", "datos_cambiados": "gbp_perfil"}
    grav = {"rojo": "alta", "ambar": "media"}
    xs = [x for x in doc.get("alertas") or [] if isinstance(x, dict) and x.get("id") and regla_de.get(x.get("regla"))
          and x.get("cliente_id") in NOMBRE_CLI]
    for x in xs:
        cid = x["cliente_id"]
        a = alerta(regla_de[x["regla"]], f"{cid}:{x.get('regla')}:{x.get('objeto')}", x.get("texto") or "La ficha de Google avisa de algo.",
                   cid=cid, desde=fecha(x.get("desde")) or fecha(x.get("detectado")), gravedad=grav.get(x.get("gravedad")),
                   abrir_en=[{"herramienta": "gbp", "texto": "Abrir Google Business", "url": x.get("fuente_enlace") or "https://business.google.com/locations"}],
                   detalle=[x.get("titulo"), x.get("que_hacer") and f"Qué hacer: {x['que_hacer']}"], cifra=x.get("cifra"), dueno=x.get("dueno_id"),
                   vence=x.get("vence"), extra={"resena_id": x.get("resena_id"), "copia_a": [p for p in (x.get("copia_a") or []) if p in PER]})
        if a.get("dueno_id") in a.get("copia_a", []):
            a["copia_a"] = [p for p in a["copia_a"] if p != a["dueno_id"]]
    coherencia("Alertas de la ficha de Google (reseñas 1-3★, caídas > 30 %, ficha suspendida o cambiada)", "Ficha de Google (Business Profile)",
               len(xs), len(ALERTAS) - antes)
    fuente("Ficha de Google (Business Profile)", "gbp/gbp", doc, len(ALERTAS) - antes)


# =================================================================== 2 · SEO
def de_seo():
    doc = leer("seo/seo")
    antes = len(ALERTAS)
    if not doc:
        return fuente("SEO", "seo/seo", None, 0)
    for c in doc.get("clientes", []):
        if c.get("estado") not in ("rojo", "ambar"):
            continue
        cid = c["cliente_id"]
        tipos = Counter(a.get("tipo") for a in c.get("alertas") or [])
        det = []
        if tipos.get("fuera_top10"):
            det.append(f"{pl(tipos['fuera_top10'], 'palabra')} fuera del top 10")
        if tipos.get("desaparece"):
            det.append(f"{pl(tipos['desaparece'], 'palabra')} que no aparecen en la comprobación (mirar en Google antes de actuar)")
        if tipos.get("clics"):
            det.append("Clics a la baja semana contra semana")
        if tipos.get("sin_top10"):
            det.append("Ninguna de las 15 palabras del informe en el top 10")
        det += [a.get("texto") for a in (c.get("alertas") or [])[:2]]
        alerta("seo_rojo" if c["estado"] == "rojo" else "seo_ambar", cid, f"{c.get('cliente')}: {c.get('motivo')}.", cid=cid,
               desde=fecha(((doc.get("_meta") or {}).get("seranking") or {}).get("leido")), cifra=c.get("n_alertas"), detalle=det,
               abrir_en=[abrir(cid, "searchConsole"), {"herramienta": "seranking", "texto": "Abrir en SE Ranking", "url": "https://online.seranking.com/admin.projects.html"}])
    r = doc.get("resumen", {})
    coherencia("Clientes SEO en rojo", "SEO", r.get("rojos"), n_tipo("seo_rojo"))
    coherencia("Clientes SEO en ámbar", "SEO", r.get("ambar"), n_tipo("seo_ambar"))
    fuente("SEO", "seo/seo", doc, len(ALERTAS) - antes, (doc.get("_meta") or {}).get("generado"))


# =================================================================== 3 · CRM
def de_crm():
    doc = leer("crm/crm")
    antes = len(ALERTAS)
    if not doc:
        return fuente("Salud del CRM", "crm/crm", None, 0)
    subs = {s["sub_id"]: s for s in doc.get("subcuentas", [])}
    por = defaultdict(list)
    for x in doc.get("leads_sin_tocar", []):
        por[(x.get("cliente_id"), x.get("sub_id"))].append(x)
    for (cid, sub), xs in sorted(por.items(), key=lambda kv: -len(kv[1])):
        s = subs.get(sub, {})
        nombre = NOMBRE_CLI.get(cid) or xs[0].get("subcuenta")
        mas_viejo = min(fecha(x.get("creado")) or AHORA for x in xs)
        ab = [{"herramienta": "ghl", "texto": "Abrir contactos en GoHighLevel", "url": f"https://app.gohighlevel.com/v2/location/{sub}/contacts/smart_list/All"}] if sub else []
        alerta("crm_sin_tocar", cid or sub, f"{nombre}: {pl(len(xs), 'lead')} de más de 24 h sin ningún intento en GoHighLevel.", cid=cid, sub=sub,
               desde=mas_viejo, cifra=len(xs), abrir_en=ab, dueno=None if cid else (xs[0].get("especialista_id")),
               detalle=[f"El más antiguo entró el {mas_viejo:%d-%m} ({miles(int((AHORA - mas_viejo).total_seconds() // 3600))} h)",
                        f"Especialista en la subcuenta: {corto(s.get('especialista_id'))}" if s.get("especialista_id") else "La subcuenta no tiene especialista"])
    por = defaultdict(list)
    for x in doc.get("citas_sin_estado", []):
        por[(x.get("cliente_id"), x.get("sub_id"))].append(x)
    for (cid, sub), xs in sorted(por.items(), key=lambda kv: -len(kv[1])):
        nombre = NOMBRE_CLI.get(cid) or xs[0].get("subcuenta")
        mas_vieja = min(fecha(x.get("inicio")) or AHORA for x in xs)
        alerta("crm_citas_sin_estado", cid or sub, f"{nombre}: {pl(len(xs), 'cita')} de los últimos 14 días sin marcar si vino.", cid=cid, sub=sub,
               desde=mas_vieja, cifra=len(xs), abrir_en=[{"herramienta": "ghl", "texto": "Abrir el calendario en GoHighLevel", "url": xs[0].get("enlace")}],
               detalle=["Sin marcar, la asistencia no se puede medir"])
    sin_uso = 0
    for s in doc.get("subcuentas", []):
        cid = s.get("cliente_id")
        if s.get("tipo") == "cliente" and s.get("sin_uso"):
            sin_uso += 1
            alerta("crm_sin_usar", cid or s["sub_id"], f"{NOMBRE_CLI.get(cid) or s.get('nombre')}: la subcuenta de GoHighLevel no se usa ({s.get('contactos_total', 0)} contacto{'' if s.get('contactos_total', 0) == 1 else 's'}).",
                   cid=cid, sub=s["sub_id"], desde=None,
                   abrir_en=[{"herramienta": "ghl", "texto": "Abrir la subcuenta", "url": f"https://app.gohighlevel.com/v2/location/{s['sub_id']}/dashboard"}])
        wa = s.get("whatsapp") or {}
        if s.get("tipo") == "cliente" and isinstance(wa.get("pct_fallo"), (int, float)) and wa["pct_fallo"] > 10:
            alerta("crm_whatsapp", cid or s["sub_id"], f"{NOMBRE_CLI.get(cid) or s.get('nombre')}: fallan {wa.get('fallidos')} de {wa.get('enviados')} WhatsApp ({str(wa['pct_fallo']).replace('.', ',')} %).",
                   cid=cid, sub=s["sub_id"], cifra=wa.get("fallidos"),
                   abrir_en=[{"herramienta": "ghl", "texto": "Abrir conversaciones", "url": f"https://app.gohighlevel.com/v2/location/{s['sub_id']}/conversations/conversations"}])
    r = doc.get("resumen", {})
    coherencia("Leads sin tocar > 24 h", "Salud del CRM", r.get("sin_tocar_24h"), suma_cifra("crm_sin_tocar"))
    coherencia("Citas sin estado (14 días)", "Salud del CRM", (r.get("citas_14d") or {}).get("sin_estado"), suma_cifra("crm_citas_sin_estado"))
    coherencia("Subcuentas de cliente sin usar", "Salud del CRM", sin_uso, n_tipo("crm_sin_usar"))
    fuente("Salud del CRM", "crm/crm", doc, len(ALERTAS) - antes)


# =================================================================== 4 · publicidad (Captación)
def de_captacion():
    doc = leer("captacion/captacion")
    antes = len(ALERTAS)
    if not doc:
        return fuente("Captación", "captacion/captacion", None, 0)
    for c in doc.get("clientes", []):
        cid = c["cliente_id"]
        cm = c.get("cuenta_meta") or {}
        ab = [{"herramienta": "meta", "texto": "Abrir en Meta", "url": cm.get("enlace")}] if cm.get("enlace") else [abrir(cid, "meta")]
        if cm.get("estado") and cm["estado"] != "activa":
            alerta("pub_cuenta", cid, f"{c['nombre']}: la cuenta de Meta está «{cm['estado']}».", cid=cid, abrir_en=ab,
                   detalle=[cm.get("error")], dueno=None)
        if c.get("severidad") not in ("critico", "atencion"):
            continue
        mot = [m for m in c.get("motivos") or [] if m.get("nivel") in ("critico", "atencion")]
        clases = {m.get("clase_id") for m in mot}
        # Si el cuello es de seguimiento o integración (no de anuncios), el dueño es el del CRM; la cifra sigue siendo de Captación.
        dep_crm = clases and not (clases & {"paid"})
        a = alerta("pub_critico" if c["severidad"] == "critico" else "pub_atencion", cid,
                   f"{c['nombre']}: {mot[0]['texto'] if mot else 'captación en ' + c['severidad']}.", cid=cid,
                   desde=fecha(doc.get("datos_hasta")), abrir_en=ab, cifra=len(mot),
                   detalle=[m["texto"] for m in mot[1:4]] + [f"Trafficker: {corto(c['equipo'].get('trafficker'))}" if (c.get("equipo") or {}).get("trafficker") else None],
                   extra={"gasto_7d": (c.get("gasto") or {}).get("7d"), "leads_7d": (c.get("leads") or {}).get("7d")})
        if dep_crm:
            d_id, d_or = dueno_de("crm", cid)
            a.update({"departamento": "crm", "dueno_id": d_id, "dueno_origen": d_or + " · el cuello es de seguimiento, no de anuncios",
                      "jefe_id": DEPTOS["crm"]["jefe"], "escalado_cadena": cadena_escalado("crm", d_id)})
    pg = (doc.get("resumen") or {}).get("por_gravedad", {})
    coherencia("Clientes de captación en crítico", "Captación", pg.get("critico"), n_tipo("pub_critico"))
    coherencia("Clientes de captación en atención", "Captación", pg.get("atencion"), n_tipo("pub_atencion"))
    fuente("Captación", "captacion/captacion", doc, len(ALERTAS) - antes)


# =================================================================== 5 · redes
def de_redes():
    doc = leer("redes/redes")
    antes = len(ALERTAS)
    if not doc:
        return fuente("Redes", "redes/redes", None, 0)
    con_hueco = con_fallidas = 0
    for c in doc.get("clientes", []):
        cid = c["cliente_id"]
        h7 = [x for x in c.get("huecos") or [] if x.get("en_7")]
        ab = [{"herramienta": "metricool", "texto": "Abrir en Metricool", "url": "https://app.metricool.com/planner"}]
        if h7:
            con_hueco += 1
            dias = sum(min(x["dias"], 7) for x in h7)
            alerta("redes_hueco", cid, f"{c['cliente']}: {'hueco' if len(h7) == 1 else str(len(h7)) + ' huecos'} sin nada programado en los próximos 7 días (desde el {h7[0]['desde'][8:10]}-{h7[0]['desde'][5:7]}).",
                   cid=cid, desde=fecha(h7[0]["desde"]), cifra=len(h7), abrir_en=ab,
                   detalle=[f"{x['dias']} días: {x['desde'][8:10]}-{x['desde'][5:7]} a {x['hasta'][8:10]}-{x['hasta'][5:7]}" for x in h7[:3]] + [f"{c.get('programadas_14', 0)} piezas programadas en 14 días"])
        if c.get("fallidas"):
            con_fallidas += 1
            redes = sorted({r["detalle"] for f in c["fallidas"] for r in f.get("redes") or [] if r.get("detalle")})
            ult = max(f["dia"] for f in c["fallidas"])
            alerta("redes_fallida", cid, f"{c['cliente']}: {pl(len(c['fallidas']), 'publicación fallida', 'publicaciones fallidas')}; {redes[0][0].lower() + redes[0][1:] if redes else 'revisar la conexión'}.",
                   cid=cid, desde=fecha(ult), cifra=len(c["fallidas"]), abrir_en=ab, detalle=redes[:3])
    coherencia("Clientes con hueco en 7 días", "Redes", sum(1 for c in doc.get("clientes", []) if any(x.get("en_7") for x in c.get("huecos") or [])), con_hueco,
               "El módulo cuenta 14 días (rojos: %s); la alerta salta con lo de los próximos 7." % (doc.get("resumen") or {}).get("rojos"))
    coherencia("Clientes con publicaciones fallidas (30 días)", "Redes", sum(1 for c in doc.get("clientes", []) if c.get("fallidas")), con_fallidas,
               "En los últimos 7 días: %s (resumen del módulo)." % (doc.get("resumen") or {}).get("fallidas_7"))
    fuente("Redes", "redes/redes", doc, len(ALERTAS) - antes, (doc.get("_meta") or {}).get("generado"))


# =================================================================== 6 · accounts
def de_accounts():
    antes = len(ALERTAS)
    # 6.1 en rojo · críticos de la verdad única
    for c in VERDAD.get("clientes", []):
        cid = c["cliente_id"]
        if c.get("gravedad") == "critico":
            alerta("acc_critico", cid, f"{c['nombre']} es un cliente crítico: {c['motivos'][0] if c.get('motivos') else 'ver motivos'}.", cid=cid,
                   detalle=c.get("motivos", [])[1:4], abrir_en=[abrir(cid, "clickup"), abrir(cid, "desk")])
        if c.get("sin_reunion_mes_pasado"):
            alerta("acc_sin_reunion", cid, f"{c['nombre']}: ninguna reunión el mes pasado (última, {c.get('ultima_reunion') or 'sin dato'}).", cid=cid,
                   desde=fecha(c.get("ultima_reunion")), abrir_en=[abrir(cid, "clickup")])
    vr = VERDAD.get("resumen", {})
    coherencia("Clientes en crítico", "En rojo (verdad única)", vr.get("critico"), n_tipo("acc_critico"))
    coherencia("Clientes sin reunión el mes pasado", "Reuniones (verdad única)", vr.get("sin_reunion_mes_pasado"), n_tipo("acc_sin_reunion"))
    reu = leer("reuniones/reuniones")
    if reu:
        coherencia("Sin reunión el mes pasado (pantalla Reuniones)", "Reuniones", sum(1 for c in reu.get("clientes", []) if c.get("estado") == "sin_reunion"), n_tipo("acc_sin_reunion"))
    fuente("En rojo y reuniones (verdad única)", "verdad/clientes", VERDAD, len(ALERTAS) - antes)

    # 6.2 bandeja · correos > 48 h por cliente y llamadas sin devolver
    antes = len(ALERTAS)
    pc = leer("bandeja/por_cliente")
    if pc:
        for x in pc.get("clientes", []):
            if not x.get("mas_48"):
                continue
            cid = x["cliente_id"]
            ant = x.get("mas_antiguo") or {}
            q = f" ({x['quejas']} queja{'s' if x['quejas'] > 1 else ''})" if x.get("quejas") else ""
            alerta("acc_correos", cid, f"{NOMBRE_CLI.get(cid, cid)}: {pl(x['mas_48'], 'correo')} sin contestar de más de 48 h{q}; el más antiguo, {x.get('dias_laborables_max')} días laborables.",
                   cid=cid, desde=fecha(ant.get("desde")), cifra=x["mas_48"], gravedad="alta",
                   abrir_en=[{"herramienta": "desk", "texto": f"Abrir {ant.get('numero', 'el ticket')} en Desk", "url": ant.get("url")}] if ant.get("url") else [abrir(cid, "desk")],
                   detalle=[f"Asunto del más antiguo: «{ant.get('asunto')}»" if ant.get("asunto") else None],
                   extra={"ticket": ant.get("numero")})      # A2: «Ir» abre ESE correo en la Bandeja
        coherencia("Correos de clientes > 48 h (sin automáticos)", "Bandeja", sum(x.get("mas_48") or 0 for x in pc.get("clientes", [])), suma_cifra("acc_correos"))
    band = leer("bandeja/bandeja")
    if band:
        for x in band.get("llamadas", []):
            cid = x.get("cliente_id")
            alerta("acc_llamadas", x["id"], f"{pl(x.get('llamadas') or 0, 'llamada perdida', 'llamadas perdidas')} del número {x.get('numero_oculto')} sin devolver; la última, el {x.get('ultima', '')[8:10]}-{x.get('ultima', '')[5:7]}.",
                   cid=cid, desde=fecha(x.get("primera")), cifra=x.get("llamadas"), dueno=None if cid else "mili",
                   abrir_en=[{"herramienta": "zadarma", "texto": "Abrir en Zadarma", "url": x.get("url")}], ir=f"bandeja/{x['id']}")
        coherencia("Llamadas sin devolver", "Bandeja", (band.get("resumen") or {}).get("llamadas"), n_tipo("acc_llamadas"))
    fuente("Bandeja", "bandeja/por_cliente", pc, len(ALERTAS) - antes)

    # 6.3 informes mensuales · rojo el día 6 (aviso a Mili)
    antes = len(ALERTAS)
    inf = leer("informes/informes")
    if inf:
        for f in inf.get("filas", []):
            if not f.get("aviso_mili"):
                continue
            cid = f["cliente_id"]
            m = f["mes"]
            mes_txt = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"][int(m[5:7])]
            hecho = "hecho en ClickUp pero sin enviar desde Desk" if f.get("hecho") else "sin hacer ni enviar"
            alerta("acc_informe", f"{cid}:{m}", f"{f['cliente']}: el informe de {mes_txt} está {hecho} (plazo, día 5).", cid=cid,
                   desde=fecha(f.get("limite")) + timedelta(days=1) if fecha(f.get("limite")) else None, cifra=f.get("dias_retraso"),
                   abrir_en=[{"herramienta": "clickup", "texto": "Abrir la tarea en ClickUp", "url": (f.get("tarea") or {}).get("url")} if isinstance(f.get("tarea"), dict) and f["tarea"].get("url") else abrir(cid, "clickup")],
                   extra={"mes": m})
        coherencia("Informes en rojo con aviso a Mili", "Informes mensuales", sum(1 for f in inf.get("filas", []) if f.get("aviso_mili")), n_tipo("acc_informe"))
    fuente("Informes mensuales", "informes/informes", inf, len(ALERTAS) - antes, ((inf or {}).get("_meta") or {}).get("generado"))

    # 6.4 incidencias de configuración que no salen en otro módulo (las de Desk > 48 h y llamadas ya vienen de la Bandeja)
    antes = len(ALERTAS)
    inc = leer("incidencias/incidencias")
    reglas_inc = {"desk_sin_agente": "acc_sin_agente", "desk_agente_baja": "acc_config", "zadarma_sin_destino": "acc_config", "zadarma_ext_inexistente": "acc_config"}
    if inc:
        for i in inc.get("incidencias", []):
            t = reglas_inc.get(i.get("regla"))
            if not t:
                continue
            cid = i.get("cliente_id")
            alerta(t, i["id"], f"{i.get('titulo')}: {i.get('texto', '').split('. ')[0]}.", cid=cid, desde=fecha(i.get("detectada")),
                   dueno=None if cid else "mili", abrir_en=[{"herramienta": "desk" if "desk" in i["regla"] else "zadarma", "texto": "Abrir la prueba", "url": i.get("prueba")}],
                   ir=f"incidencias/{i['id']}", extra={"incidencia_id": i["id"]})
        coherencia("Incidencias de configuración (Desk y Zadarma)", "Incidencias", sum(1 for i in inc.get("incidencias", []) if i.get("regla") in reglas_inc), n_tipo("acc_sin_agente", "acc_config"))
    fuente("Incidencias", "incidencias/incidencias", inc, len(ALERTAS) - antes)


# =================================================================== 7 · altas
def de_altas():
    doc = leer("nuevos/nuevos")
    antes = len(ALERTAS)
    if not doc:
        return fuente("Clientes nuevos", "nuevos/nuevos", None, 0)
    for a in doc.get("altas", []):
        cid = a["cliente_id"]
        pl = a.get("plazo") or {}
        dueno = (a.get("dueno") or {}).get("id")
        if pl.get("estado") == "rojo":
            tarde = pl.get("dia_encendido")
            alerta("alta_fuera_plazo", cid, f"{a['nombre']}: " + (f"encendida tarde, el día {tarde} (límite, día 12)." if tarde else f"día {a.get('dia')} sin campaña encendida (límite, día 12)."),
                   cid=cid, desde=fecha(pl.get("limite")), cifra=a.get("dia"), dueno=dueno, gravedad="media" if tarde else "alta",
                   abrir_en=[abrir(cid, "clickup"), abrir(cid, "meta")],
                   detalle=[x["texto"] for x in a.get("alertas") or [] if x.get("tipo") in ("config_sin_agendar", "urgente")][:2])
        for x in a.get("alertas") or []:
            if x.get("tipo") == "sin_tareas" and x.get("estado") == "rojo":
                alerta("alta_sin_lista", cid, f"{a['nombre']}: {x['texto'].split(' (')[0]}.", cid=cid, desde=fecha(a.get("firma")), dueno=dueno,
                       abrir_en=[{"herramienta": "clickup", "texto": "Abrir ClickUp", "url": "https://app.clickup.com/90152357276/home"}])
    r = doc.get("resumen", {})
    coherencia("Altas fuera del día 12 (sin encender + encendidas tarde)", "Clientes nuevos", r.get("fuera_de_plazo"), n_tipo("alta_fuera_plazo"))
    coherencia("Altas sin lista de arranque a las 48 h de la firma", "Clientes nuevos", r.get("sin_tareas_48h"), n_tipo("alta_sin_lista"))
    fuente("Clientes nuevos", "nuevos/nuevos", doc, len(ALERTAS) - antes)


# =================================================================== 8 · administración
def de_admin():
    doc = leer("finanzas/finanzas")
    antes = len(ALERTAS)
    if not doc:
        return fuente("Finanzas (administración)", "finanzas/finanzas", None, 0)
    ad = doc.get("admin") or {}
    for f in (ad.get("impagos") or {}).get("filas", []):
        if not f.get("dias") or f["dias"] <= 0:
            continue
        cid = f.get("cliente_id") if f.get("cliente_id") in NOMBRE_CLI else None
        alerta("adm_impago", f.get("doc"), f"{f.get('nombre')}: la factura {f.get('doc')} venció hace {f['dias']} días y no está cobrada.",
               cid=cid, desde=fecha(f.get("vence")), cifra=f["dias"], gravedad="alta" if f["dias"] > 30 else "media",
               abrir_en=[{"herramienta": "holded", "texto": "Abrir en Holded", "url": f.get("holded")}],
               detalle=[f.get("aviso") and f"Aviso: {f['aviso']}", "Devuelta por el banco" if f.get("devuelto") else None],
               extra={"impagado_eur": f.get("importe")})
    for f in ad.get("devueltos") or []:
        cid = f.get("cliente_id") if f.get("cliente_id") in NOMBRE_CLI else None
        alerta("adm_sepa", f.get("doc") or f.get("nombre"), f"{f.get('nombre')}: el banco devolvió el recibo SEPA {f.get('doc') or ''}.".replace(" .", "."),
               cid=cid, desde=fecha(f.get("fecha")), abrir_en=[{"herramienta": "holded", "texto": "Abrir en Holded", "url": f.get("holded")}],
               extra={"impagado_eur": f.get("importe")})
    for f in ad.get("firmas_sin_alta") or []:
        cid = f.get("cliente_id")
        alerta("adm_sin_alta", cid, f"{f.get('nombre')}: firmado el {f.get('firma', '')[8:10]}-{f.get('firma', '')[5:7]} y todavía sin línea en facturación.", cid=cid,
               desde=fecha(f.get("firma")), abrir_en=[{"herramienta": "airtable", "texto": "Abrir el Airtable de facturación", "url": "https://airtable.com/app9OBjN9MiqIQVxI"}],
               detalle=[f"Account: {f.get('account')}" if f.get("account") else None])
    tramos = (ad.get("impagos") or {}).get("tramos", [])
    coherencia("Facturas vencidas sin cobrar", "Finanzas (Sofía)", sum(t.get("n") or 0 for t in tramos if t.get("tramo") != "Sin vencer"), n_tipo("adm_impago"))
    coherencia("Recibos SEPA devueltos", "Finanzas (Sofía)", len(ad.get("devueltos") or []), n_tipo("adm_sepa"))
    coherencia("Firmados sin alta en facturación", "Finanzas (Sofía)", len(ad.get("firmas_sin_alta") or []), n_tipo("adm_sin_alta"))
    fuente("Finanzas (administración)", "finanzas/finanzas", doc, len(ALERTAS) - antes)


# =================================================================== 9 · RRHH
def proximo(mmdd):
    """Próxima fecha (hoy incluido) de un «MM-DD»."""
    try:
        m, d = int(mmdd[:2]), int(mmdd[3:5])
        f = date(HOY.year, m, d)
        return f if f >= HOY else date(HOY.year + 1, m, d)
    except Exception:
        return None


def de_rrhh():
    antes = len(ALERTAS)
    eq = leer("personas_m20/equipo")
    if eq:
        for p in eq.get("personas", []):
            al = p.get("alerta")
            if not al:
                continue
            pid = p["persona_id"]
            alerta("rrhh_alerta", pid, f"{p.get('alias') or p['nombre']} está en alerta: {al['motivos'][0]}.", desde=fecha(al.get("desde")),
                   cifra=len(al["motivos"]), detalle=al["motivos"][1:4], persona_ref=pid,
                   dueno="tomas" if pid == "cecilia" else None,          # nadie es dueña de su propia alerta de RRHH
                   abrir_en=[{"herramienta": "clickup", "texto": "Abrir el panel de horas en ClickUp", "url": "https://app.clickup.com/90152357276/time"}])
        coherencia("Personas en alerta", "Personas", sum(1 for p in eq.get("personas", []) if p.get("alerta")), n_tipo("rrhh_alerta"))
    ve = leer("verdad/equipo")
    if ve:
        for x in ve.get("no_imputan_ayer", []):
            pid = x["persona_id"]
            alerta("rrhh_no_imputa", f"{pid}:{ve.get('ayer')}", f"{corto(pid)} no imputó horas el {ve.get('ayer', '')[8:10]}-{ve.get('ayer', '')[5:7]}.",
                   desde=fecha(ve.get("ayer")), dueno=pid, persona_ref=pid,
                   abrir_en=[{"herramienta": "clickup", "texto": "Imputar en ClickUp", "url": "https://app.clickup.com/90152357276/time"}])
        coherencia("No imputan ayer (avisos, no alertas)", "Horas (verdad del equipo)", len(ve.get("no_imputan_ayer", [])),
                   sum(1 for a in AVISOS if a["tipo"] == "rrhh_no_imputa"))
    # cumpleaños y aniversarios: aviso a Cecilia y a Tomás 7 días antes y el mismo día
    proximos = []
    for p in PERSONAS:
        if not p.get("activo") or p.get("prueba") or p["id"].startswith("setter_"):
            continue
        for tipo, mmdd, txt in (("rrhh_cumple", p.get("cumple_dia_mes"), "cumpleaños"), ("rrhh_aniversario", (p.get("fecha_ingreso") or "")[5:], "aniversario de entrada")):
            f = proximo(mmdd) if mmdd else None
            if not f:
                continue
            dias = (f - HOY).days
            anos = f.year - int(p["fecha_ingreso"][:4]) if tipo == "rrhh_aniversario" else None
            if tipo == "rrhh_aniversario" and anos < 1:
                continue
            proximos.append({"tipo": txt, "persona": corto(p["id"]), "fecha": f.isoformat(), "dias": dias, "anos": anos})
            if dias in range(0, 8):
                cuando = "hoy" if dias == 0 else ("mañana" if dias == 1 else f"en {dias} días, el {f:%d-%m}")
                que = f"cumple años {cuando}" if tipo == "rrhh_cumple" else f"cumple {anos} año{'s' if anos != 1 else ''} en RO {cuando}"
                alerta(tipo, f"{p['id']}:{f.isoformat()}", f"{p.get('alias') or p['nombre']} {que}.", desde=f2s(datetime.combine(f - timedelta(days=7), datetime.min.time()).replace(hour=9)),
                       vence=f2s(datetime.combine(f, datetime.min.time()).replace(hour=18)), gravedad="baja",
                       detalle=["Aviso a Cecilia y a Tomás 7 días antes y el mismo día"])
    fuente("Personas, horas y fechas del equipo", "personas_m20/equipo", eq, len(ALERTAS) - antes)
    return sorted(proximos, key=lambda x: x["dias"])[:12]


# =================================================================== 10 · dirección
def de_direccion():
    antes = len(ALERTAS)
    rel = leer("decisiones/reloj")
    if rel:
        pend = [d for d in rel.get("decisiones", []) if not d.get("respuesta")]
        for d in pend:
            dueno = "constanza" if d.get("tipo") == "para_coti" else "tomas"
            alerta("dir_decision", d["id"], f"{d['titulo']}.", cid=d.get("cliente_id") if d.get("cliente_id") in NOMBRE_CLI and len(d.get("clientes") or []) <= 1 else None,
                   desde=fecha(d.get("creada")), vence=f2s(fecha(d.get("vence"))), dueno=dueno, gravedad="alta",
                   detalle=[d.get("recomendacion") and f"Recomendación: {d['recomendacion']}", f"Lo sube {corto(d.get('quien'))}" if d.get("quien") else None])
        coherencia("Decisiones pendientes con reloj", "Decisiones y rastro", len(pend), n_tipo("dir_decision"))
    for c in VERDAD.get("clientes", []):
        if c.get("sin_account") and "mantenimiento" not in c["sin_account"]:
            alerta("dir_sin_account", c["cliente_id"], f"{c['nombre']}: {c['sin_account']}.", cid=c["cliente_id"], dueno="mili")
        elif c.get("sin_account"):
            alerta("dir_sin_account", c["cliente_id"], f"{c['nombre']}: {c['sin_account']} (confirmar que no necesita account).", cid=c["cliente_id"], dueno="mili", gravedad="baja")
    coherencia("Clientes sin account", "Verdad única", (VERDAD.get("resumen") or {}).get("sin_account"), n_tipo("dir_sin_account"))
    fuente("Decisiones y rastro", "decisiones/reloj", rel, len(ALERTAS) - antes)


# =================================================================== conexiones (salud N11, formato N4)
def de_salud():
    """A8: data/conexiones/salud.json → «alertas» ya hechas por la salud de conexiones (id, tipo, departamento, dueño,
    jefe, cadena de escalado, desde, plazo, gravedad, qué hacer, ir). Aquí solo se reparten: no se recalcula nada."""
    try:
        doc = json.loads(SALUD.read_text())
    except Exception:
        doc = None
    antes = len(ALERTAS)
    if not isinstance(doc, dict):
        return FUENTES.append({"modulo": "Salud de conexiones (Ajustes)", "fichero": "data/conexiones/salud.json", "leido": False, "alertas": 0,
                               "generado": None, "nota": "Sin fichero de salud de conexiones: sus alertas entran en cuanto exista."})
    xs = [x for x in doc.get("alertas") or [] if isinstance(x, dict) and x.get("id")]
    for x in xs:
        dep = x.get("departamento") if x.get("departamento") in DEPTOS else "conexiones"       # «tecnico» → Conexiones
        dueno = x.get("dueno_id") if PER.get(x.get("dueno_id"), {}).get("activo") else None
        ir = str(x.get("ir") or "").removeprefix("#/") or None
        a = alerta("conexion_caida", str(x["id"]).split(":", 1)[-1], (x.get("motivo") or x.get("titulo") or "La conexión falla.").rstrip(".") + ".",
                   desde=fecha(x.get("desde")), gravedad=x.get("gravedad") if x.get("gravedad") in ("alta", "media", "baja") else None,
                   plazo_h=x.get("plazo_h") if isinstance(x.get("plazo_h"), (int, float)) else None, dueno=dueno, ir=ir,
                   detalle=[x.get("titulo"), x.get("que_hacer") and f"Qué hacer: {x['que_hacer']}"])
        a.update({"id": str(x["id"]), "departamento": dep, "titulo": (x.get("titulo") or REGLA["conexion_caida"]["titulo"])[:120],
                  "jefe_id": x.get("jefe_id") if x.get("jefe_id") in PER else DEPTOS[dep]["jefe"],
                  "fuente": x.get("fuente") or REGLA["conexion_caida"]["fuente"], "comprueba": x.get("comprueba") or REGLA["conexion_caida"]["comprueba"],
                  "conexion": str(x["id"]).split(":", 1)[-1]})
        cad = [p for p in (x.get("escalado_cadena") or []) if p in PER][:3]
        if cad and cad[0] == a["dueno_id"]:
            a["escalado_cadena"] = cad
    coherencia("Conexiones caídas o que caducan", "Ajustes › Conexiones (salud)", len(xs), n_tipo("conexion_caida"))
    fuente("Salud de conexiones (Ajustes)", "conexiones/salud", doc, len(ALERTAS) - antes)


# =================================================================== A2 · «Ir» al objeto exacto
# Cada alerta lleva: ir (ruta de la app al OBJETO: el correo, la ficha y su pestaña, la subcuenta, la campaña…),
# ir_texto (el verbo del botón), ir_alt (la pantalla de respaldo si quien mira no ve la del objeto) e ir_objeto (si
# llega al objeto o solo a una pantalla). Si una pantalla todavía no sabe abrir el objeto por ruta, ir_ideal dice cuál
# haría falta (apuntado en ../dudas_pintura.md, «A2 · necesita ruta»).
_BDJ = leer("bandeja/bandeja") or {}
BANDEJA_IDS = {x.get("id") for x in (_BDJ.get("correos") or []) + (_BDJ.get("llamadas") or []) if x.get("id")}


def rutas_de(a):
    t, cid = a["tipo"], a.get("cliente_id")
    sub = (a.get("ir") or "").removeprefix("#/").split("/")
    ficha = (lambda pest: f"ficha/{cid}/{pest}") if cid else (lambda pest: None)
    if t == "acc_correos":
        did = f"t-{a.get('ticket')}" if a.get("ticket") else None
        if did in BANDEJA_IDS:
            return f"bandeja/{did}", "Contestar el correo", True, ficha("comunicacion"), None
        return ficha("comunicacion") or "bandeja", "Ver sus correos", bool(cid), "bandeja", None
    if t == "acc_llamadas":
        return a["ir"].removeprefix("#/"), "Abrir la llamada", len(sub) > 1, "bandeja", None
    if t == "acc_critico":
        return ficha("resumen"), "Abrir su ficha", True, f"en-rojo/{cid}", None
    if t == "acc_sin_reunion":
        return ficha("comunicacion"), "Ver sus reuniones", True, "reuniones", None
    if t == "acc_informe":
        return ficha("informes"), "Ver su informe", True, "informes-mensuales", None
    if t in ("acc_sin_agente", "acc_config"):
        return a["ir"].removeprefix("#/"), "Abrir la incidencia", len(sub) > 1, "incidencias", None
    if t.startswith("web_"):
        clave = a["id"].split(":", 1)[1].split(":")[0]
        # R15a: SEO › Webs ya abre la fila de la web por ruta; quien no ve SEO va a la ficha › Web
        return f"seo-web/webs/{clave}", "Ver su web", True, ficha("web") or "seo-web", None
    if t.startswith(("seo_", "crm_", "pub_", "redes_", "alta_")):
        return a["ir"].removeprefix("#/"), {"seo": "Ver su SEO", "crm": "Abrir su CRM", "pub": "Ver su captación", "redes": "Ver sus redes",
                                             "alta": "Ver su alta"}[t.split("_")[0]], len(sub) > 1, sub[0], None
    if t.startswith("adm_"):
        return f"finanzas/cobros/{a['id'].split(':', 1)[1]}", "Abrir el cobro", True, None, None   # R15a: Finanzas abre el cobro por ruta
    if t.startswith("rrhh_"):
        pid = a.get("persona_id") or a["id"].split(":", 1)[1].split(":")[0]
        return a["ir"].removeprefix("#/"), "Abrir Personas" if a["ir"].endswith("personas") else "Abrir Horas", False, None, f"personas/{pid}"
    if t == "dir_decision":
        return f"decisiones/reloj/{a['id'].split(':', 1)[1]}", "Abrir la decisión", True, "decisiones", None   # R15a
    if t == "dir_sin_account":
        return (f"ajustes/asignaciones/{cid}" if cid else "ajustes/asignaciones"), "Asignar account", bool(cid), ficha("resumen"), None   # R15a
    if t.startswith("gbp_"):   # SEO › detalle del cliente (pestaña de la ficha de Google); quien no ve SEO, a su ficha › Web
        return (f"seo-web/{cid}" if cid else "seo-web"), "Ver su ficha de Google", bool(cid), ficha("web"), None
    if t in ("hosting_vps", "hosting_cuenta"):   # Ajustes › Conexiones › Hostinger (la tarjeta de la conexión)
        return "ajustes/conexiones/hostinger", "Ver Hostinger", True, "conexiones/hostinger", None
    if t == "conexion_caida":
        if a.get("conexion"):   # R15a: Ajustes › Conexiones abre la tarjeta por ruta; el técnico, su pantalla «Conexiones»
            return f"ajustes/conexiones/{a['conexion']}", "Abrir la conexión", True, f"conexiones/{a['conexion']}", None
        return (a.get("ir") or "#/ajustes/conexiones").removeprefix("#/"), "Abrir la conexión", False, None, None
    return (a.get("ir") or "").removeprefix("#/"), None, len(sub) > 1, None, None


def poner_rutas(lista):
    for a in lista:
        ir, texto, objeto, alt, ideal = rutas_de(a)
        if ir:
            a["ir"] = "#/" + ir.rstrip("/")
        a["ir_texto"] = texto
        a["ir_objeto"] = bool(objeto)
        a["ir_alt"] = "#/" + alt if alt else None
        if ideal:
            a["ir_ideal"] = "#/" + ideal


# =================================================================== estados (local.db, solo lectura) y escalado
# A8: además de los estados de una en una, «alerta_posponer» (vista_previa.hasta) y «alerta_lote» (vista_previa:
# ids[], accion lo_tengo|resuelta|no_aplica|posponer, motivo, hasta). Un lote se despliega en una entrada por alerta.
# Nadie pospone (ni despacha en lote) alertas ajenas: si quien lo manda no está en la cadena de la alerta (dueño, jefe,
# Mili/Tomás) ni ve toda la agencia, la entrada se ignora y queda en «rechazadas» con el motivo.
DE_LOTE = {"lo_tengo": "lo_tengo", "resuelta": "resuelta", "no_aplica": "no_aplica", "posponer": "posponer"}
RECHAZADAS = []


def leer_estados():
    """Acciones de cada alerta (tipos alerta_*) en la cola de acciones, en orden. creada va en UTC.

    Con DATABASE_URL (la nube) la cola está en Postgres. Sin ella, SQLite, como hasta ahora.
    """
    try:
        if os.environ.get("DATABASE_URL"):
            # F5.11: misma consulta. Se cierra la transacción antes de devolver la conexión al pool.
            sys.path.insert(0, str(AQUI / "despliegue"))
            import base as _B
            con = _B.conectar()
            try:
                filas = con.execute("SELECT * FROM acciones WHERE modulo='alertas' ORDER BY id").fetchall()
            finally:
                if getattr(con, "_con", None) is not None and con.in_transaction:
                    con.rollback()
                con.close()
        else:
            db = DB
            if not db.exists():
                return {}
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            con.row_factory = sqlite3.Row
            filas = con.execute("SELECT * FROM acciones WHERE modulo='alertas' ORDER BY id").fetchall()
            con.close()
    except Exception:
        return {}
    out = {}
    for r in filas:
        h = datetime.fromisoformat(r["creada"]).replace(tzinfo=ZoneInfo("UTC")).astimezone(MADRID).replace(tzinfo=None)
        try:
            vp = json.loads(r["vista_previa"] or "{}") or {}
        except Exception:
            vp = {}
        if r["tipo"] == "alerta_lote":
            acc = DE_LOTE.get(vp.get("accion"))
            for oid in (vp.get("ids") or [])[:500] if acc else []:
                out.setdefault(str(oid), {"historia": []})["historia"].append(
                    {"tipo": acc, "quien": r["quien"], "hora": f2s(h), "texto": r["texto"], "hasta": vp.get("hasta"), "lote": r["id"],
                     "motivo": vp.get("motivo")})
            continue
        e = out.setdefault(r["objeto"], {"historia": []})
        e["historia"].append({"tipo": r["tipo"].replace("alerta_", ""), "quien": r["quien"], "hora": f2s(h), "texto": r["texto"],
                              **({"hasta": vp.get("hasta")} if r["tipo"] == "alerta_posponer" else {})})
    return out


ESTADOS_ACCION = {"vista": "vista", "lo_tengo": "lo_tengo", "resuelta": "resuelta", "no_aplica": "no_aplica", "reabrir": "nueva", "posponer": "pospuesta"}
SOLO_SUYAS = {"posponer", "lo_tengo", "resuelta", "no_aplica", "reabrir"}   # R16 (N5): todo menos «vista»; y todo lo del lote


def puede_actuar(pid, a):
    """Quién puede posponer o despachar en lote una alerta: su cadena (dueño → jefe → Mili/Tomás), el jefe del
    departamento o quien ve toda la agencia (dirección y operaciones). El resto, no: es una alerta ajena."""
    p = PER.get(pid)
    return bool(p) and (pid in (a.get("escalado_cadena") or []) or pid == a.get("jefe_id") or es_todo(p))


def entrada_valida(x, a):
    """None si vale; si no, el motivo (alerta ajena o fecha de «posponer» imposible)."""
    if (x["tipo"] in SOLO_SUYAS or x.get("lote")) and not puede_actuar(x["quien"], a):
        return "no es suya (ni de su departamento): nadie cambia alertas ajenas"
    if x["tipo"] == "posponer":
        hasta, hora = fecha(x.get("hasta")), fecha(x.get("hora"))
        if not hasta or not hora or hasta <= hora or hasta > hora + timedelta(days=POSPONER_MAX_DIAS):
            return f"fecha de vuelta no válida (de mañana a {POSPONER_MAX_DIAS} días)"
    if x["tipo"] == "no_aplica" and x.get("lote") and len((x.get("motivo") or "").strip()) < 4:
        return "«no aplica» sin motivo"
    return None


def aplicar_estados(memoria, estados):
    """Primera vez vista, plazo, vence, estado (también «pospuesta») y escalado de cada alerta."""
    gen = AHORA
    for a in ALERTAS:
        m = memoria.get(a["id"])
        det = fecha(m["detectada"]) if m else AHORA
        a["detectada"] = f2s(det)
        if not a.get("vence") and a.get("plazo_h"):
            a["vence"] = f2s(det + timedelta(hours=a["plazo_h"]))
        e = estados.get(a["id"]) or {}
        hist = []
        for x in e.get("historia", []):
            mot = entrada_valida(x, a) if x["tipo"] in ESTADOS_ACCION else None
            if mot:
                RECHAZADAS.append({"alerta": a["id"], "quien": x["quien"], "tipo": x["tipo"], "hora": x["hora"], "lote": x.get("lote"), "motivo": mot,
                                   "dueno_id": a["dueno_id"]})
                continue
            hist.append(x)
        ult = next((x for x in reversed(hist) if x["tipo"] in ESTADOS_ACCION), None)
        estado = ESTADOS_ACCION[ult["tipo"]] if ult else "nueva"
        a["historia"] = [{k: v for k, v in x.items() if k != "motivo"} for x in hist[-8:]]
        # «Resuelta» se comprueba con el dato siguiente: si esta generación es posterior y la alerta sigue, se reabre.
        if estado == "resuelta" and fecha(ult["hora"]) and fecha(ult["hora"]) < gen:
            estado = "reabierta"
            a["reabierta"] = f"Marcada resuelta por {corto(ult['quien'])} a las {ult['hora'][11:]} del {ult['hora'][8:10]}-{ult['hora'][5:7]}; el dato de las {gen:%H:%M} sigue igual."
        # «Posponer»: hasta la fecha de vuelta no cuenta, no vence y no escala. Al volver, el plazo empieza de nuevo.
        if estado == "pospuesta":
            hasta = fecha(ult.get("hasta"))
            if a.get("vence") and a.get("plazo_h"):
                a["vence_antes"] = a["vence"]
                a["vence"] = f2s(max(fecha(a["vence"]), hasta + timedelta(hours=a["plazo_h"])))
            a["pospuesta"] = {"hasta": f2s(hasta), "quien": ult["quien"], "hora": ult["hora"]}
            if hasta <= AHORA:
                estado = "nueva"
                a["volvio"] = f"Pospuesta por {corto(ult['quien'])} hasta el {hasta:%d-%m %H:%M}: vuelve con el plazo de nuevo."
        a["estado"] = estado
        if ult:
            a["estado_por"] = {"quien": ult["quien"], "hora": ult["hora"], "texto": ult.get("texto")}
        # Escalado (la misma regla que la pantalla): pasado el plazo sin «Lo tengo» → responsable del área; cada plazo
        # igual que pasa, un escalón más de la cadena (… → Mili → Tomás). Ni las cerradas ni las pospuestas escalan.
        v = fecha(a.get("vence"))
        nivel = 0
        if v and estado in ("nueva", "vista", "reabierta"):
            plazo = timedelta(hours=a.get("plazo_h") or 24)
            if AHORA >= v:
                nivel = 1 + int((AHORA - v) / plazo)
        if not a.get("escalado_cadena"):
            a["escalado"] = {"nivel": 0, "a_id": None, "texto": "Responsable actual por confirmar."}
            a["responsable_ahora"] = None
            a["escalado_bloqueado"] = True
            continue
        a.pop("escalado_bloqueado", None)
        nivel = min(nivel, len(a["escalado_cadena"]) - 1)
        a["escalado"] = {"nivel": nivel, "a_id": a["escalado_cadena"][nivel], "texto": None if not nivel else
                         f"Pasó el plazo sin «Lo tengo»: sube a {corto(a['escalado_cadena'][nivel])}"}
        a["responsable_ahora"] = a["escalado_cadena"][nivel]


# =================================================================== A8 · UNA sola definición de cada contador
# La usan las tarjetas, los chips y la cabecera de Alertas (modulos/alertas.js la lee de aquí y la interpreta igual) y
# el bloque de Mi día (mi_dia.total, urgentes, plazo_pasado, escaladas_a_mi). Antes salían 3 cifras para «mías»
# (14, 22 y 8) y 0 frente a 8 para «plazo pasado». pruebas_coherencia.py lo comprueba con los ficheros.
# Hechos de cada alerta: estado, gravedad, dueno, responsable (a quien le toca ahora), nivel (escalado), vencida.
# Condición: [nombre_de_otra_definicion] · [hecho, op, valor] con op = | != | en | > y valor «yo» = quien mira ·
# ["alguna", [condiciones]].
DEFINICIONES = {
    "abierta": {"texto": "Abierta: nueva, vista, reabierta o con «Lo tengo». Las pospuestas, resueltas y «no aplica» no cuentan.",
                "si": [["estado", "en", ["nueva", "vista", "reabierta", "lo_tengo"]]]},
    "mia": {"texto": "Tuya: eres su dueño o te ha llegado escalada (eres quien responde ahora).",
            "si": [["alguna", [["dueno", "=", "yo"], ["responsable", "=", "yo"]]]]},
    "urgente": {"texto": "Urgente: gravedad alta.", "si": [["gravedad", "=", "alta"]]},
    "plazo_pasado": {"texto": "Plazo pasado: abierta, sin «Lo tengo» y con el vencimiento ya pasado.",
                     "si": [["abierta"], ["estado", "!=", "lo_tengo"], ["vencida", "=", True]]},
    "escalada": {"texto": "Escalada: abierta y ha subido al responsable del área, a Mili o a Tomás porque pasó el plazo sin «Lo tengo».",
                 "si": [["abierta"], ["nivel", ">", 0]]},
    "escalada_a_mi": {"texto": "Escalada a ti: te ha llegado a ti y no eres su dueño.",
                      "si": [["escalada"], ["responsable", "=", "yo"], ["dueno", "!=", "yo"]]},
    "pospuesta": {"texto": "Pospuesta: vuelve sola en la fecha elegida; mientras, no cuenta ni escala.", "si": [["estado", "=", "pospuesta"]]},
    "cerrada": {"texto": "Cerrada: resuelta o «no aplica».", "si": [["estado", "en", ["resuelta", "no_aplica"]]]},
}
# Contador = todas estas definiciones a la vez (lo que se pinta en tarjetas, chips, cabecera y Mi día).
CONTADORES = {
    "mias": ["abierta", "mia"], "urgentes": ["abierta", "mia", "urgente"], "plazo_pasado": ["mia", "plazo_pasado"],
    "escaladas_a_mi": ["escalada_a_mi"], "pospuestas": ["mia", "pospuesta"],
    "en_vista": ["abierta"], "urgentes_en_vista": ["abierta", "urgente"], "escaladas_en_vista": ["escalada"], "cerradas": ["cerrada"],
}


def hechos(a):
    v = fecha(a.get("vence"))
    return {"estado": a.get("estado") or "nueva", "gravedad": a.get("gravedad"), "dueno": a.get("dueno_id"),
            "responsable": None if a.get("escalado_bloqueado") else a.get("responsable_ahora") or a.get("dueno_id"), "nivel": (a.get("escalado") or {}).get("nivel") or 0,
            "vencida": bool(v and v <= AHORA)}


def cumple(nombre, H, yo, defs=DEFINICIONES):
    return all(_cond(c, H, yo, defs) for c in defs[nombre]["si"])


def _cond(c, H, yo, defs):
    if len(c) == 1:
        return cumple(c[0], H, yo, defs)
    if c[0] == "alguna":
        return any(_cond(x, H, yo, defs) for x in c[1])
    campo, op, val = c
    val = yo if val == "yo" else val
    x = H.get(campo)
    return {"=": lambda: x == val, "!=": lambda: x != val, "en": lambda: x in val, ">": lambda: (x or 0) > val}[op]()


def contar(lista, yo, nombre):
    return sum(1 for a in lista if all(cumple(d, hechos(a), yo) for d in CONTADORES[nombre]))


def contadores(lista, yo):
    return {k: contar(lista, yo, k) for k in CONTADORES}


# =================================================================== visibilidad por persona
CRUDO = {"asignaciones": ASIG, "personas": PERSONAS, "clientes": CLIENTES_CONTRATO}


def es_todo(p):
    return bool(set(p.get("puestos", [])) & {"direccion", "operaciones"})


def jefe_de_deps(pid):
    return {d for d, x in DEPTOS.items() if x["jefe"] == pid}


def visibles(p, lista=None):
    cp = P.contexto(p, CRUDO)
    todo = es_todo(p)
    deps = jefe_de_deps(p["id"])
    out = []
    for a in (ALERTAS if lista is None else lista):
        suya = a["dueno_id"] == p["id"] or a.get("responsable_ahora") == p["id"]
        copia = p["id"] in (a.get("copia_a") or [])          # ficha de Google: el account del cliente la ve (sin ser dueño)
        if not (todo or suya or copia or a["departamento"] in deps or (a["departamento"] == "rrhh" and "rrhh" in p.get("puestos", []))):
            continue
        if a["departamento"] == "rrhh" and a["tipo"] != "rrhh_no_imputa" and not (todo or "rrhh" in p.get("puestos", [])):
            continue      # personas en alerta, cumpleaños y aniversarios: Cecilia, Mili y Tomás
        if a.get("cliente_id") and not todo and not P.ver(p, {"tipo": "cliente_detalle", "cliente_id": a["cliente_id"]}, cp)["ok"]:
            continue
        b = dict(a)
        cid = a.get("cliente_id")
        if not P.ver(p, {"tipo": "inversion", "cliente_id": cid}, cp)["ok"]:
            b.pop("gasto_7d", None)
            b = P.sin_importes(b)
        if not P.ver(p, {"tipo": "cobros"}, cp)["ok"]:
            b.pop("impagado_eur", None)
        b["mia"] = suya
        out.append(b)
    alcance = "todas" if todo else ("departamento" if deps or "rrhh" in p.get("puestos", []) else "mias")
    return out, alcance, deps


ORD_G = {"alta": 0, "media": 1, "baja": 2}
ORD_E = {"reabierta": 0, "nueva": 1, "vista": 2, "lo_tengo": 3, "resuelta": 4, "no_aplica": 5}
ABIERTAS = ("nueva", "vista", "reabierta", "lo_tengo")


def orden(a):
    v = fecha(a.get("vence")) or datetime(2100, 1, 1)
    return (0 if a["escalado"]["nivel"] else 1, ORD_G[a["gravedad"]], ORD_E.get(a["estado"], 9), v)


def de_contador(lista, yo, nombre):
    return [a for a in lista if all(cumple(d, hechos(a), yo) for d in CONTADORES[nombre])]


def resumen_texto(p, mias):
    """Texto listo para notificación (escritorio, móvil o correo cuando haya servidor). Corto, sin jerga.
    A8: las cifras salen de CONTADORES (la misma definición que la pantalla y Mi día)."""
    ab = de_contador(mias, p["id"], "mias")
    pasadas = de_contador(mias, p["id"], "plazo_pasado")
    altas = de_contador(mias, p["id"], "urgentes")
    nombre = (p.get("alias") or p["nombre"].split()[0])
    if not ab:
        return {"titulo": f"{nombre}, hoy no tienes alertas", "texto": "Nada que atender. Buen día.", "lineas": [], "n": 0}
    lineas = []
    for a in sorted(ab, key=orden)[:5]:
        v = fecha(a.get("vence"))
        cuando = "plazo pasado" if v and v <= AHORA else (f"vence hoy a las {v:%H:%M}" if v and v.date() == HOY else (f"vence el {v:%d-%m}" if v else "aviso"))
        lineas.append(f"• {a['motivo']} ({cuando})")
    t = f"{nombre}, tienes {len(ab)} alerta{'s' if len(ab) != 1 else ''}"
    if altas:
        t += f", {len(altas)} urgente{'s' if len(altas) != 1 else ''}"
    if pasadas:
        t += f" y {len(pasadas)} con el plazo pasado"
    return {"titulo": t + ".", "texto": t + ".\n" + "\n".join(lineas) + ("\n…y %d más en Alertas del departamento." % (len(ab) - 5) if len(ab) > 5 else ""),
            "lineas": lineas, "n": len(ab), "urgentes": len(altas), "pasadas": len(pasadas)}


def bloque_mi_dia(vis, yo):
    """Mi día: las MISMAS cifras que la pantalla de Alertas (CONTADORES) y las 5 primeras de «mías»."""
    k = contadores(vis, yo)
    ab = sorted(de_contador(vis, yo, "mias"), key=orden)
    return {
        "total": k["mias"], "urgentes": k["urgentes"], "plazo_pasado": k["plazo_pasado"], "escaladas_a_mi": k["escaladas_a_mi"],
        "pospuestas": k["pospuestas"], "contadores": k,
        "primeras": [{"id": a["id"], "motivo": a["motivo"], "departamento": DEPTOS[a["departamento"]]["nombre"], "gravedad": a["gravedad"],
                      "vence": a.get("vence"), "cliente_id": a.get("cliente_id"), "ir": a["ir"], "ir_texto": a.get("ir_texto"),
                      "estado": a["estado"]} for a in ab[:5]],
        "ruta": "#/alertas",
    }


# =================================================================== main
def main():
    if not ESTADO.exists() and ESTADO_ANTIGUO.exists() and not os.environ.get("RO_ALERTAS_ESTADO"):
        ESTADO.parent.mkdir(parents=True, exist_ok=True)   # L-29: primera vez en el sitio nuevo → se hereda el estado de antes
        ESTADO.write_text(ESTADO_ANTIGUO.read_text())
    memoria = json.loads(ESTADO.read_text()) if ESTADO.exists() else {}
    de_webs(); de_modular(); de_hostinger(); de_gbp(); de_seo(); de_crm(); de_captacion(); de_redes(); de_accounts(); de_altas(); de_admin()
    proximos = de_rrhh()
    de_direccion()
    de_salud()
    poner_rutas(ALERTAS)
    poner_rutas(AVISOS)

    vistos = set()
    for a in ALERTAS:                     # ids únicos (una alerta por concepto)
        while a["id"] in vistos:
            a["id"] += "+"
        vistos.add(a["id"])
    estados = leer_estados()
    aplicar_estados(memoria, estados)

    # memoria: primera vez vista y cerradas (comprobadas con el dato nuevo)
    actuales = {a["id"] for a in ALERTAS}
    cerradas = memoria.get("_cerradas", [])
    for k, m in list(memoria.items()):
        if k.startswith("_") or k in actuales:
            continue
        e = estados.get(k) or {}
        ult = next((x for x in reversed(e.get("historia", [])) if x["tipo"] in ESTADOS_ACCION), None)
        cerradas.append({**{c: m.get(c) for c in ("motivo", "departamento", "cliente_id", "dueno_id", "detectada")}, "id": k,
                         "cerrada": f2s(AHORA), "como": "comprobada" if ult and ult["tipo"] == "resuelta" else "desaparecio_sola",
                         "marcada_por": ult and ult["quien"]})
        memoria.pop(k)
    for a in ALERTAS:
        memoria.setdefault(a["id"], {"detectada": a["detectada"]})
        memoria[a["id"]].update({c: a.get(c) for c in ("motivo", "departamento", "cliente_id", "dueno_id")})
        memoria[a["id"]]["ultima_vez"] = f2s(AHORA)
    memoria["_cerradas"] = [c for c in cerradas if (fecha(c["cerrada"]) or AHORA) >= AHORA - timedelta(days=14)][-200:]

    ALERTAS.sort(key=orden)
    por_dep = {d: {"nombre": x["nombre"], "icono": x["icono"], "jefe_id": x["jefe"], "jefe": corto(x["jefe"]), "jefe_origen": x["jefe_origen"], "pendiente": x.get("pendiente"),
                   "abiertas": sum(1 for a in ALERTAS if a["departamento"] == d and a["estado"] in ABIERTAS),
                   "urgentes": sum(1 for a in ALERTAS if a["departamento"] == d and a["gravedad"] == "alta" and a["estado"] in ABIERTAS),
                   "escaladas": sum(1 for a in ALERTAS if a["departamento"] == d and a["escalado"]["nivel"])} for d, x in DEPTOS.items()}
    comun = {
        "formato": 1, "modulo": "alertas", "generado": f2s(AHORA), "hoy": HOY.isoformat(),
        "reglas": [{**{k: v for k, v in r.items()}, "departamento": DEPTOS[r["dep"]]["nombre"]} for r in REGLAS],
        "departamentos": por_dep, "no_medible": NO_MEDIBLE, "fuentes": FUENTES,
        "escalado": ESC.config().get("cadena_alertas_texto") or "Si pasa el plazo sin «Lo tengo», sube al responsable del área; si pasa otro plazo igual, a Mili; y si pasa otro más, a Tomás.",
        "estados": {"nueva": "Nadie la ha mirado", "vista": "Alguien la ha visto", "lo_tengo": "Su dueño se encarga (para el escalado)",
                    "resuelta": "Marcada resuelta: se comprueba con el dato siguiente", "reabierta": "Se marcó resuelta y el dato nuevo dice que sigue",
                    "no_aplica": "No aplica, con motivo", "pospuesta": "Pospuesta hasta una fecha: no cuenta ni escala; vuelve sola con el plazo de nuevo"},
        # A8: la definición ÚNICA de cada contador (tarjetas, chips, cabecera y Mi día) y el tope de «posponer».
        "definiciones": DEFINICIONES, "contadores_def": CONTADORES, "posponer_max_dias": POSPONER_MAX_DIAS,
        "envio": "El resumen diario sale como texto listo para notificar; el envío real (escritorio, móvil o correo) llega con el servidor (W1).",
    }
    SALIDA.mkdir(parents=True, exist_ok=True)
    todas = {**comun, "alcance": "todas", "alertas": ALERTAS, "avisos": AVISOS, "coherencia": COHERENCIA, "cerradas": memoria["_cerradas"][-50:], "proximos_rrhh": proximos,
             "resumenes": {}, "rechazadas": RECHAZADAS[-100:],
             "ir_objeto": {"con_objeto": sum(1 for a in ALERTAS if a.get("ir_objeto")), "total": len(ALERTAS),
                           "falta_ruta": sorted({a["ir_ideal"].split("/")[1] + "/" + (a["ir_ideal"].split("/")[2] if a["ir_ideal"].count("/") > 2 else "<id>")
                                                 for a in ALERTAS if a.get("ir_ideal") and not a.get("ir_objeto")})}}
    escritas = 0
    for p in PERSONAS:
        if not p.get("activo") or not p.get("puestos"):
            continue
        vis, alcance, deps = visibles(p)
        avisos_p = visibles(p, AVISOS)[0]
        mias = [a for a in vis if a["mia"]]
        rd = resumen_texto(p, mias)
        todas["resumenes"][p["id"]] = rd
        mi = bloque_mi_dia(vis, p["id"])
        es_todo_ = alcance == "todas"
        salida = {**comun, "persona_id": p["id"], "alcance": alcance, "jefe_de": sorted(deps), "alertas": vis,
                  "resumen_diario": rd, "mi_dia": mi, "avisos": avisos_p, "contadores": mi["contadores"],
                  "rechazadas": [x for x in RECHAZADAS if es_todo_ or x["quien"] == p["id"] or x["dueno_id"] == p["id"]][-30:],
                  "equipo_resumen": [{"persona_id": q["id"], **{k: v for k, v in todas["resumenes"].get(q["id"], {}).items() if k != "texto"}}
                                     for q in PERSONAS if q.get("activo")] if es_todo_ else None,
                  "coherencia": COHERENCIA if es_todo_ else None,
                  "cerradas": [c for c in memoria["_cerradas"] if es_todo_ or c.get("dueno_id") == p["id"]][-30:],
                  "proximos_rrhh": proximos if (es_todo_ or "rrhh" in p.get("puestos", [])) else None}
        if not es_todo_:
            salida["departamentos"] = {d: x for d, x in por_dep.items() if d in deps or any(a["departamento"] == d for a in vis)}
        (SALIDA / f"p_{p['id']}.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1))
        escritas += 1
    # completar resúmenes de los que se generaron después en el bucle (equipo_resumen de Tomás y Mili)
    for pid in ("tomas", "mili"):
        f = SALIDA / f"p_{pid}.json"
        if f.exists():
            d = json.loads(f.read_text())
            d["equipo_resumen"] = [{"persona_id": q["id"], **{k: v for k, v in todas["resumenes"].get(q["id"], {}).items() if k != "texto"}}
                                   for q in PERSONAS if q.get("activo") and q["id"] in todas["resumenes"]]
            f.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    (SALIDA / "alertas.json").write_text(json.dumps(todas, ensure_ascii=False, indent=1))
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps(memoria, ensure_ascii=False, indent=1))

    c = Counter(a["departamento"] for a in ALERTAS)
    print(f"{len(ALERTAS)} alertas (+{len(AVISOS)} avisos de horas, sin escalado) · " + " · ".join(f"{DEPTOS[d]['nombre']} {c[d]}" for d in ORDEN_DEP))
    print(f"{escritas} ficheros por persona · coherencia: {sum(x['ok'] for x in COHERENCIA)}/{len(COHERENCIA)} cuadran")
    io = todas["ir_objeto"]
    print(f"A2 · «Ir» al objeto en {io['con_objeto']} de {io['total']} ({round(100 * io['con_objeto'] / max(io['total'], 1))} %) · sin ruta todavía: {', '.join(io['falta_ruta']) or '—'}")
    print(f"A8 · pospuestas {sum(1 for a in ALERTAS if a['estado'] == 'pospuesta')} · rechazadas (ajenas o fecha imposible) {len(RECHAZADAS)}")
    for x in COHERENCIA:
        if not x["ok"]:
            print("  NO CUADRA:", x)


if __name__ == "__main__":
    main()
