"""Cruce adversarial de controladores reales con fixtures sintéticos; sin servidor/red/BD real."""
import ast
import json
import os
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import cerebro_api
import borradores_api
import piloto_lectura

ROOT = Path(__file__).parent

def funciones_reales(nombres, espacio):
    arbol = ast.parse((ROOT/'servir.py').read_text())
    funciones = [n for n in arbol.body if isinstance(n, ast.FunctionDef) and n.name in nombres]
    handler = next(n for n in arbol.body if isinstance(n,ast.ClassDef) and n.name=='Manejador')
    funciones += [n for n in handler.body if isinstance(n,ast.FunctionDef) and n.name in nombres]
    assert {n.name for n in funciones} == set(nombres)
    exec(compile(ast.Module(body=funciones,type_ignores=[]), 'servir_fixture_ast', 'exec'), espacio)

class Controlador:
    def responder(self,cuerpo_codigo,cuerpo):return cuerpo_codigo,cuerpo
    def _api_get(self,*args):return 404,{'error':'No existe.'}
    def api_post(self,*args):raise AssertionError('No ejecutar escrituras')

class Ambito105(unittest.TestCase):
    def test_access_real_no_se_suplanta_con_query_cabecera_o_cookie(self):
        real={'id':'cuenta_real','estado':'activo'}
        esp={'ACCESO':SimpleNamespace(activo=lambda:True,correo_validado=lambda h:('owner@fixture.test',None)),
             'E':SimpleNamespace(por_correo=lambda c:real,persona=lambda cid:{'id':cid,'estado':'activo'},crudo={}),
             'P':SimpleNamespace(contexto=lambda *a:{},ver=lambda *a:{'ok':False})}
        funciones_reales({'_quien'},esp)
        h=SimpleNamespace(headers={'X-RO-Yo':'direccion','Cf-Access-Authenticated-User-Email':'fake@fixture.test'},galletas=lambda:{'ro_yo':'direccion'})
        r,v,error=esp['_quien'](h,{'yo':['direccion']})
        self.assertIs(r,real);self.assertIs(v,real);self.assertIsNone(error)
        self.assertEqual(esp['_quien'](h,{'yo':['direccion'],'como':['direccion']})[2][0],403)
        esp['ACCESO'].correo_validado=lambda h:(None,'Sin sello válido')
        self.assertEqual(esp['_quien'](h,{'yo':['direccion']})[2][0],403)

    def test_api_get_activa_interseccion_tambien_para_cerebro_y_borrador(self):
        from contextlib import contextmanager
        vistos=[]
        @contextmanager
        def mirando(real,crudo):
            vistos.append('entra');yield;vistos.append('sale')
        esp={'P':SimpleNamespace(mirando_como=mirando),'E':SimpleNamespace(crudo={}),
             'apuntar_lectura_ver_como':lambda *a:vistos.append('rastro')}
        funciones_reales({'api_get'},esp)
        h=SimpleNamespace(quien=lambda q:({'id':'r'},{'id':'v'},None),
            _api_get=lambda *a:vistos.append('controlador') or 'ok')
        for ruta in ('/api/cerebro/operativo','/api/cerebro/borrador'):
            vistos.clear();self.assertEqual(esp['api_get'](h,ruta,{}),'ok')
            self.assertEqual(vistos,['entra','controlador','sale'])

    def sistema(self):
        self.lecturas=[]
        clientes=[{'id':'comun','nombre':'Común fixture'},{'id':'solo_real','nombre':'NO EXPORTAR REAL'},
                  {'id':'solo_vista','nombre':'NO EXPORTAR VISTA'}]
        def recortado(real,vista,cp,rel):
            self.lecturas.append((real['id'],vista['id'],rel))
            return {'clientes':[{'cliente_id':cid} for cid in sorted(set(real['clientes']) & set(vista['clientes']))]}
        S=SimpleNamespace(E=SimpleNamespace(nucleo_bloqueado=False,crudo={'clientes':clientes}),
            P=SimpleNamespace(contexto=lambda p,c:{},hoy_iso=lambda:'2026-10-03',
                ver=lambda p,d,c:{'ok':d['cliente_id'] in p['clientes']}),
            ACT=SimpleNamespace(es_baja_id=lambda c:False),
            ve_alguno=lambda p,ms:bool(set(p['modulos'])&set(ms)),
            entrada_datos_modulo=lambda rel:{'modulos':[{'captacion':'captacion','crm':'crm','objetivos':'objetivos'}[rel.split('/')[0]]]},
            modulo_recortado=recortado)
        r={'id':'real','clientes':['comun','solo_real'],'modulos':['prioridades-cliente','captacion','crm']}
        v={'id':'vista','clientes':['comun','solo_vista'],'modulos':['prioridades-cliente','crm']}
        return S,r,v

    def test_fuentes_no_cambian_ambito_por_yo_como_query_y_area(self):
        S,r,v=self.sistema()
        class H(Controlador):pass
        cerebro_api.enganchar(H,S);piloto_lectura.enganchar(H)
        def motor(paid,crm,objetivos,**kw):
            self.assertIsNone(paid);self.assertIsNone(objetivos)
            return {'recomendaciones':[{'cliente_id':c['cliente_id'],'area':'crm'} for c in crm['clientes']]}
        with patch.dict(os.environ,{'RO_PILOTO_LECTURA':'1'}),patch('cerebro_operativo.generar',side_effect=motor):
            code,out=H()._api_get('/api/cerebro/operativo',{'yo':['direccion'],'como':['direccion'],'area':['crm']},r,v)
        self.assertEqual(code,200);self.assertEqual(out['recomendaciones'],[{'cliente_id':'comun','area':'crm'}])
        self.assertEqual(self.lecturas,[('real','vista','crm/crm')])

    def test_borrador_no_resuelve_cliente_fuera_interseccion_ni_enumeracion(self):
        S,r,v=self.sistema()
        class H(Controlador):pass
        borradores_api.enganchar(H,S);piloto_lectura.enganchar(H)
        with patch.dict(os.environ,{'RO_PILOTO_LECTURA':'1'}),patch.object(borradores_api,'resolver') as resolver:
            respuestas=[H()._api_get('/api/cerebro/borrador',{'cliente_id':[cid],'regla_id':['fixture']},r,v)
                        for cid in ('solo_real','solo_vista','inexistente')]
        self.assertTrue(all(x==respuestas[0] for x in respuestas));self.assertEqual(respuestas[0][0],404)
        resolver.assert_not_called();self.assertEqual(self.lecturas,[])

    def test_borrador_cruza_recortado_rechaza_regla_inyectada_y_limpia_contexto(self):
        S,r,v=self.sistema()
        class H(Controlador):pass
        borradores_api.enganchar(H,S);piloto_lectura.enganchar(H)
        reco={'cliente_id':'comun','regla_id':'fixture','titulo':'Revisar CRM','accion':'Verificar resultado',
            'criterio_entrega':'Anotar próximo paso','motivo':'Fuente parcial',
            'evidencias':[{'fuente':'CRM fixture','fecha':'2026-10-03','texto':'dato@fixture.test y 1470 €'}],
            'secreto':'NO EXPORTAR PRIVADO'}
        with patch.dict(os.environ,{'RO_PILOTO_LECTURA':'1'}),patch.object(borradores_api,'generar_operativo',return_value={'recomendaciones':[reco]}),patch.object(borradores_api.metodo_cuentas,'estado_operativo',return_value={'sugerencias':[]}):
            code,out=H()._api_get('/api/cerebro/borrador',{'cliente_id':['comun'],'regla_id':['fixture']},r,v)
            self.assertEqual(code,200);self.assertFalse(out['enviable']);self.assertIsNone(out['lista_id'])
            serial=json.dumps(out);self.assertNotIn('dato@fixture.test',serial);self.assertNotIn('1470',serial);self.assertNotIn('NO EXPORTAR',serial)
            self.assertEqual(self.lecturas,[('real','vista','crm/crm')])
            self.lecturas.clear()
            for q in ({'cliente_id':['comun'],'regla_id':['fixture'],'lista_id':['999']},
                      {'cliente_id':['comun','solo_real'],'regla_id':['fixture']},
                      {'cliente_id':['comun'],'regla_id':['fixture'],'accion':['escribir']}):
                self.assertEqual(H()._api_get('/api/cerebro/borrador',q,r,v)[0],400)
            self.assertEqual(self.lecturas,[])

    def test_allowlist_piloto_delega_a_puerta_real_usuarios_empresa_y_fuentes(self):
        # Actual base GET + actual puerta_modulo from servir.py, using only a temporary synthetic source.
        with tempfile.TemporaryDirectory() as tmp:
            data=Path(tmp)
            fuentes={'paneles/empresa/desk':{'puestos':['direccion']},
                     'paneles/meta/comun':{'modulos':['paneles']},
                     'personas_m20/equipo':{'modulos':['personas']}}
            for rel in fuentes:
                f=data/(rel+'.json');f.parent.mkdir(parents=True,exist_ok=True);f.write_text('{"filas":[]}')
            llamadas=[]
            esp={'re':re,'DATA':data,'NUCLEO':[], 'E':SimpleNamespace(nucleo_bloqueado=False,crudo={},bloqueados=[]),
                 'P':SimpleNamespace(contexto=lambda *a:{}), 'entrada_datos_modulo':fuentes.get,
                 've_alguno':lambda p,ms:'todo' if set(ms)&set(p['modulos']) else None,
                 'registrar_agrupado':lambda *a,**k:llamadas.append('denegado'),
                 '_estado_fichero':lambda p:None,'version_datos':lambda:1,
                 'leer_json_bueno':lambda p:(json.loads(p.read_text()),None),
                 'recortar_modulo':lambda p,cp,doc,*a:doc, 'ACT':SimpleNamespace(quitar_bajas=lambda d,r:d),
                 'DatoRoto':ValueError}
            funciones_reales({'puerta_modulo','_api_get'},esp)
            class H(Controlador):pass
            H._api_get=esp['_api_get'];piloto_lectura.enganchar(H)
            r={'id':'real','puestos':['account'],'modulos':['paneles','personas']}
            v={'id':'vista','puestos':['direccion'],'modulos':['paneles','personas']}
            with patch.dict(os.environ,{'RO_PILOTO_LECTURA':'1'}):
                self.assertEqual(H()._api_get('/api/modulo/personas_m20/equipo',{},v,v)[0],403) # Even director denied outside pilot.
                self.assertEqual(H()._api_get('/api/modulo/paneles/empresa/desk',{},r,v)[0],403) # Real lacks enterprise role.
                self.assertEqual(H()._api_get('/api/modulo/paneles/empresa/desk',{},v,v)[0],200)
                self.assertEqual(H()._api_get('/api/modulo/paneles/meta/comun',{},r,r)[0],200)
                r['modulos']=[]
                self.assertEqual(H()._api_get('/api/modulo/paneles/meta/comun',{},r,r)[0],403)
            self.assertEqual(llamadas,['denegado','denegado'])

if __name__=='__main__':unittest.main()
