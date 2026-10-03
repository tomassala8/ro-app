#!/usr/bin/env python3
"""extraer_clickup.py · M10 Producción y M11 Horas · lectura de ClickUp con la LLAVE PROPIA. SOLO LECTURA.

Reutiliza ~/RO_HERRAMIENTAS/clickup_api/cu.py (clave del llavero «clickup_api_token», GET con reintentos).
NUNCA usa el conector de ClickUp de Claude (cupo de 2.500 llamadas/día agotado).
No toca los ficheros del panel de Mili (cu.py escribe en PANEL_OPERACIONES_…; aquí solo se importan funciones).

Escribe en fuentes_produccion/_cache/ (no se sirve):
  tareas.json   tareas abiertas + cerradas o actualizadas desde el 1-jun, con asignados, estado, prioridad,
                fecha límite, carpeta y el historial de estados (bulk_time_in_status) de las que interesan.
  horas.json    registros de tiempo de todo el equipo desde el 1-abr (6 meses + el mes en curso).
Uso:  python3 extraer_clickup.py [tareas|horas|todo]
"""
import json, os, sys, datetime as dt
from pathlib import Path

sys.path.insert(1, str(Path(__file__).resolve().parents[1]))  # C5: rutas y secretos en config.py
import config  # noqa: E402
sys.path.insert(0, str(config.HERRAMIENTAS / 'clickup_api'))
import cu  # noqa: E402  (solo funciones; su main() no se ejecuta)

AQUI = Path(__file__).resolve().parent
CACHE = AQUI / '_privado' / '_cache'   # nombres de tareas con correos: fuera del escáner y de la subida
CACHE.mkdir(parents=True, exist_ok=True)
DESDE_TAREAS = dt.date(2026, 6, 1)
DESDE_HORAS = dt.date(2026, 4, 1)


def escribe(nombre, datos):
    tmp = CACHE / (nombre + '.tmp')
    tmp.write_text(json.dumps(datos, ensure_ascii=False))
    os.replace(tmp, CACHE / nombre)


def tareas(listas):
    abiertas = cu.tareas_equipo({'include_closed': 'false'})
    recientes = cu.tareas_equipo({'include_closed': 'true', 'date_updated_gt': cu.ms(DESDE_TAREAS)})
    d = {t['id']: t for t in abiertas}
    for t in recientes:
        d[t['id']] = t
    ts = list(d.values())
    tis = cu.tiempo_en_estado([t['id'] for t in ts])
    out = []
    for t in ts:
        li = listas.get(str((t.get('list') or {}).get('id')), {})
        h = tis.get(t['id']) or {}
        hist = [{'estado': x.get('status'), 'desde': (x.get('total_time') or {}).get('since'), 'minutos': (x.get('total_time') or {}).get('by_minute'),
                 'orden': x.get('orderindex')} for x in (h.get('status_history') or [])]
        cs = h.get('current_status') or {}
        out.append({
            'id': t['id'], 'nombre': t.get('name'), 'url': t.get('url'),
            'estado': (t.get('status') or {}).get('status'), 'tipo_estado': (t.get('status') or {}).get('type'),
            'estado_desde': (cs.get('total_time') or {}).get('since'),
            'prioridad': (t.get('priority') or {}).get('priority') if t.get('priority') else None,
            'vence': t.get('due_date'), 'inicio': t.get('start_date'), 'creada': t.get('date_created'), 'actualizada': t.get('date_updated'),
            'cerrada': t.get('date_done') or t.get('date_closed'), 'estimacion_ms': t.get('time_estimate'),
            'asignados': [{'id': a['id'], 'nombre': a.get('username')} for a in t.get('assignees') or []],
            'creador': (t.get('creator') or {}).get('id'),
            'etiquetas': [x.get('name') for x in t.get('tags') or []],
            'padre': t.get('parent'),
            'lista_id': str((t.get('list') or {}).get('id') or ''), 'lista': (t.get('list') or {}).get('name'),
            'carpeta_id': str((t.get('folder') or {}).get('id') or li.get('carpeta_id') or '') or None,
            'carpeta': (t.get('folder') or {}).get('name') or li.get('carpeta'),
            'espacio': li.get('espacio'),
            'historial': hist,
        })
    escribe('tareas.json', {'meta': {'generado': cu.NOW.strftime('%Y-%m-%d %H:%M'), 'desde': str(DESDE_TAREAS),
                                     'fuente': 'API pública de ClickUp (team/task + bulk_time_in_status) con la llave propia, cu.py'},
                            'tareas': out})
    return len(out)


def horas(listas):
    ms_, ex = cu.miembros()
    entradas = []
    fin = cu.HOY + dt.timedelta(days=1)
    for u in ms_ + ex:
        a = DESDE_HORAS
        while a < fin:
            b = min(a + dt.timedelta(days=31), fin)
            r = cu.get(f'/team/{cu.TEAM}/time_entries', {'start_date': cu.ms(a), 'end_date': cu.ms(b), 'assignee': u['id'], 'include_location_names': 'true'})
            for e in r.get('data', []):
                ini = dt.datetime.fromtimestamp(int(e['start']) / 1000, cu.MAD)
                dur = int(e.get('duration') or 0) / 3600000
                if dur < 0:
                    dur = (cu.NOW - ini).total_seconds() / 3600
                t = e.get('task') if isinstance(e.get('task'), dict) else {}
                loc = e.get('task_location') if isinstance(e.get('task_location'), dict) else {}
                lid = str(loc.get('list_id') or '')
                li = listas.get(lid, {})
                entradas.append({'id': str(e['id']), 'usuario_id': u['id'], 'usuario': u['nombre'], 'inicio': ini.isoformat(),
                                 'horas': round(dur, 4), 'task_id': t.get('id'), 'tarea': t.get('name'),
                                 'carpeta_id': str(loc.get('folder_id') or li.get('carpeta_id') or '') or None,
                                 'carpeta': loc.get('folder_name') or li.get('carpeta'), 'lista': loc.get('list_name') or li.get('lista'),
                                 'descripcion': (e.get('description') or '')[:120], 'etiquetas': [x.get('name') for x in e.get('tags') or []]})
            a = b
    escribe('horas.json', {'meta': {'generado': cu.NOW.strftime('%Y-%m-%d %H:%M'), 'desde': str(DESDE_HORAS),
                                    'fuente': 'API pública de ClickUp (time_entries por persona, con ubicación) con la llave propia, cu.py'},
                           'entradas': entradas})
    return len(entradas)


def main():
    orden = sys.argv[1] if len(sys.argv) > 1 else 'todo'
    _, _, listas = cu.jerarquia()
    res = {}
    if orden in ('todo', 'tareas'):
        res['tareas'] = tareas(listas)
    if orden in ('todo', 'horas'):
        res['horas'] = horas(listas)
    res['llamadas'] = cu.LLAMADAS
    print(json.dumps(res, ensure_ascii=False))


if __name__ == '__main__':
    main()
