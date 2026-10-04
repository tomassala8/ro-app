import copy, datetime as dt, unittest
from fuentes_horas.diario_238 import construir_diarios
from probar_horas_diarias_238 import fixture

class Extension(unittest.TestCase):
    def test_seven_cover_all_five_weekdays(self):
        for i in range(7):
            hoy=dt.date(2026,10,5)+dt.timedelta(days=i)
            h,p,u=fixture();h['meta']['generado']=str(hoy)+' 02:56'
            r=construir_diarios(h,p,u,str(hoy))['a']
            self.assertEqual(r['version'],'238.2');self.assertEqual(len(r['dias']),7)
            d=hoy; laborables=[]
            while len(laborables)<5:
                d-=dt.timedelta(days=1)
                if d.weekday()<5:laborables.append(str(d))
            self.assertTrue(set(laborables)<=set(x['fecha'] for x in r['dias']))
            self.assertEqual(r['hasta'],str(hoy-dt.timedelta(days=1)))
    def test_monday_positive_and_unknown(self):
        h,p,u=fixture();h['meta']['generado']='2026-10-05 02:56'
        h['entradas']=[{'id':'mon','usuario_id':1,'inicio':'2026-09-28T10:00:00+02:00','horas':2}]
        r=construir_diarios(h,p,u,'2026-10-05')['a'];self.assertEqual(r['dias'][0]['horas'],2)
        self.assertEqual(r['dias'][1]['estado'],'sin_dato');self.assertIsNone(r['dias'][1]['horas'])
    def test_zone_and_collision_extra_day(self):
        h,p,u=fixture();h['meta']['generado']='2026-10-05 02:56'
        h['entradas']=[{'id':'mon','usuario_id':2,'inicio':'2026-09-29T01:00:00+02:00','horas':2}]
        r=construir_diarios(h,p,u,'2026-10-05')['b'];self.assertEqual(r['dias'][0]['horas'],2)
        h['entradas'].append({**h['entradas'][0],'horas':3})
        self.assertIsNone(construir_diarios(h,p,u,'2026-10-05')['b']['dias'][0]['horas'])
if __name__=='__main__':unittest.main()
