"""Endpoint fixtures: ningún fichero real, red, BD o proveedor."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import borradores_api as A

R={'cliente_id':'mio','regla_id':'revisar_crm','titulo':'Revisar CRM','motivo':'Estado por contrastar',
   'accion':'Revisar el resultado registrado.','criterio_entrega':'Evidencia del resultado y siguiente paso.',
   'responsable_id':'empleado','evidencias':[{'fuente':'CRM','fecha':'2026-10-03','texto':'2 intentos.'}],
   'importe':1470,'contrato':'TEXTO_PRIVADO_NO_SALIR','contacto':'no@example.test'}

class Base:
 def _api_get(self,*a):return 'anterior'
 def responder(self,code,body):return code,body

class Prueba(unittest.TestCase):
 def setUp(self):
  self.permisos=[]
  def ver(p,dato,ctx):
   self.permisos.append((p['id'],dato['cliente_id']))
   return {'ok':dato['cliente_id'] in p.get('clientes',[])}
  self.S=SimpleNamespace(AQUI='/fixture-no-leer',E=SimpleNamespace(nucleo_bloqueado=False,crudo={
    'clientes':[{'id':'mio','nombre':'Cliente sintético','importe':1470},{'id':'baja','nombre':'Baja','estado':'baja'}],
    'personas':[],'asignaciones':[]}),P=SimpleNamespace(contexto=lambda *a:{},ver=ver,hoy_iso=lambda:'2026-10-03'),
    ACT=SimpleNamespace(es_baja_id=lambda cid:False),ve_alguno=lambda p,mods:bool(set(mods)&set(p['modulos'])))
  self.real={'id':'real','modulos':['prioridades-cliente','crm'],'clientes':['mio','baja']}
  self.vista={'id':'vista','modulos':['prioridades-cliente','crm'],'clientes':['mio','baja']}
  self.q={'cliente_id':['mio'],'regla_id':['revisar_crm']}
  class H(Base):pass
  A.enganchar(H,self.S);self.h=H()
  self.read=patch.object(A,'leer_fuentes',return_value=[None,{'autorizado':'fixture'},None]);self.fread=self.read.start()
  self.motor=patch.object(A,'generar_operativo',return_value={'recomendaciones':[R]});self.fmotor=self.motor.start()
  self.metodo=patch.object(A.metodo_cuentas,'estado_operativo',return_value={'sugerencias':[]});self.fmetodo=self.metodo.start()
  self.seo=patch.object(A.cerebro_seo_api,'generar',return_value={'recomendaciones':[]});self.fseo=self.seo.start()
  self.addCleanup(patch.stopall)
 def consultar(self,q=None):return self.h._api_get('/api/cerebro/borrador',self.q if q is None else q,self.real,self.vista)
 def test_real_borrador_pendiente_mappings_no_error(self):
  code,d=self.consultar();self.assertEqual(code,200)
  self.assertFalse(d['enviable']);self.assertIsNone(d['lista_id']);self.assertNotIn('assignees',d['payload'])
  self.assertFalse(d['listo_para_revision']);self.assertEqual(d['estado'],'borrador')
  self.assertNotIn('1470',str(d));self.assertNotIn('TEXTO_PRIVADO_NO_SALIR',str(d));self.assertNotIn('no@example',str(d))
  self.assertEqual(self.permisos,[('real','mio'),('vista','mio')]);self.fseo.assert_not_called()
 def test_bloqueado_antes_de_fuentes(self):
  self.S.E.nucleo_bloqueado=True;self.assertEqual(self.consultar()[0],503);self.fread.assert_not_called()
 def test_ambas_identidades_prioridades(self):
  for p in (self.real,self.vista):
   original=p['modulos'];p['modulos']=['crm'];self.assertEqual(self.consultar()[0],403);p['modulos']=original
  self.fread.assert_not_called()
 def test_cartera_ambas_identidades(self):
  for p in (self.real,self.vista):
   original=p['clientes'];p['clientes']=[];self.assertEqual(self.consultar()[0],404);p['clientes']=original
  self.fread.assert_not_called()
 def test_invisible_desconocido_mismo404(self):
  self.vista['clientes']=[];a=self.consultar()
  b=self.consultar({'cliente_id':['otro'],'regla_id':['revisar_crm']})
  self.assertEqual(a,b);self.fread.assert_not_called()
 def test_baja_no_fuentes(self):
  self.assertEqual(self.consultar({'cliente_id':['baja'],'regla_id':['revisar_crm']})[0],404)
  self.fread.assert_not_called()
 def test_baja_canonical_no_fuentes(self):
  self.S.ACT.es_baja_id=lambda cid:True
  self.assertEqual(self.consultar()[0],404);self.fread.assert_not_called()
 def test_id_duplicado_nucleo(self):
  self.S.E.crudo['clientes'].append({'id':'mio'})
  self.assertEqual(self.consultar()[0],404);self.fread.assert_not_called()
 def test_parametros_exactos_no_clientbody(self):
  for q in [{**self.q,'payload':['{}']},{**self.q,'lista_id':['123']},
            {**self.q,'cliente_id':['mio','otro']},{**self.q,'regla_id':['x'*101]},
            {**self.q,'cliente_id':['../mio']},{'cliente_id':['mio']},{**self.q,'regla_id':R}]:
   self.assertEqual(self.consultar(q)[0],400)
  self.fread.assert_not_called()
 def test_unique_matching404(self):
  for rows in [[],[R,R],[{**R,'cliente_id':'otro'}]]:
   self.fmotor.return_value={'recomendaciones':rows};self.assertEqual(self.consultar()[0],404)
 def test_metodo_mismo_revisable_sin_contractraw(self):
  self.fmotor.return_value={'recomendaciones':[]}
  self.fmetodo.return_value={'sugerencias':[{'cliente_id':'mio','regla_id':'cadencia_fixture',
    'recomendacion':'Confirmar última reunión.','responsable_id':'empleado',
    'fuentes_operativas':[{'tipo':'decision_humana','fecha':'2026-10-03','detalle':'PRECIO_PRIVADO'}]}]}
  code,d=self.consultar({**self.q,'regla_id':['cadencia_fixture']});self.assertEqual(code,404)
  # El adaptador308 no acepta una regla no canónica desde el antiguo extend raw.
  self.fmetodo.assert_not_called();self.assertNotIn('PRECIO_PRIVADO',str(d))
 def test_seo_puerta_ambos_antes_lectura(self):
  self.fmotor.return_value={'recomendaciones':[]};self.fseo.return_value={'recomendaciones':[{**R,'regla_id':'seo_fixture'}]}
  self.real['modulos'].append('seo-web')
  self.assertEqual(self.consultar({**self.q,'regla_id':['seo_fixture']})[0],404);self.fseo.assert_not_called()
  self.vista['modulos'].append('seo-web')
  self.assertEqual(self.consultar({**self.q,'regla_id':['seo_fixture']})[0],200);self.assertEqual(self.fseo.call_count,1)
 def test_fuentes_ya_recortadas_se_entregan_al_motor(self):
  self.consultar()
  self.fread.assert_called_once_with(self.S,self.real,self.vista)
  self.assertEqual(self.fmotor.call_args.args,(None,{'autorizado':'fixture'},None))
 def test_otra_ruta_passthrough(self):
  self.assertEqual(self.h._api_get('/api/otra',{},self.real,self.vista),'anterior');self.fread.assert_not_called()

if __name__=='__main__':unittest.main()
