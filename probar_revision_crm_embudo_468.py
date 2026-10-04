"""468 independiente: cadenas reales466/467 con fixtures privados, sin HTTP/DB/proveedor."""
import copy,json,unittest
from unittest.mock import patch
import ghl_embudo_observado_466 as G
import probar_ghl_embudo_observado_466 as F
import probar_crm_embudo_api_467 as Q

class Revision468(unittest.TestCase):
    def setUp(self):self.f=Q.Embudo467();self.f.setUp()
    def tearDown(self):self.f.tearDown()
    def chain(self,v):
        r=G.preparar(v,'c1','subCuentaA',self.f.start,self.f.end,self.f.cut)
        self.f.doc['clientes'][0]['medicion']=r['agregado'];self.f.persist()
        return self.f.read()
    def test_creation_not_start_and_no_other_result_inference(self):
        v=F.base();v['citas'][0]['inicio']=F.ms('2027-01-01T12:00:00+00:00')
        d=self.chain(v);m=d['medicion']
        self.assertEqual(m['eventos_periodo']['cita']['eventos_observados'],1)
        for st in ('contacto','respuesta','cualificado','asistencia','venta'):
            self.assertEqual(m['cohorte']['etapas'][st],{'observados':0,'estado':'desconocido'})
        t=json.dumps(d)
        for word in ('contactA','apptA','privado@example','subCuentaA','private-lead','tasa_sobre_recibidos','subcuenta_huella'):
            self.assertNotIn(word,t)
    def test_cancelled_historical_booking_and_missing_date_unknown(self):
        v=F.base();v['citas'][0]['estado']='cancelled';d=self.chain(v)
        self.assertEqual(d['medicion']['eventos_periodo']['cita']['eventos_observados'],1)
        self.assertTrue(any('cancelado' in x for x in d['medicion']['limites']))
        v['citas'][0]['creada']=None;d=self.chain(v)
        self.assertEqual(d['medicion']['eventos_periodo']['cita']['estado'],'desconocido')
    def test_orphan_manual_or_conflicting_contact_no_reception_invented(self):
        for change in ('missing','manual','conflict'):
            v=F.base()
            if change=='missing':v['leads']=[]
            if change=='manual':v['leads'][0]['es_lead']=False
            if change=='conflict':v['leads'].append({**copy.deepcopy(v['leads'][0]),'creado':v['leads'][0]['creado']+1000})
            d=self.chain(v)
            self.assertEqual(d['medicion']['cohorte']['estado'],'desconocido')
            self.assertEqual(d['medicion']['eventos_periodo']['cita']['estado'],'desconocido')
    def test_prior_reception_keeps_period_booking_not_new_cohort(self):
        v=F.base();v['leads'][0]['creado']=F.ms('2026-09-20T12:00:00+00:00');d=self.chain(v)
        self.assertEqual(d['medicion']['cohorte']['recibidos_observados'],0)
        self.assertEqual(d['medicion']['eventos_periodo']['cita']['eventos_observados'],1)
    def test_subaccount_hash_reused_foreign_client_global_denied(self):
        row=copy.deepcopy(self.f.doc['clientes'][0]);row['cliente_id']='c2';row['medicion']['grupos'][0]['cliente_id']='c2'
        self.f.doc['clientes'].append(row);self.f.persist()
        self.f.reject(503,lambda:self.f.read(rid='account'))
    def test_unsupported_qualified_or_sales_rejected_even_pinned(self):
        for st in ('cualificado','asistencia','venta'):
            old=copy.deepcopy(self.f.doc);m=self.f.doc['clientes'][0]['medicion']['grupos'][0];m['cohorte']['etapas'][st].update(observados=1,estado='parcial')
            m['eventos_periodo'][st].update(eventos_observados=1,leads_unicos_observados=1,estado='parcial')
            self.f.persist();self.f.reject(503,lambda:self.f.read());self.f.doc=old
    def test_foreign_denied_before_IO_and_final_grant_revoked(self):
        with patch.object(Q.A,'cargar',side_effect=AssertionError('no IO')):
            self.f.reject(403,lambda:self.f.read(rid='foreign'))
        real=Q.A.cargar;calls=[0]
        def revoke(*a,**k):
            d=real(*a,**k);calls[0]+=1
            if calls[0]==2:self.f.S.E.crudo['asignaciones']=[]
            return d
        with patch.object(Q.A,'cargar',side_effect=revoke):self.f.reject(403,lambda:self.f.read(rid='account'))
    def test_errors_partial_and_missing_client_not_zero(self):
        v=F.base();v['errores']=['no-publicar-error-contacto'];d=self.chain(v)
        self.assertEqual(d['medicion']['cohorte']['estado'],'parcial');self.assertNotIn('no-publicar',json.dumps(d))
        self.f.doc['clientes']=[];self.f.persist();self.f.reject(503,lambda:self.f.read())

if __name__=='__main__':unittest.main()
