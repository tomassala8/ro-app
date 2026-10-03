// modulos/_trabajo_ancho.js · Ronda U · U3 (3-oct): variante a todo el ancho del molde común (modulos/_trabajo.js).
//
// Para pantallas cuya lista de trabajo es una TABLA ANCHA (Salud del CRM, Captación, SEO y webs, Outreach): partirla en
// 2/3 + 1/3 la obligaría a desplazarse en horizontal. Misma regla de aceptación que el molde (la primera fila accionable a
// menos de 300 px, a 1440 y a 390): arriba la franja de cifras y las pestañas con la lista; DEBAJO, plegado en una línea,
// «Contexto y cifras» con «Lo primero hoy», las tarjetas grandes y «cómo se mide»; y el consejo de la IA, plegado, detrás
// (lo coloca consejoCompacto: nunca queda encima de la lista).
//
//   pantallaAncha({ id, filtros, lista, contexto: [nodos], tituloContexto, abiertoContexto })
//     → <div data-trabajo="<id>" data-trabajo-ancho> con el.lista y el.contexto.
//
// Diseño estricto: solo clases comunes (pila, que-es) y tokens.

import { h } from '../componentes.js';
import { consejoCompacto } from './_trabajo.js';

export function pantallaAncha(o = {}) {
  const lista = h('div', { class: 'pila', 'data-trabajo-lista': '', style: { minWidth: '0', gap: 'var(--s-3)' } }, o.filtros || null, o.lista || null);
  const hueco = h('div', { 'data-trabajo-consejo': '', style: { minWidth: '0' } });
  const nodos = (Array.isArray(o.contexto) ? o.contexto : [o.contexto]).filter(Boolean);
  // El consejo de la IA: consejoCompacto (de _trabajo.js) lo deja plegado justo DESPUÉS de esta pantalla (hijo directo de
  // #main, como pide la carcasa). Sin nodos de contexto no se pinta el plegable vacío.
  const contexto = nodos.length ? h('details', { class: 'que-es', 'data-trabajo-contexto': '', open: o.abiertoContexto ? true : null, style: { minWidth: '0' } },
    h('summary', {}, o.tituloContexto || 'Contexto y cifras'),
    h('div', { class: 'pila', style: { marginTop: 'var(--s-3)', gap: 'var(--s-4)', minWidth: '0' } }, ...nodos)) : null;
  const el = h('div', { class: 'pila', 'data-trabajo': o.id || '', 'data-trabajo-ancho': '', style: { minWidth: '0', gap: 'var(--s-4)' } }, lista, contexto, hueco);
  el.lista = lista; el.contexto = contexto;
  queueMicrotask(() => consejoCompacto(el, hueco));
  return el;
}

/** franjaEnLinea(franja) · la franja de cifras en UNA línea (48 px) también en el móvil: lo que no cabe se desliza dentro de
 *  la propia franja (la página no se desplaza en horizontal). Devuelve la misma franja. */
export function franjaEnLinea(f) {
  if (!f) return f;
  Object.assign(f.style, { flexWrap: 'nowrap', overflowX: 'auto', minWidth: '0', maxWidth: '100%', paddingBottom: 'var(--s-1)' });
  f.querySelectorAll('button').forEach(b => Object.assign(b.style, { whiteSpace: 'nowrap', flex: 'none' }));
  return f;
}
