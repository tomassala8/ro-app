const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const file=n=>fs.readFileSync(path.join(__dirname,'modulos',n),'utf8');
const cargar=src=>import('data:text/javascript;base64,'+Buffer.from(src).toString('base64'));
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return{promise,resolve}};
class El {constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=children.flat(Infinity).filter(x=>x!=null);this.value=attrs.value||'';this.open=false;this.disabled=false;this.isConnected=true;this.listeners=attrs.on||{};this.textContent='';}addEventListener(e,f){this.listeners[e]=f}replaceChildren(...xs){this.children=xs.flat(Infinity).filter(x=>x!=null)}focus(){}select(){}all(){return this.children.flatMap(x=>x instanceof El?[x,...x.all()]:[])}}
(async()=>{
 const pure=await cargar(file('_tarea_ia.js'));
 const tarea={id:'fixture143',persona_id:'ana',cli:'cliente-fixture',tarea:'Encargo confirmado',descripcion:'Descripción',estado:'diario'};
 const client={id:tarea.cli,nombre:'Fixture',servicios:{seo:'sí',publicidad:'posible'}};
 const option={id:'seo_page_qa',titulo:'Revisión propuesta',estado:'propuesta',version:'134.1.0',fuente:'PL-QA.md',fecha_fuente:'2026-09-11',fuente_sha256:'a'.repeat(64),extracto_sha256:'b'.repeat(64),pasos:['Contrastar evidencia.'],limites:['Propuesta sin ratificar reglas comerciales.'],conectores_necesarios:['Google Search Console']};
 const dto={tarea:{...tarea},fuente:'Copia local',leido:'2026-10-03T00:00:00+00:00',procedimientos_ia:{version:'134.1.0',estado:'propuesta',autoridad:'datos_de_referencia',binding:{tarea_id:tarea.id,persona_id:tarea.persona_id,cliente_id:tarea.cli},opciones:[option],seleccion_automatica:false}};
 const base={tarea,tareasVisibles:[tarea],clientesVisibles:[client],procedimientosIA:dto.procedimientos_ia};
 assert.equal(pure.prepararTareaIA(base).contexto.checklist_sugerida,null);
 const chosen=pure.prepararTareaIA({...base,procedimientoElegido:option.id});
 assert.equal(chosen.contexto.checklist_sugerida.estado,'propuesta');assert.equal(chosen.contexto.checklist_sugerida.aprobacion_comercial,false);
 assert(chosen.texto.includes('no una obligación vigente'));assert(!chosen.contexto.cliente.servicios_segun_app.some(x=>x.includes('posible')));
 assert.throws(()=>pure.prepararTareaIA({...base,procedimientoElegido:'no-autorizado'}));
 assert.throws(()=>pure.prepararTareaIA({...base,procedimientoElegido:option.id,procedimientosIA:{...dto.procedimientos_ia,binding:{...dto.procedimientos_ia.binding,cliente_id:'ajeno'}}}));
 let copias=0;Object.defineProperty(globalThis,'navigator',{configurable:true,value:{clipboard:{writeText:async()=>{copias++}}}});
 globalThis.__deps={h:(tag,a,...xs)=>new El(tag,a,xs),icono:()=>null,prepararTareaIA:pure.prepararTareaIA,cargarObjetivos:async()=>new Map()};
 const ui=await cargar(file('tarea_ia.js').replace(/^import .*;$/mg,'')+'\nconst {h,icono,prepararTareaIA,cargarObjetivos}=globalThis.__deps;');
 const montar=(lectura)=>{let activa=true,contador=0;const ctx={servidor:true,clientesVisibles:[client],nombre:()=> 'Ana',vigente:()=>activa,api:route=>{
   if(route.startsWith('cliente/'))return Promise.resolve({fuentes:{}});
   contador++;return contador===1?Promise.resolve(dto):lectura.promise;}};
   const det=ui.bloqueTareaIA({ctx,D:{tareas:[tarea]}},tarea);return {det,salir:()=>{activa=false;det.isConnected=false}};};
 const rev=deferred(),r=montar(rev);r.det.open=true;await r.det.listeners.toggle();
 const select=r.det.all().find(x=>x.tag==='select');assert.equal(select.value,'');
 select.value=option.id;select.listeners.change({target:select});
 const boton=r.det.all().find(x=>x.attrs['data-uso']==='copiar-ia');
 const promise=boton.listeners.click();rev.resolve({...dto,procedimientos_ia:{...dto.procedimientos_ia,opciones:[]}});await promise;
 assert.equal(copias,0);assert.equal(r.det.all().find(x=>x.tag==='textarea').value,'');
 const stale=deferred(),s=montar(stale);s.det.open=true;await s.det.listeners.toggle();
 const copy=s.det.all().find(x=>x.attrs['data-uso']==='copiar-ia');const resultado=copy.listeners.click();s.salir();stale.resolve(dto);await resultado;
 assert.equal(copias,0);await copy.listeners.click();assert.equal(copias,0);
 const permitido=deferred(),p=montar(permitido);p.det.open=true;await p.det.listeners.toggle();
 const copiar=p.det.all().find(x=>x.attrs['data-uso']==='copiar-ia');const escrito=copiar.listeners.click();permitido.resolve(dto);await escrito;
 assert.equal(copias,1);
 console.log('PASS: propuestas opcionales, binding exacto, servicios sí, revalidación/revocación antes de copiar, navegación obsoleta y copia autorizada.');
})().catch(e=>{console.error(e);process.exitCode=1});
