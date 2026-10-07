"""Contexto puro SE Ranking: configuración observada separada del contexto de posiciones."""
from collections import Counter
from datetime import datetime, date, timezone
import re

def entero(v):
    if isinstance(v, bool): return None
    if isinstance(v, int) and v >= 0: return v
    if isinstance(v, str) and re.fullmatch(r'[0-9]{1,16}', v): return int(v)
    return None

def _texto(v):
    if not isinstance(v, str) or not v.strip() or len(v) > 200: return None
    if re.search(r'[\x00-\x1f]|https?://|@|password|secret|token|guest_link', v, re.I): return None
    return v.strip()

def fecha_contexto_valida(v, ahora=None):
    """Fecha de día sigue siendo día; nunca fabricar hora de una captura antigua."""
    if ahora is None: ahora = datetime.now(timezone.utc)
    if isinstance(ahora, str):
        try: ahora = datetime.fromisoformat(ahora.replace('Z', '+00:00'))
        except ValueError: return None
    if not isinstance(ahora, datetime) or ahora.tzinfo is None: return None
    ahora = ahora.astimezone(timezone.utc)
    if not isinstance(v, str): return None
    try:
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', v):
            d = date.fromisoformat(v)
            return {'fecha': v, 'precision': 'dia'} if d <= ahora.date() else None
        d = datetime.fromisoformat(v.replace('Z', '+00:00'))
        if d.tzinfo is None or d > ahora: return None
        return {'fecha': d.astimezone(timezone.utc).isoformat().replace('+00:00','Z'), 'precision': 'instante_utc'}
    except ValueError: return None

def motores_contexto(configuraciones, catalogo):
    """Descriptor actual por IDs únicos exactos. IDs ambiguos no acreditan metadata."""
    configuraciones = configuraciones if isinstance(configuraciones, list) else []
    catalogo = catalogo if isinstance(catalogo, list) else []
    cuenta_cat = Counter(entero(x.get('id')) for x in catalogo if isinstance(x, dict))
    cat = {entero(x.get('id')): x for x in catalogo if isinstance(x, dict) and entero(x.get('id')) is not None and cuenta_cat[entero(x.get('id'))] == 1}
    cuenta_sid = Counter(entero(x.get('site_engine_id')) for x in configuraciones if isinstance(x, dict))
    salida=[]
    for m in configuraciones:
        if not isinstance(m, dict): continue
        sid=entero(m.get('site_engine_id')); eid=entero(m.get('search_engine_id'))
        if sid is None or cuenta_sid[sid] != 1 or eid not in cat: continue
        e=cat[eid]; nombre=_texto(e.get('name'))
        device=e.get('device') if e.get('device') in ('mobile','desktop') else None
        fuente_device='campo_provider_no_documentado' if device else None
        if device is None and nombre and re.search(r'\bmobile\b',nombre,re.I):
            device='mobile'; fuente_device='nombre_catalogo_explicito'
        maps=entero(m.get('merge_map')); maps=maps if maps in (0,1,2) else None
        idioma=m.get('lang_code')
        idioma=idioma if isinstance(idioma,str) and re.fullmatch(r'[a-z]{2}(?:-[A-Za-z]{2})?',idioma) else None
        salida.append({'site_engine_id':sid,'search_engine_id':eid,'buscador':nombre,
            'tipo':e.get('type') if e.get('type') in ('google','bing','yahoo','yandex') else None,
            'dispositivo':device,'dispositivo_estado':'confirmado' if device else 'sin_dato','fuente_dispositivo':fuente_device,
            'region_id':entero(m.get('region_id')),'region':_texto(m.get('region_name')),'idioma':idioma,
            'maps_modo':maps,'maps_separado':None if maps is None else maps==2,
            'serie_actual':{0:'sin_maps',1:'resultados_con_maps_incluidos',2:'maps_presentados_separadamente'}.get(maps,'desconocida'),
            'fuente':'SE Ranking /sites/search-engines + /system/search-engines'})
    return salida

def contexto_desde_cache(cliente_id, proyecto, motores, documento, ahora=None):
    """No acredita aplicabilidad a posiciones por compartir ID/fecha de lectura.
    Campos legacy de posición quedan unknown. Descriptor disponible en configuracion_actual.
    """
    doc=documento if isinstance(documento,dict) else {}
    clientes=doc.get('clientes') if isinstance(doc.get('clientes'),dict) else {}
    registro=clientes.get(cliente_id,{})
    pid=entero(proyecto)
    cuenta_proyectos=Counter(entero(x.get('proyecto')) for x in clientes.values() if isinstance(x,dict))
    f=fecha_contexto_valida(registro.get('leido'),ahora) if isinstance(registro,dict) else None
    valido=isinstance(registro,dict) and pid is not None and entero(registro.get('proyecto'))==pid and cuenta_proyectos[pid]==1 and f is not None
    configuraciones=registro.get('configuraciones',[]) if valido else []
    proyectados=motores_contexto(configuraciones,doc.get('catalogo'))
    por_id={m['site_engine_id']:m for m in proyectados}
    motores=motores if isinstance(motores,list) else []
    cuenta_motores=Counter(entero(x.get('site_engine_id')) for x in motores if isinstance(x,dict))
    salida=[]
    for motor in motores:
        if not isinstance(motor,dict): continue
        sid=entero(motor.get('site_engine_id')); con=por_id.get(sid) if sid is not None and cuenta_motores[sid]==1 else None
        actual={**con,'fecha_contexto':f['fecha'],'precision_fecha':f['precision']} if con else None
        salida.append({'site_engine_id':sid,'search_engine_id':con.get('search_engine_id') if con else None,
            'buscador':con.get('buscador') if con else None,'tipo':con.get('tipo') if con else None,
            'dispositivo':None,'dispositivo_estado':'sin_dato','region_id':None,'region':None,'idioma':None,
            'maps_modo':None,'maps_separado':None,'principal':motor.get('principal') is True,
            'estado_contexto':'parcial' if con else 'sin_dato','fecha_contexto':f['fecha'] if con else None,
            'configuracion_actual':actual,'serie_actual':con.get('serie_actual') if con else 'desconocida',
            'aplica_fecha_distinta':False,'contexto_posicion_confirmado':False,'objetivo_ciudad_confirmado':False,
            'cobertura':'Configuración observada; aplicabilidad temporal a posiciones no acreditada.'})
    return salida
