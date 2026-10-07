"""Fixtures sintéticos. Generadores sólo AST; nunca imports, IO de fuentes ni proveedores."""
import ast
import copy
import datetime as dt
import textwrap
import unittest
from pathlib import Path
from fuentes_seo import posiciones as P
from fuentes_seo.seo_prioridades_fuentes import adaptar_fuentes
from fuentes_seo.seo_prioridades import evaluar_seo

APP=Path(__file__).parent
HOY=dt.date(2026,10,3)

def palabra(**kw):
    return {'k':'asesoria Ciudad','vol':10,'hoy':5,'sem':8,'mes':9,'ayer':None,'sem2':None,'mapa':2,'desde':'2026-01-01',
        'fechas':{'hoy':'2026-10-03','sem':'2026-09-26','mes':'2026-09-03','mapa':'2026-10-03'},**kw}

def motor(p):return {'site_engine_id':7,'principal':True,'palabras':p}

def solo_funciones(archivo,nombres,ns):
    tree=ast.parse((APP/'fuentes_seo'/archivo).read_text())
    body=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in nombres]
    assert len(body)==len(nombres)
    exec(compile(ast.Module(body=body,type_ignores=[]),archivo,'exec'),ns)
    return ns

def bloque_real(palabras):
    source=(APP/'fuentes_seo/generar_seo.py').read_text();a=source.index("                s={**s,'motores':");b=source.index('            else:\n                visib, reparto',a)
    ns={**{k:getattr(P,k) for k in ['preparar_motores','comparar','posicion','reparto_observado','top','suma_medida']},'s':{'motores':[motor(palabras)]},'DIA_SR':HOY,'dt':dt,'alertas':[],'fes':str,
        'CTR':{1:.30,2:.15,3:.10,4:.07,5:.05,6:.04,7:.03,8:.025,9:.02,10:.02}}
    solo_funciones('generar_seo.py',{'vis','pct'},ns)
    exec(compile(textwrap.dedent(source[a:b]),'bloque-generador-real','exec'),ns)
    return ns

class Posiciones169(unittest.TestCase):
    def test_nulos_y_no_numeros(self):
        for v in [None,0,-1,False,True,'99',1.5,float('nan'),float('inf')]:self.assertIsNone(P.posicion(v))
    def test_99_100_101_y_fuera_100_reales(self):
        for v in [99,100,101,205]:self.assertEqual(P.posicion(v),v)
        self.assertIsNone(P.posicion(101,centinela=101));self.assertIsNone(P.posicion(99,estado='sin_dato'))
    def test_seleccion_exacta_no_recicla_ni_futuro(self):
        r=[{'date':'2026-10-02','pos':3},{'date':'2026-10-04','pos':1}]
        self.assertEqual(P.seleccionar(r,HOY),(None,None))
        self.assertEqual(P.seleccionar(r,dt.date(2026,10,2)),(3,'2026-10-02'))
    def test_conflicto_y_replay_igual(self):
        r=[{'date':'2026-10-03','pos':3},{'date':'2026-10-03','pos':4}]
        self.assertEqual(P.seleccionar(r,HOY),(None,'2026-10-03'))
        r[1]['pos']=3;self.assertEqual(P.seleccionar(r,HOY),(3,'2026-10-03'))
    def test_fecha_malformada_y_sentinel(self):
        self.assertEqual(P.seleccionar([{'date':'2026-02-30','pos':1}],HOY),(None,None))
        self.assertEqual(P.seleccionar([{'date':'2026-10-03','pos':101,'pos_centinela':101}],HOY),(None,'2026-10-03'))
    def test_mejor_dos_solo_fechas_consecutivas(self):
        raw=palabra(ayer=2,fechas={'hoy':'2026-10-03','ayer':'2026-10-02','sem':'2026-09-26'})
        backup=copy.deepcopy(raw);p=P.preparar_motores([motor([raw])],HOY)[0]['palabras'][0]
        self.assertEqual(p['hoy'],2);self.assertEqual(p['fechas']['hoy'],'2026-10-02');self.assertIsNone(P.comparar(p));self.assertEqual(raw,backup)
        raw['fechas']['ayer']='2026-10-01';self.assertEqual(P.preparar_motores([motor([raw])])[0]['palabras'][0]['hoy'],5)
    def test_comparacion_estricta(self):
        p=P.preparar_motores([motor([palabra()])])[0]['palabras'][0];self.assertEqual(P.comparar(p),3)
        p['motor_id']=None;self.assertIsNone(P.comparar(p));p['motor_id']=7;p['fechas']['sem']=None;self.assertIsNone(P.comparar(p))
    def test_future_y_legacy_nullable(self):
        p=P.preparar_motores([motor([palabra(fechas={'hoy':'2026-10-04'})])],HOY)[0]['palabras'][0];self.assertIsNone(p['hoy'])
        p=P.preparar_motores([motor([palabra(fechas={},ultima='2026-10-02')])])[0]['palabras'][0];self.assertEqual(p['hoy'],5);self.assertIsNone(P.comparar(p));self.assertIsNone(p['fechas']['mapa'])
    def test_reparto_ausente_no_fuera_top(self):
        r=P.reparto_observado([palabra(hoy=None,mes=None)]);self.assertIsNone(r['fuera']['hoy']);self.assertEqual(r['sin_dato']['hoy'],1);self.assertIsNone(r['top5']['hoy'])
        r=P.reparto_observado([palabra(hoy=101,mes=100)]);self.assertEqual(r['fuera']['hoy'],1);self.assertEqual(r['top5']['hoy'],0)
    def test_reparto_no_mezcla_cohortes(self):
        rows=P.preparar_motores([motor([palabra(),palabra(fechas={})])])[0]['palabras'];r=P.reparto_observado(rows);self.assertEqual(r['top5']['hoy'],2);self.assertIsNone(r['top5']['mes']);self.assertEqual(r['top5']['comparables'],1)
    def test_sumatoria_ausencia(self):
        self.assertIsNone(P.suma_medida([None,None]));self.assertEqual(P.suma_medida([None,0]),0)
    def test_sr_leer_funciones_reales(self):
        ns=solo_funciones('sr_leer.py',{'pos_en','dia_completo','condensar'},{'seleccionar':P.seleccionar,'posicion':P.posicion,'fecha':P.fecha,'dt':dt,'Counter':__import__('collections').Counter})
        out=ns['condensar']('fixture',1,[{'site_engine_id':7,'keywords':[{'name':'k','positions':[{'date':'2026-10-03','pos':101,'map_position':2},{'date':'2026-09-25','pos':3}]}]}],HOY)
        row=out['motores'][0]['palabras'][0];self.assertEqual(row['hoy'],101);self.assertIsNone(row['sem']);self.assertEqual(row['fechas']['mapa'],'2026-10-03')
    def test_sr_condensar_funcion_real(self):
        ns=solo_funciones('sr_condensar.py',{'pos_en'},{'seleccionar':P.seleccionar})
        self.assertEqual(ns['pos_en']([{'date':'2026-10-02','pos':99}],HOY),(None,None))
    def test_generador_real_nulos_no_mov_ni_visibilidad_cero(self):
        r=bloque_real([palabra(hoy=None,mapa=None)]);self.assertEqual(r['movimientos']['n_bajan'],0);self.assertEqual(r['movimientos']['n_suben'],0);self.assertIsNone(r['visib']['hoy']);self.assertIsNone(r['visib']['var']);self.assertIsNone(r['reparto']['fuera']['hoy'])
    def test_generador_real_rank_y_legacy(self):
        r=bloque_real([palabra(hoy=101,sem=99)]);self.assertEqual(r['movimientos']['bajan'][0]['delta'],-2);self.assertEqual(r['reparto']['fuera']['hoy'],1)
        r=bloque_real([palabra(fechas={})]);self.assertEqual(r['movimientos']['n_suben'],0);self.assertIsNone(r['visib']['var']);self.assertEqual(r['informe'][0]['hoy'],5)
    def test_adapter_maps_no_fecha_organica_heredada(self):
        ctx={'cliente_id':'fixture','servicio_seo_confirmado':True,'fuente_servicio':'Fixture','ciudades_verificadas':[{'ciudad':'Ciudad','fuente':'Fixture'}],'servicios_reales':['asesoria']}
        d=adaptar_fuentes(ctx,{'clientes':{'fixture':{'proyecto':1,'motores':[motor([palabra(fechas={},ultima='2026-10-03')])]}}},{})
        org=next(x for x in d['rankings'] if x['canal']=='organico');maps=next(x for x in d['rankings'] if x['canal']=='maps')
        self.assertEqual(org['fecha'],'2026-10-03');self.assertIsNone(maps['fecha']);self.assertIsNone(maps['ubicacion_medicion'])
    def test_engine_conflictos_misma_fecha_y_ranking_fraccion(self):
        ctx={'cliente_id':'fixture','servicio_seo_confirmado':True,'fuente_servicio':'Fixture','ciudades_verificadas':[{'ciudad':'Ciudad','fuente':'Fixture'}],'servicios_reales':['asesoria']}
        base={'consulta':'asesoria Ciudad','ciudad':'Ciudad','canal':'organico','fecha':'2026-10-03','fuente':'Fixture','medicion_id':'7','dispositivo':'desktop','ubicacion_medicion':'Ciudad'}
        for rows in [[{**base,'posicion':3},{**base,'posicion':4}],[{**base,'posicion':1.5}]]:
            out=evaluar_seo(ctx,{'rankings':rows},'2026-10-03');self.assertTrue(all(x['posicion'] is None for x in out['objetivos']))

if __name__=='__main__':unittest.main()
