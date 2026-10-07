"""445: exclusión local por ticket bajo la transacción SQLite194. No entrega en Desk."""
import os
import sqlite3
from pathlib import Path
import piloto_lectura
import triaje_intenciones_437 as T
from intenciones_acciones import identidad, RechazoAccion
from operaciones_registros_269 import unica, ErrorRegistro

VERSION = '445.1'

def aplica(b):
    if not isinstance(b, dict) or (b.get('modulo'), b.get('herramienta')) != ('bandeja', 'desk') or b.get('tipo') not in ('asignar', 'cerrar'):
        return False
    vp = b.get('vista_previa')
    if not isinstance(vp, dict):
        return False
    if vp.get('origen') == 'triaje':
        return True
    # Compatibilidad EXACTA con cerrar432 ya emitido, sin cambiar su UUID/cuerpo.
    return (b['tipo'] == 'cerrar' and isinstance(b.get('objeto'), str)
            and set(vp) == {'estado', 'ticket'} and vp == {'estado': 'Cerrado', 'ticket': b['objeto']}
            and b.get('texto') == 'Solicitar cierre del ticket ' + b['objeto'] + ' desde el reparto')

def adaptador_disponible():
    return not bool(os.environ.get('DATABASE_URL'))

def _referencia(S, actor, b):
    cid, num = b.get('cliente_id'), b.get('objeto')
    if not T._id(cid) or not T._id(num):
        raise RechazoAccion(400, 'La intención de reparto necesita ticket y cliente exactos.')
    scope = T._ambito(S, actor, actor, cid)
    p = unica(S.E.crudo.get('personas'), actor)
    cp = S.P.contexto(p, S.E.crudo)
    reglas = S.P.REGLAS
    policy = T._hash(reglas)
    permitidas = reglas.get('acciones_permitidas') or {}
    tipo = b['tipo']
    if ('desk' not in permitidas.get('_herramientas', [])
            or tipo not in permitidas.get('*', []) + permitidas.get('bandeja', [])
            or not S.lleva_cliente(p, cid, cp)):
        raise RechazoAccion(403, 'La intención de reparto no está autorizada actualmente.')
    solo = (reglas.get('acciones_solo_puestos') or {}).get(tipo)
    if solo and not set(p['puestos']).intersection(solo):
        raise RechazoAccion(403, 'La intención de reparto no está autorizada actualmente.')
    regla_cliente = (reglas.get('acciones_regla_cliente') or {}).get(tipo)
    if regla_cliente and S.P.ver(p, {'tipo': regla_cliente, 'cliente_id': cid,
                                  'cliente_nuevo': any(c.get('id') == cid and c.get('nuevo') for c in S.E.crudo['clientes'])}, cp).get('ok') is not True:
        raise RechazoAccion(403, 'La intención de reparto no está autorizada actualmente.')
    numero, firma, alias, fila = T.referencia_para_guardia(Path(S.DATA) / 'bandeja/bandeja.json', 'g-' + num, cid)
    vp = b.get('vista_previa')
    if set(b) != {'modulo', 'herramienta', 'tipo', 'objeto', 'cliente_id', 'intencion_id', 'texto', 'vista_previa'} or numero != num:
        raise RechazoAccion(400, 'La intención de reparto no tiene el contrato exacto.')
    if tipo == 'asignar':
        if set(vp) != {'a', 'ticket', 'origen'} or vp.get('ticket') != num or vp.get('origen') != 'triaje' or vp.get('a') != fila.get('agente_propuesto_id'):
            raise RechazoAccion(409, 'La propuesta de reparto cambió; revisa el ticket actual.')
        recipient = unica(S.E.crudo.get('personas'), vp.get('a'))
        roles = recipient.get('puestos')
        if not isinstance(roles, list) or not roles or any(not T._id(r) for r in roles) or len(set(roles)) != len(roles):
            raise RechazoAccion(403, 'El receptor actual no es inequívoco.')
        if not set(p['puestos']).intersection({'direccion', 'operaciones', 'proyectos'}):
            raise RechazoAccion(403, 'El reparto no está autorizado para este puesto.')
        if b.get('texto') != 'Solicitar asignación del ticket ' + num:
            raise RechazoAccion(400, 'La intención de reparto no tiene el contrato exacto.')
    elif vp != {'estado': 'Cerrado', 'ticket': num} or b.get('texto') != 'Solicitar cierre del ticket ' + num + ' desde el reparto':
        raise RechazoAccion(400, 'La intención de reparto no tiene el contrato exacto.')
    try:
        clave, huella = identidad(actor, b)
    except ValueError as e:
        raise RechazoAccion(400, str(e)) from None
    if scope != T._ambito(S, actor, actor, cid) or policy != T._hash(S.P.REGLAS):
        raise RechazoAccion(403, 'La autoridad cambió durante la lectura del reparto.')
    return {'actor': actor, 'cliente_id': cid, 'numero': num, 'scope': scope, 'source': firma,
            'refs': tuple(dict.fromkeys((num, fila['id']) + ((alias,) if alias else ()))), 'intencion': clave, 'body': huella}

def preparar(S, con, real, persona, b):
    if not aplica(b):
        return None
    if (not adaptador_disponible() or not isinstance(con, sqlite3.Connection) or not con.in_transaction):
        raise RechazoAccion(503, 'La exclusión atómica de este adaptador de reparto no está validada.')
    if piloto_lectura.activo() or real.get('id') != persona.get('id'):
        raise RechazoAccion(403, 'Esta sesión sólo permite consulta.')
    try:
        return _referencia(S, real.get('id'), b)
    except RechazoAccion:
        raise
    except T.ErrorTriaje as e:
        raise RechazoAccion(409 if e.codigo == 404 else e.codigo, str(e)) from None
    except ErrorRegistro:
        raise RechazoAccion(403, 'La identidad o el receptor actuales no son inequívocos.') from None
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise RechazoAccion(503, 'La autoridad de reparto no supera la validación.') from None

def sin_previa(con, guardia):
    if guardia is None:
        return
    if not isinstance(con, sqlite3.Connection) or not con.in_transaction:
        raise RechazoAccion(503, 'Falta la transacción atómica del reparto.')
    refs = guardia['refs']
    # Cuenta cualquier solicitud Desk anterior por esos IDs comprobados: otros actores,
    # otro tipo, legado sin UUID/cliente o módulo distinto. Sólo bloquea el nuevo triaje.
    where = "herramienta='desk' AND tipo IN ('asignar','cerrar') AND objeto IN (" + ','.join('?' for _ in refs) + ')'
    if con.execute('SELECT 1 FROM acciones WHERE ' + where + ' LIMIT 1', refs).fetchone():
        raise RechazoAccion(409, 'Ya existe una intención local para este ticket. Consulta Envíos antes de otra solicitud.')

def revalidar(S, con, real, persona, b, guardia):
    if guardia is None:
        return
    actual = preparar(S, con, real, persona, b)
    if actual != guardia:
        raise RechazoAccion(409, 'El ámbito o la fuente cambiaron durante el guardado; no se conserva esta nueva intención.')
