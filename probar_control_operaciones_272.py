import json
import sqlite3
import types
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock
import operaciones_registros_269 as O
import operaciones_registros_272 as C
from probar_operaciones_registros_269 import Registros

def crear(**kw):return {'tipo':'encargo','operacion':'crear','revision':0,'intencion_id':str(uuid.uuid4()),'titulo':'Encargo sintético',**kw}
def foto(**kw):return {'tipo':'foto','revision':0,'intencion_id':str(uuid.uuid4()),**kw}

class Control(unittest.TestCase):
    def setUp(self):
        Registros.setUp(self)
        self.raw['clientes']=[{'id':'own'},{'id':'foreign'}]
        self.raw['asignaciones']=[{'persona_id':'a','cliente_id':'own','silla':'account'}]
        self.S.ACT=types.SimpleNamespace(es_activo_id=lambda cid:cid in ('own','foreign'))
        self.docs={'alertas/p_mili':{'generado':'2026-10-03 08:00','alertas':[{'id':'a','cliente_id':'own','gravedad':'rojo'}]},
                   'produccion/produccion':{'proyectos':[{'cliente_id':'own','revisiones_account':{'estado':'medido','fecha':'2026-10-03 08:00'},'rev_account_48':0}]}}
        self.S.modulo_recortado=Mock(side_effect=lambda r,v,cp,rel:self.docs.get(rel))
        self.S.P.REGLAS={}
    def con(self):return Registros.con(self)
    def guardar(self,b,r='a',v='a'):
        with self.con() as con:return C.guardar(self.S,con,r,v,b)
    def lista(self,r='a',v='a'):
        with self.con() as con:return C.listar(self.S,con,r,v)
    def test_encargo_propio_durable_prueba_y_deshecho_append_only(self):
        d=self.guardar(crear(cliente_id='own'));r=d['recibo']
        b={'tipo':'encargo','operacion':'actualizar','objeto':r['objeto'],'revision':1,'intencion_id':str(uuid.uuid4()),'hecho':True,'prueba':'Revisión sintética realizada'}
        hecho=self.guardar(b)['recibo'];self.assertTrue(hecho['hecho']);self.assertEqual(hecho['autor'],'a')
        b={**b,'revision':2,'intencion_id':str(uuid.uuid4()),'hecho':False,'prueba':''};self.guardar(b)
        self.assertFalse(self.lista()['registros'][0]['hecho'])
        with self.con() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM operaciones_control_272').fetchone()[0],3)
            for sql in ('DELETE FROM operaciones_control_272','UPDATE operaciones_control_272 SET actor="b"'):
                with self.assertRaises(sqlite3.IntegrityError):con.execute(sql)
    def test_asignado_dir_scope_actual_y_ajenos(self):
        r=self.guardar(crear(asignado='a',cliente_id='own'),'tomas','tomas')['recibo']
        self.assertEqual(len(self.lista()['registros']),1);self.assertEqual(self.lista('b','b')['registros'],[])
        with self.assertRaises(O.ErrorRegistro):self.guardar(crear(asignado='b'))
        with self.assertRaises(O.ErrorRegistro):self.guardar(crear(asignado='b'),'mili','mili')
        with self.assertRaises(O.ErrorRegistro):self.guardar(crear(cliente_id='foreign'))
        self.raw['asignaciones']=[]
        self.assertEqual(self.lista()['registros'],[])
    def test_cliente_act_duplicado_persona_revocada(self):
        self.guardar(crear(cliente_id='own'));self.S.ACT.es_activo_id=lambda cid:False
        self.assertEqual(self.lista()['registros'],[])
        self.S.ACT.es_activo_id=lambda cid:True;self.raw['personas'].append(self.raw['personas'][0].copy())
        with self.assertRaises(O.ErrorRegistro):self.lista()
    def test_probar_hecho_sin_prueba_y_no_cambiar_autor_scope(self):
        r=self.guardar(crear())['recibo'];base={'tipo':'encargo','operacion':'actualizar','objeto':r['objeto'],'revision':1,'intencion_id':str(uuid.uuid4()),'hecho':True}
        for b in [base,{**base,'prueba':'','autor':'b'},{**base,'prueba':'ok','asignado':'b'}]:
            with self.assertRaises(O.ErrorRegistro):self.guardar(b)
    def test_replay_encargo_concurrente_y_cas(self):
        b=crear();uno=self.guardar(b);self.assertEqual(self.guardar(b)['recibo'],uno['recibo'])
        with self.assertRaises(O.ErrorRegistro):self.guardar({**b,'titulo':'otro'})
        up={'tipo':'encargo','operacion':'actualizar','objeto':uno['recibo']['objeto'],'revision':1,'hecho':True,'prueba':'ok'}
        def op(_):
            try:return self.guardar({**up,'intencion_id':str(uuid.uuid4())})['resultado']
            except O.ErrorRegistro as e:return e.codigo
        with ThreadPoolExecutor(max_workers=2) as ex:res=list(ex.map(op,range(2)))
        self.assertCountEqual(res,['guardado',409])
    def test_foto_solo_servidor_sin_raw_pii_importes(self):
        b=foto();r=self.guardar(b,'mili','mili')['recibo'];self.assertEqual(len(r['metricas']),7)
        medidas={m['id']:m for m in r['metricas']};self.assertEqual(medidas['rojas']['valor'],1);self.assertEqual(medidas['revision48']['valor'],0)
        self.assertIsNone(medidas['imputacion']['valor']);self.assertIsNone(r['cumplimiento']);self.assertFalse(r['exhaustiva'])
        raw=json.dumps(r);self.assertNotIn('own',raw);self.assertNotIn('foreign',raw);self.assertNotIn('cliente_id',raw)
        self.assertEqual(self.guardar(b,'mili','mili')['recibo'],r)
        for body in [foto(metricas=[]),foto(cuota=1),foto(registrado_en='2026-01-01')]:
            with self.assertRaises(O.ErrorRegistro):self.guardar(body,'mili','mili')
        with self.assertRaises(O.ErrorRegistro):self.guardar(foto())
    def test_foto_fuente_vieja_ausente_duplicada_0_legado_unknown(self):
        for proyectos in [[{'cliente_id':'own','rev_account_48':0}],
                           [{'cliente_id':'own','revisiones_account':{'estado':'medido','fecha':'2026-10-02'},'rev_account_48':0}],
                           [{'cliente_id':'own','revisiones_account':{'estado':'medido','fecha':'2026-10-03 99:99'},'rev_account_48':0}],
                           self.docs['produccion/produccion']['proyectos']*2,[]]:
            self.docs['produccion/produccion']={'proyectos':proyectos}
            r=self.guardar(foto(),'mili','mili')['recibo'];self.assertIsNone(next(x for x in r['metricas'] if x['id']=='revision48')['valor'])
    def test_foto_scope_revocado_no_leak_historico(self):
        self.guardar(foto(),'mili','mili');self.assertEqual(len(self.lista('mili','mili')['registros']),1)
        self.S.P.REGLAS={'fixture_cambio_permiso':True}
        self.assertEqual(self.lista('mili','mili')['registros'],[])
    def test_revocacion_durante_captura_rollback(self):
        def fuente(*args):
            self.raw['personas']=[{**p,'estado':'baja'} if p['id']=='mili' else p for p in self.raw['personas']]
            return {'alertas':[]}
        self.S.modulo_recortado=fuente
        with self.assertRaises(O.ErrorRegistro):self.guardar(foto(),'mili','mili')
        with self.con() as con:self.assertFalse(con.execute("SELECT 1 FROM sqlite_master WHERE name='operaciones_control_272'").fetchone())
    def test_no_commit_ajeno_y_import_sin_io(self):
        with self.con() as con:
            con.execute('CREATE TABLE otro(x)');con.execute('INSERT INTO otro VALUES(1)')
            with self.assertRaises(O.ErrorRegistro):C.guardar(self.S,con,'a','a',crear())
            self.assertTrue(con.in_transaction);con.rollback();self.assertEqual(con.execute('SELECT COUNT(*) FROM otro').fetchone()[0],0)
    def test_foto_corrupta_no_publica_texto_arbitrario(self):
        self.guardar(foto(),'mili','mili')
        with self.con() as con:
            row=con.execute('SELECT * FROM operaciones_control_272').fetchone();d=json.loads(row['contenido']);d['metricas'][0]['detalle']='DATOS_PRIVADOS_SINTETICOS'
            con.execute('DROP TRIGGER operaciones_272_sin_update');con.execute('UPDATE operaciones_control_272 SET contenido=?',(json.dumps(d),));con.commit()
            with self.assertRaises(O.ErrorRegistro):C.listar(self.S,con,'mili','mili')
    def test_scope_revocado_al_cerrar_conexion_no_sale_foto(self):
        self.guardar(foto(),'mili','mili')
        S=self.S
        class Revoca(sqlite3.Connection):
            def close(self):
                super().close();S.P.REGLAS={'revocado_despues_lectura':True}
        self.S.conectar=lambda:sqlite3.connect(self.path,factory=Revoca)
        class H:
            def responder(self,c,d):return c,d
            def _api_get(self,*a):return 418,{}
            def api_post(self,*a):return 418,{}
        C.enganchar(H,self.S)
        code,d=H()._api_get(C.RUTA,{},self.raw['personas'][2],self.raw['personas'][2])
        self.assertEqual(code,200);self.assertEqual(d['registros'],[])
    def test_piloto_viewas_hook_no_filters_y_pg(self):
        from unittest.mock import patch
        import os
        class H:
            def responder(self,c,d):return c,d
            def _api_get(self,*a):return 418,{}
            def api_post(self,*a):return 418,{}
        C.enganchar(H,self.S);h=H()
        self.assertEqual(self.opens,0)
        self.assertEqual(h._api_get(C.RUTA,{'asignado':['b']},self.raw['personas'][0],self.raw['personas'][0])[0],400)
        with patch.dict(os.environ,{'RO_PILOTO_LECTURA':'si'}):self.assertEqual(h.api_post(C.RUTA,self.raw['personas'][0],self.raw['personas'][0],crear())[0],403)
        self.assertEqual(h.api_post(C.RUTA,self.raw['personas'][-1],self.raw['personas'][0],crear())[0],403)
        with patch.dict(os.environ,{'DATABASE_URL':'fixture'}):self.assertEqual(h._api_get(C.RUTA,{},self.raw['personas'][0],self.raw['personas'][0])[0],503)

if __name__=='__main__':unittest.main()
