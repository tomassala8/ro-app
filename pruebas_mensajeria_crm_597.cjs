const fs=require('node:fs'),assert=require('node:assert/strict'),vm=require('node:vm');
const base=fs.readFileSync(__dirname+'/pruebas_crm_compacto_245.cjs','utf8').split('vm.createContext(e);')[0];
const {e,h,N}=new Function('require',base+';return {e,h,N};')(require);
(async()=>{
const savedNow=Date.now;Date.now=()=>Date.parse('2026-10-04T12:00:00Z');
try{
const M=await import('data:text/javascript;base64,'+Buffer.from(fs.readFileSync(__dirname+'/modulos/_crm_mediciones.js','utf8')).toString('base64'));Object.assign(e,M);const M677=await import('data:text/javascript;base64,'+Buffer.from(fs.readFileSync(__dirname+'/modulos/_contacto_observado_677.js','utf8')).toString('base64'));Object.assign(e,M677);
const src=fs.readFileSync(__dirname+'/modulos/crm.js','utf8'),piece=(a,b)=>src.slice(src.indexOf(a),src.indexOf(b,src.indexOf(a)));let options,nav=0,vigente=true,n=0;
const test=(t,f)=>{f();n++;console.log('PASS '+t)};
e.tablaDensa=o=>{options=o;return h('table',{},o.filas.map(f=>h('tr',{},o.columnas.map(c=>h('td',{},c.celda(f))))));};e.notaCompacta336=(h,t,...xs)=>h('details',{},t,...xs);e.chipEstado=(s,t)=>h('span',{},t);e.semaforo=()=> 'gris';e.fDiaRO=x=>x;
vm.createContext(e);vm.runInContext(piece('function sumar(','const frescuraGHL')+piece('function pintarFlujos(','// ------------------------------------------------------------------ pestaña: montajes de altas'),e);
const fuente={hora:'2026-10-03T12:00:00Z',estado:'bien'},hoy='2026-10-04';
const raw=(sid='sidA',x={})=>({cliente_id:'cliente_fixture',sub_id:sid,nombre:'Fixture',errores_lectura:[],enlaces:{},leads_30d:10,velocidad:{auto_5min:2},whatsapp:{enviados:10,fallidos:1},sms:{enviados:2,fallidos:0},correo:{enviados:4,fallidos:1},...x});
const norm=(r=raw(),f=fuente)=>M.normalizarFilaCRM(r,f,hoy);
const ctx={vigente:()=>vigente,navegar:()=>nav++},doc={fuentes:{ghl:fuente},correo_ro:{rebote_pct:1,fecha:'2026-10-02'}};
const draw=rows=>{const zone=h('main',{});e.pintarFlujos(zone,ctx,doc,{base:rows});return zone;};
const cell=(key,row)=>options.columnas.find(c=>c.clave===key).celda(row);
test('baseline congelado mezcla10/null ynull/2; actual no ratio',()=>{
 const a=norm(raw('sidA',{whatsapp:{enviados:10,fallidos:null}})),b=norm(raw('sidB',{whatsapp:{enviados:null,fallidos:2}}));
 const legacy=(10+0?2*100/10:null);assert.equal(legacy,20);
 const s=e.sumar([a,b]);assert.equal(s.pctWa,null);assert.equal(s.wa,null);assert.equal(s.waf,null);assert.equal(s.waMedicion.observadas,0);
 draw([a,b]);assert.equal(cell('wa',a).textContent,'—');assert.equal(cell('wa',b).textContent,'—');assert(cell('wa',b).attrs.title.includes('2 fallos observados'));
});
test('paired subset n/N retain positive and explicitzero no fullcoverage',()=>{
 const a=norm(),b=norm(raw('sidB',{whatsapp:{enviados:4,fallidos:0}})),c=norm(raw('sidC',{whatsapp:{enviados:null,fallidos:2}}));
 const m=M.agregarMensajesCRM597([a,b,c],'whatsapp');assert.equal(m.enviados,14);assert.equal(m.fallidos,1);assert.equal(m.observadas,2);assert.equal(m.total,3);assert.equal(m.cobertura,'parcial');
 draw([a,b,c]);assert(cell('wa',b).textContent.includes('0 de 4'));assert.equal(cell('wa',b).attrs['data-color'],'gris');
});
test('knownzero0/0 messages not rate orgreen',()=>{
 const r=norm(raw('sidA',{whatsapp:{enviados:0,fallidos:0}}));const s=e.sumar([r]);assert.equal(s.wa,0);assert.equal(s.waf,0);assert.equal(s.pctWa,null);draw([r]);assert(cell('wa',r).textContent.includes('0 de 0'));assert.equal(cell('wa',r).attrs['data-color'],'gris');
});
test('null fail is notzero%; malformed partial counts no rate',()=>{
 for(const v of [null,undefined,true,-1,0.5,NaN,Infinity,11]){const r=norm(raw('sidA',{whatsapp:{enviados:10,fallidos:v}}));assert.equal(M.agregarMensajesCRM597([r],'whatsapp').pct,null);draw([r]);assert.equal(cell('wa',r).textContent,'—');}
});
test('source error stale impossible future and invalidoffset nullchannels',()=>{
 for(const f of [{...fuente,estado:'error'},{...fuente,error:'red'},{...fuente,hora:'2020-01-01T12:00:00Z'},{...fuente,hora:'2026-10-04T18:00:00Z'},{...fuente,hora:'2026-02-30T12:00:00Z'},{...fuente,hora:'2026-10-03T12:00:00+02:99'},{...fuente,hora:'2026-10-03T12:00:00+15:00'}]){
  const r=norm(raw(),f);for(const k of ['whatsapp','sms','correo']){assert.equal(r[k].enviados,null);assert.equal(r[k].fallidos,null);}assert.equal(e.sumar([r]).pctWa,null);draw([r]);assert.equal(cell('auto',r).textContent,'—');assert.equal(cell('wa',r).textContent,'—');
 }
});
test('missing lead sample cannot promote legacyzero messageplaceholders',()=>{const r=norm(raw('sidA',{leads_30d:null,whatsapp:{enviados:0,fallidos:0}}));assert.equal(r.whatsapp.enviados,null);assert.equal(r.whatsapp.fallidos,null);assert.equal(e.sumar([r]).pctWa,null);});
test('row and channel error no revive lastpositive',()=>{
 const r=norm(raw('sidA',{errores_lectura:['mensajes']}));assert.equal(r.whatsapp.enviados,null);
 const m=norm(raw('sidA',{whatsapp:{enviados:10,fallidos:1,error:'red'}}));assert.equal(m.whatsapp.enviados,null);assert.equal(m.correo.enviados,4);
});
test('incompatible cuts/windows not mix even matchingmonth',()=>{
 const a=norm(),b=norm(raw('sidB'),{...fuente,hora:'2026-10-02T12:00:00Z'});assert.equal(M.agregarMensajesCRM597([a,b],'whatsapp').pct,null);
 const tampered={...a,_medicionMensajesCRM:{...a._medicionMensajesCRM,desde:'2026-09-02'}};assert.equal(M.parejaMensajesCRM597(tampered,'whatsapp').valida,false);
});
test('duplicate subaccount excludesallvariants',()=>{const a=norm(),b=norm(raw('sidA',{whatsapp:{enviados:20,fallidos:2}}));assert.equal(M.agregarMensajesCRM597([a,b],'whatsapp').pct,null);});
test('differentchannel separate ratios neveremailplusWA',()=>{
 const a=norm();assert.equal(M.agregarMensajesCRM597([a],'whatsapp').pct,10);assert.equal(M.agregarMensajesCRM597([a],'correo').pct,25);assert.equal(M.agregarMensajesCRM597([a],'sms').pct,0);
});
test('safeint aggregateoverflow unknown',()=>{
 const a=norm(raw('sidA',{whatsapp:{enviados:Number.MAX_SAFE_INTEGER,fallidos:1}})),b=norm(raw('sidB',{whatsapp:{enviados:1,fallidos:0}}));assert.equal(M.agregarMensajesCRM597([a,b],'whatsapp').pct,null);
});
test('automatizacionnull no null/0 realrenderer',()=>{
 for(const x of [{velocidad:{auto_5min:null},leads_30d:null},{velocidad:{auto_5min:2},leads_30d:null},{velocidad:{auto_5min:2},leads_30d:0},{velocidad:{auto_5min:11},leads_30d:10},{velocidad:{auto_5min:true},leads_30d:10}]){
  const r=norm(raw('sidA',x));draw([r]);assert.equal(cell('auto',r).textContent,'—');assert(!cell('auto',r).textContent.includes('/0'));assert(cell('auto',r).attrs.title.includes('no hay fracción válida'));
 }
});
test('explicit0 preserved numerator when denominatorvalid',()=>{const r=norm(raw('sidA',{velocidad:{auto_5min:0},leads_30d:10}));draw([r]);assert.equal(cell('auto',r).textContent,'0/10');});
test('0leads notfabricatedfrac preservesmetadata',()=>{const r=norm(raw('sidA',{velocidad:{auto_5min:0},leads_30d:0}));draw([r]);assert.equal(cell('auto',r).textContent,'—');assert(cell('auto',r).attrs.title.includes('0 casos observados'));assert(cell('auto',r).attrs.title.includes('muestra30d: 0'));});
test('legacy missingdescriptor no claim compat',()=>{const r=raw();draw([r]);assert.equal(cell('wa',r).textContent,'—');assert.equal(cell('auto',r).textContent,'—');});
test('revoked callback no navigation clear cachedrender',()=>{const r=norm();const zone=draw([r]),click=options.alPulsar;vigente=false;click(r);assert.equal(nav,0);assert.equal(zone.children.length,0);const empty=draw([r]);assert.equal(empty.children.length,0);vigente=true;});
test('complete scope subset only visbase preserved and no grantswrites',()=>{const zone=draw([norm()]);assert.equal(options.filas.length,1);assert.equal(options.columnas.length,7);assert(!zone.textContent.includes('cliente_ajeno'));assert(!zone.textContent.includes('conversión 20'));});
console.log(n+' grupos597 PASS · normalizador, pares y rendererFlujos reales; no API/POST/datasets');
}finally{Date.now=savedNow;}
})().catch(e=>{console.error(e);process.exitCode=1});
