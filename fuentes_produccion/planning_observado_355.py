"""355 inventario observado de estados planning/backlog. Puro, sin IO ni permisos nuevos."""
from collections import Counter
from datetime import datetime,timezone
import math,re
from .estados_catalogo import resolver_estado
VERSION='355.1'
ESTADOS=frozenset({'backlog','planning mensual'})
def clave(v):
 if type(v) is int and v>0:return str(v)
 return v if isinstance(v,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,150}',v) else None
def instante(v):
 if not isinstance(v,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})',v):return None
 try:
  d=datetime.fromisoformat(v.replace('Z','+00:00'))
  return d if d.tzinfo is not None else None
 except ValueError:return None
def iso(d):return d.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
def fecha_ms(v):
 if v is None:return None,'sin_dato'
 if isinstance(v,bool) or not isinstance(v,(int,str)) or not str(v).isdigit():return None,'invalida'
 try:
  n=int(v)
  if n<=0:return None,'invalida'
  return iso(datetime.fromtimestamp(n/1000,timezone.utc)),'observada'
 except (OverflowError,OSError,ValueError):return None,'invalida'
def construir(raw,catalogo,carpetas,activos,identidades,personas_activas,ahora):
 if not isinstance(ahora,datetime) or ahora.tzinfo is None:raise ValueError('Hora explícita consciente requerida')
 if not isinstance(raw,dict) or not isinstance(raw.get('tareas'),list) or not isinstance(catalogo,dict) or not isinstance(carpetas,dict) or not isinstance(activos,set) or not isinstance(personas_activas,set) or not isinstance(identidades,dict):raise ValueError('Fuentes inválidas')
 ts=raw['tareas'];counts=Counter(clave(t.get('id')) for t in ts if isinstance(t,dict));diag=Counter();out=[]
 for t in ts:
  if not isinstance(t,dict):diag['fila_invalida']+=1;continue
  # Etiquetas exactas sólo seleccionan inventario: el tipo depende de la lista exacta.
  if not isinstance(t.get('estado'),str) or t['estado'] not in ESTADOS:continue
  tid=clave(t.get('id'));lid=t.get('lista_id');fid=clave(t.get('carpeta_id'))
  if tid is None or counts[tid]!=1 or not isinstance(lid,str) or clave(lid)!=lid:diag['identidad_tarea_lista_invalida']+=1;continue
  ref=carpetas.get(fid);cid=ref[0] if isinstance(ref,tuple) and len(ref)==2 else None
  if not isinstance(cid,str) or clave(cid)!=cid or cid not in activos:diag['cliente_no_ACT_canonico']+=1;continue
  state=resolver_estado(t,catalogo)
  if not state['determinado'] or state['final_flujo'] or t.get('tipo_estado')!=state['tipo']:diag['tipo_estado_no_confirmado']+=1;continue
  lectura=instante(t.get('estado_leido_utc'))
  if t.get('estado_fuente')!='clickup' or lectura is None or lectura>ahora:diag['lectura_estado_no_acreditada']+=1;continue
  assigned=t.get('asignados');owners=set();uids=set();invalid=False;unknown=0
  if not isinstance(assigned,list):assigned=[];unknown=1
  for a in assigned:
   uid=clave(a.get('id')) if isinstance(a,dict) else None
   if uid is None or uid in uids:invalid=True;break
   uids.add(uid);pid=identidades.get(uid)
   if isinstance(pid,str) and clave(pid)==pid and pid in personas_activas:owners.add(pid)
   else:unknown+=1
  if invalid:diag['asignacion_malformada_duplicada']+=1;continue
  inicio,ei=fecha_ms(t.get('inicio'));vence,ev=fecha_ms(t.get('vence'))
  ms=t.get('estimacion_ms');estimate=ms if type(ms) in (int,float) and math.isfinite(ms) and ms>0 else None
  out.append({'tarea_id':tid,'cliente_id':cid,'lista_id':lid,'estado':t['estado'],'tipo_estado':state['tipo'],
   'estado_fuente':'clickup','estado_leido_utc':iso(lectura),'asignados_persona_ids':sorted(owners),'asignacion_estado':'parcial' if unknown else 'observada','asignados_sin_identidad_confirmada':unknown,
   'inicio_utc':inicio,'inicio_estado':ei,'vence_utc':vence,'vence_estado':ev,'estimacion':{'valor':estimate,'unidad':'milisegundos','estado':'observada' if estimate is not None else 'sin_dato'},
   'cobertura':'parcial','actor_historico':None,'estado_inicial':None,'rompe_semanal':None,'fuego_confirmado':None})
 return {'version':VERSION,'fuente':'clickup_cache_local','cobertura':'parcial','promovido':False,'filas':sorted(out,key=lambda r:r['tarea_id']),
  'resumen':{'filas_fuente':len(ts),'filas_observadas':len(out),'rechazos':dict(diag)},'alcance':'cliente_ACT_carpeta_confirmada;asignados_correo_ID_confirmado;lectura_no_concede_permiso',
  'clasificacion_historia':False,'cumplimiento':None,'cero_no_acredita_ausencia':True}
