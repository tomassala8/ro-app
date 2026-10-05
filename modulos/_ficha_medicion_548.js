// Privado de ficha: copia observada, ventana natural y referencia separadas.
import { medirCplPaid } from './_paid_mediciones.js';
const numero548 = v => typeof v === 'number' && Number.isFinite(v) && v >= 0 ? v : null;
const conteo548 = v => Number.isSafeInteger(v) && v >= 0 ? v : null;
const dia548 = v => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v) && Number.isFinite(Date.parse(v+'T12:00:00Z')) && new Date(v+'T12:00:00Z').toISOString().slice(0,10) === v ? v : null;
const lectura548 = v => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}(?:[T ](?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?)?$/.test(v) && Number.isFinite(Date.parse(v.length===10?v+'T12:00:00Z':v.replace(' ','T'))) ? dia548(v.slice(0,10)) : null;
const mover548 = (d,n) => new Date(Date.parse(d+'T12:00:00Z')+n*864e5).toISOString().slice(0,10);
const lead548 = m => m?.version === '220.1' && m.fuente === 'meta_insights' && m.nivel === 'account' && m.periodo_valido === true && m.cohorte === 'resultados_meta_sin_union_crm_ni_cualificacion_ro' && ['lead','onsite_conversion.lead_grouped','offsite_conversion.fb_pixel_lead','onsite_web_lead'].includes(m.tipo_lead) && m.campos_observados?.includes('leads');
export function fichaMeta548(md,n,inversion,hoy,objetivo={},fuente={}) {
 const vacio={leads:null,leadsAnt:null,gasto:null,gastoAnt:null,cpl:null,cplAnt:null,etiqueta:'Resultados Meta',prefijo:'',comp:'Sin ventana cerrada compatible',estado:'gris',nota:'Sin objetivo confirmado no se evalúa CPL ni se aplica techo general.',puntos:[]};
 if(!dia548(hoy)||![7,30].includes(n)||fuente.error||fuente.errores?.length||['rota','error','con_errores'].includes(fuente.estado))return vacio;
 const corte=Object.hasOwn(md,'datos_hasta')?dia548(md.datos_hasta):mover548(hoy,-1);
 if(!corte||corte>=hoy)return vacio;
 const desde=mover548(corte,1-n),serie=Array.isArray(md.serie)?md.serie:[];
 function medir(ini,fin){let suma=0,gasto=0,dias=0,gDias=0,tipado=true,tipo=null,cuenta=null,moneda=null;const puntos=[];
  for(let d=ini;d<=fin;d=mover548(d,1)){
   const filas=serie.filter(r=>r?.d===d),r=filas.length===1?filas[0]:null;
   const leida=r?.medicion?.fecha_lectura,fecha=leida?lectura548(leida):null;
   const ok=r&&!r.error&&!r.errores?.length&&(!leida||fecha&&fecha>=d&&fecha<=hoy);
   const l=ok?conteo548(Object.hasOwn(r,'leads_meta')?r.leads_meta:r.meta?.[1]):null,g=ok?numero548(Object.hasOwn(r,'gasto_meta')?r.gasto_meta:r.meta?.[0]):null,m=r?.medicion;
   puntos.push({d,meta:[g,l]});
   if(l!==null){suma+=l;dias++;}if(g!==null){gasto+=g;gDias++;}
   if(l===null||!lead548(m)||m.desde!==d||m.hasta!==d||!fecha||typeof m.cuenta_id!=='string'||! /^[1-9][0-9]{0,29}$/.test(m.cuenta_id)||! /^[A-Z]{3}$/.test(m.moneda||'')||tipo!==null&&tipo!==m.tipo_lead||cuenta!==null&&cuenta!==m.cuenta_id||moneda!==null&&moneda!==m.moneda)tipado=false;
   if(m){tipo=m.tipo_lead;cuenta=m.cuenta_id;moneda=m.moneda;}
  }
  return {valor:Number.isSafeInteger(suma)&&(dias===n||suma>0)?suma:null,gasto:Number.isFinite(gasto)&&(gDias===n||gasto>0)?gasto:null,dias,gDias,completa:dias===n,tipado,tipo,cuenta,moneda,puntos};
 }
 const a=medir(desde,corte),b=medir(mover548(desde,-n),mover548(desde,-1));
 const compatible=a.tipado&&b.tipado&&a.tipo===b.tipo&&a.cuenta===b.cuenta&&a.moneda===b.moneda;
 const cpl=a.tipado&&a.completa&&a.gDias===n&&a.valor>0&&inversion?a.gasto/a.valor:null;
 const ref=numero548(md.cpl?.[n===7?'7d':'30d']);
 const m=a.tipado?{...serie.find(r=>r.d===desde)?.medicion,desde,hasta:corte,campos_observados:['gasto','leads']}:null;
 const refBase=n+'d',paid=medirCplPaid({dinero:inversion,gasto:{[refBase]:a.gasto},leads:{[refBase]:a.valor},cpl_resumen:{ref_base:refBase,ref:cpl===null?null:Math.round(cpl*100)/100,fiable:a.completa&&a.gDias===n,medicion:m},objetivo:{...objetivo,cpl_objetivo:objetivo.coste_lead}}, {datos_hasta:corte,ventanas:{[refBase]:[desde,corte]}},hoy);
 return {...vacio,leads:a.valor,leadsAnt:compatible&&b.valor>0?b.valor:null,gasto:inversion?a.gasto:null,etiqueta:a.tipado?'Leads Meta':'Resultados Meta',prefijo:!a.completa&&a.valor>0?'≥':'',gastoPrefijo:a.gDias<n&&a.gasto>0?'≥':'',comp:`${desde} → ${corte} · ${a.dias}/${n} días observados · copia parcial${conteo548(md.leads?.mes_anterior)!==null?' · Mes anterior: '+md.leads.mes_anterior+' resultados Meta registrados (ventana/evento por acreditar)':''}`,cpl:cpl??ref,cplReferencia:cpl===null,estado:paid.estado,nota:paid.nota,puntos:a.puntos};
}
export function fichaHoras548(f,anterior,hoy){
 const d=f?.datos||{},v=numero548(d[anterior?'horas_mes_ant':'horas_mes']),m=d[anterior?'horas_mes_ant_medicion':'horas_mes_medicion'];
 const periodo=typeof m?.periodo==='string'&&/^\d{4}-(0[1-9]|1[0-2])$/.test(m.periodo)&&m.periodo<=hoy?.slice(0,7)?m.periodo:null;
 const observado=periodo&&m.estado==='medido'&&m.fuente==='horas'&&lectura548(m.fecha)&&m.fecha===f.hora&&m.fecha.slice(0,10)<=hoy&&m.fecha.slice(0,7)>=periodo;
 const p=d.pauta_medicion,ref=numero548(d.horas_presup_mes);
 const rango=dia548(m?.desde)&&dia548(m?.hasta)&&m.desde<=m.hasta&&m.hasta<hoy&&m.desde.slice(0,7)===periodo&&m.hasta.slice(0,7)===periodo&&p?.desde===m.desde&&p?.hasta===m.hasta;
 const compatible=observado&&rango&&p?.origen==='referencia_economica'&&p.presupuesto_confirmado===false&&p.periodo===periodo&&p.definicion===m.definicion&&typeof m.definicion==='string'&&m.definicion.length>0&&lectura548(p.fecha)&&p.fecha.slice(0,10)<=hoy&&ref>0;
 const ratio=compatible&&v!==null?v/ref*100:null;
 return {valor:v===0&&!observado?null:v,etiqueta:`Horas · ${observado?periodo:anterior?'copia mes anterior':'copia mes en curso'}`,referencia:ref,ratio,estado:ratio>130?'ambar':'gris',nota:`${observado?'Registro observado; cobertura parcial.':'Copia sin descriptor de mes confirmado; cobertura parcial.'} ${ref!==null?`${ref} h de referencia histórica${p?.periodo?' · '+p.periodo:''}.`:'Referencia histórica sin dato.'} ${ratio!==null?`≥${ratio.toFixed(1)} % de referencia económica; no presupuesto contractual.`:'Sin ratio: período y definición compatibles por acreditar.'}`};
}
