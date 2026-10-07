"""362: lector opt-in del candidato359. Sin IO al importar ni escritura/proveedores."""
import collections,copy,datetime as dt,hashlib,json,math,os,re,stat
from pathlib import Path
from zoneinfo import ZoneInfo
RUTA='/api/horas/historial-diario'
ENV='RO_HISTORIAL_DIARIO_359'
SHA='21abf5db866bfd0ed9805b61bf686a625f613d37d21ce80095ef998f209f6280'
MANIFEST_SHA='7f1b34316400ed5af91625b37ee077b727e3bf79f97e0e287c2494e1e26a98f3'
VERSION='362.1'
class ErrorHistorial(Exception):
 def __init__(self,codigo,texto):self.codigo=codigo;super().__init__(texto)
def unica(filas,pid):
 if not _id(pid) or not isinstance(filas,list):raise ErrorHistorial(403,'Identidad inválida.')
 xs=[p for p in filas if isinstance(p,dict) and p.get('id')==pid]
 if len(xs)!=1 or xs[0].get('estado')!='activo' or xs[0].get('activo') is False:raise ErrorHistorial(403,'Identidad activa no inequívoca.')
 return xs[0]
def _id(v):return isinstance(v,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,100}',v) is not None
def _hash(v):
 def extra(x):
  if isinstance(x,set):return sorted(x)
  raise TypeError('Ámbito no serializable')
 return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=extra).encode()).hexdigest()
def _fecha(v):
 if not isinstance(v,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',v):raise ValueError('Fecha')
 return dt.date.fromisoformat(v)
def _instante(v):
 if not isinstance(v,str):raise ValueError('Instante')
 d=dt.datetime.fromisoformat(v.replace('Z','+00:00'))
 if d.tzinfo is None or d.utcoffset() is None or abs(d.utcoffset())>dt.timedelta(hours=14):raise ValueError('Zona')
 return d

def _ambito(S,rid,vid):
 try:
  if S.E.nucleo_bloqueado:raise ErrorHistorial(503,'Fuente de permisos no disponible.')
  crudo=S.E.crudo;catalogo=crudo.get('personas')
  if not isinstance(catalogo,list):raise ErrorHistorial(403,'Catálogo no disponible.')
  ps=[unica(catalogo,x) for x in (rid,vid)]
  niveles=[S.ve_alguno(p,['horas']) for p in ps]
  if any(n not in ('resumen','suyo','todo') for n in niveles):raise ErrorHistorial(403,'Horas no disponibles para esta sesión.')
  cps=[S.P.contexto(p,crudo) for p in ps]
  if rid!=vid and S.P.ver(ps[0],{'tipo':'ver_como'},cps[0]).get('ok') is not True:raise ErrorHistorial(403,'Vista de otra persona no autorizada.')
  counts=collections.Counter(p.get('id') for p in catalogo if isinstance(p,dict) and isinstance(p.get('id'),str))
  permitidas=[]
  for p in catalogo:
   if not isinstance(p,dict) or not _id(p.get('id')) or counts[p['id']]!=1 or p.get('estado')!='activo' or p.get('activo') is False:continue
   if all(S.P.ver(a,{'tipo':'horas_persona','persona_id':p['id']},cp).get('ok') is True for a,cp in zip(ps,cps)):permitidas.append(p['id'])
  # Huella interna únicamente: contexto/reglas/módulos nunca salen en el DTO.
  identidades=[{k:p.get(k) for k in ('id','estado','activo','puestos','jefe_id','zona','zona_a_confirmar')} for p in catalogo if isinstance(p,dict)]
  firma=_hash([rid,vid,niveles,cps,identidades,sorted(permitidas),getattr(S.P,'REGLAS',None),getattr(S.E,'modulos',None),S.P.hoy_iso()])
  return sorted(permitidas),firma
 except (TypeError,ValueError,KeyError,AttributeError):raise ErrorHistorial(403,'No se puede acreditar el ámbito de horas.')

def cargar(path):
 p=Path(path)
 if not p.is_absolute() or p.name!='candidato.json' or '..' in p.parts:raise ValueError('Ruta')
 # Traverse directorios sin seguir enlaces. Ancestros generales no se modifican.
 fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
 try:
  for part in p.parts[1:-1]:
   nf=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=nf
  st=os.fstat(fd)
  if stat.S_IMODE(st.st_mode)!=0o700 or st.st_uid!=os.getuid():raise ValueError('Depósito privado')
  identidad=(st.st_dev,st.st_ino)
  def leer(name,pin,limite):
   ff=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
   try:
    a=os.fstat(ff)
    if not stat.S_ISREG(a.st_mode) or a.st_nlink!=1 or a.st_uid!=os.getuid() or stat.S_IMODE(a.st_mode)!=0o600 or not 0<a.st_size<=limite:raise ValueError('Archivo privado')
    chunks=[];n=0
    while n<=limite:
     b=os.read(ff,min(65536,limite+1-n))
     if not b:break
     chunks.append(b);n+=len(b)
    raw=b''.join(chunks);z=os.fstat(ff)
    if len(raw)!=a.st_size or (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns,a.st_mode,a.st_nlink)!=(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns,z.st_ctime_ns,z.st_mode,z.st_nlink):raise ValueError('Archivo cambió')
    if hashlib.sha256(raw).hexdigest()!=pin:raise ValueError('SHA')
    def no_const(x):raise ValueError('JSON no finito')
    def pares(xs):
     out={}
     for k,v in xs:
      if k in out:raise ValueError('Clave JSON duplicada')
      out[k]=v
     return out
    return json.loads(raw,parse_constant=no_const,object_pairs_hook=pares)
   finally:os.close(ff)
  manifest=leer('manifest.json',MANIFEST_SHA,2_000_000);doc=leer('candidato.json',SHA,4_000_000)
  if not isinstance(manifest,dict) or manifest.get('version')!='359.1' or manifest.get('output_sha256')!=SHA or manifest.get('sin_promover') is not True or manifest.get('proveedores_consultados')!=0 or manifest.get('dias_por_persona')!=90:raise ValueError('Manifest')
  # Segunda resolución de ruta comprueba que el depósito anclado sigue siendo el actual.
  check=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
  try:
   for part in p.parts[1:-1]:
    nf=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=check);os.close(check);check=nf
   final=os.fstat(check)
   if (final.st_dev,final.st_ino)!=identidad or stat.S_IMODE(final.st_mode)!=0o700:raise ValueError('Depósito cambió')
  finally:os.close(check)
  return doc,manifest
 finally:os.close(fd)

def proyectar(doc,permitidas,ahora,hoy):
 if not isinstance(doc,dict) or doc.get('version')!='359.1' or doc.get('cobertura')!='parcial' or doc.get('unidad')!='duracion_personal_observada_atribuida_al_inicio' or doc.get('clientes_en_salida') is not False or doc.get('sin_promover') is not True or not isinstance(doc.get('personas'),list):raise ValueError('Contrato')
 corte=_fecha(doc.get('hoy'));fecha_hoy=_fecha(hoy)
 if corte>fecha_hoy or corte>ahora.astimezone(ZoneInfo('Europe/Madrid')).date():raise ValueError('Corte futuro')
 seen=set();out=[]
 for row in doc['personas']:
  pid=row.get('persona_id') if isinstance(row,dict) else None
  if not _id(pid) or pid in seen:raise ValueError('Identidad')
  seen.add(pid);s=row.get('historial_diario_359')
  if not isinstance(s,dict) or s.get('version')!='359.1' or s.get('fuente')!='ClickUp entradas' or s.get('cobertura')!='parcial' or s.get('zona_confirmada') is not True or s.get('corte_fecha')!=doc['hoy'] or s.get('criterio_corte')!='anterior_fecha_referencia' or s.get('atribucion')!='inicio' or s.get('duracion_cerrada_confirmada') is not False or s.get('sin_registros_no_equivale_a_cero') is not True:raise ValueError('Serie')
  zona=s.get('zona')
  if not isinstance(zona,str):raise ValueError('Zona')
  ZoneInfo(zona);fuente=_instante(s.get('fecha_fuente_utc'))
  if fuente.utcoffset()!=dt.timedelta(0) or fuente>ahora or fuente.astimezone(ZoneInfo('Europe/Madrid')).date()>corte:raise ValueError('Fuente futura')
  desde=corte-dt.timedelta(days=90);hasta=corte-dt.timedelta(days=1)
  if _fecha(s.get('desde'))!=desde or _fecha(s.get('hasta'))!=hasta or not isinstance(s.get('dias'),list) or len(s['dias'])!=90:raise ValueError('Ventana')
  dias=[]
  for i,d in enumerate(s['dias']):
   if not isinstance(d,dict) or _fecha(d.get('fecha'))!=desde+dt.timedelta(days=i):raise ValueError('Día repetido/ventana')
   h=d.get('horas');n=d.get('entradas');estado=d.get('estado')
   if estado=='observado':
    if type(h) not in (int,float) or not math.isfinite(h) or h<0 or type(n) is not int or n<1:raise ValueError('Observación')
   elif estado!='sin_dato' or h is not None or n is not None:raise ValueError('Desconocido')
   dias.append({'fecha':d['fecha'],'horas':h,'entradas':n,'estado':estado})
  if pid in permitidas:out.append({'persona_id':pid,'historial_diario':{'version':'359.1','fuente':'ClickUp entradas','fecha_fuente_utc':fuente.isoformat(),'cobertura':'parcial','unidad':'h','zona':zona,'zona_confirmada':True,'desde':desde.isoformat(),'hasta':hasta.isoformat(),'corte_fecha':doc['hoy'],'atribucion':'inicio','duracion_cerrada_confirmada':False,'sin_registros_no_equivale_a_cero':True,'dias':dias}})
 return out

def listar(S,rid,vid,path=None,ahora=None):
 ahora=ahora or dt.datetime.now(dt.timezone.utc)
 if not isinstance(ahora,dt.datetime) or ahora.tzinfo is None or ahora.utcoffset() is None:raise ErrorHistorial(503,'Corte de lectura inválido.')
 ids,firma=_ambito(S,rid,vid);configured=os.environ.get(ENV);p=path if path is not None else configured;config_inicio=(p,SHA,MANIFEST_SHA);rows=[];source=None
 if p:
  try:
   doc,manifest=cargar(p);rows=proyectar(doc,ids,ahora,S.P.hoy_iso());source=SHA
   if manifest.get('persona_filas')!=len(doc['personas']) or manifest.get('desde')!=(_fecha(doc['hoy'])-dt.timedelta(days=90)).isoformat():raise ValueError('Manifest ventana')
   if manifest.get('hasta')!=(_fecha(doc['hoy'])-dt.timedelta(days=1)).isoformat():raise ValueError('Manifest fin')
  except (OSError,ValueError,TypeError,KeyError,AttributeError,RecursionError,OverflowError):raise ErrorHistorial(503,'El historial privado no supera la validación. No acredita cero horas.')
 ids2,firma2=_ambito(S,rid,vid)
 if ids2!=ids or firma2!=firma or (p,SHA,MANIFEST_SHA)!=config_inicio or (path is None and os.environ.get(ENV)!=configured):raise ErrorHistorial(403,'El acceso cambió durante la lectura.')
 return {'version':VERSION,'estado':'copia_observada' if source else 'sin_dato','generado':ahora.astimezone(dt.timezone.utc).isoformat(),'fuente':'ClickUp entradas' if source else None,'fuente_version':'359.1' if source else None,'sha256_candidato':source,'cobertura':'parcial' if source else 'desconocida','unidad':'h','personas':rows,'cumplimiento':None,'capacidad_contractual':None,'nota':'Duración observada atribuida al inicio; copia parcial. Sin registros no equivale a cero. Incluye trabajo interno e histórico sin evaluar jornada.'}

def enganchar(H,S):
 original=H._api_get
 def get(self,ruta,q,real,persona):
  if ruta!=RUTA:return original(self,ruta,q,real,persona)
  if q:return self.responder(400,{'error':'Esta consulta no admite parámetros.'})
  try:return self.responder(200,listar(S,real.get('id'),persona.get('id')))
  except ErrorHistorial as e:return self.responder(e.codigo,{'error':str(e)})
 H._api_get=get
