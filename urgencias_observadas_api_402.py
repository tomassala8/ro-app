"""402: lector local398 de urgencias observadas. Import-safe, sin red/DB/activación."""
import hashlib,json,math,os,re,stat
from pathlib import Path
from datetime import datetime,timezone
from operaciones_registros_269 import unica,ErrorRegistro
from evidencia_produccion_287 import _leer_privado287
from fuentes_produccion.urgencias_observadas_398 import instante,iso
from fuentes_produccion.estados_catalogo import resolver_estado
import titulos_urgencias_485 as T485
RUTA='/api/produccion/urgencias-observadas';ENV='RO_URGENCIAS_OBSERVADAS_398';VERSION='402.1'
SHA='4d4f52762b4dd856002ebcf4724d2485d3532497e3359e86839d2e7825439544'
MANIFEST_SHA='5e827230c1f4b80aef9726d5881ba5e7d7cf8793e3c2387458eaefaf99ff31bb'
APP=Path(__file__).resolve().parent
ROLES=frozenset({'direccion','operaciones','account','trafficker','jefa_publicidad'})
NIVELES=('todo','suyo','resumen')
class ErrorUrgencias(Exception):
 def __init__(self,codigo,texto):self.codigo=codigo;super().__init__(texto)
def _id(v):return isinstance(v,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,150}',v) is not None
def _firma(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,allow_nan=False,default=lambda x:sorted(x) if isinstance(x,set) else (_ for _ in ()).throw(TypeError())).encode()).hexdigest()
def _ambito(S,rid,vid):
 if S.E.nucleo_bloqueado:raise ErrorUrgencias(503,'Permisos actuales no disponibles.')
 crudo=S.E.crudo
 try:epoca=_firma([crudo,getattr(S.P,'REGLAS',None)])
 except (ValueError,TypeError,OverflowError):raise ErrorUrgencias(503,'Permisos actuales incoherentes.')
 try:ps=[unica(crudo.get('personas'),pid) for pid in (rid,vid)]
 except ErrorRegistro:raise ErrorUrgencias(403,'Identidad activa no inequívoca.')
 conocidos=getattr(S.P,'PUESTO',{})
 niveles=[];contextos=[]
 for p in ps:
  roles=p.get('puestos')
  if not isinstance(roles,list) or not roles or any(not isinstance(r,str) or r not in conocidos for r in roles) or len(set(roles))!=len(roles) or not set(roles)&ROLES:raise ErrorUrgencias(403,'Consulta no disponible para esta sesión.')
  ns=[S.ve_alguno(p,[m]) for m in ('produccion','mi-trabajo')]
  if not any(n in NIVELES for n in ns):raise ErrorUrgencias(403,'Consulta no disponible para esta sesión.')
  niveles.append(ns);contextos.append(S.P.contexto(p,crudo))
 vista=S.P.ver(ps[0],{'tipo':'ver_como'},contextos[0]).get('ok') is True if rid!=vid else True
 if not vista:raise ErrorUrgencias(403,'Vista no autorizada.')
 cs=crudo.get('clientes');cs=cs if isinstance(cs,list) else []
 cuenta={}
 for c in cs:
  if isinstance(c,dict) and _id(c.get('id')):cuenta[c['id']]=cuenta.get(c['id'],0)+1
 ids=[];accesos=[]
 for c in cs:
  if not isinstance(c,dict) or not _id(c.get('id')):continue
  cid=c['id'];activo=S.ACT.es_activo_id(cid) is True
  permitidos=[S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},cp).get('ok') is True for p,cp in zip(ps,contextos)]
  accesos.append([cid,activo,permitidos])
  if cuenta[cid]==1 and activo and c.get('activo') is not False and c.get('estado')!='baja' and all(permitidos):ids.append(cid)
 ids.sort()
 if S.E.crudo is not crudo or _firma([crudo,getattr(S.P,'REGLAS',None)])!=epoca:raise ErrorUrgencias(403,'El catálogo cambió durante la autorización.')
 try:firma=_firma([rid,vid,ids,crudo.get('personas'),cs,crudo.get('asignaciones'),niveles,accesos,vista,contextos])
 except (ValueError,TypeError,OverflowError):raise ErrorUrgencias(503,'Permisos actuales incoherentes.')
 return ids,firma

def ambito(S,rid,vid):
 try:return _ambito(S,rid,vid)
 except ErrorUrgencias:raise
 except (ValueError,TypeError,KeyError,AttributeError,OverflowError,RecursionError):raise ErrorUrgencias(503,'La fuente de permisos no supera la validación.')

def _fuentes():
 paths={'tareas':APP/'fuentes_produccion/_privado/_cache/tareas.json','catalogo_estados':APP/'fuentes_produccion/_privado/_cache/estados_listas.json','ACT':APP/'data/verdad/estado_clientes.json'}
 paths.update({'cliente_documento:'+str(n):p for n,p in enumerate(sorted((APP/'data/clientes').glob('*.json')))})
 return paths

def _bytes_fuente(path,limite=180_000_000,guardar=False,privado=False):
 p=Path(path)
 if not p.is_absolute():raise ValueError('Fuente no absoluta')
 fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
 try:
  for part in p.parts[1:-1]:
   nxt=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=nxt
  f=os.open(p.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
  try:
   before=os.fstat(f)
   if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_uid!=os.getuid() or (privado and stat.S_IMODE(before.st_mode)!=0o600) or not 0<before.st_size<=limite:raise ValueError('Fuente inválida')
   sha=hashlib.sha256();chunks=[];n=0
   with os.fdopen(os.dup(f),'rb') as stream:
    while True:
     b=stream.read(1_000_000)
     if not b:break
     n+=len(b)
     if n>limite:raise ValueError('Fuente excesiva')
     sha.update(b)
     if guardar or limite<=2_000_000:chunks.append(b)
   after=os.fstat(f)
   if n!=before.st_size or (before.st_size,before.st_mtime_ns,before.st_ino)!=(after.st_size,after.st_mtime_ns,after.st_ino):raise ValueError('Fuente cambió')
   return sha.hexdigest(),b''.join(chunks)
  finally:os.close(f)
 finally:os.close(fd)

def verificar_fuentes(manifest,paths):
 hashes=manifest.get('fuentes_sha256')
 if not isinstance(paths,dict) or not isinstance(hashes,dict) or set(paths)!=set(hashes):raise ValueError('Inventario de fuente incoherente')
 catalogo=None
 for k,path in paths.items():
  esperado=hashes[k]
  if not isinstance(esperado,str) or not re.fullmatch('[0-9a-f]{64}',esperado):raise ValueError('SHA inválido')
  sha,raw=_bytes_fuente(path,2_000_000 if k=='catalogo_estados' else 180_000_000)
  if sha!=esperado:raise ValueError('Snapshot local cambió')
  if k=='catalogo_estados':
   catalogo=_json_estricto(raw)
 if not isinstance(catalogo,dict):raise ValueError('Catálogo no disponible')
 return catalogo

def _json_estricto(raw):
 def unicas(pares):
  d={}
  for k,v in pares:
   if k in d:raise ValueError('Clave duplicada')
   d[k]=v
  return d
 def numero(v):
  n=float(v)
  if not math.isfinite(n):raise ValueError('Número no finito')
  return n
 return json.loads(raw,object_pairs_hook=unicas,parse_float=numero,parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
def _privado402(p,sha,limite):
 _leer_privado287(p,sha,limite)
 hash_actual,raw=_bytes_fuente(p,limite,guardar=True,privado=True)
 if hash_actual!=sha:raise ValueError('SHA')
 return _json_estricto(raw),hash_actual

def cargar(path):
 p=Path(path)
 if p.name!='candidato.json' or not p.is_absolute():raise ValueError('Depósito inválido')
 st=p.parent.lstat()
 if not stat.S_ISDIR(st.st_mode) or stat.S_IMODE(st.st_mode)!=0o700 or st.st_uid!=os.getuid():raise ValueError('Depósito no privado')
 manifest,_=_privado402(p.parent/'manifest.json',MANIFEST_SHA,2_000_000)
 doc,sha=_privado402(p,SHA,8_000_000)
 if not isinstance(manifest,dict) or manifest.get('version')!='398.1' or manifest.get('promovido') is not False or manifest.get('lectura_no_concede_permiso') is not True or manifest.get('candidato_sha256')!=sha:raise ValueError('Manifest inválido')
 return doc,manifest,sha

ROW_KEYS={'tarea_id','cliente_id','lista_id','prioridad','estado','tipo_estado','estado_fuente','estado_leido_utc','prioridad_fuente','prioridad_leida_utc','verificacion_conjunta','medicion_urgencia','final_flujo_en_copia','clasificacion','es_fuego_actual','inicio_utc','inicio_estado','vence_utc','vence_estado','creada_utc','creada_estado','cerrada_utc','cerrada_estado','cobertura','actor_historico','inicio_urgencia_utc','ejecucion_verificada','aceptacion_verificada'}
def proyectar(doc,ids,catalogo,ahora):
 if not isinstance(doc,dict) or doc.get('version')!='398.1' or doc.get('fuente')!='clickup_cache_local' or doc.get('cobertura')!='parcial' or doc.get('promovido') is not False or doc.get('prioridad_seleccionada')!='urgent' or doc.get('descriptor_conjunto_disponible') is not False or doc.get('urgencias_actuales') is not None or doc.get('clasificacion_historia') is not False or doc.get('cumplimiento') is not None or doc.get('cero_no_acredita_ausencia') is not True or not isinstance(doc.get('filas'),list):raise ValueError('Esquema inválido')
 corte=instante(doc.get('corte_preparacion_utc'))
 if corte is None or corte>ahora:raise ValueError('Corte inválido')
 vistos=set();out=[];abiertas=[];finales=[]
 for r in doc['filas']:
  if not isinstance(r,dict) or set(r)!=ROW_KEYS or not all(_id(r.get(k)) for k in ('tarea_id','lista_id','cliente_id')) or r['tarea_id'] in vistos:raise ValueError('Identidad/whitelist inválida')
  vistos.add(r['tarea_id']);stamp=instante(r.get('estado_leido_utc'))
  if not isinstance(r.get('estado'),str) or not r['estado'] or len(r['estado'])>180 or any(ord(c)<32 for c in r['estado']) or stamp is None or stamp>corte or r.get('estado_fuente')!='clickup' or r.get('prioridad')!='urgent':raise ValueError('Observación inválida')
  e=resolver_estado({'lista_id':r['lista_id'],'estado':r['estado'],'tipo_estado':r.get('tipo_estado')},catalogo)
  final=e['final_flujo']
  if not e['determinado'] or r.get('tipo_estado')!=e['tipo'] or r.get('final_flujo_en_copia') is not final or r.get('clasificacion')!=('final_en_copia_no_reabrir' if final else 'abierta_en_copia_por_contrastar'):raise ValueError('Estado no ratificado')
  if r.get('prioridad_fuente')!='clickup_cache_literal' or r.get('verificacion_conjunta') is not False or r.get('ejecucion_verificada') is not False or r.get('aceptacion_verificada') is not False or r.get('cobertura')!='parcial' or any(r.get(k) is not None for k in ('prioridad_leida_utc','medicion_urgencia','es_fuego_actual','actor_historico','inicio_urgencia_utc')):raise ValueError('Certeza no acreditada')
  fechas={}
  for key in ('inicio','vence','creada','cerrada'):
   v=r.get(key+'_utc');estado=r.get(key+'_estado');d=instante(v)
   if estado=='observada':
    if d is None or (key in ('creada','cerrada') and d>corte) or (key=='cerrada' and not final):raise ValueError('Fecha no coherente')
    fechas[key+'_utc']=iso(d)
   elif v is None and estado in ('sin_dato','invalida') or (key=='cerrada' and not final and v is None and estado=='no_aplica'):fechas[key+'_utc']=None
   else:raise ValueError('Fecha no válida')
   fechas[key+'_estado']=estado
  (finales if final else abiertas).append(r['tarea_id'])
  if r['cliente_id'] in ids:
   out.append({k:r[k] for k in ('tarea_id','cliente_id','lista_id','prioridad','estado','tipo_estado','clasificacion','final_flujo_en_copia')}|{'estado_fuente':'clickup','estado_leido_utc':iso(stamp),'prioridad_fuente':'clickup_cache_literal','prioridad_leida_utc':None,'verificacion_conjunta':False,'es_fuego_actual':None,'medicion_urgencia':None,**fechas,'cobertura':'parcial','ejecucion_verificada':False,'aceptacion_verificada':False})
 if doc.get('abiertas_en_copia_ids')!=abiertas or doc.get('finales_en_copia_ids')!=finales:raise ValueError('Partición incoherente')
 return out,corte

def listar(S,rid,vid,cliente_id=None,grupo='abiertas',path=None,ahora=None,fuentes=None):
 if cliente_id is not None and not _id(cliente_id) or grupo not in ('abiertas','finales','todas'):raise ErrorUrgencias(400,'Filtro inválido.')
 ahora=ahora or datetime.now(timezone.utc)
 if not isinstance(ahora,datetime) or ahora.tzinfo is None:raise ErrorUrgencias(503,'Corte inválido.')
 ids,firma=ambito(S,rid,vid)
 if cliente_id is not None and cliente_id not in ids:raise ErrorUrgencias(403,'Cliente no disponible para esta sesión.')
 configured=os.environ.get(ENV);p=path if path is not None else configured;source=None;corte=None;out=[];paths=None;manifest=None
 if p:
  try:
   doc,manifest,source=cargar(p);paths=fuentes if fuentes is not None else _fuentes();catalogo=verificar_fuentes(manifest,paths);out,corte=proyectar(doc,ids,catalogo,ahora)
  except (OSError,ValueError,TypeError,AttributeError,RecursionError,OverflowError,UnicodeError):raise ErrorUrgencias(503,'El depósito de urgencias no supera la validación. No acredita ausencia de urgencias.')
 if cliente_id:out=[r for r in out if r['cliente_id']==cliente_id]
 abiertos=sum(not r['final_flujo_en_copia'] for r in out);finales=sum(r['final_flujo_en_copia'] for r in out)
 if grupo!='todas':out=[r for r in out if r['final_flujo_en_copia']==(grupo=='finales')]
 sin_titulos=lambda rows:[dict(r,titulo=None,titulo_estado='no_disponible',titulo_fuente=None,titulo_leido_utc=None) for r in rows]
 estado_titulos='no_disponible';validar_titulos=None;config_titulos=(os.environ.get(T485.ENV),T485.SHA,T485.MANIFEST_SHA)
 try:
  out,validar_titulos=T485.overlay(out,source_sha=source,source_manifest_sha=MANIFEST_SHA,raw_sha=manifest['fuentes_sha256']['tareas'] if manifest else None,corte=corte,leer=_privado402)
  if os.environ.get(T485.ENV):estado_titulos='validado'
 except (OSError,ValueError,TypeError,AttributeError,RecursionError,OverflowError,UnicodeError):
  out=sin_titulos(out);estado_titulos='sin_validacion'
 if validar_titulos is not None:
  try:validar_titulos()
  except (OSError,ValueError,TypeError,AttributeError,RecursionError,OverflowError,UnicodeError):
   out=sin_titulos(out);estado_titulos='sin_validacion'
 # Scope after the final IO: no old scope authorizes freshly read snapshots.
 if source:
  try:
   verificar_fuentes(manifest,paths)
   _,_,sha2=cargar(p)
   if sha2!=source:raise ValueError('Depósito cambió')
  except (OSError,ValueError,TypeError,AttributeError,RecursionError,OverflowError,UnicodeError):raise ErrorUrgencias(503,'La fuente cambió durante la lectura.')
 if config_titulos!=(os.environ.get(T485.ENV),T485.SHA,T485.MANIFEST_SHA):
  out=sin_titulos(out);estado_titulos='sin_validacion'
 ids2,firma2=ambito(S,rid,vid)
 if (ids2,firma2)!=(ids,firma) or (path is None and configured!=os.environ.get(ENV)):raise ErrorUrgencias(403,'El acceso cambió durante la lectura.')
 stamps=sorted((r['estado_leido_utc'] for r in out),key=instante)
 return {'version':VERSION,'estado':'copia_observada' if source else 'sin_dato','fuente_version':'398.1' if source else None,'fuente':'clickup_cache_local' if source else None,'sha256_candidato':source,'generado':iso(ahora),'corte_preparacion_utc':iso(corte) if corte else None,'lectura_desde_utc':stamps[0] if stamps else None,'lectura_hasta_utc':stamps[-1] if stamps else None,'cliente_ids':[cliente_id] if cliente_id else ids,'grupo':grupo,'cobertura':'parcial' if source else 'desconocida','observaciones':len(out) if out else None,'abiertas_en_copia':abiertos or None,'finales_en_copia':finales or None,'urgencias_actuales':None,'verificacion_conjunta':False,'filas':out,'titulos_estado':estado_titulos,'cumplimiento':None,'nota':'Prioridad urgent literal y estado observados en copia parcial. Falta lectura conjunta fechada; requiere contraste. No equivale a En rojo, aceptación ni ausencia actual de urgencias.'}

def enganchar(H,S):
 original=H._api_get
 def get(self,ruta,q,real,persona):
  if ruta!=RUTA:return original(self,ruta,q,real,persona)
  if not isinstance(q,dict) or set(q)-{'cliente_id','grupo'} or any(not isinstance(v,list) or len(v)!=1 or not isinstance(v[0],str) for v in q.values()):return self.responder(400,{'error':'Filtros inválidos.'})
  try:return self.responder(200,listar(S,real.get('id'),persona.get('id'),q.get('cliente_id',[None])[0],q.get('grupo',['abiertas'])[0]))
  except ErrorUrgencias as e:return self.responder(e.codigo,{'error':str(e)})
 H._api_get=get
