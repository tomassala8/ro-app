import unittest
import ast
from pathlib import Path
import datetime as dt
import math
from fuentes_crm.mediciones_cobertura import dto_medicion

# Funciones reales del generador extraídas sin imports con IO de configuración.
ruta=Path(__file__).parent/'fuentes_crm/generar_crm.py'
arbol=ast.parse(ruta.read_text())
funciones=[n for n in arbol.body if isinstance(n,ast.FunctionDef) and n.name in ('timestamp_mensaje','resumir_intentos')]
ns={'dt':dt,'math':math};exec(compile(ast.Module(body=funciones,type_ignores=[]),str(ruta),'exec'),ns)
resumir=ns['resumir_intentos']
class Pruebas(unittest.TestCase):
    def dto(self,v,**kw):return dto_medicion(v,fuente='GHL contactos',leida_el='2026-10-03',hoy='2026-10-03',**kw)
    def test_error_no_es_cero(self):
        d=self.dto(0,cobertura='completa',errores=True)
        self.assertIsNone(d['valor']);self.assertEqual(d['observado'],0);self.assertEqual(d['estado'],'desconocido')
    def test_parcial_y_legacy_no_completos(self):
        for c in ('parcial','desconocida'):
            d=self.dto(3,cobertura=c);self.assertEqual(d['observado'],3);self.assertIsNone(d['valor']);self.assertFalse(d['cobertura']['completa'])
    def test_cero_valido_solo_completo(self):self.assertEqual(self.dto(0,cobertura='completa')['valor'],0)
    def test_fecha_lectura_naive_y_futura(self):
        for f in ('2026-10-03 10:00','2026-10-04T00:00:00+02:00'):
            d=dto_medicion(4,fuente='GHL',leida_el=f,hoy='2026-10-03',cobertura='completa');self.assertIsNone(d['valor'])
    def test_fecha_madrid_y_vigencia_explicitada(self):
        d=dto_medicion(4,fuente='GHL',leida_el='2026-10-02T23:30:00Z',hoy='2026-10-03',cobertura='completa',max_dias_fuente=0)
        self.assertEqual(d['valor'],4);self.assertEqual(d['fecha_lectura'],'2026-10-03')
        viejo=dto_medicion(4,fuente='GHL',leida_el='2026-10-01',hoy='2026-10-03',cobertura='completa',max_dias_fuente=1)
        self.assertIn('fuente_antigua',viejo['motivos'])
    def test_ventana_cerrada_y_invalida(self):
        d=self.dto(3,cobertura='completa',desde='2026-09-01',hasta='2026-10-02');self.assertEqual(d['valor'],3)
        for a,b in [('2026-10-03','2026-10-03'),('2026-10-02','2026-10-01'),(None,'2026-10-02')]:
            self.assertIsNone(self.dto(3,cobertura='completa',desde=a,hasta=b)['valor'])
    def test_valores_missing_nan_bool_no_cero(self):
        for v in (None,True,float('nan'),float('inf'),-1):self.assertIsNone(self.dto(v,cobertura='completa')['valor'])
    def test_intentos_ventana_limites_orden_y_previos(self):
        creado=1_000_000;limite=creado+72*3600_000
        d=resumir([{'dateAdded':creado-1},{'dateAdded':limite+1},{'dateAdded':limite},{'dateAdded':creado}],creado,limite+2)
        self.assertEqual(d['primer_min'],0);self.assertEqual(d['intentos_72h'],2)
    def test_una_hora_sin_redondeo_que_finje_cumplimiento(self):
        creado=1_000_000;d=resumir([{'dateAdded':creado+3600_001}],creado,creado+4000_000)
        self.assertGreater(d['primer_min'],60)
    def test_fecha_ausente_desconocida_no_intento_en_cero(self):
        for v in (None,'no-fecha','2026-10-01T10:00:00',True,float('nan')):
            d=resumir([{'dateAdded':v}],1_000_000,2_000_000)
            self.assertIsNone(d['primer_min']);self.assertIsNone(d['intentos_72h']);self.assertEqual(d['fechas_desconocidas'],1)
    def test_futuro_no_cumplimiento(self):
        d=resumir([{'dateAdded':3_000_000}],1_000_000,2_000_000);self.assertIsNone(d['intentos_72h'])
    def test_iso_con_zona_y_mensajes_previos(self):
        creado=ns['timestamp_mensaje']('2026-10-01T10:00:00Z');corte=ns['timestamp_mensaje']('2026-10-03T10:00:00Z')
        d=resumir([{'dateAdded':'2026-10-01T09:59:59Z'},{'dateAdded':'2026-10-01T10:10:00Z'}],creado,corte)
        self.assertEqual(d['primer_min'],10);self.assertEqual(d['intentos_72h'],1)
if __name__=='__main__':unittest.main()
