#!/usr/bin/env python3
"""M8 · SEO, ficha de Google y webs · genera data/seo/seo.json y data/seo/webs.json (solo lectura, 2-oct-2026).

Fuentes:
  · SE Ranking: posiciones de los proyectos por la API de PROYECTOS (sr_leer.py, paso «seranking» de la tubería, cada día a
    las 6:00; no gasta créditos). Deja _cache/seranking.json con hoy, hace 7 días y hace ~30 días de cada palabra y
    «dia_dato» (la última comprobación completa), que se enseña en pantalla: «Posiciones del sábado 3-oct».
    (Hasta el 3-oct se leía en api4.seranking.com, que SE Ranking apagó: de ahí el «se ha roto».)
  · Search Console (gg.py, cuenta gmb1@): clics e impresiones semana contra semana, 28 días contra 28, serie diaria, páginas y búsquedas.
  · Google Analytics 4: lo que ya trae la capa de E1 (data/clientes/<id>.json → fuentes.ga4).
  · Monitor de webs: UNA comprobación real desde este Mac (la IP de RO): estado HTTP, redirección, tiempo, certificado y
    palabras de spam en la portada. La comprobación «desde fuera» llega con W1 (Worker de Cloudflare) + un monitor externo.
  · Fallos de medición de 17_ANALYTICS_A_CERO_REVISION.md → avisos para web.

Uso:
  python3 generar_seo.py --en-vivo gsc,monitor   # llama a Search Console (≈6 llamadas por web) y comprueba cada web una vez
  python3 generar_seo.py                         # 0 llamadas: rehace los JSON desde _cache/
"""
import concurrent.futures as cf, datetime as dt, glob, json, os, re, socket, ssl, sys, time, urllib.parse, urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(AQUI)
C = lambda n: os.path.join(AQUI, '_cache', n)
from zoneinfo import ZoneInfo  # noqa: E402
HOY = dt.datetime.now(ZoneInfo('Europe/Madrid')).date()   # 3-oct: antes fijo en el 2-oct (los certificados contaban mal los días)
LENTA_MS = 5000                                # V2: una sola regla de «web lenta» (webs.json → _meta.lenta)
# Search Console va con 2-3 días de retraso: la «semana» es la última completa con dato.
S1 = (HOY - dt.timedelta(days=9), HOY - dt.timedelta(days=3))     # 23-sep → 29-sep
S0 = (S1[0] - dt.timedelta(days=7), S1[1] - dt.timedelta(days=7))  # 16-sep → 22-sep
M1 = (HOY - dt.timedelta(days=30), HOY - dt.timedelta(days=3))    # 28 días
M0 = (M1[0] - dt.timedelta(days=28), M1[1] - dt.timedelta(days=28))
SPAM = re.compile(r'\b(casino|casinos|apuestas|tragaperras|bet365|viagra|cialis|póker online|poker online|casino online)\b', re.I)
CTR = {1: .30, 2: .15, 3: .10, 4: .07, 5: .05, 6: .04, 7: .03, 8: .025, 9: .02, 10: .02}


def guardar(ruta, obj):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    open(ruta + '.tmp', 'w').write(json.dumps(obj, ensure_ascii=False))
    os.replace(ruta + '.tmp', ruta)


def clientes():
    out = []
    for f in sorted(glob.glob(os.path.join(APP, 'data', 'clientes', '*.json'))):
        c = json.load(open(f))
        if c.get('activo_libro') in ('Baja',):
            continue
        out.append(c)
    return out


# ------------------------------------------------------------------ Search Console
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'fuentes'))
if APP not in sys.path: sys.path.insert(0, APP)
from fuentes_seo.posiciones import preparar_motores, comparar, posicion, reparto_observado, top, suma_medida, fecha as fecha_posiciones
from fuentes_seo.motores_contexto import contexto_desde_cache  # noqa: E402
from comun import consulta_basura  # noqa: E402  · barrido v1 (N14): filas de exportación de Google Ads no son búsquedas


def leer_gsc(cls):
    sys.path.insert(1, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); import config  # C5: rutas en config.py
    sys.path.insert(0, str(config.HERRAMIENTAS / 'google'))
    import gg
    tk = gg.acceso()

    def q(site, body):
        u = f'https://www.googleapis.com/webmasters/v3/sites/{urllib.parse.quote(site, safe="")}/searchAnalytics/query'
        req = urllib.request.Request(u, data=json.dumps(body).encode(), method='POST', headers={'Authorization': 'Bearer ' + tk, 'Content-Type': 'application/json'})
        try:
            return json.load(urllib.request.urlopen(req, timeout=60))
        except urllib.error.HTTPError as e:
            return {'_error': e.code}

    def tot(site, a, b):
        x = (q(site, {'startDate': str(a), 'endDate': str(b)}).get('rows') or [{}])[0]
        return {'clics': x.get('clicks', 0), 'impresiones': x.get('impressions', 0), 'ctr': x.get('ctr', 0), 'posicion': x.get('position')}

    def dim(site, d, a, b, n):
        return {r['keys'][0]: [r['clicks'], r['impressions'], round(r['position'], 1)]
                for r in q(site, {'startDate': str(a), 'endDate': str(b), 'dimensions': [d], 'rowLimit': n}).get('rows', [])}

    # Search Console va 2-3 días por detrás: las ventanas se cierran en el ÚLTIMO DÍA CON DATO de cada sitio
    # (7 días cerrados y 28 cerrados, frente a los mismos días justo antes). Así no se compara un periodo con días vacíos.
    out = {'leido': dt.datetime.now().strftime('%Y-%m-%d %H:%M'), 'regla': 'ventanas cerradas en el último día con dato de cada sitio', 'clientes': {}}
    for c in cls:
        g = c['fuentes'].get('gsc') or {}
        site = (g.get('emparejado') or {}).get('id')
        if not site:
            continue
        try:
            dias = [r['keys'][0] for r in q(site, {'startDate': str(HOY - dt.timedelta(days=10)), 'endDate': str(HOY - dt.timedelta(days=1)), 'dimensions': ['date']}).get('rows', [])]
            L = dt.date.fromisoformat(max(dias)) if dias else HOY - dt.timedelta(days=3)
            s1, s0 = (L - dt.timedelta(days=6), L), (L - dt.timedelta(days=13), L - dt.timedelta(days=7))
            m1, m0 = (L - dt.timedelta(days=27), L), (L - dt.timedelta(days=55), L - dt.timedelta(days=28))
            serie = [[r['keys'][0], r['clicks'], r['impressions']] for r in q(site, {'startDate': str(m1[0]), 'endDate': str(m1[1]), 'dimensions': ['date']}).get('rows', [])]
            pag1, pag0 = dim(site, 'page', *m1, 12), dim(site, 'page', *m0, 250)
            bus1, bus0 = dim(site, 'query', *m1, 12), dim(site, 'query', *m0, 250)
            out['clientes'][c['id']] = {'site': site, 'hasta': str(L), 'ventanas': {'semana': [str(x) for x in s1], 'semana_ant': [str(x) for x in s0], 'mes': [str(x) for x in m1], 'mes_ant': [str(x) for x in m0]},
                                        'semana': tot(site, *s1), 'semana_ant': tot(site, *s0), 'mes': tot(site, *m1), 'mes_ant': tot(site, *m0),
                                        'serie': serie,
                                        'paginas': [[k, v[0], v[1], v[2], (pag0.get(k) or [None])[0]] for k, v in pag1.items()],
                                        'busquedas': [[k, v[0], v[1], v[2], (bus0.get(k) or [None, None, None])[2]] for k, v in bus1.items()]}
            print(f"GSC {c['id'][:26]:26} hasta {L} {out['clientes'][c['id']]['semana']['clics']:>6} clics semana", flush=True)
        except Exception as e:
            out['clientes'][c['id']] = {'site': site, '_error': str(e)[:120]}
    guardar(C('gsc.json'), out)
    return out


# ------------------------------------------------------------------ monitor de webs
def comprobar(url):
    """Una comprobación: GET de la portada desde este Mac (IP de RO). Devuelve estado, tiempo, redirección, certificado y spam."""
    r = {'url': url, 'hora': dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh) RO-monitor-prototipo/0.1 (comprobacion unica)'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            cuerpo = resp.read(600_000).decode('utf-8', 'ignore')
            r.update(estado=resp.status, final=resp.geturl())
    except urllib.error.HTTPError as e:
        cuerpo = ''
        r.update(estado=e.code, final=url)
    except Exception as e:
        cuerpo = ''
        r.update(estado=None, error=type(e).__name__ + ': ' + str(e)[:120])
    r['ms'] = round((time.time() - t0) * 1000)
    spam = sorted({m.lower() for m in SPAM.findall(cuerpo)})
    r['spam'] = spam
    host = urllib.parse.urlparse(r.get('final') or url).hostname or urllib.parse.urlparse(url).hostname
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=8) as s, ctx.wrap_socket(s, server_hostname=host) as ss:
            no_after = ss.getpeercert()['notAfter']
            fin = dt.datetime.strptime(no_after, '%b %d %H:%M:%S %Y %Z')
            r['cert_caduca'] = fin.strftime('%Y-%m-%d')
            r['cert_dias'] = (fin.date() - HOY).days
    except Exception as e:
        r['cert_error'] = type(e).__name__ + ': ' + str(e)[:100]
    return r


def leer_monitor(cls):
    webs = [(c['id'], c['web']) for c in cls if c.get('web')]
    webs.append(('_ro', 'https://rankingonline.com/'))
    with cf.ThreadPoolExecutor(8) as ex:
        res = dict(zip([w[0] for w in webs], ex.map(lambda w: comprobar(w[1]), webs)))
    out = {'leido': dt.datetime.now().strftime('%Y-%m-%d %H:%M'), 'desde': 'Mac de RO (misma IP que las herramientas)', 'webs': res}
    guardar(C('monitor.json'), out)
    for k, v in res.items():
        print(f"WEB {k[:24]:24} {v.get('estado')} {v['ms']:>6} ms cert {v.get('cert_dias')} spam {v['spam']}", flush=True)
    return out


# ------------------------------------------------------------------ cálculo
def error_llano(e):
    """Traduce el error técnico a una frase llana."""
    e = str(e or '')
    if 'nodename' in e or 'Name or service' in e: return 'el dominio no existe (no resuelve en DNS)'
    if 'SSL' in e or 'TLS' in e or 'EOF occurred' in e: return 'falla la conexión segura (https)'
    if 'timed out' in e or 'Timeout' in e: return 'no contesta en 15 s'
    if 'refused' in e: return 'el servidor rechaza la conexión'
    return 'sin respuesta'


def fes(n, dec=1):
    """Número en formato de España: 5.214 · −51,9."""
    if n is None: return '—'
    t = f"{abs(n):,.{dec}f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    if dec and t.endswith(',' + '0' * dec): t = t[:-(dec + 1)]
    return ('−' if n < 0 else '') + t


def dominio(u):
    return re.sub(r'^(sc-domain:|https?://)?(www\.)?', '', str(u or '')).split('/')[0].lower()


def principal(v, silla):
    """Persona principal de una silla según la verdad única (data/verdad/clientes.json)."""
    eq = ((v or {}).get('equipo') or {}).get(silla) or []
    return (next((x for x in eq if x.get('principal')), eq[0]) if eq else {}).get('persona_id')


def pct(a, b):
    return None if a is None or not b else round(100 * (a - b) / b, 1)


def vis(palabras, campo):
    return sum((p['vol'] or 0) * (CTR.get(p[campo], .01 if p[campo] and p[campo] <= 20 else 0) if p[campo] else 0) for p in palabras)


AVISOS_MEDICION = {   # 17_ANALYTICS_A_CERO_REVISION.md (2-oct)
    'fusterguell': ('Doble Analytics', 'Tag Manager manda a dos propiedades de GA4 a la vez y a una etiqueta del Analytics antiguo.', 'Quitar una de las dos propiedades y la etiqueta antigua.'),
    'musashi-consultores': ('Medición bloqueada por el banner de cookies', 'OneTrust deniega todo por defecto: 0 sesiones en 30 días en la propiedad correcta. Hay un contenedor de Tag Manager vacío.', 'Revisar OneTrust y el modo de consentimiento; quitar el contenedor vacío.'),
    'ecija-advisory': ('Analytics en una cuenta ajena', 'La web manda a G-JRXQYQ0VL9, una propiedad de ECIJA a la que RO no tiene acceso.', 'Pedir a ECIJA lectura para gmb1@ (Agus).'),
    'busbac': ('La web no responde por https', 'Error de conexión segura; por http redirige. La propiedad marca 0 sesiones.', 'Comprobar que busbac.com está en marcha y su certificado.'),
}


UMBRAL_VERDE = {'verde': 80, 'ambar': 60, 'texto': 'Bien desde el 80 % · mal bajo el 60 %', 'fuente': 'Ficha G3 · SEO (umbral firmado)'}


def estado_pct(v):
    return None if v is None else 'verde' if v >= UMBRAL_VERDE['verde'] else 'ambar' if v >= UMBRAL_VERDE['ambar'] else 'rojo'


def aviso_sr(filas):
    """R12 · aviso único de «fallo de SE Ranking» (el mismo en SEO y en Mi día): muchas palabras dejan de verse de golpe
    mientras los clics de Google suben. Devuelve None si no aplica."""
    des = sum((f['visibilidad'] or {}).get('desaparecen', 0) for f in filas)
    con = [f for f in filas if f['clics']]
    suben = sum(1 for f in con if (f['clics']['var_mes'] or 0) > 0)
    if des <= 50:
        return None
    return {'desaparecen': des, 'clics_suben': suben, 'con_clics': len(con),
            'texto': f"SE Ranking dejó de ver {des} palabras de golpe esta semana y los clics de Google suben en {suben} de {len(con)} clientes. La diferencia no identifica la causa: contrasta fecha, motor, ubicación y dispositivo antes de tocar nada. Las palabras que hoy no ve no cuentan como caída."}


DIAS_SEM = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
MES3 = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
DIA_SR = HOY


def info_sr(sr):
    """3-oct · la fecha del dato de SE Ranking, dicha en llano («Posiciones del sábado 3-oct»), su coste y si se leyó bien
    la última vez (_cache/seranking_estado.json). Así nadie piensa que está roto cuando solo es el dato del día."""
    try:
        est = json.load(open(C('seranking_estado.json')))
    except Exception:
        est = {}
    d = dt.date.fromisoformat(sr.get('dia_dato') or (sr.get('generado') or str(HOY))[:10])
    dias = (HOY - d).days
    texto = f"Posiciones del {DIAS_SEM[d.weekday()]} {d.day}-{MES3[d.month - 1]}"
    viejo = dias >= 2
    return {'origen': sr.get('origen'), 'leido': sr.get('generado'), 'dia_dato': str(d), 'dias': dias, 'texto_dia': texto,
            'viejo': viejo, 'ultima_lectura_ok': est.get('ok', None), 'error': None if est.get('ok', True) else est.get('error'),
            # «creditos» y no «coste»: el servidor quita las claves coste* (dinero) a quien no las ve
            'creditos': sr.get('coste') or {'texto': 'Leer posiciones no gasta créditos (API de proyectos).', 'fuente': 'https://seranking.com/api/api-credits-system/'},
            'aviso': (f"{texto}: SE Ranking no se ha podido leer después ({est.get('error')})." if est.get('ok') is False else
                      f"{texto}: hace {dias} días que no se lee SE Ranking (se lee cada día a las 6:00)." if viejo else None)}


def construir(cls, sr, gsc, mon):
    # Sólo caché local. Ausencia/error no borra posiciones ni inventa contexto; se carga una vez.
    try:
        with open(C('seranking_motores.json')) as fm:
            contexto_sr = json.load(fm)
    except (OSError, ValueError):
        contexto_sr = {}
    global DIA_SR
    fecha_sr=fecha_posiciones(sr.get('dia_dato') or str(sr.get('generado') or '')[:10])
    DIA_SR=fecha_sr if fecha_sr and fecha_sr<=HOY else HOY  # límite, no acredita lectura del día
    personas = {p['id']: p['nombre'] for p in json.load(open(os.path.join(APP, 'data', 'personas.json')))}
    try:
        verdad = {x['cliente_id']: x for x in json.load(open(os.path.join(APP, 'data', 'verdad', 'clientes.json')))['clientes']}
    except Exception:
        verdad = {}
    # R12 (C-A3): el dueño de cada web = la persona principal de la silla «web» en asignaciones (una sola por cliente).
    # Se lee el equipo que deja el paso «base» (data/clientes.json, sin bajas), que corre antes que este.
    try:
        for x in json.load(open(os.path.join(APP, 'data', 'clientes.json'))):
            if x.get('equipo') is not None:
                verdad[x['id']] = {**verdad.get(x['id'], {}), 'equipo': x['equipo']}
    except Exception:
        pass
    puestos_de = {p['id']: set(p.get('puestos') or []) for p in json.load(open(os.path.join(APP, 'data', 'personas.json')))}
    filas, webs = [], []
    for c in cls:
        a = ((c['fuentes'].get('asignaciones') or {}).get('datos') or {})
        serv = a.get('servicios') or {}
        v = verdad.get(c['id'])
        # responsables: la verdad única (equipo vigente); si el cliente no está en ella, las asignaciones de E1
        sil = {k: principal(v, k) for k in ('seo', 'web', 'redes', 'account')} if v else (a.get('sillas') or {})
        s = sr['clientes'].get(c['id'])
        motores_sr = contexto_desde_cache(c['id'], s.get('proyecto'), s.get('motores'), contexto_sr) if s else []
        g = (gsc or {}).get('clientes', {}).get(c['id'])
        ga = c['fuentes'].get('ga4') or {}
        gsc_nota = (c['fuentes'].get('gsc') or {}).get('nota')
        if g and g.get('site') != ((c['fuentes'].get('gsc') or {}).get('emparejado') or {}).get('id'):
            g = None   # E1 cambió el emparejamiento después de la última lectura: no usar la caché vieja
        # el sitio de Search Console tiene que ser la web del cliente (Consulting F apuntaba a una landing)
        if g and c.get('web') and dominio(g.get('site')) != dominio(c['web']) and not dominio(c['web']).endswith(dominio(g.get('site'))):
            gsc_nota = f"El sitio emparejado ({dominio(g['site'])}) no es la web del cliente ({dominio(c['web'])}): falta el acceso a la buena"
            g = None
        con_seo = serv.get('seo') in ('sí', 'posible') or bool(s)
        # ---------------- SEO por cliente
        if con_seo:
            palabras, informe, alertas = [], [], []
            if s:
                s={**s,'motores':preparar_motores(s.get('motores'),str(DIA_SR))}
                prin=next((m for m in s['motores'] if m.get('principal')),s['motores'][0] if s['motores'] else {'palabras':[]})
                palabras=prin['palabras']
                todas = [p for m in s['motores'] for p in m['palabras']]
                # las 15 del informe: provisional, las 15 de más búsquedas del buscador principal (ver _ESTADO_seo.md)
                # primero las que el despacho trabaja de verdad (alguna vez en el top 30 este mes), luego por búsquedas
                mejor_pos = lambda p: min([x for x in (p['hoy'],p['sem'],p['mes']) if x is not None],default=float('inf'))
                informe = sorted(palabras, key=lambda p: (mejor_pos(p) > 30, -(p['vol'] or 0), p['k']))[:15]
                # alertas solo de las 15 del informe (la «lista clave», monitor-posiciones-alertas l.157)
                for p in informe:
                    if comparar(p) is not None and p['sem']<=10 and p['hoy']>10:
                        alertas.append({'tipo': 'fuera_top10', 'gravedad': 'rojo', 'palabra': p['k'], 'antes': p['sem'], 'hoy': p['hoy'],
                                        'texto': f"«{p['k']}» sale del top 10 (hace 7 días {p['sem']}, hoy {p['hoy']})"})
                    elif p['sem'] and p['sem'] <= 10 and not p['hoy']:
                        # de top 10 a «no aparece» en dos comprobaciones: o desindexación o fallo de la comprobación → se mira, no se da por caída
                        alertas.append({'tipo': 'desaparece', 'gravedad': 'ambar', 'palabra': p['k'], 'antes': p['sem'], 'hoy': None,
                                        'texto': f"«{p['k']}» sin posición observada en esta copia (lectura anterior {p['sem']}): contrastar fecha, motor y Google antes de actuar"})
                    elif comparar(p) is not None and p['sem']<=10 and (p['hoy']-p['sem']>=3 or (p['sem']<=3<p['hoy'])):
                        alertas.append({'tipo': 'cae', 'gravedad': 'ambar', 'palabra': p['k'], 'antes': p['sem'], 'hoy': p['hoy'],
                                        'texto': f"«{p['k']}» baja de {p['sem']} a {p['hoy']} en 7 días"})
                # palabras que suben y bajan (todas las seguidas, 7 días)
                mov = []
                for p in todas:
                    cambio=comparar(p)
                    a,b=p['sem'],p['hoy']
                    if cambio is None or cambio==0:
                        continue
                    mov.append({'k': p['k'], 'vol': p['vol'], 'antes': p['sem'], 'hoy': p['hoy'], 'delta':cambio,'motor_id':p['motor_id'],'fechas':dict(p['fechas'])})
                movimientos = {'suben': sorted([m for m in mov if m['delta'] > 0], key=lambda m: -m['delta'])[:6],
                               'bajan': sorted([m for m in mov if m['delta'] < 0], key=lambda m: m['delta'])[:6],
                               'n_suben': sum(1 for m in mov if m['delta'] > 0), 'n_bajan': sum(1 for m in mov if m['delta'] < 0)}
                comparables=[p for p in todas if comparar(p) is not None]
                v1, v0 = vis(comparables, 'hoy'), vis(comparables, 'sem')
                visib={'hoy':round(v1,1) if comparables else None,'sem':round(v0,1) if comparables else None,'var':pct(v1,v0) if comparables else None,'comparables':len(comparables),'cobertura':'parcial; sólo pares del mismo motor con fechas exactas7d'}
                desaparecen=sum(1 for p in todas if p['sem'] is not None and p['hoy'] is None)
                visib['desaparecen'] = desaparecen
                if visib['var'] is not None and visib['var'] <= -15 and desaparecen <= max(3, len([p for p in comparables if p['sem']]) // 4):
                    alertas.append({'tipo': 'visibilidad', 'gravedad': 'rojo', 'texto': f"Visibilidad {fes(visib['var'])} % en 7 días (el límite es −15 %)"})
                elif visib['var'] is not None and visib['var'] <= -15:
                    alertas.append({'tipo': 'visibilidad', 'gravedad': 'ambar', 'texto': f"Visibilidad {fes(visib['var'])} % en 7 días, pero {desaparecen} palabras dejan de aparecer de golpe: comprobar en Google antes de actuar"})
                reparto=reparto_observado(informe)
                todas_top10 = top('hoy', 10, todas)
                if informe and reparto['top10']['hoy'] == 0 and not any(x['gravedad'] == 'rojo' for x in alertas):
                    alertas.append({'tipo': 'sin_top10', 'gravedad': 'ambar', 'texto':'Ninguna consulta con posición observada de esta muestra está en el top 10; las ausentes no se clasifican'})
            else:
                visib, reparto, todas_top10, movimientos = None, None, None, None
            clics = None
            if g and 'semana' in g and not (g['mes']['clics'] == 0 and g['mes_ant']['clics'] == 0):
                clics = {'semana': g['semana']['clics'], 'semana_ant': g['semana_ant']['clics'], 'var_sem': pct(g['semana']['clics'], g['semana_ant']['clics']),
                         'mes': g['mes']['clics'], 'mes_ant': g['mes_ant']['clics'], 'var_mes': pct(g['mes']['clics'], g['mes_ant']['clics']),
                         'impresiones': g['mes']['impresiones'], 'impresiones_ant': g['mes_ant']['impresiones'],
                         'var_impr': pct(g['mes']['impresiones'], g['mes_ant']['impresiones']),
                         'posicion': round(g['mes']['posicion'], 1) if g['mes']['posicion'] else None,
                         'ctr': round(100 * g['mes']['ctr'], 2) if g['mes']['ctr'] else 0, 'hasta': g.get('hasta'), 'ventanas': g.get('ventanas')}
                if clics['var_sem'] is not None and clics['var_sem'] <= -25 and clics['semana_ant'] >= 10:
                    alertas.append({'tipo': 'clics', 'gravedad': 'rojo', 'texto': f"Clics {fes(clics['var_sem'])} % semana contra semana ({fes(clics['semana_ant'], 0)} → {fes(clics['semana'], 0)})"})
                elif clics['var_sem'] is not None and clics['var_sem'] <= -10 and clics['semana_ant'] >= 10:
                    alertas.append({'tipo': 'clics', 'gravedad': 'ambar', 'texto': f"Clics {fes(clics['var_sem'])} % semana contra semana ({fes(clics['semana_ant'], 0)} → {fes(clics['semana'], 0)})"})
            # semáforo del cliente (número que manda de Constanza): verde = clics 28 d ≥ −10 % y ninguna palabra fuera del top 10
            if g and 'semana' in g and not clics:
                gsc_nota = '0 clics en los dos periodos: sin dato (revisar que el sitio sea el bueno)'
            rojas = [x for x in alertas if x['gravedad'] == 'rojo']
            n10 = reparto['top10']['hoy'] if reparto else None
            if rojas:
                estado, motivo = 'rojo', rojas[0]['texto']
            elif (clics and clics['var_mes'] is not None and clics['var_mes'] < -10) or any(x['gravedad'] == 'ambar' for x in alertas):
                estado = 'ambar'
                motivo = next((x['texto'] for x in alertas if x['gravedad'] == 'ambar'), f"Clics {fes(clics['var_mes'])} % en 28 días" if clics else '')
            elif not clics:
                # sin clics medidos no hay verde: gris «sin dato» (regla 6 de la ronda de arreglos)
                estado = 'gris'
                motivo = ('Clics sin dato' + (f' · {n10} de 15 palabras en el top 10' if n10 is not None else ' · sin SE Ranking')) if s else 'Sin SE Ranking ni Search Console conectados'
            else:
                estado, motivo = 'verde', f"Clics estables o al alza y ninguna de las 15 ha salido del top 10 · {n10} de 15 en el top 10" if n10 is not None else 'Clics estables o al alza · sin SE Ranking'
            filas.append({
                'cliente_id': c['id'], 'cliente': c['nombre'], 'web': c.get('web'),
                'seo_id': sil.get('seo'), 'seo_nombre': personas.get(sil.get('seo')), 'web_id': sil.get('web'), 'web_nombre': personas.get(sil.get('web')),
                'top10_15': reparto['top10']['hoy'] if reparto else None,
                'ga4_enlace': ('https://analytics.google.com/analytics/web/#/p' + str((ga.get('emparejado') or {}).get('id') or '').split('/')[-1] + '/reports/intelligenthome') if (ga.get('emparejado') or {}).get('id') else None,
                'servicio_seo': serv.get('seo'), 'servicio_fuente': serv.get('seo_fuente'),
                'estado': estado, 'motivo': motivo, 'alertas': sorted(alertas, key=lambda x: x['gravedad'] != 'rojo')[:12],
                'n_alertas': {'rojo': len(rojas), 'ambar': len(alertas) - len(rojas)},
                'seranking': {'proyecto': s['proyecto'], 'ultima': s['ultima_comprobacion'], 'prueba': s['prueba'], 'seguidas': sum(len(m['palabras']) for m in s['motores']),
                              'top10_todas': todas_top10, 'buscadores': len(s['motores']), 'motores_contexto': motores_sr,
                              'nota_posiciones': 'Consultas provisionales del primer motor; mejor posición de dos comprobaciones. Contexto parcial si no constan región/dispositivo.'} if s else None,
                'informe15': [{'k': p['k'], 'vol': p['vol'], 'hoy': p['hoy'], 'sem': p['sem'], 'mes': p['mes'], 'mapa':p['mapa'],'motor_id':p['motor_id'],'fechas':p['fechas'],'fechas_d':p['fechas_d'],'hoy_d':p['hoy_d'],'sem_d':p['sem_d'],'cobertura':'parcial; orgánico/maps separados, contexto motor en seranking.motores_contexto'} for p in informe] if s else [],
                'reparto': reparto, 'movimientos': movimientos, 'visibilidad': visib, 'clics': clics,
                'gsc': {'site': g['site'], 'serie': g.get('serie', []), 'paginas': g.get('paginas', []), 'busquedas': [b for b in g.get('busquedas', []) if not consulta_basura(b[0] if b else '')]} if g and 'semana' in g else None,
                'gsc_estado': (c['fuentes'].get('gsc') or {}).get('estado') if g else 'sin_conectar', 'gsc_nota': re.sub(r'\s*\(\d{5,}\)', '', gsc_nota or '') or None,
                'ga4': {'actual': (ga.get('datos') or {}).get('actual'), 'anterior': (ga.get('datos') or {}).get('anterior'),
                        'canales': (ga.get('datos') or {}).get('canales'), 'estado': ga.get('estado'), 'hora': ga.get('hora')} if ga.get('datos') else {'estado': ga.get('estado'), 'nota': ga.get('nota')},
                'mes1_sin_palabras': bool(((c['fuentes'].get('arranque') or {}).get('datos')) and (not s or sum(len(m['palabras']) for m in s['motores']) < 20)),
            })
        # ---------------- webs (todas: el equipo web cubre guardias de todas, ficha G3-4)
        if c.get('web'):
            m = (mon or {}).get('webs', {}).get(c['id'])
            avisos = []
            if c['id'] in AVISOS_MEDICION:
                t, d, h = AVISOS_MEDICION[c['id']]
                avisos.append({'tipo': 'medicion', 'titulo': t, 'texto': d, 'que_hacer': h, 'fuente': 'revisión de Analytics del 2-oct'})
            if (c['fuentes'].get('ga4') or {}).get('estado') == 'a_cero' and c['id'] not in AVISOS_MEDICION:
                avisos.append({'tipo': 'medicion', 'titulo': 'Analytics a cero', 'texto': (c['fuentes'].get('ga4') or {}).get('nota') or 'La propiedad de GA4 marca 0 sesiones en 30 días.', 'que_hacer': 'Revisar la etiqueta de GA4 de la web.', 'fuente': 'Analytics, 30 días'})
            gd = (ga.get('datos') or {})
            dejo = (gd.get('anterior') or {}).get('usuarios', 0) > 50 and not (gd.get('actual') or {}).get('usuarios')
            if dejo:
                avisos.insert(0, {'tipo': 'medicion', 'gravedad': 'rojo', 'titulo': 'La etiqueta de Analytics dejó de medir', 'texto': f"El mes anterior tuvo {fes(gd['anterior']['usuarios'], 0)} usuarios y este, 0.", 'que_hacer': 'Revisar la etiqueta de Analytics y el banner de cookies (lo arregla web).', 'fuente': 'Analytics, 30 días'})
            if m:
                ok = m.get('estado') and 200 <= m['estado'] < 400
                if not ok:
                    est = 'rojo'
                    txt = f"No responde desde la IP de RO: {('error ' + str(m['estado']) + (' (la portada no existe)' if m['estado'] == 404 else '')) if m.get('estado') else error_llano(m.get('error'))}"
                elif len(m.get('spam') or []) >= 2:
                    est, txt = 'rojo', f"Posible spam inyectado en la portada: {', '.join(m['spam'])}"
                elif m.get('spam'):
                    est, txt = 'ambar', f"Palabra sospechosa en la portada («{m['spam'][0]}»): revisar"
                elif m.get('cert_dias') is not None and m['cert_dias'] <= 7:
                    est, txt = 'rojo', f"El certificado caduca en {m['cert_dias']} días"
                elif m.get('cert_error'):
                    est, txt = 'ambar', 'No se pudo leer el certificado'
                elif m.get('cert_dias') is not None and m['cert_dias'] <= 30:
                    est, txt = 'ambar', f"El certificado caduca en {m['cert_dias']} días"
                elif m['ms'] >= LENTA_MS:
                    est, txt = 'ambar', f"Respuesta lenta: {fes(m['ms']/1000)} s en servir la portada (la velocidad real, con PageSpeed)"
                else:
                    est, txt = 'verde', 'Responde bien desde la IP de RO'
            else:
                est, txt = 'gris', 'Sin comprobar'
            if dejo and est != 'rojo':
                est, txt = 'rojo', 'La etiqueta de Analytics dejó de medir (0 usuarios este mes)'
            webs.append({'cliente': c['id'], 'nombre': c['nombre'], 'url': c['web'], 'estado': est, 'motivo': txt,
                         'web_id': sil.get('web'), 'web_nombre': personas.get(sil.get('web')),
                         # R12: sin persona de web = duda para Mili (Ajustes, R12-WEB); si quien la tiene no es de web (Miguel), se dice
                         'web_aviso': ('Sin persona de web asignada: pendiente de Mili' if not sil.get('web') else
                                       'Su puesto es GoHighLevel: pendiente de que Mili o Tomás decidan quién lleva esta web'
                                       if 'web' not in puestos_de.get(sil.get('web'), {'web'}) else None),
                         'comprobacion': {k: m.get(k) for k in ('hora', 'estado', 'final', 'ms', 'cert_caduca', 'cert_dias', 'spam', 'error', 'cert_error')} if m else None,
                         'avisos': avisos, 'con_campana': bool(((c['fuentes'].get('meta') or {}).get('datos') or {}).get('campanas'))})
    ro = (mon or {}).get('webs', {}).get('_ro')
    if ro:
        webs.insert(0, {'cliente': '_ro', 'nombre': 'Ranking Online (nuestra web)', 'url': 'https://rankingonline.com/', 'propia': True,
                        'estado': 'verde' if ro.get('estado') and 200 <= ro['estado'] < 400 else 'rojo',
                        'motivo': 'Responde bien desde la IP de RO' if ro.get('estado') and 200 <= ro['estado'] < 400 else f"No responde desde la IP de RO: {ro.get('estado') or error_llano(ro.get('error'))} · caso Hostinger 2-oct: comprobar desde fuera",
                        'comprobacion': {k: ro.get(k) for k in ('hora', 'estado', 'final', 'ms', 'cert_caduca', 'cert_dias', 'spam', 'error', 'cert_error')},
                        'avisos': [], 'con_campana': True})
    # V2 · UNA definición de «web lenta» para SEO, ficha y webs, Mi día y Alertas: responde (200-399) y tarda LENTA_MS o más en
    # servir la portada, esté en el color que esté (una web con spam también puede ser lenta). Antes: 3, 10 y 14 según la pantalla.
    for w in webs:
        cpr = w.get('comprobacion') or {}
        w['lenta'] = bool(cpr.get('estado') and 200 <= cpr['estado'] < 400 and (cpr.get('ms') or 0) >= LENTA_MS)
        w['responde'] = bool(cpr.get('estado') and 200 <= cpr['estado'] < 400)
    orden = {'rojo': 0, 'ambar': 1, 'gris': 2, 'verde': 3}
    filas.sort(key=lambda f: (orden[f['estado']], -f['n_alertas']['rojo'], f['cliente']))
    webs.sort(key=lambda w: (not w.get('propia'), orden[w['estado']], -len(w['avisos']), w['nombre']))
    medibles = [f for f in filas if f['estado'] != 'gris']
    verdes = sum(1 for f in medibles if f['estado'] == 'verde')
    # V2 · visibilidad de 7 días «fiable» solo si SE Ranking no dejó de ver más de 3 palabras del cliente: si no, la caída
    # (−100 % con los clics subiendo) es el fallo suyo y se pinta en gris «sin dato fiable», nunca en rojo.
    for f in filas:
        if f.get('visibilidad'):
            f['visibilidad']['fiable'] = (f['visibilidad'].get('desaparecen') or 0) <= 3
    aviso = aviso_sr(filas)
    pct_v = round(100 * verdes / len(medibles)) if medibles else None
    meta = {'generado': dt.datetime.now().strftime('%Y-%m-%d %H:%M'), 'hoy': str(HOY),
            'seranking': info_sr(sr),
            'gsc': {'leido': (gsc or {}).get('leido'), 'regla': 'Search Console va 2-3 días por detrás: cada sitio se compara hasta su último día con dato (7 y 28 días cerrados frente a los mismos días justo antes).',
                    'hasta': max([x.get('hasta') for x in (gsc or {}).get('clientes', {}).values() if x.get('hasta')] or [None])},
            'confirmacion': 'Mejor de dos observaciones sólo cuando ambas existen con fechas consecutivas; si falta una no acredita confirmación doble. Movimientos sólo pares fechados exactamente7d del mismo motor.',
            'informe15': 'Provisional: las 15 de más búsquedas entre las que han estado en el top 30 este mes (y, si no llegan a 15, las de más búsquedas). Cuando cada SEO marque su grupo «Informe» en SE Ranking, se leen esas.',
            'visibilidad': 'Calculada con las posiciones de SE Ranking: búsquedas × clic esperado por posición (30 % el 1.º … 2 % el 10.º, 1 % del 11 al 20), hoy frente a hace 7 días, todos los buscadores del proyecto, solo palabras seguidas desde hace más de 8 días.'}
    seo = {'_meta': meta,
           # R12 · número que manda de la jefa de SEO, UNA definición para Mi día y para SEO: % de clientes en verde sobre los
           # que se pueden medir (sin los grises «sin dato»), umbral de su ficha G3: bien desde el 80 %, mal bajo el 60 %.
           # «clientes_seo» es esa base (la que se enseña: «1 de 38»); «clientes_total» cuenta también los grises.
           'resumen': {'clientes_seo': len(medibles), 'clientes_total': len(filas), 'medibles': len(medibles), 'verdes': verdes, 'pct_verde': round(100 * verdes / len(medibles)) if medibles else None,
                       'umbral': UMBRAL_VERDE, 'estado': estado_pct(round(100 * verdes / len(medibles)) if medibles else None),
                       'sello': 'a medias: las 15 palabras son provisionales y no todos tienen Search Console',
                       'rojos': sum(1 for f in filas if f['estado'] == 'rojo'), 'ambar': sum(1 for f in filas if f['estado'] == 'ambar'),
                       'sin_conectar': len(filas) - len(medibles),
                       'fuera_top10': sum(1 for f in filas for a in f['alertas'] if a['tipo'] == 'fuera_top10'),
                       'desaparecen': sum(1 for f in filas for a in f['alertas'] if a['tipo'] == 'desaparece'),
                       'desaparecen_total': sum((f['visibilidad'] or {}).get('desaparecen', 0) for f in filas),
                       'clics_suben': sum(1 for f in filas if f['clics'] and (f['clics']['var_mes'] or 0) > 0),
                       'con_gsc': sum(1 for f in filas if f['gsc']), 'con_sr': sum(1 for f in filas if f['seranking']),
                       'top5': {'hoy': suma_medida((f['reparto'] or {}).get('top5',{}).get('hoy') for f in filas),
                                'mes': suma_medida((f['reparto'] or {}).get('top5',{}).get('mes') for f in filas),
                                'sin_ver_hoy': sum((f['reparto'] or {}).get('top5', {}).get('sin_ver_hoy', 0) for f in filas)},
                       'aviso_seranking': aviso,
                       # V2 · el número que manda no da un color apoyándose en un dato en duda: con el aviso de SE Ranking
                       # va «a medias» y en gris, con el motivo. «estado» sigue siendo la regla pura (pruebas_coherencia).
                       'medible': 'medias', 'estado_mostrado': 'gris' if aviso else estado_pct(pct_v),
                       'motivo_medible': (f"Dato en duda: SE Ranking dejó de ver {aviso['desaparecen']} palabras de golpe (parece un fallo suyo). "
                                          'Hasta que se compruebe en Google, esta cifra no se pinta en verde ni en rojo.') if aviso else
                                         'Las 15 palabras son provisionales (las de más búsquedas) y no todos los clientes tienen Search Console.'},
           'clientes': filas}
    webs_out = {'_meta': {'generado': meta['generado'], 'monitor': {'leido': (mon or {}).get('leido'), 'desde': (mon or {}).get('desde')},
                          'diseno': 'Dos puntos de vista: (1) desde la IP de RO, este Mac hoy y el Worker de Cloudflare con W1; (2) desde fuera, un monitor externo gratuito. Caída = falla en los dos; «bloqueada solo para RO» = fuera responde y desde RO no (caso Hostinger 2-oct). Cada 5 minutos; aviso tras 2 fallos seguidos.',
                          'regla_dueno': 'Dueño de cada web = la persona principal de la silla «web» en asignaciones (una sola por cliente). Las webs sin dueño son una duda para Mili en Ajustes (R12-WEB); la app no inventa a nadie.',
                          'lenta': {'umbral_ms': LENTA_MS, 'texto': f'Lenta = responde, pero tarda {LENTA_MS // 1000} s o más en servir la portada desde la IP de RO (sea cual sea su color). La velocidad real, con PageSpeed.'},
                          'responde': 'Responde = la portada contesta con un código 200-399 desde la IP de RO (la cifra que manda del puesto web).',
                          'pagespeed': 'PageSpeed se conecta: falta la clave gratuita de la API (ficha G3-2, pregunta 3). Sin ella no se mide la velocidad real (puntuación móvil y carga del elemento principal); aquí solo se ve el tiempo de servir el HTML.'},
                'resumen': {'webs': len(webs), 'rojo': sum(1 for w in webs if w['estado'] == 'rojo'), 'ambar': sum(1 for w in webs if w['estado'] == 'ambar'),
                            'verde': sum(1 for w in webs if w['estado'] == 'verde'), 'avisos_medicion': sum(len(w['avisos']) for w in webs),
                            'lentas': sum(1 for w in webs if w['lenta']), 'responden': sum(1 for w in webs if w['responde']),
                            'cert_30': sum(1 for w in webs if (w['comprobacion'] or {}).get('cert_dias') is not None and w['comprobacion']['cert_dias'] <= 30)},
                'webs': webs}
    return seo, webs_out


if __name__ == '__main__':
    vivo = set((sys.argv[sys.argv.index('--en-vivo') + 1].split(',')) if '--en-vivo' in sys.argv else [])
    cls = clientes()
    sr = json.load(open(C('seranking.json')))
    gsc = leer_gsc(cls) if 'gsc' in vivo else (json.load(open(C('gsc.json'))) if os.path.exists(C('gsc.json')) else None)
    mon = leer_monitor(cls) if 'monitor' in vivo else (json.load(open(C('monitor.json'))) if os.path.exists(C('monitor.json')) else None)
    seo, webs = construir(cls, sr, gsc, mon)
    for nombre, obj in (('seo', seo), ('webs', webs)):
        texto = json.dumps(obj, ensure_ascii=False)
        if re.search(r'[\w.+-]+@[\w-]+\.[a-z]{2,}', texto):
            sys.exit(f'Puerta de secretos: hay un correo en {nombre}.json. No se escribe nada.')
        guardar(os.path.join(APP, 'data', 'seo', f'{nombre}.json'), obj)
    r = seo['resumen']
    print(f"seo.json: {r['clientes_seo']} clientes con SEO · {r['verdes']}/{r['medibles']} en verde ({r['pct_verde']} %) · {r['fuera_top10']} palabras fuera del top 10")
    w = webs['resumen']
    print(f"webs.json: {w['webs']} webs · {w['rojo']} rojo · {w['ambar']} ámbar · {w['avisos_medicion']} avisos de medición")
