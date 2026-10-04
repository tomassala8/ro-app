"""Endpoint y depósito sintéticos, permisos actuales; sin bootstrap, red o DB."""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
import metodo_cuentas as M
import metodo_evidencia_452 as E
import permisos as P

ROOT=Path(__file__).parent


class Evidencia452(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name).resolve();self.base.chmod(0o700)
        self.doc={'version':1,'importado_el':'2026-10-01','cobertura':'parcial','clientes':{'c1':[
            dict(id='fathom_'+'a'*24,cliente_id='c1',fecha='2026-09-20',fecha_ambigua=False,
                registro='registro_historico',celebrada_confirmada=False,privado='secreto contrato 1470')]}}
        self.persist()
        self.regla={'regla':{'id':M.REGLA_ID,'cadencia_dias':15,'responsable_role':'trafficker'},'clientes':[
            dict(cliente_id='c1',estado_cohorte='confirmada',tipo_cohorte='metodo_actual_recurrente',cadencia_dias=15,responsable_role='trafficker')]}
        self.active={'c1'}
        self.S=types.SimpleNamespace(P=P,ACT=types.SimpleNamespace(es_activo_id=lambda cid:cid in self.active),
            E=types.SimpleNamespace(nucleo_bloqueado=False,modulos=P.cargar_modulos(),crudo={
                'personas':[dict(id=x,estado='activo',puestos=[role]) for x,role in [('ops','operaciones'),('account','account'),('paid','trafficker')]],
                'clientes':[dict(id='c1',servicios={'publicidad':'sí'})],
                'asignaciones':[dict(cliente_id='c1',persona_id='account',silla='account',desde='2026-09-01'),
                               dict(cliente_id='c1',persona_id='paid',silla='trafficker',desde='2026-09-01')]}))
        tree=ast.parse((ROOT/'servir.py').read_text());f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='ve_alguno')
        ns={'P':P,'E':self.S.E};exec(compile(ast.Module(body=[f],type_ignores=[]),'real_gate','exec'),ns);self.S.ve_alguno=ns['ve_alguno']
        class Handler:
            def responder(self,c,b):return c,b
            def _api_get(self,*a):return 404,{}
        self.h=Handler();self.old=M.S;M.enganchar(Handler,self.S)
        self.patches=[patch.dict(os.environ,{'RO_HISTORIAL_REUNIONES':str(self.base)}),
            patch.object(M,'leer',lambda path:self.regla if path==M.REGLAS else {}),
            patch.object(M.ACT,'es_activo_id',lambda cid:cid in self.active),patch.object(P,'hoy_iso',lambda:'2026-10-04')]
        for p in self.patches:p.start()
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        M.S=self.old;self.tmp.cleanup()
    def persist(self):
        raw=json.dumps(self.doc).encode();(self.base/'reuniones.json').write_bytes(raw)
        (self.base/'manifest.json').write_text(json.dumps({'version':1,'asof':'2026-10-01','archivos':{'reuniones.json':hashlib.sha256(raw).hexdigest()}}))
        for p in self.base.iterdir():p.chmod(0o600)
    def get(self,actor='ops',vista=None):return self.h._api_get('/api/metodo/sugerencias',{},dict(id=actor),dict(id=vista or actor))
    def ev(self,actor='ops'):
        code,d=self.get(actor);self.assertEqual(code,200);self.assertEqual(len(d['sugerencias']),1)
        return d['sugerencias'][0]['evidencia_por_revisar']
    def test_real_history_additive_no_confirmation_or_private_content(self):
        e=self.ev();self.assertEqual(e['estado_fuente'],'disponible');self.assertEqual(e['registros_historicos_observados'],1)
        self.assertEqual(e['ultimo_registro_historico'],'2026-09-20')
        d=self.get()[1]['sugerencias'][0];self.assertIsNone(d['ultima_confirmada']);self.assertIsNone(d['proxima_revision'])
        for word in ('secreto','1470','fathom_'):self.assertNotIn(word,json.dumps(d))
    def test_paid_no_history_IO_but_method_still_available(self):
        with patch.object(E,'leer_historial',side_effect=AssertionError('no IO')):
            e=self.ev('paid');self.assertEqual(e['estado_fuente'],'no_autorizado');self.assertIsNone(e['registros_historicos_observados'])
    def test_account_authorized_and_no_config_unknown_not_zero(self):
        self.assertEqual(self.ev('account')['estado_fuente'],'disponible')
        with patch.dict(os.environ,{'RO_HISTORIAL_REUNIONES':''}):
            e=self.ev();self.assertEqual(e['estado_fuente'],'sin_configurar');self.assertIsNone(e['registros_historicos_observados'])
    def test_corrupt_manifest_and_mode_unknown_preserves_method(self):
        for change in (lambda:(self.base/'manifest.json').write_text('{}'),lambda:(self.base/'reuniones.json').chmod(0o644)):
            self.persist();change();e=self.ev();self.assertEqual(e['estado_fuente'],'no_disponible');self.assertIsNone(e['registros_historicos_observados'])
    def test_global_foreign_collision_not_hidden_by_scope(self):
        self.doc['clientes']['foreign']=[dict(self.doc['clientes']['c1'][0],cliente_id='foreign')];self.persist()
        e=self.ev();self.assertEqual(e['estado_fuente'],'no_disponible');self.assertIsNone(e['registros_historicos_observados'])
    def test_duplicate_json_and_nonfinite_global_rejected(self):
        for raw in (b'{"version":1,"version":1}',b'{"version":1,"extra":1e999}'):
            (self.base/'manifest.json').write_bytes(raw)
            self.assertEqual(self.ev()['estado_fuente'],'no_disponible')
    def test_revocation_during_source_read_scope_or_core_denies(self):
        for kind in ('act','role','module','duplicate','core'):
            saved=copy.deepcopy(self.S.E.crudo);self.active={'c1'};self.S.E.nucleo_bloqueado=False
            real=E.leer_historial
            def revoke(*a,**k):
                d=real(*a,**k)
                if kind=='act':self.active.clear()
                elif kind=='role':self.S.E.crudo['personas'][0]['estado']='baja'
                elif kind=='module':self.S.E.crudo['personas'][0]['puestos']=['setter']
                elif kind=='duplicate':self.S.E.crudo['personas'].append(copy.deepcopy(self.S.E.crudo['personas'][0]))
                else:self.S.E.nucleo_bloqueado=True
                return d
            with patch.object(E,'leer_historial',side_effect=revoke):self.assertEqual(self.get()[0],403,kind)
            self.S.E.crudo=saved
    def test_policy_changed_and_source_rotated_before_response(self):
        original=E.enriquecer
        def mutate(*a,**k):
            result=original(*a,**k);self.regla['clientes'][0]['estado_cohorte']='pendiente';return result
        with patch.object(E,'enriquecer',side_effect=mutate):self.assertEqual(self.get()[0],403)
        self.regla['clientes'][0]['estado_cohorte']='confirmada'
        def rotate(*a,**k):
            result=original(*a,**k);self.doc['clientes']['c1'][0]['fecha']='2026-09-21';self.persist();return result
        with patch.object(E,'enriquecer',side_effect=rotate):self.assertEqual(self.get()[0],403)
    def test_scope_view_denied_or_actor_unknown(self):
        self.assertEqual(self.get(actor='unknown')[0],403)
        self.assertEqual(self.get(actor='account',vista='ops')[0],403)
    def test_valid_empty_is_zero_observed_partial_not_absence(self):
        self.doc['clientes']['c1']=[];self.persist();e=self.ev()
        self.assertEqual(e['registros_historicos_observados'],0);self.assertEqual(e['cobertura'],'parcial')
        self.assertIsNone(e['celebracion_confirmada'])
    def test_missing_client_inventory_is_unknown_not_zero(self):
        self.doc['clientes']={};self.persist();e=self.ev()
        self.assertEqual(e['estado_fuente'],'no_disponible')
        for field in ('registros_historicos_observados','ultimo_registro_historico','importado_el'):
            self.assertIsNone(e[field])
        self.assertEqual(e['cobertura'],'desconocida')
    def test_future_import_and_hash_invalid_unknown_not_zero(self):
        mpath=self.base/'manifest.json';m=json.loads(mpath.read_text())
        for update in ({'asof':'2026-10-05'},{'archivos':{'reuniones.json':'0'*64}}):
            mpath.write_text(json.dumps({**m,**update}));e=self.ev()
            self.assertEqual(e['estado_fuente'],'no_disponible');self.assertIsNone(e['registros_historicos_observados'])
    def test_last_history_IO_revocation_before_response(self):
        real=E.H.privado
        for kind in ('act','policy','catalogue'):
            self.active={'c1'};original=copy.deepcopy(self.S.E.crudo);rules=copy.deepcopy(P.REGLAS);calls=[0]
            def revoke(*a,**k):
                r=real(*a,**k);calls[0]+=1
                if calls[0]==8:
                    if kind=='act':self.active.clear()
                    elif kind=='policy':P.REGLAS['452_test_revoked']=True
                    else:self.S.E.crudo['clientes'].append(copy.deepcopy(self.S.E.crudo['clientes'][0]))
                return r
            with patch.object(E.H,'privado',side_effect=revoke):self.assertEqual(self.get()[0],403,kind)
            self.assertEqual(calls[0],8);self.S.E.crudo=original;P.REGLAS.clear();P.REGLAS.update(rules)
    def test_mtime_rotated_after_preparation_denies(self):
        original=E.enriquecer
        def rotate(*a,**k):
            result=original(*a,**k);p=self.base/'reuniones.json';s=p.stat()
            os.utime(p,ns=(s.st_atime_ns,s.st_mtime_ns+1000000));return result
        with patch.object(E,'enriquecer',side_effect=rotate):self.assertEqual(self.get()[0],403)
    def test_module_history_denied_no_source_hint_or_IO(self):
        original=self.S.ve_alguno
        self.S.ve_alguno=lambda p,mods:False if mods==['reuniones'] else original(p,mods)
        with patch.object(E,'leer_historial',side_effect=AssertionError('history not authorized')):
            e=self.ev();self.assertEqual(e['estado_fuente'],'no_autorizado')
            self.assertIsNone(e['ultimo_registro_historico']);self.assertIsNone(e['importado_el'])

if __name__=='__main__':unittest.main()
