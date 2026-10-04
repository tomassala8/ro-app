import copy
import unittest
from seo_prioridades import evaluar_seo, consultas_objetivo
from seo_prioridades_fuentes import adaptar_fuentes

CTX = {'cliente_id': 'prueba', 'servicio_seo_confirmado': True, 'fuente_servicio': 'contrato confirmado',
       'ciudades_verificadas': [{'ciudad': 'Barcelona', 'fuente': 'objetivo confirmado'}],
       'servicios_reales': ['asesoría', 'gestoría', 'laboral', 'fiscal', 'contable']}
HOY = '2026-10-03'


def rank(**kw):
    return {'consulta': 'asesoría Barcelona', 'ciudad': 'Barcelona', 'canal': 'organico',
            'posicion': 3, 'fecha': '2026-10-02', 'fuente': 'fuente de prueba',
            'dispositivo': 'movil', 'ubicacion_medicion': 'Barcelona', **kw}


class SEOTest(unittest.TestCase):
    def test_no_infiere_servicio_de_horas(self):
        c = {**CTX, 'servicio_seo_confirmado': False, 'servicio_seo': 'sí', 'horas': 99}
        self.assertFalse(evaluar_seo(c, {}, HOY)['habilitado'])
    def test_fuentes_y_ciudad_obligatorias(self):
        for extra in [{'fuente_servicio': None}, {'ciudades_verificadas': [{'ciudad': 'Barcelona'}]}]:
            self.assertFalse(evaluar_seo({**CTX, **extra}, {}, HOY)['habilitado'])
    def test_servicios_reales(self):
        self.assertEqual(len(consultas_objetivo(CTX)), 6)
        c = {**CTX, 'servicios_reales': ['gestoría']}
        self.assertEqual(len(consultas_objetivo(c)), 1)
    def test_objetivos_ausentes_no_son_cero(self):
        out = evaluar_seo(CTX, {}, HOY)
        self.assertEqual(len(out['objetivos']), 12)
        self.assertTrue(all(o['posicion'] is None for o in out['objetivos']))
    def test_evolucion_contextos_separados(self):
        r = [rank(), rank(posicion=5, fecha='2026-09-30'), rank(canal='maps', posicion=1),
             rank(dispositivo='desktop', posicion=8), rank(ciudad='Madrid', posicion=2)]
        out = evaluar_seo(CTX, {'rankings': r}, HOY)
        o = next(o for o in out['objetivos'] if o['canal']=='organico' and o['dispositivo']=='movil')
        self.assertEqual((o['gap_posiciones'], o['evolucion']), (2, 2))
        self.assertFalse(out['garantia'])
    def test_ausencia_reciente_no_recicla_posicion_vieja(self):
        out = evaluar_seo(CTX, {'rankings': [rank(posicion=None),rank(fecha='2026-09-29')]}, HOY)
        o = next(o for o in out['objetivos'] if o['dispositivo']=='movil')
        self.assertIsNone(o['posicion'])
        self.assertIsNone(o['evolucion'])
    def test_fecha_futura_no_es_evidencia(self):
        out = evaluar_seo(CTX, {'rankings': [rank(fecha='2026-10-04',posicion=1)]}, HOY)
        self.assertTrue(all(o['posicion'] is None for o in out['objetivos']))
    def test_datos_invalidos(self):
        for pos in [0,-2,False,float('nan'),'1']:
            out = evaluar_seo(CTX, {'rankings': [rank(posicion=pos)]}, HOY)
            self.assertTrue(all(o['posicion'] is None for o in out['objetivos']))
    def test_paginas_gsc_no_ranking_maps(self):
        out = evaluar_seo(CTX, {'paginas':[{'url':'https://example.test/a', 'fecha':HOY,
            'fuente':'GSC', 'periodos_comparables':True, 'clics':0, 'clics_antes':4, 'impresiones':20, 'posicion_media':1.2}]}, HOY)
        paginas = [p for p in out['prioridades'] if p['tipo']=='revisar_pagina']
        self.assertEqual(paginas[0]['delta_clics'], -4)
        self.assertTrue(all(o['posicion'] is None for o in out['objetivos']))
    def test_contenido_cobertura_e_impulso_no_antiguedad(self):
        d={'contenido':{'cobertura_completa':True,'desde':'2026-07-01','hasta':HOY,'fuente':'CMS',
            'publicaciones':[{'url':'a','fecha':'2026-08-01','estado':'publicado'}]}}
        out=evaluar_seo(CTX,d,HOY)
        self.assertEqual((out['contenido']['publicados_30_dias'],out['contenido']['publicados_90_dias']), (0,1))
        self.assertFalse(any(p['tipo']=='revisar_plan_contenido' for p in out['prioridades']))
        d['contenido']['cobertura_completa']=False
        self.assertIsNone(evaluar_seo(CTX,d,HOY)['contenido']['publicados_30_dias'])
    def test_plan_acordado_y_duplicados(self):
        d={'contenido':{'cobertura_completa':True,'desde':'2026-07-01','hasta':HOY,'fuente':'CMS',
            'objetivo_30_dias':2,'fuente_objetivo':'plan firmado', 'publicaciones':[
            {'url':'a','fecha':'2026-10-01','estado':'publicado'}, {'url':'a','fecha':'2026-10-01','estado':'publicado'},
            {'url':'b','fecha':'2026-10-01','estado':'borrador'}]}}
        out=evaluar_seo(CTX,d,HOY)
        self.assertEqual(out['contenido']['publicados_30_dias'],1)
        self.assertTrue(any(p['tipo']=='revisar_plan_contenido' for p in out['prioridades']))
    def test_puro_no_muta_y_adaptador_no_horas(self):
        c=copy.deepcopy(CTX);d={'rankings':[rank()]};original=copy.deepcopy((c,d))
        self.assertEqual(evaluar_seo(c,d,HOY),evaluar_seo(c,d,HOY))
        self.assertEqual((c,d),original)
        datos=adaptar_fuentes(CTX,{}, {})
        self.assertEqual(datos['contenido'],{})
    def test_variantes_con_y_sin_tilde_no_se_colapsan(self):
        out=evaluar_seo(CTX,{'rankings':[rank(consulta='asesoria Barcelona',posicion=6),
            rank(consulta='asesoría Barcelona',posicion=28)]},HOY)
        posiciones=[o['posicion'] for o in out['objetivos'] if o['dispositivo']=='movil']
        self.assertEqual(sorted(posiciones),[6,28])
    def test_motores_desconocidos_no_se_fusionan(self):
        out=evaluar_seo(CTX,{'rankings':[rank(dispositivo=None,ubicacion_medicion=None,medicion_id='a'),
            rank(dispositivo=None,ubicacion_medicion=None,medicion_id='b',posicion=9)]},HOY)
        self.assertEqual(len([o for o in out['objetivos'] if o['medicion_id']]),2)

if __name__ == '__main__': unittest.main()
