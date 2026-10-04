import ast
import copy
import json
import sqlite3
import tempfile
import types
import unittest
from pathlib import Path
import permisos as P


class Lectura538(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.path = Path(self.t.name) / 'fixture.sqlite'
        self.real = {'id': 'account1', 'puestos': ['account'], 'estado': 'activo'}
        self.otra = {'id': 'account2', 'puestos': ['account'], 'estado': 'activo'}
        self.cliente = {'id': 'cid1', 'activo': True, 'estado': 'activo'}
        self.e = types.SimpleNamespace(nucleo_bloqueado=False, modulos=P.cargar_modulos(), crudo={
            'personas': [self.real, self.otra], 'clientes': [self.cliente], 'asignaciones': [
                {'cliente_id': 'cid1', 'persona_id': 'account1', 'silla': 'account', 'principal': True,
                 'confianza': 'confirmada'}]})
        self.act = {'cid1': True}
        self.hook = None
        with self.con() as c:
            c.execute('CREATE TABLE acciones(id INTEGER PRIMARY KEY,quien TEXT,cliente_id TEXT,modulo TEXT,tipo TEXT,texto TEXT,vista_previa TEXT,estado TEXT)')
            c.execute('INSERT INTO acciones VALUES (1,?,?,?,?,?,?,?)',
                      ('account1', 'cid1', 'salud-crm', 'nota', 'Texto sintético', 'Nota sintética', 'simulada'))
        tree = ast.parse((Path(__file__).parent / 'servir.py').read_text())
        branch = copy.deepcopy(next(n for n in ast.walk(tree) if isinstance(n, ast.If)
            and ast.unparse(n.test) == "ruta == '/api/acciones'" and 'SELECT * FROM acciones' in ast.unparse(n)))
        fn = ast.parse('def get(self,ruta,real,persona,q,cp):\n pass').body[0]; fn.body = [branch]
        def ve(p, mods):
            ns = [P.nivel_modulo(p, self.e.modulos.get(m, {})) for m in mods]
            ns = [n for n in ns if n]
            return max(ns, key={'resumen': 1, 'suyo': 2, 'todo': 3}.get) if ns else None
        ns = {'P': P, 'E': self.e, 'ACT': types.SimpleNamespace(estado=lambda: dict(self.act),
              es_activo_id=lambda cid: self.act.get(cid) is True), 'conectar': self.con,
              've_alguno': ve, 'json': json}
        from probar_recorte_modulo_589 import cargar as cargar_recortes589
        ns.update(cargar_recortes589())
        helper = copy.deepcopy(next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                                    and n.name == 'recorte_importes_lectura588'))
        exec(compile(ast.fix_missing_locations(ast.Module(body=[helper], type_ignores=[])), 'recorte588_actual', 'exec'), ns)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), 'GET538_actual', 'exec'), ns)
        self.get = ns['get']; self.handler = types.SimpleNamespace(responder=lambda code, dto: (code, dto))

    def tearDown(self):
        self.t.cleanup()

    def con(self):
        c = sqlite3.connect(str(self.path)); c.row_factory = sqlite3.Row
        if self.hook:
            hook, self.hook = self.hook, None; hook()
        return c

    def request(self, mod=None, vista=None):
        p = vista or self.real
        with P.mirando_como(self.real, self.e.crudo):
            return self.get(self.handler, '/api/acciones', self.real, p,
                            {'modulo': [mod]} if mod else {}, P.contexto(p, self.e.crudo))

    def test_autorizada_shape_intacto_ambas_variantes(self):
        for mod in (None, 'salud-crm'):
            code, d = self.request(mod)
            self.assertEqual(code, 200); self.assertEqual(d['acciones'][0]['texto'], 'Texto sintético')
            self.assertEqual(d['acciones'][0]['vista_previa'], 'Nota sintética')
            self.assertEqual(d['acciones'][0]['estado'], 'simulada')

    def test_cliente_revocado_unknown_duplicado_inactivo(self):
        for cambio in ('cartera', 'act', 'unknown', 'duplicado', 'inactivo'):
            with self.subTest(cambio=cambio):
                self.t.cleanup()
                self.setUp()
                if cambio == 'cartera': self.e.crudo['asignaciones'] = []
                elif cambio == 'act': self.act['cid1'] = False
                elif cambio == 'unknown': self.e.crudo['clientes'] = []
                elif cambio == 'duplicado': self.e.crudo['clientes'].append(dict(self.cliente))
                else: self.cliente['activo'] = False
                for mod in (None, 'salud-crm'):
                    code, d = self.request(mod); self.assertEqual(code, 200); self.assertEqual(d['acciones'], [])
                self.t.cleanup()

    def test_viewas_doble_alcance_y_propias(self):
        code, d = self.request('salud-crm', self.otra)
        self.assertEqual(code, 200); self.assertEqual(d['acciones'], [])
        self.e.crudo['asignaciones'].append({'cliente_id': 'cid1', 'persona_id': 'account2', 'silla': 'account'})
        self.assertEqual(len(self.request('salud-crm', self.otra)[1]['acciones']), 1)
        self.assertEqual(self.request(vista=self.otra)[1]['acciones'], [])

    def test_modulo_revocado_no_salida(self):
        self.e.modulos['salud-crm']['account'] = None
        self.assertEqual(self.request('salud-crm')[0], 403)
        self.assertEqual(self.request()[1]['acciones'], [])

    def test_identidad_dup_baja_roles_mutados(self):
        snapshot = copy.deepcopy(self.real)
        self.e.crudo['personas'].append(dict(self.real))
        self.assertEqual(self.request()[0], 403)
        self.e.crudo['personas'].pop(); self.real['estado'] = 'baja'
        self.assertEqual(self.request()[0], 403)
        self.real['estado'] = 'activo'; self.real['puestos'] = ['operaciones']
        self.real = snapshot
        self.assertEqual(self.request()[0], 403)

    def test_mutacion_durante_io_no_publica(self):
        for cambio in ('act', 'cartera', 'roles', 'modulo'):
            with self.subTest(cambio=cambio):
                self.t.cleanup()
                self.setUp()
                def mutate():
                    if cambio == 'act': self.act['cid1'] = False
                    elif cambio == 'cartera': self.e.crudo['asignaciones'] = []
                    elif cambio == 'roles': self.real['puestos'] = ['setters']
                    else: self.e.modulos['salud-crm']['account'] = None
                self.hook = mutate
                self.assertEqual(self.request()[0], 403)
                self.t.cleanup()

    def test_global_legitimo_y_empty_no_global(self):
        with self.con() as c: c.execute('UPDATE acciones SET cliente_id=NULL')
        self.assertEqual(len(self.request()[1]['acciones']), 1)
        with self.con() as c: c.execute("UPDATE acciones SET cliente_id=''")
        self.assertEqual(self.request()[1]['acciones'], [])

    def test_global_ajena_solo_todo_y_clientes_siguen_scope(self):
        with self.con() as c: c.execute("UPDATE acciones SET cliente_id=NULL, quien='account2'")
        self.assertEqual(self.request('salud-crm')[1]['acciones'], [])
        self.real['puestos'] = ['operaciones']
        self.assertEqual(len(self.request('salud-crm')[1]['acciones']), 1)
        self.assertEqual(self.request()[1]['acciones'], [])

    def test_sin_crear_tablas_de_envios_ni_alterar_accion(self):
        with self.con() as c:
            antes = tuple(c.execute('SELECT * FROM acciones').fetchone())
        self.request()
        with self.con() as c:
            self.assertEqual(tuple(c.execute('SELECT * FROM acciones').fetchone()), antes)
            self.assertEqual(c.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0], 1)


if __name__ == '__main__': unittest.main()
