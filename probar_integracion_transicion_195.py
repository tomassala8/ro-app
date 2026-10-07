"""Cadena real core→CAS191→intención194→wrapper193→recibo, DB sintética."""
import ast, copy, json, types, unittest
from pathlib import Path
from unittest.mock import patch
import mi_trabajo as M
import transiciones_mi_trabajo as T
from probar_recibo_transicion_193 import Recibo193

class Cadena(unittest.TestCase):
    conectar=Recibo193.conectar
    queue=Recibo193.queue
    count=Recibo193.count
    post=Recibo193.post
    def setUp(self):
        Recibo193.setUp(self)
        self.permiso=True
        self.actor={'id':'actor-fixture','estado':'activo','puestos':['account'],'correo':'actor@example.invalid'}
        self.D={'generado':'2026-10-03','tareas':[{'id':'task-fixture','cli':'cliente-fixture','persona_id':self.actor['id'],'lista_id':'list-fixture','estado':'abierto'}],
                'estados_lista':{'list-fixture':['abierto','cerrado']},'estados_detalle':{'list-fixture':[{'estado':'abierto','tipo':'open'},{'estado':'cerrado','tipo':'closed'}]}}
        raw={'personas':[self.actor],'clientes':[{'id':'cliente-fixture'}]}
        rules={'acciones_permitidas':{'_herramientas':['clickup'],'mi-trabajo':['cambiar_estado']},'acciones_con_efecto_fuera':{'clickup_tarea':['cambiar_estado']}}
        p=types.SimpleNamespace(REGLAS=rules,contexto=lambda*a:{},ver=lambda*a:{'ok':self.permiso},enlace_seguro=lambda*a:True)
        E=types.SimpleNamespace(crudo=raw,modulos={'mi-trabajo':{}},persona=lambda*a:self.actor)
        production=lambda*a:{'autores':{self.actor['id']},'cli':'cliente-fixture'}
        s=types.SimpleNamespace(E=E,ve_alguno=lambda*a:True,tarea_de_produccion=production,pieza_en_revision=lambda*a:None)
        import fuentes_verdad.clientes_activos as ACT
        from identidades_clickup_204 import preparar_autorizacion
        self.evidencia_autores=preparar_autorizacion([self.actor],
            [{'id':'cu-fixture','email':'actor@example.invalid'}],
            [{'id':'task-fixture','lista_id':'list-fixture','estado':'abierto','carpeta_id':'folder-fixture','asignados':[{'id':'cu-fixture'}]}],
            {'folder-fixture':['cliente-fixture']})
        for pat in (patch.object(M,'S',s),patch.object(M,'P',p),patch.object(M,'doc',lambda:self.D),patch.object(M,'SINC',None),
                    patch.object(M,'_fuente_autorizacion_tareas',lambda:self.evidencia_autores),patch.object(ACT,'es_activo_id',lambda*a:True)):
            pat.start();self.addCleanup(pat.stop)
        with self.conectar() as c:
            c.execute('DROP TABLE acciones')
            c.executescript(Path('schema_v2.sql').read_text())
            token=T.proyectar(self.D,'task-fixture',c)
        self.body['vista_previa'].update(token)
        self.body['texto']='Movimiento sintético'
        tree=ast.parse(Path('servir.py').read_text())
        validator=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='validar_accion')
        branch=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and '/api/acciones' in ast.unparse(n.test) and 'INSERT INTO acciones' in ast.unparse(n))
        fun=ast.parse('def api_post(self,ruta,real,persona,b):\n    pass').body[0];fun.body=[branch]
        ns={'P':p,'E':E,'ACT':ACT,'ve_alguno':s.ve_alguno,'_enlaces_malos':lambda*a:False,'pieza_en_revision':s.pieza_en_revision,'tarea_de_produccion':production,
            'registrar_agrupado':lambda*a:None,'registrar':lambda*a:None,'json':json,'conectar':self.conectar}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[validator,fun],type_ignores=[])),'core_real195','exec'),ns)
        class H:
            def responder(self,status,body,*a,**k):return status,body
            def _api_get(self,*a):return None
        H.validar_accion=ns['validar_accion'];H.api_post=ns['api_post']
        self.ns['enganchar'](H,types.SimpleNamespace(P=p,conectar=self.conectar));self.h=H()
    def test_cadena_replay_un_solo_recibo(self):
        code,a=self.post();self.assertEqual(code,200);self.assertTrue(a['recibo_durable'])
        code,b=self.post();self.assertEqual(code,200);self.assertEqual(a['recibo'],b['recibo'])
        self.assertTrue(b['intencion_guardada']['repetida']);self.assertEqual(self.count('acciones'),1)
    def test_dos_intenciones_version_antigua_no_sobrescriben(self):
        self.post();b=copy.deepcopy(self.body);b['intencion_id']='33333333-3333-4333-8333-333333333333'
        self.assertEqual(self.post(b)[0],409);self.assertEqual(self.count('acciones'),1)
    def test_cartera_revocada_no_guarda(self):
        self.permiso=False;self.assertEqual(self.post()[0],403);self.assertEqual(self.count('acciones'),0)
    def test_cola_fallida_reintento_misma_accion(self):
        self.queue_failure=True;r=self.post()[1];self.assertFalse(r['recibo_durable'])
        self.queue_failure=False;r=self.post()[1];self.assertTrue(r['recibo_durable']);self.assertEqual(self.count('acciones'),1)
    def test_ver_como_no_escribe(self):
        self.assertEqual(self.h.api_post('/api/acciones',self.actor,{'id':'otro'},self.body)[0],403)
        self.assertEqual(self.count('acciones'),0)

    def test_autor_solo_por_nombre_no_crea_accion(self):
        self.evidencia_autores['identidades'].clear()
        self.assertEqual(self.post()[0],403)
        self.assertEqual(self.count('acciones'),0)

    def test_carpeta_no_acredita_cliente_no_crea_accion(self):
        self.evidencia_autores['carpetas'].clear()
        self.assertEqual(self.post()[0],409)
        self.assertEqual(self.count('acciones'),0)

if __name__=='__main__':unittest.main()
