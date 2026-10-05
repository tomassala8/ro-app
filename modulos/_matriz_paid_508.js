// Lectura de la matriz: el contador legado no acredita eventos lead ni cualificación.
export const cuentaMetaError508=c=>!!c?.cuenta_meta?.error||!!c?.cuenta_meta?.errores?.length||!!c?.errores_lectura?.length;
export const conteoMeta508=v=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=0?v:null;
const dia508=v=>{if(typeof v!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(v))return null;const t=Date.parse(v+'T12:00:00Z');return Number.isFinite(t)&&new Date(t).toISOString().slice(0,10)===v?t:null;};
const lectura508=v=>{if(typeof v!=='string')return null;const m=/^(\d{4}-\d{2}-\d{2})(?:[T ]([01]\d|2[0-3]):([0-5]\d)(?::([0-5]\d)(?:\.\d{1,6})?)?(?:Z|([+-])(\d{2}):(\d{2}))?)?$/.exec(v);if(!m||m[5]&&(+m[6]>14||+m[7]>59||+m[6]===14&&+m[7]!==0))return null;return dia508(m[1]);};
export function deltaMeta508(c,d,hoy){
 const a=conteoMeta508(c?.leads?.['7d']),b=conteoMeta508(c?.leads?.['7d_prev']),w=d?.ventanas?.['7d'],p=d?.ventanas?.['7d_prev'];
 const aa=dia508(w?.[0]),ab=dia508(w?.[1]),pa=dia508(p?.[0]),pb=dia508(p?.[1]),actual=dia508(hoy);
 if(a===null||b===null||b===0||!Array.isArray(w)||w.length!==2||!Array.isArray(p)||p.length!==2||[aa,ab,pa,pb,actual].some(v=>v===null)||ab-aa!==6*864e5||pb-pa!==6*864e5||aa-pb!==864e5||ab>=actual||c?.cuenta_meta?.error||c?.cuenta_meta?.errores?.length||c?.errores_lectura?.length)return null;
 const serie=Array.isArray(c?.serie)?c.serie:[],dias=new Map();let tipo=null,cuenta=null,moneda=null;
 for(let t=pa;t<=ab;t+=864e5){const date=new Date(t).toISOString().slice(0,10),rs=serie.filter(r=>r?.d===date);if(rs.length!==1)return null;const r=rs[0],m=r.medicion,n=conteoMeta508(r.leads_meta);
  if(n===null||r.error||r.errores?.length||m?.version!=='220.1'||m.fuente!=='meta_insights'||m.nivel!=='account'||m.periodo_valido!==true||m.desde!==date||m.hasta!==date||m.cohorte!=='resultados_meta_sin_union_crm_ni_cualificacion_ro'||!['lead','onsite_conversion.lead_grouped','offsite_conversion.fb_pixel_lead','onsite_web_lead'].includes(m.tipo_lead)||!Array.isArray(m.campos_observados)||!m.campos_observados.includes('leads')||tipo!==null&&tipo!==m.tipo_lead)return null;
  if(typeof m.cuenta_id!=='string'||! /^[1-9][0-9]{0,29}$/.test(m.cuenta_id)||typeof m.moneda!=='string'||! /^[A-Z]{3}$/.test(m.moneda)||cuenta!==null&&cuenta!==m.cuenta_id||moneda!==null&&moneda!==m.moneda)return null;cuenta=m.cuenta_id;moneda=m.moneda;
  const leida=lectura508(m.fecha_lectura);if(leida===null||leida<t||leida>actual)return null;tipo=m.tipo_lead;dias.set(t,n);
 }
 let suma=0,antes=0;for(const [t,n]of dias){if(t>=aa)suma+=n;else antes+=n;}if(!Number.isSafeInteger(suma)||!Number.isSafeInteger(antes)||suma!==a||antes!==b)return null;
 const delta=(a-b)/b*100;return Number.isFinite(delta)?delta:null;
}
export function creativosMatriz508(c,d,hoy){
 const rs=c?.anuncios?.anuncios,actual=dia508(hoy),stamp=d?.anuncios_generado||d?.fuentes?.find?.(f=>f.id==='anuncios')?.hora,leida=lectura508(stamp);
 if(!Array.isArray(rs)||!rs.length||actual===null||leida===null||leida>actual||c?.cuenta_meta?.error||c?.cuenta_meta?.errores?.length||c?.anuncios?.errores?.length)return null;
 const ids=new Set();
 for(const r of rs){
  if(!r||typeof r!=='object'||Array.isArray(r)||typeof r.ad_id!=='string'||!r.ad_id.length||r.ad_id.length>256||r.ad_id.trim()!==r.ad_id||/[\u0000-\u001f\u007f]/.test(r.ad_id)||typeof r.vigilar!=='boolean'||typeof r.cansada!=='boolean'||ids.has(r.ad_id))return null;
  ids.add(r.ad_id);
 }
 const n=rs.filter(r=>r.vigilar===true||r.cansada===true).length;
 const estado=d?.fuentes?.find?.(f=>f.id==='anuncios')?.estado;
 if(n===0&&estado&& !['bien','ok'].includes(estado))return null;
 return {valor:n,parcial:true};
}
