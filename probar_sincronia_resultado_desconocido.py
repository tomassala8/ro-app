"""Motor real con proveedor sintético y SQLite temporal; sin red ni credenciales."""
import ast, json, sqlite3, tempfile, types, unittest
from pathlib import Path
from datetime import datetime, timedelta
def cargar_candidato(parche=True):
    # Ejecutar sólo funciones/constantes del módulo con proveedor fixture.
    # No imports/enganches/bootstrap del servidor ni acceso a credenciales.
    texto = (Path(__file__).parent / 'sincronia.py').read_text()
    compile(texto, '<modulo-completo>', 'exec')
    tree = ast.parse(texto)
    nombres = {'paso', 'crear_cambio', 'fila', 'pasos_de', 'estado_actual', 'detalle_de',
               'intentos', 'base_vigente', 'aplicado', 'valor_app', 'es_conflicto',
               'preparar', 'ejecutar', 'reclamar_escritura', '_error', 'verificar', 'bloqueado_por_anterior', 'ErrorSinc',
               'ahora_utc', 'txt_hora', 'leer_hora', 'iso_z', 'norm', 'marca', 'marcar_conflicto'}
    constantes = {'TABLAS_SQL', 'ESTADOS', 'SEGUROS', 'LLAVE', 'LLANO', 'CONF_DEF', 'TEXTO_PENDIENTE'}
    seleccion = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in nombres
                 or isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in constantes for t in n.targets)]
    import re, os
    from datetime import timezone
    ns = dict(json=json, sqlite3=sqlite3, datetime=datetime, timedelta=timedelta,
              timezone=timezone, re=re, os=types.SimpleNamespace(environ={}))
    exec(compile(ast.Module(body=seleccion, type_ignores=[]), '<candidato>', 'exec'), ns)
    ns.update(conf=lambda: ns['CONF_DEF'], canal_real=lambda _: True, avisar=lambda *a, **kw: None)
    return types.SimpleNamespace(**ns)

class Sincronia(unittest.TestCase):

    def setUp(self):
        self.s = cargar_candidato()
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / 'fixture.db')
        self.con = sqlite3.connect(self.db)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(self.s.TABLAS_SQL)
        self.now = datetime(2026, 10, 3, 10)
        self.cid = self.crear('a')

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def crear(self, clave):
        cid = self.s.crear_cambio(self.con, clave=clave, quien='actor_fixture', canal='clickup', tipo='comentario', objeto={'tipo': 'tarea', 'ref': 'task_fixture'}, cambio={'campo': 'comentario', 'texto': 'fixture'}, modo='prueba', hora=self.now)[0]
        self.con.commit()
        return cid

    def proveedor(self, tipo=None, aplica=False, lectura_error=False):
        s = self.s

        class Fixture:
            nombre = 'fixture'
            real = False
            writes = 0
            presente = False

            def leer(p, c):
                if lectura_error:
                    raise s.ErrorSinc('tiempo')
                return {'marcas': {s.marca(c['clave'])} if p.presente else set()}

            def aplicar(p, c):
                p.writes += 1
                p.presente = aplica
                if tipo:
                    raise s.ErrorSinc(tipo)
        return Fixture()

    def test_timeout_aplicado_confirma_sin_duplicar(self):
        p = self.proveedor('tiempo', True)
        self.assertEqual(self.s.ejecutar(self.con, self.cid, p, ahora=self.now), 'enviado')
        self.assertEqual(self.s.verificar(self.con, self.cid, p, ahora=self.now), 'confirmado')
        self.s.ejecutar(self.con, self.cid, p)
        self.assertEqual(p.writes, 1)

    def test_timeout_ausencia_no_acredita_reintento(self):
        p = self.proveedor('tiempo')
        self.s.ejecutar(self.con, self.cid, p, ahora=self.now)
        self.assertEqual(self.s.verificar(self.con, self.cid, p, ahora=self.now + timedelta(days=1)), 'enviado')
        otro = self.crear('b')
        self.assertEqual(self.s.bloqueado_por_anterior(self.con, self.s.fila(self.con, otro)), self.cid)
        self.s.ejecutar(self.con, self.cid, p)
        self.assertEqual(p.writes, 1)

    def test_resultado_incierto_persistido_tras_reabrir(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = str(Path(carpeta) / 'fixture.db')
            c = sqlite3.connect(ruta)
            c.row_factory = sqlite3.Row
            c.executescript(self.s.TABLAS_SQL)
            cid = self.s.crear_cambio(c, clave='persistencia', quien='actor_fixture', canal='clickup', tipo='comentario', objeto={'tipo': 'tarea', 'ref': 'task_fixture'}, cambio={'campo': 'comentario', 'texto': 'fixture'}, modo='prueba')[0]
            c.commit()
            self.s.ejecutar(c, cid, self.proveedor('tiempo'), ahora=self.now)
            c.commit()
            c.close()
            c = sqlite3.connect(ruta)
            c.row_factory = sqlite3.Row
            try:
                act = self.s.estado_actual(c, cid)
                self.assertTrue(self.s.detalle_de(act)['resultado_desconocido'])
                self.assertEqual(act['estado'], 'enviado')
            finally:
                c.close()

    def test_error_lectura_previa_reintenta_sin_escribir(self):
        p = self.proveedor(lectura_error=True)
        self.assertEqual(self.s.ejecutar(self.con, self.cid, p, ahora=self.now), 'pendiente')
        self.assertEqual(p.writes, 0)

    def test_error_segunda_operacion_no_afirma_ausencia(self):
        p = self.proveedor('permiso', True)
        self.assertEqual(self.s.ejecutar(self.con, self.cid, p, ahora=self.now), 'enviado')
        self.assertEqual(self.s.verificar(self.con, self.cid, p), 'confirmado')

    def test_exito_exige_lectura_posterior(self):
        p = self.proveedor(aplica=True)
        self.assertEqual(self.s.ejecutar(self.con, self.cid, p, ahora=self.now), 'confirmado')
        (cid, nuevo) = self.s.crear_cambio(self.con, clave='a', quien='actor_fixture', canal='clickup', tipo='comentario', objeto={'tipo': 'tarea', 'ref': 'task_fixture'}, cambio={'campo': 'comentario', 'texto': 'fixture'}, modo='prueba')
        self.assertEqual(cid, self.cid)
        self.assertFalse(nuevo)

    def test_conflicto_no_pisa_estado_nuevo(self):
        cid = self.s.crear_cambio(self.con, clave='estado', quien='actor_fixture', canal='clickup', tipo='estado', objeto={'tipo': 'tarea', 'ref': 'otra_tarea'}, cambio={'campo': 'estado', 'valor': 'done'}, base={'estado': 'open'}, modo='prueba', hora=self.now)[0]
        self.con.commit()
        p = self.proveedor()
        p.leer = lambda c: {'estado': 'review', 'actualizado': self.now + timedelta(minutes=1)}
        self.assertEqual(self.s.ejecutar(self.con, cid, p, ahora=self.now), 'conflicto')
        self.assertEqual(p.writes, 0)

    def test_claim_visible_antes_de_aplicar(self):
        p = self.proveedor(aplica=True)
        original = p.aplicar
        def aplicar(cambio):
            otra = sqlite3.connect(self.db); otra.row_factory = sqlite3.Row
            try:
                act = self.s.estado_actual(otra, self.cid)
                self.assertEqual(act['evento'], 'escritura_reclamada')
                self.assertTrue(self.s.detalle_de(act)['claim_durable'])
                self.assertFalse(self.con.in_transaction)
            finally:
                otra.close()
            original(cambio)
        p.aplicar = aplicar
        self.assertEqual(self.s.ejecutar(self.con,self.cid,p), 'confirmado')

    def test_caida_despues_de_efecto_reinicio_no_reenvia(self):
        class Caida(BaseException): pass
        p = self.proveedor(aplica=True)
        original = p.aplicar
        def aplicar(cambio):
            original(cambio)
            raise Caida()
        p.aplicar = aplicar
        with self.assertRaises(Caida):
            self.s.ejecutar(self.con,self.cid,p)
        self.con.close()  # Sin commit de ningún paso posterior al efecto.
        self.con = sqlite3.connect(self.db); self.con.row_factory = sqlite3.Row
        self.assertEqual(self.s.estado_actual(self.con,self.cid)['evento'],'escritura_reclamada')
        self.assertEqual(self.s.ejecutar(self.con,self.cid,p),'enviado')
        self.assertEqual(p.writes,1)
        self.assertEqual(self.s.verificar(self.con,self.cid,p),'confirmado')

    def test_caida_antes_de_efecto_tampoco_asume_ausencia(self):
        self.assertTrue(self.s.reclamar_escritura(self.con,self.cid,'fixture',0,self.now))
        self.con.close()
        self.con = sqlite3.connect(self.db); self.con.row_factory = sqlite3.Row
        p = self.proveedor()
        self.assertEqual(self.s.ejecutar(self.con,self.cid,p),'enviado')
        self.assertEqual(self.s.verificar(self.con,self.cid,p,ahora=self.now+timedelta(days=100)),'enviado')
        self.assertEqual(p.writes,0)

    def test_transaccion_ajena_no_commit_ni_efecto(self):
        self.con.execute('CREATE TABLE fixture_ajena (valor TEXT)'); self.con.commit()
        self.con.execute("INSERT INTO fixture_ajena VALUES ('no_confirmado')")
        p = self.proveedor(aplica=True)
        self.assertEqual(self.s.ejecutar(self.con,self.cid,p),'pendiente')
        self.assertEqual(p.writes,0); self.assertTrue(self.con.in_transaction)
        otra = sqlite3.connect(self.db)
        self.assertEqual(otra.execute('SELECT count(*) FROM fixture_ajena').fetchone()[0],0)
        otra.close(); self.con.rollback()
        self.assertEqual(self.s.ejecutar(self.con,self.cid,p),'confirmado')

    def test_dos_conexiones_compiten_solo_un_efecto(self):
        import threading
        barrera, candado = threading.Barrier(2), threading.Lock()
        p = self.proveedor('tiempo')
        lecturas = [0]
        original = p.leer
        def leer(cambio):
            with candado:
                lecturas[0] += 1
                primero = lecturas[0] <= 2
            if primero: barrera.wait(timeout=5)
            return original(cambio)
        p.leer = leer
        resultados, errores = [], []
        def trabajador():
            con = sqlite3.connect(self.db); con.row_factory = sqlite3.Row
            try:
                resultados.append(self.s.ejecutar(con,self.cid,p))
                con.commit()
            except BaseException as e: errores.append(e)
            finally: con.close()
        a,b = threading.Thread(target=trabajador),threading.Thread(target=trabajador)
        a.start(); b.start(); a.join(10); b.join(10)
        self.assertFalse(a.is_alive()); self.assertFalse(b.is_alive()); self.assertFalse(errores)
        self.assertEqual(resultados,['enviado','enviado']); self.assertEqual(p.writes,1)

    def test_claim_respeta_orden_por_objeto(self):
        otro = self.crear('posterior')
        self.assertFalse(self.s.reclamar_escritura(self.con,otro,'fixture',0,self.now))
        self.assertEqual(self.s.estado_actual(self.con,otro)['estado'],'pendiente')

    def test_efecto_aceptado_sin_presencia_nunca_habilita_reenvio(self):
        p = self.proveedor()
        self.assertEqual(self.s.ejecutar(self.con,self.cid,p,ahora=self.now),'enviado')
        self.con.commit()
        self.assertEqual(self.s.verificar(self.con,self.cid,p,ahora=self.now+timedelta(days=10)),'enviado')
        self.s.ejecutar(self.con,self.cid,p)
        self.assertEqual(p.writes,1)

    def test_memoria_no_promete_durabilidad(self):
        con = sqlite3.connect(':memory:'); con.row_factory = sqlite3.Row
        con.executescript(self.s.TABLAS_SQL)
        cid = self.s.crear_cambio(con,clave='memoria',quien='fixture',canal='clickup',tipo='comentario',objeto={'ref':'fixture'},cambio={'campo':'comentario'},modo='prueba')[0]
        con.commit()
        p = self.proveedor(aplica=True)
        self.assertEqual(self.s.ejecutar(con,cid,p),'pendiente'); self.assertEqual(p.writes,0)
        con.close()

    def test_preparar_no_confirma_transaccion_ajena(self):
        self.con.execute('CREATE TABLE fixture_prestada (valor TEXT)'); self.con.commit()
        self.con.execute("INSERT INTO fixture_prestada VALUES ('rollback')")
        self.s.preparar(self.con)
        self.assertTrue(self.con.in_transaction)
        otra = sqlite3.connect(self.db)
        self.assertEqual(otra.execute('SELECT count(*) FROM fixture_prestada').fetchone()[0],0)
        otra.close(); self.con.rollback()
        self.assertEqual(self.con.execute('SELECT count(*) FROM fixture_prestada').fetchone()[0],0)

    def test_preparar_nuevo_esquema_preserva_triggers(self):
        con = sqlite3.connect(':memory:'); con.row_factory = sqlite3.Row
        self.s.preparar(con)
        self.assertFalse(con.in_transaction)
        cid = self.s.crear_cambio(con,clave='schema',quien='fixture',canal='clickup',tipo='comentario',objeto={'ref':'fixture'},cambio={'campo':'comentario'},modo='prueba')[0]
        with self.assertRaises(sqlite3.IntegrityError):
            con.execute('DELETE FROM sinc_cambios WHERE id=?',(cid,))
        con.rollback(); con.close()

    def test_salida_abrupta_proceso_conserva_claim(self):
        import subprocess, sys
        marcador = str(Path(self.tmp.name) / 'efecto_fixture.txt')
        codigo = """
import os, sqlite3, sys
from pathlib import Path
from probar_sincronia_resultado_desconocido import cargar_candidato
s = cargar_candidato()
con = sqlite3.connect(sys.argv[1]); con.row_factory = sqlite3.Row
class Proveedor:
    real = False
    nombre = 'fixture'
    def leer(self,c): return {'marcas':set()}
    def aplicar(self,c):
        Path(sys.argv[3]).write_text('efecto_sintetico')
        os._exit(73)
s.ejecutar(con,int(sys.argv[2]),Proveedor())
"""
        terminado = subprocess.run([sys.executable,'-c',codigo,self.db,str(self.cid),marcador],cwd=Path(__file__).parent,capture_output=True,timeout=10)
        self.assertEqual(terminado.returncode,73,terminado.stderr.decode())
        self.assertEqual(Path(marcador).read_text(),'efecto_sintetico')
        act = self.s.estado_actual(self.con,self.cid)
        self.assertEqual(act['evento'],'escritura_reclamada')
        p = self.proveedor(aplica=True); p.presente = True
        self.assertEqual(self.s.ejecutar(self.con,self.cid,p),'enviado')
        self.assertEqual(p.writes,0)
        self.assertEqual(self.s.verificar(self.con,self.cid,p),'confirmado')

if __name__ == "__main__":
    unittest.main()
