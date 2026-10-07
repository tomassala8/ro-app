#!/usr/bin/env python3
"""Outreach de clientes a fondo (3-oct, feedback de Tomás mirando como Eulimar) · data/outreach/outreach_plus.json. SOLO LECTURA.

Lo que añade a data/ventas_ro/outreach.json (que sigue haciendo generar_ventas_ro.py):
  · Cifras de cada campaña de Snov.io: enviados, entregados, aperturas, respuestas, interesados, rebotes y bajas en 30 días
    y semana a semana (las 6 últimas), con /v2/statistics/campaign-analytics (lectura).
  · Respuestas de Snov.io CLASIFICADAS solas: positiva, neutra / más adelante, negativa, baja (que no le escriban) y
    rebote / fuera de oficina. Por reglas (palabras clave en español, catalán e inglés) y, si hay clave de IA, afinado
    con IA (tarea «clasificar», la barata) dentro de los topes de ia_gasto.py. La IA solo mira las que las reglas no
    resuelven y como mucho 40 por vuelta. El texto de la respuesta va SOLO al almacén privado (sin correos ni teléfonos).
  · Linked Helper: el CSV de un año de las 4 cuentas activas (sacado a mano el 2-oct). Entra como fuente con fecha
    («dato del 2-oct»): invitaciones, aceptadas, mensajes y respuestas por cuenta, semana y mes. No hay API: nada en vivo.
  · Explee: la app no tiene sus respuestas (llegan a tomas@ en Zoho Mail): se dice, con su cliente.
  · Resultados por cliente (cliente primero) frente a objetivo: reuniones por 1.000 contactos (≥ 4), respuesta del correo
    (≥ 5,5 %), aceptación en LinkedIn (≥ 45 %) y rebote (< 2 %), de indicadores.json (ficha G3).

Uso:
  python3 fuentes_ventas/generar_outreach.py            → lee Snov.io (completa) y el CSV de Linked Helper
  python3 fuentes_ventas/generar_outreach.py --sin-snov → sin llamadas: reclasifica con el texto ya guardado y conserva
                                                          las cifras de Snov de la última lectura buena (pasada ligera)
Salida: data/outreach/outreach_plus.json (sin nombres, correos ni teléfonos) y el «extracto» de cada respuesta en
        data/ventas_ro/_privado/outreach_respuestas.json (el almacén que ya abre «Ver respuesta», con rastro).
Las campañas de RO (frente «ro») van marcadas: el servidor solo las deja ver a quien tiene el tipo «campanas_ro».
"""
import csv, datetime as dt, hashlib, json, os, re, sys, time, unicodedata
from zoneinfo import ZoneInfo

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(1, RAIZ)
import config  # noqa: E402

MAD = ZoneInfo('Europe/Madrid')
AHORA = dt.datetime.now(MAD)
HOY = AHORA.date()
ARGS = set(sys.argv[1:])
SALIDA = os.path.join(RAIZ, 'data', 'outreach')
VENTAS = os.path.join(RAIZ, 'data', 'ventas_ro')
PRIV = os.path.join(VENTAS, '_privado', 'outreach_respuestas.json')
LH_DIR = config.CRUDOS / 'LINKED_HELPER_EXPORT_2026-10-02'
LH_FECHA = '2026-10-02'
SEMANAS = 6
TOPE_IA = 40

# Cuentas de Linked Helper → cliente (memoria del 2-oct: las 4 son de Proincentiva; Vegas Legal es su origen y
# José Luis Vegas su cara visible; Adrián Ramírez es su cofundador).
LH_CLIENTE = {'adrián ramírez': 'proincentiva', 'javier plaza': 'proincentiva', 'jorge arnau': 'proincentiva', 'josé luis vegas': 'proincentiva'}
LH_AVISOS = {'javier plaza': 'Parado desde el 2-oct: hay que arrancarlo desde el servidor de Linked Helper (no desde la web).'}

fuentes = []
def fuente(nombre, estado, detalle='', hora=None):
    fuentes.append({'fuente': nombre, 'estado': estado, 'detalle': detalle, 'hora': hora or AHORA.strftime('%Y-%m-%d %H:%M')})

def norm(x):
    x = unicodedata.normalize('NFD', (x or '').lower())
    return ' '.join(''.join(ch for ch in x if not unicodedata.combining(ch)).split())

def ts(s):
    if not s: return None
    try:
        x = dt.datetime.fromisoformat(str(s).replace('Z', '+00:00'))
    except ValueError:
        return None
    return x.astimezone(MAD) if x.tzinfo else x.replace(tzinfo=MAD)

def leer(ruta, defecto=None):
    try:
        return json.load(open(ruta, encoding='utf-8'))
    except Exception:
        return defecto

# ------------------------------------------------------------------ texto de la respuesta (sin lo citado, sin datos)
CITA = re.compile(r"(\b(El|On|Le|Am)\b[^<>]{0,120}?\b(escribió|escribio|wrote|va escriure|a écrit|schrieb)\s*:)|(-{3,}\s*(Original|Mensaje original|Missatge original))|"
                  r"(\n\s*(De|From|Enviado el|Sent):\s)|(_{6,})|(Enviado desde mi )|(Sent from my )", re.I)

def texto_respuesta(r):
    """El texto que escribió el prospecto: el cuerpo del último correo de la respuesta sin el correo citado."""
    cuerpos = [m.get('emailBody') for m in (r.get('emails') or []) if isinstance(m, dict) and isinstance(m.get('emailBody'), str)]
    for k in ('replyText', 'reply', 'message', 'text', 'body', 'emailBody'):
        if isinstance(r.get(k), str) and r[k].strip():
            cuerpos.append(r[k])
    if not cuerpos: return ''
    t = cuerpos[-1]
    t = re.sub(r'(?i)<br\s*/?>|</p>|</div>', '\n', t)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = t.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"').replace('&#39;', "'")
    m = CITA.search(t)
    if m and m.start() > 0: t = t[:m.start()]
    return re.sub(r'\s+', ' ', t).strip()

def sin_datos(t):
    """Fuera correos, teléfonos y enlaces del extracto: para clasificar no hacen falta."""
    t = re.sub(r'[\w.+-]+@[\w-]+\.[\w.]+', '[correo]', t or '')
    t = re.sub(r'(?<!\d)(\+?\d[\d .-]{7,}\d)(?!\d)', '[teléfono]', t)
    return re.sub(r'https?://\S+', '[enlace]', t)

# ------------------------------------------------------------------ clasificación por reglas (es · ca · en)
REGLAS = [   # (clase, palabras) en orden: la primera que encaja manda. Negativas antes que positivas («no me interesa»).
    ('rebote', ['fuera de la oficina', 'fuera de oficina', 'out of office', 'out of the office', 'respuesta automatica', 'automatic reply',
                'auto-reply', 'autoreply', 'respuesta automatica', 'estare fuera', 'de vacaciones', 'no estare disponible', 'ausente hasta',
                'fora de l\'oficina', 'resposta automatica', 'estic de vacances', 'undeliverable', 'delivery status notification', 'mail delivery',
                'no se ha podido entregar', 'no ha podido ser entregado', 'direccion no existe', 'ya no trabaja', 'ja no treballa', 'no longer with',
                'no longer works', 'buzon no', 'mailbox unavailable', 'baja maternal', 'baja por maternidad', 'permiso de paternidad']),
    ('baja', ['no me escrib', 'no nos escrib', 'deje de escribir', 'dejen de escribir', 'dejad de escribir', 'deja de escribir', 'darme de baja',
              'dadme de baja', 'denme de baja', 'me deis de baja', 'me den de baja', 'baja de vuestra', 'baja de su', 'eliminad mis datos', 'eliminen mis datos',
              'eliminar mis datos', 'borrad mis datos', 'borren mis datos', 'borrar mis datos', 'unsubscribe', 'remove me', 'stop emailing', 'stop sending',
              'de donde habeis sacado', 'de donde ha sacado', 'de donde sacais', 'de donde han sacado', 'de donde sacan', 'rgpd', 'proteccion de datos',
              'no em torneu', 'doneu-me de baixa', 'no vuelvan a', 'no volvais a', 'no vuelvas a', 'spam']),
    ('negativa', ['no me interesa', 'no nos interesa', 'no estamos interesados', 'no estoy interesad', 'no interesado', 'no interesada',
                  'no gracias', 'no, gracias', 'ya tenemos', 'ya tengo', 'estamos contentos', 'estoy contento', 'estamos satisfechos', 'muy contentos con',
                  'no necesitamos', 'no necesito', 'ya no dispongo', 'no dispongo de', 'no tengo empresa', 'cerrado la empresa', 'not interested',
                  'no thanks', 'no thank you', 'no m\'interessa', 'no ens interessa', 'ja tenim', 'no estem interessats', 'descartado', 'no procede',
                  'no es de nuestro interes', 'no es para nosotros', 'no aplica']),
    ('positiva', ['me interesa', 'nos interesa', 'interesado', 'interesada', 'interesante', 'mas informacion', 'mas info', 'informacion',
                  'mas detalles', 'precio', 'presupuesto', 'tarifa', 'cuanto cuesta', 'cuanto costaria', 'honorarios', 'llamame', 'llamadme', 'llamarme',
                  'me llamas', 'podemos hablar', 'hablamos', 'reunion', 'una cita', 'agendar', 'calendly', 'cuando os va bien', 'que dia', 'disponibilidad',
                  'mi telefono', 'mi movil', 'enviame', 'enviadme', 'mandame', 'mandadme', 'valorar', 'propuesta', 'me gustaria', 'nos gustaria',
                  'adelante', 'm\'interessa', 'ens interessa', 'informacio', 'truca\'m', 'trucar', 'reunio', 'parlem', 'interested', 'call me',
                  'meeting', 'send me', 'pricing', 'tell me more', 'let\'s talk', 'sounds good', 'schedule']),
    ('neutra', ['mas adelante', 'mas tarde', 'ahora no', 'en este momento no', 'no es el momento', 'el ano que viene', 'proximo ano', 'en enero',
                'a partir de', 'dentro de unos meses', 'mes endavant', 'ara no', 'later', 'not right now', 'next year', 'reenviado', 'lo paso', 'se lo paso',
                'le reenvio', 'no soy la persona', 'contacte con', 'contacta con', 'quizas', 'tal vez', 'lo pensare', 'lo consulto']),
]
REGLAS = [(c, [norm(p) for p in ps]) for c, ps in REGLAS]
CLASES = {'positiva': 'Positiva', 'neutra': 'Neutra / más adelante', 'negativa': 'Negativa', 'baja': 'Baja (que no le escriban)', 'rebote': 'Rebote / fuera de oficina'}

def por_reglas(texto, asunto=''):
    """(clase, palabra que lo decide) o (None, None) si no encaja ninguna regla."""
    t = norm(f'{asunto} {texto}') if not texto else norm(texto)
    if not t: return None, None
    for clase, palabras in REGLAS:
        for p in palabras:
            if re.search(r'(?<![a-z])' + re.escape(p), t):
                return clase, p
    return None, None

def ia_clasificar(pendientes):
    """Afina con IA las que las reglas no resuelven. Sin clave, sin paquete o sin tope: nada (y se dice)."""
    if not pendientes: return {}, 'nada que afinar'
    tiene = bool(os.environ.get('ANTHROPIC_API_KEY'))
    if not tiene and sys.platform == 'darwin':
        import subprocess
        tiene = subprocess.run(['security', 'find-generic-password', '-s', 'anthropic_api_key'], capture_output=True).returncode == 0
    if not tiene: return {}, 'sin clave de IA: solo reglas'
    try:
        os.environ.setdefault('RO_AVISOS_SIN_BUCLE', '1')
        import servir as S  # noqa: E402
        import ia as IA     # noqa: E402
        S.E.cargar()
        if IA.S is None: IA.enganchar(S.Manejador, S)
        if not IA.estado()['conectada']: return {}, IA.estado()['motivo']
    except Exception as e:
        return {}, f'IA no disponible: {str(e)[:120]}'
    sistema = ('Clasificas respuestas a correos de prospección en frío de despachos y asesorías de España (español, catalán o inglés). '
               'Clases: positiva (interés, pide información, precio o reunión), neutra (más adelante, reenvía a otra persona, duda), '
               'negativa (no le interesa, ya tiene asesoría), baja (pide que no le escriban o borrar sus datos), rebote (automática, fuera de oficina, '
               'ya no trabaja ahí). Devuelve solo la clase y una razón de 8 palabras como mucho.')
    esquema = {'type': 'object', 'properties': {'clase': {'type': 'string', 'enum': list(CLASES)}, 'razon': {'type': 'string'}}, 'required': ['clase', 'razon'], 'additionalProperties': False}
    out = {}
    for rid, texto in list(pendientes.items())[:TOPE_IA]:
        try:
            s, _ = IA.G.llamar(sistema, {'respuesta': texto[:1200]}, esquema, effort='low', tarea='clasificar')
            if isinstance(s, dict) and s.get('clase') in CLASES: out[rid] = (s['clase'], (s.get('razon') or '')[:80])
        except Exception as e:
            return out, f'IA parada a mitad: {str(e)[:120]}'
    return out, f'{len(out)} afinadas con IA'

# ------------------------------------------------------------------ Snov.io (lectura)
KEYS = {'enviados': 'emails_sent', 'entregados': 'delivered', 'contactados': 'total_contacted', 'aperturas': 'email_opens',
        'respuestas': 'email_replies', 'interesados': 'interested', 'quizas': 'maybe', 'no_interesados': 'not_interested',
        'bajas': 'unsubscribed', 'automaticas': 'auto_replied', 'rebotes': 'bounced', 'clics': 'link_clicks'}

def lunes(d): return d - dt.timedelta(days=d.weekday())

def leer_snov(outreach, priv):
    sys.path.insert(0, str(config.HERRAMIENTAS / 'snov'))
    import sv
    tk = sv.token()

    def stats(cid, a, b):
        for i in range(4):
            r = sv.get(tk, '/v2/statistics/campaign-analytics', campaign_id=cid, date_from=str(a), date_to=str(b))
            if isinstance(r, dict) and r.get('_error') == 429:
                time.sleep(2 + 2 * i); continue
            if not isinstance(r, dict) or '_error' in r: return None
            return {k: int(r.get(v) or 0) for k, v in KEYS.items()}
        return None

    campañas, textos = [], {}
    l0 = lunes(HOY)
    semanas = [(l0 - dt.timedelta(weeks=i)) for i in range(SEMANAS - 1, -1, -1)]
    for c in (outreach.get('snov') or {}).get('campañas') or []:
        cid = c['id']
        d30 = stats(cid, HOY - dt.timedelta(days=30), HOY)
        sem = []
        if d30 and (d30['enviados'] or d30['respuestas'] or d30['contactados']):
            for s in semanas:
                x = stats(cid, s, min(s + dt.timedelta(days=6), HOY))
                sem.append({'semana': s.isoformat(), **(x or {})})
                time.sleep(0.25)
        campañas.append({'id': cid, 'nombre': c['nombre'], 'estado': c.get('estado'), 'frente': c.get('frente'), 'cliente_id': c.get('cliente_id'),
                         'd30': d30, 'semanas': sem})
        # el texto de cada respuesta (para clasificar): mismo id que generar_ventas_ro.py
        reps = sv.get(tk, '/v1/get-emails-replies', campaignId=cid)
        for r in reps if isinstance(reps, list) else []:
            rid = 'r' + hashlib.sha1(f"{cid}:{r.get('id')}".encode()).hexdigest()[:12]
            asunto = next((m.get('emailSubject') for m in (r.get('emails') or []) if isinstance(m, dict) and m.get('emailSubject')), '')
            textos[rid] = {'texto': texto_respuesta(r), 'asunto': asunto or ''}
        time.sleep(0.25)
    return campañas, textos

# ------------------------------------------------------------------ Linked Helper (CSV del 2-oct)
def leer_linked_helper():
    ruta = LH_DIR / 'linkedhelper_diario.csv'
    if not ruta.exists():
        fuente('Linked Helper (CSV del 2-oct)', 'sin datos', f'no está {ruta.name}')
        return None
    filas = list(csv.DictReader(open(ruta, encoding='utf-8')))
    cuentas = {}
    hasta = dt.date.fromisoformat(LH_FECHA)
    l0 = lunes(hasta)
    sem_ini = [(l0 - dt.timedelta(weeks=i)) for i in range(7, -1, -1)]
    for f in filas:
        nombre = (f.get('cuenta') or '').strip()
        base = norm(nombre.split('(')[0])
        d = dt.date.fromisoformat(f['fecha'])
        x = cuentas.setdefault(nombre, {'cuenta': nombre, 'cliente_id': next((v for k, v in LH_CLIENTE.items() if norm(k) == base), None),
                                         'aviso': next((v for k, v in LH_AVISOS.items() if norm(k) == base), None),
                                         'd30': {'invitaciones': 0, 'aceptadas': 0, 'mensajes': 0, 'respuestas': 0},
                                         'anio': {'invitaciones': 0, 'aceptadas': 0, 'mensajes': 0, 'respuestas': 0},
                                         'semanas': {s.isoformat(): {'invitaciones': 0, 'aceptadas': 0, 'mensajes': 0, 'respuestas': 0} for s in sem_ini},
                                         'meses': {}, 'ultimo_dia_con_actividad': None})
        v = {'invitaciones': int(f.get('invited') or 0), 'aceptadas': int(f.get('accepted') or 0), 'mensajes': int(f.get('messaged') or 0), 'respuestas': int(f.get('replied') or 0)}
        for k in v: x['anio'][k] += v[k]
        if (hasta - d).days < 30:
            for k in v: x['d30'][k] += v[k]
        s = lunes(d).isoformat()
        if s in x['semanas']:
            for k in v: x['semanas'][s][k] += v[k]
        m = x['meses'].setdefault(f['fecha'][:7], {'invitaciones': 0, 'aceptadas': 0, 'mensajes': 0, 'respuestas': 0})
        for k in v: m[k] += v[k]
        if any(v.values()) and (not x['ultimo_dia_con_actividad'] or f['fecha'] > x['ultimo_dia_con_actividad']):
            x['ultimo_dia_con_actividad'] = f['fecha']
    out = []
    for x in cuentas.values():
        x['semanas'] = [{'semana': k, **v} for k, v in sorted(x['semanas'].items())]
        x['meses'] = [{'mes': k, **v} for k, v in sorted(x['meses'].items())][-12:]
        a = x['d30']
        x['d30']['aceptacion_pct'] = round(100 * a['aceptadas'] / a['invitaciones'], 1) if a['invitaciones'] else None
        x['d30']['respuesta_pct'] = round(100 * a['respuestas'] / a['mensajes'], 1) if a['mensajes'] else None
        out.append(x)
    fuente('Linked Helper (CSV del 2-oct)', 'viejo', f'{len(out)} cuentas activas, un año (2-oct-2025 → 2-oct-2026); sin API: no se actualiza solo', f'{LH_FECHA} 13:25')
    return {'dato_del': LH_FECHA, 'sello': 'Dato del 2-oct', 'cuentas': sorted(out, key=lambda c: -c['d30']['invitaciones']),
            'como_se_saco': 'A mano por la web: control remoto → Observador → Panel de control → fechas → «Descargar CSV».'}

# ------------------------------------------------------------------ objetivos (ficha G3, indicadores.json)
def objetivos():
    obj = {'reuniones_por_mil': 4, 'respuesta_correo_pct': 5.5, 'aceptacion_linkedin_pct': 45, 'rebote_max_pct': 2}
    try:
        ind = json.load(open(os.path.join(RAIZ, 'indicadores.json'), encoding='utf-8'))
        lista = ind if isinstance(ind, list) else ind.get('indicadores', ind)
        lista = list(lista.values()) if isinstance(lista, dict) else lista
        ids = {x.get('id'): x for x in lista if isinstance(x, dict)}
        obj['_origen'] = {k: (ids.get(i) or {}).get('umbral') for k, i in (('reuniones_por_mil', 'outreach.reuniones_por_1_000_contactos'),
                         ('respuesta_correo_pct', 'outreach.tasa_de_respuesta_del_correo'), ('aceptacion_linkedin_pct', 'outreach.aceptacion_de_invitaciones_en_linkedin'),
                         ('rebote_max_pct', 'outreach.rebotes_y_quejas_por_spam'))}
    except Exception:
        pass
    return obj

# ------------------------------------------------------------------ principal
def main():
    os.makedirs(SALIDA, exist_ok=True)
    outreach = leer(os.path.join(VENTAS, 'outreach.json'), {}) or {}
    privado = leer(PRIV, {'respuestas': {}}) or {'respuestas': {}}
    previo = leer(os.path.join(SALIDA, 'outreach_plus.json'), {}) or {}
    textos = {}
    if '--sin-snov' not in ARGS and (outreach.get('snov') or {}).get('campañas'):
        try:
            campañas, textos = leer_snov(outreach, privado)
            fuente('Snov.io · cifras y respuestas', 'ok', f'{len(campañas)} campañas; {SEMANAS} semanas; {len(textos)} respuestas con texto')
        except Exception as e:
            campañas = previo.get('campañas') or []
            fuente('Snov.io · cifras y respuestas', 'error', str(e)[:200])
    else:
        campañas = previo.get('campañas') or []
        f0 = next((f for f in previo.get('fuentes') or [] if f['fuente'].startswith('Snov.io')), None)
        fuente('Snov.io · cifras y respuestas', 'viejo' if campañas else 'sin datos', 'pasada ligera: última lectura buena' if campañas else 'se lee en la recarga completa', (f0 or {}).get('hora'))

    # 1 · clasificar: reglas → IA (si hay) → «neutra» por defecto (sin regla clara)
    resp = outreach.get('respuestas') or []
    clases, pend = [], {}
    priv_r = privado.setdefault('respuestas', {})
    for r in resp:
        t = textos.get(r['id'])
        if t is not None and r['id'] in priv_r:      # el extracto al almacén privado (sin correos ni teléfonos)
            limpio = sin_datos(t['texto'])
            priv_r[r['id']]['extracto'] = (limpio[:600] + '…') if len(limpio) > 600 else limpio
        texto = (t or {}).get('texto') or (priv_r.get(r['id']) or {}).get('extracto') or ''
        clase, porque = por_reglas(texto, (t or {}).get('asunto', ''))
        fila = {'id': r['id'], 'cliente_id': r.get('cliente_id'), 'frente': r.get('frente'), 'campana': r.get('campana'), 'fecha': r.get('fecha'),
                'clase': clase, 'motivo': f'«{porque}»' if porque else None, 'como': 'reglas' if clase else None, 'con_texto': bool(texto)}
        if not clase and texto: pend[r['id']] = sin_datos(texto)
        clases.append(fila)
    afinadas, nota_ia = ia_clasificar(pend)
    for f in clases:
        if f['id'] in afinadas:
            f['clase'], f['motivo'], f['como'] = afinadas[f['id']][0], afinadas[f['id']][1], 'ia'
        elif not f['clase']:
            f['clase'], f['como'] = 'neutra', 'sin_regla'
            f['motivo'] = 'ninguna palabra clave clara: revísala' if f['con_texto'] else 'Snov.io no ha dado el texto: revísala en Snov.io'
    fuente('Clasificación de respuestas', 'ok', f"{sum(1 for f in clases if f['como'] == 'reglas')} por reglas · {nota_ia} · {sum(1 for f in clases if f['como'] == 'sin_regla')} sin regla (neutra, a revisar)")

    # 2 · Linked Helper y Explee
    lh = leer_linked_helper()
    externos = [{'cliente_id': 'proincentiva', 'herramienta': 'Explee', 'respuestas': 71, 'en_app': False,
                 'texto': '71 respuestas de la campaña de Explee (deducción por cultura y Tax Lease) en el correo de tomas@ (Zoho Mail): la app no lo lee todavía. Las 22 nuevas del 2-oct, también ahí.',
                 'dato_del': '2026-10-01'}]

    # 3 · por cliente (cliente primero)
    obj = objetivos()
    mili = outreach.get('clientes') or {}
    sys.path.insert(0, AQUI)
    import campana_cliente as CC
    nombres = dict(CC.clientes())
    def de_mili(cid):
        for k, v in mili.items():
            if CC.cliente_de(k) == cid or norm(nombres.get(cid, '')) == norm(k): return v
        return None
    ids = sorted({c['cliente_id'] for c in campañas if c.get('cliente_id') and c.get('frente') == 'clientes'} |
                 {r['cliente_id'] for r in clases if r.get('cliente_id') and r.get('frente') == 'clientes'} |
                 {c['cliente_id'] for c in (lh or {}).get('cuentas', []) if c.get('cliente_id')})
    por_cliente = []
    for cid in ids:
        cs = [c for c in campañas if c.get('cliente_id') == cid and c.get('frente') == 'clientes']
        suma = {k: sum((c.get('d30') or {}).get(k) or 0 for c in cs) for k in KEYS}
        semanas = {}
        for c in cs:
            for s in c.get('semanas') or []:
                x = semanas.setdefault(s['semana'], {k: 0 for k in KEYS})
                for k in KEYS: x[k] += s.get(k) or 0
        rc = [r for r in clases if r.get('cliente_id') == cid and r.get('frente') == 'clientes']
        por_clase = {k: sum(1 for r in rc if r['clase'] == k) for k in CLASES}
        lhc = [c for c in (lh or {}).get('cuentas', []) if c.get('cliente_id') == cid]
        lh30 = {k: sum(c['d30'][k] for c in lhc) for k in ('invitaciones', 'aceptadas', 'mensajes', 'respuestas')} if lhc else None
        m = de_mili(cid) or {}
        reun = [x for x in ((m.get('sep') or {}).get('reuniones'), (m.get('oct') or {}).get('reuniones')) if x is not None]
        contactos = suma['contactados'] + ((lh30 or {}).get('invitaciones') or 0)
        por_cliente.append({
            'cliente_id': cid, 'nombre': nombres.get(cid, cid), 'campañas': len(cs), 'activas': sum(1 for c in cs if c.get('estado') == 'Active'),
            'correo_30d': suma, 'semanas': [{'semana': k, **v} for k, v in sorted(semanas.items())],
            'respuesta_pct': round(100 * suma['respuestas'] / suma['contactados'], 1) if suma['contactados'] else None,
            'rebote_pct': round(100 * suma['rebotes'] / suma['enviados'], 1) if suma['enviados'] else None,
            'apertura_pct': round(100 * suma['aperturas'] / suma['entregados'], 1) if suma['entregados'] else None,
            'clasificadas': por_clase, 'respuestas_30d': len(rc), 'linkedin_30d': lh30, 'linkedin_dato_del': LH_FECHA if lhc else None,
            'aceptacion_pct': round(100 * lh30['aceptadas'] / lh30['invitaciones'], 1) if lh30 and lh30['invitaciones'] else None,
            'reuniones': sum(reun) if reun else None, 'reuniones_fuente': 'Panel v7 de Mili (sep + oct)' if reun else None,
            'leads_mes': (m.get('sep') or {}).get('leads'),
            'objetivo_reuniones': round(contactos * obj['reuniones_por_mil'] / 1000, 1) if contactos else None,
            'contactos_30d': contactos,
        })
    por_cliente.sort(key=lambda x: (-(x['clasificadas']['positiva']), -(x['correo_30d']['enviados'] or 0)))

    out = {'generado': AHORA.strftime('%Y-%m-%d %H:%M'), 'objetivos': obj, 'clases': CLASES,
           'campañas': campañas, 'respuestas_clase': clases, 'por_cliente': por_cliente,
           'linked_helper': lh, 'externos': externos, 'fuentes': fuentes,
           'en_vivo_linked_helper': 'Para tenerlo en vivo hace falta: (1) leer la base de datos local de la máquina 92112 donde corren las 4 cuentas, o (2) un webhook de Linked Helper a GHL o a la app en cada campaña (en el plan Standard, tope de 20 perfiles al día), o (3) repetir el CSV a mano cada lunes. Nada de esto arranca ni toca cuentas.'}
    # puerta de secretos: nada de correos ni teléfonos en el fichero público
    t = json.dumps(out, ensure_ascii=False)
    t_sin_fechas = re.sub(r'"(generado|hora|fecha|semana|mes|dato_del|linkedin_dato_del|ultimo_dia_con_actividad|id)": "[^"]*"', '', t)
    if re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', t) or re.search(r'\+?\d[\d ]{8,}\d', t_sin_fechas):
        sys.exit('PUERTA DE SECRETOS: el fichero público lleva un correo o un teléfono; no escribo nada.')
    with open(os.path.join(SALIDA, 'outreach_plus.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    if textos:
        tmp = PRIV + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f: json.dump(privado, f, ensure_ascii=False, indent=1)
        os.replace(tmp, PRIV)
    resumen = {}
    for f in clases:
        if f['frente'] != 'clientes': continue
        x = resumen.setdefault(f['cliente_id'] or 'sin cliente', {k: 0 for k in CLASES})
        x[f['clase']] += 1
    print(json.dumps({'respuestas': len(clases), 'por_clase': {k: sum(1 for f in clases if f['clase'] == k) for k in CLASES},
                      'por_cliente': resumen, 'linked_helper': [(c['cuenta'], c['d30']) for c in (lh or {}).get('cuentas', [])],
                      'fuentes': [(f['fuente'], f['estado'], f['detalle']) for f in fuentes]}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
