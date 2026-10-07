"""F30: preferencias privadas del tablero en SQLite; nunca contiene tareas ni busca texto."""
import json
import re
import uuid

VERSION = 1
CAMPOS = {'vista', 'preset', 'asignado', 'cliente', 'lista', 'proyecto', 'prioridad', 'etiqueta'}
DEFAULT = dict(vista='mia', preset='daily', asignado='', cliente='', lista='', proyecto='', prioridad='', etiqueta='')
ID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')


class Conflicto(ValueError):
    pass


def cadena(v, limite):
    if not isinstance(v, str) or len(v) > limite or any(ord(c) < 32 or ord(c) == 127 for c in v):
        raise ValueError('Texto de preferencia no válido.')
    return v


def filtros_validos(f):
    if not isinstance(f, dict) or set(f) != CAMPOS:
        raise ValueError('Filtros no válidos; no se guarda búsqueda libre ni otros campos.')
    f = dict(f)
    for valor in f.values():
        cadena(valor, 160)
    if f['vista'] not in ('mia', 'equipo') or f['preset'] not in ('daily', 'todo'):
        raise ValueError('Vista o preset no válido.')
    if f['prioridad'] not in ('', '1', '2', '3', '4', '5', 'urgent', 'high', 'normal', 'low'):
        raise ValueError('Prioridad no válida.')
    return f


def referencias(tareas):
    return {'asignado': {a for t in tareas for a in t.get('asignados') or []} | ({'__sin_asignar'} if any(not t.get('asignados') for t in tareas) else set()),
            'cliente': {t['cli'] for t in tareas if t.get('cli')} | ({'__sin_cliente'} if any(not t.get('cli') for t in tareas) else set()),
            'lista': {t['lista_id'] for t in tareas if t.get('lista_id')},
            'proyecto': {t.get('proyecto') or t.get('carpeta') for t in tareas if t.get('proyecto') or t.get('carpeta')},
            'etiqueta': {a for t in tareas for a in t.get('etiquetas') or [] if isinstance(a, str)}}


def comprobar_referencias(f, tareas):
    refs = referencias(tareas)
    if any(f[c] and f[c] not in permitidas for c, permitidas in refs.items()):
        raise ValueError('Un filtro no está en el inventario autorizado actual; no se puede guardar.')


def preparar(con):
    # No confirmar trabajo ajeno: este almacén requiere conexión sin transacción previa.
    if getattr(con, 'in_transaction', None) is not False:
        raise ValueError('Las preferencias requieren una conexión propia sin transacción abierta.')
    con.execute('''CREATE TABLE IF NOT EXISTS tareas_vistas_privadas (
        propietario TEXT NOT NULL, id TEXT NOT NULL, nombre TEXT NOT NULL,
        filtros TEXT NOT NULL, version INTEGER NOT NULL, revision INTEGER NOT NULL,
        PRIMARY KEY(propietario,id))''')


def pares_unicos(pares):
    d = {}
    for k, v in pares:
        if k in d:
            raise ValueError('Preferencia almacenada ambigua.')
        d[k] = v
    return d


def dto(r):
    if r['version'] != VERSION or type(r['revision']) is not int or r['revision'] < 1 or not ID.fullmatch(r['id']):
        raise ValueError('Versión de preferencia no válida.')
    nombre = cadena(r['nombre'], 60).strip()
    if not nombre:
        raise ValueError('Nombre vacío.')
    if not isinstance(r['filtros'], str) or len(r['filtros']) > 8192:
        raise ValueError('Preferencia almacenada demasiado grande.')
    return {'id': r['id'], 'nombre': nombre, 'revision': r['revision'],
            'filtros': filtros_validos(json.loads(r['filtros'], object_pairs_hook=pares_unicos))}


def listar(con, propietario):
    preparar(con)
    vistas, invalidas = [], 0
    for r in con.execute('SELECT * FROM tareas_vistas_privadas WHERE propietario=? ORDER BY nombre,id LIMIT 21', (propietario,)):
        try:
            if len(vistas) == 20:
                raise ValueError('Límite de vistas excedido.')
            vistas.append(dto(r))
        except (ValueError, TypeError, KeyError):
            invalidas += 1
    return {'vistas': vistas, 'invalidas': invalidas, 'limite': 20, 'version': VERSION}


def mutar(con, propietario, b, tareas):
    if not isinstance(b, dict) or b.get('accion') not in ('guardar', 'eliminar'):
        raise ValueError('Acción de preferencia no válida.')
    permitidos = {'accion', 'id', 'revision'} | ({'nombre', 'filtros'} if b['accion'] == 'guardar' else set())
    if set(b) - permitidos:
        raise ValueError('Campos de preferencia no válidos.')
    ref = b.get('id')
    if ref is not None and (not isinstance(ref, str) or not ID.fullmatch(ref)):
        raise ValueError('Referencia de vista no válida.')
    if ref and (type(b.get('revision')) is not int or b['revision'] < 1):
        raise ValueError('Falta revisión de la vista.')
    if not ref and ('revision' in b or b['accion'] == 'eliminar'):
        raise ValueError('Falta referencia de vista.')
    if b['accion'] == 'guardar':
        nombre = cadena(b.get('nombre'), 60).strip()
        if not nombre:
            raise ValueError('Pon un nombre a esta vista.')
        filtros = filtros_validos(b.get('filtros'))
        comprobar_referencias(filtros, tareas)
    preparar(con)
    con.execute('BEGIN IMMEDIATE')
    try:
        previa = con.execute('SELECT * FROM tareas_vistas_privadas WHERE propietario=? AND id=?', (propietario, ref)).fetchone() if ref else None
        if ref and (not previa or previa['revision'] != b['revision']):
            raise Conflicto('La vista cambió o ya no está disponible. Recarga las vistas.')
        if b['accion'] == 'eliminar':
            con.execute('DELETE FROM tareas_vistas_privadas WHERE propietario=? AND id=? AND revision=?', (propietario, ref, b['revision']))
            con.commit()
            return {'ok': True, 'eliminada': ref}
        if not ref:
            if con.execute('SELECT count(*) FROM tareas_vistas_privadas WHERE propietario=?', (propietario,)).fetchone()[0] >= 20:
                raise ValueError('Puedes guardar como máximo 20 vistas privadas.')
            ref = str(uuid.uuid4())
            revision = 1
            con.execute('INSERT INTO tareas_vistas_privadas VALUES (?,?,?,?,?,?)',
                        (propietario, ref, nombre, json.dumps(filtros, ensure_ascii=False), VERSION, revision))
        else:
            revision = b['revision'] + 1
            con.execute('UPDATE tareas_vistas_privadas SET nombre=?, filtros=?,version=?,revision=? WHERE propietario=? AND id=?',
                        (nombre, json.dumps(filtros, ensure_ascii=False), VERSION, revision, propietario, ref))
        con.commit()
        return {'ok': True, 'vista': {'id': ref, 'nombre': nombre, 'filtros': filtros, 'revision': revision}}
    except Exception:
        con.rollback()
        raise
