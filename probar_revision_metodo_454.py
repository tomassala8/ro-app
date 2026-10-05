"""Revisión independiente452: fixtures privados y política actual, sin HTTP/DB/red."""
import copy,json,os,unittest
from unittest.mock import patch
import probar_metodo_evidencia_452 as Q

class Revision454(unittest.TestCase):
    def setUp(self):self.f=Q.Evidencia452();self.f.setUp()
    def tearDown(self):self.f.tearDown()
    def ev(self):return self.f.ev()
    def test_original_recommendation_preserved_exactly(self):
        real,vista=Q.E.canonicas(self.f.S,'ops','ops')
        expected=Q.M.estado_operativo(vista,real,self.f.S.E.crudo,Q.M.dia('2026-10-04'))
        code,actual=self.f.get();self.assertEqual(code,200)
        for r in actual['sugerencias']:r.pop('evidencia_por_revisar')
        self.assertEqual(actual,expected)
    def test_own_vs_view_cannot_expand_history_permission(self):
        with patch.object(Q.E,'leer_historial',side_effect=AssertionError('no history IO')):
            code,d=self.f.get(actor='ops',vista='paid');self.assertEqual(code,200)
            self.assertTrue(d['solo_lectura']);self.assertEqual(d['sugerencias'][0]['evidencia_por_revisar']['estado_fuente'],'no_autorizado')
            self.assertIsNone(d['sugerencias'][0]['evidencia_por_revisar']['registros_historicos_observados'])
    def test_ambiguous_foreign_historical_identity_rejects_global(self):
        self.f.doc['clientes']['foreign']=[dict(self.f.doc['clientes']['c1'][0],cliente_id='foreign')];self.f.persist()
        e=self.ev();self.assertEqual(e['estado_fuente'],'no_disponible');self.assertIsNone(e['registros_historicos_observados'])
    def test_ambiguous_date_not_counted_as_confirmed_meeting(self):
        self.f.doc['clientes']['c1'][0]['fecha_ambigua']=True;self.f.persist()
        e=self.ev();self.assertIsNone(e['celebracion_confirmada']);self.assertIsNone(e['ultimo_registro_historico'])
        code,d=self.f.get();self.assertEqual(code,200);self.assertIsNone(d['sugerencias'][0]['ultima_confirmada'])
    def test_final_read_permission_revocation(self):
        orig=Q.E.H.privado;calls=[0]
        def revoke(*a,**k):
            out=orig(*a,**k);calls[0]+=1
            if calls[0]==8:self.f.S.E.crudo['asignaciones']=[]
            return out
        with patch.object(Q.E.H,'privado',side_effect=revoke):self.assertEqual(self.f.get(actor='account')[0],403)
    def test_final_read_environment_rotation(self):
        orig=Q.E.H.privado;calls=[0]
        def rotate(*a,**k):
            out=orig(*a,**k);calls[0]+=1
            if calls[0]==8:os.environ['RO_HISTORIAL_REUNIONES']=''
            return out
        with patch.object(Q.E.H,'privado',side_effect=rotate):self.assertEqual(self.f.get()[0],403)
    def test_explicit_empty_observed_not_compliance(self):
        self.f.doc['clientes']['c1']=[];self.f.persist();e=self.ev()
        self.assertEqual(e['registros_historicos_observados'],0);self.assertEqual(e['cobertura'],'parcial')
        self.assertIsNone(e['celebracion_confirmada']);self.assertIsNone(e['participacion_trafficker_confirmada'])
    def test_client_not_in_inventory_unknown_never_zero(self):
        self.f.doc['clientes']={};self.f.persist();e=self.ev()
        self.assertEqual(e['estado_fuente'],'no_disponible')
        for k in ('registros_historicos_observados','ultimo_registro_historico','importado_el'):
            self.assertIsNone(e[k])
        self.assertEqual(e['cobertura'],'desconocida')
    def test_nonfinite_foreign_field_rejects_full_source(self):
        raw=json.dumps(self.f.doc).replace('"clientes":','"extra":1e999,"clientes":').encode()
        self.f.persist();(self.f.base/'reuniones.json').write_bytes(raw)
        import hashlib
        m=json.loads((self.f.base/'manifest.json').read_text());m['archivos']['reuniones.json']=hashlib.sha256(raw).hexdigest()
        (self.f.base/'manifest.json').write_text(json.dumps(m))
        self.assertEqual(self.ev()['estado_fuente'],'no_disponible')

if __name__=='__main__':unittest.main()
