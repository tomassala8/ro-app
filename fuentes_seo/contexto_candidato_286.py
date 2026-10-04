"""Proyección pura y acotada de configuración actual; no consulta ni escribe proveedores."""
from collections import Counter
from datetime import datetime, timezone
import re

FUENTE_CONFIG = 'https://seranking.com/api/project/project-management/'
FUENTE_CATALOGO = 'https://seranking.com/api/project/general-data/'

def entero(v):
    if isinstance(v, bool): return None
    if isinstance(v, int) and v >= 0: return v
    if isinstance(v, str) and re.fullmatch(r'[0-9]{1,16}', v): return int(v)
    return None

def texto(v):
    if not isinstance(v, str) or not v.strip() or len(v) > 200: return None
    if re.search(r'[\r\n\x00-\x1f]|https?://|@|password|secret|token|guest_link', v, re.I): return None
    return v.strip()

def fecha(v):
    if not isinstance(v, str): return None
    try:
        d = datetime.fromisoformat(v.replace('Z', '+00:00'))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except ValueError: return None

def proyectar(cliente_id, proyecto, motores_permitidos, configuraciones, catalogo, leido, ahora):
    """Caller fija ACT/MAPA; IDs de motores provienen de la copia exacta de ese proyecto.
    Dup IDs se rechazan, no first/last wins. No acredita contexto histórico ni objetivo.
    """
    p = entero(proyecto); f = fecha(leido); a = fecha(ahora)
    if p is None or f is None or a is None or f > a: raise ValueError('identidad_o_fecha_invalida')
    if not isinstance(cliente_id, str) or not re.fullmatch(r'[a-z0-9_-]{1,80}', cliente_id): raise ValueError('cliente_invalido')
    if not isinstance(configuraciones, list) or not isinstance(catalogo, list): raise ValueError('respuesta_invalida')
    permitidos = [entero(x) for x in motores_permitidos]
    if None in permitidos or len(set(permitidos)) != len(permitidos): raise ValueError('motores_ambiguos')
    cs = Counter(entero(x.get('site_engine_id')) for x in configuraciones if isinstance(x, dict))
    es = Counter(entero(x.get('id')) for x in catalogo if isinstance(x, dict))
    cats = {entero(x.get('id')): x for x in catalogo if isinstance(x, dict) and es[entero(x.get('id'))] == 1}
    configs=[]; usados={}; rechazados=0
    for x in configuraciones:
        if not isinstance(x, dict): rechazados+=1; continue
        sid=entero(x.get('site_engine_id')); eid=entero(x.get('search_engine_id'))
        if sid not in permitidos or cs[sid]!=1 or eid is None or eid not in cats: rechazados+=1; continue
        e=cats[eid]; name=texto(e.get('name')); device=e.get('device')
        device_source='campo_provider_no_documentado' if device in ('mobile','desktop') else None
        if device not in ('mobile','desktop'):
            device='mobile' if name and re.search(r'\bmobile\b',name,re.I) else None
            device_source='nombre_catalogo_explicito' if device else None
        maps=entero(x.get('merge_map')); maps=maps if maps in (0,1,2) else None
        configs.append({'site_engine_id':sid,'search_engine_id':eid,'region_id':entero(x.get('region_id')),
                        'region_name':texto(x.get('region_name')),'lang_code':x.get('lang_code') if isinstance(x.get('lang_code'),str) and re.fullmatch(r'[a-z]{2}(?:-[A-Za-z]{2})?',x['lang_code']) else None,
                        'merge_map':maps,'dispositivo':device,'fuente_dispositivo':device_source,
                        'maps_separado':None if maps is None else maps==2,
                        'contexto_historico_confirmado':False,'objetivo_ciudad_confirmado':False})
        usados[eid]={'id':str(eid),'name':name,'regionid':entero(e.get('regionid')),
                     'type':e.get('type') if e.get('type') in ('google','bing','yahoo','yandex') else None}
        if device_source=='campo_provider_no_documentado': usados[eid]['device']=device
    return {'catalogo':list(usados.values()),'registro':{'proyecto':p,'leido':f.isoformat().replace('+00:00','Z'),
            'precision_fecha':'instante_utc','fuente':FUENTE_CONFIG,'configuraciones':configs,
            'cobertura':{'motores_copia':len(permitidos),'motores_confirmados':len(configs),'rechazados':rechazados,'completa':len(configs)==len(permitidos)},
            'contexto_historico_confirmado':False,'objetivo_ciudad_confirmado':False}}
