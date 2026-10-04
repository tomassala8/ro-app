"""Recibo193: código real AST, SQLite temporal e intención194; cero proveedores."""
import ast
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import types
import unittest
from unittest.mock import Mock
import intenciones_acciones as IA
from probar_transporte_sincronia_193 import cargar

class Recibo193(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.db=str(Path(self.tmp.name)/'fixture.db');self.s=cargar();self.ns=self.s.ejecutar.__globals__
        tree=ast.parse(Path(__file__).with_name('sincronia.py').read_text())
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'recibo_transicion_tablero','enganchar'}]
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'sincronia:recibo193','exec'),self.ns)
        self.body={'herramienta':'clickup','tipo':'cambiar_estado','objeto':'task-fixture','modulo':'mi-trabajo',
          'intencion_id':'22222222-2222-4222-8222-222222222222','vista_previa':{'transicion_tablero':True,
          'lista_id':'list-fixture','revision':'revision-fixture','expected_estado':'abierto','a':'cerrado'}}
        self.actor={'id':'actor-fixture'};self.queue_failure=False;self.bad_base=False;self.queue_calls=0
        self.ns.update(conectar=self.conectar,tarea=lambda _: {'lista_id':'list-fixture'},
          estados_de_tarea=lambda _:['abierto','cerrado'],preparar=lambda c:c.executescript(self.s.TABLAS_SQL),
          _guardia=lambda *a:None,_tras_accion=self.queue,traceback=types.SimpleNamespace(print_exc=lambda:None))
        with self.conectar() as con:
            con.execute('CREATE TABLE acciones(id INTEGER PRIMARY KEY,quien TEXT,herramienta TEXT,tipo TEXT,objeto TEXT,modulo TEXT,cliente_id TEXT,vista_previa TEXT)')
            IA.preparar(con);con.executescript(self.s.TABLAS_SQL)
        owner=self
        class Handler:
            def responder(self,code,obj,*a,**k):return code,obj
            def _api_get(self,*a):return None
            def api_post(self,ruta,real,vista,b):
                with owner.conectar() as con:
                    IA.iniciar(con)
                    def insert(c):
                        cur=c.execute('INSERT INTO acciones(quien,herramienta,tipo,objeto,modulo,cliente_id,vista_previa) VALUES (?,?,?,?,?,?,?)',
                          (real['id'],b['herramienta'],b['tipo'],b['objeto'],b['modulo'],'cliente-fixture',json.dumps(b['vista_previa'])))
                        return cur.lastrowid
                    aid,repeated=IA.guardar(con,real['id'],b,insert)
                return self.responder(200,{'id':aid,'intencion_guardada':repeated})
        self.ns['enganchar'](Handler,types.SimpleNamespace(P=None,conectar=self.conectar))
        self.h=Handler()
    def conectar(self):
        c=sqlite3.connect(self.db);c.row_factory=sqlite3.Row;return c
    def queue(self,aid):
        self.queue_calls+=1
        if self.queue_failure:raise RuntimeError('Fallo sintético de cola')
        with self.conectar() as con:
            cid,_=self.s.crear_cambio(con,clave='accion:'+str(aid),accion_id=aid,quien='actor-fixture',canal='clickup',tipo='cambiar_estado',
              objeto={'tipo':'tarea','ref':'task-fixture','resuelto':True},cliente_id='cliente-fixture',
              cambio={'campo':'estado','valor':'cerrado'},base={'estado':'antiguo' if self.bad_base else 'abierto'},modo='simulado',modulo='mi-trabajo')
        return {'id':cid,'estado':'simulado'}
    def post(self,b=None):return self.h.api_post('/api/acciones',self.actor,self.actor,b or self.body)
    def receipt(self,aid=1,b=None,actor=None):return self.ns['recibo_transicion_tablero'](aid,actor or self.actor,b or self.body)
    def count(self,table):
        with self.conectar() as c:return c.execute('SELECT count(*) FROM '+table).fetchone()[0]
    def test_dos_clics_misma_intencion_mismo_recibo(self):
        a=self.post()[1];b=self.post()[1]
        self.assertTrue(a['recibo_durable']);self.assertEqual(a['recibo'],b['recibo'])
        self.assertEqual(self.count('acciones'),1);self.assertEqual(self.count('sinc_cambios'),1)
        self.assertFalse(b['confirmacion_remota']);self.assertEqual(b['cola_estado'],'simulado')
    def test_respuesta_perdida_reinicio_relee_vinculo(self):
        self.post();s=cargar();ns=s.ejecutar.__globals__
        node=next(n for n in ast.parse(Path(__file__).with_name('sincronia.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='recibo_transicion_tablero')
        exec(compile(ast.Module(body=[node],type_ignores=[]),'recibo-restart','exec'),ns)
        ns.update(conectar=self.conectar,tarea=lambda _: {'lista_id':'list-fixture'},estados_de_tarea=lambda _:['abierto','cerrado'])
        r=ns['recibo_transicion_tablero'](1,self.actor,self.body)
        self.assertTrue(r['recibo_durable']);self.assertEqual(r['recibo']['accion_id'],1)
        self.assertEqual(self.post()[1]['recibo'],r['recibo']);self.assertEqual(self.count('acciones'),1)
    def test_cola_falla_guardado_no_simula_envio_y_retry_recupera(self):
        self.queue_failure=True;r=self.post()[1]
        self.assertEqual(r['cola_estado'],'pendiente_recuperacion');self.assertFalse(r['recibo_durable'])
        self.assertEqual(self.count('acciones'),1);self.assertEqual(self.count('sinc_cambios'),0)
        self.queue_failure=False;r=self.post()[1]
        self.assertTrue(r['recibo_durable']);self.assertEqual(self.count('acciones'),1)
    def test_base_anterior_distinta_no_recibo_falso(self):
        self.bad_base=True;r=self.post()[1];self.assertFalse(r['recibo_durable']);self.assertEqual(r['cola_estado'],'pendiente_recuperacion')
    def test_actor_ajeno_no_recibo(self):
        self.post();self.assertFalse(self.receipt(actor={'id':'otro'})['recibo_durable'])
    def test_cuerpo_reintentado_distinto_no_recibo(self):
        self.post();b=copy.deepcopy(self.body);b['vista_previa']['a']='otro'
        self.assertFalse(self.receipt(b=b)['recibo_durable'])
    def test_lista_catalogo_actual_incoherente_no_recibo(self):
        self.post();self.ns['tarea']=lambda _: {'lista_id':'otra'}
        self.assertFalse(self.receipt()['recibo_durable'])
    def test_sin_ledger_no_recibo(self):
        self.post()
        with self.conectar() as con:con.execute('DELETE FROM intenciones_acciones')
        self.assertFalse(self.receipt()['recibo_durable'])
    def test_marcado_manual_no_confirmacion_remota(self):
        self.post()
        with self.conectar() as con:self.s.paso(con,1,'confirmado','hecho_a_mano')
        self.assertTrue(self.receipt()['recibo_durable']);self.assertFalse(self.receipt()['confirmacion_remota'])
    def test_simulado_verificado_no_confirmacion_remota(self):
        self.post()
        with self.conectar() as con:self.s.paso(con,1,'confirmado','verificado')
        self.assertFalse(self.receipt()['confirmacion_remota'])
    def test_catalogo_destino_desaparece_no_recibo(self):
        self.post();self.ns['estados_de_tarea']=lambda _:['abierto']
        self.assertFalse(self.receipt()['recibo_durable'])
    def test_http_rechazado_no_cola_ni_recibo(self):
        self.ns['_guardia']=lambda *a:(409,'Cambio rechazado')
        code,r=self.post();self.assertEqual(code,409);self.assertEqual(self.queue_calls,0)
        self.assertNotIn('recibo_durable',r);self.assertEqual(self.count('acciones'),0)
    def test_cola_none_no_acredita_vinculo(self):
        self.ns['_tras_accion']=lambda _:None
        code,r=self.post();self.assertEqual(code,200);self.assertFalse(r['recibo_durable'])
        self.assertEqual(r['cola_estado'],'pendiente_recuperacion')
    def test_cliente_de_accion_no_coincide_con_cola_no_recibo(self):
        self.post()
        with self.conectar() as con:con.execute("UPDATE acciones SET cliente_id='otro' WHERE id=1")
        self.assertFalse(self.receipt()['recibo_durable'])
    def test_legacy_sin_optin_no_nuevo_contrato(self):
        b=copy.deepcopy(self.body);b['vista_previa'].pop('transicion_tablero');r=self.post(b)[1]
        self.assertNotIn('recibo_durable',r);self.assertIn('sincronia',r)
    def test_ver_como_no_wrapper_de_cola(self):
        self.h.api_post('/api/acciones',self.actor,{'id':'otro'},self.body)
        self.assertEqual(self.queue_calls,0)

if __name__=='__main__':unittest.main()
