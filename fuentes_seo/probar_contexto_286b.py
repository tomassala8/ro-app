import copy,unittest
from fuentes_seo.motores_contexto import motores_contexto,contexto_desde_cache,fecha_contexto_valida
from fuentes_seo.overlay_contexto_286 import preparar_overlay
from fuentes_seo.seo_prioridades_fuentes import adaptar_fuentes
NOW='2026-10-03T18:00:00Z'
CAT=[{'id':251,'name':'Google Mobile Spain','type':'google'}]
CFG={'site_engine_id':1,'search_engine_id':251,'region_name':'City, Region, Country','lang_code':'es','merge_map':2}
def doc():return {'catalogo':copy.deepcopy(CAT),'clientes':{'fixture':{'proyecto':10,'leido':'2026-10-03T16:00:00Z','fuente':'API configuración observada','configuraciones':[copy.deepcopy(CFG)]}}}
def pos():return {'clientes':{'fixture':{'proyecto':10,'motores':[{'site_engine_id':1,'palabras':[]}]}}}
class Test(unittest.TestCase):
 def ctx(self,d=None,m=None):return contexto_desde_cache('fixture',10,m or [{'site_engine_id':1}],d or doc(),NOW)
 def ov(self,a=None,c=None,**kw):
  args={'actual':a or doc(),'candidato':c or doc(),'mapa':{'fixture':10},'posiciones':pos(),'activos':{'fixture'},'ahora':NOW};args.update(kw);return preparar_overlay(**args)
 def test_maps_unknown_null(self):
  for raw in [None,True,False,'bad',3,-1]:
   c={**CFG,'merge_map':raw};r=motores_contexto([c],CAT)[0];self.assertIsNone(r['maps_separado']);self.assertIsNone(r['maps_modo'])
 def test_maps_modes_distinct_not_maps_only(self):
  for raw,sep,label in [(0,False,'sin_maps'),('1',False,'resultados_con_maps_incluidos'),('2',True,'maps_presentados_separadamente')]:
   r=motores_contexto([{**CFG,'merge_map':raw}],CAT)[0];self.assertIs(r['maps_separado'],sep);self.assertEqual(r['serie_actual'],label);self.assertNotEqual(label,'solo_maps')
 def test_current_config_not_position(self):
  r=self.ctx()[0];self.assertEqual(r['configuracion_actual']['region'],'City, Region, Country');self.assertEqual(r['configuracion_actual']['dispositivo'],'mobile');self.assertEqual(r['configuracion_actual']['idioma'],'es');self.assertIsNone(r['region']);self.assertIsNone(r['dispositivo']);self.assertFalse(r['aplica_fecha_distinta']);self.assertFalse(r['contexto_posicion_confirmado'])
 def test_no_mobile_does_not_desktop(self):self.assertIsNone(motores_contexto([CFG],[{'id':251,'name':'Google Spain'}])[0]['dispositivo'])
 def test_mobile_substring_not_word(self):self.assertIsNone(motores_contexto([CFG],[{'id':251,'name':'Google Automobiles'}])[0]['dispositivo'])
 def test_catalog_duplicate_no_first_last(self):
  for e in [CAT+CAT,CAT+[{'id':'251','name':'Google Desktop'}]]:self.assertEqual(motores_contexto([CFG],e),[])
 def test_config_duplicate_no_first_last(self):self.assertEqual(motores_contexto([CFG,CFG],CAT),[])
 def test_input_motor_duplicate_unknown(self):self.assertTrue(all(x['configuracion_actual']is None for x in self.ctx(m=[{'site_engine_id':1},{'site_engine_id':'1'}])))
 def test_project_duplicate_unknown(self):
  d=doc();d['clientes']['foreign']=copy.deepcopy(d['clientes']['fixture']);self.assertIsNone(self.ctx(d)[0]['configuracion_actual'])
 def test_future_invalid_naive_unknown(self):
  for f in ['2026-10-04','2026-10-03T19:00:00Z','2026-10-03T12:00:00','invalid']:
   d=doc();d['clientes']['fixture']['leido']=f;self.assertIsNone(self.ctx(d)[0]['configuracion_actual'])
 def test_daily_precision_not_fabricated(self):
  d=doc();d['clientes']['fixture']['leido']='2026-10-03';r=self.ctx(d)[0];self.assertEqual(r['fecha_contexto'],'2026-10-03');self.assertEqual(r['configuracion_actual']['precision_fecha'],'dia')
 def test_offset_future_and_utc(self):
  self.assertIsNone(fecha_contexto_valida('2026-10-03T21:00:00+02:00',NOW));self.assertEqual(fecha_contexto_valida('2026-10-03T18:00:00+02:00',NOW)['fecha'],'2026-10-03T16:00:00Z')
 def test_adapter_numeric_position_survives_no_decorating(self):
  sr=pos();sr['clientes']['fixture']['motores'][0]['palabras']=[{'k':'asesoria city','hoy':5,'mapa':2,'fechas':{'hoy':'2026-09-17','mapa':'2026-09-17'}}]
  ctx={'cliente_id':'fixture','servicio_seo_confirmado':True,'fuente_servicio':'fixture documental','ciudades_verificadas':[{'ciudad':'City','fuente':'fixture documental'}],'servicios_reales':['asesoria']}
  # Source adapter's objective helper contract differs from generic words: use its actual objective generator.
  from fuentes_seo.seo_prioridades import consultas_objetivo
  objs=consultas_objetivo(ctx)
  if not objs:self.fail('fixture requiere objetivo real')
  sr['clientes']['fixture']['motores'][0]['palabras'][0]['k']=objs[0]['consulta']
  r=adaptar_fuentes(ctx,sr,{},doc())['rankings'];self.assertTrue(r);self.assertEqual(r[0]['posicion'],5);self.assertIsNone(r[0]['ubicacion_medicion']);self.assertIsNone(r[0]['dispositivo'])
 def test_overlay_exact_preserves_prior_source_changed(self):
  a=doc();a['clientes']['fixture']['leido']='2026-10-03';a['clientes']['fixture']['fuente']='Lectura anterior documentada';a['clientes']['fixture']['configuraciones'][0]['region_name']='Old city'
  r=self.ov(a=a);e=r['evidencias_lecturas_anteriores']['fixture'];self.assertTrue(e['descriptor_distinto']);self.assertEqual(e['registro']['leido'],'2026-10-03');self.assertEqual(e['registro']['fuente'],'Lectura anterior documentada');self.assertFalse(e['intervalo_vigencia_confirmado']);self.assertFalse(r['promocionado'])
 def test_overlay_act_revoked(self):self.assertEqual(self.ov(activos=set())['clientes'],{})
 def test_overlay_mapping_changed(self):self.assertEqual(self.ov(mapa={'fixture':11})['clientes'],{})
 def test_overlay_missing_engine(self):
  p=pos();p['clientes']['fixture']['motores'].append({'site_engine_id':2});self.assertEqual(self.ov(posiciones=p)['clientes'],{})
 def test_overlay_duplicate_map_project(self):self.assertEqual(self.ov(mapa={'fixture':10,'foreign':10})['clientes'],{})
 def test_overlay_rejects_older(self):
  c=doc();c['clientes']['fixture']['leido']='2026-09-17';self.assertEqual(self.ov(c=c)['rechazados']['fixture'],'lectura_anterior_no_reemplaza')
if __name__=='__main__':unittest.main()
