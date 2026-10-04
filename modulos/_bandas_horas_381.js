// Bandas del artifact804/756: referencias visuales, nunca jornada ni rendimiento.
const numero=x=>typeof x==='number'&&Number.isFinite(x)&&x>=0;
const dia=x=>{if(typeof x!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(x))return false;const d=new Date(x+'T00:00:00Z');return Number.isFinite(+d)&&d.toISOString().slice(0,10)===x;};
export function formatearBanda381(valor,tipo){
 if(!numero(valor)||!['diaria','porcentaje'].includes(tipo))return null;
 if(valor>0&&valor<0.1)return '<0,1';
 const umbrales=tipo==='diaria'?[6,8]:[60,90],cruza=digitos=>umbrales.find(x=>valor<x&&Math.round(valor*10**digitos)/10**digitos>=x);
 for(let digitos=1;digitos<=6;digitos++)if(!cruza(digitos))return new Intl.NumberFormat('es-ES',{maximumFractionDigits:digitos}).format(valor);
 return '<'+cruza(6);
}
function sello381(x,hoy){if(typeof x!=='string'||!dia(x.slice(0,10))||x.slice(0,10)>hoy)return false;const m=/^\d{4}-\d{2}-\d{2}[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?(Z|[+-](\d{2}):(\d{2}))?$/.exec(x);return !!m&&+m[1]<24&&+m[2]<60&&+(m[3]||0)<60&&(!m[4]||m[4]==='Z'||(+m[5]<=14&&+m[6]<60&&(+m[5]!==14||+m[6]===0)));}
export function bandaHoras381(valor,e){
 if(!numero(valor)||!e||e.observado!==true||e.fuente!=='ClickUp entradas'||e.cobertura!=='parcial'||!dia(e.hoy)||!sello381(e.fecha_fuente,e.hoy))return null;
 let v,bajo,alto;
 if(e.tipo==='diaria'){
  if(e.referencia_horas!==8||!dia(e.fecha)||e.fecha>e.hoy||e.fecha>e.fecha_fuente.slice(0,10))return null;
  v=valor;bajo=6;alto=8;
 }else if(e.tipo==='porcentaje'){
  if(!numero(e.referencia_horas)||e.referencia_horas<=0||!Number.isSafeInteger(e.laborables)||e.laborables<=0||e.referencia_horas!==e.laborables*8||!dia(e.desde)||!dia(e.hasta)||e.desde>e.hasta)return null;
  v=valor/e.referencia_horas*100;if(!numero(v))return null;bajo=60;alto=90;
 }else return null;
 const nivel=v>=alto?'alta':v>=bajo?'media':'baja',color=nivel==='alta'?'verde':nivel==='media'?'ambar':'rojo';
 return {nivel,color,etiqueta:`Ref. ${nivel}`,valor:v,clase:`banda381-${color}`,detalle:`Referencia visual del artifact: ${e.tipo==='diaria'?'menos de6h /6–menos de8h /8h o más':'menos de60% /60–menos de90% /90% o más;8h × '+e.laborables+' laborables'}. Lectura ${e.fecha_fuente}; copia parcial. No acredita jornada, ausencia, cumplimiento ni rendimiento.`};
}
export const cssBandas381=`.op-equipo262 .oe-ref.oe-observado[class*="banda381-"]{display:inline-flex;flex-direction:column;align-items:center;justify-content:center;min-width:46px;box-sizing:border-box;gap:2px;line-height:1.2;border-bottom:0;padding:4px 6px}.op-equipo262 .banda381-rojo{background:#fde8e9;color:#a7444e}.op-equipo262 .banda381-ambar{background:#fff2cc;color:#805500}.op-equipo262 .banda381-verde{background:#e3f5e8;color:#237648}.op-equipo262 .banda381-label{display:block;font-size:10px;line-height:1.15;color:inherit;white-space:nowrap}.op-equipo262 .banda381-leyenda{display:flex;flex-wrap:wrap;gap:5px 10px;font-size:11px;margin:0;padding:7px 18px;color:#777d9b}.op-equipo262 .banda381-leyenda span{border-radius:4px;padding:2px 5px}`;
export function leyendaHoras381(h,tipo){const labels=tipo==='diaria'?['<6 h','6–<8 h','≥8 h']:['<60 %','60–<90 %','≥90 %'];return h('p',{class:'banda381-leyenda'},'Referencia artifact:',labels.map((x,i)=>h('span',{class:['banda381-rojo','banda381-ambar','banda381-verde'][i]},x)),h('span',{},'Sin dato: gris · no jornada ni cumplimiento'));}
