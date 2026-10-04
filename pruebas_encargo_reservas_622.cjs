const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert'),{execFileSync}=require('child_process');
const source=fs.readFileSync(path.join(__dirname,'probar_prioridades_contexto_337.cjs'),'utf8');
const prefix=source.slice(0,source.indexOf('let total=0;'));
const dto=JSON.parse(execFileSync('python3',[path.join(__dirname,'probar_revision_reservas_622.py'),'--dto'],{cwd:__dirname,encoding:'utf8'}));
const box={require,__dirname,console,setImmediate,URLSearchParams,process,DTO622:dto};vm.createContext(box);
vm.runInContext(prefix+`
(async()=>{
 let n=0;const check=(label,f)=>{f();n++;console.log('PASS',label)};
 async function render(){const b=cargar(),m=main(),c=contexto(async route=>route==='cerebro/operativo'?DTO622:{sugerencias:[]});c.clientesVisibles=[{id:'c1',nombre:'Cliente sintético',activo_confirmado:true,detalle:true}];await b.modulo.render(m,c);await click(boton(m,'Revisar'));return {b,m,c};}
 const l=await render(),ta=l.m.descendants().find(n=>n.tag==='textarea'&&n.attrs['aria-label'].startsWith('Encargo'));
 check('hook real hasta textarea: nombre fuente legible y números cohorte',()=>{assert(ta);assert(ta.value.includes('Reservas enlazadas · GoHighLevel'));assert(!ta.value.includes('crm_embudo_observado'));assert(ta.value.includes('3 recibidos observados; 2 reservas'));assert(!ta.value.includes('3 reservas creadas'));});
 check('periodo/corte/cobertura y límites íntegros en encargo',()=>{for(const t of ['2026-10-01','2026-10-03','observación hasta','registros_observados_no_exhaustivos','canceladas','fecha futura','no acreditan asistencia, ventas','universos distintos'])assert(ta.value.includes(t),t);});
 check('detalle evidencia legible sin identidad privada',()=>{assert(l.m.textContent.includes('Reservas enlazadas · GoHighLevel'));for(const t of ['private-lead','private-booking','sid_fixture','subcuenta_huella'])assert(!ta.value.includes(t),t);});
 await click(boton(l.m,'copiar-ia'));check('copy real conserva mismo apéndice',()=>{assert.equal(l.b.copies.length,1);assert.equal(l.b.copies[0],ta.value);});
 const revoke=await render();revoke.c.ver=()=>({ok:false});await click(boton(revoke.m,'copiar-ia'));check('grant revocado no copia ni deja contenido',()=>{assert.equal(revoke.b.copies.length,0);assert.equal(revoke.m.textContent,'');});
 const actor=await render();actor.c.datos.personas[0].estado='baja';await click(boton(actor.m,'copiar-ia'));check('actor revocado no copia',()=>{assert.equal(actor.b.copies.length,0);assert.equal(actor.m.textContent,'');});
 console.log(n+' grupos622 DOM PASS');
})().catch(e=>{console.error(e);process.exitCode=1});
`,box,{filename:__filename});
