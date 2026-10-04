"""Matriz actual y fuente de recortes por AST. Sólo datos sintéticos, sin servidor/DB."""
import ast
import json
import re
import unittest
from pathlib import Path
import permisos as P
from analisis_recortes_576 import familias_alias_576,admite_familias_576,familia_texto_576,TODO

APP=Path(__file__).resolve().parent

def recortes_reales():
    tree=ast.parse((APP/'servir.py').read_text())
    nombres={'ClaveValor','_es_num','_quita','serie_sin_gasto','recortar_doc','_serie_de_meta','quitar_para'}
    const={'CLAVES_CUOTA','CLAVES_COBROS','CLAVES_INVERSION','CLAVES_LEAD','DINERO_CUOTA_VALOR','DINERO_INVERSION_VALOR','SERIES_CON_GASTO'}
    nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in nombres or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in const for t in n.targets)]
    ns={'re':re,'P':P};exec(compile(ast.Module(body=nodes,type_ignores=[]),'recortes reales576','exec'),ns);return ns

class Alias576(unittest.TestCase):
    def setUp(self):
        self.personas=[{'id':p,'nombre':'Fixture '+p,'estado':'activo','activo':True,'puestos':[p]} for p in ('account','trafficker','administracion','operaciones','direccion')]
        self.clientes=[{'id':'propio','servicios':{'publicidad':'sí'}},{'id':'ajeno','servicios':{'publicidad':'sí'}}]
        self.crudo={'personas':self.personas,'clientes':self.clientes,'asignaciones':[{'cliente_id':'propio','persona_id':'account','silla':'account'},{'cliente_id':'propio','persona_id':'trafficker','silla':'trafficker'}]}
        self.ns=recortes_reales()
    def permiso(self,rol,cid='propio'):
        p=next(p for p in self.personas if p['id']==rol);cp=P.contexto(p,self.crudo)
        return lambda tipo:P.ver(p,{'tipo':tipo,'cliente_id':cid},cp)['ok']
    def test_matriz_actual_no_inventa_cuota_account(self):
        acc=self.permiso('account');self.assertFalse(acc('cuota'));self.assertTrue(acc('horas_pautadas'));self.assertFalse(acc('inversion'))
        traf=self.permiso('trafficker');self.assertTrue(traf('inversion'));self.assertFalse(self.permiso('trafficker','ajeno')('inversion'))
        adm=self.permiso('administracion');self.assertTrue(adm('cuota'));self.assertFalse(adm('inversion'));self.assertTrue(adm('cobros'))
        ops=self.permiso('operaciones');self.assertTrue(ops('inversion'));self.assertFalse(ops('dinero_empresa'));self.assertFalse(ops('caja'))
    def test_repro_alias_actual_no_recortados(self):
        p=next(p for p in self.personas if p['id']=='account');cp=P.contexto(p,self.crudo)
        datos={'fee':123,'budget_ads':234,'revenue':345,'lead_email':'fixture@example.invalid','lead_phone':'fixture-phone'}
        out=self.ns['recortar_doc'](datos,self.ns['quitar_para'](p,cp,'propio'))
        self.assertEqual(out,datos) # evidencia del gap, NO cierre.
    def test_case_actual_y_propuesta_no_depende_del_case(self):
        p=next(p for p in self.personas if p['id']=='account');cp=P.contexto(p,self.crudo)
        datos={'CUOTA':100,'SPEND':200,'EMAIL_LEAD':'fixture@example.invalid'}
        self.assertEqual(self.ns['recortar_doc'](datos,self.ns['quitar_para'](p,cp,'propio')),datos)
        self.assertEqual(familias_alias_576('CUOTA',100),frozenset({'cuota'}))
        self.assertEqual(familias_alias_576('SPEND',200),frozenset({'inversion'}))
        self.assertEqual(familias_alias_576('EMAIL_LEAD','fixture',contexto='lead'),frozenset({'lead_privado'}))
    def test_inversion_300_no_tapar_como_cuota(self):
        texto='Cuota 500 € y gasto en Meta 300 €';matches=list(P.RE_IMPORTE.finditer(texto))
        familias=[familia_texto_576(texto,m.start(),m.end()) for m in matches]
        self.assertEqual(familias,[frozenset({'cuota'}),frozenset({'inversion'})])
        self.assertFalse(admite_familias_576(familias[0],self.permiso('trafficker')))
        self.assertTrue(admite_familias_576(familias[1],self.permiso('trafficker')))
    def test_regex_tarifa_cuota_no_es_contrato_economico(self):
        rx=re.compile(r'cuota|tarifa',re.I)
        for key,value in [('cuota_horas',8),('tarifa_ruta','express'),('sobrecuota','texto operativo'),('tarifa_busqueda','consulta tarifa transporte')]:
            self.assertTrue(rx.search(key));self.assertFalse(familias_alias_576(key,value))

    def test_alias_propuesta_matriz_intacta(self):
        for key,rol,esperado in [('fee','administracion',True),('fee','account',False),('budget_ads','trafficker',True),('budget_ads','administracion',False),('agency_profit','operaciones',False),('agency_profit','direccion',True),('revenue','operaciones',False),('importe_publicidad','trafficker',False),('importe_publicidad','administracion',False),('importe_publicidad','operaciones',True)]:
            self.assertEqual(admite_familias_576(familias_alias_576(key,100),self.permiso(rol)),esperado,(key,rol))
    def test_nearest_cuota_inversion_repro_y_propuesta(self):
        texto='Cuota 500 €; inversión Meta 200 €';m=list(P.RE_IMPORTE.finditer(texto))
        self.assertEqual([P.tipo_importe(texto,x.start(),x.end()) for x in m],['cuota','cuota'])
        self.assertIn('200',P.sin_importes(texto,P.importes_a_quitar(True,False)))
        self.assertEqual([familia_texto_576(texto,x.start(),x.end()) for x in m],[frozenset({'cuota'}),frozenset({'inversion'})])
    def test_finance_empresa_no_default_inversion(self):
        texto='Beneficio empresa 800 €';m=next(P.RE_IMPORTE.finditer(texto))
        self.assertEqual(P.tipo_importe(texto,m.start(),m.end()),'inversion')
        self.assertIn('800',P.sin_importes(texto,P.importes_a_quitar(True,True)))
        proposed=familia_texto_576(texto,m.start(),m.end());self.assertEqual(proposed,frozenset({'dinero_empresa'}));self.assertFalse(admite_familias_576(proposed,self.permiso('operaciones')))
    def test_desconocido_tarifa_no_siempre_cuota(self):
        for key,value in [('cuota','cuota de mercado'),('tarifa','tarifa de transporte'),('tarifa',128),('presupuesto',4),('cuota_horas',8),('ad_spend',True),('fee',float('nan'))]:
            self.assertFalse(familias_alias_576(key,value),(key,value))
        texto='Tarifa de urgencia 30 €';m=next(P.RE_IMPORTE.finditer(texto))
        self.assertEqual(familia_texto_576(texto,m.start(),m.end()),TODO)
    def test_leads_claros_no_grant_enmascarado(self):
        for alias in ('lead_email','lead_phone','lead_name','email','phone','name'):
            self.assertFalse(admite_familias_576(familias_alias_576(alias,'fixture',contexto='lead'),lambda _:True))
        self.assertFalse(familias_alias_576('email','fixture',contexto='calendario'))
    def test_real_vista_interseccion_sin_ampliar(self):
        real=next(p for p in self.personas if p['id']=='administracion');vista=next(p for p in self.personas if p['id']=='direccion')
        with P.mirando_como(real,self.crudo):
            cp=P.contexto(vista,self.crudo)
            self.assertFalse(P.ver(vista,{'tipo':'inversion','cliente_id':'propio'},cp)['ok'])
            self.assertTrue(P.ver(vista,{'tipo':'cuota','cliente_id':'propio'},cp)['ok'])

if __name__=='__main__':unittest.main()
