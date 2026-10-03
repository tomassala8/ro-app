// modulos/ficha_equipo.js · Ronda U (3-oct, carril U2 · cambios #7 y #9 del 50). Lo usa ficha.js.
//
// 1 · «Avisar al equipo» desde la cabecera de la ficha (#7). Un menú con la gente que lleva ESTE cliente por silla (verdad
//     única: publicidad, GoHighLevel, web, SEO, redes y, al revés, su account) → un compositor con el contexto del cliente
//     ya escrito (el dato del problema, según la silla) → «Enviar aviso». Va por la API de canales de avisos.py
//     (POST /api/canales/mensaje) al grupo del cliente («cliente-<id>»: solo quien lo lleva y quien puede abrirlo), con la
//     mención a la persona (le salta en la campana). Opcional: la tarea en ClickUp, que entra en la cola de sincronía
//     (sincronia.py, acción clickup/tarea → «crear tarea» SIMULADA). Es interno: sin «¿Seguro?», con «Deshacer» 8 s
//     (_deshacer.js); el mensaje se escribe al acabar el plazo (los mensajes de canal no se borran).
//
// 2 · Pestaña «Reunión» (#9): en una pantalla lo que hoy exige cuatro (ficha, informe, bandeja y producción) para preparar
//     y hacer la reunión mensual: resultados del mes cerrado frente al objetivo, lo pendiente de la última reunión (los
//     acuerdos del acta que se guardó aquí, con «Hecho» + Deshacer; los pasos del resumen de Zoom si lo hay; el enlace a la
//     última de Fathom), los temas abiertos (correos sin contestar, revisiones de más de 48 h, avisos rojos), las tareas en
//     curso con fecha, semáforo y objetivo, y el acta de hoy: notas + acuerdos (cada acuerdo crea su tarea en la cola de
//     sincronía, simulada) con «Guardar». «Copiar guion» deja el orden del día en el portapapeles.
//
// Datos: los que ya carga ficha.js (F) + ctx.api('acciones?modulo=ficha') (actas y acuerdos hechos) + Producción y
// Reuniones solo si la persona ve esas pantallas (ctx.veModulo), recortados por el servidor. Nada sale fuera de la app.
// Diseño estricto: clases comunes (panel, pila, fila, dos, bt, chip, campo, sub, lista-i, titulo-seccion) y tokens.

import {
  h, fmt, icono, chipEstado, chipsFiltro, vacioLinea, avisoFlotante, copiar, campoTexto, menuMas, tile, tiles, panel,
} from '../componentes.js';
import { botonDeshacer } from './_deshacer.js';

const MES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const MES3 = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const dia = iso => { if (!iso) return '—'; const d = new Date(String(iso).length <= 10 ? `${iso}T12:00:00` : String(iso).replace(' ', 'T')); return Number.isNaN(+d) ? String(iso) : `${d.getDate()}-${MES3[d.getMonth()]}`; };
const fuente = (doc, id) => doc?.fuentes?.[id] || null;
const META = { font: 'var(--t-meta)', color: 'var(--dim)' };
const sub = (t, extra = {}) => h('span', { style: { ...META, ...extra } }, t);

// ------------------------------------------------------------------ quién lleva qué en este cliente
const SILLA = {
  trafficker: { texto: 'Publicidad', icono: 'megafono', dep: 'publicidad' },
  crm: { texto: 'GoHighLevel', icono: 'base', dep: 'crm' },
  web: { texto: 'Web', icono: 'mundo_web', dep: 'web' },
  seo: { texto: 'SEO', icono: 'globe', dep: 'seo' },
  redes: { texto: 'Redes', icono: 'heart', dep: 'redes' },
  account: { texto: 'Account', icono: 'cli', dep: 'accounts' },
};
const MOTIVOS = {
  trafficker: ['Campaña sin leads', 'Coste por lead alto', 'Anuncio rechazado o cuenta parada', 'El cliente pide un cambio', 'Otro'],
  crm: ['Leads sin contactar', 'Citas sin estado', 'WhatsApp o formulario no llega', 'El cliente pide un cambio', 'Otro'],
  web: ['Web caída o lenta', 'Formulario que no llega', 'Cambio en la web', 'Otro'],
  seo: ['Bajada de posiciones o de clics', 'Petición del cliente', 'Otro'],
  redes: ['Hueco en el calendario', 'Publicación con fallo', 'Petición del cliente', 'Otro'],
  account: ['Hay que avisar al cliente', 'Falta un acceso o un dato del cliente', 'Otro'],
};

/** Personas del equipo del cliente, por silla, sin quien mira. [{ silla, pid, nombre, completo, principal }] */
export function equipoAvisable(ctx, F) {
  // La verdad única trae el equipo por silla, pero el servidor quita las personas cuyas horas no ve quien mira (un account
  // recibe solo su silla): entonces, las asignaciones del cliente (fuente «asignaciones», una persona por silla), como el
  // panel «Equipo y servicios» de la ficha.
  const eq = F.verdad?.equipo || {};
  const viejas = fuente(F.doc, 'asignaciones')?.datos?.sillas || {};
  const yo = ctx.real?.id;
  const out = [];
  for (const s of Object.keys(SILLA)) {
    const lista = (eq[s] || []).length ? eq[s] : (viejas[s] ? [{ persona_id: viejas[s], principal: true }] : []);
    for (const x of lista) {
      if (!x?.persona_id || x.persona_id === yo) continue;
      const p = (ctx.datos?.personas || []).find(q => q.id === x.persona_id) || {};
      if (p.estado && p.estado !== 'activo') continue;
      out.push({ silla: s, pid: x.persona_id, nombre: ctx.nombre(x.persona_id), completo: p.nombre || ctx.nombre(x.persona_id), principal: !!x.principal });
    }
  }
  return out.sort((a, b) => Object.keys(SILLA).indexOf(a.silla) - Object.keys(SILLA).indexOf(b.silla) || (b.principal - a.principal));
}

/** El dato del problema, ya escrito, según la silla de quien recibe el aviso (sin importes si quien escribe no los ve). */
function contextoPara(silla, F) {
  const L = [];
  const meta = fuente(F.doc, 'meta')?.datos;
  const capt = fuente(F.doc, 'captacion_ghl')?.datos;
  const tar = fuente(F.doc, 'tareas')?.datos;
  const rojas = (F.alarmas || []).filter(a => a.gravedad === 'rojo').map(a => a.tipo ? `${a.tipo}${a.texto ? ` (${String(a.texto).slice(0, 90)})` : ''}` : (a.motivo || a.titulo)).filter(Boolean);
  if ((silla === 'trafficker' || silla === 'account') && meta?.leads) {
    const l7 = meta.leads['7d'], l7a = meta.leads['7d_prev'];
    let t = `Meta, 7 días: ${fmt.num(l7)} leads (los 7 anteriores, ${fmt.num(l7a)})`;
    if (F.ve?.inversion && meta.gasto) t += ` · ${fmt.eur(meta.gasto['7d'])} gastados${meta.cpl?.['7d'] ? ` · ${fmt.eur(meta.cpl['7d'], 2)} por lead` : ''}`;
    if (meta.estado_cuenta && meta.estado_cuenta !== 'activa') t += ` · cuenta ${meta.estado_cuenta}`;
    L.push(t + '.');
  }
  if ((silla === 'crm' || silla === 'account') && capt?.embudo) {
    const e = capt.embudo, c14 = capt.citas?.['14d'] || {};
    L.push(`GoHighLevel: ${fmt.num(e.estancados_72h || 0)} leads parados más de 72 h · ${fmt.num(c14.sin_estado || 0)} citas sin estado en 14 días.`);
  }
  if ((silla === 'web' || silla === 'seo') && F.c?.web) L.push(`Web: ${F.c.web.replace(/^https?:\/\//, '').replace(/\/$/, '')}.`);
  if (silla === 'redes' && tar) L.push(`Tareas del cliente: ${fmt.num(tar.vencidas || 0)} vencidas.`);
  if (rojas.length) L.push(`En rojo: ${rojas.slice(0, 2).join(' · ')}.`);
  return L;
}

/** Botón de la barra de la ficha: «Avisar al equipo ▾» con una línea por persona. alElegir(persona) abre el compositor. */
export function botonAvisar(ctx, F, alElegir) {
  const gente = equipoAvisable(ctx, F);
  if (!gente.length) return h('span', { class: 'bt', 'aria-disabled': 'true', title: 'Este cliente no tiene equipo asignado por silla (lo mantiene Mili)' }, icono('campana'), 'Avisar al equipo');
  // El aviso más frecuente, en UN clic: para un account, a su publicidad (trafficker principal); para el resto del equipo,
  // al account. Los demás, en el menú «Otros».
  const yoAccount = (ctx.persona?.puestos || []).includes('account');
  const primero = (yoAccount ? gente.find(p => p.silla === 'trafficker' && p.principal) : gente.find(p => p.silla === 'account')) || gente[0];
  const directo = h('button', { type: 'button', class: 'bt', 'data-avisar': primero.silla, title: `Mensaje a ${primero.nombre} con el dato del cliente ya escrito (interno)`, on: { click: () => alElegir(primero) } },
    icono('campana'), `Avisar a ${primero.nombre} (${SILLA[primero.silla].texto.toLowerCase()})`);
  const resto = gente.filter(p => p !== primero);
  return h('span', { class: 'fila', style: { gap: 'var(--s-1)', flexWrap: 'nowrap' } }, directo,
    resto.length ? menuMas({ texto: 'Otros', etiqueta: `Avisar a otra persona del equipo de ${F.c.nombre}`,
      items: resto.map(p => ({ texto: `${SILLA[p.silla].texto} · ${p.nombre}${p.principal ? '' : ' (apoyo)'}`, icono: SILLA[p.silla].icono, alPulsar: () => alElegir(p) })) }) : null);
}

/** Compositor del aviso: motivo (chips), texto con el contexto ya escrito, tarea opcional y «Enviar aviso» (con Deshacer). */
export function compositorAviso(ctx, F, p, { alCerrar } = {}) {
  const c = F.c;
  const canal = `cliente-${c.id}`;
  const motivos = MOTIVOS[p.silla] || ['Otro'];
  const chips = chipsFiltro({ etiqueta: 'Qué pasa', opciones: motivos.map(m => ({ valor: m, texto: m })), valor: motivos[0], alCambiar: () => rehacer() });
  const area = campoTexto({ etiqueta: `Mensaje para ${p.nombre} (lo verá en el grupo de ${c.nombre} y en su campana)`, filas: 5 });
  const txt = area.querySelector('textarea');
  txt.maxLength = 1500;
  let tocado = false;
  txt.addEventListener('input', () => { tocado = true; });
  const rehacer = () => {
    if (tocado) return;
    const m = chips.valor() || motivos[0];
    txt.value = [`@${p.completo} · ${c.nombre}: ${m === 'Otro' ? '' : m.toLowerCase() + '.'}`.trim(), ...contextoPara(p.silla, F),
      `Ficha: #/ficha/${c.id}/${p.silla === 'trafficker' || p.silla === 'crm' ? 'resultados' : 'resumen'}`].join('\n');
  };
  rehacer();
  const conTarea = h('input', { type: 'checkbox', id: `aviso-tarea-${c.id}` });
  const vence = (() => { const d = new Date(`${ctx.hoy || ctx.fechas?.hoy?.()}T12:00:00`); let n = 0; while (n < 2) { d.setDate(d.getDate() + 1); if (d.getDay() % 6) n += 1; } return d.toISOString().slice(0, 10); })();
  const estado = h('span', { class: 'sub', role: 'status' });
  let foto = null;   // lo que había al pulsar «Enviar» (lo que se escribe a los 8 s)
  const enviar = botonDeshacer({
    texto: 'Enviar aviso', icono: 'send', pri: true, mini: false, hecho: `Aviso a ${p.nombre}`, soloLectura: ctx.soloLectura,
    titulo: 'Interno: le llega a la persona en la app. Tienes 8 s para deshacer',
    alHacer: async () => {
      const f = foto || { texto: txt.value.trim(), tarea: conTarea.checked, motivo: chips.valor() };
      const r = await ctx.api('canales/mensaje', { metodo: 'POST', cuerpo: { canal_id: canal, texto: f.texto } });
      let extra = '';
      if (f.tarea) {
        const tr = await ctx.accion({ herramienta: 'clickup', tipo: 'tarea', objeto: `${c.nombre} · ${f.motivo}`, cliente_id: c.id,
          texto: f.texto.replace(/^@[^·]+·\s*/, ''), vista_previa: { tarea: `${c.nombre} · ${f.motivo}`, asignado: p.pid, vence, origen: 'aviso desde la ficha' } });
        extra = ` · tarea a la cola de ClickUp (simulada, n.º ${tr?.id ?? '—'})`;
      }
      try { ctx.rastro({ accion: 'aviso_equipo', objeto: c.id, detalle: `${SILLA[p.silla].texto} · ${p.nombre} · ${f.motivo}` }); } catch { /* el mensaje ya deja rastro */ }
      const noVen = (r?.no_lo_veran || []).length ? ` (ojo: ${r.no_lo_veran.join(', ')} no está en el grupo del cliente)` : '';
      return `Avisado ${p.nombre} en el grupo de ${c.nombre}${extra}${noVen}`;
    },
    alAnular: () => { foto = null; txt.disabled = false; conTarea.disabled = false; },
  });
  // La foto se hace al pulsar (antes de que el botón cambie): lo que se ve es lo que se manda.
  enviar.addEventListener('click', e => {
    if (!e.target.closest('button') || e.target.closest('button').textContent.startsWith('Deshacer')) return;
    if (!txt.value.trim()) { e.stopPropagation(); estado.textContent = 'Escribe el mensaje.'; return; }
    foto = { texto: txt.value.trim(), tarea: conTarea.checked, motivo: chips.valor() || motivos[0] };
    txt.disabled = true; conTarea.disabled = true;
  }, true);
  const cerrar = h('button', { type: 'button', class: 'bt', on: { click: () => alCerrar?.() } }, 'Cerrar');
  const caja = h('section', { class: 'panel', 'data-aviso-equipo': p.silla, 'aria-label': `Avisar a ${p.nombre}`, style: { flexBasis: '100%', minWidth: '0', margin: '0' } },
    h('div', { class: 'cuerpo pila', style: { gap: 'var(--s-3)' } },
      h('div', { class: 'fila', style: { justifyContent: 'space-between' } },
        h('b', { style: { font: 'var(--t-h3)', display: 'inline-flex', alignItems: 'center', gap: 'var(--s-2)' } }, icono(SILLA[p.silla].icono), `Avisar a ${p.nombre} · ${SILLA[p.silla].texto.toLowerCase()} de ${c.nombre}`),
        sub('Interno: no sale de la app')),
      chips, area,
      h('label', { class: 'fila', for: conTarea.id, style: { gap: 'var(--s-2)', cursor: 'pointer', minHeight: 'var(--s-8)' } }, conTarea,
        h('span', {}, `Crear también la tarea en ClickUp para ${p.nombre}, para el ${dia(vence)}`), sub('(cola de sincronía, simulada)')),
      h('div', { class: 'fila', style: { justifyContent: 'flex-end' } }, estado, cerrar, enviar)));
  caja.addEventListener('keydown', e => { if (e.key === 'Escape') { e.stopPropagation(); alCerrar?.(); } });
  queueMicrotask(() => { try { txt.focus({ preventScroll: true }); txt.setSelectionRange(txt.value.length, txt.value.length); } catch { /* nada */ } });
  return caja;
}

// =================================================================== pestaña «Reunión»
const ACTA = cid => `reunion:${cid}:`;

async function leerActas(ctx, cid) {
  if (!ctx.servidor) return { actas: [], hechos: new Map() };
  let acc = [];
  try { acc = (await ctx.api('acciones?modulo=ficha'))?.acciones || []; } catch { acc = []; }
  const vp = a => { try { return typeof a.vista_previa === 'string' ? JSON.parse(a.vista_previa) : (a.vista_previa || {}); } catch { return {}; } };
  const actas = acc.filter(a => a.tipo === 'acta' && String(a.objeto || '').startsWith(ACTA(cid))).map(a => ({ ...a, vp: vp(a) }))
    .sort((a, b) => String(b.creada || '').localeCompare(String(a.creada || '')) || b.id - a.id);
  const hechos = new Map();
  for (const a of acc.slice().reverse()) if (a.tipo === 'marcar' && String(a.objeto || '').startsWith(`acuerdo:${cid}:`)) hechos.set(String(a.objeto), a);
  return { actas, hechos };
}

async function leerOpcional(ctx, modulo, nombre) {
  if (ctx.veModulo && !ctx.veModulo(modulo)) return null;
  try { return await ctx.datosModulo(nombre); } catch { return null; }
}

/** Resultados del mes cerrado (y el que va) frente al objetivo del cliente. */
function resultadosMes(F) {
  const meta = fuente(F.doc, 'meta')?.datos || {};
  const capt = fuente(F.doc, 'captacion_ghl')?.datos || {};
  const o = F.obj?.objetivo || {};
  const mesAnt = MES[(new Date().getMonth() + 11) % 12];
  const T = [];
  T.lineas = [];
  if (meta.leads) {
    T.lineas.push(`Leads de ${mesAnt}: ${fmt.num(meta.leads.mes_anterior)}${o.cargado && o.leads_mes ? ` (objetivo ${fmt.num(o.leads_mes)})` : ''} · este mes, ${fmt.num(meta.leads.mes)} hasta hoy`);
    const l = meta.leads.mes_anterior, obj = o.cargado ? o.leads_mes : null;
    T.push(tile({ icono: 'target', etiqueta: `Leads de ${mesAnt}`, valor: fmt.num(l), unidad: obj ? `objetivo ${fmt.num(obj)}` : 'sin objetivo',
      estado: obj ? (l >= obj ? 'verde' : l >= obj * 0.8 ? 'ambar' : 'rojo') : '', contexto: `Este mes, hasta hoy: ${fmt.num(meta.leads.mes)}`, medible: 'hoy' }));
    if (F.ve?.inversion && meta.cpl) {
      const cpl = meta.cpl.mes_anterior, objC = o.cargado ? o.coste_lead : null;
      T.push(tile({ icono: 'euro', etiqueta: `Coste por lead de ${mesAnt}`, valor: cpl != null ? fmt.eur(cpl, 2) : null, unidad: objC ? `objetivo ${fmt.eur(objC, 2)}` : 'sin objetivo',
        estado: objC && cpl != null ? (cpl <= objC ? 'verde' : cpl <= objC * 1.2 ? 'ambar' : 'rojo') : '', contexto: meta.gasto ? `${fmt.eur(meta.gasto.mes_anterior)} invertidos` : '', medible: 'hoy' }));
    }
  }
  if (F.ve?.inversion && meta.cpl?.mes_anterior != null) T.lineas.push(`Coste por lead de ${mesAnt}: ${fmt.eur(meta.cpl.mes_anterior, 2)}${o.cargado && o.coste_lead ? ` (objetivo ${fmt.eur(o.coste_lead, 2)})` : ''}`);
  const citas = capt.citas?.mes;
  if (citas) T.lineas.push(`Citas este mes: ${fmt.num(citas.agendadas || 0)} (${fmt.num(citas.celebradas || 0)} celebradas)`);
  if (citas) T.push(tile({ icono: 'cal', etiqueta: 'Citas este mes', valor: fmt.num(citas.agendadas || 0), unidad: o.cargado && o.citas_mes ? `objetivo ${fmt.num(o.citas_mes)}` : '',
    contexto: `${fmt.num(citas.celebradas || 0)} celebradas · ${fmt.num(citas.sin_estado || 0)} sin estado`, medible: 'hoy' }));
  return T;
}

/** Lo pendiente de verdad: acuerdos del acta anterior sin hacer + Zoom + temas abiertos del cliente. */
function pendientes(ctx, F, A, zoom) {
  const items = [];
  const ultima = A.actas[0];
  for (const [i, x] of (ultima?.vp?.acuerdos || []).entries()) {
    const ref = `acuerdo:${F.c.id}:${ultima.id}:${i}`;
    const hecho = A.hechos.get(ref);
    items.push({ grupo: 'acta', texto: x.texto, extra: `${x.quien ? ctx.nombre(x.quien) : 'sin dueño'}${x.vence ? ` · para el ${dia(x.vence)}` : ''} · acta del ${dia(ultima.vp.fecha || ultima.creada)}`,
      estado: hecho ? 'verde' : x.vence && x.vence < (ctx.hoy || '') ? 'rojo' : 'ambar',
      accion: hecho ? chipEstado('verde', `Hecho · ${ctx.nombre(hecho.quien)}`) : botonDeshacer({ texto: 'Hecho', icono: 'ok', hecho: 'Hecho', soloLectura: ctx.soloLectura,
        alHacer: async () => { const r = await ctx.accion({ herramienta: 'app', tipo: 'marcar', objeto: ref, cliente_id: F.c.id, texto: `Acuerdo cumplido: ${x.texto}`, vista_previa: { acta: ultima.id, acuerdo: i } });
          A.hechos.set(ref, { quien: ctx.real.id, id: r?.id }); return 'Hecho · queda en el rastro'; } }) });
  }
  for (const p of zoom?.pasos || []) items.push({ grupo: 'zoom', texto: p, extra: `Resumen de Zoom · ${dia(zoom.fecha)}`, estado: 'ambar' });
  const cc = F.cc;   // correos sin contestar de la Bandeja (ficha.js lo pone antes de pintar)
  for (const x of (cc?.del_cliente || []).slice(0, 3)) items.push({ grupo: 'abierto', texto: `Correo sin contestar: «${x.asunto}»`, extra: `${x.dias} días laborables`, estado: x.horas > 48 ? 'rojo' : 'ambar',
    accion: x.url ? h('a', { class: 'bt mini', href: x.url, target: '_blank', rel: 'noopener' }, icono('inbox'), 'Abrir en Desk') : null });
  for (const x of (fuente(F.doc, 'tareas')?.datos?.en_revision_detalle || []).filter(t => t.dias > 2).slice(0, 3)) items.push({ grupo: 'abierto', texto: `Pieza esperando: ${x.nombre}`, extra: `${x.estado} · ${fmt.num(Math.round(x.dias))} días`, estado: 'ambar',
    accion: x.url ? h('a', { class: 'bt mini', href: x.url, target: '_blank', rel: 'noopener' }, icono('ext'), 'ClickUp') : null });
  for (const a of (F.alarmas || []).filter(a => a.gravedad === 'rojo').slice(0, 2)) items.push({ grupo: 'abierto', texto: a.tipo || a.motivo || a.titulo || 'Aviso rojo', extra: a.texto || 'Aviso rojo del cliente', estado: 'rojo',
    accion: a.enlace ? h('a', { class: 'bt mini', href: a.enlace, target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir') : null });
  return items;
}

const filaLista = it => h('li', { style: { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 'var(--s-2) var(--s-3)', padding: 'var(--s-2) 0', borderTop: 'var(--borde-suave)', minWidth: '0' } },
  h('span', { class: `ico-c s ${it.estado || ''}`.trim(), 'aria-hidden': 'true' }, icono(it.estado === 'verde' ? 'ok' : it.estado === 'rojo' ? 'alert' : 'clock')),
  h('span', { style: { flex: '1 1 220px', minWidth: '0', display: 'grid', gap: '2px' } }, h('span', { style: { overflowWrap: 'anywhere' } }, it.texto), it.extra ? sub(it.extra) : null),
  it.accion || null);

/** El acta de hoy: notas + acuerdos (cada uno con dueño y fecha) → Guardar (acta en la base; cada acuerdo, tarea simulada). */
function editorActa(ctx, F, A, repintar) {
  const c = F.c;
  const equipo = [{ pid: ctx.real.id, nombre: `${ctx.nombre(ctx.real.id)} (tú)` }, ...equipoAvisable(ctx, F)];
  const notas = campoTexto({ etiqueta: 'Notas de la reunión (qué ha contado el cliente, qué le preocupa, qué se ha decidido)', filas: 5 });
  const tn = notas.querySelector('textarea');
  tn.maxLength = 3000;
  const filas = h('div', { class: 'pila', style: { gap: 'var(--s-2)' } });
  const nuevaFila = (v = {}) => {
    const t = h('input', { type: 'text', placeholder: 'Acuerdo: qué se hace', 'aria-label': 'Acuerdo', value: v.texto || '', maxLength: 200, style: { flex: '3 1 220px', minWidth: '0' } });
    const q = h('select', { 'aria-label': 'Quién lo hace', style: { flex: '1 1 140px', minWidth: '0' } }, equipo.map(p => h('option', { value: p.pid }, p.nombre ? `${p.nombre}${p.silla ? ` · ${SILLA[p.silla].texto.toLowerCase()}` : ''}` : p.pid)));
    const f = h('input', { type: 'date', 'aria-label': 'Para cuándo', value: v.vence || '', style: { flex: '0 1 150px' } });
    const quitar = h('button', { type: 'button', class: 'bt mini', 'aria-label': 'Quitar este acuerdo', on: { click: () => { fila.remove(); } } }, icono('cerrar'));
    const fila = h('div', { class: 'fila campo', style: { gap: 'var(--s-2)', flexWrap: 'wrap', display: 'flex' }, 'data-acuerdo': '' }, t, q, f, quitar);
    filas.append(fila);
    return t;
  };
  nuevaFila();
  const mas = h('button', { type: 'button', class: 'bt mini', on: { click: () => nuevaFila().focus() } }, icono('mas'), 'Otro acuerdo');
  const estado = h('span', { class: 'sub', role: 'status' });
  const guardar = h('button', { type: 'button', class: 'bt pri', 'aria-disabled': ctx.soloLectura ? 'true' : null, title: ctx.soloLectura ? 'Estás en «ver como»: solo lectura' : 'Guarda el acta en la app; cada acuerdo crea su tarea (simulada) en la cola de ClickUp',
    on: { click: async () => {
      if (ctx.soloLectura) return;
      const acuerdos = [...filas.querySelectorAll('[data-acuerdo]')].map(f => { const [t, q, d] = f.querySelectorAll('input[type=text], select, input[type=date]'); return { texto: t.value.trim(), quien: q.value, vence: d.value || null }; }).filter(x => x.texto);
      const texto = tn.value.trim();
      if (!texto && !acuerdos.length) { estado.textContent = 'Escribe las notas o al menos un acuerdo.'; tn.focus(); return; }
      if (/[\w.+-]+@[\w-]+\.\w|(\+34|\b[6789]\d{2})[\s.-]?\d{3}[\s.-]?\d{3}\b/.test(`${texto} ${acuerdos.map(x => x.texto).join(' ')}`)) { estado.textContent = 'Sin correos ni teléfonos en el acta: van en Contactos.'; return; }
      guardar.disabled = true;
      try {
        const r = await ctx.accion({ herramienta: 'app', tipo: 'acta', objeto: `${ACTA(c.id)}${ctx.hoy}`, cliente_id: c.id, texto: texto ? texto.slice(0, 600) : `Acta de ${c.nombre} (solo acuerdos)`,
          vista_previa: { fecha: ctx.hoy, notas: texto, acuerdos } });
        let n = 0;
        for (const x of acuerdos) {
          await ctx.accion({ herramienta: 'clickup', tipo: 'tarea', objeto: `${c.nombre} · ${x.texto}`.slice(0, 180), cliente_id: c.id, texto: `Acuerdo de la reunión del ${dia(ctx.hoy)} con ${c.nombre}: ${x.texto}`,
            vista_previa: { tarea: `${c.nombre} · ${x.texto}`.slice(0, 180), asignado: x.quien, vence: x.vence, origen: 'acta de reunión', acta: r?.id } });
          n += 1;
        }
        avisoFlotante(`Acta guardada${n ? ` · ${fmt.plural(n, 'tarea', 'tareas')} a la cola de ClickUp (simulada)` : ''}`);
        await repintar();
      } catch (e) { estado.textContent = `No se ha guardado: ${e?.message || e}`; guardar.disabled = false; }
    } } }, icono('ok'), 'Guardar');
  return h('section', { class: 'panel', 'aria-label': 'Acta de hoy', 'data-acta': '' },
    h('header', {}, h('div', {}, h('h2', {}, icono('doc'), `Acta de hoy · ${dia(ctx.hoy)}`), h('p', { class: 'sub' }, 'Lo que guardes aquí es lo «pendiente de la última reunión» la próxima vez')), guardar),
    h('div', { class: 'cuerpo pila', style: { gap: 'var(--s-3)' } }, notas, h('span', { class: 'titulo-seccion' }, 'Acuerdos (cada uno crea su tarea)'), filas,
      h('div', { class: 'fila', style: { justifyContent: 'space-between' } }, mas, estado)));
}

function guionTexto(ctx, F, items, lineas) {
  const c = F.c;
  const L = [`Reunión con ${c.nombre} · ${dia(ctx.hoy)}`, '', '1. Resultados del mes'];
  for (const t of lineas || []) L.push(`   · ${t}`);
  L.push('', '2. Lo pendiente de la última reunión');
  for (const it of items.filter(x => x.grupo !== 'abierto')) L.push(`   · ${it.texto}`);
  L.push('', '3. Temas abiertos');
  for (const it of items.filter(x => x.grupo === 'abierto')) L.push(`   · ${it.texto}`);
  L.push('', '4. Próximos pasos y fecha de la siguiente reunión');
  return L.join('\n');
}

export async function pintarReunion(z, ctx, F) {
  z.replaceChildren(vacioLinea('Preparando la hoja de la reunión…', { icono: 'clock' }));
  const [A, prod, reu] = await Promise.all([leerActas(ctx, F.c.id), leerOpcional(ctx, 'produccion', 'produccion/produccion'), leerOpcional(ctx, 'reuniones', 'reuniones/reuniones')]);
  const c = F.c;
  const rd = fuente(F.doc, 'reuniones')?.datos || {};
  const ultimaZoom = (reu?.asistencias || []).filter(a => (a.cli === c.id) && a.resumen?.pasos?.length).sort((a, b) => b.fecha.localeCompare(a.fecha))[0];
  const zoom = ultimaZoom ? { fecha: ultimaZoom.fecha, pasos: ultimaZoom.resumen.pasos.slice(0, 5) } : null;
  const fathom = (reu?.clientes || []).find(x => x.cliente_id === c.id)?.enlaces?.find(e => e.fuente === 'Fathom');
  const items = pendientes(ctx, F, A, zoom);
  const T = resultadosMes(F);

  // ---- barra de la reunión (arriba, a la vista): última, próxima, copiar guion, informe ----
  const ult = rd.ult_reunion || F.verdad?.ultima_reunion;
  const barra = h('div', { class: 'fila', role: 'toolbar', 'aria-label': 'Acciones de la reunión', style: { justifyContent: 'space-between', gap: 'var(--s-2) var(--s-4)' } },
    h('span', { class: 'meta-linea' },
      h('span', {}, icono('hist'), ult ? `Última reunión: ${dia(ult)}${rd.dias_sin_reunion != null ? ` (hace ${fmt.plural(rd.dias_sin_reunion, 'día', 'días')})` : ''}` : 'Sin reuniones registradas'),
      h('span', {}, icono('cal'), rd.prox_reunion ? `Próxima: ${dia(rd.prox_reunion)}` : 'Sin próxima fecha')),
    h('span', { class: 'fila', style: { gap: 'var(--s-2)' } },
      h('button', { type: 'button', class: 'bt', on: { click: () => copiar(guionTexto(ctx, F, items, T.lineas), 'Guion de la reunión copiado') } }, icono('copy'), 'Copiar guion'),
      ctx.veModulo?.('informe-cliente') ? h('a', { class: 'bt', href: `#/informe-cliente/${c.id}` }, icono('res'), 'Informe del mes') : null,
      fathom ? h('a', { class: 'bt', href: `https://fathom.video/calls/${fathom.id}`, target: '_blank', rel: 'noopener', title: `Última en Fathom · ${dia(fathom.fecha)}` }, icono('spark'), `Fathom ${dia(fathom.fecha)}`) : null));

  // ---- izquierda (trabajo): pendiente + acta ----
  const deActa = items.filter(x => x.grupo === 'acta' || x.grupo === 'zoom');
  const abiertos = items.filter(x => x.grupo === 'abierto');
  const zPend = panel({ titulo: 'Lo pendiente de la última reunión', icono: 'flag', sub: A.actas[0] ? `Acuerdos del acta del ${dia(A.actas[0].vp.fecha || A.actas[0].creada)}${zoom ? ' y pasos del resumen de Zoom' : ''}` : 'Sin acta anterior guardada en la app: la de hoy será la primera' },
    h('div', { class: 'cuerpo' }, deActa.length ? h('ul', { style: { listStyle: 'none', margin: '0', padding: '0' } }, deActa.map(filaLista))
      : vacioLinea(fathom ? `La última de Fathom (${dia(fathom.fecha)}) no trae resumen por la API: ábrela arriba. Desde hoy, los acuerdos que guardes aquí salen en esta lista.` : 'Guarda abajo los acuerdos de hoy: la próxima reunión empezará por ellos.', { icono: 'info' })));
  const zAbiertos = abiertos.length ? panel({ titulo: 'Temas abiertos del cliente', icono: 'alert', sub: 'Correos sin contestar, piezas esperando y avisos rojos: para sacarlos en la reunión' },
    h('div', { class: 'cuerpo' }, h('ul', { style: { listStyle: 'none', margin: '0', padding: '0' } }, abiertos.map(filaLista)))) : null;
  const repintar = async () => { await pintarReunion(z, ctx, F); };

  // ---- derecha (contexto): resultados, semáforo y objetivo, tareas con fecha ----
  const zResultados = h('div', {}, T.length ? tiles(T) : vacioLinea('Sin resultados de Meta ni de GoHighLevel para este cliente.', { icono: 'target', quien: 'Agus (conexiones)' }));
  const o = F.obj?.objetivo, s = F.obj?.semaforo;
  const COL = { verde: 'Verde', ambar: 'Ámbar', rojo: 'Rojo' };
  const abrirA4 = cual => { if (!F.pintarA4) return; F.a4 = cual; F.pintarA4(); document.querySelector('[data-a4-editor]')?.scrollIntoView({ block: 'center' }); };
  const zA4 = F.obj ? h('div', { class: 'fila', style: { gap: 'var(--s-2)' } },
    h('button', { type: 'button', class: 'bt mini', on: { click: () => abrirA4('semaforo') } }, icono('flag'), 'Semáforo: ', s ? chipEstado(s.color, COL[s.color] || s.color) : chipEstado('gris', 'sin poner')),
    h('button', { type: 'button', class: 'bt mini', on: { click: () => abrirA4('objetivo') } }, icono('target'), o?.cargado ? `Objetivo: ${o.leads_mes != null ? `${fmt.num(o.leads_mes)} leads/mes` : 'cargado'}` : 'Objetivo sin cargar')) : null;
  const hoy = ctx.hoy || '';
  const conFecha = (prod?.cola || []).filter(t => t.cli === c.id && t.vence).sort((a, b) => a.vence.localeCompare(b.vence)).slice(0, 8)
    .map(t => ({ texto: t.tarea, extra: `${t.estado} · ${t.vence < hoy ? 'venció' : 'vence'} el ${dia(t.vence)}${t.persona_id ? ` · ${ctx.nombre(t.persona_id)}` : ''}`, estado: t.vence < hoy ? 'rojo' : 'ambar',
      accion: t.id ? h('a', { class: 'bt mini', href: `https://app.clickup.com/t/${t.id}`, target: '_blank', rel: 'noopener' }, icono('ext'), 'ClickUp') : null }));
  const tar = fuente(F.doc, 'tareas')?.datos || {};
  const zTareas = panel({ titulo: 'Tareas en curso con fecha', icono: 'check', sub: tar.vencidas != null ? `${fmt.num(tar.vencidas)} vencidas · ${fmt.num(tar.sin_fecha || 0)} sin fecha en ClickUp` : 'De Producción (ClickUp)' },
    h('div', { class: 'cuerpo' }, conFecha.length ? h('ul', { style: { listStyle: 'none', margin: '0', padding: '0' } }, conFecha.map(filaLista))
      : vacioLinea(prod ? 'Ninguna tarea con fecha de este cliente en lo que ves de Producción.' : 'Producción no es de tu puesto: abre «Trabajo» en esta ficha.', { icono: 'check' })));

  z.replaceChildren(h('div', { class: 'pila', 'data-reunion': c.id, style: { gap: 'var(--s-4)', minWidth: '0' } }, barra,
    h('div', { class: 'dos' },
      h('div', { class: 'pila', style: { minWidth: '0' } }, zPend, editorActa(ctx, F, A, repintar)),
      h('aside', { class: 'pila', 'aria-label': 'Resultados y contexto', style: { minWidth: '0' } },
        panel({ titulo: `Resultados del mes`, icono: 'target', sub: 'Mes cerrado frente al objetivo del cliente' }, h('div', { class: 'cuerpo pila' }, zResultados, zA4)), zAbiertos, zTareas))));
}
