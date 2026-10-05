"""Puente AST676 real y transporte ficticio; nunca importa generador ni main."""
import ast,importlib.util,json,hashlib
from pathlib import Path
import probar_mensajes_crm_676 as m
fl,fuentes,hoy=m.publico_fixture676()
ns=m.cargar(m.NEW);main=next(n for n in ns['tree'].body if isinstance(n,ast.FunctionDef) and n.name=='main')
node=next(n for n in ast.walk(main) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='fuentes' for t in n.targets))
# Ejecuta también la asignación de cliente posterior, conservada por el generador.
cliente=next(n for n in ast.walk(main) if isinstance(n,ast.If) and isinstance(n.test,ast.Name) and n.test.id=='cid' and any(isinstance(k,ast.Subscript) and isinstance(k.value,ast.Name) and k.value.id=='fl' for k in ast.walk(n)))
scope_cliente={'fl':fl,'cid':'fixture'}
exec(compile(ast.Module(body=[cliente],type_ignores=[]),'<clienteFlAST676>','exec'),scope_cliente)
scope={**ns,'hora_vivo':fuentes['ghl']['hora'],'llamadas':0,'cap':{},'nuevos':{},'flujos_scope':None}
exec(compile(ast.Module(body=[node],type_ignores=[]),'<fuentesAST676>','exec'),scope)
lead=ns['leer_subcuenta'](m.Fake([m.msg()]),'sidFixture')['leads'][0]
auto=[lead];ini30=ns['inicio_dia'](30);fin=ns['inicio_dia'](0)
medicion=ns['sin_tocar_publico676'](auto,fl['cliente_id'],fl['sub_id'],fuentes['ghl']['hora'],ini30,fin,m.CUT)
branch=next(n for n in ast.walk(main) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='sin_tocar' for t in n.targets))
q={**ns,'auto':auto,'hace24':m.CUT-86400000};exec(compile(ast.Module(body=[branch],type_ignores=[]),'<sin_tocarreal>','exec'),q)
fila={'cliente_id':fl['cliente_id'],'sub_id':fl['sub_id'],'leads_30d':len(auto),'sin_tocar_24h':len(q['sin_tocar']),'sin_tocar_medicion':medicion}
print(json.dumps({'fl':fl,'fila':fila,'fuentes':scope['fuentes'],'hoy':hoy,'ahora_ms':m.CUT}))
