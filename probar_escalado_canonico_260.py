import ast,copy,json,types,unittest
from datetime import datetime,timedelta
from pathlib import Path
from unittest.mock import patch,Mock
import escalado as E
A=Path(__file__).parent

def person(id,role='seo',**kw):return {'id':id,'estado':'activo','puestos':[role],**kw}
def rows():return [person('owner',jefe='head'),person('head','jefa_seo'),person('mili','operaciones'),person('constanza','proyectos'),person('agustina','tecnico_altas'),person('tomas','direccion')]
class Cadenas(unittest.TestCase):
 def setUp(self):
  self.cfg=copy.deepcopy(E.POR_DEFECTO);self.patch=patch.object(E,'config',lambda:self.cfg);self.patch.start();self.addCleanup(self.patch.stop)
  self.deps=patch.object(E,'_departamentos',lambda:{'seo':{'jefe':'head'}});self.deps.start();self.addCleanup(self.deps.stop)
 def test_normal_y_excepcion_direccion(self):
  self.assertEqual(E.cadena_alertas('seo','owner','head',rows()),['owner','head','mili','tomas'])
  self.assertEqual(E.cadena_alertas('rrhh','owner','tomas',rows()),['owner','tomas'])
  self.assertEqual(E.a_quien('estrategia','owner',rows())['para'],'head')
 def test_no_inactivo_ni_duplicado_ni_estado_ausente(self):
  for cambio in [{'estado':'baja'},{'estado':None},{'activo':False}]:
   ps=[{**p,**cambio} if p['id']=='head' else p for p in rows()]
   self.assertNotIn('head',E.cadena_alertas('seo','owner','head',ps));self.assertEqual(E.jefe_de('owner',ps),'mili')
  self.assertNotIn('head',E.cadena_alertas('seo','owner','head',rows()+[person('head')]))
 def test_actor_revocado_o_ambiguo_sin_ruta(self):
  for ps in [rows()+[person('owner')],[p for p in rows() if p['id']!='owner'],[{**p,'estado':'baja'} if p['id']=='owner' else p for p in rows()]]:
   self.assertEqual(E.cadena_alertas('seo','owner','head',ps),[]);self.assertIsNone(E.a_quien('operaciones','owner',ps));self.assertIsNone(E.jefe_de('owner',ps))
 def test_no_salto_tomas_por_faltar_mili(self):
  for ps in [[p for p in rows() if p['id']!='mili'],rows()+[person('mili','operaciones')]]:
   self.assertEqual(E.cadena_alertas('seo','owner','head',ps),['owner','head']);self.assertIsNone(E.jefe_de('agustina',ps));self.assertIsNone(E.a_quien('operaciones','owner',ps))
 def test_final_tomas_nominal_direccion_y_siguiente_actual(self):
  for ps in [[p for p in rows() if p['id']!='tomas'],[{**p,'puestos':['seo']} if p['id']=='tomas' else p for p in rows()],rows()+[person('tomas','direccion')]]:
   self.assertIsNone(E.papel('final',ps));self.assertNotIn('tomas',E.cadena_alertas('seo','owner','head',ps));self.assertIsNone(E.a_quien('atascado','owner',ps)['siguiente'])
  self.cfg['personas']['final']='other';self.assertIsNone(E.papel('final',rows()+[person('other','direccion')]))
 def test_self_mili_si_tomas_valido_sin_repetidos(self):
  r=E.a_quien('operaciones','mili',rows());self.assertEqual(r['para'],'tomas');self.assertIsNone(r['siguiente'])
  self.assertEqual(E.cadena_alertas('seo','mili','mili',rows()),['mili','tomas'])
 def test_descriptores_usando_misma_fuente(self):
  ps=[p for p in rows() if p['id']!='mili']
  with patch.object(E,'_personas_por_id',wraps=E._personas_por_id):
   summary=E.resumen(ps);self.assertIsNone(next(x for x in summary if x['id']=='operaciones')['a_nombre'])
  self.assertFalse(E.activa({'id':'missingstate'}));self.assertEqual(E._personas_por_id({}),{})

class Consumidores(unittest.TestCase):
 def test_generador_cadena_vacia_no_500_ni_fallback_owner(self):
  tree=ast.parse((A/'fuentes_alertas/generar_alertas.py').read_text());functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['aplicar_estados','hechos']]
  alerta={'id':'fixture','dueno_id':'inactive','escalado_cadena':[],'plazo_h':24,'gravedad':'rojo'}
  now=datetime(2026,10,3,12);ns={'ALERTAS':[alerta],'AHORA':now,'timedelta':timedelta,'fecha':lambda x:datetime.fromisoformat(x) if x else None,'f2s':lambda x:x.isoformat(),'ESTADOS_ACCION':{},'RECHAZADAS':[]}
  exec(compile(ast.Module(body=functions,type_ignores=[]),'generator-fixture','exec'),ns)
  ns['aplicar_estados']({},{});self.assertIsNone(alerta['responsable_ahora']);self.assertEqual(alerta['escalado']['nivel'],0);self.assertIsNone(ns['hechos'](alerta)['responsable'])
 def test_subir_persistido_revocado_no_publicacion(self):
  tree=ast.parse((A/'avisos.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='escalar')
  payload={'tipo':'atascado','de':'owner','para':'mili','siguiente':'tomas'}
  row={'id':1,'canal_id':'direct-fixture','datos':json.dumps({'escalado':payload})};con=types.SimpleNamespace(execute=lambda *args:types.SimpleNamespace(fetchone=lambda:row))
  publish=Mock(side_effect=AssertionError('No publicar'))
  ps=rows();cfg=copy.deepcopy(E.POR_DEFECTO)
  ns={'json':json,'ESC':E,'personas':lambda:ps,'fin':lambda code,body:(code,body),'publicar':publish}
  exec(compile(ast.Module(body=[fn],type_ignores=[]),'avisos-fixture','exec'),ns)
  with patch.object(E,'config',lambda:cfg):
   for changes in [{'estado':'baja'},{'activo':False},{'puestos':['seo']}]:
    ps[:]=[{**p,**changes} if p['id']=='tomas' else p for p in rows()]
    self.assertEqual(ns['escalar'](types.SimpleNamespace(canales={'direct-fixture'}),person('mili','operaciones'),{'subir_de':1},con,[])[0],409)
   ps[:]=rows()+[person('tomas','direccion')]
   self.assertEqual(ns['escalar'](types.SimpleNamespace(canales={'direct-fixture'}),person('mili','operaciones'),{'subir_de':1},con,[])[0],409)
  publish.assert_not_called()
 def test_subir_valido_publicacion_simulada_y_cadena_unica(self):
  tree=ast.parse((A/'avisos.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='escalar')
  row={'id':1,'canal_id':'direct-fixture','datos':json.dumps({'escalado':{'tipo':'atascado','de':'owner','para':'mili','siguiente':'tomas','que':'Fixture'}})}
  cursor=Mock();cursor.fetchone.side_effect=[row,None];con=types.SimpleNamespace(execute=lambda *a:cursor)
  publisher=Mock(return_value=42);cfg=copy.deepcopy(E.POR_DEFECTO);rastro=[]
  ns={'json':json,'ESC':E,'personas':rows,'fin':lambda c,b:(c,b),'publicar':publisher,'corto':lambda id:id,'limpiar':lambda t,n:t,'habla_de_sueldo':lambda t:False,'id_directo':lambda a,b:'direct-fixture-new'}
  exec(compile(ast.Module(body=[fn],type_ignores=[]),'valid-escalation-fixture','exec'),ns)
  with patch.object(E,'config',lambda:cfg):
   code,body=ns['escalar'](types.SimpleNamespace(canales={'direct-fixture'}),person('mili','operaciones'),{'subir_de':1},con,rastro)
  self.assertEqual(code,200);self.assertEqual(body['para'],'tomas');self.assertEqual(publisher.call_count,2);self.assertEqual(len(rastro),1)

if __name__=='__main__':unittest.main()
