"""Auditoría independiente384/385: sólo fixtures; sin red, hooks ni datasets reales."""
import copy,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import meta_diaria_api_385 as M
from fuentes_captacion.mediciones_diarias_384 import resumir
import probar_meta_diaria_385 as base_api
import probar_mediciones_diarias_384 as base_dto
class Independiente(unittest.TestCase):
 def setUp(self):
  a=base_api.Meta();a.setUp();self.S=a.s;self.raw=a.doc;self.out=copy.deepcopy(a.out)
  d=base_dto.Diario();d.setUp();self.doc=d.doc;self.ctx=d.ctx
 def read(self,real='r',vista='v',loader=None):
  with patch.object(M,'cargar',side_effect=loader or [(self.raw,'pin'),(self.raw,'pin')]),patch.object(M,'resumir',return_value=self.out):return M.listar(self.S,real,vista,'ok',path='/synthetic/candidato.json')
 def test_double_scope_inversion(self):
  self.S.P.ver=lambda p,a,cp:{'ok':a['tipo']!='inversion' or p['id']=='r'}
  dto=self.read();serialized=json.dumps(dto);self.assertNotIn('gasto',serialized);self.assertNotIn('moneda',serialized);self.assertNotIn('cpl',serialized);self.assertIn('leads_observados',serialized)
 def test_real_view_client_denied_before_io(self):
  for denied in ('r','v'):
   self.S.P.ver=lambda p,a,cp:{'ok':not(a['tipo']=='cliente_detalle' and p['id']==denied)}
   with patch.object(M,'cargar') as load:
    with self.assertRaises(M.ErrorMeta) as caught:self.read()
   self.assertEqual(caught.exception.codigo,403)
 def test_viewas_revoked_final_read(self):
  calls=[0]
  def load(*args):
   calls[0]+=1
   if calls[0]==2:self.S.P.ver=lambda p,a,cp:{'ok':a['tipo']!='ver_como'}
   return self.raw,'pin'
  with self.assertRaises(M.ErrorMeta) as caught:self.read(loader=load)
  self.assertEqual(caught.exception.codigo,403)
 def test_duplicate_or_inactive_client(self):
  for change in ('duplicate','inactive','ACT'):
   a=base_api.Meta();a.setUp();self.S=a.s
   if change=='duplicate':self.S.E.crudo['clientes'].append(copy.deepcopy(self.S.E.crudo['clientes'][0]))
   elif change=='inactive':self.S.E.crudo['clientes'][0]['activo']=False
   else:self.S.ACT.es_activo_id=lambda cid:False
   with patch.object(M,'cargar') as read:
    with self.assertRaises(M.ErrorMeta):M.listar(self.S,'r','v','ok',path='/synthetic')
    read.assert_not_called()
 def test_permission_change_after_last_read(self):
  calls=[0]
  def load(*args):
   calls[0]+=1
   if calls[0]==2:self.S.E.crudo['personas'][1]['estado']='baja'
   return self.raw,'pin'
  with self.assertRaises(M.ErrorMeta) as caught:self.read(loader=load)
  self.assertEqual(caught.exception.codigo,403)
 def test_partial_pagination_is_observed_not_census(self):
  d=copy.deepcopy(self.doc);d['cobertura']['paginas_completas']=False
  out=resumir(d,self.ctx,'ok','2026-10-04T00:00:01+00:00');self.assertEqual(out['leads_observados'],8);self.assertFalse(out['paginas_completas']);self.assertEqual(out['cobertura'],'filas_recibidas_no_censo');self.assertIsNone(out['leads_calificados']);self.assertIsNone(out['cpl_calificado']);self.assertIsNone(out['ventas'])
 def test_missing_campaign_field_not_zero(self):
  d=copy.deepcopy(self.doc);r=d['filas_diarias'][0];r['leads']=None;r['medicion']['tipo_lead']=None;r['medicion']['campos_observados'].remove('leads')
  out=resumir(d,self.ctx,'ok','2026-10-04T00:00:01+00:00');self.assertIsNone(out['leads_observados']);self.assertEqual(out['gasto_observado'],12)
 def test_duplicate_campaign_day_denied_globally(self):
  d=copy.deepcopy(self.doc);d['filas_diarias'].append(copy.deepcopy(d['filas_diarias'][0]));self.assertIsNone(resumir(d,self.ctx,'ok','2026-10-04T00:00:01+00:00'))
 def test_explicit_zero_valid(self):
  d=copy.deepcopy(self.doc)
  for r in d['filas_diarias']:r['leads']=r['gasto']=0
  out=resumir(d,self.ctx,'ok','2026-10-04T00:00:01+00:00');self.assertEqual(out['leads_observados'],0);self.assertEqual(out['gasto_observado'],0)
 def test_source_fifo_and_ancestor_symlink(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp).resolve();dep=root/'private';dep.mkdir(mode=0o700);p=dep/'source';p.write_text('{}');p.chmod(0o600)
   self.assertEqual(M._leer(p,100,True),b'{}');link=root/'alias';link.symlink_to(dep,target_is_directory=True)
   with self.assertRaises(OSError):M._leer(link/'source',100,True)
   fifo=dep/'fifo';os.mkfifo(fifo,0o600)
   with self.assertRaises(ValueError):M._leer(fifo,100,True)
 def test_json_duplicate_and_nan(self):
  for raw in (b'{"x":1,"x":2}',b'{"x":NaN}'):
   with self.assertRaises(ValueError):M._json(raw)
if __name__=='__main__':unittest.main()
