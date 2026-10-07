"""Auditoría133: funciones reales con base SQLite y rutas privadas temporales; no servidor/red."""
import copy,json,os,sqlite3,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import altas_personas as A
import permisos as P
import contratos_privados as C
from despliegue import acceso_cf as CF

class Miembros(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.raiz=Path(self.tmp.name).resolve();self.db=self.raiz/'estado.sqlite'
  self.env=patch.dict(os.environ,{'RO_DB':str(self.db),'RO_CORREOS_ENTRADA':str(self.raiz/'correos.json'),'RO_LISTA_ACCESS':str(self.raiz/'access.txt'),'RO_DEPARTAMENTOS':str(self.raiz/'departamentos.json'),'RO_RELOJ':'2026-10-03T10:00'});self.env.start()
  def per(id,puestos,jefe='tomas'):return {'id':id,'alias':id,'nombre':id.title()+' Prueba','puestos':puestos,'jefe':jefe,'estado':'activo','activo':True,'zona':'Europe/Madrid','imputa_horas':True,'horas_mes':128}
  self.base={'personas':[per('tomas',['direccion'],None),per('mili',['operaciones']),per('cecilia',['rrhh']),per('anterior',['account'],'mili'),per('receptor',['account'],'mili')], 'clientes':[{'id':'c','nombre':'Cliente sintético','servicios':{}},{'id':'ajeno','nombre':'Otro sintético','servicios':{}}], 'asignaciones':[{'cliente_id':'c','persona_id':'anterior','silla':'account','principal':True,'desde':'2020-01-01','hasta':None}], 'logos':{},'alarmas':[],'meta':{}}
  self.E=NS(crudo=copy.deepcopy(self.base),modulos={});self.E.persona=lambda pid:next((p for p in self.E.crudo['personas'] if p['id']==pid),None)
  def conectar():
   c=sqlite3.connect(self.db);c.row_factory=sqlite3.Row;return c
  self.conectar=conectar
  with conectar() as c:c.execute('CREATE TABLE historial(n INTEGER PRIMARY KEY AUTOINCREMENT,quien TEXT,coleccion TEXT,id TEXT,operacion TEXT,antes TEXT,datos TEXT)');c.executescript(A.TABLA_SQL)
  def recargar(*a):
   self.E.crudo=copy.deepcopy(self.base)
   with conectar() as c:
    for r in c.execute('SELECT * FROM historial ORDER BY n'):
     d=json.loads(r['datos']);arr=self.E.crudo[r['coleccion']]
     if r['operacion']=='crear':arr.append({**d,**({'id':r['id']} if r['coleccion']=='personas' else {})})
     else:
      for x in arr:
       if (r['coleccion']=='personas' and x['id']==r['id']) or (r['coleccion']=='asignaciones' and all(x.get(k)==d.get(k) for k in ('cliente_id','persona_id','silla'))):x.update(d)
  self.E.recargar_personas=recargar
  self.S=NS(E=self.E,P=P,conectar=conectar,ahora=lambda:'2026-10-03T10:00:00',registrar=lambda *a,**k:None,registrar_agrupado=lambda *a,**k:None,pedir_recarga=lambda *a:None)
  self.before=(A.S,A.P);A.S=self.S;A.P=P
  self.h=NS(responder=lambda status,data:(status,data))
 def tearDown(self):A.S,A.P=self.before;self.env.stop();self.tmp.cleanup()
 def post(self,ruta,b,actor='mili',como=None):return A.post(self.h,'/api/altas/'+ruta,self.E.persona(actor),self.E.persona(como or actor),b)
 def alta(self,**extra):
  b={'nombre':'Zoe Sintetica','puestos':['account'],'jefe':'mili','zona':'Europe/Madrid','correo_entrada':'fixture1@rankingonline.com','cartera':[{'cliente_id':'c','silla':'account','papel':'responsable'}]};b.update(extra);return self.post('alta',b)
 def test_alta_sqlite_comprobacion_access_pendiente(self):
  status,r=self.alta();self.assertEqual(status,200);self.assertTrue(self.E.persona(r['id'])['activo']);self.assertTrue(r['comprobacion']['todo_bien']);self.assertEqual(r['asignaciones'],1)
  tasks=A.tareas_de(r['id']);self.assertEqual(tasks[0]['tipo'],'access_anadir');self.assertEqual(tasks[0]['estado'],'pendiente');self.assertIn('zoe.sintetica@',Path(A.ruta_lista()).read_text())
  self.assertFalse(P.ver(self.E.persona(r['id']),{'tipo':'cliente_detalle','cliente_id':'ajeno'},P.contexto(self.E.persona(r['id']),self.E.crudo))['ok'])
 def test_mando_autoedicion_viewas_y_datos_ajenos(self):
  self.assertEqual(self.alta(puestos=['rrhh'])[0],403);self.assertEqual(self.post('baja',{'id':'mili'})[0],403);self.assertEqual(self.post('alta',{},como='anterior')[0],403)
  self.assertEqual(self.alta(phone='+34000000000')[0],400);self.assertEqual(self.alta(sueldo=999)[0],400);self.assertEqual(self.alta(correo_entrada='persona@ejemplo.com')[0],403)
 def test_zona_propia_y_ajena_y_viewas(self):
  p=self.E.persona('anterior');r=A.cambiar_zona(p,p,{'zona':'America/Bogota'});self.assertEqual(r[0],200);self.assertEqual(self.E.persona('anterior')['zona'],'America/Bogota')
  self.assertEqual(A.cambiar_zona(self.E.persona('receptor'),self.E.persona('receptor'),{'id':'anterior','zona':'America/Lima'})[0],403)
  self.assertEqual(A.cambiar_zona(self.E.persona('tomas'),p,{'zona':'America/Lima'})[0],403)
  self.assertEqual(A.cambiar_zona(p,p,{'zona':'No/Existe'})[0],400)
 def test_baja_cierra_asignacion_y_revoca_match_local(self):
  _,r=self.alta();pid=r['id'];self.assertEqual(self.post('baja',{'id':pid})[0],200);self.assertEqual(self.E.persona(pid)['estado'],'baja');self.assertNotIn(pid,A.leer_correos()['correos']);self.assertNotIn('zoe.sintetica@', '\n'.join(x for x in A.ruta_lista().read_text().splitlines() if not x.startswith('#')))
  self.assertFalse(any(x['persona_id']==pid and not x.get('hasta') for x in self.E.crudo['asignaciones']));self.assertTrue(any(x['tipo']=='access_quitar' for x in A.tareas_de(pid)))
 def test_repartir_replay_no_duplica_y_sustituye_responsable(self):
  body={'filas':[{'cliente_id':'c','silla':'account','persona_id':'receptor'}]}
  self.assertEqual(self.post('repartir',body)[0],200);status,r=self.post('repartir',body);self.assertEqual(status,200);self.assertTrue(r['sin_cambios'])
  with self.conectar() as c:n=c.execute("SELECT count(*) FROM historial WHERE coleccion='asignaciones' AND operacion='crear'").fetchone()[0]
  self.assertEqual(n,1)
  actuales=[x for x in self.E.crudo['asignaciones'] if not x.get('hasta') and x.get('principal',True)]
  self.assertEqual([x['persona_id'] for x in actuales],['receptor'])
 def test_correo_fallo_informa_pendiente_y_reintento_no_duplica(self):
  with patch.object(A,'escribir_correos',side_effect=OSError('fallo_sintetico')):
   status,r=self.alta()
  self.assertEqual(status,200);self.assertTrue(r['alta_guardada']);self.assertEqual(r['estado'],'guardada_con_pendientes');self.assertIn('correo_entrada',r['pendientes_locales']);self.assertEqual(r['access_externo'],'pendiente')
  status,reintento=self.alta();self.assertEqual(status,200);self.assertEqual(reintento['id'],r['id']);self.assertEqual(reintento['pendientes_locales'],[])
  with self.conectar() as c:
   self.assertEqual(c.execute("SELECT count(*) FROM historial WHERE coleccion='personas' AND operacion='crear'").fetchone()[0],1);self.assertEqual(c.execute("SELECT count(*) FROM altas_tareas WHERE tipo='access_anadir'").fetchone()[0],1)
  self.assertEqual(A.leer_correos()['correos'][r['id']],'fixture1@rankingonline.com')
 def test_contratos_nominal_real_vista(self):
  self.assertTrue(C.permitido({'id':'tomas'},{'id':'tomas'}));self.assertFalse(C.permitido({'id':'mili','puestos':['direccion']},{'id':'tomas'}));self.assertFalse(C.permitido({'id':'tomas'},{'id':'cecilia'}))
 def test_sueldos_nominal_y_doble_vista(self):
  P.recargar_reglas()
  for tipo in ('sueldos','sueldo'):
   for id,roles,ok in [('tomas',['direccion'],True),('cecilia',['rrhh'],True),('otra_rrhh',['rrhh'],False),('otra_direccion',['direccion'],False),('cecilia',['account'],False)]:
    persona={'id':id,'puestos':roles};self.assertEqual(P.ver(persona,{'tipo':tipo},P.contexto(persona,self.E.crudo))['ok'],ok)
   with P.mirando_como(self.E.persona('mili'),self.E.crudo):self.assertFalse(P.ver(self.E.persona('cecilia'),{'tipo':tipo},P.contexto(self.E.persona('cecilia'),self.E.crudo))['ok'])
   with P.mirando_como(self.E.persona('tomas'),self.E.crudo):self.assertTrue(P.ver(self.E.persona('cecilia'),{'tipo':tipo},P.contexto(self.E.persona('cecilia'),self.E.crudo))['ok'])
 def test_identidad_nominal_no_reutilizable_y_admin_solo_tomas(self):
  # La ausencia de un titular en el snapshot no libera su identificador privilegiado.
  self.base['personas']=[p for p in self.base['personas'] if p['id']!='cecilia'];self.E.crudo=copy.deepcopy(self.base)
  status,r=self.post('alta',{'nombre':'Cecilia Sintetica','puestos':['rrhh'],'jefe':'tomas','zona':'Europe/Madrid'},actor='tomas')
  self.assertEqual(status,200);self.assertNotEqual(r['id'],'cecilia');nueva=self.E.persona(r['id'])
  self.assertFalse(P.ver(nueva,{'tipo':'sueldos'},P.contexto(nueva,self.E.crudo))['ok'])
  self.assertFalse(A.es_tomas({'id':'otra_direccion','puestos':['direccion']}));self.assertFalse(A.es_tomas({'id':'tomas','puestos':['account']}));self.assertTrue(A.es_tomas({'id':'tomas','puestos':['direccion']}))
  otra={'id':'otra_direccion','alias':'Otra','nombre':'Otra Dirección','puestos':['direccion'],'estado':'activo','activo':True,'jefe':None};self.base['personas'].append(otra);self.E.crudo['personas'].append(otra)
  self.assertEqual(self.post('alta',{'nombre':'Nueva Sintetica','puestos':['rrhh'],'jefe':'tomas','zona':'Europe/Madrid'},actor='otra_direccion')[0],403)
  # El slug Tomás está reservado incluso si el actor no pertenece al snapshot.
  titular=self.E.persona('tomas');self.base['personas']=[p for p in self.base['personas'] if p['id']!='tomas'];self.E.crudo=copy.deepcopy(self.base)
  status,r=A.post(self.h,'/api/altas/alta',titular,titular,{'nombre':'Tomas Sintetico','puestos':['direccion'],'zona':'Europe/Madrid'})
  self.assertEqual(status,200);self.assertNotEqual(r['id'],'tomas');self.assertFalse(C.permitido(self.E.persona(r['id']),self.E.persona(r['id'])))
 def test_leads_cartera_solo_desenmascarable_propia(self):
  _,r=self.alta();persona=self.E.persona(r['id']);cp=P.contexto(persona,self.E.crudo)
  propio=P.ver(persona,{'tipo':'lead','cliente_id':'c'},cp);ajeno=P.ver(persona,{'tipo':'lead','cliente_id':'ajeno'},cp)
  self.assertTrue(propio['ok']);self.assertTrue(propio.get('desenmascarable'));self.assertFalse(ajeno.get('desenmascarable',False))
 def test_access_sin_sello_failclosed_sinred(self):
  with patch.dict(os.environ,{'RO_MODO':'servidor'}),patch.object(CF,'_cargar_claves',side_effect=AssertionError('red prohibida')):
   self.assertTrue(CF.activo());self.assertIsNone(CF.correo_validado({'X-RO-Yo':'tomas'})[0])
if __name__=='__main__':unittest.main()
