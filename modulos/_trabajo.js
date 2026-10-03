// modulos/_trabajo.js · Ronda U (3-oct, cambio #1 del 50): el molde común de una «pantalla de trabajo».
//
// Regla de aceptación (50 §3): la primera fila accionable a menos de 300 px desde arriba del contenido, a 1440 y a 390.
// Lo que va primero es la LISTA (o el objeto) de trabajo; las cifras son filtros pequeños encima; la explicación, el
// contexto y el consejo de la IA van a un lado (escritorio) o debajo y plegados (móvil). Nada empuja la lista.
//
//   pantallaTrabajo({ id, filtros, pestanas, lista, detalle, contexto, tituloContexto, abiertoContexto, consejo })
//     filtros   · nodo pequeño (≤ 64 px): franjaCifras(), chipsFiltro()… Las cifras SON los filtros de la lista.
//     pestanas  · nodo de pestanas() (opcional), justo encima de la lista.
//     lista     · LA lista de trabajo (o el objeto abierto). Va la primera en el móvil y a la izquierda (2/3) en ancho.
//     detalle   · panel del objeto elegido con su barra de acciones (opcional). A la derecha, fijo al desplazar.
//     contexto  · [nodos] de lectura (cifras grandes, «cómo se mide», gráficos…). A la derecha bajo el detalle, en un
//                 plegable «Contexto y cifras» (abierto en ancho, cerrado en el móvil salvo abiertoContexto: true).
//     consejo   · true (por defecto): el «Qué haría yo hoy aquí» que la carcasa pone arriba baja a DESPUÉS de este
//                 bloque y se pliega a una línea; nunca queda encima de la lista. false: no se toca.
//     Devuelve un <div data-trabajo> (clase común .dos: dos columnas desde 901 px, una debajo). el.lista, el.lado.
//
//   barraAcciones({ titulo, sub, acciones, volver })
//     La barra de un DETALLE (incidencia, decisión, persona…): título corto del objeto + sus acciones, pegada arriba
//     (sticky bajo la cabecera de la app) para que «Escalar / Resolver / No aplica / Aprobar» estén siempre a la vista.
//
//   franjaCifras([{ etiqueta, valor, estado, activo, alPulsar, titulo }], { etiqueta })
//     Cifras pequeñas en una franja de 40-48 px que filtran la lista (botones con aria-pressed). Sustituyen a las
//     tarjetas grandes de arriba; las tarjetas, si hacen falta, van al contexto.
//
//   consejoCompacto(raiz, destino)
//     Lo usa pantallaTrabajo; exportado para pantallas con su propia maqueta: vigila #main y, cuando la carcasa pone el
//     consejo, lo coloca JUSTO DESPUÉS del bloque de #main que contiene a «destino» (sigue siendo hijo directo de #main:
//     si no, la carcasa pondría otro) y lo deja plegado en una línea, una vez (sin guardar la preferencia de la persona;
//     si la persona lo abre, se queda abierto). Devuelve una función para dejar de vigilar.
//
// Diseño estricto: solo clases comunes (dos, pila, fila, panel, chips-f, bt, sub, que-es) y tokens en línea.

import { h, icono } from '../componentes.js';

const esMovil = () => { try { return matchMedia('(max-width: 900px)').matches; } catch { return false; } };

/** Pliega el consejo a su línea de resumen sin tocar la preferencia guardada. */
export function plegarConsejo(c) {
  const lista = c.querySelector('ol.ia-acciones');
  const res = c.querySelector(':scope > .ia-sub');
  const b = c.querySelector('.ia-cab button[aria-controls]');
  if (!lista || lista.hidden) return;
  lista.hidden = true;
  if (res) res.hidden = false;
  if (b) { b.setAttribute('aria-expanded', 'false'); b.replaceChildren(icono('chev'), 'Ver los consejos'); }
}

export function consejoCompacto(raiz, destino) {
  // La carcasa vuelve a poner el consejo si no encuentra uno como hijo DIRECTO de #main: por eso no se mete dentro de otra
  // caja, se coloca justo DESPUÉS del hijo de #main que contiene a «destino» (la lista, la barra…) y se pliega una vez.
  const main = raiz?.closest?.('#main') || document.getElementById('main');
  if (!main || !destino) return () => {};
  const anclaDe = () => { let a = destino; while (a && a.parentElement !== main) a = a.parentElement; return a; };
  const mover = () => {
    if (!destino.isConnected) { obs.disconnect(); return; }
    const c = main.querySelector(':scope > [data-ia="consejo"]');
    const ancla = anclaDe();
    if (!c || !ancla) return;
    if (!c.dataset.plegadoU) { c.dataset.plegadoU = '1'; plegarConsejo(c); }
    if (ancla.nextElementSibling !== c) { c.style.marginBottom = '0'; c.style.marginTop = 'var(--s-4)'; ancla.after(c); }
  };
  const obs = new MutationObserver(mover);
  obs.observe(main, { childList: true });
  mover();
  return () => obs.disconnect();
}

export function pantallaTrabajo(o = {}) {
  const movil = esMovil();
  const izq = h('div', { class: 'pila', 'data-trabajo-lista': '', style: { minWidth: '0', gap: 'var(--s-3)' } },
    o.filtros || null, o.pestanas || null, o.lista || null);
  const ctxNodos = (Array.isArray(o.contexto) ? o.contexto : [o.contexto]).filter(Boolean);
  const plegable = ctxNodos.length
    ? h('details', { class: 'que-es', 'data-trabajo-contexto': '', open: (o.abiertoContexto ?? !movil) || null },
      h('summary', {}, o.tituloContexto || 'Contexto y cifras'), h('div', { class: 'pila', style: { marginTop: 'var(--s-3)' } }, ctxNodos))
    : null;
  const lado = h('aside', { class: 'pila', 'data-trabajo-lado': '', 'aria-label': 'Detalle y contexto',
    style: { minWidth: '0', gap: 'var(--s-3)', position: movil ? 'static' : 'sticky', top: 'calc(var(--alto-cabecera) + var(--s-4))', alignSelf: 'start' } },
  o.detalle || null, plegable);
  const tieneLado = !!(o.detalle || plegable || o.consejo !== false);
  const el = h('div', { class: tieneLado ? 'dos' : 'pila', 'data-trabajo': o.id || '' }, izq, tieneLado ? lado : null);
  el.lista = izq; el.lado = lado;
  if (o.consejo !== false) queueMicrotask(() => consejoCompacto(el, el));
  return el;
}

export function barraAcciones({ titulo, sub, acciones = [], volver } = {}) {
  return h('div', { class: 'panel', 'data-barra-acciones': '', role: 'toolbar', 'aria-label': `Acciones${typeof titulo === 'string' ? `: ${titulo}` : ''}`,
    style: { position: 'sticky', top: 'calc(var(--alto-cabecera) + var(--s-2))', zIndex: '5', padding: 'var(--s-3) var(--relleno)', overflow: 'visible' } },
  h('div', { class: 'fila', style: { justifyContent: 'space-between', gap: 'var(--s-2) var(--s-4)' } },
    h('div', { style: { minWidth: '0', flex: '1 1 240px' } },
      volver ? h('a', { class: 'bt mini', href: volver.href, style: { marginRight: 'var(--s-2)' } }, icono('izquierda', { clase: 's' }), volver.texto || 'Volver') : null,
      titulo ? h('b', {}, titulo) : null, sub ? h('span', { class: 'sub', style: { display: 'block' } }, sub) : null),
    h('div', { class: 'fila', style: { gap: 'var(--s-2)' } }, acciones.filter(Boolean))));
}

/** filasFlexibles(lista) · Ronda U: las filas de una lista común (ol.primero, de listaLoPrimero o propia) pasan a flex con
 *  salto de línea: el texto pide al menos `minTexto` px y, si con los botones no cabe, los botones bajan a la línea de abajo
 *  (nunca encima del texto ni el título reducido a una letra), a CUALQUIER ancho (390-1440), sin depender de media queries. */
export function filasFlexibles(lista, { minTexto = 260 } = {}) {
  if (!lista?.querySelectorAll) return lista;
  for (const li of lista.querySelectorAll(':scope > li, .primero > li')) {
    Object.assign(li.style, { display: 'flex', flexWrap: 'wrap', alignItems: 'center', columnGap: 'var(--s-3)', rowGap: 'var(--s-2)' });
    const [num, texto, acc] = li.children;
    if (num) num.style.flex = 'none';
    if (texto) Object.assign(texto.style, { flex: `1 1 ${minTexto}px`, minWidth: '0' });
    if (acc) Object.assign(acc.style, { flex: '0 1 auto', marginLeft: 'auto', marginTop: '0', gridColumn: 'auto', justifyContent: 'flex-end', minWidth: '0' });
  }
  return lista;
}

export function franjaCifras(items = [], { etiqueta = 'Filtrar' } = {}) {
  return h('nav', { class: 'chips-f', 'data-franja-cifras': '', 'aria-label': etiqueta },
    items.filter(Boolean).map(x => h('button', { type: 'button', 'aria-pressed': x.alPulsar ? String(!!x.activo) : null, title: x.titulo || null,
      disabled: x.alPulsar ? null : true, on: x.alPulsar ? { click: () => x.alPulsar() } : {} },
    x.etiqueta, x.valor !== undefined && x.valor !== null ? h('span', { class: `cu${x.estado === 'rojo' ? ' rojo' : ''}` }, String(x.valor)) : null)));
}

