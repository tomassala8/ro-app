"""Lector GET inyectado: estados cerrados actuales, no eventos de venta.

No importa credenciales, no tiene CLI, no escribe archivos ni llama APIs al importar.
El llamador autoriza previamente cliente/subcuenta y controla transporte/cuota.
"""
import re
from datetime import date, datetime, timezone

ESTADOS = ('won', 'lost', 'abandoned')
ID = re.compile(r'^[A-Za-z0-9_-]{1,128}$')


def _entero(v):
    return isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 2**53 - 1


def _fecha(v, hoy):
    """Timestamp observado, nunca fecha de cierre inferida."""
    try:
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            f = datetime.fromtimestamp(v / 1000, timezone.utc)
        elif isinstance(v, str):
            f = datetime.fromisoformat(v.replace('Z', '+00:00'))
            if f.tzinfo is None:
                return None
        else:
            return None
        return f.astimezone(timezone.utc).isoformat() if f.date() <= hoy else None
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def collect(g, location_id, *, max_pages=5, hoy, incluir_privado=False, esquema='legacy'):
    """Cada estado máximo max_pages. esquema legacy: location_id; v3: locationId.

    El esquema debe coincidir con Version del transporte g.req, no cambia cabeceras.
    No filtra date/endDate: la documentación GET no acredita su semántica de cierre.
    """
    if not isinstance(location_id, str) or not ID.fullmatch(location_id):
        raise ValueError('Subcuenta debe ser un identificador autorizado, no URL.')
    if not isinstance(max_pages, int) or isinstance(max_pages, bool) or not 1 <= max_pages <= 100:
        raise ValueError('max_pages debe estar entre 1 y 100.')
    if esquema not in ('legacy', 'v3'):
        raise ValueError('Esquema de consulta no válido.')
    actual = date.fromisoformat(hoy) if isinstance(hoy, str) else hoy
    if type(actual) is not date:
        raise ValueError('hoy debe ser una fecha explícita.')
    registros = {}
    conflictos = set()
    scopes_observados = {}
    cobertura = {}
    location_key = 'location_id' if esquema == 'legacy' else 'locationId'
    for estado in ESTADOS:
        q = {location_key: location_id, 'status': estado, 'limit': 100, 'page': 1}
        vistos = set()
        ids_estado = set()
        fallos = []
        completa = False
        paginas = 0
        total = None
        for _ in range(max_pages):
            clave = (q.get('page'), q.get('startAfter'), q.get('startAfterId'))
            if clave in vistos:
                fallos.append('ciclo_paginacion'); break
            vistos.add(clave)
            try:
                r = g.req(location_id, 'GET', '/opportunities/search', **q)
            except Exception:
                fallos.append('error_transporte'); break
            paginas += 1
            if not isinstance(r, dict) or r.get('_error') is not None or r.get('error'):
                fallos.append('error_fuente'); break
            filas = r.get('opportunities')
            if not isinstance(filas, list):
                fallos.append('respuesta_invalida'); break
            nuevos = 0
            for o in filas:
                if not isinstance(o, dict) or not isinstance(o.get('id'), str) or not ID.fullmatch(o['id']):
                    fallos.append('registro_sin_identidad'); continue
                oid = o['id']
                scope = (o.get('locationId') if o.get('locationId') is not None else location_id, o.get('status'))
                if oid in scopes_observados and scopes_observados[oid] != scope:
                    conflictos.add(oid); fallos.append('identidad_con_scope_conflictivo')
                else:
                    scopes_observados[oid] = scope
                if o.get('locationId') not in (None, location_id) or o.get('status') != estado:
                    fallos.append('registro_fuera_filtro'); continue
                registro = {'id': oid, 'estado': estado, 'fecha_cierre': None,
                    'creada': _fecha(o.get('createdAt') or o.get('dateAdded'), actual),
                    'actualizada': _fecha(o.get('updatedAt'), actual),
                    'ultimo_cambio_estado_observado': _fecha(o.get('lastStatusChangeAt'), actual),
                    'ultimo_cambio_etapa_observado': _fecha(o.get('lastStageChangeAt'), actual)}
                if oid in registros and registros[oid] != registro:
                    conflictos.add(oid); fallos.append('identidad_con_datos_conflictivos')
                else:
                    registros[oid] = registro
                if oid not in ids_estado:
                    nuevos += 1
                ids_estado.add(oid)
            meta = r.get('meta', {})
            if meta is None:
                meta = {}
            if not isinstance(meta, dict):
                fallos.append('metadatos_invalidos'); break
            if 'total' in meta and not _entero(meta['total']):
                fallos.append('total_invalido'); break
            if _entero(meta.get('total')):
                if total is not None and total != meta['total']:
                    fallos.append('total_cambio_durante_lectura')
                total = meta['total']
                if len(ids_estado) > total:
                    fallos.append('total_inconsistente')
                if len(ids_estado) == total and not fallos:
                    completa = True; break
            if not filas:
                if total is None or len(ids_estado) == total:
                    completa = not fallos
                else:
                    fallos.append('total_no_alcanzado')
                break
            if not nuevos:
                fallos.append('pagina_sin_avance'); break
            cursor_id, cursor = meta.get('startAfterId'), meta.get('startAfter')
            siguiente = meta.get('nextPage')
            if cursor_id is not None or cursor is not None:
                if not isinstance(cursor_id, str) or not ID.fullmatch(cursor_id) or not _entero(cursor):
                    fallos.append('cursor_invalido'); break
                if (cursor, cursor_id) == (q.get('startAfter'), q.get('startAfterId')):
                    fallos.append('ciclo_paginacion'); break
                q.update(startAfter=cursor, startAfterId=cursor_id)
            elif meta.get('nextPageUrl') and siguiente is None:
                # Nunca obedecer una URL devuelta por el proveedor.
                fallos.append('paginacion_solo_url_no_verificada'); break
            if siguiente is not None:
                if not _entero(siguiente) or siguiente <= q['page']:
                    fallos.append('pagina_siguiente_invalida'); break
                q['page'] = siguiente
            else:
                q['page'] += 1
        else:
            fallos.append('limite_paginas')
        cobertura[estado] = {'completa': completa, 'paginas': paginas,
            'total_declarado': total, 'incidencias': sorted(set(fallos))}
    if conflictos:
        for estado in ESTADOS:
            cobertura[estado]['completa'] = False
            cobertura[estado]['incidencias'] = sorted(set(cobertura[estado]['incidencias']) | {'conflicto_identidad_entre_lecturas'})
    registros = [r for oid, r in sorted(registros.items()) if oid not in conflictos]
    conteos = {estado: sum(r['estado'] == estado for r in registros) for estado in ESTADOS}
    completa = all(c['completa'] for c in cobertura.values())
    salida = {'version': 1, 'fecha_lectura': actual.isoformat(),
        'fuente': 'GHL GET oportunidades: estados actuales', 'esquema': esquema,
        'estado_fuente': 'leida' if completa else 'parcial' if registros else 'no_disponible',
        'conteos_observados': conteos, 'cobertura': {'completa': completa, 'estados': cobertura},
        'cierres_del_periodo': None, 'ratio_leads_ventas': None,
        'limite': 'Stock observado de estados won/lost/abandoned; no acredita cuándo cerraron ni ventas cobradas. La paginación no garantiza snapshot transaccional.'}
    if incluir_privado:
        salida['privado'] = {'oportunidades': registros}
    return salida
