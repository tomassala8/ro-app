"""Rituales propios y avisos declarados locales. Sin IO al importar/enganchar."""
import hashlib
import json
import os
import re
import sqlite3
import uuid
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
import piloto_lectura
import bd_comun as bd

RUTA = '/api/operaciones/registros'
RITUALES = ('manana','cierre','lunes','viernes','mes')
VERSION = '269.1'

class ErrorRegistro(Exception):
    def __init__(self,codigo,texto): self.codigo=codigo;super().__init__(texto)

def unica(filas,pid):
    if not isinstance(pid,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',pid):raise ErrorRegistro(403,'Identidad inválida.')
    xs=[p for p in filas or [] if isinstance(p,dict) and p.get('id')==pid] if isinstance(filas,list) else []
    if len(xs)!=1 or xs[0].get('estado')!='activo' or xs[0].get('activo') is False:
        raise ErrorRegistro(403,'Identidad activa no inequívoca.')
    return xs[0]

def autorizar(S,rid,vid,escritura=False,destino=None):
    if S.E.nucleo_bloqueado: raise ErrorRegistro(503,'Fuente de permisos no disponible.')
    if escritura and (rid!=vid or piloto_lectura.activo()):raise ErrorRegistro(403,'Esta sesión sólo permite consulta.')
    crudo=S.E.crudo
    ps=[unica(crudo.get('personas'),pid) for pid in (rid,vid)]
    if any(not S.ve_alguno(p,['mi-dia']) for p in ps): raise ErrorRegistro(403,'Rituales no disponibles para esta sesión.')
    if rid!=vid and S.P.ver(ps[0],{'tipo':'ver_como'},S.P.contexto(ps[0],crudo)).get('ok') is not True:
        raise ErrorRegistro(403,'La vista de otra persona no está autorizada.')
    if destino is not None:
        unica(crudo.get('personas'),destino)
        for p in ps:
            if not set(p.get('puestos') or []) & {'direccion','operaciones'} or not S.P.ver(p,{'tipo':'horas_persona','persona_id':destino},S.P.contexto(p,crudo)).get('ok'):
                raise ErrorRegistro(403,'No puedes registrar este aviso.')
    return ps

def periodos(S):
    hoy=date.fromisoformat(S.P.hoy_iso())
    lunes=hoy-timedelta(days=hoy.weekday())
    return {r:hoy.isoformat() if r in ('manana','cierre') else hoy.strftime('%Y-%m') if r=='mes' else lunes.isoformat() for r in RITUALES}

def validar(S,b,periodo_actual=True):
    if not isinstance(b,dict) or b.get('tipo') not in ('ritual','avisado'):raise ErrorRegistro(400,'Tipo de registro inválido.')
    base={'tipo','revision','intencion_id','nota'}
    requeridos=base|({'ritual','periodo','hecho'} if b['tipo']=='ritual' else {'persona_id'})
    if set(b)-requeridos or not (requeridos-{'nota'})<=set(b):raise ErrorRegistro(400,'Campos del registro inválidos.')
    if type(b['revision']) is not int or b['revision']<0:raise ErrorRegistro(400,'Revisión inválida.')
    try:
        u=uuid.UUID(b['intencion_id'])
        if str(u)!=b['intencion_id'] or u.version!=4:raise ValueError()
    except (ValueError,TypeError,AttributeError):raise ErrorRegistro(400,'Intención UUID inválida.')
    nota=b.get('nota','')
    if not isinstance(nota,str) or len(nota)>300 or any(ord(c)<32 and c not in '\n\t' for c in nota):raise ErrorRegistro(400,'Nota inválida (máximo 300 caracteres).')
    if b['tipo']=='ritual':
        r=b['ritual']
        formato=r'^\d{4}-\d{2}$' if r=='mes' else r'^\d{4}-\d{2}-\d{2}$'
        if (not isinstance(r,str) or r not in RITUALES or not isinstance(b['periodo'],str)
                or not re.fullmatch(formato,b['periodo']) or type(b['hecho']) is not bool
                or (periodo_actual and b['periodo']!=periodos(S)[r])):
            raise ErrorRegistro(400,'Ritual o período actual inválido.')
        contenido={'tipo':'ritual','ritual':r,'periodo':b['periodo'],'hecho':b['hecho'],'nota':nota.strip()}
        clave='ritual:'+r+':'+b['periodo']
    else:
        pid=b['persona_id']
        if not isinstance(pid,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',pid):raise ErrorRegistro(400,'Persona inválida.')
        contenido={'tipo':'avisado','persona_id':pid,'periodo':S.P.hoy_iso(),'nota':nota.strip()}
        clave='avisado:'+pid+':'+S.P.hoy_iso()
    return clave,contenido

def preparar(con):
    # No executescript/commit: el handler posee la conexión y su transacción.
    con.execute('CREATE TABLE IF NOT EXISTS operaciones_registros_269 (id INTEGER PRIMARY KEY AUTOINCREMENT, propietario TEXT NOT NULL, clave TEXT NOT NULL, revision INTEGER NOT NULL, autor TEXT NOT NULL, registrado_en TEXT NOT NULL, contenido TEXT NOT NULL, intencion TEXT NOT NULL, huella TEXT NOT NULL, UNIQUE(autor,intencion), UNIQUE(propietario,clave,revision))')
    for accion in ('UPDATE','DELETE'):
        con.execute("CREATE TRIGGER IF NOT EXISTS operaciones_269_sin_"+accion.lower()+" BEFORE "+accion+" ON operaciones_registros_269 BEGIN SELECT RAISE(ABORT,'Registro operativo inmutable'); END")

def decodificar(r):
    d=json.loads(r['contenido'])
    if not isinstance(d,dict) or d.get('tipo') not in ('ritual','avisado') or not isinstance(d.get('nota'),str) or len(d['nota'])>300:
        raise ErrorRegistro(503,'Registro almacenado incoherente.')
    keys={'tipo','ritual','periodo','hecho','nota'} if d['tipo']=='ritual' else {'tipo','persona_id','periodo','nota'}
    if set(d)!=keys or (d['tipo']=='ritual' and (d['ritual'] not in RITUALES or type(d['hecho']) is not bool)):
        raise ErrorRegistro(503,'Registro almacenado incoherente.')
    clave='ritual:'+d['ritual']+':'+str(d['periodo']) if d['tipo']=='ritual' else 'avisado:'+str(d['persona_id'])+':'+str(d['periodo'])
    normal=json.dumps({'clave':clave,'revision':r['revision']-1,'contenido':d},sort_keys=True,ensure_ascii=False,separators=(',',':'))
    if (r['clave']!=clave or r['autor']!=r['propietario'] or r['revision']<1 or
            hashlib.sha256(normal.encode()).hexdigest()!=r['huella']):
        raise ErrorRegistro(503,'Registro almacenado incoherente.')
    return {'id':r['id'],'clave':r['clave'],'revision':r['revision'],'autor':r['autor'],
            'registrado_en':r['registrado_en'],'declarado':True,'envio_realizado':False,**d}

def listar(S,con,rid,vid):
    autorizar(S,rid,vid)
    limitado=False
    if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='operaciones_registros_269'").fetchone(): rs=[]
    else:
        rows=con.execute('SELECT * FROM operaciones_registros_269 WHERE propietario=? ORDER BY id DESC LIMIT 1000',(vid,)).fetchall()
        limitado=len(rows)>=1000
        vistos=set();rs=[]
        for row in rows:
            if row['clave'] in vistos:continue
            vistos.add(row['clave'])
            d=decodificar(row)
            if d['tipo']=='avisado':
                try:autorizar(S,rid,vid,destino=d['persona_id'])
                except ErrorRegistro:continue
            rs.append(d)
    autorizar(S,rid,vid)
    return {'version':VERSION,'propietario':vid,'periodos':periodos(S),'registros':rs,
            'cobertura':'declaraciones locales; no prueba de envío ni cumplimiento externo',
            'puede_registrar':rid==vid and not piloto_lectura.activo(), 'historial_limitado':limitado}

def guardar(S,con,rid,vid,b):
    # Un recibo de ayer sigue siendo recuperable por la misma intención; una
    # escritura nueva sólo admite el período contemporáneo del servidor.
    clave,contenido=validar(S,b,periodo_actual=False)
    destino=contenido.get('persona_id')
    autorizar(S,rid,vid,True,destino)
    if con.in_transaction:raise ErrorRegistro(503,'La conexión debe ser exclusiva para este registro.')
    con.execute('BEGIN IMMEDIATE')
    try:
        autorizar(S,rid,vid,True,destino)
        preparar(con)
        anterior=con.execute('SELECT * FROM operaciones_registros_269 WHERE autor=? AND intencion=?',(rid,b['intencion_id'])).fetchone()
        if anterior and contenido['tipo']=='avisado':
            viejo=decodificar(anterior)
            contenido['periodo']=viejo['periodo'];clave='avisado:'+contenido['persona_id']+':'+viejo['periodo']
        normal=json.dumps({'clave':clave,'revision':b['revision'],'contenido':contenido},sort_keys=True,ensure_ascii=False,separators=(',',':'))
        huella=hashlib.sha256(normal.encode()).hexdigest()
        if anterior:
            if anterior['huella']!=huella:raise ErrorRegistro(409,'Esta intención ya se usó con otro contenido.')
            d=decodificar(anterior);repetido=True
        else:
            validar(S,b)
            revision=con.execute('SELECT MAX(revision) FROM operaciones_registros_269 WHERE propietario=? AND clave=?',(rid,clave)).fetchone()[0] or 0
            if revision!=b['revision']:raise ErrorRegistro(409,'El registro cambió. Vuelve a leerlo antes de guardar.')
            hora=datetime.now(timezone.utc).isoformat()
            cur=con.execute('INSERT INTO operaciones_registros_269 (propietario,clave,revision,autor,registrado_en,contenido,intencion,huella) VALUES (?,?,?,?,?,?,?,?)',
                            (rid,clave,revision+1,rid,hora,json.dumps(contenido,ensure_ascii=False),b['intencion_id'],huella))
            d=decodificar(con.execute('SELECT * FROM operaciones_registros_269 WHERE id=?',(cur.lastrowid,)).fetchone());repetido=False
        autorizar(S,rid,vid,True,destino)
        con.commit()
        return {'version':VERSION,'resultado':'duplicado' if repetido else 'guardado','recibo':d,'intencion_id':b['intencion_id']}
    except Exception:
        con.rollback();raise

def enganchar(H,S):
    get_orig,post_orig=H._api_get,H.api_post
    def responder(self,metodo,ruta,q,real,vista,b=None):
        if ruta!=RUTA:return get_orig(self,ruta,q,real,vista) if metodo=='GET' else post_orig(self,ruta,real,vista,b)
        try:
            if q:raise ErrorRegistro(400,'Esta ruta no admite filtros de identidad.')
            rid,vid=real.get('id'),vista.get('id')
            autorizar(S,rid,vid,metodo=='POST')
            with closing(S.conectar()) as con:
                if not bd.conexion_valida(con):raise ErrorRegistro(503,'Persistencia local no disponible.')
                con.row_factory=sqlite3.Row
                doc=listar(S,con,rid,vid) if metodo=='GET' else guardar(S,con,rid,vid,b)
            autorizar(S,rid,vid,metodo=='POST',b.get('persona_id') if isinstance(b,dict) and b.get('tipo')=='avisado' else None)
            return self.responder(200,doc)
        except ErrorRegistro as e:return self.responder(e.codigo,{'error':str(e)})
        except bd.ERRORES_BD+(OSError,ValueError,TypeError,KeyError,AttributeError):return self.responder(503,{'error':'Registro local no disponible; no se ha confirmado el cambio.'})
    H._api_get=lambda self,ruta,q,real,vista:responder(self,'GET',ruta,q,real,vista)
    H.api_post=lambda self,ruta,real,vista,b:responder(self,'POST',ruta,{},real,vista,b)
