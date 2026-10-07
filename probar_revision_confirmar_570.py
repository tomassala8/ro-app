"""Caracterización aislada L-13: AST real, sólo SQLite y personas sintéticas."""
import ast
import contextlib
import copy
import json
import sqlite3
import tempfile
import types
import unittest
from datetime import date, timedelta
from pathlib import Path
import permisos as P

APP=Path(__file__).resolve().parent

def extraer(archivo,nombre,ns):
    tree=ast.parse((APP/archivo).read_text())
    fn=copy.deepcopy(next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==nombre))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),archivo+' AST570','exec'),ns)
    return ns[nombre]

class Confirmar570(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'fixture.sqlite'
        self.actor={'id':'ops-fixture','alias':'Fixture','puestos':['operaciones'],'estado':'activo','activo':True}
        self.target={'id':'target-fixture','puestos':['direccion'],'estado':'activo','activo':True}
        self.personas=[self.actor,self.target]
        self.dudas=[{'id':'d-fixture','tipo':'persona','persona_id':self.actor['id']}]
        self.e=types.SimpleNamespace(crudo={'personas':self.personas,'para_confirmar':self.dudas},
            persona=lambda pid:next((p for p in self.personas if p['id']==pid),None))
        self.aplicar=extraer('build_data.py','aplicar_respuestas',{'REGLAS':P.REGLAS,'PUESTOS_APP':set(P.PUESTO),'date':date,'timedelta':timedelta})
        with self.con() as c:
            c.execute('CREATE TABLE decisiones(id INTEGER PRIMARY KEY,quien TEXT,tipo TEXT,clave TEXT,problema TEXT,respuesta TEXT,anula_a INTEGER,recomendacion TEXT,respondida TEXT,respondida_por TEXT)')
            c.execute('CREATE TABLE historial(quien TEXT,coleccion TEXT,id TEXT,operacion TEXT,antes TEXT,datos TEXT)')
        def recargar(*a):
            with self.con() as c:
                rows=c.execute('SELECT respuesta FROM decisiones WHERE respuesta IS NOT NULL ORDER BY id').fetchall()
            self.aplicar([json.loads(r[0]) for r in rows],self.personas,[],{}, {},'2026-10-04')
        self.e.recargar_personas=recargar
        ns={'P':P,'E':self.e,'json':json,'conectar':self.con,'registrar':lambda *a:None,
            'ahora':lambda:'2026-10-04T10:00:00+02:00','hoy':lambda:'2026-10-04'}
        self.ajustes=extraer('servir.py','ajustes',ns)
        self.h=types.SimpleNamespace(responder=lambda status,dto:(status,dto))
    @contextlib.contextmanager
    def con(self):
        c=sqlite3.connect(self.db);c.row_factory=sqlite3.Row
        try:
            with c:yield c
        finally:c.close()
    def tearDown(self):self.tmp.cleanup()
    def confirmar(self,cambios,pid=None,duda='d-fixture'):
        return self.ajustes(self.h,'/api/ajustes/confirmar',self.actor,{'respuesta':{'tipo':'persona','duda':duda,'persona_id':pid or self.actor['id'],'cambios':cambios}})
    def normal(self,cambios,pid=None):
        return self.ajustes(self.h,'/api/ajustes/persona',self.actor,{'id':pid or self.actor['id'],'cambios':cambios})
    def test_policy_real_operaciones_puede_ajustes(self):
        cp=P.contexto(self.actor,{'personas':self.personas,'clientes':[],'asignaciones':[]})
        self.assertTrue(P.ver(self.actor,{'tipo':'ajustes_editar'},cp)['ok'])
    def test_repro_puestos_propios_bypass_confirmar(self):
        self.assertEqual(self.normal({'puestos':['direccion']})[0],403)
        self.assertEqual(self.actor['puestos'],['operaciones'])
        self.assertEqual(self.confirmar({'puestos':['direccion']})[0],200)
        self.assertEqual(self.actor['puestos'],['direccion'],'reproducción de escalado indebido actual')
    def test_repro_target_mando_identidad_jefe_y_baja(self):
        cambios={'correo':'fixture@'+'example.invalid','jefe':'ops-fixture','estado':'baja'}
        self.assertEqual(self.normal(cambios,self.target['id'])[0],403)
        self.assertEqual(self.confirmar(cambios,self.target['id'])[0],200)
        for k,v in cambios.items():self.assertEqual(self.target[k],v)
        self.assertFalse(self.target['activo'])
    def test_repro_duda_inexistente_no_se_valida(self):
        self.assertEqual(self.confirmar({'estado':'dudoso'},duda='ausente-fixture')[0],200)
        self.assertEqual(self.actor['estado'],'dudoso')
    def test_repro_duda_persona_ajena(self):
        self.assertNotEqual(self.dudas[0]['persona_id'],self.target['id'])
        self.assertEqual(self.confirmar({'estado':'dudoso'},pid=self.target['id'])[0],200)
        self.assertEqual(self.target['estado'],'dudoso')
    def test_repro_persona_no_existe_igualmente_recibo_ok(self):
        self.assertEqual(self.confirmar({'estado':'activo'},pid='inexistente-fixture')[0],200)
        with self.con() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM decisiones').fetchone()[0],1)
    def test_control_forma_ui_activo_dudoso_no_altera_roles(self):
        original=list(self.actor['puestos'])
        for estado in ('dudoso','activo'):
            self.assertEqual(self.confirmar({'estado':estado})[0],200)
            self.assertEqual(self.actor['estado'],estado)
            self.assertEqual(self.actor['puestos'],original)
    def test_control_ajuste_normal_persona_sin_mando_guarda_historial(self):
        p={'id':'account-fixture','puestos':['account'],'estado':'activo','activo':True}
        self.personas.append(p)
        self.assertEqual(self.normal({'imputa_horas':False},p['id'])[0],200)
        with self.con() as c:
            r=c.execute('SELECT id,datos FROM historial').fetchone()
        self.assertEqual(r['id'],p['id'])
        self.assertEqual(json.loads(r['datos']),{'imputa_horas':False})

if __name__=='__main__':unittest.main()
