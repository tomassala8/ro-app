import contextlib,gzip,hashlib,importlib.util,io,json,os,sqlite3,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from despliegue import recuperacion_privada as R

class Recuperacion163(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve();self.src=self.root/'origen';self.src.mkdir(mode=0o700)
  self.ro=self.src/'ro.db';self.kpi=self.src/'kpi.db'
  for p,val in [(self.ro,'intencion-pendiente'),(self.kpi,'hecho-declarado')]:
   with sqlite3.connect(p) as c:c.execute('CREATE TABLE registros(valor TEXT)');c.execute('INSERT INTO registros VALUES (?)',(val,))
  self.cfg=self.src/'acceso.json';self.cfg.write_text('{"fixture":"sin_credenciales"}')
  self.sources={'ro_db':{'tipo':'sqlite','ruta':self.ro},'evidencias_kpi':{'tipo':'sqlite','ruta':self.kpi},'acceso':{'tipo':'json','ruta':self.cfg}}
 def tearDown(self):self.tmp.cleanup()
 def crear(self):
  b=self.root/'bundle';info=R.crear(self.sources,b,quiescente=True);return b,info['sha256_manifiesto']
 def test_restauracion_conjunto_y_privacidad_sin_reemplazar(self):
  b,sha=self.crear();d=self.root/'restaurado';r=R.restaurar(b,d,sha,requeridos=self.sources)
  self.assertTrue(r['restaurada']);self.assertFalse(r['reemplazo_runtime'])
  for nombre,valor in [('ro_db','intencion-pendiente'),('evidencias_kpi','hecho-declarado')]:
   with sqlite3.connect(d/(nombre+'.db')) as c:self.assertEqual(c.execute('SELECT valor FROM registros').fetchone()[0],valor)
  self.assertEqual(json.loads((d/'acceso.json').read_text()),{'fixture':'sin_credenciales'})
  self.assertEqual(d.stat().st_mode&0o777,0o700)
  self.assertTrue(all(p.stat().st_mode&0o777==0o600 for p in d.iterdir()))
 def test_tampering_SQLite_valida_y_hash_ancla(self):
  b,sha=self.crear()
  with sqlite3.connect(b/'ro_db.db') as c:c.execute("UPDATE registros SET valor='dato_alterado'")
  with self.assertRaises(ValueError):R.restaurar(b,self.root/'bad',sha,requeridos=self.sources)
  self.assertFalse((self.root/'bad').exists())
  m=json.loads((b/'manifiesto.json').read_text());m['archivos']['ro_db']['sha256']=R.sha((b/'ro_db.db').read_bytes());(b/'manifiesto.json').write_text(json.dumps(m))
  with self.assertRaises(ValueError):R.restaurar(b,self.root/'bad',sha,requeridos=self.sources)
 def test_traversal_aun_con_manifiesto_reanclado(self):
  b,_=self.crear();m=json.loads((b/'manifiesto.json').read_text());m['archivos']['acceso']['archivo']='../acceso.json';raw=json.dumps(m).encode();(b/'manifiesto.json').write_bytes(raw)
  with self.assertRaises(ValueError):R.restaurar(b,self.root/'bad',R.sha(raw),requeridos=self.sources)
 def test_incompleto_extra_enlaces_y_destino_existente(self):
  b,sha=self.crear()
  with self.assertRaises(ValueError):R.restaurar(b,self.root/'bad',sha,requeridos={'fuente_ausente'})
  (b/'extra.json').write_text('{}')
  with self.assertRaises(ValueError):R.restaurar(b,self.root/'bad',sha,requeridos=self.sources)
  (b/'extra.json').unlink();d=self.root/'existente';d.mkdir(mode=0o700);(d/'sentinel').write_text('intacto')
  with self.assertRaises(FileExistsError):R.restaurar(b,d,sha,requeridos=self.sources)
  self.assertEqual((d/'sentinel').read_text(),'intacto')
  (b/'acceso.json').unlink();(b/'acceso.json').symlink_to(self.cfg)
  with self.assertRaises(ValueError):R.restaurar(b,self.root/'bad',sha,requeridos=self.sources)
 def test_quiescente_fuente_link_JSONambiguo(self):
  with self.assertRaises(ValueError):R.crear(self.sources,self.root/'bad')
  self.cfg.write_text('{"a":1,"a":2}')
  with self.assertRaises(ValueError):R.crear(self.sources,self.root/'bad',quiescente=True)
  self.assertFalse((self.root/'bad').exists())
  self.cfg.unlink();self.cfg.symlink_to(self.ro)
  with self.assertRaises(ValueError):R.crear(self.sources,self.root/'bad',quiescente=True)
 def test_script_actual_omite_depositoKPI_y_restore_no_contrasta_SHA(self):
  spec=importlib.util.spec_from_file_location('backup_fixture163',Path(__file__).parent/'despliegue/copia_seguridad.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
  copies=self.root/'viejas'
  with patch.dict(os.environ,{'RO_DB':str(self.ro),'RO_COPIA_R2':'no'},clear=True),patch.object(mod.config,'ESTADO_DIR',self.src),patch.object(mod,'CARPETA',copies),patch.object(mod,'LIBRE_MIN_MB',0),contextlib.redirect_stdout(io.StringIO()):
   self.assertEqual([n for n,_ in mod.bases()],['local'])
   self.assertEqual(mod.copiar(),0)
   day=mod.hoy().isoformat();gz=copies/day/'local.db.gz'
   alterada=self.src/'alterada.db'
   with sqlite3.connect(alterada) as c:c.execute('CREATE TABLE cambio(valor TEXT)');c.execute("INSERT INTO cambio VALUES ('fixture_ajena')")
   gz.write_bytes(gzip.compress(alterada.read_bytes()))
   salida=self.root/'restaurada_vieja.db';mod.restaurar(day,salida)
   with sqlite3.connect(salida) as c:self.assertEqual(c.execute('SELECT valor FROM cambio').fetchone()[0],'fixture_ajena')

if __name__=='__main__':unittest.main()
