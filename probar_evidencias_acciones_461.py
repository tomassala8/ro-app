"""Contratos de propuestas: una copia no confirma fatiga ni transición comercial."""
import copy
import unittest
from cerebro_operativo import generar
from probar_cerebro_operativo import documentos, HOY


def anuncio():
    a, c, o = documentos()
    a['anuncios_generado'] = '2026-10-02T10:00:00+00:00'
    a['clientes'][0]['anuncios']['anuncios'] = [{'frecuencia_7d': 5, 'caida_ctr_pct': 50}]
    return a, c, o


def cards(a, c, o):
    return {r['regla_id']: r for r in generar(a, c, o, HOY)['recomendaciones']}


class EvidenciaAccion(unittest.TestCase):
    def test_copia_doble_es_propuesta_no_comparacion_de_ventanas(self):
        a, c, o = anuncio()
        a['ventanas'] = {'7d': ['2026-09-26', '2026-10-02'], '7d_prev': ['2026-09-26', '2026-10-02']}
        r = cards(a, c, o)['paid_fatiga_doble']
        self.assertEqual(r['certeza'], 'referencia_pendiente_confirmacion')
        self.assertIsNone(r['evidencias'][0]['periodo'])
        self.assertEqual(r['evidencias'][0]['fecha'], a['anuncios_generado'])
        self.assertIn('no diagnóstico', r['evidencias'][0]['texto'])
        self.assertIn('ID', r['criterio_entrega'])
        self.assertIn('zona', r['criterio_entrega'])
        self.assertIn('sin publicación', r['criterio_entrega'])

    def test_captacion_fresca_no_rejuvenece_anuncios_sin_sello(self):
        for sello in [None, '', 'no-fecha', '2026-09-20', '2026-10-04']:
            with self.subTest(sello=sello):
                a, c, o = anuncio()
                a['anuncios_generado'] = sello
                r = generar(a, c, o, HOY)
                self.assertNotIn('paid_fatiga_doble', {x['regla_id'] for x in r['recomendaciones']})
                self.assertIn('anuncios_sin_cobertura', {x['codigo'] for x in r['cobertura']['clientes'][0]['limites']})

    def test_no_se_inventa_senal_de_datos_invalidos_o_un_solo_umbral(self):
        for freq, caida in [(True, 50), (5, float('nan')), (5, float('inf')), (3, 50), (5, 39), (None, 50)]:
            with self.subTest(freq=freq, caida=caida):
                a, c, o = anuncio()
                a['clientes'][0]['anuncios']['anuncios'] = [{'frecuencia_7d': freq, 'caida_ctr_pct': caida}]
                self.assertNotIn('paid_fatiga_doble', cards(a, c, o))

    def test_error_lectura_no_reactiva_copia_con_doble_umbral(self):
        a, c, o = anuncio()
        a['clientes'][0]['anuncios']['errores'] = ['fixture']
        self.assertNotIn('paid_fatiga_doble', cards(a, c, o))

    def test_criterios_crm_exigen_evidencia_por_caso_no_un_check_generico(self):
        a, c, o = documentos()
        c['subcuentas'][0].update(velocidad={'en_1h': 0, 'juzgables': 2, 'cuatro_en_72h': 0, 'juzgables_72h': 2},
                                 whatsapp={'fallidos': 1, 'enviados': 2}, embudo={'estancados_72h': 1, 'cohorte_30d': 2})
        before = copy.deepcopy((a, c, o))
        rs = cards(a, c, o)
        self.assertEqual(len(rs), 4)
        for key in rs:
            self.assertNotEqual(rs[key]['criterio_entrega'], 'Registrar la comprobación y su resultado.')
            self.assertIn('fecha', rs[key]['criterio_entrega'])
        self.assertEqual(rs['crm_primera_hora']['ejecutor_operativo'], 'despacho')
        self.assertEqual(rs['crm_cuatro_intentos']['ejecutor_operativo'], 'despacho')
        self.assertIn('un mensaje no la sustituye', rs['crm_primera_hora']['criterio_entrega'])
        self.assertIn('duplicados', rs['crm_cuatro_intentos']['criterio_entrega'])
        self.assertIn('sin reenvío automático', rs['crm_whatsapp_fallidos']['criterio_entrega'])
        self.assertEqual((a, c, o), before)

    def test_legacy_parada_no_acredita_transicion_o_venta(self):
        a, c, o = documentos()
        c['subcuentas'][0]['embudo'] = {'estancados_72h': 1, 'cohorte_30d': 2}
        r = cards(a, c, o)['crm_etapas_paradas']
        self.assertEqual(r['certeza'], 'referencia_pendiente_confirmacion')
        self.assertIn('modificación general', r['motivo'])
        self.assertIn('updatedAt no acredita', r['criterio_entrega'])
        self.assertIn('venta confirmada', r['criterio_entrega'])
        self.assertIn('pendiente', r['evidencias'][0]['texto'])

    def test_denominador_invalido_no_se_repara_con_criterio(self):
        a, c, o = documentos()
        c['subcuentas'][0].update(velocidad={'en_1h': 3, 'juzgables': 2}, whatsapp={'fallidos': 3, 'enviados': 2}, embudo={'estancados_72h': 3, 'cohorte_30d': 2})
        self.assertEqual(cards(a, c, o), {})


if __name__ == '__main__':
    unittest.main()
