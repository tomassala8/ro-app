// modulos/dinero_comun.js · piezas compartidas por M18 «Dinero por cliente», M19 «Finanzas» y el bloque de anuncios de M16 (E10).
// No es un módulo (no está en indice.js). Desde N6 (auditoría 30) no trae hoja de estilos: barrasMes() dibuja con grafico(),
// numeroGrande() usa cifraPrincipal() y todo lo demás son clases de estilos.css. Nada de datos: todo llega por ctx.datosModulo().

import { h, icono, fmt, frescura, grafico, cifraPrincipal, vacioLinea, tile, tiles, tablaApilable, barraProgreso } from '../componentes.js';

/** Ronda N6 (auditoría 30): sin hoja de estilos propia. Se queda vacía por compatibilidad con quien la llame. */
export function estilos() {}

const MESES_CORTOS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
export const mesCorto = m => { const [y, mm] = String(m).split('-'); return `${MESES_CORTOS[Number(mm) - 1] || mm}${mm === '01' || mm === '12' ? ' ' + y.slice(2) : ''}`; };
export const mesLargo = m => { const [y, mm] = String(m).split('-'); return `${['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'][Number(mm) - 1]} de ${y}`; };

/**
 * barrasMes({ meses: [{ m, valores: [v0, v1…], titulo }], nombres: ['Cuota', …], formato, etiqueta, total: 'Total' | null })
 *   Serie mensual con el motor común grafico() (letra de 12 px, marcas redondas, burbuja al pasar el ratón).
 *   Un valor por mes → barras (las negativas en rojo). Varios (apiladas: cuota + puntual…) → barras con el total y una
 *   línea por parte. Con total: null (altas y bajas) → solo líneas, una por parte.
 */
export function barrasMes(o) {
  const meses = o.meses || [];
  if (meses.length < 2) return vacioLinea('Sin historia suficiente: hacen falta al menos dos meses.', { icono: 'grafico' });
  const x = meses.map(z => z.m);
  const f = o.formato || (v => fmt.num(v));
  const largo = meses.length > 12;
  const fx = m => { const [y, mm] = String(m).split('-'); const c = MESES_CORTOS[Number(mm) - 1] || mm; return largo ? `${c} ${y.slice(2)}` : c; };
  const partes = Math.max(...meses.map(z => z.valores.length));
  const nombres = o.nombres || (o.leyenda || []).map(l => l[1]);
  if (partes === 1) {
    return grafico({ titulo: o.titulo, x, barras: { nombre: nombres[0] || o.etiqueta || '', y: meses.map(z => z.valores[0] ?? null), formato: f }, formato: f, formatoX: fx, alto: o.alto || 200 });
  }
  const series = Array.from({ length: Math.min(partes, 4) }, (_, j) => ({ nombre: nombres[j] || `Parte ${j + 1}`, y: meses.map(z => (z.valores[j] === undefined ? null : z.valores[j])) }));
  const barras = o.total === null ? null : { nombre: o.total || 'Total', y: meses.map(z => z.valores.reduce((a, v) => a + (v || 0), 0)), formato: f };
  return grafico({ titulo: o.titulo, x, series, barras, formato: f, formatoX: fx, alto: o.alto || 200, leyenda: true });
}

/** numeroGrande({ icono, etiqueta, valor, unidad, estado, texto, lineas: [[texto, valor]], extra }) · la cifra que manda, en un panel
 *  con cifraPrincipal() (32 px) y el desglose en una lista de definición. estado: lo decide colorCifra() en quien llama. */
export function numeroGrande(o) {
  const desglose = [
    o.lineas?.length ? (o.secundaria
      ? h('div', { class: 'pila' }, o.lineas.map(([tx, v]) => h('p', { class: 'fila' }, h('span', { class: 'sub' }, tx), h('b', {}, v))))
      : h('dl', { class: 'dl' }, o.lineas.map(([tx, v]) => [h('dt', {}, tx), h('dd', {}, h('b', {}, v))]))) : null,
    o.extra || null];
  // secundaria: true → la cifra va en una tarjeta (24 px): solo hay UNA cifra a 32 px por pantalla
  if (o.secundaria) {
    return h('div', { class: 'pila', 'aria-label': o.etiqueta },
      tiles([tile({ icono: o.icono || 'euro', etiqueta: o.etiqueta, valor: o.valor, unidad: o.unidad, estado: o.colorValor ? o.estado || '' : '', contexto: o.texto })]),
      h('section', { class: 'panel' }, h('div', { class: 'cuerpo pila' }, desglose)));
  }
  return h('section', { class: 'panel', 'aria-label': o.etiqueta },
    h('div', { class: 'cuerpo pila' },
      cifraPrincipal({ etiqueta: o.etiqueta, valor: o.valor ?? '—', unidad: o.unidad, estado: o.colorValor ? o.estado || '' : '', comparacion: o.texto }),
      desglose));
}

/** filasConBarra([{ etiqueta, valor, actual, max, estado }], { titulos }) · lista de importes con su barra (tramos de impagos,
 *  coste por área): tabla común con la cifra a la derecha, que en el móvil se apila. */
export function filasConBarra(items, { titulos = ['Qué', '', 'Importe'] } = {}) {
  return tablaApilable({ filas: items, columnas: [
    { clave: 'etiqueta', titulo: titulos[0], principal: true },
    { clave: 'barra', titulo: titulos[1], celda: x => barraProgreso({ valor: x.actual, max: x.max, estado: x.estado || null, etiqueta: `${x.etiqueta}: ${x.valor}` }) },
    { clave: 'valor', titulo: titulos[2], num: true }] });
}

/** quinceFilas(caja) · en las tablas largas, 15 filas a la vista y «Ver las N filas» (guía 3.8). Se vuelve a aplicar si la tabla
 *  se repinta (ordenar, buscar) mientras no se haya pedido verlas todas. */
export function quinceFilas(caja, n = 15) {
  let todas = false;
  const aplicar = () => {
    const filas = [...caja.querySelectorAll('tbody > tr')];
    caja.querySelector(':scope > .tabla-mas')?.remove();
    filas.forEach((tr, i) => { tr.hidden = !todas && i >= n; });
    if (!todas && filas.length > n) {
      caja.append(h('div', { class: 'tabla-mas' }, h('button', { type: 'button', class: 'bt', on: { click: () => { todas = true; aplicar(); } } }, `Ver las ${fmt.num(filas.length)} filas`)));
    }
  };
  aplicar();
  const tb = caja.querySelector('tbody');
  if (tb && typeof MutationObserver === 'function') new MutationObserver(() => { if (!todas) { const f = [...tb.children]; if (f.some((tr, i) => i >= n && !tr.hidden)) aplicar(); } }).observe(tb, { childList: true });
  return caja;
}

/** Frescura a partir de las fuentes del fichero del módulo. */
export function fresco(d, prefijo) {
  const f = (d?.fuentes || []).find(x => x.fuente.startsWith(prefijo));
  if (!f) return { fuente: prefijo, estado: 'sin datos' };
  const edad = f.hora ? (Date.now() - new Date(f.hora.replace(' ', 'T'))) / 36e5 : null;
  return { fuente: f.fuente, edad_h: edad === null ? undefined : Math.max(0, edad), estado: f.estado === 'sin datos' ? 'sin datos' : (f.estado === 'viejo' || (edad ?? 0) > 26 ? 'viejo' : 'ok') };
}

/** Pie de fuentes (guía 3.6): un solo chip «Datos al día» o «N fuentes con retraso» que despliega el detalle, fuente a fuente. */
export function pieFuentes(d) {
  const fs = (d?.fuentes || []).map(f => fresco(d, f.fuente));
  const viejas = fs.filter(f => f.estado !== 'ok').length;
  return h('details', { class: 'que-es' },
    h('summary', {}, viejas ? `Datos: ${viejas} ${viejas === 1 ? 'fuente con retraso' : 'fuentes con retraso'}` : 'Datos al día'),
    h('ul', { class: 'pila' }, fs.map(f => h('li', {}, frescura(f).textContent))));
}

/** Euros con signo para márgenes y beneficio. */
export const eurS = n => (n === null || n === undefined ? '—' : `${n < 0 ? '−' : ''}${fmt.eur(Math.abs(n))}`);
export const pctS = (n, dec = 0) => (n === null || n === undefined ? '—' : `${n < 0 ? '−' : ''}${fmt.num(Math.abs(n), dec)} %`);

/** Carga un fichero de módulo; devuelve { d } o { error } (403 = no es de su puesto). */
export async function cargarDatos(ctx, nombre) {
  try {
    const d = ctx.datosModulo ? await ctx.datosModulo(nombre) : null;   // L-26: sin ctx.datosModulo no hay lectura propia
    return d ? { d } : { error: 'Sin datos' };
  } catch (e) { return { error: e.message || String(e) }; }
}

/** Botón que deja una acción simulada en la cola (R9) y lo confirma con un aviso. */
export async function encolar(ctx, a) {
  if (ctx.soloLectura) throw new Error('Estás en «ver como»: solo lectura.');
  if (ctx.accion) return ctx.accion(a);
  return { estado: 'simulada' };
}

// ---------------------------------------------------------------- periodo común por meses (R12, A-A2)
// Finanzas y Dinero por cliente solo tienen datos MENSUALES: el periodo de la barra (ctx.periodo) se lee por meses enteros.
// Un mes entra si el periodo toca alguno de sus días. Lo dice en llano textoMeses() («de julio a septiembre de 2026»).
/** Los meses 'AAAA-MM' que toca un rango { desde, hasta }. */
export function mesesDe(r) {
  if (!r?.desde || !r?.hasta) return [];
  const out = [];
  let [y, m] = r.desde.slice(0, 7).split('-').map(Number);
  const fin = r.hasta.slice(0, 7);
  for (let i = 0; i < 40; i++) {
    const k = `${y}-${String(m).padStart(2, '0')}`;
    out.push(k);
    if (k >= fin) break;
    m += 1; if (m > 12) { m = 1; y += 1; }
  }
  return out;
}
/** «septiembre de 2026» o «julio a septiembre de 2026». */
export function textoMeses(meses) {
  if (!meses.length) return 'sin meses';
  const nom = m => mesLargo(m).split(' de ')[0];
  if (meses.length === 1) return mesLargo(meses[0]);
  const a = meses[0], b = meses[meses.length - 1];
  return a.slice(0, 4) === b.slice(0, 4) ? `${nom(a)} a ${mesLargo(b)}` : `${mesLargo(a)} a ${mesLargo(b)}`;
}
/** Suma la clave k (o la función k) de una serie [{ m, … }] en los meses dados; null si ningún mes tiene dato. */
export function sumaMeses(serie, meses, k) {
  let tot = null;
  for (const x of serie || []) {
    if (!meses.includes(x.m)) continue;
    const v = typeof k === 'function' ? k(x) : x[k];
    if (typeof v === 'number') tot = (tot || 0) + v;
  }
  return tot;
}
/** { meses, comp } del periodo de la barra: meses del periodo y de su comparación (vacío si no se compara). */
export function mesesPeriodo(p) {
  return { meses: mesesDe(p), comp: p?.comp ? mesesDe(p.comp) : [] };
}
