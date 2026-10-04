"""Revisión independiente aislada; no importa servir ni usa datos reales."""
import ast, os, tempfile, threading, unittest, hashlib
from pathlib import Path
from unittest.mock import patch
import estaticos_seguro_234 as S

class Pruebas(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name).resolve();self.root=self.base/'app'
        (self.root/'modulos').mkdir(parents=True)
        (self.root/'modulos'/'a.js').write_bytes(b'public')
    def test_directorio_sustituido_por_link_despues_validacion(self):
        outside=self.base/'outside';outside.mkdir();(outside/'a.js').write_bytes(b'fixture-private')
        original=S.ruta_estatica
        def validate(*args):
            p=original(*args);(self.root/'modulos').rename(self.root/'old');(self.root/'modulos').symlink_to(outside);return p
        with patch.object(S,'ruta_estatica',validate), self.assertRaises(OSError):S.leer_estatico(self.root,'modulos/a.js')
    def test_raiz_sustituida_despues_validacion_rechazada(self):
        outside=self.base/'outside';(outside/'modulos').mkdir(parents=True);(outside/'modulos'/'a.js').write_bytes(b'fixture-private')
        original=S.ruta_estatica
        def validate(*args):
            p=original(*args);self.root.rename(self.base/'old');self.root.symlink_to(outside);return p
        with patch.object(S,'ruta_estatica',validate),self.assertRaises(OSError):S.leer_estatico(self.root,'modulos/a.js')
    def test_raiz_confiable_no_se_redefine_si_ya_es_symlink(self):
        outside=self.base/'outside';(outside/'modulos').mkdir(parents=True)
        (outside/'modulos'/'a.js').write_bytes(b'fixture-private')
        self.root.rename(self.base/'old');self.root.symlink_to(outside)
        with self.assertRaises(OSError):S.leer_estatico(self.root,'modulos/a.js')
    def test_plataforma_sin_dirfd_no_lectura(self):
        with patch.object(S.os,'supports_dir_fd',set()),patch.object(S.os,'open',side_effect=AssertionError('No abrir')),self.assertRaises(PermissionError):S.leer_estatico(self.root,'modulos/a.js')
    def test_reemplazo_publico_misma_fecha_size_actualiza(self):
        p=self.root/'modulos'/'a.js';_,marca=S.leer_estatico(self.root,'modulos/a.js');old=p.stat();q=self.root/'modulos'/'new.js';q.write_bytes(b'NEWpub');os.utime(q,ns=(old.st_atime_ns,old.st_mtime_ns));q.replace(p)
        datos,nueva=S.leer_estatico(self.root,'modulos/a.js');self.assertEqual(datos,b'NEWpub');self.assertNotEqual(marca,nueva)
    def test_descriptores_cerrados_si_open_archivo_falla(self):
        open0=S.os.open;close0=S.os.close;opened=[];closed=[]
        def opening(path,*args,**kw):
            if path=='a.js':raise OSError('fixture')
            fd=open0(path,*args,**kw);opened.append(fd);return fd
        def closing(fd):closed.append(fd);return close0(fd)
        with patch.object(S.os,'open',opening),patch.object(S.os,'supports_dir_fd',{opening}),patch.object(S.os,'close',closing),self.assertRaises(OSError):S.leer_estatico(self.root,'modulos/a.js')
        self.assertEqual(set(opened),set(closed))
    def test_fuente_same_mtime_size_actualiza_version_css(self):
        (self.root/'fuentes_web').mkdir();f=self.root/'fuentes_web'/'a.woff2';f.write_bytes(b'AAAA')
        (self.root/'estilos.css').write_text('body{src:url("fuentes_web/a.woff2")}')
        tree=ast.parse(Path(__file__).with_name('servir.py').read_text());names={'_estado_fichero','contenido_servido'};funs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
        ns={'AQUI':self.root,'ruta_estatica':S.ruta_estatica,'leer_estatico':S.leer_estatico,'_SERVIDOS':{},'_CANDADO_SERVIDOS':threading.Lock(),'hashlib':hashlib}
        exec(compile(ast.Module(body=funs,type_ignores=[]),'servir-fixture','exec'),ns)
        css0,_=ns['contenido_servido']('estilos.css');old=f.stat();replacement=f.with_name('b.woff2');replacement.write_bytes(b'BBBB');os.utime(replacement,ns=(old.st_atime_ns,old.st_mtime_ns));replacement.replace(f)
        css1,_=ns['contenido_servido']('estilos.css');newhash=ns['contenido_servido']('fuentes_web/a.woff2')[1]
        self.assertNotEqual(css0,css1);self.assertIn(newhash.encode(),css1)
if __name__=='__main__':unittest.main()
