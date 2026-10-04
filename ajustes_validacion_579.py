"""Validación ordinaria de asignación, usando reglas de Altas; sin IO propio."""
import re
from datetime import date


def unica(filas, identidad):
    if not isinstance(identidad, str) or not identidad:
        return None
    xs = [x for x in filas or [] if isinstance(x, dict) and x.get('id') == identidad]
    return xs[0] if len(xs) == 1 else None


def fecha(v):
    if not isinstance(v, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', v):
        return False
    try:
        return date.fromisoformat(v).isoformat() == v
    except ValueError:
        return False


def asignacion(P, ACT, crudo, b, hoy):
    if not isinstance(b, dict):
        return None
    op = b.get('operacion')
    if op not in ('crear', 'cerrar', 'confirmar'):
        return None
    p = unica(crudo.get('personas'), b.get('persona_id'))
    c = unica(crudo.get('clientes'), b.get('cliente_id'))
    if not p or p.get('estado') != 'activo' or p.get('activo') is False or not c or c.get('activo') is False or c.get('estado') == 'baja':
        return None
    if ACT.es_activo_id(c['id']) is not True:
        return None
    roles = p.get('puestos')
    if not isinstance(roles, list) or not roles or not all(isinstance(x, str) and x in P.PUESTO for x in roles) or len(set(roles)) != len(roles):
        return None
    silla = b.get('silla')
    sillas = [s for pu in roles for s in P.REGLAS.get('sillas_de_puesto', {}).get(pu, [])]
    if not isinstance(silla, str) or silla not in P.REGLAS['sillas'] or silla not in sillas:
        return None
    for key in ('principal', 'suplencia'):
        if key in b and type(b[key]) is not bool:
            return None
    principal, suplencia = b.get('principal', True), b.get('suplencia', False)
    desde, hasta = b.get('desde'), b.get('hasta')
    if desde is not None and not fecha(desde) or hasta is not None and not fecha(hasta):
        return None
    if op == 'crear':
        desde = desde or hoy
        if not fecha(desde) or (suplencia and (not hasta or principal)):
            return None
    if op == 'cerrar':
        hasta = hasta or hoy
        if not fecha(hasta):
            return None
    if desde and hasta and hasta < desde:
        return None
    titular = b.get('titular_id')
    if titular is not None:
        t = unica(crudo.get('personas'), titular)
        if (not suplencia or not t or t['id'] == p['id'] or t.get('estado') != 'activo' or t.get('activo') is False
                or silla not in [s for pu in t.get('puestos') or [] for s in P.REGLAS.get('sillas_de_puesto', {}).get(pu, [])]):
            return None
    return dict(cliente_id=c['id'],persona_id=p['id'],silla=silla,desde=desde,hasta=hasta,
                principal=principal,suplencia=suplencia,titular_id=titular)
