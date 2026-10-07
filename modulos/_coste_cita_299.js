// Hasta enlazar gasto y cita por identidad, el ratio heredado sólo es referencia.
const positivo=v=>typeof v==='number'&&Number.isFinite(v)&&v>0?v:null;
export function referenciaCita299(cpc){return positivo(cpc?.coste_por_cita_referencia_14d)??positivo(cpc?.coste_por_cita_14d);}
export function normalizarCita299(cpc){
 if(!cpc||typeof cpc!=='object'||Array.isArray(cpc))return null;
 return {...cpc,coste_por_cita_referencia_14d:referenciaCita299(cpc),coste_por_cita_14d:null,alarma_100:false,medicion:'referencia_legacy_sin_cohorte_enlazada'};
}
export function textoMetaQuincenal299(q,dinero,eur){
 q=q||{};const count=Number.isSafeInteger(q.leads_14d)&&q.leads_14d>0?q.leads_14d:null;
 const lines=[`· Resultados Meta · referencia: ${count===null?'Sin dato':'≥'+count}. Evento por confirmar; no acredita contactos únicos ni cualificación.`];
 if(dinero){lines.push(`· Gasto de la copia · 14 días: ${positivo(q.gasto_14d)===null?'Sin dato':eur(q.gasto_14d)}. Cuenta, moneda y periodo por contrastar.`);
 const ref=positivo(q.cpl_14d);lines.push(`· Coste por resultado · referencia anterior: ${ref===null?'Sin dato':eur(ref)}. Unidad por confirmar; no es CPL acreditado.`);
 const cita=positivo(q.coste_por_cita_referencia_14d)??positivo(q.coste_por_cita_14d);lines.push(`· Referencia anterior de gasto / citas: ${cita===null?'Sin dato':eur(cita)}. Sin cohorte enlazada; no acredita coste de captación de una cita.`);}
 return lines;
}
