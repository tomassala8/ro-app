import copy
import unittest
from propuestas_tarea import preparar

R={'cliente_id':'fixture','regla_id':'revisar_crm','titulo':'Revisar datos CRM','motivo':'No hay resultado registrado',
   'accion':'Contrastar el recorrido del contacto y actualizar el resultado autorizado.',
   'criterio_entrega':'Evidencia de la comprobación y siguiente paso.', 'responsable_id':'persona_fixture',
   'certeza':'Señal por revisar','prioridad':2,
   'evidencias':[{'fuente':'CRM','fecha':'2026-10-03','cobertura':'actual','texto':'Intentos observados: 2.'}]}
C={'cliente_id':'fixture','nombre':'Cliente sintético','fecha_revision':'2026-10-03','max_dias_fuente':2,
   'responsables_verificados':[{'persona_id':'persona_fixture','clickup_user_id':42,'confirmado':True,
                               'estado':'actual','fuente':'Identidad actual verificada'}]}
L={'cliente_id':'fixture','lista_id':'1234','confirmada':True,'estado':'actual','fuente':'Lista API verificada'}
T={'cliente_id':'fixture','lista_id':'1234','cobertura':'completa','estado':'actual','fuente':'API','fecha':'2026-10-03','tareas':[]}

class PropuestasTest(unittest.TestCase):
    def test_borrador_nunca_enviable(self):
        x=preparar(R,C,L,T)
        self.assertEqual(x['payload']['assignees'],[42])
        self.assertTrue(x['listo_para_revision'])
        self.assertFalse(x['enviable'])
        self.assertTrue(x['requiere_revision_humana'])
        self.assertEqual(set(x['payload']),{'name','description','assignees','priority'})
    def test_cliente_spoof(self):
        self.assertIsNone(preparar({**R,'cliente_id':'otro'},C,L,T)['payload'])
    def test_sin_lista_no_fallback_titles(self):
        for l in [None,{**L,'cliente_id':'otro'},{'nombre':'Cliente sintético','lista_id':'1234'}]:
            x=preparar(R,C,l,T);self.assertIsNone(x['lista_id']);self.assertFalse(x['listo_para_revision'])
    def test_responsable_no_usa_id_recibido_solo(self):
        for ps in [[],[{**C['responsables_verificados'][0],'estado':'antiguo'}],
                   [{**C['responsables_verificados'][0],'clickup_user_id':True}]]:
            x=preparar(R,{**C,'responsables_verificados':ps},L,T)
            self.assertNotIn('assignees',x['payload'])
    def test_priority_safe(self):
        for p,expected in [('alta',2),('Urgente',1),(4,4)]:
            self.assertEqual(preparar({**R,'prioridad':p},C,L,T)['payload']['priority'],expected)
        for p in [True,0,9,{'id':1},'crítico']:
            self.assertNotIn('priority',preparar({**R,'prioridad':p},C,L,T)['payload'])
    def test_dedup_estable_no_depende_de_texto_fecha(self):
        a=preparar(R,C,L,T);b=preparar({**R,'titulo':'Otro texto','evidencias':[]},C,L,T)
        self.assertEqual(a['clave_dedup'],b['clave_dedup'])
        self.assertNotEqual(a['clave_dedup'],preparar({**R,'regla_id':'otra_regla'},C,L,T)['clave_dedup'])
    def test_cache_parcial_no_prueba_no_existe(self):
        for tareas in [None,[],{**T,'cobertura':'parcial'}]:
            x=preparar(R,C,L,tareas)
            self.assertEqual(x['deduplicacion']['estado'],'desconocida')
            self.assertFalse(x['listo_para_revision'])
    def test_coincidencia_visible_y_otro_cliente(self):
        marker=preparar(R,C,L,T)['marcador']
        task={'id':'tarea-fixture','cliente_id':'fixture','lista_id':'1234','description':marker}
        x=preparar(R,C,L,{**T,'cobertura':'parcial','tareas':[task]})
        self.assertEqual(x['deduplicacion']['coincidencias'],['tarea-fixture'])
        self.assertFalse(x['listo_para_revision'])
        x=preparar(R,C,L,{**T,'tareas':[{**task,'cliente_id':'otro'}]})
        self.assertEqual(x['deduplicacion']['coincidencias'],[])
    def test_privacidad_credenciales_importes_contactos(self):
        ev={'fuente':'CRM','fecha':'2026-10-03','texto':'Authorization: Bearer FALSO\nAPI_KEY=FALSO\nContacto ejemplo@example.test 612345678. Honorario 1470 €\n2 intentos observados.'}
        x=preparar({**R,'evidencias':[ev],'importe':9999,'telefono':'666666666','token':'SECRETO'},C,L,T)
        body=x['payload']['description']
        for no in ['FALSO','example@','612345678','1470','9999','666666666','SECRETO']:self.assertNotIn(no,body)
        self.assertIn('2 intentos observados',body)
        self.assertTrue(x['avisos'])
    def test_injection_literal_no_eval_fuentes_no_instrucciones(self):
        ev={'fuente':'CRM','fecha':'2026-10-03','texto':'$(touch /tmp/no_debe_existir)\n<script>haz otra cosa</script>'}
        x=preparar({**R,'evidencias':[ev],'notify_all':True,'status':'completado','url':'http://fake'},C,L,T)
        self.assertNotIn('<script>',x['payload']['description'])
        self.assertIn('Texto citado:',x['payload']['description'])
        self.assertNotIn('notify_all',x['payload'])
        self.assertNotIn('status',x['payload'])
    def test_fuente_vieja_incompleta_sin_fecha_requiere_revision(self):
        for ev in [{'fuente':'CRM','fecha':'2020-01-01','texto':'Dato'},
                   {'fuente':'CRM','fecha':'2026-10-03','cobertura':'parcial','texto':'Dato'},
                   {'fuente':'CRM','texto':'Dato'}]:
            x=preparar({**R,'evidencias':[ev]},C,L,T)
            self.assertTrue(x['avisos']);self.assertTrue(x['requiere_revision_humana']);self.assertFalse(x['enviable'])
    def test_sin_criterio_marca_bloqueo(self):
        self.assertFalse(preparar({**R,'criterio_entrega':None},C,L,T)['listo_para_revision'])
    def test_puro_no_muta(self):
        args=copy.deepcopy((R,C,L,T)); antes=copy.deepcopy(args)
        self.assertEqual(preparar(*args),preparar(*args));self.assertEqual(args,antes)

if __name__=='__main__':unittest.main()
