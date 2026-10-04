"""Adaptador puro para una copia GHL normalizada, previamente autorizada.

No IO ni proveedor. IDs de eventos son hashes privados; sólo `agregado` puede
publicarse tras recorte del llamador. No presume exhaustividad de la copia.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import re

from embudo_eventos import _hora, calcular


def _opaco(value):
    return (isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,160}', value) is not None
            and any(c.isalpha() for c in value))


def _cliente(value):
    return (isinstance(value, str) and re.fullmatch(r'[a-z][a-z0-9_-]{0,159}', value) is not None)


def _hash(*partes):
    return hashlib.sha256(json.dumps(partes, ensure_ascii=True, separators=(',', ':')).encode()).hexdigest()


def _epoch(value):
    # El productor normaliza dateAdded a milisegundos. Cadenas, bool, NaN,
    # infinitos, negativos o fracciones de milisegundo no son esta unidad.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        if not math.isfinite(value) or value < 0 or value != int(value):
            return None
        return datetime.fromtimestamp(value / 1000, timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None


def _unicos(rows, campo, diagnosticos, prefijo):
    """Comparación de TODA variante; no elige una entre payloads conflictivos."""
    grupos = defaultdict(dict)
    if not isinstance(rows, list):
        diagnosticos[prefijo + '_coleccion_invalida'] += 1
        return {}
    for row in rows:
        if not isinstance(row, dict) or not _opaco(row.get(campo)):
            diagnosticos[prefijo + '_identidad_invalida'] += 1
            continue
        ident = row[campo]
        try:
            firma = json.dumps(row, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False)
        except (TypeError, ValueError, OverflowError, RecursionError):
            # La variante inválida también contamina la identidad: no recuperar
            # otra fila limpia como si éste fuera un replay válido.
            grupos[ident][None] = None
            diagnosticos[prefijo + '_payload_invalido'] += 1
            continue
        if firma in grupos[ident]:
            diagnosticos[prefijo + '_replay'] += 1
        grupos[ident][firma] = row
    out = {}
    for ident, variantes in grupos.items():
        if None in variantes or len(variantes) != 1:
            diagnosticos[prefijo + '_conflicto'] += 1
        else:
            out[ident] = next(iter(variantes.values()))
    return out


def preparar(vivo, cid, sid, desde, hasta, corte):
    """Recibidos y reservas observados; nunca se completa una etapa ausente.

    desde/hasta/corte son timestamps explícitos con zona; el período inclusivo
    se aplica al agregado. Recibidos anteriores se conservan para enlazar citas
    del período sin reasignarlas a una cohorte nueva. Corte limita todo evento.
    """
    inicio, fin, observado = _hora(desde), _hora(hasta), _hora(corte)
    if not _cliente(cid) or not _opaco(sid):
        raise ValueError('Identidad de contexto inválida')
    if inicio is None or fin is None or observado is None or inicio > fin or fin > observado:
        raise ValueError('Ventana con zona y corte válidos requeridos')
    if not isinstance(vivo, dict):
        raise ValueError('Subcuenta normalizada requerida')
    diagnosticos = Counter()
    leads = _unicos(vivo.get('leads'), 'contacto', diagnosticos, 'contacto')
    citas = _unicos(vivo.get('citas'), 'id', diagnosticos, 'cita')
    conocidos, eventos = {}, []
    for ident, row in leads.items():
        if row.get('es_lead') is not True:
            diagnosticos['contacto_no_lead_explicito'] += 1
            continue
        ts = _epoch(row.get('creado'))
        if ts is None:
            diagnosticos['contacto_fecha_invalida'] += 1
            continue
        if ts > observado:
            diagnosticos['contacto_fecha_futura'] += 1
            continue
        lid = _hash(sid, ident)
        conocidos[ident] = (lid, ts)
        eventos.append({'cliente_id': cid, 'source': 'ghl', 'lead_id': lid,
                        'event_id': _hash(sid, 'recibido', ident), 'etapa': 'recibido', 'fecha': ts.isoformat()})
    for ident, row in citas.items():
        contacto = row.get('contacto')
        if not _opaco(contacto) or contacto not in conocidos:
            diagnosticos['cita_contacto_no_enlazado'] += 1
            continue
        # `creada` es dateAdded normalizada, NO la fecha `inicio` de la reunión.
        ts = _epoch(row.get('creada'))
        if ts is None:
            diagnosticos['cita_fecha_creacion_invalida'] += 1
            continue
        if ts > observado:
            diagnosticos['cita_fecha_futura'] += 1
            continue
        lid, recibido = conocidos[contacto]
        if ts < recibido:
            diagnosticos['cita_anterior_recibido'] += 1
            continue
        eventos.append({'cliente_id': cid, 'source': 'ghl', 'lead_id': lid,
                        'event_id': _hash(sid, 'cita', ident), 'etapa': 'cita', 'fecha': ts.isoformat()})
    eventos.sort(key=lambda x: (x['fecha'], x['etapa'], x['event_id']))
    cov = [{'cliente_id': cid, 'source': 'ghl', 'desde': inicio.isoformat(), 'hasta': fin.isoformat(),
            'etapas': ['recibido', 'cita'], 'completa': False}]
    if isinstance(vivo.get('errores'), list) and vivo['errores']:
        diagnosticos['fuente_reporta_errores'] += len(vivo['errores'])
    agregado = calcular(eventos, inicio.isoformat(), fin.isoformat(), observado.isoformat(), cov)
    agregado['limites'].append('Cita significa reserva históricamente creada en GHL, incluidas canceladas; no acredita cita activa, celebración, asistencia ni venta.')
    return {'version': '466.1', 'eventos': eventos,
            'diagnosticos': dict(sorted(diagnosticos.items())), 'cobertura': cov,
            'agregado': agregado}
