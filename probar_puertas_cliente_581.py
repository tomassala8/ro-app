"""581: endpoints AST actuales + política/ACT reales sobre JSON temporales."""
import ast
import copy
import hashlib
import json
import os
import types
import unittest
from unittest.mock import patch
import probar_revision_cliente_modulos_578 as F

CORE=F.funciones
HELPERS=('ambito_datos_581','cliente_url_581','cliente_datos_581','documento_raiz_581',
         'modulo_vigente_581','puerta_cliente_581','cliente_vigente_581','modulo_recortado')

def cargar(ns):
    ns['E'].nucleo_bloqueado=False;ns['hashlib']=hashlib
    CORE(ns)
    nodes=[copy.deepcopy(n) for n in F.TREE.body if isinstance(n,ast.FunctionDef) and n.name in HELPERS]
    assert {n.name for n in nodes}==set(HELPERS)
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),'guards581_actual','exec'),ns)

class Puertas581(unittest.TestCase):
    def setUp(self):
        self.f=F.ClienteModulos578()
        with patch.object(F,'funciones',cargar):self.f.setUp()
        self.f.ns['PANEL_PRIVADO_249']=types.SimpleNamespace(permitido=lambda *a:False)
        self.leidos=[];reader=self.f.ns['leer_json_bueno']
        def read(p):self.leidos.append(p);return reader(p)
        self.f.ns['leer_json_bueno']=read
    def tearDown(self):self.f.tearDown()
    def doc(self,rel='clientes/cid-own',**extras):
        self.f.write(rel,{'fuentes':{'gsc':{'observado':7},'libro':{'contrato':{'fixture':True}}},**extras})
    def test_cliente_url_ajeno_denegado_antes_io(self):
        self.f.write('paneles/ga4/cid-other',{'cliente_id':'cid-other','resumen':{'sesiones':7}})
        self.assertEqual(self.f.get('/api/modulo/paneles/ga4/cid-other')[0],403);self.assertEqual(self.leidos,[])
    def test_cliente_url_desconocido_duplicado_o_baja_no_lee(self):
        for cambio in ('unknown','duplicado','baja'):
            with self.subTest(cambio=cambio):
                original=list(self.f.raw['clientes']);self.f.c1['activo']=True
                if cambio=='duplicado':self.f.raw['clientes'].append(dict(self.f.c1))
                if cambio=='baja':self.f.c1['activo']=False
                cid='unknown' if cambio=='unknown' else 'cid-own'
                self.assertEqual(self.f.get('/api/modulo/paneles/ga4/'+cid)[0],403)
                self.f.raw['clientes'][:]=original
        self.assertEqual(self.leidos,[])
    def test_patron_no_cruza_segmentos_y_conserva_multisegmento_declarado(self):
        for rel in ('chat_equipo/p_other/extra/p_owner-fixture','chat_equipo//p_owner-fixture','chat_equipo/../p_owner-fixture'):
            self.assertIsNone(self.f.ns['entrada_datos_modulo'](rel))
        self.assertIsNotNone(self.f.ns['entrada_datos_modulo']('mi_dia/puestos/account/p_owner-fixture'))
        self.assertIsNotNone(self.f.ns['entrada_datos_modulo']('informe/c_2026-10/cid-own'))
        self.assertIsNone(self.f.ns['entrada_datos_modulo']('informe/c_2026-10/cid-own/extra'))
    def test_documento_personal_legitimo_no_fila_ok_en_raiz(self):
        self.f.write('chat_equipo/p_owner-fixture',{'persona_id':'dato-no-usado-como-autoridad','marca_fixture':True,'mensajes':[]})
        code,d=self.f.get('/api/modulo/chat_equipo/p_owner-fixture')
        self.assertEqual(code,200);self.assertTrue(d['marca_fixture'])
        self.assertEqual(self.f.get('/api/modulo/chat_equipo/p_owner-fixture',real=self.f.other,vista=self.f.actor)[0],403)
    def test_raiz_cliente_ajeno_en_modulo_agregado_denegada(self):
        self.f.write('captacion/captacion',{'cliente_id':'cid-other','resumen':{'observado':7}})
        self.assertEqual(self.f.get('/api/modulo/captacion/captacion')[0],403)
    def test_raiz_cliente_propio_y_listas_recortadas(self):
        self.f.write('paneles/ga4/cid-own',{'cliente_id':'cid-own','resumen':{'observado':7},'filas':[{'cliente_id':'cid-other','observado':8}]})
        code,d=self.f.get('/api/modulo/paneles/ga4/cid-own');self.assertEqual(code,200)
        self.assertEqual(d['resumen']['observado'],7);self.assertEqual(d['filas'],[])
    def test_raiz_ids_contradictorios_y_malformados_denegados(self):
        for extra in ({'cid':'cid-other'},{'cid':[]},{'cli':{}},{'cid':''}):
            self.f.write('paneles/ga4/cid-own',{'cliente_id':'cid-own',**extra})
            self.assertEqual(self.f.get('/api/modulo/paneles/ga4/cid-own')[0],403)
    def test_root_url_discrepante_tambien_ops(self):
        self.f.actor['puestos']=['operaciones'];self.doc(cliente_id='cid-other')
        self.assertEqual(self.f.get('/api/cliente/cid-own')[0],403)
    def test_interseccion_real_vista_no_root_ajeno(self):
        self.f.write('paneles/ga4/cid-own',{'cliente_id':'cid-own','resumen':{'observado':7}})
        self.assertEqual(self.f.get('/api/modulo/paneles/ga4/cid-own',real=self.f.other,vista=self.f.actor)[0],403)
    def test_todo_real_suyo_vista_usa_cartera_de_cada_nivel(self):
        self.f.other['puestos']=['operaciones'];self.f.write('paneles/ga4/cid-own',{'cliente_id':'cid-own','resumen':{'observado':7}})
        self.assertEqual(self.f.get('/api/modulo/paneles/ga4/cid-own',real=self.f.other,vista=self.f.actor)[0],200)
    def test_cliente_grants_alternativos_legitimos_no_puerta_solo_menu(self):
        self.f.e.modulos['ficha']['account']=None;self.doc()
        self.assertEqual(self.f.get('/api/cliente/cid-own')[0],200)
        for m in ('ficha','bandeja','captacion','asistente-ia'):
            self.f.e.modulos.setdefault(m,{})['account']=None
        self.leidos.clear();self.assertEqual(self.f.get('/api/cliente/cid-own')[0],403);self.assertEqual(self.leidos,[])
    def test_outreach_actual_sin_modulo_403(self):
        self.f.actor['puestos']=['outreach'];self.f.raw['asignaciones'][0]['silla']='outreach';self.doc()
        self.assertEqual(self.f.get('/api/cliente/cid-own')[0],403);self.assertEqual(self.leidos,[])
    def test_resumen_produccion_solo_cabecera_sin_io(self):
        self.f.actor['puestos']=['produccion'];self.f.raw['asignaciones'][0]['silla']='produccion';self.doc()
        code,d=self.f.get('/api/cliente/cid-own');self.assertEqual(code,200)
        self.assertEqual(d['nivel'],'resumen');self.assertIsNone(d['fuentes']);self.assertEqual(self.leidos,[])
    def test_admin_preserva_allowlist_exacta(self):
        self.f.actor['puestos']=['administracion'];self.doc()
        code,d=self.f.get('/api/cliente/cid-own');self.assertEqual(code,200)
        self.assertEqual(set(d['fuentes']['fuentes']),{'libro'})
        self.assertTrue(d['fuentes']['fuentes']['libro']['contrato']['fixture'])
    def test_revocacion_durante_io_modulo_no_publica(self):
        self.f.write('paneles/ga4/cid-own',{'cliente_id':'cid-own','resumen':{'observado':7}})
        read=self.f.ns['leer_json_bueno']
        def changed(p):
            out=read(p);self.f.c1['activo']=False;return out
        self.f.ns['leer_json_bueno']=changed
        self.assertEqual(self.f.get('/api/modulo/paneles/ga4/cid-own')[0],403)
    def test_revocacion_durante_io_ficha_no_publica(self):
        self.doc();read=self.f.ns['leer_json_bueno']
        def changed(p):
            out=read(p);self.f.e.modulos['ficha']['account']=None;return out
        self.f.ns['leer_json_bueno']=changed
        self.assertEqual(self.f.get('/api/cliente/cid-own')[0],403)
    def test_revocacion_act_en_fichero_durante_io_no_publica(self):
        self.doc();read=self.f.ns['leer_json_bueno']
        def changed(p):
            out=read(p)
            estado=json.loads(F.ACT.ESTADO.read_text());estado['activos']=[x for x in estado['activos'] if x['id']!='cid-own']
            F.ACT.ESTADO.write_text(json.dumps(estado));return out
        self.f.ns['leer_json_bueno']=changed
        self.assertEqual(self.f.get('/api/cliente/cid-own')[0],403)
    def test_identidad_baja_duplicada_o_roles_viejos_deniega(self):
        self.doc()
        snapshot=copy.deepcopy(self.f.actor)
        self.f.raw['personas'].append(dict(self.f.actor));self.assertEqual(self.f.get('/api/cliente/cid-own')[0],403);self.f.raw['personas'].pop()
        self.f.actor['estado']='baja';self.assertEqual(self.f.get('/api/cliente/cid-own')[0],403)
        self.f.actor.update(snapshot);self.f.raw['personas'][0]=dict(snapshot,puestos=['operaciones'])
        self.assertEqual(self.f.get('/api/cliente/cid-own')[0],403)
    def test_nominal_panel_249_conservado(self):
        self.f.actor['puestos']=['direccion']
        self.assertEqual(self.f.ns['puerta_modulo'](self.f.actor,self.f.actor,'panel_direccion/panel',False)['error'][0],403)
    def test_memoria_revocada_antes_return_no_publica(self):
        self.f.write('paneles/ga4/cid-own',{'cliente_id':'cid-own','resumen':{'observado':7}})
        self.f.ns['_estado_fichero']=lambda p:('fixture',1)
        def cached(key):
            self.f.c1['activo']=False
            return {'cuerpo':b'no-publicar'}
        self.f.ns['CACHE_RESP']=types.SimpleNamespace(leer=cached)
        self.f.ns['responder_de_memoria']=lambda *a: (_ for _ in ()).throw(AssertionError('se publicó cache revocada'))
        self.assertEqual(self.f.get('/api/modulo/paneles/ga4/cid-own')[0],403)
    def test_busqueda_misma_puerta_raiz(self):
        self.f.write('captacion/captacion',{'cliente_id':'cid-other','resumen':{'observado':7}})
        cp=F.P.contexto(self.f.actor,self.f.raw)
        self.assertIsNone(self.f.ns['modulo_recortado'](self.f.actor,self.f.actor,cp,'captacion/captacion'))
    def marca_real(self):
        node=copy.deepcopy(next(n for n in F.TREE.body if isinstance(n,ast.FunctionDef) and n.name=='_estado_fichero'))
        exec(compile(ast.Module(body=[node],type_ignores=[]),'marca581_real','exec'),self.f.ns)
    def reemplazar_durante_lectura(self):
        self.marca_real();read=self.f.ns['leer_json_bueno']
        def changed(p):
            out=read(p);nuevo=p.with_suffix('.reemplazo');nuevo.write_bytes(p.read_bytes());os.replace(nuevo,p)
            return out
        self.f.ns['leer_json_bueno']=changed
    def test_epoca_fichero_modulo_cambia_aun_con_mismo_json(self):
        self.f.write('paneles/ga4/cid-own',{'cliente_id':'cid-own','resumen':{'observado':7}})
        self.reemplazar_durante_lectura()
        self.assertEqual(self.f.get('/api/modulo/paneles/ga4/cid-own')[0],403)
    def test_epoca_fichero_ficha_cambia_aun_con_mismo_json(self):
        self.doc();self.reemplazar_durante_lectura()
        self.assertEqual(self.f.get('/api/cliente/cid-own')[0],403)
    def test_cache_cambia_con_catalogo_aun_version_general_igual(self):
        self.f.write('paneles/ga4/cid-own',{'cliente_id':'cid-own','resumen':{'observado':7}})
        self.marca_real();claves=[]
        def leer(key):claves.append(key);return {'cuerpo':b'fixture-sin-datos'}
        self.f.ns['CACHE_RESP']=types.SimpleNamespace(leer=leer)
        self.f.ns['responder_de_memoria']=lambda h,g:(200,{'fixture':True})
        self.assertEqual(self.f.get('/api/modulo/paneles/ga4/cid-own')[0],200)
        self.f.raw['meta']['revision_fixture']=2
        self.assertEqual(self.f.get('/api/modulo/paneles/ga4/cid-own')[0],200)
        self.assertEqual(len(claves),2);self.assertNotEqual(claves[0],claves[1])
        self.assertEqual(claves[0][-2],claves[1][-2])

if __name__=='__main__':unittest.main()
