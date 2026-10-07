"""Proyección pura de recuentos independientes; no identifica una cohorte Meta→CRM."""
from math import isfinite


def dic(valor):
    return valor if isinstance(valor, dict) else {}


def conteo(valor):
    # No aceptar booleanos, fracciones, texto, negativos o infinito como personas/eventos.
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    if valor < 0 or valor > 2**53 - 1:
        return None
    return int(valor) if isfinite(valor) and valor == int(valor) else None


def suma_observada(valores, decimales=0):
    """Suma sólo si están todos presentes y son válidos; nunca vacío→cero."""
    valores = list(valores)
    if not valores or any(isinstance(v, bool) or not isinstance(v, (int, float))
                          or v < 0 or v > 1e308 or not isfinite(v) for v in valores):
        return None
    try:
        total = sum(valores)
        return round(total, decimales) if isfinite(total) else None
    except (OverflowError, ValueError):
        return None


def proyectar(cliente, crm=None, total=None, fecha_fuente=None):
    c, cr = dic(cliente), dic(crm)
    m, g = dic(c.get('meta')), dic(c.get('ghl'))
    citas = dic(dic(g.get('citas')).get('14d'))
    meta_error = bool(m.get('error'))
    crm_error = bool(cr.get('error') or g.get('error'))
    meta = None if meta_error else conteo(dic(m.get('leads')).get('7d'))
    contactos = None if crm_error else conteo(cr.get('leads_ghl_7d'))
    historia = None if crm_error else conteo(cr.get('contactos_total', total))
    estado_citas = None if crm_error else conteo(citas.get('sin_estado'))
    # Ni etiquetas sin_uso ni proximidad temporal enlazan un evento a un contacto.
    return {
        'leads_meta_7d': meta, 'leads_ghl_7d': contactos,
        'contactos_historia': historia, 'sin_estado_14d': estado_citas,
        'pct_llegan_crm': None, 'fuga': None, 'subcuenta_sin_uso': None,
        'medicion_integracion': {
            'version': '297.1', 'estado': 'sin_union_por_identidad',
            'cohorte_enlazada': False, 'conversion_medida': False,
            'fecha_fuente': fecha_fuente,
            'cobertura': 'recuentos_independientes_no_censo_ni_cualificacion',
            'meta_estado': 'error' if meta_error else 'observado' if meta is not None else 'sin_dato',
            'crm_estado': 'error' if crm_error else 'observado' if contactos is not None else 'sin_dato',
            'citas_estado': 'error' if crm_error else 'observado' if estado_citas is not None else 'sin_dato',
            'nota': 'El contador Meta y los contactos CRM son unidades independientes. '
                    'Falta unión por cliente, fuente e identidad del lead, periodo y cobertura; '
                    'no acreditan pérdidas, uso del CRM, cualificación ni ventas.',
        },
    }
