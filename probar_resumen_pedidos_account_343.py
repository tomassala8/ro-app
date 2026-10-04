import unittest,tempfile,sqlite3,contextlib,copy,uuid,os
from types import SimpleNamespace as NS
from datetime import datetime,timezone
from unittest.mock import patch
import operaciones_pedidos_account as M
CUT=datetime.fromisoformat('2026-10-03T18:00:00+00:00')
class Test343(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=self.tmp.name+'/test.sqlite';self.con=sqlite3.connect(self.path);self.con.row_factory=sqlite3.Row;M.preparar(self.con);self.con.commit()
  self.raw={'personas':[{'id':'mili','estado':'activo','puestos':['operaciones']},{'id':'a','estado':'activo','puestos':['account']},{'id':'b','estado':'activo','puestos':['account']},{'id':'otro','estado':'activo','puestos':['operaciones']}],'clientes':[{'id':'c'},{'id':'foreign'}],'asignaciones':[{'cliente_id':'c','persona_id':'a','silla':'account','principal':True,'confianza':'confirmada','desde':'2026-01-01'}]}
  self.allowed={'c'};self.owner='a'
  def cp(p,raw):return {'cartera_por_silla':{'account':{'c'} if p['id']==self.owner else set()}}
  def ver(p,q,cp):return {'ok':q.get('tipo')=='ver_como' or q.get('cliente_id') in self.allowed}
  self.P=NS(hoy_iso=lambda:'2026-10-03',contexto=cp,ver=ver,mirando_como=lambda *a:contextlib.nullcontext())
  self.S=NS(DB=self.path,E=NS(nucleo_bloqueado=False,crudo=self.raw),P=self.P,ACT=NS(es_activo_id=lambda cid:cid in self.allowed),ve_alguno=lambda p,m:True,modulo_recortado=lambda *a:{'generado':'2026-10-03','fuentes':{},'correos':[{'id':'t','cliente_id':'c'}],'llamadas':[]})
 def tearDown(self):self.con.close();self.tmp.cleanup()
 def event(self,rev=1,state='pedido',actor='mili',receiver='a',fecha='2026-10-01T12:00:00+00:00',ref='t',cid='c'):
  b={'cliente_id':cid,'tipo':'responder_correo','referencia_id':ref,'estado':state,'revision':rev-1,'revision_fuente':'f'*64,'intencion_id':str(uuid.uuid4())}
  self.con.execute('INSERT INTO '+M.TABLA+' VALUES (?,?,?,?,?,?,?,?,?,?,?)',(b['intencion_id'],cid,b['tipo'],ref,rev,actor,receiver,state,fecha,b['revision_fuente'],M.fingerprint(b,actor)));self.con.commit();return b
 def summary(self,rid='mili',vid='mili',con=True):return M.leer_resumen(self.S,self.con if con else None,rid,vid,CUT)
 def row(self,d,pid='a'):return next(r for r in d['filas'] if r['receptor_id']==pid)
 def test_empty_table_is_zero_only_authorized_receivers(self):
  d=self.summary();self.assertEqual(d['estado'],'medido');self.assertEqual(self.row(d)['pedidos_semana'],0);self.assertEqual(d['receptor_ids_autorizados'],['a']);self.assertEqual(d['cliente_ids_autorizados'],['c']);self.assertTrue(d['cobertura']['completa_ledger']);self.assertFalse(d['envio_realizado'])
 def test_absent_db_and_table_are_unknown(self):
  self.assertEqual(self.summary(con=False)['estado'],'sin_dato');self.assertIsNone(self.summary(con=False)['pendientes']);self.con.execute('DROP TRIGGER pedidos294_no_UPDATE');self.con.execute('DROP TRIGGER pedidos294_no_DELETE');self.con.execute('DROP TABLE '+M.TABLA);self.con.commit();self.assertEqual(self.summary()['estado'],'sin_dato')
 def test_event_week_and_current_pending(self):
  self.event();d=self.summary();self.assertEqual(self.row(d)['pedidos_semana'],1);self.assertEqual(self.row(d)['pendientes'],1);self.assertTrue(d['declarado']);self.assertFalse(d['ejecucion_verificada'])
 def test_resolution_author_does_not_rewrite_original_event(self):
  self.event();self.event(2,'resuelto_declarado','otro',fecha='2026-10-02T12:00:00Z');d=self.summary();self.assertEqual(self.row(d)['pedidos_semana'],1);self.assertEqual(self.row(d)['pendientes'],0)
 def test_reopens_are_separate_uuid_events_not_other_states(self):
  self.event();self.event(2,'anulado',fecha='2026-10-02T12:00:00Z');self.event(3,'pedido',fecha='2026-10-03T12:00:00Z');d=self.summary();self.assertEqual(self.row(d)['pedidos_semana'],2);self.assertEqual(self.row(d)['pendientes'],1)
 def test_madrid_monday_boundary(self):
  self.event(fecha='2026-09-27T21:59:59Z',ref='prev');self.event(fecha='2026-09-27T22:00:00Z',ref='monday');d=self.summary();self.assertEqual(self.row(d)['pedidos_semana'],1);self.assertEqual(self.row(d)['pendientes'],2);self.assertEqual(d['desde'],'2026-09-28');self.assertEqual(d['zona'],'Europe/Madrid')
 def test_other_author_not_mili(self):
  self.event(actor='otro');self.assertEqual(self.row(self.summary())['pedidos_semana'],0);self.assertEqual(self.row(self.summary())['pendientes'],0)
 def test_latest_pending_other_author_not_counted_as_mili(self):
  self.event();self.event(2,'anulado',fecha='2026-10-02T12:00:00Z');self.event(3,'pedido','otro',fecha='2026-10-03T12:00:00Z');d=self.summary();self.assertEqual(self.row(d)['pedidos_semana'],1);self.assertEqual(self.row(d)['pendientes'],0)
 def test_historical_receiver_not_current_owner(self):
  self.event();self.owner='b';self.raw['asignaciones'][0]['persona_id']='b';d=self.summary();self.assertEqual(self.row(d,'a')['pendientes'],1);self.assertFalse(self.row(d,'a')['asignacion_actual_confirmada']);self.assertEqual(self.row(d,'b')['pendientes'],0)
 def test_account_reassignment_chain_kept_internal_no_foreign_recipient(self):
  self.event();self.event(2,'anulado',fecha='2026-10-02T12:00:00Z');self.event(3,'pedido',receiver='b',fecha='2026-10-03T12:00:00Z');self.owner='b';self.raw['asignaciones'][0]['persona_id']='b';d=self.summary('b','b');self.assertEqual(d['receptor_ids_autorizados'],['b']);self.assertEqual(self.row(d,'b')['pedidos_semana'],1);self.assertEqual(self.row(d,'b')['pendientes'],1);self.assertNotIn('a',[r['receptor_id'] for r in d['filas']])
 def test_foreign_client_excluded_before_cap(self):
  self.event(cid='foreign',ref='f');self.event();
  with patch.object(M,'MAX_HISTORIA_RESUMEN',1):self.assertEqual(self.summary()['estado'],'medido')
 def test_truncation_unknown_not_lower_false_total(self):
  self.event(ref='t');self.event(ref='u');
  with patch.object(M,'MAX_HISTORIA_RESUMEN',1):
   d=self.summary();self.assertEqual(d['estado'],'sin_dato');self.assertTrue(d['cobertura']['truncado']);self.assertIsNone(d['pedidos_semana']);self.assertEqual(d['filas'],[])
 def test_dates_invalid_naive_future_fail_closed(self):
  for i,stamp in enumerate(['notdate','2026-10-01T12:00:00','2026-10-03T18:00:01Z','2026-02-30T12:00:00Z']):
   with self.subTest(stamp=stamp):
    self.event(fecha=stamp,ref=str(i))
    with self.assertRaises(M.ErrorPedido) as e:self.summary()
    self.assertEqual(e.exception.codigo,503)
 def test_corrupt_sequence_never_certifies(self):
  self.event(rev=2)
  with self.assertRaises(M.ErrorPedido):self.summary()
 def test_mili_missing_duplicate_inactive_wrong_role_unknown(self):
  for changed in ['missing','duplicate','inactive','role']:
   with self.subTest(changed=changed):
    prior=copy.deepcopy(self.raw['personas']);mili=self.raw['personas'][0]
    if changed=='missing':self.raw['personas']=self.raw['personas'][1:]
    elif changed=='duplicate':self.raw['personas'].append(copy.deepcopy(mili))
    elif changed=='inactive':mili['estado']='baja'
    else:mili['puestos']=['seo']
    # Operaciones de otro actor mantienen su propia autoridad; la cifra Mili falla cerrada.
    d=self.summary('otro','otro');self.assertEqual(d['estado'],'sin_dato');self.assertIsNone(d['autor_id']);self.assertIsNone(d['pedidos_semana']);self.raw['personas']=prior
 def test_receptor_inactive_is_not_unknown_zero(self):
  self.event();self.raw['personas'][1]['estado']='baja'
  with self.assertRaises(M.ErrorPedido):self.summary()
 def test_revocation_during_dto_read_denies(self):
  self.event();real=M.dto
  def revoke(r):d=real(r);self.allowed.clear();return d
  with patch.object(M,'dto',revoke):
   with self.assertRaises(M.ErrorPedido):self.summary()
 def test_pilot_and_viewas_reads_scoped_writes_remain_denied(self):
  self.event()
  with patch.object(M.piloto_lectura,'activo',lambda:True):self.assertEqual(self.summary('mili','a')['pendientes'],1)
  self.assertEqual(self.summary('mili','a')['receptor_ids_autorizados'],['a'])
 def test_readonly_restart_no_schema_write(self):
  self.event();before=self.con.total_changes
  with sqlite3.connect('file:'+self.path+'?mode=ro',uri=True) as ro:
   ro.row_factory=sqlite3.Row;self.assertEqual(M.leer_resumen(self.S,ro,'mili','mili',CUT)['pedidos_semana'],1)
  self.assertEqual(self.con.total_changes,before)
 def test_real_guardar_retry_single_event(self):
  from datetime import datetime as DT
  class Clock(DT):
   @classmethod
   def now(cls,tz=None):return CUT
  with patch.object(M,'datetime',Clock),patch.object(M.piloto_lectura,'activo',lambda:False):
   _,tok=M.capacidad(self.S,'mili','mili','c','responder_correo','t');b={'intencion_id':str(uuid.uuid4()),'cliente_id':'c','tipo':'responder_correo','referencia_id':'t','estado':'pedido','revision':0,'revision_fuente':tok};M.guardar(self.S,self.con,'mili','mili',b);self.assertEqual(M.guardar(self.S,self.con,'mili','mili',b)['resultado'],'duplicado')
  self.assertEqual(self.summary()['pedidos_semana'],1)
 def test_scope_fingerprint_includes_author_and_receiver_bandeja_grants(self):
  before=M._ambito_resumen(self.S,'otro','otro')[2]
  for pid in ['mili','a']:
   self.S.ve_alguno=lambda p,m,denied=pid:p['id']!=denied
   self.assertNotEqual(M._ambito_resumen(self.S,'otro','otro')[2],before)
 def test_late_author_or_receiver_module_revocation_cannot_emit(self):
  self.event()
  for pid in ['mili','a']:
   self.S.ve_alguno=lambda p,m:True
   real=M._ambito_resumen;calls=0
   def check(S,r,v):
    nonlocal calls
    calls+=1
    if calls==2:self.S.ve_alguno=lambda p,m:p['id']!=pid
    return real(S,r,v)
   with patch.object(M,'_ambito_resumen',check):
    with self.assertRaises(M.ErrorPedido) as e:self.summary('otro','otro')
    self.assertEqual(e.exception.codigo,409)
 def test_actor_role_revoked_denied_no_summary(self):
  self.raw['personas'][3]['puestos']=['seo']
  with self.assertRaises(M.ErrorPedido):self.summary('otro','otro')
 def test_duplicate_client_is_excluded_not_selected(self):
  self.event();self.raw['clientes'].append({'id':'c'});d=self.summary();self.assertEqual(d['cliente_ids_autorizados'],[]);self.assertEqual(d['filas'],[])
 def test_cut_aware_and_calendar_match(self):
  for stamp in [datetime(2026,10,3),datetime.fromisoformat('2026-10-04T12:00:00+00:00')]:
   with self.assertRaises(M.ErrorPedido):M.leer_resumen(self.S,self.con,'mili','mili',stamp)
 def test_hook_get_query_post_and_missing_db(self):
  class H:
   def _api_get(self,*a):return (404,{})
   def api_post(self,*a):return (404,{})
   def responder(self,code,d):return code,d
  M.enganchar(H,self.S);h=H();p={'id':'mili'}
  original=M.leer_resumen
  with patch.object(M,'leer_resumen',lambda S,c,r,v:original(S,c,r,v,CUT)):
   self.assertEqual(h._api_get(M.RUTA_RESUMEN,{},p,p)[0],200)
   self.assertEqual(h._api_get(M.RUTA_RESUMEN,{'autor':['otro']},p,p)[0],400)
   self.assertEqual(h.api_post(M.RUTA_RESUMEN,p,p,{})[0],405)
   self.S.DB=self.tmp.name+'/absent.sqlite';code,d=h._api_get(M.RUTA_RESUMEN,{},p,p);self.assertEqual(code,200);self.assertEqual(d['estado'],'sin_dato');self.assertFalse(os.path.exists(self.S.DB))
if __name__=='__main__':unittest.main()
