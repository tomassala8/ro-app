"""L21: trabajador fuente/AST; cola, procesos y base exclusivamente sintéticos."""
import ast
import contextlib
import copy
import json
import sqlite3
import tempfile
import threading
import types
import unittest
from pathlib import Path

APP=Path(__file__).resolve().parent
class PararFixture(BaseException):pass
class ColaFixture:
    def __init__(self):self.esperas=0;self.limpiezas=0
    def wait(self,timeout):
        self.esperas+=1
        if self.esperas>1:raise PararFixture()
    def clear(self):self.limpiezas+=1

class Trabajador574(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.db=Path(self.temp.name)/'fixture.sqlite'
        self.fallo_conexion=False
        with self.con() as c:
            c.execute('CREATE TABLE recargas(id INTEGER PRIMARY KEY,quien TEXT,modo TEXT,estado TEXT,empezada TEXT,terminada TEXT,pasos TEXT)')
            c.executemany('INSERT INTO recargas(id,quien,modo,estado) VALUES (?,?,?,?)',[(1,'actor-fixture','ligera','pendiente'),(2,'actor-fixture','ligera','pendiente')])
        self.cola=ColaFixture();self.procesos=[];self.registros=[];self.cargas=[];self.avisos=[]
        self.cfg=json.dumps({'ligera':[{'id':'step-fixture','cmd':['NO_EJECUTAR_FIXTURE']}]})
        self.ns={'COLA':self.cola,'conectar':self.con,'RECARGA_CFG':types.SimpleNamespace(read_text=lambda:self.cfg),
          'json':json,'time':types.SimpleNamespace(time=lambda:0), 'AQUI':Path(self.temp.name),
          'subprocess':types.SimpleNamespace(run=self.proceso,TimeoutExpired=TimeoutError),
          'ESC_linea':lambda _: '[salida-fixture]', 'registrar':lambda *a:self.registros.append(a),
          'E':types.SimpleNamespace(cargar=lambda:self.cargas.append(True)),
          'calcular_avisos':lambda:self.avisos.append(True),'traceback':types.SimpleNamespace(print_exc=lambda:None)}
        tree=ast.parse((APP/'servir.py').read_text())
        n=copy.deepcopy(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='trabajador_recargas'))
        exec(compile(ast.fix_missing_locations(ast.Module(body=[n],type_ignores=[])),'worker-real574','exec'),self.ns)
    def tearDown(self):self.temp.cleanup()
    @contextlib.contextmanager
    def con(self):
        if self.fallo_conexion:
            self.fallo_conexion=False
            raise sqlite3.OperationalError('fallo-fixture')
        c=sqlite3.connect(self.db);c.row_factory=sqlite3.Row
        try:
            with c:yield c
        finally:c.close()
    def proceso(self,cmd,**kw):
        self.procesos.append(tuple(cmd));return types.SimpleNamespace(returncode=0,stdout='',stderr='')
    def correr(self):
        resultado=[]
        def target():
            try:self.ns['trabajador_recargas']()
            except PararFixture:resultado.append('parada_controlada')
            except Exception as exc:resultado.append(type(exc).__name__)
        t=threading.Thread(target=target,daemon=True);t.start();t.join(timeout=2)
        self.assertFalse(t.is_alive(),'fixture no puede bloquear hilo')
        return resultado
    def estados(self):
        with self.con() as c:return [(r['id'],r['estado']) for r in c.execute('SELECT id,estado FROM recargas ORDER BY id')]
    def test_control_siguiente_job_se_atiende_con_parada_controlada(self):
        self.assertEqual(self.correr(),['parada_controlada'])
        self.assertEqual(self.estados(),[(1,'ok'),(2,'ok')]);self.assertEqual(len(self.procesos),2)
    def test_control_excepcion_subprocess_no_mata_worker(self):
        def proceso(*a,**k):
            if not self.procesos:self.procesos.append(('fallo-fixture',));raise OSError('fixture')
            return self.proceso(*a,**k)
        self.ns['subprocess'].run=proceso
        self.assertEqual(self.correr(),['parada_controlada'])
        self.assertEqual(self.estados(),[(1,'con_fallos'),(2,'ok')]);self.assertEqual(len(self.procesos),2)
    def test_repro_config_invalida_mata_worker_y_deja_claim(self):
        self.cfg='{'
        self.assertEqual(self.correr(),['JSONDecodeError'])
        self.assertEqual(self.estados(),[(1,'en_curso'),(2,'pendiente')]);self.assertEqual(self.procesos,[])
    def test_repro_paso_sin_id_fuera_try(self):
        self.cfg=json.dumps({'ligera':[{'cmd':['NO_EJECUTAR_FIXTURE']}]})
        self.assertEqual(self.correr(),['KeyError'])
        self.assertEqual(self.estados(),[(1,'en_curso'),(2,'pendiente')]);self.assertEqual(len(self.procesos),1)
    def test_repro_registrar_falla_y_deja_siguiente_pendiente(self):
        def fail(*a):raise RuntimeError('fixture')
        self.ns['registrar']=fail
        self.assertEqual(self.correr(),['RuntimeError'])
        self.assertEqual(self.estados(),[(1,'ok'),(2,'pendiente')]);self.assertEqual(len(self.procesos),1)
    def test_repro_avisos_falla_y_deja_siguiente_pendiente(self):
        def fail():raise RuntimeError('fixture')
        self.ns['calcular_avisos']=fail
        self.assertEqual(self.correr(),['RuntimeError'])
        self.assertEqual(self.estados(),[(1,'ok'),(2,'pendiente')]);self.assertEqual(len(self.procesos),1)
    def test_repro_lectura_cola_falla_sin_perder_job_persistido(self):
        self.fallo_conexion=True
        self.assertEqual(self.correr(),['OperationalError'])
        self.assertEqual(self.estados(),[(1,'pendiente'),(2,'pendiente')]);self.assertEqual(self.procesos,[])

if __name__=='__main__':unittest.main()
