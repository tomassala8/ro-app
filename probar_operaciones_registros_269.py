import copy
import json
import os
import sqlite3
import tempfile
import types
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
import permisos as P
import operaciones_registros_269 as O

def persona(pid,rol='account'):return {'id':pid,'estado':'activo','puestos':[rol]}
def cuerpo(ritual='manana',revision=0,**kw):return {'tipo':'ritual','ritual':ritual,'periodo':'2026-10' if ritual=='mes' else '2026-09-28' if ritual in ('lunes','viernes') else '2026-10-03','hecho':True,'revision':revision,'intencion_id':str(uuid.uuid4()),**kw}

class Registros(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'fixture.db';self.opens=0
        self.raw={'personas':[persona('a'),persona('b'),persona('mili','operaciones'),persona('tomas','direccion')],'clientes':[],'asignaciones':[]}
        self.S=types.SimpleNamespace(E=types.SimpleNamespace(crudo=self.raw,nucleo_bloqueado=False),
            P=types.SimpleNamespace(ver=P.ver,contexto=P.contexto,hoy_iso=lambda:'2026-10-03'),ve_alguno=lambda p,mods:True,conectar=self.con)
        self.env=patch.dict(os.environ,{'RO_PILOTO_LECTURA':'no','DATABASE_URL':'','PGDATABASE_URL':''});self.env.start();self.addCleanup(self.env.stop)
    def con(self):
        self.opens+=1;c=sqlite3.connect(self.path,timeout=10);c.row_factory=sqlite3.Row;return c
    def guardar(self,b,r='a',v='a'):
        with self.con() as c:return O.guardar(self.S,c,r,v,b)
    def test_cinco_rituales_durables_autor_servidor_y_reinicio(self):
        for ritual in O.RITUALES:
            d=self.guardar(cuerpo(ritual));self.assertEqual(d['recibo']['autor'],'a');self.assertFalse(d['recibo']['envio_realizado'])
        with self.con() as c:d=O.listar(self.S,c,'a','a')
        self.assertEqual(len(d['registros']),5);self.assertEqual(set(x['ritual'] for x in d['registros']),set(O.RITUALES))
        with self.con() as c:self.assertEqual(O.listar(self.S,c,'b','b')['registros'],[])
    def test_replay_y_conflicto_mismo_uuid(self):
        b=cuerpo();uno=self.guardar(b);dos=self.guardar(b)
        self.assertEqual(uno['recibo'],dos['recibo']);self.assertEqual(dos['resultado'],'duplicado')
        with self.assertRaises(O.ErrorRegistro) as e:self.guardar({**b,'nota':'otro'} )
        self.assertEqual(e.exception.codigo,409)
        with self.con() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM operaciones_registros_269').fetchone()[0],1)
    def test_cas_y_append_only(self):
        self.guardar(cuerpo())
        with self.assertRaises(O.ErrorRegistro) as e:self.guardar(cuerpo())
        self.assertEqual(e.exception.codigo,409)
        d=self.guardar(cuerpo(revision=1,hecho=False));self.assertEqual(d['recibo']['revision'],2);self.assertFalse(d['recibo']['hecho'])
        with self.con() as c:
            for sql in ['DELETE FROM operaciones_registros_269','UPDATE operaciones_registros_269 SET autor="b"']:
                with self.assertRaises(sqlite3.IntegrityError):c.execute(sql)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM operaciones_registros_269').fetchone()[0],2)
    def test_recibo_reintentado_tras_cambio_de_dia_no_duplica(self):
        b=cuerpo();uno=self.guardar(b)
        aviso={'tipo':'avisado','persona_id':'a','revision':0,'intencion_id':str(uuid.uuid4())}
        v=self.guardar(aviso,'mili','mili')
        self.S.P.hoy_iso=lambda:'2026-10-04'
        self.assertEqual(self.guardar(b)['recibo'],uno['recibo'])
        self.assertEqual(self.guardar(aviso,'mili','mili')['recibo'],v['recibo'])
        with self.assertRaises(O.ErrorRegistro):self.guardar(cuerpo())
    def test_no_confirmar_transaccion_ajena(self):
        with self.con() as c:
            c.execute('CREATE TABLE otra(x)');c.execute('INSERT INTO otra VALUES(1)')
            with self.assertRaises(O.ErrorRegistro):O.guardar(self.S,c,'a','a',cuerpo())
            self.assertTrue(c.in_transaction);c.rollback();self.assertEqual(c.execute('SELECT COUNT(*) FROM otra').fetchone()[0],0)
    def test_periodo_tipo_payload_y_autor_inyectado(self):
        for b in [cuerpo(periodo='2026-10-02'),cuerpo(ritual='otro'),cuerpo(hecho=1),cuerpo(revision=True),cuerpo(autor='b'),cuerpo(intencion_id='bad'),cuerpo(nota='x'*301)]:
            with self.assertRaises(O.ErrorRegistro):self.guardar(b)
    def test_identidad_revocada_duplicada_modulo_vista_piloto(self):
        with self.assertRaises(O.ErrorRegistro):self.guardar(cuerpo(),v='b')
        for filas in [[persona('a'),persona('a')],[{**persona('a'),'activo':False}],[{**persona('a'),'estado':'baja'}],[]]:
            self.S.E.crudo={**self.raw,'personas':filas}
            with self.assertRaises(O.ErrorRegistro):self.guardar(cuerpo())
        self.S.E.crudo=self.raw;self.S.ve_alguno=lambda *a:False
        with self.assertRaises(O.ErrorRegistro):self.guardar(cuerpo())
        self.S.ve_alguno=lambda *a:True
        with patch.dict(os.environ,{'RO_PILOTO_LECTURA':'si'}):
            with self.assertRaises(O.ErrorRegistro):self.guardar(cuerpo())
    def test_avisado_ops_propio_sin_envio_y_destino_revocado(self):
        b={'tipo':'avisado','persona_id':'a','revision':0,'intencion_id':str(uuid.uuid4())}
        with self.assertRaises(O.ErrorRegistro):self.guardar(b)
        d=self.guardar(b,'mili','mili');self.assertFalse(d['recibo']['envio_realizado']);self.assertEqual(d['recibo']['persona_id'],'a')
        self.S.E.crudo['personas']=[p for p in self.raw['personas'] if p['id']!='a']
        with self.con() as c:self.assertEqual(O.listar(self.S,c,'mili','mili')['registros'],[])
    def test_revocacion_en_transaccion_rollback(self):
        base=self.S.ve_alguno;calls=0
        def gate(*args):
            nonlocal calls;calls+=1
            return calls<3
        self.S.ve_alguno=gate
        with self.assertRaises(O.ErrorRegistro):self.guardar(cuerpo())
        self.S.ve_alguno=base
        with self.con() as c:self.assertFalse(c.execute("SELECT 1 FROM sqlite_master WHERE name='operaciones_registros_269'").fetchone())
    def test_concurrencia_una_revision_mismo_cas(self):
        def op(b):
            try:return self.guardar(b)['resultado']
            except O.ErrorRegistro as e:return e.codigo
        with ThreadPoolExecutor(max_workers=2) as ex:r=list(ex.map(op,[cuerpo(),cuerpo()]))
        self.assertCountEqual(r,['guardado',409])
    def test_http_hook_no_io_import_query_pg_y_lectura_vista(self):
        class H:
            def responder(self,c,d):return c,d
            def _api_get(self,*a):return 418,{}
            def api_post(self,*a):return 418,{}
        O.enganchar(H,self.S);h=H();self.assertEqual(self.opens,0)
        for q in [{'persona_id':['b']},{'extra':['x']}]:self.assertEqual(h._api_get(O.RUTA,q,persona('a'),persona('a'))[0],400)
        self.assertEqual(self.opens,0)
        with patch.dict(os.environ,{'DATABASE_URL':'fixture'}):self.assertEqual(h._api_get(O.RUTA,{},persona('a'),persona('a'))[0],503)
        self.assertEqual(self.opens,0)
        code,d=h._api_get(O.RUTA,{},persona('a'),persona('a'));self.assertEqual(code,200);self.assertEqual(d['registros'],[])
        self.assertEqual(h._api_get(O.RUTA,{},persona('a'),persona('b'))[0],403)
        self.guardar(cuerpo())
        code,d=h._api_get(O.RUTA,{},persona('tomas','direccion'),persona('a'));self.assertEqual(code,200);self.assertFalse(d['puede_registrar'])
    def test_corrupto_no_serializado(self):
        self.guardar(cuerpo())
        with self.con() as c:
            c.execute('DROP TRIGGER operaciones_269_sin_update');c.execute("UPDATE operaciones_registros_269 SET contenido=?",(json.dumps({'tipo':'ritual','secreto':'fixture'}),));c.commit()
            with self.assertRaises(O.ErrorRegistro):O.listar(self.S,c,'a','a')

if __name__=='__main__':unittest.main()
