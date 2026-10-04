import copy,unittest
from unittest.mock import patch
import permisos as P
from fuentes_verdad import clientes_activos as ACT
from mi_trabajo_proyeccion import recortar
from pruebas_permisos_servicio import recortador_puro
class Pruebas(unittest.TestCase):
 def doc(self):
  return {'tareas':[{'id':'t1','cli':'propio','cliente':'Propio','persona_id':'account','lista_id':'L1'}],'estados_lista':{'L1':['propio'],'L2':['privado']},'estados_detalle':{'L1':[{'estado':'propio'}],'L2':[{'estado':'privado'}]},'raras_estimacion':[{'persona_id':'account','tarea_id':'t1','tarea':'Propia'},{'persona_id':'account','tarea_id':'ajena','tarea':'Privada'}],'largas':[{'persona_id':'account','tarea_id':'ajena'}],'raras_cliente':[{'persona_id':'account','tarea_id':'t1','cliente_id':'ajeno'}],'horas_dia':[{'persona_id':'account','dias':{'2026-10-02':8}}]}
 def test_fuente_actual_P_y_recorte(self):
  p={'id':'account','puestos':['account']};raw={'personas':[p],'clientes':[{'id':'propio','nombre':'Propio'},{'id':'ajeno','nombre':'Ajeno'}],'asignaciones':[{'persona_id':'account','cliente_id':'propio','silla':'account'}]}
  d=self.doc();d['tareas'].append({'id':'ajena','cli':'ajeno','cliente':'Ajeno','persona_id':'account','lista_id':'L2'})
  out=recortador_puro(raw)(p,P.contexto(p,raw),d)
  self.assertEqual([t['id'] for t in out['tareas']],['t1']);self.assertIn('L2',out['estados_lista'])
  out=recortar(out);self.assertEqual(set(out['estados_lista']),{'L1'});self.assertEqual(set(out['estados_detalle']),{'L1'})
 def test_hook_ACT_exacto(self):
  d=self.doc()
  with patch.object(ACT,'estado',return_value={'_no_operativos':set()}),patch.object(ACT,'fila_de_baja',return_value=False),patch.object(ACT,'_exacto_baja',return_value=False):
   out=ACT.quitar_bajas(d,'mi_trabajo/mi_trabajo');other=ACT.quitar_bajas(d,'otro/modulo')
  self.assertEqual(set(out['estados_lista']),{'L1'});self.assertIn('L2',other['estados_lista'])
 def test_auxiliares_y_agregados_no_mutacion(self):
  d=self.doc();before=copy.deepcopy(d);out=recortar(d)
  self.assertEqual(out['raras_estimacion'],[d['raras_estimacion'][0]]);self.assertEqual(out['largas'],[]);self.assertEqual(out['raras_cliente'],[]);self.assertEqual(out['horas_dia'],d['horas_dia']);self.assertEqual(d,before)
 def test_vacio_failclosed(self):
  d=self.doc();d['tareas']=[];out=recortar(d);self.assertEqual(out['estados_lista'],{});self.assertEqual(out['raras_estimacion'],[])
 def test_multi_y_ambigua(self):
  d=self.doc();d['tareas'].append({**d['tareas'][0],'persona_id':'otra'});self.assertEqual(set(recortar(d)['estados_lista']),{'L1'})
  d['tareas'][1]['cli']='ajeno';self.assertEqual(recortar(d)['estados_lista'],{})
 def test_global_y_aux_persona_ajena(self):
  d=self.doc();d['tareas'][0]['cli']=None;d['raras_estimacion'][0]['persona_id']='otra';self.assertEqual(set(recortar(d)['estados_lista']),{'L1'});self.assertEqual(recortar(d)['raras_estimacion'],[])
if __name__=='__main__':unittest.main()
