"""219: proyección de metadatos locales autorizados. Sin proveedor ni escrituras."""
from collections import Counter
from datetime import datetime,timezone
import re
from identidades_clickup_204 import actor_autorizado
from transiciones_mi_trabajo import tarea_unica,instante_utc
ID=re.compile(r'^[A-Za-z0-9_-]{1,120}$')
RUTA='/api/mi_trabajo/metadatos'

def identificador(v):
 return v if isinstance(v,str) and ID.fullmatch(v) else None

def conteo(v):return isinstance(v,int) and not isinstance(v,bool) and v>=0

def cubre(cov,n):
 return all(conteo(cov.get(k)) and cov[k]==n for k in ('leidos','observados'))

def proyectar(raw,ahora):
 """Sólo IDs y bool ya preservados172. No nombres, vínculos ni campos privados."""
 meta=raw.get('metadata_cobertura') if isinstance(raw.get('metadata_cobertura'),dict) else {}
 xs=raw.get('checklists');original=meta.get('checklists',{})
 original=original if isinstance(original,dict) else {}
 listas=[];total=hechos=0;items_completos=True
 valido=isinstance(xs,list) and original.get('estado') in ('observado','parcial')
 if valido:
  lote=xs[:100];ids=Counter(identificador(c.get('id')) if isinstance(c,dict) else None for c in lote)
  for c in lote:
   cid=identificador(c.get('id')) if isinstance(c,dict) else None
   if not cid or ids[cid]!=1:items_completos=False;continue
   its=c.get('items');ic=c.get('items_cobertura');ic=ic if isinstance(ic,dict) else {}
   observados=[];completo=isinstance(its,list) and ic.get('estado')=='observado'
   if isinstance(its,list):
    entradas=its[:1000];n=Counter(identificador(i.get('id')) if isinstance(i,dict) else None for i in entradas)
    for i in entradas:
     iid=identificador(i.get('id')) if isinstance(i,dict) else None
     if not iid or n[iid]!=1 or not isinstance(i.get('resolved'),bool):completo=False;continue
     observados.append({'id':iid,'resuelto':i['resolved']})
    completo=completo and len(observados)==len(its) and cubre(ic,len(its))
   else:completo=False
   h=sum(i['resuelto'] for i in observados);total+=len(observados);hechos+=h;items_completos=items_completos and completo
   listas.append({'id':cid,'items':observados,'items_observados':len(observados),'resueltos_observados':h,
    'total_confirmado':len(observados) if completo else None,'cobertura':'observado' if completo else 'parcial_o_desconocida',
    'titulo':None,'titulo_estado':'no_preservado_en_copia'})
 completa=valido and original.get('estado')=='observado' and len(listas)==len(xs) and cubre(original,len(xs))
 estado='observado' if completa and items_completos else 'parcial' if valido else 'sin_dato'
 fecha=instante_utc(raw.get('estado_leido_utc')) if raw.get('estado_fuente')=='clickup' else None
 if fecha and fecha>ahora:fecha=None
 def cuenta(k):
  cov=meta.get(k);cov=cov if isinstance(cov,dict) else {};datos=raw.get(k)
  ok=isinstance(datos,list) and len(datos)<=200 and cov.get('estado')=='observado' and cubre(cov,len(datos))
  ids=[identificador(v.get('id')) if isinstance(v,dict) else None for v in datos] if ok else []
  ok=ok and None not in ids and len(set(ids))==len(ids)
  return {'estado':'observado' if ok else 'sin_dato','cantidad':len(datos) if ok else None}
 return {'tarea_id':raw['id'],'lista_id':raw['lista_id'],'fuente':'copia_local_clickup','cobertura_exhaustiva':False,
  'estado_leido_utc':fecha.isoformat() if fecha else None,'fecha_metadata_estado':'lectura_tarea' if fecha else 'sin_fecha_acreditada',
  'checklists':{'estado':estado,'listas':listas,'listas_observadas':len(listas) if valido else None,
   'items_observados':total if valido else None,'resueltos_observados':hechos if valido else None,
   'total_confirmado':total if estado=='observado' else None,'todos_resueltos':hechos==total if estado=='observado' and total>0 else None},
  'entregable':{'estado':'sin_dato','motivo':'campo_semantico_y_valor_no_verificados','url':None},
  'adjuntos':cuenta('attachments'),'seguidores':cuenta('watchers'),
  'aviso':'Copia local: checklist resuelta no acredita entrega ni aceptación. No se muestran enlaces privados.'}

def get_metadatos(h,q,real,vista,M,*,ahora=None):
 """GET sólo tarea exacta. Reusa fuentes204 y políticas actuales; sin datos navegador."""
 if not isinstance(q,dict) or set(q)!={'tarea'} or not isinstance(q['tarea'],list) or len(q['tarea'])!=1 or not isinstance(q['tarea'][0],str) or not re.fullmatch(r'[A-Za-z0-9_-]{3,40}',q['tarea'][0]):
  return h.responder(400,{'error':'La consulta requiere únicamente una tarea válida.'})
 if M.S.E.nucleo_bloqueado:return h.responder(503,{'error':'La fuente local no está disponible.'})
 try:
  tid=q['tarea'][0]
  from fuentes_verdad import clientes_activos as ACT
  def puerta(indice=None):
   #226: snapshots de identidad/módulo/ACT no sobreviven a la lectura de fuente.
   if M.S.E.nucleo_bloqueado:raise PermissionError()
   crudo=M.S.E.crudo;ps=crudo.get('personas') or [];clientes=crudo.get('clientes') or []
   actors=[]
   for a in (real,vista):
    filas=[p for p in ps if isinstance(p,dict) and p.get('id')==a.get('id')]
    if len(filas)!=1 or filas[0].get('estado')!='activo' or filas[0].get('activo') is False:raise PermissionError()
    actors.append(filas[0])
   if not all(M.S.ve_alguno(p,[M.MODULO]) for p in actors):raise PermissionError()
   fila=tarea_unica(M.doc(),tid);cid=fila.get('cli')
   if not isinstance(cid,str) or len([c for c in clientes if isinstance(c,dict) and c.get('id')==cid])!=1 or ACT.es_activo_id(cid) is not True:raise PermissionError()
   for p in actors:
    if not M.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},M.P.contexto(p,crudo))['ok']:raise PermissionError()
    if indice is not None and not actor_autorizado(p,fila,indice):raise PermissionError()
   return fila,cid
  puerta()
  indice=M._fuente_autorizacion_tareas()
  fila,cid=puerta(indice)
  raw=indice['tareas'][tid][0]
  out=proyectar(raw,ahora or datetime.now(timezone.utc));out['cliente_id']=cid
  # Documento cache222 compartido sólo lectura: una rotación produce otra fila.
  # Se reconstruyen identidades/config actuales; no se conserva permiso del índice.
  final=M._fuente_autorizacion_tareas()
  _,cid_final=puerta(final)
  if final['tareas'][tid][0] is not raw or cid_final!=cid:raise PermissionError()
  return h.responder(200,out)
 except (PermissionError,ValueError,KeyError,TypeError,AttributeError,IndexError):
  return h.responder(404,{'error':'Esta tarea no está disponible en tu contexto autorizado.'})
