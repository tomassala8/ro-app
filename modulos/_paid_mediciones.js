// CPL observado frente a objetivo: snapshot/techo no acredita objetivo vigente.
const numero=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0?v:null;
const dia=v=>{if(typeof v!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(v))return null;const d=new Date(v+'T12:00:00Z');return Number.isFinite(+d)&&d.toISOString().slice(0,10)===v?v:null;};
const fechaISO=v=>{if(typeof v!=='string'||!/^\d{4}-\d{2}-\d{2}(?:[T ](?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?)?$/.test(v))return null;return dia(v.slice(0,10))&&Number.isFinite(Date.parse(v.length===10?v+'T12:00:00Z':v.replace(' ','T')))?v.slice(0,10):null;};
const tiposLead285=new Set(['lead','onsite_conversion.lead_grouped','offsite_conversion.fb_pixel_lead','onsite_web_lead']);
const tienda285=c=>c?.tienda_online===true||c?.tipo_negocio==='tienda_online'||c?.cliente_id==='kiosko-box';
const error285=c=>!!c?.cuenta_meta?.error||!!c?.cuenta_meta?.errores?.length||!!c?.errores_lectura?.length;
function descriptor285(m,desde,hasta,hoy){
 const fecha=fechaISO(m?.fecha_lectura),actual=dia(hoy);
 return !!actual&&!!fecha&&fecha<=actual&&fecha>=hasta&&(Date.parse(actual)-Date.parse(fecha))/864e5<=2&&
  m?.version==='220.1'&&m.fuente==='meta_insights'&&m.nivel==='account'&&m.periodo_valido===true&&m.desde===desde&&m.hasta===hasta&&
  m.cohorte==='resultados_meta_sin_union_crm_ni_cualificacion_ro'&&tiposLead285.has(m.tipo_lead)&&Array.isArray(m.campos_observados)&&['gasto','leads'].every(k=>m.campos_observados.includes(k));
}
export function unidadCplPaid285(c,d,hoy){
 const r=c?.cpl_resumen||{},ventana=d?.ventanas?.[r.ref_base],desde=dia(ventana?.[0]),hasta=dia(ventana?.[1]);
 const gasto=numero(c?.gasto?.[r.ref_base]),leads=c?.leads?.[r.ref_base],ref=numero(r.ref);
 const valido=!!c?.dinero&&!error285(c)&&!tienda285(c)&&!!desde&&!!hasta&&desde<=hasta&&descriptor285(r.medicion,desde,hasta,hoy)&&
  gasto!==null&&Number.isSafeInteger(leads)&&leads>0&&ref!==null&&Math.abs(ref-Math.round(gasto/leads*100)/100)<0.005;
 return {acreditada:valido,tipo:valido?r.medicion.tipo_lead:null};
}
export function cplMovilPaid285(c,serie,hoy){
 const filas=Array.isArray(serie)?serie:[];
 return filas.map((p,i)=>{
  const fs=filas.slice(Math.max(0,i-6),i+1),fin=dia(p?.d);let ok=!!c?.dinero&&!error285(c)&&!tienda285(c)&&!!fin&&fs.length===7,g=0,l=0,tipo=null;
  for(let k=0;k<fs.length;k++){const f=fs[k],d=dia(f?.d),v=numero(f?.gasto_meta),n=f?.leads_meta;
   if(!d||d!==new Date(Date.parse(fin||'1970-01-01')-(6-k)*864e5).toISOString().slice(0,10)||!descriptor285(f.medicion,d,d,hoy)||v===null||!Number.isSafeInteger(n)||n<0||f.error||f.errores?.length)ok=false;
   if(tipo!==null&&tipo!==f?.medicion?.tipo_lead)ok=false;tipo=f?.medicion?.tipo_lead||null;g+=v??0;l+=Number.isSafeInteger(n)&&n>=0?n:0;
  }
  return {x:p?.d,y:ok&&l>0?Math.round(g/l*100)/100:null};
 });
}
export function medirCplPaid(c,d,hoy) {
 const actual=dia(hoy),hasta=dia(d?.datos_hasta),r=c?.cpl_resumen||{},o=c?.objetivo||{};
 const error=!!c?.cuenta_meta?.error||!!c?.cuenta_meta?.errores?.length||!!c?.errores_lectura?.length;
 const unidad=unidadCplPaid285(c,d,hoy);
 const referenciaAnterior=c?.dinero&&!error?numero(r.ref):null;
 const real=!error&&unidad.acreditada?referenciaAnterior:null;
 const objetivo=c?.dinero&&o.cargado===true&&numero(o.cpl_objetivo)>0?numero(o.cpl_objetivo):null;
 const fechaObjetivo=fechaISO(o.cuando);
 const registro=objetivo!==null&&fechaObjetivo&&actual&&fechaObjetivo<=actual;
 const vf=fechaISO(o.fuente_generado), fuenteActual=actual&&vf&&0<=((Date.parse(actual)-Date.parse(vf))/864e5)&&((Date.parse(actual)-Date.parse(vf))/864e5)<=2;
 const limiteValido=k=>!(k in o)||(dia(o[k])&&actual&&(k==='vigente_desde'?o[k]<=actual:o[k]>=actual));
 const ratificado=o.confirmado===true&&!['propuesta','pendiente','borrador','no_confirmado','rechazado'].includes(String(o.estado||'').toLowerCase());
 const objetivoVigente=ratificado&&!!registro&&o.vigente===true&&!!fuenteActual&&limiteValido('vigente_desde')&&limiteValido('vigente_hasta')&&(!('periodo' in o)||o.periodo===actual.slice(0,7));
 const ventana=d?.ventanas?.[r.ref_base],ini=dia(ventana?.[0]),fin=dia(ventana?.[1]);
 const comparable=!!actual&&!!hasta&&!!ini&&!!fin&&fin===hasta&&fin<actual&&((Date.parse(fin)-Date.parse(ini))/864e5)===6&&((Date.parse(actual)-Date.parse(fin))/864e5)===1&&r.fiable===true;
 const evaluable=real!==null&&objetivo!==null&&objetivoVigente&&comparable;
 return {real,referenciaAnterior,unidadAcreditada:unidad.acreditada,tipoEvento:unidad.tipo,objetivo,fechaObjetivo:fechaObjetivo||null,hasta,comparable,objetivoVigente,evaluable,
  estado:evaluable?(real<=objetivo?'verde':real<=objetivo*1.5?'ambar':'rojo'):'gris',
  nota:!c?.dinero?'Inversión reservada':error?'Lectura de Meta con error; no se evalúa CPL':!unidad.acreditada?'Referencia anterior: no se acredita gasto y eventos lead Meta de una misma ventana; no es CPL real ni prueba de compras':!objetivoVigente?'Referencia del snapshot sin acuerdo y vigencia acreditados; confirmar en Prioridades por cliente':!comparable?'Ventana/muestra sin comparabilidad acreditada; no se evalúa cumplimiento':'Comparación con objetivo propio vigente y semana cerrada; no mide calidad del lead'};
}
export function normalizarPaid(c,d,hoy) {
 const medicion=medirCplPaid(c,d,hoy);
 const anterior=m=>({...m,nivel:'dato',objetivo_sin_cargar:false,
  texto:'Señal anterior por contrastar: '+String(m.texto||''),
  gasto_texto:m.gasto_texto?'Señal anterior por contrastar: '+m.gasto_texto:undefined});
 const motivos=(c.motivos||[]).map(anterior),avisos=(c.avisos||[]).map(anterior);
 if(medicion.evaluable&&medicion.estado==='rojo')motivos.unshift({nivel:'critico',clase_id:'paid',clase:'Publicidad',texto:'CPL observado supera 1,5 veces el objetivo propio vigente en semana comparable; contrastar calidad y captación.'});
 return {...c,motivos,avisos,_cplMedicion:medicion,severidad_original:c.severidad,
  severidad:medicion.evaluable?({verde:'ok',ambar:'atencion',rojo:'critico'})[medicion.estado]:'dato'};
}
