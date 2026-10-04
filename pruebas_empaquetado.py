import unittest
import tempfile
import json
from pathlib import Path
from despliegue.empaquetado import plan_codigo,copiar_codigo,copiar_privado,PRIVADOS_REQUERIDOS

class Pruebas(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.base=Path(self.t.name);self.app=self.base/'app';self.app.mkdir()
 def poner(self,r,contenido='fixture'):
  p=self.app/r;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(contenido)
 def test_codigo_allowlist_y_privados_ignorados_no_copian(self):
  for r in ('servir.py','escaner_secretos.py','modulos/prioridades_cliente.js','estilos.css','index.html','schema_v2.sql','despliegue/entrada.sh','fuentes_web/a.woff2','reglas_permisos.json','recarga.json','despliegue/pasos.json'):
   self.poner(r,'{}' if r.endswith('.json') else 'fixture')
  for r in ('local.db','copia.db-wal','.env','.env.prod','clave.pem','fuentes_verdad/servicios_confirmados.json','fuentes_metodo/reglas_operativas.json','fuentes_seo/contextos_confirmados.json','nuevo_privado.json','data/personas.json','fuentes_crm/_privado/ghl_vivo.json','fuentes/_cache_extra/raw.json','capturas/pantalla.py','despliegue/estado/fuente.py'):
   self.poner(r,'SECRETO_PRIVADO')
  self.poner('.gitignore','fuentes_metodo/reglas_operativas.json\n')
  destino=self.base/'codigo';d=copiar_codigo(self.app,destino)
  self.assertFalse(d['listo_para_desplegar']);self.assertEqual(d['json_codigo'],['despliegue/pasos.json','recarga.json','reglas_permisos.json'])
  self.assertTrue((destino/'modulos/prioridades_cliente.js').exists());self.assertTrue((destino/'fuentes_web/a.woff2').exists())
  self.assertFalse(any('SECRETO_PRIVADO' in p.read_text() for p in destino.rglob('*') if p.is_file()))
 def test_bundle_privado_separado_manifest_y_permisos(self):
  for r in PRIVADOS_REQUERIDOS:self.poner(r,'{"fixture_privado":true}')
  self.poner('data/captacion/captacion.json','{"fixture":true}')
  for r in ('data/privado.db','data/notas.txt','fuentes_seo/_cache/captura.html','data/archivo.JSON'):
   self.poner(r,'NO_BUNDLE')
  codigo=self.base/'codigo';privado=self.base/'privado'
  d=copiar_privado(self.app,privado,codigo);self.assertFalse(d['listo_para_desplegar'])
  manifest=json.loads((privado/'manifiesto_privado.json').read_text())
  self.assertTrue({'data/alarmas.json','data/logos.json','data/meta.json'}<=set(PRIVADOS_REQUERIDOS))
  self.assertTrue(all(x['ruta'].endswith('.json') for x in manifest['ficheros']))
  self.assertFalse(any('NO_BUNDLE' in p.read_text() for p in privado.rglob('*') if p.is_file()))
  self.assertFalse(manifest['hidratado']);self.assertFalse(manifest['publicar_en_repositorio'])
  self.assertTrue(all(len(x['sha256'])==64 for x in manifest['ficheros']))
  self.assertEqual(privado.stat().st_mode&0o777,0o700)
  self.assertEqual((privado/PRIVADOS_REQUERIDOS[0]).stat().st_mode&0o777,0o600)
  self.assertFalse(codigo.exists())
 def test_privado_no_dentro_codigo(self):
  with self.assertRaises(ValueError):copiar_privado(self.app,self.base/'codigo'/'privado',self.base/'codigo')
 def test_fuente_obligatoria_ausente_no_bundle(self):
  destino=self.base/'privado'
  with self.assertRaises(ValueError):copiar_privado(self.app,destino,self.base/'codigo')
  self.assertFalse(destino.exists())
 def test_enlaces_externos_no_codigo(self):
  externo=self.base/'fuera.py';externo.write_text('NO_COPIAR')
  (self.app/'enlace.py').symlink_to(externo)
  self.assertEqual(plan_codigo(self.app),[])
 def test_destino_no_mezcla_codigo_existente(self):
  destino=self.base/'codigo';destino.mkdir();(destino/'privado.json').write_text('NO')
  with self.assertRaises(ValueError):copiar_codigo(self.app,destino)
 def test_enlace_privado_rechazado_antes_crear_bundle(self):
  for r in PRIVADOS_REQUERIDOS:self.poner(r,'{}')
  externo=self.base/'afuera.json';externo.write_text('{}')
  (self.app/'data'/'enlace.json').symlink_to(externo)
  destino=self.base/'privado'
  with self.assertRaises(ValueError):copiar_privado(self.app,destino,self.base/'codigo')
  self.assertFalse(destino.exists())
 def test_plan_es_lectura_y_no_crea_contexto(self):
  self.poner('servir.py');self.poner('fuentes_metodo/reglas_operativas.json','privado')
  antes={p.relative_to(self.app).as_posix():p.read_bytes() for p in self.app.rglob('*') if p.is_file()}
  self.assertEqual(plan_codigo(self.app),['servir.py'])
  despues={p.relative_to(self.app).as_posix():p.read_bytes() for p in self.app.rglob('*') if p.is_file()}
  self.assertEqual(antes,despues);self.assertFalse((self.base/'codigo').exists())
if __name__=='__main__':unittest.main()
