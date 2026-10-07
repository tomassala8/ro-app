"""Ejecuta sólo función pura y expresión append real por AST; jamás importa main."""
import ast
from collections import defaultdict
import datetime as dt
import json
from pathlib import Path
import sys
import unittest


def producir_fixture(fila,sello):
    arbol=ast.parse(Path(__file__).with_name('generar_produccion.py').read_text())
    helper=next(n for n in arbol.body if isinstance(n,ast.FunctionDef) and n.name=='medicion_revisiones_account')
    expr=next(n for n in ast.walk(arbol) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='append' and n.value.args and isinstance(n.value.args[0],ast.Dict) and any(isinstance(k,ast.Constant) and k.value=='revisiones_account' for k in n.value.args[0].keys))
    ns=dict(dt=dt,HOY=dt.date(2026,10,3),proyectos=[],f=fila,cid='a',nom='Fixture',nombres={},account_de={},bl=[],hcli=defaultdict(float),hcli_ant=defaultdict(float),H={'entradas':[]},horas_disponibles=False,horas_descartadas=0,flujo={'_meta':{'generado':sello}})
    exec(compile(ast.Module(body=[helper,expr],type_ignores=[]),'segmento_real_produccion','exec'),ns)
    return ns['proyectos'][0]

class Medicion(unittest.TestCase):
    def test_segmento_malformado_no_rompe_sort(self):
        for rev in ([], 'invalido', {'n':'2','mas48':1}, {'n':True,'mas48':0}):
            r=producir_fixture({'rev_pm':rev},'2026-10-03')
            self.assertEqual(r['revisiones_account']['estado'],'sin_dato')
            self.assertEqual(r['rev_account']+r['rev_account_48'],0)

    def test_segmento_real_desconocido_vs_cero(self):
        a=producir_fixture({},None)
        self.assertEqual(a['revisiones_account']['estado'],'sin_dato')
        self.assertIsNone(a['horas_mes'])
        b=producir_fixture({'rev_pm':{'n':0,'mas48':0}},'2026-10-03')
        self.assertEqual(b['revisiones_account']['estado'],'medido')
        self.assertEqual(b['rev_account'],0)

if __name__=='__main__':
    if '--fixture' in sys.argv:
        print(json.dumps([producir_fixture({},None),producir_fixture({},'2026-10-03'),producir_fixture({'rev_pm':{'n':0,'mas48':0}},'2026-10-03')]))
    else:unittest.main()
