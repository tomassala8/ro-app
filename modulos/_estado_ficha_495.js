// Índice histórico registrado: no es puntuación de resultados ni de cumplimiento.
export function indiceRegistrado495(verdad,cliente){
 const propio=verdad&&typeof verdad==='object'&&Object.prototype.hasOwnProperty.call(verdad,'salud');
 const valor=propio?verdad.salud:cliente?.salud;
 const valido=typeof valor==='number'&&Number.isFinite(valor)&&valor>=0&&valor<=100;
 const fuente=propio?'Verdad operativa · índice de copia':'Núcleo de clientes · índice de copia provisional';
 return {valor:valido?valor:null,etiqueta:valido?`Índice registrado ${valor}`:'Índice sin dato',tono:'gris',
 titulo:`${fuente}. Referencia provisional; no acredita desempeño, resultados Paid/CRM/SEO, cobertura ni cumplimiento. No se aplica una fórmula de salud confirmada.`};
}
export function tituloEstadoRegistrado495(verdad){
 const f=verdad&&typeof verdad==='object'?verdad:{};
 const fecha=[f.fecha,f.generado].find(x=>{
  if(typeof x!=='string'||!/^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})?)?$/.test(x))return false;
  const d=new Date(x.slice(0,10)+'T00:00:00Z'),clock=/[T ](\d{2}):(\d{2})(?::(\d{2}))?/.exec(x),offset=/[+-](\d{2}):(\d{2})$/.exec(x);
  return Number.isFinite(+d)&&d.toISOString().slice(0,10)===x.slice(0,10)&&(!clock||(+clock[1]<24&&+clock[2]<60&&+(clock[3]||0)<60))&&(!offset||(+offset[1]<=14&&+offset[2]<60&&(+offset[1]!==14||+offset[2]===0)))&&Number.isFinite(Date.parse(x));
 });
 return `Fuente: verdad operativa del cliente${fecha?` · corte registrado ${fecha}`:''}. Estado registrado de sus señales; no acredita resultados Paid/CRM/SEO ni cobertura completa.`;
}
