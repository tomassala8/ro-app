#!/usr/bin/env python3
"""despliegue/vigia.py · el VIGÍA: validador independiente de la tubería (3-oct-2026).

Encargo de Tomás: «sobre todo Agus tenga un panel de conexión con Google, con GoHighLevel, con ClickUp…; que siempre haya
un validador cada X momentos de que esté funcionando».

Qué hace cada 10 minutos (configurable en data/vigia/config.json → «cada_min», o RO_VIGIA_CADA_MIN):
  1. CONEXIONES (las de despliegue/salud_conexiones.py, la misma lista y las mismas pruebas): UNA lectura barata por
     herramienta, nada que escriba ni gaste créditos. La app de GHL que ROTA no se llama nunca (cada uso cambia la llave):
     se mira su última rotación y el último dato bueno de la tubería. Lo que tiene cupo diario corto se prueba menos a
     menudo («cada_min_conexion»: Bookings, Windsor, SE Ranking). Una conexión que sale en rojo se prueba otra vez a los
     pocos segundos antes de darla por caída (un corte de un segundo no despierta a nadie).
  2. LA APP POR DENTRO: la app web responde · última vuelta de la tubería y su estado · envíos pendientes o fallidos ·
     cambios sin reflejar en ClickUp y conflictos · uso de la IA frente a su tope (en %, sin importes) · espacio en disco ·
     tamaño y salud de la base · copia de seguridad del día.
  3. HISTÓRICO de las últimas 24 h por fila (color y tiempo de respuesta de cada prueba) para el minigráfico.
  4. AVISOS en #avisos-altas, AGRUPADOS y sin repetir: cuando algo pasa a rojo → un mensaje a Agus con todo lo que ha
     caído en esa vuelta; si sigue en rojo más de 1 h («escalar_min») → un mensaje a Mili y Tomás; cuando vuelve →
     un mensaje de recuperación (a Agus, y a Mili y Tomás si se les avisó). Nunca un aviso por vuelta.
Deja data/vigia/estado.json (lo pinta «Salud del sistema», modulos/ajustes_conexiones.js, por GET /api/vigia) y su
estado interno en data/vigia/episodios.json (qué está caído desde cuándo y qué se avisó) y data/vigia/avisos.jsonl.
Es INDEPENDIENTE de la tubería: no la necesita para correr y la vigila a ella también. No toca data/conexiones/salud.json.

Uso:
  python3 despliegue/vigia.py                    una vuelta entera (≈ 30 lecturas baratas, 10-30 s)
  python3 despliegue/vigia.py --solo clickup     solo esa fila («Probar ahora» de la pantalla); el resto se conserva
  python3 despliegue/vigia.py --bucle            LOCAL: una vuelta cada «cada_min» minutos, cada una en su propio proceso
  Otras: --sin-red (conexiones sin llamada: solo llaves) · --sin-avisos (ni avisa ni toca los episodios) · --quien <id>
         --simular '{"clickup":"rojo","*":"verde"}' (pruebas: conexiones forzadas, sin red) · --json (resumen)
         --prueba [--dejar <carpeta>]  simulacro de caídas sobre una COPIA de local.db en una carpeta temporal
  Variables: RO_DB (base de avisos y envíos; copia para pruebas) · RO_VIGIA_DIR (dónde escribe) · RO_VIGIA_APP_URL (la
         app web; vacío = no se mira) · RO_VIGIA_AHORA («AAAA-MM-DD HH:MM», reloj falso para pruebas) ·
         RO_VIGIA_LATIDO_URL (latido de Better Stack al acabar cada vuelta: si el vigía se para, avisa desde fuera).
Códigos de salida: 0 si ha podido escribir el estado (aunque algo esté en rojo) · 75 otra vuelta en marcha.
Nunca imprime ni guarda una llave: los textos se sanean (ni llaves, ni correos, ni teléfonos).
"""
import calendar
import fcntl
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
MADRID = ZoneInfo("Europe/Madrid")
FMT = "%Y-%m-%d %H:%M"
CANAL = "avisos-altas"
VEN = ["direccion", "operaciones", "tecnico_altas"]        # quién ve los avisos del vigía (Agus, Mili y Tomás)
PERSONAS = {"tomas": "Tomás", "agustina": "Agus", "mili": "Mili", "sofia": "Sofía", "yessica": "Yessica", "constanza": "Constanza"}
CONF_DEF = {
    "cada_min": 10,              # cada cuánto pasa el vigía
    "escalar_min": 60,           # rojo más de esto → aviso a Mili y Tomás
    "reintento_s": 4,            # una conexión en rojo se vuelve a probar a los N s antes de darla por caída
    "cada_min_conexion": {"zoho_bookings": 30, "windsor": 60, "seranking": 60},   # cupo diario corto: menos a menudo
    "tuberia_max_min_dia": 150,  # sin vuelta acabada en más de esto (7-23 h) → rojo; la ligera va cada hora
    "tuberia_vigilar_min_dia": 90,
    "tuberia_max_min_noche": 300,  # de 0 a 7 h: la última ligera es a las 23 y la noche a las 3
    "tuberia_atascada_min": 180,
    "envio_pendiente_vigilar_min": 30, "envio_pendiente_rojo_min": 120,
    "disco_rojo_gb": 2, "disco_vigilar_gb": 10, "disco_rojo_pct": 5, "disco_vigilar_pct": 10,
    "base_vigilar_mb": 1024, "base_rojo_mb": 4096,
    "historial_h": 24,
}
RX_SECRETO = re.compile(r"(?i)(token|key|secret|password|access_token|input_token|api_key)=[^&\s]+")
RX_LARGO = re.compile(r"[A-Za-z0-9_\-.]{32,}")
RX_CORREO = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
RX_TEL = re.compile(r"(?<![\w.\-/=#:])(?:(?:\+34|0034)[\s.-]?)?[6789]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}(?![\w.\-/:])|\+\d{10,14}\b")   # teléfonos, no fechas
RX_ID = re.compile(r"^[a-z0-9_]{2,40}$")


# ======================================================================= utilidades
def sanear(t, tope=400):
    t = RX_SECRETO.sub(r"\1=[oculto]", str(t or ""))
    t = RX_LARGO.sub("[…]", t)
    t = RX_CORREO.sub("[correo]", t)
    return RX_TEL.sub("[número]", t)[:tope]


def num(x, d=1):
    """Número a la española (1.234,5)."""
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def sin_terminal(t):
    """Quita las órdenes de terminal («con bash ~/…/pegar.sh», «security add-generic-password …»): van solo en pantalla."""
    t = re.sub(r"\s*(?:y\s+)?(?:pégala|pégalo|guárdala)?\s*con\s+bash\s+\S+", "", str(t or ""), flags=re.I)
    t = re.sub(r":\s*security\s+add-generic-password[^.]*", "", t, flags=re.I)
    t = t.replace("(botón «Consola de la llave») ", "")
    return re.sub(r"\s{2,}", " ", re.sub(r"\s+\.", ".", t)).strip()


def vigia_dir():
    import config
    return Path(os.environ.get("RO_VIGIA_DIR") or config.DATOS / "vigia")


def ruta_db():
    return Path(os.environ.get("RO_DB") or APP / "local.db")


def ahora():
    """Hora de Madrid sin zona. RO_VIGIA_AHORA fija un reloj falso (solo pruebas)."""
    f = os.environ.get("RO_VIGIA_AHORA")
    if f:
        return datetime.strptime(f, FMT)
    return datetime.now(MADRID).replace(tzinfo=None, second=0, microsecond=0)


def a_utc_txt(d):
    """Hora de Madrid sin zona → texto UTC de SQLite (lo que espera canal_mensajes.creado)."""
    return d.replace(tzinfo=MADRID).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def de_utc_txt(t):
    try:
        return datetime.strptime(str(t)[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).astimezone(MADRID).replace(tzinfo=None)
    except (TypeError, ValueError):
        return None


def minuto(d):
    """Minuto «de reloj de Madrid» como número (la hora sin zona tomada tal cual): igual en el Mac y en un servidor en UTC."""
    return int(calendar.timegm(d.timetuple()) // 60)


def leer(f, defecto):
    try:
        return json.loads(Path(f).read_text(encoding="utf-8"))
    except Exception:
        return defecto


def escribir(f, doc):
    """Atómico y SOLO si pasa la puerta de secretos de E0."""
    f = Path(f)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f".{f.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    try:
        sys.path.insert(0, str(APP)) if str(APP) not in sys.path else None
        import escaner_secretos as ESC
        hall = ESC.escanear_fichero(tmp)
    except ImportError:
        hall = []
    if hall:
        tmp.unlink()
        raise SystemExit(f"Puerta de secretos: {f.name} no se escribe ({[h.get('tipo') for h in hall[:3]]})")
    os.replace(tmp, f)


def conf():
    c = json.loads(json.dumps(CONF_DEF))
    extra = leer(vigia_dir() / "config.json", {}) or {}
    for k, v in extra.items():
        if k.startswith("_"):
            continue
        if isinstance(v, dict) and isinstance(c.get(k), dict):
            c[k].update(v)
        else:
            c[k] = v
    if os.environ.get("RO_VIGIA_CADA_MIN"):
        c["cada_min"] = max(1, int(os.environ["RO_VIGIA_CADA_MIN"]))
    return c


@contextmanager
def candado(espera_s=0):
    d = vigia_dir()
    d.mkdir(parents=True, exist_ok=True)
    f = open(d / ".vigia.lock", "a+")
    t0 = time.time()
    while True:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.time() - t0 >= espera_s:
                f.close()
                raise Ocupado()
            time.sleep(1)
    try:
        yield
    finally:
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()


class Ocupado(Exception):
    pass


def db():
    con = sqlite3.connect(str(ruta_db()), timeout=20)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=20000")
    return con


def tabla(con, nombre):
    return bool(con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (nombre,)).fetchone())


def fila(id, nombre, grupo, icono, color, titular, detalle, que_hacer=None, quien_id=None, ms=None, ok=None, critica=True, **extra):
    r = {"id": id, "nombre": nombre, "grupo": grupo, "icono": icono, "color": color, "titular": titular,
         "detalle": sanear(detalle, 500) if detalle else None,
         "que_hacer": sanear(re.sub(r"(en )?despliegue/pasos\.json", "en la lista de pasos de la tubería", que_hacer), 500) if que_hacer else None,
         "quien_id": quien_id, "quien": PERSONAS.get(quien_id) if quien_id else None, "ms": ms,
         "ok": (color in ("verde", "ambar")) if ok is None else ok, "critica": critica}
    r.update(extra)
    return r


# ======================================================================= 1 · conexiones (las de salud_conexiones.py)
_SC = None


def sc():
    """Carga despliegue/salud_conexiones.py como biblioteca (sin que lea los argumentos de este proceso)."""
    global _SC
    if _SC is None:
        for p in (str(AQUI), str(APP)):
            if p not in sys.path:
                sys.path.append(p)
        argv, sys.argv = sys.argv, [sys.argv[0]]
        try:
            import salud_conexiones as SC
        finally:
            sys.argv = argv
        _SC = SC
    return _SC


def ids_conexiones():
    return [c["id"] for c in sc().CONEXIONES]


MODULAR_QUE = "Lo hace Tomás: pegar la clave de solo lectura con modular/pegar.sh"
HOSTINGER_QUE = "Lo hace Tomás: hPanel → Perfil → API → crear token y bash ~/RO_HERRAMIENTAS/hostinger/pegar.sh"


def de_sc(f, c):
    """Fila de salud_conexiones → fila del vigía (sin el historial de 12 de allí: aquí hay 24 h)."""
    color = f.get("color") or "gris"
    estado = f.get("estado")
    r = fila(f["id"], f["nombre"], "conexiones", f.get("icono") or "plug", color, f.get("titular") or "",
             f.get("detalle"), f.get("que_hacer"), f.get("quien_id"), f.get("ms"),
             ok=bool(f.get("ok")) if f.get("ok") is not None else None, critica=bool(c.get("critica")),
             estado=estado, herramienta=f.get("grupo"), que_da=f.get("que_da"), modulos=f.get("modulos"),
             caduca=f.get("caduca"), dias_para_caducar=f.get("dias_para_caducar"), caducidad_texto=f.get("caducidad_texto"),
             renovar=f.get("renovar"), limite=f.get("limite"), error_llano=sanear(f.get("error_llano")) if f.get("error_llano") else None)
    if f["id"] == "modular" and estado in ("falta_clave", "llave_mala", "sin_permiso", "rechazo", "error"):
        hay = "" if estado == "falta_clave" else f" (la que hay en el llavero no vale: {sanear(f.get('error_llano') or estado)[:90].rstrip('.')})"
        r.update(color="ambar", estado="sin_clave", titular="Sin clave", ok=False, quien_id="tomas", quien="Tomás",
                 detalle=f"Sin clave{hay} · lo hace Tomás: pegar la clave de solo lectura con modular/pegar.sh. Hasta entonces, Webs no sabe de caídas, copias ni certificados de las webs.",
                 que_hacer=MODULAR_QUE + "; después Agus pulsa «Probar ahora» y comprueba que sale en verde.")
    if f["id"] == "hostinger" and estado in ("falta_clave", "llave_mala", "sin_permiso", "rechazo", "error"):
        hay = "" if estado == "falta_clave" else f" (la que hay en el llavero no vale: {sanear(f.get('error_llano') or estado)[:90].rstrip('.')})"
        r.update(color="ambar", estado="sin_clave", titular="Sin clave", ok=False, quien_id="tomas", quien="Tomás",
                 detalle=f"Sin clave{hay} · {HOSTINGER_QUE}. Hasta entonces, la app no sabe de VPS caídos, webs suspendidas, certificados ni dominios de Hostinger.",
                 que_hacer=HOSTINGER_QUE + "; después Agus pulsa «Probar ahora» y comprueba que sale en verde.")
    return r


def simulada(c, color):
    SC = sc()
    if color == "verde":
        return {"id": c["id"], "nombre": c["nombre"], "grupo": c["grupo"], "icono": c.get("icono"), "que_da": c.get("que_da"),
                "modulos": c.get("modulos"), "renovar": c.get("renovar"), "limite": c.get("limite"), "color": "verde",
                "estado": "bien", "ok": True, "titular": "Funciona", "detalle": "responde (simulado)", "ms": 180 + (len(c["id"]) * 37) % 400}
    tipo = "caida_proveedor" if color == "rojo" else "lenta"
    quien, paso = SC.que_hacer(c, tipo, "tecnico")
    return {"id": c["id"], "nombre": c["nombre"], "grupo": c["grupo"], "icono": c.get("icono"), "que_da": c.get("que_da"),
            "modulos": c.get("modulos"), "renovar": c.get("renovar"), "limite": c.get("limite"), "color": color,
            "estado": tipo, "ok": color != "rojo", "titular": "No responde (simulado)" if color == "rojo" else "Lenta (simulado)",
            "detalle": "La herramienta está fallando por su lado (error 503). No es de RO. (simulado)" if color == "rojo" else "responde, pero lenta (simulado)",
            "error_llano": "La herramienta está fallando por su lado (error 503). No es de RO." if color == "rojo" else None,
            "que_hacer": paso, "quien_id": quien, "ms": None if color == "rojo" else 7200}


def probar_conexiones(ids, sin_red=False, forzadas=None, reintento_s=4):
    SC = sc()
    SC.AHORA = datetime.now()
    SC.SIN_RED = bool(sin_red)
    SC.SIN_AVISOS = True
    lista = [c for c in SC.CONEXIONES if c["id"] in ids]
    if forzadas is not None:
        defecto = forzadas.get("*", "verde")
        return [de_sc(simulada(c, forzadas.get(c["id"], defecto)), c) for c in lista]
    if not sin_red and any(c.get("servicio") for c in lista):
        SC.renovar_tokens()          # tokens de acceso de 1 h: solo si les quedan < 20 min (caché compartida). GHL nunca.
    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        filas = list(ex.map(SC.evaluar, lista))
    rojas = [i for i, f in enumerate(filas) if f.get("color") == "rojo" and f.get("estado") not in ("falta_clave", "caduca_pronto", "sin_probar")]
    if rojas and not sin_red:
        time.sleep(reintento_s)
        with cf.ThreadPoolExecutor(max_workers=6) as ex:
            otra = list(ex.map(SC.evaluar, [lista[i] for i in rojas]))
        for i, f in zip(rojas, otra):
            filas[i] = f
    return [de_sc(f, c) for f, c in zip(filas, lista)]


# ======================================================================= 2 · la app por dentro
def c_app_web(C, ahora_):
    url = os.environ.get("RO_VIGIA_APP_URL", "http://127.0.0.1:8770/")
    if not url:
        return None
    t0 = time.time()
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "ro-vigia/1.0"}), timeout=10)
        code = r.status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception as e:  # noqa: BLE001
        return fila("app_web", "La app (servidor web)", "sistema", "globe", "rojo", "No responde",
                    f"No contesta en {int(time.time() - t0)} s ({type(e).__name__}). Nadie puede entrar a la app.",
                    "Agus: reinicia el servicio de la app (en Coolify: «Restart» del recurso; en el Mac: vuelve a lanzar el servidor) y mira sus registros. Si no arranca en 15 min, avisa a Tomás.",
                    "agustina", None)
    ms = int((time.time() - t0) * 1000)
    if code >= 500:
        return fila("app_web", "La app (servidor web)", "sistema", "globe", "rojo", f"Responde con error {code}",
                    "El servidor contesta pero falla por dentro: nadie puede trabajar con la app.",
                    "Agus: mira los registros del servicio y reinícialo; si sigue, avisa a Tomás.", "agustina", ms)
    if ms > 5000:
        return fila("app_web", "La app (servidor web)", "sistema", "globe", "ambar", f"Lenta ({ms / 1000:.1f} s)",
                    "La app tarda en contestar.", "Agus: mira el uso de memoria y procesador del servidor; si sigue lenta 3 vueltas, avisa a Tomás.", "agustina", ms)
    return fila("app_web", "La app (servidor web)", "sistema", "globe", "verde", "Funciona", f"contesta (código {code})", None, None, ms)


def _hora(t):
    if not t:
        return None
    try:
        return datetime.fromisoformat(str(t).replace(" ", "T")[:19])
    except ValueError:
        return None


def c_tuberia(C, ahora_):
    t0 = time.time()
    try:
        if str(AQUI) not in sys.path:
            sys.path.append(str(AQUI))
        import estado as ES
        E = ES.abrir()
        ult = E.ultimas(8)
        sellos = E.sellos()
    except Exception as e:  # noqa: BLE001
        return fila("tuberia", "Tubería de datos", "sistema", "recargar", "rojo", "No se puede leer su estado",
                    f"La base de estado de la tubería no responde ({type(e).__name__}).",
                    "Agus: comprueba la base de la app (en el servidor, el servicio de la base) y vuelve a probar.", "agustina", None)
    ms = int((time.time() - t0) * 1000)
    viejos = [s["paso"] for s in sellos if s.get("estado") in ("dato_viejo", "sin_dato")]
    if not ult:
        return fila("tuberia", "Tubería de datos", "sistema", "recargar", "ambar", "No ha corrido nunca aquí",
                    "Todavía no hay ninguna vuelta registrada en esta máquina.",
                    "Agus: comprueba que las tareas programadas de la tubería están dadas de alta (ligera cada hora, completa a las 6 y a las 14).",
                    "agustina", ms)
    filas = [dict(zip(("id", "modo", "quien", "inicio", "fin", "estado"), r)) for r in ult]
    en_curso = [f for f in filas if f["estado"] == "en_curso" and _hora(f["inicio"])]
    acabadas = [f for f in filas if f["fin"] and f["estado"] != "en_curso"]
    extra = {"ultima_vuelta": None}
    for f in en_curso:
        dur = (ahora_ - _hora(f["inicio"])).total_seconds() / 60
        if dur > C["tuberia_atascada_min"]:
            return fila("tuberia", "Tubería de datos", "sistema", "recargar", "rojo", "Atascada",
                        f"La vuelta «{f['modo']}» empezó a las {_hora(f['inicio']):%H:%M} y lleva {int(dur)} min sin acabar: las siguientes no pueden entrar.",
                        "Agus: mira el registro de esa vuelta (paso en el que está) y, si está colgada, para el proceso; la siguiente vuelta retoma con el último dato bueno.",
                        "agustina", ms)
    if not acabadas:
        return fila("tuberia", "Tubería de datos", "sistema", "recargar", "ambar", "En marcha", "Hay una vuelta en marcha y ninguna acabada todavía.", None, None, ms)
    u = acabadas[0]
    fin = _hora(u["fin"])
    edad = int((ahora_ - fin).total_seconds() / 60) if fin else 10 ** 6
    noche = ahora_.hour < 7
    tope = C["tuberia_max_min_noche"] if noche else C["tuberia_max_min_dia"]
    vigilar = C["tuberia_max_min_noche"] if noche else C["tuberia_vigilar_min_dia"]
    extra["ultima_vuelta"] = {"modo": u["modo"], "estado": u["estado"], "fin": fin.strftime(FMT) if fin else None, "hace_min": edad}
    hace = f"hace {edad} min" if edad < 120 else f"hace {edad // 60} h {edad % 60} min"
    base = f"Última vuelta «{u['modo']}» acabada a las {fin:%H:%M} del {fin:%d-%m} ({hace}): {'bien' if u['estado'] == 'ok' else u['estado'].replace('_', ' ')}."
    if viejos:
        base += f" Con dato viejo: {', '.join(viejos[:6])}{'…' if len(viejos) > 6 else ''}."
    if edad > tope:
        return fila("tuberia", "Tubería de datos", "sistema", "recargar", "rojo", "Sin vueltas", base + " Los datos de la app se están quedando viejos.",
                    "Agus: comprueba que la tarea programada de la tubería sigue activa (en Coolify, «Scheduled Tasks»; en el Mac, que alguien la lanza) y su último registro. Mientras, Mili o Tomás pueden pulsar «Actualizar ahora».",
                    "agustina", ms, **extra)
    if u["estado"] != "ok" or edad > vigilar or viejos:
        return fila("tuberia", "Tubería de datos", "sistema", "recargar", "ambar",
                    "Con fallos" if u["estado"] == "con_fallos" else "Vuelta interrumpida" if u["estado"] == "interrumpida" else "Datos con retraso" if edad > vigilar else "Con dato viejo",
                    base, "Agus: la app sigue con el último dato bueno de lo que falló. Mira qué paso falló en el registro; si falla 3 vueltas seguidas, pídeselo a Claude con este aviso.",
                    "agustina", ms, **extra)
    return fila("tuberia", "Tubería de datos", "sistema", "recargar", "verde", "Funciona", base, None, None, ms, **extra)


def c_envios(C, ahora_):
    t0 = time.time()
    con = db()
    try:
        if not tabla(con, "envios"):
            return fila("envios", "Envíos de la app (correo, WhatsApp, GHL)", "sistema", "send", "verde", "Sin envíos todavía",
                        "Todavía no ha salido nada desde la app.", None, None, int((time.time() - t0) * 1000))
        filas = con.execute("SELECT e.id, e.modo, (SELECT estado FROM envio_pasos p WHERE p.envio_id=e.id ORDER BY p.id DESC LIMIT 1) AS estado, "
                            "(SELECT hora FROM envio_pasos p WHERE p.envio_id=e.id ORDER BY p.id DESC LIMIT 1) AS hora FROM envios e").fetchall()
    finally:
        con.close()
    ms = int((time.time() - t0) * 1000)
    sim = sum(1 for f in filas if f["estado"] == "simulado")
    pend_v, pend_r, fall = [], [], []
    for f in filas:
        h = de_utc_txt(f["hora"]) or ahora_
        edad = (ahora_ - h).total_seconds() / 60
        if f["estado"] in ("pendiente", "enviado"):
            (pend_r if edad > C["envio_pendiente_rojo_min"] else pend_v if edad > C["envio_pendiente_vigilar_min"] else []).append(f["id"])
        elif f["estado"] in ("fallido", "rebotado") and edad <= 24 * 60:
            fall.append(f["id"])
    resumen = f"{len(filas)} en total · {sim} simulados (hoy nada sale de verdad)" if sim else f"{len(filas)} en total"
    extra = {"cuenta": {"fallidos_24h": len(fall), "pendientes_viejos": len(pend_r) + len(pend_v), "simulados": sim}}
    if fall or pend_r:
        partes = ([f"{len(fall)} fallidos o rebotados en 24 h"] if fall else []) + ([f"{len(pend_r)} pendientes hace más de {C['envio_pendiente_rojo_min'] // 60} h"] if pend_r else [])
        return fila("envios", "Envíos de la app (correo, WhatsApp, GHL)", "sistema", "send", "rojo", "Hay envíos sin salir",
                    f"{' · '.join(partes)}. {resumen}.",
                    "Agus: abre Envíos, mira el motivo de cada uno y pulsa «Reintentar» si es seguro (antes mira si ya llegó). Si es la llave de envío, Tomás.",
                    "agustina", ms, **extra)
    if pend_v:
        return fila("envios", "Envíos de la app (correo, WhatsApp, GHL)", "sistema", "send", "ambar", "Envíos que tardan",
                    f"{len(pend_v)} pendientes hace más de {C['envio_pendiente_vigilar_min']} min. {resumen}.",
                    "Agus: si en la próxima vuelta siguen pendientes, mira en Envíos si la herramienta los ha recibido.", "agustina", ms, **extra)
    return fila("envios", "Envíos de la app (correo, WhatsApp, GHL)", "sistema", "send", "verde", "Funciona",
                f"Nada pendiente ni fallido. {resumen}.", None, None, ms, **extra)


def c_clickup(C, ahora_):
    t0 = time.time()
    con = db()
    try:
        if not tabla(con, "sinc_cambios"):
            return fila("sincronia_clickup", "Cambios hacia ClickUp", "sistema", "check", "verde", "Sin cambios todavía",
                        "Todavía no se ha hecho ningún cambio desde la app que tenga que ir a ClickUp.", None, None, int((time.time() - t0) * 1000))
        filas = con.execute("SELECT c.id, c.modo, c.creado, (SELECT estado FROM sinc_pasos p WHERE p.cambio_id=c.id ORDER BY p.id DESC LIMIT 1) AS estado "
                            "FROM sinc_cambios c").fetchall()
    finally:
        con.close()
    try:
        if str(APP) not in sys.path:
            sys.path.append(str(APP))
        import sincronia as SIN
        horas = float(SIN.conf().get("horas_sin_reflejar") or 4)
    except Exception:  # noqa: BLE001
        horas = 4.0
    ms = int((time.time() - t0) * 1000)
    conflictos = [f["id"] for f in filas if f["estado"] == "conflicto"]
    fallidos = [f["id"] for f in filas if f["estado"] == "fallido"]
    viejos = [f["id"] for f in filas if f["estado"] in ("pendiente", "enviado")
              and (ahora_ - (de_utc_txt(f["creado"]) or ahora_)).total_seconds() > horas * 3600]
    sim = sum(1 for f in filas if f["estado"] == "simulado")
    resumen = f"{len(filas)} cambios hechos en la app" + (f" · {sim} en simulación (hoy no se escribe nada en ClickUp)" if sim else "")
    extra = {"cuenta": {"conflictos": len(conflictos), "fallidos": len(fallidos), "sin_reflejar": len(viejos), "simulados": sim}}
    if fallidos:
        return fila("sincronia_clickup", "Cambios hacia ClickUp", "sistema", "check", "rojo", "Cambios que no llegan",
                    f"{len(fallidos)} cambios fallidos: lo hecho en la app no está en ClickUp. {resumen}.",
                    "Agus: abre Envíos › ClickUp, mira el motivo y pulsa «Reintentar»; si dice «llave», Tomás renueva la llave de servicio de ClickUp.",
                    "agustina", ms, **extra)
    if conflictos or viejos:
        partes = ([f"{len(conflictos)} conflictos (en ClickUp lo cambió otra persona)"] if conflictos else []) + \
                 ([f"{len(viejos)} sin reflejar hace más de {horas:g} h"] if viejos else [])
        return fila("sincronia_clickup", "Cambios hacia ClickUp", "sistema", "check", "ambar", "Conflictos por resolver" if conflictos else "Sin reflejar",
                    f"{' · '.join(partes)}. {resumen}.",
                    "Mili (o quien hizo el cambio): abre Envíos › ClickUp y elige qué versión vale en cada conflicto. Lo que solo tarda lo vigila Agus.",
                    "mili" if conflictos else "agustina", ms, **extra)
    return fila("sincronia_clickup", "Cambios hacia ClickUp", "sistema", "check", "verde", "Funciona", f"Nada fallido ni en conflicto. {resumen}.", None, None, ms, **extra)


def c_ia(C, ahora_):
    """Uso de la IA frente a su tope, EN PORCENTAJE (los importes solo los ve Tomás en Gasto de IA)."""
    t0 = time.time()
    try:
        if str(APP) not in sys.path:
            sys.path.append(str(APP))
        import ia_gasto as IG
        topes = json.loads(json.dumps(IG.TOPES_DEFECTO))
    except Exception:  # noqa: BLE001
        topes = {"activa": True, "mes_eur": 150.0, "dia_eur": 10.0, "aviso_pct": 80}
    con = db()
    try:
        if not tabla(con, "ia_gasto"):
            return fila("ia_tope", "IA de la app frente a su tope", "sistema", "spark", "verde", "Sin uso todavía",
                        "La IA aún no ha hecho ninguna llamada.", None, None, int((time.time() - t0) * 1000))
        if tabla(con, "ia_topes"):
            f = con.execute("SELECT valores FROM ia_topes ORDER BY id DESC LIMIT 1").fetchone()
            if f:
                try:
                    topes.update({k: v for k, v in json.loads(f[0]).items() if k != "funcion_mes_eur"})
                except ValueError:
                    pass
        mes, dia = ahora_.strftime("%Y-%m"), ahora_.strftime("%Y-%m-%d")
        en_mes = float(con.execute("SELECT COALESCE(SUM(coste_eur),0) FROM ia_gasto WHERE mes=?", (mes,)).fetchone()[0] or 0)
        en_dia = float(con.execute("SELECT COALESCE(SUM(coste_eur),0) FROM ia_gasto WHERE dia=?", (dia,)).fetchone()[0] or 0)
        corte_console = con.execute("SELECT COUNT(*) FROM ia_gasto WHERE mes=? AND motivo LIKE 'tope_console%'", (mes,)).fetchone()[0]
    finally:
        con.close()
    ms = int((time.time() - t0) * 1000)
    pm = round(100 * en_mes / topes["mes_eur"]) if topes.get("mes_eur") else 0
    pd = round(100 * en_dia / topes["dia_eur"]) if topes.get("dia_eur") else 0
    texto = f"Este mes lleva el {pm} % de su tope; hoy, el {pd} % del tope del día."
    extra = {"pct_mes": pm, "pct_dia": pd}
    if not topes.get("activa", True):
        return fila("ia_tope", "IA de la app frente a su tope", "sistema", "spark", "ambar", "Apagada a mano",
                    "La IA está apagada: la app sirve reglas y lo ya preparado, sin coste. " + texto,
                    "Tomás: la enciende en Sistema › Gasto de IA cuando quiera.", "tomas", ms, **extra)
    if max(pm, pd) >= 100 or corte_console:
        return fila("ia_tope", "IA de la app frente a su tope", "sistema", "spark", "rojo", "Tope alcanzado: modo reglas",
                    "La IA ha llegado a su tope y la app ha pasado sola a reglas (sin coste; nada se rompe). " + texto,
                    "Tomás: si quieres más IA hoy o este mes, sube el tope en Sistema › Gasto de IA. Si no, vuelve sola mañana o el día 1.", "tomas", ms, **extra)
    if max(pm, pd) >= topes.get("aviso_pct", 80):
        return fila("ia_tope", "IA de la app frente a su tope", "sistema", "spark", "ambar", f"Al {max(pm, pd)} % del tope",
                    texto + " Al 100 % pasa sola a reglas, sin coste.", "Tomás: decide si subes el tope en Sistema › Gasto de IA.", "tomas", ms, **extra)
    return fila("ia_tope", "IA de la app frente a su tope", "sistema", "spark", "verde", "Dentro del tope", texto, None, None, ms, **extra)


def c_disco(C, ahora_):
    t0 = time.time()
    u = shutil.disk_usage(str(APP))
    libre_gb = u.free / 1024 ** 3
    pct = 100 * u.free / u.total if u.total else 0
    ms = int((time.time() - t0) * 1000)
    texto = f"Quedan {num(libre_gb)} GB libres ({pct:.0f} % del disco)."
    extra = {"libre_gb": round(libre_gb, 1), "libre_pct": round(pct, 1)}
    que = ("Agus: libera espacio (copias de más de 14 días y registros viejos de la tubería en la carpeta de estado); "
           "en el servidor, amplía el disco del volumen en Coolify. Sin espacio, la base y las copias dejan de guardarse.")
    if libre_gb < C["disco_rojo_gb"] or pct < C["disco_rojo_pct"]:
        return fila("disco", "Espacio en disco", "sistema", "base", "rojo", "Casi lleno", texto, que, "agustina", ms, **extra)
    if libre_gb < C["disco_vigilar_gb"] or pct < C["disco_vigilar_pct"]:
        return fila("disco", "Espacio en disco", "sistema", "base", "ambar", "Se está llenando", texto, que, "agustina", ms, **extra)
    return fila("disco", "Espacio en disco", "sistema", "base", "verde", "Funciona", texto, None, None, ms, **extra)


def _mb(p):
    try:
        return Path(p).stat().st_size / 1024 ** 2
    except OSError:
        return 0.0


def c_base(C, ahora_):
    t0 = time.time()
    p = ruta_db()
    if not p.exists():
        return fila("base", "Base de datos de la app", "sistema", "base", "rojo", "No está",
                    "No se encuentra la base de la app (rastro, decisiones, avisos).", "Agus: restaura la última copia (despliegue, «copia de la base») y avisa a Tomás.", "agustina", None)
    mb = _mb(p) + _mb(str(p) + "-wal")
    import config
    est = config.ESTADO_DIR / "tuberia.db"
    mb_est = _mb(est)
    sano = "sin mirar"
    try:
        if mb < 500:
            c = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=10)
            sano = c.execute("PRAGMA quick_check").fetchone()[0]
            c.close()
    except sqlite3.Error as e:
        sano = f"error: {type(e).__name__}"
    ms = int((time.time() - t0) * 1000)
    texto = f"Base de la app: {num(mb)} MB · estado de la tubería: {num(mb_est)} MB · comprobación interna: {'bien' if sano == 'ok' else sano}."
    extra = {"mb": round(mb, 1), "mb_estado": round(mb_est, 1)}
    if sano not in ("ok", "sin mirar"):
        return fila("base", "Base de datos de la app", "sistema", "base", "rojo", "Dañada", texto,
                    "Agus: para la app, restaura la copia de hoy (o la de ayer) aparte y compárala; avisa a Tomás antes de cambiar nada.", "agustina", ms, **extra)
    if mb > C["base_rojo_mb"]:
        return fila("base", "Base de datos de la app", "sistema", "base", "rojo", "Demasiado grande", texto, "Agus: pídeselo a Claude con este aviso (hay que archivar el rastro antiguo).", "agustina", ms, **extra)
    if mb > C["base_vigilar_mb"]:
        return fila("base", "Base de datos de la app", "sistema", "base", "ambar", "Creciendo", texto, "Agus: vigila; si pasa de 4 GB, pídeselo a Claude.", "agustina", ms, **extra)
    return fila("base", "Base de datos de la app", "sistema", "base", "verde", "Funciona", texto, None, None, ms, **extra)


def c_copia(C, ahora_):
    t0 = time.time()
    import config
    carpeta = config.ESTADO_DIR / "copias"
    dias = sorted([d for d in carpeta.iterdir() if d.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", d.name) and any(d.iterdir())],
                  key=lambda d: d.name, reverse=True) if carpeta.exists() else []
    ms = int((time.time() - t0) * 1000)
    que = ("Agus: lanza la copia a mano (paso «copia_seguridad» de la tubería) y mira que sale «verificada»; la hace sola la tubería "
           "una vez al día: si no sale, mira el registro de ese paso (sin espacio en disco no copia).")
    if not dias:
        return fila("copia", "Copia de seguridad del día", "sistema", "doc", "rojo", "Sin copia",
                    "No hay ninguna copia de la base en esta máquina: si se rompe, se pierde el rastro y las decisiones.", que, "agustina", ms)
    ult = dias[0]
    ficheros = [f for f in ult.iterdir() if f.is_file()]
    mb = sum(_mb(f) for f in ficheros)
    hora = datetime.fromtimestamp(max(f.stat().st_mtime for f in ficheros)) if ficheros else None
    hoy = ahora_.date().isoformat()
    ayer = (ahora_.date() - timedelta(days=1)).isoformat()
    texto = f"Última copia: {ult.name[8:10]}-{ult.name[5:7]}{' a las ' + hora.strftime('%H:%M') if hora else ''} · {len(ficheros)} ficheros, {num(mb)} MB."
    extra = {"ultima_copia": ult.name}
    try:
        man = json.loads((ult / "manifiesto.json").read_text())
    except Exception:  # noqa: BLE001 · copia antigua (copia_base.py) sin manifiesto
        man = None
    if man is not None:
        filas = sum((b or {}).get("filas", 0) for b in (man.get("bases") or {}).values())
        texto += f" Verificada: {'sí' if man.get('verificada') else 'NO'} ({num(filas, 0)} filas) · rotación: 7 diarias y 4 semanales · fuera de la máquina (R2): {man.get('r2') or 'apagado'}."
        extra["verificada"] = bool(man.get("verificada"))
        if not man.get("verificada"):
            return fila("copia", "Copia de seguridad del día", "sistema", "doc", "rojo", "Copia sin verificar", texto, que, "agustina", ms, **extra)
    if ult.name == hoy or (ult.name == ayer and ahora_.hour < 4):
        return fila("copia", "Copia de seguridad del día", "sistema", "doc", "verde", "Hecha", texto, None, None, ms, **extra)
    if ult.name == ayer:
        return fila("copia", "Copia de seguridad del día", "sistema", "doc", "ambar", "Falta la de hoy", texto + " La de hoy no se ha hecho.", que, "agustina", ms, **extra)
    return fila("copia", "Copia de seguridad del día", "sistema", "doc", "rojo", "Copia vieja", texto + " Hace más de un día que no se copia la base.", que, "agustina", ms, **extra)


INTERNAS = [("app_web", c_app_web), ("tuberia", c_tuberia), ("envios", c_envios), ("sincronia_clickup", c_clickup),
            ("ia_tope", c_ia), ("disco", c_disco), ("base", c_base), ("copia", c_copia)]


def probar_internas(ids, C, ahora_, forzadas=None):
    out = []
    for i, fn in INTERNAS:
        if i not in ids:
            continue
        if forzadas and i in forzadas and forzadas[i] != "real":
            col = forzadas[i]
            out.append(fila(i, dict(INTERNAS_NOMBRE).get(i, i), "sistema", "alert", col,
                            {"rojo": "Falla (simulado)", "ambar": "Vigilar (simulado)"}.get(col, "Funciona"),
                            "simulado", "Agus: simulacro; no hay que hacer nada." if col != "verde" else None, "agustina" if col != "verde" else None, 12))
            continue
        try:
            r = fn(C, ahora_)
        except Exception as e:  # noqa: BLE001 · una comprobación que revienta es un fallo de esa fila, no del vigía
            r = fila(i, dict(INTERNAS_NOMBRE).get(i, i), "sistema", "alert", "ambar", "No se pudo comprobar",
                     sanear(f"{type(e).__name__}: {e}"), "Agus: pídeselo a Claude con este aviso.", "agustina", None)
        if r:
            out.append(r)
    return out


INTERNAS_NOMBRE = [("app_web", "La app (servidor web)"), ("tuberia", "Tubería de datos"), ("envios", "Envíos de la app (correo, WhatsApp, GHL)"),
                   ("sincronia_clickup", "Cambios hacia ClickUp"), ("ia_tope", "IA de la app frente a su tope"), ("disco", "Espacio en disco"),
                   ("base", "Base de datos de la app"), ("copia", "Copia de seguridad del día")]


# ======================================================================= historia (24 h), desde, último OK
COD = {"verde": "v", "ambar": "a", "rojo": "r", "gris": "g"}


def con_historia(r, previa, ahora_, C):
    p = previa or {}
    t = ahora_.strftime(FMT)
    r["ultima_prueba"] = t
    r["desde"] = p.get("desde") if p.get("color") == r["color"] and p.get("desde") else t
    r["ultimo_ok"] = t if r.get("ok") else p.get("ultimo_ok")
    r["fallos_seguidos"] = (p.get("fallos_seguidos", 0) + 1) if r["color"] == "rojo" else 0
    lim = minuto(ahora_ - timedelta(hours=C["historial_h"]))
    h = [x for x in (p.get("h24") or []) if isinstance(x, list) and x and x[0] >= lim]
    h.append([minuto(ahora_), COD.get(r["color"], "g"), r.get("ms")])
    r["h24"] = h[-400:]
    vistos = [x for x in h if x[1] != "g"]
    r["pct_24h"] = round(100 * sum(1 for x in vistos if x[1] != "r") / len(vistos)) if vistos else None
    return r


# ======================================================================= avisos agrupados (#avisos-altas)
def publicar(con, texto, clave, menciones, hilo_de=None, datos=None):
    """Mensaje en #avisos-altas (tabla de avisos.py), idempotente por clave. Sin la tabla, no hace nada."""
    if not tabla(con, "canal_mensajes"):
        return None
    if con.execute("SELECT 1 FROM canal_mensajes WHERE clave=?", (clave,)).fetchone():
        return None
    cur = con.execute("INSERT INTO canal_mensajes (canal_id, tipo, quien, texto, hilo_de, menciones, clave, dueno_id, ver, datos, creado) "
                      "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                      (CANAL, "evento", None, sanear(texto, 1200), hilo_de, json.dumps(list(menciones)), clave, "agustina",
                       json.dumps({"puestos": VEN}), json.dumps({"icono": "alert", "ir": "#/conexiones", **(datos or {})}, ensure_ascii=False),
                       a_utc_txt(ahora())))
    return cur.lastrowid


def _lista(rs, con_que=True):
    partes = []
    for r in rs:
        t = f"{r['nombre']} ({r['titular'].lower()})"
        if con_que and r.get("que_hacer"):
            t += f": {sin_terminal(r['que_hacer'])}"
        partes.append(t)
    return partes


def _duracion(desde, ahora_):
    try:
        m = int((ahora_ - datetime.strptime(desde, FMT)).total_seconds() // 60)
    except (TypeError, ValueError):
        return "un rato"
    return f"{m} min" if m < 90 else f"{m // 60} h {m % 60} min"


def avisos(filas, previas, ahora_, C, sin_avisos=False):
    """Máquina de episodios: entra en rojo → aviso a Agus (agrupado); rojo > escalar_min → Mili y Tomás (agrupado);
    sale de rojo → recuperación (agrupada). Devuelve lo publicado en esta vuelta."""
    if sin_avisos:
        return []
    d = vigia_dir()
    ep = leer(d / "episodios.json", {}) or {}
    sello = ahora_.strftime("%Y%m%d%H%M")
    caen, escalan, vuelven = [], [], []
    por_id = {r["id"]: r for r in filas}
    for r in filas:
        e = ep.get(r["id"])
        if r["color"] == "rojo":
            if not e:
                ep[r["id"]] = {"desde": r["desde"], "aviso": None, "escalado": False, "nombre": r["nombre"]}
                caen.append(r)
            elif not e.get("escalado") and (ahora_ - datetime.strptime(e["desde"], FMT)).total_seconds() / 60 >= C["escalar_min"]:
                escalan.append(r)
        elif e and r["color"] in ("verde", "ambar"):
            vuelven.append((r, e))
    hechos = []
    con = db()
    try:
        if caen:
            n = len(caen)
            t = (f"Ha dejado de funcionar: {_lista(caen)[0]}" if n == 1 else
                 f"Han dejado de funcionar {n} cosas: " + " · ".join(_lista(caen, con_que=False)) + ". Cada fila dice qué hacer y quién.") + \
                " Abre Salud del sistema para el detalle."
            mid = publicar(con, t, f"vigia:cae:{sello}:{'+'.join(sorted(r['id'] for r in caen))[:120]}", ["agustina"],
                           datos={"gravedad": "alta", "ids": [r["id"] for r in caen]})
            for r in caen:
                ep[r["id"]]["aviso"] = mid
            hechos.append({"tipo": "cae", "ids": [r["id"] for r in caen], "a": ["agustina"], "mensaje": mid, "texto": t})
        if escalan:
            t = ("Sigue sin funcionar desde hace más de 1 h: " if len(escalan) == 1 else f"Siguen sin funcionar desde hace más de 1 h ({len(escalan)}): ") + \
                " · ".join(f"{r['nombre']} (desde las {r['desde'][11:16]}, {_duracion(ep[r['id']]['desde'], ahora_)})" for r in escalan) + \
                ". Mili y Tomás, para que lo sepáis; Agus ya tiene el aviso."
            padre = ep[escalan[0]["id"]].get("aviso") if len(escalan) == 1 else None
            mid = publicar(con, t, f"escalado:vigia:{sello}:{'+'.join(sorted(r['id'] for r in escalan))[:120]}", ["mili", "tomas"], hilo_de=padre,
                           datos={"icono": "flag", "gravedad": "alta", "ids": [r["id"] for r in escalan]})
            for r in escalan:
                ep[r["id"]]["escalado"] = True
            hechos.append({"tipo": "escalado", "ids": [r["id"] for r in escalan], "a": ["mili", "tomas"], "mensaje": mid, "texto": t})
        if vuelven:
            t = ("Vuelve a funcionar: " if len(vuelven) == 1 else f"Vuelven a funcionar ({len(vuelven)}): ") + \
                " · ".join(f"{r['nombre']} (estuvo caída {_duracion(e['desde'], ahora_)})" for r, e in vuelven) + "."
            a = ["agustina"] + (["mili", "tomas"] if any(e.get("escalado") for _, e in vuelven) else [])
            padre = vuelven[0][1].get("aviso") if len(vuelven) == 1 else None
            mid = publicar(con, t, f"vigia:vuelve:{sello}:{'+'.join(sorted(r['id'] for r, _ in vuelven))[:120]}", a, hilo_de=padre,
                           datos={"icono": "ok", "gravedad": "baja", "ids": [r["id"] for r, _ in vuelven]})
            for r, _ in vuelven:
                ep.pop(r["id"], None)
            hechos.append({"tipo": "vuelve", "ids": [r["id"] for r, _ in vuelven], "a": a, "mensaje": mid, "texto": t})
        con.commit()
    finally:
        con.close()
    escribir(d / "episodios.json", ep)
    if hechos:
        with open(d / "avisos.jsonl", "a", encoding="utf-8") as f:
            for x in hechos:
                f.write(json.dumps({"hora": ahora_.strftime(FMT), **{k: v for k, v in x.items() if k != "mensaje"},
                                    "publicado": bool(x.get("mensaje"))}, ensure_ascii=False) + "\n")
    return hechos


def ultimos_avisos(n=12):
    f = vigia_dir() / "avisos.jsonl"
    if not f.exists():
        return []
    out = []
    for linea in f.read_text(encoding="utf-8").splitlines()[-n:]:
        try:
            x = json.loads(linea)
            out.append({"hora": x.get("hora"), "tipo": x.get("tipo"), "a": [PERSONAS.get(p, p) for p in x.get("a") or []],
                        "texto": sanear(x.get("texto"), 600)})
        except ValueError:
            continue
    return list(reversed(out))


# ======================================================================= una vuelta
def vuelta(solo=None, sin_red=False, sin_avisos=False, forzadas=None, quien="vigia"):
    C = conf()
    ahora_ = ahora()
    d = vigia_dir()
    previo = leer(d / "estado.json", {}) or {}
    previas = {r["id"]: r for r in previo.get("filas") or []}
    todos_con = ids_conexiones()
    todas_int = [i for i, _ in INTERNAS]
    if solo:
        pedir_con = [i for i in todos_con if i in solo]
        pedir_int = [i for i in todas_int if i in solo]
    else:
        pedir_con = []
        for i in todos_con:
            cada = C["cada_min_conexion"].get(i)
            p = previas.get(i)
            if cada and p and p.get("ultima_prueba") and not forzadas:
                try:
                    if (ahora_ - datetime.strptime(p["ultima_prueba"], FMT)).total_seconds() < cada * 60 - 30:
                        continue
                except ValueError:
                    pass
            pedir_con.append(i)
        pedir_int = todas_int
    t0 = time.time()
    nuevas = probar_conexiones(pedir_con, sin_red=sin_red, forzadas=forzadas, reintento_s=C["reintento_s"]) if pedir_con else []
    nuevas += probar_internas(pedir_int, C, ahora_, forzadas)
    nuevas = [con_historia(r, previas.get(r["id"]), ahora_, C) for r in nuevas]
    hechas = {r["id"] for r in nuevas}
    filas = nuevas + [p for i, p in previas.items() if i not in hechas and (i in todos_con or i in todas_int)]
    for r in filas:
        cada = C["cada_min_conexion"].get(r["id"])
        r["cada_min"] = cada or C["cada_min"]
    orden = {i: n for n, i in enumerate(todas_int + todos_con)}
    filas.sort(key=lambda r: ({"rojo": 0, "ambar": 1, "gris": 2, "verde": 3}.get(r["color"], 4), orden.get(r["id"], 99)))
    publicados = avisos(filas if not solo else nuevas, previas, ahora_, C, sin_avisos=sin_avisos or (sin_red and not forzadas))
    cuenta = {k: sum(1 for r in filas if r["color"] == k) for k in ("verde", "ambar", "rojo", "gris")}
    n = cuenta["rojo"]
    doc = {
        "generado": ahora_.strftime(FMT), "segundos": round(time.time() - t0, 1), "quien": quien,
        "solo": sorted(solo) if solo else None, "en_vivo": not sin_red and not forzadas, "simulado": bool(forzadas),
        "cada_min": C["cada_min"], "escalar_min": C["escalar_min"],
        "ultima_vuelta_completa": previo.get("ultima_vuelta_completa") if solo else ahora_.strftime(FMT),
        "resumen": {**cuenta, "total": len(filas), "fallan": n,
                    "titular": "Todo funciona" if not n else ("1 cosa falla" if n == 1 else f"{n} cosas fallan"),
                    "vigilar": cuenta["ambar"]},
        "filas": filas,
        "avisos": ultimos_avisos(),
        "avisos_esta_vuelta": [{k: v for k, v in x.items() if k in ("tipo", "ids", "a")} for x in publicados],
        "como": ("Cada 10 minutos, una lectura barata por herramienta (nada que escriba ni gaste créditos) y un repaso de la app por "
                 "dentro. La llave de GoHighLevel que rota no se usa nunca aquí: se mira su última rotación. Lo que cae a rojo avisa a Agus "
                 "en #avisos-altas; si sigue más de 1 h, a Mili y Tomás; y avisa cuando vuelve. Un aviso por cambio, nunca uno por vuelta."),
    }
    if solo:
        doc["siguiente"] = previo.get("siguiente")
    else:
        doc["siguiente"] = (ahora_ + timedelta(minutes=C["cada_min"])).strftime(FMT)
    escribir(d / "estado.json", doc)
    latido(doc)
    return doc


def latido(doc):
    url = os.environ.get("RO_VIGIA_LATIDO_URL")
    if not url or doc.get("simulado"):
        return
    try:
        urllib.request.urlopen(url + ("/fail" if doc["resumen"]["fallan"] and os.environ.get("RO_VIGIA_LATIDO_FALLO") else ""), timeout=10)
    except Exception:  # noqa: BLE001 · el latido es de ayuda: si no sale, Better Stack avisa solo
        pass


# ======================================================================= bucle local
def bucle(args):
    """Una vuelta cada «cada_min», cada una en su propio proceso (si una se cuelga o revienta, la siguiente entra igual)."""
    resto = [a for a in args if a != "--bucle"]
    print(f"Vigía en bucle · cada {conf()['cada_min']} min · Ctrl+C para parar")
    while True:
        t0 = time.time()
        try:
            r = subprocess.run([sys.executable, str(Path(__file__).resolve()), *resto], timeout=600, capture_output=True, text=True)
            print((r.stdout or r.stderr or "").strip().splitlines()[-1:] or [f"código {r.returncode}"])
        except subprocess.TimeoutExpired:
            print("La vuelta del vigía se pasó de 10 min: se corta y sigue la siguiente.")
        espera = max(30, conf()["cada_min"] * 60 - (time.time() - t0))
        time.sleep(espera)


# ======================================================================= enganche a servir.py (GET /api/vigia, POST /api/vigia/probar)
_PRUEBA = {"hilo": None, "id": None, "desde": 0}
_CANDADO_PRUEBA = threading.Lock()


def enganchar(Manejador, servir):
    """GET /api/vigia → data/vigia/estado.json a quien ve «Salud del sistema» (dirección, operaciones, técnico).
    POST /api/vigia/probar {id} → «Probar ahora» de UNA fila (probar_conexiones: Agus, Mili y Tomás; nunca en «ver como»).
    Lanza `vigia.py --solo <id>` en segundo plano (≈ 1-20 s); la pantalla vuelve a pedir el estado. Sin este fichero, nada cambia."""
    S = servir
    get_orig, post_orig = Manejador._api_get, Manejador.api_post

    def ve(persona):
        return bool(S.ve_alguno(persona, ["conexiones"]))

    def _api_get(self, ruta, q, real, persona):
        if ruta != "/api/vigia":
            return get_orig(self, ruta, q, real, persona)
        if not ve(persona):
            return self.responder(403, {"error": "La salud del sistema la ven Agus, Mili y Tomás."})
        doc = leer(vigia_dir() / "estado.json", None)
        if not doc:
            return self.responder(200, {"ok": True, "vacio": True, "texto": "El vigía aún no ha pasado en esta máquina."})
        doc = dict(doc)
        doc["probando"] = _PRUEBA["id"] if _PRUEBA["hilo"] and _PRUEBA["hilo"].is_alive() else None
        doc["puede_probar"] = real["id"] == persona["id"] and S.P.ver(persona, {"tipo": "probar_conexiones"}, S.P.contexto(persona, S.E.crudo))["ok"]
        return self.responder(200, doc)

    def api_post(self, ruta, real, persona, b):
        if ruta != "/api/vigia/probar":
            return post_orig(self, ruta, real, persona, b)
        if persona["id"] != real["id"]:
            return self.responder(403, {"error": "Estás en «ver como»: es solo lectura. No se escribe nada."})
        cp = S.P.contexto(persona, S.E.crudo)
        if not S.P.ver(persona, {"tipo": "probar_conexiones"}, cp)["ok"]:
            return self.responder(403, {"error": S.P.REGLAS["tipos"]["probar_conexiones"]["no"]})
        fid = str((b or {}).get("id") or "")
        validos = set([i for i, _ in INTERNAS])
        try:
            validos |= {r["id"] for r in (leer(vigia_dir() / "estado.json", {}) or {}).get("filas") or []}
        except Exception:  # noqa: BLE001
            pass
        if not RX_ID.match(fid) or fid not in validos:
            return self.responder(400, {"error": "Esa fila no existe en la salud del sistema."})
        with _CANDADO_PRUEBA:
            if _PRUEBA["hilo"] and _PRUEBA["hilo"].is_alive():
                return self.responder(200, {"ok": True, "nueva": False, "probando": _PRUEBA["id"],
                                            "texto": "Ya hay una prueba en marcha: espera unos segundos."})

            def correr(i=fid, quien=real["id"]):
                try:
                    subprocess.run([sys.executable, str(Path(__file__).resolve()), "--solo", i, "--quien", quien],
                                   cwd=str(APP), timeout=120, capture_output=True, text=True)
                except Exception as e:  # noqa: BLE001
                    print("Vigía: «Probar ahora» no terminó:", type(e).__name__)
            _PRUEBA.update(hilo=threading.Thread(target=correr, daemon=True), id=fid, desde=time.time())
            _PRUEBA["hilo"].start()
        S.registrar(real["id"], "conexiones", "vigia_probar", fid, {"fila": fid})
        return self.responder(200, {"ok": True, "nueva": True, "probando": fid})

    Manejador._api_get = _api_get
    Manejador.api_post = api_post


# ======================================================================= simulacro de caídas (sobre una copia)
def prueba(dejar=None):
    """Copia local.db en una carpeta temporal y pasa un día simulado: caída agrupada de 2 conexiones, nada repetido cada
    10 min, escalado a la hora, recuperación agrupada. Comprueba lo que queda en #avisos-altas de la COPIA."""
    tmp = Path(dejar or tempfile.mkdtemp(prefix="vigia_prueba_"))
    tmp.mkdir(parents=True, exist_ok=True)
    copia = tmp / "prueba.db"
    if copia.exists():
        copia.unlink()
    src, dst = sqlite3.connect(str(ruta_db())), sqlite3.connect(str(copia))
    with dst:
        src.backup(dst)
    src.close(), dst.close()
    vdir = tmp / "vigia"
    if vdir.exists():
        shutil.rmtree(vdir)
    vdir.mkdir()
    env0 = {k: os.environ.get(k) for k in ("RO_DB", "RO_VIGIA_DIR", "RO_VIGIA_AHORA", "RO_VIGIA_APP_URL")}
    os.environ.update(RO_DB=str(copia), RO_VIGIA_DIR=str(vdir), RO_VIGIA_APP_URL="")
    fallos = []

    def mensajes():
        c = sqlite3.connect(str(copia))
        try:
            return c.execute("SELECT clave, texto, menciones, hilo_de FROM canal_mensajes WHERE clave LIKE 'vigia:%' OR clave LIKE 'escalado:vigia:%' ORDER BY id").fetchall()
        finally:
            c.close()

    def paso(hora, forz, esperado, que):
        os.environ["RO_VIGIA_AHORA"] = hora
        antes = len(mensajes())
        doc = vuelta(forzadas=forz, quien="prueba")
        nuevos = mensajes()[antes:]
        tipos = [("escalado" if k.startswith("escalado:") else k.split(":")[1]) for k, *_ in nuevos]
        ok = tipos == esperado
        print(f"  {'bien ' if ok else 'FALLO'} {hora[11:]} {que:<52} → {tipos or 'sin aviso'} · semáforo: {doc['resumen']['titular']}")
        if not ok:
            fallos.append(f"{hora}: esperaba {esperado}, salió {tipos}")
        return doc, nuevos

    base = datetime.strptime(ahora().strftime("%Y-%m-%d") + " 00:00", FMT) - timedelta(hours=14)
    try:
        print(f"Simulacro del vigía sobre una COPIA de la base ({copia})")
        # 1) un día casi entero en verde (relleno del minigráfico de 24 h), con un parpadeo corto de Meta que NO llega a aviso
        #    porque se recupera dentro de la misma vuelta (el reintento a los pocos segundos lo absorbe en vivo).
        t = base
        verdes = {"*": "verde", "tuberia": "verde", "envios": "real", "sincronia_clickup": "real", "ia_tope": "real", "disco": "verde", "base": "real", "copia": "verde"}
        os.environ["RO_VIGIA_AHORA"] = t.strftime(FMT)
        while t < base + timedelta(hours=13):
            os.environ["RO_VIGIA_AHORA"] = t.strftime(FMT)
            f = dict(verdes)
            if base + timedelta(hours=3) <= t < base + timedelta(hours=3, minutes=40):
                f["zoho_desk"] = "ambar"          # lenta un rato: ámbar, sin aviso
            vuelta(forzadas=f, quien="prueba", sin_avisos=False)
            t += timedelta(minutes=10)
        n0 = len(mensajes())
        if n0:
            fallos.append(f"el relleno en verde/ámbar no debía avisar y salieron {n0} mensajes")
        print(f"  {'bien ' if not n0 else 'FALLO'} 13 h en verde (y Zoho Desk lenta 40 min, en ámbar)  → {n0 or 'sin aviso'}")
        h = lambda m: (t + timedelta(minutes=m)).strftime(FMT)   # noqa: E731
        caidas = {**verdes, "clickup": "rojo", "meta": "rojo"}
        paso(h(0), caidas, ["cae"], "caen ClickUp y Meta a la vez")
        paso(h(10), caidas, [], "siguen caídas (10 min después)")
        paso(h(20), {**caidas, "zoho_crm": "rojo"}, ["cae"], "cae también Zoho CRM (aviso propio)")
        paso(h(50), {**caidas, "zoho_crm": "rojo"}, [], "siguen las tres (50 min)")
        paso(h(60), {**caidas, "zoho_crm": "rojo"}, ["escalado"], "ClickUp y Meta pasan de 1 h → Mili y Tomás")
        paso(h(70), {**caidas, "zoho_crm": "rojo"}, [], "nada nuevo (no se repite)")
        paso(h(80), {**verdes, "meta": "rojo"}, ["vuelve"], "vuelven ClickUp y Zoho CRM (agrupado)")
        doc, _ = paso(h(90), {**verdes, "meta": "rojo"}, [], "Meta sigue (ya escalada: no se repite)")
        if doc["resumen"]["titular"] != "1 cosa falla":
            fallos.append(f"semáforo: esperaba «1 cosa falla», salió «{doc['resumen']['titular']}»")
        paso(h(100), verdes, ["vuelve"], "vuelve Meta")
        M = mensajes()
        menc = {k.split(":")[1] if not k.startswith("escalado:") else "escalado": json.loads(m) for k, _t, m, _h in M}
        if menc.get("cae") != ["agustina"]:
            fallos.append(f"el aviso de caída debía ir a Agus: {menc.get('cae')}")
        if menc.get("escalado") != ["mili", "tomas"]:
            fallos.append(f"el escalado debía ir a Mili y Tomás: {menc.get('escalado')}")
        if sorted(menc.get("vuelve") or []) != ["agustina", "mili", "tomas"]:
            fallos.append(f"la vuelta de algo escalado debía ir a Agus, Mili y Tomás: {menc.get('vuelve')}")
        doc = leer(vdir / "estado.json", {})
        h24 = next((r["h24"] for r in doc["filas"] if r["id"] == "meta"), [])
        if len(h24) < 80:
            fallos.append(f"el histórico de 24 h de Meta tiene {len(h24)} puntos")
        print(f"  {'bien ' if len(h24) >= 80 else 'FALLO'} histórico de 24 h de Meta: {len(h24)} pruebas · {len(M)} avisos en #avisos-altas de la copia")
        # Modular sin clave: fila propia con el texto exacto
        mod = next((r for r in doc["filas"] if r["id"] == "modular"), None)
        print(f"  {'bien ' if mod else 'FALLO'} fila de Modular DS presente")
    finally:
        for k, v in env0.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        if not dejar:
            shutil.rmtree(tmp, ignore_errors=True)
    print("Simulacro: " + ("TODO BIEN" if not fallos else "FALLOS:\n  - " + "\n  - ".join(fallos)))
    return 0 if not fallos else 1


# ======================================================================= main
def main():
    args = sys.argv[1:]
    for p in (str(APP), str(AQUI)):
        if p not in sys.path:
            sys.path.append(p)
    if "--prueba" in args:
        return prueba(args[args.index("--dejar") + 1] if "--dejar" in args else None)
    if "--bucle" in args:
        try:
            bucle(args)
        except KeyboardInterrupt:
            return 0
    solo = {x.strip() for x in (args[args.index("--solo") + 1] if "--solo" in args else "").split(",") if x.strip()} or None
    if solo and not all(RX_ID.match(x) for x in solo):
        sys.exit("--solo: ids de fila en minúsculas")
    forzadas = None
    if "--simular" in args:
        forzadas = json.loads(args[args.index("--simular") + 1])
    quien = args[args.index("--quien") + 1] if "--quien" in args else "vigia"
    try:
        with candado(espera_s=60 if solo else 0):
            doc = vuelta(solo=solo, sin_red="--sin-red" in args, sin_avisos="--sin-avisos" in args, forzadas=forzadas, quien=re.sub(r"[^\w]", "", quien)[:30])
    except Ocupado:
        print("Ya hay otra vuelta del vigía en marcha: esta no hace nada.")
        return 75
    r = doc["resumen"]
    print(f"Vigía · {doc['generado']} · {r['titular']} · {r['verde']} verdes · {r['ambar']} ámbar · {r['rojo']} rojas · {doc['segundos']} s"
          + (f" · avisos: {', '.join(x['tipo'] for x in doc['avisos_esta_vuelta'])}" if doc["avisos_esta_vuelta"] else ""))
    for f in doc["filas"]:
        if f["color"] in ("rojo", "ambar") and (not solo or f["id"] in solo):
            print(f"  {f['color']:<5} {f['id']:<18} {sanear(f.get('titular'))} · {sanear(f.get('detalle'))[:100]}")
    if "--json" in args:
        print(json.dumps(r, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
