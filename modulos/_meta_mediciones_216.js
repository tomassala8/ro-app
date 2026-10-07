// Meta: valores de la copia, no cualificación RO ni actividad fuera de ella.
const CAMPOS_META216 = ['impresiones', 'clics', 'clics_enlace', 'leads', 'gasto'];
export function numeroMeta216(v, campo) {
  return typeof v === 'number' && Number.isFinite(v) && v >= 0 &&
    (['gasto', 'frecuencia'].includes(campo) || Number.isSafeInteger(v)) ? v : null;
}
export function filaMeta216(x) {
  return Object.fromEntries([...CAMPOS_META216, 'alcance', 'frecuencia'].map(k => [k, numeroMeta216(x?.[k], k)]));
}
function diaMeta216(x) {
  if (typeof x !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(x)) return null;
  const d = Date.parse(x + 'T00:00:00Z');
  return Number.isFinite(d) && new Date(d).toISOString().slice(0, 10) === x ? d : null;
}
export function fuenteMeta216(f, p, hoy) {
  const hasta = diaMeta216(p?.hasta), desde = diaMeta216(p?.desde), ahora = diaMeta216(hoy);
  const leido = typeof f?.leido === 'string' && Number.isFinite(Date.parse(f.leido)) ? diaMeta216(f.leido.slice(0, 10)) : null;
  return hasta !== null && desde !== null && desde <= hasta && ahora !== null && leido !== null &&
    leido >= hasta && leido <= ahora && Array.isArray(f.errores) && f.errores.length === 0;
}
export function compararMeta216(f, p, hoy, exacto, anterior) {
  if (!exacto?.cuenta || !anterior?.cuenta || !p?.comp || p.comparar !== 'anterior' || !fuenteMeta216(f, p, hoy) || !fuenteMeta216(f, p.comp, hoy)) return false;
  const a = diaMeta216(p.desde), b = diaMeta216(p.hasta), c = diaMeta216(p.comp.desde), d = diaMeta216(p.comp.hasta), h = diaMeta216(hoy);
  return b < h && d < h && a - c === b - d && a - d === 86400000;
}
export function sumaCampanasMeta216(f, p, ids) {
  const out = {}, desde = diaMeta216(p?.desde), hasta = diaMeta216(p?.hasta);
  if (desde === null || hasta === null || desde > hasta) return out;
  for (const id of new Set([...Object.keys(f.serie || {}), ...Object.keys(f.gasto_serie || {})])) {
    if (ids && !ids.has(id)) continue;
    const s = f.serie?.[id] || {}, g = f.gasto_serie?.[id] || {};
    const dias = new Set([...Object.keys(s), ...Object.keys(g)].filter(d => { const n = diaMeta216(d); return n !== null && n >= desde && n <= hasta; }));
    if (!dias.size) continue;
    out[id] = Object.fromEntries(CAMPOS_META216.map((k, i) => {
      const valores = [...dias].map(d => numeroMeta216(k === 'gasto' ? g[d] : Array.isArray(s[d]) ? s[d][i] : null, k));
      return [k, valores.every(v => v !== null) ? valores.reduce((a, b) => a + b, 0) : null];
    }));
  }
  return out;
}
export function totalMeta216(filas) {
  const rows = Object.values(filas || {});
  return Object.fromEntries(CAMPOS_META216.map(k => {
    const v = rows.map(r => numeroMeta216(r?.[k], k));
    const sum = v.reduce((a, b) => a + (b ?? 0), 0);
    return [k, v.length && v.every(n => n !== null) ? numeroMeta216(sum, k) : null];
  }));
}
export function razonMeta216(x, numerador, denominador, comparable) {
  const a = numeroMeta216(x?.[numerador], numerador), b = numeroMeta216(x?.[denominador], denominador);
  return comparable && a !== null && b !== null && b > 0 ? a / b : null;
}
export function serieMeta216(f, p, campo) {
  const desde = diaMeta216(p?.desde), hasta = diaMeta216(p?.hasta);
  if (desde === null || hasta === null || desde > hasta || hasta - desde > 800 * 86400000) return [];
  const porDia = new Map(), idx = CAMPOS_META216.indexOf(campo);
  if (idx < 0) return [];
  for (const id of new Set([...Object.keys(f.serie || {}), ...Object.keys(f.gasto_serie || {})])) {
    const s = f.serie?.[id] || {}, g = f.gasto_serie?.[id] || {};
    for (const d of new Set([...Object.keys(s), ...Object.keys(g)])) {
      const t = diaMeta216(d);
      if (t === null || t < desde || t > hasta) continue;
      const v = numeroMeta216(campo === 'gasto' ? g[d] : Array.isArray(s[d]) ? s[d][idx] : null, campo);
      if (!porDia.has(d)) porDia.set(d, []);
      porDia.get(d).push(v);
    }
  }
  const out = [];
  for (let t = desde; t <= hasta; t += 86400000) {
    const d = new Date(t).toISOString().slice(0, 10), v = porDia.get(d);
    out.push({ x: d, y: v?.length && v.every(n => n !== null) ? numeroMeta216(v.reduce((a, b) => a + b, 0), campo) : null });
  }
  return out;
}
