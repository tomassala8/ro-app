# -*- coding: utf-8 -*-
"""Finanzas v3 (3-oct-2026): beneficio mes a mes, coste del equipo mes a mes, cuadre de fuentes e impagos.

SOLO LECTURA. Se lanza DESPUÉS de fuentes_dinero/generar_dinero.py (usa lo que deja en data/finanzas/).
Lee:
  · Holded en vivo con ~/RO_HERRAMIENTAS/holded/hd.py, mes a mes (Holded corta en 500 por llamada): facturas de venta,
    rectificativas y facturas recibidas de ene-2025 a hoy. Copia en _privado/_cache/ (los números de documento no se sirven).
  · El cierre de Sofía (dashboard_cierre_31_08.xlsx, hoja Datos_Gastos) para el gasto «tal cual» por mes y partida.
  · data/finanzas/direccion.json (cuenta de resultados corregida de ene-ago 2026: la única cifra de beneficio de la app).
  · Airtable de facturación (la copia que acaba de dejar generar_dinero.py en _privado/_cache/airtable.json; solo GET).
  · data/sueldos/_privado/sueldos.json SOLO para sacar el TOTAL del equipo de cada mes (la hoja «Cuentas bancarias» no la
    abre nadie: este script ni siquiera abre el Excel). Ningún importe por persona sale de aquí.
  · local.db NO se lee: los intentos de cobro hechos desde la app los pide la pantalla a servir.py (acciones del módulo).
Escribe (puerta de secretos antes; si encuentra algo, no escribe nada):
  data/finanzas/cuadre.json              solo dirección: beneficio, equipo y cuadre completo
  data/finanzas/cuadre_facturacion.json  dirección y administración: solo lo facturado (Holded · cierre · Airtable)
  data/finanzas/impagos.json             dirección y administración: impagos con estado, account, intentos y evolución
  data/finanzas/impagos_clientes.json    cada cliente con impago (el account ve que lo hay; el importe solo quien ve la cuota)

Uso: python3 fuentes_dinero/generar_cuadre.py [--sin-red]
"""
import json, sys, calendar, datetime as dt
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
CACHE = AQUI / '_privado' / '_cache'
ENT = _cfg.PANEL_RESULTADOS
HOLDED = _cfg.HERRAMIENTAS / 'holded'
SIN_RED = '--sin-red' in sys.argv
AHORA = dt.datetime.now(); HOY = AHORA.date(); HORA = AHORA.strftime('%Y-%m-%d %H:%M'); MES = HOY.strftime('%Y-%m')
R = lambda v, d=2: round(v, d) if isinstance(v, (int, float)) else v
MESES_N = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
def eu(n, d=0, signo=False):
    """12345.6 → «12.346» (d=0) o «12.345,60» (d=2); con signo, «+»/«−»."""
    if n is None: return '—'
    t = f'{abs(n):,.{d}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return (('+' if n > 0 else '−' if n < 0 else '') if signo else ('−' if n < 0 else '')) + t
mes_txt = lambda m: f"{MESES_N[int(m[5:7]) - 1]} de {m[:4]}"
# BCE, media mensual de dólares por euro (la misma tabla que el informe financiero del panel, leída el 1-oct)
FX = {'2025-01': 1.0354, '2025-02': 1.0413, '2025-03': 1.0807, '2025-04': 1.1214, '2025-05': 1.1278, '2025-06': 1.1516, '2025-07': 1.1677,
      '2025-08': 1.1631, '2025-09': 1.1732, '2025-10': 1.1630, '2025-11': 1.1560, '2025-12': 1.1709, '2026-01': 1.1738, '2026-02': 1.1824,
      '2026-03': 1.1558, '2026-04': 1.1706, '2026-05': 1.1673, '2026-06': 1.1518, '2026-07': 1.1417, '2026-08': 1.1593, '2026-09': 1.1513, '2026-10': 1.1513}

fuentes = []
def fuente(nombre, estado, detalle='', hora=None):
    fuentes.append({'fuente': nombre, 'estado': estado, 'detalle': detalle, 'hora': hora or HORA})

def holded(path, **q):
    sys.path.insert(0, str(HOLDED))
    import hd
    try:
        return hd.get(path, **q)
    except SystemExit as e:
        raise RuntimeError(str(e))

def meses(desde, hasta):
    y, m = map(int, desde.split('-')); out = []
    while f'{y}-{m:02d}' <= hasta:
        out.append(f'{y}-{m:02d}'); m += 1
        if m > 12: y, m = y + 1, 1
    return out

def por_meses(tipo, desde, hasta, campos):
    todo = []
    for k in meses(desde, hasta):
        y, m = map(int, k.split('-'))
        a = int(dt.datetime(y, m, 1).timestamp()); b = int(dt.datetime(y, m, calendar.monthrange(y, m)[1], 23, 59, 59).timestamp())
        for x in holded(f'invoicing/v1/documents/{tipo}', starttmp=a, endtmp=b):
            fila = {c: x.get(c) for c in campos}
            if tipo == 'purchase':
                fila['cuenta'] = ((x.get('products') or [{}])[0] or {}).get('account')
            if tipo in ('invoice', 'creditnote'):
                fila['pagos'] = [[p.get('date'), p.get('amount')] for p in (x.get('paymentsDetail') or [])]
            todo.append(fila)
    return todo

def con_cache(nombre, lector, etiqueta):
    ruta = CACHE / f'{nombre}.json'
    if not SIN_RED:
        try:
            d = lector()
            CACHE.mkdir(parents=True, exist_ok=True)
            ruta.write_text(json.dumps({'hora': HORA, 'datos': d}, ensure_ascii=False))
            return d, 'ok', HORA
        except Exception as e:      # noqa: BLE001
            print(f'  {etiqueta}: en vivo falla ({str(e)[:90]}); uso la copia')
    c = leer(ruta)
    return (c['datos'], 'viejo', c['hora']) if c else (None, 'sin datos', None)

CV = ('id', 'docNumber', 'contactName', 'date', 'dueDate', 'subtotal', 'total', 'paymentsPending', 'paymentsTotal', 'paymentsRefunds', 'status', 'draft')
CC = ('id', 'docNumber', 'contactName', 'date', 'subtotal', 'currency', 'currencyChange', 'draft', 'status')
ULT_CERRADO_HOLDED = (HOY.replace(day=1) - dt.timedelta(days=1)).strftime('%Y-%m')
VENTAS, v_est, v_hora = con_cache('holded_ventas_hist', lambda: {'facturas': por_meses('invoice', '2025-01', MES, CV),
                                                                  'rectificativas': por_meses('creditnote', '2025-01', MES, CV)}, 'Holded ventas')
COMPRAS, c_est, c_hora = con_cache('holded_compras_hist', lambda: por_meses('purchase', '2025-01', ULT_CERRADO_HOLDED, CC), 'Holded compras')
fuente('Holded · facturas de venta y rectificativas, mes a mes', v_est, f"{len((VENTAS or {}).get('facturas', []))} facturas y {len((VENTAS or {}).get('rectificativas', []))} rectificativas desde enero de 2025", v_hora)
fuente('Holded · facturas recibidas, mes a mes', c_est, f'{len(COMPRAS or [])} facturas desde enero de 2025, convertidas a euros con su tipo de cambio', c_hora)
if not VENTAS or not COMPRAS:
    print('Sin Holded (ni copia): no escribo nada.'); sys.exit(2)

DIR = (leer(DATA / 'finanzas' / 'direccion.json') or {}).get('direccion', [{}])[0]
FIN = leer(DATA / 'finanzas' / 'finanzas.json') or {}
ADM = FIN.get('admin') or {}
if not DIR.get('pyg'):
    print('Falta data/finanzas/direccion.json: lanza antes generar_dinero.py.'); sys.exit(2)
fuente('Finanzas · cuenta de resultados corregida (ene-ago 2026)', 'ok', 'La misma cifra de beneficio en Finanzas, Mi día y Panel de dirección', FIN.get('generado'))

ts = lambda t: dt.datetime.fromtimestamp(t).date().isoformat() if t else None
fact = [x for x in VENTAS['facturas'] if not x.get('draft') and x.get('status') != 3]
rect = [x for x in VENTAS['rectificativas'] if not x.get('draft')]
for x in fact + rect: x['f'] = ts(x['date']); x['v'] = ts(x.get('dueDate')) or x['f']

# ------------------------------------------------------------------ 1 · gasto de Holded por mes y partida (convertido)
cg = leer(ENT / '_crudo/holded/cuentas_gasto.json') or {}
NUM = {x['id']: str(x['account_num']) for x in cg.get('items', [])}
ACC = {'60700001': 'Equipo', '64000000': 'Equipo', '64200000': 'Equipo', '64900000': 'Equipo', '64100000': 'Equipo',
       '60700002': 'Colaboradores', '60700000': 'Colaboradores', '62300000': 'Colaboradores',
       '62900007': 'Herramientas', '62900003': 'Herramientas', '62700001': 'Publicidad propia', '62700000': 'Publicidad propia'}
def a_eur(x):
    cur = (x.get('currency') or 'eur').lower()
    if cur == 'eur' or not x.get('currencyChange'): return x.get('subtotal') or 0
    return (x.get('subtotal') or 0) / x['currencyChange']
hd_gas = defaultdict(lambda: defaultdict(float)); hd_n = Counter(); paquete = defaultdict(int)
for x in COMPRAS:
    if x.get('draft'): continue
    f = ts(x['date']); m = f[:7]
    g = ACC.get(NUM.get(x.get('cuenta'), ''), 'Otros')
    hd_gas[m][g] += a_eur(x); hd_n[m] += 1
    if g in ('Equipo', 'Colaboradores') and (x.get('currency') or '').lower() == 'usd':
        paquete[f] += 1
DIA_PAQUETE, N_PAQUETE = max(paquete.items(), key=lambda kv: kv[1]) if paquete else (None, 0)

# ------------------------------------------------------------------ 2 · el cierre de Sofía «tal cual» (gasto por mes y partida)
import openpyxl
CIERRE_XLSX = ENT / '_crudo/finanzas/dashboard_cierre_31_08.xlsx'
cierre_gas = defaultdict(lambda: defaultdict(float))
CAT_EQ = {'Equipo interno': 'Equipo', 'Sueldos y salarios': 'Equipo', 'Colaboradores': 'Colaboradores'}
if CIERRE_XLSX.exists():
    wb = openpyxl.load_workbook(CIERRE_XLSX, data_only=True, read_only=True)
    for r in list(wb['Datos_Gastos'].iter_rows(values_only=True))[2:]:
        if len(r) < 7 or not isinstance(r[1], dt.datetime) or r[6] is None: continue
        cierre_gas[r[1].strftime('%Y-%m')][CAT_EQ.get(r[5], 'Resto')] += float(r[6])
    fuente('Cierre de Sofía a 31-ago (Excel, solo lectura)', 'ok', 'Gasto por mes y partida tal y como lo suma el Excel', dt.datetime.fromtimestamp(CIERRE_XLSX.stat().st_mtime).strftime('%Y-%m-%d %H:%M'))
else:
    fuente('Cierre de Sofía a 31-ago (Excel, solo lectura)', 'sin datos', 'No está el Excel del cierre')

# ------------------------------------------------------------------ 3 · el Excel de sueldos: SOLO el total del mes
SU = leer(DATA / 'sueldos' / '_privado' / 'sueldos.json') or {}
excel_eq = {}
n_personas = Counter()
for p in (SU.get('personas') or {}).values():
    for m, x in (p.get('meses') or {}).items():
        usd = x.get('salario_usd') if isinstance(x.get('salario_usd'), (int, float)) else 0
        eur = x.get('euros') if isinstance(x.get('euros'), (int, float)) else 0
        if usd or eur:
            excel_eq[m] = excel_eq.get(m, 0) + usd / FX.get(m, 1.15) + eur; n_personas[m] += 1
excel_eq = {m: R(v, 0) for m, v in excel_eq.items() if n_personas[m] >= 3}      # nunca un total de menos de 3 personas
fuente('Excel de sueldos (solo el total de cada mes)', 'ok' if excel_eq else 'sin datos',
       'Dólares pasados a euros con la media del BCE de cada mes; la hoja de cuentas bancarias no se abre', (SU.get('_meta') or {}).get('generado', '').replace('T', ' ') or None)

# ------------------------------------------------------------------ 4 · Airtable (facturación prevista por mes)
AT = (leer(CACHE / 'airtable.json') or {})
def eur_txt(s):
    if s in (None, ''): return 0.0
    s = str(s).replace('"', '').replace('€', '').replace('.', '').replace(',', '.').strip()
    try: return float(s)
    except ValueError: return 0.0
MES_AT = {f'{MESES_N[i].capitalize()} {y}': f'{y}-{i + 1:02d}' for y in (2025, 2026, 2027) for i in range(12)}
import re
def clave_fiscal(t):
    k = re.sub(r'[^a-z0-9]', '', norm(t or ''))
    for suf in ('sociedadlimitadaprofesional', 'sociedadlimitada', 'slp', 'slu', 'sl', 'sa'):
        if k.endswith(suf) and len(k) > len(suf) + 3: k = k[:-len(suf)]; break
    return k[:14]                                  # el principio del nombre fiscal: «(Jenasa)» o «S.L.» al final no separan
at_mes = defaultdict(float); at_cli = defaultdict(lambda: defaultdict(float)); at_n = Counter(); at_nombre = {}
for x in AT.get('datos') or []:
    m = MES_AT.get(x.get('Mes') or '')
    if not m or (m >= MES and (x.get('Estado cliente') or '') == 'Inactivo'): continue   # un mes pasado cuenta también a quien hoy es baja
    v = eur_txt(x.get('Importe especial')) or eur_txt(x.get('Importe'))
    at_mes[m] += v; at_n[m] += 1
    cli = (x.get('Cliente') or '').strip().strip('"')
    at_cli[m][cli] += v
fuente('Airtable de facturación (solo lectura)', 'ok' if at_mes else 'sin datos', f"{sum(at_n.values())} líneas activas de {', '.join(mes_txt(m).split(' de ')[0] for m in sorted(at_mes))}", AT.get('hora'))

# ------------------------------------------------------------------ 5 · ingresos de Holded por mes (facturas − rectificativas)
hd_ing = defaultdict(float); hd_rect = defaultdict(float); hd_cli = defaultdict(lambda: defaultdict(float))
nombres_hd = {clave_fiscal(x.get('contactName')): (x.get('contactName') or '').strip()[:40] for x in fact + rect}
for x in fact:
    hd_ing[x['f'][:7]] += x.get('subtotal') or 0; hd_cli[x['f'][:7]][clave_fiscal(x.get('contactName'))] += x.get('subtotal') or 0
for x in rect:
    hd_rect[x['f'][:7]] += x.get('subtotal') or 0; hd_cli[x['f'][:7]][clave_fiscal(x.get('contactName'))] -= x.get('subtotal') or 0
ING_PANEL = {x['m']: x for x in DIR.get('ingresos') or []}
PYG = {x['m']: x for x in DIR.get('pyg') or []}
GM = {x['m']: x for x in DIR.get('gastos_por_mes') or []}

# ------------------------------------------------------------------ 6 · coste del equipo mes a mes (todas las fuentes)
M25 = meses('2025-01', '2025-12'); M26 = meses('2026-01', ULT_CERRADO_HOLDED)
eq_hd = {m: R((hd_gas[m]['Equipo'] + hd_gas[m]['Colaboradores']), 0) for m in M25 + M26}
ing25 = {m: (ING_PANEL.get(m) or {}).get('total') or 0 for m in M25}
tot_eq25 = sum(eq_hd[m] for m in M25)
reparto25 = {m: R(tot_eq25 * ing25[m] / sum(ing25.values()), 0) for m in M25} if sum(ing25.values()) else {}
her25 = {m: hd_gas[m]['Herramientas'] for m in M25}
reparto_her25 = {m: R(sum(her25.values()) / 12, 0) for m in M25}
equipo_mes = []
for m in M25 + M26:
    gm = GM.get(m) or {}
    cierre_tal = R(cierre_gas[m]['Equipo'] + cierre_gas[m]['Colaboradores'], 0) if m in cierre_gas else None
    corregido = R((gm.get('Equipo') or 0) + (gm.get('Colaboradores') or 0), 0) if m in PYG else None
    if m in PYG:
        usado, de, estado = corregido, 'Cierre de Sofía convertido a euros', 'ok'
        nota = 'Lleva ≈ 9.000 € de facturas del equipo de diciembre fechadas el 1-ene' if m == '2026-01' else None
    elif m.startswith('2025'):
        usado, de = reparto25.get(m), 'Holded del año repartido según los ingresos del mes (propuesta)'
        if m == (DIA_PAQUETE or '')[:7]: estado, nota = 'paquete', f'El {int(DIA_PAQUETE[8:10])} de {MESES_N[int(m[5:7]) - 1]} se subieron de golpe {N_PAQUETE} facturas del equipo en dólares de meses anteriores'
        elif eq_hd[m] < 0.25 * (tot_eq25 / 12): estado, nota = 'falta', 'En Holded casi no hay facturas del equipo este mes: llegaron más tarde, con otra fecha'
        elif eq_hd[m] > 2 * (tot_eq25 / 12): estado, nota = 'paquete', 'Holded acumula facturas de otros meses'
        else: estado, nota = 'ok', None
    else:
        usado, de, estado, nota = eq_hd[m], 'Holded (sin cierre de Sofía)', 'provisional', 'Sin cerrar: las facturas del equipo llegan hasta el día 20 del mes siguiente'
    equipo_mes.append({'m': m, 'holded': eq_hd[m], 'cierre_tal_cual': cierre_tal, 'cierre_corregido': corregido, 'excel_equipo': excel_eq.get(m),
                       'usado': usado, 'de_donde': de, 'estado': estado, 'nota': nota})

# ------------------------------------------------------------------ 7 · beneficio mes a mes (ene-2025 → último cierre)
beneficio = []
for m in M25:
    ing = (ING_PANEL.get(m) or {}).get('total') or 0
    g = hd_gas[m]
    eq = reparto25.get(m, 0); her = reparto_her25.get(m, 0); pub = R(g['Publicidad propia'], 0); otros = R(g['Otros'], 0)
    gas = eq + her + pub + otros
    eq_tal = eq_hd[m]; gas_tal = R(eq_tal + g['Herramientas'] + pub + otros, 0)
    beneficio.append({'m': m, 'ing': R(ing, 0), 'equipo': eq, 'publicidad': pub, 'herramientas': her, 'otros': otros, 'gastos': R(gas, 0),
                      'bai': R(ing - gas, 0), 'sin_factura': None, 'real': None, 'margen_pct': R(100 * (ing - gas) / ing, 1) if ing else None,
                      'margen_real_pct': None, 'estimado': True, 'bai_holded_tal_cual': R(ing - gas_tal, 0),
                      'fuente': 'Holded: ingresos al euro; equipo y herramientas repartidos en el año (propuesta)'})
for m in sorted(PYG):
    p = PYG[m]; gm = GM.get(m) or {}
    eq = R((gm.get('Equipo') or 0) + (gm.get('Colaboradores') or 0), 2); her = R(gm.get('Herramientas') or 0, 2); pub = R(gm.get('Publicidad propia') or 0, 2)
    otros = R(p['gas'] - eq - her - pub, 2)
    beneficio.append({'m': m, 'ing': p['ing'], 'equipo': eq, 'publicidad': pub, 'herramientas': her, 'otros': otros, 'gastos': p['gas'],
                      'bai': p['bai'], 'sin_factura': p.get('sin_factura'), 'real': p.get('real'),
                      'margen_pct': R(100 * p['bai'] / p['ing'], 1) if p.get('ing') else None,
                      'margen_real_pct': R(100 * p['real'] / p['ing'], 1) if p.get('ing') and p.get('real') is not None else None,
                      'estimado': False, 'fuente': 'Cierre de Sofía con los gastos convertidos a euros (la cifra oficial)'})
an26 = DIR.get('anio') or {}
assert abs(sum(x['bai'] for x in beneficio if x['m'].startswith('2026')) - an26.get('bai', 0)) < 1, 'el beneficio del año no cuadra con Finanzas'
anios = {}
for y in ('2025', '2026'):
    L = [x for x in beneficio if x['m'].startswith(y)]
    if not L: continue
    ing = sum(x['ing'] for x in L); bai = sum(x['bai'] for x in L); real = sum((x['real'] if x['real'] is not None else x['bai']) for x in L)
    anios[y] = {'meses': len(L), 'desde': L[0]['m'], 'hasta': L[-1]['m'], 'ing': R(ing, 0), 'bai': R(bai, 0), 'real': R(real, 0) if y == '2026' else None,
                'margen_pct': R(100 * bai / ing, 1) if ing else None, 'estimado': y == '2025'}
anios['2026']['bai'] = an26.get('bai'); anios['2026']['real'] = an26.get('real')        # la cifra redonda de Finanzas, sin recalcular

# ------------------------------------------------------------------ 8 · cuadre mes a mes: ingresos y gastos según cada fuente
cuadre = []
for m in M25 + M26 + ([MES] if MES not in M26 else []):
    p = PYG.get(m) or {}
    ing_hd = R(hd_ing[m] - hd_rect[m], 2)
    fila = {'m': m, 'curso': m == MES,
            'facturado_holded': ing_hd, 'facturado_rectificativas': R(hd_rect[m], 2),
            'facturado_cierre': p.get('ing'), 'facturado_panel': (ING_PANEL.get(m) or {}).get('total'),
            'facturado_airtable': R(at_mes[m], 0) if m in at_mes else None,
            'gasto_holded': R(sum(hd_gas[m].values()), 0) if m <= ULT_CERRADO_HOLDED else None,
            'gasto_cierre_tal_cual': R(sum(cierre_gas[m].values()), 0) if m in cierre_gas else None,
            'gasto_corregido': p.get('gas'),
            'gasto_sin_factura': p.get('sin_factura')}
    fila['dif_facturado_holded_panel'] = R(ing_hd - fila['facturado_panel'], 2) if fila['facturado_panel'] is not None else None
    fila['dif_facturado_airtable_holded'] = R(fila['facturado_airtable'] - ing_hd, 0) if fila['facturado_airtable'] is not None else None
    fila['dif_gasto_cierre_corregido'] = R(fila['gasto_cierre_tal_cual'] - fila['gasto_corregido'], 0) if fila['gasto_cierre_tal_cual'] is not None and fila['gasto_corregido'] is not None else None
    fila['dif_gasto_corregido_holded'] = R(fila['gasto_corregido'] - fila['gasto_holded'], 0) if fila['gasto_corregido'] is not None and fila['gasto_holded'] is not None else None
    cuadre.append(fila)

# diferencias de Airtable con Holded, cliente a cliente (meses con Airtable)
at_dif = []
for m in sorted(at_mes):
    if m > MES: continue
    hk = dict(hd_cli[m]); ak = defaultdict(float)
    for cli, v in at_cli[m].items():               # Airtable escribe «Comercial (Fiscal)» o «Fiscal (Comercial)»: vale la que esté en Holded
        fuera, dentro = cli.split('(')[0], cli[cli.find('(') + 1:cli.rfind(')')] if '(' in cli else ''
        cands = [clave_fiscal(t) for t in (dentro, fuera) if t.strip()]
        k = next((c for c in cands if c in hk), cands[0] if cands else '')
        ak[k] += v; at_nombre.setdefault(k, fuera.strip() or dentro.strip())
    claves = set(ak) | set(hk)
    for k in claves:
        a, b = ak.get(k, 0), hk.get(k, 0)
        if abs(a - b) >= 50:
            at_dif.append({'m': m, 'nombre': at_nombre.get(k) or nombres_hd.get(k) or k[:40] or '(sin nombre)', 'airtable': R(a, 0), 'holded': R(b, 0), 'dif': R(b - a, 0)})
# mismo cliente con dos nombres (solo en Airtable y solo en Holded, mismo importe y mismas tres primeras letras): no es diferencia
_k3 = lambda t: clave_fiscal(t)[:3]
fuera_par = set()
for i, x in enumerate(at_dif):
    if i in fuera_par or x['holded'] != 0: continue
    j = next((j for j, y in enumerate(at_dif) if j not in fuera_par and j != i and y['m'] == x['m'] and y['airtable'] == 0
              and abs(y['holded'] - x['airtable']) < 1 and _k3(y['nombre']) == _k3(x['nombre'])), None)
    if j is not None: fuera_par |= {i, j}
at_dif = [x for i, x in enumerate(at_dif) if i not in fuera_par]
at_dif.sort(key=lambda x: (x['m'], -abs(x['dif'])))

# ------------------------------------------------------------------ 9 · incongruencias y lo que proponemos (decide Tomás)
def fila(m): return next((x for x in cuadre if x['m'] == m), {})
inc = []
# 9.1 ingresos Holded en vivo frente al panel
for x in cuadre:
    d = x.get('dif_facturado_holded_panel')
    if d is not None and abs(d) >= 1 and not x['curso']:
        inc.append({'id': f"ing-{x['m']}", 'ambito': 'facturacion', 'mes': x['m'], 'gravedad': 'baja' if abs(d) < 500 else 'media',
                    'que': f"Lo facturado en {mes_txt(x['m'])}: Holded hoy {eu(x['facturado_holded'], 2)} € y el panel {eu(x['facturado_panel'], 2)} € ({eu(d, 2, True)} €)",
                    'propuesta': 'Vale Holded: es donde se emiten las facturas y las rectificativas. Se actualiza el panel en la próxima recarga.',
                    'por_que': 'El panel se leyó el 1-oct; después se emitió o cambió alguna factura o rectificativa de ese mes.' if x['m'] >= '2026-09' else 'Diferencia de redondeo o de una factura editada en Holded después de leer el panel.',
                    'impacto': R(d, 2)})
# 9.2 Airtable frente a Holded
for x in cuadre:
    d = x.get('dif_facturado_airtable_holded')
    if d is not None and abs(d) >= 100 and not x['curso']:
        top = [y for y in at_dif if y['m'] == x['m']][:6]
        inc.append({'id': f"at-{x['m']}", 'ambito': 'facturacion', 'mes': x['m'], 'gravedad': 'media',
                    'que': f"{mes_txt(x['m']).capitalize()}: Airtable prevé {eu(x['facturado_airtable'], 0)} € y Holded factura {eu(x['facturado_holded'], 0)} € ({eu(-d, 0, True)} €)",
                    'propuesta': 'Vale Holded para lo facturado. Airtable es la previsión: Sofía actualiza las líneas de los clientes que cambian (extras, prorrateos, subidas).',
                    'por_que': 'Airtable no recoge los cambios del mes: ' + ', '.join(f"{y['nombre']} {eu(y['dif'], 0, True)} €" for y in top) if top else 'Airtable no recoge los cambios del mes.',
                    'impacto': R(-d, 0), 'detalle': top})
# 9.3 gasto del cierre sin convertir los dólares
g_tal = sum(x['gasto_cierre_tal_cual'] or 0 for x in cuadre if x['m'].startswith('2026') and x['gasto_corregido'] is not None)
g_cor = sum(x['gasto_corregido'] or 0 for x in cuadre if x['m'].startswith('2026') and x['gasto_corregido'] is not None)
inc.append({'id': 'gas-dolar', 'ambito': 'gastos', 'mes': '2026-01/2026-08', 'gravedad': 'alta',
            'que': f'Gasto de enero a agosto: el Excel de Sofía suma {eu(g_tal, 0)} € y, con los dólares pasados a euros, son {eu(g_cor, 0)} €',
            'propuesta': 'Vale la cifra convertida (es la que usan Finanzas, Mi día y el Panel). El cierre de septiembre, con la columna de divisa y el tipo de Holded.',
            'por_que': 'El Excel suma las facturas en dólares del equipo y de las herramientas como si fueran euros (auditoría del cierre del 2-oct).',
            'impacto': R(g_tal - g_cor, 0)})
# 9.4 gasto corregido frente a Holded convertido, mes a mes (una sola incongruencia con el detalle por mes)
dg = [x for x in cuadre if x.get('dif_gasto_corregido_holded') is not None]
if dg:
    lo, hi = min(x['dif_gasto_corregido_holded'] for x in dg), max(x['dif_gasto_corregido_holded'] for x in dg)
    inc.append({'id': 'gas-holded', 'ambito': 'gastos', 'mes': f"{dg[0]['m']}/{dg[-1]['m']}", 'gravedad': 'baja',
                'que': f"Cada mes de 2026, el gasto del cierre corregido pasa al de Holded entre {eu(lo)} y {eu(hi)} € ({eu(sum(x['dif_gasto_corregido_holded'] for x in dg))} € de enero a agosto)",
                'propuesta': 'Vale el cierre corregido: lleva la nómina de España y los pagos por banco que no tienen factura en Holded.',
                'por_que': 'La nómina en España («Sueldos y salarios», unos 5.800 € al mes) y algunos cargos de banco no son facturas de compra en Holded; enero, además, lleva facturas de diciembre.',
                'impacto': R(sum(x['dif_gasto_corregido_holded'] for x in dg), 0),
                'detalle': [{'m': x['m'], 'cierre_corregido': x['gasto_corregido'], 'holded': x['gasto_holded'], 'dif': x['dif_gasto_corregido_holded']} for x in dg]})
# 9.5 equipo 2025 mal fechado
falta = [e['m'] for e in equipo_mes if e['estado'] == 'falta']
inc.append({'id': 'eq-2025', 'ambito': 'equipo', 'mes': '2025', 'gravedad': 'alta',
            'que': f"Coste del equipo de 2025 en Holded: {', '.join(mes_txt(m).split(' de ')[0] for m in falta)} casi vacíos y {N_PAQUETE} facturas en dólares subidas de golpe el {int(DIA_PAQUETE[8:10])} de {MESES_N[int(DIA_PAQUETE[5:7]) - 1]}" if DIA_PAQUETE else 'Coste del equipo de 2025 mal fechado en Holded',
            'propuesta': f"Repartir el equipo de 2025 ({eu(tot_eq25, 0)} € en el año) según los ingresos de cada mes, y las herramientas a partes iguales. El año no cambia; cambia en qué mes cae cada euro. El beneficio de 2025 va marcado como estimado.",
            'por_que': 'Las facturas del equipo se subieron a Holded con la fecha del día de subida, no la del mes trabajado. Sin repartir, agosto de 2025 sale con un beneficio enorme y octubre con una pérdida que no fue.',
            'impacto': None,
            'alternativa': 'Pedir a Sofía la fecha real de cada factura del paquete y volver a fecharlas en Holded (exacto, pero lleva horas).'})
# 9.5 bis · 2025 sin la nómina de España
an25 = anios.get('2025') or {}
inc.append({'id': 'eq-nomina-2025', 'ambito': 'equipo', 'mes': '2025', 'gravedad': 'alta',
            'que': f"El beneficio de 2025 sale en {eu(an25.get('bai', 0), 0)} € ({eu(an25.get('margen_pct', 0), 1)} % de los ingresos), demasiado alto: a Holded le falta la nómina de España, que no es una factura de compra",
            'propuesta': 'Pedir a la gestoría las cuentas definitivas de 2025 (como las de 2024) y usarlas para el año; hasta entonces, 2025 va en gris y marcado como estimado.',
            'por_que': 'En 2026 la nómina de España («Sueldos y salarios») suma unos 46.000 € de enero a agosto y entra por el banco, no por Holded. En 2025 no está en ninguna fuente que lea la app.',
            'impacto': None})
# 9.6 enero de 2026 con facturas de diciembre
inc.append({'id': 'eq-ene26', 'ambito': 'equipo', 'mes': '2026-01', 'gravedad': 'media',
            'que': 'Enero de 2026 lleva unos 9.000 € de facturas del equipo de diciembre fechadas el 1-ene (15 facturas): por eso enero sale en pérdidas (−1.730 €).',
            'propuesta': 'Dejarlo así en las cifras oficiales (el beneficio de enero a agosto sigue en 93.492 €) y avisarlo junto al mes. Si se pasan a diciembre, enero quedaría en ≈ +7.270 € y el año en ≈ 102.500 €.',
            'por_que': 'Cambiarlo movería la cifra que ya ven Finanzas, Mi día y el Panel; mejor decidirlo una vez y aplicarlo en todas a la vez.',
            'impacto': 9000})
# 9.7 Excel de sueldos frente a lo cargado
dif_ex = [(e['m'], e['excel_equipo'], e['cierre_corregido']) for e in equipo_mes if e['excel_equipo'] and e['cierre_corregido']]
if dif_ex:
    s_ex = sum(a for _, a, _ in dif_ex); s_co = sum(b for _, _, b in dif_ex)
    inc.append({'id': 'eq-excel', 'ambito': 'equipo', 'mes': '2026-01/2026-08', 'gravedad': 'baja',
                'que': f'Equipo de enero a agosto: el Excel de sueldos da {eu(s_ex, 0)} € y lo cargado (equipo, colaboradores y nómina de España, en euros) {eu(s_co, 0)} €',
                'propuesta': 'Vale lo cargado (facturas de Holded convertidas + nómina): es lo que se paga de verdad. El Excel sirve de control: si un mes se separa más de un 15 %, se mira.',
                'por_que': 'El Excel no lleva la nómina de España, los colaboradores que facturan aparte ni los bonus; y va en dólares.',
                'impacto': R(s_co - s_ex, 0)})
# 9.8 facturas antiguas sin cobrar que no salían en impagos
imp_filas = (ADM.get('impagos') or {}).get('filas') or []
antiguas = [f for f in imp_filas if (f.get('fecha') or '') < '2026-04-01' and f.get('tramo') != 'Sin vencer']
if antiguas:
    inc.append({'id': 'imp-antiguas', 'ambito': 'facturacion', 'mes': 'antes de abril', 'gravedad': 'media',
                'que': f"{len(antiguas)} facturas de antes de abril siguen sin cobrar ({eu(sum(f['importe'] for f in antiguas), 2)} €) y no salían en la lista de impagos",
                'propuesta': 'Ya salen en Impagos. Para cada una: reclamarla una última vez o darla por perdida (más de 90 días).',
                'por_que': 'La lista de impagos solo leía facturas desde abril.',
                'impacto': R(sum(f['importe'] for f in antiguas), 2), 'detalle': [{'nombre': f['nombre'], 'doc': f['doc'], 'importe': f['importe'], 'dias': f['dias']} for f in antiguas]})
# 9.9 gasto sin factura
inc.append({'id': 'sin-factura', 'ambito': 'gastos', 'mes': '2026-01/2026-08', 'gravedad': 'media',
            'que': f"Gasto sin factura de enero a agosto: {eu(an26.get('sin_factura', 0), 0)} € (en agosto {eu((PYG.get('2026-08') or {}).get('sin_factura', 0), 0)} €)",
            'propuesta': 'Enseñar siempre las dos cifras (con y sin gasto sin factura). Sofía lo cierra con la conciliación de Holded antes del día 10.',
            'por_que': 'Unos 1.500-2.000 € del año sí tienen factura y se cuentan dos veces: es un techo, no una cifra exacta.',
            'impacto': an26.get('sin_factura')})
# 9.10 dos facturas de mayo
inc.append({'id': 'may-divisa', 'ambito': 'gastos', 'mes': '2026-05', 'gravedad': 'baja',
            'que': 'Dos facturas de mayo (OpenAI y ClickUp) están en dólares en Holded, pero el cargo del banco dice euros.',
            'propuesta': 'Contarlas en euros, como ahora. Sofía lo confirma con el PDF; si fueran dólares, el gasto de mayo baja 142 €.',
            'por_que': 'Los cargos de Wise de abril encajan con los importes leídos en euros.', 'impacto': 142})
# comprobado y sin incongruencia: las rectificativas sí se restan
rect_26 = R(sum(hd_rect[m] for m in M26 if m <= '2026-08'), 0)

ORDEN = {'alta': 0, 'media': 1, 'baja': 2}
inc.sort(key=lambda x: (ORDEN.get(x['gravedad'], 3), x['ambito'], x['mes']))
for i in inc: i['decide'] = 'Tomás'

cuadre_doc = {'formato': 1, 'modulo': 'finanzas', 'generado': HORA, 'fuentes': fuentes,
              'beneficio': {'meses': beneficio, 'anios': anios, 'ultimo_cerrado': max(PYG),
                            'nota': 'Enero a agosto de 2026: cierre de Sofía con los gastos convertidos a euros (la cifra oficial). 2025: ingresos de Holded al euro; equipo y herramientas repartidos en el año porque Holded los tiene mal fechados (propuesta pendiente de Tomás). Septiembre, sin cerrar hasta el día 10.'},
              'equipo_mes': equipo_mes,
              'equipo_resumen': {'total_2025_holded': R(tot_eq25, 0), 'paquete_dia': DIA_PAQUETE, 'paquete_n': N_PAQUETE, 'meses_falta': falta,
                                 'regla': 'Solo totales del mes (equipo + colaboradores + nómina de España). Ningún importe por persona.'},
              'cuadre': cuadre, 'airtable_diferencias': at_dif[:60], 'incongruencias': inc,
              'comprobado': [f'Las rectificativas sí se restan de lo facturado (enero a agosto: {eu(rect_26, 0)} €): Holded, panel y cierre coinciden.',
                             'Los ingresos de enero a agosto de 2026 cuadran al euro entre Holded, el panel y el cierre de Sofía.',
                             'El beneficio que sale aquí es el mismo que Finanzas, Mi día y el Panel de dirección (93.492 € de enero a agosto; 76.392 € con el gasto sin factura).']}

FACT_KEYS = ('m', 'curso', 'facturado_holded', 'facturado_rectificativas', 'facturado_cierre', 'facturado_panel', 'facturado_airtable',
             'dif_facturado_holded_panel', 'dif_facturado_airtable_holded')
facturacion_doc = {'formato': 1, 'modulo': 'finanzas', 'generado': HORA,
                   'fuentes': [dict(f, detalle='Lo facturado de enero a agosto, tal y como lo suma el Excel') if f['fuente'].startswith('Cierre de Sofía') else f
                               for f in fuentes if not f['fuente'].startswith(('Excel de sueldos', 'Finanzas · cuenta', 'Holded · facturas recibidas'))],
                   'cuadre': [{k: x[k] for k in FACT_KEYS} for x in cuadre], 'airtable_diferencias': at_dif[:60],
                   'incongruencias': [i for i in inc if i['ambito'] == 'facturacion'],
                   'comprobado': cuadre_doc['comprobado'][:2]}

# ------------------------------------------------------------------ 10 · impagos (las MISMAS facturas que admin.impagos → alertas y Mi día)
V = leer(DATA / 'verdad' / 'clientes.json') or {}
ACCOUNT = {c['cliente_id']: c.get('account') for c in V.get('clientes') or []}
EST = (leer(AQUI / 'impagos_estado.json') or {}).get('facturas') or {}
por_doc = {x['docNumber']: x for x in fact if x.get('docNumber')}
def intentos(doc):
    x = por_doc.get(doc) or {}
    devol = x.get('paymentsRefunds') or 0
    n = round(devol / x['total']) if devol and x.get('total') else 0
    return max(n, 1 if devol else 0), R(devol, 2)
filas = []
for f in imp_filas:
    if f.get('tramo') == 'Sin vencer': continue
    e = EST.get(f['doc']) or {}
    n_dev, devol = intentos(f['doc'])
    estado = e.get('estado') or ('recibo devuelto' if f.get('devuelto') else 'decide Tomás' if f['dias'] > 60 else 'aviso al account' if f['dias'] > 30 else 'pendiente')
    siguiente = e.get('siguiente') or ('Decidir: cortar el servicio, plan de pago o darla por perdida' if f['dias'] > 90 else
                                      'Decidir: plan de pago o monitorio (a 60 días decide Tomás)' if f['dias'] > 60 else
                                      'Avisar al account y reclamar por Desk con la plantilla' if f['dias'] > 30 else
                                      'Recordatorio por Desk; si es SEPA, volver a pasar el recibo')
    filas.append({**{k: f.get(k) for k in ('doc', 'nombre', 'fecha', 'vence', 'dias', 'importe', 'tramo', 'devuelto', 'holded', 'cliente_id') if f.get(k) is not None},
                  'account_id': ACCOUNT.get(f.get('cliente_id')), 'estado': estado, 'siguiente': siguiente,
                  'devoluciones': n_dev, 'devuelto_importe': devol or None,
                  'ultima_accion': e.get('ultima_accion'), 'ultima_fecha': e.get('fecha'), 'nota': e.get('nota'), 'ex_cliente': bool(e.get('ex_cliente'))})
for f in ADM.get('devueltos') or []:
    if not any(x['doc'] == f['doc'] for x in filas):
        filas.append({**f, 'tramo': 'Devuelto', 'estado': 'recibo devuelto', 'siguiente': 'Volver a pasar el recibo o pedir transferencia', 'account_id': ACCOUNT.get(f.get('cliente_id'))})
filas.sort(key=lambda x: -x['dias'])
clientes_imp = {x.get('cliente_id') or norm(x['nombre']) for x in filas}
tramos = [{'tramo': t, 'n': sum(1 for x in filas if x['tramo'] == t), 'importe': R(sum(x['importe'] for x in filas if x['tramo'] == t), 0)}
          for t in ('0-30 días', '31-60 días', '61-90 días', 'Más de 90 días')]
# evolución: lo vencido y sin cobrar al final de cada mes (con las fechas de cobro de Holded)
evol = []
for m in meses('2025-03', MES):
    y, mm = map(int, m.split('-'))
    corte = HOY if m == MES else dt.date(y, mm, calendar.monthrange(y, mm)[1])
    tot, n = 0.0, 0
    for x in fact:
        if not x['v'] or x['v'] >= corte.isoformat(): continue
        pagado = sum(a or 0 for t, a in (x.get('pagos') or []) if t and ts(t) <= corte.isoformat())
        if not x.get('pagos') and (x.get('paymentsPending') or 0) <= 0.01: pagado = x.get('total') or 0     # cobrada por otra vía: fecha desconocida
        pend = (x.get('total') or 0) - pagado
        if (x.get('paymentsPending') or 0) <= 0.01 and pend > 0.01 and x['v'] < (corte - dt.timedelta(days=120)).isoformat():
            pend = 0                                                                                  # saldada con una rectificativa
        if pend > 0.01: tot += pend; n += 1
    if m == MES:            # hoy: la misma cifra que la lista (el cargo SEPA de los primeros días aún no cuenta como vencido)
        tot, n = sum(x['importe'] for x in filas), len(filas)
    evol.append({'m': m, 'vencido': R(tot, 0), 'facturas': n, 'curso': m == MES})
impagos_doc = {'formato': 1, 'modulo': 'finanzas', 'generado': HORA, 'fuentes': [f for f in fuentes if f['fuente'].startswith('Holded · facturas de venta')] + [x for x in FIN.get('fuentes') or [] if x['fuente'].startswith('Holded (tesor')],
               'resumen': {'vencido': R(sum(x['importe'] for x in filas), 0), 'facturas': len(filas), 'clientes': len(clientes_imp),
                           'antiguedad_media': R(sum(x['dias'] for x in filas) / len(filas), 0) if filas else 0,
                           'antiguedad_media_ponderada': R(sum(x['dias'] * x['importe'] for x in filas) / max(1, sum(x['importe'] for x in filas)), 0),
                           'mas_60': sum(1 for x in filas if x['dias'] > 60)},
               'tramos': tramos, 'filas': filas, 'evolucion': evol,
               'regla': 'Aviso al account a 30 días, decisión de Tomás a 60, nunca más de 2 cuotas. Las mismas facturas que las alertas de administración y que «Lo mío» de Sofía.',
               'estados': ['pendiente', 'aviso al account', 'reclamado', 'plan de pago', 'monitorio', 'decide Tomás', 'recibo devuelto', 'baja']}
# lo que ve el account: que su cliente tiene un impago (el importe va en cuota_* y el servidor lo quita a quien no ve la cuota)
pc = defaultdict(lambda: {'vencidas': 0, 'dias_max': 0, 'cuota_vencida': 0.0})
for x in filas:
    if not x.get('cliente_id'): continue
    c = pc[x['cliente_id']]; c['vencidas'] += 1; c['dias_max'] = max(c['dias_max'], x['dias']); c['cuota_vencida'] += x['importe']
impagos_cli_doc = {'formato': 1, 'modulo': 'finanzas', 'generado': HORA,
                   'clientes': [{'cliente_id': k, 'vencidas': v['vencidas'], 'dias_max': v['dias_max'], 'cuota_vencida': R(v['cuota_vencida'], 2),
                                 'texto': 'Lo lleva administración: no le hables de dinero al cliente.'} for k, v in sorted(pc.items())]}

salidas = {DATA / 'finanzas' / 'cuadre.json': cuadre_doc, DATA / 'finanzas' / 'cuadre_facturacion.json': facturacion_doc,
           DATA / 'finanzas' / 'impagos.json': impagos_doc, DATA / 'finanzas' / 'impagos_clientes.json': impagos_cli_doc}
mal = {str(r): escanear(o)[:5] for r, o in salidas.items() if escanear(o)}
if mal:
    print('PUERTA DE SECRETOS: no escribo nada.'); print(json.dumps(mal, ensure_ascii=False, indent=1)); sys.exit(2)
for r, o in salidas.items():
    escribir(r, o)
print(json.dumps({'beneficio_2026': anios.get('2026'), 'beneficio_2025_estimado': anios.get('2025'), 'incongruencias': len(inc),
                  'equipo_falta': falta, 'paquete': [DIA_PAQUETE, N_PAQUETE], 'impagos': impagos_doc['resumen'],
                  'fuentes': [(f['fuente'], f['estado']) for f in fuentes]}, ensure_ascii=False, indent=1))
