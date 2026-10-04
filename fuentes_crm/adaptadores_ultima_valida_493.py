"""493: adapta respuestas en memoria a490. No API/IO/import del generador.

El llamador acredita identidad, ventanas y paginación; este módulo no otorga
permisos ni deriva exhaustividad de la longitud de una página.
"""
import copy
from embudo_eventos import _hora
from fuentes_crm.ultima_valida_490 import VERSION,DEFINICIONES,DIMENSION,_id,_n,_epoch,_datos,_ventana,_validar_ventana_recurso,_fechas_datos,actualizar
TIPOS={'TYPE_CALL':'call','TYPE_CUSTOM_CALL':'call','TYPE_IVR_CALL':'call','TYPE_WHATSAPP':'whatsapp','TYPE_SMS':'sms','TYPE_CUSTOM_SMS':'sms','TYPE_CUSTOM_PROVIDER_SMS':'sms','TYPE_EMAIL':'email','TYPE_CUSTOM_EMAIL':'email','TYPE_CUSTOM_PROVIDER_EMAIL':'email'}
AUTOMATICOS=frozenset({'workflow','campaign','bulk_actions','bulk_action','automation','trigger'})

def _fecha(v):
 if v is None:return None
 if _epoch(v) and not isinstance(v,bool):return v
 d=_hora(v)
 if d is None:raise ValueError('Fecha de fila inválida')
 try:n=int(d.timestamp()*1000)
 except (OverflowError,ValueError,OSError):raise ValueError('Fecha de fila inválida')
 if not _epoch(n):raise ValueError('Fecha de fila inválida')
 return n

def _texto(v):return v.lower() if isinstance(v,str) else ''

def _error(r,status):
 if status is not None and (not isinstance(status,int) or isinstance(status,bool) or not 100<=status<=599):raise ValueError('Status inválido')
 if status in (401,403):return 'sin_acceso'
 if status==404:return 'no_encontrado'
 code=r.get('_error') if isinstance(r,dict) else None
 if code is not None:
  if isinstance(code,bool):return 'esquema_invalido'
  if isinstance(code,int):status=code
  elif isinstance(code,str):return 'timeout' if code=='timeout' else 'red' if code=='red' else 'esquema_invalido'
  else:return 'esquema_invalido'
 if status in (401,403):return 'sin_acceso'
 if status==404:return 'no_encontrado'
 if status==429:return 'limite'
 if status is not None and status>=500:return 'http_5xx'
 if status is not None and not 200<=status<=299:return 'esquema_invalido'
 return None

def _coherente(r,sid):
 # Sólo IDs presentes. Nunca deducir subcuenta a partir de títulos o datospersonales.
 for k in ('locationId','location_id'):
  if k in r and r[k]!=sid:raise ValueError('Subcuenta incoherente')

def _rows(recurso,r):
 if recurso=='mensajes':
  box=r.get('messages')
  if not isinstance(box,dict) or not isinstance(box.get('messages'),list):raise ValueError('Mensajes sin colección')
  return box['messages']
 key={'contactos':'contacts','calendarios':'calendars','citas':'events','oportunidades':'opportunities','oportunidades_abiertas':'opportunities','conversaciones':'conversations'}[recurso]
 if not isinstance(r.get(key),list):raise ValueError('Colección ausente')
 return r[key]

def _normalizar(recurso,row,sid,dim,clasificaciones,origenes):
 if not isinstance(row,dict) or not _id(row.get('id')):raise ValueError('Fila inválida')
 _coherente(row,sid);out={'id':row['id']}
 if recurso=='contactos':
  lead=clasificaciones.get(row['id'])
  if not isinstance(lead,bool):raise ValueError('Clasificación no acreditada')
  out.update(creado=_fecha(row.get('dateAdded')),es_lead=lead)
 elif recurso=='calendarios':
  if not isinstance(row.get('isActive'),bool):raise ValueError('Actividad no acreditada')
  out['activo']=row['isActive']
 elif recurso in ('citas','oportunidades','oportunidades_abiertas'):
  if not _id(row.get('contactId')):raise ValueError('Contacto inválido')
  if recurso=='citas':
   if 'calendarId' in row and row['calendarId']!=dim:raise ValueError('Calendario incoherente')
   if 'deleted' in row and not isinstance(row['deleted'],bool):raise ValueError('Borrado ambiguo')
   if row.get('deleted') is True:raise ValueError('Evento borrado requiere contrato separado')
   a,b=row.get('appointmentStatus'),row.get('appoinmentStatus')
   if a is not None and b is not None and a!=b:raise ValueError('Estado contradictorio')
   status=a if a is not None else b
   out.update(contacto=row['contactId'],creada=_fecha(row.get('dateAdded')),inicio=_fecha(row.get('startTime')),estado=_texto(status) or 'sin_estado')
  else:
   a,b=row.get('createdAt'),row.get('dateAdded')
   if a is not None and b is not None and _fecha(a)!=_fecha(b):raise ValueError('Creación contradictoria')
   out.update(contacto=row['contactId'],creada=_fecha(a if a is not None else b),estado=_texto(row.get('status')) or 'sin_estado')
 elif recurso=='conversaciones':
  if row.get('contactId')!=dim:raise ValueError('Contacto incoherente')
  out['contacto']=dim
 elif recurso=='mensajes':
  if 'conversationId' in row and row['conversationId']!=dim:raise ValueError('Conversación incoherente')
  source=_texto(row.get('source'))
  origen='automatico' if source in AUTOMATICOS else origenes.get(source,'desconocido')
  if origen not in ('humano','automatico','desconocido'):raise ValueError('Origen inválido')
  estado=_texto(row.get('status'))
  # Ausencia de estado no acredita envío; source desconocida no acredita humano.
  estado='fallido' if estado in ('failed','undelivered','bounced') else 'enviado' if estado in ('sent','delivered','read') else 'desconocido'
  direction=_texto(row.get('direction'))
  out.update(creado=_fecha(row.get('dateAdded')),direccion=direction if direction in ('inbound','outbound') else 'desconocida',tipo=TIPOS.get(row.get('messageType'),'otro') if isinstance(row.get('messageType'),str) else 'otro',origen=origen,estado=estado)
 return out

def adaptar(recurso,respuestas,*,subcuenta_id,dimension_id=None,intentado_en,observado_en=None,ventana=None,fin_paginacion=False,lectura_limitada=False,estados_http=None,clasificaciones=None,origenes=None):
 """Respuestasraw de g.req; una lista es la ronda de páginas del mismo recurso.

 fin_paginacion sólo True si acreditado por transporte/esquema del endpoint.
 lectura_limitada incluye cap3páginas, recorte150contactos/2conversaciones etc.
 Un fallo entre páginas no promueve una observación mixta; registra causa sinraw.
 """
 if not isinstance(recurso,str) or recurso not in DEFINICIONES or not _id(subcuenta_id) or (not _id(dimension_id) if recurso in DIMENSION else dimension_id is not None):raise ValueError('Identidad/recurso inválido')
 if not isinstance(respuestas,list) or not 1<=len(respuestas)<=100:raise ValueError('Páginas inválidas')
 if not isinstance(fin_paginacion,bool) or not isinstance(lectura_limitada,bool):raise ValueError('Cobertura inválida')
 when,obs=_hora(intentado_en),_hora(observado_en)
 if when is None or (observado_en is not None and (obs is None or obs>when)):raise ValueError('Lectura inválida')
 if obs is not None:_validar_ventana_recurso(recurso,_ventana(ventana),obs)
 if estados_http is None:estados_http=[None]*len(respuestas)
 if not isinstance(estados_http,list) or len(estados_http)!=len(respuestas):raise ValueError('Status inválido')
 clasificaciones={} if clasificaciones is None else clasificaciones;origenes={} if origenes is None else origenes
 if not isinstance(clasificaciones,dict) or not isinstance(origenes,dict):raise ValueError('Catálogo inválido')
 e={'version':VERSION,'subcuenta_id':subcuenta_id,'recurso':recurso,'dimension_id':dimension_id,'definicion':DEFINICIONES[recurso],'resultado':'ok','intentado_en':when.isoformat(),'observado_en':obs.isoformat() if obs is not None else None,'ventana':copy.deepcopy(ventana),'cobertura':None,'datos':None,'codigo_error':None}
 error=None;data=[];seen=set()
 try:
  for r,status in zip(respuestas,estados_http):
   error=_error(r,status)
   if error:break
   if not isinstance(r,dict):raise ValueError('Respuesta inválida')
   _coherente(r,subcuenta_id)
   if recurso=='contactos_total':
    if len(respuestas)!=1 or not _n(r.get('total')):raise ValueError('Total inválido')
    data={'total':r['total']};continue
   rows=_rows(recurso,r)
   if len(rows)>10000:raise ValueError('Página excesiva')
   for raw in rows:
    row=_normalizar(recurso,raw,subcuenta_id,dimension_id,clasificaciones,origenes)
    if row['id'] in seen:raise ValueError('Duplicado de páginas')
    seen.add(row['id']);data.append(row)
   if len(data)>10000:raise ValueError('Colección excesiva')
 except (ValueError,TypeError,OverflowError):error='esquema_invalido'
 if error is None and obs is None:error='esquema_invalido'
 if error:
  e.update(resultado='denegado' if error in ('sin_acceso','no_encontrado') else 'error',observado_en=None,codigo_error=error)
 else:
  if not _datos(recurso,data) or not _fechas_datos(recurso,data,_ventana(ventana),obs):
   e.update(resultado='error',observado_en=None,codigo_error='esquema_invalido')
   actualizar({'version':VERSION,'recursos':{}},[e],when.isoformat())
   return e
  capped=(recurso in ('contactos','oportunidades','oportunidades_abiertas') and len(respuestas)>=3) or (recurso=='conversaciones' and len(data)>=5) or (recurso=='mensajes' and len(data)>=100)
  complete=fin_paginacion and not lectura_limitada and not capped
  empty=(not data) if isinstance(data,list) else data['total']==0
  e.update(datos=data,cobertura={'completa':complete,'paginas_leidas':len(respuestas),'fin_paginacion':fin_paginacion,'vacio_confirmado':empty and complete})
 # Acredita contrato490 con la mismavalidaciónpura; no IO y sin fechasglobales.
 actualizar({'version':VERSION,'recursos':{}},[e],when.isoformat())
 return e
