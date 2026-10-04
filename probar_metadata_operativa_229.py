"""Opt-in privado229: títulos215 y URL catálogo explícito, fixtures sin red."""
import copy,json,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from fuentes_produccion.metadata_clickup_172 import preservar
from fuentes_produccion.metadata_operativa_229 import url_permitida
from escaner_secretos import escanear_fichero
class Metadata229(unittest.TestCase):
 def setUp(self):
  self.t={'id':'task-fixture','list':{'id':'list-fixture'},'checklists':[{'id':'check','name':'Antes de entregar','items':[{'id':'item','name':'Comprobar página','resolved':False}]}],
   'custom_fields':[{'id':'delivery','name':'Entregable Final','type':'url','value':'https://drive.google.com/file/d/fixture'}]}
  self.cat={'list-fixture':{'campo_id':'delivery','tipo':'url','semantica':'entregable_final','confirmado':True,'fuente':'fixture-evidencia','hosts':['drive.google.com']}}
 def p(self,cat=None):return preservar(self.t,ampliacion_operativa=True,catalogo_entregable=cat)
 def test_default_inmutable172_no_titulos_ni_url(self):
  old=copy.deepcopy(self.t);d=preservar(self.t);self.assertNotIn('nombre',d['checklists'][0]);self.assertNotIn('entregable_candidato',d);self.assertEqual(self.t,old)
 def test_optin_titulos_sin_activar219(self):
  d=self.p();self.assertEqual(d['checklists'][0]['nombre'],'Antes de entregar');self.assertEqual(d['checklists'][0]['items'][0]['nombre'],'Comprobar página');self.assertEqual(d['ampliacion_operativa']['entregable'],'sin_catalogo');self.assertFalse(d['ampliacion_operativa']['activacion_publica'])
 def test_215_credenciales_contactos_importes_no_reaparecen(self):
  self.t['checklists'][0]['name']='**clave**: `Fixture9_Sensible`';self.t['checklists'][0]['items'][0]['name']='Revisar <b>página</b> correo persona@example.invalid\nPresupuesto 1470 €\nhttps://fixture.test/path?token=private'
  d=self.p();text=json.dumps(d);self.assertNotIn('Fixture9_Sensible',text);self.assertNotIn('persona@example',text);self.assertNotIn('1470',text);self.assertNotIn('token=',text)
  with TemporaryDirectory() as tmp:
   p=Path(tmp)/'candidato.json';p.write_text(text);self.assertEqual(len(escanear_fichero(p)),0)
 def test_titulo_truncado_estado_y_ausente(self):
  self.t['checklists'][0]['name']='x'*500;d=self.p()['checklists'][0];self.assertEqual(len(d['nombre']),400);self.assertEqual(d['nombre_estado'],'truncado');self.t['checklists'][0].pop('name');self.assertEqual(self.p()['checklists'][0]['nombre_estado'],'ausente')
 def test_no_map_nombre_libre_ni_primera_url(self):
  d=self.p();self.assertNotIn('entregable_candidato',d);self.cat['list-fixture']['campo_id']='other';d=self.p(self.cat);self.assertEqual(d['entregable_candidato']['estado'],'campo_no_observado');self.assertIsNone(d['entregable_candidato']['url'])
 def test_url_exacta_admitida_no_valida_remoto(self):
  d=self.p(self.cat);self.assertEqual(d['entregable_candidato']['url'],self.t['custom_fields'][0]['value']);self.assertEqual(d['entregable_candidato']['estado'],'url_admitida_politica')
 def test_signed_url_no_transformaciones(self):
  for url in ['https://drive.google.com/file?token=secret','https://drive.google.com/file?pwd=x','https://drive.google.com/file#secret','https://host.example/file','http://drive.google.com/file','https://user:fixture1@example.invalid/file','https://drive.google.com:9443/file','https://drive.google.com/start_url/secret','https://drive.google.com/%73tart_url/secret']:
   self.t['custom_fields'][0]['value']=url;d=self.p(self.cat);self.assertEqual(d['entregable_candidato']['estado'],'url_rechazada');self.assertIsNone(d['entregable_candidato']['url'])
 def test_catalogo_confirmacion_semantica_lista_tipo(self):
  for key,value in [('confirmado',False),('semantica','precio'),('tipo','text'),('campo_id',[]),('fuente','')]:
   cat=copy.deepcopy(self.cat);cat['list-fixture'][key]=value;self.assertNotIn('entregable_candidato',self.p(cat))
  self.t['list']['id']='list-other';self.assertNotIn('entregable_candidato',self.p(self.cat))
 def test_valor_texto_no_url_native(self):
  self.t['custom_fields'][0]['type']='text';d=self.p(self.cat);self.assertEqual(d['entregable_candidato']['estado'],'tipo_incoherente');self.assertIsNone(d['entregable_candidato']['url'])
 def test_vacio_vs_ausente(self):
  self.t['custom_fields'][0]['value']=None;self.assertEqual(self.p(self.cat)['entregable_candidato']['estado'],'vacio_observado');self.t['custom_fields'][0].pop('value');self.assertEqual(self.p(self.cat)['entregable_candidato']['estado'],'valor_ausente')
 def test_field_duplicado_no_firstwin(self):
  self.t['custom_fields'].append(copy.deepcopy(self.t['custom_fields'][0]));self.assertEqual(self.p(self.cat)['entregable_candidato']['estado'],'campo_no_observado')
 def test_boolean_optin_unico(self):
  self.assertNotIn('ampliacion_operativa',preservar(self.t,ampliacion_operativa='true'))
if __name__=='__main__':unittest.main()
