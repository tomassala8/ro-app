// Referencia literal del artifact: build/build.py603 y plantilla.html vScore682.
// No calcula una nota, modifica una celda ni interpreta cobertura como cumplimiento.
export const CRITERIOS_SCORE_408=Object.freeze([
 ['Informe mensual','Informe',15],['Reunión mensual','Reunión',20],['Correo semanal','Correo',10],
 ['Respuesta <48h','Respuesta',20],['Revisión <48h','Revisión',10],['Semáforo al día','Semáforo',10],
 ['Horas en lo pautado','Horas',5],['Nuevos en plazo','Nuevos',10]
].map(([criterio,cabecera,peso])=>Object.freeze({criterio,cabecera,peso})));
export const CABECERAS_SCORE_408=Object.freeze(CRITERIOS_SCORE_408.map(c=>c.cabecera));
export const BANDAS_SCORE_408=Object.freeze({verde_desde:80,ambar_desde:60,referencia:true,calculo_habilitado:false});
export function cabecerasScore408(){return CRITERIOS_SCORE_408.map(c=>({attrs:{title:c.criterio},elemento:c.cabecera}));}
export function renderReferenciaScore408(h,vigente=()=>true){
 const pesos=CRITERIOS_SCORE_408.map(c=>`${c.criterio}: ${c.peso}`).join(' · ');
 const d=h('details',{class:'refs263','data-referencia-score':'408'},
  h('summary',{style:{minHeight:'44px',display:'flex',alignItems:'center'}},'Referencia del Score'),
  h('p',{},`Pesos originales sobre 100: ${pesos}.`),
  h('p',{},'Bandas originales: verde desde 80; amarillo de 60 a 79; rojo por debajo de 60. Referencia del artifact, no resultado calculado en estas filas.'),
  h('p',{},'n/N cuenta proyectos con registro; no es porcentaje de cumplimiento. La Nota permanece — sin fuentes, periodos y denominadores acreditados. No se recalculan pesos ni se omiten desconocidos para fabricar una nota.'));
 d.addEventListener?.('toggle',()=>{if(d.isConnected)vigente();});
 return d;
}
