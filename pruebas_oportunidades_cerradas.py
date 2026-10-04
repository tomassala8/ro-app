import json
import unittest
from fuentes_crm.oportunidades_cerradas import collect

class Fuente:
    def __init__(self, paginas):self.paginas=paginas;self.llamadas=[]
    def req(self, loc, metodo, ruta, **q):
        self.llamadas.append((loc,metodo,ruta,q.copy()))
        lista=self.paginas.get(q['status'],[{'opportunities':[], 'meta':{'total':0}}])
        index=sum(x[3]['status']==q['status'] for x in self.llamadas)-1
        valor=lista[min(index,len(lista)-1)]
        if isinstance(valor,Exception):raise valor
        return valor

def fila(oid,estado='won',**kw):return {'id':oid,'status':estado,**kw}
def pagina(filas,**meta):return {'opportunities':filas,'meta':meta}

class Pruebas(unittest.TestCase):
    def leer(self,g,**kw):return collect(g,'local123',hoy='2026-10-03',**kw)
    def test_paginacion_cursor_total_dedup_sin_pii(self):
        g=Fuente({'won':[pagina([fila('a',name='persona',contact={'email':'oculto@example.org'},monetaryValue=999)],total=2,startAfterId='a',startAfter=100,nextPage=2),pagina([fila('a'),fila('b')],total=2)]})
        d=self.leer(g,incluir_privado=True)
        self.assertTrue(d['cobertura']['completa']);self.assertEqual(d['conteos_observados']['won'],2)
        q=g.llamadas[1][3];self.assertEqual((q['startAfterId'],q['startAfter'],q['page']),('a',100,2))
        self.assertNotIn('persona',json.dumps(d));self.assertNotIn('email',json.dumps(d));self.assertNotIn('999',json.dumps(d))
        self.assertTrue(all(x[1:3]==('GET','/opportunities/search') for x in g.llamadas))
    def test_pagina_siguiente_sin_cursor(self):
        g=Fuente({'won':[pagina([fila('a')],nextPage=2),pagina([fila('b')],total=2)]})
        self.assertTrue(self.leer(g)['cobertura']['completa']);self.assertEqual(g.llamadas[1][3]['page'],2)
    def test_sin_metadata_continua_hasta_vacio(self):
        g=Fuente({'won':[pagina([fila('a')]),pagina([])]})
        self.assertTrue(self.leer(g)['cobertura']['estados']['won']['completa'])
    def test_limite_nunca_completa(self):
        d=self.leer(Fuente({'won':[pagina([fila('a')],total=2,nextPage=2)]}),max_pages=1)
        self.assertFalse(d['cobertura']['completa']);self.assertIn('limite_paginas',d['cobertura']['estados']['won']['incidencias'])
    def test_error_no_exporta_mensaje(self):
        d=self.leer(Fuente({'won':[{'_error':403,'_msg':'token=secreto usuario@example.org'}]}))
        self.assertFalse(d['cobertura']['completa']);self.assertNotIn('secreto',json.dumps(d))
    def test_excepcion_preserva_otras_fuentes(self):
        d=self.leer(Fuente({'won':[RuntimeError('secret')],'lost':[pagina([fila('l','lost')],total=1)]}))
        self.assertEqual(d['conteos_observados']['lost'],1);self.assertEqual(d['estado_fuente'],'parcial')
    def test_ciclo_y_sin_avance(self):
        for paginas in ([pagina([fila('a')],startAfterId='a',startAfter=10),pagina([fila('b')],startAfterId='a',startAfter=10)], [pagina([fila('a')],nextPage=2),pagina([fila('a')],nextPage=3)]):
            d=self.leer(Fuente({'won':paginas}))
            self.assertFalse(d['cobertura']['estados']['won']['completa'])
            self.assertTrue(set(d['cobertura']['estados']['won']['incidencias'])&{'ciclo_paginacion','pagina_sin_avance'})
    def test_url_proveedor_no_se_sigue(self):
        g=Fuente({'won':[pagina([fila('a')],nextPageUrl='https://evil.org/?token=secreto')]})
        d=self.leer(g);self.assertFalse(d['cobertura']['estados']['won']['completa'])
        self.assertEqual(sum(x[3]['status']=='won' for x in g.llamadas),1);self.assertNotIn('evil',json.dumps(d))
    def test_fuera_subcuenta_estado_y_identidad(self):
        d=self.leer(Fuente({'won':[pagina([fila('a',locationId='otra'),fila('b','open'),{'status':'won'}],total=3)]}),max_pages=1)
        self.assertEqual(d['conteos_observados']['won'],0);self.assertFalse(d['cobertura']['completa'])
    def test_conflicto_identidad_no_cuenta_dos_estados(self):
        d=self.leer(Fuente({'won':[pagina([fila('a')],total=1)],'lost':[pagina([fila('a','lost')],total=1)]}))
        self.assertEqual(sum(d['conteos_observados'].values()),0);self.assertFalse(d['cobertura']['completa'])
    def test_update_nunca_es_fecha_de_cierre(self):
        d=self.leer(Fuente({'won':[pagina([fila('a',updatedAt='2026-10-02T10:00:00Z',lastStatusChangeAt='2026-10-01T10:00:00Z')],total=1)]}),incluir_privado=True)
        r=d['privado']['oportunidades'][0];self.assertIsNone(r['fecha_cierre']);self.assertIsNotNone(r['actualizada']);self.assertIsNotNone(r['ultimo_cambio_estado_observado'])
        self.assertIsNone(d['cierres_del_periodo']);self.assertIsNone(d['ratio_leads_ventas'])
    def test_invalidos_no_llaman_y_v3_explicito(self):
        g=Fuente({})
        for kwargs in ({'max_pages':False},{'max_pages':0},{'esquema':'inventado'}):
            with self.assertRaises(ValueError):self.leer(g,**kwargs)
        self.assertFalse(g.llamadas)
        self.leer(g,esquema='v3');self.assertIn('locationId',g.llamadas[0][3]);self.assertNotIn('location_id',g.llamadas[0][3])
    def test_default_no_ids_privados(self):
        d=self.leer(Fuente({'won':[pagina([fila('privado123')],total=1)]}))
        self.assertNotIn('privado',d);self.assertNotIn('privado123',json.dumps(d))
    def test_total_cambia_no_promete_completo(self):
        d=self.leer(Fuente({'won':[pagina([fila('a')],total=2,nextPage=2),pagina([fila('b')],total=3,nextPage=3),pagina([])]}))
        self.assertFalse(d['cobertura']['completa']);self.assertIn('total_cambio_durante_lectura',d['cobertura']['estados']['won']['incidencias'])

if __name__=='__main__':unittest.main()
