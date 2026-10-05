"""Ventanas Paid desde filas diarias220 autorizadas; no usa contadores agregados legacy."""
from datetime import date,timedelta
from math import fsum,isfinite
import re
from meta_informe_291 import medir,numero


def ventana(k,periodo,hoy):
    unknown={'leads':None,'gasto':None,'tipo_evento':None,'estado':'sin_medicion_compatible'}
    if not isinstance(k,dict) or not isinstance(periodo,(list,tuple)) or len(periodo)!=2:return unknown
    try:
        a,b=(date.fromisoformat(x) for x in periodo);now=date.fromisoformat(hoy)
        if not 0<=(b-a).days<=365 or b>=now:return unknown
    except (ValueError,TypeError):return unknown
    fechas=[str(a+timedelta(days=i)) for i in range((b-a).days+1)]
    rows=k.get('serie');cuenta=k.get('cuenta_meta')
    if not isinstance(rows,list) or not isinstance(cuenta,dict):return unknown
    fuente={'cuenta':{'id':cuenta.get('cuenta_id') or cuenta.get('id')},'moneda':cuenta.get('moneda'),'error':cuenta.get('error'),'errores':cuenta.get('errores')}
    cid=fuente['cuenta']['id'];normal=str(cid).removeprefix('act_') if type(cid) in (str,int) else ''
    if not re.fullmatch(r'[1-9][0-9]{0,39}',normal):return unknown
    if k.get('error') or k.get('errores_lectura') or fuente['error'] or fuente['errores']:return unknown
    ls=[];gs=[];tipos=set()
    for d in fechas:
        xs=[f for f in rows if isinstance(f,dict) and f.get('d')==d]
        if len(xs)!=1:return unknown
        f=xs[0];m=f.get('medicion');m=m if isinstance(m,dict) else {}
        x=medir({'leads':f.get('leads_meta'),'gasto':f.get('gasto_meta'),'medicion':m,'error':f.get('error'),'errores':f.get('errores')},fuente,{'desde':d,'hasta':d},hoy,k)
        if not x['typed']:return unknown
        try:
            fecha=date.fromisoformat(m['fecha_lectura'][:10])
            if (now-fecha).days>2:return unknown
        except (KeyError,TypeError,ValueError):return unknown
        ls.append(x['leads']);tipos.add(m.get('tipo_lead'))
        gs.append(numero(f.get('gasto_meta')) if isinstance(m.get('campos_observados'),list) and 'gasto' in m['campos_observados'] and m.get('moneda')==fuente['moneda'] and isinstance(fuente['moneda'],str) and re.fullmatch('[A-Z]{3}',fuente['moneda']) else None)
    leads=sum(ls) if all(x is not None for x in ls) and len(tipos)==1 else None
    if leads is not None and leads>9007199254740991:leads=None
    try:gasto=fsum(gs) if all(x is not None for x in gs) else None
    except OverflowError:gasto=None
    if gasto is not None and not isfinite(gasto):gasto=None
    return {'leads':leads,'gasto':gasto,'tipo_evento':next(iter(tipos)) if leads is not None else None,'estado':'observado_parcial'}
