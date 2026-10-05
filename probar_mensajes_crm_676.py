"""Portable AST real producer branches, fake transport only; no main/imports."""
import ast
from copy import deepcopy
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
import unittest
from zoneinfo import ZoneInfo
HERE=Path(__file__).resolve().parent
BASE=HERE/'fixture_mensajes_crm_676.py';NEW=HERE/'fuentes_crm/generar_crm.py'
NOW=dt.datetime(2026,10,4,12,tzinfo=ZoneInfo('Europe/Madrid'));CUT=int(NOW.timestamp()*1000);START=CUT-4*86400000

def cargar(p):
    tree=ast.parse(p.read_text());ns={'dt':dt,'math':math,'re':re,'json':json,'hashlib':hashlib,'HOY':NOW,'MAD':ZoneInfo('Europe/Madrid'),'AHORA_MS':CUT,'VENTANA_LEADS':30,'EXCLUSIONES':{},'GHL_WEB':'https://example.invalid'}
    names={'inicio_dia','iso_ms','timestamp_mensaje','resumir_intentos','intentos_medidos672','clasificar','leer_subcuenta','fecha_mensaje676','normalizar_mensajes676','conflictos_globales676','canal_observado676','respuesta_publica676','sin_tocar_publico676','ms_iso','pct','ref_de'};consts={'MEDIOS_LEAD','MEDIOS_NO','RX_PRUEBA','RX_NO_LEAD','RX_LANDING','RX_CORREO_PRUEBA','COMUNICACION','AUTOMATICO'}
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in consts for t in n.targets)];exec(compile(ast.Module(body=nodes,type_ignores=[]),'<AST676>','exec'),ns);ns['tree']=tree;return ns

def msg(**kw):return {'id':'msgFixture','dateAdded':START+60000,'messageType':'TYPE_EMAIL','direction':'inbound','source':'app','status':'received','contactId':'contactFixture',**kw}
def paquetes(*rows):return [{'mensaje':x,'contacto_conversacion':'contactFixture','conversacion_id':'conversationFixture'} for x in rows]

class Fake:
    def __init__(self,rows,cv_error=False,msg_error=False,creado=START,contacto='contactFixture'):self.rows=rows;self.cv_error=cv_error;self.msg_error=msg_error;self.creado=creado;self.contacto=contacto
    def req(self,loc,method,ruta,*args,**kw):
        assert loc=='sidFixture'
        if ruta=='/contacts/search':return {'total':10} if args and args[0].get('pageLimit')==1 else {'contacts':[{'id':self.contacto,'dateAdded':self.creado,'attributionSource':{'medium':'form'}}]}
        if ruta=='/calendars/':return {'calendars':[]}
        if ruta=='/conversations/search':return {'_error':'synthetic'} if self.cv_error else {'conversations':[{'id':'conversationFixture','contactId':'contactFixture'}]}
        if ruta=='/conversations/conversationFixture/messages':return {'_error':'synthetic'} if self.msg_error else {'messages':{'messages':deepcopy(self.rows)}}
        if ruta=='/opportunities/pipelines':return {'pipelines':[]}
        if ruta=='/opportunities/search':return {'opportunities':[]}
        if ruta=='/workflows/':return {'workflows':[]}
        raise AssertionError('No transport route')

def publico_fixture676():
    """Puente portátil: fl real generado con transporte sintético, no descriptor mock."""
    ns=cargar(NEW)
    x=ns['leer_subcuenta'](Fake([msg()]),'sidFixture')['leads'][0]
    main=next(n for n in ns['tree'].body if isinstance(n,ast.FunctionDef) and n.name=='main')
    node=next(n for n in ast.walk(main) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='fl' for t in n.targets))
    scope={**ns,'x':x,'cid':'fixture','sid':'sidFixture','ref':'ab12cd34ef56','fila':{'nombre':'Cuenta ficticia','especialista_id':None},'hora_vivo':'2026-10-04 12:00'}
    binding=next(n for n in ast.walk(main) if isinstance(n,ast.If) and isinstance(n.test,ast.Name) and n.test.id=='cid' and any(isinstance(t,ast.Subscript) and isinstance(t.value,ast.Name) and t.value.id=='fl' for a in n.body if isinstance(a,ast.Assign) for t in a.targets))
    exec(compile(ast.Module(body=[node,binding],type_ignores=[]),'<flreal676>','exec'),scope)
    return scope['fl'],{'ghl':{'hora':'2026-10-04 12:00'}},'2026-10-04'

class Tests676(unittest.TestCase):
    def setUp(self):self.old=cargar(BASE);self.new=cargar(NEW)
    def norm(self,rows,ok=True):return self.new['normalizar_mensajes676'](paquetes(*rows),START,CUT,'contactFixture',ok)
    def lead(self,ns,rows,**kw):return ns['leer_subcuenta'](Fake(rows,**kw),'sidFixture')['leads'][0]
    def test_historial_inbound_no_respuesta_actual(self):
        row=msg(dateAdded=START-60000);self.assertTrue(self.lead(self.old,[row])['respondio']);x=self.lead(self.new,[row]);self.assertIsNone(x['respondio']);self.assertIsNone(x['mensajes_medicion']['entradas_observadas'])
    def test_canales_llamadas_previos_no_atribuir(self):
        rows=[msg(direction='outbound',messageType='TYPE_WHATSAPP',status='failed',dateAdded=START-1),msg(id='callFixture',direction='outbound',messageType='TYPE_CALL',status='completed',dateAdded=START-1)]
        a=self.lead(self.old,rows);b=self.lead(self.new,rows);self.assertEqual((a['wa_env'],a['llamadas']),(1,1));self.assertEqual((b['wa_env'],b['llamadas']),(0,0));self.assertIsNone(b['respondio'])
    def test_valido_entrada_no_humano_resultado(self):
        x=self.lead(self.new,[msg()]);self.assertTrue(x['respondio']);m=x['mensajes_medicion'];self.assertEqual(m['ultima_entrada_ms'],START+60000);self.assertIsNone(m['respuesta_humana_confirmada']);self.assertIsNone(m['resultado_comercial_confirmado']);self.assertFalse(m['completa'])
    def test_replay_igual_una_entrada(self):
        n=self.norm([msg(),msg()]);self.assertEqual(n['medicion']['entradas_observadas'],1);self.assertEqual(n['medicion']['diagnosticos']['replay_id'],1)
    def test_conflicto_global_antes_filtro(self):
        for alter in ({'dateAdded':START-1},{'direction':'outbound'},{'contactId':'otherContact'},{'messageType':'TYPE_CALL'}):
            n=self.norm([msg(),msg(**alter)]);self.assertIsNone(n['respondio']);self.assertFalse(n['fiable']);self.assertIsNone(n['conteos']['mail_env'])
    def test_minimo_independiente_otra_lectura_fallida(self):
        n=self.norm([msg(direction='outbound',status='sent')],False);self.assertIsNone(n['conteos']['mail_env']);self.assertEqual(n['minimos']['mail_env'],1);self.assertIsNone(n['minimos']['wa_env'])
    def test_errores_no_fabricated0(self):
        for kw in ({'cv_error':True},{'msg_error':True}):
            a=self.lead(self.old,[],**kw);b=self.lead(self.new,[],**kw);self.assertEqual(a['mail_env'],0);self.assertIsNone(b['mail_env']);self.assertIsNone(b['respondio']);self.assertIsNone(b['intentos'])
    def test_naive_futura_invalida_unknown(self):
        for v in ('2026-10-03 10:00:00',CUT+1,None,float('nan'),'2026-10-03T10:00:00+02:99'):
            n=self.norm([msg(dateAdded=v)]);self.assertIsNone(n['respondio']);self.assertIsNone(n['conteos']['mail_env'])
    def test_source_status_type_direction_containers(self):
        for field,value in (('source',{}),('status',[]),('messageType',{}),('direction',[])):
            n=self.norm([msg(**{field:value})]);self.assertIsNone(n['respondio']);self.assertIsNone(n['conteos']['mail_env'])
    def test_auto_call_queued_no_entrada(self):
        for change in ({'source':'workflow'},{'source':'bot'},{'messageType':'TYPE_CALL'},{'status':'queued'},{'source':None}):self.assertIsNone(self.norm([msg(**change)])['respondio'])
    def test_contacto_y_conversacion_no_inferidos(self):
        n=self.new['normalizar_mensajes676']([{'mensaje':msg(contactId=None),'contacto_conversacion':None}],START,CUT,'contactFixture',True);self.assertIsNone(n['respondio'])
        n=self.norm([msg(conversationId='foreignConversation')]);self.assertIsNone(n['respondio'])
    def test_pares_agregado_none_legacy_no_TypeError(self):
        x=self.lead(self.new,[msg(direction='outbound',status='sent')]);n=self.new['canal_observado676']([x,{'mail_env':None,'mail_fallo':None}],'mail');self.assertEqual((n['enviados'],n['fallidos'],n['observados'],n['total']),(1,0,1,2))
        self.assertIsNone(self.new['canal_observado676']([{'mail_env':0,'mail_fallo':0}],'mail')['enviados'])
    def test_iso_creacion_gateway(self):
        for v in (float('nan'),float('inf'),True,False,'2026-10-03 10:00:00','2026-10-03T10:00:00+02:99'):self.assertIsNone(self.new['iso_ms'](v));self.assertIsNone(self.lead(self.new,[],creado=v)['creado'])
        self.assertEqual(self.new['iso_ms'](0),0);self.assertEqual(self.new['iso_ms']('2026-10-03T10:00:00Z'),self.new['iso_ms']('2026-10-03T12:00:00+02:00'))
    def test_public_fl_real_bound_y_sourcecut(self):
        x=self.lead(self.new,[msg()]);tree=self.new['tree'];main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main');node=next(n for n in ast.walk(main) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='fl' for t in n.targets));scope={**self.new,'x':x,'cid':'fixture','sid':'sidFixture','ref':'ab12cd34ef56','fila':{'nombre':'Cuenta ficticia','especialista_id':None},'hora_vivo':'2026-10-04 12:00'}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<flreal676>','exec'),scope);fl=scope['fl'];m=fl['respuesta_medicion676'];self.assertEqual((m['cliente_id'],m['sub_id'],m['ref']),('fixture','sidFixture','ab12cd34ef56'));self.assertEqual(self.new['iso_ms'](fl['creado_iso676']),START)
        for key in ('contactId','mensaje','source','status','messageType'):self.assertNotIn(key,m)
        self.assertIsNone(self.new['respuesta_publica676'](x,'fixture','sidFixture','ab12cd34ef56','2026-10-03 12:00'))
    def test_ids_numericos_opacos_validos(self):
        p=[{'mensaje':msg(id='123',contactId='456'),'contacto_conversacion':'456','conversacion_id':'conversationFixture'}]
        n=self.new['normalizar_mensajes676'](p,START,CUT,'456',True)
        self.assertTrue(n['respondio']);self.assertEqual(n['medicion']['entradas_observadas'],1)
    def test_extras_no_consumidos_no_conflicto(self):
        n=self.norm([msg(body='privado sintético',attachments=[{'dato':'A'}]),msg(body='otro cuerpo',attachments=[{'dato':'B'}],extra={'arbitrario':True})])
        self.assertEqual(n['medicion']['entradas_observadas'],1);self.assertTrue(n['fiable']);self.assertNotIn('body',n['sal']);self.assertNotIn('privado',json.dumps(n))
    def test_espacios_normalizados_tipo_origen_status(self):
        n=self.norm([msg(source=' workflow ',messageType=' TYPE_EMAIL ',status=' received ')])
        self.assertIsNone(n['respondio'])
        x=self.lead(self.new,[msg(direction=' OUTBOUND ',source=' workflow ',messageType=' TYPE_EMAIL ',status=' SENT ')])
        self.assertEqual(x['mail_env'],1);self.assertIsNotNone(x['auto_min']);self.assertIsNone(x['humano_min']);self.assertIsNone(x['respondio'])
    def test_salida_status_desconocido_no_ejecucion(self):
        for status in (None,'unknown','received',' queued ',' pending ','draft',{},[]):
            x=self.lead(self.new,[msg(direction='outbound',status=status)])
            self.assertIsNone(x['humano_min']);self.assertIsNone(x['auto_min']);self.assertIsNone(x['respondio'])
            self.assertNotEqual(x['mail_env'],1);self.assertNotEqual(x['intentos'],1)
        n=self.norm([msg(direction='outbound',status='unknown')])
        self.assertEqual(n['minimos']['registros_salida_estado_desconocido'],1);self.assertIsNone(n['minimos']['mail_env'])
    def test_epochs_no_representables_no_excepcion(self):
        for value in (9007199254740991,'1969-12-31T23:59:59Z',1.5):
            self.assertIsNone(self.new['iso_ms'](value));self.assertIsNone(self.lead(self.new,[],creado=value)['creado'])
    def test_main_velocidad_descriptor_legacy_no_acredita(self):
        main=next(n for n in self.new['tree'].body if isinstance(n,ast.FunctionDef) and n.name=='main')
        pairs=[(k,v) for n in ast.walk(main) if isinstance(n,ast.Dict) for k,v in zip(n.keys,n.values) if isinstance(k,ast.Constant) and k.value=='respondieron']
        self.assertEqual(len(pairs),1)
        expr=compile(ast.Expression(pairs[0][1]),'<mainrespondieron676>','eval')
        self.assertIsNone(eval(expr,{**self.new,'auto':[{'respondio':True}]}))
        x=self.lead(self.new,[msg()]);self.assertEqual(eval(expr,{**self.new,'auto':[x,{'respondio':True}]}),1)
    def test_public_fl_mismo_minuto_no_rejuvenece(self):
        x=self.lead(self.new,[msg()]);x['mensajes_medicion']['hasta_ms']=CUT+12345
        self.assertIsNotNone(self.new['respuesta_publica676'](x,'fixture','sidFixture','ab12cd34ef56','2026-10-04 12:00'))
        self.assertIsNone(self.new['respuesta_publica676'](x,'fixture','sidFixture','ab12cd34ef56','2026-10-04 12:01'))
    def test_conflicto_identidad_entre_leads_real(self):
        class Two(Fake):
            def req(self,loc,method,ruta,*args,**kw):
                if ruta=='/contacts/search' and not (args and args[0].get('pageLimit')==1):return {'contacts':[{'id':cid,'dateAdded':START,'attributionSource':{'medium':'form'}} for cid in ('contactFixture','secondContact','thirdContact')]}
                if ruta=='/conversations/search':return {'conversations':[{'id':kw['contactId'],'contactId':kw['contactId']}]}
                if ruta.startswith('/conversations/') and ruta.endswith('/messages'):return {'messages':{'messages':[msg(contactId=None,id='otherMessage' if '/thirdContact/' in ruta else 'msgFixture')]}}
                return super().req(loc,method,ruta,*args,**kw)
        ls=self.new['leer_subcuenta'](Two([]),'sidFixture')['leads']
        self.assertEqual(len(ls),3)
        for x in ls[:2]:self.assertIsNone(x['respondio']);self.assertIsNone(x['mail_env']);self.assertGreater(x['mensajes_medicion']['diagnosticos']['id_ambito_conflictivo'],0)
        self.assertTrue(ls[2]['respondio']);self.assertEqual(ls[2]['mensajes_medicion']['entradas_observadas'],1)
    def test_preflight_replay_extra_y_minimos_independientes(self):
        ps=paquetes(msg(extra='A'),msg(extra='B'))
        self.assertEqual(self.new['conflictos_globales676'](ps),set())
        ps.append({'mensaje':msg(contactId='secondContact',dateAdded=START-1),'contacto_conversacion':'secondContact'})
        bad=self.new['conflictos_globales676'](ps);self.assertEqual(bad,{'msgFixture'})
        marked=[{**p,'conflicto_global676':True} for p in ps[:2]]+paquetes(msg(id='independentMessage'))
        n=self.new['normalizar_mensajes676'](marked,START,CUT,'contactFixture',True)
        self.assertTrue(n['respondio']);self.assertEqual(n['medicion']['entradas_observadas'],1);self.assertFalse(n['fiable'])
    def test_global_binding_malformado_contamina_id_no_otra_subcuenta(self):
        good=paquetes(msg());bad=[{'mensaje':msg(contactId=[]),'contacto_conversacion':'contactFixture'}]
        self.assertEqual(self.new['conflictos_globales676'](good+bad),{'msgFixture'})
        self.assertEqual(self.new['conflictos_globales676'](good),set())
        self.assertEqual(self.new['conflictos_globales676']([{'mensaje':msg(contactId='otherContact'),'contacto_conversacion':'otherContact'}]),set())
    def test_limite_transporte_no_certifica_100mas(self):
        rows=[msg(id='message'+str(i)) for i in range(101)]
        x=self.lead(self.new,rows);self.assertIsNone(x['mail_env']);self.assertEqual(x['mensajes_medicion']['entradas_observadas'],100);self.assertFalse(x['mensajes_medicion']['conteos_acreditados'])
    def test_id_container_lector_real_unknown_no_TypeError(self):
        for ident in ({},[]):
            x=self.lead(self.new,[msg(id=ident)])
            self.assertIsNone(x['respondio']);self.assertIsNone(x['mail_env']);self.assertIsNone(x['intentos']);self.assertGreater(x['mensajes_medicion']['diagnosticos']['identidad_invalida'],0)
    def test_inbound_status_observado_explicito(self):
        for status in (None,'unknown','failed','undelivered','bounced','queued','pending','draft',{},[]):
            x=self.lead(self.new,[msg(status=status)])
            self.assertIsNone(x['respondio']);self.assertIsNone(x['mensajes_medicion']['entradas_observadas'])
        for status in ('received','delivered','read',' RECEIVED '):
            self.assertTrue(self.lead(self.new,[msg(status=status)])['respondio'])
    def test_contact_id_container_no_crash_ni_lectura_conversacion(self):
        for ident in ({},[]):
            x=self.lead(self.new,[],contacto=ident)
            self.assertFalse(x['cita']);self.assertIsNone(x['respondio']);self.assertIsNone(x['intentos']);self.assertIsNone(x['mail_env'])
    def test_sin_tocar_descriptor_cohorte_y_corte_original(self):
        x=self.lead(self.new,[])
        fin=self.new['inicio_dia'](0);inicio=self.new['inicio_dia'](30)
        f=self.new['sin_tocar_publico676'];m=f([x],'fixture','sidFixture','2026-10-04 12:00',inicio,fin,CUT)
        self.assertEqual(m['version'],'676.1');self.assertEqual((m['desde_ms'],m['cohorte_hasta_ms'],m['hasta_ms']),(inicio,fin,CUT));self.assertEqual((m['leads_observados'],m['leads_elegibles']),(1,1));self.assertFalse(m['completa'])
        self.assertIsNone(f([x],'fixture','sidFixture','2026-10-03 12:00',inicio,fin,CUT))
        self.assertIsNone(f([{'contacto':'legacy','creado':START,'es_lead':True,'intentos':0}],'fixture','sidFixture','2026-10-04 12:00',inicio,fin,CUT))
        self.assertIsNone(f([x,x],'fixture','sidFixture','2026-10-04 12:00',inicio,fin,CUT))
        self.assertIsNone(f([x],'fixture','sidFixture','2026-10-04 12:00',inicio,fin,CUT+1))
    def test_puente_fl_cid_es_asignacion_real(self):
        fl,fuentes,hoy=publico_fixture676()
        self.assertEqual(fl['cliente_id'],fl['respuesta_medicion676']['cliente_id']);self.assertEqual(fl['creado_iso676'],'2026-09-30T10:00:00+00:00');self.assertEqual(hoy,'2026-10-04')
    def test_contexto_opaco_invalido_no_minimos_positivos(self):
        for context in (123,True,None,[],{}):
            ps=[{'mensaje':msg(contactId=context),'contacto_conversacion':context}]
            n=self.new['normalizar_mensajes676'](ps,START,CUT,context,True)
            self.assertIsNone(n['respondio']);self.assertIsNone(n['medicion']['entradas_observadas']);self.assertFalse(n['fiable']);self.assertIsNone(n['conteos']['mail_env']);self.assertTrue(all(v is None for v in n['minimos'].values()));self.assertGreater(n['medicion']['diagnosticos']['contexto_invalido'],0)
        x=self.lead(self.new,[msg()]);x['contacto']=123
        self.assertIsNone(self.new['respuesta_publica676'](x,'fixture','sidFixture','ab12cd34ef56','2026-10-04 12:00'))
    def test_conversation_ruta_opaca_antes_GET(self):
        class Conv(Fake):
            def __init__(self,ident):super().__init__([msg()]);self.ident=ident;self.calls=[]
            def req(self,loc,method,ruta,*args,**kw):
                self.calls.append((method,ruta))
                if ruta=='/conversations/search':return {'conversations':[{'id':self.ident,'contactId':'contactFixture'}]}
                if self.ident=='123' and ruta=='/conversations/123/messages':return {'messages':{'messages':self.rows}}
                return super().req(loc,method,ruta,*args,**kw)
        for ident in ('../other','a/b','https://example.invalid','a'*161,{},[],None):
            tr=Conv(ident);x=self.new['leer_subcuenta'](tr,'sidFixture')['leads'][0]
            self.assertIsNone(x['respondio']);self.assertIsNone(x['intentos']);self.assertFalse(any('/messages' in route for _,route in tr.calls))
        tr=Conv('123');x=self.new['leer_subcuenta'](tr,'sidFixture')['leads'][0]
        self.assertTrue(x['respondio']);self.assertIn(('GET','/conversations/123/messages'),tr.calls)
    def test_conversation_packet_puro_opaco_sin_ruta(self):
        for ident in ('../other','a/b','https://example.invalid','a'*161,{},[]):
            ps=[{'mensaje':msg(),'contacto_conversacion':'contactFixture','conversacion_id':ident}]
            n=self.new['normalizar_mensajes676'](ps,START,CUT,'contactFixture',True)
            self.assertIsNone(n['respondio']);self.assertFalse(n['fiable']);self.assertEqual(self.new['conflictos_globales676'](ps),{'msgFixture'})
        ps=[{'mensaje':msg(),'conversacion_id':None}]
        self.assertTrue(self.new['normalizar_mensajes676'](ps,START,CUT,'contactFixture',True)['respondio'])
        ps=[{'mensaje':msg(contactId=None),'contacto_conversacion':'contactFixture','conversacion_id':None}]
        self.assertIsNone(self.new['normalizar_mensajes676'](ps,START,CUT,'contactFixture',True)['respondio'])
        self.assertEqual(self.new['conflictos_globales676'](ps),{'msgFixture'})
    def test_main_guards_reales_none_y_ausencia(self):
        main=next(n for n in self.new['tree'].body if isinstance(n,ast.FunctionDef) and n.name=='main')
        nodes=[n for n in ast.walk(main) if isinstance(n,ast.If) and isinstance(n.test,ast.BoolOp) and any(isinstance(z,ast.Name) and z.id=='wa_env' for z in ast.walk(n.test))]
        self.assertGreaterEqual(len(nodes),3)
        scope={**self.new,'wa_env':None,'wa_fallo':None,'sms_env':None,'mail_env':None,'encendida':True,'auto':[{}, {}, {}],'auto_ok':[]}
        for node in nodes:self.assertFalse(eval(compile(ast.Expression(node.test),'<ifreal676>','eval'),scope))

if __name__=='__main__':unittest.main()
