"""Proyección real después de permisos+ACT, sólo fixtures; ninguna fuente regenerada."""
import copy
import unittest
from unittest.mock import patch
import probar_clientes_activos_201 as fixtures
from proyeccion_agregados_activos import crm, verdad
from fuentes_verdad import clientes_activos as ACT
import permisos as P
from pruebas_permisos_servicio import recortador_puro


class Agregados(unittest.TestCase):
 def verdad(self):
  return {'generado':'2026-09-30','resumen':{'critico':99,'atencion':99,'bien':99,'nuevos':99,'sin_account':99,'sin_reunion_mes_pasado':99,'bloqueo_callado':99},
   'comun':[{'id':'a','gravedad':'critico','nuevo':True,'sin_account':False}],
   'clientes':[{'cliente_id':'a','sin_reunion_mes_pasado':False,'bloqueo_callado':True}],
   'carteras':[{'persona_id':'p','principal':['a'],'apoyo':[],'n_principal':99,'n_apoyo':99,'universo':{'fuera':[],'dentro':99,'texto':'Nombre ajeno legado'}}]}
 def crm(self):
  return {'generado':'2026-09-30','ventanas':{'leads':'30 días descriptivos, sin cohortes'},
   'subcuentas':[{'sub_id':'x','cliente_id':'a','tipo':'cliente','especialista_id':'p','encendida':True,'estado':'verde','leads_30d':0,'citas_30d':{'celebradas':0}}],
   'resumen':{'subcuentas':99,'leads_30d':99,'pct_verde':100,'citas_30d':{'celebradas':99},'encendidas_sin_especialista':['Cliente ajeno']},
   'especialistas':[{'id':'p','clientes':99,'subcuentas':99,'verde':99,'rojo':9,'sin_subcuenta':['Cliente ajeno'],'tope':16}]}
 def test_verdad_count_visible_flags_tipados_sin_rejuvenecer(self):
  d=self.verdad();before=copy.deepcopy(d);r=verdad(d)
  self.assertEqual(r['resumen']['critico'],1);self.assertEqual(r['resumen']['sin_account'],0);self.assertEqual(r['resumen']['bloqueo_callado'],1)
  self.assertEqual(r['carteras'][0]['n_principal'],1);self.assertEqual(r['carteras'][0]['universo']['dentro'],1);self.assertNotIn('ajeno',r['carteras'][0]['universo']['texto'])
  self.assertEqual(r['agregados_cobertura']['fuente_generado'],'2026-09-30');self.assertEqual(d,before)
 def test_portfolio_unknown_foreign_refs_not_counts_or_ids(self):
  d=self.verdad();d['carteras'][0]['principal']+=['foreign','unknown'];r=verdad(d)['carteras'][0]
  self.assertEqual(r['principal'],['a']);self.assertEqual(r['n_principal'],1)
 def test_bool_missing_strings_no_false_confirmation(self):
  d=self.verdad();d['comun'][0]['sin_account']='false';del d['clientes'][0]['sin_reunion_mes_pasado']
  r=verdad(d);self.assertIsNone(r['resumen']['sin_account']);self.assertIsNone(r['resumen']['sin_reunion_mes_pasado'])
 def test_status_unknown_not_bien_or_empty(self):
  d=self.verdad();d['comun'][0]['gravedad']='desconocido';r=verdad(d)['resumen']
  self.assertIsNone(r['bien']);self.assertIsNone(r['critico']);self.assertEqual(r['estado_desconocido'],1)
 def test_duplicate_identity_ambiguous_not_doublecount(self):
  d=self.verdad();d['comun']*=2;r=verdad(d);self.assertIsNone(r['resumen']['critico']);self.assertIsNone(r['resumen']['nuevos'])
  d=self.crm();d['subcuentas']*=2;self.assertIsNone(crm(d)['resumen']['subcuentas'])
 def test_empty_measured_rows_zero_count_no_health(self):
  d=self.crm();d['subcuentas']=[];r=crm(d)['resumen'];self.assertEqual(r['subcuentas'],0);self.assertEqual(r['encendidas'],0);self.assertIsNone(r['pct_verde']);self.assertIsNone(r['leads_30d']);self.assertIsNone(r['asistencia_pct'])
 def test_no_window_coverage_no_rates_no_calendar_fabrication(self):
  d=self.crm();r=crm(d);self.assertEqual(r['resumen']['subcuentas'],1);self.assertEqual(r['resumen']['encendidas'],1)
  for k in ('leads_30d','pct_verde','asistencia_pct','velocidad_pct_1h','despachos_cumplen_garantia','encendidas_sin_especialista'):self.assertIsNone(r['resumen'][k])
  self.assertIsNone(r['resumen']['citas_30d']['celebradas']);self.assertEqual(r['ventanas'],d['ventanas']);self.assertEqual(r['generado'],d['generado'])
 def test_specialist_connected_is_not_assigned_portfolio(self):
  d=self.crm();r=crm(d)['especialistas'][0];self.assertEqual(r['subcuentas'],1);self.assertIsNone(r['clientes']);self.assertIsNone(r['rojo']);self.assertIsNone(r['sin_subcuenta'])
 def test_diagnostics_count_not_client(self):
  d=self.crm();d['subcuentas'].append({'sub_id':'test','tipo':'prueba','encendida':True});r=crm(d)['resumen']
  self.assertEqual((r['subcuentas'],r['de_clientes'],r['pruebas_e_internas'],r['encendidas']),(2,1,1,1))
 def test_missing_array_unknown_no_cached_total(self):
  d=self.crm();del d['subcuentas'];self.assertIsNone(crm(d)['resumen']['subcuentas'])
 def test_universe_incoherent_unknown_and_no_old_text(self):
  d=self.verdad();d['carteras'][0]['universo']['fuera']=[None];r=verdad(d)['carteras'][0]['universo'];self.assertIsNone(r['dentro']);self.assertNotIn('ajeno',r['texto'])

class Alcance(unittest.TestCase):
 setUp = fixtures.Activos.setUp
 def test_summary_post_p_real_vista_no_global_count(self):
  real={'id':'tomas_fixture','puestos':['direccion']};vista={'id':'cuentas','puestos':['account']}
  raw={'clientes':[{'id':'propio','nombre':'Propio'},{'id':'ajeno','nombre':'Ajeno'}],'personas':[real,vista], 'asignaciones':[{'persona_id':'cuentas','cliente_id':'propio','silla':'account'}]}
  d={'generado':'2026-09-30','comun':[{'id':cid,'nombre':cid.title(),'gravedad':'critico','nuevo':False,'sin_account':False} for cid in ('propio','ajeno','medalba')], 'clientes':[], 'resumen':{'critico':99}}
  with P.mirando_como(real,raw):r=ACT.quitar_bajas(recortador_puro(raw)(vista,P.contexto(vista,raw),d),'verdad/clientes')
  self.assertEqual([f['id'] for f in r['comun']],['propio']);self.assertEqual(r['resumen']['critico'],1)
  self.assertEqual(r['agregados_cobertura']['fuente_generado'],'2026-09-30')
 def test_real_restricted_view_broad_cannot_expand_aggregate(self):
  real={'id':'cuentas','puestos':['account']};vista={'id':'tomas_fixture','puestos':['direccion']}
  raw={'clientes':[{'id':'propio','nombre':'Propio'},{'id':'ajeno','nombre':'Ajeno'}],'personas':[real,vista], 'asignaciones':[{'persona_id':'cuentas','cliente_id':'propio','silla':'account'}]}
  d={'subcuentas':[{'sub_id':cid,'tipo':'cliente','cliente_id':cid,'encendida':True} for cid in ('propio','ajeno')], 'resumen':{'subcuentas':99}}
  with P.mirando_como(real,raw):r=ACT.quitar_bajas(recortador_puro(raw)(vista,P.contexto(vista,raw),d),'crm/crm')
  self.assertEqual([f['cliente_id'] for f in r['subcuentas']],['propio']);self.assertEqual(r['resumen']['subcuentas'],1)
 def test_crm_after_double_scope_and_act_counts_only_returned(self):
  real={'id':'tomas_fixture','puestos':['direccion']};vista={'id':'cuentas','puestos':['account']}
  raw={'clientes':[{'id':'propio','nombre':'Propio'},{'id':'ajeno','nombre':'Ajeno'}],'personas':[real,vista], 'asignaciones':[{'persona_id':'cuentas','cliente_id':'propio','silla':'account'}]}
  d={'subcuentas':[{'sub_id':cid,'tipo':'cliente','cliente_id':cid,'encendida':True} for cid in ('propio','ajeno','medalba')], 'resumen':{'encendidas':99},'especialistas':[{'id':'p','clientes':99,'sin_subcuenta':['Ajeno']}]}
  with P.mirando_como(real,raw):r=ACT.quitar_bajas(recortador_puro(raw)(vista,P.contexto(vista,raw),d),'crm/crm')
  self.assertEqual(r['resumen']['subcuentas'],1);self.assertEqual(r['resumen']['encendidas'],1);self.assertIsNone(r['especialistas'][0]['clientes']);self.assertIsNone(r['especialistas'][0]['sin_subcuenta'])

if __name__=='__main__':unittest.main()
