"""Funciones reales; sólo fixtures sintéticas. No servidor, DB ni proveedores."""
import unittest
import re
import permisos as P
import probar_alias_importes_576 as F

class Importes580(unittest.TestCase):
    def tipos(self,t):return [P.tipo_importe(t,m.start(),m.end()) for m in P.RE_IMPORTE.finditer(t)]
    def cortar(self,t,rol):
        f=F.Alias576();f.setUp();v=f.permiso(rol)
        return P.sin_importes(t,P.importes_a_quitar(*(v(k) for k in ('cuota','inversion','cobros','dinero_empresa'))))
    def test_before_after_frozen_baseline(self):
        def baseline(t,i,f):
            antes,despues=t[max(0,i-40):i],t[f:f+25]
            if re.search('techo',antes[-25:],re.I):return 'regla'
            if re.search(r'(/\s*mes|al mes|mensual|cuota|factur|recurrente|cobr|impag|mantenimiento)',antes+' '+despues,re.I):return 'cuota'
            return 'inversion'
        t='Cuota 500 €; inversión Meta 200 €'
        self.assertEqual([baseline(t,m.start(),m.end()) for m in P.RE_IMPORTE.finditer(t)],['cuota','cuota'])
        self.assertEqual(self.tipos(t),['cuota','inversion'])
    def test_nearest_admin(self):
        t='Cuota 500 €; inversión Meta 200 €'
        self.assertEqual(self.tipos(t),['cuota','inversion'])
        self.assertIn('500',self.cortar(t,'administracion'));self.assertNotIn('200',self.cortar(t,'administracion'))
    def test_nearest_traf(self):
        t='Cuota 500 € y gasto en Meta 300 €'
        self.assertEqual(self.tipos(t),['cuota','inversion'])
        self.assertIn('300',self.cortar(t,'trafficker'));self.assertNotIn('500',self.cortar(t,'trafficker'))
    def test_agency_ops(self):
        t='Beneficio empresa 800 €. Gasto Meta 300 €.'
        self.assertEqual(self.tipos(t),['dinero_empresa','inversion'])
        self.assertNotIn('800',self.cortar(t,'operaciones'));self.assertIn('300',self.cortar(t,'operaciones'))
    def test_direccion_cobros_agencia(self):
        t='Beneficio empresa 800 €. Cobros 500 €.'
        self.assertEqual(self.cortar(t,'direccion'),t)
        self.assertNotIn('800',self.cortar(t,'administracion'));self.assertIn('500',self.cortar(t,'administracion'))
    def test_finanzas_authorized(self):
        f=F.Alias576();f.setUp();persona={'id':'financefixture','puestos':['finanzas_direccion'],'estado':'activo'}
        f.personas.append(persona);cp=P.contexto(persona,f.crudo)
        grants=[P.ver(persona,{'tipo':k,'cliente_id':'propio'},cp)['ok'] for k in ('cuota','inversion','cobros','dinero_empresa')]
        t='Beneficio empresa 800 €. Cobros 500 €.'
        self.assertEqual(P.sin_importes(t,P.importes_a_quitar(*grants)),t)
    def test_recortar_actual_ops_direction(self):
        f=F.Alias576();f.setUp();f.crudo.update(logos={},alarmas=[],meta={})
        f.clientes[0]['descripcion']='Beneficio empresa 800 €. Gasto Meta 300 €.'
        for role in ('operaciones','direccion'):
            p=next(p for p in f.personas if p['id']==role)
            c=next(c for c in P.recortar(p,f.crudo)['clientes'] if c['id']=='propio')
            self.assertIn('300',c['descripcion'])
            self.assertEqual('800' in c['descripcion'],role=='direccion')
    def test_default_money_sanitizer_still_all(self):
        self.assertNotIn("800",P.sin_importes("Beneficio empresa 800 €"))
        self.assertNotIn("500",P.sin_importes("Cobros 500 €"))
    def test_legacy_two_grants_not_inferred_roles(self):
        self.assertEqual(P.importes_a_quitar(True,True),())
        self.assertEqual(P.importes_a_quitar(True,False),('inversion',))
        self.assertEqual(P.sin_importes('Beneficio empresa 800 €',P.importes_a_quitar(True,True)),'Beneficio empresa 800 €')
    def test_unknown_no_default_inversion(self):
        t='Importe 800 €';self.assertEqual(self.tipos(t),['ambiguo'])
        self.assertNotIn('800',P.sin_importes(t,('cuota',)))
        self.assertNotIn('800',P.sin_importes(t,('inversion',)))
    def test_tie_ambiguous(self):
        t='cuota 500 € gasto';self.assertEqual(self.tipos(t),['ambiguo'])
        self.assertNotIn('500',P.sin_importes(t,('cuota',)))
    def test_techo_coste_existing(self):
        t='Coste por lead de 98 € (7 días), 2,5 veces el techo de 35 €'
        self.assertEqual(self.tipos(t),['inversion','regla'])
        self.assertEqual(P.sin_importes(t,('cuota',)),t);self.assertNotIn('€',P.sin_importes(t))
    def test_case_clauses(self):
        self.assertEqual(self.tipos('CUOTA 500 €\nGASTO META 200 € · BENEFICIO EMPRESA 800 €'),['cuota','inversion','dinero_empresa'])
    def test_operational_numbers(self):
        obj={'horas':8,'estado':3,'texto':'8 horas; estado 3; tarifa ruta rápida; cuota_horas 40'}
        self.assertEqual(P.sin_importes(obj),obj)
    def test_queries_contract(self):
        q='delito fiscal 120.000 euros anuales'
        self.assertEqual(P.sin_importes({'consultas':[q],'busquedas':[q],'keywords':[q]}),{'consultas':[q],'busquedas':[q],'keywords':[q]})
        self.assertNotIn('€',str(P.sin_importes({'consultas':['consulta €0,00']},('inversion',))))
    def test_recursive_values(self):
        x={'texto':['Cuota 500 €; gasto Meta 300 €',None,0,False]};y=P.sin_importes(x,('cuota',))
        self.assertIn('300',y['texto'][0]);self.assertNotIn('500',y['texto'][0]);self.assertEqual(y['texto'][1:],[None,0,False])
    def test_invalid_indices(self):
        self.assertEqual(P.tipo_importe('500 €',True,5),'ambiguo');self.assertEqual(P.tipo_importe(None,0,1),'ambiguo')
    def test_real_view(self):
        f=F.Alias576();f.setUp();real=next(p for p in f.personas if p['id']=='administracion');view=next(p for p in f.personas if p['id']=='direccion')
        with P.mirando_como(real,f.crudo):
            v=lambda k:P.ver(view,{'tipo':k,'cliente_id':'propio'},P.contexto(view,f.crudo))['ok']
            q=P.importes_a_quitar(*(v(k) for k in ('cuota','inversion','cobros','dinero_empresa')))
            self.assertNotIn('200',P.sin_importes('Gasto Meta 200 €',q));self.assertIn('500',P.sin_importes('Cuota 500 €',q))
if __name__=='__main__':unittest.main()
