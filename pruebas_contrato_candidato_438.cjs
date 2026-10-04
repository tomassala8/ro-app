// Contrato real candidato privado → proyección backend → modelo UI. Sólo conteos en salida.
const fs=require('fs'),assert=require('assert/strict'),cp=require('child_process');
const prefix=fs.readFileSync(__dirname+'/pruebas_operaciones_equipo_262.cjs','utf8').split('(async()=>{')[0];
const {c}=new Function('require','__dirname',prefix+';return {c};')(require,__dirname);
const py=`import json,datetime,collections
from pathlib import Path
from unittest.mock import patch
import ejemplos_creador_api_438 as A
from identidades_clickup_204 import resolver
root=Path.cwd();p=root.parent/'RECUPERACION_CODEX_2026-10-03/staging_ejemplos_creador_438_v2/candidato.json'
with patch.object(A,'SHA','23ace1eb937926c13c18a05c6ac0e42e4b2a7b40585de0be606f19efa474696d'),patch.object(A,'MANIFEST_SHA','18c982b30ae811016c41af16ccee3db941d2d4530e198a2ba4edbe987656240f'):
 d,m,cat=A.cargar(p)
 rawps=json.loads((root/'data/personas.json').read_text());count=collections.Counter(p.get('id') for p in rawps if isinstance(p,dict));ps=[{k:p.get(k) for k in ('id','estado','activo','puestos')} for p in rawps if isinstance(p,dict) and count[p.get('id')]==1 and p.get('estado')=='activo' and p.get('activo') is not False and isinstance(p.get('puestos'),list) and p['puestos']]
 members=A.D._leer(A.D.OLD/'_crudo/clickup/miembros.json',m['base395']['fuentes_sha256']['miembros'],2_000_000);ident=resolver(rawps,members.get('miembros',[])+members.get('usuarios_no_miembros_vistos',[]))['por_usuario']
 pids=sorted(p['id'] for p in ps);cids=sorted({r['cliente_id'] for r in d['filas']});now=datetime.datetime.now(datetime.timezone.utc);rows=A.proyectar(d,pids,cids,now,cat,ident)
 payload={'version':'438.1','estado':'copia_observada','sha256_candidato':A.SHA,'generado':A.iso(now),'corte_preparacion_utc':d['corte_preparacion_utc'],'fuente':'clickup_cache_local','cobertura':'parcial','persona_ids':pids,'cliente_ids':cids,'filas':rows,'atribucion':'creador_ID_exacto','creacion_no_es_planificacion':True,'cumplimiento':None}
 print(json.dumps({'dto':payload,'personas':ps}))`;
const {dto,personas}=JSON.parse(cp.execFileSync('python3',['-c',py],{cwd:__dirname,encoding:'utf8',maxBuffer:5_000_000}));
const actor=personas.find(p=>p.puestos.includes('operaciones'));assert(actor);const clients=dto.cliente_ids.map(id=>({id,activo_confirmado:true,detalle:true}));
const ctx={servidor:true,hoy:'2026-10-04',real:{...actor},persona:{...actor},datos:{personas,asignaciones:[]},clientes:clients.map(x=>({...x})),clientesVisibles:clients.map(x=>({...x})),ver:()=>({ok:true}),veModulo:()=>true,vigente:()=>true};
const before=c.ambitoEjemplos438(ctx),model=c.modeloEjemplos438(ctx,dto,before);assert(model);assert.equal(model.filas.length,2172);assert(model.filas.every(r=>!/[<>]|https?:\/\/|(?:password|pwd|pass|clave|token)\s*[:=]/i.test(r.titulo_saneado)));
const corrupted=structuredClone(dto);corrupted.filas[0].titulo_saneado='password=private_fixture';assert.equal(c.modeloEjemplos438(ctx,corrupted,before),null);
ctx.clientes[0].activo_confirmado=false;assert.equal(c.modeloEjemplos438(ctx,dto,before),null);
console.log('PASS438 candidato v2 → backend real → VM modelo UI real:2172; secret/cambioACT rechazados. No HTTP ni auth real.');
