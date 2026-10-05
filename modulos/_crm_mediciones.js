// Lectura pura de un snapshot autorizado: stock no es conversión ni ventas.
const conteo = v => typeof v === 'number' && Number.isSafeInteger(v) && v >= 0 ? v : null;
function fecha(v) {
  if (typeof v !== 'string') return null;
  const s = v.replace(' ', 'T');
  if (!/^\d{4}-\d{2}-\d{2}(?:T(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?)?$/.test(s)) return null;
  const dia = s.slice(0,10), d = new Date(`${dia}T12:00:00Z`);
  return Number.isFinite(+d) && d.toISOString().slice(0,10) === dia && Number.isFinite(Date.parse(s.length===10?`${s}T12:00:00Z`:s)) ? dia : null;
}
const fallo = d => !!d?.error || !!d?.errores?.length || !!d?.errores_lectura?.length;
export function medirEmbudoCRM(ghl, fuente, hoy) {
  const actual=fecha(hoy), leido=fecha(fuente?.hora);
  const hasta=fuente&&Object.hasOwn(fuente,'datos_hasta')?fecha(fuente.datos_hasta):leido;
  const reciente=d=>!!d&&!!actual&&d<=actual&&(Date.parse(actual)-Date.parse(d))/864e5<=2;
  // Una lectura con hora debe ser válida y no posterior al reloj; el día solo no basta.
  const tiempoValido=v=>typeof v==='string'&&(/^\d{4}-\d{2}-\d{2}$/.test(v)?fecha(v)!==null:corteCRM541(v,hoy)!==null);
  const valido=reciente(leido)&&reciente(hasta)&&tiempoValido(fuente?.hora)&&(!Object.hasOwn(fuente||{},'datos_hasta')||tiempoValido(fuente.datos_hasta))&&fuente?.estado==='bien'&&!fallo(fuente);
  const e=ghl?.embudo, cit=ghl?.citas, c14=cit?.['14d'];
  const embValido=valido && !fallo(ghl) && !fallo(e) && !!e && typeof e==='object' && !Array.isArray(e);
  const citasValidas=valido && !fallo(ghl) && !fallo(cit) && !fallo(c14) && !!c14 && typeof c14==='object' && !Array.isArray(c14);
  let total=embValido?conteo(e.contactos_90d):null;
  let etapas=['nuevo','seguimiento','cita','presupuesto','cerrado','descartado'].map(k=>({id:k,n:embValido?conteo(e.funnel?.[k]):null}));
  const suma=etapas.reduce((s,x)=>s+(x.n??0),0);
  const incoherente=total!==null && suma>total;
  if(incoherente){total=null;etapas=etapas.map(x=>({...x,n:null}));}
  const cohorte=embValido?conteo(e.cohorte_30d):null;
  const rawParados=embValido?conteo(e.estancados_72h):null;
  const parados=cohorte!==null && rawParados!==null && rawParados<=cohorte ? rawParados : null;
  let agendadas=citasValidas?conteo(c14.agendadas):null;
  let celebradas=citasValidas?conteo(c14.celebradas):null, ausencias=citasValidas?conteo(c14.no_presentadas):null;
  let sinEstado=citasValidas?conteo(c14.sin_estado):null;
  const ventana=citasValidas?conteo(c14.con_fecha_en_ventana):null;
  const canceladas=citasValidas?conteo(c14.canceladas):null;
  if(ventana!==null && [celebradas,ausencias,sinEstado,canceladas].reduce((s,n)=>s+(n??0),0)>ventana){celebradas=null;ausencias=null;sinEstado=null;}
  const marcadas=celebradas!==null && ausencias!==null ? celebradas+ausencias:null;
  const asistencia=marcadas>0 ? celebradas/marcadas*100 : null;
  return {fecha:leido,medido_hasta:hasta,vigencia:valido?'actual':'sin_vigencia',fuente:typeof fuente?.fuente==='string'?fuente.fuente:'GoHighLevel',fechaValida:valido,
    total,etapas,incoherente,cohorte,parados,agendadas,celebradas,ausencias,sinEstado,marcadas,asistencia,
    proximas:valido&&!fallo(ghl)&&!fallo(cit)?conteo(cit?.proximas):null,
    cobertura:'registros_observados_no_exhaustivos',conversiones:null,ventas:null,
    aviso:!valido?'Fuente anterior, fallida o sin medición reciente confirmada; no se evalúan estos recuentos como actuales.':incoherente?'Recuentos de etapas incoherentes; contrastar la fuente.':'Lectura parcial: el stock de etapas no acredita conversiones, cualificación ni ventas.'};
}
export const conteoCRM = conteo;
// El texto del generador anterior no confirma contratos ni cobertura completa.
const REVISIONES = Object.freeze({
 sin_uso:'Uso de GHL por confirmar: revisar contactos y servicio contratado.',
 citas_fuera:'Contrastar la agenda del cliente con las reservas registradas en GHL.',
 integracion:'Contrastar origen y recepción de leads antes de diagnosticar la integración.',
 sin_tocar:'Revisar leads sin intento registrado en esta copia; confirmar llamadas fuera de GHL.',
 sin_estado:'Completar el resultado de las citas pendientes tras confirmarlo con el despacho.',
 asistencia:'Contrastar asistencia y ausencias registradas; la muestra no cubre todas las citas.',
 sin_citas:'Revisar reservas y cobertura de la agenda; la copia no acredita ausencia de citas.',
 estancados:'Revisar oportunidades y origen de la fecha de cambio; updatedAt no confirma cambio de etapa.',
 whatsapp:'Revisar los envíos con fallo registrado y su causa antes de reenviar.',
 sin_automatico:'Comprobar automatizaciones y mensajes registrados por lead.',
 velocidad:'Revisar tiempos del primer intento registrado; no evalúa la garantía contractual.',
});
export function medirCitasCRM(citas,fuente,hoy) {
  return medirEmbudoCRM({citas:{'14d':citas}},fuente,hoy);
}
//541 · corte de la copia; hora naive del productor CRM declara Europe/Madrid.
export function corteCRM541(v,hoy){
 if(typeof v!=='string'||typeof hoy!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(hoy))return null;
 const m=/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,3}))?)?(Z|[+-]\d{2}:\d{2})?$/.exec(v);
 if(!m)return null;const [y,mo,d,hh,mm,ss]=m.slice(1,7).map(x=>Number(x||0));
 const wall=Date.UTC(y,mo-1,d,hh,mm,ss,Number((m[7]||'').padEnd(3,'0')));
 if(hh>23||mm>59||ss>59||new Date(wall).toISOString().slice(0,10)!==v.slice(0,10)||v.slice(0,10)>hoy)return null;
 let t;
 if(m[8]){if(m[8]!=='Z'){const h=Number(m[8].slice(1,3)),min=Number(m[8].slice(4,6));if(h>14||min>59||h===14&&min>0)return null;}t=Date.parse(v.replace(' ','T'));}
 else{const fmt=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}),candidates=[60,120].map(offset=>wall-offset*60000).filter(x=>{const a=Object.fromEntries(fmt.formatToParts(new Date(x)).map(p=>[p.type,p.value]));return a.year===m[1]&&a.month===m[2]&&a.day===m[3]&&a.hour===m[4]&&a.minute===m[5]&&a.second===String(ss).padStart(2,'0');});if(candidates.length!==1)return null;t=candidates[0];}
 const today=Date.parse(hoy+'T12:00:00Z');if(!Number.isFinite(today)||new Date(today).toISOString().slice(0,10)!==hoy)return null;
 return Number.isFinite(t)&&t<=Date.now()?t:null;
}
const idColor541=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,100}$/.test(x);
function fuenteColor541(f,fuente,hoy){return idColor541(f?.cliente_id)&&idColor541(f?.sub_id)&&medirEmbudoCRM({},fuente,hoy).fechaValida&&fuente?.estado==='bien'&&!fallo(fuente)&&Array.isArray(f?.errores_lectura)&&f.errores_lectura.length===0&&!fallo(f)&&corteCRM541(fuente.hora,hoy)!==null;}
function enVentanaCerrada541(instante,corte,dias){
 const fmt=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit'});
 const dia=t=>{const a=Object.fromEntries(fmt.formatToParts(new Date(t)).map(p=>[p.type,p.value]));return `${a.year}-${a.month}-${a.day}`;};
 const hasta=dia(corte),desde=new Date(Date.parse(hasta+'T12:00:00Z')-dias*864e5).toISOString().slice(0,10),observado=dia(instante);
 // Ventanas cerradas publicadas por este productor, no una nueva cohorte inferida.
 return observado>=desde&&observado<hasta;
}
export function senalFilaCRM541(tipo,x,fuente,hoy,base){
 const same=(Array.isArray(base)?base:[]).filter(f=>f?.sub_id===x?.sub_id),cut=corteCRM541(fuente?.hora,hoy);
 const unknown={estado:'gris',fecha:fuente?.hora||null,horas:null,motivo:'Referencia guardada por contrastar; no acredita ausencia de contacto ni cambio de etapa.'};
 if(!idColor541(x?.cliente_id)||!idColor541(x?.sub_id)||same.length!==1||same[0].cliente_id!==x.cliente_id||!fuenteColor541(same[0],fuente,hoy)||cut===null)return unknown;
 if(tipo==='cita'){
  // Inicio con zona del evento, nunca el nºhoras redondeado del generador.
  if(typeof x.inicio!=='string'||!/(Z|[+-]\d{2}:\d{2})$/.test(x.inicio)||!['confirmed','new','booked','sin_estado'].includes(x.estado_ghl))return unknown;
  const start=corteCRM541(x.inicio,hoy);if(start===null||start>cut||!enVentanaCerrada541(start,cut,14))return unknown;
  const horas=(cut-start)/36e5;return{estado:horas>48?'rojo':'ambar',fecha:fuente.hora,horas,motivo:'Resultado pendiente observado al corte de la copia;48h es referencia operativa, no SLA ni asistencia.'};
 }
 if(tipo==='lead'){
  if(typeof x.creado!=='string'||!/(Z|[+-]\d{2}:\d{2})$/.test(x.creado))return unknown;
  const created=corteCRM541(x.creado,hoy);if(created===null||created>cut||!enVentanaCerrada541(created,cut,30))return unknown;
  return{estado:'ambar',fecha:fuente.hora,horas:(cut-created)/36e5,motivo:'Lead señalado sin intento registrado en esta lectura parcial; no acredita ausencia de llamadas externas.'};
 }
 return unknown;
}
export function senalesSubcuentaCRM541(f,fuente,hoy){
 if(!fuenteColor541(f,fuente,hoy))return [];
 const s=[],add=(clave,n,texto)=>{if(conteo(n)!==null&&n>0)s.push({clave,n,nivel:'ambar',texto,origen:'observacion_muestra',fecha:fuente.hora});};
 add('sin_tocar',f.sin_tocar_24h,`${f.sin_tocar_24h} leads señalados sin intento registrado en la copia; contrastar llamadas externas.`);
 add('sin_estado',f.citas_14d?.sin_estado,`${f.citas_14d?.sin_estado} citas con resultado pendiente registrado en la muestra14d; confirmar con el despacho.`);
 const w=f.whatsapp;if(conteo(w?.enviados)!==null&&conteo(w?.fallidos)!==null&&w.enviados>0&&w.fallidos<=w.enviados)add('whatsapp',w.fallidos,`${w.fallidos} fallos WhatsApp de ${w.enviados} mensajes observados; revisar causa y cobertura.`);
 return s;
}
export function normalizarFilaCRM(f, fuente, hoy, fuenteEmbudo=fuente) {
 const base=medirEmbudoCRM({},fuente,hoy), valido=base.fechaValida&&!fallo(f);
 const count=v=>valido?conteo(v):null;
 const citas=k=>{const raw=f[k]||{},p=medirCitasCRM(raw,valido?fuente:null,hoy);return {...raw,agendadas:p.agendadas,celebradas:p.celebradas,no_presentadas:p.ausencias,sin_estado:p.sinEstado,asistencia_pct:p.asistencia,futuras:valido&&!fallo(raw)?conteo(raw.futuras):null};};
 const v=f.velocidad||{}, velocidadValida=valido&&!fallo(v),countV=x=>velocidadValida?conteo(x):null, observado=velocidadValida?v:Object.fromEntries(Object.keys(v).map(k=>[k,null])), juz=countV(v.juzgables),en=countV(v.en_1h),j72=countV(v.juzgables_72h),cuatro=countV(v.cuatro_en_72h);
 const velocidad={...observado,auto_5min:countV(v.auto_5min),juzgables:juz,en_1h:juz!==null&&en!==null&&en<=juz?en:null,pct_1h:juz>0&&en!==null&&en<=juz?en/juz*100:null,
  juzgables_72h:j72,cuatro_en_72h:j72!==null&&cuatro!==null&&cuatro<=j72?cuatro:null,pct_4en72:j72>0&&cuatro!==null&&cuatro<=j72?cuatro/j72*100:null};
 const e=medirEmbudoCRM({embudo:f.embudo},fallo(f)?null:fuenteEmbudo,hoy);
 const mensajes=normalizarMensajesCRM597(f,fuente,hoy);
 const senales=valido?senalesSubcuentaCRM541({...f,...mensajes},fuente,hoy):[];
 const referencias=(Array.isArray(f.motivos)?f.motivos:[]).filter(m=>m&&typeof m==='object'&&!Array.isArray(m)&&!senales.some(x=>x.clave===m.clave)).map(m=>({...m,nivel:'dato',origen:'referencia_legacy',texto:'Señal anterior: '+(REVISIONES[m.clave]||'Contrastar esta señal en GHL antes de concluir qué ocurre.')}));
 const motivos=[...senales,...referencias];
 return {...f,...mensajes,motivos,mot1:motivos[0]||null,leads_30d:count(f.leads_30d),sin_tocar_24h:count(f.sin_tocar_24h),leads_manuales_30d:count(f.leads_manuales_30d),
  citas_14d:citas('citas_14d'),citas_30d:citas('citas_30d'),citas_90d:citas('citas_90d'),velocidad,
  embudo:f.embudo?{...f.embudo,cohorte_30d:e.cohorte,estancados_72h:e.parados,funnel:Object.fromEntries(e.etapas.map(x=>[x.id,x.n]))}:null,
  _medicionCRM:{fecha:base.fecha,medido_hasta:base.medido_hasta,vigencia:base.vigencia,cobertura:base.cobertura,fechaValida:valido},
  estado_referencia:f.estado,estado:senales.length?'ambar':'gris'};
}

//597 · canales separados, muestra de leads30d del productor (no censo de mensajes).
function descriptorMensajes597(f,fuente,hoy){
 const cut=corteCRM541(fuente?.hora,hoy);
 if(!fuenteColor541(f,fuente,hoy)||cut===null||conteo(f?.leads_30d)===null)return null;
 const parts=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(cut)).map(x=>[x.type,x.value]));
 const hasta=`${parts.year}-${parts.month}-${parts.day}`;
 return {version:'597.1',fuente:'GHL',corte_utc:new Date(cut).toISOString(),desde:new Date(Date.parse(hasta+'T12:00:00Z')-30*864e5).toISOString().slice(0,10),hasta_exclusivo:hasta,zona:'Europe/Madrid',definicion:'salidas_observadas_muestra_leads_30d',cobertura:'parcial'};
}
function descriptorValido597(f){
 const m=f?._medicionMensajesCRM;if(!m||m.version!=='597.1'||m.fuente!=='GHL'||m.zona!=='Europe/Madrid'||m.definicion!=='salidas_observadas_muestra_leads_30d'||m.cobertura!=='parcial'||!idColor541(f?.cliente_id)||!idColor541(f?.sub_id))return null;
 const corte=Date.parse(m.corte_utc),a=Date.parse(m.desde+'T12:00:00Z'),b=Date.parse(m.hasta_exclusivo+'T12:00:00Z');
 if(!Number.isFinite(corte)||corte>Date.now()||new Date(corte).toISOString()!==m.corte_utc||!Number.isFinite(a)||!Number.isFinite(b)||new Date(a).toISOString().slice(0,10)!==m.desde||new Date(b).toISOString().slice(0,10)!==m.hasta_exclusivo||b-a!==30*864e5)return null;
 const p=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(corte)).map(x=>[x.type,x.value]));
 if(`${p.year}-${p.month}-${p.day}`!==m.hasta_exclusivo)return null;
 return JSON.stringify([m.corte_utc,m.desde,m.hasta_exclusivo,m.zona,m.definicion,m.cobertura]);
}
export function normalizarMensajesCRM597(f,fuente,hoy){
 const medicion=descriptorMensajes597(f,fuente,hoy),out={_medicionMensajesCRM:medicion};
 for(const canal of ['whatsapp','sms','correo']){
  const raw=f?.[canal]||{},en=medicion&&!fallo(raw)?conteo(raw.enviados):null,fallidos=medicion&&!fallo(raw)?conteo(raw.fallidos):null;
  out[canal]={...raw,enviados:en,fallidos,pct_fallo:en>0&&fallidos!==null&&fallidos<=en?fallidos/en*100:null};
 }
 return out;
}
export function parejaMensajesCRM597(f,canal){
 const m=descriptorValido597(f),x=['whatsapp','sms','correo'].includes(canal)?f?.[canal]:null;
 const enviados=m?conteo(x?.enviados):null,fallidos=m?conteo(x?.fallidos):null;
 const valida=enviados!==null&&fallidos!==null&&fallidos<=enviados;
 return {enviados,fallidos,valida,pct:valida&&enviados>0?fallidos/enviados*100:null,
  detalle:`${canal}: ${fallidos===null?'fallos sin dato':fallidos+' fallos observados'}; ${enviados===null?'envíos sin dato':enviados+' mensajes observados'}. ${m?'Muestra parcial de leads recibidos '+f._medicionMensajesCRM.desde+' → '+f._medicionMensajesCRM.hasta_exclusivo+' (fin excluido); lectura '+f._medicionMensajesCRM.corte_utc:'Fuente no compatible disponible'}. No es ventana de fecha de todos los mensajes; no acredita ausencia de envíos, lectura ni respuesta.`};
}
export function agregarMensajesCRM597(filas,canal){
 const total=Array.isArray(filas)?filas.length:0,ids=new Map();
 for(const f of filas||[])ids.set(f?.sub_id,(ids.get(f?.sub_id)||0)+1);
 const pares=(filas||[]).filter(f=>ids.get(f?.sub_id)===1&&descriptorValido597(f)&&parejaMensajesCRM597(f,canal).valida);
 const fuentes=new Set(pares.map(descriptorValido597));
 if(fuentes.size!==1)return {enviados:null,fallidos:null,pct:null,observadas:0,total,cobertura:'parcial'};
 const enviados=pares.reduce((s,f)=>s+f[canal].enviados,0),fallidos=pares.reduce((s,f)=>s+f[canal].fallidos,0);
 if(conteo(enviados)===null||conteo(fallidos)===null)return {enviados:null,fallidos:null,pct:null,observadas:0,total,cobertura:'parcial'};
 return {enviados,fallidos,pct:enviados>0?fallidos/enviados*100:null,observadas:pares.length,total,cobertura:'parcial'};
}
export function automaticosCRM597(f){
 const valid=descriptorValido597(f)&&!fallo(f?.velocidad),n=valid?conteo(f?.velocidad?.auto_5min):null,d=valid?conteo(f?.leads_30d):null;
 return {numerador:n,denominador:d,valida:n!==null&&d!==null&&d>0&&n<=d,
  detalle:`Automáticos ≤5 min: ${n===null?'sin dato':n+' casos observados'}; leads de la misma muestra30d: ${d===null?'sin dato':d}. ${valid?'Copia parcial al '+f._medicionMensajesCRM.corte_utc:'Fuente sin medición compatible'}. No es respuesta ni conversión; sin denominador positivo no hay fracción válida.`};
}
