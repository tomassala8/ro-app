import { textoSeguro, fechaSegura } from './_tarea_ia.js';
// No consultas ni campos inventados: sólo DTO y comentarios ya visibles.
const idValido = id => typeof id==='string' && /^[\w-]{3,40}$/.test(id);
export const enlaceTarea197 = id => idValido(id) ? `https://app.clickup.com/t/${encodeURIComponent(id)}` : null;
export function textoDetalle197(v,limite=12000) {
  if(typeof v!=='string')return '';
  const sinHost=v.replace(/https?:\/\/[^\s"<>]+/gi,u=>{
    try{const x=new URL(u);if(/(?:^|\.)zoom\.us$/i.test(x.hostname)&&/^\/s\//.test(x.pathname))return '[enlace de anfitrión omitido]';if(/[?&](?:zak|host_key|start_url|jwt|authorization)=/i.test(u))return '[enlace protegido omitido]';}catch{return '[enlace por contrastar]';}return u;
  });
  return textoSeguro(sinHost,limite);
}
export function prepararDetalleTarea197({tarea_id,persona_id,cliente_id,lista_id,tareasVisibles=[],cambios=[],actor_id,fechaFuente=''}) {
  const vacio={autorizado:false,brief:'',comentarios:[],hijas:[],padre:null};
  if(!idValido(tarea_id)||!persona_id||!actor_id||!Array.isArray(tareasVisibles))return vacio;
  const filas=tareasVisibles.filter(r=>r?.id===tarea_id);
  const firma=r=>JSON.stringify([r.cli ?? null,r.lista_id ?? null,r.padre ?? null,r.tarea ?? null]);
  if(!filas.some(r=>r.persona_id===persona_id&&r.cli===cliente_id&&r.lista_id===lista_id) || new Set(filas.map(firma)).size!==1)return vacio;
  const base=filas[0],briefs=[...new Set(filas.map(r=>typeof r.descripcion==='string'?r.descripcion:''))];
  const brief=briefs.length===1?textoDetalle197(briefs[0]):'';
  const grupos=new Map();
  for(const r of tareasVisibles){if(!idValido(r?.id))continue;if(!grupos.has(r.id))grupos.set(r.id,[]);grupos.get(r.id).push(r);}
  const relacionado=rs=>rs.every(r=>r.cli===cliente_id&&r.lista_id===lista_id)&&new Set(rs.map(firma)).size===1;
  const hijas=[];let padre=null;
  for(const [id,rs] of grupos){if(!relacionado(rs))continue;const r=rs[0],dto={id,titulo:textoDetalle197(r.tarea,400)||'Tarea',url:enlaceTarea197(id)};
    if(r.padre===tarea_id && id!==tarea_id)hijas.push(dto);
    if(id===base.padre && id!==tarea_id)padre=dto;
  }
  const estados={simulado:'Simulado en RO · no enviado a ClickUp',pendiente:'Pendiente de envío a ClickUp',enviado:'Enviado · sin confirmación de ClickUp',confirmado:'Estado local confirmado · consulta el hilo original',fallido:'Fallo de sincronía · revisa Envíos',conflicto:'Conflicto · revisa Envíos',descartado:'Descartado en RO'};
  const por=new Map();
  for(const c of Array.isArray(cambios)?cambios:[]){
    if(c?.tarea!==tarea_id || c.quien!==actor_id || c.campo!=='comentario' || typeof c.texto!=='string' || !c.texto.trim() || !estados[c.estado])continue;
    const texto=textoDetalle197(c.texto,2000);if(!texto)continue;
    const k=c.id!=null?'id:'+String(c.id):JSON.stringify([c.creado,c.quien,c.texto,c.estado]);
    const dto={texto,fecha:fechaSegura(c.creado)||null,estado:estados[c.estado],origen:c.local===true?'Esta sesión RO':'Archivo RO'};
    if(por.has(k) && JSON.stringify(por.get(k))!==JSON.stringify(dto)){por.set(k,null);continue;}if(!por.has(k))por.set(k,dto);
  }
  const todos=[...por.values()].filter(Boolean).sort((a,b)=>(b.fecha||'').localeCompare(a.fecha||''));
  return {autorizado:true,brief,brief_truncado:filas.some(r=>r.descripcion_truncada===true)||briefs.some(x=>x.length>12000),brief_discrepante:briefs.length!==1,
    fecha_fuente:fechaSegura(fechaFuente)||null,comentarios:todos.slice(0,20),comentarios_disponibles:todos.length,hijas:hijas.slice(0,30),hijas_disponibles:hijas.length,padre,
    padre_fuera_copia:!!base.padre && !padre,url:enlaceTarea197(tarea_id)};
}
