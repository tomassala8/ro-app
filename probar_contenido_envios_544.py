import copy
import unittest
from probar_privacidad_rastro_envios_543 import Envio543


class Contenido544(Envio543):
    def habilitar(self):
        self.raw['clientes'] = [{'id': 'revocado', 'estado': 'activo', 'activo': True}]
        self.raw['asignaciones'] = [{'cliente_id': 'revocado', 'persona_id': self.p['id'], 'silla': 'account'}]
        self.act['revocado'] = True

    def test_autorizado_conserva_shape(self):
        self.habilitar()
        d = self.ns['a_json'](None, self.e, self.p, self.p)
        self.assertFalse(d['texto_oculto']); self.assertEqual(d['texto'], 'Texto sintético')
        self.assertEqual(d['cliente_id'], 'revocado')
        self.assertEqual(d['destinatario']['nombre'], 'Persona sintética')
        self.assertEqual(d['destinatario']['ref'], 'referencia_sintetica')
        self.assertEqual(d['id'], 1)

    def test_revocacion_ultimo_io_oculta_todo_contenido(self):
        for cambio in ('act', 'roles', 'cartera', 'dup_cliente', 'dup_persona'):
            with self.subTest(cambio=cambio):
                self.setUp(); self.habilitar()
                actor = copy.deepcopy(self.p)
                def leer(c, eid):
                    if cambio == 'act': self.act['revocado'] = False
                    elif cambio == 'roles': self.p['puestos'] = ['operaciones']
                    elif cambio == 'cartera': self.raw['asignaciones'] = []
                    elif cambio == 'dup_cliente': self.raw['clientes'].append(dict(self.raw['clientes'][0]))
                    else: self.raw['personas'].append(dict(self.p))
                    return []
                self.ns['pasos_de'] = leer
                d = self.ns['a_json'](None, self.e, actor, actor)
                self.assertTrue(d['texto_oculto'])
                for k in ('cliente_id', 'cliente', 'texto', 'asunto', 'motivo'): self.assertIsNone(d[k])
                self.assertTrue(all(v is None for v in d['destinatario'].values()))
                self.assertEqual(d['id'], 1); self.assertEqual(d['canal'], 'ghl')

    def test_real_vista_interseccion_actual(self):
        self.habilitar(); otra = dict(self.p, id='otra_fixture')
        self.raw['personas'].append(otra)
        self.assertTrue(self.ns['a_json'](None, self.e, self.p, otra)['texto_oculto'])
        self.raw['asignaciones'].append({'cliente_id': 'revocado', 'persona_id': otra['id'], 'silla': 'account'})
        self.assertFalse(self.ns['a_json'](None, self.e, self.p, otra)['texto_oculto'])

    def test_act_false_no_equivale_direccion_amplia(self):
        self.habilitar(); self.p['puestos'] = ['direccion']; self.act['revocado'] = False
        self.assertTrue(self.ns['a_json'](None, self.e, self.p, self.p)['texto_oculto'])

    def test_global_legitimo_y_vacio_no_es_global(self):
        self.e['cliente_id'] = None
        self.assertFalse(self.ns['a_json'](None, self.e, self.p, self.p)['texto_oculto'])
        self.e['cliente_id'] = ''
        self.assertTrue(self.ns['a_json'](None, self.e, self.p, self.p)['texto_oculto'])


if __name__ == '__main__': unittest.main()
