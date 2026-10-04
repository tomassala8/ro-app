"""Interpreta snapshots ya autorizados. Puro: no red, archivos, relojes ni credenciales.

La declaración version_api debe proceder del transporte servidor, nunca del JSON
remoto ni del usuario. lastStatusChangeAt sólo está contratado aquí para v3.
"""
import re
from datetime import datetime, timezone

ID = re.compile(r'^[A-Za-z0-9_-]{1,128}$')
ESTADOS = frozenset(('open', 'won', 'lost', 'abandoned'))
FUENTE = 'https://marketplace.gohighlevel.com/docs/ghl/opportunities/search-opportunity/'


def _fecha(v):
    if not isinstance(v, str) or len(v) > 80:
        return None
    try:
        f = datetime.fromisoformat(v.replace('Z', '+00:00'))
        return f.astimezone(timezone.utc) if f.tzinfo is not None else None
    except (ValueError, OverflowError):
        return None


def adaptar_snapshot_v3(registros, *, cliente_id, location_id, version_api,
                        observado_en, ahora, vigente_desde, ventana_inicio,
                        ventana_fin, cobertura_completa=False):
    """DTO privado sin identidades de contactos, importes ni texto libre.

    Ventana semiabierta [inicio, fin), fechas ISO con zona. vigente_desde es
    política explícita del llamador: no fija un umbral universal de frescura.
    La cobertura declarada no convierte un snapshot en historial de eventos.
    """
    if not all(isinstance(x, str) and ID.fullmatch(x) for x in (cliente_id, location_id)):
        raise ValueError('Ámbito servidor inválido.')
    if version_api != 'v3':
        raise ValueError('Semántica de versión no verificada.')
    obs, act, vig, ini, fin = map(_fecha, (observado_en, ahora, vigente_desde, ventana_inicio, ventana_fin))
    if any(x is None for x in (obs, act, vig, ini, fin)) or ini >= fin or vig > act or obs > act:
        raise ValueError('Fechas explícitas con zona y orden válidos requeridas.')
    if not isinstance(registros, list) or len(registros) > 10000 or type(cobertura_completa) is not bool:
        raise ValueError('Snapshot o cobertura inválidos.')
    salida = {'version': 1, 'cliente_id': cliente_id, 'location_id': location_id,
        'version_api_declarada': version_api, 'fuente_documental': FUENTE,
        'observado_en': obs.isoformat(), 'estado_fuente': 'vigente' if obs >= vig else 'desactualizada',
        'ventana_utc': {'inicio_inclusivo': ini.isoformat(), 'fin_exclusivo': fin.isoformat()},
        'cobertura': {'snapshot_completo_declarado': cobertura_completa, 'historial_completo': False},
        'oportunidades': [], 'incidencias': [], 'fecha_venta': None, 'fecha_cobro': None,
        'primer_cierre': None, 'cierres_cohorte': None, 'ratio_leads_ventas': None}
    if obs < vig:
        salida['incidencias'] = [{'codigo': 'snapshot_desactualizado'}]
        return salida
    vistos, conflicto = {}, set()
    for i, row in enumerate(registros):
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not ID.fullmatch(row['id']):
            salida['incidencias'].append({'codigo': 'identidad_invalida', 'fila': i}); continue
        if row.get('locationId') not in (None, location_id):
            salida['incidencias'].append({'codigo': 'subcuenta_no_coincide', 'fila': i}); continue
        if not isinstance(row.get('status'), str) or row['status'] not in ESTADOS:
            salida['incidencias'].append({'codigo': 'estado_desconocido', 'fila': i}); continue
        cambio = _fecha(row.get('lastStatusChangeAt'))
        if cambio is None or cambio > obs:
            salida['incidencias'].append({'codigo': 'transicion_indeterminada', 'fila': i})
            cambio = None
        fecha = cambio.isoformat() if cambio else None
        dto = {'id': row['id'], 'estado_actual_observado': row['status'],
            'ultima_transicion_estado_documentada': fecha,
            'ultima_entrada_won_observada': fecha if row['status'] == 'won' else None,
            'ultima_transicion_en_ventana': ini <= cambio < fin if cambio else None,
            'alcance': 'ultimo_estado_snapshot_sin_historial'}
        if dto['id'] in vistos:
            if vistos[dto['id']] != dto:
                conflicto.add(dto['id'])
                salida['incidencias'].append({'codigo': 'identidad_conflictiva', 'fila': i})
            else:
                salida['incidencias'].append({'codigo': 'duplicado_snapshot', 'fila': i})
        else:
            vistos[dto['id']] = dto
    salida['oportunidades'] = [v for k, v in sorted(vistos.items()) if k not in conflicto]
    return salida
