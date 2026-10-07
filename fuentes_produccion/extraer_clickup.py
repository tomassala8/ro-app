#!/usr/bin/env python3
"""extraer_clickup.py · M10 Producción y M11 Horas · lectura de ClickUp con la LLAVE PROPIA. SOLO LECTURA.

Reutiliza ~/RO_HERRAMIENTAS/clickup_api/cu.py (clave del llavero «clickup_api_token», GET con reintentos).
NUNCA usa el conector de ClickUp de Claude (cupo de 2.500 llamadas/día agotado).
No toca los ficheros del panel de Mili (cu.py escribe en PANEL_OPERACIONES_…; aquí solo se importan funciones).

Escribe en fuentes_produccion/_privado/_cache/ (no se sirve):
  tareas.json   inventario accesible abierto/cerrado sin filtro temporal; asignados, estado, prioridad,
                fechas, carpeta, descripción saneada e historial de estados (bulk_time_in_status).
                Metadatos172: IDs/tipos/cobertura, sin textos/contactos/URLs/importe de customfields.
  horas.json    registros de tiempo de todo el equipo desde el 1-abr (6 meses + el mes en curso).
Uso:  python3 extraer_clickup.py [tareas|horas|todo]
"""
import json, os, re, sys, datetime as dt
from pathlib import Path

sys.path.insert(1, str(Path(__file__).resolve().parents[1]))  # C5: rutas y secretos en config.py
import config  # noqa: E402
sys.path.insert(0, str(config.HERRAMIENTAS / 'clickup_api'))
from contexto_tarea import contexto_operativo  # noqa: E402
try:
    from .metadata_clickup_172 import preservar as metadata_tarea
    from .lectura_estado_196 import sello_proveedor
except ImportError:  # También se ejecuta como script por la tubería existente.
    from metadata_clickup_172 import preservar as metadata_tarea
    from lectura_estado_196 import sello_proveedor
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
    # Sin filtro temporal: abiertas, backlog, futuras y cerradas del workspace accesible.
    #196: antes de la primera petición; jamás hora de caché/generación o bulk_history.
    inicio_estado_utc = dt.datetime.now(dt.timezone.utc).isoformat()
    completas = cu.tareas_equipo({'include_closed': 'true'})
    d = {t['id']: t for t in completas}
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
            **contexto_operativo(t),  # descripción saneada; no adjuntos ni campos privados
            **metadata_tarea(t),  #172: IDs/tipos/cobertura privados; sin nombres, links ni importes libres.
            **sello_proveedor(t, inicio_estado_utc),
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
                                     'fuente': 'API pública de ClickUp (team/task include_closed=true paginado + bulk_time_in_status) con la llave propia, cu.py',
                                     'cobertura': {'completa': False, 'sin_filtro_fecha': True, 'incluye_cerradas': True, 'subtareas': True, 'archivadas': False,
                                                  'nota': 'Workspace accesible al token, paginado completo sin filtro temporal; no confirma listas o tareas archivadas ni objetos sin acceso.'}},
                            'tareas': out})
    return len(out)


def estados_listas(listas):
    out={}
    for lid in listas:
        try:
            r=cu.get(f'/list/{lid}')
            out[str(lid)]={'ok':True,'nombre':r.get('name'),'estados':r.get('statuses') or [],'archived':r.get('archived',False)}
        except Exception:
            out[str(lid)]={'ok':False,'error':'No se pudo leer el catálogo de esta lista.'}
    ok=sum(bool(r.get('ok')) for r in out.values())
    escribe('estados_listas.json',{'leidoUTC':dt.datetime.now(dt.timezone.utc).isoformat(),'fuente':'GET /list/{id}',
        'archived_included':False,'listas':out,'cobertura':{'esperadas':len(out),'ok':ok,'error':len(out)-ok,'completa':ok==len(out)}})
    return ok


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
                                 'descripcion': (e.get('description') or '')[:120], 'etiquetas': [x.get('name') for x in e.get('tags') or []],
                                 # Mi trabajo (3-oct): huella «ro:<clave>» de las horas que nacieron en la app (la descripción se corta a 120)
                                 'marca_ro': (re.search(r'ro:[0-9a-f]{10}', e.get('description') or '') or [None])[0]})
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
        res['estados_listas'] = estados_listas(listas)
        res['tareas'] = tareas(listas)
    if orden in ('todo', 'horas'):
        res['horas'] = horas(listas)
    res['llamadas'] = cu.LLAMADAS
    print(json.dumps(res, ensure_ascii=False))


if __name__ == '__main__':
    main()
