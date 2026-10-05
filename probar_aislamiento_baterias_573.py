"""Únicamente fixtures de aislamiento; no arranca ni ejecuta las suites originales."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from aislamiento_baterias_573 import ejecutar_probe_573,entorno_573

class Aislamiento573(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def run_probe(self,code):return ejecutar_probe_573(self.p/'staging',code)
    def test_entorno_no_hereda_credenciales_ni_db(self):
        with patch.dict(os.environ,{'ANTHROPIC_API_KEY':'dummy','DATABASE_URL':'dummy','RO_DB':'principal','RO_IA_REAL':'si','PYTHONPATH':'principal'}):
            r=self.run_probe("import os,json;print(json.dumps(dict(os.environ)))")
        self.assertEqual(r.returncode,0,r.stderr);e=json.loads(r.stdout)
        self.assertFalse(set(e)&{'ANTHROPIC_API_KEY','DATABASE_URL','PYTHONPATH'})
        self.assertEqual(e['RO_IA_REAL'],'no');self.assertEqual(e['RO_DB'],str((self.p/'staging'/'fixture.db').resolve()))
    def test_lectura_y_escritura_externas_bloqueadas(self):
        victima=self.p/'principal-fixture';victima.write_text('unchanged')
        for mode in ('r','w'):
            with self.subTest(mode=mode):
                # un staging diferente por probe: no sobrescribir.
                r=ejecutar_probe_573(self.p/('stage-'+mode),f"open({str(victima)!r},{mode!r})")
                self.assertNotEqual(r.returncode,0);self.assertIn('PermissionError',r.stderr)
        self.assertEqual(victima.read_text(),'unchanged')
    def test_sqlite_principal_bloqueado(self):
        r=self.run_probe(f"import sqlite3;sqlite3.connect({str(self.p/'principal.db')!r})")
        self.assertNotEqual(r.returncode,0);self.assertFalse((self.p/'principal.db').exists())
    def test_sqlite_sintetico_y_assert_real(self):
        r=self.run_probe("import sqlite3,os;con=sqlite3.connect(os.environ['RO_DB']);con.execute('CREATE TABLE t(id INTEGER)');con.execute('INSERT INTO t VALUES(1)');assert con.execute('SELECT count(*) FROM t').fetchone()[0]==1;print('fixture PASS')")
        self.assertEqual(r.returncode,0,r.stderr);self.assertIn('fixture PASS',r.stdout)
    def test_fallo_assert_no_se_convierte_en_verde(self):
        r=self.run_probe("assert False,'negative fixture'")
        self.assertNotEqual(r.returncode,0);self.assertIn('AssertionError',r.stderr)
    def test_red_y_subproceso_bloqueados(self):
        for nombre,code in [('red',"import socket;s=socket.socket()"),('proceso',"import subprocess;subprocess.run(['never-run'])")]:
            r=ejecutar_probe_573(self.p/nombre,code);self.assertNotEqual(r.returncode,0);self.assertIn('PermissionError',r.stderr)
    def test_raiz_app_rechazada_sin_archivo(self):
        with self.assertRaises(ValueError):ejecutar_probe_573(Path(__file__).resolve().parent,'assert False')
    def test_symlink_escape_no_se_lee(self):
        stage=self.p/'staging';stage.mkdir();secret=self.p/'private-fixture';secret.write_text('not read');(stage/'link').symlink_to(secret)
        r=self.run_probe("open('link').read()")
        self.assertNotEqual(r.returncode,0);self.assertIn('PermissionError',r.stderr)

if __name__=='__main__':unittest.main()
