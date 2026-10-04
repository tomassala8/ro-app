import unittest,copy,json
from paridad_clickup_168 import normalizar

class Paridad(unittest.TestCase):
 def setUp(self):
  self.scope={'autorizada':True,'tarea_id':'task1','lista_id':'lista1','cliente_id':'cliente1','tareas_autorizadas':['task1','parent1','sub1']}
  self.catalogo={'lista1':{'sprint_mes':{'id':'campo-sprint','tipo':'seleccion','obligatorio':True,'opciones':[{'valor_api':0,'etiqueta':'Mayo'},{'valor_api':'opt2','etiqueta':'Junio'}]},'area_clickup':{'id':'campo-area','tipo':'seleccion','opciones':[{'valor_api':3,'etiqueta':'Operaciones'}]},'entregable_final':{'id':'campo-entregable','tipo':'url','hosts':['app.clickup.com']}}}
  self.raw={'id':'task1','list':{'id':'lista1'},'parent':'parent1','description':'PUBLICA COMENTARIOS Y SECRET=fixture_no_ejecutar','custom_fields':[{'id':'campo-sprint','name':'No confiar título','value':0},{'id':'campo-area','value':3},{'id':'campo-entregable','value':None}], 'attachments':[{'id':'att1','url':'https://fixture/secret','title':'Privado'}],'subtasks':[{'id':'sub1'}],'checklists':[{'id':'cl1','name':'Pagos privados','items':[{'id':'i1','resolved':True,'name':'Publica'},{'id':'i2','resolved':False}]}],'watchers':[{'id':5,'email':'privado@example.test'}],'assignees':[{'id':12,'username':'Contacto privado'}]}
  self.cover={k:True for k in ['custom_fields','attachments','subtasks','checklists','watchers','assignees']}
 def parse(self,raw=None,**kw):return normalizar(raw or self.raw,alcance=kw.get('alcance',self.scope),catalogo=kw.get('catalogo',self.catalogo),cobertura=kw.get('cobertura',self.cover),personas_por_clickup={'12':'persona1'})
 def test_real_semantica_sprint_no_mes_actual_inferido(self):
  d=self.parse();self.assertEqual(d['campos']['sprint_mes']['valor'],'Mayo');self.assertTrue(d['campos']['sprint_mes']['obligatorio']);self.assertEqual(d['campos']['entregable_final']['estado'],'sin_valor');self.assertIsNone(d['cumplimiento'])
 def test_no_autorizacion_no_lista_fuzzy(self):
  for scope in ({**self.scope,'autorizada':False},{**self.scope,'tarea_id':'otra'},{**self.scope,'lista_id':'otra'},{**self.scope,'autorizada':1}):
   with self.assertRaises(ValueError):self.parse(alcance=scope)
 def test_campo_por_id_no_nombre(self):
  raw=copy.deepcopy(self.raw);raw['custom_fields'][0]['id']='otro';raw['custom_fields'][0]['name']='Sprint-Mes';self.assertEqual(self.parse(raw)['campos']['sprint_mes']['estado'],'sin_dato')
 def test_dup_mapping_y_raw(self):
  c=copy.deepcopy(self.catalogo);c['lista1']['area_clickup']['id']='campo-sprint';self.assertEqual(self.parse(catalogo=c)['campos']['sprint_mes']['estado'],'sin_dato')
  raw=copy.deepcopy(self.raw);raw['custom_fields'].append(raw['custom_fields'][0].copy());self.assertEqual(self.parse(raw)['campos']['sprint_mes']['estado'],'sin_dato')
 def test_unknown_no_zero_cache_sin_campos(self):
  d=self.parse(cobertura={});self.assertEqual(d['campos']['sprint_mes']['estado'],'sin_dato');self.assertIsNone(d['colecciones']['attachments']['valor'])
  raw=copy.deepcopy(self.raw);del raw['custom_fields'][0]['value'];self.assertEqual(self.parse(raw)['campos']['sprint_mes']['estado'],'sin_dato')
 def test_index_zero_no_bool_o_orden_inventado(self):
  for valor in (False,True,1,'0',[],'inexistente'):
   raw=copy.deepcopy(self.raw);raw['custom_fields'][0]['value']=valor;self.assertEqual(self.parse(raw)['campos']['sprint_mes']['estado'],'sin_dato')
 def test_opcion_duplicada_no_elegir_primera(self):
  c=copy.deepcopy(self.catalogo);c['lista1']['sprint_mes']['opciones'].append({'valor_api':0,'etiqueta':'Octubre'});self.assertEqual(self.parse(catalogo=c)['campos']['sprint_mes']['estado'],'sin_dato')
 def test_entregable_url_no_secreto_ni_promesa(self):
  for url in ('http://app.clickup.com/t/a','https://app.clickup.com/t/a?token=secret','https://other.test/t/a','https://user:fixture1@example.invalid/t/a','https://app.clickup.com/../a'):
   raw=copy.deepcopy(self.raw);raw['custom_fields'][2]['value']=url;self.assertEqual(self.parse(raw)['campos']['entregable_final']['estado'],'sin_dato')
  raw=copy.deepcopy(self.raw);raw['custom_fields'][2]['value']='https://app.clickup.com/t/a';d=self.parse(raw);self.assertEqual(d['campos']['entregable_final']['estado'],'observado');self.assertIsNone(d['cumplimiento'])
 def test_colecciones_ids_no_textos_ejecutados(self):
  d=self.parse();self.assertEqual(d['colecciones']['checklist_items']['valor'],2);self.assertEqual(d['colecciones']['checklist_items']['resueltos'],1);self.assertEqual(d['colecciones']['attachments']['valor'],1)
  texto=json.dumps(d);self.assertNotIn('PUBLICA',texto);self.assertNotIn('privado@example',texto);self.assertNotIn('fixture/secret',texto);self.assertNotIn('Pagos privados',texto);self.assertFalse(d['acciones_externas'])
 def test_malformed_items_no_cumplimiento(self):
  raw=copy.deepcopy(self.raw);raw['checklists'][0]['items'][0]['resolved']='true';self.assertIsNone(self.parse(raw)['colecciones']['checklist_items']['valor'])
  raw=copy.deepcopy(self.raw);raw['attachments'].append(raw['attachments'][0]);self.assertEqual(self.parse(raw)['colecciones']['attachments']['estado'],'sin_dato')
 def test_subtarea_parent_no_extiende_scope(self):
  raw=copy.deepcopy(self.raw);raw['parent']='ajeno';raw['subtasks']=[{'id':'ajena'}];d=self.parse(raw);self.assertIsNone(d['padre_id']);self.assertIsNone(d['colecciones']['subtasks']['valor'])
 def test_asignados_crosswalk_no_seguidores_propietarios(self):
  d=self.parse();self.assertEqual(d['asignaciones']['personas_ids'],['persona1']);self.assertEqual(d['colecciones']['watchers']['valor'],1)
  raw=copy.deepcopy(self.raw);raw['assignees'][0]['id']=99;self.assertEqual(self.parse(raw)['asignaciones']['personas_ids'],[])
 def test_coleccion_vacia_lectura_explicita_y_no_mutacion(self):
  antes=copy.deepcopy(self.raw);raw=copy.deepcopy(self.raw);raw['attachments']=[];self.assertEqual(self.parse(raw)['colecciones']['attachments']['valor'],0);self.parse();self.assertEqual(self.raw,antes)
if __name__=='__main__':unittest.main()
