"""Reproducciones independientes sobre AST real; no importa bootstrap ni abre DB."""
import ast,json,math
from pathlib import Path
from datetime import date,timedelta
APP=Path(__file__).parent
tree=ast.parse((APP/'mi_trabajo.py').read_text())
ns={'math':math,'date':date,'timedelta':timedelta,'persona':lambda _: {},'hoy_de':lambda _:date(2026,10,3),'es_dia':lambda x:date.fromisoformat(x) if x else None}
funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('raras_de','laborables_atras','numero_horas_370','suma_horas_370')]
exec(compile(ast.Module(body=funcs,type_ignores=[]),'real370B','exec'),ns)
checks=[]
for value,label in [(None,'null'),('2','string'),(True,'bool'),(math.inf,'inf')]:
 rs=ns['raras_de']('p',{'2026-10-02':{'cu':value,'app':None}},None,{'jornada':[]},{},lambda _:False)
 assert rs==[]
 checks.append('raras_'+label+'_sin_alerta_falsa')
rs=ns['raras_de']('p',{'2026-10-02':{'cu':1e308,'app':1e308}},None,{'jornada':[]},{},lambda _:False)
assert rs==[]
checks.append('overflow_sin_Infinity')
# Segmento de get_estado que compone el DTO de días, incluidas marcas RO existentes.
g=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='get_estado'][0]
start=next(i for i,n in enumerate(g.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='marcas' for t in n.targets))
end=next(i for i,n in enumerate(g.body[start:],start) if isinstance(n,ast.FunctionDef) and n.name=='ve_cli')
v={**ns,'D':{'horas_dia':[]},'ids':{'p'},'cambios_personales':[{'campo':'horas','estado':'simulado','marca':'ro:fixture','quien':'p','tarea':'t','dia':'2026-10-02','minutos':60}],'tareas_autorizadas':{'t'}}
exec(compile(ast.Module(body=g.body[start:end],type_ignores=[]),'dto370B','exec'),v)
x=v['dias']['p']['2026-10-02'];assert x['cu'] is None and x['cu_observado'] is False and x['app']==1 and x['app_observado'] is True
checks.append('RO_solo_CU_ausente_null')
# El mismo segmento sí conserva la deduplicación real mediante marca ro:<clave>.
v={**ns,'D':{'horas_dia':[{'persona_id':'p','dias':{'2026-10-02':1},'marcas':['ro:fixture']}]},'ids':{'p'},'cambios_personales':[{'campo':'horas','estado':'enviado','marca':'ro:fixture','quien':'p','tarea':'t','dia':'2026-10-02','minutos':60}],'tareas_autorizadas':{'t'}}
exec(compile(ast.Module(body=g.body[start:end],type_ignores=[]),'dto370B','exec'),v)
x=v['dias']['p']['2026-10-02'];assert x['cu']==1 and x['app'] is None and not x['app_observado']
assert v['horas_app'][0]['en_clickup'] is True
print(json.dumps({'contratos_defensivos_verificados':checks,'marca_RO_en_CU_no_dobleconteo':'PASS'},ensure_ascii=False))
