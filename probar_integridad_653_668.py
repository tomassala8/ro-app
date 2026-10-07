import sys,importlib.util,copy,unittest
from pathlib import Path
def cargar(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
BASE=cargar('base668',Path(__file__).parent/'baselinefixture_embudo_668.py').calcular
from embudo_eventos import calcular as FIX
D='2026-10-01T00:00:00Z';H=C='2026-10-04T00:00:00Z'
def fixtures(etapa='venta'):
 ev=[];cov=[]
 for cid in ('clienteA','clienteB'):
  ev.extend([{'cliente_id':cid,'source':'ghl','lead_id':'lead'+cid,'event_id':'recibido'+cid,'etapa':'recibido','fecha':D},
    {'cliente_id':cid,'source':'ghl','lead_id':'lead'+cid,'event_id':'resultadoUnico','etapa':etapa,'fecha':'2026-10-02T00:00:00Z','confirmado':True,'criterio_version':'criterioV1'}])
  cov.append({'cliente_id':cid,'source':'ghl','desde':D,'hasta':H,'etapas':['recibido',etapa],'completa':True,'criterio_version':'criterioV1'})
 return ev,cov
class Integridad653(unittest.TestCase):
 def test_baseline_falsa_doble_tasa_y_candidato(self):
  for etapa in ('venta','asistencia','cualificado'):
   ev,cov=fixtures(etapa);old=BASE(ev,D,H,C,cov)
   self.assertEqual([g['cohorte']['etapas'][etapa]['tasa_sobre_recibidos'] for g in old['grupos']],[1.0,1.0])
   out=FIX(ev,D,H,C,cov);self.assertEqual(out['incidencias']['event_id_ambito_conflictivo'],1)
   for g in out['grupos']:
    self.assertEqual(g['cohorte']['etapas'][etapa]['observados'],0);self.assertEqual(g['cohorte']['etapas'][etapa]['estado'],'desconocido');self.assertIsNone(g['cohorte']['etapas'][etapa]['tasa_sobre_recibidos'])
 def test_variante_no_confirmada_otro_cid_no_desaparece_antes_conflicto(self):
  ev,cov=fixtures();ev[-1]['confirmado']=False
  self.assertEqual(BASE(ev,D,H,C,cov)['grupos'][0]['cohorte']['etapas']['venta']['tasa_sobre_recibidos'],1.0)
  self.assertTrue(all(g['cohorte']['etapas']['venta']['tasa_sobre_recibidos'] is None for g in FIX(ev,D,H,C,cov)['grupos']))
 def test_variante_cliente_malformado_invalida_ambas(self):
  ev,cov=fixtures();ev[-1]['cliente_id']={'invalido':True}
  out=FIX(ev,D,H,C,cov);self.assertEqual(out['incidencias']['event_id_ambito_conflictivo'],1)
  self.assertIsNone(out['grupos'][0]['cohorte']['etapas']['venta']['tasa_sobre_recibidos'])
 def test_order_y_replay_no_cambia_resultado(self):
  ev,cov=fixtures();ev.append(copy.deepcopy(ev[-1]));self.assertEqual(FIX(ev,D,H,C,cov),FIX(list(reversed(ev)),D,H,C,cov))
 def test_sources_independientes_preservan_namespace(self):
  ev,cov=fixtures();ev[2]['source']=ev[3]['source']=cov[1]['source']='otroOrigen'
  self.assertEqual(FIX(ev,D,H,C,cov),BASE(ev,D,H,C,cov))
 def test_event_ids_distintos_conservan_positivos(self):
  ev,cov=fixtures();ev[-1]['event_id']='resultadoB';before=copy.deepcopy(ev)
  self.assertEqual(FIX(ev,D,H,C,cov),BASE(ev,D,H,C,cov));self.assertEqual(ev,before)
 def test_futuro_id_distinto_no_contamina_cobertura_actual(self):
  ev,cov=fixtures();ev[-1]['event_id']='resultadoB';ev.append({**ev[1],'event_id':'eventoFuturo','fecha':'2026-10-05T00:00:00Z'})
  out=FIX(ev,D,H,C,cov);self.assertEqual(out,BASE(ev,D,H,C,cov));self.assertEqual(out['incidencias']['posterior_al_corte'],1)
  self.assertEqual(out['grupos'][0]['cohorte']['etapas']['venta']['tasa_sobre_recibidos'],1.0)
 def test_mismo_ambito_no_confirmado_ya_bloqueado_sin_nueva_semantica(self):
  ev,cov=fixtures();ev=ev[:2]+[{**ev[1],'confirmado':False}];cov=cov[:1]
  self.assertEqual(FIX(ev,D,H,C,cov),BASE(ev,D,H,C,cov))
if __name__=='__main__':unittest.main()
