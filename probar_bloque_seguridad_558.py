import ast
import copy
import io
import json
import sqlite3
import tempfile
import types
import unittest
from email.message import Message
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
import permisos as P
import probar_rastro_actual_544 as R

ROOT = Path(__file__).parent


class Bloque558(unittest.TestCase):
    def test_aplicar_respuestas_no_sombrea_reloj(self):
        tree = ast.parse((ROOT / 'servir.py').read_text())
        fn = copy.deepcopy(next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'aplicar_ajustes'))
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'fixture.sqlite'
            def con():
                c = sqlite3.connect(str(path)); c.row_factory = sqlite3.Row; return c
            with con() as c:
                c.execute('CREATE TABLE historial(n INTEGER,coleccion TEXT)')
                c.execute('CREATE TABLE decisiones(id INTEGER,tipo TEXT,respuesta TEXT,anula_a INTEGER)')
                c.execute('INSERT INTO decisiones VALUES (1,?,?,NULL)', ('para_confirmar', '[{"duda":"d1"}]'))
            calls = []
            ns = {'conectar': con, 'json': json, 'P': P, 'hoy': lambda: '2026-10-04',
                  'aplicar_respuestas': lambda *a, **kw: calls.append(a) or [{'duda': 'd1'}]}
            exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), 'Estado_actual558', 'exec'), ns)
            raw = {'personas': [], 'clientes': [], 'asignaciones': [], 'para_confirmar': [{'id': 'd1'}]}
            ns['aplicar_ajustes'](types.SimpleNamespace(id_app=lambda x: x), raw)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][-1], '2026-10-04')
            self.assertTrue(raw['para_confirmar'][0]['respondida'])

    def test_rastro_viewas_interseccion_registros(self):
        f = R.RastroActual544(); f.setUp()
        try:
            with f.f.con() as c:
                c.execute('INSERT INTO registro VALUES (3,?,?,?)', ('account1', 'account2', 'Cruce sintético'))
            code, d = f.leer(f.f.otra)
            self.assertEqual(code, 200)
            self.assertEqual({r['id'] for r in d['registro']}, {3})
            self.assertFalse(d['todo'])
        finally: f.tearDown()

    def test_acciones_sinmodulo_viewas_vacio_sin_io(self):
        f = R.RastroActual544(); f.setUp()
        try:
            def fail(): raise AssertionError('Se consultó la base de acciones')
            f.f.hook = fail
            code, d = f.f.request(vista=f.f.otra)
            self.assertEqual(code, 200); self.assertEqual(d, {'modulo': None, 'acciones': []})
        finally: f.tearDown()

    def test_head_uniforme_405_sin_metadata_ni_lectura(self):
        tree = ast.parse((ROOT / 'servir.py').read_text())
        method = copy.deepcopy(next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'do_HEAD'))
        cls = ast.ClassDef(name='Handler558', bases=[ast.Name(id='SimpleHTTPRequestHandler', ctx=ast.Load())],
                           keywords=[], body=[method], decorator_list=[])
        ns = {'SimpleHTTPRequestHandler': SimpleHTTPRequestHandler}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[])), 'HEAD_actual558', 'exec'), ns)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'data' / '_privado'; path.mkdir(parents=True)
            (path / 'sintetico.db').write_bytes(b'contenido_sintetico')
            for ruta in ('/data/_privado/sintetico.db', '/app.js', '/api/sesion', '/no_existe'):
                h = ns['Handler558'].__new__(ns['Handler558'])
                h.directory = td; h.path = ruta; h.headers = Message()
                h.request_version = 'HTTP/1.1'; h.requestline = 'HEAD '+ruta+' HTTP/1.1'
                h.wfile = io.BytesIO(); h.log_request = lambda *a: None
                def no_leer(): raise AssertionError('HEAD no puede seleccionar archivo')
                h.send_head = no_leer
                h.do_HEAD(); out = h.wfile.getvalue()
                self.assertIn(b'405 Method Not Allowed', out); self.assertIn(b'Content-Length: 0', out)
                self.assertIn(b'Allow: GET, POST', out); self.assertIn(b'Cache-Control: no-store', out)
                self.assertEqual(out.split(b'\r\n\r\n')[1], b'')

    def test_rastro_real_self_intacto_y_auditor_ambos(self):
        f = R.RastroActual544(); f.setUp()
        try:
            self.assertEqual([r['id'] for r in f.leer()[1]['registro']], [1])
            self.assertEqual(len(f.f.request()[1]['acciones']), 1)
            f.f.real['puestos'] = ['direccion']
            self.assertEqual({r['id'] for r in f.leer()[1]['registro']}, {1, 2})
            f.f.otra['puestos'] = ['direccion']
            self.assertEqual(f.leer(f.f.otra)[1]['registro'], [])
        finally: f.tearDown()

    def test_558_1_viewas_todos_roles_solo_inspeccion_sin_leer_acciones(self):
        for roles_real, roles_vista in [('account', 'account'), ('direccion', 'account'),
                                       ('account', 'direccion'), ('direccion', 'direccion')]:
            with self.subTest(real=roles_real, vista=roles_vista):
                f = R.RastroActual544(); f.setUp()
                try:
                    f.f.real['puestos'] = [roles_real]
                    f.f.otra.update(id='tomas', puestos=[roles_vista])
                    with f.f.con() as c:
                        c.execute("UPDATE registro SET quien='tomas' WHERE id=2")
                        c.execute('INSERT INTO registro VALUES (3,?,?,?)', ('account1', 'tomas', 'Esta inspección'))
                        c.execute('INSERT INTO registro VALUES (4,?,?,?)', ('tomas', 'account1', 'Inspección inversa'))
                        c.execute('INSERT INTO registro VALUES (5,?,?,?)', ('account1', 'otra_vista', 'Otra inspección'))
                    sqls = []
                    conectar = f.get.__globals__['conectar']
                    def con():
                        c = conectar(); c.set_trace_callback(sqls.append); return c
                    f.get.__globals__['conectar'] = con
                    code, d = f.leer(f.f.otra)
                    self.assertEqual(code, 200); self.assertFalse(d['todo'])
                    self.assertEqual([r['id'] for r in d['registro']], [3])
                    self.assertEqual(d['acciones'], [])
                    self.assertFalse(any('FROM acciones' in s for s in sqls))
                finally: f.tearDown()

    def test_modulo_explicitado_mantiene_cartera_compartida(self):
        f = R.RastroActual544(); f.setUp()
        try:
            f.f.e.crudo['asignaciones'].append({'cliente_id': 'cid1', 'persona_id': 'account2', 'silla': 'account'})
            self.assertEqual(len(f.f.request('salud-crm', f.f.otra)[1]['acciones']), 1)
            self.assertEqual(f.f.request(vista=f.f.otra)[1]['acciones'], [])
        finally: f.tearDown()


if __name__ == '__main__': unittest.main()
