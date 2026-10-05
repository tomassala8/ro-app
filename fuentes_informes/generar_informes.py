#!/usr/bin/env python3
"""M13 · Informes mensuales · genera data/informes/informes.json (solo lectura de ClickUp y Desk).

Reglas (D-09 firmada el 2-oct; punto 2 de Mili; M2 de 09_MILI_MECANISMOS_CONTROL/01):
  · HECHO    = tarea del informe del mes («Informe mensual», «Reporte mensual», «Entrega de resultados», «Cierre de mes»…)
               CERRADA en ClickUp (cu.py, llave propia; nunca el conector de Claude).
  · ENVIADO  = correo SALIENTE en Zoho Desk (zh.py, los 30 departamentos) a un contacto del cliente con «informe»,
               «resultados» o «reporte» en el asunto y el mes o «mensual» en el asunto (o adjunto PDF). Del día 1 al 10
               del mes siguiente (o los últimos días del propio mes, si sale antes). Los «enviado» verificados a mano el
               2-oct (build/informes_mensuales.json del panel) se respetan.
  · PENDIENTE = lo demás. EXENTOS: mantenimiento y «sin contacto mensual» (cartera / panel). Altas del propio mes: no aplica.
  · Plazo: verde si sale el día 5 incluido; desde el día 6, rojo con aviso a Mili.
Si el asunto no dice el mes ni «mensual», el correo sale como «posible» (para mirarlo a mano), nunca como «enviado»
(prueba de aceptación: cero falsos «enviado»).

Plan A (por defecto): ClickUp + Desk en vivo. Plan B (--ficheros o si falla): build/informes_mensuales.json del panel.
Histórico (W5): data/informes/historico.json si existe (lo deja importar_hoja_w5.py). Escáner de secretos al final.
"""
import importlib.util
import json
import re
import sys
import urllib.parse
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
sys.path.insert(0, str(APP / 'fuentes'))
from comun import ahora_madrid, escanear, escribir, leer, norm, sanear, slug, tokens  # noqa: E402

DATA = APP / 'data'
SALIDA = DATA / 'informes' / 'informes.json'
HISTORICO = DATA / 'informes' / 'historico.json'
CACHE = AQUI / '_cache' / 'vivo.json'
sys.path.insert(1, str(Path(__file__).resolve().parents[1]))  # C5: rutas y secretos en config.py
import config  # noqa: E402
PANEL = config.PANEL_OPERACIONES
BASE = PANEL / 'build/informes_mensuales.json'
CARPETAS = PANEL / '_crudo/clickup/carpetas_clientes.json'
HERR = config.HERRAMIENTAS
HOY = date.today()
AHORA = datetime.now()

MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
ABREV_MES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']


def ultimos_meses(n, hasta=None):
    """L-20: los `n` meses que acaban en el de hoy (Madrid), del más viejo al más nuevo: ['2026-08', '2026-09', '2026-10']."""
    h = hasta or ahora_madrid()
    a, m = h.year, h.month
    salida = []
    for _ in range(n):
        salida.append(f'{a}-{m:02d}')
        m -= 1
        if m == 0:
            a, m = a - 1, 12
    return salida[::-1]


# L-20: las claves de los cuatro últimos meses salen de hoy; las que ya producen los ficheros no cambian (jul…oct de 2026).
CLAVE_MES = {m: ABREV_MES[int(m[5:]) - 1] for m in ultimos_meses(4)}
RE_TAREA = re.compile(r'informe mensual|reporte mensual|entrega de resultados|cierre de mes|informe (de )?(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)|reporte (de )?(acciones )?(de )?(julio|agosto|septiembre|octubre)', re.I)
RE_ASUNTO = re.compile(r'informe|resultados|reporte|report', re.I)
RE_MES_ASUNTO = re.compile(r'mensual|' + '|'.join(MESES), re.I)
CERRADA = {'completado', 'complete', 'completada', 'cerrado', 'closed', 'done', 'finalizado', 'enviado', 'entregado'}


def mes_anterior(d):
    return (d.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')


def mes_de_texto(texto, anio=None):
    anio = anio or ahora_madrid().year
    t = norm(texto)
    for i, m in enumerate(MESES):
        if re.search(rf'\b{m}\b', t):
            return f'{anio}-{i + 1:02d}'
    return None


def mes_por_fecha(d):
    """Un informe que sale del 1 al 20 es del mes anterior; del 21 al 31, del propio mes (sale antes de cerrar)."""
    return mes_anterior(d) if d.day <= 20 else d.strftime('%Y-%m')


def cargar(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def etiqueta_dominio(d):
    """gacgrup.es y gacgrup.com → «gacgrup» (el cliente cambia de terminación entre web y correo)."""
    partes = [p for p in (d or '').lower().split('.') if p]
    if len(partes) >= 3 and partes[-2] in ('com', 'co', 'org', 'net'):
        partes = partes[:-2]
    elif len(partes) >= 2:
        partes = partes[:-1]
    return partes[-1] if partes else ''


# ------------------------------------------------------------------ clientes
def clientes():
    idx = (leer(DATA / 'indice_clientes.json', {}) or {}).get('clientes', [])
    base = {c['id']: c for c in (leer(DATA / 'clientes.json', []) or [])}
    pers = {p['id']: p for p in (leer(DATA / 'personas.json', []) or [])}
    verdad = {c['cliente_id']: c for c in (leer(DATA / 'verdad/clientes.json', {}) or {}).get('clientes', [])}
    privados = ((leer(DATA / 'ficha/_privado/contactos.json', {}) or {}).get('clientes') or {})
    out = {}
    for f in idx:
        cid = f['id']
        ficha = leer(DATA / 'clientes' / f'{cid}.json', {}) or {}
        fu = ficha.get('fuentes', {})
        cart = (fu.get('cartera') or {}).get('datos') or {}
        b = base.get(cid, {})
        etiquetas = set()
        web = re.sub(r'^(https?://)?(www\.)?', '', str(ficha.get('web') or '').lower()).split('/')[0]
        if web:
            etiquetas.add(etiqueta_dominio(web))
        for p in ((privados.get(cid) or {}).get('datos') or {}).get('personas', []):
            for c in p.get('correos') or []:
                dom = str(c.get('correo') if isinstance(c, dict) else c).split('@')[-1].lower()
                if dom not in ('gmail.com', 'hotmail.com', 'outlook.com', 'yahoo.es', 'yahoo.com', 'icloud.com', 'live.com', 'hotmail.es', 'rankingonline.com'):
                    etiquetas.add(etiqueta_dominio(dom))
        acc_id = verdad[cid]['account'] if cid in verdad else b.get('responsable_id')   # verdad única
        out[cid] = {
            'id': cid, 'nombre': f['nombre'], 'en_panel': f.get('en_panel'), 'activo': f.get('activo_libro'),
            'account_id': acc_id, 'account': (pers.get(acc_id) or {}).get('alias') if acc_id else 'sin account',
            'alta': b.get('alta'), 'nuevo': bool(cart.get('nuevo') or b.get('nuevo')),
            'exento': bool(cart.get('exento')), 'motivo_exento': cart.get('motivo_exento'),
            'informes': ((fu.get('informes') or {}).get('datos') or {}), 'panel': (ficha.get('ids') or {}).get('panel'),
            'etiquetas': {e for e in etiquetas if len(e) >= 3}, 'tokens': {w for w in tokens(f['nombre']) if len(w) >= 4},
        }
    return out


# ------------------------------------------------------------------ ClickUp en vivo
def clickup_en_vivo(cli):
    cu = cargar('cu', HERR / 'clickup_api/cu.py')
    carp = {c['carpeta_id']: slug(c['cartera_nombre']) for c in (leer(CARPETAS, {}) or {}).get('carpetas', []) if c.get('cartera_nombre')}
    por_panel = {slug(c['panel'] or c['nombre']): cid for cid, c in cli.items()}
    desde = cu.ms(date(2026, 8, 1))
    tareas = cu.tareas_equipo({'include_closed': 'true', 'date_updated_gt': desde})
    out = defaultdict(list)
    vistas = 0
    for t in tareas:
        nombre = t.get('name') or ''
        if not RE_TAREA.search(nombre):
            continue
        vistas += 1
        cid = por_panel.get(carp.get((t.get('folder') or {}).get('id')))
        if not cid:  # por el nombre del cliente en la tarea
            tt = tokens(nombre)
            cands = [k for k, c in cli.items() if c['tokens'] and (c['tokens'] <= tt or any(len(w) >= 6 for w in c['tokens'] & tt))]
            cid = cands[0] if len(cands) == 1 else None
        if not cid:
            continue
        mes = mes_de_texto(nombre + ' ' + ((t.get('list') or {}).get('name') or ''))
        if not mes:
            ref = t.get('due_date') or t.get('date_created')
            mes = mes_por_fecha(cu.fecha_local(ref)) if ref else None
        if not mes:
            continue
        st = (t.get('status') or {})
        cerrada = st.get('type') == 'closed' or norm(st.get('status')) in CERRADA
        out[(cid, mes)].append({'nombre': sanear(nombre)[:90], 'estado': st.get('status'), 'cerrada': cerrada,
                                'cerrada_el': str(cu.fecha_local(t['date_closed'])) if t.get('date_closed') else None,
                                'url': t.get('url'), 'asignada': ', '.join((a.get('username') or '') for a in t.get('assignees') or [])[:60]})
    return out, {'tareas_leidas': len(tareas), 'tareas_de_informe': vistas, 'llamadas': cu.LLAMADAS}


# ------------------------------------------------------------------ Desk en vivo
def desk_en_vivo(cli):
    zh = cargar('zh', HERR / 'zoho/zh.py')
    tk, _ = zh.acceso()
    oid = str(zh.get(tk, 'https://desk.zoho.eu/api/v1/organizations')['data'][0]['id'])
    D = 'https://desk.zoho.eu/api/v1'
    rango = f'2026-08-20T00:00:00.000Z,{HOY.isoformat()}T23:59:59.000Z'
    tickets, llamadas = {}, 1
    for termino in ('informe', 'resultados', 'reporte', 'report'):
        for campo in ('createdTimeRange', 'modifiedTimeRange'):
            desde = 0
            while True:
                q = {'subject': f'*{termino}*', 'limit': 100, 'from': desde, campo: rango}
                try:
                    r = zh.get(tk, f'{D}/tickets/search?' + urllib.parse.urlencode(q), orgId=oid)
                except json.JSONDecodeError:  # 204 sin resultados
                    r = {}
                llamadas += 1
                for t in r.get('data', []) or []:
                    tickets[t['id']] = t
                if len(r.get('data', []) or []) < 100:
                    break
                desde += 100
    envios, posibles = defaultdict(list), defaultdict(list)
    for tid, t in tickets.items():
        asunto = t.get('subject') or ''
        if not RE_ASUNTO.search(asunto):
            continue
        th = zh.get(tk, f'{D}/tickets/{tid}/threads?limit=50', orgId=oid)
        llamadas += 1
        for x in th.get('data', []) or []:
            if x.get('direction') != 'out' or (x.get('channel') or '').upper() != 'EMAIL':
                continue
            dom = [etiqueta_dominio(c.split('@')[-1].strip('> "')) for c in re.findall(r'[\w.+-]+@[\w.-]+', str(x.get('to') or '') + ',' + str(x.get('cc') or ''))]
            dom = {d for d in dom if d and d not in ('rankingonline', 'gmail', 'hotmail', 'outlook')}
            nombres_to = tokens(re.sub(r'<[^>]*>', ' ', str(x.get('to') or '')))
            cids = [cid for cid, c in cli.items() if c['etiquetas'] & dom]
            if not cids:
                cids = [cid for cid, c in cli.items() if c['tokens'] and (c['tokens'] <= (nombres_to | tokens(asunto)))]
            if len(cids) != 1:
                continue
            cid = cids[0]
            f = datetime.strptime(x['createdTime'][:19], '%Y-%m-%dT%H:%M:%S').date()
            pdf = False
            if x.get('hasAttach'):
                det = zh.get(tk, f'{D}/tickets/{tid}/threads/{x["id"]}', orgId=oid)
                llamadas += 1
                pdf = any(str(a.get('name', '')).lower().endswith('.pdf') for a in det.get('attachments', []) or [])
            mes = mes_de_texto(asunto) or mes_por_fecha(f)
            fila = {'fecha': f.isoformat(), 'ticket': t.get('ticketNumber'), 'url': t.get('webUrl'), 'asunto': sanear(asunto)[:90], 'pdf': pdf}
            if RE_MES_ASUNTO.search(asunto) or pdf:
                envios[(cid, mes)].append(fila)
            else:
                posibles[(cid, mes)].append(fila)
    return envios, posibles, {'tickets_candidatos': len(tickets), 'llamadas': llamadas}


# ------------------------------------------------------------------ principal
def main():
    cli = clientes()
    base = leer(BASE, {}) or {}
    plan, error, info = 'A · ClickUp y Desk en vivo', [], {}
    tareas, envios, posibles = {}, {}, {}
    if '--ficheros' not in sys.argv:
        try:
            tareas, info['clickup'] = clickup_en_vivo(cli)
        except (SystemExit, Exception) as e:  # noqa: BLE001
            error.append(f'ClickUp: {type(e).__name__} {str(e)[:100]}')
        try:
            envios, posibles, info['desk'] = desk_en_vivo(cli)
        except (SystemExit, Exception) as e:  # noqa: BLE001
            error.append(f'Desk: {type(e).__name__} {str(e)[:100]}')
        if error and not tareas and not envios:
            plan = 'B · build/informes_mensuales.json del panel (2-oct 06:30)'
        else:
            escribir(CACHE, {'_meta': {'leido': AHORA.strftime('%Y-%m-%d %H:%M'), 'info': info},
                             'tareas': {f'{k[0]}|{k[1]}': v for k, v in tareas.items()},
                             'envios': {f'{k[0]}|{k[1]}': v for k, v in envios.items()},
                             'posibles': {f'{k[0]}|{k[1]}': v for k, v in posibles.items()}})
    else:
        c = leer(CACHE)
        if c:
            plan = f'B · última lectura en vivo ({c["_meta"]["leido"]})'
            sp = lambda d: {tuple(k.split('|')): v for k, v in d.items()}
            tareas, envios, posibles, info = sp(c['tareas']), sp(c['envios']), sp(c['posibles']), c['_meta']['info']
        else:
            plan = 'B · build/informes_mensuales.json del panel (2-oct 06:30)'

    ciclo = mes_anterior(HOY)                       # el informe que toca enviar este mes
    meses = [m for m in ultimos_meses(3) if m <= ciclo]
    filas = []
    for cid, c in cli.items():
        if c['activo'] == 'Baja' or (not c['en_panel'] and c['activo'] != 'Activo'):
            continue
        for mes in meses:
            fin_mes = (datetime.strptime(mes + '-01', '%Y-%m-%d').date() + timedelta(days=32)).replace(day=1)
            limite = fin_mes.replace(day=5)
            manual = c['informes'].get(CLAVE_MES[mes]) or {}
            ts = tareas.get((cid, mes), [])
            # «enviado» solo con el mes o «mensual» en el asunto (y sin «semanal»): un PDF suelto no basta
            # (2-oct: «Reunión mañana + informe de migración» llevaba PDF y no era el informe). Lo demás, «posible».
            todos = envios.get((cid, mes), []) + posibles.get((cid, mes), [])
            es = sorted([x for x in todos if RE_MES_ASUNTO.search(x['asunto'] or '') and not re.search(r'semanal|newsletter', x['asunto'] or '', re.I)], key=lambda x: x['fecha'])
            ps = [x for x in todos if x not in es]
            enviado = None
            if es:
                enviado = {'fecha': es[0]['fecha'], 'ticket': es[0]['ticket'], 'url': es[0]['url'], 'asunto': es[0]['asunto'],
                           'pdf': es[0]['pdf'], 'metodo': 'Desk en vivo'}
            if manual.get('estado') == 'enviado' and (not enviado or (manual.get('fecha_envio') or '9') < enviado['fecha']):
                enviado = {'fecha': manual.get('fecha_envio'), 'ticket': (re.search(r'RO-\d+', manual.get('prueba') or '') or [None])[0],
                           'url': manual.get('url'), 'asunto': sanear(manual.get('prueba'))[:120], 'pdf': None,
                           'metodo': 'verificado a mano el 2-oct (panel)'}
            tarea = None
            if ts:
                tarea = sorted(ts, key=lambda x: (not x['cerrada'], x['nombre']))[0]
            elif manual.get('url') and 'clickup' in (manual.get('url') or ''):
                tarea = {'nombre': sanear(manual.get('prueba'))[:90], 'estado': manual.get('estado'), 'cerrada': False, 'url': manual['url'], 'cerrada_el': None}
            hecho = bool(tarea and tarea['cerrada'])
            alta = c['alta']
            no_aplica = bool(alta and alta[:7] >= mes) or (not c['en_panel'])
            if c['exento']:
                estado = 'exento'
            elif enviado:
                estado = 'enviado'
            elif no_aplica:
                estado = 'no_aplica'
            elif hecho:
                estado = 'hecho'
            elif tarea:
                estado = 'en_curso'
            else:
                estado = 'sin_tarea'
            # plazo D-09: verde el día 5 incluido; rojo desde el 6 con aviso a Mili
            if estado in ('exento', 'no_aplica'):
                plazo, retraso = 'gris', None
            elif enviado and enviado.get('fecha'):
                fe = date.fromisoformat(enviado['fecha'])
                retraso = max(0, (fe - limite).days)
                plazo = 'verde' if fe <= limite else 'ambar'
            else:
                retraso = max(0, (HOY - limite).days)
                plazo = 'rojo' if HOY > limite else 'en_plazo'
            filas.append({
                'id': f'{cid}·{mes}', 'cliente_id': cid, 'cliente': c['nombre'], 'account_id': c['account_id'], 'account': c['account'],
                'mes': mes, 'limite': limite.isoformat(), 'estado': estado, 'hecho': hecho, 'tarea': tarea, 'enviado': enviado,
                'posibles': ps[:3], 'plazo': plazo, 'dias_retraso': retraso, 'aviso_mili': plazo == 'rojo',
                'exento_motivo': c['motivo_exento'] if c['exento'] else None,
                'no_aplica_motivo': (f'alta en {alta[:7]}' if alta and alta[:7] >= mes else 'fuera de la cartera mensual') if estado == 'no_aplica' else None,
                'nuevo': c['nuevo'], 'nota_manual': sanear(manual.get('prueba'))[:160] if manual.get('prueba') else None,
            })

    hist = leer(HISTORICO)
    cuadre = None
    if hist and hist.get('estado') == 'importado':
        # cuadre con lo que ve la app (ClickUp + Desk) en los meses que tienen las dos
        hoja = {(f['cliente_id'], f['mes']): f for f in hist.get('filas', []) if f.get('cliente_id')}
        dif = []
        for f in filas:
            h_ = hoja.get((f['cliente_id'], f['mes']))
            if not h_:
                continue
            f['hoja'] = {k: h_.get(k) for k in ('enviado', 'informado_en_reunion', 'enlace_informe', 'enlace_estadisticas')}
            app_env = f['estado'] == 'enviado'
            if h_.get('enviado') and not app_env and f['estado'] not in ('exento', 'no_aplica'):
                f['diferencia'] = 'La hoja lo marca enviado; en Desk no hay correo con el informe'
            elif app_env and h_.get('enviado') is False:
                f['diferencia'] = 'Desk tiene el correo; la hoja no lo marca'
            if f.get('diferencia'):
                dif.append({'cliente_id': f['cliente_id'], 'cliente': f['cliente'], 'mes': f['mes'], 'diferencia': f['diferencia']})
        cuadre = {'meses': sorted({m for (_, m) in hoja} & set(meses)), 'comparados': sum(1 for f in filas if f.get('hoja')),
                  'coinciden': sum(1 for f in filas if f.get('hoja') and not f.get('diferencia')), 'diferencias': dif}
    salida = {
        '_meta': {
            'generado': AHORA.strftime('%Y-%m-%d %H:%M'), 'plan': plan, 'error': '; '.join(error) or None, 'lectura': info,
            'ciclo': {'mes': ciclo, 'limite': (HOY.replace(day=5)).isoformat(), 'hoy': HOY.isoformat(),
                      'dias_para_limite': (HOY.replace(day=5) - HOY).days},
            'meses': meses,
            'reglas': {
                'hecho': 'Tarea del informe del mes cerrada en ClickUp (Informe mensual, Reporte mensual, Entrega de resultados, Cierre de mes).',
                'enviado': 'Correo saliente en Desk a un contacto del cliente con «informe», «resultados» o «reporte» y el mes o «mensual» en el asunto. Con PDF pero sin el mes, sale como «posible» para mirarlo.',
                'plazo': 'Verde si sale el día 5 incluido; desde el día 6, rojo con aviso a Mili (decisión firmada el 2-oct).',
                'exentos': 'Clientes de mantenimiento y sin contacto mensual. Altas del propio mes: no aplica.',
            },
            'limites': 'El «enviado» por WhatsApp o desde un correo personal no se ve: la norma es enviarlo siempre desde Desk. '
                       'Un informe mandado dentro de un hilo con otro asunto puede no aparecer: queda como «posible» para mirarlo. '
                       'Para esos casos está el botón «Enviado por otra vía», con motivo y sello.',
            'base_panel': (base.get('_meta') or {}).get('generado'),
        },
        'filas': filas,
        'cuadre': cuadre,
        'historico': hist or {
            'estado': 'espera_w5',
            'texto': 'El histórico de la hoja de Zoho Sheet «Informes mensuales» llega con W5 (llave de lectura limitada a esa hoja). '
                     'El importador ya está preparado (fuentes_informes/importar_hoja_w5.py). Nunca se lee la pestaña «Credenciales».',
            'columnas': ['cliente', 'mes', 'enlace_informe', 'enlace_estadisticas', 'informado_en_reunion', 'enviado'],
            'filas': [],
        },
    }
    hall = escanear(salida)
    if hall:
        print('Puerta de secretos: NO se escribe.', *hall[:10], sep='\n  ')
        sys.exit(2)
    escribir(SALIDA, salida)
    from collections import Counter
    for mes in meses:
        cnt = Counter(f['estado'] for f in filas if f['mes'] == mes)
        print(mes, dict(cnt), '· a tiempo', sum(1 for f in filas if f['mes'] == mes and f['plazo'] == 'verde'))
    print('plan', plan, '·', info, '·', error or 'sin errores')


if __name__ == '__main__':
    main()
