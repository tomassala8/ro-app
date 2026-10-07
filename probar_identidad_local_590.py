"""590 correctiva L17: métodos actuales AST y comportamiento anterior explícito."""
import ast,copy,types,unittest
from pathlib import Path
from urllib.parse import urlparse,unquote,parse_qs
import permisos as P
APP=Path(__file__).resolve().parent
TREE=ast.parse((APP/'servir.py').read_text())

class Identidad590(unittest.TestCase):
 def setUp(self):
    self.account={'id':'account-fixture','correo':'account@example.invalid','estado':'activo','activo':True,'puestos':['account']}
    self.dir={'id':'direccion-fixture','correo':'direccion@example.invalid','estado':'activo','activo':True,'puestos':['direccion']}
    self.rows=[self.account,self.dir]
    self.e=types.SimpleNamespace(crudo={'personas':self.rows,'clientes':[],'asignaciones':[]},
      por_correo=lambda email:next((p for p in self.rows if p['correo']==email),None))
    self.validaciones=[]
    self.access=types.SimpleNamespace(activo=lambda:False,correo_validado=self.validar)
    ns={'E':self.e,'P':P,'ACCESO':self.access,'unquote':unquote,'urlparse':urlparse,'parse_qs':parse_qs}
    methods=[n for n in ast.walk(TREE) if isinstance(n,ast.FunctionDef) and n.name in ('_quien','galletas','host_ok','do_GET')]
    cls=ast.ClassDef(name='H',bases=[],keywords=[],body=methods,decorator_list=[])
    exec(compile(ast.fix_missing_locations(ast.Module(body=[cls],type_ignores=[])),'identity-current590','exec'),ns)
    self.ns=ns
    self.h=ns['H']();self.h.server=types.SimpleNamespace(server_address=('127.0.0.1',8772))
    self.h.client_address=('127.0.0.1',12000);self.h.headers={'Host':'localhost:8772','X-RO-Yo':self.account['id']}
    self.h.path='/api/elegir';self.h.responder=lambda c,d:(c,d)
 def validar(self,headers):
    self.validaciones.append(dict(headers));return None,'Sello sintético denegado'
 def legado(self,nombre):
    fn=copy.deepcopy(next(n for n in ast.walk(TREE) if isinstance(n,ast.FunctionDef) and n.name==nombre))
    # Restauración explícita de las tres líneas cambiadas en590, no stub de resultado.
    fn.body=[n for n in fn.body if not (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='peer' for t in n.targets))
             and not (isinstance(n,ast.If) and 'peer' in ast.unparse(n.test))]
    if nombre=='_quien':
      rama=next(n for n in fn.body if isinstance(n,ast.If) and isinstance(n.test,ast.Name) and n.test.id=='servidor')
      rama.orelse[0].value=ast.parse('self.headers.get("Cf-Access-Authenticated-User-Email")',mode='eval').body
    ns=dict(self.ns);exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'antes590-explicito','exec'),ns)
    return types.MethodType(ns[nombre],self.h)
 def test_cfemail_antes_sustituye_ahora_se_ignora(self):
    self.h.headers['Cf-Access-Authenticated-User-Email']=self.dir['correo']
    self.assertEqual(self.legado('_quien')({})[0]['id'],self.dir['id'])
    r,v,e=self.h._quien({});self.assertIsNone(e);self.assertEqual(r['id'],self.account['id'])
    self.assertFalse(P.ver(r,{'tipo':'ver_como'},P.contexto(r,self.e.crudo))['ok'])
    self.assertEqual(self.validaciones,[])
 def test_peer_remoto_antes_admitido_ahora_host_y_identidad_deniegan(self):
    self.h.client_address=('192.0.2.40',12000)
    self.assertTrue(self.legado('host_ok')())
    self.assertFalse(self.h.host_ok());self.assertEqual(self.h.do_GET()[0],403)
    self.assertEqual(self.h._quien({})[2][0],403)
 def test_host_ajeno_se_deniega_antes_datos(self):
    self.h.headers['Host']='otro.example.invalid:8772'
    self.assertFalse(self.h.host_ok());self.assertEqual(self.h.do_GET()[0],403)
 def test_forwarded_no_se_usa_como_identidad_por_si_solo(self):
    self.h.headers={'Host':'localhost:8772','X-Forwarded-For':'127.0.0.1','X-Forwarded-Email':self.dir['correo']}
    self.assertEqual(self.h._quien({})[2][0],401)
 def test_identidad_local_explicit_y_cookie_legitimas(self):
    for headers,q in [({'Host':'localhost:8772','X-RO-Yo':self.account['id']},{}),({'Host':'localhost:8772'},{'yo':[self.account['id']]}),({'Host':'localhost:8772','Cookie':'ro_yo='+self.account['id']},{})]:
      self.h.headers=headers;self.assertEqual(self.h._quien(q)[0]['id'],self.account['id'])
 def test_cfemail_solo_no_identifica(self):
    self.h.headers={'Host':'localhost:8772','Cf-Access-Authenticated-User-Email':self.dir['correo']}
    self.assertEqual(self.h._quien({})[2][0],401)
 def test_canonica_baja_duplicada_no_revive(self):
    self.h.headers['X-RO-Yo']=self.dir['id']
    self.h.headers['Cf-Access-Authenticated-User-Email']=self.account['correo']
    self.dir['estado']='baja';self.assertEqual(self.h._quien({})[2][0],403)
    self.dir['estado']='activo';self.rows.append(dict(self.dir));self.assertEqual(self.h._quien({})[2][0],403)
 def test_peer_desconocido_invalido_y_forwarded_no_lo_sustituyen(self):
    self.h.headers['X-Forwarded-For']='127.0.0.1'
    for peer in (None,(),[],{},'127.0.0.1',('192.0.2.4',12000)):
      self.h.client_address=peer;self.assertFalse(self.h.host_ok());self.assertEqual(self.h._quien({})[2][0],403)
 def test_loopback_ipv6_y_forwarded_conservan_local(self):
    self.h.client_address=('::1',12000);self.h.headers['X-Forwarded-For']='192.0.2.4'
    self.assertTrue(self.h.host_ok());self.assertEqual(self.h._quien({})[0]['id'],self.account['id'])
    self.assertEqual(self.h.do_GET()[0],200)
 def test_servidor_no_fallback_a_cfemail_raw_yo_o_cookie(self):
    self.access.activo=lambda:True
    self.h.headers.update({'Cf-Access-Authenticated-User-Email':self.dir['correo'],'Cookie':'ro_yo='+self.dir['id']})
    self.assertEqual(self.h._quien({'yo':[self.dir['id']]})[2][0],403);self.assertEqual(len(self.validaciones),1)
 def test_servidor_usa_resultado_validador_y_canon_actual(self):
    self.h.client_address=('192.0.2.4',12000)
    self.access.activo=lambda:True;self.access.correo_validado=lambda h:(self.account['correo'],None)
    self.h.headers['Cf-Access-Authenticated-User-Email']=self.dir['correo']
    self.assertEqual(self.h._quien({'yo':[self.dir['id']]})[0]['id'],self.account['id'])
    self.account['activo']=False;self.assertEqual(self.h._quien({})[2][0],403)
if __name__=='__main__':unittest.main()
