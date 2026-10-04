"""Modos de capacidad: fixtures SQLite, sin servidor/PG/proveedores."""
import importlib.util
import os
import types
import unittest
from pathlib import Path
from unittest.mock import patch
import intenciones_acciones as I
import mi_trabajo as M
import transiciones_mi_trabajo as T
import probar_transiciones_191 as F
PERS=F.PERS


class Modos(unittest.TestCase):
 setUp=F.Pruebas.setUp
 get=F.Pruebas.get
 cuerpo=F.Pruebas.cuerpo
 def setUp(self):
  env=patch.dict(os.environ,{},clear=False);env.start();self.addCleanup(env.stop)
  os.environ.pop('RO_PILOTO_LECTURA',None);os.environ.pop('DATABASE_URL',None)
  F.Pruebas.setUp(self)
 def test_sqlite_normal_activo_con_tarea_autorizada(self):
  d=self.get();self.assertEqual(d['capacidad_transicion'],{'version':'191.1','activo':True,'motivo':None});self.assertIn('task_fixture',d['transiciones'])
 def test_piloto_no_anuncia_tokens_mantiene_lectura(self):
  os.environ['RO_PILOTO_LECTURA']='si';d=self.get()
  self.assertFalse(d['capacidad_transicion']['activo']);self.assertEqual(d['capacidad_transicion']['motivo'],'piloto_solo_lectura');self.assertEqual(d['transiciones'],{});self.assertIn('list_fixture',d['estados_lista'])
 def test_piloto_valor_desconocido_falla_cerrado(self):
  os.environ['RO_PILOTO_LECTURA']='mal_configurado';self.assertEqual(self.get()['transiciones'],{})
 def test_piloto_callback_directo_denegado_sin_SQL(self):
  b=self.cuerpo();self.db.execute('BEGIN IMMEDIATE');sql=[];self.db.set_trace_callback(sql.append)
  os.environ['RO_PILOTO_LECTURA']='si';self.assertEqual(M.validar_transicion_en_transaccion(self.db,PERS,b)[0],403);self.assertEqual(sql,[])
 def test_pg_configurado_no_anuncia_capacidad_ni_fallback_simulado(self):
  os.environ['DATABASE_URL']='postgresql://fixture-invalid-no-connect'
  d=self.get();self.assertFalse(d['capacidad_transicion']['activo']);self.assertEqual(d['transiciones'],{});self.assertEqual(d['capacidad_transicion']['motivo'],'base_no_validada')
  self.db.execute('BEGIN IMMEDIATE');b={'vista_previa':{'transicion_tablero':True}}
  self.assertEqual(M.validar_transicion_en_transaccion(self.db,PERS,b)[0],503)
 def test_vercomo_capacidad_false_sin_ampliacion(self):
  d=self.get(vista={**PERS,'id':'vista_fixture'});self.assertFalse(d['capacidad_transicion']['activo']);self.assertEqual(d['transiciones'],{});self.assertEqual(d['capacidad_transicion']['motivo'],'ver_como')
 def test_modulo_revocado_no_capacidad_y_siguiente_request_fresca(self):
  self.s.ve_alguno=lambda*a:False;d=self.get();self.assertFalse(d['capacidad_transicion']['activo']);self.assertEqual(d['transiciones'],{})
  self.s.ve_alguno=lambda*a:True;self.assertTrue(self.get()['capacidad_transicion']['activo'])
 def test_identidad_revocada_no_capacidad(self):
  self.crudo['personas'][0]['estado']='baja';self.assertFalse(self.get()['capacidad_transicion']['activo'])
 def test_cambio_piloto_entre_GET_y_callback(self):
  b=self.cuerpo();self.db.execute('BEGIN IMMEDIATE');os.environ['RO_PILOTO_LECTURA']='si'
  self.assertEqual(M.validar_transicion_en_transaccion(self.db,PERS,b)[0],403)
 def test_sqlite_query_only_no_anuncia_movimientos(self):
  self.db.execute('PRAGMA query_only=1');d=self.get();self.assertFalse(d['capacidad_transicion']['activo']);self.assertEqual(d['capacidad_transicion']['motivo'],'base_solo_lectura');self.assertEqual(d['transiciones'],{})
  self.db.execute('BEGIN');self.assertEqual(M.validar_transicion_en_transaccion(self.db,PERS,{'vista_previa':{'transicion_tablero':True}})[0],503)
 def test_adapter_pg_actual_rechazado_sin_conexion(self):
  spec=importlib.util.spec_from_file_location('adapter_pg_fixture',Path(__file__).parent/'despliegue/base.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
  con=object.__new__(b.ConexionPG)
  self.assertFalse(hasattr(con,'in_transaction'));self.assertFalse(T.capacidad(con,PERS,PERS)['activo'])
  with self.assertRaises(I.PersistenciaNoDisponible):I.iniciar(con)
  self.assertEqual(b.traducir('BEGIN IMMEDIATE')[0],'BEGIN IMMEDIATE')
  self.assertIn('sqlite_master',b.traducir("SELECT name FROM sqlite_master WHERE type='table'")[0])
  self.assertNotIn('RETURNING',b.traducir('INSERT INTO sinc_cambios (clave) VALUES (?)')[0])

if __name__=='__main__':unittest.main()
