import copy,hashlib,json,pathlib,unittest
from fuentes_verdad.candidato_alerta_290 import preparar,GASTO,CAPTACION,BLOQUEO
CID='cliente-sintetico';HASH=hashlib.sha256(CID.encode()).hexdigest()
def fixture():
 return {'generado':'2026-10-03','clientes':[{'cliente_id':CID,'motivos':[GASTO,BLOQUEO,CAPTACION],'gravedad':'critico','salud':47,'salud_sello':'anterior','bloqueo_callado':True,'bloqueos':{'dias_max':51.7,'tarea_id':'opaque-fixture'},'cuota':310,'leads_meta_7d':None},{'cliente_id':'otro','gravedad':'critico','motivos':['Otra señal'],'salud':63,'cuota':999}], 'comun':[{'id':CID,'gravedad':'critico','motivo':'Gasto en publicidad sin leads','n_motivos':3,'responsable_id':'fixture-persona'},{'id':'otro','gravedad':'critico','motivo':'Otra señal','n_motivos':1}], 'resumen':{'critico':2,'atencion':0,'bien':0,'nuevos':8},'carteras':[{'persona_id':'fixture-persona','principal':[CID,'otro']}],'cuota_empresa':{'referencia':777},'definiciones':{'referencia':'sin cambiar'},'reglas_gravedad':{'referencia':['sin cambiar']}}
def changes(a,b,p=''):
 if type(a)!=type(b):return [p]
 if isinstance(a,dict):
  return sum(([p+'/'+k] if k not in a or k not in b else changes(a[k],b[k],p+'/'+k) for k in set(a)|set(b)),[])
 if isinstance(a,list):
  return [p] if len(a)!=len(b) else sum((changes(x,y,p+'/'+str(i))for i,(x,y)in enumerate(zip(a,b))),[])
 return [] if a==b else [p]
class Tests(unittest.TestCase):
 def test_candidate_preserves_rest_and_source(self):
  d=fixture();before=copy.deepcopy(d);out,m=preparar(d,HASH);self.assertEqual(d,before);self.assertEqual(out['clientes'][1],before['clientes'][1]);self.assertEqual(out['comun'][1],before['comun'][1]);
  for k in ['generado','carteras','cuota_empresa','definiciones','reglas_gravedad']:self.assertEqual(out[k],before[k])
  self.assertEqual(out['clientes'][0]['cuota'],310);self.assertEqual(out['clientes'][0]['bloqueos'],before['clientes'][0]['bloqueos']);self.assertEqual(out['resumen']['nuevos'],8)
  self.assertEqual(set(changes(d,out)),set(m['whitelist_paths']))
 def test_no_fake_health_or_good(self):
  out,m=preparar(fixture(),HASH);r=out['clientes'][0];self.assertEqual(r['gravedad'],'atencion');self.assertIsNone(r['salud']);self.assertEqual(r['motivos'],[BLOQUEO]);self.assertEqual(r['referencia_anterior_290']['salud'],47);self.assertEqual(r['referencia_anterior_290']['motivos_paid_no_acreditados'],[GASTO,CAPTACION]);self.assertFalse(m['promovido'])
 def test_changed_evidence_denies(self):
  for edit in [lambda d:d['clientes'][0]['motivos'].append('Otra señal'),lambda d:d['clientes'][0].__setitem__('salud',40),lambda d:d['clientes'][0].__setitem__('bloqueo_callado',False),lambda d:d['comun'][0].__setitem__('n_motivos',2),lambda d:d['resumen'].__setitem__('critico',0)]:
   d=fixture();edit(d)
   with self.assertRaises(ValueError):preparar(d,HASH)
 def test_duplicate_and_foreign_identity_deny(self):
  for key in ['clientes','comun']:
   d=fixture();d[key].append(copy.deepcopy(d[key][0]));
   with self.assertRaises(ValueError):preparar(d,HASH)
  with self.assertRaises(ValueError):preparar(fixture(),hashlib.sha256(b'foreign').hexdigest())
 def test_reapplying_candidate_denies(self):
  out,_=preparar(fixture(),HASH)
  with self.assertRaises(ValueError):preparar(out,HASH)
 def test_prepared_private_actual_diff_only_whitelist(self):
  app=pathlib.Path(__file__).resolve().parent;s=app.parent/'RECUPERACION_CODEX_2026-10-03/staging290';m=json.loads((s/'manifest.json').read_text());raw=(app/'data/verdad/clientes.json').read_bytes();candidate=(s/m['candidate_file']).read_bytes()
  self.assertEqual(hashlib.sha256(raw).hexdigest(),m['source_sha256']);self.assertEqual(hashlib.sha256(candidate).hexdigest(),m['candidate_sha256']);self.assertEqual(set(changes(json.loads(raw),json.loads(candidate))),set(m['whitelist_paths']))
  for p in [s/'manifest.json',s/m['candidate_file']]:self.assertEqual(p.stat().st_mode&0o777,0o600)
  self.assertEqual(s.stat().st_mode&0o777,0o700)
if __name__=='__main__':unittest.main()
