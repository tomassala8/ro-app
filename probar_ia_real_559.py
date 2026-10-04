"""Fuente real/AST y dobles locales: ninguna lectura de llave ni conexión real."""
import ast
import os
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
import ia_real_559 as R
import ia_gasto as G

BASE = Path(__file__).resolve().parent

def funciones_ia():
    tree=ast.parse((BASE/'ia.py').read_text())
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('clave','estado','llamar')]
    env={'IA_REAL':R,'G':G,'os':os,'time':time,'sys':types.SimpleNamespace(platform='darwin'),
         'subprocess':types.SimpleNamespace(check_output=Mock(side_effect=AssertionError('llavero')),DEVNULL=None),
         '_CLAVE':{'t':time.time(),'v':'dummy-cached'},'MODELO':'dummy','MOTIVO_SIN_CLAVE':'sin clave'}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'ia.py real AST','exec'),env)
    return env

class Guardia559(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'interruptor.json'
        self.p=patch.object(R,'INTERRUPTOR',self.path);self.p.start()
        self.e=patch.dict(os.environ,{'RO_IA_REAL':'no','ANTHROPIC_API_KEY':'dummy','ANTHROPIC_API_KEY_RESPALDO':'dummy'},clear=True);self.e.start()
    def tearDown(self):self.e.stop();self.p.stop();self.temp.cleanup()
    def activar(self):
        os.environ['RO_IA_REAL']='si';self.path.write_text('{"ia_real":true,"activado_por":"tomas"}')
    def test_dos_requisitos_y_false_boolean(self):
        self.activar();self.assertTrue(R.autorizada())
        for env in ('no','SI','true',' si'):
            os.environ['RO_IA_REAL']=env;self.assertFalse(R.autorizada())
        os.environ['RO_IA_REAL']='si'
        for doc in ('{}','{"activado_por":"tomas"}','{"ia_real":1,"activado_por":"tomas"}',
                    '{"ia_real":true,"activado_por":"cecilia"}','[]','null','{',
                    '{"ia_real":false,"ia_real":true,"activado_por":"tomas"}',
                    '{"ia_real":true,"activado_por":"tomas","x":NaN}'):
            self.path.write_text(doc);self.assertFalse(R.autorizada(),doc)
        self.path.unlink();self.assertFalse(R.autorizada())
    def test_archivo_enlace_y_limite(self):
        self.activar();dest=self.path.with_name('real.json');self.path.rename(dest);self.path.symlink_to(dest)
        self.assertFalse(R.autorizada());self.path.unlink();self.path.write_text(' '*16385);self.assertFalse(R.autorizada())
    def test_off_no_lee_interruptor_ni_credenciales_cache(self):
        ia=funciones_ia()
        with patch.object(R.os,'open',side_effect=AssertionError('lectura archivo')),patch.object(os.environ,'get',wraps=os.environ.get) as get:
            self.assertIsNone(ia['clave']());self.assertFalse(ia['estado']()['conectada'])
            self.assertIsNone(G._clave_principal());self.assertIsNone(G.clave_respaldo())
            self.assertTrue(all(call.args[0]=='RO_IA_REAL' for call in get.call_args_list))
        ia['subprocess'].check_output.assert_not_called()
    def test_off_no_db_contador_reserva_modelo(self):
        fail=Mock(side_effect=AssertionError('efecto prohibido'))
        with patch.object(G,'S',types.SimpleNamespace(conectar=fail)),patch.object(G,'topes',fail),patch.object(G,'PROVEEDOR',types.SimpleNamespace(contar_entrada=fail,crear=fail)),patch.object(G,'apuntar',fail):
            self.assertEqual(G.modo()['modo'],'reglas')
            with self.assertRaises(G.SinGasto):G.llamar('x',{}, {})
            with self.assertRaises(G.SinGasto):G._comprobar_y_reservar('consejo','tomas','principal',1,{})
            fail.assert_not_called()
    def test_adaptador_directo_off(self):
        p=G.ProveedorAnthropic()
        for action in (lambda:p.crear('dummy','dummy','x',{}, {},'medium',1),lambda:p.lote_crear('dummy',[]),lambda:p.lote_resultados('dummy','dummy')):
            with self.assertRaises(G.SinGasto):action()
    def test_revocacion_invalida_incluso_cache(self):
        self.activar();ia=funciones_ia();self.assertEqual(ia['clave'](),'dummy-cached')
        self.path.write_text('{"ia_real":true,"activado_por":"otra"}')
        self.assertIsNone(ia['clave']());self.assertIsNone(G.clave_respaldo())
        with self.assertRaises(G.SinGasto):G.llamar('x',{}, {})
    def test_opt_in_no_elimina_barreras_tarifas(self):
        self.activar()
        with patch.object(G,'topes',lambda:{'mes_eur':1,'dia_eur':1}),patch.object(G,'gastado',lambda:{'mes':0,'dia':0}),patch.object(G,'_reservado',lambda:0):
            self.assertFalse(G.PRECIOS_VERIFICADOS);self.assertEqual(G.modo()['modo'],'reglas')
    def test_revocacion_durante_conteo_no_clave_ni_reserva(self):
        self.activar()
        def contar(*args,**kwargs):
            self.path.unlink()
            return {'acreditado':True,'modelo':'fixture','tokens':1}
        fail=Mock(side_effect=AssertionError('efecto prohibido'))
        with patch.object(G,'S',object()),patch.object(G,'peticion_actual',lambda:('tomas','tomas','mi-dia')),patch.object(G,'topes',lambda:{'consejo_pantallas':['mi-dia']}),patch.object(G,'modelo_de',lambda _: 'fixture'),patch.object(G,'precio',lambda _: {}),patch.object(G,'coste_maximo',lambda *a,**k:1),patch.object(G,'PROVEEDOR',types.SimpleNamespace(contar_entrada=contar,crear=fail)),patch.object(G,'_comprobar_y_reservar',fail):
            with self.assertRaises(G.SinGasto):G.llamar('x',{}, {},tarea='consejo')
            fail.assert_not_called()

    def test_preserva_formato_local_sin_provider(self):
        p=G.ProveedorAnthropic.peticion('dummy','instrucciones',{'texto':'fixture'},{},'medium',10)
        self.assertEqual(p['messages'][0]['role'],'user');self.assertEqual(p['max_tokens'],10)

if __name__=='__main__':unittest.main()
