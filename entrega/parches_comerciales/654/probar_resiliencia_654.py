"""Fixtures ficticias: cadena real generar -> Paid331 -> medición291; sin proveedores."""
import copy, importlib.util, pathlib, sys, unittest, json
STAGE=pathlib.Path(__file__).parent
APP=STAGE
sys.path.append(str(APP))
if '--antes' in sys.argv:
    sys.argv.remove('--antes')
    for name in ['meta_informe_291','paid_mediciones_331','cerebro_operativo']:
        spec=importlib.util.spec_from_file_location(name,STAGE/'baseline'/(name+'.py'));m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m)
from cerebro_operativo import generar
spec=importlib.util.spec_from_file_location('fixtures_originales654',APP/'probar_cerebro_operativo.py');fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
HOY=fixtures.HOY

def documentos():
    a,c,o=fixtures.documentos()
    a['anuncios_generado']=HOY
    a['clientes'][0]['cliente_id']='bueno'
    a['clientes'][0]['gasto']['7d']=0
    fixtures.acreditar_paid331(a)
    c['subcuentas'][0].update(cliente_id='bueno',tipo='cliente',velocidad={'en_1h':1,'juzgables':3},whatsapp={'fallidos':1,'enviados':2})
    return a,c,o

def reglas(r,cid):return {x['regla_id'] for x in r['recomendaciones'] if x['cliente_id']==cid}

class Resiliencia654(unittest.TestCase):
    def base(self):
        a,c,o=documentos();self.assertIn('paid_sin_gasto',reglas(generar(a,c,o,HOY),'bueno'));return a,c,o
    def test_seccion_mala_conserva_otro_cliente_y_otra_seccion(self):
        for campo in ['velocidad','citas_30d','whatsapp','correo','embudo']:
            for bad in [True,5,'CSV-no-dict',[1],float('nan')]:
                with self.subTest(campo=campo,tipo=type(bad).__name__):
                    a,c,o=self.base();row=copy.deepcopy(c['subcuentas'][0]);row['cliente_id']='parcial';row[campo]=bad;c['subcuentas'].append(row)
                    antes=copy.deepcopy((a,c,o));original=json.dumps((a,c,o),sort_keys=True);r=generar(a,c,o,HOY)
                    self.assertEqual(json.dumps((a,c,o),sort_keys=True),original)
                    self.assertIn('paid_sin_gasto',reglas(r,'bueno'))
                    self.assertIn('crm_whatsapp_fallidos' if campo!='whatsapp' else 'crm_primera_hora',reglas(r,'parcial'))
                    gaps=next(x for x in r['cobertura']['clientes'] if x['cliente_id']=='parcial')['limites']
                    self.assertTrue(any(x['codigo']=='estructura_invalida_'+campo for x in gaps))
                    # Do not alter the row or timestamps supplied to the generator.
                    self.assertEqual(c['subcuentas'][0],antes[1]['subcuentas'][0])
    def test_paid_shapes_preservan_crm_y_bueno(self):
        for campo in ['equipo','cuenta_meta','leads','gasto','presupuesto_ads','anuncios','cpl_resumen']:
            for bad in ['CSV',[1],True]:
                with self.subTest(campo=campo,bad=bad):
                    a,c,o=self.base();row=copy.deepcopy(a['clientes'][0]);row['cliente_id']='parcial';row[campo]=bad;a['clientes'].append(row)
                    cr=copy.deepcopy(c['subcuentas'][0]);cr['cliente_id']='parcial';c['subcuentas'].append(cr)
                    r=generar(a,c,o,HOY);self.assertIn('paid_sin_gasto',reglas(r,'bueno'));self.assertIn('crm_whatsapp_fallidos',reglas(r,'parcial'))
    def test_anuncio_malo_no_oculta_anuncio_valido(self):
        a,c,o=self.base();a['clientes'][0]['anuncios']['anuncios']=['CSV',None,{'frecuencia_7d':4,'caida_ctr_pct':50}]
        r=generar(a,c,o,HOY);self.assertIn('paid_fatiga_doble',reglas(r,'bueno'));self.assertIn('crm_primera_hora',reglas(r,'bueno'))
    def test_huge_crm_unknown_no_cero(self):
        a,c,o=self.base();c['subcuentas'][0]['velocidad']['en_1h']=10**1000
        r=generar(a,c,o,HOY);self.assertNotIn('crm_primera_hora',reglas(r,'bueno'));self.assertIn('crm_whatsapp_fallidos',reglas(r,'bueno'))
        self.assertTrue(any(x['codigo']=='crm_primera_hora_sin_cohorte' for x in r['cobertura']['clientes'][0]['limites']))
    def test_huge_paid_serie_dependency_real(self):
        for campo in ['leads_meta','gasto_meta']:
            a,c,o=self.base();a['clientes'][0]['serie'][0][campo]=10**1000
            r=generar(a,c,o,HOY);self.assertIn('crm_whatsapp_fallidos',reglas(r,'bueno'))
            if campo=='gasto_meta':self.assertNotIn('paid_sin_gasto',reglas(r,'bueno'))
            else:
                self.assertIn('paid_sin_gasto',reglas(r,'bueno'))  # gasto 0 still explicitly observed
                self.assertTrue(any(x['codigo']=='leads_ausentes' for x in r['cobertura']['clientes'][0]['limites']))
    def test_collections_and_windows_unknown(self):
        for source,field in [(0,'ventanas'),(1,'ventanas'),(1,'fuentes')]:
            for bad in ['CSV',True,4]:
                a,c,o=self.base();docs=[a,c,o];docs[source][field]=bad
                r=generar(*docs,HOY);self.assertIn('crm_whatsapp_fallidos',reglas(r,'bueno'))
        for bad in ['CSV',True,4,{}]:
            a,c,o=self.base();a['clientes']=bad
            r=generar(a,c,o,HOY);self.assertIn('crm_whatsapp_fallidos',reglas(r,'bueno'))
    def test_identity_malformed_no_string_coercion(self):
        a,c,o=self.base();c['subcuentas'] += [{'cliente_id':x,'velocidad':{}} for x in [[],{},12,True]]
        r=generar(a,c,o,HOY);self.assertEqual([x['cliente_id'] for x in r['cobertura']['clientes']],['bueno'])
    def test_source_wrong_shape_still_other_source(self):
        a,c,o=self.base()
        for bad in ['CSV',[],True,3]:
            r=generar(bad,c,o,HOY);self.assertIn('crm_whatsapp_fallidos',reglas(r,'bueno'));self.assertEqual(r['cobertura']['fuentes']['captacion']['estado'],'ausente');self.assertIn({'fuente':'captacion','codigo':'documento_no_estructurado'},r['cobertura']['estructuras_invalidas'])
    def test_invalid_hoy_not_silenced(self):
        with self.assertRaises(ValueError):generar(hoy='not-a-day')

if __name__=='__main__':unittest.main()
