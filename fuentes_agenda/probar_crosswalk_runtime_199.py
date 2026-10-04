"""199 fixtures del contrato crosswalk; no importa productores ni proveedores."""
from copy import deepcopy
from pathlib import Path
import ast
import unittest
import json
import os
import tempfile
try:
    from .crosswalk_runtime_199 import cargar_manifest, integrar, identidad_observada
except ImportError:
    from crosswalk_runtime_199 import cargar_manifest, integrar, identidad_observada
try:
    from .crosswalk_confirmado import consolidar_confirmados
except ImportError:
    from crosswalk_confirmado import consolidar_confirmados

HOY='2026-10-03'
def evento(fuente,**extra):
    return dict(id=fuente+'-fixture',fuente=fuente,persona_id='owner-fixture',
      inicio='2026-10-05T08:00:00+02:00',fin='2026-10-05T08:45:00+02:00',
      titulo='Mismo título',atajos=[],**extra)
def registro(e,**extra):
    return dict(confirmado=True,referencia_reunion='occurrence-fixture',persona_id=e['persona_id'],
      fuente=e['fuente'],event_id=e['id'],inicio=e['inicio'],fin=e['fin'],
      evidencia={'tipo':'verificacion_manual','registro_ref':'private-evidence-fixture','fecha_verificacion':HOY},**extra)

class Crosswalk199(unittest.TestCase):
    def run_case(self,events,records):return consolidar_confirmados(events,records,HOY)
    def test_fuentes_originales_y_zona_se_conservan(self):
        events=[evento('crm'),evento('ghl')]
        out,r=self.run_case(events,[registro(e) for e in events])
        self.assertEqual(len(out),1);self.assertEqual(out[0]['inicio'],events[0]['inicio'])
        self.assertEqual(out[0]['fin'],events[0]['fin'])
        self.assertEqual({(o['fuente'],o['id']) for o in out[0]['origenes']},{('crm','crm-fixture'),('ghl','ghl-fixture')})
        self.assertEqual(r['retirados'],1)
    def test_url_sala_compartida_no_identifica_ocurrencia(self):
        events=[evento('crm',join_url='https://zoom.us/j/111'),evento('ghl',join_url='https://zoom.us/j/111')]
        out,r=self.run_case(events,[]);self.assertEqual(out,events);self.assertEqual(r['retirados'],0)
    def test_referencia_recurrente_no_une_fechas_distintas(self):
        events=[evento('crm'),evento('ghl')];events[1]['inicio']='2026-10-06T08:00:00+02:00';events[1]['fin']='2026-10-06T08:45:00+02:00'
        out,r=self.run_case(events,[registro(e) for e in events]);self.assertEqual(out,events)
    def test_enlaces_proveedor_distintos_no_se_pierden(self):
        events=[evento('crm'),evento('ghl')]
        events[0]['atajos']=[{'h':'crm','url':'https://provider.invalid/event/one'}]
        events[1]['atajos']=[{'h':'ghl','url':'https://provider.invalid/event/two'}]
        out,_=self.run_case(events,[registro(e) for e in events])
        self.assertEqual(len(out[0]['atajos']),2)
    def test_owner_distinto_no_fusion(self):
        events=[evento('crm'),evento('ghl')];events[1]['persona_id']='other-owner'
        out,_=self.run_case(events,[registro(e) for e in events]);self.assertEqual(out,events)
    def test_zona_distinta_no_equivalencia_inferida(self):
        events=[evento('crm'),evento('ghl')];events[1]['inicio']='2026-10-05T06:00:00Z';events[1]['fin']='2026-10-05T06:45:00Z'
        out,_=self.run_case(events,[registro(e) for e in events]);self.assertEqual(out,events)
    def test_duracion_distinta_no_fusion(self):
        events=[evento('crm'),evento('ghl')];events[1]['fin']='2026-10-05T09:00:00+02:00'
        out,_=self.run_case(events,[registro(e) for e in events]);self.assertEqual(out,events)
    def test_evidencia_futura_no_fusion(self):
        events=[evento('crm'),evento('ghl')];records=[registro(e) for e in events]
        records[1]['evidencia']['fecha_verificacion']='2027-01-01'
        out,_=self.run_case(events,records);self.assertEqual(out,events)
    def test_inputs_inmutables(self):
        events=[evento('crm'),evento('ghl')];records=[registro(e) for e in events];before=deepcopy((events,records))
        self.run_case(events,records);self.assertEqual((events,records),before)
    def test_diagnostico_productor_zoom_default_no_ventana_acreditada(self):
        # Caracterización del defecto actual, no prueba de seguridad de ese default.
        tree=ast.parse(Path(__file__).with_name('generar_agenda.py').read_text())
        defaults=[n for n in ast.walk(tree) if isinstance(n,ast.BoolOp) and isinstance(n.op,ast.Or)
          and any(isinstance(v,ast.Call) and isinstance(v.func,ast.Attribute) and v.func.attr=='get'
            and v.args and isinstance(v.args[0],ast.Constant) and v.args[0].value=='minutos_reunion' for v in n.values)]
        self.assertTrue(defaults);self.assertTrue(any(isinstance(v,ast.Constant) and v.value==30 for v in defaults[0].values))

class Runtime199(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'manifest.json'
        self.events=[evento('crm'),evento('ghl')]
        for e in self.events:e['identidad_fuente']=identidad_observada(e['fuente'],e['id'],e['inicio'],e['fin'])
        self.manifest={'version':1,'confirmado':True,'evidencia':{'tipo':'revision_documental','registro_ref':'private-review-fixture','fecha_verificacion':HOY},
          'registros':[dict(registro(e),propietario_verificado=True,ventana_verificada=True) for e in self.events]}
    def write(self,m=None):
        self.path.write_text(json.dumps(m or self.manifest));self.path.chmod(0o600)
    def test_manifest_ausente_cero_fusiones_razon_honesta(self):
        out,r=integrar(self.events,self.path,HOY)
        self.assertEqual(len(out),2);self.assertEqual(r['retirados'],0);self.assertEqual(r['manifest_estado'],'ausente')
        self.assertNotIn(str(self.path),str(r))
    def test_runtime_aplica_cruce_validado_y_preserva_identidades(self):
        self.write();out,r=integrar(self.events,self.path,HOY)
        self.assertEqual(len(out),1);self.assertEqual(r['retirados'],1);self.assertTrue(r['integracion_runtime'])
        self.assertEqual(len(out[0]['identidades_fuente']),2);self.assertEqual(r['manifest_estado'],'validado')
        self.assertNotIn('private-review-fixture',str(out)+str(r))
    def test_invalidacion_manifest_conserva_filas(self):
        cases=[{'version':2},{'confirmado':False},{'extra':'unknown'}]
        for extra in cases:
            with self.subTest(extra=extra):
                self.write(dict(self.manifest,**extra));out,r=integrar(self.events,self.path,HOY)
                self.assertEqual(len(out),2);self.assertEqual(r['manifest_estado'],'invalido')
    def test_sin_verificacion_owner_o_ventana_rechaza(self):
        for k in ['propietario_verificado','ventana_verificada']:
            m=deepcopy(self.manifest);m['registros'][0][k]=False;self.write(m)
            self.assertEqual(cargar_manifest(self.path,HOY),([],'invalido'))
    def test_manifest_privado_y_symlink_hardlink_rechazados(self):
        self.write();self.path.chmod(0o644);self.assertEqual(cargar_manifest(self.path,HOY),([],'invalido'))
        self.path.chmod(0o600);link=self.path.with_name('link.json');link.symlink_to(self.path)
        self.assertEqual(cargar_manifest(link,HOY),([],'invalido'))
        link.unlink();os.link(self.path,link);self.assertEqual(cargar_manifest(self.path,HOY),([],'invalido'))
    def test_directorio_manifest_symlink_no_redirige(self):
        self.write();alias=Path(self.tmp.name)/'alias';alias.symlink_to(Path(self.tmp.name),target_is_directory=True)
        self.assertEqual(cargar_manifest(alias/'manifest.json',HOY),([],'invalido'))
    def test_fifo_rechazado_sin_bloqueo(self):
        os.mkfifo(self.path);self.assertEqual(cargar_manifest(self.path,HOY),([],'invalido'))
    def test_demasiado_grande_y_json_duplicado_rechazados(self):
        self.path.write_text('x'*262145);self.path.chmod(0o600)
        self.assertEqual(cargar_manifest(self.path,HOY),([],'invalido'))
        self.path.write_text('{"version":1,"version":1}');self.assertEqual(cargar_manifest(self.path,HOY),([],'invalido'))
    def test_json_anidado_malformado_no_rompe_generacion(self):
        self.path.write_text('['*2000+'0'+']'*2000);self.path.chmod(0o600)
        self.assertEqual(cargar_manifest(self.path,HOY),([],'invalido'))
    def test_evidencia_futura_estructura_privada_extra_rechaza(self):
        m=deepcopy(self.manifest);m['evidencia']['fecha_verificacion']='2027-01-01';self.write(m)
        self.assertEqual(cargar_manifest(self.path,HOY),([],'invalido'))
        m=deepcopy(self.manifest);m['registros'][0]['email']='fixture@example.invalid';self.write(m)
        self.assertEqual(cargar_manifest(self.path,HOY),([],'invalido'))
    def test_naive_zona_literal_no_certifica_y_zoom_defaults_no_certifican(self):
        m=identidad_observada('bookings','fixture','2026-10-05 08:00','2026-10-05 08:45',zona='Europe/Madrid')
        self.assertEqual(m['zona_fuente'],'Europe/Madrid');self.assertFalse(m['ventana_confirmada']);self.assertIsNone(m['inicio_utc'])
        self.assertFalse(identidad_observada('zoom','fixture',None,None)['ventana_confirmada'])
    def test_aware_utc_duracion_exacta_y_uid_contacto_no_expuesto(self):
        m=identidad_observada('calendar','person@example.invalid','2026-10-05T08:00:00+02:00','2026-10-05T08:45:00+02:00')
        self.assertTrue(m['ventana_confirmada']);self.assertEqual(m['inicio_utc'],'2026-10-05T06:00:00Z')
        self.assertEqual(m['duracion_minutos'],45);self.assertIsNone(m['source_event_id'])
    def test_productor_integra_ruta_fija_ast_sin_ejecutarlo(self):
        text=Path(__file__).with_name('generar_agenda.py').read_text();tree=ast.parse(text)
        calls=[c for c in ast.walk(tree) if isinstance(c,ast.Call) and isinstance(c.func,ast.Name) and c.func.id=='integrar_crosswalk']
        self.assertEqual(len(calls),1);self.assertEqual(ast.unparse(calls[0].args[1]),"os.path.join(AQUI, '_privado', 'crosswalk_confirmado.json')")
        # Runtime exacto del segmento puro de integración, sin ejecutar imports/generador.
        a=text.index('ids_antes_crosswalk =');b=text.index('quitadas =',a)
        if __package__:
            from .duplicados import deduplicar
        else:
            from duplicados import deduplicar
        self.write()
        class Now:
            def date(self):return __import__('datetime').date(2026,10,3)
        private=Path(self.tmp.name)/'_privado';private.mkdir();self.path.rename(private/'crosswalk_confirmado.json')
        ns={'eventos':deepcopy(self.events),'privado':{},'integrar_crosswalk':integrar,'deduplicar':deduplicar,'os':os,'AQUI':self.tmp.name,'AHORA':Now()}
        exec(compile(text[a:b],'productor-salida:AST199','exec'),ns)
        self.assertEqual(len(ns['eventos']),1);self.assertEqual(len(ns['fuera']),1)
        self.assertEqual(ns['resumen_crosswalk']['manifest_estado'],'validado')

if __name__=='__main__':unittest.main()

