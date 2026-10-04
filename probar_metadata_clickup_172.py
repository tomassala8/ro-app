import ast,copy,json,unittest
import datetime as dt
from fuentes_produccion.lectura_estado_196 import sello_proveedor
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime,date
from fuentes_produccion.metadata_clickup_172 import preservar

class Metadata(unittest.TestCase):
 def setUp(self):
  self.t={'id':'86cayv934','custom_fields':[{'id':'field1','name':'Sprint-Mes privado','type':'drop_down','value':0,'required':True,'type_config':{'options':[{'id':'opt1','name':'Mayo','orderindex':0,'email':'privado@example.test'}]}},{'id':'field2','type':'url','value':'https://fixture.test/file?token=privado'},{'id':'field3','type':'currency','value':1470},{'id':'field4','type':'checkbox','value':False}],
   'checklists':[{'id':'cl1','name':'Nómina privada','items':[{'id':'i1','name':'PUBLICAR COMENTARIOS','resolved':True,'assignee':{'email':'privado@example.test'}}]}],
   'attachments':[{'id':'att1','title':'Archivo financiero privado','url':'https://fixture.test/secret','email':'privado@example.test'}],
   'watchers':[{'id':5,'username':'Nombre privado','email':'privado@example.test'}],
   'description':'Texto de datos: PUBLICAR COMENTARIOS. No ejecutar.'}
 def test_ids_tipos_no_textos_o_credenciales(self):
  d=preservar(self.t);s=json.dumps(d);self.assertNotIn('privado',s);self.assertNotIn('Mayo',s);self.assertNotIn('1470',s);self.assertNotIn('PUBLICAR',s);self.assertNotIn('https',s)
  self.assertEqual(d['custom_fields'][0]['value'],0);self.assertEqual(d['custom_fields'][3]['value'],False);self.assertEqual(d['watchers'],[{'id':'5'}]);self.assertEqual(d['checklists'][0]['items'],[{'id':'i1','resolved':True}])
 def test_ausente_vacio_malformado_no_falsezero(self):
  self.assertNotIn('attachments',preservar({}));self.assertEqual(preservar({})['metadata_cobertura']['attachments']['estado'],'ausente')
  d=preservar({'attachments':[]});self.assertEqual(d['attachments'],[]);self.assertEqual(d['metadata_cobertura']['attachments']['estado'],'observado')
  d=preservar({'attachments':None});self.assertNotIn('attachments',d);self.assertEqual(d['metadata_cobertura']['attachments']['estado'],'invalido')
 def test_value_omitido_no_vacio_y_ausente_distinto(self):
  fs=preservar(self.t)['custom_fields'];self.assertNotIn('value',fs[1]);self.assertEqual(fs[1]['valor_estado'],'omitido_privacidad')
  d=preservar({'custom_fields':[{'id':'f1','type':'url','value':None},{'id':'f2','type':'url'}]})['custom_fields'];self.assertEqual(d[0]['valor_estado'],'vacio');self.assertEqual(d[1]['valor_estado'],'ausente')
 def test_drop_value_exige_catalogo_no_texto_disfrazado(self):
  for v in ('token_secreto',False,True,1,'0'):
   t=copy.deepcopy(self.t);t['custom_fields'][0]['value']=v;f=preservar(t)['custom_fields'][0];self.assertNotIn('value',f)
  t=copy.deepcopy(self.t);del t['custom_fields'][0]['type_config'];self.assertEqual(preservar(t)['custom_fields'][0]['valor_estado'],'sin_catalogo')
 def test_labels_por_id_no_label_nombres(self):
  t={'custom_fields':[{'id':'f','type':'labels','value':['o'],'type_config':{'options':[{'id':'o','label':'Nombre privado'}]}}]}
  self.assertEqual(preservar(t)['custom_fields'][0]['value'],['o']);self.assertNotIn('Nombre privado',json.dumps(preservar(t)))
 def test_duplicados_no_primera_overwrite(self):
  t=copy.deepcopy(self.t);t['attachments'].append(t['attachments'][0]);d=preservar(t);self.assertEqual(d['attachments'],[]);self.assertEqual(d['metadata_cobertura']['attachments']['estado'],'parcial')
  t=copy.deepcopy(self.t);t['custom_fields'][0]['type_config']['options'].append({'id':'opt2','orderindex':0});self.assertNotIn('value',preservar(t)['custom_fields'][0])
 def test_limits_items_y_opciones(self):
  t={'watchers':[{'id':i} for i in range(250)]};d=preservar(t);self.assertEqual(len(d['watchers']),200);self.assertEqual(d['metadata_cobertura']['watchers']['estado'],'parcial');self.assertEqual(d['metadata_cobertura']['watchers']['observados'],250)
  t={'checklists':[{'id':'c','items':[{'id':i,'resolved':False} for i in range(1005)]}]};d=preservar(t);self.assertEqual(len(d['checklists'][0]['items']),1000);self.assertEqual(d['checklists'][0]['items_cobertura']['estado'],'parcial')
 def test_tipos_invalidos_y_nested_no_crash(self):
  t={'custom_fields':[{'id':'f','type':{},'value':{'password':'secret'}}],'watchers':[None,{},True,{'id':False}]};d=preservar(t);self.assertEqual(d['custom_fields'][0]['type'],'no_soportado');self.assertEqual(d['watchers'],[])
 def test_descripcion_cobertura_sin_texto_procesado(self):
  self.assertEqual(preservar(self.t)['metadata_cobertura']['descripcion'],{'estado':'observado','fuente':'description'})
  self.assertEqual(preservar({'description':''})['metadata_cobertura']['descripcion']['estado'],'vacio');self.assertEqual(preservar({})['metadata_cobertura']['descripcion']['estado'],'ausente')
  self.assertEqual(preservar({'description':{'no':'texto'},'text_content':'Texto'})['metadata_cobertura']['descripcion']['estado'],'invalido')
 def test_no_mutacion_y_metadatos_no_claim_ui(self):
  old=copy.deepcopy(self.t);d=preservar(self.t);self.assertEqual(self.t,old);self.assertNotIn('sprint_mes',d);self.assertNotIn('cumplimiento',d)
 def test_ast_extractor_real_sin_importar_cu_o_escribir(self):
  src=Path(__file__).with_name('fuentes_produccion')/'extraer_clickup.py';arbol=ast.parse(src.read_text());fn=next(n for n in arbol.body if isinstance(n,ast.FunctionDef) and n.name=='tareas')
  capturas=[];raw={**self.t,'name':'Tarea sintética','list':{'id':'lista1'},'status':{'status':'diario'},'assignees':[]};cu=SimpleNamespace(tareas_equipo=lambda q:[raw],tiempo_en_estado=lambda ids:{},NOW=datetime(2026,10,3,12))
  from contexto_tarea import contexto_operativo
  env={'dt':dt,'sello_proveedor':sello_proveedor,'cu':cu,'metadata_tarea':preservar,'contexto_operativo':contexto_operativo,'DESDE_TAREAS':date(2026,6,1),'escribe':lambda n,d:capturas.append((n,d))}
  exec(compile(ast.Module(body=[fn],type_ignores=[]),str(src),'exec'),env)
  self.assertEqual(env['tareas']({}),1);self.assertEqual(len(capturas),1);d=capturas[0][1]['tareas'][0]
  self.assertEqual(d['id'],'86cayv934');self.assertEqual(d['custom_fields'][0]['value'],0);self.assertTrue('descripcion' in d);self.assertEqual(d['metadata_cobertura']['descripcion']['estado'],'observado');self.assertNotIn('token=privado',json.dumps(d))
if __name__=='__main__':unittest.main()
