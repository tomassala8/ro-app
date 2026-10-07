// Fechas puras RO: textos sin zona son Europe/Madrid; fechas civiles no son instantes.
// No usa el huso del navegador ni un offset fijo. Sin datos válidos devuelve null.
export const ZONA_FECHAS_RO = 'Europe/Madrid';
const formatos = new Map();
export function zonaFechaRO(zona) {
  try { new Intl.DateTimeFormat('en', { timeZone: zona || ZONA_FECHAS_RO }); return zona || ZONA_FECHAS_RO; }
  catch { return ZONA_FECHAS_RO; }
}
function formato(zona) {
  if (!formatos.has(zona)) formatos.set(zona, new Intl.DateTimeFormat('en-GB', {
    timeZone: zona, year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23',
  }));
  return formatos.get(zona);
}
function partes(ms, zona) {
  return Object.fromEntries(formato(zona).formatToParts(new Date(ms))
    .filter(p => p.type !== 'literal').map(p => [p.type, Number(p.value)]));
}
function utc(a, m, d, h = 0, min = 0, s = 0, ms = 0) {
  const fecha = new Date(0); fecha.setUTCFullYear(a, m - 1, d); fecha.setUTCHours(h, min, s, ms);
  return +fecha;
}
const pad = n => String(n).padStart(2, '0');
const civil = p => `${String(p.year).padStart(4, '0')}-${pad(p.month)}-${pad(p.day)}`;
function leer(t) {
  if (typeof t !== 'string') return null;
  const s = t.trim();
  const m = /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,9}))?)?(Z|[+-]\d{2}:?\d{2})?)?$/.exec(s)
    || /^(\d{2})-(\d{2})-(\d{4})(?:[ T](\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,9}))?)?)?$/.exec(s)?.map((v, i, a) => i === 1 ? a[3] : i === 3 ? a[1] : v);
  if (!m) return null;
  const p = { year: +m[1], month: +m[2], day: +m[3], hour: +(m[4] || 0), minute: +(m[5] || 0), second: +(m[6] || 0), ms: +((m[7] || '').padEnd(3, '0').slice(0, 3)), zona: m[8] || null, conHora: m[4] !== undefined };
  if (p.year < 1 || p.year > 9999 || p.month < 1 || p.month > 12 || p.day < 1 || p.hour > 23 || p.minute > 59 || p.second > 59) return null;
  const d = new Date(utc(p.year, p.month, p.day));
  if (d.getUTCFullYear() !== p.year || d.getUTCMonth() + 1 !== p.month || d.getUTCDate() !== p.day) return null;
  return p;
}
/** Fecha civil válida, sin inferir una hora; no recorta cadenas inválidas. */
export function fechaCivilRO(t) { const p = leer(t); return p && !p.zona ? civil(p) : null; }
/** Date|null. Sin zona = Madrid. Sólo-fecha, hueco DST y hora repetida = null.
 * En la hora repetida, el dato debe traer +02:00/+01:00 para identificar el instante.
 * Fracciones submilisegundo se truncan a la precisión de Date, no se conservan para auditoría.
 */
export function instanteRO(t) {
  if (t instanceof Date) return Number.isFinite(+t) ? new Date(+t) : null;
  const p = leer(t); if (!p?.conHora) return null;
  const base = utc(p.year, p.month, p.day, p.hour, p.minute, p.second, p.ms);
  if (p.zona) {
    let offset = 0;
    if (p.zona !== 'Z') {
      const m = /^([+-])(\d{2}):?(\d{2})$/.exec(p.zona);
      if (+m[2] > 23 || +m[3] > 59) return null;
      offset = (m[1] === '+' ? 1 : -1) * (+m[2] * 60 + +m[3]) * 60000;
    }
    const d = new Date(base - offset); return Number.isFinite(+d) ? d : null;
  }
  // Descubrir offsets IANA alrededor de la fecha y comprobar cada candidato
  // por round-trip. Detecta 0 (hueco), 1 (normal) o 2 (hora repetida) instantes.
  const offsets = new Set();
  for (const h of [-48, -24, 0, 24, 48]) {
    const ms = base + h * 3600000, q = partes(ms, ZONA_FECHAS_RO);
    offsets.add(utc(q.year, q.month, q.day, q.hour, q.minute, q.second) - Math.floor(ms / 1000) * 1000);
  }
  const candidatos = [...offsets].map(o => base - o).filter(ms => {
    const q = partes(ms, ZONA_FECHAS_RO);
    return ['year', 'month', 'day', 'hour', 'minute', 'second'].every(k => q[k] === p[k]);
  });
  return candidatos.length === 1 ? new Date(candidatos[0]) : null;
}
/** Día de negocio: civil sin zona se conserva; instante explícito se convierte a zona. */
export function diaRO(t, zona = ZONA_FECHAS_RO) {
  if (!(t instanceof Date)) { const p = leer(t); if (p && !p.zona) return civil(p); }
  const d = instanteRO(t); return d ? civil(partes(+d, zonaFechaRO(zona))) : null;
}
export function horaRO(t, zona = ZONA_FECHAS_RO) {
  const d = instanteRO(t); if (!d) return '';
  const p = partes(+d, zonaFechaRO(zona)); return `${pad(p.hour)}:${pad(p.minute)}`;
}
/** Duración real (incluye DST), negativa si t está en el futuro. Reloj inyectable. */
export function horasDesdeRO(t, ahora = new Date()) {
  const d = instanteRO(t), a = instanteRO(ahora);
  return d && a ? (+a - +d) / 3600000 : null;
}
export function horasHastaRO(t, ahora = new Date()) {
  const n = horasDesdeRO(t, ahora); return n === null ? null : -n;
}
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
export function mesRO(t, zona = ZONA_FECHAS_RO) {
  if (typeof t === 'string' && /^\d{4}-\d{2}$/.test(t.trim())) { const m = t.trim(); return fechaCivilRO(`${m}-01`) ? m : null; }
  return diaRO(t, zona)?.slice(0, 7) || null;
}
export function nombreMesRO(t, zona = ZONA_FECHAS_RO) { const m = mesRO(t, zona); return m ? MESES[+m.slice(5) - 1] : ''; }
