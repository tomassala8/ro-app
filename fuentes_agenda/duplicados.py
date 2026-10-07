"""Deduplicación conservadora pura; nombres/horarios no prueban identidad de reunión."""
from collections import Counter
from copy import deepcopy
from datetime import datetime
import re
from urllib.parse import urlsplit

PRIORIDAD = {'bookings': 0, 'ghl': 1, 'crm': 2, 'calendar': 3, 'zoom': 4}


def referencia(valor):
    """Sólo referencias explícitas opacas; no convertir dict/list/número/título en ID."""
    return valor if isinstance(valor, str) and 1 <= len(valor) <= 200 and valor == valor.strip() and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/@-]*', valor) else None


def identidad(e):
    valor = e.get('referencia_reunion')
    if valor is not None and referencia(valor) is None:
        return None
    ref = referencia(valor)
    if ref:
        return ('referencia', ref)
    # Un crosswalk confirmado del caller, no coincidencia de nombre en con_quien.
    participante = referencia(e.get('participante_ref'))
    if e.get('identidad_confirmada') is True and participante:
        return ('participante_confirmado', participante)
    return None


def sala(e):
    encontrados = set()
    atajos = e.get('atajos') if isinstance(e.get('atajos'), list) else []
    for enlace in [e.get('join_url'), e.get('zoom_url'), e.get('enlace_zoom')] + [a.get('url') for a in atajos if isinstance(a, dict)]:
        if not isinstance(enlace, str):
            continue
        try:
            u = urlsplit(enlace)
            if u.scheme == 'https' and (u.hostname == 'zoom.us' or (u.hostname or '').endswith('.zoom.us')) and not u.username and not u.password:
                # No equivalencia de alias/sala numérica inferida; enlaces completos se conservan.
                if re.fullmatch(r'/(?:j|my|join|wc/join)/[^/]+/?', u.path):
                    encontrados.add((u.hostname, u.path.rstrip('/')))
        except ValueError:
            pass
    return encontrados


def ventana(e):
    try:
        ini, fin = e.get('inicio'), e.get('fin')
        if not isinstance(ini, str) or not isinstance(fin, str):
            return None
        a, b = datetime.fromisoformat(ini.replace('Z', '+00:00')), datetime.fromisoformat(fin.replace('Z', '+00:00'))
        if (a.tzinfo is None) != (b.tzinfo is None) or b <= a:
            return None
        # Exactitud de representación: caller debe normalizar zona, no se adivina aquí.
        return (ini, fin, bool(e.get('todo_el_dia')))
    except (ValueError, TypeError, OverflowError):
        return None


def deduplicar(eventos, privados=None):
    """Devuelve copia y IDs retirados. `privados` se conserva por compatibilidad, no se usa.

    El caller sólo aporta referencia común o identidad canónica confirmada tras
    verificar procedencia. Ningún campo aquí concede permisos ni confirma cliente.
    """
    originales = deepcopy(eventos)
    ids = Counter(e.get('id') for e in originales if isinstance(e, dict) and isinstance(e.get('id'), str))
    grupos = {}
    for e in originales:
        if not isinstance(e, dict):
            continue
        eid, propietario = e.get('id'), e.get('persona_id')
        if not isinstance(e.get('fuente'), str) or e.get('fuente') not in PRIORIDAD or not isinstance(eid, str) or not eid or ids[eid] != 1 or not referencia(propietario):
            continue
        quien, rango = identidad(e), ventana(e)
        if quien is None or rango is None:
            continue
        clave = (propietario, *rango, quien)
        grupos.setdefault(clave, []).append(e)
    fuera = set()
    for g in grupos.values():
        fuentes = [e['fuente'] for e in g]
        if len(g) < 2 or len(set(fuentes)) != len(fuentes):
            continue  # Doble reserva o ambigüedad: conservar todo el grupo.
        clientes = {e.get('cliente_ref') for e in g if isinstance(e.get('cliente_ref'), str) and e['cliente_ref']}
        # Un cliente malformado no debe convertirse en identidad igual al conocido.
        if any(e.get('cliente_ref') is not None and not isinstance(e.get('cliente_ref'), str) for e in g):
            continue
        participantes = {referencia(e.get('participante_ref')) for e in g if e.get('identidad_confirmada') is True and referencia(e.get('participante_ref'))}
        salas = set().union(*(sala(e) for e in g))
        if len(clientes) > 1 or len(salas) > 1 or len(participantes) > 1:
            continue
        g.sort(key=lambda e: (PRIORIDAD[e['fuente']], e['id']))
        principal = g[0]
        origenes, atajos, vistos, vistos_origen = [], [], set(), set()
        for e in g:
            anteriores = e.get('origenes') if isinstance(e.get('origenes'), list) else []
            for o in [{'fuente': e['fuente'], 'id': e['id']}, *anteriores]:
                if isinstance(o, dict) and isinstance(o.get('fuente'), str) and isinstance(o.get('id'), str):
                    clave_o = (o['fuente'], o['id'])
                    if clave_o not in vistos_origen:
                        origenes.append({'fuente': o['fuente'], 'id': o['id']}); vistos_origen.add(clave_o)
            for a in e.get('atajos') if isinstance(e.get('atajos'), list) else []:
                if not isinstance(a, dict) or not isinstance(a.get('url'), str) or (a.get('h') is not None and not isinstance(a.get('h'), str)):
                    continue
                k = (a.get('h'), a['url'])
                if k not in vistos:
                    atajos.append(a); vistos.add(k)
            for k in ('join_url', 'zoom_url', 'enlace_zoom'):
                if isinstance(e.get(k), str) and e[k]:
                    # Distintos enlaces de igual tipo no desaparecen por setdefault.
                    if principal.get(k) and principal[k] != e[k]:
                        ka = (k, e[k])
                        if ka not in vistos:
                            atajos.append({'h': k, 'url': e[k]}); vistos.add(ka)
                    else:
                        principal.setdefault(k, e[k])
            if e['fuente'] == 'zoom' and e.get('celebrada') is True:
                principal['celebrada'] = True
        principal['origenes'], principal['atajos'] = origenes, atajos
        anteriores = principal.get('tambien_en') if isinstance(principal.get('tambien_en'), list) else []
        principal['tambien_en'] = list(dict.fromkeys([f for f in anteriores if isinstance(f, str) and f != principal['fuente']] + [e['fuente'] for e in g[1:]]))
        fuera.update(e['id'] for e in g[1:])
    return [e for e in originales if not isinstance(e, dict) or not isinstance(e.get('id'), str) or e.get('id') not in fuera], fuera
