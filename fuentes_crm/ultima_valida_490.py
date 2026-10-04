"""490: conservación por recurso normalizado GHL; no API/DB ni IO al importar.

Formato independiente de466. Una observación es privada y nunca autoriza lectura.
El adaptador futuro debe convertir fallos explícitos; no puede llamar 'ok' a HTTP200
malformado o vacío sin cobertura acreditada.
"""
import copy,fcntl,hashlib,json,os,re,stat,tempfile
from pathlib import Path
from embudo_eventos import _hora
VERSION='490.3';MAX=5_000_000;CAP=10000
DEFINICIONES={'contactos':'contactos_creados_ventana490.2','contactos_total':'total_contactos490.2','calendarios':'catalogo_calendarios490.2','citas':'citas_por_calendario490.2','oportunidades':'oportunidades_ventana490.2','conversaciones':'conversaciones_contacto490.2','mensajes':'mensajes_conversacion490.2'}
DIMENSION=frozenset({'citas','conversaciones','mensajes'})
DEFINICIONES['oportunidades_abiertas']='stock_oportunidades_abiertas490.3'
ERRORES=frozenset({'red','timeout','http_5xx','limite','esquema_invalido','paginacion_incompleta','sin_acceso','no_encontrado','vacio_no_acreditado'})
ENVELOPE={'version','subcuenta_id','recurso','dimension_id','definicion','resultado','intentado_en','observado_en','ventana','cobertura','datos','codigo_error'}
ROW={'contactos':{'id','creado','es_lead'},'calendarios':{'id','activo'},'citas':{'id','contacto','creada','inicio','estado'},'oportunidades':{'id','contacto','creada','estado'},'conversaciones':{'id','contacto'},'mensajes':{'id','creado','direccion','tipo','origen','estado'}}
ROW['oportunidades_abiertas']=set(ROW['oportunidades'])
def _id(v):return isinstance(v,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,160}',v) is not None
def _n(v):return isinstance(v,int) and not isinstance(v,bool) and 0<=v<=2**53-1
def _epoch(v):return v is None or (_n(v) and v<=253402300799999)
def _enum(v,opciones):return isinstance(v,str) and v in opciones

def _ventana(v):
 if v is None:return None
 if not isinstance(v,dict) or set(v)!={'tipo','desde','hasta'}:raise ValueError('Ventana inválida')
 if not _enum(v['tipo'],('medicion_pasada','inventario_programado')):raise ValueError('Tipo de ventana inválido')
 a,b=_hora(v['desde']),_hora(v['hasta'])
 if a is None or b is None or a>b:raise ValueError('Ventana inválida')
 return {'tipo':v['tipo'],'desde':a.isoformat(),'hasta':b.isoformat()}

def _validar_ventana_recurso(resource,window,observed):
 if resource=='oportunidades_abiertas' and window is not None:raise ValueError('Stock abierto no tiene ventana de cohorte')
 if resource in ('contactos','citas','mensajes','oportunidades') and window is None:raise ValueError('Falta ventana observada')
 if window is None:return
 if window['tipo']=='inventario_programado' and resource!='citas':raise ValueError('Inventario futuro sólo citas')
 if window['tipo']=='medicion_pasada' and _hora(window['hasta'])>observed:raise ValueError('Ventana posterior a observación')

def _datos(resource,d):
 if resource=='contactos_total':return isinstance(d,dict) and set(d)=={'total'} and _n(d['total'])
 if not isinstance(d,list) or len(d)>CAP:return False
 seen=set()
 for r in d:
  if not isinstance(r,dict) or set(r)!=ROW[resource] or not _id(r.get('id')) or r['id'] in seen:return False
  seen.add(r['id'])
  if 'contacto' in r and not _id(r['contacto']):return False
  if any(not _epoch(r[k]) for k in ('creado','creada','inicio') if k in r):return False
  if resource=='contactos' and not isinstance(r['es_lead'],bool):return False
  if resource=='calendarios' and not isinstance(r['activo'],bool):return False
  if resource=='citas' and not _enum(r['estado'],{'confirmed','cancelled','invalid','showed','noshow','sin_estado','new'}):return False
  if resource=='oportunidades' and not _enum(r['estado'],{'open','won','lost','abandoned','sin_estado'}):return False
  if resource=='oportunidades_abiertas' and r['estado']!='open':return False
  if resource=='mensajes' and (not _enum(r['direccion'],{'inbound','outbound','desconocida'}) or not _enum(r['tipo'],{'call','whatsapp','sms','email','otro'}) or not _enum(r['origen'],{'humano','automatico','desconocido'}) or not _enum(r['estado'],{'enviado','fallido','desconocido'})):return False
 return True

def _fechas_datos(resource,data,window,observed):
 if not isinstance(data,list):return True
 ceiling=int(observed.timestamp()*1000)
 for row in data:
  if any(row.get(k) is not None and row[k]>ceiling for k in ('creado','creada')):return False
  if row.get('inicio') is not None and row['inicio']>ceiling and (resource!='citas' or window is None or window['tipo']!='inventario_programado'):return False
 return True

def _cobertura(c):
 if not isinstance(c,dict) or set(c)!={'completa','paginas_leidas','fin_paginacion','vacio_confirmado'} or not all(isinstance(c[k],bool) for k in ('completa','fin_paginacion','vacio_confirmado')) or not _n(c['paginas_leidas']):raise ValueError('Cobertura inválida')
 if c['completa'] and (not c['fin_paginacion'] or c['paginas_leidas']<1):raise ValueError('Completitud incoherente')
 return copy.deepcopy(c)

def clave(e):
 resource=e.get('recurso');dim=e.get('dimension_id')
 if not _id(e.get('subcuenta_id')) or (not isinstance(resource,str) or resource not in DEFINICIONES) or e.get('definicion')!=DEFINICIONES[resource] or (not _id(dim) if resource in DIMENSION else dim is not None):raise ValueError('Identidad/recurso inválido')
 return hashlib.sha256(json.dumps([e['subcuenta_id'],resource,dim,e['definicion']],separators=(',',':')).encode()).hexdigest()

def validar_estado(d):
 if not isinstance(d,dict) or set(d)!={'version','recursos'} or d['version']!=VERSION or not isinstance(d['recursos'],dict) or len(d['recursos'])>CAP:raise ValueError('Estado inválido')
 for key,r in d['recursos'].items():
  if not isinstance(r,dict) or set(r)!={'subcuenta_id','recurso','dimension_id','definicion','acceso','ultima_valida','ultimo_intento'} or clave(r)!=key or not _enum(r['acceso'],('permitido','denegado')):raise ValueError('Registro inválido')
  x=r['ultima_valida'];attempt=r['ultimo_intento']
  if not isinstance(attempt,dict) or set(attempt)!={'intentado_en','resultado','codigo_error','observacion_promovida','ventana_solicitada'} or _hora(attempt['intentado_en']) is None or not _enum(attempt['resultado'],('valida','parcial','error','denegado','no_promovido')) or not isinstance(attempt['observacion_promovida'],bool) or (attempt['codigo_error'] is not None and not _enum(attempt['codigo_error'],ERRORES)):raise ValueError('Intento inválido')
  requested=_ventana(attempt['ventana_solicitada'])
  if r['recurso']=='oportunidades_abiertas' and requested is not None:raise ValueError('Stock abierto no tiene ventana')
  if requested is not None and requested['tipo']=='inventario_programado' and r['recurso']!='citas':raise ValueError('Inventario futuro sólo citas')
  if r['acceso']=='denegado' and x is not None:raise ValueError('Acceso denegado conserva payload')
  if x is not None:
   if not isinstance(x,dict) or set(x)!={'observado_en','ventana','cobertura','datos'} or _hora(x['observado_en']) is None or _hora(x['observado_en'])>_hora(attempt['intentado_en']) or not _datos(r['recurso'],x['datos']):raise ValueError('Observación inválida')
   window=_ventana(x['ventana']);cov=_cobertura(x['cobertura'])
   _validar_ventana_recurso(r['recurso'],window,_hora(x['observado_en']))
   if not _fechas_datos(r['recurso'],x['datos'],window,_hora(x['observado_en'])):raise ValueError('Fecha de fila posterior a lectura')
   empty=isinstance(x['datos'],list) and not x['datos'] or r['recurso']=='contactos_total' and x['datos']['total']==0
   if empty and not (cov['completa'] and cov['fin_paginacion'] and cov['vacio_confirmado']):raise ValueError('Vacío almacenado no acreditado')
 return d

def migrar_490_2(anterior):
 """Transición explícita pura. No acepta recurso503 ni toca fechas/keys/bytes."""
 if not isinstance(anterior,dict) or anterior.get('version')!='490.2' or not isinstance(anterior.get('recursos'),dict):raise ValueError('Origen no es490.2')
 if any(not isinstance(r,dict) or r.get('recurso')=='oportunidades_abiertas' for r in anterior['recursos'].values()):raise ValueError('Recurso no existía en490.2')
 out=copy.deepcopy(anterior);out['version']=VERSION
 validar_estado(out)
 return out

def actualizar(anterior,intentos,ahora):
 """Merge puro. No muta entradas ni fabrica cero por fallo/ausencia."""
 now=_hora(ahora)
 if now is None or not isinstance(intentos,list) or len(intentos)>CAP:raise ValueError('Ronda inválida')
 out=copy.deepcopy(validar_estado(anterior));keys=set()
 if any(_hora(r['ultimo_intento']['intentado_en'])>now for r in out['recursos'].values()):raise ValueError('Estado anterior futuro')
 for e in intentos:
  if not isinstance(e,dict) or set(e)!=ENVELOPE or e['version']!=VERSION:raise ValueError('Intento inválido')
  key=clave(e);when=_hora(e['intentado_en'])
  if key in keys or when is None or when>now:raise ValueError('Intento ambiguo/futuro')
  keys.add(key);old=out['recursos'].get(key)
  if old and when<_hora(old['ultimo_intento']['intentado_en']):raise ValueError('Ronda anterior')
  if not _enum(e['resultado'],('ok','error','denegado')):raise ValueError('Resultado inválido')
  rec={k:e[k] for k in ('subcuenta_id','recurso','dimension_id','definicion')};rec.update(acceso=old['acceso'] if old else 'permitido',ultima_valida=copy.deepcopy(old['ultima_valida']) if old else None)
  promoted=False;error=e['codigo_error'];status='error'
  if e['resultado']=='ok':
   observed=_hora(e['observado_en']);window=_ventana(e['ventana']);cov=_cobertura(e['cobertura'])
   if observed is not None:_validar_ventana_recurso(e['recurso'],window,observed)
   if old and old['ultima_valida'] and observed is not None and observed<_hora(old['ultima_valida']['observado_en']):raise ValueError('No rejuvenecer lectura anterior')
   if error is not None or observed is None or observed>when:raise ValueError('Lectura inválida')
   valid=_datos(e['recurso'],e['datos']) and _fechas_datos(e['recurso'],e['datos'],window,observed);empty=isinstance(e['datos'],list) and not e['datos'] or (e['recurso']=='contactos_total' and valid and e['datos']['total']==0)
   if not valid:error='esquema_invalido'
   elif empty and not (cov['completa'] and cov['fin_paginacion'] and cov['vacio_confirmado']):error='vacio_no_acreditado';status='no_promovido'
   else:
    rec['acceso']='permitido'
    rec['ultima_valida']={'observado_en':observed.isoformat(),'ventana':window,'cobertura':cov,'datos':copy.deepcopy(e['datos'])};promoted=True;status='valida' if cov['completa'] else 'parcial'
  else:
   if not _enum(error,ERRORES) or e['datos'] is not None or e['observado_en'] is not None or e['cobertura'] is not None:raise ValueError('Fallo incluye payload o causa inválida')
   requested=_ventana(e['ventana'])
   if e['recurso']=='oportunidades_abiertas' and requested is not None:raise ValueError('Stock abierto no tiene ventana')
   if requested is not None and requested['tipo']=='inventario_programado' and e['recurso']!='citas':raise ValueError('Inventario futuro sólo citas')
   if e['resultado']=='denegado' or error in ('sin_acceso','no_encontrado'):rec.update(acceso='denegado',ultima_valida=None);status='denegado'
  rec['ultimo_intento']={'intentado_en':when.isoformat(),'resultado':status,'codigo_error':error,'observacion_promovida':promoted,'ventana_solicitada':_ventana(e['ventana'])}
  if old and when==_hora(old['ultimo_intento']['intentado_en']) and rec!=old:raise ValueError('Mismo intento con payload distinto')
  out['recursos'][key]=rec
 validar_estado(out);return out

def _serial(d):
 b=json.dumps(validar_estado(d),sort_keys=True,ensure_ascii=True,allow_nan=False,separators=(',',':')).encode()
 if len(b)>MAX:raise ValueError('Estado excesivo')
 return b

def _leer(path):
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  s=os.fstat(fd)
  if not stat.S_ISREG(s.st_mode) or stat.S_IMODE(s.st_mode)!=0o600 or s.st_uid!=os.getuid() or s.st_nlink!=1 or not 0<s.st_size<=MAX:raise ValueError('Archivo no privado')
  with os.fdopen(os.dup(fd),'rb') as f:b=f.read(MAX+1)
  z=os.fstat(fd)
  if len(b)!=s.st_size or (s.st_ino,s.st_size,s.st_mtime_ns)!=(z.st_ino,z.st_size,z.st_mtime_ns):raise ValueError('Archivo cambió')
  return b
 finally:os.close(fd)

def guardar_atomico(path,estado,sha_anterior=None,validar_scope=None):
 """Writer privado aislado. CAS con flock/replace; no toca ruta por defecto."""
 if validar_scope is not None and not callable(validar_scope):raise ValueError('Gate inválido')
 if validar_scope is not None:validar_scope()
 p=Path(path);parent=p.parent
 if not p.is_absolute() or p.resolve()!=p or parent.is_symlink() or not parent.is_dir():raise ValueError('Ruta inválida')
 s=parent.stat()
 if stat.S_IMODE(s.st_mode)!=0o700 or s.st_uid!=os.getuid():raise ValueError('Directorio no privado')
 b=_serial(estado);lock=p.with_name(p.name+'.lock');fd=os.open(lock,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
 temp=None
 try:
  ls=os.fstat(fd)
  if not stat.S_ISREG(ls.st_mode) or stat.S_IMODE(ls.st_mode)!=0o600 or ls.st_uid!=os.getuid() or ls.st_nlink!=1:raise ValueError('Lock no privado')
  fcntl.flock(fd,fcntl.LOCK_EX)
  exists=p.exists() or p.is_symlink()
  old=_leer(p) if exists else None
  if validar_scope is not None:validar_scope()
  if sha_anterior!=(hashlib.sha256(old).hexdigest() if old is not None else None):raise ValueError('CAS: estado cambió')
  if old==b:return hashlib.sha256(b).hexdigest()
  tf,name=tempfile.mkstemp(prefix='.lkg490-',dir=parent);temp=Path(name)
  with os.fdopen(tf,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
  if validar_scope is not None:validar_scope()
  os.replace(temp,p);temp=None;df=os.open(parent,os.O_RDONLY|os.O_DIRECTORY)
  try:os.fsync(df)
  finally:os.close(df)
  if validar_scope is not None:validar_scope()
  return hashlib.sha256(b).hexdigest()
 finally:
  if temp is not None:temp.unlink(missing_ok=True)
  os.close(fd)
