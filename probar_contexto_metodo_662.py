"""Contexto308 actual, sin fuente privada/IO/runtime ni atribución histórica."""
import copy,unittest
import consejo_metodo_308 as C
H='2026-10-04'
P=[{'id':'paid','puestos':['trafficker'],'estado':'activo','activo':True}]
A=[{'cliente_id':'c','persona_id':'paid','silla':'trafficker','desde':'2026-09-01','principal':True,'confianza':'confirmada'}]
def doc():return {'hoy':H,'cobertura_reuniones':{'completa':False},'sugerencias':[{'cliente_id':'c','regla_id':C.REGLA,'cadencia_dias':15,'responsable_role':'trafficker','incumplimiento':None,'responsables_ids':['paid'],'responsable_id':'paid','ultima_confirmada':'2026-10-01','proxima_revision':'2026-10-16','fuentes_operativas':[{'tipo':'reunion_celebrada','fecha':'2026-10-01','fuente':'zoom'}]}]}
def run(d=None,ps=None,ids=None):return C.recomendaciones_metodo308(d or doc(),['c'] if ids is None else ids,P if ps is None else ps,A,H)
class Contexto662(unittest.TestCase):
 def test_fechas_fuente_y_revision_calculada_en_dos_areas(self):
  ds=doc();before=copy.deepcopy(ds);rs=run(ds);self.assertEqual(ds,before);self.assertEqual({r['area'] for r in rs},{'paid','accounts'})
  for r in rs:
   es={e['fuente']:e for e in r['evidencias']};ev=es['metodo_celebracion_confirmada'];rev=es['metodo_revision_calculada']
   self.assertEqual(ev['fecha'],'2026-10-01');self.assertIn('fuente: zoom',ev['texto']);self.assertIn('responsable histórico',ev['texto'])
   self.assertEqual(rev['fecha'],H);self.assertIn('2026-10-16',rev['texto']);self.assertIn('no acredita reunión programada o agendada',rev['texto']);self.assertIsNone(rev['periodo'])
   self.assertIsNone(r['metodo_308']['reunion_agendada']);self.assertIsNone(r['metodo_308']['incumplimiento']);self.assertEqual(r['responsable_id'],'paid')
 def test_ausente_y_programada_no_crean_evento_ni_revision(self):
  for sources in ([],[{'tipo':'reunion_programada','fecha':'2026-10-01','fuente':'zoom'}]):
   d=doc();d['sugerencias'][0]['fuentes_operativas']=sources
   for r in run(d):self.assertEqual([e['fuente'] for e in r['evidencias']],['metodo_confirmado_local'])
 def test_fecha_o_fuente_no_validada_no_promueve(self):
  for fuente in ('fuente_inventada','https://private.invalid/key',None):
   d=doc();d['sugerencias'][0]['fuentes_operativas'][0]['fuente']=fuente
   self.assertTrue(all(len(r['evidencias'])==1 for r in run(d)))
  d=doc();d['sugerencias'][0]['ultima_confirmada']='2026-10-05';self.assertTrue(all(len(r['evidencias'])==1 for r in run(d)))
 def test_proxima_incoherente_no_evidencia_calculo(self):
  d=doc();d['sugerencias'][0]['proxima_revision']='2026-10-17'
  for r in run(d):self.assertEqual([e['fuente'] for e in r['evidencias']],['metodo_confirmado_local','metodo_celebracion_confirmada'])
 def test_owner_revocado_no_atribuye_evento_a_otro(self):
  ps=[{**P[0],'puestos':['account']}]
  for r in run(ps=ps):
   self.assertIsNone(r['responsable_id']);self.assertFalse(r['metodo_308']['responsable_confirmado'])
   ev=r['evidencias'][1];self.assertNotIn('paid',ev['texto']);self.assertIn('No atribuye participantes',ev['texto'])
 def test_fuera_scope_y_cid_ambiguo_no_contexto(self):
  self.assertEqual(run(ids=[]),[]);d=doc();d['sugerencias'].append(copy.deepcopy(d['sugerencias'][0]));self.assertEqual(run(d),[])
 def test_evidencias_independientes_sin_modificar_otras(self):
  rs=run();rs[0]['evidencias'][1]['texto']='mutado';self.assertNotEqual(rs[1]['evidencias'][1]['texto'],'mutado')
if __name__=='__main__':unittest.main()
