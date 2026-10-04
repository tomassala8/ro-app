"""Revisión nueva: serialización y revocación; SQLite temporal, sin servidor real."""
import json
import sqlite3
import unittest
from unittest.mock import patch
import evidencias_kpi_api as K
from evidencias_kpi import ArchivoEvidencias
import probar_evidencias_kpi_api_151 as F151
import pruebas_informe_word_api_154 as F154

class Hechos160(unittest.TestCase):
 def setUp(self):self.f=F151.Api();self.f.setUp()
 def tearDown(self):self.f.tearDown()
 def test_payload_de_otro_cliente_no_se_serializa(self):
  self.f.post()
  with sqlite3.connect(self.f.path) as c:
   d=json.loads(c.execute('SELECT payload FROM registros').fetchone()[0]);d['cliente_id']='dos';d['email']='NO_DEBE_SALIR@example.com'
   c.execute('UPDATE registros SET payload=?',(json.dumps(d),))
  n,d=self.f.get();self.assertEqual(n,503);self.assertNotIn('registros',d)
 def test_campo_extra_privado_no_se_serializa(self):
  self.f.post()
  with sqlite3.connect(self.f.path) as c:
   d=json.loads(c.execute('SELECT payload FROM registros').fetchone()[0]);d['telefono']='612345678'
   c.execute('UPDATE registros SET payload=?',(json.dumps(d),))
  n,d=self.f.get();self.assertEqual(n,503);self.assertNotIn('registros',d)
 def test_recibo_post_revocado_despues_commit_no_entrega_datos(self):
  orig=ArchivoEvidencias.registrar
  def registrar(a,*args):
   d=orig(a,*args);self.f.S.E.crudo['personas'][0]['estado']='baja';return d
  with patch.object(ArchivoEvidencias,'registrar',registrar):n,d=self.f.post()
  self.assertEqual(n,403);self.assertNotIn('registro',d)
  with sqlite3.connect(self.f.path) as c:self.assertEqual(c.execute('SELECT count(*) FROM registros').fetchone()[0],1)
 def test_resumen_no_cuenta_payload_con_fecha_periodo_incoherente(self):
  self.f.post()
  with sqlite3.connect(self.f.path) as c:
   d=json.loads(c.execute('SELECT payload FROM registros').fetchone()[0]);d['fecha']='2026-08-30T10:00:00+00:00'
   c.execute('UPDATE registros SET payload=?',(json.dumps(d),))
  n,d=self.f.h._api_get(K.RUTA+'/resumen',{'semana_inicio':['2026-09-28']},self.f.own,self.f.own)
  self.assertEqual(n,503);self.assertNotIn('clientes',d)
 def test_DATABASE_URL_requiere_deposito_explicit(self):
  with patch.dict('os.environ',{'DATABASE_URL':'postgresql://fixture'},clear=True):
   with self.assertRaises(K.ErrorEvidencia):K.deposito()

class Word160(unittest.TestCase):
 def setUp(self):self.f=F154.WordAPI154();self.f.setUp()
 def tearDown(self):self.f.tearDown()
 def test_cliente_desactivado_canonico_no_exporta_aunque_ACT_positive(self):
  self.f.cl['activo']=False
  h,_=self.f.run_get();self.assertEqual(h.status,403);self.assertEqual(h.wfile.getvalue(),b'')
 def test_exencion_contrato_solo_Tomas_real_y_vista(self):
  from io import BytesIO
  import zipfile
  url='https://sign.zoho.eu/document/fixture'
  self.f.db.execute('UPDATE acciones SET vista_previa=?',(json.dumps({'periodo':'2026-09','apartados':{'mes':'Fuente '+url}}),));self.f.db.commit()
  tomas={'id':'tomas','puestos':['direccion'],'estado':'activo'};ops={'id':'ops','puestos':['operaciones'],'estado':'activo'}
  self.f.raw['personas']=[tomas,ops]
  for real,vista,esperado in [(ops,ops,False),(tomas,ops,False),(ops,tomas,False),(tomas,tomas,True)]:
   h,_=self.f.run_get(real=real,vista=vista);self.assertEqual(h.status,200)
   self.assertEqual(url in self.f.body(h),esperado)

if __name__=='__main__':unittest.main()
