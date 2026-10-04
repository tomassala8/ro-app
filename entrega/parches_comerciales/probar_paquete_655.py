from pathlib import Path
import subprocess,sys
B=Path(__file__).resolve().parent
commands=[('652', 'probar_revision_cerradas_652.py'),('653','probar_integridad_eventos_653.py'),('653','probar_embudo_eventos.py'),('654','probar_resiliencia_654.py'),('654','probar_cerebro_operativo.py')]
for folder,file in commands:
 if folder=='653' and file=='probar_embudo_eventos.py':
  code="import importlib.util,sys,runpy;import embudo_eventos_candidato_653 as m;sys.modules['embudo_eventos']=m;runpy.run_path('probar_embudo_eventos.py',run_name='__main__')"
  args=[sys.executable,'-c',code]
 else: args=[sys.executable,file]
 result=subprocess.run(args,cwd=B/folder,capture_output=True,text=True,timeout=60)
 print(folder,file,'PASS' if result.returncode==0 else 'FAIL')
 print((result.stdout+result.stderr).strip())
 if result.returncode:raise SystemExit(result.returncode)
