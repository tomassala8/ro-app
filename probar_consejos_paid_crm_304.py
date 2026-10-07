"""Gate y funciones reales por AST/import puro; no proveedor/servir ni DB real."""
import ast,copy,json,types,unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from consejos_paid_crm_304 import neutralizar_consejo_paid_crm as gate,TIPOS
from consejos_horas import neutralizar_consejo_horas
from consejo_metodo_308 import normalizar_candidato_metodo308
from consejos_cartera_318 import normalizar_consejo_cartera318
HOY='2026-10-03'
BASE={'id':'al:fixture','tipo':'pub_critico','cliente_id':'cliente-fixture','cliente':'Fixture','dueno':'persona','personal':False,'pantallas':['captacion'],
 'que':'El coste por lead se ha disparado','porque':'Coste superior al umbral anterior','cifra':'99 €','umbral':'35 €','confianza':'alta','confianza_porque':'Dato del día y regla con fuente.',
 'criterio':{'id':'doc','texto':'Criterio RO antiguo','url':'https://example.test/documento'},'evidencia':[{'dato':'Contador previo','fecha':'2026-10-03','fuente':'Captación','url':'https://example.test/meta'}],
 'diagnostico':{'sintoma':'pocos_leads','causa':{'dato':'0 leads'}},'prioridad':{'puntos':190,'motivo':'Incumplimiento'},'orden':190,'gravedad':'rojo','accion':{'tipo':'avisar'},'metrica':{'valor':99,'mejor':'baja'}}
def funciones(*names):
 tree=ast.parse(Path(__file__).with_name('ia.py').read_text())
 return compile(ast.Module(body=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in names],type_ignores=[]),'ia.py:AST304','exec')
class Consejo304(unittest.TestCase):
 def test_all_exact_legacy_quantitative_types_neutral(self):
  for tipo in TIPOS:
   with self.subTest(tipo=tipo):
    out=gate(dict(BASE,tipo=tipo),HOY);self.assertEqual(out['confianza'],'media');self.assertIsNone(out['metrica']);self.assertIsNone(out['diagnostico']);self.assertEqual(out['gravedad'],'gris');self.assertIsNone(out['accion']);self.assertIn('Referencia anterior',out['porque']);self.assertEqual(out['criterio']['url'],BASE['criterio']['url']);self.assertEqual(out['evidencia'][0]['url'],BASE['evidencia'][0]['url']);self.assertIsNone(out['evidencia'][0]['fecha'])
 def test_global_generation_date_not_event_date(self):
  out=gate(BASE,HOY);self.assertIsNone(out['verificacion_304']['fecha_medicion']);self.assertEqual(out['evidencia'][0]['fecha_referencia'],HOY);self.assertFalse(out['verificacion_304']['evento_acreditado'])
 def test_bad_future_dates_not_rejuvenated(self):
  for d in ('2099-01-01','2026-02-30','2026-10-03 25:00',None):
   out=gate(dict(BASE,evidencia=[{'dato':'A','fecha':d}]),HOY);self.assertEqual(out['verificacion_304']['fechas_referencia'],[]);self.assertIsNone(out['evidencia'][0]['fecha_referencia'])
 def test_ticket_web_hours_stock_otherdept_preserved_even_same_client(self):
  for tipo in ('acc_correos','web_caida','prod_bloqueada','rrhh_no_imputa','crm_whatsapp','crm_sin_tocar','crm_citas_sin_estado','jefa_cartera_roja','paid_cpl_objetivo'):
   c=dict(BASE,tipo=tipo,diagnostico=None);self.assertEqual(gate(c,HOY),c)
 def test_cartera_requires_structured_exact_symptom(self):
  c=dict(BASE,tipo='jefa_cartera_roja',diagnostico={'sintoma':'relacion_en_riesgo'});self.assertEqual(gate(c,HOY),c)
  c['diagnostico']['sintoma']='leads_sin_citas';out=gate(c,HOY);self.assertEqual(out['gravedad'],'gris');self.assertEqual(gate(dict(out,que='Falsa orden IA',porque='Seguro incumple'),HOY)['que'],out['que'])
 def test_not_fuzzy_title_or_count(self):
  c=dict(BASE,tipo='acc_correos',que='CPL Meta sin leads',diagnostico=None);self.assertIs(gate(c,HOY),c)
 def test_input_immutable_and_idempotent(self):
  old=copy.deepcopy(BASE);out=gate(BASE,HOY);self.assertEqual(BASE,old);self.assertEqual(gate(out,HOY),out)
 def test_llm_rewrites_reconstructed_by_original_structured_reference(self):
  out=gate(BASE,HOY);llm={**out,'que':'¡Incumplimiento seguro!','porque':'Actúa ahora sin revisar','confianza':'alta','diagnostico':{'causa':{'dato':'False'}}}
  again=gate(llm,HOY);self.assertEqual(again['porque'],out['porque']);self.assertEqual(again['que'],out['que']);self.assertEqual(again['confianza'],'media')
 def entorno(self,base=None):
  P=types.SimpleNamespace(ver=lambda *a:{'ok':True},enlace_seguro=lambda x:True,puestos_de=lambda p:set(p['puestos']))
  S=types.SimpleNamespace(ve_alguno=lambda p,ms:True,P=P,E=types.SimpleNamespace(modulos={'captacion'},crudo={'clientes':[]}))
  MC=types.SimpleNamespace(ahora_madrid=lambda:datetime(2026,10,3),SIN_CONSEJO=set(),elegir=lambda cs,*a,**k:cs,retrasos=lambda *a:[])
  b={'S':S,'MC':MC,'normalizar_candidato_metodo308':normalizar_candidato_metodo308,'normalizar_consejo_cartera318':normalizar_consejo_cartera318,'leer_como':lambda *a:None,'neutralizar_consejo_horas':neutralizar_consejo_horas,'neutralizar_consejo_paid_crm':gate,'_explicable':lambda *a:a[-1],'limpiar':lambda x:x,'CUOTA_GLOBAL':{'direccion'},'recortar_dinero':lambda p,cp,cid,c:c,'TAPA_COBRO':'fixture-tapa',
   '_con_valoraciones':lambda p,r,x:x,'estado_para':lambda p:{'conectada':True,'motivo':None,'modelo':'fixture'},'candidatos_al_momento':lambda *a:[],'para_quien':lambda p,c:c,
   'candidatos_de':lambda *a:{'candidatos':[copy.deepcopy(base or BASE)],'generado':HOY},'_tabla_para':lambda *a:[],'_con_motivo':lambda x:x,'Denegado':RuntimeError,'MINUSCULA_INICIAL':set()}
  exec(funciones('_limpio_consejo','consejo'),b);return b
 def test_actual_API_cache_gate_after_permissions(self):
  b=self.entorno();p={'id':'persona','puestos':['direccion']};c=b['consejo'](p,p,{},'captacion')['consejos'][0];self.assertEqual(c['confianza'],'media');self.assertEqual(c['orden'],0)
  b['S'].P.ver=lambda *a:{'ok':False};self.assertEqual(b['consejo'](p,p,{},'captacion')['consejos'],[])
  b['S'].ve_alguno=lambda *a:False;self.assertIsNone(b['_limpio_consejo'](p,p,{},BASE))
 def test_actual_API_llm_cannot_restore_claim(self):
  b=self.entorno();b['_con_ia']=lambda *a:({'consejos':[{'ref':BASE['id'],'que':'Acelera ya','porque':'Incumplimiento seguro'}],'modelo':'fixture','generado':HOY},False);p={'id':'persona','puestos':['direccion']}
  c=b['consejo'](p,p,{},'captacion',con_ia=True)['consejos'][0];self.assertNotIn('Incumplimiento seguro',c['porque']);self.assertEqual(c['confianza'],'media')
 def test_actual_API_viewas_foreign_personal_denied(self):
  b=self.entorno(dict(BASE,personal=True));p={'id':'persona','puestos':['direccion']};r={'id':'other','puestos':['direccion']};b['_con_ia']=lambda *a:(_ for _ in ()).throw(AssertionError('No provider'))
  self.assertEqual(b['consejo'](r,p,{},'captacion',con_ia=True)['consejos'],[])
 def test_actual_live_enrich_gate(self):
  from fuentes_consejos import cerebro_decisiones as C
  with patch.object(C,'tipos',return_value={}),patch.object(C,'regla_de',return_value='doc'),patch.object(C,'criterio',return_value=BASE['criterio']),patch.object(C.PR,'puntuar',return_value={'puntos':190}),patch.object(C.PZ,'revisar',side_effect=lambda c,*a:(c,[])):
   out=C.enriquecer({'id':'persona','puestos':['direccion']},[dict(copy.deepcopy(BASE),diagnostico=None)],{'diagnosticos':{},'fechas':{'captacion':HOY}},completo=False)
  self.assertEqual(out[0]['confianza'],'media');self.assertEqual(out[0]['orden'],0);self.assertIsNone(out[0]['diagnostico'])
 def test_real_local_cache_shape_without_private_text_output(self):
  n=0
  for p in (Path(__file__).parent/'data'/'consejos').glob('p_*.json'):
   d=json.loads(p.read_text())
   for c in d.get('candidatos',[]):
    if c.get('tipo') in TIPOS:
     old=copy.deepcopy(c);out=gate(c,HOY);self.assertEqual(c,old);self.assertNotEqual(out['confianza'],'alta');self.assertEqual(out['id'],c['id']);n+=1
  self.assertGreater(n,0)
 def test_actual_valorar_no_legacy_ratio_learning(self):
  from fuentes_consejos import cerebro_decisiones as C
  b=self.entorno();record=[];b['S'].registrar=lambda *args:record.append(args);b['CD']=C;b['_verdad']=lambda cid:{'gravedad':'atencion'};b['re']=__import__('re');exec(funciones('valorar'),b)
  p={'id':'persona','puestos':['direccion']};r=b['valorar'](p,p,{}, {'consejo':BASE['id'],'valor':'util','pantalla':'captacion'})
  self.assertTrue(r['ok']);self.assertEqual(len(record),1);self.assertIsNone(record[0][-1]['metrica']['valor']);self.assertIsNone(record[0][-1]['puntos']);self.assertEqual(record[0][-1]['regla'],'doc')
 def test_actual_valorar_otherdept_preserved_and_permission_revoked(self):
  from fuentes_consejos import cerebro_decisiones as C
  base=dict(BASE,tipo='acc_correos',diagnostico=None,cifra='3 correos',metrica={'valor':3,'mejor':'baja'})
  b=self.entorno(base);record=[];b['S'].registrar=lambda *args:record.append(args);b['CD']=C;b['_verdad']=lambda cid:{'gravedad':'atencion'};b['re']=__import__('re');exec(funciones('valorar'),b);p={'id':'persona','puestos':['direccion']}
  b['valorar'](p,p,{}, {'consejo':BASE['id'],'valor':'util'});self.assertEqual(record[0][-1]['metrica']['valor'],3)
  b['S'].P.ver=lambda *a:{'ok':False}
  with self.assertRaises(RuntimeError):b['valorar'](p,p,{}, {'consejo':BASE['id'],'valor':'util'})
  self.assertEqual(len(record),1)
 def test_valorar_viewas_denies_before_record(self):
  b=self.entorno();b['re']=__import__('re');exec(funciones('valorar'),b);p={'id':'persona','puestos':['direccion']};r={'id':'other','puestos':['direccion']};b['S'].registrar=lambda *args:(_ for _ in ()).throw(AssertionError('No record'))
  with self.assertRaises(RuntimeError):b['valorar'](r,p,{}, {'consejo':BASE['id'],'valor':'util'})
if __name__=='__main__':unittest.main()
