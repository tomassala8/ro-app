"""Fixtures sintéticos. AST evita imports, main, red, llavero y escritura del generador."""
import ast
import importlib.util
import json
from pathlib import Path
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
import urllib.parse

APP = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('meta220', APP/'fuentes_paneles/meta_mediciones_220.py')
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
TREE = ast.parse((APP/'fuentes_paneles/generar_paneles.py').read_text())

class Reloj220(datetime):
    @classmethod
    def now(cls, tz=None):
        fijo = datetime(2026, 10, 3, 8, 0, tzinfo=timezone.utc)
        return fijo.astimezone(tz) if tz else fijo.replace(tzinfo=None)

def functions(names, extras=None):
    ns = {'META220':M, 'datetime':Reloj220, 'date':date, 'timedelta':timedelta, 'json':json, 'AHORA':'2026-10-03 10:00', 'HOY':date(2026,10,3),
          'DESDE_SERIE':'2026-10-03', 'PERIODOS':[{'desde':'2026-10-01','hasta':'2026-10-02','anterior':['2026-09-29','2026-09-30']}],
          'C':SimpleNamespace(sanear=lambda s:s), 'urllib':SimpleNamespace(parse=urllib.parse)}
    ns.update(extras or {})
    exec(compile(ast.Module(body=[n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'generador_AST_220','exec'),ns)
    return ns

class Pruebas220(unittest.TestCase):
    def test_contexto297_solo_productor_no_payload(self):
        payload={'account_id':'999','currency':'USD','spend':'10','actions':[{'action_type':'lead','value':'2'}],'date_start':'2026-10-01','date_stop':'2026-10-02'}
        m=M.fila(payload,'2026-10-03','account',cuenta='act_123',moneda='EUR')['medicion']
        self.assertEqual((m['cuenta_id'],m['moneda']),('123','EUR'))
        self.assertIsNone(M.fila(payload,'2026-10-03','account')['medicion']['cuenta_id'])
    def test_contexto297_invalidos_no_identidad(self):
        for v in (True,123,'','act_','0123',' 123','act_act_123','1e3',{},'9'*31):
            self.assertIsNone(M.contexto_cuenta(v,'EUR')['cuenta_id'])
        for v in (True,123,'eur',' EUR','EURO',None,{}):
            self.assertIsNone(M.contexto_cuenta('123',v)['moneda'])
    def test_contexto297_legacy_no_rellena_descriptor(self):
        raw={'cuenta':'act_123','moneda':'EUR','leido':'2026-09-01','periodos':{'x':{'cuenta':{'gasto':10,'leads':2}}}}
        row=M.proyectar_cache(raw)['periodos']['x']['cuenta']
        self.assertEqual(row['medicion']['fuente'],'cache_legacy')
        self.assertNotIn('cuenta_id',row['medicion']);self.assertNotIn('moneda',row['medicion'])
        self.assertNotIn('medicion',raw['periodos']['x']['cuenta'])
    def test_contexto297_productor_ast_propaga_info(self):
        def paginate(tk,path,**q):
            if not path.endswith('/insights') or 'time_increment' in q:return [],None
            return [{'date_start':'2026-10-01','date_stop':'2026-10-02','campaign_id':'a','adset_id':'b','ad_id':'c','spend':'10','actions':[{'action_type':'lead','value':'2'}],'account_id':'999','currency':'USD'}],None
        ns=functions({'meta_leer'},{'get_json':lambda url:{'account_status':1,'currency':'EUR'},'meta_paginar':paginate})
        out=ns['meta_leer']('fixture',{'meta':'act_123'})
        proj=M.proyectar_cache(out)
        self.assertEqual(proj['moneda'],'EUR')
        for nivel in ('cuenta','campaign','adset','ad'):
            rows=proj['periodos']['2026-10-01|2026-10-02'][nivel]
            row=rows if nivel=='cuenta' else next(iter(rows.values()))
            self.assertEqual((row['medicion']['cuenta_id'],row['medicion']['moneda']),('123','EUR'))

    def test_cero_api_explicito(self):
        self.assertEqual(M.numero('0',True),0)
        self.assertEqual(M.leads([{'action_type':'lead','value':'0'}]),(0,'lead'))
    def test_invalidos_enteros(self):
        for v in (None,False,True,'', 'nan','Infinity','-1','0.5',2**53,' 0',{}):
            self.assertIsNone(M.numero(v,True))
    def test_decimal_gasto_sin_truncar(self):
        self.assertEqual(M.numero('0.004'),0.004)
    def test_leads_ausentes_no_cero(self):
        for v in (None,[],{},[{'action_type':'click','value':'5'}],[None]):
            self.assertIsNone(M.leads(v)[0])
    def test_lead_reconocido_invalido_no_fallback(self):
        self.assertIsNone(M.leads([{'action_type':'lead','value':'x'},{'action_type':'onsite_web_lead','value':'9'}])[0])
    def test_no_sumar_variantes_solapadas(self):
        self.assertEqual(M.leads([{'action_type':'lead','value':'2'},{'action_type':'onsite_web_lead','value':'2'}])[0],2)
    def test_prioridad_cero_no_cambia_a_otra_variante(self):
        self.assertEqual(M.leads([{'action_type':'lead','value':'0'},{'action_type':'onsite_web_lead','value':'2'}])[0],0)
    def test_duplicado_discordante_no_ultimo(self):
        self.assertIsNone(M.leads([{'action_type':'lead','value':'1'},{'action_type':'lead','value':'2'}])[0])
    def test_replay_identico_no_doble_lead(self):
        self.assertEqual(M.leads([{'action_type':'lead','value':'2'}]*2)[0],2)
    def test_fila_observaciones_y_no_pii(self):
        row=M.fila({'spend':'0','impressions':'0','actions':[{'action_type':'lead','value':'0'}], 'date_start':'2026-10-01','date_stop':'2026-10-02','email':'privado','token':'privado'},'2026-10-03','account')
        self.assertEqual(row['leads'],0);self.assertIn('leads',row['medicion']['campos_observados'])
        self.assertIsNone(row['clics']);self.assertNotIn('privado',json.dumps(row));self.assertEqual(row['medicion']['desde'],'2026-10-01')
    def test_fechas_invalidas_y_revertidas_no_medicion(self):
        for a,b in [('2026-02-31','2026-03-02'),('2026-10-03','2026-10-02')]:
            row=M.fila({'impressions':'2','date_start':a,'date_stop':b},'2026-10-03','account')
            self.assertIsNone(row['impresiones']);self.assertFalse(row['medicion']['periodo_valido'])
    def test_legacy_cero_desconocido_fecha_no_revive(self):
        raw={'leido':'2026-09-01','gasto_serie':{'a':{'2026-09-01':[0,2,0,0,0]}},'periodos':{'x':{'cuenta':{'leads':0,'gasto':10}}}}
        out=M.preparar_cache(raw)
        self.assertIsNone(out['periodos']['x']['cuenta']['leads']);self.assertEqual(out['periodos']['x']['cuenta']['gasto'],10)
        self.assertEqual(out['medicion_meta']['fecha_lectura'],'2026-09-01');self.assertTrue(out['errores'])
        self.assertEqual(raw['periodos']['x']['cuenta']['leads'],0)
    def test_nuevo_cache_conserva_cero(self):
        raw={'medicion_meta':M.descriptor('2026-10-03'),'gasto_serie':{'a':{'x':[0,0,0,0,0]}}}
        self.assertEqual(M.preparar_cache(raw),raw)
    def test_cache_legacy_malformado_no_crash(self):
        out=M.preparar_cache({'gasto_serie':[],'periodos':[]})
        self.assertEqual(out['periodos'],{});self.assertTrue(out['errores'])
    def test_paginas_truncadas_no_exito_silencioso(self):
        ns=functions({'meta_paginar'},{'get_json':lambda url:{'data':[],'paging':{'next':'https://example.invalid'}}})
        data,error=ns['meta_paginar']('fixture','/insights');self.assertEqual(data,[]);self.assertEqual(error,'paginacion_incompleta')
    def test_productor_real_puro_ast_preserva_missing(self):
        def paginate(tk,path,**q):
            if not path.endswith('/insights'):return [],None
            if 'time_increment' in q:
                return [{'campaign_id':'a','date_start':'2026-10-03','date_stop':'2026-10-03','impressions':'0','actions':[{'action_type':'lead','value':'0'}]}],None
            row={'date_start':'2026-10-01','date_stop':'2026-10-02','spend':'1.5','impressions':'0','campaign_id':'a','adset_id':'b','ad_id':'c'}
            return [row],None
        ns=functions({'meta_leer'},{'get_json':lambda url:{'account_status':1,'currency':'EUR'},'meta_paginar':paginate})
        out=ns['meta_leer']('fixture',{'meta':'fixture'})
        self.assertEqual(out['gasto_serie']['a']['2026-10-03'],[None,0,None,None,0])
        row=out['periodos']['2026-10-01|2026-10-02']['cuenta'];self.assertIsNone(row['leads']);self.assertEqual(row['gasto'],1.5)
        self.assertEqual(out['medicion_meta']['observacion_campos'],'presencia_validada')
    def test_productor_duplicate_y_periodo_fuera_rango(self):
        def paginate(tk,path,**q):
            if not path.endswith('/insights'):return [],None
            row={'campaign_id':'a','adset_id':'b','ad_id':'c','date_start':'2026-10-01','date_stop':'2026-10-02','impressions':'1'}
            return [row,{**row,'impressions':'2'},{**row,'date_start':'2099-01-01','date_stop':'2099-01-02'}],None
        ns=functions({'meta_leer'},{'get_json':lambda url:{},'meta_paginar':paginate})
        out=ns['meta_leer']('fixture',{'meta':'fixture'})
        self.assertIsNone(out['periodos']['2026-10-01|2026-10-02']['cuenta']['impresiones'])
        self.assertNotIn('2099-01-01|2099-01-02',out['periodos']);self.assertTrue(out['errores'])
    def test_diario_fuera_rango_no_actual(self):
        def paginate(tk,path,**q):
            if 'time_increment' not in q:return [],None
            return [{'campaign_id':'a','date_start':'2099-01-01','date_stop':'2099-01-01','impressions':'0'}],None
        ns=functions({'meta_leer'},{'get_json':lambda url:{},'meta_paginar':paginate})
        out=ns['meta_leer']('fixture',{'meta':'fixture'})
        self.assertEqual(out['gasto_serie'],{});self.assertTrue(out['errores'])
    def test_error_parcial_no_cero_ni_cobertura_total(self):
        def paginate(tk,path,**q):
            return [], 'fixture_error' if path.endswith('/insights') else None
        ns=functions({'meta_leer'},{'get_json':lambda url:{},'meta_paginar':paginate})
        out=ns['meta_leer']('fixture',{'meta':'fixture'})
        self.assertEqual(out['periodos'],{});self.assertEqual(out['gasto_serie'],{})
        self.assertTrue(out['errores']);self.assertEqual(out['medicion_meta']['cobertura'],'no_acreditada_completa')
    def test_preparar_legacy_idempotente(self):
        x=M.preparar_cache({'leido':'2026-09-01','gasto_serie':{'a':{'2026-09-01':[0,1,0,0,0]}}})
        self.assertEqual(M.preparar_cache(x),x)
    def test_proyeccion_meta_only_sin_payload_secreto(self):
        raw={'cuenta':'fixture', 'leido':'2026-09-01','gasto_serie':{'a':{'2026-09-01':[0,1,0,0,0]}}, 'secret':'NO_PUBLICAR','ga4':{'datos':'NO_PUBLICAR'}}
        out=M.proyectar_cache(raw)
        self.assertIsNone(out['serie']['a']['2026-09-01'][3]);self.assertIsNone(out['gasto_serie']['a']['2026-09-01'])
        self.assertNotIn('NO_PUBLICAR',json.dumps(out));self.assertEqual(out['leido'],'2026-09-01')
    def test_proyeccion_nueva_conserva_ceros_y_decimal(self):
        out=M.proyectar_cache({'medicion_meta':M.descriptor('2026-10-03'),'gasto_serie':{'a':{'2026-10-03':[0.004,0,0,0,0]}}})
        self.assertEqual(out['gasto_serie']['a']['2026-10-03'],0.004);self.assertEqual(out['serie']['a']['2026-10-03'],[0,0,0,0])
    def test_construir_real_ast_proyecta_solo_meta_y_conserva_fecha(self):
        captured=[];writes=[]
        raw={'leido':'2026-09-01','gasto_serie':{'a':{'2026-09-01':[0,0,0,0,0]}},'periodos':{}}
        ns=functions({'construir'},{'cache_leer':lambda fuente,cid:raw if fuente=='meta' else None,'escribir_fila':lambda fuente,c,f:captured.append((fuente,f)),
            'ENLACE':{'meta':lambda c:'#'},'nota_error':lambda x:None,'SALIDA':Path('/unused_fixture'), '_compacto':lambda *a:writes.append(a),'log':lambda *a:None})
        ns['construir']([{'id':'fixture','nombre':'fixture','meta':'fixture'}])
        self.assertEqual(len(captured),1);self.assertEqual(captured[0][0],'meta');self.assertIsNone(captured[0][1]['serie']['a']['2026-09-01'][3])
        self.assertEqual(captured[0][1]['leido'],'2026-09-01');self.assertEqual(captured[0][1]['medicion_meta']['origen'],'cache_legacy')

if __name__=='__main__':unittest.main()
