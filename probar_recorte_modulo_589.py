"""Recortes reales AST con reglas actuales. Sin importar servidor ni datos reales."""
import ast,re,types,unittest
from pathlib import Path
import permisos as P
import probar_alias_importes_576 as F
APP=Path(__file__).parent

def cargar():
    names={'ClaveValor','_es_num','_quita','serie_sin_gasto','recortar_doc','_serie_de_meta','quitar_para','sin_cuota','recortar_modulo','clientes_ajenos','cliente_de_fila'}
    constants={'CONSUMIDAS','SERIES_CON_GASTO','DINERO_CUOTA_VALOR','DINERO_INVERSION_VALOR'}
    tree=ast.parse((APP/'servir.py').read_text())
    nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and (t.id.startswith('CLAVES_') or t.id in constants) for t in n.targets)]
    ns={'P':P,'re':re};exec(compile(ast.Module(body=nodes,type_ignores=[]),'recortes reales589','exec'),ns);return ns

class Recorte589(unittest.TestCase):
 def setUp(self):
    self.f=F.Alias576();self.f.setUp();self.ns=cargar();self.ns['E']=types.SimpleNamespace(crudo=self.f.crudo)
    for c in self.f.clientes:c['nombre']='Fixture '+c['id']
 def p(self,rol):return next(p for p in self.f.personas if p['id']==rol)
 def cut(self,rol,x,mod=False,cid='propio',**kw):
    p=self.p(rol);cp=P.contexto(p,self.f.crudo)
    if mod:return self.ns['recortar_modulo'](p,cp,x,**kw)
    return self.ns['recortar_doc'](x,self.ns['quitar_para'](p,cp,cid))
 def test_baseline_before_after(self):
    x={'FEE':100,'CPC':3,'CPM':7,'BUDGET_ADS':200,'CUOTA':300}
    baseline=[re.compile(r'^(cuota|cuota_.*|importe|importe_.*)$'),re.compile(r'^(gasto.*|ultimo_gasto|coste.*|cpl.*|inversion.*|spend|presupuesto_ads)$')]
    self.assertEqual({k:v for k,v in x.items() if not any(r.match(k) for r in baseline)},x)
    self.assertEqual(self.cut('account',x),{})
 def test_five_roles_money(self):
    x={'FEE':100,'BUDGET_ADS':200,'REVENUE':300,'AGENCY_PROFIT':400,'importe_publicidad':500,'importe':600,'CPL_eur':8,'gasto_eur':9,'cpc':10,'cpm':11}
    expected={'account':set(),'trafficker':{'BUDGET_ADS','CPL_eur','gasto_eur','cpc','cpm'},'administracion':{'FEE','REVENUE','importe'},'operaciones':{'FEE','BUDGET_ADS','importe_publicidad','importe','CPL_eur','gasto_eur','cpc','cpm'},'direccion':set(x)}
    for rol,e in expected.items():
      self.assertEqual(set(self.cut(rol,x)),e,rol)
      row={'cliente_id':'propio',**x};self.assertEqual(set(self.cut(rol,[row],mod=True)[0])-{'cliente_id'},e,rol)
 def test_segments_search(self):
    for key in ('total_spend_eur','summary-CPC-usd','meta.CPM','importe_publicidad'):
      self.assertEqual(self.cut('account',{key:5}),{})
    self.assertEqual(self.cut('trafficker',{'total_spend_eur':5}),{'total_spend_eur':5})
 def test_no_currency_quota_confusion(self):
    x={'cpl_eur':1,'gasto_eur':2,'cpc':3,'cpm':4,'cuota_eur':5}
    self.assertEqual(set(self.cut('trafficker',x)),set(x)-{'cuota_eur'})
 def test_double_family(self):
    for rol in ('account','trafficker','administracion'):self.assertEqual(self.cut(rol,{'importe_publicidad':5}),{})
    self.assertEqual(self.cut('operaciones',{'importe_publicidad':5}),{'importe_publicidad':5})
 def test_generic_importe_preserves_legacy_quota_contract(self):
    for rol in ('account','trafficker'):self.assertEqual(self.cut(rol,{'IMPORTE_ajuste':5}),{})
    for rol in ('administracion','operaciones','direccion'):self.assertEqual(self.cut(rol,{'IMPORTE_ajuste':5}),{'IMPORTE_ajuste':5})
 def test_known_pii_aliases_root_and_lists(self):
    keys=('MOVIL','móvil','whatsapp','telefono_contacto','DNI','NIF','NIE','IBAN','contacto-DNI','lead.whatsapp')
    x={k:'synthetic' for k in keys}
    for rol in ('account','trafficker','administracion','operaciones','direccion'):
      self.assertEqual(self.cut(rol,x),{})
      self.assertEqual(self.cut(rol,[{'cliente_id':'propio',**x}],mod=True),[{'cliente_id':'propio'}])
 def test_presupuesto_scalar_ambiguity_not_guessed(self):
    # Presupuesto es etapa CRM (count) en fuentes_captacion; no equivale a presupuesto_ads.
    x={'presupuesto':4,'presupuesto_ads':50}
    self.assertEqual(self.cut('account',x),{'presupuesto':4})
    self.assertEqual(self.cut('trafficker',x),x)
 def test_numeros_operativos(self):
    x={'cuota_horas':8,'coste_horas':{'oct':12},'tarifa_ruta':'express','sobrecuota':'operativo','tarifa_busqueda':'consulta','estado':0,'leads':0}
    self.assertEqual(self.cut('account',x),x)
 def test_operational_horas_authorized_own(self):
    x=[{'cliente_id':'propio','cuota_horas':{'pautadas':8,'cuota':900},'coste_horas':{'oct':2}}]
    y=self.cut('account',x,mod=True);self.assertEqual(y[0]['cuota_horas'],{'pautadas':8});self.assertEqual(y[0]['coste_horas'],{'oct':2})
 def test_lead_public_mask(self):
    x={'Nombre_lead':'Fixture','LEAD_EMAIL':'synthetic@example.invalid','lead_phone':'synthetic','nombre':'Hotel Fixture','email':'authorized@example.invalid'}
    for rol in ('account','direccion'):self.assertEqual(self.cut(rol,x),{'nombre':'Hotel Fixture','email':'authorized@example.invalid'})
 def test_lead_collection_context(self):
    x={'leads':[{'nombre':'Fixture','email':'synthetic@example.invalid','id':'opaque','estado':0}]}
    self.assertEqual(self.cut('direccion',x),{'leads':[{'id':'opaque','estado':0}]})
    x={'cliente_id':'propio',**x};self.assertEqual(self.cut('direccion',x,mod=True,filas_lead=('leads',))['leads'],[{'id':'opaque','estado':0}])
 def test_employee_hotel_contacts_no_new_grant(self):
    x={'empleados':[{'nombre':'Fixture','email':'authorized@example.invalid','telefono':'synthetic'}],'hotel':{'nombre':'Hotel Fixture','email':'authorized@example.invalid'}}
    y=self.cut('direccion',x);self.assertNotIn('telefono',y['empleados'][0]);self.assertEqual(y['hotel'],x['hotel']);self.assertIn('email',y['empleados'][0])
 def test_resumen_lead_alias_empty(self):
    x={'lista':[{'cliente_id':'propio','LEAD_EMAIL':'synthetic@example.invalid'}]}
    self.assertEqual(self.cut('direccion',x,mod=True,nivel='resumen')['lista'],[])
 def test_unknown_null_numeric_zero_preserve_authorized(self):
    x={'ad_spend':None,'CPM':0,'CPC':False,'cantidad':0}
    self.assertEqual(self.cut('trafficker',x),x);self.assertEqual(self.cut('account',x),{'cantidad':0})
 def test_series_cash_removed_not_counts(self):
    x={'gasto':12,'campanas':[],'serie':[['2026-10-01',3,4]],'serie_ant':[{'d':'x','meta':[5,6],'CPM':7}]}
    y=self.cut('account',x);self.assertEqual(y['serie'],[['2026-10-01',None,4]]);self.assertEqual(y['serie_ant'],[{'d':'x','meta':[None,6]}])
 def test_uppercase_series_same_security(self):
    x={'GASTO':12,'CAMPANAS':[],'SERIE':[['2026-10-01',3,4]],'SERIE_ANT':[{'d':'x','META':[5,6],'CPM':7}]}
    y=self.cut('account',x);self.assertEqual(y['SERIE'],[['2026-10-01',None,4]]);self.assertEqual(y['SERIE_ANT'],[{'d':'x','META':[None,6]}])
 def test_no_inversion_ajena(self):
    self.assertEqual(self.cut('trafficker',{'CPC':2},cid='ajeno'),{})
 def test_scope_account_rows(self):
    y=self.cut('account',[{'cliente_id':'propio','estado':1},{'cliente_id':'ajeno','estado':2}],mod=True)
    self.assertEqual(y,[{'cliente_id':'propio','estado':1}])
 def test_real_view(self):
    with P.mirando_como(self.p('administracion'),self.f.crudo):
      self.assertEqual(self.cut('direccion',{'fee':1,'ad_spend':2,'revenue':3,'agency_profit':4}),{'fee':1,'revenue':3})
if __name__=='__main__':unittest.main()
