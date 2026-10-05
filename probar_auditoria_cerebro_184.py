"""Regresiones puras184, sin proveedor/DB/fuentes personales."""
import copy,unittest
from types import SimpleNamespace
from cerebro_operativo import generar
from cerebro_api import responsables_actuales
from probar_cerebro_operativo import documentos,HOY
import permisos as P
class Pruebas(unittest.TestCase):
 def reglas(self,r):return {x['regla_id'] for x in r['recomendaciones']}
 def test_lectura_ghl_no_rejuvenece_medicion_antigua_ni_null(self):
  for hasta in ('2026-08-01',None):
   a,c,o=documentos();c.update(datos_hasta=hasta,fuentes={'ghl':{'hora':HOY,'estado':'bien'}});c['subcuentas'][0]['velocidad']={'en_1h':0,'juzgables':5}
   r=generar(a,c,o,HOY);self.assertEqual(r['cobertura']['fuentes']['crm']['estado'],'sin_vigencia');self.assertNotIn('crm_primera_hora',self.reglas(r))
 def test_objetivo_expresamente_no_confirmado_no_se_describe_acordado(self):
  for extra in ({'confirmado':False},{'estado':'propuesta'},{'confirmado':True,'estado':'pendiente'}):
   a,c,o=documentos();a['clientes'][0]['cpl_resumen']={'ref':100,'fiable':True,'ref_base':'7d'};o['clientes']=[{'cliente_id':'fixture','objetivo':{'cpl_objetivo':40,'periodo':'2026-10',**extra}}]
   self.assertNotIn('paid_cpl_objetivo',self.reglas(generar(a,c,o,HOY)))
 def test_legado_referencia_sin_aprobacion_inventada_y_confirmado(self):
  a,c,o=documentos();a['clientes'][0]['cpl_resumen']={'ref':100,'fiable':True,'ref_base':'7d'};o['clientes']=[{'cliente_id':'fixture','objetivo':{'cpl_objetivo':40}}]
  # Una referencia legacy no acredita medición ni aprobación comercial.
  self.assertNotIn('paid_cpl_objetivo',self.reglas(generar(a,c,o,HOY)))
  o['clientes'][0]['objetivo']['confirmado']=True
  self.assertNotIn('paid_cpl_objetivo',self.reglas(generar(a,c,o,HOY)))
  from probar_cerebro_operativo import acreditar_paid331
  from paid_mediciones_331 import ventana
  # Serie220 íntegra y semana cerrada: 4 eventos lead observados /400EUR.
  # La primera semana completa de octubre termina el7; no mezclar septiembre.
  hoy='2026-10-08';periodo=['2026-10-01','2026-10-07']
  a.update(generado=hoy,datos_hasta=periodo[1],ventanas={'7d':periodo})
  c['generado']=hoy;o['generado']=hoy
  k=a['clientes'][0];k.update(leads={'7d':4},gasto={'7d':400})
  k['cpl_resumen']={'ref':1,'fiable':False,'ref_base':'legacy'}
  acreditar_paid331(a)
  for fila in k['serie']:fila['medicion']['fecha_lectura']=hoy+' 01:00'
  o['clientes'][0]['objetivo'].update(periodo='2026-10')
  medida=ventana(k,periodo,hoy)
  self.assertEqual((medida['leads'],medida['gasto'],medida['tipo_evento']),(4,400,'lead'))
  r=next(x for x in generar(a,c,o,hoy)['recomendaciones'] if x['regla_id']=='paid_cpl_objetivo')
  self.assertIn('acordado',r['titulo']);self.assertEqual(r['certeza'],'señal')
  self.assertEqual(r['evidencias'][0]['periodo'],periodo)
  # Igual medición y objetivo mensual sin aprobación siguen sin recomendar.
  o['clientes'][0]['objetivo'].pop('confirmado')
  self.assertNotIn('paid_cpl_objetivo',self.reglas(generar(a,c,o,hoy)))
  o['clientes'][0]['objetivo']['confirmado']=True
  # Medición válida, pero semana cruzada entre septiembre/octubre: no comparar
  # su CPL con el objetivo mensual de octubre.
  a.update(generado=HOY,datos_hasta='2026-10-02',ventanas={'7d':['2026-09-26','2026-10-02']})
  c['generado']=HOY;o['generado']=HOY;acreditar_paid331(a)
  medida=ventana(k,a['ventanas']['7d'],HOY)
  self.assertEqual((medida['leads'],medida['gasto']),(4,400))
  self.assertNotIn('paid_cpl_objetivo',self.reglas(generar(a,c,o,HOY)))
 def owner(self,*,baja=False,duplicado=False,asignado=True,vista_denegada=False,act=True):
  actor={'id':'dir','puestos':['direccion'],'estado':'activo'};p={'id':'paid','puestos':['trafficker'],'estado':'baja' if baja else 'activo'}
  cliente={'id':'fixture','servicios':{'publicidad':'sí'}}
  raw={'personas':[actor,p]+([copy.deepcopy(p)] if duplicado else []),'clientes':[cliente],'asignaciones':[{'persona_id':'paid','cliente_id':'fixture','silla':'trafficker'}] if asignado else []}
  vista=actor
  if vista_denegada:
   vista={'id':'account','puestos':['account'],'estado':'activo'};raw['personas'].append(vista)
  S=SimpleNamespace(E=SimpleNamespace(crudo=raw),P=P,ACT=SimpleNamespace(es_activo_id=lambda cid:act))
  rec={'cliente_id':'fixture','responsable_id':'paid','responsable_role':'trafficker'}
  return responsables_actuales(S,{'recomendaciones':[rec]},actor,vista)['recomendaciones'][0]
 def test_owner_actual_exacto(self):self.assertEqual(self.owner()['responsable_id'],'paid')
 def test_owner_inactivo_ambiguo_sin_silla_act_o_vista(self):
  for kw in ({'baja':True},{'duplicado':True},{'asignado':False},{'vista_denegada':True},{'act':False}):
   r=self.owner(**kw);self.assertIsNone(r['responsable_id']);self.assertEqual(r['responsable_estado'],'asignacion_pendiente')
if __name__=='__main__':unittest.main()
