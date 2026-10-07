import copy
import math
import unittest
from fuentes_horas.agrupaciones_artifact_375 import construir, grupo_titulo


class Agrupaciones(unittest.TestCase):
    def setUp(self):
        self.tareas = [{'id': f't{i}', 'cliente_id': 'c1', 'nombre': 'Optimización SEO Acme septiembre 2026'} for i in range(5)]
        self.entradas = [{'id': f'e{i}', 'usuario_id': 'u1', 'task_id': f't{i}', 'inicio': '2026-09-10T10:00:00Z', 'horas': i + 1} for i in range(5)]
        self.kw = dict(cliente_ids={'c1'}, tarea_ids={f't{i}' for i in range(5)}, usuario_ids={'u1'}, nombres_clientes=['Acme'], observado_hasta='2026-10-03T08:00:00Z', fuente={'leido': '2026-10-03T07:00:00Z', 'sha256': 'a' * 64})

    def run_helper(self, entradas=None, tareas=None, **kw):
        return construir(self.entradas if entradas is None else entradas, self.tareas if tareas is None else tareas, **{**self.kw, **kw})

    def test_cinco_columnas_misma_unidad(self):
        row = self.run_helper()['filas'][0]
        self.assertEqual(row, dict(grupo='optimizacion seo', casos=5, mediana_h=3, max_h=5, total_h=15, registros_mas10h=0))

    def test_maximo_de_suma_no_registro(self):
        self.entradas.append({**self.entradas[4], 'id': 'extra', 'horas': 2})
        r = self.run_helper()['filas'][0]
        self.assertEqual((r['max_h'], r['total_h']), (7, 17))

    def test_casos_persona_tarea_y_minimo_cinco(self):
        self.assertEqual(self.run_helper(entradas=self.entradas[:4])['filas'], [])
        self.entradas.append({**self.entradas[0], 'id': 'otheruser', 'usuario_id': 'u2', 'horas': 8})
        r = self.run_helper(usuario_ids={'u1', 'u2'})['filas'][0]
        self.assertEqual((r['casos'], r['total_h']), (6, 23))

    def test_cero_explicito_vacio_no_cero(self):
        for e in self.entradas:
            e['horas'] = 0
        r = self.run_helper()['filas'][0]
        self.assertEqual((r['casos'], r['mediana_h'], r['max_h'], r['total_h']), (5, 0, 0, 0))
        self.assertEqual(self.run_helper(entradas=[])['filas'], [])

    def test_frontera_60_fechas_madrid(self):
        # 5 agosto enMadrid está dentro;4 agosto está fuera aunque mismafechaUTC.
        for e in self.entradas:
            e['inicio'] = '2026-08-04T22:00:00Z'
        self.assertEqual(self.run_helper()['filas'][0]['total_h'], 15)
        self.entradas[0]['inicio'] = '2026-08-04T21:59:59Z'
        self.assertEqual(self.run_helper()['filas'], [])

    def test_futuros_y_tipos_invalidos(self):
        for v in (True, None, '2', float('inf'), float('nan'), -1, 10 ** 1000):
            with self.subTest(v=type(v).__name__):
                rows = copy.deepcopy(self.entradas); rows[0]['horas'] = v
                self.assertEqual(self.run_helper(entradas=rows)['filas'], [])
        for inicio in ('2026-10-03T09:00:00Z', '2026-09-10T10:00:00', 'mal'):
            rows = copy.deepcopy(self.entradas); rows[0]['inicio'] = inicio
            self.assertEqual(self.run_helper(entradas=rows)['filas'], [])

    def test_dedup_y_colision_global_ajena(self):
        self.assertEqual(self.run_helper(entradas=self.entradas + [dict(self.entradas[0])])['filas'][0]['total_h'], 15)
        foreign = {**self.entradas[0], 'usuario_id': 'ajeno', 'task_id': 'ajeno'}
        self.assertEqual(self.run_helper(entradas=self.entradas + [foreign])['filas'], [])

    def test_scope_y_tarea_duplicada(self):
        self.assertEqual(self.run_helper(cliente_ids=set())['filas'], [])
        self.assertEqual(self.run_helper(usuario_ids={'ajeno'})['filas'], [])
        self.assertEqual(self.run_helper(tareas=self.tareas + [dict(self.tareas[0])])['filas'], [])
        self.assertEqual(self.run_helper(tarea_ids={'t0'})['filas'], [])

    def test_internos_solo_explicitos(self):
        for t in self.tareas:
            t['cliente_id'] = None
        self.assertEqual(self.run_helper()['filas'], [])
        self.assertEqual(len(self.run_helper(tareas_internas=self.kw['tarea_ids'])['filas']), 1)
        del self.tareas[0]['cliente_id']
        self.assertEqual(self.run_helper(tareas_internas=self.kw['tarea_ids'])['filas'], [])

    def test_grandes_y_overflow_sin_falsear(self):
        self.entradas[4]['horas'] = 20
        r = self.run_helper()['filas'][0]
        self.assertEqual((r['max_h'], r['registros_mas10h']), (20, 1))
        for e in self.entradas:
            e['horas'] = 1e308
        self.assertEqual(self.run_helper()['filas'], [])

    def test_normalizacion_original_y_limites(self):
        self.assertEqual(grupo_titulo('ÁCME – 12 Septiembre V2 Revisión de blogs y landings externas importantes', ['Acme']), 'revision de blogs y landings')
        for kw in (dict(fuente={'leido': '2026-10-04T00:00:00Z', 'sha256': 'a' * 64}), dict(tarea_ids=['t0']), dict(nombres_clientes=['Acme', None])):
            with self.assertRaises(ValueError):
                self.run_helper(**kw)

    def test_inmutabilidad_y_no_ids_al_dto(self):
        before = copy.deepcopy((self.entradas, self.tareas, self.kw))
        r = self.run_helper()
        self.assertEqual(before, (self.entradas, self.tareas, self.kw))
        self.assertFalse(r['tipo_historico_confirmado'])
        self.assertIsNone(r['tiempo_normativo'])
        self.assertEqual(r['unidad_maximo'], 'suma_por_caso')
        self.assertFalse(any(k in row for row in r['filas'] for k in ('usuario_id', 'cliente_id', 'tarea_id', 'nombre')))

    def test_secretos_contactos_y_fuente_no_futura(self):
        for titulo in ('password secretoFixtureSoloPrueba revisión mensual', 'clave: Fixture9_Sensible', 'Enviar a ana@example.test', 'Presupuesto 5000 revisión mensual', 'Bearer ' + 'Q' * 30):
            self.assertEqual(grupo_titulo(titulo, []), '')
        self.entradas[0]['inicio'] = '2026-10-03T07:30:00Z'
        self.assertEqual(self.run_helper()['filas'], [])


if __name__ == '__main__':
    unittest.main()
