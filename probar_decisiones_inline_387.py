"""387: contratos reales382 en SQLite temporal; ningún servidor/proveedor/DB principal."""
import json,sys,unittest
import probar_decisiones_durables_382 as B
UUID=B.UUID;UUID2=B.UUID2
import decisiones_durables_382 as M

def fixture():
 t=B.Pruebas382();t.setUp()
 try:
  b=t.nueva();b['tipo']='para_coti';a=t.save(b);antes=M.listar(t.S,t.con,'tomas','tomas')
  r={'operacion':'responder','intencion_id':UUID2,'id':a['recibo']['id'],'revision':a['recibo']['revision'],'decision':'Delegar','motivo':'Revisar el alcance','delegada_en':'coti'}
  recibo=t.save(r);despues=M.listar(t.S,t.con,'tomas','tomas')
  return {'antes':antes,'despues':despues,'recibo':recibo}
 finally:t.tearDown()
class Pruebas387(unittest.TestCase):
 def test_default_coti_y_capacidad(self):
  d=fixture();r=d['antes']['decisiones'][0];self.assertEqual(r['tipo'],'para_coti');self.assertTrue(r['puede_responder']);self.assertIsNone(r['respondida']);self.assertFalse(r['envio_realizado'])
 def test_respuesta_minima_delegada_no_notificacion(self):
  d=fixture();r=d['despues']['decisiones'][0];self.assertEqual(r['respuesta'],{'decision':'Delegar','motivo':'Revisar el alcance','delegada_en':'coti'});self.assertFalse(r['puede_responder']);self.assertFalse(d['recibo']['recibo']['ejecucion_verificada']);self.assertNotIn('datos',r)
if __name__=='__main__':
 if '--fixture' in sys.argv:print(json.dumps(fixture()))
 else:unittest.main()
