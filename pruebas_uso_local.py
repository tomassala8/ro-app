"""Pruebas aisladas: no servidor, red ni base de producto."""
import sqlite3
import unittest
from types import SimpleNamespace
from contextlib import contextmanager
from unittest.mock import patch
import uso_local as U

SESSION = '12345678-1234-1234-1234-123456789012'


def evento(n=0,ms=0,sesion=SESSION,**kw):
    return dict(sesion=sesion,secuencia=n,pantalla='app',accion='latido',control='ninguno',activo_ms=ms,**kw)


class Uso(unittest.TestCase):
    def setUp(self):
        self.c = sqlite3.connect(':memory:')
        self.c.row_factory = sqlite3.Row
        self.c.executescript(U.SCHEMA)
    def tearDown(self):
        self.c.close()
    def put(self,n,ms,t,**kw):
        return U.guardar(self.c,'real','real',evento(n,ms,**kw),t)
    def test_validacion_no_acepta_contenido_actor_rutas_ni_control_libre(self):
        U.validar(evento(),{'app'})
        for cambio in ({'actor':'otra'}, {'texto':'secreto'}, {'pantalla':'cliente/privado'}, {'control':'Nombre Cliente'}, {'accion':'tecla'}, {'activo_ms':float('nan')}, {'activo_ms':True},{'activo_ms':30001}):
            b=evento();b.update(cambio)
            with self.assertRaises(ValueError): U.validar(b,{'app'})
    def test_primero_no_cuenta_tiempo_abierto_y_ventana_clamp(self):
        self.assertEqual(self.put(0,30000,100)['activo_ms'],0)
        self.assertEqual(self.put(1,30000,101)['activo_ms'],1000)
        self.assertEqual(self.put(2,30000,100000)['activo_ms'],30000)
    def test_duplicados_fuera_orden_no_suman(self):
        self.put(0,0,100);self.put(1,10000,110)
        self.assertTrue(self.put(1,10000,111)['duplicado'])
        self.assertTrue(self.put(0,10000,112)['duplicado'])
        self.assertEqual(self.c.execute('select sum(activo_ms) from uso_eventos').fetchone()[0],10000)
    def test_pestanas_no_duplican_tiempo(self):
        otra='87654321-1234-1234-1234-123456789012'
        self.put(0,0,100);self.put(0,0,100,sesion=otra)
        self.put(1,30000,130)
        self.assertEqual(self.put(1,30000,130,sesion=otra)['activo_ms'],0)
        self.assertEqual(self.put(2,30000,135,sesion=otra)['activo_ms'],5000)
    def test_ver_como_actor_real_y_contexto_separado(self):
        self.put(0,0,100)
        U.guardar(self.c,'real','otra',evento(1,30000),130)
        U.guardar(self.c,'real','otra',evento(2,30000),160)
        r=self.c.execute('select * from uso_eventos order by id desc').fetchone()
        self.assertEqual((r['actor'],r['visto'],r['activo_ms']),('real','otra',30000))
        self.assertEqual(self.c.execute('select activo_ms from uso_eventos where id=2').fetchone()[0],0)
    def test_retencion_purga_y_resumen_no_filtra_datos_viejos(self):
        self.put(0,0,100);self.put(1,10000,110)
        ahora=U.RETENCION_DIAS*86400+111
        self.assertEqual(U.resumen(self.c,30,ahora)['filas'],[])
        self.put(2,10000,ahora)
        self.assertEqual(self.c.execute('select count(*) from uso_eventos').fetchone()[0],1)
    def test_lectura_solo_puestos_reales_y_sin_suplantacion(self):
        ops={'id':'ops','puestos':['operaciones']};acc={'id':'acc','puestos':['account']}
        self.assertTrue(U.puede_resumen(ops,ops))
        self.assertFalse(U.puede_resumen(acc,ops))
        self.assertFalse(U.puede_resumen(ops,acc))
    def test_tope_eventos_y_reloj_atras(self):
        self.put(0,0,100)
        self.assertEqual(self.put(1,10000,90)['activo_ms'],0)
        for n in range(2,120):self.put(n,0,100)
        self.assertTrue(self.put(120,0,100)['limite'])
    def test_endpoint_identidad_permisos_y_respuestas(self):
        con=self.c
        @contextmanager
        def conectar():yield con
        servir=SimpleNamespace(conectar=conectar,E=SimpleNamespace(nucleo_bloqueado=False,modulos={'privado':{}}),ve_alguno=lambda p,m:p['id']=='ops')
        class Handler:
            def responder(self,code,body):return code,body
            def _api_get(self,*args):return 'original_get'
            def api_post(self,*args):return 'original_post'
        U.enganchar(Handler,servir)
        h=Handler();ops={'id':'ops','puestos':['operaciones']};acc={'id':'acc','puestos':['account']}
        self.assertEqual(h._api_get('/api/uso',{},acc,acc)[0],403)
        self.assertEqual(h._api_get('/api/uso',{},ops,acc)[0],403)
        self.assertEqual(h._api_get('/api/uso',{'dias':['31']},ops,ops)[0],400)
        self.assertEqual(h._api_get('/api/uso/aviso',{},acc,acc)[0],200)
        b=evento();b['pantalla']='privado'
        self.assertEqual(h.api_post('/api/uso',ops,acc,b)[0],403)
        self.assertEqual(h.api_post('/api/uso',ops,acc,evento())[0],200)
        row=self.c.execute('select actor,visto from uso_eventos').fetchone()
        self.assertEqual(tuple(row),('ops','acc'))
        self.assertEqual(h._api_get('/api/otra',{},ops,ops),'original_get')
        self.assertEqual(h.api_post('/api/otra',ops,ops,{}),'original_post')
        servir.E.nucleo_bloqueado=True
        self.assertEqual(h.api_post('/api/uso',ops,ops,evento())[0],503)

    def test_enganche_aviso_y_validaciones_no_abren_base(self):
        def prohibido():raise AssertionError('No se debe abrir la base')
        servir=SimpleNamespace(conectar=prohibido,E=SimpleNamespace(nucleo_bloqueado=False,modulos={}),ve_alguno=lambda p,m:False)
        class Handler:
            def responder(self,code,body):return code,body
            def _api_get(self,*args):return 'original_get'
            def api_post(self,*args):return 'original_post'
        U.enganchar(Handler,servir)
        h=Handler();ops={'id':'ops','puestos':['operaciones']};acc={'id':'acc','puestos':['account']}
        self.assertEqual(h._api_get('/api/uso/aviso',{},acc,acc)[0],200)
        self.assertEqual(h._api_get('/api/uso',{},acc,acc)[0],403)
        self.assertEqual(h.api_post('/api/uso',acc,acc,{'texto':'x'})[0],400)
        with patch.dict('os.environ',{'DATABASE_URL':'postgresql://example/unused'}):
            aviso=h._api_get('/api/uso/aviso',{},ops,ops)
            self.assertFalse(aviso[1]['disponible'])
            self.assertEqual(h._api_get('/api/uso',{},ops,ops)[0],503)
            self.assertEqual(h.api_post('/api/uso',ops,ops,evento())[0],503)

    def test_schema_solo_primera_peticion_valida(self):
        con=sqlite3.connect(':memory:');con.row_factory=sqlite3.Row
        @contextmanager
        def conectar():yield con
        servir=SimpleNamespace(conectar=conectar,E=SimpleNamespace(nucleo_bloqueado=False,modulos={}),ve_alguno=lambda p,m:True)
        class Handler:
            def responder(self,code,body):return code,body
            def _api_get(self,*args):pass
            def api_post(self,*args):pass
        U.enganchar(Handler,servir)
        self.assertEqual(con.execute("select count(*) from sqlite_master where name like 'uso_%'").fetchone()[0],0)
        p={'id':'ops','puestos':['operaciones']}
        self.assertEqual(Handler().api_post('/api/uso',p,p,evento())[0],200)
        self.assertEqual(con.execute('select count(*) from uso_eventos').fetchone()[0],1)
        con.close()

    def test_dia_madrid_no_fecha_utc(self):
        from datetime import datetime,timezone
        t=datetime(2026,10,3,23,30,tzinfo=timezone.utc).timestamp()
        self.put(0,0,t)
        r=U.resumen(self.c,7,t+1)
        self.assertEqual(r['zona_dias'],'Europe/Madrid')
        self.assertEqual(r['filas'][0]['dia'],'2026-10-04')

    def test_control_agrupa_sin_contenido(self):
        b=evento();b['control']='guardar';U.guardar(self.c,'a','a',b,100)
        filas=U.resumen(self.c,7,101)['filas']
        self.assertEqual(filas[0]['control'],'guardar')
        self.assertEqual(filas[0]['eventos'],1)

if __name__ == '__main__':unittest.main()
