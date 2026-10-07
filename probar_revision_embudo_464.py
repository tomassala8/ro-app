"""Regresiones independientes464; motor puro y fixtures, sin archivos de clientes/red/DB."""
import copy
import unittest
from embudo_eventos import calcular, _hora
from probar_embudo_eventos import ev, cobertura, run, DESDE, HASTA, CORTE

class Revision464(unittest.TestCase):
    def setUp(self):
        self.events=[ev('a','recibido','2026-09-20T10:00:00Z'),ev('a','cualificado','2026-09-21T10:00:00Z')]
    def group(self,cov):return run(self.events,cov)['grupos'][0]
    def test_string_and_dictionary_stages_never_accredit_complete(self):
        for stages in ['recibido cualificado contacto respuesta cita asistencia venta',{'recibido':True,'cualificado':True},True, ['recibido','cualificado',{'bad':True}]]:
            c=cobertura();c[0]['etapas']=stages
            g=self.group(c)
            q=g['cohorte']['etapas']['cualificado']
            self.assertIsNone(q['valor'],repr(stages));self.assertIsNone(q['tasa_sobre_recibidos'])
            self.assertNotEqual(g['eventos_periodo']['cualificado']['estado'],'completo')
    def test_invalid_offsets_and_UTC_overflow_rejected_without_crash(self):
        for stamp in ['2026-09-21T10:00:00+02:99','2026-09-21T10:00:00+15:00','2026-09-21T10:00:00+14:01','9999-12-31T23:59:59-14:00']:
            self.assertIsNone(_hora(stamp),stamp)
            events=[self.events[0],{**self.events[1],'fecha':stamp}]
            first=run(events+events,cobertura());second=run(list(reversed(events+events)),cobertura())
            self.assertEqual(first,second)
            stage=first['grupos'][0]['cohorte']['etapas']['cualificado']
            self.assertIsNone(stage['valor']);self.assertIsNone(stage['tasa_sobre_recibidos'])
    def test_invalid_cut_rejected_as_controlled_error(self):
        for cut in ['2026-10-03T12:00:00+02:99','9999-12-31T23:59:59-14:00']:
            with self.assertRaises(ValueError):calcular(self.events,DESDE,HASTA,cut,cobertura())
    def test_july_policy_does_not_contaminate_september(self):
        c=cobertura();c.append({**c[0],'desde':'2026-07-01','hasta':'2026-07-31','criterio_version':'old-v0'})
        g=self.group(c)
        self.assertTrue(g['cualificacion']['criterio_comparable'])
        self.assertEqual(g['cohorte']['etapas']['cualificado']['tasa_sobre_recibidos'],1)
        self.assertEqual(g['eventos_periodo']['cualificado']['estado'],'completo')
    def test_overlapping_policy_still_blocks_comparability(self):
        c=cobertura();c.append({**c[0],'desde':'2026-09-15','hasta':'2026-09-25','criterio_version':'other-v2'})
        g=self.group(c)
        self.assertFalse(g['cualificacion']['criterio_comparable'])
        self.assertIsNone(g['cohorte']['etapas']['cualificado']['tasa_sobre_recibidos'])
        self.assertNotEqual(g['eventos_periodo']['cualificado']['estado'],'completo')
    def test_after_period_version_affects_cohort_not_period(self):
        c=cobertura();c.append({**c[0],'desde':'2026-10-01','hasta':CORTE,'criterio_version':'october-v2'})
        g=self.group(c)
        self.assertFalse(g['cualificacion']['criterio_comparable'])
        self.assertIsNone(g['cohorte']['etapas']['cualificado']['tasa_sobre_recibidos'])
        self.assertEqual(g['eventos_periodo']['cualificado']['estado'],'completo')
    def test_unrelated_source_version_does_not_fill_or_poison(self):
        c=cobertura();c.append({**c[0],'source':'other','criterio_version':'other-v2'})
        g=next(x for x in run(self.events,c)['grupos'] if x['source']=='formulario')
        self.assertTrue(g['cualificacion']['criterio_comparable'])
        self.assertEqual(g['cohorte']['etapas']['cualificado']['tasa_sobre_recibidos'],1)
    def test_valid_zone_and_real_version_mix_controls(self):
        self.assertEqual(_hora('2026-09-21T14:00:00+14:00'),_hora('2026-09-21T00:00:00Z'))
        events=self.events+[ev('b','recibido','2026-09-20T10:00:00Z'),{**ev('b','cualificado','2026-09-22T10:00:00Z'),'criterio_version':'other-v2'}]
        before=copy.deepcopy(events);g=run(events,cobertura())['grupos'][0]
        self.assertIsNone(g['cohorte']['etapas']['cualificado']['tasa_sobre_recibidos'])
        self.assertEqual(events,before)

if __name__=='__main__':unittest.main()
