"""Regresión aislada del symlink234; no crea enlaces en APP."""
import ast, io, mimetypes, tempfile, unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from estaticos_seguro_234 import ruta_estatica
SRC = Path(__file__).with_name('servir.py')
class Prueba(unittest.TestCase):
    def test_symlink_publico_alcanza_fichero_privado(self):
        tree=ast.parse(SRC.read_text())
        f=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='fichero_comprimido')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()/'app'; (root/'modulos').mkdir(parents=True)
            private=root/'fuentes'/'_privado'; private.mkdir(parents=True)
            target=private/'fixture.json'; target.write_bytes(b'fixture-no-personal')
            (root/'modulos'/'fixture.js').symlink_to(target)
            ns={'ruta_estatica':ruta_estatica,'AQUI':root,'mimetypes':mimetypes,'parse_qs':parse_qs,'urlparse':urlparse,'INMUTABLE':'immutable','contenido_servido':lambda rel: ((root/rel).read_bytes(),'fixture')}
            exec(compile(ast.Module(body=[f],type_ignores=[]),str(SRC),'exec'),ns)
            class H:
                path='/modulos/fixture.js'; headers={}
                def __init__(self): self.wfile=io.BytesIO();self.code=None
                def responder(self,c,b): self.code=c
                def send_response(self,c): self.code=c
                def send_header(self,*a): pass
                def end_headers(self): pass
                def codificacion(self): return None
            h=H(); ns['fichero_comprimido'](h,'modulos/fixture.js')
            self.assertEqual(h.code,404)
            self.assertEqual(h.wfile.getvalue(),b'')
if __name__=='__main__': unittest.main()
