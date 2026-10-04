"""Política de cohorte exacta: fixtures locales; sin proveedores ni datos escritos."""
import copy
import unittest
from datetime import date
import metodo_cuentas as M

class Cohorte305(unittest.TestCase):
    def setUp(self):
        self.r={'cliente_id':'fixture','estado_cohorte':'confirmada','cadencia_dias':15,'responsable_role':'trafficker','tipo_cohorte':'metodo_actual_recurrente'}
        self.doc={'regla':{'id':M.REGLA_ID,'cadencia_dias':15,'responsable_role':'trafficker'},'clientes':[self.r]}
    def calcular(self,d):
        return M.sugerencias(d,[],{},[],{},date(2026,10,3),lambda cid:cid=='fixture')
    def test_compatible_no_inventa_responsable_fecha_o_breach(self):
        r=self.calcular(self.doc)[0]
        self.assertEqual(r['estado'],'confirmar_responsable');self.assertIsNone(r['responsable_id']);self.assertIsNone(r['ultima_confirmada']);self.assertIsNone(r['incumplimiento'])
    def test_cadencia_rol_tipo_estado_incompatible(self):
        for patch in [{'cadencia_dias':30},{'cadencia_dias':15.0},{'cadencia_dias':'15'},{'cadencia_dias':True},{'responsable_role':'account'},{'tipo_cohorte':'setup_unico'},{'estado_cohorte':'pendiente'}]:
            with self.subTest(patch=patch):self.assertEqual(self.calcular({**self.doc,'clientes':[{**self.r,**patch,'precio':1470}]}),[])
    def test_campos_ausentes_no_reconstruidos_por_importe(self):
        for key in ['cadencia_dias','responsable_role','tipo_cohorte','estado_cohorte']:
            r={**self.r,'precio':1470};r.pop(key);self.assertEqual(self.calcular({**self.doc,'clientes':[r]}),[])
    def test_conflicto_duplicados_incluso_pendiente(self):
        for extra in [self.r,{**self.r,'responsable_role':'account'},{**self.r,'estado_cohorte':'pendiente'}]:
            self.assertEqual(self.calcular({**self.doc,'clientes':[self.r,extra]}),[])
    def test_regla_global_incompatible_ausente(self):
        for regla in [None,[],{}, {'id':'otra','cadencia_dias':15,'responsable_role':'trafficker'},{**self.doc['regla'],'cadencia_dias':30},{**self.doc['regla'],'responsable_role':'account'}]:
            self.assertEqual(self.calcular({**self.doc,'regla':regla}),[])
    def test_config_malformada_no_tumba_feed(self):
        for doc in [None,[],False,{'clientes':{}},{**self.doc,'clientes':'malformado'},{**self.doc,'clientes':[None,[],{'cliente_id':123},self.r]}]:
            result=self.calcular(doc);self.assertEqual(len(result),1 if isinstance(doc,dict) and isinstance(doc.get('clientes'),list) else 0)
    def test_scope_exacto_no_nombre(self):
        for cid in ['fixture ',123,None,'otro']:
            self.assertEqual(self.calcular({**self.doc,'clientes':[{**self.r,'cliente_id':cid,'nombre':'fixture'}]}),[])
    def test_actual14_compatibles_sin_modificar_fuente(self):
        antes=M.REGLAS.read_bytes();doc=M.leer(M.REGLAS)
        self.assertEqual(len(M.reglas_confirmadas(doc)),14)
        self.assertEqual(len(M.sugerencias(doc,[],{},[],{},date(2026,10,3),lambda cid:True)),14)
        self.assertEqual(M.REGLAS.read_bytes(),antes)
    def test_puro_no_muta_config(self):
        d=copy.deepcopy(self.doc);antes=copy.deepcopy(d);self.calcular(d);self.assertEqual(d,antes)

if __name__=='__main__':unittest.main()
