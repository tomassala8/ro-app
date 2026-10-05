"""L14: schema/SEGURIDAD_SQL/conectar reales por AST; sólo SQLite temporal."""
import ast
import copy
import os
import sqlite3
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

APP=Path(__file__).resolve().parent
TREE=ast.parse((APP/'servir.py').read_text())
SQL=(APP/'schema_v2.sql').read_text()
SEG=next(ast.literal_eval(n.value) for n in TREE.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SEGURIDAD_SQL' for t in n.targets))
F=next(n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name=='conectar')
EXISTE='''CREATE TRIGGER propuesta_registro_insert BEFORE INSERT ON registro
WHEN EXISTS (SELECT 1 FROM registro WHERE id=NEW.id)
BEGIN SELECT RAISE(ABORT,'No sustituir registro'); END;
CREATE TRIGGER propuesta_huellas_insert BEFORE INSERT ON registro_huellas
WHEN EXISTS (SELECT 1 FROM registro_huellas WHERE id=NEW.id)
BEGIN SELECT RAISE(ABORT,'No sustituir huella'); END;'''
MAXIMO='''CREATE TRIGGER propuesta_registro_max BEFORE INSERT ON registro
WHEN NEW.id <= (SELECT MAX(id) FROM registro)
BEGIN SELECT RAISE(ABORT,'No reutilizar ID'); END;'''

def connector(db,propuesta=False):
    f=copy.deepcopy(F)
    # Baseline histórico explícito: se conserva el repro previo sin el PRAGMA nuevo.
    if not propuesta:
        f.body=[n for n in f.body if not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and n.value.args and isinstance(n.value.args[0],ast.Constant) and n.value.args[0].value=='PRAGMA recursive_triggers = ON')]
    env={'os':os,'sqlite3':sqlite3,'DB':db}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[f],type_ignores=[])),'conectar real/propuesta569','exec'),env)
    return env['conectar']

class Rastro569(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'fixture.sqlite3'
        self.env=patch.dict(os.environ,{},clear=True);self.env.start()
        self.con=connector(self.db)();self.con.executescript(SQL);self.con.executescript(SEG)
        self.con.execute("INSERT INTO registro(id,quien,coleccion,accion) VALUES(1,'fixture','fixture','observado')")
        self.con.execute("INSERT INTO registro_huellas VALUES(1,'huella-fixture')");self.con.commit()
    def tearDown(self):self.con.close();self.env.stop();self.tmp.cleanup()
    def replace(self,tabla):
        if tabla=='registro':self.con.execute("INSERT OR REPLACE INTO registro(id,quien,coleccion,accion) VALUES(1,'cambiado','fixture','observado')")
        else:self.con.execute("INSERT OR REPLACE INTO registro_huellas VALUES(1,'cambiado')")
    def test_baseline_anterior_replace_omite_delete(self):
        self.assertEqual(self.con.execute('PRAGMA recursive_triggers').fetchone()[0],0)
        for tabla in ('registro','registro_huellas'):self.replace(tabla)
        self.assertEqual(self.con.execute('SELECT quien FROM registro WHERE id=1').fetchone()[0],'cambiado')
        self.assertEqual(self.con.execute('SELECT huella FROM registro_huellas WHERE id=1').fetchone()[0],'cambiado')
    def test_update_delete_originales_bloqueados(self):
        for tabla in ('registro','registro_huellas'):
            for sql in (f'DELETE FROM {tabla} WHERE id=1',f'UPDATE {tabla} SET id=2 WHERE id=1'):
                with self.assertRaises(sqlite3.IntegrityError):self.con.execute(sql)
    def test_pragma_propuesto_por_conexion(self):
        self.con.close();self.con=connector(self.db,True)()
        self.assertEqual(self.con.execute('PRAGMA recursive_triggers').fetchone()[0],1)
        for tabla in ('registro','registro_huellas'):
            with self.assertRaises(sqlite3.IntegrityError):self.replace(tabla)
        self.con.close();self.con=sqlite3.connect(self.db)
        self.assertEqual(self.con.execute('PRAGMA recursive_triggers').fetchone()[0],0)
        self.replace('registro') # PRAGMA del servidor no protege clientes externos que lo omiten.
    def test_maximo_rechaza_autoincremento_legitimo(self):
        self.con.executescript(MAXIMO)
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute("INSERT INTO registro(quien,coleccion) VALUES('legitimo','fixture')")
        self.assertEqual(self.con.execute('SELECT count(*) FROM registro').fetchone()[0],1)
    def test_exists_rechaza_replace_off_y_on_y_preserva_append(self):
        self.con.executescript(EXISTE)
        for recursive in (0,1):
            self.con.execute(f'PRAGMA recursive_triggers={recursive}')
            for tabla in ('registro','registro_huellas'):
                with self.assertRaises(sqlite3.IntegrityError):self.replace(tabla)
            row=self.con.execute("INSERT INTO registro(quien,coleccion) VALUES('legitimo','fixture')").lastrowid
            self.con.execute('INSERT INTO registro_huellas VALUES(?,?)',(row,'huella-nueva'))
        self.assertEqual(self.con.execute('SELECT count(*) FROM registro').fetchone()[0],3)
        self.assertEqual(self.con.execute('SELECT huella FROM registro_huellas WHERE id=1').fetchone()[0],'huella-fixture')
    def test_maximo_con_id_positivo_preserva_append(self):
        self.con.executescript(MAXIMO.replace('WHEN NEW.id <=','WHEN NEW.id > 0 AND NEW.id <='))
        with self.assertRaises(sqlite3.IntegrityError):self.replace('registro')
        row=self.con.execute("INSERT INTO registro(quien,coleccion) VALUES('legitimo','fixture')").lastrowid
        self.assertEqual(row,2)
    def test_limite_exists_id_negativo_legacy(self):
        self.con.execute("INSERT INTO registro(id,quien,coleccion) VALUES(-1,'fixture','fixture')")
        self.con.executescript(EXISTE)
        # NEW.id provisional=-1: documenta la precondición IDs positivos, no se oculta.
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute("INSERT INTO registro(quien,coleccion) VALUES('legitimo','fixture')")

    def test_pg_rama_no_recibe_pragma(self):
        sentinel=object();base=types.SimpleNamespace(conectar=lambda:sentinel)
        with patch.dict(os.environ,{'DATABASE_URL':'fixture-no-connection'}),patch.dict(sys.modules,{'base':base}):
            self.assertIs(connector(self.db,True)(),sentinel)
    def test_traductor_actual_no_soporta_insert_condicional(self):
        t=ast.parse((APP/'despliegue/base.py').read_text())
        f=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='esquema_postgres')
        import re
        env={'re':re,'AHORA_PG':'fixture','HOY_PG':'fixture'}
        exec(compile(ast.Module(body=[f],type_ignores=[]),'traductor actual AST','exec'),env)
        result=env['esquema_postgres'](EXISTE)
        self.assertIn('BEFORE INSERT',result);self.assertIn('RAISE(ABORT',result)
        # Prueba textual de ausencia de traducción; no certificación PostgreSQL real.

def literal(nombre):
    return next(ast.literal_eval(n.value) for n in TREE.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==nombre for t in n.targets))

def inicializar(con):
    fn=next(n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name=='iniciar_base')
    env={'conectar':lambda:con,'sqlite3':sqlite3,'ESQUEMA':APP/'schema_v2.sql','SEGURIDAD_SQL':SEG,
         'SEGURIDAD_INSERT_SQLITE_569':literal('SEGURIDAD_INSERT_SQLITE_569'),'R15_SQL':literal('R15_SQL'),
         'PLANES_FUEGOS_255':types.SimpleNamespace(iniciar=lambda _:None)}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'iniciar_base real AST569','exec'),env)
    env['iniciar_base']()

class FuenteImplementada569(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'real-fixture.db'
        self.env=patch.dict(os.environ,{},clear=True);self.env.start()
        self.con=connector(self.path,True)();inicializar(self.con)
    def tearDown(self):self.con.close();self.env.stop();self.tmp.cleanup()
    def append(self):
        rid=self.con.execute("INSERT INTO registro(quien,coleccion) VALUES('fixture','fixture')").lastrowid
        self.con.execute('INSERT INTO registro_huellas VALUES(?,?)',(rid,'hash-fixture'))
        return rid
    def test_conectar_real_activa_recursive(self):
        self.assertEqual(self.con.execute('PRAGMA recursive_triggers').fetchone()[0],1)
    def test_append_multiples_y_reiniciar_idempotente(self):
        ids=[self.append() for _ in range(4)];self.assertEqual(ids,[1,2,3,4]);inicializar(self.con)
        self.assertEqual(self.append(),5)
    def test_replace_rechazado_off_y_on_ambas_tablas(self):
        self.append()
        for flag in (0,1):
            self.con.execute(f'PRAGMA recursive_triggers={flag}')
            for sql in ("INSERT OR REPLACE INTO registro(id,quien,coleccion) VALUES(1,'otro','fixture')","INSERT OR REPLACE INTO registro_huellas VALUES(1,'otro')"):
                with self.assertRaises(sqlite3.IntegrityError):self.con.execute(sql)
        self.assertEqual(self.con.execute('SELECT quien FROM registro WHERE id=1').fetchone()[0],'fixture')
        self.assertEqual(self.con.execute('SELECT huella FROM registro_huellas WHERE id=1').fetchone()[0],'hash-fixture')
    def test_negativo_existente_no_bloquea_append(self):
        self.con.execute("INSERT INTO registro(id,quien,coleccion) VALUES(-1,'fixture','fixture')")
        self.con.execute("INSERT INTO registro_huellas VALUES(-1,'fixture')")
        self.assertEqual([self.append() for _ in range(3)],[1,2,3])
    def test_hueco_positivo_no_es_reescritura_historica(self):
        self.con.execute("INSERT INTO registro(id,quien,coleccion) VALUES(5,'fixture','fixture')")
        self.con.execute("INSERT INTO registro_huellas VALUES(5,'fixture')")
        for sql in ("INSERT INTO registro(id,quien,coleccion) VALUES(2,'fixture','fixture')","INSERT INTO registro_huellas VALUES(2,'fixture')"):
            with self.assertRaises(sqlite3.IntegrityError):self.con.execute(sql)
        self.assertEqual(self.append(),6)
    def test_guard_tipo_real_no_env(self):
        os.environ['DATABASE_URL']='fixture-no-pg'
        # conectar no se llama aquí; init usa tipo efectivo, aunque entorno cambie.
        inicializar(self.con)
        self.assertEqual(self.con.execute("SELECT count(*) FROM sqlite_master WHERE name LIKE '%sin_reinsertar_569'").fetchone()[0],2)
    def test_wrapper_no_sqlite_no_recibe_ddl(self):
        outer=self
        class PGSimulado:
            sql=[]
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def execute(self,*a):return outer.con.execute(*a)
            def executescript(self,sql):self.sql.append(sql);return outer.con.executescript(sql)
        fake=PGSimulado();inicializar(fake)
        self.assertFalse(any('sin_reinsertar_569' in sql for sql in fake.sql))

if __name__=='__main__':unittest.main()
