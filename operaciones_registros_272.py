"""Encargos y fotos de control locales. Ningún proveedor ni IO al importar."""
import hashlib
import json
import os
import re
import sqlite3
import uuid
from contextlib import closing
from datetime import date,datetime,timezone
import operaciones_registros_269 as O
import mediciones_fotos_329 as MF329

RUTA='/api/operaciones/control'
VERSION='272.1'
METRICAS=(('pend48','Clientes +48 h sin respuesta'),('rojas','Alarmas en rojo'),('imputacion','% horas imputadas'),
          ('revision48','Tareas en revisión +48 h'),('nota_accounts','Nota media de accounts'),
          ('semaforo_sin','Semáforos sin rellenar'),('rastro','Acciones con rastro (acumulado)'))
DETALLE_UNKNOWN='Sin medición compatible; no se convierte en cero ni se usa capacidad universal.'
DETALLES={'rojas':'Alertas autorizadas de la copia; no total exhaustivo actual.',
          'revision48':'Revisión account ≥48 h de proyectos presentes con medición; cobertura de copia.'}

def uuid4(x):
    try:u=uuid.UUID(x);return str(u)==x and u.version==4
    except (ValueError,TypeError,AttributeError):return False

def texto(x,maximo,obligatorio=False):
    if not isinstance(x,str) or len(x)>maximo or any(ord(c)<32 and c not in '\n\t' for c in x) or (obligatorio and not x.strip()):
        raise O.ErrorRegistro(400,'Texto del registro inválido.')
    return x.strip()

def cliente(S,ps,cid):
    if cid is None:return
    xs=[c for c in S.E.crudo.get('clientes') or [] if isinstance(c,dict) and c.get('id')==cid]
    if (not isinstance(cid,str) or len(xs)!=1 or S.ACT.es_activo_id(cid) is not True or
        any(S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},S.P.contexto(p,S.E.crudo)).get('ok') is not True for p in ps)):
        raise O.ErrorRegistro(403,'Cliente fuera de tu ámbito activo.')

def alcance(S,rid,vid):
    ps=O.autorizar(S,rid,vid)
    crudo=S.E.crudo;contextos=[S.P.contexto(p,crudo) for p in ps]
    clientes=[c for c in crudo.get('clientes') or [] if isinstance(c,dict) and isinstance(c.get('id'),str)]
    cuenta={}
    for c in clientes:cuenta[c['id']]=cuenta.get(c['id'],0)+1
    ids=[]
    for c in clientes:
        cid=c['id']
        if cuenta[cid]==1 and S.ACT.es_activo_id(cid) is True and all(S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},cp).get('ok') is True for p,cp in zip(ps,contextos)):ids.append(cid)
    identidad=[{'id':p['id'],'puestos':sorted(p.get('puestos') or []),'jefe':p.get('jefe')} for p in ps]
    reglas=getattr(S.P,'REGLAS',{})
    permisos_fuente={m:[bool(S.ve_alguno(p,[m])) for p in ps] for m in ('alertas','produccion')}
    firma={'clientes':sorted(set(ids)),'identidad':identidad,'reglas':reglas,'fuentes':permisos_fuente}
    return hashlib.sha256(json.dumps(firma,sort_keys=True,separators=(',',':')).encode()).hexdigest(),set(ids)

def encargo_permitido(S,rid,vid,d,escritura=False):
    ps=O.autorizar(S,rid,vid,escritura)
    if not isinstance(d,dict):raise O.ErrorRegistro(503,'Encargo almacenado incoherente.')
    autor=O.unica(S.E.crudo.get('personas'),d.get('autor'))
    destino=O.unica(S.E.crudo.get('personas'),d.get('asignado'))
    for p in ps:
        if p['id'] not in (autor['id'],destino['id']):raise O.ErrorRegistro(403,'Encargo fuera de tu ámbito.')
        if p['id']!=destino['id'] and S.P.ver(p,{'tipo':'notas_persona','persona_id':destino['id']},S.P.contexto(p,S.E.crudo)).get('ok') is not True:
            raise O.ErrorRegistro(403,'El destinatario está fuera de tu ámbito actual.')
    cliente(S,ps+[destino],d.get('cliente_id'))
    return ps

def foto_permitida(S,rid,vid,escritura=False):
    ps=O.autorizar(S,rid,vid,escritura)
    if any(not set(p.get('puestos') or []) & {'operaciones','direccion'} for p in ps):raise O.ErrorRegistro(403,'Fotos de control no disponibles para este puesto.')
    return ps

def sello(x):
    # Sólo una fecha de la copia, nunca rutas o texto privado de fuente.
    if not isinstance(x,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?',x):return None
    try:
        if len(x)==10:date.fromisoformat(x)
        else:
            d=datetime.fromisoformat(x.replace('Z','+00:00'))
            if d.tzinfo is not None and d>datetime.now(timezone.utc):return None
    except ValueError:return None
    return x

def capturar(S,rid,vid):
    ps=foto_permitida(S,rid,vid,True)
    huella,ids=alcance(S,rid,vid)
    cp=S.P.contexto(ps[1],S.E.crudo)
    def leer(rel):
        modulo='alertas' if rel.startswith('alertas/') else 'produccion'
        if any(not S.ve_alguno(p,[modulo]) for p in ps):return None
        try:return S.modulo_recortado(ps[0],ps[1],cp,rel)
        except (OSError,ValueError,KeyError,TypeError):return None
    al=leer('alertas/p_'+vid);pr=leer('produccion/produccion')
    valores={};descriptores=[];leido=datetime.now(timezone.utc).isoformat()
    if isinstance(al,dict) and isinstance(al.get('alertas'),list):
        filas=[a for a in al['alertas'] if isinstance(a,dict) and (not a.get('cliente_id') or a['cliente_id'] in ids)]
        ident=[a.get('id') for a in filas]
        if all(isinstance(x,str) and x for x in ident) and len(ident)==len(set(ident)):
            valores['rojas']=(sum(a.get('gravedad')=='rojo' for a in filas),sello(al.get('generado')),DETALLES['rojas'])
            # No certificar ausencia/serie si la población está vacía o el corte carece de zona.
            m=MF329.descriptor('rojas',valores['rojas'][0],ident,al.get('generado'),leido,huella)
            if m is not None:descriptores.append(m)
    if isinstance(pr,dict) and isinstance(pr.get('proyectos'),list):
        filas=[p for p in pr['proyectos'] if isinstance(p,dict) and p.get('cliente_id') in ids]
        cids=[p['cliente_id'] for p in filas]
        mediciones=[p.get('revisiones_account') for p in filas]
        # El legado rellena 0 cuando no hay medición: sólo DTO medido+fecha hoy.
        if (filas and len(cids)==len(set(cids)) and all(isinstance(m,dict) and m.get('estado')=='medido'
                and sello(m.get('fecha')) and m['fecha'][:10]==S.P.hoy_iso() for m in mediciones)
                and all(type(p.get('rev_account_48')) is int and p['rev_account_48']>=0 for p in filas)):
            valores['revision48']=(sum(p['rev_account_48'] for p in filas),min(m['fecha'] for m in mediciones),DETALLES['revision48'])
            # La misma fecha exacta de flujo y población medida, no un mínimo entre lecturas distintas.
            if (all(m.get('fuente')=='flujo' for m in mediciones) and len({m['fecha'] for m in mediciones})==1
                    and all(type(p.get('rev_account')) is int and p['rev_account']>=p['rev_account_48'] for p in filas)):
                descriptor=MF329.descriptor('revision48',valores['revision48'][0],cids,mediciones[0]['fecha'],leido,huella)
                if descriptor is not None:descriptores.append(descriptor)
    if alcance(S,rid,vid)[0]!=huella:raise O.ErrorRegistro(409,'El ámbito cambió durante la captura. Vuelve a intentarlo.')
    foto_permitida(S,rid,vid,True)
    return {'tipo':'foto','scope_hash':huella,'dia':S.P.hoy_iso(),'mediciones_329':descriptores,'metricas':[{'id':k,'etiqueta':et,
        'valor':valores.get(k,(None,None,''))[0],'fecha_fuente':valores.get(k,(None,None,''))[1],
        'estado':'observado_copia' if k in valores else 'desconocido',
        'detalle':valores.get(k,(None,None,DETALLE_UNKNOWN))[2]}
        for k,et in METRICAS], 'cumplimiento':None,'exhaustiva':False}

def preparar(con):
    con.execute('CREATE TABLE IF NOT EXISTS operaciones_control_272 (id INTEGER PRIMARY KEY AUTOINCREMENT, objeto TEXT NOT NULL, revision INTEGER NOT NULL, actor TEXT NOT NULL, autor TEXT NOT NULL, asignado TEXT NOT NULL, tipo TEXT NOT NULL, hora TEXT NOT NULL, contenido TEXT NOT NULL, intencion TEXT NOT NULL, huella TEXT NOT NULL, UNIQUE(actor,intencion), UNIQUE(objeto,revision))')
    for accion in ('UPDATE','DELETE'):
        con.execute("CREATE TRIGGER IF NOT EXISTS operaciones_272_sin_"+accion.lower()+" BEFORE "+accion+" ON operaciones_control_272 BEGIN SELECT RAISE(ABORT,'Registro de control inmutable'); END")

def decodificar(r):
    d=json.loads(r['contenido'])
    if not isinstance(d,dict) or d.get('tipo')!=r['tipo'] or r['tipo'] not in ('encargo','foto') or type(r['revision']) is not int or r['revision']<1:
        raise O.ErrorRegistro(503,'Registro de control incoherente.')
    if d['tipo']=='encargo':
        if set(d)!={'tipo','autor','asignado','cliente_id','titulo','limite','hecho','prueba'} or d['autor']!=r['autor'] or d['asignado']!=r['asignado'] or type(d['hecho']) is not bool:
            raise O.ErrorRegistro(503,'Encargo almacenado incoherente.')
        texto(d['titulo'],400,True);texto(d['prueba'],500,d['hecho'])
        if d['limite'] is not None:
            try:
                if not isinstance(d['limite'],str) or date.fromisoformat(d['limite']).isoformat()!=d['limite']:raise ValueError()
            except ValueError:raise O.ErrorRegistro(503,'Fecha del encargo incoherente.')
    else:
        if set(d) not in ({'tipo','scope_hash','dia','metricas','cumplimiento','exhaustiva'}, {'tipo','scope_hash','dia','metricas','cumplimiento','exhaustiva','mediciones_329'}) or not re.fullmatch(r'[0-9a-f]{64}',str(d['scope_hash'])) or d['cumplimiento'] is not None or d['exhaustiva'] is not False or not isinstance(d['metricas'],list) or len(d['metricas'])!=len(METRICAS):
            raise O.ErrorRegistro(503,'Foto almacenada incoherente.')
        try:
            if not isinstance(d['dia'],str) or date.fromisoformat(d['dia']).isoformat()!=d['dia']:raise ValueError()
        except ValueError:raise O.ErrorRegistro(503,'Fecha de foto incoherente.')
        for m,(k,et) in zip(d['metricas'],METRICAS):
            if (not isinstance(m,dict) or set(m)!={'id','etiqueta','valor','fecha_fuente','estado','detalle'} or m['id']!=k or m['etiqueta']!=et
                or m['estado'] not in ('desconocido','observado_copia') or not isinstance(m['detalle'],str) or len(m['detalle'])>300
                or (m['valor'] is not None and (type(m['valor']) is not int or m['valor']<0))
                or (m['estado']=='desconocido' and (m['valor'] is not None or m['fecha_fuente'] is not None or m['detalle']!=DETALLE_UNKNOWN))
                or (m['estado']=='observado_copia' and (k not in DETALLES or m['valor'] is None or m['detalle']!=DETALLES[k]))
                or (m['fecha_fuente'] is not None and not sello(m['fecha_fuente']))):
                raise O.ErrorRegistro(503,'Foto almacenada incoherente.')
        if 'mediciones_329' in d:
            ms=d['mediciones_329'];valores={m['id']:m['valor'] for m in d['metricas']}
            if not isinstance(ms,list) or len(ms)>2 or any(not MF329.validar(m,d['scope_hash'],valores) for m in ms) or len({m['id'] for m in ms})!=len(ms):
                raise O.ErrorRegistro(503,'Descriptores de foto incoherentes.')
    try:
        hora=datetime.fromisoformat(r['hora'])
        if hora.tzinfo is None or hora>datetime.now(timezone.utc):raise ValueError()
    except (ValueError,TypeError):raise O.ErrorRegistro(503,'Hora del registro incoherente.')
    if d['tipo']=='foto' and any(MF329.instante(m['leido'])>hora for m in d.get('mediciones_329',[])):
        raise O.ErrorRegistro(503,'La medición es posterior al guardado de la foto.')
    return {'objeto':r['objeto'],'revision':r['revision'],'registrado_por':r['actor'],'registrado_en':r['hora'],**d}

def leer(con,objeto):
    return con.execute('SELECT * FROM operaciones_control_272 WHERE objeto=? ORDER BY revision DESC LIMIT 1',(objeto,)).fetchone()

def guardar(S,con,rid,vid,b):
    O.autorizar(S,rid,vid,True)
    if not isinstance(b,dict) or b.get('tipo') not in ('encargo','foto') or not uuid4(b.get('intencion_id')) or type(b.get('revision')) is not int or b['revision']<0:
        raise O.ErrorRegistro(400,'Registro de control inválido.')
    tipo=b['tipo'];operacion=b.get('operacion')
    permitidos={'tipo','intencion_id','revision'}|({'objeto','operacion','asignado','cliente_id','titulo','limite','hecho','prueba'} if tipo=='encargo' else set())
    if set(b)-permitidos:raise O.ErrorRegistro(400,'Campos no admitidos.')
    normal=json.dumps(b,sort_keys=True,ensure_ascii=False,separators=(',',':'))
    huella=hashlib.sha256(normal.encode()).hexdigest()
    if con.in_transaction:raise O.ErrorRegistro(503,'Se necesita una conexión exclusiva.')
    con.execute('BEGIN IMMEDIATE')
    try:
        O.autorizar(S,rid,vid,True);preparar(con)
        replay=con.execute('SELECT * FROM operaciones_control_272 WHERE actor=? AND intencion=?',(rid,b['intencion_id'])).fetchone()
        if replay:
            if replay['huella']!=huella:raise O.ErrorRegistro(409,'Intención usada con otro contenido.')
            d=decodificar(replay)
            if tipo=='encargo':encargo_permitido(S,rid,vid,d,True)
            else:
                foto_permitida(S,rid,vid,True)
                if alcance(S,rid,vid)[0]!=d['scope_hash']:raise O.ErrorRegistro(403,'La foto ya no pertenece a tu ámbito actual.')
            con.commit();return {'version':VERSION,'resultado':'duplicado','intencion_id':b['intencion_id'],'recibo':d}
        if tipo=='foto':
            if b['revision']!=0:raise O.ErrorRegistro(400,'Una foto nueva empieza en revisión cero.')
            d=capturar(S,rid,vid);objeto=str(uuid.uuid4());autor=asignado=rid;revision=1
        else:
            if operacion not in ('crear','actualizar'):raise O.ErrorRegistro(400,'Operación de encargo inválida.')
            if operacion=='crear':
                if b['revision']!=0 or 'objeto' in b:raise O.ErrorRegistro(400,'Encargo nuevo inválido.')
                asignado=b.get('asignado',rid);ps=O.autorizar(S,rid,vid,True);O.unica(S.E.crudo.get('personas'),asignado)
                if asignado!=rid and ('direccion' not in (ps[0].get('puestos') or []) or S.P.ver(ps[0],{'tipo':'notas_persona','persona_id':asignado},S.P.contexto(ps[0],S.E.crudo)).get('ok') is not True):raise O.ErrorRegistro(403,'Sólo dirección autorizada puede asignar este encargo.')
                autor=rid;objeto=str(uuid.uuid4());revision=1
                d={'tipo':'encargo','autor':autor,'asignado':asignado,'cliente_id':b.get('cliente_id'),'titulo':texto(b.get('titulo'),400,True),'limite':b.get('limite'),'hecho':False,'prueba':''}
                if b.get('hecho') not in (None,False) or b.get('prueba') not in (None,''):raise O.ErrorRegistro(400,'El encargo nuevo no está hecho.')
            else:
                objeto=b.get('objeto')
                if not uuid4(objeto):raise O.ErrorRegistro(400,'Encargo inválido.')
                row=leer(con,objeto)
                if not row or row['tipo']!='encargo':raise O.ErrorRegistro(403,'Encargo no disponible.')
                d=decodificar(row);encargo_permitido(S,rid,vid,d,True)
                if row['revision']!=b['revision']:raise O.ErrorRegistro(409,'El encargo cambió; vuelve a leerlo.')
                if set(b)-{'tipo','intencion_id','revision','objeto','operacion','hecho','prueba'}:raise O.ErrorRegistro(400,'La actualización no cambia autor, destinatario o alcance.')
                if type(b.get('hecho')) is not bool:raise O.ErrorRegistro(400,'Estado de encargo inválido.')
                d={k:d[k] for k in ('tipo','autor','asignado','cliente_id','titulo','limite','hecho','prueba')}
                d['hecho']=b['hecho'];d['prueba']=texto(b.get('prueba',''),500,d['hecho'])
                autor,asignado=d['autor'],d['asignado'];revision=row['revision']+1
            if d['limite'] is not None:
                try:
                    if not isinstance(d['limite'],str) or date.fromisoformat(d['limite']).isoformat()!=d['limite']:raise ValueError()
                except ValueError:raise O.ErrorRegistro(400,'Fecha límite inválida.')
            encargo_permitido(S,rid,vid,d,True)
        hora=datetime.now(timezone.utc).isoformat()
        cur=con.execute('INSERT INTO operaciones_control_272 (objeto,revision,actor,autor,asignado,tipo,hora,contenido,intencion,huella) VALUES (?,?,?,?,?,?,?,?,?,?)',
                        (objeto,revision,rid,autor,asignado,tipo,hora,json.dumps(d,ensure_ascii=False),b['intencion_id'],huella))
        recibo=decodificar(con.execute('SELECT * FROM operaciones_control_272 WHERE id=?',(cur.lastrowid,)).fetchone())
        if tipo=='encargo':encargo_permitido(S,rid,vid,d,True)
        elif alcance(S,rid,vid)[0]!=d['scope_hash']:raise O.ErrorRegistro(409,'El ámbito cambió antes de guardar la foto.')
        O.autorizar(S,rid,vid,True);con.commit()
        return {'version':VERSION,'resultado':'guardado','intencion_id':b['intencion_id'],'recibo':recibo}
    except Exception:con.rollback();raise

def listar(S,con,rid,vid):
    O.autorizar(S,rid,vid)
    def scope_actual():
        try:
            foto_permitida(S,rid,vid)
            return alcance(S,rid,vid)[0]
        except O.ErrorRegistro as e:
            if e.codigo==403:return None
            raise
    scope_inicio=scope_actual()
    out=[];limitado=False
    if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='operaciones_control_272'").fetchone():
        rows=con.execute('SELECT * FROM operaciones_control_272 WHERE autor=? OR asignado=? ORDER BY id DESC LIMIT 1000',(vid,vid)).fetchall();limitado=len(rows)>=1000
        vistos=set();scope_foto=None
        for r in rows:
            if r['objeto'] in vistos:continue
            vistos.add(r['objeto']);d=decodificar(r)
            try:
                if d['tipo']=='encargo':encargo_permitido(S,rid,vid,d)
                else:
                    foto_permitida(S,rid,vid)
                    if scope_foto is None:scope_foto=alcance(S,rid,vid)[0]
                    if r['autor']!=vid or scope_foto!=d['scope_hash']:continue
            except O.ErrorRegistro as e:
                if e.codigo==403:continue
                raise
            out.append(d)
    O.autorizar(S,rid,vid)
    scope_fin=scope_actual()
    if scope_fin!=scope_inicio:raise O.ErrorRegistro(409,'El ámbito cambió durante la lectura de control.')
    return {'version':VERSION,'propietario':vid,'registros':out,'historial_limitado':limitado,
            'puede_registrar':rid==vid and not O.piloto_lectura.activo(),'envio_realizado':False,
            'scope_foto_actual':scope_fin}

def enganchar(H,S):
    get_orig,post_orig=H._api_get,H.api_post
    def responder(self,metodo,ruta,q,real,vista,b=None):
        if ruta!=RUTA:return get_orig(self,ruta,q,real,vista) if metodo=='GET' else post_orig(self,ruta,real,vista,b)
        try:
            if q:raise O.ErrorRegistro(400,'Esta ruta no admite filtros de identidad.')
            rid,vid=real.get('id'),vista.get('id');O.autorizar(S,rid,vid,metodo=='POST')
            if os.environ.get('DATABASE_URL') or os.environ.get('PGDATABASE_URL'):raise O.ErrorRegistro(503,'Este registro requiere SQLite local verificado.')
            with closing(S.conectar()) as con:
                if not isinstance(con,sqlite3.Connection):raise O.ErrorRegistro(503,'Persistencia local no disponible.')
                con.row_factory=sqlite3.Row
                doc=listar(S,con,rid,vid) if metodo=='GET' else guardar(S,con,rid,vid,b)
            O.autorizar(S,rid,vid,metodo=='POST')
            items=doc['registros'] if metodo=='GET' else [doc['recibo']]
            actuales=[];scope_foto=None
            for d in items:
                try:
                    if d['tipo']=='encargo':encargo_permitido(S,rid,vid,d,metodo=='POST')
                    else:
                        foto_permitida(S,rid,vid,metodo=='POST')
                        if scope_foto is None:scope_foto=alcance(S,rid,vid)[0]
                        if scope_foto!=d['scope_hash']:raise O.ErrorRegistro(403,'Foto fuera del ámbito actual.')
                except O.ErrorRegistro as e:
                    if metodo=='GET' and e.codigo==403:continue
                    raise
                actuales.append(d)
            if metodo=='GET':doc['registros']=actuales
            if metodo=='GET':
                try:
                    foto_permitida(S,rid,vid)
                    actual=alcance(S,rid,vid)[0]
                    if actual!=doc['scope_foto_actual']:
                        doc['scope_foto_actual']=actual
                        doc['registros']=[d for d in doc['registros'] if d['tipo']!='foto' or d['scope_hash']==actual]
                except O.ErrorRegistro as e:
                    if e.codigo==403:
                        doc['scope_foto_actual']=None
                        doc['registros']=[d for d in doc['registros'] if d['tipo']!='foto']
                    else:raise
            return self.responder(200,doc)
        except O.ErrorRegistro as e:return self.responder(e.codigo,{'error':str(e)})
        except (sqlite3.Error,OSError,ValueError,TypeError,KeyError,AttributeError):return self.responder(503,{'error':'Registro de control no disponible; no se confirma el cambio.'})
    H._api_get=lambda self,ruta,q,real,vista:responder(self,'GET',ruta,q,real,vista)
    H.api_post=lambda self,ruta,real,vista,b:responder(self,'POST',ruta,{},real,vista,b)
