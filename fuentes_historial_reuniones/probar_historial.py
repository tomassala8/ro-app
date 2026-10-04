import copy
import tempfile
import unittest
from datetime import date
from pathlib import Path
from fuentes_historial_reuniones.normalizador import normalizar, leer_privado, fecha
from fuentes_historial_reuniones.importar_offline import documentos_locales

M = {'url':'https://fathom.video/calls/123', 'recording_id':99,
     'recording_start_time':'2026-10-02T10:00:00Z','recording_end_time':'2026-10-02T10:30:00Z',
     'transcript':[{'text':'contenido privado cuenta 1234', 'speaker':{'display_name':'Persona privada'}}],
     'recorded_by': {'name':'Host privado'},'title':'Privado'}
C = {'Carpeta':{'cliente_id':'c1','confirmado':True,'fuente':'archivo revisado línea 3'}}


def go(ms=None, **kw):
    return normalizar([M] if ms is None else ms, {'123':'Carpeta'}, C, {'c1'}, **kw)


class Historial(unittest.TestCase):
    def test_replay_id_hash_no_pii_publica(self):
        x = go([M,copy.deepcopy(M)])
        self.assertEqual(len(x['reuniones']),1)
        self.assertEqual(x['cobertura']['duplicados_cache'],1)
        r=x['reuniones'][0]
        self.assertEqual(r['inicio'],'2026-10-02T10:00:00+00:00')
        self.assertEqual(r['duracion_minutos'],30)
        self.assertFalse(r['celebrada_confirmada'])
        self.assertNotIn('Privado',str(r));self.assertNotIn('Persona privada',str(r))
        self.assertIsNotNone(x['privados'][r['id']]['transcripcion'])
    def test_conflicto_no_overwrite(self):
        changed=dict(M,title='otra versión')
        x=go([M,changed]);self.assertEqual(x['reuniones'],[]);self.assertEqual(x['cobertura']['conflictos'],1)
    def test_unknown_vinculo_no_fuzzy(self):
        x=normalizar([M],{'123':'carpeta'},C,{'c1'})
        self.assertEqual(x['reuniones'],[])
        for cat in ({'Carpeta':{'cliente_id':'c1','confirmado':False,'fuente':'x'}}, {'Carpeta':{'cliente_id':'otro','confirmado':True,'fuente':'x'}}):
            self.assertEqual(normalizar([M],{'123':'Carpeta'},cat,{'c1'})['reuniones'],[])
    def test_exclusion_ventas_internos_borrados(self):
        for cat in ['Reunion_de_Venta','Reunion_Interna_Equipo','_Para_Eliminar','HR']:
            x=go(indice=[{'id':'123','carpeta':cat}]);self.assertEqual(x['reuniones'],[]);self.assertEqual(x['cobertura']['excluidos'],1)
    def test_conflicto_carpeta_no_reasigna(self):
        self.assertEqual(go(documentos=[{'call_id':'123','carpeta':'Otra'}])['reuniones'],[])
    def test_sin_texto_sin_grabacion_no_celebrada(self):
        m=dict(M,transcript=[],recording_end_time=None)
        r=go([m])['reuniones'][0]
        self.assertFalse(r['transcripcion_disponible']);self.assertFalse(r['celebrada_confirmada'])
        self.assertEqual(r['grabacion_acceso'],'no_verificado');self.assertIsNone(r['duracion_minutos'])
    def test_agendada_fecha_creacion_no_fecha_real(self):
        m=dict(M,recording_start_time=None,recording_end_time=None,created_at='2026-10-01T00:00:00Z',scheduled_start_time='2026-10-03T00:00:00Z')
        self.assertIsNone(go([m])['reuniones'][0]['fecha'])
    def test_fecha_invalid_timezone_madrid_real(self):
        self.assertIsNone(fecha('2026-02-30T10:00:00Z'));self.assertIsNone(fecha('2026-10-02T10:00:00'))
        m=dict(M,recording_start_time='2026-03-28T23:30:00Z',recording_end_time='2026-03-29T00:00:00Z')
        self.assertEqual(go([m])['reuniones'][0]['fecha'],'2026-03-29')
    def test_account_no_actual_ni_host(self):
        a={'cliente_id':'c1','silla':'account','persona_id':'actual','fuente':'cartera','desde':'2026-01-01','hasta':'2026-12-31'}
        self.assertEqual(go(asignaciones=[a])['reuniones'][0]['account_historico']['estado'],'sin_evidencia')
        a['historico_confirmado']=True
        self.assertEqual(go(asignaciones=[a])['reuniones'][0]['account_historico']['persona_id'],'actual')
        b=dict(a,persona_id='otro')
        self.assertEqual(go(asignaciones=[a,b])['reuniones'][0]['account_historico']['estado'],'ambiguo')
    def test_indice_sin_texto_conserva_registro_sin_certeza(self):
        r=go([],indice=[{'id':'123','fecha':'2025-10-01','carpeta':'Reunion_con_Cliente'}])['reuniones'][0]
        self.assertEqual(r['fecha'],'2025-10-01');self.assertEqual(r['estado_realizacion'],'sin_confirmar')
        self.assertFalse(r['transcripcion_disponible'])
    def test_lector_no_symlink_traversal_ni_fuera(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            root=Path(tmp); f=root/'x';f.write_text('privado'); link=root/'link';link.symlink_to(f)
            self.assertEqual(leer_privado(f,root),b'privado')
            for p in [link,root/'..'/'x',root.parent/'otro']:
                with self.assertRaises(ValueError):leer_privado(p,root)
            with self.assertRaises(ValueError):leer_privado(f,root,limite=2)
    def test_discovery_sin_texto_salida_solo_indice_privado(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            f=Path(tmp)/'10_CLIENTES'/'Carpeta'/'15_Reuniones'/'_fathom'/'2026-01-01_x_123.md';f.parent.mkdir(parents=True);f.write_text('00:03 - Privado\n secreto')
            x=documentos_locales(tmp);self.assertEqual(len(x),1);self.assertTrue(x[0]['transcripcion_disponible']);self.assertNotIn('secreto',str(x))
    def test_documento_sin_cache_no_desaparece(self):
        r=go([],documentos=[{'call_id':'123','carpeta':'Carpeta','fecha':'2025-01-01','transcripcion_disponible':True}])['reuniones'][0]
        self.assertEqual(r['fecha'],'2025-01-01');self.assertEqual(r['fecha_fuente'],'documento_fecha')
        self.assertFalse(r['celebrada_confirmada'])

    def test_malformed_top_level_no_caida(self):
        for campo in ['cache','clasificacion','catalogo','documentos','indice']:
            args={'cache':[M],'clasificacion':{'123':'Carpeta'},'catalogo':C,'clientes_ids':{'c1'},'documentos':[],'indice':[]}
            args[campo]=42
            x=normalizar(**args)
            self.assertGreaterEqual(x['cobertura']['entradas_malformadas'],1)
    def test_malformed_rows_no_caida_ni_foreign(self):
        for campo, malo in [('cache',None),('documentos',False),('indice','csv nuevo')]:
            args={'cache':[M],'clasificacion':{'123':'Carpeta'},'catalogo':C,'clientes_ids':{'c1'},'documentos':[],'indice':[]}
            args[campo].append(malo)
            self.assertGreater(normalizar(**args)['cobertura']['entradas_malformadas'],0)
        for folder in [{},[],42]:
            x=normalizar([M],{'123':folder},C,{'c1'})
            self.assertEqual(x['reuniones'],[]);self.assertEqual(x['cobertura']['entradas_malformadas'],1)
        x=normalizar([M],{'123':'Carpeta'},{'Carpeta':{'cliente_id':[],'confirmado':True,'fuente':'x'}},{'c1'})
        self.assertEqual(x['reuniones'],[])
    def test_fecha_fuente_documento_prioridad_y_discrepancia(self):
        x=go([],documentos=[{'call_id':'123','carpeta':'Carpeta','fecha':'2025-02-01'}],indice=[{'id':'123','fecha':'2025-01-01','carpeta':'Reunion_con_Cliente'}])
        r=x['reuniones'][0]
        self.assertEqual(r['fecha'],'2025-02-01');self.assertEqual(r['fecha_fuente'],'documento_fecha');self.assertTrue(r['fecha_discrepancia'])
        self.assertEqual(r['fechas_evidencia']['indice'],'2025-01-01')
    def test_fecha_cache_prioridad_no_silencia_documento(self):
        r=go(documentos=[{'call_id':'123','carpeta':'Carpeta','fecha':'2025-01-01'}])['reuniones'][0]
        self.assertEqual(r['fecha_fuente'],'recording_start_time');self.assertTrue(r['fecha_discrepancia'])
        self.assertEqual(r['fechas_evidencia']['documentos'],['2025-01-01'])
    def test_hardlink_rechazado(self):
        import os
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            f=Path(tmp)/'archivo';f.write_text('datos');b=Path(tmp)/'enlace';os.link(f,b)
            for p in [f,b]:
                with self.assertRaises(ValueError):leer_privado(p,Path(tmp))

    def test_indice_duplicado_fecha_conflictiva_no_overwrite(self):
        x=go(indice=[{'id':'123','fecha':'2025-01-01','carpeta':'Reunion_con_Cliente'}, {'id':'123','fecha':'2025-02-01','carpeta':'Reunion_con_Cliente'}])
        self.assertEqual(x['reuniones'],[]);self.assertEqual(x['cobertura']['conflictos'],1)

    def test_limite_hasta_no_futuro(self):
        self.assertEqual(go(hasta=date(2026,10,1))['reuniones'],[])

if __name__ == '__main__': unittest.main()
