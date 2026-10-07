"""356: depósito355 privado → inventario de planning scoped. Sin IO al importar ni proveedores."""
import collections,hashlib,json,os,math,re,stat
from pathlib import Path
from datetime import datetime,timezone
from historico_llamadas_350 import ambito,ErrorHistorico
from evidencia_produccion_287 import _leer_privado287
from fuentes_produccion.planning_observado_355 import instante,iso
RUTA='/api/produccion/planning-observado';ENV='RO_PLANNING_OBSERVADO_355';VERSION='356.1'
SHA='be7ff0dcc533d283d7fb2f02cc556b0fc0d9e39f080e5eb1b95ddde02818a7a4'
MANIFEST_SHA='2460b02f6327ce178e07e3d2bec20fd51e75e7f53795e7457101aedcad48bc3a'
class ErrorPlanning(Exception):
 def __init__(self,codigo,texto):self.codigo=codigo;super().__init__(texto)
def _id(v):return isinstance(v,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,150}',v) is not None
def _ambito(S,rid,vid):
 try:ids,base=ambito(S,rid,vid)
 except ErrorHistorico as e:raise ErrorPlanning(e.codigo,str(e))
 ps=S.E.crudo.get('personas') or []
 actores=[next(p for p in ps if isinstance(p,dict) and p.get('id')==pid) for pid in (rid,vid)]
 mods=[S.ve_alguno(p,['produccion']) for p in actores]
 if not all(n in ('resumen','suyo','todo') for n in mods):raise ErrorPlanning(403,'Planning no disponible para esta sesión.')
 return ids,hashlib.sha256(json.dumps([base,mods]).encode()).hexdigest()
def cargar(path):
 p=Path(path)
 if p.name!='candidato.json':raise ValueError('Ruta de depósito inválida')
 st=p.parent.lstat()
 if not stat.S_ISDIR(st.st_mode) or stat.S_IMODE(st.st_mode)!=0o700 or st.st_uid!=os.getuid():raise ValueError('Depósito no privado')
 manifest,_=_leer_privado287(p.parent/'manifest.json',MANIFEST_SHA,2_000_000)
 doc,sha=_leer_privado287(p,SHA,8_000_000)
 if not isinstance(manifest,dict) or manifest.get('version')!='355.1' or manifest.get('promovido') is not False or manifest.get('candidato_sha256')!=sha or manifest.get('lectura_no_concede_permiso') is not True:raise ValueError('Manifest inválido')
 return doc,sha

def proyectar(doc,ids,personas,ahora):
 if not isinstance(doc,dict) or doc.get('version')!='355.1' or doc.get('fuente')!='clickup_cache_local' or doc.get('cobertura')!='parcial' or doc.get('promovido') is not False or doc.get('clasificacion_historia') is not False or doc.get('cumplimiento') is not None or doc.get('cero_no_acredita_ausencia') is not True or not isinstance(doc.get('filas'),list):raise ValueError('Esquema inválido')
 if not isinstance(ahora,datetime) or ahora.tzinfo is None:raise ValueError('Corte explícito inválido')
 counts=collections.Counter(p.get('id') for p in personas if isinstance(p,dict) and isinstance(p.get('id'),str));active={p['id'] for p in personas if isinstance(p,dict) and _id(p.get('id')) and counts[p['id']]==1 and p.get('estado')=='activo' and p.get('activo') is not False}
 seen=set();out=[]
 for r in doc['filas']:
  if not isinstance(r,dict) or not all(_id(r.get(k)) for k in ('tarea_id','cliente_id','lista_id')) or r['tarea_id'] in seen:raise ValueError('Identidad de fila inválida')
  seen.add(r['tarea_id'])
  stamp=instante(r.get('estado_leido_utc'))
  if r.get('estado') not in ('backlog','planning mensual') or r.get('tipo_estado') not in ('open','custom','unstarted') or r.get('estado_fuente')!='clickup' or stamp is None or stamp>ahora or r.get('cobertura')!='parcial' or any(r.get(k) is not None for k in ('actor_historico','estado_inicial','rompe_semanal','fuego_confirmado')):raise ValueError('Descriptor inválido')
  assigned=r.get('asignados_persona_ids');unknown=r.get('asignados_sin_identidad_confirmada')
  if not isinstance(assigned,list) or any(not _id(x) for x in assigned) or len(set(assigned))!=len(assigned) or type(unknown) is not int or unknown<0 or r.get('asignacion_estado') not in ('observada','parcial') or (r['asignacion_estado']=='observada' and unknown!=0):raise ValueError('Asignación inválida')
  dates={}
  for k in ('inicio','vence'):
   v=r.get(k+'_utc');state=r.get(k+'_estado')
   if state=='observada':
    d=instante(v)
    if d is None:raise ValueError('Fecha programada inválida')
    dates[k+'_utc']=iso(d)
   elif state in ('sin_dato','invalida') and v is None:dates[k+'_utc']=None
   else:raise ValueError('Fecha desconocida inválida')
   dates[k+'_estado']=state
  e=r.get('estimacion')
  if not isinstance(e,dict) or e.get('unidad')!='milisegundos':raise ValueError('Unidad inválida')
  value=e.get('valor');known=type(value) in (int,float) and math.isfinite(value) and value>0
  if (known and e.get('estado')!='observada') or (not known and (value is not None or e.get('estado')!='sin_dato')):raise ValueError('Estimación inválida')
  if r['cliente_id'] not in ids:continue
  pids=[pid for pid in assigned if pid in active];missing=unknown+len(assigned)-len(pids)
  out.append({k:r[k] for k in ('tarea_id','cliente_id','lista_id','estado','tipo_estado')}|{'estado_fuente':'clickup','estado_leido_utc':iso(stamp),'asignados_persona_ids':pids,'asignacion_estado':'parcial' if missing else 'observada','asignados_sin_identidad_confirmada':missing,
   **dates,'estimacion':{'valor':value,'unidad':'milisegundos','estado':e['estado']},'cobertura':'parcial','actor_historico':None,'estado_inicial':None,'rompe_semanal':None,'fuego_confirmado':None})
 return out

def listar(S,rid,vid,path=None,ahora=None):
 ahora=ahora or datetime.now(timezone.utc)
 if not isinstance(ahora,datetime) or ahora.tzinfo is None:raise ErrorPlanning(503,'Corte de lectura inválido.')
 ids,firma=_ambito(S,rid,vid);configured=os.environ.get(ENV);p=path if path is not None else configured
 out=[];source=None
 if p:
  try:
   doc,sha=cargar(p);out=proyectar(doc,ids,S.E.crudo.get('personas') or [],ahora);source=sha
  except (OSError,ValueError,TypeError,AttributeError,RecursionError,OverflowError):raise ErrorPlanning(503,'El depósito de planning no supera la validación. No acredita ausencia de tareas.')
 ids2,firma2=_ambito(S,rid,vid)
 if ids2!=ids or firma2!=firma or (path is None and configured!=os.environ.get(ENV)):raise ErrorPlanning(403,'El acceso cambió durante la lectura.')
 readings=sorted((r['estado_leido_utc'] for r in out),key=instante)
 return {'version':VERSION,'fuente_version':'355.1' if source else None,'sha256_candidato':source,'estado':'copia_observada' if source else 'sin_dato','fuente':'clickup_cache_local' if source else None,'generado':iso(ahora),'cobertura':'parcial' if source else 'desconocida','lectura_desde_utc':readings[0] if readings else None,'lectura_hasta_utc':readings[-1] if readings else None,'observaciones':len(out) if out else None,'cliente_ids':ids,'filas':out,'disciplina':None,'cumplimiento':None,'nota':'Estado observado en copia parcial. No clasifica fuegos ni ruptura del planning; estimación no es capacidad. Sin filas no acredita ausencia de tareas.'}

def enganchar(H,S):
 original=H._api_get
 def get(self,ruta,q,real,persona):
  if ruta!=RUTA:return original(self,ruta,q,real,persona)
  if q:return self.responder(400,{'error':'Esta consulta no admite parámetros.'})
  try:return self.responder(200,listar(S,real.get('id'),persona.get('id')))
  except ErrorPlanning as e:return self.responder(e.codigo,{'error':str(e)})
 H._api_get=get
