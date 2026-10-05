#!/usr/bin/env python3
"""
servir.py · servidor local de la app de RO (E0). Python estándar, SOLO en 127.0.0.1.

Hace en el Mac lo mismo que hará el Worker de Cloudflare con W1:
  1. Sabe quién eres  → cabecera Cf-Access-Authenticated-User-Email (como Cloudflare Access) o, en el
                         prototipo, ?yo=<id> / cabecera X-RO-Yo. Sin nada: Tomás (solo prototipo).
  2. «Ver como»        → ?como=<id> / X-RO-Como, solo si reglas_permisos.json lo permite (Mili y Tomás);
                         solo lectura y queda en el rastro.
  3. Manda tu trozo    → recorta con permisos.py (las mismas reglas que permisos.js) y nunca sirve data/ en bruto.
  4. 403 si pides un cliente ajeno, sin ningún dato en la respuesta.
  5. Rastro imborrable, acciones simuladas, Ajustes y «ver datos» de leads en local.db (schema_v2.sql).
  6. Puerta de secretos: no sirve un fichero en el que el escáner encuentre algo.
  7. Foto diaria en historia/ al arrancar (si hoy aún no hay).

Uso:
  python3 servir.py                      # http://127.0.0.1:8770
  python3 servir.py --puerto 8771
  python3 servir.py --bind 127.0.0.1     # (solo vale 127.0.0.1 / localhost sin RO_MODO=servidor)
  python3 servir.py --importar-rastro <carpeta>   # importa el volcado de ArtifactData (solo lectura del artefacto)
  python3 servir.py --verificar-rastro   # ¿la cadena del rastro está entera? (sale con 0 o 1)
  python3 servir.py --ancla-diaria [AAAA-MM-DD]   # huella del día fuera de la base
  python3 servir.py --anotar-corte <fila> <motivo> · --anotar-incidencia <tipo> <desde> <hasta> <motivo>
  python3 servir.py --help               # esta ayuda (no arranca nada ni toca la base)
  RO_DB=<copia.db> python3 servir.py …   # pruebas sin tocar el rastro real

Velocidad (ronda 14, auditoría 37): el código va con su huella en la dirección (?v=…) y caché de un año; index.html
lleva el mapa de versiones y pide la sesión a la vez que el código; /api/modulo/* guarda en memoria lo ya recortado y
comprimido por persona real + vista + versión de los datos, con ETag (304 si no ha cambiado); logos en /logos/<id>.jpg.

Nada de esto escribe en ninguna herramienta externa.
"""
import json
import mimetypes
import os
import re
import sqlite3
import subprocess
import time
import sys
import threading
import traceback
from datetime import date, datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
ThreadingHTTPServer.request_queue_size = 64  # la app carga ~30 módulos a la vez (aviso de M14)
ThreadingHTTPServer.daemon_threads = True
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import permisos as P                      # noqa: E402
import escaner_secretos as ESC            # noqa: E402
import foto_diaria as FOTO                # noqa: E402
from build_data import aplicar_respuestas  # noqa: E402
sys.path.insert(1, str(AQUI / "despliegue"))
import acceso_cf as ACCESO                # noqa: E402  (C5: en modo servidor solo vale el sello firmado de Cloudflare Access)
from fuentes_verdad import clientes_activos as ACT   # noqa: E402  (Tomás 3-oct: un solo filtro «cliente activo»; bajas fuera de pantallas de trabajo)

DATA = AQUI / "data"
DB = Path(os.environ.get("RO_DB") or AQUI / "local.db")   # RO_DB=<ruta> para pruebas sin tocar el rastro real
ESQUEMA = AQUI / "schema_v2.sql"
NUCLEO = ["personas", "asignaciones", "clientes", "alarmas", "logos", "meta"]
CANDADO = threading.Lock()

# Lo único que se sirve como fichero: la carcasa, el código y las reglas (que no son secretas).
# Ronda 14: fuentes propias (fuentes_web/), sin Google. El mapa de versiones de index.html va con su huella sha256.
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
       "font-src 'self'; img-src 'self' data: https:; connect-src 'self'; object-src 'none'; "
       "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
ESTATICOS_PERMITIDOS = re.compile(r"^(index\.html|[\w\-]+\.(js|css)|reglas_permisos\.json|modulos/[\w\-/]+\.(js|css|svg|png)|fuentes_web/[\w\-]+\.woff2)$")
from estaticos_seguro_234 import ruta_estatica, leer_estatico
import panel_direccion_privado_249 as PANEL_PRIVADO_249
import planes_fuegos_255 as PLANES_FUEGOS_255


# ===================================================================== ronda 14 · velocidad (auditoría 37)
# Causa 2: huella de cada fichero propio → «nombre?v=<huella>» con caché de un año (immutable); index.html sin caché.
# Causa 7: index.html con el mapa de versiones (import map), modulepreload y la sesión pedida a la vez que el código.
# Causa 8: /api/modulo/* recortado + comprimido en memoria por (persona real, persona vista, fichero, versión de datos),
#          con ETag. Nunca se comparte entre personas: la clave y la huella llevan las dos personas.
import hashlib                            # noqa: E402
import base64                             # noqa: E402
from collections import OrderedDict       # noqa: E402
try:
    import brotli as _BROTLI              # opcional: si no está, gzip
except Exception:
    _BROTLI = None
INMUTABLE = "private, max-age=31536000, immutable"
_SERVIDOS = {}
_CANDADO_SERVIDOS = threading.Lock()


def _estado_fichero(p):
    st = p.stat()
    return (st.st_dev, st.st_ino, st.st_ctime_ns, st.st_mtime_ns, st.st_size)


def contenido_servido(rel):
    """(bytes tal y como se sirven, huella de 12). estilos.css lleva las fuentes con su versión. Memoria por identidad y versión de cada archivo."""
    p = ruta_estatica(AQUI, rel)
    datos, estado_seguro = leer_estatico(AQUI, rel)
    marca = [estado_seguro]
    fuentes = sorted((AQUI / "fuentes_web").glob("*.woff2")) if rel == "estilos.css" else []
    lecturas_fuentes = [(f, leer_estatico(AQUI, f.relative_to(AQUI).as_posix())) for f in fuentes]
    marca += [lectura[1] for _, lectura in lecturas_fuentes]
    marca = tuple(marca)
    with _CANDADO_SERVIDOS:
        previo = _SERVIDOS.get(rel)
    if previo and previo[0] == marca:
        return previo[1], previo[2]
    if fuentes:
        texto = datos.decode()
        for f, (contenido_fuente, _) in lecturas_fuentes:
            r = f"fuentes_web/{f.name}"
            version_fuente = hashlib.sha1(contenido_fuente).hexdigest()[:12]
            texto = texto.replace(f'url("{r}")', f'url("{r}?v={version_fuente}")')
        datos = texto.encode()
    huella = hashlib.sha1(datos).hexdigest()[:12]
    with _CANDADO_SERVIDOS:
        _SERVIDOS[rel] = (marca, datos, huella)
    return datos, huella


def ficheros_codigo():
    """Lo que entra en el mapa de versiones: el código (raíz y modulos/) y las reglas (import JSON de permisos.js)."""
    rels = [f.name for f in sorted(AQUI.glob("*.js"))]
    rels += [f.relative_to(AQUI).as_posix() for f in sorted((AQUI / "modulos").rglob("*.js"))]
    rels.append("reglas_permisos.json")
    permitidos = []
    for r in rels:
        if not ESTATICOS_PERMITIDOS.fullmatch(r):
            continue
        try:
            ruta_estatica(AQUI, r)
            permitidos.append(r)
        except (OSError, ValueError):
            continue
    return permitidos


def mapa_versiones():
    """(texto del import map, huella sha256 para la CSP)."""
    imports = {f"./{r}": f"./{r}?v={contenido_servido(r)[1]}" for r in ficheros_codigo()}
    texto = json.dumps({"imports": imports}, separators=(",", ":"))
    return texto, base64.b64encode(hashlib.sha256(texto.encode()).digest()).decode()


def comprimir(cuerpo, codificacion):
    if codificacion == "br" and _BROTLI:
        return _BROTLI.compress(cuerpo, quality=5)
    if codificacion == "gzip":
        import gzip
        return gzip.compress(cuerpo, compresslevel=6)
    return cuerpo


class CacheRespuestas:
    """Memoria de respuestas ya recortadas (y comprimidas al pedirlas), con tope de tamaño: se tira lo más antiguo."""

    def __init__(self, tope=200 * 1024 * 1024):
        self.tope, self.bytes, self.d = tope, 0, OrderedDict()
        self.candado = threading.Lock()
        self.aciertos = self.fallos = 0

    def leer(self, clave):
        with self.candado:
            e = self.d.get(clave)
            if e:
                self.d.move_to_end(clave)
                self.aciertos += 1
            else:
                self.fallos += 1
            return e

    def guardar(self, clave, e):
        with self.candado:
            if clave in self.d:
                self.bytes -= self.d[clave]["tam"]
            e["tam"] = len(e["cuerpo"])
            self.d[clave] = e
            self.bytes += e["tam"]
            while self.bytes > self.tope and self.d:
                _, viejo = self.d.popitem(last=False)
                self.bytes -= viejo["tam"]

    def comprimido(self, e, codificacion):
        with self.candado:
            if codificacion in e:
                return e[codificacion]
        z = comprimir(e["cuerpo"], codificacion)
        with self.candado:
            e[codificacion] = z
            e["tam"] += len(z)
            self.bytes += len(z)
        return z

    def vaciar(self):
        with self.candado:
            self.d.clear()
            self.bytes = 0


CACHE_RESP = CacheRespuestas()


def version_datos():
    """Todo lo que cambia un recorte además del fichero: base (Ajustes), reglas, índice de módulos y el día (suplencias)."""
    return (getattr(E, "version", 0), _MARCAS.get("reglas"), _MARCAS.get("modulos"), hoy(), ACT._CACHE.get("marca"))   # + lista de bajas


def etag_de(clave, cuerpo):
    return '"' + hashlib.sha1(repr(clave).encode() + b"|" + cuerpo).hexdigest()[:24] + '"'


def responder_de_memoria(h, e):
    """Con el manejador HTTP, la respuesta guardada (ETag/304). Con otro «manejador» (la captura de ia.py, que lee datos
    por la misma puerta), el objeto: siempre uno nuevo, nunca el de la memoria."""
    if hasattr(h, "responder_guardado"):
        return h.responder_guardado(e)
    return h.responder(200, json.loads(e["cuerpo"]))


def logo_de(cid):
    """(bytes, tipo, huella) del logo del cliente (data URI de data/logos.json) o None. Solo imágenes de mapa de bits."""
    uri = ((getattr(E, "crudo", None) or {}).get("logos") or {}).get(cid)
    m = re.match(r"data:(image/(?:jpeg|png|webp|gif));base64,(.+)$", uri or "", re.S)
    if not m:
        return None
    marca_logo = hashlib.sha256(uri.encode()).hexdigest()
    with _CANDADO_SERVIDOS:
        previo = _SERVIDOS.get(("logo", cid))
    if previo and previo[0] == marca_logo:
        return previo[1]
    datos = base64.b64decode(m.group(2))
    r = (datos, m.group(1), hashlib.sha1(datos).hexdigest()[:12])
    with _CANDADO_SERVIDOS:
        _SERVIDOS[("logo", cid)] = (marca_logo, r)
    return r


EXT_LOGO = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}


def logos_a_direcciones(datos):
    """En la sesión, el logo de cada cliente es la dirección del fichero (con versión) en lugar del base64 (−124 KB)."""
    out = []
    for c in datos.get("clientes") or []:
        lg = logo_de(c.get("id")) if isinstance(c, dict) and c.get("logo") else None
        out.append({**c, "logo": f"logos/{c['id']}.{EXT_LOGO[lg[1]]}?v={lg[2]}"} if lg else c)
    return {**datos, "clientes": out}


def ahora():
    return datetime.now().isoformat(timespec="seconds")


def hoy():
    """R16 (N6): la FECHA de negocio, siempre en hora de Madrid (igual en el Mac que en Render, que va en UTC). Las horas
    de la base (datetime('now')) siguen en UTC; quien compare una fecha de negocio con la base usa esta, nunca date('now')."""
    return P.hoy_iso()


# R16 (N1, N10): lo que escribe una persona en un texto libre (opiniones, canales): contraseñas tapadas, sin correos, sin
# teléfonos ni claves en enlaces (fuentes_chat_equipo/tapado.py) y, además, «la contraseña de … es X» sin dos puntos.
sys.path.insert(2, str(AQUI / "fuentes_chat_equipo"))
try:
    import tapado as TAPADO               # noqa: E402
except ImportError:                       # una copia de la app sin fuentes_*/ (pruebas): lo mínimo, igual de estricto
    class TAPADO:                         # noqa: N801
        TAPADA = "•••• (tapada)"
        _CRED = re.compile(r"(?i)\b(usuari[oa]s?|user(?:name)?|login|contrase(?:ñ|n)as?|password|passw(?:or)?d|pass|clave|pwd|pin)(\s*[:=]\s*)([^\s|*`\"'<>]+)")

        @staticmethod
        def limpiar(t, largo=2000):
            t = str(t or "").replace("\r\n", "\n").strip()
            t = re.sub(r"(?i)([?&])(pwd|token|key|password|secret|access_token)=[^&\s)\]]+", r"\1\2=…", t)
            t = TAPADO._CRED.sub(lambda m: m.group(1) + m.group(2) + TAPADO.TAPADA, t)
            t = re.sub(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", "[correo]", t)
            t = re.sub(r"(?<![\w/])(?:\+34[\s.-]?|0034[\s.-]?)?[6789]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}(?![\w/])", "[teléfono]", t)
            t = re.sub(r"(?<![\w/])\+\d[\d\s.-]{8,16}\d(?![\w/])", "[teléfono]", t)
            return t[:largo]
# V3a: manda la expresión de fuentes_chat_equipo/tapado.py (una sola vara para canales, espejo de ClickUp y «Algo va mal»);
# la de aquí queda solo de respaldo, para una copia de la app sin fuentes_*/ o con un tapado.py antiguo.
_RX_CLAVE_ES_RESPALDO = re.compile(r"(?i)\b(contrase(?:ñ|n)as?|password|passw(?:or)?d|clave|pass|pwd|pin|c[oó]digo de acceso)\b"
                                   r"([^.\n]{0,50}?\b(?:es|era|será|sería|son|queda|nueva)\s+)(?!••••)([^\s,;)]+)")
RX_CLAVE_ES = getattr(TAPADO, "RX_CLAVE_ES", None) or _RX_CLAVE_ES_RESPALDO


def _parece_clave_respaldo(x):
    return bool(re.search(r"\d|[!@#$%&*_+=?¿¡]", x)) or (len(x) >= 8 and x != x.lower() and x != x.upper())


_parece_clave = getattr(TAPADO, "parece_clave", None) or _parece_clave_respaldo


def limpiar_texto(t, largo=2000):
    t = TAPADO.limpiar(t, largo * 2)
    t = RX_CLAVE_ES.sub(lambda m: m.group(1) + m.group(2) + (TAPADO.TAPADA if _parece_clave(m.group(3)) else m.group(3)), t)
    return t[:largo]


# =============================================================== base local
def conectar():
    if os.environ.get("DATABASE_URL"):    # C5 · Render: la misma interfaz sobre Postgres (despliegue/base.py)
        import base as BASE_PG
        return BASE_PG.conectar()
    con = sqlite3.connect(DB, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA recursive_triggers = ON")  # 569: DELETE interno de REPLACE también dispara la protección.
    return con


def iniciar_base():
    with conectar() as con:
        con.executescript(ESQUEMA.read_text())
        # Ronda 4: columnas nuevas de «decisiones» en bases ya creadas (CREATE IF NOT EXISTS no las añade).
        cols = {r[1] for r in con.execute("PRAGMA table_info(decisiones)")}
        for col in ("titulo", "cliente_id", "datos"):
            if col not in cols:
                con.execute(f"ALTER TABLE decisiones ADD COLUMN {col} TEXT")
        # Ronda 6 (M3): huella encadenada del rastro y disparadores en decisiones y acciones.
        cols = {r[1] for r in con.execute("PRAGMA table_info(registro)")}
        if "huella_previa" not in cols:
            con.execute("ALTER TABLE registro ADD COLUMN huella_previa TEXT")
        con.executescript(SEGURIDAD_SQL)
        # 569: sólo SQLite; el traductor PG no soporta estos INSERT condicionales.
        if isinstance(con, sqlite3.Connection):
            con.executescript(SEGURIDAD_INSERT_SQLITE_569)
        con.executescript(R15_SQL)
        PLANES_FUEGOS_255.iniciar(con)


_CANDADO_RASTRO = threading.Lock()


def _huella(previa, campos):
    import hashlib
    return hashlib.sha256((previa or "").encode() + json.dumps(campos, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


# R15 (facilidad de uso): «Mis clientes» fijados por persona (preferencias) y «Algo va mal / Tengo una idea» (opiniones).
# Las opiniones no se borran ni se cambian salvo su estado (visto/resuelto por Mili o Tomás); todo queda además en el rastro.
R15_SQL = """
CREATE TABLE IF NOT EXISTS preferencias (persona TEXT NOT NULL, clave TEXT NOT NULL, valor TEXT NOT NULL,
  cambiado TEXT NOT NULL DEFAULT (datetime('now')), PRIMARY KEY (persona, clave));
CREATE TABLE IF NOT EXISTS opiniones (
  id INTEGER PRIMARY KEY AUTOINCREMENT, creada TEXT NOT NULL DEFAULT (datetime('now')), quien TEXT NOT NULL,
  tipo TEXT NOT NULL CHECK (tipo IN ('fallo','idea')), prioridad TEXT NOT NULL DEFAULT 'gris' CHECK (prioridad IN ('rojo','ambar','gris')),
  texto TEXT NOT NULL, esperaba TEXT, ruta TEXT, pantalla TEXT, ancho INTEGER, alto INTEGER, frescura TEXT, captura TEXT,
  estado TEXT NOT NULL DEFAULT 'nueva' CHECK (estado IN ('nueva','vista','resuelta')), estado_por TEXT, estado_hora TEXT);
CREATE TRIGGER IF NOT EXISTS opiniones_sin_delete BEFORE DELETE ON opiniones BEGIN SELECT RAISE(ABORT, 'Las opiniones no se borran'); END;
CREATE TRIGGER IF NOT EXISTS opiniones_solo_estado BEFORE UPDATE ON opiniones
  WHEN NEW.quien IS NOT OLD.quien OR NEW.texto IS NOT OLD.texto OR NEW.creada IS NOT OLD.creada OR NEW.tipo IS NOT OLD.tipo OR NEW.captura IS NOT OLD.captura
  BEGIN SELECT RAISE(ABORT, 'De una opinión solo cambia el estado'); END;
"""

SEGURIDAD_SQL = """
CREATE TABLE IF NOT EXISTS registro_huellas (id INTEGER PRIMARY KEY, huella TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS rastro_cortes (id INTEGER PRIMARY KEY, motivo TEXT NOT NULL, anotado TEXT NOT NULL DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS rastro_incidencias (n INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT NOT NULL CHECK (tipo IN ('corte','sin_huella','nota')),
  desde INTEGER NOT NULL, hasta INTEGER NOT NULL, motivo TEXT NOT NULL, anotado TEXT NOT NULL DEFAULT (datetime('now')));
CREATE TRIGGER IF NOT EXISTS incidencias_sin_update BEFORE UPDATE ON rastro_incidencias BEGIN SELECT RAISE(ABORT, 'Una incidencia del rastro no se cambia'); END;
CREATE TRIGGER IF NOT EXISTS incidencias_sin_delete BEFORE DELETE ON rastro_incidencias BEGIN SELECT RAISE(ABORT, 'Una incidencia del rastro no se borra'); END;
CREATE TRIGGER IF NOT EXISTS cortes_sin_update BEFORE UPDATE ON rastro_cortes BEGIN SELECT RAISE(ABORT, 'Un corte anotado no se cambia'); END;
CREATE TRIGGER IF NOT EXISTS cortes_sin_delete BEFORE DELETE ON rastro_cortes BEGIN SELECT RAISE(ABORT, 'Un corte anotado no se borra'); END;
CREATE TRIGGER IF NOT EXISTS huellas_sin_update BEFORE UPDATE ON registro_huellas BEGIN SELECT RAISE(ABORT, 'La huella del rastro no se modifica'); END;
CREATE TRIGGER IF NOT EXISTS huellas_sin_delete BEFORE DELETE ON registro_huellas BEGIN SELECT RAISE(ABORT, 'La huella del rastro no se borra'); END;
CREATE TRIGGER IF NOT EXISTS decisiones_sin_delete BEFORE DELETE ON decisiones BEGIN SELECT RAISE(ABORT, 'Las decisiones no se borran'); END;
CREATE TRIGGER IF NOT EXISTS decisiones_una_respuesta BEFORE UPDATE ON decisiones
  WHEN OLD.respondida IS NOT NULL OR NEW.quien IS NOT OLD.quien OR NEW.tipo IS NOT OLD.tipo OR NEW.problema IS NOT OLD.problema
    OR NEW.recomendacion IS NOT OLD.recomendacion OR NEW.titulo IS NOT OLD.titulo OR NEW.creada IS NOT OLD.creada
  BEGIN SELECT RAISE(ABORT, 'Una decisión solo se contesta una vez y no se reescribe'); END;
CREATE TRIGGER IF NOT EXISTS acciones_solo_estado BEFORE UPDATE ON acciones
  WHEN NEW.quien IS NOT OLD.quien OR NEW.herramienta IS NOT OLD.herramienta OR NEW.tipo IS NOT OLD.tipo OR NEW.objeto IS NOT OLD.objeto
    OR NEW.cliente_id IS NOT OLD.cliente_id OR NEW.texto IS NOT OLD.texto OR NEW.vista_previa IS NOT OLD.vista_previa OR NEW.creada IS NOT OLD.creada
  BEGIN SELECT RAISE(ABORT, 'De una acción solo puede avanzar el estado'); END;
"""


# 569: append-only SQLite incluso con una conexión externa recursive_triggers=OFF.
# NEW.id=-1 provisional de autoincremento no debe bloquear un INSERT normal.
# PostgreSQL pendiente: no enviar este DDL al traductor heredado.
SEGURIDAD_INSERT_SQLITE_569 = """
CREATE TRIGGER IF NOT EXISTS registro_sin_reinsertar_569 BEFORE INSERT ON registro
WHEN NEW.id > 0 AND NEW.id <= (SELECT MAX(id) FROM registro)
BEGIN SELECT RAISE(ABORT, 'El rastro no reutiliza IDs: crea una anulación'); END;
CREATE TRIGGER IF NOT EXISTS huellas_sin_reinsertar_569 BEFORE INSERT ON registro_huellas
WHEN NEW.id > 0 AND NEW.id <= (SELECT MAX(id) FROM registro_huellas)
BEGIN SELECT RAISE(ABORT, 'La huella del rastro no reutiliza IDs'); END;
"""


def registrar(quien, coleccion, accion, clave=None, datos=None, motivo=None, como=None, anula_a=None, origen="app"):
    """Rastro imborrable y ENCADENADO (ronda 6, M3): cada fila guarda la huella SHA-256 de la anterior más la suya.
    Si alguien cambia o borra una fila (saltándose los disparadores), /api/rastro/verificar lo detecta.
    Ronda 11 (auditoría 34, M-07): «unable to open database file» / «database is locked» con dos navegadores a la vez →
    se reintenta con espera (hasta ~3 s) antes de fallar."""
    for intento in range(6):
        try:
            return _registrar(quien, coleccion, accion, clave, datos, motivo, como, anula_a, origen)
        except sqlite3.OperationalError as e:
            if intento == 5 or not any(x in str(e) for x in ("unable to open", "locked", "busy")):
                raise
            time.sleep(0.1 * (2 ** intento))


def _registrar(quien, coleccion, accion, clave=None, datos=None, motivo=None, como=None, anula_a=None, origen="app"):
    texto = json.dumps(datos, ensure_ascii=False) if datos is not None else None
    with _CANDADO_RASTRO, conectar() as con:
        # Ronda 8: bloqueo de escritura ENTRE PROCESOS (varios servir.py comparten local.db): sin él, dos servidores
        # leían la misma huella previa y la cadena se partía (fila 1262, 15:25:34).
        con.isolation_level = None
        con.execute("BEGIN IMMEDIATE")
        previa = (con.execute("SELECT huella FROM registro_huellas ORDER BY id DESC LIMIT 1").fetchone() or [None])[0]
        cur = con.execute(
            "INSERT INTO registro (quien, como, coleccion, accion, clave, datos, motivo, anula_a, origen, huella_previa) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (quien, como, coleccion, accion, clave, texto, motivo, anula_a, origen, previa))
        rid = cur.lastrowid
        creada = con.execute("SELECT creada FROM registro WHERE id=?", (rid,)).fetchone()[0]
        h = _huella(previa, [rid, creada, quien, como, coleccion, accion, clave, texto, motivo, anula_a, origen])
        con.execute("INSERT INTO registro_huellas (id, huella) VALUES (?, ?)", (rid, h))
        con.execute("COMMIT")
        return rid


# Ronda 11 (M7): el rastro no se inunda. Los denegados (y las lecturas que se repiten) dejan UNA fila por persona, ruta y
# minuto; y como mucho TOPE_RASTRO_MINUTO filas de este tipo por persona y minuto (al pasarlo, una sola fila
# «rastro_limitado» ese minuto). Las filas sensibles (ver_dato, cambios, acciones) nunca se agrupan ni se limitan.
TOPE_RASTRO_MINUTO = int(os.environ.get("RO_TOPE_RASTRO_MINUTO") or 30)
_AGRUPADOS, _POR_MINUTO = {}, {}
_CANDADO_AGRUPADO = threading.Lock()


def registrar_agrupado(quien, coleccion, accion, clave=None, datos=None, motivo=None, como=None):
    minuto = datetime.now().strftime("%Y-%m-%d %H:%M")
    k = (quien, como, coleccion, accion, clave, minuto)
    with _CANDADO_AGRUPADO:
        if len(_AGRUPADOS) > 20000:
            _AGRUPADOS.clear()
            _POR_MINUTO.clear()
        if k in _AGRUPADOS:
            _AGRUPADOS[k] += 1
            return None
        n = _POR_MINUTO.get((quien, minuto), 0)
        _POR_MINUTO[(quien, minuto)] = n + 1
        if n > TOPE_RASTRO_MINUTO:
            return None
        _AGRUPADOS[k] = 1
    if n == TOPE_RASTRO_MINUTO:
        return registrar(quien, "rastro", "rastro_limitado", minuto, {"detalle": f"Más de {TOPE_RASTRO_MINUTO} denegados o lecturas en un minuto: el resto de ese minuto no deja fila."}, como=como)
    datos = dict(datos or {}, agrupado="una fila por persona, ruta y minuto")
    return registrar(quien, coleccion, accion, clave, datos, motivo, como=como)


def tope_rastro_navegador(quien):
    """Ronda 11 (M7): el navegador escribe como mucho TOPE_RASTRO_MINUTO * 2 filas por persona y minuto en /api/rastro."""
    minuto = datetime.now().strftime("%Y-%m-%d %H:%M")
    with _CANDADO_AGRUPADO:
        n = _POR_MINUTO.get((quien, "nav", minuto), 0)
        _POR_MINUTO[(quien, "nav", minuto)] = n + 1
    return n < TOPE_RASTRO_MINUTO * 2


def cortes_anotados(con):
    """Filas donde la cadena se reancla con su motivo: rastro_cortes (ronda 8) + rastro_incidencias de tipo «corte» (ronda 11)."""
    cortes = {r["id"] for r in con.execute("SELECT id FROM rastro_cortes")}
    try:
        for r in con.execute("SELECT desde, hasta FROM rastro_incidencias WHERE tipo='corte'"):
            cortes.update(range(r["desde"], r["hasta"] + 1))
    except Exception:
        pass
    return cortes


def fila_tras_anotacion():
    """Ronda 11 (A7): primera fila DESPUÉS de la última incidencia anotada. Desde ahí la cadena tiene que estar entera sin
    ninguna excepción (verificar_rastro(fila_tras_anotacion()))."""
    with conectar() as con:
        try:
            ult = con.execute("SELECT max(hasta) FROM rastro_incidencias").fetchone()[0]
        except Exception:
            ult = None
        ult = max(ult or 0, con.execute("SELECT coalesce(max(id), 0) FROM rastro_cortes").fetchone()[0] or 0)
    return ult + 1 if ult else None


def verificar_rastro(desde=None):
    """Recorre la cadena: devuelve (ok, primera fila rota o None, filas comprobadas). «desde» = empezar en esa fila
    (ancla en su huella previa); sirve para comprobar solo lo escrito por un proceso concreto. «desde="anotado"» =
    empezar justo después de la última incidencia anotada (ronda 11)."""
    if desde == "anotado":
        desde = fila_tras_anotacion()
    with conectar() as con:
        filas = con.execute("SELECT r.*, h.huella AS huella_guardada FROM registro r JOIN registro_huellas h ON h.id = r.id WHERE r.id >= ? ORDER BY r.id", (int(desde or 0),)).fetchall()
    with conectar() as con:
        cortes = cortes_anotados(con)
    previa = filas[0]["huella_previa"] if (desde and filas) else None
    for r in filas:
        if (r["huella_previa"] or None) != previa and r["id"] not in cortes:
            return False, r["id"], len(filas)
        previa = r["huella_previa"] if r["id"] in cortes and (r["huella_previa"] or None) != previa else previa
        h = _huella(previa, [r["id"], r["creada"], r["quien"], r["como"], r["coleccion"], r["accion"], r["clave"], r["datos"], r["motivo"], r["anula_a"], r["origen"]])
        if h != r["huella_guardada"]:
            return False, r["id"], len(filas)
        previa = h
    return True, None, len(filas)


# ------------------------------------------------ ancla diaria del rastro (ronda 11, A7)
ANCLAS = Path(os.environ.get("RO_ANCLAS") or AQUI / "despliegue" / "estado" / "anclas_rastro.jsonl")


def _sha_huellas(filas):
    import hashlib
    return hashlib.sha256("".join(f["huella"] for f in filas).encode()).hexdigest()


def _limites_dia_utc(dia):
    """El día de Madrid «dia» en horas UTC de la base: [desde, hasta)."""
    from datetime import timedelta, timezone
    d0 = datetime.fromisoformat(dia).replace(tzinfo=P.MADRID)
    d1 = (d0 + timedelta(days=1)).replace(tzinfo=P.MADRID)
    f = lambda d: d.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    return f(d0), f(d1)


def ultima_ancla():
    if not ANCLAS.exists():
        return None
    ult = None
    for linea in ANCLAS.read_text().splitlines():
        try:
            a = json.loads(linea)
        except ValueError:
            continue
        if a.get("ultima"):
            ult = a if not ult or a["ultima"] >= ult["ultima"] else ult
    return ult


def ancla_del_dia(dia=None):
    """R16 (N6): el ancla cubre un RANGO DE IDS del rastro, sin depender de la zona horaria: desde la fila siguiente a la
    última anclada hasta la última fila de ahora (sin ancla previa, desde la primera). «dia» = día de Madrid, solo de
    etiqueta. Con un día pedido a mano (--ancla-diaria AAAA-MM-DD), las filas de ese día DE MADRID (pasado a UTC, que es
    la hora de la base). Guardada FUERA de la base, quien recalcule la cadena entera no la cuadra."""
    with conectar() as con:
        if dia:
            d0, d1 = _limites_dia_utc(dia)
            filas = con.execute("SELECT r.id, h.huella FROM registro r JOIN registro_huellas h ON h.id = r.id "
                                "WHERE r.creada >= ? AND r.creada < ? ORDER BY r.id", (d0, d1)).fetchall()
            desde = filas[0]["id"] if filas else None
        else:
            prev = ultima_ancla()
            desde = (prev["ultima"] + 1) if prev else 1
            filas = con.execute("SELECT r.id, h.huella FROM registro r JOIN registro_huellas h ON h.id = r.id "
                                "WHERE r.id >= ? ORDER BY r.id", (desde,)).fetchall()
    return {"dia": dia or hoy(), "modo": "dia_madrid" if dia else "ids", "desde": filas[0]["id"] if filas else desde,
            "filas": len(filas), "primera": filas[0]["id"] if filas else None, "ultima": filas[-1]["id"] if filas else None,
            "ultima_huella": filas[-1]["huella"] if filas else None, "sha_dia": _sha_huellas(filas)}


def escribir_ancla(dia=None):
    """Añade (nunca reescribe) el ancla al fichero de anclas (y a RO_ANCLAS_COPIA, si está: otro disco o un volumen de
    fuera; publicarla fuera del Mac es el paso de Render/R2). Devuelve el ancla."""
    a = {**ancla_del_dia(dia), "hecha": ahora(), "zona": "Europe/Madrid"}
    for ruta in [ANCLAS] + ([Path(os.environ["RO_ANCLAS_COPIA"])] if os.environ.get("RO_ANCLAS_COPIA") else []):
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(ruta, "a") as f:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")
    return a


def comprobar_anclas():
    """Recalcula cada ancla guardada. Un ancla que cubría N filas tiene que seguir dando lo mismo para esas N filas.
    R16 (N6): las anclas nuevas van por rango de ids (primera..ultima); las de antes (solo «dia»), por la fecha UTC con
    la que se hicieron."""
    malas, n = [], 0
    if not ANCLAS.exists():
        return True, [], 0
    with conectar() as con:
        for linea in ANCLAS.read_text().splitlines():
            if not linea.strip():
                continue
            try:
                a = json.loads(linea)
            except ValueError:
                malas.append({"linea": linea[:80], "motivo": "línea rota en el fichero de anclas"})
                continue
            n += 1
            if not a.get("filas"):
                continue
            if a.get("modo") in ("ids", "dia_madrid") and a.get("primera"):
                filas = con.execute("SELECT r.id, h.huella FROM registro r JOIN registro_huellas h ON h.id = r.id "
                                    "WHERE r.id >= ? AND r.id <= ? ORDER BY r.id", (a["primera"], a["ultima"])).fetchall()
            else:
                filas = con.execute("SELECT r.id, h.huella FROM registro r JOIN registro_huellas h ON h.id = r.id "
                                    "WHERE substr(r.creada, 1, 10) = ? AND r.id <= ? ORDER BY r.id", (a["dia"], a["ultima"])).fetchall()
            if len(filas) != a["filas"] or _sha_huellas(filas) != a["sha_dia"]:
                malas.append({"dia": a["dia"], "hecha": a.get("hecha"), "filas_ancla": a["filas"], "filas_hoy": len(filas)})
    return not malas, malas, n


def importar_rastro(carpeta):
    """Importa un volcado de ArtifactData (out_dir: <carpeta>/<coleccion>/<doc>.json) sin borrar nada.
    Cada documento entra en `docs` (si no estaba) y en `registro` con origen panel_v7 (una sola vez)."""
    carpeta = Path(carpeta)
    iniciar_base()
    n = 0
    with conectar() as con:
        for f in sorted(carpeta.rglob("*.json")):
            col = str(f.parent.relative_to(carpeta))
            try:
                doc = json.loads(f.read_text())
            except Exception:
                continue
            datos = doc.get("data", doc) if isinstance(doc, dict) else doc
            existe = con.execute("SELECT 1 FROM registro WHERE origen='panel_v7' AND coleccion=? AND clave=?", (col, f.stem)).fetchone()
            if existe:
                continue
            con.execute("INSERT OR IGNORE INTO docs (coleccion, id, datos, uid) VALUES (?,?,?,?)",
                        (col, f.stem, json.dumps(datos, ensure_ascii=False), (datos or {}).get("uid") if isinstance(datos, dict) else None))
            con.execute("INSERT INTO registro (quien, coleccion, accion, clave, datos, origen) VALUES (?,?,?,?,?, 'panel_v7')",
                        ("declarado:" + str((datos or {}).get("uid") or "panel"), col, "importado", f.stem, json.dumps(datos, ensure_ascii=False)))
            n += 1   # (M3) el «quien» lo declaró el artefacto, que pudo escribir cualquiera: se marca «declarado:»
    return n


# =============================================================== estado en memoria
class Estado:
    """Datos base (data/*.json) + cambios hechos en Ajustes (historial y decisiones de local.db)."""

    def __init__(self):
        self.crudo = None
        self.bloqueados = {}
        self.nucleo_bloqueado = False
        self.foto = None
        self.version = 0          # ronda 14: sube con cada carga (Ajustes, recargas): forma parte de la clave de la caché

    def cargar(self):
        with CANDADO:
            self.modulos = P.cargar_modulos()      # qué módulos ve cada puesto (indice.js + ficheros)
            hallazgos = ESC.escanear(DATA)
            self.bloqueados = hallazgos
            self.nucleo_bloqueado = any(f"data/{n}.json" in hallazgos for n in NUCLEO)
            crudo = {n: json.loads((DATA / f"{n}.json").read_text()) for n in NUCLEO}
            crudo["para_confirmar"] = json.loads((DATA / "para_confirmar.json").read_text()) if (DATA / "para_confirmar.json").exists() else []
            ids = json.loads((DATA / "ids_clientes.json").read_text()) if (DATA / "ids_clientes.json").exists() else {}
            self.id_app = ids.get("portal_a_app") or {}
            from fuentes_verdad.servicios_confirmados import aplicar as aplicar_servicios
            aplicar_servicios(crudo['clientes'])
            self.aplicar_ajustes(crudo)
            ACT.limpiar_nucleo(crudo)          # Tomás 3-oct: clientes de baja fuera de la base (data/verdad/estado_clientes.json)
            self.crudo = crudo
            self.sembrar_tablas()
            self.marcas_nucleo = self._marcas_nucleo()
            self.version += 1
            CACHE_RESP.vaciar()

    # ------------------------------------------------------------------ V3a · recarga parcial
    # Guardar en Ajustes, Altas y bajas o Mi perfil solo escribe en local.db (historial/decisiones): los ficheros de data/ no
    # cambian, así que NO hace falta volver a pasar la puerta de secretos por todo data/ (≈ 6 s, lo que hacía tardar ~4 s
    # cada «Guardar») ni releer el índice de módulos. Se releen solo personas, asignaciones, clientes y para_confirmar, se
    # reaplica el historial y se siembran las tablas. Seguridad antes que velocidad: la versión de la base SUBE y la memoria
    # de recortes se vacía entera (vaciarla es barato; lo caro era la puerta de secretos), así ningún recorte ni ETag de
    # antes del cambio se vuelve a servir (pruebas_seguridad › R14).
    PARCIAL = ("personas", "asignaciones", "clientes")

    def _marcas_nucleo(self):
        out = []
        for n in [*NUCLEO, "para_confirmar", "ids_clientes"]:
            try:
                st = (DATA / f"{n}.json").stat()
                out.append((n, st.st_mtime_ns, st.st_size))
            except OSError:
                out.append((n, None, None))
        return tuple(out)

    def recargar_personas(self, motivo=""):
        """Recarga parcial tras guardar en Ajustes / Altas y bajas / Mi perfil (objetivo < 1 s). Si algún fichero del núcleo
        ha cambiado en disco desde la última carga (o no hay carga), hace la entera: la puerta de secretos tiene que mirarlo.
        Devuelve True si fue parcial."""
        if self.crudo is None or getattr(self, "marcas_nucleo", None) != self._marcas_nucleo():
            self.cargar()
            return False
        t0 = time.perf_counter()
        with CANDADO:
            crudo = dict(self.crudo)                  # logos, alarmas y meta no los toca Ajustes: se reutilizan tal cual
            for n in self.PARCIAL:
                crudo[n] = json.loads((DATA / f"{n}.json").read_text())
            crudo["para_confirmar"] = json.loads((DATA / "para_confirmar.json").read_text()) if (DATA / "para_confirmar.json").exists() else []
            from fuentes_verdad.servicios_confirmados import aplicar as aplicar_servicios
            aplicar_servicios(crudo['clientes'])
            self.aplicar_ajustes(crudo)
            ACT.limpiar_nucleo(crudo)
            self.crudo = crudo
            self.sembrar_tablas()
            self.version += 1
            CACHE_RESP.vaciar()
        print(f"[{ahora()}] recarga parcial{f' ({motivo})' if motivo else ''}: {int((time.perf_counter() - t0) * 1000)} ms", flush=True)
        return True

    def aplicar_ajustes(self, crudo):
        """Reaplica, en orden, lo cambiado en Ajustes. Nada se borra: todo sale de historial y decisiones."""
        with conectar() as con:
            filas = con.execute("SELECT * FROM historial WHERE coleccion IN ('personas','asignaciones') ORDER BY n").fetchall()
            decis = con.execute("SELECT * FROM decisiones WHERE tipo='para_confirmar' ORDER BY id").fetchall()
        por_persona = {p["id"]: p for p in crudo["personas"]}
        for h in filas:
            d = json.loads(h["datos"] or "{}")
            if h["coleccion"] == "personas" and h["operacion"] == "cambiar" and h["id"] in por_persona:
                por_persona[h["id"]].update(d)
            elif h["coleccion"] == "asignaciones" and h["operacion"] == "crear":
                crudo["asignaciones"].append(d)
            elif h["coleccion"] == "asignaciones" and h["operacion"] in ("cerrar", "confirmar"):
                for a in crudo["asignaciones"]:
                    if a["cliente_id"] == d["cliente_id"] and a["silla"] == d["silla"] and a["persona_id"] == d["persona_id"] and not a.get("hasta"):
                        if h["operacion"] == "cerrar":
                            a["hasta"] = d["hasta"]
                        else:
                            a["confianza"] = "confirmada"
        anuladas = {r["anula_a"] for r in decis if r["anula_a"]}
        respuestas = []
        for r in decis:
            if r["id"] not in anuladas and not r["anula_a"] and r["respuesta"]:
                try:
                    respuesta = json.loads(r["respuesta"])
                    if not isinstance(respuesta, (dict, list)):
                        raise ValueError('formato no válido')
                    respuestas.append(respuesta)
                except (TypeError, ValueError):
                    print('Confirmación histórica omitida: formato no válido.', flush=True)
        if respuestas:
            servicios = {c["id"]: c.get("servicios") or {} for c in crudo["clientes"]}
            aplicadas = aplicar_respuestas(respuestas, crudo["personas"], crudo["asignaciones"], servicios, self.id_app, hoy(), dudas=crudo.get("para_confirmar"))
            if any(x.get('error') for x in aplicadas):
                print('Confirmación histórica omitida: contrato no válido.', flush=True)
            hechas = {x.get("duda") for x in aplicadas if not x.get("error")}
            for d in crudo["para_confirmar"]:
                if d["id"] in hechas:
                    d["respondida"] = True
        # El account principal vigente manda como responsable del cliente
        fecha_hoy = P.hoy_iso()
        for c in crudo["clientes"]:
            acc = [a for a in crudo["asignaciones"] if a["cliente_id"] == c["id"] and a["silla"] == "account"
                   and a.get("principal", True) and not a.get("suplencia")
                   and (not a.get("desde") or a["desde"] <= fecha_hoy) and (not a.get("hasta") or a["hasta"] >= fecha_hoy)]
            if acc:
                c["responsable_id"], c["sin_account"] = acc[-1]["persona_id"], None

    def sembrar_tablas(self):
        """Copia personas y asignaciones vigentes a local.db para consultas SQL (v_cartera_hoy).
        Ronda 6 (A7): un dato duplicado (p. ej. un correo repetido) NO tumba el arranque: se ignora con un aviso."""
        vistos = set()
        for p in self.crudo["personas"]:
            for c in [p.get("correo"), *(p.get("otros_correos") or [])]:
                c = (c or "").strip().lower()
                if not c:
                    continue
                if c in vistos:
                    print(f"⚠️  Correo repetido ({p['id']}): se ignora en esta persona hasta que Mili lo corrija en Ajustes.")
                    if (p.get("correo") or "").strip().lower() == c:
                        p["correo"] = None
                    p["otros_correos"] = [x for x in (p.get("otros_correos") or []) if x.strip().lower() != c]
                vistos.add(c)
        with conectar() as con:
            con.execute("DELETE FROM persona_puestos")
            con.execute("DELETE FROM asignaciones")
            con.execute("DELETE FROM personas")
            for p in self.crudo["personas"]:
                con.execute("INSERT INTO personas (id,nombre,alias,alias_todos,correo,otros_correos,nivel,jefe_id,horas_mes,imputa_horas,estado,activo,nota) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (p["id"], p["nombre"], p.get("alias"), json.dumps(p.get("alias_todos") or []), p.get("correo"),
                             json.dumps(p.get("otros_correos") or []), p.get("nivel"), p.get("jefe"), p.get("horas_mes") or 128,
                             p.get("imputa_horas"), p.get("estado") or "activo", 1 if p.get("activo") else 0, p.get("nota")))
                for pu in p.get("puestos", []):
                    con.execute("INSERT INTO persona_puestos VALUES (?,?,?)", (p["id"], pu, 1 if pu == p.get("puesto_principal") else 0))
            for a in self.crudo["asignaciones"]:
                con.execute("INSERT INTO asignaciones (cliente_id,cliente_id_portal,persona_id,silla,principal,suplencia,titular_id,desde,hasta,fuente,confianza,duda) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                            (a["cliente_id"], a.get("cliente_id_portal"), a["persona_id"], a["silla"], 1 if a.get("principal", True) else 0,
                             1 if a.get("suplencia") else 0, a.get("titular_id"), a.get("desde"), a.get("hasta") or (hoy() if a.get("suplencia") else None),
                             a.get("fuente"), a.get("confianza") if a.get("confianza") in ("alta", "media", "baja", "confirmada") else None, a.get("duda")))

    def persona(self, pid):
        return next((p for p in self.crudo["personas"] if p["id"] == pid), None)

    def por_correo(self, correo):
        """La persona de un correo. Si coincide con más de una, nadie (A7): 403 antes que entrar como otra."""
        correo = (correo or "").strip().lower()
        # Ronda 8: manda el correo de entrada (lista de Tomás, el de Cloudflare Access); los demás quedan de respaldo.
        try:   # data/_privado/correos_entrada.json: fuera de personas.json para que no se sirva (ronda 8)
            privados = json.loads((DATA / "_privado" / "correos_entrada.json").read_text()).get("correos", {})
        except (OSError, ValueError):
            privados = {}
        entrada = [p for p in self.crudo["personas"] if correo and (privados.get(p["id"]) or "").strip().lower() == correo]
        if entrada:
            return entrada[0] if len(entrada) == 1 else None
        hits = [p for p in self.crudo["personas"] if (p.get("correo") or "").strip().lower() == correo
                or correo in [c.strip().lower() for c in p.get("otros_correos") or []]]
        return hits[0] if len(hits) == 1 else None


E = Estado()


# =============================================================== recortes de datos de módulos
# Importes numéricos también llegan como importe/importe_*; el saneado de textos no los quita.
CLAVES_CUOTA = re.compile(r"(?:^|[_\-.])(?:cuota(?![_\-.]horas(?:$|[_\-.]))|fee|importe)(?:$|[_\-.])", re.I)
# Ronda 5 (I-01): horas pautadas = cuota ÷ 31,47 €/h, así que revelan la cuota. A quien no ve la cuota no le llegan
# ni las pautadas ni los porcentajes sobre ellas ni el segmento: solo «dentro / fuera de lo pautado».
CLAVES_DERIVADAS_CUOTA = re.compile(r"^(pautadas|horas_pautadas|horas_presup.*|pct_sep|pct_oct|pct_horas|pct_cuota.*|segmento|valor_vida.*)$")
CONSUMIDAS = ("sep", "oct", "horas_mes", "horas_mes_ant", "consumidas")


# Tomás 3-oct: el account ve las horas pactadas frente a las imputadas de SUS clientes (regla «horas_pautadas»), sin euros.
CLAVES_HORAS_PAUTADAS = re.compile(r"^(pautadas|horas_pautadas|horas_presup.*|pct_sep|pct_oct|pct_horas)$")


def sin_cuota(o, deja_pautadas=False):
    """Sustituye las horas pautadas por «dentro_de_lo_pautado» y quita lo que permite deducir la cuota.
    deja_pautadas (Tomás 3-oct, regla «horas_pautadas»): el account del cliente conserva las horas pactadas y su %."""
    pautadas = o.get("pautadas", o.get("horas_pautadas", o.get("horas_presup_mes")))
    if deja_pautadas:
        return {k: v for k, v in o.items() if not CLAVES_DERIVADAS_CUOTA.match(k) or CLAVES_HORAS_PAUTADAS.match(k)}
    out = {k: v for k, v in o.items() if not CLAVES_DERIVADAS_CUOTA.match(k)}
    if isinstance(pautadas, (int, float)) and pautadas > 0:
        out["dentro_de_lo_pautado"] = {k: o[k] <= pautadas for k in CONSUMIDAS if isinstance(o.get(k), (int, float))}
    return out
# Holded/cuadres usan facturado_mes, facturado_holded, facturado_panel, etc.
CLAVES_COBROS = re.compile(r"(?:^|[_\-.])(?:facturas?\w*|facturado\w*|cobrad\w*|impag\w*|pendiente_cobro|revenue|invoice_total)(?:$|[_\-.])", re.I)
CLAVES_INVERSION = re.compile(r"(?:^|[_\-.])(?:gasto\w*|coste(?![_\-.]horas(?:$|[_\-.]))\w*|cpl\w*|cpc\w*|cpm\w*|inversion\w*|spend|budget_ads|presupuesto_ads|ad_spend|cost_per_lead|cost_per_click|importe_publicidad)(?:$|[_\-.])", re.I)
CLAVES_LEAD = re.compile(r"(?:^|[_\-.])(?:nombre_lead|lead_name|nombre_m|telefono|tel|tel_m|correo_lead|email_lead|lead_email|lead_phone|phone_lead|movil|móvil|whatsapp|telefono_contacto|dni|nif|nie|iban)(?:$|[_\-.])", re.I)


class ClaveValor:
    """Ronda 9 (D-P · M4, fuga de /api/cliente): dinero que solo se reconoce mirando también el VALOR.
    «meses» es la cuota de cada mes si es {mes: número} (en Horas o Informes es la lista de meses: no se toca);
    «presupuesto» es dinero si es un bloque (aprobado, invertido…), no si es el número de leads en esa etapa del embudo."""
    def __init__(self, nombre, prueba):
        self.nombre, self.prueba = nombre, prueba

    def match(self, k, v=None):
        return self.prueba(k, v)


def _es_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


DINERO_CUOTA_VALOR = ClaveValor("cuota_por_mes_y_ltv", lambda k, v: (
    (str(k).casefold() == "meses" and isinstance(v, dict) and bool(v) and all(_es_num(x) or x is None for x in v.values()))
    or (re.match(r"^ltv(_eur|_media|_mediana|_total)?$", str(k), re.I) is not None and _es_num(v))))
DINERO_INVERSION_VALOR = ClaveValor("presupuesto_e_invertido", lambda k, v: (
    (str(k).casefold().startswith("presupuesto") and isinstance(v, dict)) or str(k).casefold().startswith("invertido")))
SERIES_CON_GASTO = ("serie", "serie_ant", "serie_anio")     # en un bloque «meta»: [día, gasto, leads] o {d, meta: [gasto, leads]}


def _quita(rx, k, v):
    return rx.match(k, v) if isinstance(rx, ClaveValor) else rx.search(str(k))


def serie_sin_gasto(serie):
    """Deja la serie diaria de Meta con los leads y sin el gasto (posición 1 de [día, gasto, leads…] o meta[0])."""
    if not isinstance(serie, list):
        return serie
    out = []
    for x in serie:
        if isinstance(x, list) and len(x) >= 3 and isinstance(x[0], str):
            out.append([x[0], None, *x[2:]])
        elif isinstance(x, dict):
            y = {k: w for k, w in x.items() if not CLAVES_INVERSION.search(str(k))}
            meta_key = next((k for k in y if str(k).casefold() == "meta"), None)
            if meta_key is not None and isinstance(y[meta_key], list) and y[meta_key]:
                y[meta_key] = [None, *y[meta_key][1:]]
            out.append(y)
        else:
            out.append(x)
    return out


def recortar_doc(obj, quitar, _lead=False):
    """Quita, a cualquier profundidad, las claves que no tocan (y, sin inversión, el gasto de las series de Meta)."""
    if isinstance(obj, dict):
        sin_inv = CLAVES_INVERSION in quitar
        return {k: (serie_sin_gasto(recortar_doc(v, quitar, _lead or str(k).casefold() in ("leads", "leads_detalle", "contactos_lead"))) if sin_inv and str(k).casefold() in SERIES_CON_GASTO and _serie_de_meta(obj) else recortar_doc(v, quitar, _lead or str(k).casefold() in ("leads", "leads_detalle", "contactos_lead")))
                for k, v in obj.items() if not any(_quita(rx, k, v) for rx in quitar)
                and not (_lead and str(k).casefold() in ("nombre", "name", "email", "correo", "phone"))}
    if isinstance(obj, list):
        return [recortar_doc(v, quitar, _lead) for v in obj]
    return obj


def _serie_de_meta(bloque):
    """¿Es un bloque de Meta? (tiene leads/gasto/campañas o su serie lleva «meta»). GA4 y Search Console no se tocan."""
    normal = {str(k).casefold(): v for k, v in bloque.items()}
    ser = normal.get("serie")
    if isinstance(ser, list) and ser and isinstance(ser[0], dict) and "meta" in {str(k).casefold() for k in ser[0]}:
        return True
    return bool({"campanas", "conjuntos", "gasto", "cpl", "actual", "presupuesto"} & set(normal)) and not {"clics", "impresiones_web", "usuarios"} & set(normal)


def quitar_para(persona, cp, cliente_id=None):
    v = lambda t: P.ver(persona, {"tipo": t, "cliente_id": cliente_id}, cp)["ok"]
    q = [CLAVES_LEAD]
    if not v("cuota"):
        q += [CLAVES_CUOTA, DINERO_CUOTA_VALOR]
    if not v("cobros"):
        q.append(CLAVES_COBROS)
    if not v("inversion"):
        q += [CLAVES_INVERSION, DINERO_INVERSION_VALOR]
    if not v("dinero_empresa"):
        q.append(re.compile(r"(?:^|[_\-.])(?:agency_(?:profit|margin|cost)|beneficio\w*|margen\w*|rentabilidad\w*|tarifa_hora|coste_eur)(?:$|[_\-.])", re.I))
    return q


# Dinero con otros nombres en la ficha de E1 (D-P-CAP2 y D-P · M4): «presupuesto», «serie» e «invertido» de las fuentes
# de publicidad, los importes dentro de los textos de motivos y avisos, «meses» y «ltv» del libro, y el bloque de horas.
FUENTES_CON_DINERO = ("meta", "captacion", "captacion_ghl", "google_ads", "tiktok")
CLAVES_DINERO_CAPTACION = re.compile(r"^(presupuesto.*|serie.*|invertido.*|objetivo.*)$")
CLAVES_LIBRO_CUOTA = re.compile(r"^(meses|ltv.*|vida_meses|cuota.*)$")
RE_IMPORTE = P.RE_IMPORTE


def _sin_importes(o):
    """Ronda 11 (B-A02): los textos de las fuentes de publicidad, sin importes y sin dejar «[importe]» a la vista."""
    return P.sin_importes(o)


def recortar_ficha(persona, cp, cid, doc):
    """Ficha de E1 (data/clientes/<id>.json) recortada en el servidor según puesto y cliente:
    claves de dinero (cuota, cobros, inversión) a cualquier profundidad y, además, lo que E1 nombra distinto:
    sin inversión → fuera presupuesto, series, invertido y objetivo de las fuentes de publicidad, y los importes
    de sus textos; sin cuota → fuera meses y LTV del libro; sin horas_cliente → fuera el dato de horas."""
    v = lambda t: P.ver(persona, {"tipo": t, "cliente_id": cid}, cp)["ok"]
    out = recortar_doc(doc, quitar_para(persona, cp, cid))
    fuentes = out.get("fuentes") or {}
    # Ronda 5 (I-02): administración (Sofía) solo necesita cabecera, cuota, contrato y accesos para cobrar.
    if set(persona.get("puestos", [])) <= set(P.REGLAS.get("ficha_solo_contrato", {}).get("puestos", [])):
        deja = set(P.REGLAS["ficha_solo_contrato"].get("fuentes", []))
        out["fuentes"] = {k: x for k, x in fuentes.items() if k in deja}
        out["recortada"] = "Solo cabecera, cuota, contrato y accesos: lo que hace falta para cobrar."
        return ficha_sin_importes(out, v("cuota"), v("inversion"))
    if not v("inversion"):
        for fuente in FUENTES_CON_DINERO:
            if isinstance(fuentes.get(fuente), dict):
                # Ronda 9: la serie diaria de Meta ([gasto, leads] por día) va entera fuera, como presupuesto, invertido y objetivo.
                fuentes[fuente] = _sin_importes(recortar_doc(fuentes[fuente], [CLAVES_DINERO_CAPTACION, DINERO_INVERSION_VALOR, CLAVES_INVERSION]))
    if not v("cuota") and isinstance(fuentes.get("libro"), dict):
        fuentes["libro"] = recortar_doc(fuentes["libro"], [CLAVES_LIBRO_CUOTA])
    if not v("cuota") and isinstance((fuentes.get("horas") or {}).get("datos"), dict):
        fuentes["horas"]["datos"] = sin_cuota(fuentes["horas"]["datos"], v("horas_pautadas"))
    if not v("horas_cliente") and isinstance(fuentes.get("horas"), dict):
        fuentes["horas"] = {k: x for k, x in fuentes["horas"].items() if k != "datos"}
        fuentes["horas"]["nota"] = "Las horas por cliente las ven quien lo lleva, sus jefas, operaciones y dirección (D-84)."
    return ficha_sin_importes(out, v("cuota"), v("inversion"))


def ficha_sin_importes(out, ve_cuota, ve_inversion):
    """Ronda 11 (A1): los importes escritos DENTRO de los textos (asignaciones «Meta d30/sep 354 €», alarmas «137 € en
    Meta», arranque «Gasto en Meta: 142,58 €», cartera «Relanzamiento con 305 €», libro «(72 €/mes)»…) se tapan para
    quien no ve el dinero de ese cliente. Misma regla que recortar_modulo, afinada por fuente: con la cuota se deja el
    libro (es la cuota); con la inversión, las fuentes de publicidad; con las dos, nada se toca."""
    quita = P.importes_a_quitar(ve_cuota, ve_inversion)
    if not quita or not isinstance(out, dict):
        return out
    deja = set()
    if ve_cuota:
        deja.add("libro")
    if ve_inversion:
        deja.update(FUENTES_CON_DINERO)
    fuentes = out.get("fuentes")
    res = {k: (x if k == "fuentes" else P.sin_importes(x, quita)) for k, x in out.items()}
    if isinstance(fuentes, dict):
        res["fuentes"] = {k: (x if k in deja else P.sin_importes(x, quita)) for k, x in fuentes.items()}
    return res


# Claves que delatan una fila de un lead concreto (ronda 4): con nivel «resumen» esas filas no viajan.
CLAVES_FILA_LEAD = {"nombre_lead", "telefono", "tel", "tel_m", "nombre_m", "correo_lead", "email_lead", "enlace_contacto", "contacto_id", "lead_id"}


CLAVES_RENTABILIDAD = re.compile(r"(?:^|[_\-.])(?:tarifa_hora|vida_meses|en_facturacion|margen\w*|rentabilidad\w*|coste_eur|agency_(?:profit|margin|cost))(?:$|[_\-.])", re.I)
CLAVES_ENLACE = re.compile(r"(?i)^(url|enlace.*|href|web|prueba|link.*|enlaces)$")


def recortar_modulo(persona, cp, obj, nivel=None, solo_todo=(), filas_lead=(), conf=None):
    """Contrato genérico para data/<módulo>.json (ver LEEME): filas con cliente_id → solo clientes que ve;
    con persona_id → solo las suyas salvo que pueda ver horas de esa persona; con setter → solo las suyas
    salvo dirección, ventas de RO y jefa de CRM. Las claves de dinero se quitan como en los clientes, y
    se deciden CON EL CLIENTE DE CADA FILA (D-P-CAP1): Lina y Lucía ven el dinero de sus clientes y no el de los demás.
    solo_todo = listas cuyas filas SIN cliente_id solo llegan a quien ve el módulo con nivel «todo»."""
    conf = conf or {}
    if nivel == "vacio":                   # R16c: contrato «lista vacía» (la setter y la verdad): solo lo genérico
        return recorte_vacio(obj, conf)
    puestos = P.puestos_de(persona)        # ronda 7: en «ver como», solo los puestos de las dos
    ve_todos_setters = bool(puestos & {"direccion", "ventas_ro", "jefa_crm", "operaciones"})
    mi_setter = persona["id"].replace("setter_", "") if persona["id"].startswith("setter_") else None

    conf = conf or {}
    cartera = cp.get("cartera_ids", set())
    activo = getattr(P._HILO, "real", None)               # ronda 11 (X1): la persona real en «ver como»
    real_id = activo[0]["id"] if activo else None
    ve_rentabilidad = P.ver(persona, {"tipo": "rentabilidad_cliente"}, cp)["ok"]
    filas_tipo = {f["lista"]: f for f in conf.get("filas_solo_tipo", [])}
    # Tomás 3-oct (58_FEEDBACK_TOMAS_03OCT): el account solo recibe SUS clientes en todas partes. Además de las filas con
    # cliente_id (ya fuera por cliente_detalle), fuera las filas que nombran a otro cliente por «cliente», «cid» o
    # «id»+«nombre» (seo/webs, la lista común de la verdad única), las claves que son otro cliente y las listas de nombres.
    ajeno = clientes_ajenos(persona, cp) if P.solo_su_cartera(persona) else None

    def fila_ok(x):
        if not isinstance(x, dict):
            return True
        if x.get("cliente_id") and not P.ver(persona, {"tipo": "cliente_detalle", "cliente_id": x["cliente_id"]}, cp)["ok"]:
            return False
        if ajeno is not None and not x.get("cliente_id") and cliente_de_fila(x, ajeno):
            return False
        # Ronda 6 (M4): nivel «suyo» de verdad: solo los clientes de su cartera, aunque su ámbito vea más.
        if nivel == "suyo" and x.get("cliente_id") and x["cliente_id"] not in cartera:
            return False
        if x.get("persona_id") and not P.ver(persona, {"tipo": conf.get("regla_persona") or "horas_persona", "persona_id": x["persona_id"]}, cp)["ok"]:
            return False
        # Ronda 6 (chat del equipo): una fila con «miembros» solo llega a sus miembros; ni jefes ni dirección.
        # Ronda 11 (X1): en «ver como» también tiene que ser miembro la persona REAL (mínimo de las dos).
        if isinstance(x.get("miembros"), list):
            ids = {m.get("pid") if isinstance(m, dict) else m for m in x["miembros"]}
            if persona["id"] not in ids or (real_id and real_id not in ids):
                return False
        if "setter" in x and isinstance(x.get("setter"), str) and not ve_todos_setters and x["setter"] != mi_setter:
            return False
        return True

    cache = {}
    cache_p = {}

    def ve_pautadas(cid):
        if cid not in cache_p:
            cache_p[cid] = bool(cid) and P.ver(persona, {"tipo": "horas_pautadas", "cliente_id": cid}, cp)["ok"]
        return cache_p[cid]

    def deja_horas(k, cid):
        """Tomás 3-oct: «cuota_horas» (las horas pactadas) y «coste_horas» (las horas consumidas, no euros) viajan al account
        del cliente aunque no vea la cuota; dentro, sin_cuota() deja solo las horas."""
        return (k == "cuota_horas" and ve_pautadas(cid)) or (k == "coste_horas" and ve_pautadas(cid))

    def quitar(cid):
        if cid not in cache:
            cache[cid] = quitar_para(persona, cp, cid)
        return cache[cid]

    def paso(o, cid=None, lista=None, libre=False, lead_privado=False):
        # Ronda 12 (R13): dentro de una lista de búsquedas/consultas/palabras clave, el texto es del usuario: sin tocar importes.
        libre = libre or bool(lista and P.CLAVES_TEXTO_LIBRE.match(str(lista)))
        if isinstance(o, dict):
            cid = o.get("cliente_id") or o.get("cid") or cid    # el cliente de la fila manda para ella y sus hijos
            q = quitar(cid)
            if CLAVES_CUOTA in q:
                o = sin_cuota(o, ve_pautadas(cid))
            if not ve_rentabilidad:                              # A3: tarifa, vida, márgenes = rentabilidad (D-85)
                o = {k: v for k, v in o.items() if not CLAVES_RENTABILIDAD.search(str(k))}
            sin_inv = CLAVES_INVERSION in q and str(lista).casefold() in ("meta", "datos", "meta_ads") and _serie_de_meta(o)
            return {k: (serie_sin_gasto(paso(v, cid, k, libre, lead_privado or str(k).casefold() in {str(x).casefold() for x in filas_lead})) if sin_inv and str(k).casefold() in SERIES_CON_GASTO else paso(v, cid, k, libre, lead_privado or str(k).casefold() in {str(x).casefold() for x in filas_lead}))
                    for k, v in o.items() if (not any(_quita(rx, k, v) for rx in q) or deja_horas(k, cid))
                    and not (ajeno is not None and str(k).strip().lower() in ajeno)
                    and not (lead_privado and str(k).casefold() in ("nombre", "name", "email", "correo", "phone"))}
        if isinstance(o, str):
            if lista and CLAVES_ENLACE.match(lista):              # A4: nada de javascript: ni data: en enlaces
                return P.enlace_seguro(o)
            # A2/A3: en la fila de un cliente, los importes de cuota solo para quien ve su cuota, y los de gasto, para
            # quien ve su inversión (ronda 11, B-A02: sin dejar «[importe]»; el techo general de coste por lead se deja).
            if cid and (CLAVES_CUOTA in quitar(cid) or CLAVES_INVERSION in quitar(cid)):
                qi = P.importes_a_quitar(CLAVES_CUOTA not in quitar(cid), CLAVES_INVERSION not in quitar(cid))
                return P.sin_importes_libre(o, qi) if libre else P.sin_importes(o, qi)
            return o
        if isinstance(o, list):
            ft = filas_tipo.get(lista)
            if ft and not P.ver(persona, {"tipo": ft["tipo"]}, cp)["ok"]:
                o = [x for x in o if not (isinstance(x, dict) and x.get(ft["campo"]) in ft["valores"])]
            sin_cliente_fuera = lista in solo_todo and nivel != "todo"
            # Nivel «resumen» (p. ej. Valeria en Salud del CRM): fuera las listas de leads y cualquier fila de un lead concreto.
            if nivel == "resumen" and str(lista).casefold() in {str(k).casefold() for k in filas_lead}:
                return []
            return [paso(x, cid, None, libre, lead_privado) for x in o if fila_ok(x)
                    and not (ajeno is not None and isinstance(x, str) and x.strip().lower() in ajeno)
                    and not (sin_cliente_fuera and isinstance(x, dict) and not x.get("cliente_id"))
                    and not (nivel == "resumen" and isinstance(x, dict) and {"nombre_lead", "lead_name", "telefono", "tel", "tel_m", "nombre_m", "correo_lead", "email_lead", "lead_email", "lead_phone", "enlace_contacto", "contacto_id", "lead_id"} & {str(k).casefold() for k in x})]
        return o

    out = paso(obj)
    if isinstance(out, dict):
        for clave, tipo in (conf.get("claves_solo_tipo") or {}).items():       # M5: la parte de dirección, por regla
            if clave in out and not P.ver(persona, {"tipo": tipo}, cp)["ok"]:
                out.pop(clave)
        if nivel == "resumen" and conf.get("resumen"):                         # M4: proyección del nivel «resumen»
            out = {k: v for k, v in out.items() if k in set(conf["resumen"])}
    t = conf.get("textos_sin_importes_salvo")
    if t and not P.ver(persona, {"tipo": t}, cp)["ok"]:                        # A1: dinero de la empresa en textos
        out = P.sin_importes(out)
    for ruta, tipo in (conf.get("ramas_sin_importes_salvo") or {}).items():    # ronda 11 (M5): solo esa rama
        if not P.ver(persona, {"tipo": tipo}, cp)["ok"]:
            out = _rama_sin_importes(out, ruta.split("."))
    if conf.get("solo_cartera_silla"):                                         # R16c: outreach, solo su cartera
        out = recorte_por_silla(persona, cp, out, conf["solo_cartera_silla"])
    # Tomás 3-oct: los accounts no ven dinero en ninguna parte (cuota, facturado, gasto, coste por lead), tampoco escrito
    # dentro de textos sin cliente (prioridades, chat, reglas). Solo se respetan las palabras del propio cliente en sus
    # correos y mensajes («textos_del_cliente») y las búsquedas de la gente (consultas, palabras clave).
    if ajeno is not None and "account" in persona.get("puestos", []) and not P.ver(persona, {"tipo": "cuota"}, cp)["ok"] and not conf.get("textos_del_cliente"):
        out = P.sin_importes(out)
    return out


def clientes_ajenos(persona, cp):
    """Tomás 3-oct: ids y nombres (en minúsculas) de los clientes que NO son de la cartera de la persona. Solo se usa con
    los puestos de «solo_su_cartera» (accounts)."""
    mios = cp.get("cartera_ids") or set()
    out = set()
    for c in E.crudo["clientes"]:
        if c["id"] in mios:
            continue
        out.add(c["id"].lower())
        if (c.get("nombre") or "").strip():
            out.add(c["nombre"].strip().lower())
    return out


def cliente_de_fila(x, ajeno):
    """¿Esta fila (sin cliente_id) es de un cliente ajeno? Por «cid», por «cliente» (id o nombre exacto) o por «id» cuando
    la fila es la de un cliente (lleva también su «nombre»)."""
    for k in ("cid", "cliente", "cliente_slug"):
        v = x.get(k)
        if isinstance(v, str) and v.strip().lower() in ajeno:
            return True
    v = x.get("id")
    return isinstance(v, str) and v.lower() in ajeno and isinstance(x.get("nombre"), str) and x["nombre"].strip().lower() in ajeno


def recorte_vacio(obj, conf):
    """R16c · «vacio_para_puestos»: el fichero con sus claves genéricas («deja») y todas sus listas vacías. Así quien no ve
    la pantalla pero la carcasa le pide el dato (la setter y la verdad única) recibe 200 sin ningún cliente."""
    deja = set((conf.get("vacio_para_puestos") or {}).get("deja") or [])
    if not isinstance(obj, dict):
        return []
    return {k: ([] if isinstance(v, list) else v) for k, v in obj.items() if k in deja or isinstance(v, list)}


_CAMPANA_CLIENTE = {}


def cliente_por_nombre(nombre):
    """R16c · el cliente de un nombre corto («GAC», «PGB Auditores»): la MISMA regla del generador
    (fuentes_ventas/campana_cliente.py) contra los clientes de data/clientes.json. None si no hay coincidencia."""
    if "m" not in _CAMPANA_CLIENTE:
        import importlib.util
        spec = importlib.util.spec_from_file_location("campana_cliente", AQUI / "fuentes_ventas" / "campana_cliente.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _CAMPANA_CLIENTE["m"] = mod
    lista = [(c["id"], c.get("nombre") or c["id"]) for c in E.crudo["clientes"]]
    exacto = next((cid for cid, nom in lista if (nom or "").strip().lower() == (nombre or "").strip().lower()), None)
    return exacto or _CAMPANA_CLIENTE["m"].cliente_de(nombre, lista)


def recorte_por_silla(persona, cp, out, regla):
    """R16c · «solo_cartera_silla»: para quien tiene uno de regla.puestos (y ninguno de salvo_puestos), las listas indicadas
    («snov.campañas» = out["snov"]["campañas"]) solo con filas cuyo cliente_id está en su cartera de esa silla, y las
    tablas por nombre de cliente («clientes») solo con esos clientes. Se mira con los puestos de la persona VISTA: en
    «ver como», Tomás viendo como Eulimar recibe lo de Eulimar."""
    propios = set(persona.get("puestos", []))
    if not propios & set(regla.get("puestos") or []) or propios & set(regla.get("salvo_puestos") or []):
        return out
    if not isinstance(out, dict):
        return out
    suyos = (cp.get("cartera_por_silla") or {}).get(regla.get("silla"), set())
    out = dict(out)
    for ruta in regla.get("listas") or []:
        partes = ruta.split(".")
        padre = out
        for k in partes[:-1]:
            if not isinstance(padre.get(k), dict):
                padre = None
                break
            padre[k] = dict(padre[k])
            padre = padre[k]
        if isinstance(padre, dict) and isinstance(padre.get(partes[-1]), list):
            padre[partes[-1]] = [x for x in padre[partes[-1]] if isinstance(x, dict) and x.get("cliente_id") in suyos]
    for clave in regla.get("claves_por_nombre") or []:
        if isinstance(out.get(clave), dict):
            out[clave] = {k: v for k, v in out[clave].items() if cliente_por_nombre(k) in suyos}
    return out


def _rama_sin_importes(o, ruta):
    """Tapa los importes solo dentro de o[ruta[0]][ruta[1]]…; el resto del fichero, intacto."""
    if not ruta:
        return P.sin_importes(o)
    if isinstance(o, dict) and ruta[0] in o:
        return {**o, ruta[0]: _rama_sin_importes(o[ruta[0]], ruta[1:])}
    return o


def ve_alguno(persona, modulos):
    """¿Ve la persona alguno de estos módulos (a cualquier nivel)? Devuelve el mejor nivel o None."""
    niveles = [P.nivel_modulo(persona, E.modulos.get(m, {})) for m in modulos]
    niveles = [n for n in niveles if n]
    return max(niveles, key=lambda n: {"resumen": 1, "suyo": 2, "todo": 3}[n]) if niveles else None


def config_almacen(almacen):
    import fnmatch
    if not isinstance(almacen, str) or any(s in ('', '.', '..') for s in almacen.split('/')):
        return None
    segmentos = almacen.split('/')
    for patron, conf in P.REGLAS.get("almacenes_privados", {}).items():
        if (len(patron.split('/')) == len(segmentos)
                and all(fnmatch.fnmatchcase(s, p) for s, p in zip(segmentos, patron.split('/')))):
            return conf
    return None


# =============================================================== cliente de un dato privado (ronda 6, C4)
_CORREO_GENERICO = {"gmail.com", "hotmail.com", "hotmail.es", "outlook.com", "outlook.es", "yahoo.com", "yahoo.es", "icloud.com",
                    "live.com", "msn.com", "me.com", "protonmail.com", "gmx.com", "gmx.es", "telefonica.net", "terra.es"}


def empresa_de_correo(correo):
    """3-oct: la empresa de un prospecto de outreach cuando Snov.io no la trae: el dominio de su correo («gestepa.com»),
    nunca un buzón genérico (gmail, hotmail…). El correo completo sigue detrás de «Ver respuesta»."""
    dom = (correo or "").rsplit("@", 1)[-1].strip().lower() if "@" in (correo or "") else ""
    return "" if not dom or dom in _CORREO_GENERICO else dom


def nombres_para_su_dueno(persona, real, reglas, salida, rel, cp=None):
    """Ronda 6 (auditoría 29, F-10; D-88 ya lo permite): el dueño de un lead (su setter, Tomás en sus reuniones de venta,
    la persona de la agenda) recibe el nombre y el despacho completos. Teléfono y correo siguen detrás de «Ver completo».
    Cada vez queda en el rastro (una fila por fichero y minuto).
    3-oct (Tomás dirige a los setters): «tambien_puestos» en la regla = esos puestos (dirección, ventas de RO) ven en claro
    los leads de TODOS los setters, como su setter. «dueno»: «outreach» = dirección y jefa de CRM, todos; el puesto outreach,
    solo las filas de clientes de SU cartera de outreach (además del recorte por silla). «anadir» = campos que la fila
    pública no trae (la empresa del prospecto) y se añaden solo para quien la ve en claro."""
    puestos = set(P.puestos_de(persona))
    mi_setter = persona["id"].replace("setter_", "") if persona["id"].startswith("setter_") else None
    cartera_out = ((cp or {}).get("cartera_por_silla") or {}).get("outreach", set())
    abiertos = 0
    cache = {}
    import copy
    original = copy.deepcopy(salida)
    for r in reglas:
        dueno = r.get("dueno")
        for fila in (salida.get(r["lista"]) or []) if isinstance(salida, dict) else []:
            if not isinstance(fila, dict):
                continue
            es_dueno = ((dueno == "setter" and mi_setter and fila.get("setter") == mi_setter)
                        or (dueno == "setter" and fila.get("setter") in ("ana", "javier") and puestos & set(r.get("tambien_puestos") or []))
                        or (dueno == "persona_id" and fila.get("persona_id") == persona["id"])
                        or (dueno == "ventas_ro" and fila.get("setter") == "_closer" and "ventas_ro" in puestos)
                        or (dueno == "outreach" and (puestos & {"direccion", "jefa_crm"}
                                                     or ("outreach" in puestos and fila.get("cliente_id") and fila.get("cliente_id") in cartera_out))))
            if not es_dueno:
                continue
            try:
                almacen = r["almacen"].format(**{k: v for k, v in fila.items() if isinstance(v, str)})
            except KeyError:
                continue
            if almacen not in cache:
                p = (DATA / f"{almacen}.json").resolve()
                cache[almacen] = json.loads(p.read_text()) if str(p).startswith(str(DATA.resolve())) and p.exists() else None
            doc = cache[almacen]
            for paso in r["ruta"]:
                doc = doc.get(paso.format(**{k: v for k, v in fila.items() if isinstance(v, str)})) if isinstance(doc, dict) else None
            if doc is None:
                continue
            for enmascarado, completo in r["campos"].items():
                valor = doc.get(completo) if isinstance(doc, dict) and completo else doc
                if completo == "empresa" and not valor and isinstance(doc, dict):
                    valor = empresa_de_correo(doc.get("correo"))
                if isinstance(valor, str) and (enmascarado in fila or (valor and enmascarado in (r.get("anadir") or []))):
                    fila[enmascarado] = valor
                    abiertos += 1
            fila["nombre_completo"] = True
    if abiertos:
        clave = (persona["id"], rel, datetime.now().strftime("%Y-%m-%d %H:%M"))
        if clave not in _LECTURAS_VISTAS:
            try:
                registrar(real["id"], "leads", "nombres_propios", rel, {"campos": abiertos, "detalle": "nombres de sus propios leads (D-88)"})
            except sqlite3.OperationalError:
                traceback.print_exc()          # ronda 11 (M-07): sin rastro no se abren los nombres, pero la pantalla carga
                return original
            _LECTURAS_VISTAS[clave] = True
    return salida


_MARCAS = {}


def recargar_si_cambian():
    """Relee reglas_permisos.json y el índice de módulos (indice.js y modulos/*.js) si han cambiado en disco.
    Ronda 14: como mucho una vez por segundo (antes, 44 stat por petición)."""
    t = time.monotonic()
    if t - _MARCAS.get("_mirado", -9) < 1:
        return
    _MARCAS["_mirado"] = t
    try:
        m_reglas = (AQUI / "reglas_permisos.json").stat().st_mtime
        m_mod = max(f.stat().st_mtime for f in (AQUI / "modulos").glob("*.js"))
    except Exception:
        return
    if _MARCAS.get("reglas") not in (None, m_reglas):
        try:
            P.recargar_reglas()
            print(f"[{ahora()}] reglas_permisos.json releído")
        except Exception:
            traceback.print_exc()          # un JSON a medio escribir: se sigue con las reglas anteriores
            return
    if _MARCAS.get("modulos") not in (None, m_mod):
        try:
            E.modulos = P.cargar_modulos()
            print(f"[{ahora()}] índice de módulos releído")
        except Exception:
            traceback.print_exc()
    if (_MARCAS.get("reglas"), _MARCAS.get("modulos")) != (m_reglas, m_mod):
        CACHE_RESP.vaciar()
    _MARCAS["reglas"], _MARCAS["modulos"] = m_reglas, m_mod


# Ronda 11 (M2): un fichero de datos roto (a medio escribir), de 0 bytes o vacío ({} / []) NO da 500 ni sale vacío: se sirve
# el último dato bueno que el servidor leyó de ese fichero, con su hora. Sin uno anterior, 503 con un motivo legible.
_ULTIMO_BUENO = {}
_CANDADO_BUENO = threading.Lock()


class DatoRoto(Exception):
    pass


class DatoSecreto(DatoRoto):
    pass


def _lectura_secreta_actual(fichero):
    """Escanea exactamente el texto leído; política y fichero forman la versión."""
    from types import SimpleNamespace
    permitidos_f = AQUI / 'escaner_permitidos.json'
    rel = fichero.relative_to(AQUI).as_posix()
    for _ in range(2):
        marca = _estado_fichero(fichero)
        politica = _estado_fichero(permitidos_f) if permitidos_f.exists() else None
        with _CANDADO_BUENO:
            previo = _ULTIMO_BUENO.get(str(fichero))
        sello = (marca, politica)
        if previo and previo[0] == sello:
            return previo[1], previo[2], sello
        texto = fichero.read_text()
        try:
            permisos = json.loads(permitidos_f.read_text()) if politica is not None else {}
            if not isinstance(permisos, dict) or not isinstance(permisos.get(rel, []), list) or not all(isinstance(x, str) for x in permisos.get(rel, [])):
                raise ValueError('política inválida')
        except (OSError, ValueError, TypeError):
            raise DatoSecreto('La política de secretos no está disponible.')
        captura = SimpleNamespace(name=fichero.name, parent=fichero.parent, suffix=fichero.suffix,
                                  relative_to=fichero.relative_to, read_text=lambda **kw: texto)
        hallazgos = ESC.escanear_fichero(captura, set(permisos.get(rel, [])))
        if marca != _estado_fichero(fichero) or politica != (_estado_fichero(permitidos_f) if permitidos_f.exists() else None):
            continue
        with CANDADO:
            if hallazgos:
                E.bloqueados[rel] = hallazgos
            else:
                E.bloqueados.pop(rel, None)
            E.nucleo_bloqueado = any(f'data/{n}.json' in E.bloqueados for n in NUCLEO)
        if hallazgos:
            raise DatoSecreto('La puerta de secretos ha encontrado algo en este fichero: no se sirve.')
        obj = json.loads(texto)
        return obj, datetime.fromtimestamp(fichero.stat().st_mtime).isoformat(timespec='seconds'), sello
    raise DatoSecreto('El fichero cambió durante la comprobación de secretos: vuelve a probar.')


def leer_json_bueno(fichero):
    """(objeto, aviso o None). aviso = {"dato_de": hora, "motivo": …} cuando se sirve el último bueno."""
    clave = str(fichero)
    try:
        obj, fecha, sello = _lectura_secreta_actual(fichero)
        if obj in ({}, [], None):
            raise ValueError("fichero vacío")
    except DatoSecreto:
        raise
    except (OSError, ValueError) as e:
        with _CANDADO_BUENO:
            previo = _ULTIMO_BUENO.get(clave)
        if previo:
            return previo[1], {"dato_de": previo[2], "motivo": f"El fichero de datos está {'vacío' if 'vacío' in str(e) else 'roto o a medio escribir'}: se enseña el último dato bueno, de las {previo[2][11:16]}."}
        if isinstance(e, ValueError) and "vacío" in str(e):
            return obj, {"dato_de": None, "motivo": "El fichero de datos está vacío y no hay un dato anterior en el servidor."}
        raise DatoRoto("El fichero de datos está roto o a medio escribir y no hay un dato anterior: vuelve a probar en un minuto.")
    with _CANDADO_BUENO:
        _ULTIMO_BUENO[clave] = (sello, obj, fecha)
    return obj, None


def entrada_datos_modulo(rel):
    """Entrada de datos_de_modulo: exacta o por patrón («chat_equipo/p_*»)."""
    import fnmatch
    if not isinstance(rel, str) or any(s in ('', '.', '..') for s in rel.split('/')):
        return None
    dm = P.REGLAS.get("datos_de_modulo", {})
    if rel in dm:
        return dm[rel]
    segmentos = rel.split('/')
    return next((v for k, v in dm.items() if '*' in k
                 and len(k.split('/')) == len(segmentos)
                 and all(fnmatch.fnmatchcase(s, patron) for s, patron in zip(segmentos, k.split('/')))), None)


def ambito_datos_581(real, persona):
    from acciones_lectura_544 import ambito
    return ambito(E, P, ACT, real, persona)


def cliente_url_581(rel):
    partes = rel.split('/')
    if len(partes) == 2 and partes[0] == 'clientes':
        return partes[1]
    if len(partes) == 3 and ((partes[0] == 'paneles' and partes[1] in ('ga4', 'gsc', 'meta', 'ghl', 'mc'))
                            or (partes[0] == 'informe' and partes[1].startswith('c_'))):
        return partes[2]
    return None


def cliente_datos_581(cid, ambito, niveles):
    from acciones_lectura_544 import cliente_visible
    if (ambito is None or not isinstance(cid, str) or not re.fullmatch(r'[\w\-]{1,100}', cid)
            or not cliente_visible(cid, E, P, ACT, ambito[0], ambito[1])):
        return False
    return all(nivel != 'suyo' or cid in cp.get('cartera_ids', set())
               for nivel, cp in zip(niveles, ambito[1]))


def documento_raiz_581(doc, rel, ambito, niveles):
    """Sólo autoridad de cliente explícito; no aplica reglas de filas/personas a la raíz."""
    ids = [cliente_url_581(rel)] if cliente_url_581(rel) is not None else []
    if isinstance(doc, dict):
        ids += [doc[k] for k in ('cliente_id', 'cid', 'cli') if k in doc and doc[k] is not None]
    return (not ids or (all(isinstance(cid, str) and cid == ids[0] for cid in ids)
                        and cliente_datos_581(ids[0], ambito, niveles)))


def modulo_vigente_581(real, persona, rel, previo, doc):
    final = puerta_modulo(real, persona, rel, apuntar=False)
    return (not final.get('error') and final.get('firma581') == previo.get('firma581')
            and final.get('nivel') == previo.get('nivel')
            and final.get('marca581') == previo.get('marca581')
            and documento_raiz_581(doc, rel, final.get('ambito581'), final.get('niveles581', [])))


def puerta_cliente_581(real, persona, cid):
    ambito = ambito_datos_581(real, persona)
    if ambito is None:
        return None
    niveles = [ve_alguno(p, ['ficha', 'bandeja', 'captacion', 'asistente-ia']) for p in ambito[0]]
    if not all(niveles) or not cliente_datos_581(cid, ambito, niveles):
        return None
    return {'ambito': ambito, 'niveles': niveles,
            'nivel': min(niveles, key={'resumen': 1, 'suyo': 2, 'todo': 3}.get)}


def cliente_vigente_581(real, persona, cid, previo):
    final = puerta_cliente_581(real, persona, cid)
    if final is None or final['ambito'][2] != previo['ambito'][2]:
        return False
    if 'fichero581' in previo:
        try:
            marca = _estado_fichero(previo['fichero581'])
        except OSError:
            marca = None
        if marca != previo['marca581']:
            return False
    return True


def puerta_modulo(real, persona, rel, apuntar=True):
    """R15 (A5): la puerta de /api/modulo/<rel>, sacada a una función para que el índice del buscador pase por la MISMA.
    Devuelve {"error": (código, texto)} o {"fichero", "conf", "nivel"}. apuntar=False no deja «denegado» en el rastro
    (el índice prueba muchos ficheros a la vez; lo que no se puede leer, simplemente no entra)."""
    ambito581 = ambito_datos_581(real, persona)
    if ambito581 is None:
        return {"error": (403, "El ámbito actual de estos datos no está disponible.")}
    # 249: sólo este panel es nominal; todas sus rutas/cache/buscador pasan por
    # esta puerta antes de leer. Una dirección nueva ni Vercomo sustituyen a Tomás.
    if rel.split('/')[0] == 'panel_direccion' and not PANEL_PRIVADO_249.permitido(real, persona, E.crudo.get('personas')):
        return {"error": (403, "El panel de dirección está reservado a Tomás, sin «ver como».")}
    solo_lectura = persona["id"] != real["id"]
    fichero = (DATA / f"{rel}.json").resolve()
    try:
        marca581 = _estado_fichero(fichero)
    except OSError:
        marca581 = None
    if "_privado" in rel or not str(fichero).startswith(str(DATA.resolve())) or rel.split("/")[0] in NUCLEO + ["clientes", "para_confirmar", "ids_clientes"]:
        return {"error": (403, "Ese fichero no se sirve por aquí.")}
    entrada = entrada_datos_modulo(rel)
    # Formato: lista de módulos, o {"modulos": [...], "puestos": [...], "solo_todo_sin_cliente": [...], "filas_lead": [...]}
    # «puestos» (ronda 4): el fichero solo lo leen esos puestos (con nivel «todo»), vean o no una pantalla concreta.
    conf = entrada if isinstance(entrada, dict) else {"modulos": entrada}
    modulos, puestos_ok = conf.get("modulos") or [], conf.get("puestos")
    if not entrada or not (modulos or puestos_ok):
        return {"error": (403, f"data/{rel}.json no está asignado a ningún módulo en reglas_permisos.json (datos_de_modulo): no se sirve.")}
    # Ronda 6: «solo_propio» = fichero de la propia persona (<carpeta>/p_<id>); nadie pide el de otro.
    # Ronda 11 (X1): se mira con la persona REAL también: en «ver como» nadie lee el fichero privado de otro
    # (chats directos, alertas propias…), ni Mili ni Tomás. Solo el propio miembro.
    if conf.get("solo_propio") and (rel.split("/")[-1] != f"p_{persona['id']}" or rel.split("/")[-1] != f"p_{real['id']}"):
        if apuntar:
            registrar_agrupado(real["id"], "modulo", "denegado", rel, {"motivo": "fichero de otra persona"}, como=persona["id"] if solo_lectura else None)
        return {"error": (403, "Ese fichero es de otra persona.")}
    if puestos_ok:   # (C3) en «ver como», también la persona real tiene que tener el puesto
        niveles581 = ['todo' if set(p.get('puestos', [])) & set(puestos_ok) else None for p in ambito581[0]]
        nivel = "todo" if all(niveles581) else None
        if conf.get("solo_real") and not set(real.get("puestos", [])) & set(puestos_ok):   # D-P-C2
            nivel = None
    else:
        niveles581 = [ve_alguno(p, modulos) for p in ambito581[0]]
        nivel = min(niveles581, key={'resumen': 1, 'suyo': 2, 'todo': 3}.get) if all(niveles581) else None
    # Ronda 5 (I-02): «excluir_puestos» = quien solo tiene esos puestos no recibe el fichero (Sofía y Reuniones).
    if conf.get("excluir_puestos") and any(set(p.get('puestos', [])) <= set(conf['excluir_puestos']) for p in ambito581[0]):
        nivel = None
    # R16c: «vacio_para_puestos» = quien solo tiene esos puestos y no ve el módulo recibe 200 con las listas vacías
    # (la setter y la verdad única: la carcasa la pide a todos). Nunca más que eso.
    vacio = (conf.get("vacio_para_puestos") or {}).get("puestos") or []
    if not nivel and vacio and persona.get("puestos") and set(persona["puestos"]) <= set(vacio):
        return {"fichero": fichero, "conf": conf, "nivel": "vacio", 'firma581': ambito581[2],
                'ambito581': ambito581, 'niveles581': niveles581, 'marca581': marca581}
    if not nivel:
        if apuntar:
            registrar_agrupado(real["id"], "modulo", "denegado", rel, {"modulos": modulos}, como=persona["id"] if solo_lectura else None)
        return {"error": (403, "Estos datos son de una pantalla que no es de tu puesto.")}
    cid581 = cliente_url_581(rel)
    if cid581 is not None and not cliente_datos_581(cid581, ambito581, niveles581):
        return {"error": (403, "El cliente de estos datos no está autorizado.")}
    return {"fichero": fichero, "conf": conf, "nivel": nivel, 'firma581': ambito581[2],
            'ambito581': ambito581, 'niveles581': niveles581, 'marca581': marca581}


# ===================================================================== R15 · buscador (A5), Mis clientes (A6) y «Algo va mal» (A7)
def modulo_recortado(real, persona, cp, rel):
    """El fichero data/<rel>.json ya recortado para esta persona, por la MISMA puerta que /api/modulo/<rel> (sin dejar
    «denegado» en el rastro: lo que no puede leer no entra en el índice). None si no puede o no existe."""
    pm = puerta_modulo(real, persona, rel, apuntar=False)
    if pm.get("error") or not pm["fichero"].exists():
        return None
    try:
        doc, aviso_dato_287 = leer_json_bueno(pm["fichero"])
    except Exception:
        return None
    if not modulo_vigente_581(real, persona, rel, pm, doc):
        return None
    conf = pm["conf"]
    salida = ACT.quitar_bajas(recortar_modulo(persona, cp, doc, pm["nivel"], tuple(conf.get("solo_todo_sin_cliente", [])), tuple(conf.get("filas_lead", [])), conf), rel)
    if rel == "produccion/produccion" and not aviso_dato_287:
        salida = EVIDENCIA_PRODUCCION_287.enriquecer287(salida, sys.modules[__name__], real, persona)
        import controlador_planning_681 as PLANNING_681
        salida = PLANNING_681.enriquecer681(salida, sys.modules[__name__], real, persona)
    return salida if modulo_vigente_581(real, persona, rel, pm, doc) else None


def vencidas_al_dia(d, pid, hoy):
    """R16c · «Vencidas en tu mano» con el hoy de Madrid, con LA MISMA regla que alDia() de modulos/produccion_comun.js (y el
    generador): si el dato es de otro día, vence < hoy → vencida (más de 30 días → olvidada); revisión y bloqueadas no cambian.
    Se cuenta sobre la cola ya recortada para la persona, como la pantalla. Con el dato de hoy, la cifra del fichero."""
    dato = d.get("hoy") or str(d.get("generado") or "")[:10] or hoy
    propia = next((x for x in d.get("personas") or [] if isinstance(x, dict) and x.get("persona_id") == pid), None)
    if dato >= hoy or not isinstance(d.get("cola"), list):
        return (propia or {}).get("vencidas") or 0
    n = 0
    for r in d["cola"]:
        if not isinstance(r, dict) or r.get("persona_id") != pid or not r.get("vence") or r.get("grupo") in ("revision", "bloqueada"):
            continue
        g = r.get("grupo")
        if r["vence"] < hoy and g in ("hoy", "semana", "despues", "vencida"):
            try:
                g = "olvidada" if (date.fromisoformat(hoy) - date.fromisoformat(r["vence"][:10])).days > 30 else "vencida"
            except ValueError:
                g = "vencida"
        n += g == "vencida"
    return n


def _txt(x, n=140):
    return re.sub(r"\s+", " ", str(x if x is not None else "")).strip()[:n]


# Ficheros que alimentan el índice del buscador (cada uno pasa por su puerta; el de alertas es el propio, p_<id>).
FUENTES_BUSCAR = ["produccion/produccion", "bandeja/bandeja", "seo/webs", "captacion/captacion", "reuniones/reuniones",
                  "decisiones/reloj", "incidencias/incidencias"]
TOPE_TAREAS_INDICE = 3000


def indice_busqueda(real, persona, cp):
    """Índice ligero por persona: lo que su puesto puede ver, sacado de los datos YA recortados. Cada fila:
    {g: grupo, t: texto, s: detalle, ir: ruta exacta, k?: claves extra (ticket, url), id?, cli?: cliente, pos?: puede posponer}."""
    out = []
    alias = {p["id"]: p.get("alias") or p.get("nombre") for p in E.crudo["personas"]}

    def fila(g, t, s, ir, **x):
        if t and ir:
            out.append({"g": g, "t": _txt(t), "s": _txt(s, 160), "ir": ir, **{k: v for k, v in x.items() if v not in (None, "", False)}})

    d = modulo_recortado(real, persona, cp, "produccion/produccion")
    if isinstance(d, dict):
        tareas = {}
        for r in d.get("cola") or []:
            if not isinstance(r, dict) or not r.get("id") or not r.get("tarea"):
                continue
            x = tareas.setdefault(r["id"], {"r": r, "quien": []})
            if r.get("persona_id") and r["persona_id"] not in x["quien"]:
                x["quien"].append(r["persona_id"])
        mias = sorted(tareas.values(), key=lambda x: (persona["id"] not in x["quien"], not x["r"].get("vencida")))[:TOPE_TAREAS_INDICE]
        for x in mias:
            r = x["r"]
            quien = ", ".join(alias.get(q, q) for q in x["quien"][:3])
            fila("Tareas", r["tarea"], " · ".join(v for v in (r.get("cliente"), quien, r.get("estado"), "vencida" if r.get("vencida") else None) if v),
                 f"#/produccion/{r['id']}", cli=r.get("cliente"), mia=persona["id"] in x["quien"])
    d = modulo_recortado(real, persona, cp, "bandeja/bandeja")
    if isinstance(d, dict):
        for r in d.get("correos") or []:
            if not isinstance(r, dict) or not r.get("id"):
                continue
            esp = f"{round(r['horas'])} h sin contestar" if isinstance(r.get("horas"), (int, float)) else None
            fila("Correos", r.get("asunto") or "(sin asunto)", " · ".join(v for v in (r.get("cliente") or "Sin cliente", r.get("numero"), esp, "queja" if r.get("queja") else None) if v),
                 f"#/bandeja/{r['id']}", k=r.get("numero"), id=r["id"], cli=r.get("cliente"), cid=r.get("cliente_id"),
                 h=r.get("horas") if isinstance(r.get("horas"), (int, float)) else None,
                 mia=r.get("account_id") == persona["id"] or r.get("cliente_id") in (cp.get("cartera_ids") or set()))
    if persona["id"] == real["id"]:   # alertas: solo las propias (p_<id>); en «ver como» no hay índice de alertas ajeno
        d = modulo_recortado(real, persona, cp, f"alertas/p_{persona['id']}")
        if isinstance(d, dict):
            for a in d.get("alertas") or []:
                if not isinstance(a, dict) or a.get("estado") in ("resuelta", "no_aplica"):
                    continue
                pos = (persona["id"] in (a.get("escalado_cadena") or []) or persona["id"] == a.get("jefe_id")
                       or bool(P.puestos_de(persona) & {"direccion", "operaciones"}))
                fila("Alertas", f"{a.get('titulo') or 'Alerta'}{' · ' + a['cliente'] if a.get('cliente') else ''}", a.get("motivo"),
                     a.get("ir") if str(a.get("ir") or "").startswith("#/") else "#/alertas", id=a.get("id"), pos=pos, plazo_h=a.get("plazo_h"))
    d = modulo_recortado(real, persona, cp, "seo/webs")
    if isinstance(d, dict):
        for w in d.get("webs") or []:
            if isinstance(w, dict) and w.get("cliente"):
                fila("Webs", w.get("nombre") or w["cliente"], " · ".join(v for v in (w.get("url"), w.get("motivo")) if v),
                     f"#/seo-web/webs/{w['cliente']}", k=w.get("url"))
    d = modulo_recortado(real, persona, cp, "captacion/captacion")
    if isinstance(d, dict):
        for c in d.get("clientes") or []:
            if isinstance(c, dict) and c.get("cliente_id"):
                fila("Campañas", f"Campañas de {c.get('nombre') or c['cliente_id']}", c.get("nicho"), f"#/captacion/{c['cliente_id']}", cli=c.get("nombre"))
    d = modulo_recortado(real, persona, cp, "reuniones/reuniones")
    if isinstance(d, dict):
        for r in (d.get("asistencias") or [])[-400:]:
            if isinstance(r, dict) and r.get("tema"):
                fila("Reuniones", r["tema"], " · ".join(v for v in (r.get("fecha"), r.get("hora"), r.get("cliente")) if v),
                     f"#/reuniones/{r['reunion']}" if r.get("reunion") else "#/reuniones", id=r.get("reunion"))
    d = modulo_recortado(real, persona, cp, "decisiones/reloj")
    if isinstance(d, dict):
        for r in d.get("decisiones") or []:
            if isinstance(r, dict) and r.get("id"):
                fila("Decisiones", r.get("titulo") or r["id"], r.get("problema"), f"#/decisiones/reloj/{r['id']}")
    d = modulo_recortado(real, persona, cp, "incidencias/incidencias")
    if isinstance(d, dict):
        for r in d.get("incidencias") or []:
            if isinstance(r, dict) and r.get("id"):
                fila("Incidencias", f"{r.get('titulo') or 'Incidencia'}{' · ' + r['cliente'] if r.get('cliente') else ''}", r.get("texto"), f"#/incidencias/{r['id']}")
    return out


def marcas_buscar(persona):
    m = []
    for rel in FUENTES_BUSCAR + [f"alertas/p_{persona['id']}"]:
        try:
            m.append(_estado_fichero((DATA / f"{rel}.json")))
        except OSError:
            m.append(None)
    return tuple(m)


def _sin_tilde(t):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", str(t or "").lower()) if unicodedata.category(c) != "Mn")


def buscar_en(indice, q, tope=50):
    palabras = _sin_tilde(q).split()
    if not palabras:
        return []
    res = []
    for x in indice:
        hay = _sin_tilde(" ".join((x.get("t") or "", x.get("s") or "", x.get("k") or "")))
        if all(w in hay for w in palabras):
            t = _sin_tilde(x.get("t"))
            res.append((0 if t.startswith(palabras[0]) else 1 if f" {palabras[0]}" in f" {t}" else 2, x))
    return [x for _, x in sorted(res, key=lambda y: y[0])[:tope]]


TOPE_FIJADOS = 30
TOPE_OPINIONES_HORA = 20
MAX_CAPTURA = 190_000
RUTA_APP = re.compile(r"^#/[\w\-/%.?=&]{0,200}$")
RUTA_SENSIBLE = re.compile(r"(?i)sueld|n[oó]min|salari")


def leer_preferencia(pid, clave):
    with conectar() as con:
        r = con.execute("SELECT valor FROM preferencias WHERE persona=? AND clave=?", (pid, clave)).fetchone()
    try:
        return json.loads(r["valor"]) if r else None
    except Exception:
        return None


def opinion_a_json(r, con_captura=False):
    d = {k: r[k] for k in r.keys() if k != "captura"}
    for k in ("texto", "esperaba", "frescura", "pantalla"):    # R16 (N1): también lo guardado antes del tapado
        if d.get(k):
            d[k] = limpiar_texto(d[k])
    d["tiene_captura"] = bool(r["captura"])
    if con_captura:
        d["captura"] = r["captura"]
    p = next((x for x in E.crudo["personas"] if x["id"] == r["quien"]), None)
    d["quien_alias"] = (p or {}).get("alias") or r["quien"]
    return d


def avisar_opinion(real, oid, b):
    """Aviso en #avisos-dirección (avisos.py), solo para dirección y operaciones. Nada sale de la app."""
    av = sys.modules.get("avisos")
    if not av or not hasattr(av, "publicar"):
        return False
    que = "Algo va mal" if b["tipo"] == "fallo" else "Idea"
    prio = {"rojo": " · rojo", "ambar": " · ámbar"}.get(b["prioridad"], "")
    texto = f"{que}{prio} · {real.get('alias') or real['id']} en «{b.get('pantalla') or b.get('ruta') or 'la app'}» ({b.get('ancho') or '?'} px): «{_txt(limpiar_texto(b['texto']), 220)}»"
    try:
        with conectar() as con:
            return bool(av.publicar(con, "avisos-direccion", "evento", texto, f"opinion:{oid}", quien=real["id"], dueno_id="tomas",
                                    menciones=[x for x in ("tomas", "mili") if x != real["id"]], ver={"puestos": ["direccion", "operaciones"]},
                                    datos={"icono": "alert" if b["tipo"] == "fallo" else "spark", "ir": "#/ajustes/opiniones"}))
    except Exception:
        traceback.print_exc()
        return False


def cliente_de_ticket(objeto):
    """Cliente de un ticket de Desk según la Bandeja (id o número). None = no está en la bandeja; "" = ticket sin cliente."""
    try:
        d = json.loads((DATA / "bandeja/bandeja.json").read_text())
    except Exception:
        return None
    for fila in d.get("correos", []) + d.get("triaje", []):
        if str(objeto) in (str(fila.get("id")), str(fila.get("numero"))):
            return fila.get("cliente_id") or ""
    return None


def cliente_de_objeto(herramienta, objeto):
    """Ronda 11 (A4): el cliente de lo que se contesta lo saca el SERVIDOR del propio objeto, nunca del navegador.
    desk → el ticket en la Bandeja; whatsapp → el grupo del cliente (data/whatsapp/whatsapp.json, por cliente_id);
    ghl → el lead, la cita o la oportunidad (data/crm/crm.json, por ref). None = no se puede saber (o la fuente
    no se lee); "" = el objeto existe pero no es de ningún cliente."""
    objeto = str(objeto or "")
    if not objeto:
        return None
    if herramienta == "desk":
        return cliente_de_ticket(objeto)
    try:
        if herramienta == "whatsapp":
            d = json.loads((DATA / "whatsapp/whatsapp.json").read_text())
            fila = next((f for f in d.get("clientes", []) if isinstance(f, dict) and f.get("cliente_id") == objeto), None)
            return (fila.get("cliente_id") or "") if fila else None
        if herramienta == "ghl":
            d = json.loads((DATA / "crm/crm.json").read_text())
            m = re.search(r"(?:lead|cita|oportunidad|contacto)\s+(\S+)$", objeto)      # R16: «Subcuenta · cita <ref>»
            refs = {objeto} | ({m.group(1)} if m else set())
            for lista in ("leads_sin_tocar", "citas_sin_estado", "oportunidades_paradas"):
                for f in d.get(lista, []) or []:
                    if isinstance(f, dict) and str(f.get("ref")) in refs:
                        return f.get("cliente_id") or ""
            return None
    except Exception:
        return None
    return None


def referencia_accion603(herramienta, tipo, objeto):
    """Referencia exacta: (cliente, conocida, ambigua/inválida); nunca CID del cuerpo."""
    if isinstance(objeto, bool) or not isinstance(objeto, (str, int)):
        return None, False, True
    objeto = str(objeto)
    clientes = [c for c in E.crudo.get("clientes") or [] if isinstance(c, dict) and c.get("id") == objeto]
    if len(clientes) > 1:
        return None, False, True
    if herramienta == "desk" and tipo == "recordatorio_impago":
        archivo, listas, campos = "finanzas/impagos.json", ("filas",), ("doc",)
    elif herramienta in ("desk", "app"):
        archivo, listas, campos = "bandeja/bandeja.json", ("correos", "triaje"), ("id", "numero")
    elif herramienta == "whatsapp":
        archivo, listas, campos = "whatsapp/whatsapp.json", ("clientes",), ("cliente_id",)
    elif herramienta == "ghl":
        archivo, listas, campos = "crm/crm.json", ("leads_sin_tocar", "citas_sin_estado", "oportunidades_paradas"), ("ref",)
    else:
        return None, False, False
    refs = {objeto}
    if herramienta == "ghl":
        m = re.search(r"(?:lead|cita|oportunidad|contacto)\s+(\S+)$", objeto)
        if m:
            refs.add(m.group(1))
    try:
        doc = json.loads((DATA / archivo).read_text())
        if not isinstance(doc, dict):
            raise ValueError("Forma de fuente inválida")
        filas = []
        for lista in listas:
            xs = doc.get(lista, [])
            if not isinstance(xs, list):
                raise ValueError("Forma de fuente inválida")
            filas.extend(x for x in xs if isinstance(x, dict) and any(x.get(k) is not None and str(x[k]) in refs for k in campos))
    except Exception:
        # App conserva sus referencias globales; no se finge una referencia de proveedor.
        if herramienta == "app" and len(clientes) == 1:
            return objeto, True, False
        return None, False, herramienta != "app"
    if len(filas) > 1:
        return None, False, True
    if filas:
        cid = filas[0].get("cliente_id")
        if herramienta == "desk" and tipo == "recordatorio_impago" and not cid:
            return None, False, True
        if cid is not None and (not isinstance(cid, str) or not cid):
            return None, False, True
        if clientes and cid != objeto:
            return None, False, True
        return cid, True, False
    if len(clientes) == 1 and (herramienta == "app" or herramienta == "desk" and tipo in ("pedir_accesos", "correo", "crear_reunion", "recordatorio_seguimiento")):
        return objeto, True, False
    return None, False, False


def autoridad_decision607(real, clientes):
    """Autoridad actual para una decisión nueva, incluida su lista de clientes."""
    from acciones_lectura_544 import ambito, cliente_visible
    inicial = ambito(E, P, ACT, real, real)
    if inicial is None:
        return None
    ps, cps, firma = inicial
    if not all(cliente_visible(cid, E, P, ACT, ps, cps) for cid in clientes):
        return None
    final = ambito(E, P, ACT, real, real)
    return firma if final is not None and final[2] == firma else None


_ACCIONES_RECIENTES = {}


def accion_repetida(quien, b):
    """Ronda 11 (M1): la misma acción (quién + herramienta + tipo + objeto + texto) en N segundos → id de la anterior."""
    import hashlib
    seg = int(P.REGLAS.get("acciones_repetidas_segundos") or 0)
    if seg <= 0:
        return None
    clave = hashlib.sha256(json.dumps([quien, b.get("herramienta"), b.get("tipo"), str(b.get("objeto")), b.get("texto")],
                                      ensure_ascii=False, default=str).encode()).hexdigest()
    ahora_t = time.time()
    with CANDADO_ACCIONES:
        for k in [k for k, (t, _) in _ACCIONES_RECIENTES.items() if ahora_t - t > seg]:
            _ACCIONES_RECIENTES.pop(k, None)
        previa = _ACCIONES_RECIENTES.get(clave)
        return clave, (previa[1] if previa else None)


CANDADO_ACCIONES = threading.Lock()

_PIEZAS = {"mtime": None, "por_id": {}}


def pieza_en_revision(objeto):
    """R14 (B2) · la pieza de Producción que espera revisión, sacada SIEMPRE de data/produccion/produccion.json (nunca del
    navegador): {id, cli, estado, autores:set(ids)}. None si no está esperando revisión."""
    f = DATA / "produccion" / "produccion.json"
    try:
        mt = f.stat().st_mtime
        if _PIEZAS["mtime"] != mt:
            d = json.loads(f.read_text())
            por_nombre = {}
            for p in E.crudo.get("personas", []):
                for forma in (p.get("alias"), p.get("nombre"), (p.get("nombre") or "").split(" ")[0]):
                    if forma:
                        por_nombre[forma.strip().lower()] = p["id"]
            por_id = {}
            for r in d.get("cola") or []:
                if r.get("grupo") == "revision":
                    x = por_id.setdefault(r["id"], {"id": r["id"], "cli": r.get("cli"), "estado": r.get("estado"), "autores": set()})
                    x["autores"].add(r.get("persona_id"))
            for r in d.get("revisiones") or []:
                if r.get("estado") == "bloqueado":
                    continue
                x = por_id.setdefault(r["id"], {"id": r["id"], "cli": r.get("cliente_id"), "estado": r.get("estado"), "autores": set()})
                x["cli"] = x["cli"] or r.get("cliente_id")
                x["autores"] |= {por_nombre[n.strip().lower()] for n in r.get("asignados") or [] if n and n.strip().lower() in por_nombre}
            _PIEZAS.update(mtime=mt, por_id=por_id)
    except Exception:
        return None
    return _PIEZAS["por_id"].get(str(objeto or ""))


_TAREAS = {"mtime": None, "por_id": {}}


def tarea_de_produccion(objeto):
    """R16 (N4): una tarea de ClickUp según Producción (data/produccion/produccion.json): {id, cli, estado, autores}.
    None si no está (o no se puede leer). La saca SIEMPRE el servidor, nunca el navegador."""
    f = DATA / "produccion" / "produccion.json"
    try:
        mt = f.stat().st_mtime
        if _TAREAS["mtime"] != mt:
            por_id = {}
            for r in json.loads(f.read_text()).get("cola") or []:
                if isinstance(r, dict) and r.get("id"):
                    x = por_id.setdefault(str(r["id"]), {"id": r["id"], "cli": r.get("cli"), "estado": r.get("estado"), "autores": set()})
                    x["autores"].add(r.get("persona_id"))
            _TAREAS.update(mtime=mt, por_id=por_id)
    except Exception:
        return None
    t = _TAREAS["por_id"].get(str(objeto or ""))
    if t is None:   # Mi trabajo (3-oct): lo de «planning mensual» o «backlog» que vence este mes (fuera de la cola de Producción)
        try:
            fm = DATA / "mi_trabajo" / "mi_trabajo.json"
            mm = fm.stat().st_mtime
            if _TAREAS.get("mt_mtime") != mm:
                extra = {}
                for r in json.loads(fm.read_text()).get("tareas") or []:
                    if isinstance(r, dict) and r.get("id") and r.get("extra"):
                        x = extra.setdefault(str(r["id"]), {"id": r["id"], "cli": r.get("cli"), "estado": r.get("estado"), "autores": set()})
                        x["autores"].add(r.get("persona_id"))
                _TAREAS.update(mt_mtime=mm, extra=extra)
            t = _TAREAS.get("extra", {}).get(str(objeto or ""))
        except Exception:
            t = None
    return t


def lleva_cliente(persona, cid, cp):
    """R16 (N4): ¿lleva esta persona ese cliente? Su cartera (cualquier silla) o un puesto que responde de todos
    (reglas_permisos.json → acciones_con_efecto_fuera.lleva_puestos)."""
    conf = P.REGLAS.get("acciones_con_efecto_fuera") or {}
    return bool(cid) and (cid in (cp.get("cartera_ids") or set()) or bool(set(persona.get("puestos", [])) & set(conf.get("lleva_puestos") or [])))


RX_DIRECCION_CRUDA = re.compile(r"@|^\+?[\d\s().-]{7,}$")


def _enlaces_malos(o, clave=None, prof=0):
    """R16 (B6): cualquier enlace (url, enlace, href, prueba…) con javascript:, data:… a cualquier profundidad."""
    if prof > 6:
        return False
    if isinstance(o, dict):
        return any(_enlaces_malos(v, k, prof + 1) for k, v in o.items())
    if isinstance(o, list):
        return any(_enlaces_malos(v, clave, prof + 1) for v in o)
    if isinstance(o, str) and clave and re.search(r"(?i)url|enlace|href|link|prueba", str(clave)):
        return bool(o.strip()) and not P.enlace_seguro(o)
    return False


def puede_revisar_pieza(persona, pieza, cp):
    """R14 (B2) · ¿puede esta persona (la REAL) aprobar o pedir cambios en esta pieza? Reglas en reglas_permisos.json
    → revision_piezas (las mismas que lee produccion.js para enseñar los botones). Nadie se aprueba a sí mismo."""
    rp = P.REGLAS.get("revision_piezas") or {}
    if not pieza or persona["id"] in pieza["autores"] or pieza["estado"] in rp.get("espera_cliente", []):
        return False
    regla = (rp.get("por_estado") or {}).get(pieza["estado"])
    if not regla:
        return False
    puestos = set(persona.get("puestos", []))
    if puestos & set(rp.get("siempre", [])):
        return True
    if regla.get("revisa") == "account":
        return bool(pieza["cli"]) and pieza["cli"] in (cp.get("cartera_por_silla") or {}).get("account", set())
    if regla.get("revisa") == "puestos":
        mias = puestos & set(regla.get("puestos", []))
        if not mias:
            return False
        # R16 (N11): la jefa revisa solo las piezas de SU área (puesto del autor o su jefe directo).
        areas = rp.get("areas_tecnica") or {}
        if not areas:
            return True
        oficios = {o for j in mias for o in areas.get(j, [])}
        for aid in pieza["autores"]:
            a = E.persona(aid) if aid else None
            if a and (set(a.get("puestos") or []) & oficios or a.get("jefe") == persona["id"]):
                return True
        return False
    if regla.get("revisa") == "persona":
        return regla.get("persona") == persona["id"]
    return False


def tipo_de_decision(did):
    """Tipo (para_tomas, para_coti, escalada) de una decisión de la tabla, de una acción subida o del reloj generado."""
    did = str(did or "")
    m = re.fullmatch(r"db-(\d+)", did)
    with conectar() as con:
        if m:
            fila = con.execute("SELECT tipo FROM decisiones WHERE id=?", (int(m.group(1)),)).fetchone()
            return fila["tipo"] if fila else None
        m = re.fullmatch(r"acc-(\d+)", did)
        if m:
            fila = con.execute("SELECT vista_previa FROM acciones WHERE id=? AND tipo='decision_nueva'", (int(m.group(1)),)).fetchone()
            return (json.loads(fila["vista_previa"] or "{}") or {}).get("tipo", "para_tomas") if fila else None
    try:
        reloj = json.loads((DATA / "decisiones/reloj.json").read_text())
        return next((d.get("tipo") for d in reloj.get("decisiones", []) if d.get("id") == did), None)
    except Exception:
        return None


def cliente_del_dato(conf, ref, almacen=None):
    """«cliente»: "ref" → el ref ES el cliente (contactos, chat, WhatsApp); {"desde": "crm/crm", "listas": [...], "clave": "ref"}
    → se busca la fila con ese ref en el fichero del módulo y se toma su cliente_id; {"campo": "cliente_id"} (R16c) → el
    campo de la fila ref en el PROPIO almacén privado (respuestas de outreach); sin «cliente» → None (no es de un cliente)."""
    c = conf.get("cliente")
    if not c:
        return None
    if c == "ref":
        return ref if any(x["id"] == ref for x in E.crudo["clientes"]) else None
    if isinstance(c, dict) and c.get("campo"):
        try:
            f = (DATA / f"{almacen}.json").resolve()
            doc = json.loads(f.read_text()) if almacen and str(f).startswith(str(DATA.resolve())) else {}
        except Exception:
            return None
        for coleccion in (doc.values() if isinstance(doc, dict) else []):
            if isinstance(coleccion, dict) and isinstance(coleccion.get(ref), dict):
                cid = coleccion[ref].get(c["campo"])
                return cid if any(x["id"] == cid for x in E.crudo["clientes"]) else None
        return None
    try:
        d = json.loads((DATA / f"{c['desde']}.json").read_text())
    except Exception:
        return None
    for lista in c.get("listas", []):
        for fila in d.get(lista, []) or []:
            if isinstance(fila, dict) and str(fila.get(c.get("clave", "ref"))) == ref:
                return fila.get("cliente_id")
    return None


# =============================================================== «ver como»: lecturas al rastro (ronda 6, M2)
_LECTURAS_VISTAS = {}
_CANDADO_LECTURAS_VISTAS = threading.Lock()


def ruta_lectura_ver_como585(ruta):
    """Familia pública del lector; nunca guarda segmentos dinámicos ni consultas."""
    segmentos = str(ruta).split("?", 1)[0].split("/", 3)
    familias = {"sesion", "modulo", "cliente", "buscar", "decisiones", "ajustes", "acciones", "rastro",
                "ia", "avisos", "envios", "sincronia", "canales", "cerebro", "metodo", "mi_trabajo",
                "tareas", "uso", "operaciones", "crm", "agenda", "recarga", "opiniones"}
    familia = segmentos[2] if len(segmentos) >= 3 and segmentos[:2] == ["", "api"] else ""
    return "/api/" + (familia if familia in familias else "otra")


def apuntar_lectura_ver_como(real, vista, ruta):
    """Solicitud autenticada de lectura, agrupada sólo después de persistir."""
    ruta = ruta_lectura_ver_como585(ruta)
    clave = (real["id"], vista["id"], ruta, datetime.now().strftime("%Y-%m-%d %H:%M"))
    with _CANDADO_LECTURAS_VISTAS:
        if clave in _LECTURAS_VISTAS:
            return
        registrar(real["id"], "ver_como", "lectura", ruta,
                  {"metodo": "GET", "evento": "solicitud", "agrupacion": "familia_minuto"}, como=vista["id"])
        if len(_LECTURAS_VISTAS) >= 5000:
            _LECTURAS_VISTAS.clear()
        _LECTURAS_VISTAS[clave] = True


# =============================================================== decisiones en vivo (ronda 4, D-P-PER1)
TIPOS_DECISION = ("para_tomas", "para_coti", "escalada")


def puede_contestar(persona, tipo):
    pu = set(persona.get("puestos", []))
    return ("proyectos" in pu or "direccion" in pu) if tipo == "para_coti" else "direccion" in pu


def recorte_importes_lectura588(filas, personas, contextos):
    """Importes estructurados y texto según los cuatro grants de ambos actores.

    vista_previa conserva su formato almacenado; si es JSON se examinan sus
    textos decodificados, también para tipos no incluidos en el recorte estructural.
    """
    salida = []
    for original in filas:
        fila = dict(original)
        cid = fila.get("cliente_id")
        permisos = [all(P.ver(p, {"tipo": tipo, "cliente_id": cid}, cp).get("ok") is True
                        for p, cp in zip(personas, contextos))
                    for tipo in ("cuota", "inversion", "cobros", "dinero_empresa")]
        quitar = P.importes_a_quitar(*permisos)
        # 632: un número bajo fee/CPC/agency_profit no es texto monetario.
        # Reutilizar los patrones económicos de 589, sin añadir aquí política
        # de leads. La unión conserva la intersección de ambos grants.
        patrones = []
        for p, cp in zip(personas, contextos):
            for patron in quitar_para(p, cp, cid):
                if patron is not CLAVES_LEAD and patron not in patrones:
                    patrones.append(patron)
        fila = recortar_doc(fila, patrones)
        if quitar:
            vp = fila.pop("vista_previa", None)
            tiene_vp = "vista_previa" in original.keys()
            fila = P.sin_importes(fila, quitar)
            if tiene_vp:
                if isinstance(vp, str):
                    try:
                        valor = json.loads(vp)
                    except (ValueError, TypeError):
                        fila["vista_previa"] = P.sin_importes(vp, quitar)
                    else:
                        limpio = P.sin_importes(recortar_doc(valor, patrones), quitar)
                        fila["vista_previa"] = vp if limpio == valor else json.dumps(limpio, ensure_ascii=False)
                else:
                    fila["vista_previa"] = P.sin_importes(recortar_doc(vp, patrones), quitar)
        salida.append(fila)
    return salida


def decisiones_para(persona, cp):
    """Tabla «decisiones» (tipo ≠ para_confirmar) + las subidas y contestadas como acción simulada (M21 hasta hoy),
    en vivo y recortadas: dirección y operaciones, todas; Coti (proyectos), las «para_coti» y las suyas; el resto,
    las que subió."""
    with conectar() as con:
        tabla = [dict(r) for r in con.execute("SELECT * FROM decisiones WHERE tipo <> 'para_confirmar' AND anula_a IS NULL ORDER BY id")]
        acc = [dict(r) for r in con.execute("SELECT * FROM acciones WHERE tipo IN ('decision_nueva','decidir') ORDER BY id")]
    lista = []
    for d in tabla:
        extra = json.loads(d.get("datos") or "{}") if d.get("datos") else {}
        lista.append({"id": f"db-{d['id']}", "clave": d.get("clave"), "tipo": d["tipo"], "quien": d["quien"], "persona_id": d["quien"],
                      "titulo": d.get("titulo") or (d.get("problema") or "")[:80], "problema": d.get("problema"),
                      "recomendacion": d.get("recomendacion"), "cliente_id": d.get("cliente_id"), "creada": d["creada"],
                      "respuesta": json.loads(d["respuesta"]) if d.get("respuesta") else None, "respondida": d.get("respondida"),
                      "respondida_por": d.get("respondida_por"), "origen": "Subida desde la app (local.db)", **extra})
    for a in acc:
        vp = json.loads(a.get("vista_previa") or "{}") if a.get("vista_previa") not in (None, "null") else {}
        if a["tipo"] == "decision_nueva":
            lista.append({"id": f"acc-{a['id']}", "clave": f"acc-{a['id']}", "tipo": vp.get("tipo") or "para_tomas", "quien": a["quien"],
                          "persona_id": a["quien"], "titulo": vp.get("titulo") or a.get("texto"), "problema": vp.get("problema"),
                          "recomendacion": vp.get("recomendacion"), "cliente_id": a.get("cliente_id"), "creada": a["creada"],
                          "fecha_limite": vp.get("fecha"), "respuesta": None, "respondida": None, "respondida_por": None,
                          "origen": "Botón «Subir una decisión» · simulado", "simulada": True})
    for a in acc:
        vp = json.loads(a.get("vista_previa") or "{}") if a.get("vista_previa") not in (None, "null") else {}
        if a["tipo"] == "decidir":
            d = next((x for x in lista if x["id"] == vp.get("decision_id") and not x["respondida"]), None)
            quien_decide = E.persona(a["quien"]) or {}
            if d and puede_contestar(quien_decide, d["tipo"]):   # A5: una «decidir» de otra persona no cuenta
                d.update({"respuesta": {"decision": vp.get("decision"), "motivo": vp.get("motivo"), "delegada_en": vp.get("delegada_en")},
                          "respondida": a["creada"], "respondida_por": a["quien"], "simulada": True})
    pu = P.puestos_de(persona)
    if pu & {"direccion", "operaciones"}:
        return lista
    if "proyectos" in pu:
        return [d for d in lista if d["tipo"] == "para_coti" or d["quien"] == persona["id"]]
    return [d for d in lista if d["quien"] == persona["id"]]


# =============================================================== «Actualizar ahora» y avisos (ronda 3)
RECARGA_CFG = Path(os.environ.get("RO_RECARGA_CONFIG") or AQUI / "recarga.json")
TOPE_AVISOS_DIA = 3
COLA = threading.Event()


def pedir_recarga(quien, modo="ligera"):
    """Encola una recarga. Si ya hay una pendiente o en curso, devuelve esa (no se apilan)."""
    with conectar() as con:
        viva = con.execute("SELECT * FROM recargas WHERE estado IN ('pendiente','en_curso') ORDER BY id LIMIT 1").fetchone()
        if viva:
            return dict(viva), False
        cur = con.execute("INSERT INTO recargas (quien, modo) VALUES (?, ?)", (quien, modo))
        fila = con.execute("SELECT * FROM recargas WHERE id=?", (cur.lastrowid,)).fetchone()
    COLA.set()
    return dict(fila), True


def _validar_pasos_recarga575(cfg, modo):
    if not isinstance(cfg, dict) or modo not in cfg or not isinstance(cfg[modo], list):
        raise ValueError('Configuración de recarga inválida')
    pasos = cfg[modo]
    ids = set()
    for paso in pasos:
        if not isinstance(paso, dict):
            raise ValueError('Paso inválido')
        pid, cmd, limite = paso.get('id'), paso.get('cmd'), paso.get('timeout', 300)
        if not isinstance(pid, str) or not pid or pid in ids:
            raise ValueError('Identificador de paso inválido')
        ids.add(pid)
        if not ((isinstance(cmd, str) and bool(cmd.strip())) or (isinstance(cmd, list) and bool(cmd) and all(isinstance(x, str) and bool(x) for x in cmd))):
            raise ValueError('Comando inválido')
        if isinstance(limite, bool) or not isinstance(limite, (int, float)) or not 0 < limite <= 86400:
            raise ValueError('Límite inválido')
    return pasos


def _fallo_recarga575(fila, pasos, fase, clase):
    """Diagnóstico público genérico. Nunca texto de excepción, comando ni cuerpo privado."""
    diagnostico = {'id': 'worker_error', 'ok': False, 'segundos': 0,
                  'salida': ['fase: ' + fase, 'clase: ' + clase]}
    salida = list(pasos) + [diagnostico]
    with conectar() as con:
        con.execute("UPDATE recargas SET estado='con_fallos', terminada=datetime('now'), pasos=? WHERE id=? AND estado IN ('en_curso','ok','con_fallos')",
                    (json.dumps(salida, ensure_ascii=False), fila['id']))


def trabajador_recargas():
    """Atiende jobs una vez; errores recuperables no terminan el hilo ni reejecutan pasos."""
    reparaciones = {}
    errores = 0
    while True:
        COLA.wait(timeout=60)
        COLA.clear()
        while True:
            fila, tomada, pasos, fase = None, False, [], 'consulta'
            try:
                # Fallos de persistencia previos se terminalizan, nunca vuelven a pendiente.
                for jid, reparacion in list(reparaciones.items()):
                    _fallo_recarga575(*reparacion)
                    del reparaciones[jid]
                with conectar() as con:
                    fila = con.execute("SELECT * FROM recargas WHERE estado='pendiente' ORDER BY id LIMIT 1").fetchone()
                    if not fila:
                        break
                    fase = 'claim'
                    if con.execute("UPDATE recargas SET estado='en_curso', empezada=datetime('now') WHERE id=? AND estado='pendiente'", (fila['id'],)).rowcount != 1:
                        continue
                    tomada = True
                fase = 'configuracion'
                cfg = json.loads(RECARGA_CFG.read_text())
                plan = _validar_pasos_recarga575(cfg, fila['modo'])
                for paso in plan:
                    fase = 'ejecucion'
                    t0 = time.time()
                    try:
                        r = subprocess.run(paso['cmd'], cwd=AQUI, capture_output=True, text=True, timeout=paso.get('timeout', 300))
                        ok, salida = r.returncode == 0, (r.stdout + r.stderr).strip().splitlines()[-3:]
                    except subprocess.TimeoutExpired:
                        ok, salida = False, ['Tiempo de ejecución agotado.']
                    except Exception as exc:
                        ok, salida = False, ['Fallo de ejecución: ' + type(exc).__name__]
                    pasos.append({'id': paso['id'], 'ok': ok, 'segundos': round(time.time() - t0, 1), 'salida': [ESC_linea(x) for x in salida]})
                    fase = 'progreso'
                    with conectar() as con:
                        con.execute('UPDATE recargas SET pasos=? WHERE id=?', (json.dumps(pasos, ensure_ascii=False), fila['id']))
                fase = 'finalizacion'
                estado = 'ok' if all(p['ok'] for p in pasos) else 'con_fallos'
                with conectar() as con:
                    con.execute("UPDATE recargas SET estado=?, terminada=datetime('now') WHERE id=?", (estado, fila['id']))
                fase = 'registro'
                registrar(fila['quien'], 'recarga', 'recarga_terminada', str(fila['id']), {'estado': estado, 'fallos': [p['id'] for p in pasos if not p['ok']]})
                fase = 'carga'
                E.cargar()
                fase = 'avisos'
                calcular_avisos()
                errores = 0
            except Exception as exc:
                clase = type(exc).__name__
                print('Recarga: fallo controlado · fase=' + fase + ' · clase=' + clase, flush=True)
                if tomada and fila is not None:
                    reparacion = (dict(fila), list(pasos), fase, clase)
                    try:
                        _fallo_recarga575(*reparacion)
                    except Exception as secundaria:
                        reparaciones[fila['id']] = reparacion
                        print('Recarga: terminalización pendiente · clase=' + type(secundaria).__name__, flush=True)
                    try:
                        registrar(fila['quien'], 'recarga', 'recarga_error', str(fila['id']), {'fase': fase, 'clase': clase})
                    except Exception as secundaria:
                        print('Recarga: registro de fallo no disponible · clase=' + type(secundaria).__name__, flush=True)
                # La tabla sigue siendo autoridad; Event no es la única memoria de pendientes.
                errores = min(errores + 1, 5)
                time.sleep(errores)


def ESC_linea(texto):
    """Una línea de salida de un generador, sin correos ni teléfonos (va a la base y a la pantalla)."""
    texto = re.sub(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", "[correo]", texto or "")
    return re.sub(r"\+?\d[\d\s.-]{8,}\d", "[número]", texto)[:240]


def calcular_avisos():
    """Avisos a Tomás (07_SUPERPROMPT_AVISOS): fuente rota, fuente vieja con el plan B también pasado
    (más del doble de su límite) y paso de recarga que falla dos veces seguidas. Como mucho 3 al día
    «para avisar»; el resto, «retenido». No se repite el mismo aviso en el mismo día."""
    hoy = P.hoy_iso()
    candidatos = []
    try:
        fuentes = json.loads((DATA / "fuentes.json").read_text()).get("fuentes", [])
    except Exception:
        fuentes = []
    for x in fuentes:
        if x.get("estado") == "rota":
            candidatos.append((1, "fuente_rota", x["id"], f"{x.get('nombre', x['id'])}: no responde ({x.get('error') or 'sin detalle'})."))
        elif x.get("estado") == "dato_viejo" and x.get("limite_h") and (x.get("edad_h") or 0) > 2 * x["limite_h"]:
            candidatos.append((3, "fuente_vieja", x["id"], f"{x.get('nombre', x['id'])}: dato de hace {x.get('edad_h')} h (límite {x['limite_h']} h)."))
    with conectar() as con:
        ult = [json.loads(r["pasos"] or "[]") for r in con.execute("SELECT pasos FROM recargas WHERE estado IN ('ok','con_fallos') ORDER BY id DESC LIMIT 2")]
    if len(ult) == 2:
        mal = {p["id"] for p in ult[0] if not p["ok"]} & {p["id"] for p in ult[1] if not p["ok"]}
        for pid in sorted(mal):
            candidatos.append((2, "recarga_fallida", pid, f"La recarga de «{pid}» ha fallado dos veces seguidas."))
    candidatos.sort()
    with conectar() as con:
        for _, tipo, clave, texto in candidatos:
            if con.execute("SELECT 1 FROM avisos WHERE dia=? AND tipo=? AND clave=?", (hoy, tipo, clave)).fetchone():
                continue
            n = con.execute("SELECT count(*) FROM avisos WHERE dia=? AND estado='para_avisar'", (hoy,)).fetchone()[0]
            con.execute("INSERT INTO avisos (dia, tipo, clave, texto, estado) VALUES (?,?,?,?,?)",
                        (hoy, tipo, clave, texto, "para_avisar" if n < TOPE_AVISOS_DIA else "retenido"))


# =============================================================== servidor HTTP
class Manejador(SimpleHTTPRequestHandler):
    server_version = "RO"          # R16 (B2): sin versión de Python ni del servidor en la cabecera «Server»
    sys_version = ""

    def version_string(self):
        return "RO"

    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(AQUI), **k)

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[{ahora()}] {self.address_string()} {fmt % args}\n")

    # ---------------------------------------------------------------- respuestas
    def acepta_gzip(self):
        return "gzip" in (self.headers.get("Accept-Encoding") or "").lower()

    def codificacion(self):
        """Ronda 14: br si el navegador lo acepta y está el módulo brotli; si no, gzip."""
        ae = (self.headers.get("Accept-Encoding") or "").lower()
        if _BROTLI and re.search(r"\bbr\b", ae):
            return "br"
        return "gzip" if "gzip" in ae else None

    def responder_guardado(self, e):
        """Ronda 14 (causas 4 y 8): respuesta ya recortada de la memoria, con su ETag; 304 sin cuerpo si no ha cambiado.
        Sigue con no-store: el navegador no la guarda en disco; la memoria de la app manda el If-None-Match a mano."""
        if (self.headers.get("If-None-Match") or "").strip() == e["etag"]:
            self.send_response(304)
            self.send_header("ETag", e["etag"])
            self.send_header("Cache-Control", "no-store")
            self.send_header("Vary", "Accept-Encoding, Cookie, X-RO-Yo, X-RO-Como")
            self.end_headers()
            return
        cod = self.codificacion() if len(e["cuerpo"]) > 1024 else None
        cuerpo = CACHE_RESP.comprimido(e, cod) if cod else e["cuerpo"]
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("ETag", e["etag"])
        if cod:
            self.send_header("Content-Encoding", cod)
        self.send_header("Vary", "Accept-Encoding, Cookie, X-RO-Yo, X-RO-Como")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def responder(self, codigo, obj):
        cuerpo = json.dumps(obj, ensure_ascii=False).encode()
        # Ronda 8: gzip para respuestas de más de 1 kB (Producción pesaba 1,5 MB). Ronda 14: br si se puede.
        cod = self.codificacion() if len(cuerpo) > 1024 else None
        comprimido = bool(cod)
        if comprimido:
            cuerpo = comprimir(cuerpo, cod)
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        if comprimido:
            self.send_header("Content-Encoding", cod)
        self.send_header("Vary", "Accept-Encoding")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def fichero_comprimido(self, rel):
        """Ronda 8: .js, .css y .json estáticos con gzip. Ronda 14 (causa 2): ETag con la huella del contenido y, si la
        dirección lleva ?v=<esa huella>, caché de un año (immutable): el navegador no vuelve a preguntar."""
        try:
            p = ruta_estatica(AQUI, rel)
            datos, huella = contenido_servido(rel)
        except (OSError, ValueError):
            return self.responder(404, {"error": "No existe."})
        etag = f'"{huella}"'
        v = (parse_qs(urlparse(self.path).query).get("v") or [None])[0]
        cache = INMUTABLE if v == huella else "no-cache"
        if (self.headers.get("If-None-Match") or "").strip() == etag:
            self.send_response(304)
            self.send_header("ETag", etag)
            self.send_header("Cache-Control", cache)
            self.end_headers()
            return
        tipo = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
        if tipo.startswith("text/") or tipo in ("application/javascript", "application/json"):
            tipo += "; charset=utf-8"
        cod = self.codificacion() if len(datos) > 1024 and not rel.endswith(".woff2") else None
        comprimido = bool(cod)
        if comprimido:
            clave = (rel, huella, cod)
            with _CANDADO_SERVIDOS:
                z = _SERVIDOS.get(clave)
            if z is None:
                z = comprimir(datos, cod)
                with _CANDADO_SERVIDOS:
                    _SERVIDOS[clave] = z
            datos = z
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("ETag", etag)
        self.send_header("Cache-Control", cache)
        if comprimido:
            self.send_header("Content-Encoding", cod)
        self.send_header("Vary", "Accept-Encoding")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        # Ronda 6 (A4, B3): nada de iframes, ni scripts de fuera, ni enlaces que ejecuten código.
        # Ronda 14: index.html añade la huella de su mapa de versiones (el único script en línea permitido).
        self.send_header("Content-Security-Policy", getattr(self, "_csp", None) or CSP)
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        super().end_headers()

    def cuerpo(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 200_000:
            raise ValueError("cuerpo demasiado grande")
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    # ---------------------------------------------------------------- identidad
    def quien(self, q):
        recargar_si_cambian()   # ronda 6 (auditoría 29, F-04): reglas e índice de módulos al día sin reiniciar
        return self._quien(q)

    def _quien(self, q):
        """(real, persona_vista, error). Producción: correo de Cloudflare Access. Prototipo: ?yo= / X-RO-Yo."""
        def canonica(pid):
            # 259: la sesión nunca hereda roles de una persona retirada ni el
            # primer registro de una identidad duplicada. Autoridad actual, sin alias.
            personas = E.crudo.get("personas")
            if not isinstance(pid, str) or not pid or not isinstance(personas, list):
                return None
            candidatas = [p for p in personas if isinstance(p, dict) and p.get("id") == pid]
            if len(candidatas) != 1:
                return None
            actual = candidatas[0]
            return actual if actual.get("estado") == "activo" and actual.get("activo") is not False else None

        servidor = ACCESO.activo()
        peer = getattr(self, 'client_address', None)
        if not servidor and (not isinstance(peer, (tuple, list)) or not peer or peer[0] not in ('127.0.0.1', '::1')):
            return None, None, (403, "El prototipo sólo admite conexiones locales.")
        if servidor:   # C5 · servidor: el correo sale SOLO del sello firmado de Access (E49); ?yo= y X-RO-Yo no valen
            correo, motivo = ACCESO.correo_validado(self.headers)
            if not correo:
                return None, None, (403, motivo)
        else:
            correo = None   # Local: una cabecera Access sin sello no acredita identidad.
        if correo:
            real = E.por_correo(correo)
            if not real:
                return None, None, (403, "Tu correo no está en la tabla de personas. Pídeselo a Mili o a Tomás.")
        else:
            galleta = self.galletas()
            # Ronda 6 (C2): sin identidad NO se entra como Tomás. 401 y la carcasa enseña «¿Quién eres?» (solo prototipo, 127.0.0.1).
            yo = self.headers.get("X-RO-Yo") or (q.get("yo") or [None])[0] or galleta.get("ro_yo")
            if not yo:
                return None, None, (401, "Sin identificar. En el prototipo, elige quién eres; en el servidor, entra por Cloudflare Access.")
            real = canonica(yo)
            if not real:
                return None, None, (403, "No existe esa persona.")
        # Ronda 6 (M7): solo entra quien está «activo». Dudosos, por incorporar y bajas, no, hasta que Mili los active.
        real = canonica(real.get("id")) if isinstance(real, dict) else None
        if real is None:
            return None, None, (403, "Esta persona no está activa: Mili la activa en Ajustes › Personas.")
        como = self.headers.get("X-RO-Como") or (q.get("como") or [None])[0]
        if como is None and not correo and not self.headers.get("X-RO-Yo") and not q.get("yo"):
            como = self.galletas().get("ro_como") or None
        if como and como != real["id"]:
            vista = canonica(como)
            if vista is None:
                return None, None, (403, "La persona de esta vista no está activa o su identidad no es inequívoca.")
            cp = P.contexto(real, E.crudo)
            if not P.ver(real, {"tipo": "ver_como"}, cp)["ok"]:
                return None, None, (403, "«Ver como» es solo para Mili y Tomás.")
            return real, vista, None
        return real, real, None

    def galletas(self):
        """Identidad del prototipo en cookie (la pone app.js) para los fetch() de los módulos."""
        out = {}
        for trozo in (self.headers.get("Cookie") or "").split(";"):
            if "=" in trozo:
                k, v = trozo.strip().split("=", 1)
                out[k] = unquote(v)
        return out

    def host_ok(self):
        """Ronda 6 (C2): en local solo se atiende a 127.0.0.1 / localhost con el puerto propio (contra «DNS rebinding»)."""
        if ACCESO.activo():
            return True
        peer = getattr(self, 'client_address', None)
        if not isinstance(peer, (tuple, list)) or not peer or peer[0] not in ('127.0.0.1', '::1'):
            return False
        host = (self.headers.get("Host") or "").lower()
        puerto = self.server.server_address[1]
        return host in (f"127.0.0.1:{puerto}", f"localhost:{puerto}")

    def peticion_propia(self):
        """Ronda 6 (C2): todo POST lleva X-RO-App: 1, Content-Type JSON y, si trae Origin, el de la propia app."""
        if self.headers.get("X-RO-App") != "1":
            return "Falta la cabecera de la app (X-RO-App)."
        if not (self.headers.get("Content-Type") or "").lower().startswith("application/json"):
            return "Solo se acepta JSON."
        origen = self.headers.get("Origin")
        if origen:
            puerto = self.server.server_address[1]
            propios = {f"http://127.0.0.1:{puerto}", f"http://localhost:{puerto}"} | set(filter(None, (os.environ.get("RO_ORIGEN_APP") or "").split(",")))
            if origen not in propios:
                return "Origen no permitido."
        if (self.headers.get("Sec-Fetch-Site") or "same-origin") not in ("same-origin", "none"):
            return "Petición desde otra web."
        return None

    # ---------------------------------------------------------------- GET
    def do_HEAD(self):
        # 558: SimpleHTTPRequestHandler.send_head no pasa las puertas de GET.
        # Rechazo uniforme, sin resolver rutas ni abrir archivos y sin cuerpo HEAD.
        self.send_response(405)
        self.send_header("Allow", "GET, POST")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        url = urlparse(self.path)
        ruta = unquote(url.path)
        if not self.host_ok():
            return self.responder(403, {"error": "Host no permitido."})
        if ruta == "/api/elegir" and not ACCESO.activo():
            # «¿Quién eres?» del prototipo: solo en local y solo nombres y puestos de las personas activas.
            return self.responder(200, {"personas": [{"id": p["id"], "alias": p.get("alias"), "puestos": p.get("puestos")}
                                                     for p in E.crudo["personas"] if p.get("estado") == "activo"]})
        if ACCESO.activo() and not ruta.startswith("/api/"):   # C5: en el servidor ni la carcasa sale sin sello de Access
            if ruta == "/vivo":                                 # comprobación de salud de Render (sin datos)
                return self.responder(200, {"ok": True})
            if not ACCESO.correo_validado(self.headers)[0]:
                return self.responder(403, {"error": "Entra por la dirección de la app (Cloudflare Access)."})
        if not ruta.startswith("/api/"):
            return self.estatico(ruta)
        try:
            self.api_get(ruta, parse_qs(url.query))
        except Exception as e:
            traceback.print_exc()
            self.responder(500, {"error": "Error interno (el detalle queda en el registro del servidor)."})

    def index_versionado(self):
        """Ronda 14 (causas 2 y 7): index.html con el mapa de versiones, cada fichero propio con ?v=<huella>, las fuentes
        precargadas y la sesión pedida a la vez que el código. Sin caché (no-cache + ETag): es lo único que se pregunta."""
        try:
            html = leer_estatico(AQUI, "index.html")[0].decode('utf-8')
        except (OSError, ValueError):
            return self.responder(404, {"error": "No existe."})
        mapa, sha = mapa_versiones()

        def ver(m):
            rel = m.group(2)
            if ESTATICOS_PERMITIDOS.match(rel) and (AQUI / rel).is_file():
                return f'{m.group(1)}="{rel}?v={contenido_servido(rel)[1]}"'
            return m.group(0)
        html = re.sub(r'(src|href)="((?:modulos/|fuentes_web/)?[\w\-/]+\.(?:js|css|woff2|json))"', ver, html)
        html = html.replace("<!--MAPA-->", f'<script type="importmap">{mapa}</script>', 1)
        q = parse_qs(urlparse(self.path).query)
        yo = (q.get("yo") or [None])[0] or self.galletas().get("ro_yo")
        href = "api/sesion" if ACCESO.activo() else (f"api/sesion?yo={yo}" if yo and re.fullmatch(r"[\w\-]+", yo) else None)
        if href:
            html = html.replace("<!--PRECARGA-->", f'<link id="precarga-sesion" rel="preload" as="fetch" href="{href}" crossorigin>', 1)
        cuerpo = html.encode()
        etag = '"' + hashlib.sha1(cuerpo).hexdigest()[:24] + '"'
        self._csp = CSP.replace("script-src 'self'", f"script-src 'self' 'sha256-{sha}'")
        if (self.headers.get("If-None-Match") or "").strip() == etag:
            self.send_response(304)
            self.send_header("ETag", etag)
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            return
        cod = self.codificacion()
        if cod:
            cuerpo = comprimir(cuerpo, cod)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("ETag", etag)
        self.send_header("Vary", "Accept-Encoding, Cookie")
        if cod:
            self.send_header("Content-Encoding", cod)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def servir_logo(self, cid):
        """Ronda 14 (causa 6): /logos/<cliente>.jpg desde data/logos.json (en memoria), con caché de un año si ?v= casa.
        Los logos son comunes (todos ven nombre y logo de los 68): no hay recorte que hacer."""
        lg = logo_de(cid)
        if not lg:
            return self.responder(404, {"error": "Sin logo."})
        datos, tipo, huella = lg
        etag = f'"{huella}"'
        v = (parse_qs(urlparse(self.path).query).get("v") or [None])[0]
        cache = INMUTABLE if v == huella else "no-cache"
        if (self.headers.get("If-None-Match") or "").strip() == etag:
            self.send_response(304)
            self.send_header("ETag", etag)
            self.send_header("Cache-Control", cache)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("ETag", etag)
        self.send_header("Cache-Control", cache)
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def estatico(self, ruta):
        rel = ruta.lstrip("/") or "index.html"
        if rel == "index.html":
            return self.index_versionado()
        m_logo = re.fullmatch(r"logos/([\w\-]+)\.(?:jpg|png|webp|gif)", rel)
        if m_logo:
            return self.servir_logo(m_logo.group(1))
        # data/<carpeta>/<fichero>.json de un módulo (no los comunes ni _privado/): se sirve RECORTADO,
        # igual que /api/modulo/<carpeta>/<fichero>, con la identidad de la cookie del prototipo.
        m = re.fullmatch(r"data/([\w\-]+/[\w\-]+)\.json", rel)
        if m and "_privado" not in rel and not rel.startswith("data/clientes/"):
            try:
                return self.api_get(f"/api/modulo/{m.group(1)}", {})
            except Exception as e:
                traceback.print_exc()
                return self.responder(500, {"error": "Error interno (el detalle queda en el registro del servidor)."})
        if not ESTATICOS_PERMITIDOS.match(rel) or ".." in rel:
            # data/, historia/, local.db, *.py, *.sql, fuentes/… no se sirven nunca como fichero.
            return self.responder(403, {"error": "No se sirve como fichero. Los datos salen recortados de /api/."})
        if rel.endswith((".js", ".css", ".json", ".woff2")):
            return self.fichero_comprimido(rel)
        # También PNG/SVG usan la lectura segura, sin el lector de ficheros base.
        return self.fichero_comprimido(rel)

    def api_get(self, ruta, q):
        real, persona, err = self.quien(q)
        if err:
            return self.responder(err[0], {"error": err[1]})
        if persona["id"] == real["id"]:
            return self._api_get(ruta, q, real, persona)
        # Ronda 6 (C3): «ver como» = lo que ven LAS DOS personas; (M2) y lo leído queda en el rastro.
        try:
            apuntar_lectura_ver_como(real, persona, ruta)
        except Exception:
            return self.responder(503, {"error": "No se ha podido registrar la lectura en ver como. Inténtalo de nuevo."})
        with P.mirando_como(real, E.crudo):
            return self._api_get(ruta, q, real, persona)

    def _api_get(self, ruta, q, real, persona):
        if E.nucleo_bloqueado:
            return self.responder(503, {"error": "La puerta de secretos ha encontrado algo en los datos: no se sirve nada. Avisa a Tomás."})
        cp = P.contexto(persona, E.crudo)
        solo_lectura = persona["id"] != real["id"]

        if ruta == "/api/en-rojo/planes":
            code, dto = PLANES_FUEGOS_255.responder(sys.modules[__name__], real, persona, query=q)
            return self.responder(code, dto)

        if ruta == "/api/sesion":
            if solo_lectura:
                registrar(real["id"], "sesion", "ver_como", persona["id"], {"detalle": f"{real['alias']} ve como {persona['alias']} (solo lectura)"}, como=persona["id"])
            datos = logos_a_direcciones(P.recortar(persona, E.crudo))
            return self.responder(200, {
                # Ronda 14 (causa 1): qué pantalla ve cada puesto, para pintar el menú sin bajar el código de las 46.
                "modulos_puestos": PILOTO_LECTURA.modulos_disponibles(E.modulos),
                "servidor": True, "hora": ahora(),
                "real": {k: real.get(k) for k in P.PERSONA_PUBLICA},
                "persona": {k: persona.get(k) for k in P.PERSONA_PUBLICA},
                "soloLectura": solo_lectura or PILOTO_LECTURA.activo(),
                "pilotoLectura": PILOTO_LECTURA.activo(),
                "puedeVerComo": P.ver(real, {"tipo": "ver_como"}, P.contexto(real, E.crudo))["ok"],
                "datos": datos,
                "bloqueados": sorted(E.bloqueados) if P.ver(persona, {"tipo": "ver_como"}, cp)["ok"] else [],
            })

        m = re.fullmatch(r"/api/cliente/([\w\-]+)", ruta)
        if m:
            cid = m.group(1)
            puerta581 = puerta_cliente_581(real, persona, cid)
            if puerta581 is None:
                return self.responder(403, {"error": "El cliente o el ámbito actual de Ficha no está autorizado."})
            resumen = next((c for c in P.recortar(persona, E.crudo)["clientes"] if c["id"] == cid), None)
            if resumen is None:
                return self.responder(403, {"error": "El cliente no está disponible en este ámbito."})
            administracion581 = any(set(p['puestos']) <= set(P.REGLAS.get('ficha_solo_contrato', {}).get('puestos', []))
                                    for p in puerta581['ambito'][0])
            if puerta581['nivel'] == 'resumen' and not administracion581:
                if not cliente_vigente_581(real, persona, cid, puerta581):
                    return self.responder(403, {"error": "El ámbito cambió durante la lectura."})
                return self.responder(200, {"cliente": resumen, "fuentes": None, "nivel": "resumen"})
            fichero = DATA / "clientes" / f"{cid}.json"
            try:
                puerta581['marca581'] = _estado_fichero(fichero)
            except OSError:
                puerta581['marca581'] = None
            puerta581['fichero581'] = fichero
            rel = f"data/clientes/{cid}.json"
            aviso_dato = None
            try:
                doc, aviso_dato = leer_json_bueno(fichero) if fichero.exists() else (None, None)
            except DatoSecreto as e:
                return self.responder(503, {"error": str(e)})
            except DatoRoto:
                doc, aviso_dato = None, {"dato_de": None, "motivo": "La ficha de este cliente está a medio escribir: vuelve a probar en un minuto."}
            if (not cliente_vigente_581(real, persona, cid, puerta581)
                    or not documento_raiz_581(doc, 'clientes/' + cid, puerta581['ambito'], puerta581['niveles'])):
                return self.responder(403, {"error": "El ámbito o la referencia del cliente cambió durante la lectura."})
            res = {"cliente": resumen, "fuentes": recortar_ficha(persona, cp, cid, doc) if doc else None}
            if administracion581 and isinstance(res['fuentes'], dict):
                permitidas581 = set(P.REGLAS['ficha_solo_contrato'].get('fuentes', []))
                res['fuentes']['fuentes'] = {k: v for k, v in (res['fuentes'].get('fuentes') or {}).items() if k in permitidas581}
            if aviso_dato:
                res["_ultimo_dato_bueno"] = aviso_dato
            if not cliente_vigente_581(real, persona, cid, puerta581):
                return self.responder(403, {"error": "El ámbito cambió durante la lectura."})
            return self.responder(200, res)

        if ruta == "/api/indicadores":
            clave_ind = ("indicadores", real["id"], persona["id"], _estado_fichero(AQUI / "indicadores.json"), version_datos())
            guardada = CACHE_RESP.leer(clave_ind)
            if guardada:
                return responder_de_memoria(self, guardada)
            cat = json.loads((AQUI / "indicadores.json").read_text())
            if not P.ver(persona, {"tipo": "catalogo_indicadores"}, cp)["ok"]:
                mios = P.puestos_de(persona)
                cat["indicadores"] = [i for i in cat["indicadores"] if i["puesto"] in mios]
                cat["_meta"]["recortado"] = "Solo los indicadores de tus puestos."
            # R16 (N13): umbrales en euros solo para quien ve la inversión (o la cuota) en general; al resto, sin cifra.
            pu = P.puestos_de(persona)
            quita = P.importes_a_quitar(bool(pu & {"direccion", "operaciones", "proyectos", "administracion", "finanzas_direccion"}),
                                        bool(pu & {"direccion", "operaciones", "jefa_publicidad", "trafficker", "finanzas_direccion"}))
            if quita:
                cat = P.sin_importes(cat, quita)          # indicadores y umbrales firmados
            cuerpo = json.dumps(cat, ensure_ascii=False).encode()
            e = {"cuerpo": cuerpo, "etag": etag_de(clave_ind, cuerpo)}
            CACHE_RESP.guardar(clave_ind, e)
            return responder_de_memoria(self, e)

        if ruta == "/api/ajustes":
            nivel_ok = P.ver(persona, {"tipo": "ajustes_editar"}, cp)["ok"]
            es_rrhh = "rrhh" in P.puestos_de(persona)
            if not (nivel_ok or es_rrhh):
                return self.responder(403, {"error": "Ajustes es de Mili y Tomás (RRHH, en resumen)."})
            personas = E.crudo["personas"] if nivel_ok else [{k: p.get(k) for k in P.PERSONA_PUBLICA + ["horas_mes", "imputa_horas"]} for p in E.crudo["personas"]]
            with conectar() as con:
                decis = [dict(r) for r in con.execute("SELECT * FROM decisiones WHERE tipo='para_confirmar' ORDER BY id DESC").fetchall()]
                hist = [dict(r) for r in con.execute("SELECT * FROM historial ORDER BY n DESC LIMIT 200").fetchall()]
            return self.responder(200, {
                "puedeEditar": nivel_ok and not solo_lectura,
                "personas": personas,
                "asignaciones": E.crudo["asignaciones"] if nivel_ok else [],
                "para_confirmar": E.crudo["para_confirmar"] if nivel_ok else [],
                "clientes": [{"id": c["id"], "nombre": c["nombre"], "sin_account": c.get("sin_account"), "responsable_id": c.get("responsable_id")} for c in E.crudo["clientes"]],
                "decisiones": decis if nivel_ok else [], "historial": hist if nivel_ok else [],
                "sillas": P.REGLAS["sillas"], "puestos": P.REGLAS["puestos"],
                # Ronda 11 (A3): para que la pantalla no ofrezca lo que solo puede hacer Tomás.
                "puestos_solo_tomas": P.REGLAS.get("puestos_solo_tomas") or [],
                "realEsDireccion": "direccion" in real.get("puestos", []),
            })

        if ruta == "/api/rastro":
            from acciones_lectura_544 import ambito as ambito_lectura544, fila_visible as fila_lectura544, recortar_vistas as recortar_vistas544
            ambito_rastro = ambito_lectura544(E, P, ACT, real, persona)
            if ambito_rastro is None:
                return self.responder(403, {"error": "El ámbito actual del rastro no está disponible."})
            actuales, contextos, firma_rastro = ambito_rastro
            auditorias = [P.ver(p, {"tipo": "rastro_todo"}, c)["ok"] for p, c in zip(actuales, contextos)]
            mirando = real["id"] != persona["id"]
            todo = not mirando and all(auditorias)
            with conectar() as con:
                if mirando:
                    # 558.1: sólo el rastro de ESTA inspección, nunca la historia
                    # personal de la vista, aunque el real tenga auditoría completa.
                    filas = con.execute("SELECT * FROM registro WHERE quien=? AND como=? ORDER BY id DESC LIMIT 500",
                                        (real["id"], persona["id"])).fetchall()
                    acciones = []
                else:
                    limitados = [p["id"] for p, auditora in zip(actuales, auditorias) if not auditora]
                    clausulas = ["(quien=? OR como=?)" for _ in limitados]
                    where = " WHERE " + " AND ".join(clausulas) if clausulas else ""
                    parametros = tuple(pid for pid in limitados for _ in range(2))
                    filas = con.execute("SELECT * FROM registro" + where + " ORDER BY id DESC LIMIT 500", parametros).fetchall()
                    where_acciones = " WHERE " + " AND ".join("quien=?" for _ in limitados) if limitados else ""
                    acciones = con.execute("SELECT * FROM acciones" + where_acciones + " ORDER BY id DESC LIMIT 200", tuple(limitados)).fetchall()
            acciones = [r for r in acciones if fila_lectura544(r, E, P, ACT, ve_alguno,
                                                               actuales, contextos, persona["id"])]
            acciones = recortar_vistas544(acciones, P, lambda cid: quitar_para(actuales[1], contextos[1], cid),
                                         lambda vp, q: recortar_doc(vp, q), lambda: CLAVES_INVERSION, lambda: CLAVES_DINERO_CAPTACION)
            final_rastro = ambito_lectura544(E, P, ACT, real, persona)
            if final_rastro is None or final_rastro[2] != firma_rastro:
                return self.responder(403, {"error": "El ámbito del rastro cambió durante la lectura."})
            return self.responder(200, {"todo": todo, "registro": [dict(r) for r in filas], "acciones": [dict(r) for r in acciones]})

        if ruta == "/api/acciones":
            # Acciones de un módulo, para todos los que ven ese módulo (propuesta 4 de E6: el «dueño» que
            # pone Eulimar lo ve Fátima). Sin ?modulo=, solo las propias.
            mod = (q.get("modulo") or [None])[0]
            if not mod and real["id"] != persona["id"]:
                # La lista personal no es una cola de módulo compartida.
                return self.responder(200, {"modulo": None, "acciones": []})
            from acciones_lectura_544 import ambito as ambito_lectura544, fila_visible as fila_lectura544, recortar_vistas as recortar_vistas544
            def ambito_acciones538():
                return ambito_lectura544(E, P, ACT, real, persona)
            ambito = ambito_acciones538()
            if ambito is None:
                return self.responder(403, {"error": "El ámbito actual de las acciones no está disponible."})
            actuales, contextos, firma_acciones = ambito
            cp = contextos[1]  # La privacidad económica también usa cartera actual, no el contexto previo al IO.
            if mod and not all(ve_alguno(p, [mod]) for p in actuales):
                return self.responder(403, {"error": "Esa pantalla no es de tu puesto."})
            def fila_visible538(r):
                return fila_lectura544(r, E, P, ACT, ve_alguno, actuales, contextos, persona["id"])
            with conectar() as con:
                if mod:
                    if not ve_alguno(persona, [mod]):
                        return self.responder(403, {"error": "Esa pantalla no es de tu puesto."})
                    filas = con.execute("SELECT * FROM acciones WHERE modulo=? ORDER BY id DESC LIMIT 500", (mod,)).fetchall()
                    # Solo las de clientes que ve (D-P-BDJ); las que no son de un cliente, solo con nivel «todo» o si son suyas.
                    nivel = ve_alguno(persona, [mod])
                    filas = [r for r in filas if (r["cliente_id"] and P.ver(persona, {"tipo": "cliente_detalle", "cliente_id": r["cliente_id"]}, cp)["ok"])
                             or (not r["cliente_id"] and (nivel == "todo" or r["quien"] == persona["id"]))]
                else:
                    filas = con.execute("SELECT * FROM acciones WHERE quien=? ORDER BY id DESC LIMIT 500", (persona["id"],)).fetchall()
            # Autoría pasada no concede acceso actual al cliente ni a su contenido.
            filas = [r for r in filas if fila_visible538(r)]
            # A4 (2-oct): el objetivo del cliente lleva costes; su vista previa sale recortada como cualquier dato del cliente.
            filas = [dict(r) for r in filas]
            # La acción en cola no demuestra entrega. Solo añadimos estado y fecha
            # a las acciones que ya pasaron el recorte de permisos de arriba.
            with conectar() as con:
                hay_envios = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='envio_pasos'").fetchone()
                if hay_envios:
                    for r in filas:
                        envio = con.execute("SELECT p.estado, p.hora FROM envios e JOIN envio_pasos p ON p.envio_id=e.id WHERE e.accion_id=? ORDER BY p.id DESC LIMIT 1", (r["id"],)).fetchone()
                        if envio:
                            r["envio_estado"], r["envio_fecha"] = envio["estado"], envio["hora"]
            filas = recortar_vistas544(filas, P, lambda cid: quitar_para(persona, cp, cid),
                                      lambda vp, q: recortar_doc(vp, q), lambda: CLAVES_INVERSION, lambda: CLAVES_DINERO_CAPTACION)
            filas = recorte_importes_lectura588(filas, actuales, contextos)
            final = ambito_acciones538()
            if final is None or final[2] != firma_acciones:
                return self.responder(403, {"error": "El ámbito de las acciones cambió durante la lectura."})
            return self.responder(200, {"modulo": mod, "acciones": filas})

        if ruta == "/api/recarga":
            if not P.ver(persona, {"tipo": "recargar"}, cp)["ok"]:
                return self.responder(403, {"error": P.REGLAS["tipos"]["recargar"]["no"]})
            with conectar() as con:
                filas = [dict(r) for r in con.execute("SELECT * FROM recargas ORDER BY id DESC LIMIT 10")]
            for r in filas:
                r["pasos"] = json.loads(r["pasos"] or "[]")
            return self.responder(200, {"recargas": filas, "datos_de": (E.crudo.get("meta") or {}).get("generado")})

        if ruta == "/api/avisos":
            if not P.ver(persona, {"tipo": "recargar"}, cp)["ok"]:
                return self.responder(403, {"error": P.REGLAS["tipos"]["recargar"]["no"]})
            with conectar() as con:
                filas = [dict(r) for r in con.execute("SELECT * FROM avisos ORDER BY id DESC LIMIT 100")]
            return self.responder(200, {"tope_dia": TOPE_AVISOS_DIA, "avisos": filas,
                                        "nota": "La notificación real (escritorio y móvil) llega con W1. En el prototipo se ven aquí."})

        if ruta == "/api/decisiones":
            from acciones_lectura_544 import ambito as ambito_lectura588
            ambito_decisiones = ambito_lectura588(E, P, ACT, real, persona)
            if ambito_decisiones is None:
                return self.responder(403, {"error": "El ámbito actual de las decisiones no está disponible."})
            actuales, contextos, firma_decisiones = ambito_decisiones
            decisiones = decisiones_para(actuales[1], contextos[1])
            decisiones = recorte_importes_lectura588(decisiones, actuales, contextos)
            final_decisiones = ambito_lectura588(E, P, ACT, real, persona)
            if final_decisiones is None or final_decisiones[2] != firma_decisiones:
                return self.responder(403, {"error": "El ámbito de las decisiones cambió durante la lectura."})
            return self.responder(200, {"decisiones": decisiones, "hora": ahora()})

        # R15 (A5) · índice del buscador por persona: solo lo que ya le llega recortado por la puerta de cada fichero.
        if ruta in ("/api/buscar/indice", "/api/buscar"):
            clave_b = ("buscar", real["id"], persona["id"], marcas_buscar(persona), version_datos())
            guardada = CACHE_RESP.leer(clave_b)
            if guardada:
                indice = None
            else:
                indice = indice_busqueda(real, persona, cp)
                cuerpo = json.dumps({"generado": ahora(), "filas": indice}, ensure_ascii=False).encode()
                guardada = {"cuerpo": cuerpo, "etag": etag_de(clave_b, cuerpo)}
                CACHE_RESP.guardar(clave_b, guardada)
            if ruta == "/api/buscar/indice":
                return responder_de_memoria(self, guardada)
            if indice is None:
                indice = json.loads(guardada["cuerpo"])["filas"]
            q_txt = ((q.get("q") or [""])[0])[:120]
            return self.responder(200, {"q": q_txt, "filas": buscar_en(indice, q_txt)})

        # R15 (A6) · contadores del menú que se sacan mejor aquí que bajando el fichero entero (Producción: 0,9 MB).
        # «Vencidas en tu mano» = personas[].vencidas del fichero ya recortado: la cifra de «Mi cola» en Producción y Mi día.
        if ruta == "/api/contadores":
            clave_c = ("contadores", real["id"], persona["id"], marcas_buscar(persona), version_datos(), P.hoy_iso())   # R16c: cambia a medianoche
            guardada = CACHE_RESP.leer(clave_c)
            if not guardada:
                res = {"produccion": None}
                d = modulo_recortado(real, persona, cp, "produccion/produccion")
                if isinstance(d, dict):
                    res["produccion"] = vencidas_al_dia(d, persona["id"], P.hoy_iso())
                cuerpo = json.dumps(res).encode()
                guardada = {"cuerpo": cuerpo, "etag": etag_de(clave_c, cuerpo)}
                CACHE_RESP.guardar(clave_c, guardada)
            return responder_de_memoria(self, guardada)

        # Mi perfil (3-oct) · nombre, puesto, jefe y zona horaria (altas_personas.py → perfil; en «ver como», solo lectura).
        if ruta == "/api/perfil":
            AL = sys.modules.get("altas_personas")
            c, r = AL.perfil(real, persona, (q.get("id") or [""])[0]) if AL else (503, {"error": "Mi perfil no está cargado en este servidor."})
            return self.responder(c, r)

        # R15 (A6) · «Mis clientes» fijados (por persona; en «ver como», los de la persona vista, solo lectura).
        if ruta == "/api/preferencias":
            fij = leer_preferencia(persona["id"], "fijados")
            vis = {c["id"] for c in P.recortar(persona, E.crudo)["clientes"] if c.get("detalle")} if fij else set()
            return self.responder(200, {"fijados": [c for c in fij if c in vis] if fij is not None else None, "tope": TOPE_FIJADOS})

        # R15 (A7) · «Algo va mal / Tengo una idea»: Mili y Tomás ven todos; el resto, los suyos.
        if ruta in ("/api/opiniones", "/api/opiniones/captura"):
            todas = P.ver(persona, {"tipo": "opiniones_ver"}, cp)["ok"] and P.ver(real, {"tipo": "opiniones_ver"}, P.contexto(real, E.crudo))["ok"]
            with conectar() as con:
                if ruta == "/api/opiniones/captura":
                    oid = (q.get("id") or ["0"])[0]
                    r = con.execute("SELECT * FROM opiniones WHERE id=?", (int(oid) if str(oid).isdigit() else 0,)).fetchone()
                    if not r or not (todas or r["quien"] == persona["id"]):
                        return self.responder(403 if r else 404, {"error": "Esa opinión no es tuya."})
                    from capturas_opiniones_565 import permiso as permiso_captura565
                    autorizacion = permiso_captura565(E, P, ACT, PANEL_PRIVADO_249, real, persona, r)
                    if autorizacion is None:
                        return self.responder(403, {"error": "La captura no está disponible en tu ámbito actual."})
                    salida = opinion_a_json(r, con_captura=True)
                    if permiso_captura565(E, P, ACT, PANEL_PRIVADO_249, real, persona, r) != autorizacion:
                        return self.responder(403, {"error": "La captura no está disponible en tu ámbito actual."})
                    return self.responder(200, salida)
                filas = con.execute("SELECT * FROM opiniones " + ("" if todas else "WHERE quien=? ") + "ORDER BY id DESC LIMIT 300",
                                    () if todas else (persona["id"],)).fetchall()
                # R16 (primera semana): su jefe directo sabe SOLO si cada persona de su equipo ya mandó algún «Algo va mal»
                # (sí/no y el día), nunca el texto ni la captura.
                suyos = [p["id"] for p in E.crudo["personas"] if p.get("jefe") == persona["id"] and p.get("activo")]
                equipo = {}
                for pid in suyos:
                    r1 = con.execute("SELECT min(creada) FROM opiniones WHERE quien=?", (pid,)).fetchone()[0]
                    equipo[pid] = {"alguna": bool(r1), "primera": (r1 or "")[:10] or None}
            return self.responder(200, {"todas": todas, "opiniones": [opinion_a_json(r) for r in filas], "equipo": equipo})

        if ruta == "/api/respuestas_mili":
            if not P.ver(persona, {"tipo": "ajustes_editar"}, cp)["ok"]:
                return self.responder(403, {"error": "Solo Mili y Tomás."})
            with conectar() as con:
                filas = con.execute("SELECT * FROM decisiones WHERE tipo='para_confirmar' ORDER BY id").fetchall()
            anuladas = {r["anula_a"] for r in filas if r["anula_a"]}
            resp = []
            for r in filas:
                if r["id"] not in anuladas and not r["anula_a"] and r["respuesta"]:
                    x = json.loads(r["respuesta"])
                    resp.extend(x if isinstance(x, list) else [x])
            return self.responder(200, {"_meta": {"generado": ahora(), "origen": "Ajustes › Para confirmar (local.db)",
                                                  "uso": "Guárdalo como 20_FASE0_DATOS/respuestas_mili.json y lanza build_data.py"},
                                        "respuestas": resp})

        m = re.fullmatch(r"/api/modulo/([\w\-/]+)", ruta)
        if m:
            rel = m.group(1)
            # R15 (A5): la puerta del fichero es una función (la usa también el índice del buscador, /api/buscar/indice).
            pm = puerta_modulo(real, persona, rel)
            if pm.get("error"):
                return self.responder(pm["error"][0], {"error": pm["error"][1]})
            fichero, conf, nivel = pm["fichero"], pm["conf"], pm["nivel"]
            solo_todo, filas_lead = tuple(conf.get("solo_todo_sin_cliente", [])), tuple(conf.get("filas_lead", []))
            if not fichero.exists():
                return self.responder(404, {"error": f"No existe data/{rel}.json"})
            # La puerta se ejecuta antes de la memoria HTTP, incluso tras un bloqueo anterior.
            try:
                doc_mod, aviso_dato = leer_json_bueno(fichero)
            except DatoRoto as e:
                return self.responder(503, {"error": str(e)})
            if not modulo_vigente_581(real, persona, rel, pm, doc_mod):
                return self.responder(403, {"error": "El ámbito o el cliente de estos datos no está autorizado."})
            # Ronda 14 (causas 4 y 8): lo ya recortado para ESTA persona real + vista, este fichero (fecha y tamaño) y esta
            # versión de reglas, base y módulos sale de la memoria, con su ETag. Los nombres de leads de su dueño (que dejan
            # rastro cada vez) y el «último dato bueno» no se guardan.
            try:
                marca = _estado_fichero(fichero)
            except OSError:
                marca = None
            clave_mod = ("modulo", real["id"], persona["id"], rel, marca, nivel, version_datos(),
                         hashlib.sha256(pm['firma581'].encode()).hexdigest())
            guardable = marca is not None and rel != 'agenda/agenda' and not (rel == 'produccion/produccion' and (os.environ.get('RO_EVIDENCIA_PRODUCCION_275') or os.environ.get('RO_COMPARACION_SEMANAL_296') or os.environ.get('RO_PLANNING_TRANSICIONES_681'))) and not (conf.get("nombres_dueno") and not solo_lectura)
            guardada = CACHE_RESP.leer(clave_mod) if guardable and not aviso_dato else None
            if guardada:
                if not modulo_vigente_581(real, persona, rel, pm, doc_mod):
                    return self.responder(403, {"error": "El ámbito cambió durante la lectura."})
                return responder_de_memoria(self, guardada)
            salida = ACT.quitar_bajas(recortar_modulo(persona, cp, doc_mod, nivel, solo_todo, filas_lead, conf), rel)   # bajas solo en histórico
            if rel == 'produccion/produccion' and not aviso_dato:
                salida = EVIDENCIA_PRODUCCION_287.enriquecer287(salida, sys.modules[__name__], real, persona)
                import controlador_planning_681 as PLANNING_681
                salida = PLANNING_681.enriquecer681(salida, sys.modules[__name__], real, persona)
            if rel == 'produccion/produccion' and salida is None:
                return self.responder(403, {"error": "El ámbito cambió durante la lectura de planificación."})
            if rel == 'agenda/agenda':
                salida = AGENDA_ZOOM_API.disponibilidad(salida, real, persona)
            if conf.get("nombres_dueno") and not solo_lectura:   # F-10: quien trabaja el lead ve su nombre sin pulsar nada
                salida = nombres_para_su_dueno(persona, real, conf["nombres_dueno"], salida, rel, cp)
            if aviso_dato and isinstance(salida, dict):
                salida = {**salida, "_ultimo_dato_bueno": aviso_dato}
            if not modulo_vigente_581(real, persona, rel, pm, doc_mod):
                return self.responder(403, {"error": "El ámbito cambió durante la lectura."})
            if guardable and not aviso_dato:
                cuerpo = json.dumps(salida, ensure_ascii=False).encode()
                e = {"cuerpo": cuerpo, "etag": etag_de(clave_mod, cuerpo)}
                CACHE_RESP.guardar(clave_mod, e)
                return responder_de_memoria(self, e)
            return self.responder(200, salida)

        if ruta == "/api/rastro/verificar":     # ronda 6 (M3): ¿la cadena del rastro está entera?
            if "direccion" not in P.puestos_de(persona):
                return self.responder(403, {"error": "Solo dirección."})
            desde = (q.get("desde") or [None])[0]
            if desde not in (None, "anotado") and not str(desde).isdigit():
                return self.responder(400, {"error": "«desde» es un número de fila o «anotado»."})
            bien, rota, n = verificar_rastro(desde)
            res = {"ok": bien, "primera_fila_rota": rota, "filas_encadenadas": n}
            if desde is None:   # ronda 11: además, desde la última anotación y las anclas diarias
                b2, r2, n2 = verificar_rastro("anotado")
                ok_a, malas, na = comprobar_anclas()
                res.update({"tras_anotacion": {"desde": fila_tras_anotacion(), "ok": b2, "primera_fila_rota": r2, "filas": n2},
                            "anclas": {"ok": ok_a, "comprobadas": na, "malas": malas}})
            return self.responder(200, res)

        if ruta == "/api/salud":
            if "direccion" not in P.puestos_de(persona):
                return self.responder(403, {"error": "Solo dirección."})
            with conectar() as con:
                cuenta = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("registro", "historial", "acciones", "decisiones", "incidencias", "personas", "asignaciones", "docs")}
            return self.responder(200, {"bloqueados": E.bloqueados, "foto": E.foto, "tablas": cuenta})

        return self.responder(404, {"error": "No existe esa ruta de la API."})

    # ---------------------------------------------------------------- POST
    def do_POST(self):
        url = urlparse(self.path)
        if not self.host_ok():
            return self.responder(403, {"error": "Host no permitido."})
        motivo = self.peticion_propia()
        if motivo:
            return self.responder(403, {"error": motivo})
        try:
            q = parse_qs(url.query)
            real, persona, err = self.quien(q)
            if err:
                return self.responder(err[0], {"error": err[1]})
            if persona["id"] == real["id"]:
                self.api_post(unquote(url.path), real, persona, self.cuerpo())
            else:
                with P.mirando_como(real, E.crudo):     # C3: también aquí, lo que ven las dos
                    self.api_post(unquote(url.path), real, persona, self.cuerpo())
        except Exception as e:
            traceback.print_exc()
            self.responder(500, {"error": "Error interno (el detalle queda en el registro del servidor)."})

    def validar_accion(self, real, persona, b):
        """Permisos y forma de una acción; reutilizable por lotes sin escribir acciones ni despachar herramientas."""
        if real["id"] != persona["id"]:
            return None, (403, {"error": "Estás en «ver como»: es solo lectura. No se escribe nada."})
        cp = P.contexto(persona, E.crudo)
        tipo, herr = str(b.get("tipo") or ""), str(b.get("herramienta") or "")
        # Ronda 8 (D-P-PER2 a): la acción va a nombre de un módulo y quien la manda tiene que ver ese módulo
        # (en «ver como», el mínimo de las dos personas). Sin módulo, o con uno que no ve, no entra.
        mod_acc = str(b.get("modulo") or "")
        if not mod_acc or mod_acc not in E.modulos:
            return None, (400, {"error": "Falta el módulo de la acción (o no existe)."})
        if not ve_alguno(persona, [mod_acc]):
            return None, (403, {"error": "No puedes mandar acciones desde una pantalla que no ves."})
        # 536: la propuesta general de CRM es una intención local de su jefatura,
        # no una acción de cartera ni una reasignación ejecutada.
        if tipo == "proponer_reasignacion":
            if (mod_acc != "salud-crm" or herr != "app" or b.get("objeto") != "Subcuentas sin especialista"
                    or b.get("cliente_id") is not None or not b.get("intencion_id")):
                return None, (403, {"error": "La propuesta general de CRM no corresponde a este contexto."})
            for identidad in (real, persona):
                filas = [p for p in E.crudo.get("personas") or []
                         if isinstance(p, dict) and p.get("id") == identidad.get("id")]
                roles = identidad.get("puestos")
                if (len(filas) != 1 or filas[0].get("estado") != "activo"
                        or filas[0].get("activo") is False
                        or identidad.get("estado") != "activo" or identidad.get("activo") is False
                        or not isinstance(roles, list) or not roles
                        or not all(isinstance(r, str) and r in P.PUESTO for r in roles)
                        or len(set(roles)) != len(roles)
                        or not isinstance(filas[0].get("puestos"), list)
                        or filas[0]["puestos"] != roles
                        or P.nivel_modulo(filas[0], E.modulos.get("salud-crm", {})) != "todo"):
                    return None, (403, {"error": "La propuesta general necesita la jefatura actual de CRM."})
        permitidas = P.REGLAS.get("acciones_permitidas", {})
        if herr not in permitidas.get("_herramientas", []) or tipo not in (permitidas.get("*", []) + permitidas.get(b.get("modulo") or "", [])):
            return None, (400, {"error": f"Acción no permitida ({herr}/{tipo}). Se añade a «acciones_permitidas» de reglas_permisos.json."})
        if tipo == "decision_nueva":
            return None, (400, {"error": "Sube la decisión desde su formulario de Decisiones."})
        for campo in ("prueba", "enlace", "url"):
            if b.get(campo) and not P.enlace_seguro(b[campo]):
                return None, (400, {"error": "Enlace no válido (solo http, https, mailto, tel o sip)."})
        if isinstance(b.get("vista_previa"), (dict, list)) and _enlaces_malos(b["vista_previa"]):
            return None, (400, {"error": "Enlace no válido en la vista previa (solo http, https, mailto, tel o sip)."})
        if tipo == "decidir":                               # A5: solo el destinatario contesta
            did = (b.get("vista_previa") or {}).get("decision_id") or b.get("objeto")
            tipo_dec = tipo_de_decision(did)
            if not tipo_dec or not puede_contestar(real, tipo_dec):
                return None, (403, {"error": "Esta decisión la contesta su destinatario (Tomás o Coti)."})
        # Ronda 11 (M1): además de la pantalla, algunos tipos exigen puesto (a la persona REAL): un account no encola
        # bajas, cobros reclamados ni quitar accesos.
        solo_puestos = (P.REGLAS.get("acciones_solo_puestos") or {}).get(tipo)
        if solo_puestos and not (set(real.get("puestos", [])) & set(solo_puestos)):
            registrar_agrupado(real["id"], "acciones", "denegado", f"{herr}/{tipo}", {"motivo": "tipo de acción no permitido a su puesto"})
            return None, (403, {"error": f"«{tipo}» no es de tu puesto."})
        # A4 (2-oct): el objetivo del cliente y el semáforo del lunes, solo su account, operaciones y dirección (regla por cliente).
        regla_cli = (P.REGLAS.get("acciones_regla_cliente") or {}).get(tipo)
        cli_nuevo = any(x["id"] == b.get("cliente_id") and x.get("nuevo") for x in E.crudo["clientes"])   # en alta: lo dice la base, no el navegador
        if regla_cli and (not b.get("cliente_id") or not P.ver(persona, {"tipo": regla_cli, "cliente_id": b.get("cliente_id"), "cliente_nuevo": cli_nuevo}, cp)["ok"]):
            registrar_agrupado(real["id"], "acciones", "denegado", f"{herr}/{tipo}", {"motivo": f"regla {regla_cli}", "cliente_id": b.get("cliente_id")})
            return None, (403, {"error": (P.REGLAS["tipos"].get(regla_cli) or {}).get("no") or "No puedes hacer esto en este cliente."})
        # R14 (B2) · Aprobar / Pedir cambios en una pieza: la pieza y su cliente los saca el servidor de produccion.json;
        # solo quien la revisa según revision_piezas (nunca su autor); pedir cambios exige decir qué cambiar.
        if tipo in ("pieza_aprobar", "pieza_pedir_cambios"):
            pieza = pieza_en_revision(b.get("objeto"))
            if not pieza:
                return None, (403, {"error": "Esa pieza no está esperando revisión (o no se puede leer Producción)."})
            if not puede_revisar_pieza(real, pieza, P.contexto(real, E.crudo)):
                registrar_agrupado(real["id"], "acciones", "denegado", f"{herr}/{tipo}", {"motivo": "no revisa esta pieza", "objeto": str(b.get("objeto"))[:40]})
                return None, (403, {"error": "Esta pieza no la revisas tú (o es tuya: nadie se aprueba a sí mismo)."})
            if tipo == "pieza_pedir_cambios" and len(str((b.get("vista_previa") or {}).get("comentario") or b.get("texto") or "").strip()) < 3:
                return None, (400, {"error": "Pedir cambios necesita decir qué hay que cambiar."})
            b["cliente_id"] = pieza["cli"] or None
        # 603: referencias de proveedor exactas; desconocidas o ambiguas se deniegan.
        # App conserva referencias globales, pero ticket/cliente reconocido decide
        # el CID. El cuerpo no puede disfrazar una referencia ajena como propia.
        if herr in ("app", "desk", "whatsapp", "ghl"):
            cid_srv, conocido, invalido = referencia_accion603(herr, tipo, b.get("objeto"))
            if invalido or herr != "app" and not conocido:
                return None, (403, {"error": "La referencia no existe inequívocamente en su fuente actual."})
            if conocido:
                if b.get("cliente_id") not in (None, "") and b["cliente_id"] != cid_srv:
                    return None, (403, {"error": "El cliente no corresponde a esta referencia."})
                b["cliente_id"] = cid_srv
        if tipo == "responder":
            if herr not in ("desk", "whatsapp", "ghl"):
                return None, (403, {"error": "Desde la app solo se contesta a un ticket de Desk, un grupo de WhatsApp o un contacto de GHL."})
            if not b.get("cliente_id") or not P.ver(persona, {"tipo": "responder_cliente", "cliente_id": b["cliente_id"]}, cp)["ok"]:
                return None, (403, {"error": P.REGLAS["tipos"]["responder_cliente"]["no"]})
        cli_tarea = None
        # R16 (N12): un paso de «Tu primera semana» solo de la propia persona.
        if tipo == "primera_semana_paso" and not str(b.get("objeto") or "").startswith(f"{real['id']}:"):
            return None, (403, {"error": "Los pasos de tu primera semana son tuyos: «<tu id>:<paso>»."})
        # R16 (N4): lo que tiene efecto fuera (WhatsApp, correo, llamadas, GHL, Metricool, Zoom, chat de ClickUp…)
        # exige un cliente que la persona LLEVE; el destinatario lo pone el servidor desde el cliente, nunca una
        # dirección o un teléfono escritos en el navegador.
        efecto = P.REGLAS.get("acciones_con_efecto_fuera") or {}
        # 3-oct (setters_srv.py): un lead de la subcuenta de RO de ESA setter (comprobado allí, nunca por el navegador) no es un cliente.
        if not b.get("_lead_ro") and (tipo in (efecto.get("tipos") or []) or herr in (efecto.get("herramientas") or [])):
            motivo = None
            if herr in ("whatsapp", "ghl") and cliente_de_objeto(herr, b.get("objeto")) is None and tipo in (efecto.get("tipos_destinatario") or []):
                motivo = "No sé a quién va (no es un grupo de cliente ni un contacto del CRM): el destinatario lo pone el servidor."
            elif tipo in (efecto.get("tipos_destinatario") or []) and RX_DIRECCION_CRUDA.search(str(b.get("objeto") or "").strip()):
                motivo = "No se escribe a una dirección o un teléfono a mano: elige el cliente y el servidor pone el destinatario."
            elif not b.get("cliente_id"):
                motivo = "Esta acción sale fuera de la app: necesita el cliente."
            elif not lleva_cliente(real, b["cliente_id"], P.contexto(real, E.crudo)):
                motivo = "Solo lo hace quien lleva ese cliente (su account o su equipo), operaciones o dirección."
            if motivo:
                registrar_agrupado(real["id"], "acciones", "denegado", f"{herr}/{tipo}", {"motivo": motivo[:80], "cliente_id": b.get("cliente_id")})
                return None, (403, {"error": motivo})
        # R16 (N4): en ClickUp, una tarea que espera revisión solo cambia con «Aprobar» o «Pedir cambios» (pieza_*), y una
        # tarea se mueve o se comenta solo si es tuya (o de tu equipo, o eres operaciones o dirección).
        if herr == "clickup" and tipo in (efecto.get("clickup_tarea") or []):
            if tipo != "comentario" and pieza_en_revision(b.get("objeto")):
                registrar_agrupado(real["id"], "acciones", "denegado", f"{herr}/{tipo}", {"motivo": "saltarse la revisión", "objeto": str(b.get("objeto"))[:40]})
                return None, (403, {"error": "Esa pieza espera revisión: solo cambia con «Aprobar» o «Pedir cambios» de quien la revisa."})
            t = tarea_de_produccion(b.get("objeto"))
            if not t:
                return None, (403, {"error": "No encuentro esa tarea en Producción: no se mueve desde la app."})
            jefes = {(E.persona(a) or {}).get("jefe") for a in t["autores"] if a}
            if not (real["id"] in t["autores"] or real["id"] in jefes or set(real.get("puestos", [])) & {"direccion", "operaciones"}):
                registrar_agrupado(real["id"], "acciones", "denegado", f"{herr}/{tipo}", {"motivo": "tarea ajena", "objeto": str(b.get("objeto"))[:40]})
                return None, (403, {"error": "Esa tarea no es tuya ni de tu equipo."})
            cli_tarea = t["cli"]
        cid = b.get("cliente_id")
        if herr == "clickup" and tipo in (efecto.get("clickup_tarea") or []):
            # La tarea decide el cliente ANTES de autorizarlo; el cuerpo no cambia su cartera.
            if cid not in (None, "") and cid != cli_tarea:
                return None, (403, {"error": "El cliente no corresponde a esta tarea."})
            cid = cli_tarea
        if cid:
            actuales = []
            for identidad in (real, persona):
                filas = [p for p in E.crudo.get("personas") or [] if p.get("id") == identidad.get("id")]
                if len(filas) != 1 or filas[0].get("estado") != "activo" or filas[0].get("activo") is False:
                    return None, (403, {"error": "La identidad ya no está activa."})
                actuales.append(filas[0])
            clientes = [c for c in E.crudo.get("clientes") or [] if c.get("id") == cid]
            if len(clientes) != 1 or ACT.es_activo_id(cid) is not True or not all(P.ver(p, {"tipo": "cliente_detalle", "cliente_id": cid}, P.contexto(p, E.crudo))["ok"] for p in actuales):
                return None, (403, {"error": "No puedes actuar sobre un cliente que no llevas activo."})
        b["cliente_id"] = cid  # La cola recibe exclusivamente la identidad autorizada por el servidor.
        if b.get("tipo") == "responder" and cid and not P.ver(persona, {"tipo": "responder_cliente", "cliente_id": cid}, cp)["ok"]:
            return None, (403, {"error": P.REGLAS["tipos"]["responder_cliente"]["no"]})
        for campo in ("herramienta", "tipo", "objeto"):
            if not b.get(campo):
                return None, (400, {"error": f"Falta «{campo}»."})
        return cid, None

    def api_post(self, ruta, real, persona, b):
        solo_lectura = persona["id"] != real["id"]
        cp = P.contexto(persona, E.crudo)
        # «Ver como» es solo lectura. Única excepción: «ver datos» (contactos, chat, mensajes, leads), que no escribe
        # nada fuera del rastro y que Mili y Tomás necesitan para revisar lo que ve cada uno (D-P · M4).
        if solo_lectura and ruta != "/api/ver_dato":
            return self.responder(403, {"error": "Estás en «ver como»: es solo lectura. No se escribe nada."})

        if ruta == "/api/en-rojo/planes":
            code, dto = PLANES_FUEGOS_255.responder(sys.modules[__name__], real, persona, cuerpo=b)
            return self.responder(code, dto)

        if ruta == "/api/rastro":
            if not tope_rastro_navegador(real["id"]):
                return self.responder(429, {"error": "Demasiadas anotaciones en un minuto: espera un poco."})
            accion = str(b.get("accion") or "evento")[:60]
            # Ronda 6 (M1): el navegador solo escribe acciones de su lista blanca; las sensibles las escribe el servidor.
            if accion in P.REGLAS.get("rastro_solo_servidor", []):
                return self.responder(403, {"error": "Esa acción solo la apunta el servidor."})
            if accion not in P.REGLAS.get("rastro_navegador", []):
                accion = "nav:" + re.sub(r"[^a-z0-9_]", "", accion.lower())[:40]
            if accion == "no_aplica" and not (b.get("motivo") or "").strip():
                return self.responder(400, {"error": "«No aplica» necesita un motivo."})
            # R16 (N9): el navegador solo apunta en la colección de una pantalla que ve (o «app»); las colecciones del
            # servidor (sueldos, leads, contactos, opiniones, acciones…) no se fingen, ni se nombra un almacén privado.
            col = str(b.get("modulo") or b.get("coleccion") or "app")
            if col != "app" and (col not in E.modulos or not ve_alguno(real, [col])):
                registrar_agrupado(real["id"], "rastro", "denegado", col[:40], {"motivo": "colección ajena desde el navegador"})
                return self.responder(403, {"error": "Desde el navegador solo se apunta en una pantalla que ves."})
            if "_privado" in str(b.get("objeto") or b.get("clave") or "") or len(json.dumps(b.get("datos"), ensure_ascii=False, default=str)) > 4000:
                return self.responder(400, {"error": "Anotación no válida (almacén privado o demasiado larga)."})
            if b.get("anula_a") is not None and not re.fullmatch(r"\d{1,12}", str(b.get("anula_a"))):
                return self.responder(400, {"error": "«anula_a» tiene que ser el número de una fila."})   # R16 (B1)
            if b.get("anula_a"):
                with conectar() as con:
                    previa = con.execute("SELECT quien, coleccion FROM registro WHERE id=?", (int(b["anula_a"]),)).fetchone()
                if not previa or previa["quien"] != real["id"] or previa["coleccion"] != (b.get("modulo") or b.get("coleccion") or "app"):
                    return self.responder(403, {"error": "Solo se anula una fila propia de la misma pantalla."})
            rid = registrar(real["id"], b.get("modulo") or b.get("coleccion") or "app", accion, b.get("objeto") or b.get("clave"),
                            b.get("datos") if "datos" in b else {k: v for k, v in b.items() if k not in ("accion", "modulo", "objeto", "clave", "motivo", "anula_a")},
                            b.get("motivo"), anula_a=b.get("anula_a"))
            return self.responder(200, {"ok": True, "id": rid, "hora": ahora()})

        if ruta == "/api/acciones":
            cid, error = self.validar_accion(real, persona, b)
            if error:
                return self.responder(*error)
            import triaje_guardia_445 as triaje445
            es_triaje445 = triaje445.aplica(b)
            if es_triaje445 and "intencion_id" not in b:
                return self.responder(400, {"error": "El reparto necesita una intención UUID durable."})
            if es_triaje445 and not triaje445.adaptador_disponible():
                return self.responder(503, {"error": "La exclusión atómica de este adaptador de reparto no está validada."})
            clave_rep, previa = (None, None) if "intencion_id" in b else (accion_repetida(real["id"], b) or (None, None))
            if previa:   # ronda 11 (M1): doble clic o bucle → la misma fila, sin otra
                return self.responder(200, {"ok": True, "id": previa, "estado": "simulada", "repetida": True,
                                            "vista_previa": b.get("vista_previa"), "texto": b.get("texto")})
            from intenciones_acciones import guardar as guardar_intencion, iniciar as iniciar_intencion, ConflictoIntencion, PersistenciaNoDisponible, RechazoAccion
            guardia_triaje445 = None
            def insertar_accion(con):
                triaje445.sin_previa(con, guardia_triaje445)
                vp_transicion = b.get("vista_previa")
                if isinstance(vp_transicion, dict) and vp_transicion.get("transicion_tablero") is True:
                    import mi_trabajo as trabajo_transiciones
                    error_transicion = trabajo_transiciones.validar_transicion_en_transaccion(con, real, b)
                    if error_transicion:
                        raise RechazoAccion(*error_transicion)
                if isinstance(vp_transicion, dict) and vp_transicion.get("transicion_produccion") is True:
                    import transiciones_produccion_208 as produccion_transiciones
                    error_transicion = produccion_transiciones.validar_en_transaccion(con, real, b)
                    if error_transicion:
                        raise RechazoAccion(*error_transicion)
                cur = con.execute("INSERT INTO acciones (quien, herramienta, tipo, objeto, cliente_id, modulo, texto, vista_previa, estado, detalle) VALUES (?,?,?,?,?,?,?,?, 'simulada', ?)",
                                  (real["id"], b["herramienta"], b["tipo"], str(b["objeto"]), cid, b.get("modulo"), b.get("texto"),
                                   json.dumps(b.get("vista_previa"), ensure_ascii=False), "Prototipo: no se ha llamado a ninguna API. Se ejecutará con W1."))
                return cur.lastrowid
            repetida_intencion = False
            try:
                with conectar() as con:
                    if "intencion_id" in b:
                        iniciar_intencion(con)
                        if es_triaje445:
                            guardia_triaje445 = triaje445.preparar(sys.modules[__name__], con, real, persona, b)
                        aid, repetida_intencion = guardar_intencion(con, real["id"], b, insertar_accion)
                        if es_triaje445:
                            triaje445.revalidar(sys.modules[__name__], con, real, persona, b, guardia_triaje445)
                    else:
                        aid = insertar_accion(con)
            except RechazoAccion as exc:
                return self.responder(exc.codigo, {"error": str(exc)})
            except PersistenciaNoDisponible as exc:
                return self.responder(503, {"error": str(exc)})
            except ConflictoIntencion as exc:
                return self.responder(409, {"error": str(exc)})
            except ValueError as exc:
                return self.responder(400, {"error": str(exc)})
            if clave_rep:
                with CANDADO_ACCIONES:
                    _ACCIONES_RECIENTES[clave_rep] = (time.time(), aid)
            registrar(real["id"], b.get("modulo") or "acciones", "accion_simulada", str(b["objeto"]), {"accion_id": aid, "tipo": b["tipo"], "herramienta": b["herramienta"]})
            return self.responder(200, {"ok": True, "id": aid, "estado": "simulada", "vista_previa": b.get("vista_previa"), "texto": b.get("texto"), **({"intencion_guardada": {"id": b["intencion_id"], "accion_id": aid, "repetida": repetida_intencion}} if "intencion_id" in b else {})})

        if ruta == "/api/ver_dato":
            # «Ver datos» de un lead (D-88): solo quien lo trabaja, y queda en el rastro.
            almacen, ref, campo = b.get("almacen") or "", str(b.get("ref") or ""), b.get("campo") or ""
            if not re.fullmatch(r"[\w\-/]+", almacen) or "_privado" not in almacen.split("/"):
                return self.responder(400, {"error": "Almacén no válido (debe ser una carpeta _privado/ de data/)."})
            conf = config_almacen(almacen)
            if not conf:
                return self.responder(403, {"error": "Ese almacén no está en reglas_permisos.json (almacenes_privados): no se abre."})
            # Rastro con colección propia por tipo de dato (antes todo iba a «leads») y, en «ver como», quién lo vio.
            coleccion_rastro = {"contactos_cliente": "contactos", "chat_cliente": "chat", "mensaje_cliente": "whatsapp", "sueldos": "sueldos"}.get(conf["tipo"], "leads")
            como_rastro = persona["id"] if solo_lectura else None
            extra_como = {"detalle": f"visto como {persona.get('alias') or persona['id']} por {real.get('alias') or real['id']}"} if solo_lectura else {}
            # Ronda 6 (C4): el cliente lo decide el SERVIDOR desde el propio dato, nunca el cliente_id del navegador.
            cliente_real = cliente_del_dato(conf, ref, almacen)
            # Los datos operativos privados no recuperan clientes excluidos del núcleo
            # ni ganan alcance porque el dato no tenga un cliente reconocible.
            clientes_dato = [c for c in E.crudo.get("clientes", [])
                             if isinstance(c, dict) and c.get("id") == cliente_real] if cliente_real else []
            cliente_ok = (not conf.get("cliente") or
                          (len(clientes_dato) == 1 and ACT.es_activo_id(cliente_real) is True
                           and all(P.ver(p, {"tipo": "cliente_detalle", "cliente_id": cliente_real},
                                         P.contexto(p, E.crudo)).get("ok") for p in (real, persona))))
            if not cliente_ok:
                registrar_agrupado(real["id"], coleccion_rastro, "ver_dato_denegado", f"{almacen}#{ref}", {"campo": campo, "motivo": "dato sin cliente", **extra_como}, como=como_rastro)
                return self.responder(403, {"error": "Ese dato no pertenece a un cliente activo que puedas consultar."})
            b["cliente_id"] = cliente_real
            dueno = almacen.split("/")[-1] if conf.get("dueno") == "fichero" else None   # «solo lo tuyo»: el fichero es de esa persona
            v = P.ver(persona, {"tipo": conf["tipo"], "cliente_id": cliente_real, "persona_id": dueno}, cp)
            nombre_alm = almacen.split("/")[-1]
            dueño_ok = (not conf.get("dueno_setter") or nombre_alm == persona["id"]
                        or bool(P.puestos_de(persona) & {"direccion", "ventas_ro"}))
            modulo_ok = bool(ve_alguno(persona, conf.get("modulos", [])))
            if not v.get("desenmascarable") or not dueño_ok or not modulo_ok:
                registrar_agrupado(real["id"], coleccion_rastro, "ver_dato_denegado", f"{almacen}#{ref}", {"campo": campo, "cliente_id": cliente_real, **extra_como}, como=como_rastro)
                return self.responder(403, {"error": P.REGLAS["tipos"].get(conf["tipo"], {}).get("no") or "Estos datos solo los ve quien los trabaja."})
            f = (DATA / f"{almacen}.json").resolve()
            if not str(f).startswith(str(DATA.resolve())) or not f.exists():
                return self.responder(404, {"error": "No existe ese almacén."})
            doc = json.loads(f.read_text())
            valor = None
            for coleccion in (doc.values() if isinstance(doc, dict) else []):
                if isinstance(coleccion, dict) and ref in coleccion and isinstance(coleccion[ref], dict):
                    valor = coleccion[ref].get(campo)
                    break
            if valor is None:   # Ronda 8 (D-P-PER2 b): sin fila no es un error; 200 «sin dato» y queda en el rastro igual
                rid = registrar(real["id"], coleccion_rastro, "ver_dato", f"{almacen}#{ref}", {"campo": campo, "sin_dato": True, **extra_como}, como=como_rastro)
                return self.responder(200, {"ok": True, "valor": None, "sin_dato": True, "texto": "sin dato", "rastro": rid})
            rid = registrar(real["id"], coleccion_rastro, "ver_dato", f"{almacen}#{ref}", {"campo": campo, "cliente_id": b.get("cliente_id"), **extra_como}, como=como_rastro)
            return self.responder(200, {"ok": True, "valor": valor, "rastro": rid})

        if ruta == "/api/decisiones":
            return self.post_decision(real, cp, b)

        if ruta == "/api/recarga":
            # R15: Agus (técnico) puede pulsar «Probar ahora» de Conexiones: SOLO el paso salud_conexiones (modo «conexiones»),
            # nunca la recarga entera. Sin «modo», quien no puede recargar pero sí probar conexiones pide solo ese paso.
            modo = str(b.get("modo") or "")
            puede_todo = P.ver(persona, {"tipo": "recargar"}, cp)["ok"]
            puede_con = P.ver(persona, {"tipo": "probar_conexiones"}, cp)["ok"]
            if modo == "conexiones" or (not modo and not puede_todo and puede_con):
                if not puede_con:
                    return self.responder(403, {"error": P.REGLAS["tipos"]["probar_conexiones"]["no"]})
                fila, nueva = pedir_recarga(real["id"], "conexiones")
                if nueva:
                    registrar(real["id"], "recarga", "recarga_pedida", str(fila["id"]), {"modo": fila["modo"]})
                return self.responder(200, {"ok": True, "nueva": nueva, "recarga": fila, "solo_conexiones": True})
            if modo not in ("", "ligera"):
                return self.responder(400, {"error": "Modo de recarga no válido (ligera o conexiones)."})
            if not puede_todo:
                return self.responder(403, {"error": P.REGLAS["tipos"]["recargar"]["no"]})
            fila, nueva = pedir_recarga(real["id"])
            if nueva:
                registrar(real["id"], "recarga", "recarga_pedida", str(fila["id"]), {"modo": fila["modo"]})
            return self.responder(200, {"ok": True, "nueva": nueva, "recarga": fila})

        # Mi perfil (3-oct) · cambiar la zona horaria (la lógica y la regla, en altas_personas.py → cambiar_zona).
        if ruta == "/api/perfil/zona":
            AL = sys.modules.get("altas_personas")
            c, r = AL.cambiar_zona(real, persona, b) if AL else (503, {"error": "Mi perfil no está cargado en este servidor."})
            return self.responder(c, r)

        if ruta == "/api/preferencias":
            # R15 (A6): la lista entera de «Mis clientes» fijados; solo clientes que esta persona puede abrir.
            lista = b.get("fijados")
            if not isinstance(lista, list) or len(lista) > TOPE_FIJADOS or not all(isinstance(x, str) and re.fullmatch(r"[\w\-]{1,80}", x) for x in lista):
                return self.responder(400, {"error": f"«fijados» es una lista de hasta {TOPE_FIJADOS} clientes."})
            lista = list(dict.fromkeys(lista))
            malos = [c for c in lista if not P.ver(persona, {"tipo": "cliente_detalle", "cliente_id": c}, cp)["ok"]]
            if malos:
                registrar_agrupado(real["id"], "preferencias", "denegado", ",".join(malos)[:80], {"motivo": "fijar un cliente que no abre"})
                return self.responder(403, {"error": "Solo puedes fijar clientes que abres."})
            antes = leer_preferencia(real["id"], "fijados") or []
            with conectar() as con:
                con.execute("INSERT OR REPLACE INTO preferencias (persona, clave, valor, cambiado) VALUES (?, 'fijados', ?, datetime('now'))",
                            (real["id"], json.dumps(lista)))
            for c in [x for x in lista if x not in antes]:
                registrar(real["id"], "preferencias", "cliente_fijado", c)
            for c in [x for x in antes if x not in lista]:
                registrar(real["id"], "preferencias", "cliente_desfijado", c)
            return self.responder(200, {"ok": True, "fijados": lista})

        if ruta == "/api/opinion":
            # R15 (A7): «Algo va mal / Tengo una idea». Quién y cuándo los pone el SERVIDOR (nunca el navegador); nada sale fuera.
            tipo, prio = b.get("tipo"), b.get("prioridad") or "gris"
            # R16 (N1): contraseñas, correos y teléfonos fuera ANTES de guardar, de avisar y del rastro.
            texto = limpiar_texto(_txt(b.get("texto"), 2000), 2000)
            if tipo not in ("fallo", "idea") or prio not in ("rojo", "ambar", "gris") or len(texto) < 3:
                return self.responder(400, {"error": "Falta qué ha pasado (o el tipo no es «fallo» o «idea»)."})
            ruta_app = str(b.get("ruta") or "")[:200]
            if ruta_app and not RUTA_APP.match(ruta_app):
                ruta_app = ""
            cap = b.get("captura")
            if cap and RUTA_SENSIBLE.search(ruta_app or str(b.get("pantalla") or "")):
                cap = None        # R16 (N1, bajo): una captura de Sueldos no viaja (la verían Mili y otros)
            if cap and (not isinstance(cap, str) or not re.fullmatch(r"data:image/jpeg;base64,[A-Za-z0-9+/=]+", cap) or len(cap) > MAX_CAPTURA):
                return self.responder(400, {"error": "La captura tiene que ser una imagen JPEG de menos de 190 KB."})
            ent = lambda v: int(v) if isinstance(v, (int, float)) and 0 < v < 20000 else None
            with conectar() as con:
                n = con.execute("SELECT count(*) FROM opiniones WHERE quien=? AND creada >= datetime('now', '-1 hour')", (real["id"],)).fetchone()[0]
                if n >= TOPE_OPINIONES_HORA:
                    return self.responder(429, {"error": "Muchos avisos en una hora: espera un poco o escribe a Mili."})
                cur = con.execute("INSERT INTO opiniones (quien, tipo, prioridad, texto, esperaba, ruta, pantalla, ancho, alto, frescura, captura) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                                  (real["id"], tipo, prio, texto, limpiar_texto(_txt(b.get("esperaba"), 1000), 1000) or None, ruta_app or None,
                                   limpiar_texto(_txt(b.get("pantalla"), 80), 80) or None, ent(b.get("ancho")), ent(b.get("alto")),
                                   limpiar_texto(_txt(b.get("frescura"), 300), 300) or None, cap or None))
                oid = cur.lastrowid
            registrar(real["id"], "opiniones", "opinion_enviada", str(oid), {"tipo": tipo, "prioridad": prio, "ruta": ruta_app, "ancho": ent(b.get("ancho")),
                                                                              "captura": bool(cap), "largo": len(texto)})
            avisado = avisar_opinion(real, oid, {"tipo": tipo, "prioridad": prio, "texto": texto, "pantalla": limpiar_texto(_txt(b.get("pantalla"), 80), 80),
                                                 "ruta": ruta_app, "ancho": ent(b.get("ancho"))})
            return self.responder(200, {"ok": True, "id": oid, "avisado": avisado, "hora": ahora()})

        if ruta == "/api/opiniones/estado":
            if not P.ver(persona, {"tipo": "opiniones_ver"}, cp)["ok"]:
                return self.responder(403, {"error": P.REGLAS["tipos"]["opiniones_ver"]["no"]})
            est = b.get("estado")
            if est not in ("vista", "resuelta", "nueva"):
                return self.responder(400, {"error": "Estado no válido."})
            with conectar() as con:
                n = con.execute("UPDATE opiniones SET estado=?, estado_por=?, estado_hora=datetime('now') WHERE id=?", (est, real["id"], int(b.get("id") or 0))).rowcount
            if not n:
                return self.responder(404, {"error": "No existe esa opinión."})
            registrar(real["id"], "opiniones", f"opinion_{est}", str(b.get("id")))
            return self.responder(200, {"ok": True})

        if ruta == "/api/avisos/visto":
            if not P.ver(persona, {"tipo": "recargar"}, cp)["ok"]:
                return self.responder(403, {"error": P.REGLAS["tipos"]["recargar"]["no"]})
            with conectar() as con:
                con.execute("UPDATE avisos SET visto=datetime('now'), visto_por=? WHERE id=? AND visto IS NULL", (real["id"], int(b.get("id") or 0)))
            registrar(real["id"], "avisos", "aviso_visto", str(b.get("id")))
            return self.responder(200, {"ok": True})

        if ruta.startswith("/api/ajustes/"):
            if not P.ver(persona, {"tipo": "ajustes_editar"}, cp)["ok"]:
                return self.responder(403, {"error": P.REGLAS["tipos"]["ajustes_editar"]["no"]})
            return self.ajustes(ruta, real, b)

        return self.responder(404, {"error": "No existe esa ruta de la API."})

    def post_decision(self, real, cp, b):
        """Subir una decisión (para Tomás 48 h, para Coti 24 h, escalada) o contestarla. Nada se borra:
        contestar rellena la respuesta una sola vez; cambiarla es una decisión nueva."""
        if not isinstance(b, dict):
            return self.responder(400, {"error": "La decisión debe ser un objeto."})
        op = b.get("operacion") or "nueva"
        if op == "nueva":
            tipo = b.get("tipo") or "para_tomas"
            if tipo not in TIPOS_DECISION:
                return self.responder(400, {"error": "Tipo no válido (para_tomas, para_coti o escalada)."})
            if not all(isinstance(b.get(k), str) and b[k].strip() for k in ("titulo", "problema")):
                return self.responder(400, {"error": "Falta qué hay que decidir o el problema."})
            if not isinstance(b.get("recomendacion"), str) or not b["recomendacion"].strip():
                return self.responder(400, {"error": "Falta tu recomendación (exigencia 48: sin recomendación no se sube)."})
            cid = b.get("cliente_id")
            if cid is not None and (not isinstance(cid, str) or not cid):
                return self.responder(400, {"error": "Cliente no válido."})
            otros = b.get("clientes")
            if otros is not None and (not isinstance(otros, list)
                    or not all(isinstance(x, str) and x for x in otros)
                    or len(set(otros)) != len(otros)):
                return self.responder(400, {"error": "La lista de clientes debe contener identidades únicas."})
            clientes = sorted(set(([cid] if cid is not None else []) + (otros or [])))
            firma = autoridad_decision607(real, clientes)
            if firma is None:
                return self.responder(403, {"error": "No puedes subir una decisión con ese ámbito actual."})
            if b.get("prueba") and not str(b["prueba"]).startswith(("https://", "#/")):
                return self.responder(400, {"error": "La prueba tiene que ser un enlace https:// o una pantalla de la app (#/…)."})
            extra = {k: b.get(k) for k in ("opciones", "fecha", "prueba", "clientes") if b.get(k) is not None}
            if otros is not None:
                extra["clientes"] = list(otros)
            with conectar() as con:
                if autoridad_decision607(real, clientes) != firma:
                    return self.responder(403, {"error": "El ámbito de la decisión ha cambiado; no se ha guardado."})
                cur = con.execute("INSERT INTO decisiones (quien, tipo, clave, titulo, problema, recomendacion, cliente_id, datos) VALUES (?,?,?,?,?,?,?,?)",
                                  (real["id"], tipo, b.get("clave"), b["titulo"].strip()[:200], b["problema"].strip(), b["recomendacion"].strip(), cid,
                                   json.dumps(extra, ensure_ascii=False)))
                did = cur.lastrowid
            registrar(real["id"], "decisiones", "decision_nueva", f"db-{did}", {"tipo": tipo, "titulo": b["titulo"][:120]})
            return self.responder(200, {"ok": True, "id": f"db-{did}"})
        if op == "responder":
            m = re.fullmatch(r"db-(\d+)", str(b.get("id") or ""))
            if not m:
                return self.responder(400, {"error": "Solo se contestan aquí las decisiones de la tabla (id «db-…»)."})
            with conectar() as con:
                fila = con.execute("SELECT * FROM decisiones WHERE id=?", (int(m.group(1)),)).fetchone()
                if not fila or fila["tipo"] not in TIPOS_DECISION:
                    return self.responder(404, {"error": "No existe esa decisión."})
                if not puede_contestar(real, fila["tipo"]):
                    return self.responder(403, {"error": "Esta decisión la contesta su destinatario (Tomás o Coti)."})
                if fila["respondida"]:
                    return self.responder(409, {"error": "Ya está contestada. Para cambiarla, sube una decisión nueva."})
                resp = {"decision": b.get("decision"), "motivo": b.get("motivo"), "delegada_en": b.get("delegada_en")}
                if resp["decision"] != "Aprobar la recomendación" and not (resp["motivo"] or "").strip():
                    return self.responder(400, {"error": "Rechazar o delegar necesita un motivo."})
                con.execute("UPDATE decisiones SET respuesta=?, respondida=datetime('now'), respondida_por=? WHERE id=?",
                            (json.dumps(resp, ensure_ascii=False), real["id"], fila["id"]))
            registrar(real["id"], "decisiones", "decidir", b["id"], resp)
            return self.responder(200, {"ok": True})
        return self.responder(400, {"error": "Operación no válida (nueva o responder)."})

    def ajustes(self, ruta, real, b):
        if ruta == "/api/ajustes/persona":
            p = E.persona(b.get("id"))
            if not p:
                return self.responder(404, {"error": "No existe esa persona."})
            permitidos = {"puestos", "jefe", "horas_mes", "imputa_horas", "estado", "correo", "nombre", "alias"}
            cambios = {k: v for k, v in (b.get("cambios") or {}).items() if k in permitidos}
            if "puestos" in cambios:
                malos = [x for x in cambios["puestos"] if x not in P.PUESTO]
                if malos or not cambios["puestos"]:
                    return self.responder(400, {"error": f"Puestos no válidos: {malos or 'ninguno'}"})
            if "estado" in cambios:
                if cambios["estado"] not in ("activo", "dudoso", "por_incorporar", "baja"):
                    return self.responder(400, {"error": "Estado no válido."})
                cambios["activo"] = cambios["estado"] == "activo"
            if "sueldo" in json.dumps(b):
                return self.responder(400, {"error": "Los sueldos no se cambian desde Ajustes."})
            # Ronda 6 (A7): nadie cambia sus propios puestos; los puestos de mando y cualquier cambio a una persona con
            # dirección solo los hace Tomás (dirección).
            # Ronda 11 (A3): «de mando» son también operaciones («ver como» y Ajustes), ventas de RO (prospectos de Tomás)
            # y administración (cobros): lista en reglas_permisos.json → puestos_solo_tomas. Y a una persona que ya tiene
            # uno de ellos (Mili, Cecilia, Sofía…) solo Tomás le cambia puestos, estado (baja), jefe o correo.
            es_direccion = "direccion" in real.get("puestos", [])
            mando = set(P.REGLAS.get("puestos_solo_tomas") or ["direccion", "finanzas_direccion", "rrhh", "operaciones", "ventas_ro", "administracion"])
            cambia = {k for k, x in cambios.items() if k != "activo" and x != p.get(k)}
            if "puestos" in cambios and set(cambios["puestos"]) == set(p.get("puestos", [])):
                cambia.discard("puestos")
            if "puestos" in cambia and p["id"] == real["id"]:
                return self.responder(403, {"error": "Nadie cambia sus propios puestos: pídeselo a Tomás."})
            if "puestos" in cambia and (set(cambios["puestos"]) ^ set(p.get("puestos", []))) & mando and not es_direccion:
                return self.responder(403, {"error": "Dar o quitar dirección, finanzas de dirección, RRHH, operaciones, ventas de RO o administración solo lo hace Tomás."})
            if "direccion" in p.get("puestos", []) and cambia and not es_direccion:
                return self.responder(403, {"error": "Los datos de una persona de dirección solo los cambia Tomás."})
            # R16 (N8): a una persona con un puesto de mando, CUALQUIER campo (también alias, nombre u horas) solo lo cambia
            # Tomás, como ya hace altas_personas.puede_tocar.
            if set(p.get("puestos", [])) & mando and cambia and not es_direccion:
                return self.responder(403, {"error": "A una persona con un puesto de mando (operaciones, RRHH, administración, ventas de RO…) solo la cambia Tomás."})
            if "estado" in cambios and cambios["estado"] != p.get("estado") and ('baja' in (cambios["estado"], p.get("estado"))):
                return self.responder(400, {"error": "Las bajas y reincorporaciones se gestionan desde Altas y bajas."})
            if "correo" in cambios:
                if cambios["correo"] is not None and not isinstance(cambios["correo"], str):
                    return self.responder(400, {"error": "Correo no válido."})
                correo = (cambios["correo"] or "").strip().lower()
                if correo and not correo.endswith(("@rankingonline.com", "@rankingonlinemarketing.com")):
                    return self.responder(400, {"error": "El correo tiene que ser de RO."})
                otros = [x for x in E.crudo["personas"] if x["id"] != p["id"] and correo and
                         (correo == (x.get("correo") or "").lower() or correo in [c.lower() for c in x.get("otros_correos") or []])]
                if otros:
                    return self.responder(409, {"error": "Ese correo ya es de otra persona: tiene que ser único."})
                if correo != (p.get("correo") or "").strip().lower():
                    return self.responder(400, {"error": "El correo de entrada se gestiona desde Altas y bajas; aquí no cambia Access."})
                cambios["correo"] = p.get("correo")
            antes = {k: p.get(k) for k in cambios}
            with conectar() as con:
                con.execute("INSERT INTO historial (quien, coleccion, id, operacion, antes, datos) VALUES (?,?,?,?,?,?)",
                            (real["id"], "personas", p["id"], "cambiar", json.dumps(antes, ensure_ascii=False), json.dumps(cambios, ensure_ascii=False)))
            registrar(real["id"], "ajustes", "cambio_persona", p["id"], {"antes": antes, "despues": cambios})
            E.recargar_personas("ajustes · persona")   # V3a: parcial (antes, la entera: ~4 s)
            return self.responder(200, {"ok": True})

        if ruta == "/api/ajustes/asignacion":
            from ajustes_validacion_579 import asignacion as validar_asignacion579
            op = b.get("operacion")
            d = validar_asignacion579(P, ACT, E.crudo, b, hoy())
            if d is None:
                return self.responder(400, {"error": "Asignación no válida: revisa persona activa, silla, fechas y suplencia."})
            if op == 'crear':
                d.update({"fuente": f"Ajustes · {real['alias']} · {ahora()}", "confianza": "confirmada"})
            with conectar() as con:
                if validar_asignacion579(P, ACT, E.crudo, b, hoy()) is None:
                    return self.responder(403, {"error": "La asignación ha cambiado de ámbito."})
                con.execute("INSERT INTO historial (quien, coleccion, id, operacion, datos) VALUES (?,?,?,?,?)",
                            (real["id"], "asignaciones", f"{d['cliente_id']}·{d['silla']}·{d['persona_id']}", op, json.dumps(d, ensure_ascii=False)))
            registrar(real["id"], "ajustes", f"asignacion_{op}", d["cliente_id"], d)
            E.recargar_personas("ajustes · asignación")
            return self.responder(200, {"ok": True})

        if ruta == "/api/ajustes/confirmar":
            resp = b.get("respuesta") or {}
            lista = resp if isinstance(resp, list) else [resp]
            from confirmar_personas_572 import validar_lista, actor_actual, permite_estados
            if not actor_actual(P, E.crudo, real):
                return self.responder(403, {"error": "No puedes confirmar en tu ámbito actual."})
            if not validar_lista(resp, E.crudo):
                return self.responder(400, {"error": "Respuesta no válida para la duda actual."})
            if not permite_estados(P, E.crudo, real, resp):
                return self.responder(403, {"error": "No puedes modificar el estado de esa persona."})
            duda = lista[0].get("duda")
            with conectar() as con:
                if not actor_actual(P, E.crudo, real) or not validar_lista(resp, E.crudo) or not permite_estados(P, E.crudo, real, resp):
                    return self.responder(403, {"error": "El ámbito de confirmación ha cambiado."})
                previa = con.execute("SELECT id FROM decisiones WHERE tipo='para_confirmar' AND clave=? AND anula_a IS NULL ORDER BY id DESC LIMIT 1", (duda,)).fetchone()
                if not actor_actual(P, E.crudo, real) or not validar_lista(resp, E.crudo) or not permite_estados(P, E.crudo, real, resp):
                    return self.responder(403, {"error": "El ámbito de confirmación ha cambiado."})
                if previa:   # contestar otra vez = anular la anterior (nada se borra)
                    con.execute("INSERT INTO decisiones (quien, tipo, clave, problema, respuesta, anula_a) VALUES (?,?,?,?,NULL,?)",
                                (real["id"], "para_confirmar", duda, "anulada por una respuesta nueva", previa["id"]))
                con.execute("INSERT INTO decisiones (quien, tipo, clave, respuesta, recomendacion, respondida, respondida_por) VALUES (?,?,?,?,?,?,?)",
                            (real["id"], "para_confirmar", duda, json.dumps(resp, ensure_ascii=False), lista[0].get("nota"), ahora(), real["id"]))
            registrar(real["id"], "ajustes", "para_confirmar", duda, resp)
            E.recargar_personas("ajustes · para confirmar")
            return self.responder(200, {"ok": True})

        return self.responder(404, {"error": "No existe esa ruta de Ajustes."})


# N3 (2-oct) · IA: si existe ia.py, atiende /api/ia/* (borradores de Desk y copiloto del account). Sin él, nada cambia.
try:
    import ia as IA                                        # noqa: E402
    IA.enganchar(Manejador, sys.modules[__name__])
except ImportError:
    pass
except Exception as _e:                                    # la app arranca igual; la IA queda fuera
    print("⚠️  IA no cargada:", _e)

# N9 (2-oct noche) · Altas y bajas de personas desde Ajustes: /api/altas/* (altas_personas.py). Sin él, nada cambia.
try:
    import altas_personas as ALTAS                         # noqa: E402
    ALTAS.enganchar(Manejador, sys.modules[__name__])
except ImportError:
    pass
except Exception as _e:
    print("⚠️  Altas de personas no cargadas:", _e)

# N15 (2-oct noche) · Canales de avisos, grupos de la app y campana: /api/canales/* (avisos.py). Sin él, nada cambia.
try:
    import avisos as AVISOS                                # noqa: E402
    AVISOS.enganchar(Manejador, sys.modules[__name__])
except ImportError:
    pass
except Exception as _e:
    print("⚠️  Canales de avisos no cargados:", _e)

# Avisos automáticos (3-oct) · /api/avisos_programados/* (avisos_programados.py): recordatorios programados en los canales
# de la app (horas, semáforo del lunes, informe mensual, cierre de facturación, resúmenes). Va DESPUÉS de avisos.py.
try:
    if "avisos" in sys.modules:
        import avisos_programados as AVISOS_PROG           # noqa: E402
        AVISOS_PROG.enganchar(Manejador, sys.modules[__name__])
except ImportError:
    pass
except Exception as _e:
    print("⚠️  Avisos automáticos no cargados:", _e)

# Envíos verificados (3-oct) · /api/envios/* (envios.py): ciclo de vida de cada envío, verificación y avisos. Hoy, simulado.
try:
    import envios as ENVIOS                                # noqa: E402
    ENVIOS.enganchar(Manejador, sys.modules[__name__])
except ImportError:
    pass
except Exception as _e:
    print("⚠️  Envíos no cargados:", _e)

# Sincronía con herramientas (3-oct) · /api/sincronia/* (sincronia.py): copia segura de cada cambio que va a ClickUp. Hoy, simulado.
try:
    import sincronia as SINCRONIA                          # noqa: E402
    SINCRONIA.enganchar(Manejador, sys.modules[__name__])
except ImportError:
    pass
except Exception as _e:
    print("⚠️  Sincronía no cargada:", _e)

# Mi trabajo (3-oct) · GET /api/mi_trabajo y POST /api/mi_trabajo/crono (mi_trabajo.py): tareas y horas sin salir de la app.
# Valida las acciones del módulo «mi-trabajo» antes de la cola; todo va a la copia segura de sincronia.py. Sin él, nada cambia.
try:
    import mi_trabajo as MI_TRABAJO                        # noqa: E402
    MI_TRABAJO.enganchar(Manejador, sys.modules[__name__])
except ImportError:
    pass
except Exception as _e:
    print("⚠️  Mi trabajo no cargado:", _e)

# Vigía (3-oct) · GET /api/vigia y POST /api/vigia/probar (despliegue/vigia.py): «Salud del sistema». Sin él, nada cambia.
try:
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("vigia", AQUI / "despliegue" / "vigia.py")
    VIGIA = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(VIGIA)
    VIGIA.enganchar(Manejador, sys.modules[__name__])
except FileNotFoundError:
    pass
except Exception as _e:
    print("⚠️  Vigía no cargado:", _e)

# N5 Modular DS (3-oct) · POST /api/modular/acceso (fuentes_modular/acceso.py): «Entrar al WordPress» solo para web, jefe de
# SEO y web y dirección, con rastro; apagado mientras la clave de Modular sea de solo lectura. Sin el fichero, nada cambia.
try:
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("modular_acceso", AQUI / "fuentes_modular" / "acceso.py")
    MODULAR_ACCESO = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(MODULAR_ACCESO)
    MODULAR_ACCESO.enganchar(Manejador, sys.modules[__name__])
except FileNotFoundError:
    pass
except Exception as _e:
    print("⚠️  Acceso a Modular no cargado:", _e)

# Proponer fecha (3-oct) · /api/reuniones/propuesta* (fuentes_reuniones/propuesta_reunion.py): correo de propuesta de reunión
# ya redactado por reglas (huecos de la agenda, motivo, firma) y su nota de calidad. Enviar va por la cola y envios.py.
try:
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("propuesta_reunion", AQUI / "fuentes_reuniones" / "propuesta_reunion.py")
    PROPUESTA_REUNION = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(PROPUESTA_REUNION)
    PROPUESTA_REUNION.enganchar(Manejador, sys.modules[__name__])
except FileNotFoundError:
    pass
except Exception as _e:
    print("⚠️  Proponer fecha (correo de reunión) no cargado:", _e)

# Ficha de Google (3-oct) · /api/gbp/* (fuentes_gbp/servidor_gbp.py): «Proponer respuesta» a una reseña con el cerebro de
# reseñas y respuesta en SIMULACIÓN (cola de acciones, canal de Google apagado). Sin el fichero, nada cambia.
try:
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("servidor_gbp", AQUI / "fuentes_gbp" / "servidor_gbp.py")
    SERVIDOR_GBP = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(SERVIDOR_GBP)
    SERVIDOR_GBP.enganchar(Manejador, sys.modules[__name__])
except FileNotFoundError:
    pass
except Exception as _e:
    print("⚠️  Ficha de Google (reseñas) no cargada:", _e)


# A8 (2-oct noche) · Alertas: nadie pospone ni despacha en lote alertas ajenas (fuentes_alertas/guardia_alertas.py)
try:
    sys.path.insert(0, str(AQUI / "fuentes_alertas"))
    import guardia_alertas as GUARDIA_ALERTAS              # noqa: E402
    GUARDIA_ALERTAS.enganchar(Manejador, sys.modules[__name__])
except ImportError:
    pass

# Setters (3-oct, 58_FEEDBACK_TOMAS_03OCT) · setters_srv.py: cada setter solo actúa sobre SUS leads y citas (comprobado aquí),
# «Agendar cita» en simulación (crear_cita_ghl, vista previa del servidor) y POST /api/setters/propuesta_cita. Va el último:
# su guardia corre antes que las demás. Sin el fichero, nada cambia.
try:
    import setters_srv as SETTERS_SRV                      # noqa: E402
    SETTERS_SRV.enganchar(Manejador, sys.modules[__name__])
except ImportError:
    pass
except Exception as _e:
    print("⚠️  Setters (servidor) no cargado:", _e)

# Acta y acuerdos: un lote transaccional, idempotente y siempre simulado. No despacha APIs externas.
try:
    import actas as ACTAS
    ACTAS.enganchar(Manejador, sys.modules[__name__])
except ImportError:
    pass
except Exception as _e:
    print("⚠️  Actas transaccionales no cargadas:", _e)

# Analítica propia de uso: sin envío externo ni contenido de negocio.
import uso_local as USO_LOCAL
USO_LOCAL.enganchar(Manejador, sys.modules[__name__])

# Cadencia operativa confirmada; sin agendar ni escribir fuera.
import metodo_cuentas as METODO_CUENTAS
METODO_CUENTAS.enganchar(Manejador, sys.modules[__name__])

# Diagnóstico de lectura: cada fuente pasa por su puerta y recorte existentes.
import cerebro_api as CEREBRO_API
CEREBRO_API.enganchar(Manejador, sys.modules[__name__])
import cerebro_seo_api as CEREBRO_SEO_API
CEREBRO_SEO_API.enganchar(Manejador, sys.modules[__name__])
import borradores_api as BORRADORES_API
BORRADORES_API.enganchar(Manejador, sys.modules[__name__])
import informes_tareas_api as INFORMES_TAREAS_API
INFORMES_TAREAS_API.enganchar(Manejador, sys.modules[__name__])
import agenda_zoom_api as AGENDA_ZOOM_API
AGENDA_ZOOM_API.enganchar(Manejador, sys.modules[__name__])
from fuentes_pagespeed import lectura_api as PAGESPEED_API
PAGESPEED_API.enganchar(Manejador, sys.modules[__name__])
import historial_reuniones_api as HISTORIAL_REUNIONES_API
HISTORIAL_REUNIONES_API.enganchar(Manejador, sys.modules[__name__])

# Última barrera: ninguna escritura de módulos elude el piloto de consulta.
# Preferencias privadas de tareas: no activa el tablero experimental ni sus cambios.
import informe_word_api as INFORME_WORD_API
INFORME_WORD_API.enganchar(Manejador, sys.modules[__name__])
import evidencias_kpi_api as EVIDENCIAS_KPI_API
EVIDENCIAS_KPI_API.enganchar(Manejador, sys.modules[__name__])
import evidencia_produccion_287 as EVIDENCIA_PRODUCCION_287
import operaciones_registros_269 as OPERACIONES_REGISTROS_269
OPERACIONES_REGISTROS_269.enganchar(Manejador, sys.modules[__name__])
import operaciones_registros_272 as OPERACIONES_CONTROL_272
OPERACIONES_CONTROL_272.enganchar(Manejador, sys.modules[__name__])
import operaciones_feedback_273 as OPERACIONES_FEEDBACK_273
OPERACIONES_FEEDBACK_273.enganchar(Manejador, sys.modules[__name__])
import operaciones_pedidos_account as OPERACIONES_PEDIDOS_ACCOUNT_294
OPERACIONES_PEDIDOS_ACCOUNT_294.enganchar(Manejador, sys.modules[__name__])
import historico_llamadas_350 as HISTORICO_LLAMADAS_350
HISTORICO_LLAMADAS_350.enganchar(Manejador, sys.modules[__name__])
import planning_observado_api_356 as PLANNING_OBSERVADO_356
PLANNING_OBSERVADO_356.enganchar(Manejador, sys.modules[__name__])
import planning_observado_api_405 as PLANNING_OBSERVADO_405
PLANNING_OBSERVADO_405.enganchar(Manejador, sys.modules[__name__])
import historial_diario_api_362 as HISTORIAL_DIARIO_362
HISTORIAL_DIARIO_362.enganchar(Manejador, sys.modules[__name__])
import urgencias_observadas_api_402 as URGENCIAS_OBSERVADAS_402
URGENCIAS_OBSERVADAS_402.enganchar(Manejador, sys.modules[__name__])
import agrupaciones_tarea_api_376 as AGRUPACIONES_TAREA_376
AGRUPACIONES_TAREA_376.enganchar(Manejador, sys.modules[__name__])
import meta_diaria_api_385 as META_DIARIA_385
META_DIARIA_385.enganchar(Manejador, sys.modules[__name__])
import crm_embudo_api_467 as CRM_EMBUDO_467
CRM_EMBUDO_467.enganchar(Manejador, sys.modules[__name__])
import crm_ultima_valida_api_513 as CRM_ULTIMA_VALIDA_513
CRM_ULTIMA_VALIDA_513.enganchar(Manejador, sys.modules[__name__])
import operaciones_prioridades_300 as OPERACIONES_PRIORIDADES_300
OPERACIONES_PRIORIDADES_300.enganchar(Manejador, sys.modules[__name__])
import operaciones_anomalias_276 as OPERACIONES_ANOMALIAS_276
OPERACIONES_ANOMALIAS_276.enganchar(Manejador, sys.modules[__name__])
import operaciones_notas_equipo_281 as OPERACIONES_NOTAS_EQUIPO_281
OPERACIONES_NOTAS_EQUIPO_281.enganchar(Manejador, sys.modules[__name__])
import tareas_local as TAREAS_PREFERENCIAS
TAREAS_PREFERENCIAS.enganchar(Manejador, sys.modules[__name__], solo_preferencias=True)

import contratos_privados as CONTRATOS_PRIVADOS
CONTRATOS_PRIVADOS.enganchar(Manejador, sys.modules[__name__])
import transiciones_produccion_208 as PRODUCCION_TRANSICIONES_208
PRODUCCION_TRANSICIONES_208.enganchar(Manejador, sys.modules[__name__])
import decisiones_durables_382 as DECISIONES_DURABLES_382
DECISIONES_DURABLES_382.enganchar(Manejador, sys.modules[__name__])
import triaje_intenciones_437 as TRIAJE_INTENCIONES_437
TRIAJE_INTENCIONES_437.enganchar(Manejador, sys.modules[__name__])
import ejemplos_creador_api_438 as EJEMPLOS_CREADOR_438
EJEMPLOS_CREADOR_438.enganchar(Manejador, sys.modules[__name__])
import piloto_lectura as PILOTO_LECTURA
PILOTO_LECTURA.enganchar(Manejador)

def main():
    if "--help" in sys.argv or "-h" in sys.argv:   # ronda 14: la ayuda sale sin arrancar el servidor ni abrir la base
        print(__doc__.strip())
        return
    if "--anotar-corte" in sys.argv:   # ronda 8: un corte conocido de la cadena queda anotado (imborrable) con su motivo
        i = sys.argv.index("--anotar-corte")
        iniciar_base()
        with conectar() as con:
            con.execute("INSERT INTO rastro_cortes (id, motivo) VALUES (?, ?)", (int(sys.argv[i + 1]), sys.argv[i + 2]))
        print("Corte anotado.")
        return
    if "--anotar-incidencia" in sys.argv:   # ronda 11: incidencia del rastro (corte o filas sin huella), imborrable
        i = sys.argv.index("--anotar-incidencia")
        tipo, desde, hasta, motivo = sys.argv[i + 1], int(sys.argv[i + 2]), int(sys.argv[i + 3]), sys.argv[i + 4]
        iniciar_base()
        with conectar() as con:
            ya = con.execute("SELECT 1 FROM rastro_incidencias WHERE tipo=? AND desde=? AND hasta=?", (tipo, desde, hasta)).fetchone()
            if ya:
                print("Ya estaba anotada (no se repite).")
                return
            con.execute("INSERT INTO rastro_incidencias (tipo, desde, hasta, motivo) VALUES (?,?,?,?)", (tipo, desde, hasta, motivo))
        print(f"Incidencia anotada: {tipo} {desde}-{hasta}.")
        return
    if "--verificar-rastro" in sys.argv:    # ronda 11: la cadena entera (con lo anotado) y desde la última anotación
        iniciar_base()
        bien, rota, n = verificar_rastro()
        bien2, rota2, n2 = verificar_rastro("anotado")
        ok_a, malas, na = comprobar_anclas()
        print(json.dumps({"entera": {"ok": bien, "primera_fila_rota": rota, "filas": n},
                          "tras_anotacion": {"desde": fila_tras_anotacion(), "ok": bien2, "primera_fila_rota": rota2, "filas": n2},
                          "anclas": {"ok": ok_a, "comprobadas": na, "malas": malas}}, ensure_ascii=False, indent=1))
        sys.exit(0 if bien and bien2 and ok_a else 1)
    if "--ancla-diaria" in sys.argv:        # ronda 11: huella del día en un fichero FUERA de la base
        i = sys.argv.index("--ancla-diaria")
        dia = sys.argv[i + 1] if len(sys.argv) > i + 1 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", sys.argv[i + 1]) else None
        iniciar_base()
        print(json.dumps(escribir_ancla(dia), ensure_ascii=False))
        print(f"Añadida a {ANCLAS}")
        return
    if "--importar-rastro" in sys.argv:
        carpeta = sys.argv[sys.argv.index("--importar-rastro") + 1]
        print(f"Importados {importar_rastro(carpeta)} documentos del panel (los ya importados no se repiten).")
        return
    puerto = int(sys.argv[sys.argv.index("--puerto") + 1]) if "--puerto" in sys.argv else 8770
    # R16 (B4): las negativas a arrancar van ANTES de la foto, la base y el trabajador de recargas.
    # Ronda 6 (C2): en modo servidor no se arranca sin Access configurado; fuera de él, solo 127.0.0.1.
    if ACCESO.activo() and not (os.environ.get("RO_CF_EQUIPO") and os.environ.get("RO_CF_AUD")):
        sys.exit("⛔ RO_MODO=servidor sin RO_CF_EQUIPO y RO_CF_AUD: no arranco (sin Cloudflare Access no hay identidad).")
    if not ACCESO.activo() and ("--bind" in sys.argv or os.environ.get("PORT")):
        pedido = sys.argv[sys.argv.index("--bind") + 1] if "--bind" in sys.argv else "0.0.0.0"
        if pedido not in ("127.0.0.1", "localhost"):
            sys.exit("⛔ Sin RO_MODO=servidor y Cloudflare Access solo escucho en 127.0.0.1.")
    iniciar_base()
    if PILOTO_LECTURA.activo():
        E.foto = {"nota": "Piloto de consulta: no se genera una foto nueva."}
    elif not FOTO.hay_foto_de_hoy():
        E.foto = FOTO.hacer_foto()
    else:
        E.foto = {"fecha": hoy(), "nota": "ya había foto de hoy"}
    E.cargar()
    if not PILOTO_LECTURA.activo():
        calcular_avisos()
        threading.Thread(target=trabajador_recargas, daemon=True).start()
        with conectar() as con:   # una recarga que quedó a medias al cerrar el servidor se marca y no se repite sola
            con.execute("UPDATE recargas SET estado='con_fallos', terminada=datetime('now') WHERE estado='en_curso'")
        COLA.set()                # si quedó alguna pendiente, se atiende ya
    if E.bloqueados:
        print("⚠️  Puerta de secretos: no se sirven", ", ".join(E.bloqueados))
    if E.nucleo_bloqueado:
        print("⛔  Hay secretos en los datos comunes: la API responde 503 hasta que se limpien.")
    if ACCESO.activo():   # C5 · servidor (Render): escucha fuera, en el PORT que da Render; los datos llegan de la base
        puerto = int(os.environ.get("PORT") or puerto)
        if os.environ.get("DATABASE_URL") and not PILOTO_LECTURA.activo():
            import publicacion as PUB    # despliegue/publicacion.py: baja la versión vigente de data/ y recarga
            PUB.arrancar_sincronizacion(E.cargar)
    anfitrion = "0.0.0.0" if ACCESO.activo() else "127.0.0.1"
    srv = ThreadingHTTPServer((anfitrion, puerto), Manejador)
    print(f"App RO en http://{anfitrion}:{puerto}  " + ("(modo servidor: solo con sello de Cloudflare Access)" if ACCESO.activo()
          else "(solo este Mac · ?yo=<id> para entrar como otra persona)"))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    mimetypes.add_type("text/javascript", ".js")
    main()
