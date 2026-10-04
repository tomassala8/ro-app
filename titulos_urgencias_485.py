"""485: títulos observados saneados; sólo overlay local bajo autoridad402."""
import hashlib,json,os,re,stat
from pathlib import Path
from collections import Counter
from contexto_tarea import texto_operativo
from identidad_generadores_212 import carpetas_confirmadas
from fuentes_produccion.urgencias_observadas_398 import instante,iso
ENV='RO_TITULOS_URGENCIAS_485'
SHA='790fbc685e8c2f51ef87b5306b436b3cc2d2a9de3e556893e8c999ff93bdd5ce'
MANIFEST_SHA='25418c3bf64ddace30ac1009666ec6037fdc2c993b320454cff90fd6ce7d751b'
KEYS={'tarea_id','lista_id','cliente_id','estado','estado_leido_utc','titulo','titulo_estado'}
def id_ok(v):return isinstance(v,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,150}',v) is not None

def titulo_seguro(v):
 if not isinstance(v,str):return None
 v=re.sub(r'https?://[^\s<>]+',' ',v,flags=re.I)
 v=' '.join(texto_operativo(v,1000).split())[:240]
 if not v or not re.sub(r'\[[^\]]*omitido\]','',v).strip():return None
 return v

def construir(raw,doc,documentos,source_sha,manifest_sha,raw_sha):
 if not isinstance(raw,dict) or not isinstance(raw.get('tareas'),list) or not isinstance(doc,dict) or not isinstance(doc.get('filas'),list):raise ValueError('Fuente inválida')
 folders,_=carpetas_confirmadas(documentos)
 by={};counts=Counter(t.get('id') for t in raw['tareas'] if isinstance(t,dict) and id_ok(t.get('id')))
 for t in raw['tareas']:
  if isinstance(t,dict) and id_ok(t.get('id')) and counts[t['id']]==1:by[t['id']]=t
 out=[];seen=set()
 for r in doc['filas']:
  if not isinstance(r,dict) or not all(id_ok(r.get(k)) for k in ('tarea_id','lista_id','cliente_id')) or r['tarea_id'] in seen:raise ValueError('Identidad ambigua')
  seen.add(r['tarea_id']);t=by.get(r['tarea_id']);stamp=instante(r.get('estado_leido_utc'))
  if not t or t.get('lista_id')!=r['lista_id'] or t.get('estado')!=r.get('estado') or t.get('estado_fuente')!='clickup' or stamp is None or instante(t.get('estado_leido_utc'))!=stamp or t.get('prioridad')!='urgent' or folders.get(str(t.get('carpeta_id')),(None,))[0]!=r['cliente_id']:raise ValueError('Join no acreditado')
  title=titulo_seguro(t.get('nombre'))
  out.append({**{k:r[k] for k in ('tarea_id','lista_id','cliente_id','estado')},'estado_leido_utc':iso(stamp),'titulo':title,'titulo_estado':'observado_saneado' if title else 'no_disponible'})
 return {'version':'485.1','fuente':'clickup_cache_local','promovido':False,'cobertura':'parcial','source_sha256':source_sha,'source_manifest_sha256':manifest_sha,'raw_sha256':raw_sha,'corte_preparacion_utc':doc['corte_preparacion_utc'],'filas':out}

def overlay(filas,*,source_sha,source_manifest_sha,raw_sha,corte,leer):
 """Sin opt-in devuelve campos desconocidos. No concede ámbito por título."""
 configured=os.environ.get(ENV);pins=(SHA,MANIFEST_SHA)
 def vacio(r):return dict(r,titulo=None,titulo_estado='no_disponible',titulo_fuente=None,titulo_leido_utc=None)
 if not configured:return [vacio(r) for r in filas],lambda:None
 def cargar():
  if configured!=os.environ.get(ENV) or pins!=(SHA,MANIFEST_SHA) or any(not isinstance(x,str) or not re.fullmatch('[0-9a-f]{64}',x) for x in pins):raise ValueError('Opt-in o pins cambiaron')
  p=Path(configured)
  if not p.is_absolute() or p.name!='candidato.json' or p.parent.is_symlink():raise ValueError('Depósito inválido')
  s=p.parent.lstat()
  if not stat.S_ISDIR(s.st_mode) or stat.S_IMODE(s.st_mode)!=0o700 or s.st_uid!=os.getuid():raise ValueError('Depósito no privado')
  manifest,_=leer(p.parent/'manifest.json',pins[1],2_000_000);d,_=leer(p,pins[0],2_000_000)
  if not isinstance(manifest,dict) or manifest.get('version')!='485.1' or manifest.get('candidato_sha256')!=pins[0] or manifest.get('lectura_no_concede_permiso') is not True or manifest.get('source_sha256')!=source_sha or manifest.get('source_manifest_sha256')!=source_manifest_sha or manifest.get('raw_sha256')!=raw_sha:raise ValueError('Manifest inválido')
  expected={'version':'485.1','fuente':'clickup_cache_local','promovido':False,'cobertura':'parcial','source_sha256':source_sha,'source_manifest_sha256':source_manifest_sha,'raw_sha256':raw_sha}
  if not isinstance(d,dict) or set(d)!=set(expected)|{'corte_preparacion_utc','filas'} or d.get('promovido') is not False or any(d.get(k)!=v for k,v in expected.items()) or instante(d.get('corte_preparacion_utc'))!=corte or not isinstance(d.get('filas'),list) or len(d['filas'])>20000:raise ValueError('Snapshot distinto')
  by={}
  for r in d['filas']:
   if not isinstance(r,dict) or set(r)!=KEYS or not all(id_ok(r.get(k)) for k in ('tarea_id','lista_id','cliente_id')) or r['tarea_id'] in by or not isinstance(r.get('estado'),str) or not r['estado'] or instante(r.get('estado_leido_utc')) is None:raise ValueError('Fila inválida')
   t=r['titulo']
   if r['titulo_estado']!=('observado_saneado' if t else 'no_disponible') or (t is not None and (not isinstance(t,str) or t!=titulo_seguro(t))):raise ValueError('Título no saneado')
   by[r['tarea_id']]=r
  if configured!=os.environ.get(ENV) or pins!=(SHA,MANIFEST_SHA):raise ValueError('Opt-in o pins cambiaron durante lectura')
  return by
 by=cargar();out=[]
 for r in filas:
  title=by.get(r['tarea_id'])
  if title is None or any(title.get(k)!=r.get(k) for k in ('tarea_id','lista_id','cliente_id','estado')) or instante(title['estado_leido_utc'])!=instante(r['estado_leido_utc']):raise ValueError('Título sin referencia exacta')
  out.append(dict(r,titulo=title['titulo'],titulo_estado=title['titulo_estado'],titulo_fuente='clickup_cache_local' if title['titulo'] else None,titulo_leido_utc=r['estado_leido_utc'] if title['titulo'] else None))
 def validar():
  if cargar()!=by:raise ValueError('Overlay cambió')
 return out,validar
