"""496: pipeline local y proyección mínima; sin proveedor/DB ni IO al importar.

El callback confiable del servidor acredita permisos/canonicalidad; nunca se
usa el contexto de una respuesta como autoridad. Archivo490.3 independiente.
"""
import copy,hashlib,json,math,os,re,stat
from pathlib import Path
from embudo_eventos import _hora
from fuentes_crm.ultima_valida_490 import VERSION,DEFINICIONES,MAX,_id,_leer,validar_estado,actualizar,guardar_atomico
from fuentes_crm.adaptadores_ultima_valida_493 import adaptar
VERSION_PUBLICA='496.2'
LECTURA={'recurso','respuestas','subcuenta_id','dimension_id','intentado_en','observado_en','ventana','fin_paginacion','lectura_limitada','estados_http','clasificaciones','origenes'}
UNIDADES={'contactos':'contactos_observados','contactos_total':'contactos','calendarios':'calendarios','citas':'reservas_observadas','oportunidades':'oportunidades','conversaciones':'conversaciones','mensajes':'mensajes'}
UNIDADES['oportunidades_abiertas']='oportunidades_abiertas_observadas'

def _ambito(autorizar):
 if not callable(autorizar):raise PermissionError('Ámbito no autorizado')
 try:a=autorizar()
 except Exception:raise PermissionError('Ámbito no autorizado') from None
 if not isinstance(a,dict) or set(a)!={'actor_real','actor_vista','firma_sha256','clientes'} or not _id(a['actor_real']) or not _id(a['actor_vista']) or not isinstance(a['firma_sha256'],str) or re.fullmatch('[a-f0-9]{64}',a['firma_sha256']) is None or not isinstance(a['clientes'],list) or not 1<=len(a['clientes'])<=10000:raise PermissionError('Ámbito no autorizado')
 cs=[];cids=set();sids=set()
 for c in a['clientes']:
  if not isinstance(c,dict) or set(c)!={'cliente_id','subcuenta_id'} or not _id(c['cliente_id']) or not _id(c['subcuenta_id']) or c['cliente_id'] in cids or c['subcuenta_id'] in sids:raise PermissionError('Ámbito no autorizado')
  cids.add(c['cliente_id']);sids.add(c['subcuenta_id']);cs.append((c['cliente_id'],c['subcuenta_id']))
 return (a['actor_real'],a['actor_vista'],a['firma_sha256'],tuple(sorted(cs)))

def _gate(autorizar,scope):
 if _ambito(autorizar)!=scope:raise PermissionError('Ámbito cambió')

def _path(path):
 p=Path(path)
 if not p.is_absolute() or p.resolve()!=p or p.parent.is_symlink() or not p.parent.is_dir():raise ValueError('Depósito no privado')
 s=p.parent.stat()
 if stat.S_IMODE(s.st_mode)!=0o700 or s.st_uid!=os.getuid():raise ValueError('Depósito no privado')
 return p

def _pares(pairs):
 d={}
 for k,v in pairs:
  if k in d:raise ValueError('JSON duplicado')
  d[k]=v
 return d

def _float(v):
 n=float(v)
 if not math.isfinite(n):raise ValueError('JSON no finito')
 return n

def _const(v):raise ValueError('JSON no finito')

def _cargar(path):
 p=_path(path)
 try:b=_leer(p)
 except FileNotFoundError:return {'version':VERSION,'recursos':{}},None
 try:d=json.loads(b.decode('utf-8'),object_pairs_hook=_pares,parse_float=_float,parse_constant=_const)
 except (ValueError,UnicodeError,RecursionError):raise ValueError('Depósito inválido') from None
 validar_estado(d)
 return d,hashlib.sha256(b).hexdigest()

def _ahora(ahora):
 t=_hora(ahora)
 if t is None:raise ValueError('Corte inválido')
 return t.isoformat()

def proyectar(estado,scope,ahora):
 """Scope sólo producido por _ambito servidor. No sumar dimensiones/cortes."""
 cut=_ahora(ahora);actualizar(estado,[],cut)
 sid_to_cid={sid:cid for cid,sid in scope[3]}
 groups={cid:{r:[] for r in DEFINICIONES} for cid,sid in scope[3]}
 for key,record in sorted(estado['recursos'].items()):
  cid=sid_to_cid.get(record['subcuenta_id'])
  if cid is None:continue
  valid=record['ultima_valida'];attempt=record['ultimo_intento']
  if record['acceso']=='denegado':status='sin_acceso'
  elif valid is None:status='sin_dato'
  elif not attempt['observacion_promovida']:status='ultima_valida_anterior'
  else:status='leida' if valid['cobertura']['completa'] else 'parcial'
  n=(valid['datos']['total'] if record['recurso']=='contactos_total' else len(valid['datos'])) if valid is not None else None
  obs={'conteo_observado':n,'estado_lectura':status,'observado_en':valid['observado_en'] if valid else None,'ventana':copy.deepcopy(valid['ventana']) if valid else None,'cobertura':dict(valid['cobertura']) if valid else None,'ultimo_intento':{'intentado_en':attempt['intentado_en'],'resultado':attempt['resultado'],'codigo_error':attempt['codigo_error'],'observacion_promovida':attempt['observacion_promovida'],'ventana_solicitada':copy.deepcopy(attempt['ventana_solicitada'])}}
  groups[cid][record['recurso']].append(obs)
 rows=[]
 for cid,by_resource in sorted(groups.items()):
  resources=[]
  for resource,observations in by_resource.items():
   # Un único registro puede dar número del recurso; múltiples dimensiones
   # quedan observaciones separadas, sin suma/falso total/mezcla de fechas.
   resources.append({'recurso':resource,'unidad':UNIDADES[resource],'conteo_observado':observations[0]['conteo_observado'] if len(observations)==1 else None,'estado_lectura':observations[0]['estado_lectura'] if len(observations)==1 else 'sin_dato' if not observations else 'dimensiones_separadas','observaciones':observations})
  rows.append({'cliente_id':cid,'recursos':resources})
 return {'version':VERSION_PUBLICA,'generado':cut,'cobertura':'parcial','completa':False,'fuente':'ultima_valida_privada_490.3','clientes':rows}

def leer_version(path,autorizar,ahora):
 cut=_ahora(ahora);scope=_ambito(autorizar)
 state,sha=_cargar(path)
 _gate(autorizar,scope)
 dto=proyectar(state,scope,cut)
 _gate(autorizar,scope)
 return {'version':VERSION_PUBLICA,'sha_estado':sha,'proyeccion':dto}

def leer_proyeccion(path,autorizar,ahora):
 # HTTP futuro devuelve sólo proyección; SHA es recibo interno del writer.
 return leer_version(path,autorizar,ahora)['proyeccion']

def procesar(path,lecturas,autorizar,ahora,sha_anterior=None):
 """Adaptación→merge→CAS. Sin transporte/red y sin activar generadorlegacy."""
 cut=_ahora(ahora);scope=_ambito(autorizar);allowed={sid for cid,sid in scope[3]}
 if not isinstance(lecturas,list) or len(lecturas)>10000:raise ValueError('Ronda inválida')
 es=[]
 for raw in lecturas:
  if not isinstance(raw,dict) or not {'recurso','respuestas','subcuenta_id','intentado_en'}<=set(raw) or set(raw)-LECTURA:raise ValueError('Lectura inválida')
  if not _id(raw['subcuenta_id']) or raw['subcuenta_id'] not in allowed:raise PermissionError('Lectura fuera de ámbito')
  kwargs={k:v for k,v in raw.items() if k not in ('recurso','respuestas')}
  es.append(adaptar(raw['recurso'],raw['respuestas'],**kwargs))
 _gate(autorizar,scope)
 state,oldsha=_cargar(path)
 _gate(autorizar,scope)
 if oldsha!=sha_anterior:raise ValueError('CAS: estado cambió')
 updated=actualizar(state,es,cut)
 # Callback dentro del writer garantiza chequeos trasleer y antesreplace.
 sha=guardar_atomico(path,updated,sha_anterior,validar_scope=lambda:_gate(autorizar,scope))
 _gate(autorizar,scope)
 dto=proyectar(updated,scope,cut)
 _gate(autorizar,scope)
 return {'version':VERSION_PUBLICA,'guardado_privado':True,'sha_estado':sha,'proyeccion':dto}
