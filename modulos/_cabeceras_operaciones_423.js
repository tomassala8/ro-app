//423 · etiquetas exactas de tablas propias. Sólo presentación: sin truncar ni reinterpretar datos.
const nombres423=Object.freeze({
 'Semáforo':'Estado','Sin responder':'Sin resp.','Última reunión':'Últ. reunión',
 'Llamadas (sep2026)':'Llam. sep26','Horas / presup.':'H. / presup.',
 'Empujes de Mili':'Emp. Mili','Pedidos semana':'Ped. sem.','Última declaración':'Últ. decl.',
 'Reuniones semana':'Reu. sem.','Seguimiento quincenal':'Seguim. 15d','Trafficker':'Traf.',
 'Última confirmada':'Últ. confirm.','Próxima revisión':'Próx. rev.','Estado / evidencia':'Estado / evid.',
 'Sin responder · +48h':'Sin resp. +48h','Semáforo · sin rellenar':'Estado pend.',
 'Semáforo · en rojo':'Estado rojo','Sin reunión · periodo de referencia':'Sin reu. (ref.)',
 'Sin correo · esta semana':'Sin correo sem.','Revisión · tareas +48h':'Rev. +48h',
 'Nuevos · fuera de plazo':'Nuevos f/plazo','Cerradas ayer':'Cerr. ayer',
 'Días con horas':'Días c/h','Última hora':'Últ. hora','Por qué llama la atención':'Motivo',
 'Tipo de tarea':'Tipo','Horas totales':'H. total','Quién crea':'Creador',
 'Fuegos directos':'Fuegos','Rompen el semanal':'Rupturas sem.','Semana pasada':'Sem. ant.',
 'Creadas semana pasada':'Creadas sem. ant.'
});
export function cabeceraOperaciones423(texto){
 return {breve:typeof texto==='string'&&Object.hasOwn(nombres423,texto)?nombres423[texto]:texto,completo:typeof texto==='string'?texto:null};
}
