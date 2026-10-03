#!/usr/bin/env python3
"""M9 · Redes · genera data/redes/redes.json (solo lectura, 2-oct-2026).

Fuente: Metricool con la llave propia (~/RO_HERRAMIENTAS/metricool/mc.py, llavero metricool_token / metricool_user_id).
  · /admin/simpleProfiles            → las 25 marcas y sus redes conectadas
  · /v2/scheduler/posts              → lo programado, publicado y fallido (hace 30 días → dentro de 14)
  · /v2/analytics/posts/<red>        → rendimiento de lo publicado (Instagram, Facebook, LinkedIn), 30 días
Cliente ↔ marca: el emparejamiento de E1 (data/clientes/<id>.json → fuentes.metricool.emparejado.nombre).

Uso:
  python3 generar_redes.py --en-vivo   # llama a Metricool (≈100 llamadas de lectura) y guarda _cache/metricool.json
  python3 generar_redes.py             # rehace data/redes/redes.json desde la caché, 0 llamadas

Nunca se guarda el correo de quien creó la publicación (creatorUserMail) ni el gasto. Nada se escribe en Metricool.
"""
import datetime as dt, json, os, re, sys, glob, collections

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(AQUI)
CACHE = os.path.join(AQUI, '_cache', 'metricool.json')
SALIDA = os.path.join(APP, 'data', 'redes', 'redes.json')
HOY = dt.date(2026, 10, 2)
DESDE = HOY - dt.timedelta(days=30)
HASTA = HOY + dt.timedelta(days=13)          # los próximos 14 días, hoy incluido
HUECO_DIAS = 4                                 # 4 días seguidos sin nada = hueco (plan por defecto de RO ≈ 3-4 piezas por semana)
NO_CLIENTE = {'Ranking Online', 'Tomás'}       # marcas propias: fuera de la vista por cliente (ver _ESTADO_redes.md)
# Marcas que E1 no emparejó (Metricool «sin conectar» en la ficha) y cuyo nombre no deja duda. Revisable por Agus.
# Errores de las redes, en llano (lo que da Metricool viene en inglés)
ERRORES = [
    (r'could not set all user tags', 'Publicado, pero no se pudieron etiquetar todas las cuentas'),
    (r'no facebook page connected', 'No hay página de Facebook conectada: el cliente tiene que reconectarla'),
    (r'instagram was disconnected', 'Instagram se desconectó: el cliente tiene que reconectarlo'),
    (r'session has been invalidated|error validating access token', 'La sesión de Facebook caducó (cambio de contraseña): hay que reconectar'),
    (r'page access token', 'No se pudo obtener el permiso de la página de Facebook: reconectar'),
    (r'does not resolve to a valid user id', 'Una cuenta etiquetada no existe'),
]


def traducir(t):
    for rx, es in ERRORES:
        if re.search(rx, t or '', re.I):
            return es
    return t or ''


TEL = re.compile(r"(?<![\w.\-/])(?:\+34[\s.-]?|0034[\s.-]?)?[6789]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}(?![\w.\-/])")
CORREO = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def limpiar(t):
    """Fuera teléfonos y correos del texto de las publicaciones (la puerta de secretos no los deja ni en la caché)."""
    return CORREO.sub('[correo]', TEL.sub('[teléfono]', t or ''))


def limpiar_cache(obj):
    if isinstance(obj, dict):
        return {k: (limpiar(v) if isinstance(v, str) and k in ('texto', 'detalle') else limpiar_cache(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [limpiar_cache(x) for x in obj]
    return obj


def leer_en_vivo():
    from pathlib import Path  # 3-oct: faltaba (NameError en la vuelta completa, solo con --en-vivo)
    sys.path.insert(1, str(Path(__file__).resolve().parents[1])); import config  # C5: rutas en config.py
    sys.path.insert(0, str(config.HERRAMIENTAS / 'metricool'))
    import mc, urllib.request, urllib.parse

    def g(path, **q):
        q = {'userId': mc.llave('metricool_user_id'), **q}
        req = urllib.request.Request('https://app.metricool.com/api' + path + '?' + urllib.parse.urlencode(q),
                                     headers={'X-Mc-Auth': mc.llave('metricool_token'), 'Accept': 'application/json'})
        try:
            return json.load(urllib.request.urlopen(req, timeout=60))
        except Exception as e:  # una marca que falla no tumba al resto
            return {'_error': str(e)[:120]}

    marcas = g('/admin/simpleProfiles')
    marcas = marcas if isinstance(marcas, list) else marcas.get('data', [])
    out = {'leido': dt.datetime.now().strftime('%Y-%m-%d %H:%M'), 'marcas': []}
    for b in marcas:
        redes = [k for k in ('instagram', 'facebook', 'linkedinCompany', 'tiktok', 'youtube', 'gmb', 'twitter') if b.get(k)]
        p = g('/v2/scheduler/posts', blogId=b['id'], start=f'{DESDE}T00:00:00', end=f'{HASTA}T23:59:59', timezone='Europe/Madrid')
        posts = p.get('data', p) if isinstance(p, dict) else p
        limpios = []
        for x in posts if isinstance(posts, list) else []:
            limpios.append({
                'id': x.get('id'), 'fecha': (x.get('publicationDate') or {}).get('dateTime'),
                'texto': re.sub(r'\s+', ' ', x.get('text') or '').strip()[:160],
                'draft': bool(x.get('draft')), 'auto': bool(x.get('autoPublish')),
                'miniatura': (x.get('videoThumbnailUrl') or (x.get('media') or [None])[0]),
                'redes': [{'red': pr.get('network'), 'estado': pr.get('status'), 'detalle': (pr.get('detailedStatus') or '')[:140],
                           'url': pr.get('publicUrl')} for pr in x.get('providers', [])],
            })
        rend = {}
        for net in ('instagram', 'facebook', 'linkedin'):
            if (net == 'linkedin' and 'linkedinCompany' not in redes) or (net != 'linkedin' and net not in redes):
                continue
            r = g(f'/v2/analytics/posts/{net}', blogId=b['id'], **{'from': f'{DESDE}T00:00:00', 'to': f'{HOY}T23:59:59'})
            filas = []
            for y in (r.get('data') if isinstance(r, dict) else r) or []:
                if net == 'instagram':
                    filas.append({'fecha': (y.get('publishedAt') or {}).get('dateTime'), 'url': y.get('url'), 'tipo': y.get('type'),
                                  'texto': re.sub(r'\s+', ' ', y.get('content') or '')[:110], 'alcance': y.get('reach'),
                                  'interacciones': y.get('interactions'), 'guardados': y.get('saved'), 'compartidos': y.get('shares'),
                                  'me_gusta': y.get('likes'), 'vistas': y.get('views')})
                elif net == 'facebook':
                    filas.append({'fecha': (y.get('created') or {}).get('dateTime'), 'url': y.get('link'), 'tipo': y.get('type'),
                                  'texto': re.sub(r'\s+', ' ', y.get('text') or '')[:110], 'alcance': y.get('impressionsUnique'),
                                  'interacciones': (y.get('reactions') or 0) + (y.get('comments') or 0) + (y.get('shares') or 0) + (y.get('clicks') or 0)})
                else:
                    filas.append({'fecha': (y.get('created') or {}).get('dateTime'), 'url': y.get('url'), 'tipo': 'post',
                                  'texto': re.sub(r'\s+', ' ', y.get('title') or y.get('comment') or '')[:110], 'impresiones': y.get('impressions'),
                                  'interacciones': (y.get('clicks') or 0) + (y.get('likes') or 0) + (y.get('shares') or 0) + (y.get('comments') or 0)})
            rend[net] = filas
        out['marcas'].append({'id': b['id'], 'nombre': b.get('label'), 'redes': redes, 'posts': limpios, 'rendimiento': rend})
        print(f"{(b.get('label') or '')[:30]:30} {len(limpios):4} publicaciones", flush=True)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    out = limpiar_cache(out)
    json.dump(out, open(CACHE + '.tmp', 'w'), ensure_ascii=False)
    os.replace(CACHE + '.tmp', CACHE)
    return out


def tasa(f, red):
    """Interacción de una pieza según la regla de RO (rrss-celula l.145-152): IG y Facebook sobre alcance; LinkedIn sobre impresiones."""
    den = f.get('impresiones') if red == 'linkedin' else f.get('alcance')
    return round(100 * (f.get('interacciones') or 0) / den, 1) if den else None


UMBRAL_RED = {'instagram': 1.5, 'facebook': 1.5, 'linkedin': 3.0}


def construir(cache):
    clientes = {}
    for f in glob.glob(os.path.join(APP, 'data', 'clientes', '*.json')):
        c = json.load(open(f))
        m = (c['fuentes'].get('metricool') or {})
        emp = m.get('emparejado') or {}
        if emp.get('id'):
            clientes[('id', int(emp['id']))] = (c, False)
        elif emp.get('nombre'):
            clientes[('nombre', emp['nombre'])] = (c, False)   # E1 sin id estable: se empareja por nombre
    try:
        verdad = {x['cliente_id']: x for x in json.load(open(os.path.join(APP, 'data', 'verdad', 'clientes.json')))['clientes']}
    except Exception:
        verdad = {}
    # R12 (C-A2): quién lleva las redes lo deciden las asignaciones. Se lee el equipo que deja el paso «base»
    # (data/clientes.json, ya sin bajas), que corre antes que este; la verdad única se genera después con lo mismo.
    try:
        base_cli = {x['id']: x for x in json.load(open(os.path.join(APP, 'data', 'clientes.json')))}
        for cid, x in base_cli.items():
            if x.get('equipo') is not None:
                verdad[cid] = {**verdad.get(cid, {}), 'cliente_id': cid, 'nombre': x.get('nombre'), 'equipo': x['equipo'],
                               'account': x.get('responsable_id')}
    except Exception:
        base_cli = {}

    def principal(v, silla):
        eq = ((v or {}).get('equipo') or {}).get(silla) or []
        return (next((x for x in eq if x.get('principal')), eq[0]) if eq else {}).get('persona_id')
    personas = {p['id']: p['nombre'] for p in json.load(open(os.path.join(APP, 'data', 'personas.json')))}
    filas, fuera = [], []
    dias14 = [HOY + dt.timedelta(days=i) for i in range(14)]
    for b in cache['marcas']:
        par = clientes.get(('id', b['id'])) or clientes.get(('nombre', b['nombre']))
        if not par:
            fuera.append(b['nombre'])
            continue
        c, provisional = par
        v = verdad.get(c['id'])
        sillas = {'redes': principal(v, 'redes'), 'account': (v or {}).get('account') or principal(v, 'account')} if v else (((c['fuentes'].get('asignaciones') or {}).get('datos') or {}).get('sillas') or {})
        apoyo = [x['persona_id'] for x in ((v or {}).get('equipo') or {}).get('redes') or [] if x['persona_id'] != sillas.get('redes')]
        posts = []
        for p in b['posts']:
            if not p['fecha']:
                continue
            d = dt.date.fromisoformat(p['fecha'][:10])
            # «publicado con avisos» (etiquetas que no se pusieron) no es una fallida: salió
            estados = {('PUBLISHED' if r['estado'] == 'ERROR' and re.search('user tags', r.get('detalle') or '', re.I) else r['estado']) for r in p['redes']}
            estado = 'fallida' if 'ERROR' in estados else 'borrador' if p['draft'] else 'publicada' if estados <= {'PUBLISHED'} and estados else \
                'publicando' if 'PUBLISHING' in estados else 'programada'
            if estado == 'programada' and d < HOY:
                estado = 'no_salio'      # pendiente con fecha pasada: no salió
            posts.append({**p, 'dia': str(d), 'estado': estado})
        futuro = [p for p in posts if HOY <= dt.date.fromisoformat(p['dia']) <= HASTA and p['estado'] != 'fallida']
        cubiertos = {p['dia'] for p in futuro}
        # huecos: tramos de ≥ HUECO_DIAS días seguidos sin nada en los próximos 14
        huecos, tramo = [], []
        for d in dias14 + [None]:
            if d is not None and str(d) not in cubiertos:
                tramo.append(d)
                continue
            if len(tramo) >= HUECO_DIAS:
                huecos.append({'desde': str(tramo[0]), 'hasta': str(tramo[-1]), 'dias': len(tramo), 'en_7': (tramo[0] - HOY).days < 7})
            tramo = []
        estado14 = 'rojo' if any(h['en_7'] for h in huecos) else 'ambar' if huecos else 'verde'
        pasado = [p for p in posts if dt.date.fromisoformat(p['dia']) < HOY]
        publicadas = [p for p in pasado if p['estado'] == 'publicada']
        fallidas = [p for p in posts if p['estado'] in ('fallida', 'no_salio')]
        # 7 días naturales cerrados, sin el día en curso (misma ventana que el resto de la app)
        fallidas7 = [p for p in fallidas if 1 <= (HOY - dt.date.fromisoformat(p['dia'])).days <= 7]
        # rendimiento
        piezas = []
        for red, lista in (b.get('rendimiento') or {}).items():
            for f in lista:
                t = tasa(f, red)
                if t is None:
                    continue
                piezas.append({'red': red, 'fecha': (f.get('fecha') or '')[:10], 'url': f.get('url'), 'texto': f.get('texto'), 'tipo': f.get('tipo'),
                               'tasa': t, 'umbral': UMBRAL_RED[red], 'base': f.get('impresiones') if red == 'linkedin' else f.get('alcance'),
                               'interacciones': f.get('interacciones')})
        por_red = {}
        for red in ('instagram', 'facebook', 'linkedin'):
            ps = [p for p in piezas if p['red'] == red]
            if ps:
                inter = sum(p['interacciones'] or 0 for p in ps)
                base = sum(p['base'] or 0 for p in ps)
                por_red[red] = {'piezas': len(ps), 'tasa': round(100 * inter / base, 2) if base else None, 'umbral': UMBRAL_RED[red]}
        piezas.sort(key=lambda p: -p['tasa'])
        mt = (c['fuentes'].get('metricool') or {}).get('datos') or {}
        filas.append({
            'cliente_id': c['id'], 'cliente': c['nombre'], 'marca': b['nombre'], 'marca_id': b['id'], 'redes': b['redes'],
            'emparejamiento_provisional': provisional,
            'redes_id': sillas.get('redes'), 'redes_nombre': personas.get(sillas.get('redes')), 'redes_apoyo': apoyo,
            'metricool_conectada': True,
            'account_id': sillas.get('account'), 'account_nombre': personas.get(sillas.get('account')),
            'cubiertos_14': len(cubiertos), 'huecos': huecos, 'estado_14': estado14,
            'programadas_14': len(futuro), 'borradores': len([p for p in posts if p['estado'] == 'borrador' and dt.date.fromisoformat(p['dia']) >= HOY]),
            'publicadas_30': len(publicadas), 'pasadas_30': len(pasado),
            'en_fecha_pct': round(100 * len(publicadas) / len(pasado)) if pasado else None,
            'fallidas': [{'dia': p['dia'], 'texto': p['texto'][:90], 'redes': [{**r, 'detalle': traducir(r.get('detalle'))} for r in p['redes'] if r['estado'] != 'PUBLISHED'], 'estado': p['estado']} for p in fallidas],
            'fallidas_7': len(fallidas7),
            'por_red': por_red, 'mejor': piezas[:3], 'peor': piezas[-2:][::-1] if len(piezas) > 3 else [],
            'seguidores': {k: mt.get(k) for k in ('instagram', 'linkedin') if mt.get(k)},
            'calendario': sorted([{'dia': p['dia'], 'hora': p['fecha'][11:16], 'texto': p['texto'][:110], 'estado': p['estado'],
                                   'redes': [r['red'] for r in p['redes']], 'miniatura': p['miniatura'],
                                   'url': next((r['url'] for r in p['redes'] if r.get('url')), None)}
                                  for p in posts if dt.date.fromisoformat(p['dia']) >= HOY - dt.timedelta(days=3)], key=lambda x: (x['dia'], x['hora'])),
            'prueba': f"https://app.metricool.com/planner?blogId={b['id']}",
        })
    filas.sort(key=lambda f: ({'rojo': 0, 'ambar': 1, 'verde': 2}[f['estado_14']], -f['fallidas_7'], f['cliente']))
    # R12 (C-A2): clientes con persona de redes en asignaciones y SIN marca en Metricool. No se pintan como cubiertos ni
    # como huecos (no hay dato): van aparte, para que nadie piense que no los lleva. Metricool solo dice qué está conectado.
    en_metricool = {f['cliente_id'] for f in filas}
    sin_metricool = []
    for cid, v in sorted(verdad.items(), key=lambda kv: (kv[1].get('nombre') or kv[0])):
        eq = ((v.get('equipo') or {}).get('redes') or [])
        if cid in en_metricool or not eq or cid not in base_cli:
            continue
        pr = principal(v, 'redes')
        sin_metricool.append({'cliente_id': cid, 'cliente': v.get('nombre') or cid, 'redes_id': pr, 'redes_nombre': personas.get(pr),
                              'redes_apoyo': [x['persona_id'] for x in eq if x['persona_id'] != pr],
                              'account_id': v.get('account'), 'account_nombre': personas.get(v.get('account')),
                              'metricool_conectada': False, 'motivo': 'Sin marca conectada en Metricool: no se puede ver su calendario.'})
    por_persona = {}
    for f in filas + sin_metricool:
        for pid, papel in [(f['redes_id'], 'principal')] + [(x, 'apoyo') for x in f.get('redes_apoyo') or []]:
            if not pid:
                continue
            e = por_persona.setdefault(pid, {'principal': 0, 'apoyo': 0, 'principal_en_metricool': 0, 'apoyo_en_metricool': 0})
            e[papel] += 1
            if f['metricool_conectada']:
                e[papel + '_en_metricool'] += 1
    for pid, e in por_persona.items():
        e['texto'] = (f"Llevas {e['principal']} clientes de redes ({e['principal_en_metricool']} conectados en Metricool)"
                      + (f" y ayudas en {e['apoyo']} ({e['apoyo_en_metricool']} conectados)" if e['apoyo'] else '') + '.')
    total = len(filas)
    verdes = sum(1 for f in filas if f['estado_14'] == 'verde')
    return {
        '_meta': {'generado': dt.datetime.now().strftime('%Y-%m-%d %H:%M'), 'leido_metricool': cache['leido'],
                  'hoy': str(HOY), 'ventana': [str(HOY), str(HASTA)], 'hueco_dias': HUECO_DIAS,
                  'regla_hueco': f'Hueco = {HUECO_DIAS} días seguidos o más sin nada programado (plan por defecto de RO ≈ 3-4 piezas por semana; el plan pactado de cada cliente todavía no está cargado).',
                  'aprobaciones': 'La API de Metricool no da el estado de aprobación (pendiente / aprobado / rechazado): solo «borrador». Se cuentan los borradores con fecha futura como «por aprobar».',
                  'marcas_fuera': fuera, 'fuente': 'Metricool (llave propia, mc.py)',
                  'regla_dueno': 'Quién lleva las redes de cada cliente = asignaciones (silla redes; principal y apoyo). Metricool solo dice qué marcas están conectadas: los clientes sin marca van en «sin_metricool».'},
        'sin_metricool': sin_metricool,
        'por_persona': [{'persona_id': pid, **e} for pid, e in sorted(por_persona.items())],
        'resumen': {'clientes': total, 'verdes_14': verdes, 'pct_14': round(100 * verdes / total) if total else None,
                    'rojos': sum(1 for f in filas if f['estado_14'] == 'rojo'), 'ambar': sum(1 for f in filas if f['estado_14'] == 'ambar'),
                    'fallidas_7': sum(f['fallidas_7'] for f in filas), 'borradores': sum(f['borradores'] for f in filas),
                    'programadas_14': sum(f['programadas_14'] for f in filas)},
        'clientes': filas,
    }


if __name__ == '__main__':
    cache = leer_en_vivo() if '--en-vivo' in sys.argv else json.load(open(CACHE))
    if '--en-vivo' not in sys.argv:   # cachés antiguas: se limpian y se reescriben
        cache = limpiar_cache(cache)
        json.dump(cache, open(CACHE + '.tmp', 'w'), ensure_ascii=False); os.replace(CACHE + '.tmp', CACHE)
    datos = construir(cache)
    texto = json.dumps(datos, ensure_ascii=False)
    if re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', texto):
        sys.exit('Puerta de secretos: hay un correo en los datos de redes. No se escribe nada.')
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    open(SALIDA + '.tmp', 'w').write(texto)
    os.replace(SALIDA + '.tmp', SALIDA)
    r = datos['resumen']
    print(f"redes.json: {r['clientes']} clientes · {r['verdes_14']} con 14 días cubiertos ({r['pct_14']} %) · {r['fallidas_7']} fallidas en 7 días · fuera: {datos['_meta']['marcas_fuera']}")
