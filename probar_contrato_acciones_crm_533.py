"""Caracterización read-only del validador real; sin servidor ni base real."""
import ast
import copy
import types
import sqlite3
import tempfile
import unittest
import json
import re
from pathlib import Path
import permisos as P

ROOT = Path(__file__).parent


class Contrato533(unittest.TestCase):
    def setUp(self):
        tree = ast.parse((ROOT / 'servir.py').read_text())
        fn = copy.deepcopy(next(n for n in ast.walk(tree)
                                if isinstance(n, ast.FunctionDef) and n.name == 'validar_accion'))
        self.actor = {'id': 'account_fixture', 'estado': 'activo', 'activo': True,
                      'puestos': ['account']}
        self.e = types.SimpleNamespace(modulos=P.cargar_modulos(), crudo={
            'personas': [self.actor], 'clientes': [], 'asignaciones': []})
        deposito = tempfile.TemporaryDirectory()
        self.addCleanup(deposito.cleanup)
        ns = {'P': P, 'E': self.e, 'registrar_agrupado': lambda *a, **k: None,
              'DATA': Path(deposito.name), 'json': json, 're': re}
        def ve_alguno(persona, modulos):
            niveles = [P.nivel_modulo(persona, self.e.modulos.get(m, {})) for m in modulos]
            return next((n for n in niveles if n), None)
        ns['ve_alguno'] = ve_alguno
        resolver = copy.deepcopy(next(n for n in tree.body
                                      if isinstance(n, ast.FunctionDef)
                                      and n.name == 'referencia_accion603'))
        exec(compile(ast.fix_missing_locations(ast.Module(body=[resolver, fn], type_ignores=[])),
                     'validar_accion_actual533', 'exec'), ns)
        self.validar = ns['validar_accion']
        self.body = {'modulo': 'salud-crm', 'herramienta': 'app',
                     'tipo': 'proponer_reasignacion', 'objeto': 'Subcuentas sin especialista',
                     'cliente_id': None, 'texto': 'Propuesta sintética',
                     'vista_previa': 'Propuesta sintética'}

    def call(self, actor=None, vista=None, body=None):
        return self.validar(None, actor or self.actor, vista or self.actor,
                            copy.deepcopy(body or self.body))

    def test_regresion_propuesta_global_account_denegada_536(self):
        self.assertEqual(P.nivel_modulo(self.actor, self.e.modulos['salud-crm']), 'suyo')
        self.assertIn(self.body['tipo'], P.REGLAS['acciones_permitidas']['*'])
        self.assertNotIn(self.body['tipo'], P.REGLAS['acciones_solo_puestos'])
        self.assertEqual(self.call()[1][0], 403)

    def test_viewas_denegado_antes_contexto(self):
        vista = dict(self.actor, id='otra_fixture')
        self.assertEqual(self.call(vista=vista)[1][0], 403)

    def test_modulo_sin_permiso_denegado(self):
        actor = dict(self.actor, puestos=['setters'])
        self.assertEqual(self.call(actor=actor, vista=actor)[1][0], 403)

    def test_tipo_desconocido_rechazado(self):
        self.assertEqual(self.call(body=dict(self.body, tipo='tipo_no_permitido'))[1][0], 400)


class LecturaHistorica533(unittest.TestCase):
    def test_regresion538_propias_sin_modulo_ocultan_cliente_revocado(self):
        tree = ast.parse((ROOT / 'servir.py').read_text())
        branch = copy.deepcopy(next(n for n in ast.walk(tree) if isinstance(n, ast.If)
            and ast.unparse(n.test) == "ruta == '/api/acciones'"
            and 'SELECT * FROM acciones' in ast.unparse(n)))
        fn = ast.parse('def get(self,ruta,real,persona,q,cp):\n pass').body[0]
        fn.body = [branch]
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'sintetico.sqlite'
            def con():
                c = sqlite3.connect(str(path)); c.row_factory = sqlite3.Row
                return c
            with con() as c:
                c.execute('CREATE TABLE acciones(id INTEGER PRIMARY KEY,quien TEXT,cliente_id TEXT,modulo TEXT,tipo TEXT,texto TEXT,vista_previa TEXT)')
                c.execute('INSERT INTO acciones VALUES (1,?,?,?,?,?,?)',
                          ('account_fixture', 'cliente_revocado', 'salud-crm', 'nota', 'Nota sintética privada', 'Nota sintética privada'))
            p = {'id': 'account_fixture', 'puestos': ['account'], 'estado': 'activo'}
            e = types.SimpleNamespace(nucleo_bloqueado=False, modulos=P.cargar_modulos(),
                                      crudo={'personas': [p], 'clientes': [], 'asignaciones': []})
            ns = {'P': P, 'E': e, 'ACT': types.SimpleNamespace(estado=lambda: {}, es_activo_id=lambda cid: False),
                  've_alguno': lambda persona, mods: next((P.nivel_modulo(persona, e.modulos[m]) for m in mods), None),
                  'conectar': con, 'json': __import__('json')}
            from probar_recorte_modulo_589 import cargar as cargar_recortes589
            ns.update(cargar_recortes589())
            recorte = copy.deepcopy(next(n for n in tree.body
                                        if isinstance(n, ast.FunctionDef)
                                        and n.name == 'recorte_importes_lectura588'))
            exec(compile(ast.fix_missing_locations(ast.Module(body=[recorte, fn], type_ignores=[])),
                         'GET_acciones_actual533', 'exec'), ns)
            handler = types.SimpleNamespace(responder=lambda code, dto: (code, dto))
            cp = P.contexto(p, {'personas': [p], 'clientes': [], 'asignaciones': []})
            self.assertFalse(P.ver(p, {'tipo': 'cliente_detalle', 'cliente_id': 'cliente_revocado'}, cp)['ok'])
            code, dto = ns['get'](handler, '/api/acciones', p, p, {}, cp)
            self.assertEqual(code, 200)
            self.assertEqual(dto['acciones'], [])


if __name__ == '__main__':
    unittest.main()
