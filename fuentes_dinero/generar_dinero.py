# -*- coding: utf-8 -*-
"""M18 «Dinero por cliente», M19 «Finanzas de la empresa» y el bloque de anuncios y previsión de M16 (E10).

SOLO LECTURA. Lee:
  · Holded en vivo con ~/RO_HERRAMIENTAS/holded/hd.py (tesorería y facturas de venta): solo GET.
  · Airtable de facturación (base app9OBjN9MiqIQVxI, tabla «Facturación mensual») con airtable_token: solo GET.
    El Airtable lo lleva Sofía: NUNCA se escribe (MEM feedback_no_tocar_airtable_facturacion).
  · Panel financiero v29: ~/Downloads/PANEL_RESULTADOS_RO_2026-09-18/ENTREGA/financiero_ro.json (historia desde dic-2022,
    cierre de Sofía, proveedores, concentración) y finanzas_ajustes.json (altas, bajas y cambios del mes).
  · Libro de clientes ~/Downloads/BAJAS_LTV_CHURN_2026-10-01/ (vía data/clientes/<id>.json de E1) y horas de ClickUp
    (bloque «horas» de E1, sello «horas incompletas»), tarifa 31,47 €/h.
  · data/asignaciones.json y data/personas.json (E0), data/nuevos/nuevos.json (Sign, M12), data/ventas_ro/ventas_ro.json (E6)
    y la atribución de anuncios del panel v30 (atribucion_anuncios.json).
Escribe (a temporal y renombra; si la puerta de secretos encuentra algo, no escribe):
  data/dinero_cliente/dinero_cliente.json · data/finanzas/finanzas.json · data/ventas_ro_extra/anuncios.json
Permisos (servir.py + reglas_permisos.json → datos_de_modulo): ver _ESTADO_dinero.md. Sueldos individuales: nunca.

Uso:  python3 fuentes_dinero/generar_dinero.py            (Holded y Airtable en vivo; si fallan, la última copia de _cache)
      python3 fuentes_dinero/generar_dinero.py --sin-red  (solo la copia de _cache)
"""
import json, os, re, sys, subprocess, urllib.request, urllib.parse, datetime as dt
from collections import defaultdict, Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
sys.path.insert(0, str(APP / 'fuentes'))
from comun import escribir, escanear, norm, leer   # noqa: E402
import pathlib as _pl_l27, sys as _sys_l27  # L-27: rutas del Mac por config.py
if str(_pl_l27.Path(__file__).resolve().parents[1]) not in _sys_l27.path:
    _sys_l27.path.append(str(_pl_l27.Path(__file__).resolve().parents[1]))
import config as _cfg  # noqa: E402

DATA = APP / 'data'
CACHE = AQUI / '_privado' / '_cache'   # Holded en bruto (números de documento): fuera del escáner y de la subida
ENT = _cfg.PANEL_RESULTADOS
HOLDED = _cfg.HERRAMIENTAS / 'holded'
SIN_RED = '--sin-red' in sys.argv

AHORA = dt.datetime.now()
HOY = AHORA.date()
HORA = AHORA.strftime('%Y-%m-%d %H:%M')
MES = HOY.strftime('%Y-%m')
TARIFA = 31.47              # €/h, D-85 (Mili y Coti)
TOPE_ACCOUNT = 12           # D-07
HORAS_MES = 128             # D-25
USD_EUR = 0.8686            # BCE, media de septiembre (la misma que usó el panel financiero v29)
LOC_RO = 'uARKuoIbrfrbnvXQ85dY'
R = lambda v, d=2: round(v, d) if isinstance(v, (int, float)) else v

fuentes = []
def fuente(nombre, estado, detalle='', hora=None):
    fuentes.append({'fuente': nombre, 'estado': estado, 'detalle': detalle, 'hora': hora or HORA})

def hora_fichero(p):
    try: return dt.datetime.fromtimestamp(os.path.getmtime(p)).strftime('%Y-%m-%d %H:%M')
    except OSError: return None

# ------------------------------------------------------------------ lectores (solo GET)
def holded(path, **q):
    sys.path.insert(0, str(HOLDED))
    import hd
    try:
        return hd.get(path, **q)
    except SystemExit as e:          # hd.get sale con sys.exit si la API responde mal
        raise RuntimeError(str(e))

def airtable_lineas():
    t = _cfg.secreto('airtable_token')     # N-14: sin llave, error como antes (con_cache usa la copia de _cache)
    if not t: raise RuntimeError('falta la llave airtable_token')
    recs, off = [], None
    while True:
        q = {'pageSize': '100', 'cellFormat': 'string', 'timeZone': 'Europe/Madrid', 'userLocale': 'es'}
        if off: q['offset'] = off
        u = 'https://api.airtable.com/v0/app9OBjN9MiqIQVxI/' + urllib.parse.quote('Facturación mensual') + '?' + urllib.parse.urlencode(q)
        r = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'Authorization': 'Bearer ' + t}), timeout=60))
        recs += r['records']; off = r.get('offset')
        if not off: break
    campos = ('Cliente', 'Mes', 'Importe', 'Importe especial', 'Estado facturación', 'Estado cliente', 'Forma de pago', 'Tipo',
              'Cobrada', 'Alta cliente', 'Baja cliente', 'Fecha factura', 'Factura emitida', 'Aprobado CEO', 'Fuera de contrato')
    return [{'id': x['id'], **{k: x['fields'].get(k) for k in campos}} for x in recs]

def con_cache(nombre, lector, etiqueta):
    """Lee en vivo; si falla (o --sin-red), la última copia de _cache. Devuelve (datos, estado, hora)."""
    ruta = CACHE / f'{nombre}.json'
    if not SIN_RED:
        try:
            d = lector()
            CACHE.mkdir(parents=True, exist_ok=True)
            ruta.write_text(json.dumps({'hora': HORA, 'datos': d}, ensure_ascii=False))
            return d, 'ok', HORA
        except Exception as e:     # noqa: BLE001
            print(f'  {etiqueta}: en vivo falla ({str(e)[:90]}); uso la copia de _cache')
    c = leer(ruta)
    if c: return c['datos'], 'viejo', c['hora']
    return None, 'sin datos', None

def eur(s):
    """«"€1.470,00"» → 1470.0"""
    if s in (None, ''): return 0.0
    if isinstance(s, (int, float)): return float(s)
    s = str(s).replace('"', '').replace('€', '').replace('.', '').replace(',', '.').strip()
    try: return float(s)
    except ValueError: return 0.0

def fecha_us(s):
    """«9/18/2026» → '2026-09-18'"""
    m = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})', str(s or ''))
    return f'{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}' if m else None

def mascara(texto):
    texto = (texto or '').strip()
    return ' '.join(p[0] + '···' for p in texto.split() if p) if texto else ''

# ------------------------------------------------------------------ nombres fiscales ↔ clientes de la app
VACIAS = {'sl', 'slp', 'slu', 'sa', 's', 'l', 'u', 'p', 'y', 'i', 'de', 'del', 'la', 'el', 'en', 'and', 'the', 'co',
          'asesores', 'asesoria', 'assessoria', 'assessors', 'consultores', 'consulting', 'consultoria', 'consultancy',
          'grupo', 'grup', 'gestion', 'gestio', 'economistes', 'economistas', 'abogados', 'advocats', 'advisory', 'advisors',
          'auditores', 'auditors', 'economistas', 'services', 'servicios', 'serveis', 'soluciones', 'solutions', 'fiscales', 'sociedad', 'limitada', 'international',
          'internacional', 'asesoramiento', 'investment', 'holding', 'empresarial', 'lawyers', 'legal', 'cfo', 'smart'}
def toks(s):
    return [w for w in norm(s).split() if len(w) >= 3 and w not in VACIAS]

# Nombres fiscales que no se parecen al nombre comercial (comprobado a mano el 2-oct con el libro y el portal)
ALIAS = {
    'busbac': 'busbac', 'torres de aragon': 'centro-consulting', 'mg economistes': 'mg-economistes', 'consulting f sl': 'consulting-f',
    'j d consulting': 'j-d-consulting', 'montis': None, 'uhy fay': None, 'hacelerix': None, 'power global': None,
    # por fecha de alta y cuota (comprobar con Sofía, dudas_pintura.md): Legal4U = Laver (alta 1-sep) · Gold Global Projects = Gestió Plural (alta 16-sep)
    'legal advisory': 'laver', 'legal4u': 'laver', 'gold global': 'gestio-plural', 'expertos': 'greconsult', 'instagrafic': 'kiosko-box',
    'fountainhead': 'accompany', 'martinez jacal': 'emex', 'realfinance': 'impulsa-cfo', 'productika': 'akua',
    'solà coll': 'finexen', 'sola coll': 'finexen', 'strategic management': 'ecom-advisory', 'liebana': 'liebana-consulting',
    'jesus navarro': 'jenasa', 'aunexcon': 'oteca', 'forense': 'ip-forense', 'fitec': 'fitec-asesores', 'gemap': None,
    'bonet': 'bonet-asesores', 'segu': 'segu-assessors', 'ahedo': 'ahedo', 'ecija': 'ecija-advisory', 'deudout': 'deudot',
    'christian': 'christian-sanchez', 'mishel': 'gomez-y-carvacho', 'joan lluis vives': 'joan-lluis-vives',
    'gestanex': 'gestanex', 'tst consulting': 'tst-consulting', 'fuster lawyers': 'fusterguell', 'fuster guell': 'fusterguell',
}

def emparejador(clientes):
    """Devuelve f(nombre fiscal) → cliente_id | None, con alias manuales primero y tokens después."""
    idx = []
    for c in clientes:
        t = set(toks(c['nombre'])) | set(toks(c.get('libro') or ''))
        idx.append((c['id'], t))
    def f(nombre):
        n = norm(nombre)
        for k, v in ALIAS.items():
            if norm(k) in n: return v
        tn = set(toks(nombre))
        mejor, punt = None, 0
        for cid, t in idx:
            comun = len(tn & t) + 0.5 * sum(1 for a in tn for b in t if a != b and len(a) >= 5 and (a.startswith(b) or b.startswith(a)))
            if comun > punt: mejor, punt = cid, comun
        return mejor if punt >= 1 else None
    return f

# ------------------------------------------------------------------ 0 · lo común
def cargar_clientes():
    out = []
    for p in sorted((DATA / 'clientes').glob('*.json')):
        c = json.loads(p.read_text())
        F = c.get('fuentes') or {}
        g = lambda k: ((F.get(k) or {}).get('datos') or {})
        out.append({'id': c['id'], 'nombre': c['nombre'], 'activo_libro': c.get('activo_libro'), 'libro': (c.get('ids') or {}).get('libro'),
                    'L': g('libro'), 'H': g('horas'), 'H_meta': {k: (F.get('horas') or {}).get(k) for k in ('hora', 'estado', 'nota')},
                    'L_hora': (F.get('libro') or {}).get('hora')})
    return out

CLI = cargar_clientes()
NOMBRE = {c['id']: c['nombre'] for c in CLI}
casar = emparejador(CLI)
PERSONAS = {p['id']: p for p in (leer(DATA / 'personas.json') or [])}
ASIG = leer(DATA / 'asignaciones.json') or []
def vigente(a):
    return not a.get('hasta') or a['hasta'] >= HOY.isoformat()
ACCOUNT = {}
for a in ASIG:
    if a['silla'] == 'account' and vigente(a) and not a.get('suplencia') and (a.get('principal') or a['cliente_id'] not in ACCOUNT):
        ACCOUNT[a['cliente_id']] = a['persona_id']
alias_p = lambda pid: (PERSONAS.get(pid) or {}).get('alias') or (PERSONAS.get(pid) or {}).get('nombre') or pid
fuente('Asignaciones (fase 0 + respuestas de Mili)', 'ok', f'{len(ACCOUNT)} clientes con account', hora_fichero(DATA / 'asignaciones.json'))

FIN = leer(ENT / 'financiero_ro.json') or {}
AJ = leer(ENT / 'finanzas_ajustes.json') or {}
fuente('Panel financiero v29 (Holded, cierre de Sofía, libro)', 'ok' if FIN else 'sin datos', 'historia desde dic-2022; último mes cerrado por Sofía: ' + (FIN.get('cerr') or '—'), FIN.get('leido'))

# ------------------------------------------------------------------ 1 · Airtable (facturación de Sofía, lectura)
AT, at_estado, at_hora = con_cache('airtable', airtable_lineas, 'Airtable')
fuente('Airtable · Facturación mensual (solo lectura)', at_estado, f'{len(AT or [])} líneas (ago-oct)', at_hora)
MES_AT = {'2026-08': 'Agosto 2026', '2026-09': 'Septiembre 2026', '2026-10': 'Octubre 2026', '2026-11': 'Noviembre 2026'}
at_por_mes = defaultdict(list)
for x in AT or []:
    m = next((k for k, v in MES_AT.items() if v == x.get('Mes')), None)
    if not m: continue
    nombre = (x.get('Cliente') or '').replace('"', '').replace('\n', ' ').strip()
    x2 = {'rec': x.get('id'), 'nombre_fiscal': nombre, 'cliente_id': casar(nombre), 'importe': eur(x.get('Importe')) + eur(x.get('Importe especial')),
          'tipo': x.get('Tipo'), 'estado_cliente': x.get('Estado cliente'), 'estado_fact': x.get('Estado facturación'),
          'forma': x.get('Forma de pago'), 'alta': fecha_us(x.get('Alta cliente')), 'baja': fecha_us(x.get('Baja cliente'))}
    at_por_mes[m].append(x2)
at_oct = at_por_mes.get(MES, [])
at_cuota, at_recs = {}, defaultdict(list)
for x in at_oct:
    if x['cliente_id'] and x['tipo'] == 'Recurrente' and x['estado_cliente'] != 'Inactivo':
        at_cuota[x['cliente_id']] = at_cuota.get(x['cliente_id'], 0) + x['importe']     # dos sociedades = dos líneas (FusterGüell: 2 × 499,50)
        at_recs[x['cliente_id']].append(x['rec'])
at_proy = defaultdict(float)          # proyectos con fin (Jenasa, Optimalia): se facturan este mes, no son cuota recurrente
for x in at_oct:
    if x['cliente_id'] and x['tipo'] != 'Recurrente' and x['estado_cliente'] != 'Inactivo':
        at_proy[x['cliente_id']] += x['importe']; at_recs[x['cliente_id']].append(x['rec'])
at_cuota_sep = defaultdict(float)
for x in at_por_mes.get('2026-09', []):
    if x['cliente_id'] and x['tipo'] == 'Recurrente': at_cuota_sep[x['cliente_id']] += x['importe']
AT_TABLA = 'tblP2RuadyzE0VmaH'     # «Facturación mensual» (auditoría 25)
sin_casar_at = [x['nombre_fiscal'] for x in at_oct if not x['cliente_id'] and x['estado_cliente'] != 'Inactivo']
AT_RECURRENTE = R(sum(x['importe'] for x in at_oct if x['tipo'] == 'Recurrente' and x['estado_cliente'] != 'Inactivo'), 0)
AT_LINEAS = sum(1 for x in at_oct if x['tipo'] == 'Recurrente' and x['estado_cliente'] != 'Inactivo')

# ------------------------------------------------------------------ 2 · Holded (tesorería y facturas de venta)
def leer_holded():
    t = holded('invoicing/v1/treasury')
    desde = int(dt.datetime(2026, 4, 1).timestamp()); hasta = int(dt.datetime.combine(HOY, dt.time(23, 59)).timestamp())
    inv = holded('invoicing/v1/documents/invoice', starttmp=desde, endtmp=hasta)
    cuentas = [{'nombre': a.get('name', '').strip(), 'saldo': a.get('balance'), 'tipo': a.get('type')} for a in t]
    campos = ('id', 'docNumber', 'contactName', 'date', 'dueDate', 'subtotal', 'total', 'paymentsPending', 'paymentsTotal', 'paymentsRefunds', 'status', 'draft', 'tags')
    facturas = [{k: x.get(k) for k in campos} for x in inv]
    # Finanzas v3 (3-oct): facturas anteriores a abril que siguen sin cobrar (ene-2025 → mar-2026), mes a mes porque Holded
    # corta en 500 por llamada. Solo entran en los impagos: lo demás sigue leyendo desde abril.
    import calendar as _cal
    antiguas = []
    y, m = 2025, 1
    while (y, m) < (2026, 4):
        a = int(dt.datetime(y, m, 1).timestamp()); b = int(dt.datetime(y, m, _cal.monthrange(y, m)[1], 23, 59, 59).timestamp())
        antiguas += [{k: x.get(k) for k in campos} for x in holded('invoicing/v1/documents/invoice', starttmp=a, endtmp=b)
                     if (x.get('paymentsPending') or 0) > 0.01 and not x.get('draft') and x.get('status') != 3]
        m += 1
        if m > 12: y, m = y + 1, 1
    return {'cuentas': cuentas, 'facturas': facturas, 'antiguas': antiguas}

HD, hd_estado, hd_hora = con_cache('holded', leer_holded, 'Holded')
fuente('Holded (tesorería y facturas de venta)', hd_estado, f"{len((HD or {}).get('facturas', []))} facturas desde abril · {len((HD or {}).get('cuentas', []))} cuentas", hd_hora)
FACT = [x for x in (HD or {}).get('facturas', []) if not x.get('draft') and x.get('status') != 3]   # status 3 = anulada (F-26-412, auditoría 25)
ANTIGUAS = [x for x in (HD or {}).get('antiguas', []) if not x.get('draft') and x.get('status') != 3]   # sin cobrar de antes de abril (solo impagos)
for x in FACT + ANTIGUAS:
    x['fecha'] = dt.datetime.fromtimestamp(x['date']).date().isoformat() if x.get('date') else None
    x['vence'] = dt.datetime.fromtimestamp(x['dueDate']).date().isoformat() if x.get('dueDate') else x['fecha']
    x['cliente_id'] = casar(x.get('contactName') or '')

# ------------------------------------------------------------------ 3 · M18 · dinero por cliente
def horas_cli(c, cuota):
    """Horas consumidas (todos los que ven horas) y pautadas (= cuota ÷ tarifa, solo quien ve la cuota; auditoría 28 E-04)."""
    H = c['H'] or {}
    pautadas = R(cuota / TARIFA, 1) if cuota else None
    reserva = H.get('horas_presup_mes')
    aviso = bool(pautadas and reserva and abs(reserva - pautadas) / pautadas > 0.05)
    sep = H.get('horas_mes_ant')
    return ({'sep': sep, 'oct': H.get('horas_mes')},
            {'pautadas': pautadas,          # el % se calcula en pantalla: solo lo ve quien recibe horas Y cuota
             'aviso_cartera': f'La Cartera de ClickUp pauta {reserva} h (cuota vieja)' if aviso else None})

# Cuota de cada cliente: UNA fuente. Línea recurrente de octubre en Airtable (Sofía); si no hay, factura recurrente de octubre en Holded.
# El libro de clientes y la Cartera de ClickUp ya no dan cuota (auditoría 28 E-05). build_data.py debe leer fuentes_dinero/cuotas.json.
hd_cuota, hd_doc = defaultdict(float), {}
for x in FACT:
    if (x.get('fecha') or '')[:7] == MES and x.get('cliente_id') and 'puntual' not in [t.lower() for t in (x.get('tags') or [])]:
        hd_cuota[x['cliente_id']] += x.get('subtotal') or 0; hd_doc.setdefault(x['cliente_id'], x)
VERDAD = {v['cliente_id']: v for v in ((leer(DATA / 'verdad' / 'clientes.json') or {}).get('clientes') or [])} if isinstance((leer(DATA / 'verdad' / 'clientes.json') or {}).get('clientes'), list) else ((leer(DATA / 'verdad' / 'clientes.json') or {}).get('clientes') or {})

NUEVOS = leer(DATA / 'nuevos' / 'nuevos.json') or {}
ALTAS_90 = {a['cliente_id'] for a in NUEVOS.get('altas', []) if a.get('alta') and (HOY - dt.date.fromisoformat(a['alta'][:10])).days < 90}
# Firmados con día 0 pasado y sin ficha en Airtable (Sign vía M12 + columna «Cliente» de GHL): cuentan en la cuota (Tomás, 2-oct)
FIRMADOS_SIN_FICHA = {a['cliente_id'] for a in NUEVOS.get('altas', []) if a.get('alta') and a['alta'][:10] <= HOY.isoformat()} | {'marlex-consulting', 'think-value'}
# R12 (A-A2): lo facturado a cada cliente mes a mes (Holded, sin IVA, sin anuladas ni borradores, desde abril) para el periodo
# común. Clave cuota_*: solo llega a quien ve la cuota de ese cliente (servir.py, CLAVES_CUOTA).
fact_mes = defaultdict(lambda: defaultdict(float))
for x in FACT:
    if x.get('cliente_id') and x.get('fecha'):
        fact_mes[x['cliente_id']][x['fecha'][:7]] += x.get('subtotal') or 0
filas_cli, rent_tarifa, por_acc = [], [], defaultdict(lambda: {'clientes': 0, 'cuota': 0.0, 'pautadas': 0.0, 'sep': 0.0, 'nuevos': 0})
for c in CLI:
    L = c['L'] or {}
    estado = c['activo_libro'] or ('Firmado, sin libro' if c['id'] in ('marlex-consulting', 'think-value') else None)
    if estado in ('Baja',) and not at_cuota.get(c['id']):
        continue
    cuota, cuota_fuente = at_cuota.get(c['id']), 'Airtable (línea de octubre)'
    if not cuota and at_proy.get(c['id']):
        cuota, cuota_fuente = at_proy[c['id']], 'Airtable (proyecto con fin, cuota de octubre)'
    if not cuota and hd_cuota.get(c['id']):
        cuota, cuota_fuente = R(hd_cuota[c['id']]), 'Holded (factura de octubre)'
    if not cuota and c['id'] in FIRMADOS_SIN_FICHA:
        cuota, cuota_fuente = 1470.0, 'Acuerdo firmado, aún sin ficha en Airtable (1.470 €)'
    if not cuota: cuota_fuente = 'sin línea en Airtable ni factura en Holded'
    ver = VERDAD.get(c['id']) or {}
    nuevo = bool(ver.get('nuevo')) if ver else c['id'] in ALTAS_90          # verdad única (E0 ronda 5)
    acc = ver.get('account') if ver else ACCOUNT.get(c['id'])
    consumo, pautado = horas_cli(c, cuota)
    doc = hd_doc.get(c['id'])
    fila = {'cliente_id': c['id'], 'nombre': c['nombre'], 'account_id': acc, 'account': alias_p(acc) if acc else None,
            'estado_libro': estado, 'nicho': L.get('espec') or L.get('clasif'), 'nuevo': nuevo,
            'cuota': cuota, 'cuota_fuente': cuota_fuente, 'cuota_segmento': L.get('segmento'),
            'cuota_valor_vida': L.get('ltv'), 'cuota_vida_meses': L.get('vida_meses'), 'cuota_en_facturacion': bool(at_cuota.get(c['id'])),
            'cuota_horas': pautado, 'coste_horas': consumo,
            'cuota_facturado_mes': {m: R(v, 2) for m, v in sorted(fact_mes.get(c['id'], {}).items())},
            'facturas_holded_url': f"https://app.holded.com/sales/revenue#open:invoice-{doc['id']}" if doc else None,
            'facturas_holded_doc': doc['docNumber'] if doc else None,
            'facturas_airtable_url': f"https://airtable.com/app9OBjN9MiqIQVxI/{AT_TABLA}/{at_recs[c['id']][0]}" if at_recs.get(c['id']) else None}
    filas_cli.append(fila)
    if acc:
        p = por_acc[acc]; p['clientes'] += 1; p['cuota'] += cuota or 0; p['pautadas'] += pautado['pautadas'] or 0; p['sep'] += consumo['sep'] or 0; p['nuevos'] += int(nuevo)
    hrs = {**consumo, **pautado}
    # rentabilidad a tarifa: cuota de septiembre en Airtable (o la de octubre si no había) y horas de septiembre
    base = at_cuota_sep.get(c['id']) or (cuota if not nuevo else None)
    if base and hrs['sep'] is not None and estado not in ('Proyecto',):
        coste = hrs['sep'] * TARIFA
        rent_tarifa.append({'cid': c['id'], 'nombre': c['nombre'], 'account': fila['account'], 'nuevo': nuevo,
                            'coste': {'cuota_mes': base, 'horas': hrs['sep'], 'eur': R(coste, 0), 'margen': R(base - coste, 0),
                                      'margen_pct': R(100 * (base - coste) / base, 0)}})

rent_tarifa.sort(key=lambda r: r['coste']['margen_pct'])
filas_cli.sort(key=lambda f: -(f['cuota'] or 0))
dinero_cliente = {
    'formato': 1, 'modulo': 'dinero-cliente', 'generado': HORA, 'mes_cuota': MES, 'mes_horas': '2026-09',
    'cuota_tarifa_hora': TARIFA, 'tope_account': TOPE_ACCOUNT, 'facturado_desde': '2026-04',
    'cuota_fuente': 'Cuota de cada cliente: línea recurrente de octubre en el Airtable de Sofía (suma de sus sociedades); si no tiene, su factura de octubre en Holded. La misma para toda la app (fuentes_dinero/cuotas.json).',
    'imputacion': {'pct': 51.7, 'periodo': '16 al 30 de septiembre', 'texto': 'Solo se imputa en ClickUp el 51,7 % de la jornada: las horas y la rentabilidad salen infladas. Úsalo como aviso, no como prueba.'},
    'fuentes': [f for f in fuentes if f['fuente'].startswith(('Airtable', 'Asignaciones'))] + [
        {'fuente': 'ClickUp · horas por cliente', 'estado': 'viejo' if any(c['H_meta'].get('estado') == 'dato_viejo' for c in CLI) else 'ok',
         'detalle': 'horas de septiembre y de octubre en curso', 'hora': max((c['H_meta'].get('hora') or '') for c in CLI) or None},
        {'fuente': 'Libro de clientes (cerrado con Tomás 1-oct)', 'estado': 'ok', 'detalle': 'estado, vida y valor de vida (no la cuota)', 'hora': max((c['L_hora'] or '') for c in CLI) or None}],
    'clientes': filas_cli,
    'por_account': [{'account_id': k, 'account': alias_p(k), 'clientes': v['clientes'], 'cuota': R(v['cuota'], 0), 'nuevos': v['nuevos'],
                     'coste_horas': {'sep': R(v['sep'], 1)}, 'cuota_horas': {'pautadas': R(v['pautadas'], 1)}, 'huecos': TOPE_ACCOUNT - v['clientes']}
                    for k, v in sorted(por_acc.items(), key=lambda kv: -kv[1]['clientes'])],
    'rentabilidad': rent_tarifa,
}

# ------------------------------------------------------------------ 4 · M19 · finanzas (Sofía: admin · Tomás: direccion)
hoy_s = HOY.isoformat()
# 4.1 caja por banco (Holded en vivo)
cuentas = []
for a in (HD or {}).get('cuentas', []):
    if a['tipo'] in ('gateway', 'card') or not a.get('saldo'): continue
    usd = 'USD' in a['nombre'].upper()
    cuentas.append({'banco': a['nombre'].title().replace('Ppal', '').strip(), 'saldo': R(a['saldo']), 'moneda': 'USD' if usd else 'EUR',
                    'eur': R(a['saldo'] * USD_EUR if usd else a['saldo'], 0)})
cuentas.sort(key=lambda x: -x['eur'])
caja_total = R(sum(x['eur'] for x in cuentas), 0)
gasto3 = (FIN.get('tes') or {}).get('gasto3') or (FIN.get('tes') or {}).get('burn')
sin_conc = ((FIN.get('tes') or {}).get('vivo') or {}).get('sin_conciliar') or {}

# 4.2 facturado y cobrado del mes (Holded), impagos por antigüedad, devueltos
def mes_de(x): return (x.get('fecha') or '')[:7]
fact_mes = [x for x in FACT if mes_de(x) == MES]
fact_ant = [x for x in FACT if mes_de(x) == '2026-09']
def suma(L, k): return R(sum((x.get(k) or 0) for x in L), 2)
facturado_mes = suma(fact_mes, 'subtotal')
cobrado_mes_total = R(sum((x['total'] or 0) - (x['paymentsPending'] or 0) for x in fact_mes), 2)
pct_cobrado = R(100 * cobrado_mes_total / suma(fact_mes, 'total'), 1) if suma(fact_mes, 'total') else None
pct_cobrado_sep = R(100 * sum((x['total'] or 0) - (x['paymentsPending'] or 0) for x in fact_ant) / suma(fact_ant, 'total'), 1) if fact_ant else None
TRAMOS = [('Sin vencer', -10**6, 0), ('0-30 días', 0, 30), ('31-60 días', 31, 60), ('61-90 días', 61, 90), ('Más de 90 días', 91, 10**6)]
imp_filas = []
for x in FACT + ANTIGUAS:
    pend = x.get('paymentsPending') or 0
    if pend <= 0.01: continue
    dias = (HOY - dt.date.fromisoformat(x['vence'])).days if x.get('vence') else 0
    if mes_de(x) == MES and dias <= 5: dias = 0          # en cobro: el cargo SEPA del día 2 aún no ha entrado
    tramo = next(t for t, a, b in TRAMOS if (dias <= 0 and t == 'Sin vencer') or (dias > 0 and a <= dias <= b and t != 'Sin vencer'))
    fila = {'doc': x['docNumber'], 'nombre': NOMBRE.get(x['cliente_id']) or x.get('contactName'), 'fecha': x['fecha'], 'vence': x['vence'],
            'dias': max(dias, 0), 'importe': R(pend), 'tramo': tramo, 'devuelto': bool(x.get('paymentsRefunds')),
            'aviso': 'decide Tomás (60 días)' if dias > 60 else ('aviso al account (30 días)' if dias > 30 else None),
            'holded': f"https://app.holded.com/sales/revenue#open:invoice-{x['id']}"}
    if x.get('cliente_id'): fila['cliente_id'] = x['cliente_id']
    imp_filas.append(fila)
imp_filas.sort(key=lambda f: -f['dias'])
tramos = [{'tramo': t, 'importe': R(sum(f['importe'] for f in imp_filas if f['tramo'] == t), 0), 'n': sum(1 for f in imp_filas if f['tramo'] == t)} for t, _, _ in TRAMOS]
vencidos = [f for f in imp_filas if f['tramo'] != 'Sin vencer']
devueltos = [{k: f[k] for k in ('doc', 'nombre', 'fecha', 'importe', 'dias', 'holded', *(['cliente_id'] if 'cliente_id' in f else []))}
             for f in imp_filas if f['devuelto']]

# 4.3 firmas sin alta en facturación (Sign/GHL → Airtable de octubre)
VENTAS = leer(DATA / 'ventas_ro' / 'ventas_ro.json') or {}
firmas = []
vistos = set()
for a in NUEVOS.get('altas', []):
    cid = a.get('cliente_id'); vistos.add(cid)
    en_at = bool(at_cuota.get(cid))
    firmas.append({'cliente_id': cid, 'nombre': a.get('nombre'), 'firma': (a.get('firma') or '')[:10], 'alta': a.get('alta'),
                   'account': (a.get('account') or {}).get('nombre'), 'en_facturacion': en_at,
                   'dia0_pasado': bool(a.get('alta') and a['alta'] <= hoy_s)})
for cid, nom in (('marlex-consulting', 'Marlex Consulting'), ('think-value', 'Think Value')):   # firmados (MEM 1-oct) fuera de Sign/M12
    if cid not in vistos:
        firmas.append({'cliente_id': cid, 'nombre': nom, 'firma': None, 'alta': None, 'account': alias_p(ACCOUNT[cid]) if cid in ACCOUNT else None,
                       'en_facturacion': bool(at_cuota.get(cid)), 'dia0_pasado': True, 'nota': 'Firmado (GHL «Cliente», 1-oct); sin contrato en Zoho Sign leído por M12'})
sin_alta = [f for f in firmas if not f['en_facturacion']]

# 4.4 bajas y cambios de cuota del mes (doc de octubre para Sofía + Airtable)
cambios = []     # se rellena después de la cuota en tres líneas (mismo criterio: lo que Airtable aún no recoge)

# 4.5 calendario administrativo (06 Anexo A; mapa_enrutado.md:90-94)
CAL = [(1, 'Emisión de las facturas de cuota', 'Holded'), (2, 'Cargo de la remesa SEPA', 'Banco'), (5, 'Facturas de colaboradores', 'Holded'),
       (10, 'Cierre del mes para Tomás', 'Excel de cierre'), (20, 'Facturas del equipo', 'Holded'), (25, 'Pagos a proveedores y equipo', 'Banco')]
calendario = [{'dia': d, 'fecha': f'{MES}-{d:02d}', 'que': q, 'donde': w,
               'estado': 'hoy' if d == HOY.day else ('hecho' if d < HOY.day else 'proximo')} for d, q, w in CAL]

# 4.6 cuota en tres líneas (D-12): firmada · facturada · cobrada
cuota_at = AT_RECURRENTE
firmada_sin_at = [f for f in sin_alta if f['cliente_id'] in FIRMADOS_SIN_FICHA]
firmada = cuota_at + 1470 * len(firmada_sin_at)                     # cuota recurrente firmada
proyectos = [{'nombre': NOMBRE.get(x['cliente_id'], x['nombre_fiscal']), 'importe': x['importe']} for x in at_oct
             if x['tipo'] != 'Recurrente' and x['estado_cliente'] != 'Inactivo']
inactivos = [x for x in at_oct if x['estado_cliente'] == 'Inactivo']
# cambios del mes (doc de octubre para Sofía): solo los que Airtable todavía no recoge
cambios_aplicados, cambios_ya = [], []
at_sep_por_cli = {x['cliente_id']: x['importe'] for x in at_por_mes.get('2026-09', []) if x['cliente_id']}
for x in AJ.get('cambios_mes', []):
    v = (x.get('meses') or {}).get(MES)
    if not v: continue
    cid = casar(x['n'])
    linea = next((y for y in at_oct if y['cliente_id'] == cid), None)
    nueva = re.search(r'→\s*([\d.]+)', x['n'])                      # «670 → 520»: si Airtable ya pone 520, está recogido
    ya = (linea is None or linea['estado_cliente'] == 'Inactivo' or (cid in at_sep_por_cli and abs(linea['importe'] - at_sep_por_cli[cid]) > 0.5)
          or bool(nueva and abs(linea['importe'] - float(nueva.group(1).replace('.', ''))) < 0.5))
    (cambios_ya if ya else cambios_aplicados).append({'nombre': x['n'], 'importe': v})
for c in cambios_aplicados: cambios.append({'nombre': c['nombre'], 'importe': c['importe'], 'fuente': 'Doc de octubre para Sofía: aún no está en Airtable ni en la factura'})
for c in cambios_ya: cambios.append({'nombre': c['nombre'] + ' · ya recogido en Airtable', 'importe': 0, 'fuente': 'Nada que hacer'})
for x in AJ.get('salidas', []):
    cambios.append({'nombre': f"{x['n']} · deja de facturar desde {x.get('desde')}", 'importe': -x['v'], 'fuente': 'Próximos meses: no afecta a octubre'})
cuota_mes = firmada + sum(p['importe'] for p in proyectos)            # recurrente + proyectos con fin
facturable = cuota_mes + sum(c['importe'] for c in cambios_aplicados)
desglose = ([{'concepto': f'Cuota recurrente en el Airtable de Sofía ({AT_LINEAS} líneas activas)', 'importe': cuota_at, 'tipo': 'base'}]
            + [{'concepto': f'{f["nombre"]} · firmado, aún sin ficha en Airtable', 'importe': 1470, 'tipo': 'alta'} for f in firmada_sin_at]
            + [{'concepto': f'= Cuota recurrente firmada', 'importe': R(firmada, 0), 'tipo': 'total'}]
            + [{'concepto': f'{p["nombre"]} · proyecto con fin', 'importe': p['importe'], 'tipo': 'proyecto'} for p in proyectos]
            + [{'concepto': '= Cuota de octubre (recurrente + proyectos)', 'importe': R(cuota_mes, 0), 'tipo': 'total'}]
            + [{'concepto': f'{c["nombre"]}', 'importe': c['importe'], 'tipo': 'cambio'} for c in cambios_aplicados]
            + [{'concepto': '= Facturable en octubre', 'importe': R(facturable, 0), 'tipo': 'total'}]
            + [{'concepto': f'{x["nombre_fiscal"]} · baja: su línea sigue en Airtable como inactiva y no cuenta', 'importe': 0, 'tipo': 'info'} for x in inactivos]
            + [{'concepto': f'{c["nombre"]} · ya recogido en Airtable', 'importe': 0, 'tipo': 'info'} for c in cambios_ya])
# contraste con Holded: lo emitido en octubre frente a lo facturable, cliente a cliente
hd_mes_cli = defaultdict(float)
for x in fact_mes:
    hd_mes_cli[x.get('cliente_id') or ('?' + (x.get('contactName') or ''))] += x.get('subtotal') or 0
esperado = defaultdict(float)
for cid, v in at_cuota.items(): esperado[cid] += v
for cid, v in at_proy.items(): esperado[cid] += v
for f in firmada_sin_at: esperado[f['cliente_id']] += 1470
for c in cambios_aplicados:
    cid = casar(c['nombre'])
    if cid: esperado[cid] += c['importe']
contraste = []
for cid in sorted(set(esperado) | set(hd_mes_cli)):
    a, b = esperado.get(cid, 0), hd_mes_cli.get(cid, 0)
    if abs(a - b) > 0.5:
        contraste.append({'nombre': NOMBRE.get(cid) or cid.lstrip('?'), 'facturable': R(a, 0), 'emitido_holded': R(b, 0), 'diferencia': R(b - a, 0)})
cuota_tres = {'mes': MES, 'recurrente': R(firmada, 0), 'cuota_mes': R(cuota_mes, 0), 'facturable': R(facturable, 0), 'desglose': desglose,
              'pendientes_esperados': [x['n'] for x in AJ.get('pendientes_esperados', []) if casar(x['n']) not in FIRMADOS_SIN_FICHA],
              'contraste_holded': contraste,
              'firmada': R(firmada, 0),
              'facturada': R(facturado_mes, 0),
              'facturada_total': R(facturado_mes, 0), 'facturas_n': len(fact_mes),
              'cobrada': R(cobrado_mes_total / 1.21, 0), 'cobrado_pct': pct_cobrado, 'cobrado_pct_sep': pct_cobrado_sep,
              'nota': 'Tres cifras que nunca se suman: cuota recurrente (lo firmado cada mes), facturable del mes (con proyectos y cambios) y cobrada. Emitida y cobrada salen de Holded, sin IVA. El día 2 el cargo SEPA aún no ha entrado.'}

kpi = FIN.get('kpi') or {}
conc = FIN.get('conc') or {}
admin = {
    'hoy': hoy_s, 'calendario': calendario,
    'caja': {'fecha': hd_hora, 'cuentas': cuentas, 'total_eur': caja_total, 'sin_conciliar': sin_conc,
             'sin_conciliar_total': sum(sin_conc.values()) if sin_conc else None, 'cambio_usd': USD_EUR},
    'cuota_tres': cuota_tres,
    'impagos': {'tramos': tramos, 'filas': imp_filas[:80], 'vencido_total': R(sum(f['importe'] for f in vencidos), 0), 'vencido_n': len(vencidos),
                'mas_30': sum(1 for f in vencidos if f['dias'] > 30), 'mas_60': sum(1 for f in vencidos if f['dias'] > 60)},
    'devueltos': devueltos,
    'firmas_sin_alta': sin_alta, 'firmas_revisadas': len(firmas),
    'bajas_cambios': cambios,
    'dias_cobro': {'valor': kpi.get('dso'), 'texto': 'Sin las facturas del día 1 (las cobra el cargo SEPA del día 2). Panel financiero v29, 1-oct.'},
    'concentracion': {'uno': (conc.get('cuota') or {}).get('uno'), 'cinco': (conc.get('cuota') or {}).get('cinco'), 'diez': (conc.get('cuota') or {}).get('diez'),
                      'base': (conc.get('cuota') or {}).get('base'), 'uno_12m': conc.get('uno'), 'diez_12m': conc.get('diez'), 'primero_12m': conc.get('primero')},
    'meta_sin_factura': {'mes': '2026-09', 'gasto_meta': (FIN.get('meta_mes') or {}).get('2026-09'), 'texto': 'Gasto de Meta de septiembre sin factura en la contabilidad: Meta cobra por tarjeta y las facturas hay que bajarlas del administrador de anuncios.'},
    'sin_casar_airtable': sin_casar_at,
}

# 4.6 bis · gastos de 2026 corregidos (auditoría del cierre de Sofía, 25_AUDITORIA_CIERRE_SOFIA.md, 2-oct)
# El cierre suma las facturas en dólares y libras como si fueran euros. Aquí se toma cada línea de Datos_Gastos del cierre
# (categoría de Sofía) y, si Holded la tiene en otra divisa, se divide por SU tipo de cambio (currencyChange de la factura).
# Además: fuera las facturas repetidas (también repetidas en Holded) y se usan las de Holded que faltan o cambian (agosto).
# Rupias y pesos (3 facturas dudosas, 858 €) se dejan como están y se avisan. NO se copian los gastos del cierre.
import calendar, openpyxl
CIERRE_XLSX = ENT / '_crudo/finanzas/dashboard_cierre_31_08.xlsx'
CAT_GRUPO = {'Sueldos y salarios': 'Equipo', 'Equipo interno': 'Equipo', 'Colaboradores': 'Colaboradores', 'SAAS': 'Herramientas',
             'Marketing y publicidad': 'Publicidad propia', 'Eventos y patrocinios': 'Eventos', 'Formaciones': 'Estructura', 'Compras material': 'Estructura',
             'Dietas': 'Estructura', 'Gestoría': 'Estructura', 'Otros servicios': 'Estructura', 'Comisiones bancarias': 'Estructura', 'Otros': 'Estructura'}
# Holded las marca en dólares, pero el cargo de Wise es en euros (auditoría 25, CSV de mayo): euros, a confirmar con el PDF
EUROS_A_CONFIRMAR = {'A6F8E4B6-0020': 'OpenAI', 'ES2026-6896': 'ClickUp (Mango Technologies)'}
ENTREGA_CATS = {'Equipo interno', 'Colaboradores', 'SAAS'}      # «coste de entrega» del PnL de Sofía (ene: 43.298 + 3.000 + 3.987 = 50.285)

def leer_compras_2026():
    todo = {}
    for m in range(1, 10):
        a = dt.date(2026, m, 1); b = dt.date(2026, m, calendar.monthrange(2026, m)[1])
        for x in holded('invoicing/v1/documents/purchase', starttmp=int(dt.datetime.combine(a, dt.time()).timestamp()),
                        endtmp=int(dt.datetime.combine(b, dt.time(23, 59, 59)).timestamp())):
            todo[x['id']] = {k: x.get(k) for k in ('id', 'docNumber', 'contactName', 'currency', 'currencyChange', 'subtotal', 'date', 'draft')}
    return list(todo.values())

COMPRAS, cp_estado, cp_hora = con_cache('holded_compras_2026', leer_compras_2026, 'Holded compras')
fuente('Holded · compras 2026 con su divisa', cp_estado, f'{len(COMPRAS or [])} facturas recibidas (ene-sep) para convertir el cierre', cp_hora)
nkey = lambda t: (norm(t).split() or [''])[0]
gastos_corr = None
if COMPRAS and CIERRE_XLSX.exists():
    for x in COMPRAS:
        x['f'] = dt.datetime.fromtimestamp(x['date']).date().isoformat(); x['cur'] = (x.get('currency') or 'eur').lower(); x['doc'] = (x.get('docNumber') or '').strip()
    HC = [x for x in COMPRAS if not x.get('draft') and x['f'] < '2026-09-01']
    por_doc = defaultdict(list)
    for x in HC: por_doc[x['doc']].append(x)
    sin_num = defaultdict(list)
    for x in HC:
        if x['doc'] in ('', '-'): sin_num[(x['f'][:7], nkey(x.get('contactName')))].append(x)
    wb = openpyxl.load_workbook(CIERRE_XLSX, data_only=True, read_only=True)
    filas = []
    for r in list(wb['Datos_Gastos'].iter_rows(values_only=True))[2:]:
        if len(r) < 7 or not isinstance(r[1], dt.datetime) or r[6] is None: continue
        filas.append({'m': r[1].strftime('%Y-%m'), 'doc': str(r[2] or '').strip(), 'prov': str(r[3] or ''), 'cat': r[5] or 'Otros', 'v': float(r[6])})
    corr = defaultdict(lambda: defaultdict(float)); cierre_mes = defaultdict(float)
    ajustes = Counter(); repetidas = []; vistos = Counter(); usados = set()
    for f in filas:
        cierre_mes[f['m']] += f['v']
        v = f['v']
        k = (f['doc'], f['prov'], round(f['v'], 2))
        if f['doc'] not in ('', '-') and vistos[k]:
            repetidas.append({'doc': f['doc'], 'proveedor': f['prov'], 'mes': f['m'], 'importe': R(f['v'])}); ajustes['repetidas'] += f['v']; continue
        vistos[k] += 1
        if f['doc'] in ('', '-'):
            cand = [x for x in sin_num.get((f['m'], nkey(f['prov'])), []) if x['id'] not in usados and abs(x['subtotal'] - f['v']) < 0.6]
        else:
            cand = [x for x in por_doc.get(f['doc'], []) if x['id'] not in usados and (abs(abs(x['subtotal']) - abs(f['v'])) < 0.6 or (x['cur'] == 'eur' and abs(x['subtotal'] * 1.21 - f['v']) < 0.6))]   # abonos: el cierre los lleva en negativo
            cand.sort(key=lambda x: (nkey(x.get('contactName')) != nkey(f['prov']), abs(x['subtotal'] - f['v'])))
        if not cand and f['v'] < 0 and f['doc'] not in ('', '-'):   # abono parcial de una factura en divisa (Windsor TZT4XHFM-0002): mismo tipo
            cand = [dict(x, id=x['id'] + '-abono') for x in por_doc.get(f['doc'], []) if x['cur'] in ('usd', 'gbp')][:1]
        if not cand and f['m'] == '2026-08':      # factura de agosto renumerada en Holded y cargada con IVA (KLIP-0366 → KLIP-0367)
            cand = [x for x in HC if x['f'][:7] == '2026-08' and x['id'] not in usados and x['cur'] == 'eur' and nkey(x.get('contactName')) == nkey(f['prov'])
                    and abs(x['subtotal'] * 1.21 - f['v']) < 0.6 and x['doc'] not in {g['doc'] for g in filas if nkey(g['prov']) == nkey(f['prov'])}]
        h = cand[0] if cand else None
        if h:
            usados.add(h['id'])
            if f['doc'] in EUROS_A_CONFIRMAR:
                ajustes['euros_a_confirmar'] += 0       # Holded dice dólares; el cargo de Wise dice euros: se dejan en euros
            elif h['cur'] in ('usd', 'gbp') and h.get('currencyChange'):
                v = f['v'] / h['currencyChange']; ajustes[h['cur']] += f['v'] - v
            elif h['cur'] == 'eur' and abs(h['subtotal'] - f['v']) >= 0.6:
                v = h['subtotal']; ajustes['iva_cargado'] += f['v'] - v           # cargada con IVA en el cierre (KLIP-0367)
        corr[f['m']][f['cat']] += v
    faltan = [x for x in HC if x['f'][:7] == '2026-08' and x['doc'] not in ('', '-') and x['id'] not in usados]
    for x in faltan:
        v = x['subtotal'] / x['currencyChange'] if x['cur'] != 'eur' and x.get('currencyChange') else x['subtotal']
        corr['2026-08']['Colaboradores'] += v; ajustes['faltan_agosto'] += -v
    dudosas = [{'mes': x['f'][:7], 'divisa': x['cur'].upper(), 'doc': x['doc'] or 'sin número'} for x in HC if x['cur'] in ('ars', 'idr')]
    gastos_corr = {'corr': corr, 'cierre_mes': cierre_mes, 'ajustes': ajustes, 'repetidas': repetidas, 'dudosas': dudosas, 'faltan': len(faltan)}

# 4.7 dirección (solo Tomás): beneficio, margen, historia, top 20, proveedores, cuota acumulada y escenario, caja, equipo agregado
pyg = [dict(m) for m in (FIN.get('pyg') or [])]
gm = {g['m']: dict(g) for g in (FIN.get('gmes') or [])}
if gastos_corr:                                  # PnL y gastos por partida de ene-ago con la conversión hecha
    for m in pyg:
        c = gastos_corr['corr'].get(m['m'])
        if not c: continue
        m['gas_cierre'] = m['gas']; m['bai_cierre'] = m['bai']
        m['gas'] = R(sum(c.values())); m['entrega'] = R(sum(v for k, v in c.items() if k in ENTREGA_CATS)); m['estructura'] = R(m['gas'] - m['entrega'])
        m['mb'] = R(m['ing'] - m['entrega']); m['bai'] = R(m['ing'] - m['gas']); m['real'] = R(m['bai'] - (m.get('sin_factura') or 0))
        g = gm.setdefault(m['m'], {'m': m['m']})
        for grupo in ('Equipo', 'Colaboradores', 'Herramientas', 'Publicidad propia', 'Eventos', 'Estructura', 'Impuestos'):
            g[grupo] = R(sum(v for k, v in c.items() if CAT_GRUPO.get(k, 'Estructura') == grupo))
        g['total'] = m['gas']; g['src'] = 'Cierre de Sofía convertido con el tipo de Holded'; g['ing'] = m['ing']
ult = pyg[-1] if pyg else {}
anio = {k: R(sum((m.get(k) or 0) for m in pyg), 0) for k in ('ing', 'gas', 'bai', 'real', 'plan_res', 'plan_ing', 'plan_gas', 'entrega', 'sin_factura', 'gas_cierre', 'bai_cierre')}
gan = {y: dict(v) for y, v in (FIN.get('gan') or {}).items()}
if gastos_corr:
    g26 = defaultdict(float)
    for m, g in gm.items():
        if m.startswith('2026') and m <= '2026-08':
            for k in ('Equipo', 'Colaboradores', 'Herramientas', 'Publicidad propia', 'Eventos', 'Estructura', 'Impuestos', 'total', 'ing'): g26[k] += g.get(k) or 0
    gan['2026'] = {k: R(v, 0) for k, v in g26.items()}; gan['2026']['nota'] = 'ene-ago, cierre convertido a euros'
# 2025 y 2026 en la misma moneda (euros), los mismos meses (ene-ago)
def suma_meses(y, k): return R(sum((gm.get(f'{y}-{i:02d}') or {}).get(k) or 0 for i in range(1, 9)), 0)
comparacion = [{'anio': y, 'ingresos': suma_meses(y, 'ing'), 'gastos': suma_meses(y, 'total'),
                'equipo': R(suma_meses(y, 'Equipo') + suma_meses(y, 'Colaboradores'), 0)} for y in (2025, 2026)]
for c in comparacion:
    c['beneficio'] = R(c['ingresos'] - c['gastos'], 0); c['peso_equipo'] = R(100 * c['equipo'] / c['ingresos'], 1) if c['ingresos'] else None
EQ = leer(ENT / 'equipo_ro.json') or {}
areas = []
otras_n, otras_v = 0, 0.0
for nombre, (n, v) in (EQ.get('areas') or {}).items():
    if n >= 3: areas.append({'area': nombre, 'personas': n, 'coste_mes': R(v, 0)})
    else: otras_n += n; otras_v += v
if otras_n:
    areas.append({'area': 'Otras áreas juntas (paid, vídeo y SEO)', 'personas': otras_n, 'coste_mes': R(otras_v, 0)})
assert all(a['personas'] >= 3 for a in areas), 'un área de menos de 3 personas dejaría deducir un sueldo (D-89)'
ago = gm.get(FIN.get('cerr') or '2026-08') or {}
coste_equipo_mes = (ago.get('Equipo') or 0) + (ago.get('Colaboradores') or 0)
personas_n = kpi.get('personas') or 32
coste_hora_real = R(coste_equipo_mes / (personas_n * HORAS_MES), 2) if coste_equipo_mes else None
rent_real = []
for r in rent_tarifa:
    if coste_hora_real is None: break
    c = r['coste']; cr = c['horas'] * coste_hora_real
    rent_real.append({'cid': r['cid'], 'nombre': r['nombre'], 'account': r['account'], 'cuota_mes': c['cuota_mes'], 'horas': c['horas'],
                      'coste_real': R(cr, 0), 'margen_real': R(c['cuota_mes'] - cr, 0), 'margen_real_pct': R(100 * (c['cuota_mes'] - cr) / c['cuota_mes'], 0),
                      'margen_tarifa_pct': c['margen_pct']})
rent_real.sort(key=lambda r: r['margen_real_pct'])

contratos = VENTAS.get('contratos') or []
pend_cuota = sum((x.get('cuota_mensual') or 1470) for x in contratos)
plan = FIN.get('plan') or {}
direccion = {
    'mes_cerrado': FIN.get('cerr'), 'leido': FIN.get('leido'),
    'numero': {'mes': ult.get('m'), 'beneficio': ult.get('bai'), 'beneficio_real': ult.get('real'), 'ingresos': ult.get('ing'),
               'gastos': ult.get('gas'), 'plan_res': ult.get('plan_res'), 'margen_bruto': ult.get('mb'),
               'margen_pct': R(100 * ult['bai'] / ult['ing'], 1) if ult.get('ing') else None,
               'margen_real_pct': R(100 * ult['real'] / ult['ing'], 1) if ult.get('ing') else None,
               'sin_factura': ult.get('sin_factura'), 'sin_factura_texto': 'Techo: unos 1.500-2.000 € del año (≈ 430 € en agosto) sí tienen factura y se cuentan dos veces.',
               'objetivo_norte': 30000, 'objetivo_texto': '30.000 € de beneficio al mes a final de 2027'},
    'anio': anio, 'pyg': pyg, 'comparacion_2025_2026': comparacion,
    'kpi': {**{k: kpi.get(k) for k in ('mb_serie', 'bai_serie', 'nrr', 'nrr_serie', 'churn_n', 'churn_serie', 'ltv_media', 'ltv_mediana',
                                     'vida_baja_mediana', 'vida_act_media', 'ing_persona', 'personas', 'activos', 'cuota_media', 'crec12', 'crec3')},
            'mb': R(100 * (anio['ing'] - anio['entrega']) / anio['ing'], 1) if anio.get('ing') else None,
            'bai': R(100 * anio['bai'] / anio['ing'], 1) if anio.get('ing') else None,
            'bai_real': R(100 * anio['real'] / anio['ing'], 1) if anio.get('ing') else None,
            'peso_equipo_anio': next((c['peso_equipo'] for c in comparacion if c['anio'] == 2026), None)},
    'ingresos': FIN.get('ing') or [], 'anios': FIN.get('anios') or [], 'altas_bajas': FIN.get('ab') or [], 'puente': FIN.get('puente') or [],
    'top_total': (FIN.get('top') or {}).get('total') or [], 'top_cuota': (FIN.get('top') or {}).get('cuota') or [],
    'proveedores_12m': (FIN.get('prov12') or {}).get('filas') or [], 'proveedores_12m_total': (FIN.get('prov12') or {}).get('total'),
    'gastos_por_mes': [gm[k] for k in sorted(gm)], 'gastos_por_anio': gan,
    'cuota_recurrente': {'actual': R(firmada, 0), 'cuota_mes': R(cuota_mes, 0), 'facturable': R(facturable, 0), 'desglose': desglose,
                         'facturacion_airtable': cuota_at, 'clientes': AT_LINEAS + len(firmada_sin_at),
                         'si_firman': R(firmada + pend_cuota, 0), 'si_firman_mes': R(cuota_mes + pend_cuota, 0), 'pendientes': [{'nombre_m': x.get('nombre_m'), 'cuota': x.get('cuota_mensual') or 1470,
                                                                                    'dias': x.get('dias'), 'abierta': x.get('abierta')} for x in contratos],
                         'objetivo_dic': plan.get('objetivo') or 150000, 'serie': [{'m': i['m'], 'cuota': i['cuota']} for i in (FIN.get('ing') or [])],
                         'plan_mrr': plan.get('mrr'), 'plan_texto': 'Plan de octubre: 95.921 → 135.196 → 150.991 € de octubre a diciembre. Escenario prudente, sin firmar: 99.747 €.'},
    'caja': {'total': caja_total, 'gasto_medio': R(anio['gas'] / max(1, len([m for m in pyg if m.get('gas')])), 0), 'meses': R(caja_total / R(anio['gas'] / max(1, len([m for m in pyg if m.get('gas')])), 0), 2),
             'cierre_31ago': (FIN.get('tes') or {}).get('total'), 'flujo_neto_anio': 22648,
             # R12: los meses que daba la caja del 31-ago con el MISMO gasto medio (una sola regla de «meses de caja»)
             'meses_31ago': R(((FIN.get('tes') or {}).get('total') or 0) / R(anio['gas'] / max(1, len([m for m in pyg if m.get('gas')])), 0), 2) if (FIN.get('tes') or {}).get('total') else None,
             'gasto_medio_texto': 'gasto medio al mes de enero a agosto, con los dólares convertidos',
             'texto': 'Meses que aguanta la caja SI NO ENTRARA NADA: caja de hoy ÷ gasto medio de ene-ago corregido. El flujo real del año es positivo (+22.648 € a 31-ago, cierre de Sofía, fiable).'},
    'concentracion': conc,
    'equipo': {'areas': areas, 'total_mes': R(sum(a['coste_mes'] for a in areas), 0), 'nota': 'Coste por área de 3 o más personas; las áreas pequeñas van juntas. Nómina de septiembre en euros, del modelo de equipo del panel de resultados. Coste del mes cerrado: facturas del equipo convertidas a euros con el tipo de Holded.',
               'cierre_mes': FIN.get('cerr'), 'coste_equipo_cierre': R(coste_equipo_mes, 0), 'personas': personas_n,
               'peso_ingresos': R(100 * coste_equipo_mes / ago['ing'], 1) if ago.get('ing') else None, 'presupuesto': 40000},
    'coste_hora_real': coste_hora_real, 'coste_hora_texto': f'Coste real por hora en {["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"][int((FIN.get("cerr") or "2026-08")[5:7]) - 1]}: equipo y colaboradores entre {personas_n} personas × 128 h.',
    'rentabilidad_real': rent_real,
    'correccion_cierre': {'gastos_cierre': anio.get('gas_cierre'), 'gastos': anio.get('gas'), 'beneficio_cierre': anio.get('bai_cierre'), 'beneficio': anio.get('bai'),
                          'mes_beneficio_cierre': ult.get('bai_cierre'), 'texto': 'El cierre de Sofía sumaba las facturas en dólares como euros. Aquí, cada factura convertida con el tipo de Holded.'},
}

# 4.8 · fiabilidad del cierre (25_AUDITORIA_CIERRE_SOFIA.md, 2-oct): qué hoja se puede usar y qué no
HOJAS = [('Datos de ventas', 'fiable', '488 facturas = Holded una a una; quita bien las 4 anuladas'),
         ('Bancos', 'fiable', 'saldos encadenados movimiento a movimiento; en Wise USD faltan 19 $'),
         ('Tesorería (saldos)', 'fiable', 'caja a 31-ago 74.513 € y flujo neto del año +22.648 €; saldos escritos a mano'),
         ('Tipo de cambio', 'fiable', 'correcta, pero solo se aplica al saldo en dólares, no a las facturas'),
         ('Movimientos sin conciliar', 'errores', 'faltan 17 de 394; unos 1.500-2.000 € de «gasto sin factura» sí tienen factura (doble conteo)'),
         ('Resumen ejecutivo', 'errores', 'hereda el dólar; «cuota» y «gasto último mes» leen enero; nuevos 69 (son 20); el «runway» de 1,4 meses no vale'),
         ('Cuenta de resultados', 'errores', 'fórmulas bien, pero personal y herramientas inflados todos los meses'),
         ('Ingresos y clientes', 'errores', 'cuota mensual bien; «último mes», clientes nuevos de enero y top 10 pegado a mano, mal'),
         ('Real frente a presupuesto', 'errores', 'compara con 8/12 del año (496.330 €) en vez del plan mes a mes (484.495 €)'),
         ('Datos de gastos', 'no_fiable', '695 facturas en dólares sumadas como euros (+39.568 €), 4 en libras (−164 €) y 4 repetidas'),
         ('Gastos y proveedores', 'no_fiable', 'hereda el dólar; la media divide entre 5 meses; enseña lo que cobra cada persona'),
         ('Cashflow real', 'no_fiable', 'mete ≈ 585.000 € de traspasos entre cuentas propias como cobros'),
         ('Impuestos', 'no_fiable', 'IVA escrito a mano y retención negativa: pedir a la gestoría los modelos 303, 111 y 202'),
         ('Validación', 'no_fiable', 'lista de categorías escrita a mano y hoja oculta: no controla nada')]
aj = (gastos_corr or {}).get('ajustes', {})
fiab = {'fuente': '25_AUDITORIA_CIERRE_SOFIA.md (2-oct-2026, solo lectura)', 'hojas': [{'hoja': a, 'veredicto': b, 'por_que': c} for a, b, c in HOJAS],
        'repetidas': (gastos_corr or {}).get('repetidas') or [], 'dudosas': (gastos_corr or {}).get('dudosas') or [], 'dudosas_importe': 858,
        'euros_a_confirmar': [{'doc': k, 'proveedor': v, 'mes': '2026-05', 'texto': 'Holded la marca en dólares; el cargo de Wise es en euros. Se cuenta en euros, a confirmar con el PDF.'} for k, v in EUROS_A_CONFIRMAR.items()],
        'conversion': {'usd': R(aj.get('usd', 0), 0), 'gbp': R(aj.get('gbp', 0), 0), 'repetidas': R(aj.get('repetidas', 0), 0),
                       'iva_cargado': R(aj.get('iva_cargado', 0), 0), 'faltan_agosto': R(aj.get('faltan_agosto', 0), 0),
                       'total': R(sum(aj.values()), 0)},
        'recomendacion': 'Para el cierre de septiembre: convertir cada factura en divisa con el tipo de cambio de Holded antes de pegarla (columnas «Divisa», «Importe original» y «Subtotal (€) = importe ÷ tipo») y comprobar en Validación que la suma de gastos = Holded convertido del mes, con aviso en rojo si se separan más de 50 €. Solo con eso, septiembre ya no infla unos 4.500 €.',
        'otras': ['Arreglar los indicadores que leen enero («último mes» con INDEX y MAX) y quitar lo pegado a mano.',
                  'Cerrar el gasto sin factura con la conciliación de Holded: buscar antes si ya hay factura de ese proveedor ese mes.',
                  'Borrar en Holded las 4 facturas repetidas y revisar las 3 en rupias y pesos y la F-26-408 emitida a Zoho.',
                  'Impuestos con los modelos presentados por la gestoría; cashflow sin traspasos internos; plan mes a mes.']}
admin['fiabilidad'] = fiab                       # Sofía la ve: es su cierre (sin beneficio ni peso del equipo)
# R12 (A-A2): facturado mes a mes para el periodo común. Es la MISMA serie de ingresos de dirección (FIN['ing']), sin margen
# ni gasto, para que Sofía y Tomás vean la misma cifra de facturación al elegir un periodo.
admin['facturado_mes'] = [{'m': x['m'], 'total': x.get('total'), 'cuota': x.get('cuota'), 'puntual': R((x.get('puntual') or 0) + (x.get('extra') or 0), 2),
                           'rect': x.get('rect'), 'n': x.get('n'), 'cobrado_pct': x.get('cobrado_pct'), 'curso': bool(x.get('curso'))}
                          for x in (FIN.get('ing') or [])]

finanzas = {'formato': 1, 'modulo': 'finanzas', 'generado': HORA, 'mes': MES,
            'fuentes': [f for f in fuentes if not f['fuente'].startswith('Asignaciones')],
            'admin': admin, 'direccion': [direccion]}

# ------------------------------------------------------------------ 5 · M16 · de qué anuncio viene cada conversión + previsión de altas
ATR = leer(ENT / 'atribucion_anuncios.json') or []
COMO = {'id': ('Seguro', 'id del anuncio en la atribución de GHL'), 'único': ('Seguro', 'etiqueta «anuncio:» que solo casa con un anuncio'),
        'día': ('Muy probable', 'solo ese anuncio registró leads ese día'), 'hora': ('Muy probable', 'la hora de alta casa con los leads por hora de Meta'),
        'activo': ('Probable', 'el único anuncio encendido ese día'), 'hora sin etiqueta': ('Probable', '/reuniones sin UTM: por la hora'),
        'dudoso': ('Uno de dos', 'dos anuncios posibles'), 'manual': ('Dicho por Tomás', 'origen contado por Tomás'),
        'sin anuncio': ('Sin anuncio', 'bio de Instagram, web, referidos o Zoho')}
conv = []
for x in ATR:
    conf, por_que = COMO.get(x.get('como'), ('Sin anuncio', x.get('como') or ''))
    conv.append({'id': x.get('cid'), 'nombre_m': mascara(x.get('nombre')), 'anuncio': x.get('anuncio') if conf != 'Sin anuncio' else None,
                 'campana': x.get('campana'), 'conjunto': x.get('conjunto'), 'como': x.get('como'), 'confianza': conf, 'por_que': por_que,
                 'etapa': x.get('etapa'), 'alta': x.get('alta'), 'citas': x.get('citas') or 0, 'cliente': x.get('etapa') == 'Cliente',
                 'setter': '_closer', 'ghl': f"https://app.gohighlevel.com/v2/location/{LOC_RO}/contacts/detail/{x.get('cid')}"})
por_anuncio = defaultdict(lambda: {'conversiones': 0, 'citas': 0, 'clientes': 0, 'seguras': 0, 'campana': None})
for c in conv:
    k = c['anuncio'] or 'Sin anuncio medible'
    p = por_anuncio[k]; p['conversiones'] += 1; p['citas'] += int(c['citas'] > 0); p['clientes'] += int(c['cliente'])
    p['seguras'] += int(c['confianza'] in ('Seguro', 'Muy probable', 'Dicho por Tomás')); p['campana'] = p['campana'] or c['campana']
anuncios = sorted(({'anuncio': k, **v} for k, v in por_anuncio.items()), key=lambda r: (r['anuncio'] == 'Sin anuncio medible', -r['clientes'], -r['conversiones']))
conf_n = Counter(c['confianza'] for c in conv)

# previsión de altas (embudo de GHL de hoy × tasas de septiembre) frente a huecos de los accounts (≤ 12, D-07)
sep = (VENTAS.get('meses') or {}).get('2026-09') or {}
tab = VENTAS.get('tablero_hoy') or {}
def tasa(a, b): return (sep.get(a) or 0) / sep[b] if sep.get(b) else 0
t_contrato = tasa('firmados', 'acuerdos')            # acuerdo enviado → firmado
t_propuesta = tasa('firmados', 'propuestas')
t_cita = tasa('firmados', 'citas')
pipe = {'contratos': tab.get('Contrato enviado', 0), 'propuestas': tab.get('Propuesta enviada', 0), 'citas': tab.get('Cita agendada', 0),
        'piden_reunion': tab.get('Pidió reunión · sin hueco', 0)}
esperadas = pipe['contratos'] * t_contrato + pipe['propuestas'] * t_propuesta + (pipe['citas'] + pipe['piden_reunion']) * t_cita
huecos = []
for pid, v in por_acc.items():
    p = PERSONAS.get(pid) or {}
    if p.get('puesto_principal') != 'account' or p.get('estado') not in (None, 'activo'): continue   # Agus pasa a técnica; Coti y Tomás no cuentan
    h = TOPE_ACCOUNT - v['clientes']
    huecos.append({'persona_id': pid, 'nombre': alias_p(pid), 'clientes': v['clientes'], 'nuevos': v['nuevos'], 'huecos': h,
                   'estado': 'rojo' if h <= 0 else ('ambar' if v['nuevos'] >= 4 else 'verde'),
                   'nota': 'en el tope' if h <= 0 else (f"{v['nuevos']} arranques a la vez" if v['nuevos'] >= 4 else None)})
huecos.sort(key=lambda x: -x['huecos'])
huecos_total = sum(max(0, x['huecos']) for x in huecos)
huecos_utiles = sum(max(0, x['huecos']) for x in huecos if x['nuevos'] < 4)
sin_account = [NOMBRE[c['cliente_id']] for c in filas_cli if not c['account_id'] and c['estado_libro'] == 'Activo']
prevision = {
    'pipeline': pipe,
    'tasas': {'contrato': R(t_contrato, 3), 'propuesta': R(t_propuesta, 3), 'cita': R(t_cita, 3),
              'texto': f"Tasas de septiembre: de acuerdo enviado a firma {sep.get('firmados')}/{sep.get('acuerdos')}, de propuesta {sep.get('firmados')}/{sep.get('propuestas')}, de cita reservada {sep.get('firmados')}/{sep.get('citas')}."},
    'altas_esperadas': R(esperadas, 1), 'objetivo_mes': VENTAS.get('objetivo_firmados_mes'),
    'firmados_mes': (VENTAS.get('meses') or {}).get(MES, {}).get('firmados'),
    'tope': TOPE_ACCOUNT, 'huecos_total': huecos_total, 'huecos_utiles': huecos_utiles, 'accounts': huecos,
    'sin_account': sin_account,
    'cabe': esperadas <= huecos_utiles,
    'texto': (f'Con el embudo de hoy entrarían unas {esperadas:.0f} altas en las próximas semanas. Hay {huecos_total} huecos hasta 12 por account; '
              f'quitando a quien ya tiene 4 o más arranques, {huecos_utiles}. ' + ('Cabe.' if esperadas <= huecos_utiles else 'No cabe: hay que repartir o contratar antes de firmar más.')),
}
anuncios_doc = {'formato': 1, 'modulo': 'ventas-ro', 'generado': HORA,
                'fuente': {'fichero': 'atribucion_anuncios.json (panel v30)', 'hora': hora_fichero(ENT / 'atribucion_anuncios.json'),
                           'campos_ghl': 'Anuncio de origen · id de Meta · cómo se sabe (149 fichas escritas el 2-oct)', 'panel': 'https://claude.ai/artifact/WeCVRWFTxD3MMdU2jb9siH'},
                'resumen': {'total': len(conv), 'seguros': conf_n['Seguro'] + conf_n['Muy probable'], 'probables': conf_n['Probable'] + conf_n['Uno de dos'],
                            'dichos': conf_n['Dicho por Tomás'], 'sin_anuncio': conf_n['Sin anuncio'],
                            'clientes': sum(1 for c in conv if c['cliente']), 'clientes_de_anuncio': sum(1 for c in conv if c['cliente'] and c['anuncio'])},
                'por_confianza': [{'confianza': k, 'n': n} for k, n in conf_n.most_common()],
                'por_anuncio': anuncios, 'conversiones': conv, 'prevision': prevision}

# ------------------------------------------------------------------ 6 · puerta de secretos y escritura
# Auditoría 27 (M5 y A3): lo de dirección y la rentabilidad van en ficheros propios con «puestos» en reglas_permisos.json,
# no protegidos por el nombre de una lista.
rentabilidad_doc = {'formato': 1, 'modulo': 'dinero-cliente', 'generado': HORA, 'tarifa_hora': TARIFA, 'rentabilidad': dinero_cliente.pop('rentabilidad')}
direccion_doc = {'formato': 1, 'modulo': 'finanzas', 'generado': HORA, 'direccion': finanzas.pop('direccion')}
finanzas['direccion'] = []
cuotas_doc = {'generado': HORA, 'mes': MES, 'regla': dinero_cliente['cuota_fuente'],
              'cuotas': {f['cliente_id']: {'cuota': f['cuota'], 'fuente': f['cuota_fuente']} for f in filas_cli}}
salidas = {DATA / 'dinero_cliente' / 'dinero_cliente.json': dinero_cliente, DATA / 'dinero_cliente' / 'rentabilidad.json': rentabilidad_doc,
           DATA / 'finanzas' / 'finanzas.json': finanzas, DATA / 'finanzas' / 'direccion.json': direccion_doc,
           DATA / 'ventas_ro_extra' / 'anuncios.json': anuncios_doc, AQUI / 'cuotas.json': cuotas_doc}
mal = {str(r): escanear(o)[:5] for r, o in salidas.items() if escanear(o)}
if mal:
    print('PUERTA DE SECRETOS: no escribo nada.'); print(json.dumps(mal, ensure_ascii=False, indent=1)); sys.exit(2)
for r, o in salidas.items():
    escribir(r, o)
print(json.dumps({'cuota_airtable_oct': cuota_at, 'firmada': firmada, 'si_firman': firmada + pend_cuota, 'caja': caja_total,
                  'facturado_oct': facturado_mes, 'impagos_vencidos': admin['impagos']['vencido_total'], 'firmas_sin_alta': [f['nombre'] for f in sin_alta],
                  'clientes_m18': len(filas_cli), 'rent_tarifa': len(rent_tarifa), 'coste_hora_real': coste_hora_real,
                  'altas_esperadas': R(esperadas, 1), 'huecos': huecos_total, 'sin_casar_airtable': sin_casar_at,
                  'fuentes': [(f['fuente'], f['estado']) for f in fuentes]}, ensure_ascii=False, indent=1))

# Paneles v4 (3-oct): la retención por mes de alta sale de direccion.json recién escrito (solo lectura, sin red).
import subprocess   # noqa: E402
subprocess.run([sys.executable, str(AQUI / 'generar_cohortes.py')], check=False)
