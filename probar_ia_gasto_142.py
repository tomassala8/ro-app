"""Presupuesto142 real con SQLite temporal y proveedor sintético, nunca llaves/red."""
from contextlib import contextmanager
from datetime import datetime
import json, math, sqlite3, tempfile, types, unittest
from pathlib import Path
from unittest.mock import patch
import ia_gasto as G

class Gasto142(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=str(Path(self.tmp.name)/'fixture.db')
        @contextmanager
        def conectar():
            c=sqlite3.connect(self.db,timeout=5)
            try: yield c;c.commit()
            except BaseException:c.rollback();raise
            finally:c.close()
        self.conectar=conectar
        self.patches=[patch.object(G,'S',types.SimpleNamespace(conectar=conectar,P=types.SimpleNamespace(puestos_de=lambda p:p.get('puestos',[])))),patch.object(G,'ahora',lambda:datetime(2026,10,3,12,tzinfo=G.MADRID)),patch.object(G,'PRECIOS',{'modelo-fixture':{'entrada':1.,'cache_escrita':1.25,'cache_leida':.1,'salida':5.}}),patch.object(G,'PRECIOS_VERIFICADOS',True),patch.object(G,'modelo_de',lambda _: 'modelo-fixture'),patch.object(G,'_clave_principal',lambda:'clave-fixture-no-real'),patch.object(G,'clave_respaldo',lambda:'respaldo-fixture-no-real'),patch.object(G,'_umbrales',lambda _:None)]
        for p in self.patches:p.start()
        G.iniciar();self.t=json.loads(json.dumps(G.TOPES_DEFECTO));self.t.update(mes_eur=10.,dia_eur=10.,persona_dia_eur=10.,usd_a_eur=1.,funcion_mes_eur={k:10. for k in G.TAREAS})
        self.configurar(self.t);G.fijar_peticion({'id':'fixture'},{'id':'fixture'},'mi-dia')
        self.prov=self.proveedor();self.provpatch=patch.object(G,'PROVEEDOR',self.prov);self.provpatch.start()
    def tearDown(self):
        G.soltar_peticion();self.provpatch.stop()
        for p in reversed(self.patches):p.stop()
        self.tmp.cleanup()
    def configurar(self,t):
        with self.conectar() as c:c.execute('INSERT INTO ia_topes(creada,quien,valores) VALUES (?,?,?)',('2026-10-03','fixture',json.dumps(t)))
    def proveedor(self,error=None):
        class P:
            writes=0
            def contar_entrada(p,modelo,*a,**kw):return {'acreditado':True,'modelo':modelo,'tokens':100}
            def crear(p,*a,**kw):
                p.writes+=1
                if error:raise G.ErrorProveedor(error,'fixture')
                return {'texto':'fixture'},'modelo-fixture',{'entrada':100,'salida':10},None
        return P()
    def reservar(self,eur=6.,t=None,llave='principal'):
        return G._comprobar_y_reservar('consejo','fixture',llave,eur,t or self.t)
    def llamar(self):return G.llamar('sistema',{}, {},tarea='consejo')
    def test_modelo_y_tarifa_no_verificados(self):
        with self.assertRaises(G.SinGasto):G.precio('modelo-fixture-2026')
        with patch.object(G,'PRECIOS_VERIFICADOS',False):
            with self.assertRaises(G.SinGasto):self.llamar()
            self.assertEqual(G.modo()['modo'],'reglas')
        self.assertEqual(self.prov.writes,0)
    def test_conteo_no_estimacion_por_caracteres(self):
        with self.assertRaises(G.SinGasto):G.coste_maximo('modelo-fixture','abc',10,t=self.t)
        with patch.object(G,'PROVEEDOR',types.SimpleNamespace(crear=self.prov.crear)):
            with self.assertRaises(G.SinGasto):self.llamar()
        self.assertEqual(self.prov.writes,0)
    def test_identidad_y_ver_como(self):
        for real,persona in ((None,None),({'id':'x'},None),({'id':'x'},{'id':'fixture'}),({'id':'sistema'},{'id':'sistema'})):
            G.fijar_peticion(real,persona,'mi-dia')
            with self.assertRaises(G.SinGasto):self.llamar()
        self.assertEqual(self.prov.writes,0)
    def test_nan_inf_negativo_reserva_y_topes(self):
        for v in (float('nan'),float('inf'),-1,True,None):
            with self.assertRaises((G.SinGasto,ValueError)):self.reservar(v)
        for v in (float('nan'),float('inf'),True):
            with self.assertRaises(ValueError):G.validar({'dia_eur':v},self.t)
        self.assertEqual(G._reservado(),0)
    def test_claim_sobrevive_memoria_y_cambio_dia(self):
        rid=self.reservar();G._RESERVAS.clear();self.assertEqual(G._reservado(),6.)
        with patch.object(G,'ahora',lambda:datetime(2026,11,1,12,tzinfo=G.MADRID)):
            with self.assertRaises(G.SinGasto):self.reservar()
        with self.conectar() as c:self.assertEqual(c.execute('SELECT estado FROM ia_reservas WHERE id=?',(rid,)).fetchone()[0],'activa')
    def test_topes_latest_no_snapshot_viejo(self):
        nuevo={**self.t,'mes_eur':5.,'dia_eur':5.};self.configurar(nuevo)
        with self.assertRaises(G.SinGasto):self.reservar(6.,self.t)
    def test_tope_funcion_persona_respaldo(self):
        for changes in ({'funcion_mes_eur':{**self.t['funcion_mes_eur'],'consejo':1.}},{'persona_dia_eur':1.},{'respaldo_mes_eur':1.}):
            self.configurar({**self.t,**changes})
            with self.assertRaises(G.SinGasto):self.reservar(2.,llave='respaldo')
        self.assertEqual(G._reservado(),0)
    def test_gasto_y_cierre_atomicos(self):
        rid=self.reservar(1.)
        G.apuntar('consejo','fixture',None,'modelo-fixture','principal',{'entrada':100,'salida':10},True,t=self.t,reserva_id=rid)
        self.assertEqual(G._reservado(),0)
        self.assertGreater(G.gastado()['dia'],0)
        with self.assertRaises(G.SinGasto):G.apuntar('consejo','fixture',None,'modelo-fixture','principal',{'entrada':1},True,t=self.t,reserva_id=rid)
    def test_timeout_no_libera_ni_respaldo_evade(self):
        p=self.proveedor('caida')
        t={**self.t,'dia_eur':.02,'mes_eur':.02};self.configurar(t)
        with patch.object(G,'PROVEEDOR',p):
            with self.assertRaises(G.SinGasto):self.llamar()
        self.assertEqual(p.writes,1)
        self.assertGreater(G._reservado(),0)
        with self.conectar() as c:self.assertEqual(c.execute('SELECT estado FROM ia_reservas').fetchone()[0],'incierta')
    def test_respaldo_necesita_segunda_reserva(self):
        p=self.proveedor('caida')
        with patch.object(G,'PROVEEDOR',p):
            with self.assertRaises(G.ErrorProveedor):self.llamar()
        self.assertEqual(p.writes,2)
        with self.conectar() as c:self.assertEqual(c.execute("SELECT count(*) FROM ia_reservas WHERE estado='incierta'").fetchone()[0],2)
    def test_lotes_sin_request_ni_clave(self):
        with patch.object(G,'_clave_principal',side_effect=AssertionError('no leer clave')):
            with self.assertRaises(G.SinGasto):G.lote_enviar('consejo',[])
            with self.assertRaises(G.SinGasto):G.lote_recoger('fixture')
    def test_db_error_no_defaults(self):
        with self.conectar() as c:c.execute('DROP TABLE ia_topes')
        with self.assertRaises(G.SinGasto):G.topes()
        with self.assertRaises(G.SinGasto):self.llamar()
        self.assertEqual(self.prov.writes,0)
    def test_solo_tomas_nominal_topes(self):
        def persona(id):return {'id':id,'puestos':['direccion']}
        self.assertTrue(G.puede_ver(persona('tomas'),persona('tomas')))
        for a,b in (('otra','otra'),('otra','tomas'),('tomas','otra')):self.assertFalse(G.puede_ver(persona(a),persona(b)))
    def test_uso_nan_no_libera(self):
        p=self.proveedor();p.crear=lambda *a,**kw:({},'modelo-fixture',{'entrada':float('nan'),'salida':1},None)
        with patch.object(G,'PROVEEDOR',p):
            with self.assertRaises(G.SinGasto):self.llamar()
        self.assertGreater(G._reservado(),0)

    def test_dos_procesos_no_reservan_mas_del_tope(self):
        import subprocess,sys
        codigo = """
from contextlib import contextmanager
from datetime import datetime
import sqlite3,sys,types
import ia_gasto as G
@contextmanager
def conectar():
 c=sqlite3.connect(sys.argv[1],timeout=5)
 try: yield c;c.commit()
 except BaseException:c.rollback();raise
 finally:c.close()
G.S=types.SimpleNamespace(conectar=conectar)
G.ahora=lambda:datetime(2026,10,3,12,tzinfo=G.MADRID)
try:
 G._comprobar_y_reservar('consejo','fixture','principal',6.,G.topes())
 print('reservado')
except G.SinGasto:print('bloqueado')
"""
        procesos=[subprocess.Popen([sys.executable,'-c',codigo,self.db],cwd=Path(__file__).parent,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(2)]
        resultados=[]
        for proc in procesos:
            salida,error=proc.communicate(timeout=10)
            self.assertEqual(proc.returncode,0,error);resultados.append(salida.strip())
        self.assertEqual(sorted(resultados),['bloqueado','reservado']);self.assertEqual(G._reservado(),6.)

    def test_caida_proceso_despues_efecto_conserva_claim(self):
        import subprocess,sys
        codigo = """
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import os,sqlite3,sys,types
import ia_gasto as G
@contextmanager
def conectar():
 c=sqlite3.connect(sys.argv[1],timeout=5)
 try: yield c;c.commit()
 except BaseException:c.rollback();raise
 finally:c.close()
G.S=types.SimpleNamespace(conectar=conectar)
G.ahora=lambda:datetime(2026,10,3,12,tzinfo=G.MADRID)
G.PRECIOS={'modelo-fixture':dict(entrada=1.,cache_escrita=1.25,cache_leida=.1,salida=5.)}
G.PRECIOS_VERIFICADOS=True
G.modelo_de=lambda _: 'modelo-fixture'
G._clave_principal=lambda:'fixture-no-real'
class Proveedor:
 def contar_entrada(self,modelo,*a,**kw):return dict(acreditado=True,modelo=modelo,tokens=100)
 def crear(self,*a,**kw):
  Path(sys.argv[2]).write_text('efecto-sintetico')
  os._exit(73)
G.PROVEEDOR=Proveedor()
G.fijar_peticion({'id':'fixture'},{'id':'fixture'},'mi-dia')
G.llamar('sistema',{}, {},tarea='consejo')
"""
        marca=Path(self.tmp.name)/'efecto-fixture'
        proc=subprocess.run([sys.executable,'-c',codigo,self.db,str(marca)],cwd=Path(__file__).parent,capture_output=True,text=True,timeout=10)
        self.assertEqual(proc.returncode,73,proc.stderr)
        self.assertEqual(marca.read_text(),'efecto-sintetico')
        with self.conectar() as c:
            self.assertEqual(c.execute('SELECT estado FROM ia_reservas').fetchone()[0],'activa')
            self.assertEqual(c.execute('SELECT count(*) FROM ia_gasto').fetchone()[0],0)
        pendiente=G._reservado();self.assertGreater(pendiente,0)
        with self.assertRaises(G.SinGasto):self.reservar(10.)
        self.assertEqual(G._reservado(),pendiente)

    def test_fallo_insert_reserva_nunca_llega_a_proveedor(self):
        with self.conectar() as c:c.execute("CREATE TRIGGER fixture_rechazar BEFORE INSERT ON ia_reservas BEGIN SELECT RAISE(ABORT,'fixture'); END;")
        with self.assertRaises(sqlite3.IntegrityError):self.llamar()
        self.assertEqual(self.prov.writes,0)
        self.assertEqual(G._reservado(),0)

    def test_ledger_invalido_no_se_lee_como_cero(self):
        with self.conectar() as c:c.execute("INSERT INTO ia_gasto(creada,dia,mes,quien,tarea,llave,coste_eur,ok) VALUES (?,?,?,?,?,?,?,?)",('2026-10-03','2026-10-03','2026-10','fixture','consejo','principal','NaN',False))
        with self.assertRaises(G.SinGasto):self.llamar()
        self.assertEqual(self.prov.writes,0)

    def test_fallo_apuntar_conserva_reserva(self):
        with self.conectar() as c:c.execute("CREATE TRIGGER fixture_fallo_gasto BEFORE INSERT ON ia_gasto BEGIN SELECT RAISE(ABORT,'fixture'); END;")
        with self.assertRaises(sqlite3.IntegrityError):self.llamar()
        self.assertEqual(self.prov.writes,1);self.assertGreater(G._reservado(),0)

    def test_contador_invalido_nunca_compra(self):
        for datos in ({'acreditado':False,'modelo':'modelo-fixture','tokens':100},{'acreditado':True,'modelo':'otro','tokens':100},{'acreditado':True,'modelo':'modelo-fixture','tokens':True}):
            self.prov.contar_entrada=lambda *a,datos=datos,**kw:datos
            with self.assertRaises(G.SinGasto):self.llamar()
        self.assertEqual(self.prov.writes,0)

if __name__=='__main__':unittest.main(verbosity=2)
