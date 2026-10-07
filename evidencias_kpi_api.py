"""151. Hechos declarados locales. Importar/enganchar no crea depósitos ni llama proveedores."""
import os
import sqlite3
import json
import stat
from zoneinfo import ZoneInfo
from acciones_lectura_544 import ambito
from pathlib import Path
import config
from evidencias_kpi import ArchivoEvidencias, ErrorEvidencia, identificador, validar, clave_uuid, fecha_aware
from datetime import date, datetime, timezone
import re

RUTA='/api/clientes/evidencias_kpi'
ROLES={'account','operaciones','direccion'}

def unico(filas,pid):
    if not isinstance(filas,list):raise ErrorEvidencia(503,'Catálogo no disponible.')
    encontrados=[p for p in filas if isinstance(p,dict) and p.get('id')==pid]
    if len(encontrados)!=1:raise ErrorEvidencia(403,'Identidad o cliente no inequívoco.')
    return encontrados[0]

def autorizar(S,real_id,vista_id,cid,escritura=False):
    if S.E.nucleo_bloqueado:raise ErrorEvidencia(503,'Fuente de permisos bloqueada.')
    if not all(identificador(x) for x in (real_id,vista_id,cid)):raise ErrorEvidencia(403,'Ámbito no autorizado.')
    if escritura and real_id!=vista_id:raise ErrorEvidencia(403,'Ver como sólo permite lectura.')
    crudo=S.E.crudo
    cliente=unico(crudo.get('clientes'),cid)
    if S.ACT.es_activo_id(cid) is not True or cliente.get('estado')=='baja' or cliente.get('activo') is False:raise ErrorEvidencia(403,'Cliente activo no confirmado.')
    personas={}
    for pid in (real_id,vista_id):
        p=unico(crudo.get('personas'),pid)
        roles=p.get('puestos')
        if p.get('estado')!='activo' or p.get('activo') is False or not isinstance(roles,list) or not set(roles)&ROLES:raise ErrorEvidencia(403,'Este registro no corresponde a tu puesto activo.')
        cp=S.P.contexto(p,crudo)
        if not S.ve_alguno(p,['mi-trabajo']):raise ErrorEvidencia(403,'Fuente de trabajo no autorizada.')
        tipos=['cliente_detalle']+(['responder_cliente'] if escritura else [])
        if any(S.P.ver(p,{'tipo':tipo,'cliente_id':cid},cp).get('ok') is not True for tipo in tipos):raise ErrorEvidencia(403,'Cliente fuera de tu ámbito.')
        personas[pid]=p
    return {cid:{'activo_confirmado':True}},personas

def validar_registro(S,r,cid):
    """No serializar payload privado arbitrario/corrupto ni scope distinto al SQL."""
    campos={'cliente_id','tipo','canal','motivo','fecha','fecha_madrid','semana_inicio','mes','enlace','source_kind','verificacion_externa','id','registrado_por','registrado_en','estado','cumplimiento'}
    if isinstance(r,dict) and r.get('tipo')=='informe_enviado':campos.add('periodo_informe')
    if not isinstance(r,dict) or set(r)!=campos or r.get('cliente_id')!=cid or not clave_uuid(r.get('id')) or not identificador(r.get('registrado_por')):
        raise ErrorEvidencia(503,'Registro almacenado incoherente; no se puede publicar.')
    # Conserva autores históricos, pero un ID arbitrario no se convierte en identidad.
    try:unico(S.E.crudo.get('personas'),r['registrado_por'])
    except ErrorEvidencia:raise ErrorEvidencia(503,'Autor del registro almacenado no inequívoco.')
    if r['source_kind']!='registro_equipo' or r['verificacion_externa'] is not False or r['cumplimiento'] is not None or r['estado'] not in ('declarado','revocado'):
        raise ErrorEvidencia(503,'Registro almacenado incoherente; no se puede publicar.')
    try:
        now=datetime.now(timezone.utc)
        registrado=fecha_aware(r['registrado_en'])
        if registrado>now:raise ValueError('fecha futura')
        payload={'clave':r['id'],'cliente_id':cid,**{k:r[k] for k in ('tipo','canal','motivo','fecha','semana_inicio','enlace')}}
        if r['tipo']=='informe_enviado':payload['periodo_informe']=r['periodo_informe']
        d=validar(payload,now)
        if any(r[k]!=v for k,v in d.items()):raise ValueError('normalización incoherente')
    except (ErrorEvidencia,ValueError,TypeError,KeyError):raise ErrorEvidencia(503,'Registro almacenado incoherente; no se puede publicar.')
    return {k:r[k] for k in campos}


def validar_salida(S,doc,cid,recibo=False):
    if not isinstance(doc,dict):raise ErrorEvidencia(503,'Respuesta local incoherente.')
    if recibo:
        if doc.get('resultado') not in ('aceptado','duplicado'):raise ErrorEvidencia(503,'Recibo local incoherente.')
        return {'resultado':doc['resultado'],'registro':validar_registro(S,doc.get('registro'),cid)}
    if doc.get('cliente_id')!=cid or not isinstance(doc.get('registros'),list):raise ErrorEvidencia(503,'Archivo local incoherente.')
    return {'cliente_id':cid,'registros':[validar_registro(S,r,cid) for r in doc['registros']],
            'cobertura':{'source_kind':'registro_equipo','contacto_exhaustivo':False,'verificacion_externa':False},'cumplimiento':None}

def deposito():
    ruta=os.environ.get('RO_EVIDENCIAS_KPI')
    if (os.environ.get('DATABASE_URL') or os.environ.get('PGDATABASE_URL')) and not ruta:raise ErrorEvidencia(503,'El depósito independiente no está habilitado en este entorno.')
    p=Path(ruta) if ruta else config.ESTADO_DIR/'evidencias_kpi'/'registros.sqlite3'
    if not p.is_absolute():raise ErrorEvidencia(503,'Configuración del depósito inválida.')
    return p

def archivo(S,rid,vid,cid,escritura):
    catalogo,personas=autorizar(S,rid,vid,cid,escritura)
    # Esta función se ejecuta otra vez bajo BEGIN IMMEDIATE: usa fuente/cartera/rol actuales.
    def vigente(pid,cliente):
        autorizar(S,rid,vid,cliente,escritura)
        return pid in (rid,vid)
    return ArchivoEvidencias(deposito(),catalogo,personas,vigente)

def resumen(S,rid,vid,semana):
    if not isinstance(semana,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',semana):raise ErrorEvidencia(400,'Selecciona el lunes exacto.')
    try:inicio=date.fromisoformat(semana)
    except ValueError:raise ErrorEvidencia(400,'Periodo inválido.')
    if inicio.weekday()!=0:raise ErrorEvidencia(400,'Selecciona el lunes exacto.')
    if S.E.nucleo_bloqueado:raise ErrorEvidencia(503,'Fuente de permisos bloqueada.')
    # Identidades inválidas no devuelven un resumen vacío que parezca autorizado.
    for pid in (rid,vid):
        p=unico(S.E.crudo.get('personas'),pid)
        if p.get('estado')!='activo' or p.get('activo') is False or not isinstance(p.get('puestos'),list) or not set(p['puestos'])&ROLES or not S.ve_alguno(p,['mi-trabajo']):raise ErrorEvidencia(403,'Resumen no autorizado.')
    ids=set()
    for c in S.E.crudo.get('clientes') or []:
        cid=c.get('id') if isinstance(c,dict) else None
        if not identificador(cid):continue
        try:autorizar(S,rid,vid,cid)
        except ErrorEvidencia as e:
            if e.codigo==503:raise
            continue
        ids.add(cid)
    filas={cid:{'cliente_id':cid,'contactos_declarados':0,'reuniones_declaradas':0,'source_kind':'registro_equipo','verificacion_externa':False,'cumplimiento':None} for cid in sorted(ids)}
    if ids:
        a=archivo(S,rid,vid,next(iter(ids)),False)
        with a._conectar() as con:
            # Una lectura; no agrupar ni publicar actores, fechas individuales o referencias.
            rows=con.execute('SELECT * FROM registros WHERE estado=?',('declarado',)).fetchall()
        for row in rows:
            if row['cliente'] not in ids:continue
            d=validar_registro(S,a._dto(row),row['cliente'])
            if d.get('semana_inicio')==semana and d.get('tipo') in ('contacto','reunion'):
                filas[row['cliente']]['contactos_declarados' if d['tipo']=='contacto' else 'reuniones_declaradas']+=1
        # Evitar entregar un cliente si cambió su autorización durante la lectura.
        for cid in ids:autorizar(S,rid,vid,cid)
    return {'semana_inicio':semana,'clientes':list(filas.values()),'cobertura':'parcial','verificacion_externa':False,'cumplimiento':None,'nota':'Los conteos son declaraciones del equipo. Cero no significa ausencia de contacto o reunión ni acredita cumplimiento.'}

def _ambito_informes611(S,rid,vid):
    # Sólo identidades del servidor; no roles recibidos del navegador.
    if S.E.nucleo_bloqueado:raise ErrorEvidencia(503,'Fuente de permisos bloqueada.')
    ps=[unico(S.E.crudo.get('personas'),pid) for pid in (rid,vid)]
    a=ambito(S.E,S.P,S.ACT,*ps)
    if a is None:raise ErrorEvidencia(403,'Resumen no autorizado en el ámbito actual.')
    if not all(set(p['puestos'])&ROLES and S.ve_alguno(p,['mi-trabajo']) for p in a[0]):
        raise ErrorEvidencia(403,'Resumen no autorizado.')
    ids=set()
    for c in S.E.crudo.get('clientes') or []:
        cid=c.get('id') if isinstance(c,dict) else None
        if not identificador(cid):continue
        try:autorizar(S,rid,vid,cid)
        except ErrorEvidencia as e:
            if e.codigo==503:raise
            continue
        ids.add(cid)
    final=ambito(S.E,S.P,S.ACT,*ps)
    if final is None or final[2]!=a[2]:raise ErrorEvidencia(403,'El ámbito actual cambió durante la lectura.')
    return a[2],ids

def _marca_deposito611(p):
    # No crear ni reparar un archivo/esquema desde esta lectura.
    if not p.is_absolute() or p.resolve()!=p:raise ErrorEvidencia(503,'Depósito no disponible.')
    for ancestor in p.parents:
        if ancestor.is_symlink():raise ErrorEvidencia(503,'Depósito no disponible.')
    parent=p.parent.stat()
    if parent.st_uid!=os.getuid() or parent.st_mode&0o077:raise ErrorEvidencia(503,'Depósito no disponible.')
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        st=os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid() or st.st_nlink!=1
                or st.st_mode&0o077 or st.st_size>32*1024*1024):
            raise ErrorEvidencia(503,'Depósito no disponible.')
        return st.st_dev,st.st_ino,st.st_ctime_ns,st.st_mtime_ns,st.st_size
    finally:os.close(fd)

def _leer_informes611(p):
    marca=_marca_deposito611(p)
    con=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True,timeout=5)
    try:
        con.row_factory=sqlite3.Row
        con.execute('PRAGMA query_only=ON')
        rows=con.execute('SELECT * FROM registros').fetchall()
    finally:con.close()
    if _marca_deposito611(p)!=marca:raise ErrorEvidencia(503,'El depósito cambió durante la lectura.')
    return rows

def _objeto_registro611(texto):
    def objeto(pares):
        d={}
        for k,v in pares:
            if k in d:raise ValueError('Registro ambiguo.')
            d[k]=v
        return d
    def constante(_):raise ValueError('Registro no finito.')
    return json.loads(texto,object_pairs_hook=objeto,parse_constant=constante)

def resumen_informes611(S,rid,vid,periodo):
    if not isinstance(periodo,str) or not re.fullmatch(r'[1-9]\d{3}-(?:0[1-9]|1[0-2])',periodo):
        raise ErrorEvidencia(400,'Selecciona un único mes válido.')
    hoy=datetime.now(timezone.utc).astimezone(ZoneInfo('Europe/Madrid'))
    if periodo>hoy.strftime('%Y-%m'):raise ErrorEvidencia(400,'El mes no puede ser futuro.')
    firma,ids=_ambito_informes611(S,rid,vid)
    filas={cid:{'cliente_id':cid,'informes_declarados':0,'source_kind':'registro_equipo',
                'verificacion_externa':False,'cumplimiento':None} for cid in sorted(ids)}
    if ids:
        p=deposito()
        rows=_leer_informes611(p)
        vistos=set()
        for row in rows:
            if row['cliente'] not in ids:continue
            _objeto_registro611(row['payload'])
            d=validar_registro(S,ArchivoEvidencias._dto(None,row),row['cliente'])
            if d['id'] in vistos:raise ErrorEvidencia(503,'Registro almacenado no inequívoco.')
            vistos.add(d['id'])
            if d['estado']=='declarado' and d['tipo']=='informe_enviado' and d['periodo_informe']==periodo:
                filas[d['cliente_id']]['informes_declarados']+=1
    if _ambito_informes611(S,rid,vid)!=(firma,ids):
        raise ErrorEvidencia(403,'El ámbito actual cambió durante la lectura.')
    return {'version':'611.1','periodo_informe':periodo,'source_kind':'registro_equipo','clientes':list(filas.values()),
            'cobertura':'parcial','verificacion_externa':False,'cumplimiento':None,
            'nota':'Declaraciones activas por mes del informe, no por fecha de envío. Cero no acredita ausencia de envío ni cumplimiento; no hay verificación externa.'}

def enganchar(Manejador,S):
    get_orig,post_orig=Manejador._api_get,Manejador.api_post
    def error(self,e):
        if isinstance(e,ErrorEvidencia):return self.responder(e.codigo,{'error':str(e)})
        return self.responder(503,{'error':'El registro local no está disponible. No se ha confirmado el guardado.'})
    def get(self,ruta,q,real,vista):
        if ruta not in (RUTA,RUTA+'/resumen',RUTA+'/informes'):return get_orig(self,ruta,q,real,vista)
        try:
            if ruta==RUTA+'/informes':
                if not isinstance(q,dict) or set(q)!={'periodo_informe'} or not isinstance(q['periodo_informe'],list) or len(q['periodo_informe'])!=1:
                    raise ErrorEvidencia(400,'Selecciona un único mes del informe.')
                return self.responder(200,resumen_informes611(S,real.get('id'),vista.get('id'),q['periodo_informe'][0]))
            if ruta==RUTA+'/resumen':
                if not isinstance(q,dict) or set(q)-{'semana_inicio'} or not isinstance(q.get('semana_inicio'),list) or len(q['semana_inicio'])!=1:raise ErrorEvidencia(400,'Selecciona un único periodo.')
                return self.responder(200,resumen(S,real.get('id'),vista.get('id'),q['semana_inicio'][0]))
            if not isinstance(q,dict) or set(q)-{'cliente_id'} or not isinstance(q.get('cliente_id'),list) or len(q['cliente_id'])!=1:raise ErrorEvidencia(400,'Selecciona un único cliente.')
            cid=q['cliente_id'][0];rid,vid=real.get('id'),vista.get('id')
            doc=archivo(S,rid,vid,cid,False).listar(rid,vid,cid)
            autorizar(S,rid,vid,cid)
            return self.responder(200,validar_salida(S,doc,cid))
        except (ErrorEvidencia,OSError,sqlite3.Error,ValueError,TypeError,KeyError,AttributeError) as e:return error(self,e)
    def post(self,ruta,real,vista,b):
        if ruta!=RUTA:return post_orig(self,ruta,real,vista,b)
        try:
            if not isinstance(b,dict):raise ErrorEvidencia(400,'Registro inválido.')
            accion=b.get('accion');cid=b.get('cliente_id');rid,vid=real.get('id'),vista.get('id')
            autorizar(S,rid,vid,cid,True)
            payload={k:v for k,v in b.items() if k!='accion'}
            if accion=='registrar':validar(payload,datetime.now(timezone.utc))
            elif accion=='revocar':
                if set(payload)!={'clave','cliente_id','registro_id','motivo'}:raise ErrorEvidencia(400,'Revocación inválida.')
            else:raise ErrorEvidencia(400,'Acción no admitida.')
            a=archivo(S,rid,vid,cid,True)
            doc=a.registrar(rid,vid,payload) if accion=='registrar' else a.revocar(rid,vid,cid,b['registro_id'],b['clave'],b['motivo'])
            autorizar(S,rid,vid,cid,True)
            return self.responder(200,validar_salida(S,doc,cid,True))
        except (ErrorEvidencia,OSError,sqlite3.Error,ValueError,TypeError,KeyError,AttributeError) as e:return error(self,e)
    Manejador._api_get=get;Manejador.api_post=post
