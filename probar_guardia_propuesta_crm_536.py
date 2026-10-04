"""Guardia real AST/P actual; sin POST real, servidor ni SQLite principal."""
import copy
import unittest
from probar_contrato_acciones_crm_533 import Contrato533


class Guardia536(Contrato533):
    def setUp(self):
        super().setUp()
        self.actor['puestos'] = ['operaciones']
        self.body['intencion_id'] = 'd80141d8-fc4c-48d2-a933-6719fef06993'

    # No heredar la caracterización específica de account como caso positivo.
    def test_regresion_propuesta_global_account_denegada_536(self):
        self.actor['puestos'] = ['account']
        self.assertEqual(self.call()[1][0], 403)

    def test_jefaturas_actuales_exactas_531(self):
        roles = {r for r, n in self.e.modulos['salud-crm'].items() if n == 'todo'}
        self.assertEqual(roles, {'direccion', 'finanzas_direccion', 'operaciones',
                                 'proyectos', 'jefa_crm', 'tecnico_altas'})
        for rol in sorted(roles):
            with self.subTest(rol=rol):
                self.actor['puestos'] = [rol]
                self.assertEqual(self.call(), (None, None))

    def test_forma_no_corresponde_denegada(self):
        for cambios in [{'objeto': 'Otro'}, {'cliente_id': 'cliente_fixture'},
                        {'cliente_id': ''}, {'herramienta': 'ghl'},
                        {'intencion_id': None}]:
            with self.subTest(cambios=cambios):
                self.assertEqual(self.call(body=dict(self.body, **cambios))[1][0], 403)

    def test_canonical_revocada_duplicada_o_roles_mutados(self):
        for change in [lambda e: e.crudo['personas'][0].update(estado='baja'),
                       lambda e: e.crudo['personas'][0].update(activo=False),
                       lambda e: e.crudo['personas'].append(copy.deepcopy(e.crudo['personas'][0])),
                       lambda e: e.crudo['personas'][0].update(puestos=['account']),
                       lambda e: e.crudo.update(personas=[]),
                       lambda e: e.crudo['personas'][0].update(puestos=['operaciones', 'operaciones'])]:
            with self.subTest(change=change):
                self.setUp()
                actor = copy.deepcopy(self.actor)
                change(self.e)
                self.assertEqual(self.call(actor=actor, vista=actor)[1][0], 403)

    def test_modulo_actual_reducido_a_suyo(self):
        self.e.modulos['salud-crm']['operaciones'] = 'suyo'
        self.assertEqual(self.call()[1][0], 403)

    def test_otro_modulo_visible_no_elude_contrato(self):
        self.assertIsNotNone(__import__('permisos').nivel_modulo(self.actor, self.e.modulos['mi-dia']))
        self.assertEqual(self.call(body=dict(self.body, modulo='mi-dia'))[1][0], 403)

    def test_identidad_no_usa_roles_clientes_para_elevar(self):
        actor = dict(self.actor, puestos=['account'])
        self.assertEqual(self.call(actor=actor, vista=actor)[1][0], 403)


if __name__ == '__main__':
    unittest.main()
