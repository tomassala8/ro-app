// Ventanas de la copia. No deduce calendario, jornada ni capacidad.
export function fechaControl227(v) {
  if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(v)) return null;
  const d = new Date(`${v}T00:00:00Z`);
  return Number.isFinite(+d) && d.toISOString().slice(0,10) === v ? v : null;
}
export function mesControl227(v) {
  return typeof v === 'string' && /^\d{4}-(0[1-9]|1[0-2])$/.test(v) ? v : null;
}
export function ventanasHoras227(datos, mes) {
  const fecha = fechaControl227(datos?.hoy) || fechaControl227(datos?.ayer);
  return { mes: mesControl227(mes), corte: fecha,
    dia: 'Último día de la copia', semana: 'Semana de la copia',
    mes_titulo: `Mes ${mesControl227(mes) || 'sin confirmar'}`,
    detalle: `Día: fecha individual en cada fila. Semana: ventana del productor, inicio/fin individuales no publicados; corte global ${fecha || 'sin fecha confirmada'}, puede variar por zona horaria. Mes: ${mesControl227(mes) || 'sin confirmar'}; cambiarlo no cambia las otras dos ventanas. No son horas disponibles ni jornada confirmada.` };
}
