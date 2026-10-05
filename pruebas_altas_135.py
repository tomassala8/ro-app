"""N9 sobre SQLite temporal y dependencias locales inyectadas; sin servidor ni ficheros reales."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('n9_135', Path(__file__).with_name('altas_personas.py'))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


class N9(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / 'fixture.db'
        self.real = {'id': 'mili', 'alias': 'Mili', 'puestos': ['operaciones']}
        self.personas = [self.real, {'id': 'old', 'alias': 'Old', 'puestos': ['account'], 'estado': 'activo'},
                         {'id': 'new', 'alias': 'New', 'puestos': ['account'], 'estado': 'activo'},
                         {'id': 'aux', 'alias': 'Aux', 'puestos': ['account'], 'estado': 'activo'}]
        self.asignaciones = [{'cliente_id': 'fixture', 'silla': 'account', 'persona_id': 'old', 'principal': True,
                             'desde': '2026-09-01', 'hasta': None, 'fuente': 'fixture', 'suplencia': False},
                            {'cliente_id': 'fixture', 'silla': 'account', 'persona_id': 'aux', 'principal': False,
                             'desde': '2026-09-01', 'hasta': None, 'fuente': 'fixture', 'suplencia': False},
                            {'cliente_id': 'otro', 'silla': 'account', 'persona_id': 'old', 'principal': True,
                             'desde': '2026-09-01', 'hasta': None, 'fuente': 'fixture', 'suplencia': False}]
        def conectar():
            c = sqlite3.connect(self.db)
            c.row_factory = sqlite3.Row
            return c
        self.conectar = conectar
        with conectar() as c:
            c.executescript('CREATE TABLE historial(n INTEGER PRIMARY KEY, quien TEXT, coleccion TEXT, id TEXT, operacion TEXT, antes TEXT, datos TEXT);' + M.TABLA_SQL)
        self.E = SimpleNamespace(crudo={'personas': self.personas, 'asignaciones': self.asignaciones,
                                      'clientes': [{'id': 'fixture'}, {'id': 'otro'}]}, nucleo_bloqueado=False)
        self.E.persona = lambda pid: next((p for p in self.E.crudo['personas'] if p['id'] == pid), None)
        def recargar(*args):
            with conectar() as c:
                for r in c.execute("SELECT id, datos FROM historial WHERE coleccion='personas' AND operacion='crear'"):
                    if not self.E.persona(r['id']):
                        self.E.crudo['personas'].append(json.loads(r['datos']))
                self.E.crudo['asignaciones'] = M.asignaciones_actuales(c)
        self.E.recargar_personas = Mock(side_effect=recargar)
        M.S = SimpleNamespace(E=self.E, conectar=conectar, ahora=lambda: '2026-10-03T12:00:00',
                              registrar=Mock(), pedir_recarga=Mock())
        M.P = SimpleNamespace(hoy_iso=lambda: '2026-10-03', PUESTO={'account': {'nombre': 'Account', 'nivel': 7},
                              'operaciones': {'nombre': 'Operaciones', 'nivel': 2}, 'direccion': {'nombre': 'Dirección', 'nivel': 1}},
                              REGLAS={'sillas_de_puesto': {'account': ['account']}},
                              contexto=lambda *args: {}, ver=lambda real, *args: {'ok': real['id'] in ('mili', 'tomas')})
        self.patches = [patch.object(M, 'comprobar', return_value={'fixture': True}),
                        patch.object(M, 'correo_libre', return_value=True), patch.object(M, 'guardar_correo'),
                        patch.object(M, 'actualizar_lista_access')]
        for p in self.patches:
            p.start()
        self.h = SimpleNamespace(responder=lambda status, body: (status, body))
        self.alta = {'nombre': 'Persona Fixture', 'puestos': ['account'], 'jefe': 'old', 'zona': 'Europe/Madrid',
                     'correo_entrada': 'fixture@rankingonline.com', 'cartera': [{'cliente_id': 'fixture', 'silla': 'account'}]}
        self.reparto = {'filas': [{'cliente_id': 'fixture', 'silla': 'account', 'persona_id': 'new'}]}

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def hist_count(self):
        with self.conectar() as c:
            return c.execute('SELECT count(*) FROM historial').fetchone()[0]

    def pedir(self, ruta, b, real=None, vista=None):
        r = real or self.real
        return M.post(self.h, '/api/altas/' + ruta, r, vista or r, b)

    def test_reparto_repetido_y_apoyos_otras_carteras(self):
        status, primera = self.pedir('repartir', self.reparto)
        self.assertEqual(status, 200)
        self.assertEqual(primera['repartidas'], 1)
        self.assertEqual(primera['cerradas'], 1)
        cuenta = self.hist_count()
        segunda = self.pedir('repartir', self.reparto)[1]
        self.assertTrue(segunda['sin_cambios'])
        self.assertEqual(self.hist_count(), cuenta)
        actual = self.E.crudo['asignaciones']
        principales = [a for a in actual if a['cliente_id'] == 'fixture' and a.get('principal', True) and not a.get('hasta')]
        self.assertEqual([a['persona_id'] for a in principales], ['new'])
        self.assertTrue(any(a['persona_id'] == 'aux' and not a['hasta'] for a in actual))
        self.assertTrue(any(a['cliente_id'] == 'otro' and not a['hasta'] for a in actual))
        viejo = next(a for a in actual if a['cliente_id'] == 'fixture' and a['persona_id'] == 'old')
        self.assertEqual((viejo['desde'], viejo['hasta']), ('2026-09-01', '2026-10-02'))

    def test_reparto_snapshot_no_recargado(self):
        self.E.recargar_personas.side_effect = None
        self.pedir('repartir', self.reparto)
        cuenta = self.hist_count()
        self.assertTrue(self.pedir('repartir', self.reparto)[1]['sin_cambios'])
        self.assertEqual(self.hist_count(), cuenta)

    def test_reparto_filas_duplicadas_y_conflictivas(self):
        self.assertEqual(self.pedir('repartir', {'filas': self.reparto['filas'] * 2})[1]['repartidas'], 1)
        cuenta = self.hist_count()
        filas = self.reparto['filas'] + [{'cliente_id': 'fixture', 'silla': 'account', 'persona_id': 'aux'}]
        self.assertEqual(self.pedir('repartir', {'filas': filas})[0], 400)
        self.assertEqual(self.hist_count(), cuenta)

    def test_reparto_preserva_suplencia(self):
        self.asignaciones.append({'cliente_id': 'fixture', 'silla': 'account', 'persona_id': 'aux',
                                 'principal': True, 'suplencia': True, 'desde': '2026-10-01', 'hasta': '2026-10-10'})
        self.pedir('repartir', self.reparto)
        suplencia = next(a for a in self.E.crudo['asignaciones'] if a.get('suplencia'))
        self.assertEqual(suplencia['hasta'], '2026-10-10')

    def test_reparto_rollback_segunda_fila(self):
        original = M.asig_crear
        def fallar(*args, **kwargs):
            if args[3] == 'otro':
                raise RuntimeError('fixture fallo')
            return original(*args, **kwargs)
        filas = self.reparto['filas'] + [{'cliente_id': 'otro', 'silla': 'account', 'persona_id': 'new'}]
        with patch.object(M, 'asig_crear', side_effect=fallar), self.assertRaises(RuntimeError):
            self.pedir('repartir', {'filas': filas})
        self.assertEqual(self.hist_count(), 0)

    def test_alta_recibo_tarea_y_retry_correo(self):
        M.guardar_correo.side_effect = OSError('fixture fallo')
        status, primera = self.pedir('alta', self.alta)
        self.assertEqual(status, 200)
        self.assertTrue(primera['alta_guardada'])
        self.assertEqual(primera['estado'], 'guardada_con_pendientes')
        self.assertIn('correo_entrada', primera['pendientes_locales'])
        M.actualizar_lista_access.assert_not_called()
        cuenta = self.hist_count()
        with self.conectar() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM altas_tareas').fetchone()[0], 1)
            self.assertEqual(c.execute('SELECT estado FROM altas_tareas').fetchone()[0], 'pendiente')
            self.assertNotIn('fixture@', c.execute('SELECT resultado FROM altas_recibos').fetchone()[0])
        M.guardar_correo.side_effect = None
        M.correo_libre.return_value = False  # el retry no se rechaza como un alta nueva
        segunda = self.pedir('alta', self.alta)[1]
        self.assertEqual(segunda['id'], primera['id'])
        self.assertEqual(segunda['estado'], 'guardada')
        self.assertEqual(segunda['access_externo'], 'pendiente')
        self.assertEqual(self.hist_count(), cuenta)
        self.assertEqual(M.actualizar_lista_access.call_count, 1)
        self.pedir('alta', self.alta)
        self.assertEqual(M.guardar_correo.call_count, 2)
        self.assertEqual(M.actualizar_lista_access.call_count, 1)

    def test_alta_lista_falla_retry_no_repite_correo(self):
        M.actualizar_lista_access.side_effect = OSError('fixture')
        primera = self.pedir('alta', self.alta)[1]
        self.assertEqual(primera['pendientes_locales'], ['lista_access_local'])
        M.actualizar_lista_access.side_effect = None
        segunda = self.pedir('alta', self.alta)[1]
        self.assertEqual(segunda['id'], primera['id'])
        self.assertEqual(segunda['pendientes_locales'], [])
        self.assertEqual(M.guardar_correo.call_count, 1)

    def test_alta_tarea_falla_rollback_persona_cartera_recibo(self):
        with patch.object(M, 'nueva_tarea', side_effect=RuntimeError('fixture')), self.assertRaises(RuntimeError):
            self.pedir('alta', self.alta)
        self.assertEqual(self.hist_count(), 0)
        with self.conectar() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM altas_recibos').fetchone()[0], 0)
        M.guardar_correo.assert_not_called()

    def test_alta_recarga_falla_no_reusa_pid_otra_alta(self):
        self.E.recargar_personas.side_effect = RuntimeError('fixture')
        primera = self.pedir('alta', self.alta)[1]
        self.assertIn('vista_personas', primera['pendientes_locales'])
        segunda_alta = {**self.alta, 'nombre': 'Persona Otra', 'correo_entrada': 'otra@rankingonline.com'}
        segunda = self.pedir('alta', segunda_alta)[1]
        self.assertNotEqual(primera['id'], segunda['id'])
        self.assertEqual(self.pedir('alta', self.alta)[1]['id'], primera['id'])

    def test_reparto_commit_con_recarga_fallida_retry_coherente(self):
        self.E.recargar_personas.side_effect = RuntimeError('fixture')
        primera = self.pedir('repartir', self.reparto)
        self.assertEqual(primera[0], 200)
        self.assertEqual(primera[1]['pendientes_locales'], ['vista_personas'])
        cuenta = self.hist_count()
        self.assertTrue(self.pedir('repartir', self.reparto)[1]['sin_cambios'])
        self.assertEqual(self.hist_count(), cuenta)

    def test_hook_real_con_sqlite_temporal(self):
        class Estado:
            def aplicar_ajustes(self, crudo):
                pass
            def por_correo(self, correo):
                return None
        class Handler:
            def _api_get(self, *args):
                return 'fuera'
            def api_post(self, *args):
                return 'fuera'
            def responder(self, status, body):
                return status, body
        M.S.Estado = Estado
        M.S.P = M.P
        M.enganchar(Handler, M.S)
        h = Handler()
        self.assertEqual(h.api_post('/api/otro', self.real, self.real, {}), 'fuera')
        first = h.api_post('/api/altas/alta', self.real, self.real, self.alta)
        count = self.hist_count()
        second = h.api_post('/api/altas/alta', self.real, self.real, self.alta)
        self.assertEqual(first[1]['id'], second[1]['id'])
        self.assertEqual(self.hist_count(), count)
        vista = {'id': 'old'}
        self.assertEqual(h.api_post('/api/altas/repartir', self.real, vista, self.reparto)[0], 403)

    def test_alta_cartera_no_retroactiva_y_futura(self):
        for entrada in ('2020-01-01', '2026-11-01'):
            with self.subTest(entrada=entrada):
                datos = {**self.alta, 'fecha_entrada': entrada, 'nombre': 'Fixture Antiguo' if entrada.startswith('2020') else 'Fixture Futuro',
                         'correo_entrada': None}
                status, alta = self.pedir('alta', datos)
                self.assertEqual(status, 200)
                actual = next(a for a in self.E.crudo['asignaciones'] if a['persona_id'] == alta['id'])
                self.assertEqual(actual['desde'], max(entrada, '2026-10-03'))

    def test_reparto_no_solapa_cierre_programado(self):
        self.asignaciones[0]['hasta'] = '2026-11-01'
        status, _ = self.pedir('repartir', self.reparto)
        self.assertEqual(status, 400)
        self.assertEqual(self.hist_count(), 0)
        self.assertEqual(self.asignaciones[0]['hasta'], '2026-11-01')

    def test_ids_nominales_reservados_sin_catalogo(self):
        for nombre in ('Tomas', 'Cecilia'):
            with self.subTest(nombre=nombre):
                datos = {**self.alta, 'nombre': nombre, 'correo_entrada': None, 'cartera': []}
                status, alta = self.pedir('alta', datos)
                self.assertEqual(status, 200)
                self.assertNotEqual(alta['id'], nombre.lower())
                self.assertTrue(alta['id'].startswith(nombre.lower() + '_'))
        self.assertTrue(M.es_tomas({'id': 'tomas', 'puestos': ['direccion']}))
        self.assertFalse(M.es_tomas({'id': 'nuevo', 'puestos': ['direccion']}))
        self.assertFalse(M.es_tomas({'id': 'tomas', 'puestos': ['account']}))

    def test_guardia_admin_y_vercomo_antes_escrituras(self):
        admin = {'id': 'admin', 'puestos': ['administracion']}
        for ruta, datos, real, vista in [('alta', self.alta, admin, admin), ('repartir', self.reparto, self.real, {'id': 'old'})]:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.pedir(ruta, datos, real, vista)[0], 403)
        self.assertEqual(self.hist_count(), 0)
        M.guardar_correo.assert_not_called()


if __name__ == '__main__':
    unittest.main()
