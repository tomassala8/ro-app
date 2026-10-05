import unittest
from fuentes_captacion.cpm_referencia_417 import proyectar
class Revision419(unittest.TestCase):
 def fixture(self,stamp):
  return proyectar({'cuenta':'123','moneda':'EUR','leido':stamp,'errores':[],'periodos':{'2026-09-26|2026-10-02':{'cuenta':{'gasto':20,'impresiones':1000}}}},'cid','123',['2026-09-26','2026-10-02'],'EUR',activo=True,cuenta_unica=True,observado_hasta='2026-10-04')
 def test_invalid_calendar_rejected(self):self.assertIsNone(self.fixture('2026-02-30T04:48'))
 def test_offsets_invalid_rejected(self):
  for offset in ['+02:99','-02:99','+15:00','-15:00','+14:01','-14:01']:
   self.assertIsNone(self.fixture('2026-10-03T04:48'+offset))
 def test_valid_naive_and_offsets_preserved(self):
  for stamp in ['2026-10-03 04:48','2026-10-03T04:48Z','2026-10-03T04:48+14:00','2026-10-03T04:48-14:00','2026-10-03T04:48+02:59']:
   dto=self.fixture(stamp);self.assertIsNotNone(dto);self.assertEqual(dto['fecha_lectura'],stamp);self.assertIsNone(dto['zona'])
if __name__=='__main__':unittest.main()
