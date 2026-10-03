"""Utilidades comunes de la capa de datos (E1). Solo librería estándar.

- Rutas de origen (todas de SOLO LECTURA) y de salida.
- slug() idéntico al de build_data.py: el id de cliente de la app = slug(nombre del panel).
- norm()/tokens() para emparejar nombres de distintas herramientas.
- sanear(): quita correos y teléfonos de cualquier texto.
- escanear(): puerta de secretos (R16). Si encuentra algo, el generador no escribe.
- escribir(): escritura a temporal + renombrado (nunca deja un JSON a medias).
- bloque(): forma única de cada fuente dentro del fichero de un cliente.
"""
import json
import os
import re
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path

HOME = Path.home()
AQUI = Path(__file__).resolve().parent            # 30_APP_PROTOTIPO/fuentes
APP = AQUI.parent                                  # 30_APP_PROTOTIPO
RAIZ = APP.parent                                  # APP_RO_ROLES_Y_PERMISOS_2026-10-02
import sys as _sys  # C5: rutas en config.py
_sys.path.insert(1, str(APP))
import config  # noqa: E402
PANEL = config.PANEL_OPERACIONES
BUILD = PANEL / "build"
HERRAMIENTA = config.HERRAMIENTA_RO
CAPTACION = RAIZ / "20_FASE2_CAPTACION/captacion.json"
FASE0 = RAIZ / "20_FASE0_DATOS"
LIBRO = config.LIBRO_CLIENTES
HERR = config.HERRAMIENTAS
MUESTRAS = AQUI / "_muestras"
SALIDA = APP / "data"
SALIDA_CLIENTES = SALIDA / "clientes"

AHORA = datetime.now()

ESTADOS = ("bien", "a_cero", "rota", "dato_viejo", "sin_conectar", "no_aplica")


# ------------------------------------------------------------------ nombres
def slug(texto):
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


PALABRAS_VACIAS = {"asesores", "asesoria", "consulting", "consultores", "consultoria", "grup", "grupo",
                   "gestoria", "gestion", "economistes", "economistas", "abogados", "advisory", "assessors",
                   "the", "and", "y", "de", "del", "la", "sl", "slp", "sa", "s", "l", "com", "es", "www",
                   "ae", "and", "co", "ro", "cuenta", "publicitaria"}


def norm(s):
    t = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def tokens(s):
    return {w for w in norm(s).split() if len(w) >= 3 and w not in PALABRAS_VACIAS}


def dominio(url):
    d = re.sub(r"^(sc-domain:|https?://)?(www\.)?", "", str(url or "").strip().lower())
    return d.split("/")[0]


# ------------------------------------------------------------------ saneado
RE_CORREO = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
RE_TELEFONO = re.compile(r"(?<![\w*])(?:\+?34[\s.-]?)?[6789](?:[\s.-]?\d){8}(?!\d)")
RE_SECRETO = re.compile(
    r"(EAA[A-Za-z0-9]{30,}|pit-[0-9a-f-]{20,}|sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}"
    r"|pk_[0-9]{4,}_[A-Z0-9]{20,}|xox[bp]-[A-Za-z0-9-]{20,}|AIza[0-9A-Za-z_-]{30,}"
    r"|api_key=[A-Za-z0-9]{8,}|Bearer\s+[A-Za-z0-9._-]{20,})")
CLAVES_PROHIBIDAS = ("password", "contrasena", "contraseña", "passcode", "recording_play_passcode",
                     "share_url", "host_email", "telefono", "telefonos_conocidos", "numeros_usados",
                     "email", "correo", "phone", "token", "api_key", "sueldo", "salario")


def sanear(texto):
    if texto is None:
        return None
    t = RE_CORREO.sub("[correo]", str(texto))
    return RE_TELEFONO.sub("[teléfono]", t)


def escanear(obj, ruta="$"):
    """Devuelve la lista de hallazgos (vacía = limpio). Mira claves y valores."""
    hallazgos = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            kn = norm(k).replace(" ", "_")
            if kn in CLAVES_PROHIBIDAS:
                if v not in (None, "", [], {}):
                    hallazgos.append(f"{ruta}.{k}: clave sensible «{k}»")
            hallazgos += escanear(v, f"{ruta}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hallazgos += escanear(v, f"{ruta}[{i}]")
    elif isinstance(obj, str):
        if RE_CORREO.search(obj):
            hallazgos.append(f"{ruta}: correo en el texto")
        if RE_TELEFONO.search(obj):
            hallazgos.append(f"{ruta}: posible teléfono en el texto")
        if RE_SECRETO.search(obj):
            hallazgos.append(f"{ruta}: posible clave o token")
    return hallazgos


# ------------------------------------------------------------------ ficheros
def leer(ruta, defecto=None):
    try:
        return json.loads(Path(ruta).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return defecto


def mtime(ruta):
    try:
        return datetime.fromtimestamp(os.path.getmtime(ruta))
    except OSError:
        return None


def escribir(ruta, obj):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=ruta.parent, prefix=".tmp_", suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.chmod(tmp, 0o644)
    os.replace(tmp, ruta)


# ------------------------------------------------------------------ horas
FORMATOS = ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%d-%m-%Y %H:%M", "%Y-%m-%d")


def fecha(texto, anio=2026):
    """Interpreta las horas que escriben los generadores del panel («02-10 07:00» incluido)."""
    if not texto:
        return None
    t = str(texto).strip()[:19]
    for f in FORMATOS:
        try:
            return datetime.strptime(t, f)
        except ValueError:
            pass
    m = re.match(r"(\d{2})-(\d{2}) (\d{2}):(\d{2})$", t)
    if m:
        d, mo, h, mi = map(int, m.groups())
        return datetime(anio, mo, d, h, mi)
    return None


def edad_h(dt):
    return None if dt is None else round((AHORA - dt).total_seconds() / 3600, 1)


def iso(dt):
    return dt.strftime("%Y-%m-%d %H:%M") if dt else None


# ------------------------------------------------------------------ bloques
def bloque(fuente, estado, *, hora=None, medicion="hoy", nota=None, emparejado=None, datos=None, prueba=None,
           abrir=None, alertas=None):
    """Forma única de una fuente dentro de data/clientes/<id>.json (ver FORMATO.md)."""
    assert estado in ESTADOS, estado
    return {
        "fuente": fuente,
        "estado": estado,
        "hora": hora,
        "medicion": medicion,          # hoy | medias | no  (sello del catálogo)
        "nota": llano(nota),
        "emparejado": emparejado,      # {id, nombre, metodo} con el identificador de la cuenta
        "prueba": prueba,              # enlace al origen (clic a la prueba)
        "abrir": abrir,                # {texto, url} «Abrir en …»; url null = «Falta emparejar»
        "alertas": alertas or [],      # [{gravedad: rojo|ambar, texto, dueno}]
        "datos": datos,
    }


# ------------------------------------------------------------------ texto llano
RE_CODIGO = re.compile(r"\s*\(?\b(?:D|C|X|E|W|G|M|T|R|SP|A|B)-?\d{1,3}\b\)?")
RE_FICHERO = re.compile(r"\b[\w./-]+\.(?:json|py|md|js|html|zip)\b")


def llano(texto):
    """Quita códigos de obra (D-06, W2, E-10…) y nombres de fichero de los textos que puede ver alguien."""
    if not texto:
        return texto
    t = RE_FICHERO.sub("el fichero de origen", str(texto))
    t = RE_CODIGO.sub("", t)
    return re.sub(r"\s{2,}", " ", t).replace(" ;", ";").replace("()", "").strip()


# ------------------------------------------------------------------ enlaces «Abrir en …»
CLICKUP_EQUIPO = "90152357276"


def enlace(tipo, ident):
    """Un solo sitio construye los atajos (formatos comprobados en el documento de arquitectura, parte C.2).
    Sin identificador → {texto, url: None, falta: 'Falta emparejar'} para pintar el botón en gris."""
    import urllib.parse as up
    textos = {"meta": "Abrir en Meta", "ga4": "Abrir en Analytics", "gsc": "Abrir en Search Console",
              "ghl": "Abrir en GHL", "metricool": "Abrir en Metricool", "seranking": "Abrir en SE Ranking",
              "clickup_tarea": "Abrir en ClickUp", "clickup_carpeta": "Abrir en ClickUp", "clickup_chat": "Abrir en ClickUp",
              "desk": "Abrir en Desk", "zadarma": "Abrir en Zadarma", "zoom": "Abrir en Zoom",
              "google_ads": "Abrir en Google Ads", "holded": "Abrir en Holded"}
    texto = textos.get(tipo, "Abrir")
    if not ident and tipo not in ("zadarma", "zoom", "holded", "google_ads"):
        return {"texto": texto, "url": None, "falta": "Falta emparejar"}
    i = str(ident or "")
    url = {
        "meta": lambda: f"https://adsmanager.facebook.com/adsmanager/manage/campaigns?act={i.replace('act_', '')}",
        "ga4": lambda: f"https://analytics.google.com/analytics/web/#/p{i.replace('properties/', '')}/reports/intelligenthome",
        "gsc": lambda: "https://search.google.com/search-console?resource_id=" + up.quote(i, safe=""),
        "ghl": lambda: f"https://app.gohighlevel.com/v2/location/{i}/dashboard",
        "metricool": lambda: f"https://app.metricool.com/planner?blogId={i}",
        "seranking": lambda: f"https://online.seranking.com/admin.site.rankings.site_id-{i}.html",
        "clickup_tarea": lambda: f"https://app.clickup.com/t/{i}",
        "clickup_carpeta": lambda: f"https://app.clickup.com/{CLICKUP_EQUIPO}/v/o/f/{i}",
        "clickup_chat": lambda: f"https://app.clickup.com/{CLICKUP_EQUIPO}/chat/r/{i}",
        "desk": lambda: i if i.startswith("http") else None,
        "zadarma": lambda: "https://my.zadarma.com/mystatistics/",
        "zoom": lambda: "https://zoom.us/recording",
        "google_ads": lambda: "https://ads.google.com/aw/overview",   # sin formato comprobado por cuenta: abre Google Ads
        "holded": lambda: "https://app.holded.com/sales/revenue",
    }.get(tipo, lambda: None)()
    return {"texto": texto, "url": url} if url else {"texto": texto, "url": None, "falta": "Falta emparejar"}


def todo_cero(d):
    """True si todos los números de un diccionario (anidado) son 0 o None y hay al menos uno."""
    nums = []

    def rec(x):
        if isinstance(x, dict):
            for v in x.values():
                rec(v)
        elif isinstance(x, list):
            for v in x:
                rec(v)
        elif isinstance(x, (int, float)) and not isinstance(x, bool):
            nums.append(x)
    rec(d)
    return bool(nums) and all(n == 0 for n in nums)


# N14 (2-oct-2026): consultas de Search Console que no son búsquedas reales. En Octoedro entran filas enteras de una
# exportación de Google Ads / Planificador pegadas en Google («1, alta de cursos fundae como solicitar ,0, €0,00 ,1,4»):
# número de fila, palabra, clics, coste en euros y posición separados por comas. No se enseñan como consultas.
RE_CONSULTA_EXPORTACION = re.compile(r"(€\s?\d)|(^\s*\d+\s*,\s*[^,]+,\s*\d+\s*,)|(\d+,\d{2}\s*,\s*\d+,\d+\s*$)")


def consulta_basura(q):
    """True si la «consulta» es una fila de una exportación (CSV de Google Ads), no una búsqueda de verdad."""
    return bool(RE_CONSULTA_EXPORTACION.search(str(q or "")))


def limpiar_consultas(filas):
    """Quita de una lista de consultas [consulta, clics, impresiones, posición] las filas de exportación."""
    return [f for f in (filas or []) if not (isinstance(f, (list, tuple)) and f and consulta_basura(f[0]))]
