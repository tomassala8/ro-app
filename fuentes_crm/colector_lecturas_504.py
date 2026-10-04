"""504: colector PURO de consultas de servicio y resultados en memoria.

No autoriza acceso privado ni llama al proveedor/FS.499 sólo autoriza agregado.
Rawpayload temporal no debe registrarse/serializarse; cerrar genera args493.
"""
import copy
from datetime import datetime,timedelta,timezone
from embudo_eventos import _hora
from fuentes_crm.ultima_valida_490 import _id,_n,_ventana
from fuentes_crm.adaptadores_ultima_valida_493 import adaptar,_fecha
VERSION='504.1'
Q={'version','recurso','subcuenta_id','dimension_id','metodo','ruta','parametros','pagina','limite','emitida_en','ventana_contexto'}
T={'estado_http','resultado','payload','terminado_en','observado_en'}
RECURSOS={'contactos','contactos_total','calendarios','citas','conversaciones','mensajes','oportunidades_abiertas'}

def _igual(a,b):
 # Python True==1 no debe validar parámetros numéricos.
 if type(a) is not type(b):return False
 if isinstance(a,dict):return set(a)==set(b) and all(_igual(a[k],b[k]) for k in a)
 if isinstance(a,list):return len(a)==len(b) and all(_igual(x,y) for x,y in zip(a,b))
 return a==b

def _iso_ms(n):
 if not _n(n) or n>253402300799999:raise ValueError('Fecha de consulta inválida')
 try:return (datetime(1970,1,1,tzinfo=timezone.utc)+timedelta(milliseconds=n)).isoformat()
 except (ValueError,OverflowError,OSError):raise ValueError('Fecha de consulta inválida') from None

def _consulta(q):
 if not isinstance(q,dict) or set(q)!=Q or q['version']!=VERSION or not isinstance(q['recurso'],str) or q['recurso'] not in RECURSOS or not _id(q['subcuenta_id']) or not _n(q['pagina']) or q['pagina']<1 or _hora(q['emitida_en']) is None:raise ValueError('Consulta inválida')
 r,sid,dim=q['recurso'],q['subcuenta_id'],q['dimension_id'];p=q['parametros'];page=q['pagina'];limit=q['limite']
 if not isinstance(p,dict):raise ValueError('Parámetros inválidos')
 if r in ('citas','conversaciones','mensajes'):
  if not _id(dim):raise ValueError('Dimensión inválida')
 elif dim is not None:raise ValueError('Dimensión inesperada')
 if r=='contactos_total':method,path,size='POST','/contacts/search',1;wanted={'locationId':sid,'pageLimit':1}
 elif r=='contactos':
  try:gte=p['filters'][0]['value']['gte']
  except (KeyError,IndexError,TypeError):raise ValueError('Filtro de contactos inválido') from None
  if _hora(gte) is None or _hora(gte)>_hora(q['emitida_en']):raise ValueError('Filtro de contactos inválido')
  method,path,size='POST','/contacts/search',100
  wanted={'locationId':sid,'pageLimit':100,'page':page,'filters':[{'field':'dateAdded','operator':'range','value':{'gte':gte}}],'sort':[{'field':'dateAdded','direction':'desc'}]}
 elif r=='calendarios':method,path,size='GET','/calendars/',None;wanted={'locationId':sid}
 elif r=='citas':
  a,b=p.get('startTime'),p.get('endTime')
  _iso_ms(a);_iso_ms(b)
  if a>b:raise ValueError('Intervalo de citas inválido')
  method,path,size='GET','/calendars/events',None;wanted={'locationId':sid,'calendarId':dim,'startTime':a,'endTime':b}
 elif r=='conversaciones':method,path,size='GET','/conversations/search',5;wanted={'locationId':sid,'contactId':dim,'limit':5}
 elif r=='mensajes':method,path,size='GET',f'/conversations/{dim}/messages',100;wanted={'limit':100}
 else:method,path,size='GET','/opportunities/search',100;wanted={'location_id':sid,'status':'open','limit':100,'page':page}
 if q['metodo']!=method or q['ruta']!=path or not _igual(limit,size) or not _igual(p,wanted):raise ValueError('Identidad de consulta incoherente')
 if r in ('contactos','oportunidades_abiertas'):
  if page>3:raise ValueError('Página fuera de lector actual')
 elif page!=1:raise ValueError('Página inesperada')
 context=_ventana(q['ventana_contexto'])
 if r=='mensajes':
  if context is None or context['tipo']!='medicion_pasada' or _hora(context['hasta'])>_hora(q['emitida_en']):raise ValueError('Contexto de mensajes inválido')
 elif context is not None:raise ValueError('Contexto inesperado')
 return copy.deepcopy(q)

def registrar(consulta,resultado,ahora):
 """Captura respuesta/metadata privada en memoria. Sin grant ni timestampinventado."""
 q=_consulta(consulta);now=_hora(ahora)
 if now is None or _hora(q['emitida_en'])>now or not isinstance(resultado,dict) or set(resultado)!=T:raise ValueError('Resultado inválido')
 t=resultado;status=t['estado_http'];kind=t['resultado'];end=_hora(t['terminado_en']);obs=_hora(t['observado_en'])
 if status is not None and (not isinstance(status,int) or isinstance(status,bool) or not 100<=status<=599):raise ValueError('Status inválido')
 if not isinstance(kind,str) or kind not in ('json','red','timeout','json_invalido') or end is None or not _hora(q['emitida_en'])<=end<=now:raise ValueError('Fechas de transporte inválidas')
 if t['observado_en'] is not None and (obs is None or not _hora(q['emitida_en'])<=obs<=end):raise ValueError('Observación inválida')
 # Denegación HTTP conocida prevalece aunque body/status de parse se contradiga.
 if status is not None and status>=300:payload={'_error':status};obs=None
 elif kind!='json':
  if t['payload'] is not None or t['observado_en'] is not None:raise ValueError('Fallo con payload ambiguo')
  payload={'_error':status if status is not None and status>=400 else kind if kind in ('red','timeout') else 'esquema_invalido'}
 else:
  if not isinstance(t['payload'],dict):payload={'_error':'esquema_invalido'};obs=None
  elif '_error' in t['payload']:
   code=t['payload']['_error']
   allowed=(isinstance(code,int) and not isinstance(code,bool) and 100<=code<=599) or (isinstance(code,str) and code in ('red','timeout','esquema_invalido'))
   payload={'_error':code if allowed else 'esquema_invalido'};obs=None
  elif obs is None:payload={'_error':'esquema_invalido'}
  else:payload=copy.deepcopy(t['payload'])
 return {'version':VERSION,'consulta':q,'transporte':{'estado_http':status,'respuesta':payload,'terminado_en':end.isoformat(),'observado_en':obs.isoformat() if obs else None}}

def _ventana_captura(c):
 q,t=c['consulta'],c['transporte'];r=q['recurso']
 if r=='contactos':return {'tipo':'medicion_pasada','desde':q['parametros']['filters'][0]['value']['gte'],'hasta':t['observado_en'] or t['terminado_en']}
 if r=='citas':return {'tipo':'inventario_programado','desde':_iso_ms(q['parametros']['startTime']),'hasta':_iso_ms(q['parametros']['endTime'])}
 if r=='mensajes':return copy.deepcopy(q['ventana_contexto'])
 return None

def _identidad(q):
 d=copy.deepcopy(q);d.pop('emitida_en');d.pop('pagina')
 if q['recurso'] in ('contactos','oportunidades_abiertas'):d['parametros'].pop('page')
 return d

def _fuera_contexto(c):
 q,t=c['consulta'],c['transporte'];r=q['recurso'];payload=t['respuesta']
 if '_error' in payload:return False
 try:
  if r=='mensajes':rows=payload['messages']['messages'];field='dateAdded';v=_ventana(q['ventana_contexto']);a,b=_hora(v['desde']),_hora(v['hasta'])
  elif r=='contactos':rows=payload['contacts'];field='dateAdded';a=_hora(q['parametros']['filters'][0]['value']['gte']);b=_hora(t['observado_en'])
  elif r=='citas':rows=payload['events'];field='startTime';a=_hora(_iso_ms(q['parametros']['startTime']));b=_hora(_iso_ms(q['parametros']['endTime']))
  else:return False
  if not isinstance(rows,list):return True
  for row in rows:
   ms=_fecha(row.get(field)) if isinstance(row,dict) else None
   # Fechas desconocidas se preservan como tales, no se inventan ni filtran.
   if ms is not None and not int(a.timestamp()*1000)<=ms<=int(b.timestamp()*1000):return True
 except (KeyError,TypeError,ValueError,OverflowError):return True
 return False

def cerrar_recurso(capturas,*,fin_explicito=False,recortado=False,clasificaciones=None,origenes=None):
 """Devuelve un dict de argumentos493; NO hace IO ni autoriza captura privada.

Sólo fin_explicito acreditado por contrato proveedor, nunca len<limit.
Mensajes con rango de interpretación siguen parciales: API no filtró porfecha.
 """
 if not isinstance(capturas,list) or not 1<=len(capturas)<=3 or not isinstance(fin_explicito,bool) or not isinstance(recortado,bool):raise ValueError('Ronda inválida')
 validated=[];identity=None;prev=None;resource=None
 for i,c in enumerate(capturas,1):
  if not isinstance(c,dict) or set(c)!={'version','consulta','transporte'} or c['version']!=VERSION:raise ValueError('Captura inválida')
  q=_consulta(c['consulta']);t=c['transporte']
  if not isinstance(t,dict) or set(t)!={'estado_http','respuesta','terminado_en','observado_en'}:raise ValueError('Transporte inválido')
  # Revalida captures modificadas usando exactamente registrar, sin nuevoreloj.
  x=registrar(q,{'estado_http':t['estado_http'],'resultado':'json','payload':t['respuesta'],'terminado_en':t['terminado_en'],'observado_en':t['observado_en']},t['terminado_en'])
  if x!=c:raise ValueError('Captura alterada')
  if q['pagina']!=i or (prev is not None and _hora(q['emitida_en'])<prev):raise ValueError('Páginas fuera de orden')
  ident=_identidad(q)
  if identity is None:identity=ident;resource=q['recurso']
  elif ident!=identity:raise ValueError('Consultas mezcladas')
  prev=_hora(t['terminado_en']);validated.append(c)
 # Cada página se comprueba a su fecha original, no al sello de lapáginafinal.
 responses=[];statuses=[];had_error=False;transport_failed=False
 for c in validated:
  q,t=c['consulta'],c['transporte'];response=copy.deepcopy(t['respuesta'])
  if transport_failed:raise ValueError('Página posterior a fallo de transporte')
  transport_failed='_error' in response
  if '_error' not in response:
   if _fuera_contexto(c):response={'_error':'esquema_invalido'}
   else:
    one=adaptar(resource,[response],subcuenta_id=q['subcuenta_id'],dimension_id=q['dimension_id'],intentado_en=t['terminado_en'],observado_en=t['observado_en'],ventana=_ventana_captura(c),fin_paginacion=False,clasificaciones=clasificaciones,origenes=origenes,estados_http=[t['estado_http']])
    if one['resultado']!='ok':response={'_error':one['codigo_error']}
  had_error=had_error or '_error' in response;responses.append(response);statuses.append(t['estado_http'])
 last=validated[-1];q,t=last['consulta'],last['transporte']
 limited=recortado or resource=='mensajes' or (resource in ('contactos','oportunidades_abiertas') and len(validated)>=3)
 args={'recurso':resource,'respuestas':responses,'subcuenta_id':q['subcuenta_id'],'dimension_id':q['dimension_id'],'intentado_en':t['terminado_en'],'observado_en':t['observado_en'] if not had_error else None,'ventana':_ventana_captura(last),'fin_paginacion':fin_explicito and not had_error,'lectura_limitada':limited,'estados_http':statuses,'clasificaciones':copy.deepcopy(clasificaciones),'origenes':copy.deepcopy(origenes)}
 # Verifica que el contrato recibido puede consumirse antes de entregarlo.
 adaptar(resource,args['respuestas'],**{k:v for k,v in args.items() if k not in ('recurso','respuestas')})
 return args
