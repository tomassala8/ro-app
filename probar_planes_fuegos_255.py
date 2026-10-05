"""SQLite temporal y política real, sin import de servir ni proveedores."""
import ast
import copy
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
import threading
from unittest.mock import patch
import os
from uuid import uuid4
import permisos as P
import planes_fuegos_255 as F
import piloto_lectura as PILOTO

def persona(pid, roles):
    return {'id':pid,'nombre':pid,'alias':pid,'estado':'activo','puestos':roles}

class Planes(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'fixture.db'
        self.core = {'personas':[persona('ops',['operaciones']),persona('acc',['account']),persona('foreign',['account']),persona('constanza',['proyectos','account']),persona('otherpm',['proyectos'])],
                     'clientes':[{'id':'c','nombre':'Fixture','activo_confirmado':True,'responsable_id':'acc'}],
                     'asignaciones':[{'persona_id':'acc','cliente_id':'c','silla':'account'}], 'logos':{}, 'alarmas':[], 'meta':{}}
        self.S = SimpleNamespace(E=SimpleNamespace(crudo=self.core),P=P,ACT=SimpleNamespace(es_activo_id=lambda cid:cid=='c'),
                                 PILOTO_LECTURA=SimpleNamespace(activo=lambda:False),conectar=self.conectar,
                                 ve_alguno=lambda p,mods:P.nivel_modulo(p,{'*':'todo','setters':None}) is not None)
        with self.conectar() as con:F.iniciar(con)
    def conectar(self):
        con=sqlite3.connect(self.path,timeout=2); con.row_factory=sqlite3.Row; return con
    def p(self,pid):return next(p for p in self.core['personas'] if p['id']==pid)
    def body(self,version=0,**kw):
        return {'operacion':'plan','accion_id':str(uuid4()),'cliente_id':'c','expected_version':version,
                'que':'Revisar el bloqueo y dejar evidencia','responsable_id':'acc','plazo':'2026-10-09',**kw}
    def post(self,b,pid='acc',vista=None):return F.responder(self.S,self.p(pid),self.p(vista or pid),cuerpo=b)
    def get(self,pid='acc',vista=None):return F.responder(self.S,self.p(pid),self.p(vista or pid),query={'cliente_id':['c']})
    def test_policy_real_account_own_ops_and_foreign(self):
        self.assertTrue(self.get()[1]['capacidades']['editar'])
        self.assertTrue(self.get('ops')[1]['capacidades']['editar'])
        self.assertEqual(self.get('foreign')[0],404)
    def test_read_intersection_and_write_denied_ver_como(self):
        self.assertEqual(self.get('ops','foreign')[0],404)
        self.assertEqual(self.post(self.body(),'ops','acc')[0],403)
        self.assertTrue(self.get('ops','acc')[1]['capacidades']['solo_lectura'])
    def test_pilot_no_write(self):
        self.S.PILOTO_LECTURA.activo=lambda:True
        self.assertEqual(self.post(self.body(),'ops')[0],403)
        self.assertEqual(self.get()[1]['version'],0)
    def test_actual_pilot_wrapper_get_scoped_post_blocked(self):
        with patch.dict(os.environ,{'RO_PILOTO_LECTURA':'1'}):
            self.S.PILOTO_LECTURA=PILOTO
            S=self.S
            class Handler:
                def responder(self,code,dto):return code,dto
                def _api_get(self,ruta,q,real,vista):return F.responder(S,real,vista,query=q)
                def api_post(self,*a):raise AssertionError('POST llegó al escritor')
            PILOTO.enganchar(Handler);h=Handler()
            self.assertEqual(h._api_get('/api/en-rojo/planes',{'cliente_id':['c']},self.p('acc'),self.p('acc'))[0],200)
            self.assertEqual(h._api_get('/api/en-rojo/planes',{'cliente_id':['c']},self.p('foreign'),self.p('foreign'))[0],404)
            self.assertEqual(h._api_get('/api/en-rojo/planes/externo',{},self.p('acc'),self.p('acc'))[0],403)
            self.assertEqual(h.api_post('/api/en-rojo/planes',self.p('acc'),self.p('acc'),self.body())[0],403)
    def test_current_unique_active_identity_and_client(self):
        for field,value in [('personas',copy.deepcopy(self.p('acc'))),('clientes',copy.deepcopy(self.core['clientes'][0]))]:
            self.core[field].append(value);self.assertEqual(self.get()[0],404);self.core[field].pop()
        self.p('acc')['estado']='baja';self.assertEqual(self.get()[0],404)
    def test_act_authority_denies(self):
        self.S.ACT.es_activo_id=lambda cid:None
        self.assertEqual(self.get()[0],404);self.assertEqual(self.post(self.body())[0],404)
    def test_source_secret_gate_denies_write(self):
        self.S.E.nucleo_bloqueado=True
        self.assertEqual(self.post(self.body(),'ops')[0],503)
    def test_only_exact_current_reviewer(self):
        self.assertTrue(self.get('constanza')[1]['capacidades']['revisar'])
        self.assertFalse(self.get('otherpm')[1]['capacidades']['revisar'])
        self.p('constanza')['puestos']=['account']
        self.assertFalse(self.get('ops')[1]['capacidades']['revisar'])
        self.p('constanza')['puestos']=['proyectos'];self.core['personas'].append(copy.deepcopy(self.p('constanza')))
        self.assertEqual(self.get('constanza')[0],404)
    def test_durable_restart_and_same_uuid_replay(self):
        b=self.body();code,d=self.post(b);self.assertEqual(code,200);self.assertFalse(d['confirmado_proveedor'])
        self.assertEqual(self.get()[1]['plan']['que'],b['que'])
        self.assertTrue(self.post(b)[1]['repetida'])
        with self.conectar() as con:self.assertEqual(con.execute('SELECT count(*) FROM planes_fuegos_255').fetchone()[0],1)
    def test_uuid_payload_or_actor_changes_conflict(self):
        b=self.body();self.post(b)
        self.assertEqual(self.post({**b,'que':'Otro contenido'})[0],409)
        self.assertEqual(self.post(b,'ops')[0],409)
    def test_two_connections_cas_and_replay(self):
        caps=F.permisos(self.S,self.p('acc'),self.p('acc'),'c');b=self.body()
        with self.conectar() as c1:F.guardar(c1,b,caps,'acc','2026-10-03T11:00:00+00:00')
        with self.conectar() as c2:
            with self.assertRaises(F.ErrorPlan) as e:F.guardar(c2,self.body(),caps,'acc','2026-10-03T11:00:01+00:00')
            self.assertEqual(e.exception.codigo,409)
            self.assertTrue(F.guardar(c2,b,caps,'acc','2026-10-03T11:00:02+00:00')['repetida'])
    def test_simultaneous_two_writers_one_cas_winner(self):
        caps=F.permisos(self.S,self.p('acc'),self.p('acc'),'c')
        barrier=threading.Barrier(2);local=threading.local();actual=F.leer;results=[]
        def lectura(*args):
            d=actual(*args)
            if not getattr(local,'read',False):local.read=True;barrier.wait(timeout=2)
            return d
        def escribir():
            try:
                with self.conectar() as con:F.guardar(con,self.body(),caps,'acc','2026-10-03T11:00:00+00:00')
                results.append(200)
            except F.ErrorPlan as e:results.append(e.codigo)
        with patch.object(F,'leer',lectura):
            ts=[threading.Thread(target=escribir) for _ in range(2)]
            for t in ts:t.start()
            for t in ts:t.join(timeout=4)
            self.assertFalse(any(t.is_alive() for t in ts))
        self.assertEqual(sorted(results),[200,409])
        self.assertEqual(self.get()[1]['version'],1)
    def test_revision_exact_version_and_changed_plan_invalidates(self):
        self.post(self.body())
        b={'operacion':'revision','accion_id':str(uuid4()),'cliente_id':'c','expected_version':1,'plan_version':1,'estado':'visto','nota':''}
        code,d=self.post(b,'constanza');self.assertEqual(code,200);self.assertEqual(d['revision']['plan_version'],1)
        self.assertEqual(self.post(self.body(2))[0],200)
        d=self.get()[1];self.assertIsNone(d['revision']);self.assertEqual(len(d['historial']),3)
        self.assertEqual(self.post({**b,'accion_id':str(uuid4()),'expected_version':3},'constanza')[0],409)
    def test_revision_without_plan_or_wrong_reviewer(self):
        b={'operacion':'revision','accion_id':str(uuid4()),'cliente_id':'c','expected_version':0,'plan_version':1,'estado':'visto','nota':''}
        self.assertEqual(self.post(b,'constanza')[0],409);self.assertEqual(self.post(b,'ops')[0],403)
    def test_changes_need_note(self):
        self.post(self.body())
        b={'operacion':'revision','accion_id':str(uuid4()),'cliente_id':'c','expected_version':1,'plan_version':1,'estado':'pedir_cambios','nota':''}
        self.assertEqual(self.post(b,'constanza')[0],400)
        self.assertEqual(self.post({**b,'nota':'Concretar la evidencia'},'constanza')[0],200)
    def test_validation_unknown_fields_date_bool_version_inactive_responsible(self):
        for kw in [{'actor_id':'ops'},{'plazo':'2026-02-30'},{'expected_version':True},{'responsable_id':'missing'},{'que':''}]:
            self.assertEqual(self.post(self.body(**kw))[0],400)
        self.p('otherpm')['estado']='baja'
        self.assertEqual(self.post(self.body(responsable_id='otherpm'))[0],400)
    def test_sanitizer_real_secret_contact_price_html(self):
        b=self.body(que='Revisar bloqueo\npassword: FixtureSecret9\nContacto fixture@example.test\nCuota 100 EUR\n<script>evil()</script>')
        code,d=self.post(b);self.assertEqual(code,200)
        raw=json.dumps(d);self.assertNotIn('FixtureSecret9',raw);self.assertNotIn('fixture@example.test',raw);self.assertNotIn('100 EUR',raw);self.assertNotIn('evil()',raw)
    def test_append_only_triggers(self):
        self.post(self.body())
        for sql in ['DELETE FROM planes_fuegos_255','UPDATE planes_fuegos_255 SET actor_id=\'ops\'']:
            with self.conectar() as c:
                with self.assertRaises(sqlite3.IntegrityError):c.execute(sql)
    def test_query_exact_only_no_identity_payload(self):
        for q in [{},{'cliente_id':['c','c']},{'cliente_id':['c'],'yo':['ops']}]:
            self.assertEqual(F.responder(self.S,self.p('ops'),self.p('ops'),query=q)[0],400)
    def test_source_hooks_actual_ast_no_server_bootstrap(self):
        source=Path(__file__).with_name('servir.py').read_text();tree=ast.parse(source)
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Manejador')
        get=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_api_get')
        post=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='api_post')
        for method in [get,post]:
            branch=next(n for n in method.body if isinstance(n,ast.If) and '/api/en-rojo/planes' in ast.unparse(n.test))
            ns={'PLANES_FUEGOS_255':F,'sys':SimpleNamespace(modules={'fixture':self.S}),'__name__':'fixture'}
            fn=ast.FunctionDef(name='hook',args=ast.arguments(posonlyargs=[],args=[ast.arg(arg=n) for n in ['self','real','persona','q','b']],kwonlyargs=[],kw_defaults=[],defaults=[]),body=branch.body,decorator_list=[])
            exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'fixture','exec'),ns)
            h=SimpleNamespace(responder=lambda code,dto:(code,dto))
            result=ns['hook'](h,self.p('acc'),self.p('acc'),{'cliente_id':['c']},self.body())
            self.assertEqual(result[0],200)

if __name__=='__main__':unittest.main()
