#!/usr/bin/env python3
"""M23 · Agenda · genera data/agenda/agenda.json (+ data/agenda/_privado/<persona>.json) · SOLO LECTURA.

Qué junta (2-oct-2026), de hace 14 días a dentro de 21:
  1. Zoho CRM · módulo Events (zh.py, llave propia de zoho.eu): las reuniones que cada persona tiene en su calendario
     de Zoho y que pasan por el CRM (las que se crean desde Bookings con la integración CRM también caen aquí).
  2. GoHighLevel de RO (subcuenta de RO, lector de ~/Downloads/SETTERS_RO_2026-09-24/25_GHL_PRUEBA_SETTERS):
     las citas de los calendarios de Tomás (45 min, 15 min, taller de la oferta, curso Claude). Si el contacto lleva
     la etiqueta setter:<x>, la cita sale también en la agenda de esa setter («la agendaste tú»).
  3. Zoom (data/reuniones/reuniones.json de M15): las reuniones grabadas de los últimos 14 días, para la vista semana.
  4. Zoho Bookings (todas las citas del personal) y Zoho Calendar (el calendario de Tomás, dueño de la llave) con
     ~/RO_HERRAMIENTAS/zoho/zbookings.py, desde el 2-oct 17:10 (Tomás canjeó la llave con sus permisos).
  Sólo citas con referencia compartida explícita o identidad canónica confirmada se consolidan.
  Grabaciones de Zoom sin vínculo confirmado permanecen independientes; la hora no prueba celebración.

Privacidad:
  · Cada fila lleva persona_id (dueño del calendario) → servir.py la manda a esa persona, su jefe, operaciones, RRHH y
    dirección (regla horas_persona). Nada más.
  · El cliente va en «cliente_ref» (no cliente_id) para que tu propia reunión con un cliente que no llevas no desaparezca
    de TU agenda; el enlace a la ficha solo se pinta si puedes abrir ese cliente.
  · Prospectos y gente de fuera: en el fichero público solo iniciales («M··· L···»). Los títulos completos van a
    data/agenda/_privado/<persona_id>.json y solo los abre su dueño (o dirección) con «Ver nombres» (queda en el rastro).
  · Enlaces de Zoom: sin la contraseña (pwd=…). Correos y teléfonos fuera de los textos.
"""
import datetime as dt, json, os, re, sys, unicodedata, urllib.request
from zoneinfo import ZoneInfo
import pathlib as _pl_l27, sys as _sys_l27  # L-27: rutas del Mac por config.py
if str(_pl_l27.Path(__file__).resolve().parents[1]) not in _sys_l27.path:
    _sys_l27.path.append(str(_pl_l27.Path(__file__).resolve().parents[1]))
import config as _cfg  # noqa: E402
try:
    from .crosswalk_runtime_199 import identidad_observada, integrar as integrar_crosswalk
except ImportError:
    from crosswalk_runtime_199 import identidad_observada, integrar as integrar_crosswalk

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
DATA = os.path.join(RAIZ, 'data')
SAL = os.path.join(DATA, 'agenda')
PRIV = os.path.join(SAL, '_privado')
HOME = str(_cfg.HOME)
MAD = ZoneInfo('Europe/Madrid')
AHORA = dt.datetime.now(MAD)
# 30 días atrás (antes 14): el riesgo de baja cuenta las reuniones de un mes (OK de Tomás, 4-oct-2026)
DESDE = (AHORA - dt.timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
HASTA = (AHORA + dt.timedelta(days=21)).replace(hour=23, minute=59, second=0, microsecond=0)

fuentes = []
# Reuniones con CLIENTES canceladas (4-oct): no salen en la agenda, pero el riesgo de baja mira si se reagendaron
# (cancelar sin reagendar es la señal 2 del código semafórico). Solo cliente, fecha y persona: sin nombres.
canceladas = []
def fuente(id_, nombre, estado, detalle, n=0):
    fuentes.append({'id': id_, 'fuente': nombre, 'estado': estado, 'detalle': detalle, 'n': n, 'hora': AHORA.strftime('%Y-%m-%d %H:%M')})

# ------------------------------------------------------------------ utilidades
def norm(x):
    x = unicodedata.normalize('NFD', str(x or '').lower())
    return re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in x if not unicodedata.combining(c))).strip()

STOP = {'asesores', 'asesoria', 'asesoramiento', 'consulting', 'consultores', 'consultoria', 'grup', 'grupo', 'gestoria', 'ranking',
        'online', 'reunion', 'mensual', 'con', 'para', 'del', 'las', 'los', 'una', 'seguimiento', 'llamada', 'taller', 'oferta',
        'tomas', 'sala', 'advisory', 'abogados', 'economistes', 'assessors', 'partners', 'auditores', 'gestor', 'despacho',
        'cliente', 'clientes', 'nuevo', 'nueva', 'minutos', 'min', 'curso', 'claude', 'presentacion', 'propuesta', 'kick', 'off'}
def toks(s): return {t for t in norm(s).split() if len(t) >= 3 and t not in STOP}

def mascara(texto):
    texto = re.sub(r'\s+', ' ', str(texto or '')).strip()
    return ' '.join(p[0].upper() + '···' for p in texto.split(' ') if p and p[0].isalnum())[:60] or 'Persona de fuera'

GENERICO = re.compile(r"(?i)^(\d+\s*minutos|reuni[oó]n|taller|segunda|2\.ª|confirmaci[oó]n|decisi[oó]n|llamada|ranking online|configuraciones b[aá]sicas)|tom[aá]s sala$|^con tom[aá]s|\bcon tom[aá]s sala\b")
def mascara_titulo(t):
    """Deja la plantilla de la reunión y enmascara lo que nombra a alguien de fuera."""
    t = re.sub(r'\s+', ' ', str(t or '')).strip()
    m = re.match(r'(?i)^(.+?) and (.+)$', t)                      # citas de Zoho Bookings que entran al CRM: «<cliente> and <servicio>»
    if m:
        return f'{m.group(2)} · {mascara(m.group(1))}'
    m = re.match(r'(?i)^(reuni[oó]n con tom[aá]s(?: sala)?) con (.+)$', t)
    if m:
        return f'{m.group(1)} · {mascara(m.group(2))}'
    partes = re.split(r'\s(?:·|<>|><|\+|//|-)\s', t)
    if len(partes) > 1:
        return ' · '.join(p if GENERICO.search(p.strip()) else mascara(p) for p in partes)
    return 'Reunión · ' + mascara(t)

RX_CORREO = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')
RX_TEL = re.compile(r'(?:\+34[\s.-]?|0034[\s.-]?)?[6789]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}')
def limpio(t):
    t = RX_CORREO.sub('[correo]', str(t or ''))
    t = RX_TEL.sub('[teléfono]', t)
    return re.sub(r'([?&])(pwd|token|key|password|secret)=[^&\s]+', r'\1\2=…', t)

def ts(s):
    if not s: return None
    if isinstance(s, (int, float)): return dt.datetime.fromtimestamp(s / 1000, MAD)
    try: x = dt.datetime.fromisoformat(str(s).replace('Z', '+00:00'))
    except ValueError: return None
    return x.astimezone(MAD) if x.tzinfo else x.replace(tzinfo=MAD)
def iso(x): return x.astimezone(MAD).strftime('%Y-%m-%d %H:%M') if x else None

# ------------------------------------------------------------------ personas y clientes de la app
PERSONAS = json.load(open(os.path.join(DATA, 'personas.json')))
P_ID = {p['id']: p for p in PERSONAS}
def persona_por_correo(correo, nombre=''):
    loc = (correo or '').split('@')[0].lower()
    for p in PERSONAS:
        for c in [p.get('correo')] + list(p.get('otros_correos') or []):
            if c and c.split('@')[0].lower() == loc:
                return p['id']
    if loc in P_ID: return loc
    n = norm(nombre)
    for p in PERSONAS:
        if n and (norm(p['nombre']) == n or norm(p['nombre']).split(' ')[0] == n.split(' ')[0] and n.split(' ')[-1] in norm(p['nombre'])):
            return p['id']
    return None
ALIAS = {}
for p in PERSONAS:
    ALIAS.setdefault(norm(p.get('alias')), p['id'])

CLIENTES = json.load(open(os.path.join(DATA, 'clientes.json')))
CLI = {c['id']: c for c in CLIENTES}
nombres = {c['id']: {c['nombre']} for c in CLIENTES}
try:
    emp = json.load(open(os.path.join(DATA, 'emparejamientos.json')))['clientes']
    for cid, e in emp.items():
        if cid in nombres:
            for k in ('panel', 'libro'):
                if (e.get('ids') or {}).get(k): nombres[cid].add(e['ids'][k])
            for k in ('ghl', 'metricool'):
                if (e.get(k) or {}).get('nombre'): nombres[cid].add(e[k]['nombre'])
except Exception:
    pass
try:
    for portal, app in json.load(open(os.path.join(DATA, 'ids_clientes.json')))['portal_a_app'].items():
        if app in nombres: nombres[app].add(portal.replace('-', ' '))
except Exception:
    pass
GENERICAS = {'and', 'gestion', 'fiscal', 'laboral', 'contable', 'empresas', 'autonomos', 'administrativa', 'investment',
             'economistas', 'advocats', 'assessoria', 'servicios', 'solutions', 'human', 'finance', 'legal', 'tax'}
# Un cliente casa si TODAS las palabras distintivas de uno de sus nombres cortos (app, portal, subcuenta de GHL) están en el texto.
NOMBRES_CORTOS = {}
for cid, ns in nombres.items():
    for n in ns:
        t = toks(n) - GENERICAS
        if t and len(t) <= 3:
            NOMBRES_CORTOS.setdefault(cid, []).append(t)
def cliente_de(*textos):
    t = set().union(*[toks(x) for x in textos if x])
    mejor, punt = None, 0
    for cid, variantes in NOMBRES_CORTOS.items():
        for v in variantes:
            if v <= t and sum(len(x) for x in v) > punt:
                mejor, punt = cid, sum(len(x) for x in v)
    return mejor

# En rojo = la verdad única (data/verdad/clientes.json, lista común): gravedad «critico» con su motivo corto.
EN_ROJO = {}
try:
    for c in json.load(open(os.path.join(DATA, 'verdad', 'clientes.json'))).get('comun', []):
        if c.get('gravedad') == 'critico':
            EN_ROJO[c['id']] = [c.get('motivo') or 'Cliente en crítico']
except Exception:
    pass

eventos, privado = [], {}
def privado_de(pid):
    return privado.setdefault(pid, {'titulos': {}, 'con_quien': {}})

def alta(ev, titulo_real=None, con_quien_real=None):
    """Una fila por persona y evento. Lo sensible al almacén privado de esa persona."""
    if ev['tipo'] in ('prospecto', 'fuera', 'evento'):
        priv = privado_de(ev['persona_id'])
        if titulo_real: priv['titulos'][ev['id']] = limpio(titulo_real)
        if con_quien_real: priv['con_quien'][ev['id']] = limpio(con_quien_real)
    if ev.get('enlace') and not ev.get('atajos'):
        ev['atajos'] = [{'h': ev['fuente'], 'url': ev['enlace']}]
    ev.pop('enlace', None)
    cref = ev.get('cliente_ref')
    if cref and cref in EN_ROJO:
        ev['en_rojo'] = EN_ROJO[cref]
    eventos.append(ev)

# ------------------------------------------------------------------ 1. Zoho CRM · Events
sys.path.insert(0, os.path.join(HOME, 'RO_HERRAMIENTAS/zoho'))
crm_ok = 0
try:
    import zh
    tk, api = zh.acceso()
    usuarios = {u['id']: u for u in zh.get(tk, api + '/crm/v6/users?type=AllUsers').get('users', [])}
    def coql(q):
        req = urllib.request.Request(api + '/crm/v6/coql', data=json.dumps({'select_query': q}).encode(),
                                     headers={'Authorization': 'Zoho-oauthtoken ' + tk, 'Content-Type': 'application/json'}, method='POST')
        return json.load(urllib.request.urlopen(req, timeout=60))
    filas, off = [], 0
    while True:
        q = ("select Event_Title, Start_DateTime, End_DateTime, Owner, What_Id, Who_Id, Venue, All_day, $se_module from Events "
             f"where Start_DateTime between '{DESDE.isoformat(timespec='seconds')}' and '{HASTA.isoformat(timespec='seconds')}' "
             f"order by Start_DateTime limit {off}, 200")
        r = coql(q)
        filas += r.get('data', [])
        if not (r.get('info') or {}).get('more_records') or off > 2000: break
        off += 200
    # nombres de cuentas y contactos (para emparejar con el cliente), en lectura
    def nombre_registro(mod, rid, cache={}):
        if not rid: return None
        k = (mod, rid)
        if k not in cache:
            d = zh.get(tk, f'{api}/crm/v6/{mod}/{rid}?fields=' + ('Account_Name' if mod == 'Accounts' else 'Full_Name,Account_Name,Company'))
            x = (d.get('data') or [{}])[0]
            cache[k] = x.get('Account_Name') if mod == 'Accounts' else (x.get('Full_Name'), (x.get('Account_Name') or {}).get('name') if isinstance(x.get('Account_Name'), dict) else x.get('Company'))
        return cache[k]
    for e in filas:
        u = usuarios.get((e.get('Owner') or {}).get('id'), {})
        pid = persona_por_correo(u.get('email'), u.get('full_name'))
        if not pid: continue
        ini, fin = ts(e.get('Start_DateTime')), ts(e.get('End_DateTime'))
        modulo = e.get('$se_module')
        cuenta = None
        if (e.get('What_Id') or {}).get('id'):
            cuenta = nombre_registro('Accounts', e['What_Id']['id']) if modulo in (None, 'Accounts') else None
        persona_fuera = None
        contacto_id = (e.get('Who_Id') or {}).get('id') or ((e.get('What_Id') or {}).get('id') if modulo == 'Contacts' else None)
        if contacto_id:
            r_ = nombre_registro('Contacts', contacto_id)
            if isinstance(r_, tuple):
                persona_fuera, emp_ = r_
                cuenta = cuenta or emp_
        titulo = e.get('Event_Title') or 'Reunión'
        cref = cliente_de(cuenta, titulo)
        interna = not cref and not persona_fuera and not cuenta and re.search(r'(?i)\b(daily|interna|equipo|1:1|coordinaci)', titulo or '')
        tipo = 'cliente' if cref else ('interna' if interna else 'prospecto')
        venue = limpio(e.get('Venue') or '')
        ev = {'id': f"crm-{e['id']}", 'persona_id': pid, 'fuente': 'crm', 'inicio': iso(ini), 'fin': iso(fin),
              'todo_el_dia': bool(e.get('All_day')), 'tipo': tipo,
              'identidad_fuente': identidad_observada('crm',str(e['id']),e.get('Start_DateTime'),e.get('End_DateTime'),str((e.get('Owner') or {}).get('id') or '')), 
              'titulo': limpio(titulo) if tipo in ('cliente', 'interna') else mascara_titulo(titulo),
              'cliente_ref': cref, 'cliente_nombre': CLI[cref]['nombre'] if cref else None,
              'con_quien_m': mascara(persona_fuera) if persona_fuera else None,
              'video': 'zoom' if 'zoom' in venue.lower() else ('meet' if 'meet.google' in venue.lower() else None),
              'atajos': [{'h': 'crm', 'url': f"https://crm.zoho.eu/crm/tab/Events/{e['id']}"}]
                        + ([{'h': 'crm_contacto', 'url': f"https://crm.zoho.eu/crm/tab/Contacts/{contacto_id}"}] if contacto_id else []),
              'origen': 'Zoho CRM · calendario de Zoho'}
        alta(ev, titulo, persona_fuera)
        crm_ok += 1
    fuente('crm', 'Zoho CRM · eventos del calendario', 'bien', f'{len(filas)} eventos del {DESDE:%d-%m} al {HASTA:%d-%m}; {crm_ok} de personas activas de la app', crm_ok)
except SystemExit as e:
    fuente('crm', 'Zoho CRM · eventos del calendario', 'rota', f'zh.py: {e}')
except Exception as e:
    fuente('crm', 'Zoho CRM · eventos del calendario', 'rota', f'{type(e).__name__}: {e}'[:200])

# ------------------------------------------------------------------ 2. GHL de RO · citas de los calendarios de Tomás
REPARTO = os.path.join(HOME, 'Downloads/SETTERS_RO_2026-09-24/25_GHL_PRUEBA_SETTERS')
CALS = {'ChisJEQCj8fXSnML13AQ': ('Reunión de 45 min', 'venta'), 'gzgK7Mz7Al7G9bVZY9uO': ('15 minutos', 'venta'),
        'brkp8BflHwar8ffAtRLQ': ('Taller de la oferta', 'taller'), 'qIVWgA1ki8CHBRbRtxJo': ('15 min · curso Claude', 'venta'),
        'mWBSx8J4GcYQkWdEWF09': ('Reunión (calendario antiguo)', 'venta')}
ghl_n = 0
try:
    sys.path.insert(0, REPARTO)
    import repartir_setters as R
    from ghl_comun import LOC
    for cal, (nom, clase) in CALS.items():
        for e in R.eventos(cal, DESDE, HASTA):
            if e.get('appointmentStatus') == 'invalid': continue
            c = R.contacto(e.get('contactId')) if e.get('contactId') else {}
            nombre = ' '.join(x for x in [c.get('firstName'), c.get('lastName')] if x) or c.get('contactName') or ''
            empresa = c.get('companyName') or ''
            cref = cliente_de(empresa, nombre, e.get('title')) if clase == 'taller' or empresa else None
            if e.get('appointmentStatus') == 'cancelled':
                if cref:
                    canceladas.append({'id': f"ghl-{e['id']}", 'persona_id': 'tomas', 'fuente': 'ghl', 'inicio': iso(ts(e.get('startTime'))),
                                       'cliente_ref': cref, 'estado_cita': 'cancelled'})
                continue
            tipo = 'cliente' if cref else 'prospecto'
            setters = [t.split(':', 1)[1] for t in (c.get('tags') or []) if t.startswith('setter:')]
            base = {'fuente': 'ghl', 'inicio': iso(ts(e.get('startTime'))), 'fin': iso(ts(e.get('endTime'))), 'tipo': tipo,
                    'calendario': nom, 'estado_cita': e.get('appointmentStatus'),
                    'identidad_fuente': identidad_observada('ghl',str(e['id']),e.get('startTime'),e.get('endTime')),
                    'titulo': (f'{nom} · {CLI[cref]["nombre"]}' if cref else f'{nom} · {mascara(empresa or nombre)}'),
                    'cliente_ref': cref, 'cliente_nombre': CLI[cref]['nombre'] if cref else None,
                    'con_quien_m': mascara(nombre) if nombre else None, 'video': 'zoom',
                    'atajos': ([{'h': 'ghl', 'url': f"https://app.gohighlevel.com/v2/location/{LOC}/contacts/detail/{e.get('contactId')}"}] if e.get('contactId') else [])
                              + [{'h': 'ghl_calendario', 'url': f"https://app.gohighlevel.com/v2/location/{LOC}/calendars/view"}],
                    'origen': 'GoHighLevel de RO · calendarios de Tomás'}
            real = f'{nom} · {empresa or nombre}'.strip(' ·')
            alta({**base, 'id': f"ghl-{e['id']}", 'persona_id': 'tomas'}, real, nombre)
            ghl_n += 1
            for s in setters:
                pid = f'setter_{s}'
                if pid in P_ID:
                    alta({**base, 'id': f"ghl-{e['id']}-{s}", 'persona_id': pid, 'agendada_por_ti': True,
                          'titulo': f'Agendaste: {base["titulo"]}'}, f'Agendaste: {real}', nombre)
    fuente('ghl', 'GoHighLevel de RO · citas de venta y talleres', 'bien', f'{ghl_n} citas (sin canceladas) en {len(CALS)} calendarios de Tomás', ghl_n)
except BaseException as e:
    fuente('ghl', 'GoHighLevel de RO · citas de venta y talleres', 'rota', f'{type(e).__name__}: {e}'[:200])

# ------------------------------------------------------------------ 3. Zoom (grabadas, de M15)
zoom_n = 0
try:
    R15 = json.load(open(os.path.join(DATA, 'reuniones', 'reuniones.json')))
    vistas = set()
    for a in R15.get('asistencias', []):
        ini = dt.datetime.fromisoformat(f"{a['fecha']} {a.get('hora') or '00:00'}").replace(tzinfo=MAD)
        if ini < DESDE or ini > HASTA: continue
        pid = a.get('persona_id') or ALIAS.get(norm(a.get('persona') or a.get('anfitrion')))
        if not pid or (a['reunion'], pid) in vistas: continue
        vistas.add((a['reunion'], pid))
        cref = next((x for x in (a.get('cli'), a.get('cliente')) if x in CLI), None)
        tipo = 'cliente' if cref else ('interna' if a.get('ambito') == 'interna' else 'fuera')
        fin = ini + dt.timedelta(minutes=a.get('minutos_reunion') or 30)
        alta({'id': f"zoom-{a['reunion']}-{pid}", 'persona_id': pid, 'fuente': 'zoom', 'inicio': iso(ini), 'fin': iso(fin), 'tipo': tipo,
              'titulo': limpio(a.get('tema')) if tipo != 'fuera' else 'Reunión de Zoom con gente de fuera',
              'cliente_ref': cref, 'cliente_nombre': CLI[cref]['nombre'] if cref else None, 'video': 'zoom', 'celebrada': True,
              'con_ro': [x for x in (a.get('internos') or [])][:8],
              # Fecha/hora y duración del cache histórico pueden contener defaults: no certificar ventana.
              'identidad_fuente': identidad_observada('zoom',str(a['reunion']),None,None),
              'atajos': [{'h': 'zoom', 'url': (a.get('acta') or {}).get('enlace_grabacion')}] if (a.get('acta') or {}).get('enlace_grabacion') else [],
              'origen': 'Zoom de RO · reuniones grabadas'},
             a.get('tema'))
        zoom_n += 1
    fuente('zoom', 'Zoom de RO · reuniones grabadas', 'bien' if zoom_n else 'a_cero',
           f'{zoom_n} asistencias grabadas en la ventana. Las próximas reuniones de Zoom no se leen: a la app de Zoom le falta el permiso meeting:read:list_meetings:admin', zoom_n)
except Exception as e:
    fuente('zoom', 'Zoom de RO · reuniones grabadas', 'rota', f'{type(e).__name__}: {e}'[:200])

# ------------------------------------------------------------------ 4. Zoho Bookings y Zoho Calendar (directos)
# Llave canjeada por Tomás el 2-oct (17:10) con zohobookings.data.READ/CREATE y ZohoCalendar.calendar/event.READ.
book_n = cal_n = 0
try:
    sys.path.insert(0, os.path.join(HOME, 'RO_HERRAMIENTAS/zoho'))
    import zbookings as ZB
    if 'tk' in dir() and 'api' in dir():
        ZB._TOKEN['tk'] = (tk, api)          # la misma llave de acceso que el CRM: Zoho limita las peticiones seguidas
    try:
        for c in ZB.citas(DESDE.replace(tzinfo=None), HASTA.replace(tzinfo=None)):
            pid = persona_por_correo(c.get('staff_email'), c.get('staff_name'))
            if not pid or not c.get('inicio'): continue
            cref = cliente_de(c.get('customer_name'))
            if str(c.get('status') or '').startswith('cancel'):     # por si el lector de Bookings deja pasar las canceladas
                if cref:
                    canceladas.append({'id': f"bk-{c['booking_id'].lstrip('#')}", 'persona_id': pid, 'fuente': 'bookings', 'inicio': c['inicio'],
                                       'cliente_ref': cref, 'estado_cita': 'cancelled'})
                continue
            tipo = 'cliente' if cref else 'prospecto'
            alta({'id': f"bk-{c['booking_id'].lstrip('#')}", 'persona_id': pid, 'fuente': 'bookings', 'inicio': c['inicio'], 'fin': c['fin'], 'tipo': tipo,
                  'titulo': f"{c.get('service_name') or 'Cita'} · " + (CLI[cref]['nombre'] if cref else mascara(c.get('customer_name'))),
                  'identidad_fuente': identidad_observada('bookings',str(c['booking_id']),c.get('inicio'),c.get('fin'),zona=c.get('zona')),
                  'calendario': c.get('service_name'), 'estado_cita': {'upcoming': 'confirmed', 'yet_to_mark': 'sin_marcar', 'completed': 'showed', 'no_show': 'noshow'}.get(c.get('status'), c.get('status')),
                  'cliente_ref': cref, 'cliente_nombre': CLI[cref]['nombre'] if cref else None,
                  'con_quien_m': mascara(c.get('customer_name')), 'video': c.get('video'), 'reserva': c.get('booking_id'),
                  'atajos': [{'h': 'bookings', 'url': 'https://bookings.zoho.eu/'}], 'origen': 'Zoho Bookings'},
                 f"{c.get('service_name')} · {c.get('customer_name')}", c.get('customer_name'))
            book_n += 1
        fuente('bookings', 'Zoho Bookings · citas por persona', 'bien', f'{book_n} citas sin canceladas, de todo el personal', book_n)
    except Exception as e:
        fuente('bookings', 'Zoho Bookings · citas por persona', 'rota', f'{type(e).__name__}: {e}'[:200])
    try:
        for c in ZB.eventos_calendar(DESDE.replace(tzinfo=None), HASTA.replace(tzinfo=None)):
            if not c.get('inicio'): continue
            cref = cliente_de(c.get('titulo'))
            interna = not cref and re.search(r'(?i)\b(equipo|daily|interna|1:1|coordinaci|retro|heads)', c['titulo'])
            tipo = 'cliente' if cref else ('interna' if interna else 'evento')
            alta({'id': 'cal-' + __import__('hashlib').sha1(f"{c['uid']}|{c['inicio']}".encode()).hexdigest()[:12], 'persona_id': 'tomas', 'fuente': 'calendar', 'inicio': c['inicio'], 'fin': c['fin'],
                  'todo_el_dia': c['todo_el_dia'], 'tipo': tipo,
                  # UID puede contener correo; no exponerlo como ID original público.
                  'identidad_fuente': identidad_observada('calendar',c.get('uid'),c.get('inicio'),c.get('fin')),
                  'titulo': limpio(c['titulo']) if tipo in ('cliente', 'interna') else mascara_titulo(c['titulo']),
                  'cliente_ref': cref, 'cliente_nombre': CLI[cref]['nombre'] if cref else None,
                  'atajos': [{'h': 'calendar', 'url': c['enlace']}] if c.get('enlace') else [], 'origen': 'Zoho Calendar · calendario de Tomás'},
                 c['titulo'])
            cal_n += 1
        fuente('calendar', 'Zoho Calendar · eventos', 'bien', f'{cal_n} eventos del calendario de Tomás (la llave es suya: los de cada persona llegan con su propio acceso al publicar la app)', cal_n)
    except Exception as e:
        fuente('calendar', 'Zoho Calendar · eventos', 'rota', f'{type(e).__name__}: {e}'[:200])
except Exception as e:
    fuente('bookings', 'Zoho Bookings · citas por persona', 'rota', f'{type(e).__name__}: {e}'[:200])

# ------------------------------------------------------------------ salida
# Una cita se consolida sólo con referencia explícita o identidad canónica confirmada,
# mismo dueño/duración y sin conflictos. El horario o nombre privado no bastan.
try:
    from .duplicados import deduplicar
except ImportError:  # Ejecución como script, sin paquete.
    from duplicados import deduplicar
#199: ruta fija privada; ausencia/invalidación nunca autoriza coincidencias débiles.
ids_antes_crosswalk = {e['id'] for e in eventos}
eventos, resumen_crosswalk = integrar_crosswalk(eventos, os.path.join(AQUI,'_privado','crosswalk_confirmado.json'),AHORA.date().isoformat())
retiradas_crosswalk = ids_antes_crosswalk - {e['id'] for e in eventos}
eventos, fuera = deduplicar(eventos, privado)
fuera = set(fuera) | retiradas_crosswalk
quitadas = len(fuera)
# Zoom permanece independiente salvo identidad estricta compartida. No enlazar ±20min
# ni convertir una cita en celebrada por proximidad a una grabación.
for pid_, d in privado.items():
    for i in fuera:
        d['titulos'].pop(i, None); d['con_quien'].pop(i, None)
fuente('dedup', 'Citas con identidad compartida entre fuentes', 'bien',
       f'{quitadas} copias consolidadas con identidad confirmada; manifest {resumen_crosswalk["manifest_estado"]}. Coincidencias de hora/nombre y grabaciones sin vínculo confirmado conservadas', quitadas)
eventos.sort(key=lambda e: (e['inicio'] or '', e['persona_id']))
# Las setters que aún no tienen citas reciben la agenda vacía con su explicación (no una caja en blanco)
salida = {
    '_meta': {'generado': AHORA.strftime('%Y-%m-%d %H:%M'), 'hoy': AHORA.strftime('%Y-%m-%d'), 'desde': DESDE.strftime('%Y-%m-%d'),
              'hasta': HASTA.strftime('%Y-%m-%d'), 'jornada': {'inicio': '09:00', 'fin': '18:00', 'dias': [0, 1, 2, 3, 4]},
              'fuentes': fuentes, 'crosswalk': resumen_crosswalk,
              'nota': 'Fuentes parciales; pueden coexistir copias sin identidad compartida confirmada. Prospectos enmascarados; los nombres, sólo su dueño con «Ver nombres».'},
    'eventos': eventos,
    'canceladas': sorted(canceladas, key=lambda e: (e['inicio'] or '', e['persona_id'])),
}
os.makedirs(PRIV, exist_ok=True)
json.dump(salida, open(os.path.join(SAL, 'agenda.json'), 'w'), ensure_ascii=False, indent=1)
for pid, d in privado.items():
    json.dump({'nombres': {pid: {'titulos': d['titulos'], 'con_quien': d['con_quien']}}},
              open(os.path.join(PRIV, f'{pid}.json'), 'w'), ensure_ascii=False, indent=1)
from collections import Counter as C2
print('agenda ·', len(eventos), 'filas ·', dict(C2(e['fuente'] for e in eventos)), '·', dict(C2(e['tipo'] for e in eventos)))
print('por persona:', dict(C2(e['persona_id'] for e in eventos)))
for f in fuentes: print(' ', f['id'], f['estado'], f['detalle'])
