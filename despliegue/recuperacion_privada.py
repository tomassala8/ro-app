"""163: respaldo/restauración privada explícita; nunca publica ni sustituye un runtime.
El operador debe detener mutaciones para coherencia entre bases/configuración.
"""
import hashlib,json,os,re,sqlite3,stat,tempfile
from pathlib import Path

MAX=64*1024*1024
EXT={'sqlite':'.db','json':'.json','jsonl':'.jsonl','texto':'.txt'}


def sha(b):return hashlib.sha256(b).hexdigest()
def pares(xs):
 d={}
 for k,v in xs:
  if k in d:raise ValueError('JSON ambiguo.')
  d[k]=v
 return d

def regular(p):
 p=Path(p)
 if not p.is_absolute() or any(q.is_symlink() for q in (p,*p.parents)):raise ValueError('Ruta enlazada/no absoluta.')
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  s=os.fstat(fd)
  if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1 or s.st_size>MAX:raise ValueError('Archivo no regular o excesivo.')
  data=b''
  while True:
   trozo=os.read(fd,min(1024*1024,MAX+1-len(data)))
   if not trozo:break
   data+=trozo
   if len(data)>MAX:raise ValueError('Archivo excesivo.')
  fin=os.fstat(fd)
  if (s.st_size,s.st_mtime_ns)!=(fin.st_size,fin.st_mtime_ns):raise ValueError('Fuente cambiada durante lectura.')
  return data
 finally:os.close(fd)

def validar(data,tipo):
 if tipo not in EXT:raise ValueError('Tipo desconocido.')
 if tipo!='sqlite':
  text=data.decode('utf-8')
  if tipo=='json':json.loads(text,object_pairs_hook=pares)
  if tipo=='jsonl':
   for linea in text.splitlines():json.loads(linea,object_pairs_hook=pares)
  return None
 with tempfile.TemporaryDirectory(prefix='ro_validar_163_') as tmp:
  p=Path(tmp)/'fixture.db';p.write_bytes(data)
  con=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)
  try:
   if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('SQLite inválida.')
   nombres=[r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
   return {n:con.execute('SELECT count(*) FROM "'+n.replace('"','""')+'"').fetchone()[0] for n in nombres}
  finally:con.close()

def escribir(p,data):
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:
  with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 except Exception:raise

def nuevo(destino):
 p=Path(destino)
 if not p.is_absolute() or any(x.is_symlink() for x in (p,*p.parents)) or not p.parent.is_dir() or stat.S_IMODE(p.parent.stat().st_mode)&0o077:raise ValueError('Padre privado/absoluto requerido.')
 p.mkdir(mode=0o700)  # exclusivo: ni reemplazo ni merge de destino previo.
 return p

def crear(origenes,destino,*,quiescente=False,codigo_sha256=None,fuentes_sha256=None):
 if quiescente is not True:raise ValueError('Detén mutaciones antes de respaldar el conjunto.')
 if not isinstance(origenes,dict) or not origenes:raise ValueError('Fuentes explícitas requeridas.')
 datos={};filas={};total=0
 for alias,o in origenes.items():
  if not isinstance(alias,str) or not re.fullmatch(r'[a-z0-9_-]{1,60}',alias) or not isinstance(o,dict) or set(o)!={'tipo','ruta'} or o['tipo'] not in EXT:raise ValueError('Fuente no válida.')
  ruta=Path(o['ruta']);tipo=o['tipo']
  if tipo=='sqlite':
   regular(ruta)  # no enlaces/hardlinks ni archivos especiales.
   with tempfile.TemporaryDirectory(prefix='ro_snapshot_163_') as tmp:
    plano=Path(tmp)/'snapshot.db';src=sqlite3.connect(ruta.as_uri()+'?mode=ro',uri=True);dst=sqlite3.connect(plano)
    try:src.backup(dst)
    finally:src.close();dst.close()
    data=plano.read_bytes()
  else:data=regular(ruta)
  total+=len(data)
  if total>MAX:raise ValueError('Conjunto excesivo.')
  filas[alias]=validar(data,tipo);datos[alias]=(tipo,data)
 out=nuevo(destino)
 man={'version':1,'coherencia':'operador_detiene_mutaciones','codigo_sha256':codigo_sha256,'fuentes_sha256':fuentes_sha256,'archivos':{}}
 for alias,(tipo,data) in datos.items():
  nombre=alias+EXT[tipo];escribir(out/nombre,data)
  man['archivos'][alias]={'archivo':nombre,'tipo':tipo,'bytes':len(data),'sha256':sha(data),'filas':filas[alias]}
 b=json.dumps(man,sort_keys=True,separators=(',',':')).encode();escribir(out/'manifiesto.json',b)
 return {'sha256_manifiesto':sha(b),'archivos':len(datos),'bytes':total}

def restaurar(bundle,destino,sha256_manifiesto,*,requeridos):
 root=Path(bundle)
 if not root.is_absolute() or any(x.is_symlink() for x in (root,*root.parents)) or not root.is_dir() or stat.S_IMODE(root.stat().st_mode)&0o077:raise ValueError('Bundle privado requerido.')
 if stat.S_IMODE((root/'manifiesto.json').lstat().st_mode)!=0o600:raise ValueError('Manifiesto no privado.')
 b=regular(root/'manifiesto.json')
 if not isinstance(sha256_manifiesto,str) or not re.fullmatch(r'[a-f0-9]{64}',sha256_manifiesto) or sha(b)!=sha256_manifiesto:raise ValueError('Manifiesto no coincide con ancla confiable.')
 m=json.loads(b,object_pairs_hook=pares)
 if set(m)!={'version','coherencia','codigo_sha256','fuentes_sha256','archivos'} or m['version']!=1 or not isinstance(m['archivos'],dict) or not set(requeridos)<=set(m['archivos']):raise ValueError('Bundle incompleto.')
 data={};total=0
 for alias,v in m['archivos'].items():
  if not re.fullmatch(r'[a-z0-9_-]{1,60}',alias) or not isinstance(v,dict) or set(v)!={'archivo','tipo','bytes','sha256','filas'} or v['tipo'] not in EXT or v['archivo']!=alias+EXT[v['tipo']]:raise ValueError('Ruta/contrato de archivo inválido.')
  p=root/v['archivo']
  if stat.S_IMODE(p.lstat().st_mode)!=0o600:raise ValueError('Archivo no privado.')
  raw=regular(p);total+=len(raw)
  if total>MAX or type(v['bytes']) is not int or v['bytes']!=len(raw) or sha(raw)!=v['sha256'] or validar(raw,v['tipo'])!=v['filas']:raise ValueError('Archivo alterado.')
  data[v['archivo']]=raw
 if {p.name for p in root.iterdir()}!={*data,'manifiesto.json'}:raise ValueError('Bundle con archivos desconocidos.')
 out=nuevo(destino)
 for n,raw in data.items():escribir(out/n,raw)
 escribir(out/'manifiesto.json',b)  # marcador final; un fallo previo deja destino NO confirmado.
 return {'restaurada':True,'archivos':len(data),'bytes':total,'reemplazo_runtime':False}
