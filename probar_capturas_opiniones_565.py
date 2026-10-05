import ast
import base64
import copy
import io
import sqlite3
import tempfile
import types
import unittest
from pathlib import Path
from PIL import Image
import permisos as P
import panel_direccion_privado_249 as PANEL
from capturas_opiniones_565 import permiso

AQUI = Path(__file__).parent

class Capturas565(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'sintetica.sqlite'
        self.a = dict(id='a', estado='activo', activo=True, puestos=['account'])
        self.b = dict(id='b', estado='activo', activo=True, puestos=['account'])
        self.E = types.SimpleNamespace(nucleo_bloqueado=False, modulos=P.cargar_modulos(),
            crudo=dict(personas=[self.a,self.b],clientes=[],asignaciones=[]))
        self.ACT = types.SimpleNamespace(estado=lambda: {'activos': set()})
        im = Image.new('RGB',(1,1),'white'); buf=io.BytesIO(); im.save(buf,format='JPEG')
        self.cap='data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode()
        with self.con() as c:
            c.execute('CREATE TABLE opiniones(id INTEGER, quien TEXT, ruta TEXT, captura TEXT)')
            c.execute('INSERT INTO opiniones VALUES (1,?,?,?)',('b','#/mi-dia/account?x=1',self.cap))
        self.mutacion=None
        tree=ast.parse((AQUI/'servir.py').read_text())
        branch=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and ast.unparse(n.test)=="ruta in ('/api/opiniones', '/api/opiniones/captura')")
        fn=ast.FunctionDef(name='leer',args=ast.arguments(posonlyargs=[],args=[ast.arg(arg=x) for x in ('self','real','persona','cp','ruta','q')],kwonlyargs=[],kw_defaults=[],defaults=[]),body=[copy.deepcopy(branch)],decorator_list=[])
        ns=dict(P=P,E=self.E,ACT=self.ACT,PANEL_PRIVADO_249=PANEL,conectar=self.con,opinion_a_json=self.dto)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'GET565actual','exec'),ns)
        self.leer=ns['leer']; self.handler=types.SimpleNamespace(responder=lambda c,d:(c,d))
    def tearDown(self): self.tmp.cleanup()
    def con(self):
        c=sqlite3.connect(str(self.path)); c.row_factory=sqlite3.Row; return c
    def dto(self,r,con_captura=False):
        if self.mutacion: self.mutacion()
        return dict(r)
    def get(self,real=None,vista=None):
        r=real or self.b; v=vista or self.b
        return self.leer(self.handler,r,v,P.contexto(v,self.E.crudo),'/api/opiniones/captura',{'id':['1']})
    def ruta(self,v):
        with self.con() as c: c.execute('UPDATE opiniones SET ruta=?',(v,))
    def test_owner_modulo_permitido_jpeg_real(self):
        c,d=self.get(); self.assertEqual(c,200); self.assertEqual(d['captura'],self.cap)
        with Image.open(io.BytesIO(base64.b64decode(d['captura'].split(',')[1]))) as im: self.assertEqual(im.size,(1,1))
    def test_real_y_vista_necesitan_modulo(self):
        self.ruta('#/uso-app')
        # opinión de b: incluso con propietario visto autorizado, real debe poder leer módulo.
        self.b['puestos']=['operaciones']; self.assertEqual(self.get(self.a,self.b)[0],403)
        self.a['puestos']=['operaciones']; self.b['puestos']=['account']; self.assertEqual(self.get(self.a,self.b)[0],403)
        self.b['puestos']=['operaciones']; self.assertEqual(self.get(self.a,self.b)[0],403)
        self.assertEqual(self.get()[0],200)
    def test_ruta_desconocida_no_fallback(self):
        for ruta in ('','#/no-existe','#/mi_dia','#/%6di-dia','https://ejemplo.invalid/#/mi-dia','#/','mi-dia',None):
            self.ruta(ruta); self.assertEqual(self.get()[0],403,ruta)
    def test_no_autor_sin_opiniones_ver(self): self.assertEqual(self.get(self.a,self.a)[0],403)
    def test_panel_nominal_no_rol_direccion(self):
        self.b['puestos']=['direccion']; self.ruta('#/panel-direccion'); self.assertEqual(self.get()[0],403)
        self.b['id']='tomas'
        with self.con() as c: c.execute("UPDATE opiniones SET quien='tomas'")
        self.assertEqual(self.get()[0],200)
        self.a['puestos']=['direccion']; self.assertEqual(self.get(self.a,self.b)[0],403)
    def test_canonicos_inactivos_duplicados_y_stale(self):
        self.b['activo']=False; self.assertEqual(self.get()[0],403); self.b['activo']=True
        self.E.crudo['personas'].append(dict(self.b)); self.assertEqual(self.get()[0],403)
        self.E.crudo['personas'].pop(); old=dict(self.b); self.b['puestos']=['setters']; self.assertEqual(self.get(old,old)[0],403)
    def test_resumen_no_acredita_bitmap(self):
        self.E.modulos['mi-dia']={'account':'resumen'}
        self.assertEqual(self.get()[0],403)
    def test_ficha_cliente_activo_detalle_y_revocacion(self):
        self.E.crudo['clientes']=[dict(id='c1',activo=True,estado='activo')]
        self.E.crudo['asignaciones']=[dict(cliente_id='c1',persona_id='b',papel='account',principal=True,confianza='confirmada')]
        self.ACT.es_activo_id=lambda cid:cid=='c1'
        self.ruta('#/ficha/c1/resumen')
        self.assertEqual(self.get()[0],200)
        self.mutacion=lambda:self.E.crudo['asignaciones'].clear()
        self.assertEqual(self.get()[0],403); self.mutacion=None
        for ruta in ('#/ficha','#/ficha/unknown','#/ficha/c1'):
            self.ruta(ruta); self.assertEqual(self.get()[0],403)
    def test_revocacion_durante_serializacion_no_imagen(self):
        for cambio in (lambda:self.b.update(activo=False),lambda:self.E.modulos.update({'mi-dia':{}}),lambda:self.E.crudo['personas'].append(dict(self.b))):
            self.b['activo']=True; self.E.crudo['personas']=[self.a,self.b]; self.E.modulos=P.cargar_modulos()
            self.mutacion=cambio; c,d=self.get(); self.assertEqual(c,403); self.assertNotIn('captura',d)

if __name__=='__main__': unittest.main()
