import ast,json,re,unittest,hashlib
from datetime import date,timedelta
from pathlib import Path
APP=Path(__file__).parent
BASELINE=APP/'fixtures/metodo_cuentas_640_original.py'
NOMBRES=('dia','responsables','reglas_confirmadas','sugerencias','eventos_confirmados640')
def extraer(path):
    ns={'date':date,'timedelta':timedelta,'json':json,'re':re,'REGLA_ID':'seguimiento_quincenal_especialista'}
    tree=ast.parse(path.read_text());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in NOMBRES]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'AST_sin_lectores_640','exec'),ns);return ns
class EventosCadencia644(unittest.TestCase):
    def setUp(self):
        self.old=extraer(BASELINE);self.new=extraer(APP/'metodo_cuentas.py')
        self.rules={'regla':{'id':self.new['REGLA_ID'],'cadencia_dias':15,'responsable_role':'trafficker'},'clientes':[{'cliente_id':'fixture','estado_cohorte':'confirmada','tipo_cohorte':'metodo_actual_recurrente','cadencia_dias':15,'responsable_role':'trafficker'}]}
        self.ps={'actual':{'id':'actual','estado':'activo','puestos':['trafficker']}}
        self.asig=[{'cliente_id':'fixture','persona_id':'actual','silla':'trafficker','desde':'2026-01-01','principal':True,'confianza':'confirmada'}]
        self.ev={'evento_id':'evt_fixture-1','cliente_id':'fixture','fecha':'2026-10-01','celebrada':True,'cliente_confirmado':True,'rol_responsable_confirmado':'trafficker','fuente':'zoom'}
    def call(self,events,old=False):
        ns=self.old if old else self.new
        return ns['sugerencias'](self.rules,self.asig,self.ps,events,{},date(2026,10,4),lambda c:c=='fixture')[0]
    def unknown(self,events):
        x=self.call(events);self.assertIsNone(x['ultima_confirmada']);self.assertIsNone(x['proxima_revision']);self.assertEqual(x['estado'],'sin_dato')
    def test_original_hash_pinned(self):
        self.assertEqual(hashlib.sha256((BASELINE).read_bytes()).hexdigest(),'5db2207f775fb6a5120dbd232b7e4aef9d81860b65586155abf0c3b824f45184')
    def test_positivo_before_after(self):
        for old in (True,False):self.assertEqual(self.call([self.ev],old)['estado'],'en_cadencia')
    def test_conflicto_celebracion_before_bad_after_unknown(self):
        rows=[self.ev,{**self.ev,'celebrada':False}];self.assertEqual(self.call(rows,True)['estado'],'en_cadencia');self.unknown(rows)
    def test_conflicto_cliente_global_before_bad_after_unknown(self):
        rows=[self.ev,{**self.ev,'cliente_id':'otro'}];self.assertEqual(self.call(rows,True)['ultima_confirmada'],'2026-10-01');self.unknown(rows)
    def test_fuente_objeto_before_verificada_after_unknown(self):
        rows=[{**self.ev,'fuente':{'tipo':'pendiente'}}];self.assertEqual(self.call(rows,True)['fuentes_operativas'][-1]['fuente'],'evidencia interna verificada');self.unknown(rows)
    def test_controles_false_futuro_sinrol(self):
        for change in ({'celebrada':False},{'fecha':'2026-10-05'},{'rol_responsable_confirmado':None}):self.unknown([{**self.ev,**change}])
    def test_replay_identico_una_observacion(self):
        events=[self.ev,dict(self.ev)];self.assertEqual(len(self.new['eventos_confirmados640'](events)),1);self.assertEqual(self.call(events)['ultima_confirmada'],'2026-10-01')
    def test_fuentes_admitidas_y_unknown(self):
        for src in ('zoom','fathom','ghl','registro_local'):self.assertEqual(self.call([{**self.ev,'fuente':src}])['ultima_confirmada'],'2026-10-01')
        for src in ('app_pendiente','manual_desconocida','',None,True,[] ):self.unknown([{**self.ev,'fuente':src}])
    def test_id_obligatorio_opaco(self):
        for eid in (None,'','mail@example.test','../path','a'*161,True,123):self.unknown([{**self.ev,'evento_id':eid}])
        row=dict(self.ev);del row['evento_id'];self.unknown([row]);self.assertEqual(self.call([row],True)['estado'],'en_cadencia')
    def test_variante_malformada_invalida_global(self):
        for change in ({'fecha':'invalida'},{'fuente':[]},{'cliente_id':None}):self.unknown([self.ev,{**self.ev,**change}])
    def test_nan_no_se_promueve(self):self.unknown([{**self.ev,'valor':float('nan')}])
    def test_historico_no_requiere_owner_actual(self):
        self.assertEqual(self.call([{**self.ev,'responsable_historico_id':'anterior'}])['ultima_confirmada'],'2026-10-01')
    def test_conflicto_no_afecta_otro_evento_legitimo(self):
        rows=[self.ev,{**self.ev,'celebrada':False},{**self.ev,'evento_id':'segundo','fecha':'2026-09-29'}]
        self.assertEqual(self.call(rows)['ultima_confirmada'],'2026-09-29')
if __name__=='__main__':unittest.main()
