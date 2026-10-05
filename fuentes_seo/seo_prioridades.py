"""Motor puro SEO: argumentos explícitos; sin lectura, red, reloj ni mutaciones.

Contexto: servicio_seo_confirmado bool, fuente_servicio str, ciudades_verificadas
[{ciudad, fuente}], servicios_reales [asesoria, gestoria, laboral, fiscal, contable].
Datos: rankings [{consulta,ciudad,canal,posicion,fecha,fuente,dispositivo,
ubicacion_medicion,url_o_ficha,cobertura}], paginas [{url,fecha,fuente,clics,
clics_antes,impresiones,posicion_media}], contenido {cobertura_completa:bool,
desde,hasta,fuente,publicaciones:[{url,fecha,estado}], objetivo_30_dias:int opcional}.
#1 es aspiración explícita del usuario, nunca garantía ni umbral de alarma.
"""
from datetime import date
import math
import re
import unicodedata


def normalizar(valor):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', str(valor or ''))
                            if not unicodedata.combining(c)).casefold().split())


def _fecha(v):
    try:
        return date.fromisoformat(str(v))
    except (ValueError, TypeError):
        return None


def _numero(v):
    return (isinstance(v, (int, float)) and not isinstance(v, bool)
            and math.isfinite(v))


def consultas_objetivo(contexto):
    servicios = {normalizar(s) for s in contexto.get('servicios_reales', [])}
    bases = [s for s in ('asesoria', 'gestoria') if s in servicios]
    if {'asesoria', 'gestoria'} <= servicios:
        bases.append('asesoria gestoria')
    if 'asesoria' in servicios:
        bases += ['asesoria ' + s for s in ('laboral', 'fiscal', 'contable') if s in servicios]
    ciudades = {normalizar(c.get('ciudad')): c.get('ciudad')
                for c in contexto.get('ciudades_verificadas', [])
                if isinstance(c, dict) and c.get('ciudad') and c.get('fuente')}
    return [{'consulta': base + ' ' + ciudad, 'ciudad': nombre, 'servicio': base}
            for ciudad, nombre in sorted(ciudades.items()) for base in bases]


def evaluar_seo(contexto, datos, hoy):
    """Devuelve JSON serializable determinista. Datos faltantes nunca valen cero."""
    actual = _fecha(hoy)
    if not actual:
        raise ValueError('hoy debe ser fecha ISO explícita')
    salida = {'version': 1, 'cliente_id': contexto.get('cliente_id'), 'fecha': hoy,
              'habilitado': False, 'objetivo_posicion': 1, 'garantia': False,
              'dudas': [], 'objetivos': [], 'prioridades': [], 'contenido': None}
    if contexto.get('servicio_seo_confirmado') is not True or not contexto.get('fuente_servicio'):
        salida['dudas'].append('Falta SEO contratado o autorizado y su fuente vigente; no se deduce de horas, MCR o nombres.')
    objetivos = consultas_objetivo(contexto)
    if not objetivos:
        salida['dudas'].append('Faltan ciudad verificada y servicios reales para definir consultas objetivo.')
    if salida['dudas']:
        return salida
    salida['habilitado'] = True
    for objetivo in objetivos:
        for canal in ('organico', 'maps'):
            filas = [r for r in datos.get('rankings', [])
                     if normalizar(r.get('consulta')) == normalizar(objetivo['consulta'])
                     and normalizar(r.get('ciudad')) == normalizar(objetivo['ciudad'])
                     and r.get('canal') == canal and r.get('fuente')
                     and not r.get('error') and _fecha(r.get('fecha'))
                     and _fecha(r['fecha']) <= actual]
            # No fusionar dispositivos ni ubicaciones: son mediciones distintas.
            grupos = {}
            for r in filas:
                key = (r.get('dispositivo'), r.get('ubicacion_medicion'), r.get('medicion_id'), r.get('fuente'), ' '.join(str(r.get('consulta') or '').casefold().split()))
                grupos.setdefault(key, []).append(r)
            if not grupos:
                grupos[(None, None, None, None, None)] = []
            for (dispositivo, ubicacion, medicion_id, _, variante), grupo in sorted(grupos.items(), key=lambda x: str(x[0])):
                grupo.sort(key=lambda r: r['fecha'], reverse=True)
                r = grupo[0] if grupo else {}
                pos = r.get('posicion')
                if not (_numero(pos) and pos>=1 and float(pos).is_integer()):
                    pos = None
                conflicto=bool(r) and len({f.get('posicion') if _numero(f.get('posicion')) else None for f in grupo if f['fecha']==r['fecha']})>1
                if conflicto:pos=None
                anterior = next((f for f in grupo[1:] if f['fecha'] < r['fecha']
                                 and _numero(f.get('posicion')) and f['posicion']>=1 and float(f['posicion']).is_integer()),{})
                # Una consulta coincidente no prueba el lugar/canal de la medición.
                ciudad_id = next((c.get('ciudad_id') for c in contexto.get('ciudades_verificadas', [])
                                  if isinstance(c, dict) and normalizar(c.get('ciudad')) == normalizar(objetivo['ciudad'])), None)
                ciudad_id = ciudad_id if isinstance(ciudad_id, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,120}', ciudad_id) else None
                acreditada = bool(r and ciudad_id and r.get('ciudad_id') == ciudad_id
                                  and r.get('contexto_posicion_confirmado') is True
                                  and r.get('canal_confirmado') is True
                                  and dispositivo in ('desktop', 'movil') and ubicacion
                                  and normalizar(ubicacion) == normalizar(objetivo['ciudad']))
                evidencia = {**objetivo, 'consulta_medida': r.get('consulta'), 'canal': canal, 'posicion': pos,
                    'fecha': r.get('fecha'), 'fuente': r.get('fuente'),
                    'dispositivo': dispositivo, 'ubicacion_medicion': ubicacion, 'medicion_id': medicion_id,
                    'ciudad_id': ciudad_id, 'objetivo_local_acreditado': acreditada,
                    'url_o_ficha': r.get('url_o_ficha'), 'cobertura':r.get('cobertura','desconocida'),'conflicto_lecturas':conflicto,
                    'dias_dato': (actual - _fecha(r['fecha'])).days if r else None,
                    'posicion_anterior': anterior.get('posicion'),
                    'fecha_anterior': anterior.get('fecha'),
                    'evolucion': anterior['posicion'] - pos if anterior and pos is not None else None,
                    'gap_posiciones': pos - 1 if pos is not None else None,
                    'estado': 'sin_medicion' if pos is None else ('objetivo_local_observado' if acreditada else 'posicion_1_observada_contexto_pendiente') if pos == 1 else 'por_revisar'}
                salida['objetivos'].append(evidencia)
                if pos == 1 and not acreditada:
                    salida['prioridades'].append({'tipo': 'confirmar_contexto', 'estado': 'propuesta',
                        'evidencia': evidencia, 'accion': 'Contrastar fecha, ciudad, canal y dispositivo de la posición observada antes de acreditar el objetivo local.',
                        'verificar_contexto': True, 'ejecutar_automaticamente': False})
                if pos != 1:
                    salida['prioridades'].append({'tipo': 'medir' if pos is None else 'revisar_posicion',
                        'estado': 'propuesta', 'evidencia': evidencia,
                        'accion': 'Obtener medición de la consulta objetivo.' if pos is None else
                        'Revisar resultado, intención y página/ficha antes de proponer cambios.',
                        'verificar_contexto': not dispositivo or not ubicacion,
                        'ejecutar_automaticamente': False})
    paginas = []
    for r in datos.get('paginas', []):
        fin = _fecha(r.get('fecha'))
        if not r.get('url') or not r.get('fuente') or not fin or fin > actual or r.get('error'):
            continue
        clicks, prev, imp = r.get('clics'), r.get('clics_antes'), r.get('impresiones')
        if not _numero(clicks) or clicks < 0:
            continue
        delta = clicks - prev if (r.get('periodos_comparables') is True and _numero(prev) and prev >= 0) else None
        if (delta is not None and delta < 0) or (_numero(imp) and imp > 0 and clicks == 0):
            paginas.append({'tipo': 'revisar_pagina', 'estado': 'propuesta', 'url': r['url'],
                'fecha': r['fecha'], 'fuente': r['fuente'], 'clics': clicks,
                'clics_antes': prev if delta is not None else None, 'delta_clics': delta,
                'impresiones': imp if _numero(imp) and imp >= 0 else None,
                'periodo_actual': r.get('periodo_actual'), 'periodo_anterior': r.get('periodo_anterior'),
                'posicion_media_gsc': r.get('posicion_media'),
                'accion': 'Contrastar intención, contenido y medición; revisar página existente antes de crear otra.',
                'contexto': 'GSC: posición media; no equivale a ranking puntual ni Maps.',
                'ejecutar_automaticamente': False})
    paginas.sort(key=lambda r: (r['delta_clics'] if r['delta_clics'] is not None else 0, r['url']))
    salida['prioridades'] += paginas[:10]
    contenido = datos.get('contenido') or {}
    ini, fin = _fecha(contenido.get('desde')), _fecha(contenido.get('hasta'))
    completo = (contenido.get('cobertura_completa') is True and contenido.get('fuente')
                and ini and fin and ini <= actual and fin == actual)
    publicaciones = [r for r in contenido.get('publicaciones', [])
                     if r.get('estado') == 'publicado' and r.get('url')
                     and _fecha(r.get('fecha')) and _fecha(r['fecha']) <= actual]
    # URL publicada única: revisiones/duplicados no cuentan como artículos nuevos.
    unicas = {}
    for r in publicaciones:
        if r['url'] not in unicas or r['fecha'] < unicas[r['url']]['fecha']:
            unicas[r['url']] = r
    fechas = [_fecha(r['fecha']) for r in unicas.values()]
    ultimo = max(fechas) if fechas else None
    c30 = sum(0 <= (actual-f).days < 30 for f in fechas) if completo and (actual-ini).days >= 29 else None
    c90 = sum(0 <= (actual-f).days < 90 for f in fechas) if completo and (actual-ini).days >= 89 else None
    salida['contenido'] = {'fuente': contenido.get('fuente'), 'cobertura_completa': bool(completo),
        'publicados_30_dias': c30, 'publicados_90_dias': c90,
        'ultima_publicacion_observada': ultimo.isoformat() if ultimo else None,
        'dias_desde_publicacion_observada': (actual-ultimo).days if ultimo else None,
        'nota': 'Antigüedad no implica incumplimiento; solo se cuentan ventanas con cobertura completa.'}
    objetivo = contenido.get('objetivo_30_dias')
    if (isinstance(objetivo, int) and not isinstance(objetivo, bool) and objetivo > 0
            and contenido.get('fuente_objetivo') and c30 is not None and c30 < objetivo):
        salida['prioridades'].append({'tipo': 'revisar_plan_contenido', 'estado': 'propuesta',
            'publicados': c30, 'objetivo': objetivo, 'fuente_objetivo': contenido['fuente_objetivo'],
            'accion': 'Revisar el plan de publicación acordado y las tareas existentes.',
            'ejecutar_automaticamente': False})
    return salida
