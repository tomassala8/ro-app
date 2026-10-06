#!/usr/bin/env python3
"""E6 · Setters, ventas de RO y outreach · generador de data/ventas_ro/*.json (SOLO LECTURA).

Uso:
  python3 fuentes_ventas/generar_ventas_ro.py            → lee GHL, Zadarma, Snov y el panel v29 y escribe data/ventas_ro/
  python3 fuentes_ventas/generar_ventas_ro.py --sin-zadarma --sin-snov   (si hay prisa o no hay cupo)

Fuentes (todas en lectura; nada se escribe en ninguna herramienta):
  · GoHighLevel, subcuenta de RO: token GHL_PIT_NEW de ~/RO_BANDEJA_GHL/config/ghl.env, a través de las funciones
    de lectura de ~/Downloads/SETTERS_RO_2026-09-24/25_GHL_PRUEBA_SETTERS/repartir_setters.py (mismo alcance y mismas
    exclusiones que el reparto real del lunes 5-oct). Solo GET y POST /contacts/search (que es una búsqueda).
    No se usa la app de agencia (su refresh token rota en cada uso y no hace falta para la subcuenta de RO).
  · Zadarma: ~/RO_HERRAMIENTAS/zadarma/zd.py, UNA consulta de estadísticas (cupo: 3 por minuto).
  · Snov.io: ~/RO_HERRAMIENTAS/snov/sv.py (campañas y respuestas).
  · Panel de resultados de RO (v29): ~/Downloads/PANEL_RESULTADOS_RO_2026-09-18/ENTREGA/dataset_ro.json y frescura.json.
  · Outreach de clientes: ~/Downloads/MILI_PANEL_Y_FEEDBACK_2026-10-02/panel_v7/outreach_clientes.json (cifras, sin notas).

Salida:
  data/ventas_ro/setters.json, ventas_ro.json, outreach.json, meta.json  → datos de leads ENMASCARADOS
  data/ventas_ro/_privado/setter_<clave>.json, ventas_tomas.json, outreach_respuestas.json
      → nombre, despacho y teléfono completos SOLO de los leads de esa persona. Prueba local: nunca a GitHub ni a publicar.
"""
import datetime as dt, json, os, re, sys, unicodedata, urllib.parse, hashlib, traceback
from zoneinfo import ZoneInfo

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
SALIDA = os.path.join(RAIZ, 'data', 'ventas_ro')
PRIV = os.path.join(SALIDA, '_privado')
sys.path.insert(1, RAIZ)  # C5: rutas en config.py
import config  # noqa: E402
HOME = str(config.HOME)
REPARTO = str(config.SETTERS_REPARTO)
PANEL = str(config.PANEL_RESULTADOS)
OUTREACH_CLI = str(config.MILI_PANEL_V7 / 'outreach_clientes.json')
MAD = ZoneInfo('Europe/Madrid')
AHORA = dt.datetime.now(MAD)
HOY = AHORA.date()
ARGS = set(sys.argv[1:])

# Extensiones de Zadarma de cada setter: POR CONFIRMAR. La 107 y la 110 (memoria del 1-oct) están desconectadas o son
# de Lourdes según la auditoría de incidencias. Hasta que Tomás las confirme, ext = None y el marcador sale «sin dato».
def setters_de_personas():
    """L-09: las setters son las personas con el puesto «setters» de data/personas.json, con su `clave_setter`
    (la de su etiqueta `setter:<clave>` en GHL y la de su fichero `_privado/setter_<clave>.json`). Sin nombres fijos."""
    try:
        with open(os.path.join(RAIZ, 'data', 'personas.json'), encoding='utf-8') as f:
            personas = json.load(f)
    except (OSError, ValueError):
        return []
    lista = personas.get('personas') if isinstance(personas, dict) else personas
    sal = []
    for p in lista or []:
        if not isinstance(p, dict) or 'setters' not in (p.get('puestos') or []) or p.get('estado') == 'baja':
            continue
        clave = p.get('clave_setter') or (p['id'].removeprefix('setter_') if p['id'].startswith('setter_') else None)  # L-09: respaldo hasta la primera recarga
        if clave and clave not in {x['clave'] for x in sal}:
            sal.append({'clave': clave, 'alias': p.get('alias') or p['id'], 'tag': f'setter:{clave}', 'ext': None, 'ext_confirmada': False})
    return sal
SETTERS = setters_de_personas()
_ALIAS = [s['alias'] for s in SETTERS]
NOMBRES_SETTERS = (', '.join(_ALIAS[:-1]) + ' y ' + _ALIAS[-1]) if len(_ALIAS) > 1 else ''.join(_ALIAS)
ENLACES = {  # formatos comprobados en 26_ARQUITECTURA_ERRORES_PLANES_B.md parte C
    'zadarma_estadisticas': 'https://my.zadarma.com/mystatistics/',
    'zadarma_centralita': 'https://my.zadarma.com/mypbx/',
}
CALENDARIOS_VENTA = {  # calendarios comerciales de RO (los talleres de la oferta son de clientes ya firmados: fuera)
    'ChisJEQCj8fXSnML13AQ': '45 min',
    'gzgK7Mz7Al7G9bVZY9uO': '15 min',
    'mWBSx8J4GcYQkWdEWF09': 'Reunión (antiguo)',
}
CAL45 = 'ChisJEQCj8fXSnML13AQ'
# Filas con nombres de prospectos (aunque vayan enmascarados) solo para el closer y quien dirige la venta:
# servir.py (E0) quita las filas con «setter» distinto del de la persona salvo a dirección, ventas de RO, jefa de CRM
# y operaciones. Marcarlas con este valor hace que a setters y outreach no les lleguen. Ver _ESTADO_E6.md.
CLOSER = '_closer'
OBJETIVO_FIRMADOS_OCT = 18      # ficha del closer (G3 §8, «objetivo 18 altas en octubre»)
MESES_C = ['', 'ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
DIAS_ES = ['el lunes', 'el martes', 'el miércoles', 'el jueves', 'el viernes', 'el sábado', 'el domingo']

fuentes = []   # frescura y estado de cada fuente
def fuente(nombre, estado, detalle='', hora=None):
    fuentes.append({'fuente': nombre, 'estado': estado, 'detalle': detalle,
                    'hora': (hora or AHORA.strftime('%Y-%m-%d %H:%M'))})

# ------------------------------------------------------------------ utilidades
def norm(x):
    x = unicodedata.normalize('NFD', (x or '').lower())
    return ' '.join(''.join(ch for ch in x if not unicodedata.combining(ch)).split())

def mascara(texto):
    """«María López» → «M··· L···» (misma regla que permisos.enmascarar)."""
    texto = (texto or '').strip()
    if not texto: return ''
    return ' '.join(p[0] + '···' for p in texto.split() if p)

def mascara_tel(t):
    d = re.sub(r'\D', '', t or '')
    return f'··· ··· {d[-3:]}' if len(d) >= 6 else ('' if not d else '···')

def ult9(t):
    d = re.sub(r'\D', '', str(t or ''))
    return d[-9:] if len(d) >= 9 else ''

def ts(s):
    if not s: return None
    if isinstance(s, (int, float)): return dt.datetime.fromtimestamp(s / 1000, MAD)
    try:
        x = dt.datetime.fromisoformat(str(s).replace('Z', '+00:00'))
    except ValueError:
        return None
    return x.astimezone(MAD) if x.tzinfo else x.replace(tzinfo=MAD)

def iso(x): return x.astimezone(MAD).strftime('%Y-%m-%d %H:%M') if x else None

def ghl_url(loc, cid): return f'https://app.gohighlevel.com/v2/location/{loc}/contacts/detail/{cid}'

# Regla común de teléfonos (3-oct, telefono.py): «+34…» sin espacios; lo que no cuadra no se guarda y va a
# data/telefonos/dudosos.json (apartado «ventas_ro», sin el número entero).
from telefono import limpiar as limpiar_tel, Dudosos  # noqa: E402
DUD_TEL = Dudosos('ventas_ro')

def tel_priv(c):
    """{'telefono': '+34…' | '', 'extension'?} para el almacén privado del setter; el raro se anota y no se guarda."""
    r = limpiar_tel(c.get('phone'))
    if r['motivo'] == 'dudoso':
        DUD_TEL.anotar(None, c.get('phone'), r['aviso'], f"Lead de Ventas de RO en GoHighLevel: {ghl_url(LOC, c.get('id'))}")
    return {'telefono': r['telefono'] or '', **({'extension': r['extension']} if r['extension'] else {})}

def guardar(nombre, datos, priv=False):
    ruta = os.path.join(PRIV if priv else SALIDA, nombre)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, 'w', encoding='utf-8') as f: json.dump(datos, f, ensure_ascii=False, indent=1)
    return ruta

# ------------------------------------------------------------------ GHL (lectura)
sys.path.insert(0, REPARTO)
try:
    import repartir_setters as R
    from ghl_comun import call, LOC
except Exception as e:
    sys.exit(f'No puedo cargar el lector de GHL de {REPARTO}: {e}')

def eventos(cal, desde, hasta):
    try:
        return R.eventos(cal, desde, hasta)
    except SystemExit as e:
        raise RuntimeError(str(e))

def oportunidades_crudas():
    pipes = call('GET', f'/opportunities/pipelines?locationId={LOC}').get('pipelines', [])
    etapa = {s['id']: (p['name'], s['name']) for p in pipes for s in p['stages']}
    out, page = [], 1
    while True:
        r = call('GET', f'/opportunities/search?location_id={LOC}&limit=100&page={page}&status=all')
        if 'ERR' in r: raise RuntimeError(f'oportunidades: {r}')
        ops = r.get('opportunities', [])
        for o in ops:
            p, s = etapa.get(o.get('pipelineStageId'), ('?', '?'))
            o['_pipe'], o['_etapa'] = p, s
        out += ops
        if len(ops) < 100: return out
        page += 1

def todos_los_contactos():
    out, page = [], 1
    while page < 40:
        r = call('POST', '/contacts/search', {'locationId': LOC, 'page': page, 'pageLimit': 100})
        if 'ERR' in r: raise RuntimeError(f'contactos: {r}')
        cs = r.get('contacts', [])
        out += cs
        if len(cs) < 100: break
        page += 1
    return out

def huecos_libres(cal, desde, hasta):
    q = urllib.parse.urlencode({'startDate': int(desde.timestamp() * 1000), 'endDate': int(hasta.timestamp() * 1000), 'timezone': 'Europe/Madrid'})
    r = call('GET', f'/calendars/{cal}/free-slots?{q}', version='2021-04-15')
    if 'ERR' in r: raise RuntimeError(f'huecos: {r}')
    dias = {}
    for k, v in r.items():
        if re.match(r'\d{4}-\d{2}-\d{2}$', k):
            dias[k] = len((v or {}).get('slots', []))
    return dias

def huecos_detalle(cal, desde, hasta):
    """3-oct (setters, «Agendar cita»): los huecos libres con su HORA de Madrid ({'2026-10-07': ['10:00', '10:45']}).
    Solo lectura (GET free-slots). Los usa la pantalla del setter para proponer día y hora; la cita NO se crea desde aquí."""
    q = urllib.parse.urlencode({'startDate': int(desde.timestamp() * 1000), 'endDate': int(hasta.timestamp() * 1000), 'timezone': 'Europe/Madrid'})
    r = call('GET', f'/calendars/{cal}/free-slots?{q}', version='2021-04-15')
    if 'ERR' in r: raise RuntimeError(f'huecos: {r}')
    dias = {}
    for k, v in r.items():
        if not re.match(r'\d{4}-\d{2}-\d{2}$', k): continue
        horas = []
        for sl in (v or {}).get('slots', []):
            try:
                t = dt.datetime.fromisoformat(str(sl).replace('Z', '+00:00'))
                t = t.astimezone(MAD) if t.tzinfo else t.replace(tzinfo=MAD)
                if t > AHORA + dt.timedelta(minutes=30): horas.append(t.strftime('%H:%M'))
            except ValueError:
                continue
        if horas: dias[k] = sorted(set(horas))
    return dias

def huecos_setters():
    """Bloque «huecos» de setters.json: calendario de 45 min (el de Tomás), próximos 14 días, horas de Madrid."""
    return {'calendario': 'Reunión de 45 min', 'calendario_id': CAL45, 'con': 'Tomás', 'zona': 'Europe/Madrid', 'duracion_min': 45,
            'leido': iso(AHORA), 'dias': huecos_detalle(CAL45, AHORA, AHORA + dt.timedelta(days=14))}

if '--solo-huecos' in ARGS:
    # Refresco rápido (cada hora si se quiere): SOLO el bloque «huecos» de setters.json, sin tocar leads ni citas.
    ruta_s = os.path.join(SALIDA, 'setters.json')
    d_s = json.load(open(ruta_s, encoding='utf-8'))
    d_s['huecos'] = huecos_setters()
    guardar('setters.json', d_s)
    print(json.dumps({'huecos': {k: len(v) for k, v in d_s['huecos']['dias'].items()}}, ensure_ascii=False))
    sys.exit(0)

# ------------------------------------------------------------------ lectura
print(f'E6 · generando datos de ventas de RO · {AHORA:%Y-%m-%d %H:%M} (Madrid) · solo lectura')
ghl_ok = True
try:
    usuarios = call('GET', f'/users/?locationId={LOC}').get('users', [])
    ops_crudas = oportunidades_crudas()
    contactos = todos_los_contactos()
    hace14, en14 = AHORA - dt.timedelta(days=14), AHORA + dt.timedelta(days=14)
    evs = {}
    for cal in CALENDARIOS_VENTA:
        evs[cal] = eventos(cal, hace14, en14)
    bofu = R.buscar_tag('bofu')
    fuente('GoHighLevel (subcuenta RO)', 'ok', f'{len(contactos)} contactos, {len(ops_crudas)} tarjetas, {sum(len(v) for v in evs.values())} citas (±14 días)')
except Exception as e:
    ghl_ok = False
    traceback.print_exc()
    fuente('GoHighLevel (subcuenta RO)', 'error', str(e)[:200])
    usuarios, ops_crudas, contactos, evs, bofu = [], [], [], {}, []

por_contacto_ops = {}
for o in ops_crudas:
    por_contacto_ops.setdefault(o.get('contactId'), []).append({'pipeline': o['_pipe'], 'etapa': o['_etapa'], 'status': o.get('status'),
                                                               'cambio': o.get('lastStageChangeAt') or o.get('updatedAt')})
contacto_por_id = {c['id']: c for c in contactos}
tel_a_contacto = {}
for c in contactos:
    k = ult9(c.get('phone'))
    if k: tel_a_contacto.setdefault(k, c)

def contacto(cid):
    if cid in contacto_por_id: return contacto_por_id[cid]
    c = R.contacto(cid); c.setdefault('id', cid); contacto_por_id[cid] = c
    return c

def exclusion(cid):
    return R.motivo_exclusion(contacto(cid), por_contacto_ops.get(cid, []))

def nombre_de(c):
    return (f"{c.get('firstName') or ''} {c.get('lastName') or ''}".strip() or c.get('contactName') or '(sin nombre)')

# Zadarma
llamadas = []
if '--sin-zadarma' not in ARGS:
    try:
        sys.path.insert(0, str(config.HERRAMIENTAS / 'zadarma'))
        import zd
        filas = zd.llamadas_pbx((AHORA - dt.timedelta(days=15)).replace(tzinfo=None), AHORA.replace(tzinfo=None))
        for f in zd.agrupar(filas):
            llamadas.append({'cuando': ts(f.get('callstart')), 'sentido': zd.sentido(f), 'ext': zd.extension(f),
                             'num': ult9(zd.numero_externo(f)), 'seg': int(f.get('seconds') or 0),
                             'contestada': f.get('disposition') == 'answered'})
        fuente('Zadarma', 'ok', f'{len(llamadas)} llamadas en 15 días (1 consulta)')
    except Exception as e:
        traceback.print_exc()
        fuente('Zadarma', 'error', str(e)[:200])
else:
    fuente('Zadarma', 'sin datos', 'no consultado en esta pasada (--sin-zadarma)')

def llamadas_a(num9, desde=None):
    return [l for l in llamadas if l['num'] == num9 and num9 and (desde is None or (l['cuando'] and l['cuando'] >= desde))]

# ------------------------------------------------------------------ SETTERS
setters_out = {'generado': iso(AHORA), 'ubicacion_ghl': LOC if ghl_ok else None, 'setters': [], 'leads': [], 'citas': [],
               'pasadas': [], 'perdidas': [], 'marcador': [], 'reparto': {}, 'avisos': []}
privados = {s['clave']: {} for s in SETTERS}
usuarios_setters = {}
for s in SETTERS:
    u = next((u for u in usuarios if s['alias'].lower() in norm(u.get('name') or u.get('firstName') or '') and not u.get('deleted')), None)
    usuarios_setters[s['clave']] = bool(u)
    setters_out['setters'].append({'clave': s['clave'], 'alias': s['alias'], 'ext': s['ext'], 'ext_confirmada': s['ext_confirmada'],
                                   'usuario_ghl': bool(u)})

cand = {}
def meter(cid, grupo, detalle, desde):
    if cid and cid not in cand:
        cand[cid] = {'grupo': grupo, 'detalle': detalle, 'desde': desde}

if ghl_ok:
    # (a) cita de 45 min futura (lo que el setter confirma)
    for e in sorted(evs.get(CAL45, []), key=lambda e: e['startTime']):
        t = ts(e['startTime'])
        if not t or t < AHORA - dt.timedelta(hours=1) or e.get('appointmentStatus') in ('cancelled', 'invalid'): continue
        meter(e.get('contactId'), 'a', f"Reunión de 45 min el {DIAS_ES[t.weekday()].replace('el ', '')} {t.day} a las {t:%H:%M}", ts(e.get('dateAdded')) or t)
    # (c) no presentados 14 días (cita noshow o tarjeta «No se presentó»)
    for cal, lista in evs.items():
        for e in lista:
            t = ts(e['startTime'])
            if e.get('appointmentStatus') == 'noshow' and t and t < AHORA and not R.cita_futura_viva(e.get('contactId'), AHORA):
                meter(e.get('contactId'), 'c', f'No se presentó a la reunión del {t.day}-{MESES_C[t.month]}', t)
    for o in ops_crudas:
        cambio = ts(o.get('lastStageChangeAt'))
        if o['_pipe'] == 'Ventas RO' and o['_etapa'] == 'No se presentó' and o.get('status') == 'open' and cambio and cambio >= hace14 \
           and not R.cita_futura_viva(o['contactId'], AHORA):
            meter(o['contactId'], 'c', f'No se presentó a su reunión (marcado el {cambio.day}-{MESES_C[cambio.month]})', cambio)
    # (b) dejaron datos en /reuniones/ (o «Pidió reunión · sin hueco») y no reservaron
    reservaron = [c for c in bofu if 'bofu-agendado' in c.get('tags', [])]
    tel9_res = {ult9(c.get('phone')) for c in reservaron if c.get('phone')}
    for c in sorted(bofu, key=lambda c: c.get('dateAdded', ''), reverse=True):
        tags = set(c.get('tags', []))
        alta = ts(c.get('dateAdded'))
        if 'bofu-agendado' in tags or not alta or alta < hace14: continue
        if R.citas_contacto(c['id']): continue
        if ult9(c.get('phone')) and ult9(c.get('phone')) in tel9_res: continue
        estado = ' y el cuestionario' if 'bofu-completo' in tags else (' y no encontró hueco' if 'etapa:sin-hueco' in tags else '')
        meter(c['id'], 'b', f'Rellenó el formulario de la web{estado} y no reservó', alta)
    for o in ops_crudas:
        if o['_pipe'] == 'Ventas RO' and o['_etapa'] == 'Pidió reunión · sin hueco' and o.get('status') == 'open':
            cambio = ts(o.get('lastStageChangeAt')) or ts(o.get('createdAt'))
            if cambio and cambio >= hace14 and not R.cita_futura_viva(o['contactId'], AHORA):
                meter(o['contactId'], 'b', 'Pidió reunión y no encontró hueco', cambio)

    # exclusiones (las mismas del reparto del lunes) + reparto
    filas = []
    excluidos = {}
    for cid, d in cand.items():
        m = exclusion(cid)
        if m:
            excluidos[m] = excluidos.get(m, 0) + 1
            continue
        c = contacto(cid)
        tags = c.get('tags', [])
        previo = next((s['clave'] for s in SETTERS if s['tag'] in tags), None)
        filas.append({'cid': cid, **d, 'c': c, 'setter': previo, 'reparto': 'etiqueta' if previo else 'simulado'})
    orden_g = {'a': 0, 'c': 1, 'b': 2}
    filas.sort(key=lambda f: (orden_g[f['grupo']], f['desde'] or AHORA))
    cuenta = {s['clave']: sum(1 for f in filas if f['setter'] == s['clave']) for s in SETTERS}
    for g in ('a', 'c', 'b'):
        cg = {s['clave']: sum(1 for f in filas if f['grupo'] == g and f['setter'] == s['clave']) for s in SETTERS}
        for f in [f for f in filas if f['grupo'] == g and not f['setter']]:
            s = min(SETTERS, key=lambda s: (cg[s['clave']], cuenta[s['clave']], SETTERS.index(s)))
            f['setter'] = s['clave']; cg[s['clave']] += 1; cuenta[s['clave']] += 1
    setters_out['reparto'] = {'por_setter': cuenta, 'excluidos': excluidos,
                              'nota': 'Mismo alcance y exclusiones que repartir_setters.py. «simulado» = todavía sin etiqueta setter:* en GHL (se pone el lunes 5 con el sí de Tomás).'}

    for f in filas:
        c, cid = f['c'], f['cid']
        num = ult9(c.get('phone'))
        ref = f['desde'] or ts(c.get('dateAdded')) or AHORA
        hechas = [l for l in llamadas_a(num, ref - dt.timedelta(hours=1)) if l['sentido'] == 'saliente']
        entrantes = [l for l in llamadas_a(num, ref - dt.timedelta(hours=1)) if l['sentido'] == 'entrante']
        conv = [l for l in hechas + entrantes if l['contestada'] and l['seg'] >= 60]
        primera = min((l['cuando'] for l in hechas), default=None)
        ultima = max((l['cuando'] for l in hechas), default=None)
        if f['grupo'] == 'a':
            lista = None  # va a «citas por confirmar» (abajo)
        elif conv:
            lista = 'hablado'
        elif not hechas:
            lista = 'llamar_ya'
        else:
            lista = 'segunda'
        vence = (primera + dt.timedelta(hours=48)) if primera else None
        tel = c.get('phone') or ''
        aviso = '' if limpiar_tel(tel)['motivo'] == 'ok' else ('sin teléfono' if not tel else 'teléfono raro: revisar')   # regla común (extranjeros con «+» valen)
        lead = {
            'id': cid, 'setter': f['setter'], 'reparto': f['reparto'], 'grupo': f['grupo'], 'lista': lista,
            'motivo': f['detalle'], 'entro': iso(ref), 'minutos_sin_llamar': int((AHORA - ref).total_seconds() // 60) if lista == 'llamar_ya' else None,
            'intentos': len(hechas), 'primera_llamada': iso(primera), 'ultima_llamada': iso(ultima),
            'segunda_vence': iso(vence) if lista == 'segunda' else None, 'conversaciones': len(conv),
            'nombre_m': mascara(nombre_de(c)), 'despacho_m': mascara(c.get('companyName') or ''), 'tel_m': mascara_tel(tel),
            'aviso_tel': aviso, 'sin_tel': not tel, 'tiene_correo': bool(c.get('email')), 'ghl': ghl_url(LOC, cid),
            'zona': c.get('timezone') or None,   # 3-oct: zona horaria de la ficha (para «hora del lead»); sin ella, España
        }
        setters_out['leads'].append(lead)
        privados[f['setter']][cid] = {'nombre': nombre_de(c), 'despacho': c.get('companyName') or '', **tel_priv(c), 'correo': c.get('email') or ''}

    # citas de hoy y mañana por confirmar (calendario de 45 min, ya repartidas en (a))
    # «hoy y mañana» = hoy y el siguiente día laborable (un viernes se confirman las del lunes)
    siguiente = HOY + dt.timedelta(days=1)
    while siguiente.weekday() >= 5: siguiente += dt.timedelta(days=1)
    fin_manana = dt.datetime.combine(siguiente, dt.time(23, 59), MAD)
    por_cid = {f['cid']: f for f in filas}
    for e in sorted(evs.get(CAL45, []), key=lambda e: e['startTime']):
        t = ts(e['startTime']); cid = e.get('contactId')
        if not t or t < AHORA - dt.timedelta(hours=1) or t > fin_manana or e.get('appointmentStatus') in ('cancelled', 'invalid'): continue
        f = por_cid.get(cid)
        if not f: continue  # excluida (cliente, segunda reunión, etc.): es de Tomás, no del setter
        c = contacto(cid); num = ult9(c.get('phone'))
        reservada = ts(e.get('dateAdded')) or t - dt.timedelta(days=3)
        conf = [l for l in llamadas_a(num, reservada) if l['contestada'] and l['seg'] >= 60]
        setters_out['citas'].append({'id': cid, 'cita_id': e.get('id'), 'setter': f['setter'], 'cuando': iso(t),
                                     'dia': 'hoy' if t.date() == HOY else ('mañana' if t.date() == HOY + dt.timedelta(days=1) else DIAS_ES[t.weekday()]), 'estado_ghl': e.get('appointmentStatus'),
                                     'confirmada_tel': bool(conf), 'llamadas': len(llamadas_a(num, reservada)),
                                     'nombre_m': mascara(nombre_de(c)), 'despacho_m': mascara(c.get('companyName') or ''),
                                     'tel_m': mascara_tel(c.get('phone')), 'sin_tel': not c.get('phone'), 'tiene_correo': bool(c.get('email')), 'ghl': ghl_url(LOC, cid),
                                     'zona': c.get('timezone') or None})
        privados[f['setter']][cid] = {'nombre': nombre_de(c), 'despacho': c.get('companyName') or '', **tel_priv(c), 'correo': c.get('email') or ''}

    # citas pasadas sin resultado (7 días): GHL no marca la cita y la tarjeta sigue en «Cita agendada» o no hay tarjeta
    etapa_ventas = {}
    for o in ops_crudas:
        if o['_pipe'] == 'Ventas RO' and o.get('status') == 'open': etapa_ventas[o['contactId']] = o['_etapa']
    alterna = 0
    for cal, lista in evs.items():
        for e in lista:
            t = ts(e['startTime']); cid = e.get('contactId')
            if not t or t > AHORA - dt.timedelta(hours=1) or t < AHORA - dt.timedelta(days=7): continue
            if e.get('appointmentStatus') in ('showed', 'noshow', 'cancelled', 'invalid'): continue
            et = etapa_ventas.get(cid)
            if et not in (None, 'Cita agendada'): continue  # la tarjeta ya se movió: hay resultado
            if exclusion(cid): continue
            c = contacto(cid)
            previo = next((s['clave'] for s in SETTERS if s['tag'] in c.get('tags', [])), None)
            setter = previo or (por_cid[cid]['setter'] if cid in por_cid else (SETTERS[alterna % len(SETTERS)]['clave'] if SETTERS else None))
            if not previo and cid not in por_cid: alterna += 1
            setters_out['pasadas'].append({'id': cid, 'setter': setter, 'cuando': iso(t), 'calendario': CALENDARIOS_VENTA[cal],
                                           'estado_ghl': e.get('appointmentStatus'), 'etapa': et or 'sin tarjeta',
                                           'grabada_zadarma': bool([l for l in llamadas_a(ult9(c.get('phone')), t - dt.timedelta(hours=2)) if l['contestada']]),
                                           'nombre_m': mascara(nombre_de(c)), 'despacho_m': mascara(c.get('companyName') or ''), 'ghl': ghl_url(LOC, cid)})
            privados[setter][cid] = {'nombre': nombre_de(c), 'despacho': c.get('companyName') or '', **tel_priv(c), 'correo': c.get('email') or ''}

# llamadas perdidas o de números sin ficha (48 h). Solo número enmascarado; el setter ve las de SU extensión.
for l in llamadas:
    if not l['cuando'] or l['cuando'] < AHORA - dt.timedelta(hours=48) or l['sentido'] != 'entrante': continue
    c = tel_a_contacto.get(l['num'])
    sin_ficha = c is None
    perdida = not l['contestada']
    if not (sin_ficha or perdida): continue
    if c and exclusion(c['id']) in ('cliente (etiqueta)', 'cliente (pipeline)'):
        continue  # clientes de la agencia: no es trabajo del setter
    setter = next((s['clave'] for s in SETTERS if s['ext'] == l['ext']), None)
    setters_out['perdidas'].append({'cuando': iso(l['cuando']), 'ext': l['ext'], 'setter': setter or '', 'perdida': perdida,
                                    'sin_ficha': sin_ficha, 'seg': l['seg'], 'tel_m': '··· ··· ' + l['num'][-3:] if l['num'] else 'oculto',
                                    'ghl': ghl_url(LOC, c['id']) if c else None})

# marcador del día y de la semana por extensión
lunes = dt.datetime.combine(HOY - dt.timedelta(days=HOY.weekday()), dt.time(0, 0), MAD)
for s in SETTERS:
    for periodo, desde in (('hoy', dt.datetime.combine(HOY, dt.time(0, 0), MAD)), ('semana', lunes)):
        sal = [l for l in llamadas if s['ext'] and l['ext'] == s['ext'] and l['sentido'] == 'saliente' and l['cuando'] and l['cuando'] >= desde]
        conv = [l for l in sal if l['contestada'] and l['seg'] >= 60]
        citas = 0
        for e in evs.get(CAL45, []):
            alta = ts(e.get('dateAdded'))
            if alta and alta >= desde and s['tag'] in contacto(e.get('contactId')).get('tags', []) and e.get('appointmentStatus') not in ('cancelled', 'invalid'):
                citas += 1
        con_ext = bool(s['ext'])   # sin extensión confirmada: «sin dato», nunca un cero falso
        setters_out['marcador'].append({'setter': s['clave'], 'periodo': periodo, 'marcaciones': len(sal) if con_ext else None,
                                        'conversaciones': len(conv) if con_ext else None,
                                        'pct_conv': round(100 * len(conv) / len(sal), 1) if sal else None, 'citas': citas,
                                        'citas_medibles': any(s['tag'] in (c.get('tags') or []) for c in contactos)})

if SETTERS and not any(usuarios_setters.get(s['clave']) for s in SETTERS):
    setters_out['avisos'].append(f'{NOMBRES_SETTERS} todavía no tienen usuario en GHL: se crean el lunes 5 con el sí de Tomás (manda invitación por correo).')
setters_out['avisos'].append(f'Extensiones de Zadarma de {NOMBRES_SETTERS} por confirmar (la 107 y la 110 están desconectadas o son de Lourdes): hasta entonces las llamadas del marcador salen «sin dato».')
setters_out['enlaces'] = {**ENLACES, 'ghl_oportunidades': f'https://app.gohighlevel.com/v2/location/{LOC}/opportunities/list',
                          'ghl_calendario': f'https://app.gohighlevel.com/v2/location/{LOC}/calendars/view',
                          'ghl_conversaciones': f'https://app.gohighlevel.com/v2/location/{LOC}/conversations/conversations'}
# Recuento por setter (para quien lo ve en «resumen»: sin filas de leads)
setters_out['recuento'] = [{'quien': s['clave'], 'llamar_ya': sum(1 for l in setters_out['leads'] if l['setter'] == s['clave'] and l['lista'] == 'llamar_ya'),
                            'segundas': sum(1 for l in setters_out['leads'] if l['setter'] == s['clave'] and l['lista'] == 'segunda'),
                            'citas': sum(1 for c in setters_out['citas'] if c['setter'] == s['clave']),
                            'pasadas': sum(1 for c in setters_out['pasadas'] if c['setter'] == s['clave'])} for s in SETTERS]

# ------------------------------------------------------------------ VENTAS DE RO (panel v29 + GHL en vivo)
FATHOM = {}
ventas = {'generado': iso(AHORA), 'meses': {}, 'hoy': [], 'propuestas': [], 'contratos': [], 'huecos': {}, 'bajas_tempranas': None,
          'circuito': None, 'avisos': []}
priv_tomas = {}
try:
    D = json.load(open(os.path.join(PANEL, 'dataset_ro.json'), encoding='utf-8'))
    def calc(desde, hasta):
        """Réplica de calc() del panel v29 (modo «por fecha del hecho», todas las capas)."""
        inR = lambda d: d is not None and desde <= d <= hasta
        spend = sum(s[2] for s in D['spend'] if inR(s[0]))
        sales = [c for c in D['citas'] if c['k'] != 'taller']
        booked = [c for c in sales if c.get('b') and inR(c['b']) and c['status'] != 'cancelled']
        dated = [c for c in sales if inR(c.get('at'))]
        held = [c for c in dated if c['status'] == 'showed']
        noshow = [c for c in dated if c['status'] == 'noshow']
        sinm = [c for c in dated if c['status'] == 'sin_marcar']
        L = D['leads']
        leads = [l for l in L if inR(l['d'])]
        props = [l for l in L if l.get('prop') and inR(l['prop']['d'])]
        acus = [l for l in L if l.get('acu') and inR(l['acu']['d'])]
        signed = [l for l in L if l.get('sale') and inR(l['sale']['d'])]
        paid = [l for l in L if l.get('sale') and l['sale'].get('paid') and inR(l['sale'].get('dp'))]
        return {'desde': desde, 'hasta': hasta, 'inversion': round(spend, 2), 'contactos': len(leads),
                'piden_reunion': sum(1 for l in leads if l.get('ask')), 'citas': len(booked), 'celebradas': len(held),
                'ausencias': len(noshow), 'sin_marcar': len(sinm), 'propuestas': len(props), 'acuerdos': len(acus),
                'firmados': len(signed), 'cobrados': len(paid), 'cuota_firmada': sum((l['sale'].get('v') or 0) for l in signed)}
    fin_sep = '2026-09-30'
    # Fathom: última grabación de cada contacto (cid → url) a partir de las ventas del panel y sus lecturas reus/
    FATHOM = {}
    for vv in D.get('ventas', []):
        fa, cidv = vv.get('fa'), vv.get('cid')
        ruta = os.path.join(PANEL, 'reus', f'{fa}.json') if fa else None
        if cidv and ruta and os.path.exists(ruta):
            u = json.load(open(ruta, encoding='utf-8')).get('url')
            if u and u.startswith('https://fathom.video/'): FATHOM[cidv] = u
    ventas['meses']['2026-09'] = calc('2026-09-01', fin_sep)
    ventas['meses']['2026-10'] = calc('2026-10-01', HOY.isoformat())
    # R12 (A-A2): serie DIARIA con las mismas reglas (todo es «por fecha del hecho», así que los días se suman): con ella
    # la pantalla responde a cualquier periodo (7 días, mes, mes anterior, trimestre, año, a medida) sin otro cálculo.
    primer = min([s_[0] for s_ in D['spend']] + [l['d'] for l in D['leads'] if l.get('d')])
    ventas['dias'] = {}
    dd = dt.date.fromisoformat(primer[:10])
    while dd <= HOY:
        x = calc(dd.isoformat(), dd.isoformat()); x.pop('desde', None); x.pop('hasta', None)
        ventas['dias'][dd.isoformat()] = x
        dd += dt.timedelta(days=1)
    ventas['datos_desde'] = primer[:10]
    ventas['panel_generado'] = D.get('generated')
    ventas['circuito'] = {'pasos': [{'t': p['t'], 'de': p['m'], 'pasaron': p['n'], 'en_curso': p['viv'], 'se_quedaron': p['no']} for p in D['circ']['pasos']],
                          'fases': D['circ'].get('fases'), 'sin_marcar_personas': D['circ']['tot'].get('sinMarcar')}
    ventas['velocidad'] = None
    # bajas tempranas de lo vendido (90 días): nombres de bajas del libro de clientes frente a firmados desde agosto
    firmados_nombres = [norm(v['n']) for v in D['ventas'] if v.get('col') == 'Cliente']
    bajas = []
    for m in D['cli'].get('churn', []):
        if m['mes'] < '2026-08': continue
        for b in (m.get('nombres_bajas') or '').split(','):
            nb = norm(b)
            if nb and any(len(w) >= 5 and w in fn for w in nb.split() for fn in firmados_nombres):
                bajas.append({'mes': m['mes'], 'cliente': b.strip()})
    ventas['bajas_tempranas'] = {'n': len(bajas), 'detalle': bajas, 'firmados_desde_agosto': len(firmados_nombres),
                                 'libro_leido': D['cli'].get('leido')}
    fr = json.load(open(os.path.join(PANEL, 'frescura.json'), encoding='utf-8'))
    for nombre, hora, que in fr['fuentes']:
        fuente(f'Panel v29 · {nombre}', 'ok' if hora >= (HOY - dt.timedelta(days=2)).isoformat() else 'viejo', que, hora)
except Exception as e:
    traceback.print_exc()
    fuente('Panel de resultados de RO (v29)', 'error', str(e)[:200])

if ghl_ok:
    eng_open = {}
    try:
        eng_open = json.load(open(os.path.join(PANEL, '_crudo/eng_open.json')))
    except Exception:
        pass
    # reuniones de hoy (todas las comerciales, también segundas: son del closer)
    for cal, lista in evs.items():
        for e in lista:
            t = ts(e['startTime']); cid = e.get('contactId')
            if not t or t.date() != HOY or e.get('appointmentStatus') in ('cancelled', 'invalid'): continue
            c = contacto(cid)
            m = exclusion(cid)
            if m and m.startswith('ficha de prueba'): continue
            et = etapa_ventas.get(cid) or 'sin tarjeta'
            setter = next((s['alias'] for s in SETTERS if s['tag'] in c.get('tags', [])), None)
            ventas['hoy'].append({'id': cid, 'setter': CLOSER, 'fathom': FATHOM.get(cid), 'cuando': iso(t), 'calendario': CALENDARIOS_VENTA[cal], 'estado_ghl': e.get('appointmentStatus'),
                                  'etapa': et, 'setter_alias': setter, 'segunda': 'cita:segunda' in c.get('tags', []),
                                  'nombre_m': mascara(nombre_de(c)), 'despacho_m': mascara(c.get('companyName') or ''), 'ghl': ghl_url(LOC, cid)})
            priv_tomas[cid] = {'nombre': nombre_de(c), 'despacho': c.get('companyName') or ''}
    ventas['hoy'].sort(key=lambda x: x['cuando'])
    # R12 (C medio «0 celebradas»): el embudo del mes sale del panel v29, cuya foto es de la madrugada; las reuniones de HOY
    # que ya pasaron se cuentan con la etapa de GHL en vivo (misma regla que el panel: «celebrada» = pasó a propuesta,
    # contrato o cliente; «no se presentó» = ausencia; lo demás, sin marcar). Cada reunión de hoy lleva su resultado.
    ETAPAS_CELEBRADA = ('Propuesta enviada', 'Contrato enviado', 'Cliente')
    for x in ventas['hoy']:
        pasada = ts(x['cuando'].replace(' ', 'T') + ':00+02:00') if x.get('cuando') else None
        x['pasada'] = bool(pasada and pasada + dt.timedelta(minutes=45) <= AHORA)
        x['resultado'] = (None if not x['pasada'] else 'celebrada' if (x['etapa'] in ETAPAS_CELEBRADA or x.get('fathom'))
                          else 'no_se_presento' if x['etapa'] == 'No se presentó' else 'sin_marcar')
    mo = ventas['meses'].get(HOY.strftime('%Y-%m'))
    try:   # si la foto del panel ya marcó las de hoy, no se suman dos veces
        ya_marcadas = sum(1 for c in D['citas'] if c.get('at') == HOY.isoformat() and c.get('status') in ('showed', 'noshow'))
    except Exception:
        ya_marcadas = 0
    if mo is not None and not ya_marcadas:
        hoy_c = sum(1 for x in ventas['hoy'] if x['resultado'] == 'celebrada')
        hoy_a = sum(1 for x in ventas['hoy'] if x['resultado'] == 'no_se_presento')
        hoy_s = sum(1 for x in ventas['hoy'] if x['resultado'] == 'sin_marcar')
        mo['celebradas'] += hoy_c; mo['ausencias'] += hoy_a; mo['sin_marcar'] += hoy_s
        mo['de_hoy_en_vivo'] = {'celebradas': hoy_c, 'ausencias': hoy_a, 'sin_marcar': hoy_s, 'hora': iso(AHORA)}
        dh = ventas.get('dias', {}).get(HOY.isoformat())
        if dh is not None:
            dh['celebradas'] += hoy_c; dh['ausencias'] += hoy_a; dh['sin_marcar'] += hoy_s
    # propuestas y contratos (tarjetas abiertas de Ventas RO)
    for o in ops_crudas:
        if o['_pipe'] != 'Ventas RO' or o.get('status') != 'open': continue
        if o['_etapa'] not in ('Propuesta enviada', 'Contrato enviado'): continue
        cambio = ts(o.get('lastStageChangeAt')) or ts(o.get('updatedAt'))
        dias = (AHORA - cambio).days if cambio else None
        cid = o['contactId']; c = contacto(cid)
        abierta = eng_open.get(cid)
        abierta_t = ts(abierta) if abierta else None
        fila = {'id': cid, 'setter': CLOSER, 'fathom': FATHOM.get(cid), 'etapa': o['_etapa'], 'desde': iso(cambio), 'dias': dias, 'cuota_mensual': o.get('monetaryValue'),
                'abierta': bool(abierta_t and cambio and abierta_t >= cambio - dt.timedelta(hours=1)), 'ultima_apertura': iso(abierta_t),
                'nombre_m': mascara(o.get('name') or nombre_de(c)), 'ghl': ghl_url(LOC, cid)}
        priv_tomas[cid] = {'nombre': (o.get('name') or nombre_de(c)).strip(), 'despacho': c.get('companyName') or ''}
        (ventas['propuestas'] if o['_etapa'] == 'Propuesta enviada' else ventas['contratos']).append(fila)
    ventas['propuestas'].sort(key=lambda x: -(x['dias'] or 0)); ventas['contratos'].sort(key=lambda x: -(x['dias'] or 0))
    ventas['tablero_hoy'] = {}
    for o in ops_crudas:
        if o['_pipe'] == 'Ventas RO' and o.get('status') == 'open':
            ventas['tablero_hoy'][o['_etapa']] = ventas['tablero_hoy'].get(o['_etapa'], 0) + 1
    ventas['cliente_en_octubre_ghl'] = sum(1 for o in ops_crudas if o['_pipe'] == 'Ventas RO' and o['_etapa'] == 'Cliente'
                                            and (ts(o.get('lastStageChangeAt')) or AHORA).date() >= dt.date(2026, 10, 1))
    try:
        ventas['huecos'] = {'calendario': '45 min', 'por_dia': huecos_libres(CAL45, AHORA, AHORA + dt.timedelta(days=14)),
                            'citas_ya': sum(1 for e in evs.get(CAL45, []) if ts(e['startTime']) and ts(e['startTime']) >= AHORA
                                            and e.get('appointmentStatus') not in ('cancelled', 'invalid'))}
        fuente('GoHighLevel · huecos libres', 'ok', '45 min, próximos 14 días')
    except Exception as e:
        fuente('GoHighLevel · huecos libres', 'error', str(e)[:200])
    try:
        setters_out['huecos'] = huecos_setters()   # 3-oct: «Agendar cita» del setter (horas libres del calendario de 45 min)
    except Exception as e:
        setters_out['huecos'] = {'calendario': 'Reunión de 45 min', 'calendario_id': CAL45, 'dias': {}, 'error': str(e)[:200]}
ventas['objetivo_firmados_mes'] = OBJETIVO_FIRMADOS_OCT
ventas['enlaces'] = setters_out.get('enlaces', {})
ventas['avisos'].append('Zoho Sign sin leer desde la app: los contratos salen de la columna «Contrato enviado» de GHL.')

# ------------------------------------------------------------------ OUTREACH
outreach = {'generado': iso(AHORA), 'ro': {}, 'clientes': {}, 'snov': None, 'respuestas': [], 'avisos': []}
priv_out = {}
try:
    oc = json.load(open(OUTREACH_CLI, encoding='utf-8'))
    for k, v in oc.items():
        if k.startswith('_'): continue
        outreach['clientes'][k] = {'canales': v.get('canales'), 'sep': v.get('sep'), 'oct': v.get('oct'),
                                   'ultimo_lead': v.get('ultimo_lead'),
                                   'prueba': [u for u in re.findall(r'https://app\.clickup\.com/t/\w+', v.get('fuente') or '')][:2]}
    outreach['clientes_meta'] = {'generado': oc['_meta'].get('generado'), 'nota': 'Cifras del panel v7 de Mili (ClickUp, chats y hojas públicas). Sin notas: llevaban nombres de leads.'}
    fuente('Outreach de clientes (panel v7 de Mili)', 'ok', f"{len(outreach['clientes'])} clientes", oc['_meta'].get('generado'))
except Exception as e:
    fuente('Outreach de clientes (panel v7 de Mili)', 'error', str(e)[:200])

if '--sin-snov' not in ARGS:
    try:
        sys.path.insert(0, str(config.HERRAMIENTAS / 'snov'))
        import sv
        tk = sv.token()
        cs = sv.get(tk, '/v1/get-user-campaigns')
        cs = cs if isinstance(cs, list) else cs.get('data', [])
        clientes_nombres = [norm(k) for k in outreach['clientes']] + ['busbac', 'musashi', 'greconsult', 'centro consulting', 'pgba', 'gac',
                                                                    'ecom', 'proincentiva', 'ecija', 'finexen']
        campañas = []
        hace30 = AHORA - dt.timedelta(days=30)
        # V2 · de qué cliente es cada campaña (una regla: fuentes_ventas/campana_cliente.py). Con él, pantalla y servidor
        # recortan por la cartera de outreach: Eulimar ve SOLO sus campañas y sus respuestas.
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import campana_cliente as CC
        _cli = CC.clientes()
        for c in cs:
            if c.get('status') not in ('Active', 'Paused'): continue
            nombre = c.get('campaign') or ''
            if norm(nombre) in ('prueba', 'test'): continue
            de_cliente = next((n for n in clientes_nombres if n.split()[0] in norm(nombre)), None)
            reps = sv.get(tk, '/v1/get-emails-replies', campaignId=c['id'])
            reps = reps if isinstance(reps, list) else []
            r30 = [r for r in reps if ts(r.get('visitedAt')) and ts(r.get('visitedAt')) >= hace30]
            cli_id = CC.cliente_de(nombre, _cli)
            campañas.append({'id': c['id'], 'nombre': nombre, 'estado': c.get('status'), 'frente': 'clientes' if de_cliente else 'ro', 'cliente_id': cli_id,
                             'respuestas_total': len(reps), 'respuestas_30d': len(r30),
                             'ultima_respuesta': iso(max((ts(r['visitedAt']) for r in reps if ts(r.get('visitedAt'))), default=None))})
            for r in r30:
                rid = 'r' + hashlib.sha1(f"{c['id']}:{r.get('id')}".encode()).hexdigest()[:12]
                nombre_p = r.get('prospectName') or f"{r.get('prospectFirstName') or ''} {r.get('prospectLastName') or ''}"
                outreach['respuestas'].append({'id': rid, 'campana': nombre, 'frente': 'clientes' if de_cliente else 'ro', 'cliente_id': cli_id,
                                               'fecha': iso(ts(r.get('visitedAt'))), 'nombre_m': mascara(nombre_p),
                                               'zona': (r.get('locality') or '').split(',')[-2].strip() if (r.get('locality') or '').count(',') >= 1 else '',
                                               'clase': 'sin clasificar', 'dueno': None})
                emails = r.get('prospectEmail') or ''
                li = r.get('sourcePage') or r.get('links') or ''
                li = li if isinstance(li, str) and 'linkedin.com/' in li else ''
                cid_ghl = None
                if emails and ghl_ok:
                    q = urllib.parse.urlencode({'locationId': LOC, 'email': emails})
                    cid_ghl = (call('GET', f'/contacts/search/duplicate?{q}').get('contact') or {}).get('id')
                outreach['respuestas'][-1].update({'ghl': ghl_url(LOC, cid_ghl) if cid_ghl else None, 'tiene_linkedin': bool(li)})
                # V2 · extracto de la respuesta (para clasificarla sin salir de la app): solo en el almacén privado, con rastro al abrirlo
                cuerpo = next((r.get(k) for k in ('replyText', 'reply', 'message', 'text', 'body', 'emailBody') if isinstance(r.get(k), str) and r.get(k).strip()), '')
                cuerpo = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', cuerpo)).strip()
                priv_out[rid] = {'nombre': nombre_p.strip(), 'correo': emails, 'campana': nombre, 'linkedin': li, 'cliente_id': cli_id,
                                 'extracto': (cuerpo[:600] + '…') if len(cuerpo) > 600 else cuerpo}
        outreach['respuestas'].sort(key=lambda x: x['fecha'] or '', reverse=True)
        outreach['snov'] = {'campañas': campañas, 'activas': sum(1 for c in campañas if c['estado'] == 'Active'),
                            'activas_ro': sum(1 for c in campañas if c['estado'] == 'Active' and c['frente'] == 'ro'),
                            'leido': iso(AHORA)}
        fuente('Snov.io', 'ok', f'{len(campañas)} campañas activas o en pausa; respuestas de 30 días')
    except Exception as e:
        traceback.print_exc()
        fuente('Snov.io', 'error', str(e)[:200])
else:
    # R12 (C-A4): la pasada ligera no lee Snov, pero NO borra lo último bueno: antes dejaba snov=null y Prospección
    # decía «0 campañas, 0 respuestas» con 18 campañas activas. Se conserva la última lectura con su hora.
    try:
        prev = json.load(open(os.path.join(SALIDA, 'outreach.json'), encoding='utf-8'))
        prev_priv = json.load(open(os.path.join(PRIV, 'outreach_respuestas.json'), encoding='utf-8')).get('respuestas', {})
    except Exception:
        prev, prev_priv = {}, {}
    if prev.get('snov'):
        outreach['snov'] = prev['snov']
        outreach['respuestas'] = prev.get('respuestas') or []
        priv_out.update({k: v for k, v in prev_priv.items() if any(r['id'] == k for r in outreach['respuestas'])})
        leido = prev['snov'].get('leido') or prev.get('generado')
        fuente('Snov.io', 'viejo' if leido and leido[:10] < HOY.isoformat() else 'ok',
               f"última lectura buena ({len(prev['snov'].get('campañas') or [])} campañas); esta pasada no consulta Snov", leido)
    else:
        fuente('Snov.io', 'sin datos', 'todavía no hay ninguna lectura buena de Snov.io (se lee en la recarga completa)')
outreach['avisos'] += [
    'Linked Helper y Explee no tienen API: sus cifras solo entran por la hoja semanal declarada.',
    'Las respuestas de Snov no traen si son positivas: se clasifican a mano al asignarlas.',
    'Las respuestas de Explee llegan al correo de tomas@ (Zoho Mail), que la app no lee todavía.',
]
if ghl_ok:
    outreach['ro']['en_ghl_origen_outreach'] = sum(1 for c in contactos if any(t.startswith('origen:outreach') for t in c.get('tags', [])))

# ------------------------------------------------------------------ salida
# Puerta de secretos propia (la de E0 aún no existe): ANTES de escribir, nada de teléfonos ni correos completos fuera de _privado/
publicos = {'setters.json': setters_out, 'ventas_ro.json': ventas, 'outreach.json': outreach,
            'meta.json': {'generado': iso(AHORA), 'fuentes': fuentes,
                          'nota': 'Datos de leads enmascarados. Los completos están en _privado/ (solo prueba local; nunca a GitHub ni a publicar).'}}
FECHAS = r'"(generado|hora|entro|cuando|desde|hasta|fecha|primera_llamada|ultima_llamada|segunda_vence|ultima_apertura|ultima_respuesta|panel_generado|ultimo_lead|id|cita_id|libro_leido)": "[^"]*"'
malos = []
for n, datos in publicos.items():
    t = json.dumps(datos, ensure_ascii=False)
    if re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', t): malos.append(f'{n}: correo')
    for m in re.finditer(r'\+?\d[\d ]{8,}\d', re.sub(FECHAS, '', t)):
        malos.append(f'{n}: posible teléfono «…{m.group()[-3:]}»')
if malos:
    sys.exit('PUERTA DE SECRETOS: no escribo nada. ' + '; '.join(malos[:5]))
for n, datos in publicos.items():
    guardar(n, datos)
for s in SETTERS:
    guardar(f"setter_{s['clave']}.json", {'setter': s['clave'], 'generado': iso(AHORA), 'leads': privados[s['clave']]}, priv=True)
guardar('ventas_tomas.json', {'generado': iso(AHORA), 'leads': priv_tomas}, priv=True)
guardar('outreach_respuestas.json', {'generado': iso(AHORA), 'respuestas': priv_out}, priv=True)
with open(os.path.join(PRIV, '.gitignore'), 'w') as f: f.write('*\n')
DUD_TEL.guardar()

print(json.dumps({'leads': len(setters_out['leads']), 'citas_48h': len(setters_out['citas']), 'pasadas': len(setters_out['pasadas']),
                  'perdidas': len(setters_out['perdidas']), 'reparto': setters_out['reparto'].get('por_setter'),
                  'sep': ventas['meses'].get('2026-09'), 'oct': ventas['meses'].get('2026-10'),
                  'respuestas_outreach': len(outreach['respuestas']), 'fuentes': [(f['fuente'], f['estado']) for f in fuentes]},
                 ensure_ascii=False, indent=1))
