#!/usr/bin/env python3
"""
generar_modular.py · N5 «Modular DS» → data/modular/webs.json (SOLO LECTURA; nada se escribe en Modular).

Con clave (llavero «modulards_api_key», la guarda ~/RO_HERRAMIENTAS/modular/pegar.sh):
  lee de la API pública de Modular DS (https://api.modulards.com/api/public/v1) las webs, su disponibilidad,
  las copias, las actualizaciones pendientes y las vulnerabilidades; empareja cada web con su cliente por
  dominio (data/clientes/*.json → campo «web») y deja por web su semáforo, sus motivos y sus incidencias
  en el formato de alertas de N4 (ver FORMATO.md).
Sin clave: escribe el mismo fichero con estado «sin_conectar» y la instrucción para Tomás. No inventa nada.

Uso:
  python3 fuentes_modular/generar_modular.py                 # en vivo (si hay clave)
  python3 fuentes_modular/generar_modular.py --desde-cache   # usa fuentes_modular/_cache/volcado.json
  python3 fuentes_modular/generar_modular.py --certificados  # además, certificado de cada web emparejada (1 llamada por web)
"""
import datetime as dt
import glob
import json
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(AQUI)
SALIDA = os.path.join(APP, 'data', 'modular', 'webs.json')
CACHE = os.path.join(AQUI, '_cache', 'volcado.json')
HERR = os.path.expanduser('~/RO_HERRAMIENTAS/modular')
ENLACE_MODULAR = 'https://app.modulards.com/'
DOC_API = 'https://api.docs.modulards.com/'
SEV = {'c': 'crítica', 'h': 'alta', 'm': 'media', 'l': 'baja', 'n': 'informativa', None: 'sin dato'}
# Umbrales (se pueden mover sin tocar el resto)
DIAS_COPIA_AMBAR = 2      # planes Starter+ hacen copia cada 24 h: 2 días sin copia buena ya es raro
DIAS_COPIA_ROJO = 7
ACTUALIZ_AMBAR = 5        # 5 o más plugins/temas pendientes


def guardar(ruta, obj):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    open(ruta + '.tmp', 'w').write(json.dumps(obj, ensure_ascii=False))
    os.replace(ruta + '.tmp', ruta)


def dominio(u):
    return re.sub(r'^(https?://)?(www\.)?', '', str(u or '').strip().lower()).split('/')[0].split(':')[0]


def clientes():
    out = []
    for f in sorted(glob.glob(os.path.join(APP, 'data', 'clientes', '*.json'))):
        c = json.load(open(f))
        if c.get('activo_libro') in ('Baja',):
            continue
        out.append(c)
    return out


def sillas_web():
    """Persona principal de web por cliente (verdad única)."""
    try:
        verdad = json.load(open(os.path.join(APP, 'data', 'verdad', 'clientes.json')))['clientes']
        personas = {p['id']: p['nombre'] for p in json.load(open(os.path.join(APP, 'data', 'personas.json')))}
    except Exception:
        return {}
    out = {}
    for v in verdad:
        eq = (v.get('equipo') or {}).get('web') or []
        p = (next((x for x in eq if x.get('principal')), eq[0]) if eq else {}).get('persona_id')
        out[v['cliente_id']] = (p, personas.get(p))
    return out


def a(x):
    return (x or {}).get('attributes') or {}


def dias_desde(iso, ahora):
    if not iso:
        return None
    try:
        t = dt.datetime.fromisoformat(str(iso).replace('Z', '+00:00'))
        return (ahora - t).total_seconds() / 86400
    except Exception:
        return None


def fecha_corta(iso):
    if not iso:
        return None
    try:
        t = dt.datetime.fromisoformat(str(iso).replace('Z', '+00:00')).astimezone()
        return t.strftime('%d/%m %H:%M')
    except Exception:
        return str(iso)[:16]


def sin_conectar(motivo):
    return {
        '_meta': {'generado': dt.datetime.now().strftime('%Y-%m-%d %H:%M'), 'fuente': 'Modular DS · API pública',
                  'estado': 'sin_conectar', 'motivo': motivo,
                  'que_hacer': 'Tomás: en Modular DS, Mi perfil → API → Crear clave (solo lectura) → copiarla y ejecutar '
                               'bash ~/RO_HERRAMIENTAS/modular/pegar.sh. Después, volver a generar.',
                  'doc_api': DOC_API},
        'resumen': None, 'webs': [], 'sin_cliente': [], 'clientes_sin_modular': [], 'alertas': []}


def leer():
    if '--desde-cache' in sys.argv:
        return json.load(open(CACHE))
    sys.path.insert(0, HERR)
    import md  # noqa: E402
    try:
        d = md.volcar()
    except md.SinClave as e:
        return {'_sin_clave': str(e)}
    except md.ModularError as e:
        return {'_error': str(e)}
    if '--certificados' in sys.argv:
        d['certificados'] = {}
        for s in d.get('webs') or []:
            try:
                d['certificados'][s['id']] = a(md.certificado(s['id']).get('data'))
            except md.ModularError as e:
                d['errores']['certificado_' + str(s['id'])] = str(e)
    guardar(CACHE, d)  # crudo SOLO en fuentes_modular/_cache (no se sirve)
    return d


def construir(d):
    ahora = dt.datetime.now(dt.timezone.utc)
    cls = clientes()
    por_dom = {}
    for c in cls:
        if c.get('web'):
            por_dom[dominio(c['web'])] = c
    sil = sillas_web()
    up = {str(a(u).get('site', {}).get('id')): a(u) for u in (d.get('caidas') or [])}
    cop = {str(x.get('id')): a(x) for x in (d.get('copias') or [])}
    vul = {}
    for v in d.get('vulnerabilidades') or []:
        va = a(v)
        vul.setdefault(str((va.get('site') or {}).get('id')), []).append(va)
    act = {}
    for i in d.get('actualizaciones') or []:
        sid = str((((i.get('relationships') or {}).get('site') or {}).get('data') or {}).get('id') or '')
        if sid:
            act.setdefault(sid, []).append(a(i))
    certs = {str(k): v for k, v in (d.get('certificados') or {}).items()}

    webs, sin_cliente, alertas, vistos = [], [], [], set()
    for s in d.get('webs') or []:
        sid, sa = str(s['id']), a(s)
        dom = dominio(sa.get('display_host') or sa.get('host') or sa.get('uri'))
        c = por_dom.get(dom)
        if not c:  # subdominio o dominio raíz
            c = next((cc for dd, cc in por_dom.items() if dom.endswith('.' + dd) or dd.endswith('.' + dom)), None)
        u, b, vs, it = up.get(sid) or {}, cop.get(sid) or {}, vul.get(sid) or [], act.get(sid) or []
        motivos, inc = [], []

        def incid(regla, grav, titulo, texto, que_hacer, desde=None):
            inc.append({'id': f"modular:{regla}:{sid}", 'departamento': 'web', 'regla': regla, 'gravedad': grav,
                        'cliente_id': c['id'] if c else None, 'web': dom, 'titulo': titulo, 'texto': texto,
                        'que_hacer': que_hacer, 'fuente': 'Modular DS', 'fuente_enlace': ENLACE_MODULAR,
                        'detectado': dt.datetime.now().strftime('%Y-%m-%d %H:%M'), 'desde': desde})

        # conexión
        if not sa.get('is_connected'):
            motivos.append(('ambar', 'Desconectada de Modular: no se actualiza ni se copia'))
            incid('modular_desconectada', 'ambar', 'Web desconectada de Modular DS',
                  f"{dom}: Modular no conecta con la web ({sa.get('connection_status') or 'sin estado'}). Mientras tanto no hay copias ni actualizaciones.",
                  'Revisar el plugin Modular Connector en el WordPress y verificar la conexión en Modular.')
        # disponibilidad
        lp = u.get('last_ping') or {}
        if u and u.get('enabled') and u.get('status') == 'down':
            motivos.append(('rojo', f"Caída desde {fecha_corta(u.get('status_since'))}"))
            incid('web_caida', 'rojo', 'La web está caída', f"{dom} no responde según el monitor de Modular desde {fecha_corta(u.get('status_since'))}"
                  f" (último intento: {lp.get('status_code') or 'sin respuesta'}{', ' + lp['error'] if lp.get('error') else ''}).",
                  'Comprobar el alojamiento; si responde desde fuera y no desde RO, puede ser la IP de RO bloqueada (caso Hostinger 2-oct).',
                  u.get('status_since'))
        elif u and not u.get('enabled'):
            motivos.append(('gris', 'Monitor de disponibilidad apagado en Modular'))
        elif not u:
            motivos.append(('gris', 'Sin monitor de disponibilidad en Modular'))
        # copias
        dsc = dias_desde(b.get('last_done_at'), ahora)
        fase = (b.get('last_backup') or {}).get('phase')
        if b and not b.get('last_done_at'):
            motivos.append(('rojo', 'Nunca ha tenido una copia buena'))
            incid('copia_nunca', 'rojo', 'Web sin ninguna copia de seguridad buena', f"{dom}: Modular no tiene ninguna copia terminada de esta web.",
                  'Revisar la configuración de copias en Modular y lanzar la primera.')
        elif dsc is not None and dsc >= DIAS_COPIA_AMBAR:
            g = 'rojo' if dsc >= DIAS_COPIA_ROJO else 'ambar'
            motivos.append((g, f"Última copia buena hace {int(dsc)} días"))
            incid('copia_atrasada', g, 'Copia de seguridad atrasada', f"{dom}: la última copia buena es de hace {int(dsc)} días"
                  f"{' y la última terminó en fallo' if fase == 'failed' else ''}.", 'Mirar por qué falla la copia en Modular (espacio, conexión, tiempo).',
                  b.get('last_done_at'))
        elif fase == 'failed':
            motivos.append(('ambar', 'La última copia falló (hay una buena reciente)'))
        # vulnerabilidades
        crit = [x for x in vs if x.get('severity') in ('c', 'h')]
        if crit:
            peor = 'rojo' if any(x.get('severity') == 'c' for x in crit) else 'ambar'
            motivos.append((peor, f"{len(crit)} vulnerabilidad(es) crítica(s) o alta(s)"))
            nombres = ', '.join(sorted({(x.get('component') or {}).get('name', '?') for x in crit}))[:200]
            incid('vulnerabilidad', peor, 'Vulnerabilidad grave en la web', f"{dom}: {len(crit)} vulnerabilidad(es) {('crítica' if peor == 'rojo' else 'alta')} en {nombres}"
                  f"{'; alguna sin parche todavía' if any(x.get('unfixed') for x in crit) else ''}.",
                  'Actualizar el componente (con copia previa) o desactivarlo si no tiene parche.')
        # actualizaciones
        n_act = sa.get('updatable_items_count')
        if isinstance(n_act, int) and n_act >= ACTUALIZ_AMBAR:
            motivos.append(('ambar', f"{n_act} actualizaciones pendientes"))
            incid('actualizaciones', 'ambar', 'Actualizaciones acumuladas', f"{dom}: {n_act} plugins, temas o WordPress con actualización pendiente.",
                  'Pasar la actualización segura de Modular (hace copia y compara antes de dejarla).')
        # certificado (solo con --certificados)
        ce = certs.get(sid)
        if ce and ce.get('configured') and isinstance(ce.get('days_until_expiry'), (int, float)) and ce['days_until_expiry'] <= 14:
            g = 'rojo' if ce['days_until_expiry'] <= 3 else 'ambar'
            motivos.append((g, f"Certificado caduca en {int(ce['days_until_expiry'])} días"))
            incid('certificado', g, 'Certificado a punto de caducar', f"{dom}: el certificado caduca en {int(ce['days_until_expiry'])} días.",
                  'Renovar o revisar la renovación automática en el alojamiento.', ce.get('valid_to'))

        orden = {'rojo': 3, 'ambar': 2, 'gris': 1}
        estado = max([m[0] for m in motivos], key=lambda g: orden[g], default='verde')
        if estado == 'gris' and not [m for m in motivos if m[0] != 'gris']:
            estado = 'verde' if b or vs or sa.get('is_connected') else 'gris'
        fila = {
            'modular_id': s['id'], 'nombre': sa.get('name'), 'dominio': dom, 'url': sa.get('uri'),
            'cliente_id': c['id'] if c else None, 'cliente': c['nombre'] if c else None,
            'web_id': (sil.get(c['id']) or (None, None))[0] if c else None,
            'web_nombre': (sil.get(c['id']) or (None, None))[1] if c else None,
            'conectada': sa.get('is_connected'), 'wordpress': sa.get('core_version'), 'php': sa.get('engine_version'),
            'sincronizada': sa.get('synced_at'),
            'disponibilidad': {'monitor': u.get('enabled') if u else None, 'estado': u.get('status') if u else None,
                               'desde': u.get('status_since') if u else None, 'ultimo_ping': lp.get('at'),
                               'codigo': lp.get('status_code'), 'ms': lp.get('response_time_ms'), 'error': lp.get('error'),
                               'ultima_caida': (u.get('status_since') if u.get('status') == 'down' else None) if u else None,
                               'nota': 'Si está «up», «desde» es cuando volvió (fin de la última caída) o cuando empezó a vigilarse.'},
            'copias': {'ultima': (b.get('last_backup') or {}).get('created_at'), 'fase_ultima': fase,
                       'ultima_buena': b.get('last_done_at'), 'dias_sin_copia_buena': round(dsc, 1) if dsc is not None else None,
                       'total': b.get('total_count'), 'espacio_mb': round((b.get('storage_used') or 0) / 1048576)} if b else None,
            'actualizaciones': {'pendientes': n_act,
                                'detalle': [{'tipo': x.get('type'), 'nombre': x.get('name'), 'de': x.get('version'), 'a': x.get('new_version'),
                                             'con_vulnerabilidad': x.get('vulnerabilities_exists')} for x in it][:30]},
            'vulnerabilidades': {'total': len(vs), 'criticas': sum(1 for x in vs if x.get('severity') == 'c'),
                                 'altas': sum(1 for x in vs if x.get('severity') == 'h'),
                                 'sin_parche': sum(1 for x in vs if x.get('unfixed')),
                                 'lista': [{'gravedad': SEV.get(x.get('severity'), x.get('severity')), 'componente': (x.get('component') or {}).get('name'),
                                            'tipo': (x.get('component') or {}).get('type'), 'nombre': x.get('name'), 'sin_parche': x.get('unfixed'),
                                            'fuente': x.get('source_url')} for x in vs][:10]},
            'certificado': {'dias': ce.get('days_until_expiry'), 'caduca': ce.get('valid_to'), 'estado': ce.get('ssl_status')} if ce else None,
            'estado': estado, 'motivos': [m[1] for m in sorted(motivos, key=lambda m: -orden[m[0]])] or ['Todo en orden según Modular'],
            'incidencias': inc,
        }
        alertas.extend(inc)
        if c:
            vistos.add(c['id'])
            webs.append(fila)
        else:
            sin_cliente.append({k: fila[k] for k in ('modular_id', 'nombre', 'dominio', 'estado', 'motivos')})
    orden = {'rojo': 0, 'ambar': 1, 'gris': 2, 'verde': 3}
    webs.sort(key=lambda w: (orden.get(w['estado'], 9), w['cliente'] or ''))
    faltan = [{'cliente_id': c['id'], 'cliente': c['nombre'], 'web': c['web']} for c in cls if c.get('web') and c['id'] not in vistos]
    resumen = {'webs_modular': len(d.get('webs') or []), 'emparejadas': len(webs), 'sin_cliente': len(sin_cliente),
               'clientes_con_web_fuera_de_modular': len(faltan),
               'rojo': sum(w['estado'] == 'rojo' for w in webs), 'ambar': sum(w['estado'] == 'ambar' for w in webs),
               'verde': sum(w['estado'] == 'verde' for w in webs), 'gris': sum(w['estado'] == 'gris' for w in webs),
               'caidas_ahora': sum((w['disponibilidad'] or {}).get('estado') == 'down' for w in webs),
               'vulnerabilidades_graves': sum(w['vulnerabilidades']['criticas'] + w['vulnerabilidades']['altas'] for w in webs),
               'actualizaciones_pendientes': sum(w['actualizaciones']['pendientes'] or 0 for w in webs)}
    ri = d.get('resumen_items') or {}
    return {'_meta': {'generado': dt.datetime.now().strftime('%Y-%m-%d %H:%M'), 'leido': d.get('leido'),
                      'fuente': 'Modular DS · API pública (solo lectura)', 'estado': 'conectado', 'doc_api': DOC_API,
                      'enlace': ENLACE_MODULAR, 'errores_parciales': d.get('errores') or {},
                      'totales_modular': ri.get('meta')},
            'resumen': resumen, 'webs': webs, 'sin_cliente': sin_cliente, 'clientes_sin_modular': faltan, 'alertas': alertas}


def main():
    d = leer()
    if '_sin_clave' in d:
        out = sin_conectar('No hay clave de la API de Modular DS en este equipo.')
    elif '_error' in d:
        out = sin_conectar('La API de Modular DS respondió con error: ' + d['_error'])
    else:
        out = construir(d)
    guardar(SALIDA, out)
    r = out.get('resumen')
    print(f"data/modular/webs.json · {out['_meta']['estado']}" + (f" · {r}" if r else f" · {out['_meta']['motivo']}"))


if __name__ == '__main__':
    main()
