"""499: constructor real + P/gate servidor reales; sólo fixtures anónimas."""
import ast
import copy
from pathlib import Path
import types
import unittest
import tempfile
import os
import permisos as P
from fuentes_crm.autoridad_ultima_valida_499 import construir_callback


class Autoridad499(unittest.TestCase):
    def setUp(self):
        self.active={'c1','c2'}
        self.S=types.SimpleNamespace(P=P,ACT=types.SimpleNamespace(es_activo_id=lambda cid:cid in self.active),
            E=types.SimpleNamespace(nucleo_bloqueado=False,modulos=P.cargar_modulos(),crudo={
                'personas':[dict(id=p,estado='activo',puestos=[r]) for p,r in [('ops','operaciones'),('account','account'),('other','account')]],
                'clientes':[{'id':'c1'},{'id':'c2'}],
                'asignaciones':[dict(persona_id='account',cliente_id='c1',silla='account'),dict(persona_id='other',cliente_id='c2',silla='account')]}))
        tree=ast.parse((Path(__file__).resolve().parent.parent/'servir.py').read_text())
        f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='ve_alguno')
        ns={'P':P,'E':self.S.E};exec(compile(ast.Module(body=[f],type_ignores=[]),'actual_gate','exec'),ns)
        self.S.ve_alguno=ns['ve_alguno']
        self.doc={'subcuentas':[dict(cliente_id='c1',sub_id='s1',tipo='cliente'),dict(cliente_id='c2',sub_id='s2',tipo='cliente')]}
        self.reads=0
    def read(self):self.reads+=1;return copy.deepcopy(self.doc)
    def cb(self,r='ops',v=None,reader=None):return construir_callback(self.S,r,v or r,reader or self.read)
    def test_pure_creation_and_current_exact_mapping(self):
        cb=self.cb();self.assertEqual(self.reads,0)
        d=cb();self.assertEqual(self.reads,2);self.assertEqual(d['clientes'],[{'cliente_id':'c1','subcuenta_id':'s1'},{'cliente_id':'c2','subcuenta_id':'s2'}])
        self.assertEqual(set(d),{'actor_real','actor_vista','firma_sha256','clientes'})
    def test_scope_intersection_and_viewas_real_gate(self):
        self.assertEqual(self.cb('ops','account')()['clientes'],[{'cliente_id':'c1','subcuenta_id':'s1'}])
        self.assertEqual(self.cb('account')()['clientes'],[{'cliente_id':'c1','subcuenta_id':'s1'}])
        with self.assertRaises(PermissionError):self.cb('account','ops')()
    def test_global_duplicate_cid_sid_including_foreign_and_internal(self):
        for row in [dict(cliente_id='c2',sub_id='s3',tipo='cliente'),dict(cliente_id='c3',sub_id='s2',tipo='cliente'),dict(sub_id='s2',tipo='interna')]:
            old=copy.deepcopy(self.doc);self.doc['subcuentas'].append(row)
            with self.assertRaises(PermissionError):self.cb('account')()
            self.doc=old
    def test_unknown_and_inactive_never_grant(self):
        self.active.remove('c1')
        with self.assertRaises(PermissionError):self.cb('account')()
        self.active.add('c1');self.S.E.crudo['clientes'].append({'id':'c1'})
        with self.assertRaises(PermissionError):self.cb('account')()
    def test_canonical_person_roles_and_module_current(self):
        for mutate in ('duplicate','inactive','role'):
            old=copy.deepcopy(self.S.E.crudo)
            if mutate=='duplicate':self.S.E.crudo['personas'].append(copy.deepcopy(old['personas'][0]))
            elif mutate=='inactive':self.S.E.crudo['personas'][0]['estado']='baja'
            else:self.S.E.crudo['personas'][0]['puestos']=['seo']
            with self.assertRaises(PermissionError):self.cb()()
            self.S.E.crudo=old
    def test_second_source_read_rotations_deny(self):
        for change in ('mapping','act','role','blocked'):
            self.setUp()
            def rotate():
                d=self.read()
                if self.reads==2:
                    if change=='mapping':d['subcuentas'][0]['sub_id']='rotated'
                    elif change=='act':self.active.remove('c1')
                    elif change=='role':self.S.E.crudo['personas'][0]['puestos']=['seo']
                    else:self.S.E.nucleo_bloqueado=True
                return d
            with self.assertRaises(PermissionError):self.cb(reader=rotate)()
    def test_blocked_is_global_not_omitted(self):
        self.S.E.nucleo_bloqueado=True
        with self.assertRaises(PermissionError):self.cb()()
        self.assertEqual(self.reads,0)
    def test_fresh_callback_not_permission_cache(self):
        cb=self.cb('account');before=cb();self.doc['subcuentas'][0]['sub_id']='s-new'
        self.assertNotEqual(cb()['firma_sha256'],before['firma_sha256'])
        self.S.E.crudo['asignaciones']=[]
        with self.assertRaises(PermissionError):cb()
    def test_pipeline_real_callback_offline_no_body_authority(self):
        from fuentes_crm.pipeline_ultima_valida_496 import procesar,leer_proyeccion
        with tempfile.TemporaryDirectory() as t:
            path=Path(t).resolve()/'state.json';os.chmod(path.parent,0o700)
            cb=self.cb('account');now='2026-10-04T12:00:00Z'
            read={'recurso':'contactos_total','respuestas':[{'total':0}],
                  'subcuenta_id':'s1','intentado_en':now,'observado_en':now,'fin_paginacion':True}
            dto=procesar(path,[read],cb,now,None)['proyeccion']
            self.assertEqual([r['cliente_id'] for r in dto['clientes']],['c1'])
            with self.assertRaises(PermissionError):procesar(path,[dict(read,subcuenta_id='s2')],cb,now,None)
            self.active.remove('c1')
            with self.assertRaises(PermissionError):leer_proyeccion(path,cb,now)
    def test_bad_source_error_generic(self):
        def bad():raise OSError('private/path')
        with self.assertRaises(PermissionError) as error:self.cb(reader=bad)()
        self.assertNotIn('private',str(error.exception))

if __name__=='__main__':unittest.main()
