import { semanticaMeta285 } from './_meta_semantica_285.js';
// DTOs ya recortados servidor. No solicita fuentes ni deduce permisos/IDs por nombre.
const numero=n=>typeof n==='number'&&Number.isFinite(n)&&n>=0;
const fecha=d=>typeof d==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(d)&&Number.isFinite(Date.parse(d+'T00:00:00Z'))&&new Date(d+'T00:00:00Z').toISOString().slice(0,10)===d;
const mes=m=>typeof m==='string'&&/^\d{4}-(0[1-9]|1[0-2])$/.test(m);
function unica(rows,id){const rs=(Array.isArray(rows)?rows:[]).filter(r=>r?.cliente_id===id);return rs.length===1?rs[0]:null;}
export function muestraLeads30Tarjeta277(c,C,{cliente,hoy}={}){
 if(c?.cuenta_meta?.error||c?.cuenta_meta?.errores?.length||c?.errores_lectura?.length)return null;
 const hasta=C?.ventanas?.serie?.[1];if(!fecha(hasta)||!fecha(C?.datos_hasta)||hasta!==C.datos_hasta)return null;
 const ini=new Date(hasta+'T00:00:00Z');ini.setUTCDate(ini.getUTCDate()-29);const desde=ini.toISOString().slice(0,10);
 if(!Array.isArray(c?.serie))return null;
 const seen=new Set(),filas=[];let suma=0,obs=0;
 for(const r of c.serie){
  if(!fecha(r?.d)||r.d<desde||r.d>hasta)continue;
  if(seen.has(r.d))return null;seen.add(r.d);
  filas.push(r);
  if(Number.isInteger(r.leads_meta)&&r.leads_meta>0){suma+=r.leads_meta;obs++;}
 }
 if(!Number.isSafeInteger(suma))return null;
 const semantica=semanticaMeta285(filas,{...cliente,tienda_online:cliente?.tienda_online===true||c?.tienda_online===true},hoy);
 return {valor:obs?suma:null,desde,hasta,cobertura:'parcial',dias_presentes:seen.size,fuente:'Meta · serie de Captación',...semantica};
}
export function metricasTarjetas277(rows,ctx,{captacion=null,produccion=null,dinero=null}={}){
 const base=Array.isArray(rows)?rows:[],cs=Array.isArray(ctx?.clientesVisibles)?ctx.clientesVisibles:[],cu=new Map();for(const c of cs)cu.set(c?.id,(cu.get(c?.id)||0)+1);
 const scope=new Set(cs.filter(c=>typeof c?.id==='string'&&cu.get(c.id)===1&&c.activo_confirmado===true&&c.detalle===true&&ctx.ver?.({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true).map(c=>c.id));
 const counts=new Map();for(const r of base)counts.set(r?.id,(counts.get(r?.id)||0)+1);
 return base.filter(r=>scope.has(r?.id)&&counts.get(r.id)===1).map(r=>{
  const leads=fecha(ctx.hoy)&&fecha(captacion?.datos_hasta)&&captacion.datos_hasta<=ctx.hoy&&ctx.veModulo?.('captacion')===true?muestraLeads30Tarjeta277(unica(captacion?.clientes,r.id),captacion,{cliente:cs.find(c=>c.id===r.id),hoy:ctx.hoy}):null;
  const p=ctx.veModulo?.('produccion')===true?unica(produccion?.proyectos,r.id):null,m=p?.horas_medicion;
  const fh=typeof m?.fecha==='string'?m.fecha.slice(0,10):null;
  const measured=m?.estado==='medido'&&m.fuente==='horas'&&m.cobertura==='parcial'&&m.alcance==='entradas_leidas'&&mes(m.periodo)&&fecha(fh)&&fecha(produccion?.hoy)&&fecha(ctx.hoy)&&produccion.hoy<=ctx.hoy&&fh<=produccion.hoy&&fh.slice(0,7)===m.periodo&&produccion.hoy.slice(0,7)===m.periodo&&numero(p?.horas_mes);
  const horas=measured?{valor:p.horas_mes,periodo:m.periodo,fecha:m.fecha,cobertura:'parcial',fuente:'ClickUp · entradas de horas leídas'}:null;
  const d=ctx.veModulo?.('dinero-cliente')===true&&ctx.ver?.({tipo:'horas_pautadas',cliente_id:r.id})?.ok===true?unica(dinero?.clientes,r.id):null;
  const pauta=horas&&mes(dinero?.mes_cuota)&&dinero.mes_cuota===horas.periodo&&numero(d?.cuota_horas?.pautadas)&&d.cuota_horas.pautadas>0?d.cuota_horas.pautadas:null;
  const pct=horas&&pauta!==null?horas.valor/pauta*100:null;
  return {...r,leads30:leads?.eventos_lead_acreditados===true?leads.valor:null,leads30Medicion:leads?.eventos_lead_acreditados===true?leads:null,resultadosMeta30:leads?.valor??null,resultadosMeta30Medicion:leads,horasObservadas:horas?.valor??null,horasMedicion:horas,horasPct:Number.isFinite(pct)?pct:null,horasPauta:pauta,horasRatioReferencia:!!horas&&pauta!==null,horasDetalle:horas?`${horas.periodo} · ${horas.fecha} · copia parcial${pauta!==null?' · pauta derivada de cuota/tarifa del mismo mes; referencia original, no presupuesto contractual':''}`:'Sin medición tipada compatible autorizada'};
 });
}
