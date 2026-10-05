// Contrato puro propuesto: solo DTO autorizado, no catálogo/grants ni títulos como autoridad.
const id397=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,120}$/.test(x);
const dia397=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T00:00:00Z'))&&new Date(x+'T00:00:00Z').toISOString().slice(0,10)===x;
function fecha397(x){if(typeof x!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(x)||!dia397(x.slice(0,10)))return null;const m=/T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(Z|([+-])(\d{2}):(\d{2}))$/.exec(x);if(+m[1]>23||+m[2]>59||+m[3]>59||(m[4]!=='Z'&&(+m[6]>14||+m[7]>59||(+m[6]===14&&+m[7]!==0))))return null;const n=Date.parse(x);return Number.isFinite(n)?n:null;}
const madrid397=n=>new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(n));
export function clasificarUrgencia397(t,{hoy,cliente_ids,catalogo,corte_utc}={}){
 const desconocido={es_fuego:null,estado:'sin_dato',detalle:'Falta acreditar urgencia y estado no final de la misma tarea/lectura. Un cliente en rojo o una fecha vencida no basta.'};
 if(!dia397(hoy)||!Array.isArray(cliente_ids)||cliente_ids.some(x=>!id397(x))||new Set(cliente_ids).size!==cliente_ids.length||!id397(t?.id)||!id397(t?.lista_id)||!cliente_ids.includes(t?.cliente_id))return desconocido;
 const m=t.medicion_urgencia,corte=fecha397(corte_utc),lectura=fecha397(m?.leido_utc);
 if(corte===null||lectura===null||lectura>corte||madrid397(corte)>hoy||m?.version!=='397.1'||m.fuente!=='clickup_task'||m.task_id!==t.id||m.lista_id!==t.lista_id||m.cliente_id!==t.cliente_id||m.prioridad!==t.prioridad||m.estado!==t.estado||!Array.isArray(m.campos_observados)||m.campos_observados.length!==2||new Set(m.campos_observados).size!==2||!['prioridad','estado'].every(x=>m.campos_observados.includes(x)))return desconocido;
 const tipos=['open','custom','unstarted','done','closed'],ls=catalogo?.[t.lista_id];
 if(!Array.isArray(ls)||!ls.length||ls.some(x=>typeof x?.estado!=='string'||!tipos.includes(x.tipo))||new Set(ls.map(x=>x.estado)).size!==ls.length)return desconocido;
 const estados=ls.filter(x=>x.estado===t.estado);if(estados.length!==1||t.tipo_estado!==estados[0].tipo||!['urgent','high','normal','low'].includes(t.prioridad))return desconocido;
 const base={cliente_id:t.cliente_id,tarea_id:t.id,lista_id:t.lista_id,fuente:'clickup_task',leido_utc:m.leido_utc,tipo_estado:estados[0].tipo,ejecucion_verificada:false};
 if(tipos.slice(3).includes(estados[0].tipo))return {...base,es_fuego:madrid397(lectura)===hoy?false:null,estado:'final_en_copia',detalle:'Final según catálogo exacto de lista en esta lectura; no acredita aceptación de entrega ni cierre actual fuera de la copia.'};
 if(t.prioridad!=='urgent')return {...base,es_fuego:madrid397(lectura)===hoy?false:null,estado:'sin_prioridad_urgente',detalle:'Prioridad observada no urgente. No se modifica por semáforo, título ni vencimiento.'};
 if(madrid397(lectura)!==hoy)return {...base,es_fuego:null,estado:'urgencia_historica_por_contrastar',detalle:'Urgent y estado no final en copia anterior. Pendiente contrastar si sigue abierto; no se presenta como fuego actual.'};
 return {...base,es_fuego:true,estado:'urgencia_abierta_observada',detalle:'Prioridad urgent y estado no final observados hoy en la misma lectura. No acredita ejecución ni fecha original de inicio de la urgencia.'};
}
