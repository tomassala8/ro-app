// modulos/_ir.js · R15a (A2 «Ir al objeto exacto»): al abrir una ruta profunda (#/finanzas/cobros/A-26-117,
// #/seo-web/webs/gac…) la pantalla va a su pestaña y este ayudante RESALTA el objeto, lo lleva al centro y le da el foco.
// · llevarA(raiz, buscar, { foco, alNoEncontrar }) → espera (hasta ~3 s) a que el objeto exista: las pestañas y las tablas
//   se pintan después de render(). Si la tabla está paginada, pulsa «Ver más» hasta dar con él.
// · filaConTexto(raiz, texto) → la fila (tr / li / tarjeta) más pequeña que contiene ese texto.
// Solo tokens: fondo --accent-soft y contorno --accent (sin colores ni px sueltos fuera de la escala).

export function marcar(el, { foco = true } = {}) {
  if (!el) return null;
  el.dataset.irObjetivo = '1';
  el.style.background = 'var(--accent-soft)';
  el.style.outline = '2px solid var(--accent)';
  el.style.outlineOffset = '-2px';
  if (!el.hasAttribute('tabindex') && !/^(A|BUTTON|INPUT|TEXTAREA|SELECT)$/.test(el.tagName)) el.setAttribute('tabindex', '-1');
  try { el.scrollIntoView({ block: 'center' }); } catch { el.scrollIntoView(); }
  if (foco) { try { el.focus({ preventScroll: true }); } catch { /* sin foco */ } }
  // La carcasa mete después bloques arriba («Qué haría yo hoy aquí», avisos): si eso lo saca de la vista y la persona no ha
  // tocado nada (sigue con el foco o sin desplazarse), se vuelve a centrar.
  const y0 = window.scrollY;
  const seguir = () => {
    if (!el.isConnected) return;
    const b = el.getBoundingClientRect();
    const fuera = b.top < 0 || b.bottom > window.innerHeight;
    if (fuera && (document.activeElement === el || window.scrollY === y0)) { try { el.scrollIntoView({ block: 'center' }); } catch { /* nada */ } }
  };
  setTimeout(seguir, 500); setTimeout(seguir, 1300);
  return el;
}

const norm = s => String(s ?? '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/\s+/g, ' ').trim();

/** La fila más pequeña (tr, li, .tarjeta, article) que contiene el texto (sin acentos ni mayúsculas). */
export function filaConTexto(raiz, texto, sel = 'tr, li, article, .tarjeta, details') {
  const t = norm(texto);
  if (!t || !raiz) return null;
  const cand = [...raiz.querySelectorAll(sel)].filter(el => norm(el.textContent).includes(t));
  if (!cand.length) return null;
  return cand.reduce((a, b) => (b.textContent.length < a.textContent.length ? b : a));
}

function verMas(raiz) {
  return [...raiz.querySelectorAll('button')].find(b => /^\s*ver (?:[\d.]+ m[aá]s|las [\d.]+ filas|m[aá]s)/i.test(b.textContent) && !b.disabled && b.offsetParent !== null);
}

/** Espera a que exista el objeto y lo marca. buscar: selector CSS o función raiz => Element|null. */
export function llevarA(raiz, buscar, { foco = true, alNoEncontrar = null, intentos = 30 } = {}) {
  let n = 0;
  return new Promise(res => {
    const paso = () => {
      const el = typeof buscar === 'function' ? buscar(raiz) : raiz.querySelector(buscar);
      // solo cuando ya está en la página (las vistas que se montan tras un await llegan al DOM después)
      if (el && el.isConnected) { res(marcar(el, { foco })); return; }
      const mas = n % 3 === 2 ? verMas(raiz) : null;
      if (mas) mas.click();
      if (++n >= intentos) { if (alNoEncontrar) alNoEncontrar(); res(null); return; }
      setTimeout(paso, 100);
    };
    requestAnimationFrame(paso);
  });
}
