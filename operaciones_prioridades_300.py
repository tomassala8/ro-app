"""Rastro propio de prioridades exactas. Local, append-only; nunca envío externo."""
import hashlib
import json
import os
import re
import sqlite3
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID
import piloto_lectura
import bd_comun as bd
from contexto_tarea import texto_operativo
from operaciones_registros_269 import unica, ErrorRegistro

RUTA='/api/operaciones/prioridades'
VERSION='300.1'
TABLA='operaciones_prioridades_300'
ESTADOS=('empujado','resuelto','coti','na','anulado')
class ErrorPrioridad(Exception):
    def __init__(self,codigo,texto):self.codigo=codigo;super().__init__(texto)
def hash_(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def autorizar(S,rid,vid,escritura=False,cid=None):
    if S.E.nucleo_bloqueado:raise ErrorPrioridad(503,'Permisos actuales no disponibles.')
    if escritura and (rid!=vid or piloto_lectura.activo()):raise ErrorPrioridad(403,'Esta sesión sólo permite consulta.')
    try:ps=[unica(S.E.crudo.get('personas'),pid) for pid in (rid,vid)]
    except ErrorRegistro:raise ErrorPrioridad(403,'Identidad activa no inequívoca.')
    if rid!=vid and S.P.ver(ps[0],{'tipo':'ver_como'},S.P.contexto(ps[0],S.E.crudo)).get('ok') is not True:raise ErrorPrioridad(403,'Vista no autorizada.')
    for p in ps:
        if not set(p.get('puestos') or [])&{'direccion','operaciones'} or not S.ve_alguno(p,['mi-dia']) or not S.ve_alguno(p,['alertas']):raise ErrorPrioridad(403,'Prioridades no disponibles para esta sesión.')
        if cid is not None:
            cs=[c for c in S.E.crudo.get('clientes') or [] if isinstance(c,dict) and c.get('id')==cid]
            if len(cs)!=1 or S.ACT.es_activo_id(cid) is not True or S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},S.P.contexto(p,S.E.crudo)).get('ok') is not True:raise ErrorPrioridad(404,'Prioridad no disponible.')
    return ps

def referencias(S,rid,vid):
    ps=autorizar(S,rid,vid);cp=S.P.contexto(ps[1],S.E.crudo)
    with S.P.mirando_como(ps[0],S.E.crudo):d=S.modulo_recortado(ps[0],ps[1],cp,'alertas/p_'+vid)
    if not isinstance(d,dict) or not isinstance(d.get('alertas'),list):raise ErrorPrioridad(503,'Las prioridades actuales no están disponibles.')
    rows=d['alertas'];counts=Counter(x.get('id') for x in rows if isinstance(x,dict) and isinstance(x.get('id'),str));out={}
    if len(rows)>1000:raise ErrorPrioridad(503,'Inventario de prioridades excede el límite seguro.')
    for x in rows:
        if not isinstance(x,dict) or not isinstance(x.get('id'),str) or not re.fullmatch(r'[A-Za-z0-9_:.-]{1,180}',x['id']) or counts[x['id']]!=1:continue
        cid=x.get('cliente_id')
        if cid is not None and not isinstance(cid,str):continue
        try:autorizar(S,rid,vid,cid=cid)
        except ErrorPrioridad:continue
        # No hora de lectura: cualquier cambio de contenido/acción invalida el rastro vigente.
        out[x['id']]={'prioridad_id':x['id'],'cliente_id':cid,'fuente_revision':hash_([VERSION,vid,x])}
    autorizar(S,rid,vid)
    return out

def resolver(S,rid,vid,pid,token,escritura=False):
    autorizar(S,rid,vid,escritura)
    r=referencias(S,rid,vid).get(pid)
    if r is None:raise ErrorPrioridad(404,'Prioridad no disponible.')
    if r['fuente_revision']!=token:raise ErrorPrioridad(409,'La prioridad cambió. Recarga antes de registrar el avance.')
    autorizar(S,rid,vid,escritura,r['cliente_id']);return r

def preparar(con):
    con.execute('CREATE TABLE IF NOT EXISTS operaciones_prioridades_300 (intencion_id TEXT PRIMARY KEY,actor TEXT NOT NULL,prioridad_id TEXT NOT NULL,fuente_revision TEXT NOT NULL,dia TEXT NOT NULL,revision INTEGER NOT NULL,estado TEXT NOT NULL,nota TEXT NOT NULL,registrado_en TEXT NOT NULL,huella TEXT NOT NULL,UNIQUE(actor,prioridad_id,fuente_revision,dia,revision))')
    for op in ('UPDATE','DELETE'):con.execute("CREATE TRIGGER IF NOT EXISTS prioridades300_sin_"+op.lower()+" BEFORE "+op+" ON operaciones_prioridades_300 BEGIN SELECT RAISE(ABORT,'Rastro propio inmutable'); END")
def fingerprint(actor,b,nota):return hash_([actor,b['prioridad_id'],b['fuente_revision'],b['dia'],b['revision'],b['estado'],nota])
def dto(row):
    d=dict(row)
    b={k:d[k] for k in ('prioridad_id','fuente_revision','dia','revision','estado')};b['revision']-=1
    if d['revision']<1 or d['estado'] not in ESTADOS or d['huella']!=fingerprint(d['actor'],b,d['nota']):raise ErrorPrioridad(503,'El rastro guardado no es coherente.')
    return {k:d[k] for k in ('intencion_id','actor','prioridad_id','fuente_revision','dia','revision','estado','nota','registrado_en')}|{'declarado':True,'origen':'local','envio_realizado':False,'ejecucion_verificada':False}
def tabla_existe(con):return con is not None and con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(TABLA,)).fetchone() is not None

def leer(S,con,rid,vid):
    refs=referencias(S,rid,vid);dia=S.P.hoy_iso();out=[]
    for ref in refs.values():
        rows=[]
        if tabla_existe(con):rows=con.execute('SELECT * FROM operaciones_prioridades_300 WHERE actor=? AND prioridad_id=? AND fuente_revision=? ORDER BY registrado_en DESC,revision DESC LIMIT 21',(vid,ref['prioridad_id'],ref['fuente_revision'])).fetchall()
        historial=[dto(r) for r in rows[:20]]
        actual=None
        if tabla_existe(con):
            r=con.execute('SELECT * FROM operaciones_prioridades_300 WHERE actor=? AND prioridad_id=? AND fuente_revision=? AND dia=? ORDER BY revision DESC LIMIT 1',(vid,ref['prioridad_id'],ref['fuente_revision'],dia)).fetchone();actual=dto(r) if r else None
        out.append({**ref,'revision':actual['revision'] if actual else 0,'actual':actual,'historial':historial,'historial_truncado':len(rows)>20})
    # No devolver datos antiguos si el ámbito/catálogo cambió durante la lectura.
    final=referencias(S,rid,vid)
    out=[r for r in out if final.get(r['prioridad_id'])==refs.get(r['prioridad_id'])]
    return {'version':VERSION,'propietario':vid,'dia':dia,'prioridades':out,'puede_registrar':rid==vid and not piloto_lectura.activo(),'alcance':'Rastro declarado local; no prueba de mensaje enviado, resolución ni ejecución externa.'}

def guardar(S,con,rid,vid,b):
    keys={'prioridad_id','fuente_revision','dia','revision','estado','nota','intencion_id'}
    if not isinstance(b,dict) or set(b)!=keys or type(b.get('revision')) is not int or b['revision']<0 or b.get('estado') not in ESTADOS:raise ErrorPrioridad(400,'Campos del avance inválidos.')
    if not isinstance(b['fuente_revision'],str) or not re.fullmatch('[a-f0-9]{64}',b['fuente_revision']):raise ErrorPrioridad(400,'Referencia inválida.')
    try:
        u=UUID(b['intencion_id'])
        if u.version!=4 or str(u)!=b['intencion_id']:raise ValueError()
    except (TypeError,AttributeError,ValueError):raise ErrorPrioridad(400,'Intención UUID inválida.')
    if not isinstance(b['nota'],str) or len(b['nota'])>300:raise ErrorPrioridad(400,'Nota inválida (máximo 300 caracteres).')
    nota=texto_operativo(b['nota'],300).strip()
    if b['estado']=='resuelto' and not nota:raise ErrorPrioridad(400,'Explica qué has comprobado; sigue siendo una declaración local.')
    resolver(S,rid,vid,b['prioridad_id'],b['fuente_revision'],True)
    if con.in_transaction:raise ErrorPrioridad(503,'Se requiere una conexión exclusiva.')
    con.execute('BEGIN IMMEDIATE')
    try:
        resolver(S,rid,vid,b['prioridad_id'],b['fuente_revision'],True);preparar(con)
        h=fingerprint(rid,b,nota);old=con.execute('SELECT * FROM operaciones_prioridades_300 WHERE intencion_id=?',(b['intencion_id'],)).fetchone()
        if old:
            if old['huella']!=h:raise ErrorPrioridad(409,'Esta intención contiene otro avance.')
            recibo=dto(old);repetida=True
        else:
            if b['dia']!=S.P.hoy_iso():raise ErrorPrioridad(400,'Sólo se registra el día vigente.')
            rev=con.execute('SELECT MAX(revision) FROM operaciones_prioridades_300 WHERE actor=? AND prioridad_id=? AND fuente_revision=? AND dia=?',(rid,b['prioridad_id'],b['fuente_revision'],b['dia'])).fetchone()[0] or 0
            if rev!=b['revision']:raise ErrorPrioridad(409,'El avance cambió. Recarga; conserva tu nota.')
            con.execute('INSERT INTO operaciones_prioridades_300 VALUES (?,?,?,?,?,?,?,?,?,?)',(b['intencion_id'],rid,b['prioridad_id'],b['fuente_revision'],b['dia'],rev+1,b['estado'],nota,datetime.now(timezone.utc).isoformat(timespec='microseconds'),h))
            recibo=dto(con.execute('SELECT * FROM operaciones_prioridades_300 WHERE intencion_id=?',(b['intencion_id'],)).fetchone());repetida=False
        resolver(S,rid,vid,b['prioridad_id'],b['fuente_revision'],True)
        con.commit();return {'version':VERSION,'resultado':'duplicado' if repetida else 'guardado','recibo':recibo,'recibo_durable':True}
    except Exception:con.rollback();raise

def enganchar(H,S):
    original_get,original_post=H._api_get,H.api_post
    def responder(self,metodo,ruta,q,real,vista,b=None):
        if ruta!=RUTA:return original_get(self,ruta,q,real,vista) if metodo=='GET' else original_post(self,ruta,real,vista,b)
        try:
            if q:raise ErrorPrioridad(400,'No se admiten filtros de identidad.')
            rid,vid=real.get('id'),vista.get('id');autorizar(S,rid,vid,metodo=='POST')
            if metodo=='GET':
                db=getattr(S,'DB',None)
                if bd.es_pg():
                    with closing(S.conectar()) as con:doc=leer(S,con,rid,vid)
                elif db is None:raise ErrorPrioridad(503,'Persistencia no configurada.')
                elif not Path(db).exists():doc=leer(S,None,rid,vid)
                else:
                    with closing(sqlite3.connect(Path(db).resolve().as_uri()+'?mode=ro',uri=True)) as con:con.row_factory=sqlite3.Row;doc=leer(S,con,rid,vid)
            else:
                with closing(S.conectar()) as con:
                    if not bd.conexion_valida(con):raise ErrorPrioridad(503,'Persistencia no disponible.')
                    con.row_factory=sqlite3.Row;doc=guardar(S,con,rid,vid,b)
            autorizar(S,rid,vid,metodo=='POST');return self.responder(200,doc)
        except ErrorPrioridad as e:return self.responder(e.codigo,{'error':str(e)})
        except bd.ERRORES_BD+(OSError,ValueError,TypeError,KeyError,AttributeError):return self.responder(503,{'error':'No se ha confirmado el avance. Reintenta la misma intención.'})
    H._api_get=lambda self,ruta,q,real,vista:responder(self,'GET',ruta,q,real,vista)
    H.api_post=lambda self,ruta,real,vista,b:responder(self,'POST',ruta,{},real,vista,b)
