"""Abrir una sala existente: enlaces privados del dueño, sin iniciar reuniones desde el servidor."""
import json
import os
import re
import stat
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlsplit, parse_qs


def enlace_valido(url):
    if not isinstance(url, str) or len(url) > 8192 or any(ord(c) <= 32 or ord(c) == 127 for c in url):
        return False
    try:
        u = urlsplit(url)
        return (u.scheme == 'https' and not u.username and not u.password and u.port in (None, 443)
                and (u.hostname == 'zoom.us' or (u.hostname or '').endswith('.zoom.us'))
                and re.fullmatch(r'/(?:s|j|my|join|wc/join)/[^/]+/?', u.path) is not None)
    except ValueError:
        return False


def deposito():
    nombre = os.environ.get('RO_ZOOM_ENLACES')
    if not nombre:
        return {}
    if not hasattr(os,'O_NOFOLLOW'):return {}
    ruta=Path(os.path.abspath(nombre))
    if any(p.is_symlink() for p in (ruta,*ruta.parents)):
        return {}
    fd = os.open(ruta, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_size > 2_000_000 or stat.S_IMODE(st.st_mode) != 0o600 or st.st_uid != os.geteuid():
            return {}
        with os.fdopen(fd, 'r', closefd=False) as f:
            def unico(pares):
                out={}
                for k,v in pares:
                    if k in out:raise ValueError('Depósito ambiguo.')
                    out[k]=v
                return out
            d = json.loads(f.read(2_000_001),object_pairs_hook=unico)
        return d.get('salas') if isinstance(d, dict) and isinstance(d.get('salas'), dict) else {}
    finally:
        os.close(fd)


def elegir(evento, salas, real_id, vista_id, ahora=None):
    if not isinstance(real_id,str) or not real_id or real_id != vista_id or not isinstance(evento,dict) or evento.get('persona_id') != real_id or not isinstance(salas,dict):
        return None
    ahora = ahora or datetime.now(timezone.utc)
    if not isinstance(ahora,datetime) or ahora.tzinfo is None:return None
    ids = [evento.get('id')] + [x.get('id') for x in evento.get('origenes') or [] if isinstance(x, dict)]
    encontrados = []
    for eid in ids:
        if not isinstance(eid,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,200}',eid):continue
        fila = salas.get(eid)
        if not isinstance(fila, dict) or fila.get('persona_id') != real_id:
            continue
        try:
            leido = datetime.fromisoformat(fila['leido'])
            expira = datetime.fromisoformat(fila['valido_hasta'])
            if leido.tzinfo is None or expira.tzinfo is None or not leido <= ahora < leido + timedelta(hours=24):
                continue
        except (KeyError, TypeError, ValueError):
            continue
        host = fila.get('start_url') if ahora < min(expira, leido + timedelta(hours=1)) else None
        url = host if enlace_valido(host) else fila.get('join_url')
        if enlace_valido(url):
            encontrados.append(url)
    unicos = set(encontrados)
    return next(iter(unicos)) if len(unicos) == 1 else None


def _sin_enlaces_host(o):
    if isinstance(o,dict):
        return {k:_sin_enlaces_host(v) for k,v in o.items() if k.lower() not in ('start_url','host_url','zak')}
    if isinstance(o,list):return [_sin_enlaces_host(v) for v in o]
    if isinstance(o,str):
        try:
            u=urlsplit(o)
            if enlace_valido(o) and (u.path.startswith('/s/') or any(k.lower()=='zak' for k in parse_qs(u.query))):return None
        except ValueError:pass
    return o


def disponibilidad(doc, real, persona):
    try:
        salas = deposito()
    except (OSError, ValueError):
        salas = {}
    if not isinstance(doc,dict):return {'eventos':[]}
    doc=_sin_enlaces_host(doc)
    return {**doc, 'eventos': [{**e, 'zoom_privado_disponible': bool(elegir(e, salas, real['id'], persona['id']))}
                              for e in doc.get('eventos') or [] if isinstance(e,dict)]}


def enganchar(Manejador, S):
    anterior = Manejador._api_get

    def get(self, ruta, q, real, persona):
        if ruta != '/api/agenda/zoom':
            return anterior(self, ruta, q, real, persona)
        if S.E.nucleo_bloqueado:
            return self.responder(503, {'error': 'Datos temporalmente bloqueados.'})
        if real['id'] != persona['id'] or not S.ve_alguno(real, ['agenda']):
            return self.responder(403, {'error': 'La sala sólo la abre su dueño en su propia agenda.'})
        if set(q)-{'evento_id','yo','como'} or len(q.get('evento_id') or [])!=1:
            return self.responder(400, {'error': 'Referencia de cita inválida.'})
        eid = (q.get('evento_id') or [''])[0]
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,200}', eid):
            return self.responder(400, {'error': 'Referencia de cita inválida.'})
        d = S.modulo_recortado(real, persona, S.P.contexto(persona, S.E.crudo), 'agenda/agenda') or {}
        if not isinstance(d,dict):d={}
        candidatos = [e for e in d.get('eventos') or [] if isinstance(e,dict) and e.get('id') == eid and e.get('persona_id') == real['id']]
        try:
            url = elegir(candidatos[0], deposito(), real['id'], persona['id']) if len(candidatos) == 1 else None
        except (OSError, ValueError):
            url = None
        if not url:
            return self.responder(404, {'error': 'No hay un enlace Zoom vigente y confirmado para esta cita.'})
        # El vínculo de anfitrión nunca aparece en un JSON, búsqueda, caché pública ni log.
        self.send_response(302)
        self.send_header('Location', url)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Length', '0')
        self.end_headers()

    Manejador._api_get = get
