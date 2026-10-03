#!/usr/bin/env python3
"""generar_nuevos.py · M12 «Clientes nuevos, de la firma al día 90» (E4 del plan v2 · punto 6 de Mili · ficha de Agus).

SOLO LECTURA. Lee y deja data/nuevos/nuevos.json (lo sirve servir.py recortado por persona: datos_de_modulo).

Fuentes (todas con los lectores de ~/RO_HERRAMIENTAS y las llaves del llavero, sin imprimirlas):
  · Zoho Sign (zoho/zh.py)          → sobres del Método Cliente Rentable / Motor: firma, alta del contrato (día 0),
                                       cláusula de encargo de tratamiento (art. 28) y si lleva garantía.
                                       Base: PANEL_OPERACIONES_2026-10-01/_crudo/nuevos/altas_contrato.json; lo nuevo, del PDF.
  · ClickUp (clickup_api/cu.py)     → listas «Onboarding —» de cada alta: tareas, estado, asignados, fecha límite,
                                       última actualización y días bloqueada (tiempo en estado).
  · Meta (meta/mt.py)               → cuenta publicitaria, estado y motivo de bloqueo, gasto y leads diarios desde la firma
                                       (encendido = primer día con gasto; primer lead), píxel y su último evento.
  · GHL agencia (ghl_agencia/app.py)→ las 66 subcuentas: calendarios y si tienen usuario, usuarios, WhatsApp fallidos
                                       en 7 días y citas de las altas desde el encendido (garantía D-30).
  · DNS público (dig)               → SPF, DMARC y DKIM (selectores habituales) del dominio de la web.
  · Capa de E1 (data/clientes/*.json) y E0 (data/asignaciones.json, personas.json) → web, emparejamientos, account,
                                       reuniones (primera reunión de resultados) y talleres (GHL de RO, panel 1-oct).

Uso:
  python3 generar_nuevos.py               # 0 llamadas: usa lo último guardado en fuentes_nuevos/_crudo/
  python3 generar_nuevos.py --en-vivo     # lee todo otra vez (Sign, ClickUp, Meta, GHL y DNS)
  python3 generar_nuevos.py --en-vivo sign,clickup   # solo esas fuentes

Nunca guarda correos, teléfonos, claves ni datos de leads (solo recuentos). Escribe a temporal y renombra.
"""
import datetime as dt
import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from zoneinfo import ZoneInfo

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
DATA = APP / 'data'
CRUDO = AQUI / '_privado' / '_crudo'   # sobres de Sign y tareas en bruto: fuera del escáner y de la subida
SALIDA = DATA / 'nuevos' / 'nuevos.json'
sys.path.insert(1, str(Path(__file__).resolve().parents[1]))  # C5: rutas y secretos en config.py
import config  # noqa: E402
PANEL = config.PANEL_OPERACIONES
HERR = config.HERRAMIENTAS
MAD = ZoneInfo('Europe/Madrid')
AHORA = dt.datetime.now(MAD)
HOY = AHORA.date()
CRUDO.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------------------------------- reglas firmadas
ENCENDIDO_OBJETIVO, ENCENDIDO_LIMITE = 10, 12          # D-28 · desde el alta del contrato
VENTANA = 90                                           # de la firma al día 90
BLOQUEO_ESCALAR_DIAS = 5                               # punto 6 de Mili
SIN_TAREAS_HORAS = 48                                  # punto 6 de Mili
GARANTIA_DIAS, GARANTIA_REUNIONES = 30, 2              # D-30
DUENO_TECNICO = 'agustina'                             # Agus, técnico de altas (D-48: dueño hasta el día 90)
VIGILANTE = 'mili'                                     # regla del 9-sep: cada hito con un vigilante distinto

# Sobre de Sign → cliente de la app. Los que no están aquí no son altas del Motor (se listan en «fuera»).
SIGN_A_APP = {
    'MarlexConsulting': 'marlex-consulting', 'ConficonsultingAsesores': 'conficonsulting', 'TSTConsulting': 'tst-consulting',
    'ImpulsaCFO': 'impulsa-cfo', 'Imfor': 'imfor-asesores', 'Geslabor': 'geslabor', 'Billeo': 'billeo', 'AGC': 'agc',
    'Abner': 'abner-advisory', 'CIBPartners': 'cib-partners', 'GestioPlural': 'gestio-plural', 'LoboSmart': 'lobo',
    'Deudout': 'deudot', 'MartinezYJacal': 'emex', 'Garmande': 'garmande', 'Legal4U': 'laver', 'ThinkValueFinance': 'think-value',
}
# Sobres enviados y sin firmar: contratos que vienen (no son clientes hasta firmar).
PREVISTAS = {'AseconConsultingEmpresarial': 'Asecon', 'TaxAdviseLtd': 'Tax & Advise', 'Asefilco': 'Asefilco'}
# Ya no son altas en curso aunque sigan en el sobre: sobre antiguo sustituido por otro firmado.
SUSTITUIDOS = {'Acuerdo_MCR_Marlex'}
# Acuerdos de Sign que no son del Motor (no tienen encendido de campaña): fuera del módulo, con su porqué.
FUERA = [
    {'nombre': 'Optimalia', 'porque': 'Proyecto one-shot (mandato SEPA del 20-jul, alta 3-sep): no tiene campaña que encender.'},
    {'nombre': 'PG Business Audit (PGB)', 'porque': 'Acuerdo de colaboración del 13-jul sin fecha de inicio ni campaña de Meta (outreach por LinkedIn).'},
]

# Cuenta de Meta de cada alta (identificador, nunca por parecido de nombre). Solo las que RO ve hoy.
META_CUENTA = {
    'garmande': 'act_958596937287965', 'laver': 'act_1591667929090671', 'emex': 'act_125546504832976',
    'deudot': 'act_105489791447612', 'lobo': 'act_2145647453026345',
}
MOTIVO_META = {1: 'activa', 2: 'desactivada por Meta', 3: 'pago pendiente', 7: 'en revisión de riesgo', 8: 'pago pendiente de liquidar',
               9: 'en periodo de gracia', 100: 'pendiente de cierre', 101: 'cerrada', 201: 'cualquier activa', 202: 'cualquier cerrada'}

# Hitos de la firma al día 90 (orden, quién lo hace y día objetivo desde el alta del contrato).
HITOS = [
    ('firma', 'Firma', 'Ventas (Tomás)', None),
    ('accesos', 'Accesos', 'Agus', 3),
    ('arranque', 'Taller y arranque', 'Tomás y Coti', 2),
    ('encendido', 'Encendido', 'Trafficker y Agus', ENCENDIDO_OBJETIVO),
    ('primer_lead', 'Primer lead', 'Trafficker', ENCENDIDO_OBJETIVO + 3),
    ('reunion_resultados', 'Primera reunión de resultados', 'Account', 30),
    ('garantia', 'Día 30 · garantía', 'Coti', 30),
    ('dia90', 'Día 90', 'Account', 90),
]

# Propuesta D+N de la plantilla «Onboarding — [PLANTILLA]» (1200220000003981). Se aplicará cuando haya escritura (W7).
# Orden de las reglas: la primera que casa manda. ⚠️ Propuesta para validar con Agus y Coti.
PLANTILLA_DN = [
    (r'alta de cliente', 0, 'Alta y espacios'),
    (r'web de onboarding', 1, 'Alta y espacios'),
    (r'taller de oferta', 2, 'Taller'),
    (r'accesos (meta|crm)', 3, 'Accesos'),
    (r'listar lo que falta', 3, 'Accesos'),
    (r'configuraciones b[aá]sicas', 4, 'Accesos'),
    (r'verificar 0[12]_|lanzamiento-ro', 5, 'Oferta y ángulos'),
    (r'set-?up crm|copys crm|flujos ghl', 6, 'CRM'),
    (r'landing|revisar creativos|modificaci[oó]n de creativos|03_propuesta', 7, 'Landing y creativos'),
    (r'borrador|form nativo|end-?to-?end|utms', 8, 'Prueba de punta a punta'),
    (r'tareas onboarding', 9, 'Prueba de punta a punta'),
    (r'lanzamiento|panel paid|set-?up ads', ENCENDIDO_OBJETIVO, 'Encendido'),
    (r'rrss', 14, 'Redes'),
    (r'gsc|ga4|windsor|conversi[oó]n documentada|medici[oó]n|looker|cuadre', 21, 'Medición'),
    (r'estado inicial|saneado', 30, 'Web'),
    (r'gmb|nap|rese[ñn]as|productos y servicios|kws', 45, 'Ficha de Google'),
    (r'seo|keywords|quick wins', 60, 'SEO'),
]
HECHO = {'completado', 'cerrado', 'campaña en curso', 'complete', 'closed'}
ACTIVOS_SEMANA = {'planning semanal', 'diario', 'en curso'}


RX_CORREO = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
RX_TEL = re.compile(r"(?<![\w.\-/])(?:\+34[\s.-]?|0034[\s.-]?)?[6789]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}(?![\w.\-/])")


def limpio(t):
    """Quita correos y teléfonos de un texto libre (nombres de tareas, asuntos): la app nunca los enseña."""
    return RX_TEL.sub('[teléfono]', RX_CORREO.sub('[correo]', t or '')) if isinstance(t, str) else t


def leads_de(actions):
    """Misma regla que Captación (captacion.py → leads_de): «lead» ya incluye formularios y píxel; si no está,
    lead_grouped + fb_pixel_lead. Nunca se suman los dos (eso contaba cada lead dos veces)."""
    a = {x['action_type']: float(x['value']) for x in (actions or [])}
    if 'lead' in a:
        return a['lead']
    return a.get('onsite_conversion.lead_grouped', 0) + a.get('offsite_conversion.fb_pixel_lead', 0)


MESES_CORTOS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sept', 'oct', 'nov', 'dic']


def fecha_es(iso):
    """2026-09-28 → «28 sept» (fechas en pantalla, nunca ISO)."""
    if not iso:
        return 'sin fecha'
    d = dt.date.fromisoformat(str(iso)[:10])
    return f'{d.day} {MESES_CORTOS[d.month - 1]}'


def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def lee(ruta, defecto=None):
    try:
        return json.loads(Path(ruta).read_text())
    except Exception:
        return defecto


def escribe(ruta, datos):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix('.tmp')
    tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=1))
    os.replace(tmp, ruta)


def herramienta(carpeta, modulo):
    sys.path.insert(0, str(HERR / carpeta))
    argv = sys.argv
    sys.argv = ['x']
    try:
        return __import__(modulo)
    finally:
        sys.argv = argv


def fecha(x):
    return dt.date.fromisoformat(str(x)[:10]) if x else None


def ms_a_fecha(v):
    return dt.datetime.fromtimestamp(int(v) / 1000, MAD) if v else None


def hora_crudo(nombre):
    p = CRUDO / f'{nombre}.json'
    return dt.datetime.fromtimestamp(p.stat().st_mtime, MAD).strftime('%Y-%m-%d %H:%M') if p.exists() else None


# ================================================================================================ 1 · Zoho Sign
MESES = {m: i for i, m in enumerate(['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'], 1)}


def clave_sobre(nombre):
    m = re.search(r'(?:ACUERDO_MCR_|ACUERDO MOTOR |Acuerdo_MCR_)([A-Za-z0-9]+)', nombre or '')
    return m.group(1) if m else None


def leer_sign():
    import io, zipfile, urllib.parse, urllib.request
    zh = herramienta('zoho', 'zh')
    tk, _ = zh.acceso()
    r = zh.get(tk, 'https://sign.zoho.eu/api/v1/requests?data=' + urllib.parse.quote(json.dumps(
        {'page_context': {'row_count': 60, 'start_index': 1, 'sort_column': 'created_time', 'sort_order': 'DESC'}})))
    if '_error' in r:
        raise RuntimeError(f"Sign responde {r['_error']}")
    previo = {x['request_id']: x for x in (lee(CRUDO / 'sign.json', {}) or {}).get('sobres', [])}
    base = {x['request_id']: x for x in lee(PANEL / '_crudo/nuevos/altas_contrato.json', [])}
    sobres = []
    for q in r.get('requests', []):
        nombre = q.get('request_name') or ''
        clave = clave_sobre(nombre)
        if not clave:
            continue
        rid = str(q.get('request_id'))
        s = {'request_id': rid, 'documento': nombre, 'clave': clave, 'estado': q.get('request_status'),
             'enviado': ms_a_fecha(q.get('sign_submitted_time')).strftime('%Y-%m-%d %H:%M') if q.get('sign_submitted_time') else None,
             'firma': ms_a_fecha(q.get('action_time')).strftime('%Y-%m-%d %H:%M') if q.get('request_status') == 'completed' else None}
        if rid in base and base[rid].get('fecha_alta'):
            s['alta'] = base[rid]['fecha_alta']
            s['alta_prueba'] = base[rid].get('cita_literal') or 'altas_contrato.json (panel 1-oct)'
        p = previo.get(rid, {})
        for k in ('alta', 'alta_prueba', 'encargo_art28', 'garantia', 'garantia_literal'):
            if k in p and k not in s:
                s[k] = p[k]
        # Lo que falta (alta del contrato, encargo y garantía) sale del propio PDF (una lectura por sobre, se guarda).
        if (clave in SIGN_A_APP or clave in PREVISTAS) and ('encargo_art28' not in s or not s.get('alta')):
            try:
                req = urllib.request.Request(f'https://sign.zoho.eu/api/v1/requests/{rid}/pdf', headers={'Authorization': 'Zoho-oauthtoken ' + tk})
                cuerpo = urllib.request.urlopen(req, timeout=90).read()
                textos = []
                import pypdf
                if cuerpo[:2] == b'PK':
                    z = zipfile.ZipFile(io.BytesIO(cuerpo))
                    for n in z.namelist():
                        if n.lower().endswith('.pdf') and 'sepa' not in n.lower():
                            textos.append('\n'.join(pg.extract_text() or '' for pg in pypdf.PdfReader(io.BytesIO(z.read(n))).pages))
                else:
                    textos.append('\n'.join(pg.extract_text() or '' for pg in pypdf.PdfReader(io.BytesIO(cuerpo)).pages))
                t = re.sub(r'\s+', ' ', ' '.join(textos))
                m = re.search(r'(?:comienzan|dan inicio|empiezan)[^.]{0,30}?el (\d{1,2}) de (\w+)(?: de (\d{4}))?', t, re.I)
                if m and not s.get('alta'):
                    anyo = int(m.group(3) or (s['firma'] or s['enviado'])[:4])
                    s['alta'] = dt.date(anyo, MESES[m.group(2).lower()], int(m.group(1))).isoformat()
                    s['alta_prueba'] = m.group(0)[:160]
                s['encargo_art28'] = bool(re.search(r'encargo de tratamiento \(art\. ?28', t, re.I))
                # Garantía de reuniones (D-30): solo la cláusula expresa («garantiza que, en los 30 días… dos reuniones»).
                g = re.search(r'garantiza que,? en los \d+ d[ií]as[^.]{0,220}\.', t, re.I)
                s['garantia'] = bool(g)
                s['garantia_literal'] = g.group(0).strip()[:240] if g else None
            except Exception as e:  # el PDF no es imprescindible: queda «sin dato»
                s.setdefault('encargo_art28', None)
                s['pdf_error'] = str(e)[:120]
        sobres.append(s)
    escribe(CRUDO / 'sign.json', {'hora': AHORA.strftime('%Y-%m-%d %H:%M'), 'sobres': sobres})


# ================================================================================================ 2 · ClickUp
def leer_clickup():
    cu = herramienta('clickup_api', 'cu')
    _, _, listas = cu.jerarquia()
    onb = {lid: v for lid, v in listas.items() if v['lista'].lower().startswith('onboarding') and 'plantilla' not in v['lista'].lower()
           and 'pasante' not in v['lista'].lower() and 'prueba' not in v['lista'].lower() and '[cliente]' not in v['lista'].lower()}
    salida = {'hora': AHORA.strftime('%Y-%m-%d %H:%M'), 'listas': [], 'carpetas': sorted({v['carpeta'] for v in listas.values() if v.get('carpeta')})}
    for lid, v in onb.items():
        tareas = cu.tareas_lista(lid)
        bloqueadas = [t['id'] for t in tareas if (t.get('status') or {}).get('status', '').lower() == 'bloqueado']
        tiempo = cu.tiempo_en_estado(bloqueadas) if bloqueadas else {}
        filas = []
        for t in tareas:
            est = (t.get('status') or {}).get('status', '').lower()
            fila = {'id': t['id'], 'nombre': t['name'].strip(), 'estado': est,
                    'asignados': [a.get('username') for a in t.get('assignees') or []],
                    'etiquetas': [x['name'] for x in t.get('tags') or []],
                    'limite': ms_a_fecha(t.get('due_date')).date().isoformat() if t.get('due_date') else None,
                    'actualizada': ms_a_fecha(t.get('date_updated')).strftime('%Y-%m-%d %H:%M') if t.get('date_updated') else None,
                    'hecha_el': (ms_a_fecha(t.get('date_done') or t.get('date_closed')).date().isoformat() if (t.get('date_done') or t.get('date_closed')) else None),
                    'creada': ms_a_fecha(t.get('date_created')).date().isoformat() if t.get('date_created') else None,
                    'padre': t.get('parent'), 'url': t.get('url')}
            if t['id'] in tiempo:
                cur = (tiempo[t['id']] or {}).get('current_status') or {}
                minutos = (cur.get('total_time') or {}).get('by_minute')
                fila['dias_bloqueada'] = round(minutos / 1440, 1) if minutos else None
            filas.append(fila)
        salida['listas'].append({'list_id': lid, 'lista': v['lista'].strip(), 'carpeta': v.get('carpeta'), 'tareas': filas})
    escribe(CRUDO / 'clickup.json', salida)


# ================================================================================================ 3 · Meta
def leer_meta(altas):
    mt = herramienta('meta', 'mt')
    tk = mt.llave('meta_token')
    cuentas = {c['id']: c for c in mt.cuentas(tk)}
    salida = {'hora': AHORA.strftime('%Y-%m-%d %H:%M'), 'cuentas_visibles': len(cuentas), 'por_cliente': {}}
    for a in altas:
        cid = a['cliente_id']
        act = META_CUENTA.get(cid)
        if not act:
            continue
        c = cuentas.get(act) or mt.get(f'/{act}', access_token=tk, fields='name,account_status,disable_reason,amount_spent')
        info = mt.get(f'/{act}', access_token=tk, fields='name,account_status,disable_reason,funding_source_details')
        desde = (fecha(a['firma']) - dt.timedelta(days=7)).isoformat()
        ins = mt.get(f'/{act}/insights', access_token=tk, fields='spend,actions', time_increment=1,
                     time_range=json.dumps({'since': desde, 'until': HOY.isoformat()}), limit=200)
        serie = []
        for d in ins.get('data', []):
            leads = leads_de(d.get('actions'))
            serie.append({'d': d['date_start'], 'gasto': round(float(d.get('spend') or 0), 2), 'leads': int(leads)})
        px = mt.get(f'/{act}/adspixels', access_token=tk, fields='name,last_fired_time,is_unavailable')
        salida['por_cliente'][cid] = {
            'cuenta': act, 'nombre': info.get('name') or c.get('name'), 'estado_num': info.get('account_status'),
            'motivo_bloqueo': info.get('disable_reason'), 'con_pago': bool(info.get('funding_source_details')),
            'serie': serie,
            'pixeles': [{'nombre': p.get('name'), 'ultimo_evento': (p.get('last_fired_time') or '')[:16].replace('T', ' ') or None,
                         'no_disponible': p.get('is_unavailable')} for p in px.get('data', [])],
        }
    escribe(CRUDO / 'meta.json', salida)


# ================================================================================================ 4 · GHL (66 subcuentas)
def leer_ghl(altas, ghl_de_cliente):
    app = herramienta('ghl_agencia', 'app')
    tk, est = app.acceso()                       # rota el refresh token y lo guarda (como app.py)
    co = est['companyId']
    subs = app.subcuentas(tk, co)
    inicio = int(dt.datetime.combine(HOY - dt.timedelta(days=7), dt.time(0), MAD).timestamp() * 1000)   # 7 días naturales cerrados
    salida = {'hora': AHORA.strftime('%Y-%m-%d %H:%M'), 'subcuentas': []}
    altas_por_loc = {ghl_de_cliente.get(a['cliente_id']): a for a in altas if ghl_de_cliente.get(a['cliente_id'])}
    for s in subs:
        loc = s['id']
        fila = {'loc': loc, 'nombre': (s.get('name') or '').strip(), 'creada': (s.get('dateAdded') or '')[:10] or None}
        try:
            lt = app.token_sub(tk, co, loc)
        except SystemExit as e:
            fila['error'] = str(e)[:120]
            salida['subcuentas'].append(fila)
            continue
        cal = app.get(lt, '/calendars/', locationId=loc)
        cals = cal.get('calendars', []) if '_error' not in cal else None
        us = app.get(lt, '/users/', locationId=loc)
        usuarios = [u for u in us.get('users', []) if not u.get('deleted')] if '_error' not in us else None
        fila['calendarios'] = len(cals) if cals is not None else None
        fila['calendarios_activos'] = len([c for c in cals or [] if c.get('isActive', True)])
        fila['calendarios_sin_usuario'] = [c.get('name') for c in cals or [] if c.get('isActive', True) and not [m for m in c.get('teamMembers') or [] if m.get('userId')] and c.get('calendarType') not in ('event',)]
        fila['usuarios'] = len(usuarios) if usuarios is not None else None
        # WhatsApp: mensajes salientes de los últimos 7 días en las conversaciones con WhatsApp más recientes.
        enviados = fallidos = 0
        conv = app.get(lt, '/conversations/search', locationId=loc, limit=40, sort='desc', sortBy='last_message_date')
        cs = [c for c in conv.get('conversations', []) if (c.get('lastMessageDate') or 0) >= inicio] if '_error' not in conv else []
        wa = [c for c in cs if c.get('lastMessageType') == 'TYPE_WHATSAPP' or 19 in (c.get('messageTypes') or [])][:12]
        for c in wa:
            m = app.get(lt, f"/conversations/{c['id']}/messages", limit=30)
            for x in (m.get('messages') or {}).get('messages', []) if '_error' not in m else []:
                if x.get('messageType') != 'TYPE_WHATSAPP' or x.get('direction') != 'outbound':
                    continue
                cuando = x.get('dateAdded') or ''
                if cuando:
                    dia_l = dt.datetime.fromisoformat(cuando.replace('Z', '+00:00')).astimezone(MAD).date()
                    if not (HOY - dt.timedelta(days=7) <= dia_l < HOY):
                        continue
                enviados += 1
                fallidos += 1 if (x.get('status') or '').lower() in ('failed', 'undelivered') else 0
        fila['wa_conversaciones_7d'] = len(wa)
        fila['wa_enviados_7d'] = enviados
        fila['wa_fallidos_7d'] = fallidos
        # Citas del despacho desde el encendido (solo las altas): para la garantía (D-30).
        a = altas_por_loc.get(loc)
        if a and cals:
            desde = int(dt.datetime.combine(fecha(a['alta']), dt.time(0), MAD).timestamp() * 1000)
            hasta = int((AHORA + dt.timedelta(days=45)).timestamp() * 1000)
            citas = []
            for c in cals:
                ev = app.get(lt, '/calendars/events', locationId=loc, calendarId=c['id'], startTime=desde, endTime=hasta)
                for e in ev.get('events', []) if '_error' not in ev else []:
                    citas.append({'inicio': (e.get('startTime') or '')[:16], 'estado': e.get('appointmentStatus') or e.get('appoinmentStatus'),
                                  'calendario': c.get('name')})
            fila['citas_desde_alta'] = sorted(citas, key=lambda x: x['inicio'])
        salida['subcuentas'].append(fila)
    escribe(CRUDO / 'ghl.json', salida)


# ================================================================================================ 5 · DNS público
SELECTORES = ['google', 'selector1', 'selector2', 'default', 'k1', 's1', 's2', 'mail', 'zoho', 'zmail', 'dkim', 'smtp', 'ionos', 'hostinger', 'resend', 'mailjet', 'mxvault']


def dig(nombre, tipo='TXT'):
    try:
        r = subprocess.run(['dig', '+short', '+time=3', '+tries=1', tipo, nombre], capture_output=True, text=True, timeout=8)
        return [l.strip().strip('"') for l in r.stdout.splitlines() if l.strip()]
    except Exception:
        return None


def leer_dns(altas):
    salida = {'hora': AHORA.strftime('%Y-%m-%d %H:%M'), 'dominios': {}}
    for a in altas:
        d = a.get('dominio')
        if not d or d in salida['dominios']:
            continue
        txt = dig(d) or []
        spf = [t for t in txt if t.lower().startswith('v=spf1')]
        dm = [t for t in (dig('_dmarc.' + d) or []) if 'v=dmarc1' in t.lower()]
        dk = None
        for sel in SELECTORES:
            r = dig(f'{sel}._domainkey.{d}')
            if r and any('p=' in x.lower() or 'dkim' in x.lower() or x.endswith('.') for x in r):
                dk = sel
                break
        politica = re.search(r'p=(\w+)', dm[0], re.I).group(1).lower() if dm and re.search(r'p=(\w+)', dm[0], re.I) else None
        salida['dominios'][d] = {'spf': spf[0][:160] if spf else None, 'spf_varios': len(spf) > 1, 'dmarc': politica, 'dkim_selector': dk,
                                 'mx': bool(dig(d, 'MX'))}
    escribe(CRUDO / 'dns.json', salida)



# ================================================================================================ estado del equipo de arranque
MANUAL = AQUI / 'estado_altas_manual_2026-10-02.json'
AUTOR_MANUAL = 'equipo de arranque (Coti, Valeria y Agus)'
TXT_TALLER = {'hecho': 'hecho', 'agendado': 'agendado', 'segunda_sesion': '2.ª sesión', 'sin_agendar': 'sin agendar', 'pendiente': 'sin agendar'}
TXT_CONFIG = {'hecho': 'hecha', 'agendada': 'agendada', 'sin_agendar': 'sin agendar', 'pendiente': 'sin agendar'}


def estado_equipo():
    """Estado declarado por el equipo de arranque, por alta. Base: la tabla del 2-oct (fichero manual).
    Encima, lo último que se haya guardado desde la app (acciones «estado_alta» de local.db, modo simulación):
    así la próxima vez no hace falta pegar una tabla."""
    m = lee(MANUAL, {}) or {}
    fecha_m = (m.get('_meta') or {}).get('fecha')
    out = {}
    for x in m.get('altas', []):
        out[x['cliente']] = {**x, 'actualizado': fecha_m, 'autor': AUTOR_MANUAL, 'origen': 'tabla del equipo pegada por Tomás'}
    manual = {k: dict(v) for k, v in out.items()}
    try:
        import sqlite3
        con = sqlite3.connect(f'file:{APP / "local.db"}?mode=ro', uri=True)
        filas = con.execute("SELECT creada, quien, cliente_id, vista_previa FROM acciones WHERE modulo='clientes-nuevos' AND tipo='estado_alta' ORDER BY id").fetchall()
        con.close()
        alias = {k: (v.get('alias') or v.get('nombre')) for k, v in personas().items()}
        for creada, quien, cid, vp in filas:
            try:
                v = json.loads(vp or '{}')
            except Exception:
                continue
            base = out.get(cid, {'cliente': cid})
            claves = ('taller', 'config_basicas', 'estado', 'proximo_paso')
            igual = lambda r: all(v.get(k) == r.get(k) for k in claves) and bool(v.get('urgente')) == bool(r.get('urgente'))
            if cid in manual and igual(manual[cid]):
                out[cid] = dict(manual[cid])   # vuelve al texto de la tabla: autor y fecha, los de la tabla
                continue
            if igual(base):
                continue   # guardado sin cambios: el autor y la fecha siguen siendo los del texto vigente
            out[cid] = {**base, **{k: v[k] for k in ('taller', 'config_basicas', 'estado', 'proximo_paso', 'urgente') if k in v},
                        'actualizado': (dt.datetime.fromisoformat(creada).replace(tzinfo=dt.timezone.utc).astimezone(MAD).strftime('%Y-%m-%d %H:%M') if creada else None), 'autor': alias.get(quien, quien), 'origen': 'formulario de la app (simulación)'}
    except Exception:
        pass
    return out


def fecha_corta(f):
    return f[:16].replace('T', ' ') if f else None

# ================================================================================================ montar
def personas():
    p = lee(DATA / 'personas.json', [])
    p = p if isinstance(p, list) else p.get('personas', [])
    return {x['id']: x for x in p}


def asignaciones():
    a = lee(DATA / 'asignaciones.json', [])
    return a if isinstance(a, list) else a.get('asignaciones', [])


def silla(asig, pers, cid, s):
    filas = [x for x in asig if x['cliente_id'] == cid and x['silla'] == s and not x.get('hasta') and not x.get('suplencia')]
    filas.sort(key=lambda x: (not x.get('principal', True), x.get('confianza') != 'confirmada'))
    return [{'id': x['persona_id'], 'nombre': (pers.get(x['persona_id']) or {}).get('alias') or (pers.get(x['persona_id']) or {}).get('nombre') or x['persona_id']} for x in filas]


def dia_objetivo(nombre):
    n = nombre.lower()
    for patron, dn, fase in PLANTILLA_DN:
        if re.search(patron, n):
            return dn, fase
    return None, 'Otras'


def lunes(d):
    return d - dt.timedelta(days=d.weekday())


def montar():
    sign = lee(CRUDO / 'sign.json', {}) or {}
    cu = lee(CRUDO / 'clickup.json', {}) or {}
    meta = lee(CRUDO / 'meta.json', {}) or {}
    ghl = lee(CRUDO / 'ghl.json', {}) or {}
    dns = lee(CRUDO / 'dns.json', {}) or {}
    pers, asig = personas(), asignaciones()
    panel = {norm(n['nombre']).split(' ')[0]: n for n in (lee(PANEL / 'build/datos.json', {}) or {}).get('nuevos', [])}
    eventos_ro = lee(PANEL / '_crudo/nuevos/ghl_eventos_ro_jun_nov.json', []) or []

    # cliente → subcuenta de GHL (por identificador de la capa E1)
    ghl_de, nombre_de = {}, {}
    for f in (DATA / 'clientes').glob('*.json'):
        c = lee(f, {})
        nombre_de[c.get('id')] = c.get('nombre')
        emp = (((c.get('fuentes') or {}).get('ghl') or {}).get('emparejado') or {})
        if emp.get('id'):
            ghl_de[c['id']] = emp['id']
    loc_a_cliente = {v: k for k, v in ghl_de.items()}

    # ---- altas en la ventana
    altas, previstas = [], []
    vistos = set()
    for s in sign.get('sobres', []):
        if s['documento'] in SUSTITUIDOS or any(s['documento'].startswith(x) for x in SUSTITUIDOS):
            continue
        if s['clave'] in PREVISTAS and s['estado'] != 'completed':
            previstas.append({'cliente_id': 'prevista-' + norm(PREVISTAS[s['clave']]).replace(' ', '-'), 'nombre': PREVISTAS[s['clave']],
                              'enviado': s.get('enviado'), 'alta_prevista': s.get('alta'), 'alta_prueba': s.get('alta_prueba'),
                              'estado_sign': 'enviado, sin firmar', 'documento': s['documento']})
            continue
        cid = SIGN_A_APP.get(s['clave'])
        if not cid or s['estado'] != 'completed' or cid in vistos:
            continue
        alta = fecha(s.get('alta')) or fecha(s.get('firma'))
        if not alta or (HOY - alta).days > VENTANA:
            continue
        vistos.add(cid)
        c = lee(DATA / 'clientes' / f'{cid}.json', {}) or {}
        web = c.get('web')
        dominio = re.sub(r'^https?://(www\.)?', '', web or '').strip('/').split('/')[0] or None
        altas.append({'cliente_id': cid, 'nombre': c.get('nombre') or nombre_de.get(cid) or cid, 'firma': s['firma'], 'alta': alta.isoformat(),
                      'alta_prueba': s.get('alta_prueba'), 'documento': s['documento'], 'sign_id': s['request_id'],
                      'encargo_art28': s.get('encargo_art28'), 'garantia_firmada': s.get('garantia'), 'garantia_literal': s.get('garantia_literal'),
                      'web': web, 'dominio': dominio, '_c': c})
    return altas, previstas, sign, cu, meta, ghl, dns, pers, asig, panel, eventos_ro, ghl_de, loc_a_cliente, nombre_de


def construir():
    altas, previstas, sign, cu, meta, ghl, dns, pers, asig, panel, eventos_ro, ghl_de, loc_a_cliente, nombre_de = montar()
    listas = {}
    for l in cu.get('listas', []):
        nl = norm(l['lista'] + ' ' + (l.get('carpeta') or ''))
        listas[l['list_id']] = (nl, l)
    claves_lista = {'garmande': 'garmande', 'laver': 'laver', 'emex': 'emex', 'deudot': 'deudout', 'lobo': 'lobo', 'gestio-plural': 'gestio plural',
                    'cib-partners': 'cib partners', 'abner-advisory': 'abner', 'agc': 'agc', 'geslabor': 'geslabor'}
    subs = {s['loc']: s for s in ghl.get('subcuentas', [])}
    hoy = HOY
    equipo_todo = estado_equipo()
    # Una sola verdad por cliente (E0 ronda 5): el account sale de ahí, nunca de la Cartera ni del CRM.
    verdad = {c['cliente_id']: c for c in (lee(DATA / 'verdad/clientes.json', {}) or {}).get('clientes', [])}
    carpetas_cu = {norm(c) for c in cu.get('carpetas', [])}
    filas = []
    for a in altas:
        cid, c = a['cliente_id'], a.pop('_c')
        alta = fecha(a['alta'])
        firma_dt = dt.datetime.strptime(a['firma'], '%Y-%m-%d %H:%M').replace(tzinfo=MAD) if a.get('firma') else None
        dia = (hoy - alta).days
        cuenta = silla(asig, pers, cid, 'account')
        vd = verdad.get(cid)
        if vd is not None:
            acc_id = vd.get('account')
            cuenta = [{'id': acc_id, 'nombre': (pers.get(acc_id) or {}).get('alias') or acc_id}] if acc_id else []
        sin_account = re.sub(r'\s*\([A-Z]\d+\)', '', (vd or {}).get('sin_account') or '') or (None if cuenta else 'sin account')
        traff = silla(asig, pers, cid, 'trafficker')
        crm = silla(asig, pers, cid, 'crm')
        # ---------------- ClickUp
        lista = None
        k = claves_lista.get(cid, norm(a['nombre']).split(' ')[0])
        for lid, (nl, l) in listas.items():
            if k in nl:
                lista = l
                break
        tareas, alertas = [], []
        if lista:
            for t in lista['tareas']:
                if t.get('padre') is None and re.search(r'^tareas onboarding', t['nombre'], re.I):
                    pass
                dn, fase = dia_objetivo(t['nombre'])
                hecha = t['estado'] in HECHO
                limite = fecha(t.get('limite'))
                propuesta = (alta + dt.timedelta(days=dn)).isoformat() if dn is not None else None
                semana_ref = limite or (fecha(propuesta) if propuesta else None)
                act = dt.datetime.strptime(t['actualizada'], '%Y-%m-%d %H:%M').date() if t.get('actualizada') else None
                fila = {'id': t['id'], 'nombre': limpio(t['nombre']), 'estado': t['estado'], 'hecha': hecha, 'asignados': t['asignados'],
                        'limite': t.get('limite'), 'propuesta': propuesta, 'dia_objetivo': dn, 'fase': fase,
                        'semana': (lunes(semana_ref) - lunes(alta)).days // 7 if semana_ref else None,
                        'actualizada': t.get('actualizada'), 'url': t.get('url'), 'alertas': []}
                if not hecha and limite and limite < hoy:
                    fila['alertas'].append('vencida')
                if not hecha and t['estado'] in ACTIVOS_SEMANA and act and (hoy - act).days > 7:
                    fila['alertas'].append('no_avanza')
                if not hecha and limite and lunes(limite) < lunes(hoy) and act and act < lunes(limite) + dt.timedelta(days=7):
                    if 'no_avanza' not in fila['alertas']:
                        fila['alertas'].append('no_avanza')
                if t['estado'] == 'bloqueado':
                    fila['dias_bloqueada'] = t.get('dias_bloqueada')
                    if (t.get('dias_bloqueada') or 0) > BLOQUEO_ESCALAR_DIAS:
                        fila['alertas'].append('bloqueo_5d')
                tareas.append(fila)
        hechas = [t for t in tareas if t['hecha']]
        pct = round(len(hechas) / len(tareas) * 100, 1) if tareas else None
        vencidas = [t for t in tareas if 'vencida' in t['alertas']]
        bloqueadas = [t for t in tareas if t['estado'] == 'bloqueado']
        sin_plazo = [t for t in tareas if not t['hecha'] and not t['limite']]
        no_avanza = [t for t in tareas if 'no_avanza' in t['alertas']]
        bloq5 = [t for t in tareas if 'bloqueo_5d' in t['alertas']]
        horas_firma = round((AHORA - firma_dt).total_seconds() / 3600, 1) if firma_dt else None
        if not tareas:
            if horas_firma is not None and horas_firma > SIN_TAREAS_HORAS:
                alertas.append({'tipo': 'sin_tareas', 'estado': 'rojo', 'texto': (f'Sin lista de arranque en ClickUp a los {round(horas_firma / 24)} días de la firma (límite {SIN_TAREAS_HORAS} h).' if horas_firma > 48 else f'Sin lista de arranque en ClickUp a las {int(horas_firma)} h de la firma (límite {SIN_TAREAS_HORAS} h).')})
            else:
                faltan = SIN_TAREAS_HORAS - (horas_firma or 0)
                alertas.append({'tipo': 'sin_tareas', 'estado': 'ambar', 'texto': f'Todavía sin lista de arranque; el plazo de {SIN_TAREAS_HORAS} h vence en {int(faltan)} h.'})
        for t in vencidas:
            alertas.append({'tipo': 'vencida', 'estado': 'rojo', 'texto': f'«{t["nombre"]}» venció el {fecha_es(t["limite"])}.', 'tarea': t['id'], 'url': t['url']})
        for t in no_avanza:
            alertas.append({'tipo': 'no_avanza', 'estado': 'ambar', 'texto': f'«{t["nombre"]}» ({t["estado"]}) sin moverse desde el {fecha_es(t["actualizada"])}.', 'tarea': t['id'], 'url': t['url']})
        for t in bloq5:
            alertas.append({'tipo': 'bloqueo_5d', 'estado': 'rojo', 'texto': f'«{t["nombre"]}» lleva {t.get("dias_bloqueada")} días bloqueada sin escalar.', 'tarea': t['id'], 'url': t['url']})

        # ---------------- Meta
        m = (meta.get('por_cliente') or {}).get(cid)
        encendido = primer_lead = None
        gasto_desde_alta = leads_desde_alta = None
        meta_out = None
        if m:
            serie = m.get('serie') or []
            # Encendido = primer día con gasto ≥ 5 € seguido de otros 2 días con gasto (un céntimo suelto no es encender).
            desde_f = (fecha(a['firma'][:10]) - dt.timedelta(days=7)).isoformat()
            por_dia = {x['d']: x['gasto'] for x in serie}
            encendido = None
            for x in serie:
                if x['d'] < desde_f or x['gasto'] < 5:
                    continue
                d1, d2 = (fecha(x['d']) + dt.timedelta(days=1)).isoformat(), (fecha(x['d']) + dt.timedelta(days=2)).isoformat()
                if por_dia.get(d1, 0) > 0 and (por_dia.get(d2, 0) > 0 or d2 >= HOY.isoformat()):
                    encendido = x['d']
                    break
            if encendido:
                lead = [x for x in serie if x['leads'] > 0 and x['d'] >= encendido]
                primer_lead = lead[0]['d'] if lead else None
            gasto_desde_alta = round(sum(x['gasto'] for x in serie if x['d'] >= a['alta']), 2)
            leads_desde_alta = sum(x['leads'] for x in serie if x['d'] >= a['alta'])
            ultimo = max((x['d'] for x in serie if x['gasto'] > 0), default=None)
            px = m.get('pixeles') or []
            meta_out = {'cuenta': m['cuenta'], 'nombre': m.get('nombre'), 'estado': MOTIVO_META.get(m.get('estado_num'), f"estado {m.get('estado_num')}"),
                        'estado_num': m.get('estado_num'), 'motivo_bloqueo': m.get('motivo_bloqueo'), 'con_pago': m.get('con_pago'),
                        'ultimo_dia_con_gasto': ultimo, 'gasto_desde_alta': gasto_desde_alta, 'leads_desde_alta': leads_desde_alta,
                        'pixel': ({'nombre': px[0]['nombre'], 'ultimo_evento': px[0]['ultimo_evento']} if px else None),
                        'serie_gasto': [{'d': x['d'], 'gasto': x['gasto'], 'leads': x['leads']} for x in serie if x['d'] >= a['alta']],
                        'prueba': f"https://adsmanager.facebook.com/adsmanager/manage/campaigns?act={m['cuenta'].replace('act_', '')}",
                        # R12 (C-02): «activa» es el estado de la CUENTA publicitaria, no de la campaña. Se dice así.
                        'estado_cuenta': f"cuenta {MOTIVO_META.get(m.get('estado_num'), 'en estado ' + str(m.get('estado_num')))}"}
        dia_enc = (fecha(encendido) - alta).days if encendido else None
        if encendido:
            estado_enc = 'verde' if dia_enc <= ENCENDIDO_OBJETIVO else 'ambar' if dia_enc <= ENCENDIDO_LIMITE else 'rojo'
        else:
            estado_enc = 'rojo' if dia > ENCENDIDO_LIMITE else 'ambar' if dia > 8 else 'gris'
        plazo = {'verde': 'encendida en plazo', 'ambar': 'encendida el día 11-12' if encendido else 'en riesgo: día 9-12 sin encender',
                 'rojo': 'encendida tarde' if encendido else 'fuera de plazo: pasado el día 12 sin encender', 'gris': 'en plazo, todavía sin encender'}[estado_enc]
        if not encendido and dia > ENCENDIDO_LIMITE:
            alertas.insert(0, {'tipo': 'fuera_plazo', 'estado': 'rojo', 'texto': f'Día {dia} sin campaña encendida (objetivo día {ENCENDIDO_OBJETIVO}, límite {ENCENDIDO_LIMITE}).'})
        elif not encendido and dia >= 8:
            alertas.insert(0, {'tipo': 'riesgo_plazo', 'estado': 'ambar', 'texto': f'Día {dia}: si el día 8 no está la prueba de punta a punta, se avisa a Coti y a Mili el día 10.'})

        # ---------------- GHL de la subcuenta del alta
        loc = ghl_de.get(cid)
        sub = subs.get(loc) if loc else None
        citas = (sub or {}).get('citas_desde_alta') or []
        if encendido:
            fin_g = (fecha(encendido) + dt.timedelta(days=GARANTIA_DIAS)).isoformat()
            en_vent = [x for x in citas if encendido <= x['inicio'][:10] <= fin_g]
        else:
            fin_g, en_vent = None, []
        validas = [x for x in en_vent if (x['estado'] or '').lower() == 'showed']
        sin_estado = [x for x in en_vent if (x['estado'] or '').lower() in ('confirmed', 'new', 'booked') and x['inicio'][:10] < hoy.isoformat()]
        if not primer_lead and sub and encendido:
            pass

        # ---------------- reuniones (capa E1) y talleres (GHL de RO, panel 1-oct)
        reus = (((c.get('fuentes') or {}).get('reuniones') or {}).get('datos') or {})
        hist = reus.get('historial') or []
        res = [r for r in hist if encendido and r.get('fecha') and r['fecha'] >= encendido and re.search(r'resultad|seguimiento|mensual|revisi', r.get('asunto') or '', re.I)]
        claves_nombre = [norm(a['nombre']).split(' ')[0]] + ({'imfor-asesores': ['imfor'], 'cib-partners': ['cib'], 'abner-advisory': ['abner'], 'tst-consulting': ['tst'],
                                                              'think-value': ['think'], 'marlex-consulting': ['marlex'], 'impulsa-cfo': ['impulsa'], 'deudot': ['deudout']}.get(cid, []))
        talleres = [e for e in eventos_ro if 'taller' in (e.get('title') or '').lower() and any(k2 in norm(e.get('title')) for k2 in claves_nombre)]
        talleres.sort(key=lambda e: e.get('startTime') or '')
        p_hitos = (panel.get(norm(a['nombre']).split(' ')[0]) or {}).get('hitos') or []
        arr_panel = next((h for h in p_hitos if h['nombre'] == 'Arranque'), None)
        tarea_taller = next((t for t in tareas if re.search(r'taller de oferta|configuraciones b[aá]sicas', t['nombre'], re.I) and t['hecha']), None)
        acc_t = [t for t in tareas if re.search(r'^accesos (meta|crm)', t['nombre'], re.I)]

        # ---------------- hitos
        def obj(dn):
            return (alta + dt.timedelta(days=dn)).isoformat() if dn is not None else None
        hitos = []
        hitos.append({'id': 'firma', 'nombre': 'Firma', 'quien': 'Ventas (Tomás)', 'objetivo': None, 'fecha': (a.get('firma') or '')[:10] or None,
                      'estado': 'hecho', 'fuente': 'Zoho Sign', 'prueba': a['documento']})
        if acc_t:
            ok = [t for t in acc_t if t['hecha']]
            hitos.append({'id': 'accesos', 'nombre': 'Accesos', 'quien': 'Agus', 'objetivo': obj(3),
                          'fecha': None if len(ok) < len(acc_t) else None, 'estado': 'hecho' if len(ok) == len(acc_t) else ('tarde' if dia > 3 else 'pendiente'),
                          'fuente': 'ClickUp', 'prueba': f'{len(ok)} de {len(acc_t)} tareas de accesos hechas (Meta y CRM)'})
        else:
            hitos.append({'id': 'accesos', 'nombre': 'Accesos', 'quien': 'Agus', 'objetivo': obj(3), 'fecha': None,
                          'estado': 'tarde' if dia > 3 else 'pendiente', 'fuente': 'ClickUp', 'prueba': 'Sin tareas de accesos en ClickUp (no hay lista de onboarding)'})
        t_fecha, t_prueba, t_estado = None, None, 'pendiente'
        if talleres:
            e = talleres[0]
            t_fecha = (e.get('startTime') or '')[:10]
            t_estado = 'hecho' if t_fecha <= hoy.isoformat() else 'agendado'
            t_prueba = f"{limpio(e.get('title'))} · {e.get('startTime', '')[:16].replace('T', ' ')} (calendario de GHL de RO)"
        elif tarea_taller:
            t_estado, t_prueba = 'hecho', f'Tarea «{tarea_taller["nombre"]}» completada en ClickUp'
        elif arr_panel and arr_panel['estado'] == 'hecho':
            t_estado, t_fecha, t_prueba = 'hecho', arr_panel.get('fecha'), arr_panel.get('prueba')
        else:
            t_prueba = 'Sin taller en el calendario de RO ni tarea hecha'
            t_estado = 'tarde' if dia > 2 else 'pendiente'
        eq = equipo_todo.get(cid)
        ap_fuente = 'GHL de RO / ClickUp / Fathom'
        if eq and eq.get('taller'):
            tq = eq['taller']
            te = tq.get('estado')
            tf = (tq.get('fecha') or '')[:10] or None
            eq_estado = 'hecho' if te == 'hecho' else 'agendado' if te in ('agendado', 'segunda_sesion') else 'tarde' if dia > 2 else 'pendiente'
            if te in ('agendado', 'segunda_sesion') and tf and tf < hoy.isoformat():
                eq_estado = 'tarde'
            t_prueba = f"Equipo de arranque: {TXT_TALLER.get(te, te)}{(' · ' + fecha_corta(tq.get('fecha'))) if tq.get('fecha') else ''}" + (f" · calendario de RO: {t_prueba}" if talleres else '')
            t_estado, t_fecha, ap_fuente = eq_estado, tf or t_fecha, 'Equipo de arranque (2-oct) + calendario de RO'
        hitos.append({'id': 'arranque', 'nombre': 'Taller de oferta', 'quien': 'Tomás y Coti', 'objetivo': obj(2), 'fecha': t_fecha, 'estado': t_estado, 'fuente': ap_fuente, 'prueba': t_prueba})
        t_cfg = next((t for t in tareas if re.search(r'configuraciones b[aá]sicas', t['nombre'], re.I) and t['nombre'].lower().startswith('reuni')), None)
        cq = (eq or {}).get('config_basicas') or {}
        ce = cq.get('estado')
        if ce:
            c_estado = 'hecho' if ce == 'hecho' else 'agendado' if ce == 'agendada' else ('tarde' if dia > 4 else 'pendiente')
            c_prueba = f"Equipo de arranque: {TXT_CONFIG.get(ce, ce)}{(' · ' + fecha_corta(cq.get('fecha'))) if cq.get('fecha') else ''}{(' · ' + cq['nota']) if cq.get('nota') else ''}"
            c_fecha, c_fuente = (cq.get('fecha') or '')[:10] or None, 'Equipo de arranque (2-oct) + ClickUp'
        elif t_cfg:
            c_estado = 'hecho' if t_cfg['hecha'] else ('tarde' if dia > 4 else 'pendiente')
            c_prueba, c_fecha, c_fuente = f"Tarea «{t_cfg['nombre']}» en ClickUp: {t_cfg['estado']}", t_cfg.get('limite'), 'ClickUp'
        else:
            c_estado, c_prueba, c_fecha, c_fuente = ('tarde' if dia > 4 else 'pendiente'), 'Sin agendar: ni declarada por el equipo ni tarea en ClickUp', None, 'ClickUp'
        hitos.append({'id': 'config', 'nombre': 'Configuración básica', 'quien': 'Agus, Valeria y Yessica', 'objetivo': obj(4), 'fecha': c_fecha, 'estado': c_estado, 'fuente': c_fuente, 'prueba': c_prueba,
                      'sin_agendar': ce in ('sin_agendar', 'pendiente') or (not ce and not t_cfg)})
        hitos.append({'id': 'encendido', 'nombre': 'Encendido', 'quien': 'Trafficker y Agus', 'objetivo': obj(ENCENDIDO_OBJETIVO), 'limite': obj(ENCENDIDO_LIMITE),
                      'fecha': encendido, 'dia': dia_enc, 'estado': ('hecho' if estado_enc == 'verde' else 'hecho_tarde') if encendido else ('tarde' if estado_enc == 'rojo' else 'pendiente'),
                      'fuente': 'Meta', 'prueba': (f'Primer día con gasto en {meta_out["nombre"]}: {encendido}' if encendido else
                                                   f'Cuenta {meta_out["nombre"]} sin gasto desde la firma' if meta_out else 'RO no ve ninguna cuenta publicitaria de este cliente en Meta')})
        hitos.append({'id': 'primer_lead', 'nombre': 'Primer lead', 'quien': 'Trafficker', 'objetivo': obj((dia_enc or ENCENDIDO_OBJETIVO) + 3),
                      'fecha': primer_lead, 'dias_desde_encendido': (fecha(primer_lead) - fecha(encendido)).days if primer_lead and encendido else None,
                      'estado': 'hecho' if primer_lead else ('pendiente' if not encendido or (hoy - fecha(encendido)).days <= 7 else 'tarde'),
                      'fuente': 'Meta (formularios)', 'prueba': f'Primer día con leads en Meta: {primer_lead}' if primer_lead else ('Sin leads desde el encendido' if encendido else 'Sin encendido')})
        hitos.append({'id': 'reunion_resultados', 'nombre': 'Primera reunión de resultados', 'quien': 'Account', 'objetivo': obj(30),
                      'fecha': res[0]['fecha'] if res else None, 'estado': 'hecho' if res else ('tarde' if dia > 30 else 'pendiente'),
                      'fuente': 'CRM + Fathom (capa E1)', 'prueba': limpio(res[0].get('asunto')) if res else 'Sin reunión de resultados después del encendido'})
        garantia = None
        if a.get('garantia_firmada'):
            garantia = {'firmada': True, 'literal': a.get('garantia_literal'), 'desde': encendido, 'hasta': fin_g, 'validas': len(validas), 'sin_estado': len(sin_estado),
                        'necesarias': GARANTIA_REUNIONES, 'citas_en_ventana': len(en_vent)}
        hitos.append({'id': 'garantia', 'nombre': 'Día 30 · garantía', 'quien': 'Coti', 'objetivo': fin_g or obj(30), 'fecha': None,
                      'estado': ('hecho' if garantia and len(validas) >= GARANTIA_REUNIONES else 'tarde' if garantia and fin_g and fin_g < hoy.isoformat() else 'pendiente') if garantia else 'no_aplica',
                      'fuente': 'Sign + GHL del despacho', 'prueba': (f'{len(validas)} de {GARANTIA_REUNIONES} reuniones celebradas desde el encendido' if garantia else 'El acuerdo no lleva garantía de reuniones (solo cuenta en quien la firmó)')})
        hitos.append({'id': 'dia90', 'nombre': 'Día 90', 'quien': 'Account', 'objetivo': obj(90), 'fecha': None, 'estado': 'pendiente', 'fuente': 'Calendario', 'prueba': f'Paso a cliente consolidado el {fecha_es(obj(90))}'})
        if encendido:
            for h in hitos:
                if h['id'] in ('accesos', 'arranque', 'config') and h['estado'] != 'hecho':
                    h['estado'] = 'hecho'
                    h['implicito'] = True
                    h['prueba'] = f"Se da por hecho: la campaña está encendida (el contrato exige accesos y taller para encender) · {h['prueba']}"
        siguiente = next((h for h in hitos if h['estado'] in ('pendiente', 'tarde', 'agendado')), None)

        # ---------------- accesos (lista canónica de la skill onboarding-accesos-ro; nunca la clave)
        f = c.get('fuentes') or {}
        def est_fuente(nombre):
            e = (f.get(nombre) or {}).get('estado')
            return 'dado' if e in ('bien', 'a_cero', 'dato_viejo') else 'falta'
        def tarea_acc(patron):
            t = next((x for x in tareas if re.search(patron, x['nombre'], re.I)), None)
            return t
        accesos = []
        tm = tarea_acc(r'^accesos meta')
        accesos.append({'recurso': 'Meta (portfolio, cuenta y píxel)', 'icono': 'megafono', 'estado': 'dado' if meta_out else 'falta',
                        'quien': ', '.join(tm['asignados']) if tm and tm['asignados'] else (traff[0]['nombre'] if traff else 'trafficker sin asignar'),
                        'desde': a['alta'], 'prueba': f'Cuenta {meta_out["nombre"]} visible para RO' if meta_out else 'RO no ve su cuenta publicitaria', 'tarea': tm['url'] if tm else None,
                        'tarea_estado': tm['estado'] if tm else None})
        tc = tarea_acc(r'^accesos crm')
        accesos.append({'recurso': 'CRM (subcuenta de GHL)', 'icono': 'base', 'estado': 'dado' if loc else 'falta',
                        'quien': ', '.join(tc['asignados']) if tc and tc['asignados'] else (crm[0]['nombre'] if crm else 'CRM sin asignar'),
                        'desde': a['alta'], 'prueba': f'Subcuenta «{(sub or {}).get("nombre") or loc}»' if loc else 'Sin subcuenta de GHL entre las 66', 'tarea': tc['url'] if tc else None,
                        'tarea_estado': tc['estado'] if tc else None})
        for nombre, rec, ic in (('ga4', 'Google Analytics', 'grafico'), ('gsc', 'Search Console', 'buscar'), ('metricool', 'Redes (Metricool)', 'compartir'), ('chat', 'Canal de ClickUp', 'chat')):
            accesos.append({'recurso': rec, 'icono': ic, 'estado': est_fuente(nombre), 'quien': 'Agus', 'desde': a['alta'],
                            'prueba': ((f.get(nombre) or {}).get('nota') or ('Conectado en la capa de datos' if est_fuente(nombre) == 'dado' else 'Sin emparejar en la capa de datos'))[:140]})
        accesos.append({'recurso': 'Web (WordPress)', 'icono': 'globe', 'estado': 'sin_registro', 'quien': 'Agus', 'desde': a['alta'], 'prueba': 'No hay registro de este acceso en ninguna herramienta: se marca a mano con prueba'})
        accesos.append({'recurso': 'Ficha de Google', 'icono': 'pin', 'estado': 'sin_registro', 'quien': 'Agus', 'desde': a['alta'], 'prueba': 'No hay registro de este acceso en ninguna herramienta: se marca a mano con prueba'})

        # ---------------- casillas técnicas
        d = (dns.get('dominios') or {}).get(a['dominio'] or '') or {}
        casillas = []
        px = (meta_out or {}).get('pixel')
        casillas.append({'id': 'pixel', 'texto': 'Píxel de Meta', 'estado': ('verde' if px and px.get('ultimo_evento') and px['ultimo_evento'][:10] >= (hoy - dt.timedelta(days=7)).isoformat() else 'ambar' if px else 'rojo') if meta_out else 'gris',
                         'detalle': (f'«{px["nombre"]}» · último evento {px["ultimo_evento"] or "nunca"}' if px else 'La cuenta no tiene píxel') if meta_out else 'Sin cuenta de Meta visible', 'fuente': 'Meta'})
        casillas.append({'id': 'dominio', 'texto': 'Dominio verificado en Meta', 'estado': 'gris', 'detalle': 'Todavía no se mide: pide leer el Business Manager del cliente (permiso nuevo)', 'fuente': 'Meta', 'medible': 'no'})
        if d:
            casillas.append({'id': 'spf', 'texto': 'DNS · SPF', 'estado': 'verde' if d.get('spf') and not d.get('spf_varios') else 'ambar' if d.get('spf') else 'rojo',
                             'detalle': ('Dos registros SPF: el correo puede fallar' if d.get('spf_varios') else 'Registro SPF publicado') if d.get('spf') else 'Sin registro SPF', 'fuente': 'DNS público'})
            casillas.append({'id': 'dmarc', 'texto': 'DNS · DMARC', 'estado': 'verde' if d.get('dmarc') in ('quarantine', 'reject') else 'ambar' if d.get('dmarc') == 'none' else 'rojo',
                             'detalle': f'Política «{d["dmarc"]}»' if d.get('dmarc') else 'Sin registro DMARC', 'fuente': 'DNS público'})
            casillas.append({'id': 'dkim', 'texto': 'DNS · DKIM', 'estado': 'verde' if d.get('dkim_selector') else 'ambar',
                             'detalle': f'Firma con el selector «{d["dkim_selector"]}»' if d.get('dkim_selector') else 'No aparece con los selectores habituales: comprobar con su proveedor de correo', 'fuente': 'DNS público'})
        else:
            casillas.append({'id': 'dns', 'texto': 'DNS (SPF, DKIM, DMARC)', 'estado': 'gris', 'detalle': 'Sin dominio de web en la capa de datos', 'fuente': 'DNS público'})
        if sub:
            wa_e, wa_f = sub.get('wa_enviados_7d') or 0, sub.get('wa_fallidos_7d') or 0
            casillas.append({'id': 'whatsapp', 'texto': 'WhatsApp en GHL', 'estado': 'gris' if not wa_e else ('rojo' if wa_f / wa_e > 0.10 else 'verde'),
                             'detalle': f'{wa_f} fallidos de {wa_e} enviados en 7 días' if wa_e else 'Sin WhatsApp enviados en 7 días (o el número no está conectado: GHL no da su estado por API)', 'fuente': 'GHL'})
            sin_u = sub.get('calendarios_sin_usuario') or []
            casillas.append({'id': 'calendario', 'texto': 'Calendario con usuario', 'estado': 'rojo' if not sub.get('calendarios') else 'ambar' if sin_u else 'verde',
                             'detalle': ('Sin calendarios' if not sub.get('calendarios') else (f'{len(sin_u)} calendario sin persona asignada' if len(sin_u) == 1 else f'{len(sin_u)} calendarios sin persona asignada') if sin_u else (f'{sub["calendarios"]} calendario con persona asignada' if sub['calendarios'] == 1 else f'{sub["calendarios"]} calendarios con persona asignada')), 'fuente': 'GHL'})
            casillas.append({'id': 'snapshot', 'texto': 'Subcuenta creada (snapshot)', 'estado': 'verde', 'detalle': f'Subcuenta «{sub["nombre"]}» con {sub.get("usuarios") or 0} usuario(s)', 'fuente': 'GHL'})
        else:
            for i2, t2 in (('whatsapp', 'WhatsApp en GHL'), ('calendario', 'Calendario con usuario'), ('snapshot', 'Subcuenta creada (snapshot)')):
                casillas.append({'id': i2, 'texto': t2, 'estado': 'rojo' if dia > 3 else 'ambar', 'detalle': 'Sin subcuenta de GHL para este cliente', 'fuente': 'GHL'})
        casillas.append({'id': 'landing_posts', 'texto': 'Landing y posts revisados', 'estado': 'gris', 'detalle': 'Se marca a mano con prueba: si Meta gasta sin esta casilla, salta un aviso', 'fuente': 'Manual', 'manual': True})
        if meta_out and gasto_desde_alta and gasto_desde_alta > 0:
            alertas.append({'tipo': 'gasta_sin_casilla', 'estado': 'ambar', 'texto': 'Meta ya gasta y la casilla «Landing y posts revisados» no está marcada.'})

        # ---------------- bloqueos de Meta
        if meta_out and meta_out['estado_num'] not in (1, None):
            alertas.append({'tipo': 'bloqueo_meta', 'estado': 'rojo', 'texto': f'Cuenta de Meta {meta_out["estado"]}' + (f' (motivo {meta_out["motivo_bloqueo"]})' if meta_out.get('motivo_bloqueo') else '') + '.'})

        # ---------------- cruce: lo que dice el equipo frente a lo que ve la app
        diferencias = []
        def dif(tipo, equipo, app_ve, estado='ambar'):
            diferencias.append({'tipo': tipo, 'equipo': equipo, 'app': app_ve, 'estado': estado})
        txt = norm(' '.join([(eq or {}).get('estado') or '', (eq or {}).get('proximo_paso') or '']))
        dice_ghl = bool(re.search(r'(subcuenta|cuenta|snapshot)[a-z ]{0,20}(ghl|creada)|cuenta snapshot', txt))
        if dice_ghl and not loc:
            dif('ghl', 'Subcuenta de GHL creada', 'GHL: no hay ninguna subcuenta emparejada con este cliente entre las 66', 'rojo')
        elif dice_ghl and loc:
            dif('ghl', 'Subcuenta de GHL creada', f'GHL: subcuenta «{(sub or {}).get("nombre") or loc}» · coincide', 'verde')
        elif not loc:
            dif('ghl', 'No lo menciona', 'GHL: sin subcuenta para este cliente', 'rojo' if dia > 3 else 'ambar')
        falta_acc = [x['recurso'] for x in accesos if x['estado'] == 'falta']
        if 'accesos completados' in txt:
            dif('accesos', 'Accesos completados', ('La app aún ve pendientes: ' + ', '.join(falta_acc)) if falta_acc else 'Coincide: la app no ve accesos pendientes', 'rojo' if falta_acc else 'verde')
        elif 'accesos pedidos' in txt and not lista:
            dif('accesos', 'Accesos pedidos', 'Sin tareas de accesos en ClickUp: el seguimiento no queda en ninguna herramienta', 'ambar')
        if not lista:
            k_c = norm(a['nombre']).split(' ')[0]
            tiene_carpeta = any(k_c in c for c in carpetas_cu)
            dif('clickup', 'Trabajo en marcha (taller, accesos)' if eq else 'Sin estado del equipo',
                'ClickUp: ' + ('carpeta del cliente sin lista de onboarding' if tiene_carpeta else 'sin carpeta ni lista de onboarding'), 'rojo')
        if cq.get('estado') == 'hecho' and t_cfg and not t_cfg['hecha']:
            dif('config', 'Configuración básica hecha', f'ClickUp: «{t_cfg["nombre"]}» sigue en «{t_cfg["estado"]}»', 'ambar')
        if cq.get('estado') == 'agendada' and t_cfg and t_cfg.get('limite') and cq.get('fecha') and t_cfg['limite'] != cq['fecha'][:10]:
            dif('config', f'Configuración agendada el {cq["fecha"][:10]}', f'ClickUp: fecha límite {t_cfg["limite"]}', 'ambar')
        if eq and (eq.get('taller') or {}).get('estado') == 'hecho' and not talleres and (eq['taller'].get('fecha') or '') >= '2026-07-01':
            dif('taller', f'Taller hecho{(" el " + eq["taller"]["fecha"][:10]) if eq["taller"].get("fecha") else ""}', 'Calendario de RO (foto del 1-oct): sin cita de taller con este cliente', 'gris')
        if not a.get('encargo_art28') and 'accesos pedidos' in txt:
            dif('art28', 'Accesos pedidos', 'Sin encargo de tratamiento firmado: no se debían pedir', 'rojo')
        if eq:
            if eq.get('urgente'):
                alertas.insert(0, {'tipo': 'urgente', 'estado': 'rojo', 'texto': f'Marcada urgente por el equipo de arranque: {eq.get("proximo_paso") or eq.get("estado")}'})
            nota_cfg = norm(' '.join([cq.get('nota') or '', eq.get('proximo_paso') or '', eq.get('estado') or '']))
            if cq.get('estado') == 'sin_agendar':
                sin_resp = 'sin responder' in nota_cfg or 'recordatorio' in nota_cfg
                alertas.insert(1 if eq.get('urgente') else 0, {'tipo': 'config_sin_agendar', 'estado': 'rojo',
                    'texto': f'Configuración básica sin agendar{" y cliente sin responder" if sin_resp else ""} en el día {dia}' + (f' ({cq["nota"]})' if cq.get('nota') else '') + ': sin ella no hay encendido.'})
                for al in alertas:
                    if al['tipo'] == 'fuera_plazo':
                        al['texto'] += f' Causa declarada: configuración sin agendar{" y cliente sin responder" if sin_resp else ""}.'
        for x in diferencias:
            if x['estado'] == 'rojo' and x['tipo'] in ('ghl', 'accesos', 'art28') and x['equipo'] not in ('No lo menciona',):
                alertas.append({'tipo': 'diferencia', 'estado': 'ambar', 'texto': f'El equipo dice «{x["equipo"]}»; {x["app"]}.'})
        equipo_out = None
        if eq:
            equipo_out = {'taller': eq.get('taller'), 'config_basicas': eq.get('config_basicas'), 'estado': limpio(eq.get('estado')), 'proximo_paso': limpio(eq.get('proximo_paso')),
                          'urgente': bool(eq.get('urgente')), 'actualizado': eq.get('actualizado'), 'autor': eq.get('autor'), 'origen': eq.get('origen')}
        orden = {'rojo': 0, 'ambar': 1, 'gris': 2}
        alertas.sort(key=lambda x: orden.get(x['estado'], 3))
        filas.append({
            'cliente_id': cid, 'nombre': a['nombre'], 'firma': a['firma'], 'alta': a['alta'], 'alta_prueba': a.get('alta_prueba'), 'dia': dia,
            'semana': dia // 7 + 1, 'documento': a['documento'], 'web': a['web'], 'dominio': a['dominio'],
            'dueno': {'id': DUENO_TECNICO, 'nombre': (pers.get(DUENO_TECNICO) or {}).get('alias') or 'Agus'},
            'vigilante': {'id': VIGILANTE, 'nombre': (pers.get(VIGILANTE) or {}).get('alias') or 'Mili'},
            'account': cuenta[0] if cuenta else None, 'sin_account': sin_account, 'trafficker': traff[0] if traff else None, 'crm': crm[0] if crm else None,
            'plazo': {'estado': estado_enc, 'texto': plazo, 'objetivo': obj(ENCENDIDO_OBJETIVO), 'limite': obj(ENCENDIDO_LIMITE), 'dia_encendido': dia_enc},
            # R12 (C-02): estado de la CAMPAÑA (encendida o no), el mismo que la verdad única (encendido / campana_activa)
            'campana': {'encendida': dia_enc is not None,
                        'texto': (f'campaña encendida el día {dia_enc}' if dia_enc is not None else 'campaña sin encender')},
            'encargo_art28': a.get('encargo_art28'),
            'hitos': hitos, 'siguiente': {'id': siguiente['id'], 'nombre': siguiente['nombre'], 'objetivo': siguiente.get('objetivo'), 'estado': siguiente['estado'], 'quien': siguiente['quien']} if siguiente else None,
            'onboarding': ({'list_id': lista['list_id'], 'lista': lista['lista'], 'url': f"https://app.clickup.com/90152357276/v/li/{lista['list_id']}",
                            'n': len(tareas), 'hechas': len(hechas), 'pct': pct, 'vencidas': len(vencidas), 'bloqueadas': len(bloqueadas),
                            'sin_plazo': len(sin_plazo), 'no_avanza': len(no_avanza), 'tareas': tareas} if lista else None),
            'horas_desde_firma': horas_firma, 'alertas': alertas, 'accesos': accesos, 'casillas': casillas, 'meta': meta_out,
            'equipo': equipo_out, 'diferencias': diferencias, 'urgente': bool((eq or {}).get('urgente')),
            'garantia': garantia, 'subcuenta': ({'loc': loc, 'nombre': sub['nombre']} if sub else None),
            'citas_desde_alta': len(citas),
        })
    filas.sort(key=lambda x: (not x['urgente'], {'rojo': 0, 'ambar': 1, 'gris': 2, 'verde': 3}[x['plazo']['estado']], -x['dia']))

    # ---- 66 subcuentas: conexiones caídas
    ventana = {a['cliente_id']: a for a in filas}
    caidas = []
    for s in ghl.get('subcuentas', []):
        cid = loc_a_cliente.get(s['loc'])
        prob = []
        if s.get('error'):
            prob.append({'tipo': 'lectura', 'estado': 'gris', 'texto': 'GHL no deja leer esta subcuenta'})
        else:
            if s.get('calendarios') == 0:
                prob.append({'tipo': 'calendario', 'estado': 'ambar', 'texto': 'Sin calendarios'})
            if s.get('calendarios_sin_usuario'):
                prob.append({'tipo': 'calendario', 'estado': 'rojo', 'texto': (f'1 calendario sin persona asignada: «{s["calendarios_sin_usuario"][0]}»' if len(s['calendarios_sin_usuario']) == 1 else f'{len(s["calendarios_sin_usuario"])} calendarios sin persona asignada: ' + ', '.join('«' + x + '»' for x in s['calendarios_sin_usuario'][:3]))})
            if s.get('wa_enviados_7d') and s['wa_fallidos_7d'] / s['wa_enviados_7d'] > 0.10:
                prob.append({'tipo': 'whatsapp', 'estado': 'rojo', 'texto': f'WhatsApp: {s["wa_fallidos_7d"]} fallidos de {s["wa_enviados_7d"]} en 7 días ({round(s["wa_fallidos_7d"] / s["wa_enviados_7d"] * 100)} %)'})
            elif s.get('wa_fallidos_7d'):
                prob.append({'tipo': 'whatsapp', 'estado': 'ambar', 'texto': f'WhatsApp: {s["wa_fallidos_7d"]} fallidos de {s["wa_enviados_7d"]} en 7 días'})
            if s.get('usuarios') == 0:
                prob.append({'tipo': 'usuarios', 'estado': 'ambar', 'texto': 'Sin usuarios'})
        en_alta = cid in ventana
        dueno = 'Agus (alta hasta el día 90)' if en_alta else 'Especialista en GHL'
        fila = {'loc': s['loc'], 'subcuenta': s['nombre'], 'calendarios': s.get('calendarios'), 'calendarios_sin_usuario': len(s.get('calendarios_sin_usuario') or []),
                'usuarios': s.get('usuarios'), 'wa_enviados_7d': s.get('wa_enviados_7d'), 'wa_fallidos_7d': s.get('wa_fallidos_7d'),
                'problemas': prob, 'estado': 'rojo' if any(p['estado'] == 'rojo' for p in prob) else 'ambar' if prob else 'verde',
                'dueno': dueno, 'en_alta': en_alta, 'cliente': nombre_de.get(cid) if cid else None,
                'tipo': 'cliente' if cid else ('interna' if re.search(r'ranking|snapsho|dummy|prueba|eliminar|no tocar', s['nombre'], re.I) else 'sin cliente en la app')}
        if cid:
            fila['cliente_id'] = cid
        caidas.append(fila)
    caidas.sort(key=lambda x: ({'rojo': 0, 'ambar': 1, 'verde': 2}[x['estado']], not x['en_alta'], x['subcuenta'].lower()))

    # ---- indicadores
    llegan12 = [a for a in filas if a['dia'] >= ENCENDIDO_LIMITE]
    en_plazo = [a for a in llegan12 if a['plazo']['dia_encendido'] is not None and a['plazo']['dia_encendido'] <= ENCENDIDO_OBJETIVO]
    semana_ini = lunes(HOY)
    esta_semana = [a for a in filas if fecha(a['alta']) >= semana_ini or ((fecha(a['firma'][:10]) >= semana_ini) if a.get('firma') else False)]
    arranques_sem = [a for a in filas if semana_ini <= fecha(a['alta']) < semana_ini + dt.timedelta(days=7)]
    lead_dias = [h['dias_desde_encendido'] for a in filas for h in a['hitos'] if h['id'] == 'primer_lead' and h.get('dias_desde_encendido') is not None]
    resumen = {
        'altas': len(filas), 'en_plazo_dia12': {'si': len(en_plazo), 'de': len(llegan12), 'pct': int(len(en_plazo) / len(llegan12) * 100 + 0.5) if llegan12 else None},   # V2: redondeo como Math.round (1 de 8 = 13 %, no 12 %)
        'fuera_de_plazo': len([a for a in filas if a['plazo']['estado'] == 'rojo']),
        'en_riesgo': len([a for a in filas if a['plazo']['estado'] == 'ambar']),
        'sin_tareas': len([a for a in filas if not a['onboarding']]),
        'sin_tareas_48h': len([a for a in filas if not a['onboarding'] and (a['horas_desde_firma'] or 0) > SIN_TAREAS_HORAS]),
        'tareas_vencidas': sum((a['onboarding'] or {}).get('vencidas', 0) for a in filas),
        'tareas_no_avanzan': sum((a['onboarding'] or {}).get('no_avanza', 0) for a in filas),
        'tareas_bloqueadas': sum((a['onboarding'] or {}).get('bloqueadas', 0) for a in filas),
        'tareas_sin_plazo': sum((a['onboarding'] or {}).get('sin_plazo', 0) for a in filas),
        'tareas_total': sum((a['onboarding'] or {}).get('n', 0) for a in filas),
        'accesos_falta': sum(1 for a in filas for x in a['accesos'] if x['estado'] == 'falta'),
        'subcuentas': len(caidas), 'subcuentas_caidas': len([x for x in caidas if x['estado'] == 'rojo']),
        'subcuentas_aviso': len([x for x in caidas if x['estado'] == 'ambar']),
        'carga_semana': len(arranques_sem), 'carga_tope': 5,
        'primer_lead_mediana_dias': sorted(lead_dias)[len(lead_dias) // 2] if lead_dias else None,
        'encargo_firmado': len([a for a in filas if a['encargo_art28']]),
        'urgentes': len([a for a in filas if a['urgente']]),
        'config_sin_agendar': len([a for a in filas if any(h['id'] == 'config' and h.get('sin_agendar') for h in a['hitos'])]),
        'diferencias': sum(1 for a in filas for x in a['diferencias'] if x['estado'] in ('rojo', 'ambar')),
    }
    plantilla = [{'patron': p, 'dia': dn, 'fase': fase} for p, dn, fase in PLANTILLA_DN]
    talleres = []
    for e in eventos_ro:
        t = e.get('title') or ''
        ini = (e.get('startTime') or '')[:16]
        if 'taller' not in t.lower() or not ini or not ((HOY - dt.timedelta(days=7)).isoformat() <= ini[:10] <= (HOY + dt.timedelta(days=14)).isoformat()):
            continue
        nt = norm(t)
        cid = next((a['cliente_id'] for a in filas if any(k in nt for k in [norm(a['nombre']).split(' ')[0]] + {'imfor-asesores': ['imfor'], 'cib-partners': ['cib'], 'tst-consulting': ['tst'], 'think-value': ['think'], 'deudot': ['deudout']}.get(a['cliente_id'], []))), None)
        prev = next((p['nombre'] for p in previstas if norm(p['nombre']).split(' ')[0] in nt), None)
        fila_t = {'inicio': ini.replace('T', ' '), 'titulo': limpio(t.split('·')[0].strip()), 'cliente': (next((a['nombre'] for a in filas if a['cliente_id'] == cid), None) if cid else prev),
                  'estado': e.get('appointmentStatus') or e.get('appoinmentStatus'), 'pasado': ini[:10] < HOY.isoformat()}
        if cid:
            fila_t['cliente_id'] = cid
        talleres.append(fila_t)
    talleres.sort(key=lambda x: x['inicio'])
    datos = {
        'formato': 1, 'modulo': 'clientes-nuevos', 'generado': AHORA.strftime('%Y-%m-%d %H:%M'), 'hoy': HOY.isoformat(),
        'reglas': {'encendido_objetivo': ENCENDIDO_OBJETIVO, 'encendido_limite': ENCENDIDO_LIMITE, 'ventana': VENTANA,
                   'sin_tareas_horas': SIN_TAREAS_HORAS, 'bloqueo_escalar_dias': BLOQUEO_ESCALAR_DIAS, 'garantia_dias': GARANTIA_DIAS,
                   'garantia_reuniones': GARANTIA_REUNIONES, 'carga_tope_semana': 5,
                   'origen': 'Encendido el día 10, como tarde el 12, desde el alta del contrato · alertas pedidas por Mili · garantía solo en quien la firmó · Agus es dueño de las conexiones hasta el día 90'},
        'fuentes': {
            'sign': {'fuente': 'Zoho Sign', 'hora': sign.get('hora'), 'estado': 'bien' if sign.get('sobres') else 'sin_conectar'},
            'clickup': {'fuente': 'ClickUp', 'hora': cu.get('hora'), 'estado': 'bien' if cu.get('listas') is not None else 'sin_conectar', 'listas': len(cu.get('listas') or [])},
            'meta': {'fuente': 'Meta', 'hora': meta.get('hora'), 'estado': 'bien' if meta.get('por_cliente') is not None else 'sin_conectar', 'cuentas_visibles': meta.get('cuentas_visibles')},
            'ghl': {'fuente': 'GHL (66 subcuentas)', 'hora': ghl.get('hora'), 'estado': 'bien' if ghl.get('subcuentas') else 'sin_conectar'},
            'dns': {'fuente': 'DNS público', 'hora': dns.get('hora'), 'estado': 'bien' if dns.get('dominios') is not None else 'sin_conectar'},
        },
        'equipo_fuente': {'fichero': MANUAL.name, 'autor': AUTOR_MANUAL, 'fecha': ((lee(MANUAL, {}) or {}).get('_meta') or {}).get('fecha'),
                          'edicion': 'Desde la app: formulario «Estado del equipo» en cada alta (Coti, Agus, Vale, Mili, Tomás); en el prototipo queda en la cola simulada y el generador lo recoge de local.db.'},
        'resumen': resumen, 'altas': filas, 'previstas': previstas, 'talleres': talleres,
        'talleres_nota': 'Calendario «Taller de la oferta» de la subcuenta de RO en GHL (foto del panel del 1-oct): los talleres agendados después no salen hasta la próxima lectura.', 'fuera': FUERA, 'subcuentas': caidas,
        'plantilla_dn': {'lista': 'Onboarding — [PLANTILLA]', 'list_id': '1200220000003981', 'reglas': plantilla,
                         'nota': 'Propuesta: cada tarea de la plantilla con su día objetivo (día 0 + N). Se aplicará cuando la app pueda escribir en ClickUp; hasta entonces, nada se escribe y las tareas sin fecha salen «sin plazo» en gris.'},
    }
    return datos


def main():
    vivo = '--en-vivo' in sys.argv
    que = set()
    if vivo:
        i = sys.argv.index('--en-vivo')
        que = set(sys.argv[i + 1].split(',')) if len(sys.argv) > i + 1 and not sys.argv[i + 1].startswith('-') else {'sign', 'clickup', 'meta', 'ghl', 'dns'}
    errores = {}
    if 'sign' in que:
        try:
            leer_sign()
        except Exception as e:
            errores['sign'] = str(e)[:200]
    if 'clickup' in que:
        try:
            leer_clickup()
        except BaseException as e:
            errores['clickup'] = str(e)[:200]
    altas, *_ = montar()
    if 'meta' in que:
        try:
            leer_meta(altas)
        except BaseException as e:
            errores['meta'] = str(e)[:200]
    if 'ghl' in que:
        try:
            ghl_de = {}
            for f in (DATA / 'clientes').glob('*.json'):
                c = lee(f, {})
                emp = (((c.get('fuentes') or {}).get('ghl') or {}).get('emparejado') or {})
                if emp.get('id'):
                    ghl_de[c['id']] = emp['id']
            leer_ghl(altas, ghl_de)
        except BaseException as e:
            errores['ghl'] = str(e)[:200]
    if 'dns' in que:
        try:
            leer_dns(altas)
        except Exception as e:
            errores['dns'] = str(e)[:200]
    datos = construir()
    datos['errores_lectura'] = errores
    sys.path.insert(0, str(APP))
    import escaner_secretos as E
    tmp = CRUDO / '_revisar_nuevos.json'
    tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=1))
    hall = E.escanear_fichero(tmp)
    if hall:
        print('La puerta de secretos encuentra algo: no escribo.', hall[:5])
        sys.exit(2)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    os.replace(tmp, SALIDA)
    r = datos['resumen']
    print(f"data/nuevos/nuevos.json · {r['altas']} altas · en plazo {r['en_plazo_dia12']} · fuera {r['fuera_de_plazo']} · sin tareas {r['sin_tareas']} "
          f"({r['sin_tareas_48h']} > 48 h) · vencidas {r['tareas_vencidas']} · bloqueadas {r['tareas_bloqueadas']} · subcuentas {r['subcuentas']} "
          f"(caídas {r['subcuentas_caidas']}) · errores {errores or 'ninguno'}")


if __name__ == '__main__':
    main()
