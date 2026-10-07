// Integra modelo390 y pintor/caller MiDía reales en DOM sintético.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const prefix=fs.readFileSync(__dirname+'/pruebas_control_macro_138.cjs','utf8').split('const macros=root.desc()')[0];
const {b,h,N,cli}=new Function('require','__dirname',prefix+';return {b,h,N,cli};')(require,__dirname);
N.prototype.setAttribute=function(k,v){this.attrs[k]=String(v);};Object.defineProperty(N.prototype,'className',{get(){return this.attrs.class||'';},set(v){this.attrs.class=v;}});N.prototype.append=function(...ks){for(const x of ks.flat(Infinity).filter(x=>x!=null)){this.k.push(x);if(x instanceof N){x.parent=this;x.isConnected=this.isConnected;}}};N.prototype.remove=function(){if(this.parent)this.parent.k=this.parent.k.filter(x=>x!==this);this.isConnected=false;};
for(const name of ['_historial_diario_364','_bandas_horas_381']){
 const src=fs.readFileSync(__dirname+'/modulos/'+name+'.js','utf8');const exported=[...src.matchAll(/export (?:async )?function (\w+)/g)].map(x=>x[1]);
 vm.runInContext('Object.assign(globalThis,(()=>{'+src.replace(/^import .*;$/gm,'').replace(/export /g,'')+';return {'+exported.join(',')+'};})())',b);
}
// La prueba base expone sólo renderer y guard390; aquí cargamos todos los exports reales.
const source=fs.readFileSync(__dirname+'/modulos/_imputa_personal_390.js','utf8'),exported=[...source.matchAll(/export (?:async )?function (\w+)/g)].map(x=>x[1]);
vm.runInContext('Object.assign(globalThis,(()=>{'+source.replace(/^import .*;$/gm,'').replace(/export /g,'')+';return {'+exported.join(',')+'};})())',b);
const ps=[{id:'ops',estado:'activo',puestos:['operaciones']},{id:'account',estado:'activo',puestos:['account']}],cp=x=>JSON.parse(JSON.stringify(x));
const c={servidor:true,hoy:'2026-10-05',real:cp(ps[0]),persona:cp(ps[0]),datos:{personas:cp(ps),asignaciones:[{cliente_id:'uno',persona_id:'account',silla:'account',principal:true,desde:'2026-01-01'}]},clientes:cli,clientesVisibles:cli,carteraPorSilla:{},veModulo:()=>true,ver:()=>({ok:true}),vigente:()=>true,nombre:x=>x};
const days=Array.from({length:90},(_,i)=>{const fecha=new Date(Date.parse('2026-10-05T00:00:00Z')-(90-i)*864e5).toISOString().slice(0,10);return {fecha,estado:fecha==='2026-10-03'?'observado':'sin_dato',horas:fecha==='2026-10-03'?38.37:null,entradas:fecha==='2026-10-03'?1:null};});
c.api=async()=>({version:'362.1',estado:'copia_observada',generado:'2026-10-05T01:00:00Z',fuente:'ClickUp entradas',fuente_version:'359.1',sha256_candidato:'21abf5db866bfd0ed9805b61bf686a625f613d37d21ce80095ef998f209f6280',cobertura:'parcial',unidad:'h',cumplimiento:null,capacidad_contractual:null,personas:[{persona_id:'account',historial_diario:{version:'359.1',fuente:'ClickUp entradas',cobertura:'parcial',unidad:'h',zona:'Europe/Madrid',zona_confirmada:true,desde:days[0].fecha,hasta:days.at(-1).fecha,corte_fecha:'2026-10-05',fecha_fuente_utc:'2026-10-05T00:30:00Z',atribucion:'inicio',duracion_cerrada_confirmada:false,sin_registros_no_equivale_a_cero:true,dias:days}}]});
(async()=>{
 const model=await b.cargarImputa390(c,['account']);assert(model);const cell=b.celdaImputa390(c,model,'account');assert.equal(cell.total,38.37);assert.equal(cell.valor,38.37);assert.equal(cell.estado,'gris');assert.equal(cell.banda_referencia.color,'verde');
 const root=b.panelControlCartera(c,{opcional:n=>n==='horas_personales/390'?model:null},'operaciones',()=>true);
 const button=root.desc().find(n=>n.tag==='button'&&n.attrs['aria-label']?.startsWith('account · Imputa'));assert(button);assert.equal(button.textContent,'38,4');assert(button.attrs.class.includes('ref390-verde'));assert(!button.textContent.includes('Ref.'));assert(root.textContent.includes('no jornada confirmada'));
 N.prototype.focus=function(){};
 let checks=1;
 for(const [name,change] of [['modulo',x=>x.veModulo=m=>m!=='horas'],['grant',x=>x.ver=()=>({ok:false})],['vista',x=>x.persona.id='account'],['baja',x=>x.datos.personas[1].estado='baja'],['duplicado',x=>x.datos.personas.push(cp(x.datos.personas[0]))]]){
  const current={...c,real:cp(ps[0]),persona:cp(ps[0]),datos:{...c.datos,personas:cp(ps)},veModulo:()=>true,ver:()=>({ok:true})},actual=await b.cargarImputa390(current,['account']);
  const view=b.panelControlCartera(current,{opcional:n=>n==='horas_personales/390'?actual:null},'operaciones',()=>true),hours=view.desc().find(n=>n.tag==='button'&&n.attrs['aria-label']?.startsWith('account · Imputa'));
  hours.listeners.click();assert(view.textContent.includes('38,4 h personales observadas'));change(current);
  const otra=view.desc().find(n=>n.tag==='button'&&n.attrs['aria-label']?.startsWith('account · Revisa'));otra.listeners.click();
  assert(!view.textContent.includes('38,4 h personales observadas'),name+' no conserva detalle preabierto');assert.equal(hours.textContent,'—');assert.equal(hours.attrs.class,'c250 gris');assert(hours.attrs['aria-label'].includes('Sin dato'));
  hours.listeners.click();assert(!view.textContent.includes('38,4 h personales observadas'),name+' no vuelve a abrir detalle');checks++;
 }
 console.log(checks+' grupos integración390B PASS · caller/celda/formato/referencia/roles/grants/detallepreabierto.');
})().catch(e=>{console.error(e.message);process.exitCode=1});
