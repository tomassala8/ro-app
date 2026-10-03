// modulos/redes.js · M9 «Redes» (E8 del plan v2; ficha G3-5).
//
// Qué pinta (arriba lo de cada día, abajo lo de cada semana o mes):
//   #/redes            → el número que manda (clientes con los próximos 14 días cubiertos), huecos, fallidas, por aprobar,
//                        «Lo primero hoy», el calendario de 14 días de todos los clientes (una fila por cliente, un punto por día)
//                        con chips que se quedan, y el rendimiento de lo publicado en 30 días frente a la regla de RO.
//   #/redes/<cliente>  → su calendario día a día, huecos, fallidas con el motivo, rendimiento por red, mejores y peores piezas,
//                        seguidores y botones de programar / mover (simulación con doble confirmación).
//
// Datos: data/redes/redes.json (fuentes_redes/generar_redes.py: Metricool con la llave propia, solo lectura). Filas con
// cliente_id → servir.py solo manda los clientes que la persona ve. Botones: ctx.accion() → cola «simulada».
// Diseño (auditoría 30, N6): sin hoja propia; calendario como tabla común (cabecera 11 px en mayúsculas y 700), punto de
// 8 px para huecos, tokens --s-*/--r-* y nada < 12 px. Periodo: no usa el común; todo son ventanas fijas (14 días adelante,
// 7 y 30 atrás) y así se dice junto a cada cifra.

import {
  h, fmt, semaforo, tile, rejillaTarjetas, listaLoPrimero, tablaDensa, chipEstado, chipsFiltro, selectorCliente, vacio, vacioLinea,
  botonConfirmar, avisoParcial, logoCliente, panel, icono, iniciales, hoyMadrid,
} from '../componentes.js';

// Revisión 44 (textos cortados): lo que la pantalla corta con «…» (una línea o el límite de líneas) lleva el texto entero
// en el title, para que la regla de la tarjeta o el nombre largo no se pierdan. Mira el contenedor mientras se pinta.
const _SEL_CORTE = '.tile .tx, .tile .tt span, .tile em, .det, .mot, .sub, .t, td, .chip, summary, b, small';
function vigilarCortes(raiz) {
  if (!raiz || raiz.__cortes) return;
  raiz.__cortes = true;
  let t = 0;
  const mirar = () => { t = 0; for (const el of raiz.querySelectorAll(_SEL_CORTE)) {
    if (el.title || el.closest('[title]') !== null && el.closest('[title]') !== el || !el.isConnected) continue;
    if (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 2) { const s = el.textContent.trim(); if (s && s.length > 8) el.title = s; } } };
  new MutationObserver(() => { if (!t) t = setTimeout(mirar, 400); }).observe(raiz, { childList: true, subtree: true });
  if (typeof ResizeObserver !== 'undefined') new ResizeObserver(() => { if (!t) t = setTimeout(mirar, 400); }).observe(raiz);
}

// Revisión 44 (§2.3): fechas con el formato único de la app: «2-oct» y «2-oct, 17:34» (nunca «2 oct» ni «sept»).
const _MES3 = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const _fechaDe = iso => (iso ? new Date(String(iso).length <= 10 ? `${iso}T12:00:00` : String(iso).replace(' ', 'T')) : null);
const fDiaRO = iso => { const d = _fechaDe(iso); return !d ? '—' : Number.isNaN(+d) ? String(iso) : `${d.getDate()}-${_MES3[d.getMonth()]}`; };
const fDiaHoraRO = iso => { const d = _fechaDe(iso); return !d ? '—' : Number.isNaN(+d) ? String(iso) : `${d.getDate()}-${_MES3[d.getMonth()]}, ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; };

const JEFES = ['direccion', 'finanzas_direccion', 'operaciones', 'proyectos', 'jefa_seo'];
const EST = { rojo: 0, ambar: 1, verde: 2 };
const TXT14 = { rojo: 'Hueco en 7 días', ambar: 'Hueco en 8-14 días', verde: 'Cubierto' };
const RED = { instagram: 'Instagram', facebook: 'Facebook', linkedin: 'LinkedIn', linkedinCompany: 'LinkedIn', tiktok: 'TikTok', youtube: 'YouTube', gmb: 'Ficha de Google', twitter: 'X' };
const DIAS = ['DO', 'LU', 'MA', 'MI', 'JU', 'VI', 'SÁ'];
const DIAS_LARGO = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
const PUNTO = { rojo: 'var(--bad)', ambar: 'var(--warn)', gris: 'var(--off)' };
/** Punto de 8 px (guía 3.8): estado sobrio en celdas, sin pastilla. */
/** Barrido v1: Metricool a veces da como «miniatura» un PDF (carrusel subido como documento). Un PDF no va en <img>
 *  (sale roto y el navegador lo bloquea): va como enlace «Ver PDF ↗». Si una imagen no carga, queda el icono. */
const ES_IMAGEN = /\.(?:jpe?g|png|gif|webp|avif)(?:[?#]|$)/i;
function miniatura(url) {
  const icoDoc = () => h('span', { class: 'ico-c gris' }, icono('doc'));
  if (!url) return icoDoc();
  if (/\.pdf(?:[?#]|$)/i.test(url)) return h('a', { class: 'bt mini', href: url, target: '_blank', rel: 'noopener', title: 'La pieza es un PDF: se abre en otra pestaña' }, icono('doc', { clase: 's' }), 'Ver PDF ↗');
  if (!ES_IMAGEN.test(url) && /\.[a-z0-9]{2,4}(?:[?#]|$)/i.test(url)) return h('a', { class: 'bt mini', href: url, target: '_blank', rel: 'noopener' }, icono('doc', { clase: 's' }), 'Ver pieza ↗');
  const img = h('img', { src: url, alt: '', loading: 'lazy', referrerpolicy: 'no-referrer', style: { width: '40px', height: '40px', borderRadius: 'var(--r-s)', objectFit: 'cover', background: 'var(--off-soft)', flex: 'none' } });
  img.addEventListener('error', () => img.replaceWith(icoDoc()), { once: true });
  return img;
}
const punto = (estado, titulo) => h('span', { 'aria-hidden': titulo ? null : 'true', title: titulo || null, role: titulo ? 'img' : null, 'aria-label': titulo || null,
  style: { width: '8px', height: '8px', borderRadius: '50%', background: PUNTO[estado] || PUNTO.gris, display: 'inline-block', flex: 'none' } });
/** Lo que todavía no se mide: plegado al pie (guía 3.6), no como panel. */
const piePlegado = (titulo, items) => h('details', { class: 'pie-fase2' }, h('summary', {}, titulo),
  h('ul', {}, items.map(([a, b]) => h('li', {}, h('b', {}, a), ` · falta: ${b}`))));

/** Una acción principal + «⋯» con el resto (details + .menu-flot comunes): nunca 3 botones en dos filas en el móvil. */
const masAcciones = (principal, ...resto) => {
  resto = resto.filter(Boolean);
  if (!resto.length) return [principal];
  return [principal, h('details', { style: { position: 'relative', display: 'flex' } },
    h('summary', { class: 'bt mini', 'aria-label': 'Más acciones', title: 'Más acciones', style: { listStyle: 'none', cursor: 'pointer', minWidth: '36px', justifyContent: 'center', flex: '1' } }, '⋯'),
    h('div', { class: 'menu-flot', role: 'menu', style: { left: 'auto', right: '0', minWidth: '200px' } }, resto))];
};
/** Rojo con cuentagotas (guía 3.4): en una lista, rojo solo el tercio de arriba (lo más urgente va primero); el resto, ámbar. */
const cuentagotas = (estado, i, n) => (estado === 'rojo' && i >= Math.max(1, Math.ceil(n / 3)) ? 'ambar' : estado);
/** Dos columnas: la clase común .dos, que desde la ronda 10 se apila de verdad en el móvil (R13: sin rejilla en línea). */
const dos = (...hijos) => h('div', { class: 'dos' }, ...hijos);
const esJefe = ctx => ctx.persona.puestos.some(p => JEFES.includes(p));
const nom = (ctx, id) => (id ? (ctx.nombre ? ctx.nombre(id) : id) : null);
const mio = (ctx, f) => f.redes_id === ctx.persona.id || f.account_id === ctx.persona.id;
const fecha = s => new Date(s + 'T12:00:00');
const dias14 = hoy => Array.from({ length: 14 }, (_, i) => { const d = fecha(hoy); d.setDate(d.getDate() + i); return d.toISOString().slice(0, 10); });
/** V2 · «hoy» real: la fecha de Madrid de hoy (helper común hoyMadrid), nunca el día en que se leyó Metricool. Si el dato es
 *  de otro día, se dice («datos del vie 2»). ctx.hoy es el común de E0 (V2-E); hoyMadrid, su respaldo. */
const hoyDe = ctx => ctx.hoy || hoyMadrid();
const diaTxt = x => { const d = fecha(x); return `${DIAS_LARGO[d.getDay()].slice(0, 3)} ${d.getDate()}`; };
/** V2 · UNA definición de «tus clientes de redes» (la misma que Mi día y pruebas_coherencia): la cartera de redes de las
 *  ASIGNACIONES (silla redes: los que llevas y en los que ayudas), no el responsable que trae Metricool. */
const silla = ctx => { const x = ctx.carteraPorSilla?.redes; return x && typeof x.has === 'function' ? x : null; };

// =================================================================== portada
function pintarPortada(cont, ctx, d) {
  const todos = d.clientes || [];
  const deRedes = ctx.persona.puestos.includes('redes') && !esJefe(ctx);
  const mia = silla(ctx);
  const esMio = f => (mia ? mia.has(f.cliente_id) : mio(ctx, f));
  const misClientes = todos.filter(esMio);
  const base = deRedes ? misClientes : todos;
  const m = d._meta;
  const hoy = hoyDe(ctx);
  const fres = { fuente: 'Metricool', fecha: m.leido_metricool };
  // R12 · cartera de la verdad única (asignaciones): Metricool no decide quién lleva qué
  const miCartera = (d.por_persona || []).find(x => x.persona_id === ctx.persona.id) || null;
  const sinMc = (d.sin_metricool || []).filter(x => (deRedes ? (mia ? mia.has(x.cliente_id) : x.redes_id === ctx.persona.id) : true));
  const lleva = base.filter(f => f.redes_id === ctx.persona.id).length;
  const verdes = base.filter(f => f.estado_14 === 'verde').length;
  const pct = base.length ? Math.round((verdes / base.length) * 100) : null;
  const rojos = base.filter(f => f.estado_14 === 'rojo');
  const fall7 = base.reduce((a, f) => a + f.fallidas_7, 0);
  const borr = base.reduce((a, f) => a + f.borradores, 0);
  const prog = base.reduce((a, f) => a + f.programadas_14, 0);
  const pub = base.reduce((a, f) => a + f.publicadas_30, 0);
  const pas = base.reduce((a, f) => a + f.pasadas_30, 0);
  const enFecha = pas ? Math.round((pub / pas) * 100) : null;
  ctx.titulo('Redes', `${base.length} clientes con marca en Metricool${deRedes ? ' · los de tu cartera' : ''} · del ${fDiaRO(hoy > m.ventana[0] ? hoy : m.ventana[0])} al ${fDiaRO(m.ventana[1])}`);
  if (ctx.nivel === 'resumen') cont.append(avisoParcial('Tu puesto ve el resumen de Redes: cifras y calendario. El detalle de cada cliente lo ven su persona de redes y su account.', { tipo: 'info' }));

  // 1 · cifras (6 → rejilla de 3 + 3). Ventanas fijas: lo programado mira 14 días adelante; lo publicado, 30 días atrás.
  cont.append(rejillaTarjetas([
    tile({ icono: 'cal', etiqueta: '14 días cubiertos', valor: fmt.pct(pct), unidad: `${verdes} de ${base.length}`, estado: pct === 100 ? 'verde' : rojos.length ? 'rojo' : 'ambar',
      contexto: deRedes ? `Número que manda · bien el 100 % · tu cartera de redes: ${base.length} con calendario en Metricool (${lleva} que llevas y ${base.length - lleva} en que ayudas)${sinMc.length ? ` · ${sinMc.length} sin marca, no cuentan` : ''}` : 'Número que manda · bien el 100 %', medible: 'medias', medibleDetalle: m.regla_hueco, frescura: fres, ir: 'Ver el calendario', alPulsar: () => document.getElementById('red-cal')?.scrollIntoView({ behavior: 'smooth' }) }),
    tile({ icono: 'alert', etiqueta: 'Hueco en 7 días', valor: rojos.length, unidad: `de ${base.length}`, estado: rojos.length ? 'rojo' : 'verde',
      contexto: '48 h sin cubrir → account y Coti (no hay jefa de redes)', medible: 'hoy', frescura: fres, ir: 'Ver cuáles', alPulsar: () => elegirChip(cont, 'rojo') }),
    tile({ icono: 'cerrar', etiqueta: 'Fallidas · 7 días', valor: fall7, estado: fall7 ? 'rojo' : 'verde', contexto: '7 días cerrados, sin hoy', medible: 'hoy', medibleDetalle: 'Error de la red o pendiente con fecha pasada', frescura: fres, ir: 'Ver cuáles', alPulsar: () => elegirChip(cont, 'fallidas') }),
    tile({ icono: 'editar', etiqueta: 'Por aprobar', valor: borr, unidad: 'borradores', estado: borr ? 'ambar' : 'verde', contexto: 'Borradores con fecha', medible: 'medias', medibleDetalle: m.aprobaciones, frescura: fres }),
    tile({ icono: 'send', etiqueta: 'Programadas · 14 días', valor: fmt.num(prog), contexto: `${fmt.num(prog / Math.max(base.length, 1), 1)} por cliente · plan de RO ≈ 7`, medible: 'hoy', frescura: fres }),
    tile({ icono: 'check', etiqueta: 'En fecha · 30 días', valor: fmt.pct(enFecha), unidad: `${fmt.num(pub)} de ${fmt.num(pas)}`, estado: semaforo(enFecha, { verde: 100, ambar: 95 }), contexto: 'Bien el 100 % · mal por debajo del 95 %', medible: 'hoy', frescura: fres }),
  ]));

  if (miCartera) cont.append(h('p', { class: 'sub', style: { margin: '0', maxWidth: '72ch' } }, miCartera.texto, deRedes ? ' Las cifras de arriba cuentan los dos (la misma cartera que Mi día).' : ''));
  if (m.hoy && m.hoy < hoy) cont.append(avisoParcial(`Datos de Metricool del ${diaTxt(m.hoy)} (${fDiaRO(m.hoy)}). El calendario empieza hoy, ${diaTxt(hoy)}: lo programado después de esa lectura todavía no sale.`, { tipo: 'info' }));
  if (sinMc.length) cont.append(panel({ titulo: deRedes ? 'Tus clientes sin marca en Metricool' : 'Clientes con persona de redes y sin marca en Metricool', icono: 'plug', sub: 'Sin marca conectada no se puede ver su calendario: no cuentan en las cifras de arriba.' },
    h('ul', { class: 'cuerpo', style: { listStyle: 'none', margin: '0', display: 'grid', gap: 'var(--s-2)' } }, sinMc.map(x => h('li', { class: 'fila', style: { gap: 'var(--s-2)', minHeight: '32px' } },
      chipEstado('gris', x.cliente), h('span', { class: 'sub' }, deRedes ? (x.account_nombre ? `account: ${x.account_nombre}` : 'sin account') : `${x.redes_nombre || 'sin persona'}${x.account_nombre ? ` · account: ${x.account_nombre}` : ''}`))))));
  cont.append(h('p', { class: 'sub', style: { margin: '0', maxWidth: '72ch' } }, 'Esta pantalla no cambia con el periodo: lo programado mira 14 días adelante y lo publicado, 30 días atrás (Metricool no da serie diaria por cliente).'));

  // 2 · lo primero hoy: fallidas y huecos en 7 días (máximo 7)
  const prim = [
    ...base.filter(f => f.fallidas_7).map(f => ({ f, tipo: 'fallida' })),
    ...rojos.map(f => ({ f, tipo: 'hueco' })),
  ];
  const restoPrim = Math.max(0, prim.length - 7);
  const manana = dias14(hoy)[1];
  cont.append(panel({ titulo: 'Lo primero hoy', icono: 'zap', sub: 'Fallidas y huecos en los próximos 7 días',
    pie: restoPrim ? h('span', {}, `${fmt.plural(restoPrim, 'cliente más', 'clientes más')} con hueco: en el calendario de abajo`) : null },
    listaLoPrimero(prim.slice(0, 7).map(({ f, tipo }, i, lista) => {
      const hu = f.huecos.find(x => x.en_7) || f.huecos[0];
      const fa = f.fallidas[0];
      // rojo: fallida o hueco que empieza hoy o mañana (y como mucho el tercio de arriba); el resto, ámbar
      const urgente = tipo === 'fallida' || (hu && hu.desde <= manana);
      return {
        estado: cuentagotas(urgente ? 'rojo' : 'ambar', i, lista.length), icono: tipo === 'fallida' ? 'cerrar' : 'cal',
        motivo: tipo === 'fallida' ? `${f.cliente} · publicación fallida` : `${f.cliente} · ${hu.dias} días sin nada (${fDiaRO(hu.desde)} → ${fDiaRO(hu.hasta)})`,
        detalle: tipo === 'fallida' ? `${fDiaRO(fa.dia)} · ${(fa.redes[0] || {}).detalle || fa.estado} · «${fa.texto}»` : [nom(ctx, f.redes_id) ? `Redes: ${nom(ctx, f.redes_id)}` : 'Sin persona de redes', nom(ctx, f.account_id) ? `account: ${nom(ctx, f.account_id)}` : null].filter(Boolean).join(' · '),
        botones: masAcciones(
          h('a', { class: 'bt mini', href: `#/redes/${f.cliente_id}` }, icono('cli'), 'Ver cliente'),
          h('a', { href: f.prueba, target: '_blank', rel: 'noopener', role: 'menuitem' }, icono('ext', { clase: 's' }), 'Abrir en Metricool'),
          botonConfirmar({ texto: tipo === 'fallida' ? 'Avisar al account' : 'Me encargo', pregunta: tipo === 'fallida' ? '¿Avisar con el motivo?' : '¿Te encargas tú?', confirmar: 'Sí', mini: true, soloLectura: ctx.soloLectura,
            alConfirmar: async () => { await ctx.accion({ herramienta: 'app', tipo: tipo === 'fallida' ? 'aviso_account' : 'hueco_lo_cubro', objeto: f.cliente, cliente_id: f.cliente_id, texto: tipo === 'fallida' ? (fa.redes[0] || {}).detalle : `Hueco ${hu.desde} → ${hu.hasta}`, vista_previa: tipo === 'fallida' ? `Aviso al account de ${f.cliente}: publicación fallida del ${fa.dia} (${(fa.redes[0] || {}).detalle}).` : `${ctx.persona.nombre} cubre el hueco de ${f.cliente} del ${hu.desde} al ${hu.hasta}.` }); return 'En la cola (simulación)'; } })),
      };
    }), { vacio: { titulo: 'Sin huecos ni fallidas', porque: 'Todos tus clientes tienen la semana cubierta.', celebrar: true } })));

  // 3 · calendario de 14 días: una tabla común (cabecera en mayúsculas de 11 px y 700), una fila por cliente
  const ops = [
    { valor: '', texto: 'Todos', cuenta: base.length },
    { valor: 'rojo', texto: 'Hueco en 7 días', icono: 'fire', cuenta: rojos.length, cuentaEstado: 'rojo' },
    { valor: 'ambar', texto: 'Hueco en 8-14', icono: 'alert', cuenta: base.filter(f => f.estado_14 === 'ambar').length },
    { valor: 'verde', texto: 'Cubiertos', icono: 'ok', cuenta: verdes },
    { valor: 'fallidas', texto: 'Con fallidas', icono: 'cerrar', cuenta: base.filter(f => f.fallidas.length).length, cuentaEstado: 'rojo' },
  ];
  if (misClientes.length && base !== misClientes) ops.push({ valor: 'mios', texto: 'Mis clientes', icono: 'persona', cuenta: misClientes.length });
  else if (deRedes && lleva && lleva < base.length) ops.push({ valor: 'llevo', texto: 'Los que llevo', icono: 'persona', cuenta: lleva });
  const caja = h('div');
  const chips = chipsFiltro({ etiqueta: 'Ver', clave: `redes.chip.${ctx.persona.id}`, opciones: ops, alCambiar: () => pintar() });
  [...chips.querySelectorAll('button')].forEach((b, i) => { if (ops[i]) b.dataset.v = ops[i].valor; });
  chips.id = 'red-chips';
  const dias = dias14(hoy);
  const urgentes = new Set(dias.slice(0, 2));   // hoy y mañana: el hueco que hay que tapar ya va en rojo; el resto, ámbar
  const centro = { textAlign: 'center', paddingLeft: 'var(--s-1)', paddingRight: 'var(--s-1)' };
  const pintar = () => {
    const v = chips.valor();
    const filas = base.filter(f => !v || (v === 'fallidas' ? f.fallidas.length : v === 'mios' ? esMio(f) : v === 'llevo' ? f.redes_id === ctx.persona.id : f.estado_14 === v));
    if (!filas.length) { caja.replaceChildren(vacioLinea('Ningún cliente con este filtro. Cambia el filtro de arriba.', { icono: 'cal' })); return; }
    const cab = h('tr', {}, h('th', { scope: 'col' }, 'Cliente'), dias.map((x, i) => {
      const dd = fecha(x);
      return h('th', { scope: 'col', title: `${DIAS_LARGO[dd.getDay()]} ${fDiaRO(x)}${i === 0 ? ' (hoy)' : ''}`, style: { ...centro, color: i === 0 ? 'var(--accent-ink)' : null } }, `${DIAS[dd.getDay()]} ${dd.getDate()}`);
    }));
    const cuerpo = filas.map(f => {
      const porDia = new Map();
      for (const p of f.calendario) if (p.estado !== 'fallida') { const o = porDia.get(p.dia) || { n: 0, borr: 0 }; o.n++; if (p.estado === 'borrador') o.borr++; porDia.set(p.dia, o); }
      const enHueco = x => f.huecos.find(hh => x >= hh.desde && x <= hh.hasta);
      return h('tr', {},
        h('td', { class: 'principal', style: { minWidth: '140px' } },
          h('a', { class: 'celda-cli', href: `#/redes/${f.cliente_id}`, title: `${f.cliente} · ${TXT14[f.estado_14]}`, style: { color: 'var(--ink)', textDecoration: 'none', display: 'flex', alignItems: 'center', minHeight: '32px' } },
            h('span', { style: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, f.cliente))),
        dias.map(x => {
          const o = porDia.get(x); const hu = enHueco(x);
          const titulo = `${f.cliente} · ${fDiaRO(x)}: ${o ? `${fmt.plural(o.n, 'publicación', 'publicaciones')}${o.borr ? ` (${o.borr} por aprobar)` : ''}` : x > m.ventana[1] ? 'sin dato todavía (fuera de la última lectura de Metricool)' : hu ? (urgentes.has(x) ? 'hueco que hay que tapar ya' : 'hueco') : 'nada programado'}`;
          return h('td', { style: centro, title: titulo },
            o ? h('span', { class: `chip sin-punto ${o.borr === o.n ? 'azul' : 'verde'}`, 'aria-label': titulo }, String(o.n))
              : punto(hu ? (urgentes.has(x) ? 'rojo' : 'ambar') : 'gris', titulo));
        }));
    });
    caja.replaceChildren(h('div', { class: 'tabla-scroll' }, h('table', { class: 'densa', 'aria-label': 'Calendario de los próximos 14 días' }, h('thead', {}, cab), h('tbody', {}, cuerpo))));
  };
  pintar();
  const leyenda = h('span', { class: 'fila', style: { gap: 'var(--s-2) var(--s-4)' } },
    h('span', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'nowrap' } }, h('span', { class: 'chip sin-punto verde' }, '2'), 'Programadas'),
    h('span', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'nowrap' } }, h('span', { class: 'chip sin-punto azul' }, '1'), 'Por aprobar'),
    h('span', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'nowrap' } }, punto('rojo'), 'Hueco hoy o mañana'),
    h('span', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'nowrap' } }, punto('ambar'), 'Hueco más adelante'),
    h('span', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'nowrap' } }, punto('gris'), 'Nada, sin llegar a hueco'));
  const cal = panel({ titulo: 'Calendario de los próximos 14 días', icono: 'cal', sub: 'Una fila por cliente; pulsa el nombre para ver su detalle. Ventana fija: de hoy a 13 días vista.', pie: leyenda },
    h('div', { class: 'cuerpo', style: { paddingBottom: 'var(--s-1)' } }, chips), caja);
  cal.id = 'red-cal';
  cont.append(cal);

  // 4 · rendimiento de lo publicado (ventana fija de 30 días: Metricool no da serie diaria por cliente)
  const filasR = base.map(f => ({ ...f, ig: f.por_red.instagram?.tasa ?? null, li: f.por_red.linkedin?.tasa ?? null, fb: f.por_red.facebook?.tasa ?? null }));
  const celdaTasa = (v, um) => v === null ? h('span', { class: 'sub' }, '—') : chipEstado(semaforo(v, { verde: um, ambar: um / 2 }), `${fmt.num(v, 1)} %`);
  cont.append(panel({ titulo: 'Rendimiento de lo publicado · 30 días', icono: 'grafico', sub: 'Interacción por red. Instagram y Facebook sobre alcance (bien desde 1,5 %); LinkedIn sobre impresiones (bien desde 3 %). Últimos 30 días, fijo.' },
    tablaDensa({
      filas: filasR, porPagina: 15, apilable: false, buscar: { campos: ['cliente', 'redes_quien'], placeholder: 'Buscar cliente o persona' }, filtros: esJefe(ctx) ? [{ clave: 'redes_quien', titulo: 'Lo lleva' }] : [],
      columnas: [
        { clave: 'cliente', titulo: 'Cliente', principal: true, celda: f => h('span', { class: 'celda-cli' }, logoCliente({ nombre: f.cliente, logo: (ctx.clientes.find(c => c.id === f.cliente_id) || {}).logo }), f.cliente) },
        { clave: 'publicadas_30', titulo: 'Publicadas', num: true, celda: f => fmt.num(f.publicadas_30) },
        { clave: 'ig', titulo: 'Instagram', num: true, celda: f => celdaTasa(f.ig, 1.5) },
        { clave: 'fb', titulo: 'Facebook', num: true, celda: f => celdaTasa(f.fb, 1.5) },
        { clave: 'li', titulo: 'LinkedIn', num: true, celda: f => celdaTasa(f.li, 3) },
        { clave: 'redes_quien', titulo: 'Lo lleva', celda: f => nom(ctx, f.redes_id) ? nom(ctx, f.redes_id) : h('span', { class: 'sub' }, 'sin asignar') },
      ],
      alPulsar: f => ctx.navegar(`redes/${f.cliente_id}`), etiquetaFila: f => `${f.cliente}: abrir detalle de redes`,
      vacio: { titulo: 'Sin rendimiento todavía', porque: 'Metricool no devuelve publicaciones medidas en 30 días.' },
    })));

  // 5 · lo que todavía no se mide, plegado al pie
  cont.append(piePlegado('Todavía no se mide · 4 cosas (fase 2)', [
    ['Volumen frente a lo pactado con cada cliente', 'cargar el plan de cada cliente; hoy se usa el de RO por defecto'],
    ['Aprobaciones atascadas más de 5 días', 'la API de Metricool no da el estado de aprobación'],
    ['Comentarios y mensajes respondidos en < 24 h', 'no está en el alcance de la API usada'],
    ['Paquete de validación del día 20', 'tarea con fecha en ClickUp'],
  ]));
}

function elegirChip(cont, v) {
  const b = [...cont.querySelectorAll('#red-chips button')].find(x => x.dataset.v === v);
  if (b && b.getAttribute('aria-pressed') !== 'true') b.click();
  cont.querySelector('#red-cal')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// =================================================================== detalle
function pintarDetalle(cont, ctx, d, id) {
  const volver = h('a', { class: 'bt', href: '#/redes' }, icono('volver'), 'Volver a Redes');
  const f = (d.clientes || []).find(x => x.cliente_id === id);
  const c = ctx.clientes.find(x => x.id === id);
  if (!f) {
    ctx.titulo(c ? c.nombre : 'Cliente', '');
    cont.append(vacio({ icono: c && !c.detalle ? 'candado' : 'heart', titulo: c && !c.detalle ? 'Las redes de este cliente no son de tu puesto' : 'Este cliente no tiene marca en Metricool',
      texto: c && !c.detalle ? `Lo ven su persona de redes y su account (${c.responsable}).` : 'Para verlo aquí, conectar sus redes en Metricool (lo autoriza el cliente) y emparejar la marca.', quien: c && !c.detalle ? c.responsable : 'Agus', accion: volver, borde: true }));
    return;
  }
  if (ctx.nivel === 'resumen') {
    ctx.titulo(f.cliente, '');
    cont.append(vacio({ icono: 'candado', titulo: 'Tu puesto ve el resumen de Redes', texto: 'El detalle de cada cliente lo ven su persona de redes, su account, Coti y dirección.', accion: volver, borde: true }));
    return;
  }
  const m = d._meta;
  ctx.titulo(f.cliente, `Redes · ${nom(ctx, f.redes_id) ? `lo lleva ${nom(ctx, f.redes_id)}` : 'sin persona de redes'} · marca «${f.marca}» en Metricool`);
  const visibles = d.clientes.map(x => ctx.clientes.find(k => k.id === x.cliente_id)).filter(Boolean);
  cont.append(h('div', { class: 'fila', style: { justifyContent: 'space-between' } },
    h('nav', { class: 'migas', 'aria-label': 'Migas' }, h('a', { href: '#/redes' }, icono('heart', { clase: 's' }), 'Redes'), h('span', { 'aria-hidden': 'true' }, '›'), h('span', { 'aria-current': 'page' }, f.cliente)),
    selectorCliente({ clientes: visibles, actual: id, etiqueta: 'Cambiar de cliente', alElegir: x => ctx.navegar(`redes/${x.id}`), insignia: x => { const y = d.clientes.find(k => k.cliente_id === x.id); return y ? chipEstado(y.estado_14, TXT14[y.estado_14]) : null; } })));
  cont.append(h('section', { class: 'detalle-cab' }, h('div', { class: 'fila', style: { gap: 'var(--s-4)', alignItems: 'center' } },
    logoCliente({ nombre: f.cliente, logo: c?.logo }, 'logo-cli xl'),
    h('div', { style: { minWidth: 0, flex: '1 1 260px' } }, h('h2', {}, f.cliente),
      h('div', { class: 'meta-linea', style: { marginTop: 'var(--s-1)' } }, h('span', {}, icono('heart'), f.redes.map(r => RED[r] || r).join(' · ')),
        nom(ctx, f.redes_id) ? h('span', {}, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(nom(ctx, f.redes_id))), nom(ctx, f.redes_id)) : null,
        nom(ctx, f.account_id) ? h('span', {}, icono('persona'), `account: ${nom(ctx, f.account_id)}`) : null),
      h('div', { class: 'fila', style: { marginTop: 'var(--s-3)', gap: 'var(--s-2)' } }, chipEstado(f.estado_14, TXT14[f.estado_14]))),
    h('a', { class: 'bt', href: f.prueba, target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir en Metricool'))));

  const seg = (k, et) => f.seguidores[k] ? tile({ icono: 'users', etiqueta: et, valor: fmt.num(f.seguidores[k].seguidores), unidad: 'seguidores', comparacion: { delta: f.seguidores[k].seguidores - f.seguidores[k].hace30, texto: 'en 30 días' }, contexto: 'Bien si crece un 1 % al mes', medible: 'hoy' }) : null;
  cont.append(rejillaTarjetas([
    tile({ icono: 'cal', etiqueta: 'Días cubiertos', valor: f.cubiertos_14, unidad: 'de 14', estado: f.estado_14, contexto: f.huecos.length ? `Hueco: ${f.huecos.map(x => `${fDiaRO(x.desde)} → ${fDiaRO(x.hasta)}`).join(' · ')}` : 'Sin huecos', medible: 'medias', medibleDetalle: m.regla_hueco, frescura: { fuente: 'Metricool', fecha: m.leido_metricool } }),
    tile({ icono: 'check', etiqueta: 'En fecha · 30 días', valor: fmt.pct(f.en_fecha_pct), unidad: `${fmt.num(f.publicadas_30)} de ${fmt.num(f.pasadas_30)}`, estado: semaforo(f.en_fecha_pct, { verde: 100, ambar: 95 }), contexto: 'Bien el 100 % · mal por debajo del 95 %', medible: 'hoy' }),
    tile({ icono: 'cerrar', etiqueta: 'Fallidas · 30 días', valor: f.fallidas.length, estado: f.fallidas.length ? 'rojo' : 'verde', contexto: `${fmt.num(f.fallidas_7)} en los últimos 7 días`, medible: 'hoy' }),
    seg('instagram', 'Instagram'), seg('linkedin', 'LinkedIn'),
  ].filter(Boolean)));

  // calendario día a día (hoy primero) con los huecos intercalados
  const hoyD = hoyDe(ctx);
  const dias = dias14(hoyD);
  const items = [];
  const filaDia = (x, ...resto) => {
    const dd = fecha(x);
    return h('li', { style: { flexWrap: 'wrap', alignItems: 'center', gap: 'var(--s-3)' } },
      h('span', { style: { width: '64px', flex: 'none', display: 'grid' } }, h('b', {}, `${DIAS[dd.getDay()]} ${dd.getDate()}`), h('span', { class: 'sub' }, x === hoyD ? 'hoy' : fDiaRO(x))), ...resto);
  };
  for (const x of dias) {
    const ps = f.calendario.filter(p => p.dia === x);
    if (!ps.length) {
      const hu = f.huecos.find(hh => x >= hh.desde && x <= hh.hasta);
      if (hu && x === hu.desde) items.push(filaDia(x, h('span', { style: { flex: '1 1 140px', minWidth: 0 } }, chipEstado(hu.en_7 ? 'rojo' : 'ambar', `Hueco de ${hu.dias} días`), h('span', { class: 'sub' }, ` hasta el ${fDiaRO(hu.hasta)}`)),
        botonConfirmar({ texto: 'Programar', pregunta: 'Sale sola en la cuenta del cliente. ¿Dejarlo en la cola?', confirmar: 'Sí, a la cola', mini: true, soloLectura: ctx.soloLectura,
          alConfirmar: async () => { await ctx.accion({ herramienta: 'metricool', tipo: 'programar', objeto: `${f.cliente} · ${x}`, cliente_id: f.cliente_id, texto: `Programar publicación el ${x}`, vista_previa: `Metricool · marca «${f.marca}» · nueva publicación el ${x} (pide plan Advanced y permiso de escritura)` }); return 'En la cola (simulación)'; } })));
      continue;
    }
    for (const p of ps) {
      items.push(filaDia(x,
        miniatura(p.miniatura),
        h('span', { style: { flex: '1 1 140px', minWidth: 0, overflowWrap: 'anywhere', display: 'grid', gap: 'var(--s-1)' } },
          h('span', { class: 'fila', style: { gap: 'var(--s-2)' } }, chipEstado(p.estado === 'borrador' ? 'azul' : p.estado === 'publicada' ? 'verde' : p.estado === 'fallida' || p.estado === 'no_salio' ? 'rojo' : 'gris', { borrador: 'Por aprobar', publicada: 'Publicada', programada: 'Programada', fallida: 'Fallida', no_salio: 'No salió', publicando: 'Publicando' }[p.estado] || p.estado), h('span', { class: 'sub' }, `${p.hora} · ${p.redes.map(r => RED[r] || r).join(', ')}`)),
          p.texto ? h('span', {}, p.texto.length > 160 ? `${p.texto.slice(0, 157)}…` : p.texto) : h('span', { class: 'sub' }, 'Sin texto')),
        botonConfirmar({ texto: 'Mover', pregunta: '¿Cambiar de día? Sale sola en la cuenta del cliente.', confirmar: 'Sí, a la cola', mini: true, soloLectura: ctx.soloLectura || p.estado === 'publicada',
          alConfirmar: async () => { await ctx.accion({ herramienta: 'metricool', tipo: 'mover', objeto: `${f.cliente} · ${p.dia} ${p.hora}`, cliente_id: f.cliente_id, texto: p.texto, vista_previa: `Metricool · mover la publicación del ${p.dia} ${p.hora} (doble confirmación hecha)` }); return 'En la cola (simulación)'; } })));
    }
  }
  cont.append(panel({ titulo: 'Los próximos 14 días', icono: 'cal', sub: 'Lo programado, día a día, con los huecos a la vista. Programar y mover quedan en la cola en simulación.' },
    h('div', { class: 'cuerpo' }, items.length ? h('ul', { class: 'lista-i' }, items) : vacioLinea('Nada programado ni huecos en los próximos 14 días.', { icono: 'cal' }))));

  // fallidas y rendimiento (últimos 30 días, fijo)
  const pieza = p => h('li', {}, h('span', { style: { flex: '1', minWidth: 0, overflowWrap: 'anywhere' } }, h('b', {}, `${RED[p.red]} · ${fDiaRO(p.fecha)}`), ' ', p.texto ? (p.texto.length > 120 ? `${p.texto.slice(0, 117)}…` : p.texto) : ''),
    h('span', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'nowrap' } }, chipEstado(semaforo(p.tasa, { verde: p.umbral, ambar: p.umbral / 2 }), `${fmt.num(p.tasa, 1)} %`), p.url ? h('a', { class: 'bt mini', href: p.url, target: '_blank', rel: 'noopener', 'aria-label': 'Abrir la publicación' }, icono('ext')) : null));
  const titulo = t => h('p', { style: { font: 'var(--t-eyebrow)', textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--dim)', margin: 'var(--s-3) 0 0' } }, t);
  cont.append(dos(
    panel({ titulo: 'Lo que mejor y peor funcionó · 30 días', icono: 'star', sub: 'Interacción sobre alcance (Instagram, Facebook) o sobre impresiones (LinkedIn)' },
      h('div', { class: 'cuerpo' }, f.mejor.length ? [titulo('Mejores'), h('ul', { class: 'lista-i' }, f.mejor.map(pieza)), f.peor.length ? [titulo('Peores'), h('ul', { class: 'lista-i' }, f.peor.map(pieza))] : null]
        : vacioLinea('Sin piezas medidas en 30 días: Metricool no devuelve rendimiento de este cliente (o solo publica en redes sin analítica por la API, como TikTok o YouTube).', { icono: 'grafico' }))),
    panel({ titulo: 'Publicaciones fallidas', icono: 'cerrar', sub: 'Con el motivo que da la red' },
      h('div', { class: 'cuerpo' }, f.fallidas.length ? h('ul', { class: 'lista-i' }, f.fallidas.map(x => h('li', { style: { alignItems: 'flex-start' } }, h('b', { style: { width: '64px', flex: 'none' } }, fDiaRO(x.dia)),
        h('span', { style: { flex: '1', minWidth: 0, overflowWrap: 'anywhere', display: 'grid', gap: 'var(--s-1)' } }, h('b', {}, x.redes.map(r => `${RED[r.red] || r.red}: ${r.detalle || r.estado}`).join(' · ')), h('span', { class: 'sub' }, `«${x.texto}»`)))))
        : vacioLinea('Ninguna fallida: todo lo programado salió.', { icono: 'ok' })))));
}

export default {
  id: 'redes',
  titulo: 'Redes',
  grupo: 'SEO, web y redes',
  puestos_que_lo_ven: { direccion: 'todo', finanzas_direccion: 'todo', operaciones: 'todo', proyectos: 'todo', jefa_seo: 'resumen', account: 'suyo', redes: 'suyo', produccion: 'resumen' },
  async render(cont, ctx) {
    vigilarCortes(cont);
    let d;
    try { d = await ctx.datosModulo('redes/redes'); for (const f of d.clientes || []) f.redes_quien = nom(ctx, f.redes_id) || 'Sin asignar'; } catch (e) {
      cont.append(vacio({ icono: 'alert', tono: 'aviso', titulo: 'No llegan los datos de Redes', texto: `${e.message}. Se generan con fuentes_redes/generar_redes.py.`, quien: 'Agus', borde: true }));
      return;
    }
    const [id] = ctx.params;
    if (id) pintarDetalle(cont, ctx, d, id);
    else pintarPortada(cont, ctx, d);
  },
};
