"""Notas humanas del equipo: declaraciones locales, nunca decisiones laborales."""
import hashlib
import json
import os
import re
import sqlite3
from contextlib import closing
from datetime import datetime,timezone
import operaciones_registros_269 as O
import operaciones_registros_272 as C

RUTA='/api/operaciones/notas-equipo'
VERSION='281.1'
ACCIONES=('mantener','formar','reorientar','salida')

def autorizar(S,rid,vid,pid,escritura=False):
    ps=O.autorizar(S,rid,vid,escritura)
    O.unica(S.E.crudo.get('personas'),pid)
    for p in ps:
        if S.P.ver(p,{'tipo':'notas_persona','persona_id':pid},S.P.contexto(p,S.E.crudo)).get('ok') is not True:
            raise O.ErrorRegistro(403,'Notas fuera de tu ámbito actual.')
    return ps

def validar(b):
    campos={'persona_id','periodo','nota','prueba','accion_propuesta','revision','intencion_id'}
    if (not isinstance(b,dict) or set(b)!=campos or not isinstance(b['persona_id'],str) or
            type(b['revision']) is not int or b['revision']<0 or not C.uuid4(b['intencion_id']) or
            (b['nota'] is not None and (type(b['nota']) is not int or not 1<=b['nota']<=10)) or
            (b['accion_propuesta'] is not None and b['accion_propuesta'] not in ACCIONES) or
            not isinstance(b['periodo'],str) or not re.fullmatch(r'\d{4}-(?:0[1-9]|1[0-2])',b['periodo'])):
        raise O.ErrorRegistro(400,'Nota humana inválida.')
    return {**b,'prueba':C.texto(b['prueba'],300,True)}

def huella(actor,b):
    return hashlib.sha256(json.dumps({'actor':actor,'body':b},sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def preparar(con):
    con.execute('CREATE TABLE IF NOT EXISTS operaciones_notas_equipo_281 (id INTEGER PRIMARY KEY AUTOINCREMENT, persona_id TEXT NOT NULL, periodo TEXT NOT NULL, revision INTEGER NOT NULL, autor TEXT NOT NULL, hora TEXT NOT NULL, nota INTEGER, prueba TEXT NOT NULL, accion TEXT, intencion TEXT NOT NULL, huella TEXT NOT NULL, UNIQUE(persona_id,revision), UNIQUE(autor,intencion))')
    for accion in ('UPDATE','DELETE'):
        con.execute("CREATE TRIGGER IF NOT EXISTS operaciones_281_sin_"+accion.lower()+" BEFORE "+accion+" ON operaciones_notas_equipo_281 BEGIN SELECT RAISE(ABORT,'Nota humana inmutable'); END")

def decodificar(r):
    try:
        b=validar({'persona_id':r['persona_id'],'periodo':r['periodo'],'nota':r['nota'],'prueba':r['prueba'],'accion_propuesta':r['accion'],'revision':r['revision']-1,'intencion_id':r['intencion']})
        t=datetime.fromisoformat(r['hora'])
        if t.tzinfo is None or t>datetime.now(timezone.utc) or huella(r['autor'],b)!=r['huella']:raise ValueError()
    except (O.ErrorRegistro,ValueError,TypeError,KeyError):raise O.ErrorRegistro(503,'Nota almacenada incoherente.')
    return {'persona_id':r['persona_id'],'periodo':r['periodo'],'revision':r['revision'],'nota':r['nota'],'prueba':r['prueba'],
            'accion_propuesta':r['accion'],'autor':r['autor'],'registrado_en':r['hora'],'declarado':True,
            'puntuacion_automatica':False,'decision_laboral':False,'envio_realizado':False}

def ultima(con,pid):
    return con.execute('SELECT * FROM operaciones_notas_equipo_281 WHERE persona_id=? ORDER BY revision DESC LIMIT 1',(pid,)).fetchone()

def listar(S,con,rid,vid,pid):
    autorizar(S,rid,vid,pid)
    r=ultima(con,pid) if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='operaciones_notas_equipo_281'").fetchone() else None
    d=decodificar(r) if r else None
    autorizar(S,rid,vid,pid)
    puede=True
    try:autorizar(S,rid,vid,pid,True)
    except O.ErrorRegistro as e:
        if e.codigo!=403:raise
        puede=False
    return {'version':VERSION,'persona_id':pid,'periodo_actual':S.P.hoy_iso()[:7],'revision':r['revision'] if r else 0,'registro':d,'puede_registrar':puede,
            'cobertura':'Declaración humana local; no KPI objetivo ni decisión laboral.'}

def guardar(S,con,rid,vid,b):
    b=validar(b);pid=b['persona_id'];autorizar(S,rid,vid,pid,True)
    if con.in_transaction:raise O.ErrorRegistro(503,'Se necesita una conexión exclusiva.')
    con.execute('BEGIN IMMEDIATE')
    try:
        autorizar(S,rid,vid,pid,True);preparar(con)
        digest=huella(rid,b)
        replay=con.execute('SELECT * FROM operaciones_notas_equipo_281 WHERE autor=? AND intencion=?',(rid,b['intencion_id'])).fetchone()
        if replay:
            if replay['huella']!=digest:raise O.ErrorRegistro(409,'Esta intención tiene otro contenido.')
            recibo=decodificar(replay);resultado='duplicado'
        else:
            if b['periodo']!=S.P.hoy_iso()[:7]:raise O.ErrorRegistro(400,'Una nota nueva exige el período actual del servidor.')
            r=ultima(con,pid);revision=r['revision'] if r else 0
            if r:decodificar(r)
            if revision!=b['revision']:raise O.ErrorRegistro(409,'La nota cambió. Vuelve a leerla.')
            cur=con.execute('INSERT INTO operaciones_notas_equipo_281 (persona_id,periodo,revision,autor,hora,nota,prueba,accion,intencion,huella) VALUES (?,?,?,?,?,?,?,?,?,?)',
                (pid,b['periodo'],revision+1,rid,datetime.now(timezone.utc).isoformat(),b['nota'],b['prueba'],b['accion_propuesta'],b['intencion_id'],digest))
            recibo=decodificar(con.execute('SELECT * FROM operaciones_notas_equipo_281 WHERE id=?',(cur.lastrowid,)).fetchone());resultado='guardado'
        autorizar(S,rid,vid,pid,True);con.commit()
        return {'version':VERSION,'resultado':resultado,'intencion_id':b['intencion_id'],'recibo':recibo}
    except Exception:con.rollback();raise

def enganchar(H,S):
    get_orig,post_orig=H._api_get,H.api_post
    def responder(self,metodo,ruta,q,real,vista,b=None):
        if ruta!=RUTA:return get_orig(self,ruta,q,real,vista) if metodo=='GET' else post_orig(self,ruta,real,vista,b)
        try:
            rid,vid=real.get('id'),vista.get('id')
            if metodo=='GET':
                if set(q)!={'persona_id'} or not isinstance(q['persona_id'],list) or len(q['persona_id'])!=1:raise O.ErrorRegistro(400,'Selecciona una persona exacta.')
                pid=q['persona_id'][0]
            else:pid=b.get('persona_id') if isinstance(b,dict) else None
            autorizar(S,rid,vid,pid,metodo=='POST')
            if os.environ.get('DATABASE_URL') or os.environ.get('PGDATABASE_URL'):raise O.ErrorRegistro(503,'Notas locales requieren SQLite verificado.')
            with closing(S.conectar()) as con:
                if not isinstance(con,sqlite3.Connection):raise O.ErrorRegistro(503,'Persistencia local no disponible.')
                con.row_factory=sqlite3.Row
                d=listar(S,con,rid,vid,pid) if metodo=='GET' else guardar(S,con,rid,vid,b)
            autorizar(S,rid,vid,pid,metodo=='POST')
            return self.responder(200,d)
        except O.ErrorRegistro as e:return self.responder(e.codigo,{'error':str(e)})
        except (sqlite3.Error,OSError,ValueError,TypeError,KeyError,AttributeError):return self.responder(503,{'error':'Nota local no disponible; no se confirma el registro.'})
    H._api_get=lambda self,ruta,q,real,vista:responder(self,'GET',ruta,q,real,vista)
    H.api_post=lambda self,ruta,real,vista,b:responder(self,'POST',ruta,{},real,vista,b)
