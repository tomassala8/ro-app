"""Cadena real 466→motor candidato, exclusivamente datos ficticios."""
import copy,json,unittest
from embudo_eventos import calcular
from ghl_embudo_observado_466 import preparar
from probar_ghl_embudo_observado_466 import base,DESDE,HASTA,CORTE
from probar_integridad_653_668 import BASE

def lecturas(sids=('subCuentaA','subCuentaB')):
 return [preparar(base(),cid,sid,DESDE,HASTA,CORTE) for cid,sid in zip(('cliente-a','cliente-b'),sids)]
def combinar(rs):
 return ([e for r in rs for e in r['eventos']],[c for r in rs for c in r['cobertura']])
class Namespace668(unittest.TestCase):
 def test_mismos_ids_contacto_y_cita_entre_tenants_no_colisionan(self):
  rs=lecturas();ev,cov=combinar(rs)
  for campo in ('event_id','lead_id'):
   self.assertTrue(set(e[campo] for e in rs[0]['eventos']).isdisjoint(e[campo] for e in rs[1]['eventos']))
  out=calcular(ev,DESDE,HASTA,CORTE,cov)
  self.assertEqual(out,BASE(ev,DESDE,HASTA,CORTE,cov))
  self.assertEqual([g['cohorte']['recibidos_observados'] for g in out['grupos']],[1,1])
  self.assertEqual([g['cohorte']['etapas']['cita']['observados'] for g in out['grupos']],[1,1])
 def test_misma_subcuenta_mapeada_a_dos_clientes_no_doble_conteo(self):
  ev,cov=combinar(lecturas(('subCuentaA','subCuentaA')))
  self.assertEqual([g['cohorte']['recibidos_observados'] for g in BASE(ev,DESDE,HASTA,CORTE,cov)['grupos']],[1,1])
  out=calcular(ev,DESDE,HASTA,CORTE,cov)
  self.assertEqual(out['incidencias']['event_id_ambito_conflictivo'],2)
  for g in out['grupos']:
   self.assertEqual(g['cohorte']['recibidos_observados'],0)
   self.assertEqual(g['cohorte']['estado'],'desconocido')
   self.assertIsNone(g['cohorte']['etapas']['cita']['valor'])
 def test_etapas_de_entidades_no_comparten_event_id(self):
  v=base();v['citas'][0]['id']=v['leads'][0]['contacto']
  r=preparar(v,'cliente-a','subCuentaA',DESDE,HASTA,CORTE)
  self.assertNotEqual(r['eventos'][0]['event_id'],r['eventos'][1]['event_id'])
  self.assertEqual(r['eventos'][0]['lead_id'],r['eventos'][1]['lead_id'])
 def test_conflicto_no_elimina_otro_cliente_valido(self):
  rs=lecturas(('subCuentaA','subCuentaA'))
  rs.append(preparar(base(),'cliente-c','subCuentaC',DESDE,HASTA,CORTE))
  ev,cov=combinar(rs);g=calcular(ev,DESDE,HASTA,CORTE,cov)['grupos'][-1]
  self.assertEqual(g['cliente_id'],'cliente-c');self.assertEqual(g['cohorte']['recibidos_observados'],1)
  self.assertEqual(g['cohorte']['etapas']['cita']['observados'],1)
 def test_salida_agregada_no_expone_identidades_privadas(self):
  ev,cov=combinar(lecturas());antes=copy.deepcopy(ev)
  out=calcular(ev,DESDE,HASTA,CORTE,cov);texto=json.dumps(out)
  for item in ev:
   self.assertNotIn(item['event_id'],texto);self.assertNotIn(item['lead_id'],texto)
  for dato in ('contactA','apptA','privado@example.invalid','subCuentaA'):self.assertNotIn(dato,texto)
  self.assertEqual(ev,antes)
 def test_cita_futura_no_asistencia_y_fuente_fecha_preservadas(self):
  ev,cov=combinar(lecturas());out=calcular(ev,DESDE,HASTA,CORTE,cov)
  for g in out['grupos']:
   self.assertEqual(g['source'],'ghl')
   for etapa in ('asistencia','venta','cualificado'):
    self.assertEqual(g['cohorte']['etapas'][etapa]['observados'],0)
    self.assertIsNone(g['cohorte']['etapas'][etapa]['tasa_sobre_recibidos'])
  self.assertEqual(ev[1]['fecha'],'2026-10-02T06:00:00+00:00')
if __name__=='__main__':unittest.main()
