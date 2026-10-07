import ast
import io
import mimetypes
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
import estaticos_seguro_234 as S

class Pruebas(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = Path(self.tmp.name).resolve() / 'app'
        (self.raiz / 'modulos').mkdir(parents=True)
        self.publico = self.raiz / 'modulos' / 'fixture.js'
        self.publico.write_bytes(b'public-fixture')
        self.privado = self.raiz / 'fuentes' / '_privado' / 'fixture.json'
        self.privado.parent.mkdir(parents=True)
        self.privado.write_bytes(b'private-fixture')

    def test_asset_regular(self):
        datos, marca = S.leer_estatico(self.raiz, 'modulos/fixture.js')
        self.assertEqual(datos, b'public-fixture')
        self.assertEqual(len(marca), 5)

    def test_symlink_al_privado(self):
        self.publico.unlink()
        self.publico.symlink_to(self.privado)
        with self.assertRaises(OSError):
            S.leer_estatico(self.raiz, 'modulos/fixture.js')

    def test_symlink_incluso_a_otro_publico(self):
        otro = self.raiz / 'otro.js'; otro.write_bytes(b'otro-fixture')
        self.publico.unlink(); self.publico.symlink_to(otro)
        with self.assertRaises(OSError):
            S.leer_estatico(self.raiz, 'modulos/fixture.js')

    def test_directorio_simbolico(self):
        (self.raiz / 'alias').symlink_to(self.publico.parent, target_is_directory=True)
        with self.assertRaises(OSError):
            S.leer_estatico(self.raiz, 'alias/fixture.js')

    def test_escape_raiz_hermana(self):
        hermana = self.raiz.with_name('app-adjunta'); hermana.mkdir()
        (hermana / 'fixture.js').write_bytes(b'outside-fixture')
        for ruta in ['../app-adjunta/fixture.js', str(hermana / 'fixture.js'), 'modulos/../otro.js', 'modulos//fixture.js']:
            with self.subTest(ruta=ruta), self.assertRaises((OSError, ValueError)):
                S.leer_estatico(self.raiz, ruta)

    def test_directorio_no_es_asset(self):
        with self.assertRaises(OSError):
            S.leer_estatico(self.raiz, 'modulos')

    def test_cambio_a_symlink_tras_validar(self):
        original = S.ruta_estatica
        def cambiar(raiz, rel):
            p = original(raiz, rel)
            self.publico.unlink(); self.publico.symlink_to(self.privado)
            return p
        with patch.object(S, 'ruta_estatica', cambiar), self.assertRaises(OSError):
            S.leer_estatico(self.raiz, 'modulos/fixture.js')

    def test_asset_mayor_al_limite(self):
        with patch.object(S, 'TOPE', 3), self.assertRaises(OSError):
            S.leer_estatico(self.raiz, 'modulos/fixture.js')

    def test_png_no_usa_lector_base(self):
        tree = ast.parse(Path(__file__).with_name('servir.py').read_text())
        fun = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'estatico')
        import re
        ns = {'re':re, 'ESTATICOS_PERMITIDOS':re.compile(r'^modulos/[\w-]+\.png$')}
        exec(compile(ast.Module(body=[fun],type_ignores=[]),'servir.py','exec'),ns)
        class H:
            def fichero_comprimido(self, rel): return ('seguro', rel)
        self.assertEqual(ns['estatico'](H(), '/modulos/fixture.png'), ('seguro','modulos/fixture.png'))

    def test_lector_real_rechaza_link_sin_emitir_bytes(self):
        tree=ast.parse(Path(__file__).with_name('servir.py').read_text())
        fun=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='fichero_comprimido')
        self.publico.unlink();self.publico.symlink_to(self.privado)
        ns={'AQUI':self.raiz,'ruta_estatica':S.ruta_estatica,'contenido_servido':lambda r: (_ for _ in ()).throw(AssertionError('No debe leer'))}
        exec(compile(ast.Module(body=[fun],type_ignores=[]),'servir.py','exec'),ns)
        class H:
            def __init__(self):self.wfile=io.BytesIO();self.code=None
            def responder(self, c, d):self.code=c
        h=H();ns['fichero_comprimido'](h,'modulos/fixture.js')
        self.assertEqual(h.code,404);self.assertEqual(h.wfile.getvalue(),b'')

if __name__ == '__main__':unittest.main()
