"""Agregado puro por tarea, sin inferir taxonomía ni autorización.
El caller acredita los conjuntos permitidos y revalida su scope al devolver DTO.
Duraciones observadas atribuidas por inicio; no demuestra fin del cronómetro.
"""
import datetime as dt
import math
from collections import Counter, defaultdict
from zoneinfo import ZoneInfo

ZONA = ZoneInfo('Europe/Madrid')


def _fecha(valor):
    if not isinstance(valor, str):
        return None
    try:
        x = dt.datetime.fromisoformat(valor.replace('Z', '+00:00'))
        return x if x.tzinfo and x.utcoffset() is not None else None
    except ValueError:
        return None


def resumen_tareas_observadas(entradas, tareas, *, cliente_ids, tarea_ids,
                              usuario_ids, observado_hasta, fuente):
    """60 fechas inclusivas hasta observado_hasta, no 60x24h móviles.
    `fuente` sólo admite hash y fecha lectura; ninguna ruta/texto libre al DTO.
    `max_registro_h` mide un registro; `total_h` suma entradas de la tarea.
    No envía títulos, usuarios ni exclusiones ajenas al scope del caller.
    """
    fin = _fecha(observado_hasta)
    sello = _fecha(fuente.get('leido')) if isinstance(fuente, dict) else None
    sha = fuente.get('sha256') if isinstance(fuente, dict) else None
    if not fin or not sello or sello > fin or not isinstance(sha, str) or len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
        raise ValueError('Fecha/hash de fuente no acreditados')
    for ids in (cliente_ids, tarea_ids, usuario_ids):
        if not isinstance(ids, (set, frozenset)) or any(not isinstance(x, str) or not x for x in ids):
            raise ValueError('Scope explícito requerido')
    if not isinstance(entradas, list) or not isinstance(tareas, list):
        raise ValueError('Colecciones requeridas')
    hasta = fin.astimezone(ZONA).date()
    desde = hasta - dt.timedelta(days=59)
    ids = Counter(t['id'] for t in tareas if isinstance(t, dict) and isinstance(t.get('id'), str))
    catalogo = {t['id']: t for t in tareas if isinstance(t, dict) and isinstance(t.get('id'), str) and ids[t['id']] == 1 and t['id'] in tarea_ids and isinstance(t.get('cliente_id'), str) and t['cliente_id'] in cliente_ids}
    candidatas = [e for e in entradas if isinstance(e, dict) and isinstance(e.get('task_id'), str) and e['task_id'] in catalogo and isinstance(e.get('usuario_id'), str) and e['usuario_id'] in usuario_ids]
    cuentas = Counter(e['id'] for e in candidatas if isinstance(e.get('id'), str))
    valores, grandes = defaultdict(list), defaultdict(int)
    rechazadas = 0
    for e in candidatas:
        eid, fecha, h = e.get('id'), _fecha(e.get('inicio')), e.get('horas')
        try:
            duracion_valida = isinstance(h, (int, float)) and not isinstance(h, bool) and math.isfinite(h) and h >= 0
        except (OverflowError, ValueError):
            duracion_valida = False
        if not isinstance(eid, str) or not eid or cuentas[eid] != 1 or not fecha or not duracion_valida or fecha > fin:
            rechazadas += 1
            continue
        if not desde <= fecha.astimezone(ZONA).date() <= hasta:
            continue
        tid = e['task_id']
        valores[tid].append(h)
        grandes[tid] += h > 10
    filas = []
    for tid in sorted(valores):
        hs = valores[tid]
        try:
            total = math.fsum(hs)
        except (OverflowError, ValueError) as exc:
            raise ValueError('Total observado fuera de rango') from exc
        if not math.isfinite(total):
            raise ValueError('Total observado fuera de rango')
        filas.append({'tarea_id': tid, 'cliente_id': catalogo[tid]['cliente_id'],
                      'entradas': len(hs), 'total_h': round(total, 4),
                      'max_registro_h': round(max(hs), 4),
                      'registros_mas10h': grandes[tid], 'taxonomia': 'pendiente',
                      'estado': 'observado', 'duracion_cerrada_confirmada': False})
    return {'ventana': {'desde': desde.isoformat(), 'hasta_exclusivo': (hasta + dt.timedelta(days=1)).isoformat(), 'zona': 'Europe/Madrid', 'atribucion': 'inicio'},
            'fuente': {'sha256': sha, 'leido': sello.isoformat(), 'completa': False},
            'unidad_maximo': 'registro', 'filas': filas,
            'entradas_scope_rechazadas': rechazadas,
            'cobertura': 'parcial', 'taxonomia': 'pendiente',
            'sin_entradas_no_equivale_a_cero': True}
