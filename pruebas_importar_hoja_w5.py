"""Lectores reales con entradas sintéticas; sin API, importación ni generación."""
import csv
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('importador_w5_prueba', APP / 'fuentes_informes/importar_hoja_w5.py')
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def rejilla(etiqueta='Septiembre 2026'):
    return {(1, 3): {'content': etiqueta}, (2, 2): {'content': 'Informe entregables'},
            (2, 3): {'content': 'Informes estadísticas'}, (2, 4): {'content': 'informado a cliente'},
            (2, 5): {'content': 'Enviado a cliente'}, (3, 1): {'content': 'Cliente Fixture'},
            (3, 2): {'content': 'Ver informe', 'url': 'https://example.org/informe'},
            (3, 4): {'content': 'FALSE'}, (3, 5): {'content': 'TRUE'}}


class Importacion(unittest.TestCase):
    def csv(self, filas, **kwargs):
        with tempfile.TemporaryDirectory() as td:
            ruta = Path(td) / 'fixture.csv'
            with ruta.open('w', newline='', encoding='utf-8-sig') as f:
                csv.writer(f).writerows(filas)
            return list(M.leer_csv(ruta, **kwargs))

    def test_h09_anio_escrito(self):
        filas, meses = M.leer_rejilla(rejilla(), 3, 5)
        self.assertEqual(meses, ['2026-09'])
        self.assertEqual(filas[0]['mes'], '2026-09')
        self.assertTrue(filas[0]['enviado'])
        self.assertFalse(filas[0]['informado_en_reunion'])
        self.assertEqual(filas[0]['enlace_informe'], 'https://example.org/informe')

    def test_anio_ausente_requiere_confirmacion(self):
        with self.assertRaises(ValueError):
            M.leer_rejilla(rejilla('Septiembre'), 3, 5)
        filas, _ = M.leer_rejilla(rejilla('Septimebre'), 3, 5, anio_confirmado=2026)
        self.assertEqual(filas[0]['mes'], '2026-09')
        self.assertEqual(M.periodo_de('Septiembre 2027', 2026), '2027-09')

    def test_no_mes_inferido(self):
        r = rejilla()
        r[(2, 6)] = {'content': 'Informe entregables'}
        with self.assertRaises(ValueError):
            M.leer_rejilla(r, 3, 6, anio_confirmado=2026)

    def test_cambio_anio_explicito(self):
        r = rejilla('Diciembre 2025')
        r[(1, 6)] = {'content': 'Enero 2026'}
        r[(2, 6)] = {'content': 'Informe entregables'}
        r[(3, 6)] = {'url': 'https://example.org/enero'}
        self.assertEqual(M.leer_rejilla(r, 3, 6)[1], ['2025-12', '2026-01'])

    def test_duplicados_bloque_y_columnas(self):
        for modificar in ('periodo', 'columna', 'cliente'):
            with self.subTest(modificar=modificar):
                r = rejilla()
                filas, cols = 3, 6
                if modificar == 'periodo':
                    r[(1, 6)] = {'content': 'Septiembre 2026'}
                    r[(2, 6)] = {'content': 'Informe entregables'}
                elif modificar == 'columna':
                    r[(2, 6)] = {'content': 'Enviado a cliente'}
                else:
                    r[(4, 1)] = {'content': 'Cliente Fixture'}
                    filas = 4
                with self.assertRaises(ValueError):
                    M.leer_rejilla(r, filas, cols)

    def test_cabecera_fecha_ambigua(self):
        for etiqueta in ('Septiembre 2025 / 2026', 'Septiembre y Octubre 2026'):
            with self.subTest(etiqueta=etiqueta), self.assertRaises(ValueError):
                M.leer_rejilla(rejilla(etiqueta), 3, 5)

    def test_h10_csv_minimo_sin_fallback(self):
        f = self.csv([['mes', 'cliente', 'enviado'], ['2026-09', 'Cliente Fixture', 'TRUE']])[0]
        self.assertTrue(f['enviado'])
        self.assertEqual(f['mes'], '2026-09')
        for campo in ('enlace_informe', 'enlace_estadisticas', 'informado_en_reunion'):
            self.assertIsNone(f[campo])

    def test_csv_reordenado_alias(self):
        f = self.csv([['Enviado a cliente', 'URL estadísticas', 'Nombre cliente', 'Periodo', 'Informado al cliente', 'Informe entregables'],
                      ['FALSE', 'https://example.org/stats', 'Fixture', 'Septiembre 2026', 'SI', 'https://example.org/report']])[0]
        self.assertFalse(f['enviado'])
        self.assertTrue(f['informado_en_reunion'])
        self.assertEqual(f['enlace_estadisticas'], 'https://example.org/stats')
        self.assertEqual(f['enlace_informe'], 'https://example.org/report')

    def test_csv_fecha_sin_anio(self):
        entrada = [['cliente', 'mes'], ['Fixture', 'Septiembre']]
        with self.assertRaises(ValueError):
            self.csv(entrada)
        self.assertEqual(self.csv(entrada, anio_confirmado=2026)[0]['mes'], '2026-09')

    def test_csv_ambiguo_obligatorias_anchura(self):
        entradas = [[['cliente', 'mes', 'periodo'], ['Fixture', '2026-09', '2026-09']],
                    [['mes', 'enviado'], ['2026-09', 'TRUE']],
                    [['cliente', 'mes'], ['Fixture']],
                    [['cliente', 'mes'], ['Fixture', '2026-09', 'TRUE']]]
        for entrada in entradas:
            with self.subTest(entrada=entrada), self.assertRaises(ValueError):
                self.csv(entrada)

    def test_csv_duplicados_cliente_periodo(self):
        with self.assertRaises(ValueError):
            self.csv([['cliente', 'mes'], ['Fixture', '2026-09'], ['Fixture', '2026-09']])
        self.assertEqual(len(self.csv([['cliente', 'mes'], ['Fixture', '2026-09'], ['Otro', '2026-09']])), 2)

    def test_valores_invalidos_no_silenciosos(self):
        for campo, valor in [('mes', '2026-13'), ('mes', '0000-09'), ('enviado', 'quizás'),
                             ('enlace_informe', 'TRUE'), ('enlace_informe', 'javascript:alert(1)'),
                             ('enlace_informe', 'https://usuario:clave@example.org/x'),
                             ('enlace_informe', 'https://example.org/x\nsecreto'),
                             ('enlace_informe', 'https://example.org:mal/x')]:
            entrada = [['cliente', 'mes', 'enviado', 'enlace_informe'], ['Fixture', '2026-09', '', '']]
            entrada[1][entrada[0].index(campo)] = valor
            with self.subTest(campo=campo, valor=valor), self.assertRaises(ValueError):
                self.csv(entrada)

    def test_rejilla_url_y_boolean_invalidos(self):
        for celda in [(3, 2), (3, 5)]:
            r = rejilla()
            r[celda] = {'url': 'TRUE'} if celda == (3, 2) else {'content': 'quizás'}
            with self.subTest(celda=celda), self.assertRaises(ValueError):
                M.leer_rejilla(r, 3, 5)

    def test_empate_identidad_y_sugerencias(self):
        catalogo = {'clientes': [{'id': 'a', 'nombre': 'Alpha Asesores'}, {'id': 'b', 'nombre': 'Beta'}]}
        def leer(ruta, *args):
            return catalogo if ruta.name == 'indice_clientes.json' else {'Confirmado': 'a', 'No cliente': '-'}
        filas = [{'cliente_hoja': n} for n in ('Alpha', 'AlphaAsesores', 'Alpha Asesores', 'Confirmado', 'No cliente')]
        with patch.object(M, 'leer', side_effect=leer):
            out, sin = M.emparejar(filas)
        self.assertIsNone(out[0]['cliente_id'])
        self.assertIsNone(out[1]['cliente_id'])
        self.assertEqual(out[0]['sugerencias_cliente_ids'], ['a'])
        self.assertEqual(out[2]['cliente_id'], 'a')
        self.assertEqual(out[3]['emparejamiento'], 'manual')
        self.assertTrue(out[4]['no_es_cliente'])
        self.assertEqual(sin, ['Alpha', 'AlphaAsesores'])

    def test_reemparejar_no_arrastra_descartado_anterior(self):
        idx = {'clientes': [{'id': 'a', 'nombre': 'Alpha'}]}
        with patch.object(M, 'leer', side_effect=lambda ruta, *args: idx if ruta.name == 'indice_clientes.json' else {}):
            filas, _ = M.emparejar([{'cliente_hoja': 'Alpha', 'no_es_cliente': True}])
            self.assertEqual(filas[0]['cliente_id'], 'a')
            self.assertNotIn('no_es_cliente', filas[0])

    def test_nombre_ambiguo_y_manual_inexistente(self):
        idx = {'clientes': [{'id': 'a', 'nombre': 'Alpha'}, {'id': 'b', 'nombre': 'Alpha'}]}
        with patch.object(M, 'leer', side_effect=lambda ruta, *args: idx if ruta.name == 'indice_clientes.json' else {}):
            filas, _ = M.emparejar([{'cliente_hoja': 'Alpha'}])
            self.assertIsNone(filas[0]['cliente_id'])
        with patch.object(M, 'leer', side_effect=lambda ruta, *args: idx if ruta.name == 'indice_clientes.json' else {'Alpha': 'ausente'}):
            with self.assertRaises(ValueError):
                M.emparejar([{'cliente_hoja': 'Alpha'}])


if __name__ == '__main__':
    unittest.main()
