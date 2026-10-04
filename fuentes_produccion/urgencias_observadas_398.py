"""398 prioridad urgent literal observada en copia; nunca fuego actual sin lectura conjunta. Puro, sin IO ni permisos nuevos."""
from collections import Counter
from datetime import datetime,timezone
import math,re
from .estados_catalogo import resolver_estado
VERSION='398.1'
PRIORIDAD='urgent'
def clave(v):
 if type(v) is int and 0<v<10**150:return str(v)
 return v if isinstance(v,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,150}',v) else None
def instante(v):
 if not isinstance(v,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})',v):return None
 if v[-1]!='Z':
  hh,mm=map(int,v[-5:].split(':'))
  if mm>59 or hh>14 or (hh==14 and mm!=0):return None
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
def construir(raw,catalogo,carpetas,activos,ahora):
 if not isinstance(ahora,datetime) or ahora.tzinfo is None:raise ValueError('Hora explícita consciente requerida')
 if not isinstance(raw,dict) or not isinstance(raw.get('tareas'),list) or not isinstance(catalogo,dict) or not isinstance(carpetas,dict) or not isinstance(activos,set):raise ValueError('Fuentes inválidas')
 ts=raw['tareas'];counts=Counter(clave(t.get('id')) for t in ts if isinstance(t,dict));diag=Counter();out=[]
 for t in ts:
  if not isinstance(t,dict):diag['fila_invalida']+=1;continue
  # Etiquetas exactas sólo seleccionan inventario: el tipo depende de la lista exacta.
  if t.get('prioridad')!=PRIORIDAD:continue
  if not isinstance(t.get('estado'),str):diag['estado_ausente']+=1;continue
  tid=clave(t.get('id'));lid=t.get('lista_id');fid=clave(t.get('carpeta_id'))
  if tid is None or counts[tid]!=1 or not isinstance(lid,str) or clave(lid)!=lid:diag['identidad_tarea_lista_invalida']+=1;continue
  ref=carpetas.get(fid);cid=ref[0] if isinstance(ref,tuple) and len(ref)==2 else None
  if not isinstance(cid,str) or clave(cid)!=cid or cid not in activos:diag['cliente_no_ACT_canonico']+=1;continue
  state=resolver_estado(t,catalogo)
  if not state['determinado'] or t.get('tipo_estado')!=state['tipo']:diag['tipo_estado_no_confirmado']+=1;continue
  lectura=instante(t.get('estado_leido_utc'))
  if t.get('estado_fuente')!='clickup' or lectura is None or lectura>ahora:diag['lectura_estado_no_acreditada']+=1;continue
  inicio,ei=fecha_ms(t.get('inicio'));vence,ev=fecha_ms(t.get('vence'))
  creada,ec=fecha_ms(t.get('creada'));cerrada,ef=fecha_ms(t.get('cerrada'))
  if creada and instante(creada)>ahora:creada,ec=None,'invalida'
  if cerrada and instante(cerrada)>ahora:cerrada,ef=None,'invalida'
  if not state['final_flujo']:cerrada,ef=None,'no_aplica'
  out.append({'tarea_id':tid,'cliente_id':cid,'lista_id':lid,'prioridad':'urgent','estado':t['estado'],'tipo_estado':state['tipo'],
   'estado_fuente':'clickup','estado_leido_utc':iso(lectura),
   'prioridad_fuente':'clickup_cache_literal','prioridad_leida_utc':None,'verificacion_conjunta':False,'medicion_urgencia':None,
   'final_flujo_en_copia':state['final_flujo'],'clasificacion':'final_en_copia_no_reabrir' if state['final_flujo'] else 'abierta_en_copia_por_contrastar',
   'es_fuego_actual':None,'inicio_utc':inicio,'inicio_estado':ei,'vence_utc':vence,'vence_estado':ev,
   'creada_utc':creada,'creada_estado':ec,'cerrada_utc':cerrada,'cerrada_estado':ef,
   'cobertura':'parcial','actor_historico':None,'inicio_urgencia_utc':None,'ejecucion_verificada':False,'aceptacion_verificada':False})
 ordenadas=sorted(out,key=lambda r:r['tarea_id'])
 return {'version':VERSION,'fuente':'clickup_cache_local','cobertura':'parcial','promovido':False,'corte_preparacion_utc':iso(ahora),
  'prioridad_seleccionada':'urgent','descriptor_conjunto_disponible':False,'urgencias_actuales':None,
  'lecturas_estado':{'desde':iso(min(instante(r['estado_leido_utc']) for r in out)) if out else None,'hasta':iso(max(instante(r['estado_leido_utc']) for r in out)) if out else None,'no_rejuvenecido':True},
  'filas':ordenadas,'abiertas_en_copia_ids':[r['tarea_id'] for r in ordenadas if not r['final_flujo_en_copia']],
  'finales_en_copia_ids':[r['tarea_id'] for r in ordenadas if r['final_flujo_en_copia']],
  'resumen':{'filas_fuente':len(ts),'filas_observadas':len(out),'abiertas_en_copia':sum(not r['final_flujo_en_copia'] for r in out),'finales_en_copia':sum(r['final_flujo_en_copia'] for r in out),'rechazos':dict(diag)},
  'alcance':'cliente_ACT_carpeta_confirmada;lectura_no_concede_permiso','clasificacion_historia':False,'cumplimiento':None,'cero_no_acredita_ausencia':True}
