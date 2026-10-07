"""Reproducción aislada de lectura operativa privada: AST real y permisos reales."""
import ast
import json
import re
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock
import permisos as P

A = Path(__file__).parent

def funciones(data, crudo, activos=('activo',)):
    arbol = ast.parse((A / 'servir.py').read_text())
    nodos = [n for n in arbol.body if isinstance(n, ast.FunctionDef) and n.name in ('config_almacen', 'cliente_del_dato')]
    api = next(n for c in arbol.body if isinstance(c, ast.ClassDef) for n in c.body if isinstance(n, ast.FunctionDef) and n.name == 'api_post')
    ns = dict(P=P, E=types.SimpleNamespace(crudo=crudo), DATA=data, json=json, re=re,
              ACT=types.SimpleNamespace(es_activo_id=lambda cid: cid in activos),
              ve_alguno=lambda persona, mods: bool(mods), registrar=Mock(return_value=1), registrar_agrupado=Mock())
    exec(compile(ast.Module(body=nodos + [api], type_ignores=[]), str(A / 'servir.py'), 'exec'), ns)
    return ns

class LecturaACT(unittest.TestCase):
    def test_reproduce_cliente_inactivo_whatsapp_para_direccion(self):
        tomas = {'id':'tomas', 'puestos':['direccion'], 'estado':'activo'}
        crudo = {'personas':[tomas], 'clientes':[{'id':'activo'}], 'asignaciones':[]}
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            fichero = data / 'whatsapp/_privado/textos.json'
            fichero.parent.mkdir(parents=True)
            fichero.write_text(json.dumps({'mensajes':{'inactivo':{'ultimo':'MARCADOR_SINTETICO'}}}))
            ns = funciones(data, crudo)
            conf = ns['config_almacen']('whatsapp/_privado/textos')
            self.assertIsNone(ns['cliente_del_dato'](conf, 'inactivo', 'whatsapp/_privado/textos'))
            handler = types.SimpleNamespace(responder=lambda code, dto: (code, dto))
            code, dto = ns['api_post'](handler, '/api/ver_dato', tomas, tomas,
                                      {'almacen':'whatsapp/_privado/textos', 'ref':'inactivo', 'campo':'ultimo'})
            self.assertEqual(code, 403)
            self.assertNotIn('valor', dto)

    def test_activo_ajeno_duplicado_y_vista(self):
        tomas = {'id':'tomas', 'puestos':['direccion'], 'estado':'activo'}
        cuenta = {'id':'cuenta', 'puestos':['account'], 'estado':'activo'}
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            fichero = data / 'whatsapp/_privado/textos.json'
            fichero.parent.mkdir(parents=True)
            fichero.write_text(json.dumps({'mensajes':{'activo':{'ultimo':'MARCADOR_SINTETICO'}}}))
            handler = types.SimpleNamespace(responder=lambda code, dto: (code, dto))
            for clientes, reales, vistas, esperado in [
                ([{'id':'activo'}], tomas, tomas, 200),
                ([{'id':'activo'}, {'id':'activo'}], tomas, tomas, 403),
                ([{'id':'activo'}], cuenta, cuenta, 403),
                ([{'id':'activo'}], tomas, cuenta, 403),
                ([{'id':'activo'}], cuenta, tomas, 403)]:
                crudo = {'personas':[tomas,cuenta], 'clientes':clientes, 'asignaciones':[]}
                ns = funciones(data, crudo)
                code, dto = ns['api_post'](handler, '/api/ver_dato', reales, vistas,
                                          {'almacen':'whatsapp/_privado/textos', 'ref':'activo', 'campo':'ultimo'})
                self.assertEqual(code, esperado)
                if esperado == 403: self.assertNotIn('valor', dto)

    def test_cliente_presente_pero_act_inactivo_y_sin_archivo(self):
        tomas = {'id':'tomas', 'puestos':['direccion'], 'estado':'activo'}
        with tempfile.TemporaryDirectory() as tmp:
            ns = funciones(Path(tmp), {'personas':[tomas], 'clientes':[{'id':'activo'}], 'asignaciones':[]}, activos=())
            handler = types.SimpleNamespace(responder=lambda code, dto: (code, dto))
            code, dto = ns['api_post'](handler, '/api/ver_dato', tomas, tomas,
                                      {'almacen':'whatsapp/_privado/textos', 'ref':'activo', 'campo':'ultimo'})
            self.assertEqual(code, 403)  # Antes de intentar abrir el almacén inexistente.

    def test_almacen_sin_cliente_no_gana_restriccion_act(self):
        tomas = {'id':'tomas', 'puestos':['direccion'], 'estado':'activo'}
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            f = data / 'sueldos/_privado/sueldos.json'; f.parent.mkdir(parents=True)
            f.write_text(json.dumps({'personas':{'otro':{'sueldo':17}}}))
            ns = funciones(data, {'personas':[tomas], 'clientes':[], 'asignaciones':[]}, activos=())
            handler = types.SimpleNamespace(responder=lambda code, dto: (code, dto))
            code, dto = ns['api_post'](handler, '/api/ver_dato', tomas, tomas,
                                      {'almacen':'sueldos/_privado/sueldos', 'ref':'otro', 'campo':'sueldo'})
            self.assertEqual(code, 200)
            self.assertEqual(dto.get('valor'), 17)

if __name__ == '__main__':
    unittest.main()
