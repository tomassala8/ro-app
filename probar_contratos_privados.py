import ast,collections,concurrent.futures,gzip,io,json,re,tempfile,threading,unittest
from pathlib import Path
from contratos_privados import enganchar,sanear,permitido,indice_confirmado

T={'id':'tomas','puestos':['direccion']};O={'id':'ops','puestos':['direccion','operaciones']};A={'id':'account'}
DOC='1ContratoConfirmadoDriveId'
DATA={'fuentes':{'contrato':{'texto':'contenido reservado','url':'https://docs.google.com/document/d/NoIndice123/edit'},'reuniones':{'datos':[{'tipo':'incidencia','texto':'Queja sobre contrato, revisar SOP','url':'https://drive.google.com/drive/folders/Generico123'}]}},
 'adjuntos':[{'tipo':'contrato_firmado','texto':'privado'},{'titulo':'CONTRATO DE PRESTACIÓN DE SERVICIOS','url':'https://docs.google.com/document/d/Desconocido123/edit'},{'tipo':'informe','url':'https://drive.google.com/file/d/'+DOC+'/view'}],
 'servicios_contratados':{'seo':'sí'},'nota':'Queja: revisar https://sign.zoho.eu/zs/privado y responder',
 'drive_general':'https://drive.google.com/drive/folders/Generico123','objetivos':{'tipo':'comercial','valor':3}}

class Contratos(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.indice=Path(self.tmp.name)/'indice.json'
  self.indice.write_text(json.dumps({'documentos':[{'tipo':'contrato_firmado','confirmado':True,'fuente':'fixture confirmada','proveedor':'google_drive','document_id':DOC}]}))
 def handler(self):
  class H:
   def __init__(self):self.posts=[]
   def responder(self,code,obj):return code,obj
   def responder_guardado(self,e):return 200,json.loads(e['cuerpo']),e['etag']
   def _api_get(self,ruta,q,real,vista):
    if ruta=='/fallo':raise RuntimeError('fixture')
    if ruta=='/cache':return self.responder_guardado({'cuerpo':json.dumps(DATA).encode(),'etag':'original','gzip':b'contenido sin recortar'})
    return self.responder(200,DATA)
   def api_post(self,ruta,real,vista,b):self.posts.append(b);return self.responder(201,b)
  enganchar(H,indice=self.indice);return H()
 def test_identidad_exacta_real_y_vista(self):
  self.assertTrue(permitido(T,T))
  for real,vista in ((T,O),(O,T),(O,O),(A,A),({'id':'tomas-falso'},T),(None,T)):
   self.assertFalse(permitido(real,vista))
 def test_roles_y_vercomo_no_elevan(self):
  h=self.handler()
  for real,vista in ((T,O),(O,T),(O,O),(A,A)):
   code,out=h._api_get('/api/cliente/a',{},real,vista)
   self.assertEqual(code,200);self.assertNotIn('contrato',out['fuentes'])
   texto=json.dumps(out);self.assertNotIn('contenido reservado',texto);self.assertNotIn('sign.zoho',texto)
   self.assertNotIn('NoIndice123',texto);self.assertNotIn('Desconocido123',texto);self.assertNotIn(DOC,texto)
   self.assertIn('Queja sobre contrato',texto);self.assertIn('servicios_contratados',texto);self.assertIn('Generico123',texto)
 def test_tomas_tomas_conserva_y_no_muta_original(self):
  h=self.handler();_,out=h._api_get('/api/cliente/a',{},T,T)
  self.assertEqual(out,DATA);h._api_get('/api/cliente/a',{},O,O);self.assertIn('contrato',DATA['fuentes'])
 def test_rutas_docs_bloqueadas_y_desconocidas_no_se_crean(self):
  h=self.handler()
  for ruta in ('/api/contratos','/api/cliente/a/contrato','/api/contratos_sign/123'):
   self.assertEqual(h._api_get(ruta,{},T,O)[0],403)
   self.assertEqual(h._api_get(ruta,{},O,T)[0],403)
 def test_cache_filtrada_responde_normal_sin_etag_ajeno(self):
  h=self.handler();result=h._api_get('/cache',{},O,O)
  self.assertEqual(len(result),2);code,out=result
  self.assertEqual(code,200);self.assertNotIn('contrato',out['fuentes'])
  self.assertEqual(h._api_get('/cache',{},O,O),result)
  self.assertEqual(h._api_get('/cache',{},T,T)[2],'original')
 def test_post_no_guarda_metadata_contrato_ni_link_reservado(self):
  h=self.handler()
  for body in ({'contrato':{'texto':'privado'}},{'nota':'https://sign.zoho.com/id'},{'url':'https://drive.google.com/file/d/'+DOC+'/view'}):
   self.assertEqual(h.api_post('/api/acciones',O,O,body)[0],403)
  self.assertEqual(h.posts,[])
  self.assertEqual(h.api_post('/api/acciones',O,O,{'nota':'Queja sobre contrato, revisar SOP'})[0],201)
  self.assertEqual(h.api_post('/api/acciones',T,T,{'contrato':{'texto':'privado'}})[0],201)
 def test_sin_contexto_cierra_privacidad(self):
  _,out=self.handler().responder(200,DATA);self.assertNotIn('contrato',out['fuentes'])
 def test_contexto_no_se_filtra_entre_threads_ni_tras_excepcion(self):
  h=self.handler()
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
   tasks=[pool.submit(h._api_get,'/api/cliente/a',{},*( (T,T) if i%2 else (O,O))) for i in range(20)]
   for i,f in enumerate(tasks):self.assertEqual('contrato' in f.result()[1]['fuentes'],bool(i%2))
  with self.assertRaises(RuntimeError):h._api_get('/fallo',{},T,T)
  self.assertNotIn('contrato',h.responder(200,DATA)[1]['fuentes'])
 def test_indice_no_adivina_y_no_drive_generico(self):
  self.indice.write_text(json.dumps({'documentos':[{'tipo':'contrato_firmado','confirmado':False,'fuente':'fixture','proveedor':'google_drive','document_id':DOC}]}))
  self.assertEqual(indice_confirmado(self.indice),frozenset())
  out=sanear({'url':'https://drive.google.com/file/d/'+DOC+'/view'})
  self.assertIsNotNone(out['url'])
 def test_claves_camelcase_sin_borrar_sop(self):
  out=sanear({'contratoUrl':'privado','signedDocument':'privado','urlContrato':'privado','sop':'Cómo revisar un contrato','serviciosContratados':['seo']})
  self.assertEqual(out,{'sop':'Cómo revisar un contrato','serviciosContratados':['seo']})
 def test_texto_con_url_al_inicio_preserva_resto(self):
  out=sanear('https://sign.zoho.com/id Queja comercial ordinaria')
  self.assertIn('Queja comercial',out);self.assertNotIn('https://',out)

class CompresionServidor(unittest.TestCase):
 def test_metodos_reales_gzip_privacidad_sin_contabilidad_fantasma(self):
  # AST real de servir, sin importarlo: no inicialización/DB ni red.
  source=Path(__file__).with_name('servir.py').read_text();tree=ast.parse(source)
  clases={n.name:n for n in tree.body if isinstance(n,ast.ClassDef)}
  comprimir=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='comprimir')
  clase=clases['Manejador']
  funcs=[n for n in clase.body if isinstance(n,ast.FunctionDef) and n.name in ('codificacion','responder_guardado','responder')]
  raw=ast.ClassDef(name='RawHandler',bases=[],keywords=[],body=funcs,decorator_list=[])
  programa=ast.fix_missing_locations(ast.Module(body=[comprimir,clases['CacheRespuestas'],raw],type_ignores=[]))
  scope={'json':json,'re':re,'threading':threading,'OrderedDict':collections.OrderedDict,'_BROTLI':None}
  exec(compile(programa,'servir_real_ast','exec'),scope)
  cache=scope['CacheRespuestas']();scope['CACHE_RESP']=cache
  body={'contratos':[{'texto':'RESERVADO_CONTRATO'}],'trabajo':'Texto operativo '*250}
  entry={'cuerpo':json.dumps(body).encode(),'etag':'"original"'};cache.guardar('fixture',entry)
  antes=cache.bytes;tam=entry['tam']
  class H(scope['RawHandler']):
   def __init__(self,encoding='gzip'):
    self.headers={'Accept-Encoding':encoding,'If-None-Match':'"original"'};self.out=[];self.wfile=io.BytesIO();self.code=None
   def _api_get(self,*args):return self.responder_guardado(entry)
   def api_post(self,*args):raise AssertionError('No POST')
   def send_response(self,code):self.code=code
   def send_header(self,k,v):self.out.append((k,v))
   def end_headers(self):pass
  enganchar(H,indice=Path('/ruta_inexistente_fixture'))
  for real,vista in ((O,O),(T,O),(O,T),(A,A)):
   for encoding in ('gzip','','br, gzip'):
    h=H(encoding);h._api_get('/api/modulo/fixture/fixture',{},real,vista)
    self.assertEqual(h.code,200);headers=dict(h.out)
    payload=h.wfile.getvalue()
    if 'gzip' in encoding:
     self.assertEqual(headers['Content-Encoding'],'gzip');payload=gzip.decompress(payload)
    else:self.assertNotIn('Content-Encoding',headers)
    doc=json.loads(payload);self.assertNotIn('contratos',doc);self.assertEqual(doc['trabajo'],body['trabajo'])
    self.assertNotIn('ETag',headers);self.assertEqual(headers['Cache-Control'],'no-store')
    self.assertEqual(cache.bytes,antes);self.assertEqual(entry['tam'],tam);self.assertNotIn('gzip',entry)
  # El ETag original sigue válido para Tomás; la proyección ajena nunca lo usa.
  h=H();h._api_get('/api/modulo/fixture/fixture',{},T,T)
  self.assertEqual(h.code,304);self.assertEqual(h.wfile.getvalue(),b'')
  h=H();h.headers.pop('If-None-Match');h._api_get('/api/modulo/fixture/fixture',{},T,T)
  self.assertEqual(h.code,200);doc=json.loads(gzip.decompress(h.wfile.getvalue()))
  self.assertIn('contratos',doc);self.assertGreater(cache.bytes,antes)
  # Las respuestas cacheadas sin material contractual conservan ruta/ETag/304.
  entry={'cuerpo':json.dumps({'trabajo':'operativo'}).encode(),'etag':'"limpio"'};cache.guardar('limpio',entry)
  h=H();h.headers['If-None-Match']='"limpio"';h._api_get('/api/modulo/fixture/fixture',{},A,A)
  self.assertEqual(h.code,304);self.assertEqual(h.wfile.getvalue(),b'')

if __name__=='__main__':unittest.main()
