from contextlib import contextmanager
import copy
from io import BytesIO
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile
import informe_word_api as A
from pruebas_informe_word_149 import png

class WordAPI154(unittest.TestCase):
    def setUp(self):
        self.real={'id':'fixture-account','puestos':['account'],'estado':'activo'}
        self.vista={'id':'fixture-paid','puestos':['trafficker'],'estado':'activo'}
        self.cl={'id':'fixture','nombre':'Cliente ficticio','servicios':{'publicidad':'sí'}}
        self.periodo={'id':'2026-09','desde':'2026-09-01','hasta':'2026-09-30'}
        self.raw={'clientes':[self.cl],'personas':[self.real,self.vista],'asignaciones':[]}
        self.permiso=True;self.version=1;self.bloqueado=False;self.logo=(png(),'image/png','sha')
        self.docs={'informe/comun':{'periodos':[self.periodo]},'informe/c_2026-09/fixture':{'_meta':{'periodo':self.periodo.copy()},'filas':[{'cliente_id':'fixture','ga4':{'actual':{'usuarios':15}},'meta':{'actual':{'leads':3}},'fuentes':{}}]},'mi_trabajo/mi_trabajo':None}
        self.db=sqlite3.connect(':memory:');self.db.row_factory=sqlite3.Row
        self.db.execute('CREATE TABLE acciones(id INTEGER,creada TEXT,vista_previa TEXT,modulo TEXT,cliente_id TEXT,tipo TEXT)')
        self.db.execute('INSERT INTO acciones VALUES (1,?,?,?,?,?)',('2026-10-03', '{"periodo":"2026-09","apartados":{"mes":"Resumen correcto","funciona":"Funciona","no_funciona":"Por revisar","pasos":"Próximos pasos","perdidas":"Sin detalle personal"}}',A.MOD,'fixture','analisis_mes'));self.db.commit()
        @contextmanager
        def con():yield self.db
        @contextmanager
        def mirando(*args):yield
        self.S=SimpleNamespace(E=SimpleNamespace(crudo=self.raw,nucleo_bloqueado=False),ACT=SimpleNamespace(es_activo_id=lambda cid:cid=='fixture'),
          P=SimpleNamespace(contexto=lambda *a:{},ver=lambda p,*a:{'ok':self.permiso},mirando_como=mirando),
          ve_alguno=lambda p,m:self.permiso,version_datos=lambda:self.version,modulo_recortado=lambda r,v,c,rel:copy.deepcopy(self.docs.get(rel)),
          conectar=con,recortar_modulo=lambda p,c,d:d,logo_de=lambda cid:self.logo,AQUI=Path('/fixture-no-data'))
        class H:
            def __init__(self):self.headers={};self.wfile=BytesIO();self.status=None
            def _api_get(self,*a):return 404,{}
            def responder(self,status,body):self.status=status;return status,body
            def send_response(self,status):self.status=status
            def send_header(self,k,v):self.headers[k]=v
            def end_headers(self):pass
        self.H=H;A.enganchar(H,self.S);self.q={'cliente_id':['fixture'],'periodo_id':['2026-09']}
    def tearDown(self):self.db.close()
    def run_get(self,real=None,vista=None,q=None):
        h=self.H();r=h._api_get(A.RUTA,q or self.q,real or self.real,vista or self.real);return h,r
    def body(self,h):
        with zipfile.ZipFile(BytesIO(h.wfile.getvalue())) as z:return z.read('word/document.xml').decode()
    def test_exporta_blob_privado_narrativa_tabla_sin_mutacion(self):
        antes=self.db.total_changes;h,_=self.run_get()
        self.assertEqual(h.status,200);self.assertEqual(h.headers['Cache-Control'],'private, no-store')
        self.assertIn('Resumen correcto',self.body(h));self.assertIn('<w:tbl>',self.body(h))
        self.assertEqual(self.db.total_changes,antes)
    def test_real_vista_y_filtro_restringen_bloques(self):
        h,_=self.run_get(vista=self.vista)
        self.assertEqual(h.status,200);self.assertNotIn('<w:t xml:space="preserve">Usuarios</w:t>',self.body(h))
        self.permiso=False;self.assertEqual(self.run_get()[0].status,403)
    def test_act_y_cliente_unico(self):
        self.S.ACT.es_activo_id=lambda _:False;self.assertEqual(self.run_get()[0].status,403)
        self.S.ACT.es_activo_id=lambda _:True;self.raw['clientes'].append(self.cl.copy());self.assertEqual(self.run_get()[0].status,403)
    def test_periodo_exacto_no_reemplaza_y_payload_ajeno(self):
        self.assertEqual(self.run_get(q={**self.q,'persona':['fixture-paid']})[0].status,400)
        self.assertEqual(self.run_get(q={'cliente_id':['fixture'],'periodo_id':['2026-08']})[0].status,400)
        self.docs['informe/c_2026-09/fixture']['_meta']['periodo']['id']='2026-08'
        self.assertEqual(self.run_get()[0].status,409)
    def test_source_ajeno_privado_y_logo_bloquean(self):
        fila=self.docs['informe/c_2026-09/fixture']['filas'][0]
        fila['cliente_id']='ajeno';self.assertEqual(self.run_get()[0].status,409);fila['cliente_id']='fixture'
        fila['avisos']=[{'color':'rojo','tipo':'otro_cliente'}];self.assertEqual(self.run_get()[0].status,409);fila['avisos']=[]
        self.logo=None;h,_=self.run_get();self.assertEqual(h.status,409);self.assertEqual(h.wfile.getvalue(),b'')
    def test_permiso_real_ledger_service_revocado(self):
        import permisos as P
        self.S.P=P
        self.raw['asignaciones']=[{'persona_id':self.real['id'],'cliente_id':'fixture','silla':'account'},
                                 {'persona_id':self.vista['id'],'cliente_id':'fixture','silla':'trafficker'}]
        h,_=self.run_get(vista=self.vista);self.assertEqual(h.status,200)
        self.cl['servicios']['publicidad']='no'
        with patch.object(self.S,'modulo_recortado',side_effect=AssertionError('No leer')):
            self.assertEqual(self.run_get(vista=self.vista)[0].status,403)
    def test_analisis_anulado_y_periodo_exacto(self):
        filas=[{'id':1,'creada':'2026-10-01','vista_previa':{'periodo':'2026-09','apartados':{'mes':'Anulado'}}},
               {'id':2,'creada':'2026-10-02','vista_previa':{'anula':1}},
               {'id':3,'creada':'2026-10-03','vista_previa':{'periodo':'2026-08','apartados':{'mes':'Otro periodo'}}}]
        self.assertEqual(A.analisis(filas,'2026-09'),{})
    def test_logo_raster_conversion_sin_metadatos(self):
        from PIL import Image,PngImagePlugin
        im=Image.new('RGB',(3,2),(12,34,56));out=BytesIO()
        info=PngImagePlugin.PngInfo();info.add_text('privado','lead@example.com')
        im.save(out,format='PNG',pnginfo=info)
        convertido=A.logo_png(out.getvalue())
        self.assertNotIn(b'lead@example.com',convertido)
        self.assertEqual(A.W.png_valido(convertido),(3,2))
        for formato in ('JPEG','GIF','WEBP'):
            out=BytesIO();im.save(out,format=formato)
            self.assertEqual(A.W.png_valido(A.logo_png(out.getvalue())),(3,2))
    def test_binario_no_bypassea_privacidad_contratos(self):
        v='Resumen https://sign.zoho.eu/document/abc y https://docs.google.com/document/d/fixturecontractid/edit'
        self.db.execute('UPDATE acciones SET vista_previa=?',(__import__('json').dumps({'periodo':'2026-09','apartados':{'mes':v}}),));self.db.commit()
        with patch('contratos_privados.indice_confirmado',return_value=frozenset({'fixturecontractid'})):
            h,_=self.run_get();self.assertEqual(h.status,200)
        body=self.body(h)
        self.assertNotIn('sign.zoho',body);self.assertNotIn('fixturecontractid',body)
        self.assertIn('Documento reservado',body)
    def test_canonicos_duplicados_inactivos_y_snapshot_no_autoriza(self):
        stale={'id':self.real['id'],'puestos':['direccion'],'estado':'activo'}
        self.raw['personas'][0]['puestos']=['account']
        with patch.object(self.S,'ve_alguno',side_effect=lambda p,m:p['puestos']==['direccion']):
            self.assertEqual(self.run_get(real=stale)[0].status,403)
        self.raw['personas'].append(self.real.copy())
        self.assertEqual(self.run_get()[0].status,403);self.raw['personas'].pop()
        for cambio in ({'estado':None},{'estado':'inactivo'},{'activo':False}):
            previo=self.real.copy();self.real.update(cambio)
            self.assertEqual(self.run_get()[0].status,403)
            self.real.clear();self.real.update(previo)
    def test_revocacion_canonica_sin_cambio_version(self):
        def revocar(_):
            self.raw['personas'][0]={**self.real,'puestos':['trafficker']}
            return self.logo
        self.S.logo_de=revocar
        h,_=self.run_get();self.assertEqual(h.status,403);self.assertEqual(h.wfile.getvalue(),b'')
    def test_revocacion_durante_logo_no_blob(self):
        def revocar(_):self.version+=1;return self.logo
        self.S.logo_de=revocar;h,_=self.run_get();self.assertEqual(h.status,403);self.assertEqual(h.wfile.getvalue(),b'')
    def test_analisis_otro_periodo_no_importado_y_PII_bloquea(self):
        self.db.execute('UPDATE acciones SET vista_previa=?',('{"periodo":"2026-08","apartados":{"mes":"NO AGOSTO"}}',));self.db.commit()
        h,_=self.run_get();self.assertNotIn('NO AGOSTO',self.body(h));self.assertIn('pendiente',self.body(h))
        self.db.execute('UPDATE acciones SET vista_previa=?',('{"periodo":"2026-09","apartados":{"mes":"lead@example.com"}}',));self.db.commit()
        self.assertEqual(self.run_get()[0].status,409)
    def test_nucleo_y_identidad_desconocida_antes_fuentes(self):
        self.S.E.nucleo_bloqueado=True
        with patch.object(self.S,'modulo_recortado',side_effect=AssertionError('No leer')):self.assertEqual(self.run_get()[0].status,403)
        self.S.E.nucleo_bloqueado=False
        with patch.object(self.S,'modulo_recortado',side_effect=AssertionError('No leer')):self.assertEqual(self.run_get(real={'id':'ajeno','puestos':['direccion']})[0].status,403)

if __name__=='__main__':unittest.main()
