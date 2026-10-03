#!/usr/bin/env python3
"""
generar_modular.py · N5 «Modular DS» → data/modular/webs.json y data/modular/tablero.json (SOLO LECTURA; nada se
escribe en Modular: solo peticiones GET).

Con clave (llavero «modulards_api_key», la guarda ~/RO_HERRAMIENTAS/modular/pegar.sh):
  · cada pasada (≈ 8-10 peticiones): webs, disponibilidad, copias, vulnerabilidades, actualizaciones, resumen de
    componentes y análisis de malware (listas globales, 50 por página);
  · por web, en ROTACIÓN (el contrato pide no leer /sites/{id}/uptime en bucle sobre todas): disponibilidad de 1 día,
    1 semana y 1 mes, salud de WordPress, enlaces rotos y certificado. Cada pasada lee las webs caídas y las N más
    antiguas (--detalle N; 8 por defecto, 17 en la completa): cada web se refresca cada 3-4 h. Lo leído se guarda en
    fuentes_modular/_cache/detalle.json (no se sirve) y se reutiliza en las pasadas siguientes con su hora.
  Empareja cada web con su cliente por dominio (data/clientes/*.json → «web»), cruza con el monitor propio de RO
  (data/seo/webs.json: si responde desde la IP de RO) y deja por web su semáforo, sus problemas con acción y dueño, su
  urgencia y sus incidencias en el formato de alertas de N4 (FORMATO.md).
Sin clave: escribe el mismo fichero con estado «sin_conectar» y la instrucción para Tomás. No inventa nada.

No duplica al vigía (despliegue/vigia.py mira la conexión cada 10 min con /sites/count): este generador no llama nunca
a /sites/count, y si el vigía ha visto la clave rota en los últimos 20 min, no llama a la API y reutiliza lo último
(marcado «dato_viejo»).

Uso:
  python3 fuentes_modular/generar_modular.py                 # en vivo (si hay clave), rotación de 8 webs
  python3 fuentes_modular/generar_modular.py --detalle 17    # rotación más larga (la pasada completa de las 6:00 y 14:00)
  python3 fuentes_modular/generar_modular.py --desde-cache   # sin red: fuentes_modular/_cache/volcado.json + detalle.json
  python3 fuentes_modular/generar_modular.py --certificados  # compatibilidad: igual que --detalle 17
"""
import datetime as dt
import glob
import json
import os
import re
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(AQUI)
SALIDA = os.path.join(APP, 'data', 'modular', 'webs.json')
TABLERO = os.path.join(APP, 'data', 'modular', 'tablero.json')
CACHE = os.path.join(AQUI, '_cache', 'volcado.json')
CACHE_DET = os.path.join(AQUI, '_cache', 'detalle.json')
VIGIA = os.path.join(APP, 'data', 'vigia', 'estado.json')
HERR = os.path.expanduser('~/RO_HERRAMIENTAS/modular')
ENLACE_MODULAR = 'https://app.modulards.com/'
DOC_API = 'https://api.docs.modulards.com/'
# El contrato público (openapi.json, 3-oct) no trae la dirección de cada web dentro del panel de Modular: «Abrir en
# Modular» lleva al panel y se busca la web por su nombre. El acceso de un clic al WordPress (POST /sites/{id}/login)
# es una ESCRITURA en Modular: lo da solo el servidor (fuentes_modular/acceso.py), apagado mientras la clave sea de
# solo lectura.
NOTA_ENLACE = 'El contrato de la API no da la dirección de cada web dentro de Modular: se abre el panel y se busca por su nombre.'
SEV = {'c': 'crítica', 'h': 'alta', 'm': 'media', 'l': 'baja', 'n': 'informativa', None: 'sin dato'}
# Umbrales (se pueden mover sin tocar el resto)
DIAS_COPIA_AMBAR = 2      # planes Starter+ hacen copia cada 24 h: 2 días sin copia buena ya es raro
DIAS_COPIA_ROJO = 7
ACTUALIZ_AMBAR = 5        # 5 o más plugins/temas pendientes
CERT_AMBAR = 14           # «certificado < 15 días»
CERT_ROJO = 3
ENLACES_AMBAR = 10        # enlaces rotos abiertos
DETALLE_POR_PASADA = 8
PAUSA_S = 0.55            # entre peticiones por web: < 120 por minuto (límite de la clave) con margen para el vigía


def guardar(ruta, obj):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    open(ruta + '.tmp', 'w').write(json.dumps(obj, ensure_ascii=False))
    os.replace(ruta + '.tmp', ruta)


def leer_json(ruta, defecto=None):
    try:
        return json.load(open(ruta))
    except Exception:
        return defecto


def arg(nombre, defecto=None):
    return sys.argv[sys.argv.index(nombre) + 1] if nombre in sys.argv and sys.argv.index(nombre) + 1 < len(sys.argv) else defecto


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


def sillas():
    """Persona principal de web y account por cliente (verdad única)."""
    try:
        verdad = json.load(open(os.path.join(APP, 'data', 'verdad', 'clientes.json')))['clientes']
        personas = {p['id']: p['nombre'] for p in json.load(open(os.path.join(APP, 'data', 'personas.json')))}
    except Exception:
        return {}, {}
    web, acc = {}, {}
    for v in verdad:
        eq = (v.get('equipo') or {}).get('web') or []
        p = (next((x for x in eq if x.get('principal')), eq[0]) if eq else {}).get('persona_id')
        web[v['cliente_id']] = (p, personas.get(p))
        acc[v['cliente_id']] = (v.get('account'), personas.get(v.get('account')))
    return web, acc


def jefe_web():
    """Responsable del equipo web (departamento «web» de data/departamentos.json); sin dato, Jerónimo (jefe de SEO y web)."""
    d = leer_json(os.path.join(APP, 'data', 'departamentos.json'), {}) or {}
    dep = (d.get('departamentos') or d).get('web') if isinstance(d, dict) else None
    j = (dep or {}).get('jefe') if isinstance(dep, dict) else None
    return j or 'jeronimo'


def monitor_ro():
    """Monitor propio (data/seo/webs.json): si la web responde desde la IP de RO. Por cliente y por dominio."""
    d = leer_json(os.path.join(APP, 'data', 'seo', 'webs.json'), {}) or {}
    por_cli, por_dom = {}, {}
    for w in d.get('webs') or []:
        c = w.get('comprobacion') or {}
        fila = {'responde': bool(c.get('estado') and 200 <= c['estado'] < 400), 'codigo': c.get('estado'), 'hora': c.get('hora'),
                'ms': c.get('ms'), 'cert_dias': c.get('cert_dias'), 'cert_caduca': c.get('cert_caduca'),
                'spam': len(c.get('spam') or []), 'motivo': w.get('motivo')}
        if w.get('cliente'):
            por_cli[w['cliente']] = fila
        por_dom[dominio(w.get('url'))] = fila
    return por_cli, por_dom


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
        return f"{t.day}-{['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'][t.month - 1]}, {t:%H:%M}"   # formato único de la app: «2-jul, 15:42»
    except Exception:
        return str(iso)[:16]


def sin_conectar(motivo):
    return {
        '_meta': {'generado': dt.datetime.now().strftime('%Y-%m-%d %H:%M'), 'fuente': 'Modular DS · API pública',
                  'estado': 'sin_conectar', 'motivo': motivo,
                  'que_hacer': 'Tomás: en Modular DS, Mi perfil → API → Crear clave (solo lectura) → copiarla y ejecutar '
                               'bash ~/RO_HERRAMIENTAS/modular/pegar.sh. Después, volver a generar.',
                  'doc_api': DOC_API, 'enlace': ENLACE_MODULAR},
        'resumen': None, 'webs': [], 'sin_cliente': [], 'clientes_sin_modular': [], 'alertas': []}


# ------------------------------------------------------------------ lectura
def vigia_dice_rota():
    """El vigía (cada 10 min) ya ha probado la clave: si la vio rota hace < 20 min, no se llama a la API."""
    v = leer_json(VIGIA, {}) or {}
    f = next((r for r in v.get('filas') or [] if r.get('id') == 'modular'), None)
    if not f or f.get('color') != 'rojo':
        return None
    try:
        t = dt.datetime.strptime(f.get('ultima_prueba') or '', '%Y-%m-%d %H:%M')
    except ValueError:
        return None
    if (dt.datetime.now() - t).total_seconds() > 20 * 60:
        return None
    return f.get('titular') or f.get('detalle') or 'el vigía ve la conexión con Modular caída'


def leer_detalle(md, d, n):
    """Detalle por web en rotación: las caídas y las n leídas hace más tiempo. Devuelve el caché de detalle actualizado."""
    det = leer_json(CACHE_DET, {}) or {}
    caidas = {str(a(u).get('site', {}).get('id')) for u in (d.get('caidas') or []) if a(u).get('status') == 'down'}
    ids = [str(s['id']) for s in d.get('webs') or []]
    det = {k: v for k, v in det.items() if k in ids}           # webs que ya no están en Modular, fuera
    orden = sorted(ids, key=lambda i: (i not in caidas, (det.get(i) or {}).get('leido') or ''))
    elegidas = [i for i in orden if i in caidas] + [i for i in orden if i not in caidas][:n]
    errores = {}
    for sid in elegidas:
        fila = dict(det.get(sid) or {})
        for parte, f in (('uptime', lambda: (md.uptime_web(sid) or {}).get('meta')),
                         ('salud', lambda: [a(x) for x in md.todas(f'/sites/{sid}/health', {'filter[status][]': ['critical', 'recommended']}, tope=2)]),
                         ('enlaces', lambda: md.get('/site-broken-link-issues/stats', {'filter[site]': sid})),
                         ('certificado', lambda: a((md.certificado(sid) or {}).get('data')))):
            try:
                fila[parte] = f()
            except md.SinClave:
                raise
            except md.ModularError as e:      # un 404 por rol o por plan no tumba lo demás
                fila[parte] = None
                errores[f'{parte}'] = str(e)[:160]
            time.sleep(PAUSA_S)
        fila['leido'] = dt.datetime.now().strftime('%Y-%m-%d %H:%M')
        det[sid] = fila
    guardar(CACHE_DET, det)
    return det, errores, len(elegidas)


def leer():
    if '--desde-cache' in sys.argv:
        d = leer_json(CACHE)
        if not d:
            return {'_sin_clave': 'No hay volcado guardado de Modular DS (fuentes_modular/_cache/volcado.json).'}
        d['detalle'] = leer_json(CACHE_DET, {}) or {}
        d['_desde_cache'] = True
        return d
    rota = vigia_dice_rota()
    if rota:
        d = leer_json(CACHE)
        if not d:
            return {'_error': f'el vigía ve la conexión rota ({rota}) y no hay copia guardada'}
        d['detalle'] = leer_json(CACHE_DET, {}) or {}
        d['_dato_viejo'] = f'No se ha llamado a Modular: el vigía ve la conexión rota ({rota}). Es la última lectura buena.'
        return d
    sys.path.insert(0, HERR)
    import md  # noqa: E402
    try:
        d = md.volcar()
        try:   # análisis de malware: lista global, la más reciente primero (1-4 peticiones)
            d['malware'] = md.todas('/site-scans', {'sort': '-created_at'}, tope=4)
        except md.ModularError as e:
            d['malware'] = None
            d['errores']['malware'] = str(e)[:160]
        n = int(arg('--detalle', 17 if '--certificados' in sys.argv else DETALLE_POR_PASADA))
        det, err, leidas = leer_detalle(md, d, n)
        d['errores'].update({f'detalle_{k}': v for k, v in err.items()})
        d['detalle_leidas'] = leidas
    except md.SinClave as e:
        return {'_sin_clave': str(e)}
    except md.ModularError as e:
        return {'_error': str(e)}
    guardar(CACHE, {k: v for k, v in d.items() if k != 'detalle'})   # crudo SOLO en fuentes_modular/_cache (no se sirve)
    d['detalle'] = det
    return d


# ------------------------------------------------------------------ construcción
ORDEN_EST = {'rojo': 3, 'ambar': 2, 'gris': 1}


def construir(d):
    ahora = dt.datetime.now(dt.timezone.utc)
    cls = clientes()
    nombre_cli = {c['id']: c['nombre'] for c in cls}
    por_dom = {}
    for c in cls:
        if c.get('web'):
            por_dom[dominio(c['web'])] = c
    sil_web, sil_acc = sillas()
    jefe = jefe_web()
    try:
        personas = {p['id']: p['nombre'] for p in json.load(open(os.path.join(APP, 'data', 'personas.json')))}
    except Exception:
        personas = {}
    mon_cli, mon_dom = monitor_ro()
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
    mal = {}
    for s in d.get('malware') or []:             # la más reciente primero: se queda la primera de cada web
        sa_ = a(s)
        mal.setdefault(str(sa_.get('site_id')), sa_)
    det = {str(k): v for k, v in (d.get('detalle') or {}).items()}
    for k, v in (d.get('certificados') or {}).items():      # volcados antiguos (--certificados de la primera versión)
        det.setdefault(str(k), {}).setdefault('certificado', v)

    webs, sin_cliente, alertas, vistos = [], [], [], set()
    for s in d.get('webs') or []:
        sid, sa = str(s['id']), a(s)
        dom = dominio(sa.get('display_host') or sa.get('host') or sa.get('uri'))
        c = por_dom.get(dom)
        if not c:  # subdominio o dominio raíz
            c = next((cc for dd, cc in por_dom.items() if dom.endswith('.' + dd) or dd.endswith('.' + dom)), None)
        u, b, vs, it = up.get(sid) or {}, cop.get(sid) or {}, vul.get(sid) or [], act.get(sid) or []
        dw = det.get(sid) or {}
        mon = (mon_cli.get(c['id']) if c else None) or mon_dom.get(dom) or (mon_cli.get('_ro') if dom == 'rankingonline.com' else None)
        web_id, web_nombre = (sil_web.get(c['id']) or (None, None)) if c else (None, None)
        acc_id, acc_nombre = (sil_acc.get(c['id']) or (None, None)) if c else (None, None)
        dueno_id = web_id or jefe
        dueno = personas.get(dueno_id) or dueno_id
        motivos, inc, problemas = [], [], []

        def incid(regla, grav, titulo, texto, que_hacer, desde=None):
            inc.append({'id': f"modular:{regla}:{sid}", 'departamento': 'web', 'regla': regla, 'gravedad': grav,
                        'cliente_id': c['id'] if c else None, 'web': dom, 'titulo': titulo, 'texto': texto,
                        'que_hacer': que_hacer, 'fuente': 'Modular DS', 'fuente_enlace': ENLACE_MODULAR,
                        'detectado': dt.datetime.now().strftime('%Y-%m-%d %H:%M'), 'desde': desde,
                        'dueno_id': dueno_id})

        def prob(clave, grav, titulo, detalle, accion, urg):
            problemas.append({'clave': clave, 'gravedad': grav, 'titulo': titulo, 'detalle': detalle, 'accion': accion,
                              'dueno_id': dueno_id, 'dueno': dueno, 'urgencia': urg})

        # conexión
        if not sa.get('is_connected'):
            motivos.append(('ambar', 'Desconectada de Modular: no se actualiza ni se copia'))
            t = f"{dom}: Modular no conecta con la web ({sa.get('connection_status') or 'sin estado'}). Mientras tanto no hay copias ni actualizaciones."
            q = 'Revisar el plugin Modular Connector en el WordPress y verificar la conexión en Modular.'
            incid('modular_desconectada', 'ambar', 'Web desconectada de Modular DS', t, q)
            prob('desconectada', 'ambar', 'Desconectada de Modular', t, q, 150)
        # disponibilidad (con el monitor propio de RO: dos puntos de vista)
        lp = u.get('last_ping') or {}
        err = lp.get('error')
        err_txt = (err.get('message') or err.get('code') or 'error') if isinstance(err, dict) else (str(err) if err else '')
        if u and u.get('enabled') and u.get('status') == 'down':
            de_verdad = not (mon and mon.get('responde'))
            ultimo = f"último intento: {lp.get('status_code') or 'sin respuesta'}{', ' + err_txt if err_txt else ''}"
            if de_verdad:
                motivos.append(('rojo', f"Caída desde {fecha_corta(u.get('status_since'))}"))
                t = (f"{dom} no responde según el monitor de Modular desde {fecha_corta(u.get('status_since'))} ({ultimo})"
                     f"{' y tampoco desde la IP de RO' if mon else ''}.")
                q = 'Comprobar el alojamiento y el dominio ya; avisar al account si la caída sigue al cabo de 1 h.'
                incid('web_caida', 'rojo', 'La web está caída', t, q, u.get('status_since'))
                prob('caida', 'rojo', 'Caída', t, q, 1000)
            else:
                redir = lp.get('status_code') in (301, 302, 307, 308)
                motivos.append(('ambar', 'Modular la da por caída, pero responde desde la IP de RO'))
                t = (f"{dom}: Modular la da por caída desde {fecha_corta(u.get('status_since'))} ({ultimo}), pero desde la IP de RO responde "
                     f"{mon.get('codigo')}. {'Modular recibe una redirección y solo acepta respuestas 2xx: el monitor apunta a una dirección vieja.' if redir else 'Puede ser un bloqueo a Modular o un fallo intermitente.'}")
                q = ('Poner en Modular la dirección final de la web (la que no redirige) en la vigilancia de disponibilidad.' if redir
                     else 'Mirar en Modular el último intento y el alojamiento; si se repite, revisar el cortafuegos.')
                incid('web_caida', 'ambar', 'Modular la da por caída (desde RO responde)', t, q, u.get('status_since'))
                prob('caida_fuera', 'ambar', 'Caída solo desde fuera', t, q, 600)
        elif u and not u.get('enabled'):
            motivos.append(('gris', 'Monitor de disponibilidad apagado en Modular'))
        elif not u:
            motivos.append(('gris', 'Sin monitor de disponibilidad en Modular'))
        # copias
        dsc = dias_desde(b.get('last_done_at'), ahora)
        fase = (b.get('last_backup') or {}).get('phase')
        if b and not b.get('last_done_at'):
            motivos.append(('rojo', 'Nunca ha tenido una copia buena'))
            t = f"{dom}: Modular no tiene ninguna copia terminada de esta web."
            q = 'Configurar las copias en Modular y lanzar la primera (antes de tocar nada en la web).'
            incid('copia_nunca', 'rojo', 'Web sin ninguna copia de seguridad buena', t, q)
            prob('sin_copia', 'rojo', 'Sin ninguna copia buena', t, q, 800)
        elif dsc is not None and dsc >= DIAS_COPIA_AMBAR:
            g = 'rojo' if dsc >= DIAS_COPIA_ROJO else 'ambar'
            motivos.append((g, f"Última copia buena hace {int(dsc)} días"))
            t = f"{dom}: la última copia buena es de hace {int(dsc)} días{' y la última terminó en fallo' if fase == 'failed' else ''}."
            q = 'Mirar por qué no se copia en Modular (programación, espacio, conexión) y lanzar una copia.'
            incid('copia_atrasada', g, 'Copia de seguridad atrasada', t, q, b.get('last_done_at'))
            prob('copia_atrasada', g, f'Copia de hace {int(dsc)} días', t, q, 500 + min(int(dsc), 60))
        elif fase == 'failed':
            motivos.append(('ambar', 'La última copia falló (hay una buena reciente)'))
            prob('copia_fallida', 'ambar', 'La última copia falló', f'{dom}: la última copia falló; hay una buena de hace menos de {DIAS_COPIA_AMBAR} días.',
                 'Mirar el motivo del fallo en Modular antes de la siguiente.', 120)
        # vulnerabilidades
        crit = [x for x in vs if x.get('severity') in ('c', 'h')]
        if crit:
            peor = 'rojo' if any(x.get('severity') == 'c' for x in crit) else 'ambar'
            motivos.append((peor, f"{len(crit)} vulnerabilidad(es) crítica(s) o alta(s)"))
            nombres = ', '.join(sorted({(x.get('component') or {}).get('name', '?') for x in crit}))[:200]
            n_c = sum(1 for x in crit if x.get('severity') == 'c')
            t = (f"{dom}: {len(crit)} vulnerabilidad(es) {'crítica(s) o alta(s)' if peor == 'rojo' else 'alta(s)'} en {nombres}"
                 f"{'; alguna sin parche todavía' if any(x.get('unfixed') for x in crit) else ''}.")
            q = 'Actualizar el componente con la actualización segura de Modular (hace copia antes) o desactivarlo si no tiene parche.'
            incid('vulnerabilidad', peor, 'Vulnerabilidad grave en la web', t, q)
            prob('vulnerabilidad', peor, f"{n_c} crítica(s) · {len(crit) - n_c} alta(s)" if n_c else f'{len(crit)} vulnerabilidad(es) alta(s)', t, q,
                 (300 + n_c * 10) if peor == 'rojo' else 100 + len(crit))
        # actualizaciones
        n_act = sa.get('updatable_items_count')
        if isinstance(n_act, int) and n_act >= ACTUALIZ_AMBAR:
            motivos.append(('ambar', f"{n_act} actualizaciones pendientes"))
            t = f"{dom}: {n_act} plugins, temas o WordPress con actualización pendiente."
            q = 'Pasar la actualización segura de Modular (hace copia y compara antes de dejarla).'
            incid('actualizaciones', 'ambar', 'Actualizaciones acumuladas', t, q)
            prob('actualizaciones', 'ambar', f'{n_act} actualizaciones', t, q, 50 + n_act)
        elif isinstance(n_act, int) and n_act:
            prob('actualizaciones', 'verde', f'{n_act} actualización(es)', f'{dom}: {n_act} pendiente(s), por debajo del aviso ({ACTUALIZ_AMBAR}).',
                 'Pasarlas en la ronda semanal de actualizaciones.', n_act)
        # certificado (del detalle; si Modular no lo vigila, el del monitor de RO)
        ce = dw.get('certificado') or {}
        cert = None
        if ce.get('configured') and isinstance(ce.get('days_until_expiry'), (int, float)):
            cert = {'dias': int(ce['days_until_expiry']), 'caduca': ce.get('valid_to'), 'estado': ce.get('ssl_status'),
                    'emisor': ce.get('issuer'), 'fuente': 'Modular DS'}
        elif mon and isinstance(mon.get('cert_dias'), int):
            cert = {'dias': mon['cert_dias'], 'caduca': mon.get('cert_caduca'), 'estado': None, 'emisor': None,
                    'fuente': 'Monitor de RO', 'nota': 'Modular no vigila el certificado de esta web: dato del monitor de RO.'}
        if cert and cert['dias'] <= CERT_AMBAR:
            g = 'rojo' if cert['dias'] <= CERT_ROJO else 'ambar'
            motivos.append((g, f"Certificado caduca en {cert['dias']} días"))
            t = f"{dom}: el certificado caduca en {cert['dias']} días ({str(cert.get('caduca') or '')[:10]})."
            q = 'Renovar o revisar la renovación automática en el alojamiento.'
            if cert['fuente'] == 'Modular DS':     # el del monitor de RO ya lo avisa su propia regla (web_certificado)
                incid('certificado', g, 'Certificado a punto de caducar', t, q, cert.get('caduca'))
            prob('certificado', g, f"Certificado: {cert['dias']} días", t, q, 200 + (CERT_AMBAR - cert['dias']) * 5)
        # salud de WordPress (del detalle)
        sal = dw.get('salud')
        salud = None
        if isinstance(sal, list):
            cr = [x for x in sal if x.get('effective_status') == 'critical']
            rec = [x for x in sal if x.get('effective_status') == 'recommended']
            salud = {'criticas': len(cr), 'recomendadas': len(rec),
                     'lista': [{'categoria': {'performance': 'rendimiento', 'security': 'seguridad'}.get(x.get('category'), x.get('category')),
                                'etiqueta': x.get('label'), 'estado': {'critical': 'crítica', 'recommended': 'recomendada'}.get(x.get('effective_status'))}
                               for x in (cr + rec)][:8]}
            if cr:
                prob('salud', 'ambar', f'Salud de WordPress: {len(cr)} crítica(s)', f"{dom}: {', '.join(x.get('label') or '?' for x in cr[:3])}.",
                     'Revisar la salud del sitio en Modular (o en Herramientas › Salud del sitio del WordPress).', 90 + len(cr))
        # malware
        m = mal.get(sid)
        malware = None
        if m:
            amen = (m.get('files_infected') or 0) + (m.get('files_malicious') or 0) + (m.get('db_threats_detected') or 0)
            malware = {'veredicto': {'clean': 'limpia', 'threats_found': 'amenazas', 'failed': 'falló', 'quota_exceeded': 'sin cupo',
                                     'pending': 'en curso', 'in_progress': 'en curso'}.get(m.get('verdict'), m.get('verdict')),
                       'fecha': m.get('created_at'), 'amenazas': amen, 'sospechosos': m.get('files_suspicious') or 0}
            if m.get('verdict') == 'threats_found' or m.get('has_threats'):
                motivos.append(('rojo', f'Malware: {amen} amenaza(s)'))
                prob('malware', 'rojo', f'Malware: {amen} amenaza(s)', f"{dom}: el último análisis de Modular ({fecha_corta(m.get('created_at'))}) encontró {amen} amenaza(s).",
                     'Limpiar con copia previa, cambiar los accesos del WordPress y pedir revisión en Search Console.', 900)
        # enlaces rotos (del detalle)
        en = dw.get('enlaces')
        enlaces = None
        if isinstance(en, dict):
            cat = en.get('by_category') or {}
            ls = en.get('last_scan') or {}
            enlaces = {'abiertos': en.get('total_issues'), 'rotos': cat.get('broken_link'), 'contenido_mixto': cat.get('mixed_content'),
                       'ultimo_escaneo': ls.get('finished_at') or ls.get('started_at'), 'estado_escaneo': ls.get('status')}
            if (en.get('total_issues') or 0) >= ENLACES_AMBAR:
                prob('enlaces', 'ambar', f"{en['total_issues']} enlaces rotos", f"{dom}: {cat.get('broken_link') or 0} enlaces rotos y {cat.get('mixed_content') or 0} recursos sin https.",
                     'Corregir o quitar los enlaces desde la lista de Modular (los internos primero).', 40)
        # disponibilidad por ventanas (del detalle)
        upd = dw.get('uptime') or {}
        av = upd.get('availability') or {}
        ventanas = {k: (av.get(k) or {}).get('percentage') for k in ('day', 'week', 'month')} if av else {}

        estado = max([mm[0] for mm in motivos], key=lambda g: ORDEN_EST[g], default='verde')
        if estado == 'gris' and not [mm for mm in motivos if mm[0] != 'gris']:
            estado = 'verde' if b or vs or sa.get('is_connected') else 'gris'
        problemas.sort(key=lambda p: -p['urgencia'])
        fila = {
            'modular_id': s['id'], 'nombre': sa.get('name'), 'dominio': dom, 'url': sa.get('uri'),
            'cliente_id': c['id'] if c else None, 'cliente': c['nombre'] if c else None,
            'web_id': web_id, 'web_nombre': web_nombre, 'account_id': acc_id, 'account_nombre': acc_nombre,
            'dueno_id': dueno_id, 'dueno': dueno,
            'conectada': sa.get('is_connected'), 'wordpress': sa.get('core_version'), 'php': sa.get('engine_version'),
            'sincronizada': sa.get('synced_at'), 'enlace_modular': ENLACE_MODULAR, 'enlace_nota': NOTA_ENLACE,
            'disponibilidad': {'monitor': u.get('enabled') if u else None, 'estado': u.get('status') if u else None,
                               'desde': u.get('status_since') if u else None, 'ultimo_ping': lp.get('at'),
                               'codigo': lp.get('status_code'), 'ms': lp.get('response_time_ms'), 'error': err_txt or None,
                               'ultima_caida': (u.get('status_since') if u.get('status') == 'down' else None) if u else None,
                               'dia': ventanas.get('day'), 'semana': ventanas.get('week'), 'mes': ventanas.get('month'),
                               'nota': 'Si está «up», «desde» es cuando volvió (fin de la última caída) o cuando empezó a vigilarse.'},
            'monitor_ro': mon,
            'copias': {'ultima': (b.get('last_backup') or {}).get('created_at'), 'fase_ultima': fase,
                       'ultima_buena': b.get('last_done_at'), 'dias_sin_copia_buena': round(dsc, 1) if dsc is not None else None,
                       'total': b.get('total_count'), 'espacio_mb': round((b.get('storage_used') or 0) / 1048576)} if b else None,
            'actualizaciones': {'pendientes': n_act,
                                'nucleo': sum(1 for x in it if x.get('type') == 'core'),
                                'plugins': sum(1 for x in it if x.get('type') == 'plugin'),
                                'temas': sum(1 for x in it if x.get('type') == 'theme'),
                                'detalle': [{'tipo': x.get('type'), 'nombre': x.get('name'), 'de': x.get('version'), 'a': x.get('new_version'),
                                             'con_vulnerabilidad': x.get('vulnerabilities_exists')}
                                            for x in sorted(it, key=lambda x: ({'core': 0, 'plugin': 1, 'theme': 2}.get(x.get('type'), 3), not x.get('vulnerabilities_exists')))][:30]},
            'vulnerabilidades': {'total': len(vs), 'criticas': sum(1 for x in vs if x.get('severity') == 'c'),
                                 'altas': sum(1 for x in vs if x.get('severity') == 'h'),
                                 'medias': sum(1 for x in vs if x.get('severity') == 'm'),
                                 'bajas': sum(1 for x in vs if x.get('severity') in ('l', 'n')),
                                 'sin_parche': sum(1 for x in vs if x.get('unfixed')),
                                 'lista': [{'gravedad': SEV.get(x.get('severity'), x.get('severity')), 'componente': (x.get('component') or {}).get('name'),
                                            'tipo': (x.get('component') or {}).get('type'), 'nombre': x.get('name'), 'sin_parche': x.get('unfixed'),
                                            'fuente': x.get('source_url')}
                                           for x in sorted(vs, key=lambda x: {'c': 0, 'h': 1, 'm': 2, 'l': 3}.get(x.get('severity'), 4))][:12]},
            'certificado': cert,
            'salud': salud, 'malware': malware, 'enlaces_rotos': enlaces,
            'detalle_leido': dw.get('leido'),
            'estado': estado, 'motivos': [mm[1] for mm in sorted(motivos, key=lambda mm: -ORDEN_EST[mm[0]])] or ['Todo en orden según Modular'],
            'problemas': problemas, 'urgencia': sum(p['urgencia'] for p in problemas if p['gravedad'] != 'verde'),
            'incidencias': inc,
        }
        alertas.extend(inc)
        if c:
            vistos.add(c['id'])
            webs.append(fila)
        else:
            sin_cliente.append(fila)
    webs.sort(key=lambda w: (-w['urgencia'], w['cliente'] or ''))
    sin_cliente.sort(key=lambda w: -w['urgencia'])
    faltan = []
    for c in cls:
        if c.get('web') and c['id'] not in vistos:
            web_id, web_nombre = sil_web.get(c['id']) or (None, None)
            faltan.append({'cliente_id': c['id'], 'cliente': c['nombre'], 'web': c['web'], 'dominio': dominio(c['web']),
                           'web_id': web_id, 'web_nombre': web_nombre, 'dueno_id': web_id or jefe, 'dueno': personas.get(web_id or jefe) or (web_id or jefe),
                           'monitor_ro': mon_cli.get(c['id']) or mon_dom.get(dominio(c['web'])),
                           'accion': 'Añadir la web a Modular (instalar Modular Connector) para tener copias, actualizaciones y seguridad.'})
    resumen = {'webs_modular': len(d.get('webs') or []), 'emparejadas': len(webs), 'sin_cliente': len(sin_cliente),
               'clientes_con_web_fuera_de_modular': len(faltan),
               'rojo': sum(w['estado'] == 'rojo' for w in webs), 'ambar': sum(w['estado'] == 'ambar' for w in webs),
               'verde': sum(w['estado'] == 'verde' for w in webs), 'gris': sum(w['estado'] == 'gris' for w in webs),
               'caidas_ahora': sum((w['disponibilidad'] or {}).get('estado') == 'down' for w in webs),
               'caidas_de_verdad': sum(any(p['clave'] == 'caida' for p in w['problemas']) for w in webs),
               'sin_copia_buena': sum(any(p['clave'] in ('sin_copia', 'copia_atrasada') for p in w['problemas']) for w in webs),
               'con_vulnerabilidad_critica': sum(w['vulnerabilidades']['criticas'] > 0 for w in webs),
               'vulnerabilidades_graves': sum(w['vulnerabilidades']['criticas'] + w['vulnerabilidades']['altas'] for w in webs),
               'actualizaciones_pendientes': sum(w['actualizaciones']['pendientes'] or 0 for w in webs),
               'con_detalle': sum(1 for w in webs if w['detalle_leido'])}
    ri = d.get('resumen_items') or {}
    meta = {'generado': dt.datetime.now().strftime('%Y-%m-%d %H:%M'), 'leido': d.get('leido'),
            'fuente': 'Modular DS · API pública (solo lectura)', 'estado': 'conectado', 'doc_api': DOC_API,
            'enlace': ENLACE_MODULAR, 'enlace_nota': NOTA_ENLACE, 'errores_parciales': d.get('errores') or {},
            'totales_modular': ri.get('meta'), 'detalle_leidas': d.get('detalle_leidas'),
            'detalle_rotacion': 'Disponibilidad por ventanas, salud, enlaces rotos y certificado: las caídas en cada pasada y el resto por turnos (cada web cada 3-4 h).',
            'jefe_web': jefe}
    if d.get('_dato_viejo'):
        meta['dato_viejo'] = d['_dato_viejo']
    if d.get('_desde_cache'):
        meta['desde_cache'] = True
    return {'_meta': meta, 'resumen': resumen, 'webs': webs, 'sin_cliente': sin_cliente, 'clientes_sin_modular': faltan, 'alertas': alertas}


def tablero(out):
    """data/modular/tablero.json · el tablero del equipo web: TODAS las webs (también las que no son de su cartera y las
    sin cliente) con la clave «cliente» (no «cliente_id»), como data/seo/webs.json, para cubrir guardias. Solo lo leen los
    puestos de web, el jefe de SEO y web, operaciones y dirección (reglas_permisos.json → datos_de_modulo)."""
    def fila(w, sin_cli=False):
        x = {k: v for k, v in w.items() if k not in ('cliente_id', 'cliente', 'incidencias')}
        x['cliente'] = w.get('cliente_id') or None
        x['cliente_nombre'] = w.get('cliente') or None
        x['sin_cliente'] = sin_cli
        return x
    filas = [fila(w) for w in out.get('webs') or []] + [fila(w, True) for w in out.get('sin_cliente') or []]
    filas.sort(key=lambda w: (-(w.get('urgencia') or 0), w.get('cliente_nombre') or w.get('nombre') or ''))
    fuera = [{**{k: v for k, v in f.items() if k != 'cliente_id'}, 'cliente': f['cliente_id'], 'cliente_nombre': f['cliente']}
             for f in out.get('clientes_sin_modular') or []]
    return {'_meta': out['_meta'], 'resumen': out.get('resumen'), 'webs': filas, 'fuera_de_modular': fuera}


def main():
    d = leer()
    if '_sin_clave' in d:
        out = sin_conectar('No hay clave de la API de Modular DS en este equipo.')
    elif '_error' in d:
        out = sin_conectar('La API de Modular DS respondió con error: ' + d['_error'])
    else:
        out = construir(d)
    guardar(SALIDA, out)
    guardar(TABLERO, tablero(out) if out['_meta']['estado'] == 'conectado' else {'_meta': out['_meta'], 'resumen': None, 'webs': [], 'fuera_de_modular': []})
    r = out.get('resumen')
    print(f"data/modular/webs.json + tablero.json · {out['_meta']['estado']}" + (f" · {r}" if r else f" · {out['_meta']['motivo']}"))


if __name__ == '__main__':
    main()
