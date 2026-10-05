import copy
import json
import sqlite3
import types
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock,patch
import os
import operaciones_registros_269 as O
import operaciones_anomalias_276 as A
from probar_operaciones_registros_269 import Registros

class Anomalias(unittest.TestCase):
    def setUp(self):
        Registros.setUp(self)
        self.raw['clientes']=[{'id':'own'},{'id':'foreign'}]
        self.raw['asignaciones']=[{'persona_id':'a','cliente_id':'own','silla':'account'}]
        self.S.ACT=types.SimpleNamespace(es_activo_id=lambda cid:cid in ('own','foreign'))
        self.doc={'generado':'2026-10-03 08:00','raras':[{'id':'entry_1','persona_id':'a','fecha':'2026-10-02','horas':9,'tipo':'largo','tarea':'TEXTO_PRIVADO_SINTETICO','motivo':'motivo','url':'https://example.invalid/private'}],
                  'raras_cliente':[{'id':'entry_1','persona_id':'a','cliente_id':'own','tarea_completa':'TEXTO_PRIVADO_SINTETICO'}]}
        self.nota=None
        self.S.puerta_modulo=Mock(return_value={'fichero':self.path.parent/'horas.json'})
        self.S.leer_json_bueno=Mock(side_effect=lambda p:(copy.deepcopy(self.doc),self.nota))
        self.S.modulo_recortado=Mock(side_effect=lambda *args:copy.deepcopy(self.doc))
    def con(self):return Registros.con(self)
    def b(self,decision='correcto',revision=0,**kw):
        origen=A.resolver(self.S,'mili','mili','entry_1',True)
        return {'anomalia_id':'entry_1','decision':decision,'revision':revision,'intencion_id':str(uuid.uuid4()),'huella_origen':origen['huella_origen'],**kw}
    def guardar(self,b,r='mili',v='mili'):
        with self.con() as con:return A.guardar(self.S,con,r,v,b)
    def listar(self,r='mili',v='mili'):
        with self.con() as con:return A.listar(self.S,con,r,v,'entry_1')
    def test_correcto_durable_recibo_sin_modificar_fuente(self):
        antes=copy.deepcopy(self.doc);r=self.guardar(self.b())['recibo']
        self.assertEqual(r['revision'],1);self.assertEqual(r['decision'],'correcto');self.assertFalse(r['entrada_modificada']);self.assertFalse(r['envio_realizado'])
        self.assertEqual(self.listar()['registro'],r);self.assertEqual(self.doc,antes)
        texto=json.dumps(r);self.assertNotIn('TEXTO_PRIVADO',texto);self.assertNotIn('example.invalid',texto);self.assertNotIn('own',texto)
    def test_error_y_rectificar_necesitan_prueba(self):
        with self.assertRaises(O.ErrorRegistro):self.guardar(self.b('error'))
        self.guardar(self.b())
        with self.assertRaises(O.ErrorRegistro):self.guardar(self.b('hablar',1))
        r=self.guardar(self.b('hablar',1,prueba='Se revisó la evidencia sintética'))['recibo'];self.assertEqual(r['revision'],2)
    def test_replay_mismo_uuid_body409_y_cas(self):
        b=self.b();r=self.guardar(b);self.assertEqual(self.guardar(b)['recibo'],r['recibo'])
        with self.assertRaises(O.ErrorRegistro) as e:self.guardar({**b,'prueba':'otro'} )
        self.assertEqual(e.exception.codigo,409)
        with self.assertRaises(O.ErrorRegistro):self.guardar(self.b())
        with self.con() as con:self.assertEqual(con.execute('SELECT COUNT(*) FROM operaciones_anomalias_276').fetchone()[0],1)
    def test_actor_lectura_propia_no_adquiere_validacion(self):
        self.assertFalse(self.listar('a','a')['puede_registrar'])
        with self.assertRaises(O.ErrorRegistro):self.guardar(self.b(),r='a',v='a')
        with self.assertRaises(O.ErrorRegistro):self.listar('b','b')
    def test_cid_derivado_foreign_baja_dupe_metadata(self):
        for cambio in ['foreign',None]:
            self.doc['raras_cliente'][0]['cliente_id']=cambio
            with self.assertRaises(O.ErrorRegistro):self.listar('a','a')
        self.doc['raras_cliente'][0]['cliente_id']='own';self.S.ACT.es_activo_id=lambda cid:False
        with self.assertRaises(O.ErrorRegistro):self.listar()
        self.S.ACT.es_activo_id=lambda cid:True;self.doc['raras_cliente']*=2
        with self.assertRaises(O.ErrorRegistro):self.listar()
    def test_cliente_ambiguo_persona_inactiva_id_dup_no_nombre(self):
        self.doc['raras']*=2
        with self.assertRaises(O.ErrorRegistro):self.listar()
        self.doc['raras']=self.doc['raras'][:1];self.raw['personas'][0]['estado']='baja'
        with self.assertRaises(O.ErrorRegistro):self.listar()
    def test_vinculos_contradictorios_no_escoger_el_permitido(self):
        self.doc['raras'][0]['cliente_id']='foreign'
        with self.assertRaises(O.ErrorRegistro) as e:self.listar('a','a')
        self.assertEqual(e.exception.codigo,403)
    def test_revocacion_al_cerrar_conexion_no_publica_dto(self):
        class H:
            def responder(self,c,d):return c,d
            def _api_get(self,*args):return 418,{}
            def api_post(self,*args):return 418,{}
        raw=self.raw
        class Con(sqlite3.Connection):
            def close(con):
                super().close();raw['personas'][2]['estado']='baja'
        self.S.conectar=lambda:sqlite3.connect(self.path,factory=Con)
        A.enganchar(H,self.S);p=raw['personas'][2]
        codigo,d=H()._api_get(A.RUTA,{'id':['entry_1']},p,p)
        self.assertEqual(codigo,403);self.assertNotIn('origen',d)
    def test_fuente_cambiada_y_sello_de_copia_no_rejuvenecer(self):
        b=self.b();self.guardar(b);self.doc['raras'][0]['horas']=10
        with self.assertRaises(O.ErrorRegistro) as e:self.guardar(b)
        self.assertEqual(e.exception.codigo,409)
        d=self.listar();self.assertTrue(d['anterior_incompatible']);self.assertIsNone(d['registro']);self.assertEqual(d['revision'],1);self.assertEqual(d['origen']['fecha_origen'],'2026-10-03 08:00')
        with self.assertRaises(O.ErrorRegistro):self.guardar(self.b(revision=1))
        self.guardar(self.b(revision=1,prueba='Entrada nueva revisada'))
    def test_fallback_rotura_no_autoridad_y_omision_scoped(self):
        self.nota={'dato_de':'ayer'}
        with self.assertRaises(O.ErrorRegistro) as e:self.listar()
        self.assertEqual(e.exception.codigo,503)
        self.nota=None;self.S.modulo_recortado=Mock(return_value={'raras':[]})
        with self.assertRaises(O.ErrorRegistro):self.listar()
    def test_modulo_revoque_antes_leer_y_dentro_transaccion(self):
        self.S.ve_alguno=lambda *args:False
        with self.assertRaises(O.ErrorRegistro):self.listar()
        self.S.leer_json_bueno.assert_not_called()
        self.S.ve_alguno=lambda *args:True;b=self.b();n=0
        def read(path):
            nonlocal n;n+=1
            if n==2:self.raw['personas'][2]['estado']='baja'
            return copy.deepcopy(self.doc),None
        self.S.leer_json_bueno=read
        with self.assertRaises(O.ErrorRegistro):self.guardar(b)
        with self.con() as con:self.assertFalse(con.execute("SELECT 1 FROM sqlite_master WHERE name='operaciones_anomalias_276'").fetchone())
    def test_concurrencia_cas_y_triggers(self):
        b=self.b()
        def op(_):
            try:return self.guardar({**b,'intencion_id':str(uuid.uuid4())})['resultado']
            except O.ErrorRegistro as e:return e.codigo
        with ThreadPoolExecutor(max_workers=2) as ex:res=list(ex.map(op,range(2)))
        self.assertCountEqual(res,['guardado',409])
        with self.con() as con:
            for sql in ['DELETE FROM operaciones_anomalias_276','UPDATE operaciones_anomalias_276 SET prueba="otra"']:
                with self.assertRaises(sqlite3.IntegrityError):con.execute(sql)
    def test_nunca_commit_conexion_ajena_y_piloto_viewas(self):
        b=self.b()
        with self.con() as con:
            con.execute('CREATE TABLE otra(x)');con.execute('INSERT INTO otra VALUES(1)')
            with self.assertRaises(O.ErrorRegistro):A.guardar(self.S,con,'mili','mili',b)
            self.assertTrue(con.in_transaction);con.rollback()
        with patch.dict(os.environ,{'RO_PILOTO_LECTURA':'si'}):
            with self.assertRaises(O.ErrorRegistro):self.guardar(b)
        with self.assertRaises(O.ErrorRegistro):self.guardar(b,'tomas','mili')
    def test_payload_whitelist_hash_prueba_uuid_revision(self):
        b=self.b()
        for payload in [{**b,'cliente_id':'own'},{**b,'actor':'tomas'},{**b,'revision':True},{**b,'decision':'despedir'},{**b,'prueba':'x'*501},{**b,'intencion_id':'bad'},{k:v for k,v in b.items() if k!='revision'}]:
            with self.assertRaises(O.ErrorRegistro):self.guardar(payload)
    def test_hook_noio_query_exacta_pg_y_revocacion_antes_respuesta(self):
        class H:
            def responder(self,c,d):return c,d
            def _api_get(self,*args):return 418,{}
            def api_post(self,*args):return 418,{}
        A.enganchar(H,self.S);h=H();self.assertEqual(self.opens,0)
        p=self.raw['personas'][2]
        for q in [{},{'id':['entry_1','entry_1']},{'id':['entry_1'],'persona_id':['a']}]:self.assertEqual(h._api_get(A.RUTA,q,p,p)[0],400)
        with patch.dict(os.environ,{'DATABASE_URL':'fixture'}):self.assertEqual(h._api_get(A.RUTA,{'id':['entry_1']},p,p)[0],503)
        self.assertEqual(self.opens,0)

if __name__=='__main__':unittest.main()
