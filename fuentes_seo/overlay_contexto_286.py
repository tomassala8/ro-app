"""Overlay puro y revisable; no escribe caché ni acredita historia de configuración."""
from collections import Counter
from .motores_contexto import entero, motores_contexto, fecha_contexto_valida, _texto

def _limpiar(reg, catalogo, ahora):
    if not isinstance(reg,dict):return None
    f=fecha_contexto_valida(reg.get('leido'),ahora)
    if not f:return None
    configs=reg.get('configuraciones')
    if not isinstance(configs,list):return None
    con=motores_contexto(configs,catalogo)
    if len(con)!=len(configs):return None
    return {'proyecto':entero(reg.get('proyecto')),'leido':f['fecha'],'precision_fecha':f['precision'],
            'fuente':reg.get('fuente') if reg.get('fuente')=='https://seranking.com/api/project/project-management/' else _texto(reg.get('fuente')),'configuraciones':[{'site_engine_id':x['site_engine_id'],
            'search_engine_id':x['search_engine_id'],'region_id':x['region_id'],'region_name':x['region'],
            'lang_code':x['idioma'],'merge_map':x['maps_modo']} for x in con],
            'contexto_historico_confirmado':False,'objetivo_ciudad_confirmado':False}

def preparar_overlay(actual,candidato,mapa,posiciones,activos,ahora):
    """activos viene de ACT actual; nunca de payload/browser. Sólo metadata de IDs exactos.
    Evita last-wins en catálogo/proyectos/motores y preserva evidencia previa, no intervalos.
    """
    if not all(isinstance(x,dict) for x in (actual,candidato,mapa,posiciones)):raise ValueError('documentos_invalidos')
    ac=actual.get('clientes');nc=candidato.get('clientes');pc=posiciones.get('clientes')
    if not all(isinstance(x,dict) for x in (ac,nc,pc)):raise ValueError('clientes_invalidos')
    if not isinstance(activos,(set,frozenset)):raise ValueError('activos_no_confirmados')
    if not fecha_contexto_valida(ahora,ahora):raise ValueError('ahora_invalido')
    cat_actual=actual.get('catalogo');cat_nuevo=candidato.get('catalogo')
    if not isinstance(cat_actual,list) or not isinstance(cat_nuevo,list):raise ValueError('catalogo_invalido')
    duplicados=Counter(entero(x) for x in mapa.values())
    proyectos_ac=Counter(entero(x.get('proyecto')) for x in ac.values() if isinstance(x,dict))
    proyectos_nc=Counter(entero(x.get('proyecto')) for x in nc.values() if isinstance(x,dict))
    def scope(cid,reg,cuenta):
        p=entero(mapa.get(cid));row=pc.get(cid)
        if cid not in activos or p is None or duplicados[p]!=1 or cuenta[p]!=1 or not isinstance(row,dict) or entero(row.get('proyecto'))!=p or entero(reg.get('proyecto'))!=p:return False
        ms=row.get('motores');cs=reg.get('configuraciones')
        if not isinstance(ms,list) or not isinstance(cs,list):return False
        ids=[entero(x.get('site_engine_id')) for x in ms if isinstance(x,dict)]
        ids_config=[entero(x.get('site_engine_id')) for x in cs if isinstance(x,dict)]
        return len(ids)==len(ms) and len(ids_config)==len(cs) and None not in ids and None not in ids_config and len(set(ids))==len(ids) and len(set(ids_config))==len(ids_config) and set(ids_config)==set(ids)
    clientes={};reg_cats={};rechazos={};evidencias={}
    for cid,reg in ac.items():
        if isinstance(reg,dict) and scope(cid,reg,proyectos_ac):
            limpio=_limpiar(reg,cat_actual,ahora)
            if limpio:clientes[cid]=limpio;reg_cats[cid]=cat_actual
    for cid,reg in nc.items():
        if not isinstance(reg,dict) or not scope(cid,reg,proyectos_nc):rechazos[cid]='identidad_o_cobertura_no_confirmada';continue
        limpio=_limpiar(reg,cat_nuevo,ahora)
        if not limpio:rechazos[cid]='configuracion_o_fecha_ambigua';continue
        anterior=clientes.get(cid)
        if anterior:
            # Una lectura más vieja nunca reemplaza la configuración observada más reciente.
            if limpio['leido'][:10]<anterior['leido'][:10] or (len(limpio['leido'])>10 and len(anterior['leido'])>10 and limpio['leido']<anterior['leido']):
                rechazos[cid]='lectura_anterior_no_reemplaza';continue
            evidencias[cid]={'registro':anterior,'descriptor_distinto':anterior['configuraciones']!=limpio['configuraciones'],
                            'intervalo_vigencia_confirmado':False,'fuente':'copia_previa_antes_overlay'}
        clientes[cid]=limpio;reg_cats[cid]=cat_nuevo
    # Catálogo sólo referido por registros aceptados. Conflictos entre catálogos no se fusionan.
    entradas={};conflictos=set()
    for cid,reg in clientes.items():
        ids={x['search_engine_id'] for x in reg['configuraciones']}
        for e in reg_cats[cid]:
            if not isinstance(e,dict) or entero(e.get('id')) not in ids:continue
            key=entero(e['id']);v={'id':str(key),'name':_texto(e.get('name')),'type':e.get('type') if e.get('type') in ('google','bing','yahoo','yandex') else None}
            if e.get('device') in ('mobile','desktop'):v['device']=e['device']
            if key in entradas and entradas[key]!=v:conflictos.add(key)
            entradas[key]=v
    for cid,reg in list(clientes.items()):
        if any(x['search_engine_id'] in conflictos for x in reg['configuraciones']):
            del clientes[cid];evidencias.pop(cid,None);rechazos[cid]='catalogo_conflictivo'
    ids={x['search_engine_id'] for reg in clientes.values() for x in reg['configuraciones']}
    return {'version':'286B.1','catalogo':[entradas[x] for x in sorted(ids)],'clientes':clientes,
            'evidencias_lecturas_anteriores':evidencias,'rechazados':rechazos,'promocionado':False,
            'preparado':fecha_contexto_valida(ahora,ahora)['fecha'],'contexto_historico_confirmado':False}
