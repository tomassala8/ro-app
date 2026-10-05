"""Fixtures aislados: nunca llaman CLI ni leen caches privados."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from datetime import datetime,timezone

HERE=Path(__file__).resolve().parent
APP=HERE
spec=importlib.util.spec_from_file_location('offline669',APP/'fuentes_crm/preparar_embudo_offline_669.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)

def lector():
    names={'_n','_id','_sha','_instante','_diagnosticos','_medicion'}
    tree=ast.parse((APP/'crm_embudo_api_467.py').read_text())
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'DIAGNOSTICOS','INCIDENCIAS_MOTOR','VERSION','LIMITES'} for t in n.targets)]
    ns={'datetime':datetime,'timezone':timezone,'re':re,'ETAPAS':('recibido','cualificado','contacto','respuesta','cita','asistencia','venta')};exec(compile(ast.Module(body=nodes,type_ignores=[]),'<lector467>','exec'),ns);return ns

class Contrato669(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve();self.app=self.root/'30_APP_PROTOTIPO';self.app.mkdir();self.r=self.root/'RECUPERACION_CODEX_2026-10-03';self.r.mkdir(mode=0o700)
        for f in ('ghl_embudo_observado_466.py','embudo_eventos.py'):(self.app/f).write_bytes((APP/f).read_bytes())
        self.motor=self.app/'embudo_eventos.py';self.pin=M.sha(self.motor.read_bytes())
        p=self.app/'fuentes_verdad/clientes_activos.py';p.parent.mkdir();p.write_text("TIPOS_ACTIVOS={'activo'}\nBAJAS_CONFIRMADAS=set()\n")
        # literal_eval no acepta llamada set(): usar literal vacío mediante lista.
        p.write_text("TIPOS_ACTIVOS={'activo'}\nBAJAS_CONFIRMADAS=[]\n")
        self.raw={'hora':'2026-10-03 04:01','subs':[{'id':'sidFixture'}],'vivo':{'sidFixture':{'leads':[{'contacto':'leadFixture','es_lead':True,'creado':1788998400000}], 'citas':[]}}}
        self.crm={'subcuentas':[{'tipo':'cliente','cliente_id':'fixture','sub_id':'sidFixture'}]};self.act={'activos':[{'id':'fixture','tipo':'activo'}],'bajas_ids':[]};self.flush()
    def tearDown(self):self.tmp.cleanup()
    def flush(self):
        for name,d in (('fuentes_crm/_privado/ghl_vivo.json',self.raw),('data/crm/crm.json',self.crm),('data/verdad/estado_clientes.json',self.act)):
            p=self.app/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(M.serial(d));p.chmod(0o600)
    def build(self):return M.construir(self.app,self.motor,self.pin,'2026-10-04T12:00:00Z')
    def test_offline_preserva_fecha_sin_eventos_privados(self):
        b,mb,rb=self.build();d=json.loads(b);m=json.loads(mb);self.assertEqual(d['hora_fuente'],'2026-10-03T04:01:00+02:00');self.assertNotIn(b'leadFixture',b);self.assertNotIn(b'sidFixture',b);self.assertEqual(m['codigo_sha256']['embudo_eventos'],self.pin);self.assertFalse(json.loads(rb)['promovido'])
        row=d['clientes'][0];out=lector()['_medicion'](row['medicion'],'fixture',d['desde'],d['hasta'],d['corte']);self.assertEqual(out['cohorte']['estado'],'parcial');self.assertIsNone(row['medicion']['grupos'][0]['cohorte']['etapas']['venta']['valor'])
    def test_empty_no_cero_completo(self):
        self.raw['vivo']['sidFixture']['leads']=[];self.flush();d=json.loads(self.build()[0]);co=d['clientes'][0]['medicion']['grupos'][0]['cohorte'];self.assertEqual(co['estado'],'desconocido');self.assertEqual(co['recibidos_observados'],0);self.assertIsNone(co['etapas']['recibido']['valor'])
    def test_pin_incorrecto_rechazado(self):
        with self.assertRaises(ValueError):M.construir(self.app,self.motor,'0'*64,'2026-10-04T12:00:00Z')
    def test_symlink_y_modo_privado(self):
        p=self.app/'fuentes_crm/_privado/ghl_vivo.json';p.chmod(0o644)
        with self.assertRaises(ValueError):self.build()
        p.chmod(0o600);other=p.with_name('raw.json');p.rename(other);p.symlink_to(other)
        with self.assertRaises(ValueError):self.build()
    def test_ambiguedad_act_no_fila(self):
        self.act['activos']*=2;self.flush()
        with self.assertRaises(ValueError):self.build()
    def test_sourcechange_rechazado(self):
        original=M.leer;calls=0
        def changed(p,*args):
            nonlocal calls
            b=original(p,*args);calls+=1
            if calls==6:self.raw['hora']='2026-10-03 04:02';self.flush()
            return b
        M.leer=changed
        try:
            with self.assertRaises(ValueError):self.build()
        finally:M.leer=original
    def test_atomic_privado_no_overwrite(self):
        files=self.build();p=self.r/'staging_embudo_669_fixture';M.guardar(p,self.app,files);self.assertEqual(p.stat().st_mode&0o777,0o700)
        self.assertTrue(all(x.stat().st_mode&0o777==0o600 for x in p.iterdir()))
        with self.assertRaises(ValueError):M.guardar(p,self.app,files)
    def test_newdiag_653_requiere_lector_actualizado(self):
        d=json.loads(self.build()[0]);med=d['clientes'][0]['medicion'];med['incidencias']['event_id_ambito_conflictivo']=1;ns=lector();ns['INCIDENCIAS_MOTOR']=ns['INCIDENCIAS_MOTOR']-M.NUEVAS_INCIDENCIAS
        with self.assertRaises(ValueError):ns['_medicion'](med,'fixture',d['desde'],d['hasta'],d['corte'])
        ns=lector()
        out=ns['_medicion'](med,'fixture',d['desde'],d['hasta'],d['corte']);self.assertNotIn('incidencias',out)
    def test_no_amplia_etapas(self):
        d=json.loads(self.build()[0]);med=d['clientes'][0]['medicion'];g=med['grupos'][0];g['cohorte']['etapas']['venta']['observados']=1;g['cohorte']['etapas']['venta']['estado']='parcial'
        with self.assertRaises(ValueError):lector()['_medicion'](med,'fixture',d['desde'],d['hasta'],d['corte'])
    def test_motor668_sintetico_sin_cambiar_pin_APP(self):
        candidate=APP/'embudo_eventos.py'
        self.motor=candidate;self.pin='fa0186a9c7f8122c9eb0efa281d6999f4e777305c449e14af6d18b5949777e2d'
        d=json.loads(self.build()[0]);self.assertEqual(d['clientes'][0]['medicion']['grupos'][0]['cohorte']['recibidos_observados'],1)
        self.assertNotIn('event_id_ambito_conflictivo',d['clientes'][0]['medicion']['incidencias'])
    def test_whitelist_no_unknown_bool_negativo(self):
        ns=lector()
        for v in ({'unknown':1},{'event_id_ambito_conflictivo':True},{'event_id_ambito_conflictivo':-1}):
            with self.assertRaises(ValueError):ns['_diagnosticos'](v,ns['INCIDENCIAS_MOTOR'])
        self.assertEqual(ns['_diagnosticos']({},ns['INCIDENCIAS_MOTOR']),{})
    def test_620_sigue_etapas_no_instrumentadas_desconocidas(self):
        d=json.loads(self.build()[0]);row=d['clientes'][0];ns=lector();med=ns['_medicion'](row['medicion'],'fixture',d['desde'],d['hasta'],d['corte'])
        sp=importlib.util.spec_from_file_location('reservas620fixture',APP/'cerebro_reservas_620.py');c=importlib.util.module_from_spec(sp);sp.loader.exec_module(c)
        dto={'version':'467.1','estado':'copia_observada','cliente_id':'fixture','medicion':med,'diagnosticos':row['diagnosticos'],**{k:d[k] for k in ('hora_fuente','desde','hasta','corte')}}
        model=c._modelo(dto,'fixture',datetime(2026,10,4).date(),datetime(2026,10,4,12,tzinfo=timezone.utc));self.assertEqual(model[:2],(1,0))
        for k in ('venta','asistencia','cualificado'):
            self.assertEqual(med['cohorte']['etapas'][k],{'observados':0,'estado':'desconocido'})
    def test_json_ambiguo_no_fuente_futura(self):
        with self.assertRaises(ValueError):M.estricto(b'{"a":1,"a":2}')
        with self.assertRaises(ValueError):M.estricto(b'{"a":NaN}')
        with self.assertRaises(ValueError):M.construir(self.app,self.motor,self.pin,'2026-10-02T00:00:00Z')

if __name__=='__main__':unittest.main()
