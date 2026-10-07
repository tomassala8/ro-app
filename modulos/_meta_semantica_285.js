// Identifica eventos observados; no acredita contactos, cualificación, ventas ni CPL.
const eventosLead285=new Set(['lead','onsite_conversion.lead_grouped','offsite_conversion.fb_pixel_lead','onsite_web_lead']);
const dia285=d=>typeof d==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(d)&&Number.isFinite(Date.parse(d+'T00:00Z'))&&new Date(d+'T00:00Z').toISOString().slice(0,10)===d;
export function semanticaMeta285(filas,cliente,hoy){
 const tienda=cliente?.tipo_negocio==='tienda_online'||cliente?.tienda_online===true;
 let tipo=null,acreditado=!!dia285(hoy)&&!tienda&&Array.isArray(filas)&&filas.length>0;
 for(const f of Array.isArray(filas)?filas:[]){
  const m=f?.medicion,fecha=typeof m?.fecha_lectura==='string'?m.fecha_lectura.slice(0,10):null;
  const stamp=typeof m?.fecha_lectura==='string'?m.fecha_lectura.replace(' ','T'):'';
  if(!m||m.version!=='220.1'||m.fuente!=='meta_insights'||m.nivel!=='account'||m.periodo_valido!==true||
     m.desde!==f.d||m.hasta!==f.d||!dia285(f.d)||!dia285(fecha)||fecha>hoy||fecha<f.d||
     !/^\d{4}-\d{2}-\d{2}(?:T(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?)?$/.test(stamp)||!Number.isFinite(Date.parse(stamp))||
     m.cohorte!=='resultados_meta_sin_union_crm_ni_cualificacion_ro'||!Array.isArray(m.campos_observados)||!m.campos_observados.includes('leads')||
     !eventosLead285.has(m.tipo_lead)||!Number.isSafeInteger(f.leads_meta)||f.leads_meta<0||f.error||f.errores?.length)acreditado=false;
  if(tipo!==null&&tipo!==m?.tipo_lead)acreditado=false;
  tipo=m?.tipo_lead||null;
 }
 return {eventos_lead_acreditados:acreditado,tipo_evento:acreditado?tipo:null,
  etiqueta:acreditado?'eventos lead Meta':'Resultados Meta',
  detalle:acreditado?'Eventos lead declarados por Meta; no contactos únicos ni leads cualificados.':
   tienda?'Tienda online: contador Meta sin definición de evento acreditada; no se afirma que sean leads ni compras.':'Contador Meta; definición pendiente. No acredita leads ni compras.',
  cualificados:false,contactos_unicos:false,compras:false,conversion_crm:false,cpl_real:false};
}
