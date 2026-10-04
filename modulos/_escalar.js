// modulos/_escalar.js · «Pedir ayuda / Escalar» con el orden de escalado oficial de RO (Tomás, 3-oct-2026).
//
// Un solo diálogo para toda la app: el botón de la cabecera (carcasa.js, en cualquier pantalla: ficha, tareas, Mi día…),
// el chat del equipo, «Algo va mal» (ayudas.js) y quien quiera llamarlo. Pregunta el tipo en una línea y lo manda a la
// persona correcta como mensaje directo en el chat de la app, con el contexto (cliente, pantalla y qué pasa).
// A quién va cada tipo lo dice el servidor (GET /api/canales/escalado ← escalado.py ← data/escalado.json): aquí no hay
// ningún nombre escrito. «Nadie lo resuelve» llega a Mili con el botón «Pasar a Tomás» (lo pinta chat_equipo.js).
//
// Uso:  import { abrirPedirAyuda, botonPedirAyuda } from './_escalar.js';
//       abrirPedirAyuda({ api, contexto: { cliente_id, cliente, pantalla, ruta }, soloLectura, tipo });
import { h, icono, avisoFlotante } from '../componentes.js';

let _tipos = null;     // caché por persona (quien mira): { clave, datos }

async function leerTipos(api) {
  const est = window.RO?.estado;
  const clave = `${est?.real?.id}|${est?.persona?.id}`;
  if (_tipos?.clave === clave) return _tipos.datos;
  const datos = await api('canales/escalado');
  _tipos = { clave, datos };
  return datos;
}

/** Contexto de la pantalla actual: título, ruta y cliente si la ruta lo lleva (#/ficha/<cliente>/…). */
export function contextoActual() {
  const ruta = (location.hash || '#/').split('?')[0].slice(0, 200);
  const [, id, p1] = ruta.replace(/^#/, '').split('/');
  const conCliente = new Set(['ficha', 'en-rojo', 'captacion', 'seo-web', 'redes', 'clientes-nuevos', 'informe-cliente', 'paneles', 'dinero-cliente', 'bandeja']);
  let cliente_id = null;
  try { if (conCliente.has(id) && p1 && !p1.startsWith('t-')) cliente_id = decodeURIComponent(p1); } catch { cliente_id = null; }
  return { pantalla: document.getElementById('titulo')?.textContent || id || '', ruta, cliente_id };
}

export function abrirPedirAyuda({ api, contexto = {}, soloLectura = false, tipo = null, alEnviar } = {}) {
  api = api || window.RO?.api;
  if (!api) return;
  const previo = document.activeElement;
  document.getElementById('pedir-ayuda')?.remove();
  const estado = h('p', { class: 'sub', role: 'status', 'aria-live': 'polite' });
  const zona = h('div', { class: 'pila' }, h('p', { class: 'sub' }, 'Cargando a quién va cada cosa…'));
  const cerrar = () => { fondo.remove(); previo?.focus?.(); };
  const caja = h('div', { class: 'paleta dialogo', role: 'dialog', 'aria-modal': 'true', 'aria-labelledby': 'pedir-ayuda-t' },
    h('div', { class: 'dialogo-cab' },
      h('div', {}, h('h2', { id: 'pedir-ayuda-t' }, 'Pedir ayuda'),
        h('p', {}, 'Elige qué te pasa y le llega a la persona que toca, en un mensaje directo del chat de la app, con esta pantalla y el cliente.')),
      h('button', { type: 'button', class: 'bt icono', 'aria-label': 'Cerrar', on: { click: cerrar } }, icono('cerrar'))),
    zona);
  const fondo = h('div', { class: 'paleta-fondo dialogo-fondo', id: 'pedir-ayuda' }, caja);
  fondo.addEventListener('click', e => { if (e.target === fondo) cerrar(); });
  fondo.addEventListener('keydown', e => {
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); cerrar(); return; }
    if (e.key !== 'Tab') return;
    const foc = [...caja.querySelectorAll('button, a[href], input, textarea, select')].filter(x => !x.disabled && x.offsetParent !== null);
    if (!foc.length) return;
    if (e.shiftKey && document.activeElement === foc[0]) { e.preventDefault(); foc[foc.length - 1].focus(); }
    else if (!e.shiftKey && document.activeElement === foc[foc.length - 1]) { e.preventDefault(); foc[0].focus(); }
  });
  document.body.append(fondo);
  caja.querySelector('button')?.focus();

  leerTipos(api).then(d => {
    const tipos = d.tipos || [];
    let elegido = tipos.find(t => t.id === tipo) || null;
    const texto = h('textarea', { id: 'ayuda-texto', rows: 3, maxlength: 1500, placeholder: 'Qué pasa, en una o dos frases (por ejemplo: «El informe de GAC no carga las cifras de Meta desde ayer»)' });
    const quien = h('p', { class: 'sub', 'aria-live': 'polite' });
    const enviar = h('button', { type: 'button', class: 'bt pri', disabled: true }, icono('send'), 'Enviar');
    const pintarQuien = () => {
      enviar.disabled = soloLectura || !elegido;
      if (!elegido) { quien.textContent = 'Elige primero qué te pasa.'; return; }
      quien.replaceChildren(icono('persona', { clase: 's' }), ' Le llega a ', h('b', {}, elegido.para_nombre || 'quien toca'),
        `. ${elegido.por_que || ''}`, elegido.siguiente_nombre ? ` Si no encuentra quién lo resuelva, lo pasa a ${elegido.siguiente_nombre}.` : '');
      enviar.lastChild.textContent = `Enviar a ${elegido.para_nombre || 'quien toca'}`;
    };
    const fila = h('div', { class: 'fila', role: 'radiogroup', 'aria-label': 'Qué te pasa', style: { flexWrap: 'wrap', gap: 'var(--s-2)' } },
      tipos.map(t => {
        const b = h('button', { type: 'button', class: 'bt mini', role: 'radio', 'aria-checked': String(elegido?.id === t.id), title: t.texto,
          on: { click: () => { elegido = t; fila.querySelectorAll('[role=radio]').forEach(x => x.setAttribute('aria-checked', String(x === b))); pintarQuien(); texto.focus(); } } },
        t.corto || t.texto);
        return b;
      }));
    const ctxTxt = [contexto.cliente || contexto.cliente_id ? `Cliente: ${contexto.cliente || contexto.cliente_id}` : null,
      contexto.pantalla ? `Pantalla: ${contexto.pantalla}` : null].filter(Boolean).join(' · ');
    enviar.addEventListener('click', async () => {
      if (soloLectura) { estado.textContent = 'Estás en «ver como»: solo lectura. Lo pide la persona real.'; return; }
      if (!elegido) return;
      if (texto.value.trim().length < 3) { estado.textContent = 'Cuenta en una frase qué pasa.'; texto.focus(); return; }
      enviar.disabled = true; estado.textContent = 'Enviando…';
      try {
        const r = await api('canales/escalar', { metodo: 'POST', cuerpo: { tipo: elegido.id, texto: texto.value.trim(), cliente_id: contexto.cliente_id || null, pantalla: contexto.pantalla || '', ruta: contexto.ruta || '' } });
        window.dispatchEvent(new CustomEvent('ro:avisos'));
        zona.replaceChildren(h('div', { class: 'pila' },
          h('p', {}, h('b', {}, `Enviado a ${r.para_nombre}.`), ' Lo tiene en un mensaje directo del chat, con esta pantalla. La respuesta te llega a la campana.'),
          h('div', { class: 'fila' }, h('a', { class: 'bt', href: `#/chat-equipo/${encodeURIComponent(r.canal_id)}`, on: { click: cerrar } }, icono('chat'), 'Ver la conversación'),
            h('button', { type: 'button', class: 'bt pri', on: { click: cerrar } }, 'Cerrar'))));
        alEnviar?.(r);
      } catch (e) { enviar.disabled = false; estado.textContent = `No se ha enviado: ${e?.message || 'error'}`; }
    });
    zona.replaceChildren(
      h('span', { class: 'campo-et' }, 'Qué te pasa'), fila, quien,
      h('label', { class: 'campo', for: 'ayuda-texto' }, h('span', { class: 'campo-et' }, 'Qué pasa'), texto),
      ctxTxt ? h('p', { class: 'opinion-meta' }, `Va con: ${ctxTxt}`) : null,
      soloLectura ? h('p', { class: 'sub' }, 'Estás en «ver como»: puedes ver a quién iría, pero no se envía nada.') : null,
      h('div', { class: 'fila' }, enviar, estado),
      d.cadena_alertas ? h('p', { class: 'sub' }, `Las alertas que nadie coge siguen la misma cadena: ${d.cadena_alertas}`) : null);
    pintarQuien();
  }).catch(e => zona.replaceChildren(h('p', { class: 'sub' }, `No puedo leer a quién va cada cosa: ${e?.message || 'error'}. Escribe a Mili por el chat.`)));
}

/** Botón listo para poner en una cabecera o una tarjeta. */
export function botonPedirAyuda({ api, contexto, soloLectura, clase = 'bt mini', texto = 'Pedir ayuda' } = {}) {
  return h('button', { type: 'button', class: clase, style: { minHeight: 'var(--s-8)' }, title: 'Pedir ayuda o escalar a quien toca (orden de escalado de RO)',
    on: { click: () => abrirPedirAyuda({ api, contexto: typeof contexto === 'function' ? contexto() : (contexto || contextoActual()), soloLectura }) } },
  icono('sube'), texto);
}

export function avisoSinServidor() { avisoFlotante('Pedir ayuda necesita el servidor de la app.', { icono: 'alert' }); }
