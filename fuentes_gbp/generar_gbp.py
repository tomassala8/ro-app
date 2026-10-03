#!/usr/bin/env python3
"""
generar_gbp.py · Google Business Profile (la ficha de Google de cada cliente) → data/gbp/gbp.json. SOLO LECTURA.

Con acceso (Google aprueba el proyecto y Tomás ejecuta ~/RO_HERRAMIENTAS/google/gbp.py instalar):
  lee con gbp.volcar() las cuentas, las fichas, su estado (suspendida, deshabilitada, cambios hechos por Google), el
  rendimiento diario (llamadas, clics a la web, rutas, mensajes, reservas, vistas en Búsqueda y en Maps), los términos de
  búsqueda del último mes y las reseñas con estrellas y respuesta. Empareja cada ficha con su cliente (data/clientes/*.json)
  por nombre, web y teléfono (el teléfono solo se compara en memoria: nunca se guarda) o por fuentes_gbp/emparejar.json,
  y deja por cliente su semáforo, sus reseñas por responder y sus incidencias en el formato de alertas de N4 (las recoge
  fuentes_alertas/generar_alertas.py → de_gbp).
Sin acceso: escribe el mismo fichero con estado «pendiente_aprobacion» y los pasos de Tomás. No inventa nada.

Uso:
  python3 fuentes_gbp/generar_gbp.py                       # en vivo (si hay llave y Google ha aprobado)
  python3 fuentes_gbp/generar_gbp.py --desde-cache         # usa fuentes_gbp/_cache/volcado.json (sin red)
  python3 fuentes_gbp/generar_gbp.py --simulado --salida <fichero>   # PRUEBA con datos inventados (nunca a data/)
Reloj falso para pruebas: RO_GBP_AHORA=2026-10-03T09:00
"""
import datetime as dt
import glob
import hashlib
import json
import os
import re
import sys
import unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(AQUI)
SALIDA = os.path.join(APP, 'data', 'gbp', 'gbp.json')
CACHE = os.path.join(AQUI, '_cache', 'volcado.json')          # crudo: no se sirve (el escáner salta _cache)
MANUAL = os.path.join(AQUI, 'emparejar.json')
HERR = os.path.expanduser('~/RO_HERRAMIENTAS/google')
ENLACE = 'https://business.google.com/locations'
DOC_API = 'https://developers.google.com/my-business/content/prereqs'
FORMULARIO = 'https://support.google.com/business/contact/api_default'

# Umbrales (se pueden mover sin tocar el resto)
RESENA_MALA = 3              # estrellas: 1, 2 o 3 = «mala»
RESENA_PLAZO_H = 24          # sin responder más de esto = rojo
RESENA_DIAS_ALERTA = 60      # las reseñas malas más antiguas sin responder se cuentan, pero no levantan alerta
CAIDA_PCT = 30               # llamadas o rutas: caída semana contra semana que avisa (ámbar)
CAIDA_ROJO_PCT = 60          # … y que es roja
CAIDA_BASE_MIN = 8           # la semana anterior tiene que tener al menos esto (con 3 llamadas, una caída no dice nada)

ESTRELLAS = {'ONE': 1, 'TWO': 2, 'THREE': 3, 'FOUR': 4, 'FIVE': 5}
CAMPOS_GOOGLE = {'title': 'nombre', 'phoneNumbers': 'teléfono', 'websiteUri': 'web', 'storefrontAddress': 'dirección',
                 'regularHours': 'horario', 'categories': 'categoría'}
PASOS = [
    {'texto': 'Copiar el número del proyecto de Google Cloud de la app (el mismo que usa Analytics).', 'enlace': 'https://console.cloud.google.com/home/dashboard'},
    {'texto': 'Pedir el acceso con el formulario de Google «Application for Basic API Access», desde la cuenta que gestiona las fichas de los clientes.', 'enlace': FORMULARIO},
    {'texto': 'Requisitos de Google: ficha verificada y activa más de 60 días, con la web del negocio en la ficha, y correo de empresa. Google contesta por correo (dice «en 14 días»).', 'enlace': DOC_API},
    {'texto': 'Cuando aprueben, habilitar las APIs de Business Profile en Google Cloud (la cuota pasa de 0 a 300 por minuto).', 'enlace': 'https://developers.google.com/my-business/content/basic-setup'},
    {'texto': 'En el Mac: python3 ~/RO_HERRAMIENTAS/google/gbp.py instalar (elegir la cuenta que gestiona las fichas). Al día siguiente la tubería lo trae solo.', 'enlace': None},
]
QUE_HACER = ('Lo hace Tomás: pedir el acceso a la API de Google Business Profile (formulario «Application for Basic API Access») '
             'y, cuando Google lo apruebe, python3 ~/RO_HERRAMIENTAS/google/gbp.py instalar.')
TITULAR_PENDIENTE = 'Pendiente de aprobación de Google'
RX_CORREO = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')
RX_TEL = re.compile(r'(?:\+?\d[\s.-]?){9,}')
VACIAS = {'asesores', 'asesoria', 'asesor', 'consultores', 'consulting', 'consultoria', 'abogados', 'economistas', 'gestoria',
          'gestion', 'advisory', 'asesoramiento', 'despacho', 'fiscal', 'laboral', 'contable', 'legal', 'empresas', 'y', 'de',
          'del', 'la', 'el', 'los', 'las', 'en', 'para', 'sl', 'slp', 'sa', 'slu', 'cb', 'group', 'grupo', 'and', 'tax',
          'partners', 'asociados', 'auditores', 'assessors', 'assessoria', 'e', 'i', 'a', 'autonomos'}


# ------------------------------------------------------------------ utilidades
def guardar(ruta, obj):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    open(ruta + '.tmp', 'w').write(json.dumps(obj, ensure_ascii=False))
    os.replace(ruta + '.tmp', ruta)


def ahora():
    if os.environ.get('RO_GBP_AHORA'):
        return dt.datetime.fromisoformat(os.environ['RO_GBP_AHORA']).replace(tzinfo=dt.timezone.utc)
    return dt.datetime.now(dt.timezone.utc)


def t(iso):
    if not iso:
        return None
    try:
        x = dt.datetime.fromisoformat(str(iso).replace('Z', '+00:00'))
        return x if x.tzinfo else x.replace(tzinfo=dt.timezone.utc)
    except Exception:
        return None


def dominio(u):
    return re.sub(r'^(https?://)?(www\.)?', '', str(u or '').strip().lower()).split('/')[0].split(':')[0]


def sin_tildes(s):
    return ''.join(c for c in unicodedata.normalize('NFD', str(s or '').lower()) if unicodedata.category(c) != 'Mn')


def fichas_nombre(s):
    return {w for w in re.findall(r'[a-z0-9]+', sin_tildes(s)) if w not in VACIAS and len(w) > 1}


def tel(s):
    d = re.sub(r'\D', '', str(s or ''))
    if d.startswith('0034'):
        d = d[4:]
    elif d.startswith('34') and len(d) == 11:
        d = d[2:]
    return d if len(d) == 9 else None


def limpio(s, tope=1500):
    """Texto de una reseña o respuesta, sin correos ni teléfonos (la puerta de secretos no los deja pasar)."""
    s = RX_CORREO.sub('[dato quitado]', str(s or ''))
    s = RX_TEL.sub('[dato quitado]', s)
    s = re.sub(r'\(Translated by Google\).*$|\(Traducido por Google\).*$', '', s, flags=re.S).strip()
    return s[:tope]


def pl(n, uno, varios=None):
    return f"{n} {uno if n == 1 else (varios or uno + 's')}"


def ref_resena(nombre):
    return 'r_' + hashlib.sha256(str(nombre).encode()).hexdigest()[:14]


def ref_ficha(nombre):
    return 'f_' + hashlib.sha256(str(nombre).encode()).hexdigest()[:10]


def leer_json(ruta, defecto=None):
    try:
        return json.load(open(ruta))
    except Exception:
        return defecto


# ------------------------------------------------------------------ clientes y sillas
def _telefonos(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and re.search(r'(?i)tel[eé]fono|phone|movil|m[oó]vil', k):
                n = tel(v)
                if n:
                    out.add(n)
            else:
                _telefonos(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _telefonos(v, out)


def clientes():
    out = []
    for f in sorted(glob.glob(os.path.join(APP, 'data', 'clientes', '*.json'))):
        c = leer_json(f)
        if not c or c.get('activo_libro') in ('Baja',):
            continue
        tels = set()
        _telefonos(c, tels)
        nombres = {c.get('nombre') or ''} | {v for v in (c.get('ids') or {}).values() if isinstance(v, str)}
        out.append({'id': c['id'], 'nombre': c.get('nombre'), 'web': dominio(c.get('web')), '_tels': tels,
                    '_fichas': [fichas_nombre(n) for n in nombres if fichas_nombre(n)]})
    return out


def sillas():
    """cliente_id → (seo/ficha de Google principal, account) desde la verdad única."""
    v = leer_json(os.path.join(APP, 'data', 'verdad', 'clientes.json'), {}) or {}
    out = {}
    for c in v.get('clientes') or []:
        eq = (c.get('equipo') or {}).get('seo') or []
        seo = (next((x for x in eq if x.get('principal')), eq[0]) if eq else {}).get('persona_id')
        out[c['cliente_id']] = {'seo_id': seo, 'account_id': c.get('account')}
    return out


def emparejar(l, cls, manual):
    """(cliente | None, motivos, confianza, candidatos). Manual > web y teléfono > nombre."""
    loc = l.get('name')
    if loc in manual:
        c = next((x for x in cls if x['id'] == manual[loc]), None)
        if c:
            return c, ['a mano (emparejar.json)'], 'alta', []
    web = dominio(l.get('websiteUri'))
    tels = {tel(x) for x in [((l.get('phoneNumbers') or {}).get('primaryPhone'))] + list((l.get('phoneNumbers') or {}).get('additionalPhones') or []) if tel(x)}
    nom = fichas_nombre(l.get('title'))
    puntos = []
    for c in cls:
        p, por = 0, []
        if web and c['web'] and (web == c['web'] or web.endswith('.' + c['web']) or c['web'].endswith('.' + web)):
            p += 3
            por.append('web')
        if tels and tels & c['_tels']:
            p += 3
            por.append('teléfono')
        mejor = 0.0
        for f in c['_fichas']:
            if f and f <= nom:
                mejor = max(mejor, 1.0)
            elif f and nom:
                mejor = max(mejor, len(f & nom) / len(f | nom))
        if mejor >= 1.0:
            p += 2
            por.append('nombre')
        elif mejor >= 0.5:
            p += 1
            por.append('nombre parecido')
        if p:
            puntos.append((p, c, por))
    puntos.sort(key=lambda x: -x[0])
    if not puntos or puntos[0][0] < 2:
        return None, [], None, [x[1]['id'] for x in puntos[:3]]
    if len(puntos) > 1 and puntos[1][0] == puntos[0][0]:
        return None, ['empate'], None, [x[1]['id'] for x in puntos[:3]]
    p, c, por = puntos[0]
    conf = 'alta' if p >= 3 else 'media'
    if web and c['web'] and 'web' not in por:
        conf = 'media'      # la web de la ficha no es la del cliente: revisar
    return c, por, conf, []


# ------------------------------------------------------------------ simulado (datos INVENTADOS para probar)
def simulado():
    a = ahora()
    iso = lambda h: (a - dt.timedelta(hours=h)).strftime('%Y-%m-%dT%H:%M:%SZ')
    cls = {c['id']: c for c in clientes()}
    elegidos = [x for x in ('musashi-consultores', 'oteca', 'ayg-asesores', 'garmande', 'lobo') if x in cls][:5]
    while len(elegidos) < 5 and len(elegidos) < len(cls):
        elegidos.append(next(k for k in cls if k not in elegidos))
    ubic, voz, gu, met, bus, res = [], {}, {}, {}, {}, {}
    hoy = a.date()

    def serie(base, cae=1.0):
        out = {}
        for i in range(1, 36):
            d = hoy - dt.timedelta(days=i)
            f = cae if i <= 7 else 1.0
            out[d.isoformat()] = max(0, int(round(base * f * (0.7 + 0.6 * ((i * 37) % 10) / 10))))
        return out

    for n, cid in enumerate(elegidos):
        c = cls[cid]
        loc = f'locations/{9000000000 + n}'
        cuenta = 'accounts/100000000000000000001'
        web = f"https://{c['web']}/" if c['web'] and n != 3 else 'https://otra-web-de-prueba.es/'
        titulo = (c['nombre'] or cid) + (' | Asesoría' if n % 2 else '')
        ubic.append({'name': loc, '_cuenta': cuenta, 'title': titulo, 'websiteUri': web,
                     'metadata': {'hasGoogleUpdated': n == 2, 'hasVoiceOfMerchant': n != 1, 'mapsUri': f'https://maps.google.com/?cid={n}',
                                  'newReviewUri': f'https://g.page/r/prueba{n}/review', 'placeId': f'PRUEBA{n}'},
                     'openInfo': {'status': 'OPEN'}, 'storefrontAddress': {'locality': 'Ciudad de prueba'}})
        voz[loc] = {'hasVoiceOfMerchant': n != 1, 'hasBusinessAuthority': n != 1,
                    **({'complyWithGuidelines': {'recommendationReason': 'BUSINESS_LOCATION_SUSPENDED'}} if n == 1 else {})}
        if n == 2:
            gu[loc] = {'diffMask': 'regularHours,websiteUri', 'pendingMask': ''}
        cae_llam = 0.5 if n == 0 else 1.0
        cae_rut = 0.2 if n == 2 else 1.0
        met[loc] = {'CALL_CLICKS': serie(4, cae_llam), 'WEBSITE_CLICKS': serie(6), 'BUSINESS_DIRECTION_REQUESTS': serie(3, cae_rut),
                    'BUSINESS_CONVERSATIONS': serie(0.4), 'BUSINESS_BOOKINGS': {},
                    'BUSINESS_IMPRESSIONS_MOBILE_SEARCH': serie(60), 'BUSINESS_IMPRESSIONS_DESKTOP_SEARCH': serie(25),
                    'BUSINESS_IMPRESSIONS_MOBILE_MAPS': serie(30), 'BUSINESS_IMPRESSIONS_DESKTOP_MAPS': serie(8)}
        bus[loc] = {'mes': (hoy.replace(day=1) - dt.timedelta(days=1)).strftime('%Y-%m'),
                    'terminos': [{'termino': 'asesoria cerca de mi', 'veces': 120 - 10 * n, 'menos_de': None},
                                 {'termino': (c['nombre'] or '').lower(), 'veces': 85, 'menos_de': None},
                                 {'termino': 'gestoria autonomos', 'veces': None, 'menos_de': 15}]}
        revs = [
            {'name': f'{cuenta}/{loc}/reviews/A{n}', 'reviewer': {'displayName': 'Persona de prueba A'}, 'starRating': 'FIVE',
             'comment': 'Muy buen trato y rapidez con la renta. Recomendable.', 'createTime': iso(30), 'updateTime': iso(30),
             'reviewReply': {'comment': 'Gracias por tu confianza.', 'updateTime': iso(20)}},
            {'name': f'{cuenta}/{loc}/reviews/B{n}', 'reviewer': {'displayName': 'Persona de prueba B'}, 'starRating': 'FOUR',
             'comment': 'Bien en general, aunque tardaron en contestar un correo.', 'createTime': iso(50), 'updateTime': iso(50)},
        ]
        if n in (0, 2, 4):
            revs.append({'name': f'{cuenta}/{loc}/reviews/C{n}', 'reviewer': {'displayName': 'Persona de prueba C'},
                         'starRating': ['ONE', 'TWO', 'THREE'][n // 2],
                         'comment': 'Me cobraron una cuota que no esperaba y nadie me llamó (escribidme a prueba@ejemplo.es o al ' + '6' + '00 000 000).',
                         'createTime': iso(40 if n != 4 else 6), 'updateTime': iso(40 if n != 4 else 6)})
        if n == 0:
            revs.append({'name': f'{cuenta}/{loc}/reviews/D{n}', 'reviewer': {'isAnonymous': True}, 'starRating': 'TWO',
                         'comment': '', 'createTime': iso(24 * 200), 'updateTime': iso(24 * 200)})
        res[loc] = {'media': round(sum(ESTRELLAS[r['starRating']] for r in revs) / len(revs), 1), 'total': len(revs) + 20, 'reviews': revs}
    # una ficha sin cliente
    ubic.append({'name': 'locations/9999999999', '_cuenta': 'accounts/100000000000000000001', 'title': 'Ficha de prueba sin cliente',
                 'websiteUri': 'https://sin-cliente-prueba.es/', 'metadata': {'hasVoiceOfMerchant': True}, 'openInfo': {'status': 'OPEN'}})
    return {'leido': a.strftime('%Y-%m-%d %H:%M'), '_simulado': True, 'cuentas': [{'name': 'accounts/100000000000000000001', 'accountName': 'Cuenta de prueba', 'type': 'PERSONAL', 'role': 'MANAGER'}],
            'ubicaciones': ubic, 'voz': voz, 'google_actualizo': gu, 'metricas': met, 'busquedas': bus, 'resenas': res, 'errores': {}}


# ------------------------------------------------------------------ lectura
def leer():
    if '--simulado' in sys.argv:
        return simulado()
    if '--desde-cache' in sys.argv:
        d = leer_json(CACHE)
        return d if d else {'_sin_clave': 'No hay lectura guardada de Business Profile.'}
    sys.path.insert(0, HERR)
    try:
        import gbp  # noqa: E402
    except ImportError:
        return {'_sin_clave': 'No está el lector ~/RO_HERRAMIENTAS/google/gbp.py en este equipo.'}
    try:
        d = gbp.volcar()
    except gbp.SinClave as e:
        return {'_sin_clave': str(e)}
    except gbp.PendienteAprobacion as e:
        return {'_pendiente': str(e)}
    except gbp.LlaveMala as e:
        return {'_llave_mala': str(e)}
    except gbp.GBPError as e:
        return {'_error': str(e)}
    except Exception as e:  # noqa: BLE001 · red caída, etc.
        return {'_error': f'{type(e).__name__}'}
    guardar(CACHE, d)
    return d


def cuenta_que_gestiona():
    """Lo que se sabe hoy (sin la API) de qué cuenta gestiona las fichas: de la lectura del 3-oct (Metricool y SE Ranking)."""
    return {'probable': 'la cuenta gmb1 de RO (la misma de Analytics y Search Console): sin confirmar',
            'pistas': ['Metricool: las fichas de Oteca y AyG cuelgan de la MISMA cuenta de Google (accounts/107856548535336564170): una sola cuenta gestiona varias fichas de clientes.',
                       'SE Ranking (local): 3 fichas conectadas por Jerónimo con su conexión de Google (Musashi, CLCripto, QualityConta).',
                       'El correo de esa cuenta de Google no sale en ninguna de las dos: lo confirma Tomás entrando en business.google.com/locations con la cuenta gmb1.'],
            'como_confirmar': 'Entrar en https://business.google.com/locations con la cuenta gmb1 de RO y mirar cuántas fichas salen y con qué rol (propietario o gestor).'}


def no_conectado(estado, motivo):
    titular = {'pendiente_aprobacion': TITULAR_PENDIENTE, 'llave_mala': 'La llave de Google no vale',
               'error': 'Google no responde'}.get(estado, TITULAR_PENDIENTE)
    return {'_meta': {'generado': dt.datetime.now().strftime('%Y-%m-%d %H:%M'), 'fuente': 'Google Business Profile · API oficial (solo lectura)',
                      'estado': estado, 'titular': titular, 'motivo': motivo,
                      'texto': f'{titular} · {QUE_HACER[0].lower() + QUE_HACER[1:]}',
                      'que_hacer': QUE_HACER, 'pasos': PASOS, 'doc_api': DOC_API, 'formulario': FORMULARIO, 'enlace': ENLACE,
                      'cuenta_que_gestiona': cuenta_que_gestiona(),
                      'nota': 'La app solo LEE la ficha de Google. Responder una reseña va en simulación (cola de acciones, interruptor apagado).'},
            'resumen': None, 'clientes': [], 'sin_cliente': [], 'clientes_sin_ficha': [], 'alertas': []}


# ------------------------------------------------------------------ construir
def sumar(serie, desde, hasta):
    return sum(v for f, v in (serie or {}).items() if desde <= f <= hasta)


def construir(d):
    a = ahora()
    hoy_txt = dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    cls = clientes()
    sil = sillas()
    manual = (leer_json(MANUAL, {}) or {}).get('fichas') or {}
    alertas = []

    def incid(regla, grav, titulo, texto, que_hacer, *, cid, objeto, desde=None, cifra=None, extra=None):
        x = {'id': f'gbp:{regla}:{objeto}', 'departamento': 'seo', 'regla': regla, 'gravedad': grav, 'cliente_id': cid,
             'objeto': objeto, 'titulo': titulo, 'texto': texto, 'que_hacer': que_hacer, 'fuente': 'Google Business Profile',
             'fuente_enlace': ENLACE, 'detectado': hoy_txt, 'desde': desde, 'cifra': cifra}
        if cid:
            x.update({'dueno_id': (sil.get(cid) or {}).get('seo_id'), 'copia_a': [p for p in [(sil.get(cid) or {}).get('account_id')] if p]})
        if extra:
            x.update(extra)
        alertas.append(x)
        return x

    por_cli, sin_cliente = {}, []
    for l in d.get('ubicaciones') or []:
        loc = l.get('name')
        fid = ref_ficha(loc)
        c, por, conf, cand = emparejar(l, cls, manual)
        cid = c['id'] if c else None
        nombre_ficha = l.get('title') or loc
        mot = []                                                   # (gravedad, texto)
        meta = l.get('metadata') or {}
        # ---- estado de la ficha
        v = (d.get('voz') or {}).get(loc) or {}
        motivo_g = ((v.get('complyWithGuidelines') or {}).get('recommendationReason'))
        estado_g = 'bien'
        if motivo_g in ('BUSINESS_LOCATION_SUSPENDED', 'BUSINESS_LOCATION_DISABLED'):
            estado_g = 'suspendida' if motivo_g.endswith('SUSPENDED') else 'deshabilitada'
            mot.append(('rojo', f'Ficha {estado_g} por Google'))
            incid('perfil_suspendido', 'rojo', f'Ficha de Google {estado_g}', f'{nombre_ficha}: Google la da como {estado_g}. No sale en Maps ni en la búsqueda con normalidad.',
                  'Revisar en business.google.com el aviso de Google y pedir el restablecimiento. Lo lleva SEO/ficha de Google; el account avisa al cliente.',
                  cid=cid, objeto=fid)
        elif v and not v.get('hasVoiceOfMerchant'):
            estado_g = 'sin_control'
            que = ('verificación pendiente' if v.get('verify') else 'en revisión de Google' if 'waitForVoiceOfMerchant' in v
                   else 'conflicto de propiedad (ficha duplicada)' if v.get('resolveOwnershipConflict') else 'sin control del negocio')
            mot.append(('ambar', f'Google no da el control de la ficha: {que}'))
            incid('perfil_suspendido', 'ambar', 'Ficha de Google sin control', f'{nombre_ficha}: {que}. Los cambios no se publican.',
                  'Revisar en business.google.com qué pide Google (verificar, esperar o reclamar la propiedad).', cid=cid, objeto=fid)
        gu = (d.get('google_actualizo') or {}).get(loc)
        cambiados = [CAMPOS_GOOGLE.get(x.split('.')[0], x) for x in (gu or {}).get('diffMask', '').split(',') if x]
        if meta.get('hasGoogleUpdated') or cambiados:
            txt = ', '.join(dict.fromkeys(cambiados)) or 'algún dato'
            mot.append(('ambar', f'Google ha cambiado datos de la ficha ({txt})'))
            incid('datos_cambiados', 'ambar', 'Google ha cambiado datos de la ficha', f'{nombre_ficha}: Google ha cambiado {txt} por su cuenta.',
                  'Comprobar en business.google.com si el cambio es correcto; si no, corregirlo (Google lo hace con sugerencias de usuarios).',
                  cid=cid, objeto=fid, extra={'campos': cambiados})
        abierto = (l.get('openInfo') or {}).get('status')
        if abierto in ('CLOSED_PERMANENTLY', 'CLOSED_TEMPORARILY'):
            g = 'rojo' if abierto == 'CLOSED_PERMANENTLY' else 'ambar'
            txt = 'cerrada definitivamente' if g == 'rojo' else 'cerrada temporalmente'
            mot.append((g, f'Ficha marcada como {txt}'))
            incid('perfil_suspendido', g, f'Ficha marcada como {txt}', f'{nombre_ficha}: la ficha dice «{txt}».',
                  'Si el despacho está abierto, corregirlo YA en business.google.com.', cid=cid, objeto=fid + ':abierto')
        # ---- rendimiento
        m = (d.get('metricas') or {}).get(loc) or {}
        fechas = sorted({f for s in m.values() for f in (s or {})})
        rend = None
        if fechas:
            ult = dt.date.fromisoformat(fechas[-1])
            s_ini, s_fin = (ult - dt.timedelta(days=6)).isoformat(), ult.isoformat()
            a_ini, a_fin = (ult - dt.timedelta(days=13)).isoformat(), (ult - dt.timedelta(days=7)).isoformat()

            def bloque(i, f):
                return {'llamadas': sumar(m.get('CALL_CLICKS'), i, f), 'clics_web': sumar(m.get('WEBSITE_CLICKS'), i, f),
                        'rutas': sumar(m.get('BUSINESS_DIRECTION_REQUESTS'), i, f), 'mensajes': sumar(m.get('BUSINESS_CONVERSATIONS'), i, f),
                        'reservas': sumar(m.get('BUSINESS_BOOKINGS'), i, f),
                        'vistas_busqueda': sumar(m.get('BUSINESS_IMPRESSIONS_MOBILE_SEARCH'), i, f) + sumar(m.get('BUSINESS_IMPRESSIONS_DESKTOP_SEARCH'), i, f),
                        'vistas_maps': sumar(m.get('BUSINESS_IMPRESSIONS_MOBILE_MAPS'), i, f) + sumar(m.get('BUSINESS_IMPRESSIONS_DESKTOP_MAPS'), i, f)}
            sem, ant = bloque(s_ini, s_fin), bloque(a_ini, a_fin)
            for b in (sem, ant):
                b['vistas'] = b['vistas_busqueda'] + b['vistas_maps']
            var = {k: (round(100 * (sem[k] - ant[k]) / ant[k]) if ant[k] else None) for k in sem}
            dias = [{'fecha': f, 'llamadas': (m.get('CALL_CLICKS') or {}).get(f, 0), 'clics_web': (m.get('WEBSITE_CLICKS') or {}).get(f, 0),
                     'rutas': (m.get('BUSINESS_DIRECTION_REQUESTS') or {}).get(f, 0),
                     'vistas': sum((m.get(k) or {}).get(f, 0) for k in m if k.startswith('BUSINESS_IMPRESSIONS'))} for f in fechas[-28:]]
            rend = {'ultimo_dia': s_fin, 'semana': {'desde': s_ini, 'hasta': s_fin, **sem}, 'semana_anterior': {'desde': a_ini, 'hasta': a_fin, **ant},
                    'variacion_pct': var, 'dias': dias, 'nota': 'Google da el rendimiento con unos días de retraso: la semana es la de los últimos 7 días con dato.'}
            for k, nombre in (('llamadas', 'Llamadas'), ('rutas', 'Rutas')):
                if ant[k] >= CAIDA_BASE_MIN and var[k] is not None and var[k] <= -CAIDA_PCT:
                    g = 'rojo' if var[k] <= -CAIDA_ROJO_PCT else 'ambar'
                    mot.append((g, f'{nombre} desde la ficha: {sem[k]} frente a {ant[k]} la semana anterior ({var[k]} %)'))
                    incid('caida_' + k, g, f'Caída de {nombre.lower()} desde la ficha de Google',
                          f'{nombre_ficha}: {sem[k]} {nombre.lower()} del {s_ini[8:]}/{s_ini[5:7]} al {s_fin[8:]}/{s_fin[5:7]} frente a {ant[k]} la semana anterior ({var[k]} %).',
                          'Mirar si ha cambiado algo en la ficha (horario, teléfono, categoría, reseñas recientes) o si Google la ha bajado; contrastar con Search Console.',
                          cid=cid, objeto=f'{fid}:{k}', cifra=var[k], desde=s_fin)
        # ---- búsquedas
        bq = (d.get('busquedas') or {}).get(loc) or {}
        terminos = sorted(bq.get('terminos') or [], key=lambda x: -(x.get('veces') or 0))[:15]
        # ---- reseñas
        r = (d.get('resenas') or {}).get(loc) or {}
        lista, por_resp = [], []
        viejas_malas = 0
        for x in r.get('reviews') or []:
            est = ESTRELLAS.get(x.get('starRating'))
            cre = t(x.get('updateTime') or x.get('createTime'))
            rep = x.get('reviewReply') or {}
            horas = round((a - cre).total_seconds() / 3600, 1) if cre else None
            rr = {'id': ref_resena(x.get('name')), 'ref': x.get('name'), 'estrellas': est, 'texto': limpio(x.get('comment')),
                  'autor': 'Anónimo' if (x.get('reviewer') or {}).get('isAnonymous') else limpio((x.get('reviewer') or {}).get('displayName') or 'Sin nombre', 80),
                  'fecha': x.get('createTime'), 'editada': x.get('updateTime') if x.get('updateTime') != x.get('createTime') else None,
                  'respondida': bool(rep), 'respuesta': {'texto': limpio(rep.get('comment')), 'fecha': rep.get('updateTime'),
                                                         'estado': rep.get('reviewReplyState')} if rep else None,
                  'horas_sin_responder': None if rep else horas, 'ficha_id': fid}
            lista.append(rr)
            if not rep:
                por_resp.append(rr)
                if est and est <= RESENA_MALA:
                    if horas is not None and horas > 24 * RESENA_DIAS_ALERTA:
                        viejas_malas += 1
                        continue
                    g = 'rojo' if (horas or 0) >= RESENA_PLAZO_H else 'ambar'
                    rr['alerta'] = g
                    incid('resena_mala', g, f'Reseña de {est} estrella{"s" if est != 1 else ""} sin responder',
                          f'{nombre_ficha}: reseña de {est}★ de hace {int(horas // 24)} días' if horas and horas >= 48 else
                          f'{nombre_ficha}: reseña de {est}★ de hace {int(horas or 0)} h sin responder.',
                          'Proponer respuesta desde la app (SEO › Ficha de Google o la ficha del cliente), revisarla con el account y publicarla. '
                          'Sin confirmar que es cliente ni dar datos suyos (secreto profesional).',
                          cid=cid, objeto=rr['id'], desde=x.get('createTime'), cifra=est,
                          extra={'resena_id': rr['id'], 'vence': (cre + dt.timedelta(hours=RESENA_PLAZO_H)).strftime('%Y-%m-%d %H:%M') if cre else None})
        por_resp.sort(key=lambda z: ((z['estrellas'] or 5), -(z['horas_sin_responder'] or 0)))
        if viejas_malas:
            mot.append(('ambar', f'{pl(viejas_malas, "reseña mala antigua", "reseñas malas antiguas")} sin responder (más de {RESENA_DIAS_ALERTA} días)'))
        malas_rec = [z for z in por_resp if z.get('alerta')]
        if malas_rec:
            mot.append(('rojo' if any(z['alerta'] == 'rojo' for z in malas_rec) else 'ambar', f'{pl(len(malas_rec), "reseña")} de 1-3★ sin responder'))
        res = {'media': r.get('media'), 'total': r.get('total'), 'sin_responder': len(por_resp), 'malas_sin_responder': len(malas_rec),
               'malas_antiguas_sin_responder': viejas_malas, 'por_responder': por_resp[:30], 'ultimas': lista[:10],
               'enlace_resenas': meta.get('newReviewUri')}
        orden = {'rojo': 3, 'ambar': 2}
        ficha = {'ficha_id': fid, 'ubicacion': loc, 'cuenta': l.get('_cuenta'), 'nombre': nombre_ficha, 'web': dominio(l.get('websiteUri')) or None,
                 'localidad': (l.get('storefrontAddress') or {}).get('locality'), 'maps': meta.get('mapsUri'),
                 'estado_google': estado_g, 'abierta': abierto, 'google_cambio': cambiados, 'emparejado_por': por, 'confianza': conf,
                 'estado': max([g for g, _ in mot], key=lambda g: orden[g], default='verde'),
                 'motivos': [x for _, x in sorted(mot, key=lambda z: -orden[z[0]])] or ['Todo en orden en la ficha de Google'],
                 'rendimiento': rend, 'busquedas': {'mes': bq.get('mes'), 'terminos': terminos}, 'resenas': res}
        if c:
            f = por_cli.setdefault(cid, {'cliente_id': cid, 'cliente': c['nombre'], **(sil.get(cid) or {'seo_id': None, 'account_id': None}), 'fichas': []})
            f['fichas'].append(ficha)
        else:
            sin_cliente.append({**{k: ficha[k] for k in ('ficha_id', 'ubicacion', 'nombre', 'web', 'localidad', 'estado', 'motivos')},
                                'candidatos': cand, 'como_emparejar': f'Añadir «"{loc}": "<cliente_id>"» en fuentes_gbp/emparejar.json'})
    orden = {'rojo': 0, 'ambar': 1, 'verde': 2}
    cl = []
    for f in por_cli.values():
        g = [x['estado'] for x in f['fichas']]
        f['estado'] = 'rojo' if 'rojo' in g else 'ambar' if 'ambar' in g else 'verde'
        f['motivos'] = [m for x in f['fichas'] for m in x['motivos'] if not m.startswith('Todo en orden')] or ['Todo en orden en la ficha de Google']
        f['resenas_por_responder'] = sum(x['resenas']['sin_responder'] for x in f['fichas'])
        f['resenas_malas_sin_responder'] = sum(x['resenas']['malas_sin_responder'] for x in f['fichas'])
        cl.append(f)
    cl.sort(key=lambda f: (orden[f['estado']], f['cliente'] or ''))
    con_ficha = {f['cliente_id'] for f in cl}
    sin_ficha = [{'cliente_id': c['id'], 'cliente': c['nombre']} for c in cls if c['id'] not in con_ficha]
    resumen = {'cuentas': len(d.get('cuentas') or []), 'fichas': len(d.get('ubicaciones') or []), 'clientes_con_ficha': len(cl),
               'clientes_sin_ficha': len(sin_ficha), 'fichas_sin_cliente': len(sin_cliente),
               'clientes_rojo': sum(f['estado'] == 'rojo' for f in cl), 'clientes_ambar': sum(f['estado'] == 'ambar' for f in cl),
               'resenas_por_responder': sum(f['resenas_por_responder'] for f in cl), 'resenas_malas_sin_responder': sum(f['resenas_malas_sin_responder'] for f in cl),
               'alertas': len(alertas), 'alertas_rojas': sum(x['gravedad'] == 'rojo' for x in alertas)}
    return {'_meta': {'generado': dt.datetime.now().strftime('%Y-%m-%d %H:%M'), 'leido': d.get('leido'),
                      'fuente': 'Google Business Profile · API oficial (solo lectura)', 'estado': 'simulado' if d.get('_simulado') else 'conectado',
                      'titular': 'Datos inventados de prueba' if d.get('_simulado') else 'Conectado', 'doc_api': DOC_API, 'enlace': ENLACE,
                      'errores_parciales': d.get('errores') or {}, 'umbrales': {'resena_mala_estrellas': RESENA_MALA, 'resena_plazo_h': RESENA_PLAZO_H,
                      'resena_dias_alerta': RESENA_DIAS_ALERTA, 'caida_pct': CAIDA_PCT, 'caida_rojo_pct': CAIDA_ROJO_PCT, 'caida_base_min': CAIDA_BASE_MIN},
                      'nota': 'La app solo LEE la ficha de Google. Responder una reseña va en simulación (cola de acciones, interruptor apagado).'},
            'resumen': resumen, 'clientes': cl, 'sin_cliente': sin_cliente, 'clientes_sin_ficha': sin_ficha, 'alertas': alertas}


def main():
    d = leer()
    previo = leer_json(SALIDA, {}) or {}
    if '_sin_clave' in d:
        out = no_conectado('pendiente_aprobacion', d['_sin_clave'])
    elif '_pendiente' in d:
        out = no_conectado('pendiente_aprobacion', d['_pendiente'])
    elif '_llave_mala' in d:
        out = no_conectado('llave_mala', d['_llave_mala'])
    elif '_error' in d:
        if (previo.get('_meta') or {}).get('estado') == 'conectado':     # último dato bueno, marcado como viejo
            previo['_meta'].update({'dato_viejo': True, 'error': d['_error'], 'error_hora': dt.datetime.now().strftime('%Y-%m-%d %H:%M')})
            out = previo
        else:
            out = no_conectado('error', 'Google Business Profile respondió con error: ' + d['_error'])
    else:
        out = construir(d)
    destino = sys.argv[sys.argv.index('--salida') + 1] if '--salida' in sys.argv else SALIDA
    if out['_meta']['estado'] == 'simulado' and os.path.abspath(destino) == os.path.abspath(SALIDA):
        sys.exit('--simulado escribe solo con --salida <fichero> (los datos inventados nunca van a data/).')
    guardar(destino, out)
    r = out.get('resumen')
    print(f"{os.path.relpath(destino, APP) if destino.startswith(APP) else destino} · {out['_meta']['estado']}"
          + (f" · {r}" if r else f" · {out['_meta'].get('texto')}"))


if __name__ == '__main__':
    main()
