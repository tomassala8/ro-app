const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const tick = () => new Promise(r => setImmediate(r));
const defer = () => { let resolve; const p = new Promise(r => resolve = r); return {p,resolve}; };
class Nodo {
  constructor(tag, attrs = {}) { this.tag = tag; this.attrs = attrs; this.children = []; this.value = attrs.value || ''; this._connected = false; }
  get isConnected() { return this._connected; }
  conectar(v) { this._connected = v; for (const n of this.children) if (n instanceof Nodo) n.conectar(v); }
  append(...ns) { for (const n of ns.flat(Infinity).filter(x=>x!==null && x!==undefined)) { this.children.push(n); if(n instanceof Nodo)n.conectar(this.isConnected); } }
  replaceChildren(...ns) { for(const n of this.children)if(n instanceof Nodo)n.conectar(false);this.children=[];this.append(...ns); }
  get classList() { return { add() {} }; }
}
const h = (tag, attrs = {}, ...children) => { const n = new Nodo(tag,attrs); n.append(...children); return n; };
const all = n => n instanceof Nodo ? [n,...n.children.flatMap(all)] : [];
const text = n => n instanceof Nodo ? n.children.map(text).join(' ') : String(n);
const find = (root, aria) => all(root).find(n=>n.attrs['aria-label']===aria);
const filtros = {vista:'mia',preset:'daily',asignado:'',cliente:'revocado',lista:'lista-obsoleta',proyecto:'',prioridad:'',etiqueta:''};
const guardada = {id:'11111111-1111-1111-1111-111111111111',nombre:'Privada',revision:1,filtros};
function montar(views) {
  let activa = true;
  const llamadas = [];
  const post = defer();
  const doc = {tareas:[{id:'t1',asignados:['ana'],cli:'actual',cliente:'Actual',lista_id:'lista-actual',lista:'Actual',estado:'diario',tarea:'Fixture',puede_editar:false}],personas:[],solo_lectura:false,estados_detalle:{'lista-actual':[{estado:'diario',orden:1}]}};
  const ctx = {servidor:true,persona:{id:'ana'},titulo(){},nombre:x=>x,vigente:()=>activa,
    api:(ruta,op)=>{llamadas.push({ruta,op});return ruta==='tareas/tablero'?Promise.resolve(doc):op?.metodo==='POST'?post.p:views.p;}};
  const cont = new Nodo('root');cont.conectar(true);
  const scope={h,icono:()=>null,vacioLinea:t=>h('p',{},t),bloqueTareaIA:()=>null,globalThis:{crypto:{randomUUID:()=> 'fixture'}}};
  vm.createContext(scope);
  vm.runInContext(fs.readFileSync(path.join(__dirname,'modulos/_tablero_tareas.js'),'utf8').replace(/^export /gm,''),scope);
  vm.runInContext(fs.readFileSync(path.join(__dirname,'modulos/tablero_tareas.js'),'utf8').replace(/^import .*;\n/gm,'').replace('export default','globalThis.tablero ='),scope);
  return {ctx,cont,llamadas,post,render:()=>scope.globalThis.tablero.render(cont,ctx),salir:()=>{activa=false;cont.conectar(false);}};
}
(async()=>{
  // GET demorado después de navegación no aplica preferencia ni repinta nodos retirados.
  const lectura = defer(), a = montar(lectura);
  await a.render();
  const anterior = text(a.cont);
  a.salir();lectura.resolve({vistas:[guardada]});await tick();
  assert.equal(text(a.cont),anterior);
  assert.equal(a.llamadas.filter(x=>x.op?.metodo==='POST').length,0);
  // No aplicación automática; referencia retirada se conserva y produce cero, no la lista amplia.
  const lect = defer(), b = montar(lect);await b.render();lect.resolve({vistas:[guardada]});await tick();
  assert.equal(find(b.cont,'Cliente').children.at(-1).value,'actual');
  const selector = find(b.cont,'Elegir vista privada guardada');
  selector.value = guardada.id;selector.attrs.on.change({target:selector});
  const clientes = find(b.cont,'Cliente'), listas = find(b.cont,'Lista y flujo de trabajo');
  assert.equal(clientes.value,'revocado');assert.equal(listas.value,'lista-obsoleta');
  assert.match(text(b.cont),/0 tareas en esta lista/);
  assert.match(text(clientes),/Referencia no disponible/);
  // Una escritura iniciada mientras vigente puede finalizar; su callback no repinta ni encadena tras navegar.
  const boton = all(b.cont).find(n=>n.tag==='button'&&text(n)==='Actualizar esta vista');
  const promesa = boton.attrs.on.click({currentTarget:boton});
  assert.equal(b.llamadas.filter(x=>x.op?.metodo==='POST').length,1);
  const payload = b.llamadas.find(x=>x.op?.metodo==='POST').op.cuerpo;
  assert.equal(payload.filtros.cliente,'revocado');assert.equal('buscar' in payload.filtros,false);
  const antes = text(b.cont);b.salir();b.post.resolve({ok:true,vista:{...guardada,revision:2}});await promesa;
  assert.equal(text(b.cont),antes);
  await boton.attrs.on.click({currentTarget:boton});
  assert.equal(b.llamadas.filter(x=>x.op?.metodo==='POST').length,1);
  console.log('3 escenarios reales de UI PASS: lectura demorada, filtro obsoleto, escritura/navegación.');
})().catch(e=>{console.error(e);process.exitCode=1;});
