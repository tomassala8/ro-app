"""Revisión independiente: SQLite temporal; ninguna fuente o servidor real."""
import copy,json,sqlite3,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
import decisiones_durables_382 as M
import probar_decisiones_durables_382 as B

class Revision387B(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.path=Path(self.t.name)/'fixture.sqlite'
  self.con=sqlite3.connect(self.path);self.con.row_factory=sqlite3.Row;self.con.executescript(B.DDL)
  self.S=B.fake();self.p=patch.object(M.piloto_lectura,'activo',return_value=False);self.p.start()
 def tearDown(self):self.p.stop();self.con.close();self.t.cleanup()
 def nueva(self):return {'operacion':'nueva','intencion_id':B.UUID,'tipo':'para_tomas','cliente_id':'ok','titulo':'Decisión operativa','problema':'Revisar el alcance','recomendacion':'Confirmar planificación'}
 def insertar(self,creada='2026-10-04 08:00:00',respondida=None,respuesta=None):
  self.con.execute('INSERT INTO decisiones(quien,tipo,titulo,problema,recomendacion,cliente_id,creada,respondida,respuesta) VALUES(?,?,?,?,?,?,?,?,?)',('tomas','para_tomas','Operativa','Revisar','Decidir','ok',creada,respondida,respuesta));self.con.commit()
 def filas(self):return M.listar(self.S,self.con,'tomas','tomas')['decisiones']
 def test_fecha_legacy_no_es_canal_de_secretos(self):
  self.insertar('password: fixture-secret','correo fixture@example.invalid','{}')
  d=self.filas()[0]
  self.assertIsNone(d['creada']);self.assertIsNone(d['respondida']);self.assertTrue(d['respuesta_registrada']);self.assertFalse(d['puede_responder'])
  self.assertNotIn('fixture-secret',json.dumps(d));self.assertNotIn('fixture@example.invalid',json.dumps(d))
 def test_fechas_invalidas_no_se_presentan_como_registro_fechado(self):
  for value in ['2026-02-30 01:00:00','2026-10-04 25:00:00','2026-10-04garbage',123,True]:
   with self.subTest(value=value):
    r={'respondida':None,'respuesta':None,'creada':value}
    self.con.execute('DELETE FROM decisiones');self.con.commit();self.insertar(value)
    self.assertIsNone(self.filas()[0]['creada'])
 def test_JSON_ambiguo_no_acredita_aprobacion(self):
  self.insertar(respondida='2026-10-04 09:00:00',respuesta='{"decision":"Rechazar","decision":"Aprobar la recomendación","motivo":null}')
  self.assertIsNone(self.filas()[0]['respuesta'])
 def test_JSON_no_finito_y_duplicado_anidado_se_rechaza(self):
  for raw in ['{"decision":"Aprobar la recomendación","motivo":null,"extra":NaN}','{"decision":"Aprobar la recomendación","motivo":null,"extra":{"x":1,"x":2}}']:
   with self.subTest(raw=raw):
    self.con.execute('DELETE FROM decisiones');self.con.commit();self.insertar(respondida='2026-10-04 09:00:00',respuesta=raw)
    self.assertIsNone(self.filas()[0]['respuesta'])
 def test_revocacion_catalogo_real_y_vista_tras_lectura(self):
  self.insertar();self.con.execute("UPDATE decisiones SET tipo='para_coti'");self.con.commit();old=M.dto
  for modo in ['modulo','ACT','vista','duplicate']:
   self.S=B.fake()
   def cambiar(*a):
    out=old(*a)
    if modo=='modulo':self.S.ve_alguno=lambda *x:False
    elif modo=='ACT':self.S.ACT.es_activo_id=lambda *x:False
    elif modo=='vista':self.S.P.ver=lambda p,x,c:{'ok':p['id']!='coti'}
    else:self.S.E.crudo['personas'].append(copy.deepcopy(self.S.E.crudo['personas'][0]))
    return out
   with self.subTest(modo=modo),patch.object(M,'dto',side_effect=cambiar):
    with self.assertRaises(M.ErrorDecision):M.listar(self.S,self.con,'tomas','coti')
 def test_concurrencia_replay_mismo_UUID_una_fila(self):
  barrera=threading.Barrier(2);resultados=[];errores=[]
  def trabajo():
   try:
    with sqlite3.connect(self.path,timeout=3) as c:
     c.row_factory=sqlite3.Row;barrera.wait();resultados.append(M.guardar(B.fake(),c,'tomas','tomas',self.nueva()))
   except Exception as e:errores.append(type(e).__name__)
  ts=[threading.Thread(target=trabajo) for _ in range(2)]
  for t in ts:t.start()
  for t in ts:t.join(5);self.assertFalse(t.is_alive())
  self.assertEqual(errores,[]);self.assertEqual(len(resultados),2)
  self.assertEqual(resultados[0]['recibo'],resultados[1]['recibo']);self.assertEqual({x['resultado'] for x in resultados},{'guardado','duplicado'})
  self.assertEqual(self.con.execute('SELECT COUNT(*) FROM decisiones').fetchone()[0],1)
 def test_concurrencia_respuestas_distintas_un_CAS(self):
  receipt=M.guardar(self.S,self.con,'tomas','tomas',self.nueva())['recibo'];barrera=threading.Barrier(2);resultados=[]
  def trabajo(key):
   b={'operacion':'responder','intencion_id':key,'id':receipt['id'],'revision':receipt['revision'],'decision':'Aprobar la recomendación','motivo':None,'delegada_en':None}
   with sqlite3.connect(self.path,timeout=3) as c:
    c.row_factory=sqlite3.Row;barrera.wait()
    try:resultados.append(M.guardar(B.fake(),c,'tomas','tomas',b)['resultado'])
    except M.ErrorDecision as e:resultados.append(e.codigo)
  ts=[threading.Thread(target=trabajo,args=(key,)) for key in [B.UUID2,'00000000-0000-4000-8000-000000000003']]
  for t in ts:t.start()
  for t in ts:t.join(5);self.assertFalse(t.is_alive())
  self.assertCountEqual(resultados,['guardado',409]);self.assertEqual(self.con.execute('SELECT COUNT(*) FROM decisiones_intenciones_382').fetchone()[0],2)
 def test_transaccion_ajena_no_confirmada(self):
  self.con.execute('INSERT INTO decisiones(quien,tipo) VALUES(?,?)',('tomas','para_tomas'))
  with self.assertRaises(M.ErrorDecision) as e:M.guardar(self.S,self.con,'tomas','tomas',self.nueva())
  self.assertEqual(e.exception.codigo,503);self.assertTrue(self.con.in_transaction)
  self.con.rollback();self.assertEqual(self.con.execute('SELECT COUNT(*) FROM decisiones').fetchone()[0],0)

if __name__=='__main__':unittest.main()
