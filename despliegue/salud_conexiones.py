#!/usr/bin/env python3
"""despliegue/salud_conexiones.py · salud de TODAS las conexiones de la app de RO (carril N11, 2-oct-2026).

Tomás: «sin fallos de conexión por API». Este fichero es lo PRIMERO que corre en cada vuelta de la tubería
(paso «salud_conexiones» de pasos.json) y deja data/conexiones/salud.json, que enseña Ajustes › Conexiones.

Por cada conexión (26: ClickUp, Zoho Desk/CRM/Sign/Bookings/Calendar/Sheet, Zadarma, Meta, Google GA4/Search
Console/Ads, Metricool, SE Ranking, GHL agencia (app que rota y token privado), subcuenta de RO y escritura,
Holded, Airtable, Snov, Zoom, Windsor, Modular, Anthropic, Cloudflare):
  · prueba de humo SOLO LECTURA: UNA llamada barata (nada que gaste créditos ni escriba). La app de GHL que rota NO
    se llama (cada uso cambia la llave): se mira su última rotación y la última lectura buena de la tubería;
  · tiempo de respuesta, caducidad si se sabe (Meta con debug_token, Cloudflare con tokens/verify, tokens de acceso
    de 1 h desde la caché compartida), último OK, desde cuándo está en su color y los últimos resultados;
  · error en llano y QUÉ HACER con su dueño: lo que es de llave (caducada, revocada, sin permiso, falta) → quien
    tiene la cuenta, casi siempre Tomás, con el paso exacto («pega la clave con … pegar.sh»); lo técnico (5xx,
    tiempo agotado, red, demasiadas consultas) → Agus (técnico), que vigila y escala;
  · colores: verde (responde bien y rápido) · ámbar (lenta, caduca en ≤ 21 días, falta la llave de algo que la app
    aún no usa, o cae algo que hoy no se usa) · rojo (no responde o caduca en ≤ 7 días, y la app la usa).
Además:
  · RENUEVA antes de que caduquen los tokens de acceso de 1 h (Zoho, Google, Zoom, Snov) con la caché compartida de
    ~/RO_HERRAMIENTAS/cache_tokens.py: si a uno le quedan < 20 min, se pide ya, así ningún paso de la vuelta se lo
    encuentra caducado. La llave de GHL ya rota sola en cada uso (dueño único: la tubería).
  · ALERTA si una conexión de la que depende la app se cae: aviso de E0 (despliegue/avisos_tuberia.py: ≤ 3 al día, sin
    repetir) y una lista «alertas» en el formato de N4 (departamento, dueño, motivo, desde, plazo, escalado
    dueño → jefe → Tomás), para que el motor de alertas la reparta sin recalcular.
Nunca imprime ni guarda una llave: del llavero o del entorno solo sale el valor para la llamada; los errores se
sanean (ni llaves, ni correos, ni teléfonos) y la salida pasa la puerta de secretos.

Uso:
  python3 despliegue/salud_conexiones.py                 todas, en vivo (≈ 26 lecturas, 10-30 s)
  python3 despliegue/salud_conexiones.py --solo meta,zoho_desk   solo esas (el resto se conserva del último)
  python3 despliegue/salud_conexiones.py --sin-red       sin llamadas: llaves presentes y lo último probado
  Otras: --sin-avisos (no apunta avisos de E0) · --salida <fichero> (pruebas) · --json (imprime el resumen)
Código de salida: 0 siempre que haya podido escribir el fichero (una conexión caída NO tumba la tubería).
"""
import concurrent.futures as cf
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
sys.path.insert(0, str(AQUI))
sys.path.insert(1, str(APP))
import config  # noqa: E402

HERR = config.HERRAMIENTAS
if str(HERR) not in sys.path:
    sys.path.append(str(HERR))
ARGS = sys.argv[1:]
SIN_RED = "--sin-red" in ARGS
SIN_AVISOS = "--sin-avisos" in ARGS
SOLO = {x.strip() for x in (ARGS[ARGS.index("--solo") + 1] if "--solo" in ARGS else "").split(",") if x.strip()}
SALIDA = Path(ARGS[ARGS.index("--salida") + 1]) if "--salida" in ARGS else config.DATOS / "conexiones" / "salud.json"
AHORA = datetime.now()
FMT = "%Y-%m-%d %H:%M"
TIEMPO_S = 15          # tiempo máximo de cada prueba
LENTA_MS = 5000        # más de esto = ámbar «lenta»
MARGEN_RENOVAR_S = 1200
HISTORIAL = 12

PERSONAS = {"tomas": "Tomás", "agustina": "Agus", "mili": "Mili", "sofia": "Sofía", "yessica": "Yessica", "constanza": "Constanza"}
JEFE = {"agustina": "mili", "mili": "tomas", "tomas": "tomas", "sofia": "tomas", "yessica": "mili", "constanza": "mili"}

RX_SECRETO = re.compile(r"(?i)(token|key|secret|password|access_token|input_token|api_key)=[^&\s]+")
RX_LARGO = re.compile(r"[A-Za-z0-9_\-.]{32,}")
RX_CORREO = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
RX_TEL = re.compile(r"\+?\d[\d\s.-]{8,}\d")


def sanear(t):
    t = RX_SECRETO.sub(r"\1=[oculto]", str(t or ""))
    t = RX_LARGO.sub("[…]", t)
    t = RX_CORREO.sub("[correo]", t)
    return RX_TEL.sub("[número]", t)[:220]


# ------------------------------------------------------------------ red (solo lectura, con red_segura si está)
try:
    from red_segura import abrir as _abrir_seguro
except Exception:  # sin el módulo, una sola llamada como antes
    _abrir_seguro = None


def pedir(url, cabeceras=None, datos=None, metodo=None, lectura=None):
    """(json, cabeceras, ms). Errores HTTP como urllib.error.HTTPError (con .code). Nunca escribe nada fuera."""
    req = urllib.request.Request(url, data=datos, headers={"User-Agent": "ro-salud/1.0", **(cabeceras or {})}, method=metodo)
    t0 = time.time()
    if _abrir_seguro:
        r = _abrir_seguro(req, timeout=TIEMPO_S, lectura=lectura, intentos=2, tope_s=25)
    else:
        r = urllib.request.urlopen(req, timeout=TIEMPO_S)
    cuerpo = r.read()
    ms = int((time.time() - t0) * 1000)
    try:
        doc = json.loads(cuerpo.decode() or "null")
    except ValueError:
        doc = None
    return doc, dict(r.headers), ms


def secreto(nombre):
    return config.secreto(nombre)


def env_ghl():
    """ghl.env de la subcuenta de RO (GHL_PIT_NEW, GHL_PIT_WRITE, GHL_LOCATION_ID). Solo para la llamada."""
    out = {}
    f = config.BANDEJA_GHL_CONFIG / "ghl.env"
    if f.exists():
        for linea in f.read_text(encoding="utf-8").splitlines():
            if "=" in linea and not linea.lstrip().startswith("#"):
                k, v = linea.split("=", 1)
                out[k.strip()] = v.strip()
    for k in ("GHL_PIT_NEW", "GHL_PIT_WRITE", "GHL_LOCATION_ID"):
        if os.environ.get(k):
            out[k] = os.environ[k]
    return out


def _lector(carpeta, modulo):
    d = str(HERR / carpeta)
    if d not in sys.path:
        sys.path.insert(0, d)
    return __import__(modulo)


# ------------------------------------------------------------------ tokens de acceso de 1 h: renovar ANTES de caducar
RENUEVA = {   # servicio de la caché: (carpeta, módulo, función sin caché, llave que identifica la entrada, llaves necesarias)
    "zoho": ("zoho", "zh", "_acceso_sin_cache", "zoho_refresh_token", ["zoho_client_id", "zoho_client_secret", "zoho_refresh_token"]),
    "google": ("google", "gg", "_acceso_sin_cache", "google_refresh_token", ["google_client_id", "google_client_secret", "google_refresh_token"]),
    "zoom": ("zoom", "zm", "_token_sin_cache", "zoom_client_id", ["zoom_account_id", "zoom_client_id", "zoom_client_secret"]),
    "snov": ("snov", "sv", "_token_sin_cache", "snov_client_id", ["snov_client_id", "snov_client_secret"]),
}
ACCESO = {}      # servicio → token de acceso (solo en memoria, nunca se guarda en salud.json)
RENOVACION = {}  # servicio → {"estado", "quedan_min", "detalle"} (sin el token)


def renovar_tokens():
    try:
        import cache_tokens as CT
    except Exception:
        CT = None
    for srv, (carpeta, modulo, fn, id_llave, llaves) in RENUEVA.items():
        if any(not secreto(x) for x in llaves):
            RENOVACION[srv] = {"estado": "sin_llave", "detalle": "falta la llave: no hay token que renovar"}
            continue
        try:
            m = _lector(carpeta, modulo)
            refrescar = getattr(m, fn)
            if CT:
                antes = CT.vida_restante(srv, secreto(id_llave)) if hasattr(CT, "vida_restante") else None
                kw = {"margen_s": MARGEN_RENOVAR_S} if "margen_s" in CT.token.__code__.co_varnames else {}
                tk, extra = CT.token(srv, secreto(id_llave), refrescar, **kw)
                despues = CT.vida_restante(srv, secreto(id_llave)) if hasattr(CT, "vida_restante") else None
                renovado = antes is None or antes < MARGEN_RENOVAR_S
                RENOVACION[srv] = {"estado": "renovado" if renovado else "vigente",
                                   "quedan_min": int(despues // 60) if despues else None,
                                   "detalle": ("renovado ahora (le quedaban menos de 20 min)" if renovado and antes is not None
                                               else "pedido ahora (no había ninguno en la caché)" if renovado
                                               else f"vigente, le quedan {int(antes // 60)} min")}
            else:
                tk, _vida, extra = refrescar()
                RENOVACION[srv] = {"estado": "renovado", "quedan_min": None, "detalle": "pedido sin caché (falta cache_tokens.py)"}
            ACCESO[srv] = (tk, extra)
        except SystemExit as e:
            RENOVACION[srv] = {"estado": "error", "detalle": sanear(e)}
        except Exception as e:  # noqa: BLE001
            RENOVACION[srv] = {"estado": "error", "detalle": sanear(f"{type(e).__name__}: {getattr(e, 'code', '')} {e}")}


def acceso(srv):
    if srv not in ACCESO:
        raise RuntimeError(f"No hay token de acceso de {srv}: {RENOVACION.get(srv, {}).get('detalle', 'sin renovar')}")
    return ACCESO[srv]


# ------------------------------------------------------------------ pruebas de humo (UNA lectura barata cada una)
def p_clickup():
    _, h, ms = pedir("https://api.clickup.com/api/v2/user", {"Authorization": secreto("clickup_api_token")})
    hl = {k.lower(): v for k, v in h.items()}
    q = hl.get("x-ratelimit-remaining")
    return {"ms": ms, "detalle": "responde con la llave propia" + (f" · cupo: quedan {q} de {hl.get('x-ratelimit-limit')} este minuto" if q else "")}


def _zoho_h(org=None):
    tk, _ = acceso("zoho")
    h = {"Authorization": "Zoho-oauthtoken " + tk}
    if org:
        h["orgId"] = str(org)
    return h


def p_zoho_desk():
    d, _, ms = pedir("https://desk.zoho.eu/api/v1/organizations", _zoho_h())
    return {"ms": ms, "detalle": f"responde · {len((d or {}).get('data', []))} organización(es) de Desk"}


def p_zoho_crm():
    _, api = acceso("zoho")
    d, _, ms = pedir((api or "https://www.zohoapis.eu") + "/crm/v6/users?type=CurrentUser", _zoho_h())
    return {"ms": ms, "detalle": "responde · usuario de la llave leído" if (d or {}).get("users") else "responde"}


def p_zoho_sign():
    q = urllib.parse.quote(json.dumps({"page_context": {"row_count": 1, "start_index": 1}}))
    _, _, ms = pedir("https://sign.zoho.eu/api/v1/requests?data=" + q, _zoho_h())
    return {"ms": ms, "detalle": "responde · se leen los contratos firmados"}


def p_zoho_bookings():
    _, _, ms = pedir("https://www.zohoapis.eu/bookings/v1/json/workspaces", _zoho_h())
    return {"ms": ms, "detalle": "responde · espacios de Bookings visibles"}


def p_zoho_calendar():
    d, _, ms = pedir("https://calendar.zoho.eu/api/v1/calendars", _zoho_h())
    return {"ms": ms, "detalle": f"responde · {len((d or {}).get('calendars', []))} calendario(s) de la cuenta de la llave"}


LIBRO_INFORMES = "h4owxade0a8fd840349be9d38b45d75ec0313"   # «CARTERA CLIENTES RO» (fuentes_informes/importar_hoja_w5.py)


def p_zoho_sheet():
    datos = urllib.parse.urlencode({"method": "worksheet.list"}).encode()
    d, _, ms = pedir(f"https://sheet.zoho.eu/api/v2/{LIBRO_INFORMES}", _zoho_h(), datos=datos, metodo="POST", lectura=True)
    n = len((d or {}).get("worksheet_names", []))
    if not n:
        raise urllib.error.HTTPError("sheet", 403, "sin hojas visibles", {}, None)
    return {"ms": ms, "detalle": f"responde · el libro de informes tiene {n} hojas visibles (solo se lee «Informes mensuales»)"}


def p_zadarma():
    zd = _lector("zadarma", "zd")
    t0 = time.time()
    r = zd.get("/v1/info/balance/")
    out = {"ms": int((time.time() - t0) * 1000), "detalle": "responde · cuenta de la centralita leída (consulta de saldo, fuera del cupo de 3 por minuto)"}
    try:
        if float(r.get("balance")) < 10:   # sin saldo, las llamadas fallan: aviso sin enseñar el importe
            out["aviso"] = "saldo bajo en la centralita: si se acaba, no salen llamadas. Tomás: recarga en my.zadarma.com"
    except (TypeError, ValueError):
        pass
    return out


def p_meta():
    tk = secreto("meta_token")
    d, _, ms = pedir("https://graph.facebook.com/v26.0/debug_token?" + urllib.parse.urlencode({"input_token": tk, "access_token": tk}))
    x = (d or {}).get("data") or {}
    if not x.get("is_valid"):
        raise urllib.error.HTTPError("meta", 401, "llave no válida", {}, None)
    out = {"ms": ms, "detalle": f"responde · llave válida con {len(x.get('scopes') or [])} permisos"}
    exp = x.get("expires_at") or 0
    if exp:
        out["caduca"] = datetime.fromtimestamp(exp).strftime("%Y-%m-%d")
    elif exp == 0 and "expires_at" in x:
        out["caducidad_texto"] = "no caduca (usuario del sistema)"
    return out


def _google_h():
    return {"Authorization": "Bearer " + acceso("google")[0]}


def p_ga4():
    d, _, ms = pedir("https://analyticsadmin.googleapis.com/v1beta/accountSummaries?pageSize=1", _google_h())
    return {"ms": ms, "detalle": "responde · cuentas de Analytics visibles con la cuenta gmb1 de RO"}


def p_gsc():
    d, _, ms = pedir("https://www.googleapis.com/webmasters/v3/sites", _google_h())
    return {"ms": ms, "detalle": f"responde · {len((d or {}).get('siteEntry', []))} sitios de Search Console"}


def p_metricool():
    q = urllib.parse.urlencode({"userId": secreto("metricool_user_id")})
    d, _, ms = pedir("https://app.metricool.com/api/admin/simpleProfiles?" + q, {"X-Mc-Auth": secreto("metricool_token"), "Accept": "application/json"})
    n = len(d if isinstance(d, list) else (d or {}).get("data", []))
    return {"ms": ms, "detalle": f"responde · {n} marcas"}


def p_seranking():
    d, _, ms = pedir("https://api4.seranking.com/sites", {"Authorization": "Token " + secreto("seranking_project_key")})
    return {"ms": ms, "detalle": f"responde · {len(d or [])} proyectos (lectura de la lista, sin gastar créditos)"}


GHL = "https://services.leadconnectorhq.com"


def _ghl_h(tk):
    return {"Authorization": "Bearer " + tk, "Version": "2021-07-28", "Accept": "application/json"}


def p_ghl_pit():
    d, _, ms = pedir(GHL + "/locations/search?limit=1", _ghl_h(secreto("ghl_agency_pit")))
    return {"ms": ms, "detalle": "responde · lista de subcuentas legible con el token privado de agencia"}


def p_ghl_ro():
    e = env_ghl()
    _, _, ms = pedir(f"{GHL}/locations/{e['GHL_LOCATION_ID']}", _ghl_h(e["GHL_PIT_NEW"]))
    return {"ms": ms, "detalle": "responde · subcuenta de Ranking Online legible (setters, ventas y agenda)"}


def p_ghl_escritura():
    e = env_ghl()
    _, _, ms = pedir(f"{GHL}/locations/{e['GHL_LOCATION_ID']}", _ghl_h(e["GHL_PIT_WRITE"]))
    misma = e.get("GHL_PIT_WRITE") == e.get("GHL_PIT_NEW")
    return {"ms": ms, "detalle": "responde a una lectura" + (" (hoy es la misma llave que la de la subcuenta: pegar_token.sh guarda las tres)" if misma else "")
            + " · sus permisos de escritura no se prueban: la app no escribe en GHL"}


def p_ghl_app():
    """La app que ROTA no se llama: cada uso cambia la llave. Se mira su última rotación y la última lectura buena."""
    est = HERR / "ghl_agencia" / "app_estado.json"
    rot = datetime.fromtimestamp(est.stat().st_mtime) if est.exists() else None
    f = fuente("ghl") or {}
    hora = f.get("hora")
    ult = datetime.strptime(hora, FMT) if hora else None
    ref = max([x for x in (rot, ult) if x], default=None)
    if f.get("estado") in ("rota", "a_cero"):
        raise RuntimeError(f"la última lectura de GHL de la tubería salió «{f.get('estado')}»: {f.get('error') or 'sin detalle'}")
    out = {"ms": None, "sin_llamada": True,
           "detalle": f"no se llama aquí (cada uso cambia la llave) · última rotación {rot.strftime(FMT) if rot else '—'} · último dato bueno {hora or '—'}",
           "caducidad_texto": "token de acceso de 24 h; la llave vale 1 año o hasta su próximo uso (rota sola)"}
    if not ref or ref < AHORA - timedelta(hours=26):
        out["aviso"] = f"sin uso desde {ref.strftime(FMT) if ref else 'nunca'}: la próxima vuelta completa la usa y lo confirma"
    return out


def p_holded():
    hoy = int(datetime.combine(date.today(), datetime.min.time()).timestamp())
    d, _, ms = pedir(f"https://api.holded.com/api/invoicing/v1/documents/purchase?starttmp={hoy}&endtmp={hoy + 86399}",
                     {"key": secreto("holded_api_key"), "accept": "application/json"})
    return {"ms": ms, "detalle": "responde · compras de hoy legibles (los sueldos nunca entran)"}


def p_airtable():
    _, _, ms = pedir("https://api.airtable.com/v0/meta/whoami", {"Authorization": "Bearer " + secreto("airtable_token")})
    return {"ms": ms, "detalle": "responde · llave de SOLO LECTURA de la base de facturación"}


def p_snov():
    d, _, ms = pedir("https://api.snov.io/v1/get-balance", {"Authorization": "Bearer " + acceso("snov")[0]})
    saldo = ((d or {}).get("data") or {}).get("balance")
    try:
        saldo = f"{int(float(saldo)):,}".replace(",", ".")
    except (TypeError, ValueError):
        pass
    return {"ms": ms, "detalle": f"responde · {saldo} créditos de búsqueda" if saldo is not None else "responde"}


def p_zoom():
    d, _, ms = pedir("https://api.zoom.us/v2/users?page_size=1", {"Authorization": "Bearer " + acceso("zoom")[0]})
    return {"ms": ms, "detalle": f"responde · {(d or {}).get('total_records', '?')} usuarios en la cuenta de RO"}


def p_windsor():
    d, _, ms = pedir("https://connectors.windsor.ai/list_connectors?" + urllib.parse.urlencode({"api_key": secreto("windsor_api_key")}))
    return {"ms": ms, "detalle": "responde (lista de conectores, sin gastar cupo de datos)"}


def p_modular():
    """La misma lectura barata que ~/RO_HERRAMIENTAS/modular/md.py probar: /sites/count («per_page» no existe: daba 422)."""
    d, _, ms = pedir("https://api.modulards.com/api/public/v1/sites/count",
                     {"Authorization": "Bearer " + secreto("modulards_api_key"), "Accept": "application/json", "User-Agent": "RO-modular/1.0"})
    n = ((d or {}).get("meta") or {}).get("count")
    return {"ms": ms, "detalle": f"responde · {n} webs legibles con la clave de solo lectura" if n is not None else "responde · webs legibles"}


def p_hostinger():
    """La misma lectura barata que ~/RO_HERRAMIENTAS/hostinger/hg.py: lista de VPS (GET; el token no es de solo lectura,
    pero la app solo hace GET)."""
    d, _, ms = pedir("https://developers.hostinger.com/api/vps/v1/virtual-machines",
                     {"Authorization": "Bearer " + secreto("hostinger_api_token"), "Accept": "application/json", "User-Agent": "RO-hostinger-lectura/1.0"})
    n = len(d) if isinstance(d, list) else None
    return {"ms": ms, "detalle": f"responde · {n} VPS legibles (la app solo lee)" if n is not None else "responde"}


def p_gbp():
    """Google Business Profile (ficha de Google): la misma lectura barata que ~/RO_HERRAMIENTAS/google/gbp.py comprobar
    (lista de cuentas, GET). Mientras Google no apruebe el proyecto (cuota 0) sale «Pendiente de aprobación de Google»."""
    gbp = _lector("google", "gbp")
    t0 = time.time()
    n = len(gbp.cuentas(gbp.acceso()))
    return {"ms": int((time.time() - t0) * 1000), "detalle": f"responde · {n} cuenta(s) de Business Profile (la app solo lee)"}


def p_anthropic():
    k = (os.environ.get("ANTHROPIC_API_KEY") or "").strip() or secreto("anthropic_api_key")
    base = (os.environ.get("ANTHROPIC_BASE_URL") or "https://api.anthropic.com").rstrip("/")
    _, _, ms = pedir(base + "/v1/models?limit=1", {"x-api-key": k, "anthropic-version": "2023-06-01"})
    return {"ms": ms, "detalle": "responde · lista de modelos (no gasta: no genera texto)"}


def p_cloudflare():
    """La llave es de CUENTA (empieza por «cfat_»): /user/tokens/verify responde 401 aunque valga. Se lee la cuenta y
    se verifica la llave en /accounts/<id>/tokens/verify (estado y caducidad). Dos lecturas, ninguna escritura."""
    h = {"Authorization": "Bearer " + secreto("cloudflare_api_token")}
    d, _, ms = pedir("https://api.cloudflare.com/client/v4/accounts?per_page=1", h)
    cuentas = (d or {}).get("result") or []
    if not cuentas:
        raise urllib.error.HTTPError("cloudflare", 403, "sin cuentas visibles", {}, None)
    v, _, ms2 = pedir(f"https://api.cloudflare.com/client/v4/accounts/{cuentas[0]['id']}/tokens/verify", h)
    r = (v or {}).get("result") or {}
    if r.get("status") != "active":
        raise urllib.error.HTTPError("cloudflare", 401, f"estado {r.get('status')}", {}, None)
    out = {"ms": ms + ms2, "detalle": "responde · llave de cuenta activa"}
    if r.get("expires_on"):
        out["caduca"] = r["expires_on"][:10]
    else:
        out["caducidad_texto"] = "no caduca (sin fecha de caducidad)"
    return out


def fuente(fid):
    try:
        f = json.loads((config.DATOS / "fuentes.json").read_text())
        return next((x for x in f["fuentes"] if x["id"] == fid), None)
    except Exception:
        return None


# ------------------------------------------------------------------ inventario
H = "bash ~/RO_HERRAMIENTAS"


def guardar_en_llavero(nombre):
    return f"guárdala en el llavero del Mac: security add-generic-password -U -a \"$USER\" -s {nombre} -w (te la pide sin enseñarla)"


CONEXIONES = [
    # id, nombre, grupo, icono, llaves, prueba, dueño de la llave, crítica (la app la usa hoy), qué da, módulos, renovar, pegar
    dict(id="clickup", nombre="ClickUp (llave propia)", grupo="Trabajo", icono="check", llaves=["clickup_api_token"], prueba=p_clickup,
         dueno="tomas", critica=True, que_da="horas, tareas, revisiones y chat", modulos="Horas, Producción, Ficha (chat), Clientes nuevos, Chat del equipo",
         renovar={"url": "https://app.clickup.com/settings/apps", "donde": "Ajustes › Apps › Llave de API personal"},
         pegar=guardar_en_llavero("clickup_api_token"), caducidad="no caduca (llave personal)", limite="100 consultas por minuto"),
    dict(id="zoho_desk", nombre="Zoho Desk", grupo="Zoho", icono="inbox", llaves=RENUEVA["zoho"][4], prueba=p_zoho_desk, servicio="zoho",
         dueno="tomas", critica=True, que_da="correos de clientes (todos los departamentos)", modulos="Bandeja, Ficha, Informes mensuales",
         renovar={"url": "https://api-console.zoho.eu/", "donde": "Self Client › Generate Code con todos los permisos"},
         pegar=f"{H}/zoho/pegar_codigo.sh (copia antes el código de 10 min)", caducidad="llave permanente · token de acceso de 1 h que se renueva solo",
         limite="cupo diario de Desk según plan"),
    dict(id="zoho_crm", nombre="Zoho CRM", grupo="Zoho", icono="base", llaves=RENUEVA["zoho"][4], prueba=p_zoho_crm, servicio="zoho",
         dueno="tomas", critica=True, que_da="eventos y cuentas del CRM", modulos="Agenda, Portal de clientes",
         renovar={"url": "https://api-console.zoho.eu/", "donde": "Self Client › Generate Code"}, pegar=f"{H}/zoho/pegar_codigo.sh",
         caducidad="llave permanente · token de acceso de 1 h que se renueva solo"),
    dict(id="zoho_sign", nombre="Zoho Sign", grupo="Zoho", icono="doc", llaves=RENUEVA["zoho"][4], prueba=p_zoho_sign, servicio="zoho",
         dueno="tomas", critica=True, que_da="contratos firmados (día 0 del alta)", modulos="Clientes nuevos",
         renovar={"url": "https://api-console.zoho.eu/", "donde": "Self Client › Generate Code"}, pegar=f"{H}/zoho/pegar_codigo.sh",
         caducidad="llave permanente · token de acceso de 1 h que se renueva solo"),
    dict(id="zoho_bookings", nombre="Zoho Bookings", grupo="Zoho", icono="cal", llaves=RENUEVA["zoho"][4], prueba=p_zoho_bookings, servicio="zoho",
         dueno="tomas", critica=False, que_da="citas de todo el personal", modulos="Agenda",
         renovar={"url": "https://api-console.zoho.eu/", "donde": "Self Client › Generate Code con zohobookings.data.READ y CREATE"},
         pegar=f"{H}/zoho/pegar_codigo.sh", caducidad="llave permanente · token de acceso de 1 h que se renueva solo", limite="250-3.000 consultas al día"),
    dict(id="zoho_calendar", nombre="Zoho Calendar", grupo="Zoho", icono="cal", llaves=RENUEVA["zoho"][4], prueba=p_zoho_calendar, servicio="zoho",
         dueno="tomas", critica=False, que_da="calendarios de la cuenta de la llave", modulos="Agenda",
         renovar={"url": "https://api-console.zoho.eu/", "donde": "Self Client › Generate Code con ZohoCalendar.calendar.READ y event.READ"},
         pegar=f"{H}/zoho/pegar_codigo.sh", caducidad="llave permanente · token de acceso de 1 h que se renueva solo"),
    dict(id="zoho_sheet", nombre="Zoho Sheet (hoja de informes)", grupo="Zoho", icono="doc", llaves=RENUEVA["zoho"][4], prueba=p_zoho_sheet, servicio="zoho",
         dueno="tomas", critica=True, que_da="la hoja «Informes mensuales» (solo esa)", modulos="Informes mensuales, Ficha",
         renovar={"url": "https://api-console.zoho.eu/", "donde": "Self Client › Generate Code con ZohoSheet.dataAPI.READ"},
         pegar=f"{H}/zoho/pegar_codigo.sh", caducidad="llave permanente · token de acceso de 1 h que se renueva solo"),
    dict(id="zadarma", nombre="Zadarma (centralita)", grupo="Teléfono", icono="phone", llaves=["ZADARMA_KEY", "ZADARMA_SECRET"], prueba=p_zadarma,
         dueno="tomas", critica=True, que_da="llamadas, grabaciones y transcripciones", modulos="Bandeja, Setters, Ficha",
         renovar={"url": "https://my.zadarma.com/api/", "donde": "Ajustes › API: llave y secreto"},
         pegar=f"{H}/zadarma/pegar_claves.sh", caducidad="no caduca", limite="estadísticas: 3 consultas por minuto"),
    dict(id="meta", nombre="Meta Ads", grupo="Publicidad", icono="megafono", llaves=["meta_token"], prueba=p_meta,
         dueno="tomas", critica=True, que_da="cuentas publicitarias, gasto, leads y anuncios", modulos="Captación, Ficha, Informe del cliente, Paneles",
         renovar={"url": "https://business.facebook.com/settings/system-users", "donde": "Usuarios del sistema › generar llave que no caduca (o Explorador de la API de la app «MCP Claude»)"},
         pegar=f"{H}/meta/pegar_llave.sh", caducidad="60 días (llave de usuario)", limite="límite por cuenta publicitaria (Meta pide esperar)"),
    dict(id="ga4", nombre="Google Analytics 4", grupo="Google", icono="grafico", llaves=RENUEVA["google"][4], prueba=p_ga4, servicio="google",
         dueno="tomas", critica=True, que_da="visitas y conversiones de las webs", modulos="Informe del cliente, SEO, Ficha, Paneles",
         renovar={"url": "https://console.cloud.google.com/apis/credentials", "donde": "volver a autorizar con la cuenta gmb1 de RO"},
         pegar="python3 ~/RO_HERRAMIENTAS/google/gg.py instalar (abre Google; elige la cuenta gmb1)",
         caducidad="llave permanente mientras no se revoque · token de acceso de 1 h que se renueva solo"),
    dict(id="gsc", nombre="Google Search Console", grupo="Google", icono="globe", llaves=RENUEVA["google"][4], prueba=p_gsc, servicio="google",
         dueno="tomas", critica=True, que_da="clics y posiciones en Google", modulos="SEO, Informe del cliente, Ficha",
         renovar={"url": "https://console.cloud.google.com/apis/credentials", "donde": "volver a autorizar con la cuenta gmb1 de RO"},
         pegar="python3 ~/RO_HERRAMIENTAS/google/gg.py instalar", caducidad="llave permanente mientras no se revoque · token de 1 h que se renueva solo"),
    dict(id="google_ads", nombre="Google Ads (directo)", grupo="Google", icono="target",
         llaves=["google_ads_developer_token", "google_ads_login_customer_id", "google_ads_refresh_token"], prueba=None,
         dueno="tomas", critica=False, que_da="gasto y conversiones de Google Ads", modulos="Captación, Informe del cliente (hoy, muestra de Windsor)",
         renovar={"url": "https://ads.google.com/aw/apicenter", "donde": "Centro de API de la cuenta de administrador: token de desarrollador"},
         pegar=f"{H}/google/pegar_ads.sh token, luego mcc y por último instalar", caducidad="—"),
    dict(id="metricool", nombre="Metricool", grupo="Redes", icono="heart", llaves=["metricool_token", "metricool_user_id"], prueba=p_metricool,
         dueno="tomas", critica=True, que_da="marcas, seguidores y publicaciones", modulos="Redes, Informe del cliente",
         renovar={"url": "https://app.metricool.com/", "donde": "Ajustes de la cuenta › API (plan Advanced)"},
         pegar=f"{H}/metricool/pegar.sh", caducidad="no caduca"),
    dict(id="seranking", nombre="SE Ranking (proyectos)", grupo="SEO", icono="globe", llaves=["seranking_project_key"], prueba=p_seranking,
         dueno="tomas", critica=False, que_da="posiciones de los proyectos SEO", modulos="SEO, Informe del cliente",
         renovar={"url": "https://online.seranking.com/admin.api.dashboard.html", "donde": "Ajustes › API › llave de la API de PROYECTOS (no la de datos)"},
         pegar=f"{H}/seranking/pegar.sh", caducidad="no caduca", limite="los datos gastan créditos: la prueba solo lista proyectos"),
    dict(id="ghl_agencia_app", nombre="GoHighLevel · agencia (app que rota)", grupo="GoHighLevel", icono="base",
         llaves=["ghl_app_client_id", "ghl_app_client_secret", "ghl_app_refresh_token"], prueba=p_ghl_app,
         dueno="tomas", critica=True, que_da="contactos, oportunidades y citas de las 66 subcuentas", modulos="Salud del CRM, Captación, Ficha, Paneles",
         renovar={"url": "https://marketplace.gohighlevel.com/", "donde": "Mis apps › «Panel RO lectura subcuentas» › volver a instalar (solo si deja de rotar)"},
         pegar="python3 ~/RO_HERRAMIENTAS/ghl_agencia/app.py instalar (y autorizar en GHL)", caducidad="rota sola en cada uso", limite="100 consultas por 10 s por subcuenta"),
    dict(id="ghl_agencia_pit", nombre="GoHighLevel · agencia (token privado)", grupo="GoHighLevel", icono="base", llaves=["ghl_agency_pit"], prueba=p_ghl_pit,
         dueno="tomas", critica=False, que_da="lista de subcuentas (ga.py)", modulos="comprobaciones sueltas",
         renovar={"url": "https://app.gohighlevel.com/settings/private-integrations", "donde": "Agencia › Ajustes › Integraciones privadas"},
         pegar=guardar_en_llavero("ghl_agency_pit"), caducidad="la pone quien la crea en GHL"),
    dict(id="ghl_ro", nombre="GoHighLevel · subcuenta de RO", grupo="GoHighLevel", icono="base", llaves=["GHL_PIT_NEW"], prueba=p_ghl_ro, env_ghl=True,
         dueno="tomas", critica=True, que_da="leads, citas y conversaciones de Ranking Online", modulos="Setters, Ventas de RO, Agenda",
         renovar={"url": "https://app.gohighlevel.com/", "donde": "Subcuenta de RO › Ajustes › Integraciones privadas"},
         pegar=f"{H}/ghl/pegar_token.sh", caducidad="la pone quien la crea en GHL"),
    dict(id="ghl_escritura", nombre="GoHighLevel · escritura (RO)", grupo="GoHighLevel", icono="editar", llaves=["GHL_PIT_WRITE"], prueba=p_ghl_escritura, env_ghl=True,
         dueno="tomas", critica=False, que_da="escribir en GHL (la app hoy NO escribe: cola simulada)", modulos="Setters (cuando haya escritura)",
         renovar={"url": "https://app.gohighlevel.com/", "donde": "Subcuenta de RO › Ajustes › Integraciones privadas › llave con permisos de escritura"},
         pegar=f"{H}/ghl/pegar_token.sh", caducidad="la pone quien la crea en GHL"),
    dict(id="holded", nombre="Holded", grupo="Dinero", icono="euro", llaves=["holded_api_key"], prueba=p_holded,
         dueno="sofia", critica=True, que_da="compras, suscripciones y facturas (sueldos nunca)", modulos="Finanzas, Dinero por cliente",
         renovar={"url": "https://app.holded.com/", "donde": "Configuración › Desarrolladores › Llaves de API"},
         pegar=guardar_en_llavero("holded_api_key"), caducidad="no caduca"),
    dict(id="airtable", nombre="Airtable de facturación (solo lectura)", grupo="Dinero", icono="doc", llaves=["airtable_token"], prueba=p_airtable,
         dueno="sofia", critica=True, que_da="base de facturación (cuotas)", modulos="Finanzas, Dinero por cliente",
         renovar={"url": "https://airtable.com/create/tokens", "donde": "Llaves personales › solo lectura de la base de facturación"},
         pegar=guardar_en_llavero("airtable_token"), caducidad="la que se le ponga al crearla"),
    dict(id="snov", nombre="Snov.io (correo en frío)", grupo="Ventas", icono="send", llaves=RENUEVA["snov"][4], prueba=p_snov, servicio="snov",
         dueno="yessica", critica=True, que_da="campañas de correo y sus estadísticas", modulos="Prospección, Ventas de RO, Informe del cliente",
         renovar={"url": "https://app.snov.io/account/api", "donde": "Cuenta › API: identificador y secreto"},
         pegar=f"{H}/snov/pegar.sh", caducidad="no caduca · token de acceso de 1 h que se renueva solo"),
    dict(id="zoom", nombre="Zoom (toda la cuenta)", grupo="Reuniones", icono="video", llaves=RENUEVA["zoom"][4], prueba=p_zoom, servicio="zoom",
         dueno="tomas", critica=True, que_da="grabaciones y transcripciones", modulos="Reuniones",
         renovar={"url": "https://marketplace.zoom.us/user/build", "donde": "Gestionar › app de servidor a servidor › Credenciales"},
         pegar=guardar_en_llavero("zoom_client_secret") + " (y zoom_account_id / zoom_client_id si cambian)",
         caducidad="no caduca · token de acceso de 1 h que se renueva solo"),
    dict(id="windsor", nombre="Windsor (Google Ads y TikTok)", grupo="Publicidad", icono="plug", llaves=["windsor_api_key"], prueba=p_windsor,
         dueno="tomas", critica=False, que_da="Google Ads y TikTok mientras no haya conexión directa", modulos="Captación, Informe del cliente (hoy, muestra manual)",
         renovar={"url": "https://onboard.windsor.ai/", "donde": "Cuenta › API key"}, pegar=f"{H}/windsor/pegar.sh",
         caducidad="no caduca", limite="gasta cupo: solo en la vuelta completa"),
    dict(id="modular", nombre="Modular DS (webs)", grupo="Webs", icono="mundo_web", llaves=["modulards_api_key"], prueba=p_modular,
         dueno="tomas", critica=False, que_da="caídas, copias, certificados y actualizaciones de las webs", modulos="Webs (N5), Alertas",
         renovar={"url": "https://app.modulards.com/", "donde": "Ajustes › API"}, pegar=f"{H}/modular/pegar.sh", caducidad="no caduca"),
    dict(id="hostinger", nombre="Hostinger (hosting, VPS y dominios)", grupo="Webs", icono="mundo_web", llaves=["hostinger_api_token"], prueba=p_hostinger,
         dueno="tomas", critica=False, que_da="estado de los VPS (también el del gestor de contraseñas), webs suspendidas, certificados, dominios y renovaciones",
         modulos="Webs, Alertas", renovar={"url": "https://hpanel.hostinger.com/profile/api", "donde": "Perfil › API › crear token (con caducidad)"},
         pegar=f"{H}/hostinger/pegar.sh", caducidad="la que se le ponga al crearla",
         limite="90 consultas por minuto; el token NO es de solo lectura (Hostinger no lo permite): la app solo hace GET"),
    dict(id="gbp", nombre="Google Business Profile (ficha de Google)", grupo="Google", icono="pin", llaves=["google_client_id", "google_client_secret", "google_gbp_refresh_token"],
         prueba=p_gbp, dueno="tomas", critica=False, que_da="reseñas, llamadas, rutas, clics y estado de la ficha de Google de cada cliente",
         modulos="SEO › Ficha de Google, Ficha del cliente, Alertas",
         renovar={"url": "https://support.google.com/business/contact/api_default", "donde": "Google: formulario «Application for Basic API Access» (aprobación previa; 60 días de ficha verificada y web)"},
         pegar="python3 ~/RO_HERRAMIENTAS/google/gbp.py instalar (cuando Google apruebe; elegir la cuenta que gestiona las fichas)",
         caducidad="llave permanente mientras no se revoque · token de acceso de 1 h que se renueva solo",
         limite="0 consultas hasta que Google apruebe; luego 300 por minuto. El permiso (business.manage) NO es de solo lectura: la app solo hace GET"),
    dict(id="anthropic", nombre="Anthropic (IA de la app)", grupo="IA", icono="spark", llaves=["anthropic_api_key"], prueba=p_anthropic, env_alt="ANTHROPIC_API_KEY",
         dueno="tomas", critica=False, que_da="borradores de Desk y copiloto del account", modulos="IA (N3)",
         renovar={"url": "https://console.anthropic.com/settings/keys", "donde": "Console › API keys"},
         pegar=guardar_en_llavero("anthropic_api_key"), caducidad="no caduca"),
    dict(id="cloudflare", nombre="Cloudflare (DNS y Access)", grupo="Servidor", icono="escudo", llaves=["cloudflare_api_token"], prueba=p_cloudflare,
         dueno="tomas", critica=False, que_da="DNS y puerta de acceso del servidor (cuando se suba)", modulos="Despliegue (C5)",
         renovar={"url": "https://dash.cloudflare.com/profile/api-tokens", "donde": "Mi perfil › Tokens de API"},
         pegar=f"{H}/despliegue/pegar_llave.sh cloudflare", caducidad="la que se le ponga al crearla"),
]
POR_ID = {c["id"]: c for c in CONEXIONES}
# Envíos verificados (3-oct): la conexión «Envío de correos» (llave de escritura de Desk, departamento, dirección de envío,
# firmas y cupo; SOLO lectura) vive en envios.py. Sin ese fichero, nada cambia.
try:
    if str(APP) not in sys.path:
        sys.path.insert(0, str(APP))
    import envios as _ENVIOS  # noqa: E402
    CONEXIONES.append(_ENVIOS.conexion_salud(pedir, secreto))
    POR_ID = {c["id"]: c for c in CONEXIONES}
except Exception as _e:  # noqa: BLE001 · la salud del resto no puede caer por esto
    print(f"(aviso) sin la conexión «Envío de correos»: {type(_e).__name__}")


# ------------------------------------------------------------------ errores en llano y qué hacer
def llave_presente(c, nombre):
    if c.get("env_ghl"):
        return bool(env_ghl().get(nombre))
    if c.get("env_alt") and os.environ.get(c["env_alt"]):
        return True
    return bool(secreto(nombre))


def traducir(e, c):
    """(tipo, texto en llano, a quién le toca: 'llave' o 'tecnico')."""
    if type(e).__name__ == "PendienteAprobacion":      # Google Business Profile: cuota 0 hasta que Google apruebe
        return "pendiente", "Pendiente de aprobación de Google: el proyecto tiene cuota 0 hasta que Google conteste el formulario de acceso.", "llave"
    code = getattr(e, "code", None)
    if isinstance(e, urllib.error.HTTPError) or isinstance(code, int):
        if code == 401:
            return "llave_mala", "No acepta la llave: está caducada, revocada o mal copiada.", "llave"
        if code == 403:
            return "sin_permiso", "La llave entra pero no tiene permiso para leer esto (le falta un permiso o el plan no lo incluye).", "llave"
        if code == 404:
            return "ruta", "La dirección de la API ya no existe o cambió de versión.", "tecnico"
        if code == 429:
            return "cupo", "Demasiadas consultas seguidas: la herramienta pide esperar (cupo agotado por ahora).", "tecnico"
        if code and code >= 500:
            return "caida_proveedor", f"La herramienta está fallando por su lado (error {code}). No es de RO.", "tecnico"
        if code == 400:
            return "rechazo", "La herramienta rechaza la consulta (400): suele ser la llave o un permiso.", "llave"
        return "error", f"La herramienta responde con el error {code}.", "tecnico"
    nombre = type(e).__name__
    if nombre in ("TimeoutError", "timeout") or "timed out" in str(e):
        return "tiempo", f"No ha contestado en {TIEMPO_S} s.", "tecnico"
    if isinstance(e, urllib.error.URLError):
        return "red", "No hay conexión con la herramienta (red, DNS o la herramienta no está).", "tecnico"
    if isinstance(e, SystemExit) or "rechaza" in str(e) or "invalid" in str(e).lower():
        return "llave_mala", sanear(e) or "El lector no pudo entrar con la llave.", "llave"
    return "error", sanear(f"{nombre}: {e}"), "tecnico"


def que_hacer(c, tipo, a_quien):
    dueno = c["dueno"]
    if tipo == "falta_clave":
        return dueno, f"{PERSONAS[dueno]}: crea la llave en {c['renovar']['donde']} (botón «Consola de la llave») y {c['pegar'] if c['pegar'].startswith('guárdala') else 'pégala con ' + c['pegar']}."
    if a_quien == "llave" or tipo in ("caduca_pronto", "caducada"):
        return dueno, f"{PERSONAS[dueno]}: renueva la llave en {c['renovar']['donde']} (botón «Consola de la llave») y {c['pegar'] if c['pegar'].startswith('guárdala') else 'pégala con ' + c['pegar']}. Luego «Probar ahora»."
    if tipo == "cupo":
        return "agustina", "Agus: no hace falta tocar nada; se reintenta solo con espera. Si sigue en rojo 3 vueltas seguidas, baja la frecuencia de ese paso en despliegue/pasos.json («cada_min»)."
    if tipo in ("caida_proveedor", "tiempo", "red"):
        return "agustina", ("Agus: es de la herramienta o de la red, no de la llave. La app sigue con el último dato bueno. "
                            "Mira su página de estado; si dura más de 2 h, abre incidencia con el proveedor y avisa a Mili.")
    if tipo == "lenta":
        return "agustina", "Agus: responde, pero lenta. Si sigue lenta 3 vueltas seguidas, sube su tiempo máximo en pasos.json o muévela a la vuelta completa."
    if tipo == "ruta":
        return "agustina", "Agus: hay que actualizar la versión de la API en su lector de ~/RO_HERRAMIENTAS (pídeselo a Claude con este aviso)."
    return "agustina", "Agus: mira el detalle y, si no está claro, pídeselo a Claude con este aviso."


# ------------------------------------------------------------------ evaluar una conexión
def evaluar(c):
    fila = {k: c.get(k) for k in ("id", "nombre", "grupo", "icono", "critica", "que_da", "modulos", "renovar", "limite")}
    fila.update({"llaves_total": len(c["llaves"]), "ultima_prueba": AHORA.strftime(FMT), "ms": None, "caduca": None,
                 "dias_para_caducar": None, "caducidad_texto": c.get("caducidad"), "error_llano": None})
    faltan = [n for n in c["llaves"] if not llave_presente(c, n)]
    fila["llaves_faltan"] = len(faltan)
    if faltan:
        quien, paso = que_hacer(c, "falta_clave", "llave")
        fila.update({"color": "rojo" if c["critica"] else "ambar", "estado": "falta_clave", "ok": False,
                     "titular": "Falta la llave",
                     "detalle": f"Falta la llave · lo hace {PERSONAS[quien]} (faltan {len(faltan)} de {len(c['llaves'])} en el llavero o el entorno)" + ("" if c["critica"] else " · hoy la app no la necesita"),
                     "que_hacer": paso, "quien_id": quien})
        return fila
    if SIN_RED or c["prueba"] is None:
        fila.update({"color": "gris", "estado": "sin_probar", "ok": None, "titular": "Sin probar (vuelta sin red)",
                     "detalle": "llaves presentes; la prueba en vivo corre en la próxima vuelta con red", "que_hacer": None, "quien_id": None})
        return fila
    try:
        r = c["prueba"]()
    except BaseException as e:  # noqa: BLE001 · un SystemExit de un lector también es un fallo de esta conexión
        if isinstance(e, KeyboardInterrupt):
            raise
        tipo, llano, a_quien = traducir(e, c)
        quien, paso = que_hacer(c, tipo, a_quien)
        color = "rojo" if c["critica"] else "ambar"
        fila.update({"color": color, "estado": tipo, "ok": False, "error_llano": llano,
                     "titular": {"sin_permiso": "Sin permiso", "cupo": "Cupo agotado", "rechazo": "Rechaza la consulta", "pendiente": "Pendiente de aprobación de Google"}.get(tipo, "No responde" if a_quien == "tecnico" else "La llave no vale")
                                + ("" if c["critica"] else " · hoy la app no la usa"),
                     "detalle": llano, "que_hacer": paso, "quien_id": quien})
        return fila
    fila.update({"ok": True, "ms": r.get("ms"), "detalle": r.get("detalle"), "color": "verde", "estado": "bien",
                 "titular": "Funciona", "que_hacer": None, "quien_id": None})
    if r.get("caducidad_texto"):
        fila["caducidad_texto"] = r["caducidad_texto"]
    cad = r.get("caduca")
    if not cad and c["id"] == "meta":
        try:
            cad = json.loads((HERR / "meta" / "estado.json").read_text()).get("caduca")
        except Exception:
            cad = None
    if cad:
        dias = (date.fromisoformat(cad) - date.today()).days
        fila.update({"caduca": cad, "dias_para_caducar": dias})
        if dias <= 21:
            quien, paso = que_hacer(c, "caduca_pronto", "llave")
            fila.update({"color": "rojo" if dias <= 7 else "ambar", "estado": "caduca_pronto",
                         "titular": f"Caduca en {dias} días", "que_hacer": paso, "quien_id": quien})
    if r.get("aviso") and c["id"] == "zadarma":
        fila.update({"color": "ambar", "estado": "saldo_bajo", "titular": "Saldo bajo", "detalle": f"{r['detalle']} · {r['aviso']}",
                     "que_hacer": "Tomás: recarga saldo en my.zadarma.com (Finanzas › Recargar).", "quien_id": "tomas"})
    elif r.get("aviso"):
        fila.update({"color": "ambar", "estado": "sin_uso_reciente", "titular": "Funciona, sin uso reciente", "detalle": f"{r['detalle']} · {r['aviso']}",
                     "que_hacer": "Agus: nada que hacer si la próxima vuelta completa sale bien; si sale «rota», Tomás vuelve a instalar la app.", "quien_id": "agustina"})
    elif fila["ms"] and fila["ms"] > LENTA_MS and fila["color"] == "verde":
        quien, paso = que_hacer(c, "lenta", "tecnico")
        fila.update({"color": "ambar", "estado": "lenta", "titular": f"Lenta ({fila['ms'] / 1000:.1f} s)", "que_hacer": paso, "quien_id": quien})
    return fila


# ------------------------------------------------------------------ historia, alertas y escritura
def leer_previo():
    try:
        return {c["id"]: c for c in json.loads(SALIDA.read_text()).get("conexiones", [])}
    except Exception:
        return {}


def con_historia(fila, previa):
    p = previa or {}
    fila["desde"] = p.get("desde") if p.get("color") == fila["color"] and p.get("desde") else fila["ultima_prueba"]
    if fila["ok"]:
        fila["ultimo_ok"] = fila["ultima_prueba"]
    else:
        fila["ultimo_ok"] = p.get("ultimo_ok")
    fila["fallos_seguidos"] = (p.get("fallos_seguidos", 0) + 1) if fila["ok"] is False else 0
    if fila["estado"] == "sin_probar" and p.get("color") not in (None, "gris"):   # sin red: se queda lo último probado
        for k in ("color", "estado", "titular", "detalle", "que_hacer", "quien_id", "ms", "error_llano", "caduca", "dias_para_caducar", "desde", "ultima_prueba"):
            fila[k] = p.get(k)
        fila["detalle"] = f"{p.get('detalle') or ''} (probado {p.get('ultima_prueba')}; esta vuelta va sin red)"
    hist = list(p.get("historial") or [])
    if fila["estado"] != "sin_probar":
        hist.append({"hora": fila["ultima_prueba"], "color": fila["color"], "ms": fila["ms"]})
    fila["historial"] = hist[-HISTORIAL:]
    fila["quien"] = PERSONAS.get(fila.get("quien_id")) if fila.get("quien_id") else None
    return fila


def alertas_n4(filas):
    """Formato de N4 (fuentes_alertas/generar_alertas.py): una alerta por conexión que la app usa y está en rojo, o
    que caduca en ≤ 21 días. Dueño: el de la llave (dirección) o Agus si es técnico; escalado dueño → jefe → Tomás."""
    out = []
    for f in filas:
        if not f.get("quien_id") or f["color"] not in ("rojo", "ambar"):
            continue
        if f["color"] == "ambar" and f["estado"] not in ("caduca_pronto",):
            continue
        d = f["quien_id"]
        cadena = [d] + [x for x in (JEFE.get(d), "tomas") if x and x != d]
        out.append({
            "id": f"conexion_caida:{f['id']}", "tipo": "conexion_caida", "departamento": "direccion" if d == "tomas" else "tecnico",
            "titulo": f"{f['nombre']}: {f['titular'].lower()}", "motivo": f.get("error_llano") or f.get("detalle"),
            "dueno_id": d, "jefe_id": JEFE.get(d, "tomas"), "escalado_cadena": cadena[:3], "desde": f["desde"],
            "plazo_h": 4 if f["color"] == "rojo" else 72, "gravedad": "alta" if f["color"] == "rojo" else "media",
            "que_hacer": f["que_hacer"], "ir": "#/ajustes/conexiones", "modulo_origen": "ajustes", "fuente": "Salud de conexiones (N11)",
            "comprueba": "La siguiente prueba de la conexión sale en verde."})
    return out


def avisar(filas, previas):
    """Aviso de E0 (≤ 3 al día, sin repetir) cuando una conexión que la app usa CAE (pasa a rojo) o sigue caída 3 vueltas."""
    if SIN_AVISOS or SIN_RED:
        return []
    try:
        import avisos_tuberia as AV
    except Exception:
        return []
    hechos = []
    for f in filas:
        if f["color"] != "rojo" or not f.get("critica"):
            continue
        antes = (previas.get(f["id"]) or {}).get("color")
        if antes == "rojo" and f.get("fallos_seguidos", 0) not in (1, 3):
            continue
        texto = f"{f['nombre']} · {f['titular']}: {f.get('error_llano') or f.get('detalle')} Qué hacer → {f['que_hacer']}"
        try:
            r = AV.avisar("conexion_caida", f["id"], RX_SECRETO.sub(r"\1=[oculto]", texto)[:400])
            hechos.append({"id": f["id"], "estado": r or "ya_avisado_hoy", "a": f.get("quien_id")})
        except Exception as e:  # un aviso que no sale no puede tumbar la tubería
            hechos.append({"id": f["id"], "estado": f"no_salio: {sanear(e)}"})
    return hechos


def escribir(doc):
    """Escritura atómica y SOLO si pasa la puerta de secretos de E0 (escaner_secretos.py)."""
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    tmp = SALIDA.with_name(f".{SALIDA.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    try:
        import escaner_secretos as ESC
        hall = ESC.escanear_fichero(tmp)
    except ImportError:
        hall = []
    if hall:
        tmp.unlink()
        raise SystemExit(f"Puerta de secretos: salud.json no se escribe ({[h.get('tipo') for h in hall[:3]]} en {[h.get('ruta') for h in hall[:3]]})")
    os.replace(tmp, SALIDA)


def main():
    t0 = time.time()
    previas = leer_previo()
    lista = [c for c in CONEXIONES if not SOLO or c["id"] in SOLO]
    if SOLO and not lista:
        sys.exit(f"Ninguna conexión con esos ids. Hay: {', '.join(POR_ID)}")
    if not SIN_RED:
        renovar_tokens()
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        filas = list(ex.map(evaluar, lista))
    filas = [con_historia(f, previas.get(f["id"])) for f in filas]
    if SOLO:   # el resto se conserva tal cual de la última vuelta
        nuevos = {f["id"] for f in filas}
        filas += [p for i, p in previas.items() if i not in nuevos and i in POR_ID]
    orden = {c["id"]: i for i, c in enumerate(CONEXIONES)}
    filas.sort(key=lambda f: ({"rojo": 0, "ambar": 1, "gris": 2, "verde": 3}.get(f["color"], 4), orden.get(f["id"], 99)))
    av = avisar(filas, previas)
    cuenta = {k: sum(1 for f in filas if f["color"] == k) for k in ("verde", "ambar", "rojo", "gris")}
    doc = {
        "generado": AHORA.strftime(FMT), "segundos": round(time.time() - t0, 1), "en_vivo": not SIN_RED,
        "solo": sorted(SOLO) or None, "resumen": {**cuenta, "total": len(filas)},
        "como": ("Una lectura barata por conexión (nada que escriba ni gaste créditos), con su tiempo. La app de GHL que rota no "
                 "se llama: se mira su última rotación. Los tokens de acceso de 1 h se renuevan aquí si les quedan menos de 20 min."),
        "renovacion_acceso": RENOVACION, "conexiones": filas, "alertas": alertas_n4(filas), "avisos_enviados": av,
        "probar_ahora": "python3 despliegue/salud_conexiones.py [--solo id1,id2]  · o «Probar ahora» en Ajustes › Conexiones (lanza una vuelta ligera)",
    }
    escribir(doc)
    print(f"Salud de conexiones · {doc['generado']} · {cuenta['verde']} verdes · {cuenta['ambar']} ámbar · {cuenta['rojo']} rojas"
          f"{' · ' + str(cuenta['gris']) + ' sin probar' if cuenta['gris'] else ''} · {doc['segundos']} s → {SALIDA}")
    for f in filas:
        if f["color"] != "verde":
            print(f"  {f['color']:<5} {f['id']:<17} {sanear(f.get('error_llano') or f.get('detalle'))[:110]}")
    if "--json" in ARGS:
        print(json.dumps(doc["resumen"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
