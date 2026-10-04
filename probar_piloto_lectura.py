import os
import unittest
import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import piloto_lectura as piloto


class PilotoLectura(unittest.TestCase):
    def ejecutar_arranque(self, restringido):
        llamadas = []
        class Conexion:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def execute(self, *args): llamadas.append('actualizar_recargas')
        class Servidor:
            def __init__(self, *args): llamadas.append('servidor')
            def serve_forever(self): raise KeyboardInterrupt
        e = SimpleNamespace(cargar=lambda: llamadas.append('cargar'), bloqueados=[], nucleo_bloqueado=False)
        espacio = dict(sys=SimpleNamespace(argv=['servir.py']), os=SimpleNamespace(environ={}),
            ACCESO=SimpleNamespace(activo=lambda:False), PILOTO_LECTURA=SimpleNamespace(activo=lambda:restringido),
            iniciar_base=lambda:llamadas.append('esquema'), E=e,
            FOTO=SimpleNamespace(hay_foto_de_hoy=lambda:False, hacer_foto=lambda:llamadas.append('foto')),
            hoy=lambda:'2026-10-03', calcular_avisos=lambda:llamadas.append('avisos'),
            threading=SimpleNamespace(Thread=lambda **kw:SimpleNamespace(start=lambda:llamadas.append('trabajador'))),
            trabajador_recargas=lambda:None, conectar=Conexion, COLA=SimpleNamespace(set=lambda:llamadas.append('cola')),
            ThreadingHTTPServer=Servidor, Manejador=object, print=lambda *args:None)
        nodo = next(n for n in ast.parse(Path(__file__).with_name('servir.py').read_text()).body
                    if isinstance(n, ast.FunctionDef) and n.name=='main')
        exec(compile(ast.Module(body=[nodo], type_ignores=[]), 'arranque_real', 'exec'), espacio)
        espacio['main']()
        return llamadas

    def test_arranque_piloto_no_foto_avisos_trabajadores_recargas(self):
        self.assertEqual(self.ejecutar_arranque(True), ['esquema','cargar','servidor'])

    def test_arranque_normal_conserva_operaciones_previas(self):
        self.assertEqual(self.ejecutar_arranque(False),
            ['esquema','foto','cargar','avisos','trabajador','actualizar_recargas','cola','servidor'])

    def controlador(self):
        class Handler:
            def __init__(self): self.llamadas = []
            def api_post(self, ruta, real, persona, cuerpo):
                self.llamadas.append((ruta, cuerpo))
                return 'controlador original'
            def _api_get(self, ruta, q, real, persona):
                self.llamadas.append(ruta)
                return 'lectura con permisos originales'
            def responder(self, codigo, cuerpo): return codigo, cuerpo
        piloto.enganchar(Handler)
        return Handler()

    def test_todas_escrituras_se_bloquean_sin_ejecutar_controlador(self):
        h = self.controlador()
        with patch.dict(os.environ, {'RO_PILOTO_LECTURA': '1'}):
            for ruta in ('/api/accion', '/api/acciones/lote', '/api/actas', '/api/mi_trabajo',
                         '/api/recargar', '/api/uso/evento', '/api/ruta-futura'):
                respuesta = h.api_post(ruta, {'id':'real'}, {'id':'vista'}, {'texto':'no persistir'})
                self.assertEqual(respuesta[0], 403)
                self.assertEqual(respuesta[1]['codigo'], 'piloto_solo_lectura')
        self.assertEqual(h.llamadas, [])

    def test_sin_flag_no_cambia_el_controlador_ni_el_payload(self):
        h = self.controlador()
        with patch.dict(os.environ, {'RO_PILOTO_LECTURA': 'no'}):
            b = {'texto': 'original'}
            self.assertEqual(h.api_post('/api/accion', {}, {}, b), 'controlador original')
        self.assertIs(h.llamadas[0][1], b)

    def test_valor_desconocido_restringe(self):
        with patch.dict(os.environ, {'RO_PILOTO_LECTURA': 'valor incorrecto'}):
            self.assertTrue(piloto.activo())

    def test_get_mutables_y_desconocidos_no_ejecutan_controladores(self):
        h = self.controlador()
        with patch.dict(os.environ, {'RO_PILOTO_LECTURA': '1'}):
            for ruta in ('/api/canales', '/api/canales/resumen', '/api/sincronia', '/api/envios',
                         '/api/ia', '/api/futura', '/api/modulo/a/b/c', '/api/cliente/a/dato'):
                self.assertEqual(h._api_get(ruta, {}, {}, {})[0], 403)
        self.assertEqual(h.llamadas, [])

    def test_lecturas_delegan_sin_ampliar_permiso(self):
        h = self.controlador()
        with patch.dict(os.environ, {'RO_PILOTO_LECTURA': '1'}):
            for ruta in ('/api/sesion', '/api/cerebro/borrador', '/api/mi_trabajo',
                         '/api/modulo/crm/crm', '/api/cliente/a', '/api/historial/reuniones'):
                self.assertEqual(h._api_get(ruta, {}, {}, {}), 'lectura con permisos originales')
            self.assertEqual(piloto.modulos_disponibles({'ficha': 1, 'envios': 2, 'nueva': 3}), {'ficha': 1})

    def test_fuentes_piloto_exactas_y_paneles_tres_segmentos(self):
        h = self.controlador()
        rutas = ['/api/modulo/'+rel for rel in piloto.FUENTES_LECTURA | piloto.FUENTES_EMPRESA]
        rutas += ['/api/modulo/paneles/'+herr+'/cliente_fixture' for herr in piloto.HERRAMIENTAS_PANELES]
        with patch.dict(os.environ, {'RO_PILOTO_LECTURA':'1'}):
            for ruta in rutas:
                self.assertEqual(h._api_get(ruta, {}, {}, {}), 'lectura con permisos originales')
        self.assertEqual(len(h.llamadas),len(rutas))

    def test_no_carpeta_generica_ni_travesia_ni_privados(self):
        h = self.controlador()
        rutas = ('/api/modulo/personas_m20/equipo', '/api/modulo/personas_m20/contratacion',
                 '/api/modulo/horas/horas', '/api/modulo/finanzas/panel', '/api/modulo/ficha/_privado',
                 '/api/modulo/ficha/_privado/contactos', '/api/modulo/verdad/equipo',
                 '/api/modulo/paneles/nueva/cliente', '/api/modulo/paneles/empresa/nueva',
                 '/api/modulo/paneles/meta/cliente/extra', '/api/modulo/paneles/meta/../cliente',
                 '/api/modulo/paneles/meta/%2e%2e', '/api/modulo/paneles/meta/cliente.json',
                 '/api/modulo/captacion/captacion/extra', '/api/modulo/captacion//captacion',
                 '/api/modulo/ficha/portal?otro=1', '/api/cliente/../cliente',
                 '/api/cliente/%2fcliente', '/api/cliente/cliente/extra')
        with patch.dict(os.environ, {'RO_PILOTO_LECTURA':'1'}):
            for ruta in rutas:
                self.assertEqual(h._api_get(ruta, {}, {}, {})[0], 403, ruta)
        self.assertEqual(h.llamadas, [])

    def test_herramientas_coinciden_con_catalogo_frontend(self):
        import re
        s = Path(__file__).with_name('modulos').joinpath('paneles.js').read_text()
        herr = s.split('const HERR = {',1)[1].split('\n};',1)[0]
        self.assertEqual(piloto.HERRAMIENTAS_PANELES, set(re.findall(r'^  (\w+): \{',herr,re.M)))

    def test_enganchado_despues_de_modulos_y_sesion_marcada(self):
        from pathlib import Path
        s = Path(__file__).with_name('servir.py').read_text()
        self.assertGreater(s.index('PILOTO_LECTURA.enganchar(Manejador)'), s.index('BORRADORES_API.enganchar'))
        self.assertIn('"soloLectura": solo_lectura or PILOTO_LECTURA.activo()', s)


if __name__ == '__main__': unittest.main()
