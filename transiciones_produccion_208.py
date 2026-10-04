"""208: revisiones duraderas de Producción; lectura local y validación, sin envíos.

El caller194 conserva BEGIN IMMEDIATE/INSERT. No crea tablas ni depósitos.
"""
import hashlib,json,re,sys
from collections import defaultdict
import mi_trabajo as M
import transiciones_mi_trabajo as T
from identidades_clickup_204 import autores_confirmados

RUTA='/api/produccion/transiciones'
MODULO='produccion'
TIPOS={'pieza_aprobar','pieza_pedir_cambios','mover_estado'}
ORIGENES_A_REVISION={'diario','en curso','planning semanal','próximo sprint'}
S=None
class Rechazo(Exception):
    def __init__(self,codigo,texto):self.codigo=codigo;super().__init__(texto)

def unico(rows,pid):
    encontrados=[r for r in rows if isinstance(r,dict) and r.get('id')==pid]
    if len(encontrados)!=1:raise Rechazo(403,'Identidad o cliente no inequívocos.')
    return encontrados[0]

def fuentes():
    D=M.doc()
    if not isinstance(D,dict):raise Rechazo(503,'No hay copia de tareas disponible.')
    filas=defaultdict(list)
    for r in D.get('tareas') or []:
        if isinstance(r,dict) and isinstance(r.get('id'),str):filas[r['id']].append(r)
    return {'D':D,'filas':dict(filas),'identidad':M._fuente_autorizacion_tareas()}

def identidades(real,vista,escritura=False):
    if S.E.nucleo_bloqueado:raise Rechazo(503,'Fuente de permisos bloqueada.')
    if escritura and real.get('id')!=vista.get('id'):raise Rechazo(403,'Ver como sólo permite consulta.')
    out=[]
    for p in (real,vista):
        current=unico(S.E.crudo.get('personas') or [],p.get('id'))
        if current.get('estado')!='activo' or current.get('activo') is False or not S.ve_alguno(current,[MODULO]):raise Rechazo(403,'Producción no está autorizada para la identidad activa.')
        out.append((current,S.P.contexto(current,S.E.crudo)))
    return out

def pieza_actual(tid,src):
    try:
        row=T.tarea_unica(src['D'],tid,src['filas'].get(tid,[]))
        cat=T.catalogo(src['D'],row['lista_id'])
        if cat.get(row['estado'])!=row.get('tipo_estado'):raise ValueError('tipo')
        owners=autores_confirmados(row,src['identidad'])
        raw=src['identidad']['tareas'].get(tid,[])
        if len(raw)!=1 or not isinstance(raw[0].get('asignados'),list) or not raw[0]['asignados']:raise ValueError('autores')
        # 204 permite owners parciales para otras acciones; revisar exige TODOS.
        for a in raw[0]['asignados']:
            pid=src['identidad']['identidades'].get(str(a['id']))
            pp=src['identidad']['personas'].get(pid,[])
            if len(pp)!=1 or pp[0].get('estado')!='activo' or pp[0].get('activo') is False or pid not in owners:raise ValueError('autor sin resolver')
        if not owners:raise ValueError('autores vacíos')
        prod=S.tarea_de_produccion(tid)
        if not prod or prod.get('cli')!=row.get('cli') or prod.get('estado')!=row['estado']:raise ValueError('producción')
        return row,cat,{'id':tid,'cli':row.get('cli'),'estado':row['estado'],'autores':owners}
    except (ValueError,KeyError,TypeError):raise Rechazo(409,'Copia, catálogo o autoría canónica incompletos o contradictorios.')

def autorizar(real,vista,tid,tipo,src,escritura=False):
    ident=src.get('_contextos') or identidades(real,vista,escritura)
    if tipo not in TIPOS:raise Rechazo(400,'Tipo de revisión no permitido.')
    row,cat,piece=pieza_actual(tid,src);cid=row.get('cli')
    if not isinstance(cid,str) or not cid:raise Rechazo(403,'La tarea necesita cliente confirmado.')
    c=unico(S.E.crudo.get('clientes') or [],cid)
    if S.ACT.es_activo_id(cid) is not True or c.get('activo') is False or c.get('estado')=='baja':raise Rechazo(403,'Cliente activo no confirmado.')
    en_revision=S.pieza_en_revision(tid)
    if en_revision and (en_revision.get('cli')!=cid or en_revision.get('estado')!=row['estado']):raise Rechazo(409,'Las copias de revisión no coinciden.')
    for p,cp in ident:
        if S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},cp).get('ok') is not True:raise Rechazo(403,'Cliente fuera de tu ámbito de Producción.')
        if tipo in ('pieza_aprobar','pieza_pedir_cambios'):
            if not en_revision or not S.puede_revisar_pieza(p,piece,cp):raise Rechazo(403,'La pieza no la revisas tú; nadie se aprueba a sí mismo.')
        else:
            if en_revision or row['estado'] not in ORIGENES_A_REVISION:raise Rechazo(403,'La etapa actual no permite pasar a revisión desde esta acción.')
            if not (p['id'] in piece['autores'] or set(p.get('puestos') or [])&{'direccion','operaciones'} or any(unico(S.E.crudo.get('personas') or [],a).get('jefe')==p['id'] for a in piece['autores'])):raise Rechazo(403,'La tarea no es tuya ni de tu equipo.')
    return row,cat,piece

def destino(tipo,row,cat):
    rp=S.P.REGLAS.get('revision_piezas') or {}
    if tipo=='pieza_aprobar':wanted=((rp.get('por_estado') or {}).get(row['estado']) or {}).get('a')
    elif tipo=='pieza_pedir_cambios':wanted=rp.get('pedir_cambios_a')
    else:wanted='revisión project manager'  # Política exacta del botón A revisión existente.
    if not isinstance(wanted,str) or wanted not in cat or wanted==row['estado']:raise Rechazo(409,'El destino de revisión no existe como estado exacto en la lista.')
    sinc=sys.modules.get('sincronia')
    if sinc is None:raise Rechazo(503,'No está disponible la traducción local de la cola.')
    try:
        channel,obj,change,base,_=sinc.traducir({'tipo':tipo,'objeto':row['id'],'cliente_id':row['cli'],'texto':'Validación de revisión','vista_previa':json.dumps({'a':wanted,'comentario':'Cambios por revisar'})})
        if channel!='clickup' or obj.get('ref')!=row['id'] or obj.get('resuelto') is not True or change.get('campo')!='estado' or change.get('valor')!=wanted or not isinstance(base,dict) or base.get('estado')!=row['estado']:raise ValueError('traducción')
    except (ValueError,TypeError,KeyError):raise Rechazo(409,'La traducción de sincronía no concuerda con la copia y el destino.')
    return wanted

def revision_produccion(actual,row,piece,src):
    # Firma propiedad canónica y política además de la copia/cola genérica191.
    prueba={'tarea':row['id'],'cliente':row['cli'],'lista':row['lista_id'],'estado':row['estado'],
            'tipo':row.get('tipo_estado'),'autores':sorted(piece['autores']),
            'asignacion_fuente':src['identidad']['tareas'][row['id']][0].get('asignados'),
            'reglas':S.P.REGLAS.get('revision_piezas'),'generado':src['D'].get('generado'),
            'catalogo':src['D'].get('estados_detalle',{}).get(row['lista_id']),'base':actual['revision']}
    # Sólo IDs de asignación canónicos; jamás correos/nombres ni texto raw en hash.
    prueba['asignacion_fuente']=sorted(str(x['id']) for x in prueba['asignacion_fuente'])
    return hashlib.sha256(json.dumps(prueba,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def forma(b):
    if not isinstance(b,dict):raise Rechazo(400,'Cuerpo de acción inválido.')
    vp=b.get('vista_previa')
    if b.get('modulo')!=MODULO or b.get('herramienta')!='clickup' or b.get('tipo') not in TIPOS or not isinstance(vp,dict) or vp.get('transicion_produccion') is not True or vp.get('transicion_tablero') is not None:raise Rechazo(400,'La revisión necesita su origen y contrato de Producción.')
    if not isinstance(b.get('objeto'),str) or not re.fullmatch(r'[\w-]{3,80}',b['objeto']):raise Rechazo(400,'ID de tarea inválido.')
    if not isinstance(b.get('intencion_id'),str) or not re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}',b['intencion_id'],re.I):raise Rechazo(400,'Falta intención UUIDv4.')
    if not isinstance(vp.get('lista_id'),str) or not vp['lista_id'] or not isinstance(vp.get('expected_estado'),str) or not isinstance(vp.get('revision'),str) or not re.fullmatch(r'[0-9a-f]{64}',vp['revision']) or not isinstance(vp.get('a'),str):raise Rechazo(400,'Falta revisión o estado exactos.')
    if b['tipo']=='pieza_pedir_cambios':
        comentario=vp.get('comentario')
        if not isinstance(comentario,str) or not 3<=len(comentario.strip())<=2000:raise Rechazo(400,'Pedir cambios necesita un comentario de 3 a 2.000 caracteres.')
    return vp

def validar_previo(real,vista,b,src=None):
    try:
        vp=forma(b);src=src or fuentes()
        row,cat,_=autorizar(real,vista,b['objeto'],b['tipo'],src,True)
        if b.get('cliente_id') not in (None,'',row['cli']):raise Rechazo(403,'El cliente no corresponde a la pieza.')
        if vp['lista_id']!=row['lista_id']:raise Rechazo(409,'La pieza cambió de lista.')
        if vp['a']!=destino(b['tipo'],row,cat):raise Rechazo(400,'El destino no es el que establece la revisión vigente.')
        # No comparar revision/expected_estado aquí: replay194 precede al CAS.
        return row['cli'],None
    except Rechazo as e:return None,(e.codigo,str(e))

def validar_en_transaccion(con,real,b):
    try:
        cap=T.capacidad(con,real,real)
        if not cap['activo']:raise Rechazo(403 if cap['motivo']=='piloto_solo_lectura' else 503,'La revisión durable no está habilitada en este modo.')
        if not con.in_transaction:raise Rechazo(409,'La revisión necesita la transacción de escritura.')
        src=fuentes();cid,error=validar_previo(real,real,b,src)
        if error:return error
        row,cat,piece=autorizar(real,real,b['objeto'],b['tipo'],src,True)
        vp=b['vista_previa'];actual=T.proyectar(src['D'],b['objeto'],con)
        actual['revision']=revision_produccion(actual,row,piece,src)
        if actual['bloqueada'] or actual['expected_estado']!=row['estado'] or any(vp[k]!=actual[k] for k in ('lista_id','expected_estado','revision')):raise Rechazo(409,'La pieza o su cola cambiaron; actualiza antes de revisar.')
        # Revalidar permisos/ruta y fuente después de la lectura de cola.
        latest=fuentes();_,error=validar_previo(real,real,b,latest)
        if error:return error
        fresh,_,freshpiece=autorizar(real,real,b['objeto'],b['tipo'],latest,True)
        latest_actual=T.proyectar(latest['D'],b['objeto'],con)
        if vp['revision']!=revision_produccion(latest_actual,fresh,freshpiece,latest):raise Rechazo(409,'Autoría, política o copia cambiaron durante la revisión.')
        if any(fresh.get(k)!=row.get(k) for k in ('cli','lista_id','estado','tipo_estado')):raise Rechazo(409,'La fuente cambió durante la revisión.')
        return None
    except Rechazo as e:return e.codigo,str(e)
    except (ValueError,TypeError,KeyError):return 409,'Copia de revisión incoherente; actualiza.'

def obtener(con,real,vista):
    identidades(real,vista);cap=T.capacidad(con,real,vista)
    out={'capacidad_revision':{**cap,'version':'206.1'},'transiciones_revision':{},'estados_detalle':{},'cobertura':{'fuente':'copia_local','completa':False}}
    if not cap['activo']:return out
    src=fuentes();src['_contextos']=identidades(real,vista);candidatos=[]
    for tid in src['filas']:
        try:
            row=T.tarea_unica(src['D'],tid,src['filas'][tid])
            if row['estado'] in ORIGENES_A_REVISION or row['estado'] in (S.P.REGLAS.get('revision_piezas') or {}).get('por_estado',{}):candidatos.append(tid)
        except (ValueError,TypeError):continue
    indices=T.preparar_lectura(src['D'],con,candidatos,src['filas'])
    for tid in candidatos:
        acciones={};row=None
        for tipo in TIPOS:
            try:
                row,cat,piece=autorizar(real,vista,tid,tipo,src)
                a=destino(tipo,row,cat);acciones[tipo]={'autorizacion_confirmada':True,'destino':a}
            except Rechazo:continue
        if not acciones:continue
        try:
            actual=T.proyectar(src['D'],tid,con,indices)
            if actual['bloqueada'] or actual['expected_estado']!=row['estado']:continue
            actual['revision']=revision_produccion(actual,row,piece,src)
            out['transiciones_revision'][tid]={'modulo':MODULO,'tarea_id':tid,'cliente_id':row['cli'],'tipo_estado':row['tipo_estado'],**actual,'acciones':acciones}
            out['estados_detalle'][row['lista_id']]=src['D']['estados_detalle'][row['lista_id']]
        except (ValueError,TypeError,KeyError):continue
    # Revalidación actual justo antes de serializar: no conservar permisos retirados.
    final=fuentes();final['_contextos']=identidades(real,vista)
    for tid,token in list(out['transiciones_revision'].items()):
        for tipo in list(token['acciones']):
            try:
                row,cat,piece=autorizar(real,vista,tid,tipo,final)
                fresh_actual=T.proyectar(final['D'],tid,con,indices)
                if revision_produccion(fresh_actual,row,piece,final)!=token['revision']:raise Rechazo(409,'Cambio de autoría o copia')
                if destino(tipo,row,cat)!=token['acciones'][tipo]['destino']:raise Rechazo(409,'Cambio de regla')
            except Rechazo:del token['acciones'][tipo]
        if not token['acciones']:del out['transiciones_revision'][tid]
    listas={x['lista_id'] for x in out['transiciones_revision'].values()}
    out['estados_detalle']={k:v for k,v in out['estados_detalle'].items() if k in listas}
    return out

def enganchar(H,servir):
    global S
    S=servir;oldget=H._api_get;oldvalidar=H.validar_accion
    def get(self,ruta,q,real,vista):
        if ruta!=RUTA:return oldget(self,ruta,q,real,vista)
        if q:return self.responder(400,{'error':'Esta consulta no admite filtros ni identidades por parámetros.'})
        try:
            with S.conectar() as con:return self.responder(200,obtener(con,real,vista))
        except Rechazo as e:return self.responder(e.codigo,{'error':str(e)})
    def validar(self,real,vista,b):
        vp=b.get('vista_previa')
        if isinstance(vp,dict) and vp.get('transicion_produccion') is True:
            cid,error=validar_previo(real,vista,b)
            if error:return None,error
        return oldvalidar(self,real,vista,b)
    H._api_get=get;H.validar_accion=validar
