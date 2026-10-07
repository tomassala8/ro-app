import copy
import json
import tempfile
import unittest
from pathlib import Path
from fuentes_seo.seo_prioridades_fuentes import cargar_local, adaptar_fuentes
CTX={'cliente_id':'fixture','servicio_seo_confirmado':True,'fuente_servicio':'fixture confirmada','ciudades_verificadas':[{'ciudad':'Barcelona','fuente':'fixture'}],'servicios_reales':['asesoria']}
HOY='2026-10-04'
def sr():return {'clientes':{'fixture':{'proyecto':1,'motores':[{'site_engine_id':1,'palabras':[{'k':'asesoria Barcelona','hoy':6,'mapa':None,'fechas':{'hoy':'2026-10-03'}}]}]}}}
def gsc():return {'clientes':{'fixture':{'hasta':'2026-10-01','ventanas':{'mes':['2026-09-04','2026-10-01'],'mes_ant':['2026-08-07','2026-09-03']},'paginas':[['https://fixture.invalid/',5,30,4,10]]}}}
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.app=Path(self.tmp.name);self.cache=self.app/'fuentes_seo/_cache';self.cache.mkdir(parents=True)
 def tearDown(self):self.tmp.cleanup()
 def put(self,name,d): (self.cache/name).write_text(json.dumps(d))
 def load(self):return cargar_local(self.app,CTX,HOY)
 def valid(self):self.put('seranking.json',sr());self.put('gsc.json',gsc())
 def posiciones(self,r):return [o['posicion'] for o in r['objetivos'] if o['posicion'] is not None]
 def paginas(self,r):return [p for p in r['prioridades'] if p['tipo']=='revisar_pagina']
 def test_baseline(self):
  self.valid();r=self.load();self.assertEqual(self.posiciones(r),[6]);self.assertEqual(self.paginas(r)[0]['clics'],5);self.assertEqual(self.paginas(r)[0]['fecha'],'2026-10-01')
 def test_gsc_corrupto_sr_preservado(self):
  self.valid();(self.cache/'gsc.json').write_text('{PRIVATE');r=self.load();self.assertEqual(self.posiciones(r),[6]);self.assertEqual(self.paginas(r),[]);self.assertEqual(r['diagnosticos_fuentes']['gsc'],'copia_invalida');self.assertNotIn('PRIVATE',str(r));self.assertNotIn(str(self.cache),str(r))
 def test_sr_corrupto_gsc_preservado(self):
  self.valid();(self.cache/'seranking.json').write_text('{PRIVATE');r=self.load();self.assertEqual(self.posiciones(r),[]);self.assertEqual(self.paginas(r)[0]['clics'],5)
 def test_missingall_unknown_nozero(self):
  r=self.load();self.assertEqual(self.posiciones(r),[]);self.assertTrue(all(o['posicion'] is None for o in r['objetivos']));self.assertEqual(self.paginas(r),[]);self.assertTrue(all(v=='ausente' for v in r['diagnosticos_fuentes'].values()))
 def test_source_error_con_previous_no_promueve(self):
  self.valid();s=sr();s['clientes']['fixture']['_source_error']={'message':'PRIVATE','old':True};self.put('seranking.json',s);r=self.load();self.assertEqual(self.posiciones(r),[]);self.assertEqual(len(self.paginas(r)),1);self.assertEqual(r['diagnosticos_fuentes']['seranking'],'fuente_con_error');self.assertNotIn('PRIVATE',str(r))
 def test_errores_top_y_gsc(self):
  for k in ('_error','_source_error'):
   self.valid();s=sr();s[k]='PRIVATE';self.put('seranking.json',s);self.assertEqual(self.posiciones(self.load()),[])
   self.valid();s=gsc();s['clientes']['fixture'][k]='PRIVATE';self.put('gsc.json',s);r=self.load();self.assertEqual(self.paginas(r),[]);self.assertEqual(self.posiciones(r),[6])
 def test_duplicate_json_no_lastwins(self):
  self.valid();(self.cache/'seranking.json').write_text('{"clientes":{"fixture":{},"fixture":{}}}');r=self.load();self.assertEqual(self.posiciones(r),[]);self.assertEqual(r['diagnosticos_fuentes']['seranking'],'copia_invalida');self.assertEqual(len(self.paginas(r)),1)
 def test_shapes_no500(self):
  for s in [None,[],{'clientes':[]},{'clientes':{'fixture':None}},{'clientes':{'fixture':{'motores':{}}}},{'clientes':{'fixture':{'motores':[{'site_engine_id':1,'palabras':{}}]}}}]:
   self.valid();self.put('seranking.json',s);r=self.load();self.assertEqual(self.posiciones(r),[]);self.assertEqual(len(self.paginas(r)),1)
 def test_duplicate_motor_y_query(self):
  for dup in ('motor','palabra'):
   self.valid();s=sr();m=s['clientes']['fixture']['motores'][0]
   if dup=='motor':s['clientes']['fixture']['motores'].append(copy.deepcopy(m))
   else:m['palabras'].append(dict(m['palabras'][0],hoy=28))
   self.put('seranking.json',s);r=self.load();self.assertEqual(self.posiciones(r),[]);self.assertEqual(r['diagnosticos_fuentes']['seranking'],'identidad_duplicada')
 def test_duplicate_url_noalerta_fabricada(self):
  self.valid();g=gsc();g['clientes']['fixture']['paginas'].append(copy.deepcopy(g['clientes']['fixture']['paginas'][0]));self.put('gsc.json',g);r=self.load();self.assertEqual(self.paginas(r),[]);self.assertEqual(self.posiciones(r),[6])
 def test_future_y_stale_fecha_original(self):
  self.valid();s=sr();s['clientes']['fixture']['motores'][0]['palabras'][0]['fechas']['hoy']='2026-10-05';self.put('seranking.json',s);self.assertEqual(self.posiciones(self.load()),[])
  s['clientes']['fixture']['motores'][0]['palabras'][0]['fechas']['hoy']='2026-09-01';self.put('seranking.json',s);r=self.load();row=next(o for o in r['objetivos'] if o['posicion']==6);self.assertEqual(row['fecha'],'2026-09-01');self.assertEqual(row['dias_dato'],33)
 def test_contexto_corrupto_no_tumba_sr_gsc(self):
  self.valid();(self.cache/'seranking_motores.json').write_text('PRIVATE');r=self.load();self.assertEqual(self.posiciones(r),[6]);self.assertEqual(len(self.paginas(r)),1);self.assertEqual(r['diagnosticos_fuentes']['seranking_motores'],'copia_invalida')
 def test_nan_inf_bigint_no500(self):
  for val in [float('nan'),float('inf'),10**400]:
   self.valid();s=sr();s['clientes']['fixture']['motores'][0]['palabras'][0]['hoy']=val;self.put('seranking.json',s);self.assertEqual(self.posiciones(self.load()),[])
 def test_cero_posicion_unknown_clic0_observado(self):
  self.valid();s=sr();s['clientes']['fixture']['motores'][0]['palabras'][0]['hoy']=0;self.put('seranking.json',s);g=gsc();g['clientes']['fixture']['paginas'][0][1]=0;self.put('gsc.json',g);r=self.load();self.assertEqual(self.posiciones(r),[]);self.assertEqual(self.paginas(r)[0]['clics'],0)
 def test_symlink_recurso_no_lee_exterior(self):
  self.put('gsc.json',gsc());p=self.app/'outside.json';p.write_text(json.dumps(sr()));(self.cache/'seranking.json').symlink_to(p);r=self.load();self.assertEqual(self.posiciones(r),[]);self.assertEqual(len(self.paginas(r)),1);self.assertEqual(r['diagnosticos_fuentes']['seranking'],'no_disponible')
 def test_adapter_puro_no_mutar_y_recursos_errores(self):
  s=sr();g=gsc();old=copy.deepcopy((s,g));adaptar_fuentes(CTX,s,g);self.assertEqual((s,g),old)
if __name__=='__main__':unittest.main()
