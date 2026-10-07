import copy,json,os,tempfile,unittest
from pathlib import Path
from fuentes_crm import ultima_valida_490 as W
from fuentes_crm.adaptadores_ultima_valida_493 import adaptar
from fuentes_crm import pipeline_ultima_valida_496 as P
NOW='2026-10-04T12:00:00Z'
WINDOW={'tipo':'medicion_pasada','desde':'2026-10-01T00:00:00Z','hasta':'2026-10-04T11:00:00Z'}
ROW={'id':'op-fixture','contactId':'contact-fixture','createdAt':'2026-01-01T00:00:00Z','status':'open','monetaryValue':99}
def read(resource='oportunidades_abiertas',rows=None,window=None,**kw):
    return adaptar(resource,[{'opportunities':[copy.deepcopy(ROW)] if rows is None else rows}],subcuenta_id='sub-fixture',
                   intentado_en=NOW,observado_en=NOW,ventana=window,**kw)
def merge(es):return W.actualizar({'version':W.VERSION,'recursos':{}},es,NOW)
class Stock503(unittest.TestCase):
    def test_stock_old_creation_no_fake_period_privacy(self):
        e=read();d=merge([e]);r=d['recursos'][W.clave(e)]
        self.assertIsNone(r['ultima_valida']['ventana']);self.assertEqual(r['ultima_valida']['datos'][0]['estado'],'open')
        self.assertNotIn('monetaryValue',json.dumps(d));self.assertEqual(e['definicion'],'stock_oportunidades_abiertas490.3')
    def test_closed_unknown_future_duplicate_rejected(self):
        for rows in [[dict(ROW,status=x)] for x in ('won','lost','abandoned',None)]+[[dict(ROW,createdAt='2026-11-01T00:00:00Z')],[ROW,ROW]]:
            e=read(rows=rows);self.assertEqual(e['codigo_error'],'esquema_invalido');self.assertIsNone(merge([e])['recursos'][W.clave(e)]['ultima_valida'])
    def test_window_forbidden_stock_and_required_cohort(self):
        with self.assertRaises(ValueError):read(window=WINDOW)
        with self.assertRaises(ValueError):read(resource='oportunidades')
        e=read(resource='oportunidades',window=WINDOW,rows=[dict(ROW,status='won')])
        self.assertIsNotNone(merge([e])['recursos'][W.clave(e)]['ultima_valida'])
    def test_resource_keys_independent_same_opid(self):
        stock=read();cohort=read(resource='oportunidades',window=WINDOW)
        self.assertNotEqual(W.clave(stock),W.clave(cohort));self.assertEqual(len(merge([stock,cohort])['recursos']),2)
    def test_verified_zero_and_partial_empty(self):
        e=read(rows=[]);self.assertIsNone(merge([e])['recursos'][W.clave(e)]['ultima_valida'])
        e=read(rows=[],fin_paginacion=True);self.assertEqual(merge([e])['recursos'][W.clave(e)]['ultima_valida']['datos'],[])
    def test_explicit_migration_preserves_every_record_and_input(self):
        e=read(resource='oportunidades',window=WINDOW);old=merge([e]);old['version']='490.2';before=copy.deepcopy(old)
        with self.assertRaises(ValueError):W.validar_estado(old)
        with self.assertRaises(ValueError):W.actualizar(old,[],NOW)
        migrated=W.migrar_490_2(old);self.assertEqual(migrated['recursos'],old['recursos']);self.assertEqual(old,before);self.assertEqual(migrated['version'],'490.3')
        e['version']='490.2'
        with self.assertRaises(ValueError):merge([e])
    def test_invalid_legacy_not_laundered(self):
        old=merge([read()]);old['version']='490.2'
        with self.assertRaises(ValueError):W.migrar_490_2(old)
        old=merge([read(resource='oportunidades',window=WINDOW)]);old['version']='490.2'
        next(iter(old['recursos'].values()))['ultima_valida']['datos'][0]['creada']=999999999999999
        with self.assertRaises(ValueError):W.migrar_490_2(old)
    def test_reader_does_not_migrate_file_and_public_stock_unit(self):
        scope=lambda:{'actor_real':'actor','actor_vista':'actor','firma_sha256':'a'*64,'clientes':[{'cliente_id':'cid','subcuenta_id':'sub-fixture'}]}
        with tempfile.TemporaryDirectory() as t:
            path=Path(t).resolve()/'state.json';os.chmod(path.parent,0o700)
            old=merge([read(resource='oportunidades',window=WINDOW)]);old['version']='490.2'
            path.write_text(json.dumps(old));path.chmod(0o600);b=path.read_bytes()
            with self.assertRaises(ValueError):P.leer_proyeccion(path,scope,NOW)
            self.assertEqual(path.read_bytes(),b)
            d=P.proyectar(merge([read()]),P._ambito(scope),NOW)
            r=next(x for x in d['clientes'][0]['recursos'] if x['recurso']=='oportunidades_abiertas')
            self.assertEqual(d['version'],'496.2');self.assertEqual(r['unidad'],'oportunidades_abiertas_observadas')
            self.assertIsNone(r['observaciones'][0]['ventana']);self.assertEqual(r['conteo_observado'],1)
            for word in ('sub-fixture','op-fixture','contact-fixture','"venta"','"tasa"'):self.assertNotIn(word,json.dumps(d))
if __name__=='__main__':unittest.main()
