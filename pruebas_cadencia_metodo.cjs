const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const ruta=p=>path.join(__dirname,p);
const s=fs.readFileSync(ruta('modulos/_cadencia_metodo.js'),'utf8').replace(/^import[^;]+;\s*/gm,'').replaceAll('export function','function');
class FechaFixture extends Date{constructor(...a){super(...(a.length?a:['2026-10-03T12:00:00Z']));}}
const box={Date:FechaFixture,Intl};vm.createContext(box);const helper305=fs.readFileSync(ruta('modulos/_metodo_cohorte_305.js'),'utf8').replace(/export /g,'');vm.runInContext(`(()=>{${helper305};this.proyectarMetodo305=proyectarMetodo305;})()`,box);vm.runInContext(s+';this.split=separarCadencias;this.estado=estadoCadencia;this.texto=textoCadencia;this.ambito=ambitoCadencia307;',box);
const row={cliente_id:'a',regla_id:'seguimiento_quincenal_especialista',cadencia_dias:15,responsable_role:'trafficker',estado:'sin_dato',incumplimiento:null,responsables_ids:[],responsable_id:null,fuentes_operativas:[]};
let x=box.split([{cliente_id:'a'},{cliente_id:'b',importe:1470}],{hoy:'2026-10-03',sugerencias:[row]});assert.equal(x.historicos.length,1);assert.equal(x.historicos[0].cliente_id,'b');assert.equal(x.seguimiento.length,1);assert.equal(box.estado(row),'gris');assert.equal(box.estado({...row,estado:'confirmar_recencia'}),'gris');assert.equal(box.estado({...row,estado:'revisar_cadencia'}),'gris');assert.equal(box.estado({...row,estado:'en_cadencia'}),'gris');
assert.equal(box.split([{cliente_id:'a'}],null).historicos.length,1);
for(const invalid of [{...row,cadencia_dias:30},{...row,responsable_role:'account'},{...row,regla_id:'otra'}])assert.equal(box.split([{cliente_id:'a'}],{hoy:'2026-10-03',sugerencias:[invalid]}).historicos.length,1);
assert(box.texto(x.seguimiento[0]).includes('pendiente de evidencia'));
assert(box.texto(x.seguimiento[0]).includes('sin dato confirmado'));
const bloques=fs.readFileSync(ruta('modulos/mi_dia_bloques.js'),'utf8');
const desde=bloques.indexOf('function reunionesCartera('),hasta=bloques.indexOf("\ndef('bandeja_mia'",desde);
const fx={separarCadencias:box.split,yo:ctx=>ctx.persona.id,verdad:()=>null,ambitoCadencia307:box.ambito};vm.createContext(fx);vm.runInContext(bloques.slice(desde,hasta)+';this.cartera=reunionesCartera;',fx);
const actor={id:'account',estado:'activo',puestos:['account']};
const ctxAccount={real:{...actor},persona:{...actor},clientesVisibles:[{id:'a',activo_confirmado:true,detalle:true},{id:'b',activo_confirmado:true,detalle:true}],veModulo:()=>true,vigente:()=>true,hoy:'2026-10-03',carteraIds:new Set(['a','b']),clientes:[{id:'a',activo_confirmado:true,detalle:true},{id:'b',activo_confirmado:true,detalle:true}],ver:()=>({ok:true}),datos:{personas:[{...actor}]}};
const feed={clientes:[{cliente_id:'a',account_id:'account',estado:'sin_reunion'},{cliente_id:'b',account_id:'account',estado:'sin_reunion'}]};
const datos={dato:()=>feed,opcional:()=>({hoy:'2026-10-03',sugerencias:[row]})};const splitActual=fx.cartera(ctxAccount,datos);assert.equal(splitActual.sin.length,1);assert.equal(splitActual.sin[0].cliente_id,'b');assert.equal(splitActual.actuales.length,1);
const sinOverlay=fx.cartera(ctxAccount,{...datos,opcional:()=>null});assert.equal(sinOverlay.sin.length,2);assert.equal(sinOverlay.actuales.length,0);
const md=fs.readFileSync(ruta('modulos/mi_dia.js'),'utf8');
const b=md.indexOf('function cargador('),e=md.indexOf('\nasync function cargarConfig',b);assert(e>b);
const caches=new Map();const fixture={CACHE:caches,CONFIG:{},VIDA_CACHE_MS:300000,MODULOS:[],motivoDe:(status,error,modulo)=>({ok:false,error,modulo}),Object,Date,Set,Promise,ambitoCadencia307:box.ambito};vm.createContext(fixture);vm.runInContext(md.slice(b,e)+';this.cargador=cargador;',fixture);
(async()=>{
 let calls=0;const ctx={hoy:'2026-10-03',servidor:true,veModulo:()=>true,clientes:[{id:'a',activo_confirmado:true,detalle:true}],clientesVisibles:[{id:'a',activo_confirmado:true,detalle:true}],ver:()=>({ok:true}),real:{id:'p',estado:'activo',puestos:['account']},persona:{id:'p',estado:'activo',puestos:['account']},datos:{personas:[{id:'p',estado:'activo',puestos:['account']},{id:'view',estado:'activo',puestos:['account']}]},api:async p=>{assert.equal(p,'metodo/sugerencias');calls++;return {hoy:'2026-10-03',sugerencias:[row]};},datosModulo:()=>{throw new Error('No debe tratar el overlay como fichero.');}};
 const d=fixture.cargador(ctx);await d.precargar(['metodo/sugerencias']);assert.equal(d.opcional('metodo/sugerencias').sugerencias.length,1);assert.equal(caches.size,0);assert.equal(d.sueltos.length,0);
 const falla=fixture.cargador({...ctx,api:async()=>{throw {status:403,message:'Sin acceso'};}});await falla.precargar(['metodo/sugerencias']);assert.equal(falla.opcional('metodo/sugerencias'),null);assert.equal(box.split([{cliente_id:'a'}],falla.opcional('metodo/sugerencias')).historicos.length,1);
 let finish;const viejo=fixture.cargador({...ctx,api:()=>new Promise(r=>finish=r)});const wait=viejo.precargar(['metodo/sugerencias']);const nuevo=fixture.cargador({...ctx,persona:{id:'view',estado:'activo',puestos:['account']},api:async()=>({sugerencias:[]})});await nuevo.precargar(['metodo/sugerencias']);finish({hoy:'2026-10-03',sugerencias:[row]});await wait;assert.equal(nuevo.opcional('metodo/sugerencias').sugerencias.length,0);assert.equal(caches.size,0);
 console.log('Cadencia: cohorte sólo overlay, unknown gris, cita/celebración separadas, fallo conserva histórico, API exacta y aislamiento sin caché compartida: OK.');
})().catch(e=>{console.error(e);process.exitCode=1;});
