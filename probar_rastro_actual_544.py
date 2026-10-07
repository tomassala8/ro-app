import ast
import copy
import types
import unittest
from pathlib import Path
import probar_lectura_acciones_538 as F
import permisos as P


class RastroActual544(unittest.TestCase):
    def setUp(self):
        self.f = F.Lectura538(); self.f.setUp()
        with self.f.con() as c:
            c.execute('CREATE TABLE registro(id INTEGER,quien TEXT,como TEXT,datos TEXT)')
            c.execute('INSERT INTO registro VALUES (1,?,?,?)', ('account1', None, 'Metadato sintético propio'))
            c.execute('INSERT INTO registro VALUES (2,?,?,?)', ('account2', None, 'Metadato sintético ajeno'))
        tree = ast.parse((Path(__file__).parent / 'servir.py').read_text())
        b = copy.deepcopy(next(n for n in ast.walk(tree) if isinstance(n, ast.If)
            and ast.unparse(n.test) == "ruta == '/api/rastro'" and 'SELECT * FROM acciones' in ast.unparse(n)))
        fn = ast.parse('def get(self,ruta,real,persona,cp):\n pass').body[0]; fn.body = [b]
        ns = dict(self.f.get.__globals__)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), 'Rastro544_actual', 'exec'), ns)
        self.get = ns['get']

    def tearDown(self): self.f.tearDown()

    def leer(self, vista=None):
        p = vista or self.f.real
        with P.mirando_como(self.f.real, self.f.e.crudo):
            return self.get(self.f.handler, '/api/rastro', self.f.real, p, P.contexto(p, self.f.e.crudo))

    def test_actual_permitido_y_registro_propio_policy(self):
        code, d = self.leer()
        self.assertEqual(code, 200); self.assertFalse(d['todo'])
        self.assertEqual([r['id'] for r in d['registro']], [1])
        self.assertEqual(d['acciones'][0]['texto'], 'Texto sintético')

    def test_inactivo_oculta_accion_no_borra_registro_autorizado(self):
        self.f.act['cid1'] = False
        code, d = self.leer()
        self.assertEqual(code, 200); self.assertEqual(d['acciones'], [])
        self.assertEqual(d['registro'][0]['datos'], 'Metadato sintético propio')

    def test_auditoria_todo_no_abre_contenido_cliente_inactivo(self):
        self.f.real['puestos'] = ['direccion']; self.f.act['cid1'] = False
        code, d = self.leer()
        self.assertEqual(code, 200); self.assertTrue(d['todo'])
        self.assertEqual({r['id'] for r in d['registro']}, {1, 2})
        self.assertEqual(d['acciones'], [])

    def test_vista_denegada_y_rotacion_antes_respuesta(self):
        code, d = self.leer(self.f.otra)
        self.assertEqual(code, 200); self.assertEqual(d['acciones'], [])
        self.f.hook = lambda: self.f.act.update(cid1=False)
        self.assertEqual(self.leer()[0], 403)


if __name__ == '__main__': unittest.main()
