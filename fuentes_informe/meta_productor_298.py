"""Lectura Meta de informes: callback acotado y normalización; sin IO al importar."""
from copy import deepcopy
from datetime import date,timedelta
import re,json
from fuentes_paneles import meta_mediciones_220 as M


def paginas(pedir, path, **params):
    filas=[];vistos=set()
    for _ in range(60):
        r=pedir(path,**params)
        if not isinstance(r,dict) or r.get('_error') or not isinstance(r.get('data'),list):
            return filas,'lectura_meta_incompleta'
        if any(not isinstance(x,dict) for x in r['data']) or len(filas)+len(r['data'])>30000:
            return filas,'filas_meta_invalidas'
        filas.extend(r['data'])
        paging=r.get('paging') or {}
        if not isinstance(paging,dict):return filas,'paginacion_meta_invalida'
        if not paging.get('next'):return filas,None
        # Nunca abrir la URL next aportada por la respuesta: mantener origen/ruta solicitados.
        after=(paging.get('cursors') or {}).get('after') if isinstance(paging.get('cursors') or {},dict) else None
        if not isinstance(after,str) or not 1<=len(after)<=512 or any(ord(c)<33 or ord(c)>126 for c in after) or after in vistos:
            return filas,'paginacion_meta_incompleta'
        vistos.add(after);params={**params,'after':after}
    return filas,'paginacion_meta_incompleta'


def leer(pedir, cuenta, periodos, fecha, sanear=lambda x:x):
    if not isinstance(fecha,str) or not M.dia(fecha[:10]):return {'_error':'fecha_meta_invalida'}
    periodos=[p for p in periodos if isinstance(p,dict)] if isinstance(periodos,(list,tuple)) else []
    context=M.contexto_cuenta(cuenta,None)
    if context['cuenta_id'] is None:return {'_error':'cuenta_meta_invalida'}
    info=pedir('/'+cuenta,fields='currency')
    moneda=M.contexto_cuenta(cuenta,info.get('currency') if isinstance(info,dict) and not info.get('_error') else None)['moneda']
    errores=[] if moneda else ['moneda_meta_sin_confirmar']
    rangos=set()
    for p in periodos:
        if not isinstance(p,dict):continue
        ant=p.get('anterior');ant=ant if isinstance(ant,(list,tuple)) and len(ant)==2 else (None,None)
        for a,b in ((p.get('desde'),p.get('hasta')),ant):
            if M.dia(a) and M.dia(b) and a<=b<=fecha[:10]:rangos.add((a,b))
    if not rangos:return {'_error':'periodos_meta_invalidos'}
    path='/'+cuenta+'/insights'
    rows,err=paginas(pedir,path,level='account',fields='spend,impressions,reach,frequency,actions,clicks',time_ranges=json.dumps([{'since':a,'until':b}for a,b in sorted(rangos)]),limit=100)
    if err:errores.append(err)
    tot={}
    for x in rows:
        row=M.fila(x,fecha,'account',cuenta,moneda);m=row['medicion']
        if (m['desde'],m['hasta']) not in rangos:errores.append('periodo_meta_fuera_rango');continue
        k=m['desde']+'|'+m['hasta']
        if k in tot and tot[k]!=row:
            row={k:None for k in (*M.CAMPOS,'leads')}|{'medicion':{**m,'campos_observados':[]},'errores':['periodo_meta_duplicado_discordante']}
            errores.append('periodo_meta_duplicado_discordante')
        tot[k]=row
    desde=min(a for a,b in rangos);hasta=max(b for a,b in rangos)
    daily,err=paginas(pedir,path,level='account',fields='spend,actions',time_increment=1,time_range=json.dumps({'since':desde,'until':hasta}),limit=500)
    if err:errores.append(err)
    serie={};mediciones={}
    for x in daily:
        row=M.fila(x,fecha,'account_diario',cuenta,moneda);m=row['medicion'];d=m['desde']
        if not m['periodo_valido'] or d!=m['hasta'] or not desde<=d<=hasta:errores.append('dia_meta_fuera_rango');continue
        v=[row['gasto'],row['leads']]
        if d in serie and serie[d]!=v:v=[None,None];errores.append('dia_meta_duplicado_discordante');m={**m,'campos_observados':[]}
        serie[d]=v;mediciones[d]=m
    camp={}
    for p in periodos:
        if (p.get('desde'),p.get('hasta'))not in rangos:continue
        rows,err=paginas(pedir,path,level='adset',fields='adset_id,campaign_name,adset_name,spend,impressions,frequency,actions',time_range=json.dumps({'since':p['desde'],'until':p['hasta']}),limit=200)
        if err:errores.append(err)
        items={};conflictos=set()
        for x in rows:
            row=M.fila(x,fecha,'adset',cuenta,moneda);m=row['medicion'];aid=x.get('adset_id')
            if not isinstance(aid,str) or not re.fullmatch(r'[1-9][0-9]{0,29}',aid) or (m['desde'],m['hasta'])!=(p['desde'],p['hasta']):errores.append('conjunto_meta_sin_identidad_periodo');continue
            item={**row,'id':aid,'campana':sanear(x.get('campaign_name')),'conjunto':sanear(x.get('adset_name'))}
            if aid in items and items[aid]!=item:conflictos.add(aid);errores.append('conjunto_meta_duplicado_discordante')
            items[aid]=item
        camp[p['id']]=[v for k,v in items.items() if k not in conflictos]
    return {'totales':tot,'serie':serie,'serie_mediciones':mediciones,'conjuntos':camp,'moneda':moneda,'cuenta_id':context['cuenta_id'],'errores':sorted(set(errores)),'medicion_meta':M.descriptor(fecha)}


def periodo(m,p):
    if not isinstance(m,dict) or m.get('_error'):return {'_error':m.get('_error')}if isinstance(m,dict)else None
    def total(a,b):
        row=deepcopy((m.get('totales') or {}).get(a+'|'+b))
        if not isinstance(row,dict):return None
        row.pop('cpl',None) # El consumidor291 calcula sólo con contrato cuenta/moneda/evento.
        if not isinstance(row.get('medicion'),dict):
            for k in (*M.CAMPOS,'leads'):
                n=M.numero(row.get(k),entero=k not in ('gasto','frecuencia'));row[k]=n if n is not None and n>0 else None
            row['medicion']={'version':M.VERSION,'fuente':'cache_legacy','cobertura':'presencia_original_no_acreditada'}
        return row
    try:a,b=date.fromisoformat(p['desde']),date.fromisoformat(p['hasta'])
    except (ValueError,KeyError,TypeError):return None
    if a>b or (b-a).days>3660:return None
    dias=[]
    while a<=b:
        v=(m.get('serie')or{}).get(str(a));v=v if isinstance(v,list)and len(v)==2 else [None,None]
        md=(m.get('serie_mediciones')or{}).get(str(a))
        typed=isinstance(md,dict) and md.get('version')==M.VERSION and md.get('fuente')=='meta_insights' and md.get('nivel')=='account_diario' and md.get('periodo_valido')is True and md.get('desde')==str(a)==md.get('hasta') and md.get('cuenta_id')==m.get('cuenta_id') and bool(m.get('cuenta_id')) and md.get('cohorte')==M.COHORTE
        ns=[M.numero(v[0]),M.numero(v[1],True)]
        if not typed:ns=[n if n is not None and n>0 else None for n in ns]
        dias.append([str(a),*ns]);a+=timedelta(days=1)
    return {'actual':total(p['desde'],p['hasta']),'anterior':total(*p['anterior']),'serie':dias,'conjuntos':sorted(deepcopy((m.get('conjuntos')or{}).get(p['id'],[])),key=lambda x:-(M.numero(x.get('gasto')) or 0)), 'errores':deepcopy(m.get('errores')or[])}


def estado_fuente(m):
    if not m:return 'sin_conectar'
    if m.get('_error'):return 'rota'
    if m.get('errores'):return 'dato'
    a=m.get('actual') or {};md=a.get('medicion') or {}
    n=M.numero(a.get('gasto'))
    observado=md.get('version')==M.VERSION and md.get('fuente')=='meta_insights' and md.get('periodo_valido')is True and 'gasto'in(md.get('campos_observados')or[])
    return ('a_cero' if n==0 else 'bien') if observado and n is not None else 'dato'


def fuente(m, cache, hora, cuenta, nota):
    cache=cache if isinstance(cache,dict)else {}
    out={'estado':estado_fuente(m),'hora':hora,'cuenta':deepcopy(cuenta),'moneda':M.contexto_cuenta(cache.get('cuenta_id'),cache.get('moneda'))['moneda'],'nota':nota}
    if isinstance(m,dict)and m.get('errores'):out['errores']=['lectura_meta_por_contrastar']
    return out
