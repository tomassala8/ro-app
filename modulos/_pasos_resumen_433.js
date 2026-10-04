//433 · sólo observaciones del modelo274; no nueva fuente, progreso ni cumplimiento.
const DEFINICIONES433=[
 {indice:9,unidad:'señales de registros de horas',alcance:'Copia autorizada; revisar no equivale a mala imputación.'},
 {indice:0,unidad:'clientes con correos de más de 48 h',alcance:'Copia de clientes medidos; puede incluir histórico, no urgencias confirmadas hoy.'},
 {indice:3,unidad:'revisiones de más de 48 h',alcance:'Revisiones observadas en copia parcial; no todos los proyectos ni entregas aceptadas.'},
 {indice:null,unidad:'urgencias abiertas',alcance:'Los clientes en rojo y sus planes no acreditan Fuegos urgentes.'},
 {indice:null,unidad:'contactos y reuniones',alcance:'No existe aquí un contador compatible de contacto o reunión ejecutados; el semáforo no los sustituye.'},
 {indice:6,unidad:'señales de plazo en altas',alcance:'Estados de plazo de la copia; no cumplimiento de contrato ni hitos aceptados.',patron:/^(\d+) señales$/},
 {indice:10,unidad:'decisiones sin respuesta registrada',alcance:'Decisiones presentes en lista parcial; no totalidad del historial ni cierre ejecutado.'},
];
export function badgesPasos433(indicadores,urgencias=null){
 return DEFINICIONES433.map((d,i)=>{
  if(i===3&&urgencias?.disponible===true&&Array.isArray(urgencias.filas)&&urgencias.filas.length>0&&typeof urgencias.hasta==='string'&&Number.isFinite(Date.parse(urgencias.hasta))){const fecha=new Intl.DateTimeFormat('es-ES',{timeZone:'Europe/Madrid',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}).format(new Date(urgencias.hasta));return {valor:String(urgencias.filas.length),estado:'gris',detalle:`${urgencias.filas.length} urgencias abiertas observadas en copia parcial. Estado leído hasta ${fecha} Madrid (${urgencias.hasta}). Fuegos actuales por confirmar; sin verificación conjunta de prioridad y estado.`};}
  const x=d.indice===null?null:(Array.isArray(indicadores)?indicadores[d.indice]:null);
  const match=typeof x?.valor==='string'?(d.patron||/^(\d+)$/).exec(x.valor):null;
  const valor=match?Number(match[1]):null;
  const valido=Number.isSafeInteger(valor)&&valor>=0&&typeof x?.detalle==='string'&&x.detalle.trim().length>0;
  return {valor:valido?String(valor):'—',estado:valido&&['rojo','ambar'].includes(x.estado)?x.estado:'gris',
   detalle:`${valido?valor+' ':''}${d.unidad}. ${d.alcance}${valido?' '+x.detalle:' Sin observación compatible en este resumen.'}`};
 });
}
