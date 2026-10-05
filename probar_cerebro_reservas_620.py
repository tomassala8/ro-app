import copy
import unittest
import ast
from pathlib import Path
from datetime import datetime,timezone
from cerebro_reservas_620 import enriquecer_reservas620, ETAPAS, LIMITES, CRITERIO

HOY='2026-10-04'; AHORA='2026-10-04T10:00:00Z'
DESDE='2026-09-03T04:01:00Z';HASTA=CORTE='2026-10-03T04:01:00Z'
def dto(n=10,citas=3,evento_citas=8):
 es={k:{'observados':n if k=='recibido' else citas if k=='cita' else 0,'estado':'parcial' if (n if k=='recibido' else citas if k=='cita' else 0) else 'desconocido'} for k in ETAPAS}
 pe={k:{'eventos_observados':n if k=='recibido' else evento_citas if k=='cita' else 0,'leads_unicos_observados':n if k=='recibido' else min(evento_citas,5) if k=='cita' else 0,'estado':'parcial' if (n if k=='recibido' else evento_citas if k=='cita' else 0) else 'desconocido'} for k in ETAPAS}
 return {'version':'467.1','estado':'copia_observada','cliente_id':'cliente','diagnosticos':{},'hora_fuente':CORTE,'desde':DESDE,'hasta':HASTA,'corte':CORTE,
  'medicion':{'version':'467.1','cohorte':{'recibidos_observados':n,'estado':'parcial' if n else 'desconocido','etapas':es},'eventos_periodo':pe,'observado_hasta':CORTE,'ventana_recepcion':{'desde':DESDE,'hasta':HASTA},'ventana_eventos':{'desde':DESDE,'hasta':HASTA},'zona':'UTC','limites':list(LIMITES)}}
def result():
 return {'version':1,'recomendaciones':[{'cliente_id':'cliente','regla_id':'crm_citas_sin_estado','criterio_entrega':'Pendiente de comprobar resultado comercial.','evidencias':[{'fuente':'crm','texto':'Legacy parcial'}],'prioridad':1,'responsable_id':'owner','score':None},
  {'cliente_id':'cliente','regla_id':'crm_primera_hora','criterio_entrega':'Otro criterio','evidencias':[]}]}
def run(d=None,r=None,**opts):return enriquecer_reservas620(result() if r is None else r,{'cliente':dto() if d is None else d},opts.pop('hoy',HOY),**{'ahora':AHORA,**opts})
class Tests(unittest.TestCase):
 def no_change(self,d,**opts):self.assertEqual(run(d,**opts),result())
 def test_positivo_recomendacionexistente_y_no_mutar(self):
  r=result();d=dto();before=copy.deepcopy((r,d));out=run(d,r);self.assertEqual((r,d),before);self.assertEqual(out['recomendaciones'][1],r['recomendaciones'][1]);e=out['recomendaciones'][0]['evidencias'][-1];self.assertEqual(e['fuente'],'crm_embudo_observado');self.assertEqual(e['fecha'],CORTE);self.assertEqual(e['periodo'],[DESDE,HASTA]);self.assertEqual(e['vigencia'],'actual');self.assertIn('10 recibidos',e['texto']);self.assertIn('3 reservas',e['texto']);self.assertNotIn('8 reservas',e['texto']);self.assertIn('incluidas canceladas o con fecha futura',e['texto']);self.assertIn('no acreditan asistencia, ventas',e['texto']);self.assertEqual(out['recomendaciones'][0]['prioridad'],1);self.assertIsNone(out['recomendaciones'][0]['score'])
 def test_idempotente(self):
  r=run();self.assertEqual(run(r=r),r);self.assertEqual(r['recomendaciones'][0]['criterio_entrega'].count(CRITERIO),1)
 def test_recibido_sin_reserva_unknown_noausencia(self):
  r=run(dto(citas=0));self.assertIn('dato desconocido, no ausencia',r['recomendaciones'][0]['evidencias'][-1]['texto']);self.assertNotIn('0 reservas',r['recomendaciones'][0]['evidencias'][-1]['texto'])
 def test_ambos0_sin_observacion_skip(self):self.no_change(dto(n=0,citas=0,evento_citas=0))
 def test_ningunareco_nuevas(self):
  r={'recomendaciones':[]};self.assertEqual(run(r=r),r);r=result();r['recomendaciones'][0]['regla_id']='paid_cpl';self.assertEqual(run(r=r),r)
 def test_noreloj_y_madrid(self):
  self.no_change(dto(),ahora=None);self.no_change(dto(),ahora='2026-10-03T22:30:00Z',hoy='2026-10-03');self.no_change(dto(),hoy='2026-10-31',ahora='invalid')
 def test_futuro_mismo_dia(self):
  d=dto();d['corte']='2026-10-04T11:00:00Z';d['medicion']['observado_hasta']=d['corte'];self.no_change(d)
 def test_fuente_posterior_corte(self):
  d=dto();d['hora_fuente']='2026-10-03T05:00:00Z';self.no_change(d)
 def test_viejo_ambos_sellos(self):
  d=dto();d['hora_fuente']='2026-10-01T12:00:00Z';self.no_change(d)
  self.no_change(dto(),hoy='2026-10-07',ahora='2026-10-07T10:00:00Z')
 def test_offsets_invalidos_naive_y_fecha(self):
  for stamp in ['2026-10-03T04:01:00+02:99','2026-10-03T04:01:00+14:01','2026-10-03T04:01:00','2026-09-31T04:01:00Z','2026-10-03T25:01:00Z',True]:
   d=dto();d['hora_fuente']=stamp;self.no_change(d)
 def test_cliente_version_flags_extra(self):
  for k,v in [('cliente_id','otro'),('version','466.1'),('estado','sin_configurar'),('estado','error'),('token','PRIVATE')]:
   d=dto();d[k]=v;self.no_change(d)
 def test_cohorte_counts_estados_types(self):
  for n in [True,1.5,-1,None,float('nan'),2**54]:
   d=dto();d['medicion']['cohorte']['recibidos_observados']=n;self.no_change(d)
  for change in [lambda d:d['medicion']['cohorte'].update(estado='completo'),lambda d:d['medicion']['cohorte']['etapas']['cita'].update(observados=11),lambda d:d['medicion']['cohorte']['etapas']['cita'].update(estado='completo'),lambda d:d['medicion']['cohorte']['etapas']['cita'].update(tasa=30)]:
   d=dto();change(d);self.no_change(d)
 def test_no_instrumentadas_ni_tasas(self):
  for k in ['cualificado','contacto','respuesta','asistencia','venta']:
   d=dto();d['medicion']['cohorte']['etapas'][k]={'observados':1,'estado':'parcial'};self.no_change(d)
   d=dto();d['medicion']['eventos_periodo'][k]={'eventos_observados':1,'leads_unicos_observados':1,'estado':'parcial'};self.no_change(d)
 def test_ventanas_no_mezclar(self):
  for change in [lambda d:d['medicion']['ventana_eventos'].update(desde='2026-09-04T04:01:00Z'),lambda d:d.update(hasta='2026-10-03T05:00:00Z'),lambda d:d['medicion'].update(observado_hasta='2026-10-03T05:00:00Z'),lambda d:d['medicion'].update(zona='Europe/Madrid')]:
   d=dto();change(d);self.no_change(d)
 def test_diag_y_limites_no_textoprivado(self):
  d=dto();d['diagnosticos']={'email_PRIVATE':1};self.no_change(d)
  d=dto();d['medicion']['limites']=['PRIVATE'];self.no_change(d)
 def test_error_fuente_declarado_skip(self):
  d=dto();d['diagnosticos']={'fuente_reporta_errores':1};self.no_change(d)
 def test_limite_2dias_madrid_y_mismo_dia_corte(self):
  self.assertEqual(len(run(hoy='2026-10-05',ahora='2026-10-05T10:00:00Z')['recomendaciones'][0]['evidencias']),2)
  d=dto();d['corte']='2026-10-04T11:00:00+02:00';d['medicion']['observado_hasta']=d['corte'];self.assertEqual(len(run(d)['recomendaciones'][0]['evidencias']),2)
 def test_eventos_periodo_otra_universo_valido(self):
  d=dto(evento_citas=100);out=run(d);e=out['recomendaciones'][0]['evidencias'][-1];self.assertIn('3 reservas',e['texto']);self.assertNotIn('100',e['texto'])
 def test_fuente_sinconfig_y_resultadomalformado(self):
  self.assertEqual(enriquecer_reservas620(result(),{},HOY,AHORA),result());self.assertEqual(enriquecer_reservas620(None,{},HOY,AHORA),None)
 def test_publico_matches_medicion_real467(self):
  # AST puro: valida puente de forma pública primaria467 sin importarla ni sus lectores.
  tree=ast.parse(Path('crm_embudo_api_467.py').read_text());nodes=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in {'_n','_instante','_diagnosticos','_medicion'}]
  ns={'re':__import__('re'),'datetime':datetime,'timezone':timezone,'ETAPAS':ETAPAS,'VERSION':'467.1','LIMITES':tuple(LIMITES),'DIAGNOSTICOS':set(),'INCIDENCIAS_MOTOR':set()};exec(compile(ast.Module(body=nodes,type_ignores=[]),'467fixture','exec'),ns)
  public=dto()['medicion'];co=copy.deepcopy(public['cohorte']);co['etapas']={k:{**v,'valor':None,'denominador_recibidos':None,'tasa_sobre_recibidos':None} for k,v in co['etapas'].items()}
  raw={'version':1,'ventana_recepcion':public['ventana_recepcion'],'ventana_eventos':public['ventana_eventos'],'observado_hasta':CORTE,'zona':'UTC','grupos':[{'cliente_id':'cliente','source':'ghl','cualificacion':{'criterios_observados':[],'criterio_comparable':False},'cohorte':co,'eventos_periodo':public['eventos_periodo']}],'incidencias':{},'limites':list(LIMITES)}
  self.assertEqual(ns['_medicion'](raw,'cliente',DESDE,HASTA,CORTE),public)
if __name__=='__main__':unittest.main()
