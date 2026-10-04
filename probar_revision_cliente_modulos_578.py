"""L05/L10: endpoint AST real, reglas reales, ficheros/ACT únicamente sintéticos."""
import ast
import copy
import json
import os
import re
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
import permisos as P
from fuentes_verdad import clientes_activos as ACT

APP=Path(__file__).resolve().parent
TREE=ast.parse((APP/'servir.py').read_text())

def funciones(ns):
    # Definiciones/constantes puras de recorte; no se ejecuta Estado() ni bootstrap.
    nodes=[copy.deepcopy(n) for n in TREE.body if 808<=n.lineno<1208 and isinstance(n,(ast.FunctionDef,ast.ClassDef,ast.Assign))]
    nodes += [copy.deepcopy(next(n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name==s)) for s in ('entrada_datos_modulo','puerta_modulo')]
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),'recortes-reales578','exec'),ns)
    api=next(n for n in ast.walk(TREE) if isinstance(n,ast.FunctionDef) and n.name=='_api_get')
    body=[]
    for i,n in enumerate(api.body):
        if isinstance(n,ast.Assign) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='fullmatch' and isinstance(n.value.args[0],ast.Constant) and n.value.args[0].value in (r'/api/cliente/([\w\-]+)',r'/api/modulo/([\w\-/]+)'):
            body.extend(copy.deepcopy(api.body[i:i+2]))
    assert len(body)==4,'fragmentos reales API requeridos'
    f=ast.parse('def endpoint(self,ruta,q,real,persona,cp,solo_lectura):\n pass').body[0];f.body=body
    exec(compile(ast.fix_missing_locations(ast.Module(body=[f],type_ignores=[])),'api-real578','exec'),ns)

class ClienteModulos578(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.data=Path(self.t.name)/'data';self.data.mkdir()
        self.actor={'id':'owner-fixture','nombre':'Owner fixture','alias':'Fixture','puestos':['account'],'estado':'activo','activo':True}
        self.other={'id':'other-fixture','nombre':'Other fixture','alias':'Fixture2','puestos':['account'],'estado':'activo','activo':True}
        self.c1={'id':'cid-own','nombre':'Own fixture','estado':'activo','activo':True,'activo_confirmado':True}
        self.c2={'id':'cid-other','nombre':'Other fixture','estado':'activo','activo':True,'activo_confirmado':True}
        self.raw={'personas':[self.actor,self.other],'clientes':[self.c1,self.c2],
          'asignaciones':[{'cliente_id':'cid-own','persona_id':self.actor['id'],'silla':'account','principal':True,'confianza':'confirmada'},
                          {'cliente_id':'cid-other','persona_id':self.other['id'],'silla':'account','principal':True,'confianza':'confirmada'}],
          'logos':{},'alarmas':[],'meta':{}}
        self.e=types.SimpleNamespace(crudo=self.raw,modulos=copy.deepcopy(P.cargar_modulos()))
        estado=Path(self.t.name)/'estado.json';estado.write_text(json.dumps({'activos':[{'id':c['id'],'tipo':next(iter(ACT.TIPOS_ACTIVOS))} for c in self.raw['clientes']],'bajas_ids':[],'bajas':[],'dudosos':[]}))
        self.patches=[patch.object(ACT,'ESTADO',estado),patch.object(ACT,'_CACHE',{'marca':None,'estado':None})]
        for p in self.patches:p.start()
        self.ns={'P':P,'E':self.e,'ACT':ACT,'re':re,'json':json,'os':os,'DATA':self.data,'NUCLEO':['personas','asignaciones'],
          'registrar_agrupado':lambda *a,**k:None,'leer_json_bueno':lambda p:(json.loads(p.read_text()),None),
          '_estado_fichero':lambda _:None,'version_datos':lambda:1,'DatoRoto':type('DatoRoto',(Exception,),{}),'DatoSecreto':type('DatoSecreto',(Exception,),{})}
        funciones(self.ns);self.h=types.SimpleNamespace(responder=lambda c,d:(c,d))
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.t.cleanup()
    def write(self,rel,d):
        p=self.data/(rel+'.json');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d))
    def get(self,ruta,real=None,vista=None):
        r=real or self.actor;p=vista or r
        with P.mirando_como(r,self.raw):
            return self.ns['endpoint'](self.h,ruta,{},r,p,P.contexto(p,self.raw),r['id']!=p['id'])
    def test_repro_raiz_cliente_ajeno_conservada_endpoint_modulo(self):
        doc={'cliente_id':'cid-other','resumen':{'sesiones':7},'filas':[{'cliente_id':'cid-other','sesiones':7}]}
        self.write('paneles/ga4/cid-other',doc)
        self.assertFalse(P.ver(self.actor,{'tipo':'cliente_detalle','cliente_id':'cid-other'},P.contexto(self.actor,self.raw))['ok'])
        code,d=self.get('/api/modulo/paneles/ga4/cid-other')
        self.assertEqual(code,200);self.assertEqual(d['resumen']['sesiones'],7)
        self.assertEqual(d['cliente_id'],'cid-other');self.assertEqual(d['filas'],[])
    def test_control_api_cliente_ajeno_si_denegado(self):
        self.write('clientes/cid-other',{'fuentes':{'gsc':{'observado':7}}})
        self.assertEqual(self.get('/api/cliente/cid-other')[0],403)
    def test_repro_patron_cruza_segmentos_y_solo_propio_no_basta(self):
        rel='chat_equipo/p_other/extra/p_owner-fixture'
        self.assertIsNotNone(self.ns['entrada_datos_modulo'](rel))
        self.write(rel,{'mensajes':[],'marca_fixture':True})
        code,d=self.get('/api/modulo/'+rel)
        self.assertEqual(code,200);self.assertTrue(d['marca_fixture'])
    def test_control_documento_personal_propio_y_vercomo(self):
        self.write('chat_equipo/p_owner-fixture',{'persona_id':self.actor['id'],'mensajes':[],'marca_fixture':True})
        self.assertEqual(self.get('/api/modulo/chat_equipo/p_owner-fixture')[0],200)
        self.assertEqual(self.get('/api/modulo/chat_equipo/p_owner-fixture',real=self.other,vista=self.actor)[0],403)
    def test_repro_nivel_ficha_ninguno_no_es_puerta(self):
        self.e.modulos['ficha']['account']=None
        self.write('clientes/cid-own',{'fuentes':{'gsc':{'observado':7}}})
        self.assertIsNone(self.ns['ve_alguno'](self.actor,['ficha']))
        code,d=self.get('/api/cliente/cid-own')
        self.assertEqual(code,200);self.assertEqual(d['fuentes']['fuentes']['gsc']['observado'],7)
    def test_repro_resumen_produccion_no_limita_fuentes(self):
        self.actor['puestos']=['produccion'];self.raw['asignaciones'][0]['silla']='produccion'
        self.write('clientes/cid-own',{'fuentes':{'gsc':{'observado':7},'tareas':{'marca_fixture':True}}})
        self.assertEqual(self.ns['ve_alguno'](self.actor,['ficha']),'resumen')
        code,d=self.get('/api/cliente/cid-own')
        self.assertEqual(code,200);self.assertEqual(d['fuentes']['fuentes']['gsc']['observado'],7)
        self.assertTrue(d['fuentes']['fuentes']['tareas']['marca_fixture'])
    def test_control_administracion_contrato_se_preserva(self):
        self.actor['puestos']=['administracion']
        self.write('clientes/cid-own',{'fuentes':{'gsc':{'observado':7},'libro':{'contrato':{'marca_fixture':True}}}})
        self.assertEqual(self.ns['ve_alguno'](self.actor,['ficha']),'resumen')
        code,d=self.get('/api/cliente/cid-own');self.assertEqual(code,200)
        self.assertNotIn('gsc',d['fuentes']['fuentes']);self.assertTrue(d['fuentes']['fuentes']['libro']['contrato']['marca_fixture'])
    def test_control_interseccion_real_vista_modulo_raiz(self):
        self.write('paneles/ga4/cid-own',{'cliente_id':'cid-own','resumen':{'sesiones':7},'filas':[{'cliente_id':'cid-own','sesiones':7}]})
        code,d=self.get('/api/modulo/paneles/ga4/cid-own',real=self.other,vista=self.actor)
        self.assertEqual(code,200);self.assertEqual(d['filas'],[])
        self.assertEqual(d['resumen']['sesiones'],7,'repro raíz conserva valores pese intersección')

if __name__=='__main__':unittest.main()
