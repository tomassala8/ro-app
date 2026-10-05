"""Rutas GET actuales, permisos reales y base temporal; ningún dato operativo."""
import json, unittest
import permisos as P
import probar_importes_acciones_decisiones_588 as F

class Recorte632(unittest.TestCase):
 def setUp(self):
  self.f=F.Importes588();self.f.setUp()
  self.valor={'agency_profit':900,'fee':1470,'invoice_total':600,'CPC':3.2,'horas':7,'cantidad':0,'cuota_horas':8,'nested':{'AGENCY_MARGIN':12,'horas':2}}
  with self.f.con() as c:
   c.execute('UPDATE acciones SET texto=?,vista_previa=?',('Revisar tarea',json.dumps(self.valor)))
   c.execute('UPDATE decisiones SET titulo=?,problema=?,recomendacion=?,datos=?,respuesta=?',('Revisar','Revisar','Revisar',json.dumps(self.valor),json.dumps(self.valor)))
 def tearDown(self): self.f.tearDown()
 def filas(self):
  out=[]
  for ruta in ('acciones','decisiones'):
   code,doc=self.f.request(ruta);self.assertEqual(code,200)
   fila=doc[ruta][0]
   out.append(json.loads(fila['vista_previa']) if ruta=='acciones' else fila)
  return out
 def esperado(self,keys):
  for fila in self.filas():
   self.assertEqual(set(fila)&set(self.valor),set(keys)|{'horas','cantidad','cuota_horas','nested'})
   self.assertEqual(fila['horas'],7);self.assertEqual(fila['cantidad'],0);self.assertEqual(fila['cuota_horas'],8)
   self.assertEqual(fila['nested'],{'horas':2,**({'AGENCY_MARGIN':12} if 'agency_profit' in keys else {})})
   if 'respuesta' in fila:
    self.assertEqual(set(fila['respuesta'])&set(self.valor),set(keys)|{'horas','cantidad','cuota_horas','nested'})
 def test_account_deny_four_current_grants(self):
  cp=P.contexto(self.f.real,self.f.e.crudo)
  with P.mirando_como(self.f.real,self.f.e.crudo):
   for tipo in ('cuota','inversion','cobros','dinero_empresa'):
    self.assertIs(P.ver(self.f.real,{'tipo':tipo,'cliente_id':'c'},cp)['ok'],False)
  self.esperado(set())
 def test_administracion_preserves_fee_and_invoice(self):
  self.f.real['puestos']=['administracion'];self.esperado({'fee','invoice_total'})
 def test_trafficker_preserves_authorized_cpc(self):
  self.f.real['puestos']=['trafficker'];self.esperado({'CPC'})
 def test_direccion_preserves_all(self):
  self.f.real['puestos']=['direccion'];self.esperado({'fee','invoice_total','CPC','agency_profit'})
 def test_view_never_elevates(self):
  self.f.real['puestos']=['direccion'];self.f.vista={'id':'v','puestos':['account'],'estado':'activo','activo':True}
  self.f.e.crudo['personas'].append(self.f.vista)
  self.f.e.crudo['asignaciones'].append({'cliente_id':'c','persona_id':'v','silla':'account'})
  with self.f.con() as c:c.execute("UPDATE decisiones SET quien='v'")
  self.esperado(set())
 def test_serialized_array_vp_nested_money_removed(self):
  with self.f.con() as c:c.execute('UPDATE acciones SET vista_previa=?',(json.dumps([self.valor]),))
  code,d=self.f.request('acciones');self.assertEqual(code,200)
  self.assertEqual(json.loads(d['acciones'][0]['vista_previa']),[{'horas':7,'cantidad':0,'cuota_horas':8,'nested':{'horas':2}}])

if __name__=='__main__': unittest.main()
