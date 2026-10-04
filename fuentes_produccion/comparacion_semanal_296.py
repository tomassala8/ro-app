"""Comparación adicional pura: creación por creador y finales por proyecto.
No sustituye la columna original «Semana pasada» (rompen); no red/IO.
"""
from collections import Counter,defaultdict
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from .estados_catalogo import resolver_estado

MADRID=ZoneInfo('Europe/Madrid')
def ident(v):
 return str(v) if isinstance(v,(str,int)) and not isinstance(v,bool) and str(v) else None

def instante_ms(v):
 if isinstance(v,bool) or not isinstance(v,(int,str)) or not str(v).isdigit():return None
 try:return datetime.fromtimestamp(int(v)/1000,timezone.utc) if int(v)>0 else None
 except (ValueError,OverflowError,OSError):return None

def iso(v):return v.astimezone(timezone.utc).isoformat().replace('+00:00','Z')

def construir(raw,catalogo,carpetas,activos,identidades,personas_activas,corte,ahora):
 if not isinstance(corte,datetime) or corte.tzinfo is None or not isinstance(ahora,datetime) or ahora.tzinfo is None or corte>ahora:raise ValueError('Corte válido no futuro requerido')
 if not isinstance(raw,dict) or not isinstance(raw.get('tareas'),list) or not isinstance(catalogo,dict) or not isinstance(carpetas,dict) or not isinstance(identidades,dict) or not isinstance(activos,set) or not isinstance(personas_activas,set):raise ValueError('Fuentes/ámbito inválidos')
 local=corte.astimezone(MADRID);lunes=(local-timedelta(days=local.weekday())).replace(hour=0,minute=0,second=0,microsecond=0);anterior=lunes-timedelta(days=7)
 ventanas={}
 for key,start,end,inclusiva in [('actual',lunes,corte,True),('anterior',anterior,lunes,False)]:
  ventanas[key]={'desde_utc':iso(start),'hasta_utc':iso(end),'hasta_inclusiva':inclusiva,'desde_madrid':start.astimezone(MADRID).isoformat(),'hasta_madrid':end.astimezone(MADRID).isoformat(),'zona':'Europe/Madrid','cobertura':'parcial'}
 def periodo(v):return 'actual' if lunes<=v<=corte else 'anterior' if anterior<=v<lunes else None
 def metrica(n,campo,p,atribucion):return {'valor':n if n else None,'observaciones':n,'campo':campo,'ventana':p,'atribucion':atribucion,'cobertura':'parcial','cero_no_acredita_ausencia':True}
 ts=raw['tareas'];counts=Counter(ident(t.get('id')) for t in ts if isinstance(t,dict));by=defaultdict(Counter);autores=defaultdict(Counter);diag=Counter()
 for t in ts:
  tid=ident(t.get('id')) if isinstance(t,dict) else None
  if tid is None or counts[tid]!=1:diag['tarea_ID_ausente_duplicado']+=1;continue
  ref=carpetas.get(ident(t.get('carpeta_id')));cid=ref[0] if isinstance(ref,tuple) and len(ref)==2 and isinstance(ref[0],str) else None
  if cid not in activos:diag['sin_carpeta_cliente_ACT_unico']+=1;continue
  by[cid] # Conserva proyecto observado aunque no haya eventos en esas ventanas.
  cr=instante_ms(t.get('creada'));cl=instante_ms(t.get('cerrada'))
  if cr is None or cr>corte:diag['creacion_invalida_futura']+=1;continue
  p=periodo(cr)
  if p:
   by[cid]['creadas_'+p]+=1;pid=identidades.get(ident(t.get('creador')))
   if isinstance(pid,str) and pid in personas_activas:autores[cid,pid][p]+=1
   else:diag['creador_no_canonico_activo']+=1
  if cl is not None:
   est=resolver_estado(t,catalogo)
   if cl<cr or cl>corte or not est['determinado'] or not est['final_flujo']:diag['cierre_incoherente_o_catalogo_no_terminal']+=1;continue
   p=periodo(cl)
   if p:by[cid]['finales_'+p]+=1
 # No usa historial agregado, asignados, títulos, tags, orden o updatedAt para clasificar.
 proyectos=[]
 for cid,x in sorted(by.items()):
  proyectos.append({'cliente_id':cid,'creadas':{p:metrica(x['creadas_'+p],'date_created',p,'proyecto') for p in ventanas},'finales':{p:metrica(x['finales_'+p],'date_done_or_closed+catalogo_actual_terminal',p,'proyecto') for p in ventanas},'actor_cierre':None,'aceptacion_entrega':None})
 creadores=[{'cliente_id':cid,'persona_id':pid,'creadas':{p:metrica(x[p],'date_created+creator_ID_canonico',p,'creador')for p in ventanas},'al_planning':None,'fuegos_directos':None,'rompen_semanal':None}for(cid,pid),x in sorted(autores.items())]
 return {'version':'296.1','referencia_pipeline':'275.1','fuente':'clickup_cache_local','fuente_corte_original':raw.get('meta',{}).get('generado'),'corte_utc':iso(corte),'ventanas':ventanas,'cobertura':'parcial','proyectos':proyectos,'creadores':creadores,'diagnosticos':dict(diag),'columna_original_semana_pasada':'rompen_semanal;no_sustituir_por_creaciones','historia_transiciones_confirmada':False,'comparacion_rendimiento':None,'promovido':False}
