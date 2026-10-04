import copy,types,unittest
from unittest.mock import patch
import meta_diaria_api_385 as M
class Meta(unittest.TestCase):
 def setUp(self):
  ps=[{'id':'r','estado':'activo','activo':True,'puestos':['trafficker']},{'id':'v','estado':'activo','activo':True,'puestos':['account']}]
  self.s=types.SimpleNamespace(E=types.SimpleNamespace(nucleo_bloqueado=False,crudo={'personas':ps,'clientes':[{'id':'ok','activo':True}]}),ACT=types.SimpleNamespace(es_activo_id=lambda cid:True),P=types.SimpleNamespace(contexto=lambda p,raw:{'id':p['id']},ver=lambda p,a,cp:{'ok':True}),ve_alguno=lambda p,m:'todo')
  self.doc={'cuenta_id':'123','moneda':'EUR','zona':'Europe/Madrid'}
  self.out={'gasto_observado':5,'cpl_calificado':None,'moneda':'EUR','leads_observados':None,'dias':[{'gasto_observado':3,'dia':'2026-10-02','leads_observados':None}]}
 def test_sin_copia(self):
  with patch.dict(M.os.environ,{},clear=True):self.assertEqual(M.listar(self.s,'r','r','ok')['estado'],'sin_dato')
 def run_c(self,load=None):
  with patch.object(M,'cargar',side_effect=load or [(self.doc,'pin'),(self.doc,'pin')]),patch.object(M,'resumir',return_value=copy.deepcopy(self.out)):
   return M.listar(self.s,'r','r','ok',path='/private/test/candidato.json')
 def test_inversion(self):self.assertEqual(self.run_c()['medicion']['gasto_observado'],5)
 def test_sin_inversion(self):
  self.s.P.ver=lambda p,a,cp:{'ok':a['tipo']!='inversion'};o=self.run_c()['medicion'];self.assertNotIn('gasto_observado',o);self.assertNotIn('moneda',o);self.assertNotIn('gasto_observado',o['dias'][0]);self.assertIsNone(o['leads_observados'])
 def test_baja_antes_no_io(self):
  self.s.E.crudo['personas'][0]['estado']='baja'
  with patch.object(M,'cargar') as load:
   with self.assertRaises(M.ErrorMeta):M.listar(self.s,'r','r','ok',path='/private/test/candidato.json')
   load.assert_not_called()
 def test_revoke_ultimo_io(self):
  n=[0]
  def read(*a):
   n[0]+=1
   if n[0]==2:self.s.E.crudo['clientes'][0]['activo']=False
   return self.doc,'pin'
  with self.assertRaises(M.ErrorMeta):self.run_c(read)
 def test_pins_cambio(self):
  n=[0];old=M.SHA
  def read(*a):
   n[0]+=1
   if n[0]==2:M.SHA='changed'
   return self.doc,'pin'
  try:
   with self.assertRaises(M.ErrorMeta):self.run_c(read)
  finally:M.SHA=old
 def test_persona_dup(self):
  self.s.E.crudo['personas'].append(copy.deepcopy(self.s.E.crudo['personas'][0]))
  with self.assertRaises(M.ErrorMeta):self.run_c()
 def test_scope_modulo(self):
  self.s.ve_alguno=lambda *a:None
  with self.assertRaises(M.ErrorMeta):self.run_c()
if __name__=='__main__':unittest.main()
