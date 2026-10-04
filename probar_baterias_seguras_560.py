"""Fixtures sintéticas. Extrae funciones fuente sin ejecutar las baterías ni sus datos/servidores."""
import ast
import contextlib
import importlib.util
import io
import json
import sqlite3
import tempfile
import unittest
import urllib.error
import types
from pathlib import Path

APP = Path(__file__).resolve().parent

def funciones(nombre, seleccion, entorno):
    tree = ast.parse((APP / nombre).read_text())
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in seleccion]
    assert {n.name for n in nodes} == set(seleccion)
    module = ast.Module(body=nodes, type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), nombre, 'exec'), entorno)
    return entorno

class Pruebas560(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        spec = importlib.util.spec_from_file_location('scanner_fixture560', APP / 'escaner_secretos.py')
        self.scanner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.scanner)
    def tearDown(self):
        self.tmp.cleanup()
    def test_carril_aislado_no_hereda_secretos_y_propaga_fallo(self):
        calls=[]
        def run(args, **kwargs):
            calls.append((args,kwargs))
            return types.SimpleNamespace(returncode=1 if len(calls)==2 else 0,
                                         stdout='',stderr='Fallo sintético')
        env={'Path':Path,'AQUI':APP,'os':types.SimpleNamespace(defpath='/usr/bin:/bin'),
             'sys':types.SimpleNamespace(executable='python-fixture'),
             'subprocess':types.SimpleNamespace(run=run,TimeoutExpired=TimeoutError)}
        funciones('pruebas_seguridad.py', ['ejecutar_aisladas_560'], env)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(env['ejecutar_aisladas_560'](),1)
        self.assertEqual(len(calls),29)
        self.assertEqual(Path(calls[3][0][1]).name,'probar_capturas_opiniones_565.py')
        self.assertIn('✓ probar_capturas_opiniones_565.py',out.getvalue())
        self.assertEqual(Path(calls[4][0][1]).name,'probar_secretos_calientes_567.py')
        self.assertIn('✓ probar_secretos_calientes_567.py',out.getvalue())
        self.assertEqual(Path(calls[5][0][1]).name,'probar_rastro_replace_569.py')
        self.assertIn('✓ probar_rastro_replace_569.py',out.getvalue())
        self.assertEqual(Path(calls[6][0][1]).name,'probar_confirmar_personas_572.py')
        self.assertIn('✓ probar_confirmar_personas_572.py',out.getvalue())
        self.assertEqual(Path(calls[7][0][1]).name,'probar_trabajador_resiliente_575.py')
        self.assertIn('✓ probar_trabajador_resiliente_575.py',out.getvalue())
        self.assertEqual([Path(c[0][1]).name for c in calls[8:]],
                         ['probar_ajustes_validaciones_579.py', 'probar_clasificacion_importes_580.py',
                          'probar_puertas_cliente_581.py', 'probar_lecturas_sincronia_585.py',
                          'probar_patrones_privados_587.py', 'probar_importes_acciones_decisiones_588.py',
                          'probar_recorte_modulo_589.py', 'probar_identidad_local_590.py',
                          'probar_evidencias_kpi_148.py', 'probar_evidencias_kpi_api_151.py',
                          'probar_informes_declarados_596.py', 'probar_acciones_tipadas_603.py',
                          'probar_decisiones_clientes_607.py', 'probar_resumen_informes_611.py', 'probar_cerebro_reservas_620.py',
                          'probar_puente_cerebro_reservas_621.py', 'probar_seo_fuentes_624.py',
                          'probar_seguridad_cerebro_seo_625.py', 'probar_recorte_estructurado_632.py',
                          'probar_eventos_cadencia_644.py', 'probar_lector_metodo_649.py'])
        for c in calls[8:]:
            self.assertIn('✓ '+Path(c[0][1]).name,out.getvalue())
        self.assertIn('✗ probar_bloque_seguridad_558.py',out.getvalue())
        for args,op in calls:
            self.assertEqual(args[0],'python-fixture')
            self.assertEqual(op['env']['RO_IA_REAL'],'no')
            self.assertEqual(set(op['env']),{'PATH','PYTHONIOENCODING','PYTHONDONTWRITEBYTECODE','RO_IA_REAL'})
        tree=ast.parse((APP/'pruebas_seguridad.py').read_text())
        guard=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.If) and '--aisladas' in ast.unparse(n.test))
        persons=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PERSONAS' for t in n.targets))
        self.assertLess(guard,persons)
    def scan(self, texto):
        p = self.root / 'fixture.txt'
        p.write_text(texto)
        return self.scanner.escanear_fichero(p)
    def test_lsof_preciso_no_email_false_positive(self):
        for texto in ['lsof -iTCP@127.0.0.1:8771 -sTCP:LISTEN', 'args=["lsof","-iTCP@10.2.3.4:8899"]', '`-iUDP@192.168.1.2`']:
            correo = next(rx for tipo,rx in self.scanner.PATRONES if tipo == 'correo')
            self.assertTrue(list(correo.finditer(texto)), 'reproduce coincidencia anterior')
            self.assertFalse(self.scan(texto))
    def test_no_whitelist_email_by_ip_or_arbitrary_domain(self):
        for texto in ['persona@' + '127.0.0.1', '-iTCP@' + 'dominio.test', '-iTCP@' + '127.0.0.1.evil', '-iTCP@' + '999.0.0.1', '-iTCP@' + '127.0.0.1:70000', '-iTCP@' + '127.0.0.1:abc', 'persona-iTCP@' + '127.0.0.1']:
            self.assertTrue(any(h['tipo'] == 'correo' for h in self.scan(texto)))
    def test_other_secrets_on_command_still_detected(self):
        texto = 'lsof -iTCP@127.0.0.1:8771 ' + 'sk-' + 'A'*24 + '\npassword: ' + 'Synthetic' + '9!'
        hs = self.scan(texto)
        self.assertTrue(any(h['tipo'] == 'clave_api' for h in hs))
        self.assertTrue(any(h['tipo'] == 'contrasena' for h in hs))
        self.assertFalse(any(h['tipo'] == 'correo' for h in hs))
    def entorno_m3(self):
        return funciones('pruebas_seguridad.py', ['_intentar_mutacion_m3', '_leer_fila_db'], {'sqlite3': sqlite3, 'Path': Path})
    def db(self, trigger=True):
        p = self.root / 'fixture.db'
        con = sqlite3.connect(p)
        try:
            con.execute('CREATE TABLE registro (id INTEGER PRIMARY KEY, quien TEXT)')
            con.execute("INSERT INTO registro VALUES(1,'actor-fixture')")
            if trigger:
                # Trigger tomado de fuente real; ningún import/bootstrap de servir ni esquema de negocio.
                s = (APP / 'schema_v2.sql').read_text()
                start = s.index('CREATE TRIGGER IF NOT EXISTS registro_sin_delete')
                end = s.index('END;', start) + 4
                con.executescript(s[start:end])
            con.commit()
        finally:
            con.close()
        return p
    def test_m3_trigger_exacto_closes_and_next_writer_works(self):
        e = self.entorno_m3(); p = self.db()
        for _ in range(4):
            ok,motivo = e['_intentar_mutacion_m3'](p, 'DELETE FROM registro', 'El rastro no se borra: crea una anulación')
            self.assertTrue(ok); self.assertEqual(motivo, 'rechazo del disparador esperado')
        con = sqlite3.connect(p, timeout=0.1)
        try:
            con.execute("INSERT INTO registro VALUES(2,'otro-fixture')"); con.commit()
        finally:
            con.close()
        self.assertEqual(e['_leer_fila_db'](p, 'SELECT count(*) FROM registro')[0], 2)
    def test_m3_locked_is_not_trigger_pass(self):
        e = self.entorno_m3();p = self.db();lock = sqlite3.connect(p)
        try:
            lock.execute('BEGIN IMMEDIATE')
            # La batería anterior habría marcado cualquier DatabaseError como PASS.
            with self.assertRaises(sqlite3.DatabaseError):
                con = sqlite3.connect(p, timeout=0.01)
                try: con.execute('DELETE FROM registro')
                finally: con.close()
            bloqueada,motivo = e['_intentar_mutacion_m3'](p, 'DELETE FROM registro', 'El rastro no se borra: crea una anulación')
            self.assertFalse(bloqueada);self.assertIn('distinto', motivo)
        finally:
            lock.rollback();lock.close()
    def test_m3_no_trigger_mutation_rolled_back_not_pass(self):
        e=self.entorno_m3();p=self.db(False)
        self.assertFalse(e['_intentar_mutacion_m3'](p,'DELETE FROM registro','El rastro no se borra: crea una anulación')[0])
        self.assertEqual(e['_leer_fila_db'](p,'SELECT count(*) FROM registro')[0],1)
    def test_m3_other_constraint_and_schema_do_not_pass(self):
        e=self.entorno_m3();p=self.db()
        self.assertFalse(e['_intentar_mutacion_m3'](p,'DELETE FROM no_existe','El rastro no se borra: crea una anulación')[0])
        self.assertFalse(e['_intentar_mutacion_m3'](p,"INSERT INTO registro VALUES(1,'duplicado')",'El rastro no se borra: crea una anulación')[0])
        self.assertFalse(e['_intentar_mutacion_m3'](p,'DELETE FROM registro','mensaje incorrecto')[0])
    def test_m3_missing_database_not_created(self):
        e=self.entorno_m3();p=self.root / "absente.db"
        self.assertFalse(e["_intentar_mutacion_m3"](p,"DELETE FROM registro","rechazo")[0])
        self.assertFalse(p.exists())
    def entorno_e0(self, get):
        return funciones('pruebas_e0.py', ['ok','leer_json_e0','sesion_e0'], {'json':json,'urllib':__import__('urllib'),'fallos':[],'get':get})
    def test_e0_missing_identity_fail_continues_valid_identity(self):
        good={'datos':{'clientes':[{'id':'c-fixture','detalle':False}],'carteraIds':[]}}
        def get(ruta,yo=None,como=None):
            return (403,json.dumps({'error':'denegado'})) if yo=='faltante' else (200,json.dumps(good))
        # Reproduce KeyError de la lectura directa anterior, con body403 sintético.
        with self.assertRaises(KeyError): json.loads(get('/api/sesion','faltante')[1])['datos']
        e=self.entorno_e0(get)
        out=io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertIsNone(e['sesion_e0']('faltante'))
            self.assertEqual(e['sesion_e0']('legitimo'),good['datos'])
            e['ok'](True,'comprobación independiente sigue')
        self.assertEqual(len(e['fallos']),1)
        self.assertIn('✗ ',out.getvalue());self.assertIn('403',out.getvalue());self.assertIn('✓ comprobación independiente sigue',out.getvalue())
    def test_e0_bad_shapes_missing_fields_and_invalid_json_are_fail(self):
        for payload in ['{roto',json.dumps({'datos':None}),json.dumps({'error':'fallo'}),json.dumps({'datos':{'clientes':{},'carteraIds':[]}})]:
            e=self.entorno_e0(lambda *args:(200,payload))
            with contextlib.redirect_stdout(io.StringIO()): self.assertIsNone(e['sesion_e0']('fixture'))
            self.assertEqual(len(e['fallos']),1)
    def test_e0_network_error_no_body_or_contacts_logged(self):
        def get(*args): raise urllib.error.URLError('mensaje privado no imprimible')
        e=self.entorno_e0(get);out=io.StringIO()
        with contextlib.redirect_stdout(out): self.assertIsNone(e['sesion_e0']('fixture'))
        self.assertEqual(len(e['fallos']),1);self.assertNotIn('mensaje privado',out.getvalue())
    def test_e0_foreign_loop_skips_only_invalid_response_not_next_actor(self):
        fuente=ast.parse((APP/'pruebas_e0.py').read_text())
        loop=next(n for n in fuente.body if isinstance(n,ast.For) and isinstance(n.iter,ast.Tuple) and [getattr(x,'value',None) for x in n.iter.elts]==['lucia','lina','setter_ana'])
        asked=[]
        def get(ruta,yo=None,como=None):
            asked.append((ruta,yo))
            if ruta=='/api/sesion': return (403,'{}') if yo=='lina' else (200,json.dumps({'datos':{'clientes':[{'id':'ajeno-fixture','detalle':False}],'carteraIds':[]}}))
            return 403,json.dumps({'error':'denegado'})
        e=self.entorno_e0(get)
        with contextlib.redirect_stdout(io.StringIO()): exec(compile(ast.fix_missing_locations(ast.Module(body=[loop],type_ignores=[])),'e0-real-loop','exec'),e)
        self.assertEqual(len(e['fallos']),1)
        self.assertIn(('/api/cliente/ajeno-fixture','lucia'),asked)
        self.assertIn(('/api/cliente/ajeno-fixture','setter_ana'),asked)
        self.assertNotIn(('/api/cliente/ajeno-fixture','lina'),asked)

if __name__=='__main__': unittest.main()
