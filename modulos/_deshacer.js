// modulos/_deshacer.js · Ronda U (3-oct, cambio #4 del 50): acciones INTERNAS sin «¿Seguro? Sí».
//
// La acción se ve hecha al primer clic y sale «Hecho · Deshacer» durante 8 s. Si nadie pulsa «Deshacer», al acabar el
// plazo se encola de verdad (ctx.accion / ctx.api); si lo pulsa, se anula y no se escribe nada. Si la persona se va de la
// pantalla (cambio de ruta, cierra la pestaña o la deja en segundo plano) antes de los 8 s, lo pendiente se encola en ese
// momento: nunca se pierde una acción que se vio hecha.
//
// El «¿Seguro?» (botonConfirmar de componentes.js) queda SOLO para lo que sale fuera de la app (envíos reales: correo,
// WhatsApp, GoHighLevel…) o borra algo. Hecho, Visto, Lo tengo, Reclamado, Aprobar, A revisión, Correcto… van con esto.
//
//   botonDeshacer({ texto, hecho, alHacer, alDeshacer, alAnular, validar, plazo, mini, pri, icono, soloLectura, atajo, titulo })
//     Botón en su sitio. Clic → «✓ <hecho> · Deshacer (8)» en el mismo hueco. A los 8 s llama a alHacer() (la escritura
//     real; puede ser async y devolver el texto final) y deja «✓ <texto final>». «Deshacer» → vuelve el botón y llama a
//     alAnular(). Si alHacer falla, «No se pudo: …» y el botón vuelve a los 2,5 s.
//     alDeshacer: alias de alAnular (por legibilidad en la llamada). validar(): se llama al pulsar; si devuelve un texto (o
//     lanza), no empieza y enseña ese texto («escribe el motivo»).
//
//   conDeshacer({ mensaje, hacer, optimista, revertir, plazo })
//     Para filas que DESAPARECEN al marcarlas (Lo mío, una alerta resuelta): optimista() las quita al momento, sale el
//     aviso flotante «<mensaje> · Deshacer» abajo, y a los 8 s hacer() escribe. «Deshacer» → revertir(). Un segundo
//     conDeshacer encola el anterior al momento (como Gmail). Devuelve { deshacer(), ya() }.
//
//   pendientes() · cuántas acciones esperan su plazo (para pruebas). encolarTodo() · las escribe ya (lo llama la carcasa
//     al cambiar de ruta; un módulo no lo necesita).
//
// Diseño: solo clases comunes (bt, mini, pri, estado, tostada, confirmar) y tokens. Sin hoja propia.

import { h, icono as ico } from '../componentes.js';

export const PLAZO_DESHACER_MS = 8000;

const PEND = new Set();   // { ya: () => Promise } de todo lo que espera su plazo

/** Escribe ya todo lo pendiente (al salir de la pantalla). */
export function encolarTodo() { for (const p of [...PEND]) { try { p.ya(); } catch { /* cada una lleva su error */ } } }
export const pendientes = () => PEND.size;

let _enganchado = false;
function enganchar() {
  if (_enganchado || typeof window === 'undefined') return;
  _enganchado = true;
  window.addEventListener('hashchange', encolarTodo);
  window.addEventListener('pagehide', encolarTodo);
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') encolarTodo(); });
}

/** Un temporizador de plazo con su cuenta atrás; ya() ejecuta antes de tiempo, anular() lo cancela. */
function plazoDe(ms, { alTic, alFin }) {
  enganchar();
  let restan = Math.ceil(ms / 1000), hecho = false;
  const tic = setInterval(() => { restan -= 1; if (restan > 0) alTic?.(restan); }, 1000);
  const fin = setTimeout(() => ya(), ms);
  const parar = () => { clearInterval(tic); clearTimeout(fin); PEND.delete(obj); };
  function ya() { if (hecho) return null; hecho = true; parar(); return alFin(); }
  const obj = { ya, anular: () => { if (hecho) return false; hecho = true; parar(); return true; } };
  PEND.add(obj);
  return obj;
}

export function botonDeshacer(o = {}) {
  const plazo = o.plazo ?? PLAZO_DESHACER_MS;
  const caja = h('span', { class: 'confirmar', 'data-deshacer': '' });
  const cls = `bt${o.mini === false ? '' : ' mini'}${o.pri ? ' pri' : ''}`;
  const anular = o.alAnular || o.alDeshacer;
  const inicial = () => {
    const b = h('button', { type: 'button', class: `${cls}${o.texto === '' && o.icono ? ' icono' : ''}`, 'aria-label': o.etiqueta || (o.texto === '' ? (o.titulo || o.hecho || null) : null), 'data-atajo': o.atajo || null, title: o.soloLectura ? 'Estás en «ver como»: solo lectura' : (o.titulo || null),
      'aria-disabled': o.soloLectura ? 'true' : null, on: { click: () => { if (o.soloLectura) return; const mal = validar(); if (!mal) hacer(); } } },
    o.icono ? ico(o.icono, { clase: 's' }) : null, o.texto ?? 'Hecho');   // texto '' + icono = solo icono
    caja.replaceChildren(b);
    return b;
  };
  // validar(): antes de empezar (p. ej. «escribe el motivo»). Si devuelve texto o lanza, no se hace nada y se dice por qué.
  const validar = () => {
    let msg = null;
    try { const r = o.validar?.(); if (typeof r === 'string' && r) msg = r; } catch (e) { msg = e?.message || String(e); }
    if (!msg) return null;
    caja.querySelector('.estado.error')?.remove();
    caja.append(h('span', { class: 'estado error', role: 'alert' }, msg));
    return msg;
  };
  const hacer = () => {
    const txtHecho = o.hecho || 'Hecho';
    const cuenta = h('span', { class: 'sub' }, `(${Math.ceil(plazo / 1000)})`);
    const des = h('button', { type: 'button', class: 'bt mini', 'aria-label': `Deshacer: ${o.etiqueta || txtHecho}`, on: { click: () => {
      if (t.anular()) { try { anular?.(); } catch { /* nada */ } inicial().focus(); }
    } } }, 'Deshacer', cuenta);
    caja.replaceChildren(h('span', { class: 'estado', role: 'status' }, `✓ ${txtHecho}`), des);
    des.focus({ preventScroll: true });
    const t = plazoDe(plazo, {
      alTic: n => { cuenta.textContent = `(${n})`; },
      alFin: async () => {
        try {
          const msg = await o.alHacer?.();
          caja.replaceChildren(h('span', { class: 'estado', role: 'status' }, `✓ ${typeof msg === 'string' && msg ? msg : txtHecho}`));
        } catch (err) {
          caja.replaceChildren(h('span', { class: 'estado error', role: 'alert' }, `No se pudo: ${err?.message || err}`));
          setTimeout(() => { if (caja.isConnected) inicial(); }, 2500);
        }
      },
    });
  };
  inicial();
  return caja;
}

let _actual = null;   // el conDeshacer que enseña el aviso flotante ahora
export function conDeshacer({ mensaje = 'Hecho', hacer, optimista, revertir, plazo = PLAZO_DESHACER_MS } = {}) {
  if (_actual) _actual.ya();   // el anterior se escribe ya: un solo aviso a la vez
  try { optimista?.(); } catch { /* la vista se arregla al repintar */ }
  document.querySelector('.tostada')?.remove();
  const cuenta = h('span', {}, ` (${Math.ceil(plazo / 1000)})`);
  const des = h('button', { type: 'button', class: 'bt mini', style: { marginLeft: 'var(--s-2)' }, 'aria-label': `Deshacer: ${mensaje}` }, 'Deshacer', cuenta);
  const el = h('div', { class: 'tostada', role: 'status', 'aria-live': 'polite', 'data-deshacer': '' }, ico('ok', { clase: 's' }), h('span', {}, mensaje), des);
  document.body.append(el);
  const quitar = () => { el.remove(); if (_actual === yo) _actual = null; };
  const t = plazoDe(plazo, {
    alTic: n => { cuenta.textContent = ` (${n})`; },
    alFin: async () => {
      quitar();
      try { await hacer?.(); }
      catch (err) {
        try { revertir?.(); } catch { /* nada */ }
        const e = h('div', { class: 'tostada', role: 'alert' }, ico('alert', { clase: 's' }), `No se pudo: ${err?.message || err}`);
        document.body.append(e); setTimeout(() => e.remove(), 3000);
      }
    },
  });
  des.addEventListener('click', () => { if (t.anular()) { quitar(); try { revertir?.(); } catch { /* nada */ } } });
  const yo = { ya: () => t.ya(), deshacer: () => des.click() };
  _actual = yo;
  return yo;
}
