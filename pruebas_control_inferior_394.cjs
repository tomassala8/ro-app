const fs=require('node:fs'),prefix=fs.readFileSync(__dirname+'/pruebas_control_macro_138.cjs','utf8').split('const macros=root.desc()')[0];
new Function('require','__dirname',prefix+String.raw`
return (async()=>{
let n=0;const test=(label,f)=>{f();n++;},copy=x=>JSON.parse(JSON.stringify(x));
const visible=x=>typeof x!=='object'?String(x):x.tag==='details'?x.k.filter(y=>y.tag==='summary').map(visible).join(''):x.k.map(visible).join('');
const fixture=()=>{
 const f=copy(fuentes),c={...ctx,servidor:true,real:{id:'account',estado:'activo',puestos:['account']},persona:{id:'account',estado:'activo',puestos:['account']},clientes:copy(cli),clientesVisibles:copy(cli),datos:{asignaciones:copy(base.asignaciones),personas:[{id:'account',estado:'activo',puestos:['account']}]},ver:q=>({ok:q.cliente_id==='uno'}),api:async()=>({semana_inicio:'2026-09-28',cobertura:'parcial',verificacion_externa:false,cumplimiento:null,clientes:[{cliente_id:'uno',contactos_declarados:0,reuniones_declaradas:2,source_kind:'registro_equipo',verificacion_externa:false,cumplimiento:null}]})};
 const dinero={generado:'2026-10-03 06:31',mes_cuota:'2026-10',mes_horas:'2026-09',clientes:[{cliente_id:'uno',cuota_horas:{pautadas:20}}]};
 const source={opcional:key=>key==='dinero_cliente/dinero_cliente'?dinero:key==='metodo/sugerencias'?{clientes:[{cliente_id:'uno',cadencia_dias:15}]}:({'produccion/produccion':f.produccion,'bandeja/por_cliente':f.bandeja}[key]||null)};
 return {c,f,dinero,source,render:()=>b.panelControlCartera(c,source,'account',()=>true)};
};
const table=r=>r.desc().find(x=>x.tag==='table'),cells=r=>table(r).desc().find(x=>x.tag==='tbody').k[0].k;
let x=fixture(),r=x.render();
test('ten columns services last separate queues',()=>{const headers=table(r).desc().find(x=>x.tag==='thead').k[0].k.map(x=>x.textContent);assert.deepEqual(headers,['Cliente / account','Sem.','Pend.','h / ref.','Rev.','Tk.','Cont./sem.','Reu./sem.','Detalle','Serv.']);});
test('compact numeric hour pair and totals',()=>{const c=cells(r);assert.equal(c[2].textContent,'3');assert.equal(c[3].textContent,'2,5 / 20');assert.equal(c[4].textContent,'0');assert.equal(c[5].textContent,'0');assert(!visible(table(r)).includes('Asignación por confirmar'));assert(c[2].attrs['aria-label'].includes('fecha pasada'));assert.equal(c[9].textContent,'Paid / CRM');});
test('cadence not meeting count without declarations',()=>{assert.equal(cells(r)[7].textContent,'—');assert(!visible(table(r)).includes('15d'));});
test('economic reference stays documented not planned compliance',()=>{assert(r.textContent.includes('no presupuesto ni objetivo contractual confirmado'));assert(cells(r)[3].attrs['aria-label'].includes('Pauta económica'));assert(r.textContent.includes('Pauta de referencia: 20 h'));});
x=fixture();x.dinero.mes_cuota='2026-09';r=x.render();test('different months no pair',()=>assert.equal(cells(r)[3].textContent,'2,5 / —'));
x=fixture();x.c.ver=q=>({ok:q.tipo!=='horas_pautadas'&&q.cliente_id==='uno'});r=x.render();test('no private reference without grant',()=>{assert.equal(cells(r)[3].textContent,'2,5 / —');assert(!r.textContent.includes('Pauta de referencia:'));});
x=fixture();delete x.f.produccion.proyectos[0].horas_medicion;r=x.render();test('legacy positive unknown period cannot pair',()=>assert.equal(cells(r)[3].textContent,'2,5 / —'));
x=fixture();delete x.f.produccion.proyectos[0].revisiones_account;delete x.f.bandeja.fuentes;r=x.render();test('legacy zeros not queue measurement',()=>{assert.equal(cells(r)[4].textContent,'—');assert.equal(cells(r)[5].textContent,'—');});
x=fixture();x.f.produccion.proyectos[0].rev_account=6;x.f.produccion.proyectos[0].rev_account_48=6;x.f.bandeja.clientes[0].sin_contestar=2;x.f.bandeja.clientes[0].mas_48=1;b.chipEstado=(estado,valor)=>h('span',{'data-estado':estado},valor);r=x.render();test('backed age thresholds not total thresholds',()=>{assert.equal(cells(r)[4].k[0].attrs['data-estado'],'rojo');assert.equal(cells(r)[5].k[0].attrs['data-estado'],'rojo');assert(cells(r)[5].attrs.title.includes('1 >48h'));});
x=fixture();r=x.render();await new Promise(resolve=>setImmediate(resolve));test('current weekly declarations numeric zero and two',()=>{assert.equal(cells(r)[6].textContent,'0');assert.equal(cells(r)[7].textContent,'2');assert.equal(cells(r)[6].k[0].attrs['data-estado'],'gris');assert(!visible(table(r)).includes('declarad'));});
for(const [label,change]of [['canonical ACT',c=>c.clientes[0].activo_confirmado=false],['duplicate clients',c=>c.clientes.push({...c.clientes[0]})],['person inactive',c=>c.datos.personas[0].estado='baja'],['private grant',c=>c.ver=q=>({ok:q.tipo!=='horas_pautadas'&&q.cliente_id==='uno'})]]){
 x=fixture();r=x.render();const detail=r.desc().find(y=>y.tag==='details'&&y.desc().some(z=>z.tag==='summary'&&z.textContent==='Ver detalle'));change(x.c);detail.listeners.toggle();test('detail revocation '+label,()=>assert.equal(detail.textContent,''));
 r.desc().find(y=>y.tag==='select'&&y.attrs['aria-label']==='Filtrar por servicio confirmado').listeners.change();test('repaint clears '+label,()=>assert.equal(r.desc().filter(y=>y.tag==='table').length,0));
}
for(const [label,change]of [['initial ACT revoked',c=>c.clientes[0].activo_confirmado=false],['initial actor ambiguity',c=>c.datos.personas.push({...c.datos.personas[0]})]]){x=fixture();change(x.c);r=x.render();test(label,()=>assert.equal(r.desc().filter(y=>y.tag==='table').length,0));}
x=fixture();let release;x.c.api=()=>new Promise(resolve=>release=resolve);r=x.render();await new Promise(resolve=>setImmediate(resolve));x.c.clientes[0].activo_confirmado=false;release({});await new Promise(resolve=>setImmediate(resolve));test('revoke during GET removes old rows',()=>assert.equal(r.desc().filter(y=>y.tag==='table').length,0));
console.log(n+' grupos394 PASS · tabla inferior real, periodo, números, declaraciones y revocación');
})();`)(require,__dirname).catch(e=>{console.error(e);process.exitCode=1});
