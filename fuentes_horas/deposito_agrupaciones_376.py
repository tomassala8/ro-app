"""376 depósito mínimo privado. No agrega ni concede permisos; puro sin IO."""
import collections,datetime as dt,math,hashlib,json
from fuentes_horas.agrupaciones_artifact_375 import grupo_titulo,clave,instante
from fuentes_horas.historial_diario_359 import _instante
VERSION='376.1'
def uid(v):
 return str(v) if type(v) is int and v>0 else v if isinstance(v,str) and len(v)<=150 and v.isascii() and v.isdigit() and int(v)>0 and str(int(v))==v else None

def construir(horas,tareas,carpetas,identidades,nombres,ahora):
 if not isinstance(ahora,dt.datetime) or ahora.tzinfo is None or not isinstance(horas,dict) or not isinstance(horas.get('entradas'),list) or not isinstance(tareas,dict) or not isinstance(tareas.get('tareas'),list):raise ValueError('Fuentes explícitas')
 leido=_instante((horas.get('meta') or {}).get('generado'),'Europe/Madrid')
 if not leido or leido>ahora:raise ValueError('Lectura no acreditada')
 ts=tareas['tareas'];counts=collections.Counter(t.get('id') for t in ts if isinstance(t,dict) and clave(t.get('id')));out=[];diag=collections.Counter()
 for t in ts:
  if not isinstance(t,dict) or not clave(t.get('id')) or counts[t['id']]!=1:diag['tarea_identidad_invalida']+=1;continue
  lid=t.get('lista_id');folder=t.get('carpeta_id');ref=carpetas.get(str(folder)) if type(folder) in (str,int) else None
  cid=ref[0] if isinstance(ref,tuple) and len(ref)==2 else None
  if not clave(lid) or not clave(cid):diag['tarea_sin_cliente_lista_confirmados']+=1;continue
  g=grupo_titulo(t.get('nombre'),nombres)
  if not g:diag['grupo_protegido_o_vacio']+=1;continue
  out.append({'id':t['id'],'lista_id':lid,'carpeta_id':str(folder),'cliente_id':cid,'nombre':g})
 # Dedupe de todo el inventario ANTES de que ningún usuario/cliente recorte entradas.
 versions=collections.defaultdict(list)
 for e in horas['entradas']:
  if isinstance(e,dict) and clave(e.get('id')):versions[e['id']].append(e)
  else:diag['entrada_id_invalida']+=1
 es=[]
 for eid,xs in versions.items():
  fingerprints=[];normal=[]
  for e in xs:
   u=uid(e.get('usuario_id'));tid=e.get('task_id');stamp=instante(e.get('inicio'));h=e.get('horas')
   try:valid=type(h) in (int,float) and math.isfinite(h) and h>=0
   except OverflowError:valid=False
   if not u or not clave(tid) or not stamp or stamp>leido or not valid:fingerprints.append(None);continue
   row={'id':eid,'usuario_id':u,'task_id':tid,'inicio':stamp.astimezone(dt.timezone.utc).isoformat(),'horas':h}
   # tipo de h conserva diferencias entre versiones; no stringify de objetos.
   fingerprints.append((u,tid,row['inicio'],type(h).__name__,repr(h)));normal.append(row)
  if None in fingerprints or len(set(fingerprints))!=1:diag['entrada_colision_o_invalida']+=1;continue
  diag['replays_eliminados']+=len(xs)-1;es.append(normal[0])
 return {'version':VERSION,'sin_promover':True,'fuente':'clickup_cache_local','cobertura':'parcial','leido':leido.isoformat(),'corte':leido.isoformat(),'clasificacion':'orientativa_por_titulo','entradas':sorted(es,key=lambda e:e['id']),'tareas':sorted(out,key=lambda t:t['id']),
  'identidades':{u:p for u,p in identidades.items() if uid(u)==u and clave(p)},'diagnostico':dict(diag),'entradas_fuente':len(horas['entradas']),'sin_agregado_global':True,'dedup_global_antes_scope':True}
