// modulos/ia_componentes.js · N3 · IA en la app de RO (2-oct-2026). Componentes para cualquier módulo.
//
// El servidor (ia.py, rutas /api/ia/*) arma el contexto con lo que ESA persona puede ver; el navegador solo manda ids.
// Nada se envía: el borrador se revisa, se edita y «Usar» lo pasa a la caja de respuesta (que sigue en simulación).
//
//   import { botonIA, panelCopiloto, bloqueCopiloto, iaDe } from './ia_componentes.js';
//
//   botonIA(ctx, { ticket, destino })
//       «Sugerir respuesta». ticket = número de Desk («RO-6627») o id de la Bandeja. destino = el <textarea> de la
//       respuesta (Bandeja: el de id «bdj-texto»); «Usar» le pone el texto y lanza «input». Sin destino (ficha),
//       «Usar» copia el texto y ofrece «Contestar en la Bandeja».
//   panelCopiloto(ctx, clienteId, { compacto })
//       «Qué haría hoy»: diagnóstico en 3 líneas y 3 acciones con su porqué, el dato y «Ver la prueba».
//       Para la pestaña Resumen de la ficha.
//   bloqueCopiloto(ctx, { max })
//       Para «Mi día» del account: sus clientes con propuesta, el color y la primera acción (abre la pantalla).
//   iaDe(ctx) → { estado(), borrador(ticket, nuevo), copiloto(clienteId, nuevo), lista() }   (lo que pediría ctx.ia)
//
// Enganche en 1 línea (dueños de Bandeja, Ficha y Mi día): ver _ESTADO_ia.md.

import { h, icono, chipEstado, vacio, avisoFlotante, copiar, iniciales, panel, fechaCorta as diaMes } from '../componentes.js';
import { conTickets } from './_legible.js';   // R15a: los RO-xxxx de Desk dentro de un consejo, como enlace a ese correo

// Ronda 10 (E0): la hoja de este fichero vive en estilos.css («IA · ia_componentes.js»). estilos() se queda vacía para no
// romper a quien la llame.
export function estilos() { /* sin <style> propio (auditoría 30) */ }

// V2-B (A1): una sola vara. El servidor manda el color de la gravedad de la verdad única (dato critico/atencion/bien) y
// aquí se nombra con el glosario de toda la app (44 §2.1): «Crítico / Vigilar / Bien». Nunca «Rojo» ni «Atención».
const COLOR = { rojo: ['rojo', 'Crítico'], ambar: ['ambar', 'Vigilar'], verde: ['verde', 'Bien'] };
export const ETIQUETA_GRAVEDAD = COLOR;

/** Lo que sería ctx.ia: llamadas al servidor con la identidad de la sesión (nunca datos, solo ids). */
export function iaDe(ctx) {
  return {
    estado: () => ctx.api('ia/estado'),
    lista: () => ctx.api('ia/lista'),
    borrador: (ticket, nuevo = false) => ctx.api('ia/borrador', { metodo: 'POST', cuerpo: { ticket, nuevo } }),
    copiloto: (cliente_id, nuevo = false) => ctx.api('ia/copiloto', { metodo: 'POST', cuerpo: { cliente_id, nuevo } }),
    // 4-oct · cerebros de área: buscar y leer una ficha va SIN IA; adaptarla a un cliente, con IA (si hay clave)
    cerebroBuscar: q => ctx.api(`ia/cerebro?q=${encodeURIComponent(q)}`),
    cerebroFicha: id => ctx.api(`ia/cerebro?id=${encodeURIComponent(id)}`),
    cerebroAdaptar: (id, cliente = null, pregunta = '') => ctx.api('ia/cerebro', { metodo: 'POST', cuerpo: { id, cliente, pregunta } }),
  };
}

const cargando = texto => h('div', { class: 'ia-cargando', role: 'status' }, h('i'), h('i'), h('i'), texto);

function selloOrigen(r) {
  if (r.origen === 'vivo') return chipEstado('verde', `IA en vivo · ${r.generado?.slice(11, 16) || ''}`.trim());
  if (r.origen === 'precalculado') return chipEstado('ambar', `Precalculado · ${fechaCorta(r.generado)}`);
  return chipEstado('gris', 'IA sin conectar');
}
/** «2-oct, 17:34» (44 §2.3): el día con el formato común y la hora tal cual llega. */
function fechaCorta(t) {
  const s = String(t || '');
  if (!/^\d{4}-\d{2}-\d{2}/.test(s)) return s;
  const hm = s.slice(11, 16);
  return `${diaMes(s.slice(0, 10))}${/^\d\d:\d\d$/.test(hm) ? `, ${hm}` : ''}`;
}
/** F9 · «Mili: …» / «A Mili hoy: …» → «Escalar a Mili: …» / «Escalar a Mili hoy: …» (nunca «Escalar: Mili:»). */
export function textoEscalar(t) {
  const s = String(t || '').trim();
  const m = s.match(/^(?:a\s+)?([^:]{2,40}?):\s*(.+)$/is);
  return m && /^[A-ZÁÉÍÓÚÑ]/.test(m[1].trim()) ? { cab: `Escalar a ${m[1].trim()}: `, resto: m[2] } : { cab: 'Escalar: ', resto: s };
}
// 3-oct · cerebro de respuestas: nota «calidad del borrador» (la calcula el servidor) con el tipo de correo y lo que falta
function calidadIA(r) {
  const c = r?.calidad;
  if (!c || typeof c.nota !== 'number') return null;
  const tono = c.nivel === 'lista' ? 'verde' : c.nivel === 'revisar' ? 'ambar' : 'rojo';   // con datos por completar, nunca en verde
  const faltas = (c.faltas || []).filter(Boolean);
  return h('div', { class: 'ia-calidad', role: 'note' },
    h('p', { class: 'ia-sub' }, chipEstado(tono, `Calidad del borrador ${c.nota}/100${c.por_completar ? ` · ${c.por_completar} ${c.por_completar === 1 ? 'dato' : 'datos'} por completar` : ''}`), ' ',
      r.tipo_nombre ? `Tipo: ${r.tipo_nombre}.` : '', r.recomendacion ? ` ${r.recomendacion}` : ''),
    faltas.length ? h('details', {}, h('summary', { class: 'ia-sub', style: { minHeight: 'var(--s-8)', paddingBlock: 'var(--s-2)', cursor: 'pointer' } },
      `Lo que falta (${faltas.length})`), h('ul', { class: 'ia-lista' }, faltas.map(f => h('li', {}, f)))) : null);
}

function avisoIA(texto) {
  return h('div', { class: 'ia-aviso', role: 'note' }, icono('alert'), h('span', {}, texto));
}
function sinIA(motivo, { titulo = 'IA sin conectar', quien = 'Tomás' } = {}) {
  return vacio({ icono: 'spark', tono: 'aviso', titulo, texto: motivo || 'No hay propuesta todavía.', quien });
}
function error(e) {
  if (e?.status === 403) return vacio({ icono: 'candado', titulo: 'No es de tu cartera', texto: e.message });
  return vacio({ icono: 'alert', tono: 'aviso', titulo: 'No se ha podido pedir', texto: e?.message || String(e) });
}

// =================================================================== borrador
/**
 * botonIA(ctx, { ticket, destino, abierto })
 * Devuelve un elemento con el botón «Sugerir respuesta» que, al pulsar, pinta el borrador editable.
 * abierto: true lo pide al pintar (pantalla Asistente IA).
 */
export function botonIA(ctx, { ticket, destino = null, abierto = false } = {}) {
  estilos();
  const ia = iaDe(ctx);
  const raiz = h('div', { class: 'ia-boton', 'data-ia': 'borrador' });
  const zona = h('div', { 'aria-live': 'polite' });
  const boton = h('button', { type: 'button', class: 'bt', on: { click: () => pedir(false) } }, icono('spark'), 'Sugerir respuesta');
  raiz.append(h('div', { class: 'ia-acc' }, boton, h('span', { class: 'ia-sub' }, 'Borrador en la voz de RO con el hilo y el estado del cliente. Lo revisas tú; no se envía nada.')), zona);

  async function pedir(nuevo) {
    boton.disabled = true;
    zona.replaceChildren(cargando(nuevo ? 'Pidiendo otra versión…' : 'Preparando el borrador…'));
    try {
      const r = await ia.borrador(ticket, nuevo);
      pintar(r);
    } catch (e) { zona.replaceChildren(error(e)); }
    finally { boton.disabled = false; }
  }

  function pintar(r) {
    if (!r.ok) { zona.replaceChildren(sinIA(r.motivo)); return; }
    boton.hidden = true;
    raiz.querySelector('.ia-sub')?.remove();
    const asunto = h('input', { type: 'text', id: `ia-asunto-${ticket}`, value: r.asunto || '' });
    const cuerpo = h('textarea', { id: `ia-cuerpo-${ticket}`, spellcheck: 'true' });
    cuerpo.value = r.cuerpo || '';
    const ajustar = () => { cuerpo.style.height = 'auto'; cuerpo.style.height = Math.min(cuerpo.scrollHeight + 4, 560) + 'px'; };
    cuerpo.addEventListener('input', ajustar);
    requestAnimationFrame(ajustar);
    const usar = async () => {
      const texto = cuerpo.value.trim();
      if (!texto) { avisoFlotante('El borrador está vacío', { icono: 'alert' }); return; }
      if (destino) {
        destino.value = texto;
        destino.dispatchEvent(new Event('input', { bubbles: true }));
        destino.focus();
        avisoFlotante('Borrador en la caja de respuesta: revísalo antes de enviar');
      } else {
        await copiar(texto, 'Borrador copiado');
      }
      ctx.rastro?.({ accion: 'ia_usar', objeto: r.ticket, detalle: { origen: r.origen, editado: texto !== (r.cuerpo || '').trim() } });
    };
    const descartar = () => {
      ctx.rastro?.({ accion: 'ia_descartar', objeto: r.ticket });
      zona.replaceChildren();
      boton.hidden = false;
      boton.focus();
    };
    const puntos = (r.puntos_del_cliente || []).filter(p => p?.punto);
    const huecos = (r.huecos || []).filter(Boolean);
    zona.replaceChildren(h('div', { class: 'ia-caja' },
      h('div', { class: 'ia-cab' }, h('b', {}, icono('spark'), 'Borrador sugerido'), selloOrigen(r)),
      r.aviso ? avisoIA(r.aviso) : null,
      r.origen === 'precalculado' && r.motivo_conexion ? h('p', { class: 'ia-sub' }, r.motivo_conexion) : null,
      calidadIA(r),
      h('div', { class: 'ia-campo' }, h('label', { for: asunto.id }, 'Asunto'), asunto),
      h('div', { class: 'ia-campo' }, h('label', { for: cuerpo.id }, 'Respuesta (edítala a tu gusto)'), cuerpo),
      h('div', { class: 'ia-firma' }, h('span', { class: 'av', 'aria-hidden': 'true' }, iniciales(r.firma?.nombre)),
        h('span', {}, `Sale con la firma de Desk de ${r.firma?.alias || r.firma?.nombre || 'quien responde'}.`, r.nota_firma ? ' ' + r.nota_firma : '')),
      huecos.length ? h('div', {}, h('p', { class: 'ia-sub' }, h('b', {}, `Antes de enviar, completa ${huecos.length === 1 ? 'esto' : 'estas ' + huecos.length + ' cosas'}:`)),
        h('ul', { class: 'ia-lista ia-huecos' }, huecos.map(x => h('li', {}, conTickets(x))))) : null,
      puntos.length ? h('details', {}, h('summary', { class: 'ia-sub', style: { minHeight: 'var(--s-8)', paddingBlock: 'var(--s-2)', cursor: 'pointer' } }, `Qué pedía el cliente y cómo queda (${puntos.length})`),
        h('ul', { class: 'ia-lista' }, puntos.map(p => h('li', {}, conTickets(p.punto), ' ', h('span', {}, conTickets(`→ ${p.como_queda || ''}`)))))) : null,
      h('p', { class: 'ia-sub' }, r.contexto_usado ? `Contexto: ${r.contexto_usado.hilo ? `${r.contexto_usado.mensajes} ${r.contexto_usado.mensajes === 1 ? 'mensaje' : 'mensajes'} del hilo` : 'sin hilo (solo el asunto)'}${r.contexto_usado.verdad ? ' y el estado del cliente' : ''}.` : ''),
      h('div', { class: 'ia-acc' },
        h('button', { type: 'button', class: 'bt pri', on: { click: usar } }, icono(destino ? 'send' : 'copy'), destino ? 'Usar este borrador' : 'Copiar el borrador'),
        !destino && ctx.veModulo?.('bandeja') ? h('a', { class: 'bt', href: '#/bandeja' }, icono('inbox'), 'Contestar en la Bandeja') : null,
        h('button', { type: 'button', class: 'bt', disabled: !r.conectada || ctx.soloLectura,
          title: !r.conectada ? 'Llega cuando haya clave de Anthropic' : ctx.soloLectura ? 'En «ver como» no se genera nada' : null,
          on: { click: () => { boton.hidden = false; pedir(true); } } }, icono('recargar'), 'Otra versión'),
        h('button', { type: 'button', class: 'bt', on: { click: descartar } }, icono('cerrar'), 'Descartar'))));
  }

  if (abierto) pedir(false);
  return raiz;
}

// =================================================================== copiloto
/** Una acción del copiloto: qué, porqué, dato y prueba. */
function accionEl(a, i) {
  const p = a.prueba || {};
  const enlaces = [];
  if (p.url) enlaces.push(h('a', { href: p.url, target: '_blank', rel: 'noopener noreferrer' }, icono('ext'), `Ver la prueba en ${limpiaFuente(p.texto)}`));
  if (p.app) enlaces.push(h('a', { href: p.app }, icono('cli'), 'Abrir la ficha'));
  return h('li', { class: 'ia-accion' },
    h('span', { class: 'n', 'aria-hidden': 'true' }, String(i + 1)),
    h('div', {},
      h('b', {}, conTickets(a.que)),
      h('p', {}, conTickets(a.porque, { boton: true })),
      a.dato ? h('div', { class: 'dato' }, icono('grafico'), h('span', {}, conTickets(a.dato, { boton: true }))) : null,
      h('div', { class: 'pie' },
        a.quien ? h('span', { style: { display: 'inline-flex', gap: '4px', alignItems: 'center' } }, icono('persona'), a.quien) : null,
        a.cuando ? h('span', { style: { display: 'inline-flex', gap: '4px', alignItems: 'center' } }, icono('clock'), a.cuando) : null,
        ...enlaces)));
}
const limpiaFuente = t => String(t || 'la fuente').replace(/\s*\(.*?\)\s*/g, ' ').trim().slice(0, 40);

/** panelCopiloto(ctx, clienteId, { compacto }) · «Qué haría hoy» de un cliente (pestaña Resumen de la ficha). */
export function panelCopiloto(ctx, clienteId, { compacto = false } = {}) {
  estilos();
  const ia = iaDe(ctx);
  const cuerpo = h('div', { class: 'cuerpo ia-cop', 'aria-live': 'polite' }, cargando('Pensando qué haría hoy…'));
  const acciones = h('span', { class: 'ia-acc' });
  const caja = h('section', { class: 'panel', 'data-ia': 'copiloto' },
    h('header', {}, h('div', {}, h('h2', {}, icono('spark'), 'Qué haría hoy'), h('p', { class: 'sub' }, 'Copiloto del account · criterio de RO · lo decides tú')), acciones),
    cuerpo);

  async function pedir(nuevo) {
    cuerpo.replaceChildren(cargando(nuevo ? 'Pidiendo otra propuesta…' : 'Pensando qué haría hoy…'));
    try { pintar(await ia.copiloto(clienteId, nuevo)); }
    catch (e) { cuerpo.replaceChildren(error(e)); }
  }
  function pintar(r) {
    acciones.replaceChildren();
    if (!r.ok) { cuerpo.replaceChildren(sinIA(r.motivo, { titulo: r.conectada ? 'Sin propuesta todavía' : 'IA sin conectar' })); return; }
    const [cls, txt] = COLOR[r.color] || ['gris', 'Sin color'];
    acciones.append(selloOrigen(r));
    // Glosario: un diagnóstico precalculado que empieza por el color («Rojo: …») se lee con el nivel («Crítico: …»).
    const NIVEL = { rojo: 'Crítico', ámbar: 'Vigilar', ambar: 'Vigilar', verde: 'Bien' };
    const diag = (r.diagnostico || []).filter(d => d && d !== 'null').slice(0, 3)
      .map(d => String(d).replace(/^(rojo|ámbar|ambar|verde)\s*:/i, (m, c) => `${NIVEL[c.toLowerCase()]}:`));
    const escalar = r.escalar && r.escalar !== 'null' ? r.escalar : null;
    // C4 / barrido v1: replaceChildren() escribe «null» si recibe null (h() no). Por eso se filtra antes de pintar.
    cuerpo.replaceChildren(...[
      h('div', { class: 'ia-cab' }, (c => { c.setAttribute('aria-label', `Estado del cliente: ${txt}`); return c; })(chipEstado(cls, txt)), h('span', { class: 'ia-sub' }, 'Estado del cliente en la verdad única: el mismo que En rojo y la ficha'),
        r.para && r.para !== ctx.persona?.id ? h('span', { class: 'ia-sub' }, `Pensado para ${ctx.nombre?.(r.para) || r.para}`) : null),
      h('ul', { class: 'ia-diag', 'aria-label': 'Diagnóstico' }, diag.map((d, i) => h('li', {}, icono(i === 0 ? 'medidor' : 'info'), h('span', {}, conTickets(d, { boton: true }))))),
      h('ol', { class: 'ia-acciones', style: { listStyle: 'none', margin: 0, padding: 0 }, 'aria-label': 'Tres acciones propuestas' },
        (compacto ? (r.acciones || []).slice(0, 1) : (r.acciones || [])).filter(Boolean).map(accionEl)),
      escalar ? (e => h('div', { class: 'ia-escalar', role: 'note' }, icono('flag'), h('span', {}, h('b', {}, e.cab), conTickets(e.resto))))(textoEscalar(escalar)) : null,
      r.aviso ? avisoIA(r.aviso) : null,
      h('div', { class: 'ia-acc' },
        compacto ? h('a', { class: 'bt mini', href: `#/asistente-ia/${encodeURIComponent(clienteId)}` }, icono('derecha'), 'Ver las 3 acciones') : null,
        h('button', { type: 'button', class: 'bt mini', disabled: !r.conectada || ctx.soloLectura,
          title: !r.conectada ? 'Llega cuando haya clave de Anthropic' : ctx.soloLectura ? 'En «ver como» no se genera nada' : null,
          on: { click: () => pedir(true) } }, icono('recargar'), 'Otra propuesta'))].filter(Boolean));
  }
  pedir(false);
  return caja;
}

/** bloqueCopiloto(ctx, { max }) · para «Mi día»: tus clientes con propuesta, el rojo arriba, y la primera acción. */
export function bloqueCopiloto(ctx, { max = 5 } = {}) {
  estilos();
  // C24/M10: es el copiloto del ACCOUNT (cliente a cliente). A quien no lleva cartera de account no se le pinta: su
  // «qué hacer» ya está en «Qué haría yo hoy aquí», arriba de la pantalla.
  if (!(ctx.persona?.puestos || []).includes('account')) return null;
  const cuerpo = h('div', { class: 'cuerpo' }, cargando('Buscando las propuestas de tus clientes…'));
  const caja = h('section', { class: 'panel', 'data-ia': 'bloque' },
    h('header', {}, h('div', {}, h('h2', {}, icono('spark'), 'Tus clientes por gravedad · lo que propone la IA'), h('p', { class: 'sub' }, 'Crítico arriba (la gravedad de la verdad única) y la primera acción de cada uno')),
      h('a', { class: 'bt mini', href: '#/asistente-ia' }, icono('derecha'), 'Ver las propuestas de tus clientes')),
    cuerpo);
  iaDe(ctx).lista().then(l => {
    const xs = (l.copiloto || []).filter(c => !ctx.carteraIds || ctx.carteraIds.has(c.cliente_id) || ctx.nivel === 'todo').slice(0, max);
    if (!xs.length) {
      cuerpo.replaceChildren(vacio({ icono: 'spark', titulo: 'Sin propuestas para tus clientes', texto: l.estado?.conectada ? 'Ábrelas desde la ficha de cada cliente.' : (l.estado?.motivo || ''), quien: l.estado?.conectada ? null : 'Tomás' }));
      return;
    }
    cuerpo.replaceChildren(h('nav', { class: 'ia-bloque', 'aria-label': 'Clientes con propuesta' }, xs.map(c => {
      const [cls, txt] = COLOR[c.color] || ['gris', 'Sin color'];
      return h('a', { href: `#/asistente-ia/${encodeURIComponent(c.cliente_id)}` }, chipEstado(cls, txt), h('span', { class: 't' }, c.nombre || c.cliente_id), h('span', { class: 'd' }, c.primera));
    })));
  }).catch(e => cuerpo.replaceChildren(error(e)));
  return caja;
}

// =================================================================== N12 · consejo por pantalla y «Qué hacer» ante errores
// El servidor (ia.py → /api/ia/consejo) arma 1 a 3 consejos por REGLAS con lo que ESA persona ve (alertas con dueño y
// plazo, bloqueos, fuentes caídas) y, con clave de Anthropic, la IA los redacta y prioriza (POST, nunca en «ver como»).
// La carcasa (carcasa.js) pinta el bloque arriba de cada pantalla y lo oculta si no hay nada útil. Nada se envía:
// el único botón es «Lo tengo», que va a la cola simulada de Alertas con rastro.
//
//   bloqueConsejo(r, { soloLectura, plegado, alPlegar, alAccion })   r = respuesta de /api/ia/consejo
//   queHacerPara(texto, tabla, { error })  → { texto, quien } | null   (tabla = r.que_hacer)
//   enriquecerErrores(raiz, tabla)         añade «Qué hacer» a vacíos, «Sin dato» y errores que no lo traen

const EN_LINEA = { display: 'inline-flex', gap: '4px', alignItems: 'center' };
/** V1 · un botón dice verbo + objeto. Lo viejo precalculado («Ir a «Hoy»», «Ir a las respuestas») pasa a «Ver …». */
const textoIr = t => (!t ? '' : String(t).replace(/^Ir a «([^»]+)»$/, 'Ver la lista «$1»').replace(/^Ir a (las?|los?|el)\s/i, 'Ver $1 '));
/** Un consejo en una fila: qué, porqué, cifra y umbral, quién y cuándo, «Ver fuente ↗», «Ir» y «Lo tengo». */
/** «Ir a «Llamar ya»»: deja elegida la pestaña (la misma clave de sesión que usa pestanas()) y, si ya estás en esa
 *  pantalla, la pulsa; si no, navega y la pantalla abre en ella. */
function irPestana(c) {
  try { sessionStorage.setItem(`ro.pestana.${c.pestana.sesion}`, c.pestana.id); } catch { /* sin almacenamiento */ }
  const tab = [...document.querySelectorAll('#main [role="tab"]')].find(b => b.id.endsWith(`-${c.pestana.id}`));
  if (tab && (location.hash || '').split('?')[0] === c.ir) { tab.click(); tab.focus(); return; }
  location.hash = c.ir;
}
/** «Avisar a X» de un consejo delegado: va a la cola simulada con rastro (nada sale de la app). */
async function avisar(c, pantalla) {
  if (!window.RO?.api) throw new Error('Sin servidor');
  return window.RO.api('acciones', { metodo: 'POST', cuerpo: {
    modulo: pantalla, herramienta: 'app', tipo: 'avisar', objeto: String(c.accion.objeto || c.id), cliente_id: c.cliente_id || null,
    texto: `${c.que} · ${c.porque || ''}`.slice(0, 400), vista_previa: { para: c.accion.persona, consejo: c.id, que: c.que, desde: 'consejo' } } });
}
function consejoEl(c, i, { soloLectura, alAccion, aqui, pantalla }) {
  const conPestana = c.pestana?.id && c.ir;
  const pie = [
    h('span', { style: EN_LINEA }, icono('persona'), c.quien || '—'),
    h('span', { style: EN_LINEA }, icono('clock'), c.cuando || '—'),
    c.fuente?.url ? h('a', { href: c.fuente.url, target: '_blank', rel: 'noopener noreferrer', title: c.fuente.texto }, 'Ver fuente ↗')
      : h('span', { title: 'Sale de la app: no hay una pantalla externa que abrir' }, c.fuente?.texto || 'Fuente: la app'),
    // «Ir» a la misma pantalla no lleva a nada. A2: lleva al OBJETO (el correo, la ficha en su pestaña…), con su verbo.
    conPestana ? h('button', { type: 'button', class: 'bt mini', 'data-ir': 'pestana', on: { click: () => irPestana(c) } }, icono('derecha'), textoIr(c.ir_texto) || `Ver la lista «${c.pestana.texto}»`)
      : c.ir && !aqui.includes(c.ir) ? h('a', { href: c.ir, 'data-ir': 'objeto' }, icono('derecha'), textoIr(c.ir_texto) || 'Ver el detalle') : null,
  ];
  if (c.accion?.tipo === 'avisar') {
    // V2-B: consejo de su equipo («Pide a X…»): el botón avisa a esa persona (cola simulada con rastro), no la sustituye
    const b = h('button', { type: 'button', class: 'bt mini', disabled: soloLectura || null,
      title: soloLectura ? 'En «ver como» no se avisa a nadie' : 'Queda en la cola de acciones (simulada) y en el rastro' }, icono('campana'), c.accion.texto || 'Avisar');
    b.addEventListener('click', async () => {
      b.disabled = true;
      try { await avisar(c, pantalla); b.replaceChildren(icono('ok'), 'Avisado'); }
      catch (e) { b.disabled = false; b.title = e?.message || String(e); b.replaceChildren(icono('alert'), 'No se pudo'); }
    });
    pie.push(b);
  } else if (c.accion?.tipo) {
    const b = h('button', { type: 'button', class: 'bt mini', disabled: soloLectura || null,
      title: soloLectura ? 'En «ver como» no se marca nada' : 'Se anota en Alertas (cola simulada) y para el escalado' }, icono('ok'), c.accion.texto || 'Lo tengo');
    b.addEventListener('click', async () => {
      b.disabled = true;
      try { await alAccion?.(c); b.replaceChildren(icono('ok'), 'Anotado'); }
      catch (e) { b.disabled = false; b.title = e?.message || String(e); b.replaceChildren(icono('alert'), 'No se pudo'); }
    });
    pie.push(b);
  }
  // V8: sin «Umbral»; la regla ya llega en palabras («Bien con 2 citas al día o más»).
  const dato = [c.cifra, c.umbral ? textoRegla(c.umbral) : null].filter(Boolean).join(' · ');
  return ligarMotivo(h('li', { class: 'ia-accion' },
    h('span', { class: 'n', 'aria-hidden': 'true' }, String(i + 1)),
    h('div', {},
      h('b', {}, conTickets(c.que)),
      h('p', {}, conTickets(c.porque)),
      dato ? h('div', { class: 'dato' }, icono('grafico'), h('span', {}, conTickets(dato))) : null,
      c.dato_en_duda && !String(c.porque || '').includes(c.dato_en_duda) ? h('div', { class: 'dato' }, icono('alert'), h('span', {}, `Dato en duda: ${c.dato_en_duda}`)) : null,
      h('div', { class: 'pie' }, pie.filter(Boolean)),
      fichaConsejo(c.ficha),
      filaValoracion(c, { soloLectura, pantalla, i }))));
}

// ------------------------------------------------------------------ 4-oct · cerebros de área
// Cada consejo trae su ficha de situación (servidor, sin IA): qué hacer hoy, qué comprobar primero y cuándo escalar.
// Plegada por defecto para no alargar la lista; «Ver la ficha entera» abre el Asistente en «Qué hago si…».
function fichaConsejo(f) {
  if (!f?.id) return null;
  const lista = (titulo, xs) => xs?.length ? h('div', {}, h('b', {}, titulo), h('ul', { style: { margin: '4px 0 8px 18px' } }, xs.filter(Boolean).map(x => h('li', {}, x)))) : null;
  return h('details', { class: 'ia-ficha', 'data-ficha': f.id, style: { marginTop: '6px' } },
    h('summary', {}, icono('libro', { clase: 's' }), ' Cómo se resuelve'),
    lista('Hoy', f.hoy), lista('Comprueba primero', f.comprueba),
    f.escalar?.a ? h('p', { class: 'ia-sub' }, `Escala a ${f.escalar.a}: ${f.escalar.cuando || ''}`) : null,
    f.exito ? h('p', { class: 'ia-sub' }, `Resuelto cuando: ${f.exito}`) : null,
    botonFichaEntera(f.id));
}
/** «Ver la ficha entera» dentro del propio consejo (sirve en cualquier pantalla, sin depender del Asistente). */
function botonFichaEntera(id) {
  const zona = h('div');
  const b = h('button', { type: 'button', class: 'bt mini' }, icono('derecha', { clase: 's' }), 'Ver la ficha entera');
  b.addEventListener('click', async () => {
    if (!window.RO?.api) return;
    b.disabled = true; zona.replaceChildren(cargando('Abriendo la ficha…'));
    try { const r = await window.RO.api(`ia/cerebro?id=${encodeURIComponent(id)}`); b.hidden = true; zona.replaceChildren(fichaCompleta(window.RO.api, r.ficha)); }
    catch (e) { b.disabled = false; zona.replaceChildren(error(e)); }
  });
  return h('div', {}, b, zona);
}

/** La ficha entera: síntoma, hoy, diagnóstico, causas, mensajes listos, qué no hacer, escalar y fuentes. */
export function fichaCompleta(api, f, { clienteId = null, pregunta = () => '' } = {}) {
  const sec = (titulo, ...hijos) => hijos.some(Boolean) ? h('div', { style: { marginTop: 'var(--s-3)' } }, h('h4', { style: { font: 'var(--t-h3)' } }, titulo), ...hijos) : null;
  const ul = xs => xs?.length ? h('ul', { style: { margin: '4px 0 0 18px' } }, xs.map(x => h('li', {}, x))) : null;
  const zonaIA = h('div', { 'aria-live': 'polite' });
  const adaptar = h('button', { type: 'button', class: 'bt mini', on: { click: async () => {
    adaptar.disabled = true; zonaIA.replaceChildren(cargando('Adaptando la ficha…'));
    try {
      const r = await api('ia/cerebro', { metodo: 'POST', cuerpo: { id: f.id, cliente: clienteId, pregunta: pregunta() } });
      if (r.origen !== 'vivo') { zonaIA.replaceChildren(avisoIA(r.motivo || 'Sin IA: usa la ficha tal cual, ya está completa.')); return; }
      zonaIA.replaceChildren(h('div', { class: 'ia-caja' }, h('div', { class: 'ia-cab' }, h('b', {}, icono('spark'), 'Para tu caso'), selloOrigen(r)),
        h('p', {}, r.resumen || ''), ul((r.pasos || []).map(p => `${p.que} — ${p.porque}`)),
        r.mensaje ? h('div', {}, h('pre', { style: { whiteSpace: 'pre-wrap', font: 'inherit' } }, r.mensaje),
          h('button', { type: 'button', class: 'bt mini', on: { click: () => copiar(r.mensaje, 'Mensaje copiado') } }, 'Copiar el mensaje')) : null,
        r.escalar ? h('p', { class: 'ia-sub' }, `Escalar: ${r.escalar}`) : null));
    } catch (e) { zonaIA.replaceChildren(error(e)); }
    finally { adaptar.disabled = false; }
  } } }, icono('spark', { clase: 's' }), clienteId ? 'Adaptar a este cliente' : 'Adaptar a mi caso');
  return h('article', { class: 'ia-caja', 'data-ficha': f.id },
    h('div', { class: 'ia-cab' }, h('b', {}, f.titulo), h('span', { class: 'ia-acc' },
      chipEstado(f.gravedad === 'alta' ? 'rojo' : f.gravedad === 'media' ? 'ambar' : 'gris', f.plazo || f.gravedad || ''), adaptar)),
    h('p', {}, f.sintoma || ''),
    sec('Hoy, aunque no sepas la causa', ul(f.acciones_inmediatas)),
    sec('Diagnóstico, en orden', h('ol', { style: { margin: '4px 0 0 18px' } }, (f.diagnostico || []).map(d => h('li', {}, `${d.comprueba}`, d.donde ? h('span', { class: 'ia-sub' }, ` · ${d.donde}`) : null)))),
    sec('Causas y solución', ...(f.causas || []).map(c => h('details', {}, h('summary', {}, c.causa),
      c.como_confirmar ? h('p', { class: 'ia-sub' }, `Cómo confirmarlo: ${c.como_confirmar}`) : null, ul(c.solucion),
      c.quien ? h('p', { class: 'ia-sub' }, `Quién: ${c.quien}${c.plazo ? ` · ${c.plazo}` : ''}`) : null))),
    sec('Mensajes listos', ...(f.guiones || []).map(g => h('details', {}, h('summary', {}, `${g.canal} · para ${g.para} · ${g.cuando || ''}`),
      h('pre', { style: { whiteSpace: 'pre-wrap', font: 'inherit' } }, g.texto),
      h('button', { type: 'button', class: 'bt mini', on: { click: () => copiar(g.texto, 'Mensaje copiado') } }, 'Copiar')))),
    sec('Qué no hacer', ul(f.que_no_hacer)),
    f.escalar?.a ? sec('Cuándo escalar', h('p', {}, `A ${f.escalar.a}: ${f.escalar.cuando || ''}`)) : null,
    f.exito ? sec('Resuelto cuando', h('p', {}, f.exito)) : null,
    zonaIA,
    f.fuentes?.length ? h('details', { style: { marginTop: 'var(--s-3)' } }, h('summary', { class: 'ia-sub' }, `De dónde sale (${f.fuentes.length} fuentes)`),
      ul(f.fuentes.map(x => `${x.autor ? x.autor + ' · ' : ''}${x.fichero}${x.linea ? ':' + x.linea : ''}${x.nota ? ' — ' + x.nota : ''}`))) : null);
}

/**
 * panelCerebro(ctx, { fichaInicial, clienteId })
 * «Qué hago si…»: la persona escribe lo que le pasa y la app le enseña la ficha de situación de los cerebros de área
 * (diagnóstico, causas, guiones, qué no hacer, cuándo escalar). Buscar y leer no gastan IA. Con clave, «Adaptar a este
 * cliente» pide a la IA que ajuste ESA ficha (modelo barato); sin clave, la ficha ya sirve tal cual.
 */
export function panelCerebro(ctx, { fichaInicial = null, clienteId = null, compacto = false } = {}) {
  const ia = iaDe(ctx);
  const entrada = h('input', { type: 'search', placeholder: 'Ej.: los leads no vienen a las citas · el cliente pide la baja · la campaña no gasta',
    'aria-label': 'Qué te pasa', style: { flex: '1 1 260px', minWidth: 0 } });
  const resultados = h('div', { 'aria-live': 'polite' });
  const detalle = h('div', { 'aria-live': 'polite' });
  let t = 0;
  async function buscar() {
    const q = entrada.value.trim();
    if (q.length < 3) { resultados.replaceChildren(); return; }
    resultados.replaceChildren(cargando('Buscando la ficha…'));
    try {
      const r = await ia.cerebroBuscar(q);
      if (!r.fichas?.length) { resultados.replaceChildren(h('p', { class: 'ia-sub' }, 'Sin ficha para eso. Prueba con otras palabras o pregunta a tu responsable.')); return; }
      resultados.replaceChildren(h('ol', { class: 'ia-acciones', style: { listStyle: 'none', margin: 0, padding: 0 } }, r.fichas.map((f, i) =>
        h('li', { class: 'ia-accion' }, h('span', { class: 'n', 'aria-hidden': 'true' }, String(i + 1)),
          h('div', {}, h('button', { type: 'button', style: { font: 'inherit', fontWeight: 600, textAlign: 'left', background: 'none', border: 0, padding: 0, color: 'var(--accent)', cursor: 'pointer' }, on: { click: () => abrir(f.id) } }, f.titulo),
            h('p', { class: 'ia-sub' }, (f.hoy || [])[0] || ''))))));
    } catch (e) { resultados.replaceChildren(error(e)); }
  }
  entrada.addEventListener('input', () => { clearTimeout(t); t = setTimeout(buscar, 350); });
  entrada.addEventListener('keydown', e => { if (e.key === 'Enter') { clearTimeout(t); buscar(); } });

  async function abrir(id) {
    detalle.replaceChildren(cargando('Abriendo la ficha…'));
    try { pintarFicha((await ia.cerebroFicha(id)).ficha); }
    catch (e) { detalle.replaceChildren(error(e)); }
  }
  function pintarFicha(f) { detalle.replaceChildren(f ? fichaCompleta(ctx.api, f, { clienteId, pregunta: () => entrada.value.trim() }) : ''); }
  if (fichaInicial) abrir(fichaInicial);
  const cuerpo = h('div', { class: 'cuerpo' },
    h('div', { style: { display: 'flex', gap: 'var(--s-2)', flexWrap: 'wrap' } }, entrada),
    h('p', { class: 'ia-sub' }, 'Busca en los cerebros de RO (criterio interno, con su fuente). Buscar no gasta IA.'),
    resultados, detalle);
  return compacto ? cuerpo : panel({ titulo: 'Qué hago si…', icono: 'libro', sub: 'Escribe lo que te pasa como se lo dirías a tu responsable' }, cuerpo);
}

// ------------------------------------------------------------------ 3-oct · cerebro de decisiones v2: valoración
// Debajo de cada consejo: por qué va en ese puesto («Primero porque…»), su criterio con «Ver fuente ↗» (la regla de Cole
// Gordon, Hormozi o RO en GitHub), la confianza y los botones «Útil / No útil / Ya hecho». El navegador solo manda el id del
// consejo y el valor; el servidor apunta en el rastro la métrica de ese momento (para ver a 7 y 14 días si mejoró).
const VALORES = [['util', 'Útil'], ['no_util', 'No útil'], ['hecho', 'Ya hecho']];
const CONFIANZA = { alta: ['verde', 'Confianza alta'], media: ['ambar', 'Confianza media'], baja: ['rojo', 'Confianza baja'] };
async function valorar(c, valor, pantalla) {
  if (!window.RO?.api) throw new Error('Sin servidor');
  return window.RO.api('ia/consejo/valorar', { metodo: 'POST', cuerpo: { consejo: c.id, valor, pantalla } });
}
/** Mi día renumera los consejos que quedan tras quitar lo que ya está en «Lo mío»: «Primero / Luego» sigue a ese número. */
function ligarMotivo(li) {
  const n = li.querySelector('.n');
  const m = li.querySelector('[data-motivo]');
  if (!n || !m || typeof MutationObserver === 'undefined') return li;
  const poner = () => { m.textContent = `${n.textContent.trim() === '1' ? 'Primero' : 'Luego'} porque ${m.dataset.motivo}`; };
  new MutationObserver(poner).observe(n, { childList: true, characterData: true, subtree: true });
  return li;
}
function filaValoracion(c, { soloLectura, pantalla, i = 0 }) {
  if (!c?.id) return null;
  // «Primero / Luego» según el sitio en ESTA lista (una pantalla puede quitar alguno que ya está en «Lo mío»)
  const motivo = c.motivo_linea ? String(c.motivo_linea).replace(/^(Primero|Luego) porque/, i === 0 ? 'Primero porque' : 'Luego porque') : null;
  const cr = c.criterio;
  const conf = CONFIANZA[c.confianza];
  const chip = conf ? chipEstado(conf[0], conf[1]) : null;
  if (chip && c.confianza_porque) chip.title = c.confianza_porque;
  const criterio = cr?.regla ? (cr.url
    ? h('a', { href: cr.url, target: '_blank', rel: 'noopener noreferrer', title: cr.regla, 'data-criterio': cr.id }, `Criterio ${cr.autor || 'RO'} · Ver fuente ↗`)
    : h('span', { title: `${cr.regla}${cr.fichero ? ` (${cr.fichero})` : ''}`, 'data-criterio': cr.id }, `Criterio ${cr.autor || 'RO'}${cr.fichero ? ` · ${cr.fichero}` : ''}`)) : null;
  const estado = h('span', { role: 'status', 'aria-live': 'polite' }, c.valoracion_nota || '');
  const botones = VALORES.map(([v, t]) => {
    const b = h('button', { type: 'button', class: 'bt mini', 'data-valorar': v, 'aria-pressed': String(c.valoracion === v),
      disabled: soloLectura || null, title: soloLectura ? 'En «ver como» no se valora nada' : 'Queda en el rastro: sirve para saber qué consejos funcionan' }, t);
    b.addEventListener('click', async () => {
      botones.forEach(x => { x.disabled = true; });
      try {
        await valorar(c, v, pantalla);
        botones.forEach(x => x.setAttribute('aria-pressed', String(x === b)));
        estado.textContent = v === 'hecho' ? 'Anotado: hoy no vuelve a salir; en 7 y 14 días se mira si el dato mejoró.' : 'Anotado, gracias.';
      } catch (e) { estado.textContent = `No se pudo anotar (${e?.message || e}).`; }
      finally { botones.forEach(x => { x.disabled = soloLectura || null; }); }
    });
    return b;
  });
  return h('div', { class: 'pie', 'data-ia': 'valoracion' },
    motivo ? h('span', { style: { flexBasis: '100%' }, 'data-motivo': motivo.replace(/^(Primero|Luego) porque /, '') }, motivo) : null,
    criterio, chip, ...botones, estado);
}

/** Lo viejo precalculado con colores («verde ≥ 2 · ámbar 1 · rojo 0») se lee con el glosario: Bien / Vigilar / Crítico. */
const textoRegla = t => String(t).replace(/\bverde\b/gi, 'bien').replace(/\bámbar\b/gi, 'vigilar').replace(/\brojo\b/gi, 'crítico');
const DIA_CORTO = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'];
/** C30/B12: la hora de los datos con su día («de las 9:16» si es de hoy; «del vie 2-oct, 23:14» si no). */
export function horaDatos(t) {
  const s = String(t || '');
  const d = new Date(s.replace(' ', 'T'));
  if (!s || isNaN(d)) return '';
  const hm = s.slice(11, 16);
  const hoy = new Date();
  return d.toDateString() === hoy.toDateString() ? `de las ${hm}` : `del ${DIA_CORTO[d.getDay()]} ${diaMes(s.slice(0, 10))}, ${hm}`;
}

/** El bloque «Qué haría yo hoy aquí». Devuelve null si no hay consejos (nunca relleno). */
export function bloqueConsejo(r, { soloLectura = false, plegado = false, alPlegar, alAccion } = {}) {
  const xs = (r?.consejos || []).slice(0, 3);
  if (!xs.length) return null;
  const id = `consejo-${Math.random().toString(36).slice(2, 8)}`;
  const vivo = r.origen === 'vivo';
  const lista = h('ol', { id, class: 'ia-acciones', style: { listStyle: 'none', margin: 0, padding: 0 }, 'aria-label': 'Consejos para esta pantalla' },
    xs.map((c, i) => consejoEl(c, i, { soloLectura, alAccion, pantalla: r.pantalla,
      aqui: [`#/${r.pantalla}`, r.cliente_id ? `#/${r.pantalla}/${r.cliente_id}` : null, (typeof location !== 'undefined' ? location.hash : '')].filter(Boolean) })));
  const resumen = h('p', { class: 'ia-sub' }, h('b', {}, xs[0].que), xs.length > 1 ? ` · y ${xs.length === 2 ? '1 consejo más' : `${xs.length - 1} consejos más`}` : '');
  const boton = h('button', { type: 'button', class: 'bt mini', 'aria-controls': id }, '');
  const pintarEstado = p => {
    lista.hidden = p; resumen.hidden = !p;
    boton.setAttribute('aria-expanded', String(!p));
    boton.replaceChildren(...(p ? [icono('chev'), 'Ver los consejos'] : ['Plegar']));
  };
  boton.addEventListener('click', () => { const p = !lista.hidden; pintarEstado(p); alPlegar?.(p); });
  const sello = vivo ? chipEstado('verde', `IA · ${String(r.generado || '').slice(11, 16)}`.trim())
    : chipEstado('gris', `Reglas · datos ${horaDatos(r.generado)}`.trim());
  if (!vivo) sello.title = r.ia?.conectada ? 'La IA lo está redactando' : (r.ia?.motivo || 'Sin clave de Anthropic: salen las reglas, que ya funcionan solas');
  // M1: las fuentes con retraso ya no ocupan un consejo: van aquí, en una sola chapa con el detalle al pasar por encima
  const ret = (r.retrasos || []).filter(x => x?.nombre);
  const selloFuentes = ret.length ? chipEstado('ambar', ret.length === 1 ? `${ret[0].nombre} con retraso` : `${ret.length} fuentes con retraso`) : null;
  if (selloFuentes) { selloFuentes.title = ret.map(x => x.paso).join('\n'); selloFuentes.setAttribute('aria-description', ret.map(x => x.paso).join('. ')); }
  const caja = h('section', { class: 'ia-caja no-imprimir', 'data-ia': 'consejo', 'aria-label': 'Consejo para esta pantalla', style: { marginBottom: '16px' } },
    h('div', { class: 'ia-cab' }, h('b', {}, icono('spark'), 'Qué haría yo hoy aquí'), h('span', { class: 'ia-acc' }, sello, selloFuentes, boton)),
    resumen, lista,
    r.solo_lectura ? h('p', { class: 'ia-sub' }, 'Estás en «ver como»: lo que vería esta persona, sin lo personal y sin marcar nada.') : null);
  pintarEstado(!!plegado);
  return caja;
}

// ------------------------------------------------------------------ «Qué hacer» ante errores, vacíos y «Sin dato»
const RE_ERROR = /(sin dato|no carga|no se ha podido|no se pudo|ha fallado|error|falla|ca[ií]d[ao]|rot[ao]\b|sin conectar|no responde|dato viejo|a medio escribir|último dato bueno)/i;
const _reCache = new Map();
const reDe = a => { if (!_reCache.has(a)) { try { _reCache.set(a, new RegExp(a, 'i')); } catch { _reCache.set(a, /$^/); } } return _reCache.get(a); };

/** La sugerencia para un texto de error o vacío: la fuente que nombra (si la nombra) con su estado y quién lo revisa. */
const RE_PREVISTO = /(todav[ií]a no|se mide desde|se mide a medias|fase 2|llega con|llega cuando)/i;   // hueco conocido, no un fallo
export function queHacerPara(texto, tabla, { error = RE_ERROR.test(texto || '') } = {}) {
  const t = String(texto || '');
  if (!t || !Array.isArray(tabla) || RE_PREVISTO.test(t)) return null;
  // Solo una fuente que está mal (caída, rota, sin conectar, vieja o a cero) da sugerencia: «funciona» no ayuda a nadie.
  const f = tabla.find(x => x.estado !== 'bien' && (x.alias || []).some(a => reDe(a).test(t)));
  if (f) return { texto: f.paso, quien: f.quien, fuente: f.nombre, estado: f.estado };
  if (error && /(no carga|no se ha podido|no se pudo|ha fallado|error)/i.test(t))
    return { texto: 'Recarga la página; si sigue igual, avisa a Tomás con la pantalla y la hora.', quien: 'Tomás', fuente: null, estado: 'error' };
  return null;
}

/** Recorre la pantalla y añade «Qué hacer» donde falta. Idempotente (marca data-qh). */
export function enriquecerErrores(raiz, tabla) {
  if (!raiz || !Array.isArray(tabla) || !tabla.length) return 0;
  let n = 0;
  const yaTiene = el => /Qu[eé] hacer/i.test(el.textContent || '');
  for (const el of raiz.querySelectorAll('.vacio-linea:not([data-qh]), .vacio-g:not([data-qh]):not(.celebrar), .vacio:not([data-qh]):not(.celebrar)')) {
    el.dataset.qh = '1';
    if (yaTiene(el) || el.closest('[data-ia="consejo"]')) continue;
    const s = queHacerPara(el.textContent, tabla);
    if (!s) continue;
    if (el.matches('.vacio-linea')) el.append(h('small', { class: 'que-hacer' }, `Qué hacer: ${s.texto}`));
    else {
      const p = h('p', { class: 'que-hacer' }, h('b', {}, 'Qué hacer: '), s.texto);
      const quien = el.querySelector(':scope > .quien');
      quien ? el.insertBefore(p, quien) : el.append(p);
    }
    n++;
  }
  for (const el of raiz.querySelectorAll('.sin-dato:not([data-qh])')) {
    el.dataset.qh = '1';
    const caja = el.closest('.tile, .ind') || el;
    const s = queHacerPara(caja.textContent, tabla, { error: true });
    if (!s || caja.title) continue;
    caja.title = `Qué hacer: ${s.texto}`;
    caja.setAttribute('aria-description', `Qué hacer: ${s.texto}`);
    n++;
  }
  return n;
}
