"""Modo de consulta optativo: no admite operaciones POST de la aplicación.

Debe engancharse después de todos los demás controladores. La autenticación,
Host y origen siguen comprobándose antes en do_POST. No sustituye Access,
copias, ni las banderas que paran trabajadores y envíos externos.
"""
import os
import re

MODULOS_PILOTO = frozenset(('prioridades-cliente', 'mi-trabajo', 'captacion', 'salud-crm',
                            'reuniones', 'ficha', 'paneles'))
LECTURAS = frozenset(('/api/sesion', '/api/cerebro/operativo', '/api/cerebro/seo',
                     '/api/cerebro/borrador', '/api/metodo/sugerencias', '/api/mi_trabajo',
                     '/api/recarga', '/api/uso/aviso', '/api/historial/reuniones',
                     '/api/en-rojo/planes', '/api/produccion/urgencias-observadas',
                     '/api/bandeja/triaje-intenciones'))  # Lecturas locales con puertas ACT/P.


# Lista de fuentes, no patrón genérico de todas las carpetas. Los módulos originales
# siguen comprobando puesto, cliente, inversión, ámbito real/vista y filas de datos.
FUENTES_LECTURA = frozenset((
    'mi_trabajo/mi_trabajo', 'captacion/captacion', 'verdad/clientes',
    'crm/crm', 'reuniones/reuniones', 'paneles/indice',
    'ficha/basica', 'ficha/portal', 'ficha/web', 'ficha/correos', 'ficha/informes',
    # Dependencias directas de la ficha (ficha.js:300-303), ya recortadas por cliente.
    'bandeja/por_cliente', 'objetivos/objetivos', 'fuentes/hallazgos_medicion',
))
# Herramientas declaradas en modulos/paneles.js HERR; empresa tiene puertas por puesto.
HERRAMIENTAS_PANELES = frozenset(('meta', 'ghl', 'ga4', 'gsc', 'mc'))
FUENTES_EMPRESA = frozenset(('paneles/empresa/desk', 'paneles/empresa/zadarma'))
_ID_CLIENTE = re.compile(r'[a-zA-Z0-9_-]{1,100}')


def permite_lectura(ruta):
    if not isinstance(ruta, str): return False
    if ruta in LECTURAS: return True
    if ruta.startswith('/api/cliente/'):
        return _ID_CLIENTE.fullmatch(ruta.removeprefix('/api/cliente/')) is not None
    if not ruta.startswith('/api/modulo/'): return False
    rel = ruta.removeprefix('/api/modulo/')
    if rel in FUENTES_LECTURA or rel in FUENTES_EMPRESA: return True
    partes = rel.split('/')
    return (len(partes) == 3 and partes[0] == 'paneles'
            and partes[1] in HERRAMIENTAS_PANELES
            and _ID_CLIENTE.fullmatch(partes[2]) is not None)


def modulos_disponibles(modulos):
    if not activo(): return modulos
    return {k: v for k, v in modulos.items() if k in MODULOS_PILOTO}


def activo():
    # Un valor desconocido activa la restricción, nunca amplía escritura.
    return os.environ.get('RO_PILOTO_LECTURA', '').strip().lower() not in ('', '0', 'no', 'false')


def enganchar(Manejador):
    original = Manejador.api_post
    lectura_original = Manejador._api_get

    def get(self, ruta, q, real, persona):
        if activo() and not permite_lectura(ruta):
            return self.responder(403, {'error': 'Esta función está fuera del piloto de consulta.',
                                        'codigo': 'piloto_lectura_limitada'})
        return lectura_original(self, ruta, q, real, persona)

    def post(self, ruta, real, persona, cuerpo):
        if activo():
            return self.responder(403, {'error': 'Este piloto es de consulta. No se ha guardado ni enviado ningún cambio.',
                                        'codigo': 'piloto_solo_lectura'})
        return original(self, ruta, real, persona, cuerpo)

    Manejador.api_post = post
    Manejador._api_get = get
