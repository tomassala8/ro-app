"""Fixtures sintéticas + hook real AST. No imports de productor/servidor ni red."""
import datetime as dt
import ast,copy,hashlib,json,os,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
def localizar_app():
 explicit=os.environ.get('RO_APP_681')
 if explicit:
  p=Path(explicit).resolve()
  if not (p/'servir.py').is_file():raise RuntimeError('APP explícita no válida')
  return p
 for p in (HERE,*HERE.parents):
  if (p/'servir.py').is_file():return p
  if (p/'30_APP_PROTOTIPO/servir.py').is_file():return p/'30_APP_PROTOTIPO'
 return None
APP=localizar_app()
INTEGRADO=APP is not None and (APP/'controlador_planning_681.py').is_file()
SOURCE=APP if INTEGRADO else HERE.parent
if not (SOURCE/'controlador_planning_681.py').is_file():raise RuntimeError('Falta fuente candidata o integrada681')
sys.path.insert(0,str(SOURCE))
from planning_transiciones_681 import enriquecer_produccion681,KEY
from controlador_planning_681 import conectar_produccion681
from lector_planning_681 import leer_planning681
D='2026-09-27T22:00:00Z';C='2026-10-03T12:00:00Z';NOW='2026-10-04T12:00:00Z'
CAT={'listFixture':[{'nombre':n,'tipo':'open'} for n in ('backlog','planning mensual','planning semanal','diario','en curso')]}
def task(tid='taskFixture',initial='backlog',creator='creatorFixture',cid='clientFixture',complete=False):
 return {'task_id':tid,'list_id':'listFixture','cliente_id':cid,'creada':'2026-09-28T08:00:00Z','creador_id':creator,'estado_inicial':initial,'fuente_creacion':'clickup','historial':{'completo':complete,'desde_creacion':complete,'hasta':C},'fuego':{'confirmado':False,'fuente':'clasificacion_confirmada','instante':'2026-09-28T08:00:00Z'}}
def event(tid='taskFixture',eid='eventFixture',old='backlog',new='planning mensual',stamp='2026-09-28T09:00:00Z',actor='actorFixture',cid='clientFixture',source='clickup'):
 return {'event_id':eid,'task_id':tid,'list_id':'listFixture','cliente_id':cid,'actor_id':actor,'estado_anterior':old,'estado_nuevo':new,'instante':stamp,'fuente':source}
def payload(tasks=None,events=None):
 return {'registro':{'version':'681.1','fuente':'eventos_clickup_observados','corte':C,'tareas':tasks if tasks is not None else [task()],'eventos':events if events is not None else [event()]},'catalogo':copy.deepcopy(CAT),'desde':D,'hasta':C,'corte':C}
def dto():return {'proyectos':[{'cliente_id':'clientFixture','no_planificadas':99}], 'personas':[{'persona_id':'creatorFixture','creadas':7},{'persona_id':'actorFixture','creadas':4}], 'fuentes':{'flujo':{'hora':'2026-10-02 10:00'}}}
def scope():return {'produccion_real':True,'produccion_vista':True,'firma':'a'*64,**{k:{'clientFixture'} for k in ('clientes_real','clientes_vista','clientes_ACT')},**{k:{'creatorFixture','actorFixture'} for k in ('actores_real','actores_vista','actores_activos')}}
class Permissions:
 def __init__(self):self.denied=set()
 def contexto(self,p,core):return {}
 def ver(self,p,obj,cp):return {'ok':(p['id'],obj['tipo'],obj.get('cliente_id',obj.get('persona_id'))) not in self.denied}
class Server:
 def __init__(self):
  self.real={'id':'realFixture','estado':'activo','puestos':['operaciones']};self.view={'id':'viewFixture','estado':'activo','puestos':['account']}
  self.E=types.SimpleNamespace(nucleo_bloqueado=False,crudo={'personas':[copy.deepcopy(self.real),copy.deepcopy(self.view),{'id':'creatorFixture','estado':'activo','puestos':['tecnico']},{'id':'actorFixture','estado':'activo','puestos':['tecnico']}],'clientes':[{'id':'clientFixture','estado':'activo'},{'id':'outsideFixture','estado':'activo'}]})
  self.P=Permissions();self.active={'clientFixture'};self.ACT=types.SimpleNamespace(es_activo_id=lambda cid:cid in self.active);self.level='todo'
 def ve_alguno(self,p,mods):return self.level
class Tests681(unittest.TestCase):
 def apply(self,p=None,sc=None,ok=lambda _:True):
  p=p or payload();return enriquecer_produccion681(dto(),p['registro'],p['catalogo'],sc or scope(),p['desde'],p['hasta'],p['corte'],ok)
 def test_606_previamente_desconectado(self):
  app=APP
  if app is not None and app.exists():self.assertNotIn('transiciones_observadas_606',(app/'fuentes_produccion/generar_produccion.py').read_text())
  self.assertNotIn(KEY,dto()['personas'][0]);self.assertEqual(self.apply()['personas'][0][KEY]['metricas']['al_planning'],1)
 def test_asignado_actual_no_actor_ni_creador(self):
  r=self.apply();self.assertEqual(r['personas'][0][KEY]['metricas']['al_planning'],1);self.assertIsNone(r['personas'][1][KEY]['metricas']['al_planning']);self.assertEqual(r['personas'][0]['creadas'],7)
 def test_salto_sin_cadena_completa_no_ruptura(self):
  p=payload(events=[event(new='planning semanal')]);self.assertIsNone(self.apply(p)['personas'][0][KEY]['metricas']['rompen_semanal'])
 def test_ruptura_solo_cadena_y_clasificacion(self):
  p=payload(tasks=[task(complete=True)],events=[event(new='planning semanal')]);self.assertEqual(self.apply(p)['personas'][0][KEY]['metricas']['rompen_semanal'],1)
  p['registro']['tareas'][0].pop('fuego');self.assertIsNone(self.apply(p)['personas'][0][KEY]['metricas']['rompen_semanal'])
 def test_fuego_confirmado_separado_de_rojo(self):
  p=payload(tasks=[task(complete=True)],events=[event(new='planning semanal')]);p['registro']['tareas'][0]['fuego']['confirmado']=True;r=self.apply(p)['personas'][0][KEY]['metricas'];self.assertEqual(r['fuegos_directos'],1);self.assertIsNone(r['rompen_semanal'])
 def test_snapshot395_no_historificar(self):
  p=payload();p['registro']={'version':'395.1','fuente':'clickup_cache_local','filas':[{'estado':'planning semanal','estado_inicial':None}]};self.assertEqual(self.apply(p),dto())
 def test_intencion208_no_evento(self):
  p=payload(events=[event(source='app_pendiente')]);r=self.apply(p)['personas'][0][KEY];self.assertTrue(all(x is None for x in r['metricas'].values()));self.assertEqual(r['tareas_observadas'],0)
 def test_vacio_no_cero_completo(self):
  p=payload(tasks=[],events=[]);r=self.apply(p)['personas'][0][KEY];self.assertTrue(all(x is None for x in r['metricas'].values()));self.assertIsNone(r['creadas_observadas']);self.assertIs(r['inventario_completo'],False)
 def test_ausente_y_metadatos_obsoletos_no_reviven(self):
  r=dto();r['personas'][0][KEY]={'metricas':{'al_planning':99}};out=enriquecer_produccion681(r,None,CAT,scope(),D,C,C,lambda _:True);self.assertNotIn(KEY,out['personas'][0]);self.assertEqual(out['personas'][0]['creadas'],7)
 def test_cliente_actor_revocados_no_positivos(self):
  for k in ('clientes_real','clientes_vista','clientes_ACT','actores_real','actores_vista','actores_activos'):
   sc=scope();sc[k]=set();self.assertEqual(self.apply(sc=sc),dto())
 def test_duplicado_id_global_fuera_scope_invalida(self):
  p=payload(events=[event(),event(tid='outsideTask',cid='outsideFixture')]);self.assertIsNone(self.apply(p)['personas'][0][KEY]['metricas']['al_planning'])
 def test_catalogo_ambiguo_tiempo_futuro_y_corte(self):
  for change in ('cat','future','cut'):
   p=payload()
   if change=='cat':p['catalogo']['listFixture'].append(p['catalogo']['listFixture'][0])
   if change=='future':p['registro']['eventos'][0]['instante']='2026-10-04T12:00:00Z'
   if change=='cut':p['registro']['corte']='2026-10-02T12:00:00Z'
   r=self.apply(p);self.assertTrue(KEY not in r['personas'][0] or r['personas'][0][KEY]['metricas']['al_planning'] is None)
 def test_no_mutacion_ni_PII_evento_en_DTO(self):
  p=payload();p['registro']['eventos'][0]['token']='syntheticprivate';before=copy.deepcopy(p);r=self.apply(p);self.assertEqual(p,before);s=json.dumps(r);self.assertNotIn('syntheticprivate',s);self.assertNotIn('eventFixture',s);self.assertNotIn('taskFixture',s);self.assertEqual(r['proyectos'][0]['no_planificadas'],99)
 def test_revalidar_despues_proyeccion(self):
  n=[0]
  def ok(_):n[0]+=1;return n[0]<2
  self.assertEqual(self.apply(ok=ok),dto())
 def controller(self,S=None,reader=None,p=None,enabled=True):
  S=S or Server();return conectar_produccion681(dto(),S,S.real,S.view,reader or (lambda:p or payload()),NOW,enabled)
 def test_controller_off_cero_IO(self):
  calls=[];r=self.controller(reader=lambda:calls.append(True),enabled=False);self.assertEqual(r,dto());self.assertEqual(calls,[])
 def test_controller_actual_grants_y_roles(self):
  for alter in ('roles','duplicate','activo','module','grant','ACT'):
   S=Server();calls=[]
   if alter=='roles':S.real['puestos']=['seo']
   if alter=='duplicate':S.E.crudo['personas'].append(copy.deepcopy(S.E.crudo['personas'][0]))
   if alter=='activo':S.E.crudo['personas'][0]['activo']=False
   if alter=='module':S.level=True
   if alter=='grant':S.P.denied.add(('realFixture','cliente_detalle','clientFixture'))
   if alter=='ACT':S.active.clear()
   self.assertIsNone(self.controller(S,lambda:calls.append(True)));self.assertEqual(calls,[])
 def test_controller_revoke_durante_lector(self):
  S=Server()
  def read():S.active.clear();return payload()
  self.assertIsNone(self.controller(S,read))
 def test_controller_fuente_rota_no_500_ni_cero(self):
  def read():raise ValueError('no divulgar detalles')
  self.assertEqual(self.controller(reader=read),dto());self.assertEqual(self.controller(p=payload(events=[]))['personas'][0][KEY]['metricas']['al_planning'],None)
 def test_reader_privado_pin_modo_symlink_json_duplicado(self):
  with tempfile.TemporaryDirectory() as d:
   d=str(Path(d).resolve())
   p=Path(d)/'sidecar.json';os.chmod(d,0o700);raw=json.dumps(payload()).encode();p.write_bytes(raw);os.chmod(p,0o600);sha=hashlib.sha256(raw).hexdigest();self.assertEqual(leer_planning681(str(p),sha),payload())
   with self.assertRaises(ValueError):leer_planning681(str(p),'0'*64)
   os.chmod(p,0o644)
   with self.assertRaises(ValueError):leer_planning681(str(p),sha)
   os.chmod(p,0o600);link=Path(d)/'link.json';link.symlink_to(p)
   with self.assertRaises(OSError):leer_planning681(str(link),sha)
   for raw in (b'{"x":1,"x":2}',b'{"x":NaN}'):
    p.write_bytes(raw)
    with self.assertRaises(ValueError):leer_planning681(str(p),hashlib.sha256(raw).hexdigest())
 def test_reader_json_profundo_controller_preserva_primario(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d).resolve()/'sidecar.json';os.chmod(p.parent,0o700);raw=('['*2000+'0'+']'*2000).encode();p.write_bytes(raw);os.chmod(p,0o600);pin=hashlib.sha256(raw).hexdigest()
   # El límite de profundidad de json.loads varía por versión Python.
   # El contrato es conservar el primario sin500, acepte o rechace el parser.
   self.assertEqual(self.controller(reader=lambda:leer_planning681(str(p),pin)),dto())
 def test_reader_exponente_no_finito_preserva_primario(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d).resolve()/'sidecar.json';os.chmod(p.parent,0o700)
   for raw in (b'{"dato":1e400}',b'{"dato":-1e400}'):
    p.write_bytes(raw);os.chmod(p,0o600);pin=hashlib.sha256(raw).hexdigest()
    with self.assertRaises(ValueError):leer_planning681(str(p),pin)
    self.assertEqual(self.controller(reader=lambda:leer_planning681(str(p),pin)),dto())
 def test_controller_lector_recursion_directa_no_500(self):
  def read():raise RecursionError('detalle privado sintético')
  self.assertEqual(self.controller(reader=read),dto())
 def test_parser_recursion_controlada_no_500(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d).resolve()/'sidecar.json';os.chmod(p.parent,0o700);raw=b'{}';p.write_bytes(raw);os.chmod(p,0o600);pin=hashlib.sha256(raw).hexdigest()
   with patch('lector_planning_681.json.loads',side_effect=RecursionError('sintético')):
    with self.assertRaisesRegex(ValueError,'Profundidad no válida'):leer_planning681(str(p),pin)
    self.assertEqual(self.controller(reader=lambda:leer_planning681(str(p),pin)),dto())
 def test_json_objeto_profundo_controller_preserva(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d).resolve()/'sidecar.json';os.chmod(p.parent,0o700);raw=('{"x":'*2000+'0'+'}'*2000).encode();p.write_bytes(raw);os.chmod(p,0o600);pin=hashlib.sha256(raw).hexdigest()
   self.assertEqual(self.controller(reader=lambda:leer_planning681(str(p),pin)),dto())
 def test_creacion_mensual_explicita_no_fingir_transicion(self):
  p=payload(tasks=[task(initial='planning mensual')],events=[]);r=self.apply(p)['personas'][0][KEY];self.assertEqual(r['metricas']['al_planning'],1);self.assertFalse(r['inventario_completo']);self.assertIsNone(r['metricas']['rompen_semanal'])
 def test_cliente_duplicado_y_registro_truncado_no_agregado(self):
  r=dto();r['proyectos'].append(copy.deepcopy(r['proyectos'][0]));p=payload();self.assertEqual(enriquecer_produccion681(r,p['registro'],CAT,scope(),D,C,C,lambda _:True),r)
  p['registro']['tareas'].append(copy.deepcopy(p['registro']['tareas'][0]));self.assertIsNone(self.apply(p)['personas'][0][KEY]['metricas']['al_planning'])
 def test_hook_modulo_recortado_AST_antes_despues(self):
  S=Server();S.ACT.quitar_bajas=lambda obj,rel:obj;sys.modules['fixture_server_681']=S
  with tempfile.TemporaryDirectory() as d:
   d=str(Path(d).resolve())
   path=Path(d)/'sidecar.json';os.chmod(d,0o700);raw=json.dumps(payload()).encode();path.write_bytes(raw);os.chmod(path,0o600)
   class Clock(dt.datetime):
    @classmethod
    def now(cls,tz=None):return cls.fromisoformat(NOW.replace('Z','+00:00')).astimezone(tz)
   environment={'RO_PLANNING_TRANSICIONES_681':str(path),'RO_SHA_PLANNING_TRANSICIONES_681':hashlib.sha256(raw).hexdigest()}
   outputs=[]
   for file in ('servir_hooks_681_AST.py','servir_hooks_681_candidato_AST.py'):
    source_path=(HERE/file) if file=='servir_hooks_681_AST.py' else (APP/'servir.py' if INTEGRADO else SOURCE/'servir_hooks_681_candidato_AST.py')
    tree=ast.parse(source_path.read_text());func=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='modulo_recortado')
    if file!='servir_hooks_681_AST.py':self.assertIn('PLANNING_681.enriquecer681',ast.unparse(func))
    ns={'__name__':'fixture_server_681','sys':sys,'ACT':S.ACT,'puerta_modulo':lambda *args,**kw:{'fichero':types.SimpleNamespace(exists=lambda:True),'conf':{},'nivel':'todo'},'leer_json_bueno':lambda _:({'fuente_no_autorizada':'outsideFixture'},None),'modulo_vigente_581':lambda *args:True,'recortar_modulo':lambda *args: dto(),'EVIDENCIA_PRODUCCION_287':types.SimpleNamespace(enriquecer287=lambda obj,*args:obj)}
    exec(compile(ast.Module(body=[func],type_ignores=[]),'<realHook681>','exec'),ns)
    with patch.dict(os.environ,environment,clear=True),patch('datetime.datetime',Clock):outputs.append(ns['modulo_recortado'](S.real,S.view,{},'produccion/produccion'))
   self.assertNotIn(KEY,outputs[0]['personas'][0]);self.assertEqual(outputs[1]['personas'][0][KEY]['metricas']['al_planning'],1);self.assertNotIn('outsideFixture',json.dumps(outputs[1]))
if __name__=='__main__':unittest.main()
