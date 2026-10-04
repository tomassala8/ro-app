const fs=require('fs'),vm=require('vm'),assert=require('assert');const b={};vm.createContext(b);
b.h=(tag,attrs={},...children)=>({tag,attrs,children:children.flat(Infinity),get isConnected(){return !!this.parent?.isConnected;},append(...ns){for(const n of ns.flat(Infinity)){if(n&&typeof n==='object')n.parent=this;this.children.push(n);}},replaceChildren(...ns){this.children=[];this.append(...ns);}});b.chipEstado=(a,t)=>b.h('span',{},t);b.panelPlanFuego255=()=>b.h('div',{},'Plan');b.metricasProyectoBaseline=()=>null;
for(const [file,names] of [['control_cartera',['pautaHorasControl','prepararControlCartera']],['_operaciones_equipo_262',['horasProyectoRango262','pautaProyectoRango262']],['_horas_fuegos_341',['ambitoFuegos341','horasFuego341']],['_account_fuegos_346',['accountFuego346','firmaAccountFuegos346']]])vm.runInContext('Object.assign(globalThis,(()=>{'+fs.readFileSync(__dirname+'/modulos/'+file+'.js','utf8').replace(/^import .*;\n/gm,'').replace(/export /g,'')+';return {'+names.join(',')+'};})());',b);
for(const file of ['_cabeceras_operaciones_423.js','_meta_semantica_285.js','_operaciones_fuegos_268.js'])vm.runInContext(fs.readFileSync(__dirname+'/modulos/'+file,'utf8').replace(/^import .*;\n/gm,'').replace(/export /g,''),b);
const W={serie:['2026-09-01','2026-10-02']},H='2026-10-03';
const row=(d,g,l,more={})=>({d,gasto_meta:g,leads_meta:l,medicion:{version:'220.1',fuente:'meta_insights',nivel:'account',periodo_valido:true,desde:d,hasta:d,fecha_lectura:'2026-10-03T08:00:00Z',cohorte:'resultados_meta_sin_union_crm_ni_cualificacion_ro',campos_observados:['gasto','leads'],tipo_lead:'lead',...more}});
const calc=(rs,c={})=>b.muestraMeta30Fuego268({serie:rs},W,c,H);
let tests=0;function t(name,f){f();tests++;}
t('typed same rows CPL',()=>{let m=calc([row('2026-10-01',10,2),row('2026-10-02',20,3)]);assert.equal(m.leads,5);assert.equal(m.cpl,6);assert.equal(m.cpl_acreditado,true);});
t('legacy counts observed but unknown CPL',()=>{let r=row('2026-10-02',20,3);delete r.medicion;let m=calc([r]);assert.equal(m.resultados,3);assert.equal(m.leads,null);assert.equal(m.cpl,null);});
t('commerce not leads/purchases',()=>{let m=calc([row('2026-10-02',20,3)],{tipo_negocio:'tienda_online'});assert.equal(m.leads,null);assert.equal(m.cpl,null);assert.equal(m.semantica.compras,false);});
t('event mismatch',()=>assert.equal(calc([row('2026-10-01',10,2),row('2026-10-02',20,3,{tipo_lead:'onsite_web_lead'})]).cpl,null));
t('wrong window',()=>assert.equal(calc([row('2026-10-02',20,3,{desde:'2026-09-01'})]).cpl,null));
t('spend absent in metadata',()=>assert.equal(calc([row('2026-10-02',20,3,{campos_observados:['leads']})]).cpl,null));
t('spend invalid among valid leads',()=>assert.equal(calc([row('2026-10-01',10,2),row('2026-10-02',null,3)]).cpl,null));
t('typed zero observed not positive empty',()=>{let m=calc([row('2026-10-02',0,0)]);assert.equal(m.leads,0);assert.equal(m.gasto,0);assert.equal(m.cpl,null);});
t('empty never zero',()=>{let m=calc([]);assert.equal(m.resultados,null);assert.equal(m.gasto,null);assert.equal(m.cpl,null);});
t('future metadata',()=>assert.equal(calc([row('2026-10-02',20,3,{fecha_lectura:'2026-10-04T00:00:00Z'})]).cpl,null));
t('unknown observation day',()=>assert.equal(b.muestraMeta30Fuego268({serie:[row('2026-10-02',20,3)]},W,{},undefined).cpl,null));
t('overflow not finite metric',()=>assert.equal(calc([row('2026-10-01',1e308,2),row('2026-10-02',1e308,3)]).cpl,null));
const text=n=>typeof n==='string'?n:(n?.children||[]).map(text).join(' ');
(async()=>{
 const render=async(rs,client={},truth={})=>{let cont={isConnected:true,children:[],append(...ns){for(const n of ns){if(n&&typeof n==='object')n.parent=this;this.children.push(n);}}};const c={id:'fixture',nombre:'Fixture',activo_confirmado:true,detalle:true,...client};const ctx={servidor:true,datos:{personas:[{id:'r',estado:'activo',puestos:['operaciones']}]},real:{id:'r',estado:'activo',puestos:['operaciones']},persona:{id:'r',estado:'activo',puestos:['operaciones']},ver:x=>({ok:x.tipo==='cliente_detalle'&&x.cliente_id==='fixture'}),hoy:H,clientesVisibles:[c],veModulo:()=>true,vigente:()=>true,nombre:()=>'',verdad:()=>({gravedad:'critico',...truth}),datosModulo:async ruta=>ruta.startsWith('captacion')?{clientes:[{cliente_id:'fixture',serie:rs}],ventanas:W}:{proyectos:[]}};await b.renderFuegos268(cont,ctx);return cont;};
 let raw=row('2026-10-02',20,3);delete raw.medicion;let view=await render([raw]);assert(text(view).includes('Resultados Meta · 30 días'));assert(text(view).includes('CPL sin acreditar'));assert(!text(view).includes('6,67 €'));tests++;
 view=await render([row('2026-10-02',20,3)]);assert(text(view).includes('Leads Meta · 30 días'));assert(text(view).includes('6,67 €'));assert(text(view).includes('no contactos únicos'));tests++;
 view=await render([row('2026-10-02',20,3)],{tienda_online:true});assert(text(view).includes('Resultados Meta · 30 días'));assert(text(view).includes('Tienda online'));assert(!text(view).includes('6,67 €'));tests++;
 for(const [truth,expected]of [[{motivos:['Señal real del proveedor']},'Señal real del proveedor'],[{motivos:[{texto:'Señal estructurada'}]},'Señal estructurada'],[{motivo:'Motivo principal',motivos:['Secundario']},'Motivo principal'],[{motivos:[null,{},'Señal posterior válida']},'Señal posterior válida']]){view=await render([],{},truth);assert(text(view).includes(expected));assert(!text(view).includes('Consulta las señales del cliente'));tests++;}
 const walk=(n,tag)=>[...(n?.tag===tag?[n]:[]),...(n?.children||[]).flatMap(x=>walk(x,tag))];
 assert.equal(walk(view,'table').length,1);assert.equal(walk(view,'th').length,17);assert.equal(walk(view,'details').length,1);assert.equal(walk(view,'details')[0].attrs.open,undefined);assert.equal(walk(view,'tbody')[0].children.length,1);tests++;
 console.log(`${tests} grupos PASS: helper285 real, CPL compatible y render Fuegos desconocido/typed/commerce.`);
})().catch(e=>{console.error(e);process.exit(1)});
