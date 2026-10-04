"""376 lectura privada: permisos antes del agregado375. Sin IO al importar/red/escrituras."""
import collections,datetime as dt,hashlib,json,math,os,re,stat
from pathlib import Path
from fuentes_horas.agrupaciones_artifact_375 import construir,clave,instante,grupo_titulo
from fuentes_horas.deposito_agrupaciones_376 import uid
from historial_diario_api_362 import _ambito as ambito_personas,ErrorHistorial,_hash,unica
from identidades_clickup_204 import resolver
from identidad_generadores_212 import clientes_directos
RUTA='/api/horas/agrupaciones-tarea';ENV='RO_AGRUPACIONES_TAREA_376';VERSION='376.1'
SHA='1045a53219b967885e5bfe6748327c3ca19a48e71266bd4c522c4e236e833670'
MANIFEST_SHA='fec21a30b11933ae2c43241d5178b9eff030fc4f5badeb04b331501420955902'
APP=Path(__file__).resolve().parent
class ErrorAgrupaciones(Exception):
 def __init__(self,codigo,texto):self.codigo=codigo;super().__init__(texto)
def _ambito(S,rid,vid):
 try:return _ambito_actual(S,rid,vid)
 except ErrorHistorial as e:raise ErrorAgrupaciones(e.codigo,str(e))
 except (TypeError,ValueError,KeyError,AttributeError,StopIteration):raise ErrorAgrupaciones(403,'No se puede acreditar el ámbito actual.')
def _ambito_actual(S,rid,vid):
 pids,base=ambito_personas(S,rid,vid)
 ps=[unica(S.E.crudo.get('personas'),i) for i in (rid,vid)];niveles=[S.ve_alguno(p,['produccion']) for p in ps]
 if any(n not in ('todo','suyo','resumen') for n in niveles):raise ErrorAgrupaciones(403,'Producción no disponible para esta sesión.')
 cps=[S.P.contexto(p,S.E.crudo) for p in ps];cs=S.E.crudo.get('clientes');cs=cs if isinstance(cs,list) else []
 counts=collections.Counter(c.get('id') for c in cs if isinstance(c,dict) and clave(c.get('id')))
 ids=sorted(c['id'] for c in cs if isinstance(c,dict) and clave(c.get('id')) and counts[c['id']]==1 and c.get('activo') is not False and S.ACT.es_activo_id(c['id']) is True and all(S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':c['id']},cp).get('ok') is True for p,cp in zip(ps,cps)))
 p2,b2=ambito_personas(S,rid,vid)
 if (pids,base)!=(p2,b2):raise ErrorAgrupaciones(403,'El catálogo cambió durante la autorización.')
 return pids,ids,_hash([base,niveles,ids,cs,S.E.crudo.get('asignaciones'),cps])
def _leer_fuente(path,limit=100_000_000):
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 with os.fdopen(fd,'rb') as f:
  a=os.fstat(f.fileno())
  if not stat.S_ISREG(a.st_mode) or a.st_nlink!=1 or not 0<a.st_size<=limit:raise ValueError('Fuente no regular/acotada')
  raw=f.read(limit+1);z=os.fstat(f.fileno())
  if (a.st_size,a.st_mtime_ns,a.st_ctime_ns)!=(z.st_size,z.st_mtime_ns,z.st_ctime_ns) or len(raw)!=a.st_size:raise ValueError('Fuente cambió')
 return raw,hashlib.sha256(raw).hexdigest()
def _hash_fuente(path,limit=180_000_000):
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 with os.fdopen(fd,'rb') as f:
  a=os.fstat(f.fileno())
  if not stat.S_ISREG(a.st_mode) or a.st_nlink!=1 or not 0<a.st_size<=limit:raise ValueError('Fuente no regular/acotada')
  h=hashlib.sha256();n=0
  while True:
   b=f.read(65536)
   if not b:break
   n+=len(b)
   if n>limit:raise ValueError('Fuente excede límite')
   h.update(b)
  z=os.fstat(f.fileno())
  if (a.st_size,a.st_mtime_ns,a.st_ctime_ns)!=(z.st_size,z.st_mtime_ns,z.st_ctime_ns) or n!=a.st_size:raise ValueError('Fuente cambió')
 return h.hexdigest()
def evidencia_actual(S):
 from config import PANEL_OPERACIONES
 b,msha=_leer_fuente(Path(PANEL_OPERACIONES)/'_crudo/clickup/miembros.json',8_000_000)
 m=json.loads(b);users=(m.get('miembros') or [])+(m.get('usuarios_no_miembros_vistos') or [])
 folders,_=clientes_directos(APP/'data');ident=resolver(S.E.crudo.get('personas'),users)['por_usuario']
 tsha=_hash_fuente(APP/'fuentes_produccion/_privado/_cache/tareas.json')
 return {'identidades':ident,'carpetas':folders,'tareas_sha256':tsha,'firma':_hash([msha,folders,ident,tsha])}
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
  manifest=leer('manifest.json',MANIFEST_SHA,2_000_000);doc=leer('candidato.json',SHA,12_000_000)
  if not isinstance(manifest,dict) or manifest.get('version')!='376.1' or manifest.get('output_sha256')!=SHA or manifest.get('sin_promover') is not True or manifest.get('proveedores_consultados')!=0 or manifest.get('dedup_global_antes_scope') is not True:raise ValueError('Manifest')
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


def proyectar(doc,pids,cids,evidencia,ahora):
 if not isinstance(doc,dict) or doc.get('version')!=VERSION or doc.get('sin_promover') is not True or doc.get('sin_agregado_global') is not True or doc.get('dedup_global_antes_scope') is not True or doc.get('cobertura')!='parcial' or doc.get('clasificacion')!='orientativa_por_titulo':raise ValueError('Contrato')
 leido=instante(doc.get('leido'));corte=instante(doc.get('corte'))
 if not leido or not corte or leido!=corte or corte>ahora:raise ValueError('Corte')
 hashes=doc.get('fuentes_sha256')
 if not isinstance(hashes,dict) or hashes.get('tareas')!=evidencia.get('tareas_sha256'):raise ValueError('Inventario actual no coincide con copia')
 ident=doc.get('identidades');ts=doc.get('tareas');es=doc.get('entradas')
 if not isinstance(ident,dict) or not all(uid(u)==u and clave(p) for u,p in ident.items()) or not isinstance(ts,list) or len(ts)>30_000 or not isinstance(es,list) or len(es)>50_000:raise ValueError('Catálogos')
 tasks=[];tids=set();seen=set()
 for t in ts:
  if not isinstance(t,dict) or set(t)!={'id','lista_id','carpeta_id','cliente_id','nombre'} or not all(clave(t.get(k)) for k in ('id','lista_id','carpeta_id','cliente_id')) or t['id'] in seen or not isinstance(t.get('nombre'),str) or grupo_titulo(t['nombre'],[])!=t['nombre']:raise ValueError('Tarea/grupo inválidos')
  seen.add(t['id']);ref=evidencia['carpetas'].get(t['carpeta_id'])
  if ref and ref[0]==t['cliente_id'] and t['cliente_id'] in cids:tasks.append({k:t[k] for k in ('id','cliente_id','nombre')});tids.add(t['id'])
 eids=set()
 for e in es:
  if not isinstance(e,dict) or set(e)!={'id','usuario_id','task_id','inicio','horas'} or not clave(e.get('id')) or e['id'] in eids or uid(e.get('usuario_id'))!=e.get('usuario_id') or not clave(e.get('task_id')):raise ValueError('Entrada inválida')
  eids.add(e['id']);inicio=instante(e.get('inicio'));h=e.get('horas')
  if not inicio or inicio>leido or type(h) not in (int,float) or not math.isfinite(h) or h<0:raise ValueError('Tiempo inválido')
 uids={u for u,p in ident.items() if p in pids and evidencia['identidades'].get(u)==p}
 result=construir(es,tasks,cliente_ids=set(cids),tarea_ids=tids,usuario_ids=uids,nombres_clientes=[],observado_hasta=corte.isoformat(),fuente={'leido':leido.isoformat(),'sha256':SHA})
 return result

def listar(S,rid,vid,path=None,ahora=None):
 ahora=ahora or dt.datetime.now(dt.timezone.utc)
 if not isinstance(ahora,dt.datetime) or ahora.tzinfo is None:raise ErrorAgrupaciones(503,'Corte inválido.')
 pids,cids,firma=_ambito(S,rid,vid);configured=os.environ.get(ENV);p=path if path is not None else configured;inicio_config=(p,SHA,MANIFEST_SHA);out=None;ev=None
 if p:
  try:
   ev=evidencia_actual(S);doc,manifest=cargar(p);out=proyectar(doc,pids,cids,ev,ahora)
  except (OSError,ValueError,TypeError,KeyError,AttributeError,RecursionError,OverflowError):raise ErrorAgrupaciones(503,'La copia privada no supera la validación. No acredita cero horas.')
 p2,c2,f2=_ambito(S,rid,vid)
 if (pids,cids,firma)!=(p2,c2,f2) or (path is None and os.environ.get(ENV)!=configured):raise ErrorAgrupaciones(403,'El ámbito cambió durante la lectura.')
 if ev:
  try:posterior=evidencia_actual(S)['firma']
  except (OSError,ValueError,TypeError,KeyError,AttributeError):raise ErrorAgrupaciones(503,'La fuente de identidad dejó de estar disponible.')
  if posterior!=ev['firma']:raise ErrorAgrupaciones(403,'La identidad o inventario cambió durante la lectura.')
 # Último IO también puede coincidir con una revocación: revalidar DESPUÉS.
 p3,c3,f3=_ambito(S,rid,vid)
 if (pids,cids,firma)!=(p3,c3,f3) or inicio_config!=(p,SHA,MANIFEST_SHA) or (path is None and os.environ.get(ENV)!=configured):raise ErrorAgrupaciones(403,'El ámbito cambió antes de entregar el resultado.')
 return {'version':VERSION,'estado':'copia_observada' if out else 'sin_dato','generado':ahora.astimezone(dt.timezone.utc).isoformat(),'sha256_candidato':SHA if out else None,'fuente':'ClickUp entradas' if out else None,'cobertura':'parcial' if out else 'desconocida','ventana':out['ventana'] if out else None,'fecha_fuente':out['fuente']['leido'] if out else None,'unidad':'h','unidad_muestra':'usuario_id+task_id','unidad_maximo':'suma_por_caso','clasificacion':'orientativa_por_titulo','minimo_casos':5,'filas':out['filas'] if out else [],'duracion_cerrada_confirmada':False,'tipo_historico_confirmado':False,'tiempo_normativo':None,'nota':'Agrupación orientativa, copia parcial de 60 fechas naturales de Madrid. Sin cinco casos autorizados no se calcula una fila; ausencia no equivale a cero.'}
def enganchar(H,S):
 original=H._api_get
 def get(self,ruta,q,real,persona):
  if ruta!=RUTA:return original(self,ruta,q,real,persona)
  if q:return self.responder(400,{'error':'Esta consulta no admite parámetros.'})
  try:return self.responder(200,listar(S,real.get('id'),persona.get('id')))
  except ErrorAgrupaciones as e:return self.responder(e.codigo,{'error':str(e)})
 H._api_get=get
