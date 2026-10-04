// Presentación de celdas263: no calcula métricas, concede permisos ni carga datos.
const valorValido396=x=>typeof x==='string'||(typeof x==='number'&&Number.isFinite(x));
const fecha396=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T00:00:00Z'))&&new Date(x+'T00:00:00Z').toISOString().slice(0,10)===x;
const mes396=x=>/^\d{4}-(?:0[1-9]|1[0-2])$/.test(x);
const informe396=Object.freeze({no_aplica:'No aplica',en_curso:'En curso',sin_tarea:'Sin tarea',hecho:'Tarea hecha'});
export const LEYENDA_KPIS_396=Object.freeze({account:'n/N: proyectos con registro, no porcentaje de cumplimiento. —: sin dato. Fuente, periodo y cobertura al pulsar.',proyecto:'Tickets y revisión: total · >48h. Decl.: registro del equipo, no ejecución verificada. —: sin dato. Fuente y periodo al pulsar.'});
export function celdaKpiCompacta396(c,{tabla,indice}={}) {
 if(!c||typeof c!=='object'||Array.isArray(c)||!valorValido396(c.valor)||!['account','proyecto'].includes(tabla)||!Number.isSafeInteger(indice)||indice<0||indice>7)return c;
 const original=String(c.valor);let valor=original==='Sin dato'?'—':original;
 if(tabla==='account'){
  // Cardinalidad de proyectos observados, no KPI aprobado.
  if(/^\d+\/\d+ registros$/.test(original))valor=original.slice(0,-' registros'.length);
 }else{
  if(indice===0){
   const m=/^(Envío|no_aplica|en_curso|sin_tarea|hecho) (\d{4}-\d{2})$/.exec(original)||/^(no_aplica|en_curso|sin_tarea|hecho) · (\d{4}-\d{2})$/.exec(original);
   if(m&&mes396(m[2]))valor=informe396[m[1]]||m[1];
   else if(Object.hasOwn(informe396,original))valor=informe396[original];
  }
  if(indice===1&&fecha396(original))valor=`${original.slice(8,10)}/${original.slice(5,7)}/${original.slice(2,4)}`;
  if(indice===2&&/^\d+ declarado(?:s)?$/.test(original))valor=original.replace(/ declarado(?:s)?$/,' decl.');
  if(indice===6&&/^(?:≥)?(?:\d+(?:[.,]\d+)?|<0[.,]1) h registradas$/.test(original))valor=original.slice(0,-' registradas'.length);
 }
 if(valor===original)return c;
 // Conserva todo el DTO y su evidencia, incluidas guardas y origen.
 const detalle=[typeof c.detalle==='string'?c.detalle:'',`Valor leído: ${original}.`].filter(Boolean).join(' ');
 return {...c,valor,detalle};
}
