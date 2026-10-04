"""510 independiente: contratos reales504→493→490, sólo memoria sintética."""
import copy
import unittest
from datetime import datetime,timezone
from fuentes_crm.colector_lecturas_504 import registrar,cerrar_recurso
from fuentes_crm.adaptadores_ultima_valida_493 import adaptar
from fuentes_crm.ultima_valida_490 import VERSION,actualizar,clave
from fuentes_crm.probar_colector_lecturas_504 import query,transport,NOW,START,LATER
from fuentes_crm.probar_adaptadores_ultima_valida_493 import RAW
def env(cs,**kw):
    a=cerrar_recurso(cs,**kw)
    return adaptar(a['recurso'],a['respuestas'],**{k:v for k,v in a.items() if k not in ('recurso','respuestas')})
def capture(q,t):return registrar(q,t,t['terminado_en'])
class Revision510(unittest.TestCase):
    def test_http_denial_does_not_return_last_valid_or_raw_error(self):
        good=env([capture(query('contactos_total'),transport('contactos_total'))],fin_explicito=True)
        old=actualizar({'version':VERSION,'recursos':{}},[good],NOW)
        for code in (401,403,404):
            denied=env([capture(query('contactos_total',emit=NOW),transport('contactos_total',status=code,kind='json_invalido',payload={'_error':'timeout','token':'private-fixture'},end=LATER,obs=None))])
            result=actualizar(old,[denied],LATER)['recursos'][clave(denied)]
            self.assertEqual(result['acceso'],'denegado');self.assertIsNone(result['ultima_valida'])
    def test_missing_http_status_success_clock_still_cannot_certify_end(self):
        q=query('oportunidades_abiertas');t=transport('oportunidades_abiertas',status=None)
        e=env([capture(q,t)])
        self.assertIsNone(e['ventana']);self.assertFalse(e['cobertura']['completa'])
        self.assertEqual(e['datos'][0]['estado'],'open')
    def test_query_not_response_defines_sid_and_stock(self):
        for patch in ({'status':'won'},{'status':'all'},{'limit':True},{'page':True},{'location_id':'foreign'}):
            q=query('oportunidades_abiertas');q['parametros'].update(patch)
            with self.assertRaises(ValueError):capture(q,transport('oportunidades_abiertas'))
        raw=copy.deepcopy(RAW['oportunidades']);raw['opportunities'][0]['locationId']='foreign'
        self.assertEqual(env([capture(query('oportunidades_abiertas'),transport('oportunidades_abiertas',payload=raw))])['codigo_error'],'esquema_invalido')
    def test_clock_instant_order_not_lexical_or_last_page_rejuvenation(self):
        one=capture(query('contactos_total'),transport('contactos_total',obs='2026-10-04T10:00:00Z'))
        self.assertEqual(one['transporte']['observado_en'],'2026-10-04T10:00:00+00:00')
        for field,value in [('observado_en','2026-10-04T10:00:00.000001Z'),('terminado_en','2026-10-04T09:58:59Z')]:
            t=transport('contactos_total');t[field]=value
            with self.assertRaises(ValueError):capture(query('contactos_total'),t)
    def test_later_page_cannot_backdate_or_mix_filters(self):
        one=capture(query(),transport());q=query(page=2,emit=NOW)
        q['parametros']['filters'][0]['value']['gte']='2026-09-01T00:00:00Z'
        two=capture(q,transport(end=LATER,obs=LATER))
        with self.assertRaises(ValueError):cerrar_recurso([one,two])
        q=query(page=2,emit=START);two=capture(q,transport(end=LATER,obs=LATER))
        with self.assertRaises(ValueError):cerrar_recurso([one,two])
    def test_messages_context_unknown_date_not_false_current_cohort(self):
        raw=copy.deepcopy(RAW['mensajes']);raw['messages']['messages'][0]['dateAdded']=None
        c=capture(query('mensajes'),transport('mensajes',payload=raw))
        e=env([c],fin_explicito=True)
        self.assertIsNone(e['datos'][0]['creado']);self.assertFalse(e['cobertura']['completa'])
        q=query('mensajes');q['parametros']['startTime']=0
        with self.assertRaises(ValueError):capture(q,transport('mensajes'))
    def test_capture_mutation_detected_and_empty_pages_not_end(self):
        c=capture(query('calendarios'),transport('calendarios',payload={'calendars':[]}))
        e=env([c]);self.assertFalse(e['cobertura']['vacio_confirmado'])
        c['transporte']['observado_en']='2026-10-05T00:00:00Z'
        with self.assertRaises(ValueError):cerrar_recurso([c],fin_explicito=True)
    def test_context_calendar_matches_transmitted_bounds_not_creation_cohort(self):
        q=query('citas');q['parametros']['startTime']+=1;q['parametros']['endTime']+=1
        e=env([capture(q,transport('citas'))])
        self.assertEqual(e['ventana']['tipo'],'inventario_programado')
        start=datetime.fromisoformat(e['ventana']['desde']);delta=start-datetime(1970,1,1,tzinfo=timezone.utc)
        self.assertEqual(delta.days*86400000+delta.seconds*1000+delta.microseconds//1000,q['parametros']['startTime'])
        self.assertNotIn('asistencia',e['datos'][0])
if __name__=='__main__':unittest.main()
