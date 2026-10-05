import unittest
import probar_alias_importes_576 as F
from recorte_alias_propuesta_583 import familias_583,recortar_propuesta_583 as cortar

class Alias583(unittest.TestCase):
    def setUp(self):self.f=F.Alias576();self.f.setUp()
    def grants(self,rol,cid='propio'):
        v=self.f.permiso(rol,cid)
        return {k:v(k) for k in ('cuota','inversion','cobros','dinero_empresa')}
    def test_matrix_four_roles(self):
        x={'FEE':100,'BUDGET_ADS':200,'REVENUE':300,'AGENCY_PROFIT':400,'importe_publicidad':500,'cuota_horas':8}
        expected={'account':{'cuota_horas':8},'administracion':{'FEE':100,'REVENUE':300,'cuota_horas':8},'operaciones':{'FEE':100,'BUDGET_ADS':200,'importe_publicidad':500,'cuota_horas':8},'trafficker':{'BUDGET_ADS':200,'cuota_horas':8}}
        for rol,y in expected.items():self.assertEqual(cortar(x,self.grants(rol),contexto='cliente'),y)
    def test_actual_comparison_not_closure(self):
        p=next(p for p in self.f.personas if p['id']=='account');cp=F.P.contexto(p,self.f.crudo)
        x={'FEE':100,'BUDGET_ADS':200,'lead_email':'synthetic@example.invalid'}
        actual=self.f.ns['recortar_doc'](x,self.f.ns['quitar_para'](p,cp,'propio'))
        self.assertEqual(actual,x) # actual regex bypass; no producto corregido.
        self.assertEqual(cortar(x,self.grants('account'),contexto='cliente'),{})
    def test_own_versus_other_investment(self):
        self.assertEqual(cortar({'ad_spend':10},self.grants('trafficker'),contexto='cliente'),{'ad_spend':10})
        self.assertEqual(cortar({'ad_spend':10},self.grants('trafficker','ajeno'),contexto='cliente'),{})
    def test_multiple_families_case_segments(self):
        self.assertEqual(familias_583('CUOTA-INVERSION'),frozenset({'cuota','inversion'}))
        self.assertEqual(cortar({'CUOTA-INVERSION':10},self.grants('administracion'),contexto='cliente'),{})
        self.assertEqual(cortar({'CUOTA-INVERSION':10},self.grants('operaciones'),contexto='cliente'),{'CUOTA-INVERSION':10})
    def test_ambiguous_importe_all_families(self):
        self.assertEqual(cortar({'importe':10,'importe_ajuste':20},self.grants('operaciones'),contexto='cliente'),{})
        self.assertEqual(cortar({'importe':10},self.grants('direccion'),contexto='cliente'),{'importe':10})
    def test_derivatives_no_finance_ops(self):
        self.assertEqual(cortar({'tarifa_hora':20,'margen':10,'rentabilidad':30},self.grants('operaciones'),contexto='cliente'),{})
    def test_operational_not_substring(self):
        x={'cuota_horas':8,'horas_pautadas':40,'tarifa_ruta':'rápida','tarifa_busqueda':'consulta','sobrecuota':'texto','estado':2}
        self.assertEqual(cortar(x,self.grants('account'),contexto='operativo'),x)
    def test_employee_and_hotel_contacts(self):
        x={'nombre':'Fixture','email':'synthetic@example.invalid','telefono':'synthetic'}
        for ctx in ('empleado','hotel','cliente'):self.assertEqual(cortar(x,self.grants('account'),contexto=ctx),x)
    def test_lead_context_private_alias(self):
        x={'nombre':'Fixture','email':'synthetic@example.invalid','id':'opaque','lead_phone':'synthetic'}
        self.assertEqual(cortar(x,self.grants('direccion'),contexto='lead'),{'id':'opaque'})
        self.assertEqual(cortar({'leads':[x]},self.grants('direccion'),contexto='empleado'),{'leads':[{'id':'opaque'}]})
    def test_unknown_context_no_person_guess(self):
        self.assertEqual(cortar({'nombre':'Fixture','email':'synthetic@example.invalid','estado':1},self.grants('direccion')),{'estado':1})
    def test_null_bool_values_denied_by_field_not_amount_guess(self):
        self.assertEqual(cortar({'fee':None,'ad_spend':False,'estado':0},self.grants('account'),contexto='cliente'),{'estado':0})
    def test_real_view_actual_matrix(self):
        real=next(p for p in self.f.personas if p['id']=='administracion');view=next(p for p in self.f.personas if p['id']=='direccion')
        with F.P.mirando_como(real,self.f.crudo):
            cp=F.P.contexto(view,self.f.crudo);g={k:F.P.ver(view,{'tipo':k,'cliente_id':'propio'},cp)['ok'] for k in ('cuota','inversion','cobros','dinero_empresa')}
            self.assertEqual(cortar({'fee':1,'ad_spend':2,'revenue':3,'agency_profit':4},g,contexto='cliente'),{'fee':1,'revenue':3})
if __name__=='__main__':unittest.main()
