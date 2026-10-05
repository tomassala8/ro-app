const fs=require('node:fs');
const prefix=fs.readFileSync(__dirname+'/pruebas_control_macro_138.cjs','utf8').split('const macros=root.desc()')[0];
new Function('require','__dirname',prefix+String.raw`
let n=0;const test=(label,f)=>{f();n++;};
const visible=x=>typeof x!=='object'?String(x):x.tag==='details'?x.k.filter(y=>y.tag==='summary').map(visible).join(''):x.k.map(visible).join('');
const make=(ops=true,money=true)=>b.panelControlCartera({...ctx,veModulo:key=>key==='dinero-cliente'?money:true},D,ops?'operaciones':'account',()=>true);
let r=make(),cuerpo=r.k[0];
test('closure footer follows tables',()=>{const at=cuerpo.k.findIndex(x=>x.tag==='a'&&x.attrs.href==='#/dinero-cliente/cierre-septiembre');const tableAt=cuerpo.k.findIndex(x=>x.desc?.().some(y=>y.tag==='table'));assert(at>tableAt);assert.equal(at,cuerpo.k.length-1);});
test('closure permission remains required',()=>assert(!make(true,false).desc().some(x=>x.tag==='a'&&x.attrs.href==='#/dinero-cliente/cierre-septiembre')));
test('macro stays above lower section',()=>{const a=cuerpo.k.findIndex(x=>x.desc?.().some(y=>y.tag==='table'));const lower=cuerpo.k.findIndex(x=>x.tag==='h3');assert(a<lower);assert.equal(r.desc().filter(x=>x.tag==='table').length,2);});
test('interpretation closed preserves warnings',()=>{const d=r.desc().find(x=>x.tag==='details'&&x.k[0]?.textContent==='Cómo interpretar');assert(d);assert(!d.attrs.open);assert(d.textContent.includes('sin dato no significa cero ni cumplido'));assert(d.textContent.includes('no hay desglose de subproyectos'));assert(d.textContent.includes('no presupuesto ni objetivo contractual confirmado'));assert(!visible(r).includes('sin dato no significa cero'));});
test('period is a single visible line',()=>{const lines=r.desc().filter(x=>x.tag==='small'&&x.textContent.startsWith('Horas por proyecto:'));assert.equal(lines.length,1);assert(lines[0].textContent.includes('declaraciones: semana'));assert(!lines[0].textContent.includes('Gris:'));});
test('status brief with complete accessible explanation',()=>{const status=r.desc().find(x=>x.attrs.role==='status');assert(/^\d+ de \d+ clientes activos$/.test(status.textContent));assert(status.k[0].attrs.title.includes('Copias parciales'));assert.equal(status.k[0].attrs.title,status.k[0].attrs['aria-label']);});
r=make(false);
test('account has no redundant lower heading and same columns',()=>{assert(!r.desc().some(x=>x.tag==='h3'&&x.textContent==='Clientes y proyectos agrupados'));assert.equal(r.desc().filter(x=>x.tag==='table').length,1);assert.equal(r.desc().find(x=>x.tag==='thead').k[0].k.length,10);});
test('filter updates brief status without hiding warnings',()=>{const input=r.desc().find(x=>x.tag==='input'&&x.attrs.type==='search');input.value='nonexistent';input.listeners.input();assert.equal(r.desc().find(x=>x.attrs.role==='status').textContent,'0 de 1 clientes activos');assert(r.textContent.includes('Cero declaraciones no significa ausencia de actividad'));});
console.log(n+' grupos511 PASS · estructura real, accesos, periodos y fuentes');
`)(require,__dirname);
