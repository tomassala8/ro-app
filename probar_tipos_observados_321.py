import unittest
from fuentes_horas.tipos_observados_321 import resumen_tareas_observadas as resumen

class Tipos321(unittest.TestCase):
    def calc(self, entradas, tareas=None, **kw):
        args = dict(cliente_ids={'c'}, tarea_ids={'t'}, usuario_ids={'u'}, observado_hasta='2026-10-03T12:00:00+02:00', fuente={'leido':'2026-10-03T10:00:00Z','sha256':'a'*64})
        args.update(kw)
        return resumen(entradas, tareas or [{'id':'t','cliente_id':'c'}], **args)
    def e(self, eid='1', h=2, date='2026-10-02T10:00:00+02:00', **kw):
        return dict(id=eid,task_id='t',usuario_id='u',inicio=date,horas=h,**kw)
    def test_real_zero_distinto_vacio(self):
        self.assertEqual(self.calc([self.e(h=0)])['filas'][0]['total_h'],0)
        self.assertEqual(self.calc([])['filas'],[])
    def test_max_registro_no_total_tarea(self):
        row=self.calc([self.e(h=2),self.e('2',3)])['filas'][0]
        self.assertEqual((row['total_h'],row['max_registro_h'],row['entradas']),(5,3,2))
    def test_ventana_estricta_y_zona(self):
        r=self.calc([self.e(date='2026-08-04T21:59:59Z'), self.e('2',date='2026-08-04T22:00:00Z')])
        self.assertEqual(r['filas'][0]['entradas'],1)
        self.assertEqual(r['ventana']['desde'],'2026-08-05')
    def test_future_naive_nan_bool_reject(self):
        for x in [self.e(date='2026-10-04T00:00:00Z'),self.e(date='2026-10-02T00:00:00'),self.e(h=float('nan')),self.e(h=True),self.e(h=-1)]:
            self.assertEqual(self.calc([x])['filas'],[])
    def test_duplicate_no_doble(self):
        self.assertEqual(self.calc([self.e(),self.e()])['filas'],[])
        self.assertEqual(self.calc([self.e()],[{'id':'t','cliente_id':'c'},{'id':'t','cliente_id':'c'}])['filas'],[])
    def test_scope_sin_filtrar_ajenos_a_dto(self):
        for kw in [dict(cliente_ids=set()),dict(tarea_ids=set()),dict(usuario_ids=set())]:
            r=self.calc([self.e()],**kw);self.assertEqual(r['filas'],[]);self.assertEqual(r['entradas_scope_rechazadas'],0)
    def test_large_observado_no_descarte_juicio(self):
        r=self.calc([self.e(h=12)])['filas'][0]
        self.assertEqual(r['total_h'],12);self.assertEqual(r['registros_mas10h'],1);self.assertFalse(r['duracion_cerrada_confirmada'])
    def test_source_fail_closed(self):
        for f in [{}, {'leido':'2026-10-04T10:00:00Z','sha256':'a'*64}, {'leido':'2026-10-03','sha256':'a'*64}]:
            with self.assertRaises(ValueError):self.calc([],fuente=f)
    def test_inputs_inmutables_sin_nombres(self):
        es=[self.e(descripcion='PRIVATE')];ts=[{'id':'t','cliente_id':'c','nombre':'PRIVATE'}]
        r=self.calc(es,ts);self.assertNotIn('PRIVATE',str(r));self.assertEqual(es[0]['descripcion'],'PRIVATE');self.assertEqual(ts[0]['nombre'],'PRIVATE')
    def test_ids_malformados_no_excepcion_ni_coercion(self):
        for campo in ('task_id','usuario_id'):
            for valor in ({'id':'t'}, ['t'], 1, None, True):
                e=self.e();e[campo]=valor
                self.assertEqual(self.calc([e])['filas'],[])
        e=self.e();e['usuario_id']=1
        self.assertEqual(self.calc([e],usuario_ids={'1'})['filas'],[])
        for valor in ({'id':'c'}, ['c'], None, 1):
            self.assertEqual(self.calc([self.e()],[{'id':'t','cliente_id':valor}])['filas'],[])
        for valor in ({'id':'t'}, ['t'], 1, None):
            self.assertEqual(self.calc([self.e()],[{'id':valor,'cliente_id':'c'}])['filas'],[])
    def test_entry_id_malformado_y_int_gigante(self):
        for valor in ({}, [], 1, None):
            e=self.e();e['id']=valor
            self.assertEqual(self.calc([e])['filas'],[])
        self.assertEqual(self.calc([self.e(h=10**10000)])['filas'],[])
    def test_overflow_total_falla_cerrado(self):
        with self.assertRaisesRegex(ValueError,'fuera de rango'):
            self.calc([self.e(h=1e308),self.e('2',h=1e308)])

if __name__=='__main__':unittest.main()
