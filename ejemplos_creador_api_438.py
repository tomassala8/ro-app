"""438 lectura opt-in, sin IO al importar; candidato no se activa automáticamente."""
import os,collections
from pathlib import Path
from datetime import datetime,timezone
import agrupaciones_tarea_api_376 as G
import planning_observado_api_405 as D
from fuentes_produccion.ejemplos_creador_438 import VERSION,CAMPOS
from fuentes_produccion.planning_observado_395 import instante,iso,clave,ESTADOS
from fuentes_produccion.estados_catalogo import resolver_estado
from contexto_tarea import texto_operativo
from identidades_clickup_204 import resolver
RUTA='/api/produccion/ejemplos-creador';ENV='RO_EJEMPLOS_CREADOR_438'
# QA raíz: hashes, código y proyección2172 validados antes de activar sólo revisión local.
SHA='23ace1eb937926c13c18a05c6ac0e42e4b2a7b40585de0be606f19efa474696d';MANIFEST_SHA='18c982b30ae811016c41af16ccee3db941d2d4530e198a2ba4edbe987656240f'
APP=Path(__file__).resolve().parent
CODES=[APP/'fuentes_produccion/ejemplos_creador_438.py',APP/'contexto_tarea.py',APP.parent/'RECUPERACION_CODEX_2026-10-03/preparar_ejemplos_creador_438.py']
def cargar(path):
 if not isinstance(SHA,str) or not isinstance(MANIFEST_SHA,str):raise ValueError('Pins no aprobados')
 p=Path(path)
 if p.name!='candidato.json':raise ValueError('Ruta')
 m=D._leer(p.parent/'manifest.json',MANIFEST_SHA,2_000_000,True);doc=D._leer(p,SHA,3_000_000,True)
 if m.get('version')!=VERSION or m.get('candidato_sha256')!=SHA or m.get('sin_promover') is not True or m.get('proveedores_consultados')!=0:raise ValueError('Manifest')
 if {p.name for p in CODES}!=set(m.get('codigo438_sha256',{})):raise ValueError('Código')
 for p in CODES:D._leer(p,m['codigo438_sha256'][p.name],2_000_000,json_doc=False)
 return doc,m,D.verificar_fuentes(m['base395'])
def proyectar(doc,pids,cids,ahora,catalogo,identidades):
 if not isinstance(doc,dict) or doc.get('version')!=VERSION or doc.get('fuente')!='clickup_cache_local' or doc.get('cobertura')!='parcial' or doc.get('sin_promover') is not True or doc.get('atribucion')!='creador_ID_exacto' or doc.get('creacion_no_es_planificacion') is not True or doc.get('cumplimiento') is not None or not isinstance(doc.get('filas'),list):raise ValueError('Esquema')
 corte=instante(doc.get('corte_preparacion_utc'))
 if corte is None or corte>ahora:raise ValueError('Corte')
 seen=set();out=[]
 for r in doc['filas']:
  if not isinstance(r,dict) or set(r)!=CAMPOS or not all(isinstance(r.get(k),str) and clave(r[k])==r[k] for k in ('tarea_id','cliente_id','lista_id','persona_id','creador_usuario_id')) or r['tarea_id'] in seen:raise ValueError('Identidad')
  seen.add(r['tarea_id']);created=instante(r['creada_utc']);read=instante(r['estado_leido_utc'])
  match=resolver_estado({'lista_id':r['lista_id'],'estado':r['estado_observado'],'tipo_estado':r['tipo_estado']},catalogo)
  if created is None or read is None or not created<=read<=corte or r['estado_observado'] not in ESTADOS or not match['determinado'] or match['final_flujo'] or match['tipo']!=r['tipo_estado']:raise ValueError('Fecha/estado')
  label=r['titulo_saneado']
  if not isinstance(label,str) or len(label)>240 or texto_operativo(label,240)!=label or 'http://' in label.lower() or 'https://' in label.lower():raise ValueError('Título')
  if identidades.get(r['creador_usuario_id'])!=r['persona_id']:continue
  if r['persona_id'] in pids and r['cliente_id'] in cids:out.append({k:v for k,v in r.items() if k!='creador_usuario_id'})
 return out

def _ambito_actual(S,rid,vid):
 pids,cids,scope=G._ambito(S,rid,vid)
 ps=S.E.crudo.get('personas') or []
 def roles(p):
  rs=p.get('puestos')
  return isinstance(rs,list) and bool(rs) and all(isinstance(r,str) and clave(r)==r for r in rs) and len(set(rs))==len(rs)
 if any(not roles(G.unica(ps,i)) for i in (rid,vid)):raise G.ErrorAgrupaciones(403,'Perfil actual no inequívoco.')
 pids=[pid for pid in pids if roles(G.unica(ps,pid))]
 return pids,cids,G._hash([scope,pids,ps])

def _ambito(S,rid,vid):
 try:return _ambito_actual(S,rid,vid)
 except G.ErrorHistorial as e:raise G.ErrorAgrupaciones(e.codigo,'El catálogo actual no acredita el acceso.')
 except (TypeError,ValueError,KeyError,AttributeError):raise G.ErrorAgrupaciones(403,'No se puede acreditar el perfil actual.')

def listar(S,rid,vid,path=None,ahora=None):
 now=ahora or datetime.now(timezone.utc);pids,cids,scope=_ambito(S,rid,vid);configured=os.environ.get(ENV);path=path if path is not None else configured
 if not path:raise G.ErrorAgrupaciones(503,'Ejemplos de creador no habilitados.')
 try:
  doc,m,catalogo=cargar(path)
  members=D._leer(D.OLD/'_crudo/clickup/miembros.json',m['base395']['fuentes_sha256']['miembros'],2_000_000)
  users=members.get('miembros',[])+members.get('usuarios_no_miembros_vistos',[])
  ident=resolver(S.E.crudo.get('personas'),users)['por_usuario']
  rows=proyectar(doc,pids,cids,now,catalogo,ident)
  D.verificar_fuentes(m['base395'])
  for p in CODES:D._leer(p,m['codigo438_sha256'][p.name],2_000_000,json_doc=False)
 except (OSError,ValueError,TypeError,AttributeError,KeyError,OverflowError,RecursionError):raise G.ErrorAgrupaciones(503,'La copia de ejemplos no supera la validación.')
 p2,c2,s2=_ambito(S,rid,vid)
 if resolver(S.E.crudo.get('personas'),users)['por_usuario']!=ident or (pids,cids,scope)!=(p2,c2,s2) or (configured!=os.environ.get(ENV)):raise G.ErrorAgrupaciones(403,'El acceso cambió durante la lectura.')
 return {'version':VERSION,'estado':'copia_observada','sha256_candidato':SHA,'generado':iso(now),'corte_preparacion_utc':doc['corte_preparacion_utc'],'fuente':'clickup_cache_local','cobertura':'parcial','persona_ids':pids,'cliente_ids':cids,'filas':rows,'atribucion':'creador_ID_exacto','creacion_no_es_planificacion':True,'cumplimiento':None}
def enganchar(H,S):
 original=H._api_get
 def get(self,ruta,q,real,persona):
  if ruta!=RUTA:return original(self,ruta,q,real,persona)
  if q:return self.responder(400,{'error':'Esta consulta no admite parámetros.'})
  try:return self.responder(200,listar(S,real.get('id'),persona.get('id')))
  except G.ErrorAgrupaciones as e:return self.responder(e.codigo,{'error':str(e)})
 H._api_get=get
