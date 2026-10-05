// CTR total legado: clicks / impressions, distinto de CTR de enlace.
// No deriva una comparación vigente de porcentajes sin descriptor de ventanas.
export function ctrTotalPaid682(fila) {
  const valido = n => typeof n === 'number' && Number.isFinite(n) && n >= 0;
  const propio = k => fila != null && Object.prototype.hasOwnProperty.call(fila, k);
  const conteo = n => typeof n === 'number' && Number.isSafeInteger(n) && n >= 0;
  const baseValida = (!propio('impresiones_7d') || (conteo(fila.impresiones_7d) && fila.impresiones_7d > 0))
    && (!propio('clics_7d') || conteo(fila.clics_7d));
  const actual = baseValida && valido(fila?.ctr_7d) ? fila.ctr_7d : null;
  const previo = valido(fila?.ctr_previo) ? fila.ctr_previo : null;
  return { valor: actual, previo, titulo: 'CTR total registrado · clics totales / impresiones · 7 días; clics no únicos, puede superar 100 %. '
    + (previo === null ? 'Periodo anterior sin dato acreditado.' : `Periodo anterior: ${previo} % (referencia guardada).`)
    + ' Fechas, cobertura y comparabilidad pendientes; no acredita CTR de enlace.' };
}
export function celdaCtrTotalPaid682(h, num, fila) {
  const dato = ctrTotalPaid682(fila);
  return h('span', {title:dato.titulo, 'aria-label':dato.valor === null ? 'CTR total sin dato acreditado' : `CTR total registrado: ${dato.valor} por ciento. ${dato.titulo}`, class:'dim'},
    dato.valor === null ? '—' : `${num(dato.valor, 2)} %`);
}
