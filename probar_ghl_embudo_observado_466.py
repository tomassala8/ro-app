"""Fixtures sintéticos: no lee cachés, archivos privados ni proveedores."""
import copy
from datetime import datetime
import json
import unittest
from ghl_embudo_observado_466 import preparar

DESDE='2026-10-01T00:00:00+02:00'
HASTA='2026-10-03T23:59:59+02:00'
CORTE='2026-10-04T12:00:00+02:00'
def ms(s): return int(datetime.fromisoformat(s).timestamp()*1000)
def base():
    return {'leads':[{'contacto':'contactA','creado':ms('2026-10-01T08:00:00+02:00'),'es_lead':True,
                      'privado':{'correo':'privado@example.invalid','telefono':'+34999999999'},'humano_min':1,'respondio':True}],
            'citas':[{'id':'apptA','contacto':'contactA','creada':ms('2026-10-02T08:00:00+02:00'),
                      'inicio':ms('2026-10-15T08:00:00+02:00'),'estado':'showed'}], 'errores':[]}
def run(v=None,cid='cliente-prueba',sid='subCuentaA'):
    return preparar(base() if v is None else v,cid,sid,DESDE,HASTA,CORTE)

class Adaptador(unittest.TestCase):
    def test_salida_minima_privacidad_y_etapas(self):
        r=run();self.assertEqual(r['version'],'466.1');self.assertEqual([e['etapa'] for e in r['eventos']],['recibido','cita'])
        for e in r['eventos']:
            self.assertEqual(set(e),{'cliente_id','source','lead_id','event_id','etapa','fecha'})
            self.assertEqual(len(e['lead_id']),64);self.assertEqual(len(e['event_id']),64)
        text=json.dumps(r);self.assertNotIn('privado@example',text);self.assertNotIn('contactA',text);self.assertNotIn('+349',text)
        g=r['agregado']['grupos'][0];self.assertEqual(g['cohorte']['recibidos_observados'],1)
        for etapa,v in g['cohorte']['etapas'].items():self.assertIsNone(v['valor']);self.assertIsNone(v['tasa_sobre_recibidos'])
        self.assertEqual(g['cohorte']['etapas']['cita']['observados'],1)
        self.assertFalse(r['cobertura'][0]['completa'])
    def test_cancelada_es_reserva_historica_no_asistencia(self):
        v=base();v['citas'][0]['estado']='cancelled';r=run(v)
        self.assertEqual([e['etapa'] for e in r['eventos']],['recibido','cita'])
        self.assertIn('canceladas',r['agregado']['limites'][-1])
    def test_fecha_reserva_no_inicio(self):
        e=run()['eventos'][1];self.assertEqual(e['fecha'],'2026-10-02T06:00:00+00:00')
        v=base();v['citas'][0].pop('creada');r=run(v);self.assertEqual(len(r['eventos']),1)
    def test_lead_solo_true(self):
        for flag in [1,'true',False,None]:
            v=base();v['leads'][0]['es_lead']=flag;self.assertEqual(run(v)['eventos'],[])
    def test_epoch_estricto(self):
        for fecha in [True,'1790834400000',None,-1,float('inf'),float('nan'),1.25,10**1000]:
            v=base();v['leads'][0]['creado']=fecha;self.assertEqual(run(v)['eventos'],[])
    def test_duplicate_identico_replay(self):
        v=base();v['leads']*=2;v['citas']*=2;r=run(v);self.assertEqual(len(r['eventos']),2)
        self.assertEqual(r['diagnosticos']['contacto_replay'],1);self.assertEqual(r['diagnosticos']['cita_replay'],1)
    def test_contacto_conflictivo_todas_variantes_excluidas(self):
        v=base();otro=copy.deepcopy(v['leads'][0]);otro['es_lead']=False;v['leads'].append(otro)
        r=run(v);self.assertEqual(r['eventos'],[]);self.assertEqual(r['diagnosticos']['contacto_conflicto'],1)
        v['leads'].reverse();self.assertEqual(run(v),r)
    def test_cita_conflictiva_todas_excluidas(self):
        v=base();otro=copy.deepcopy(v['citas'][0]);otro['creada']+=1000;v['citas'].append(otro)
        r=run(v);self.assertEqual(len(r['eventos']),1);self.assertEqual(r['diagnosticos']['cita_conflicto'],1)
    def test_variante_invalida_no_recupera_limpia(self):
        v=base();otro=copy.deepcopy(v['leads'][0]);otro['x']=float('nan');v['leads'].append(otro)
        self.assertEqual(run(v)['eventos'],[])
    def test_namespace_sid(self):
        a=run();b=run(sid='subCuentaB');self.assertNotEqual(a['eventos'][0]['lead_id'],b['eventos'][0]['lead_id'])
    def test_contacto_exact_no_alias(self):
        v=base();v['citas'][0]['contacto']='ContactA';r=run(v);self.assertEqual(len(r['eventos']),1)
    def test_identidades_sin_pii(self):
        for ident in ['a@example.invalid','+34999999999','34999999999','a b','a/b','a'*161,None,1]:
            v=base();v['leads'][0]['contacto']=ident;self.assertEqual(run(v)['eventos'],[])
        for cid in ['Nombre cliente','a@example.invalid',None,'Cliente']:
            with self.assertRaises(ValueError):run(cid=cid)
    def test_no_futuro_y_no_cita_antes_lead(self):
        v=base();v['citas'][0]['creada']=ms('2026-10-05T00:00:00+02:00');self.assertEqual(len(run(v)['eventos']),1)
        v=base();v['citas'][0]['creada']=ms('2026-09-30T00:00:00+02:00');self.assertEqual(len(run(v)['eventos']),1)
        v=base();v['leads'][0]['creado']=ms('2026-10-05T00:00:00+02:00');self.assertEqual(run(v)['eventos'],[])
    def test_recibido_antes_ventana_cita_periodo_no_nueva_cohorte(self):
        v=base();v['leads'][0]['creado']=ms('2026-09-20T08:00:00+02:00');g=run(v)['agregado']['grupos'][0]
        self.assertEqual(g['cohorte']['recibidos_observados'],0)
        self.assertEqual(g['eventos_periodo']['cita']['eventos_observados'],1)
    def test_ventanas_invalidas(self):
        for desde,hasta,corte in [(DESDE,HASTA,'2026-10-01T00:00:00Z'),('2026-10-01',HASTA,CORTE),
                                   ('2026-10-01T00:00:00+02:99',HASTA,CORTE),(HASTA,DESDE,CORTE),
                                   (DESDE,HASTA,'2026-10-04T00:00:00+14:01')]:
            with self.assertRaises(ValueError):preparar(base(),'cliente-prueba','subCuentaA',desde,hasta,corte)
    def test_vacia_desconocida_no_cero_certificado(self):
        r=run({'leads':[],'citas':[]});g=r['agregado']['grupos'][0]
        self.assertEqual(g['cohorte']['estado'],'desconocido');self.assertIsNone(g['cohorte']['etapas']['recibido']['valor'])
    def test_no_muta_fuente_y_diagnostico_no_texto(self):
        v=base();v['errores']=['token=secret'];antes=copy.deepcopy(v);r=run(v)
        self.assertEqual(v,antes);self.assertEqual(r['diagnosticos']['fuente_reporta_errores'],1);self.assertNotIn('secret',json.dumps(r))

if __name__=='__main__':unittest.main()
