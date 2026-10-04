import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import acciones_lectura_544 as L
import probar_lectura_acciones_538 as F
import probar_rastro_actual_544 as R
from fuentes_verdad import clientes_activos as ACT


class FirmaRuntime550(unittest.TestCase):
    def setUp(self): self.f = F.Lectura538(); self.f.setUp()
    def tearDown(self): self.f.tearDown()

    def test_estado_real_sintetico_con_sets_y_patron(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'estado.json'
            path.write_text(json.dumps({'activos': [{'id': 'cid1', 'tipo': next(iter(ACT.TIPOS_ACTIVOS))}],
                                        'bajas_ids': [], 'bajas': [], 'dudosos': []}))
            with patch.object(ACT, 'ESTADO', path), patch.object(ACT, '_CACHE', {'marca': None, 'estado': None}):
                estado = ACT.estado()
                self.assertIsInstance(estado['_activos'], set)
                self.assertIsInstance(estado['_rx'], re.Pattern)
                self.f.get.__globals__['ACT'] = ACT
                code, d = self.f.request('salud-crm')
                self.assertEqual(code, 200); self.assertEqual(len(d['acciones']), 1)
                r = R.RastroActual544(); r.setUp()
                try:
                    r.get.__globals__['ACT'] = ACT
                    code, d = r.leer()
                    self.assertEqual(code, 200); self.assertEqual(len(d['acciones']), 1)
                finally:
                    r.tearDown()

    def test_firma_determinista_y_detecta_rotacion(self):
        a = {'ids': {'b', 'a'}, 'rx': re.compile('a', re.I)}
        b = {'rx': re.compile('a', re.I), 'ids': {'a', 'b'}}
        enc = lambda x: json.dumps(x, sort_keys=True, default=L._tipo_firma550)
        self.assertEqual(enc(a), enc(b))
        self.assertNotEqual(enc(a), enc(dict(b, ids={'a'})))
        self.assertNotEqual(enc(a), enc(dict(b, rx=re.compile('a'))))
        self.assertNotEqual(enc(a), enc(dict(b, rx=re.compile('b', re.I))))

    def test_no_default_str_ni_objetos_desconocidos(self):
        for v in (object(), {1}, re.compile(b'a')):
            with self.assertRaises(TypeError): json.dumps(v, default=L._tipo_firma550)
        with self.assertRaises(ValueError):
            json.dumps(float('nan'), allow_nan=False, default=L._tipo_firma550)
        self.f.get.__globals__['ACT'].estado = lambda: {'malformado': object()}
        self.assertEqual(self.f.request()[0], 403)


if __name__ == '__main__': unittest.main()
