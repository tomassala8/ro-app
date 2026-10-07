// Consumidor CRM real: fixtures, render stub sin DOM/red ni datos personales.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
(async()=>{
const crm=await import('data:text/javascript;base64,'+Buffer.from(fs.readFileSync(__dirname+'/modulos/_crm_mediciones.js','utf8')).toString('base64'));
const src=fs.readFileSync(__dirname+'/modulos/crm.js','utf8').replace(/import[\s\S]*?from ['"][^'"]+['"];\n/g,'').replace('export default {','const modulo = {');
const tables=[],panels=[],bars=[],actions=[];
const env={conteoCRM:crm.conteoCRM,h:(tag,attrs,...children)=>({tag,attrs,children}),panel:(p,...children)=>{const x={p,children};panels.push(x);return x;},
 tablaApilable:t=>{tables.push(t);return t;},vacioLinea:t=>t,iniciales:()=>'',fmt:{num:n=>n===null?'Sin dato':String(n)},barraProgreso:p=>{bars.push(p);return p;},
 puntoEstado:(c,t)=>({c,t}),semaforo:(v)=>{assert.notEqual(v,null,'No semáforo con unknown');return 'verde';},botonDeshacer:p=>{actions.push(p);return p;},ESP:{},chipEstado:(c,t)=>({c,t}),accionSim:p=>p};
vm.createContext(env);vm.runInContext(src+'\nglobalThis.render=pintarEspecialistas;globalThis.medidos=especialistasMedidosCRM;globalThis.sinEsp=sinEspecialistaCRM;',env);
const ctx={persona:{id:'p'},soloLectura:false},vis={jefatura:true};
const row={id:'p',nombre:'Fixture',clientes:null,encendidas:null,verde:null,ambar:null,rojo:null,sin_tocar:null,sin_estado:null,sin_subcuenta:null,tope:16};
env.render({append:()=>{}},ctx,{especialistas:[row],resumen:{encendidas_sin_especialista:null}},vis);
const cols=tables[0].columnas;
for(const key of ['clientes','encendidas','verde','ambar','rojo','sin_tocar','sin_estado','sin_subcuenta']){
 const value=cols.find(c=>c.clave===key).celda(row);assert.match(value,/Sin dato|Pendiente de verificar/);
}
cols.find(c=>c.clave==='reparto').celda(row);assert.equal(actions.length,0);assert.equal(bars.length,0);
assert(JSON.stringify(panels).includes('Asignaciones pendientes de verificar'));assert(!JSON.stringify(panels).includes('Todas las encendidas'));
const legacy=env.medidos({especialistas:[{...row,clientes:99,rojo:99,sin_subcuenta:['Ajeno']}]})[0];assert.equal(legacy.clientes,null);assert.equal(legacy.rojo,null);assert.equal(legacy.sin_subcuenta,null);assert.equal(env.sinEsp({resumen:{encendidas_sin_especialista:['Ajeno']}}),null);
// Medido cero de clientes vs unknown no confluyen: sólo cifra realmente conocida dibuja barra.
const known={...row,clientes:0,rojo:0,sin_subcuenta:[],agregados_cobertura:{estado:'completa',cartera_asignada_confirmada:true}};assert.equal(env.medidos({especialistas:[known]})[0].clientes,0);cols.find(c=>c.clave==='clientes').celda(known);assert.equal(bars[0].valor,0);assert.equal(actions.length,0);
// Copia vacía explícita limita afirmación al universo visible, nunca «todas» global.
panels.length=0;env.render({append:()=>{}},ctx,{especialistas:[],resumen:{encendidas_sin_especialista:[]},agregados_cobertura:{estado:'completa',asignaciones_confirmadas:true}},vis);
assert(JSON.stringify(panels).includes('En la copia visible no constan'));assert(!JSON.stringify(panels).includes('Todas las encendidas'));
console.log('207 UI PASS: renderer actual null no 0/barra/salud/CTA; lista desconocida no Todas; cero medido distingue unknown.');
})().catch(e=>{console.error(e);process.exitCode=1;});
