import ast
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from despliegue.empaquetado import copiar_privado, PRIVADOS_REQUERIDOS
from despliegue.hidratar_privado import hidratar, validar
import piloto_lectura

class Hidratacion(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve(); self.app=self.root/'app';self.app.mkdir()
        for r in PRIVADOS_REQUERIDOS:
            p=self.app/r;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{}')
        self.bundle=self.root/'bundle';copiar_privado(self.app,self.bundle,self.root/'codigo')
        self.dest=self.root/'dest'
    def huella(self):return hashlib.sha256((self.bundle/'manifiesto_privado.json').read_bytes()).hexdigest()
    def cambiar_manifest(self,fn):
        p=self.bundle/'manifiesto_privado.json';m=json.loads(p.read_text());fn(m);p.write_text(json.dumps(m))
    def test_bundle_real_y_permisos_restrictivos(self):
        r=hidratar(self.bundle,self.dest,self.huella(),codigo_destino=self.root/'codigo')
        self.assertFalse(r['listo_para_desplegar']);self.assertFalse(r['integrado_en_servidor'])
        for rel in PRIVADOS_REQUERIDOS:
            p=self.dest/rel;self.assertEqual(p.read_bytes(),(self.app/rel).read_bytes())
            self.assertEqual(p.stat().st_mode & 0o777,0o600)
        self.assertEqual(self.dest.stat().st_mode & 0o777,0o700)
        self.assertTrue(json.loads((self.dest/'hidratacion_completa.json').read_text())['hidratacion_completa'])
    def test_destino_existente_se_conserva(self):
        self.dest.mkdir();(self.dest/'conservar').write_text('ok')
        with self.assertRaises(FileExistsError):hidratar(self.bundle,self.dest,self.huella(),codigo_destino=self.root/'codigo')
        self.assertEqual((self.dest/'conservar').read_text(),'ok')
    def test_manifiesto_tampering_y_fuente_tampering(self):
        sha=self.huella();self.cambiar_manifest(lambda m:m.update(version=2))
        with self.assertRaises(ValueError):hidratar(self.bundle,self.dest,sha,codigo_destino=self.root/'codigo')
        self.assertFalse(self.dest.exists())
        self.cambiar_manifest(lambda m:m.update(version=1));sha=self.huella()
        (self.bundle/PRIVADOS_REQUERIDOS[0]).write_text('{"alterado":true}')
        with self.assertRaises(ValueError):hidratar(self.bundle,self.dest,sha,codigo_destino=self.root/'codigo')
        self.assertFalse(self.dest.exists())
    def test_traversal_rutas_codigo_y_duplicados(self):
        original=(self.bundle/'manifiesto_privado.json').read_bytes()
        for ruta in ('../fuera.json','/tmp/x.json','data/../x.json','data//x.json','data/x.py','data/x.db','data/x\\y.json'):
            (self.bundle/'manifiesto_privado.json').write_bytes(original)
            self.cambiar_manifest(lambda m:m['ficheros'][0].update(ruta=ruta))
            with self.assertRaises(ValueError):validar(self.bundle,self.huella())
        (self.bundle/'manifiesto_privado.json').write_bytes(original)
        self.cambiar_manifest(lambda m:m['ficheros'].append(dict(m['ficheros'][0])))
        with self.assertRaises(ValueError):validar(self.bundle,self.huella())
    def test_enlaces_fuente_destino_y_extras(self):
        source=self.bundle/PRIVADOS_REQUERIDOS[0];b=source.read_bytes();source.unlink()
        target=self.root/'fuera';target.write_bytes(b);source.symlink_to(target)
        with self.assertRaises(ValueError):hidratar(self.bundle,self.dest,self.huella(),codigo_destino=self.root/'codigo')
        source.unlink();source.write_bytes(b)
        self.dest.symlink_to(self.root/'ausente')
        with self.assertRaises(ValueError):hidratar(self.bundle,self.dest,self.huella(),codigo_destino=self.root/'codigo')
        self.dest.unlink();(self.bundle/'.env').write_text('prohibido')
        with self.assertRaises(ValueError):hidratar(self.bundle,self.dest,self.huella(),codigo_destino=self.root/'codigo')
        self.assertFalse(self.dest.exists())
    def test_falta_obligatoria_limite_y_hash_no_confiable(self):
        with self.assertRaises(ValueError):validar(self.bundle,'')
        with self.assertRaises(ValueError):validar(self.bundle,self.huella(),max_bytes=1)
        self.cambiar_manifest(lambda m:m['ficheros'].pop())
        with self.assertRaises(ValueError):validar(self.bundle,self.huella())
    def test_fallo_escritura_no_marca_directorio_completo(self):
        with patch('despliegue.hidratar_privado._escribir',side_effect=OSError('fixture')):
            with self.assertRaises(OSError):hidratar(self.bundle,self.dest,self.huella(),codigo_destino=self.root/'codigo')
        self.assertTrue(self.dest.is_dir())
        self.assertFalse((self.dest/'hidratacion_completa.json').exists())
    def test_hardlink_y_json_duplicado_rechazados(self):
        source=self.bundle/PRIVADOS_REQUERIDOS[0]
        os.link(source,self.root/'hardlink')
        with self.assertRaises(ValueError):validar(self.bundle,self.huella())
        (self.root/'hardlink').unlink()
        b=b'{"x":1,"x":2}';source.write_bytes(b)
        def actualizar(m):
            e=next(e for e in m['ficheros'] if e['ruta']==PRIVADOS_REQUERIDOS[0])
            e.update(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
        self.cambiar_manifest(actualizar)
        with self.assertRaises(ValueError):validar(self.bundle,self.huella())
        self.assertFalse(self.dest.exists())
    def test_destino_dentro_del_codigo_denegado(self):
        codigo=self.root/'codigo';codigo.mkdir()
        with self.assertRaises(ValueError):
            hidratar(self.bundle,codigo/'privado',self.huella(),codigo_destino=codigo)
        self.assertFalse((codigo/'privado').exists())
    def test_validacion_no_escribe(self):
        before={p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        validar(self.bundle,self.huella())
        after={p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before,after);self.assertFalse(self.dest.exists())

class Trabajadores(unittest.TestCase):
    def test_guardias_reales_sin_arrancar_hilos(self):
        for nombre in ('avisos.py','avisos_programados.py'):
            arbol=ast.parse(Path(nombre).read_text())
            eng=next(n for n in arbol.body if isinstance(n,ast.FunctionDef) and n.name=='enganchar')
            guardia=next(n for n in eng.body if isinstance(n,ast.If) and 'RO_AVISOS_SIN_BUCLE' in ast.unparse(n.test))
            codigo=compile(ast.fix_missing_locations(ast.Module(body=[guardia],type_ignores=[])),nombre,'exec')
            for piloto,env,esperado in [('1','',0),('desconocido','',0),('no','1',0),('no','',1)]:
                threading=Mock();scope={'os':os,'piloto_lectura':piloto_lectura,'threading':threading,'bucle':Mock()}
                with patch.dict(os.environ,{'RO_PILOTO_LECTURA':piloto,'RO_AVISOS_SIN_BUCLE':env}):exec(codigo,scope)
                self.assertEqual(threading.Thread.call_count,esperado,(nombre,piloto,env))
                self.assertEqual(threading.Thread.return_value.start.call_count,esperado)

if __name__=='__main__':unittest.main()
