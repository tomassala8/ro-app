"""Lector opt-in del piloto privado380. Sólo GET, sin red ni escrituras.

Los permisos actuales preceden al IO y vuelven a comprobarse al entregar.
No se engancha automáticamente: revisión independiente previa a la activación.
"""
import hashlib,json,os,re,stat
from pathlib import Path
from fuentes_captacion.mediciones_diarias_384 import resumir
from historial_diario_api_362 import unica,_hash,ErrorHistorial
APP=Path(__file__).resolve().parent
R=APP.parent/'RECUPERACION_CODEX_2026-10-03'
ENV='RO_META_DIARIA_385'
SHA='f7b06c007384dfdf3bbc5b031ed3ea5e2c62bbe53416b7c50c4b3fedc94dfc9c'
MANIFEST_SHA='cf221c0cc350fb5d8f0bc9c936daa0246b4dbe78699aa9b51c5ef400538518e5'
VERSION='385.1'
class ErrorMeta(Exception):
 def __init__(self,codigo,texto):self.codigo=codigo;super().__init__(texto)

def _ambito(S,rid,vid,cid):
 try:
  if S.E.nucleo_bloqueado:raise ErrorMeta(503,'Permisos no disponibles.')
  raw=S.E.crudo;ps=[unica(raw.get('personas'),x) for x in (rid,vid)]
  xs=[c for c in raw.get('clientes',[]) if isinstance(c,dict) and c.get('id')==cid]
  if len(xs)!=1 or xs[0].get('activo') is False or S.ACT.es_activo_id(cid) is not True:raise ErrorMeta(403,'Cliente fuera del ámbito actual.')
  cps=[S.P.contexto(p,raw) for p in ps]
  if rid!=vid and S.P.ver(ps[0],{'tipo':'ver_como'},cps[0]).get('ok') is not True:raise ErrorMeta(403,'Vista no autorizada.')
  if any(not S.ve_alguno(p,['captacion']) or S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},cp).get('ok') is not True for p,cp in zip(ps,cps)):raise ErrorMeta(403,'Captación no disponible para esta sesión.')
  inv=all(S.P.ver(p,{'tipo':'inversion','cliente_id':cid},cp).get('ok') is True for p,cp in zip(ps,cps))
  return inv,_hash([raw,cps,cid,inv])
 except ErrorHistorial as e:raise ErrorMeta(e.codigo,str(e))
 except (KeyError,TypeError,ValueError,AttributeError):raise ErrorMeta(403,'Ámbito no acreditado.')

def _leer(path,limit,privado=False):
 # La copia privada exige todos los ancestros reales y modo700 del depósito.
 p=Path(path)
 if not p.is_absolute() or '..' in p.parts:raise ValueError('Ruta')
 fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
 try:
  for part in p.parts[1:-1]:
   nf=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=nf
  a=os.fstat(fd)
  if privado and (stat.S_IMODE(a.st_mode)!=0o700 or a.st_uid!=os.getuid()):raise ValueError('Depósito')
  leaf=os.open(p.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
  with os.fdopen(leaf,'rb') as f:
   a=os.fstat(f.fileno())
   if not stat.S_ISREG(a.st_mode) or a.st_nlink!=1 or not 0<a.st_size<=limit or (privado and (a.st_uid!=os.getuid() or stat.S_IMODE(a.st_mode)!=0o600)):raise ValueError('Archivo')
   b=f.read(limit+1);z=os.fstat(f.fileno())
   if (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)!=(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns,z.st_ctime_ns) or len(b)!=a.st_size:raise ValueError('Cambio')
   return b
 finally:os.close(fd)

def _json(b):
 def pares(xs):
  d={}
  for k,v in xs:
   if k in d:raise ValueError('Duplicado')
   d[k]=v
  return d
 return json.loads(b,object_pairs_hook=pares,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Número')))

def cargar(path,cid):
 p=Path(path)
 if p.name!='candidato.json':raise ValueError('Nombre')
 b=_leer(p,10_000_000,True);mb=_leer(p.parent/'manifest.json',1_000_000,True);m=_json(mb)
 if hashlib.sha256(mb).hexdigest()!=MANIFEST_SHA:raise ValueError('Manifest no anclado')
 if hashlib.sha256(b).hexdigest()!=SHA or m.get('sha256')!=SHA or m.get('version')!='380.1' or m.get('solo_get') is not True or m.get('promovido') is not False or m.get('campos_personales_solicitados') is not False:raise ValueError('Copia no anclada')
 d=_json(b)
 if d.get('cliente_id')!=cid:raise ValueError('Cliente')
 catalogo={p.name:p for p in (APP/'data/clientes').glob('*.json')}
 paths={'cliente':APP/'data/clientes'/(cid+'.json'),'meta_cache':APP/'fuentes_paneles/_cache/meta'/(cid+'.json'),'act':APP/'data/verdad/estado_clientes.json',**{'catalogo:'+n:p for n,p in catalogo.items()}}
 hs=m.get('fuentes_sha256')
 if not isinstance(hs,dict) or set(hs)!=set(paths):raise ValueError('Inventario')
 for k,p in paths.items():
  if hashlib.sha256(_leer(p,10_000_000)).hexdigest()!=hs[k]:raise ValueError('Fuente cambió')
 codes={'colector380':R/'capturar_meta_diaria_380.py','contrato373':APP/'fuentes_paneles/meta_envelope_373.py','adaptador220':APP/'fuentes_paneles/meta_mediciones_220.py'}
 hs=m.get('codigo_sha256')
 if not isinstance(hs,dict) or set(hs)!=set(codes):raise ValueError('Código no anclado')
 for k,p in codes.items():
  if hashlib.sha256(_leer(p,1_000_000)).hexdigest()!=hs[k]:raise ValueError('Código cambió')
 return d,hashlib.sha256(mb).hexdigest()

def listar(S,rid,vid,cid,path=None):
 inv,firma=_ambito(S,rid,vid,cid);configured=os.environ.get(ENV);p=path if path is not None else configured
 out=None;manifest=None;pins=(SHA,MANIFEST_SHA)
 if p:
  try:
   d,manifest=cargar(p,cid)
   ctx={'cuenta':'act_'+d['cuenta_id'],'moneda':d['moneda'],'zona_horaria':d['zona'],'medicion_meta':{'version':'220.1','origen':'api_meta','observacion_campos':'presencia_validada'}}
   out=resumir(d,ctx,cid)
   if out is None:raise ValueError('Descriptor')
   _,posterior=cargar(p,cid)
   if posterior!=manifest:raise ValueError('Manifest cambió')
  except (ValueError,OSError,KeyError,TypeError,OverflowError,RecursionError):raise ErrorMeta(503,'La copia diaria no supera la validación; no acredita cero leads.')
 inv2,f2=_ambito(S,rid,vid,cid)
 if (inv,firma)!=(inv2,f2) or pins!=(SHA,MANIFEST_SHA) or (path is None and os.environ.get(ENV)!=configured):raise ErrorMeta(403,'El acceso cambió durante la consulta.')
 if out and not inv:
  out={k:v for k,v in out.items() if not k.startswith(('gasto','cpl')) and k!='moneda'}
  out['dias']=[{k:v for k,v in d.items() if not k.startswith(('gasto','cpl'))} for d in out['dias']]
 return {'version':VERSION,'estado':'copia_observada' if out else 'sin_dato','cliente_id':cid,'medicion':out}

def enganchar(H,S):
 original=H._api_get
 def get(self,ruta,q,real,persona):
  m=re.fullmatch(r'/api/paid/mediciones-diarias/([A-Za-z0-9_-]{1,100})',ruta)
  if not m:return original(self,ruta,q,real,persona)
  if q:return self.responder(400,{'error':'Esta consulta no admite parámetros.'})
  try:return self.responder(200,listar(S,real.get('id'),persona.get('id'),m.group(1)))
  except ErrorMeta as e:return self.responder(e.codigo,{'error':str(e)})
 H._api_get=get
