"""GET de la caché privada PageSpeed: no dispara mediciones ni permite URLs arbitrarias."""
import hashlib
import json
import os
from pathlib import Path
import stat
from .cliente import numero, fecha, url_publica

LIMITE = 128 * 1024

def _leer(carpeta, cid, estrategia):
    carpeta=Path(carpeta)
    if any(p.is_symlink() for p in (carpeta,*carpeta.parents)):raise ValueError('cache_insegura')
    if not carpeta.exists():return None
    if not carpeta.is_dir() or carpeta.stat().st_mode & 0o077:raise ValueError('cache_insegura')
    key=hashlib.sha256((cid+'\0'+estrategia).encode()).hexdigest()+'.json'
    dfd=os.open(carpeta,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        try:fd=os.open(key,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=dfd)
        except FileNotFoundError:return None
        try:
            st=os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or st.st_mode&0o077 or st.st_size>LIMITE:raise ValueError('cache_insegura')
            with os.fdopen(fd,'rb',closefd=False) as f:contenido=f.read(LIMITE+1)
            if len(contenido)>LIMITE:raise ValueError('cache_demasiado_grande')
            doc=json.loads(contenido)
            if not isinstance(doc,dict) or doc.get('cliente_id')!=cid or doc.get('estrategia')!=estrategia:raise ValueError('cache_identidad_no_coincide')
            return doc
        finally:os.close(fd)
    finally:os.close(dfd)


def _experiencia(v):
    medidas=v.get('metricas') if isinstance(v,dict) else None
    medidas=medidas if isinstance(medidas,dict) else {}
    out={k:numero(medidas.get(k)) for k in ('lcp_ms','fcp_ms','inp_ms','cls_centésimas')}
    return {'estado':'medido' if any(v is not None for v in out.values()) else 'sin_dato','metricas':out,'estadistico':'percentil_75'}


def proyectar(doc, cid, estrategia, web):
    out={'estrategia':estrategia,'estado':'pendiente','ultimo_intento':None,'ultimo_intento_ok':None,'error':None,'http':None,'medicion':None}
    if doc is None:return out
    if not isinstance(doc,dict) or doc.get('cliente_id')!=cid or doc.get('estrategia')!=estrategia:raise ValueError('cache_identidad_no_coincide')
    error=doc.get('error')
    out.update(ultimo_intento=fecha(doc.get('ultimo_intento')),
               ultimo_intento_ok=doc.get('ultimo_intento_ok') if type(doc.get('ultimo_intento_ok')) is bool else None,
               error=error if error in ('sin_autorizacion','cuota_o_limite','proveedor_error','red_o_timeout','respuesta_no_utilizable') else None,
               http=doc.get('http') if type(doc.get('http')) is int and 100<=doc['http']<=599 else None)
    out['estado']='lectura_fallida' if out['ultimo_intento_ok'] is False else 'pendiente'
    m=doc.get('medicion')
    if not isinstance(m,dict):return out
    esperado=url_publica(web)
    if url_publica(m.get('url_solicitada'))!=esperado or m.get('estrategia')!=estrategia:raise ValueError('cache_url_no_coincide')
    dia=fecha(m.get('fecha_medicion'));lab=m.get('laboratorio') or {}
    score=numero(lab.get('performance')) if isinstance(lab,dict) else None
    if dia is None or score is None or score>100:raise ValueError('cache_medicion_invalida')
    final=url_publica(m.get('url_final'))
    # No publicar URLs de otro dominio desde una caché alterada/redirección ajena.
    from urllib.parse import urlsplit
    mismo=urlsplit(final).hostname.removeprefix('www.')==urlsplit(esperado).hostname.removeprefix('www.')
    metrics=lab.get('metricas') if isinstance(lab.get('metricas'),dict) else {}
    out['medicion']={'fuente':'Google PageSpeed Insights v5','fecha_medicion':dia,'estrategia':estrategia,
        'url_solicitada':esperado,'url_final':final if mismo else None,'redireccion_otro_dominio':not mismo,
        'laboratorio':{'performance':score,'metricas':{k:numero(metrics.get(k)) for k in ('fcp_ms','lcp_ms','tbt_ms','cls','speed_index_ms')}},
        'campo_url':_experiencia(m.get('campo_url')),'campo_origen':_experiencia(m.get('campo_origen')),
        'cobertura':'Una URL y estrategia. Laboratorio y experiencia real separados; no acredita toda la web.'}
    if out['ultimo_intento_ok'] is True:out['estado']='medido'
    else:out['medicion_anterior']=True
    return out


def leer_cache(carpeta,cid,web):
    out={}
    for estrategia in ('mobile','desktop'):
        try:out[estrategia]=proyectar(_leer(carpeta,cid,estrategia),cid,estrategia,web)
        except (ValueError,TypeError,AttributeError,OSError):out[estrategia]={'estrategia':estrategia,'estado':'cache_no_utilizable','medicion':None,'error':'cache_no_utilizable'}
    return {'cliente_id':cid,'solo_lectura':True,'estrategias':out,
            'actualizacion':'Piloto manual; actualización periódica pendiente de clave/cuota y programación.'}


def enganchar(Manejador,S):
    original=Manejador._api_get
    def get(self,ruta,q,real,persona):
        if ruta!='/api/pagespeed/cache':return original(self,ruta,q,real,persona)
        if S.E.nucleo_bloqueado:return self.responder(503,{'error':'Datos temporalmente bloqueados.'})
        if set(q)-{'cliente_id','yo','como'} or len(q.get('cliente_id') or [])!=1:return self.responder(400,{'error':'Selecciona un único cliente.'})
        cid=q['cliente_id'][0]
        if not isinstance(cid,str) or not S.ACT.es_activo_id(cid):return self.responder(404,{'error':'Cliente activo no encontrado.'})
        for p in (real,persona):
            if not S.ve_alguno(p,['seo-web']):return self.responder(403,{'error':'Esta fuente no corresponde a tu puesto.'})
            cp=S.P.contexto(p,S.E.crudo)
            if not S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},cp)['ok']:return self.responder(403,{'error':'No puedes consultar este cliente.'})
        cliente=next((c for c in S.E.crudo.get('clientes',[]) if c.get('id')==cid),None)
        if not cliente:return self.responder(404,{'error':'Cliente no encontrado.'})
        return self.responder(200,leer_cache(Path(S.AQUI)/'fuentes_pagespeed/_privado',cid,cliente.get('web')))
    Manejador._api_get=get
