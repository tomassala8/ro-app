"""438 ejemplos del creador exacto, no historia de planificación. Puro/sin IO."""
from collections import Counter
from contexto_tarea import texto_operativo
from .planning_observado_395 import construir as planning,clave,instante,fecha_ms,iso
VERSION='438.1'
CAMPOS=frozenset({'tarea_id','cliente_id','lista_id','persona_id','creada_utc','estado_observado','tipo_estado','estado_leido_utc','titulo_saneado','creador_usuario_id'})
def construir(raw,catalogo,carpetas,activos,identidades,personas_activas,ahora):
 base=planning(raw,catalogo,carpetas,activos,identidades,personas_activas,ahora)
 counts=Counter(clave(t.get('id')) for t in raw['tareas'] if isinstance(t,dict))
 index={clave(t.get('id')):t for t in raw['tareas'] if isinstance(t,dict) and counts[clave(t.get('id'))]==1}
 out=[];rechazos=Counter()
 for r in base['filas']:
  t=index[r['tarea_id']];creator=clave(t.get('creador'));pid=identidades.get(creator)
  if not isinstance(pid,str) or clave(pid)!=pid or pid not in personas_activas:rechazos['creador_sin_identidad_activa']+=1;continue
  creada,estado=fecha_ms(t.get('creada'))
  if estado!='observada' or instante(creada)>instante(r['estado_leido_utc']):rechazos['fecha_creacion_no_acreditada']+=1;continue
  label=texto_operativo(t.get('nombre'),240)
  # El título es opcional, nunca identidad/autoridad y no incluye enlaces externos.
  import re
  label=re.sub(r'https?://\S+','[enlace omitido]',label,flags=re.I)
  label=label.replace('<','‹').replace('>','›')
  out.append({'tarea_id':r['tarea_id'],'cliente_id':r['cliente_id'],'lista_id':r['lista_id'],'persona_id':pid,'creador_usuario_id':creator,'creada_utc':creada,'estado_observado':r['estado'],'tipo_estado':r['tipo_estado'],'estado_leido_utc':r['estado_leido_utc'],'titulo_saneado':label})
 return {'version':VERSION,'fuente':'clickup_cache_local','cobertura':'parcial','sin_promover':True,'atribucion':'creador_ID_exacto','creacion_no_es_planificacion':True,'corte_preparacion_utc':iso(ahora),'filas':out,'resumen':{'planning_observado':len(base['filas']),'ejemplos':len(out),'rechazos':dict(rechazos)},'cumplimiento':None}
