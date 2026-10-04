const fs=require('node:fs');
const prefijo=fs.readFileSync(__dirname+'/pruebas_tablero_mi_trabajo_181.cjs','utf8').split('const a=')[0];
new Function('require','__dirname',prefijo+String.raw`
const a={id:'task-a',persona_id:'yo',cli:'cliente-1',lista_id:'list-1',tarea:'Tarea visible',descripcion:'Brief operativo con instrucciones de trabajo',padre:'task-parent',estado:'in progress',grupoV:'hoy',capa:{cambios:[]}};
const child={...a,id:'task-child',padre:a.id,tarea:'Subtarea visible'};
const parent={...a,id:'task-parent',padre:null,tarea:'Padre visible'};
const comment={id:4,tarea:a.id,quien:'yo',campo:'comentario',texto:'Texto de revisión suficientemente completo '.repeat(6),creado:'2026-10-03T09:07:26Z',estado:'simulado'};
const params={tarea_id:a.id,persona_id:'yo',cliente_id:a.cli,lista_id:a.lista_id,actor_id:'yo',fechaFuente:'2026-10-03T09:07:26Z',tareasVisibles:[a,child,parent],cambios:[comment]};
const prep=patch=>c.prepararDetalleTarea197({...params,...patch});
let d=prep({});assert(d.autorizado);assert.equal(d.brief,a.descripcion);assert.equal(d.comentarios.length,1);assert(d.comentarios[0].texto.length>60);assert.equal(d.hijas.length,1);assert.equal(d.padre.id,parent.id);assert.equal(d.fecha_fuente,params.fechaFuente);casos++;
assert.equal(d.comentarios[0].fecha,comment.creado);assert(d.comentarios[0].estado.includes('no enviado'));casos++;
for(const patch of [{tarea_id:'missing'},{persona_id:'ajeno'},{cliente_id:'ajeno'},{lista_id:'ajena'},{actor_id:''},{tareasVisibles:null}]){assert.equal(prep(patch).autorizado,false);casos++;}
for(const patch of [{cli:'ajeno'},{lista_id:'ajena'},{padre:'other-parent'},{tarea:'Título incompatible'}]){assert.equal(prep({tareasVisibles:[a,{...a,...patch,persona_id:'otra'}]}).autorizado,false);casos++;}
d=prep({tareasVisibles:[{...a,descripcion:''}]});assert(d.autorizado);assert.equal(d.brief,'');assert(d.padre_fuera_copia);casos++;
d=prep({tareasVisibles:[a,{...a,persona_id:'otra',descripcion:'Otro brief'}]});assert(d.brief_discrepante);assert.equal(d.brief,'');casos++;
d=prep({cambios:[comment,{...comment,id:5,quien:'otra'},{...comment,id:6,tarea:'ajena'},{...comment,id:7,estado:'desconocido'}]});assert.equal(d.comentarios.length,1);casos++;
d=prep({cambios:[comment,comment]});assert.equal(d.comentarios.length,1);casos++;
d=prep({cambios:[comment,{...comment,texto:'Contenido incompatible'},comment]});assert.equal(d.comentarios.length,0);casos++;
d=prep({tareasVisibles:[a,{...child,cli:'ajeno'},{...parent,lista_id:'otra'}]});assert.equal(d.hijas.length,0);assert.equal(d.padre,null);assert(d.padre_fuera_copia);casos++;
d=prep({tareasVisibles:[a,child,{...child,persona_id:'otra'}]});assert.equal(d.hijas.length,1);casos++;
d=prep({tareasVisibles:[a,...Array.from({length:34},(_,i)=>({...child,id:'child-'+i}))],cambios:Array.from({length:24},(_,i)=>({...comment,id:i}))});assert.equal(d.hijas.length,30);assert.equal(d.hijas_disponibles,34);assert.equal(d.comentarios.length,20);assert.equal(d.comentarios_disponibles,24);casos++;
const sensitive='<script>doEvil()</script> Texto visible\nCorreo: persona@example.com\nTeléfono: +34 612345678\nSalario: 2.000 €\napi_key=SECRET123\nhttps://zoom.us/s/123456?zak=SECRET456';
d=prep({tareasVisibles:[{...a,descripcion:sensitive}],cambios:[{...comment,texto:sensitive}]});const safe=d.brief+' '+d.comentarios[0].texto;assert(!/doEvil|persona@example|612345678|2\.000|SECRET123|SECRET456|zoom\.us\/s\//.test(safe));assert(safe.includes('Texto visible'));casos++;
assert.equal(vm.runInContext("enlaceTarea197('../secret')",c),null);assert.equal(vm.runInContext("enlaceTarea197('task-a')",c),'https://app.clickup.com/t/task-a');casos++;
d=prep({fechaFuente:'sin fecha',cambios:[{...comment,creado:'no fecha'}]});assert.equal(d.fecha_fuente,null);assert.equal(d.comentarios[0].fecha,null);casos++;
for(const state of ['pendiente','enviado','confirmado','fallido','conflicto','descartado']){assert.equal(prep({cambios:[{...comment,estado:state}]}).comentarios.length,1);casos++;}
let posts=0;
const E={D:{tareas:[a,child,parent],fuentes:{tareas:{hora:params.fechaFuente}}},V:{yo:'yo',personas:[{id:'yo'}],cambios:[comment],estados_lista:{'list-1':['in progress','complete']},sincronia:{texto:'Guardado en RO · envío a ClickUp sin confirmar'}},local:[],ctx:{hoy:'2026-10-03',persona:{id:'yo',puestos:[]},real:{id:'yo'},servidor:true,soloLectura:true,pilotoLectura:true,clientes:[{id:'cliente-1'}],nombre:id=>id,api:()=>{throw Error('No lectura remota');},accion:()=>{posts++;},vigente:()=>true},vigente:()=>true};
const original=JSON.stringify(E.D);const node=c.detalle(E,a,()=>{}),rendered=text(node);assert(rendered.includes(comment.texto.trim()));assert(rendered.includes('no es el hilo completo de ClickUp'));assert(rendered.includes('Subtarea visible'));assert(rendered.includes(a.descripcion));assert(rendered.includes('Los cambios se guardan primero'));assert(!rendered.includes('Guardado en RO · envío'));assert.equal(posts,0);assert.equal(JSON.stringify(E.D),original);casos++;
assert.equal(buscar(c.lecturaDetalle197(E,a),n=>n.tag==='a'&&n.attrs.href==='https://app.clickup.com/t/task-a').length,1);assert.equal(buscar(node,n=>n.attrs.innerHTML!==undefined).length,0);casos++;
E.D.tareas=[{...a,descripcion:''}];E.V.cambios=[];const missing=text(c.lecturaDetalle197(E,a));assert(missing.includes('no significa que falte en ClickUp'));assert(missing.includes('no permite concluir'));assert(missing.includes('no significa que no existan'));casos++;
E.ctx.persona.id='otra';assert(!text(c.lecturaDetalle197(E,a)).includes(comment.texto));casos++;
assert(!source.includes("actuar(E, t, 'cambiar_estado', { a: estadoNuevo }"),'Regresión200: detalle ya no debe escapar al CAS191.');casos++;
console.log(casos+' pruebas197 PASS: helper autorizado, sanitización, límites, origen, relaciones y detalle real sin POST ni falsa persistencia.');
`)(require,__dirname);
