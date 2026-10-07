"""148: hechos manuales auditados, sin hook/API, proveedor ni evaluación de cumplimiento.
Catálogo, identidades, reloj y autorización son dependencias del servidor, nunca del payload.
"""
import hashlib,json,os,re,sqlite3,stat,uuid
from contextlib import contextmanager
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.parse import urlsplit,unquote
from zoneinfo import ZoneInfo

MADRID=ZoneInfo('Europe/Madrid')
ID=re.compile(r'^[a-zA-Z0-9_-]{1,80}$')
TIPOS={'contacto','reunion','informe_enviado'}
CANALES={'email','telefono','whatsapp','video','presencial','otro'}
MOTIVOS={'seguimiento','soporte','revision','otro'}
HOSTS=frozenset({'desk.zoho.eu','desk.zoho.com','crm.zoho.eu','crm.zoho.com','app.clickup.com'})
SCHEMA='''CREATE TABLE IF NOT EXISTS registros(id TEXT PRIMARY KEY,clave TEXT UNIQUE NOT NULL,cliente TEXT NOT NULL,actor TEXT NOT NULL,payload TEXT NOT NULL,hash TEXT NOT NULL,estado TEXT NOT NULL,creado TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS eventos(n INTEGER PRIMARY KEY AUTOINCREMENT,registro TEXT NOT NULL,operacion TEXT NOT NULL,actor TEXT NOT NULL,fecha TEXT NOT NULL,datos TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS revocaciones(clave TEXT PRIMARY KEY,registro TEXT NOT NULL,actor TEXT NOT NULL,motivo TEXT NOT NULL);'''

class ErrorEvidencia(ValueError):
 def __init__(self,codigo,motivo):self.codigo=codigo;super().__init__(motivo)

def identificador(x):return isinstance(x,str) and bool(ID.fullmatch(x))
def clave_uuid(x):
 try:return isinstance(x,str) and str(uuid.UUID(x))==x.lower()
 except (ValueError,AttributeError,TypeError):return False

def fecha_aware(x):
 if not isinstance(x,str) or len(x)>40 or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})',x):raise ErrorEvidencia(400,'Fecha inválida')
 try:f=datetime.fromisoformat(x.replace('Z','+00:00'))
 except ValueError:raise ErrorEvidencia(400,'Fecha inválida')
 if f.tzinfo is None or f.utcoffset() is None:raise ErrorEvidencia(400,'La fecha necesita zona horaria')
 return f

def enlace_seguro(x,hosts):
 if x is None or x=='':return None
 if not isinstance(x,str) or len(x)>400 or any(ord(c)<33 for c in x):raise ErrorEvidencia(400,'Referencia inválida')
 try:u=urlsplit(x);port=u.port
 except ValueError:raise ErrorEvidencia(400,'Referencia inválida')
 p=unquote(u.path)
 if u.scheme!='https' or u.hostname not in hosts or u.username or u.password or port not in (None,443) or u.query or u.fragment or not re.fullmatch(r'/[a-zA-Z0-9_./-]{1,256}',p) or '..' in p.split('/') or re.search(r'(?:token|secret|password|passcode|oauth|authorization)',p,re.I):raise ErrorEvidencia(400,'Referencia no admitida')
 return x

def validar(payload,ahora,hosts=HOSTS):
 if not isinstance(payload,dict):raise ErrorEvidencia(400,'Campos no admitidos')
 campos={'clave','cliente_id','tipo','canal','fecha','motivo','enlace','semana_inicio'}
 if payload.get('tipo')=='informe_enviado':campos.add('periodo_informe')
 if set(payload)-campos:raise ErrorEvidencia(400,'Campos no admitidos')
 if not clave_uuid(payload.get('clave')) or not identificador(payload.get('cliente_id')):raise ErrorEvidencia(400,'Identidad inválida')
 if payload.get('tipo') not in TIPOS or payload.get('canal') not in CANALES or payload.get('motivo') not in MOTIVOS:raise ErrorEvidencia(400,'Tipo, canal o motivo inválido')
 if payload['tipo']=='reunion' and payload['canal'] not in {'video','telefono','presencial','otro'}:raise ErrorEvidencia(400,'Canal de reunión inválido')
 f=fecha_aware(payload.get('fecha'))
 if f>ahora:raise ErrorEvidencia(400,'Un hecho realizado no puede tener fecha futura')
 local=f.astimezone(MADRID);dia=local.date();lunes=dia-timedelta(days=dia.weekday())
 if 'semana_inicio' in payload and payload['semana_inicio']!=lunes.isoformat():raise ErrorEvidencia(400,'El periodo no coincide con la fecha en Madrid')
 if payload['tipo']=='informe_enviado':
  periodo=payload.get('periodo_informe')
  if not isinstance(periodo,str) or not re.fullmatch(r'[1-9]\d{3}-(?:0[1-9]|1[0-2])',periodo) or periodo>dia.strftime('%Y-%m'):raise ErrorEvidencia(400,'Indica el mes del informe, sin periodos futuros')
  if payload['canal'] not in {'email','whatsapp','otro'}:raise ErrorEvidencia(400,'Canal de envío inválido')
  if not enlace_seguro(payload.get('enlace'),hosts):raise ErrorEvidencia(400,'El envío declarado requiere una referencia admitida')
 d={'cliente_id':payload['cliente_id'],'tipo':payload['tipo'],'canal':payload['canal'],'motivo':payload['motivo'],'fecha':f.astimezone(timezone.utc).isoformat(),'fecha_madrid':dia.isoformat(),'semana_inicio':lunes.isoformat(),'mes':dia.strftime('%Y-%m'),'enlace':enlace_seguro(payload.get('enlace'),hosts),'source_kind':'registro_equipo','verificacion_externa':False}
 if payload['tipo']=='informe_enviado':d['periodo_informe']=periodo
 return d

class ArchivoEvidencias:
 def __init__(self,ruta,catalogo,personas,puede_ver,puede_revocar=None,ahora=None,hosts=HOSTS):
  self.ruta=Path(ruta).absolute();self.catalogo=catalogo;self.personas=personas;self.puede_ver=puede_ver;self.puede_revocar=puede_revocar or (lambda actor,cid,registro:False);self.ahora=ahora or (lambda:datetime.now(timezone.utc));self.hosts=frozenset(hosts)
  parent=self.ruta.parent
  if not parent.exists():parent.mkdir(mode=0o700,parents=True)
  if any(p.is_symlink() for p in (parent,*parent.parents)) or stat.S_IMODE(parent.stat().st_mode)&0o077:raise ErrorEvidencia(503,'Depósito no privado')
  if self.ruta.is_symlink():raise ErrorEvidencia(503,'Archivo no admitido')
  try:fd=os.open(self.ruta,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);os.close(fd)
  except FileExistsError:pass
  self._privado()
  with self._conectar() as con:con.executescript(SCHEMA)
 def _privado(self):
  fd=os.open(self.ruta,os.O_RDONLY|os.O_NOFOLLOW)
  try:s=os.fstat(fd)
  finally:os.close(fd)
  if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1 or stat.S_IMODE(s.st_mode)!=0o600:raise ErrorEvidencia(503,'Archivo no privado')
 @contextmanager
 def _conectar(self):
  self._privado();con=sqlite3.connect(self.ruta,timeout=5);con.row_factory=sqlite3.Row
  try:
   with con:yield con
  finally:con.close()
 def _scope(self,real,vista,cid,escritura=False):
  if not identificador(real) or not identificador(vista) or not identificador(cid):raise ErrorEvidencia(403,'Ámbito no autorizado')
  if escritura and real!=vista:raise ErrorEvidencia(403,'Ver como sólo permite lectura')
  for pid in (real,vista):
   p=self.personas.get(pid)
   if not isinstance(p,dict) or p.get('id')!=pid or p.get('estado')!='activo' or p.get('activo') is False:raise ErrorEvidencia(403,'Identidad no activa')
  c=self.catalogo.get(cid)
  if not isinstance(c,dict) or c.get('activo_confirmado') is not True:raise ErrorEvidencia(403,'Cliente no activo confirmado')
  if self.puede_ver(real,cid) is not True or self.puede_ver(vista,cid) is not True:raise ErrorEvidencia(403,'Cliente fuera del ámbito')
 def _dto(self,r):
  d=json.loads(r['payload']);return {**d,'id':r['id'],'registrado_por':r['actor'],'registrado_en':r['creado'],'estado':r['estado'],'cumplimiento':None}
 def registrar(self,real,vista,payload):
  self._scope(real,vista,payload.get('cliente_id') if isinstance(payload,dict) else None,True)
  ahora=self.ahora()
  if ahora.tzinfo is None:raise ErrorEvidencia(503,'Reloj sin zona')
  d=validar(payload,ahora,self.hosts);texto=json.dumps(d,sort_keys=True,separators=(',',':'));h=hashlib.sha256(texto.encode()).hexdigest();clave=payload['clave'].lower()
  with self._conectar() as con:
   con.execute('BEGIN IMMEDIATE')
   self._scope(real,vista,d['cliente_id'],True)
   r=con.execute('SELECT * FROM registros WHERE clave=?',(clave,)).fetchone()
   if r:
    if r['actor']!=real or r['hash']!=h:raise ErrorEvidencia(409,'Clave utilizada para otro hecho')
    return {'resultado':'duplicado','registro':self._dto(r)}
   rid=str(uuid.uuid4());stamp=ahora.astimezone(timezone.utc).isoformat()
   con.execute('INSERT INTO registros VALUES (?,?,?,?,?,?,?,?)',(rid,clave,d['cliente_id'],real,texto,h,'declarado',stamp))
   con.execute('INSERT INTO eventos(registro,operacion,actor,fecha,datos) VALUES (?,?,?,?,?)',(rid,'crear',real,stamp,texto))
   r=con.execute('SELECT * FROM registros WHERE id=?',(rid,)).fetchone()
  return {'resultado':'aceptado','registro':self._dto(r)}
 def revocar(self,real,vista,cid,registro_id,clave,motivo):
  self._scope(real,vista,cid,True)
  if not clave_uuid(registro_id) or not clave_uuid(clave) or motivo not in {'correccion','duplicado','no_realizado'}:raise ErrorEvidencia(400,'Revocación inválida')
  registro_id,clave=registro_id.lower(),clave.lower()
  with self._conectar() as con:
   con.execute('BEGIN IMMEDIATE');self._scope(real,vista,cid,True);r=con.execute('SELECT * FROM registros WHERE id=? AND cliente=?',(registro_id,cid)).fetchone()
   if not r:raise ErrorEvidencia(404,'Registro no encontrado')
   if r['actor']!=real and self.puede_revocar(real,cid,self._dto(r)) is not True:raise ErrorEvidencia(403,'No puedes revocar este registro')
   old=con.execute('SELECT * FROM revocaciones WHERE clave=?',(clave,)).fetchone()
   if old:
    if (old['registro'],old['actor'],old['motivo'])!=(registro_id,real,motivo):raise ErrorEvidencia(409,'Clave utilizada para otra revocación')
    return {'resultado':'duplicado','registro':self._dto(r)}
   if r['estado']=='revocado':raise ErrorEvidencia(409,'Registro ya revocado')
   con.execute('UPDATE registros SET estado=? WHERE id=?',('revocado',registro_id));con.execute('INSERT INTO revocaciones VALUES (?,?,?,?)',(clave,registro_id,real,motivo))
   con.execute('INSERT INTO eventos(registro,operacion,actor,fecha,datos) VALUES (?,?,?,?,?)',(registro_id,'revocar',real,self.ahora().astimezone(timezone.utc).isoformat(),json.dumps({'motivo':motivo})))
   r=con.execute('SELECT * FROM registros WHERE id=?',(registro_id,)).fetchone()
  return {'resultado':'aceptado','registro':self._dto(r)}
 def listar(self,real,vista,cid,semana_inicio=None):
  self._scope(real,vista,cid)
  if semana_inicio is not None:
   try:f=datetime.fromisoformat(semana_inicio)
   except (ValueError,TypeError):raise ErrorEvidencia(400,'Periodo inválido')
   if f.strftime('%Y-%m-%d')!=semana_inicio or f.weekday()!=0:raise ErrorEvidencia(400,'Se necesita el lunes exacto del periodo')
  with self._conectar() as con:rows=con.execute('SELECT * FROM registros WHERE cliente=? ORDER BY creado DESC',(cid,)).fetchall()
  dto=[self._dto(r) for r in rows];dto=[r for r in dto if semana_inicio is None or r['semana_inicio']==semana_inicio]
  return {'cliente_id':cid,'registros':dto,'cobertura':{'source_kind':'registro_equipo','contacto_exhaustivo':False,'verificacion_externa':False},'cumplimiento':None}
