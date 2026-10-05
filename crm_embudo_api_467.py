"""467: lector optativo de agregados466. No IO al importar, red ni escrituras.

No se engancha automáticamente. Pins pendientes de raíz y revisión independiente.
El motor privado no se publica literalmente: la respuesta excluye source/IDs/tasas.
"""
import hashlib
import math
import os
from pathlib import Path
import re
from datetime import datetime,timezone
from meta_diaria_api_385 import _leer,_json as _json_base
from operaciones_registros_269 import unica,ErrorRegistro
from embudo_eventos import ETAPAS

APP=Path(__file__).resolve().parent
ENV='RO_EMBUDO_OBSERVADO_467'
SHA='165c83eacd2773ebbc0ee56680b752c97cd2546feed0f483318d750257158359'
MANIFEST_SHA='7f209d41b52f4c3e71010e90b3656b9b65893201a5bde65935fe52894cd8d28a'
VERSION='467.1'
MAX=5_000_000
INCIDENCIAS_MOTOR=frozenset({'evento_invalido','cobertura_invalida','cualificacion_sin_criterio_confirmado',
    'resultado_sin_confirmacion','replay_id','event_id_conflictivo','replay_semantico',
    'posterior_al_corte','lead_sin_recepcion','recepcion_repetida','evento_antes_de_recepcion','event_id_ambito_conflictivo'})
DIAGNOSTICOS=frozenset({'contacto_coleccion_invalida','contacto_identidad_invalida','contacto_payload_invalido',
    'contacto_replay','contacto_conflicto','contacto_no_lead_explicito','contacto_fecha_invalida',
    'contacto_fecha_futura','cita_coleccion_invalida','cita_identidad_invalida','cita_payload_invalido',
    'cita_replay','cita_conflicto','cita_contacto_no_enlazado','cita_fecha_creacion_invalida',
    'cita_fecha_futura','cita_anterior_recibido','fuente_reporta_errores'})
LIMITES=('Copia parcial: sólo eventos observados, sin censo completo.',
    'La cohorte de recibidos y los eventos del periodo son universos distintos.',
    'Cita registra creación de un evento: puede estar cancelado o tener una fecha futura; no acredita asistencia o validez.',
    'Sin tasas, conversión, cualificación automática ni cumplimiento contractual.',
    'Una venta no acredita cobro, margen o rentabilidad; las etapas no se infieren entre sí.')


class ErrorEmbudo(Exception):
    def __init__(self,codigo,texto):self.codigo=codigo;super().__init__(texto)


def _id(v):return isinstance(v,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,100}',v) is not None
def _sha(v):return isinstance(v,str) and re.fullmatch(r'[a-f0-9]{64}',v) is not None
def _n(v):return type(v) is int and 0<=v<=9007199254740991
def _hash(b):return hashlib.sha256(b).hexdigest()


def _json(b):
    d=_json_base(b)
    def revisar(x):
        if type(x) is float and not math.isfinite(x):raise ValueError('no_finito')
        if isinstance(x,dict):
            for v in x.values():revisar(v)
        elif isinstance(x,list):
            for v in x:revisar(v)
    revisar(d)
    return d


def _instante(v):
    if not isinstance(v,str):raise ValueError('instante')
    m=re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(Z|[+-]\d{2}:\d{2})',v)
    if not m:raise ValueError('zona')
    off=m[1]
    if off!='Z':
        h,n=int(off[1:3]),int(off[4:6])
        if n>59 or h>14 or (h==14 and n):raise ValueError('offset')
    return datetime.fromisoformat(v.replace('Z','+00:00')).astimezone(timezone.utc)


def _hash_objeto(d):
    def extra(x):
        if isinstance(x,set):return sorted(x)
        raise TypeError()
    import json
    return _hash(json.dumps(d,sort_keys=True,allow_nan=False,default=extra).encode())


def _ambito(S,rid,vid,cid):
    try:
        if S.E.nucleo_bloqueado:raise ErrorEmbudo(503,'Datos temporalmente bloqueados.')
        if not _id(cid):raise ErrorEmbudo(403,'Cliente fuera del ámbito actual.')
        raw=S.E.crudo;ps=[unica(raw.get('personas'),x) for x in (rid,vid)]
        for p in ps:
            roles=p.get('puestos')
            if not isinstance(roles,list) or not roles or not all(_id(r) for r in roles) or len(set(roles))!=len(roles):raise ErrorEmbudo(403,'Identidad no disponible.')
        cs=[c for c in raw.get('clientes') or [] if isinstance(c,dict) and c.get('id')==cid]
        if len(cs)!=1 or cs[0].get('activo') is False or cs[0].get('estado')=='baja' or S.ACT.es_activo_id(cid) is not True:raise ErrorEmbudo(403,'Cliente fuera del ámbito actual.')
        cps=[S.P.contexto(p,raw) for p in ps]
        if rid!=vid and S.P.ver(ps[0],{'tipo':'ver_como'},cps[0]).get('ok') is not True:raise ErrorEmbudo(403,'Vista no autorizada.')
        gates=[S.ve_alguno(p,['salud-crm']) for p in ps]
        grant=[S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},cp) for p,cp in zip(ps,cps)]
        if any(g not in ('todo','suyo','resumen') for g in gates) or any(g.get('ok') is not True for g in grant):raise ErrorEmbudo(403,'CRM no disponible para esta sesión.')
        return _hash_objeto([rid,vid,cid,raw,cps,S.P.REGLAS,S.E.modulos,gates,grant,S.P.hoy_iso()])
    except ErrorEmbudo:raise
    except (ErrorRegistro,ValueError,TypeError,KeyError,AttributeError,RecursionError):raise ErrorEmbudo(403,'Ámbito no disponible.') from None


def _diagnosticos(d,permitidos=DIAGNOSTICOS):
    if not isinstance(d,dict) or any(k not in permitidos or not _n(v) for k,v in d.items()):raise ValueError('diagnosticos')
    return dict(d)


def _medicion(m,cid,desde,hasta,corte):
    if not isinstance(m,dict) or set(m)!={'version','ventana_recepcion','ventana_eventos','observado_hasta','zona','grupos','incidencias','limites'} or type(m['version']) is not int or m['version']!=1 or m['zona']!='UTC':raise ValueError('medicion')
    for k in ('ventana_recepcion','ventana_eventos'):
        w=m[k]
        if not isinstance(w,dict) or set(w)!={'desde','hasta'} or _instante(w['desde'])!=_instante(desde) or _instante(w['hasta'])!=_instante(hasta):raise ValueError('ventana')
    if _instante(m['observado_hasta'])!=_instante(corte):raise ValueError('corte')
    _diagnosticos(m['incidencias'],INCIDENCIAS_MOTOR)
    if not isinstance(m['limites'],list) or any(not isinstance(x,str) for x in m['limites']):raise ValueError('limites')
    gs=m['grupos']
    if not isinstance(gs,list) or len(gs)!=1:raise ValueError('grupo')
    g=gs[0]
    if not isinstance(g,dict) or set(g)!={'cliente_id','source','cualificacion','cohorte','eventos_periodo'} or g['cliente_id']!=cid or g['source']!='ghl':raise ValueError('cliente')
    q=g['cualificacion']
    if not isinstance(q,dict) or set(q)!={'criterios_observados','criterio_comparable'} or q['criterio_comparable'] is not False or q['criterios_observados']!=[]:raise ValueError('cualificacion')
    co=g['cohorte']
    if not isinstance(co,dict) or set(co)!={'recibidos_observados','estado','etapas'} or not _n(co['recibidos_observados']) or co['estado'] not in ('parcial','desconocido') or not isinstance(co['etapas'],dict) or set(co['etapas'])!=set(ETAPAS):raise ValueError('cohorte')
    n=co['recibidos_observados'];estados={}
    if co['estado']!=('parcial' if n else 'desconocido'):raise ValueError('estado')
    for etapa,v in co['etapas'].items():
        if (not isinstance(v,dict) or set(v)!={'observados','valor','estado','denominador_recibidos','tasa_sobre_recibidos'}
                or not _n(v['observados']) or v['observados']>n or any(v[k] is not None for k in ('valor','denominador_recibidos','tasa_sobre_recibidos'))
                or v['estado']!=('parcial' if v['observados'] else 'desconocido')):raise ValueError('etapa')
        if etapa not in ('recibido','cita') and v['observados']!=0:raise ValueError('etapa_no_acreditada')
        estados[etapa]={'observados':v['observados'],'estado':v['estado']}
    if estados['recibido']['observados']!=n:raise ValueError('recibidos')
    pe=g['eventos_periodo']
    if not isinstance(pe,dict) or set(pe)!=set(ETAPAS):raise ValueError('eventos')
    periodos={}
    for etapa,v in pe.items():
        if (not isinstance(v,dict) or set(v)!={'eventos_observados','leads_unicos_observados','estado'}
                or not _n(v['eventos_observados']) or not _n(v['leads_unicos_observados'])
                or v['leads_unicos_observados']>v['eventos_observados']
                or v['estado']!=('parcial' if v['eventos_observados'] else 'desconocido')):raise ValueError('evento')
        if etapa not in ('recibido','cita') and (v['eventos_observados']!=0 or v['leads_unicos_observados']!=0):raise ValueError('evento_no_acreditado')
        periodos[etapa]=dict(v)
    return {'version':VERSION,'cohorte':{'recibidos_observados':n,'estado':co['estado'],'etapas':estados},
        'eventos_periodo':periodos,'observado_hasta':m['observado_hasta'],
        'ventana_recepcion':dict(m['ventana_recepcion']),'ventana_eventos':dict(m['ventana_eventos']),
        'zona':'UTC','limites':list(LIMITES)}


def _paths():
    return ({'ghl_vivo':APP/'fuentes_crm/_privado/ghl_vivo.json','crm':APP/'data/crm/crm.json','act':APP/'data/verdad/estado_clientes.json'},
        {'adaptador466':APP/'ghl_embudo_observado_466.py','embudo_eventos':APP/'embudo_eventos.py'})


def _marcas(paths):
    out=[]
    for p in paths:
        for node in (p,*p.parents):
            if node.is_symlink():raise ValueError('enlace')
        s=p.lstat();out.append((s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode,s.st_nlink))
    return tuple(out)


def cargar(path):
    p=Path(path)
    if not p.is_absolute() or p.name!='candidato.json' or '..' in p.parts or not _sha(SHA) or not _sha(MANIFEST_SHA):raise ValueError('configuracion')
    sources,codes=_paths();paths=[p,p.parent/'manifest.json',*sources.values(),*codes.values()]
    marcas=_marcas(paths)
    b=_leer(p,MAX,True);mb=_leer(p.parent/'manifest.json',1_000_000,True)
    if _hash(b)!=SHA or _hash(mb)!=MANIFEST_SHA:raise ValueError('anclas')
    m=_json(mb)
    if not isinstance(m,dict) or set(m)!={'version','sha256','codigo_sha256','fuentes_sha256'} or m['version']!='466.1' or m['sha256']!=SHA:raise ValueError('manifest')
    for key,inventario in zip(('fuentes_sha256','codigo_sha256'),(sources,codes)):
        hs=m[key]
        if not isinstance(hs,dict) or set(hs)!=set(inventario):raise ValueError('inventario')
        for k,q in inventario.items():
            if not _sha(hs[k]) or _hash(_leer(q,5_000_000))!=hs[k]:raise ValueError('fuente')
    d=_json(b)
    if not isinstance(d,dict) or set(d)!={'version','hora_fuente','desde','hasta','corte','clientes','sin_pii','cobertura'} or d['version']!='466.1' or d['sin_pii'] is not True or d['cobertura']!='parcial' or not isinstance(d['clientes'],list):raise ValueError('candidato')
    if not (_instante(d['desde'])<=_instante(d['hasta'])<=_instante(d['corte'])) or _instante(d['hora_fuente'])>_instante(d['corte']):raise ValueError('periodo')
    out={};huellas=set()
    for r in d['clientes']:
        if (not isinstance(r,dict) or set(r)!={'cliente_id','subcuenta_huella','medicion','diagnosticos','solo_observados'}
                or not _id(r['cliente_id']) or r['cliente_id'] in out or not _sha(r['subcuenta_huella'])
                or r['subcuenta_huella'] in huellas or r['solo_observados'] is not True):raise ValueError('fila')
        huellas.add(r['subcuenta_huella'])
        cid=r['cliente_id'];out[cid]={'medicion':_medicion(r['medicion'],cid,d['desde'],d['hasta'],d['corte']),
            'diagnosticos':_diagnosticos(r['diagnosticos'])}
    if _marcas(paths)!=marcas:raise ValueError('rotacion')
    return d,out


def listar(S,rid,vid,cid):
    firma=_ambito(S,rid,vid,cid);configured=os.environ.get(ENV);pins=(SHA,MANIFEST_SHA)
    out={'version':VERSION,'estado':'sin_configurar','cliente_id':cid,'medicion':None,
        'diagnosticos':None,'hora_fuente':None,'desde':None,'hasta':None,'corte':None}
    if configured:
        try:
            d,rows=cargar(configured)
            if cid not in rows:raise ValueError('sin_inventario')
            # Las etapas pueden observarse antes del corte, nunca desde una copia futura.
            today=S.P.hoy_iso()
            if not isinstance(today,str) or _instante(d['corte']).date().isoformat()>today:raise ValueError('futuro')
            out.update(estado='copia_observada',**rows[cid],**{k:d[k] for k in ('hora_fuente','desde','hasta','corte')})
            d2,rows2=cargar(configured)
            if d2!=d or rows2!=rows:raise ValueError('rotacion')
        except (ValueError,OSError,TypeError,KeyError,OverflowError,RecursionError):raise ErrorEmbudo(503,'La copia del embudo no supera la validación. No acredita ausencia de eventos.') from None
    if pins!=(SHA,MANIFEST_SHA) or os.environ.get(ENV)!=configured or _ambito(S,rid,vid,cid)!=firma:raise ErrorEmbudo(403,'El acceso o la copia cambió durante la consulta.')
    return out


def enganchar(H,S):
    original=H._api_get
    def get(self,ruta,q,real,persona):
        m=re.fullmatch(r'/api/crm/embudo-observado/([A-Za-z0-9_-]{1,100})',ruta)
        if not m:return original(self,ruta,q,real,persona)
        if q:return self.responder(400,{'error':'Esta consulta no admite parámetros.'})
        try:return self.responder(200,listar(S,real.get('id'),persona.get('id'),m[1]))
        except ErrorEmbudo as e:return self.responder(e.codigo,{'error':str(e)})
    H._api_get=get
