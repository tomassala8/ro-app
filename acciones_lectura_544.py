"""Proyección actual de contenido de acciones. Sin IO al importar ni permisos propios."""
import json
import re


def _tipo_firma550(valor):
    """ACT conserva índices y regex compilada; no convertir objetos arbitrarios a texto."""
    if isinstance(valor, (set, frozenset)):
        if not all(isinstance(v, str) for v in valor):
            raise TypeError('Índice de ámbito no válido.')
        return {'_tipo_firma': 'conjunto_cadenas', 'valores': sorted(valor)}
    if isinstance(valor, re.Pattern) and isinstance(valor.pattern, str):
        return {'_tipo_firma': 'patron', 'patron': valor.pattern, 'flags': valor.flags}
    raise TypeError('Tipo de ámbito no acreditado.')


def ambito(E, P, ACT, real, persona):
    try:
        if E.nucleo_bloqueado:
            return None
        ps = []
        for identidad in (real, persona):
            if not isinstance(identidad.get('id'), str) or not identidad['id']:
                return None
            xs = [p for p in E.crudo.get('personas') or []
                  if isinstance(p, dict) and p.get('id') == identidad['id']]
            roles = identidad.get('puestos')
            if (len(xs) != 1 or xs[0].get('estado') != 'activo' or xs[0].get('activo') is False
                    or not isinstance(roles, list) or not roles
                    or not all(isinstance(r, str) and r in P.PUESTO for r in roles)
                    or len(set(roles)) != len(roles)
                    or sorted(xs[0].get('puestos') or []) != sorted(roles)):
                return None
            ps.append(xs[0])
        cps = [P.contexto(p, E.crudo) for p in ps]
        firma = json.dumps([E.crudo, P.REGLAS, E.modulos, ACT.estado(), P.hoy_iso()],
                           sort_keys=True, ensure_ascii=False, allow_nan=False, default=_tipo_firma550)
        return ps, cps, firma
    except (AttributeError, TypeError, ValueError, KeyError):
        return None


def cliente_visible(cid, E, P, ACT, ps, cps):
    try:
        cs = [c for c in E.crudo.get('clientes') or []
              if isinstance(c, dict) and c.get('id') == cid]
        return (isinstance(cid, str) and bool(cid) and len(cs) == 1
                and cs[0].get('activo') is not False and cs[0].get('estado') != 'baja'
                and ACT.es_activo_id(cid) is True
                and all(P.ver(p, {'tipo': 'cliente_detalle', 'cliente_id': cid}, cp).get('ok') is True
                        for p, cp in zip(ps, cps)))
    except (AttributeError, TypeError, ValueError, KeyError):
        return False


def fila_visible(r, E, P, ACT, ve_alguno, ps, cps, vista_id):
    try:
        modulo = r['modulo']
        if not modulo or not all(ve_alguno(p, [modulo]) for p in ps):
            return False
        cid = r['cliente_id']
        if cid is None:
            return r['quien'] == vista_id or all(ve_alguno(p, [modulo]) == 'todo' for p in ps)
        return cliente_visible(cid, E, P, ACT, ps, cps)
    except (AttributeError, TypeError, ValueError, KeyError, IndexError):
        return False


def recortar_vistas(filas, P, quitar, recortar, claves_inversion, claves_captacion):
    """Misma política económica preexistente de GETacciones; no examina texto libre."""
    tipos = set(P.REGLAS.get('acciones_vista_previa_recortada') or [])
    salida = [dict(r) for r in filas]
    for r in salida:
        if r.get('tipo') in tipos and r.get('vista_previa'):
            try:
                vp = json.loads(r['vista_previa'])
            except Exception:
                vp = None
            q = quitar(r.get('cliente_id'))
            if claves_inversion() in q:
                q.append(claves_captacion())
            r['vista_previa'] = json.dumps(recortar(vp, q) if isinstance(vp, dict) else None,
                                          ensure_ascii=False)
    return salida
