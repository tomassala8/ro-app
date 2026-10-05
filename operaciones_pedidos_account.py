"""294: pedidos internos declarados append-only. No mensajes externos ni IO al importar."""
import collections,hashlib,json,os,re,sqlite3
from contextlib import closing
from datetime import date,datetime,timezone,timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from uuid import UUID
import piloto_lectura
from operaciones_registros_269 import unica,ErrorRegistro
RUTA='/api/operaciones/pedidos-account';VERSION='294.1';TABLA='operaciones_pedidos_account_294';TIPOS={'responder_correo':'correos','devolver_llamada':'llamadas'};ESTADOS={'pedido','anulado','resuelto_declarado'}
RUTA_RESUMEN=RUTA+'/resumen';VERSION_RESUMEN='343.1';AUTOR_RESUMEN='mili';MAX_HISTORIA_RESUMEN=20000
class ErrorPedido(Exception):
 def __init__(self,codigo,texto):self.codigo=codigo;super().__init__(texto)
def hash_(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def autorizar(S,rid,vid,cid=None,escritura=False):
 if S.E.nucleo_bloqueado:raise ErrorPedido(503,'Los permisos actuales no están disponibles.')
 if escritura and (rid!=vid or piloto_lectura.activo()):raise ErrorPedido(403,'Esta sesión sólo permite consulta.')
 try:ps=[unica(S.E.crudo.get('personas'),x) for x in (rid,vid)]
 except ErrorRegistro:raise ErrorPedido(403,'Identidad actual no inequívoca.')
 if rid!=vid and not S.P.ver(ps[0],{'tipo':'ver_como'},S.P.contexto(ps[0],S.E.crudo)).get('ok'):raise ErrorPedido(403,'Vista no autorizada.')
 for p in ps:
  cp=S.P.contexto(p,S.E.crudo);roles=set(p.get('puestos') or [])
  if not S.ve_alguno(p,['bandeja']) or not roles&{'direccion','operaciones','account'}:raise ErrorPedido(404,'Pedido no disponible en tu ámbito.')
  if cid is not None:
   cs=[c for c in S.E.crudo.get('clientes') or [] if isinstance(c,dict) and c.get('id')==cid]
   if len(cs)!=1 or cs[0].get('activo') is False or cs[0].get('estado')=='baja' or S.ACT.es_activo_id(cid) is not True:raise ErrorPedido(404,'Cliente no disponible.')
   if not S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},cp).get('ok') or not (roles&{'direccion','operaciones'} or cid in cp.get('cartera_por_silla',{}).get('account',set())):raise ErrorPedido(404,'Pedido no disponible en tu ámbito.')
   if escritura and not S.P.ver(p,{'tipo':'responder_cliente','cliente_id':cid},cp).get('ok'):raise ErrorPedido(403,'No puedes registrar este pedido.')
 return ps

def receptor(S,cid):
 hoy=S.P.hoy_iso();rs=[]
 for a in S.E.crudo.get('asignaciones') or []:
  if not isinstance(a,dict) or a.get('cliente_id')!=cid or a.get('silla')!='account':continue
  try:
   if a.get('desde') and date.fromisoformat(a['desde']).isoformat()!=a['desde']:raise ValueError()
   if a.get('hasta') and date.fromisoformat(a['hasta']).isoformat()!=a['hasta']:raise ValueError()
  except (ValueError,TypeError):raise ErrorPedido(409,'Asignación de account por confirmar.')
  if (not a.get('desde') or a['desde']<=hoy) and (not a.get('hasta') or a['hasta']>=hoy):rs.append(a)
 # Dos filas vigentes son conflicto aunque apunten a la misma persona: no elegir la última.
 if len(rs)!=1:raise ErrorPedido(409,'Account actual único por confirmar.')
 a=rs[0]
 if a.get('principal') is not True or a.get('suplencia') or a.get('duda') or a.get('confianza')!='confirmada':raise ErrorPedido(409,'Account actual por confirmar; no se asigna el pedido.')
 try:p=unica(S.E.crudo.get('personas'),a.get('persona_id'))
 except ErrorRegistro:raise ErrorPedido(409,'Account activo por confirmar.')
 if 'account' not in (p.get('puestos') or []) or not S.ve_alguno(p,['bandeja']):raise ErrorPedido(409,'El account no tiene acceso actual a su bandeja.')
 cp=S.P.contexto(p,S.E.crudo)
 if cid not in cp.get('cartera_por_silla',{}).get('account',set()) or not S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},cp).get('ok'):raise ErrorPedido(409,'El receptor no tiene este cliente en su ámbito.')
 return p['id'],{k:a.get(k) for k in ('persona_id','cliente_id','silla','desde','hasta','principal','confianza','fuente','fuente_confirmacion')}

def referencias(S,rid,vid,cid):
 ps=autorizar(S,rid,vid,cid);cp=S.P.contexto(ps[1],S.E.crudo)
 with S.P.mirando_como(ps[0],S.E.crudo):d=S.modulo_recortado(ps[0],ps[1],cp,'bandeja/bandeja')
 autorizar(S,rid,vid,cid)
 if not isinstance(d,dict):raise ErrorPedido(503,'La copia de Bandeja no está disponible.')
 rows=[]
 for tipo,col in TIPOS.items():
  fs=d.get(col);fs=fs if isinstance(fs,list) else [];counts=collections.Counter(x.get('id') for x in fs if isinstance(x,dict) and isinstance(x.get('id'),str))
  for x in fs:
   if not isinstance(x,dict) or x.get('cliente_id')!=cid or not isinstance(x.get('id'),str) or not re.fullmatch(r'[A-Za-z0-9_:-]{1,150}',x['id']) or counts[x['id']]!=1 or x.get('auto') or x.get('boletin'):continue
   rows.append({'tipo':tipo,'referencia_id':x['id']})
 return rows,hash_({'generado':d.get('generado'),'fuentes':d.get('fuentes'),'referencias':sorted(rows,key=lambda x:(x['tipo'],x['referencia_id']))})

def capacidad(S,rid,vid,cid,tipo,ref):
 autorizar(S,rid,vid,cid);owner,evidencia=receptor(S,cid);rs,fuente=referencias(S,rid,vid,cid)
 if {'tipo':tipo,'referencia_id':ref} not in rs:raise ErrorPedido(409,'La referencia ya no está disponible. Recarga Bandeja.')
 owner2,evidencia2=receptor(S,cid)
 if (owner2,evidencia2)!=(owner,evidencia):raise ErrorPedido(409,'El receptor cambió durante la consulta.')
 token=hash_([VERSION,cid,tipo,ref,owner,evidencia,fuente])
 autorizar(S,rid,vid,cid)
 return owner,token

def preparar(con):
 con.execute('CREATE TABLE IF NOT EXISTS operaciones_pedidos_account_294 (intencion_id TEXT PRIMARY KEY,cliente_id TEXT NOT NULL,tipo TEXT NOT NULL,referencia_id TEXT NOT NULL,revision INTEGER NOT NULL,autor TEXT NOT NULL,receptor TEXT NOT NULL,estado TEXT NOT NULL,registrado_en TEXT NOT NULL,revision_fuente TEXT NOT NULL,huella TEXT NOT NULL,UNIQUE(cliente_id,tipo,referencia_id,revision))')
 for op in ('UPDATE','DELETE'):con.execute('CREATE TRIGGER IF NOT EXISTS pedidos294_no_'+op+' BEFORE '+op+' ON '+TABLA+" BEGIN SELECT RAISE(ABORT,'Pedido inmutable'); END")
def fingerprint(b,actor):return hash_({**b,'autor':actor})
def dto(r):
 r=dict(r)
 try:
  u=UUID(r['intencion_id'])
  b={k:r[k] for k in ('intencion_id','cliente_id','tipo','referencia_id','estado','revision_fuente')};b['revision']=r['revision']-1
  if u.version!=4 or str(u)!=r['intencion_id'] or r['tipo'] not in TIPOS or r['estado'] not in ESTADOS or type(r['revision']) is not int or r['revision']<1 or fingerprint(b,r['autor'])!=r['huella']:raise ValueError()
 except (KeyError,ValueError,TypeError,AttributeError):raise ErrorPedido(503,'Registro local incoherente.')
 return {k:r[k] for k in ('intencion_id','cliente_id','tipo','referencia_id','revision','autor','receptor','estado','registrado_en')}|{'origen':'registro_equipo','declarado':True,'envio_realizado':False,'llamada_realizada':False,'respuesta_verificada':False}
def validar(b):
 if not isinstance(b,dict) or set(b)!={'intencion_id','cliente_id','tipo','referencia_id','revision','revision_fuente','estado'}:raise ErrorPedido(400,'Campos del pedido inválidos.')
 if not isinstance(b['tipo'],str) or not isinstance(b['estado'],str) or b['tipo'] not in TIPOS or b['estado'] not in ESTADOS or type(b['revision']) is not int or b['revision']<0 or not isinstance(b['revision_fuente'],str) or not re.fullmatch('[a-f0-9]{64}',b['revision_fuente']):raise ErrorPedido(400,'Estado o revisión inválida.')
 for k in ('cliente_id','referencia_id'):
  if not isinstance(b[k],str) or not re.fullmatch(r'[A-Za-z0-9_:-]{1,150}',b[k]):raise ErrorPedido(400,'Referencia inválida.')
 try:
  u=UUID(b['intencion_id'])
  if u.version!=4 or str(u)!=b['intencion_id']:raise ValueError()
 except (ValueError,TypeError,AttributeError):raise ErrorPedido(400,'Intención UUID inválida.')
def guardar(S,con,rid,vid,b):
 validar(b);cid=b['cliente_id'];autorizar(S,rid,vid,cid,True)
 if con.in_transaction:raise ErrorPedido(503,'La conexión no es exclusiva.')
 con.execute('BEGIN IMMEDIATE')
 try:
  autorizar(S,rid,vid,cid,True);owner,token=capacidad(S,rid,vid,cid,b['tipo'],b['referencia_id']);preparar(con);fp=fingerprint(b,rid)
  old=con.execute('SELECT * FROM '+TABLA+' WHERE intencion_id=?',(b['intencion_id'],)).fetchone()
  if old:
   if old['huella']!=fp or old['receptor']!=owner:raise ErrorPedido(409,'La intención o su receptor cambió.')
   receipt=dto(old);repetida=True
  else:
   if token!=b['revision_fuente']:raise ErrorPedido(409,'La copia o el account cambió. Recarga antes de guardar.')
   old=con.execute('SELECT * FROM '+TABLA+' WHERE cliente_id=? AND tipo=? AND referencia_id=? ORDER BY revision DESC LIMIT 1',(cid,b['tipo'],b['referencia_id'])).fetchone();revision=old['revision'] if old else 0
   if revision!=b['revision']:raise ErrorPedido(409,'El pedido cambió. Conserva el intento y recarga.')
   if old is None and b['estado']!='pedido':raise ErrorPedido(409,'Primero debe existir un pedido.')
   if old is not None and old['estado']==b['estado']:raise ErrorPedido(409,'Este estado ya está registrado.')
   hora=datetime.now(timezone.utc).isoformat(timespec='microseconds');con.execute('INSERT INTO '+TABLA+' VALUES (?,?,?,?,?,?,?,?,?,?,?)',(b['intencion_id'],cid,b['tipo'],b['referencia_id'],revision+1,rid,owner,b['estado'],hora,token,fp));receipt=dto(con.execute('SELECT * FROM '+TABLA+' WHERE intencion_id=?',(b['intencion_id'],)).fetchone());repetida=False
  # Fuente/receptor/permiso se vuelven a comprobar dentro de la transacción antes del commit.
  owner2,token2=capacidad(S,rid,vid,cid,b['tipo'],b['referencia_id']);autorizar(S,rid,vid,cid,True)
  if owner2!=owner or token2!=token:raise ErrorPedido(409,'El contexto del pedido cambió durante el registro.')
  con.commit();return {'version':VERSION,'resultado':'duplicado' if repetida else 'guardado','recibo':receipt}
 except Exception:con.rollback();raise

def leer(S,con,rid,vid,cid=None):
 ps=autorizar(S,rid,vid,cid);ops=all(set(p.get('puestos') or [])&{'direccion','operaciones'} for p in ps);table=con is not None and con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(TABLA,)).fetchone();rows=[]
 if table:
  sql='SELECT p.* FROM '+TABLA+' p WHERE revision=(SELECT MAX(q.revision) FROM '+TABLA+' q WHERE q.cliente_id=p.cliente_id AND q.tipo=p.tipo AND q.referencia_id=p.referencia_id)'
  args=[]
  if cid is not None:sql+=' AND p.cliente_id=?';args=[cid]
  else:
   counts=collections.Counter(c.get('id') for c in S.E.crudo.get('clientes') or [] if isinstance(c,dict) and isinstance(c.get('id'),str));ids=[]
   for client,n in counts.items():
    if n!=1:continue
    try:autorizar(S,rid,vid,client);ids.append(client)
    except ErrorPedido:continue
   if not ids:sql+=' AND 1=0'
   else:sql+=' AND p.cliente_id IN ('+','.join('?' for _ in ids)+')';args+=ids
  if not ops:sql+=' AND p.receptor=?';args.append(vid)
  rows=con.execute(sql+" ORDER BY CASE WHEN estado='pedido' THEN 0 ELSE 1 END,registrado_en DESC LIMIT 501",args).fetchall()
 selected=[]
 for r in rows[:500]:
  try:autorizar(S,rid,vid,r['cliente_id'])
  except ErrorPedido:continue
  if not ops and r['receptor']!=vid:continue
  selected.append(dto(r))
 caps=[]
 if cid is not None:
  refs,fuente=referencias(S,rid,vid,cid);lookup={(r['tipo'],r['referencia_id']):r for r in selected}
  try:owner,evidencia=receptor(S,cid);motivo=None
  except ErrorPedido as e:owner=None;evidencia=None;motivo=str(e)
  writable=rid==vid and not piloto_lectura.activo() and owner is not None
  if writable:
   try:autorizar(S,rid,vid,cid,True)
   except ErrorPedido:writable=False
  for ref in refs:
   actual=lookup.get((ref['tipo'],ref['referencia_id']))
   caps.append({**ref,'cliente_id':cid,'receptor':owner,'revision_fuente':hash_([VERSION,cid,ref['tipo'],ref['referencia_id'],owner,evidencia,fuente]) if owner else None,'revision':actual['revision'] if actual else 0,'actual':actual,'puede_registrar':writable,'motivo':None if writable else motivo or 'Consulta: no se puede registrar en esta sesión.'})
  # Un solo snapshot por cliente para todos sus tickets: no releer N veces la misma fuente.
  _,fuente2=referencias(S,rid,vid,cid)
  if fuente2!=fuente:raise ErrorPedido(409,'La copia cambió durante la consulta.')
  if owner is not None:
   owner2,evidencia2=receptor(S,cid)
   if (owner2,evidencia2)!=(owner,evidencia):raise ErrorPedido(409,'La asignación cambió durante la consulta.')
 # Revalidar todo el ámbito consultado, incluido cada cliente que saldrá en el DTO.
 autorizar(S,rid,vid,cid)
 for r in selected:autorizar(S,rid,vid,r['cliente_id'])
 return {'version':VERSION,'cliente_id':cid,'pedidos':selected,'capacidades':caps,'truncado':len(rows)>500,'alcance':'Pedidos registrados en RO. No se han enviado mensajes ni realizado llamadas; resuelto es una declaración propia.'}

def _ambito_resumen(S,rid,vid):
 ps=autorizar(S,rid,vid);raw=S.E.crudo
 ids=[];counts=collections.Counter(c.get('id') for c in raw.get('clientes') or [] if isinstance(c,dict) and isinstance(c.get('id'),str))
 for cid,n in counts.items():
  if n!=1:continue
  try:autorizar(S,rid,vid,cid);ids.append(cid)
  except ErrorPedido as e:
   if e.codigo==503:raise
 ids.sort();ops=all(set(p.get('puestos') or [])&{'direccion','operaciones'} for p in ps)
 personas=[{**{k:p.get(k) for k in ('id','estado','activo','puestos')},'bandeja_permitida':S.ve_alguno(p,['bandeja']) is True} for p in raw.get('personas') or [] if isinstance(p,dict)]
 asignaciones=[{k:a.get(k) for k in ('cliente_id','persona_id','silla','desde','hasta','principal','confianza','duda','suplencia')} for a in raw.get('asignaciones') or [] if isinstance(a,dict) and a.get('cliente_id') in ids]
 return ids,ops,hash_([rid,vid,ids,ops,personas,asignaciones,S.P.hoy_iso()])

def leer_resumen(S,con,rid,vid,ahora=None):
 """Historia local: eventos pedido únicos, no envíos. Nunca crea persistencia."""
 ids,ops,scope=_ambito_resumen(S,rid,vid)
 ahora=ahora or datetime.now(timezone.utc)
 if not isinstance(ahora,datetime) or ahora.tzinfo is None or ahora.utcoffset() is None:raise ErrorPedido(503,'Corte de lectura sin confirmar.')
 ahora=ahora.astimezone(timezone.utc);local=ahora.astimezone(ZoneInfo('Europe/Madrid'));hoy=local.date()
 if hoy.isoformat()!=S.P.hoy_iso():raise ErrorPedido(503,'Corte y calendario no coinciden.')
 lunes=hoy-timedelta(days=hoy.weekday());inicio=datetime.combine(lunes,datetime.min.time(),tzinfo=ZoneInfo('Europe/Madrid')).astimezone(timezone.utc)
 out={'version':VERSION_RESUMEN,'generado':ahora.isoformat(),'corte_utc':ahora.isoformat(),'hoy':hoy.isoformat(),'desde':lunes.isoformat(),'hasta':hoy.isoformat(),'zona':'Europe/Madrid','estado':'sin_dato','origen':'ledger_pedidos_account_294','autor_id':None,'declarado':True,'envio_realizado':False,'llamada_realizada':False,'ejecucion_verificada':False,'filas':[],'pedidos_semana':None,'pendientes':None,'cliente_ids_autorizados':ids,'receptor_ids_autorizados':[],'scope_hash_actual':scope,'cobertura':{'ambito':'real_interseccion_vista_ACT','completa_ledger':False,'semana_en_curso':True,'truncado':False},'motivo':'Persistencia histórica no disponible.'}
 def terminar():
  if _ambito_resumen(S,rid,vid)!=(ids,ops,scope):raise ErrorPedido(409,'El ámbito cambió durante la lectura del resumen.')
  return out
 try:mili=unica(S.E.crudo.get('personas'),AUTOR_RESUMEN)
 except ErrorRegistro:out['motivo']='Autor de Operaciones por confirmar.';return terminar()
 if 'operaciones' not in (mili.get('puestos') or []) or not S.ve_alguno(mili,['bandeja']):out['motivo']='Autor de Operaciones por confirmar.';return terminar()
 out['autor_id']=AUTOR_RESUMEN
 actuales=collections.defaultdict(set)
 for cid in ids:
  try:pid,_=receptor(S,cid)
  except ErrorPedido as e:
   if e.codigo==503:raise
   continue
  if ops or pid==vid:actuales[pid].add(cid)
 out['receptor_ids_autorizados']=sorted(actuales)
 if con is None or not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(TABLA,)).fetchone():return terminar()
 args=list(ids);where='cliente_id IN ('+','.join('?' for _ in ids)+')' if ids else '1=0'
 # La secuencia completa del cliente permite resolver la última revisión incluso
 # si cambió receptor. El DTO account sigue limitado a su receptor propio.
 rs=con.execute('SELECT * FROM '+TABLA+' WHERE '+where+' ORDER BY cliente_id,tipo,referencia_id,revision LIMIT ?',args+[MAX_HISTORIA_RESUMEN+1]).fetchall()
 if len(rs)>MAX_HISTORIA_RESUMEN:out['cobertura']['truncado']=True;out['motivo']='Historia demasiado extensa para acreditar el agregado.';return terminar()
 grupos=collections.defaultdict(list);uuids=set()
 for row in rs:
  d=dto(row)
  if d['intencion_id'] in uuids:raise ErrorPedido(503,'Historia local incoherente.')
  uuids.add(d['intencion_id'])
  try:
   fecha=datetime.fromisoformat(d['registrado_en'].replace('Z','+00:00'))
   if fecha.tzinfo is None or fecha.utcoffset() is None or fecha>ahora:raise ValueError()
  except (ValueError,TypeError,AttributeError,OverflowError):raise ErrorPedido(503,'Fecha histórica sin confirmar.')
  if not isinstance(d['autor'],str) or not isinstance(d['receptor'],str):raise ErrorPedido(503,'Historia local incoherente.')
  d['_fecha']=fecha.astimezone(timezone.utc);grupos[(d['cliente_id'],d['tipo'],d['referencia_id'])].append(d)
 cuentas={pid:{'receptor_id':pid,'cliente_ids':set(cids),'pedidos_semana':0,'pendientes':0,'ultima_declaracion':None,'receptores_historicos':True,'asignacion_actual_confirmada':True} for pid,cids in actuales.items()}
 def acumular(evento,clave):
  if evento['autor']!=AUTOR_RESUMEN:return
  pid=evento['receptor']
  if not ops and pid!=vid:return
  try:p=unica(S.E.crudo.get('personas'),pid)
  except ErrorRegistro:raise ErrorPedido(503,'Receptor histórico por confirmar.')
  if 'account' not in (p.get('puestos') or []) or not S.ve_alguno(p,['bandeja']):raise ErrorPedido(503,'Receptor histórico por confirmar.')
  autorizar(S,rid,vid,evento['cliente_id'])
  c=cuentas.setdefault(pid,{'receptor_id':pid,'cliente_ids':set(),'pedidos_semana':0,'pendientes':0,'ultima_declaracion':None,'receptores_historicos':True,'asignacion_actual_confirmada':True})
  c['cliente_ids'].add(evento['cliente_id']);c[clave]+=1
  fecha=evento['_fecha'].isoformat()
  if c['ultima_declaracion'] is None or fecha>c['ultima_declaracion']:c['ultima_declaracion']=fecha
  try:actual,_=receptor(S,evento['cliente_id'])
  except ErrorPedido as e:
   if e.codigo==503:raise
   actual=None
  if actual!=pid:c['asignacion_actual_confirmada']=False
 for gs in grupos.values():
  for i,g in enumerate(gs):
   if g['revision']!=i+1 or (i==0 and g['estado']!='pedido') or (i and (g['_fecha']<gs[i-1]['_fecha'] or g['estado']==gs[i-1]['estado'])):raise ErrorPedido(503,'Secuencia histórica incoherente.')
   if g['estado']=='pedido' and inicio<=g['_fecha']<=ahora:acumular(g,'pedidos_semana')
  ultimo=gs[-1]
  if ultimo['estado']=='pedido':acumular(ultimo,'pendientes')
 for c in cuentas.values():c['cliente_ids']=sorted(c['cliente_ids'])
 out.update(estado='medido',motivo='Declaraciones locales; no mensajes enviados, llamadas o resoluciones verificadas.',filas=sorted(cuentas.values(),key=lambda c:c['receptor_id']),pedidos_semana=sum(c['pedidos_semana'] for c in cuentas.values()),pendientes=sum(c['pendientes'] for c in cuentas.values()))
 out['receptor_ids_autorizados']=sorted(cuentas)
 out['cobertura']['completa_ledger']=True
 return terminar()

def enganchar(H,S):
 original_get,original_post=H._api_get,H.api_post
 def responder(self,metodo,ruta,q,real,vista,b=None):
  if ruta==RUTA_RESUMEN and metodo!='GET':return self.responder(405,{'error':'El resumen sólo permite lectura.'})
  if ruta not in (RUTA,RUTA_RESUMEN):return original_get(self,ruta,q,real,vista) if metodo=='GET' else original_post(self,ruta,real,vista,b)
  try:
   if os.environ.get('DATABASE_URL') or os.environ.get('PGDATABASE_URL'):raise ErrorPedido(503,'Este registro requiere SQLite local verificado.')
   rid,vid=real.get('id'),vista.get('id')
   if ruta==RUTA_RESUMEN:
    if not isinstance(q,dict) or q:raise ErrorPedido(400,'El resumen no admite filtros de identidad, fechas ni cuerpo.')
    autorizar(S,rid,vid);db=getattr(S,'DB',None)
    if db is None:d=leer_resumen(S,None,rid,vid)
    elif not Path(db).exists():d=leer_resumen(S,None,rid,vid)
    else:
     with closing(sqlite3.connect(Path(db).resolve().as_uri()+'?mode=ro',uri=True)) as con:con.row_factory=sqlite3.Row;d=leer_resumen(S,con,rid,vid)
    autorizar(S,rid,vid)
    if _ambito_resumen(S,rid,vid)[2]!=d['scope_hash_actual']:raise ErrorPedido(409,'El ámbito cambió durante la lectura del resumen.')
    for r in d['filas']:
     for cid in r['cliente_ids']:autorizar(S,rid,vid,cid)
    return self.responder(200,d)
   if metodo=='GET':
    if not isinstance(q,dict) or set(q)-{'cliente_id'} or ('cliente_id' in q and (not isinstance(q['cliente_id'],list) or len(q['cliente_id'])!=1)):raise ErrorPedido(400,'No se admiten filtros de identidad.')
    cid=q['cliente_id'][0] if q else None
    autorizar(S,rid,vid,cid);db=getattr(S,'DB',None)
    if db is None:raise ErrorPedido(503,'Persistencia no disponible.')
    if not Path(db).exists():d=leer(S,None,rid,vid,cid)
    else:
     with closing(sqlite3.connect(Path(db).resolve().as_uri()+'?mode=ro',uri=True)) as con:con.row_factory=sqlite3.Row;d=leer(S,con,rid,vid,cid)
   else:
    if q:raise ErrorPedido(400,'No se admiten filtros de identidad.')
    validar(b);autorizar(S,rid,vid,b['cliente_id'],True)
    with closing(S.conectar()) as con:
     if not isinstance(con,sqlite3.Connection):raise ErrorPedido(503,'Persistencia local no disponible.')
     con.row_factory=sqlite3.Row;d=guardar(S,con,rid,vid,b)
   autorizar(S,rid,vid,b['cliente_id'] if metodo=='POST' else cid,metodo=='POST')
   if metodo=='GET':
    for r in d.get('pedidos',[]):autorizar(S,rid,vid,r['cliente_id'])
   return self.responder(200,d)
  except ErrorPedido as e:return self.responder(e.codigo,{'error':str(e)})
  except (sqlite3.Error,OSError,ValueError,TypeError,KeyError,AttributeError):return self.responder(503,{'error':'No se ha confirmado el pedido. Conserva la misma intención para reintentar.'})
 H._api_get=lambda self,ruta,q,real,vista:responder(self,'GET',ruta,q,real,vista)
 H.api_post=lambda self,ruta,real,vista,b:responder(self,'POST',ruta,{},real,vista,b)
