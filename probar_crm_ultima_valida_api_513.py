"""513 autoridad real499/P y archivos anónimos temporales; sin servidor/red."""
import copy,hashlib,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import crm_ultima_valida_api_513 as A
from fuentes_crm import probar_autoridad_ultima_valida_499 as fixtures499
from fuentes_crm.ultima_valida_490 import VERSION

class API513(unittest.TestCase):
    def setUp(self):
        f=fixtures499.Autoridad499();f.setUp();self.f=f;self.S=f.S
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve()
        self.app=self.root/'app';self.app.mkdir();self.stage=self.root/'stage';self.stage.mkdir(mode=0o700)
        self.path=self.stage/'estado.json';self.papp=patch.object(A,'APP',self.app);self.papp.start()
        for p in [*A._fuentes().values(),*A._codigos().values()]:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'{}')
        A._fuentes()['crm'].write_text(json.dumps(f.doc))
        self.state={'version':VERSION,'recursos':{}};self.pins=A.MANIFEST_SHA
        self.env=patch.dict(os.environ,{A.ENV:str(self.path),A.PIN_ENV:''});self.env.start();self.persist()
    def tearDown(self):A.MANIFEST_SHA=self.pins;self.env.stop();self.papp.stop();self.tmp.cleanup()
    def persist(self):
        self.path.write_text(json.dumps(self.state));self.path.chmod(0o600)
        m={'version':'513.1','estado_sha256':hashlib.sha256(self.path.read_bytes()).hexdigest(),
            'fuentes_sha256':{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in A._fuentes().items()},
            'codigo_sha256':{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in A._codigos().items()}}
        mb=json.dumps(m).encode();mp=self.stage/'manifest.json';mp.write_bytes(mb);mp.chmod(0o600);A.MANIFEST_SHA=hashlib.sha256(mb).hexdigest()
    def read(self,r='ops',v=None):return A.listar(self.S,r,v or r)
    def reject(self,code,call):
        with self.assertRaises(A.ErrorLectura) as e:call()
        self.assertEqual(e.exception.codigo,code);self.assertNotIn(str(self.root),str(e.exception))
    def test_valid_unknown_empty_no_private_ids(self):
        dto=self.read('ops','account');self.assertEqual(dto['estado'],'copia_observada')
        self.assertEqual(dto['proyeccion']['version'],'496.2');self.assertEqual([c['cliente_id'] for c in dto['proyeccion']['clientes']],['c1'])
        for r in dto['proyeccion']['clientes'][0]['recursos']:self.assertIsNone(r['conteo_observado'])
        for value in ('s1','s2',str(self.path),'firma_sha256','actor_real'):self.assertNotIn(value,json.dumps(dto))
    def test_off_no_io_and_unauthorized_before_config_disclosure(self):
        with patch.dict(os.environ,{A.ENV:''}),patch.object(A,'_leer',side_effect=AssertionError('IO')):
            self.assertIsNone(self.read()['proyeccion'])
            self.reject(403,lambda:self.read('account','ops'))
            self.f.active.clear();self.reject(403,lambda:self.read())
    def test_corruption_old_version_and_pin_fail_closed(self):
        for value in ('not json','{"version":"490.3","version":"490.3","recursos":{}}',json.dumps({'version':'490.2','recursos':{}})):
            self.path.write_text(value);self.path.chmod(0o600)
            self.reject(503,self.read)
        self.persist();A.MANIFEST_SHA='f'*64;self.reject(503,self.read)
    def test_private_modes_links_and_wrong_confined_path(self):
        self.path.chmod(0o644);self.reject(503,self.read);self.path.chmod(0o600)
        target=self.stage/'other.json';self.path.rename(target);self.path.symlink_to(target);self.reject(503,self.read)
        self.path.unlink();target.rename(self.path)
        link=self.root/'link';link.symlink_to(self.stage,target_is_directory=True)
        with patch.dict(os.environ,{A.ENV:str(link/'estado.json')}):self.reject(503,self.read)
        extra=self.stage/'hardlink';os.link(self.path,extra);self.reject(503,self.read)
    def test_source_corruption_and_mapping_revocation_never_fallback(self):
        A._fuentes()['crm'].write_text('not json');self.reject(503,self.read)
        A._fuentes()['crm'].write_text(json.dumps(self.f.doc));self.persist()
        original=A._cargar;count=[]
        def rotate(*args):
            result=original(*args);count.append(1)
            if len(count)==2:self.S.E.crudo['asignaciones']=[]
            return result
        with patch.object(A,'_cargar',side_effect=rotate):self.reject(403,lambda:self.read('account'))
    def test_config_and_source_rotated_last_io(self):
        original=A._cargar;calls=[]
        def rotate(*args):
            result=original(*args);calls.append(1)
            if len(calls)==2:os.environ[A.ENV]=''
            return result
        with patch.object(A,'_cargar',side_effect=rotate):self.reject(403,self.read)
    def test_bound_and_json_metadata_no_fallback(self):
        self.path.write_bytes(b' '* (A.MAX+1));self.path.chmod(0o600);self.reject(503,self.read)
    def test_unknown_mapping_denied_before_private_state_io(self):
        self.f.doc['subcuentas']=[self.f.doc['subcuentas'][1]]
        A._fuentes()['crm'].write_text(json.dumps(self.f.doc));self.persist()
        with patch.object(A,'_cargar',side_effect=AssertionError('private state IO')):
            self.reject(403,lambda:self.read('account'))
        self.S.E.nucleo_bloqueado=True
        with patch.object(A,'_leer',side_effect=AssertionError('IO')):self.reject(503,self.read)
    def test_zero_observed_original_stamp_not_get_stamp(self):
        from fuentes_crm.adaptadores_ultima_valida_493 import adaptar
        from fuentes_crm.ultima_valida_490 import actualizar
        old='2020-01-01T12:00:00Z'
        e=adaptar('contactos_total',[{'total':0}],subcuenta_id='s1',intentado_en=old,observado_en=old,fin_paginacion=True)
        self.state=actualizar(self.state,[e],old);self.persist()
        dto=self.read('account')['proyeccion'];r=next(r for r in dto['clientes'][0]['recursos'] if r['recurso']=='contactos_total')
        self.assertEqual(r['conteo_observado'],0)
        self.assertEqual(r['observaciones'][0]['observado_en'],'2020-01-01T12:00:00+00:00')
        self.assertNotEqual(dto['generado'],r['observaciones'][0]['observado_en'])
    def test_hook_optin_exact_route_no_query(self):
        class H:
            def _api_get(self,*args):return 'original'
            def responder(self,status,obj):return status,obj
        A.enganchar(H,self.S);h=H()
        self.assertEqual(h._api_get('/other',{}, {'id':'ops'},{'id':'ops'}),'original')
        self.assertEqual(h._api_get('/api/crm/ultima-valida',{'path':'private'}, {'id':'ops'},{'id':'ops'})[0],400)
        self.assertEqual(h._api_get('/api/crm/ultima-valida',{}, {'id':'ops'},{'id':'account'})[0],200)
    def test_runtime_pin_activation_without_code_change_and_rotation(self):
        pin=A.MANIFEST_SHA;A.MANIFEST_SHA=''
        code_before=A._codigos()['api'].read_bytes()
        with patch.dict(os.environ,{A.PIN_ENV:pin}):
            self.assertEqual(self.read()['estado'],'copia_observada')
            self.assertEqual(A._codigos()['api'].read_bytes(),code_before)
            original=A._cargar;calls=[]
            def rotate(*args):
                value=original(*args);calls.append(1)
                if len(calls)==2:os.environ[A.PIN_ENV]='f'*64
                return value
            with patch.object(A,'_cargar',side_effect=rotate):self.reject(403,self.read)
        with patch.dict(os.environ,{A.PIN_ENV:'invalid'}):self.reject(503,self.read)
    def test_pinned_mapping_precedes_state_payload(self):
        doc=copy.deepcopy(self.f.doc);doc['subcuentas'][0]['sub_id']='foreign-valid-sid'
        A._fuentes()['crm'].write_text(json.dumps(doc))
        original=A._leer;reads=[]
        def reader(path,*args):
            reads.append(Path(path))
            if Path(path)==self.path:raise AssertionError('state payload before mapping pin')
            return original(path,*args)
        with patch.object(A,'_leer',side_effect=reader):self.reject(503,lambda:self.read('account'))
        self.assertNotIn(self.path,reads)
    def test_scope_revoked_after_pins_before_state_payload(self):
        original=A._leer
        def reader(path,*args):
            result=original(path,*args)
            if Path(path)==A._codigos()['gate']:self.f.active.clear()
            if Path(path)==self.path:raise AssertionError('state IO after revoke')
            return result
        with patch.object(A,'_leer',side_effect=reader):self.reject(403,self.read)
if __name__=='__main__':unittest.main()
