from fuentes_captacion.cpm_referencia_417 import proyectar as cpm_referencia417
"""297A: fixtures sintéticas. AST evita importar config, objetivos o ejecutar el productor real."""
import ast
import contextlib
import io
import json
import math
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from fuentes_captacion.coherencia_crm_297 import conteo, proyectar, suma_observada

APP = Path(__file__).resolve().parent
SOURCE = APP / 'fuentes_captacion/generar_captacion.py'


class Pure(unittest.TestCase):
    def test_ausente_no_cero(self):
        p = proyectar({})
        for key in ('leads_meta_7d', 'leads_ghl_7d', 'contactos_historia', 'sin_estado_14d'):
            self.assertIsNone(p[key])
        self.assertEqual(p['medicion_integracion']['crm_estado'], 'sin_dato')

    def test_observado_cero_con_cobertura_no_exhaustiva(self):
        p = proyectar({'meta': {'leads': {'7d': 0}}, 'ghl': {'citas': {'14d': {'sin_estado': 0}}}}, {'leads_ghl_7d': 0})
        self.assertEqual(p['leads_meta_7d'], 0)
        self.assertEqual(p['sin_estado_14d'], 0)
        self.assertFalse(p['medicion_integracion']['conversion_medida'])

    def test_invalidos(self):
        for v in (None, '', '2', True, -1, 0.5, math.nan, math.inf, 10**1000, [], {}):
            self.assertIsNone(conteo(v))
        self.assertEqual(conteo(2.0), 2)

    def test_pocos_contactos_no_no_uso(self):
        for n in (0, 1, 4, 200):
            p = proyectar({'meta': {'leads': {'7d': 50}}}, {'sin_uso': True, 'leads_ghl_7d': n, 'contactos_total': n})
            for k in ('pct_llegan_crm', 'fuga', 'subcuenta_sin_uso'):
                self.assertIsNone(p[k])
            self.assertEqual(p['leads_ghl_7d'], n)

    def test_error_no_copia_completa(self):
        p = proyectar({'meta': {'leads': {'7d': 23}, 'error': 'fixture'}, 'ghl': {'error': 'fixture', 'citas': {'14d': {'sin_estado': 0}}}}, {'leads_ghl_7d': 9})
        self.assertIsNone(p['leads_meta_7d'])
        self.assertIsNone(p['leads_ghl_7d'])
        self.assertIsNone(p['sin_estado_14d'])
        self.assertEqual(p['medicion_integracion']['meta_estado'], 'error')

    def test_metadata_no_importa_ids_ni_nombres(self):
        p = proyectar({'nombre': 'PERSONAL_SYNTHETIC', 'lead_id': 'PRIVATE_SYNTHETIC', 'meta': {'leads': {'7d': 3}}})
        self.assertNotIn('SYNTHETIC', json.dumps(p))

    def test_sumas_no_zero_ni_parcial_completa(self):
        self.assertIsNone(suma_observada([]))
        self.assertIsNone(suma_observada([1, None]))
        self.assertEqual(suma_observada([0, 0]), 0)
        self.assertEqual(suma_observada([2.3, 1.2], 2), 3.5)


def fixture_main(cliente, crm=None):
    tree = ast.parse(SOURCE.read_text())
    defs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / 'clientes').mkdir()
        cap = {'clientes': [cliente], 'generado': '2026-10-03 08:00', 'datos_hasta': '2026-10-02',
               'ventanas': {'14d': ['2026-09-19', '2026-10-02']}, 'parametros': {}}
        fixture = {d / 'cap': cap, d / 'anu': {'cuentas': {}}, d / 'tot': {'subcuentas': {}},
                   d / 'personas.json': [], d / 'asignaciones.json': [], d / 'clientes.json': [],
                   d / 'crm/crm.json': {'subcuentas': [dict(crm, cliente_id='fixture')] if crm else []}}
        env = dict(Path=Path, json=json, re=__import__('re'), sys=__import__('sys'), date=date,
                   datetime=datetime, timedelta=timedelta, DATA=d, CAPTACION=d/'cap', ANUNCIOS=d/'anu',
                   GHL_TOTALES=d/'tot', SALIDA=d/'out/result.json', APP=d, TORRE_ZIP=d/'none',
                   CLASE_TXT={}, GADS_MUESTRA={}, GADS_PARADAS={}, GADS_FUERA_DE_WINDSOR=[], GADS_SIN_CLIENTE=[],
                   TORRE_A_APP={}, TECHO_CPL=35, ALARMA_CITA=100, ARRANQUE_CITA=45, FATIGA_FREC=3,
                   FATIGA_CAIDA_CTR=40, FATIGA_COSTE_X=2, MIN_IMPRESIONES=1000, GANADOR_VECES=10,
                   GANADOR_ARRANQUE=(3,45), ROJOS_TRAFFICKER=(2,4), ASISTENCIA=(75,60), CUENTAS_TRAFFICKER=16,
                   LIMITE_LECTOR_H=7, LIMITE_ANUNCIOS_H=30, conteo=conteo, suma_observada=suma_observada,
                   proyectar_crm=proyectar, cpm_referencia417=cpm_referencia417, ACT=SimpleNamespace(es_activo_id=lambda cid:False), OBJETIVOS=SimpleNamespace(leer=lambda: ({}, None)))
        exec(compile(ast.Module(body=defs, type_ignores=[]), str(SOURCE), 'exec'), env)
        env['leer'] = lambda path, defecto=None: fixture.get(Path(path), defecto)
        env['torre'] = lambda: None
        with contextlib.redirect_stdout(io.StringIO()):
            env['main']()
        return json.loads((d/'out/result.json').read_text())


class Producer(unittest.TestCase):
    def cliente(self, **campos):
        return dict(id='fixture', nombre='Fixture', severidad='ok', meta_activa=True, **campos)

    def test_main_no_fuga_grave_contadores_desiguales(self):
        out = fixture_main(self.cliente(meta={'leads': {'7d': 100}}, ghl_subcuenta={'id': 'x'}), {'leads_ghl_7d': 1, 'sin_uso': True})
        f = out['clientes'][0]
        self.assertIsNone(f['despacho']['pct_llegan_crm'])
        self.assertIsNone(f['despacho']['fuga'])
        self.assertEqual(f['severidad'], 'dato')
        self.assertNotIn('integracion', f['cuello'])
        self.assertEqual(f['despacho']['leads_meta_7d'], 100)
        self.assertEqual(f['despacho']['leads_ghl_7d'], 1)

    def test_main_ausente_no_salud_no_cero(self):
        f = fixture_main(self.cliente())['clientes'][0]
        self.assertEqual(f['severidad'], 'dato')
        self.assertIsNone(f['muestra']['leads_7d'])
        self.assertIsNone(f['despacho']['sin_estado_14d'])

    def test_main_diagnostico_heredado_solo_referencia(self):
        f = fixture_main(self.cliente(motivos=[{'texto': 'Los leads no van a GHL', 'clase_id': 'integracion', 'nivel': 'critico'}], problema_integracion=True))['clientes'][0]
        self.assertEqual(f['motivos'], [])
        self.assertEqual(f['diagnosticos_legacy'][0]['vigencia'], 'referencia_legacy_no_validada')
        self.assertEqual(f['severidad_torre_reglas'], 'ok')

    def test_main_coste_cita_no_cohorte_no_alarma(self):
        f = fixture_main(self.cliente(coste_por_cita={'coste_por_cita_14d': 500}))['clientes'][0]
        self.assertFalse(f['coste_por_cita']['alarma_100'])
        self.assertIsNone(f['quincenal']['coste_por_cita_14d'])
        self.assertEqual(f['quincenal']['coste_por_cita_referencia_14d'], 500)

    def test_main_historia_missing_no_suma_falsa(self):
        serie = [{'d': '2026-09-0'+str(i+1), 'meta': [None, None]} for i in range(7)]
        out = fixture_main(self.cliente(serie=serie))
        self.assertIsNone(out['clientes'][0]['historia']['hace_4_semanas']['leads_meta'])
        self.assertIsNone(out['resumen']['leads_7d_casa'])

    def test_main_techo_legacy_no_objetivo_actual(self):
        out = fixture_main(self.cliente(cpl={'ref': 12}))
        self.assertIsNone(out['resumen']['cuentas_en_techo_cpl'])
        self.assertIsNone(out['resumen']['cuentas_juzgables_cpl'])
        self.assertEqual(out['resumen']['referencia_legacy_cuentas_cpl']['con_ratio'], 1)
        self.assertEqual(out['fuentes'][0]['medicion'], 'copia')

    def test_fuente_sin_cuentas_no_bien(self):
        out = fixture_main(self.cliente())
        self.assertEqual(out['fuentes'][0]['estado'], 'sin_dato')


if __name__ == '__main__':
    unittest.main()
