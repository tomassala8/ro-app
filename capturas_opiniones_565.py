"""Puerta de capturas guardadas: mismo ID de módulo que el router, sin IO propio."""
import re
from acciones_lectura_544 import ambito, cliente_visible


def permiso(E, P, ACT, panel_privado, real, persona, fila):
    actual = ambito(E, P, ACT, real, persona)
    if not actual:
        return None
    ps, cps, firma = actual
    try:
        ruta = fila['ruta']
        if not isinstance(ruta, str) or len(ruta) > 200 or not re.fullmatch(r'#/[-\w/.%?=&]*', ruta):
            return None
        # app.ruta toma el primer segmento literal, sin decodificar ni alias/fallback.
        mid = ruta[2:].split('?', 1)[0].split('/', 1)[0]
        if not re.fullmatch(r'[\w-]+', mid) or mid not in E.modulos:
            return None
        mapa = E.modulos[mid]
        if not isinstance(mapa, dict) or not all(P.nivel_modulo(p, mapa) in ('suyo', 'todo') for p in ps):
            return None
        if mid == 'panel-direccion' and not panel_privado.permitido(ps[0], ps[1], E.crudo.get('personas')):
            return None
        todas = all(P.ver(p, {'tipo': 'opiniones_ver'}, cp).get('ok') is True for p, cp in zip(ps, cps))
        if not todas and fila['quien'] != ps[1]['id']:
            return None
        # Una imagen no ofrece metadatos para recortar carteras, modales o campos.
        # opiniones_ver conserva texto/listado; no acredita contenido bitmap de terceros.
        if any(p['id'] != fila['quien'] for p in ps):
            return None
        if mid == 'ficha':
            partes = ruta[2:].split('?', 1)[0].split('/')
            if len(partes) < 2 or not cliente_visible(partes[1], E, P, ACT, ps, cps):
                return None
        return (mid, firma)
    except (KeyError, TypeError, AttributeError, ValueError, IndexError):
        return None
