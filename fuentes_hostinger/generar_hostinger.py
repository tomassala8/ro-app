#!/usr/bin/env python3
"""
generar_hostinger.py · Hostinger → data/hostinger/hostinger.json (SOLO LECTURA; nada se escribe en Hostinger).

Con token (llavero «hostinger_api_token», lo guarda ~/RO_HERRAMIENTAS/hostinger/pegar.sh):
  lee de la API oficial (https://developers.hostinger.com) los VPS (estado, CPU, RAM, disco, copias, acciones fallidas,
  malware), las webs del hosting compartido, los dominios (estado y caducidad) y las suscripciones (renovación);
  empareja cada web y dominio con su cliente por dominio (data/clientes/*.json → «web», igual que Modular) y deja por
  cliente su semáforo, sus motivos y sus incidencias en el formato de alertas de N4 (las recoge
  fuentes_alertas/generar_alertas.py → de_hostinger). Lo de la cuenta de RO (VPS, renovaciones, dominios sin cliente)
  va a dirección y al técnico.
  El VPS del gestor de contraseñas (claves.rankingonline.com) se reconoce y se marca como «interno»: solo se LEE.
Sin token: escribe el mismo fichero con estado «sin_conectar» y la instrucción para Tomás. No inventa nada.

Uso:
  python3 fuentes_hostinger/generar_hostinger.py                 # en vivo (si hay token)
  python3 fuentes_hostinger/generar_hostinger.py --ssl           # además, el certificado de cada web (1 llamada por web)
  python3 fuentes_hostinger/generar_hostinger.py --desde-cache   # usa fuentes_hostinger/_cache/volcado.json
  python3 fuentes_hostinger/generar_hostinger.py --simulado [--salida <fichero>]   # PRUEBA con datos inventados
"""
import datetime as dt
import glob
import json
import math
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(AQUI)
if APP not in sys.path:
    sys.path.insert(0, APP)
from fuentes.lectura import leer as leer_api, marcar  # noqa: E402  · N-01/N-05: toda lectura de API se guarda; si falla, la última buena
import pathlib as _pl_l27, sys as _sys_l27  # L-27: rutas del Mac por config.py
if str(_pl_l27.Path(__file__).resolve().parents[1]) not in _sys_l27.path:
    _sys_l27.path.append(str(_pl_l27.Path(__file__).resolve().parents[1]))
import config as _cfg  # noqa: E402
SALIDA = os.path.join(APP, 'data', 'hostinger', 'hostinger.json')   # webs, certificados y dominios por cliente (SEO, ficha y webs)
CUENTA = os.path.join(APP, 'data', 'hostinger', 'cuenta.json')        # VPS y renovaciones: solo dirección, operaciones y técnico
CACHE = os.path.join(AQUI, '_cache', 'volcado.json')
HERR = str(_cfg.HERRAMIENTAS / 'hostinger')
ENLACE = 'https://hpanel.hostinger.com/'
DOC_API = 'https://docs.hostinger.com/api-reference/overview'
QUE_HACER = ('Lo hace Tomás: hPanel → Perfil → API → crear token (con caducidad) y '
             'bash ~/RO_HERRAMIENTAS/hostinger/pegar.sh. Después, volver a generar.')
# VPS interno del gestor de contraseñas: la app SOLO lee su estado (nunca lo toca)
INTERNOS = {'claves.rankingonline.com': 'Gestor de contraseñas (Vaultwarden)', '72.61.188.128': 'Gestor de contraseñas (Vaultwarden)'}
# Umbrales (se pueden mover sin tocar el resto)
CPU_AMBAR, CPU_ROJO = 80, 95          # % medio de la última hora
RAM_AMBAR = 92                        # % de la memoria
DISCO_AMBAR, DISCO_ROJO = 80, 90      # % del disco
COPIA_AMBAR, COPIA_ROJO = 8, 15       # días sin copia (Hostinger hace copia semanal en los VPS)
DOM_AMBAR, DOM_ROJO = 30, 7           # días para caducar un dominio
SSL_AMBAR, SSL_ROJO = 14, 3           # días para caducar un certificado
RENOV_AMBAR, RENOV_ROJO = 30, 7       # días para que venza una suscripción sin renovación automática
EST_VPS_ROJO = {'stopped', 'error', 'suspended', 'suspending', 'recovery', 'destroyed', 'destroying', 'stopping'}
EST_VPS_AMBAR = {'starting', 'creating', 'initial', 'unsuspending', 'recreating', 'restoring', 'stopping_recovery'}


def guardar(ruta, obj):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    open(ruta + '.tmp', 'w').write(json.dumps(obj, ensure_ascii=False))
    os.replace(ruta + '.tmp', ruta)


def dominio(u):
    return re.sub(r'^(https?://)?(www\.)?', '', str(u or '').strip().lower()).split('/')[0].split(':')[0]


def clientes():
    out = []
    for f in sorted(glob.glob(os.path.join(APP, 'data', 'clientes', '*.json'))):
        try:
            c = json.load(open(f))
        except Exception:
            continue
        if c.get('activo_libro') in ('Baja',):
            continue
        out.append(c)
    return out


def sillas_web():
    try:
        verdad = json.load(open(os.path.join(APP, 'data', 'verdad', 'clientes.json')))['clientes']
        personas = {p['id']: p['nombre'] for p in json.load(open(os.path.join(APP, 'data', 'personas.json')))}
    except Exception:
        return {}
    out = {}
    for v in verdad:
        eq = (v.get('equipo') or {}).get('web') or []
        p = (next((x for x in eq if x.get('principal')), eq[0]) if eq else {}).get('persona_id')
        out[v['cliente_id']] = (p, personas.get(p))
    return out


def ahora_utc():
    if os.environ.get('RO_HOSTINGER_AHORA'):   # reloj falso para pruebas
        return dt.datetime.fromisoformat(os.environ['RO_HOSTINGER_AHORA']).replace(tzinfo=dt.timezone.utc)
    return dt.datetime.now(dt.timezone.utc)


def t(iso):
    if not iso:
        return None
    try:
        x = dt.datetime.fromisoformat(str(iso).replace('Z', '+00:00'))
        return x if x.tzinfo else x.replace(tzinfo=dt.timezone.utc)
    except Exception:
        return None


def dias_hasta(iso, ahora):
    x = t(iso)
    return None if x is None else (x - ahora).total_seconds() / 86400


def dias_n(x, negativo=False):
    """Días que quedan, redondeando hacia arriba (1,99 días = 2)."""
    n = math.ceil(x - 1e-6)
    return n if negativo else max(n, 0)


def corta(iso):
    x = t(iso)
    return x.astimezone().strftime('%d/%m/%Y') if x else None


def ultimos(m, n=6):
    u = (m or {}).get('usage') or {}
    ks = sorted(u, key=lambda k: int(k))[-n:]
    return [u[k] for k in ks if isinstance(u[k], (int, float))]


def sin_conectar(motivo):
    return {'_meta': {'generado': dt.datetime.now().strftime('%Y-%m-%d %H:%M'), 'fuente': 'Hostinger · API oficial',
                      'estado': 'sin_conectar', 'titular': 'sin clave', 'motivo': motivo, 'que_hacer': QUE_HACER,
                      'doc_api': DOC_API, 'enlace': ENLACE},
            'resumen': None, 'vps': [], 'clientes': [], 'dominios_sin_cliente': [], 'suscripciones': [],
            'sin_cliente': [], 'alertas': []}


def simulado():
    """Datos INVENTADOS para probar las reglas (no salen nunca a data/ sin --salida)."""
    a = ahora_utc()
    iso = lambda d: (a + dt.timedelta(days=d)).strftime('%Y-%m-%dT%H:%M:%SZ')
    ts = lambda h: str(int((a - dt.timedelta(hours=h)).timestamp()))
    cs = [c for c in clientes() if c.get('web')][:4]
    d0, d1, d2, d3 = [dominio(c['web']) for c in cs] + ['a.es', 'b.es', 'c.es', 'd.es'][len(cs):]
    return {'leido': a.strftime('%Y-%m-%d %H:%M'), 'errores': {}, '_simulado': True,
            'vps': [{'id': 1, 'hostname': 'claves.rankingonline.com', 'state': 'running', 'plan': 'KVM 1', 'cpus': 1, 'memory': 4096, 'disk': 51200, 'ipv4': [{'address': '72.61.188.128'}]},
                    {'id': 2, 'hostname': 'srv-pruebas', 'state': 'stopped', 'plan': 'KVM 2', 'cpus': 2, 'memory': 8192, 'disk': 102400, 'ipv4': []}],
            'metricas': {'1': {'cpu_usage': {'unit': '%', 'usage': {ts(h): 97 for h in range(6)}},
                               'ram_usage': {'unit': 'bytes', 'usage': {ts(0): 1.0 * 1024 ** 3}},
                               'disk_space': {'unit': 'bytes', 'usage': {ts(0): 47000 * 1048576}}}},
            'copias': {'1': [{'id': 9, 'created_at': iso(-20)}], '2': []},
            'acciones': {'1': [{'id': 5, 'name': 'backup', 'state': 'error', 'created_at': iso(-1)}]},
            'malware': {'1': {'malicious': 0, 'compromised': 0, 'scan_ended_at': iso(-1)}},
            'webs': [{'domain': d0, 'is_enabled': False, 'username': 'u1', 'website_type': 'wordpress'},
                     {'domain': d1, 'is_enabled': True, 'username': 'u1', 'website_type': 'wordpress'},
                     {'domain': 'www.' + d2, 'is_enabled': True, 'username': 'u1', 'website_type': 'wordpress'},
                     {'domain': 'pruebas-sin-cliente.es', 'is_enabled': True, 'username': 'u1', 'website_type': 'other'}],
            'ssl': {d1: {'status': 'active', 'is_lifetime': False, 'expires_at': iso(2)},
                    'www.' + d2: {'status': 'failed', 'last_error': 'dns'}},
            'dominios': [{'domain': d3, 'status': 'active', 'expires_at': iso(5)},
                         {'domain': d1, 'status': 'active', 'expires_at': iso(200)},
                         {'domain': 'rankingonline-viejo.es', 'status': 'expired', 'expires_at': iso(-3)}],
            'suscripciones': [{'id': 'S1', 'name': 'VPS KVM 1', 'status': 'active', 'is_auto_renewed': False, 'next_billing_at': iso(4), 'expires_at': iso(4)},
                              {'id': 'S2', 'name': 'Business Web Hosting', 'status': 'active', 'is_auto_renewed': True, 'next_billing_at': iso(20)},
                              {'id': 'S3', 'name': 'Dominio ' + d3, 'status': 'not_renewing', 'is_auto_renewed': False, 'expires_at': iso(5)}]}


def leer():
    if '--simulado' in sys.argv:
        return simulado()
    if '--desde-cache' in sys.argv:
        return json.load(open(CACHE))
    sys.path.insert(0, HERR)
    try:
        import hg  # noqa: E402
    except ImportError:
        return {'_sin_clave': 'No está el lector ~/RO_HERRAMIENTAS/hostinger/hg.py en este equipo.'}
    sin_clave = []

    def llamar():
        try:
            return hg.volcar(ssl='--ssl' in sys.argv)
        except hg.SinClave as e:       # no hay token: no es un fallo de la API
            sin_clave.append(str(e))
            raise
        except hg.HostingerError as e:   # N-05: el error lanza; leer() sirve la última lectura buena
            raise RuntimeError(str(e)) from e
    l = leer_api('hostinger', 'cuenta', llamar)
    if sin_clave:
        return {'_sin_clave': sin_clave[0]}
    if l.estado == 'ok':
        guardar(CACHE, l.datos)  # crudo SOLO en fuentes_hostinger/_cache (no se sirve)
        return l.datos
    if l.estado == 'viejo':
        return marcar(l)
    try:    # la base empieza vacía: la caché de ficheros de la última vuelta buena vale como dato viejo
        previa = json.load(open(CACHE))
        return {**previa, '_viejo': True, '_desde': previa.get('leido')}
    except (OSError, ValueError):
        return {'_error': l.error or 'sin respuesta', '_sin_dato': True}


def construir(d):
    ahora = ahora_utc()
    hoy_txt = dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    cls = clientes()
    por_dom = {dominio(c['web']): c for c in cls if c.get('web')}
    sil = sillas_web()

    def cliente_de(dom):
        dom = dominio(dom)
        c = por_dom.get(dom)
        if not c:
            c = next((cc for dd, cc in por_dom.items() if dom.endswith('.' + dd) or dd.endswith('.' + dom)), None)
        return c

    alertas = []

    def incid(regla, grav, titulo, texto, que_hacer, *, cid=None, objeto, departamento='web', desde=None, cifra=None):
        x = {'id': f"hostinger:{regla}:{objeto}", 'departamento': departamento, 'regla': regla, 'gravedad': grav,
             'cliente_id': cid, 'objeto': objeto, 'titulo': titulo, 'texto': texto, 'que_hacer': que_hacer,
             'fuente': 'Hostinger', 'fuente_enlace': ENLACE, 'detectado': hoy_txt, 'desde': desde, 'cifra': cifra}
        alertas.append(x)
        return x

    # ------------------------------------------------------------------ VPS (cuenta de RO)
    vps = []
    for v in d.get('vps') or []:
        vid = str(v.get('id'))
        host = v.get('hostname') or vid
        ips = [x.get('address') for x in (v.get('ipv4') or []) if isinstance(x, dict)] if isinstance(v.get('ipv4'), list) else []
        interno = INTERNOS.get(host) or next((INTERNOS[i] for i in ips if i in INTERNOS), None)
        nombre = f"{interno} · {host}" if interno else host
        dep = 'conexiones'   # el técnico (Agus) lo mira; sube a Mili y a Tomás
        mot, inc = [], []
        st = v.get('state')
        if st in EST_VPS_ROJO:
            mot.append(('rojo', f"Estado «{st}»"))
            inc.append(incid('vps_caido', 'rojo', 'Servidor (VPS) parado o con error',
                             f"{nombre}: Hostinger lo da como «{st}»." + (' El equipo no puede abrir el gestor de contraseñas.' if interno else ''),
                             'Mirar en hPanel › VPS qué ha pasado. La app no lo arranca ni lo toca: lo hace Agus (técnico) o Tomás en hPanel.',
                             objeto=vid, departamento=dep))
        elif st in EST_VPS_AMBAR:
            mot.append(('ambar', f"Estado «{st}» (en transición)"))
        m = (d.get('metricas') or {}).get(vid) or {}
        cpu = ultimos(m.get('cpu_usage'))
        cpu_med = round(sum(cpu) / len(cpu), 1) if cpu else None
        ram = ultimos(m.get('ram_usage'), 1)
        ram_pct = round(100 * ram[-1] / (v['memory'] * 1048576), 1) if ram and v.get('memory') else None
        dsk = ultimos(m.get('disk_space'), 1)
        dsk_pct = round(100 * dsk[-1] / (v['disk'] * 1048576), 1) if dsk and v.get('disk') else None
        if cpu_med is not None and cpu_med >= CPU_AMBAR:
            g = 'rojo' if cpu_med >= CPU_ROJO else 'ambar'
            mot.append((g, f"CPU al {cpu_med} % de media en la última hora"))
            inc.append(incid('vps_cpu', g, 'Servidor (VPS) con la CPU al límite', f"{nombre}: CPU al {cpu_med} % de media en la última hora.",
                             'Mirar qué proceso la come (hPanel › VPS › Uso de recursos) antes de que se cuelgue.', objeto=vid, departamento=dep, cifra=cpu_med))
        if ram_pct is not None and ram_pct >= RAM_AMBAR:
            mot.append(('ambar', f"Memoria al {ram_pct} %"))
            inc.append(incid('vps_memoria', 'ambar', 'Servidor (VPS) sin memoria', f"{nombre}: memoria al {ram_pct} %.",
                             'Revisar procesos o subir de plan.', objeto=vid, departamento=dep, cifra=ram_pct))
        if dsk_pct is not None and dsk_pct >= DISCO_AMBAR:
            g = 'rojo' if dsk_pct >= DISCO_ROJO else 'ambar'
            mot.append((g, f"Disco al {dsk_pct} %"))
            inc.append(incid('vps_disco', g, 'Servidor (VPS) con el disco casi lleno', f"{nombre}: disco al {dsk_pct} %.",
                             'Borrar copias o registros viejos, o ampliar disco. Con el disco lleno se paran las copias y la base de datos.',
                             objeto=vid, departamento=dep, cifra=dsk_pct))
        cps = (d.get('copias') or {}).get(vid)
        ult = max((t(c.get('created_at')) for c in (cps or []) if t(c.get('created_at'))), default=None)
        dias_copia = round((ahora - ult).total_seconds() / 86400, 1) if ult else None
        if cps is not None and ult is None:
            mot.append(('ambar', 'Sin ninguna copia de Hostinger'))
            inc.append(incid('vps_copia', 'ambar', 'Servidor (VPS) sin copia de seguridad', f"{nombre}: Hostinger no tiene ninguna copia.",
                             'Activar las copias semanales en hPanel (y, si es el gestor de contraseñas, comprobar también su copia cifrada propia).',
                             objeto=vid, departamento=dep))
        elif dias_copia is not None and dias_copia >= COPIA_AMBAR:
            g = 'rojo' if dias_copia >= COPIA_ROJO else 'ambar'
            mot.append((g, f"Última copia hace {int(dias_copia)} días"))
            inc.append(incid('vps_copia', g, 'Copia del servidor (VPS) atrasada', f"{nombre}: la última copia de Hostinger es de hace {int(dias_copia)} días.",
                             'Mirar en hPanel › VPS › Copias por qué no se hace.', objeto=vid, departamento=dep, desde=ult.isoformat(), cifra=int(dias_copia)))
        fall = [x for x in ((d.get('acciones') or {}).get(vid) or [])
                if x.get('state') == 'error' and t(x.get('created_at')) and (ahora - t(x['created_at'])).days < 2]
        if fall:
            nombres = ', '.join(sorted({str(x.get('name')) for x in fall}))[:120]
            g = 'ambar'
            mot.append((g, f"{len(fall)} operación(es) fallida(s) en 48 h ({nombres})"))
            inc.append(incid('vps_operacion', g, 'Operación fallida en el servidor (VPS)', f"{nombre}: {len(fall)} operación(es) fallida(s) en 48 h: {nombres}.",
                             'Mirar en hPanel › VPS › Historial qué falló (una copia fallida cuenta aquí).', objeto=vid, departamento=dep))
        mw = (d.get('malware') or {}).get(vid) or {}
        mal = (mw.get('malicious') or 0) + (mw.get('compromised') or 0)
        if mal:
            mot.append(('rojo', f"{mal} fichero(s) con malware"))
            inc.append(incid('vps_malware', 'rojo', 'Malware en el servidor (VPS)', f"{nombre}: el analizador de Hostinger encontró {mal} fichero(s) maliciosos o comprometidos.",
                             'Avisar a Agus y a Tomás; no borrar a mano sin copia.', objeto=vid, departamento=dep, cifra=mal))
        orden = {'rojo': 3, 'ambar': 2}
        vps.append({'id': v.get('id'), 'nombre': nombre, 'hostname': host, 'interno': interno, 'solo_lectura': True,
                    'estado_hostinger': st, 'plan': v.get('plan'), 'cpus': v.get('cpus'), 'memoria_mb': v.get('memory'), 'disco_mb': v.get('disk'),
                    'cpu_pct_1h': cpu_med, 'ram_pct': ram_pct, 'disco_pct': dsk_pct, 'ultima_copia': ult.isoformat() if ult else None,
                    'dias_sin_copia': dias_copia, 'malware': mal if mw else None,
                    'estado': max([x[0] for x in mot], key=lambda g: orden[g], default='verde'),
                    'motivos': [x[1] for x in sorted(mot, key=lambda x: -orden[x[0]])] or ['Todo en orden según Hostinger'],
                    'incidencias': [i['id'] for i in inc]})

    # ------------------------------------------------------------------ webs, dominios y SSL por cliente
    por_cli, sin_cliente, dom_sin = {}, [], []

    def fila(c):
        if c['id'] not in por_cli:
            w = sil.get(c['id']) or (None, None)
            por_cli[c['id']] = {'cliente_id': c['id'], 'cliente': c.get('nombre'), 'web_id': w[0], 'web_nombre': w[1],
                                'webs': [], 'dominios': [], 'motivos': [], 'incidencias': [], '_g': []}
        return por_cli[c['id']]

    ssl = d.get('ssl') or {}
    for w in d.get('webs') or []:
        dom = w.get('domain')
        if not dom:
            continue
        c = cliente_de(dom)
        cid = c['id'] if c else None
        mot = []
        if w.get('is_enabled') is False:
            mot.append(('rojo', 'Web suspendida en Hostinger'))
            x = incid('web_suspendida', 'rojo', 'Web suspendida en el hosting', f"{dominio(dom)}: Hostinger la tiene suspendida (no se sirve).",
                      'Mirar en hPanel el motivo (impago, abuso, malware) y avisar a Tomás.', cid=cid, objeto=dominio(dom),
                      departamento='web' if cid else 'direccion')
            if c:
                fila(c)['incidencias'].append(x['id'])
        s = ssl.get(dom) or ssl.get(dominio(dom)) or {}
        if s:
            ds = dias_hasta(s.get('expires_at'), ahora)
            if s.get('status') in ('expired', 'failed'):
                mot.append(('rojo', f"Certificado {'caducado' if s['status'] == 'expired' else 'con error'}"))
                x = incid('ssl', 'rojo', 'Certificado de seguridad caducado o con error', f"{dominio(dom)}: certificado «{s['status']}»"
                          + (f" ({s['last_error']})" if s.get('last_error') else '') + '. El navegador avisa de «no seguro».',
                          'Reinstalar el certificado en hPanel › Webs › Seguridad (la app no lo hace).', cid=cid, objeto=dominio(dom),
                          departamento='web' if cid else 'direccion')
                if c:
                    fila(c)['incidencias'].append(x['id'])
            elif ds is not None and not s.get('is_lifetime') and ds <= SSL_AMBAR:
                g = 'rojo' if ds <= SSL_ROJO else 'ambar'
                mot.append((g, f"Certificado caduca en {dias_n(ds)} días"))
                x = incid('ssl', g, 'Certificado a punto de caducar', f"{dominio(dom)}: el certificado caduca el {corta(s.get('expires_at'))}.",
                          'Comprobar la renovación automática en hPanel.', cid=cid, objeto=dominio(dom), departamento='web' if cid else 'direccion',
                          cifra=dias_n(ds))
                if c:
                    fila(c)['incidencias'].append(x['id'])
        entrada = {'dominio': dominio(dom), 'tipo': w.get('website_type'), 'activa': w.get('is_enabled'),
                   'ssl': {'estado': s.get('status'), 'caduca': s.get('expires_at'), 'vitalicio': s.get('is_lifetime')} if s else None,
                   'motivos': [m[1] for m in mot]}
        if c:
            f = fila(c)
            f['webs'].append(entrada)
            f['_g'] += [m[0] for m in mot]
            f['motivos'] += [m[1] for m in mot]
        else:
            sin_cliente.append({**entrada, 'estado': max([m[0] for m in mot], key=lambda g: {'rojo': 3, 'ambar': 2}[g], default='verde')})

    for x in d.get('dominios') or []:
        dom = x.get('domain')
        if not dom:
            continue
        c = cliente_de(dom)
        cid = c['id'] if c else None
        dd = dias_hasta(x.get('expires_at'), ahora)
        mot = []
        if x.get('status') in ('expired', 'suspended', 'deleted', 'failed'):
            mot.append(('rojo', f"Dominio «{x['status']}»"))
            i = incid('dominio', 'rojo', 'Dominio caducado o suspendido', f"{dominio(dom)}: Hostinger lo da como «{x['status']}»"
                      + (f" (caducó el {corta(x.get('expires_at'))})" if x.get('expires_at') else '') + '.',
                      'Si es de un cliente activo, renovarlo YA (web y correo dejan de funcionar). Lo decide Tomás.', cid=cid,
                      objeto=dominio(dom), departamento='web' if cid else 'direccion')
            if c:
                fila(c)['incidencias'].append(i['id'])
        elif dd is not None and dd <= DOM_AMBAR and x.get('status') == 'active':
            g = 'rojo' if dd <= DOM_ROJO else 'ambar'
            mot.append((g, f"Dominio caduca en {dias_n(dd)} días"))
            i = incid('dominio', g, 'Dominio a punto de caducar', f"{dominio(dom)}: caduca el {corta(x.get('expires_at'))}.",
                      'Comprobar que la renovación automática está puesta y la tarjeta vale (hPanel › Dominios).', cid=cid,
                      objeto=dominio(dom), departamento='web' if cid else 'direccion', cifra=dias_n(dd))
            if c:
                fila(c)['incidencias'].append(i['id'])
        entrada = {'dominio': dominio(dom), 'estado_hostinger': x.get('status'), 'caduca': x.get('expires_at'),
                   'dias_para_caducar': dias_n(dd, negativo=True) if dd is not None else None, 'motivos': [m[1] for m in mot]}
        if c:
            f = fila(c)
            f['dominios'].append(entrada)
            f['_g'] += [m[0] for m in mot]
            f['motivos'] += [m[1] for m in mot]
        else:
            dom_sin.append({**entrada, 'estado': max([m[0] for m in mot], key=lambda g: {'rojo': 3, 'ambar': 2}[g], default='verde')})

    # ------------------------------------------------------------------ renovaciones (cuenta de RO, sin importes)
    subs = []
    for s in d.get('suscripciones') or []:
        vence = s.get('next_billing_at') or s.get('expires_at')
        dv = dias_hasta(vence, ahora)
        mot = []
        sin_auto = not s.get('is_auto_renewed')
        if s.get('status') in ('active', 'not_renewing', 'in_trial') and (sin_auto or s.get('status') == 'not_renewing') and dv is not None and dv <= RENOV_AMBAR:
            g = 'rojo' if dv <= RENOV_ROJO else 'ambar'
            mot.append((g, f"Vence en {dias_n(dv)} días sin renovación automática"))
            incid('renovacion', g, 'Renovación pendiente en Hostinger', f"«{s.get('name')}» vence el {corta(vence)} y no se renueva sola.",
                  'Decidir si se renueva (hPanel › Facturación). La app no renueva ni paga nada: lo hace Tomás.',
                  objeto=str(s.get('id')), departamento='direccion', cifra=dias_n(dv))
        elif s.get('status') == 'paused':
            mot.append(('ambar', 'Suscripción en pausa'))
        subs.append({'id': s.get('id'), 'nombre': s.get('name'), 'estado_hostinger': s.get('status'),
                     'renovacion_automatica': s.get('is_auto_renewed'), 'vence': vence,
                     'dias': dias_n(dv, negativo=True) if dv is not None else None, 'motivos': [m[1] for m in mot],
                     'estado': max([m[0] for m in mot], key=lambda g: {'rojo': 3, 'ambar': 2}[g], default='verde')})

    orden = {'rojo': 0, 'ambar': 1, 'verde': 2}
    cl = []
    for f in por_cli.values():
        g = f.pop('_g')
        f['estado'] = 'rojo' if 'rojo' in g else 'ambar' if 'ambar' in g else 'verde'
        f['motivos'] = f['motivos'] or ['Todo en orden según Hostinger']
        cl.append(f)
    cl.sort(key=lambda f: (orden[f['estado']], f['cliente'] or ''))
    # Dueño de cada alerta de cliente: persona principal de web
    for x in alertas:
        if x.get('cliente_id'):
            x['dueno_id'] = (sil.get(x['cliente_id']) or (None, None))[0]
    res = {'vps': len(vps), 'vps_rojo': sum(v['estado'] == 'rojo' for v in vps), 'vps_ambar': sum(v['estado'] == 'ambar' for v in vps),
           'webs': len(d.get('webs') or []), 'dominios': len(d.get('dominios') or []), 'suscripciones': len(subs),
           'clientes_emparejados': len(cl), 'clientes_rojo': sum(f['estado'] == 'rojo' for f in cl),
           'clientes_ambar': sum(f['estado'] == 'ambar' for f in cl), 'webs_sin_cliente': len(sin_cliente),
           'dominios_sin_cliente': len(dom_sin), 'renovaciones_pendientes': sum(1 for x in alertas if x['regla'] == 'renovacion'),
           'alertas': len(alertas), 'alertas_rojas': sum(x['gravedad'] == 'rojo' for x in alertas)}
    return {'_meta': {'generado': dt.datetime.now().strftime('%Y-%m-%d %H:%M'), 'leido': d.get('leido'),
                      'fuente': 'Hostinger · API oficial (solo lectura)', 'estado': 'simulado' if d.get('_simulado') else 'conectado',
                      'doc_api': DOC_API, 'enlace': ENLACE, 'errores_parciales': d.get('errores') or {},
                      'con_ssl': bool(d.get('ssl')),
                      'nota': 'La app solo LEE Hostinger: no arranca, reinicia, renueva ni cambia nada (tampoco el VPS del gestor de contraseñas).'},
            'resumen': res, 'vps': vps, 'clientes': cl, 'dominios_sin_cliente': dom_sin, 'suscripciones': subs,
            'sin_cliente': sin_cliente, 'alertas': alertas}


def partir(out):
    """Un fichero para las webs de clientes y otro para la cuenta de RO (VPS, también el del gestor de contraseñas, y
    renovaciones), que solo llega a dirección, operaciones y el técnico (reglas_permisos.json)."""
    m = out['_meta']
    cuenta_al = [x for x in out['alertas'] if x['departamento'] in ('conexiones', 'direccion')]
    web = {k: v for k, v in out.items() if k not in ('vps', 'suscripciones')}
    web['alertas'] = [x for x in out['alertas'] if x not in cuenta_al]
    cuenta = {'_meta': m, 'resumen': out.get('resumen'), 'vps': out.get('vps', []), 'suscripciones': out.get('suscripciones', []),
              'alertas': cuenta_al}
    return web, cuenta


def main():
    d = leer()
    if '_sin_clave' in d:
        out = sin_conectar('No hay token de la API de Hostinger en este equipo.')
    elif '_error' in d:
        out = sin_conectar('La API de Hostinger respondió con error: ' + d['_error'])
        out['_meta'].update(estado='sin_dato', titular='sin dato', que_hacer='La API de Hostinger no respondió y no hay lectura anterior: se reintenta en la próxima vuelta.')
    else:
        out = construir(d)
        if d.get('_viejo'):    # N-05: la API falló; son los últimos datos buenos
            out['_meta'].update(estado='dato_viejo', dato_viejo_desde=d.get('_desde'))
    destino = sys.argv[sys.argv.index('--salida') + 1] if '--salida' in sys.argv else SALIDA
    if out['_meta']['estado'] == 'simulado' and destino == SALIDA:
        sys.exit('--simulado escribe solo con --salida <fichero> (los datos inventados nunca van a data/).')
    web, cuenta = partir(out)
    guardar(destino, web)
    guardar(CUENTA if destino == SALIDA else re.sub(r'(\.json)?$', '_cuenta.json', destino, count=1), cuenta)
    r = out.get('resumen')
    print(f"{os.path.relpath(destino, APP)} (+ cuenta) · {out['_meta']['estado']}" + (f" · {r}" if r else f" · sin clave · {out['_meta']['que_hacer']}"))
    if out['_meta']['estado'] == 'sin_dato':
        sys.exit(2)    # N-05: la tubería tiene que ver que no hubo dato (antes salía 0 con «sin conectar»)


if __name__ == '__main__':
    main()
