"""382: decisión local duradera sobre tabla legacy. Sin DB/red/escritura al importar. Dependencias operativas de saneado existentes."""
import hashlib,json,os,re,sqlite3,math
from datetime import datetime,timezone
from contextlib import closing
from uuid import UUID
import piloto_lectura
import bd_comun as bd
from contexto_tarea import texto_operativo
from operaciones_registros_269 import unica,ErrorRegistro
RUTA='/api/operaciones/decisiones-locales';VERSION='382.1'
TIPOS={'para_tomas','para_coti','escalada'};OPCIONES={'Aprobar la recomendación','Rechazar','Delegar'}
class ErrorDecision(Exception):
 def __init__(self,codigo,texto):self.codigo=codigo;super().__init__(texto)
def huella(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def persona(S,pid):
 try:p=unica(S.E.crudo.get('personas'),pid)
 except ErrorRegistro:raise ErrorDecision(403,'Identidad actual no inequívoca.')
 roles=p.get('puestos')
 if not isinstance(roles,list) or not roles or any(not isinstance(x,str) for x in roles) or len(set(roles))!=len(roles):raise ErrorDecision(403,'Roles actuales no inequívocos.')
 return p

def autorizar(S,rid,vid,cid=None,escritura=False):
 if S.E.nucleo_bloqueado:raise ErrorDecision(503,'Permisos actuales no disponibles.')
 if escritura and (rid!=vid or piloto_lectura.activo()):raise ErrorDecision(403,'Esta sesión sólo permite lectura.')
 ps=[persona(S,x) for x in (rid,vid)]
 if rid!=vid and S.P.ver(ps[0],{'tipo':'ver_como'},S.P.contexto(ps[0],S.E.crudo)).get('ok') is not True:raise ErrorDecision(403,'Vista no autorizada.')
 for p in ps:
  if not S.ve_alguno(p,['decisiones']):raise ErrorDecision(403,'Decisiones fuera de tu ámbito.')
  if cid is not None:
   cs=[c for c in S.E.crudo.get('clientes') or [] if isinstance(c,dict) and c.get('id')==cid]
   if len(cs)!=1 or cs[0].get('activo') is False or cs[0].get('estado')=='baja' or S.ACT.es_activo_id(cid) is not True or S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},S.P.contexto(p,S.E.crudo)).get('ok') is not True:raise ErrorDecision(404,'Cliente fuera de tu ámbito actual.')
 return ps

def visible(p,r):
 roles=set(p['puestos']);return bool(roles&{'direccion','operaciones'} or ('proyectos' in roles and r['tipo']=='para_coti') or r['quien']==p['id'])
def texto(v,maximo,obligatorio=True):
 if v is None and not obligatorio:return None
 if not isinstance(v,str) or not (1<=len(v.strip())<=maximo):raise ErrorDecision(400,'Texto operativo vacío o demasiado largo.')
 limpio=texto_operativo(v.strip(),maximo)
 if limpio!=v.strip():raise ErrorDecision(400,'Retira datos personales, importes o credenciales del texto operativo.')
 return limpio

def validar(b):
 if not isinstance(b,dict) or b.get('operacion') not in {'nueva','responder'}:raise ErrorDecision(400,'Operación inválida.')
 campos={'intencion_id','operacion','cliente_id','tipo','titulo','problema','recomendacion'} if b['operacion']=='nueva' else {'intencion_id','operacion','id','revision','decision','motivo','delegada_en'}
 if set(b)!=campos:raise ErrorDecision(400,'Campos no admitidos.')
 try:
  u=UUID(b['intencion_id'])
  if u.version!=4 or str(u)!=b['intencion_id']:raise ValueError()
 except (ValueError,TypeError,AttributeError):raise ErrorDecision(400,'Intención UUID inválida.')
 if b['operacion']=='nueva':
  if not isinstance(b['tipo'],str) or b['tipo'] not in TIPOS:raise ErrorDecision(400,'Tipo no admitido.')
  if b['cliente_id'] is not None and (not isinstance(b['cliente_id'],str) or not re.fullmatch('[A-Za-z0-9_-]{1,120}',b['cliente_id'])):raise ErrorDecision(400,'Cliente inválido.')
  for k,n in [('titulo',200),('problema',2000),('recomendacion',2000)]:texto(b[k],n)
 else:
  if not isinstance(b['id'],str) or not re.fullmatch(r'db-[1-9][0-9]{0,12}',b['id']) or not isinstance(b['revision'],str) or not re.fullmatch('[a-f0-9]{64}',b['revision']):raise ErrorDecision(400,'Referencia o revisión inválida.')
  if not isinstance(b['decision'],str) or b['decision'] not in OPCIONES:raise ErrorDecision(400,'Decisión no admitida.')
  texto(b['motivo'],2000,b['decision']!='Aprobar la recomendación')
  if b['decision']=='Delegar':
   if not isinstance(b['delegada_en'],str) or not re.fullmatch('[A-Za-z0-9_-]{1,100}',b['delegada_en']):raise ErrorDecision(400,'Elige un destinatario canónico.')
  elif b['delegada_en'] is not None:raise ErrorDecision(400,'Delegación no aplicable.')

def preparar(con):
 con.execute('CREATE TABLE IF NOT EXISTS decisiones_intenciones_382 (intencion_id TEXT PRIMARY KEY,autor TEXT NOT NULL,huella TEXT NOT NULL,decision_id INTEGER NOT NULL,operacion TEXT NOT NULL,revision_final TEXT NOT NULL,registrado_en TEXT NOT NULL DEFAULT (datetime(\'now\')))')
 for op in ('UPDATE','DELETE'):con.execute('CREATE TRIGGER IF NOT EXISTS decisiones382_no_'+op+' BEFORE '+op+' ON decisiones_intenciones_382 BEGIN SELECT RAISE(ABORT,\'Intención inmutable\'); END')
def leer(con,id):
 r=con.execute('SELECT * FROM decisiones WHERE id=?',(int(id[3:]),)).fetchone() if id else None
 if r is None or r['tipo'] not in TIPOS or r['anula_a'] is not None:raise ErrorDecision(404,'Decisión no disponible.')
 return dict(r)
def revision(r):return huella(r)
def autorizar_fila(S,rid,vid,r,escritura=False):
 ps=autorizar(S,rid,vid,r['cliente_id'],escritura)
 if not all(visible(p,r) for p in ps):raise ErrorDecision(404,'Decisión fuera de tu ámbito.')
 if escritura and not S.puede_contestar(ps[0],r['tipo']):raise ErrorDecision(403,'Sólo su destinatario puede contestar.')
 return ps

def identidad_confirmada(S,pid):
 if not isinstance(pid,str) or not re.fullmatch('[A-Za-z0-9_-]{1,100}',pid):return None
 ps=[p for p in S.E.crudo.get('personas') or [] if isinstance(p,dict) and p.get('id')==pid]
 return pid if len(ps)==1 and ps[0].get('estado')=='activo' and ps[0].get('activo') is not False else None

def fecha_publica(v):
 # SQLite datetime('now') es UTC. Fuera de este formato o ISO aware, desconocido.
 if not isinstance(v,str) or len(v)>40:return None
 try:
  if re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',v):d=datetime.strptime(v,'%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
  elif re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})',v):d=datetime.fromisoformat(v.replace('Z','+00:00'))
  else:return None
  return d.astimezone(timezone.utc).isoformat()
 except (ValueError,OverflowError):return None

def json_estricto(raw):
 def invalido(*_):raise ValueError('JSON ambiguo')
 def pares(items):
  d={}
  for k,v in items:
   if k in d:invalido()
   d[k]=v
  return d
 def decimal(v):
  f=float(v)
  if not math.isfinite(f):invalido()
  return f
 return json.loads(raw,object_pairs_hook=pares,parse_constant=invalido,parse_float=decimal)

def respuesta_minima(S,r):
 # La marca de respuesta no acredita que un JSON legado sea una decisión válida.
 if r.get('respondida') is None:return None
 raw=r.get('respuesta')
 if not isinstance(raw,str) or len(raw)>40000:return None
 try:d=json_estricto(raw)
 except (ValueError,TypeError,RecursionError):return None
 if not isinstance(d,dict) or not isinstance(d.get('decision'),str) or d['decision'] not in OPCIONES:return None
 motivo=d.get('motivo')
 if motivo is not None and (not isinstance(motivo,str) or len(motivo)>2000):return None
 if d['decision']!='Aprobar la recomendación' and (not isinstance(motivo,str) or not motivo.strip()):return None
 delegado=d.get('delegada_en')
 if delegado is not None and (not isinstance(delegado,str) or not re.fullmatch('[A-Za-z0-9_-]{1,100}',delegado)):return None
 if d['decision']!='Delegar' and delegado is not None:return None
 return {'decision':d['decision'],'motivo':texto_operativo(motivo,2000) if motivo else None,'delegada_en':identidad_confirmada(S,delegado) if d['decision']=='Delegar' else None}

def dto(S,rid,vid,r):
 ps=autorizar_fila(S,rid,vid,r)
 author=identidad_confirmada(S,r['quien'])
 return {'id':'db-'+str(r['id']),'tipo':r['tipo'],'cliente_id':r['cliente_id'],'quien':author,'titulo':texto_operativo(r.get('titulo') or '',200),'problema':texto_operativo(r.get('problema') or '',2000),'recomendacion':texto_operativo(r.get('recomendacion') or '',2000),'creada':fecha_publica(r['creada']),'respondida':fecha_publica(r['respondida']),'respuesta_registrada':r['respondida'] is not None,'respondida_por':identidad_confirmada(S,r.get('respondida_por')),'respuesta':respuesta_minima(S,r),'revision':revision(r),'puede_responder':rid==vid and not piloto_lectura.activo() and r['respondida'] is None and S.puede_contestar(ps[0],r['tipo']),'origen':'registro_local','ejecucion_verificada':False,'envio_realizado':False}

def listar(S,con,rid,vid):
 ps=autorizar(S,rid,vid)
 rs=[dict(x) for x in con.execute("SELECT * FROM decisiones WHERE tipo IN ('para_tomas','para_coti','escalada') AND anula_a IS NULL ORDER BY id DESC LIMIT 1001")];out=[]
 for r in rs[:1000]:
  if not all(visible(p,r) for p in ps):continue
  try:out.append(dto(S,rid,vid,r))
  except ErrorDecision as e:
   if e.codigo not in {403,404}:raise
 autorizar(S,rid,vid)
 # Revalida todas las filas tras terminar lectura; no entregar un cliente revocado.
 for r in rs[:1000]:
  if any(x['id']=='db-'+str(r['id']) for x in out):autorizar_fila(S,rid,vid,r)
 return {'version':VERSION,'decisiones':out,'truncado':len(rs)>1000,'origen':'registro_local','envio_realizado':False}

def guardar(S,con,rid,vid,b):
 validar(b);autorizar(S,rid,vid,escritura=True)
 if con.in_transaction:raise ErrorDecision(503,'Se requiere conexión exclusiva.')
 con.execute('BEGIN IMMEDIATE')
 try:
  preparar(con);autorizar(S,rid,vid,escritura=True);fp=huella({'autor':rid,'cuerpo':b})
  r=leer(con,b['id']) if b['operacion']=='responder' else None
  if r:autorizar_fila(S,rid,vid,r,True)
  else:autorizar(S,rid,vid,b['cliente_id'],True)
  delegado=persona(S,b['delegada_en']) if b.get('delegada_en') is not None else None
  delegado_hash=huella(delegado) if delegado is not None else None
  anterior=con.execute('SELECT * FROM decisiones_intenciones_382 WHERE intencion_id=?',(b['intencion_id'],)).fetchone()
  if anterior:
   if anterior['autor']!=rid or anterior['huella']!=fp:raise ErrorDecision(409,'Esta intención ya tiene otro contenido.')
   final=dict(anterior);repetida=True
  else:
   if r:
    if r['respondida'] is not None or revision(r)!=b['revision']:raise ErrorDecision(409,'La decisión cambió. Conserva el intento y vuelve a leer.')
    respuesta=json.dumps({k:b[k] for k in ('decision','motivo','delegada_en')},ensure_ascii=False)
    actualizada=con.execute("UPDATE decisiones SET respuesta=?,respondida=datetime('now'),respondida_por=? WHERE id=? AND respondida IS NULL",(respuesta,rid,r['id']))
    if actualizada.rowcount!=1:raise ErrorDecision(409,'La decisión ya no está abierta.')
    did=r['id']
   else:
    cur=con.execute('INSERT INTO decisiones (quien,tipo,titulo,problema,recomendacion,cliente_id,datos) VALUES (?,?,?,?,?,?,?)',(rid,b['tipo'],b['titulo'].strip(),b['problema'].strip(),b['recomendacion'].strip(),b['cliente_id'],'{}'));did=cur.lastrowid
   fin=leer(con,'db-'+str(did));rv=revision(fin)
   con.execute('INSERT INTO decisiones_intenciones_382 (intencion_id,autor,huella,decision_id,operacion,revision_final) VALUES (?,?,?,?,?,?)',(b['intencion_id'],rid,fp,did,b['operacion'],rv));final=dict(con.execute('SELECT * FROM decisiones_intenciones_382 WHERE intencion_id=?',(b['intencion_id'],)).fetchone());repetida=False
  current=leer(con,'db-'+str(final['decision_id']));autorizar_fila(S,rid,vid,current,b['operacion']=='responder')
  if delegado is not None and huella(persona(S,delegado['id']))!=delegado_hash:raise ErrorDecision(409,'El destinatario cambió durante el registro.')
  con.commit();autorizar_fila(S,rid,vid,current,b['operacion']=='responder')
  return {'version':VERSION,'resultado':'duplicado' if repetida else 'guardado','recibo':{'intencion_id':b['intencion_id'],'id':'db-'+str(final['decision_id']),'operacion':b['operacion'],'revision':final['revision_final'],'autor':rid,'guardado_local':True,'envio_realizado':False,'ejecucion_verificada':False}}
 except Exception:con.rollback();raise

def enganchar(H,S):
 get_orig,post_orig=H._api_get,H.api_post
 def handler(self,metodo,ruta,q,real,vista,b=None):
  if ruta!=RUTA:return get_orig(self,ruta,q,real,vista) if metodo=='GET' else post_orig(self,ruta,real,vista,b)
  try:
   if q:raise ErrorDecision(400,'Esta ruta no admite filtros de identidad.')
   rid,vid=real.get('id'),vista.get('id');ps=autorizar(S,rid,vid,escritura=metodo=='POST')
   for provided,canonical in zip((real,vista),ps):
    if provided.get('estado')!='activo' or provided.get('activo') is False or not isinstance(provided.get('puestos'),list) or sorted(provided['puestos'])!=sorted(canonical['puestos']):raise ErrorDecision(403,'Contexto actual incoherente.')
   with closing(S.conectar()) as con:
    if not bd.conexion_valida(con):raise ErrorDecision(503,'Persistencia local no disponible.')
    con.row_factory=sqlite3.Row;doc=listar(S,con,rid,vid) if metodo=='GET' else guardar(S,con,rid,vid,b)
   autorizar(S,rid,vid,escritura=metodo=='POST')
   return self.responder(200,doc)
  except ErrorDecision as e:return self.responder(e.codigo,{'error':str(e)})
  except bd.ERRORES_BD:return self.responder(503,{'error':'Persistencia local no disponible; conserva la intención.'})
 H._api_get=lambda self,ruta,q,real,vista:handler(self,'GET',ruta,q,real,vista)
 H.api_post=lambda self,ruta,real,vista,b:handler(self,'POST',ruta,{},real,vista,b)
