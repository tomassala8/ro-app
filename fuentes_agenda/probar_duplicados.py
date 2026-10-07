"""Fixtures sintéticas del helper puro: nunca importa/ejecuta el generador."""
import ast
from copy import deepcopy
from pathlib import Path
import unittest
from duplicados import deduplicar


def evento(fuente='bookings', **campos):
    base = dict(id=(fuente if isinstance(fuente,str) else 'malformada')+'-fixture', fuente=fuente, persona_id='persona-fixture',
                inicio='2026-10-03T09:00:00+02:00', fin='2026-10-03T09:30:00+02:00',
                referencia_reunion='reunion-fixture', cliente_ref='cliente-fixture', atajos=[])
    return dict(base, **campos)


class Duplicados(unittest.TestCase):
    def separados(self, a, b):
        original = [a, b]
        resultado, fuera = deduplicar(original, {'persona-fixture': {'con_quien': {'reserva-a': 'Nombre Completo', 'reserva-b': 'Nombre Completo'}}})
        self.assertEqual(resultado, original)
        self.assertEqual(fuera, set())

    def test_referencia_compartida(self):
        a, b = evento(), evento('crm')
        salida, fuera = deduplicar([b, a])
        self.assertEqual(len(salida), 1)
        self.assertEqual(fuera, {b['id']})
        self.assertEqual(salida[0]['tambien_en'], ['crm'])
        self.assertEqual(salida[0]['origenes'], [{'fuente': 'bookings', 'id': a['id']}, {'fuente': 'crm', 'id': b['id']}])

    def test_no_muta_entrada(self):
        datos = [evento(), evento('crm')]; antes = deepcopy(datos)
        deduplicar(datos)
        self.assertEqual(datos, antes)

    def test_nombre_hora_no_bastan(self):
        self.separados(evento(referencia_reunion=None), evento('crm', referencia_reunion=None))

    def test_referencia_malformada(self):
        for ref in ([], {}, 7, '', 'Nombre Apellido', ' espacio', 'x'*201):
            with self.subTest(ref=type(ref).__name__):
                self.separados(evento(referencia_reunion=ref), evento('crm', referencia_reunion=ref))

    def test_invalid_ref_no_fallback(self):
        self.separados(evento(referencia_reunion=[], identidad_confirmada=True, participante_ref='p1'), evento('crm', referencia_reunion=[], identidad_confirmada=True, participante_ref='p1'))

    def test_identidad_canonica_confirmada(self):
        a = evento(referencia_reunion=None, participante_ref='p1', identidad_confirmada=True)
        b = evento('crm', referencia_reunion=None, participante_ref='p1', identidad_confirmada=True)
        self.assertEqual(len(deduplicar([a, b])[0]), 1)
        b['identidad_confirmada'] = 'true'
        self.separados(a, b)

    def test_dueno_diferente(self):
        self.separados(evento(), evento('crm', persona_id='otra-persona'))

    def test_duracion_diferente(self):
        self.separados(evento(), evento('crm', fin='2026-10-03T10:00:00+02:00'))

    def test_fechas_invalidas_y_zonas(self):
        for fin in ('bad', '2026-10-03T08:00:00+02:00', '2026-10-03T09:30:00', None):
            self.separados(evento(fin=fin), evento('crm', fin=fin))
        self.separados(evento(), evento('crm', inicio='2026-10-03T07:00:00Z', fin='2026-10-03T07:30:00Z'))

    def test_conflicto_cliente(self):
        self.separados(evento(), evento('crm', cliente_ref='otro-cliente'))
        self.separados(evento(), evento('crm', cliente_ref=[]))

    def test_conflicto_participante(self):
        self.separados(evento(identidad_confirmada=True, participante_ref='p1'), evento('crm', identidad_confirmada=True, participante_ref='p2'))

    def test_conflicto_sala(self):
        self.separados(evento(join_url='https://zoom.us/j/123'), evento('crm', join_url='https://zoom.us/j/456'))

    def test_atajo_tambien_detecta_sala(self):
        self.separados(evento(atajos=[{'h':'zoom','url':'https://zoom.us/j/123'}]), evento('crm', zoom_url='https://zoom.us/j/456'))

    def test_conserva_enlaces_distintos(self):
        a = evento(atajos=[{'h':'cita','url':'https://fixture.invalid/a'}], join_url='https://zoom.us/j/123?pwd=a')
        b = evento('crm', atajos=[{'h':'cita','url':'https://fixture.invalid/b'}], join_url='https://zoom.us/j/123?pwd=b')
        r, _ = deduplicar([a,b])
        self.assertEqual({x['url'] for x in r[0]['atajos']}, {'https://fixture.invalid/a','https://fixture.invalid/b','https://zoom.us/j/123?pwd=b'})

    def test_misma_fuente_no_fusiona(self):
        self.separados(evento(), evento(id='otra-reserva'))
        r, fuera = deduplicar([evento(), evento(id='otra-reserva'), evento('crm')])
        self.assertEqual(len(r),3); self.assertFalse(fuera)

    def test_zoom_sin_identidad_no_celebra(self):
        a, b = evento(referencia_reunion=None), evento('zoom', referencia_reunion=None, celebrada=True)
        self.separados(a,b)
        r,_ = deduplicar([a,b]); self.assertNotIn('celebrada',r[0])

    def test_zoom_confirmado_preserva_id_y_grabacion(self):
        z = evento('zoom', celebrada=True, atajos=[{'h':'grabacion','url':'https://zoom.us/rec/share/fixture'}])
        r, _ = deduplicar([evento(),z])
        self.assertTrue(r[0]['celebrada'])
        self.assertIn({'fuente':'zoom','id':z['id']},r[0]['origenes'])
        self.assertEqual(r[0]['atajos'][0]['url'],z['atajos'][0]['url'])

    def test_id_colision_no_retira_otra_persona(self):
        a,b = evento(),evento('crm',id='bookings-fixture',persona_id='otra-persona')
        self.separados(a,b)

    def test_datos_malformados_no_rompen(self):
        for campo in ({'fuente':[]},{'id':[]},{'persona_id':{}},{'fuente':'desconocida'}):
            self.separados(evento(**campo),evento('crm'))
        r,_ = deduplicar([evento(tambien_en=[{},'crm']),evento('crm')])
        self.assertEqual(r[0]['tambien_en'],['crm'])

    def test_no_transfiere_cliente_por_nombre(self):
        r,_ = deduplicar([evento(cliente_ref=None,cliente_nombre=None),evento('crm',cliente_nombre='Nombre privado')])
        self.assertIsNone(r[0]['cliente_ref']); self.assertIsNone(r[0]['cliente_nombre'])

    def test_integracion_estatica_sin_ejecucion(self):
        texto = Path(__file__).with_name('generar_agenda.py').read_text()
        arbol = ast.parse(texto)
        llamadas = [n for n in ast.walk(arbol) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='deduplicar']
        self.assertEqual(len(llamadas),1)
        self.assertNotIn('1200',texto)
        self.assertNotIn("mejor['celebrada']",texto)


if __name__ == '__main__':
    unittest.main(verbosity=2)
