"""586 diagnóstico, no fix: AST ver_dato real y reglas actuales, sólo fixtures."""
import ast,copy,json,re,tempfile,types,unittest
from pathlib import Path
import permisos as P
import probar_alias_importes_576 as F
from recorte_alias_propuesta_583 import familias_583,recortar_propuesta_583
APP=Path(__file__).resolve().parent
TREE=ast.parse((APP/'servir.py').read_text())

def match_segmentos(almacen,patron):
    import fnmatch
    return (isinstance(almacen,str) and all(s not in ('','.','..') for s in almacen.split('/'))
            and len(almacen.split('/'))==len(patron.split('/'))
            and all(fnmatch.fnmatchcase(s,p) for s,p in zip(almacen.split('/'),patron.split('/'))))

class Almacenes586(unittest.TestCase):
 def setUp(self):
    self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
    self.actor={'id':'setter_fixture','estado':'activo','activo':True,'puestos':['setters']}
    self.raw={'personas':[self.actor],'clientes':[],'asignaciones':[]}
    self.e=types.SimpleNamespace(crudo=self.raw,modulos=P.cargar_modulos())
    self.ns={'P':P,'E':self.e,'DATA':Path(self.tmp.name),'re':re,'json':json,
             'registrar':lambda *a,**kw:1,'registrar_agrupado':lambda *a,**kw:None}
    nombres=('config_almacen','cliente_del_dato','ve_alguno')
    nodes=[copy.deepcopy(n) for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name in nombres]
    fn=next(n for n in ast.walk(TREE) if isinstance(n,ast.FunctionDef) and n.name=='api_post')
    branch=next(n for n in fn.body if isinstance(n,ast.If) and isinstance(n.test,ast.Compare)
                and any(isinstance(c,ast.Constant) and c.value=='/api/ver_dato' for c in n.test.comparators))
    ep=ast.parse('def endpoint(self,ruta,b,real,persona,cp,solo_lectura):\n pass').body[0]
    ep.body=[copy.deepcopy(branch)]
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes+[ep],type_ignores=[])),'ver_dato_real586','exec'),self.ns)
 def get(self,almacen,actor=None):
    p=actor or self.actor
    f=Path(self.tmp.name)/(almacen+'.json');f.parent.mkdir(parents=True,exist_ok=True)
    f.write_text(json.dumps({'grupo':{'ref-fixture':{'marca':'dato-sintetico'}}}))
    h=types.SimpleNamespace(responder=lambda c,d:(c,d))
    with P.mirando_como(p,self.raw):
      return self.ns['endpoint'](h,'/api/ver_dato',{'almacen':almacen,'ref':'ref-fixture','campo':'marca'},p,p,P.contexto(p,self.raw),False)
 def test_repro_setter_extra_segmento_abre_dato(self):
    path='ventas_ro/_privado/setter_extra/otro/setter_fixture'
    self.assertIsNotNone(self.ns['config_almacen'](path))
    code,d=self.get(path);self.assertEqual(code,200);self.assertEqual(d['valor'],'dato-sintetico')
    self.assertFalse(match_segmentos(path,'ventas_ro/_privado/setter_*'))
 def test_repro_agenda_extra_segmento_conserva_dueno_final(self):
    path='agenda/_privado/otra/persona/setter_fixture'
    self.assertIsNotNone(self.ns['config_almacen'](path))
    code,d=self.get(path);self.assertEqual(code,200);self.assertEqual(d['valor'],'dato-sintetico')
    self.assertFalse(match_segmentos(path,'agenda/_privado/*'))
 def test_almacenes_propios_legitimos_conservados(self):
    for path,patron in [('ventas_ro/_privado/setter_fixture','ventas_ro/_privado/setter_*'),('agenda/_privado/setter_fixture','agenda/_privado/*')]:
      self.assertTrue(match_segmentos(path,patron));self.assertEqual(self.get(path)[0],200)
 def test_dueño_setter_y_agenda_ajenos_denegados(self):
    for path in ('ventas_ro/_privado/setter_ajeno','agenda/_privado/ajeno'):
      self.assertEqual(self.get(path)[0],403)
 def test_segmentos_vacios_relativos_y_typed(self):
    for path in ('agenda/_privado//setter_fixture','agenda/_privado/../setter_fixture',None,[]):
      self.assertFalse(match_segmentos(path,'agenda/_privado/*'))
 def test_propuesta_no_cambia_politica_ni_exige_prefijo_p(self):
    for patron in P.REGLAS['almacenes_privados']:
      path=patron.replace('*','fixture')
      self.assertTrue(match_segmentos(path,patron))
    self.assertTrue(match_segmentos('agenda/_privado/p_fixture','agenda/_privado/*'))

class Campos586(unittest.TestCase):
 def setUp(self):self.f=F.Alias576();self.f.setUp()
 def cortar(self,rol,datos):
    p=next(p for p in self.f.personas if p['id']==rol)
    return self.f.ns['recortar_doc'](datos,self.f.ns['quitar_para'](p,P.contexto(p,self.f.crudo),'propio'))
 def test_inversion_autorizada_no_se_confunde_con_cuota_por_eur(self):
    x={k:7 for k in ('cpl_eur','gasto_eur','cpm','cpc','cuota_eur')}
    out=self.cortar('trafficker',x)
    self.assertEqual(set(out),{'cpl_eur','gasto_eur','cpm','cpc'})
    g={k:self.f.permiso('trafficker')(k) for k in ('cuota','inversion','cobros','dinero_empresa')}
    self.assertEqual(set(recortar_propuesta_583(x,g,contexto='cliente')),set(out))
 def test_repro_cpm_cpc_actuales_sin_inversion_permanecen(self):
    x={k:7 for k in ('cpl_eur','gasto_eur','cpm','cpc','cuota_eur')}
    self.assertFalse(self.f.permiso('account')('inversion'))
    self.assertEqual(set(self.cortar('account',x)),{'cpm','cpc'})
    self.assertEqual(familias_583('cpc'),frozenset()) # residuo propuesta, NO cierre
    self.assertEqual(familias_583('cpm'),frozenset({'inversion'}))
if __name__=='__main__':unittest.main()
