#!/usr/bin/env python3
"""M15 · Reuniones · genera data/reuniones/reuniones.json (solo lectura de Zoom, CRM y panel).

Qué lee:
  · Zoom de toda la cuenta de RO con la app «Panel RO lectura» (~/RO_HERRAMIENTAS/zoom/zm.py, llave del llavero):
      - /accounts/me/recordings       → reuniones GRABADAS en la nube (Zoom las borra a los 120 días).
      - /past_meetings/<uuid>/participants → quién entró y cuánto rato (este permiso SÍ está).
      - /meetings/<uuid>/meeting_summary   → si hay resumen de Zoom (texto solo en reuniones internas).
    NO está el permiso de «reuniones pasadas» (meeting:read:list_meetings / past_meeting): las reuniones
    que no se graban no se ven. La grabación automática está activada y bloqueada para toda la cuenta desde el 2-oct;
    antes solo hay las que alguien grabó a mano. Se dice en pantalla (W4 lo amplía).
  · Reuniones con cliente del CRM, Fathom y la verificación manual: data/clientes/<id>.json (capa E1, fuente
    «reuniones») + panel de Mili (datos.json: exento, nuevo, sin_reunion_mes_ant).
  · Personas (correo, alias, horas al mes) de data/personas.json para casar participantes.

Plan A (por defecto): Zoom en vivo (≈ 1 + N + resúmenes llamadas) → copia SANEADA en fuentes_reuniones/_cache/.
Plan B (--ficheros o si Zoom falla): esa copia.
Salida sin correos, teléfonos, claves de acceso ni enlaces compartidos (share_url, passcode). Escáner al final.
Uso:  python3 generar_reuniones.py [--ficheros]
"""
import importlib.util
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
sys.path.insert(0, str(APP / 'fuentes'))
from comun import escanear, escribir, leer, norm, sanear, slug, tokens  # noqa: E402

DATA = APP / 'data'
SALIDA = DATA / 'reuniones' / 'reuniones.json'
CACHE = AQUI / '_cache' / 'zoom_reuniones.json'
sys.path.insert(1, str(Path(__file__).resolve().parents[1]))  # C5: rutas y secretos en config.py
import config  # noqa: E402
PANEL = config.PANEL_BUILD / 'datos.json'
ZM = config.HERRAMIENTAS / 'zoom/zm.py'
DOMINIOS_RO = ('rankingonline.com', 'rankingonline.es')
HOY = date.today()
AHORA = datetime.now()

TIPOS = ['Daily', 'Coordinación', '1:1', 'Seguimiento', 'Formación', 'Cliente']
RE_TIPO = re.compile(r'^\s*(daily|coordinaci[oó]n|1\s*[:a]\s*1|uno a uno|seguimiento|formaci[oó]n|cliente)\b', re.I)


def tipo_por_nombre(tema):
    m = RE_TIPO.match(tema or '')
    if not m:
        return None
    t = norm(m.group(1))
    if t.startswith('daily'): return 'Daily'
    if t.startswith('coordinac'): return 'Coordinación'
    if t.startswith('seguim'): return 'Seguimiento'
    if t.startswith('formac'): return 'Formación'
    if t.startswith('cliente'): return 'Cliente'
    return '1:1'


# ------------------------------------------------------------------ Zoom en vivo
def cargar_zm():
    spec = importlib.util.spec_from_file_location('zm', ZM)
    zm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(zm)
    return zm


def zoom_en_vivo():
    zm = cargar_zm()
    tk = zm.token()

    def g(path, **q):
        url = 'https://api.zoom.us/v2' + path + ('?' + urllib.parse.urlencode(q) if q else '')
        try:
            return 200, json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'Authorization': 'Bearer ' + tk}), timeout=60))
        except urllib.error.HTTPError as e:
            return e.code, {'_msg': e.read().decode()[:160]}

    def enc(u):  # Zoom: doble codificación si el uuid empieza por / o lleva //
        return urllib.parse.quote(urllib.parse.quote(u, safe=''), safe='') if u.startswith('/') or '//' in u else urllib.parse.quote(u, safe='')

    # usuarios (para el anfitrión): solo id → correo, que se traduce a persona aquí y no se guarda
    c, u = g('/users', page_size=300)
    usuarios = {x['id']: (x.get('email') or '').lower() for x in (u.get('users') or [])} if c == 200 else {}

    # grabaciones: ventanas de un mes, desde hace 120 días (lo que Zoom guarda)
    ini = HOY - timedelta(days=120)
    crudas, d = {}, ini
    while d <= HOY:
        fin = min(d + timedelta(days=29), HOY)
        tok = ''
        while True:
            c, r = g('/accounts/me/recordings', **{'from': d.isoformat(), 'to': fin.isoformat(), 'page_size': 300, 'next_page_token': tok})
            if c != 200:
                raise RuntimeError(f'Zoom grabaciones {c}: {r.get("_msg")}')
            for m in r.get('meetings', []):
                crudas[m['uuid']] = m
            tok = r.get('next_page_token') or ''
            if not tok:
                break
        d = fin + timedelta(days=1)

    permisos = {'grabaciones': True, 'participantes': None, 'resumen': None, 'reuniones_no_grabadas': False}
    reuniones = []
    for uuid, m in crudas.items():
        tipos = sorted({f.get('file_type') for f in m.get('recording_files', []) if f.get('file_type')})
        c, p = g(f'/past_meetings/{enc(uuid)}/participants', page_size=300)
        partes = []
        if c == 200:
            permisos['participantes'] = True
            for x in p.get('participants', []):
                partes.append({'nombre': x.get('name') or '', 'correo': (x.get('user_email') or '').lower(),
                               'interno_zoom': bool(x.get('internal_user')), 'segundos': x.get('duration') or 0})
        elif permisos['participantes'] is None:
            permisos['participantes'] = False
        resumen = None
        if 'SUMMARY' in tipos:
            c, s = g(f'/meetings/{enc(uuid)}/meeting_summary')
            if c == 200:
                permisos['resumen'] = True
                resumen = {'titulo': s.get('summary_title'), 'texto': s.get('summary_overview'),
                           'pasos': [str(x)[:200] for x in (s.get('next_steps') or [])][:6],
                           'enlace': s.get('summary_doc_url')}
            elif permisos['resumen'] is None:
                permisos['resumen'] = False
        reuniones.append({
            'uuid': uuid, 'tema': m.get('topic') or '', 'inicio': m.get('start_time'), 'minutos': m.get('duration') or 0,
            'anfitrion_correo': usuarios.get(m.get('host_id'), '') or (m.get('host_email') or '').lower(),
            'archivos': tipos, 'participantes': partes, 'resumen': resumen,
        })
    return reuniones, permisos


# ------------------------------------------------------------------ casar personas y clientes
def indice_personas():
    pers = leer(DATA / 'personas.json', [])
    por_correo, por_nombre = {}, []
    for p in pers:
        for c in [p.get('correo')] + (p.get('otros_correos') or []):
            if c:
                por_correo[c.lower()] = p
        nombres = {p.get('nombre') or '', p.get('alias') or ''} | set(p.get('alias_todos') or [])
        por_nombre.append((p, [tokens(n) | {w for w in norm(n).split() if len(w) >= 3} for n in nombres if n]))
    return pers, por_correo, por_nombre


def persona_de(part, por_correo, por_nombre):
    if part['correo'] in por_correo:
        return por_correo[part['correo']]
    nt = {w for w in norm(part['nombre']).split() if len(w) >= 3}
    if not nt:
        return None
    mejores = []
    for p, variantes in por_nombre:
        nombre_completo = {w for w in norm(p.get('nombre')).split() if len(w) >= 3}
        if nombre_completo and nombre_completo <= nt | nombre_completo and len(nt & nombre_completo) >= 2:
            mejores.append((3, p))
        elif norm(p.get('alias')) and norm(p.get('alias')) in nt and len(nt) == 1:
            mejores.append((1, p))
    if not mejores:
        return None
    mejores.sort(key=lambda x: -x[0])
    if len(mejores) > 1 and mejores[0][0] == mejores[1][0]:
        return None  # dos personas posibles: no se adivina
    return mejores[0][1]


def dominio_web(url):
    d = re.sub(r'^(https?://)?(www\.)?', '', str(url or '').strip().lower())
    return d.split('/')[0]


def indice_clientes():
    idx = leer(DATA / 'indice_clientes.json', {}) or {}
    filas = idx.get('clientes', []) if isinstance(idx, dict) else idx
    base = {c['id']: c for c in (leer(DATA / 'clientes.json', []) or [])}
    out = {}
    for f in filas:
        cid = f['id']
        ficha = leer(DATA / 'clientes' / f'{cid}.json', {}) or {}
        out[cid] = {'id': cid, 'nombre': f.get('nombre') or ficha.get('nombre'), 'activo': f.get('activo_libro'), 'en_panel': f.get('en_panel'),
                    'dominio': dominio_web(ficha.get('web')), 'ficha': ficha, 'base': base.get(cid, {})}
    return out


# R12 (Emex ≠ Romero Martínez): un apellido corriente suelto en el título («Reunión de Candela con Álvaro Martínez») no
# empareja con un cliente que se llama como dos apellidos («Romero Martínez»). Con apellidos corrientes hacen falta TODAS
# las palabras del nombre del cliente; si no, la reunión queda sin cliente (mejor «sin emparejar» que en la ficha de otro).
APELLIDOS_CORRIENTES = {'garcia', 'martinez', 'lopez', 'sanchez', 'gonzalez', 'rodriguez', 'fernandez', 'perez', 'gomez', 'martin',
                        'jimenez', 'ruiz', 'hernandez', 'diaz', 'moreno', 'alvarez', 'munoz', 'romero', 'alonso', 'gutierrez',
                        'navarro', 'torres', 'dominguez', 'vazquez', 'ramos', 'gil', 'ramirez', 'serrano', 'blanco', 'molina',
                        'morales', 'suarez', 'ortega', 'delgado', 'castro', 'ortiz', 'rubio', 'marin', 'sanz', 'iglesias',
                        'nunez', 'medina', 'garrido', 'cortes', 'castillo', 'santos', 'lozano', 'guerrero', 'cano', 'prieto',
                        'mendez', 'cruz', 'calvo', 'gallego', 'vidal', 'leon', 'herrera', 'marquez', 'pena', 'flores',
                        'cabrera', 'campos', 'vega', 'fuentes', 'carrasco', 'diez', 'caballero', 'reyes', 'nieto', 'aguilar',
                        'pascual', 'santana', 'herrero', 'lorenzo', 'hidalgo', 'montero', 'ibanez', 'gimenez', 'ferrer', 'duran',
                        'vicente', 'benitez', 'mora', 'santiago', 'arias', 'vargas', 'carmona', 'crespo', 'roman', 'pastor',
                        'soto', 'saez', 'velasco', 'moya', 'soler', 'parra', 'esteban', 'bravo', 'gallardo', 'rojas'}


def cliente_de(tema, dominios, clientes):
    for cid, c in clientes.items():
        if c['dominio'] and c['dominio'] in dominios:
            return cid, 'dominio del participante'
    tt = tokens(tema)
    candidatos = []
    for cid, c in clientes.items():
        t_cli = {w for w in tokens(c['nombre']) if len(w) >= 4}
        comun_ = t_cli & tt
        if comun_ and (comun_ == t_cli or any(len(w) >= 6 and w not in APELLIDOS_CORRIENTES for w in comun_)):
            candidatos.append(cid)
    if not candidatos:  # siglas cortas («AGC»): palabra entera en mayúsculas en el título
        for cid, c in clientes.items():
            n = (c['nombre'] or '').strip()
            if 2 < len(n) <= 4 and n.isupper() and re.search(rf'(?<![\w]){re.escape(n)}(?![\w])', tema or ''):
                candidatos.append(cid)
    if len(candidatos) == 1:
        return candidatos[0], 'nombre del cliente en el título'
    return None, None


def limpiar_titulo(t):
    """Títulos de Zoom en español: «with» → «con», «X's Zoom Meeting» → «Reunión de X», «Call» → «Llamada»."""
    t = t.strip()
    if re.search(r'(\.\.\.|…)$', t):  # título cortado por Zoom: fuera la palabra a medias
        t = re.sub(r'\s*\S*(\.\.\.|…)$', '', t)
    t = re.sub(r"^(.+?)'s Zoom Meeting$", r'Reunión de \1', t)
    t = re.sub(r'^Meeting created by (.+)$', r'Reunión creada por \1', t)
    t = re.sub(r'^Call con\b', 'Llamada con', t)
    t = re.sub(r'\s+with\s+', ' con ', t)
    t = re.sub(r'\s*<>\s*', ' · ', t)
    t = re.sub(r'^Reunión con (\S+) con ', r'Reunión de \1 con ', t)
    return re.sub(r'\s*(\.\.\.|…)\s*$', '', t).strip()


def fathom_por_cliente(clientes):
    """Llamadas de Fathom de Tomás (panel de dirección: id, enlace, fecha, despacho) casadas con el cliente por el nombre
    del despacho. Sin el nombre del lead (dato de ventas)."""
    txt = (DATA / 'panel_direccion/original.json').read_text() if (DATA / 'panel_direccion/original.json').exists() else ''
    out = defaultdict(list)
    for m in re.finditer(r'\{\\?"id\\?":\\?"R\d+\\?",\\?"url\\?":\\?"(https://fathom\.video/calls/\d+)\\?",\\?"fecha\\?":\\?"([\d-]+)\\?".{0,400}?\\?"despacho\\?":\\?"([^"\\]*)', txt):
        url, fecha, despacho = m.groups()
        cid, _ = cliente_de(despacho, set(), clientes)
        if cid:
            # el id va como número: la app compone https://fathom.video/calls/<id> (un id de 9 cifras parece un teléfono al escáner)
            out[cid].append({'fecha': fecha, 'fuente': 'Fathom', 'id': int(url.rsplit('/', 1)[1]), 'quien': 'Tomás'})
    return out


def enlace_grabacion(uuid):
    # Página de la grabación en el portal de Zoom (pide iniciar sesión; nunca el enlace compartido con código).
    return 'https://zoom.us/recording/management/detail?meeting_id=' + urllib.parse.quote(uuid, safe='')


# ------------------------------------------------------------------ principal
def main():
    plan, error, permisos = 'A · Zoom en vivo', None, None
    if '--ficheros' not in sys.argv:
        try:
            crudas, permisos = zoom_en_vivo()
            pers, por_correo, por_nombre = indice_personas()
            # copia saneada: personas casadas y dominios, sin correos ni nombres de gente de fuera
            limpias = []
            for r in crudas:
                partes = []
                for x in r['participantes']:
                    p = persona_de(x, por_correo, por_nombre)
                    dom = x['correo'].split('@')[1] if '@' in x['correo'] else ''
                    interna = bool(p) or dom in DOMINIOS_RO
                    partes.append({'persona_id': p['id'] if p else None, 'interna': interna,
                                   'ro_sin_ficha': interna and not p, 'dominio': None if interna else (dom or None),
                                   'segundos': x['segundos']})
                anf = por_correo.get(r['anfitrion_correo'])
                limpias.append({'uuid': r['uuid'], 'tema': sanear(r['tema']), 'inicio': r['inicio'], 'minutos': r['minutos'],
                                'anfitrion_id': anf['id'] if anf else None, 'archivos': r['archivos'], 'participantes': partes,
                                'resumen': None if not r['resumen'] else {
                                    'titulo': sanear(r['resumen'].get('titulo')), 'texto': sanear(r['resumen'].get('texto')),
                                    'pasos': [sanear(x) for x in r['resumen'].get('pasos') or []], 'enlace': r['resumen'].get('enlace')}})
            escribir(CACHE, {'_meta': {'leido': AHORA.strftime('%Y-%m-%d %H:%M'), 'permisos': permisos,
                                       'fuente': 'Zoom API (zm.py), solo lectura; copia saneada'}, 'reuniones': limpias})
        except (SystemExit, Exception) as e:  # noqa: BLE001
            plan, error = 'B · copia saneada en _cache/', f'{type(e).__name__}: {str(e)[:140]}'
    else:
        plan = 'B · copia saneada en _cache/ (--ficheros)'
    cache = leer(CACHE)
    if not cache:
        sys.exit(f'No hay copia de Zoom y no se pudo leer en vivo ({error}).')
    permisos = cache['_meta'].get('permisos') or permisos or {}
    leido = cache['_meta']['leido']

    pers = {p['id']: p for p in leer(DATA / 'personas.json', [])}
    clientes = indice_clientes()
    panel = {slug(c['nombre']): c for c in (leer(PANEL, {}) or {}).get('clientes', [])}

    asistencias, reuniones_out = [], []
    sin_ficha = cortas = 0
    for r in sorted(cache['reuniones'], key=lambda x: x['inicio'] or ''):
        inicio = datetime.strptime(r['inicio'][:19], '%Y-%m-%dT%H:%M:%S') + timedelta(hours=2)  # UTC → Madrid (CEST)
        internos = defaultdict(int)
        externos_dom, n_ext = Counter(), 0
        for x in r['participantes']:
            if x['interna'] and x['persona_id']:
                internos[x['persona_id']] += x['segundos'] or 0
            elif x['interna']:
                sin_ficha += 1
            else:
                n_ext += 1
                externos_dom[x['dominio'] or 'invitado sin correo'] += 1
        if r.get('anfitrion_id') and r['anfitrion_id'] not in internos:
            internos[r['anfitrion_id']] += 0
        if (r['minutos'] or 0) < 2:
            cortas += 1  # reuniones de menos de 2 minutos: pruebas o salas abiertas por error; no cuentan
            continue
        cid, metodo = cliente_de(r['tema'], set(externos_dom), clientes)
        # interna = solo gente de RO · cliente = un cliente reconocido (dominio o nombre) · externa = gente de fuera
        # sin cliente reconocido (prospectos de ventas, proveedores, candidatos o invitados sin correo)
        ambito = 'cliente' if cid else 'externa' if n_ext else 'interna'
        tipo = tipo_por_nombre(r['tema'])
        tnorm = norm(r['tema'])
        sugerido = ('Cliente' if ambito == 'cliente' or (ambito == 'externa' and len(internos) < 4) else 'Daily' if 'daily' in tnorm
                    else 'Formacion' if re.search(r'formaci|capacitaci|curso|taller interno', tnorm)
                    else '1:1' if len(internos) == 2 else 'Coordinación')
        sugerido = 'Formación' if sugerido == 'Formacion' else sugerido
        archivos = set(r['archivos'])
        acta = {'grabacion': bool(archivos & {'MP4', 'M4A'}), 'transcripcion': 'TRANSCRIPT' in archivos,
                'resumen': bool(r.get('resumen')), 'enlace_grabacion': enlace_grabacion(r['uuid']),
                'enlace_resumen': (r.get('resumen') or {}).get('enlace')}
        rid = 'z' + slug(r['uuid'])[:14]
        tema = r['tema'] or '(sin título)'
        if ambito == 'externa':  # noqa
            # sin cliente reconocido suelen ser prospectos de ventas o candidatos: fuera el nombre de la persona de fuera
            # del título (D-88: datos de leads solo para quien los trabaja; el título lo ven también su jefe y Operaciones)
            tema = re.split(r'\s+(?:with|·|-\s+con)\s+', tema)[0].strip() + (' · con persona de fuera' if re.search(r'\s(with|·)\s', tema) else '')
        tema = limpiar_titulo(tema)
        minutos = r['minutos'] or 0
        quienes = sorted(internos, key=lambda p: -internos[p])
        fila_base = {
            'reunion': rid, 'fecha': inicio.strftime('%Y-%m-%d'), 'hora': inicio.strftime('%H:%M'), 'mes': inicio.strftime('%Y-%m'),
            'tema': tema, 'minutos_reunion': minutos, 'tipo': tipo, 'tipo_sugerido': sugerido,
            'ambito': ambito, 'cliente': clientes[cid]['nombre'] if cid else None, 'cli': cid, 'cliente_metodo': metodo,
            'anfitrion': pers.get(r.get('anfitrion_id'), {}).get('alias'),
            'internos': [pers[p]['alias'] for p in quienes if p in pers], 'n_externos': n_ext,
            'dominios_externos': sorted(d for d in externos_dom if d != 'invitado sin correo')[:4],
            'invitados_sin_correo': externos_dom.get('invitado sin correo', 0), 'acta': acta,
            # texto del resumen de Zoom solo en internas (en las de cliente, el enlace: grabación = participantes + jefe + dirección)
            'resumen': ({'texto': (r['resumen'].get('texto') or '')[:700], 'pasos': (r['resumen'].get('pasos') or [])[:5]}
                        if r.get('resumen') and ambito == 'interna' else None),
        }
        for pid in quienes:
            seg = internos[pid]
            mins = min(minutos, round(seg / 60)) if seg else minutos
            asistencias.append({**fila_base, 'id': f'{rid}·{pid}', 'persona_id': pid, 'persona': pers.get(pid, {}).get('alias', pid),
                                'minutos': mins, 'es_anfitrion': pid == r.get('anfitrion_id')})
        reuniones_out.append(rid)

    # por persona y mes
    pm = defaultdict(lambda: {'reuniones': 0, 'min': 0, 'min_int': 0, 'min_cli': 0, 'min_ext': 0, 'tipos': Counter(), 'sin_tipo': 0, 'sin_acta': 0})
    for a in asistencias:
        k = (a['persona_id'], a['mes'])
        x = pm[k]
        x['reuniones'] += 1
        x['min'] += a['minutos']
        x[{'interna': 'min_int', 'cliente': 'min_cli'}.get(a['ambito'], 'min_ext')] += a['minutos']
        x['tipos'][a['tipo'] or 'Sin tipo'] += a['minutos']
        x['sin_tipo'] += 0 if a['tipo'] else 1
        x['sin_acta'] += 0 if (a['acta']['grabacion'] or a['acta']['resumen']) else 1
    por_persona_mes = []
    for (pid, mes), x in sorted(pm.items()):
        p = pers.get(pid, {})
        cap = p.get('horas_mes') or 128
        horas = round(x['min'] / 60, 2)
        por_persona_mes.append({'persona_id': pid, 'persona': p.get('alias', pid), 'nombre': p.get('nombre'),
                                'puestos': p.get('puestos', []), 'mes': mes, 'reuniones': x['reuniones'], 'horas': horas,
                                'horas_internas': round(x['min_int'] / 60, 2), 'horas_cliente': round(x['min_cli'] / 60, 2), 'horas_externas': round(x['min_ext'] / 60, 2),
                                'por_tipo': {t: round(m / 60, 2) for t, m in x['tipos'].items()}, 'sin_tipo': x['sin_tipo'],
                                'sin_acta': x['sin_acta'], 'capacidad_h': cap, 'pct_capacidad': round(horas / cap * 100, 1)})

    # reunión con cada cliente el mes pasado (regla del panel: alarma si no hubo; mantenimiento exento)
    mes_pas = (HOY.replace(day=1) - timedelta(days=1))
    mes_pasado = mes_pas.strftime('%Y-%m')
    zoom_cli = defaultdict(list)
    for a in asistencias:
        if a['cli']:
            zoom_cli[a['cli']].append(a)
    verdad = {c['cliente_id']: c for c in (leer(DATA / 'verdad/clientes.json', {}) or {}).get('clientes', [])}
    wa = {c['cliente_id']: c for c in (leer(DATA / 'whatsapp/whatsapp.json', {}) or {}).get('clientes', [])}
    fathom = fathom_por_cliente(clientes)
    crm_ev = defaultdict(list)
    for e in (leer(DATA / 'agenda/agenda.json', {}) or {}).get('eventos', []):
        if e.get('fuente') == 'crm' and e.get('cliente_ref') and e.get('enlace'):
            crm_ev[e['cliente_ref']].append({'fecha': e['inicio'][:10], 'fuente': 'CRM', 'id': int(e['enlace'].rsplit('/', 1)[1]), 'quien': pers.get(e.get('persona_id'), {}).get('alias')})
    filas_cli = []
    for cid, c in clientes.items():
        if c['activo'] == 'Baja':
            continue
        f = c['ficha'].get('fuentes', {}) if c['ficha'] else {}
        reu = (f.get('reuniones') or {}).get('datos') or {}
        cart = (f.get('cartera') or {}).get('datos') or {}
        pn = panel.get(cid) or {}
        hist = [x for x in reu.get('historial') or [] if (x.get('fecha') or '')[:7] == mes_pasado]
        zl = {}
        for a in zoom_cli.get(cid, []):
            zl[a['reunion']] = a
        z_mes = [a for a in zl.values() if a['mes'] == mes_pasado and a['minutos_reunion'] >= 20]
        exento = bool(cart.get('exento') or pn.get('exento'))
        nuevo = bool(cart.get('nuevo') or pn.get('nuevo') or c['base'].get('nuevo'))
        alta = c['base'].get('alta')
        aplica = not (alta and alta[:7] >= mes_pasado)
        n_crm = reu.get('reuniones_mes_anterior') if reu.get('reuniones_mes_anterior') is not None else len(hist)
        verif = pn.get('reu_verif')
        w = wa.get(cid) or {}
        w_mes = [x for x in w.get('reuniones') or [] if str((x.get('fecha') if isinstance(x, dict) else x) or '')[:7] == mes_pasado]
        f_mes = [x for x in fathom.get(cid, []) if x['fecha'][:7] == mes_pasado]
        hubo = (n_crm or 0) > 0 or bool(z_mes) or verif == 'hubo' or bool(w_mes) or bool(f_mes)
        motivo_na = None
        if not c.get('en_panel'):
            aplica, motivo_na = False, 'fuera de la cartera mensual (alta nueva o proyecto)'
        elif not aplica:
            motivo_na = f'alta en {alta[:7]}'
        estado = 'exento' if exento else 'ok' if hubo else 'no_aplica' if not aplica else 'sin_reunion'
        ult = max([x for x in [reu.get('ult_reunion')] + [a['fecha'] for a in zl.values()] if x] or [None]) if (reu.get('ult_reunion') or zl) else None
        v = verdad.get(cid) or {}
        acc_id = v.get('account') if cid in verdad else c['base'].get('responsable_id')   # verdad única: principal vigente
        enlaces = sorted([x for x in fathom.get(cid, []) + crm_ev.get(cid, []) if x['fecha'] >= (HOY - timedelta(days=75)).isoformat()]
                         + [{'fecha': a['fecha'], 'fuente': 'Zoom', 'enlace': a['acta']['enlace_grabacion'], 'quien': a['anfitrion']} for a in zl.values()],
                         key=lambda x: x['fecha'], reverse=True)[:6]
        filas_cli.append({
            'cliente_id': cid, 'cliente': c['nombre'], 'account_id': acc_id,
            'account': pers.get(acc_id, {}).get('alias') if acc_id else 'sin account',
            'reuniones_whatsapp': len(w_mes), 'whatsapp_conectado': w.get('estado') not in (None, 'sin_conectar'),
            'reuniones_fathom': len(f_mes), 'enlaces': enlaces,
            'mes': mes_pasado, 'estado': estado, 'motivo_no_aplica': motivo_na,
            'motivo_exento': cart.get('motivo_exento') or pn.get('motivo_exento'), 'nuevo': nuevo, 'alta': alta,
            'reuniones_crm': n_crm or 0, 'reuniones_zoom': len(z_mes), 'verificacion': verif,
            'ultima': ult, 'dias_sin': (HOY - date.fromisoformat(ult)).days if ult else None,
            'proxima': reu.get('prox_reunion'),
            'detalle': [{'fecha': x.get('fecha'), 'asunto': sanear(x.get('asunto'))[:90] if x.get('asunto') else None, 'fuente': x.get('fuente'), 'quien': x.get('quien')} for x in hist][-5:]
                       + [{'fecha': a['fecha'], 'asunto': a['tema'][:90], 'fuente': 'Zoom', 'quien': a['anfitrion'], 'minutos': a['minutos_reunion']} for a in z_mes],
        })

    meses = sorted({a['mes'] for a in asistencias})
    salida = {
        '_meta': {
            'generado': AHORA.strftime('%Y-%m-%d %H:%M'), 'plan': plan, 'error': error, 'zoom_leido': leido,
            'fuente': 'Zoom (cuenta de RO, app «Panel RO lectura», zm.py) + CRM/Fathom/verificación (capa E1) + panel de Mili',
            'permisos': permisos, 'meses': meses, 'mes_pasado': mes_pasado,
            'reuniones': len(reuniones_out), 'asistencias': len(asistencias), 'participantes_ro_sin_ficha': sin_ficha,
            'cortas_descartadas': cortas,
            'limite': 'Lo que no pasa por el Zoom de RO no se cuenta. Hoy solo se ven las reuniones grabadas: falta el permiso '
                      'de Zoom para leer las no grabadas. La grabación automática está activada y bloqueada para toda la cuenta '
                      'desde el 2-oct; antes solo están las que alguien grabó a mano. Zoom borra a los 120 días.',
            'tipos': TIPOS, 'capacidad_por_defecto_h': 128,
            'regla_cliente': 'Misma regla que En rojo: ninguna reunión el mes pasado en el CRM, Fathom, Zoom (20 min o más) '
                             'ni en los grupos de WhatsApp. Exentos los de mantenimiento y las altas de ese mes.',
        },
        'asistencias': asistencias,
        'por_persona_mes': por_persona_mes,
        'clientes': filas_cli,
    }
    hall = escanear(salida)
    # los dominios de empresa (gacgrup.com) no son correos; el escáner no los marca. Si marca algo, no se escribe.
    if hall:
        print('Puerta de secretos: NO se escribe.', *hall[:10], sep='\n  ')
        sys.exit(2)
    escribir(SALIDA, salida)
    print(f'reuniones.json · plan {plan}{" · " + error if error else ""}')
    print(f'  {len(reuniones_out)} reuniones grabadas · {len(asistencias)} asistencias · meses {meses} · permisos {permisos}')
    print(f'  {len(por_persona_mes)} filas persona×mes · {len(filas_cli)} clientes · sin reunión en {mes_pasado}: '
          f'{sum(1 for f in filas_cli if f["estado"] == "sin_reunion")} · exentos {sum(1 for f in filas_cli if f["estado"] == "exento")}')


if __name__ == '__main__':
    main()
