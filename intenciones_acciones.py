"""Intenciones persistentes: una petición reintentada conserva la misma acción.

El llamador debe autorizar la acción y abrir una transacción BEGIN IMMEDIATE.
La intención y la acción se guardan en esa misma transacción; no hay envíos aquí.
"""
import hashlib
import json
import uuid


class RechazoAccion(ValueError):
    def __init__(self, codigo, texto):
        super().__init__(texto)
        self.codigo = codigo


class PersistenciaNoDisponible(RuntimeError):
    pass


def iniciar(con):
    if not hasattr(con, "in_transaction"):
        raise PersistenciaNoDisponible("Las intenciones persistentes necesitan validar primero el adaptador de esta base.")
    con.execute("BEGIN IMMEDIATE")


class ConflictoIntencion(ValueError):
    pass


def preparar(con):
    con.execute('''CREATE TABLE IF NOT EXISTS intenciones_acciones (
        actor TEXT NOT NULL,
        intencion TEXT NOT NULL,
        huella TEXT NOT NULL,
        accion_id INTEGER NOT NULL REFERENCES acciones(id),
        PRIMARY KEY(actor, intencion)
    )''')


def identidad(actor, cuerpo):
    clave = cuerpo.get('intencion_id')
    if not isinstance(actor, str) or not actor.strip():
        raise ValueError('Falta la identidad autorizada.')
    if not isinstance(clave, str):
        raise ValueError('Falta la intención de la acción.')
    try:
        parsed = uuid.UUID(clave)
    except (ValueError, AttributeError):
        raise ValueError('La intención debe ser un UUID canónico.') from None
    if str(parsed) != clave or parsed.version != 4:
        raise ValueError('La intención debe ser un UUID v4 canónico.')
    contenido = {k: v for k, v in cuerpo.items() if k != 'intencion_id'}
    try:
        serializado = json.dumps(contenido, ensure_ascii=False, sort_keys=True,
                                 separators=(',', ':'), allow_nan=False)
    except (TypeError, ValueError):
        raise ValueError('El contenido de la acción no es válido.') from None
    if len(serializado.encode('utf-8')) > 32000:
        raise ValueError('La acción supera el límite de tamaño.')
    return clave, hashlib.sha256(serializado.encode('utf-8')).hexdigest()


def guardar(con, actor, cuerpo, insertar):
    """Devuelve (acción_id, repetida). No confirma ni despacha a ClickUp."""
    if not con.in_transaction:
        raise RuntimeError('La intención necesita una transacción explícita.')
    preparar(con)
    clave, huella = identidad(actor, cuerpo)
    fila = con.execute('SELECT huella, accion_id FROM intenciones_acciones '
                       'WHERE actor=? AND intencion=?', (actor, clave)).fetchone()
    if fila:
        if fila[0] != huella:
            raise ConflictoIntencion('Esa intención ya corresponde a otra acción.')
        existe = con.execute('SELECT 1 FROM acciones WHERE id=?', (fila[1],)).fetchone()
        if not existe:
            raise ConflictoIntencion('La acción guardada necesita revisión de integridad.')
        return fila[1], True
    aid = insertar(con)
    if not isinstance(aid, int) or isinstance(aid, bool) or aid < 1:
        raise ValueError('La acción no se ha guardado correctamente.')
    if not con.execute('SELECT 1 FROM acciones WHERE id=?', (aid,)).fetchone():
        raise ValueError('La acción no existe en la transacción.')
    con.execute('INSERT INTO intenciones_acciones(actor,intencion,huella,accion_id) '
                'VALUES (?,?,?,?)', (actor, clave, huella, aid))
    return aid, False
