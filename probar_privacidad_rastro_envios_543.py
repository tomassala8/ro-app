"""Auditoría aislada de las ramas reales; sólo datos sintéticos."""
import ast
import copy
import json
import sqlite3
import tempfile
import types
import unittest
from pathlib import Path
import permisos as P

ROOT = Path(__file__).parent


class Rastro543(unittest.TestCase):
    def test_rastro_propio_recupera_nota_de_cliente_revocado(self):
        tree = ast.parse((ROOT / 'servir.py').read_text())
        b = copy.deepcopy(next(n for n in ast.walk(tree) if isinstance(n, ast.If)
                and ast.unparse(n.test) == "ruta == '/api/rastro'" and 'SELECT * FROM acciones' in ast.unparse(n)))
        f = ast.parse('def get(self,real,persona,cp):\n pass').body[0]
        f.body = [ast.parse("ruta='/api/rastro'").body[0], b]
        p = {'id': 'account_fixture', 'puestos': ['account'], 'estado': 'activo'}
        cp = P.contexto(p, {'personas': [p], 'clientes': [], 'asignaciones': []})
        self.assertFalse(P.ver(p, {'tipo': 'rastro_todo'}, cp)['ok'])
        self.assertFalse(P.ver(p, {'tipo': 'cliente_detalle', 'cliente_id': 'revocado'}, cp)['ok'])
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'fixture.sqlite'
            def con():
                c = sqlite3.connect(str(path)); c.row_factory = sqlite3.Row; return c
            with con() as c:
                c.execute('CREATE TABLE registro(id INTEGER,quien TEXT,como TEXT,datos TEXT)')
                c.execute('CREATE TABLE acciones(id INTEGER,quien TEXT,cliente_id TEXT,texto TEXT,vista_previa TEXT,modulo TEXT)')
                c.execute('INSERT INTO acciones VALUES (1,?,?,?,?,?)', ('account_fixture', 'revocado', 'Nota sintética', 'Nota sintética', 'salud-crm'))
            e = types.SimpleNamespace(nucleo_bloqueado=False, modulos=P.cargar_modulos(),
                                      crudo={'personas': [p], 'clientes': [], 'asignaciones': []})
            ns = {'P': P, 'E': e, 'ACT': types.SimpleNamespace(estado=lambda: {}, es_activo_id=lambda cid: False),
                  've_alguno': lambda person, mods: next((P.nivel_modulo(person, e.modulos[m]) for m in mods), None),
                  'conectar': con}
            exec(compile(ast.fix_missing_locations(ast.Module(body=[f], type_ignores=[])), 'GET_rastro543', 'exec'), ns)
            code, d = ns['get'](types.SimpleNamespace(responder=lambda c, d: (c, d)), p, p, cp)
            self.assertEqual(code, 200); self.assertFalse(d['todo'])
            self.assertEqual(d['acciones'], [])


class Envio543(unittest.TestCase):
    def setUp(self):
        self.p = {'id': 'account_fixture', 'puestos': ['account'], 'estado': 'activo'}
        self.raw = {'personas': [self.p], 'clientes': [], 'asignaciones': []}
        tree = ast.parse((ROOT / 'envios.py').read_text())
        nombres = {'reglas', 've_todos', 'puede_reintentar', '_visible', '_abre_cliente', 'a_json'}
        fs = [copy.deepcopy(n) for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in nombres]
        self.act = {}
        self.ns = {'P': P, 'S': types.SimpleNamespace(E=types.SimpleNamespace(crudo=self.raw,
                    nucleo_bloqueado=False, modulos=P.cargar_modulos()), ACT=types.SimpleNamespace(
                    estado=lambda: dict(self.act), es_activo_id=lambda cid: self.act.get(cid) is True)),
                   'json': json, 'pasos_de': lambda con, eid: [], 'ultimo_hecho': lambda ps: {},
                   '_persona': lambda pid: {'alias': 'Autor sintético'}, 'iso_z': lambda x: x,
                   '_cliente_nombre': lambda cid: 'Cliente sintético', 'CANALES': {'ghl': 'GHL'}}
        exec(compile(ast.fix_missing_locations(ast.Module(body=fs, type_ignores=[])), 'DTO_envios543', 'exec'), self.ns)
        self.e = dict(id=1, creado='2026-10-01T10:00:00Z', quien=self.p['id'], canal='ghl',
            tipo='mensaje', modo='simulado', modulo='salud-crm', cliente_id='revocado',
            asunto='Asunto sintético', texto='Texto sintético', destinatario=json.dumps({
                'tipo': 'contacto', 'ref': 'referencia_sintetica', 'nombre': 'Persona sintética', 'resuelto': True}))

    def test_texto_oculto_pero_destinatario_no_oculto(self):
        self.assertTrue(self.ns['_visible'](self.p, self.p, self.e))
        self.assertFalse(self.ns['_abre_cliente'](self.p, 'revocado'))
        d = self.ns['a_json'](None, self.e, self.p, self.p)
        self.assertTrue(d['texto_oculto']); self.assertIsNone(d['texto']); self.assertIsNone(d['asunto'])
        self.assertIsNone(d['destinatario']['nombre'])
        self.assertIsNone(d['destinatario']['ref'])

    def test_metadatos_pasos_motivo_libres_no_recortados(self):
        self.ns['pasos_de'] = lambda c, eid: [dict(estado='fallido', evento='error_envio', hora='2026-10-01T10:00:00Z',
                        quien='account_fixture', intento=1, motivo='Nota sintética del destinatario')]
        d = self.ns['a_json'](None, self.e, self.p, self.p)
        self.assertTrue(d['texto_oculto'])
        self.assertIsNone(d['pasos'][0]['motivo'])

    def test_puesto_amplio_no_exige_cliente_catalogado_ni_act(self):
        self.p['puestos'] = ['direccion']
        self.assertEqual(self.raw['clientes'], [])
        self.assertTrue(self.ns['_abre_cliente'](self.p, 'revocado'))
        d = self.ns['a_json'](None, self.e, self.p, self.p)
        self.assertTrue(d['texto_oculto'])
        self.assertIsNone(d['texto'])


if __name__ == '__main__': unittest.main()
