"""HTTP aislado: bloque real /api/modulo + 287, no arranque/DB de servir.
Autenticación y recorte base son fixtures explícitos; no certifica sesión Cloudflare.
"""
import ast,copy,json,os,re,sys,threading,unittest,urllib.request
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from types import SimpleNamespace as NS
from unittest.mock import patch
import evidencia_produccion_287 as M
import probar_evidencia_287 as F

class Transporte(unittest.TestCase):
 setUp=F.Pruebas.setUp
 tearDown=F.Pruebas.tearDown
 write=F.Pruebas.write
 def test_http_bloque_actual_con_dto_scoped_y_sin_cache(self):
  tree=ast.parse(Path(M.__file__).with_name('servir.py').read_text())
  cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Manejador')
  api=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_api_get')
  block=next(n for n in api.body if isinstance(n,ast.If) and any(isinstance(x,ast.Constant) and x.value=='/api/modulo/([\\w\\-/]+)' for x in ast.walk(n.test))) if False else None
  # Toma la asignación m del endpoint exacto y el if m asociado, no una réplica.
  index=next(i for i,n in enumerate(api.body) if isinstance(n,ast.Assign) and any(isinstance(x,ast.Constant) and x.value==r'/api/modulo/([\w\-/]+)' for x in ast.walk(n)))
  api.body=api.body[:3]+api.body[index:index+2]
  self.S.E.bloqueados=[];self.S.ACT.quitar_bajas=lambda d,rel:d
  self.catalogo['personas'].append({'id':'vista','estado':'activo'})
  self.S.P.ver=lambda p,q,cp:{'ok':not(p['id']=='vista' and q.get('cliente_id')=='a')}
  # Base ya recortada a la vista; el candidato contiene además b y no debe añadirla.
  def recortar(p,*args):return {'proyectos':[],'personas':[{'persona_id':'p'}]} if p['id']=='vista' else copy.deepcopy(self.dto)
  ns={'E':self.S.E,'P':self.S.P,'ACT':self.S.ACT,'os':os,'re':re,'json':json,'sys':NS(modules={'http_fixture':self.S}),'__name__':'http_fixture','_estado_fichero':lambda p:('fixture',),'version_datos':lambda:1,'puerta_modulo':lambda real,vista,rel:{'fichero':self.path,'conf':{},'nivel':'todo'},'CACHE_RESP':NS(leer=lambda key:(_ for _ in ()).throw(AssertionError('Candidato no debe leer cache'))),'leer_json_bueno':lambda p:(copy.deepcopy(self.dto),None),'recortar_modulo':recortar,'EVIDENCIA_PRODUCCION_287':M}
  exec(compile(ast.Module(body=[api],type_ignores=[]),'<api_modulo_actual>','exec'),ns)
  class H(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def responder(self,code,dto):
    raw=json.dumps(dto).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
   def do_GET(h):
    vista={'id':h.headers.get('X-Test-Vista','ops')}
    ns['_api_get'](h,h.path,{},self.actor,vista)
  server=ThreadingHTTPServer(('127.0.0.1',0),H);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  def get(view=None):
   req=urllib.request.Request('http://127.0.0.1:'+str(server.server_address[1])+'/api/modulo/produccion/produccion',headers={'X-Test-Vista':view or 'ops'})
   with urllib.request.urlopen(req,timeout=3) as r:self.assertEqual(r.status,200);return json.load(r)
  try:
   out=get();self.assertEqual(out['personas'][0]['_evidencia_equipo_275']['creadas_semana'],2);self.assertEqual([r['cliente_id'] for r in out['proyectos']],['a'])
   out=get('vista');self.assertEqual(out['proyectos'],[]);self.assertIsNone(out['personas'][0]['_evidencia_equipo_275']['creadas_semana'])
   self.active.remove('a');out=get();self.assertNotIn('_evidencia_produccion_275',out['proyectos'][0]);self.assertIsNone(out['personas'][0]['_evidencia_equipo_275']['creadas_semana'])
   self.S.E.nucleo_bloqueado=True
   with self.assertRaises(urllib.error.HTTPError) as ex:get()
   self.assertEqual(ex.exception.code,503)
  finally:server.shutdown();server.server_close();thread.join(2)

if __name__=='__main__':unittest.main()
