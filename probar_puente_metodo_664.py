import sys,json,copy,types,unittest,subprocess,shutil,os
from pathlib import Path
from unittest.mock import patch
APP=Path(__file__).resolve().parent;sys.path.insert(0,str(APP))
import consejo_metodo_308 as C
import cerebro_api as API
HOY='2026-10-04'
class Puente664(unittest.TestCase):
    def entorno(self):
        ps=[{'id':'ops_fixture','estado':'activo','puestos':['operaciones']},{'id':'paid_fixture','estado':'activo','puestos':['trafficker']}]
        raw={'personas':ps,'clientes':[{'id':'fixture','estado':'activo','activo':True}],'asignaciones':[{'persona_id':'paid_fixture','cliente_id':'fixture','silla':'trafficker','desde':'2026-09-01','principal':True,'confianza':'confirmada'}]}
        p=types.SimpleNamespace(hoy_iso=lambda:HOY,contexto=lambda *a:{},ver=lambda *a:{'ok':True},_vigente=lambda *a:True,cartera_por_silla=lambda *a,**k:{'trafficker':{'fixture'}})
        return types.SimpleNamespace(E=types.SimpleNamespace(crudo=raw,nucleo_bloqueado=False),P=p,ACT=types.SimpleNamespace(es_activo_id=lambda cid:cid=='fixture'),ve_alguno=lambda *a:'todo',entrada_datos_modulo=lambda rel:{'modulos':[rel.split('/')[0]]},modulo_recortado=lambda *a:None)
    def leer(self,modo=None):
        S=self.entorno();actor=S.E.crudo['personas'][0];n=[0]
        regla={'regla':{'id':C.REGLA,'cadencia_dias':15,'responsable_role':'trafficker'},'clientes':[{'cliente_id':'fixture','estado_cohorte':'confirmada','cadencia_dias':15,'responsable_role':'trafficker','tipo_cohorte':'metodo_actual_recurrente','precio_privado':1470,'contrato':'NO_EXPORTAR_PRIVADO'}]}
        events=[{'evento_id':'evt_fixture','cliente_id':'fixture','fecha':'2026-10-01','celebrada':True,'cliente_confirmado':True,'rol_responsable_confirmado':'trafficker','fuente':'zoom','texto_raw':'NO_EXPORTAR_PRIVADO'}]
        def source(path):
            n[0]+=1
            if n[0]==5:
                if modo=='owner':S.E.crudo['personas'][1]['estado']='baja'
                elif modo=='celebracion':events.clear()
                elif modo=='ACT':S.ACT.es_activo_id=lambda cid:False
            return copy.deepcopy(regla if path==C.M.REGLAS else {'reuniones':events,'cobertura':{'completa':False}})
        class H:
            def _api_get(self,*a):raise AssertionError('No otra ruta')
            def responder(self,code,body):return code,body
        API.enganchar(H,S)
        with patch.object(C.M,'leer',side_effect=source):
            code,body=H()._api_get('/api/cerebro/operativo',{'area':['accounts']},actor,actor)
        self.assertEqual(code,200);return body
    def copiar(self,r,hoy=HOY):
        code=r"""const fs=require('fs'),vm=require('vm');const a=process.argv[1],hoy=process.argv[2];const c={URL,Date,Intl,Number};vm.createContext(c);for(const f of ['_tarea_ia.js','_prioridades_contexto_337.js'])vm.runInContext(fs.readFileSync(a+'/modulos/'+f,'utf8').replace(/^import[^;]+;\s*/gm,'').replace(/export /g,''),c);const r=JSON.parse(fs.readFileSync(0,'utf8'));process.stdout.write(c.encargoPrioridades337(r,'Cliente fixture',{},hoy));"""
        node=shutil.which('node') or os.environ.get('RO_NODE')
        if not node:raise RuntimeError('Se requiere Node en PATH o RO_NODE explícito para este fixture')
        out=subprocess.run([node,'-e',code,str(APP),hoy],input=json.dumps(r),text=True,capture_output=True);self.assertEqual(out.returncode,0,out.stderr);return out.stdout
    def test_cadena_API_motor_filtrar_encargo_reales(self):
        body=self.leer();self.assertEqual(len(body['recomendaciones']),1);r=body['recomendaciones'][0];m=r['metodo_308'];self.assertEqual(m['ultima_confirmada'],'2026-10-01');self.assertEqual(m['proxima_revision'],'2026-10-16');self.assertIsNone(m['reunion_agendada']);self.assertIsNone(m['incumplimiento'])
        t=self.copiar(r);self.assertIn('2026-10-01',t);self.assertIn('2026-10-16',t);self.assertIn('2026-10-04',t);self.assertIn('Comprobador: Account',t);self.assertIn('Ejecutor operativo: Trafficker',t);self.assertIn('no cita agendada',t);self.assertNotIn('paid_fixture',t)
        self.assertNotIn('NO_EXPORTAR_PRIVADO',json.dumps(body));self.assertNotIn('1470',json.dumps(body));self.assertNotIn('NO_EXPORTAR_PRIVADO',t)
    def test_owner_revocado_antes_respuesta_no_conserva_owner(self):
        body=self.leer('owner');self.assertEqual(body['recomendaciones'],[])
        self.assertNotIn('paid_fixture',json.dumps(body));self.assertNotIn('2026-10-01',json.dumps(body))
    def test_celebracion_eliminada_no_conserva_fecha_previa(self):
        r=self.leer('celebracion')['recomendaciones'][0];self.assertIsNone(r['metodo_308']['ultima_confirmada']);self.assertIsNone(r['metodo_308']['proxima_revision']);t=self.copiar(r);self.assertNotIn('2026-10-01',t);self.assertNotIn('2026-10-16',t);self.assertNotIn('metodo_celebracion_confirmada',t)
    def test_ACT_revocado_no_recomendacion(self):self.assertEqual(self.leer('ACT')['recomendaciones'],[])
    def test_dia_contexto_missing_distinto_omite_seccion_nueva(self):
        r=self.leer()['recomendaciones'][0]
        for hoy in ('','2026-10-05'):
            t=self.copiar(r,hoy);self.assertNotIn('Comprobador:',t);self.assertNotIn('Ejecutor operativo:',t)
            # El contenido genérico/evidencias legado permanece; el padre debe invalidar el contexto entero.
if __name__=='__main__':unittest.main()
