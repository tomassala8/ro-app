import { semanticaMeta285 } from './_meta_semantica_285.js';
import { medirCplPaid } from './_paid_mediciones.js';
import { normalizarFilaCRM, medirEmbudoCRM } from './_crm_mediciones.js';
const count=v=>Number.isSafeInteger(v)&&v>=0?v:null;
const dia=v=>{if(typeof v!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(v))return null;const t=Date.parse(v+'T00:00Z');return Number.isFinite(t)&&new Date(t).toISOString().slice(0,10)===v?v:null;};
export function clientesDia314(ctx,filas){
 const clientes=ctx.clientesVisibles||ctx.clientes||[],counts=new Map();
 for(const c of clientes)counts.set(c.id,(counts.get(c.id)||0)+1);
 const ids=new Set(clientes.filter(c=>c.activo_confirmado===true&&counts.get(c.id)===1&&(!ctx.ver||ctx.ver({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true)).map(c=>c.id));
 const rep=new Map();for(const f of filas||[])rep.set(f.cliente_id,(rep.get(f.cliente_id)||0)+1);
 return (filas||[]).filter(f=>ids.has(f.cliente_id)&&rep.get(f.cliente_id)===1);
}
export function metaDia314(c,cap,clave,hoy){
 const ventana=cap?.ventanas?.[clave],desde=dia(Array.isArray(ventana)?ventana[0]:ventana),hasta=dia(Array.isArray(ventana)?ventana[1]:ventana),h=dia(hoy);
 const ref=count(c?.leads?.[clave]);
 const r={valor:null,referencia:ref>0?ref:null,etiqueta:'Resultados Meta · referencia',tipo:null,acreditado:false,desde,hasta};
 if(!h||!desde||!hasta||desde>hasta||hasta>=h||Date.parse(hasta)-Date.parse(desde)>35*864e5||c?.cuenta_meta?.error||c?.cuenta_meta?.errores?.length||c?.errores_lectura?.length)return r;
 const fin=new Date(Date.parse(h)-(clave==='7d_prev'?8:1)*864e5).toISOString().slice(0,10);
 if(!['ayer','7d','7d_prev'].includes(clave)||hasta!==fin||(Date.parse(hasta)-Date.parse(desde))/864e5!==(clave==='ayer'?0:6))return r;
 const fs=(c.serie||[]).filter(f=>dia(f.d)&&f.d>=desde&&f.d<=hasta),dias=new Set(fs.map(f=>f.d));
 const n=(Date.parse(hasta)-Date.parse(desde))/864e5+1;
 if(fs.length!==n||dias.size!==n)return r;
 const sem=semanticaMeta285(fs,{...c,tienda_online:c.tienda_online===true||c.cliente_id==='kiosko-box'},h);
 if(!sem.eventos_lead_acreditados)return r;
 return {...r,valor:fs.reduce((a,f)=>a+f.leads_meta,0),etiqueta:'eventos lead Meta',tipo:sem.tipo_evento,acreditado:true};
}
export function textoMetaDia314(m){return m.acreditado?`${m.valor} ${m.etiqueta}`:m.referencia!==null?`≥${m.referencia} ${m.etiqueta} (evento por confirmar)`:'Resultados Meta: Sin dato';}
export function totalMetaDia314(ms){
 const first=ms[0];return ms.length&&ms.every(m=>m.acreditado&&m.tipo===first.tipo&&m.desde===first.desde&&m.hasta===first.hasta)?ms.reduce((n,m)=>n+m.valor,0):null;
}
export function resultadosFilaDia314(c,cap,hoy){
 const m=metaDia314(c,cap,'7d',hoy),p=medirCplPaid(c,cap,hoy);
 return {meta:m,cpl:p,estado:p.evaluable?p.estado:'gris',extra:textoMetaDia314(m)+' · 7 días'+(p.real!==null?` · CPL observado: ${p.real} €${p.evaluable?' · objetivo propio vigente':' · objetivo por confirmar'}`:p.referenciaAnterior!==null?' · coste anterior por contrastar; no CPL acreditado':' · CPL: Sin dato')};
}
export function crmDia314(s,crm,hoy){
 return normalizarFilaCRM(s,crm?.fuentes?.ghl,hoy,crm?.fuentes?.captacion);
}
export function fuenteCrmDia314(crm,hoy){return medirEmbudoCRM({},crm?.fuentes?.ghl,hoy).fechaValida===true;}
