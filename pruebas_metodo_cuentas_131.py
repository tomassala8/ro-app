"""QA131: fuentes sintéticas, catálogo ACT real; sin red/datasets de clientes."""
import ast, datetime as dt, json, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import metodo_cuentas as M
from fuentes_verdad import clientes_activos as ACT

class Metodo131(unittest.TestCase):
    def setUp(self):
        self.hoy=dt.date(2026,10,3)
        self.a={'cliente_id':'activo','persona_id':'p','silla':'trafficker','desde':'2026-09-01','principal':True,'confianza':'confirmada'}
        self.ps={'p':{'id':'p','estado':'activo','puestos':['trafficker']}}
    def test_personas_no_activas(self):
        for estado in ('dudoso','sin incorporar','baja',None):
            self.assertEqual(M.responsables('activo',[self.a],{'p':{'id':'p','estado':estado}},self.hoy),[])
        self.assertEqual(M.responsables('activo',[self.a],self.ps,self.hoy),['p'])
    def test_tenure_suplencia_confirmadas(self):
        for campos in ({'desde':None},{'desde':'invalida'},{'desde':'2026-10-04'},{'hasta':'2026-10-02'},{'hasta':'invalida'},{'suplencia':True},{'duda':True}):
            self.assertEqual(M.responsables('activo',[{**self.a,**campos}],self.ps,self.hoy),[])
        self.assertEqual(M.responsables('activo',[{**self.a,'suplencia':True,'hasta':'2026-10-20'}],self.ps,self.hoy),['p'])
    def test_catalogo_act_core_y_scope(self):
        ids=['activo','dudoso','medalba','fuera_core']
        reglas={'regla':{'id':M.REGLA_ID,'cadencia_dias':15,'responsable_role':'trafficker'},'clientes':[{'cliente_id':c,'estado_cohorte':'confirmada','cadencia_dias':15,'responsable_role':'trafficker','tipo_cohorte':'metodo_actual_recurrente'} for c in ids]}
        crudo={'clientes':[{'id':c} for c in ids[:-1]],'personas':list(self.ps.values()),'asignaciones':[]}
        servicio=SimpleNamespace(P=SimpleNamespace(contexto=lambda p,c:{},ver=lambda p,o,c:{'ok':p['id']!='denegado'}))
        with tempfile.TemporaryDirectory() as td:
            archivo=Path(td)/'estado.json'
            archivo.write_text(json.dumps({'activos':[{'id':'activo','tipo':'recurrente'},{'id':'dudoso','tipo':'dudoso'},{'id':'medalba','tipo':'recurrente'},{'id':'fuera_core','tipo':'proyecto'}]}))
            with patch.object(ACT,'ESTADO',archivo),patch.object(ACT,'_CACHE',{'marca':None,'estado':None}),patch.object(M,'S',servicio),patch.object(M,'leer',lambda p:reglas if p==M.REGLAS else {}):
                resultado=M.estado_operativo({'id':'real'},{'id':'real'},crudo,self.hoy)
                self.assertEqual([r['cliente_id'] for r in resultado['sugerencias']],['activo'])
                self.assertTrue(resultado['cohorte_actual_verificada'])
                self.assertEqual(M.estado_operativo({'id':'denegado'},{'id':'real'},crudo,self.hoy)['sugerencias'],[])
                archivo.unlink()
                salida=M.estado_operativo({'id':'real'},{'id':'real'},crudo,self.hoy)
                self.assertEqual(salida['sugerencias'],[]);self.assertFalse(salida['cohorte_actual_verificada'])
    def test_productor_metadato_real_no_main(self):
        fuente=Path(__file__).parent/'fuentes_produccion/generar_produccion.py'
        arbol=ast.parse(fuente.read_text());ns={'dt':dt}
        nodo=next(n for n in arbol.body if isinstance(n,ast.FunctionDef) and n.name=='medicion_revisiones_account')
        exec(compile(ast.Module(body=[nodo],type_ignores=[]),str(fuente),'exec'),ns)
        medir=ns['medicion_revisiones_account']
        for fila,sello in (({},'2026-10-03'),({'rev_pm':{}},'2026-10-03'),({'rev_pm':{'n':0,'mas48':0}},None),({'rev_pm':{'n':True,'mas48':0}},'2026-10-03'),({'rev_pm':{'n':1,'mas48':2}},'2026-10-03'),({'rev_pm':{'n':0,'mas48':0}},'2026-10-04')):
            self.assertEqual(medir(fila,sello,self.hoy)['estado'],'sin_dato')
        self.assertEqual(medir({'rev_pm':{'n':0,'mas48':0}},'2026-10-03',self.hoy)['estado'],'medido')

if __name__=='__main__':unittest.main(verbosity=2)
