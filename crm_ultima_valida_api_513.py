"""513 GET agregado optativo. No hook automático, proveedor, DB ni escrituras."""
import os
from pathlib import Path
from crm_embudo_api_467 import _ambito,ErrorEmbudo,_id,_sha,_hash,_json,_marcas
from meta_diaria_api_385 import _leer
from fuentes_crm.autoridad_ultima_valida_499 import construir_callback
from fuentes_crm import pipeline_ultima_valida_496 as P
from fuentes_crm.ultima_valida_490 import validar_estado,MAX
APP=Path(__file__).resolve().parent
ENV='RO_CRM_ULTIMA_VALIDA_513'
PIN_ENV='RO_CRM_ULTIMA_VALIDA_513_MANIFEST_SHA'
MANIFEST_SHA=''

def _pin():
    value=os.environ.get(PIN_ENV)
    return value if value not in (None,'') else MANIFEST_SHA

class ErrorLectura(Exception):
    def __init__(self,codigo,texto):self.codigo=codigo;super().__init__(texto)

def _fuentes():return {'crm':APP/'data/crm/crm.json','act':APP/'data/verdad/estado_clientes.json'}
def _codigos():return {k:APP/p for k,p in {'api':'crm_ultima_valida_api_513.py','lector':'meta_diaria_api_385.py','conservacion':'fuentes_crm/ultima_valida_490.py','adaptador':'fuentes_crm/adaptadores_ultima_valida_493.py','pipeline':'fuentes_crm/pipeline_ultima_valida_496.py','autoridad':'fuentes_crm/autoridad_ultima_valida_499.py','gate':'crm_embudo_api_467.py'}.items()}

def _pre(S,rid,vid):
    if S.E.nucleo_bloqueado:raise ErrorLectura(503,'Datos temporalmente bloqueados.')
    firms=[]
    for c in S.E.crudo.get('clientes') or []:
        if not isinstance(c,dict) or not _id(c.get('id')):continue
        try:firms.append((c['id'],_ambito(S,rid,vid,c['id'])))
        except ErrorEmbudo as e:
            if e.codigo!=403:raise ErrorLectura(e.codigo,'Ámbito no disponible.') from None
    if not firms:raise ErrorLectura(403,'CRM no disponible para esta sesión.')
    return sorted(firms)

def _cargar(path,pin,validar_scope=None):
    p=Path(path)
    if not p.is_absolute() or p.resolve()!=p or p.name!='estado.json' or APP==p or APP in p.parents or not _sha(pin):raise ValueError('Configuración')
    src,codes=_fuentes(),_codigos();paths=[p,p.parent/'manifest.json',*src.values(),*codes.values()]
    marcas=_marcas(paths);mb=_leer(p.parent/'manifest.json',1_000_000,True)
    if _hash(mb)!=pin:raise ValueError('Ancla')
    m=_json(mb)
    if not isinstance(m,dict) or set(m)!={'version','estado_sha256','fuentes_sha256','codigo_sha256'} or m['version']!='513.1' or not _sha(m['estado_sha256']):raise ValueError('Manifest')
    for field,paths_dict in [('fuentes_sha256',src),('codigo_sha256',codes)]:
        if not isinstance(m[field],dict) or set(m[field])!=set(paths_dict):raise ValueError('Inventario')
        for k,q in paths_dict.items():
            content=_leer(q,MAX)
            if not _sha(m[field][k]) or _hash(content)!=m[field][k]:raise ValueError('Fuente')
            if field=='fuentes_sha256':_json(content)
    # Fuentes/códigos anclados y autoridad actual ANTES del payload privado.
    if validar_scope is not None:validar_scope()
    b=_leer(p,MAX,True)
    if m['estado_sha256']!=_hash(b):raise ValueError('Estado')
    state=_json(b);validar_estado(state)
    if _marcas(paths)!=marcas:raise ValueError('Rotación')
    if validar_scope is not None:validar_scope()
    return state,marcas

def listar(S,rid,vid):
    before=_pre(S,rid,vid);config=os.environ.get(ENV);pin=_pin();pin_config=(os.environ.get(PIN_ENV),MANIFEST_SHA)
    if not config:
        if _pre(S,rid,vid)!=before or os.environ.get(ENV)!=config or _pin()!=pin or (os.environ.get(PIN_ENV),MANIFEST_SHA)!=pin_config:raise ErrorLectura(403,'Ámbito cambió.')
        return {'version':'513.1','estado':'sin_configurar','proyeccion':None}
    try:
        def read_crm():return _json(_leer(_fuentes()['crm'],MAX))
        # Parse actual de autoridad antes de tocar estado privado. Fallo de
        # fuente no se convierte en catálogo vacío ni last-known-good.
        read_crm()
        cb=construir_callback(S,rid,vid,read_crm);scope=P._ambito(cb)
        def gate():
            if P._ambito(cb)!=scope or _pre(S,rid,vid)!=before or os.environ.get(ENV)!=config or _pin()!=pin or (os.environ.get(PIN_ENV),MANIFEST_SHA)!=pin_config:raise PermissionError()
        state,marks=_cargar(config,pin,gate)
        # Corte real aware, nunca final del día ni una hora de proveedor inventada.
        from datetime import datetime,timezone
        dto=P.proyectar(state,scope,datetime.now(timezone.utc).isoformat())
        if P._ambito(cb)!=scope:raise PermissionError()
        state2,marks2=_cargar(config,pin,gate)
        if marks2!=marks or state2!=state:raise ValueError('Rotación')
        if P._ambito(cb)!=scope or _pre(S,rid,vid)!=before:raise PermissionError()
        if os.environ.get(ENV)!=config or _pin()!=pin or (os.environ.get(PIN_ENV),MANIFEST_SHA)!=pin_config:raise PermissionError()
        return {'version':'513.1','estado':'copia_observada','proyeccion':dto}
    except PermissionError:raise ErrorLectura(403,'El acceso cambió durante la consulta.') from None
    except (OSError,ValueError,KeyError,TypeError,AttributeError,RecursionError,OverflowError):raise ErrorLectura(503,'La copia no supera la validación. No acredita cero registros.') from None

def enganchar(H,S):
    original=H._api_get
    def get(self,ruta,q,real,persona):
        if ruta!='/api/crm/ultima-valida':return original(self,ruta,q,real,persona)
        if q:return self.responder(400,{'error':'Esta consulta no admite parámetros.'})
        try:
            dto=listar(S,real.get('id'),persona.get('id'))
            # responder actual fija no-store; no caché de respuestas/documentos.
            return self.responder(200,dto)
        except ErrorLectura as e:return self.responder(e.codigo,{'error':str(e)})
    H._api_get=get
