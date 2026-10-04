import copy
import unittest
from fuentes_produccion.transiciones_observadas_606 import proyectar

D='2026-09-28T00:00:00+02:00'
H=C='2026-10-05T00:00:00+02:00'
AT='2026-09-29T10:00:00+02:00'
CAT={'lista': [{'nombre':s,'tipo':'open'} for s in ['backlog','planning mensual','planning semanal','diario','en curso']]}
def task(initial='backlog',complete=False):
 return {'task_id':'task','list_id':'lista','cliente_id':'cliente','creada':AT,'creador_id':'creador','estado_inicial':initial,'fuente_creacion':'clickup','historial':{'completo':complete,'desde_creacion':complete,'hasta':C}}
def event(old='backlog',new='planning mensual',eid='evt',at='2026-09-30T10:00:00+02:00'):
 return {'event_id':eid,'task_id':'task','list_id':'lista','cliente_id':'cliente','actor_id':'movedor','estado_anterior':old,'estado_nuevo':new,'instante':at,'fuente':'clickup','token':'PRIVATE-SYNTHETIC','asignado_actual':'otro'}
def run(es=None,t=None,cat=None,clients=None,actors=None):
 return proyectar([event()] if es is None else es,[task() if t is None else t],cat or CAT,{'cliente'} if clients is None else clients,{'creador','movedor'} if actors is None else actors,D,H,C)
class Tests(unittest.TestCase):
 def test_mensual_positivo_no_inventa_cadena(self):
  r=run();self.assertEqual(r['tareas'][0]['metricas']['al_planning'],1);self.assertIsNone(r['tareas'][0]['metricas']['rompen_semanal']);self.assertFalse(r['tareas'][0]['historial_desde_creacion_completo'])
 def test_actor_no_creator(self):
  r=run();self.assertEqual(r['eventos'][0]['actor_id'],'movedor');self.assertEqual(r['por_creador'][0]['actor_id'],'creador');self.assertNotIn('token',str(r));self.assertNotIn('asignado_actual',str(r));self.assertNotIn('PRIVATE',str(r))
 def test_no_eventos_no_cero(self):
  r=run([]);self.assertIsNone(r['tareas'][0]['metricas']['al_planning']);self.assertIsNone(r['por_creador'][0]['metricas']['al_planning']);self.assertFalse(r['inventario_completo'])
 def test_directo_requiere_historia_y_clasificacion(self):
  for fire,key in [(True,'fuegos_directos'),(False,'rompen_semanal')]:
   t=task('planning semanal',True);t['fuego']={'confirmado':fire,'fuente':'clasificacion_confirmada','instante':AT};r=run([],t);self.assertEqual(r['tareas'][0]['metricas'][key],1)
   t['historial']['completo']=False;self.assertIsNone(run([],t)['tareas'][0]['metricas'][key])
 def test_intencion_no_evento(self):
  e=event();e['fuente']='app_pendiente';self.assertEqual(run([e])['eventos'],[]);self.assertEqual(run([e])['tareas'],[])
 def test_sin_class_no_breach(self):
  r=run([],task('diario',True));self.assertIsNone(r['tareas'][0]['metricas']['rompen_semanal']);self.assertIsNone(r['tareas'][0]['metricas']['fuegos_directos'])
 def test_salto_directo_complete(self):
  t=task(complete=True);t['fuego']={'confirmado':False,'fuente':'clasificacion_confirmada','instante':AT};r=run([event(new='diario')],t);self.assertEqual(r['tareas'][0]['metricas']['rompen_semanal'],1)
 def test_pasa_mensual_no_directo(self):
  t=task(complete=True);t['fuego']={'confirmado':False,'fuente':'clasificacion_confirmada','instante':AT};r=run([event(),event('planning mensual','diario','evt2','2026-10-01T10:00:00+02:00')],t);self.assertIsNone(r['tareas'][0]['metricas']['rompen_semanal'])
 def test_duplicados_globales_no_ultimo(self):
  for duplicate in [event(),dict(event(),estado_nuevo='diario')]:self.assertEqual(run([event(),duplicate])['tareas'],[])
  r=proyectar([event()],[task(),task()],CAT,{'cliente'},{'creador','movedor'},D,H,C);self.assertEqual(r['tareas'],[])
 def test_order_chain(self):
  for es in [[event(),event('planning mensual','diario','e2','2026-09-29T12:00:00+02:00')],[event(),event('backlog','diario','e2','2026-10-01T12:00:00+02:00')]]:self.assertEqual(run(es)['tareas'],[])
 def test_revoked_and_exact_binding(self):
  self.assertEqual(run(clients=set())['tareas'],[]);self.assertEqual(run(actors={'creador'})['tareas'],[])
  for k,v in [('list_id','otra'),('cliente_id','otro'),('actor_id','unknown'),('event_id',{}),('instante','2026-09-30T10:00:00+02:99')]:
   e=event();e[k]=v;self.assertEqual(run([e])['tareas'],[])
 def test_fechar(self):
  for at in ['2026-10-06T00:00:00Z','2026-09-30T10:00:00','2026-09-31T10:00:00Z','2026-09-30T10:00:00+14:01',True]:
   self.assertEqual(run([event(at=at)])['tareas'],[])
  with self.assertRaises(ValueError):proyectar([],[],CAT,{'cliente'},{'creador'},D,H,'invalid')
 def test_mensual_terminal_no_planning(self):
  cat=copy.deepcopy(CAT);cat['lista'][1]['tipo']='done';self.assertIsNone(run(cat=cat)['tareas'][0]['metricas']['al_planning'])
 def test_catalog_ambiguo(self):
  cat=copy.deepcopy(CAT);cat['lista'].append(cat['lista'][0]);self.assertEqual(run(cat=cat)['tareas'],[])
 def test_tipos_malformados_sin_excepcion(self):
  cat=copy.deepcopy(CAT);cat['lista'][0]['tipo']={};self.assertEqual(run(cat=cat)['tareas'],[])
  t=task();t['estado_inicial']=[];self.assertFalse(run(t=t)['tareas'][0]['creacion_observada'])
  t=task('diario',True);t['fuego']={'confirmado':1,'fuente':'clasificacion_confirmada','instante':AT};self.assertIsNone(run([],t)['tareas'][0]['metricas']['rompen_semanal'])
 def test_initial_chain_mismatch_no_directo(self):
  t=task('backlog',True);t['fuego']={'confirmado':False,'fuente':'clasificacion_confirmada','instante':AT};r=run([event('planning semanal','diario')],t);self.assertFalse(r['tareas'][0]['historial_desde_creacion_completo']);self.assertIsNone(r['tareas'][0]['metricas']['rompen_semanal'])
 def test_creation_aparte_invalida_no_asigna(self):
  t=task();t['creador_id']='unknown';r=run(t=t);self.assertEqual(r['tareas'][0]['metricas']['al_planning'],1);self.assertIsNone(r['tareas'][0]['creador_id']);self.assertEqual(r['por_creador'],[])
 def test_no_rejuvenecer_cobertura(self):
  t=task('diario',True);t['historial']['hasta']='2026-10-01T00:00:00Z';t['fuego']={'confirmado':False,'fuente':'clasificacion_confirmada','instante':AT};self.assertIsNone(run([],t)['tareas'][0]['metricas']['rompen_semanal'])
 def test_fuego_posterior_no_retroactividad(self):
  t=task('diario',True);t['fuego']={'confirmado':False,'fuente':'clasificacion_confirmada','instante':'2026-10-01T00:00:00Z'};self.assertIsNone(run([],t)['tareas'][0]['metricas']['rompen_semanal'])
 def test_ventana_halfopen_and_immutability(self):
  e=event(at=H);t=task();before=copy.deepcopy((e,t));r=run([e],t);self.assertEqual(r['eventos'],[]);self.assertIsNone(r['tareas'][0]['metricas']['al_planning']);self.assertEqual((e,t),before)
if __name__=='__main__': unittest.main()
