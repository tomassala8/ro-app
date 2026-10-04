// modulos/_plegar_consejo.js · Ronda U (3-oct, carril U2). Molde común (#1): el «Qué haría yo hoy aquí» de la carcasa
// queda plegado en su línea de resumen SIN moverlo de sitio.
//
// Por qué no consejoCompacto() de _trabajo.js: carcasa.js vuelve a pintar el consejo si no lo encuentra como hijo DIRECTO
// de #main (`:scope > [data-ia="consejo"]`); al moverlo dentro del módulo, la carcasa pinta otro, se vuelve a mover… y se
// apilan (visto en la ficha el 3-oct, 05:20). Plegarlo en su sitio da el mismo resultado (una línea, nunca empuja la lista)
// sin ese bucle. Si la carcasa aprende a buscarlo en todo #main, se puede volver a consejoCompacto().
//
//   plegarConsejo(raiz) → vigila #main mientras raiz esté en la página y pliega el consejo (sin tocar la preferencia
//   guardada de la persona: si lo abre, se queda abierto hasta que cambie de pantalla).

import { icono } from '../componentes.js';

function plegar(c) {
  if (c.dataset.u2Plegado) return;
  const lista = c.querySelector('ol.ia-acciones');
  const res = c.querySelector(':scope > .ia-sub');
  const b = c.querySelector('.ia-cab button[aria-controls]');
  c.dataset.u2Plegado = '1';
  c.style.marginBottom = 'var(--s-3)';
  if (!lista || lista.hidden) return;
  lista.hidden = true;
  if (res) res.hidden = false;
  if (b) { b.setAttribute('aria-expanded', 'false'); b.replaceChildren(icono('chev'), 'Ver los consejos'); }
}

export function plegarConsejo(raiz, { despues = false } = {}) {
  const main = document.getElementById('main');
  if (!main) return () => {};
  const mirar = () => {
    if (!raiz.isConnected) { obs.disconnect(); return; }
    const c = main.querySelector(':scope > [data-ia="consejo"]');
    if (c) {
      plegar(c);
      // Sigue siendo hijo directo de main: carcasa no crea un consejo duplicado.
      if (despues && main.lastElementChild !== c) main.append(c);
    }
  };
  const obs = new MutationObserver(mirar);
  obs.observe(main, { childList: true });
  queueMicrotask(mirar);
  return () => obs.disconnect();
}
