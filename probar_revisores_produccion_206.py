"""Fixtures sobre función REAL aislada por AST; no importa servidor ni DB."""
import ast,json,unittest
from pathlib import Path
from types import SimpleNamespace
HERE=Path(__file__).resolve().parent
source=ast.parse((HERE/'servir.py').read_text())
fn=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='puede_revisar_pieza')
reglas=json.loads((HERE/'reglas_permisos.json').read_text())
personas={'seo-author':{'puestos':['seo']},'ads-author':{'puestos':['trafficker']},'direct-author':{'puestos':['web'],'jefe':'lead'}}
namespace={'P':SimpleNamespace(REGLAS=reglas),'E':SimpleNamespace(persona=lambda pid:personas.get(pid))}
exec(compile(ast.Module(body=[fn],type_ignores=[]),'servir.py:puede_revisar_pieza','exec'),namespace)
can=namespace['puede_revisar_pieza']
class PruebaRevisores(unittest.TestCase):
 def test_autor_nunca_incluso_ops(self):
  self.assertFalse(can({'id':'seo-author','puestos':['operaciones']},{'autores':{'seo-author'},'estado':'revisión técnica','cli':'c'},{}))
 def test_account_solo_cartera_actual(self):
  p={'id':'account','puestos':['account']};piece={'autores':{'seo-author'},'estado':'revisión project manager','cli':'c'}
  self.assertTrue(can(p,piece,{'cartera_por_silla':{'account':{'c'}}}))
  self.assertFalse(can(p,piece,{'cartera_por_silla':{'account':{'otro'}}}))
 def test_tecnica_area_correcta(self):
  p={'id':'lead','puestos':['jefa_seo']};piece={'autores':{'seo-author'},'estado':'revisión técnica','cli':'c'}
  self.assertTrue(can(p,piece,{}));piece['autores']={'ads-author'};self.assertFalse(can(p,piece,{}))
 def test_tecnica_jefe_directo(self):
  self.assertTrue(can({'id':'lead','puestos':['jefa_crm']},{'autores':{'direct-author'},'estado':'revisión técnica','cli':'c'},{}))
 def test_autor_ausente_no_area(self):
  self.assertFalse(can({'id':'lead','puestos':['jefa_seo']},{'autores':{'missing'},'estado':'revisión técnica','cli':'c'},{}))
 def test_ops_estado_de_revision_permitido(self):
  self.assertTrue(can({'id':'ops','puestos':['operaciones']},{'autores':{'seo-author'},'estado':'revisión técnica','cli':'c'},{}))
 def test_ops_no_estado_externo(self):
  for estado in reglas['revision_piezas']['espera_cliente']:
   self.assertFalse(can({'id':'ops','puestos':['operaciones']},{'autores':{'seo-author'},'estado':estado,'cli':'c'},{}))
 def test_ops_estado_desconocido_no(self):
  self.assertFalse(can({'id':'ops','puestos':['operaciones']},{'autores':{'seo-author'},'estado':'inventado','cli':'c'},{}))
 def test_revision_nominal(self):
  piece={'autores':{'seo-author'},'estado':'revisión tomás','cli':'c'}
  self.assertTrue(can({'id':'tomas','puestos':[]},piece,{}));self.assertFalse(can({'id':'homonimo','puestos':[]},piece,{}))
 def test_pieza_ausente(self):
  self.assertFalse(can({'id':'ops','puestos':['operaciones']},None,{}))
if __name__=='__main__':unittest.main()
