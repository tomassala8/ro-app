"""Opinión semanal declarada: pedido != conseguida. SQLite append-only local.
Sin IO al importar/enganchar; ninguna herramienta externa recibe mensajes.
"""
import hashlib
import json
import os
import re
import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID
import piloto_lectura
import bd_comun as bd
from contexto_tarea import texto_operativo
from operaciones_registros_269 import unica, ErrorRegistro

RUTA = '/api/operaciones/feedback'
VERSION = '273.1'
ESTADOS = ('pedida', 'conseguida', 'sin_opinion')
TABLA = 'operaciones_feedback_273'

class ErrorFeedback(Exception):
    def __init__(self, codigo, texto): self.codigo = codigo; super().__init__(texto)

def semana_actual(S):
    hoy = date.fromisoformat(S.P.hoy_iso())
    return (hoy-timedelta(days=hoy.weekday())).isoformat()

def autorizar(S, rid, vid, cid, escritura=False):
    if S.E.nucleo_bloqueado: raise ErrorFeedback(503, 'Permisos actuales no disponibles.')
    if escritura and (rid != vid or piloto_lectura.activo()): raise ErrorFeedback(403, 'Esta sesión sólo permite consulta.')
    crudo = S.E.crudo
    try: ps = [unica(crudo.get('personas'), p) for p in (rid, vid)]
    except ErrorRegistro: raise ErrorFeedback(403, 'Identidad activa no inequívoca.')
    if rid != vid and S.P.ver(ps[0], {'tipo':'ver_como'}, S.P.contexto(ps[0], crudo)).get('ok') is not True:
        raise ErrorFeedback(403, 'La vista de otra persona no está autorizada.')
    clientes = [c for c in crudo.get('clientes', []) if c.get('id') == cid]
    if not isinstance(cid, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', cid) or len(clientes) != 1 or S.ACT.es_activo_id(cid) is not True:
        raise ErrorFeedback(404, 'No se puede consultar la opinión de este cliente.')
    for p in ps:
        cp = S.P.contexto(p, crudo)
        roles = set(p.get('puestos') or [])
        cartera = cp.get('cartera_por_silla', {}).get('account', set())
        if (not S.ve_alguno(p, ['bandeja']) or not S.P.ver(p, {'tipo':'cliente_detalle', 'cliente_id':cid}, cp).get('ok') or
                not (roles & {'direccion','operaciones'} or ('account' in roles and cid in cartera))):
            raise ErrorFeedback(404, 'No se puede consultar la opinión de este cliente.')
    return {'puede_registrar':rid == vid and not piloto_lectura.activo(), 'solo_lectura':rid != vid or piloto_lectura.activo()}

def preparar(con):
    con.execute('CREATE TABLE IF NOT EXISTS operaciones_feedback_273 (intencion_id TEXT PRIMARY KEY, cliente_id TEXT NOT NULL, semana TEXT NOT NULL, revision INTEGER NOT NULL, autor TEXT NOT NULL, registrado_en TEXT NOT NULL, estado TEXT NOT NULL, nota TEXT NOT NULL, huella TEXT NOT NULL, UNIQUE(cliente_id,semana,revision))')
    for op in ('UPDATE', 'DELETE'):
        con.execute("CREATE TRIGGER IF NOT EXISTS feedback273_sin_"+op.lower()+" BEFORE "+op+" ON operaciones_feedback_273 BEGIN SELECT RAISE(ABORT,'Opinión declarada inmutable'); END")

def huella(cid, semana, revision, actor, estado, nota):
    return hashlib.sha256(json.dumps([cid, semana, revision, actor, estado, nota], ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()

def dto(row):
    d = dict(row)
    try:
        s = date.fromisoformat(d['semana'])
        if s.weekday()!=0 or s.isoformat()!=d['semana'] or type(d['revision']) is not int or d['revision']<1 or d['estado'] not in ESTADOS:
            raise ValueError()
        if not isinstance(d['nota'],str) or len(d['nota'])>300 or d['nota']!=texto_operativo(d['nota'],300): raise ValueError()
        if d['huella'] != huella(d['cliente_id'], d['semana'], d['revision']-1, d['autor'], d['estado'], d['nota']): raise ValueError()
        uid=UUID(d['intencion_id'])
        if uid.version!=4 or str(uid)!=d['intencion_id']:raise ValueError()
    except (ValueError,TypeError,KeyError,AttributeError): raise ErrorFeedback(503, 'El registro local no es coherente.')
    return {k:d[k] for k in ('intencion_id','cliente_id','semana','revision','autor','registrado_en','estado','nota')} | {
        'origen':'local', 'declarado':True, 'envio_realizado':False, 'respuesta_verificada':False}

def leer(S, con, rid, vid, cid):
    caps = autorizar(S,rid,vid,cid)
    semana = semana_actual(S)
    rows=[]
    if con is not None and con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TABLA,)).fetchone():
        rows=con.execute('SELECT * FROM operaciones_feedback_273 WHERE cliente_id=? ORDER BY registrado_en DESC,revision DESC LIMIT 101',(cid,)).fetchall()
    historia=[dto(r) for r in rows[:100]]
    # El estado de esta semana se busca de forma independiente al límite histórico.
    actual=None
    if con is not None and rows:
        r=con.execute('SELECT * FROM operaciones_feedback_273 WHERE cliente_id=? AND semana=? ORDER BY revision DESC LIMIT 1',(cid,semana)).fetchone()
        actual=dto(r) if r else None
    autorizar(S,rid,vid,cid)
    return {'version':VERSION,'cliente_id':cid,'semana':semana,'revision':actual['revision'] if actual else 0,
            'actual':actual,'historial':historia,'historial_truncado':len(rows)>100,'capacidades':caps,
            'alcance':'Declaración propia local, no prueba de envío, recepción automática, calidad del lead ni venta.'}

def validar(S, b, actor):
    requeridos={'cliente_id','semana','estado','revision','intencion_id'}
    if not isinstance(b,dict) or not requeridos <= set(b) or set(b)-requeridos-{'nota'}: raise ErrorFeedback(400,'Campos de la opinión inválidos.')
    if b['estado'] not in ESTADOS or type(b['revision']) is not int or b['revision']<0: raise ErrorFeedback(400,'Estado o revisión inválidos.')
    try:
        u=UUID(b['intencion_id']); s=date.fromisoformat(b['semana'])
        if str(u)!=b['intencion_id'] or u.version!=4 or s.isoformat()!=b['semana'] or s.weekday()!=0 or s>date.fromisoformat(S.P.hoy_iso()):raise ValueError()
    except (ValueError,TypeError,AttributeError):raise ErrorFeedback(400,'Semana o intención inválidas.')
    nota=b.get('nota','')
    if not isinstance(nota,str) or len(nota)>300 or any(ord(c)<32 and c not in '\n\t' for c in nota):raise ErrorFeedback(400,'Nota inválida (máximo300 caracteres).')
    return texto_operativo(nota,300)

def guardar(S,con,rid,vid,b):
    cid=b.get('cliente_id') if isinstance(b,dict) else None
    autorizar(S,rid,vid,cid,True);nota=validar(S,b,rid)
    if con.in_transaction:raise ErrorFeedback(503,'La conexión debe ser exclusiva para este registro.')
    con.execute('BEGIN IMMEDIATE')
    try:
        autorizar(S,rid,vid,cid,True);preparar(con)
        hash_=huella(cid,b['semana'],b['revision'],rid,b['estado'],nota)
        previa=con.execute('SELECT * FROM operaciones_feedback_273 WHERE intencion_id=?',(b['intencion_id'],)).fetchone()
        if previa:
            if previa['huella']!=hash_:raise ErrorFeedback(409,'La intención ya existe con otro contenido.')
            recibo=dto(previa);repetida=True
        else:
            if b['semana']!=semana_actual(S):raise ErrorFeedback(400,'Una nueva opinión sólo admite la semana vigente.')
            actual=con.execute('SELECT MAX(revision) FROM operaciones_feedback_273 WHERE cliente_id=? AND semana=?',(cid,b['semana'])).fetchone()[0] or 0
            if actual!=b['revision']:raise ErrorFeedback(409,'La opinión cambió. Recarga antes de guardar; tu nota se conserva.')
            hora=datetime.now(timezone.utc).isoformat(timespec='microseconds')
            con.execute('INSERT INTO operaciones_feedback_273 VALUES (?,?,?,?,?,?,?,?,?)',(b['intencion_id'],cid,b['semana'],actual+1,rid,hora,b['estado'],nota,hash_))
            recibo=dto(con.execute('SELECT * FROM operaciones_feedback_273 WHERE intencion_id=?',(b['intencion_id'],)).fetchone());repetida=False
        autorizar(S,rid,vid,cid,True)
        con.commit()
        return {'version':VERSION,'cliente_id':cid,'semana':b['semana'],'intencion_id':b['intencion_id'],
                'resultado':'duplicado' if repetida else 'guardado','recibo':recibo}
    except Exception:
        con.rollback();raise

def enganchar(H,S):
    """Root puede instalar el hook. No abre DB ni cambia el servidor al importar."""
    original_get,original_post=H._api_get,H.api_post
    def responder(self,metodo,ruta,q,real,vista,b=None):
        if ruta!=RUTA:return original_get(self,ruta,q,real,vista) if metodo=='GET' else original_post(self,ruta,real,vista,b)
        try:
            rid,vid=real.get('id'),vista.get('id')
            if metodo=='GET':
                if not isinstance(q,dict) or set(q)!={'cliente_id'} or len(q['cliente_id'])!=1:raise ErrorFeedback(400,'Elige un solo cliente; no se admiten filtros de identidad.')
                cid=q['cliente_id'][0];autorizar(S,rid,vid,cid)
                # Un GET nunca crea la base ni una tabla: archivo configurado por el servidor.
                db=getattr(S,'DB',None)
                if bd.es_pg():
                    with closing(S.conectar()) as con:doc=leer(S,con,rid,vid,cid)
                elif db is None:raise ErrorFeedback(503,'Ruta de persistencia local no disponible.')
                elif not Path(db).exists():doc=leer(S,None,rid,vid,cid)
                else:
                    with closing(sqlite3.connect(Path(db).resolve().as_uri()+'?mode=ro',uri=True)) as con:
                        con.row_factory=sqlite3.Row;doc=leer(S,con,rid,vid,cid)
            else:
                if q:raise ErrorFeedback(400,'No se admiten filtros de identidad.')
                cid=b.get('cliente_id') if isinstance(b,dict) else None;autorizar(S,rid,vid,cid,True)
                with closing(S.conectar()) as con:
                    if not bd.conexion_valida(con):raise ErrorFeedback(503,'Persistencia local no disponible.')
                    con.row_factory=sqlite3.Row;doc=guardar(S,con,rid,vid,b)
            autorizar(S,rid,vid,cid,metodo=='POST')
            return self.responder(200,doc)
        except ErrorFeedback as e:return self.responder(e.codigo,{'error':str(e)})
        except bd.ERRORES_BD+(OSError,ValueError,TypeError,KeyError,AttributeError):return self.responder(503,{'error':'No se ha confirmado el registro local. Reintenta la misma intención.'})
    H._api_get=lambda self,ruta,q,real,vista:responder(self,'GET',ruta,q,real,vista)
    H.api_post=lambda self,ruta,real,vista,b:responder(self,'POST',ruta,{},real,vista,b)
