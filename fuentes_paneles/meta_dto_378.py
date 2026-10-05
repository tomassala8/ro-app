"""Whitelist de sidecar Meta373; validación de DTO, no permisos/red/IO."""
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import re,math
ID=re.compile(r'[A-Za-z0-9_-]{1,120}')
METRICAS=('gasto','impresiones','alcance','frecuencia','clics','clics_enlace','leads')
TIPOS=('lead','onsite_conversion.lead_grouped','offsite_conversion.fb_pixel_lead','onsite_web_lead')

def sello(v):
    if not isinstance(v,str):return None
    try:
        d=datetime.fromisoformat(v)
        return d if d.utcoffset() is not None else None
    except (ValueError,TypeError):return None

def dia(v):
    if not isinstance(v,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',v):return None
    try:return v if datetime.fromisoformat(v).date().isoformat()==v else None
    except ValueError:return None

def proyectar(sidecar,cache,cliente_id,observado_hasta=None):
    """observado_hasta aware opcional; por defecto reloj UTC de esta proyección.
    No convierte `cache.leido` naive en fecha UTC ni revive su frescura.
    """
    try:
        if not isinstance(sidecar,dict) or not isinstance(cache,dict) or not isinstance(cliente_id,str) or not ID.fullmatch(cliente_id):return None
        md=cache.get('medicion_meta')
        if not isinstance(md,dict) or md.get('version')!='220.1' or md.get('origen')!='api_meta' or md.get('observacion_campos')!='presencia_validada':return None
        aid=cache.get('cuenta');aid=aid.removeprefix('act_') if isinstance(aid,str) else None
        moneda=cache.get('moneda');zona=cache.get('zona_horaria')
        if not aid or not re.fullmatch('[1-9][0-9]{0,29}',aid) or not isinstance(moneda,str) or not re.fullmatch('[A-Z]{3}',moneda) or not isinstance(zona,str):return None
        z=ZoneInfo(zona);leido=sello(sidecar.get('leido_utc'));ahora=sello(observado_hasta) if observado_hasta is not None else datetime.now(timezone.utc)
        if not leido or not ahora or leido>ahora or sidecar.get('version')!='373.1' or sidecar.get('cliente_id')!=cliente_id or sidecar.get('cuenta_id')!=aid or sidecar.get('moneda')!=moneda or sidecar.get('zona')!=zona:return None
        req=sidecar.get('request');cov=sidecar.get('cobertura');rs=sidecar.get('filas_diarias');errs=sidecar.get('errores')
        if not isinstance(req,dict) or not isinstance(cov,dict) or not isinstance(rs,list) or len(rs)>100000 or not isinstance(errs,list):return None
        desde,hasta=dia(req.get('desde')),dia(req.get('hasta'))
        if req.get('level')!='campaign' or type(req.get('time_increment')) is not int or req['time_increment']!=1 or not desde or not hasta or not desde<=hasta<=leido.astimezone(z).date().isoformat():return None
        if type(cov.get('paginas_completas')) is not bool or cov.get('completa_leads') is not False or cov.get('tipo')!='filas_y_campos_recibidos':return None
        if any(e not in {'fila_invalida','identidad_o_fecha_fila_invalida','duplicado_diario_discordante'} for e in errs):return None
        filas=[];keys=set()
        for r in rs:
            if not isinstance(r,dict):return None
            camp,d,m=r.get('campaign_id'),dia(r.get('dia')),r.get('medicion')
            if not isinstance(camp,str) or not re.fullmatch('[1-9][0-9]{0,29}',camp) or not d or not desde<=d<=hasta or (camp,d) in keys or not isinstance(m,dict):return None
            keys.add((camp,d));f={}
            for k in METRICAS:
                if k not in r:return None
                v=r[k]
                if v is not None and (type(v) not in (int,float) or not math.isfinite(v) or v<0 or (k not in ('gasto','frecuencia') and (type(v) is not int or v>9007199254740991))):return None
                f[k]=v
            obs=m.get('campos_observados');kind=m.get('tipo_lead');conf=m.get('conflicto',False)
            if not isinstance(obs,list) or any(k not in METRICAS for k in obs) or len(set(obs))!=len(obs) or set(obs)!={k for k in METRICAS if f[k] is not None}:return None
            if kind is not None and kind not in TIPOS:return None
            if f['leads'] is not None and kind is None:return None
            if type(conf) is not bool or (conf and (obs or kind is not None)):return None
            if m.get('version')!='220.1' or m.get('fuente')!='meta_insights' or m.get('fecha_lectura')!=sidecar['leido_utc'] or m.get('desde')!=d or m.get('hasta')!=d or m.get('nivel')!='campaign_diario' or m.get('periodo_valido') is not True or m.get('cohorte')!='resultados_meta_sin_union_crm_ni_cualificacion_ro' or m.get('cobertura')!='campos_recibidos_no_censo_leads' or m.get('cuenta_id')!=aid or m.get('moneda')!=moneda or m.get('zona')!=zona or m.get('unidad_contador')!='eventos_meta_no_cualificados' or m.get('dia_en_curso') is not (d==leido.astimezone(z).date().isoformat()):return None
            met={'version':'220.1','fuente':'meta_insights','fecha_lectura':sidecar['leido_utc'],'desde':d,'hasta':d,'nivel':'campaign_diario','periodo_valido':True,'cohorte':'resultados_meta_sin_union_crm_ni_cualificacion_ro','campos_observados':[k for k in METRICAS if k in obs],'tipo_lead':kind,'cobertura':'campos_recibidos_no_censo_leads','cuenta_id':aid,'moneda':moneda,'zona':zona,'unidad_contador':'eventos_meta_no_cualificados','dia_en_curso':d==leido.astimezone(z).date().isoformat()}
            if conf:met['conflicto']=True
            filas.append({**f,'campaign_id':camp,'dia':d,'medicion':met})
        return {'version':'373.1','cliente_id':cliente_id,'cuenta_id':aid,'moneda':moneda,'zona':zona,'leido_utc':sidecar['leido_utc'],'request':{'level':'campaign','time_increment':1,'desde':desde,'hasta':hasta},'cobertura':{'paginas_completas':cov['paginas_completas'],'completa_leads':False,'tipo':'filas_y_campos_recibidos'},'filas_diarias':sorted(filas,key=lambda r:(r['campaign_id'],r['dia'])),'errores':sorted(set(errs))}
    except (TypeError,ValueError,KeyError,OverflowError):return None
