"""Serie diaria mínima de lectura. Sin red, IO ni texto de tareas en salida."""
import datetime as dt
import math
from collections import defaultdict
from zoneinfo import ZoneInfo
from identidad_generadores_212 import identidades


def construir_diarios(cache, personas, usuarios, hoy):
    try:
        corte = dt.date.fromisoformat(hoy)
        fecha = cache['meta']['generado']
        fuente = dt.datetime.fromisoformat(fecha.replace('Z', '+00:00').replace(' ', 'T'))
        if fuente.date() > corte or not isinstance(cache.get('entradas'), list): return {}
    except (ValueError, TypeError, KeyError, AttributeError): return {}
    dias = [str(corte - dt.timedelta(days=n)) for n in range(7, 0, -1)]
    mapa = identidades(personas, usuarios)['por_usuario']
    por_pid = defaultdict(list)
    for p in personas if isinstance(personas, list) else []:
        if isinstance(p, dict): por_pid[p.get('id')].append(p)
    zonas = {}
    for pid, filas in por_pid.items():
        if len(filas) != 1 or not isinstance(pid, str): continue
        p = filas[0]
        if p.get('estado') != 'activo' or p.get('activo') is False: continue
        try: zonas[pid] = ZoneInfo(p['zona'])
        except (KeyError, ValueError, TypeError): continue
    entradas = defaultdict(list)
    for e in cache['entradas']:
        if not isinstance(e, dict): continue
        pid = mapa.get(str(e.get('usuario_id')))
        eid = e.get('id')
        if pid not in zonas or isinstance(eid, bool) or not isinstance(eid, (str, int)) or not str(eid): continue
        h = e.get('horas')
        try:
            inicio = dt.datetime.fromisoformat(e['inicio'].replace('Z', '+00:00'))
            if inicio.tzinfo is None or abs(inicio.utcoffset().total_seconds()) > 14 * 3600: continue
            dia = str(inicio.astimezone(zonas[pid]).date())
            if isinstance(h, bool) or not isinstance(h, (int, float)) or not math.isfinite(h) or h < 0 or h > 10: continue
        except (ValueError, TypeError, KeyError, AttributeError): continue
        # El ID del registro es único en el proveedor; una colisión nunca se suma ni sobrescribe.
        entradas[str(eid)].append((pid, dia, float(h), inicio.isoformat(), str(e.get('task_id') or '')))
    sumas = defaultdict(list); conflictos = set()
    for versiones in entradas.values():
        distintas = set(versiones)
        if len(distintas) != 1:
            conflictos.update((pid, dia) for pid, dia, *_ in versiones); continue
        pid, dia, h, *_ = versiones[0]
        if dia in dias: sumas[pid, dia].append(h)
    salida = {}
    for pid, zona in zonas.items():
        filas = []
        for dia in dias:
            valores = sumas.get((pid, dia), [])
            observado = bool(valores) and (pid, dia) not in conflictos
            total = math.fsum(valores) if observado else None
            if total is not None and not math.isfinite(total): total = None
            filas.append({'fecha': dia, 'horas': round(total, 2) if total is not None else None,
                          'entradas': len(valores) if total is not None else None,
                          'estado': 'observado' if total is not None else 'sin_dato'})
        salida[pid] = {'version': '238.2', 'fuente': 'ClickUp entradas', 'fecha_fuente': fecha,
                       'cobertura': 'parcial', 'zona': str(zona), 'zona_confirmada': True,
                       'desde': dias[0], 'hasta': dias[-1], 'dias': filas,
                       'corte_fecha': str(corte), 'criterio_corte': 'anterior_fecha_referencia'}
    return salida
