"""Contrato puro para futura captura Meta diaria. No red, llaves, IO ni promoción legacy."""
from datetime import date, datetime
from zoneinfo import ZoneInfo
import re
try:
    from . import meta_mediciones_220 as M
except ImportError:  # ejecución del productor como script, sin importar su bootstrap
    import meta_mediciones_220 as M
VERSION='373.1'
ID=re.compile(r'[A-Za-z0-9_-]{1,120}')

def proyectar(envelope, catalogo):
    """El collector fija request/account; ningún nombre identifica clientes.

    catálogo: lista {cliente_id,cuenta_id,moneda,zona,confirmada:true}.
    envelope: {request:{cuenta_id,level:'campaign',time_increment:1,desde,hasta},
      account:{id,currency,timezone_name},leido_utc:ISO-aware,
      response:{data:[insight...]},paginas_completas:bool}.
    No fila implica desconocido, jamás día/lead cero. La captura sigue parcial.
    """
    if not isinstance(envelope,dict) or not isinstance(catalogo,list):
        raise ValueError('envoltorio_invalido')
    req=envelope.get('request');acc=envelope.get('account');resp=envelope.get('response')
    if not isinstance(req,dict) or not isinstance(acc,dict) or not isinstance(resp,dict):
        raise ValueError('fuentes_ausentes')
    aid=req.get('cuenta_id')
    if not isinstance(aid,str) or not re.fullmatch(r'[1-9][0-9]{0,29}',aid):
        raise ValueError('cuenta_invalida')
    cs=[c for c in catalogo if isinstance(c,dict) and c.get('cuenta_id')==aid]
    if len(cs)!=1:raise ValueError('cuenta_no_unica')
    c=cs[0];cid=c.get('cliente_id')
    if c.get('confirmada') is not True or not isinstance(cid,str) or not ID.fullmatch(cid) or sum(isinstance(x,dict) and x.get('cliente_id')==cid for x in catalogo)!=1:
        raise ValueError('cliente_no_confirmado_unico')
    if acc.get('id')!=aid or acc.get('currency')!=c.get('moneda') or acc.get('timezone_name')!=c.get('zona') or not isinstance(c.get('moneda'),str) or not re.fullmatch('[A-Z]{3}',c['moneda']):
        raise ValueError('contexto_cuenta_discordante')
    try:
        z=ZoneInfo(c['zona']);stamp=datetime.fromisoformat(envelope['leido_utc'])
        if stamp.utcoffset() is None:raise ValueError()
    except (ValueError,TypeError,KeyError):raise ValueError('fecha_zona_invalida') from None
    desde,hasta=M.dia(req.get('desde')),M.dia(req.get('hasta'))
    if req.get('level')!='campaign' or type(req.get('time_increment')) is not int or req['time_increment']!=1 or not desde or not hasta or desde>hasta or hasta>stamp.astimezone(z).date().isoformat():
        raise ValueError('peticion_no_diaria_o_periodo_invalido')
    rows=resp.get('data')
    if not isinstance(rows,list) or len(rows)>100000 or type(envelope.get('paginas_completas')) is not bool:
        raise ValueError('respuesta_sin_cobertura')
    output={};errores=[]
    for raw in rows:
        if not isinstance(raw,dict):errores.append('fila_invalida');continue
        camp=raw.get('campaign_id');d=M.dia(raw.get('date_start'))
        if not isinstance(camp,str) or not re.fullmatch(r'[1-9][0-9]{0,29}',camp) or not d or d!=M.dia(raw.get('date_stop')) or not desde<=d<=hasta or (raw.get('account_id') is not None and raw['account_id']!=aid):
            errores.append('identidad_o_fecha_fila_invalida');continue
        fila=M.fila(raw,stamp.isoformat(),'campaign_diario',cuenta=aid,moneda=c['moneda'])
        fila.update(campaign_id=camp,dia=d)
        fila['medicion'].update(zona=c['zona'],unidad_contador='eventos_meta_no_cualificados',dia_en_curso=d==stamp.astimezone(z).date().isoformat())
        key=(camp,d)
        if key not in output:output[key]=fila
        elif output[key]!=fila:
            output[key]={**fila,**{k:None for k in (*M.CAMPOS,'leads')},'medicion':{**fila['medicion'],'campos_observados':[],'tipo_lead':None,'conflicto':True}}
            errores.append('duplicado_diario_discordante')
    return {'version':VERSION,'cliente_id':cid,'cuenta_id':aid,'moneda':c['moneda'],'zona':c['zona'],'leido_utc':stamp.isoformat(),
            'request':{'level':'campaign','time_increment':1,'desde':desde,'hasta':hasta},
            'cobertura':{'paginas_completas':envelope['paginas_completas'],'completa_leads':False,'tipo':'filas_y_campos_recibidos'},
            'filas_diarias':[output[k] for k in sorted(output)],'errores':sorted(set(errores))}
