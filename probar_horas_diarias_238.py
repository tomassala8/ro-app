import ast, copy, datetime as dt, re, types, unittest
from pathlib import Path
from fuentes_horas.diario_238 import construir_diarios


def fixture():
    return {'meta':{'generado':'2026-10-03 02:56'},'entradas':[
        {'id':'one','usuario_id':'1','inicio':'2026-10-02T10:00:00+02:00','horas':2,'descripcion':'not exported'},
        {'id':'zero','usuario_id':'1','inicio':'2026-10-01T10:00:00+02:00','horas':0}]},[
        {'id':'a','correo':'a@fixture.invalid','estado':'activo','zona':'Europe/Madrid'},
        {'id':'b','correo':'b@fixture.invalid','estado':'activo','zona':'America/Caracas'}],[
        {'id':1,'correo':'a@fixture.invalid'},{'id':2,'correo':'b@fixture.invalid'}]

class Tests(unittest.TestCase):
    def run_series(self, h=None,p=None,u=None):
        a,b,c=fixture();return construir_diarios(h or a,p or b,u or c,'2026-10-03')
    def test_positive_zero_unknown_and_allowlist(self):
        r=self.run_series()['a'];self.assertEqual(r['dias'][-1]['horas'],2);self.assertEqual(r['dias'][-2]['horas'],0);self.assertIsNone(r['dias'][0]['horas']);self.assertEqual(r['cobertura'],'parcial');self.assertNotIn('descripcion',str(r))
    def test_replay(self):
        h,p,u=fixture();h['entradas'].append(copy.deepcopy(h['entradas'][0]));self.assertEqual(self.run_series(h,p,u)['a']['dias'][-1]['entradas'],1)
    def test_collision_unknown(self):
        h,p,u=fixture();h['entradas'].append({**h['entradas'][0],'horas':3});self.assertIsNone(self.run_series(h,p,u)['a']['dias'][-1]['horas'])
    def test_cross_zone(self):
        h,p,u=fixture();h['entradas'].append({'id':'tz','usuario_id':2,'inicio':'2026-10-02T01:00:00+02:00','horas':1});self.assertEqual(self.run_series(h,p,u)['b']['dias'][-2]['horas'],1);self.assertIsNone(self.run_series(h,p,u)['b']['dias'][-1]['horas'])
    def test_canonical_not_name(self):
        h,p,u=fixture();u[0]={'id':1,'nombre':'a'};self.assertIsNone(self.run_series(h,p,u)['a']['dias'][-1]['horas'])
    def test_ambiguous_person(self):
        h,p,u=fixture();p.append(copy.deepcopy(p[0]));self.assertNotIn('a',self.run_series(h,p,u))
    def test_no_unconfirmed_zone(self):
        h,p,u=fixture();p[0].pop('zona');self.assertNotIn('a',self.run_series(h,p,u))
    def test_invalid_counts_dates(self):
        for bad in [-1,float('nan'),float('inf'),True,11,'2']:
            h,p,u=fixture();h['entradas'][0]['horas']=bad;self.assertIsNone(self.run_series(h,p,u)['a']['dias'][-1]['horas'])
        h,p,u=fixture();h['entradas'][0]['inicio']='2026-10-02T10:00:00';self.assertIsNone(self.run_series(h,p,u)['a']['dias'][-1]['horas'])
    def test_invalid_future_source(self):
        for source in ['bad','2026-10-04 02:56']:
            h,p,u=fixture();h['meta']['generado']=source;self.assertEqual(self.run_series(h,p,u),{})
    def test_producer_wiring(self):
        s=Path('fuentes_horas/generar_horas.py').read_text();ast.parse(s);self.assertIn('construir_diarios(H, personas_fuente, miembros_clickup(), str(HOY))',s);self.assertIn("'diario_238': diarios_238[pid]",s)
    def test_actual_scoped_projection(self):
        source=ast.parse(Path('servir.py').read_text());f=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='recortar_modulo')
        allowed={'a'}
        P=types.SimpleNamespace(_HILO=types.SimpleNamespace(real=None),puestos_de=lambda p:set(),ver=lambda p,d,cp:{'ok':d.get('persona_id',p['id']) in cp['allowed']},solo_su_cartera=lambda p:False,CLAVES_TEXTO_LIBRE=re.compile(r'^$'),enlace_seguro=lambda s:s)
        env={'P':P,'quitar_para':lambda *a:set(),'CLAVES_CUOTA':re.compile('cuota'),'CLAVES_INVERSION':re.compile('inv'),'CLAVES_RENTABILIDAD':re.compile('coste'),'CLAVES_ENLACE':re.compile('url'),'_quita':lambda *a:False}
        exec(compile(ast.Module(body=[f],type_ignores=[]),'<actual serving projection>','exec'),env)
        diarios=self.run_series();doc={'personas':[{'persona_id':pid,'diario_238':series} for pid,series in diarios.items()]}
        out=env['recortar_modulo']({'id':'a'},{'allowed':allowed},doc);self.assertEqual([p['persona_id'] for p in out['personas']],['a']);self.assertEqual(out['personas'][0]['diario_238']['dias'][-1]['horas'],2)
        out=env['recortar_modulo']({'id':'b'},{'allowed':{'b'}},out);self.assertEqual(out['personas'],[])

if __name__=='__main__':unittest.main()
