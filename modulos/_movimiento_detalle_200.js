import { identidadMovimiento192 } from './_movimiento_tablero_192.js';
// Adaptador del detalle al contrato 192: no cambia selección del tablero ni la copia.
export function contextoMovimientoDetalle200(E,t) {
  const identidad=identidadMovimiento192(E.ctx);
  const firma=r=>JSON.stringify([r.cli??null,r.lista_id??null,r.estado??null,r.tipo_estado??null]);
  const filas=()=>Array.isArray(E.D?.tareas)?E.D.tareas.filter(r=>r?.id===t.id):[];
  const inicial=filas(),f=firma(t);
  const coherente=inicial.length>0 && inicial.some(r=>r.persona_id===t.persona_id) && inicial.every(r=>firma(r)===f);
  const vigente=()=>coherente && (!E.vigente||E.vigente()) && identidadMovimiento192(E.ctx)===identidad && filas().length>0 && filas().some(r=>r.persona_id===t.persona_id) && filas().every(r=>firma(r)===f);
  const scope=Object.create(E);scope.tableroLista=t.lista_id;scope.vigente=vigente;
  return {E:scope,t:{...t,coherente},vigente};
}
