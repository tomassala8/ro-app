"""Preferencias privadas en SQLite temporal, sin tareas/ficheros/proveedores reales."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import vistas_tareas as V
import tareas_local as T


class Vistas(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / 'fixture.db'
        self.tareas = [{'id': 'fixture', 'asignados': ['ana'], 'cli': 'cliente-fixture', 'lista_id': 'lista-fixture',
                        'proyecto': 'Proyecto fixture', 'etiquetas': ['Urgente'], 'prio_n': 1}]
        self.filtros = {**V.DEFAULT, 'cliente': 'cliente-fixture', 'lista': 'lista-fixture'}
        with self.con() as c:
            c.execute('CREATE TABLE negocio (valor TEXT)')
            c.execute("INSERT INTO negocio VALUES ('intacto')")

    def tearDown(self):
        self.tmp.cleanup()

    def con(self):
        c = sqlite3.connect(self.db, timeout=10)
        c.row_factory = sqlite3.Row
        return c

    def guardar(self, nombre='Fixture', actor='ana', **extras):
        with self.con() as c:
            return V.mutar(c, actor, {'accion': 'guardar', 'nombre': nombre, 'filtros': self.filtros, **extras}, self.tareas)['vista']

    def test_persiste_entre_conexiones_no_snapshot(self):
        guardada = self.guardar()
        with self.con() as c:
            d = V.listar(c, 'ana')
            self.assertEqual(d['vistas'], [guardada])
            self.assertEqual(c.execute('SELECT valor FROM negocio').fetchone()[0], 'intacto')
            body = c.execute('SELECT filtros FROM tareas_vistas_privadas').fetchone()[0]
            self.assertEqual(set(json.loads(body)), V.CAMPOS)
            self.assertNotIn('tareas', body)

    def test_aislamiento_y_ids_ajenos(self):
        ana = self.guardar()
        with self.con() as c:
            self.assertEqual(V.listar(c, 'bob')['vistas'], [])
            with self.assertRaises(V.Conflicto):
                V.mutar(c, 'bob', {'accion': 'eliminar', 'id': ana['id'], 'revision': ana['revision']}, [])
        with self.con() as c:
            self.assertEqual(V.listar(c, 'ana')['vistas'], [ana])

    def test_revision_concurrente_no_sobrescribe(self):
        original = self.guardar()
        actual = self.guardar('Cambio', id=original['id'], revision=original['revision'])
        with self.assertRaises(V.Conflicto):
            self.guardar('Obsoleto', id=original['id'], revision=original['revision'])
        with self.con() as c:
            self.assertEqual(V.listar(c, 'ana')['vistas'], [actual])
            with self.assertRaises(V.Conflicto):
                V.mutar(c, 'ana', {'accion': 'eliminar', 'id': original['id'], 'revision': original['revision']}, [])

    def test_limites_nombre_y_campos(self):
        for nombre in ('', 'x' * 61, 'Texto\nextra'):
            with self.subTest(nombre=nombre), self.assertRaises(ValueError):
                self.guardar(nombre)
        for extra in ('buscar', 'propietario', 'persona_id', 'flujo'):
            with self.subTest(extra=extra), self.con() as c, self.assertRaises(ValueError):
                V.mutar(c, 'ana', {'accion': 'guardar', 'nombre': 'Fixture', 'filtros': {**self.filtros, extra: 'texto'}}, self.tareas)
        for valor in (True, [], 1, None):
            with self.subTest(valor=valor), self.con() as c, self.assertRaises(ValueError):
                V.mutar(c, 'ana', {'accion': 'guardar', 'nombre': 'Fixture', 'filtros': {**self.filtros, 'cliente': valor}}, self.tareas)

    def test_referencia_no_autorizada_y_revocada_no_amplia(self):
        original = self.guardar()
        with self.con() as c:
            # Revocación: devuelve preferencia privada intacta, no transforma filtro en todos.
            self.assertEqual(V.listar(c, 'ana')['vistas'][0]['filtros']['cliente'], 'cliente-fixture')
            with self.assertRaises(ValueError):
                V.mutar(c, 'ana', {'accion': 'guardar', 'id': original['id'], 'revision': 1,
                    'nombre': 'Actualizada', 'filtros': self.filtros}, [])
        with self.con() as c:
            self.assertEqual(V.listar(c, 'ana')['vistas'], [original])
            self.assertTrue(V.mutar(c, 'ana', {'accion': 'eliminar', 'id': original['id'], 'revision': 1}, [])['ok'])

    def test_corrupcion_no_aplica_ni_borra(self):
        original = self.guardar()
        with self.con() as c:
            c.execute('UPDATE tareas_vistas_privadas SET filtros=?', ('{"vista":"mia","vista":"equipo"}',))
        with self.con() as c:
            self.assertEqual(V.listar(c, 'ana')['vistas'], [])
            self.assertEqual(V.listar(c, 'ana')['invalidas'], 1)
            self.assertEqual(c.execute('SELECT count(*) FROM tareas_vistas_privadas').fetchone()[0], 1)
        with self.con() as c:
            c.execute('UPDATE tareas_vistas_privadas SET filtros=?, version=?', (json.dumps(self.filtros), 999))
        with self.con() as c:
            self.assertEqual(V.listar(c, 'ana')['invalidas'], 1)

    def test_limite_20_con_creacion_concurrente(self):
        with self.con() as c:
            V.preparar(c)
        def crear(i):
            try:
                return self.guardar('Vista ' + str(i))
            except ValueError:
                return None
        with ThreadPoolExecutor(max_workers=6) as ex:
            resultados = list(ex.map(crear, range(30)))
        self.assertEqual(sum(x is not None for x in resultados), 20)
        with self.con() as c:
            self.assertEqual(len(V.listar(c, 'ana')['vistas']), 20)
            self.assertEqual(c.execute('SELECT valor FROM negocio').fetchone()[0], 'intacto')

    def test_conexion_prestada_no_confirma_transaccion_ajena(self):
        with self.con() as c:
            V.preparar(c)
        for accion in ('preparar', 'listar', 'mutar'):
            with self.subTest(accion=accion):
                c = self.con()
                try:
                    c.execute("INSERT INTO negocio VALUES ('pendiente')")
                    self.assertTrue(c.in_transaction)
                    with self.assertRaises(ValueError):
                        if accion == 'preparar':
                            V.preparar(c)
                        elif accion == 'listar':
                            V.listar(c, 'ana')
                        else:
                            V.mutar(c, 'ana', {'accion': 'guardar', 'nombre': 'Fixture', 'filtros': self.filtros}, self.tareas)
                    self.assertTrue(c.in_transaction)
                    with self.con() as otra:
                        self.assertEqual(otra.execute("SELECT count(*) FROM negocio WHERE valor='pendiente'").fetchone()[0], 0)
                    c.rollback()
                    self.assertEqual(c.execute("SELECT count(*) FROM negocio WHERE valor='pendiente'").fetchone()[0], 0)
                finally:
                    c.close()

    def test_endpoint_guardias_y_dueño_servidor(self):
        ana = {'id': 'ana', 'puestos': ['account']}
        bob = {'id': 'bob', 'puestos': ['account']}
        permiso = {'ok': True}
        E = SimpleNamespace(nucleo_bloqueado=False, crudo={'personas': [ana, bob], 'asignaciones': [], 'clientes': [{'id': 'cliente-fixture', 'servicios': {'publicidad': 'sí'}}]})
        S = SimpleNamespace(E=E, conectar=self.con, ve_alguno=lambda p, _: permiso['ok'],
            P=SimpleNamespace(contexto=lambda *a: {}, ver=lambda *a: {'ok': True}))
        class H:
            def _api_get(self, *a):return 'otro'
            def api_post(self, *a):return 'otro'
            def responder(self, status, body):return status, body
        with patch.dict(sys.modules, {'sincronia': SimpleNamespace()}), patch.dict('os.environ', {}, clear=True), \
             patch.object(T, 'inventario', return_value={'tareas': self.tareas}), patch.object(T, 'leer', return_value={}), \
             patch('fuentes_verdad.clientes_activos.es_activo_id', side_effect=lambda cid: cid == 'cliente-fixture'):
            T.enganchar(H, S)
            h = H()
            self.assertEqual(h.api_post('/api/tareas/vistas', ana, bob, {})[0], 403)
            self.assertEqual(h._api_get('/api/tareas/vistas', {}, ana, bob)[0], 403)
            self.assertEqual(h.api_post('/api/tareas/vistas', ana, ana, {'accion': 'guardar', 'nombre': 'X', 'filtros': self.filtros, 'propietario': 'bob'})[0], 400)
            status, body = h.api_post('/api/tareas/vistas', ana, ana, {'accion': 'guardar', 'nombre': 'X', 'filtros': self.filtros})
            self.assertEqual(status, 200)
            self.assertEqual(h._api_get('/api/tareas/vistas', {}, bob, bob)[1]['vistas'], [])
            permiso['ok'] = False
            self.assertEqual(h._api_get('/api/tareas/vistas', {}, ana, ana)[0], 403)
            self.assertEqual(h.api_post('/api/tareas/vistas', ana, ana, {'accion': 'eliminar', 'id': body['vista']['id'], 'revision': 1})[0], 403)
            permiso['ok'] = True
            E.nucleo_bloqueado = True
            self.assertEqual(h._api_get('/api/tareas/vistas', {}, ana, ana)[0], 503)
            E.nucleo_bloqueado = False
            with patch.dict('os.environ', {'DATABASE_URL': 'fixture'}):
                self.assertEqual(h._api_get('/api/tareas/vistas', {}, ana, ana)[0], 503)
            with self.con() as c:
                self.assertEqual(V.listar(c, 'ana')['vistas'][0]['nombre'], 'X')


if __name__ == '__main__':
    unittest.main()
