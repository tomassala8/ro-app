import ast,json,re,tempfile,unittest
from pathlib import Path
from datetime import date,timedelta
A=Path(__file__).resolve().parent
D=A/'fixtures'
source=(A/'metodo_cuentas.py').read_text();tree=ast.parse(source)
def cargar():
 ns={'json':json,'re':re,'date':date,'timedelta':timedelta,'REGLA_ID':'seguimiento_quincenal_especialista'}
 names={'leer','dia','eventos_confirmados640','responsables','reglas_confirmadas','sugerencias'}
 nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
 exec(compile(ast.Module(body=nodes,type_ignores=[]),'metodo_actual_AST','exec'),ns)
 return ns
NS=cargar();baseline={'json':json};exec(compile((D/'baseline_lector_metodo_649.py').read_text(),'baseline_AST_congelado','exec'),baseline);BASE=baseline['leer'];FIX=NS['leer']
POL={'regla':{'id':NS['REGLA_ID'],'cadencia_dias':15,'responsable_role':'trafficker'},'clientes':[{'cliente_id':'c','estado_cohorte':'confirmada','cadencia_dias':15,'responsable_role':'trafficker','tipo_cohorte':'metodo_actual_recurrente'}]}
P={'p':{'id':'p','puestos':['trafficker'],'estado':'activo','activo':True}}
AS=[{'cliente_id':'c','persona_id':'p','silla':'trafficker','desde':'2026-09-01','principal':True,'confianza':'confirmada'}]
EV={'evento_id':'e1','fuente':'registro_local','cliente_id':'c','fecha':'2026-10-04','celebrada':True,'cliente_confirmado':True,'rol_responsable_confirmado':'trafficker'}
class Lector649(unittest.TestCase):
 def read(self,text,lector=FIX):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'fixture.json';p.write_text(text);return lector(p)
 def proyectar(self,doc):return NS['sugerencias'](POL,AS,P,doc.get('reuniones',[]),doc.get('cobertura',{}),date(2026,10,4),lambda cid:cid=='c')[0]
 def test_conflicto_baseline_positivo_falso_y_candidato_unknown(self):
  raw=json.dumps({'reuniones':[EV]}).replace('"celebrada": true','"celebrada": false, "celebrada": true')
  self.assertEqual(self.proyectar(self.read(raw,BASE))['estado'],'en_cadencia')
  row=self.proyectar(self.read(raw));self.assertEqual(row['estado'],'sin_dato');self.assertIsNone(row['ultima_confirmada']);self.assertIsNone(row['proxima_revision'])
 def test_positivo_intacto(self):
  raw=json.dumps({'reuniones':[EV],'cobertura':{'completa':False}})
  self.assertEqual(self.read(raw),self.read(raw,BASE));self.assertEqual(self.proyectar(self.read(raw)),self.proyectar(self.read(raw,BASE)))
 def test_dup_en_toda_profundidad(self):
  for raw in ('{"x":{"y":{"cliente_id":"c","cliente_id":"d"}}}', '{"reuniones":[{"evento_id":"e1","evento_id":"e2"}]}', '{"x":1,"x":1}'):
   with self.subTest(raw=raw):self.assertEqual(self.read(raw),{})
 def test_politica_ambigua_no_habilita_cohorte(self):
  raw=json.dumps(POL).replace('"cadencia_dias": 15','"cadencia_dias": 10,"cadencia_dias": 15',1)
  self.assertTrue(NS['reglas_confirmadas'](self.read(raw,BASE)));self.assertEqual(NS['reglas_confirmadas'](self.read(raw)),[])
 def test_cobertura_ambigua_no_afirma_ausencia(self):
  ev={**EV,'fecha':'2026-09-01'}
  raw=json.dumps({'reuniones':[ev],'cobertura':{'completa':True,'desde':'2026-09-01','hasta':'2026-10-04'}}).replace('"completa": true','"completa": false,"completa": true')
  self.assertEqual(self.proyectar(self.read(raw,BASE))['estado'],'revisar_cadencia');self.assertEqual(self.proyectar(self.read(raw))['estado'],'sin_dato')
 def test_numeros_no_finitos_y_overflow(self):
  for n in ('NaN','Infinity','-Infinity','1e999'):
   with self.subTest(n=n):self.assertEqual(self.read('{"x":'+n+'}'),{})
 def test_json_malformado_y_ausente(self):
  for raw in ('{','{"x":1,}', '{"x":'):
   self.assertEqual(self.read(raw),{})
  with tempfile.TemporaryDirectory() as td:self.assertEqual(FIX(Path(td)/'ausente.json'),{})
 def test_ceros_vacio_y_decimales_legitimos(self):
  for v in ({},[],{'n':0,'v':False,'x':None,'decimal':1.25}):self.assertEqual(self.read(json.dumps(v)),v)
if __name__=='__main__':unittest.main()
