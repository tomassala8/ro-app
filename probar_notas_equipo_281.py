import os
import sqlite3
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from probar_operaciones_registros_269 import Registros
import operaciones_registros_269 as O
import operaciones_notas_equipo_281 as N

class Notas(unittest.TestCase):
    def setUp(self):Registros.setUp(self)
    def con(self):return Registros.con(self)
    def b(self,**kw):return {'persona_id':'a','periodo':'2026-10','nota':7,'prueba':'Hecho sintético observable','accion_propuesta':'formar','revision':0,'intencion_id':str(uuid.uuid4()),**kw}
    def guardar(self,b,r='mili',v='mili'):
        with self.con() as c:return N.guardar(self.S,c,r,v,b)
    def leer(self,p='a',r='mili',v='mili'):
        with self.con() as c:return N.listar(self.S,c,r,v,p)
    def test_durable_autor_periodo_no_kpi_no_decision_laboral(self):
        r=self.guardar(self.b())['recibo'];self.assertEqual(r,self.leer()['registro']);self.assertEqual(r['autor'],'mili');self.assertEqual(r['periodo'],'2026-10')
        for k in ('puntuacion_automatica','decision_laboral','envio_realizado'):self.assertIs(r[k],False)
        self.assertNotIn('horas',r);self.assertNotIn('nombre',r)
    def test_uuid_replay_body_conflict_cas_y_append_only(self):
        b=self.b();r=self.guardar(b);self.assertEqual(r['recibo'],self.guardar(b)['recibo'])
        for x in [{**b,'nota':8},self.b()]:
            with self.assertRaises(O.ErrorRegistro) as e:self.guardar(x)
            self.assertEqual(e.exception.codigo,409)
        self.guardar(self.b(revision=1,nota=None,accion_propuesta=None,prueba='Se retira la valoración previa'))
        with self.con() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM operaciones_notas_equipo_281').fetchone()[0],2)
            for sql in ['DELETE FROM operaciones_notas_equipo_281','UPDATE operaciones_notas_equipo_281 SET nota=10']:
                with self.assertRaises(sqlite3.IntegrityError):c.execute(sql)
    def test_grant_exacto_propio_jefe_no_otra_persona(self):
        self.guardar(self.b(),r='a',v='a');self.assertTrue(self.leer(r='a',v='a')['puede_registrar'])
        with self.assertRaises(O.ErrorRegistro):self.leer(r='b',v='b')
        with self.assertRaises(O.ErrorRegistro):self.guardar(self.b(persona_id='b'),r='a',v='a')
        self.raw['personas'][1]['jefe']='a';self.assertTrue(self.leer('b','a','a')['puede_registrar'])
        self.raw['personas'][1]['jefe']=None
        with self.assertRaises(O.ErrorRegistro):self.leer('b','a','a')
    def test_piloto_vercomo_y_destino_duplicado_inactivo(self):
        b=self.b()
        with patch.dict(os.environ,{'RO_PILOTO_LECTURA':'si'}):
            with self.assertRaises(O.ErrorRegistro):self.guardar(b)
            self.assertFalse(self.leer()['puede_registrar'])
        self.assertFalse(self.leer(r='tomas',v='mili')['puede_registrar'])
        with self.assertRaises(O.ErrorRegistro):self.guardar(b,'tomas','mili')
        for cambio in ('baja','duplicado'):
            if cambio=='baja':self.raw['personas'][0]['estado']='baja'
            else:self.raw['personas'][0]['estado']='activo';self.raw['personas'].append(dict(self.raw['personas'][0]))
            with self.assertRaises(O.ErrorRegistro):self.leer()
    def test_tipos_escala_prueba_payload_periodo(self):
        b=self.b()
        for cambios in [{'nota':True},{'nota':0},{'nota':11},{'nota':7.5},{'prueba':''},{'prueba':'x'*301},{'accion_propuesta':'despedir'},{'autor':'tomas'},{'revision':True},{'periodo':'2026-13'},{'periodo':'2026-09'},{'intencion_id':'bad'}]:
            with self.assertRaises(O.ErrorRegistro):self.guardar({**b,**cambios})
    def test_replay_cambio_mes_pero_nuevo_pasado_no(self):
        b=self.b();r=self.guardar(b);self.S.P.hoy_iso=lambda:'2026-11-01'
        self.assertEqual(self.guardar(b)['recibo'],r['recibo'])
        with self.assertRaises(O.ErrorRegistro):self.guardar(self.b(revision=1))
        self.guardar(self.b(revision=1,periodo='2026-11'))
    def test_concurrencia_no_perdida_actualizacion(self):
        b=self.b()
        def op(_):
            try:return self.guardar({**b,'intencion_id':str(uuid.uuid4())})['resultado']
            except O.ErrorRegistro as e:return e.codigo
        with ThreadPoolExecutor(max_workers=2) as ex:self.assertCountEqual(list(ex.map(op,range(2))),['guardado',409])
    def test_transaccion_prestada_no_commit(self):
        with self.con() as c:
            c.execute('CREATE TABLE otra(x)');c.execute('INSERT INTO otra VALUES(1)')
            with self.assertRaises(O.ErrorRegistro):N.guardar(self.S,c,'mili','mili',self.b())
            self.assertTrue(c.in_transaction);c.rollback();self.assertEqual(c.execute('SELECT COUNT(*) FROM otra').fetchone()[0],0)
    def test_revocacion_antes_commit_rollback(self):
        orig=N.autorizar;n=0
        def puerta(*args,**kw):
            nonlocal n;n+=1
            if n==3:self.raw['personas'][2]['estado']='baja'
            return orig(*args,**kw)
        with patch.object(N,'autorizar',side_effect=puerta):
            with self.assertRaises(O.ErrorRegistro):self.guardar(self.b())
        with self.con() as c:self.assertIsNone(c.execute("SELECT 1 FROM sqlite_master WHERE name='operaciones_notas_equipo_281'").fetchone())
    def test_dto_corrupto_no_publicar(self):
        self.guardar(self.b())
        with self.con() as c:
            row=dict(c.execute('SELECT * FROM operaciones_notas_equipo_281').fetchone());row['prueba']='texto ajeno alterado'
            with self.assertRaises(O.ErrorRegistro):N.decodificar(row)
    def test_hook_get_no_schema_y_revocacion_final(self):
        class H:
            def responder(self,c,d):return c,d
            def _api_get(self,*args):return 418,{}
            def api_post(self,*args):return 418,{}
        N.enganchar(H,self.S);self.assertEqual(self.opens,0);h=H();p=self.raw['personas'][2]
        code,d=h._api_get(N.RUTA,{'persona_id':['a']},p,p);self.assertEqual(code,200);self.assertIsNone(d['registro'])
        with self.con() as c:self.assertFalse(c.execute("SELECT 1 FROM sqlite_master WHERE name='operaciones_notas_equipo_281'").fetchone())
        for q in [{},{'persona_id':['a','b']},{'persona_id':['a'],'autor':['tomas']}]:self.assertEqual(h._api_get(N.RUTA,q,p,p)[0],400)
        with patch.dict(os.environ,{'DATABASE_URL':'fixture'}):self.assertEqual(h._api_get(N.RUTA,{'persona_id':['a']},p,p)[0],503)
        raw=self.raw
        class Con(sqlite3.Connection):
            def close(c):super().close();raw['personas'][2]['estado']='baja'
        self.S.conectar=lambda:sqlite3.connect(self.path,factory=Con)
        code,d=h._api_get(N.RUTA,{'persona_id':['a']},p,p);self.assertEqual(code,403);self.assertNotIn('registro',d)

if __name__=='__main__':unittest.main()
