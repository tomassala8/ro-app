"""Regresiones del filtro operativo; catálogo sintético, sin editar fuentes reales."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fuentes_verdad import clientes_activos as A


class Operativos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name) / 'estado.json'
        self.p.write_text(json.dumps({'activos': [
            {'id': 'vigente', 'tipo': 'recurrente'}, {'id': 'nuevo', 'tipo': 'firmado_sin_ficha'},
            {'id': 'dudoso', 'tipo': 'dudoso'}, {'id': 'medalba', 'tipo': 'recurrente'}],
            'bajas_ids': ['baja'], 'bajas': []}))
        self.mock = patch.object(A, 'ESTADO', self.p)
        self.mock.start()
        A._CACHE.update(marca=None, estado=None)

    def tearDown(self):
        self.mock.stop()
        A._CACHE.update(marca=None, estado=None)
        self.tmp.cleanup()

    def test_confirmados_y_prioridad_feedback(self):
        self.assertTrue(A.es_activo_id('vigente'))
        self.assertTrue(A.es_activo_id('nuevo'))
        for cid in ('dudoso', 'medalba', 'baja', 'desconocido'):
            self.assertFalse(A.es_activo_id(cid))

    def test_filas_distintas_fuentes(self):
        for campo in ('cliente_id', 'cid', 'cli'):
            self.assertEqual(A.quitar_bajas([{'id': 't', campo: 'medalba'},
                {'id': 'v', campo: 'vigente'}]), [{'id': 'v', campo: 'vigente'}])
        self.assertTrue(A.fila_de_baja({'cliente': 'Medalba', 'dominio': 'medalba.com'}))
        self.assertFalse(A.fila_de_baja({'tarea': 'Reunión interna'}))

    def test_nucleo_desconocidos_fuera(self):
        d = {'clientes': [{'id': c} for c in ('vigente', 'medalba', 'dudoso')],
             'asignaciones': [{'cliente_id': c} for c in ('vigente', 'desconocido')],
             'alarmas': [{'cliente_id': 'medalba'}, {'tipo': 'interno'}],
             'logos': {'vigente': 'a', 'medalba': 'b'}}
        A.limpiar_nucleo(d)
        self.assertEqual(d['clientes'], [{'id': 'vigente', 'activo_confirmado': True}])
        self.assertEqual(d['asignaciones'], [{'cliente_id': 'vigente'}])
        self.assertEqual(d['alarmas'], [{'tipo': 'interno'}])
        self.assertEqual(d['logos'], {'vigente': 'a'})

    def test_sin_catalogo_no_habilita_clientes(self):
        self.p.unlink()
        self.assertFalse(A.es_activo_id('vigente'))
        self.assertTrue(A.fila_de_baja({'cliente': 'Medalba'}))
        self.assertEqual(A.quitar_bajas([{'cliente_id': 'vigente'}]), [])

    def test_historial_separado_no_exenta_panel_operativo(self):
        d = [{'cliente_id': 'baja'}]
        self.assertEqual(A.quitar_bajas(d, 'informes/archivo'), d)
        self.assertEqual(A.quitar_bajas(d, 'panel_direccion/resumen'), [])


if __name__ == '__main__':
    unittest.main()
