"""467 fixtures anónimas + motor/P reales; sin principal, proveedor, red o DB."""
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
import crm_embudo_api_467 as A
import embudo_eventos as B
import permisos as P

ROOT=Path(__file__).parent


class Embudo467(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name).resolve();self.app=self.base/'app';self.app.mkdir()
        self.stage=self.base/'stage';self.stage.mkdir(mode=0o700);self.path=self.stage/'candidato.json'
        self.start='2026-10-01T00:00:00+00:00';self.end='2026-10-03T23:59:59.999999+00:00';self.cut='2026-10-04T03:00:00+00:00'
        ev=[dict(cliente_id='c1',source='ghl',lead_id='private-lead',event_id='private-event',etapa='recibido',fecha='2026-10-01T01:00:00+00:00')]
        m=B.calcular(ev,self.start,self.end,self.cut)
        self.doc={'version':'466.1','hora_fuente':'2026-10-04T04:01:00+02:00','desde':self.start,'hasta':self.end,'corte':self.cut,'clientes':[
            dict(cliente_id='c1',subcuenta_huella='a'*64,medicion=m,diagnosticos={},solo_observados=True)],'sin_pii':True,'cobertura':'parcial'}
        self.app_patch=patch.object(A,'APP',self.app);self.app_patch.start()
        paths,codes=A._paths()
        for p in [*paths.values(),*codes.values()]:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'{}')
        self.active={'c1','c2'}
        self.S=types.SimpleNamespace(P=P,ACT=types.SimpleNamespace(es_activo_id=lambda cid:cid in self.active),E=types.SimpleNamespace(nucleo_bloqueado=False,modulos=P.cargar_modulos(),crudo={
            'personas':[dict(id=x,estado='activo',puestos=[role]) for x,role in [('ops','operaciones'),('account','account'),('foreign','account')]],
            'clientes':[dict(id='c1'),dict(id='c2')],
            'asignaciones':[dict(persona_id='account',cliente_id='c1',silla='account'),dict(persona_id='foreign',cliente_id='c2',silla='account')]}))
        tree=ast.parse((ROOT/'servir.py').read_text());f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='ve_alguno')
        ns={'P':P,'E':self.S.E};exec(compile(ast.Module(body=[f],type_ignores=[]),'actual_gate','exec'),ns);self.S.ve_alguno=ns['ve_alguno']
        self.env=patch.dict(os.environ,{A.ENV:str(self.path)});self.env.start()
        self.oldpins=(A.SHA,A.MANIFEST_SHA);self.persist()
    def tearDown(self):
        A.SHA,A.MANIFEST_SHA=self.oldpins;self.env.stop();self.app_patch.stop();self.tmp.cleanup()
    def persist(self,raw=None):
        b=raw if raw is not None else json.dumps(self.doc).encode();self.path.write_bytes(b)
        paths,codes=A._paths();m={'version':'466.1','sha256':hashlib.sha256(b).hexdigest(),
            'fuentes_sha256':{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in paths.items()},
            'codigo_sha256':{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in codes.items()}}
        mb=json.dumps(m).encode();(self.stage/'manifest.json').write_bytes(mb)
        self.path.chmod(0o600);(self.stage/'manifest.json').chmod(0o600)
        A.SHA=m['sha256'];A.MANIFEST_SHA=hashlib.sha256(mb).hexdigest()
    def read(self,rid='ops',vid=None,cid='c1'):return A.listar(self.S,rid,vid or rid,cid)
    def reject(self,code,fn):
        with self.assertRaises(A.ErrorEmbudo) as e:fn()
        self.assertEqual(e.exception.codigo,code)
        return str(e.exception)
    def test_valid_pure_aggregate_and_private_fields_not_public(self):
        d=self.read();self.assertEqual(d['estado'],'copia_observada');self.assertEqual(d['medicion']['version'],'467.1')
        self.assertEqual(d['medicion']['cohorte']['recibidos_observados'],1)
        self.assertEqual(d['hora_fuente'],'2026-10-04T04:01:00+02:00')
        for denied in ('source','subcuenta_huella','grupos','private-lead','private-event','tasa_sobre_recibidos','denominador_recibidos'):
            self.assertNotIn(denied,json.dumps(d))
        self.assertEqual(d['medicion']['cohorte']['etapas']['venta'],{'observados':0,'estado':'desconocido'})
    def test_foreign_denied_before_any_IO_and_off_is_unknown(self):
        with patch.object(A,'_leer',side_effect=AssertionError('no IO')):
            self.reject(403,lambda:self.read('foreign'))
            with patch.dict(os.environ,{A.ENV:''}):
                d=self.read();self.assertEqual(d['estado'],'sin_configurar');self.assertIsNone(d['medicion']);self.assertIsNone(d['diagnosticos'])
    def test_viewas_intersection_and_revoked_view_grant(self):
        self.assertEqual(self.read('ops','account')['estado'],'copia_observada')
        self.reject(403,lambda:self.read('ops','foreign'))
        self.reject(403,lambda:self.read('account','ops'))
    def test_active_duplicates_roles_and_module_denied_no_IO(self):
        for change in ('act','person','client','role','module'):
            original=copy.deepcopy(self.S.E.crudo);self.active={'c1','c2'}
            if change=='act':self.active.remove('c1')
            elif change=='person':self.S.E.crudo['personas'].append(copy.deepcopy(self.S.E.crudo['personas'][0]))
            elif change=='client':self.S.E.crudo['clientes'].append(copy.deepcopy(self.S.E.crudo['clientes'][0]))
            elif change=='role':self.S.E.crudo['personas'][0]['puestos']=['operaciones','operaciones']
            else:self.S.E.crudo['personas'][0]['puestos']=['seo']
            with patch.object(A,'_leer',side_effect=AssertionError('no IO')):self.reject(403,lambda:self.read())
            self.S.E.crudo=original
    def test_global_duplicate_foreign_inventory_rejected(self):
        self.doc['clientes'].append(copy.deepcopy(self.doc['clientes'][0]));self.persist()
        self.reject(503,lambda:self.read())
    def test_global_shared_subaccount_for_other_client_denied(self):
        r=copy.deepcopy(self.doc['clientes'][0]);r['cliente_id']='c2';r['medicion']['grupos'][0]['cliente_id']='c2'
        self.doc['clientes'].append(r);self.persist();self.reject(503,lambda:self.read())
    def test_unsupported_stages_not_promoted_from_snapshot(self):
        original=copy.deepcopy(self.doc)
        for etapa in ('cualificado','contacto','respuesta','asistencia','venta'):
            self.doc=copy.deepcopy(original);g=self.doc['clientes'][0]['medicion']['grupos'][0]
            g['cohorte']['etapas'][etapa].update(observados=1,estado='parcial');self.persist()
            self.reject(503,lambda:self.read())
            self.doc=copy.deepcopy(original);g=self.doc['clientes'][0]['medicion']['grupos'][0]
            g['eventos_periodo'][etapa].update(eventos_observados=1,leads_unicos_observados=1,estado='parcial');self.persist()
            self.reject(503,lambda:self.read())
    def test_global_extra_keys_and_unsafe_counts_no_free_text(self):
        original=copy.deepcopy(self.doc)
        for n in (True,-1,1e999,9007199254740992):
            self.doc=copy.deepcopy(original);self.doc['clientes'][0]['medicion']['grupos'][0]['cohorte']['recibidos_observados']=n;self.persist()
            self.reject(503,lambda:self.read())
        self.doc=copy.deepcopy(original);self.doc['clientes'][0]['contacto']='private@example.test';self.persist()
        self.assertNotIn('private',self.reject(503,lambda:self.read()))
    def test_json_ambiguity_and_float_overflow(self):
        for raw in (b'{"version":"466.1","version":"466.1"}',b'{"overflow":1e999}'):
            self.persist(raw);self.reject(503,lambda:self.read())
    def test_reject_full_rates_or_sourceidentity(self):
        original=copy.deepcopy(self.doc)
        for change in ('full','rate','source'):
            self.doc=copy.deepcopy(original);g=self.doc['clientes'][0]['medicion']['grupos'][0]
            if change=='full':g['cohorte']['estado']='completo'
            elif change=='rate':g['cohorte']['etapas']['recibido']['tasa_sobre_recibidos']=1
            else:g['source']='subaccount-sensitive'
            self.persist();self.reject(503,lambda:self.read())
    def test_source_and_code_hash_changes_not_fallback(self):
        for p in [*A._paths()[0].values(),*A._paths()[1].values()]:
            before=p.read_bytes();p.write_bytes(b'changed')
            self.reject(503,lambda:self.read());p.write_bytes(before)
    def test_manifest_candidate_modes_symlinks(self):
        self.path.chmod(0o644);self.reject(503,lambda:self.read());self.path.chmod(0o600)
        original=self.path.read_bytes();self.path.unlink();target=self.base/'outside';target.write_bytes(original);target.chmod(0o600);self.path.symlink_to(target)
        self.reject(503,lambda:self.read())
    def test_last_IO_revoke_authority_pins_environment(self):
        real=A.cargar
        for change in ('act','role','core','pin','env'):
            original=copy.deepcopy(self.S.E.crudo);pins=(A.SHA,A.MANIFEST_SHA);self.active={'c1','c2'};self.S.E.nucleo_bloqueado=False;calls=[0]
            def revoke(*a,**k):
                d=real(*a,**k);calls[0]+=1
                if calls[0]==2:
                    if change=='act':self.active.clear()
                    elif change=='role':self.S.E.crudo['personas'][0]['estado']='baja'
                    elif change=='core':self.S.E.nucleo_bloqueado=True
                    elif change=='pin':A.SHA='0'*64
                    else:os.environ[A.ENV]=''
                return d
            with patch.object(A,'cargar',side_effect=revoke):self.reject(503 if change=='core' else 403,lambda:self.read())
            self.S.E.crudo=original;A.SHA,A.MANIFEST_SHA=pins;os.environ[A.ENV]=str(self.path)
    def test_change_code_during_second_load_rejected(self):
        real=A.cargar;calls=[0]
        def change(*a,**k):
            d=real(*a,**k);calls[0]+=1
            if calls[0]==1:A._paths()[1]['adaptador466'].write_bytes(b'changed')
            return d
        with patch.object(A,'cargar',side_effect=change):self.reject(503,lambda:self.read())
    def test_source_mutated_at_last_code_IO_not_returned(self):
        real=A._leer;paths,codes=A._paths();calls=[0]
        def mutate(p,*a,**k):
            b=real(p,*a,**k)
            if Path(p)==codes['embudo_eventos']:
                calls[0]+=1
                if calls[0]==2:paths['ghl_vivo'].write_bytes(b'late rotation')
            return b
        with patch.object(A,'_leer',side_effect=mutate):self.reject(503,lambda:self.read())
    def test_offset_future_and_unknown_diagnostic_fail_closed(self):
        original=copy.deepcopy(self.doc)
        for key,value in (('desde','2026-10-01T00:00:00+02:99'),('hora_fuente','2026-10-04T04:00:00+00:00'),('corte','2026-10-05T03:00:00+00:00')):
            self.doc=copy.deepcopy(original);self.doc[key]=value;self.persist();self.reject(503,lambda:self.read())
        self.doc=copy.deepcopy(original);self.doc['clientes'][0]['diagnosticos']={'contact-private@example.test':1};self.persist()
        self.assertNotIn('private',self.reject(503,lambda:self.read()))
    def test_real_466_adapter_roundtrip_only_observed(self):
        from ghl_embudo_observado_466 import preparar
        from datetime import datetime
        def epoch(s):return int(datetime.fromisoformat(s).timestamp()*1000)
        vivo={'leads':[{'contacto':'leadA','creado':epoch('2026-10-01T01:00:00+00:00'),'es_lead':True},
            {'contacto':'notALead','es_lead':False}],
            'citas':[{'id':'appointmentA','contacto':'leadA','creada':epoch('2026-10-02T01:00:00+00:00'),'estado':'cancelled'}]}
        d=preparar(vivo,'c1','locationA',self.start,self.end,self.cut)
        self.doc['clientes'][0].update(medicion=d['agregado'],diagnosticos=d['diagnosticos']);self.persist()
        out=self.read();self.assertEqual(out['diagnosticos'],{'contacto_no_lead_explicito':1})
        self.assertEqual(out['medicion']['cohorte']['etapas']['cita']['observados'],1)
        self.assertEqual(out['medicion']['cohorte']['etapas']['asistencia']['estado'],'desconocido')
    def test_route_exact_no_query_and_off_read(self):
        class H:
            def responder(self,c,d):return c,d
            def _api_get(self,*a):return 404,{}
        A.enganchar(H,self.S);h=H();p={'id':'ops'}
        self.assertEqual(h._api_get('/api/crm/embudo-observado/c1',{},p,p)[0],200)
        self.assertEqual(h._api_get('/api/crm/embudo-observado/c1',{'yo':['ops']},p,p)[0],400)
        self.assertEqual(h._api_get('/api/crm/embudo-observado/c1/extra',{},p,p)[0],404)

if __name__=='__main__':unittest.main()
