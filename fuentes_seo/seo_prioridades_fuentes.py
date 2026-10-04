"""Adaptación separada de las fuentes existentes. Solo el cargador hace IO local."""
import json
import math
import os
import re
import stat
from datetime import date
from pathlib import Path
try:
    from .seo_prioridades import consultas_objetivo, normalizar, evaluar_seo
    from .posiciones import posicion, preparar_motores
    from .motores_contexto import contexto_desde_cache
except ImportError:
    from seo_prioridades import consultas_objetivo, normalizar, evaluar_seo
    from posiciones import posicion, preparar_motores
    from motores_contexto import contexto_desde_cache


def _id(v):
    return isinstance(v, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,150}', v) is not None

def _error(d):
    return isinstance(d, dict) and any(k in d and d[k] not in (None, False, '') for k in ('_error', '_source_error', 'error'))

def _numero(v):
    try:
        return type(v) in (int, float) and math.isfinite(v) and v >= 0
    except OverflowError:
        return False

def _recurso(d, tipo, cid):
    """Valida identidad/colecciones, sin seleccionar una variante duplicada como autoridad."""
    if not isinstance(d, dict) or not isinstance(d.get('clientes'), dict):
        return {}, 'estructura_invalida'
    cs=d['clientes']
    if any(not _id(k) or not isinstance(v,dict) or ('cliente_id' in v and v['cliente_id']!=k) for k,v in cs.items()):
        return {}, 'identidad_invalida'
    if _error(d): return {}, 'fuente_con_error'
    if cid not in cs: return {}, 'sin_registro'
    r=cs[cid]
    if _error(r): return {}, 'fuente_con_error'
    if tipo=='ranking':
        ms=r.get('motores')
        if not isinstance(ms,list): return {}, 'estructura_invalida'
        mids=[]
        for m in ms:
            if not isinstance(m,dict) or _error(m) or not isinstance(m.get('palabras'),list): return {}, 'estructura_invalida' if not _error(m) else 'fuente_con_error'
            mid=m.get('site_engine_id')
            if isinstance(mid,bool) or not (isinstance(mid,int) and 0<=mid<10**16 or isinstance(mid,str) and re.fullmatch(r'[0-9]{1,16}',mid)): return {}, 'identidad_invalida'
            mids.append(str(int(mid)))
            words=[]
            for w in m['palabras']:
                if not isinstance(w,dict) or not isinstance(w.get('k'),str) or not w['k'].strip() or len(w['k'])>500: return {}, 'estructura_invalida'
                if _error(w): return {}, 'fuente_con_error'
                if 'fechas' in w and not isinstance(w['fechas'],dict): return {}, 'estructura_invalida'
                if any(type(w.get(k)) in (int,float) and not _numero(w[k]) for k in ('hoy','ayer','sem','sem2','mes','mapa') if w.get(k) is not None): return {}, 'valor_invalido'
                words.append(' '.join(w['k'].casefold().split()))
            if len(set(words))!=len(words): return {}, 'identidad_duplicada'
        if len(set(mids))!=len(mids): return {}, 'identidad_duplicada'
    elif tipo=='gsc':
        if not isinstance(r.get('paginas'),list) or not isinstance(r.get('ventanas'),dict): return {}, 'estructura_invalida'
        urls=[]
        for row in r['paginas']:
            if not isinstance(row,list) or len(row)<5 or not isinstance(row[0],str) or not row[0].strip(): return {}, 'estructura_invalida'
            if any(not (x is None or _numero(x)) for x in row[1:5]): return {}, 'valor_invalido'
            urls.append(row[0])
        if len(set(urls))!=len(urls): return {}, 'identidad_duplicada'
    elif tipo=='motores':
        if not isinstance(r.get('configuraciones',[]),list) or any(not isinstance(x,dict) for x in r.get('configuraciones',[])) or not isinstance(d.get('catalogo',[]),list) or any(not isinstance(x,dict) for x in d.get('catalogo',[])): return {}, 'estructura_invalida'
    return d, 'disponible'


def adaptar_fuentes(contexto, seranking, gsc, contexto_motores=None):
    seranking, estado_sr = _recurso(seranking, 'ranking', contexto.get('cliente_id'))
    gsc, estado_gsc = _recurso(gsc, 'gsc', contexto.get('cliente_id'))
    contexto_motores, estado_motores = _recurso(contexto_motores, 'motores', contexto.get('cliente_id'))
    objetivos = {normalizar(o['consulta']): o for o in consultas_objetivo(contexto)}
    sr = (seranking.get('clientes') or {}).get(contexto.get('cliente_id'), {})
    datos = {'rankings': [], 'paginas': [], 'contenido': {}, 'cobertura': {
        'ranking': 'Solo consultas exactas disponibles; ubicaciones/dispositivos no preservados en caché.',
        'gsc': 'Hasta 12 páginas actuales y 250 anteriores, no inventario completo.',
        'contenido': 'No hay inventario fechado de artículos ni objetivo editorial en las fuentes SEO actuales.',
        'ga4': 'Totales/canales disponibles; no evidencia de clics o ventas por landing en este adaptador.'}}
    motores=preparar_motores(sr.get('motores',[]))
    metadatos=contexto_desde_cache(contexto.get('cliente_id'),sr.get('proyecto'),motores,contexto_motores)
    por_motor={m.get('site_engine_id'):m for m in metadatos}
    for motor in motores:
        con=por_motor.get(motor.get('site_engine_id'),{})
        for palabra in motor.get('palabras', []):
            objetivo = objetivos.get(normalizar(palabra.get('k')))
            if not objetivo:
                continue
            for canal, campo in [('organico', 'hoy'), ('maps', 'mapa')]:
                datos['rankings'].append({**objetivo, 'consulta': palabra.get('k'), 'canal': canal, 'posicion':posicion(palabra.get(campo)),
                    'fecha':(palabra.get('fechas') or {}).get(campo), 'fuente': 'SE Ranking: caché de proyectos',
                    'medicion_id':str(motor.get('site_engine_id')) if motor.get('site_engine_id') is not None else None,
                    'dispositivo':{'mobile':'movil','desktop':'desktop'}.get(con.get('dispositivo')) if con.get('dispositivo_estado')=='confirmado' else None,'ubicacion_medicion':con.get('region'), 'url_o_ficha': None,
                    'cobertura': 'parcial: contexto del motor pendiente'})
    gs = (gsc.get('clientes') or {}).get(contexto.get('cliente_id'), {})
    ventanas = gs.get('ventanas') or {}
    mes, anterior = ventanas.get('mes'), ventanas.get('mes_ant')
    comparable = False
    try:
        a, b = [date.fromisoformat(x) for x in mes]
        c, d = [date.fromisoformat(x) for x in anterior]
        comparable = a <= b and c <= d and (b-a).days == (d-c).days and (a-d).days == 1
    except (TypeError, ValueError):
        pass
    if not gs.get('_error'):
        for fila in gs.get('paginas', []):
            if isinstance(fila, list) and len(fila) >= 5:
                datos['paginas'].append({'url': fila[0], 'clics': fila[1], 'impresiones': fila[2],
                    'posicion_media': fila[3], 'clics_antes': fila[4], 'fecha': gs.get('hasta'),
                    'fuente': 'GSC: caché, últimas ventanas cerradas de 28 días',
                    'periodos_comparables': comparable, 'periodo_actual': mes, 'periodo_anterior': anterior})
    datos['diagnosticos_fuentes'] = {'seranking':estado_sr,'gsc':estado_gsc,'seranking_motores':estado_motores}
    return datos


def cargar_local(app, contexto, hoy):
    """No lee credenciales ni llama APIs. Root debe pasar contexto autorizado."""
    carpeta = Path(app) / 'fuentes_seo' / '_cache'
    estados={}
    def pares(items):
        out={}
        for k,v in items:
            if k in out: raise ValueError('duplicado')
            out[k]=v
        return out
    def leer(nombre, clave):
        ruta=carpeta/nombre
        try:
            fd=os.open(ruta,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
            with os.fdopen(fd,'rb') as f:
                antes=os.fstat(f.fileno())
                if not stat.S_ISREG(antes.st_mode) or antes.st_size>10_000_000: raise ValueError('recurso')
                raw=f.read(10_000_001)
                despues=os.fstat(f.fileno())
                if len(raw)>10_000_000 or (antes.st_ino,antes.st_size,antes.st_mtime_ns,antes.st_ctime_ns)!=(despues.st_ino,despues.st_size,despues.st_mtime_ns,despues.st_ctime_ns): raise ValueError('rotacion')
            doc=json.loads(raw.decode('utf-8-sig'),object_pairs_hook=pares,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('no_finito')))
            estados[clave]='leida'
            return doc
        except FileNotFoundError:
            estados[clave]='ausente'
        except (ValueError,UnicodeError,RecursionError):
            estados[clave]='copia_invalida'
        except OSError:
            estados[clave]='no_disponible'
        return {}
    datos = adaptar_fuentes(contexto, leer('seranking.json','seranking'),leer('gsc.json','gsc'),leer('seranking_motores.json','seranking_motores'))
    for k,v in estados.items():
        if v!='leida': datos['diagnosticos_fuentes'][k]=v
    resultado = evaluar_seo(contexto, datos, hoy)
    resultado['cobertura'] = datos['cobertura']
    resultado['diagnosticos_fuentes'] = datos['diagnosticos_fuentes']
    return resultado
