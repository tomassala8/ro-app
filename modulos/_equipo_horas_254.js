import { serieHorasDiaria238 } from './_horas_diarias_238.js';
import { fechaControl227, mesControl227 } from './_control_periodos_227.js';

const numero254 = v => typeof v === 'number' && Number.isFinite(v) && v >= 0 ? v : null;
const mover254 = (f, n) => new Date(Date.parse(f + 'T00:00:00Z') + n * 864e5).toISOString().slice(0, 10);
export function rangoEquipo254(tipo, hoy, mes) {
  if (!fechaControl227(hoy)) return null;
  const hasta = mover254(hoy, -1);
  if (tipo === 'dia') return { tipo, desde: hasta, hasta };
  if (tipo === 'cinco') return { tipo, desde: mover254(hoy, -5), hasta };
  if (tipo === 'semana') {
    const inicio = mover254(hoy, -((new Date(hoy + 'T00:00:00Z').getUTCDay() + 6) % 7));
    return inicio <= hasta ? { tipo, desde: inicio, hasta } : { tipo, desde: inicio, hasta: inicio, sin_dia_cerrado: true };
  }
  if (tipo === 'mes' && mesControl227(mes) && mes <= hoy.slice(0, 7)) {
    const fin = mover254(new Date(Date.UTC(+mes.slice(0,4), +mes.slice(5), 1)).toISOString().slice(0,10), -1);
    return { tipo, mes, desde: mes + '-01', hasta: mes === hoy.slice(0,7) ? hasta : fin, sin_dia_cerrado: mes + '-01' > hasta };
  }
  return null;
}
export function filaEquipo254(persona, datos, rango) {
  const serie = serieHorasDiaria238(persona, datos?.hoy);
  const observadas = serie?.dias.filter(d => d.estado === 'observado') || [];
  const total5 = observadas.length ? observadas.reduce((s,d) => s + d.horas, 0) : null;
  let horas = null, dias = 0, ventana = false, fuente = serie?.fecha_fuente || datos?.fuentes?.horas?.hora || datos?.generado || null;
  if (rango?.tipo === 'mes' && !rango.sin_dia_cerrado) {
    const meses = (persona.meses || []).filter(m => m.mes === rango.mes);
    if (meses.length === 1 && !meses[0].antes_de_imputar && typeof fuente==='string' && /^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})?$/.test(fuente) && Number.isFinite(Date.parse(fuente.replace(' ','T'))) && fechaControl227(fuente.slice(0,10)) && fuente.slice(0,10) <= datos.hoy && fuente.slice(0,7) >= rango.mes) horas = numero254(meses[0].imputadas);
    // El productor legado rellena meses sin entradas con cero; no es una medición certificada.
    if (horas === 0) horas = null;
  } else if (rango && fechaControl227(rango.desde) && fechaControl227(rango.hasta) && rango.desde <= rango.hasta && !rango.sin_dia_cerrado && serie) {
    // No extrapolar desde cinco días ni rellenar huecos del export con cero.
    ventana = rango.desde >= serie.dias[0].fecha && rango.hasta <= serie.dias[4].fecha;
    if (ventana) {
      const encontrados = observadas.filter(d => d.fecha >= rango.desde && d.fecha <= rango.hasta);
      dias = encontrados.length;
      horas = encontrados.length ? encontrados.reduce((s,d) => s + d.horas, 0) : null;
    }
  }
  return { persona_id: persona.persona_id, nombre: persona.nombre || persona.alias || persona.persona_id,
    equipo: persona.equipo || '', serie, total5: numero254(total5), horas: numero254(horas), dias_observados: dias, fuente,
    ultima: observadas.at(-1)?.fecha || null, ventana_en_copia: ventana,
    capacidad: null, porcentaje: null, cobertura: 'parcial',
    detalle: rango?.tipo === 'mes' ? 'Agregado mensual de la copia; mes en Madrid. No es jornada confirmada.' : ventana ? 'Suma de registros observados; fechas en la zona de la persona. Los huecos siguen sin dato.' : 'Rango fuera de las cinco fechas tipadas disponibles; no se extrapola.' };
}
