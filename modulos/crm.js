// modulos/crm.js · M7 «Salud del CRM» (E5 del plan v2, parte CRM). Ruta #/salud-crm y #/salud-crm/<subcuenta>.
//
// Para quién: especialista en GHL y la jefa de CRM (Yessica) · dirección,
// operaciones y técnico de altas lo ven entero · account, sus clientes · publicidad, en resumen.
// Orden por frecuencia: cifras del día → «Lo primero hoy» (máx. 7) → pestañas (subcuentas, leads sin tocar,
// citas sin estado, por especialista, flujos y WhatsApp, montajes de altas) → indicadores con su umbral → Fase 2.
//
// Datos: data/crm/crm.json (fuentes_crm/generar_crm.py, solo lectura: GHL de las 66 subcuentas + captacion.json +
// asignaciones + clientes nuevos). Servido RECORTADO por servir.py: filas por cliente visible; las subcuentas sin
// cliente de la app, solo a quien lo ve todo. Los datos de cada lead, en data/crm/_privado/leads.json, solo con
// ctx.verDato() (D-88, queda en el rastro).
// Botones (mover oportunidad, nota, marcar y reprogramar cita, tarea al account): ctx.accion() → cola «simulada».
// Nunca escribe en GHL ni en ClickUp: la escritura de GHL espera la W3.

import {
  h, fmt, semaforo, tile, rejillaTarjetas, listaLoPrimero, tablaDensa, tablaApilable, chipEstado, chipsFiltro, selectorCliente,
  vacio, botonConfirmar, avisoParcial, logoCliente, panel, frescura, icono, iniciales, pestanas, fichaCatalogo, pieFase2,
  botonesContacto, avisoFlotante, campoTexto, embudoBarras, barraProgreso, esqueleto, vacioLinea,
} from '../componentes.js';
import { motivoSinCartera } from './ficha.js';   // V2 (B-M7): la misma frase de «sin cartera» en todas las pantallas
import { franjaCifras } from './_trabajo.js';
import { pantallaAncha, franjaEnLinea } from './_trabajo_ancho.js';
import { conDeshacer, botonDeshacer } from './_deshacer.js';

// Ronda U (3-oct, cambio #10 del 50): «Revisado · motivo» en leads sin tocar y citas sin estado. Interno (queda en la app
// con rastro, acción revisado_lead / revisado_cita): un clic en el motivo, la fila sale y «Deshacer» 8 s. No toca GoHighLevel.
const MOTIVOS_REVISADO = {
  lead: ['El despacho lo llamó desde su móvil', 'Duplicado', 'Prueba o spam', 'Ya es cliente del despacho', 'Número o datos falsos', 'Lo llama el despacho hoy'],
  cita: ['Vino (lo confirma el despacho)', 'No vino (lo confirma el despacho)', 'Cita de prueba', 'Duplicada', 'Cancelada fuera de GoHighLevel'],
};
const claveRev = (tipo, x) => `${tipo} ${x.ref}`;
function botonRevisado(ctx, x, tipo, d) {
  if (ctx.soloLectura) return null;
  const caja = h('details', { class: 'periodo-mas menu-mas', style: { display: 'inline-grid', justifyItems: 'start' } },
    h('summary', { class: 'bt mini pri', style: { display: 'inline-flex', listStyle: 'none' }, 'aria-label': `Revisado: elegir el motivo (${x.subcuenta})` }, icono('check'), 'Revisado'),
    h('div', { class: 'menu-flot', role: 'menu', style: { position: 'static', boxShadow: 'none', marginTop: 'var(--s-2)', minWidth: 0, display: 'grid', gap: 'var(--s-1)' } },
      MOTIVOS_REVISADO[tipo].map(m => h('button', { type: 'button', role: 'menuitem', class: 'bt mini', 'data-motivo': m, style: { justifyContent: 'flex-start', whiteSpace: 'normal', textAlign: 'left' }, on: { click: e => {
        caja.open = false;
        const fila = e.currentTarget.closest('tr') || e.currentTarget.closest('li') || e.currentTarget.closest('[role=row]');
        const clave = claveRev(tipo, x);
        conDeshacer({
          mensaje: `${tipo === 'lead' ? 'Lead' : 'Cita'} de ${x.subcuenta} revisado · ${m}`,
          optimista: () => { if (fila) fila.hidden = true; d.revisados?.set(clave, { texto: m }); contarRevisados(fila); },
          revertir: () => { if (fila) fila.hidden = false; d.revisados?.delete(clave); contarRevisados(fila); },
          hacer: () => ctx.accion({ herramienta: 'app', tipo: tipo === 'lead' ? 'revisado_lead' : 'revisado_cita', objeto: clave, cliente_id: x.cliente_id || undefined, texto: m,
            vista_previa: `${tipo === 'lead' ? 'Lead' : 'Cita'} de ${x.subcuenta} (${tipo === 'lead' ? `entró el ${fDiaRO(x.creado)}` : `cita del ${fDiaRO(x.inicio)}`}) revisado por ${ctx.nombre(ctx.persona.id)}: «${m}». Sale de la lista; no se toca GoHighLevel.` }),
        });
      } } }, m))));
  caja.addEventListener('keydown', e => { if (e.key === 'Escape') { caja.open = false; caja.querySelector('summary')?.focus(); } });
  return caja;
}
/** Tras marcar o deshacer, la cuenta de la pestaña y de la franja baja o sube sin repintar (el filtro de la tabla se queda). */
function contarRevisados(fila) {
  const panelT = fila?.closest('[role=tabpanel]');
  const tab = panelT ? document.getElementById(panelT.getAttribute('aria-labelledby') || '') : null;
  const filas = panelT ? [...panelT.querySelectorAll('tbody tr, ul > li')].filter(r => r.querySelector('[data-motivo]')) : [];
  const vivas = filas.filter(r => !r.hidden).length;
  const cu = tab?.querySelector('span.c');
  if (cu && /^\d+$/.test(cu.textContent.trim())) cu.textContent = String(Math.max(0, Number(cu.textContent) + (fila?.hidden ? -1 : 1)));
  return vivas;
}

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

const ID = 'salud-crm';
let JEFA = 'Yessica';   // nombre de la jefa de CRM: sale de ctx.nombre('yessica') al pintar
const EST = { rojo: { t: 'En rojo', o: 0 }, ambar: { t: 'Vigilar', o: 1 }, verde: { t: 'En verde', o: 2 }, gris: { t: 'Sin actividad', o: 3 } };
const ICO_MOT = { sin_uso: 'plug', citas_fuera: 'cal', integracion: 'plug', sin_tocar: 'phone', sin_estado: 'cal', asistencia: 'users', sin_citas: 'cal', estancados: 'clock', whatsapp: 'wa', sin_automatico: 'zap', velocidad: 'clock' };
const QUIEN_MOT = { sin_uso: 'account (confirmar si el servicio de CRM está contratado)', citas_fuera: 'especialista (conectar la agenda con GoHighLevel)', integracion: 'Agus (técnico)', sin_tocar: 'account con el despacho', sin_estado: 'account (que el despacho marque)', asistencia: 'especialista y account', sin_citas: 'account con el despacho', estancados: 'especialista', whatsapp: 'especialista', sin_automatico: 'especialista', velocidad: 'account con el despacho' };
const ETAPAS = [['nuevo', 'Nuevo'], ['seguimiento', 'Seguimiento'], ['cita', 'Cita'], ['presupuesto', 'Presupuesto'], ['cerrado', 'Cerrado'], ['descartado', 'Descartado']];
const pc = n => (n === null || n === undefined ? '—' : `${fmt.num(n, n < 10 && n % 1 ? 1 : 0)} %`);
const horasTxt = hh => (hh === null || hh === undefined ? '—' : hh < 48 ? `${hh} h` : `${Math.round(hh / 24)} días`);
const JEFATURA = ['direccion', 'finanzas_direccion', 'operaciones', 'proyectos', 'jefa_crm', 'tecnico_altas'];

// Sin hoja propia (N6, auditoría 30): solo clases comunes de estilos.css y `style` en línea con tokens.
const ESP = { gap: 'var(--s-2)', flexWrap: 'nowrap' };   // fila apretada (avatar + nombre)
// En vez de un «—» de 24 px: texto pequeño en la tarjeta gris (toString para que la etiqueta accesible de tile() diga «sin dato»).
const sinDato = (texto = 'Sin dato') => Object.assign(h('span', { class: 'sub', style: { fontWeight: 600 } }, texto), { toString: () => texto.toLowerCase() });
/** Estado de una fila de tabla: punto de color + texto en tinta (guía 3.8), no una pastilla en cada fila. */
const puntoEstado = (estado, texto) => h('span', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'nowrap', whiteSpace: 'nowrap', fontWeight: '600' } },
  h('span', { 'aria-hidden': 'true', style: { width: 'var(--s-2)', height: 'var(--s-2)', borderRadius: 'var(--r-full)', flex: 'none', background: `var(--${({ rojo: 'bad', ambar: 'warn', verde: 'good' })[estado] || 'off'})` } }), texto);
/** Bloque plegado al pie (explicaciones, listas largas). dentro: sin caja de panel (va dentro de otro panel). */
function plegable(titulo, contenido, { icono: ico = 'chev', dentro = false } = {}) {
  return h('details', { class: dentro ? null : 'panel', style: dentro ? { borderTop: 'var(--borde-suave)' } : { padding: 0 } },
    h('summary', { style: { padding: 'var(--s-3) var(--relleno)', minHeight: 'var(--s-10)', cursor: 'pointer', font: dentro ? 'var(--t-h3)' : 'var(--t-h2)', color: dentro ? 'var(--accent)' : null, display: 'flex', gap: 'var(--s-2)', alignItems: 'center' } }, icono(ico), titulo),
    contenido);
}
/** Rojo con cuentagotas (guía 3.4): de las filas que el umbral pone en rojo, solo el tercio más grave lleva el punto rojo;
 *  el resto, ámbar. El texto del estado no cambia. Devuelve una función fila → 'rojo' | 'ambar' | estado original. */
function cuentagotas(filas, estadoDe, peso) {
  const rojas = filas.filter(r => estadoDe(r) === 'rojo').sort((a, b) => peso(b) - peso(a));
  const tope = Math.max(1, Math.ceil(filas.length / 3));
  const quedan = new Set(rojas.length > tope ? rojas.slice(0, tope) : rojas);
  return r => { const e = estadoDe(r); return e === 'rojo' && !quedan.has(r) ? 'ambar' : e; };
}
const pesoSub = f => (f.sin_tocar_24h || 0) + (f.citas_14d?.sin_estado || 0) * 2 + (f.citas_14d?.sin_estado_max_h || 0) / 24 + (f.leads_30d || 0) / 100;
/** «⋯» del móvil: el resto de botones de una fila, en un <details> con .menu-flot (menuMas() pinta «null» cerrado; ver dudas_pintura.md).
 *  El menú se abre en su sitio (no flota) para que el panel, que recorta lo que sale de él, no lo corte. */
function masAcciones(botones, nombre) {
  if (!botones.length) return null;
  const caja = h('details', { class: 'periodo-mas menu-mas', style: { display: 'inline-grid', justifyItems: 'end' } },
    h('summary', { class: 'bt mini', style: { display: 'inline-flex', listStyle: 'none' }, 'aria-label': `Más acciones de ${nombre}` }, '⋯'),
    h('div', { class: 'menu-flot', role: 'menu', style: { position: 'static', boxShadow: 'none', marginTop: 'var(--s-2)', minWidth: 0 } }, botones));
  caja.addEventListener('keydown', e => { if (e.key === 'Escape') { caja.open = false; caja.querySelector('summary')?.focus(); } });
  return caja;
}
const MOVIL = () => window.matchMedia?.('(max-width: 640px)').matches;   // en el móvil, tablas de 8 filas
const numFuerte = n => (n ? h('b', { style: { fontVariantNumeric: 'tabular-nums' } }, fmt.num(n)) : fmt.num(n ?? 0));

// ------------------------------------------------------------------ datos y vista
async function cargar(ctx) {
  let d;
  try { d = await ctx.datosModulo('crm/crm'); } catch (e) { return { error: e.message || String(e) }; }
  if (!d || !Array.isArray(d.subcuentas)) return { error: 'No hay datos del CRM. Lanza fuentes_crm/generar_crm.py.' };
  const cli = new Map(ctx.clientes.map(c => [c.id, c]));
  for (const f of d.subcuentas) {
    const c = f.cliente_id ? cli.get(f.cliente_id) : null;
    f.logo = c?.logo || null;
    f.enCartera = !!(f.cliente_id && ctx.carteraIds.has(f.cliente_id));
    f.mot1 = f.motivos?.[0] || null;
    const v = f.cliente_id ? ctx.verdad(f.cliente_id) : null;     // verdad única: account y gravedad del cliente
    if (v?.account !== undefined) f.account_id = v.account || null;
    f.gravedad_cliente = v?.gravedad || null;
    f.especialista = f.especialista_id ? ctx.nombre(f.especialista_id) : null;
    f.account = f.account_id ? ctx.nombre(f.account_id) : null;
  }
  for (const e of d.especialistas || []) e.nombre = ctx.nombre(e.id);
  d.revisados = new Map();
  if (ctx.servidor && ctx.api) {
    try {
      const r = await ctx.api('acciones?modulo=salud-crm');
      for (const a of (r.acciones || []).slice().reverse()) if (a.tipo === 'revisado_lead' || a.tipo === 'revisado_cita') d.revisados.set(a.objeto, a);
    } catch { /* sin revisados: la lista sale entera */ }
  }
  return d;
}

/** Qué subcuentas ve esta persona y con qué mirada. */
function vista(ctx, d) {
  const puestos = ctx.persona.puestos;
  const jefatura = puestos.some(p => JEFATURA.includes(p)) && ctx.nivel === 'todo';
  const especialista = puestos.includes('especialista_ghl');
  const resumen = ctx.nivel === 'resumen';
  const reales = d.subcuentas.filter(f => f.tipo === 'cliente' || f.tipo === 'sin_cliente');
  let mias;
  if (ctx.nivel === 'suyo') mias = reales.filter(f => f.enCartera || (especialista && f.especialista_id === ctx.persona.id));
  else mias = reales.filter(f => f.enCartera || f.especialista_id === ctx.persona.id);
  const base = ctx.nivel === 'suyo' ? mias : reales;
  const verCompararPersonas = ctx.ver({ tipo: 'comparar_personas' }).ok;
  return { jefatura, especialista, resumen, reales, mias, base, verCompararPersonas,
    etiqueta: jefatura ? 'Toda la casa' : ctx.nivel === 'suyo' ? (especialista ? 'Tus subcuentas' : 'Tus clientes') : 'Resumen de tus clientes' };
}

function sumar(filas) {
  const enc = filas.filter(f => f.encendida);
  const s = (fn) => filas.reduce((a, f) => a + (fn(f) || 0), 0);
  const cel = s(f => f.citas_30d?.celebradas), nop = s(f => f.citas_30d?.no_presentadas);
  const juz = s(f => f.velocidad?.juzgables), en1 = s(f => f.velocidad?.en_1h);
  const wa = s(f => f.whatsapp?.enviados), waf = s(f => f.whatsapp?.fallidos);
  return {
    filas, enc, verde: enc.filter(f => f.estado === 'verde').length, rojo: enc.filter(f => f.estado === 'rojo').length, ambar: enc.filter(f => f.estado === 'ambar').length,
    pctVerde: enc.length ? Math.round(enc.filter(f => f.estado === 'verde').length * 1000 / enc.length) / 10 : null,
    leads: s(f => f.leads_30d), sinTocar: s(f => f.sin_tocar_24h), sinEstado14: s(f => f.citas_14d?.sin_estado),
    agendadas30: s(f => f.citas_30d?.agendadas), celebradas: cel, noPresentadas: nop, asistencia: cel + nop ? Math.round(cel * 1000 / (cel + nop)) / 10 : null,
    futuras: s(f => f.citas_30d?.futuras), estancados: s(f => f.embudo?.estancados_72h), opps30: s(f => f.embudo?.cohorte_30d), agendadas14: s(f => f.citas_14d?.agendadas), juzgables: juz, en1h: en1, pct1h: juz ? Math.round(en1 * 1000 / juz) / 10 : null,
    wa, waf, pctWa: wa ? Math.round(waf * 1000 / wa) / 10 : null,
  };
}

const frescuraGHL = d => ({ fuente: 'GHL', fecha: d.fuentes?.ghl?.hora, estado: d.fuentes?.ghl?.estado === 'bien' ? 'ok' : 'viejo' });
const frescuraCap = d => ({ fuente: 'Embudo (captación)', fecha: d.fuentes?.captacion?.hora, estado: 'ok' });

// ------------------------------------------------------------------ botones (simulación)
function accionSim(ctx, { texto, pregunta, tipo, herramienta = 'ghl', objeto, cliente_id, vista_previa, mini = true, peligro }) {
  return botonConfirmar({
    texto, mini, pregunta, confirmar: 'Sí (simulación)', soloLectura: ctx.soloLectura, peligro,
    alConfirmar: async () => {
      const prev = typeof vista_previa === 'function' ? vista_previa() : vista_previa;
      if (prev === null) throw new Error('Rellena el dato antes');
      await ctx.accion({ herramienta, tipo, objeto: String(typeof objeto === 'function' ? objeto() : objeto).slice(0, 200), cliente_id: cliente_id || undefined, texto: prev, vista_previa: prev });
      return 'En la cola (simulación)';
    },
  });
}
const tareaAccount = (ctx, f, que) => f.account
  ? accionSim(ctx, { texto: `Tarea a ${f.account}`, pregunta: `¿Crear tarea a ${f.account}?`, tipo: 'tarea', herramienta: 'clickup', objeto: `${f.nombre} · ${que}`, cliente_id: f.cliente_id,
    vista_previa: `Crearía en ClickUp una tarea para ${f.account} (account de ${f.nombre}): «${que}». En el prototipo no se crea (W1).` })
  : null;
const abrirGHL = (url, texto = 'Abrir en GHL') => url ? h('a', { class: 'bt mini', href: url, target: '_blank', rel: 'noopener' }, icono('ext'), texto) : null;

async function verDatosLead(ctx, fila, caja, boton) {
  boton.disabled = true;
  try {
    const r = await ctx.verDato({ almacen: 'crm/_privado/leads', ref: fila.ref, campo: 'datos', cliente_id: fila.cliente_id });
    const v = r.valor || {};
    caja.replaceChildren(botonesContacto({ nombre: v.nombre || 'Lead', telefono: v.telefono, correo: v.correo, fuente: 'GoHighLevel · queda en el rastro' }));
    boton.remove();
  } catch (e) {
    boton.disabled = false;
    avisoFlotante(e.message || 'No se pudo abrir', { icono: 'candado' });
  }
}
function botonVerDatos(ctx, fila, vis) {
  if (!ctx.servidor || vis.resumen || ctx.soloLectura) return null;
  if (!ctx.ver({ tipo: 'lead', cliente_id: fila.cliente_id }).desenmascarable) return null;
  const caja = h('div', { style: { marginTop: 'var(--s-2)' } });
  const b = h('button', { type: 'button', class: 'bt mini', title: 'Nombre, teléfono y correo del lead. Queda en el rastro.' }, icono('ojo'), 'Ver datos');
  b.addEventListener('click', () => verDatosLead(ctx, fila, caja, b));
  return h('span', {}, b, caja);
}

// ------------------------------------------------------------------ pantalla principal
function pintarInicio(cont, ctx, d) {
  const vis = vista(ctx, d);
  const S = sumar(vis.base);
  const casa = sumar(vis.reales);
  ctx.titulo('Salud del CRM', `${vis.etiqueta} · ${vis.base.length} subcuentas de GoHighLevel · 30 días naturales cerrados · dato de las ${(d.fuentes?.ghl?.hora || '').slice(11) || '—'}`);

  if (!vis.base.length) {
    cont.append(vacio({ icono: 'base', titulo: ctx.nivel === 'suyo' ? 'No tienes subcuentas de GoHighLevel a tu cargo' : 'No hay subcuentas que enseñar',
      texto: ctx.nivel === 'suyo' ? (ctx.carteraIds?.size ? 'Ninguno de tus clientes tiene subcuenta de GoHighLevel emparejada. Lo empareja Agus.' : motivoSinCartera(ctx)) : 'El fichero del CRM no trae subcuentas para tu puesto.',
      quien: 'Mili', borde: true }));
    return;
  }

  // ---- cabecera: de quién es la vista y frescura
  const cabecera = h('div', { class: 'fila', style: { justifyContent: 'space-between', gap: 'var(--s-2) var(--s-4)' } },
    h('span', { class: 'fila', style: ESP }, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(ctx.persona.alias || ctx.persona.nombre)),
      h('span', { class: 'sub' }, `${vis.etiqueta} · ${S.enc.length} con campaña o leads entrando · foto de ahora con ventanas fijas de 24 h, 14 y 30 días`)),
    h('div', { class: 'fila' }, frescura(frescuraGHL(d)), frescura(frescuraCap(d))));
  const ctxNodos = [cabecera];   // Ronda U: lo de leer va DEBAJO de la lista (pantallaAncha), plegado

  // ---- 1 · lo primero hoy (máximo 7): lo que pide acción va arriba (guía 3.6)
  let pest = null;
  const ir = (id) => () => { pest?.elegir(id); pest?.scrollIntoView({ behavior: 'smooth', block: 'start' }); };
  const prim = [];
  const ordenadas = [...vis.base].filter(f => f.estado === 'rojo' || f.estado === 'ambar')
    .sort((a, b) => EST[a.estado].o - EST[b.estado].o || ((b.sin_tocar_24h || 0) + (b.citas_14d?.sin_estado || 0)) - ((a.sin_tocar_24h || 0) + (a.citas_14d?.sin_estado || 0)) || (b.leads_30d || 0) - (a.leads_30d || 0));
  const integ = ordenadas.filter(f => f.motivos.some(m => m.clave === 'integracion'));
  for (const f of [...integ, ...ordenadas.filter(x => !integ.includes(x))].slice(0, 7)) {
    const m = f.motivos.find(x => x.clave === 'integracion') || f.motivos[0];
    prim.push({
      estado: f.estado, icono: ICO_MOT[m.clave] || 'alert', motivo: `${f.nombre} · ${m.texto}`,
      detalle: `${f.motivos.length > 1 ? `Y ${f.motivos.length - 1} motivo${f.motivos.length > 2 ? 's' : ''} más. ` : ''}Lo arregla: ${QUIEN_MOT[m.clave] || 'especialista'}${f.especialista ? ` · especialista: ${f.especialista}` : ' · sin especialista asignado'}${f.account ? ` · account: ${f.account}` : ''}.`,
      botones: (() => {
        const principal = h('a', { class: 'bt mini', href: `#/${ID}/${f.sub_id}` }, icono('base'), 'Ver subcuenta');
        const resto = [abrirGHL(m.clave === 'sin_estado' || m.clave === 'sin_citas' ? f.enlaces.calendarios : m.clave === 'integracion' ? f.enlaces.contactos : f.enlaces.conversaciones),
          !vis.resumen ? tareaAccount(ctx, f, m.texto) : null].filter(Boolean);
        return MOVIL() ? [h('div', { class: 'fila', style: { alignItems: 'flex-start', justifyContent: 'flex-end' } }, principal, masAcciones(resto, f.nombre))] : [principal, ...resto];
      })(),
    });
  }
  ctxNodos.push(panel({ titulo: 'Lo primero hoy', icono: 'zap', sub: vis.jefatura ? 'Las subcuentas que más pierden hoy y quién lo arregla. Las de integración rota, arriba.' : 'Tus subcuentas, lo más grave arriba' },
    prim.length ? listaLoPrimero(prim.slice(0, MOVIL() ? 4 : 7)) : null,
    prim.length > 4 && MOVIL() ? plegable(`Ver las ${prim.length - 4} restantes`, listaLoPrimero(prim.slice(4)), { dentro: true }) : null,
    prim.length ? null : h('div', { class: 'cuerpo' }, vacioLinea('Ninguna subcuenta en rojo: leads tocados, citas marcadas y WhatsApp sin fallos.', { icono: 'ok' }))));

  // ---- 2 · cifras (etiqueta de una línea, cifra, una línea de contexto y adónde lleva: 4 líneas como mucho)
  const fichas = [];
  const sd = (v, txt) => (v === null || v === undefined ? sinDato(txt) : v);
  fichas.push(tile({
    icono: 'base', etiqueta: vis.jefatura ? 'CRM en verde' : ctx.nivel === 'suyo' ? 'Mis subcuentas en verde' : 'Subcuentas en verde', valor: sd(S.pctVerde === null ? null : pc(S.pctVerde)),
    unidad: S.pctVerde === null ? '' : `${S.verde} de ${S.enc.length}`, estado: S.pctVerde === null ? 'gris' : semaforo(S.pctVerde, { verde: 80, ambar: 60 }),
    contexto: `El número de ${JEFA} · bien desde el 80 % · a medias`, ir: 'Ver subcuentas', alPulsar: ir('subcuentas'),
  }));
  fichas.push(tile({
    icono: 'users', etiqueta: 'Asistencia · 30 días', valor: sd(S.asistencia === null ? null : pc(S.asistencia), 'Sin dato'),
    unidad: S.asistencia === null ? '' : `${S.celebradas} de ${S.celebradas + S.noPresentadas}`, estado: S.asistencia === null ? 'gris' : semaforo(S.asistencia, { verde: 75, ambar: 60 }),
    contexto: S.asistencia === null ? (S.agendadas30 ? 'Ninguna cita de los últimos 30 días tiene marcado si vino: márcalas en GoHighLevel y sale el porcentaje. Las de 14 días, en «Citas sin estado».' : 'Sin citas en tus subcuentas en 30 días.') : 'Bien desde el 75 % · a medias', ir: 'Ver citas sin estado', alPulsar: ir('citas'),
  }));
  fichas.push(tile({
    icono: 'phone', etiqueta: 'Sin tocar > 24 h', valor: fmt.num(S.sinTocar), unidad: `de ${fmt.num(S.leads)} leads`,
    estado: !S.leads ? 'gris' : S.sinTocar === 0 ? 'verde' : 'rojo', contexto: S.leads ? 'Ningún intento en GHL · bien solo con 0' : 'Sin leads en 30 días', ir: 'Ver los leads', alPulsar: ir('leads'),
  }));
  fichas.push(tile({
    icono: 'cal', etiqueta: 'Citas sin estado · 14 d', valor: fmt.num(S.sinEstado14), unidad: 'sin marcar',
    estado: !S.agendadas14 ? 'gris' : vis.jefatura ? semaforo(S.sinEstado14, { verde: 0, ambar: 20, mejorSi: 'bajo' }) : semaforo(S.sinEstado14, { verde: 0, ambar: 5, mejorSi: 'bajo' }),
    contexto: vis.jefatura ? 'Verde 0 · ámbar 1-20 · rojo > 20' : 'Verde 0 · ámbar 1-5 · rojo > 5', ir: 'Marcarlas', alPulsar: ir('citas'),
  }));
  fichas.push(tile({
    icono: 'clock', etiqueta: '1.er intento < 1 h', valor: sd(S.pct1h === null ? null : pc(S.pct1h)), unidad: S.pct1h === null ? '' : `${S.en1h} de ${S.juzgables}`,
    estado: S.pct1h === null ? 'gris' : semaforo(S.pct1h, { verde: 70, ambar: 40 }), contexto: 'Garantía: ≥ 70 % en < 1 h · a medias', ir: 'Ver por subcuenta', alPulsar: ir('subcuentas'),
  }));
  fichas.push(tile({
    icono: 'hist', etiqueta: 'Paradas > 72 h', valor: S.opps30 ? fmt.num(S.estancados) : sinDato('Sin oportunidades'),
    estado: !S.opps30 ? 'gris' : S.estancados ? 'ambar' : 'verde', unidad: S.opps30 ? `de ${fmt.num(S.opps30)}` : '', contexto: 'Leads del mes sin cambiar de etapa', ir: 'Ver cuáles', alPulsar: ir('paradas'),
  }));
  fichas.push(tile({
    icono: 'wa', etiqueta: 'WhatsApp fallido', valor: sd(S.pctWa === null ? null : pc(S.pctWa), 'Sin envíos'), unidad: S.pctWa === null ? '' : `${S.waf} de ${S.wa}`,
    estado: S.wa ? semaforo(S.pctWa, { verde: 2, ambar: 10, mejorSi: 'bajo' }) : 'gris', contexto: 'Verde < 2 % · rojo > 10 %', ir: 'Ver WhatsApp y flujos', alPulsar: ir('flujos'),
  }));
  if (vis.jefatura) {
    const masCarga = [...(d.especialistas || [])].sort((a, b) => b.clientes - a.clientes)[0];
    fichas.push(tile({
      icono: 'eq', etiqueta: 'Especialista más cargado', valor: masCarga ? masCarga.clientes : sinDato(),
      unidad: masCarga ? `de ${masCarga.tope}` : '', estado: masCarga ? (masCarga.clientes > masCarga.tope ? 'rojo' : masCarga.clientes >= 14 ? 'ambar' : 'verde') : 'gris',
      contexto: masCarga ? `${ctx.nombre(masCarga.id)} · ${(d.resumen?.encendidas_sin_especialista || []).length} encendidas sin especialista` : 'Sin especialistas en asignaciones',
      ir: 'Ver por especialista', alPulsar: ir('especialistas'),
    }));
  }
  ctxNodos.push(rejillaTarjetas(fichas));

  // ---- 3 · pestañas (lo revisado con motivo ya no sale: la lista baja de verdad)
  const rev = d.revisados || new Map();
  const leads = (d.leads_sin_tocar || []).filter(x => vis.base.some(f => f.sub_id === x.sub_id) && !rev.has(claveRev('lead', x)));
  const citas = (d.citas_sin_estado || []).filter(x => vis.base.some(f => f.sub_id === x.sub_id) && !rev.has(claveRev('cita', x)));
  const paradas = (d.oportunidades_paradas || []).filter(x => vis.base.some(f => f.sub_id === x.sub_id));
  const defs = [
    { id: 'subcuentas', texto: 'Subcuentas', icono: 'base', cuenta: S.rojo, cuentaEstado: 'rojo' },
    !vis.resumen ? { id: 'leads', texto: 'Leads sin tocar', icono: 'phone', cuenta: leads.length, cuentaEstado: 'rojo' } : null,
    !vis.resumen ? { id: 'citas', texto: 'Citas sin estado', icono: 'cal', cuenta: citas.length, cuentaEstado: 'rojo' } : null,
    !vis.resumen ? { id: 'paradas', texto: 'Paradas', icono: 'hist', cuenta: paradas.length } : null,
    vis.jefatura || (vis.especialista && vis.verCompararPersonas) ? { id: 'especialistas', texto: 'Especialistas', icono: 'eq' } : null,
    { id: 'flujos', texto: 'Flujos y WhatsApp', icono: 'zap' },
    !vis.resumen ? { id: 'montajes', texto: 'Altas', icono: 'rocket', cuenta: (d.montajes || []).filter(m => vis.jefatura || ctx.carteraIds.has(m.cliente_id)).length } : null,
  ].filter(Boolean);
  // Quien trabaja la lista (especialista, jefa de CRM) abre en «Leads sin tocar»; el resto, en Subcuentas.
  const trabajaLista = !vis.resumen && (vis.especialista || ctx.persona.puestos.includes('jefa_crm'));
  pest = pestanas({
    pestanas: defs, clave: 'crm.pestana', etiqueta: 'Salud del CRM', activa: trabajaLista && leads.length ? 'leads' : trabajaLista && citas.length ? 'citas' : 'subcuentas',
    pintar: (id, zona) => {
      if (id === 'subcuentas') pintarSubcuentas(zona, ctx, d, vis);
      if (id === 'leads') pintarLeads(zona, ctx, d, vis, leads);
      if (id === 'citas') pintarCitas(zona, ctx, d, vis, citas);
      if (id === 'paradas') pintarParadas(zona, ctx, d, vis, paradas);
      if (id === 'especialistas') pintarEspecialistas(zona, ctx, d, vis);
      if (id === 'flujos') pintarFlujos(zona, ctx, d, vis);
      if (id === 'montajes') pintarMontajes(zona, ctx, d, vis);
    },
  });

  // ---- 4 · hallazgos de la casa (semanal) e indicadores con su umbral
  const hall = (d.hallazgos || []).filter(x => !x.cliente_id || vis.base.some(f => f.cliente_id === x.cliente_id));
  if (hall.length) {
    // Lista propia con clases comunes (no .primero: en el móvil la carcasa sube al principio todo lo que sea «Lo primero»).
    const lista = xs => h('ul', { class: 'pila', style: { listStyle: 'none', margin: 0, padding: 0, gap: 0 } }, xs.map(x => h('li', {
      style: { display: 'grid', gridTemplateColumns: 'auto minmax(0, 1fr) auto', gap: 'var(--s-1) var(--s-3)', alignItems: 'start', padding: 'var(--s-3) var(--relleno)', borderTop: 'var(--borde-suave)' } },
      h('span', { class: `ico-c s ${x.estado === 'rojo' ? 'rojo' : 'ambar'}` }, icono(x.estado === 'rojo' ? 'alert' : 'info')),
      h('div', { style: { minWidth: 0 } }, h('b', { style: { font: 'var(--t-h3)' } }, x.titulo), h('p', { class: 'sub', style: { margin: 'var(--s-1) 0 0', maxWidth: '72ch' } }, x.texto)),
      x.prueba ? h('a', { class: 'bt mini', href: x.prueba, target: '_blank', rel: 'noopener' }, icono('ext'), 'Ver prueba') : h('span'))));
    const N = MOVIL() ? 3 : 5;
    ctxNodos.push(panel({ titulo: 'Hallazgos', icono: 'flag', sub: 'Lo que el dato dice que se rompe, con la prueba en GoHighLevel' },
      lista(hall.slice(0, N)),
      hall.length > N ? plegable(`Ver los ${hall.length - N} hallazgos restantes`, lista(hall.slice(N)), { dentro: true }) : null));
  }
  ctxNodos.push(indicadoresPuesto(ctx, S, casa, vis));
  ctxNodos.push(plegable('Cómo se cuenta', h('div', { class: 'cuerpo pila' },
    h('p', { style: { margin: 0, maxWidth: '72ch' } }, `${d.reglas?.lead || ''} Un «intento» es una llamada o un mensaje que sale de GoHighLevel hecho por una persona (no por un flujo): las llamadas del despacho desde su móvil no constan, por eso «sin tocar» y la velocidad van «a medias». Encendida = campaña de Meta activa o 3 o más leads en 30 días.`),
    h('p', { style: { margin: 0, maxWidth: '72ch' } }, `Esta pantalla es una foto de ahora con ventanas fijas (leads de 30 días, citas de 14 y 30 días, «sin tocar» a las 24 h, paradas a las 72 h); no depende de ningún periodo. ${d.ventanas?.leads ? `Ventanas: ${d.ventanas.leads}.` : ''}`),
    h('p', { style: { margin: 0, maxWidth: '72ch' } }, 'Los flujos con error no salen por la API y la asistencia depende de que el despacho marque las citas: por eso varias cifras van «a medias».'),
    h('p', { style: { margin: 0, maxWidth: '72ch' } }, 'En las tablas, el punto rojo marca solo el tercio más grave (más leads y citas sin atender, o más horas esperando); el resto de lo que pasa el umbral va con punto ámbar. El texto («En rojo», las horas) no cambia.')), { icono: 'info' }));
  ctxNodos.push(h('p', { class: 'sub', style: { margin: 0 } }, `GoHighLevel leído el ${d.fuentes?.ghl?.hora || '—'} en hora de Madrid (${fmt.num(d.fuentes?.ghl?.llamadas)} lecturas, solo lectura) · Meta de Captación del ${d.fuentes?.captacion?.hora || '—'}`));

  // ---- franja de cifras (filtran la lista: llevan a su pestaña) + lista + contexto debajo
  const franja = franjaCifras([
    !vis.resumen ? { etiqueta: 'Sin tocar > 24 h', valor: leads.length, estado: leads.length ? 'rojo' : '', alPulsar: () => pest.elegir('leads') } : null,
    !vis.resumen ? { etiqueta: 'Citas sin estado', valor: citas.length, estado: citas.length ? 'rojo' : '', alPulsar: () => pest.elegir('citas') } : null,
    { etiqueta: 'En rojo', valor: S.rojo, estado: S.rojo ? 'rojo' : '', alPulsar: () => pest.elegir('subcuentas') },
    !vis.resumen ? { etiqueta: 'Paradas > 72 h', valor: paradas.length, alPulsar: () => pest.elegir('paradas') } : null,
    { etiqueta: 'WhatsApp fallido', valor: S.pctWa === null ? 'sin envíos' : pc(S.pctWa), alPulsar: () => pest.elegir('flujos') },
    rev.size ? { etiqueta: 'Revisados con motivo', valor: rev.size, titulo: 'Leads y citas que alguien revisó y salieron de la lista' } : null,
  ], { etiqueta: 'Cifras del CRM (llevan a su lista)' });
  cont.append(pantallaAncha({ id: ID, filtros: franjaEnLinea(franja), lista: pest, contexto: ctxNodos, tituloContexto: 'Lo primero hoy, cifras e indicadores' }));
}

// ------------------------------------------------------------------ pestaña: subcuentas
function pintarSubcuentas(zona, ctx, d, vis) {
  const todas = vis.jefatura ? d.subcuentas : vis.base;
  const cuenta = e => todas.filter(f => (e === 'pruebas' ? (f.tipo === 'prueba' || f.tipo === 'interna') : f.estado === e && f.tipo !== 'prueba' && f.tipo !== 'interna')).length;
  const opciones = [
    { valor: 'activas', texto: 'Con actividad', icono: 'zap', cuenta: todas.filter(f => f.estado !== 'gris').length },
    { valor: 'rojo', texto: 'En rojo', icono: 'fire', cuenta: cuenta('rojo'), cuentaEstado: 'rojo' },
    { valor: 'ambar', texto: 'Vigilar', icono: 'alert', cuenta: cuenta('ambar') },
    { valor: 'verde', texto: 'En verde', icono: 'ok', cuenta: cuenta('verde') },
    { valor: 'gris', texto: 'Sin actividad', icono: 'vacio', cuenta: cuenta('gris') },
    { valor: '', texto: 'Todas', cuenta: todas.length },
  ];
  if (vis.jefatura) opciones.splice(5, 0, { valor: 'pruebas', texto: 'Pruebas e internas', icono: 'aj', cuenta: cuenta('pruebas') });
  if (!vis.jefatura && vis.mias.length && vis.base !== vis.mias) opciones.unshift({ valor: 'mias', texto: 'Mis subcuentas', icono: 'persona', cuenta: vis.mias.length });
  const caja = h('div');
  const chips = chipsFiltro({ etiqueta: 'Estado', clave: 'crm.estado', opciones, valor: 'activas', alCambiar: () => pintar() });
  const pintar = () => {
    const v = chips.valor();
    const filas = todas.filter(f => v === '' ? true : v === 'activas' ? f.estado !== 'gris' : v === 'pruebas' ? (f.tipo === 'prueba' || f.tipo === 'interna') : v === 'mias' ? vis.mias.includes(f) : f.estado === v && f.tipo !== 'prueba' && f.tipo !== 'interna')
      .sort((a, b) => EST[a.estado].o - EST[b.estado].o || (b.leads_30d || 0) - (a.leads_30d || 0));
    const punto = cuentagotas(filas, f => f.estado, pesoSub);
    caja.replaceChildren(tablaDensa({
      filas, buscar: { campos: ['nombre', 'especialista', 'account', 'nombre_sub'], placeholder: 'Buscar subcuenta, especialista o account' },
      filtros: vis.jefatura ? [{ clave: 'especialista', titulo: 'Especialista' }] : [],
      columnas: [
        { clave: 'nombre', titulo: 'Subcuenta', principal: true, celda: f => h('span', { class: 'celda-cli', style: { minWidth: '200px' } }, logoCliente(f), h('span', { style: { display: 'grid', minWidth: 0 } }, f.nombre, f.tipo === 'sin_cliente' ? h('small', { class: 'sub', style: { fontWeight: 500, fontSize: 'var(--fs-12)' } }, 'sin cliente en la app') : null)) },
        { clave: 'estado', titulo: 'Estado', valor: f => EST[f.estado].o, celda: f => h('span', { style: { display: 'grid', gap: 'var(--s-1)', minWidth: '240px', maxWidth: '320px' } }, puntoEstado(punto(f), EST[f.estado].t),
          f.mot1 ? h('span', { class: 'sub', title: f.mot1.texto, style: { fontSize: 'var(--fs-12)', lineHeight: '16px', display: '-webkit-box', WebkitLineClamp: '2', WebkitBoxOrient: 'vertical', overflow: 'hidden', whiteSpace: 'normal' } }, f.mot1.texto) : null) },
        { clave: 'especialista', titulo: 'Especialista', celda: f => f.especialista ? h('span', { class: 'fila', style: ESP }, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(f.especialista)), f.especialista) : h('span', { class: 'sub', style: { whiteSpace: 'nowrap' } }, 'sin asignar') },
        { clave: 'leads_30d', titulo: 'Leads 30 d', num: true, celda: f => fmt.num(f.leads_30d) },
        { clave: 'sin_tocar_24h', titulo: 'Sin tocar', num: true, celda: f => numFuerte(f.sin_tocar_24h) },
        { clave: 'v1h', titulo: '1.er intento < 1 h', num: true, valor: f => f.velocidad?.pct_1h, celda: f => f.velocidad?.juzgables ? h('span', { style: { whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums' } }, `${pc(f.velocidad.pct_1h)} · ${f.velocidad.en_1h}/${f.velocidad.juzgables}`) : '—' },
        { clave: 'se', titulo: 'Citas sin estado 14 d', num: true, valor: f => f.citas_14d?.sin_estado, celda: f => numFuerte(f.citas_14d?.sin_estado) },
        { clave: 'asis', titulo: 'Asistencia 30 d', num: true, valor: f => f.citas_30d?.asistencia_pct, celda: f => f.citas_30d?.asistencia_pct !== null && f.citas_30d?.asistencia_pct !== undefined ? puntoEstado(semaforo(f.citas_30d.asistencia_pct, { verde: 75, ambar: 60 }), pc(f.citas_30d.asistencia_pct)) : h('span', { class: 'sub', style: { whiteSpace: 'nowrap' }, title: 'Ninguna cita marcada como celebrada o no presentada' }, f.citas_30d?.agendadas ? 'sin marcar' : '—') },
        { clave: 'ir', titulo: 'Abrir', ordenable: false, celda: f => abrirGHL(f.enlaces.ghl) },
      ],
      porPagina: MOVIL() ? 8 : 15,
      alPulsar: f => ctx.navegar(`${ID}/${f.sub_id}`),
      etiquetaFila: f => `${f.nombre}: ${EST[f.estado].t}${f.mot1 ? `, ${f.mot1.texto}` : ''}. Abrir`,
      vacio: { titulo: 'Ninguna subcuenta con este filtro', porque: 'Cambia el filtro de estado.' },
    }));
  };
  pintar();
  zona.append(panel({ titulo: 'Subcuentas de GoHighLevel', icono: 'base', sub: vis.jefatura ? `Las ${d.subcuentas.length} de la agencia; las de clientes con campaña, arriba. Pulsa una para ver su detalle.` : 'Tus subcuentas. Pulsa una para ver su detalle y actuar.' },
    h('div', { class: 'cuerpo', style: { paddingBottom: 'var(--s-1)' } }, chips), caja));
}

// ------------------------------------------------------------------ pestaña: leads sin tocar
function pintarLeads(zona, ctx, d, vis, leads) {
  leads = leads.filter(x => !d.revisados?.has(claveRev('lead', x)));
  const gota = cuentagotas(leads, x => (x.horas > 72 ? 'rojo' : 'ambar'), x => x.horas || 0);
  const porSub = new Map(d.subcuentas.map(f => [f.sub_id, f]));
  zona.append(panel({ titulo: 'Leads sin tocar más de 24 h', icono: 'phone', sub: 'Sin ninguna llamada ni mensaje de una persona en GoHighLevel. «Revisado» con su motivo lo saca de la lista (se puede deshacer). Los datos del lead van tapados: «Ver datos» queda en el rastro.' },
    tablaDensa({
      porPagina: MOVIL() ? 8 : 15, filas: leads, buscar: { campos: ['subcuenta', 'medio'], placeholder: 'Buscar subcuenta u origen' }, filtros: [{ clave: 'subcuenta', titulo: 'Subcuenta' }],
      orden: { clave: 'horas', dir: 'desc' },
      columnas: [
        { clave: 'subcuenta', titulo: 'Subcuenta', principal: true, celda: x => h('span', { class: 'celda-cli' }, logoCliente(porSub.get(x.sub_id) || { nombre: x.subcuenta }), x.subcuenta) },
        { clave: 'creado', titulo: 'Entró', celda: x => `${fDiaRO(x.creado)} · ${x.creado?.slice(11) || ''}` },
        { clave: 'horas', titulo: 'Esperando', num: true, celda: x => puntoEstado(gota(x), horasTxt(x.horas)) },
        { clave: 'medio', titulo: 'Origen', celda: x => h('span', { style: { display: 'inline-block', minWidth: '140px' } }, x.medio || '—') },
        { clave: 'automatico', titulo: 'Mensaje automático', celda: x => x.automatico ? 'Sí salió' : puntoEstado('ambar', 'No salió') },
        { clave: 'respondio', titulo: 'El lead escribió', celda: x => x.respondio ? puntoEstado('ambar', 'Sí, sin respuesta') : 'No' },
        { clave: 'acc', titulo: 'Acciones', ordenable: false, celda: x => h('span', { class: 'fila', style: { gap: 'var(--s-2)' } },
          // Ronda U: fila compacta · verbo principal (Revisado) + Ver datos + «⋯» con lo que sale fuera (GHL, nota, tarea)
          botonRevisado(ctx, x, 'lead', d), botonVerDatos(ctx, x, vis),
          masAcciones([abrirGHL(x.enlace, 'Abrir contacto en GHL'),
            accionSim(ctx, { texto: 'Nota en GHL', pregunta: '¿Poner la nota «sin contactar a las 24 h»?', tipo: 'nota', objeto: `${x.subcuenta} · lead ${x.ref}`, cliente_id: x.cliente_id,
              vista_previa: `Pondría en el contacto de GHL (${x.subcuenta}) la nota: «Sin contactar a las ${horasTxt(x.horas)} · revisado desde la app». Espera el permiso de GHL (falta un permiso de GoHighLevel).` }),
            porSub.get(x.sub_id) ? tareaAccount(ctx, porSub.get(x.sub_id), `Llamar al lead del ${fDiaRO(x.creado)} (${horasTxt(x.horas)} sin contactar)`) : null].filter(Boolean), `el lead de ${x.subcuenta}`)) },
      ],
      vacio: { titulo: 'Ningún lead sin tocar', porque: 'Todos los leads del mes tienen al menos un intento en GHL.' },
    })));
}

// ------------------------------------------------------------------ pestaña: oportunidades paradas 72 h
function pintarParadas(zona, ctx, d, vis, paradas) {
  const gota = cuentagotas(paradas, x => (x.horas > 7 * 24 ? 'rojo' : 'ambar'), x => x.horas || 0);
  const porSub = new Map(d.subcuentas.map(f => [f.sub_id, f]));
  zona.append(panel({ titulo: 'Oportunidades paradas más de 72 h', icono: 'hist', sub: 'Abiertas, creadas en el último mes y sin cambiar de etapa en 72 h. GoHighLevel no tiene enlace a una oportunidad suelta: el atajo abre el contacto, que enseña sus oportunidades.' },
    tablaDensa({
      porPagina: MOVIL() ? 8 : 15, filas: paradas, buscar: { campos: ['subcuenta', 'etapa'], placeholder: 'Buscar subcuenta o etapa' }, filtros: [{ clave: 'subcuenta', titulo: 'Subcuenta' }, { clave: 'etapa', titulo: 'Etapa' }],
      orden: { clave: 'horas', dir: 'desc' },
      columnas: [
        { clave: 'subcuenta', titulo: 'Subcuenta', principal: true, celda: x => h('span', { class: 'celda-cli' }, logoCliente(porSub.get(x.sub_id) || { nombre: x.subcuenta }), x.subcuenta) },
        { clave: 'etapa', titulo: 'Etapa', celda: x => x.etapa || '—' },
        { clave: 'creada', titulo: 'Creada', celda: x => fDiaRO(x.creada) },
        { clave: 'horas', titulo: 'Parada', num: true, celda: x => puntoEstado(gota(x), horasTxt(x.horas)) },
        { clave: 'acc', titulo: 'Acciones', ordenable: false, celda: x => h('span', { class: 'fila', style: { gap: 'var(--s-2)' } },
          !vis.resumen ? accionSim(ctx, { texto: 'Mover', pregunta: '¿Mover la oportunidad a «Seguimiento»?', tipo: 'mover_oportunidad', objeto: `${x.subcuenta} · oportunidad ${x.ref}`, cliente_id: x.cliente_id,
            vista_previa: `Movería la oportunidad (${x.etapa || 'sin etapa'}) de ${x.subcuenta} a «Seguimiento». Espera un permiso de GoHighLevel.` }) : null,
          abrirGHL(x.enlace, 'Abrir contacto en GHL')) },
      ],
      vacio: { titulo: 'Ninguna oportunidad parada', porque: 'Todas las del último mes se han movido en las últimas 72 h.' },
    })));
}

// ------------------------------------------------------------------ pestaña: citas sin estado
function pintarCitas(zona, ctx, d, vis, citas) {
  citas = citas.filter(x => !d.revisados?.has(claveRev('cita', x)));
  const gota = cuentagotas(citas, x => (x.horas > 48 ? 'rojo' : 'ambar'), x => x.horas || 0);
  const porSub = new Map(d.subcuentas.map(f => [f.sub_id, f]));
  zona.append(avisoParcial('Marcar el estado de una cita en GoHighLevel manda un WhatsApp al lead (ley de la casa). En el prototipo no se marca nada: queda en la cola con su vista previa hasta tener el permiso de GoHighLevel.', { titulo: 'Ojo al marcar.' }));
  zona.append(panel({ titulo: 'Citas de los últimos 14 días sin marcar', icono: 'cal', sub: 'Pasadas y sin «se presentó» ni «no se presentó». Sin marcar, la asistencia no se puede medir.' },
    tablaDensa({
      porPagina: MOVIL() ? 8 : 15, filas: citas, buscar: { campos: ['subcuenta', 'calendario'], placeholder: 'Buscar subcuenta o calendario' }, filtros: [{ clave: 'subcuenta', titulo: 'Subcuenta' }],
      orden: { clave: 'horas', dir: 'desc' },
      columnas: [
        { clave: 'subcuenta', titulo: 'Subcuenta', principal: true, celda: x => h('span', { class: 'celda-cli' }, logoCliente(porSub.get(x.sub_id) || { nombre: x.subcuenta }), x.subcuenta) },
        { clave: 'inicio', titulo: 'Cita', celda: x => `${fDiaRO(x.inicio)} · ${x.inicio?.slice(11) || ''}` },
        { clave: 'calendario', titulo: 'Calendario', celda: x => h('span', { style: { display: 'inline-block', minWidth: '160px' } }, x.calendario || '—') },
        { clave: 'horas', titulo: 'Sin marcar', num: true, celda: x => puntoEstado(gota(x), horasTxt(x.horas)) },
        { clave: 'acc', titulo: 'Acciones', ordenable: false, celda: x => h('span', { class: 'fila', style: { gap: 'var(--s-2)' } },
          botonRevisado(ctx, x, 'cita', d),
          masAcciones([accionSim(ctx, { texto: 'Se presentó', pregunta: '¿Marcar «se presentó»? Manda WhatsApp al lead', tipo: 'marcar_cita', objeto: `${x.subcuenta} · cita ${x.ref}`, cliente_id: x.cliente_id,
            vista_previa: `Marcaría en GHL la cita del ${fDiaRO(x.inicio)} ${x.inicio?.slice(11)} (${x.calendario}) como «se presentó». GHL avisará al lead por WhatsApp. Espera un permiso de GoHighLevel.` }),
          accionSim(ctx, { texto: 'No vino', pregunta: '¿Marcar «no se presentó»? Manda WhatsApp al lead', tipo: 'marcar_cita', objeto: `${x.subcuenta} · cita ${x.ref}`, cliente_id: x.cliente_id,
            vista_previa: `Marcaría en GHL la cita del ${fDiaRO(x.inicio)} ${x.inicio?.slice(11)} (${x.calendario}) como «no se presentó» y el flujo de reagendar le escribiría. Espera un permiso de GoHighLevel.` }),
          accionSim(ctx, { texto: 'Reprogramar', pregunta: '¿Proponer otra hora al lead?', tipo: 'reprogramar_cita', objeto: `${x.subcuenta} · cita ${x.ref}`, cliente_id: x.cliente_id,
            vista_previa: `Abriría la cita del ${fDiaRO(x.inicio)} para moverla y mandaría al lead el enlace de reagendar. Espera un permiso de GoHighLevel.` }),
          x.datos ? botonVerDatos(ctx, x, vis) : null, abrirGHL(x.enlace_contacto || x.enlace, x.enlace_contacto ? 'Abrir contacto en GHL' : 'Abrir calendario en GHL')].filter(Boolean), `la cita de ${x.subcuenta}`)) },
      ],
      vacio: { titulo: 'Todas las citas están marcadas', porque: 'Ninguna cita pasada de los últimos 14 días sin estado.' },
    })));
  if (porSub.size) {
    const top = [...porSub.values()].filter(f => vis.base.includes(f) && f.citas_30d?.agendadas).sort((a, b) => (b.citas_30d.sin_estado || 0) - (a.citas_30d.sin_estado || 0)).slice(0, 8);
    if (top.length) zona.append(panel({ titulo: 'Citas por subcuenta · 30 días', icono: 'users', sub: 'Agendadas, celebradas, no presentadas, sin estado y próximas' },
      tablaApilable({
        filas: top, columnas: [
          { clave: 'nombre', titulo: 'Subcuenta', principal: true },
          { clave: 'a', titulo: 'Agendadas', num: true, celda: f => fmt.num(f.citas_30d.agendadas) },
          { clave: 'c', titulo: 'Celebradas', num: true, celda: f => fmt.num(f.citas_30d.celebradas) },
          { clave: 'n', titulo: 'No vinieron', num: true, celda: f => fmt.num(f.citas_30d.no_presentadas) },
          { clave: 's', titulo: 'Sin estado', num: true, celda: f => fmt.num(f.citas_30d.sin_estado) },
          { clave: 'x', titulo: 'Canceladas', num: true, celda: f => fmt.num(f.citas_30d.canceladas) },
          { clave: 'f', titulo: 'Próximas', num: true, celda: f => fmt.num(f.citas_30d.futuras) },
        ],
        alPulsar: f => ctx.navegar(`${ID}/${f.sub_id}`),
      })));
  }
}

// ------------------------------------------------------------------ pestaña: por especialista (vista de Yessica)
function pintarEspecialistas(zona, ctx, d, vis) {
  const esp = (d.especialistas || []).filter(e => vis.jefatura || e.id === ctx.persona.id);
  const max = Math.max(16, ...esp.map(e => e.clientes));
  zona.append(panel({ titulo: 'Carga y salud por especialista', icono: 'eq', sub: 'Clientes con silla CRM en asignaciones (tope 16) y estado de sus subcuentas. Rojos por persona: verde ≤ 2 · rojo ≥ 5.' },
    tablaApilable({
      filas: esp,
      columnas: [
        { clave: 'nombre', titulo: 'Especialista', principal: true, celda: e => h('span', { class: 'fila', style: ESP }, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(e.nombre)), e.nombre) },
        { clave: 'clientes', titulo: 'Carga', celda: e => h('span', { style: { display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: 'var(--s-2)', alignItems: 'center', minWidth: '160px' } },
          barraProgreso({ valor: e.clientes, max, estado: e.clientes > e.tope ? 'rojo' : e.clientes >= 14 ? 'ambar' : 'verde', marca: e.tope, etiqueta: `${e.clientes} de ${e.tope} clientes` }), h('b', { style: { fontVariantNumeric: 'tabular-nums' } }, `${e.clientes}/${e.tope}`)) },
        { clave: 'encendidas', titulo: 'Encendidas', num: true },
        { clave: 'verde', titulo: 'Verde', num: true, celda: e => fmt.num(e.verde) },
        { clave: 'ambar', titulo: 'Vigilar', num: true, celda: e => fmt.num(e.ambar) },
        { clave: 'rojo', titulo: 'Rojo', num: true, celda: e => puntoEstado(semaforo(e.rojo, { verde: 2, ambar: 4, mejorSi: 'bajo' }), fmt.num(e.rojo)) },
        { clave: 'sin_tocar', titulo: 'Leads sin tocar', num: true },
        { clave: 'sin_estado', titulo: 'Citas sin estado', num: true },
        { clave: 'sin_subcuenta', titulo: 'Sin subcuenta emparejada', celda: e => e.sin_subcuenta?.length ? h('span', { class: 'sub', style: { display: 'inline-block', whiteSpace: 'normal', minWidth: '200px' } }, e.sin_subcuenta.join(', ')) : '—' },
        // Ronda U: «Proponer reparto a Mili» en la fila de quien pasa del tope o acumula rojos (interno: deshacer, sin «¿Seguro?»)
        vis.jefatura ? { clave: 'reparto', titulo: 'Reparto', ordenable: false, celda: e => (e.clientes > e.tope || e.rojo >= 5) && !ctx.soloLectura ? botonDeshacer({ texto: 'Proponer reparto a Mili', hecho: 'Propuesta enviada a Mili', icono: 'users',
          alHacer: async () => { await ctx.accion({ herramienta: 'app', tipo: 'proponer_reasignacion', objeto: `Carga de ${e.nombre}`, texto: `${e.nombre}: ${e.clientes} de ${e.tope} clientes y ${e.rojo} en rojo`, vista_previa: `Propone a Mili repartir parte de la cartera de CRM de ${e.nombre} (${e.clientes} de ${e.tope} clientes, ${e.rojo} subcuentas en rojo). Deciden Mili y Tomás.` }); return 'Propuesta en el Mi día de Mili'; } }) : h('span', { class: 'sub' }, '—') } : null,
      ].filter(Boolean),
      vacio: { titulo: 'Sin especialistas en asignaciones', texto: 'La silla CRM no tiene a nadie asignado todavía.' },
    })));
  const sin = d.resumen?.encendidas_sin_especialista || [];
  if (vis.jefatura) {
    zona.append(panel({ titulo: 'Encendidas sin especialista', icono: 'persona', sub: 'Subcuentas con campaña o leads entrando que nadie tiene en la silla CRM' },
      sin.length ? h('div', { class: 'cuerpo' }, h('div', { class: 'fila' }, sin.map(n => chipEstado('ambar', n))),
        h('div', { class: 'fila', style: { marginTop: 'var(--s-3)' } }, accionSim(ctx, { texto: 'Proponer reparto a Mili', pregunta: '¿Mandar la propuesta a Mili?', tipo: 'proponer_reasignacion', herramienta: 'app', objeto: 'Subcuentas sin especialista',
          vista_previa: `Propondría a Mili asignar la silla CRM de: ${sin.join(', ')}. Deciden Mili y Tomás.`, mini: false })))
        : h('div', { class: 'cuerpo' }, vacioLinea('Todas las encendidas tienen especialista.', { icono: 'ok' }))));
  }
}

// ------------------------------------------------------------------ pestaña: flujos, WhatsApp y correo
function pintarFlujos(zona, ctx, d, vis) {
  const filas = vis.base.filter(f => f.estado !== 'gris').sort((a, b) => (b.whatsapp?.fallidos || 0) - (a.whatsapp?.fallidos || 0) || (b.leads_30d || 0) - (a.leads_30d || 0));
  zona.append(h('div', { class: 'dos' },
    panel({ titulo: 'Flujos con error', icono: 'zap', sub: 'Lo que hoy no se puede leer y por qué' },
      h('div', { class: 'cuerpo' }, vacioLinea('Los flujos no salen por la API: falta un permiso de GoHighLevel y la pestaña de errores no consta. Mientras, el aviso es el correo diario de GHL.', { icono: 'candado', quien: 'Tomás (falta un permiso de GoHighLevel)' }))),
    panel({ titulo: 'Número de WhatsApp conectado', icono: 'wa', sub: 'Conectado, restringido o caído' },
      h('div', { class: 'cuerpo' }, vacioLinea('No medible por API. Sí se mide el fallo de cada mensaje (tabla de abajo): si todo falla, sospecha de número desconectado.', { icono: 'wa', quien: 'especialista (Ajustes › WhatsApp en GHL)' })))));
  zona.append(panel({ titulo: 'Por subcuenta: flujos, WhatsApp y correo', icono: 'base', sub: 'Mensajes a los leads del mes. «Abrir flujos» lleva a la pestaña de flujos de esa subcuenta.' },
    tablaDensa({
      porPagina: MOVIL() ? 8 : 15, filas, buscar: { campos: ['nombre', 'especialista'], placeholder: 'Buscar subcuenta' },
      columnas: [
        { clave: 'nombre', titulo: 'Subcuenta', principal: true, celda: f => h('span', { class: 'celda-cli' }, logoCliente(f), f.nombre) },
        { clave: 'auto', titulo: 'Automático en < 5 min', num: true, valor: f => f.velocidad?.auto_5min, celda: f => f.velocidad ? `${f.velocidad.auto_5min}/${f.leads_30d || 0}` : '—' },
        { clave: 'wa', titulo: 'WhatsApp fallido', num: true, valor: f => f.whatsapp?.pct_fallo, celda: f => f.whatsapp?.enviados ? puntoEstado(semaforo(f.whatsapp.pct_fallo, { verde: 2, ambar: 10, mejorSi: 'bajo' }), `${f.whatsapp.fallidos} de ${f.whatsapp.enviados}`) : h('span', { class: 'sub' }, 'sin envíos') },
        { clave: 'sms', titulo: 'SMS fallido', num: true, valor: f => f.sms?.fallidos, celda: f => f.sms?.enviados ? `${f.sms.fallidos} de ${f.sms.enviados}` : '—' },
        { clave: 'mail', titulo: 'Correos fallidos', num: true, valor: f => f.correo?.fallidos, celda: f => f.correo?.enviados ? `${f.correo.fallidos} de ${f.correo.enviados}` : '—' },
        { clave: 'num', titulo: 'Número WhatsApp', ordenable: false, celda: () => h('span', { class: 'sub' }, 'no medible') },
        { clave: 'ir', titulo: 'Abrir', ordenable: false, celda: f => h('span', { class: 'fila', style: { gap: 'var(--s-2)' } }, abrirGHL(f.enlaces.flujos, 'Abrir flujos en GHL'), abrirGHL(f.enlaces.whatsapp, 'Abrir WhatsApp en GHL')) },
      ],
      alPulsar: f => ctx.navegar(`${ID}/${f.sub_id}`),
      vacio: { titulo: 'Sin subcuentas con actividad', porque: 'No entra ningún lead en tus subcuentas.' },
    })));
  const ro = d.correo_ro || {};
  zona.append(panel({ titulo: 'Entregabilidad del correo', icono: 'mail', sub: 'Rebote y quejas: verde rebote < 2 % · ámbar 2-5 % · rojo quejas ≥ 0,3 %' },
    h('div', { class: 'cuerpo pila' },
      h('div', { class: 'fila' }, chipEstado(semaforo(ro.rebote_pct, { verde: 2, ambar: 5, mejorSi: 'bajo' }), `Subcuenta de RO: ${fmt.num(ro.rebote_pct, 1)} % de rebote`), h('span', { class: 'sub' }, `${ro.fuente || ''} · ${fDiaRO(ro.fecha)}`)),
      h('p', { class: 'sub', style: { margin: 0 } }, ro.nota || ''))));
}

// ------------------------------------------------------------------ pestaña: montajes de altas
function pintarMontajes(zona, ctx, d, vis) {
  const lista = (d.montajes || []).filter(m => vis.jefatura || ctx.carteraIds.has(m.cliente_id)).sort((a, b) => (a.dia ?? 99) - (b.dia ?? 99));
  const cli = new Map(ctx.clientes.map(c => [c.id, c]));
  zona.append(avisoParcial('Las casillas de CRM de cada alta. La hoja de ruta completa (firma → día 90) está en «Clientes nuevos». Flujos validados, WhatsApp conectado y la prueba del circuito no se pueden leer todavía: van en una línea aparte.', { tipo: 'info' }));
  if (!lista.length) { zona.append(panel({}, h('div', { class: 'cuerpo' }, vacioLinea('Ninguna alta en montaje: no hay clientes nuevos en los últimos 90 días a tu cargo.', { icono: 'rocket' })))); return; }
  const rejilla = xs => h('div', { class: 'rejilla', style: { gridTemplateColumns: 'repeat(auto-fill, minmax(min(300px, 100%), 1fr))', gap: 'var(--s-4)' } }, xs.map(m => h('article', { class: 'panel pila', style: { padding: 'var(--relleno)', gap: 'var(--s-3)', alignContent: 'start' } },
    h('header', { class: 'fila', style: { gap: 'var(--s-3)', flexWrap: 'nowrap' } }, logoCliente(cli.get(m.cliente_id) || { nombre: m.nombre }), h('div', { style: { minWidth: 0, flex: 1, display: 'grid' } }, h('b', { style: { font: 'var(--t-h3)' } }, m.nombre), h('span', { class: 'sub', style: { fontSize: 'var(--fs-12)' } }, `Día ${m.dia ?? '—'} desde el alta · CRM: ${m.crm || 'sin asignar'}`)),
      chipEstado(m.listas >= m.medibles ? 'verde' : m.sub_id ? 'ambar' : 'rojo', `${m.listas} de ${m.medibles}`)),
    h('div', { class: 'fila', style: { gap: 'var(--s-2)' } }, m.casillas.filter(c => c.medible !== 'no').map(c => h('span', { class: `chip ${c.estado}`, title: c.detalle, style: { whiteSpace: 'normal' } }, c.texto))),
    m.casillas.some(c => c.medible === 'no') ? h('p', { class: 'sub', style: { margin: 0, fontSize: 'var(--fs-12)' } }, `Todavía no se leen: ${m.casillas.filter(c => c.medible === 'no').map(c => c.texto).join(' · ')}.`) : null,
    h('div', { class: 'fila', style: { gap: 'var(--s-2)' } },
      h('a', { class: 'bt mini', href: `#/clientes-nuevos/${m.cliente_id}` }, icono('rocket'), 'Hoja de ruta'),
      m.sub_id ? h('a', { class: 'bt mini', href: `#/${ID}/${m.sub_id}` }, icono('base'), 'Subcuenta') : null, abrirGHL(m.enlace),
      accionSim(ctx, { texto: 'Formación dada', pregunta: '¿Apuntar la formación al despacho como dada?', tipo: 'casilla_montaje', herramienta: 'app', objeto: `${m.nombre} · formación`, cliente_id: m.cliente_id,
        vista_previa: `Apuntaría en la app que la formación de GHL al despacho de ${m.nombre} está dada (casilla del montaje).` })))));
  const N = MOVIL() ? 3 : 6;
  zona.append(rejilla(lista.slice(0, N)));
  if (lista.length > N) zona.append(plegable(`Ver las ${lista.length - N} altas restantes`, h('div', { class: 'cuerpo' }, rejilla(lista.slice(N))), { icono: 'rocket' }));
}

// ------------------------------------------------------------------ indicadores con su umbral firmado (abajo: semanal)
function indicadoresPuesto(ctx, S, casa, vis) {
  const ind = id => ctx.indicador(id);
  const fr = { fuente: 'GHL', estado: 'ok' };
  const items = [
    vis.jefatura ? fichaCatalogo(ind('jefa_crm.de_subcuentas_con_el_crm_en_verde_el_que_manda'), { valor: casa.pctVerde === null ? null : fmt.num(casa.pctVerde, 1), unidad: '%', estado: semaforo(casa.pctVerde, { verde: 80, ambar: 60 }), frescura: fr, icono: 'base', parcial: 'Sin los flujos con error (no se pueden leer).' }) : null,
    fichaCatalogo(ind('especialista_ghl.asistencia_a_las_citas_de_sus_despachos_el_que_m'), { valor: S.asistencia === null ? null : fmt.num(S.asistencia, 1), unidad: '%', estado: semaforo(S.asistencia, { verde: 75, ambar: 60 }), frescura: fr, icono: 'users', parcial: S.asistencia === null ? `0 de ${S.agendadas30} citas marcadas: sin dato.` : null }),
    fichaCatalogo(ind('especialista_ghl.citas_sin_estado'), { valor: S.sinEstado14, unidad: 'en 14 días', estado: semaforo(S.sinEstado14, { verde: 0, ambar: 5, mejorSi: 'bajo' }), frescura: fr, icono: 'cal' }),
    fichaCatalogo(ind('especialista_ghl.leads_sin_tocar_a_las_24_h'), { valor: S.sinTocar, estado: S.sinTocar ? 'rojo' : 'verde', frescura: fr, icono: 'phone', parcial: 'Solo intentos que pasan por GHL.' }),
    fichaCatalogo(ind('especialista_ghl.velocidad_del_despacho_con_el_lead'), { valor: S.pct1h === null ? null : fmt.num(S.pct1h, 1), unidad: '% en < 1 h', estado: semaforo(S.pct1h, { verde: 70, ambar: 40 }), frescura: fr, icono: 'clock' }),
    fichaCatalogo(ind('especialista_ghl.whatsapp_fallido_o_desconectado'), { valor: S.pctWa === null ? null : fmt.num(S.pctWa, 1), unidad: '%', estado: S.wa ? semaforo(S.pctWa, { verde: 2, ambar: 10, mejorSi: 'bajo' }) : 'gris', frescura: fr, icono: 'wa' }),
  ].filter(Boolean);
  const todos = ctx.indicadores().filter(i => /^(especialista_ghl|jefa_crm)\./.test(i.id || ''));
  return plegable('Indicadores del puesto con su umbral firmado', h('div', { class: 'cuerpo pila' }, rejillaTarjetas(items), pieFase2(todos)), { icono: 'medidor' });
}

// ------------------------------------------------------------------ detalle de una subcuenta
function pintarDetalle(cont, ctx, d, subId) {
  const vis = vista(ctx, d);
  const f = d.subcuentas.find(x => x.sub_id === subId);
  const volver = h('a', { class: 'bt', href: `#/${ID}` }, icono('volver'), 'Volver a Salud del CRM');
  if (!f || (ctx.nivel === 'suyo' && !vis.base.includes(f))) {
    ctx.titulo('Salud del CRM', '');
    cont.append(vacio({ icono: 'candado', titulo: 'Esta subcuenta no es de tu puesto o no existe', texto: `Solo ves las subcuentas de los clientes que llevas. Si necesitas una, habla con ${JEFA} o con Mili.`, accion: volver, borde: true }));
    return;
  }
  ctx.titulo(f.nombre, `Subcuenta de GoHighLevel «${f.nombre_sub}» · ${EST[f.estado].t}${f.especialista ? ` · especialista ${f.especialista}` : ''}`);
  const lista = (vis.jefatura ? d.subcuentas : vis.base).filter(x => x.estado !== 'gris' || x === f)
    .map(x => ({ id: x.sub_id, nombre: x.nombre, logo: x.logo, responsable: x.especialista ? `CRM: ${x.especialista}` : 'sin especialista', estado: x.estado }));
  cont.append(h('div', { class: 'fila', style: { justifyContent: 'space-between' } },
    h('nav', { class: 'migas', 'aria-label': 'Migas' }, h('a', { href: `#/${ID}` }, icono('base', { clase: 's' }), 'Salud del CRM'), h('span', { 'aria-hidden': 'true' }, '›'), h('span', { 'aria-current': 'page' }, f.nombre)),
    selectorCliente({ clientes: lista, actual: f.sub_id, etiqueta: 'Cambiar de subcuenta', insignia: x => chipEstado(x.estado, EST[x.estado].t), alElegir: x => ctx.navegar(`${ID}/${x.id}`) })));

  cont.append(h('section', { class: 'detalle-cab pila', style: { gap: 'var(--s-3)' }, 'aria-label': 'Cabecera de la subcuenta' },
    h('div', { class: 'fila', style: { gap: 'var(--s-4)', alignItems: 'center' } },
      logoCliente(f, 'logo-cli xl'),
      h('div', { style: { minWidth: 0, flex: '1 1 260px' } },
        h('h2', {}, f.nombre),
        h('div', { class: 'meta-linea', style: { marginTop: 'var(--s-1)' } },
          h('span', {}, icono('base'), `GHL: ${f.nombre_sub}`),
          f.especialista ? h('span', {}, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(f.especialista)), `CRM: ${f.especialista}`) : h('span', {}, icono('persona'), 'Sin especialista asignado'),
          f.account ? h('span', {}, icono('persona'), `Account: ${f.account}`) : null,
          h('span', {}, icono('cal'), `${f.calendarios ?? 0} calendario${f.calendarios === 1 ? '' : 's'}`)),
        h('div', { class: 'fila', style: { marginTop: 'var(--s-3)', gap: 'var(--s-2)' } }, chipEstado(f.estado, `CRM: ${EST[f.estado].t}`), f.gravedad_cliente ? chipEstado(f.gravedad_cliente === 'critico' ? 'rojo' : f.gravedad_cliente === 'atencion' ? 'ambar' : 'verde', `Cliente: ${f.gravedad_cliente === 'critico' ? 'crítico' : f.gravedad_cliente === 'atencion' ? 'atención' : 'bien'}`) : null, f.encendida ? chipEstado('azul', f.meta_activa ? 'Campaña de Meta activa' : 'Leads entrando') : chipEstado('gris', 'Sin campaña'), f.tipo === 'sin_cliente' ? chipEstado('gris', 'Sin cliente en la app') : null)),
      h('div', { class: 'fila' }, abrirGHL(f.enlaces.ghl, 'Abrir en GHL'), abrirGHL(f.enlaces.conversaciones, 'Conversaciones'), abrirGHL(f.enlaces.calendarios, 'Calendarios'), abrirGHL(f.enlaces.oportunidades, 'Oportunidades'), abrirGHL(f.enlaces.flujos, 'Flujos')))));

  const v = f.velocidad || {};
  const c14 = f.citas_14d || {}, c30 = f.citas_30d || {}, c90 = f.citas_90d || {};
  const asis = c30.asistencia_pct === null || c30.asistencia_pct === undefined ? null : c30.asistencia_pct;
  cont.append(rejillaTarjetas([
    tile({ icono: 'users', etiqueta: 'Asistencia · 30 días', valor: asis === null ? sinDato() : pc(asis), unidad: asis === null ? '' : `${c30.celebradas} de ${c30.celebradas + c30.no_presentadas}`, estado: asis === null ? 'gris' : semaforo(asis, { verde: 75, ambar: 60 }), contexto: asis === null ? (c30.agendadas ? 'Ninguna cita de los últimos 30 días tiene marcado si vino: márcalas en GoHighLevel y sale el porcentaje.' : 'Sin citas en 30 días.') : 'Bien desde el 75 % · a medias' }),
    tile({ icono: 'phone', etiqueta: 'Sin tocar > 24 h', valor: fmt.num(f.sin_tocar_24h ?? 0), unidad: `de ${fmt.num(f.leads_30d ?? 0)} leads`, estado: !f.leads_30d ? 'gris' : f.sin_tocar_24h ? 'rojo' : 'verde', contexto: `${f.leads_manuales_30d || 0} contactos creados a mano, aparte` }),
    tile({ icono: 'clock', etiqueta: '1.er intento < 1 h', valor: v.juzgables ? pc(v.pct_1h) : sinDato(), unidad: v.juzgables ? `${v.en_1h} de ${v.juzgables}` : '', estado: v.juzgables ? semaforo(v.pct_1h, { verde: 70, ambar: 40 }) : 'gris', contexto: `Mediana ${v.mediana_min !== null && v.mediana_min !== undefined ? horasTxt(Math.round(v.mediana_min / 60)) : '—'} · 4 intentos en 72 h: ${v.juzgables_72h ? `${v.cuatro_en_72h} de ${v.juzgables_72h}` : '—'}` }),
    tile({ icono: 'cal', etiqueta: 'Citas sin estado · 14 d', valor: fmt.num(c14.sin_estado ?? 0), unidad: c14.sin_estado ? `la más antigua, ${horasTxt(c14.sin_estado_max_h)}` : '', estado: !c14.agendadas ? 'gris' : c14.sin_estado > 5 || c14.sin_estado_max_h > 48 ? 'rojo' : c14.sin_estado ? 'ambar' : 'verde', contexto: `${c90.agendadas ?? 0} citas en 90 días · ${c30.futuras ?? 0} próximas` }),
    tile({ icono: 'hist', etiqueta: 'Paradas > 72 h', valor: f.embudo?.cohorte_30d ? fmt.num(f.embudo.estancados_72h) : sinDato('Sin oportunidades'), unidad: f.embudo?.cohorte_30d ? `de ${f.embudo.cohorte_30d} del mes` : '', estado: !f.embudo?.cohorte_30d ? 'gris' : (f.embudo.pct_estancado || 0) >= 50 ? 'ambar' : 'verde', contexto: 'Sin cambiar de etapa en 72 h' }),
    tile({ icono: 'wa', etiqueta: 'WhatsApp fallido', valor: f.whatsapp?.enviados ? `${f.whatsapp.fallidos}/${f.whatsapp.enviados}` : sinDato('Sin envíos'), estado: f.whatsapp?.enviados ? semaforo(f.whatsapp.pct_fallo, { verde: 2, ambar: 10, mejorSi: 'bajo' }) : 'gris', contexto: 'El número conectado no se mide por API' }),
    f.sin_uso ? tile({ icono: 'plug', etiqueta: 'Uso de GoHighLevel', valor: fmt.num(f.contactos_total), unidad: 'contactos en total', estado: 'gris', contexto: 'No usa la subcuenta: ¿CRM contratado?', href: f.enlaces.contactos, ir: 'Ver contactos' }) : null,
    !f.sin_uso && f.leads_meta_7d !== null && f.leads_meta_7d !== undefined ? tile({ icono: 'plug', etiqueta: 'Meta y GHL · 7 días', valor: fmt.num(f.leads_meta_7d), unidad: `en Meta · ${f.leads_ghl_7d ?? 0} en GHL`, estado: f.motivos.some(m => m.clave === 'integracion') ? 'rojo' : 'verde', contexto: 'Si a GHL no llega ninguno, el formulario está roto' }) : null,
  ].filter(Boolean)));

  const sidebar = h('div', { class: 'pila' });
  const emb = f.embudo?.funnel;
  if (emb) {
    const max = Math.max(1, ...ETAPAS.map(([k]) => emb[k] || 0));
    sidebar.append(panel({ titulo: 'Embudo · 90 días', icono: 'cap', sub: 'Oportunidades por etapa (captación)' },
      h('div', { class: 'cuerpo' }, embudoBarras(ETAPAS.map(([k, t]) => ({ etiqueta: t, valor: emb[k] || 0, estado: k === 'descartado' ? 'rojo' : k === 'cerrado' ? 'verde' : null })), { max }))));
  } else sidebar.append(panel({ titulo: 'Embudo · 90 días', icono: 'cap' }, h('div', { class: 'cuerpo' }, vacioLinea('Sin oportunidades en 90 días: esta subcuenta no tiene embudo con movimiento.', { icono: 'cap' }))));
  sidebar.append(panel({ titulo: 'Flujos y WhatsApp', icono: 'zap' }, h('div', { class: 'cuerpo pila' },
    h('p', { class: 'sub', style: { margin: 0 } }, 'Los errores de flujo no salen por la API (falta un permiso de GoHighLevel). El número de WhatsApp conectado: no medible.'),
    h('div', { class: 'fila' }, abrirGHL(f.enlaces.flujos, 'Abrir flujos en GHL'), abrirGHL(f.enlaces.whatsapp, 'WhatsApp de la subcuenta')))));

  const principal = h('div', { class: 'pila' });
  principal.append(panel({ titulo: 'Qué falla y quién lo arregla', icono: 'alert', sub: 'Motivos con el umbral firmado' },
    f.motivos.length ? listaLoPrimero(f.motivos.map(m => ({ estado: m.nivel === 'rojo' ? 'rojo' : 'ambar', icono: ICO_MOT[m.clave] || 'alert', motivo: m.texto, detalle: `Lo arregla: ${QUIEN_MOT[m.clave] || 'especialista'}` })))
      : h('div', { class: 'cuerpo' }, vacioLinea(f.estado === 'gris' ? 'Sin actividad: nada que vigilar.' : 'Esta subcuenta está en verde.', { icono: 'ok' }))));

  if (!vis.resumen) {
    const leads = (d.leads_sin_tocar || []).filter(x => x.sub_id === f.sub_id);
    const citas = (d.citas_sin_estado || []).filter(x => x.sub_id === f.sub_id);
    const gotaL = cuentagotas(leads, x => (x.horas > 72 ? 'rojo' : 'ambar'), x => x.horas || 0);
    const gotaC = cuentagotas(citas, x => (x.horas > 48 ? 'rojo' : 'ambar'), x => x.horas || 0);
    if (leads.length) principal.append(panel({ titulo: `Leads sin tocar (${leads.length})`, icono: 'phone' }, tablaApilable({
      filas: leads.slice(0, 25), porPagina: MOVIL() ? 8 : 15, columnas: [
        { clave: 'creado', titulo: 'Entró', principal: true, celda: x => `${fDiaRO(x.creado)} · ${x.creado?.slice(11) || ''}` },
        { clave: 'horas', titulo: 'Esperando', num: true, celda: x => puntoEstado(gotaL(x), horasTxt(x.horas)) },
        { clave: 'medio', titulo: 'Origen', celda: x => h('span', { style: { display: 'inline-block', minWidth: '140px' } }, x.medio || '—') },
        { clave: 'automatico', titulo: 'Automático', celda: x => x.automatico ? 'Sí' : puntoEstado('ambar', 'No') },
        { clave: 'acc', titulo: 'Abrir', ordenable: false, celda: x => h('span', { class: 'fila', style: { gap: 'var(--s-2)' } }, botonVerDatos(ctx, x, vis), abrirGHL(x.enlace, 'Abrir contacto en GHL')) },
      ] })));
    if (citas.length) principal.append(panel({ titulo: `Citas sin estado (${citas.length})`, icono: 'cal' }, tablaApilable({
      filas: citas, porPagina: MOVIL() ? 8 : 15, columnas: [
        { clave: 'inicio', titulo: 'Cita', principal: true, celda: x => `${fDiaRO(x.inicio)} · ${x.inicio?.slice(11) || ''}` },
        { clave: 'calendario', titulo: 'Calendario', celda: x => h('span', { style: { display: 'inline-block', minWidth: '160px' } }, x.calendario || '—') },
        { clave: 'horas', titulo: 'Sin marcar', num: true, celda: x => puntoEstado(gotaC(x), horasTxt(x.horas)) },
        { clave: 'acc', titulo: 'Abrir', ordenable: false, celda: x => abrirGHL(x.enlace_contacto || x.enlace, x.enlace_contacto ? 'Abrir contacto en GHL' : 'Abrir calendario en GHL') },
      ] })));
    principal.append(panel({ titulo: 'Actuar', icono: 'zap', sub: 'En el prototipo todo va a la cola con su vista previa. Mover, anotar y citas esperan un permiso de GoHighLevel.' }, acciones(ctx, f, citas, (d.oportunidades_paradas || []).filter(x => x.sub_id === f.sub_id))));
  }
  cont.append(h('div', { class: 'dos' }, principal, sidebar));
  const desc = Object.entries(f.descartados_30d || {});
  const DESC = { prueba: 'de prueba o demostración', otro_negocio: 'de otro negocio', manual: 'creados a mano', importado: 'importados', no_lead: 'que no son leads (candidaturas, cursos, clientes)', sin_origen: 'sin origen de formulario ni anuncio' };
  if (desc.length) cont.append(avisoParcial(`En 30 días no cuentan como leads: ${desc.map(([k, n]) => `${n} ${DESC[k] || k}`).join(', ')}.`, { tipo: 'info', titulo: 'Contactos que no se cuentan.' }));
  if (f.calendarios_ajenos?.length) cont.append(avisoParcial(`Esta subcuenta tiene calendarios de otro negocio, que no se cuentan: ${f.calendarios_ajenos.join(', ')}. Conviene sacarlos de aquí.`, { titulo: 'Calendario ajeno.' }));
  if (f.errores_lectura?.length) cont.append(avisoParcial(`Al leer esta subcuenta, GoHighLevel respondió: ${f.errores_lectura.join(' · ')}.`, { titulo: 'Lectura incompleta.' }));
}

function acciones(ctx, f, citas, paradas = []) {
  // Campos comunes (N6): chips para la etapa y campoTexto para la nota y la fecha; la lógica de cada botón no cambia.
  const etapa = chipsFiltro({ etiqueta: 'Etapa de destino', opciones: ETAPAS.map(([k, t]) => ({ valor: k, texto: t })), valor: ETAPAS[0][0] });
  const textoEtapa = () => (ETAPAS.find(([k]) => k === etapa.valor()) || ETAPAS[0])[1];
  const opps = paradas.slice().sort((a, b) => (b.horas || 0) - (a.horas || 0)).slice(0, 6);
  const cualOpp = opps.length ? chipsFiltro({ etiqueta: 'Oportunidad parada', valor: opps[0].ref,
    opciones: opps.map(o => ({ valor: o.ref, texto: `${fDiaRO(o.creada)} · ${(o.etapa || 'sin etapa').slice(0, 28)}` })) }) : null;
  const oppElegida = () => opps.find(o => o.ref === cualOpp?.valor()) || opps[0];
  const notaCampo = campoTexto({ etiqueta: 'Texto de la nota', nombre: 'nota', filas: 2, placeholder: 'P. ej. «Llamado sin respuesta, reintentar mañana»' });
  const nota = notaCampo.querySelector('textarea');
  const cita = citas[0];
  const cuandoCampo = cita ? campoTexto({ etiqueta: 'Nueva fecha y hora', nombre: 'cuando', tipo: 'datetime-local' }) : null;
  const cuando = cuandoCampo?.querySelector('input');
  const grupo = (titulo, ...hijos) => h('div', { class: 'pila', style: { gap: 'var(--s-2)', paddingTop: 'var(--s-3)', borderTop: 'var(--borde-suave)' } },
    h('span', { style: { font: 'var(--t-eyebrow)', letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--dim)' } }, titulo), ...hijos);
  const botones = (...b) => h('div', { class: 'fila' }, ...b);
  return h('div', { class: 'cuerpo pila', style: { gap: 'var(--s-3)' } },
    // R16/V2: la acción lleva la referencia de la oportunidad («… · oportunidad <ref>») para que el servidor saque el cliente de ella.
    grupo('Oportunidad', ...(cualOpp ? [cualOpp, etapa, botones(
      accionSim(ctx, { texto: 'Mover oportunidad', pregunta: '¿Mover a esa etapa?', tipo: 'mover_oportunidad', objeto: () => `${f.nombre} · oportunidad ${oppElegida().ref}`, cliente_id: f.cliente_id,
        vista_previa: () => `Movería la oportunidad de ${f.nombre} (${oppElegida().etapa || 'sin etapa'}, creada el ${fDiaRO(oppElegida().creada)}) a «${textoEtapa()}». Nunca con el upsert, que machaca etiquetas. Espera un permiso de GoHighLevel.` }))]
      : [vacioLinea('Ninguna oportunidad parada que mover en esta subcuenta. Las demás se mueven en GoHighLevel.', { icono: 'cap' })])),
    grupo('Nota', h('div', { style: { maxWidth: '480px' } }, notaCampo), botones(
      accionSim(ctx, { texto: 'Poner nota', pregunta: '¿Poner la nota en GHL?', tipo: 'nota', objeto: `${f.nombre} · nota`, cliente_id: f.cliente_id,
        vista_previa: () => (nota.value.trim() ? `Pondría en GHL (${f.nombre}) la nota: «${nota.value.trim().slice(0, 300)}». Espera un permiso de GoHighLevel.` : null) }))),
    grupo('Reprogramar cita', cita ? h('span', { class: 'sub' }, `Cita del ${fDiaRO(cita.inicio)} ${cita.inicio?.slice(11)}`) : vacioLinea('Sin citas sin estado en esta subcuenta.', { icono: 'cal' }),
      cita ? h('div', { style: { maxWidth: '280px' } }, cuandoCampo) : null,
      cita ? botones(accionSim(ctx, { texto: 'Reprogramar', pregunta: '¿Mover la cita? Avisa al lead', tipo: 'reprogramar_cita', objeto: `${f.nombre} · cita ${cita.ref}`, cliente_id: f.cliente_id,
        vista_previa: () => (cuando.value ? `Movería la cita del ${fDiaRO(cita.inicio)} a ${cuando.value.replace('T', ' ')} y GHL avisaría al lead. Espera un permiso de GoHighLevel.` : null) })) : null),
    grupo('Equipo', botones(
      tareaAccount(ctx, f, f.mot1 ? f.mot1.texto : 'Revisar el CRM del despacho') || h('span', { class: 'sub' }, 'Sin account asignado'),
      accionSim(ctx, { texto: `Escalar a ${JEFA}`, pregunta: `¿Escalar a ${JEFA}?`, tipo: 'escalar', herramienta: 'app', objeto: f.nombre, cliente_id: f.cliente_id,
        vista_previa: `Escalaría ${f.nombre} a ${JEFA} (jefa de CRM) con: ${f.motivos.map(m => m.texto).join(' · ') || 'sin motivos'}.` }),
      f.motivos.some(m => m.clave === 'integracion') ? accionSim(ctx, { texto: 'Aviso a Agus', pregunta: '¿Avisar a Agus de la integración rota?', tipo: 'aviso_integracion', herramienta: 'app', objeto: f.nombre, cliente_id: f.cliente_id,
        vista_previa: `Pondría en la cola de Agus: «${f.nombre}: ${f.motivos.find(m => m.clave === 'integracion').texto}».` }) : null)),
    ctx.soloLectura ? h('p', { class: 'sub', style: { margin: 0 } }, 'Estás en «ver como»: los botones no hacen nada.') : null);
}

// ------------------------------------------------------------------ módulo
export default {
  id: ID,
  titulo: 'Salud del CRM',
  grupo: 'Captación y CRM',
  puestos_que_lo_ven: { direccion: 'todo', finanzas_direccion: 'todo', operaciones: 'todo', proyectos: 'todo', tecnico_altas: 'todo', jefa_crm: 'todo', jefa_publicidad: 'resumen', account: 'suyo', trafficker: 'resumen', especialista_ghl: 'suyo' },
  async render(contenedor, ctx) {
    vigilarCortes(contenedor);
    JEFA = ctx.nombre('yessica');
    const raiz = h('div', { class: 'pila', style: { gap: 'var(--s-6)' } });
    contenedor.append(raiz);
    contenedor = raiz;
    const espera = esqueleto({ tarjetas: 4, lineas: 4 });
    contenedor.append(espera);
    const d = await cargar(ctx);
    espera.remove();
    if (d.error) {
      contenedor.append(vacio({ icono: 'alert', titulo: 'No se pudieron cargar los datos del CRM', texto: d.error, quien: 'quien mantiene la app (fuentes_crm/generar_crm.py)', borde: true, tono: 'aviso' }));
      return;
    }
    const [sub] = ctx.params;
    if (sub) pintarDetalle(contenedor, ctx, d, sub);
    else pintarInicio(contenedor, ctx, d);
  },
};
