"""Medición local de facilidad de uso. Sin contenido ni destinos externos.
Los intervalos declarados son señales de interacción, nunca horas trabajadas.
"""
import math
import os
import sqlite3
import re
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo

ACCIONES = frozenset({'abrir', 'interaccion', 'latido', 'ocultar', 'error'})
RETENCION_DIAS = 30
MAX_VENTANA_MS = 30000
CONTROLES = frozenset({'boton','enlace','pestana','filtro','campo','copiar-ia','preparar-ia','abrir-tarea','guardar','buscar','menu','periodo','volver','exportar','cambiar-vista','ninguno'})
CAMPOS = frozenset({'sesion', 'secuencia', 'pantalla', 'accion', 'control', 'activo_ms'})
S = None
LOCK = threading.Lock()
SCHEMA = '''
CREATE TABLE IF NOT EXISTS uso_eventos (
 id INTEGER PRIMARY KEY, instante REAL NOT NULL, actor TEXT NOT NULL,
 visto TEXT NOT NULL, pantalla TEXT NOT NULL, accion TEXT NOT NULL, control TEXT NOT NULL, activo_ms INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS uso_instante ON uso_eventos(instante);
CREATE INDEX IF NOT EXISTS uso_actor ON uso_eventos(actor, instante);
CREATE TABLE IF NOT EXISTS uso_sesiones (
 actor TEXT NOT NULL, sesion TEXT NOT NULL, secuencia INTEGER NOT NULL,
 instante REAL NOT NULL, visto TEXT NOT NULL, pantalla TEXT NOT NULL,
 PRIMARY KEY(actor,sesion));
CREATE TABLE IF NOT EXISTS uso_ventanas (
 actor TEXT PRIMARY KEY, fin REAL NOT NULL);
'''


def validar(b, pantallas):
    if not isinstance(b, dict) or set(b) != CAMPOS:
        raise ValueError('Envía solo los seis campos de medición permitidos.')
    if not isinstance(b['sesion'], str) or not re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', b['sesion']):
        raise ValueError('Sesión de medición no válida.')
    if type(b['secuencia']) is not int or not 0 <= b['secuencia'] <= 2147483647:
        raise ValueError('Secuencia no válida.')
    if not isinstance(b['pantalla'], str) or b['pantalla'] not in pantallas:
        raise ValueError('Pantalla no permitida.')
    if not isinstance(b['accion'], str) or b['accion'] not in ACCIONES:
        raise ValueError('Acción no permitida.')
    if not isinstance(b['control'], str) or b['control'] not in CONTROLES:
        raise ValueError('Control no permitido.')
    if type(b['activo_ms']) not in (int, float) or not math.isfinite(b['activo_ms']) or not 0 <= b['activo_ms'] <= MAX_VENTANA_MS:
        raise ValueError('Intervalo activo no válido (0 a 30000 ms).')
    return b


def purgar(con, t):
    corte = t - RETENCION_DIAS * 86400
    con.execute('DELETE FROM uso_eventos WHERE instante < ?', (corte,))
    con.execute('DELETE FROM uso_sesiones WHERE instante < ?', (corte,))
    con.execute('DELETE FROM uso_ventanas WHERE fin < ?', (corte,))


def guardar(con, real, vista, b, ahora=None):
    """Conexión exclusiva por petición. BEGIN IMMEDIATE serializa también procesos.
    Primer evento, cambio de pantalla/persona y abrir no imputan intervalo anterior.
    Unión conservadora de intervalos por actor impide duplicar pestañas.
    """
    t = time.time() if ahora is None else ahora
    con.execute('BEGIN IMMEDIATE')
    purgar(con,t)
    anterior = con.execute('SELECT * FROM uso_sesiones WHERE actor=? AND sesion=?', (real, b['sesion'])).fetchone()
    if anterior and b['secuencia'] <= anterior['secuencia']:
        con.commit()
        return {'ok': True, 'duplicado': True, 'activo_ms': 0}
    n = con.execute('SELECT count(*) FROM uso_eventos WHERE actor=? AND instante>?', (real, t-60)).fetchone()[0]
    if n >= 120:
        con.rollback()
        return {'ok': False, 'limite': True}
    # Clampea con reloj servidor; un salto/desconexión nunca recupera horas abiertas.
    ms = 0
    if anterior and anterior['visto'] == vista and anterior['pantalla'] == b['pantalla'] and b['accion'] != 'abrir':
        ms = min(int(b['activo_ms']), MAX_VENTANA_MS, max(0, int((t-anterior['instante'])*1000)))
    fin = con.execute('SELECT fin FROM uso_ventanas WHERE actor=?', (real,)).fetchone()
    if fin:
        ms = min(ms, max(0, int((t-fin[0])*1000)))
    con.execute('INSERT OR REPLACE INTO uso_sesiones VALUES(?,?,?,?,?,?)', (real,b['sesion'],b['secuencia'],t,vista,b['pantalla']))
    # No desplazar la ventana por eventos sin actividad: otra pestaña puede aportar tiempo.
    if ms:
        con.execute('INSERT OR REPLACE INTO uso_ventanas VALUES(?,?)', (real,t))
    con.execute('INSERT INTO uso_eventos(instante,actor,visto,pantalla,accion,control,activo_ms) VALUES(?,?,?,?,?,?,?)', (t,real,vista,b['pantalla'],b['accion'],b['control'],ms))
    con.commit()
    return {'ok': True, 'activo_ms': ms}


def disponible():
    return not bool(os.environ.get('DATABASE_URL'))


def aviso():
    if not disponible():
        return {'local': True, 'disponible': False, 'retencion_dias': RETENCION_DIAS,
                'texto': 'La medición de uso está desactivada: esta primera versión requiere la base local SQLite. No se están recogiendo eventos.'}
    return {'local': True, 'disponible': True, 'retencion_dias': RETENCION_DIAS,
            'texto': 'Medimos pantallas, acciones generales y tiempo de interacción para facilitar el uso. Datos locales durante 30 días; sin textos, pulsaciones ni grabaciones. Dirección y operaciones pueden consultar el resumen. No mide horas trabajadas ni rendimiento.'}


def resumen(con, dias=7, ahora=None):
    t = time.time() if ahora is None else ahora
    # Purga también al consultar, incluso sin interacción reciente del equipo.
    purgar(con,t)
    con.commit()
    desde = t - min(dias,RETENCION_DIAS)*86400
    con.create_function('uso_dia',1,lambda instante:datetime.fromtimestamp(instante,ZoneInfo('Europe/Madrid')).date().isoformat(),deterministic=True)
    filas = con.execute('''SELECT actor, visto, pantalla, accion, control, sum(activo_ms) activo_ms, count(*) eventos,
        uso_dia(instante) dia FROM uso_eventos WHERE instante>=? AND instante<=?
        GROUP BY actor,visto,pantalla,accion,control,dia ORDER BY dia,actor,visto,pantalla,accion,control''', (desde,t)).fetchall()
    return {'dias': dias, 'zona_dias': 'Europe/Madrid', 'retencion_dias': RETENCION_DIAS,
            'filas': [dict(r) for r in filas], 'aviso': aviso()['texto'],
            'limites': 'Señales declaradas por el navegador, con topes y sin duplicar pestañas. No son horas de trabajo; los silencios pueden ser tareas fuera de la app. Ver como queda separado.'}


def puede_resumen(real, vista):
    return real['id'] == vista['id'] and bool(set(real.get('puestos') or []) & {'direccion','operaciones'})


def enganchar(Manejador, servir):
    global S
    S = servir
    # Enganchar/importar nunca abre ni modifica la base.
    get_orig, post_orig = Manejador._api_get, Manejador.api_post

    def get(self, ruta, q, real, persona):
        if ruta not in ('/api/uso','/api/uso/aviso'):
            return get_orig(self,ruta,q,real,persona)
        if S.E.nucleo_bloqueado:
            return self.responder(503, {'error':'Datos temporalmente bloqueados.'})
        if ruta == '/api/uso/aviso':
            return self.responder(200,aviso())
        if not puede_resumen(real,persona):
            return self.responder(403,{'error':'El resumen de uso es de dirección y operaciones en su propia sesión.'})
        try:
            dias = int((q.get('dias') or ['7'])[0])
            if not 1 <= dias <= RETENCION_DIAS:
                raise ValueError()
        except (ValueError,TypeError):
            return self.responder(400,{'error':'Entre 1 y 30 días.'})
        if not disponible():
            return self.responder(503,{'error':aviso()['texto']})
        with LOCK:
            with S.conectar() as con:
                if not isinstance(con,sqlite3.Connection):
                    return self.responder(503,{'error':'La medición de uso requiere SQLite local.'})
                con.executescript(SCHEMA)
                return self.responder(200,resumen(con,dias))

    def post(self,ruta,real,persona,b):
        if ruta != '/api/uso':
            return post_orig(self,ruta,real,persona,b)
        if S.E.nucleo_bloqueado:
            return self.responder(503, {'error':'Datos temporalmente bloqueados.'})
        try:
            validar(b, set(S.E.modulos) | {'app'})
        except ValueError as e:
            return self.responder(400,{'error':str(e)})
        if b['pantalla'] != 'app' and (not S.ve_alguno(real,[b['pantalla']]) or not S.ve_alguno(persona,[b['pantalla']])):
            return self.responder(403,{'error':'Esa pantalla no es visible en esta sesión.'})
        if not disponible():
            return self.responder(503,{'error':aviso()['texto']})
        with LOCK:
            with S.conectar() as con:
                if not isinstance(con,sqlite3.Connection):
                    return self.responder(503,{'error':'La medición de uso requiere SQLite local.'})
                con.executescript(SCHEMA)
                out = guardar(con,real['id'],persona['id'],b)
        return self.responder(429 if out.get('limite') else 200,out)

    Manejador._api_get, Manejador.api_post = get,post
