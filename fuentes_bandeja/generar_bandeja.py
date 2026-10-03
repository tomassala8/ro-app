#!/usr/bin/env python3
"""M3 · Bandeja · genera data/bandeja/bandeja.json (solo lectura de Desk y Zadarma).

Reutiliza la lógica del panel v27 de Mili (~/Downloads/PANEL_OPERACIONES_2026-10-01/build/build.py):
  · «pendiente» = último hilo ENTRANTE sin saliente posterior y ticket no cerrado (criterio de hilos_clientes.json);
    horas naturales contadas solo de lunes a viernes (hora de Madrid), como horasLVSinResponder.
  · ruido interno = filtro_ruido.py del panel (remitente @rankingonline, tomas@, avisos BOFU, setters, respuestas
    automáticas…) + la expresión _AUTO del panel («Automáticos y reenvíos»: zapier, RV:, newsletter…).
  · queja = expresión _QUEJA del panel.
  · llamadas perdidas = entrantes no contestadas de los últimos 5 días laborables que nadie devolvió (build.py 679-710),
    cruzadas con el cliente por los 6 últimos dígitos (telefonos_conocidos de zadarma_por_cliente.json).
  · triaje de tickets sin agente = triaje_desk.json del panel (propuesta seguro / dudoso).

Plan A en vivo: Desk (zh.py, llave de LECTURA) y Zadarma (zd.py, 1 consulta). Plan B: los ficheros del panel.
Uso:  python3 generar_bandeja.py            (en vivo, con plan B si algo falla)
      python3 generar_bandeja.py --ficheros (sin llamadas: solo lo último del panel)
Nada se escribe en Desk ni en Zadarma. Sin correos, teléfonos ni claves en la salida (escáner al final).
"""
import datetime as dt
import glob
import json
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
sys.path.insert(1, str(Path(__file__).resolve().parents[1]))  # C5: rutas y secretos en config.py
import config  # noqa: E402
PANEL = config.PANEL_OPERACIONES
V7 = PANEL / 'build'
CRUDO = PANEL / '_crudo'
SALIDA = APP / 'data/bandeja/bandeja.json'
sys.path.insert(0, str(config.HERRAMIENTAS / 'zoho'))
sys.path.insert(0, str(config.HERRAMIENTAS / 'zadarma'))
sys.path.insert(0, str(CRUDO / 'scripts'))
sys.path.insert(0, str(APP))

from filtro_ruido import clasifica  # noqa: E402  (mismo filtro que el panel)

EN_VIVO = '--ficheros' not in sys.argv
AHORA = dt.datetime.now()
HOY = AHORA.date()
DESK = 'https://desk.zoho.eu/api/v1'
DEP_CLIENTES = '157377000000741729'  # «Marketing Clientes.»
ESTADOS_ABIERTOS = ['Abierto', 'En espera', 'Escalado', 'Por resolver', 'Por responder', 'En Seguimiento (Cliente)']  # se sustituye por los de Desk con statusType ≠ Closed

# --- expresiones del panel v27 (build.py 673-674), sin cambios ---
_AUTO = re.compile(r'^\s*(cancelad[oa]|invitaci[oó]n|invitation|aceptad[oa]|rechazad[oa]|actualizad[oa])\s*:|elemento compartido|documento compartido|ha compartido|shared with you|zapier|newsletter|bolet[ií]n|webinar|unsubscribe|no-?reply|\[prueba\]|^\s*(rv|fw|fwd)\s*:|policy compliance|connection has expired|pago fallido|wetransfer', re.I)
# V2 (A-M11): boletines y circulares de marketing (del propio cliente o de terceros) NO son correos de cliente sin contestar.
# Se cuentan aparte, con los automáticos: ni suben los días sin contestar ni la gravedad del cliente.
_BOLETIN = re.compile(r'descúbrelo|descubre (c[oó]mo|cu[aá]nto)|en esta gu[ií]a|^\s*¿sabes (realmente|cu[aá]nto|qu[eé])|nota informativa|^\s*alerta\b|bolet[ií]n|newsletter|'
                      r'no te pierdas|inscr[ií]bete|ap[uú]ntate|masterclass|los \d+ (pecados|errores|claves)|darse de baja|webinar', re.I)
# Un encargo sobre el boletín del cliente («Revisión de la newsletter mensual», «Pedido de aprobación - Newsletters») SÍ es trabajo
_ENCARGO = re.compile(r'revisi[oó]n|aprobaci[oó]n|pedido|propuesta|preparar|enviar|textos? de|cambios', re.I)


def clasifica_asunto(asunto):
    """→ (auto, boletin): una sola regla para el generador y para --reclasificar."""
    encargo = bool(_ENCARGO.search(asunto))
    boletin = bool(_BOLETIN.search(asunto)) and not _QUEJA.search(asunto) and not encargo
    auto = boletin or (bool(_AUTO.search(asunto)) and not (encargo and re.search(r'newsletter|bolet[ií]n', asunto, re.I)))
    return auto, boletin


_QUEJA = re.compile(r'sin leads|urgente|decid|queja|molest|baja|cancel|reclam|no funciona|problema|error|insatisf', re.I)
# saneado de textos (la puerta de secretos no deja pasar correos ni teléfonos)
PLATAFORMAS = re.compile(r'@([\w-]+\.)*(anthropic\.com|atlassian\.com|elementor\.com|claude\.ai)$', re.I)
_CORREO = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')
_TEL = re.compile(r'(?:\+?\d[\d\s.\-]{7,}\d)')


def J(p, defecto=None):
    try:
        return json.load(open(p))
    except Exception:
        return defecto


def norm(t):
    t = unicodedata.normalize('NFKD', str(t or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', t)).strip()


def sanea(t, n=120):
    t = _TEL.sub('…', _CORREO.sub('[correo]', str(t or ''))).strip()
    return t[:n]


def horas_lv(desde, hasta=None):
    """Horas naturales solo de lunes a viernes entre dos datetime (como horasLVSinResponder del panel)."""
    hasta = hasta or AHORA
    if not desde or desde >= hasta:
        return 0.0
    total, t = 0.0, desde
    while t < hasta:
        fin_dia = dt.datetime.combine(t.date() + dt.timedelta(days=1), dt.time())
        tramo = min(fin_dia, hasta)
        if t.weekday() < 5:
            total += (tramo - t).total_seconds() / 3600
        t = tramo
    return round(total, 1)


def dias_lab_entre(a, b):
    """Días laborables (lunes a viernes) desde a hasta b, sin contar a."""
    n, d = 0, a
    while d < b:
        d += dt.timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def iso_local(s):
    """'2026-10-02T12:57:49.000Z' → datetime local de Madrid (UTC+2 en octubre, como el panel)."""
    if not s:
        return None
    try:
        d = dt.datetime.strptime(s[:19], '%Y-%m-%dT%H:%M:%S')
        return d + dt.timedelta(hours=2) if s.endswith('Z') else d
    except ValueError:
        return None


# ============================================================ mapas de la app
personas = J(APP / 'data/personas.json', [])
P_POR_NOMBRE = {}
for p in personas:
    n = norm(p.get('nombre'))
    if n:
        P_POR_NOMBRE[n] = p['id']
        P_POR_NOMBRE.setdefault(n.split()[0], p['id'])
P_NOMBRE = {p['id']: p.get('nombre') for p in personas}


def persona_de(nombre):
    n = norm(nombre)
    if not n:
        return None
    return P_POR_NOMBRE.get(n) or P_POR_NOMBRE.get(n.split()[0])


clientes_app = J(APP / 'data/clientes.json', [])
CLI = {c['id']: c for c in clientes_app}
PANEL_A_APP = {}
for f in glob.glob(str(APP / 'data/clientes/*.json')):
    c = J(f, {})
    if c.get('ids', {}).get('panel'):
        PANEL_A_APP[c['ids']['panel']] = c['id']
for c in clientes_app:
    PANEL_A_APP.setdefault(c['nombre'], c['id'])

puente = J(V7 / 'puente.json', {})
DESK_A_PANEL = {}
for n, p in puente.items():
    if p.get('excluir'):
        continue
    for k in p.get('desk') or []:
        DESK_A_PANEL[k.strip()] = n


GENERICOS = {'gmail.com', 'hotmail.com', 'outlook.com', 'yahoo.es', 'yahoo.com', 'icloud.com', 'live.com', 'hotmail.es', 'outlook.es', 'msn.com', 'me.com', 'telefonica.net'}
DOMINIO_A_APP = {}
for c in clientes_app:
    w = re.sub(r'^https?://(www\.)?', '', (c.get('web') or '').lower()).split('/')[0]
    if w and '.' in w:
        DOMINIO_A_APP[w] = c['id']
_dom_votos = defaultdict(Counter)


def cliente_de_cuenta(cuenta, dominio=None):
    pan = DESK_A_PANEL.get((cuenta or '').strip())
    if not pan and dominio:
        pan = DESK_A_PANEL.get('(sin cuenta) ' + dominio)
    if pan and PANEL_A_APP.get(pan):
        return PANEL_A_APP[pan]
    if dominio and dominio not in GENERICOS:
        if dominio in DOMINIO_A_APP:
            return DOMINIO_A_APP[dominio]
        v = _dom_votos.get(dominio)
        if v and len(v) == 1:
            return next(iter(v))
    return None


VERDAD = {c['cliente_id']: c for c in (J(APP / 'data/verdad/clientes.json', {}) or {}).get('clientes', [])}


def account_de(cid):
    """Account = verdad única (data/verdad/clientes.json → account); sin account, None."""
    rid = (VERDAD.get(cid) or {}).get('account')
    if not rid:
        return None, 'Sin account'
    return rid, P_NOMBRE.get(rid) or rid


# --solo-account: vuelve a sellar el account de cada fila con la verdad única actual (sin llamar a Desk ni a Zadarma)
if '--solo-account' in sys.argv:
    B_ = J(SALIDA, {})
    for k in ('correos', 'llamadas', 'triaje'):
        for x in B_.get(k, []):
            if x.get('cliente_id'):
                rid, txt = account_de(x['cliente_id'])
                if k == 'triaje':
                    x['agente_propuesto_id'], x['agente_propuesto'] = rid or x.get('agente_propuesto_id'), txt if rid else x.get('agente_propuesto')
                else:
                    x['account_id'], x['account'] = rid, txt
    tmp = SALIDA.with_suffix('.tmp')
    tmp.write_text(json.dumps(B_, ensure_ascii=False, indent=1))
    os.replace(tmp, SALIDA)
    print('account resellado con la verdad única')
    sys.exit(0)

def resumen_por_cliente(correos, llamadas, generado, fuentes):
  pc = {}
  for c in correos:
      if not c['cliente_id'] or c['auto']:
          continue
      r_ = pc.setdefault(c['cliente_id'], {'cliente_id': c['cliente_id'], 'sin_contestar': 0, 'mas_48': 0, 'entre_24_48': 0, 'quejas': 0,
                                            'mas_de_un_mes': 0, 'horas_max': 0, 'dias_laborables_max': 0, 'mas_antiguo': None, 'llamadas_sin_devolver': 0})
      r_['sin_contestar'] += 1
      r_['mas_48'] += c['gravedad'] == 'rojo'
      r_['entre_24_48'] += c['gravedad'] == 'ambar'
      r_['quejas'] += c['queja']
      r_['mas_de_un_mes'] += c['viejo']
      if c['horas'] >= r_['horas_max']:
          r_['horas_max'] = c['horas']
          r_['dias_laborables_max'] = c['dias_laborables']
          r_['mas_antiguo'] = {'numero': c['numero'], 'asunto': c['asunto'], 'url': c['url'], 'desde': c['desde']}
  for l_ in llamadas:
      if l_['cliente_id']:
          pc.setdefault(l_['cliente_id'], {'cliente_id': l_['cliente_id'], 'sin_contestar': 0, 'mas_48': 0, 'entre_24_48': 0, 'quejas': 0, 'mas_de_un_mes': 0,
                                           'horas_max': 0, 'dias_laborables_max': 0, 'mas_antiguo': None, 'llamadas_sin_devolver': 0})['llamadas_sin_devolver'] += l_['llamadas']
  return {'formato': 1, 'generado': generado, 'fuentes': fuentes, 'regla': 'la de la Bandeja: sin automáticos ni ruido, horas y días laborables', 'clientes': sorted(pc.values(), key=lambda r_: -r_['horas_max'])}


# --reclasificar (V2): vuelve a aplicar automáticos, boletines y quejas a lo último escrito (sin llamar a Desk ni a Zadarma)
RECLASIFICAR = '--reclasificar' in sys.argv
if RECLASIFICAR:
    B_ = J(SALIDA, {})
    for x in B_.get('correos', []):
        a_ = x.get('asunto') or ''
        x['auto'], x['boletin'] = clasifica_asunto(a_)
        x['queja'] = bool(_QUEJA.search(a_)) and not x['auto']
    cs = B_.get('correos', [])
    B_.setdefault('resumen', {}).update({'correos': len(cs), 'rojo': sum(1 for c in cs if c['gravedad'] == 'rojo' and not c['auto']),
        'ambar': sum(1 for c in cs if c['gravedad'] == 'ambar' and not c['auto']), 'quejas': sum(1 for c in cs if c['queja']),
        'automaticos': sum(1 for c in cs if c['auto']), 'boletines': sum(1 for c in cs if c.get('boletin'))})
    pcl = resumen_por_cliente(cs, B_.get('llamadas', []), B_.get('generado'), B_.get('fuentes', {}))
    for dst, obj in ((SALIDA, B_), (SALIDA.with_name('por_cliente.json'), pcl)):
        tmp = dst.with_suffix('.tmp')
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1))
        os.replace(tmp, dst)
    print(f"reclasificado: {B_['resumen']['automaticos']} automáticos ({B_['resumen']['boletines']} boletines)")
    sys.exit(0)

# hilos del panel: número → cuenta y remitente (para clasificar sin descargar hilos)
hilos = J(CRUDO / 'desk/hilos_clientes.json', {})
POR_NUMERO = {t['numero']: t for t in (hilos.get('porTicket') or [])}

def slug(t):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', norm(t))).strip('-')


def url_desk(tid, departamento='Marketing Clientes.'):
    """Formato nuevo de Desk (26 parte C). «Marketing Clientes.» es «marketing-clientes-1» porque hay otro sin punto."""
    dep = 'marketing-clientes-1' if (departamento or '').strip() == 'Marketing Clientes.' else slug(departamento or 'marketing clientes')
    return f'https://desk.zoho.eu/agent/rankingonline836/{dep}/tickets/details/{tid}'


def url_desk_de(antigua, departamento='Marketing Clientes.'):
    m = re.search(r'(\d{15,})', antigua or '')
    return url_desk(m.group(1), departamento) if m else antigua


# ============================================================ Desk en vivo
fuentes = {}
ERROR_DESK = None
departamentos = []
correos_vivos = None
sin_agente_vivos = []


def desk_vivo():
    import zh
    tk, _ = zh.acceso()

    def g(ruta):
        req = urllib.request.Request(DESK + ruta, headers={'Authorization': 'Zoho-oauthtoken ' + tk, 'orgId': oid})
        try:
            r = urllib.request.urlopen(req, timeout=60)
            b = r.read()
            return json.loads(b) if b else {'data': []}
        except urllib.error.HTTPError as e:
            return {'_error': e.code}

    req = urllib.request.Request(DESK + '/organizations', headers={'Authorization': 'Zoho-oauthtoken ' + tk})
    oid = str(json.load(urllib.request.urlopen(req, timeout=30))['data'][0]['id'])
    global ESTADOS_ABIERTOS
    campos = g('/organizationFields?module=tickets').get('data', [])
    st_campo = next((f for f in campos if f.get('apiName') == 'status'), None)
    if st_campo:
        ESTADOS_ABIERTOS = [v['value'] for v in st_campo.get('allowedValues', []) if v.get('statusType') != 'Closed']
    deps = g('/departments?limit=100').get('data', [])
    tickets = []
    for d in deps:
        info = {'nombre': d['name'].strip(), 'activo': bool(d.get('isEnabled')), 'legible': False, 'abiertos': None}
        n_dep = 0
        for st in ESTADOS_ABIERTOS:
            frm = 1
            while True:
                r = g(f"/tickets?departmentId={d['id']}&status={urllib.parse.quote(st)}&limit=100&from={frm}&include=assignee")
                if '_error' in r:
                    break
                info['legible'] = True
                lote = r.get('data', [])
                for t in lote:
                    t['_dep'] = info['nombre']
                tickets += lote
                n_dep += len(lote)
                if len(lote) < 100:
                    break
                frm += 100
        info['abiertos'] = n_dep if info['legible'] else None
        departamentos.append(info)
    cache_f = AQUI / '_cache_cuentas_desk.json'   # id de cuenta de Desk → nombre de la empresa (sin datos personales)
    cuentas = J(cache_f, {}) or {}

    def nombre_cuenta(t):
        h = POR_NUMERO.get(t['ticketNumber'])
        if h and h.get('accountName'):
            return h['accountName']
        aid = t.get('accountId')
        if not aid:
            return None
        if aid not in cuentas:
            cuentas[aid] = (g(f'/accounts/{aid}') or {}).get('accountName')
        return cuentas[aid]

    pend = []
    try:
        for t in tickets:
            nombre_cuenta(t)
        cache_f.write_text(json.dumps(cuentas, ensure_ascii=False))
    except Exception:
        pass
    for t in tickets:
        lt = t.get('lastThread') or {}
        cuenta = nombre_cuenta(t)
        base = {'numero': t['ticketNumber'], 'asunto': t.get('subject') or '', 'url': url_desk(t['id'], t['_dep']),
                'estado_desk': t.get('status'), 'departamento': t['_dep'], 'cuenta': cuenta, 'contactoEmail': t.get('email') or '',
                'asignado': ' '.join(x for x in [(t.get('assignee') or {}).get('firstName'), (t.get('assignee') or {}).get('lastName')] if x) or None,
                'entrante': iso_local(t.get('customerResponseTime')), 'creado': iso_local(t.get('createdTime'))}
        if not t.get('assigneeId'):
            sin_agente_vivos.append(base)
        if lt.get('direction') == 'in' and not lt.get('isDraft'):
            pend.append(base)
    return pend


if EN_VIVO:
    try:
        correos_vivos = desk_vivo()
        fuentes['desk'] = {'fuente': 'Zoho Desk', 'plan': 'en vivo', 'hora': AHORA.strftime('%Y-%m-%d %H:%M'), 'estado': 'bien',
                           'nota': f"{sum(1 for d in departamentos if d['legible'])} de {len(departamentos)} departamentos legibles con la llave de lectura"}
    except Exception as e:  # plan B
        print('Desk en vivo no disponible, uso el último dato bueno:', type(e).__name__, str(e)[:120])
        correos_vivos = None
        departamentos.clear()          # lo que se leyó a medias antes del fallo no vale
        sin_agente_vivos.clear()
        ERROR_DESK = f'{type(e).__name__}: {sanea(str(e), 100)}'

# Auditoría 35 (A5): sin Desk en vivo, la Bandeja vuelve al dato bueno MÁS RECIENTE: su propia salida anterior si es
# más nueva que la del panel v27 (antes volvía siempre al panel, p. ej. al de las 04:59 aunque hubiera uno en vivo de
# las 18:00). La hora que se enseña es la del dato, y «hora_error» apunta el fallo de esta vuelta (aviso de la tubería).
PREVIO = J(SALIDA, {}) or {}
_pd = (PREVIO.get('fuentes') or {}).get('desk') or {}
HORA_PANEL = (hilos.get('generado') or '')[:16].replace('T', ' ')
USAR_PREVIO = (correos_vivos is None and isinstance(PREVIO.get('correos'), list) and isinstance(PREVIO.get('triaje'), list)
               and str(_pd.get('hora') or '') > HORA_PANEL)

# ============================================================ correos sin contestar
correos, ruido = [], Counter()


def fila_correo(numero, asunto, cid, horas, desde, url, asignado, estado_desk, departamento, dominio):
    acc_id, acc_txt = account_de(cid) if cid else (None, 'sin cliente')
    auto, boletin = clasifica_asunto(asunto)
    queja = bool(_QUEJA.search(asunto)) and not auto
    dias_nat = (HOY - desde.date()).days if desde else None
    dias_lab = dias_lab_entre(desde.date(), HOY) if desde else None
    fila = {
        'id': 't-' + numero, 'canal': 'correo', 'numero': numero, 'asunto': sanea(asunto),
        'cliente_id': cid, 'cliente': (CLI.get(cid) or {}).get('nombre') if cid else None,
        'account_id': acc_id, 'account': acc_txt, 'asignado': asignado, 'asignado_id': persona_de(asignado),
        'horas': horas, 'desde': desde.strftime('%Y-%m-%d %H:%M') if desde else None, 'dias_laborables': dias_lab,
        'gravedad': 'rojo' if horas > 48 else 'ambar' if horas > 24 else 'verde',
        'queja': queja, 'auto': auto, 'boletin': boletin, 'viejo': bool(dias_lab is not None and dias_lab > 22 and not queja),
        'estado_desk': estado_desk, 'departamento': departamento, 'dominio': dominio, 'url': url,
    }
    if not cid:
        fila['persona_id'] = 'mili'  # sin cliente: lo triagea Operaciones (recorte del servidor por persona_id)
    return fila


if correos_vivos is not None:
    for t in correos_vivos + sin_agente_vivos:
        dom = t['contactoEmail'].split('@')[-1].lower() if '@' in t['contactoEmail'] else None
        cid0 = cliente_de_cuenta(t['cuenta'])
        if dom and cid0 and dom not in GENERICOS:
            _dom_votos[dom][cid0] += 1
    for t in correos_vivos:
        clase, motivo = clasifica({'contactoEmail': t['contactoEmail'], 'asunto': t['asunto'], 'accountName': t['cuenta']})
        if clase != 'ruido interno' and PLATAFORMAS.search(t['contactoEmail']):
            clase, motivo = 'ruido interno', 'plataforma (Atlassian, Anthropic, Elementor…)'
        if clase == 'ruido interno':
            ruido[motivo] += 1
            continue
        dominio = t['contactoEmail'].split('@')[-1].lower() if '@' in t['contactoEmail'] else None
        cid = cliente_de_cuenta(t['cuenta'], dominio)
        dominio = t['contactoEmail'].split('@')[-1].lower() if '@' in t['contactoEmail'] else None
        correos.append(fila_correo(t['numero'], t['asunto'], cid, horas_lv(t['entrante']), t['entrante'], t['url'],
                                   t['asignado'], t['estado_desk'], t['departamento'], dominio))
    hora_desk = fuentes['desk']['hora']
elif USAR_PREVIO:
    for x in PREVIO['correos']:
        try:
            desde = dt.datetime.strptime(x['desde'], '%Y-%m-%d %H:%M') if x.get('desde') else None
        except ValueError:
            desde = None
        correos.append(fila_correo(x['numero'], x.get('asunto') or '', x.get('cliente_id'), horas_lv(desde) if desde else float(x.get('horas') or 0),
                                   desde, x.get('url'), x.get('asignado'), x.get('estado_desk'), x.get('departamento'), x.get('dominio')))
    ruido.update(PREVIO.get('ruido') or {})
    departamentos.extend(PREVIO.get('departamentos') or [])
    hora_desk = str(_pd.get('hora'))
    fuentes['desk'] = {'fuente': 'Zoho Desk', 'plan': 'último dato bueno de la app', 'hora': hora_desk, 'estado': 'dato_viejo',
                       'nota': f"Sin conexión en vivo: los correos de la última lectura buena ({hora_desk}), más reciente que la del panel ({HORA_PANEL or 'sin hora'}). Las horas sin contestar se recalculan; lo contestado después no se ve hasta que vuelva Desk."}
else:
    d = J(V7 / 'datos.json', {})
    for x in (d.get('v7') or {}).get('bandeja', []):
        cid = PANEL_A_APP.get(x.get('cliente'))
        desde = dt.datetime.strptime(x['desde'], '%Y-%m-%d') if x.get('desde') else None
        correos.append(fila_correo(x['numero'], x.get('asunto') or '', cid, float(x.get('horas') or 0), desde, url_desk_de(x.get('url')),
                                   x.get('asignado'), 'Abierto', 'Marketing Clientes.', None))
    hora_desk = (hilos.get('generado') or '')[:16].replace('T', ' ')
    fuentes['desk'] = {'fuente': 'Zoho Desk', 'plan': 'fichero del panel', 'hora': hora_desk, 'estado': 'dato_viejo',
                       'nota': 'Sin conexión en vivo: bandeja del panel v27 (solo «Marketing Clientes.», últimos 30 días).'}

correos.sort(key=lambda x: (x['auto'], not x['queja'], -(x['horas'] or 0)))

# ============================================================ triaje: tickets sin agente
triaje_panel = J(V7 / 'triaje_desk.json', {})
PROP = {t['numero']: t for t in triaje_panel.get('tickets', [])}
triaje = []
fuente_triaje = sin_agente_vivos if correos_vivos is not None else [] if USAR_PREVIO else [
    {'numero': t['numero'], 'asunto': t['asunto'], 'url': t['url'], 'creado': dt.datetime.strptime(t['fecha'], '%Y-%m-%d'),
     'entrante': None, 'contactoEmail': '', 'cuenta': None, 'departamento': 'Marketing Clientes.', '_url_vieja': True}
    for t in triaje_panel.get('tickets', []) if t.get('propuesta') in ('seguro', 'dudoso')]
for t in fuente_triaje:
    pr = PROP.get(t['numero']) or {}
    if pr.get('propuesta') == 'ruido':
        ruido['triaje · ruido'] += 1
        continue
    clase, motivo = clasifica({'contactoEmail': t.get('contactoEmail', ''), 'asunto': t['asunto'], 'accountName': t.get('cuenta')})
    if clase == 'ruido interno' and not pr:
        ruido[motivo] += 1
        continue
    _d = t.get('contactoEmail', '').split('@')[-1].lower() if '@' in t.get('contactoEmail', '') else None
    cid = cliente_de_cuenta(t.get('cuenta'), _d) or PANEL_A_APP.get(pr.get('cliente'))
    if pr.get('propuesta') == 'sin_cliente':
        cid = None
    acc_id, acc_txt = account_de(cid) if cid else (None, None)
    prop_id = acc_id or persona_de(pr.get('agente_propuesto'))
    ref = t.get('entrante') or t.get('creado')
    fila = {'id': 'g-' + t['numero'], 'numero': t['numero'], 'asunto': sanea(t['asunto']), 'cliente_id': cid,
            'cliente': (CLI.get(cid) or {}).get('nombre') if cid else None,
            'propuesta': pr.get('propuesta') or ('seguro' if cid else 'sin_cliente'),
            'motivo': sanea(pr.get('motivo') or ('cuenta de Desk del cliente' if cid else 'sin cuenta de cliente en Desk'), 140),
            'agente_propuesto_id': prop_id, 'agente_propuesto': P_NOMBRE.get(prop_id) or acc_txt or pr.get('agente_propuesto'),
            'fecha': ref.strftime('%Y-%m-%d') if ref else None, 'dias': dias_lab_entre(ref.date(), HOY) if ref else None,
            'url': url_desk_de(t['url']) if t.get('_url_vieja') else t['url'], 'departamento': t.get('departamento')}
    if not cid:
        fila['persona_id'] = 'mili'
    triaje.append(fila)
if USAR_PREVIO:
    triaje = list(PREVIO['triaje'])
if EN_VIVO and correos_vivos is None:
    fuentes['desk'].update({'error': ERROR_DESK or 'sin respuesta', 'hora_error': AHORA.strftime('%Y-%m-%d %H:%M')})
triaje.sort(key=lambda x: ({'seguro': 0, 'dudoso': 1}.get(x['propuesta'], 2), x['dias'] or 0))

# ============================================================ llamadas sin devolver (Zadarma)
llam = []
ERROR_ZADARMA = None
if EN_VIVO:
    try:
        import zd
        filas = zd.agrupar(zd.llamadas_pbx(AHORA - dt.timedelta(days=9), AHORA))
        for f in filas:
            llam.append({'inicio': f.get('callstart', ''), 'sentido': zd.sentido(f), 'numero': zd.numero_externo(f) or '',
                         'estado': zd.ESTADOS.get(f.get('disposition'), f.get('disposition')), 'quien': zd.quien(f),
                         'extension': zd.extension(f), 'segundos': int(f.get('seconds') or 0)})
        fuentes['zadarma'] = {'fuente': 'Zadarma', 'plan': 'en vivo', 'hora': AHORA.strftime('%Y-%m-%d %H:%M'), 'estado': 'bien', 'nota': None}
    except Exception as e:
        print('Zadarma en vivo no disponible, uso el crudo del panel:', type(e).__name__, str(e)[:120])
        llam = []
        ERROR_ZADARMA = f'{type(e).__name__}: {sanea(str(e), 100)}'
USAR_PREVIO_Z = False
if not llam:
    zc = J(V7 / 'zadarma_crudo.json', {})
    hora_panel_z = ((zc.get('_meta') or {}).get('generado') or '')[:16].replace('T', ' ')
    _pz = (PREVIO.get('fuentes') or {}).get('zadarma') or {}
    # Auditoría 35: sin Zadarma en vivo, el dato bueno MÁS RECIENTE (las llamadas de la vuelta anterior si son más
    # nuevas que el crudo del panel), igual que con Desk.
    USAR_PREVIO_Z = isinstance(PREVIO.get('llamadas'), list) and str(_pz.get('hora') or '') > hora_panel_z
    if USAR_PREVIO_Z:
        fuentes['zadarma'] = {'fuente': 'Zadarma', 'plan': 'último dato bueno de la app', 'hora': str(_pz.get('hora')), 'estado': 'dato_viejo',
                              'nota': f"Sin conexión en vivo: las llamadas de la última lectura buena ({_pz.get('hora')}), más reciente que la del panel ({hora_panel_z or 'sin hora'}). Las horas se recalculan; lo devuelto después no se ve hasta que vuelva Zadarma."}
    else:
        for k, v in zc.items():
            if isinstance(v, dict) and isinstance(v.get('llamadas'), list):
                llam += v['llamadas']
        fuentes['zadarma'] = {'fuente': 'Zadarma', 'plan': 'fichero del panel', 'hora': hora_panel_z,
                              'estado': 'dato_viejo', 'nota': 'Sin conexión en vivo: llamadas del panel v27.'}
    if EN_VIVO and ERROR_ZADARMA:
        fuentes['zadarma'].update({'error': ERROR_ZADARMA, 'hora_error': AHORA.strftime('%Y-%m-%d %H:%M')})
llam.sort(key=lambda x: x['inicio'])

zpc = J(V7 / 'zadarma_por_cliente.json', {})
EXT = (zpc.get('_meta') or {}).get('_extensiones', {})
tel_cli = defaultdict(set)
for n2, L2 in zpc.items():
    if n2.startswith('_') or not isinstance(L2, dict):
        continue
    for t2 in L2.get('telefonos_conocidos') or []:
        tel_cli[re.sub(r'\D', '', str(t2))[-6:]].add(n2)
lim = HOY
k3 = 0
while k3 < 5:
    lim -= dt.timedelta(days=1)
    if lim.weekday() < 5:
        k3 += 1
dig = lambda s: re.sub(r'\D', '', s or '')
# Por número: lo pendiente son las entrantes sin contestar posteriores al último contacto CONTESTADO (en cualquier
# sentido). Un intento nuestro sin respuesta no la da por devuelta (revisión 22, I-13). 0 s también cuenta.
por_num = defaultdict(list)
for x in llam:
    u6 = dig(x['numero'])[-6:]
    if u6:
        por_num[u6].append(x)
grupos = {}
for u6, xs in por_num.items():
    xs.sort(key=lambda y: y['inicio'])
    ult_ok = max((y['inicio'] for y in xs if y['estado'] == 'contestada'), default='')
    pend = [y for y in xs if y['sentido'] == 'entrante' and y['estado'] != 'contestada' and y['inicio'] > ult_ok]
    pend = [y for y in pend if dt.date.fromisoformat(y['inicio'][:10]) >= lim]
    if not pend:
        continue
    intentos = sum(1 for y in xs if y['sentido'] == 'saliente' and y['inicio'] > pend[0]['inicio'])
    cl = sorted(tel_cli.get(u6, []))
    cp = cl[0] if len(cl) == 1 else None
    sono = next((EXT.get(str(y.get('extension'))) for y in pend if EXT.get(str(y.get('extension')))), None)
    k_ = cp or u6
    g_ = grupos.setdefault(k_, {'cliente_panel': cp, 'u6': u6, 'n': 0, 'primera': pend[0]['inicio'][:16], 'cuando': pend[-1]['inicio'][:16], 'sono': sono, 'intentos': 0})
    g_['n'] += len(pend)
    g_['intentos'] += intentos
    g_['primera'] = min(g_['primera'], pend[0]['inicio'][:16])
    g_['cuando'] = max(g_['cuando'], pend[-1]['inicio'][:16])
llamadas = []
for k_, g_ in grupos.items():
    cid = PANEL_A_APP.get(g_['cliente_panel']) if g_['cliente_panel'] else None
    acc_id, acc_txt = account_de(cid) if cid else (None, 'sin cliente')
    ult = dt.datetime.strptime(g_['cuando'], '%Y-%m-%d %H:%M')
    h_ = horas_lv(dt.datetime.strptime(g_['primera'], '%Y-%m-%d %H:%M'))
    fila = {'id': 'z-' + (cid or g_['u6']), 'canal': 'llamada', 'cliente_id': cid,
            'cliente': (CLI.get(cid) or {}).get('nombre') if cid else None,
            'numero_oculto': '··· ' + g_['u6'], 'llamadas': g_['n'], 'intentos_nuestros': g_['intentos'], 'ultima': g_['cuando'], 'primera': g_['primera'],
            'dias_laborables': dias_lab_entre(dt.date.fromisoformat(g_['primera'][:10]), HOY), 'url': 'https://my.zadarma.com/mystatistics/',
            'sono_a': g_['sono'], 'sono_a_id': persona_de(g_['sono']), 'account_id': acc_id, 'account': acc_txt,
            'horas': h_, 'gravedad': 'rojo' if h_ > 48 else 'ambar' if h_ > 24 else 'verde', 'dia': ult.strftime('%Y-%m-%d')}
    if not cid:
        fila['persona_id'] = 'mili'
    llamadas.append(fila)
if USAR_PREVIO_Z:
    llamadas = []
    for x in PREVIO['llamadas']:
        x = dict(x)
        try:
            h_ = horas_lv(dt.datetime.strptime(x['primera'], '%Y-%m-%d %H:%M'))
            x.update({'horas': h_, 'gravedad': 'rojo' if h_ > 48 else 'ambar' if h_ > 24 else 'verde',
                      'dias_laborables': dias_lab_entre(dt.date.fromisoformat(x['primera'][:10]), HOY)})
        except (KeyError, TypeError, ValueError):
            pass
        if x.get('cliente_id'):
            x['account_id'], x['account'] = account_de(x['cliente_id'])
        llamadas.append(x)
llamadas.sort(key=lambda x: (x['cliente_id'] is None, -x['horas']))

# ============================================================ firmas de Desk (solo si existe, sin la imagen)
firmas = {}
ff = J(config.HERRAMIENTAS / 'servidor_panel/firmas/firmas.json', {})
ALIAS_CORREO = {'cbravin': 'constanza', 'milagros': 'mili'}
for correo, v in ff.items():
    loc = correo.split('@')[0]
    pid = ALIAS_CORREO.get(loc) or persona_de(loc) or (loc if loc in P_NOMBRE else None)
    if pid:
        firmas[pid] = bool((v or {}).get('html'))

# ============================================================ salida
out = {
    'formato': 1,
    'generado': AHORA.strftime('%Y-%m-%d %H:%M'),
    'fuentes': fuentes,
    'departamentos': departamentos or [{'nombre': 'Marketing Clientes.', 'activo': True, 'legible': True, 'abiertos': None}],
    'umbrales': {'ambar_h': 24, 'rojo_h': 48, 'decision': 'D-29', 'horas': 'naturales de lunes a viernes desde el último correo del cliente'},
    'criterios': {
        'pendiente': 'el último mensaje del ticket es del cliente (no borrador) y el ticket no está cerrado',
        'ruido': 'filtro_ruido.py del panel: remitente @rankingonline, tomas@, avisos BOFU, candidaturas de setter, respuestas automáticas, alertas y notificaciones',
        'automaticos': 'expresión _AUTO del panel (zapier, newsletter, RV:/FW:, no-reply, wetransfer…) y los boletines y circulares de marketing («¿Sabes…? Descúbrelo en esta guía», «Nota informativa»): van aparte en «Automáticos y reenvíos» y no cuentan como correo de cliente sin contestar',
        'queja': 'expresión _QUEJA del panel (sin leads, urgente, baja, cancelar, reclamar, no funciona, problema…)',
        'llamadas': 'entrantes no contestadas (también las de 0 s) de los últimos 5 días laborables sin ninguna llamada contestada después con ese número; un intento nuestro sin respuesta no cuenta como devuelta',
        'estados': 'todos los estados de Desk que no son de tipo cerrado (Abierto, En espera, Escalado, Por resolver, Por responder, En seguimiento…)',
        'dias': 'siempre laborables (lunes a viernes), igual que las horas de la regla 24/48 h',
        'mas_de_un_mes': 'más de 22 días laborables sin respuesta; las quejas nunca van ahí',
        'sin_cliente': 'filas sin cliente_id van con persona_id = mili: solo las ven Operaciones y Dirección',
    },
    'firmas': firmas,
    'resumen': {
        'correos': len(correos), 'rojo': sum(1 for c in correos if c['gravedad'] == 'rojo' and not c['auto']),
        'ambar': sum(1 for c in correos if c['gravedad'] == 'ambar' and not c['auto']),
        'quejas': sum(1 for c in correos if c['queja']), 'automaticos': sum(1 for c in correos if c['auto']),
        'llamadas': len(llamadas), 'sin_agente': len(triaje), 'ruido': sum(ruido.values()),
    },
    'ruido': dict(ruido.most_common()),
    'correos': correos,
    'llamadas': llamadas,
    'triaje': triaje,
    'whatsapp': {'estado': 'sin_conectar', 'espera': 'W6', 'nota': 'Chats uno a uno con la coexistencia de WhatsApp Business (vía GHL), no antes del 16-oct. Los grupos siguen en el móvil.'},
}

# resumen por cliente: la misma regla para la ficha (auditoría 28, E-07)
por_cliente = resumen_por_cliente(correos, llamadas, out['generado'], fuentes)


# puerta de secretos antes de escribir
import escaner_secretos as E  # noqa: E402
tmp = SALIDA.with_suffix('.tmp')
SALIDA.parent.mkdir(parents=True, exist_ok=True)
tmp.write_text(json.dumps(out, ensure_ascii=False, indent=1))
hallazgos = E.escanear_fichero(tmp)
if hallazgos:
    tmp.unlink()
    print('PUERTA DE SECRETOS: no se escribe nada.', hallazgos[:5])
    sys.exit(2)
os.replace(tmp, SALIDA)
tmp2 = SALIDA.with_name('por_cliente.tmp')
tmp2.write_text(json.dumps(por_cliente, ensure_ascii=False, indent=1))
if E.escanear_fichero(tmp2):
    tmp2.unlink()
    print('PUERTA DE SECRETOS: por_cliente.json no se escribe.')
    sys.exit(2)
os.replace(tmp2, SALIDA.with_name('por_cliente.json'))
r = out['resumen']
print(f"bandeja.json · Desk {fuentes['desk']['plan']} ({hora_desk}) · Zadarma {fuentes['zadarma']['plan']}")
print(f"  correos {r['correos']} (rojo {r['rojo']}, ámbar {r['ambar']}, quejas {r['quejas']}, automáticos {r['automaticos']}) · ruido fuera {r['ruido']}")
print(f"  llamadas sin devolver {r['llamadas']} · sin agente {r['sin_agente']} · departamentos legibles {sum(1 for d in out['departamentos'] if d['legible'])}/{len(out['departamentos'])}")
