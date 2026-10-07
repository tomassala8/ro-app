"""Fixtures aisladas: funciones reales, SQLite temporal, sin servidor/proveedores."""
import ast
import contextlib
import copy
import json
import re
import sqlite3
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch
import mi_trabajo as M
import transiciones_mi_trabajo as T
APP = Path(__file__).resolve().parent
PERS = {'id':'fixture', 'estado':'activo', 'puestos':['paid'], 'correo':'fixture@example.invalid'}
UUID = '12345678-1234-4234-8234-123456789012'


def documento():
 return {'generado':'2026-10-03', 'tareas':[{'id':'task_fixture','cli':'fixture_cli','persona_id':'fixture','lista_id':'list_fixture','estado':'pendiente'}], 'estados_lista':{'list_fixture':['pendiente','en curso','cerrada']}, 'estados_detalle':{'list_fixture':[{'estado':'pendiente','tipo':'open'},{'estado':'en curso','tipo':'custom'},{'estado':'cerrada','tipo':'closed'}]}}


def funcion(fichero, nombre, ns, clase=None):
 tree=ast.parse((APP/fichero).read_text())
 body=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==clase).body if clase else tree.body
 f=next(n for n in body if isinstance(n,ast.FunctionDef) and n.name==nombre)
 exec(compile(ast.Module(body=[f],type_ignores=[]),fichero,'exec'),ns)
 return ns[nombre]


class Pruebas(unittest.TestCase):
 def setUp(self):
  self.D=documento(); self.activo=True; self.permiso=True
  self.crudo={'personas':[dict(PERS)],'clientes':[{'id':'fixture_cli'}]}
  self.p=types.SimpleNamespace(contexto=lambda*a:{},ver=lambda*a:{'ok':self.permiso})
  self.s=types.SimpleNamespace(E=types.SimpleNamespace(crudo=self.crudo),ve_alguno=lambda*a:True)
  from identidades_clickup_204 import preparar_autorizacion
  def fuente_identidad():
   return preparar_autorizacion(self.crudo['personas'],[{'id':'cu_fixture','email':'fixture@example.invalid'}],
     list({row['id']:{'id':row['id'],'lista_id':row['lista_id'],'estado':row['estado'],'carpeta_id':'folder_fixture','asignados':[{'id':'cu_fixture'}]}
      for row in self.D['tareas']}.values()),
     {'folder_fixture':['fixture_cli']})
  self.patches=[patch.object(M,'S',self.s),patch.object(M,'P',self.p),patch.object(M,'doc',lambda:self.D),patch.object(M,'SINC',None),patch.object(M,'_fuente_autorizacion_tareas',fuente_identidad)]
  for p in self.patches:p.start();self.addCleanup(p.stop)
  import fuentes_verdad.clientes_activos as ACT
  pp=patch.object(ACT,'es_activo_id',lambda*a:self.activo);pp.start();self.addCleanup(pp.stop)
  self.db=sqlite3.connect(':memory:');self.db.row_factory=sqlite3.Row;self.addCleanup(self.db.close)
  self.db.executescript('CREATE TABLE acciones(id INTEGER PRIMARY KEY,herramienta,tipo,objeto,vista_previa);CREATE TABLE sinc_cambios(id INTEGER PRIMARY KEY,accion_id,cambio,canal,objeto_ref);CREATE TABLE sinc_pasos(id INTEGER PRIMARY KEY,cambio_id,estado,evento,hora);')
 def cuerpo(self, **vp):
  return {'modulo':'mi-trabajo','herramienta':'clickup','tipo':'cambiar_estado','objeto':'task_fixture','intencion_id':UUID,'vista_previa':{'transicion_tablero':True,'a':'en curso',**T.proyectar(self.D,'task_fixture',self.db),**vp}}
 def test_transicion_valida_en_transaccion(self):
  b=self.cuerpo();self.db.execute('BEGIN IMMEDIATE');self.assertIsNone(M.validar_transicion_en_transaccion(self.db,PERS,b))
 def test_transicion_requiere_transaccion(self):
  self.assertEqual(M.validar_transicion_en_transaccion(self.db,PERS,self.cuerpo())[0],409)
 def test_cambio_snapshot_detectado(self):
  b=self.cuerpo();self.D['generado']='otra_version';self.db.execute('BEGIN IMMEDIATE');self.assertEqual(M.validar_transicion_en_transaccion(self.db,PERS,b)[0],409)
 def test_cola_persistida_sin_sinc_cambia_estado_y_revision(self):
  antes=self.cuerpo();self.db.execute("INSERT INTO acciones VALUES(1,'clickup','cambiar_estado','task_fixture',?)",(json.dumps({'a':'en curso'}),));self.db.commit()
  despues=T.proyectar(self.D,'task_fixture',self.db);self.assertEqual(despues['expected_estado'],'en curso');self.assertNotEqual(antes['vista_previa']['revision'],despues['revision'])
  self.db.execute('BEGIN IMMEDIATE');self.assertEqual(M.validar_transicion_en_transaccion(self.db,PERS,antes)[0],409)
 def test_fallido_no_es_estado_confirmado(self):
  self.db.execute("INSERT INTO acciones VALUES(1,'clickup','cambiar_estado','task_fixture',?)",(json.dumps({'a':'en curso'}),));self.db.execute("INSERT INTO sinc_cambios VALUES(1,1,?,'clickup','task_fixture')",(json.dumps({'campo':'estado','valor':'en curso'}),));self.db.execute("INSERT INTO sinc_pasos(id,cambio_id,estado,evento) VALUES(1,1,'fallido','fallo')");self.db.commit()
  self.assertTrue(T.proyectar(self.D,'task_fixture',self.db)['bloqueada'])
 def test_descarte_restaura_estado_y_cambia_revision(self):
  self.test_fallido_no_es_estado_confirmado();antes=T.proyectar(self.D,'task_fixture',self.db)
  self.db.execute("INSERT INTO sinc_pasos(id,cambio_id,estado,evento) VALUES(2,1,'descartado','descarte')");self.db.commit();d=T.proyectar(self.D,'task_fixture',self.db)
  self.assertFalse(d['bloqueada']);self.assertEqual(d['expected_estado'],'pendiente');self.assertNotEqual(d['revision'],antes['revision'])
 def test_cliente_inactivo_denegado_legacy(self):
  self.activo=False;self.assertEqual(M.validar(PERS,{**self.cuerpo(),'vista_previa':{'a':'en curso'}})[0],403)
 def test_cartera_revocada_denegada(self):
  self.permiso=False;self.assertEqual(M.validar(PERS,self.cuerpo())[0],403)
 def test_identidad_revocada_no_sigue_snapshot(self):
  self.crudo['personas'][0]['estado']='baja';self.assertEqual(M.validar(PERS,self.cuerpo())[0],403)
 def test_tarea_duplicada_ambigua_no_firstwins(self):
  b=self.cuerpo();self.D['tareas'].append({**self.D['tareas'][0],'cli':'otra'});self.assertEqual(M.validar(PERS,b)[0],409)
 def test_multiasignacion_legitima_conservada(self):
  self.D['tareas'].append({**self.D['tareas'][0],'persona_id':'otro'});self.assertIsNone(M.validar(PERS,self.cuerpo()))
 def test_catalogo_tipo_ausente_denegado(self):
  b=self.cuerpo();self.D['estados_detalle']['list_fixture'][1]['tipo']=None;self.assertEqual(M.validar(PERS,b)[0],409)
 def test_lista_ajena_no_permite_estado_homonimo(self):
  self.assertEqual(M.validar(PERS,self.cuerpo(lista_id='otra_lista'))[0],400)
 def test_global_sin_catalogo_interno_no_cliente_inventado_ni_modificacion(self):
  self.D['tareas'][0]['cli']=None;self.assertEqual(M.validar(PERS,self.cuerpo())[0],409)
 def test_postgres_no_anuncia_capacidad(self):
  self.assertFalse(T.compatible(types.SimpleNamespace(in_transaction=True)))
  self.assertEqual(M.validar_transicion_en_transaccion(types.SimpleNamespace(in_transaction=True),PERS,self.cuerpo())[0],503)
 def test_prevalidacion_permite_replay_version_antigua(self):
  b=self.cuerpo();self.D['generado']='otra';self.assertIsNone(M.validar(PERS,b))
 def test_segundo_writer_ve_accion_primera_tras_lock(self):
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'fixture.db';con=sqlite3.connect(f);con.row_factory=sqlite3.Row
   con.executescript('CREATE TABLE acciones(id INTEGER PRIMARY KEY,herramienta,tipo,objeto,vista_previa);')
   token=T.proyectar(self.D,'task_fixture',con);b={'modulo':'mi-trabajo','herramienta':'clickup','tipo':'cambiar_estado','objeto':'task_fixture','intencion_id':UUID,'vista_previa':{'transicion_tablero':True,'a':'en curso',**token}}
   con.execute('BEGIN IMMEDIATE');self.assertIsNone(M.validar_transicion_en_transaccion(con,PERS,b))
   out=[];empezado=threading.Event()
   def otro():
    cc=sqlite3.connect(f,timeout=3);cc.row_factory=sqlite3.Row;empezado.set();cc.execute('BEGIN IMMEDIATE');out.append(M.validar_transicion_en_transaccion(cc,PERS,b));cc.rollback();cc.close()
   t=threading.Thread(target=otro);t.start();empezado.wait(1)
   con.execute("INSERT INTO acciones VALUES(1,'clickup','cambiar_estado','task_fixture',?)",(json.dumps({'a':'en curso'}),));con.commit();t.join(3);con.close()
   self.assertFalse(t.is_alive());self.assertEqual(out[0][0],409)
 def get(self, vista=None):
  vista=vista or PERS
  self.s.conectar=lambda:self.db
  class H:
   def responder(h,code,data):h.code=code;h.data=data
  h=H()
  with patch.object(M,'personas',lambda:self.crudo['personas']),patch.object(M,'persona',lambda*a:PERS),patch.object(M,'ve_persona',lambda*a:True),patch.object(M,'crono_de',lambda*a:None):
   M.get_estado(h,{},PERS,vista)
  self.assertEqual(h.code,200);return h.data
 def test_get_token_solo_tarea_autorizada_y_sqlite(self):
  d=self.get();self.assertTrue(d['capacidad_transicion']['activo']);self.assertEqual(d['transiciones']['task_fixture'],T.proyectar(self.D,'task_fixture',self.db))
 def test_get_vercomo_no_ofrece_token(self):
  d=self.get(vista={**PERS,'id':'otro'});self.assertFalse(d['capacidad_transicion']['activo']);self.assertEqual(d['transiciones'],{})
 def test_get_revocacion_no_token(self):
  self.activo=False;self.assertEqual(self.get()['transiciones'],{})
 def test_transaccion_revalida_cartera_y_revision_pieza(self):
  b=self.cuerpo();self.db.execute('BEGIN IMMEDIATE');self.permiso=False
  self.assertEqual(M.validar_transicion_en_transaccion(self.db,PERS,b)[0],403)
  self.permiso=True;self.s.pieza_en_revision=lambda*a:True
  self.assertEqual(M.validar_transicion_en_transaccion(self.db,PERS,b)[0],403)
 def confirmado(self):
  self.db.execute("INSERT INTO acciones VALUES(1,'clickup','cambiar_estado','task_fixture',?)",(json.dumps({'a':'cerrada'}),))
  self.db.execute("INSERT INTO sinc_cambios VALUES(1,1,?,'clickup','task_fixture')",(json.dumps({'campo':'estado','valor':'cerrada'}),))
  self.db.execute("INSERT INTO sinc_pasos VALUES(1,1,'confirmado','verificado','2026-10-03 07:00:00')");self.db.commit()
 def test_confirmado_anterior_no_sobrescribe_copia_posterior(self):
  self.confirmado();self.D['tareas'][0].update(estado='en curso',estado_fuente='clickup',estado_leido_utc='2026-10-03T08:00:00Z')
  d=T.proyectar(self.D,'task_fixture',self.db);self.assertEqual(d['expected_estado'],'en curso');self.assertFalse(d['bloqueada'])
 def test_confirmado_sin_fecha_lectura_no_asume_generado_fresco(self):
  self.confirmado();self.D['generado']='2026-10-03 20:00';d=T.proyectar(self.D,'task_fixture',self.db)
  self.assertEqual(d['expected_estado'],'pendiente');self.assertTrue(d['bloqueada'])
 def test_confirmado_lectura_anterior_o_sin_zona_bloquea(self):
  self.confirmado()
  for fecha in ['2026-10-03T06:00:00Z','2026-10-03T08:00:00','no fecha']:
   self.D['tareas'][0].update(estado_fuente='clickup',estado_leido_utc=fecha);self.assertTrue(T.proyectar(self.D,'task_fixture',self.db)['bloqueada'])
 def test_batch_equivale_a_fresh_con_cola_y_descartes(self):
  self.test_descarte_restaura_estado_y_cambia_revision()
  indice=T.preparar_lectura(self.D,self.db,{'task_fixture'})
  self.assertEqual(T.proyectar(self.D,'task_fixture',self.db,indice),T.proyectar(self.D,'task_fixture',self.db))
 def test_tipo_unstarted_real_no_es_final(self):
  nombres=['planning mensual','próximo sprint','planning semanal','pendiente','en curso','en revisión','revisión account','revisión seo','revisión web','revisión paid','corrección','aprobado','completado','rechazado','cerrado']
  self.D['estados_lista']['list_fixture']=nombres
  self.D['estados_detalle']['list_fixture']=[{'estado':n,'tipo':'unstarted' if i<3 else 'open' if i==3 else 'custom' if i<12 else 'done' if i<14 else 'closed'} for i,n in enumerate(nombres)]
  self.D['tareas'][0]['estado']='planning mensual'
  d=self.get();self.assertEqual(d['transiciones']['task_fixture']['expected_estado'],'planning mensual');self.assertFalse(d['transiciones']['task_fixture']['bloqueada'])
  self.assertEqual(T.catalogo(self.D,'list_fixture')['planning mensual'],'unstarted')
 def test_batch_1200_tareas_permiso_una_vez_y_revocacion_siguiente_request(self):
  self.D['tareas']=[{**self.D['tareas'][0],'id':f'task_{i:04}'} for i in range(1200)]
  cuentas={'contexto':0,'ver':0,'modulo':0}
  def contexto(*a):cuentas['contexto']+=1;return {}
  def ver(*a):cuentas['ver']+=1;return {'ok':self.permiso}
  def modulo(*a):cuentas['modulo']+=1;return True
  self.p.contexto=contexto;self.p.ver=ver;self.s.ve_alguno=modulo
  consultas=[];self.db.set_trace_callback(consultas.append)
  d=self.get();self.assertEqual(len(d['transiciones']),1200)
  self.assertEqual(cuentas,{'contexto':2,'ver':2,'modulo':1})
  self.assertLessEqual(len(consultas),12)  # Lotes SQL, nunca una consulta por tarjeta.
  self.permiso=False;d=self.get();self.assertEqual(d['transiciones'],{});self.assertEqual(cuentas['contexto'],4);self.assertEqual(cuentas['modulo'],2)
 def test_batch_sql_no_incluye_otra_tarea_y_atomico_sigue_fresco(self):
  self.db.execute("INSERT INTO acciones VALUES(99,'clickup','cambiar_estado','ajena',?)",(json.dumps({'a':'cerrada'}),));self.db.commit()
  indice=T.preparar_lectura(self.D,self.db,{'task_fixture'})
  self.assertNotIn('ajena',indice['acciones'])
  viejo=T.proyectar(self.D,'task_fixture',self.db,indice)
  self.db.execute("INSERT INTO acciones VALUES(100,'clickup','cambiar_estado','task_fixture',?)",(json.dumps({'a':'en curso'}),));self.db.commit()
  self.assertNotEqual(viejo['revision'],T.proyectar(self.D,'task_fixture',self.db)['revision'])
 def core(self, cliente, permiso=False, actual=True):
  reglas={'acciones_permitidas':{'_herramientas':['clickup'],'mi-trabajo':['cambiar_estado']},'acciones_con_efecto_fuera':{'clickup_tarea':['cambiar_estado']}}
  p=types.SimpleNamespace(REGLAS=reglas,contexto=lambda*a:{},ver=lambda*a:{'ok':permiso},enlace_seguro=lambda*a:True)
  E=types.SimpleNamespace(crudo=self.crudo,modulos={'mi-trabajo':{}},persona=lambda*a:PERS)
  ns={'P':p,'E':E,'ACT':types.SimpleNamespace(es_activo_id=lambda*a:actual),'ve_alguno':lambda*a:True,'_enlaces_malos':lambda*a:False,'pieza_en_revision':lambda*a:None,'tarea_de_produccion':lambda*a:{'autores':{'fixture'},'cli':'fixture_cli'},'registrar_agrupado':lambda*a:None}
  f=funcion('servir.py','validar_accion',ns,'Manejador');return f(None,PERS,PERS,{'modulo':'mi-trabajo','herramienta':'clickup','tipo':'cambiar_estado','objeto':'task_fixture','cliente_id':cliente})
 def test_core_cliente_derivado_se_autoriza_antes_guardar(self):
  self.assertEqual(self.core(None)[1][0],403)
 def test_core_cliente_cuerpo_no_reasigna_tarea(self):
  self.assertEqual(self.core('otro',permiso=True)[1][0],403)
 def test_core_cliente_valido_activo_aceptado(self):
  self.assertEqual(self.core(None,permiso=True),('fixture_cli',None))
 def test_core_act_false_denegado_aunque_permiso_true(self):
  self.assertEqual(self.core(None,permiso=True,actual=False)[1][0],403)

if __name__=='__main__':unittest.main()
