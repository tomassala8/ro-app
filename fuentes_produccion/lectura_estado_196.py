"""Sello conservador de lectura real; no IO ni relojes implícitos.

El extractor captura inicio UTC antes de consultar el proveedor. El comienzo
es un límite inferior por tarea del lote paginado, no una lectura atómica global.
"""
from datetime import datetime, timezone


def instante(valor):
    if not isinstance(valor, str) or not valor.strip():
        return None
    try:
        t = datetime.fromisoformat(valor.replace('Z', '+00:00'))
    except ValueError:
        return None
    if t.tzinfo is None or t.utcoffset() is None:
        return None
    return t.astimezone(timezone.utc)


def sello_proveedor(tarea, inicio_utc):
    """Sólo llamar con respuesta directa del proveedor, nunca con caché."""
    status = tarea.get('status') if isinstance(tarea, dict) else None
    estado = status.get('status') if isinstance(status, dict) else None
    t = instante(inicio_utc)
    if not isinstance(estado, str) or not estado.strip() or t is None:
        return {}
    return {'estado_fuente': 'clickup', 'estado_leido_utc': t.isoformat().replace('+00:00', 'Z')}


def sello_copia(tarea, estado_emitido, ahora_utc):
    """Propaga evidencia conservando exactamente fecha; no actualiza el reloj."""
    if not isinstance(tarea, dict) or tarea.get('estado_fuente') != 'clickup':
        return {}
    if not isinstance(estado_emitido, str) or not estado_emitido.strip() or tarea.get('estado') != estado_emitido:
        return {}
    lectura, ahora = instante(tarea.get('estado_leido_utc')), instante(ahora_utc)
    if lectura is None or ahora is None or lectura > ahora:
        return {}
    return {'estado_fuente': 'clickup', 'estado_leido_utc': lectura.isoformat().replace('+00:00', 'Z')}
