import unittest
from datetime import datetime, timezone
from informes_tareas_api import preparar


class Informes(unittest.TestCase):
    def setUp(self):
        self.t = {'id': 't', 'estado': 'complete', 'tipo_estado': 'closed', 'lista_id': 'l',
                  'cerrada': int(datetime(2026, 9, 15, tzinfo=timezone.utc).timestamp() * 1000),
                  'nombre': 'PRIVADO NO PUBLICAR', 'descripcion': 'PRIVADA'}
        self.seg = [{'id': 't', 'cli': 'cliente', 'tarea': 'Nombre saneado'}]
        self.cat = {'listas': {'l': {'ok': True, 'estados': [{'status': 'complete', 'type': 'closed'}]}}}

    def salida(self, ts=None, cat=None):
        return preparar('cliente', '2026-09-01', '2026-09-30', self.seg,
                        {'meta': {'generado': '2026-10-03'}, 'tareas': ts if ts is not None else [self.t]},
                        cat if cat is not None else self.cat)

    def test_final_documentado_sin_texto_privado(self):
        d = self.salida()
        self.assertEqual(d['cobertura'], 'parcial')
        self.assertEqual(d['tareas'][0]['nombre'], 'Nombre saneado')
        self.assertEqual(d['tareas'][0]['tipo_evidencia'], 'finalizacion_flujo')
        self.assertNotIn('PRIVAD', str(d))

    def test_catalogo_ausente_no_infiere_por_nombre(self):
        self.assertEqual(self.salida(cat={})['tareas'], [])

    def test_estado_custom_llamado_complete_no_final(self):
        self.t['tipo_estado'] = 'custom'
        self.cat['listas']['l']['estados'][0]['type'] = 'custom'
        self.assertEqual(self.salida()['tareas'], [])

    def test_fecha_fuera_periodo_y_booleanos(self):
        for fecha in (True, None, 'ayer', 0, 1e309, 1790812800000):
            self.t['cerrada'] = fecha
            self.assertEqual(self.salida()['tareas'], [])

    def test_duplicados_ambiguos_fuera(self):
        self.assertEqual(self.salida(ts=[self.t, dict(self.t)])['tareas'], [])

    def test_cliente_no_autorizado_fuera(self):
        self.seg[0]['cli'] = 'otro'
        self.assertEqual(self.salida()['tareas'], [])

    def test_periodo_invalidado(self):
        for desde, hasta in [('2026-10-03', '2026-09-01'), ('2024-01-01', '2026-09-01'), ('foo', 'bar')]:
            with self.assertRaises(ValueError):
                preparar('cliente', desde, hasta, self.seg, {}, {})


if __name__ == '__main__':
    unittest.main()
