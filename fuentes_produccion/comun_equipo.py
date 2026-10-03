"""comun_equipo.py · utilidades compartidas por M10 Producción y M11 Horas (solo estos dos módulos).

- Une cada usuario de ClickUp con su persona de la app (correo, nombre completo o nombre de pila único).
- Une cada carpeta de ClickUp con su cliente de la app (data/clientes/<id>.json → fuentes.tareas.datos.carpeta_id).
- tipo_tarea(): el mismo criterio que el detector de horas raras de build.py (quita clientes, meses y números).
Solo lee. No escribe nada fuera de data/produccion y data/horas.
"""
import json, re, unicodedata, datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

APP = Path(__file__).resolve().parent.parent
DATA = APP / 'data'
CACHE = APP / 'fuentes_produccion' / '_privado' / '_cache'   # nombres de tareas con correos: fuera del escáner y de la subida
import sys as _sys  # C5: rutas en config.py
_sys.path.insert(1, str(APP))
import config  # noqa: E402
PANEL = config.PANEL_OPERACIONES
MAD = ZoneInfo('Europe/Madrid')
AHORA = dt.datetime.now(MAD)
HOY = AHORA.date()

ESTADOS_REVISION_INTERNA = {'revisión project manager', 'revisión técnica', 'revisión mili', 'revisión tomás'}
ESTADOS_TRABAJO = {'diario', 'en curso', 'in progress', 'planning semanal', 'próximo sprint', 'corrección', 'correcciones', 'to do'}
ESTADOS_PRODUCTIVOS = {'revisión project manager', 'revisión cliente', 'ver cliente', 'completado', 'complete', 'completada', 'cerrado', 'closed'}


def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def leer(p, defecto=None):
    try:
        return json.load(open(p))
    except Exception:
        return defecto


def escribir(p, datos, compacto=False):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(datos, ensure_ascii=False, separators=(',', ':')) if compacto else json.dumps(datos, ensure_ascii=False, indent=1))
    tmp.replace(p)


def personas():
    L = leer(DATA / 'personas.json', [])
    return L if isinstance(L, list) else L.get('personas', [])


def mapa_usuarios(miembros_cu):
    """{usuario_id_clickup: persona_id} por correo, nombre completo o nombre de pila único."""
    P = personas()
    por_correo = {}
    for p in P:
        for c in [p.get('correo')] + list(p.get('otros_correos') or []):
            if c:
                por_correo[c.lower()] = p['id']
    por_nombre = {norm(p['nombre']): p['id'] for p in P}
    pila = {}
    for p in P:
        k = norm(p['nombre']).split()[0] if norm(p['nombre']) else ''
        pila.setdefault(k, []).append(p['id'])
    out = {}
    for u in miembros_cu:
        pid = por_correo.get((u.get('email') or '').lower())
        nn = norm(re.sub(r'\(.*?\)', '', u.get('nombre') or ''))
        if not pid:
            pid = por_nombre.get(nn)
        if not pid and nn:
            # «Lucia Caso» = «Lucía Caso»; «Jerónimo» → jeronimo; «Milagros» → mili
            cand = [p['id'] for p in P if norm(p['nombre']).startswith(nn) or nn.startswith(norm(p['nombre']))]
            if len(cand) == 1:
                pid = cand[0]
        if not pid and nn:
            c = pila.get(nn.split()[0], [])
            if len(c) == 1:
                pid = c[0]
        if pid:
            out[str(u['id'])] = pid
    return out


def miembros_clickup():
    m = leer(PANEL / '_crudo/clickup/miembros.json', {}) or {}
    return (m.get('miembros') or []) + (m.get('usuarios_no_miembros_vistos') or [])


def clientes_app():
    """{carpeta_id: (cliente_id, nombre)} y {cliente_id: nombre}."""
    por_carpeta, nombres = {}, {}
    for f in sorted((DATA / 'clientes').glob('*.json')):
        d = leer(f, {}) or {}
        if not d.get('id'):
            continue
        nombres[d['id']] = d.get('nombre')
        cid = (((d.get('fuentes') or {}).get('tareas') or {}).get('datos') or {}).get('carpeta_id')
        if cid:
            por_carpeta[str(cid)] = (d['id'], d.get('nombre'))
    # carpetas del panel emparejadas con la Cartera (respaldo por nombre)
    car = leer(PANEL / '_crudo/clickup/carpetas_clientes.json', {}) or {}
    por_nombre = {norm(n): i for i, n in nombres.items()}
    for f in car.get('carpetas', []):
        if str(f['carpeta_id']) in por_carpeta or f.get('confianza') == 'baja':
            continue
        i = por_nombre.get(norm(f.get('cartera_nombre') or ''))
        if i:
            por_carpeta[str(f['carpeta_id'])] = (i, nombres[i])
    return por_carpeta, nombres


_NOMBRES_CLI = None


def tipo_tarea(nom):
    """Igual que build.py (detector de horas raras): quita nombres de cliente, meses, números y versiones."""
    global _NOMBRES_CLI
    if _NOMBRES_CLI is None:
        _, nombres = clientes_app()
        car = leer(PANEL / '_crudo/clickup/cartera.json', {}) or {}
        todos = set(nombres.values()) | {c.get('nombre') for c in car.get('clientes', [])}
        _NOMBRES_CLI = sorted({norm(x) for x in todos if x}, key=len, reverse=True)
    n = norm(nom)
    for c in _NOMBRES_CLI:
        if c and len(c) > 3:
            n = n.replace(c, ' ')
    n = re.sub(r'\b(\d+|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|sep|oct|ago|semana|s\d+|v\d+)\b', ' ', n)
    return ' '.join(n.split()[:5]) or 'sin nombre'


def sin_cliente(texto):
    """Quita los nombres de cliente de un texto (para RRHH: el cliente, solo en agregado · D-84)."""
    tipo_tarea('x')
    n = ' ' + norm(texto or '') + ' '
    for c in _NOMBRES_CLI:
        if c and len(c) > 3 and f' {c} ' in n:
            n = n.replace(f' {c} ', ' (cliente) ')
    return ' '.join(n.split())[:90]


def fecha_ms(v):
    return dt.datetime.fromtimestamp(int(v) / 1000, MAD) if v else None


def dias_lab(a, b):
    """Días laborables (L-V) en [a, b)."""
    n, d = 0, a
    while d < b:
        if d.weekday() < 5:
            n += 1
        d += dt.timedelta(days=1)
    return n


def mes_str(d):
    return d.strftime('%Y-%m')


MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


def nombre_mes(m):
    return MESES[int(m[5:]) - 1]


_CORREO = re.compile(r'[\w.+-]+@[\w-]+(\.[\w-]+)+')
_TEL = re.compile(r'(?<!\d)(\+?\d[\d .-]{7,}\d)(?!\d)')


_EMOJI = re.compile('[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D]')


def es_urgente(texto):
    """🔴 o ‼ en el título de ClickUp = urgente (la auditoría de experiencia pide convertirlo en etiqueta)."""
    return bool(re.search('🔴|‼|🚨', texto or ''))


def limpiar(texto):
    """Quita correos, teléfonos y emojis de un texto libre (nombres de tarea, motivos): la puerta de secretos no deja
    pasar correos ni teléfonos, y la regla de textos de la app no quiere emojis."""
    t = _EMOJI.sub('', texto or '').strip()
    t = re.sub(r'\s{2,}', ' ', t)
    t = _CORREO.sub('[correo]', t)
    return _TEL.sub(lambda m: '[teléfono]' if len(re.sub(r'\D', '', m.group(1))) >= 9 else m.group(1), t)
