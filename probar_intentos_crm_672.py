"""AST de funciones reales; transporte sólo ficticio. Nunca importa productor."""
import ast
from collections import Counter
from copy import deepcopy
import datetime as dt
import math
import json
import hashlib
from pathlib import Path
import re
import unittest
from zoneinfo import ZoneInfo

HERE=Path(__file__).resolve().parent
APP=HERE
BASE=HERE/'fixture_intentos_crm_672.py'
CANDIDATO=APP/'fuentes_crm/generar_crm.py'
NOW=dt.datetime(2026,10,4,12,tzinfo=ZoneInfo('Europe/Madrid'))
CREADO=int(dt.datetime(2026,9,30,12,tzinfo=ZoneInfo('Europe/Madrid')).timestamp()*1000)

def cargar(p):
    tree=ast.parse(p.read_text());names={'inicio_dia','iso_ms','timestamp_mensaje','resumir_intentos','intentos_medidos672','clasificar','leer_subcuenta','fecha_mensaje676','normalizar_mensajes676','conflictos_globales676','canal_observado676','respuesta_publica676','sin_tocar_publico676'}
    ns={'dt':dt,'math':math,'re':re,'json':json,'HOY':NOW,'MAD':ZoneInfo('Europe/Madrid'),'AHORA_MS':int(NOW.timestamp()*1000),'VENTANA_LEADS':30,'EXCLUSIONES':{}}
    assignments={'MEDIOS_LEAD','MEDIOS_NO','RX_PRUEBA','RX_NO_LEAD','RX_LANDING','RX_CORREO_PRUEBA','COMUNICACION','AUTOMATICO'}
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assignments for t in n.targets)]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<productorAST>','exec'),ns)
    # Compila la rama REAL exacta de main, no una reproducción aproximada.
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    branch=next(n for n in ast.walk(main) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='sin_tocar' for t in n.targets))
    ns['sin_tocar_ast']=compile(ast.Module(body=[branch],type_ignores=[]),'<ramaSinTocarAST>','exec')
    return ns

class Transporte:
    def __init__(self,mensajes=None,cv=None,msgerror=False):self.mensajes=mensajes or [];self.cv=cv;self.msgerror=msgerror;self.calls=[]
    def req(self,loc,method,ruta,*args,**kwargs):
        self.calls.append((method,ruta));assert loc=='sidFixture'
        if ruta=='/contacts/search':
            if args and args[0].get('pageLimit')==1:return {'total':10}
            return {'contacts':[{'id':'contactFixture','dateAdded':CREADO,'attributionSource':{'medium':'form'}}]}
        if ruta=='/calendars/':return {'calendars':[]}
        if ruta=='/conversations/search':return deepcopy(self.cv) if self.cv is not None else {'conversations':[{'id':'conversationFixture','contactId':'contactFixture'}]}
        if ruta=='/conversations/conversationFixture/messages':return {'_error':'fallo_sintetico'} if self.msgerror else {'messages':{'messages':deepcopy(self.mensajes)}}
        if ruta=='/opportunities/pipelines':return {'pipelines':[]}
        if ruta=='/opportunities/search':return {'opportunities':[]}
        if ruta=='/workflows/':return {'workflows':[]}
        raise AssertionError('ruta fuera de transporte falso')

def msg(fecha):return {'id':'msg'+hashlib.sha256(repr(fecha).encode()).hexdigest()[:16],'contactId':'contactFixture','dateAdded':fecha,'messageType':'TYPE_EMAIL','direction':'outbound','source':'app','status':'sent'}
def ejecutar(ns,t):
    lead=ns['leer_subcuenta'](t,'sidFixture')['leads'][0];scope={**ns,'auto':[lead],'hace24':ns['AHORA_MS']-86400000};exec(ns['sin_tocar_ast'],scope);return lead,scope['sin_tocar']

class Intentos672(unittest.TestCase):
    def setUp(self):self.old=cargar(BASE);self.new=cargar(CANDIDATO)
    def test_historico_previo_suprime_incidencia_baseline(self):
        a,old=ejecutar(self.old,Transporte([msg(CREADO-86400000)]));b,new=ejecutar(self.new,Transporte([msg(CREADO-86400000)]))
        self.assertEqual(a['intentos'],1);self.assertEqual(old,[]);self.assertIsNone(a['humano_min']);self.assertEqual(b['intentos'],0);self.assertEqual(len(new),1);self.assertFalse(b['intentos_medicion']['completa'])
        self.assertIn('sin intento observado en la copia parcial de GHL',CANDIDATO.read_text())
    def test_reciente_no_suma_historico(self):
        msgs=[msg(CREADO-86400000),msg(CREADO+15*60000)];a,_=ejecutar(self.old,Transporte(msgs));b,new=ejecutar(self.new,Transporte(msgs));self.assertEqual(a['intentos'],2);self.assertEqual(b['intentos'],1);self.assertEqual(b['humano_min'],15);self.assertEqual(b['intentos_72h'],1);self.assertEqual(new,[])
    def test_error_conversacion_no_cero(self):
        a,old=ejecutar(self.old,Transporte(cv={'_error':'synthetic'}));b,new=ejecutar(self.new,Transporte(cv={'_error':'synthetic'}));self.assertEqual(a['intentos'],0);self.assertEqual(len(old),1);self.assertIsNone(b['intentos']);self.assertEqual(new,[])
    def test_error_messages_no_cero(self):
        a,old=ejecutar(self.old,Transporte(msgerror=True));b,new=ejecutar(self.new,Transporte(msgerror=True));self.assertEqual(a['intentos'],0);self.assertEqual(len(old),1);self.assertIsNone(b['intentos']);self.assertIsNone(b['intentos_72h']);self.assertEqual(new,[])
    def test_fecha_invalida_futura_no_contar(self):
        for stamp in (None,'no_fecha',self.new['AHORA_MS']+60000,float('nan')):
            b,new=ejecutar(self.new,Transporte([msg(stamp)]));self.assertIsNone(b['intentos']);self.assertIsNone(b['humano_min']);self.assertEqual(new,[])
    def test_vacio_explicito_parcial(self):
        b,new=ejecutar(self.new,Transporte(cv={'conversations':[]}));self.assertEqual(b['intentos'],0);self.assertEqual(b['intentos_medicion']['estado'],'observado_parcial');self.assertFalse(b['intentos_medicion']['completa']);self.assertEqual(len(new),1)
    def test_shape_collection_no_observacion(self):
        for cv in ({},{'conversations':['bad']},{'conversations':False}):
            b,new=ejecutar(self.new,Transporte(cv=cv));self.assertIsNone(b['intentos']);self.assertEqual(new,[])
    def test_despues72h_es_intento_no_cuatro(self):
        b,new=ejecutar(self.new,Transporte([msg(CREADO+73*3600000)]));self.assertEqual(b['intentos'],1);self.assertEqual(b['intentos_72h'],0);self.assertEqual(new,[])
    def test_auto_no_contacto_humano(self):
        m=msg(CREADO+60000);m['source']='workflow';b,new=ejecutar(self.new,Transporte([m]));self.assertEqual(b['intentos'],0);self.assertEqual(b['auto_min'],1);self.assertIsNone(b['humano_min'])
    def test_scalar_todos_desconocidos_no_cero(self):
        tree=ast.parse(CANDIDATO.read_text());expr=None
        for node in ast.walk(tree):
            if isinstance(node,ast.Dict):
                for k,v in zip(node.keys,node.values):
                    if isinstance(k,ast.Constant) and k.value=='sin_tocar_24h':expr=v
        code=compile(ast.Expression(expr),'<scalarRealAST>','eval')
        self.assertIsNone(eval(code,{**self.new,'v':True,'auto':[{'intentos':None}],'sin_tocar':[]}));row,_=ejecutar(self.new,Transporte(cv={'conversations':[]}));self.assertEqual(eval(code,{**self.new,'v':True,'auto':[row],'sin_tocar':[{}]}),1)
    def test_media_no_unknown_cero_ni_excepcion(self):
        tree=ast.parse(CANDIDATO.read_text());expr=None
        for node in ast.walk(tree):
            if isinstance(node,ast.Dict):
                for k,v in zip(node.keys,node.values):
                    if isinstance(k,ast.Constant) and k.value=='intentos_medios':expr=v
        self.assertIsNotNone(expr);code=compile(ast.Expression(expr),'<mediaRealAST>','eval')
        self.assertIsNone(eval(code,{**self.new,'auto':[{'intentos':None}]}));row,_=ejecutar(self.new,Transporte([msg(CREADO+60000),msg(CREADO+120000)]));self.assertEqual(eval(code,{**self.new,'auto':[row,{'intentos':None}]}),2);row['intentos']=0;self.assertEqual(eval(code,{**self.new,'auto':[row]}),0)
    def test_cache_legacy_y_otrocorte_no_certificados(self):
        for n in (0,1):
            row={'creado':CREADO,'intentos':n,'cita':False};scope={**self.new,'auto':[row],'hace24':self.new['AHORA_MS']-86400000};exec(self.new['sin_tocar_ast'],scope);self.assertEqual(scope['sin_tocar'],[]);self.assertFalse(self.new['intentos_medidos672'](row));self.assertEqual(row['intentos'],n)
        row,_=ejecutar(self.new,Transporte(cv={'conversations':[]}));row['intentos_medicion']['hasta_ms']-=60000;self.assertFalse(self.new['intentos_medidos672'](row))
    def test_rama_unknown_bool_noausencia(self):
        for n in (None,False,True):
            scope={**self.new,'auto':[{'creado':CREADO,'intentos':n,'cita':False}],'hace24':self.new['AHORA_MS']-86400000};exec(self.new['sin_tocar_ast'],scope);self.assertEqual(scope['sin_tocar'],[])

if __name__=='__main__':unittest.main()
