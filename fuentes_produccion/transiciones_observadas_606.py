"""Contrato606 puro. No IO, historia reconstruida, permisos nuevos ni fuentes pendientes."""
from collections import Counter
from datetime import datetime, timezone
import re

VERSION = '606.1'
DIRECTOS = frozenset({'planning semanal', 'diario', 'en curso'})
TIPOS = frozenset({'open', 'unstarted', 'custom', 'active', 'done', 'closed'})

def _id(v):
    return v if isinstance(v, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,150}', v) else None

def _hora(v):
    if not isinstance(v, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})', v):
        return None
    if not v.endswith('Z'):
        h, m = map(int, v[-5:].split(':'))
        if h > 14 or m > 59 or (h == 14 and m):
            return None
    try:
        return datetime.fromisoformat(v.replace('Z', '+00:00')).astimezone(timezone.utc)
    except ValueError:
        return None

def _iso(v):
    return v.isoformat().replace('+00:00', 'Z')

def _catalogo(raw):
    """Cada lista tiene estados [{nombre,tipo}], sin alias ni nombres ambiguos."""
    out = {}
    if not isinstance(raw, dict):
        return out
    for lid, rows in raw.items():
        if _id(lid) is None or not isinstance(rows, list):
            continue
        names = [r.get('nombre') for r in rows if isinstance(r, dict)]
        if len(names) != len(rows) or any(not isinstance(n, str) or not n or len(n) > 120 for n in names) or len(set(names)) != len(names):
            continue
        if any(not isinstance(r.get('tipo'), str) or r['tipo'] not in TIPOS for r in rows):
            continue
        out[lid] = {r['nombre']: r['tipo'] for r in rows}
    return out

def proyectar(eventos, tareas, catalogo, clientes_activos, actores_activos, desde, hasta, corte):
    """Rango [desde,hasta). Caller entrega IDs canónicos ACT/personas y grants intersectados.

    tareas: identidad exacta + creación/creador/inicial/fuente y historial {completo,
    desde_creacion,hasta}. Clasificación fuego opcional {confirmado,fuente,instante}.
    Completo se refiere a la cadena de UNA tarea, nunca a inventario global de tareas.
    """
    d, h, c = map(_hora, (desde, hasta, corte))
    if None in (d, h, c) or not d < h <= c:
        raise ValueError('Rango y corte aware válidos requeridos')
    if not isinstance(eventos, list) or not isinstance(tareas, list) or not isinstance(clientes_activos, set) or not isinstance(actores_activos, set):
        raise ValueError('Fuentes/ámbitos explícitos requeridos')
    if any(_id(x) is None for x in clientes_activos | actores_activos):
        raise ValueError('Ámbito no canónico')
    cats = _catalogo(catalogo)
    diag = Counter()
    task_counts = Counter(t.get('task_id') for t in tareas if isinstance(t, dict) and _id(t.get('task_id')))
    event_counts = Counter(e.get('event_id') for e in eventos if isinstance(e, dict) and _id(e.get('event_id')))
    grupos = {}
    invalidos = set()
    for e in eventos:
        if not isinstance(e, dict):
            diag['evento_malformado'] += 1
            continue
        tid = _id(e.get('task_id'))
        if tid is None:
            diag['evento_sin_tarea'] += 1
            continue
        eid, lid, cid, aid = (_id(e.get(k)) for k in ('event_id', 'list_id', 'cliente_id', 'actor_id'))
        stamp = _hora(e.get('instante'))
        cat = cats.get(lid, {})
        ok = (eid is not None and event_counts[eid] == 1 and cid in clientes_activos and aid in actores_activos
              and e.get('fuente') == 'clickup' and stamp is not None and stamp <= c
              and isinstance(e.get('estado_anterior'), str) and isinstance(e.get('estado_nuevo'), str)
              and e['estado_anterior'] in cat and e['estado_nuevo'] in cat and e['estado_anterior'] != e['estado_nuevo'])
        if not ok:
            invalidos.add(tid)
            diag['evento_no_acreditado'] += 1
            continue
        # Sólo whitelist, no descripciones/nombres/tokens de entrada.
        grupos.setdefault(tid, []).append({'event_id': eid, 'task_id': tid, 'list_id': lid, 'cliente_id': cid,
            'actor_id': aid, 'estado_anterior': e['estado_anterior'], 'estado_nuevo': e['estado_nuevo'],
            'instante': _iso(stamp), 'fuente': 'clickup'})
    out, accepted = [], []
    for t in tareas:
        if not isinstance(t, dict):
            diag['tarea_malformada'] += 1
            continue
        tid, lid, cid = (_id(t.get(k)) for k in ('task_id', 'list_id', 'cliente_id'))
        cat = cats.get(lid, {})
        if tid is None or task_counts[tid] != 1 or cid not in clientes_activos or not cat:
            diag['tarea_ambigua_fuera_ambito'] += 1
            continue
        if tid in invalidos:
            diag['cadena_evento_invalido'] += 1
            continue
        es = grupos.get(tid, [])
        # No ordenar una fuente desordenada para fingir secuencia confiable.
        times = [_hora(e['instante']) for e in es]
        if any(e['list_id'] != lid or e['cliente_id'] != cid for e in es) or any(a >= b for a, b in zip(times, times[1:])) or any(a['estado_nuevo'] != b['estado_anterior'] for a, b in zip(es, es[1:])):
            diag['cadena_incoherente'] += 1
            continue
        created = _hora(t.get('creada'))
        creator = _id(t.get('creador_id'))
        initial = t.get('estado_inicial')
        creation = (t.get('fuente_creacion') == 'clickup' and created is not None and created <= c and creator in actores_activos and initial in cat if isinstance(initial, str) else False)
        if created is not None and any(stamp < created for stamp in times):
            diag['evento_anterior_creacion'] += 1
            continue
        hist = t.get('historial')
        end = _hora(hist.get('hasta')) if isinstance(hist, dict) else None
        complete = bool(creation and isinstance(hist, dict) and hist.get('completo') is True
                        and hist.get('desde_creacion') is True and end == c
                        and (not es or es[0]['estado_anterior'] == initial))
        inrange = lambda stamp: stamp is not None and d <= stamp < h
        # Positivo observado no requiere negar entradas anteriores desconocidas.
        monthly = cat.get('planning mensual') not in {None, 'done', 'closed'} and any(e['estado_nuevo'] == 'planning mensual' and inrange(_hora(e['instante'])) for e in es)
        if creation and initial == 'planning mensual' and cat[initial] not in {'done', 'closed'} and inrange(created):
            monthly = True
        direct_stamp = None
        if complete:
            if initial in DIRECTOS and cat[initial] not in {'done', 'closed'}:
                direct_stamp = created
            else:
                seen_monthly = initial == 'planning mensual'
                for e in es:
                    if e['estado_nuevo'] == 'planning mensual':
                        seen_monthly = True
                    if e['estado_nuevo'] in DIRECTOS and cat[e['estado_nuevo']] not in {'done', 'closed'}:
                        if not seen_monthly:
                            direct_stamp = _hora(e['instante'])
                        break
        fuego = t.get('fuego')
        ftime = _hora(fuego.get('instante')) if isinstance(fuego, dict) else None
        fire_known = (isinstance(fuego, dict) and type(fuego.get('confirmado')) is bool
                      and fuego.get('fuente') == 'clasificacion_confirmada' and creation
                      and ftime is not None and direct_stamp is not None and created <= ftime <= direct_stamp)
        direct = bool(direct_stamp is not None and inrange(direct_stamp))
        metrics = {'al_planning': 1 if monthly else None,
                   'fuegos_directos': 1 if direct and fire_known and fuego['confirmado'] else None,
                   'rompen_semanal': 1 if direct and fire_known and not fuego['confirmado'] else None}
        out.append({'task_id': tid, 'list_id': lid, 'cliente_id': cid,
                    'creador_id': creator if creation else None, 'creada': _iso(created) if creation else None,
                    'creacion_observada': bool(creation), 'creada_en_rango': True if creation and inrange(created) else None,
                    'historial_desde_creacion_completo': complete, 'metricas': metrics,
                    'cobertura': 'parcial', 'cumplimiento': None})
        accepted.extend(e for e in es if inrange(_hora(e['instante'])))
    for tid in grupos:
        if task_counts[tid] != 1:
            diag['eventos_sin_identidad_tarea_unica'] += 1
    # Creator explícito, nunca actor de transición ni asignado actual.
    actors = []
    for aid in sorted({r['creador_id'] for r in out if r['creador_id']}):
        rows = [r for r in out if r['creador_id'] == aid]
        totals = {k: sum(r['metricas'][k] == 1 for r in rows) or None for k in ('al_planning', 'fuegos_directos', 'rompen_semanal')}
        actors.append({'actor_id': aid, 'atribucion': 'creador_explicito', 'creadas_observadas': sum(r['creada_en_rango'] is True for r in rows) or None,
                       'metricas': totals, 'cobertura': 'parcial', 'cumplimiento': None})
    return {'version': VERSION, 'fuente': 'eventos_clickup_observados', 'desde': _iso(d), 'hasta': _iso(h), 'corte': _iso(c),
            'cobertura': 'parcial', 'inventario_completo': False, 'cumplimiento': None,
            'eventos': accepted, 'tareas': out, 'por_creador': actors, 'diagnosticos': dict(diag)}
