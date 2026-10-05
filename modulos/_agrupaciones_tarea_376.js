import {cabeceraOperaciones423} from './_cabeceras_operaciones_423.js';
// Cinco métricas autorizadas, clasificación orientativa. GET local; nunca crea acciones.
const PIN376='1045a53219b967885e5bfe6748327c3ca19a48e71266bd4c522c4e236e833670';
const id=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,150}$/.test(x);
const num=x=>typeof x==='number'&&Number.isFinite(x)&&x>=0;
const date=x=>{if(typeof x!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(x))return null;const d=new Date(x+'T00:00:00Z');return Number.isFinite(+d)&&d.toISOString().slice(0,10)===x?d:null;};
const stamp=x=>{if(typeof x!=='string'||!date(x.slice(0,10)))return null;const m=/^\d{4}-\d{2}-\d{2}T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(Z|[+-](\d{2}):(\d{2}))$/.exec(x);if(!m||+m[1]>23||+m[2]>59||+m[3]>59||(m[4]!=='Z'&&(+m[5]>14||+m[6]>59||(+m[5]===14&&+m[6]!==0))))return null;const n=new Date(x);return Number.isFinite(+n)?n:null;};
const zoneDay=d=>new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit'}).format(d);
export function ambitoAgrupaciones376(ctx){try{
 if(ctx.servidor!==true||ctx.vigente?.()===false||ctx.veModulo?.('horas')!==true||ctx.veModulo?.('produccion')!==true||!date(ctx.hoy))return null;
 const ps=Array.isArray(ctx.datos?.personas)?ctx.datos.personas:[],act=[];
 for(const a of [ctx.real,ctx.persona]){const xs=ps.filter(p=>id(p?.id)&&p.id===a?.id);if(xs.length!==1||xs[0].estado!=='activo'||xs[0].activo===false||a?.estado!=='activo'||a?.activo===false)return null;const roles=xs[0].puestos;if(!Array.isArray(roles)||!roles.length||roles.some(x=>!id(x))||new Set(roles).size!==roles.length||JSON.stringify([...roles].sort())!==JSON.stringify([...(a.puestos||[])].sort()))return null;act.push(xs[0]);}
 const persons=ps.filter(p=>id(p?.id)&&ps.filter(x=>x?.id===p.id).length===1&&p.estado==='activo'&&p.activo!==false&&ctx.ver?.({tipo:'horas_persona',persona_id:p.id})?.ok===true).map(p=>p.id).sort();
 const cs=Array.isArray(ctx.clientesVisibles)?ctx.clientesVisibles:[],actual=Array.isArray(ctx.clientes)?ctx.clientes:null;if(!actual)return null;
 const clients=cs.filter(c=>id(c?.id)&&cs.filter(x=>x?.id===c.id).length===1&&c.activo_confirmado===true&&actual.filter(x=>x?.id===c.id).length===1&&actual.some(x=>x?.id===c.id&&x.activo_confirmado===true&&x.activo!==false&&x.estado!=='baja')&&ctx.ver?.({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true).map(c=>c.id).sort();
 if(!clients.length||!persons.length)return null;
 return {firma:JSON.stringify([act,ps,actual,clients,persons,ctx.datos?.asignaciones,ctx.hoy]),personas:persons,clientes:clients};
 }catch{return null;}}
export function modeloAgrupaciones376(dto,ctx){
 if(!dto||dto.version!=='376.1'||dto.unidad!=='h'||dto.unidad_muestra!=='usuario_id+task_id'||dto.unidad_maximo!=='suma_por_caso'||dto.clasificacion!=='orientativa_por_titulo'||dto.minimo_casos!==5||dto.tiempo_normativo!==null||dto.duracion_cerrada_confirmada!==false||dto.tipo_historico_confirmado!==false||!Array.isArray(dto.filas)||dto.filas.length>5000||!stamp(dto.generado)||zoneDay(stamp(dto.generado))>ctx.hoy)return null;
 if(dto.estado==='sin_dato'&&dto.sha256_candidato===null&&dto.ventana===null&&dto.filas.length===0)return {estado:'sin_dato',filas:[],caption:'Sin copia autorizada disponible'};
 const v=dto.ventana,desde=date(v?.desde),hasta=date(v?.hasta_exclusivo),cut=stamp(v?.observado_hasta),read=stamp(dto.fecha_fuente);
 if(dto.estado!=='copia_observada'||dto.sha256_candidato!==PIN376||dto.cobertura!=='parcial'||dto.fuente!=='ClickUp entradas'||!desde||!hasta||(+hasta-desde)!==60*864e5||v.zona!=='Europe/Madrid'||v.atribucion!=='inicio'||!cut||!read||+cut!==+read||zoneDay(cut)>ctx.hoy||zoneDay(cut)!==new Date(+hasta-864e5).toISOString().slice(0,10))return null;
 const seen=new Set(),rows=[];
 for(const r of dto.filas){if(!r||typeof r.grupo!=='string'||!/^[a-z0-9]+(?: [a-z0-9]+){0,4}$/.test(r.grupo)||r.grupo.length>200||seen.has(r.grupo)||!Number.isSafeInteger(r.casos)||r.casos<5||!num(r.mediana_h)||!num(r.max_h)||!num(r.total_h)||r.mediana_h>r.max_h||r.max_h>r.total_h||!Number.isSafeInteger(r.registros_mas10h)||r.registros_mas10h<0)return null;seen.add(r.grupo);rows.push({grupo:r.grupo,casos:r.casos,mediana_h:r.mediana_h,max_h:r.max_h,total_h:r.total_h});}
 return {estado:'copia_observada',filas:rows,caption:`${v.desde} → ${new Date(+hasta-864e5).toISOString().slice(0,10)} · 60 días · agrupación orientativa · copia parcial`,fecha:dto.fecha_fuente};
}
export async function renderAgrupaciones376(h,ctx){
 const root=h('section',{class:'oe-panel','data-agrupaciones-376':''}),scope=ambitoAgrupaciones376(ctx),scopeVigente=()=>!!scope&&ambitoAgrupaciones376(ctx)?.firma===scope.firma,vivo=()=>root.isConnected!==false&&scopeVigente();
 root.append(h('header',{},h('h2',{},'Dónde se van las horas, por tipo de tarea')));
 if(!scope){root.append(h('p',{class:'oe-note',role:'status'},'Datos no disponibles con los permisos actuales.'));return root;}
 let dto;try{dto=await ctx.api('horas/agrupaciones-tarea');}catch{if(scopeVigente())root.append(h('p',{class:'oe-note',role:'status'},'No se pudo leer la copia autorizada. No acredita cero horas.'));return root;}
 if(!scopeVigente()){root.replaceChildren(h('p',{role:'status'},'El acceso cambió.'));return root;}
 const m=modeloAgrupaciones376(dto,ctx);if(!m){root.append(h('p',{class:'oe-note',role:'status'},'La copia no tiene un descriptor compatible.'));return root;}
 const fmt=x=>x>0&&x<0.1?'<0,1':new Intl.NumberFormat('es-ES',{maximumFractionDigits:1}).format(x);
 root.append(h('p',{class:'oe-note'},m.caption));
 const table=h('table',{},h('thead',{},h('tr',{},['Tipo de tarea','Casos','Mediana','Máximo','Horas totales'].map(x=>{const m=cabeceraOperaciones423(x);return h('th',{scope:'col',title:m.completo,'aria-label':m.completo},m.breve);}))),h('tbody',{},m.filas.map(r=>h('tr',{},h('td',{},r.grupo),...[r.casos,r.mediana_h,r.max_h,r.total_h].map(x=>h('td',{class:'oe-num'},fmt(x)))))));
 root.append(h('div',{class:'oe-scroll'},table));
 if(!m.filas.length)root.append(h('p',{class:'oe-note',role:'status'},m.estado==='sin_dato'?'Pendiente de disponer de una copia autorizada.':'No hay una agrupación con cinco casos autorizados en esta copia.'));
 root.append(h('details',{on:{toggle:()=>{if(!vivo())root.replaceChildren();}}},h('summary',{},'Fuente y límites'),h('p',{},`ClickUp entradas · lectura ${m.fecha||'sin fecha'}. Agrupación orientativa por cinco palabras del título saneado, no taxonomía confirmada. Caso: usuario de ClickUp + tarea; máximo: mayor suma de un caso. No mide tiempo normativo ni rendimiento. Sin registros no equivale a cero. Sólo proyectos activos y ámbitos autorizados; sin trabajos internos no acreditados.`)));
 return root;
}
