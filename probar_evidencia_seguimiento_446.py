import copy
import unittest
from evidencia_seguimiento_446 import proyectar


class Evidencia446(unittest.TestCase):
    def setUp(self):
        self.k = dict(reglas=[dict(cliente_id='c1', estado_cohorte='confirmada',
            tipo_cohorte='metodo_actual_recurrente', cadencia_dias=15, responsable_role='trafficker')],
            historial={'c1': [dict(id='r1', cliente_id='c1', fecha='2026-09-20',
                fecha_ambigua=False, registro='registro_historico', celebrada_confirmada=False,
                fuente='privada', transcripcion='NO PUBLICAR', precio=1470)]},
            clientes=[{'id':'c1'}], personas=[dict(id='tomas', estado='activo', puestos=['direccion']),
                dict(id='carla', estado='activo', puestos=['account']),
                dict(id='paid', estado='activo', puestos=['trafficker'])],
            asignaciones=[dict(cliente_id='c1', silla='trafficker', persona_id='paid', desde='2026-10-01')],
            real_id='tomas', vista_id='carla', hoy='2026-10-04', activo=lambda c:True,
            permite=lambda p,c:True)

    def rows(self):
        return proyectar(**self.k)['filas']

    def test_registro_no_es_asistencia_y_owner_actual_no_historico(self):
        r=self.rows()[0]
        self.assertEqual(r['ultimo_registro_historico'], '2026-09-20')
        self.assertEqual(r['responsable_actual_id'], 'paid')
        self.assertIsNone(r['responsable_historico'])
        for k in ('cumplimiento','celebracion_confirmada','proxima_revision','ultima_reunion_confirmada'):
            self.assertIsNone(r[k])
        self.assertNotIn('1470', str(r)); self.assertNotIn('NO PUBLICAR', str(r))

    def test_partial_empty_is_unknown_not_absence(self):
        self.k['historial']={}
        r=self.rows()[0]
        self.assertEqual(r['registros_historicos_observados'],0)
        self.assertIsNone(r['cumplimiento'])
        self.assertEqual(r['cobertura'],'parcial')

    def test_real_vista_intersection_active(self):
        self.k['permite']=lambda p,c:p['id']=='tomas'
        self.assertEqual(self.rows(),[])
        self.k['permite']=lambda p,c:True
        self.k['activo']=lambda c:False
        self.assertEqual(self.rows(),[])

    def test_duplicate_client_person_policy_denied(self):
        for field in ('clientes','personas','reglas'):
            k=copy.deepcopy(self.k);k[field].append(copy.deepcopy(k[field][0]))
            self.assertEqual(proyectar(**k)['filas'],[])

    def test_revoked_and_duplicate_roles(self):
        for change in ({'estado':'baja'}, {'activo':False}, {'puestos':['account','account']}):
            k=copy.deepcopy(self.k);k['personas'][1].update(change)
            self.assertEqual(proyectar(**k)['filas'],[])

    def test_ambiguous_invalid_future_dates_not_latest(self):
        row=self.k['historial']['c1'][0]
        for change in ({'fecha':'2026-02-30'}, {'fecha':'2026-10-05'}, {'fecha_ambigua':True}, {'cliente_id':'otro'}):
            k=copy.deepcopy(self.k);k['historial']['c1'][0].update(change)
            r=proyectar(**k)['filas'][0]
            self.assertEqual(r['registros_historicos_observados'],0)
            self.assertIsNone(r['ultimo_registro_historico'])

    def test_global_id_conflict_before_scope_and_replay(self):
        r=self.k['historial']['c1'][0]
        self.k['historial']['c1'].append(copy.deepcopy(r))
        self.assertEqual(self.rows()[0]['registros_historicos_observados'],1)
        self.k['historial']['other']=[dict(r, cliente_id='other')]
        self.assertEqual(self.rows()[0]['registros_historicos_observados'],0)

    def test_no_15d_to_other_cohort_or_unknown_owner(self):
        for change in ({'estado_cohorte':'pendiente'}, {'cadencia_dias':True}, {'responsable_role':'account'}):
            k=copy.deepcopy(self.k);k['reglas'][0].update(change)
            self.assertEqual(proyectar(**k)['filas'],[])
        self.k['personas'][2]['estado']='baja'
        self.assertIsNone(self.rows()[0]['responsable_actual_id'])


if __name__=='__main__':unittest.main()
