const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
// Evaluate the actual module, replacing imports only; no copied implementation.
const source = fs.readFileSync(path.join(__dirname, 'modulos/personas.js'), 'utf8');
const body = source.replace(/import\s+[\s\S]*?from\s+['"][^'"]+['"];\s*/g, '').replace('export default {', 'const modulo = {');
let table, filterConfig, copied = null, notice = null;
const node = (tag, attrs = {}, ...children) => ({tag, attrs, children, append(...cs) {this.children.push(...cs);}, replaceChildren(...cs) {this.children = cs;}});
const ctx = {fmt: {num: n => String(n), fecha: d => d, pct: n => String(n)}, h: node,
  chipsFiltro: c => {filterConfig = c; return {valor: () => 'ayer'};},
  tablaApilable: c => {table = c; return c;}, chipEstado: (estado, texto) => ({estado, texto}),
  frescura: x => x, avisoParcial: (texto, args) => ({texto, args}),
  panel: (cab, ...children) => ({cab, children}), icono: x => x,
  copiar: t => {copied = t;}, avisoFlotante: t => {notice = t;}, PUESTO: {},
};
vm.createContext(ctx); vm.runInContext(body, ctx);
const persona = (id, horas) => ({persona_id: id, alias: id, puestos: [], estado: 'activo', imputa: true,
  horas, cartera: {}, sobre_capacidad: [], cerca_capacidad: []});
const ps = [persona('cero', {ayer:0, ayer_fecha:'2026-10-01', semana:0, dias_sin_imputar_5:[]}),
 persona('parcial', {ayer:7.5, ayer_fecha:'2026-10-02', mes_anterior:150, pct_128:117}),
 persona('ocho', {ayer:8}), persona('nulo', {ayer:null}), persona('ausente', {}),
 persona('invalido', {ayer:'0'}), persona('negativo', {ayer:-1}), persona('nan', {ayer:NaN})];
for (const v of [undefined,null,'0',false,-1,NaN,Infinity]) assert.equal(ctx.horasRegistradas(v), null);
assert.equal(ctx.horasRegistradas(0),0); assert.equal(ctx.horasRegistradas(7.5),7.5);
assert.deepEqual(ps.filter(p => ctx.enFiltroHoras(p,'cero')).map(p=>p.persona_id), ['cero']);
assert.deepEqual(ps.filter(p => ctx.enFiltroHoras(p,'ayer')).map(p=>p.persona_id), ['cero','parcial']);
assert.equal(ps.filter(p=>ctx.enFiltroHoras(p,'sin_dato')).length,5);
assert.equal(ctx.diasSinRegistro(persona('x',{})),null);
assert.equal(ctx.diasSinRegistro(persona('x',{dias_sin_imputar_5:['2026-10-01','2026-10-01','2026-02-30','2026-99-01',null]})),1);
const view = ctx.vistaImputa({},ps,ps,{fecha:'2026-10-02 09:16'});
assert.deepEqual(table.filas.map(p=>p.persona_id),['cero','parcial']);
for (const p of ps) {
 const cell = table.columnas.find(c=>c.clave==='ayer').celda(p);
 assert.equal(cell.children[0].estado, 'gris');
 if (ctx.horasRegistradas(p.horas.ayer) === null) assert.equal(cell.children[0].texto,'Sin dato');
}
assert(view[0].texto.includes('calendario laboral')); assert(view[0].texto.includes('no prueba ausencia'));
assert(!table.vacio.titulo.includes('Todos')); assert(!JSON.stringify(view).includes('disciplina'));
filterConfig.alCambiar('sin_dato'); assert.equal(table.filas.length,5);
filterConfig.alCambiar('cero'); assert.equal(table.filas.length,1);
const mensaje = ctx.recordatorio(ps[0]); assert(mensaje.includes('2026-10-01')); assert(!mensaje.includes('ayer')); assert(!mensaje.includes('15:00')); assert(mensaje.includes('confirmar'));
assert(ctx.recordatorio(ps[3]).includes('Sin dato'));
// Executing the bulk button follows the current filter and never fabricates a zero for null.
const bulk = view[1].children[2].children[0];
bulk.attrs.on.click(); assert(copied.includes('Hola cero')); assert(!copied.includes('Hola nulo'));
filterConfig.alCambiar('sin_dato'); copied=null; bulk.attrs.on.click(); assert(copied.includes('Sin dato')); assert(!copied.includes('Hola cero'));
filterConfig.alCambiar('3dias'); copied=null; bulk.attrs.on.click(); assert.equal(copied,null); assert(notice.includes('No hay consultas'));
// Real load view: large/small/missing time alone does not turn the person into a breach or claim capacity.
ctx.vistaCarga({},ps,{fecha:'2026-10-02'});
for (const p of table.filas) {
 const aviso = table.columnas.find(c=>c.clave==='aviso').celda(p);
 assert.equal(aviso.estado,'gris'); assert.equal(aviso.texto,'sin señal de cartera');
 const hours = table.columnas.find(c=>c.clave==='pct').celda(p);
 assert(!JSON.stringify(hours).includes('de 128'));
}
const over = persona('sobrecarga',{ayer:null}); over.cartera={account:13}; over.sobre_capacidad=['account'];
ctx.vistaCarga({},[over],{}); assert.equal(table.columnas.find(c=>c.clave==='aviso').celda(table.filas[0]).estado,'rojo');
// All rendering operates on exactly the supplied authorized rows, never expanding the team.
assert.deepEqual(table.filas.map(p=>p.persona_id), ['sobrecarga']);
console.log('Personas: funciones y vistas reales verificadas; desconocido ≠ cero, registros neutrales, fechas por persona, consultas por filtro, carga separada y ámbito conservado.');
let fichas;
Object.assign(ctx, {tile: x=>x, tiles: x=>{fichas=x;return x;}, cabPersona: ()=>null,
 lineaZona: ()=>null, hoyMadrid: ()=>'2026-10-03', elegir: ()=>node('select'), vacio: x=>x});
for (const horas of [0,7.5,null,undefined,NaN]) {
 const p=persona('visible',{ayer:horas, ayer_fecha:'2026-10-01', mes_anterior:horas}); p.apuntes=[];
 const cont={append(){}};
 ctx.pintarMiFicha(cont,{},p,[],{fecha:'2026-10-02 09:16'},'2026-09','2026-T4',{});
 const regs=fichas.filter(t=>t.etiqueta.startsWith('Registro'));
 assert.equal(regs.length,2); assert(regs.every(t=>t.estado===''));
 assert.equal(regs[0].valor,ctx.horasRegistradas(horas)); assert(regs[0].contexto.includes('2026-10-01'));
 assert(regs.every(t=>!t.unidad.includes('de 8')&&!t.unidad.includes('128')));
}
console.log('Ficha individual real: cero, parcial y ausente conservan valores/fecha, sin juicio de cumplimiento diario ni capacidad mensual.');

// Full async render with an authorized fixture, including real En alerta cards and unknown absence coverage.
(async () => {
  vm.runInContext('this.modulo = modulo;',ctx);
  let summary, tabs, alertTree;
  Object.assign(ctx, {estilosLocales:()=>{}, leerCola:async()=>[], botonDeshacer:x=>x,
    campo:()=>null, dias:()=>1, limpiaTexto:x=>x, vacioLinea:x=>x, consejoCompacto:()=>{},
    franjaCifras: x=>{summary=x;return x;},
    chipsFiltro: c=>({valor:()=>c.clave==='personas.alerta'?'':'ayer'}),
    pestanas: c=>{tabs=c;const z=node('div');c.pintar('alerta',z);alertTree=z;return {elegir(){}};},
  });
  const a=persona('persona-a',{ayer:0}); a.nombre='Persona A'; a.apuntes=[];
  a.alerta={desde:'2026-10-02',peso:1,motivos:['3 tareas pendientes de revisión']};
  a.avisos=['imputó 1.6 h la semana pasada (4 % de 40)','10 registros de horas fuera de lo normal','4 clientes con correos de +48 h (de una cartera de account que ya no lleva)'];
  a.cartera={account:13}; a.sobre_capacidad=['account'];
  const b=persona('persona-b',{ayer:null});b.nombre='Persona B';b.apuntes=[];b.avisos=[];
  const E={personas:[a,b],ausencias:[],_meta:{corte_horas:'2026-10-02 09:16',generado:'2026-10-03 04:36'}};
  const appctx={persona:{id:'viewer',puestos:['account']},datos:{personas:[]},
    datosModulo: async n=>n==='personas_m20/equipo'?E:n==='verdad/clientes'?{carteras:[]}:null,
    veModulo:()=>false,titulo(){},nombre:x=>x,servidor:false,soloLectura:true};
  await ctx.modulo.render(node('main'),appctx);
  const rendered=JSON.stringify(alertTree);
  assert(rendered.includes('3 tareas pendientes de revisión')); // Real task alert unchanged.
  assert(rendered.includes('4 clientes con correos de +48 h')); // Non-hours evidence unchanged.
  assert(!rendered.includes('4 % de 40')); assert(!rendered.includes('fuera de lo normal'));
  assert(!rendered.includes('imputó')); assert(rendered.includes('cobertura sin conciliar'));
  const capacity=summary.find(x=>x.etiqueta==='Carteras sobre la referencia');
  assert.equal(capacity.valor,1);assert(capacity.titulo.includes('No acredita capacidad horaria'));
  const absence=summary.find(x=>x.etiqueta==='Registro de ausencias (14 días)');
  assert.equal(absence.valor,'Sin registros');assert(absence.titulo.includes('Cobertura no acreditada'));
  const absenceTree=node('div');tabs.pintar('ausencias',absenceTree);
  assert(JSON.stringify(absenceTree).includes('Una lista vacía no confirma'));
  assert(!JSON.stringify(absenceTree).includes('restan capacidad'));
  assert.equal(E.personas[0].alerta.motivos[0],'3 tareas pendientes de revisión');
  assert.equal(E.personas[0].avisos[0],'imputó 1.6 h la semana pasada (4 % de 40)'); // Data not rewritten.
  console.log('Render completo: alertas reales conservadas, avisos horarios heredados neutralizados, cartera sin capacidad inferida y ausencias vacías sin cobertura ficticia.');
})().catch(e=>{console.error(e);process.exitCode=1;});
