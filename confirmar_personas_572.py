"""Contrato estrecho de confirmación, sin IO ni autoridad propia."""
import re


def identificador(v):
    return isinstance(v, str) and bool(re.fullmatch(r'[\w-]{1,100}', v))


def persona_vigente(personas, pid):
    if not identificador(pid) or not isinstance(personas, list):
        return None
    xs = [p for p in personas if isinstance(p, dict) and p.get('id') == pid]
    if len(xs) != 1 or xs[0].get('estado') not in ('activo', 'dudoso'):
        return None
    if xs[0]['estado'] == 'activo' and xs[0].get('activo') is False:
        return None
    return xs[0]


def validar_persona(r, personas, dudas=None):
    if not isinstance(r, dict) or set(r) - {'tipo', 'duda', 'persona_id', 'cambios', 'nota'}:
        return False
    if r.get('tipo') != 'persona' or not identificador(r.get('duda')):
        return False
    cambios = r.get('cambios')
    if not isinstance(cambios, dict) or set(cambios) != {'estado'} or cambios['estado'] not in ('activo', 'dudoso'):
        return False
    if 'nota' in r and (not isinstance(r['nota'], str) or len(r['nota']) > 2000):
        return False
    if persona_vigente(personas, r.get('persona_id')) is None:
        return False
    if dudas is not None:
        if not isinstance(dudas, list):
            return False
        ds = [d for d in dudas if isinstance(d, dict) and d.get('id') == r['duda']]
        if len(ds) != 1 or ds[0].get('tipo') != 'persona' or ds[0].get('persona_id') != r['persona_id']:
            return False
    return True


def validar_lista(resp, crudo):
    lista = resp if isinstance(resp, list) else [resp]
    if not lista or len(lista) > 100 or not isinstance(crudo, dict):
        return False
    dudas = crudo.get('para_confirmar')
    if not isinstance(dudas, list):
        return False
    did = None
    for r in lista:
        if not isinstance(r, dict) or r.get('tipo') not in ('persona', 'nota', 'asignacion', 'servicio') or not identificador(r.get('duda')):
            return False
        if did is None:
            did = r['duda']
        if r['duda'] != did:
            return False
        ds = [d for d in dudas if isinstance(d, dict) and d.get('id') == did]
        if len(ds) != 1:
            return False
        d = ds[0]
        if r['tipo'] == 'persona':
            if not validar_persona(r, crudo.get('personas'), dudas):
                return False
        elif r['tipo'] == 'nota':
            if set(r) - {'tipo', 'duda', 'nota'} or not isinstance(r.get('nota'), str) or not r['nota'].strip() or len(r['nota']) > 2000:
                return False
            if d.get('tipo') == 'persona' and persona_vigente(crudo.get('personas'), d.get('persona_id')) is None:
                return False
        else:
            # No convertir una duda de persona en cambios administrativos de otro tipo.
            if d.get('tipo') == 'persona' or 'cambios' in r:
                return False
    return True


def actor_actual(P, crudo, real):
    try:
        p = persona_vigente(crudo.get('personas'), real.get('id'))
        roles = real.get('puestos')
        if p is None or p.get('estado') != 'activo' or not isinstance(roles, list) or not roles or len(set(roles)) != len(roles) or not all(isinstance(x, str) and x in P.PUESTO for x in roles) or sorted(roles) != sorted(p.get('puestos') or []):
            return False
        return P.ver(p, {'tipo': 'ajustes_editar'}, P.contexto(p, crudo)).get('ok') is True
    except (TypeError, ValueError, KeyError, AttributeError):
        return False


def permite_estados(P, crudo, real, resp):
    """Misma restricción de mando de ajustes/persona; notas no cambian estado."""
    lista = resp if isinstance(resp, list) else [resp]
    mando = set(P.REGLAS.get('puestos_solo_tomas') or ['direccion', 'finanzas_direccion', 'rrhh', 'operaciones', 'ventas_ro', 'administracion'])
    try:
        for r in lista:
            if r.get('tipo') == 'persona':
                p = persona_vigente(crudo.get('personas'), r.get('persona_id'))
                if p is None:
                    return False
                if r['cambios']['estado'] != p.get('estado') and set(p.get('puestos') or []) & mando and 'direccion' not in real.get('puestos', []):
                    return False
        return True
    except (TypeError, KeyError, AttributeError):
        return False
