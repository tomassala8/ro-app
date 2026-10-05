"""Revisión declarada de anomalías de horas. No modifica entradas de ClickUp."""
import hashlib
import json
import os
import re
import sqlite3
from contextlib import closing
from datetime import datetime,timezone
import operaciones_registros_269 as O
import operaciones_registros_272 as C

RUTA='/api/operaciones/anomalias'
VERSION='276.1'
DECISIONES=('correcto','hablar','error')

def identificador(x):return isinstance(x,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,120}',x) is not None

def resolver(S,rid,vid,aid,escritura=False):
    ps=O.autorizar(S,rid,vid,escritura)
    if not identificador(aid):raise O.ErrorRegistro(400,'Identificador de anomalía inválido.')
    for p in ps:
        if not S.ve_alguno(p,['horas']):raise O.ErrorRegistro(403,'Horas fuera de tu ámbito.')
        if escritura and not (set(p.get('puestos') or []) & {'direccion','operaciones','rrhh'} or
               S.P.ver(p,{'tipo':'comparar_personas'},S.P.contexto(p,S.E.crudo)).get('ok') is True):
            raise O.ErrorRegistro(403,'No tienes permiso actual de revisión de horas.')
    puerta=S.puerta_modulo(ps[0],ps[1],'horas/horas',apuntar=False)
    if puerta.get('error') or not puerta.get('fichero') or 'data/horas/horas.json' in getattr(S.E,'bloqueados',set()):
        raise O.ErrorRegistro(403,'Fuente de horas no autorizada.')
    try:raw,nota=S.leer_json_bueno(puerta['fichero'])
    except (OSError,ValueError):raise O.ErrorRegistro(503,'Fuente actual de horas no disponible.')
    if nota or not isinstance(raw,dict) or not isinstance(raw.get('raras'),list):
        raise O.ErrorRegistro(503,'La fuente de horas no está disponible como autoridad actual.')
    candidatos=[x for x in raw['raras'] if isinstance(x,dict) and x.get('id')==aid]
    if len(candidatos)!=1:raise O.ErrorRegistro(403,'Anomalía ausente o ambigua en la fuente actual.')
    r=candidatos[0];pid=r.get('persona_id');O.unica(S.E.crudo.get('personas'),pid)
    for p in ps:
        if S.P.ver(p,{'tipo':'horas_persona','persona_id':pid},S.P.contexto(p,S.E.crudo)).get('ok') is not True:
            raise O.ErrorRegistro(403,'Esta persona está fuera de tu ámbito.')
    mapa=[x for x in raw.get('raras_cliente') or [] if isinstance(x,dict) and x.get('id')==aid]
    if len(mapa)>1 or (mapa and mapa[0].get('persona_id')!=pid):raise O.ErrorRegistro(403,'Vínculo de cliente ambiguo.')
    cid=mapa[0].get('cliente_id') if mapa else r.get('cliente_id')
    if mapa and not identificador(cid):raise O.ErrorRegistro(403,'Cliente del registro no confirmado.')
    if mapa and r.get('cliente_id') is not None and r['cliente_id']!=cid:
        raise O.ErrorRegistro(403,'Vínculos de cliente contradictorios.')
    C.cliente(S,ps,cid)
    # La fila también debe sobrevivir al mismo recorte del módulo, sin usar nombres.
    scoped=S.modulo_recortado(ps[0],ps[1],S.P.contexto(ps[1],S.E.crudo),'horas/horas')
    visibles=[x for x in (scoped.get('raras') or []) if isinstance(x,dict) and x.get('id')==aid] if isinstance(scoped,dict) else []
    campos=('id','persona_id','fecha','horas','tipo')
    if len(visibles)!=1 or any(visibles[0].get(k)!=r.get(k) for k in campos):
        raise O.ErrorRegistro(403,'La anomalía ya no está visible en esta copia.')
    firma={k:r.get(k) for k in campos};firma['cliente_id']=cid
    if any(not isinstance(firma[k],str) for k in ('id','persona_id','fecha','tipo')) or type(firma['horas']) not in (int,float):
        raise O.ErrorRegistro(503,'Registro de origen incoherente.')
    try:normal=json.dumps(firma,sort_keys=True,separators=(',',':'),allow_nan=False)
    except ValueError:raise O.ErrorRegistro(503,'Horas de origen no válidas.')
    huella=hashlib.sha256(normal.encode()).hexdigest()
    # Fuente/persona/cartera revalidadas por el caller justo antes de publicar/commit.
    return {'id':aid,'persona_id':pid,'huella_origen':huella,'fecha_origen':C.sello(raw.get('generado'))}

def preparar(con):
    con.execute('CREATE TABLE IF NOT EXISTS operaciones_anomalias_276 (id INTEGER PRIMARY KEY AUTOINCREMENT, anomalia TEXT NOT NULL, revision INTEGER NOT NULL, actor TEXT NOT NULL, persona_id TEXT NOT NULL, origen_hash TEXT NOT NULL, decision TEXT NOT NULL, prueba TEXT NOT NULL, hora TEXT NOT NULL, intencion TEXT NOT NULL, request_hash TEXT NOT NULL, UNIQUE(anomalia,revision), UNIQUE(actor,intencion))')
    for accion in ('UPDATE','DELETE'):
        con.execute("CREATE TRIGGER IF NOT EXISTS operaciones_276_sin_"+accion.lower()+" BEFORE "+accion+" ON operaciones_anomalias_276 BEGIN SELECT RAISE(ABORT,'Revisión de horas inmutable'); END")

def decodificar(r):
    if (not identificador(r['anomalia']) or not identificador(r['persona_id']) or not identificador(r['actor']) or
            type(r['revision']) is not int or r['revision']<1 or r['decision'] not in DECISIONES or
            not re.fullmatch(r'[a-f0-9]{64}',r['origen_hash'])):raise O.ErrorRegistro(503,'Revisión almacenada incoherente.')
    try:
        prueba=C.texto(r['prueba'],500,r['decision']=='error')
        hora=datetime.fromisoformat(r['hora'])
        if hora.tzinfo is None or hora>datetime.now(timezone.utc):raise ValueError()
    except (O.ErrorRegistro,ValueError,TypeError):raise O.ErrorRegistro(503,'Prueba o fecha almacenada incoherente.')
    return {'anomalia_id':r['anomalia'],'persona_id':r['persona_id'],'revision':r['revision'],'huella_origen':r['origen_hash'],
            'decision':r['decision'],'prueba':prueba,'registrado_por':r['actor'],'registrado_en':r['hora'],
            'declarado':True,'entrada_modificada':False,'envio_realizado':False}

def ultima(con,aid):return con.execute('SELECT * FROM operaciones_anomalias_276 WHERE anomalia=? ORDER BY revision DESC LIMIT 1',(aid,)).fetchone()

def listar(S,con,rid,vid,aid):
    origen=resolver(S,rid,vid,aid)
    r=ultima(con,aid) if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='operaciones_anomalias_276'").fetchone() else None
    registro=decodificar(r) if r else None
    incompatible=bool(registro and registro['huella_origen']!=origen['huella_origen'])
    if resolver(S,rid,vid,aid)!=origen:raise O.ErrorRegistro(409,'La fuente cambió durante la lectura.')
    puede=True
    try:resolver(S,rid,vid,aid,True)
    except O.ErrorRegistro as e:
        if e.codigo!=403:raise
        puede=False
    return {'version':VERSION,'origen':origen,'revision':r['revision'] if r else 0,'registro':None if incompatible else registro,
            'anterior_incompatible':incompatible,'puede_registrar':puede}

def guardar(S,con,rid,vid,b):
    if (not isinstance(b,dict) or set(b)-{'anomalia_id','decision','prueba','revision','intencion_id','huella_origen'} or
            not {'anomalia_id','decision','revision','intencion_id','huella_origen'}<=set(b) or b.get('decision') not in DECISIONES or
            type(b.get('revision')) is not int or b['revision']<0 or not C.uuid4(b.get('intencion_id')) or
            not isinstance(b.get('huella_origen'),str) or not re.fullmatch(r'[a-f0-9]{64}',b['huella_origen'])):
        raise O.ErrorRegistro(400,'Registro de anomalía inválido.')
    prueba=C.texto(b.get('prueba',''),500,b['decision']=='error')
    origen=resolver(S,rid,vid,b.get('anomalia_id'),True)
    if b['huella_origen']!=origen['huella_origen']:raise O.ErrorRegistro(409,'La entrada de origen cambió. Vuelve a leerla.')
    if con.in_transaction:raise O.ErrorRegistro(503,'Se necesita una conexión exclusiva.')
    con.execute('BEGIN IMMEDIATE')
    try:
        if resolver(S,rid,vid,b['anomalia_id'],True)!=origen:raise O.ErrorRegistro(409,'La fuente cambió antes de guardar.')
        preparar(con)
        normal=json.dumps({**b,'prueba':prueba},sort_keys=True,separators=(',',':'),ensure_ascii=False)
        huella=hashlib.sha256(normal.encode()).hexdigest()
        replay=con.execute('SELECT * FROM operaciones_anomalias_276 WHERE actor=? AND intencion=?',(rid,b['intencion_id'])).fetchone()
        if replay:
            if replay['request_hash']!=huella:raise O.ErrorRegistro(409,'La intención ya tiene otro contenido.')
            recibo=decodificar(replay);resultado='duplicado'
        else:
            anterior=ultima(con,b['anomalia_id']);revision=anterior['revision'] if anterior else 0
            if revision!=b['revision']:raise O.ErrorRegistro(409,'La revisión cambió. Vuelve a leerla.')
            if anterior and (anterior['decision']!=b['decision'] or anterior['origen_hash']!=b['huella_origen']) and not prueba:
                raise O.ErrorRegistro(400,'Rectificar una revisión necesita una prueba escrita.')
            hora=datetime.now(timezone.utc).isoformat()
            cur=con.execute('INSERT INTO operaciones_anomalias_276 (anomalia,revision,actor,persona_id,origen_hash,decision,prueba,hora,intencion,request_hash) VALUES (?,?,?,?,?,?,?,?,?,?)',
                            (b['anomalia_id'],revision+1,rid,origen['persona_id'],origen['huella_origen'],b['decision'],prueba,hora,b['intencion_id'],huella))
            recibo=decodificar(con.execute('SELECT * FROM operaciones_anomalias_276 WHERE id=?',(cur.lastrowid,)).fetchone());resultado='guardado'
        if resolver(S,rid,vid,b['anomalia_id'],True)!=origen:raise O.ErrorRegistro(409,'El ámbito o la fuente cambió durante el registro.')
        con.commit();return {'version':VERSION,'resultado':resultado,'intencion_id':b['intencion_id'],'recibo':recibo}
    except Exception:con.rollback();raise

def enganchar(H,S):
    get_orig,post_orig=H._api_get,H.api_post
    def responder(self,metodo,ruta,q,real,vista,b=None):
        if ruta!=RUTA:return get_orig(self,ruta,q,real,vista) if metodo=='GET' else post_orig(self,ruta,real,vista,b)
        try:
            rid,vid=real.get('id'),vista.get('id')
            O.autorizar(S,rid,vid,metodo=='POST')
            if metodo=='GET':
                if set(q)!={'id'} or not isinstance(q['id'],list) or len(q['id'])!=1:raise O.ErrorRegistro(400,'Selecciona una anomalía exacta.')
                aid=q['id'][0]
            else:aid=b.get('anomalia_id') if isinstance(b,dict) else None
            resolver(S,rid,vid,aid,metodo=='POST')
            if os.environ.get('DATABASE_URL') or os.environ.get('PGDATABASE_URL'):raise O.ErrorRegistro(503,'La revisión local requiere SQLite verificado.')
            with closing(S.conectar()) as con:
                if not isinstance(con,sqlite3.Connection):raise O.ErrorRegistro(503,'Persistencia local no disponible.')
                con.row_factory=sqlite3.Row
                doc=listar(S,con,rid,vid,aid) if metodo=='GET' else guardar(S,con,rid,vid,b)
            fresco=resolver(S,rid,vid,aid,metodo=='POST')
            esperado=doc['origen'] if metodo=='GET' else {'id':doc['recibo']['anomalia_id'],'persona_id':doc['recibo']['persona_id'],'huella_origen':doc['recibo']['huella_origen']}
            if any(fresco[k]!=esperado[k] for k in ('id','persona_id','huella_origen')):raise O.ErrorRegistro(409,'La entrada cambió antes de responder.')
            return self.responder(200,doc)
        except O.ErrorRegistro as e:return self.responder(e.codigo,{'error':str(e)})
        except (sqlite3.Error,OSError,ValueError,TypeError,KeyError,AttributeError):return self.responder(503,{'error':'Revisión local no disponible; no se confirma el cambio.'})
    H._api_get=lambda self,ruta,q,real,vista:responder(self,'GET',ruta,q,real,vista)
    H.api_post=lambda self,ruta,real,vista,b:responder(self,'POST',ruta,{},real,vista,b)
