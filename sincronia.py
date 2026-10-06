#!/usr/bin/env python3
"""
sincronia.py · Sincronía con herramientas, empezando por ClickUp (3-oct-2026). Encargo de Tomás: «asegurarnos de que todos
los cambios que hace el equipo dentro de la plataforma (lo que dice que ya está hecho, etc.) impactan en ClickUp, pero
también se guardan como copia por si no llegaran a impactar; y lo mismo con el chat».

HOY TODO VA EN SIMULACIÓN: no se escribe nada en ClickUp ni en ninguna herramienta. Mismo patrón que envios.py (cola,
clave única, pasos imborrables, verificador en la tubería, interruptor de Tomás). Se engancha a servir.py como envios.py.

1. LA COPIA SEGURA ES LA BASE DE LA APP. Toda acción del equipo que debe reflejarse en ClickUp (mover o marcar hecha una
   tarea, aprobar o pedir cambios de una pieza, comentar, imputar horas, asignar, crear una tarea desde una alerta, un
   mensaje al chat) se guarda PRIMERO en la base (`sinc_cambios` + `sinc_pasos`, imborrables) con su estado
       simulado | pendiente → enviado → confirmado | fallido | conflicto (→ descartado si se queda lo de ClickUp)
   quién, cuándo, el objeto de ClickUp y el CAMBIO EXACTO. El objeto y el cambio los saca el SERVIDOR de sus datos
   (Producción, revision_piezas, la acción de la cola): lo que mande el navegador además (estado nuevo, id de tarea,
   lista…) se ignora y queda anotado. La pantalla lo enseña al momento como «Hecho en la app · pendiente de ClickUp».
2. DESPACHADOR con idempotencia: clave única por acción (sha256), nunca dos cambios por acción; antes de escribir mira si
   el cambio ya está en ClickUp (la marca «ro:<clave>» en comentarios, horas y tareas; el estado o el asignado); reintentos
   con espera creciente solo ante errores seguros (red, tiempo, caída, límite); ORDEN POR OBJETO: un cambio de una tarea
   no sale mientras otro anterior de la MISMA tarea siga pendiente, enviado o en conflicto.
3. VERIFICADOR / RECONCILIADOR (despliegue/reconciliar_clickup.py, paso de la tubería, SOLO LECTURA): relee la tarea y
   confirma que el cambio está. Si ClickUp tiene otro valor más nuevo (alguien lo cambió allí después), «conflicto» y aviso
   a la persona (y a Agus) con las dos versiones; elige en Envíos › ClickUp. Si ClickUp no responde: sigue pendiente, aviso
   y reintento. Llave caducada: «fallido» sin reintentos en bucle, aviso a Agus/Tomás y, cuando la llave vuelve a valer,
   se reencola solo.
4. INFORME DIARIO «cambios sin reflejar» (Agus y Mili, #avisos-altas): lo que lleva más de X horas sin estar en ClickUp.
5. INTERRUPTOR POR CANAL (data/sincronia/interruptor.json): ClickUp real solo con «activado_por: tomas» + RO_CLICKUP_REAL=si
   + una llave de escritura de USUARIO DE SERVICIO (`clickup_token_servicio`, nunca la llave de propietario de Tomás:
   ver ../47_PERMISOS_HERRAMIENTAS.md). El PUENTE DE CHAT (app ↔ chat de ClickUp, opción b de ../51_SINCRONIA_Y_CHAT.md)
   queda preparado y APAGADO (`chat_puente: "apagado"`).

Rutas (las ve cada uno con lo suyo; dirección, operaciones y el técnico, todo):
  GET  /api/sincronia[?canal=clickup|chat&estado=]  la cola con su estado, motivo en llano y pasos; informe de sin reflejar
  GET  /api/sincronia/cambio?id=N                   un cambio con todos sus pasos (y las dos versiones si hay conflicto)
  GET  /api/sincronia/objeto?ref=<id de tarea>      el último estado de cada cambio de esa tarea (para las pantallas)
  POST /api/sincronia/reintentar {id}               simulado mientras ClickUp esté apagado
  POST /api/sincronia/elegir {id, gana: app|clickup} solo en conflicto: quien lo hizo, o dirección/operaciones/técnico
  POST /api/sincronia/a_mano {id}                   «ya está en ClickUp, lo he pasado a mano» (dirección/operaciones/técnico)
El navegador solo manda el id (y «gana»): estado, objeto y cambio los pone el servidor.
"""
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo as _ZI
from pathlib import Path

AQUI = Path(__file__).resolve().parent
DATA = AQUI / "data"
CARPETA = DATA / "sincronia"
INTERRUPTOR = Path(os.environ.get("RO_SINC_INTERRUPTOR") or CARPETA / "interruptor.json")
PUENTE = Path(os.environ.get("RO_SINC_PUENTE") or CARPETA / "puente_chat.json")
TEAM = "90152357276"
_MAD = _ZI("Europe/Madrid")
API2 = "https://api.clickup.com/api/v2"
API3 = "https://api.clickup.com/api/v3"

ESTADOS = ("simulado", "pendiente", "enviado", "confirmado", "fallido", "conflicto", "descartado")
FINALES = {"confirmado", "descartado"}
CANALES = {"clickup": "ClickUp", "chat": "Chat de ClickUp"}
SEGUROS = {"red", "tiempo", "caida", "limite"}            # se puede reintentar (antes se mira si ya está)
LLAVE = {"token", "permiso"}
EVENTOS_NOTA = ("aviso", "reintento_simulado", "espera")
TEXTO_PENDIENTE = "Hecho en la app · pendiente de ClickUp"

CONF_DEF = {
    # tipo de acción de la cola (herramienta clickup) → qué cambio hace en ClickUp
    "tipos_clickup": {"mover_estado": "estado", "mover_tarjeta": "estado", "mover": "estado", "marcar_hecha": "estado_hecha",
                      "pieza_aprobar": "estado_revision", "pieza_pedir_cambios": "estado_cambios", "comentario": "comentario",
                      "imputar_horas": "horas", "asignar": "asignado", "asignacion": "asignado", "tarea": "crear_tarea",
                      "pedir_movil": "crear_tarea", "crear_lista_onboarding": "otro", "fechas_dn": "otro",
                      # Mi trabajo (3-oct): cambiar a cualquier estado de SU lista y cambiar la fecha límite
                      "cambiar_estado": "estado_libre", "cambiar_fecha": "fecha"},
    "tipos_chat": ["mensaje_chat", "chat_mensaje", "chat_respuesta"],
    "destinos_mover": ["revisión project manager"],      # a dónde se puede MOVER una tarea desde la app
    "estado_hecha": "complete",
    "estados_hecha": ["completado", "complete", "completada", "cerrado", "closed", "hecho", "done"],   # el primero que exista en la lista
    "ven_todos_puestos": ["direccion", "operaciones", "tecnico_altas"],
    "reintentan_puestos": ["direccion", "operaciones", "tecnico_altas"],
    "avisar_a": ["agustina"],
    "informe_a": ["agustina", "mili"],
    "canal_avisos": "avisos-altas",                       # el canal de Agus (y Mili lo ve como operaciones)
    "canal_avisos_copia": "avisos-direccion",
    "horas_sin_reflejar": 4,
    "hora_informe": "08:30",
    "reintentos_max": 5,
    "esperas_min": [1, 5, 15, 60, 240],
    "gracia_min": 10,
    "activa": "tomas",
    "llave_servicio": "clickup_token_servicio",
    "llave_propietario": "clickup_api_token",
}

S = P = None
_CANDADO = threading.Lock()

TABLAS_SQL = """
CREATE TABLE IF NOT EXISTS sinc_cambios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  clave TEXT NOT NULL UNIQUE,                 -- idempotencia: una por acción (o por mensaje del chat)
  accion_id INTEGER UNIQUE,                   -- la acción de la cola de la que nace
  mensaje_id INTEGER UNIQUE,                  -- o el mensaje de un grupo de la app (puente de chat)
  creado TEXT NOT NULL DEFAULT (datetime('now')),
  quien TEXT NOT NULL,
  canal TEXT NOT NULL CHECK (canal IN ('clickup','chat')),
  tipo TEXT NOT NULL,
  objeto TEXT NOT NULL,                       -- JSON: {tipo: tarea|lista|canal, ref, nombre, url, resuelto} (servidor)
  objeto_ref TEXT NOT NULL,                   -- para el orden por objeto
  cliente_id TEXT,
  modulo TEXT,
  cambio TEXT NOT NULL,                       -- JSON: el cambio EXACTO (servidor)
  base TEXT,                                  -- JSON: lo que la app creía que había en ClickUp al hacerlo
  ignorado TEXT,                              -- JSON: lo que mandó el navegador y no se usó
  modo TEXT NOT NULL CHECK (modo IN ('simulado','real','prueba'))
);
CREATE INDEX IF NOT EXISTS i_sinc_obj ON sinc_cambios(objeto_ref, id);
CREATE INDEX IF NOT EXISTS i_sinc_quien ON sinc_cambios(quien);
CREATE TABLE IF NOT EXISTS sinc_pasos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cambio_id INTEGER NOT NULL REFERENCES sinc_cambios(id),
  estado TEXT NOT NULL CHECK (estado IN ('simulado','pendiente','enviado','confirmado','fallido','conflicto','descartado')),
  evento TEXT NOT NULL,
  hora TEXT NOT NULL DEFAULT (datetime('now')),
  quien TEXT,
  intento INTEGER NOT NULL DEFAULT 0,
  motivo TEXT,
  detalle TEXT
);
CREATE INDEX IF NOT EXISTS i_sinc_pasos ON sinc_pasos(cambio_id, id);
CREATE TRIGGER IF NOT EXISTS sinc_cambios_sin_update BEFORE UPDATE ON sinc_cambios BEGIN SELECT RAISE(ABORT, 'Un cambio no se cambia: se añade un paso'); END;
CREATE TRIGGER IF NOT EXISTS sinc_cambios_sin_delete BEFORE DELETE ON sinc_cambios BEGIN SELECT RAISE(ABORT, 'Un cambio no se borra'); END;
CREATE TRIGGER IF NOT EXISTS sinc_pasos_sin_update BEFORE UPDATE ON sinc_pasos BEGIN SELECT RAISE(ABORT, 'Un paso no se cambia'); END;
CREATE TRIGGER IF NOT EXISTS sinc_pasos_sin_delete BEFORE DELETE ON sinc_pasos BEGIN SELECT RAISE(ABORT, 'Un paso no se borra'); END;
"""

LLANO = {
    "simulado": "Hecho en la app · pendiente de ClickUp. Hoy no se escribe en ClickUp (lo activa Tomás): se pasa a mano.",
    "token": "La llave de ClickUp no vale (caducada o revocada): el cambio NO está en ClickUp. Lo arregla Tomás renovando la llave del usuario de servicio; luego sale solo.",
    "permiso": "La llave de ClickUp no tiene permiso para esto (o es la de propietario, que no se usa para escribir): el cambio NO está en ClickUp.",
    "no_existe": "La tarea ya no existe en ClickUp (o la han movido a un sitio sin acceso): el cambio NO está. Míralo en ClickUp.",
    "destinatario": "No sé a qué lista, persona o canal de ClickUp va: el cambio NO está. Lo resuelve Agus en ClickUp.",
    # N-19: la tarea nueva necesita la lista del cliente y hoy no se resuelve ninguna (ClickUp real aún no crea tareas)
    "sin_lista": "Sin lista de ClickUp para este cliente: la tarea NO se ha creado en ClickUp. Queda guardada aquí hasta que Operaciones configure la lista (o la crea Agus a mano).",
    "rechazo": "ClickUp ha rechazado el cambio (dato no válido, p. ej. un estado que no existe en esa lista). Míralo en ClickUp.",
    "agotado": "ClickUp no ha respondido en varios intentos: el cambio sigue guardado aquí y NO está en ClickUp. No se ha duplicado. Reintenta desde Envíos › ClickUp.",
    "caida": "ClickUp no responde ahora: el cambio sigue guardado aquí y se reintenta solo (sin duplicar).",
    "no_aparece": "ClickUp dijo que sí, pero al releer la tarea el cambio no está. Se puede reintentar sin duplicar.",
    "no_soportado": "Este tipo de cambio aún no sabe pasarse a ClickUp solo: queda guardado aquí y se pasa a mano.",
    "apagado": "ClickUp real apagado: el cambio no ha salido.",
    "conflicto": "Alguien cambió esto en ClickUp después: hay dos versiones. Elige cuál se queda.",
}


# =================================================================== reloj, base y utilidades
def ahora_utc():
    fijo = os.environ.get("RO_RELOJ")
    if fijo:
        try:
            from zoneinfo import ZoneInfo
            return datetime.fromisoformat(fijo).replace(tzinfo=ZoneInfo("Europe/Madrid")).astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            pass
    return datetime.now(timezone.utc).replace(tzinfo=None)


def txt_hora(d):
    return d.strftime("%Y-%m-%d %H:%M:%S")


def leer_hora(t):
    try:
        return datetime.strptime(str(t)[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def iso_z(t):
    return (str(t).replace(" ", "T") + "Z") if t else None


def madrid(d):
    from zoneinfo import ZoneInfo
    return d.replace(tzinfo=timezone.utc).astimezone(ZoneInfo("Europe/Madrid"))


def leer_json(f, defecto=None):
    try:
        return json.loads(Path(f).read_text())
    except Exception:
        return defecto


def ruta_db():
    return Path(os.environ.get("RO_DB") or AQUI / "local.db")


def conectar(db=None):
    if S is not None and db is None:
        return S.conectar()
    if db is None and os.environ.get("DATABASE_URL"):   # N-17: un cron de la nube trabaja sobre la misma base que servir.py, no sobre una SQLite vacía
        sys.path.insert(1, str(AQUI / "despliegue"))
        import base as BASE_PG
        return BASE_PG.conectar()
    con = sqlite3.connect(str(db or ruta_db()), timeout=20)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=20000")
    return con


def preparar(con):
    # executescript confirma implícitamente cualquier transacción previa. No usarlo
    # sobre conexiones prestadas: las acciones del caller deben seguir reversibles.
    sentencia = ""
    for linea in TABLAS_SQL.splitlines(keepends=True):
        sentencia += linea
        if sqlite3.complete_statement(sentencia):
            con.execute(sentencia)
            sentencia = ""
    if sentencia.strip():
        raise ValueError("Esquema de sincronía incompleto")


def conf():
    base = dict(CONF_DEF)
    extra = (P.REGLAS.get("sincronia") if P is not None else (leer_json(AQUI / "reglas_permisos.json", {}) or {}).get("sincronia")) or {}
    base.update({k: v for k, v in extra.items() if not k.startswith("_")})
    return base


def marca(clave):
    """La huella que el cambio deja en ClickUp (comentario, horas, tarea o mensaje) para saber si ya está: nunca duplica."""
    return f"ro:{clave[:10]}"


def norm(t):
    return re.sub(r"\s+", " ", str(t or "")).strip().lower()


def limpio(t, tope=2000):
    t = str(t or "")
    if S is not None and hasattr(S, "limpiar_texto"):
        try:
            t = S.limpiar_texto(t)
        except Exception:
            pass
    return t[:tope]


# =================================================================== interruptor (lo activa Tomás)
# N-20 · los interruptores viven en la base (tabla `interruptor`, solo se añaden filas; manda la última de cada nombre) y
# el fichero queda de respaldo. En la nube `data/` se reemplaza con cada versión publicada y el fichero se perdería.
NOMBRES_INTERRUPTOR = ("clickup_real", "chat_puente")
_INT_BASE = {"t": 0.0, "filas": None}
_INT_SEGUNDOS = 5


def _interruptor_base():
    """{nombre: {valor, quien, cuando}} con la última fila de cada nombre. {} si no hay tabla, ni base, ni filas."""
    if _INT_BASE["filas"] is not None and time.monotonic() - _INT_BASE["t"] < _INT_SEGUNDOS:
        return _INT_BASE["filas"]
    filas = {}
    if S is not None or os.environ.get("DATABASE_URL") or ruta_db().exists():       # nunca crear una SQLite vacía por mirar
        try:
            con = conectar()
            try:
                for r in con.execute("SELECT nombre, valor, quien, cuando FROM interruptor WHERE id IN (SELECT MAX(id) FROM interruptor GROUP BY nombre)"):
                    filas[r["nombre"]] = {"valor": r["valor"], "quien": r["quien"], "cuando": r["cuando"]}
            finally:
                con.close()
        except Exception:                          # sin tabla o base apagada: manda el fichero, como antes
            filas = {}
    _INT_BASE.update(t=time.monotonic(), filas=filas)
    return filas


def _cfg_interruptor():
    """El fichero de siempre, con lo que diga la base por encima (por nombre)."""
    cfg = dict(leer_json(INTERRUPTOR, {}) or {})
    base = _interruptor_base()
    r = base.get("clickup_real")
    if r:
        cfg.update(clickup_real=str(r["valor"]).strip().lower() == "true", activado_por=r["quien"], activado_el=r["cuando"])
    r = base.get("chat_puente")
    if r:
        cfg["chat_puente"] = r["valor"]
    return cfg


def poner_interruptor(nombre, valor, quien, motivo, con=None):
    """Cambia un interruptor: deja su fila en `interruptor` y su rastro en `registro`. Encender exige a quien manda
    (`conf()["activa"]`). NO enciende nada por sí solo: ClickUp real sigue pidiendo RO_CLICKUP_REAL=si y la llave de servicio."""
    if nombre not in NOMBRES_INTERRUPTOR:
        raise ValueError(f"Interruptor desconocido: {nombre}")
    texto = ("true" if valor else "false") if isinstance(valor, bool) else str(valor)
    if nombre == "chat_puente" and texto not in ("apagado", "simulacion", "real"):
        raise ValueError("El puente de chat solo vale apagado, simulacion o real.")
    if not quien or not str(motivo or "").strip():
        raise ValueError("Hace falta quién lo cambia y el motivo.")
    enciende = texto in ("true", "real")
    if enciende and quien != conf()["activa"]:
        raise PermissionError("Solo lo enciende " + conf()["activa"] + ".")
    sv = S
    if sv is None:
        import servir as sv          # el rastro encadenado es el de servir.py (la tubería lo importa igual que avisos)
    sv.registrar(quien, "interruptor", f"interruptor_{nombre}", nombre, {"valor": texto}, motivo=str(motivo)[:300])
    propia = con is None
    con = con or conectar()
    try:
        if isinstance(con, sqlite3.Connection):       # SQLite sin el esquema al día (la tubería suelta): la tabla se crea sola
            con.execute("CREATE TABLE IF NOT EXISTS interruptor (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, valor TEXT NOT NULL, "
                        "quien TEXT NOT NULL, motivo TEXT, cuando TEXT NOT NULL DEFAULT (datetime('now')))")
        con.execute("INSERT INTO interruptor (nombre, valor, quien, motivo) VALUES (?,?,?,?)", (nombre, texto, quien, str(motivo)[:300]))
        if propia:
            con.commit()
    finally:
        if propia:
            con.close()
    _INT_BASE.update(t=0.0, filas=None)


def interruptor():
    """ClickUp real necesita LAS TRES cosas: el interruptor (la base o, de respaldo, el fichero: clickup_real: true +
    activado_por «tomas»), RO_CLICKUP_REAL=si en el entorno y la llave del usuario de servicio (se comprueba al usarla).
    El puente de chat: «apagado» | «simulacion» | «real» (este último, además, con ClickUp real activo)."""
    cfg = _cfg_interruptor()
    firma = cfg.get("activado_por") == conf()["activa"]
    env = os.environ.get("RO_CLICKUP_REAL", "").strip().lower() == "si"
    real = bool(cfg.get("clickup_real")) and firma and env
    puente = str(os.environ.get("RO_SINC_PUENTE_MODO") or cfg.get("chat_puente") or "apagado")
    if puente not in ("apagado", "simulacion", "real"):
        puente = "apagado"
    if puente == "real" and not real:
        puente = "simulacion" if os.environ.get("RO_SINC_PUENTE_MODO") == "real" else "apagado"
    canales = {"clickup": real, "chat": real and puente == "real"}
    return {"reales": real, "canales": canales, "chat_puente": puente, "fichero": bool(cfg.get("clickup_real")) and firma, "entorno": env,
            "activado_por": cfg.get("activado_por"), "activado_el": cfg.get("activado_el"),
            "texto": "ClickUp real activo: cada cambio sale, se comprueba en ClickUp y, si no está, avisa" if real
            else "ClickUp en simulación · lo activa Tomás (los cambios quedan guardados aquí)"}


def canal_real(canal):
    return interruptor()["canales"].get(canal, False)


# =================================================================== qué es cada acción en ClickUp (lo decide el servidor)
#218: dos slots documentales, no datos ni permisos de una sesión.
_DOCUMENTOS_TAREA = {}
_INDICE_TAREA = {"documentos": None, "por_id": {}}
_CANDADO_DOCUMENTOS_TAREA = threading.RLock()
_MT = {"mtime": None, "doc": {}, "por_id": {}}


def _firma_documento_tarea(path):
    try:
        st = path.stat()
        return (str(path.absolute()), st.st_dev, st.st_ino, st.st_mtime_ns, st.st_ctime_ns, st.st_size)
    except OSError:
        return None


def _documento_tarea(slot, path):
    """Una lectura por versión exacta; errores/races no recuperan copia vieja."""
    with _CANDADO_DOCUMENTOS_TAREA:
        for _ in range(2):
            antes = _firma_documento_tarea(path)
            if antes is None:
                previo = _DOCUMENTOS_TAREA.get(slot)
                if previo and previo[0] is None:
                    return previo[1]
                _DOCUMENTOS_TAREA[slot] = (None, {})
                return _DOCUMENTOS_TAREA[slot][1]
            previo = _DOCUMENTOS_TAREA.get(slot)
            if previo and previo[0] == antes:
                return previo[1]
            doc = leer_json(path, {})
            despues = _firma_documento_tarea(path)
            if antes == despues:
                doc = doc if isinstance(doc, dict) else {}
                _DOCUMENTOS_TAREA[slot] = (despues, doc)
                return doc
        _DOCUMENTOS_TAREA.pop(slot, None)
        return {}


def _produccion():
    return _documento_tarea("produccion", DATA / "produccion" / "produccion.json")


def _mi_trabajo():
    """Documento y catálogo de la misma versión; incluye inode/ctime/tamaño."""
    with _CANDADO_DOCUMENTOS_TAREA:
        d = _documento_tarea("mi_trabajo", DATA / "mi_trabajo" / "mi_trabajo.json")
        if _MT["doc"] is not d:
            _MT.update(mtime=_DOCUMENTOS_TAREA.get("mi_trabajo", (None,))[0], doc=d,
                       por_id={str(r.get("id")): r for r in d.get("tareas") or [] if isinstance(r, dict)})
        return d


def _mi_trabajo_tarea(ref):
    with _CANDADO_DOCUMENTOS_TAREA:
        _mi_trabajo()
        return _MT["por_id"].get(str(ref or ""))


def _indice_tareas_documentales(d, mi):
    """Preserva exactamente prioridad cola/revisiones/fallback y autores."""
    with _CANDADO_DOCUMENTOS_TAREA:
        previo = _INDICE_TAREA["documentos"]
        if previo is not None and previo[0] is d and previo[1] is mi:
            return _INDICE_TAREA["por_id"]
        produccion, trabajo, ultimas = {}, {}, {}
        for r in d.get("cola") or []:
            if not isinstance(r, dict):
                continue
            ref = str(r.get("id"))
            out = produccion.setdefault(ref, {"id": ref, "nombre": r.get("tarea"), "estado": r.get("estado"), "cli": r.get("cli"), "autores": set()})
            out["autores"].add(r.get("persona_id"))
        for r in d.get("revisiones") or []:
            if not isinstance(r, dict):
                continue
            ref = str(r.get("id"))
            out = produccion.setdefault(ref, {"id": ref, "nombre": r.get("tarea"), "estado": r.get("estado"), "cli": r.get("cliente_id"), "autores": set()})
            out["estado"] = r.get("estado") or out["estado"]
            out["cli"] = out["cli"] or r.get("cliente_id")
        for r in mi.get("tareas") or []:
            if not isinstance(r, dict):
                continue
            ref = str(r.get("id"))
            out = trabajo.setdefault(ref, {"id": ref, "nombre": r.get("tarea"), "estado": r.get("estado"), "cli": r.get("cli"), "autores": set()})
            out["autores"].add(r.get("persona_id"))
            ultimas[ref] = r
        todos = dict(trabajo)
        todos.update(produccion)
        for ref, out in todos.items():
            out["visto"] = d.get("generado") if ref in produccion else mi.get("generado")
            mt = ultimas.get(ref)
            if mt:
                out["vence"] = mt.get("vence")
                out["lista_id"] = mt.get("lista_id")
        _INDICE_TAREA.update(documentos=(d, mi), por_id=todos)
        return todos


def tarea(ref):
    """Lookup documental, no autoridad: las guardias actuales se aplican fuera."""
    from copy import deepcopy
    ref = str(ref or "")
    d, mi = _produccion(), _mi_trabajo()
    out = _indice_tareas_documentales(d, mi).get(ref)
    return deepcopy(out) if out is not None else None


def estados_de_tarea(ref):
    """Estados del catálogo real de SU lista leído por el extractor. [] si no se sabe."""
    r = _mi_trabajo_tarea(ref)
    return list((_mi_trabajo().get("estados_lista") or {}).get((r or {}).get("lista_id") or "", []))


def estados_hecha_de_tarea(ref):
    """El atajo sólo admite nombres configurados con tipo final acreditado en SU lista."""
    r = _mi_trabajo_tarea(ref)
    lid = (r or {}).get('lista_id')
    datos = _mi_trabajo()
    catalogos = datos.get('estados_detalle') if isinstance(datos, dict) else None
    filas = catalogos.get(lid, []) if isinstance(catalogos, dict) else []
    if not isinstance(filas, list) or not filas:
        return []
    tipos = {}
    for fila in filas:
        if not isinstance(fila, dict) or not isinstance(fila.get('estado'), str):
            return []
        nombre = fila['estado']
        if nombre in tipos:
            return []  # Catálogo ambiguo: elegir explícitamente tras actualizar.
        tipos[nombre] = fila.get('tipo')
    hay = estados_de_tarea(ref)
    return [nombre for nombre in conf().get('estados_hecha', [])
            if nombre in hay and tipos.get(nombre) in ('done', 'closed')]


def _reglas_piezas():
    if P is not None:
        return P.REGLAS.get("revision_piezas") or {}
    return (leer_json(AQUI / "reglas_permisos.json", {}) or {}).get("revision_piezas") or {}


def _personas():
    if S is not None:
        return S.E.crudo.get("personas") or []
    return leer_json(DATA / "personas.json", []) or []


def _persona(pid):
    return next((p for p in _personas() if p.get("id") == pid), {}) if pid else {}


def _cliente_nombre(cid):
    if not cid:
        return None
    for c in (S.E.crudo["clientes"] if S is not None else leer_json(DATA / "clientes.json", []) or []):
        if c.get("id") == cid:
            return c.get("nombre")
    return cid


CAMPOS_NAVEGADOR = ("a", "estado", "estado_nuevo", "status", "task_id", "tarea_id", "lista", "list_id", "cambio", "valor", "asignado",
                    "usuario", "canal_id", "destino")


def traducir(a):
    """Acción de la cola → (canal, objeto, cambio, base, ignorado). El servidor decide el objeto y el cambio con SUS datos."""
    c = conf()
    try:
        vp = json.loads(a["vista_previa"] or "null")
    except ValueError:
        vp = None
    vp = vp if isinstance(vp, dict) else {}
    tipo, ref, texto = a["tipo"], str(a["objeto"] or ""), a["texto"]
    ignorado = {k: str(vp.get(k))[:80] for k in CAMPOS_NAVEGADOR if k in vp}
    if tipo in c["tipos_chat"]:
        objeto = {"tipo": "canal", "ref": ref, "nombre": str(vp.get("canal") or "Canal de ClickUp")[:80], "resuelto": bool(re.fullmatch(r"[\w\-]{3,80}", ref))}
        cambio = {"campo": "mensaje", "texto": limpio(texto)}
        return "chat", objeto, cambio, None, ignorado
    clase = c["tipos_clickup"].get(tipo, "otro")
    if clase == "crear_tarea":
        nombre = (vp.get("tarea") if isinstance(vp.get("tarea"), str) else None) or ref
        objeto = {"tipo": "lista", "ref": f"lista:{a['cliente_id'] or 'sin-cliente'}", "nombre": f"Lista de {_cliente_nombre(a['cliente_id']) or 'sin cliente'}",
                  "resuelto": False}
        return "clickup", objeto, {"campo": "crear_tarea", "nombre": limpio(nombre, 200), "descripcion": limpio(texto)}, None, ignorado
    if clase == "otro":
        objeto = {"tipo": "otro", "ref": ref[:80] or "—", "nombre": ref[:80], "resuelto": False}
        return "clickup", objeto, {"campo": "otro", "tipo": tipo}, None, ignorado
    t = tarea(ref)
    objeto = {"tipo": "tarea", "ref": ref, "nombre": (t or {}).get("nombre") or f"Tarea {ref}", "url": f"https://app.clickup.com/t/{ref}",
              "resuelto": bool(t)}
    base = {"estado": (t or {}).get("estado"), "visto": (t or {}).get("visto")} if t else None
    if clase == "estado":
        destinos = c["destinos_mover"]
        pedido = vp.get("a")
        destino = pedido if pedido in destinos else destinos[0]
        cambio = {"campo": "estado", "valor": destino}
    elif clase == "estado_hecha":
        # Ni nombre por sí solo ni cualquier final (podría ser «rechazado»).
        cambio = {"campo": "estado", "valor": next(iter(estados_hecha_de_tarea(ref)), None)}
    elif clase == "estado_libre":
        # Mi trabajo: solo un estado que exista en SU lista (lo dice el servidor con sus datos); si no, el primero de mover
        hay = estados_de_tarea(ref)
        pedido = vp.get("a") if isinstance(vp.get("a"), str) else None
        cambio = {"campo": "estado", "valor": pedido if pedido in hay else None}
        if pedido and pedido not in hay:
            ignorado["a"] = str(pedido)[:80]
    elif clase == "fecha":
        dia = str(vp.get("dia") or "")
        cambio = {"campo": "fecha", "valor": dia if re.fullmatch(r"\d{4}-\d{2}-\d{2}", dia) else None}
        base = {"vence": (t or {}).get("vence"), "visto": (t or {}).get("visto")} if t else None
    elif clase == "estado_revision":
        regla = ((_reglas_piezas().get("por_estado") or {}).get((t or {}).get("estado")) or {})
        cambio = {"campo": "estado", "valor": regla.get("a") or "revisión project manager"}
    elif clase == "estado_cambios":
        coment = vp.get("comentario") if isinstance(vp.get("comentario"), str) else texto
        cambio = {"campo": "estado", "valor": _reglas_piezas().get("pedir_cambios_a") or "corrección", "comentario": limpio(coment)}
    elif clase == "comentario":
        cambio = {"campo": "comentario", "texto": limpio(texto)}
        base = None
    elif clase == "horas":
        try:
            minutos = int(vp.get("minutos") or 0)
        except (TypeError, ValueError):
            minutos = 0
        dia = str(vp.get("dia") or "")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", dia):
            dia = madrid(ahora_utc()).strftime("%Y-%m-%d")
        cambio = {"campo": "horas", "minutos": max(0, min(minutos, 720)), "dia": dia, "persona": a["quien"], "nota": limpio(texto, 300)}
        base = None
    elif clase == "asignado":
        pid = vp.get("persona") if isinstance(vp.get("persona"), str) else None
        p = _persona(pid)
        cambio = {"campo": "asignado", "persona": pid if p.get("activo") else None, "usuario_clickup": p.get("clickup_id")}
    else:
        cambio = {"campo": "otro", "tipo": tipo}
    if vp.get('transicion_produccion') is True:
        #209: la cola debe conservar el destino autorizado; nunca fallback legado
        # si fuente/regla cambia entre INSERT y traducción. "otro" no se envía.
        try:
            derivado = destino_produccion_recibo(tipo, ref, vp.get('expected_estado'), vp)
            coherente = (a['modulo'] == 'produccion' and tipo in ('pieza_aprobar', 'pieza_pedir_cambios', 'mover_estado')
                         and vp.get('transicion_tablero') is not True and derivado is not None
                         and derivado == vp.get('a') and cambio.get('campo') == 'estado' and cambio.get('valor') == derivado)
        except (TypeError, ValueError, KeyError, AttributeError):
            coherente = False
        if not coherente:
            cambio = {'campo': 'otro', 'tipo': tipo, 'motivo': 'Transición de Producción sin destino exacto acreditado; requiere revisión de fuente y catálogo.'}
    if cambio.get("campo") == "estado" and cambio.get("valor") not in estados_de_tarea(ref):
        cambio = {"campo": "otro", "tipo": tipo, "motivo": "Estado no confirmado en el catálogo real de esta lista."}
    return "clickup", objeto, cambio, base, ignorado


def es_de_clickup(herramienta, tipo):
    return herramienta == "clickup"


def tarea_tocable(real, ref):
    """¿Puede la persona REAL tocar esta tarea? Su autor, el jefe del autor, operaciones o dirección (la misma regla de
    servir.py para mover y comentar). La tarea la saca el servidor de Producción."""
    t = (S.tarea_de_produccion(ref) if S is not None and hasattr(S, "tarea_de_produccion") else None) or tarea(ref)
    if not t:
        return None, "No encuentro esa tarea en Producción: no se toca desde la app."
    jefes = {_persona(a).get("jefe") for a in t["autores"] if a}
    if real["id"] in t["autores"] or real["id"] in jefes or set(real.get("puestos") or []) & {"direccion", "operaciones"}:
        return t, None
    return None, "Esa tarea no es tuya ni de tu equipo."


# =================================================================== crear cambios y añadir pasos
def paso(con, cambio_id, estado, evento, *, quien="sistema", intento=0, motivo=None, detalle=None, hora=None):
    assert estado in ESTADOS, estado
    con.execute("INSERT INTO sinc_pasos (cambio_id, estado, evento, hora, quien, intento, motivo, detalle) VALUES (?,?,?,?,?,?,?,?)",
                (cambio_id, estado, evento, txt_hora(hora or ahora_utc()), quien, intento, motivo,
                 json.dumps(detalle, ensure_ascii=False) if detalle is not None else None))


def crear_cambio(con, *, clave, quien, canal, tipo, objeto, cambio, base=None, cliente_id=None, modulo=None, accion_id=None,
                 mensaje_id=None, modo=None, ignorado=None, hora=None):
    previa = con.execute("SELECT id FROM sinc_cambios WHERE clave=?", (clave,)).fetchone()
    if previa:
        return previa["id"], False
    modo = modo or ("real" if canal_real(canal) else "simulado")
    try:
        cur = con.execute("INSERT INTO sinc_cambios (clave, accion_id, mensaje_id, creado, quien, canal, tipo, objeto, objeto_ref, cliente_id, modulo, cambio, base, ignorado, modo) "
                          "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (clave, accion_id, mensaje_id, txt_hora(hora or ahora_utc()), quien, canal, tipo, json.dumps(objeto, ensure_ascii=False),
                           str(objeto.get("ref")), cliente_id, modulo, json.dumps(cambio, ensure_ascii=False),
                           json.dumps(base, ensure_ascii=False) if base else None, json.dumps(ignorado, ensure_ascii=False) if ignorado else None, modo))
    except sqlite3.IntegrityError:                     # otro hilo o la tubería lo creó a la vez: es el mismo cambio
        previa = con.execute("SELECT id FROM sinc_cambios WHERE clave=? OR (accion_id IS NOT NULL AND accion_id=?) OR (mensaje_id IS NOT NULL AND mensaje_id=?)",
                             (clave, accion_id, mensaje_id)).fetchone()
        return (previa["id"] if previa else None), False
    cid = cur.lastrowid
    if modo == "simulado":
        sin_lista = cambio.get("campo") == "crear_tarea" and not objeto.get("resuelto")      # N-19: se dice desde el principio
        paso(con, cid, "simulado", "creado", quien=quien, motivo=LLANO["simulado"] + (" " + LLANO["sin_lista"] if sin_lista else ""),
             detalle={"ignorado": ignorado} if ignorado else None, hora=hora)
    else:
        paso(con, cid, "pendiente", "en_cola", quien=quien, motivo=f"{TEXTO_PENDIENTE}: en cola para salir.",
             detalle={"ignorado": ignorado} if ignorado else None, hora=hora)
    return cid, True


def clave_accion(aid):
    return hashlib.sha256(f"sinc:accion:{aid}".encode()).hexdigest()[:32]


def sincronizar(con=None):
    """Acciones de la cola que van a ClickUp → cambios (uno por acción; idempotente por la clave)."""
    cerrar = con is None
    con = con or conectar()
    try:
        preparar(con)
        hechos = []
        filas = con.execute("SELECT a.* FROM acciones a LEFT JOIN sinc_cambios s ON s.accion_id = a.id "
                            "WHERE s.id IS NULL AND a.herramienta = 'clickup' ORDER BY a.id").fetchall()
        for a in filas:
            canal, objeto, cambio, base, ignorado = traducir(a)
            cid, nuevo = crear_cambio(con, clave=clave_accion(a["id"]), quien=a["quien"], canal=canal, tipo=a["tipo"], objeto=objeto,
                                      cambio=cambio, base=base, cliente_id=a["cliente_id"], modulo=a["modulo"], accion_id=a["id"],
                                      ignorado=ignorado, hora=leer_hora(a["creada"]))
            if nuevo:
                hechos.append(cid)
        if cerrar:
            con.commit()
        return hechos
    finally:
        if cerrar:
            con.close()


def fila(con, cid):
    r = con.execute("SELECT * FROM sinc_cambios WHERE id=?", (cid,)).fetchone()
    return dict(r) if r else None


def pasos_de(con, cid):
    return [dict(r) for r in con.execute("SELECT * FROM sinc_pasos WHERE cambio_id=? ORDER BY id", (cid,))]


def estado_actual(con, cid):
    r = con.execute("SELECT * FROM sinc_pasos WHERE cambio_id=? AND evento NOT IN ('aviso','reintento_simulado','espera') ORDER BY id DESC LIMIT 1", (cid,)).fetchone()
    return dict(r) if r else None


def detalle_de(p):
    try:
        return json.loads(p.get("detalle") or "{}") or {}
    except ValueError:
        return {}


def intentos(con, cid):
    return con.execute("SELECT count(*) FROM sinc_pasos WHERE cambio_id=? AND evento IN ('enviado','error','reintento_programado')", (cid,)).fetchone()[0]


def base_vigente(con, c):
    """La base contra la que se mira el conflicto: la del cambio o, si la persona eligió «lo de la app», la de ClickUp de
    ese momento (así no vuelve a salir el mismo conflicto)."""
    for p in reversed(pasos_de(con, c["id"])):
        d = detalle_de(p)
        if "base_nueva" in d:
            return d["base_nueva"]
    return json.loads(c["base"]) if c.get("base") else None


# =================================================================== proveedores (el ClickUp real y uno simulado)
class ErrorSinc(Exception):
    """tipo: token | permiso | no_existe | destinatario | rechazo | red | tiempo | caida | limite | apagado | no_soportado."""
    def __init__(self, tipo, texto=""):
        super().__init__(texto or tipo)
        self.tipo = tipo


class Proveedor:
    """leer() y comprobar() SOLO leen; aplicar() es lo único que escribe."""
    nombre = "base"
    real = False

    def comprobar(self):
        raise NotImplementedError

    def leer(self, c):          # → {"existe", "estado", "actualizado" (datetime UTC), "marcas": set, "asignados": set}
        raise NotImplementedError

    def aplicar(self, c):
        raise NotImplementedError

    def leer_canal(self, ref):  # chat (puente): [{"id", "texto", "autor", "fecha", "editado", "borrado", "hilo_de"}]
        return []


class ClickUpSimulado(Proveedor):
    """ClickUp FALSO en memoria para las pruebas de extremo a extremo. Nunca toca nada de fuera.
    guion = {clave: {"aplicar": ["caida" | "red" | "red_pero_aplicado" | "token" | "rechazo" | "ok", …],
                     "fuera": "<estado que pone otra persona en ClickUp>", "fuera_cuando": "antes" | "despues", "perdido": bool}}
    caida = True: cualquier llamada falla (ClickUp no responde). llave_mala = True: 401 en todo."""
    nombre = "simulado"

    def __init__(self, tareas=None, guion=None):
        self.tareas = tareas or {}
        self.guion = guion or {}
        self.canales = {}
        self.caida = False
        self.llave_mala = False
        self.llamadas = []

    def _puerta(self, op, c=None):
        self.llamadas.append((op, (c or {}).get("clave")))
        if self.llave_mala:
            raise ErrorSinc("token", "401 · llave caducada")
        if self.caida:
            raise ErrorSinc("caida", "503 · ClickUp no responde")

    def _t(self, c):
        o = json.loads(c["objeto"])
        if o["tipo"] == "canal":
            return None
        t = self.tareas.get(o["ref"])
        if t is None:
            raise ErrorSinc("no_existe", f"no existe {o['ref']}")
        return t

    def comprobar(self):
        self._puerta("comprobar")
        return {"ok": True, "usuario": "servicio", "rol": "miembro"}

    def leer(self, c):
        self._puerta("leer", c)
        g = self.guion.get(c["clave"]) or {}
        o = json.loads(c["objeto"])
        if o["tipo"] == "canal":
            msgs = self.canales.get(o["ref"], [])
            return {"existe": True, "marcas": {m["marca"] for m in msgs if m.get("marca")}}
        t = self._t(c)
        if g.get("fuera") and g.get("fuera_cuando", "antes") == "antes" and not g.get("_fuera_hecho"):
            t["estado"], t["actualizado"] = g["fuera"], ahora_utc() + timedelta(seconds=1)
            g["_fuera_hecho"] = True
        return {"existe": True, "estado": t.get("estado"), "actualizado": t.get("actualizado"), "marcas": set(t.get("marcas") or ()),
                "asignados": set(t.get("asignados") or ()), "vence": t.get("vence")}

    def aplicar(self, c):
        self._puerta("aplicar", c)
        g = self.guion.setdefault(c["clave"], {})
        restante = g.setdefault("_restante", list(g.get("aplicar") or ["ok"]))
        accion = restante.pop(0) if restante else "ok"
        if accion in ("caida", "red", "tiempo", "token", "rechazo", "permiso"):
            raise ErrorSinc(accion, f"simulado: {accion}")
        cam = json.loads(c["cambio"])
        o = json.loads(c["objeto"])
        if o["tipo"] == "canal":
            self.canales.setdefault(o["ref"], []).append({"id": f"m{len(self.llamadas)}", "texto": cam.get("texto"), "marca": marca(c["clave"]),
                                                         "autor": "servicio", "fecha": ahora_utc()})
        elif not g.get("perdido"):
            t = self._t(c)
            if cam["campo"] == "estado":
                t["estado"] = cam["valor"]
            if cam["campo"] == "fecha":
                t["vence"] = cam["valor"]
            if cam["campo"] in ("comentario", "horas", "crear_tarea") or cam.get("comentario"):
                t.setdefault("marcas", set()).add(marca(c["clave"]))
                t.setdefault("comentarios", []).append(cam.get("texto") or cam.get("comentario"))
            if cam["campo"] == "asignados":
                t["asignados"] = set(cam.get("usuarios") or [])
            if cam["campo"] == "asignado" and cam.get("usuario_clickup"):
                t.setdefault("asignados", set()).add(cam["usuario_clickup"])
            t["actualizado"] = ahora_utc()
            if g.get("fuera") and g.get("fuera_cuando") == "despues" and not g.get("_fuera_hecho"):
                t["estado"], t["actualizado"] = g["fuera"], ahora_utc() + timedelta(seconds=5)
                g["_fuera_hecho"] = True
        if accion == "red_pero_aplicado":
            raise ErrorSinc("red", "conexión cortada DESPUÉS de aplicar (no se sabe si entró)")
        return {"ok": True}

    def leer_canal(self, ref):
        self._puerta("leer_canal")
        return list(self.canales.get(ref, []))


class ClickUpApagado(Proveedor):
    nombre = "apagado"

    def comprobar(self):
        raise ErrorSinc("apagado", LLANO["apagado"])

    def leer(self, c):
        raise ErrorSinc("apagado", LLANO["apagado"])

    def aplicar(self, c):
        raise ErrorSinc("apagado", LLANO["apagado"])


def _llavero(nombre):
    """Una llave del llavero del Mac o, en el servidor, de RO_SECRETOS_DIR / variable. Nunca se imprime ni se guarda."""
    d = os.environ.get("RO_SECRETOS_DIR")
    if d and (Path(d) / nombre).is_file():
        return (Path(d) / nombre).read_text().strip() or None
    if os.environ.get(nombre.upper()):
        return os.environ[nombre.upper()].strip()
    try:
        return subprocess.run(["security", "find-generic-password", "-s", nombre, "-w"], capture_output=True, text=True, timeout=10).stdout.strip() or None
    except Exception:
        return None


class ProveedorClickUp(Proveedor):
    """ClickUp de verdad con la llave del USUARIO DE SERVICIO (`clickup_token_servicio`). Cualquier escritura con ClickUp
    real apagado se corta ANTES de pedir la llave y sin red. Nunca usa la llave de propietario de Tomás para escribir."""
    nombre = "clickup"
    real = True

    def __init__(self):
        self._tk = None

    def token(self):
        if self._tk:
            return self._tk
        tk = _llavero(conf()["llave_servicio"])
        if not tk:
            raise ErrorSinc("token", "falta la llave del usuario de servicio de ClickUp")
        prop = _llavero(conf()["llave_propietario"])
        if prop and hashlib.sha256(prop.encode()).digest() == hashlib.sha256(tk.encode()).digest():
            raise ErrorSinc("permiso", "la llave de servicio es la de propietario: no se usa para escribir")
        self._tk = tk
        return tk

    def pide(self, metodo, ruta, cuerpo=None, v3=False, canal="clickup"):
        import socket
        import urllib.error
        import urllib.request
        if metodo != "GET" and not canal_real(canal):
            raise ErrorSinc("apagado", "ClickUp real apagado: no se escribe")
        url = (API3 if v3 else API2) + ruta
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        req = urllib.request.Request(url, data=datos, method=metodo, headers={"Authorization": self.token(), "Content-Type": "application/json",
                                                                             "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                t = r.read().decode() or "{}"
                return json.loads(t)
        except urllib.error.HTTPError as e:
            raise ErrorSinc({401: "token", 403: "permiso", 404: "no_existe", 429: "limite"}.get(e.code, "caida" if e.code >= 500 else "rechazo"),
                            f"ClickUp {e.code}")
        except (socket.timeout, TimeoutError):
            raise ErrorSinc("tiempo", "ClickUp no contestó a tiempo")
        except urllib.error.URLError as e:
            raise ErrorSinc("red", f"red: {getattr(e, 'reason', e)}")

    def comprobar(self):
        u = self.pide("GET", "/user")
        equipo = next((t for t in (self.pide("GET", "/team").get("teams") or []) if str(t.get("id")) == TEAM), None)
        uid = (u.get("user") or {}).get("id")
        rol = next((m.get("user", {}).get("role") for m in (equipo or {}).get("members") or [] if m.get("user", {}).get("id") == uid), None)
        if rol in (1, 2):
            raise ErrorSinc("permiso", "la llave de servicio es de un propietario o administrador: debe ser un miembro")
        return {"ok": True, "usuario": uid, "rol": {3: "miembro", 4: "invitado"}.get(rol, rol)}

    def marca_comentario(self, ref, marca_ro):
        """GET Task Comments paginado; nunca interpretar truncamiento como ausencia.
        Fuente: developer.clickup.com/reference/gettaskcomments (start + start_id).
        """
        from urllib.parse import urlencode
        ruta = f"/task/{ref}/comment"
        cursores = set()
        for _ in range(40):
            comments = self.pide("GET", ruta).get("comments") or []
            if any(marca_ro in (x.get("comment_text") or "") for x in comments):
                return True
            if len(comments) < 25:
                return False
            ultimo = comments[-1]
            cursor = (str(ultimo.get("date") or ""), str(ultimo.get("id") or ""))
            if not all(cursor) or cursor in cursores:
                raise ErrorSinc("no_soportado", "Lectura de comentarios incompleta: no se reenvía sin verificar.")
            cursores.add(cursor)
            ruta = f"/task/{ref}/comment?" + urlencode({'start':cursor[0],'start_id':cursor[1]})
        raise ErrorSinc("no_soportado", "Comentarios superan la ventana verificable: no se reenvía sin verificar.")

    def leer(self, c):
        o = json.loads(c["objeto"])
        m = marca(c["clave"])
        if o["tipo"] == "canal":
            msgs = self.leer_canal(o["ref"])
            return {"existe": True, "marcas": {m for x in msgs if m in (x.get("texto") or "")}}
        if o["tipo"] != "tarea":
            raise ErrorSinc("no_soportado", LLANO["sin_lista"] if o["tipo"] == "lista" else LLANO["no_soportado"])      # N-19
        t = self.pide("GET", f"/task/{o['ref']}")
        marcas = set()
        cam = json.loads(c["cambio"])
        if cam["campo"] in ("comentario",) or cam.get("comentario"):
            if self.marca_comentario(o["ref"],m):
                marcas.add(m)
        if cam["campo"] == "horas":
            for x in self.pide("GET", f"/team/{TEAM}/time_entries?task_id={o['ref']}").get("data") or []:
                if m in (x.get("description") or ""):
                    marcas.add(m)
        act = t.get("date_updated")
        due = t.get("due_date")
        vence = datetime.fromtimestamp(int(due) / 1000, timezone.utc).astimezone(_MAD).strftime("%Y-%m-%d") if due else None
        return {"existe": True, "estado": (t.get("status") or {}).get("status"), "vence": vence,
                "actualizado": datetime.fromtimestamp(int(act) / 1000, timezone.utc).replace(tzinfo=None) if act else None,
                "marcas": marcas, "asignados": {str(a.get("id")) for a in t.get("assignees") or []}}

    def aplicar(self, c):
        o = json.loads(c["objeto"])
        cam = json.loads(c["cambio"])
        m = marca(c["clave"])
        firma = f"\n\n— {(_persona(c['quien']).get('alias') or c['quien'])} desde la app de RO · {m}"
        if o["tipo"] == "canal":
            return self.pide("POST", f"/workspaces/{TEAM}/chat/channels/{o['ref']}/messages", {"type": "message", "content": cam["texto"] + firma},
                             v3=True, canal="chat")
        if o["tipo"] != "tarea":
            raise ErrorSinc("no_soportado", LLANO["sin_lista"] if o["tipo"] == "lista" else LLANO["no_soportado"])      # N-19
        if cam["campo"] == "estado":
            self.pide("PUT", f"/task/{o['ref']}", {"status": cam["valor"]})
            if cam.get("comentario"):
                self.pide("POST", f"/task/{o['ref']}/comment", {"comment_text": cam["comentario"] + firma, "notify_all": False})
            return {"ok": True}
        if cam["campo"] == "comentario":
            if cam.get("menciones") or cam.get("entrega"):
                # API oficial comment-formatting: tags reales, no @nombre simulado.
                contenido = [{'text':cam.get('texto') or ''}]
                for x in cam.get('menciones') or []:
                    contenido.append({'type':'tag','user':{'id':int(x['usuario_clickup'])}})
                if cam.get('entrega'):
                    contenido.append({'text':'Entregable','attributes':{'link':cam['entrega']}})
                contenido.append({'text':firma})
                return self.pide("POST",f"/task/{o['ref']}/comment",{'comment':contenido,'notify_all':False})
            return self.pide("POST", f"/task/{o['ref']}/comment", {"comment_text": cam["texto"] + firma, "notify_all": False})
        if cam["campo"] == "horas":
            ini = datetime.strptime(cam["dia"] + " 09:00", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            return self.pide("POST", f"/team/{TEAM}/time_entries", {"tid": o["ref"], "start": int(ini.timestamp() * 1000),
                                                                    "duration": int(cam["minutos"]) * 60000, "description": (cam.get("nota") or "") + firma})
        if cam["campo"] == "fecha":
            if not cam.get("valor"):
                raise ErrorSinc("rechazo", "fecha no válida")
            fin = datetime.strptime(cam["valor"] + " 12:00", "%Y-%m-%d %H:%M").replace(tzinfo=_MAD)
            return self.pide("PUT", f"/task/{o['ref']}", {"due_date": int(fin.timestamp() * 1000), "due_date_time": False})
        if cam["campo"] == "asignados":
            actual = self.pide("GET", f"/task/{o['ref']}")
            actuales = {str(a.get("id")) for a in actual.get("assignees") or []}
            destino = set(cam.get("usuarios") or [])
            return self.pide("PUT", f"/task/{o['ref']}", {"assignees": {"add": [int(x) for x in destino-actuales], "rem": [int(x) for x in actuales-destino]}})
        if cam["campo"] == "asignado":
            if not cam.get("usuario_clickup"):
                raise ErrorSinc("destinatario", "esa persona no tiene usuario de ClickUp conocido")
            return self.pide("PUT", f"/task/{o['ref']}", {"assignees": {"add": [int(cam["usuario_clickup"])]}})
        raise ErrorSinc("no_soportado", LLANO["no_soportado"])

    def leer_canal(self, ref):
        d = self.pide("GET", f"/workspaces/{TEAM}/chat/channels/{ref}/messages?limit=50", v3=True)
        return [{"id": x.get("id"), "texto": x.get("content"), "autor": x.get("user_id"), "fecha": x.get("date"),
                 "editado": x.get("date_updated"), "hilo_de": x.get("parent_message_id")} for x in d.get("data") or []]


def proveedor_de(canal):
    return ProveedorClickUp() if canal_real(canal) else ClickUpApagado()


# =================================================================== ¿está ya el cambio en ClickUp?
def aplicado(c, r):
    cam = json.loads(c["cambio"])
    m = marca(c["clave"])
    campo = cam.get("campo")
    if campo == "estado":
        ok = norm(r.get("estado")) == norm(cam["valor"])
        return ok and (not cam.get("comentario") or m in (r.get("marcas") or set()))
    if campo in ("comentario", "horas", "crear_tarea", "mensaje"):
        return m in (r.get("marcas") or set())
    if campo == "asignados":
        return {str(x) for x in cam.get("usuarios") or []} == {str(x) for x in r.get("asignados") or []}
    if campo == "asignado":
        return bool(cam.get("usuario_clickup")) and str(cam["usuario_clickup"]) in {str(x) for x in r.get("asignados") or ()}
    if campo == "fecha":
        return bool(cam.get("valor")) and str(r.get("vence") or "") == cam["valor"]
    return False


def valor_app(c):
    cam = json.loads(c["cambio"])
    if cam.get("campo") == "asignados":
        return cam.get("usuarios")
    return cam.get("valor") if cam.get("campo") in ("estado", "fecha") else cam.get("usuario_clickup") if cam.get("campo") == "asignado" else None


def es_conflicto(con, c, r, desde):
    """Otro valor en ClickUp, distinto del que la app vio y del que la app quiere, y puesto DESPUÉS de `desde`."""
    cam = json.loads(c["cambio"])
    if cam.get("campo") not in ("estado", "fecha", "asignados"):
        return False
    base = base_vigente(con, c) or {}
    if cam["campo"] == "asignados":
        actual = {str(x) for x in r.get("asignados") or []}
        deseado = {str(x) for x in cam.get("usuarios") or []}
        anterior = {str(x) for x in base.get("asignados") or []}
        act = r.get("actualizado")
        return bool(actual != deseado and actual != anterior and act and desde and act >= desde)
    clave = "estado" if cam["campo"] == "estado" else "vence"
    actual = norm(r.get(clave))
    if not actual or actual == norm(cam["valor"]) or (base.get(clave) and actual == norm(base.get(clave))):
        return False
    act = r.get("actualizado")
    return bool(act and desde and act >= desde)


def reclamar_escritura(con, cid, quien, intento, ahora):
    """Claim durable en conexión propia; nunca confirmar una transacción del caller.

    No hay lease con caducidad: un proceso caído deja resultado incierto para
    verificación por lectura, nunca autorización automática para volver a escribir.
    """
    if con.in_transaction:
        return False  # Cola/decisión aún no persistida: siguiente vuelta tras commit del caller.
    dbs = con.execute("PRAGMA database_list").fetchall()
    archivo = next((r[2] for r in dbs if r[1] == "main"), "")
    if not archivo:
        return False  # Memoria/no archivo no puede garantizar recuperación durable.
    propia = sqlite3.connect(archivo, timeout=20)
    propia.row_factory = sqlite3.Row
    try:
        propia.execute("PRAGMA busy_timeout=20000")
        propia.execute("PRAGMA synchronous=FULL")
        propia.execute("BEGIN IMMEDIATE")
        c = fila(propia, cid)
        act = estado_actual(propia, cid)
        if not c or not act or act["estado"] != "pendiente" or bloqueado_por_anterior(propia, c):
            propia.rollback()
            return False
        paso(propia, cid, "enviado", "escritura_reclamada", quien=quien, intento=intento, hora=ahora,
             motivo="Envío reservado. Su resultado aún no está confirmado; comprobar antes de repetir.",
             detalle={"resultado_desconocido": True, "seguro_reintentar": False, "claim_durable": True})
        propia.commit()  # Sólo la transacción propia, ANTES de cualquier request de escritura.
        return True
    finally:
        propia.close()


# =================================================================== despachar, verificar, avisar
def ejecutar(con, cid, prov, quien="sistema", ahora=None):
    """Relee y reclama de forma durable antes de escribir. `enviado` no acredita aceptación.

    Una transacción prestada activa difiere el efecto; sólo el caller decide su commit.
    Un claim incierto se reconcilia por lectura y nunca caduca habilitando un reenvío.
    """
    ahora = ahora or ahora_utc()
    c = fila(con, cid)
    act = estado_actual(con, cid)
    if not c or not act or act["estado"] != "pendiente":
        return act and act["estado"]
    if getattr(prov, "real", False) and not canal_real(c["canal"]):
        paso(con, cid, "fallido", "apagado", quien=quien, motivo=LLANO["apagado"], detalle={"seguro_reintentar": True})
        return "fallido"
    cam = json.loads(c["cambio"])
    if cam.get("campo") == "otro" or (cam.get("campo") == "crear_tarea" and not json.loads(c["objeto"]).get("resuelto")):
        motivo = "no_soportado" if cam.get("campo") == "otro" else "destinatario"
        claro = "no_soportado" if cam.get("campo") == "otro" else "sin_lista"        # N-19: el texto de la tarea nueva es el claro
        paso(con, cid, "fallido", motivo, quien=quien, motivo=LLANO[claro], detalle={"seguro_reintentar": False})
        avisar(con, cid, claro)
        return "fallido"
    n = intentos(con, cid)
    escritura_iniciada = False
    # No publicar efectos externos sobre una cola/decisión no confirmada por su caller.
    if con.in_transaction:
        return "pendiente"
    try:
        r = prov.leer(c)
        if aplicado(c, r):
            paso(con, cid, "enviado", "ya_estaba", quien=quien, intento=n, motivo="Ya estaba en ClickUp: no se vuelve a escribir (sin duplicar).")
            return verificar(con, cid, prov, ahora=ahora)
        if es_conflicto(con, c, r, leer_hora(c["creado"])):
            return marcar_conflicto(con, cid, r, quien)
        if not reclamar_escritura(con, cid, quien, n, ahora):
            actual = estado_actual(con, cid)
            return actual["estado"] if actual else "pendiente"
        escritura_iniciada = True
        prov.aplicar(c)
        paso(con, cid, "enviado", "enviado", quien=quien, intento=n, motivo="ClickUp lo ha aceptado. Se relee para confirmarlo.",
             detalle={"proveedor": prov.nombre, "claim_durable": True, "resultado_desconocido": True, "seguro_reintentar": False})
    except ErrorSinc as x:
        if escritura_iniciada:
            # aplicar puede incluir varios requests: incluso un rechazo posterior
            # puede llegar después de una escritura aceptada. Nunca afirmar ausencia.
            paso(con, cid, "enviado", "resultado_desconocido", quien=quien, intento=n,
                 motivo="El proveedor no confirmó el resultado. Se comprueba antes de reenviar.",
                 detalle={"tipo": x.tipo, "resultado_desconocido": True, "seguro_reintentar": False})
            return "enviado"
        return _error(con, cid, x, quien, n, ahora)
    return verificar(con, cid, prov, ahora=ahora)


def _error(con, cid, x, quien, n, ahora):
    c = conf()
    if x.tipo in SEGUROS:
        esperas = c["esperas_min"]
        if n < int(c["reintentos_max"]):
            espera = esperas[min(n, len(esperas) - 1)]
            paso(con, cid, "pendiente", "reintento_programado", quien=quien, intento=n, motivo=LLANO["caida"],
                 detalle={"tipo": x.tipo, "reintentar_desde": txt_hora(ahora + timedelta(minutes=espera)), "espera_min": espera})
            avisar(con, cid, "caida", solo_agus=True)
            return "pendiente"
        paso(con, cid, "fallido", "agotado", quien=quien, intento=n, motivo=LLANO["agotado"], detalle={"tipo": x.tipo, "seguro_reintentar": True})
        avisar(con, cid, "agotado")
        return "fallido"
    if x.tipo in LLAVE:
        paso(con, cid, "fallido", "llave", quien=quien, intento=n, motivo=LLANO[x.tipo], detalle={"tipo": x.tipo, "seguro_reintentar": True, "llave": True})
        avisar(con, cid, x.tipo, solo_agus=True)
        return "fallido"
    if x.tipo == "apagado":
        paso(con, cid, "fallido", "apagado", quien=quien, intento=n, motivo=LLANO["apagado"], detalle={"seguro_reintentar": True})
        return "fallido"
    motivo = x.tipo if x.tipo in LLANO else "rechazo"
    paso(con, cid, "fallido", "error", quien=quien, intento=n, motivo=LLANO[motivo], detalle={"tipo": x.tipo, "seguro_reintentar": False})
    avisar(con, cid, motivo)
    return "fallido"


def verificar(con, cid, prov, ahora=None):
    """Relectura: confirma presencia o detecta conflicto. Un claim incierto no permite reenviar."""
    ahora = ahora or ahora_utc()
    c = fila(con, cid)
    act = estado_actual(con, cid)
    if not c or not act or act["estado"] != "enviado":
        return act and act["estado"]
    try:
        r = prov.leer(c)
    except ErrorSinc as x:
        if x.tipo in LLAVE:
            avisar(con, cid, "verificar_llave", solo_agus=True)
        else:
            avisar(con, cid, "sin_respuesta", solo_agus=True)
        return "enviado"
    if aplicado(c, r):
        paso(con, cid, "confirmado", "verificado", motivo="Está en ClickUp: se ha releído la tarea y el cambio está.",
             detalle={"valor_clickup": r.get("estado")})
        return "confirmado"
    if es_conflicto(con, c, r, leer_hora(act["hora"])):
        return marcar_conflicto(con, cid, r, "sistema")
    if detalle_de(act).get("resultado_desconocido"):
        # Una lectura sin marca no acredita ausencia histórica (ventana de horas,
        # chat truncado, consistencia eventual). Conservar bloqueo por objeto.
        return "enviado"
    if (ahora - (leer_hora(act["hora"]) or ahora)).total_seconds() >= int(conf()["gracia_min"]) * 60:
        paso(con, cid, "fallido", "no_aparece", motivo=LLANO["no_aparece"], detalle={"seguro_reintentar": True, "valor_clickup": r.get("estado")})
        avisar(con, cid, "no_aparece")
        return "fallido"
    return "enviado"


def marcar_conflicto(con, cid, r, quien):
    c = fila(con, cid)
    campo = json.loads(c["cambio"]).get("campo")
    actual = sorted(str(x) for x in r.get("asignados") or []) if campo == "asignados" else r.get("vence") if campo == "fecha" else r.get("estado")
    paso(con, cid, "conflicto", "conflicto", quien=quien, motivo=LLANO["conflicto"],
         detalle={"version_app": valor_app(c), "version_clickup": actual, "clickup_cambiado": iso_z(txt_hora(r["actualizado"])) if r.get("actualizado") else None,
                  "base": base_vigente(con, c)})
    avisar(con, cid, "conflicto")
    return "conflicto"


def bloqueado_por_anterior(con, c):
    """Orden por objeto: ¿hay un cambio ANTERIOR de la misma tarea sin terminar (pendiente, enviado, conflicto o un fallido
    que se va a reintentar)?"""
    for r in con.execute("SELECT id FROM sinc_cambios WHERE objeto_ref=? AND id<? AND modo != 'simulado' ORDER BY id", (c["objeto_ref"], c["id"])):
        a = estado_actual(con, r["id"])
        if not a:
            continue
        if a["estado"] in ("pendiente", "enviado", "conflicto"):
            return r["id"]
    return None


def despachar(con, prov, ahora=None, canal=None):
    """Pendientes en orden: cada efecto requiere conexión sin transacción prestada activa.

    Los pasos nuevos se confirman por el caller; los efectos restantes pueden quedar
    para la siguiente vuelta. No se hace commit de acciones ajenas para acelerar envíos.
    """
    ahora = ahora or ahora_utc()
    hechos = []
    llave_caida = False
    for r in con.execute("SELECT id FROM sinc_cambios WHERE modo != 'simulado'" + (" AND canal=?" if canal else "") + " ORDER BY id",
                         (canal,) if canal else ()).fetchall():
        c = fila(con, r["id"])
        a = estado_actual(con, c["id"])
        if not a or a["estado"] != "pendiente" or llave_caida:
            continue
        desde = leer_hora(detalle_de(a).get("reintentar_desde"))
        if desde and desde > ahora:
            continue
        previo = bloqueado_por_anterior(con, c)
        if previo:
            if not con.execute("SELECT 1 FROM sinc_pasos WHERE cambio_id=? AND evento='espera' AND detalle LIKE ?", (c["id"], f'%"tras": {previo}%')).fetchone():
                paso(con, c["id"], "pendiente", "espera", motivo=f"Espera a que termine el cambio n.º {previo} de la misma tarea (orden por objeto).",
                     detalle={"tras": previo})
            continue
        antes = a["estado"]
        despues = ejecutar(con, c["id"], prov, ahora=ahora)
        ult = estado_actual(con, c["id"])
        if ult and detalle_de(ult).get("llave"):
            llave_caida = True              # con la llave caída no se sigue llamando en esta vuelta
        hechos.append({"id": c["id"], "de": antes, "a": despues})
    return hechos


def reencolar_tras_llave(con, prov, quien="sistema"):
    """Cuando la llave vuelve a valer (comprobar() sin error), los fallidos POR LLAVE vuelven a la cola solos (nada había
    entrado en ClickUp: es seguro)."""
    try:
        prov.comprobar()
    except ErrorSinc:
        return []
    hechos = []
    for r in con.execute("SELECT id FROM sinc_cambios WHERE modo != 'simulado' ORDER BY id").fetchall():
        a = estado_actual(con, r["id"])
        if a and a["estado"] == "fallido" and detalle_de(a).get("llave"):
            paso(con, r["id"], "pendiente", "reintento_tras_llave", quien=quien, motivo="La llave de ClickUp vuelve a valer: vuelve a la cola (sin duplicar).")
            hechos.append(r["id"])
    return hechos


def vuelta(con, provs=None, ahora=None):
    """Lo que hace la tubería (despliegue/reconciliar_clickup.py): sincroniza, reencola lo caído por llave si ya vale,
    despacha pendientes y verifica enviados. Con ClickUp apagado solo sincroniza y cuenta."""
    preparar(con)
    nuevos = sincronizar(con)
    hechos = {"nuevos": len(nuevos), "reencolados": [], "despachados": [], "verificados": [], "chat_importados": 0}
    provs = provs or {}
    for canal in CANALES:
        prov = provs.get(canal)
        if prov is None:
            if not canal_real(canal):
                continue
            prov = provs.setdefault(canal, proveedor_de(canal))
        hechos["reencolados"] += reencolar_tras_llave(con, prov)
        hechos["despachados"] += despachar(con, prov, ahora=ahora, canal=canal)
        for r in con.execute("SELECT id FROM sinc_cambios WHERE modo != 'simulado' AND canal=? ORDER BY id", (canal,)).fetchall():
            a = estado_actual(con, r["id"])
            if a and a["estado"] == "enviado":
                hechos["verificados"].append({"id": r["id"], "a": verificar(con, r["id"], prov, ahora=ahora)})
        if canal == "chat":
            hechos["chat_importados"] = importar_chat(con, prov)
    return hechos


# =================================================================== decisiones de las personas
def puede_tocar(p, c):
    return c["quien"] == p["id"] or bool(set(p.get("puestos") or []) & set(conf()["reintentan_puestos"]))


def reintentar(con, cid, quien, prov=None):
    c = fila(con, cid)
    act = estado_actual(con, cid)
    if not c or not act:
        return {"ok": False, "codigo": 404, "error": "No existe ese cambio."}
    if act["estado"] == "conflicto":
        return {"ok": False, "codigo": 409, "error": "Hay dos versiones: elige cuál se queda antes de reintentar."}
    if c["modo"] == "simulado" or not canal_real(c["canal"]) and prov is None:
        paso(con, cid, act["estado"], "reintento_simulado", quien=quien,
             motivo="Reintento simulado: ClickUp real está apagado (lo activa Tomás). No se ha escrito nada en ClickUp.")
        return {"ok": True, "simulado": True, "estado": act["estado"]}
    if act["estado"] != "fallido":
        return {"ok": False, "codigo": 409, "error": "Solo se reintenta un cambio fallido."}
    if not detalle_de(act).get("seguro_reintentar"):
        return {"ok": False, "codigo": 409, "error": "Este fallo no es seguro reintentarlo (ClickUp lo rechazó o la tarea ya no está): míralo en ClickUp."}
    paso(con, cid, "pendiente", "reintento_pedido", quien=quien, motivo="Reintento pedido desde Envíos › ClickUp.")
    prov = prov or proveedor_de(c["canal"])
    return {"ok": True, "simulado": False, "estado": ejecutar(con, cid, prov, quien=quien)}


def elegir(con, cid, quien, gana):
    c = fila(con, cid)
    act = estado_actual(con, cid)
    if not c or not act:
        return {"ok": False, "codigo": 404, "error": "No existe ese cambio."}
    if act["estado"] != "conflicto":
        return {"ok": False, "codigo": 409, "error": "Ese cambio no está en conflicto."}
    if gana not in ("app", "clickup"):
        return {"ok": False, "codigo": 400, "error": "«gana» es app o clickup."}
    d = detalle_de(act)
    if gana == "clickup":
        paso(con, cid, "descartado", "gana_clickup", quien=quien,
             motivo=f"Se queda lo de ClickUp («{d.get('version_clickup')}»): el cambio de la app no se aplica. Queda guardado aquí.",
             detalle={"version_clickup": d.get("version_clickup")})
        return {"ok": True, "estado": "descartado"}
    paso(con, cid, "pendiente", "gana_app", quien=quien,
         motivo=f"Se queda lo de la app («{d.get('version_app')}»): vuelve a la cola y pisará lo de ClickUp.",
         detalle={"base_nueva": {("vence" if json.loads(c["cambio"]).get("campo") == "fecha" else "estado"): d.get("version_clickup")}})
    return {"ok": True, "estado": "pendiente"}


def a_mano(con, cid, quien):
    c = fila(con, cid)
    act = estado_actual(con, cid)
    if not c or not act:
        return {"ok": False, "codigo": 404, "error": "No existe ese cambio."}
    if act["estado"] in FINALES or act["estado"] == "enviado":
        return {"ok": False, "codigo": 409, "error": "Ese cambio ya está terminado o comprobándose."}
    paso(con, cid, "confirmado", "hecho_a_mano", quien=quien, motivo="Pasado a mano en ClickUp (lo dice quien lo marca; queda en el rastro).")
    return {"ok": True, "estado": "confirmado"}


# =================================================================== avisos (canales de avisos de la app)
DEP_AVISOS = {"account": "avisos-accounts", "tecnico_altas": "avisos-altas", "especialista_ghl": "avisos-crm", "jefa_crm": "avisos-crm",
              "outreach": "avisos-crm", "trafficker": "avisos-publicidad", "jefa_publicidad": "avisos-publicidad", "jefa_seo": "avisos-seo",
              "seo": "avisos-seo", "ficha_google": "avisos-seo", "web": "avisos-web", "redes": "avisos-redes", "produccion": "avisos-redes",
              "administracion": "avisos-administracion", "rrhh": "avisos-rrhh"}


def _publicar(con, canal_id, texto, clave, *, menciones=(), cliente_id=None, ver=None, datos=None):
    av = sys.modules.get("avisos")
    try:
        if av and hasattr(av, "publicar") and getattr(av, "S", None) is not None:
            return av.publicar(con, canal_id, "evento", texto, clave, quien=None, menciones=list(menciones), cliente_id=cliente_id,
                               dueno_id="agustina", ver=ver, datos=datos)
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='canal_mensajes'").fetchone():
            return None
        if con.execute("SELECT 1 FROM canal_mensajes WHERE clave=?", (clave,)).fetchone():
            return None
        cur = con.execute("INSERT INTO canal_mensajes (canal_id, tipo, quien, texto, menciones, clave, cliente_id, dueno_id, ver, datos, creado) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                          (canal_id, "evento", None, texto, json.dumps(list(menciones)), clave, cliente_id, "agustina",
                           json.dumps(ver) if ver is not None else None, json.dumps(datos, ensure_ascii=False) if datos else None, txt_hora(ahora_utc())))
        return cur.lastrowid
    except Exception:
        traceback.print_exc()
        return None


def avisar(con, cid, tipo, solo_agus=False):
    """Aviso en llano a quien hizo el cambio (en el canal de su departamento) y a Agus en #avisos-altas (copia en
    #avisos-dirección). En conflicto, con las dos versiones. Nunca con el texto de un comentario o mensaje. Uno por cambio
    y motivo (las caídas, uno por cambio)."""
    c = fila(con, cid)
    if not c:
        return []
    cf = conf()
    q = _persona(c["quien"])
    alias = q.get("alias") or c["quien"]
    o = json.loads(c["objeto"])
    cli = _cliente_nombre(c["cliente_id"])
    que = f"«{o.get('nombre') or o.get('ref')}»" + (f" ({cli})" if cli else "")
    if tipo == "conflicto":
        d = detalle_de(estado_actual(con, cid) or {})
        texto = (f"Dos versiones en ClickUp de {que}: en la app, «{d.get('version_app')}» (lo hizo {alias}); en ClickUp, «{d.get('version_clickup')}» "
                 f"(cambiado después allí). No se ha pisado nada. Elige cuál se queda en Envíos › ClickUp, cambio n.º {cid} ({alias}, o Agus, Mili o Tomás).")
    elif tipo in ("verificar_llave",):
        texto = "No puedo comprobar los cambios de ClickUp: la llave del usuario de servicio no vale. Agus: Conexiones; la renueva Tomás."
    elif tipo == "sin_respuesta":
        texto = f"ClickUp no responde al comprobar {que} (cambio n.º {cid}). Sigue guardado aquí; se vuelve a mirar en la vuelta siguiente."
    else:
        texto = f"Cambio de {alias} en ClickUp sobre {que} · {LLANO.get(tipo, LLANO['rechazo'])} Cambio n.º {cid}."
    menciones = list(dict.fromkeys(([c["quien"]] if not solo_agus else []) + list(cf["avisar_a"])))
    ver = {"puestos": cf["ven_todos_puestos"]}
    datos = {"icono": "alert", "ir": f"#/envios/clickup/{cid}", "cambio_id": cid, "motivo": tipo}
    hechos = []
    canales = [cf["canal_avisos"], cf["canal_avisos_copia"]]
    for canal in canales:
        if _publicar(con, canal, texto, f"sinc:{cid}:{tipo}:{canal}", menciones=menciones, ver=ver, datos=datos):
            hechos.append(canal)
    if not solo_agus:
        dep = next((DEP_AVISOS[x] for x in q.get("puestos") or [] if x in DEP_AVISOS), None)
        if dep and dep not in canales and _publicar(con, dep, texto, f"sinc:{cid}:{tipo}:{dep}", menciones=[c["quien"]], cliente_id=c["cliente_id"], datos=datos):
            hechos.append(dep)
    if hechos:
        a = estado_actual(con, cid)
        paso(con, cid, a["estado"] if a else "pendiente", "aviso", motivo=("Avisados Agus" if solo_agus else f"Avisados {alias} y Agus") + " en " + ", ".join("#" + x for x in hechos),
             detalle={"canales": hechos, "menciones": menciones, "motivo": tipo})
    return hechos


# =================================================================== informe diario «cambios sin reflejar»
def sin_reflejar(con, ahora=None, horas=None, preparar_base=True):
    """Lo que lleva más de X horas hecho en la app y no está en ClickUp (todo lo que no es confirmado ni descartado)."""
    if preparar_base:
        preparar(con)
    ahora = ahora or ahora_utc()
    horas = float(horas if horas is not None else conf()["horas_sin_reflejar"])
    lim = ahora - timedelta(hours=horas)
    out = []
    for r in con.execute("SELECT * FROM sinc_cambios ORDER BY id"):
        c = dict(r)
        a = estado_actual(con, c["id"])
        if not a or a["estado"] in FINALES:
            continue
        creado = leer_hora(c["creado"]) or ahora
        if creado > lim:
            continue
        o = json.loads(c["objeto"])
        out.append({"id": c["id"], "estado": a["estado"], "canal": c["canal"], "quien": c["quien"], "tipo": c["tipo"], "cliente_id": c["cliente_id"],
                    "objeto": o.get("nombre") or o.get("ref"), "url": o.get("url"), "horas": round((ahora - creado).total_seconds() / 3600, 1),
                    "motivo": a.get("motivo")})
    orden = {"conflicto": 0, "fallido": 1, "pendiente": 2, "enviado": 3, "simulado": 4}
    out.sort(key=lambda x: (orden.get(x["estado"], 9), -x["horas"]))
    por = {s: sum(1 for x in out if x["estado"] == s) for s in orden}
    return {"horas": horas, "total": len(out), "por_estado": por, "cambios": out, "generado": iso_z(txt_hora(ahora))}


def texto_informe(inf):
    if not inf["total"]:
        return f"Cambios sin reflejar en ClickUp (más de {inf['horas']:g} h): ninguno. Todo lo hecho en la app está en ClickUp."
    p = inf["por_estado"]
    partes = [f"{p[k]} {n}" for k, n in (("conflicto", "en conflicto (elegir versión)"), ("fallido", "fallidos"), ("pendiente", "pendientes de salir"),
                                          ("enviado", "comprobándose"), ("simulado", "en simulación (hay que pasarlos a mano: ClickUp real está apagado)")) if p.get(k)]
    viejo = max(inf["cambios"], key=lambda x: x["horas"])
    return (f"Cambios hechos en la app que aún NO están en ClickUp (más de {inf['horas']:g} h): {inf['total']} · " + " · ".join(partes)
            + f". El más antiguo: «{viejo['objeto']}», hace {viejo['horas']:g} h. Agus y Mili: Envíos › ClickUp, fallidos y conflictos arriba.")


def publicar_informe(con, ahora=None, forzar=False):
    """Una vez al día (desde la hora del informe, hora de Madrid) en #avisos-altas, mencionando a Agus y Mili."""
    ahora = ahora or ahora_utc()
    cf = conf()
    local = madrid(ahora)
    if not forzar and local.strftime("%H:%M") < cf["hora_informe"]:
        return {"publicado": False, "motivo": f"Aún no son las {cf['hora_informe']} (hora de Madrid)."}
    inf = sin_reflejar(con, ahora)
    dia = local.strftime("%Y-%m-%d")
    mid = _publicar(con, cf["canal_avisos"], texto_informe(inf), f"sinc_informe:{dia}", menciones=cf["informe_a"],
                    ver={"puestos": cf["ven_todos_puestos"]}, datos={"icono": "clock", "ir": "#/envios/clickup", "total": inf["total"]})
    return {"publicado": bool(mid), "motivo": None if mid else "El informe de hoy ya estaba publicado.", "informe": inf}


# =================================================================== puente de chat (opción b de 51) · APAGADO
def puente():
    return leer_json(PUENTE, {}) or {}


def canal_clickup_de(canal_app):
    return ((puente().get("canales") or {}).get(canal_app) or None) if canal_app else None


def encolar_chat(con, mensaje, canal_app):
    """Un mensaje de un grupo de la app → copia en la cola hacia el chat de ClickUp. SOLO con el puente encendido
    (simulación o real) y el grupo emparejado en data/sincronia/puente_chat.json. Apagado (hoy): no hace nada."""
    modo = interruptor()["chat_puente"]
    destino = canal_clickup_de(canal_app)
    if modo == "apagado" or not destino or not mensaje:
        return None
    preparar(con)
    padre_ext = None
    if mensaje["hilo_de"]:
        p = con.execute("SELECT id FROM sinc_cambios WHERE mensaje_id=?", (mensaje["hilo_de"],)).fetchone()
        padre_ext = f"cambio:{p['id']}" if p else None
    cid, _ = crear_cambio(con, clave=hashlib.sha256(f"sinc:mensaje:{mensaje['id']}".encode()).hexdigest()[:32], quien=mensaje["quien"] or "sistema",
                          canal="chat", tipo="chat_respuesta" if mensaje["hilo_de"] else "chat_mensaje",
                          objeto={"tipo": "canal", "ref": destino, "nombre": f"Chat de ClickUp de #{canal_app}", "resuelto": True, "canal_app": canal_app},
                          cambio={"campo": "mensaje", "texto": mensaje["texto"], "hilo_de_app": mensaje["hilo_de"], "hilo_de": padre_ext},
                          cliente_id=mensaje["cliente_id"], modulo="chat-equipo", mensaje_id=mensaje["id"],
                          modo="real" if modo == "real" else "simulado")
    return cid


def importar_chat(con, prov):
    """ClickUp → app (puente encendido en real o en prueba): mensajes nuevos del canal emparejado entran en el grupo de la
    app (clave cu:<id>, nunca dos veces). Editado en ClickUp: nota en el hilo con el texto nuevo (el original se conserva).
    Borrado en ClickUp: nota «borrado en ClickUp» (aquí no se borra nada). Lo propio de la app (con su marca) no vuelve."""
    if interruptor()["chat_puente"] == "apagado" and getattr(prov, "real", False):
        return 0
    if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='canal_mensajes'").fetchone():
        return 0
    n = 0
    for canal_app, ref in (puente().get("canales") or {}).items():
        try:
            msgs = prov.leer_canal(ref)
        except ErrorSinc:
            continue
        vistos = {m["id"] for m in msgs}
        for m in msgs:
            if re.search(r"ro:[0-9a-f]{10}", str(m.get("texto") or "")) or m.get("marca"):
                continue
            ya = con.execute("SELECT id FROM canal_mensajes WHERE clave=?", (f"cu:{m['id']}",)).fetchone()
            if not ya:
                _insertar_mensaje(con, canal_app, f"[ClickUp] {limpio(m.get('texto'))}", f"cu:{m['id']}")
                n += 1
            elif m.get("editado"):
                _insertar_mensaje(con, canal_app, f"Editado en ClickUp: {limpio(m.get('texto'))}", f"cu:{m['id']}:ed:{m['editado']}", hilo_de=ya["id"])
        for r in con.execute("SELECT id, clave FROM canal_mensajes WHERE canal_id=? AND clave LIKE 'cu:%' AND clave NOT LIKE 'cu:%:%'", (canal_app,)).fetchall():
            ext = r["clave"][3:]
            if ext not in vistos and msgs:
                _insertar_mensaje(con, canal_app, "Borrado en ClickUp (aquí se conserva el original).", f"cu:{ext}:borrado", hilo_de=r["id"])
    return n


def _insertar_mensaje(con, canal, texto, clave, hilo_de=None):
    if con.execute("SELECT 1 FROM canal_mensajes WHERE clave=?", (clave,)).fetchone():
        return None
    return con.execute("INSERT INTO canal_mensajes (canal_id, tipo, quien, texto, hilo_de, clave, creado) VALUES (?,?,?,?,?,?,?)",
                       (canal, "evento", None, texto, hilo_de, clave, txt_hora(ahora_utc()))).lastrowid


# =================================================================== API (enganche a servir.py)
def ve_todos(p):
    return bool(set(p.get("puestos") or []) & set(conf()["ven_todos_puestos"]))


def _visible(real, persona, c):
    return all(c["quien"] == x["id"] or ve_todos(x) for x in (real, persona))


def _abre_cliente(persona, cid):
    if not cid or S is None:
        return True
    cp = P.contexto(persona, S.E.crudo)
    return P.ver(persona, {"tipo": "cliente_detalle", "cliente_id": cid}, cp)["ok"]


ESTADO_TEXTO = {"simulado": TEXTO_PENDIENTE + " (simulación)", "pendiente": TEXTO_PENDIENTE, "enviado": "Envío sin confirmar · comprobar ClickUp",
                "confirmado": "En ClickUp (comprobado)", "fallido": "No está en ClickUp", "conflicto": "Dos versiones: elige", "descartado": "Se quedó lo de ClickUp"}


def describir(cam):
    campo = cam.get("campo")
    if campo == "estado":
        return f"Estado → «{cam['valor']}»" + (" y comentario" if cam.get("comentario") else "")
    if campo == "comentario":
        return "Comentario en la tarea"
    if campo == "fecha":
        return f"Fecha límite → {cam.get('valor') or '¿?'}"
    if campo == "horas":
        return f"Imputar {cam.get('minutos')} min el {cam.get('dia')}"
    if campo == "asignado":
        return f"Asignar a {(_persona(cam.get('persona')).get('alias') or cam.get('persona') or '¿?')}"
    if campo == "crear_tarea":
        return f"Crear tarea «{cam.get('nombre')}»"
    if campo == "mensaje":
        return "Mensaje en el chat" + (" (en un hilo)" if cam.get("hilo_de_app") else "")
    return f"«{cam.get('tipo')}» (sin traductor: a mano)"


def a_json(con, c, real, persona, con_pasos=True):
    ps = pasos_de(con, c["id"])
    act = next((x for x in reversed(ps) if x["evento"] not in EVENTOS_NOTA), ps[-1] if ps else {})
    ver_texto = _abre_cliente(persona, c["cliente_id"]) and _abre_cliente(real, c["cliente_id"])
    o = json.loads(c["objeto"])
    cam = json.loads(c["cambio"])
    d = detalle_de(act)
    q = _persona(c["quien"])
    publico = {k: v for k, v in cam.items() if k not in ("texto", "comentario", "descripcion", "nota")}
    return {
        "id": c["id"], "creado": iso_z(c["creado"]), "quien": c["quien"], "quien_alias": q.get("alias") or c["quien"], "canal": c["canal"],
        "canal_nombre": CANALES[c["canal"]], "tipo": c["tipo"], "modo": c["modo"], "modulo": c["modulo"], "cliente_id": c["cliente_id"],
        "cliente": _cliente_nombre(c["cliente_id"]) if ver_texto else None,
        "objeto": {k: o.get(k) for k in ("tipo", "ref", "nombre", "url", "resuelto")},
        "cambio": publico, "que": describir(cam),
        "texto": (cam.get("texto") or cam.get("comentario") or cam.get("descripcion") or cam.get("nota")) if ver_texto else None,
        "texto_oculto": not ver_texto and bool(cam.get("texto") or cam.get("comentario")),
        "estado": act.get("estado"), "estado_texto": ESTADO_TEXTO.get(act.get("estado")), "desde": iso_z(act.get("hora")), "motivo": act.get("motivo"),
        "versiones": {"app": d.get("version_app"), "clickup": d.get("version_clickup"), "clickup_cambiado": d.get("clickup_cambiado")}
        if act.get("estado") == "conflicto" else None,
        "intentos": sum(1 for x in ps if x["evento"] in ("enviado", "error", "reintento_programado", "ya_estaba")),
        "avisado": any(x["evento"] == "aviso" for x in ps), "seguro_reintentar": bool(d.get("seguro_reintentar")),
        "puede_tocar": puede_tocar(real, c) and real["id"] == persona["id"],
        "puede_a_mano": ve_todos(real) and real["id"] == persona["id"],
        "ignorado": sorted((json.loads(c["ignorado"]) or {}).keys()) if c.get("ignorado") else [],
        "pasos": [{"estado": x["estado"], "evento": x["evento"], "hora": iso_z(x["hora"]), "quien": x["quien"], "intento": x["intento"], "motivo": x["motivo"]}
                  for x in ps] if con_pasos else None,
    }


def resumen_estado(con, cid):
    a = estado_actual(con, cid)
    est = a["estado"] if a else "pendiente"
    return {"id": cid, "estado": est, "texto": ESTADO_TEXTO.get(est, TEXTO_PENDIENTE), "ir": f"#/envios/clickup/{cid}"}


def _get(h, ruta, q, real, persona):
    with conectar() as con:
        # El montaje del módulo/los POST inicializan el esquema. GET no reconcilia
        # acciones ni crea tablas: una base sin inicializar es indisponibilidad.
        try:
            con.execute("SELECT id FROM sinc_pasos LIMIT 0")
            filas = [dict(r) for r in con.execute("SELECT * FROM sinc_cambios ORDER BY id DESC")]
        except sqlite3.DatabaseError:
            return h.responder(503, {"error": "La lectura de Sincronía no está disponible."})
        if ruta == "/api/sincronia/cambio":
            try:
                cid = int((q.get("id") or ["0"])[0])
            except ValueError:
                return h.responder(400, {"error": "«id» tiene que ser un número."})
            c = next((x for x in filas if x["id"] == cid), None)
            if not c or not _visible(real, persona, c):
                return h.responder(403 if c else 404, {"error": "Ese cambio no es tuyo." if c else "No existe ese cambio."})
            return h.responder(200, {"cambio": a_json(con, c, real, persona)})
        if ruta == "/api/sincronia/objeto":
            ref = str((q.get("ref") or [""])[0])[:80]
            mios = [x for x in filas if x["objeto_ref"] == ref and _visible(real, persona, x)]
            return h.responder(200, {"ref": ref, "cambios": [resumen_estado(con, x["id"]) for x in mios[:20]]})
        if ruta != "/api/sincronia":
            return h.responder(404, {"error": "No existe esa ruta de Sincronía."})
        canal = (q.get("canal") or [""])[0]
        estado = (q.get("estado") or [""])[0]
        lista = [a_json(con, c, real, persona) for c in filas if _visible(real, persona, c)][:500]
        if canal:
            lista = [x for x in lista if x["canal"] == canal]
        if estado:
            lista = [x for x in lista if x["estado"] == estado]
        inf = sin_reflejar(con, preparar_base=False)
        if not (ve_todos(real) and ve_todos(persona)):
            inf = {**inf, "cambios": [x for x in inf["cambios"] if x["quien"] == persona["id"]]}
            inf["total"] = len(inf["cambios"])
        it = interruptor()
        return h.responder(200, {
            "modo": {"reales": it["reales"], "canales": it["canales"], "chat_puente": it["chat_puente"], "texto": it["texto"], "activa": "Tomás",
                     "como": "ClickUp real necesita tres cosas: el interruptor (data/sincronia/interruptor.json, lo firma Tomás), RO_CLICKUP_REAL=si en el "
                             "servidor y la llave de un usuario de servicio de ClickUp (miembro, no propietario)."},
            "ve_todos": ve_todos(real) and ve_todos(persona), "solo_lectura": real["id"] != persona["id"],
            "por_estado": {s: sum(1 for x in lista if x["estado"] == s) for s in ESTADOS},
            "por_canal": {k: sum(1 for x in lista if x["canal"] == k) for k in CANALES},
            "informe": {"horas": inf["horas"], "total": inf["total"], "por_estado": inf["por_estado"], "texto": texto_informe(inf)},
            "cambios": lista,
        })


def _post(h, ruta, real, persona, b):
    if real["id"] != persona["id"]:
        return h.responder(403, {"error": "Estás en «ver como»: es solo lectura. No se escribe nada."})
    if ruta not in ("/api/sincronia/reintentar", "/api/sincronia/elegir", "/api/sincronia/a_mano"):
        return h.responder(404, {"error": "No existe esa ruta de Sincronía. Un cambio solo nace de una acción de la cola."})
    try:
        cid = int(b.get("id"))
    except (TypeError, ValueError):
        return h.responder(400, {"error": "«id» tiene que ser un número."})
    denegado, r, c = None, None, None
    with _CANDADO:
        with conectar() as con:
            preparar(con)
            c = fila(con, cid)
            if c and not _visible(real, persona, c):
                denegado = "Ese cambio no es tuyo."
            elif c and ruta == "/api/sincronia/a_mano" and not ve_todos(real):
                denegado = "Lo marca como hecho a mano Agus, Mili o Tomás."
            elif c and not puede_tocar(real, c):
                denegado = "Ese cambio no es tuyo: lo decide quien lo hizo, Agus, Mili o Tomás."
            elif c:
                if ruta == "/api/sincronia/reintentar":
                    r = reintentar(con, cid, real["id"])
                elif ruta == "/api/sincronia/elegir":
                    r = elegir(con, cid, real["id"], str(b.get("gana") or ""))
                else:
                    r = a_mano(con, cid, real["id"])
            con.commit()
    if not c:
        return h.responder(404, {"error": "No existe ese cambio."})
    accion = {"/api/sincronia/reintentar": "sinc_reintento", "/api/sincronia/elegir": "sinc_elegir", "/api/sincronia/a_mano": "sinc_a_mano"}[ruta]
    if denegado:
        S.registrar_agrupado(real["id"], "envios", "denegado", f"sincronia:{cid}", {"motivo": accion})
        return h.responder(403, {"error": denegado})
    if not r.get("ok"):
        return h.responder(r.get("codigo", 400), {"error": r["error"]})
    S.registrar(real["id"], "envios", accion + ("_simulado" if r.get("simulado") else ""), f"sincronia:{cid}",
                {"cambio_id": cid, "estado": r.get("estado"), "gana": b.get("gana") if ruta.endswith("elegir") else None,
                 "ignorado": sorted(k for k in b if k not in ("id", "gana"))[:8]})
    with conectar() as con:
        msj = {"/api/sincronia/reintentar": "Reintento simulado: ClickUp real está apagado. No se ha escrito nada." if r.get("simulado") else "Reintento hecho.",
               "/api/sincronia/elegir": "Se queda lo de ClickUp." if r.get("estado") == "descartado" else "Se queda lo de la app: vuelve a la cola.",
               "/api/sincronia/a_mano": "Marcado como pasado a mano en ClickUp."}[ruta]
        return h.responder(200, {"ok": True, "simulado": r.get("simulado"), "mensaje": msj, "cambio": a_json(con, c, real, persona)})


def _guardia(real, persona, b):
    """Antes de que servir.py guarde una acción de ClickUp que toca una tarea y que servir.py no vigila ya por su tipo
    (marcar hecha, imputar horas, asignar…): solo quien puede tocar esa tarea. None = adelante; (código, error) = no."""
    tipo = str(b.get("tipo") or "")
    clase = conf()["tipos_clickup"].get(tipo)
    vigilados = set((P.REGLAS.get("acciones_con_efecto_fuera") or {}).get("clickup_tarea") or []) | {"pieza_aprobar", "pieza_pedir_cambios"}
    if clase in (None, "crear_tarea", "otro") or tipo in vigilados:
        return None
    _t, error = tarea_tocable(real, b.get("objeto"))
    if error:
        S.registrar_agrupado(real["id"], "acciones", "denegado", f"clickup/{tipo}", {"motivo": "tarea ajena (sincronía)", "objeto": str(b.get("objeto"))[:40]})
        return 403, error
    return None


def _tras_accion(aid):
    """Tras guardar una acción de ClickUp: nace su cambio (la copia segura). Con ClickUp real, sale al momento."""
    with _CANDADO, conectar() as con:
        preparar(con)
        sincronizar(con)
        r = con.execute("SELECT id, canal, modo FROM sinc_cambios WHERE accion_id=?", (aid,)).fetchone()
        con.commit()
        if not r:
            return None
        out = resumen_estado(con, r["id"])
    if r["modo"] == "real" and canal_real(r["canal"]):
        threading.Thread(target=_al_momento, args=(r["id"],), daemon=True).start()
    return out



def destino_produccion_recibo(tipo, ref, desde, vp):
    """209: sólo destino explícito derivado por RP y catálogo tipado de esta lista."""
    t = tarea(ref)
    if not t or t.get('estado') != desde or not isinstance(vp, dict):
        return None
    lid = t.get('lista_id')
    datos = _mi_trabajo()
    catalogos = datos.get('estados_detalle') if isinstance(datos, dict) else None
    filas = catalogos.get(lid, []) if isinstance(catalogos, dict) else []
    if not isinstance(filas, list) or not filas:
        return None
    tipos = {}
    for f in filas:
        if (not isinstance(f, dict) or not isinstance(f.get('estado'), str) or f['estado'] in tipos
                or f.get('tipo') not in ('open', 'unstarted', 'custom', 'done', 'closed')):
            return None
        tipos[f['estado']] = f['tipo']
    rp = _reglas_piezas()
    if not isinstance(rp, dict):
        return None
    if tipo == 'pieza_aprobar':
        reglas = rp.get('por_estado')
        regla = reglas.get(desde) if isinstance(reglas, dict) else None
        destino = regla.get('a') if isinstance(regla, dict) else None
    elif tipo == 'pieza_pedir_cambios':
        destino = rp.get('pedir_cambios_a')
    elif tipo == 'mover_estado':
        # Política exacta del botón A revisión de Producción208, no destinos libres.
        wanted = 'revisión project manager'
        destino = wanted if vp.get('a') == wanted and wanted in conf().get('destinos_mover', []) else None
    else:
        return None
    return destino if isinstance(destino, str) and destino != desde and desde in tipos and destino in tipos and destino in estados_de_tarea(ref) else None


def recibo_transicion_tablero(aid, real, b):
    """193: vínculo releído tras commit; no convierte guardado local en envío remoto.

    Sólo opt-in validado por Mi Trabajo/Producción. El recibo contrasta la fila durable y
    la intención194 con el cuerpo; catálogo y base deben seguir siendo coherentes.
    Un fallo de cola/lectura deja recuperación explícita, nunca otro envío.
    """
    pendiente = {"cola_estado": "pendiente_recuperacion", "recibo_durable": False,
                 "confirmacion_remota": False,
                 "texto_cola": "Acción guardada en RO; no se ha acreditado su vínculo con la cola. Revisar Envíos antes de repetir."}
    try:
        from intenciones_acciones import identidad
        if not isinstance(aid, int) or isinstance(aid, bool) or aid < 1:
            return pendiente
        vp = b.get("vista_previa")
        if not isinstance(vp, dict):
            return pendiente
        tablero = vp.get('transicion_tablero') is True
        produccion = vp.get('transicion_produccion') is True
        if tablero == produccion:
            return pendiente
        flag, modulo = ('transicion_tablero', 'mi-trabajo') if tablero else ('transicion_produccion', 'produccion')
        tipo = b.get('tipo')
        if (tablero and tipo != 'cambiar_estado') or (produccion and tipo not in ('pieza_aprobar', 'pieza_pedir_cambios', 'mover_estado')):
            return pendiente
        if not isinstance(real, dict) or not isinstance(real.get("id"), str):
            return pendiente
        iid, huella = identidad(real["id"], b)
        with conectar() as con:
            act = con.execute("SELECT * FROM acciones WHERE id=?", (aid,)).fetchone()
            cs = con.execute("SELECT * FROM sinc_cambios WHERE accion_id=?", (aid,)).fetchall()
            intent = con.execute("SELECT accion_id, huella FROM intenciones_acciones WHERE actor=? AND intencion=?", (real["id"], iid)).fetchone()
            if not act or len(cs) != 1 or not intent or intent["accion_id"] != aid or intent["huella"] != huella:
                return pendiente
            act, c = dict(act), dict(cs[0])
            stored = json.loads(act.get("vista_previa") or "null")
            obj, cam, base = json.loads(c["objeto"]), json.loads(c["cambio"]), json.loads(c.get("base") or "null")
            tid = str(act.get("objeto") or "")
            t = tarea(tid)
            actual = estado_actual(con, c["id"])
            if not isinstance(stored, dict) or not isinstance(base, dict) or not t or not actual:
                return pendiente
            if any(stored.get(k) != vp.get(k) for k in ("transicion_tablero", "transicion_produccion", "lista_id", "revision", "expected_estado", "a")):
                return pendiente
            desde, hasta, lid = stored.get("expected_estado"), stored.get("a"), stored.get("lista_id")
            if (stored.get(flag) is not True or not isinstance(lid, str) or not lid
                    or lid != t.get("lista_id") or not isinstance(desde, str) or not desde
                    or not isinstance(hasta, str) or not hasta or desde == hasta
                    or base.get("estado") != desde or hasta not in estados_de_tarea(tid)):
                return pendiente
            if (act.get("quien") != real["id"] or c.get("quien") != real["id"]
                    or act.get("herramienta") != "clickup" or act.get("tipo") != tipo
                    or act.get("modulo") != modulo or b.get("modulo") != modulo or c.get("modulo") != modulo
                    or tid != str(b.get("objeto") or "") or c.get("objeto_ref") != tid
                    or obj.get("tipo") != "tarea" or obj.get("ref") != tid
                    or c.get("tipo") != tipo or c.get("canal") != "clickup"
                    or act.get("cliente_id") != c.get("cliente_id")):
                return pendiente
            if produccion and t.get('cli') != act.get('cliente_id'):
                return pendiente
            if cam.get('campo') != 'estado':
                return {**pendiente, 'cola_estado': actual.get('estado') if actual.get('estado') in ESTADOS else 'pendiente_recuperacion',
                        'requiere_revision': True, 'reintento_seguro': False, 'motivo_recibo': 'cambio_no_enviable',
                        'texto_cola': 'Acción guardada en RO, pero el cambio no es enviable: revisar fuente, regla y catálogo. Repetir la solicitud no acredita un envío.'}
            if cam.get('valor') != hasta or (produccion and destino_produccion_recibo(tipo, tid, desde, stored) != hasta):
                return {**pendiente, 'requiere_revision': True, 'reintento_seguro': False, 'motivo_recibo': 'destino_no_coherente'}
            estado = actual.get("estado")
            if estado not in ESTADOS:
                return pendiente
            remoto = estado == "confirmado" and c.get("modo") == "real" and actual.get("evento") == "verificado"
            return {"cola_estado": estado, "recibo_durable": True, "confirmacion_remota": remoto,
                    "recibo": {"accion_id": aid, "cambio_id": c["id"], "tarea_id": tid, "lista_id": lid, "tipo": tipo, "modulo": modulo,
                               "desde": desde, "hasta": hasta, "intencion_id": iid,
                               "estado_cola": estado, "confirmacion_remota": remoto}}
    except Exception:
        return pendiente


def _al_momento(cid):
    import time
    for espera in (0, 120, int(conf()["gracia_min"]) * 60 + 5):
        time.sleep(espera)
        with _CANDADO, conectar() as con:
            c = fila(con, cid)
            if not c or not canal_real(c["canal"]):
                return
            prov = proveedor_de(c["canal"])
            est = estado_actual(con, cid)["estado"]
            if est == "pendiente" and not bloqueado_por_anterior(con, c):
                ejecutar(con, cid, prov)
            elif est == "enviado":
                verificar(con, cid, prov)
            if estado_actual(con, cid)["estado"] in FINALES | {"fallido", "conflicto"}:
                return


def enganchar(Manejador, servir):
    """Envuelve _api_get y api_post (como envios.py). Sin este fichero, nada cambia."""
    global S, P
    S, P = servir, servir.P
    with S.conectar() as con:
        preparar(con)
    get_orig, post_orig = Manejador._api_get, Manejador.api_post

    def _api_get(self, ruta, q, real, persona_):
        if ruta == "/api/sincronia" or ruta.startswith("/api/sincronia/"):
            if S.E.nucleo_bloqueado:
                return self.responder(503, {"error": "La puerta de secretos ha encontrado algo en los datos."})
            return _get(self, ruta, q, real, persona_)
        return get_orig(self, ruta, q, real, persona_)

    def api_post(self, ruta, real, persona_, b):
        if ruta.startswith("/api/sincronia"):
            return _post(self, ruta, real, persona_, b)
        if ruta != "/api/acciones" or str(b.get("herramienta") or "") != "clickup" or real["id"] != persona_["id"]:
            return post_orig(self, ruta, real, persona_, b)
        g = _guardia(real, persona_, b)
        if g:
            return self.responder(g[0], {"error": g[1]})
        orig = self.responder

        def responder(codigo, obj, *a, **k):        # la respuesta lleva «Hecho en la app · pendiente de ClickUp» al momento
            if codigo == 200 and isinstance(obj, dict) and obj.get("id"):
                try:
                    sinc = _tras_accion(int(obj["id"]))
                    if sinc:
                        obj = {**obj, "sincronia": sinc}
                except Exception:
                    traceback.print_exc()
                vp = b.get("vista_previa")
                if isinstance(vp, dict) and (vp.get("transicion_tablero") is True or vp.get("transicion_produccion") is True):
                    obj = {**obj, **recibo_transicion_tablero(int(obj["id"]), real, b)}
            return orig(codigo, obj, *a, **k)
        self.responder = responder
        try:
            return post_orig(self, ruta, real, persona_, b)
        finally:
            try:
                del self.responder
            except AttributeError:
                pass

    Manejador._api_get = _api_get
    Manejador.api_post = api_post
