"""204 fixtures puros, sin datos reales/red/proveedores."""
import unittest
from identidades_clickup_204 import resolver, preparar_autorizacion, actor_autorizado
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import tempfile
import json
import types
import mi_trabajo as M
import config
from fuentes_verdad import clientes_activos as ACT

class Identidades204(unittest.TestCase):
    def p(self,**extra):return dict(id='person-fixture',nombre='Mismo Nombre',correo='owner@example.invalid',**extra)
    def u(self,**extra):return dict(id='provider-fixture',nombre='Mismo Nombre',email='owner@example.invalid',**extra)
    def test_esquema_real_correo_persona_email_proveedor(self):
        r=resolver([self.p()],[self.u()]);self.assertEqual(r['por_usuario'],{'provider-fixture':'person-fixture'})
        self.assertEqual(r['usuario_unico_por_persona'],{'person-fixture':'provider-fixture'})
    def test_nombres_pila_apellido_no_acreditan(self):
        for nombre in ['Mismo Nombre','Mismo','Mismo Nombre (agencia)']:
            u=self.u();u['email']=None;u['nombre']=nombre
            self.assertEqual(resolver([self.p()],[u])['por_usuario'],{})
    def test_claves_alternativas_soportadas_sin_elegir_contradictorias(self):
        p=self.p();p['email']=p.pop('correo');u=self.u();u['correo']=u.pop('email')
        self.assertEqual(len(resolver([p],[u])['por_usuario']),1)
        u['email']='other@example.invalid';self.assertEqual(resolver([p],[u])['por_usuario'],{})
    def test_normaliza_correo_completo_no_localpart(self):
        u=self.u();u['email']=' OWNER@EXAMPLE.INVALID ';self.assertEqual(len(resolver([self.p()],[u])['por_usuario']),1)
        u['email']='owner@other.invalid';self.assertEqual(resolver([self.p()],[u])['por_usuario'],{})
    def test_alias_canonical_explicito(self):
        p=self.p(otros_correos=['alias@example.invalid']);u=self.u();u['email']='alias@example.invalid'
        self.assertEqual(len(resolver([p],[u])['por_usuario']),1)
    def test_alias_canonical_sin_principal_no_se_ignora(self):
        p=self.p(otros_correos=['owner@example.invalid']);p.pop('correo')
        self.assertEqual(len(resolver([p],[self.u()])['por_usuario']),1)
    def test_correo_compartido_no_ultima_fila_gana(self):
        p2=self.p();p2['id']='other-person'
        self.assertEqual(resolver([self.p(),p2],[self.u()])['por_usuario'],{})
    def test_ids_duplicados_no_se_reinterpretan(self):
        p2=self.p();p2['correo']='other@example.invalid'
        self.assertEqual(resolver([self.p(),p2],[self.u()])['por_usuario'],{})
        u2=self.u();u2['email']='other@example.invalid'
        self.assertEqual(resolver([self.p()],[self.u(),u2])['por_usuario'],{})
    def test_varios_usuarios_no_destinatario_asignacion_inventado(self):
        u2=self.u();u2['id']='second-provider'
        r=resolver([self.p()],[self.u(),u2]);self.assertEqual(len(r['por_usuario']),2);self.assertEqual(r['usuario_unico_por_persona'],{})
    def test_no_deduce_actividad_ni_roles(self):
        r=resolver([self.p(estado='baja',puestos=['direccion'])],[self.u()])
        self.assertNotIn('puede_modificar',r);self.assertFalse(r['nombres_conceden_permiso'])
    def test_salida_no_correos_nombres_ni_textos_fuente(self):
        r=resolver([self.p()],[self.u()]);self.assertNotIn('@',str(r));self.assertNotIn('Mismo',str(r))
    def test_entradas_malformadas_sin_permisos(self):
        for p,u in [(None,None),([],[]),([{'id':'p','correo':True}],[self.u()]),([self.p(otros_correos='alias')],[self.u()])]:
            self.assertEqual(resolver(p,u)['por_usuario'],{})
    def test_duplicado_proveedor_identico_no_pierde_mapeo(self):
        self.assertEqual(len(resolver([self.p()],[self.u(),self.u()])['por_usuario']),1)

class Guardia204(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.p={'id':'owner','nombre':'Fixture','correo':'owner@example.invalid','estado':'activo','puestos':['paid'],'jefe':'boss'}
        self.boss={'id':'boss','correo':'boss@example.invalid','estado':'activo','puestos':['paid']}
        self.ops={'id':'ops','correo':'ops@example.invalid','estado':'activo','puestos':['operaciones']}
        self.ps=[self.p,self.boss,self.ops]
        self.users=[{'id':'cu-owner','email':'owner@example.invalid','nombre':'Fixture'}]
        self.raw={'id':'task-fixture','lista_id':'list-fixture','estado':'abierto','carpeta_id':'folder-fixture','asignados':[{'id':'cu-owner'}]}
        self.row={'id':'task-fixture','lista_id':'list-fixture','estado':'abierto','cli':'client-fixture','persona_id':'owner'}
        self.D={'generado':'fixture','tareas':[self.row]};self.permission=True;self.active=True
        self.s=types.SimpleNamespace(E=types.SimpleNamespace(crudo={'personas':self.ps,'clientes':[{'id':'client-fixture'}]}),ve_alguno=lambda*a:True)
        self.policy=types.SimpleNamespace(contexto=lambda*a:{},ver=lambda*a:{'ok':self.permission})
        self.patches=[patch.object(M,'S',self.s),patch.object(M,'P',self.policy),patch.object(M,'doc',lambda:self.D),
          patch.object(M,'AQUI',self.root),patch.object(M,'DATA',self.root/'data'),patch.object(config,'PANEL_OPERACIONES',self.root/'panel'),
          patch.object(ACT,'es_activo_id',lambda _:self.active)]
        for p in self.patches:p.start();self.addCleanup(p.stop)
        self.write(self.root/'fuentes_produccion/_privado/_cache/tareas.json',{'tareas':[self.raw]})
        self.write(self.root/'panel/_crudo/clickup/miembros.json',{'miembros':self.users})
        self.write(self.root/'data/clientes/client-fixture.json',{'id':'client-fixture','fuentes':{'tareas':{'datos':{'carpeta_id':'folder-fixture'}}}})
    def write(self,path,body):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(body))
    def test_autor_correo_actual_modifica(self):self.assertEqual(M.tarea_para_accion(self.p,'task-fixture'),self.row)
    def test_nombre_actual_sin_email_no_concede_modificacion(self):
        self.users[0]['email']=None;self.write(self.root/'panel/_crudo/clickup/miembros.json',{'miembros':self.users})
        with self.assertRaises(PermissionError):M.tarea_para_accion(self.p,'task-fixture')
        self.assertEqual(M.tarea_doc('task-fixture'),self.row)  # lectura histórica no eliminada.
    def test_persona_id_dto_forjado_no_es_autoria(self):
        self.row['persona_id']='other';self.assertEqual(M.tarea_para_accion(self.p,'task-fixture'),self.row)
        impostor={'id':'other','correo':'other@example.invalid','estado':'activo','puestos':['paid']};self.ps.append(impostor)
        with self.assertRaises(PermissionError):M.tarea_para_accion(impostor,'task-fixture')
    def test_jefe_canonico_solo_de_autor_confirmado(self):
        self.assertEqual(M.tarea_para_accion(self.boss,'task-fixture'),self.row)
        self.users[0]['email']=None;self.write(self.root/'panel/_crudo/clickup/miembros.json',{'miembros':self.users})
        with self.assertRaises(PermissionError):M.tarea_para_accion(self.boss,'task-fixture')
    def test_ops_canonico_politica_cartera_no_admin_payload(self):
        self.assertEqual(M.tarea_para_accion(self.ops,'task-fixture'),self.row)
        with self.assertRaises(PermissionError):M.tarea_para_accion(dict(self.p,puestos=['direccion'],id='not-real'),'task-fixture')
        self.permission=False
        with self.assertRaises(PermissionError):M.tarea_para_accion(self.ops,'task-fixture')
    def test_ops_canonico_no_necesita_autoria_por_correo_para_politica_admin(self):
        self.users[0]['email']=None;self.write(self.root/'panel/_crudo/clickup/miembros.json',{'miembros':self.users})
        self.assertEqual(M.tarea_para_accion(self.ops,'task-fixture'),self.row)
        with self.assertRaises(PermissionError):M.tarea_para_accion(self.boss,'task-fixture')
    def test_actor_payload_roles_no_sustituye_canonico(self):
        other={'id':'other','correo':'other@example.invalid','estado':'activo','puestos':['paid']};self.ps.append(other)
        with self.assertRaises(PermissionError):M.tarea_para_accion(dict(other,puestos=['direccion']),'task-fixture')
    def test_cliente_activo_y_fuente_carpeta_incoherente_denegados(self):
        self.active=False
        with self.assertRaises(PermissionError):M.tarea_para_accion(self.ops,'task-fixture')
        self.active=True;self.row['cli']=None
        with self.assertRaises(ValueError):M.tarea_para_accion(self.ops,'task-fixture')
    def test_raw_task_lista_estado_duplicado_fail_closed(self):
        for rows in [[dict(self.raw,lista_id='other')],[dict(self.raw,estado='otro')],[self.raw,self.raw]]:
            self.write(self.root/'fuentes_produccion/_privado/_cache/tareas.json',{'tareas':rows})
            with self.assertRaises(ValueError):M.tarea_para_accion(self.p,'task-fixture')
    def test_carpeta_directa_duplicada_no_lastwins(self):
        self.write(self.root/'data/clientes/duplicate.json',{'id':'other-client','fuentes':{'tareas':{'datos':{'carpeta_id':'folder-fixture'}}}})
        with self.assertRaises(ValueError):M.tarea_para_accion(self.ops,'task-fixture')
    def test_fuentes_ausentes_malformadas_no_token(self):
        cache=self.root/'fuentes_produccion/_privado/_cache/tareas.json';cache.unlink()
        with self.assertRaises(ValueError):M.tarea_para_accion(self.ops,'task-fixture')
        self.write(cache,{'tareas':[self.raw]});self.write(self.root/'data/clientes/client-fixture.json',{'id':'client-fixture','fuentes':'malformado'})
        with self.assertRaises(ValueError):M.tarea_para_accion(self.ops,'task-fixture')
    def test_post_relee_identidad_no_cross_request_cache(self):
        M.tarea_para_accion(self.p,'task-fixture')
        self.write(self.root/'panel/_crudo/clickup/miembros.json',{'miembros':[{'id':'cu-owner','email':'another@example.invalid'}]})
        with self.assertRaises(PermissionError):M.tarea_para_accion(self.p,'task-fixture')
    def test_indice_por_request_no_reabre_fuentes_por_fila(self):
        evidence=M._fuente_autorizacion_tareas()
        index={'actor':[self.p],'modulo':True,'filas':{'task-fixture':[self.row]},'identidad_fuente':evidence,'cliente_autorizado':lambda _:True}
        with patch.object(M,'_fuente_autorizacion_tareas',side_effect=AssertionError('No releer cada fila')):
            for _ in range(10):self.assertEqual(M.tarea_para_accion(self.p,'task-fixture',indice=index),self.row)
    def test_autor_baja_no_jefe_grant_por_historia(self):
        self.p['estado']='baja'
        with self.assertRaises(PermissionError):M.tarea_para_accion(self.boss,'task-fixture')
    def test_asignados_raw_duplicados_rechazados(self):
        self.raw['asignados']*=2;self.write(self.root/'fuentes_produccion/_privado/_cache/tareas.json',{'tareas':[self.raw]})
        with self.assertRaises(ValueError):M.tarea_para_accion(self.p,'task-fixture')

if __name__=='__main__':unittest.main()

