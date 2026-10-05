"""Planes y revisión locales, separados del marcador visto. Sin proveedor/IO al importar.
El servidor inyecta fuente canónica, política, conexión y reloj. Historial append-only.
"""
import hashlib
import json
import re
from datetime import date, datetime, timezone
from uuid import UUID
from contexto_tarea import texto_operativo

REVISOR_ID = 'constanza'  # Identidad explícitamente confirmada por dirección, nunca alias.
ESQUEMA = """CREATE TABLE IF NOT EXISTS planes_fuegos_255 (
  accion_id TEXT PRIMARY KEY, cliente_id TEXT NOT NULL, version INTEGER NOT NULL,
  operacion TEXT NOT NULL, actor_id TEXT NOT NULL, hora TEXT NOT NULL,
  payload_hash TEXT NOT NULL, datos TEXT NOT NULL, UNIQUE(cliente_id, version)
);
CREATE TRIGGER IF NOT EXISTS fuego255_sin_update BEFORE UPDATE ON planes_fuegos_255 BEGIN SELECT RAISE(ABORT, 'El historial de planes no se modifica'); END;
CREATE TRIGGER IF NOT EXISTS fuego255_sin_delete BEFORE DELETE ON planes_fuegos_255 BEGIN SELECT RAISE(ABORT, 'El historial de planes no se borra'); END;
"""

class ErrorPlan(ValueError):
    def __init__(self, codigo, texto):
        self.codigo, self.texto = codigo, texto
        super().__init__(texto)

def iniciar(con):
    con.executescript(ESQUEMA)

def _activa(crudo, pid):
    filas = [p for p in crudo.get('personas', []) if p.get('id') == pid]
    return filas[0] if len(filas) == 1 and filas[0].get('estado') == 'activo' and filas[0].get('activo') is not False else None

def permisos(S, real, vista, cid):
    if getattr(S.E, 'nucleo_bloqueado', False):
        raise ErrorPlan(503, 'Los datos de permisos no están disponibles de forma segura.')
    crudo = S.E.crudo
    clientes = [c for c in crudo.get('clientes', []) if c.get('id') == cid]
    if not isinstance(cid, str) or not re.fullmatch(r'[\w-]{1,80}', cid) or len(clientes) != 1 or S.ACT.es_activo_id(cid) is not True:
        raise ErrorPlan(404, 'No se puede abrir el plan de este cliente.')
    actuales = [_activa(crudo, p.get('id')) for p in (real, vista)]
    if not all(actuales) or not all(S.ve_alguno(p, ['en-rojo']) and S.P.ver(p, {'tipo':'cliente_detalle', 'cliente_id':cid}, S.P.contexto(p, crudo))['ok'] for p in actuales):
        raise ErrorPlan(404, 'No se puede abrir el plan de este cliente.')
    r, v = actuales
    lectura = r['id'] != v['id'] or S.PILOTO_LECTURA.activo()
    cp = S.P.contexto(r, crudo)
    roles = set(S.P.puestos_de(r))
    editar = not lectura and (bool(roles & {'operaciones','direccion'}) or ('account' in roles and cid in cp.get('cartera_por_silla', {}).get('account', set())))
    revisor = _activa(crudo, REVISOR_ID)
    revisar = not lectura and r['id'] == REVISOR_ID and revisor is not None and 'proyectos' in set(revisor.get('puestos', []))
    visibles = S.P.recortar(v, crudo).get('personas', [])
    responsables = [{'id':p['id']} for p in visibles if _activa(crudo, p.get('id')) and len([x for x in visibles if x.get('id') == p['id']]) == 1]
    return {'editar':editar, 'revisar':revisar, 'solo_lectura':lectura, 'responsables':responsables}

def _historial(con, cid):
    return [dict(r) for r in con.execute('SELECT * FROM planes_fuegos_255 WHERE cliente_id=? ORDER BY version DESC LIMIT 101', (cid,)).fetchall()]

def leer(con, cid, capacidades):
    filas = _historial(con, cid)
    version = filas[0]['version'] if filas else 0
    eventos = []
    for f in filas[:100]:
        eventos.append({'version':f['version'], 'operacion':f['operacion'], 'actor_id':f['actor_id'], 'hora':f['hora'], **json.loads(f['datos'])})
    # El plan vigente no tiene por qué estar entre los últimos cien vistos.
    row = con.execute("SELECT * FROM planes_fuegos_255 WHERE cliente_id=? AND operacion='plan' AND version<=? ORDER BY version DESC LIMIT 1", (cid,version)).fetchone()
    plan = {'version':row['version'], 'actor_id':row['actor_id'], 'hora':row['hora'], **json.loads(row['datos'])} if row else None
    revision = None
    if plan:
        for f in con.execute("SELECT * FROM planes_fuegos_255 WHERE cliente_id=? AND operacion='revision' AND version>? AND version<=? ORDER BY version DESC LIMIT 1", (cid,plan['version'],version)):
            d = json.loads(f['datos'])
            if d.get('plan_version') == plan['version']:
                revision = {'version':f['version'], 'actor_id':f['actor_id'], 'hora':f['hora'], **d}
                break
    return {'cliente_id':cid, 'version':version, 'plan':plan, 'revision':revision,
            'historial':eventos, 'historial_truncado':len(filas)>100, 'capacidades':capacidades,
            'origen':'local', 'confirmado_proveedor':False, 'texto':'Guardado sólo en RO; no se envía a otras herramientas.'}

def _validar(b, caps):
    if not isinstance(b, dict):
        raise ErrorPlan(400, 'La solicitud no es válida.')
    op = b.get('operacion')
    comunes = {'cliente_id','operacion','accion_id','expected_version'}
    extras = {'que','responsable_id','plazo'} if op == 'plan' else {'plan_version','estado','nota'} if op == 'revision' else set()
    if op not in ('plan','revision') or set(b)-comunes-extras or not comunes.issubset(b):
        raise ErrorPlan(400, 'La solicitud no es válida.')
    if not caps['editar' if op=='plan' else 'revisar']:
        raise ErrorPlan(403, 'No puedes guardar este cambio; consulta el plan en lectura.')
    try:
        aid = str(UUID(b['accion_id']))
    except (ValueError, TypeError, AttributeError):
        raise ErrorPlan(400, 'Falta una identidad de solicitud válida.')
    ver = b['expected_version']
    if type(ver) is not int or ver < 0:
        raise ErrorPlan(400, 'La versión no es válida.')
    if op == 'plan':
        if not isinstance(b.get('que'), str) or len(b['que']) > 1500:
            raise ErrorPlan(400, 'Describe qué se hará (máximo 1500 caracteres).')
        que = texto_operativo(b['que'], 1500)
        if len(que) < 3 or not que.replace('[dato protegido omitido]', '').strip():
            raise ErrorPlan(400, 'Describe una acción sin datos protegidos.')
        if b.get('responsable_id') not in {p['id'] for p in caps['responsables']}:
            raise ErrorPlan(400, 'El responsable no está confirmado como activo y visible.')
        try:
            plazo = date.fromisoformat(b['plazo'])
            if plazo.isoformat() != b['plazo']: raise ValueError()
        except (TypeError, ValueError):
            raise ErrorPlan(400, 'El plazo debe ser una fecha válida.')
        datos = {'que':que, 'responsable_id':b['responsable_id'], 'plazo':plazo.isoformat()}
    else:
        if type(b.get('plan_version')) is not int or b['plan_version'] < 1 or b.get('estado') not in ('visto','pedir_cambios') or not isinstance(b.get('nota',''), str) or len(b.get('nota','')) > 500:
            raise ErrorPlan(400, 'La revisión no es válida.')
        nota = texto_operativo(b.get('nota',''), 500)
        if b['estado'] == 'pedir_cambios' and len(nota) < 3:
            raise ErrorPlan(400, 'Indica qué hay que cambiar.')
        datos = {'plan_version':b['plan_version'], 'estado':b['estado'], 'nota':nota}
    return op, aid, ver, datos

def guardar(con, b, caps, actor, hora):
    op, aid, ver, datos = _validar(b, caps)
    firma = hashlib.sha256(json.dumps([b['cliente_id'], actor, op, ver, datos], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    previo = con.execute('SELECT * FROM planes_fuegos_255 WHERE accion_id=?', (aid,)).fetchone()
    if previo:
        if previo['payload_hash'] != firma: raise ErrorPlan(409, 'La solicitud ya existe con otro contenido.')
        return {'ok':True, 'repetida':True, 'recibo':{'accion_id':aid,'version':previo['version'],'origen':'local'}, **leer(con,b['cliente_id'],caps)}
    vigente = leer(con,b['cliente_id'],caps)
    if vigente['version'] != ver:
        raise ErrorPlan(409, 'El plan cambió. Recarga antes de guardar; tu texto no se ha enviado.')
    if op == 'revision' and (not vigente['plan'] or vigente['plan']['version'] != datos['plan_version']):
        raise ErrorPlan(409, 'Esta revisión pertenece a otra versión del plan.')
    con.execute('INSERT OR IGNORE INTO planes_fuegos_255 (accion_id,cliente_id,version,operacion,actor_id,hora,payload_hash,datos) VALUES (?,?,?,?,?,?,?,?)',
                (aid,b['cliente_id'],ver+1,op,actor,hora,firma,json.dumps(datos,ensure_ascii=False)))
    propia = con.execute('SELECT * FROM planes_fuegos_255 WHERE accion_id=?', (aid,)).fetchone()
    if not propia or propia['payload_hash'] != firma:
        raise ErrorPlan(409, 'Hubo otro cambio simultáneo. Recarga antes de guardar.')
    return {'ok':True, 'repetida':False, 'recibo':{'accion_id':aid,'version':propia['version'],'origen':'local'}, **leer(con,b['cliente_id'],caps)}

def responder(S, real, vista, *, query=None, cuerpo=None):
    try:
        if cuerpo is None:
            if not isinstance(query, dict) or set(query) != {'cliente_id'} or len(query['cliente_id']) != 1:
                raise ErrorPlan(400, 'Elige un solo cliente.')
            cid = query['cliente_id'][0]
        else:
            cid = cuerpo.get('cliente_id') if isinstance(cuerpo, dict) else None
        caps = permisos(S, real, vista, cid)
        with S.conectar() as con:
            if cuerpo is None: return 200, leer(con,cid,caps)
            # Horas/autoría son del servidor. El cliente no puede suministrarlas.
            hora = datetime.now(timezone.utc).isoformat(timespec='seconds')
            res = guardar(con,cuerpo,caps,real['id'],hora)
        return 200, res  # El with confirma primero el commit, nunca éxito antes de persistir.
    except ErrorPlan as e:
        return e.codigo, {'error':e.texto}
