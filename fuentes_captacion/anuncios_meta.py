#!/usr/bin/env python3
"""anuncios_meta.py · M6 Captación · lectura de anuncios y conjuntos de Meta. SOLO LECTURA.

Completa lo que captacion.py (nivel campaña) no trae y la Torre tampoco tenía:
  · insights por ANUNCIO en tres ventanas (7 días, 7 anteriores y 30 días): gasto, impresiones, clics,
    porcentaje de clics, frecuencia y leads → creatividades cansadas (D-39), ganadoras (D-40) y autor (D-43).
  · anuncios rechazados o con problemas (effective_status DISAPPROVED / WITH_ISSUES).
  · conjuntos en aprendizaje limitado (learning_stage_info).

Reutiliza las utilidades de ~/RO_HERRAMIENTAS/captacion/captacion.py (token del llavero, ventanas, reintentos).
No escribe nada en Meta. Solo para las cuentas con pauta activa en captacion.json.
Salida: fuentes_captacion/anuncios.json (lo lee generar_captacion.py). Nunca va a data/ tal cual.
Uso:  python3 anuncios_meta.py
"""
import json
import os
import sys
import time
from datetime import timedelta
from pathlib import Path

sys.path.insert(1, str(Path(__file__).resolve().parents[1]))  # C5: rutas y secretos en config.py
import config  # noqa: E402
sys.path.insert(0, str(config.HERRAMIENTAS / 'captacion'))
import captacion as C  # noqa: E402  (solo funciones; su main() no se ejecuta)

AQUI = Path(__file__).resolve().parent
CAPTACION = AQUI.parent.parent / '20_FASE2_CAPTACION' / 'captacion.json'
SALIDA = AQUI / 'anuncios.json'

D30 = (C.AYER - timedelta(days=29), C.AYER)
VENTANAS = {'7d': C.D7, '7d_prev': C.D7P, '30d': D30}
CAMPOS = 'ad_id,ad_name,adset_name,campaign_id,campaign_name,spend,impressions,clicks,actions'


def insights_anuncio(tk, act, v, tz=None):
    """Totales por anuncio en la ventana v, con los días en HORA DE MADRID (auditoría E-15).
    Si la cuenta va en otra zona, gasto, impresiones, clics y leads salen de la lectura por horas convertida;
    la frecuencia (no se puede sumar por horas) sale de la lectura normal de la misma ventana en la zona de la cuenta."""
    def agregado(filas_dia):
        out = {}
        for f in filas_dia:
            a = out.setdefault(f.get('ad_id'), {'ad_id': f.get('ad_id'), 'ad_name': f.get('ad_name'), 'adset_name': f.get('adset_name'),
                                                'campaign_name': f.get('campaign_name'), 'campaign_id': f.get('campaign_id'),
                                                'spend': 0.0, 'impressions': 0, 'clicks': 0, 'leads': 0.0, 'frequency': None})
            a['spend'] += float(f.get('spend') or 0); a['impressions'] += int(f.get('impressions') or 0)
            a['clicks'] += int(f.get('clicks') or 0); a['leads'] += C.leads_de(f.get('actions'))
        return out
    filas, err = C.meta_insights(tk, act, tz, nivel='ad', campos=CAMPOS, desde=v[0], hasta=v[1])
    if err:
        return None, err
    ags = agregado(filas)
    # frecuencia: lectura sin desglose, una fila por anuncio
    q = {'access_token': tk, 'level': 'ad', 'limit': 500, 'fields': 'ad_id,frequency',
         'time_range': json.dumps({'since': v[0].isoformat(), 'until': v[1].isoformat()})}
    url = f'/{act}/insights'
    while url:
        r = C.meta_get(url, q)
        if '_error' in r:
            break
        for f in r.get('data', []):
            if f.get('ad_id') in ags:
                ags[f['ad_id']]['frequency'] = float(f.get('frequency') or 0)
        url = r.get('paging', {}).get('next'); q = None
    return list(ags.values()), None


def con_problemas(tk, act):
    q = {'access_token': tk, 'limit': 200, 'fields': 'name,effective_status,updated_time,ad_review_feedback',
         'filtering': json.dumps([{'field': 'effective_status', 'operator': 'IN', 'value': ['DISAPPROVED', 'WITH_ISSUES']}])}
    r = C.meta_get(f'/{act}/ads', q)
    if '_error' in r:
        return None, r.get('_msg')
    out = []
    for a in r.get('data', []):
        fb = a.get('ad_review_feedback') or {}
        motivo = '; '.join(list((fb.get('global') or {}).values())[:2]) if isinstance(fb.get('global'), dict) else None
        out.append({'id': a['id'], 'nombre': a.get('name'), 'estado': a.get('effective_status'),
                    'desde': (a.get('updated_time') or '')[:16].replace('T', ' '), 'motivo': (motivo or '')[:220] or None})
    return out, None


def conjuntos(tk, act):
    q = {'access_token': tk, 'limit': 200, 'fields': 'name,effective_status,learning_stage_info',
         'filtering': json.dumps([{'field': 'effective_status', 'operator': 'IN', 'value': ['ACTIVE']}])}
    r = C.meta_get(f'/{act}/adsets', q)
    if '_error' in r:
        return None, r.get('_msg')
    out = []
    for s in r.get('data', []):
        li = s.get('learning_stage_info') or {}
        out.append({'nombre': s.get('name'), 'aprendizaje': li.get('status')})  # LEARNING · SUCCESS · FAIL (= limitado)
    return out, None


def _previo():
    try:
        return json.loads(SALIDA.read_text())
    except Exception:
        return {}


def main():
    cap = json.load(open(CAPTACION))
    previo = _previo()
    hora_previa = previo.get('generado') or 'nunca'
    tk = C.llave('meta_token')
    if not tk:
        sys.exit('Falta meta_token en el llavero.')
    # Auditoría 35 (A5): si Meta no responde (token caducado, red caída), NO se escribe nada: se queda el último
    # anuncios.json bueno con su hora y se sale con error para que la tubería no lo selle «bien».
    try:
        cuentas_meta = C.meta_cuentas(tk)
    except SystemExit as e:
        print(f'META CAÍDO: {str(e.code)[:160]} · se queda anuncios.json de {hora_previa}', file=sys.stderr)
        sys.exit(3)
    ahora_txt = C.datetime.now().strftime('%Y-%m-%d %H:%M')
    cuentas = {}
    leidas = 0
    for c in cap['clientes']:
        if not c.get('meta_activa') or not (c.get('meta') or {}).get('cuenta_id'):
            continue
        act = c['meta']['cuenta_id']
        res = {'cuenta_id': act, 'ventanas': {}, 'errores': []}
        tz = (cuentas_meta.get(act) or {}).get('timezone_name')
        res['zona_horaria'] = tz
        res['convertida_a_madrid'] = not C.misma_hora_que_madrid(tz)
        ant = (previo.get('cuentas') or {}).get(c['id']) or {}
        ant = ant if ant.get('cuenta_id') == act else {}     # solo se reutiliza lo de la MISMA cuenta de Meta
        for k, v in VENTANAS.items():
            filas, err = insights_anuncio(tk, act, v, tz)
            if err:
                res['errores'].append(f'{k}: {err}')
                if k in (ant.get('ventanas') or {}):        # último dato bueno de esa ventana, con su hora
                    res['ventanas'][k] = ant['ventanas'][k]
                    res.setdefault('ventanas_de', {})[k] = (ant.get('ventanas_de') or {}).get(k) or hora_previa
                continue
            leidas += 1
            res['ventanas'][k] = [{
                'ad_id': f['ad_id'], 'nombre': f['ad_name'], 'conjunto': f['adset_name'], 'campana': f['campaign_name'], 'campaign_id': f.get('campaign_id'),
                'gasto': round(f['spend'], 2), 'impresiones': f['impressions'], 'clics': f['clicks'],
                'ctr': round(f['clicks'] / f['impressions'] * 100, 2) if f['impressions'] else 0.0,
                'frecuencia': round(f['frequency'], 2) if f['frequency'] is not None else None, 'leads': f['leads'],
            } for f in filas]
            time.sleep(0.25)
        res['problemas'], e1 = con_problemas(tk, act)
        res['conjuntos'], e2 = conjuntos(tk, act)
        res['errores'] += [x for x in (e1, e2) if x]
        if e1 and ant.get('problemas') is not None:
            res['problemas'] = ant['problemas']
        if e2 and ant.get('conjuntos') is not None:
            res['conjuntos'] = ant['conjuntos']
        if res['errores']:
            # la tubería («errores_de_fuente») cuenta esto como fallo de Meta en esta vuelta y avisa
            res.update({'fuente_id': 'meta_anuncios', 'hora_error': ahora_txt})
        cuentas[c['id']] = res
        print(f"  {c['nombre']}: {len(res['ventanas'].get('30d', []))} anuncios en 30 días · {len(res['problemas'] or [])} con problemas")
    if cuentas and not leidas:
        print(f'META CAÍDO: ninguna cuenta respondió · se queda anuncios.json de {hora_previa}', file=sys.stderr)
        sys.exit(3)
    out = {'generado': ahora_txt, 'datos_hasta': C.AYER.isoformat(),
           'ventanas': {k: [v[0].isoformat(), v[1].isoformat()] for k, v in VENTANAS.items()},
           'llamadas_meta': C.LLAMADAS['meta'], 'cuentas': cuentas}
    tmp = SALIDA.with_suffix('.tmp')
    tmp.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    tmp.replace(SALIDA)
    print('Listo:', SALIDA, '· llamadas a Meta (solo lectura):', C.LLAMADAS['meta'])


if __name__ == '__main__':
    main()
