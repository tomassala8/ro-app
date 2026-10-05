#!/usr/bin/env python3
"""M24 · Chat del equipo · genera data/chat_equipo/p_<persona>.json · SOLO LECTURA de ClickUp (API v3 de chat).

Fuente: la llave propia de ClickUp del llavero (clickup_api_token, la de ~/RO_HERRAMIENTAS/clickup_api/chat.py).
NUNCA el conector de ClickUp de Claude (cupo de 2.500 llamadas al día para todo el workspace).

Qué lee (solo GET):
  · /api/v2/team                                   → miembros del workspace (nombre y correo → persona de la app)
  · /api/v3/workspaces/{ws}/chat/channels          → canales, mensajes directos (DM) y grupos (GROUP_DM)
  · /api/v3/…/chat/channels/{id}/members           → quién está en cada canal (cada persona ve SOLO los suyos)
  · /api/v3/…/chat/channels/{id}/messages          → últimos 40 mensajes de cada canal interno con actividad (120 días)
  · /api/v3/…/chat/messages/{id}/replies           → hilos (hasta 10 por canal, 25 respuestas cada uno)

Qué NO entra:
  · Canales de clientes (ya están en la pestaña Chat de la ficha del cliente, M4).
  · Mensajes directos de otras personas: la llave es de Tomás, así que la API solo da LOS SUYOS → van solo a p_tomas.json.
  · Correos, teléfonos y contraseñas de enlaces (pwd=…) dentro de los textos.
  · Contraseñas y usuarios escritos en el texto («Contraseña: …», «clave: …»): se tapan con «•••• (tapada)».
    Sin red: `python3 generar_chat_equipo.py --solo-tapar` aplica el tapado a los ficheros ya generados.
  · Estado de «leído» por persona: la API con una sola llave no lo da (llega con OAuth por usuario en W1). La app cuenta
    como «no leído» lo que llegó después de tu última visita a la pantalla.

Salida: un fichero por persona (data/chat_equipo/p_<id>.json) con filas que llevan persona_id = esa persona, para que
servir.py lo recorte (regla horas_persona). La pantalla solo pide el de la persona vista. Ver _ESTADO_chat_equipo.md.
"""
import datetime as dt, json, os, re, subprocess, sys, time, unicodedata, urllib.request
from zoneinfo import ZoneInfo

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
DATA = os.path.join(RAIZ, 'data')
SAL = os.path.join(DATA, 'chat_equipo')
WS = '90152357276'
MAD = ZoneInfo('Europe/Madrid')
AHORA = dt.datetime.now(MAD)
LIMITE_DIAS = 120

# M4 (auditoría final, punto 9) · contraseñas y credenciales: el tapado vive en tapado.py (N15: lo usan también los
# canales y grupos de la app, avisos.py). Mismas expresiones de siempre.
sys.path.insert(0, AQUI)
from tapado import TAPADA, tapar, tapar_todo  # noqa: E402,F401
from partir_chat import partir  # noqa: E402  (N15 · velocidad: índice ligero por persona + un fichero por canal)
import pathlib as _pl_l27, sys as _sys_l27  # L-27: rutas del Mac por config.py
if str(_pl_l27.Path(__file__).resolve().parents[1]) not in _sys_l27.path:
    _sys_l27.path.append(str(_pl_l27.Path(__file__).resolve().parents[1]))
import config as _cfg  # noqa: E402


if __name__ == '__main__' and '--solo-tapar' in sys.argv:
    # Sin red y sin llave: aplica el mismo tapado a los ficheros ya generados en data/chat_equipo/.
    n = 0
    for f in sorted(os.listdir(SAL)) if os.path.isdir(SAL) else []:
        if not f.endswith('.json'): continue
        p = os.path.join(SAL, f)
        doc = json.load(open(p, encoding='utf-8'))
        nuevo = tapar_todo(doc)
        if nuevo != doc:
            json.dump(nuevo, open(p, 'w', encoding='utf-8'), ensure_ascii=False); n += 1
    priv = os.path.join(SAL, '_privado')
    for f in sorted(os.listdir(priv)) if os.path.isdir(priv) else []:
        if not f.endswith('.json'): continue
        p = os.path.join(priv, f)
        doc = json.load(open(p, encoding='utf-8'))
        nuevo = tapar_todo(doc)
        if nuevo != doc:
            json.dump(nuevo, open(p, 'w', encoding='utf-8'), ensure_ascii=False); n += 1
    print(f'chat del equipo · tapado aplicado sin red · ficheros cambiados: {n}')
    sys.exit(0)

T = subprocess.check_output(['security', 'find-generic-password', '-s', 'clickup_api_token', '-w'], text=True).strip()
LLAMADAS = 0


CACHE_F = os.environ.get('RO_CHAT_CACHE')          # solo para desarrollo: guarda las respuestas GET y no repite llamadas
CACHE = json.load(open(CACHE_F)) if CACHE_F and os.path.exists(CACHE_F) else {}


def g(url):
    if url in CACHE: return CACHE[url]
    r = _g(url)
    if CACHE_F and not r.get('_error'): CACHE[url] = r
    return r


def _g(url):
    global LLAMADAS
    LLAMADAS += 1
    for intento in range(3):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'Authorization': T}), timeout=60))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(5 * (intento + 1)); continue
            return {'_error': e.code}
        except Exception as e:
            if intento == 2: return {'_error': str(e)}
            time.sleep(2)
    return {'_error': 'reintentos'}


def norm(x):
    x = unicodedata.normalize('NFD', str(x or '').lower())
    return re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in x if not unicodedata.combining(c))).strip()


STOP = {'asesores', 'asesoria', 'consulting', 'consultores', 'grup', 'grupo', 'gestoria', 'ranking', 'online', 'tareas', 'lista',
        'onboarding', 'cliente', 'clientes', 'email', 'whatsapp', 'advisory', 'partners', 'economistes', 'assessors', 'gestor', 'and',
        'gestion', 'fiscal', 'laboral', 'contable', 'empresas', 'autonomos', 'administrativa', 'investment', 'economistas', 'advocats',
        'assessoria', 'consult', 'tarinas'}
def toks(s): return {t for t in norm(s).split() if len(t) >= 3 and t not in STOP}

RX_CORREO = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')
RX_TEL = re.compile(r'(?<![\w/])(?:\+34[\s.-]?|0034[\s.-]?)?[6789]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}(?![\w/])')
RX_MENCION = re.compile(r'\[@([^\]]+)\]\(#user_mention#(\d+)\)')
RX_GRUPO = re.compile(r'\[@([^\]]+)\]\(#[a-z_]*group_mention#[^)]*\)')
RX_SECRETO_URL = re.compile(r'(?i)([?&])(pwd|token|key|password|secret|access_token)=[^&\s)\]]+')


def limpio(t):
    t = str(t or '').encode('utf-16', 'surrogatepass').decode('utf-16', 'replace')   # emojis partidos de la API
    t = RX_GRUPO.sub(r'@\1', RX_MENCION.sub(r'@\1', str(t or '')))
    t = RX_SECRETO_URL.sub(r'\1\2=…', t)
    t = tapar(t)
    t = RX_CORREO.sub('[correo]', t)
    t = RX_TEL.sub('[teléfono]', t)
    t = t.replace('\\_', '_')
    return t[:900]


# ------------------------------------------------------------------ personas y clientes
PERSONAS = json.load(open(os.path.join(DATA, 'personas.json')))
ACTIVAS = {p['id'] for p in PERSONAS if p.get('activo') or p.get('estado') in ('activo', 'por_incorporar')}
def persona_de(correo, nombre):
    loc = (correo or '').split('@')[0].lower()
    for p in PERSONAS:
        for c in [p.get('correo')] + list(p.get('otros_correos') or []):
            if c and c.split('@')[0].lower() == loc:
                return p['id']
    n = norm(nombre)
    for p in PERSONAS:
        pn = norm(p['nombre'])
        if n and (pn == n or (n.split()[0] == pn.split()[0] and (len(n.split()) == 1 or n.split()[-1] in pn))):
            return p['id']
    return None

CLIENTES = json.load(open(os.path.join(DATA, 'clientes.json')))
nombres = {c['id']: {c['nombre']} for c in CLIENTES}
try:
    for portal, app in json.load(open(os.path.join(DATA, 'ids_clientes.json')))['portal_a_app'].items():
        if app in nombres: nombres[app].add(portal.replace('-', ' '))
    for cid, e in json.load(open(os.path.join(DATA, 'emparejamientos.json')))['clientes'].items():
        if cid in nombres and (e.get('ghl') or {}).get('nombre'): nombres[cid].add(e['ghl']['nombre'])
except Exception:
    pass
VARIANTES = {cid: [t for t in (toks(n) for n in ns) if t and len(t) <= 3] for cid, ns in nombres.items()}
# Clientes que ya no están en la app (bajas) pero cuyo canal sigue: también son «de cliente», no internos
EXTRA_CLIENTES = {'taller del patinete', 'cromomedia', 'pummba', 'qualityconta', 'medalva', 'gemap', 'clcripto', 'cl cripto', 'uhy',
                  'tributaley', 'ocps', 'ennumera', 'j d consulting', 'plan marzo a marzo', 'planmarzoamarzo', 'consulting f'}
try:
    POR_CLIENTE_M4 = set(json.load(open(str(_cfg.HERRAMIENTA_RO / 'chat.json')))['porcliente'].values())
except Exception:
    POR_CLIENTE_M4 = set()


def es_de_cliente(canal):
    n = canal.get('name') or ''
    if canal['id'] in POR_CLIENTE_M4: return True
    t = toks(n)
    if any(v <= t for vs in VARIANTES.values() for v in vs): return True
    nn = norm(n)
    if any(x in nn for x in EXTRA_CLIENTES): return True
    if re.match(r'(?i)^(tareas|onboarding|lista de)\b', n.strip()) and not re.search(r'(?i)ranking|rrhh|prospecci|generales|organizaci', n):
        return True
    return False


# ------------------------------------------------------------------ lectura
print(f'M24 · chat del equipo · {AHORA:%Y-%m-%d %H:%M} · solo lectura con la llave propia de ClickUp')
equipo = {}
for t in g('https://api.clickup.com/api/v2/team').get('teams', []):
    if str(t['id']) == WS:
        for m in t.get('members', []):
            u = m['user']
            equipo[str(u['id'])] = {'nombre': u.get('username') or (u.get('email') or '').split('@')[0], 'correo': u.get('email'),
                                    'pid': persona_de(u.get('email'), u.get('username')), 'ini': u.get('initials')}

canales, cur = [], ''
while True:
    r = g(f'https://api.clickup.com/api/v3/workspaces/{WS}/chat/channels?limit=100&include_hidden=true' + (f'&cursor={cur}' if cur else ''))
    if r.get('_error'): sys.exit(f'ClickUp no da los canales: {r}')
    canales += r.get('data', []); cur = r.get('next_cursor')
    if not cur: break

corte = (AHORA - dt.timedelta(days=LIMITE_DIAS)).timestamp() * 1000
internos, de_cliente, directos, dormidos = [], 0, [], 0
for c in canales:
    if c.get('archived'): continue
    if c.get('type') in ('DM', 'GROUP_DM'):
        if (c.get('latest_comment_at') or 0) >= corte: directos.append(c)
        continue
    if es_de_cliente(c):
        de_cliente += 1; continue
    if (c.get('latest_comment_at') or 0) < corte:
        dormidos += 1; continue
    internos.append(c)


def miembros(cid):
    out, cur = [], ''
    while True:
        r = g(f'https://api.clickup.com/api/v3/workspaces/{WS}/chat/channels/{cid}/members?limit=100' + (f'&cursor={cur}' if cur else ''))
        out += r.get('data', []); cur = r.get('next_cursor')
        if not cur or r.get('_error'): return out


def ms_iso(ms):
    return dt.datetime.fromtimestamp(int(ms) / 1000, MAD).strftime('%Y-%m-%d %H:%M') if ms else None


def mensaje(m):
    u = equipo.get(str(m.get('user_id')), {})
    contenido = m.get('content') or ''
    ids = [y for _, y in RX_MENCION.findall(contenido)]
    menc = sorted({equipo.get(x, {}).get('pid') for x in ids} - {None})
    return {'id': m['id'], 'autor': u.get('nombre') or 'Alguien', 'autor_pid': u.get('pid'), 'fecha': ms_iso(m.get('date')),
            'texto': limpio(contenido), 'menciones': menc, 'a_todos': bool(RX_GRUPO.search(contenido)),
            'n_respuestas': m.get('replies_count') or 0, 'resuelto': bool(m.get('resolved'))}


salida_canales = []
for c in internos + directos:
    mm = miembros(c['id'])
    gente = [{'nombre': x.get('name') or x.get('username'), 'pid': equipo.get(str(x['id']), {}).get('pid') or persona_de(x.get('email'), x.get('name')),
              'ini': x.get('initials')} for x in mm]
    r = g(f"https://api.clickup.com/api/v3/workspaces/{WS}/chat/channels/{c['id']}/messages?limit=40")
    msgs = [mensaje(m) for m in r.get('data', []) if m.get('type', 'message') == 'message']
    hilos = 0
    for x in msgs:
        if x['n_respuestas'] and hilos < 10:
            rr = g(f"https://api.clickup.com/api/v3/workspaces/{WS}/chat/messages/{x['id']}/replies?limit=25")
            x['respuestas'] = sorted([mensaje(y) for y in rr.get('data', [])], key=lambda y: y['fecha'] or '')
            hilos += 1
    msgs.sort(key=lambda x: x['fecha'] or '')
    if c.get('type') == 'CHANNEL':
        nombre, tipo = (c.get('name') or 'Canal').strip(), 'canal'
    else:
        otros = [x['nombre'] for x in gente if x['pid'] != 'tomas'] or ['Tomás']
        nombre, tipo = ', '.join(otros[:4]) + (f' y {len(otros) - 4} más' if len(otros) > 4 else ''), ('directo' if c.get('type') == 'DM' else 'grupo')
    salida_canales.append({'id': c['id'], 'nombre': nombre, 'tipo': tipo, 'privado': c.get('visibility') == 'PRIVATE',
                           'descripcion': limpio(c.get('description') or '')[:200], 'ultimo': ms_iso(c.get('latest_comment_at')),
                           'miembros': gente, 'n_miembros': len(gente), 'mensajes': msgs,
                           'enlace': f"https://app.clickup.com/{WS}/chat/r/{c['id']}"})

def sano(o):
    """Emojis partidos que devuelve la API (sustitutos sueltos) → carácter de reemplazo, en todo el documento."""
    if isinstance(o, dict): return {k: sano(v) for k, v in o.items()}
    if isinstance(o, list): return [sano(v) for v in o]
    if isinstance(o, str): return o.encode('utf-16', 'surrogatepass').decode('utf-16', 'replace')
    return o


if CACHE_F:
    json.dump(CACHE, open(CACHE_F, 'w'))

# ------------------------------------------------------------------ un fichero por persona
os.makedirs(SAL, exist_ok=True)
for f in os.listdir(SAL):
    if f.startswith('p_') and f.endswith('.json'): os.remove(os.path.join(SAL, f))
resumen = {}
for pid in sorted(ACTIVAS):
    mios = []
    for c in salida_canales:
        if c['tipo'] != 'canal' and pid != 'tomas':      # los directos que da la API son de Tomás
            continue
        if any(x['pid'] == pid for x in c['miembros']):
            mios.append({'persona_id': pid, **c})
    menciones = []
    for c in mios:
        for m in c['mensajes']:
            for x in [m] + m.get('respuestas', []):
                if pid in x['menciones'] or (x['a_todos'] and x['autor_pid'] != pid):
                    menciones.append({'persona_id': pid, 'canal_id': c['id'], 'canal': c['nombre'], 'mensaje_id': x['id'],
                                      'hilo_de': m['id'] if x is not m else None, 'fecha': x['fecha'], 'autor': x['autor'],
                                      'texto': x['texto'][:300], 'a_todos': x['a_todos'] and pid not in x['menciones']})
    menciones.sort(key=lambda x: x['fecha'] or '', reverse=True)
    doc = {'_meta': {'generado': AHORA.strftime('%Y-%m-%d %H:%M'), 'persona_id': pid, 'fuente': 'ClickUp · chat (API v3), llave propia, solo lectura',
                     'workspace': WS, 'canales_total': len(canales), 'canales_de_cliente': de_cliente, 'canales_internos_activos': len(internos),
                     'canales_dormidos': dormidos, 'directos_de_tomas': len(directos), 'dias': LIMITE_DIAS, 'llamadas': LLAMADAS},
           'canales': mios, 'menciones': menciones[:60]}
    json.dump(tapar_todo(sano(doc)), open(os.path.join(SAL, f'p_{pid}.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    resumen[pid] = (len(mios), len(menciones))

print(f'canales {len(canales)} · de cliente {de_cliente} · internos activos {len(internos)} · dormidos {dormidos} · directos de Tomás {len(directos)} · llamadas {LLAMADAS}')
print('internos:', ', '.join(c.get('name') or '?' for c in internos))
print('por persona (canales, menciones):', resumen)
print('partido (N15):', partir(SAL))
print('sin persona de la app:', sorted({x['nombre'] for c in salida_canales for x in c['miembros'] if not x['pid']}))
