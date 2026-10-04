"""Recuento canónico y consumidores reales por AST, sin bootstrap/proveedor/BD."""
import copy,unittest,types
import json
from pathlib import Path
from unittest.mock import patch
import consejos_cartera_318 as C
import permisos as PER
import probar_consejos_paid_crm_304 as F304
HOY='2026-10-03'
BASE={'id':'op:criticos','tipo':C.TIPO,'dueno':'ops','pantallas':['mi-dia','en-rojo'],'requiere':['en-rojo'],'personal':False,'cliente_id':None,'cifra':'11 clientes críticos','que':'Hay11 críticos','porque':'CUOTA_GLOBAL_NO_SALIR','cuota_total':987654,'confianza':'alta','orden':265,'criterio':{'texto':'Doctrina antigua'},'evidencia':[{'dato':'NO_RAW','fecha':HOY}]}
def doc(n=9):return {'generado':HOY,'clientes':[{'cliente_id':'c'+str(i),'gravedad':'critico','nombre':'NO_NAME','cuota':123456} for i in range(n)],'cuota_empresa':654321}
def entorno(n=9):
 ps=[{'id':'ops','estado':'activo','puestos':['operaciones']},{'id':'dir','estado':'activo','puestos':['direccion']}]
 raw={'personas':ps,'clientes':[{'id':'c'+str(i)} for i in range(n)]}
 S=types.SimpleNamespace(E=types.SimpleNamespace(nucleo_bloqueado=False,crudo=raw,modulos={'mi-dia','en-rojo'}),ACT=types.SimpleNamespace(es_activo_id=lambda cid:True),P=types.SimpleNamespace(hoy_iso=lambda:HOY,contexto=lambda *a:{},ver=lambda *a:{'ok':True},enlace_seguro=lambda *a:True,puestos_de=lambda p:set(p['puestos'])),ve_alguno=lambda *a:True)
 S.P.sin_importes=PER.sin_importes;S.P.importes_a_quitar=PER.importes_a_quitar
 return S,ps[0],ps[1]
class Cartera318(unittest.TestCase):
 def test_cached11_current9_noquota_or_name(self):
  old=copy.deepcopy(BASE);v=doc();out=C.normalizar_agregado318(BASE,v,['c'+str(i) for i in range(9)],HOY)
  self.assertEqual(out['cifra'],'9 clientes críticos observados');self.assertTrue(out['verificacion_318']['actual']);self.assertNotIn('CUOTA_GLOBAL',str(out));self.assertNotIn('987654',str(out));self.assertNotIn('123456',str(out));self.assertNotIn('NO_NAME',str(out));self.assertEqual(BASE,old)
 def test_incomplete_duplicate_unknown_gravity_dates_neutral(self):
  for mode in ('missing','duplicate','gravity','stale','future','datebad'):
   d=doc(2)
   if mode=='missing':d['clientes'].pop()
   if mode=='duplicate':d['clientes'].append(d['clientes'][0])
   if mode=='gravity':d['clientes'][0]['gravedad']='verde'
   if mode in ('stale','future','datebad'):d['generado']={'stale':'2026-10-02','future':'2026-10-04','datebad':'2026-02-30'}[mode]
   out=C.normalizar_agregado318(BASE,d,['c0','c1'],HOY);self.assertFalse(out['verificacion_318']['actual']);self.assertIsNone(out['metrica']);self.assertEqual(out['gravedad'],'gris');self.assertNotIn('11',out['que'])
 def test_zero_scope_not_global_success(self):
  d=doc(1);d['clientes'][0]['gravedad']='bien';out=C.normalizar_agregado318(BASE,d,['c0'],HOY);self.assertEqual(out['metrica']['valor'],0);self.assertEqual(out['gravedad'],'gris');self.assertNotIn('verde',out['que'])
 def test_unrelated_candidate_unchanged(self):
  b={'tipo':'web_caida'};self.assertIs(C.normalizar_consejo_cartera318(b,None,None,None,None),b)
 def test_identity_roles_modules_owner_read_scope(self):
  for mode in ('inactive','duplicate','role','module','owner','viewas'):
   S,p,r=entorno()
   if mode=='inactive':p['estado']='baja'
   if mode=='duplicate':S.E.crudo['personas'].append(copy.deepcopy(p))
   if mode=='role':p['puestos']=['account']
   if mode=='module':S.ve_alguno=lambda *a:False
   b=copy.deepcopy(BASE)
   if mode=='owner':b['dueno']='other'
   if mode=='viewas':S.P.ver=lambda p,d,c:{'ok':d['tipo']!='ver_como'};real=r
   else:real=p
   reads=[];out=C.normalizar_consejo_cartera318(b,S,real,p,lambda *a:reads.append(a) or doc());self.assertIsNone(out);self.assertEqual(reads,[])
 def test_inactive_foreign_and_duplicate_clients_excluded(self):
  S,p,r=entorno();S.ACT.es_activo_id=lambda cid:cid!='c0';S.P.ver=lambda p,d,c:{'ok':d.get('cliente_id')!='c1'};S.E.crudo['clientes'].append({'id':'c2'})
  out=C.normalizar_consejo_cartera318(BASE,S,p,p,lambda *a:doc());self.assertEqual(out['metrica']['valor'],6)
 def test_revocation_after_read_no_count(self):
  S,p,r=entorno()
  def reader(*a):p['estado']='baja';return doc()
  self.assertIsNone(C.normalizar_consejo_cartera318(BASE,S,p,p,reader))
 def test_viewas_scoped_no_financial_extras(self):
  S,p,r=entorno();S.P.ver=lambda actor,d,c:{'ok':d['tipo']=='ver_como' or d.get('cliente_id') in ('c0','c1')};out=C.normalizar_consejo_cartera318(BASE,S,r,p,lambda *a:doc());self.assertEqual(out['metrica']['valor'],2);self.assertNotIn('cuota',out);self.assertNotIn('NO_NAME',str(out))
 def test_actual_cache_and_LLM_paths(self):
  for llm in (False,True):
   S,p,_=entorno();b=F304.Consejo304().entorno(BASE);b.update(S=S,leer_como=lambda *a:doc(),normalizar_consejo_cartera318=C.normalizar_consejo_cartera318)
   b['_con_ia']=lambda *a:({'consejos':[{'ref':BASE['id'],'que':'Hay11 y paga987654','porque':'Total global'}]},False)
   out=b['consejo'](p,p,{},'mi-dia',con_ia=llm)['consejos'][0];self.assertEqual(out['cifra'],'9 clientes críticos observados');self.assertNotIn('987654',str(out));self.assertNotIn('Hay11',out['que']);self.assertEqual(out['confianza'],'media')
 def test_actual_local_source_shape_ACT_and_no_mutation(self):
  from fuentes_verdad import clientes_activos as ACT
  path=Path(__file__).parent/'data'/'verdad'/'clientes.json';antes=path.read_bytes();d=json.loads(antes)
  clientes=json.loads((Path(__file__).parent/'data'/'clientes.json').read_text());ids=[c['id'] for c in clientes if ACT.es_activo_id(c['id']) is True]
  out=C.normalizar_agregado318(BASE,d,ids,HOY);esperado=sum(r.get('gravedad')=='critico' for r in d['clientes'] if r['cliente_id'] in ids)
  self.assertEqual(out['metrica']['valor'],esperado);self.assertNotIn('cuota_total',out);self.assertEqual(path.read_bytes(),antes)
if __name__=='__main__':unittest.main()
