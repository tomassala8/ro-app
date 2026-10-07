#!/usr/bin/env python3
"""
mi_trabajo.py · «Mi trabajo» (3-oct-2026). Encargo de Tomás: que el equipo deje de usar ClickUp en el día a día y trabaje
desde la app: sus tareas (hoy, semana, mes), actuar sin salir (estado, hecha, fecha, comentario), imputar horas
(cronómetro y «Añadir tiempo») y las horas raras.

NADA SE ESCRIBE EN CLICKUP. Cada acción entra por POST /api/acciones (herramienta «clickup», módulo «mi-trabajo") y
sincronia.py la guarda en su copia segura (sinc_cambios, imborrable, clave única por acción) en «simulado» mientras el
interruptor de Tomás esté apagado. Este fichero solo:
  1. VALIDA antes (envuelve api_post): el estado tiene que existir en la lista de esa tarea; la fecha, un día real y
     razonable; las horas, de 1 a 720 minutos, de hoy o de los 14 días anteriores en la zona de la persona, y solo en una
     tarea SUYA (las horas son de quien las imputa). El resto (dueño de la tarea, revisión, «ver como») lo mira servir.py.
  2. Guarda el CRONÓMETRO en marcha (tabla mt_crono: uno por persona). Al pararlo, el servidor calcula los minutos y
     deja él mismo la acción «imputar_horas» por la misma puerta (/api/acciones): el navegador no pone los minutos.
  3. GET /api/mi_trabajo: lo que ya hizo la app (cambios de sinc_cambios con su estado), las horas de cada día (ClickUp +
     app, SIN DUPLICAR: una hora de la app cuya huella «ro:<clave>» ya aparece en las horas de ClickUp no se suma dos
     veces), la jornada y las horas raras. Cada uno lo suyo; su jefe, operaciones, RRHH y dirección, las de su gente
     (regla horas_persona de reglas_permisos.json). Nunca sueldos ni euros.

Rutas:
  GET  /api/mi_trabajo                               mi estado (y el de mi equipo si lo veo)
  POST /api/mi_trabajo/crono {accion: empezar|parar|descartar, tarea}
"""
import json
import re
import threading
import traceback
import time
import math
from contexto_tarea import contexto_operativo
from documento_privado_222 import DocumentoPrivado
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

AQUI = Path(__file__).resolve().parent
DATA = AQUI / "data"
FICHERO = DATA / "mi_trabajo" / "mi_trabajo.json"
MODULO = "mi-trabajo"
TIPOS = ("cambiar_estado", "cambiar_fecha", "marcar_hecha", "imputar_horas", "comentario")
DIAS_ATRAS_HORAS = 14
MAX_MIN = 720
CRONO_MAX_H = 10
TEXTO_GUARDADO = "Guardado en RO · envío a ClickUp sin confirmar"
S = P = SINC = None
_CANDADO = threading.Lock()
_DOC = {"mtime": None, "doc": {}}
_RAW_TAREAS_222 = DocumentoPrivado()

TABLA = """
CREATE TABLE IF NOT EXISTS mt_crono (
  persona TEXT PRIMARY KEY,                 -- un cronómetro en marcha por persona
  tarea TEXT NOT NULL,
  inicio TEXT NOT NULL                      -- UTC, ISO
);
"""


# =================================================================== utilidades
def ahora_utc():
    return datetime.now(timezone.utc)


def zona(p):
    try:
        return ZoneInfo((p or {}).get("zona") or "Europe/Madrid")
    except Exception:
        return ZoneInfo("Europe/Madrid")


def hoy_de(p):
    return ahora_utc().astimezone(zona(p)).date()


def doc():
    """data/mi_trabajo/mi_trabajo.json sin recortar (el recorte se hace aquí con horas_persona)."""
    try:
        mt = FICHERO.stat().st_mtime
    except OSError:
        return {}
    if _DOC["mtime"] != mt:
        try:
            _DOC.update(mtime=mt, doc=json.loads(FICHERO.read_text()))
        except Exception:
            return _DOC["doc"] or {}
    return _DOC["doc"]


def personas():
    return (S.E.crudo.get("personas") if S is not None else json.loads((DATA / "personas.json").read_text())) or []


def persona(pid):
    return next((p for p in personas() if p.get("id") == pid), None)


def ve_persona(viewer, pid, cp=None):
    """¿Puede ver las horas y las tareas de esa persona? La persona, su jefe, operaciones, RRHH y dirección."""
    if viewer["id"] == pid:
        return True
    return P.ver(viewer, {"tipo": "horas_persona", "persona_id": pid}, cp or P.contexto(viewer, S.E.crudo))["ok"]


def tarea_doc(tid, pid=None):
    for r in doc().get("tareas") or []:
        if str(r.get("id")) == str(tid) and (pid is None or r.get("persona_id") == pid):
            return r
    return None


def es_dia(t):
    try:
        return date.fromisoformat(str(t)) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(t or "")) else None
    except ValueError:
        return None


def _fuente_autorizacion_tareas():
    """204/222: fuente documental por versión; autoridad reconstruida en cada GET/POST.

    No reutiliza persona_id heurística de Producción/Mi Trabajo para conceder
    escritura. Ausencia del inventario privado deja lectura histórica sin token.
    """
    from identidades_clickup_204 import preparar_autorizacion
    from config import PANEL_OPERACIONES
    def archivo(path):
        try:
            d = json.loads(path.read_text())
            return d if isinstance(d, dict) else {}
        except (OSError, ValueError, TypeError, RecursionError):
            return {}
    t = _RAW_TAREAS_222.leer(AQUI / 'fuentes_produccion' / '_privado' / '_cache' / 'tareas.json')
    m = archivo(PANEL_OPERACIONES / '_crudo' / 'clickup' / 'miembros.json')
    usuarios = [u for key in ('miembros', 'usuarios_no_miembros_vistos')
                for u in (m.get(key) if isinstance(m.get(key), list) else [])]
    carpetas = {}
    try:
        documentos = sorted((DATA / 'clientes').glob('*.json'))
    except OSError:
        documentos = []
    for path in documentos:
        d = archivo(path)
        cid = d.get('id')
        datos = d
        for key in ('fuentes', 'tareas', 'datos'):
            datos = datos.get(key) if isinstance(datos, dict) else None
        folder = datos.get('carpeta_id') if isinstance(datos, dict) else None
        if isinstance(cid, str) and cid and isinstance(folder, (str, int)) and not isinstance(folder, bool) and str(folder):
            carpetas.setdefault(str(folder), []).append(cid)
    return preparar_autorizacion(S.E.crudo.get('personas') or [], usuarios, t.get('tareas'), carpetas)


def tarea_para_accion(real, tid, contexto=None, indice=None):
    """Identidad actual y cliente confirmado; no conceder permisos por asignación vieja."""
    from fuentes_verdad import clientes_activos as ACT
    from transiciones_mi_trabajo import tarea_unica
    actuales = indice['actor'] if indice is not None else [p for p in S.E.crudo.get('personas') or [] if p.get('id') == real.get('id')]
    if len(actuales) != 1 or actuales[0].get('estado') != 'activo' or actuales[0].get('activo') is False:
        raise PermissionError('Sesión sin identidad activa única')
    p = actuales[0]
    if not (indice['modulo'] if indice is not None else S.ve_alguno(p, [MODULO])):
        raise PermissionError('Mi trabajo no está autorizado')
    r = tarea_unica(doc(), tid, indice['filas'].get(tid, []) if indice is not None else None)
    cid = r.get('cli')
    if cid not in (None, ''):
        if indice is not None:
            autorizado = indice['cliente_autorizado'](cid)
        else:
            clientes = [c for c in S.E.crudo.get('clientes') or [] if c.get('id') == cid]
            autorizado = isinstance(cid, str) and len(clientes) == 1 and ACT.es_activo_id(cid) is True and P.ver(p, {'tipo': 'cliente_detalle', 'cliente_id': cid}, (contexto if contexto is not None else P.contexto(p, S.E.crudo)))['ok']
        if not autorizado:
            raise PermissionError('Cliente fuera de la cartera activa autorizada')
    from identidades_clickup_204 import actor_autorizado
    evidencia = indice['identidad_fuente'] if indice is not None else _fuente_autorizacion_tareas()
    if not actor_autorizado(p, r, evidencia):
        raise PermissionError('Asignación de ClickUp sin identidad confirmada autorizada')
    if hasattr(S, 'tarea_de_produccion'):
        produccion = S.tarea_de_produccion(tid)
        if produccion and produccion.get('cli') != cid:
            raise ValueError('Producción y Mi trabajo no concuerdan en el cliente')
    return r


def validar_transicion_en_transaccion(con, real, b):
    """Antes del INSERT y después de replay194, bajo BEGIN IMMEDIATE del caller."""
    vp = b.get('vista_previa')
    if not isinstance(vp, dict) or vp.get('transicion_tablero') is not True:
        return None
    from transiciones_mi_trabajo import capacidad
    disponible = capacidad(con, real, real)
    if not disponible['activo']:
        if disponible['motivo'] == 'piloto_solo_lectura':
            return 403, 'Este piloto es sólo de consulta.'
        return 503, 'Las transiciones duraderas necesitan SQLite compatible.'
    if not con.in_transaction:
        return 409, 'La transición necesita una transacción de escritura.'
    error = validar(real, b)
    if error:
        return error
    if hasattr(S, 'pieza_en_revision') and S.pieza_en_revision(b.get('objeto')):
        return 403, 'Esta pieza requiere la puerta de revisión.'
    from transiciones_mi_trabajo import proyectar
    try:
        actual = proyectar(doc(), str(b.get('objeto') or ''), con)
    except (ValueError, TypeError, KeyError):
        return 409, 'Actualiza la copia de la tarea antes de moverla.'
    if actual['bloqueada'] or any(vp.get(k) != actual[k] for k in ('lista_id', 'expected_estado', 'revision')):
        return 409, 'La tarea o su cola han cambiado; actualiza antes de moverla.'
    if vp['a'] == actual['expected_estado']:
        return 409, 'La copia ya está en ese estado.'
    return None


# =================================================================== 1 · validación antes de la cola
def validar(real, b):
    """None = adelante; (código, error) = no. Lo demás (dueño, revisión, «ver como») lo comprueba servir.py."""
    tipo = str(b.get("tipo") or "")
    if tipo not in TIPOS:
        return 400, "Esa acción no es de Mi trabajo."
    if str(b.get("herramienta") or "") != "clickup":
        return 400, "Las acciones de Mi trabajo son sobre tareas de ClickUp."
    tid = str(b.get("objeto") or "")
    if not re.fullmatch(r"[\w\-]{3,40}", tid):
        return 400, "Falta la tarea."
    vp = b.get("vista_previa") if isinstance(b.get("vista_previa"), dict) else {}
    try:
        fila = tarea_para_accion(real, tid)
    except PermissionError:
        return 403, "Esta tarea no está en tu cartera activa autorizada."
    except (ValueError, TypeError):
        return 409, "La identidad de esta tarea es ambigua o incompleta."
    tablero = vp.get('transicion_tablero') is True
    if tablero:
        if tipo != 'cambiar_estado' or not isinstance(b.get('intencion_id'), str) or not re.fullmatch(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', b['intencion_id']):
            return 400, 'La transición necesita una intención UUID y cambiar_estado.'
        if not isinstance(vp.get('expected_estado'), str) or not isinstance(vp.get('revision'), str) or not re.fullmatch(r'[0-9a-f]{64}', vp['revision']) or vp.get('lista_id') != fila['lista_id']:
            return 400, 'Falta la lista o la revisión de la transición.'
    if tipo == "cambiar_estado":
        a = vp.get("a")
        from transiciones_mi_trabajo import catalogo
        try:
            hay = catalogo(doc(), fila['lista_id'])
        except (ValueError, TypeError):
            return 409, 'Actualiza el catálogo confirmado de esta lista.'
        if not isinstance(a, str) or a not in hay:
            return 400, "Ese estado no existe en la lista de esta tarea en ClickUp."
        actual = (tarea_doc(tid) or {}).get("estado")
        if not tablero and actual and a == actual:
            return 400, "La tarea ya está en ese estado."
    elif tipo == "marcar_hecha":
        finales = SINC.estados_hecha_de_tarea(tid) if SINC else []
        if not finales:
            return 400, "No hay un estado de tarea hecha confirmado para esta lista; elige un estado explícito."
    elif tipo == "cambiar_fecha":
        d = es_dia(vp.get("dia"))
        hoy = hoy_de(real)
        if not d or not (hoy - timedelta(days=60) <= d <= hoy + timedelta(days=366)):
            return 400, "La fecha no es válida (de hace dos meses a dentro de un año)."
    elif tipo == "imputar_horas":
        try:
            m = int(vp.get("minutos"))
        except (TypeError, ValueError):
            return 400, "Faltan los minutos."
        if not 1 <= m <= MAX_MIN:
            return 400, f"Entre 1 minuto y {MAX_MIN // 60} horas por apunte."
        d = es_dia(vp.get("dia"))
        hoy = hoy_de(real)
        if not d or not (hoy - timedelta(days=DIAS_ATRAS_HORAS) <= d <= hoy):
            return 400, f"Las horas se apuntan de hoy o de los {DIAS_ATRAS_HORAS} días anteriores."
        if not tarea_doc(tid, real["id"]):
            return 403, "Las horas se imputan en tus propias tareas (las tuyas en ClickUp)."
    elif tipo == "comentario":
        if len(str(b.get("texto") or "").strip()) < 2:
            return 400, "Escribe el comentario."
        if len(str(b.get("texto") or "")) > 2000:
            return 400, "El comentario es demasiado largo (2.000 caracteres)."
    return None


# =================================================================== 2 · cronómetro
def _con():
    con = S.conectar()
    con.executescript(TABLA)
    return con


def crono_de(pid):
    with _con() as con:
        r = con.execute("SELECT tarea, inicio FROM mt_crono WHERE persona=?", (pid,)).fetchone()
    return {"tarea": r["tarea"], "inicio": r["inicio"]} if r else None


def _post_interno(h, real, persona_, cuerpo):
    """Deja una acción por la MISMA puerta que el navegador (/api/acciones, con todas sus comprobaciones y la sincronía)
    y devuelve (código, respuesta) sin escribir aún al navegador."""
    captura = {}

    def capturar(codigo, obj, *a, **k):
        captura["r"] = (codigo, obj)
    h.responder = capturar
    try:
        h.api_post("/api/acciones", real, persona_, cuerpo)
    finally:
        try:
            del h.responder
        except AttributeError:
            pass
    return captura.get("r") or (500, {"error": "Sin respuesta."})


def post_crono(h, real, persona_, b):
    if real["id"] != persona_["id"]:
        return h.responder(403, {"error": "Estás en «ver como»: es solo lectura. No se escribe nada."})
    accion = str(b.get("accion") or "")
    tid = str(b.get("tarea") or "")
    with _CANDADO:
        actual = crono_de(real["id"])
        if accion == "empezar":
            if not tarea_doc(tid, real["id"]):
                return h.responder(403, {"error": "El cronómetro solo va en tus propias tareas."})
            if actual:
                return h.responder(409, {"error": "Ya tienes el cronómetro en marcha en otra tarea: páralo antes.", "crono": actual})
            with _con() as con:
                con.execute("INSERT INTO mt_crono (persona, tarea, inicio) VALUES (?,?,?)", (real["id"], tid, ahora_utc().isoformat()))
            S.registrar(real["id"], MODULO, "crono_empezar", tid)
            return h.responder(200, {"ok": True, "crono": crono_de(real["id"])})
        if accion not in ("parar", "descartar"):
            return h.responder(400, {"error": "«accion» es empezar, parar o descartar."})
        if not actual:
            return h.responder(409, {"error": "No hay ningún cronómetro en marcha."})
        with _con() as con:
            con.execute("DELETE FROM mt_crono WHERE persona=?", (real["id"],))
    if accion == "descartar":
        S.registrar(real["id"], MODULO, "crono_descartar", actual["tarea"])
        return h.responder(200, {"ok": True, "descartado": True})
    ini = datetime.fromisoformat(actual["inicio"])
    seg = (ahora_utc() - ini).total_seconds()
    minutos = max(1, min(MAX_MIN, round(seg / 60)))
    largo = seg > CRONO_MAX_H * 3600
    dia = ini.astimezone(zona(real)).date().isoformat()
    cuerpo = {"herramienta": "clickup", "tipo": "imputar_horas", "objeto": actual["tarea"], "modulo": MODULO,
              "texto": f"{minutos} min con el cronómetro de la app ({ahora_utc().astimezone(zona(real)).strftime('%H:%M:%S')})",
              "vista_previa": {"minutos": minutos, "dia": dia, "origen": "cronometro"}}
    codigo, r = _post_interno(h, real, persona_, cuerpo)
    if codigo != 200:
        with _con() as con:                      # no se pierde: vuelve el cronómetro tal cual
            con.execute("INSERT OR REPLACE INTO mt_crono (persona, tarea, inicio) VALUES (?,?,?)", (real["id"], actual["tarea"], actual["inicio"]))
        return h.responder(codigo, r)
    S.registrar(real["id"], MODULO, "crono_parar", actual["tarea"], {"minutos": minutos, "accion_id": r.get("id")})
    return h.responder(200, {"ok": True, "minutos": minutos, "dia": dia, "largo": largo, "accion": r,
                             "texto": TEXTO_GUARDADO, "aviso": "Más de 10 horas seguidas: ¿se quedó encendido? Revísalo en Envíos › ClickUp." if largo else None})


# =================================================================== 3 · estado (GET)
def cambios_app(con, ids_visibles):
    """Cambios de la copia segura (sinc_cambios) sobre tareas, de las personas que se ven, con su último estado."""
    filas = con.execute("SELECT * FROM sinc_cambios WHERE canal='clickup' ORDER BY id").fetchall() if _tabla(con, "sinc_cambios") else []
    out = []
    for c in filas:
        if c["quien"] not in ids_visibles:
            continue
        o = json.loads(c["objeto"])
        if o.get("tipo") != "tarea":
            continue
        act = SINC.estado_actual(con, c["id"]) if SINC else None
        cam = json.loads(c["cambio"])
        out.append({"id": c["id"], "quien": c["quien"], "tarea": o.get("ref"), "tipo": c["tipo"], "modulo": c["modulo"], "creado": c["creado"],
                    "campo": cam.get("campo"), "valor": cam.get("valor"), "minutos": cam.get("minutos"), "dia": cam.get("dia"),
                    "texto": cam.get("texto") or cam.get("comentario") or cam.get("nota"),
                    "marca": SINC.marca(c["clave"]) if SINC else None,
                    "estado": (act or {}).get("estado"), "estado_texto": SINC.ESTADO_TEXTO.get((act or {}).get("estado")) if SINC else None})
    return out


def _tabla(con, nombre):
    return bool(con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (nombre,)).fetchone())


def numero_horas_370(v):
    if type(v) not in (int, float):
        return None
    try:
        return float(v) if math.isfinite(v) and v >= 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def suma_horas_370(valores):
    buenos = [x for v in valores if (x := numero_horas_370(v)) is not None]
    if not buenos:
        return None
    return numero_horas_370(sum(buenos))


def laborables_atras(hoy, n, desde=None):
    out, d = [], hoy - timedelta(days=1)
    while len(out) < n and d > hoy - timedelta(days=21):
        if d.weekday() < 5 and (not desde or d >= desde):
            out.append(d)
        d -= timedelta(days=1)
    return out


def raras_de(pid, dias, jornada, D, app_por_tarea, ve_cli):
    """Reglas de horas raras de UNA persona. dias = {dia: {"cu", "app"}}."""
    p = persona(pid) or {}
    out = []
    hoy = hoy_de(p)
    j = next((x for x in D.get("jornada") or [] if x.get("persona_id") == pid), None)
    total = lambda d: suma_horas_370([(dias.get(d) or {}).get("cu"), (dias.get(d) or {}).get("app")])
    if j:                                                    # día laborable con 0 h (los 5 últimos, desde que entró)
        desde = es_dia(j.get("desde"))
        for d in laborables_atras(hoy, 5, desde):
            if d.isoformat() not in dias:
                out.append({"persona_id": pid, "regla": "sin_registros_copia", "dia": d.isoformat(), "horas": None, "source_kind": "copia_horas_clickup_y_registro_ro", "cobertura": "parcial", "calendario_confirmado": False})
    for d, v in sorted(dias.items()):
        dd = es_dia(d)
        if not dd or dd >= hoy:
            continue
        t = total(d)
        if t is not None and t > 10:
            out.append({"persona_id": pid, "regla": "mas_10", "dia": d, "horas": t})
        if dd.weekday() >= 5 and t is not None and t > 0 and dd >= hoy - timedelta(days=14):
            out.append({"persona_id": pid, "regla": "fin_semana", "dia": d, "horas": t})
    for x in D.get("largas") or []:
        if x.get("persona_id") == pid and numero_horas_370(x.get("horas")) is not None:
            out.append({"persona_id": pid, "regla": "mas_10", "dia": x.get("dia"), "horas": x.get("horas"), "tarea_id": x.get("tarea_id"), "una_sola": True})
    for x in D.get("raras_estimacion") or []:
        if x.get("persona_id") == pid:
            ht = suma_horas_370([x.get("horas_t"), app_por_tarea.get(x.get("tarea_id"))])
            if ht is None or numero_horas_370(x.get("est_h")) is None:
                continue
            out.append({"persona_id": pid, "regla": "doble_estimacion", "tarea_id": x.get("tarea_id"), "tarea": x.get("tarea"), "est_h": x.get("est_h"), "horas": ht})
    vistos = set()
    for x in D.get("raras_cliente_n") or []:
        if x.get("persona_id") != pid:
            continue
        cli = next((y.get("cliente_id") for y in D.get("raras_cliente") or [] if y.get("persona_id") == pid and y.get("tarea_id") == x.get("tarea_id")
                    and y.get("dia") == x.get("dia") and ve_cli(y.get("cliente_id"))), None)
        k = (x.get("dia"), x.get("tarea_id"))
        if k in vistos:
            continue
        vistos.add(k)
        out.append({"persona_id": pid, "regla": "cliente_ajeno", "dia": x.get("dia"), "tarea_id": x.get("tarea_id"), "horas": numero_horas_370(x.get("horas")), "cliente_id": cli})
    return out


def get_estado(h, q, real, persona_):
    D = doc()
    cp = P.contexto(persona_, S.E.crudo)
    visibles = [p for p in personas() if p.get("estado") != "baja" and ve_persona(persona_, p["id"], cp)
                and (real["id"] == persona_["id"] or ve_persona(real, p["id"]))]
    ids = {p["id"] for p in visibles}
    # El permiso de horas/persona no concede el catálogo de otro cliente.
    from fuentes_verdad import clientes_activos as ACT
    cr = P.contexto(real, S.E.crudo)
    clientes_por_id, permiso_clientes = {}, {}
    for c in S.E.crudo.get('clientes') or []:
        clientes_por_id.setdefault(c.get('id'), []).append(c)
    def cliente_autorizado(cid):
        if cid is None or cid == '':
            return True  # Global conocida; ninguna cartera inventada.
        if not isinstance(cid, str):
            return False
        if cid not in permiso_clientes:
            permiso_clientes[cid] = len(clientes_por_id.get(cid, [])) == 1 and ACT.es_activo_id(cid) is True and all(
                P.ver(p, {'tipo': 'cliente_detalle', 'cliente_id': cid}, ctx)['ok']
                for p, ctx in ((real, cr), (persona_, cp)))
        return permiso_clientes[cid]
    def lista_autorizada(r):
        return r.get('persona_id') in ids and 'cli' in r and cliente_autorizado(r.get('cli'))
    # Una tarea multi-asignada puede tener una fila por persona; no elegir first-wins
    # ante duplicados de la misma persona o identidades cliente/lista contradictorias.
    por_tarea = {}
    for r in D.get("tareas") or []:
        if isinstance(r, dict) and isinstance(r.get("id"), str):
            por_tarea.setdefault(r["id"], []).append(r)
    tareas_autorizadas = set()
    for tid, filas in por_tarea.items():
        identidades = {(str(r.get("cli")), str(r.get("lista_id"))) for r in filas}
        personas_tarea = [r.get("persona_id") for r in filas]
        if len(identidades) != 1 or len(set(personas_tarea)) != len(personas_tarea):
            continue
        if any(lista_autorizada(r) for r in filas):
            tareas_autorizadas.add(tid)
    listas_visibles = {r.get("lista_id") for tid, filas in por_tarea.items()
                       if tid in tareas_autorizadas for r in filas if lista_autorizada(r)}
    with S.conectar() as con:
        cambios_personales = cambios_app(con, ids)
        cambios = [c for c in cambios_personales if c.get("tarea") in tareas_autorizadas]
        transiciones = {}
        from transiciones_mi_trabajo import capacidad
        capacidad_transicion = capacidad(con, real, persona_)
        if capacidad_transicion['activo']:
            from transiciones_mi_trabajo import proyectar, preparar_lectura
            actores = [p for p in S.E.crudo.get('personas') or [] if p.get('id') == real.get('id')]
            modulo_actual = len(actores) == 1 and actores[0].get('estado') == 'activo' and actores[0].get('activo') is not False and S.ve_alguno(actores[0], [MODULO])
            if not modulo_actual:
                capacidad_transicion.update(activo=False, motivo='permiso_actual_revocado')
            indice_auth = {'actor': actores, 'modulo': modulo_actual, 'filas': por_tarea, 'jefes': {}, 'cliente_autorizado': cliente_autorizado,
                           'identidad_fuente': _fuente_autorizacion_tareas()}
            for p in S.E.crudo.get('personas') or []:
                indice_auth['jefes'].setdefault(p.get('id'), []).append(p.get('jefe'))
            tareas_con_capacidad = tareas_autorizadas if modulo_actual else set()
            indice_cola = preparar_lectura(D, con, tareas_con_capacidad, por_tarea)
            for tid in tareas_con_capacidad:
                try:
                    tarea_para_accion(real, tid, cr, indice_auth)
                    transiciones[tid] = proyectar(D, tid, con, indice_cola)
                except (ValueError, TypeError, KeyError, PermissionError):
                    pass  # Sin token no se ofrece movimiento; lectura existente conservada.
    # horas: ClickUp por día (zona de la persona) + horas de la app que aún NO están en ClickUp (huella ro:<clave>)
    marcas = {x["persona_id"]: set(x.get("marcas") or []) for x in D.get("horas_dia") or []}
    dias = {pid: {d: {"cu": numero_horas_370(v), "app": None, "cu_observado": numero_horas_370(v) is not None, "app_observado": False, "cu_invalido": v is not None and numero_horas_370(v) is None} for d, v in (next((x for x in D.get("horas_dia") or [] if x["persona_id"] == pid), {}).get("dias") or {}).items()}
            for pid in ids}
    app_por_tarea = {}
    horas_app = []
    for c in cambios_personales:
        if c["campo"] != "horas" or c["estado"] == "descartado":
            continue
        minutos = numero_horas_370(c.get("minutos"))
        if minutos is None:
            continue
        en_cu = c["marca"] in marcas.get(c["quien"], set())
        if c.get("tarea") in tareas_autorizadas:
            horas_app.append({**c, "minutos": minutos, "en_clickup": en_cu})
        if en_cu:
            continue                                         # ya viene en las horas de ClickUp: no se suma dos veces
        x = dias.setdefault(c["quien"], {}).setdefault(c["dia"], {"cu": None, "app": None, "cu_observado": False, "app_observado": False})
        x["app"] = suma_horas_370([x["app"], minutos / 60]) if not x.get("app_invalido") else None
        x["app_observado"] = x["app"] is not None
        x["app_invalido"] = x["app"] is None
        total_tarea = suma_horas_370([app_por_tarea.get(c["tarea"]), minutos / 60])
        app_por_tarea[c["tarea"]] = total_tarea
    def ve_cli(cid):
        clientes = [c for c in S.E.crudo.get("clientes") or [] if c.get("id") == cid]
        return bool(cid) and len(clientes) == 1 and ACT.es_activo_id(cid) is True and all(
            P.ver(p, {"tipo": "cliente_detalle", "cliente_id": cid}, ctx)["ok"]
            for p, ctx in ((real, cr), (persona_, cp)))
    D_raras = dict(D)
    for clave_raras in ("largas", "raras_estimacion", "raras_cliente", "raras_cliente_n"):
        D_raras[clave_raras] = [r for r in D.get(clave_raras) or []
                              if r.get("tarea_id") in tareas_autorizadas]
    raras = []
    for pid in ids:
        raras += raras_de(pid, dias.get(pid, {}), None, D_raras, app_por_tarea if pid == persona_["id"] else {}, ve_cli)
    desde = (hoy_de(persona_) - timedelta(days=DIAS_ATRAS_HORAS + 7)).isoformat()
    for pid in list(dias):
        dias[pid] = {d: v for d, v in dias[pid].items() if d >= desde}
    yo = persona_["id"]
    crono = crono_de(yo) if real["id"] == persona_["id"] else None
    if crono and crono.get("tarea") not in tareas_autorizadas:
        crono = None  # no borrar ni parar el cronómetro: GET sólo oculta fuera de alcance.
    for c in cambios:                                        # el texto de un comentario, solo para quien lo escribió
        if c["quien"] != yo:
            c["texto"] = None
    return h.responder(200, {
        "transiciones": transiciones,
        "capacidad_transicion": capacidad_transicion,
        "yo": yo, "hoy": hoy_de(persona_).isoformat(), "zona": (persona(yo) or {}).get("zona"), "generado": D.get("generado"),
        "fuentes": D.get("fuentes"), "cobertura_tareas": D.get("cobertura_tareas"), "cobertura_estados": D.get("cobertura_estados"),
        "estados_detalle": {k:v for k,v in (D.get("estados_detalle") or {}).items() if k in listas_visibles}, "solo_lectura": real["id"] != persona_["id"],
        "jornada": [x for x in D.get("jornada") or [] if x.get("persona_id") in ids],
        "estados_lista": {k: v for k, v in (D.get("estados_lista") or {}).items()
                          if k in listas_visibles},
        "personas": sorted([{"id": p["id"], "nombre": p.get("alias") or p.get("nombre"), "jefe": p.get("jefe"), "zona": p.get("zona"),
                             "hoy": hoy_de(p).isoformat()} for p in visibles], key=lambda x: (x["id"] != yo, x["nombre"])),
        "cambios": cambios[-400:], "horas_app": horas_app[-200:], "dias": dias, "raras": raras,
        "dias_fuente": {"version": "370.2", "fuente": "copia_horas_clickup_y_registro_ro",
                         "lectura_clickup": (D.get("fuentes") or {}).get("horas"), "cobertura": "parcial",
                         "calendario_confirmado": False, "jornada_confirmada": False,
                         "apuntes_largos_apartados": True, "declaraciones_ro_no_confirman_clickup": True},
        "crono": crono,
        "ve_equipo": len(ids) > 1,
        "sincronia": {"texto": TEXTO_GUARDADO, "real": bool(SINC and SINC.canal_real("clickup"))},
    })


# =================================================================== lectura de contexto de UNA tarea autorizada
_CTX_CACHE = {}
_CONECTOR_CU = None


def leer_tarea_clickup(tid):
    """GET exacto, timeout 8 s, sin reintentos ni escrituras. Reutiliza autenticación del conector cu.py."""
    global _CONECTOR_CU
    import importlib.util
    import urllib.request
    import config
    if _CONECTOR_CU is None:
        spec = importlib.util.spec_from_file_location("ro_cu_contexto", config.HERRAMIENTAS / "clickup_api" / "cu.py")
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        _CONECTOR_CU = modulo
    cu = _CONECTOR_CU
    credencial = getattr(cu, "TOK", None) or cu.token()
    req = urllib.request.Request(f"{cu.API}/task/{tid}", headers={"Authorization": credencial, "Accept": "application/json"}, method="GET")
    with urllib.request.urlopen(req, timeout=8) as r:
        contenido = r.read(1024 * 1024 + 1)
    if len(contenido) > 1024 * 1024:
        raise ValueError("Respuesta demasiado grande")
    dato = json.loads(contenido)
    if not isinstance(dato, dict) or str(dato.get("id")) != tid:
        raise ValueError("Respuesta de otra tarea")
    return dato


def contexto_ia(h, q, real, vista, *, lector=None):
    if S.E.nucleo_bloqueado:
        return h.responder(503, {"error": "La puerta de secretos ha bloqueado los datos."})
    if not S.ve_alguno(vista, [MODULO]) or not S.ve_alguno(real, [MODULO]):
        return h.responder(403, {"error": "Mi trabajo no es de tu puesto."})
    tid, pid = str((q.get("tarea") or [""])[0]), str((q.get("persona") or [""])[0])
    if not re.fullmatch(r"[a-zA-Z0-9_-]{3,40}", tid):
        return h.responder(400, {"error": "Falta una tarea válida."})
    cp = P.contexto(vista, S.E.crudo)
    cr = P.contexto(real, S.E.crudo)
    fila = next((t for t in doc().get("tareas", []) if str(t.get("id")) == tid and (not pid or t.get("persona_id") == pid)
                 and ve_persona(vista, t.get("persona_id"), cp) and ve_persona(real, t.get("persona_id"), cr)
                 and (persona(t.get("persona_id")) or {}).get("estado") != "baja"), None)
    if not fila:
        return h.responder(403, {"error": "Esta tarea no está en tu contexto autorizado."})
    cid = fila.get('cli')
    if cid:
        from fuentes_verdad import clientes_activos as ACT
        clientes = [c for c in S.E.crudo.get('clientes') or [] if c.get('id') == cid]
        if len(clientes) != 1 or not ACT.es_activo_id(cid) or not all(
                P.ver(p, {'tipo': 'cliente_detalle', 'cliente_id': cid}, contexto)['ok']
                for p, contexto in ((real, cr), (vista, cp))):
            return h.responder(403, {'error': 'El cliente de esta tarea no está en tu contexto activo autorizado.'})
    # No se acepta cliente del navegador ni se lee una tarea que no pasó la misma regla de persona que la pantalla.
    base = {"id": fila["id"], "persona_id": fila["persona_id"], "cli": fila.get("cli"), **contexto_operativo(fila)}
    def responder_contexto(payload):
        import procedimientos_contexto as PC
        return h.responder(200, PC.ampliar(payload, fila=fila, real=real, vista=vista, S=S, P=P))
    reciente = _CTX_CACHE.get(tid)
    if reciente and time.monotonic() - reciente[0] < 300:
        return responder_contexto({"tarea": {**base, **reciente[1]}, "fuente": "ClickUp en lectura", "leido": reciente[2], "cache": True})
    try:
        raw = (lector or leer_tarea_clickup)(tid)
        if not isinstance(raw, dict) or str(raw.get("id")) != tid:
            raise ValueError("Respuesta de otra tarea")
        operativa = contexto_operativo(raw)
        leido = ahora_utc().isoformat(timespec="seconds")
        if len(_CTX_CACHE) >= 256:
            _CTX_CACHE.pop(next(iter(_CTX_CACHE)), None)
        _CTX_CACHE[tid] = (time.monotonic(), operativa, leido)
        return responder_contexto({"tarea": {**base, **operativa}, "fuente": "ClickUp en lectura", "leido": leido,
                                 "aviso": None if operativa["descripcion"] else "La tarea de ClickUp no tiene descripción disponible."})
    except (Exception, SystemExit):
        # Nunca devolver errores de proveedor: podrían incluir token, contactos o contenido crudo.
        return responder_contexto({"tarea": base, "fuente": "Copia local", "leido": doc().get("generado"),
                                 "aviso": "No se pudo leer la descripción actual de ClickUp. Se conserva la copia local; confirma el brief en la tarea antes de ejecutar."})


# =================================================================== horas de la app para otros generadores
def entradas_app(con, marcas_cu=()):
    """Horas imputadas en la app que todavía NO están en ClickUp (sin la huella en marcas_cu) y no descartadas:
    [{id, persona_id, dia, horas, task_id, marca}]. Para generar_horas.py (pantalla Horas e indicadores)."""
    import sincronia as SN
    out = []
    if not _tabla(con, "sinc_cambios"):
        return out
    marcas_cu = set(marcas_cu)
    for c in con.execute("SELECT * FROM sinc_cambios WHERE canal='clickup' ORDER BY id").fetchall():
        cam = json.loads(c["cambio"])
        if cam.get("campo") != "horas" or not cam.get("minutos"):
            continue
        act = SN.estado_actual(con, c["id"])
        if (act or {}).get("estado") == "descartado":
            continue
        m = SN.marca(c["clave"])
        if m in marcas_cu:
            continue
        out.append({"id": f"app:{c['clave'][:16]}", "persona_id": c["quien"], "dia": cam.get("dia"), "horas": round(cam["minutos"] / 60, 4),
                    "task_id": json.loads(c["objeto"]).get("ref"), "marca": m})
    return out


# =================================================================== enganche a servir.py
def enganchar(Manejador, servir):
    global S, P, SINC
    S, P = servir, servir.P
    import sys
    SINC = sys.modules.get("sincronia")
    with S.conectar() as con:
        con.executescript(TABLA)
    get_orig, post_orig = Manejador._api_get, Manejador.api_post

    def _api_get(self, ruta, q, real, persona_):
        if ruta == "/api/mi_trabajo/metadatos":
            import tareas_metadata_219 as metadata_tareas
            import sys
            return metadata_tareas.get_metadatos(self, q, real, persona_, sys.modules[__name__])
        if ruta == "/api/mi_trabajo/contexto_ia":
            return contexto_ia(self, q, real, persona_)
        if ruta == "/api/mi_trabajo":
            if S.E.nucleo_bloqueado:
                return self.responder(503, {"error": "La puerta de secretos ha encontrado algo en los datos."})
            if not S.ve_alguno(persona_, [MODULO]):
                return self.responder(403, {"error": "Mi trabajo no es de tu puesto."})
            return get_estado(self, q, real, persona_)
        return get_orig(self, ruta, q, real, persona_)

    def api_post(self, ruta, real, persona_, b):
        if ruta == "/api/mi_trabajo/crono":
            if not S.ve_alguno(persona_, [MODULO]):
                return self.responder(403, {"error": "Mi trabajo no es de tu puesto."})
            try:
                return post_crono(self, real, persona_, b)
            except Exception:
                traceback.print_exc()
                return self.responder(500, {"error": "Error interno (el detalle queda en el registro del servidor)."})
        if ruta == "/api/acciones" and str(b.get("modulo") or "") == MODULO and real["id"] == persona_["id"]:
            v = validar(real, b)
            if v:
                S.registrar_agrupado(real["id"], "acciones", "denegado", f"mi-trabajo/{str(b.get('tipo'))[:30]}", {"motivo": v[1][:80]})
                return self.responder(v[0], {"error": v[1]})
        return post_orig(self, ruta, real, persona_, b)

    Manejador._api_get = _api_get
    Manejador.api_post = api_post


def entradas_para_cache(H, T, db=None):
    """Para generar_horas.py y generar_mi_trabajo.py: las horas de la app que todavía NO están en ClickUp, con la MISMA
    forma que las entradas de la caché de ClickUp (y «persona_id» en vez de usuario). Sin duplicar: si la huella
    «ro:<clave>» ya aparece en una entrada de ClickUp, esa hora ya cuenta allí y aquí no sale."""
    import os
    import sqlite3
    ruta = Path(db or os.environ.get("RO_DB") or AQUI / "local.db")
    if not ruta.exists():
        return []
    marcas = set()
    for e in (H or {}).get("entradas") or []:
        m = e.get("marca_ro") or (re.search(r"ro:[0-9a-f]{10}", e.get("descripcion") or "") or [None])[0]
        if m:
            marcas.add(m)
    carpeta = {t["id"]: (t.get("carpeta_id"), t.get("carpeta"), t.get("lista"), t.get("nombre")) for t in (T or {}).get("tareas") or []}
    con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True, timeout=20)
    con.row_factory = sqlite3.Row
    try:
        filas = entradas_app(con, marcas)
    finally:
        con.close()
    pz = {p["id"]: p for p in json.loads((DATA / "personas.json").read_text())}
    out = []
    for x in filas:
        if not es_dia(x["dia"]) or x["persona_id"] not in pz:
            continue
        ini = datetime.fromisoformat(f"{x['dia']}T12:00:00").replace(tzinfo=zona(pz[x["persona_id"]]))
        c = carpeta.get(x["task_id"]) or (None, None, None, None)
        out.append({"id": x["id"], "persona_id": x["persona_id"], "usuario_id": None, "usuario": None, "inicio": ini.isoformat(), "horas": x["horas"],
                    "task_id": x["task_id"], "tarea": c[3], "carpeta_id": c[0], "carpeta": c[1], "lista": c[2],
                    "descripcion": f"desde la app · {x['marca']}", "etiquetas": [], "marca_ro": x["marca"], "app": True})
    return out
