"""Crosswalk sintético y evidencia estructural local; no importa el generador ni proveedores."""
import ast
from copy import deepcopy
import json
from pathlib import Path
import unittest
from crosswalk_confirmado import consolidar_confirmados
from duplicados import deduplicar

HOY='2026-10-03'

def evento(fuente='crm',**extra):
    return dict({'id':fuente+'-fixture','fuente':fuente,'persona_id':'persona-fixture','inicio':'2026-10-05 08:00',
                 'fin':'2026-10-05 08:45','cliente_ref':None,'titulo':'Nombre idéntico','atajos':[]},**extra)


def registro(e,**extra):
    return dict({'confirmado':True,'referencia_reunion':'ref-fixture','persona_id':e['persona_id'],
                 'inicio':e['inicio'],'fin':e['fin'],'fuente':e['fuente'],'event_id':e['id'],
                 'evidencia':{'tipo':'verificacion_manual','registro_ref':'prueba-privada-fixture','fecha_verificacion':HOY}},**extra)


class Crosswalk189(unittest.TestCase):
    def setUp(self):self.eventos=[evento(),evento('ghl')];self.registros=[registro(e) for e in self.eventos]
    def separados(self,eventos,registros):
        orig=deepcopy(eventos);out,r=consolidar_confirmados(eventos,registros,HOY)
        self.assertEqual(out,orig);self.assertEqual(eventos,orig);self.assertEqual(r['grupos_confirmados'],0);self.assertEqual(r['retirados'],0)

    def test_mismo_slot_sin_identidad_actual_no_se_fusiona(self):
        self.assertEqual(len(deduplicar(self.eventos)[0]),2);self.separados(self.eventos,[])

    def test_cruce_confirmado_fuentes_distintas(self):
        out,r=consolidar_confirmados(self.eventos,self.registros,HOY)
        self.assertEqual(len(out),1);self.assertEqual(r['grupos_confirmados'],1);self.assertEqual(r['retirados'],1)
        self.assertEqual(out[0]['referencia_reunion'],'ref-fixture');self.assertEqual(len(out[0]['origenes']),2)
        self.assertFalse(r['integracion_runtime']);self.assertNotIn('referencia_reunion',self.eventos[0])

    def test_otra_persona_separada(self):
        self.separados([self.eventos[0],evento('ghl',persona_id='otra')],self.registros)

    def test_homonimo_diferentes_referencias(self):
        r=deepcopy(self.registros);r[1]['referencia_reunion']='otra-reunion';self.separados(self.eventos,r)

    def test_duracion_diferente(self):
        self.separados([self.eventos[0],evento('ghl',fin='2026-10-05 08:30')],self.registros)

    def test_nombre_mascara_no_sustituye_prueba(self):
        es=[dict(e,con_quien_m='P. F.',identidad_confirmada=False) for e in self.eventos]
        rs=[dict(r,evidencia={'tipo':'nombre_coincide','registro_ref':'misma-mascara','fecha_verificacion':HOY}) for r in self.registros]
        self.separados(es,rs)

    def test_missing_false_malformed_evidence(self):
        for value in [None,{},'confirmado',{'tipo':'verificacion_manual','fecha_verificacion':HOY},
                      {'tipo':'verificacion_manual','registro_ref':{},'fecha_verificacion':HOY}]:
            self.separados(self.eventos,[dict(r,evidencia=value) for r in self.registros])
        self.separados(self.eventos,[dict(r,confirmado='true') for r in self.registros])

    def test_fecha_future_impossible_invalid(self):
        for date in ['2026-10-04','2026-02-30','2026-10-03 24:00',None]:
            self.separados(self.eventos,[dict(r,evidencia=dict(r['evidencia'],fecha_verificacion=date)) for r in self.registros])

    def test_unknown_source_and_bad_ref_no_fusion(self):
        for change in [{'fuente':[]},{'fuente':'otra'},{'referencia_reunion':7},{'referencia_reunion':'Nombre Apellido'},{'referencia_reunion':'fixture@example.test'},
                       {'event_id':'otro-evento'},{'persona_id':'ajena'},{'inicio':'2026-10-05 08:01'}]:
            self.separados(self.eventos,[dict(r,**change) for r in self.registros])

    def test_same_source_ambiguity_exact_realshape(self):
        es=self.eventos+[evento(id='crm-segunda-fixture')]
        self.separados(es,self.registros)
        self.separados(es,self.registros+[registro(es[-1])])

    def test_doble_claim_no_prevalece_ultimo(self):
        rs=self.registros+[dict(self.registros[0],referencia_reunion='otra-ref')]
        self.separados(self.eventos,rs)
        self.separados(self.eventos,self.registros+[deepcopy(self.registros[0])])

    def test_cliente_sala_participante_conflict(self):
        for a,b in [({'cliente_ref':'cliente-a'},{'cliente_ref':'cliente-b'}),
                    ({'join_url':'https://zoom.us/j/123'},{'join_url':'https://zoom.us/j/456'}),
                    ({'identidad_confirmada':True,'participante_ref':'persona-a'},{'identidad_confirmada':True,'participante_ref':'persona-b'})]:
            self.separados([dict(self.eventos[0],**a),dict(self.eventos[1],**b)],self.registros)

    def test_enlaces_origenes_y_zoom_no_inventado(self):
        es=[dict(self.eventos[0],atajos=[{'h':'crm','url':'https://example.test/a'}]),dict(self.eventos[1],atajos=[{'h':'ghl','url':'https://example.test/b'}])]
        out,r=consolidar_confirmados(es,self.registros,HOY)
        self.assertEqual({x['url'] for x in out[0]['atajos']},{'https://example.test/a','https://example.test/b'})
        self.assertNotIn('join_url',out[0]);self.assertNotIn('celebrada',out[0]);self.assertNotIn('evidencia',out[0])

    def test_id_collision_y_otro_empleado_no_retira(self):
        self.separados(self.eventos+[dict(self.eventos[0],persona_id='otra')],self.registros)

    def test_idempotencia_no_pierde_origenes(self):
        out,r=consolidar_confirmados(self.eventos,self.registros,HOY)
        otra,r=consolidar_confirmados(out,self.registros,HOY);self.assertEqual(otra,out)

    def test_invalid_inputs(self):
        self.separados(self.eventos,None)
        self.assertEqual(consolidar_confirmados(None,[],HOY)[0],[])
        self.assertEqual(consolidar_confirmados(self.eventos,self.registros,'mañana')[0],self.eventos)

    def test_generador_actual_no_emite_identidades(self):
        # AST, no importar: el generador efectúa red/escrituras a nivel superior.
        tree=ast.parse(Path(__file__).with_name('generar_agenda.py').read_text())
        claves={k.value for node in ast.walk(tree) if isinstance(node,ast.Dict) for k in node.keys if isinstance(k,ast.Constant) and isinstance(k.value,str)}
        self.assertFalse({'referencia_reunion','participante_ref','identidad_confirmada'}&claves)
        self.assertTrue(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='deduplicar' for n in ast.walk(tree)))

    def test_snapshot_real_structural_sin_imprimir_identidades(self):
        path=Path(__file__).resolve().parents[1]/'data/agenda/agenda.json'
        if not path.exists():self.skipTest('No hay snapshot local; se mantienen fixtures sintéticos.')
        rows=json.loads(path.read_text()).get('eventos') or []
        groups={}
        for e in rows:
            if e.get('inicio','')[:10] in ('2026-10-01','2026-10-05') and e.get('inicio','')[11:16]=='08:00':
                groups.setdefault((e.get('persona_id'),e.get('inicio'),e.get('fin')),[]).append(e)
        duplicados=[g for g in groups.values() if len(g)>1 and {'crm','ghl'}<={e.get('fuente') for e in g}]
        if not duplicados:self.skipTest('La fuente cambió: no contiene el caso observado.')
        for g in duplicados:
            if any(e.get('referencia_reunion') or e.get('identidad_confirmada') for e in g):continue
            self.assertEqual(len(deduplicar(g)[0]),len(g));self.separados(g,[])

if __name__=='__main__':unittest.main()
