const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const setup=fs.readFileSync('pruebas_captacion_compacta_243.cjs','utf8').split('const c={')[0];
const outer={require,console,__dirname:process.cwd()};vm.createContext(outer);vm.runInContext(setup+';globalThis.E=e;globalThis.H=h;',outer);const e=outer.E,h=outer.H;
const r={version:'417.1',cliente_id:'cid',cuenta_id:'123',moneda:'EUR',fuente:'cache_legacy',nivel:'account_agregado_legacy',estado:'referencia_observada',medicion_actual:false,zona:null,cobertura:'presencia_original_no_acreditada',desde:'2026-09-26',hasta:'2026-10-02',fecha_lectura:'2026-10-03 04:48',gasto_observado:20,impresiones_observadas:1000,coste_por_mil:20};
const c={cliente_id:'cid',nombre:'Cliente fixture',dinero:true,cuenta_meta:{moneda:'EUR'},coste_cpm_referencia_7d:r,panelEspecialista:{},equipo:{},severidad:'dato',leads:{},gasto:{},motivos:[],meta_activa:false};
const d={ventanas:{'7d':[r.desde,r.hasta]},parametros:{},bitacora:new Map()};
let n=0;function test(fn){fn();n++;}
test(()=>assert.equal(e.referenciaCpm417(c,d),r));
for(const patch of [{coste_cpm_referencia_7d:undefined},{dinero:false},{panelEspecialista:{cuentaError:true}},{cuenta_meta:{moneda:'EUR',error:'denied'}},{cuenta_meta:{moneda:'USD'}}])test(()=>assert.equal(e.referenciaCpm417({...c,...patch},d),null));
for(const patch of [{gasto_observado:null},{gasto_observado:-1},{gasto_observado:true},{impresiones_observadas:0},{impresiones_observadas:Infinity},{coste_por_mil:19},{coste_por_mil:NaN},{medicion_actual:true},{zona:'Europe/Madrid'},{cliente_id:'other'},{desde:'2026-09-25'}])test(()=>assert.equal(e.referenciaCpm417({...c,coste_cpm_referencia_7d:{...r,...patch}},d),null));
test(()=>assert.equal(e.referenciaCpm417(c,{...d,ventanas:{'7d':['2026-09-25',r.hasta]}}),null));
test(()=>assert.equal(e.referenciaCpm417({...c,coste_cpm_referencia_7d:{...r,gasto_observado:0,coste_por_mil:0}},d).coste_por_mil,0));
let options;e.tablaDensa=o=>{options=o;return h('table',{});};e.pCuentas(h('main',{}),{nivel:'resumen',soloLectura:true,navegar(){},fechas:{esHoy:()=>false}},d,[c],{},{});
test(()=>{assert.equal(options.columnas.find(x=>x.clave==='gasto7').titulo,'Gasto');assert.equal(options.columnas.find(x=>x.clave==='cplref').titulo,'CPL');assert.equal(options.columnas.find(x=>x.clave==='cpm').titulo,'CPM');assert(!options.columnas.some(x=>x.clave==='objetivo'));});
test(()=>{const col=options.columnas.find(x=>x.clave==='cpm');const cell=col.celda(c);assert.equal(cell.textContent,'20€§');assert(cell.attrs.class.includes('gris'));assert(cell.attrs.title.includes('no medición actual'));assert.equal(col.celda({...c,dinero:false}).textContent,'Reservado');assert.equal(col.celda({...c,coste_cpm_referencia_7d:null}).textContent,'—');});
// Cierre independiente: calendario/reloj/offset/ventana se validan ahora en el consumidor.
for(const fecha_lectura of ['2026-02-30T99:99','2026-10-03T24:00','2026-10-03T23:60','2026-10-03T23:59:60','2026-10-03T04:48+02:99','2026-10-03T04:48+15:00','2026-10-03T04:48+14:01','2026-10-02T23:59','2026-10-03T04:48tail'])test(()=>assert.equal(e.referenciaCpm417({...c,coste_cpm_referencia_7d:{...r,fecha_lectura}},d),null));
for(const w of [['2026-02-30','2026-03-08'],['2026-09-25','2026-10-02'],['2026-10-02','2026-09-26']])test(()=>assert.equal(e.referenciaCpm417({...c,coste_cpm_referencia_7d:{...r,desde:w[0],hasta:w[1]}},{...d,ventanas:{'7d':w}}),null));
for(const fecha_lectura of ['2026-10-03 04:48','2026-10-03T04:48:59.123456Z','2026-10-03T04:48+14:00','2026-10-03T04:48-02:30'])test(()=>assert.equal(e.referenciaCpm417({...c,coste_cpm_referencia_7d:{...r,fecha_lectura}},d)?.fecha_lectura,fecha_lectura));
console.log(n+' grupos419 PASS · consumidor/render actual, referencia naive preservada, calendario/reloj/offset y ventanas malformadas rechazados.');
