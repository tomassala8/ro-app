#!/usr/bin/env python3
"""config.py · ÚNICA fuente de rutas y de secretos de la app de RO (carril C5, 2-oct-2026).

Por qué existe: los generadores tenían rutas fijas a ~/Downloads/… y leían las llaves del llavero del Mac.
En un servidor (Render, Hetzner o Cloud Run) no hay ni Descargas ni llavero. Este fichero lo resuelve en un
solo sitio, SIN cambiar nada en el Mac: si no hay ninguna variable de entorno, todo apunta a lo de siempre.

RUTAS (todas se pueden mover con una variable de entorno; si no hay variable, la ruta del Mac de hoy):
  RO_HOME         la «casa» de la que cuelga todo (Mac: ~ · servidor: /srv/ro). Por defecto, Path.home().
  RO_CRUDOS       carpeta de los datos a mano que hoy viven en Descargas (por defecto RO_HOME/Downloads).
                  En el servidor se copia ahí la misma estructura de subcarpetas (ver despliegue/DESPLIEGUE.md).
  RO_HERRAMIENTAS los lectores de ~/RO_HERRAMIENTAS (por defecto RO_HOME/RO_HERRAMIENTAS).
  RO_DATOS        la salida de la app (por defecto <app>/data). Solo para la tubería; los generadores escriben
                  junto a sí mismos como hasta ahora.
  RO_ESTADO_DIR   estado de la tubería (registros, bloqueos, copias). Por defecto <app>/despliegue/estado.

SECRETOS · orden de búsqueda de secreto('meta_token'):
  1. Fichero <RO_SECRETOS_DIR>/meta_token  (carpeta privada 0700 que la tubería rellena al arrancar; en Render
     es efímera y solo vive durante la vuelta).
  2. Variable de entorno META_TOKEN (el nombre del llavero en mayúsculas). Así se cargan en Render/Cloud Run.
  3. Llavero del Mac (security find-generic-password -s meta_token -w), solo en macOS. Igual que hoy.
  ⚠️ La llave de GHL de agencia que ROTA (ghl_app_refresh_token) NUNCA va en una variable de entorno: su dueño
     único es la tubería y vive en la base de estado con bloqueo (despliegue/llave_ghl.py).

Uso:  python3 config.py            → rutas resueltas y qué secretos hay (sin enseñar ningún valor)
      python3 config.py --json     → lo mismo en JSON (para la pantalla de salud)
"""
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent                       # 30_APP_PROTOTIPO
PROYECTO = APP.parent                                        # APP_RO_ROLES_Y_PERMISOS_2026-10-02 (10_FICHAS, 20_FASE0_DATOS…)


def _ruta(var, defecto):
    v = os.environ.get(var)
    return Path(v).expanduser() if v else Path(defecto)


# ------------------------------------------------------------------ raíces
HOME = _ruta("RO_HOME", Path.home())
CRUDOS = _ruta("RO_CRUDOS", HOME / "Downloads")
HERRAMIENTAS = _ruta("RO_HERRAMIENTAS", HOME / "RO_HERRAMIENTAS")
DATOS = _ruta("RO_DATOS", APP / "data")
ESTADO_DIR = _ruta("RO_ESTADO_DIR", APP / "despliegue" / "estado")
BANDEJA_GHL_CONFIG = _ruta("RO_BANDEJA_GHL_CONFIG", HOME / "RO_BANDEJA_GHL" / "config")   # ghl.env, zadarma.env

# ------------------------------------------------------------------ datos a mano (riesgo R7: caducan en silencio)
# Cada una lleva su dueño y su edad máxima (horas) para que la pantalla de salud marque la edad.
PANEL_OPERACIONES = CRUDOS / "PANEL_OPERACIONES_2026-10-01"                 # panel v27 de Mili
PANEL_BUILD = PANEL_OPERACIONES / "build"
LIBRO_CLIENTES = CRUDOS / "BAJAS_LTV_CHURN_2026-10-01" / "clientes.json"    # libro de clientes (D-16)
HERRAMIENTA_RO = CRUDOS / "HERRAMIENTA_RO_2026-10-02"                       # externos.json, chat.json (ficha v3)
PLAN_FICHAJES = CRUDOS / "PLAN_FICHAJES_Q4_2026" / "plan_fichajes_q4.html"
PANEL_RESULTADOS = CRUDOS / "PANEL_RESULTADOS_RO_2026-09-18" / "ENTREGA"    # panel v29 (dataset_ro, financiero)
MILI_PANEL_V7 = CRUDOS / "MILI_PANEL_Y_FEEDBACK_2026-10-02" / "panel_v7"
SETTERS_REPARTO = CRUDOS / "SETTERS_RO_2026-09-24" / "25_GHL_PRUEBA_SETTERS"   # lector de GHL de la subcuenta de RO
MOVILES_CORREOS = CRUDOS / "MOVILES_Y_CORREOS_CLIENTES_RO_2026-10-02.md"
TORRE_ZIP = CRUDOS / "torre-de-control-paid.zip"
SALARIOS_XLSX = CRUDOS / "SALARIOS EQUIPO (4).xlsx"                         # sueldos (sensible: solo _privado/)

DATOS_A_MANO = {
    # id: (ruta, dueño, edad máxima en horas antes de marcarla vieja, qué la rellena)
    "panel_v27": (PANEL_OPERACIONES, "Mili / recarga del panel", 26, "recarga del panel v27 (RECARGA.md)"),
    "libro_clientes": (LIBRO_CLIENTES, "Sofía / Tomás", 24 * 31, "a mano (Holded + motivos de baja)"),
    "herramienta_ro": (HERRAMIENTA_RO, "Claude", 26, "~/RO_HERRAMIENTAS/externos.py y clickup_api/chat.py"),
    "plan_fichajes": (PLAN_FICHAJES, "Operaciones", 24 * 31, "a mano"),
    "panel_v29": (PANEL_RESULTADOS, "Tomás", 24 * 7, "a mano (panel de resultados)"),
    "panel_v7_mili": (MILI_PANEL_V7, "Mili", 24 * 7, "a mano"),
    "reparto_setters": (SETTERS_REPARTO, "Tomás", 24 * 31, "código (lector de GHL de RO)"),
    "moviles_correos": (MOVILES_CORREOS, "Operaciones", 24 * 31, "a mano"),
    "torre_zip": (TORRE_ZIP, "Valeria", 24 * 31, "a mano (anuncios de la Torre)"),
    "salarios_xlsx": (SALARIOS_XLSX, "Cecilia / Tomás (SENSIBLE)", 24 * 31, "a mano (sin la hoja de cuentas bancarias)"),
}

# ------------------------------------------------------------------ secretos
# Nombre del llavero → para qué. La variable de entorno es el mismo nombre en MAYÚSCULAS.
SECRETOS = {
    "clickup_api_token": "ClickUp (llave propia, solo lectura)",
    "zoho_client_id": "Zoho (Desk, CRM, Sign)", "zoho_client_secret": "Zoho", "zoho_refresh_token": "Zoho (no rota)",
    "zoho_sheet_refresh_token": "Zoho Sheet (importador W5, sin ejecutar)",
    "ghl_app_client_id": "GHL agencia (app privada)", "ghl_app_client_secret": "GHL agencia (app privada)",
    "ghl_app_refresh_token": "GHL agencia · ROTA EN CADA USO: dueño único la tubería, vive en la base de estado",
    "ghl_agency_pit": "GHL agencia (token privado, ga.py)",
    "GHL_PIT_NEW": "GHL subcuenta de RO (ghl.env; setters y ventas)",
    "meta_token": "Meta Ads (caduca 1-dic: cambiar por usuario de sistema)", "meta_app_secret": "Meta (renovación)",
    "google_client_id": "Google (Analytics, Search Console, Hojas)", "google_client_secret": "Google",
    "google_refresh_token": "Google (no rota)",
    "google_ads_developer_token": "Google Ads", "google_ads_login_customer_id": "Google Ads",
    "google_ads_refresh_token": "Google Ads",
    "google_gbp_refresh_token": "Google Business Profile (ficha de Google; permiso business.manage, la app solo lee; sin ella, «pendiente de aprobación»)",
    "metricool_token": "Metricool", "metricool_user_id": "Metricool",
    "zoom_account_id": "Zoom (Server-to-Server)", "zoom_client_id": "Zoom", "zoom_client_secret": "Zoom",
    "snov_client_id": "Snov.io", "snov_client_secret": "Snov.io",
    "seranking_project_key": "SE Ranking (proyectos)", "seranking_data_key": "SE Ranking (datos, gasta créditos)",
    "windsor_api_key": "Windsor (gasta cupo)",
    "modulards_api_key": "Modular DS (webs; sin ella, «sin conectar»)",
    "hostinger_api_token": "Hostinger (VPS, webs, dominios y renovaciones; solo GET; sin ella, «sin conectar»)",
    "holded_api_key": "Holded (solo GET)",
    "airtable_token": "Airtable de facturación (SOLO LECTURA)",
    "ZADARMA_KEY": "Zadarma (zadarma.env)", "ZADARMA_SECRET": "Zadarma (zadarma.env)",
}

# Lo que necesita cada lector de ~/RO_HERRAMIENTAS (y los generadores que leen llaves por su cuenta).
SECRETOS_POR_LECTOR = {
    "clickup_api/cu.py": ["clickup_api_token"],
    "clickup_api/chat.py": ["clickup_api_token"],
    "zoho/zh.py": ["zoho_client_id", "zoho_client_secret", "zoho_refresh_token"],
    "zoho/zbookings.py": ["zoho_client_id", "zoho_client_secret", "zoho_refresh_token"],
    "zadarma/zd.py": ["ZADARMA_KEY", "ZADARMA_SECRET"],
    "ghl_agencia/app.py": ["ghl_app_client_id", "ghl_app_client_secret", "ghl_app_refresh_token"],
    "ghl_agencia/ga.py": ["ghl_agency_pit"],
    "captacion/captacion.py": ["meta_token", "ghl_app_client_id", "ghl_app_client_secret", "ghl_app_refresh_token"],
    "meta/mt.py": ["meta_token", "meta_app_secret"],
    "google/gg.py": ["google_client_id", "google_client_secret", "google_refresh_token"],
    "google/gads.py": ["google_client_id", "google_client_secret", "google_ads_developer_token",
                       "google_ads_login_customer_id", "google_ads_refresh_token"],
    "google/gbp.py": ["google_client_id", "google_client_secret", "google_gbp_refresh_token"],
    "metricool/mc.py": ["metricool_token", "metricool_user_id"],
    "zoom/zm.py": ["zoom_account_id", "zoom_client_id", "zoom_client_secret"],
    "snov/sv.py": ["snov_client_id", "snov_client_secret"],
    "seranking/sr.py": ["seranking_project_key", "seranking_data_key"],
    "windsor/ws.py": ["windsor_api_key"],
    "holded/hd.py": ["holded_api_key"],
    "externos.py": ["google_client_id", "google_client_secret", "google_refresh_token", "metricool_token",
                    "metricool_user_id", "ghl_app_client_id", "ghl_app_client_secret", "ghl_app_refresh_token"],
    # generadores de la app que leen una llave directamente
    "30_APP/fuentes_dinero (airtable)": ["airtable_token"],
    "30_APP/fuentes_ajustes/generar_conexiones.py": ["meta_token", "clickup_api_token", "zoho_client_id",
        "zoho_client_secret", "zoho_refresh_token", "zoom_account_id", "zoom_client_id", "zoom_client_secret",
        "airtable_token", "snov_client_id", "snov_client_secret", "metricool_token", "metricool_user_id",
        "google_client_id", "google_client_secret", "google_refresh_token"],
    "30_APP/fuentes_ventas (ghl_comun.py de SETTERS_REPARTO)": ["GHL_PIT_NEW"],
}

# Ficheros .env que algunos lectores leen del disco (se generan desde las variables en el servidor).
FICHEROS_ENV = {
    "ghl.env": ["GHL_PIT_NEW"],
    "zadarma.env": ["ZADARMA_KEY", "ZADARMA_SECRET"],
}

ROTA = {"ghl_app_refresh_token"}   # llaves que cambian en cada uso: nunca en variables de entorno


def es_mac():
    return platform.system() == "Darwin"


def _de_llavero(nombre):
    if not es_mac():
        return None
    try:
        r = subprocess.run(["security", "find-generic-password", "-s", nombre, "-w"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or None if r.returncode == 0 else None
    except Exception:
        return None


def _de_env_fichero(nombre):
    """GHL_PIT_NEW y las de Zadarma viven hoy en ~/RO_BANDEJA_GHL/config/*.env."""
    for fichero, claves in FICHEROS_ENV.items():
        if nombre in claves:
            f = BANDEJA_GHL_CONFIG / fichero
            if f.exists():
                for linea in f.read_text(encoding="utf-8").splitlines():
                    if "=" in linea and not linea.lstrip().startswith("#"):
                        k, v = linea.split("=", 1)
                        if k.strip() == nombre and v.strip():
                            return v.strip()
    return None


def secreto(nombre, obligatorio=False):
    """Devuelve el valor (nunca lo imprime). Orden: carpeta privada → variable de entorno → .env → llavero.
    Con RO_SIN_LLAVES=1 (la noche de la migración, la pone migracion/noche.sh) no hay ninguna llave real: el agente que
    trabaja solo no puede leerlas ni llamar a un proveedor de verdad."""
    if os.environ.get("RO_SIN_LLAVES") == "1":
        if obligatorio:
            sys.exit(f"Sin llaves esta noche (RO_SIN_LLAVES=1): «{nombre}» no se lee.")
        return None
    d = os.environ.get("RO_SECRETOS_DIR")
    if d and (Path(d) / nombre).is_file():
        v = (Path(d) / nombre).read_text().strip()
        if v:
            return v
    if nombre not in ROTA:
        v = os.environ.get(nombre.upper()) or os.environ.get(nombre)
        if v:
            return v.strip()
    v = _de_env_fichero(nombre) or _de_llavero(nombre)
    if v:
        return v
    if obligatorio:
        sys.exit(f"Falta el secreto «{nombre}» ({SECRETOS.get(nombre, '¿?')}). "
                 f"En el Mac: llavero. En el servidor: variable {nombre.upper()}.")
    return None


def de_donde(nombre):
    """De dónde saldría cada secreto (para la salud y DESPLIEGUE.md). Nunca el valor."""
    d = os.environ.get("RO_SECRETOS_DIR")
    if d and (Path(d) / nombre).is_file():
        return "carpeta_privada"
    if nombre not in ROTA and (os.environ.get(nombre.upper()) or os.environ.get(nombre)):
        return "entorno"
    if _de_env_fichero(nombre):
        return "fichero_env"
    if _de_llavero(nombre):
        return "llavero"
    return None


def resumen():
    return {
        "maquina": "mac" if es_mac() else platform.system().lower(),
        "rutas": {k: str(v) for k, v in {
            "APP": APP, "PROYECTO": PROYECTO, "HOME": HOME, "CRUDOS": CRUDOS, "HERRAMIENTAS": HERRAMIENTAS,
            "DATOS": DATOS, "ESTADO_DIR": ESTADO_DIR, "BANDEJA_GHL_CONFIG": BANDEJA_GHL_CONFIG}.items()},
        "datos_a_mano": {k: {"ruta": str(r), "existe": Path(r).exists(), "dueno": d, "edad_max_h": h, "origen": o}
                         for k, (r, d, h, o) in DATOS_A_MANO.items()},
        "secretos": {n: de_donde(n) for n in SECRETOS},
    }


if __name__ == "__main__":
    r = resumen()
    if "--json" in sys.argv:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        sys.exit(0)
    print(f"Máquina: {r['maquina']}")
    for k, v in r["rutas"].items():
        print(f"  {k:<20} {v}")
    print("Datos a mano:")
    for k, v in r["datos_a_mano"].items():
        print(f"  {'✔' if v['existe'] else '✘'} {k:<16} {v['ruta']}")
    faltan = [n for n, o in r["secretos"].items() if not o]
    print(f"Secretos: {len(r['secretos']) - len(faltan)} de {len(r['secretos'])} disponibles (sin enseñar valores).")
    for n in faltan:
        print(f"  falta {n}  ({SECRETOS[n]})")
