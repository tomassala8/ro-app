import ast
import copy
import json
import re
import unittest
from pathlib import Path
import permisos as P
import probar_rastro_actual_544 as R


class FinanzasRastro544(unittest.TestCase):
    def setUp(self):
        self.f = R.RastroActual544(); self.f.setUp()
        tree = ast.parse((Path(__file__).parent / 'servir.py').read_text())
        names = {'ClaveValor', '_es_num', '_quita', 'serie_sin_gasto', 'recortar_doc', '_serie_de_meta', 'quitar_para'}
        constants = {'CLAVES_CUOTA', 'CLAVES_COBROS', 'CLAVES_INVERSION', 'CLAVES_LEAD',
                     'DINERO_CUOTA_VALOR', 'DINERO_INVERSION_VALOR', 'SERIES_CON_GASTO', 'CLAVES_DINERO_CAPTACION'}
        nodes = [copy.deepcopy(n) for n in tree.body if
                 isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names
                 or isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in constants for t in n.targets)]
        for ns in (self.f.get.__globals__, self.f.f.get.__globals__):
            ns['re'] = re
            exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), 'Finanzas_reales544', 'exec'), ns)
        with self.f.f.con() as c:
            c.execute('UPDATE acciones SET tipo=?,vista_previa=?', ('objetivo_alta', json.dumps({
                'presupuesto': 100, 'cpl_objetivo': 20, 'nota': 'Referencia sintética', 'cantidad': 7})))

    def tearDown(self): self.f.tearDown()

    def test_account_recorte_equivalente_dos_rutas(self):
        p = self.f.f.real; cp = P.contexto(p, self.f.f.e.crudo)
        self.assertFalse(P.ver(p, {'tipo': 'inversion', 'cliente_id': 'cid1'}, cp)['ok'])
        vps = []
        for code, d in (self.f.leer(), self.f.f.request('salud-crm')):
            self.assertEqual(code, 200)
            vps.append(json.loads(d['acciones'][0]['vista_previa']))
        self.assertEqual(vps[0], vps[1]); self.assertNotIn('presupuesto', vps[0]); self.assertNotIn('cpl_objetivo', vps[0])
        self.assertEqual(vps[0]['cantidad'], 7); self.assertEqual(vps[0]['nota'], 'Referencia sintética')

    def test_direccion_conserva_y_vercomo_no_eleva(self):
        self.f.f.real['puestos'] = ['direccion']
        self.assertIn('presupuesto', json.loads(self.f.leer()[1]['acciones'][0]['vista_previa']))
        otra = self.f.f.otra
        self.f.f.e.crudo['asignaciones'].append({'cliente_id': 'cid1', 'persona_id': otra['id'], 'silla': 'account'})
        with self.f.f.con() as c: c.execute("UPDATE acciones SET quien='account2'")
        code, d = self.f.leer(otra)
        self.assertEqual(code, 200); self.assertEqual(d['acciones'], [])
        code, d = self.f.f.request('salud-crm', otra)
        self.assertEqual(code, 200)
        self.assertNotIn('presupuesto', json.loads(d['acciones'][0]['vista_previa']))


if __name__ == '__main__': unittest.main()
