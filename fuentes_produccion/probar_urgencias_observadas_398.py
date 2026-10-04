import copy,importlib.util,json,os,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
from fuentes_produccion.urgencias_observadas_398 import construir
APP=Path(__file__).resolve().parents[1];R=APP.parent/'RECUPERACION_CODEX_2026-10-03'
spec=importlib.util.spec_from_file_location('writer398',R/'preparar_urgencias_398.py');W=importlib.util.module_from_spec(spec);spec.loader.exec_module(W)
class Urgencias398(unittest.TestCase):
 def setUp(self):
  self.now=datetime(2026,10,4,1,tzinfo=timezone.utc);self.t={'id':'t1','lista_id':'l1','carpeta_id':'f1','prioridad':'urgent','estado':'completado','tipo_estado':'custom','estado_fuente':'clickup','estado_leido_utc':'2026-10-03T10:00:00Z','creada':'1790935200000','vence':'1791158400000','nombre':'CONTACTO_PRECIO','url':'https://host/?secret=x','prio_n':1}
  self.raw={'tareas':[self.t]};self.cat={'listas':{'l1':{'ok':True,'estados':[{'status':'completado','type':'custom'}]}}};self.folders={'f1':('c1','NO_PUBLICAR')}
 def build(self):return construir(self.raw,self.cat,self.folders,{'c1'},self.now)
 def test_explicit_priority_only(self):
  for p in [None,'high','normal','low',1,True,'URGENT',' urgent']:
   self.t['prioridad']=p;self.assertEqual(self.build()['filas'],[])
 def test_custom_completado_open_not_label_closed(self):
  d=self.build();self.assertEqual(d['abiertas_en_copia_ids'],['t1']);self.assertEqual(d['finales_en_copia_ids'],[]);self.assertIsNone(d['urgencias_actuales']);self.assertFalse(d['filas'][0]['final_flujo_en_copia'])
 def test_closed_done_not_reopened_and_not_acceptance(self):
  for tipo in ['closed','done']:
   self.t['tipo_estado']=tipo;self.cat['listas']['l1']['estados'][0]['type']=tipo;d=self.build();self.assertEqual(d['abiertas_en_copia_ids'],[]);self.assertEqual(d['finales_en_copia_ids'],['t1']);self.assertFalse(d['filas'][0]['aceptacion_verificada']);self.assertIsNone(d['filas'][0]['es_fuego_actual'])
 def test_today_state_stamp_cannot_certify_priority_same_read(self):
  self.t['estado_leido_utc']='2026-10-04T00:59:00Z';r=self.build()['filas'][0];self.assertIsNone(r['medicion_urgencia']);self.assertFalse(r['verificacion_conjunta']);self.assertIsNone(r['prioridad_leida_utc']);self.assertIsNone(r['es_fuego_actual'])
 def test_missing_future_naive_invalid_offset_state_read(self):
  for v in [None,'2026-10-04 00:59','2026-10-04T02:00:00Z','2026-02-30T12:00:00Z','2026-10-04T00:59:00+02:99']:
   self.t['estado_leido_utc']=v;self.assertEqual(self.build()['filas'],[])
 def test_wrong_provider_no_global_cache_timestamp(self):
  self.raw['meta']={'generado':'2026-10-04'};self.t['estado_fuente']='cache';self.assertEqual(self.build()['filas'],[])
 def test_catalog_missing_mismatch_or_duplicate(self):
  for cat in [{},{'listas':{'l1':{'ok':False}}},{'listas':{'l1':{'ok':True,'estados':[{'status':'completado','type':'closed'}]}}},{'listas':{'l1':{'ok':True,'estados':[{'status':'completado','type':'custom'}]*2}}}]:
   self.cat=cat;self.assertEqual(self.build()['filas'],[])
 def test_global_duplicate_even_with_nonurgent_copy(self):
  self.raw['tareas'].append({**self.t,'prioridad':'normal'});self.assertEqual(self.build()['filas'],[])
 def test_ids_malformed_do_not_coerce(self):
  for k,v in [('id',{}),('id',True),('id',10**1000),('lista_id',12),('carpeta_id',[]),('lista_id',[])]:
   orig=self.t[k];self.t[k]=v;self.assertEqual(self.build()['filas'],[]);self.t[k]=orig
 def test_act_canonical_and_empty_not_zero(self):
  d=construir(self.raw,self.cat,self.folders,set(),self.now);self.assertEqual(d['filas'],[]);self.assertIsNone(d['urgencias_actuales']);self.assertIsNone(d['cumplimiento']);self.assertTrue(d['cero_no_acredita_ausencia'])
 def test_future_due_date_does_not_create_or_filter_urgency(self):
  self.t['vence']='1893456000000';r=self.build()['filas'][0];self.assertEqual(r['vence_estado'],'observada');self.assertIsNone(r['inicio_urgencia_utc'])
 def test_invalid_dates_not_zero_future_creation_unknown(self):
  for v in [0,True,'bad',{},'1893456000000']:
   self.t['creada']=v;r=self.build()['filas'][0];self.assertIsNone(r['creada_utc']);self.assertEqual(r['creada_estado'],'invalida')
 def test_privacy_and_source_inputs_unchanged(self):
  orig=copy.deepcopy(self.raw);d=self.build();txt=json.dumps(d);self.assertNotIn('CONTACTO',txt);self.assertNotIn('NO_PUBLICAR',txt);self.assertNotIn('http',txt);self.assertNotIn('secret',txt);self.assertNotIn('nombre',txt);self.assertEqual(orig,self.raw)
 def test_private_replay_conflict(self):
  with tempfile.TemporaryDirectory() as tmp:
   dest=Path(tmp)/'candidate';d=self.build();a=W.publicar_candidato(dest,d,{});b=W.publicar_candidato(dest,d,{});self.assertTrue(b['replay']);self.assertEqual(a['candidato_sha256'],b['candidato_sha256']);self.assertEqual(dest.stat().st_mode&0o777,0o700)
   for p in dest.iterdir():self.assertEqual(p.stat().st_mode&0o777,0o600)
   with self.assertRaises(ValueError):W.publicar_candidato(dest,{**d,'urgencias_actuales':0},{})
 def test_json_duplicate_overflow_no_nan(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'fixture'
   for txt in ['{"x":1,"x":2}','{"x":1e999}','{"x":NaN}']:
    p.write_text(txt)
    with self.assertRaises(ValueError):W.leer(p)
 def test_fifo_does_not_block(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'fifo';os.mkfifo(p);real=W.os.open
   def audited(path,flags,*a):
    if Path(path)==p:self.assertTrue(flags&os.O_NONBLOCK)
    return real(path,flags,*a)
   with patch.object(W.os,'open',side_effect=audited):
    with self.assertRaises(ValueError):W.leer(p)
 def test_atomic_failure_no_half_candidate(self):
  with tempfile.TemporaryDirectory() as tmp:
   dest=Path(tmp)/'candidate'
   with patch.object(W.os,'rename',side_effect=OSError('fixture')):
    with self.assertRaises(OSError):W.publicar_candidato(dest,self.build(),{})
   self.assertEqual(list(Path(tmp).iterdir()),[])
if __name__=='__main__':unittest.main()
