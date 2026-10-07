const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const c={Intl,Date,Set,Map};vm.createContext(c);
for(const file of ['control_cartera.js','_produccion_accounts_237.js'])vm.runInContext(fs.readFileSync('modulos/'+file,'utf8').replace(/^import[^;]+;\s*/gm,'').replace(/export /g,''),c);
const owner=(pid,confianza='confirmada')=>({persona_id:pid,principal:true,confianza});
const cli=(id,pid='a')=>({id,detalle:true,activo_confirmado:true,equipo:{account:pid?[owner(pid)]:[]}});
const p=(id,a=null,t=null)=>({cliente_id:id,cliente:id,_revision_account:a,_revision_tecnica:t,rev_account:999,cerradas_semana:50,account_id:'legacywrong'});
const m=(n=0,mas48=0)=>({n,mas48,fecha:'2026-10-03T09:00:00'});
const fixture=()=>({hoy:'2026-10-03',clientes:[cli('c'),cli('d','b'),cli('e')],personas:[{id:'a',estado:'activo'},{id:'b',estado:'activo'}],asignaciones:[],proyectos:[p('c',m(2,1),m()),p('d'),p('e')]});
let n=0,f=fixture(),r=c.resumirAccountsProduccion237(f),a=r.grupos.find(g=>g.account_id==='a');
assert.equal(a.proyectos,2);assert.equal(a.account.observadas,2);assert.equal(a.account.medidos,1);assert(!a.account.completo_en_copia);assert.equal(a.tecnica.observadas,0);n++;
assert.equal(r.grupos.find(g=>g.account_id==='b').account.observadas,null);assert.equal(c.textoRevisionAccount237(r.grupos.find(g=>g.account_id==='b').account).principal,'Sin dato');n++;
f=fixture();f.clientes[0].equipo.account[0].confianza='alta';r=c.resumirAccountsProduccion237(f);assert.equal(r.grupos.find(g=>g.account_id==='a').por_confirmar,1);n++;
f=fixture();f.clientes[0].equipo.account.push(owner('b'));r=c.resumirAccountsProduccion237(f);assert(r.grupos.find(g=>g.account_id===null).clientes_ids.includes('c'));n++;
f=fixture();f.personas[0].estado='baja';r=c.resumirAccountsProduccion237(f);assert(!r.grupos.some(g=>g.account_id==='a'));n++;
f=fixture();f.clientes[0].equipo.account=[];f.asignaciones=[{cliente_id:'c',silla:'account',...owner('b'),hasta:'2026-10-02'}];r=c.resumirAccountsProduccion237(f);assert(r.grupos.find(g=>g.account_id===null).clientes_ids.includes('c'));n++;
for(const modify of [x=>x.clientes[0].activo_confirmado=false,x=>x.clientes[0].detalle=false,x=>x.clientes.push(cli('c')),x=>x.proyectos.push(p('c')),x=>x.clientes=x.clientes.filter(t=>t.id!=='c')]){f=fixture();modify(f);r=c.resumirAccountsProduccion237(f);assert(!r.proyectos.some(t=>t.cliente_id==='c'));n++;}
f=fixture();f.proyectos[0]._revision_account=m(.5,0);r=c.resumirAccountsProduccion237(f);assert.equal(r.grupos.find(g=>g.account_id==='a').account.observadas,null);n++;
// El baseline252 sustituye estructura6cols por12; se conservan los mismos asserts de scope y drill.
vm.runInContext(fs.readFileSync('modulos/_produccion_baseline.js','utf8').replace(/export /g,''),c);
class N{constructor(tag){this.tag=tag;this.attrs={};this.events={};this.children=[];this.style={};this.isConnected=true;}append(...xs){this.children.push(...xs.flat(Infinity).filter(x=>x!=null));}replaceChildren(...xs){this.children=[];this.append(...xs);}setAttribute(k,v){this.attrs[k]=String(v);}set className(v){this.attrs.class=v;}addEventListener(k,v){this.events[k]=v;}focus(){this.focused=true;}scrollIntoView(){this.scrolled=true;}}
c.Node=N;c.document={createElement:tag=>new N(tag),createTextNode:x=>String(x)};
const composants=fs.readFileSync('componentes.js','utf8');vm.runInContext(composants.slice(composants.indexOf('export function h('),composants.indexOf('const svgNS =')).replace('export ',''),c);
const h=c.h,all=node=>node&&typeof node==='object'?[node,...(node.children||[]).flatMap(all)]:[],text=node=>typeof node==='string'?node:node?.children?.map(text).join(' ')||'';
const dependencia296=fs.readFileSync('modulos/_produccion_creadas_287.js','utf8').replace(/^import[^;]+;\s*/gm,'').replace(/export /g,'');
c.panelComparacionSemanal296=vm.runInContext('(function(){'+dependencia296+';return panelComparacionSemanal296;})()',c);
let live=true,allowed=true,navigations=[];f=fixture();
Object.assign(c,{D:{hoy:'2026-10-03',lunes:'2026-09-28',fuentes:{},revisiones:[],no_planificado:[]},proyectos:f.proyectos,ctx:{clientesVisibles:f.clientes,datos:{personas:f.personas,asignaciones:[]},ver:()=>({ok:allowed}),navegar:x=>navigations.push(x)},vigente:()=>live,alias:id=>({a:'Account A',b:'Account B'})[id]||id,
 S:[0,4,8,12,16],vacio:o=>h('empty',{},o.titulo),cliNombre:new Map()});
const source=fs.readFileSync('modulos/produccion.js','utf8'),body=source.slice(source.indexOf('    function pintarProyectos(z)'),source.indexOf('    // ================================================================ equipo'));
vm.runInContext(body,c);const root=h('root');c.pintarProyectos(root);
const tables=()=>all(root).filter(x=>x.tag==='table'),filas=()=>all(tables()[1]).find(x=>x.tag==='tbody').children.length;
assert.equal(text(all(root).filter(x=>x.tag==='h2')[0]),'Por account');assert.equal(text(all(root).filter(x=>x.tag==='h2')[1]),'Por proyecto');assert.equal(all(tables()[0]).filter(x=>x.tag==='th').length,12);assert.equal(filas(),3);n++;
const btn=all(root).find(x=>x.tag==='button'&&x.attrs['aria-label']==='Ver Account A');assert(btn);btn.events.click();assert.equal(filas(),2);assert(all(root).some(x=>x.focused&&x.scrolled));n++;
const reset=all(root).find(x=>x.tag==='button'&&text(x).includes('Restablecer account'));reset.events.click();assert.equal(filas(),3);n++;
let oldTable=tables()[1];live=false;btn.events.click();assert.equal(tables()[1],oldTable);n++;
live=true;allowed=false;btn.events.click();assert.equal(tables()[1],oldTable);n++;
assert.equal(navigations.length,0);console.log(`237 PASS: ${n} casos helper/render reales, alcance, owners, unknown/cero observado, cobertura y drill/restablecer/vigencia; layout25212columnas.`);
