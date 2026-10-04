"""405: depósito395 opt-in en GET356. Sólo lectura; ningún IO al importar."""
import collections,copy,hashlib,json,math,os,stat
from pathlib import Path
from datetime import datetime,timezone
import planning_observado_api_356 as B
from fuentes_produccion.planning_observado_395 import ESTADOS,instante,iso
from fuentes_produccion.estados_catalogo import resolver_estado
ENV='RO_PLANNING_OBSERVADO_395';VERSION='405.1'
SHA='f0503e6e5edeaff1fabffb602e5a2bb80ed3e2c432c2bf9fad03ec25c0f8a292'
MANIFEST_SHA='d460f17ef25ae632191206ad98c464a6ead768eb395c562caee3ec376de25a02'
APP=Path(__file__).resolve().parent
OLD=Path('/Users/tomassala/Downloads/PANEL_OPERACIONES_2026-10-01')
def _leer(path,sha,limite,privado=False,json_doc=True):
 p=Path(path)
 if not p.is_absolute():raise ValueError('Ruta')
 fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
 try:
  for part in p.parts[1:-1]:
   nf=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=nf
  parent=os.fstat(fd)
  if privado and (stat.S_IMODE(parent.st_mode)!=0o700 or parent.st_uid!=os.getuid()):raise ValueError('Depósito privado')
  ff=os.open(p.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
  try:
   a=os.fstat(ff)
   if not stat.S_ISREG(a.st_mode) or a.st_nlink!=1 or a.st_uid!=os.getuid() or not 0<a.st_size<=limite or (privado and stat.S_IMODE(a.st_mode)!=0o600):raise ValueError('Archivo')
   with os.fdopen(os.dup(ff),'rb') as f:raw=f.read(limite+1)
   z=os.fstat(ff)
   if len(raw)!=a.st_size or (a.st_size,a.st_mtime_ns,a.st_ino)!=(z.st_size,z.st_mtime_ns,z.st_ino):raise ValueError('Archivo cambiado')
  finally:os.close(ff)
 finally:os.close(fd)
 if hashlib.sha256(raw).hexdigest()!=sha:raise ValueError('SHA')
 if not json_doc:return None
 def unico(pares):
  out={}
  for k,v in pares:
   if k in out:raise ValueError('JSON ambiguo')
   out[k]=v
  return out
 def no(v):raise ValueError('JSON no finito')
 def flotante(v):
  n=float(v)
  if not math.isfinite(n):raise ValueError('JSON no finito')
  return n
 return json.loads(raw,object_pairs_hook=unico,parse_constant=no,parse_float=flotante)
def verificar_fuentes(manifest):
 paths={'tareas':APP/'fuentes_produccion/_privado/_cache/tareas.json','catalogo_estados':APP/'fuentes_produccion/_privado/_cache/estados_listas.json','personas':APP/'data/personas.json','miembros':OLD/'_crudo/clickup/miembros.json','ACT':APP/'data/verdad/estado_clientes.json'}
 paths.update({'cliente_documento:'+str(i):p for i,p in enumerate(sorted((APP/'data/clientes').glob('*.json')))})
 codes=[APP/'identidades_clickup_204.py',APP/'identidad_generadores_212.py',APP/'fuentes_produccion/estados_catalogo.py',APP/'fuentes_produccion/planning_observado_355.py',APP/'fuentes_produccion/planning_observado_395.py',APP/'fuentes_verdad/clientes_activos.py',APP.parent/'RECUPERACION_CODEX_2026-10-03/preparar_planning_observado_395.py']
 if set(paths)!=set(manifest.get('fuentes_sha256',{})) or {p.name for p in codes}!=set(manifest.get('codigo_sha256',{})):raise ValueError('Conjunto de fuentes cambiado')
 catalogo=None
 for key,p in paths.items():
  data=_leer(p,manifest['fuentes_sha256'][key],180_000_000,json_doc=key=='catalogo_estados')
  if key=='catalogo_estados':catalogo=data
 for p in codes:_leer(p,manifest['codigo_sha256'][p.name],2_000_000,json_doc=False)
 return catalogo

def cargar(path):
 p=Path(path)
 if p.name!='candidato.json':raise ValueError('Ruta de candidato')
 manifest=_leer(p.parent/'manifest.json',MANIFEST_SHA,2_000_000,True)
 doc=_leer(p,SHA,8_000_000,True)
 if not isinstance(manifest,dict) or manifest.get('version')!='395.1' or manifest.get('candidato_sha256')!=SHA or manifest.get('promovido') is not False or manifest.get('lectura_no_concede_permiso') is not True or doc.get('entradas_sha256')!=manifest.get('fuentes_sha256') or doc.get('codigo_sha256')!=manifest.get('codigo_sha256'):raise ValueError('Manifest')
 return doc,manifest,verificar_fuentes(manifest)

def proyectar(doc,ids,personas,ahora,catalogo):
 if not isinstance(doc,dict) or doc.get('version')!='395.1' or doc.get('estados_incluidos')!=sorted(ESTADOS) or not isinstance(doc.get('filas'),list):raise ValueError('Esquema395')
 prep=instante(doc.get('corte_preparacion_utc'))
 if not isinstance(ahora,datetime) or ahora.tzinfo is None or prep is None or prep>ahora:raise ValueError('Corte')
 estados={}
 for r in doc['filas']:
  if not isinstance(r,dict) or r.get('estado') not in ESTADOS:raise ValueError('Estado')
  match=resolver_estado({'lista_id':r.get('lista_id'),'estado':r.get('estado'),'tipo_estado':r.get('tipo_estado')},catalogo)
  if not match['determinado'] or match['final_flujo'] or match['tipo']!=r.get('tipo_estado'):raise ValueError('Catálogo de lista')
  lectura=instante(r.get('estado_leido_utc'))
  if lectura is None or lectura>prep:raise ValueError('Lectura')
  estados[r.get('tarea_id')]=(r['estado'],r['tipo_estado'])
 # Reutiliza validaciones355 de identidad global, fechas, estimaciones, asignados y minimización.
 base=copy.deepcopy(doc);base['version']='355.1'
 for r in base['filas']:r['estado']='planning mensual';r['tipo_estado']='custom'
 rows=B.proyectar(base,ids,personas,ahora)
 for r in rows:r['estado'],r['tipo_estado']=estados[r['tarea_id']]
 return rows

def listar(S,rid,vid,path=None,ahora=None):
 ahora=ahora or datetime.now(timezone.utc)
 ids,firma=B._ambito(S,rid,vid);configured=os.environ.get(ENV);p=path if path is not None else configured
 if not p:raise B.ErrorPlanning(503,'Inventario ampliado no habilitado.')
 try:
  doc,manifest,catalogo=cargar(p);rows=proyectar(doc,ids,S.E.crudo.get('personas') or [],ahora,catalogo)
  verificar_fuentes(manifest)
 except (OSError,ValueError,TypeError,AttributeError,KeyError,RecursionError,OverflowError):raise B.ErrorPlanning(503,'El depósito ampliado no supera la validación; no acredita ausencia de tareas.')
 ids2,firma2=B._ambito(S,rid,vid)
 if ids2!=ids or firma2!=firma or (path is None and configured!=os.environ.get(ENV)):raise B.ErrorPlanning(403,'El acceso cambió durante la lectura.')
 readings=sorted((r['estado_leido_utc'] for r in rows),key=instante)
 return {'version':VERSION,'fuente_version':'395.1','sha256_candidato':SHA,'estado':'copia_observada','fuente':'clickup_cache_local','generado':iso(ahora),'corte_preparacion_utc':doc['corte_preparacion_utc'],'estados_incluidos':sorted(ESTADOS),'cobertura':'parcial','lectura_desde_utc':readings[0] if readings else None,'lectura_hasta_utc':readings[-1] if readings else None,'observaciones':len(rows) or None,'cliente_ids':ids,'filas':rows,'disciplina':None,'cumplimiento':None,'nota':'Inventario observado parcial; cinco estados exactos. No acredita ruptura, fuego, carga completa ni entrega aceptada.'}
def enganchar(H,S):
 original=H._api_get
 def get(self,ruta,q,real,persona):
  if ruta!=B.RUTA or not os.environ.get(ENV):return original(self,ruta,q,real,persona)
  if q:return self.responder(400,{'error':'Esta consulta no admite parámetros.'})
  try:return self.responder(200,listar(S,real.get('id'),persona.get('id')))
  except B.ErrorPlanning as e:return self.responder(e.codigo,{'error':str(e)})
 H._api_get=get
