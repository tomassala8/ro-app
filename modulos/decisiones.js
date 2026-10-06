// modulos/decisiones.js · M21 Decisiones y rastro (E2 «Para Tomás» + E10 + exigencias 48 y 49 de Mili).
// · Decisiones con reloj: 48 h para Tomás, 24 h para Coti (auditoría C-14), de incidencias (tabla `decisiones` de local.db,
//   la que llena M14) y de cualquier puesto (botón «Subir una decisión»). Problema, recomendación y fecha, siempre.
// · Las 101 decisiones firmadas el 2-oct, consultables por todos (11_DECISIONES_PARA_TOMAS.md).
// · Informe semanal para Tomás y cierre de mes de Operaciones: solo Tomás y Mili (data/decisiones/direccion.json).
// · Rastro: el de E0 (mismos datos que rastro.js) en su pestaña, con «Sobre qué» y «Texto» en claro (barrido v1:
//   sin rutas «_privado», ids «p_…» ni códigos; los tickets RO-… enlazan a la Bandeja).
// Datos: fuentes_decisiones/generar_decisiones.py → data/decisiones/{firmadas,reloj,direccion}.json.

import {
  fmt, tile, tiles, pestanas, chipsFiltro, chipEstado, tablaDensa, tablaApilable, vacio, panel, avisoParcial,
  copiar, avisoFlotante, icono, listaConIcono,
} from '../componentes.js';
import { conTickets, sinCodigos, claveLegible } from './_legible.js';
import { llevarA } from './_ir.js';
import { limpiaTexto, deDondeSale } from '../componentes.js';
import { h, elegir, estilosLocales, campo, horasTxt, chipReloj } from './personas_comun.js';
// Ronda U (50 #4, #5, #14): «Deshacer» en vez de «¿Seguro?»; #/decisiones/reloj/<id> abre ESA decisión sola con su barra de
// acciones arriba (Aprobar · Rechazar · Delegar), y las cifras de arriba son una franja pequeña que filtra.
import { botonDeshacer } from './_deshacer.js';
import { barraAcciones, franjaCifras, consejoCompacto } from './_trabajo.js';

/** Contesta una decisión (la usa también «Lo mío» para «Aprobar» en la fila). Una detectada por la app entra primero en la
 *  tabla con su clave. Nada sale de la app: queda en local.db y en el rastro. */
export async function contestarDecision(ctx, d, decision, motivo = null) {
  let id = d.id;
  if (!/^db-\d+$/.test(String(id))) {
    const r = await ctx.api('decisiones', { metodo: 'POST', cuerpo: { operacion: 'nueva', tipo: d.tipo, clave: d.clave, titulo: d.titulo, problema: d.problema,
      recomendacion: d.recomendacion, cliente_id: d.cliente_id || null, clientes: d.clientes || null, prueba: /^(https:\/\/|#\/)/.test(d.prueba || '') ? d.prueba : null } });
    id = r.id;
  }
  await ctx.api('decisiones', { metodo: 'POST', cuerpo: { operacion: 'responder', id, decision, motivo: motivo || null } });
  return id;
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

const TIPO_TXT = { para_tomas: 'Para dirección · 48 h', para_coti: 'Para proyectos · 24 h', escalada: 'Escalada · 48 h' };   // L-45: el texto nombra el puesto, no a la persona (el `tipo` interno no cambia)
const RELOJ = { para_tomas: 48, para_coti: 24, escalada: 48 };

export default {
  id: 'decisiones',
  titulo: 'Decisiones y rastro',
  grupo: 'Sistema',
  puestos_que_lo_ven: { '*': 'suyo', direccion: 'todo', operaciones: 'todo' },

  async render(cont, ctx) {
    vigilarCortes(cont);
    estilosLocales();
    const pu = ctx.persona.puestos;
    const esTomas = pu.includes('direccion');
    const esCoti = pu.includes('proyectos');
    const direccion = esTomas || pu.includes('operaciones');
    const carga = async n => { try { return await ctx.datosModulo(n); } catch { return null; } };
    const [F, R, D] = await Promise.all([carga('decisiones/firmadas'), carga('decisiones/reloj'), direccion ? carga('decisiones/direccion') : null]);
    const nombre = new Proxy({}, { get: (_, id) => ctx.nombre(id) });

    // Reloj: lo detectado al generar (reglas de la ficha de Mili sobre la verdad única) + la tabla «decisiones» en vivo
    // (GET /api/decisiones, recortada por el servidor: subidas desde aquí y escaladas por Incidencias). Lo vivo manda.
    let vivas = [];
    if (ctx.servidor) { try { vivas = (await ctx.api('decisiones')).decisiones || []; } catch { vivas = []; } }
    const clavesVivas = new Set(vivas.map(d => d.clave).filter(Boolean));
    const decis = [
      ...(R?.decisiones || []).filter(d => !vivas.some(v => v.id === d.id) && !(d.clave && clavesVivas.has(d.clave))).map(d => ({ ...d })),
      ...vivas.map(d => ({ ...d })),
    ];
    // Una detectada que se contesta entra en la tabla con la misma clave: su reloj sigue contando desde que se detectó.
    const detectadaEn = Object.fromEntries((R?.decisiones || []).filter(d => d.detectada && d.clave).map(d => [d.clave, d.creada]));
    for (const d of decis) if (d.clave && detectadaEn[d.clave] && fechaUTC(detectadaEn[d.clave]) < fechaUTC(d.creada)) { d.creada = detectadaEn[d.clave]; d.detectada = true; }
    const ahora = Date.now();
    for (const d of decis) {
      const h_ = RELOJ[d.tipo] || 48;
      const t0 = fechaUTC(d.creada);
      const fin = d.respondida ? fechaUTC(d.respondida) : ahora;
      d.horas = (fin - t0) / 36e5; d.reloj_h = h_; d.quedan = h_ - d.horas;
      d.vence = new Date(t0 + h_ * 36e5);
      d.estado = d.respondida ? (d.horas <= h_ ? 'contestada a tiempo' : 'contestada tarde') : d.horas > h_ ? 'caducada' : d.horas >= h_ * 0.75 ? 'por caducar' : 'en plazo';
    }
    decis.sort((a, b) => !!a.respondida - !!b.respondida || a.vence - b.vence);
    const abiertas = decis.filter(d => !d.respondida);
    const mias = abiertas.filter(d => (esTomas && d.tipo !== 'para_coti') || (esCoti && d.tipo === 'para_coti'));
    const caducadas = abiertas.filter(d => d.estado === 'caducada');
    const contestadas = decis.filter(d => d.respondida);
    const aTiempo = contestadas.filter(d => d.estado === 'contestada a tiempo');

    ctx.titulo('Decisiones y rastro', esTomas ? `${mias.length} decisiones te esperan · reloj de 48 h · las 101 firmadas · informe y cierre`
      : direccion ? 'Lo que sube a Tomás y a Coti, el informe semanal y el cierre de mes' : 'Sube una decisión con problema, recomendación y fecha; consulta las 101 firmadas');

    let tabs;
    const ir = id => () => { tabs?.elegir(id); tabs?.scrollIntoView({ behavior: 'smooth', block: 'start' }); };
    // Ronda U (molde): las cuatro tarjetas grandes (≈ 250 px) pasan a una franja de cifras que lleva a su pestaña.
    const esperan = esTomas || esCoti ? mias : abiertas;
    const franja = franjaCifras([
      { etiqueta: esTomas || esCoti ? 'Te esperan' : 'Abiertas que ves', valor: esperan.length, estado: esperan.some(d => d.estado === 'caducada') ? 'rojo' : '', alPulsar: ir('reloj'),
        titulo: abiertas[0] ? `La próxima vence ${fmtVence(abiertas[0].vence)}` : 'Nada pendiente' },
      { etiqueta: 'Caducadas', valor: caducadas.length, estado: caducadas.length ? 'rojo' : '', alPulsar: ir('reloj'), titulo: 'A las 36 h salta el aviso; pasadas las 48 h cuenta como «tarde»' },
      { etiqueta: 'Contestadas en 48 h', valor: contestadas.length ? `${aTiempo.length} de ${contestadas.length}` : '—', titulo: 'Indicador de Dirección' },
      { etiqueta: 'Firmadas', valor: F?.decisiones?.length ?? '—', alPulsar: ir('firmadas'), titulo: 'No se vuelve a preguntar nada de lo firmado' },
    ], { etiqueta: 'Cifras de decisiones' });
    // #/decisiones/reloj/<id> (o #/decisiones/<id>): la decisión sola, arriba del todo, con su barra de acciones fija.
    const idObj = ctx.params[0] === 'reloj' ? ctx.params[1] : (ctx.params[0] && !['reloj', 'informe', 'cierre', 'firmadas', 'rastro'].includes(ctx.params[0]) ? ctx.params[0] : null);
    const dObj = idObj ? decis.find(d => String(d.id) === String(idObj) || d.clave === idObj) : null;
    if (dObj) cont.append(focoDecision(ctx, dObj, { esTomas, esCoti, nombre }));
    else if (idObj) cont.append(avisoParcial('Esa decisión ya no está en tu lista (contestada y archivada, o no es de las que ves).', { titulo: 'No la encuentro.' }));
    cont.append(franja);
    // el consejo de la IA, plegado a una línea y debajo de la decisión y las cifras: nunca empuja lo que hay que decidir


    const lista = [
      { id: 'reloj', texto: 'Con reloj', icono: 'clock', cuenta: abiertas.length, cuentaEstado: caducadas.length ? 'rojo' : undefined },
      ...(D ? [{ id: 'informe', texto: 'Informe semanal', icono: 'doc' }, { id: 'cierre', texto: 'Cierre de mes', icono: 'cal' }] : []),
      { id: 'firmadas', texto: 'Las 101 firmadas', icono: 'libro' },
      { id: 'rastro', texto: 'Rastro', icono: 'hist' },
    ];
    tabs = pestanas({ pestanas: lista, clave: 'decisiones', etiqueta: 'Secciones de Decisiones', activa: ctx.params[0], pintar: (id, z) => {
      if (id === 'reloj') z.append(...vistaReloj(ctx, decis, { esTomas, esCoti, direccion, nombre, R, objetivo: dObj ? null : (ctx.params[0] === 'reloj' ? ctx.params[1] : null) }));
      if (id === 'informe') z.append(...vistaInforme(ctx, D));
      if (id === 'cierre') z.append(...vistaCierre(ctx, D));
      if (id === 'firmadas') z.append(...vistaFirmadas(F));
      if (id === 'rastro') { const caja = h('div', { class: 'pila' }); z.append(caja); Promise.resolve(pintarRastro(caja, ctx)).catch(e => caja.append(vacio({ titulo: 'No se pudo pintar el rastro', texto: e.message, tono: 'aviso' }))); }
    } });
    cont.append(tabs);
    consejoCompacto(cont, tabs);   // el consejo de la IA, plegado y DEBAJO de la lista: nunca empuja lo que hay que decidir
    if (ctx.params[0] && lista.some(p => p.id === ctx.params[0])) tabs.elegir(ctx.params[0]);
    else if (dObj) tabs.elegir('reloj');   // R15a (A2): la ruta manda sobre la pestaña recordada
  },
};

/** Las horas de la base van en UTC sin zona («2026-10-02 14:16:26»); las generadas, en ISO con Z. */
const fechaUTC = s => new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(s || '') ? s : String(s || '').replace(' ', 'T') + 'Z').getTime();
const _M3M = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const _partesMadrid = d => Object.fromEntries(new Intl.DateTimeFormat('es-ES', { timeZone: 'Europe/Madrid', day: 'numeric', month: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(d).map(x => [x.type, x.value]));
const _diaHoraMadrid = d => { const p = _partesMadrid(d); return `${+p.day}-${_M3M[+p.month - 1]}, ${p.hour}:${p.minute}`; };   // §2.3: «2-oct, 17:34»
// Revisión 44 (E1): el rastro guarda códigos («ver_como», «chat_abrir»); en pantalla, qué pasó dicho en llano.
const ACCION_TXT = {
  sesion: 'Inicio de sesión', ver_como: 'Vista como otra persona', lectura: 'Consulta de una pantalla', modulo: 'Abrió una pantalla',
  denegado: 'Acceso denegado', ver_dato: 'Vio un dato protegido', ver_dato_denegado: 'Dato protegido denegado', ver_lead: 'Vio los datos de un lead',
  ver_lead_denegado: 'Datos de un lead denegados', ia_copiloto: 'Consultó el copiloto de IA', ia_borrador: 'Pidió un borrador a la IA', ia_usar: 'Usó un texto de la IA',
  chat_abrir: 'Abrió el chat', mensaje_chat: 'Mensaje en el chat', nombres_propios: 'Vio nombres de personas', accion_simulada: 'Acción en la cola (simulada)',
  avisos_publicados: 'Publicó avisos', resumen_diario: 'Resumen del día', analisis_mes: 'Análisis del mes', descargar_pdf: 'Descargó un PDF',
  incidencia_visto: 'Incidencia vista', incidencia_resolver: 'Incidencia resuelta', incidencia_reiterar: 'Incidencia reiterada', incidencia_escalar: 'Incidencia escalada', incidencia_avisar: 'Incidencia avisada',
  escalar: 'Escalado', personas_salida: 'Lista de salida', personas_plan: 'Plan con una persona', estado_alta: 'Cambio de estado de un alta', visto: 'Marcado como visto',
  responder: 'Respuesta', resolver: 'Resuelto', reiterar: 'Reiterado', causa: 'Causa anotada', avisar: 'Aviso', alarma_vista: 'Aviso visto', asignar: 'Asignación', quitar_acceso: 'Quitar un acceso',
  decidir_incongruencia: 'Incongruencia decidida', paridad_comprobada: 'Mes en paralelo firmado', analisis: 'Análisis',
};
const accionTxt = a => { const k = String(a || ''); if (ACCION_TXT[k]) return ACCION_TXT[k]; const t = k.replace(/_/g, ' '); return t ? t[0].toUpperCase() + t.slice(1) : '—'; };
/** E2: «02-10-2026 11:06» → «vie 2-oct, 11:06». */
const corteLegible = t => { const m = /^(\d{2})-(\d{2})-(\d{4})(?:\s+(\d{1,2}:\d{2}))?/.exec(String(t || '')); if (!m) return String(t || '—'); const d = new Date(`${m[3]}-${m[2]}-${m[1]}T12:00:00`); return `${['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'][d.getDay()]} ${+m[1]}-${_M3M[+m[2] - 1]}${m[4] ? `, ${m[4]}` : ''}`; };
/** E3: textos guardados antes del formato común («1249 clics») salen con punto de miles. */
const miles = t => (typeof t === 'string' ? t.replace(/(^|[\s(])(\d{1,3})(\d{3})(?= (?:clics|impresiones|usuarios|leads|sesiones|visitas|correos|contactos|€))/g, (m, a, b, c) => `${a}${b}.${c}`) : t);
const horaMadrid = ms => _diaHoraMadrid(new Date(ms));

const fmtVence = d => {
  const q = (d - Date.now()) / 36e5;
  return q < 0 ? `hace ${horasTxt(-q)}` : `en ${horasTxt(q)}`;
};

// ======================================================================== Con reloj
function vistaReloj(ctx, decis, { esTomas, esCoti, direccion, nombre, R, objetivo }) {
  let filtro = '';
  const caja = h('div', { class: 'pm-tarjetas' });
  const pasa = d => !filtro || (filtro === 'abiertas' ? !d.respondida : filtro === 'contestadas' ? !!d.respondida : d.tipo === filtro);
  const pintar = () => {
    const ls = decis.filter(pasa);
    caja.replaceChildren(...(ls.length ? ls.map(d => tarjeta(ctx, d, { esTomas, esCoti, nombre }))
      : [vacio({ icono: 'ok', tono: 'celebrar', titulo: 'Nada en este filtro', texto: 'Cuando alguien suba una decisión o una incidencia se escale, aparece aquí con su reloj.' })]));
  };
  const chips = chipsFiltro({ clave: 'decisiones.reloj', etiqueta: 'Ver', opciones: [
    { valor: 'abiertas', texto: 'Abiertas', icono: 'clock', cuenta: decis.filter(d => !d.respondida).length, cuentaEstado: 'rojo' },
    { valor: 'para_tomas', texto: 'Para dirección', icono: 'crown', cuenta: decis.filter(d => d.tipo !== 'para_coti').length },
    ...(decis.some(d => d.tipo === 'para_coti') ? [{ valor: 'para_coti', texto: 'Para proyectos', icono: 'persona', cuenta: decis.filter(d => d.tipo === 'para_coti').length }] : []),   // L-45: solo a quien tiene alguna
    { valor: 'contestadas', texto: 'Contestadas', icono: 'check', cuenta: decis.filter(d => d.respondida).length },
    { valor: '', texto: 'Todas', cuenta: decis.length }], alCambiar: v => { filtro = v; pintar(); } });
  filtro = chips.valor();
  // R15a (A2): #/decisiones/reloj/<id> → esa decisión a la vista aunque el filtro guardado la escondiera
  const obj = objetivo ? decis.find(d => String(d.id) === objetivo || d.clave === objetivo) : null;
  if (obj && !pasa(obj)) filtro = '';
  pintar();
  if (obj) llevarA(caja, r => r.querySelector(`[data-decision="${CSS.escape(String(obj.id))}"]`));
  const out = [];
  if (objetivo && !obj) out.push(avisoParcial('Esa decisión ya no está en tu lista (contestada y archivada, o no es de las que ves).', { titulo: 'No la encuentro.' }));
  if (!direccion) out.push(avisoParcial('Ves las decisiones que has subido tú (y, si eres jefa, las de tu equipo). Lo que suben otros lo ven Tomás y Mili.', { tipo: 'info' }));
  out.push(panel({ titulo: 'Decisiones con reloj', icono: 'clock', sub: `Problema, recomendación y fecha. ${R?._meta?.reloj || ''}. Se ordenan por lo que antes vence.` }, h('div', { class: 'pm-pad' }, chips), caja));
  out.push(formNueva(ctx));
  if (R?._meta) out.push(h('p', { class: 'sub' }, `Las detectadas salen de las reglas de la ficha de Mili sobre la verdad única (generado ${R._meta.generado}); las subidas desde aquí y las escaladas desde Incidencias llegan en vivo.`));
  return out;
}

function tarjeta(ctx, d, { esTomas, esCoti, nombre }) {
  const color = { 'en plazo': 'verde', 'por caducar': 'ambar', caducada: 'rojo', 'contestada a tiempo': 'gris', 'contestada tarde': 'gris' }[d.estado];
  const puedeDecidir = !d.respondida && ((esTomas && d.tipo !== 'para_coti') || (esCoti && d.tipo === 'para_coti'));
  const motivo = h('input', { type: 'text', placeholder: 'Motivo (obligatorio para rechazar o delegar)', 'aria-label': 'Motivo', style: { minHeight: 'var(--s-8)' } });
  const lt = limpiaTexto;
  const decidir = decision => botonDecidir(ctx, d, decision, motivo);
  return h('article', { class: `pm-tarjeta ${color}`, 'data-decision': String(d.id) },
    h('div', { class: 'pm-cab' }, h('span', { class: `ico-c ${color}` }, icono(d.tipo === 'para_coti' ? 'persona' : 'crown')),
      h('span', { class: 't' }, h('b', { class: 'pm-dos', title: lt(d.titulo) }, lt(d.titulo)), h('span', {}, `${TIPO_TXT[d.tipo] || 'Para dirección · 48 h'} · sube ${nombre[d.quien]}`)), h('span', { class: 'der' }, chipReloj(d))),
    // Ronda U (50 #14): las acciones arriba de la tarjeta, justo bajo el título (antes al final, a 600-700 px en el móvil)
    puedeDecidir ? h('div', { class: 'pila pm-form', style: { gap: 'var(--s-2)', gridTemplateColumns: 'minmax(0, 1fr)' } },
      h('div', { class: 'fila' }, decidir('Aprobar la recomendación'), decidir('Rechazar'), decidir('Delegar')), motivo) : null,
    h('div', { class: 'pm-dec' },
      d.problema ? h('p', {}, h('b', {}, 'Problema: '), lt(d.problema)) : null,
      d.recomendacion ? h('p', { class: 'rec' }, h('b', {}, 'Recomendación: '), lt(d.recomendacion)) : h('p', { class: 'sub' }, 'Sin recomendación: devuélvela pidiendo una.')),
    h('div', { class: 'meta-linea' },
      h('span', {}, icono('clock'), d.respondida ? `Contestada en ${horasTxt(d.horas)}` : d.quedan >= 0 ? h('span', { class: 'pm-reloj' }, `Quedan ${horasTxt(d.quedan)}`) : h('span', { class: 'pm-reloj' }, `Pasada ${horasTxt(-d.quedan)}`)),
      h('span', {}, icono('cal'), `Subida ${horaMadrid(fechaUTC(d.creada))} · vence ${horaMadrid(+d.vence)} (hora de Madrid)`),
      d.prueba ? h('a', { class: 'bt mini', href: d.prueba, target: /^https?:/.test(d.prueba) ? '_blank' : null, rel: /^https?:/.test(d.prueba) ? 'noopener' : null }, icono('ext'), /^#\//.test(d.prueba) ? 'Ver en la app' : 'Ver la prueba ↗') : null),
    h('span', { class: 'sub' }, icono('info', { clase: 's' }), ` ${lt(String(d.origen || '').replace(/\s*\(local\.db\)/, ''))}${d.detectada ? ' Detectada por la app.' : ''}`),
    d.respondida ? h('p', { class: 'rec', style: { margin: 0 } }, h('b', {}, `${d.respuesta?.decision || 'Contestada'}`), d.respuesta?.motivo ? ` · ${lt(d.respuesta.motivo)}` : '', h('span', { class: 'sub' }, ` · ${nombre[d.respondida_por]}${d.simulada ? ' · simulado' : ''}`)) : null,
    null);
}

/** Ronda U (50 #4): Aprobar / Rechazar / Delegar al primer clic con «Deshacer» 8 s (antes «¿Aprobar? Sí»). Rechazar y delegar
 *  piden el motivo antes de empezar. Al escribirse, la tarjeta dice «Contestada» (sin recargar la página). */
function botonDecidir(ctx, d, decision, motivo, { pri = false } = {}) {
  const corto = decision === 'Aprobar la recomendación' ? 'Aprobar' : decision;
  return botonDeshacer({ texto: decision, pri: pri || decision === 'Aprobar la recomendación', hecho: decision === 'Aprobar la recomendación' ? 'Aprobada' : decision === 'Rechazar' ? 'Rechazada' : 'Delegada',
    soloLectura: ctx.soloLectura, titulo: `${corto}: se puede deshacer durante 8 s`,
    validar: () => (decision !== 'Aprobar la recomendación' && !motivo.value.trim() ? 'Escribe el motivo' : null),
    alHacer: async () => {
      await contestarDecision(ctx, d, decision, motivo.value.trim() || null);
      d.respondida = new Date().toISOString(); d.respuesta = { decision, motivo: motivo.value.trim() || null };
      document.querySelectorAll(`[data-decision="${CSS.escape(String(d.id))}"] .pm-form`).forEach(f => f.replaceWith(h('p', { class: 'rec', style: { margin: 0 } }, h('b', {}, decision), motivo.value.trim() ? ` · ${limpiaTexto(motivo.value.trim())}` : '', h('span', { class: 'sub' }, ' · ahora mismo'))));
      return 'Contestada · queda en el rastro';
    } });
}

/** #/decisiones/reloj/<id>: la decisión sola, con la barra de acciones arriba (sticky) y debajo su problema y recomendación. */
function focoDecision(ctx, d, { esTomas, esCoti, nombre }) {
  const puede = !d.respondida && ((esTomas && d.tipo !== 'para_coti') || (esCoti && d.tipo === 'para_coti'));
  const motivo = h('input', { type: 'text', placeholder: 'Motivo (para rechazar o delegar)', 'aria-label': 'Motivo', style: { minHeight: 'var(--s-8)', minWidth: '220px' } });
  const reloj = d.respondida ? `Contestada en ${horasTxt(d.horas)}` : d.quedan >= 0 ? `Quedan ${horasTxt(d.quedan)} · vence ${horaMadrid(+d.vence)}` : `Pasada ${horasTxt(-d.quedan)}`;
  const barra = barraAcciones({ titulo: limpiaTexto(d.titulo), sub: `${TIPO_TXT[d.tipo] || 'Para dirección · 48 h'} · sube ${nombre[d.quien]} · ${reloj}`,
    volver: { href: '#/decisiones/reloj', texto: 'Todas' },
    acciones: puede ? [botonDecidir(ctx, d, 'Aprobar la recomendación', motivo, { pri: true }), motivo, botonDecidir(ctx, d, 'Rechazar', motivo), botonDecidir(ctx, d, 'Delegar', motivo)]
      : [chipEstado(d.respondida ? 'gris' : 'ambar', d.respondida ? (d.respuesta?.decision || 'Contestada') : 'No es tuya: la decide su destinatario')] });
  const caja = h('div', { class: 'pila', 'data-decision': String(d.id), 'data-foco-decision': '' }, barra,
    h('div', { class: 'panel', style: { padding: 'var(--relleno)' } },
      d.problema ? h('p', { style: { margin: 0 } }, h('b', {}, 'Problema: '), limpiaTexto(d.problema)) : null,
      d.recomendacion ? h('p', { class: 'rec' }, h('b', {}, 'Recomendación: '), limpiaTexto(d.recomendacion)) : h('p', { class: 'sub' }, 'Sin recomendación: devuélvela pidiendo una.'),
      d.prueba ? h('a', { class: 'bt mini', href: d.prueba, target: /^https?:/.test(d.prueba) ? '_blank' : null, rel: /^https?:/.test(d.prueba) ? 'noopener' : null }, icono('ext'), /^#\//.test(d.prueba) ? 'Ver en la app' : 'Ver la prueba ↗') : null));
  return caja;
}

function formNueva(ctx) {
  const tipo = elegir([{ valor: 'para_tomas', texto: 'A dirección (48 h)', icono: 'crown' }, { valor: 'para_coti', texto: 'A proyectos (24 h)', icono: 'persona' }]);
  const titulo = h('input', { type: 'text', placeholder: 'En una línea: qué hay que decidir' });
  const problema = h('textarea', { placeholder: 'El problema con datos y nombres (no «desde sensación»)' });
  const rec = h('textarea', { placeholder: 'Tu recomendación marcada: qué harías tú' });
  const fecha = h('input', { type: 'date' });
  return panel({ titulo: 'Subir una decisión', icono: 'mas', sub: 'Filtrado primero y con una recomendación marcada. Sin recomendación no se sube. Queda en la base de la app con tu nombre y la hora.' },
    h('div', { class: 'pm-form' }, campo('Para', tipo), campo('Fecha límite (opcional)', fecha), campo('Qué hay que decidir', titulo, { ancho: true }),
      campo('Problema', problema, { ancho: true }), campo('Recomendación', rec, { ancho: true }),
      // Ronda U (50 #4): «Subir» al primer clic, con «Deshacer» 8 s (es interno: empieza a correr el reloj de Tomás o Coti)
      botonDeshacer({ texto: 'Subir', pri: true, hecho: 'Subida', soloLectura: ctx.soloLectura, mini: false,
        validar: () => (!titulo.value.trim() || !problema.value.trim() ? 'Falta qué hay que decidir o el problema' : !rec.value.trim() ? 'Falta tu recomendación' : null),
        alHacer: async () => {
          await ctx.api('decisiones', { metodo: 'POST', cuerpo: { operacion: 'nueva', tipo: tipo.value, titulo: titulo.value.trim(), problema: problema.value.trim(),
            recomendacion: rec.value.trim(), fecha: fecha.value || null } });
          avisoFlotante('Decisión subida: empieza a correr el reloj'); setTimeout(() => location.reload(), 900);
          return 'Subida';
        } })));
}

// ======================================================================== Informe semanal (exigencia 48)
function vistaInforme(ctx, D) {
  const I = D.informe_semanal;
  return [
    avisoParcial('Corto y con datos: arriba lo que tiene que desbloquear Tomás, con la recomendación marcada; después los 3 números frente a su umbral; luego clientes en rojo y equipo. Se genera solo con el corte de cada fuente.', { tipo: 'info', titulo: 'Exigencia 48 de Mili.' }),
    h('div', { class: 'dos' },
      h('div', { class: 'pila' },
        panel({ titulo: 'Qué necesito que desbloquees', icono: 'flag', sub: `Semana ${I.semana}` },
          I.desbloquear.length ? listaConIcono(I.desbloquear.map(d => ({ icono: 'flag', estado: d.estado === 'caducada' ? 'rojo' : 'ambar', texto: `${d.titulo}. Recomiendo: ${d.recomendacion}`, extra: `vence ${fDiaRO(d.vence)}` })))
            : vacio({ icono: 'ok', tono: 'celebrar', titulo: 'Nada que desbloquear esta semana' })),
        panel({ titulo: 'Los 3 números', icono: 'medidor' }, tablaApilable({ filas: I.numeros, columnas: [
          { clave: 'nombre', titulo: 'Número', principal: true },
          { clave: 'valor', titulo: 'Valor', celda: n => chipEstado(n.estado, n.valor) },
          { clave: 'umbral', titulo: 'Umbral' },
          { clave: 'detalle', titulo: 'Detalle', celda: n => h('span', { class: 'sub' }, n.detalle) },
        ] })),
        panel({ titulo: `Clientes en rojo (${I.clientes_rojo.length})`, icono: 'fire' }, listaConIcono(I.clientes_rojo.map(c => ({ icono: 'fire', estado: 'rojo', texto: `${c.cliente} · ${c.motivo}`, extra: c.account })))),
        panel({ titulo: 'Equipo', icono: 'eq' }, h('dl', { class: 'pm-kv' }, h('dt', {}, 'Imputación'), h('dd', {}, I.equipo.imputacion), h('dt', {}, 'En alerta'), h('dd', {}, String(I.equipo.en_alerta)),
          h('dt', {}, 'Por encima de capacidad'), h('dd', {}, I.equipo.sobre_capacidad.join('; ') || 'nadie')))),
      panel({ titulo: 'Texto para mandar', icono: 'copy', sub: `Datos del ${corteLegible(I.corte)}`, acciones: h('button', { type: 'button', class: 'bt pri', on: { click: () => copiar(I.texto, 'Informe copiado') } }, icono('copy'), 'Copiar') },
        h('div', { class: 'pm-texto', tabindex: '0', 'aria-label': 'Informe semanal en texto' }, I.texto))),
  ];
}

// ======================================================================== Cierre de mes (exigencia 49)
function vistaCierre(ctx, D) {
  const C = D.cierre_mes;
  const sinMotivo = C.bajas.filter(b => !b.con_motivo).length;
  const fuera = C.horas_por_account.filter(x => x.pct !== null && (x.pct > 130 || x.pct < 50));
  return [
    avisoParcial(C.verificacion_mili, { tipo: 'parcial', titulo: 'Por qué se genera solo.' }),
    tiles([
      tile({ icono: 'rocket', etiqueta: `Altas de ${C.mes}`, valor: C.altas.length, contexto: `${C.altas.filter(a => a.cruce === 'facturado').length} con factura en el mes (Holded)`, estado: C.altas.every(a => a.cruce === 'facturado') ? 'verde' : 'ambar', medible: 'hoy' }),
      tile({ icono: 'baja', etiqueta: 'Bajas', valor: C.bajas.length, contexto: sinMotivo ? `${sinMotivo} sin motivo` : 'Todas con motivo', estado: sinMotivo ? 'rojo' : C.bajas.length > 2 ? 'rojo' : C.bajas.length ? 'ambar' : 'verde', medible: 'hoy' }),
      tile({ icono: 'clock', etiqueta: 'Accounts fuera de la banda de horas', valor: fuera.length, unidad: `de ${C.horas_por_account.length}`, contexto: 'Banda 50-130 % de lo pautado · solo aviso', estado: fuera.length ? 'ambar' : 'verde', medible: 'medias', medibleDetalle: 'Horas incompletas' }),
      tile({ icono: 'doc', etiqueta: 'Informes del mes enviados', valor: C.informes.enviado || 0, unidad: `de ${Object.values(C.informes).reduce((s, n) => s + n, 0)}`, contexto: Object.entries(C.informes).map(([k, v]) => `${k} ${v}`).join(' · '), estado: (C.informes.enviado || 0) ? 'ambar' : 'rojo', medible: 'hoy', href: '#/informes-mensuales', ir: 'Ver informes' }),
    ]),
    panel({ titulo: 'Altas y bajas cruzadas con la facturación', icono: 'euro', sub: C.fuentes.altas_bajas, acciones: h('button', { type: 'button', class: 'bt pri', on: { click: () => copiar(C.texto, 'Cierre copiado') } }, icono('copy'), 'Copiar el cierre') },
      tablaApilable({ filas: [...C.altas.map(a => ({ ...a, tipo: 'alta' })), ...C.bajas.map(b => ({ ...b, tipo: 'baja' }))], columnas: [
        { clave: 'cliente', titulo: 'Cliente', principal: true },
        { clave: 'tipo', titulo: 'Movimiento', celda: r => chipEstado(r.tipo === 'alta' ? 'verde' : 'rojo', r.tipo) },
        { clave: 'fecha', titulo: 'Fecha', celda: r => fDiaRO(r.primera_factura || r.fecha_baja) },
        { clave: 'cuota', titulo: 'Cuota', num: true, celda: r => r.cuota === undefined ? h('span', { class: 'sub' }, 'no visible') : fmt.eur(r.cuota) },
        { clave: 'facturado_mes', titulo: 'Facturado en el mes', num: true, celda: r => fmt.eur(r.facturado_mes) },
        { clave: 'cruce', titulo: 'Cruce', celda: r => h('span', { class: 'sub' }, `${r.cruce}${r.nota ? ' · ' + r.nota : ''}`) },
        { clave: 'motivo', titulo: 'Motivo de la baja', celda: r => r.tipo === 'baja' ? (r.motivo || chipEstado('rojo', 'sin motivo')) : '—' },
      ] })),
    panel({ titulo: 'Horas por account frente a lo pautado', icono: 'clock', sub: `${C.horas_sello} · ${C.fuentes.horas}` },
      tablaApilable({ filas: C.horas_por_account, columnas: [
        { clave: 'account', titulo: 'Account', principal: true },
        { clave: 'reales', titulo: 'Reales', num: true, celda: x => `${fmt.num(x.reales, 1)} h` },
        { clave: 'pautadas', titulo: 'Pautadas', num: true, celda: x => `${fmt.num(x.pautadas, 1)} h` },
        { clave: 'pct', titulo: 'Desviación', num: true, celda: x => x.pct === null ? chipEstado('gris', 'sin pautadas') : chipEstado(x.pct > 130 || x.pct < 50 ? 'ambar' : 'verde', `${x.desviacion > 0 ? '+' : ''}${x.desviacion} %`) },
        { clave: 'fuera', titulo: 'Clientes fuera de banda', celda: x => h('span', { class: 'sub' }, x.fuera_banda.join(' · ') || '—') },
      ] })),
    panel({ titulo: `Clientes en rojo al cierre (${C.rojos.length})`, icono: 'fire', sub: C.fuentes.rojos },
      listaConIcono(C.rojos.map(r => ({ icono: 'fire', estado: 'rojo', texto: `${r.cliente} · ${r.motivo}`, extra: r.account })))),
  ];
}

// ======================================================================== 101 firmadas
function vistaFirmadas(F) {
  if (!F) return [vacio({ icono: 'libro', titulo: 'No se pudieron leer las decisiones firmadas', texto: 'Hay que volver a generar los datos de Decisiones.', quien: 'Agus', tono: 'aviso' })];
  const lt = limpiaTexto;
  const filas = F.decisiones.map(d => ({ ...d, n: `n.º ${d.num}`, que_t: lt(d.que), decision_t: lt(d.decision), contexto_t: lt(d.contexto || '') }));
  const detalle = h('div');
  const tabla = tablaDensa({
    filas,
    buscar: { campos: ['n', 'que_t', 'decision_t', 'contexto_t', 'tema'], placeholder: 'Buscar: «nota», «Meta», «impago», «74»…' },
    filtros: [{ clave: 'tema', titulo: 'Tema' }],
    orden: { clave: 'num', dir: 'asc' },
    columnas: [
      { clave: 'num', titulo: 'N.º', num: true, celda: d => h('b', {}, String(d.num)) },
      { clave: 'que_t', titulo: 'Qué se decidió', principal: true },
      { clave: 'decision_t', titulo: 'Decisión' },
      { clave: 'tema', titulo: 'Tema', celda: d => h('span', { class: 'sub' }, d.tema) },
    ],
    alPulsar: d => {
      detalle.replaceChildren(panel({ titulo: `Decisión n.º ${d.num} · ${d.que_t}`, icono: 'libro', sub: `${d.tema} · aceptada el 2-oct` },
        h('dl', { class: 'pm-kv' }, h('dt', {}, 'Decisión'), h('dd', {}, d.decision_t), h('dt', {}, 'Contexto'), h('dd', {}, d.contexto_t || '—')),
        deDondeSale(`${d.id} · afecta a: ${d.afecta || '—'} · 11_DECISIONES_PARA_TOMAS.md`)));
      detalle.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    },
    etiquetaFila: d => `Decisión ${d.num}: ${d.que_t}. Abrir`,
  });
  return [
    avisoParcial('Tomás las aceptó todas el 2-oct. Si alguna cambia, se anota con fecha. No se vuelve a preguntar nada de lo que está aquí.', { tipo: 'info', titulo: 'Firmadas.' }),
    panel({ titulo: `Las ${F.decisiones.length} decisiones firmadas`, icono: 'libro', sub: 'Pulsa una para ver el contexto' }, tabla), detalle,
  ];
}


// ---------------------------------------------------------------- rastro (barrido v1)
/** «2 oct, 17:12» en hora de Madrid (el servidor guarda UTC). */
const cuandoR = t => { if (!t) return '—'; const d = new Date(String(t).replace(' ', 'T') + (/[zZ]|[+-]\d\d:?\d\d$/.test(t) ? '' : 'Z')); return Number.isNaN(+d) ? t : _diaHoraMadrid(d); };

async function pintarRastro(cont, ctx) {
  if (!ctx.servidor) {
    cont.append(vacio({ icono: 'hist', titulo: 'El rastro vive en el servidor', texto: 'Sin servidor solo hay un rastro de esta pestaña del navegador, que no vale como prueba. Abre la app desde su servidor.' }));
    return;
  }
  let R;
  try { R = await ctx.api('rastro'); } catch (e) { cont.append(vacio({ icono: 'hist', titulo: 'No se pudo leer el rastro', texto: e.message, tono: 'aviso' })); return; }
  const nombres = Object.fromEntries(ctx.datos.personas.map(p => [p.id, p.alias || p.nombre]));
  const clientes = Object.fromEntries((ctx.clientes || []).map(c => [c.id, c.nombre]));
  const op = { nombres, clientes };
  const celdaTicket = t => { const x = claveLegible(t, op); return /\bRO-\d{2,}\b/.test(x) ? h('span', {}, conTickets(x, { boton: true })) : x; };
  cont.append(avisoParcial(R.todo ? 'Ves el rastro de todo el equipo. Nada se borra: desmarcar crea una anulación.' : 'Ves tu propio rastro. Nada se borra: desmarcar crea una anulación.', { tipo: 'info' }));
  const filas = R.registro.map(r => ({ ...r, quien_txt: nombres[r.quien] || r.quien, como_txt: r.como ? nombres[r.como] || r.como : '',
    accion_txt: r.anula_a ? 'Anulación' : accionTxt(r.accion), sobre_txt: claveLegible(r.clave, op), donde_txt: sinCodigos(String(r.coleccion || '').replace(/_/g, ' '), op), motivo_txt: miles(sinCodigos(r.motivo || '', op)) }));
  cont.append(panel({ titulo: 'Rastro', icono: 'hist', sub: `${fmt.num(filas.length)} últimas filas · hora de Madrid` }, tablaDensa({
    filas,
    buscar: { campos: ['accion', 'sobre_txt', 'quien_txt', 'donde_txt', 'motivo_txt'], placeholder: 'Buscar' },
    filtros: [{ clave: 'accion_txt', titulo: 'Qué' }, { clave: 'quien_txt', titulo: 'Quién' }, { clave: 'origen', titulo: 'Origen' }],
    orden: { clave: 'id', dir: 'desc' },
    columnas: [
      { clave: 'creada', titulo: 'Cuándo', celda: r => h('span', { class: 'dim', style: { whiteSpace: 'nowrap' }, title: r.creada }, cuandoR(r.creada)) },
      { clave: 'quien_txt', titulo: 'Quién', principal: true, celda: r => h('span', {}, r.quien_txt, r.como_txt ? h('span', { class: 'sub' }, ` como ${r.como_txt}`) : null) },
      { clave: 'accion', titulo: 'Qué', celda: r => chipEstado(r.anula_a ? 'gris' : /denegado/.test(r.accion || '') ? 'rojo' : 'azul', r.anula_a ? `anula #${r.anula_a}` : accionTxt(r.accion)) },
      { clave: 'donde_txt', titulo: 'Dónde' },
      { clave: 'sobre_txt', titulo: 'Sobre qué', celda: r => celdaTicket(r.clave) },
      { clave: 'motivo_txt', titulo: 'Motivo' },
    ],
    vacio: { titulo: 'Aún no hay rastro', porque: 'Cuando alguien use «ver como», «ver datos» de un lead, Ajustes o un botón, sale aquí.' },
  })));
  cont.append(panel({ titulo: 'Acciones en cola (simuladas)', icono: 'send', sub: 'En el prototipo ningún botón llama a una herramienta externa: queda aquí con su vista previa. Se ejecutarán cuando la app se despliegue.' }, tablaDensa({
    filas: R.acciones.map(a => ({ ...a, quien_txt: nombres[a.quien] || a.quien, sobre_txt: claveLegible(a.objeto, op), texto_txt: miles(sinCodigos((a.texto || '').slice(0, 160), op)) })),
    orden: { clave: 'id', dir: 'desc' },
    columnas: [
      { clave: 'creada', titulo: 'Cuándo', celda: a => h('span', { class: 'dim', style: { whiteSpace: 'nowrap' }, title: a.creada }, cuandoR(a.creada)) }, { clave: 'quien_txt', titulo: 'Quién', principal: true },
      { clave: 'herramienta', titulo: 'Herramienta' }, { clave: 'tipo', titulo: 'Qué', celda: a => accionTxt(a.tipo) }, { clave: 'sobre_txt', titulo: 'Sobre qué', celda: a => celdaTicket(a.objeto) },
      { clave: 'estado', titulo: 'Estado', celda: a => chipEstado(a.estado === 'simulada' ? 'gris' : a.estado === 'ok' ? 'verde' : 'rojo', a.estado) },
      { clave: 'texto_txt', titulo: 'Texto', celda: a => h('span', { class: 'sub' }, conTickets(a.texto_txt)) },
    ],
    vacio: { titulo: 'Ninguna acción en cola', porque: 'Aquí aparece lo que pidas desde los botones de la app (responder, asignar, escalar…), con su vista previa.', celebrar: false },
  })));
}
