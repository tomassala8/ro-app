"""Caché real de logo, sin importar el arranque del servidor ni usar imágenes de clientes."""
import ast
import base64
import hashlib
import re
import threading
import types
import unittest
from pathlib import Path


class Logo(unittest.TestCase):
    def test_cambio_mismo_tamano_y_sufijo(self):
        tree = ast.parse(Path(__file__).with_name('servir.py').read_text())
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'logo_de')
        e = types.SimpleNamespace(crudo={'logos': {}})
        ns = dict(E=e, re=re, base64=base64, hashlib=hashlib,
                  _SERVIDOS={}, _CANDADO_SERVIDOS=threading.Lock())
        exec(compile(ast.Module(body=[fn], type_ignores=[]), 'logo_real', 'exec'), ns)
        # Bytes sintéticos distintos con idéntico tamaño y larga cola común.
        a, b = b'AAA' + b'\0' * 128, b'BBB' + b'\0' * 128
        uri = lambda v: 'data:image/png;base64,' + base64.b64encode(v).decode()
        self.assertEqual(uri(a)[-64:], uri(b)[-64:])
        e.crudo['logos']['fixture'] = uri(a)
        primero = ns['logo_de']('fixture')
        e.crudo['logos']['fixture'] = uri(b)
        segundo = ns['logo_de']('fixture')
        self.assertEqual(primero[0], a)
        self.assertEqual(segundo[0], b)
        self.assertNotEqual(primero[2], segundo[2])
        self.assertEqual(ns['logo_de']('fixture'), segundo)
        self.assertIsNone(ns['logo_de']('ausente'))


if __name__ == '__main__':
    unittest.main()
