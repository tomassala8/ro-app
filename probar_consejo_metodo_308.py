"""Cadencia local; fixtures y consumidores reales, sin HTTP/proveedor/BD real."""
import copy,ast,json,types,unittest
from contextlib import nullcontext
from datetime import date,datetime
from pathlib import Path
from unittest.mock import patch
import consejo_metodo_308 as C
import cerebro_operativo as B
import cerebro_api as API
import permisos as PER
import borradores_api as BA
from consejos_horas import neutralizar_consejo_horas
from consejos_paid_crm_304 import neutralizar_consejo_paid_crm
HOY='2026-10-03'
P=[{'id':'ops','estado':'activo','puestos':['operaciones']},{'id':'paid','estado':'activo','puestos':['trafficker']},{'id':'acc','estado':'activo','puestos':['account']}]
A=[{'persona_id':'paid','cliente_id':'c','silla':'trafficker','desde':'2026-09-01','principal':True,'confianza':'confirmada'}]
R={'cliente_id':'c','regla_id':C.REGLA,'cadencia_dias':15,'responsable_role':'trafficker','responsables_ids':['paid'],'responsable_id':'paid','incumplimiento':None,'estado':'sin_dato','ultima_confirmada':None,'proxima_revision':None,'fuentes_operativas':[{'tipo':'decision_humana','fecha':HOY,'detalle':'NO_COPIAR_PRECIO'}]}
D={'hoy':HOY,'sugerencias':[R],'cobertura_reuniones':{'completa':False},'_ids_308':['c'],'_personas_308':P,'_asignaciones_308':A}
REG={'regla':{'id':C.REGLA,'cadencia_dias':15,'responsable_role':'trafficker'},'clientes':[{'cliente_id':'c','estado_cohorte':'confirmada','cadencia_dias':15,'responsable_role':'trafficker','tipo_cohorte':'metodo_actual_recurrente'}]}

def pro(d=None,ps=None,asigs=None):return C.proyectar_metodo308(d or D,['c'],ps or P,asigs if asigs is not None else A,HOY)
def funciones(*names):
 tree=ast.parse(Path(__file__).with_name('ia.py').read_text());return compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'ia.py:308', 'exec')
class Metodo308(unittest.TestCase):
 def test_rule_without_events_not_noncompliance_schedule(self):
  r=pro()[0];self.assertEqual(r['estado'],'confirmar_programacion');self.assertIsNone(r['incumplimiento']);self.assertIsNone(r['reunion_agendada']);self.assertIsNone(r['ultima_confirmada']);self.assertEqual(r['responsable_id'],'paid');self.assertEqual(r['contacto_semanal_account'],'separado')
 def test_unclear_inactive_duplicate_tenure_not_confirmed_owner(self):
  variants=[[],[dict(A[0],confianza='alta')],[dict(A[0],principal=False)],[A[0],A[0]],[dict(A[0],desde=None)],[dict(A[0],desde='2026-10-04')],[dict(A[0],hasta='2026-09-30')],[dict(A[0],suplencia=True)]]
  for a in variants:
   with self.subTest(a=a):self.assertIsNone(pro(asigs=a)[0]['responsable_id']);self.assertEqual(pro(asigs=a)[0]['estado'],'confirmar_responsable')
  for ps in [[dict(P[1],estado='baja')],[P[1],P[1]],[dict(P[1],puestos=['account'])]]:self.assertIsNone(pro(ps=ps)[0]['responsable_id'])
 def test_exact_rule_no_price_alias_wrong_or_duplicate(self):
  for change in [{'regla_id':'otro'},{'cadencia_dias':15.0},{'responsable_role':'account'},{'incumplimiento':False},{'cliente_id':'c '}]:
   d=copy.deepcopy(D);d['sugerencias'][0].update(change);d['sugerencias'][0]['precio']=1470;self.assertEqual(pro(d),[])
  d=copy.deepcopy(D);d['sugerencias'].append(copy.deepcopy(R));self.assertEqual(pro(d),[])
 def test_source_date_stale_future_or_invalid_denied(self):
  for dt in ['2026-10-02','2026-10-04','2026-02-30']:self.assertEqual(pro(dict(D,hoy=dt)),[])
 def test_planning_not_celebration_or_fake_next_date(self):
  d=copy.deepcopy(D);d['sugerencias'][0].update(ultima_confirmada='2026-10-01',proxima_revision='2026-10-16',fuentes_operativas=[{'tipo':'reunion_programada','fecha':'2026-10-01','fuente':'zoom'}]);self.assertIsNone(pro(d)[0]['ultima_confirmada'])
  d['sugerencias'][0]['fuentes_operativas'][0]['tipo']='reunion_celebrada';d['sugerencias'][0]['proxima_revision']='2026-10-17';r=pro(d)[0];self.assertEqual(r['ultima_confirmada'],'2026-10-01');self.assertIsNone(r['proxima_revision']);self.assertEqual(r['estado'],'confirmar_programacion')
 def test_observed_interval_partial_unknown_not_breach_and_full_review(self):
  d=copy.deepcopy(D);d['sugerencias'][0].update(ultima_confirmada='2026-09-17',proxima_revision='2026-10-02',fuentes_operativas=[{'tipo':'reunion_celebrada','fecha':'2026-09-17','fuente':'zoom'}]);self.assertEqual(pro(d)[0]['estado'],'confirmar_recencia');self.assertIsNone(pro(d)[0]['incumplimiento'])
  d['cobertura_reuniones']={'completa':True,'desde':'2026-09-17','hasta':HOY};self.assertEqual(pro(d)[0]['estado'],'revisar_cadencia');self.assertIsNone(pro(d)[0]['incumplimiento']);self.assertIsNone(pro(d)[0]['reunion_agendada'])
  d['cobertura_reuniones']['hasta']='2026-10-30';self.assertEqual(pro(d)[0]['estado'],'confirmar_recencia')
 def test_pure_brain_adds_canonical_two_areas_no_prices_and_immutable(self):
  old=copy.deepcopy(D);r=B.generar(hoy=HOY,metodo=D);self.assertEqual(D,old);self.assertEqual(len(r['recomendaciones']),2);self.assertEqual({x['area'] for x in r['recomendaciones']},{'paid','accounts'});self.assertNotIn('NO_COPIAR_PRECIO',str(r));self.assertTrue(all(x['metodo_308']['incumplimiento'] is None for x in r['recomendaciones']));self.assertNotEqual(r['recomendaciones'][0]['regla_id'],r['recomendaciones'][1]['regla_id'])
 def entorno(self):
  raw={'personas':copy.deepcopy(P),'clientes':[{'id':'c','activo_confirmado':True}],'asignaciones':copy.deepcopy(A)}
  S=types.SimpleNamespace(E=types.SimpleNamespace(crudo=raw,nucleo_bloqueado=False),P=types.SimpleNamespace(hoy_iso=lambda:HOY,contexto=lambda *a:{},ver=lambda *a:{'ok':True},_vigente=PER._vigente,cartera_por_silla=PER.cartera_por_silla),ACT=types.SimpleNamespace(es_activo_id=lambda cid:True),ve_alguno=lambda *a:True)
  return S
 def lectura(self,path):return copy.deepcopy(REG if path==C.M.REGLAS else {'reuniones':[],'cobertura':{'completa':False}})
 def test_local_loader_scope_before_after_ACT_role_identity(self):
  S=self.entorno()
  with patch.object(C.M,'leer',side_effect=self.lectura):
   self.assertEqual(len(C.leer_metodo308(S,P[0],P[0])['_proyeccion_308']),1)
   S.ACT.es_activo_id=lambda cid:False;self.assertEqual(C.leer_metodo308(S,P[0],P[0])['_proyeccion_308'],[])
   S.E.crudo['personas'].append(copy.deepcopy(P[0]));self.assertIsNone(C.leer_metodo308(S,P[0],P[0]))
 def test_revocation_during_read_no_metadata_exposed(self):
  S=self.entorno();n=[0]
  def loader(p):
   n[0]+=1
   if n[0]==2:S.ACT.es_activo_id=lambda cid:False
   return self.lectura(p)
  with patch.object(C.M,'leer',side_effect=loader):
   d=C.leer_metodo308(S,P[0],P[0]);self.assertIsNone(d)  # Cambio durante IO: no reutilizar DTO ni metadatos.
 def test_current_owner_revalidated_before_API_response(self):
  S=self.entorno();initial=B.generar(hoy=HOY,metodo=D);S.E.crudo['asignaciones'][0]['confianza']='baja'
  with patch.object(C.M,'leer',side_effect=self.lectura):r=C.filtrar_recomendaciones308(S,P[0],P[0],initial)
  self.assertTrue(all(x['responsable_id'] is None for x in r['recomendaciones']))
 def test_actual_brain_API_and_area_filter_local_only(self):
  S=self.entorno();S.entrada_datos_modulo=lambda rel:{'modulos':['x']};S.modulo_recortado=lambda *a:None
  class H:
   def _api_get(self,*a):return 'fallback'
   def responder(self,code,d):return code,d
  API.enganchar(H,S)
  with patch.object(C.M,'leer',side_effect=self.lectura):
   code,r=H()._api_get('/api/cerebro/operativo',{'area':['accounts']},P[0],P[0]);self.assertEqual(code,200);self.assertEqual(len(r['recomendaciones']),1);self.assertEqual(r['recomendaciones'][0]['area'],'accounts')
 def test_current_actual_policy_14_without_external_reads(self):
  b=C.M.REGLAS.read_bytes();doc=json.loads(b);rows=C.M.reglas_confirmadas(doc);self.assertEqual(len(rows),14);self.assertTrue(all(r['cadencia_dias']==15 and r['responsable_role']=='trafficker' for r in rows));self.assertEqual(C.M.REGLAS.read_bytes(),b)
 def test_actual_draft_resolves_only_one_canonical_rule_no_raw_extension(self):
  S=self.entorno()
  with patch.object(C.M,'leer',side_effect=self.lectura),patch.object(BA,'leer_fuentes',return_value=[None,None,None]),patch.object(BA.cerebro_seo_api,'generar',return_value={'recomendaciones':[]}),patch.object(BA.metodo_cuentas,'estado_operativo',side_effect=AssertionError('raw extension forbidden')):
   for regla in (C.REGLA,C.REGLA+'_account'):
    r=BA.resolver(S,P[0],P[0],'c',regla);self.assertEqual(r['regla_id'],regla);self.assertIsNone(r['metodo_308']['reunion_agendada'])
    d=BA.preparar(r,{'cliente_id':'c','nombre':'Fixture','fecha_revision':HOY,'responsables_verificados':[]},lista_validada=None,tareas_visibles=None)
    self.assertFalse(d['enviable']);self.assertNotIn('assignees',d['payload']);self.assertNotIn('NO_COPIAR_PRECIO',str(d))
   self.assertIsNone(BA.resolver(S,P[0],P[0],'c','cadencia_fixture'))
 def test_identity_modules_viewas_and_client_intersection_denied(self):
  for mode in ('real_module','view_module','viewas','client'):
   S=self.entorno()
   if mode.endswith('module'):S.ve_alguno=lambda p,m:p['id']!=('ops' if mode=='real_module' else 'acc')
   else:S.P.ver=lambda p,d,c:{'ok':d['tipo']!=('ver_como' if mode=='viewas' else 'cliente_detalle')}
   with patch.object(C.M,'leer',side_effect=self.lectura):
    d=C.leer_metodo308(S,P[0],P[2]);self.assertTrue(d is None or not d['_ids_308'])
 def test_cached_or_llm_candidate_rebuilt_not_planned_meeting(self):
  S=self.entorno()
  with patch.object(C.M,'leer',side_effect=self.lectura):
   c=C.candidatos_metodo308(S,P[0],P[0])[0];out=C.normalizar_candidato_metodo308(dict(c,que='Reunión ya agendada',porque='Incumplimiento probado',confianza='alta'),S,P[0],P[0]);self.assertNotIn('ya agendada',out['que']);self.assertNotIn('Incumplimiento probado',out['porque']);self.assertEqual(out['confianza'],'media');self.assertIsNone(out['metodo_308']['reunion_agendada'])
   S.ACT.es_activo_id=lambda cid:False;self.assertIsNone(C.normalizar_candidato_metodo308(c,S,P[0],P[0]))
 def test_other_candidates_unaffected(self):
  c={'tipo':'ticket_urgente','cliente_id':'c','que':'Contestar'};self.assertIs(C.normalizar_candidato_metodo308(c,None,None,None),c)
 def test_candidate_identifies_only_authorized_unique_client(self):
  S=self.entorno();S.E.crudo['clientes'][0]['nombre']='Cliente autorizado'
  S.E.crudo['clientes'].append({'id':'foreign','nombre':'NO_EXPOSURE'})
  S.ACT.es_activo_id=lambda cid:cid=='c'
  with patch.object(C.M,'leer',side_effect=self.lectura):
   xs=C.candidatos_metodo308(S,P[0],P[0]);self.assertTrue(all(x['que'].endswith(' · Cliente autorizado') for x in xs));self.assertNotIn('NO_EXPOSURE',str(xs))
   S.E.crudo['clientes'].append({'id':'c','nombre':'Ambiguo'});self.assertEqual(C.candidatos_metodo308(S,P[0],P[0]),[])
 def test_actual_IA_cache_dynamic_and_LLM_rewrite_use_canonical_feed(self):
  from probar_consejos_paid_crm_304 import Consejo304
  S=self.entorno();S.E.modulos={'captacion'};S.P.enlace_seguro=lambda x:True;S.P.puestos_de=lambda p:set(p['puestos'])
  with patch.object(C.M,'leer',side_effect=self.lectura):
   c=C.candidatos_metodo308(S,P[0],P[0])[0]
   for modo in ('cache','dinamico','llm'):
    b=Consejo304().entorno(c);b['S']=S;b['candidatos_metodo308']=C.candidatos_metodo308;b['MC'].elegir=lambda cs,pant,*a,**k:[x for x in cs if pant in x.get('pantallas',[])]
    if modo=='dinamico':
     b['candidatos_de']=lambda *a:{'candidatos':[],'generado':HOY};exec(funciones('candidatos_al_momento'),b)
    b['_con_ia']=lambda *a:({'consejos':[{'ref':c['id'],'que':'Reunión agendada','porque':'Incumplimiento probado'}]},False)
    out=b['consejo'](P[0],P[0],{},'captacion',con_ia=modo=='llm')['consejos'];self.assertTrue(out)
    self.assertTrue(all(x['tipo']=='metodo_seguimiento_15d_paid' and x['confianza']=='media' and x['metodo_308']['reunion_agendada'] is None for x in out))
    self.assertNotIn('Incumplimiento probado',str(out))
   S.ACT.es_activo_id=lambda cid:False;self.assertEqual(b['consejo'](P[0],P[0],{},'captacion')['consejos'],[])
if __name__=='__main__':unittest.main()
