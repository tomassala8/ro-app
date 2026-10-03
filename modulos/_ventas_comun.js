// modulos/_ventas_comun.js · piezas compartidas de E6 (setters, ventas de RO, prospección). No es un módulo.
//
// Datos: data/ventas_ro/*.json (fuentes_ventas/generar_ventas_ro.py, solo lectura), servidos RECORTADOS por servir.py:
// cada setter solo sus filas; con nivel «resumen» solo recuentos; el dueño de un lead recibe su nombre y despacho
// completos (nombre_completo: true). Teléfono, correo y LinkedIn salen uno a uno por ctx.verDato (con rastro).
// Botones: ctx.accion → acción «simulada» con su vista previa. Nunca escribe en GHL, Zadarma ni Snov.
// Sistema visual: el de la ola 0 (componentes.js). Aquí solo lo que es propio de la venta de RO.

import { h, icono, botonesContacto, normalizarTelefono, avisoFlotante, chipEstado } from '../componentes.js';

/** data/ventas_ro/<nombre>.json recortado por el servidor. null si no existe. R15 (E0): SIEMPRE por ctx.datosModulo (la
 *  memoria por persona y el ETag de la carcasa; en «ver como» la memoria es aparte). Sin servidor, ctx.datosModulo ya lee
 *  el fichero tal cual: aquí no queda ningún fetch('data/…'). */
export async function cargar(ctx, nombre) {
  try { return ctx?.datosModulo ? await ctx.datosModulo(`ventas_ro/${nombre}`) : null; } catch { return null; }
}

/** ¿Qué setter es esta persona? (personas: setter_ana, setter_javier). */
export const SETTERS = ['ana', 'javier'];
export function setterDe(persona) {
  if (!persona?.puestos?.includes('setters')) return null;
  const id = (persona.id || '').toLowerCase();
  return SETTERS.find(s => id === s || id === `setter_${s}`) || null;
}
/** Nombre de un setter desde personas.json (nunca escrito a mano). */
export const nombreSetter = (ctx, s) => (s ? ctx.nombre(`setter_${s}`) : 'Sin setter');

/** Frescura de una fuente de data/ventas_ro/meta.json, en hora de Madrid. */
export function fresco(meta, prefijo, texto) {
  const f = (meta?.fuentes || []).find(x => x.fuente.startsWith(prefijo));
  if (!f) return { fuente: texto || prefijo, estado: 'sin datos' };
  if (f.estado === 'error' || f.estado === 'sin datos') return { fuente: texto || f.fuente, estado: 'sin datos' };
  const edad = (Date.now() - new Date(f.hora.replace(' ', 'T'))) / 36e5;
  return { fuente: texto || f.fuente.replace('Panel v29 · ', 'Panel de resultados · '), edad_h: Math.max(0, edad), estado: f.estado === 'viejo' || edad > 26 ? 'viejo' : 'ok' };
}

export function duracionTexto(min) {
  if (min === null || min === undefined) return '—';
  if (min < 60) return `${min} min`;
  if (min < 60 * 24) return `${Math.floor(min / 60)} h${min % 60 ? ` ${min % 60} min` : ''}`;
  const d = Math.floor(min / 1440); return `${d} día${d === 1 ? '' : 's'}`;
}
/** «2026-10-05 11:00» → «lun 5 · 11:00» (hora de Madrid: así vienen del generador). */
export function cuandoTexto(s) {
  if (!s) return '—';
  const d = new Date(s.replace(' ', 'T'));
  if (Number.isNaN(+d)) return s;
  return `${d.toLocaleDateString('es-ES', { weekday: 'short', day: 'numeric' })} · ${d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}`;
}
export const minutosDesde = s => (s ? Math.max(0, Math.round((Date.now() - new Date(s.replace(' ', 'T'))) / 6e4)) : null);

/** Nombre a la vista: completo si el servidor lo ha abierto para su dueño (su setter; 3-oct: también dirección y ventas
 *  de RO, que dirigen a los setters); si no, enmascarado. Es un dato, no un texto de la app: sin limpiaTexto (se comía
 *  el «···» final y dejaba una letra suelta, «J»). Sin nombre: el teléfono enmascarado o «Sin nombre · formulario del 2-oct». */
const MESES_C = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
export const diaCorto = s => (s && /^\d{4}-\d{2}-\d{2}/.test(s) ? `${Number(s.slice(8, 10))}-${MESES_C[Number(s.slice(5, 7)) - 1]}` : '');
export function nombreLead(x) {
  const n = String(x.nombre_m || '').trim();
  const desp = String(x.despacho_m || '').trim();
  const tel = String(x.tel_m || '').trim();
  let base = n;
  if (!n || n === '(sin nombre)' || /^\S$/.test(n)) {
    const dia = diaCorto(x.entro || x.cuando);
    base = tel ? `Sin nombre · ${tel}` : `Sin nombre${dia ? ` · formulario del ${dia}` : ''}`;
  } else if (!x.nombre_completo && /^\S···$/.test(n) && !desp && tel) {
    base = `${n} · ${tel}`;              // enmascarado de una sola inicial: el final del teléfono lo distingue
  }
  return `${base}${desp ? ' · ' + desp : ''}`;
}
export const estaEnmascarado = x => !x.nombre_completo && /···/.test(x.nombre_m || '');

// ------------------------------------------------------------------ acciones (cola «simulada»)
export async function leerCola(ctx, modulo) {
  if (ctx?.servidor && ctx.api) {
    try {
      const r = await ctx.api(`acciones?modulo=${encodeURIComponent(modulo)}`);
      return (r.acciones || []).map(a => ({ que: a.tipo, sobre: a.objeto, texto: a.texto, hora: (a.creada || '').replace(' ', 'T'), como: a.quien }))
        .sort((x, y) => (x.hora || '').localeCompare(y.hora || ''));
    } catch {
      try { const r = await ctx.api('rastro'); return (r.acciones || []).filter(a => a.modulo === modulo).map(a => ({ que: a.tipo, sobre: a.objeto, texto: a.texto, hora: (a.creada || '').replace(' ', 'T'), como: a.quien })).reverse(); }
      catch { return []; }
    }
  }
  try { return JSON.parse(localStorage.getItem('ro.acciones.e6') || '[]').filter(a => !modulo || a.modulo === modulo); } catch { return []; }
}
/** Deja la acción en la cola «simulada». herramienta: una de la lista blanca (app, ghl, zadarma, whatsapp, snov). */
export async function encolar(ctx, { que, sobre, texto, herramienta = 'app', vista }) {
  if (ctx.soloLectura) throw new Error('«Ver como» es solo lectura: no se hace nada.');
  const r = await ctx.accion({ herramienta, tipo: que, objeto: sobre, texto: texto || '', vista_previa: vista || '' });
  if (!ctx.servidor) {
    try { const c = JSON.parse(localStorage.getItem('ro.acciones.e6') || '[]'); c.push({ que, sobre, texto, hora: new Date().toISOString(), como: ctx.persona.id }); localStorage.setItem('ro.acciones.e6', JSON.stringify(c.slice(-500))); } catch { /* nada */ }
  }
  return r;
}
export function vistaPrevia(texto) {
  return h('p', { class: 'fila sub' }, icono('info', { clase: 's' }), h('span', {}, h('b', {}, 'Simulación: '), texto));
}

// ------------------------------------------------------------------ atajos «Abrir en …»
/** Enlace a la herramienta de origen. Sin enlace, el botón sale en gris con el motivo (nunca desaparece). */
export function abrirEn(herramienta, url, { motivo = 'Falta el enlace · lo empareja Mili', mini = true } = {}) {
  const cls = `bt${mini ? ' mini' : ''}`;
  if (!url) return h('button', { type: 'button', class: cls, 'aria-disabled': 'true', title: motivo }, icono('ext'), `Abrir en ${herramienta}`);
  return h('a', { class: cls, href: url, target: '_blank', rel: 'noopener' }, icono('ext'), `Abrir en ${herramienta}`);
}

/** «⋯ Más»: desplegable nativo (details) con acciones secundarias, para no aplastar filas. */
export function masAcciones(...botones) {
  const hijos = botones.flat().filter(Boolean);
  if (!hijos.length) return null;
  return h('details', { class: 'mas-acc pila' },
    h('summary', { class: 'bt mini' }, icono('mas'), 'Más'),
    h('div', { class: 'fila' }, hijos));
}

// ------------------------------------------------------------------ datos completos de un lead (D-88)
export function puedeAbrir(ctx, almacen) {
  if (ctx.soloLectura) return false;
  const p = ctx.persona.puestos;
  // R12 (C-A1): el fichero de una setter lo abre ella, dirección o ventas de RO (misma regla que servir.py, dueno_setter).
  // Nunca «setter_null» ni «setter_undefined»: sin setter conocido no hay almacén.
  if (almacen.startsWith('setter_')) {
    const s = almacen.slice(7);
    if (!s || s === 'null' || s === 'undefined') return false;
    return s === setterDe(ctx.persona) || p.includes('direccion') || p.includes('ventas_ro');
  }
  if (almacen === 'ventas_tomas') return p.includes('ventas_ro') || p.includes('direccion');
  if (almacen === 'outreach_respuestas') return p.includes('outreach') || p.includes('jefa_crm') || p.includes('direccion');
  return false;
}
async function dato(ctx, almacen, id, campo) {
  try { return (await ctx.verDato({ almacen: `ventas_ro/_privado/${almacen}`, ref: id, campo })).valor || ''; }
  catch (e) { if (e.status === 403) throw e; return ''; }
}

/**
 * Contacto de un lead en un clic: «Llamar» y «WhatsApp» (o «Escribir por correo» si no dejó teléfono).
 * Al pulsar, pide el dato por ver_dato (queda en el rastro), apunta el intento y abre la app (sip: de Zadarma,
 * wa.me o mailto:). Después deja a la vista el componente común botonesContacto con el número y «copiar».
 */
export function contactoLead(ctx, { almacen, x, modulo = 'setters' }) {
  const nombre = x.nombre_completo ? x.nombre_m : '';
  if (!puedeAbrir(ctx, almacen)) {
    return h('span', { class: 'sub', title: ctx.soloLectura ? 'En «ver como» no se llama a nadie' : 'Solo quien trabaja el lead' }, icono('candado'), ' Contacto: solo su setter');
  }
  const caja = h('div', { class: 'fila' });
  const abrir = async (b, tipo) => {
    b.disabled = true;
    try {
      const campo = tipo === 'correo' ? 'correo' : 'telefono';
      const valor = await dato(ctx, almacen, x.id, campo);
      if (!valor) { b.replaceChildren(icono('alert'), tipo === 'correo' ? 'Sin correo' : 'Sin teléfono'); return; }
      const tel = campo === 'telefono' ? normalizarTelefono(valor) : null;
      const url = tipo === 'llamar' ? `sip:${tel?.intl}@sip.zadarma.com` : tipo === 'whatsapp' ? `https://wa.me/${tel?.intl}` : `mailto:${valor}`;
      if (campo === 'telefono' && !tel) { b.replaceChildren(icono('alert'), 'Teléfono raro: míralo en GHL'); return; }
      await encolar(ctx, { que: tipo === 'llamar' ? 'llamada_iniciada' : tipo === 'whatsapp' ? 'whatsapp_abierto' : 'correo_abierto', sobre: x.id,
        herramienta: tipo === 'llamar' ? 'zadarma' : tipo === 'whatsapp' ? 'whatsapp' : 'app',
        texto: `${tipo === 'llamar' ? 'Llamada' : tipo === 'whatsapp' ? 'WhatsApp' : 'Correo'} a ${nombre || 'un lead'}`,
        vista: tipo === 'llamar' ? 'Abre la app de Zadarma con el número' : tipo === 'whatsapp' ? 'Abre WhatsApp; el mensaje lo escribes tú' : 'Abre tu correo; el mensaje lo escribes tú' }).catch(() => null);
      caja.replaceChildren(botonesContacto({ nombre, telefono: campo === 'telefono' ? valor : '', correo: campo === 'correo' ? valor : '', modo: 'lista' }));
      if (tipo === 'whatsapp') window.open(url, '_blank', 'noopener'); else location.href = url;
    } catch (e) { b.replaceChildren(icono('candado'), e.message || 'No permitido'); }
  };
  const boton = (tipo, texto, ico, pri) => {
    const b = h('button', { type: 'button', class: `bt${pri ? ' pri' : ''}` }, icono(ico), texto);
    b.addEventListener('click', () => abrir(b, tipo));
    return b;
  };
  if (x.sin_tel) {
    caja.append(x.tiene_correo ? boton('correo', 'Escribir por correo', 'mail', true) : h('span', { class: 'sub' }, icono('alert'), ' Sin teléfono ni correo: míralo en GHL'));
  } else {
    caja.append(boton('llamar', 'Llamar', 'phone', true), boton('whatsapp', 'WhatsApp', 'wa', false));
  }
  return caja;
}

/** «Ver datos»: abre teléfono y correo (o LinkedIn) en el sitio. Queda en el rastro. */
export function verDatos(ctx, { almacen, id, destino, campos = ['telefono', 'correo'] }) {
  if (!puedeAbrir(ctx, almacen)) return null;
  const b = h('button', { type: 'button', class: 'bt mini' }, icono('ojo'), 'Ver datos');
  b.addEventListener('click', async () => {
    b.disabled = true;
    try {
      const v = {};
      for (const c of ['nombre', 'despacho', ...campos]) v[c] = await dato(ctx, almacen, id, c);
      destino.replaceChildren(h('b', {}, [v.nombre, v.despacho].filter(Boolean).join(' · ') || '—'),
        botonesContacto({ nombre: v.nombre, telefono: v.telefono, correo: v.correo, modo: 'lista' }),
        v.linkedin ? h('a', { class: 'bt mini', href: v.linkedin, target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir en LinkedIn') : null);
      b.remove();
    } catch (e) { b.replaceChildren(icono('candado'), e.message || 'No permitido'); }
  });
  return b;
}

/** Abre el perfil de LinkedIn de un prospecto (dato privado: por ver_dato y con rastro). */
export function abrirLinkedIn(ctx, { almacen, id, tiene }) {
  if (!tiene) return abrirEn('LinkedIn', null, { motivo: 'Snov.io no trae su perfil de LinkedIn' });
  if (!puedeAbrir(ctx, almacen)) return null;
  const b = h('button', { type: 'button', class: 'bt mini' }, icono('ext'), 'Abrir en LinkedIn');
  b.addEventListener('click', async () => {
    try {
      const u = await dato(ctx, almacen, id, 'linkedin');
      if (!/^https:\/\/([\w-]+\.)?linkedin\.com\//.test(u)) { avisoFlotante('Sin perfil de LinkedIn', { icono: 'alert' }); return; }
      encolar(ctx, { que: 'linkedin_abierto', sobre: id, herramienta: 'app', texto: 'Perfil de LinkedIn', vista: 'Abre el perfil en LinkedIn' }).catch(() => null);
      window.open(u, '_blank', 'noopener');
    } catch (e) { avisoFlotante(e.message || 'No permitido', { icono: 'alert' }); }
  });
  return b;
}

/** Chip del grupo de un lead. */
export function chipGrupo(g) {
  return { a: chipEstado('azul', 'Reunión de 45 min'), b: chipEstado('ambar', 'Formulario sin reservar'), c: chipEstado('rojo', 'No se presentó') }[g] || null;
}

/** Campo de formulario con la clase común .campo (36 px de alto, radio --r-m, foco con anillo): solo tokens de estilos.css. */
export function campo({ etiqueta, nombre, tipo = 'text', valor = '', opciones, ayuda, min, filas }) {
  const id = `c-${nombre}-${Math.random().toString(36).slice(2, 6)}`;
  let control;
  if (opciones) control = h('select', { id, name: nombre }, opciones.map(o => h('option', { value: o.valor ?? o, selected: (o.valor ?? o) === valor ? true : null }, o.texto ?? o)));
  else if (tipo === 'textarea') control = h('textarea', { id, name: nombre, rows: filas || 3 }, valor);
  else control = h('input', { id, name: nombre, type: tipo, value: valor, min, inputmode: tipo === 'number' ? 'numeric' : null });
  return h('label', { class: 'campo', for: id }, h('span', { class: 'campo-et' }, etiqueta), control, ayuda ? h('small', {}, ayuda) : null);
}
