// modulos/nuevos.js · M12 «Clientes nuevos», de la firma al día 90 (E4 del plan v2 · punto 6 de Mili · ficha de Agus, G2 §6).
//
// Qué enseña (arriba lo de cada día, abajo lo de cada semana):
//   1. Cifras: altas encendidas en plazo (el número de Agus, D-28: día 10, límite 12), fuera de plazo, sin tareas a las 48 h,
//      tareas vencidas, bloqueos, carga de la semana (tope 5) y conexiones caídas de las 66 subcuentas.
//   2. Lo primero hoy: las alertas del punto 6 de Mili (vencida · no avanza en su semana · alta sin tareas a las 48 h ·
//      bloqueo de más de 5 días sin escalar), las de plazo y los bloqueos de Meta. Máximo 7.
//   3. Altas en curso: una fila por alta con día X de 90, marcas del día 10 y 12, barra de avance (% de tareas hechas de
//      su lista de onboarding de ClickUp), hito siguiente, dueño, vencidas y bloqueadas. Al abrirla, la línea de tiempo.
//   4. Pestañas: accesos pendientes · casillas técnicas · conexiones caídas · bloqueos de Meta · garantía · talleres ·
//      contratos que vienen · fechas automáticas de la plantilla (D+N, «se aplicará cuando haya escritura»).
// Datos: data/nuevos/nuevos.json (fuentes_nuevos/generar_nuevos.py, solo lectura), RECORTADO por servir.py: cada fila con
// cliente_id llega solo si la persona ve ese cliente y sin las claves de dinero que no le tocan (gasto_*).
// Botones: ctx.accion() → cola local «simulada» con vista previa. Nunca escribe en ClickUp, Sign, Meta, GHL ni Desk.

// Diseño (N6, auditoría 30): sin hoja propia. Clases comunes de estilos.css y, donde no llegan, style inline solo con tokens.
import {
  h, fmt, tile, tiles, listaLoPrimero, chipEstado, chipsFiltro, selectorCliente, vacio, vacioLinea, botonConfirmar, avisoParcial,
  logoCliente, panel, frescura, icono, iniciales, pestanas, tablaApilable, listaConIcono, grafico, campoTexto, menuMas,
  fechas, sumarDias,
} from '../componentes.js';
import { botonDeshacer } from './_deshacer.js';
import { plegarConsejo } from './_plegar_consejo.js';
import { cargarObjetivos, puedeEditar, veObjetivos } from './objetivos_comun.js';

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

const ID = 'clientes-nuevos';
const ESTADOS_HITO = {
  hecho: ['verde', 'Hecho'], hecho_tarde: ['ambar', 'Hecho tarde'], agendado: ['azul', 'Agendado'], pendiente: ['gris', 'Pendiente'],
  tarde: ['rojo', 'Tarde'], no_aplica: ['gris', 'No aplica'],
};
const ICONO_HITO = { firma: 'flag', accesos: 'key', arranque: 'video', config: 'aj', encendido: 'rocket', primer_lead: 'target', reunion_resultados: 'users', garantia: 'escudo', dia90: 'heart' };
const ICONO_ALERTA = { urgente: 'fire', config_sin_agendar: 'cal', diferencia: 'compartir', fuera_plazo: 'rocket', riesgo_plazo: 'clock', sin_tareas: 'capas', vencida: 'cal', no_avanza: 'clock', bloqueo_5d: 'candado', bloqueo_meta: 'megafono', gasta_sin_casilla: 'check' };
const TEXTO_ALERTA = { urgente: 'Prioritaria (equipo de arranque)', config_sin_agendar: 'Configuración sin agendar', diferencia: 'El equipo y la app no coinciden', fuera_plazo: 'Fuera de plazo', riesgo_plazo: 'En riesgo de plazo', sin_tareas: 'Sin tareas', vencida: 'Tarea vencida', no_avanza: 'No avanza en su semana', bloqueo_5d: 'Bloqueo de más de 5 días', bloqueo_meta: 'Bloqueo de Meta', gasta_sin_casilla: 'Gasta sin la casilla' };
const ORDEN_ALERTA = ['urgente', 'config_sin_agendar', 'fuera_plazo', 'sin_tareas', 'bloqueo_meta', 'bloqueo_5d', 'vencida', 'riesgo_plazo', 'no_avanza', 'gasta_sin_casilla', 'diferencia'];
const rangoAlerta = a => (a.estado === 'rojo' ? 0 : a.estado === 'ambar' ? 10 : 20) + Math.max(0, ORDEN_ALERTA.indexOf(a.tipo));

// ------------------------------------------------------------------ utilidades
// V2-E: «hoy» y «esta semana» con la vara común (calendario de Madrid; ?hoy= en local), nunca UTC ni la zona del Mac.
const hoyISO = () => fechas.hoy();
const masDias = (iso, n) => sumarDias(String(iso).slice(0, 10), n);
/** «2026-10-02 22:14» (UTC, local.db) → «2026-10-03 00:14» en hora de Madrid (antes: zona del Mac). */
const utcAMadrid = t => { if (!t) return ''; const iso = String(t).replace(' ', 'T') + (/[Zz]|[+-]\d\d:?\d\d$/.test(String(t)) ? '' : 'Z'); return fechas.dia(iso) ? `${fechas.dia(iso)} ${fechas.hora(iso)}` : ''; };
// El productor usa hora local de Europe/Madrid sin offset; ISO con zona también se admite.
// Fechas inexistentes o ambiguas (cambio de hora), futuras y lecturas fallidas no son recientes.
function instanteFuente488(hora) {
  if (typeof hora !== 'string') return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,3}))?)?(Z|[+-]\d{2}:?\d{2})?$/.exec(hora);
  if (!m) return null;
  const [y, mo, d, hh, mm, ss] = m.slice(1, 7).map(x => Number(x || 0));
  if (y < 1900 || mo < 1 || mo > 12 || d < 1 || hh > 23 || mm > 59 || ss > 59) return null;
  const base = Date.UTC(y, mo - 1, d, hh, mm, ss, Number((m[7] || '').padEnd(3, '0')));
  const dt = new Date(base);
  if (dt.getUTCFullYear() !== y || dt.getUTCMonth() !== mo - 1 || dt.getUTCDate() !== d) return null;
  if (m[8]) {
    if (m[8] === 'Z') return base;
    const z = /^([+-])(\d{2}):?(\d{2})$/.exec(m[8]);
    const zh = Number(z[2]), zm = Number(z[3]);
    if (zh > 14 || zm > 59 || (zh === 14 && zm !== 0)) return null;
    return base - (z[1] === '+' ? 1 : -1) * (zh * 60 + zm) * 60000;
  }
  const formato = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Madrid', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' });
  const candidatos = [1, 2].map(offset => base - offset * 36e5).filter(t => {
    const partes = Object.fromEntries(formato.formatToParts(new Date(t)).map(p => [p.type, p.value]));
    return Number(partes.year) === y && Number(partes.month) === mo && Number(partes.day) === d && Number(partes.hour) === hh && Number(partes.minute) === mm && Number(partes.second) === ss;
  });
  return candidatos.length === 1 ? candidatos[0] : null;
}
const edadH = (hora, ahora = Date.now()) => {
  const t = instanteFuente488(hora);
  return t !== null && Number.isFinite(ahora) && t <= ahora ? (ahora - t) / 36e5 : null;
};
const fres = (f, nombre, ahora = Date.now()) => {
  const edad = edadH(f?.hora, ahora);
  return { fuente: nombre || f?.fuente || 'Fuente', edad_h: edad,
    estado: f?.estado === 'bien' && edad !== null ? (edad > 30 ? 'viejo' : 'ok') : 'sin datos',
    lectura: instanteFuente488(f?.hora) !== null ? f.hora : null };
};
const _M3N = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const _DSN = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'];
const fechaLarga = iso => { if (!iso) return '—'; const d = new Date(iso.slice(0, 10) + 'T12:00:00'); return `${d.getDate()}-${_M3N[d.getMonth()]}`; };   // §2.3: «18-sep»
const nombrePersona = p => p?.nombre || null;
const verLeads = n => `${fmt.num(n)} lead${n === 1 ? '' : 's'}`;

async function cargar(ctx) {
  try { return await ctx.datosModulo('nuevos/nuevos'); }
  catch (e) { return { _error: e.message || String(e) }; }
}
/** Encima del estado del equipo que trae el servidor, lo último guardado desde el formulario (cola simulada): se ve al instante. */
function aplicarEstadosGuardados(d, acciones, ctx) {
  const ult = new Map();
  for (const x of [...acciones].reverse()) if (x.tipo === 'estado_alta' && x.cliente_id) ult.set(x.cliente_id, x);
  for (const a of d.altas || []) {
    const x = ult.get(a.cliente_id);
    if (!x) continue;
    const local = utcAMadrid(x.creada);
    if (local && d.generado && local <= d.generado) continue;   // ya está en los datos (el generador lo recogió de local.db)
    let v = {}; try { v = JSON.parse(x.vista_previa || '{}'); } catch { v = {}; }
    a.equipo = { ...(a.equipo || {}), ...v, actualizado: utcAMadrid(x.creada), autor: ctx.nombre ? ctx.nombre(x.quien) : x.quien, origen: 'formulario de la app (simulación)' };
    a.urgente = !!a.equipo.urgente;
  }
}
const TXT_T = { hecho: 'hecho', agendado: 'agendado', segunda_sesion: '2.ª sesión', sin_agendar: 'sin agendar', pendiente: 'sin agendar' };
const TXT_C = { hecho: 'hecha', agendada: 'agendada', sin_agendar: 'sin agendar', pendiente: 'sin agendar' };
const fechaHora = f => !f ? '' : f.length > 10 ? `${fechaLarga(f)} ${f.slice(11, 16)}` : fechaLarga(f);
const ghlUrl = loc => loc ? `https://app.gohighlevel.com/v2/location/${encodeURIComponent(loc)}/dashboard` : null;
const ENC_A_ESTADO = { en_plazo: 'verde', en_limite: 'ambar', tarde: 'rojo', sin_encender_fuera_de_plazo: 'rojo', pendiente_en_plazo: 'gris' };
// V2 (B-M5): el siguiente paso dicho como verbo («Siguiente paso: encender la campaña»), nunca «Siguiente: Encendido»,
// que se lee como si ya estuviera encendida.
const PASO_HITO = { firma: 'firmar el acuerdo', accesos: 'conseguir los accesos', arranque: 'hacer el taller de oferta', config: 'agendar la configuración básica',
  encendido: 'encender la campaña', primer_lead: 'conseguir el primer lead', reunion_resultados: 'hacer la primera reunión de resultados', garantia: 'revisar la garantía del día 30', dia90: 'cerrar el día 90' };
const pasoDe = sig => (sig ? `Siguiente paso: ${PASO_HITO[sig.id] || sig.nombre.toLowerCase()}` : 'Todos los hitos hechos');
/** V2 (B-B4): «28925 FBC EUROCONSULTING» → «FBC Euroconsulting» (sin número interno ni todo en mayúsculas). */
const nombreSubcuenta = t => String(t || '').replace(/^\d{3,}\s+/, '').replace(/[A-ZÁÉÍÓÚÑ]{4,}/g, w => w.charAt(0) + w.slice(1).toLowerCase());
const ENC_A_TEXTO = { en_plazo: 'encendida en plazo', en_limite: 'encendida el día 11-12', tarde: 'encendida tarde', sin_encender_fuera_de_plazo: 'fuera de plazo: pasado el día 12 sin encender', pendiente_en_plazo: 'en plazo, todavía sin encender' };
/** Una sola verdad por cliente: account, «sin account» y plazo de encendido salen de ctx.verdad (igual que En rojo). */
function aplicarVerdad(d, ctx) {
  if (typeof ctx.verdad !== 'function') return;
  for (const a of d.altas || []) {
    const v = ctx.verdad(a.cliente_id);
    if (!v) continue;
    if ('account' in v) {
      a.account = v.account ? { id: v.account, nombre: ctx.nombre ? ctx.nombre(v.account) : v.account } : null;
      a.sin_account = v.account ? null : (typeof v.sin_account === 'string' ? v.sin_account.replace(/\s*\([A-Z]\d+\)/g, '') : 'sin account');
    }
    const e = v.encendido;
    if (e && ENC_A_ESTADO[e.estado]) {
      a.plazo = { ...a.plazo, estado: ENC_A_ESTADO[e.estado], texto: ENC_A_TEXTO[e.estado], dia_encendido: a.plazo.dia_encendido ?? e.dia };   // el día sale de Meta (este módulo es la fuente de la verdad)
      // R12 (C-02): el estado de la CAMPAÑA sale de la verdad única; «activa» de Meta es la cuenta publicitaria
      const dia = a.plazo.dia_encendido;
      a.campana = { encendida: dia !== null && dia !== undefined, texto: dia !== null && dia !== undefined ? `campaña encendida el día ${dia}` : 'campaña sin encender' };
    }
  }
  for (const k of ['trafficker', 'crm']) for (const a of d.altas || []) if (a[k]?.id && ctx.nombre) a[k].nombre = ctx.nombre(a[k].id);
}
const PUEDEN_EDITAR = ['direccion', 'operaciones', 'proyectos', 'tecnico_altas', 'jefa_publicidad'];

async function accionesPrevias(ctx) {
  try { return (await ctx.api(`acciones?modulo=${ID}`))?.acciones || []; } catch { return []; }
}

/** Botón de acción simulada (R9): vista previa, cola local, nunca API externa. */
function botonAccion(ctx, { texto, icono: ico, pregunta, confirmar, accion, mini = true, peligro }) {
  // Ronda U (#4): lo interno (herramienta «app»: escalar, casillas…) va al primer clic con «Deshacer» 8 s; el «¿Seguro?»
  // queda para lo que sale fuera (Desk, ClickUp).
  if (accion?.herramienta === 'app' && !peligro) {
    return botonDeshacer({ texto, icono: ico, mini, hecho: texto === 'Escalar' ? 'Escalado' : 'Hecho', soloLectura: ctx.soloLectura,
      alHacer: async () => { const r = await ctx.accion(accion); return r?.local ? 'Apuntado en local (sin servidor)' : `En la cola (n.º ${r?.id ?? '—'}) · queda en el rastro`; } });
  }
  return botonConfirmar({
    texto, pregunta, confirmar: confirmar || 'Sí', mini, peligro, soloLectura: ctx.soloLectura,
    alConfirmar: async () => {
      const r = await ctx.accion(accion);
      return r?.local ? 'Apuntado en local (sin servidor) · simulado' : `En la cola como «simulada» (n.º ${r?.id ?? '—'}) · se hará de verdad cuando la app pueda escribir`;
    },
  });
}

// ================================================================== piezas de pintura (sin hoja propia: clases comunes + tokens)
// Ronda N6 (auditoría 30): nada de <style>. Lo que no tiene clase común va en style inline y SOLO con tokens de estilos.css.
const S = {
  meta: { font: 'var(--t-meta)', color: 'var(--dim)' },
  metaMid: { font: 'var(--t-meta)', color: 'var(--mid)' },
  h3: { font: 'var(--t-h3)', color: 'var(--ink)' },
  corte: { minWidth: '0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  pila: g => ({ display: 'grid', gap: g || 'var(--s-3)', minWidth: '0' }),
  rejilla: (min, g) => ({ display: 'grid', gridTemplateColumns: `repeat(auto-fit, minmax(min(100%, ${min}px), 1fr))`, gap: g || 'var(--s-3)' }),
  lectura: { font: 'var(--t-cuerpo)', color: 'var(--mid)', maxWidth: '72ch', margin: '0' },
};
const COLOR_ESTADO = { verde: 'var(--good)', ambar: 'var(--warn)', rojo: 'var(--bad)', gris: 'var(--off)', azul: 'var(--accent)' };

/** Chip que no rompe su caja: se corta con «…» y lleva el texto entero en la burbuja. */
function chipCorto(estado, texto) {
  const c = chipEstado(estado, texto);
  Object.assign(c.style, { maxWidth: '100%', overflow: 'hidden', textOverflow: 'ellipsis', justifySelf: 'start' });
  c.title = texto;
  return c;
}
/** Fecha propuesta (D+N): chip azul con borde discontinuo. */
const chipPropuesta = (texto, titulo) => h('span', { class: 'chip azul sin-punto', title: titulo || null, style: { border: '1px dashed var(--accent-2)' } }, texto);
/** Botón pequeño con alto de clic de 32 px (guía 3.11). */
const btMini = (attrs, ...hijos) => h('a', { class: 'bt mini', ...attrs, style: { minHeight: 'var(--s-8)', ...(attrs.style || {}) } }, ...hijos);
/** Enlace al alta dentro de una tabla: 13/600 en tinta y 32 px de alto (no un enlace azul de 20 px). */
const enlaceAlta = a => h('a', { href: `#/${ID}/${a.cliente_id}`, style: { ...S.h3, display: 'inline-flex', alignItems: 'center', minHeight: 'var(--s-8)', textDecoration: 'none', maxWidth: '100%' } },
  h('span', { style: S.corte }, a.nombre));
/** Explicación plegada al pie (guía 3.6: «las explicaciones, plegadas al final»). */
function nota(titulo, texto, { icono: ico = 'info' } = {}) {
  return h('details', { style: { borderTop: 'var(--borde-suave)', paddingTop: 'var(--s-2)' } },
    h('summary', { style: { ...S.metaMid, fontWeight: 600, cursor: 'pointer', minHeight: 'var(--s-8)', display: 'flex', alignItems: 'center', gap: 'var(--s-2)', width: 'max-content', maxWidth: '100%' } },
      icono(ico, { clase: 's' }), titulo),
    h('div', { style: { ...S.pila('var(--s-2)'), paddingTop: 'var(--s-1)' } }, [].concat(texto).filter(Boolean).map(t => typeof t === 'string' ? h('p', { style: S.lectura }, t) : t)));
}
/** Lista recortada: enseña n y un botón «Ver todas (N)» que despliega el resto (páginas cortas en el móvil). */
function recortado(lista, n, pintar, { nombre = 'todas', menos = 'Ver menos' } = {}) {
  const caja = h('div', { style: S.pila() });
  let todo = false;
  const dibujar = () => {
    const vis = todo || lista.length <= n ? lista : lista.slice(0, n);
    caja.replaceChildren(...[].concat(pintar(vis)).filter(Boolean),
      ...(lista.length > n ? [h('div', { class: 'fila' }, h('button', { type: 'button', class: 'bt', 'aria-expanded': String(todo), on: { click: () => { todo = !todo; dibujar(); } } },
        icono(todo ? 'up' : 'chev', { clase: 's' }), todo ? menos : `Ver ${nombre} (${fmt.num(lista.length)})`))] : []));
  };
  dibujar();
  return caja;
}
/** «Abrir en…»: el menuMas() común (ronda 10) con los enlaces a herramientas de fuera (ClickUp, GHL, Meta), en otra pestaña. */
function menuAbrir(etiqueta, items) {
  return menuMas({ texto: 'Abrir en…', etiqueta,
    items: items.map(it => ({ texto: it.texto, icono: it.icono || 'ext', alPulsar: () => window.open(it.href, '_blank', 'noopener') })) });
}
/** Leyenda de una línea (12 px) con muestras de color. */
const muestra = (color, forma = 'barra') => h('i', { 'aria-hidden': 'true', style: forma === 'linea'
  ? { display: 'inline-block', width: '2px', height: 'var(--s-3)', background: color, borderRadius: 'var(--r-full)' }
  : { display: 'inline-block', width: 'var(--s-3)', height: 'var(--s-2)', background: color, borderRadius: 'var(--r-full)' } });
const leyenda = items => h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-1) var(--s-4)', ...S.meta } },
  items.map(([m, t]) => h('span', { style: { display: 'inline-flex', alignItems: 'center', gap: 'var(--s-2)' } }, m, t)));

// ================================================================== cabecera común
/** Recencia de las cinco lecturas; no acredita cobertura de los datos. */
function avisoDatos(d) {
  const f = d.fuentes || {};
  const lista = [fres(f.sign, 'Zoho Sign'), fres(f.clickup, 'ClickUp'), fres(f.meta, 'Meta'), fres(f.ghl, 'GHL'), fres(f.dns, 'DNS')];
  const malas = lista.filter(x => x.estado !== 'ok').length;
  return h('details', { style: { minWidth: '0' } },
    h('summary', { style: { display: 'inline-flex', alignItems: 'center', gap: 'var(--s-2)', minHeight: 'var(--s-8)', cursor: 'pointer', listStyle: 'none' } },
      h('span', { title: 'Lecturas dentro de 30 h; no acredita cobertura', 'aria-label': malas ? `${malas} fuentes con lectura antigua, no válida o no disponible; no acredita cobertura` : '5 fuentes con lecturas dentro de 30 h; no acredita cobertura' }, chipEstado(malas ? 'ambar' : 'verde', malas ? `${malas} fuente${malas === 1 ? '' : 's'} por revisar` : 'Fuentes recientes')),
      h('span', { style: S.meta }, 'Ver de dónde salen')),
    h('div', { class: 'fila', style: { paddingTop: 'var(--s-2)' } }, lista.map(x => h('span', { title: x.lectura ? `Lectura original: ${x.lectura}${/[Z]|[+-]\d\d:?\d\d$/.test(x.lectura) ? '' : ' · Europe/Madrid'}` : 'Lectura no válida o no disponible' }, frescura(x), x.lectura ? h('span', { style: S.meta }, ` · ${x.lectura}${/[Z]|[+-]\d\d:?\d\d$/.test(x.lectura) ? '' : ' Madrid'}`) : null))));
}

// ================================================================== fila de un alta
function pista(a, reglas) {
  const max = 30;                                        // la pista enseña el primer mes: lo que decide el plazo
  const dia = Math.min(a.dia, max);
  const pos = n => `${Math.min(100, (n / max) * 100)}%`;
  const enc = a.plazo.dia_encendido;
  const tarde = enc !== null && enc !== undefined && enc > reglas.encendido_limite;
  const marca = (n, color, titulo) => h('span', { title: titulo, style: { position: 'absolute', top: '-4px', bottom: '-4px', left: pos(n), width: '2px', background: color, borderRadius: 'var(--r-full)' } });
  return h('div', { style: { padding: 'var(--s-1) 0' } },
    h('div', { role: 'img', 'aria-label': `Día ${a.dia} de 90. Encendido objetivo el día ${reglas.encendido_objetivo}, límite el ${reglas.encendido_limite}.${enc !== null && enc !== undefined ? ` Encendida el día ${enc}.` : ' Sin encender.'}`,
      style: { position: 'relative', height: 'var(--s-2)', borderRadius: 'var(--r-full)', background: 'var(--off-soft)' } },
      h('span', { style: { position: 'absolute', left: '0', top: '0', bottom: '0', width: pos(dia), borderRadius: 'var(--r-full)', background: COLOR_ESTADO[a.plazo.estado] || 'var(--accent)' } }),
      marca(reglas.encendido_objetivo, 'var(--ink)', `Día ${reglas.encendido_objetivo}: objetivo de encendido`),
      marca(reglas.encendido_limite, 'var(--bad)', `Día ${reglas.encendido_limite}: límite`),
      enc !== null && enc !== undefined ? h('span', { title: `Encendida el día ${enc}`, style: { position: 'absolute', top: '50%', left: pos(enc), transform: 'translate(-50%, -50%)', width: 'var(--s-5)', height: 'var(--s-5)',
        borderRadius: 'var(--r-full)', background: 'var(--card)', border: `2px solid ${tarde ? 'var(--bad)' : 'var(--good)'}`, color: tarde ? 'var(--bad-ink)' : 'var(--good-ink)', display: 'grid', placeItems: 'center' } }, icono('rocket', { clase: 's' })) : null));
}

function barraAvance(o) {
  const barra = (...trozos) => h('div', { style: { height: 'var(--s-2)', borderRadius: 'var(--r-full)', background: 'var(--off-soft)', overflow: 'hidden', display: 'flex' } }, ...trozos);
  const cab = (izq, der, color) => h('div', { style: { display: 'flex', justifyContent: 'space-between', gap: 'var(--s-2)', ...S.metaMid } }, h('span', { style: S.corte }, izq), h('b', { style: { color: color || 'var(--ink)', fontWeight: 700 } }, der));
  if (!o) return h('div', { style: S.pila('var(--s-2)') }, cab('Tareas de arranque', 'sin lista', 'var(--bad-ink)'), barra());
  const n = o.n || 1;
  const venc = o.vencidas || 0, bloq = o.bloqueadas || 0;
  const trozo = (x, color) => h('i', { style: { display: 'block', height: '100%', width: `${(x / n) * 100}%`, background: color } });
  return h('div', { style: S.pila('var(--s-2)') },
    cab(`${o.hechas} de ${o.n} tareas`, fmt.pct(o.pct)),
    h('div', { role: 'img', 'aria-label': `${o.pct} % de tareas hechas; ${venc} vencidas; ${bloq} bloqueadas` },
      barra(trozo(o.hechas, 'var(--good)'), trozo(venc, 'var(--bad)'), trozo(bloq, 'var(--warn)'))));
}

function lineaEquipo(eq) {
  if (!eq) return null;
  const t = eq.taller || {}, c = eq.config_basicas || {};
  const linea = (ico, txt) => h('span', { style: { display: 'flex', gap: 'var(--s-1)', alignItems: 'center', minWidth: '0' } }, icono(ico, { clase: 's' }), h('span', { style: S.corte, title: txt }, txt));
  return h('span', { style: { ...S.pila('var(--s-1)'), ...S.meta, marginTop: 'var(--s-1)' } },
    linea('video', `Taller: ${TXT_T[t.estado] || 'sin dato'}${t.fecha ? ' · ' + fechaHora(t.fecha) : ''}`),
    linea('aj', `Configuración: ${TXT_C[c.estado] || 'sin dato'}${c.fecha ? ' · ' + fechaHora(c.fecha) : ''}`));
}

function filaAlta(a, d, ctx, puedeAbrir) {
  const sig = a.siguiente;
  const [estSig] = ESTADOS_HITO[sig?.estado] || ['gris'];
  const o = a.onboarding;
  const rojas = a.alertas.filter(x => x.estado === 'rojo').length;
  const difRojas = (a.diferencias || []).filter(x => x.estado === 'rojo').length;
  const encendida = a.plazo.dia_encendido !== null && a.plazo.dia_encendido !== undefined;
  const textoPlazo = ({ rojo: encendida ? 'Encendida tarde' : 'Fuera de plazo', ambar: encendida ? 'Encendida el día 11-12' : 'En riesgo', verde: 'Encendida en plazo', gris: 'En plazo, sin encender' })[a.plazo.estado] || a.plazo.texto;
  const cuerpo = [
    h('div', { style: { display: 'flex', gap: 'var(--s-3)', alignItems: 'flex-start', minWidth: '0' } }, logoCliente(ctx.clientes.find(c => c.id === a.cliente_id) || { nombre: a.nombre }),
      h('span', { style: { ...S.pila('0'), flex: '1 1 0' } },
        h('span', { style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-1) var(--s-2)', alignItems: 'center', minWidth: '0' } }, h('b', { style: { ...S.h3, overflowWrap: 'anywhere', minWidth: '0' }, title: a.nombre }, a.nombre), a.urgente ? chipEstado('rojo', 'Prioritaria') : null),
        h('span', { style: { ...S.meta, ...S.corte } }, [a.account ? `Account ${a.account.nombre}` : (a.sin_account ? a.sin_account.charAt(0).toUpperCase() + a.sin_account.slice(1) : 'Sin account'), `alta ${fechaLarga(a.alta)}`].join(' · ')),
        lineaEquipo(a.equipo))),
    h('div', { style: S.pila('var(--s-2)') },
      h('div', { style: { display: 'flex', justifyContent: 'space-between', gap: 'var(--s-2)', ...S.metaMid } },
        h('span', {}, h('b', { style: { color: 'var(--ink)', fontWeight: 700 } }, `Día ${a.dia}`), ' de 90'),
        h('span', { style: S.corte }, encendida ? `encendida el día ${a.plazo.dia_encendido}` : `límite ${fechaLarga(a.plazo.limite)}`)),
      pista(a, d.reglas),
      h('span', { title: a.plazo.texto, style: { display: 'flex', minWidth: '0' } }, chipCorto(a.plazo.estado === 'gris' ? 'azul' : a.plazo.estado, textoPlazo))),
    barraAvance(o),
    h('div', { style: S.pila('var(--s-1)') },
      h('span', { style: { display: 'flex', alignItems: 'center', gap: 'var(--s-2)', ...S.h3, minWidth: '0' } }, h('span', { style: { color: 'var(--accent)', display: 'inline-flex' } }, icono(ICONO_HITO[sig?.id] || 'flag', { clase: 's' })),
        h('span', { style: S.corte, title: pasoDe(sig) }, pasoDe(sig))),
      sig ? h('span', { style: { ...S.meta, ...S.corte } }, `${sig.quien} · ${sig.objetivo ? `objetivo ${fechaLarga(sig.objetivo)}` : 'sin fecha'}`) : null,
      sig ? h('span', { style: { display: 'flex', minWidth: '0' } }, chipCorto(estSig, ESTADOS_HITO[sig.estado]?.[1] || sig.estado)) : null),
    h('div', { style: { display: 'flex', gap: 'var(--s-2)', flexWrap: 'wrap', alignItems: 'center', minWidth: '0' } },
      o?.vencidas ? chipEstado('rojo', `${o.vencidas} vencida${o.vencidas === 1 ? '' : 's'}`) : null,
      o?.bloqueadas ? chipEstado('ambar', `${o.bloqueadas} bloqueada${o.bloqueadas === 1 ? '' : 's'}`) : null,
      difRojas ? chipEstado('ambar', `${difRojas} diferencia${difRojas === 1 ? '' : 's'}`) : null,
      !o ? chipEstado(a.alertas.some(x => x.tipo === 'sin_tareas' && x.estado === 'rojo') ? 'rojo' : 'ambar', 'Sin tareas') : null,
      rojas && !o?.vencidas && o ? chipEstado('rojo', `${rojas} alerta${rojas === 1 ? '' : 's'}`) : null,
      h('span', { class: 'av s', title: `Dueño: ${a.dueno.nombre} (técnico de altas, hasta el día 90)`, 'aria-label': `Dueño: ${a.dueno.nombre}` }, iniciales(a.dueno.nombre))),
  ];
  // Fila = tarjeta común (.tile: borde, sombra y realce al pasar el ratón) con 5 columnas que se pliegan solas (5 → 3 → 1).
  const estilo = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 176px), 1fr))', gap: 'var(--s-3) var(--s-5)', alignItems: 'center', width: '100%',
    borderLeft: `4px solid ${a.plazo.estado === 'gris' ? 'var(--line)' : COLOR_ESTADO[a.plazo.estado]}`, font: 'var(--t-cuerpo)' };
  if (!puedeAbrir) return h('div', { class: 'tile', role: 'listitem', style: estilo }, cuerpo);
  return h('button', { type: 'button', class: 'tile', role: 'listitem', style: { ...estilo, cursor: 'pointer' }, 'aria-label': `${a.nombre}, día ${a.dia} de 90, ${a.plazo.texto}. Abrir la línea de tiempo`,
    on: { click: () => ctx.navegar(`${ID}/${a.cliente_id}`) } }, cuerpo);
}

// ================================================================== lista

/** Cifras recalculadas con las altas que la persona recibe (el servidor ya recortó): nadie ve totales de la casa que no le tocan. */
function resumenDe(altas, d) {
  const lim = d.reglas.encendido_limite, obj = d.reglas.encendido_objetivo;
  const llegan = altas.filter(a => a.dia >= lim);
  const si = llegan.filter(a => a.plazo.dia_encendido !== null && a.plazo.dia_encendido !== undefined && a.plazo.dia_encendido <= obj).length;
  const suma = k => altas.reduce((n, a) => n + ((a.onboarding || {})[k] || 0), 0);
  const { desde: l, hasta: dom } = fechas.semana();   // V2-E: de lunes a domingo de la semana de hoy (Madrid)
  return {
    en_plazo_dia12: { si, de: llegan.length, pct: llegan.length ? Math.round(si / llegan.length * 100) : null },
    fuera_de_plazo: altas.filter(a => a.plazo.estado === 'rojo').length,
    sin_tareas: altas.filter(a => !a.onboarding).length,
    sin_tareas_48h: altas.filter(a => !a.onboarding && (a.horas_desde_firma || 0) > d.reglas.sin_tareas_horas).length,
    tareas_vencidas: suma('vencidas'), tareas_no_avanzan: suma('no_avanza'), tareas_bloqueadas: suma('bloqueadas'),
    tareas_sin_plazo: suma('sin_plazo'), tareas_total: suma('n'),
    carga_semana: altas.filter(a => a.alta >= l && a.alta <= dom).length, carga_tope: d.reglas.carga_tope_semana || 5,
  };
}
function pintarLista(cont, ctx, d, acciones) {
  const altas = d.altas || [];
  const r = resumenDe(altas, d);
  const reglas = d.reglas;
  const verTodo = ctx.nivel === 'todo';
  const puedeAbrir = ctx.nivel !== 'resumen';
  ctx.titulo('Clientes nuevos', `${altas.length} alta${altas.length === 1 ? '' : 's'} entre la firma y el día 90 · encendido el día ${reglas.encendido_objetivo}, como tarde el ${reglas.encendido_limite}`);

  cont.append(avisoDatos(d));

  if (!altas.length) {
    cont.append(vacio({ icono: 'rocket', titulo: verTodo ? 'No hay ninguna alta entre la firma y el día 90' : 'Ninguno de tus clientes está en alta', tono: verTodo ? 'neutro' : 'celebrar', borde: true,
      texto: verTodo ? 'Cuando se firme un acuerdo en Zoho Sign, aparecerá aquí con su día 0 (fecha de alta del contrato).' : 'Aquí salen tus clientes del día 0 al 90. Ahora mismo no llevas ninguno en arranque; si crees que falta alguno, revisa las asignaciones con Mili.',
      quien: verTodo ? null : 'Mili' }));
  }

  // ---- 1 · lo primero hoy (lo que pide acción, arriba del todo) ----
  // Una línea por cliente: su alerta más grave como titular y el resto de motivos en la misma línea.
  const porCliente = altas.map(a => {
    const al = [...a.alertas].sort((x, y) => rangoAlerta(x) - rangoAlerta(y));
    return al.length ? { alta: a, top: al[0], resto: al.slice(1) } : null;
  }).filter(Boolean).sort((x, y) => rangoAlerta(x.top) - rangoAlerta(y.top) || (y.alta.urgente - x.alta.urgente) || y.alta.dia - x.alta.dia);
  const primeras = porCliente.slice(0, 7);
  if (altas.length && puedeAbrir) {
    const escaladas = new Set(acciones.filter(a => a.tipo === 'escalar').map(a => a.objeto));
    const item = ({ alta: a, top: x, resto }) => {
      const objeto = a.cliente_id;
      const otros = [...new Set(resto.map(y => TEXTO_ALERTA[y.tipo] || y.tipo).filter(t => t !== (TEXTO_ALERTA[x.tipo] || x.tipo)))];
      const dosRojos = x.estado === 'rojo' && (x.tipo === 'fuera_plazo' || x.tipo === 'sin_tareas' || x.tipo === 'urgente' || x.tipo === 'config_sin_agendar');
      const fuera = [
        a.onboarding?.url ? { texto: 'ClickUp', icono: 'ext', href: a.onboarding.url } : null,
        a.subcuenta ? { texto: 'GHL', icono: 'base', href: ghlUrl(a.subcuenta.loc) } : null,
      ].filter(Boolean);
      return {
        estado: x.estado, icono: ICONO_ALERTA[x.tipo] || 'alert',
        motivo: `${a.nombre} · ${TEXTO_ALERTA[x.tipo] || x.tipo}`,
        detalle: `${/[.!?]$/.test(x.texto) ? x.texto : x.texto + '.'}${otros.length ? ` También: ${otros.join(' · ').toLowerCase()}.` : ''}${escaladas.has(objeto) ? ' Ya escalado (simulado).' : ''}`,
        // Un botón principal + «Escalar» si toca; las herramientas de fuera, en el menú «Abrir en…» (guía: 1 primario + menú)
        botones: [
          btMini({ href: `#/${ID}/${a.cliente_id}` }, icono('hist'), 'Ver la línea de tiempo'),
          x.estado === 'rojo' && !escaladas.has(objeto) ? botonAccion(ctx, { texto: 'Escalar', pregunta: dosRojos ? '¿Escalar a Coti y a Mili?' : '¿Escalar a Mili?', confirmar: 'Sí, escalar',
            accion: { herramienta: 'app', tipo: 'escalar', objeto, cliente_id: a.cliente_id, texto: `${a.nombre}: ${x.texto}`,
              vista_previa: { a: dosRojos ? ['Coti', 'Mili'] : ['Mili'], motivos: [TEXTO_ALERTA[x.tipo], ...otros], alta: a.nombre, dia: a.dia } } }) : null,
          fuera.length ? menuAbrir(`Abrir ${a.nombre} en otra herramienta`, fuera) : null,
        ],
      };
    };
    cont.append(panel({ titulo: 'Lo primero hoy', icono: 'zap', sub: `${porCliente.length} de las ${altas.length} altas tienen algo pendiente; aquí, una línea por alta y lo más grave arriba${porCliente.length > primeras.length ? ` (las ${primeras.length} primeras)` : ''}. «Escalar» deja la acción en la cola simulada.` },
      primeras.length ? recortado(primeras, 4, vis => listaLoPrimero(vis.map(item)), { nombre: 'todas' })
        : h('div', { class: 'cuerpo' }, vacioLinea('Ninguna alerta en las altas: todo en plazo, sin tareas vencidas ni bloqueos.', { icono: 'ok' }))));
  }

  // ---- 2 · cifras (el número de Agus primero; 4 tarjetas, sin huérfanas) ----
  const ep = r.en_plazo_dia12 || {};
  const sinCfg = altas.filter(a => a.hitos.some(x => x.id === 'config' && x.sin_agendar) && a.equipo?.config_basicas?.estado === 'sin_agendar');
  const fichas = [
    tile({ icono: 'rocket', etiqueta: 'Altas encendidas en plazo', valor: ep.de ? fmt.pct(ep.pct) : null, unidad: ep.de ? `${ep.si} de ${ep.de}` : '',
      estado: !ep.de ? 'gris' : ep.pct === 100 ? 'verde' : ep.si === ep.de ? 'ambar' : 'rojo',
      contexto: ep.de ? `Encendidas el día ${reglas.encendido_objetivo} o antes, de las que ya llegan a su día ${reglas.encendido_limite}. Verde: 100 %` : 'Sin dato: ninguna alta llega todavía a su día 12', medible: 'hoy', frescura: fres(d.fuentes.meta, 'Meta'),
      ir: 'Ver fuera de plazo', alPulsar: () => elegirChip(cont, 'fuera') }),
    tile({ icono: 'alert', etiqueta: 'Fuera de plazo', valor: r.fuera_de_plazo, unidad: `de ${altas.length}`, estado: r.fuera_de_plazo ? 'rojo' : 'verde',
      contexto: `Pasado el día ${reglas.encendido_limite} sin encender, o encendidas tarde`, medible: 'hoy', frescura: fres(d.fuentes.meta, 'Meta'), ir: 'Ver cuáles', alPulsar: () => elegirChip(cont, 'fuera') }),
    tile({ icono: 'capas', etiqueta: 'Sin tareas a las 48 h', valor: r.sin_tareas_48h, unidad: r.sin_tareas > r.sin_tareas_48h ? `+${r.sin_tareas - r.sin_tareas_48h} en plazo` : '',
      estado: r.sin_tareas_48h ? 'rojo' : r.sin_tareas ? 'ambar' : 'verde', contexto: 'Alta sin lista de arranque en ClickUp 48 h después de la firma', medible: 'hoy', frescura: fres(d.fuentes.clickup, 'ClickUp'),
      ir: 'Ver cuáles', alPulsar: () => elegirChip(cont, 'sin_tareas') }),
    tile({ icono: 'aj', etiqueta: 'Configuración sin agendar', valor: sinCfg.length, unidad: sinCfg.length ? sinCfg.map(a => a.nombre).join(', ') : '',
      estado: sinCfg.length ? 'rojo' : 'verde', contexto: 'Lo declara el equipo de arranque: sin configuración básica no hay encendido', medible: 'medias', medibleDetalle: 'Estado declarado a mano por el equipo; se cruza con ClickUp', ir: 'Ver el equipo', alPulsar: () => irPestana(cont, 'equipo') }),
  ];
  if (altas.length) cont.append(tiles(fichas));
  // V2 (B-M5): cómo cuadran 17, 8 y 16 en una línea llana
  if (altas.length && ep.de !== undefined) {
    const aun = altas.length - (ep.de || 0);
    const cuadra = (ep.si || 0) + (r.fuera_de_plazo || 0) === ep.de;
    cont.append(h('p', { class: 'sub', style: { margin: '0', maxWidth: '90ch' } },
      `Cómo cuadran las cifras: ${altas.length} altas en arranque (de la firma al día 90). ${fmt.num(ep.de || 0)} ya pasaron su día ${reglas.encendido_limite} y se pueden juzgar: `
      + (cuadra ? `${fmt.num(ep.si || 0)} ${ep.si === 1 ? 'se encendió' : 'se encendieron'} en plazo y ${fmt.num(r.fuera_de_plazo || 0)} ${r.fuera_de_plazo === 1 ? 'está' : 'están'} fuera de plazo (sin encender o encendidas tarde).` : `${fmt.num(ep.si || 0)} ${ep.si === 1 ? 'se encendió' : 'se encendieron'} en plazo; ${fmt.num(r.fuera_de_plazo || 0)} de las ${altas.length} ${r.fuera_de_plazo === 1 ? 'está' : 'están'} fuera de plazo.`)
      + ` ${aun === 1 ? 'La otra aún está' : `Las otras ${fmt.num(aun)} aún están`} dentro de su plazo.${porCliente.length ? ` ${porCliente.length} de las ${altas.length} tienen algo pendiente en «Lo primero hoy».` : ''}`));
  }

  // ---- 3 · altas en curso ----
  if (altas.length) {
    const grupos = {
      '': altas,
      fuera: altas.filter(a => a.plazo.estado === 'rojo'),
      riesgo: altas.filter(a => a.plazo.estado === 'ambar'),
      sin_tareas: altas.filter(a => !a.onboarding),
      plazo: altas.filter(a => a.plazo.estado === 'gris' || a.plazo.estado === 'verde'),
      mias: altas.filter(a => ctx.carteraIds.has(a.cliente_id)),
    };
    const opciones = [
      { valor: '', texto: 'Todas', cuenta: altas.length },
      { valor: 'fuera', texto: 'Fuera de plazo', icono: 'alert', cuenta: grupos.fuera.length, cuentaEstado: 'rojo' },
      { valor: 'riesgo', texto: 'En riesgo', icono: 'clock', cuenta: grupos.riesgo.length, cuentaEstado: 'rojo' },
      { valor: 'sin_tareas', texto: 'Sin tareas', icono: 'capas', cuenta: grupos.sin_tareas.length, cuentaEstado: 'rojo' },
      { valor: 'plazo', texto: 'En plazo', icono: 'ok', cuenta: grupos.plazo.length },
    ];
    if (ctx.carteraIds.size && verTodo) opciones.push({ valor: 'mias', texto: 'Mis clientes', icono: 'persona', cuenta: grupos.mias.length });
    const caja = h('div', { role: 'list', 'aria-label': 'Altas en curso', style: S.pila() });
    const chips = chipsFiltro({ etiqueta: 'Ver', clave: 'nuevos.vista', opciones, alCambiar: () => pintarFilas() });
    chips.id = 'm12-chips';
    const pintarFilas = () => {
      const lista = grupos[chips.valor()] || altas;
      caja.replaceChildren(lista.length ? recortado(lista, 6, vis => vis.map(a => filaAlta(a, d, ctx, puedeAbrir)), { nombre: 'todas las altas' })
        : vacioLinea('Ninguna alta en este filtro. Prueba con «Todas».', { icono: 'ok' }));
    };
    pintarFilas();
    cont.append(panel({ titulo: 'Altas en curso', icono: 'rocket', sub: `Día X de 90 y el % de tareas hechas de su lista de arranque.${puedeAbrir ? ' Pulsa una fila para ver su línea de tiempo.' : ''}`,
      pie: leyenda([
        [muestra('var(--ink)', 'linea'), `día ${reglas.encendido_objetivo} (objetivo)`],
        [muestra('var(--bad)', 'linea'), `día ${reglas.encendido_limite} (límite)`],
        [h('span', { style: { display: 'inline-flex', color: 'var(--good-ink)' }, 'aria-hidden': 'true' }, icono('rocket', { clase: 's' })), 'encendida: primer día con gasto real en Meta'],
        [h('span', { style: { display: 'inline-flex', gap: 'var(--s-1)' } }, muestra('var(--good)'), muestra('var(--bad)'), muestra('var(--warn)')), 'tareas hechas · vencidas · bloqueadas'],
      ]) },
      h('div', { class: 'cuerpo', style: { paddingBottom: '0' } }, chips),
      h('div', { class: 'cuerpo' }, caja)));
  }

  // ---- 4 · lo de cada semana: cifras de apoyo + pestañas (orden de la ficha de Agus) ----
  if (puedeAbrir) cont.append(pestanasSemana(cont, ctx, d, acciones, r));
  else cont.append(avisoParcial('Ves el resumen de las altas. La línea de tiempo, los accesos y las casillas los ven Agus, Mili, Coti, las jefas y quien lleva el cliente.', { tipo: 'info', titulo: 'Vista de resumen.' }));

  cont.append(nota('Cómo se cuenta', 'El día 0 es la fecha de alta del contrato en Zoho Sign (no la de la firma). El encendido es el primer día con 5 € o más de gasto en Meta seguido de otros dos días con gasto (un céntimo suelto no cuenta), en la fecha de la cuenta de Meta. Los leads se cuentan igual que en Captación. Las tareas sin fecha límite salen «sin plazo» en gris hasta que la plantilla ponga las fechas solas. La primera reunión de resultados sale del CRM y de Fathom; Zoom completo llega con el módulo de reuniones.'));
}

function elegirChip(cont, valor) {
  const caja = cont.querySelector('#m12-chips');
  if (!caja) return;
  const op = { fuera: 'Fuera de plazo', sin_tareas: 'Sin tareas', riesgo: 'En riesgo' }[valor];
  const b = [...caja.querySelectorAll('button')].find(x => x.textContent.startsWith(op));
  if (b && b.getAttribute('aria-pressed') !== 'true') b.click();
  caja.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
function irPestana(cont, id) {
  const p = cont.querySelector('#m12-pestanas');
  if (!p) return;
  p.elegir?.(id);
  p.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ------------------------------------------------------------------ pestañas de la lista
function pestanasSemana(cont, ctx, d, acciones, r) {
  const altas = d.altas || [];
  const verTodo = ctx.nivel === 'todo';
  const reglas = d.reglas;
  const subs = (d.subcuentas || []).filter(s => verTodo || s.cliente_id);
  const accFalta = altas.reduce((n, a) => n + a.accesos.filter(x => x.estado === 'falta').length, 0);
  const casRojas = altas.reduce((n, a) => n + a.casillas.filter(x => x.estado === 'rojo').length, 0);
  const caidas = subs.filter(s => s.estado === 'rojo').length;
  const bloqueosMeta = altas.filter(a => a.meta && a.meta.estado_num !== 1).length;
  const conGarantia = altas.filter(a => a.garantia).length;
  const talleres = (d.talleres || []);
  // Cifras de cada semana (apoyo): 4 tarjetas que llevan a su pestaña. Sin GHL leído, la de conexiones sale en gris con su porqué.
  const ghlBien = d.fuentes.ghl?.estado === 'bien';
  const apoyo = altas.length ? tiles([
    tile({ icono: 'cal', etiqueta: 'Tareas vencidas', valor: r.tareas_vencidas, unidad: `de ${fmt.num(r.tareas_total)}`, estado: !r.tareas_total ? 'gris' : r.tareas_vencidas ? 'rojo' : 'verde',
      contexto: `${fmt.num(r.tareas_sin_plazo)} tareas sin plazo esperan las fechas automáticas`, medible: 'medias', medibleDetalle: 'Solo cuentan las tareas que tienen fecha límite en ClickUp', frescura: fres(d.fuentes.clickup, 'ClickUp'),
      ir: 'Ver fechas automáticas', alPulsar: () => irPestana(cont, 'plantilla') }),
    tile({ icono: 'candado', etiqueta: 'Bloqueadas', valor: r.tareas_bloqueadas, unidad: r.tareas_no_avanzan ? `${r.tareas_no_avanzan} no avanzan` : '', estado: !r.tareas_total ? 'gris' : r.tareas_bloqueadas ? 'ambar' : 'verde',
      contexto: `Se escala si pasa de ${reglas.bloqueo_escalar_dias} días bloqueada`, medible: 'hoy', frescura: fres(d.fuentes.clickup, 'ClickUp') }),
    tile({ icono: 'users', etiqueta: 'Arranques esta semana', valor: r.carga_semana, unidad: `tope ${r.carga_tope}`, estado: r.carga_semana <= r.carga_tope ? 'verde' : r.carga_semana === r.carga_tope + 1 ? 'ambar' : 'rojo',
      contexto: 'Carga de altas de Agus: verde hasta 5 · ámbar 6 · rojo más de 6', medible: 'hoy', frescura: fres(d.fuentes.sign, 'Zoho Sign') }),
    ghlBien ? tile({ icono: 'plug', etiqueta: 'Conexiones caídas', valor: caidas, unidad: `de ${subs.length} subcuentas`, estado: caidas === 0 ? 'verde' : caidas <= 3 ? 'ambar' : 'rojo',
      contexto: 'WhatsApp con fallos o calendario sin usuario. Verde 0 · ámbar 1-3 · rojo más de 3', medible: 'medias', medibleDetalle: 'El estado del número de WhatsApp y la calidad del píxel no tienen API', frescura: fres(d.fuentes.ghl, 'GHL'),
      ir: 'Ver cuáles', alPulsar: () => irPestana(cont, 'conexiones') })
      : tile({ icono: 'plug', etiqueta: 'Conexiones caídas', valor: null, estado: 'gris', contexto: 'Sin dato: falta la lectura de las subcuentas de GHL' }),
  ]) : null;
  const p = pestanas({
    clave: 'nuevos.pestana', etiqueta: 'Seguimiento de las altas',
    pestanas: [
      { id: 'equipo', texto: 'Equipo', icono: 'compartir', cuenta: altas.reduce((n, a) => n + (a.diferencias || []).filter(x => x.estado === 'rojo').length, 0), cuentaEstado: 'rojo' },
      { id: 'accesos', texto: 'Accesos', icono: 'key', cuenta: accFalta, cuentaEstado: 'rojo' },
      { id: 'casillas', texto: 'Casillas', icono: 'check', cuenta: casRojas, cuentaEstado: 'rojo' },
      { id: 'conexiones', texto: 'Conexiones', icono: 'plug', cuenta: caidas, cuentaEstado: 'rojo' },
      { id: 'talleres', texto: 'Talleres', icono: 'video', cuenta: talleres.filter(t => !t.pasado).length },
      { id: 'meta', texto: 'Meta', icono: 'megafono', cuenta: bloqueosMeta, cuentaEstado: 'rojo' },
      { id: 'garantia', texto: 'Garantía', icono: 'escudo', cuenta: conGarantia },
      { id: 'vienen', texto: 'Por firmar', icono: 'doc', cuenta: (d.previstas || []).length },
      { id: 'plantilla', texto: 'Fechas', icono: 'cal' },
    ],
    pintar: (id, zona) => {
      if (id === 'equipo') zona.append(tablaEquipo(ctx, d, altas));
      else if (id === 'accesos') zona.append(matrizAccesos(ctx, altas));
      else if (id === 'casillas') zona.append(matrizCasillas(ctx, altas));
      else if (id === 'conexiones') zona.append(tablaConexiones(ctx, d, subs));
      else if (id === 'talleres') zona.append(tablaTalleres(ctx, d));
      else if (id === 'meta') zona.append(tablaMeta(ctx, altas));
      else if (id === 'garantia') zona.append(tablaGarantia(ctx, altas));
      else if (id === 'vienen') zona.append(tablaVienen(d));
      else if (id === 'plantilla') zona.append(plantillaDN(ctx, d, null, acciones));
    },
  });
  p.id = 'm12-pestanas';
  return panel({ titulo: 'Seguimiento de las altas', icono: 'capas', sub: 'Lo de cada semana: tareas, accesos, casillas, conexiones de las subcuentas, talleres, Meta, garantía y lo que viene.' },
    apoyo ? h('div', { class: 'cuerpo', style: { paddingBottom: '0' } }, apoyo) : null,
    h('div', { class: 'cuerpo' }, p));
}

function tablaEquipo(ctx, d, altas) {
  const conEq = altas.filter(a => a.equipo || (a.diferencias || []).length);
  const ef = d.equipo_fuente || {};
  if (!conEq.length) return vacioLinea('Sin estado del equipo: aún no se ha declarado el estado de ninguna alta.', { icono: 'compartir', quien: 'Agus' });
  return h('div', { style: S.pila() },
    recortado(conEq, 6, vis => tablaApilable({
      filas: vis,
      alPulsar: a => ctx.navegar(`${ID}/${a.cliente_id}`), etiquetaFila: a => `${a.nombre}: abrir la línea de tiempo`,
      columnas: [
        { clave: 'nombre', titulo: 'Alta', principal: true, celda: a => h('span', { style: S.pila('0') }, h('span', { style: { display: 'flex', gap: 'var(--s-2)', alignItems: 'center', flexWrap: 'wrap' } }, h('b', { style: S.h3 }, a.nombre), a.urgente ? chipEstado('rojo', 'Prioritaria') : null), h('span', { style: S.meta }, `día ${a.dia}`)) },
        { clave: 'taller', titulo: 'Taller de oferta', celda: a => { const t = a.equipo?.taller || {}; return chipEstado(t.estado === 'hecho' ? 'verde' : ['agendado', 'segunda_sesion'].includes(t.estado) ? 'azul' : a.equipo ? 'ambar' : 'gris', a.equipo ? `${TXT_T[t.estado] || 'sin dato'}${t.fecha ? ' · ' + fechaHora(t.fecha) : ''}` : 'sin dato del equipo'); } },
        { clave: 'config', titulo: 'Configuración básica', celda: a => { const c = a.equipo?.config_basicas || {}; return chipEstado(c.estado === 'hecho' ? 'verde' : c.estado === 'agendada' ? 'azul' : c.estado === 'sin_agendar' ? 'rojo' : a.equipo ? 'ambar' : 'gris', a.equipo ? `${TXT_C[c.estado] || 'sin dato'}${c.fecha ? ' · ' + fechaHora(c.fecha) : ''}` : 'sin dato del equipo'); } },
        { clave: 'estado', titulo: 'Estado y paso (equipo)', celda: a => a.equipo ? h('span', { style: { ...S.pila('var(--s-1)'), minWidth: 'min(200px, 30vw)', textAlign: 'left' } }, h('span', { style: { overflowWrap: 'anywhere', minWidth: '0' } }, a.equipo.estado), h('span', { style: { ...S.meta, overflowWrap: 'anywhere', minWidth: '0' } }, `→ ${a.equipo.proximo_paso}`)) : h('span', { style: S.meta }, 'Sin estado declarado') },
        { clave: 'dif', titulo: 'Lo que ve la app', celda: a => { const ds = (a.diferencias || []).filter(x => x.estado !== 'verde'); const ok = (a.diferencias || []).filter(x => x.estado === 'verde'); return h('span', { style: { ...S.pila('var(--s-1)'), justifyItems: 'start', maxWidth: 'min(320px, 60vw)' } }, ds.map(x => chipCorto(x.estado, x.app)), ok.map(x => chipCorto('verde', x.app)), !ds.length && !ok.length ? chipEstado('verde', 'Sin diferencias') : null); } },
      ],
    }), { nombre: 'todas las altas' }),
    nota('De dónde sale', `Estado declarado por el ${ef.autor || 'equipo de arranque'} el ${fechaLarga(ef.fecha)} y cruzado con ClickUp, GHL, Meta y Sign. ${ef.edicion || ''}`));
}

const PUNTO = { dado: ['verde', 'ok', 'Dado'], falta: ['rojo', 'cerrar', 'Falta'], sin_registro: ['gris', 'info', 'Sin registro'] };
/** Punto de estado = cuadrito de icono común (.ico-c s) con su color. */
function punto(estado, titulo) {
  const [cls, ico, txt] = PUNTO[estado] || [estado, estado === 'verde' ? 'ok' : estado === 'rojo' ? 'cerrar' : estado === 'ambar' ? 'alert' : 'info', ''];
  return h('span', { class: `ico-c s ${cls}`, title: titulo || txt, role: 'img', 'aria-label': titulo || txt, style: { display: 'inline-grid' } }, icono(ico));
}
/** Tabla de matriz (cliente × recurso) con la tabla común .densa: cabeceras en mayúsculas 11/700, celdas centradas. */
function matriz(cabeceras, filas) {
  return h('div', { class: 'tabla-scroll' }, h('table', { class: 'densa' },
    h('thead', {}, h('tr', {}, cabeceras.map((c, i) => h('th', { scope: 'col', title: c.titulo || null, style: i ? { textAlign: 'center' } : null }, c.texto)))),
    h('tbody', {}, filas.map(celdas => h('tr', {}, celdas.map((c, i) => h('td', { style: i ? { textAlign: 'center' } : { minWidth: '160px' } }, c)))))));
}
const celdaAlta = (a, sub) => h('span', { style: S.pila('0') }, enlaceAlta(a), h('span', { style: S.meta }, sub));

function matrizAccesos(ctx, altas) {
  if (!altas.length) return vacioLinea('Sin altas: no hay accesos que perseguir.', { icono: 'key' });
  const recursos = altas[0].accesos.map(x => x.recurso);
  const corto = { 'Meta (portfolio, cuenta y píxel)': 'Meta', 'CRM (subcuenta de GHL)': 'CRM', 'Google Analytics': 'Analytics', 'Search Console': 'Search Console', 'Redes (Metricool)': 'Redes', 'Canal de ClickUp': 'Canal', 'Web (WordPress)': 'Web', 'Ficha de Google': 'Ficha de Google' };
  const orden = [...altas].sort((a, b) => b.accesos.filter(x => x.estado === 'falta').length - a.accesos.filter(x => x.estado === 'falta').length || b.dia - a.dia);
  return h('div', { style: S.pila() },
    matriz([{ texto: 'Cliente · día' }, ...recursos.map(r => ({ texto: corto[r] || r, titulo: r })), { texto: 'Encargo art. 28', titulo: 'Encargo de tratamiento (art. 28 RGPD)' }],
      orden.map(a => { const faltan = a.accesos.filter(x => x.estado === 'falta').length; return [
        celdaAlta(a, `día ${a.dia}${faltan ? ` · faltan ${faltan}` : ''}`),
        ...a.accesos.map(x => punto(x.estado, `${x.recurso}: ${PUNTO[x.estado]?.[2] || x.estado} · ${x.prueba}${x.quien ? ` · lo tiene ${x.quien}` : ''}${x.estado === 'falta' ? ` · desde el ${fechaLarga(x.desde)}` : ''}`)),
        punto(a.encargo_art28 ? 'dado' : a.encargo_art28 === false ? 'falta' : 'sin_registro', a.encargo_art28 ? 'Firmado: la cláusula de encargo de tratamiento (art. 28 RGPD) va en el acuerdo de Zoho Sign' : 'Sin prueba del encargo de tratamiento'),
      ]; })),
    leyenda([[punto('dado'), 'dado (con prueba en la herramienta)'], [punto('falta'), 'falta'], [punto('sin_registro'), 'sin registro: se marca a mano con prueba']]),
    nota('De dónde sale', 'Nunca se enseña una clave: solo «dado / falta / quién lo tiene / desde cuándo». Meta y CRM salen de si RO ve la cuenta o la subcuenta; Analytics, Search Console, Redes y el canal, de los emparejamientos de la capa de datos; la web y la ficha de Google no tienen registro en ninguna herramienta. El encargo de tratamiento va dentro del acuerdo firmado (cláusula «Encargo de tratamiento (art. 28 RGPD)»).'));
}

function matrizCasillas(ctx, altas) {
  if (!altas.length) return vacioLinea('Sin altas: no hay casillas técnicas que revisar.', { icono: 'check' });
  const ids = altas[0].casillas.map(x => x.id);
  const titulo = Object.fromEntries(altas.flatMap(a => a.casillas.map(x => [x.id, x.texto])));
  const todas = [...new Set(altas.flatMap(a => a.casillas.map(x => x.id)))];
  const corto = { pixel: 'Píxel', dominio: 'Dominio en Meta', spf: 'SPF', dmarc: 'DMARC', dkim: 'DKIM', dns: 'DNS', whatsapp: 'WhatsApp', calendario: 'Calendario', snapshot: 'Subcuenta', landing_posts: 'Landing y posts' };
  const cols = todas.length ? todas : ids;
  return h('div', { style: S.pila() },
    matriz([{ texto: 'Cliente · web' }, ...cols.map(c => ({ texto: corto[c] || titulo[c] || c, titulo: titulo[c] }))],
      altas.map(a => [celdaAlta(a, a.dominio || 'sin web'),
        ...cols.map(c => { const x = a.casillas.find(y => y.id === c); return x ? punto(x.estado, `${x.texto}: ${x.detalle} (${x.fuente})`) : punto('gris', 'No aplica'); })])),
    leyenda([[punto('verde'), 'bien'], [punto('ambar'), 'vigilar'], [punto('rojo'), 'falta o falla'], [punto('gris'), 'sin dato o todavía no se mide']]),
    nota('De dónde sale', 'SPF, DKIM y DMARC salen de una consulta DNS pública (sin permisos). El DKIM se prueba con los selectores habituales: si no aparece, puede usar otro; confírmalo con su proveedor de correo. El dominio verificado en Meta y la casilla «Landing y posts revisados» todavía se marcan a mano.'));
}

function tablaConexiones(ctx, d, subs) {
  if (d.fuentes.ghl?.estado !== 'bien') return vacioLinea('Sin lectura de las subcuentas de GHL: la lectura no ha terminado o ha fallado. Se relanza desde el generador de altas.', { icono: 'plug', quien: 'Agus' });
  const opciones = [
    { valor: 'problema', texto: 'Con problema', icono: 'alert', cuenta: subs.filter(s => s.estado !== 'verde').length, cuentaEstado: 'rojo' },
    { valor: 'alta', texto: 'Altas (hasta el día 90)', icono: 'rocket', cuenta: subs.filter(s => s.en_alta).length },
    { valor: '', texto: 'Todas', cuenta: subs.length },
  ];
  const caja = h('div');
  const chips = chipsFiltro({ etiqueta: 'Ver', clave: 'nuevos.conexiones', opciones, alCambiar: () => pintar() });
  const pintar = () => {
    const v = chips.valor();
    const filas = subs.filter(s => v === 'problema' ? s.estado !== 'verde' : v === 'alta' ? s.en_alta : true);
    if (!filas.length) { caja.replaceChildren(vacioLinea(v === 'problema' ? 'Ninguna subcuenta con la conexión caída: WhatsApp sin fallos y calendarios con usuario.' : 'Nada en este filtro.', { icono: 'ok' })); return; }
    caja.replaceChildren(recortado(filas, 8, vis => tablaApilable({
      filas: vis,
      porPagina: 0,
      columnas: [
        { clave: 'subcuenta', titulo: 'Subcuenta', principal: true, celda: s => h('span', { style: { display: 'flex', gap: 'var(--s-2)', alignItems: 'center', minWidth: '0' } }, punto(s.estado === 'verde' ? 'verde' : s.estado, s.estado), h('span', { style: S.pila('0') }, h('b', { style: S.h3, title: s.subcuenta }, nombreSubcuenta(s.subcuenta)), h('span', { style: S.meta }, s.cliente ? `Cliente: ${s.cliente}` : s.tipo))) },
        { clave: 'problemas', titulo: 'Qué falla', celda: s => s.problemas.length ? h('span', { style: { ...S.pila('var(--s-1)'), justifyItems: 'start' } }, s.problemas.map(p => chipEstado(p.estado, p.texto))) : chipEstado('verde', 'Bien') },
        { clave: 'calendarios', titulo: 'Calendarios', num: true, celda: s => s.calendarios === null || s.calendarios === undefined ? 'sin dato' : `${fmt.num(s.calendarios)}${s.calendarios_sin_usuario ? ` (${s.calendarios_sin_usuario} sin usuario)` : ''}` },
        { clave: 'wa', titulo: 'WhatsApp 7 días', num: true, celda: s => s.wa_enviados_7d ? `${fmt.num(s.wa_fallidos_7d)} de ${fmt.num(s.wa_enviados_7d)} fallidos` : 'sin envíos' },
        { clave: 'abrir', titulo: 'Abrir', ordenable: false, celda: s => btMini({ href: ghlUrl(s.loc), target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir en GHL') },
        { clave: 'dueno', titulo: 'Dueño', celda: s => h('span', { style: { display: 'inline-flex', gap: 'var(--s-2)', alignItems: 'center' } }, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(s.dueno)), s.dueno) },
      ],
    }), { nombre: 'todas las subcuentas' }));
  };
  pintar();
  return h('div', { style: S.pila() }, chips, caja,
    nota('Quién lo arregla y cómo se mide', 'Dueño: Agus hasta el día 90 de cada alta; después, el especialista en GHL. A las 24 h sin arreglar, sube a Yessica. WhatsApp: mensajes salientes de los últimos 7 días en las conversaciones con WhatsApp más recientes de cada subcuenta (rojo si fallan más del 10 %). El estado del número de WhatsApp no tiene API.'));
}

function tablaTalleres(ctx, d) {
  const t = d.talleres || [];
  return h('div', { style: S.pila() },
    t.length ? tablaApilable({
      filas: t,
      alPulsar: x => ctx.navegar(`${ID}/${x.cliente_id}`), puedePulsar: x => !!x.cliente_id, etiquetaFila: x => `${x.cliente}: abrir la línea de tiempo`,
      columnas: [
        { clave: 'inicio', titulo: 'Cuándo', principal: true, celda: x => h('span', {}, h('b', { style: S.h3 }, (d => `${_DSN[d.getDay()]} ${d.getDate()}-${_M3N[d.getMonth()]}`)(new Date(x.inicio.replace(' ', 'T')))), ` · ${x.inicio.slice(11, 16)}`) },
        { clave: 'cliente', titulo: 'Cliente', celda: x => x.cliente || 'sin cliente' },
        { clave: 'titulo', titulo: 'Reunión' },
        { clave: 'estado', titulo: 'Estado', celda: x => x.pasado ? chipEstado('gris', 'Celebrado') : chipEstado('azul', 'Agendado') },
      ],
    }) : vacioLinea('Sin talleres en estas tres semanas: no hay talleres de la oferta agendados entre hace 7 días y dentro de 14.', { icono: 'video' }),
    nota('Cómo se confirma', `${d.talleres_nota || ''} La víspera (48 h antes) se confirma; si no contesta, se llama, no otro correo.`));
}

function tablaMeta(ctx, altas) {
  const con = altas.filter(a => a.meta);
  const sin = altas.filter(a => !a.meta);
  return h('div', { style: S.pila() },
    sin.length ? avisoParcial(`RO no ve la cuenta publicitaria de ${sin.length} alta${sin.length === 1 ? '' : 's'}: ${sin.map(a => a.nombre).join(', ')}. Sin ella no hay encendido posible: es el primer acceso que hay que conseguir.`, { titulo: 'Sin cuenta de Meta.' }) : null,
    con.length ? tablaApilable({
      filas: con,
      alPulsar: a => ctx.navegar(`${ID}/${a.cliente_id}`), etiquetaFila: a => `${a.nombre}: abrir la línea de tiempo`,
      columnas: [
        { clave: 'nombre', titulo: 'Cliente', principal: true, celda: a => h('b', { style: S.h3 }, a.nombre) },
        { clave: 'estado', titulo: 'Cuenta', celda: a => h('span', { class: 'fila', style: { gap: 'var(--s-2)' } }, chipEstado(a.meta.estado_num === 1 ? 'verde' : 'rojo', `${a.meta.nombre} · ${a.meta.estado_cuenta || `cuenta ${a.meta.estado}`}`),
          a.campana ? chipEstado(a.campana.encendida ? 'verde' : 'rojo', a.campana.texto) : null) },
        { clave: 'pago', titulo: 'Pago', celda: a => a.meta.con_pago ? chipEstado('verde', 'Con método de pago') : chipEstado('ambar', 'Sin método de pago visible') },
        { clave: 'ultimo', titulo: 'Último día con gasto', celda: a => a.meta.ultimo_dia_con_gasto ? fechaLarga(a.meta.ultimo_dia_con_gasto) : chipEstado('gris', 'Nunca desde la firma') },
        { clave: 'abrir', titulo: 'Abrir', ordenable: false, celda: a => btMini({ href: a.meta.prueba, target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir en Meta') },
      ],
    }) : vacioLinea('RO no ve ninguna cuenta de Meta de las altas: falta que cada despacho comparta su cuenta publicitaria con el portfolio de RO.', { icono: 'megafono' }),
    nota('Si Meta se bloquea', 'Bloqueo de Meta en la reunión de arranque: si pasa de 90 minutos, portfolio nuevo y aviso a Valeria (ficha de Agus).'));
}

function tablaGarantia(ctx, altas) {
  const con = altas.filter(a => a.garantia);
  return h('div', { style: S.pila() },
    con.length ? tablaApilable({
      filas: con,
      alPulsar: a => ctx.navegar(`${ID}/${a.cliente_id}`), etiquetaFila: a => `${a.nombre}: abrir la línea de tiempo`,
      columnas: [
        { clave: 'nombre', titulo: 'Cliente', principal: true, celda: a => h('b', { style: S.h3 }, a.nombre) },
        { clave: 'ventana', titulo: 'Ventana', celda: a => a.garantia.desde ? `${fechaLarga(a.garantia.desde)} → ${fechaLarga(a.garantia.hasta)}` : 'Empieza con el encendido' },
        { clave: 'validas', titulo: 'Reuniones celebradas', num: true, celda: a => h('span', {}, h('b', {}, `${a.garantia.validas} de ${a.garantia.necesarias}`), a.garantia.sin_estado ? h('span', { style: S.meta }, ` · ${a.garantia.sin_estado} sin estado`) : null) },
        { clave: 'estado', titulo: 'Estado', celda: a => { const ok = a.garantia.validas >= a.garantia.necesarias; const fin = a.garantia.hasta && a.garantia.hasta < hoyISO(); return chipEstado(ok ? 'verde' : fin ? 'rojo' : 'ambar', ok ? 'Cumplida' : fin ? 'Vencida sin cumplir' : 'En curso'); } },
      ],
    }) : vacioLinea('Ninguna alta en curso lleva garantía: la de 2 reuniones en 30 días solo cuenta en quien la firmó.', { icono: 'escudo' }),
    nota('Cómo se cuenta', 'Solo cuentan los acuerdos con la cláusula «Garantía: dos reuniones en 30 días» (leída del PDF de Zoho Sign). Reunión válida = cita del despacho marcada como celebrada en su calendario de GHL desde el encendido; las citas sin estado no cuentan hasta que alguien las marque. Lo vigila Coti.'));
}

function tablaVienen(d) {
  const v = d.previstas || [];
  return h('div', { style: S.pila() },
    v.length ? tablaApilable({
      filas: v,
      columnas: [
        { clave: 'nombre', titulo: 'Despacho', principal: true, celda: x => h('b', { style: S.h3 }, x.nombre) },
        { clave: 'enviado', titulo: 'Contrato enviado', celda: x => fechaLarga(x.enviado) },
        { clave: 'alta', titulo: 'Inicio previsto', celda: x => x.alta_prevista ? h('span', {}, fechaLarga(x.alta_prevista), x.alta_prevista < hoyISO() ? h('span', { style: S.meta }, ' · ya pasado') : null) : 'sin fecha' },
        { clave: 'estado', titulo: 'Estado', celda: () => chipEstado('ambar', 'Enviado, sin firmar') },
      ],
    }) : vacioLinea('No hay contratos enviados sin firmar: todo lo enviado está firmado.', { icono: 'doc' }),
    nota('Por qué no cuentan todavía', ['No son clientes hasta firmar: no cuentan en ninguna cifra ni tienen día 0. Al firmarse en Zoho Sign entran solos en «Altas en curso» con la fecha de inicio del contrato (Asecon: 22-oct).',
      (d.fuera || []).length ? `Fuera de este módulo: ${(d.fuera || []).map(f => `${f.nombre}: ${f.porque}`).join(' · ')}` : null]));
}

// ------------------------------------------------------------------ fechas automáticas (D+N) · se aplicará con escritura
function plantillaDN(ctx, d, alta, acciones) {
  const pd = d.plantilla_dn;
  const objetivo = alta ? [alta] : (d.altas || []).filter(a => a.onboarding);
  const cambios = objetivo.flatMap(a => (a.onboarding?.tareas || []).filter(t => !t.hecha && !t.limite && t.propuesta).map(t => ({ ...t, alta: a })));
  const yaPedido = acciones.some(x => x.tipo === 'fechas_dn' && (!alta || x.cliente_id === alta.cliente_id));
  const reglas = matriz([{ texto: 'Tareas de la plantilla (por su nombre)' }, { texto: 'Día objetivo' }, { texto: 'Fase' }],
    pd.reglas.map(r => [h('span', { style: { color: 'var(--mid)' } }, r.patron.replace(/\\/g, '').replace(/\(\?:?|\)|\[|\]/g, '').replace(/\|/g, ' · ')), chipPropuesta(`día ${r.dia}`), r.fase]));
  return h('div', { style: S.pila() },
    h('div', { class: 'fila', style: { justifyContent: 'space-between', alignItems: 'center' } },
      h('span', { style: { font: 'var(--t-cuerpo)' } }, h('b', {}, `${fmt.num(cambios.length)} tareas sin fecha`), ` recibirían su fecha límite${alta ? ` en ${alta.nombre}` : ` en ${objetivo.length} altas`} (día 0 + N).`),
      yaPedido ? chipEstado('azul', 'Ya en la cola simulada') : botonAccion(ctx, {
        texto: 'Proponer estas fechas', pregunta: `¿Dejar en la cola las ${cambios.length} fechas? No se escribe nada en ClickUp hasta que la app pueda escribir.`, confirmar: 'Sí, a la cola', mini: false,
        accion: { herramienta: 'clickup', tipo: 'fechas_dn', objeto: alta ? alta.onboarding.list_id : 'todas', cliente_id: alta?.cliente_id,
          texto: `Fechas por día de alta para ${cambios.length} tareas sin plazo`, vista_previa: cambios.slice(0, 60).map(t => ({ alta: t.alta.nombre, tarea: t.nombre, fecha: t.propuesta })) } })),
    cambios.length ? recortado(cambios.slice(0, 40), 5, vis => tablaApilable({
      filas: vis,
      columnas: [
        { clave: 'alta', titulo: 'Alta', celda: t => t.alta.nombre },
        { clave: 'nombre', titulo: 'Tarea', principal: true, celda: t => t.url ? h('a', { href: t.url, target: '_blank', rel: 'noopener', style: { ...S.h3, display: 'inline-flex', alignItems: 'center', minHeight: 'var(--s-8)', textDecoration: 'none' } }, t.nombre) : h('b', { style: S.h3 }, t.nombre) },
        { clave: 'propuesta', titulo: 'Fecha propuesta', celda: t => chipPropuesta(`día ${t.dia_objetivo} · ${fechaLarga(t.propuesta)}`) },
      ],
    }), { nombre: cambios.length > 40 ? 'las 40 primeras' : 'todas' }) : vacioLinea('Todas las tareas pendientes tienen fecha: nada que proponer.', { icono: 'ok' }),
    cambios.length > 40 ? h('p', { style: S.meta }, `Y ${fmt.num(cambios.length - 40)} más.`) : null,
    alta ? null : nota('Reglas de la plantilla (día objetivo por tarea)', reglas, { icono: 'cal' }),
    nota('Se aplicará cuando haya escritura', `${pd.nota} Lista de origen: «${pd.lista}».`));
}

// ================================================================== detalle de un alta
function pintarDetalle(cont, ctx, d, id, acciones) {
  const altas = d.altas || [];
  const a = altas.find(x => x.cliente_id === id);
  const volver = h('a', { class: 'bt', href: `#/${ID}` }, icono('volver'), 'Volver a Clientes nuevos');
  if (!a) {
    const c = ctx.clientes.find(x => x.id === id);
    ctx.titulo(c ? c.nombre : 'Clientes nuevos', '');
    cont.append(vacio({ icono: c && !c.detalle ? 'candado' : 'buscar', borde: true, accion: volver,
      titulo: c && !c.detalle ? 'Esta alta no es de tu puesto' : 'Este cliente no está en alta',
      texto: c && !c.detalle ? `La línea de tiempo la ven Agus, Mili, Coti, las jefas y quien lleva el cliente. Si necesitas algo de ${c.nombre}, habla con ${c.responsable}.` : 'Solo salen los clientes del día 0 al 90 desde el alta del contrato.' }));
    return;
  }
  const c = ctx.clientes.find(x => x.id === a.cliente_id) || { nombre: a.nombre };
  ctx.titulo(a.nombre, `Día ${a.dia} de 90 · ${a.plazo.texto}`);
  const visibles = altas.map(x => ({ ...(ctx.clientes.find(y => y.id === x.cliente_id) || {}), id: x.cliente_id, nombre: x.nombre, responsable: `Día ${x.dia} · ${x.plazo.texto}`, salud: undefined }));

  // Barra de contexto: volver + cambiar de alta (el nombre ya está en el título y en la cabecera: no se repite en migas)
  cont.append(h('div', { class: 'fila', style: { justifyContent: 'space-between' } },
    h('a', { class: 'bt', href: `#/${ID}` }, icono('volver', { clase: 's' }), 'Clientes nuevos'),
    selectorCliente({ clientes: visibles, actual: a.cliente_id, etiqueta: 'Cambiar de alta', insignia: x => { const y = altas.find(z => z.cliente_id === x.id); return y ? chipEstado(y.plazo.estado === 'gris' ? 'azul' : y.plazo.estado, `día ${y.dia}`) : null; }, alElegir: x => ctx.navegar(`${ID}/${x.id}`) })));

  // ---- cabecera ----
  const o = a.onboarding;
  const dato = (et, val) => h('div', { style: S.pila('var(--s-1)') }, h('span', { style: S.meta }, et), h('b', { style: S.h3 }, val));
  cont.append(h('section', { class: 'detalle-cab', 'aria-label': 'Cabecera del alta' },
    h('div', { class: 'fila', style: { gap: 'var(--s-4)', alignItems: 'center', flex: '1 1 100%' } },
      logoCliente(c, 'logo-cli xl'),
      h('div', { style: { minWidth: '0', flex: '1 1 260px' } },
        h('h2', {}, a.nombre),
        h('div', { class: 'meta-linea', style: { marginTop: 'var(--s-1)' } },
          h('span', {}, icono('flag'), `Firma ${fechaLarga(a.firma)}`),
          h('span', {}, icono('cal'), `Alta del contrato ${fechaLarga(a.alta)} (día 0)`),
          a.dominio ? h('span', {}, icono('link'), h('a', { href: a.web, target: '_blank', rel: 'noopener', style: { display: 'inline-flex', alignItems: 'center', minHeight: 'var(--s-8)' } }, a.dominio)) : null),
        h('div', { class: 'fila', style: { marginTop: 'var(--s-3)' } },
          chipEstado(a.plazo.estado === 'gris' ? 'azul' : a.plazo.estado, a.plazo.texto),
          chipEstado('azul', `Día ${a.dia} de 90 · semana ${a.semana}`),
          a.garantia ? chipEstado('ambar', 'Con garantía de 2 reuniones') : null,
          a.encargo_art28 ? chipEstado('verde', 'Encargo de tratamiento firmado') : chipEstado('rojo', 'Sin encargo de tratamiento'))),
      h('div', { class: 'fila' },
        o ? h('a', { class: 'bt', href: o.url, target: '_blank', rel: 'noopener' }, icono('check'), 'Abrir en ClickUp') : null,
        (a.meta || a.subcuenta) ? menuAbrir('Abrir en Meta o en GHL', [
          a.meta ? { texto: 'Meta', icono: 'megafono', href: a.meta.prueba } : null,
          a.subcuenta ? { texto: 'GHL', icono: 'base', href: ghlUrl(a.subcuenta.loc) } : null,
        ].filter(Boolean)) : null,
        h('a', { class: 'bt', href: `#/ficha/${a.cliente_id}` }, icono('cli'), 'Ficha del cliente'))),
    h('div', { style: { ...S.rejilla(150, 'var(--s-3) var(--s-5)'), flex: '1 1 100%', borderTop: 'var(--borde-suave)', paddingTop: 'var(--s-3)' } },
      dato('Dueño (técnico de altas)', `${a.dueno.nombre} · hasta el día 90`),
      dato('Vigilante', a.vigilante.nombre),
      dato('Account', nombrePersona(a.account) || (a.sin_account ? a.sin_account.charAt(0).toUpperCase() + a.sin_account.slice(1) : 'Sin asignar')),
      dato('Trafficker', nombrePersona(a.trafficker) || 'Sin asignar'),
      dato('CRM', nombrePersona(a.crm) || 'Sin asignar'),
      dato('Encendido', a.plazo.dia_encendido !== null && a.plazo.dia_encendido !== undefined ? `Día ${a.plazo.dia_encendido}` : `Objetivo ${fechaLarga(a.plazo.objetivo)} · límite ${fechaLarga(a.plazo.limite)}`))));

  // ---- Ronda U (#14): «Lo que falta» arriba, con su verbo en cada fila (Dado / Hecho, al primer clic y con Deshacer) y
  //      «Pedir lo que falta en un correo» en su barra. Antes las casillas estaban a 1.941 px y el correo a 2.300 px. ----
  const falta = panelLoQueFalta(ctx, a, acciones);
  if (matchMedia('(max-width: 640px)').matches) cont.querySelector('section.detalle-cab')?.before(falta);   // en el móvil, antes de la cabecera
  else cont.append(falta);

  // ---- lo que pide atención, arriba (guía 3.6) ----
  const escaladas = new Set(acciones.filter(x => x.tipo === 'escalar').map(x => x.objeto));
  const itemAlerta = x => {
    const objeto = x.tarea || `${a.cliente_id}:${x.tipo}`;
    return {
      estado: x.estado, icono: ICONO_ALERTA[x.tipo] || 'alert', motivo: TEXTO_ALERTA[x.tipo] || x.tipo, detalle: `${x.texto}${escaladas.has(objeto) ? ' · ya escalado (simulado)' : ''}`,
      botones: [
        x.url ? btMini({ href: x.url, target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir en ClickUp') : null,
        x.estado === 'rojo' && !escaladas.has(objeto) ? botonAccion(ctx, { texto: 'Escalar', pregunta: '¿Escalar a Mili?', confirmar: 'Sí, escalar',
          accion: { herramienta: 'app', tipo: 'escalar', objeto, cliente_id: a.cliente_id, texto: `${a.nombre}: ${x.texto}`, vista_previa: { a: ['Mili'], motivo: TEXTO_ALERTA[x.tipo], dia: a.dia } } }) : null,
      ],
    };
  };
  const alertas = a.alertas.slice(0, 12);
  cont.append(panel({ titulo: 'Qué pide atención', icono: 'alert', sub: 'Tareas vencidas o paradas, bloqueos, plazo de encendido y lo que marca el equipo' },
    alertas.length ? recortado(alertas, 4, vis => listaLoPrimero(vis.map(itemAlerta), { subir: false }), { nombre: 'todas' })
      : h('div', { class: 'cuerpo' }, vacioLinea('Esta alta no tiene alertas: en plazo, sin tareas vencidas ni bloqueos.', { icono: 'ok' })),
    a.alertas.length > 12 ? h('p', { class: 'cuerpo', style: { ...S.meta, margin: '0' } }, `Y ${a.alertas.length - 12} más en la línea de tiempo.`) : null));

  // ---- hitos de la firma al día 90 ----
  const sigId = a.siguiente?.id;
  cont.append(panel({ titulo: 'Hitos de la firma al día 90', icono: 'flag', sub: 'Quién lo hace, fecha objetivo desde el día 0 y la prueba de cada uno. Pasa el ratón para ver la prueba.' },
    h('div', { class: 'cuerpo' }, h('ol', { style: { ...S.rejilla(112, 'var(--s-2)'), listStyle: 'none', margin: '0', padding: '0' } }, a.hitos.map(x => {
      const [est, txt] = ESTADOS_HITO[x.estado] || ['gris', x.estado];
      const cuando = x.fecha ? fechaLarga(x.fecha) : x.objetivo ? `objetivo ${fechaLarga(x.objetivo)}` : 'sin fecha';
      const sig = x.id === sigId;
      return h('li', { title: `${x.nombre}: ${txt}. ${x.prueba || ''} (${x.fuente})`, 'aria-current': sig ? 'step' : null,
        style: { display: 'grid', gap: 'var(--s-1)', justifyItems: 'center', alignContent: 'start', textAlign: 'center', padding: 'var(--s-2) var(--s-1)', minWidth: '0', borderRadius: 'var(--r-m)', background: sig ? 'var(--accent-soft)' : null } },
        h('span', { class: `ico-c ${est === 'azul' ? '' : est}`.trim(), 'aria-hidden': 'true', style: sig ? { boxShadow: '0 0 0 2px var(--accent)' } : null }, icono(ICONO_HITO[x.id] || 'flag')),
        h('b', { style: { ...S.h3, overflowWrap: 'anywhere' } }, x.nombre),
        h('span', { style: S.metaMid }, x.estado === 'no_aplica' ? 'No aplica' : `${txt} · ${cuando}`),
        h('span', { style: S.meta }, x.quien));
    })))));

  cont.append(panelEquipo(ctx, d, a, acciones));

  // ---- cifras del alta ----
  const leadH = a.hitos.find(x => x.id === 'primer_lead');
  const fich = [
    tile({ icono: 'rocket', etiqueta: 'Encendido', valor: a.plazo.dia_encendido !== null && a.plazo.dia_encendido !== undefined ? `Día ${a.plazo.dia_encendido}` : null,
      unidad: a.plazo.dia_encendido === null || a.plazo.dia_encendido === undefined ? '' : `objetivo ${d.reglas.encendido_objetivo}`, estado: a.plazo.estado === 'gris' ? '' : a.plazo.estado,
      contexto: a.plazo.dia_encendido === null || a.plazo.dia_encendido === undefined ? `Sin encender · objetivo ${fechaLarga(a.plazo.objetivo)}, límite ${fechaLarga(a.plazo.limite)}` : a.plazo.texto, medible: 'hoy', frescura: fres(d.fuentes.meta, 'Meta') }),
    tile({ icono: 'check', etiqueta: 'Avance del arranque', valor: o ? fmt.pct(o.pct) : null, unidad: o ? `${o.hechas} de ${o.n}` : '', estado: !o ? 'rojo' : '',
      contexto: o ? `${o.sin_plazo} sin plazo · ${o.no_avanza} no avanzan` : 'Sin lista de arranque en ClickUp', medible: 'hoy', frescura: fres(d.fuentes.clickup, 'ClickUp'), ir: 'Ver la línea de tiempo', alPulsar: () => document.getElementById('m12-tiempo')?.scrollIntoView({ behavior: 'smooth' }) }),
    tile({ icono: 'cal', etiqueta: 'Tareas vencidas', valor: o ? o.vencidas : null, estado: !o ? 'gris' : o.vencidas ? 'rojo' : 'verde', contexto: o ? `${o.bloqueadas} bloqueadas` : 'Sin dato: no hay lista de tareas', medible: 'hoy', frescura: fres(d.fuentes.clickup, 'ClickUp') }),
    tile({ icono: 'target', etiqueta: 'Primer lead', valor: leadH?.fecha ? fechaLarga(leadH.fecha) : null, unidad: leadH?.dias_desde_encendido !== null && leadH?.dias_desde_encendido !== undefined ? `${leadH.dias_desde_encendido} días tras encender` : '',
      estado: leadH?.dias_desde_encendido === null || leadH?.dias_desde_encendido === undefined ? 'gris' : leadH.dias_desde_encendido <= 3 ? 'verde' : leadH.dias_desde_encendido <= 7 ? 'ambar' : 'rojo',
      contexto: leadH?.fecha ? 'Propuesta: verde hasta 3 días · ámbar 4-7 · rojo más de 7' : 'Sin dato: todavía no hay lead desde el encendido', medible: 'hoy', frescura: fres(d.fuentes.meta, 'Meta') }),
  ];
  if (a.meta && a.meta.leads_desde_alta !== undefined) {
    fich.push(tile({ icono: 'megafono', etiqueta: 'Desde el alta en Meta', valor: a.meta.gasto_desde_alta !== undefined ? fmt.eur(a.meta.gasto_desde_alta) : verLeads(a.meta.leads_desde_alta),
      unidad: a.meta.gasto_desde_alta !== undefined ? verLeads(a.meta.leads_desde_alta) : '', estado: '', contexto: `${a.meta.nombre} · ${a.meta.estado_cuenta || `cuenta ${a.meta.estado}`}${a.campana ? ` · ${a.campana.texto}` : ''}`, medible: 'hoy', frescura: fres(d.fuentes.meta, 'Meta'), href: a.meta.prueba, ir: 'Abrir en Meta' }));
  }
  cont.append(tiles(fich));

  // ---- accesos y casillas ----
  cont.append(h('div', { class: 'dos' },
    panel({ titulo: 'Accesos', icono: 'key', sub: 'Dado / falta / quién lo tiene / desde cuándo. Nunca la clave.' },
      h('div', { class: 'cuerpo' }, listaConIcono(a.accesos.map(x => ({
        icono: x.icono, estado: x.estado === 'dado' ? 'verde' : x.estado === 'falta' ? 'rojo' : 'gris',
        texto: (() => { const t = `${x.recurso} · ${x.estado === 'dado' ? 'dado' : x.estado === 'falta' ? 'falta' : 'sin registro'}`; const url = x.tarea || (x.icono === 'base' && a.subcuenta ? ghlUrl(a.subcuenta.loc) : null);
          return url ? h('a', { href: url, target: '_blank', rel: 'noopener', title: t, style: { display: 'inline-flex', alignItems: 'center', minHeight: 'var(--s-8)', maxWidth: '100%' } }, h('span', { style: S.corte }, t)) : t; })(),
        extra: x.estado === 'falta' ? `${x.quien} · desde ${fechaLarga(x.desde)}` : x.quien,
      }))),
      a.accesos.some(x => x.estado === 'falta') ? h('div', { class: 'fila', style: { marginTop: 'var(--s-3)' } },
        botonAccion(ctx, { texto: 'Pedir los accesos en un solo correo', mini: false, pregunta: a.encargo_art28 ? '¿Dejar el correo único de accesos en la cola? Se enviará por Desk cuando la app pueda escribir.' : 'Sin encargo de tratamiento no se piden accesos.',
          confirmar: 'Sí, a la cola', accion: { herramienta: 'desk', tipo: 'pedir_accesos', objeto: a.cliente_id, cliente_id: a.cliente_id,
            texto: `Correo único de accesos para ${a.nombre}: ${a.accesos.filter(x => x.estado === 'falta').map(x => x.recurso).join(', ')}`,
            vista_previa: { asunto: `${a.nombre} · accesos para arrancar`, pide: a.accesos.filter(x => x.estado !== 'dado').map(x => x.recurso), cierre_ronda: masDias(a.alta, 7), regla: 'Si no contesta en 48 h, se llama (no otro correo).' } } })) : null)),
    panel({ titulo: 'Casillas técnicas', icono: 'check', sub: 'Píxel, dominio, DNS, WhatsApp, calendario y subcuenta' },
      h('div', { class: 'cuerpo' }, recortado(a.casillas, 4, vis => h('div', { style: S.rejilla(232) }, vis.map(x => h('div', { style: { display: 'grid', gridTemplateColumns: 'auto minmax(0, 1fr)', gap: 'var(--s-1) var(--s-3)', alignItems: 'start', border: 'var(--borde)', borderRadius: 'var(--r-m)', padding: 'var(--s-3)', background: 'var(--card)', minWidth: '0' } },
        h('span', { class: `ico-c s ${x.estado}`, style: { gridRow: 'span 2' } }, icono(x.estado === 'verde' ? 'ok' : x.estado === 'rojo' ? 'cerrar' : x.estado === 'ambar' ? 'alert' : 'info')),
        h('b', { style: S.h3 }, x.texto), h('span', { style: { ...S.meta, overflowWrap: 'anywhere' } }, `${x.detalle} · ${x.fuente}`)))), { nombre: 'todas las casillas' })),
      h('div', { class: 'cuerpo fila', style: { paddingTop: '0' } },
        botonDeshacer({ texto: 'Marcar «Landing y posts revisados»', icono: 'ok', hecho: 'Casilla marcada', soloLectura: ctx.soloLectura,   // ronda U (#4): interna, con Deshacer
          alHacer: async () => { const r = await ctx.accion({ herramienta: 'app', tipo: 'casilla', objeto: `${a.cliente_id}:landing_posts`, cliente_id: a.cliente_id, texto: `Casilla «Landing y posts revisados» de ${a.nombre}`, vista_previa: { casilla: 'landing_posts', prueba: 'enlace a la landing y a los posts revisados' } }); return `En la cola (n.º ${r?.id ?? '—'}) · queda en el rastro`; } }),
        a.dominio ? btMini({ href: `https://mxtoolbox.com/SuperTool.aspx?action=dmarc%3a${encodeURIComponent(a.dominio)}`, target: '_blank', rel: 'noopener' }, icono('ext'), 'Comprobar DNS fuera') : null))));

  // ---- línea de tiempo por semanas ----
  cont.append(lineaSemanas(ctx, d, a));

  // ---- Meta, garantía y objetivo del alta ----
  const fila2 = [];
  if (a.meta && a.meta.serie_gasto?.length) {
    const serie = a.meta.serie_gasto;
    const conGasto = serie[0].gasto !== undefined;
    fila2.push(panel({ titulo: conGasto ? 'Gasto y leads diarios en Meta desde el alta' : 'Leads diarios en Meta desde el alta', icono: 'grafico', sub: 'Del número a la prueba: «Abrir en Meta».' },
      h('div', { class: 'cuerpo' }, conGasto
        ? grafico({ x: serie.map(x => x.d), alto: 160, barras: { y: serie.map(x => x.gasto || 0), nombre: 'Gasto (barras)', formato: v => fmt.eur(v), escalaPropia: true },
          series: [{ nombre: 'Leads', y: serie.map(x => x.leads || 0) }], leyenda: true, vacio: 'Sin gasto ni leads desde el alta' })
        : grafico({ x: serie.map(x => x.d), alto: 160, tipo: 'barras', series: [{ nombre: 'Leads', y: serie.map(x => x.leads || 0) }], vacio: 'Sin leads desde el alta' }))));
  }
  if (a.garantia) {
    const g = a.garantia;
    fila2.push(panel({ titulo: 'Garantía: 2 reuniones en 30 días', icono: 'escudo', sub: 'Desde el encendido, en el calendario de GHL del despacho. La vigila Coti.' },
      h('div', { class: 'cuerpo', style: S.pila() }, tiles([
        tile({ icono: 'users', etiqueta: 'Reuniones celebradas', valor: `${g.validas} de ${g.necesarias}`, estado: g.validas >= g.necesarias ? 'verde' : (g.hasta && g.hasta < hoyISO()) ? 'rojo' : 'ambar',
          contexto: g.desde ? `Ventana ${fechaLarga(g.desde)} → ${fechaLarga(g.hasta)} · ${g.citas_en_ventana} citas, ${g.sin_estado} sin estado` : 'Empieza a contar con el encendido', medible: 'hoy', frescura: fres(d.fuentes.ghl, 'GHL') }),
      ]), g.literal ? h('p', { style: S.lectura }, `«${g.literal}»`) : null)));
  }
  fila2.push(objetivoAlta(ctx, a, acciones));
  cont.append(h('div', { style: { ...S.rejilla(380, 'var(--s-5)'), alignItems: 'start' } }, fila2));   // 1 a 3 paneles

  cont.append(panel({ titulo: 'Fechas automáticas de su lista', icono: 'cal', sub: 'Día 0 + N para las tareas sin fecha. Se aplicará cuando la app pueda escribir en ClickUp.' },
    h('div', { class: 'cuerpo' }, o ? plantillaDN(ctx, d, a, acciones) : vacioLinea(`No hay lista de arranque: primero hay que crear «Onboarding — [${a.nombre}]» desde la plantilla. Cuando la app pueda escribir, la creará con las fechas ya puestas.`, { icono: 'capas', quien: 'Agus' }))));
  cont.append(avisoDatos(d));
}

const slug = t => String(t || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '').slice(0, 40);
function panelLoQueFalta(ctx, a, acciones) {
  const puede = ctx.persona.puestos.some(p => PUEDEN_EDITAR.includes(p)) && !ctx.soloLectura;
  const marcadas = new Map();
  for (const x of acciones) if (x.tipo === 'casilla' && x.cliente_id === a.cliente_id) marcadas.set(String(x.objeto), x);
  const filas = [
    ...a.accesos.filter(x => x.estado !== 'dado').map(x => ({ obj: `${a.cliente_id}:acceso:${slug(x.recurso)}`, icono: x.icono || 'key', texto: `Acceso · ${x.recurso}`, extra: `${x.estado === 'falta' ? 'Falta' : 'Sin registro'}${x.quien ? ` · ${x.quien}` : ''}${x.desde ? ` · desde ${fechaLarga(x.desde)}` : ''}`, estado: x.estado === 'falta' ? 'rojo' : 'gris', verbo: 'Dado', url: x.tarea })),
    ...a.casillas.filter(x => x.estado !== 'verde' && x.medible !== 'no').map(x => ({ obj: `${a.cliente_id}:${x.id}`, icono: 'check', texto: x.texto, extra: `${x.detalle} · ${x.fuente}`, estado: x.estado === 'rojo' ? 'rojo' : x.estado === 'ambar' ? 'ambar' : 'gris', verbo: 'Hecho' })),
  ];
  const fila = it => {
    const m = marcadas.get(it.obj);
    const accion = m ? chipEstado('verde', `${it.verbo} · ${ctx.nombre ? ctx.nombre(m.quien) : m.quien} · se comprueba con el dato`)
      : puede ? botonDeshacer({ texto: it.verbo, icono: 'ok', hecho: it.verbo, atajo: 'e',
        alHacer: async () => { const r = await ctx.accion({ herramienta: 'app', tipo: 'casilla', objeto: it.obj, cliente_id: a.cliente_id, texto: `${a.nombre} · ${it.texto}: ${it.verbo.toLowerCase()}`, vista_previa: { casilla: it.obj.split(':').slice(1).join(':'), marca: it.verbo, comprobar: 'con la lectura siguiente de la fuente' } });
          marcadas.set(it.obj, { quien: ctx.real.id, id: r?.id }); return `${it.verbo} · queda en el rastro`; } }) : null;
    return h('li', { 'data-fila': '', style: { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 'var(--s-2) var(--s-3)', padding: 'var(--s-2) 0', borderTop: 'var(--borde-suave)', minWidth: '0' } },
      h('span', { class: `ico-c s ${m ? 'verde' : it.estado}`, 'aria-hidden': 'true' }, icono(it.icono)),
      h('span', { style: { flex: '1 1 220px', minWidth: '0', display: 'grid', gap: '2px' } }, h('b', { style: S.h3 }, it.texto), h('span', { style: { ...S.meta, overflowWrap: 'anywhere' } }, it.extra)),
      h('span', { class: 'fila', style: { gap: 'var(--s-1)' } }, it.url ? btMini({ href: it.url, target: '_blank', rel: 'noopener' }, icono('ext'), 'ClickUp') : null, accion));
  };
  const faltanAcc = a.accesos.filter(x => x.estado === 'falta');
  const pedir = faltanAcc.length ? botonAccion(ctx, { texto: 'Pedir lo que falta en un correo', mini: true, pregunta: a.encargo_art28 ? '¿Dejar el correo único de accesos en la cola? Se enviará por Desk cuando la app pueda escribir.' : 'Sin encargo de tratamiento no se piden accesos.',
    confirmar: 'Sí, a la cola', accion: { herramienta: 'desk', tipo: 'pedir_accesos', objeto: a.cliente_id, cliente_id: a.cliente_id,
      texto: `Correo único de accesos para ${a.nombre}: ${faltanAcc.map(x => x.recurso).join(', ')}`,
      vista_previa: { asunto: `${a.nombre} · accesos para arrancar`, pide: faltanAcc.map(x => x.recurso), cierre_ronda: masDias(a.alta, 7), regla: 'Si no contesta en 48 h, se llama (no otro correo).' } } }) : null;
  return panel({ titulo: 'Lo que falta', icono: 'check', id: 'm12-falta', sub: filas.length ? `${fmt.plural(filas.length, 'paso', 'pasos')} entre accesos y casillas técnicas. «Dado» y «Hecho» se deshacen en 8 s; el dato siguiente lo comprueba.` : 'Accesos y casillas técnicas al día.',
    acciones: pedir },
  h('div', { class: 'cuerpo' }, filas.length ? h('ul', { style: { listStyle: 'none', margin: '0', padding: '0' } }, [...filas].sort((x, y) => (marcadas.has(x.obj) ? 1 : 0) - (marcadas.has(y.obj) ? 1 : 0)).map(fila)) : vacioLinea('Nada pendiente: accesos dados y casillas en verde.', { icono: 'ok' })));
}

function lineaSemanas(ctx, d, a) {
  const o = a.onboarding;
  if (!o) {
    const vencido = (a.horas_desde_firma || 0) > d.reglas.sin_tareas_horas;
    return panel({ titulo: 'Línea de tiempo por semanas', icono: 'hist', id: 'm12-tiempo' },
      h('div', { class: 'cuerpo' }, vacio({ icono: 'capas', tono: vencido ? 'aviso' : 'neutro', borde: true,
        titulo: vencido ? `Sin tareas a las ${Math.round(a.horas_desde_firma)} h de la firma` : 'Todavía sin lista de arranque',
        texto: `No hay lista «Onboarding — [${a.nombre}]» en ClickUp${vencido ? `: el plazo de ${d.reglas.sin_tareas_horas} h ya ha pasado` : ''}. Se crea desde la plantilla «Onboarding — [PLANTILLA]» y, cuando la app pueda escribir, con las fechas puestas solas (día 0 + N).`,
        quien: 'Agus', accion: botonAccion(ctx, { texto: 'Pedir la lista de arranque', mini: false, pregunta: '¿Dejar el encargo en la cola? Cuando la app pueda escribir, la creará desde la plantilla.', confirmar: 'Sí, a la cola',
          accion: { herramienta: 'clickup', tipo: 'crear_lista_onboarding', objeto: a.cliente_id, cliente_id: a.cliente_id, texto: `Crear «Onboarding — [${a.nombre}]» desde la plantilla con fechas D+N`, vista_previa: { plantilla: d.plantilla_dn.list_id, dia0: a.alta } } }) })));
  }
  const semanaHoy = Math.floor(a.dia / 7);
  const porSemana = new Map();
  const sinPlazo = [];
  for (const t of o.tareas) {
    const tieneReal = !!t.limite;
    const s = t.semana;
    if (s === null || s === undefined || (!tieneReal && t.hecha)) { (t.hecha ? (porSemana.get('hechas') || porSemana.set('hechas', []).get('hechas')) : sinPlazo).push(t); continue; }
    const k = Math.max(0, Math.min(12, s));
    if (!porSemana.has(k)) porSemana.set(k, []);
    porSemana.get(k).push(t);
  }
  // Las 13 semanas con el motor único de gráficos: barras = tareas de la semana; líneas = hechas y vencidas.
  const semanasN = [...Array(13).keys()];
  const enSemana = i => porSemana.get(i) || [];
  const graf = grafico({
    x: semanasN.map(i => `S${i + 1}`), formatoX: v => v, alto: 160, leyenda: true,
    barras: { y: semanasN.map(i => enSemana(i).length), nombre: 'Tareas de la semana' },
    series: [
      { nombre: 'Hechas', y: semanasN.map(i => enSemana(i).filter(t => t.hecha).length), color: 'var(--good)' },
      { nombre: 'Vencidas', y: semanasN.map(i => enSemana(i).filter(t => t.alertas.includes('vencida')).length), color: 'var(--bad)' },
    ],
    etiquetaUltimo: false, vacio: 'Ninguna tarea con semana prevista',
  });
  const tareaLi = t => {
    const est = t.hecha ? 'verde' : t.alertas.includes('vencida') || t.alertas.includes('bloqueo_5d') ? 'rojo' : t.estado === 'bloqueado' || t.alertas.includes('no_avanza') ? 'ambar' : 'gris';
    const nombre = { display: 'block', ...S.corte, color: t.hecha ? 'var(--dim)' : 'var(--ink)', textDecoration: t.hecha ? 'line-through' : 'none', font: 'var(--t-h3)' };
    return h('li', { style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-2) var(--s-3)', alignItems: 'center', padding: 'var(--s-2)', borderTop: 'var(--borde-suave)', minWidth: '0' } },
      h('span', { class: `ico-c s ${est}`, 'aria-hidden': 'true' }, icono(t.hecha ? 'ok' : est === 'rojo' ? 'alert' : est === 'ambar' ? 'clock' : 'info')),
      h('span', { style: { flex: '1 1 220px', minWidth: '0' } },
        t.url ? h('a', { href: t.url, target: '_blank', rel: 'noopener', title: t.nombre, style: { ...nombre, lineHeight: 'var(--s-8)' } }, t.nombre) : h('span', { title: t.nombre, style: nombre }, t.nombre),
        h('span', { style: { display: 'block', ...S.meta, overflowWrap: 'anywhere' } }, [t.estado, t.asignados.length ? t.asignados.join(', ') : 'sin asignar', t.fase].join(' · '))),
      h('span', { style: { display: 'flex', gap: 'var(--s-2)', flexWrap: 'wrap', alignItems: 'center' } },
        t.alertas.includes('vencida') ? chipEstado('rojo', `venció ${fechaLarga(t.limite)}`) : t.limite ? chipEstado(t.hecha ? 'verde' : 'gris', `límite ${fechaLarga(t.limite)}`) : null,
        !t.limite && t.propuesta && !t.hecha ? chipPropuesta(`propuesta ${fechaLarga(t.propuesta)}`, 'Fecha propuesta por la plantilla (día 0 + N): se aplicará cuando la app pueda escribir') : null,
        t.alertas.includes('no_avanza') ? chipEstado('ambar', 'no avanza') : null,
        t.estado === 'bloqueado' ? chipEstado(t.alertas.includes('bloqueo_5d') ? 'rojo' : 'ambar', `bloqueada${t.dias_bloqueada ? ` ${fmt.num(t.dias_bloqueada)} d` : ''}`) : null));
  };
  const bloque = (titulo, sub, ts, esHoy) => h('section', { style: { ...S.pila('var(--s-2)'), borderTop: 'var(--borde-suave)', paddingTop: 'var(--s-3)' } },
    h('header', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 'var(--s-1) var(--s-3)', flexWrap: 'wrap' } },
      h('b', { style: { ...S.h3, color: esHoy ? 'var(--accent-ink)' : 'var(--ink)' } }, titulo), h('span', { style: S.meta }, sub)),
    recortado(ts.sort((x, y) => (x.hecha - y.hecha) || ((y.alertas.length) - (x.alertas.length)) || String(x.limite || x.propuesta).localeCompare(String(y.limite || y.propuesta))), 4,
      vis => h('ul', { style: { listStyle: 'none', margin: '0', padding: '0', display: 'grid' } }, vis.map(tareaLi)), { nombre: 'las de esta semana' }));
  const semanas = [...porSemana.keys()].filter(k => k !== 'hechas').sort((x, y) => x - y);
  const filtro = chipsFiltro({ etiqueta: 'Ver', clave: 'nuevos.tiempo', opciones: [
    { valor: 'pend', texto: 'Pendientes', cuenta: o.tareas.filter(t => !t.hecha).length },
    { valor: '', texto: 'Todas', cuenta: o.tareas.length },
    { valor: 'alerta', texto: 'Con alerta', icono: 'alert', cuenta: o.tareas.filter(t => t.alertas.length).length, cuentaEstado: 'rojo' },
  ], alCambiar: () => pintar() });
  const caja = h('div', { style: S.pila('var(--s-4)') });
  const pintar = () => {
    const v = filtro.valor();
    const pasa = t => v === '' ? true : v === 'pend' ? !t.hecha : t.alertas.length > 0;
    const hijos = [];
    for (const k of semanas) {
      const ts = porSemana.get(k).filter(pasa);
      if (!ts.length) continue;
      const ini = masDias(a.alta, k * 7 - (new Date(a.alta + 'T12:00:00').getDay() + 6) % 7);
      hijos.push(bloque(`Semana ${k + 1}${k === semanaHoy ? ' · esta semana' : ''}`, `${fechaLarga(ini)} – ${fechaLarga(masDias(ini, 6))} · días ${Math.max(0, k * 7)}-${k * 7 + 6}`, ts, k === semanaHoy));
    }
    const sp = sinPlazo.filter(pasa);
    if (sp.length) hijos.push(bloque('Sin plazo', 'Sin fecha límite ni propuesta: salen en gris (no generan alerta)', sp, false));
    const hechasSin = (porSemana.get('hechas') || []).filter(pasa);
    if (hechasSin.length && v !== 'pend' && v !== 'alerta') hijos.push(bloque('Hechas sin fecha', `${hechasSin.length} tareas completadas que nunca tuvieron fecha`, hechasSin, false));
    caja.replaceChildren(hijos.length ? recortado(hijos, 3, vis => vis, { nombre: 'todas las semanas', menos: 'Ver solo las primeras' }) : vacioLinea('Nada en este filtro. Prueba con «Todas».', { icono: 'ok' }));
  };
  pintar();
  return panel({ titulo: 'Línea de tiempo por semanas', icono: 'hist', id: 'm12-tiempo', sub: `Cada tarea en su semana prevista: la fecha límite de ClickUp o, si no tiene, la propuesta día 0 + N (borde discontinuo). Hoy es la semana ${semanaHoy + 1}.` },
    h('div', { class: 'cuerpo', style: S.pila() }, graf, filtro, caja));
}

function panelEquipo(ctx, d, a, acciones) {
  const eq = a.equipo;
  const puede = ctx.persona.puestos.some(p => PUEDEN_EDITAR.includes(p));
  const difs = a.diferencias || [];
  const cita = (titulo, texto) => h('blockquote', { style: { margin: '0', padding: 'var(--s-2) var(--s-3)', borderLeft: '3px solid var(--accent-2)', background: 'var(--card-2)', borderRadius: 'var(--r-s)', font: 'var(--t-cuerpo)' } },
    h('b', { style: { display: 'block', ...S.meta, fontWeight: 600, marginBottom: 'var(--s-1)' } }, titulo), texto || 'sin dato');
  const izq = h('div', { style: S.pila() },
    eq ? [
      h('div', { class: 'fila' },
        eq.urgente ? chipEstado('rojo', 'Prioritaria') : null,
        chipEstado(eq.taller?.estado === 'hecho' ? 'verde' : ['agendado', 'segunda_sesion'].includes(eq.taller?.estado) ? 'azul' : 'ambar', `Taller: ${TXT_T[eq.taller?.estado] || 'sin dato'}${eq.taller?.fecha ? ' · ' + fechaHora(eq.taller.fecha) : ''}`),
        chipEstado(eq.config_basicas?.estado === 'hecho' ? 'verde' : eq.config_basicas?.estado === 'agendada' ? 'azul' : eq.config_basicas?.estado === 'sin_agendar' ? 'rojo' : 'ambar', `Configuración: ${TXT_C[eq.config_basicas?.estado] || 'sin dato'}${eq.config_basicas?.fecha ? ' · ' + fechaHora(eq.config_basicas.fecha) : ''}`)),
      eq.config_basicas?.nota ? h('p', { style: S.lectura }, `Configuración: ${eq.config_basicas.nota}`) : null,
      cita('Estado', eq.estado),
      cita('Próximo paso', eq.proximo_paso),
      h('span', { style: S.meta }, `${eq.autor || 'equipo de arranque'} · ${fechaHora(eq.actualizado)} · ${eq.origen || ''}`),
    ] : vacioLinea('El equipo no ha declarado el estado de esta alta. Coti, Agus o Valeria lo dejan con «Actualizar el estado del equipo».', { icono: 'compartir', quien: 'Agus' }));
  const der = h('div', { style: S.pila('var(--s-1)') },
    h('b', { style: S.h3 }, 'Cruce con lo que ve la app'),
    difs.length ? difs.map(x => h('div', { style: { display: 'flex', gap: 'var(--s-3)', alignItems: 'flex-start', padding: 'var(--s-2) 0', borderTop: 'var(--borde-suave)', font: 'var(--t-cuerpo)' } },
      punto(x.estado === 'verde' ? 'verde' : x.estado, x.estado === 'verde' ? 'Coincide' : 'Diferencia'),
      h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-2) var(--s-3)', flex: '1 1 0', minWidth: '0' } },
        h('span', { style: { flex: '1 1 140px', minWidth: '0', overflowWrap: 'anywhere' } }, h('small', { style: { display: 'block', ...S.meta, fontWeight: 600 } }, 'El equipo dice'), x.equipo),
        h('span', { style: { flex: '1 1 140px', minWidth: '0', overflowWrap: 'anywhere' } }, h('small', { style: { display: 'block', ...S.meta, fontWeight: 600 } }, 'La app ve'), x.app)))) : h('p', { style: S.lectura }, 'Sin diferencias entre lo declarado y las herramientas.'));
  const cuerpo = [h('div', { class: 'cuerpo', style: { ...S.rejilla(300, 'var(--s-5)'), alignItems: 'start' } }, izq, der)];
  if (puede) cuerpo.push(h('details', { class: 'cuerpo', style: { paddingTop: '0' } },
    h('summary', { style: { cursor: 'pointer', font: 'var(--t-h3)', color: 'var(--accent)', minHeight: 'var(--s-8)', display: 'flex', alignItems: 'center', gap: 'var(--s-2)', width: 'max-content', maxWidth: '100%' } }, icono('editar', { clase: 's' }), 'Actualizar el estado del equipo'),
    formularioEquipo(ctx, a)));
  return panel({ titulo: 'Estado del equipo de arranque', icono: 'users', sub: 'Lo que declaran Coti, Valeria y Agus, con autor y fecha, frente a lo que leen ClickUp, GHL, Meta y Sign.' }, cuerpo);
}

/** Campo común con id fijo para leerlo al guardar; desactivado si la persona solo puede leer. */
function campo(ctx, id, o) {
  const c = campoTexto(o);
  const el = c.querySelector('input, textarea');
  el.id = `m12-${id}`; c.setAttribute('for', el.id);
  if (ctx.soloLectura) el.disabled = true;
  return c;
}
function formularioEquipo(ctx, a) {
  const eq = a.equipo || {};
  const fechaVal = f => (f || '').slice(0, 10);
  // Opciones cerradas como chips (sin desplegable nativo); el valor se lee con .valor()
  const elegir = (etiqueta, opciones, valor) => h('div', { style: S.pila('var(--s-1)') }, h('span', { class: 'campo-et' }, etiqueta),
    chipsFiltro({ etiqueta: '', opciones: opciones.map(([v, t]) => ({ valor: v, texto: t })), valor }));
  const tEst = elegir('Taller de oferta', [['hecho', 'Hecho'], ['agendado', 'Agendado'], ['segunda_sesion', '2.ª sesión'], ['sin_agendar', 'Sin agendar']], eq.taller?.estado || 'sin_agendar');
  const cEst = elegir('Configuración básica', [['hecho', 'Hecha'], ['agendada', 'Agendada'], ['sin_agendar', 'Sin agendar']], eq.config_basicas?.estado === 'pendiente' ? 'sin_agendar' : (eq.config_basicas?.estado || 'sin_agendar'));
  const urg = h('input', { id: 'm12-e-urg', type: 'checkbox', checked: eq.urgente || null, disabled: ctx.soloLectura || null });
  return h('div', { style: { ...S.pila(), marginTop: 'var(--s-3)' } },
    h('div', { style: S.rejilla(200) }, tEst, campo(ctx, 't-fecha', { etiqueta: 'Fecha del taller', tipo: 'date', valor: fechaVal(eq.taller?.fecha) }),
      cEst, campo(ctx, 'c-fecha', { etiqueta: 'Fecha de la configuración', tipo: 'date', valor: fechaVal(eq.config_basicas?.fecha) })),
    campo(ctx, 'e-est', { etiqueta: 'Estado', filas: 3, valor: eq.estado || '' }),
    campo(ctx, 'e-prox', { etiqueta: 'Próximo paso', filas: 3, valor: eq.proximo_paso || '' }),
    h('label', { style: { display: 'inline-flex', gap: 'var(--s-2)', alignItems: 'center', minHeight: 'var(--s-8)', font: 'var(--t-h3)', width: 'max-content' } }, urg, 'Prioritaria'),
    h('div', { class: 'fila' }, botonConfirmar({
      texto: 'Guardar estado', pregunta: '¿Guardar el estado de esta alta? Queda con tu nombre y la hora en la cola simulada y en el rastro.', confirmar: 'Sí, guardar', soloLectura: ctx.soloLectura,
      alConfirmar: async () => {
        const v = id => document.getElementById(`m12-${id}`);
        const nuevo = {
          taller: { estado: tEst.querySelector('.chips-f').valor(), fecha: v('t-fecha').value || null },
          config_basicas: { estado: cEst.querySelector('.chips-f').valor(), fecha: v('c-fecha').value || null },
          estado: v('e-est').value.trim(), proximo_paso: v('e-prox').value.trim(), urgente: urg.checked,
        };
        if (!nuevo.estado && !nuevo.proximo_paso) throw new Error('Escribe al menos el estado o el próximo paso.');
        const r = await ctx.accion({ herramienta: 'app', tipo: 'estado_alta', objeto: a.cliente_id, cliente_id: a.cliente_id, texto: `Estado del equipo de arranque de ${a.nombre}`, vista_previa: nuevo });
        return r?.local ? 'Guardado en local (sin servidor)' : `Guardado (n.º ${r?.id ?? '—'}) · recarga para verlo; el generador lo recoge de la base local`;
      },
    })),
    h('p', { style: S.meta }, 'Pueden actualizarlo Coti, Agus, Valeria, Mili y Tomás. En el prototipo no se escribe en ninguna herramienta: queda en la cola simulada con rastro y sustituye a la tabla pegada.'));
}

function objetivoAlta(ctx, a, acciones) {
  // A4: lectura común (objetivos_comun.js); «presupuesto» se guarda igual y se lee como inversion_mes.
  const o = a._objetivo?.cargado || a._objetivo?.citas_mes != null || a._objetivo?.inversion_mes != null ? a._objetivo : null;
  const previo = o ? { creado: o.cuando } : null;
  const guardado = o ? { coste_cita: o.coste_cita, coste_lead: o.coste_lead, citas_mes: o.citas_mes, presupuesto: o.inversion_mes } : null;
  const edita = puedeEditar(ctx, a.cliente_id, 'objetivo');
  const num = (id, etiqueta, valor, sufijo) => {
    const c = campo(ctx, id, { etiqueta: `${etiqueta}${sufijo ? ` (${sufijo})` : ''}`, tipo: 'number', valor: valor ?? '' });
    const el = c.querySelector('input'); el.min = '0'; el.step = '1'; el.setAttribute('inputmode', 'decimal');
    return c;
  };
  const sinDato = v => v === null || v === undefined ? 'sin dato' : fmt.num(v);
  const cuerpo = h('div', { class: 'cuerpo', style: S.pila() },
    guardado ? avisoParcial(`Cargado en la cola simulada el ${fechaLarga(previo.creado || previo.hora || '')}: coste por cita ${sinDato(guardado.coste_cita)} €, coste por lead ${sinDato(guardado.coste_lead)} €, ${sinDato(guardado.citas_mes)} citas al mes, presupuesto ${sinDato(guardado.presupuesto)} €.`, { tipo: 'info', titulo: 'Objetivo cargado.' })
      : avisoParcial('Falta el objetivo del alta: sin él, la captación usa la alarma general (más de 100 € por cita). No existe en ninguna herramienta: se carga aquí.', { titulo: 'Sin objetivo.' }),
    h('div', { style: S.rejilla(160) },
      num('cita', 'Coste por cita', guardado?.coste_cita, '€'), num('lead', 'Coste por lead', guardado?.coste_lead, '€'),
      num('citas', 'Citas al mes', guardado?.citas_mes), num('pres', 'Presupuesto al mes', guardado?.presupuesto, '€')),
    h('div', { class: 'fila' }, botonConfirmar({
      texto: 'Cargar objetivo', pregunta: '¿Guardar el objetivo del alta? Queda en la cola local y en el rastro.', confirmar: 'Sí, guardar', soloLectura: !edita,
      alConfirmar: async () => {
        const v = id => { const x = document.getElementById(`m12-${id}`)?.value; return x === '' || x === undefined ? null : Number(x); };
        const obj = { coste_cita: v('cita'), coste_lead: v('lead'), citas_mes: v('citas'), presupuesto: v('pres') };
        if (Object.values(obj).every(x => x === null)) throw new Error('Rellena al menos un campo.');
        const r = await ctx.accion({ herramienta: 'app', tipo: 'objetivo_alta', objeto: a.cliente_id, cliente_id: a.cliente_id, texto: `Objetivo del alta de ${a.nombre}`, vista_previa: obj });
        return r?.local ? 'Guardado en local (sin servidor)' : `Guardado en la cola (n.º ${r?.id ?? '—'})`;
      },
    }), edita ? null : h('span', { style: S.meta }, 'Lo cargan su account, operaciones y dirección; en las altas, también proyectos y el técnico de altas.')));
  return panel({ titulo: 'Objetivo del alta', icono: 'target', sub: 'Coste por cita y por lead, citas y presupuesto. Lo usa Captación para medir contra él.' }, cuerpo);
}

// ================================================================== módulo
export default {
  id: ID,
  titulo: 'Clientes nuevos',
  grupo: 'Clientes',
  async render(contenedor, ctx) {
    vigilarCortes(contenedor);
    plegarConsejo(contenedor);   // ronda U (#1): el consejo de la carcasa, en una línea
    // A4: el objetivo del alta es el objetivo del cliente, de un solo sitio (objetivos_comun.js: base de la app, lo cargue la ficha o esta pantalla)
    const [d, acciones, objetivos] = await Promise.all([cargar(ctx), accionesPrevias(ctx), veObjetivos(ctx) ? cargarObjetivos(ctx).catch(() => new Map()) : new Map()]);   // R15a: Sofía no los ve → no se piden
    if (!d || d._error) {
      ctx.titulo('Clientes nuevos', '');
      contenedor.append(vacio({ icono: 'alert', tono: 'aviso', borde: true, titulo: 'No llegan los datos de las altas',
        texto: `${d?._error || 'Sin respuesta'}. Los prepara el generador de altas y los sirve el servidor de la app según tu puesto.`, quien: 'Agus' }));
      return;
    }
    aplicarEstadosGuardados(d, acciones, ctx);
    for (const a of d.altas || []) a._objetivo = objetivos.get(a.cliente_id)?.objetivo || null;
    aplicarVerdad(d, ctx);
    const [id] = ctx.params;
    if (id && ctx.nivel !== 'resumen') pintarDetalle(contenedor, ctx, d, id, acciones);
    else pintarLista(contenedor, ctx, d, acciones);
  },
};
