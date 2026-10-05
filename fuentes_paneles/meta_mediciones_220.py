"""Normalización pura de Meta; no red, llaves ni escritura.

La identidad de fuente es fijada por el productor, nunca por el payload.
Las variantes de lead pueden solaparse: prioridad explícita, no se suman.
"""
from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation
import math
import re

VERSION = '220.1'
LEADS = ('lead', 'onsite_conversion.lead_grouped', 'offsite_conversion.fb_pixel_lead', 'onsite_web_lead')
CAMPOS = {'gasto': 'spend', 'impresiones': 'impressions', 'alcance': 'reach',
          'frecuencia': 'frequency', 'clics': 'clicks', 'clics_enlace': 'inline_link_clicks'}
COHORTE = 'resultados_meta_sin_union_crm_ni_cualificacion_ro'


def numero(valor, entero=False):
    if isinstance(valor, bool) or not isinstance(valor, (int, float, str, Decimal)):
        return None
    if isinstance(valor, str) and (not valor or valor.strip() != valor):
        return None
    try:
        n = Decimal(str(valor))
        if not n.is_finite() or n < 0:
            return None
        if entero:
            return int(n) if n == n.to_integral_value() and n <= 9007199254740991 else None
        f = float(n)
        return f if math.isfinite(f) else None
    except (InvalidOperation, ValueError, OverflowError):
        return None


def leads(actions):
    if not isinstance(actions, list) or any(not isinstance(a, dict) for a in actions):
        return None, None
    for tipo in LEADS:
        encontrados = [a for a in actions if a.get('action_type') == tipo]
        if encontrados:
            valores = [numero(a.get('value'), entero=True) for a in encontrados]
            if any(v is None for v in valores) or len(set(valores)) != 1:
                return None, tipo
            return valores[0], tipo
    # Lista vacía o sólo acciones de otra clase no declara cero leads.
    return None, None


def dia(valor):
    if not isinstance(valor, str) or len(valor) != 10:
        return None
    try:
        return valor if date.fromisoformat(valor).isoformat() == valor else None
    except ValueError:
        return None


def contexto_cuenta(cuenta, moneda):
    # Sólo argumentos del productor: nunca confiar en account_id/currency del insight.
    cid = cuenta.removeprefix('act_') if isinstance(cuenta, str) else None
    cid = cid if cid and re.fullmatch(r'[1-9][0-9]{0,29}', cid) else None
    divisa = moneda if isinstance(moneda, str) and re.fullmatch(r'[A-Z]{3}', moneda) else None
    return {'cuenta_id': cid, 'moneda': divisa}


def fila(payload, fecha_lectura, nivel, cuenta=None, moneda=None):
    payload = payload if isinstance(payload, dict) else {}
    out = {k: numero(payload.get(v), entero=k not in ('gasto', 'frecuencia')) for k, v in CAMPOS.items()}
    out['leads'], tipo = leads(payload.get('actions'))
    desde, hasta = dia(payload.get('date_start')), dia(payload.get('date_stop'))
    periodo_valido = desde is not None and hasta is not None and desde <= hasta
    out['medicion'] = {'version': VERSION, 'fuente': 'meta_insights', 'fecha_lectura': fecha_lectura,
                       'desde': desde, 'hasta': hasta, 'nivel': nivel,
                       'periodo_valido': periodo_valido, 'cohorte': COHORTE,
                       'campos_observados': [k for k in (*CAMPOS, 'leads') if out[k] is not None],
                       'tipo_lead': tipo, 'cobertura': 'campos_recibidos_no_censo_leads',
                       **contexto_cuenta(cuenta, moneda)}
    if not periodo_valido:
        for k in (*CAMPOS, 'leads'):
            out[k] = None
        out['medicion']['campos_observados'] = []
    return out


def descriptor(fecha_lectura):
    return {'version': VERSION, 'origen': 'api_meta', 'observacion_campos': 'presencia_validada',
            'fecha_lectura': fecha_lectura, 'cohorte': COHORTE, 'cobertura': 'no_acreditada_completa'}


def preparar_cache(cache):
    """Copia defensiva. No revive frescura ni interpreta ceros del productor antiguo."""
    out = deepcopy(cache) if isinstance(cache, dict) else {}
    md = out.get('medicion_meta')
    actual = isinstance(md, dict) and md.get('version') == VERSION and md.get('origen') == 'api_meta' and md.get('observacion_campos') == 'presencia_validada'
    if actual:
        return out
    out['medicion_meta'] = {'version': VERSION, 'origen': 'cache_legacy', 'observacion_campos': 'no_acreditada',
                            'fecha_lectura': out.get('leido'), 'cohorte': COHORTE,
                            'cobertura': 'no_acreditada_completa', 'ceros_anteriores': 'desconocidos'}
    errs = out.get('errores')
    out['errores'] = list(errs) if isinstance(errs, list) else []
    aviso = 'Caché anterior: presencia original de campos y ceros no acreditada; ratios no certificados.'
    if aviso not in out['errores']:
        out['errores'].append(aviso)
    series_map = out.get('gasto_serie')
    if not isinstance(series_map, dict):
        out['gasto_serie'] = {}
    for series in out.get('gasto_serie', {}).values():
        if not isinstance(series, dict):
            continue
        for d, vector in list(series.items()):
            vector = vector if isinstance(vector, list) else []
            values = [numero(vector[i], entero=i != 0) if i < len(vector) else None for i in range(5)]
            series[d] = [v if v != 0 else None for v in values]
    if not isinstance(out.get('periodos'), dict):
        out['periodos'] = {}
    for period in out['periodos'].values():
        if not isinstance(period, dict):
            continue
        rows = [period.get('cuenta')]
        for nivel in ('campaign', 'adset', 'ad'):
            level = period.get(nivel)
            rows.extend(level.values() if isinstance(level, dict) else [])
        for row in rows:
            if not isinstance(row, dict):
                continue
            for k in (*CAMPOS, 'leads'):
                v = numero(row.get(k), entero=k not in ('gasto', 'frecuencia'))
                row[k] = v if v != 0 else None
            row['medicion'] = {'version': VERSION, 'fuente': 'cache_legacy', 'fecha_lectura': out.get('leido'),
                               'cohorte': COHORTE, 'cobertura': 'presencia_original_no_acreditada'}
    return out


def proyectar_cache(cache, cliente_id=None, observado_hasta=None):
    """DTO Meta puro para candidato offline. No escribe ni mezcla otras herramientas.

    Aún requiere el escáner de datos sensibles/allowlist y autorización habituales
    antes de instalarlo o entregarlo. Esta función no concede permisos.
    """
    me = preparar_cache(cache)
    series = me.get('gasto_serie') if isinstance(me.get('gasto_serie'), dict) else {}
    serie, gasto = {}, {}
    for cmp, dias in series.items():
        if not isinstance(dias, dict):
            continue
        serie[cmp], gasto[cmp] = {}, {}
        for d, vector in dias.items():
            if not isinstance(vector, list) or len(vector) != 5 or dia(d) is None:
                continue
            gasto[cmp][d] = numero(vector[0])
            serie[cmp][d] = [numero(v, entero=True) for v in vector[1:]]
    # Import local para evitar dependencia circular con el normalizador373.
    try:
        from .meta_dto_378 import proyectar as sidecar378
    except ImportError:
        try:
            from meta_dto_378 import proyectar as sidecar378
        except ModuleNotFoundError:
            from fuentes_paneles.meta_dto_378 import proyectar as sidecar378
    diario = sidecar378(me.get('mediciones_diarias_373'), me, cliente_id, observado_hasta)
    return {'mediciones_diarias_373': diario, 'cuenta': me.get('cuenta'), 'cuenta_nombre': me.get('nombre'), 'leido': me.get('leido'),
            'estado_cuenta': me.get('estado_cuenta'), 'moneda': contexto_cuenta(me.get('cuenta'), me.get('moneda'))['moneda'],
            'campanas': me.get('campaigns'),
            'conjuntos': me.get('adsets'), 'anuncios': me.get('ads'), 'serie': serie, 'gasto_serie': gasto,
            'periodos': me.get('periodos'), 'errores': me.get('errores'), 'medicion_meta': me.get('medicion_meta')}
