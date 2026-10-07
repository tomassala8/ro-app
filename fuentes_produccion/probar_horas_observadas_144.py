import ast
import datetime as dt
import math
from collections import defaultdict
from pathlib import Path
import unittest


class HorasObservadas(unittest.TestCase):
    def setUp(self):
        tree = ast.parse(Path(__file__).with_name('generar_produccion.py').read_text())
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'sumar_horas_cliente')
        ns = {'dt': dt, 'math': math, 'defaultdict': defaultdict}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), 'fuente_real', 'exec'), ns)
        self.sumar = lambda rows: ns['sumar_horas_cliente'](rows, {'carpeta': ('cliente', '')}, dt.date(2026, 10, 3))

    def fila(self, fecha='2026-10-01', horas=1):
        return {'carpeta_id': 'carpeta', 'inicio': fecha, 'horas': horas}

    def test_ausencia_no_es_cero(self):
        a, b, n = self.sumar([])
        self.assertNotIn('cliente', a)
        self.assertEqual(n, 0)

    def test_cero_explicito_observado(self):
        self.assertEqual(self.sumar([self.fila(horas=0)])[0]['cliente'], 0)

    def test_meses_y_futuro(self):
        a, b, n = self.sumar([self.fila(), self.fila('2026-09-30', 2), self.fila('2026-08-31', 4), self.fila('2026-10-04', 8)])
        self.assertEqual(a, {'cliente': 1})
        self.assertEqual(b, {'cliente': 2})

    def test_invalidas_no_contaminan_ni_rompen(self):
        rows = [self.fila(horas=x) for x in (True, '1', -1, float('nan'), float('inf'), 11)]
        rows += [self.fila('2026-02-30'), None, self.fila()]
        a, b, n = self.sumar(rows)
        self.assertEqual(a, {'cliente': 1})
        self.assertEqual(n, 8)

    def test_carpeta_sin_identidad_no_atribuye(self):
        row = self.fila(); row['carpeta_id'] = 'otra'
        self.assertEqual(self.sumar([row])[0], {})


if __name__ == '__main__':
    unittest.main()
