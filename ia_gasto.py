#!/usr/bin/env python3
"""Control local de presupuesto IA: claims durables, fallo cerrado (candidato142).

No equivale a la suscripción Max ni acredita un tope del proveedor. Tarifas
heredadas sin verificar y ausencia del contador acreditado mantienen modo reglas.
No se compra por una estimación de caracteres. Los resultados inciertos conservan
su reserva; una segunda llave necesita presupuesto adicional. Los lotes están
pausados hasta validar claim previo y recogida idempotente. Sin identidad real/vista
coincidente tampoco se permite generar. Sólo Tomás nominal administra topes.
"""
import json
import math
import os
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import ia_real_559 as IA_REAL

S = None                       # el módulo servir (lo pone enganchar)
MADRID = ZoneInfo("Europe/Madrid")
FUENTE_PRECIOS = "https://platform.claude.com/docs/en/about-claude/pricing"
FECHA_PRECIOS = None
PRECIOS_VERIFICADOS = False  # No hay verificación oficial actual en este encargo local.

# Catálogo histórico NO verificado: USD/millón. No habilita compras ni acredita tasas actuales.
PRECIOS = {
    "claude-opus-5":     {"entrada": 5.00, "cache_escrita": 6.25, "cache_leida": 0.50, "salida": 25.00},
    "claude-opus-5-5":   {"entrada": 4.00, "cache_escrita": 5.00, "cache_leida": 0.20, "salida": 20.00},
    "claude-sonnet-5":   {"entrada": 2.00, "cache_escrita": 2.50, "cache_leida": 0.20, "salida": 10.00},
    "claude-haiku-4-5":  {"entrada": 1.00, "cache_escrita": 1.25, "cache_leida": 0.10, "salida": 5.00},
    "claude-fable-5-1":  {"entrada": 10.00, "cache_escrita": 12.50, "cache_leida": 0.25, "salida": 50.00},
}
PRECIO_DESCONOCIDO = None # Sin tarifa exacta: no comprar. Catálogo heredado, no verificación externa actual.
DESCUENTO_LOTE = 0.5

TAREAS = {   # nombre en pantalla, modelo por defecto (variable de entorno que lo cambia), techo de salida, esfuerzo
    "borrador":   {"nombre": "Borradores de correo", "modelo": "claude-opus-5", "env": "RO_IA_MODELO_BORRADOR", "max_tokens": 8000},
    "copiloto":   {"nombre": "Copiloto del account", "modelo": "claude-sonnet-5", "env": "RO_IA_MODELO_COPILOTO", "max_tokens": 8000},
    "consejo":    {"nombre": "Consejos por pantalla", "modelo": "claude-haiku-4-5", "env": "RO_IA_MODELO_CONSEJO", "max_tokens": 2000},
    "clasificar": {"nombre": "Clasificar correos", "modelo": "claude-haiku-4-5", "env": "RO_IA_MODELO_CLASIFICAR", "max_tokens": 600},
    "otra":       {"nombre": "Otras", "modelo": "claude-haiku-4-5", "env": "RO_IA_MODELO_OTRA", "max_tokens": 2000},
}

TOPES_DEFECTO = {
    "activa": True,             # interruptor general: False = modo reglas a mano
    "mes_eur": 150.0,           # presupuesto del mes (Europe/Madrid)
    "dia_eur": 10.0,            # presupuesto del día
    "aviso_pct": 80,            # aviso a Tomás al llegar a este % del mes o del día
    "persona_dia_eur": 2.0,     # lo que puede gastar una persona en un día (Tomás: el doble)
    "funcion_mes_eur": {"borrador": 100.0, "copiloto": 25.0, "consejo": 10.0, "clasificar": 10.0, "otra": 5.0},
    "respaldo_mes_eur": 15.0,   # tope de la llave de respaldo (además del que se le ponga en su espacio de la Console)
    "consejo_pantallas": ["mi-dia"],   # la IA redacta consejos SOLO aquí (con caché de 3 h); el resto de pantallas, reglas
    "usd_a_eur": 0.92,          # cambio prudente (algo peor que el real): mejor sobrestimar el gasto que quedarse corto
}
LIMITES = {"mes_eur": (0, 2000), "dia_eur": (0, 200), "aviso_pct": (10, 99), "persona_dia_eur": (0, 50),
           "respaldo_mes_eur": (0, 200), "usd_a_eur": (0.5, 1.5), "funcion": (0, 2000)}

TABLAS_SQL = """
CREATE TABLE IF NOT EXISTS ia_gasto (
  id INTEGER PRIMARY KEY AUTOINCREMENT, creada TEXT NOT NULL, dia TEXT NOT NULL, mes TEXT NOT NULL,
  quien TEXT NOT NULL, tarea TEXT NOT NULL, objeto TEXT, modelo TEXT, llave TEXT NOT NULL, lote INTEGER NOT NULL DEFAULT 0,
  entrada INTEGER NOT NULL DEFAULT 0, cache_escrita INTEGER NOT NULL DEFAULT 0, cache_leida INTEGER NOT NULL DEFAULT 0,
  salida INTEGER NOT NULL DEFAULT 0, coste_usd REAL NOT NULL DEFAULT 0, coste_eur REAL NOT NULL DEFAULT 0,
  ok INTEGER NOT NULL, motivo TEXT, peticion TEXT);
CREATE INDEX IF NOT EXISTS ia_gasto_mes ON ia_gasto (mes, dia);
CREATE TRIGGER IF NOT EXISTS ia_gasto_sin_update BEFORE UPDATE ON ia_gasto BEGIN SELECT RAISE(ABORT, 'El gasto de la IA no se cambia'); END;
CREATE TRIGGER IF NOT EXISTS ia_gasto_sin_delete BEFORE DELETE ON ia_gasto BEGIN SELECT RAISE(ABORT, 'El gasto de la IA no se borra'); END;
CREATE TABLE IF NOT EXISTS ia_topes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, creada TEXT NOT NULL, quien TEXT NOT NULL, valores TEXT NOT NULL, motivo TEXT);
CREATE TRIGGER IF NOT EXISTS ia_topes_sin_update BEFORE UPDATE ON ia_topes BEGIN SELECT RAISE(ABORT, 'Un cambio de topes no se reescribe'); END;
CREATE TRIGGER IF NOT EXISTS ia_topes_sin_delete BEFORE DELETE ON ia_topes BEGIN SELECT RAISE(ABORT, 'Un cambio de topes no se borra'); END;
CREATE TABLE IF NOT EXISTS ia_reservas (
  id TEXT PRIMARY KEY, creada TEXT NOT NULL, tarea TEXT NOT NULL, quien TEXT NOT NULL,
  llave TEXT NOT NULL, reservado_eur REAL NOT NULL CHECK(reservado_eur >= 0),
  estado TEXT NOT NULL CHECK(estado IN ('activa','incierta','cerrada')));
CREATE TRIGGER IF NOT EXISTS ia_reservas_sin_delete BEFORE DELETE ON ia_reservas BEGIN SELECT RAISE(ABORT,'Una reserva no se borra'); END;
CREATE TABLE IF NOT EXISTS ia_lotes (
  id TEXT PRIMARY KEY, creado TEXT NOT NULL, quien TEXT NOT NULL, tarea TEXT NOT NULL, llave TEXT NOT NULL, modelo TEXT,
  n INTEGER NOT NULL, reservado_eur REAL NOT NULL, estado TEXT NOT NULL, cerrado TEXT, peticiones TEXT);
"""

_CANDADO = threading.Lock()
_RESERVAS = {}                 # id de reserva → (eur, tarea, quien, llave)
_CORTES = {}                   # (periodo, sello) → tope vigente cuando se cortó (si Tomás cambia el tope, deja de valer)
_HILO = threading.local()      # quién pide (lo pone ia.py al atender cada ruta)
_N = [0]
_CLAVE_R = {"t": 0, "v": None}


class SinGasto(RuntimeError):
    """La llamada no sale: tope alcanzado, «ver como», IA apagada… El texto es legible y va a la pantalla."""


class ErrorProveedor(Exception):
    """Fallo del proveedor ya clasificado: tipo = «caida» (vale el respaldo), «tope_console» (modo reglas) u «otro»."""
    def __init__(self, tipo, texto):
        super().__init__(texto)
        self.tipo = tipo


# ======================================================================= reloj y base
def ahora():
    return datetime.now(MADRID)


def _hoy():
    return ahora().strftime("%Y-%m-%d")


def _mes():
    return ahora().strftime("%Y-%m")


def iniciar():
    with S.conectar() as con:
        con.executescript(TABLAS_SQL)


def _topes_en(con):
    t = json.loads(json.dumps(TOPES_DEFECTO))
    f = con.execute("SELECT valores FROM ia_topes ORDER BY id DESC LIMIT 1").fetchone()
    if f:
        v = json.loads(f[0], parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Tope no finito")))
        if not isinstance(v, dict): raise SinGasto("Topes ilegibles: no se compra IA.")
        t.update(v)
        t['funcion_mes_eur'] = {**TOPES_DEFECTO['funcion_mes_eur'], **(v.get('funcion_mes_eur') or {})}
    try: return validar(t, TOPES_DEFECTO)
    except (ValueError, TypeError, KeyError) as e: raise SinGasto("Topes inválidos: no se compra IA.") from e


def topes():
    try:
        with S.conectar() as con: return _topes_en(con)
    except SinGasto: raise
    except Exception as e: raise SinGasto("No se puede verificar el presupuesto de IA: modo reglas.") from e


def _importe(v):
    if isinstance(v, bool) or not isinstance(v, (int,float)) or not math.isfinite(v) or v < 0:
        raise SinGasto("Importe desconocido o inválido: no se compra IA.")
    return float(v)


def _suma_en(con, where, args):
    filas = con.execute(f"SELECT coste_eur FROM ia_gasto WHERE {where}", args).fetchall()
    return sum(_importe(r[0]) for r in filas), len(filas)


def _suma(where, args):
    with S.conectar() as con: return _suma_en(con, where, args)


def gastado():
    m, d = _mes(), _hoy()
    return {"mes": _suma("mes=?", (m,))[0], "dia": _suma("dia=?", (d,))[0]}


def _reservado_en(con, tarea=None, quien=None, llave=None):
    total = 0.0
    for tabla, campo, estados in (("ia_reservas","reservado_eur","('activa','incierta')"),("ia_lotes","reservado_eur","('enviado')")):
        for e, rt, rq, rl in con.execute(f"SELECT {campo}, tarea, quien, llave FROM {tabla} WHERE estado IN {estados}"):
            if (tarea is None or rt==tarea) and (quien is None or rq==quien) and (llave is None or rl==llave): total += _importe(e)
    return total


def _reservado(tarea=None, quien=None, llave=None):
    with S.conectar() as con: return _reservado_en(con,tarea,quien,llave)



# ======================================================================= precio
def precio(modelo):
    if PRECIOS_VERIFICADOS is not True: raise SinGasto("Catálogo de tarifas pendiente de verificación: no se compra IA.")
    p = PRECIOS.get(modelo) if isinstance(modelo,str) else None
    if not isinstance(p,dict) or any(k not in p or _importe(p[k])<=0 for k in ('entrada','cache_escrita','cache_leida','salida')):
        raise SinGasto("Modelo sin tarifa exacta válida: no se compra IA.")
    return p


def _tokens(uso):
    if not isinstance(uso,dict): raise SinGasto("Uso no confirmado: conservar reserva.")
    valores={}
    for k in ('entrada','cache_escrita','cache_escrita_1h','cache_leida','salida'):
        v=uso.get(k,0)
        if type(v) is not int or v<0: raise SinGasto("Uso inválido: conservar reserva.")
        valores[k]=v
    return valores


def coste(modelo, uso, lote=False, t=None):
    p, u = precio(modelo), _tokens(uso)
    cambio = _importe((t or topes())['usd_a_eur'])
    usd=(u['entrada']*p['entrada']+u['cache_escrita']*p['cache_escrita']+u['cache_escrita_1h']*p['entrada']*2+u['cache_leida']*p['cache_leida']+u['salida']*p['salida'])/1e6
    if lote: usd *= DESCUENTO_LOTE
    return round(_importe(usd),6),round(_importe(usd*cambio),6)


def coste_maximo(modelo, texto_entrada, max_tokens, lote=False, t=None, entrada_tokens=None):
    if type(entrada_tokens) is not int or entrada_tokens<0 or type(max_tokens) is not int or max_tokens<0:
        raise SinGasto("Falta conteo de entrada acreditado; la estimación por caracteres no autoriza compras.")
    p=precio(modelo); cambio=_importe((t or topes())['usd_a_eur'])
    usd=(entrada_tokens*max(p['entrada'],p['cache_escrita'],p['cache_leida'],p['entrada']*2)+max_tokens*p['salida'])/1e6
    if lote: raise SinGasto("Lotes en pausa: falta recuperación durable validada.")
    return math.ceil(_importe(usd*cambio)*1e6)/1e6


def modelo_de(tarea):
    c = TAREAS.get(tarea) or TAREAS["otra"]
    if tarea in ("borrador", "copiloto") and os.environ.get("RO_IA_MODELO"):   # compatibilidad con N3
        return os.environ.get(c["env"]) or os.environ["RO_IA_MODELO"]
    return os.environ.get(c["env"]) or c["modelo"]


# ======================================================================= quién pide (lo pone ia.py)
def fijar_peticion(real, persona, objeto=None):
    _HILO.real = (real or {}).get("id")
    _HILO.persona = (persona or {}).get("id")
    _HILO.objeto = objeto


def soltar_peticion():
    _HILO.real = _HILO.persona = _HILO.objeto = None


def peticion_actual():
    return getattr(_HILO, "real", None), getattr(_HILO, "persona", None), getattr(_HILO, "objeto", None)


# ======================================================================= modo (ia / reglas)
def _pausa_console():
    """¿La Console cortó este mes (tope propio, de nivel o saldo) y Tomás no ha pulsado «Reabrir» después?"""
    try:
        with S.conectar() as con:
            corte = con.execute("SELECT MAX(creada) FROM ia_gasto WHERE mes=? AND motivo LIKE 'tope_console%'", (_mes(),)).fetchone()[0]
            reab = con.execute("SELECT MAX(creada) FROM ia_topes WHERE motivo LIKE 'reabrir%'").fetchone()[0]
        return bool(corte) and not (reab and reab >= corte)
    except Exception:
        return False


def modo():
    """{"modo": "ia"|"reglas", "motivo" (para dirección), "llano" (para el resto), gastado, topes}."""
    if not IA_REAL.autorizada():
        return {"modo":"reglas", "motivo":IA_REAL.MOTIVO, "llano":"IA en pausa; seguimos con reglas.", "gastado":{"mes":None,"dia":None}, "topes":{}}
    try:
        t = topes()
        g = gastado()
        reservado = _reservado()
    except Exception:
        return {'modo':'reglas','motivo':'No se puede verificar el registro de gasto de IA.','llano':'IA en pausa; seguimos con reglas.','gastado':{'mes':None,'dia':None},'topes':{}}
    out = {"modo": "ia", "motivo": None, "llano": None, "gastado": g, "topes": {"mes_eur": t["mes_eur"], "dia_eur": t["dia_eur"]}}
    llano = "La IA ha llegado a su tope de gasto: la app sigue con reglas y lo ya preparado, sin coste. Lo reabre Tomás."
    if PRECIOS_VERIFICADOS is not True:
        out.update(modo='reglas',motivo='Catálogo de tarifas pendiente de verificación; no se autoriza compra de IA.',llano='IA en pausa; seguimos con reglas.')
    elif not callable(getattr(PROVEEDOR,'contar_entrada',None)):
        out.update(modo='reglas',motivo='Falta conteo de entrada acreditado; no se autoriza compra de IA.',llano='IA en pausa; seguimos con reglas.')
    elif not t.get("activa", True):
        out.update(modo="reglas", motivo="IA apagada a mano por Tomás (Sistema › Gasto de IA): la app va con reglas y lo precalculado, sin coste.",
                   llano="La IA está en pausa: la app sigue con reglas y lo ya preparado, sin coste.")
    elif g['mes'] + reservado >= t['mes_eur'] or g['dia'] + reservado >= t['dia_eur']:
        out.update(modo='reglas',motivo='Presupuesto comprometido por gasto y reservas; verificar resultados pendientes antes de comprar más.',llano=llano)
    elif g["mes"] >= t["mes_eur"]:
        out.update(modo="reglas", llano=llano, motivo=f"Tope del mes alcanzado ({_e(g['mes'])} de {_e(t['mes_eur'])}): modo reglas, sin coste, "
                   "hasta el día 1 o hasta que subas el tope en Sistema › Gasto de IA.")
    elif g["dia"] >= t["dia_eur"]:
        out.update(modo="reglas", llano=llano, motivo=f"Tope del día alcanzado ({_e(g['dia'])} de {_e(t['dia_eur'])}): modo reglas, sin coste, "
                   "hasta mañana o hasta que subas el tope en Sistema › Gasto de IA.")
    elif any(_CORTES.get(k) == v for k, v in ((("mes", _mes()), t["mes_eur"]), (("día", _hoy()), t["dia_eur"]))):
        out.update(modo="reglas", llano=llano, motivo=f"Tope casi agotado ({_e(g['mes'])} de {_e(t['mes_eur'])} este mes, {_e(g['dia'])} de "
                   f"{_e(t['dia_eur'])} hoy): lo que queda no cubre ni una petición. Modo reglas, sin coste, hasta mañana o el día 1, "
                   "o hasta que subas el tope en Sistema › Gasto de IA.")
    elif _pausa_console():
        out.update(modo="reglas", llano=llano, motivo="La Console de Anthropic ha cortado (tope de gasto o saldo): modo reglas, sin coste. "
                   "Sube el límite en la Console y pulsa «Reabrir» en Sistema › Gasto de IA.")
    return out


def _e(x):
    return f"{x:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


# ======================================================================= avisos (#avisos-dirección) y rastro
def avisar(texto, clave):
    """Una vez por clave: aviso a Tomás en #avisos-dirección (si avisos.py está cargado) y fila en el rastro."""
    A = sys.modules.get("avisos")
    publicado = False
    if A is not None and hasattr(A, "publicar"):
        try:
            with S.conectar() as con:
                publicado = bool(A.publicar(con, "avisos-direccion", "evento", texto, f"ia_gasto:{clave}", dueno_id="tomas",
                                            menciones=["tomas"], ver={"puestos": ["direccion"]},
                                            datos={"icono": "alert", "ir": "#/gasto-ia"}))
        except Exception as e:
            print("Aviso de gasto de IA no publicado:", e)
    try:
        with S.conectar() as con:
            ya = con.execute("SELECT 1 FROM registro WHERE accion='ia_aviso_gasto' AND clave=? LIMIT 1", (clave,)).fetchone()
        if not ya:
            S.registrar("sistema", "ia", "ia_aviso_gasto", clave, {"texto": texto, "canal": "avisos-direccion", "publicado": publicado})
    except Exception:
        pass
    return publicado


def _umbrales(t):
    """Tras cada gasto: aviso al 80 % y corte al 100 % del mes y del día (una vez por periodo)."""
    g = gastado()
    for periodo, valor, tope, sello in (("mes", g["mes"], t["mes_eur"], _mes()), ("día", g["dia"], t["dia_eur"], _hoy())):
        if tope <= 0:
            continue
        pct = valor / tope * 100
        if pct >= 100:
            avisar(f"IA: tope del {periodo} alcanzado ({_e(valor)} de {_e(tope)}). La app ha pasado sola a modo reglas, sin coste. "
                   f"Si quieres más, sube el tope en Sistema › Gasto de IA.", f"corte:{periodo}:{sello}")
        elif pct >= t["aviso_pct"]:
            avisar(f"IA: llevas el {pct:.0f} % del tope del {periodo} ({_e(valor)} de {_e(tope)}). Al 100 % pasa sola a modo reglas.",
                   f"aviso:{periodo}:{sello}")


# ======================================================================= reservar y apuntar
def _comprobar_y_reservar(tarea, quien, llave, maximo, t):
    _exigir_real()
    maximo=_importe(maximo)
    if tarea not in TAREAS or not isinstance(quien,str) or not quien or llave not in ('principal','respaldo'):
        raise SinGasto("Reserva sin identidad/función válida.")
    if _pausa_console(): raise SinGasto("Console en pausa; no se compra IA.")
    with S.conectar() as con:
        if con.in_transaction: raise SinGasto("No reservar sobre una transacción ajena.")
        con.execute('BEGIN IMMEDIATE')
        vigente=_topes_en(con)
        if not vigente['activa']: raise SinGasto("IA pausada: modo reglas.")
        maximo=math.ceil(maximo*max(1,vigente['usd_a_eur']/_importe(t['usd_a_eur']))*1e6)/1e6
        total=_reservado_en(con)
        for where,arg,tope in (('mes=?',_mes(),vigente['mes_eur']),('dia=?',_hoy(),vigente['dia_eur'])):
            if _suma_en(con,where,(arg,))[0]+total+maximo>tope: raise SinGasto("La petición no cabe en el presupuesto vigente: modo reglas.")
        if _suma_en(con,'mes=? AND tarea=?',(_mes(),tarea))[0]+_reservado_en(con,tarea=tarea)+maximo>vigente['funcion_mes_eur'][tarea]: raise SinGasto("Tope de función: modo reglas.")
        if _suma_en(con,'dia=? AND quien=?',(_hoy(),quien))[0]+_reservado_en(con,quien=quien)+maximo>vigente['persona_dia_eur']*(2 if quien=='tomas' else 1): raise SinGasto("Tope personal: modo reglas.")
        if llave=='respaldo' and _suma_en(con,"mes=? AND llave='respaldo'",(_mes(),))[0]+_reservado_en(con,llave='respaldo')+maximo>vigente['respaldo_mes_eur']: raise SinGasto("Tope de respaldo: modo reglas.")
        _exigir_real()
        rid=uuid.uuid4().hex
        con.execute('INSERT INTO ia_reservas VALUES (?,?,?,?,?,?,?)',(rid,ahora().strftime('%Y-%m-%d %H:%M:%S'),tarea,quien,llave,maximo,'activa'))
    return rid


def _retener_reserva(rid):
    with S.conectar() as con: con.execute("UPDATE ia_reservas SET estado='incierta' WHERE id=? AND estado='activa'",(rid,))



def apuntar(tarea, quien, objeto, modelo, llave, uso, ok, motivo=None, lote=False, peticion=None, t=None, reserva_id=None):
    t = t or topes()
    usd, eur = coste(modelo, uso or {}, lote, t)          # lo que se ha gastado de verdad, salga bien o no
    a = ahora()
    with S.conectar() as con:
        con.execute('BEGIN IMMEDIATE')
        if reserva_id:
            r=con.execute('SELECT tarea,quien,llave,estado FROM ia_reservas WHERE id=?',(reserva_id,)).fetchone()
            if not r or tuple(r[:3])!=(tarea,quien,llave) or r[3]=='cerrada': raise SinGasto('Reserva no válida para apuntar el gasto.')
        con.execute("INSERT INTO ia_gasto (creada, dia, mes, quien, tarea, objeto, modelo, llave, lote, entrada, cache_escrita, cache_leida, "
                    "salida, coste_usd, coste_eur, ok, motivo, peticion) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (a.strftime("%Y-%m-%d %H:%M:%S"), a.strftime("%Y-%m-%d"), a.strftime("%Y-%m"), quien, tarea,
                     str(objeto)[:120] if objeto else None, modelo, llave, 1 if lote else 0,
                     int((uso or {}).get("entrada", 0)), int((uso or {}).get("cache_escrita", 0)) + int((uso or {}).get("cache_escrita_1h", 0)), int((uso or {}).get("cache_leida", 0)),
                     int((uso or {}).get("salida", 0)), usd, eur, 1 if ok else 0, motivo, peticion))
        if reserva_id: con.execute("UPDATE ia_reservas SET estado='cerrada' WHERE id=?",(reserva_id,))
    return eur


# ======================================================================= llaves
def clave_respaldo():
    """Segunda clave (otro espacio de trabajo de la Console): ANTHROPIC_API_KEY_RESPALDO o llavero «anthropic_api_key_respaldo»."""
    if not IA_REAL.autorizada():
        return None
    if time.time() - _CLAVE_R["t"] < 300:
        return _CLAVE_R["v"]
    v = (os.environ.get("ANTHROPIC_API_KEY_RESPALDO") or "").strip() or None
    if not v and sys.platform == "darwin":
        try:
            v = subprocess.check_output(["security", "find-generic-password", "-s", "anthropic_api_key_respaldo", "-w"],
                                        text=True, stderr=subprocess.DEVNULL, timeout=5).strip() or None
        except Exception:
            v = None
    _CLAVE_R.update(t=time.time(), v=v)
    return v


def _clave_principal():
    if not IA_REAL.autorizada():
        return None
    ia = sys.modules.get("ia")
    return ia.clave() if ia else (os.environ.get("ANTHROPIC_API_KEY") or None)


def _exigir_real():
    if not IA_REAL.autorizada():
        raise SinGasto(IA_REAL.MOTIVO)


# ======================================================================= proveedor (Anthropic de verdad)
class ProveedorAnthropic:
    """El único sitio que habla con Anthropic. Devuelve (salida_json, modelo, uso) o lanza ErrorProveedor ya clasificado."""

    @staticmethod
    def peticion(modelo, sistema, contexto, esquema, effort, max_tokens, tarea=None):
        # Caché de prompts en las instrucciones fijas. Borradores: 1 hora (llegan sueltos a lo largo del día y sus
        # instrucciones son largas: una escritura a 2× por hora sale más barata que reescribir cada 5 minutos).
        cc = {"type": "ephemeral", "ttl": "1h"} if tarea == "borrador" else {"type": "ephemeral"}
        pet = dict(model=modelo, max_tokens=max_tokens,
                   system=[{"type": "text", "text": sistema, "cache_control": cc}],
                   messages=[{"role": "user", "content": json.dumps(contexto, ensure_ascii=False)}])
        oc = {"format": {"type": "json_schema", "schema": esquema}}
        if not modelo.startswith("claude-haiku"):        # Haiku 4.5: sin pensamiento adaptativo ni esfuerzo
            pet["thinking"] = {"type": "adaptive"}
            oc["effort"] = effort
        pet["output_config"] = oc
        return pet

    @staticmethod
    def _clasificar(e):
        import anthropic
        txt = str(getattr(e, "message", "") or e)
        cuerpo = getattr(e, "body", None) or {}
        codigo = json.dumps(cuerpo, ensure_ascii=False) if isinstance(cuerpo, dict) else str(cuerpo)
        if "enforced_spend_limit_reached" in codigo or "usage limits" in txt or "credit balance" in txt.lower():
            return ErrorProveedor("tope_console", "La Console de Anthropic ha cortado: tope de gasto o saldo agotado.")
        if isinstance(e, anthropic.AuthenticationError):
            return ErrorProveedor("caida", "La clave de Anthropic ha sido rechazada (revocada o mal pegada).")
        if isinstance(e, (anthropic.APIConnectionError, anthropic.APITimeoutError)):
            return ErrorProveedor("caida", "Sin conexión con Anthropic desde el servidor.")
        if isinstance(e, anthropic.RateLimitError):
            return ErrorProveedor("otro", "Anthropic pide esperar un poco (límite de peticiones por minuto). Prueba en un minuto.")
        if isinstance(e, anthropic.APIStatusError):
            if getattr(e, "status_code", 0) >= 500:
                return ErrorProveedor("caida", f"Anthropic está caído o sobrecargado (error {e.status_code}).")
            return ErrorProveedor("otro", f"Anthropic ha devuelto un error {e.status_code}. Prueba otra vez en un rato.")
        return ErrorProveedor("otro", "Error inesperado al llamar a Anthropic.")

    @staticmethod
    def _uso(r):
        u = getattr(r, "usage", None)
        g = (lambda k: int(getattr(u, k, 0) or 0)) if u is not None else (lambda k: 0)
        cc = getattr(u, "cache_creation", None) if u is not None else None
        una_hora = int(getattr(cc, "ephemeral_1h_input_tokens", 0) or 0) if cc is not None else 0
        return {"entrada": g("input_tokens"), "cache_escrita": max(0, g("cache_creation_input_tokens") - una_hora),
                "cache_escrita_1h": una_hora, "cache_leida": g("cache_read_input_tokens"), "salida": g("output_tokens")}

    def crear(self, clave, modelo, sistema, contexto, esquema, effort, max_tokens, tarea=None):
        _exigir_real()
        import anthropic
        cliente = anthropic.Anthropic(api_key=clave, timeout=180, max_retries=1)
        pet = self.peticion(modelo, sistema, contexto, esquema, effort, max_tokens, tarea)
        _exigir_real()
        try:
            if modelo.startswith(("claude-opus-5", "claude-fable")):   # respaldo por rechazo dentro de la misma llamada
                pet["betas"] = ["server-side-fallback-2026-07-01"]
                try:
                    r = cliente.beta.messages.create(**pet, fallbacks="default")
                except TypeError:
                    _exigir_real()
                    r = cliente.beta.messages.create(**pet, extra_body={"fallbacks": "default"})
            else:
                r = cliente.messages.create(**pet)
        except anthropic.APIError as e:
            raise self._clasificar(e)
        uso = self._uso(r)
        if r.stop_reason == "refusal":
            return None, getattr(r, "model", modelo), uso, "El modelo no ha querido redactar esto. Escríbelo a mano."
        if r.stop_reason == "max_tokens":
            return None, getattr(r, "model", modelo), uso, "La respuesta se ha cortado. Prueba otra vez."
        texto = next((b.text for b in r.content if getattr(b, "type", "") == "text"), "")
        return json.loads(texto), getattr(r, "model", modelo), uso, None

    # ---------------- lotes (Batch API: la mitad de precio, resultado en menos de 24 h)
    def lote_crear(self, clave, peticiones):
        _exigir_real()
        import anthropic
        cliente = anthropic.Anthropic(api_key=clave, timeout=120, max_retries=1)
        try:
            b = cliente.messages.batches.create(requests=[{"custom_id": cid, "params": p} for cid, p in peticiones])
        except anthropic.APIError as e:
            raise self._clasificar(e)
        return b.id

    def lote_resultados(self, clave, lote_id):
        """None si aún no ha terminado; si no, {custom_id: (salida|None, modelo, uso, motivo)}."""
        _exigir_real()
        import anthropic
        cliente = anthropic.Anthropic(api_key=clave, timeout=120, max_retries=1)
        if cliente.messages.batches.retrieve(lote_id).processing_status != "ended":
            return None
        out = {}
        for x in cliente.messages.batches.results(lote_id):
            if x.result.type == "succeeded":
                m = x.result.message
                texto = next((b.text for b in m.content if getattr(b, "type", "") == "text"), "")
                try:
                    out[x.custom_id] = (json.loads(texto), m.model, self._uso(m), None)
                except ValueError:
                    out[x.custom_id] = (None, m.model, self._uso(m), "Respuesta del lote ilegible")
            else:
                out[x.custom_id] = (None, None, {}, f"Lote: {x.result.type}")
        return out


PROVEEDOR = ProveedorAnthropic()     # las pruebas lo cambian por uno simulado


# ======================================================================= la llamada
def tarea_de(sistema):
    ia = sys.modules.get("ia")
    if ia is not None:
        for nombre, var in (("borrador", "SISTEMA_BORRADOR"), ("copiloto", "SISTEMA_COPILOTO"), ("consejo", "SISTEMA_CONSEJO"),
                            ("clasificar", "SISTEMA_CLASIFICAR")):
            if getattr(ia, var, None) is sistema or (getattr(ia, var, None) and getattr(ia, var) == sistema):
                return nombre
    return "otra"


def llamar(sistema, contexto, esquema, effort="medium", tarea=None):
    """No compra sin identidad, conteo acreditado y reserva durable previa.

    El adaptador actual no incorpora contar_entrada: permanece en reglas hasta
    integrar y verificar ese contrato; no se infiere un máximo por caracteres.
    """
    _exigir_real()
    if S is None: raise SinGasto("Control de gasto sin conectar: no se compra IA.")
    real, persona, objeto = peticion_actual()
    if not isinstance(real,str) or not real or real != persona or real in ('tuberia','sistema'):
        raise SinGasto("Falta identidad real/vista coincidente; no se compra IA en ver como ni sin contexto.")
    tarea = tarea or tarea_de(sistema)
    if tarea not in TAREAS: raise SinGasto("Función IA desconocida.")
    t = topes()
    if tarea=='consejo' and objeto not in (t.get('consejo_pantallas') or []): raise SinGasto("Consejo fuera de pantalla autorizada: reglas.")
    modelo = modelo_de(tarea); precio(modelo)
    max_tokens = TAREAS[tarea]['max_tokens']
    entrada = json.dumps([sistema,contexto,esquema],ensure_ascii=False,allow_nan=False)
    if len(entrada.encode('utf-8'))>524288: raise SinGasto("Contexto demasiado extenso; no se compra IA.")
    contador = getattr(PROVEEDOR,'contar_entrada',None)
    if not callable(contador): raise SinGasto("Falta contador de entrada acreditado: modo reglas, sin compra.")
    _exigir_real()
    conteo = contador(modelo,sistema,contexto,esquema,effort,max_tokens,tarea=tarea)
    if not isinstance(conteo,dict) or conteo.get('acreditado') is not True or conteo.get('modelo')!=modelo or type(conteo.get('tokens')) is not int or conteo['tokens']<0:
        raise SinGasto("Conteo de entrada no acreditado para este modelo: no se compra IA.")
    maximo = coste_maximo(modelo,entrada,max_tokens,t=t,entrada_tokens=conteo['tokens'])
    clave_p = _clave_principal()
    if not clave_p: raise SinGasto("IA sin clave: no se compra.")
    rid = _comprobar_y_reservar(tarea,real,'principal',maximo,t)
    llave='principal'
    try:
        try:
            _exigir_real()
            salida,mod,uso,motivo=PROVEEDOR.crear(clave_p,modelo,sistema,contexto,esquema,effort,max_tokens,tarea=tarea)
        except ErrorProveedor as e:
            _retener_reserva(rid)  # Un timeout/rechazo posterior no demuestra coste cero.
            if e.tipo=='tope_console':
                apuntar(tarea,real,objeto,modelo,llave,{},False,'tope_console: resultado incierto',t=t)
                raise SinGasto('Console en pausa; reserva incierta conservada.')
            if e.tipo!='caida': raise SinGasto('Resultado del proveedor incierto; reserva conservada.')
            clave_r=clave_respaldo()
            if not clave_r: raise SinGasto('Resultado incierto sin respaldo; reserva conservada.')
            # La primera reserva continúa: el segundo request consume otro presupuesto.
            rid=_comprobar_y_reservar(tarea,real,'respaldo',maximo,t); llave='respaldo'
            _exigir_real()
            salida,mod,uso,motivo=PROVEEDOR.crear(clave_r,modelo,sistema,contexto,esquema,effort,max_tokens,tarea=tarea)
        if not isinstance(uso,dict) or not uso or 'entrada' not in uso or 'salida' not in uso:
            raise SinGasto('Respuesta sin uso acreditado; reserva conservada.')
        apuntar(tarea,real,objeto,mod or modelo,llave,uso,motivo is None,motivo,t=t,reserva_id=rid)
        try: _umbrales(t)
        except Exception: pass
        if motivo: raise SinGasto('Respuesta no utilizable; gasto registrado.')
        return salida,mod or modelo
    except BaseException:
        _retener_reserva(rid)
        raise



# ======================================================================= lotes nocturnos (lo que puede esperar)
def lote_enviar(tarea, trabajos, quien="tuberia"):
    raise SinGasto("Lotes en pausa: falta claim previo, conteo acreditado y recuperación durable validados. No se ha enviado nada.")


def reservado_en_lotes():
    try:
        with S.conectar() as con:
            return float(con.execute("SELECT COALESCE(SUM(reservado_eur),0) FROM ia_lotes WHERE estado='enviado'").fetchone()[0] or 0)
    except Exception:
        return 0.0


def lote_recoger(lote_id):
    raise SinGasto("Recogida de lotes en pausa: requiere conciliación idempotente verificada; no se libera su reserva.")


# ======================================================================= pantalla «Gasto de IA» (solo Tomás)
def puede_ver(real, persona):
    return real["id"] == persona["id"] and "direccion" in S.P.puestos_de(persona) and persona["id"] == "tomas"


def _nombre(pid):
    if pid in ("tuberia", "sistema"):
        return "Tubería (de noche)"
    p = S.E.persona(pid) if pid else None
    return (p.get("alias") or p.get("nombre")) if p else pid


def resumen():
    t = topes()
    m, d = _mes(), _hoy()
    a = ahora()
    with S.conectar() as con:
        por_f = con.execute("SELECT tarea, SUM(coste_eur), COUNT(*), SUM(ok), MAX(modelo) FROM ia_gasto WHERE mes=? GROUP BY tarea", (m,)).fetchall()
        por_p = con.execute("SELECT quien, SUM(coste_eur), COUNT(*) FROM ia_gasto WHERE mes=? GROUP BY quien ORDER BY 2 DESC", (m,)).fetchall()
        por_p_dia = {r[0]: r[1] for r in con.execute("SELECT quien, SUM(coste_eur) FROM ia_gasto WHERE dia=? GROUP BY quien", (d,)).fetchall()}
        por_m = con.execute("SELECT modelo, llave, SUM(coste_eur), COUNT(*), SUM(entrada), SUM(cache_escrita), SUM(cache_leida), SUM(salida) "
                            "FROM ia_gasto WHERE mes=? GROUP BY modelo, llave ORDER BY 3 DESC", (m,)).fetchall()
        dias = con.execute("SELECT dia, SUM(coste_eur), COUNT(*) FROM ia_gasto WHERE mes=? GROUP BY dia ORDER BY dia", (m,)).fetchall()
        ultimas = con.execute("SELECT creada, quien, tarea, objeto, modelo, llave, lote, entrada, cache_escrita, cache_leida, salida, coste_eur, ok, motivo "
                              "FROM ia_gasto ORDER BY id DESC LIMIT 40").fetchall()
        hist = con.execute("SELECT creada, quien, valores, motivo FROM ia_topes ORDER BY id DESC LIMIT 20").fetchall()
        lotes = con.execute("SELECT id, creado, tarea, n, reservado_eur, estado, cerrado FROM ia_lotes ORDER BY creado DESC LIMIT 10").fetchall()
    g = gastado()
    dias_mes = (datetime(a.year + (a.month == 12), a.month % 12 + 1, 1) - timedelta(days=1)).day
    transcurrido = (a.day - 1) + (a.hour * 60 + a.minute) / 1440
    prevision = round(g["mes"] / transcurrido * dias_mes, 2) if transcurrido >= 0.25 and g["mes"] else round(g["mes"], 2)
    tf = t.get("funcion_mes_eur") or {}
    funciones = {r[0]: r for r in por_f}
    md = modo()
    return {
        "ok": True, "hoy": d, "mes": m, "generado": a.strftime("%Y-%m-%d %H:%M"),
        "modo": md["modo"], "motivo": md["motivo"],
        "gasto": {"mes": round(g["mes"], 4), "dia": round(g["dia"], 4), "reservado": round(_reservado(), 4),
                  "prevision_mes": prevision, "dias_mes": dias_mes},
        "topes": t,
        "pct": {"mes": round(g["mes"] / t["mes_eur"] * 100, 1) if t["mes_eur"] else None,
                "dia": round(g["dia"] / t["dia_eur"] * 100, 1) if t["dia_eur"] else None},
        "por_funcion": [{"tarea": k, "nombre": c["nombre"], "modelo": modelo_de(k), "eur": round(float((funciones.get(k) or [0, 0])[1] or 0), 4),
                         "llamadas": int((funciones.get(k) or [0, 0, 0])[2] or 0), "tope_mes": float(tf.get(k, 0))} for k, c in TAREAS.items()],
        "por_persona": [{"id": r[0], "nombre": _nombre(r[0]), "eur_mes": round(float(r[1] or 0), 4), "llamadas": r[2],
                         "eur_hoy": round(float(por_p_dia.get(r[0]) or 0), 4)} for r in por_p],
        "por_modelo": [{"modelo": r[0], "llave": r[1], "eur": round(float(r[2] or 0), 4), "llamadas": r[3], "entrada": r[4] or 0,
                        "cache_escrita": r[5] or 0, "cache_leida": r[6] or 0, "salida": r[7] or 0} for r in por_m],
        "por_dia": [{"dia": r[0], "eur": round(float(r[1] or 0), 4), "llamadas": r[2]} for r in dias],
        "ultimas": [{"creada": r[0], "quien": _nombre(r[1]), "tarea": (TAREAS.get(r[2]) or TAREAS["otra"])["nombre"], "objeto": r[3], "modelo": r[4],
                     "llave": r[5], "lote": bool(r[6]), "entrada": r[7], "cache_escrita": r[8], "cache_leida": r[9], "salida": r[10],
                     "eur": round(float(r[11] or 0), 5), "ok": bool(r[12]), "motivo": r[13]} for r in ultimas],
        "historial_topes": [{"creada": r[0], "quien": _nombre(r[1]), "valores": json.loads(r[2] or "{}"), "motivo": r[3]} for r in hist],
        "lotes": [{"id": r[0], "creado": r[1], "tarea": r[2], "n": r[3], "reservado_eur": r[4], "estado": r[5], "cerrado": r[6]} for r in lotes],
        "llaves": {"principal": bool(_clave_principal()), "respaldo": bool(clave_respaldo()),
                   "respaldo_mes_eur": round(_suma("mes=? AND llave='respaldo'", (m,))[0], 4)},
        "precios": {"fuente": FUENTE_PRECIOS, "fecha": FECHA_PRECIOS, "verificados": PRECIOS_VERIFICADOS, "lote": DESCUENTO_LOTE,
                    "modelos": {k: v for k, v in PRECIOS.items() if k in {modelo_de(x) for x in TAREAS} | {"claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5"}}},
    }


def _num(v, nombre, lim):
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"«{nombre}» tiene que ser un número.")
    if isinstance(v,bool) or not math.isfinite(x) or not (lim[0] <= x <= lim[1]):
        raise ValueError(f"«{nombre}» tiene que estar entre {lim[0]} y {lim[1]}.")
    return round(x, 2)


def validar(nuevos, actuales):
    if not isinstance(nuevos,dict): raise ValueError("Topes mal formados.")
    out = json.loads(json.dumps(actuales))
    for k in ("mes_eur", "dia_eur", "aviso_pct", "persona_dia_eur", "respaldo_mes_eur", "usd_a_eur"):
        if k in nuevos:
            out[k] = _num(nuevos[k], k, LIMITES[k])
    if "activa" in nuevos:
        if not isinstance(nuevos["activa"], bool):
            raise ValueError("«activa» es sí o no.")
        out["activa"] = nuevos["activa"]
    if "funcion_mes_eur" in nuevos:
        if not isinstance(nuevos["funcion_mes_eur"], dict):
            raise ValueError("Topes por función mal formados.")
        for k, v in nuevos["funcion_mes_eur"].items():
            if k not in TAREAS:
                raise ValueError(f"No existe la función «{k}».")
            out["funcion_mes_eur"][k] = _num(v, k, LIMITES["funcion"])
    if out["dia_eur"] > out["mes_eur"]:
        raise ValueError("El tope del día no puede ser mayor que el del mes.")
    return out


def get(h, ruta, q, real, persona):
    if not puede_ver(real, persona):
        S.registrar_agrupado(real["id"], "ia", "ia_denegado", "gasto", {"ruta": ruta, "motivo": "Gasto de IA: solo Tomás"},
                             como=persona["id"] if real["id"] != persona["id"] else None)
        return h.responder(403, {"error": "El gasto de la IA solo lo ve Tomás."})
    return h.responder(200, resumen())


def post(h, ruta, real, persona, b):
    if not puede_ver(real, persona):
        S.registrar_agrupado(real["id"], "ia", "ia_denegado", "gasto", {"ruta": ruta, "motivo": "Gasto de IA: solo Tomás"},
                             como=persona["id"] if real["id"] != persona["id"] else None)
        return h.responder(403, {"error": "Los topes de la IA solo los cambia Tomás."})
    motivo = str(b.get("motivo") or "").strip()[:300]
    if ruta == "/api/ia/gasto/topes":
        antes = topes()
        try:
            nuevos = validar(b.get("valores") or {}, antes)
        except ValueError as e:
            return h.responder(400, {"error": str(e)})
        cambios = {k: {"antes": antes.get(k), "despues": nuevos.get(k)} for k in nuevos if nuevos.get(k) != antes.get(k)}
        if not cambios:
            return h.responder(200, {"ok": True, "sin_cambios": True, **resumen()})
        with S.conectar() as con:
            con.execute("INSERT INTO ia_topes (creada, quien, valores, motivo) VALUES (?,?,?,?)",
                        (ahora().strftime("%Y-%m-%d %H:%M:%S"), real["id"], json.dumps(nuevos, ensure_ascii=False), motivo or "cambio de topes"))
        S.registrar(real["id"], "ia", "ia_topes_cambiados", "topes", {"cambios": cambios}, motivo=motivo or None)
        return h.responder(200, {"ok": True, "cambios": cambios, **resumen()})
    if ruta == "/api/ia/gasto/reabrir":
        with S.conectar() as con:
            con.execute("INSERT INTO ia_topes (creada, quien, valores, motivo) VALUES (?,?,?,?)",
                        (ahora().strftime("%Y-%m-%d %H:%M:%S"), real["id"], json.dumps(topes(), ensure_ascii=False),
                         "reabrir: " + (motivo or "límite de la Console subido")))
        S.registrar(real["id"], "ia", "ia_reabierta", "console", {"motivo": motivo or "límite de la Console subido"})
        return h.responder(200, {"ok": True, **resumen()})
    return h.responder(404, {"error": "No existe esa ruta del gasto de la IA."})


def enganchar(servir):
    global S
    S = servir
    iniciar()
