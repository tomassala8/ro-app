"""518: router/auth/JSON responder actuales extraídos, sin servidor ni BD."""
import ast,io,json,os,traceback,types,unittest
from pathlib import Path
from urllib.parse import urlparse,unquote,parse_qs
from unittest.mock import patch
import permisos as P
import crm_ultima_valida_api_513 as A
from fuentes_crm import probar_autoridad_ultima_valida_499 as F

class Enganche518(unittest.TestCase):
    def setUp(self):
        f=F.Autoridad499();f.setUp();self.f=f;self.S=f.S
        tree=ast.parse((Path(__file__).parent/'servir.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Manejador')
        funcs=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in ('do_GET','api_get','_quien','responder')]
        ns={'json':json,'P':P,'E':self.S.E,'ACCESO':types.SimpleNamespace(activo=lambda:False),
            'urlparse':urlparse,'unquote':unquote,'parse_qs':parse_qs,'traceback':traceback}
        exec(compile(ast.Module(body=funcs,type_ignores=[]),'actual_server_methods','exec'),ns)
        class H:
            def __init__(self,headers,path,host=True,cookies=None):
                self.headers=headers;self.path=path;self.host=host;self.cookies=cookies or {};self.wfile=io.BytesIO();self.sent=[];self.code=None
            def host_ok(self):return self.host
            def galletas(self):return self.cookies
            def codificacion(self):return None
            def send_response(self,code):self.code=code
            def send_header(self,k,v):self.sent.append((k,v))
            def end_headers(self):pass
            def estatico(self,r):return self.responder(403,{'error':'no static'})
            def _api_get(self,*args):return self.responder(404,{'error':'unknown'})
            def _api_post(self,*args):return 'post-original'
        for name in ('do_GET','api_get','_quien','responder'):setattr(H,name,ns[name])
        H.quien=H._quien;A.enganchar(H,self.S);self.H=H
        self.env=patch.dict(os.environ,{A.ENV:'',A.PIN_ENV:''});self.env.start()
    def tearDown(self):self.env.stop()
    def request(self,headers=None,path='/api/crm/ultima-valida',**kw):
        h=self.H(headers or {},path,**kw);h.do_GET();return h,json.loads(h.wfile.getvalue())
    def test_missing_inactive_duplicate_identity_denied_before_loader(self):
        with patch.object(A,'_leer',side_effect=AssertionError('IO')):
            h,d=self.request();self.assertEqual(h.code,401)
            self.S.E.crudo['personas'][0]['estado']='baja';h,d=self.request({'X-RO-Yo':'ops'});self.assertEqual(h.code,403)
            self.S.E.crudo['personas'][0]['estado']='activo';self.S.E.crudo['personas'].append(dict(self.S.E.crudo['personas'][0]))
            h,d=self.request({'X-RO-Yo':'ops'});self.assertEqual(h.code,403)
    def test_current_header_cookie_and_real_view_scope(self):
        h,d=self.request({'X-RO-Yo':'ops','X-RO-Como':'account'})
        self.assertEqual(h.code,200);self.assertEqual(d,{'version':'513.1','estado':'sin_configurar','proyeccion':None})
        self.assertIn(('Cache-Control','no-store'),h.sent);self.assertIn(('Content-Type','application/json; charset=utf-8'),h.sent)
        self.assertEqual(int(dict(h.sent)['Content-Length']),len(h.wfile.getvalue()))
        h,d=self.request(cookies={'ro_yo':'account'});self.assertEqual(h.code,200)
        h,d=self.request({'X-RO-Yo':'account','X-RO-Como':'ops'});self.assertEqual(h.code,403)
    def test_host_query_and_routes_no_scope_expansion(self):
        with patch.object(A,'_leer',side_effect=AssertionError('IO')):
            h,d=self.request({'X-RO-Yo':'ops'},host=False);self.assertEqual(h.code,403)
            for suffix in ('?cliente_id=c2','?path=private','?yo=ops','?como=account'):
                h,d=self.request({'X-RO-Yo':'ops'},path='/api/crm/ultima-valida'+suffix);self.assertEqual(h.code,400)
            h,d=self.request({'X-RO-Yo':'ops'},path='/api/crm/ultima-valida/foreign');self.assertEqual(h.code,404)
    def test_post_hook_untouched_and_blocked_returns_no_private(self):
        self.assertEqual(self.H({},'')._api_post('/api/crm/ultima-valida'),'post-original')
        self.S.E.nucleo_bloqueado=True
        h,d=self.request({'X-RO-Yo':'ops'});self.assertEqual(h.code,503)
        self.assertEqual(set(d),{'error'});self.assertIn(('Cache-Control','no-store'),h.sent)
    def test_runtime_revocation_role_before_get_no_data(self):
        self.S.E.crudo['personas'][0]['puestos']=['seo']
        with patch.object(A,'_leer',side_effect=AssertionError('IO')):
            h,d=self.request({'X-RO-Yo':'ops'});self.assertEqual(h.code,403)
        for key in ('subcuenta_id','contacto','proyeccion','clientes'):self.assertNotIn(key,d)
    def test_pilot_last_hook_preserves_existing_deny_policy(self):
        import piloto_lectura as PIL
        self.H.api_post=self.H._api_post;PIL.enganchar(self.H)
        with patch.dict(os.environ,{'RO_PILOTO_LECTURA':'si'}),patch.object(A,'_leer',side_effect=AssertionError('IO')):
            h,d=self.request({'X-RO-Yo':'ops'});self.assertEqual(h.code,403)
            self.assertEqual(d['codigo'],'piloto_lectura_limitada')
            post=self.H({},'');post.api_post('/api/crm/ultima-valida',None,None,None)
            self.assertEqual(post.code,403);self.assertEqual(json.loads(post.wfile.getvalue())['codigo'],'piloto_solo_lectura')
if __name__=='__main__':unittest.main()
