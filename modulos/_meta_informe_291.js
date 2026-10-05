// Informes comerciales: legado conserva contador, nunca lo convierte en lead/CPL.
const leadTipos=new Set(['lead','onsite_conversion.lead_grouped','offsite_conversion.fb_pixel_lead','onsite_web_lead']);
const num=(v,entero=false)=>typeof v==='number'&&Number.isFinite(v)&&v>=0&&(!entero||Number.isSafeInteger(v))?v:null;
const dia=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+'T00:00Z'))&&new Date(v+'T00:00Z').toISOString().slice(0,10)===v;
export function metaInforme291(actual,fuente,periodo,hoy,cliente={},nivel='account'){
 const a=actual||{},m=a.medicion,fecha=typeof m?.fecha_lectura==='string'?m.fecha_lectura.slice(0,10):null;
 const cuenta=x=>typeof x==='string'||typeof x==='number'?String(x).replace(/^act_/,''):null;
 const cid=cuenta(fuente?.cuenta?.id),mid=cuenta(m?.cuenta_id);
 const typed=m?.version==='220.1'&&m.fuente==='meta_insights'&&m.nivel===nivel&&m.periodo_valido===true&&dia(m.desde)&&dia(m.hasta)&&m.desde<=m.hasta&&m.desde===periodo?.desde&&m.hasta===periodo?.hasta&&dia(fecha)&&dia(hoy)&&fecha>=m.hasta&&fecha<=hoy&&/^\d{4}-\d{2}-\d{2}[T ](?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?$/.test(m.fecha_lectura)&&Number.isFinite(Date.parse(m.fecha_lectura.replace(' ','T')))&&m.cohorte==='resultados_meta_sin_union_crm_ni_cualificacion_ro'&&Array.isArray(m.campos_observados)&&cid&&mid===cid&&!a.error&&!a.errores?.length&&!fuente?.error&&!fuente?.errores?.length;
 const tienda=cliente?.tipo_negocio==='tienda_online'||cliente?.tienda_online===true;
 const leads=typed&&!tienda&&m.campos_observados.includes('leads')&&leadTipos.has(m.tipo_lead)?num(a.leads,true):null;
 const moneda=typeof m?.moneda==='string'&&/^[A-Z]{3}$/.test(m.moneda)&&m.moneda===fuente?.moneda;
 const gasto=typed&&moneda&&m.campos_observados.includes('gasto')?num(a.gasto):null;
 const resultados=typed&&m.campos_observados.includes('leads')?num(a.leads,true):(num(a.leads,true)>0?a.leads:null);
 return {resultados,leads,cpl:leads>0&&gasto!==null?gasto/leads:null,etiqueta:leads!==null?'Eventos lead Meta':'Resultados Meta · referencia',evento:leads!==null?m.tipo_lead:null,typed:!!typed,detalle:leads!==null?'Eventos declarados por Meta, no contactos únicos, cualificados RO ni ventas.':'Evento por confirmar. Este recuento no acredita leads ni compras.',campo:k=>typed&&m.campos_observados.includes(k)?num(a[k],k!=='gasto'&&k!=='frecuencia'):(num(a[k],k!=='gasto'&&k!=='frecuencia')>0?a[k]:null)};
}
