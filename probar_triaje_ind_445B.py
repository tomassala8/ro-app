"""Revisión independiente sin servidor: módulos reales/P actual + SQLite temporal."""
import ast
import concurrent.futures
import copy
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import types
import unittest
import uuid
from unittest.mock import patch
import permisos as P
import triaje_guardia_445 as G
import intenciones_acciones as I

ROOT=Path(__file__).parent


class Independiente(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name)
        self.source=self.base/'bandeja/bandeja.json';self.source.parent.mkdir()
        self.doc={'triaje':[dict(id='g-T1',numero='T1',cliente_id='c1',propuesta='seguro',agente_propuesto_id='account',fecha='2026-10-04',url='https://desk.example/ticket/1',departamento='dept')],
            'correos':[dict(id='t-T1',numero='T1',cliente_id='c1',url='https://desk.example/ticket/1',departamento='dept')]}
        self.persist()
        self.active={'c1'}
        self.S=types.SimpleNamespace(P=P,DATA=self.base,ACT=types.SimpleNamespace(es_activo_id=lambda c:c in self.active),
            E=types.SimpleNamespace(nucleo_bloqueado=False,modulos=P.cargar_modulos(),crudo={
                'personas':[dict(id=x,estado='activo',puestos=[r]) for x,r in [('ops','operaciones'),('ops2','operaciones'),('account','account')]],
                'clientes':[dict(id='c1')],'asignaciones':[dict(persona_id='account',cliente_id='c1',silla='account')]}))
        tree=ast.parse((ROOT/'servir.py').read_text())
        funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('ve_alguno','lleva_cliente')]
        ns={'P':P,'E':self.S.E};exec(compile(ast.Module(body=funcs,type_ignores=[]),'actual_helpers','exec'),ns)
        self.S.ve_alguno=ns['ve_alguno'];self.S.lleva_cliente=ns['lleva_cliente']
        self.db=self.base/'test.sqlite'
        with sqlite3.connect(self.db) as c:c.executescript((ROOT/'schema_v2.sql').read_text())
        self.body=dict(modulo='bandeja',herramienta='desk',tipo='asignar',objeto='T1',cliente_id='c1',intencion_id=str(uuid.uuid4()),texto='Solicitar asignación del ticket T1',vista_previa=dict(a='account',ticket='T1',origen='triaje'))
        self.env=patch.dict(os.environ,{'DATABASE_URL':'','RO_PILOTO_LECTURA':''});self.env.start()

    def tearDown(self):self.env.stop();self.tmp.cleanup()
    def persist(self):self.source.write_text(json.dumps(self.doc))
    def store(self,b=None,actor='ops',final=None):
        b=b or self.body;r={'id':actor}
        with sqlite3.connect(self.db,timeout=5) as c:
            I.iniciar(c);g=G.preparar(self.S,c,r,r,b)
            def insert(con):
                G.sin_previa(con,g)
                aid=con.execute("INSERT INTO acciones(quien,herramienta,tipo,objeto,cliente_id,modulo,estado) VALUES (?,?,?,?,?,?,'simulada')",(actor,'desk',b['tipo'],b['objeto'],b['cliente_id'],'bandeja')).lastrowid
                if final:final()
                return aid
            result=I.guardar(c,actor,b,insert);G.revalidar(self.S,c,r,r,b,g);return result
    def count(self):
        with sqlite3.connect(self.db) as c:return c.execute('SELECT count(*) FROM acciones').fetchone()[0]

    def test_two_actors_concurrent_and_same_uuid_replay(self):
        barrier=threading.Barrier(2)
        def attempt(actor):
            barrier.wait()
            try:return self.store(actor=actor),200
            except I.RechazoAccion as e:return None,e.codigo
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:rows=list(ex.map(attempt,['ops','ops2']))
        self.assertEqual(sorted(x[1] for x in rows),[200,409]);self.assertEqual(self.count(),1)
        winner=['ops','ops2'][next(i for i,x in enumerate(rows) if x[1]==200)]
        aid,rep=self.store(actor=winner);self.assertTrue(rep);self.assertEqual(self.count(),1)

    def test_close432_first_then_assignment_blocked(self):
        close=dict(self.body,intencion_id=str(uuid.uuid4()),tipo='cerrar',texto='Solicitar cierre del ticket T1 desde el reparto',vista_previa=dict(estado='Cerrado',ticket='T1'))
        self.assertTrue(G.aplica(close));self.store(close)
        with self.assertRaises(I.RechazoAccion) as e:self.store()
        self.assertEqual(e.exception.codigo,409);self.assertEqual(self.count(),1)

    def test_module_and_recipient_revoked_at_final_validation_rollback(self):
        for revoke in (lambda:self.S.E.crudo['personas'][0].update(puestos=['account']),
                       lambda:self.S.E.crudo['personas'][2].update(estado='baja')):
            original=copy.deepcopy(self.S.E.crudo)
            with self.assertRaises(I.RechazoAccion):self.store(final=revoke)
            self.assertEqual(self.count(),0);self.S.E.crudo=original

    def test_cross_client_alias_collision_rollback(self):
        self.doc['correos'][0]['cliente_id']='c2';self.persist()
        with self.assertRaises(I.RechazoAccion) as e:self.store()
        self.assertEqual(e.exception.codigo,503);self.assertEqual(self.count(),0)

    def test_source_replacement_between_insert_and_final_rolls_back(self):
        def rotate():
            self.doc['triaje'][0]['agente_propuesto_id']='ops2';self.persist()
        with self.assertRaises(I.RechazoAccion):self.store(final=rotate)
        self.assertEqual(self.count(),0)

    def test_replay_after_active_revocation_not_receipt(self):
        self.store();self.active.clear()
        with self.assertRaises(I.RechazoAccion) as e:self.store()
        self.assertEqual(e.exception.codigo,403);self.assertEqual(self.count(),1)


if __name__=='__main__':unittest.main()
