"""Resumen de filas de campaña Meta373 verificadas. Puro; no IO/red ni permisos.

No cambia campaign_diario a account: nunca alimenta el contrato account de331.
El llamador aporta contexto de cuenta acreditado e identidad autorizada explícita.
"""
from datetime import date, timedelta
from math import fsum, isfinite
from fuentes_paneles.meta_dto_378 import proyectar

VERSION = '384.1'

def _suma(rows, campo):
    if not rows or any(r.get(campo) is None for r in rows):
        return None
    try:
        value = sum(r[campo] for r in rows) if campo != 'gasto' else fsum(r[campo] for r in rows)
        return value if isfinite(value) and (campo == 'gasto' or value <= 9007199254740991) else None
    except (OverflowError, ValueError):
        return None


def resumir(sidecar, contexto, cliente_id, observado_hasta=None):
    """Sólo campos recibidos, días completos en zona de la cuenta y máximo366 días.

    Observado no equivale a censo. Un campo ausente/conflictivo invalida su suma,
    no las otras métricas observadas. No suma alcance ni frecuencia entre campañas.
    La ausencia de campañas/días no crea ceros. No calcula contactos/cualificación.
    """
    doc = proyectar(sidecar, contexto, cliente_id, observado_hasta)
    if doc is None:
        return None
    desde, hasta = (date.fromisoformat(doc['request'][k]) for k in ('desde', 'hasta'))
    if not 0 <= (hasta-desde).days <= 365:
        return None
    rows = [r for r in doc['filas_diarias'] if r['medicion']['dia_en_curso'] is False]
    dias = []
    for i in range((hasta-desde).days+1):
        d = (desde+timedelta(days=i)).isoformat()
        rs = [r for r in rows if r['dia'] == d]
        tipos = {r['medicion']['tipo_lead'] for r in rs}
        leads = _suma(rs, 'leads') if len(tipos) == 1 and None not in tipos else None
        dias.append({'dia': d, 'filas_recibidas': len(rs),
                     'leads_observados': leads, 'gasto_observado': _suma(rs, 'gasto'),
                     'impresiones_observadas': _suma(rs, 'impresiones'),
                     'clics_observados': _suma(rs, 'clics'),
                     'tipo_lead': next(iter(tipos)) if leads is not None else None})
    tipos = {d['tipo_lead'] for d in dias}
    # Una fecha sin filas/campo o tipos distintos impide el total del periodo.
    leads = _suma([{'leads': d['leads_observados']} for d in dias], 'leads') if len(tipos) == 1 and None not in tipos else None
    gasto = _suma([{'gasto': d['gasto_observado']} for d in dias], 'gasto')
    return {'version': VERSION, 'cliente_id': cliente_id, 'fecha_fuente': doc['leido_utc'],
            'periodo': {'desde': str(desde), 'hasta': str(hasta), 'zona': doc['zona']},
            'moneda': doc['moneda'], 'nivel': 'campaign_diario',
            'cobertura': 'filas_recibidas_no_censo',
            'paginas_completas': doc['cobertura']['paginas_completas'],
            'errores_tipados': list(doc['errores']), 'dias': dias,
            'leads_observados': leads, 'gasto_observado': gasto,
            'contactos_unicos': None, 'leads_calificados': None, 'ventas': None,
            'cpl_calificado': None,
            'nota': 'Eventos Meta por campañas recibidas; ausencias desconocidas. No acredita contactos únicos, cualificación ni ventas.'}
