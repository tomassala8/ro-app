import ast
import json
import concurrent.futures
import sqlite3
import tempfile
import types
import unittest
from unittest.mock import patch
from pathlib import Path
from intenciones_acciones import guardar, ConflictoIntencion

CLAVE = 'd80141d8-fc4c-48d2-a933-6719fef06993'
BODY = {'intencion_id': CLAVE, 'objeto': 'tarea123', 'tipo': 'cambiar_estado',
        'vista_previa': {'a': 'en curso', 'revision': 'r1'}}


class Pruebas(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'prueba.sqlite3'
        with self.con() as c:
            c.execute('CREATE TABLE acciones(id INTEGER PRIMARY KEY, objeto TEXT)')

    def tearDown(self):
        self.temp.cleanup()

    def con(self):
        return sqlite3.connect(str(self.path), timeout=5)

    def ejecutar(self, actor='persona1', cuerpo=None, fallar=False):
        with self.con() as c:
            c.execute('BEGIN IMMEDIATE')
            def insertar(con):
                aid = con.execute('INSERT INTO acciones(objeto) VALUES (?)',
                                  ('tarea123',)).lastrowid
                if fallar:
                    raise RuntimeError('Interrupción simulada')
                return aid
            return guardar(c, actor, cuerpo or BODY, insertar)

    def test_reintento_tras_reabrir_base(self):
        self.assertEqual(self.ejecutar(), (1, False))
        self.assertEqual(self.ejecutar(), (1, True))

    def test_concurrencia_una_sola_accion(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            rs = list(pool.map(lambda _: self.ejecutar(), range(12)))
        self.assertEqual(sum(not repetida for _, repetida in rs), 1)
        self.assertEqual({aid for aid, _ in rs}, {1})

    def test_cambio_cuerpo_conflicto_sin_insertar(self):
        self.ejecutar()
        with self.assertRaises(ConflictoIntencion):
            self.ejecutar(cuerpo={**BODY, 'objeto': 'otra_tarea'})
        with self.con() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM acciones').fetchone()[0], 1)

    def test_actor_distinto_no_reutiliza_accion(self):
        self.ejecutar()
        self.assertEqual(self.ejecutar(actor='persona2'), (2, False))

    def test_rollback_no_deja_accion_huerfana(self):
        with self.assertRaises(RuntimeError):
            self.ejecutar(fallar=True)
        with self.con() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM acciones').fetchone()[0], 0)
        self.assertEqual(self.ejecutar(), (1, False))

    def test_clave_invalida_no_inserta(self):
        for clave in [None, '', CLAVE.upper(), '123', True]:
            with self.assertRaises(ValueError):
                self.ejecutar(cuerpo={**BODY, 'intencion_id': clave})

    def test_json_invalido_no_inserta(self):
        with self.assertRaises(ValueError):
            self.ejecutar(cuerpo={**BODY, 'vista_previa': {'numero': float('nan')}})

    def test_callback_sin_accion_no_crea_recibo(self):
        with self.con() as c:
            c.execute('BEGIN IMMEDIATE')
            with self.assertRaises(ValueError):
                guardar(c, 'persona1', BODY, lambda _: 999)
            self.assertEqual(c.execute('SELECT count(*) FROM intenciones_acciones').fetchone()[0], 0)

    def test_necesita_transaccion(self):
        with self.con() as c, self.assertRaises(RuntimeError):
            guardar(c, 'persona1', BODY, lambda _: 1)


class IntegracionPost(unittest.TestCase):
    con = Pruebas.con
    tearDown = Pruebas.tearDown

    def setUp(self):
        Pruebas.setUp(self)
        with self.con() as con:
            con.execute('DROP TABLE acciones')
            con.executescript((Path(__file__).parent / 'schema_v2.sql').read_text())
        tree = ast.parse((Path(__file__).parent / 'servir.py').read_text())
        branch = next(n for n in ast.walk(tree) if isinstance(n, ast.If)
            and '/api/acciones' in ast.unparse(n.test)
            and 'INSERT INTO acciones' in ast.unparse(n))
        fn = ast.parse('def post(self,ruta,real,persona,b):\n    pass').body[0]
        fn.body = [branch]
        ns = {'conectar': self.con, 'json': json, 'registrar': lambda *a, **k: None}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])),
                     'POST_acciones_real', 'exec'), ns)
        self.post = ns['post']
        class Handler:
            def validar_accion(self, *args):
                return None, None
            def responder(self, status, body):
                return status, body
        self.handler = Handler()
        self.body = {**BODY, 'herramienta': 'clickup', 'modulo': 'mi-trabajo', 'texto': 'Mover'}

    def request(self, body=None):
        return self.post(self.handler, '/api/acciones', {'id':'persona1'},
                         {'id':'persona1'}, body or self.body)

    def test_post_recibo_y_retry_persistente(self):
        a = self.request()
        b = self.request()
        self.assertEqual(a[0], 200)
        self.assertEqual(b[1]['id'], a[1]['id'])
        self.assertTrue(b[1]['intencion_guardada']['repetida'])
        self.assertNotIn('confirmado_clickup', b[1])

    def test_post_conflicto_no_nueva_accion(self):
        self.request()
        self.assertEqual(self.request({**self.body, 'texto':'Otro movimiento'})[0], 409)
        with self.con() as con:
            self.assertEqual(con.execute('SELECT count(*) FROM acciones').fetchone()[0], 1)

    def test_transition_atomic_replay_skips_old_revision(self):
        body = {**self.body, 'vista_previa': {**BODY['vista_previa'], 'transicion_tablero': True}}
        def verifier(con, actor, payload):
            self.assertTrue(con.in_transaction)
            self.assertEqual(con.execute('SELECT count(*) FROM acciones').fetchone()[0], 0)
        with patch('mi_trabajo.validar_transicion_en_transaccion', side_effect=verifier) as check:
            self.assertEqual(self.request(body)[0], 200)
            self.assertEqual(self.request(body)[0], 200)
            self.assertEqual(check.call_count, 1)

    def test_transition_conflict_rolls_back_action_and_intent(self):
        body = {**self.body, 'vista_previa': {**BODY['vista_previa'], 'transicion_tablero': True}}
        with patch('mi_trabajo.validar_transicion_en_transaccion', return_value=(409, 'Cambió la tarea')):
            self.assertEqual(self.request(body)[0], 409)
        with self.con() as con:
            self.assertEqual(con.execute('SELECT count(*) FROM acciones').fetchone()[0], 0)
            tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'intenciones_acciones' in tables:
                self.assertEqual(con.execute('SELECT count(*) FROM intenciones_acciones').fetchone()[0], 0)

    def test_post_uuid_invalido(self):
        self.assertEqual(self.request({**self.body, 'intencion_id':'invalida'})[0], 400)

    def test_production_atomic_callback_and_same_intent_replay(self):
        body = {**self.body, 'modulo':'produccion', 'tipo':'pieza_aprobar',
                'vista_previa': {**BODY['vista_previa'], 'transicion_produccion':True}}
        llamadas = []
        def verifier(con, actor, payload):
            self.assertTrue(con.in_transaction)
            self.assertEqual(con.execute('SELECT count(*) FROM acciones').fetchone()[0], 0)
            self.assertEqual(payload['modulo'], 'produccion')
            self.assertEqual(payload['tipo'], 'pieza_aprobar')
            llamadas.append(payload['intencion_id'])
        with patch.dict('sys.modules', {'transiciones_produccion_208': types.SimpleNamespace(validar_en_transaccion=verifier)}):
            a=self.request(body);b=self.request(body)
        self.assertEqual(a[0], 200);self.assertEqual(b[0], 200)
        self.assertEqual(a[1]['id'], b[1]['id']);self.assertEqual(llamadas, [CLAVE])

    def test_production_conflict_rolls_back_before_insert(self):
        body = {**self.body, 'modulo':'produccion', 'tipo':'pieza_pedir_cambios',
                'vista_previa': {**BODY['vista_previa'], 'transicion_produccion':True}}
        def verifier(con, actor, payload):
            self.assertTrue(con.in_transaction)
            return 409, 'Cambió la pieza'
        with patch.dict('sys.modules', {'transiciones_produccion_208': types.SimpleNamespace(validar_en_transaccion=verifier)}):
            self.assertEqual(self.request(body)[0], 409)
        with self.con() as con:
            self.assertEqual(con.execute('SELECT count(*) FROM acciones').fetchone()[0], 0)
            if con.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='intenciones_acciones'").fetchone()[0]:
                self.assertEqual(con.execute('SELECT count(*) FROM intenciones_acciones').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
