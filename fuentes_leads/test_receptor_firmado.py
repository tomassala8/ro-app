"""Fixtures sintéticas; no credenciales, contactos ni peticiones de red."""
import copy
import hashlib
import hmac
import json
import unittest
import tempfile
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from leads_archivo import ArchivoLeads
from receptor_firmado import validar_entrega, MAX_BYTES

AHORA = 1791000000
SECRET = 'fixture-falsa-sin-acceso-a-ningun-servicio-0000'
CAT = {'prueba': {'secret': SECRET, 'cliente_id': 'cliente_ficticio', 'source_id': 'sitio_ficticio',
                  'actor_id': 'captura_wp', 'formularios': {5: {'fuente_key': 'form_ficticio_5',
                                                             'privado_campos': ['campo_ficticio']}}}}
EVENT = {'schema_version': 1, 'event': 'form_submission_accepted',
         'event_id': '65d90001-88c5-4136-97b8-55ed562d2a14', 'source_id': 'sitio_ficticio',
         'cliente_id': 'cliente_ficticio', 'form_id': 5, 'entry_id': None,
         'occurred_at': '2026-10-03T00:00:00Z', 'private_fields': {'campo_ficticio': 'Texto sintético ñ'}}


def firmar(body, stamp=AHORA):
    t = str(stamp)
    return {'X-RO-Key-ID': 'prueba', 'X-RO-Timestamp': t,
            'X-RO-Event-ID': EVENT['event_id'],
            'X-RO-Signature': 'v1=' + hmac.new(SECRET.encode(), t.encode()+b'.'+body, hashlib.sha256).hexdigest()}


def serializar(e):
    # Mismas opciones PHP UNESCAPED_UNICODE/SLASHES; validador no reserializa.
    return json.dumps(e, ensure_ascii=False, separators=(',', ':')).encode()


def comprobar(e):
    b = serializar(e)
    return validar_entrega(b, firmar(b), CAT, AHORA)


class ReceptorTest(unittest.TestCase):
    def test_valido_dto_compatible_sin_secretos(self):
        r=comprobar(EVENT)
        self.assertTrue(r['ok'],r)
        self.assertEqual(r['dto']['evento']['etapa'],'recibido')
        self.assertEqual(r['dto']['evento']['meta_privados'],EVENT['private_fields'])
        self.assertEqual(r['dto']['fuente_key'],'form_ficticio_5')
        self.assertNotIn(SECRET,json.dumps(r))
    def test_php_vacio_array(self):
        self.assertEqual(comprobar({**EVENT,'private_fields':[]})['dto']['evento']['meta_privados'],{})
    def test_tamper_bytes_y_no_canonicalizacion(self):
        b=serializar(EVENT);h=firmar(b)
        self.assertEqual(validar_entrega(b+b' ',h,CAT,AHORA)['codigo'],'firma_invalida')
        pretty=json.dumps(EVENT,ensure_ascii=False,indent=2).encode()
        self.assertTrue(validar_entrega(pretty,firmar(pretty),CAT,AHORA)['ok'])
    def test_bad_firma(self):
        b=serializar(EVENT);h=firmar(b);h['X-RO-Signature']='v1='+'0'*64
        self.assertFalse(validar_entrega(b,h,CAT,AHORA)['ok'])
    def test_ventana_pasado_futuro_limite(self):
        b=serializar(EVENT)
        for delta in [-301,301]:
            self.assertEqual(validar_entrega(b,firmar(b,AHORA+delta),CAT,AHORA)['codigo'],'timestamp_fuera_ventana')
        for delta in [-300,300]: self.assertTrue(validar_entrega(b,firmar(b,AHORA+delta),CAT,AHORA)['ok'])
    def test_cliente_source_form_spoof_firmado(self):
        for extra in [{'cliente_id':'otro'},{'source_id':'otro'},{'form_id':6}]:
            self.assertFalse(comprobar({**EVENT,**extra})['ok'])
    def test_unknown_key(self):
        b=serializar(EVENT);h=firmar(b);h['X-RO-Key-ID']='otra'
        self.assertEqual(validar_entrega(b,h,CAT,AHORA)['codigo'],'autorizacion_denegada')
    def test_campos_no_allowlist_tipo_y_tamano(self):
        for fields in [{'raw_post':'no'}, {'campo_ficticio':{'email':'no'}}, {'campo_ficticio':'x'*2049}]:
            self.assertFalse(comprobar({**EVENT,'private_fields':fields})['ok'])
    def test_extra_tipo_bool_y_etapa(self):
        for extra in [{'raw_post':{}},{'schema_version':True},{'form_id':True},
                      {'entry_id':False},{'event':'qualified_lead'},{'etapa':'vendido'}]:
            self.assertFalse(comprobar({**EVENT,**extra})['ok'])
    def test_invalid_utf8_json_duplicado_nan(self):
        bodies=[b'\xff',b'{',b'null',serializar(EVENT).replace(b'"schema_version":1',b'"schema_version":1,"schema_version":1'),
                serializar(EVENT).replace(b'"entry_id":null',b'"entry_id":NaN')]
        for body in bodies:self.assertFalse(validar_entrega(body,firmar(body),CAT,AHORA)['ok'])
    def test_identidad_header_invalida_y_fecha(self):
        b=serializar(EVENT);h=firmar(b);h['X-RO-Event-ID']='otro'
        self.assertEqual(validar_entrega(b,h,CAT,AHORA)['codigo'],'identidad_invalida')
        for extra in [{'event_id':'no-uuid'},{'occurred_at':'not-date'},
                      {'occurred_at':'2099-01-01T00:00:00Z'}]:self.assertFalse(comprobar({**EVENT,**extra})['ok'])
    def test_tamano_y_headers_duplicados(self):
        self.assertFalse(validar_entrega(b'x'*(MAX_BYTES+1),{},CAT,AHORA)['ok'])
        b=serializar(EVENT);h=firmar(b);h['x-ro-key-id']='prueba'
        self.assertEqual(validar_entrega(b,h,CAT,AHORA)['codigo'],'cabeceras_invalidas')
    def test_identidad_estable_y_lite_no_deduce_persona(self):
        r1=comprobar({**EVENT,'entry_id':4})
        # Corregir header al nuevo UUID: helper usa el eventid inicial por defecto.
        b=serializar({**EVENT,'entry_id':4,'event_id':'485728e9-4ee4-4109-b4cc-0942ba5d3a77'});h=firmar(b)
        h['X-RO-Event-ID']='485728e9-4ee4-4109-b4cc-0942ba5d3a77';r2=validar_entrega(b,h,CAT,AHORA)
        self.assertEqual(r1['dto']['evento']['lead_id'],r2['dto']['evento']['lead_id'])
        lite1=comprobar(EVENT);b=serializar({**EVENT,'event_id':h['X-RO-Event-ID']});h=firmar(b);h['X-RO-Event-ID']='485728e9-4ee4-4109-b4cc-0942ba5d3a77'
        lite2=validar_entrega(b,h,CAT,AHORA)
        self.assertNotEqual(lite1['dto']['evento']['lead_id'],lite2['dto']['evento']['lead_id'])
    def test_privacidad_secretos_aunque_configurados(self):
        c=copy.deepcopy(CAT);c['prueba']['formularios'][5]['privado_campos']=['api_key']
        b=serializar({**EVENT,'private_fields':{'api_key':'fixture'}})
        self.assertFalse(validar_entrega(b,firmar(b),c,AHORA)['ok'])
        self.assertFalse(comprobar({**EVENT,'private_fields':{'campo_ficticio':'Bearer ficticio'}})['ok'])
    def test_archivo_persistencia_y_replay_idempotente(self):
        r=comprobar(EVENT);dto=r['dto']
        cat={dto['fuente_key']:{'cliente_id':'cliente_ficticio','source':'wpforms:sitio_ficticio:5',
             'etapas':['recibido'],'actores':['captura_wp'],'privado_campos':['campo_ficticio']}}
        with tempfile.TemporaryDirectory() as directorio:
            a=ArchivoLeads(Path(directorio)/'prueba.sqlite',cat)
            primero=a.ingestar(dto['fuente_key'],dto['actor_id'],[dto['evento']])
            repetido=a.ingestar(dto['fuente_key'],dto['actor_id'],[dto['evento']])
            self.assertEqual(primero['resultados'][0]['resultado'],'aceptado')
            self.assertEqual(repetido['resultados'][0]['resultado'],'duplicado')
    def test_pureza_repeticion_en_ventana_no_persistencia(self):
        c=copy.deepcopy(CAT);b=serializar(EVENT);h=firmar(b);original=copy.deepcopy((c,h))
        self.assertEqual(validar_entrega(b,h,c,AHORA),validar_entrega(b,h,c,AHORA))
        self.assertEqual((c,h),original)
        self.assertEqual(validar_entrega(b,h,c,AHORA)['codigo'],'validado_no_persistido')

if __name__=='__main__':unittest.main()
