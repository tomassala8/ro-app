"""437: historial local exacto de un ticket autorizado. Sólo lecturas, sin IO al importar."""
import hashlib
import json
import math
import os
import re
import sqlite3
import stat
import uuid
from datetime import datetime, timezone
from pathlib import Path
from operaciones_registros_269 import unica, ErrorRegistro

RUTA = '/api/bandeja/triaje-intenciones'
VERSION = '437.1'
_ID = re.compile(r'[A-Za-z0-9_-]{1,120}')
MAX_FUENTE = 4_000_000
NIVELES = {'todo', 'suyo', 'resumen'}

class ErrorTriaje(Exception):
    def __init__(self, codigo, texto):
        self.codigo = codigo
        super().__init__(texto)

def _id(x):
    return isinstance(x, str) and _ID.fullmatch(x) is not None

def _hash(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def _ambito_impl(S, rid, vid, cid):
    if S.E.nucleo_bloqueado:
        raise ErrorTriaje(503, 'Permisos actuales no disponibles.')
    try:
        ps = [unica(S.E.crudo.get('personas'), x) for x in (rid, vid)]
    except ErrorRegistro:
        raise ErrorTriaje(403, 'Lectura no autorizada.') from None
    cps = []
    for p in ps:
        roles = p.get('puestos')
        if (not isinstance(roles, list) or not roles or not all(_id(x) for x in roles)
                or len(roles) != len(set(roles)) or S.ve_alguno(p, ['bandeja']) not in NIVELES):
            raise ErrorTriaje(403, 'Lectura no autorizada.')
        cps.append(S.P.contexto(p, S.E.crudo))
    if rid != vid and S.P.ver(ps[0], {'tipo': 'ver_como'}, cps[0]).get('ok') is not True:
        raise ErrorTriaje(403, 'Lectura no autorizada.')
    cs = S.E.crudo.get('clientes')
    cs = [c for c in cs if isinstance(c, dict) and c.get('id') == cid] if isinstance(cs, list) else []
    if (len(cs) != 1 or cs[0].get('activo') is False or cs[0].get('estado') == 'baja'
            or S.ACT.es_activo_id(cid) is not True
            or any(S.P.ver(p, {'tipo': 'cliente_detalle', 'cliente_id': cid}, cp).get('ok') is not True
                   for p, cp in zip(ps, cps))):
        raise ErrorTriaje(403, 'Lectura no autorizada.')
    return _hash([rid, vid, cid, S.E.crudo.get('personas'), S.E.crudo.get('clientes'),
                  S.E.crudo.get('asignaciones'),
                  [S.ve_alguno(p, ['bandeja']) for p in ps],
                  [[sorted(cp.get('cartera_ids') or []), {k: sorted(v) for k, v in (cp.get('cartera_por_silla') or {}).items()}] for cp in cps],
                  [S.P.ver(p, {'tipo': 'cliente_detalle', 'cliente_id': cid}, cp) for p, cp in zip(ps, cps)]])

def _ambito(S, rid, vid, cid):
    try:
        return _ambito_impl(S, rid, vid, cid)
    except ErrorTriaje:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise ErrorTriaje(503, 'El catálogo de autorización no supera la validación.') from None

def _pares(pares):
    salida = {}
    for k, v in pares:
        if k in salida:
            raise ValueError()
        salida[k] = v
    return salida

def _float(x):
    n = float(x)
    if not math.isfinite(n):
        raise ValueError()
    return n

def _ticket(path, tid, cid, detalles=False):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as f:
            a = os.fstat(f.fileno())
            if not stat.S_ISREG(a.st_mode) or a.st_nlink != 1 or a.st_size > MAX_FUENTE:
                raise ValueError()
            raw = f.read(MAX_FUENTE + 1)
            b = os.fstat(f.fileno())
            if len(raw) > MAX_FUENTE or (a.st_dev, a.st_ino, a.st_mtime_ns, a.st_size) != (b.st_dev, b.st_ino, b.st_mtime_ns, b.st_size):
                raise ValueError()
        doc = json.loads(raw.decode('utf8'), object_pairs_hook=_pares, parse_float=_float,
                         parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        rows = doc.get('triaje') if isinstance(doc, dict) else None
        if not isinstance(rows, list):
            raise ValueError()
        chosen = [t for t in rows if isinstance(t, dict) and t.get('id') == tid]
        if len(chosen) != 1:
            raise ErrorTriaje(404, 'Ticket no disponible en el reparto actual.')
        t = chosen[0]
        num = t.get('numero')
        if not _id(num) or t.get('cliente_id') != cid or t.get('propuesta') not in ('seguro', 'dudoso', 'sin_cliente', 'ruido'):
            raise ErrorTriaje(404, 'Ticket no disponible en el reparto actual.')
        if any(isinstance(x, dict) and x is not t and (x.get('id') in (tid, num) or x.get('numero') in (tid, num)) for x in rows):
            raise ErrorTriaje(503, 'La referencia del ticket no es inequívoca.')
        otros = doc.get('correos', [])
        if not isinstance(otros, list):
            raise ErrorTriaje(503, 'La referencia del ticket no es inequívoca.')
        coincidencias = [x for x in otros if isinstance(x, dict) and (x.get('id') in (tid, num) or x.get('numero') in (tid, num))]
        alias = None
        if coincidencias:
            # El productor documenta g-<número> (triaje) y t-<número> (correo).
            # No son dos tickets: sólo se admite el par exacto y concordante.
            if len(coincidencias) != 1:
                raise ErrorTriaje(503, 'La referencia del ticket no es inequívoca.')
            c = coincidencias[0]
            url, dep = t.get('url'), t.get('departamento')
            if (tid != 'g-' + num or c.get('id') != 't-' + num or not _id(c.get('id'))
                    or c.get('numero') != num or c.get('cliente_id') != cid
                    or not isinstance(url, str) or not url.startswith('https://') or len(url) > 2048
                    or c.get('url') != url or not isinstance(dep, str) or not dep or len(dep) > 120
                    or c.get('departamento') != dep
                    or sum(isinstance(x, dict) and x.get('id') == c['id'] for x in otros) != 1):
                raise ErrorTriaje(503, 'Las representaciones del ticket no son concordantes.')
            alias = c['id']
        ref = {k: t.get(k) for k in ('id', 'numero', 'cliente_id', 'propuesta', 'agente_propuesto_id', 'fecha')}
        if any(v is not None and (not isinstance(v, str) or len(v) > 120) for v in ref.values()):
            raise ValueError()
        # También revalidar la evidencia del alias después de la consulta SQLite.
        result = (num, _hash([ref, alias, t.get('url') if alias else None, t.get('departamento') if alias else None]), alias)
        return result + (ref,) if detalles else result
    except ErrorTriaje:
        raise
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        raise ErrorTriaje(503, 'La fuente del reparto no está disponible o no supera la validación.') from None

def referencia_para_guardia(path, tid, cid):
    """445: referencia mínima interna; nunca añade texto/PII al GET437."""
    return _ticket(path, tid, cid, detalles=True)

def _fecha(x):
    if not isinstance(x, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}', x):
        raise ValueError()
    return datetime.fromisoformat(x).replace(tzinfo=timezone.utc).isoformat()

def _ledger(S, rid, vid, cid, num, tid, alias=None):
    if os.environ.get('DATABASE_URL'):
        raise ErrorTriaje(503, 'La lectura exacta de este adaptador de registro no está validada.')
    path = Path(S.DB).absolute()
    try:
        a = path.lstat()
        if not stat.S_ISREG(a.st_mode) or a.st_nlink != 1:
            raise ValueError()
        with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=3) as con:
            con.row_factory = sqlite3.Row
            con.execute('PRAGMA query_only=ON')
            con.execute('BEGIN')
            refs = tuple(dict.fromkeys((num, tid) + ((alias,) if alias else ())))
            args = ('bandeja', 'desk') + refs
            where = "modulo=? AND herramienta=? AND objeto IN (" + ','.join('?' for _ in refs) + ") AND tipo IN ('asignar','cerrar')"
            # Buscar el ticket antes de agrupar; jamás LIMIT global ni exclusión silenciosa de vínculos inciertos.
            conflict = con.execute('SELECT count(*) FROM acciones WHERE ' + where + ' AND (cliente_id IS NULL OR cliente_id<>?)', args + (cid,)).fetchone()[0]
            if conflict:
                raise ValueError()
            resumen = {r['tipo']: (r['n'], r['ultimo']) for r in con.execute(
                'SELECT tipo,count(*) AS n,max(id) AS ultimo FROM acciones WHERE ' + where + ' AND cliente_id=? GROUP BY tipo', args + (cid,))}
            hay_intenciones = bool(con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='intenciones_acciones'").fetchone())
            result = {}
            for tipo in ('asignar', 'cerrar'):
                n, ultimo = resumen.get(tipo, (0, None))
                if type(n) is not int or not 0 <= n <= 9007199254740991:
                    raise ValueError()
                metadata = None
                if n:
                    r = con.execute('SELECT id,quien,tipo,objeto,cliente_id,estado,creada FROM acciones WHERE id=?', (ultimo,)).fetchone()
                    if (r is None or type(r['id']) is not int or not 0 < r['id'] <= 9007199254740991
                            or not _id(r['quien']) or r['tipo'] != tipo or r['cliente_id'] != cid
                            or r['estado'] not in ('simulada', 'pendiente', 'ok', 'error')):
                        raise ValueError()
                    propia = rid == vid == r['quien']
                    intents = list(con.execute('SELECT actor,intencion FROM intenciones_acciones WHERE accion_id=?', (ultimo,))) if hay_intenciones else []
                    if len(intents) > 1:
                        raise ValueError()
                    clave = None
                    if intents:
                        it = intents[0]
                        u = uuid.UUID(it['intencion'])
                        if it['actor'] != r['quien'] or str(u) != it['intencion'] or u.version != 4:
                            raise ValueError()
                        # Un alias legado por ID también bloquea, pero no ofrece UUID
                        # para reproducir un payload nuevo normalizado por número.
                        if propia and r['objeto'] == num:
                            clave = str(u)
                    metadata = {'accion_id': r['id'], 'estado_registro': r['estado'], 'intencion_id': clave,
                                'propia': propia, 'registrada_en': _fecha(r['creada'])}
                result[tipo] = {'cantidad': n, 'ultima': metadata}
            b = path.lstat()
            if (a.st_dev, a.st_ino) != (b.st_dev, b.st_ino):
                raise ValueError()
            return result
    except (OSError, ValueError, TypeError, AttributeError, sqlite3.Error):
        raise ErrorTriaje(503, 'El registro exacto no está disponible o contiene vínculos incoherentes; no acredita ausencia de intenciones.') from None

def listar(S, rid, vid, tid, cid):
    if not _id(tid) or not _id(cid):
        raise ErrorTriaje(400, 'Selecciona un ticket y cliente con referencias válidas.')
    scope = _ambito(S, rid, vid, cid)
    source = Path(S.DATA) / 'bandeja/bandeja.json'
    num, ref, alias = _ticket(source, tid, cid)
    tipos = _ledger(S, rid, vid, cid, num, tid, alias)
    num2, ref2, alias2 = _ticket(source, tid, cid)
    if (num, ref, alias) != (num2, ref2, alias2) or scope != _ambito(S, rid, vid, cid):
        raise ErrorTriaje(403, 'El ámbito o la referencia del ticket han cambiado durante la lectura.')
    return {'version': VERSION, 'ticket_id': tid, 'cliente_id': cid, 'objeto': num,
            'origen': 'ledger_local', 'lectura_exacta': True, 'confirmacion_desk': False,
            'generado': datetime.now(timezone.utc).isoformat(), 'huella_fuente_ticket': ref, 'tipos': tipos}

def enganchar(H, S):
    original = H._api_get
    def get(self, ruta, q, real, persona):
        if ruta != RUTA:
            return original(self, ruta, q, real, persona)
        if (set(q) != {'ticket_id', 'cliente_id'} or any(not isinstance(q[k], list) or len(q[k]) != 1 for k in q)):
            return self.responder(400, {'error': 'Selecciona exactamente un ticket y un cliente.'})
        try:
            return self.responder(200, listar(S, real.get('id'), persona.get('id'), q['ticket_id'][0], q['cliente_id'][0]))
        except ErrorTriaje as e:
            return self.responder(e.codigo, {'error': str(e)})
    H._api_get = get
