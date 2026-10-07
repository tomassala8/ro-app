"""Catálogo sintético; no importa servidor, almacenamiento ni proveedor."""
import ast
from pathlib import Path
import unittest


class FinalTarea(unittest.TestCase):
    def setUp(self):
        self.doc = {'estados_lista': {'lista': ['completado', 'rechazado']},
                    'estados_detalle': {'lista': [{'estado': 'completado', 'tipo': 'done'},
                                                {'estado': 'rechazado', 'tipo': 'closed'}]}}
        tree = ast.parse(Path(__file__).with_name('sincronia.py').read_text())
        funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name in ('estados_de_tarea', 'estados_hecha_de_tarea')]
        self.ns = {'_mi_trabajo_tarea': lambda ref: {'lista_id': 'lista'} if ref == 'tarea' else None,
                   '_mi_trabajo': lambda: self.doc,
                   'conf': lambda: {'estados_hecha': ['completado', 'done']}}
        exec(compile(ast.Module(body=funcs, type_ignores=[]), 'fuente_real', 'exec'), self.ns)

    def finales(self):
        return self.ns['estados_hecha_de_tarea']('tarea')

    def test_final_tipado_y_rechazado_no_elegido(self):
        self.assertEqual(self.finales(), ['completado'])

    def test_nombre_enganoso_custom(self):
        self.doc['estados_detalle']['lista'][0]['tipo'] = 'custom'
        self.assertEqual(self.finales(), [])

    def test_sin_catalogo_tipado(self):
        self.doc.pop('estados_detalle')
        self.assertEqual(self.finales(), [])

    def test_catalogo_duplicado_conflictivo(self):
        self.doc['estados_detalle']['lista'].append({'estado': 'completado', 'tipo': 'custom'})
        self.assertEqual(self.finales(), [])

    def test_final_otra_lista_no_autoriza(self):
        self.doc['estados_lista']['lista'] = ['rechazado']
        self.assertEqual(self.finales(), [])
        self.assertEqual(self.ns['estados_hecha_de_tarea']('otra'), [])

    def test_finalizacion_validacion_y_envio_comparten_selector(self):
        base = Path(__file__).parent
        # La misma función probada debe resolver ambas fases, evitando validar una cosa y enviar otra.
        for nombre, funcion in [('mi_trabajo.py', 'validar'), ('sincronia.py', 'resolver')]:
            tree = ast.parse((base / nombre).read_text())
            funciones = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                         and (n.name == funcion or (nombre == 'sincronia.py' and 'estado_hecha' in ast.unparse(n)))]
            self.assertTrue(any('estados_hecha_de_tarea' in ast.unparse(n) for n in funciones))


if __name__ == '__main__':
    unittest.main()
