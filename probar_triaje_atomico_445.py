"""HTTP loopback, POST194 AST real y SQLite efímera. Sin bootstrap/proveedores."""
import ast, concurrent.futures, copy, json, sqlite3, sys, types, uuid, threading
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch
import unittest
import triaje_guardia_445 as G
from probar_triaje_intenciones_437 import Pruebas as Base437, ROOT

class Atomico(unittest.TestCase):
    def setUp(self):
        self.f = Base437(); self.f.setUp()
        f = self.f
        f.doc['triaje'][0].update(id='g-RO123',url='https://desk.example/ticket/123',departamento='dep1')
        f.doc['correos']=[{'id':'t-RO123','numero':'RO123','cliente_id':'cliente1', 'url':'https://desk.example/ticket/123','departamento':'dep1'}]
        f.persist()
        f.S.E.crudo['personas'].append({'id':'ops2','estado':'activo','puestos':['operaciones']})
        tree=ast.parse((ROOT/'servir.py').read_text())
        lleva=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='lleva_cliente')
        ns={'P':f.S.P}; exec(compile(ast.Module(body=[lleva],type_ignores=[]),'lleva_real','exec'),ns)
        f.S.lleva_cliente=ns['lleva_cliente']
        self.name='qa445_'+uuid.uuid4().hex
        mod=types.ModuleType(self.name); mod.__dict__.update(vars(f.S)); sys.modules[self.name]=mod
        self.mod=mod
        branch=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and '/api/acciones' in ast.unparse(n.test) and 'INSERT INTO acciones' in ast.unparse(n))
        fn=ast.parse('def post(self,ruta,real,persona,b):\n pass').body[0]; fn.body=[branch]
        def conectar():
            c=sqlite3.connect(f.db,timeout=8); c.row_factory=sqlite3.Row; return c
        ns={'conectar':conectar,'json':json,'registrar':lambda *a,**k:None,'sys':sys,'__name__':self.name}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'POST194_real','exec'),ns)
        H=f.http.RequestHandlerClass
        H.validar_accion=lambda h,r,p,b:(b.get('cliente_id'),None)
        H.api_post=ns['post']
        def do_POST(h):
            b=json.loads(h.rfile.read(int(h.headers['Content-Length'])))
            r=h.headers.get('X-RO-Yo'); v=h.headers.get('X-RO-Como') or r
            h.api_post('/api/acciones',{'id':r},{'id':v},b)
        H.do_POST=do_POST
        self.body={'modulo':'bandeja','herramienta':'desk','tipo':'asignar','objeto':'RO123','cliente_id':'cliente1','intencion_id':str(uuid.uuid4()),'texto':'Solicitar asignación del ticket RO123','vista_previa':{'a':'account','ticket':'RO123','origen':'triaje'}}
    def tearDown(self):
        sys.modules.pop(self.name,None); self.f.tearDown()
    def request(self,b=None,actor='ops',como=None):
        headers={'Content-Type':'application/json','X-RO-Yo':actor,'X-RO-App':'1'}
        if como:headers['X-RO-Como']=como
        req=Request(self.f.url+'/api/acciones',json.dumps(b or self.body).encode(),headers=headers)
        try:
            with urlopen(req,timeout=12) as r:return r.status,json.load(r)
        except HTTPError as e:return e.code,json.load(e)
    def counts(self):
        with sqlite3.connect(self.f.db) as c:
            tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            return (c.execute('SELECT count(*) FROM acciones').fetchone()[0],c.execute('SELECT count(*) FROM intenciones_acciones').fetchone()[0] if 'intenciones_acciones' in tables else 0)
    def test_invalid_UUID_rejected_without_write(self):
        self.assertEqual(self.request({**self.body,'intencion_id':'invalid'})[0],400)
        self.assertEqual(self.counts(),(0,0))
    def test_authority_revoked_during_final_source_IO(self):
        orig=G.T.referencia_para_guardia
        calls=[0]
        def revoke(*a,**k):
            result=orig(*a,**k);calls[0]+=1
            if calls[0]==2:self.f.activos.clear()
            return result
        with patch.object(G.T,'referencia_para_guardia',side_effect=revoke):self.assertEqual(self.request()[0],403)
        self.assertEqual(self.counts(),(0,0))
    def test_role_revoked_after_insert_rolls_back(self):
        orig=G.revalidar
        def revoke(S,c,r,p,b,g):
            self.f.S.E.crudo['personas'][0]['puestos']=['account'];return orig(S,c,r,p,b,g)
        with patch.object(G,'revalidar',side_effect=revoke):self.assertEqual(self.request()[0],403)
        self.assertEqual(self.counts(),(0,0))
    def test_duplicate_receiver_denied(self):
        self.f.S.E.crudo['personas'].append(copy.deepcopy(self.f.S.E.crudo['personas'][1]))
        self.assertEqual(self.request()[0],403);self.assertEqual(self.counts(),(0,0))
    def test_two_UUID_concurrent_one_action_one_receipt(self):
        b={**self.body,'intencion_id':str(uuid.uuid4())}
        for _ in range(2):
            code,dto,_headers=self.f.req(query='ticket_id=g-RO123&cliente_id=cliente1')
            self.assertEqual(code,200);self.assertEqual(dto['tipos']['asignar']['cantidad'],0)
        barrier=threading.Barrier(2)
        def simultaneous(body):
            barrier.wait(timeout=5);return self.request(body)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            out=list(pool.map(simultaneous,[self.body,b]))
        self.assertEqual(sorted(x[0] for x in out),[200,409]); self.assertEqual(self.counts(),(1,1))
    def test_ack_lost_same_uuid_restart_connection_replays(self):
        a=self.request(); b=self.request()
        self.assertEqual((a[0],b[0]),(200,200));self.assertEqual(a[1]['id'],b[1]['id'])
        self.assertTrue(b[1]['intencion_guardada']['repetida']);self.assertEqual(self.counts(),(1,1))
        self.assertEqual(b[1]['estado'],'simulada');self.assertNotIn('confirmado_desk',b[1])
    def test_other_actor_and_close_bridge_blocked(self):
        self.assertEqual(self.request()[0],200)
        self.assertEqual(self.request({**self.body,'intencion_id':str(uuid.uuid4())},actor='ops2')[0],409)
        b={**self.body,'intencion_id':str(uuid.uuid4()),'tipo':'cerrar','texto':'Solicitar cierre del ticket RO123 desde el reparto','vista_previa':{'estado':'Cerrado','ticket':'RO123'}}
        self.assertTrue(G.aplica(b));self.assertEqual(self.request(b)[0],409);self.assertEqual(self.counts(),(1,1))
    def test_legacy_alias_nullable_client_blocks(self):
        with sqlite3.connect(self.f.db) as c:c.execute("INSERT INTO acciones(quien,herramienta,tipo,objeto,cliente_id,modulo,estado) VALUES ('ops2','desk','cerrar','t-RO123',NULL,'otro','simulada')")
        self.assertEqual(self.request()[0],409);self.assertEqual(self.counts(),(1,0))
    def test_generic_close_not_acquires_triaje_protocol(self):
        b={**self.body,'tipo':'cerrar','texto':'Cierre general','vista_previa':{'estado':'Cerrado','ticket':'RO123'}}
        self.assertFalse(G.aplica(b));self.assertEqual(self.request(b)[0],200)
    def test_revocation_after_insert_rolls_back(self):
        orig=G.revalidar
        def revoke(S,c,r,p,b,g):
            self.assertEqual(c.execute('SELECT count(*) FROM acciones').fetchone()[0],1)
            self.f.activos.clear(); return orig(S,c,r,p,b,g)
        with patch.object(G,'revalidar',side_effect=revoke):self.assertEqual(self.request()[0],403)
        self.assertEqual(self.counts(),(0,0))
    def test_source_changed_after_insert_rolls_back(self):
        orig=G.revalidar
        def change(S,c,r,p,b,g):
            self.f.doc['triaje'][0]['fecha']='2026-10-04';self.f.persist();return orig(S,c,r,p,b,g)
        with patch.object(G,'revalidar',side_effect=change):self.assertEqual(self.request()[0],409)
        self.assertEqual(self.counts(),(0,0))
    def test_viewas_and_pilot_denied(self):
        self.assertEqual(self.request(como='account')[0],403)
        with patch.dict('os.environ',{'RO_PILOTO_LECTURA':'1'}):self.assertEqual(self.request()[0],403)
        self.assertEqual(self.counts(),(0,0))
    def test_inactive_duplicate_role_and_foreign(self):
        self.f.S.E.crudo['personas'][0]['estado']='baja';self.assertEqual(self.request()[0],403)
        self.f.S.E.crudo['personas'][0]['estado']='activo'
        self.f.S.E.crudo['personas'].append(copy.deepcopy(self.f.S.E.crudo['personas'][0]));self.assertEqual(self.request()[0],403)
        self.assertEqual(self.request(actor='ajeno')[0],403);self.assertEqual(self.counts(),(0,0))
    def test_proposal_and_null_client_denied(self):
        self.assertEqual(self.request({**self.body,'cliente_id':None})[0],400)
        b=copy.deepcopy(self.body);b['vista_previa']['a']='ajeno';self.assertEqual(self.request(b)[0],409)
        self.assertEqual(self.counts(),(0,0))
    def test_alias_conflict_denied(self):
        self.f.doc['correos'][0]['cliente_id']='cliente2';self.f.persist()
        self.assertEqual(self.request()[0],503);self.assertEqual(self.counts(),(0,0))
    def test_postgres_no_validated_claim(self):
        with patch.dict('os.environ',{'DATABASE_URL':'postgresql://synthetic-invalid'}):self.assertEqual(self.request()[0],503)
        self.assertEqual(self.counts(),(0,0))
    def test_replay_after_revocation_denied_no_new_action(self):
        self.assertEqual(self.request()[0],200);self.f.activos.clear()
        self.assertEqual(self.request()[0],403);self.assertEqual(self.counts(),(1,1))
    def test_changed_payload_same_UUID_conflict(self):
        self.assertEqual(self.request()[0],200)
        b={**self.body,'tipo':'cerrar','texto':'Solicitar cierre del ticket RO123 desde el reparto','vista_previa':{'estado':'Cerrado','ticket':'RO123'}}
        self.assertEqual(self.request(b)[0],409);self.assertEqual(self.counts(),(1,1))

if __name__=='__main__':unittest.main()
