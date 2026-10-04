import { fechas as FECHAS_RO, fechaCorta as fechaCortaRO, sumarDias as sumarDiasRO } from '../componentes.js';
// modulos/produccion_comun.js · piezas compartidas por M10 Producción y M11 Horas y productividad.
// Ronda de diseño (auditoría 30, 2-oct noche): SIN hoja de estilos propia. Solo clases comunes de estilos.css
// (fila, pila, sub, chip, av, barra-prog, titulo-seccion, lista-i…) y, donde hace falta, estilo en línea con los tokens
// de la guía (--s-*, --r-*, con su valor por defecto mientras E0 los da de alta). Nada por debajo de 12 px.
// Componentes locales (candidatos a componentes.js; apuntados en dudas_pintura.md D-P-E7):
//   barras()          barras con raya de referencia, sobre el motor único grafico() de componentes.js
//   cuentagotas()     R13: el común de componentes.js (ronda 10); se reexporta para no tocar a quien lo importa
//   barraMini()       barra horizontal pequeña para tablas: es la barraProgreso() común + su cifra
//   selectorPersona() R13: el común (con buscador y avatares) + la etiqueta «Cola de / Horas de» y la memoria por pestaña
//   lineaFuentes()    un único chip «Datos al día» que despliega la hora de cada fuente (guía 3.6)
//   punto()           punto de estado de 8 px (guía 3.8: estado de fila = punto + texto en tinta, no pastilla)

import { h, fmt, icono, barraProgreso, frescura, grafico, cuentagotas as cuentagotasComun, selectorPersona as selectorPersonaComun, hoyMadrid, sumarDias, logoCliente, vacioLinea } from '../componentes.js';

// Revisión 44 (§2.3): fechas con el formato único de la app: «2-oct» y «2-oct, 17:34» (nunca «2 oct» ni «sept»).
const _MES3 = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const fDiaRO = iso => fechaCortaRO(FECHAS_RO.dia(iso));
const fDiaHoraRO = iso => { const dia = FECHAS_RO.dia(iso), hora = FECHAS_RO.hora(iso); return dia ? `${fechaCortaRO(dia)}${hora ? `, ${hora}` : ''}` : '—'; };

// tokens de la guía con su valor de hoy (si E0 ya los ha dado de alta, mandan los suyos)
export const S = { 1: 'var(--s-1, 4px)', 2: 'var(--s-2, 8px)', 3: 'var(--s-3, 12px)', 4: 'var(--s-4, 16px)', 5: 'var(--s-5, 20px)', 6: 'var(--s-6, 24px)' };
export const R = { s: 'var(--r-s, 6px)', m: 'var(--r-m, 10px)', l: 'var(--r-l, 14px)', full: 'var(--r-full, 999px)' };
const COLOR = { verde: 'var(--good)', ambar: 'var(--warn)', rojo: 'var(--bad)', gris: 'var(--off)', azul: 'var(--accent)', '': 'var(--accent)' };

/** Ya no hay hoja de estilos propia: se deja la función para no romper a quien la llame. */
export function estilos() { /* sin <style> propio (auditoría 30) */ }

const leer = k => { try { return sessionStorage.getItem(k); } catch { return null; } };
const guardar = (k, v) => { try { sessionStorage.setItem(k, v); } catch { /* sin almacenamiento */ } };

/** punto('rojo') · punto de estado de 8 px. */
export const punto = (estado = 'gris') => h('span', { 'aria-hidden': 'true', style: { width: '8px', height: '8px', borderRadius: R.full, background: COLOR[estado] || COLOR.gris, flex: 'none', display: 'inline-block' } });

/** estadoTexto(estado, texto) · punto + texto en tinta (lo que sustituye a la pastilla roja en cada fila). */
export const estadoTexto = (estado, texto, titulo) => h('span', { class: 'fila', title: titulo || null, style: { gap: S[2], flexWrap: 'nowrap', color: 'var(--ink)', whiteSpace: 'nowrap' } }, punto(estado), texto);

/** selectorPersona({ personas: [{persona_id, nombre, puesto, grupo}], actual, clave, etiqueta, alElegir(pid) })
 *  R13: el selector común de la ronda 10 (buscador y avatares; la segunda línea dice el grupo o el puesto) con su
 *  etiqueta visible delante y, con clave, la persona elegida recordada en la pestaña del navegador. el.valor() = id. */
export function selectorPersona(o) {
  const lista = o.personas || [];
  let actual = (o.clave && leer(`ro.persona.${o.clave}`)) || o.actual;
  if (!lista.some(p => p.persona_id === actual)) actual = o.actual && lista.some(p => p.persona_id === o.actual) ? o.actual : lista[0]?.persona_id;
  const sel = selectorPersonaComun({ personas: lista, actual, etiqueta: `${o.etiqueta || 'Persona'}: cambiar de persona`,
    alElegir: p => { actual = p.persona_id; if (o.clave) guardar(`ro.persona.${o.clave}`, actual); o.alElegir?.(actual); } });
  // Revisión 44 (H3): en el móvil el selector baja de línea y usa el ancho entero (antes se veían 66 de 189 px del nombre).
  const el = h('div', { class: 'fila', style: { gap: S[2], flexWrap: 'wrap', minWidth: '0', maxWidth: '100%' } },
    h('span', { class: 'sub', style: { fontWeight: '600', whiteSpace: 'nowrap' } }, o.etiqueta || 'Persona'), sel);
  el.valor = () => actual;
  return el;
}

/**
 * barras({ puntos: [{ etiqueta, valor, ref, estado, curso }], alto, formato, titulo })
 * Barras verticales con la referencia (p. ej. horas esperadas) como raya discontinua sobre cada barra.
 * Dibuja en píxeles reales: mide su caja (ResizeObserver) y vuelve a dibujar al cambiar de ancho → letra de 12 px siempre.
 */
export function barras(o) {
  // Motor único grafico() de componentes.js (auditoría 30 §3.9): sin SVG propio. Si la referencia es la misma en todas
  // las barras, va como umbral (raya con su texto); si cambia, como serie discontinua de comparación.
  const pts = o.puntos || [];
  const refs = pts.map(p => (p.ref === null || p.ref === undefined ? null : p.ref));
  const iguales = refs.every(r => r !== null && r === refs[0]);
  return grafico({
    x: pts.map(p => p.etiqueta), alto: o.alto || 200, formato: o.formato,
    barras: { nombre: o.nombreBarras || 'Imputadas', y: pts.map(p => (p.valor === null || p.valor === undefined ? null : p.valor)) },
    series: !iguales && refs.some(r => r !== null) ? [{ nombre: o.nombreRef || 'Esperadas', y: refs, ant: true }] : [],
    umbral: iguales && refs[0] !== null ? { y: refs[0], texto: o.textoRef || fmt.num(refs[0]) } : undefined,
  });
}

/** cuentagotas(valores, umbral = 14) · R13: el común de componentes.js (ronda 10), mismo resultado. */
export const cuentagotas = (valores, umbral = 14) => cuentagotasComun(valores, umbral);

/** esMovil() · ventana de menos de 900 px (cajón de menú): se enseñan menos filas a la vista. */
/** R12 · UNA definición de «tu cola ahora» (la misma en Mi día › Tareas y en Producción › Mi cola; la fija el generador en definiciones.cola_ahora). */
export const GRUPOS_AHORA = ['vencida', 'hoy', 'semana', 'bloqueada'];

/**
 * V2 · «hoy» real en Producción. El generador agrupa la cola con el día en que corrió (D.hoy); si la pantalla se abre otro
 * día (un sábado con datos del viernes, un lunes, una recarga que falló), una tarea que vencía «hoy» ya está vencida.
 * alDia(D, hoy) reagrupa la cola con la fecha de Madrid de hoy (helper común hoyMadrid) con LA MISMA regla del generador
 * (fuentes_produccion/generar_produccion.py): vence < hoy → vencida (más de 30 días → olvidada) · vence = hoy → para hoy ·
 * vence ≤ domingo → esta semana. Revisión y bloqueadas no cambian. Recalcula las cifras de cada persona (vencidas, hoy,
 * semana, cola_ahora, olvidadas) desde las filas, así que «Para hoy» nunca lleva vencidas. Devuelve D (mutado) con
 * D.dato_de = el día del dato y D.hoy = hoy. Pedido a E0/servir.py: el mismo reagrupado para el contador del menú.
 */
export function alDia(D, hoy = hoyMadrid()) {
  if (!D || !Array.isArray(D.cola) || !FECHAS_RO.fechaCivil(hoy)) return D;
  const dato = D.hoy || hoy;
  D.dato_de = dato;
  if (dato >= hoy) return D;
  const dow = new Date(hoy + 'T12:00:00Z').getUTCDay();               // 0 = domingo
  const domingo = sumarDias(hoy, dow === 0 ? 0 : 7 - dow);
  const diasDe = v => Math.round((Date.parse(hoy) - Date.parse(v)) / 864e5);
  for (const r of D.cola) {
    const diaVence = FECHAS_RO.dia(r.vence);
    if (!diaVence || ['revision', 'bloqueada'].includes(r.grupo)) continue;
    if (diaVence < hoy) { r.vencida = true; if (['hoy', 'semana', 'despues', 'vencida'].includes(r.grupo)) r.grupo = diasDe(diaVence) > 30 ? 'olvidada' : 'vencida'; }
    else if (diaVence === hoy && ['semana', 'despues'].includes(r.grupo)) r.grupo = 'hoy';
    else if (diaVence <= domingo && r.grupo === 'despues') r.grupo = 'semana';
  }
  const por = new Map();
  for (const r of D.cola) { const l = por.get(r.persona_id) || []; l.push(r); por.set(r.persona_id, l); }
  for (const p of D.personas || []) {
    const mi = por.get(p.persona_id) || [];
    const n = g => mi.filter(r => r.grupo === g).length;
    Object.assign(p, { vencidas: n('vencida'), hoy: n('hoy'), semana: n('semana'), olvidadas: n('olvidada'), cola_ahora: mi.filter(r => GRUPOS_AHORA.includes(r.grupo)).length });
  }
  D.hoy = hoy;
  return D;
}

/** V2 (A-A5) · UNA definición de «tus revisiones» del account, la misma que Mi día («Trabajo» y «Tu cumplimiento»,
 *  revisionesAccount): revisiones de Producción con account_id = tú y revisa = 'account'; «> 48 h» = mas48. */
export function revisionesDelAccount(D, yo) {
  const todas = (D?.revisiones || []).filter(x => x.account_id === yo && x.revisa === 'account');
  return { todas, mas48: todas.filter(x => x.mas48) };
}

/** «del vie 2» · día corto en llano para decir de cuándo es el dato. */
export const diaCortoTxt = iso => { const dia = FECHAS_RO.dia(iso); return dia ? `${FECHAS_RO.diaSemana(dia)} ${Number(dia.slice(8))}` : '—'; };

export const esMovil = () => typeof matchMedia === 'function' && matchMedia('(max-width: 899px)').matches;

/** ancharBuscador(el) · R13: tablaDensa ya pone el buscador a 280 px (ronda 10); se deja pasar sin tocarlo. */
export const ancharBuscador = el => el;

/** dosColumnas(...hijos) · dos columnas IGUALES (Accounts | Especialistas): la .dos común es 2/3 + 1/3 y aquí apretaba el
 *  segundo gráfico (R13, comprobado en captura). Ya no es parche del móvil: se apila sola por debajo de 2 × 420 px.
 *  Si E0 da una variante común de columnas iguales (p. ej. .dos.iguales), se cambia aquí y vale para Horas. */
export const dosColumnas = (...hijos) => h('div', { style: { display: 'grid', gap: S[5], alignItems: 'start', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))' } }, ...hijos);

/** barraMini(valor, max, estado, texto) · barraProgreso() común + su cifra a la derecha. */
export function barraMini(valor, max, estado = '', texto) {
  return h('span', { title: texto || null, style: { display: 'inline-grid', gridTemplateColumns: 'minmax(48px, 64px) auto', gap: S[2], alignItems: 'center', whiteSpace: 'nowrap' } },
    barraProgreso({ valor: Number(valor) || 0, max: max || 1, estado: estado || null, etiqueta: texto || fmt.num(valor) }),
    texto === '' ? null : h('span', {}, texto ?? fmt.num(valor)));
}

/** Prioridad de ClickUp con icono y color (urgente rojo, alta ámbar, normal azul, baja o sin prioridad gris). */
export function prioridad(r) {
  const n = r.prio_n || 5;
  const txt = { 1: 'urgente', 2: 'alta', 3: 'normal', 4: 'baja' }[n];
  const c = { 1: ['var(--bad-ink)', 'var(--bad-soft)'], 2: ['var(--warn-ink)', 'var(--warn-soft)'], 3: ['var(--accent)', 'var(--accent-soft)'] }[n] || ['var(--off)', 'transparent'];
  return h('span', { title: txt ? `Prioridad ${txt}` : 'Sin prioridad', style: { display: 'grid', placeItems: 'center', width: '28px', height: '28px', borderRadius: R.s, color: c[0], background: c[1], flex: 'none' } }, icono('flag', { clase: 's' }));
}

/** «Vence hoy», «Vencida hace 3 días», «Vence el 5 oct», con su color. */
export function vence(iso) {
  const edad = FECHAS_RO.diasDesde(iso);
  if (edad === null) return { texto: 'Sin fecha', estado: 'gris' };
  const dias = -edad;
  if (dias < 0) return { texto: `Vencida hace ${fmt.num(-dias)} día${dias === -1 ? '' : 's'}`, estado: -dias > 14 ? 'rojo' : 'ambar', dias: -dias };
  if (dias === 0) return { texto: 'Vence hoy', estado: 'ambar', dias: 0 };
  if (dias === 1) return { texto: 'Vence mañana', estado: '', dias: 0 };
  return { texto: `Vence el ${fDiaRO(iso)}`, estado: '', dias: 0 };
}

/** Tiempo en un estado como punto + días en tinta (guía 3.8): ≤ 2 días verde, hasta 14 ámbar, > 14 rojo. */
export function chipDias(d, { verde = 2, ambar = 14 } = {}) {
  if (typeof d !== 'number' || !Number.isFinite(d) || d < 0) return estadoTexto('gris', 'sin dato');
  const est = d <= verde ? 'verde' : d <= ambar ? 'ambar' : 'rojo';
  return estadoTexto(est, d < 1 ? `${Math.round(d * 24)} h` : `${fmt.num(d, d < 10 ? 1 : 0)} días`);
}

/** horaCorta('2026-10-02 09:16') → «09:16» si es de hoy; «1 oct, 09:38» si no. */
export function horaCorta(iso) {
  const dia = FECHAS_RO.dia(iso), hm = FECHAS_RO.hora(iso);
  if (!dia || !hm) return 'sin hora';
  return FECHAS_RO.esHoy(iso) ? hm : `${fechaCortaRO(dia)}, ${hm}`;
}

/** edadFuente({ fecha, edad_h, limite_h, estado }) → { edad_h, estado: 'ok'|'viejo'|'roto' }: con límite, la edad manda
 *  (R14: antes, sin estado, salía siempre «Datos al día» aunque el consejo dijera «hace 12 h»). */
export function edadFuente(f) {
  let edad = typeof f.edad_h === 'number' && Number.isFinite(f.edad_h) && f.edad_h >= 0 ? f.edad_h : null;
  if (f.fecha) { const horas = FECHAS_RO.horasDesde(f.fecha); edad = horas !== null && horas >= 0 ? horas : null; }
  let estado = f.estado || 'ok';
  if (edad === null) estado = 'roto';
  else if (f.limite_h && edad > f.limite_h && estado === 'ok') estado = 'viejo';
  return { edad_h: edad, estado };
}

/**
 * lineaFuentes([{ fuente, nombre?, fecha|edad_h, limite_h?, estado? }], ...extra) · R14: UN solo sello de frescura.
 * Cerrado ya dice la hora real de cada fuente («Colas 15:29 · Revisiones 09:16»); el punto es verde solo si TODAS están
 * dentro de su límite de horas (el de data/fuentes.json, el mismo que usan los consejos y la cabecera), así que nunca
 * dice «al día» debajo de un «ojo con las cifras». Abierto: cuánto hace de cada una, quién la pone al día y lo extra.
 * Opciones (último argumento si es un objeto plano con «quien»): { quien: 'Mili', como: '«Actualizar ahora» en Ajustes' }.
 */
export function lineaFuentes(fuentes, ...extra) {
  const op = extra.length && extra[extra.length - 1] && extra[extra.length - 1].quien && !(extra[extra.length - 1] instanceof Node) ? extra.pop() : {};
  const lista = (fuentes || []).filter(Boolean).map(f => ({ ...f, ...edadFuente(f) }));
  const viejas = lista.filter(f => f.estado !== 'ok');
  const corto = f => f.nombre || f.fuente;
  const resumen = lista.map(f => `${corto(f)} ${horaCorta(f.fecha)}`).join(' · ');
  return h('details', { class: 'que-es', style: { minWidth: '0' }, 'data-sello': 'frescura' },
    h('summary', { style: { display: 'inline-flex', alignItems: 'center', gap: S[2], minHeight: '32px', flexWrap: 'wrap' } },
      punto(viejas.length ? 'ambar' : 'verde'),
      h('b', {}, viejas.length ? `${viejas.length === 1 ? `${corto(viejas[0])} con retraso` : `${viejas.length} fuentes con retraso`}` : 'Datos al día'),
      h('span', { class: 'sub', style: { overflowWrap: 'anywhere' } }, `· ${resumen}`)),
    h('div', { class: 'pila', style: { marginTop: S[2], gap: S[2] } },
      h('div', { class: 'fila', style: { gap: `${S[2]} ${S[3]}` } }, lista.map(f => frescura({ fuente: `${corto(f)} (${horaCorta(f.fecha)})`, edad_h: f.edad_h === null ? undefined : Math.round(f.edad_h * 10) / 10, estado: f.estado === 'roto' ? 'sin datos' : f.estado }))),
      viejas.length ? h('p', { class: 'sub', style: { margin: '0', maxWidth: '72ch' } },
        `${viejas.map(f => `${corto(f)}: dato de las ${horaCorta(f.fecha)}${f.edad_h !== null ? ` (hace ${fmt.num(f.edad_h, 0)} h, el límite es ${fmt.num(f.limite_h)} h)` : ''}`).join(' · ')}. `
        + `Ojo antes de decidir con esas cifras${op.quien ? `: lo pone al día ${op.quien}${op.como ? ` con ${op.como}` : ''}` : ''}.`) : null,
      ...extra));
}

export const NOMBRE_ESTADO = {
  'revisión project manager': 'Revisión del account', 'revisión técnica': 'Revisión técnica', 'revisión mili': 'Revisión de Mili',
  'revisión tomás': 'Revisión de Tomás', 'revisión cliente': 'Revisión del cliente', 'enviar  cliente': 'Enviar al cliente', 'ver cliente': 'Ver con el cliente',
  'bloqueado': 'Bloqueada', 'planning semanal': 'Plan de la semana', 'planning mensual': 'Plan del mes', 'próximo sprint': 'Próxima tanda',
  'diario': 'Diario', 'en curso': 'En curso', 'in progress': 'En curso', 'to do': 'Por hacer', 'complete': 'Completada', 'completado': 'Completada', 'cerrado': 'Cerrada', 'backlog': 'Pendiente sin fecha', 'campaña en curso': 'Campaña en curso',
};
export const estadoTxt = e => NOMBRE_ESTADO[e] || (e ? e[0].toUpperCase() + e.slice(1) : '—');

export const PUESTO_TXT = {
  account: 'Account', tecnico_altas: 'Técnico de altas', trafficker: 'Publicidad', jefa_publicidad: 'Jefa de publicidad', especialista_ghl: 'CRM',
  jefa_crm: 'Jefa de CRM', outreach: 'Outreach', seo: 'SEO', ficha_google: 'Ficha de Google', jefa_seo: 'Jefe de SEO', web: 'Web', redes: 'Redes',
  produccion: 'Producción creativa', operaciones: 'Operaciones', proyectos: 'Proyectos y oferta', rrhh: 'RRHH', direccion: 'Dirección', administracion: 'Administración',
};

/** Zona horaria en llano: «hora de Venezuela», «hora de España». */
export const ZONA_TXT = { 'America/Argentina/Buenos_Aires': 'hora de Argentina', 'America/Caracas': 'hora de Venezuela', 'Europe/Madrid': 'hora de España', 'Atlantic/Canary': 'hora de Canarias' };
export const zonaTxt = z => ZONA_TXT[z] || (z ? `hora de ${z.split('/').pop().replace(/_/g, ' ')}` : 'zona sin dato');

/**
 * Etiquetas de puesto que cambian cómo se lee la carga (personas.json → etiquetas).
 * «transversal»: trabaja para varias áreas (Camilo, copy), responde ante su jefe y no tiene cartera propia.
 */
export function etiquetasDe(ctx, id) {
  return (ctx.datos?.personas || []).find(p => p.id === id)?.etiquetas || [];
}

/**
 * Ronda U · U3 (3-oct, cambio #13 del 50) · fichaMarca({ cliente, marca, pedidos, tarea, alias })
 * La marca y el brief del cliente DENTRO de la tarea de producción, para no salir a ClickUp ni a Drive: logo, colores
 * (muestra + código), tono, lo que nunca se dice, enlaces a la carpeta del cliente y a la última pieza aprobada, y el brief
 * del último pedido de creatividades de publicidad. marca = fila de data/produccion/marca.json (fuentes_produccion/
 * generar_marca.py); pedidos = acciones de Captación con vista_previa.pedido_creatividad. Solo clases comunes y tokens; los
 * colores de la muestra son DATO del cliente, no del diseño de la app.
 */
export function fichaMarca({ cliente, marca, pedidos = [], tarea, alias = x => x } = {}) {
  const m = marca || {};
  const enlace = (href, ico, texto) => (href ? h('a', { class: 'bt mini', href, target: '_blank', rel: 'noopener' }, icono(ico), texto) : null);
  const titulo = t => h('p', { class: 'titulo-seccion', style: { margin: '0' } }, t);
  const colores = (m.colores || []).filter(c => /^#[0-9A-Fa-f]{6}$/.test(c));
  const ped = pedidos[0] || null;
  const vp = ped?.vp || {};
  const bloques = [
    h('div', { class: 'fila', style: { gap: S[3], flexWrap: 'nowrap', alignItems: 'center' } },
      cliente ? logoCliente(cliente) : null,
      h('div', { style: { minWidth: '0' } }, h('b', {}, `Marca de ${cliente?.nombre || m.nombre || 'el cliente'}`),
        h('span', { class: 'sub', style: { display: 'block' } }, m.logo === false ? 'Sin logo en la app: pídelo al account' : 'Logo, colores y tono para esta pieza'))),
    colores.length ? h('div', { class: 'pila', style: { gap: S[1] } }, titulo(`Colores · ${m.colores_de || 'de la marca'}`),
      h('div', { class: 'fila', style: { gap: S[2] } }, colores.map(c => h('span', { class: 'fila', style: { gap: S[1], flexWrap: 'nowrap', fontVariantNumeric: 'tabular-nums' }, title: `Copiar ${c}` },
        h('span', { 'aria-hidden': 'true', style: { width: '20px', height: '20px', borderRadius: R.s, border: '1px solid var(--line)', background: c, display: 'inline-block', flex: 'none' } }), h('span', { class: 'sub' }, c))))) : null,
    m.tipografias?.length ? h('p', { class: 'sub', style: { margin: '0' } }, `Tipografías: ${m.tipografias.join(' · ')}`) : null,
    m.tono ? h('div', { class: 'pila', style: { gap: S[1] } }, titulo('Tono'), h('p', { style: { margin: '0', maxWidth: '72ch' } }, m.tono)) : null,
    m.vetado?.length ? h('div', { class: 'pila', style: { gap: S[1] } }, titulo('Lo que nunca se dice'),
      h('ul', { style: { margin: '0', paddingLeft: S[5], display: 'grid', gap: S[1], maxWidth: '72ch' } }, m.vetado.map(v => h('li', {}, v)))) : null,
    ped ? h('div', { class: 'pila', style: { gap: S[1] } }, titulo(`Brief de publicidad · ${alias(ped.quien)}${vp.para ? ` · para el ${vp.para.slice(8, 10)}-${['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'][Number(vp.para.slice(5, 7)) - 1] || ''}` : ''}`),
      h('p', { style: { margin: '0', maxWidth: '72ch' } }, vp.brief || ped.texto), vp.anuncio ? h('p', { class: 'sub', style: { margin: '0' } }, `Sustituye a «${vp.anuncio}»`) : null) : null,
    h('div', { class: 'fila', style: { gap: S[2] } },
      enlace(m.carpeta, 'drive', 'Carpeta del cliente'),
      m.ultima_aprobada ? enlace(m.ultima_aprobada.url, 'ok', 'Última pieza aprobada') : null,
      enlace(m.web, 'globe', 'Web del cliente'),
      tarea ? enlace(tarea.url || `https://app.clickup.com/t/${encodeURIComponent(tarea.id)}`, 'ext', 'Brief en ClickUp') : null),
    m.ultima_aprobada ? h('p', { class: 'sub', style: { margin: '0' } }, `Última aprobada: «${m.ultima_aprobada.tarea}»${m.ultima_aprobada.dias !== null && m.ultima_aprobada.dias !== undefined ? ` · hace ${fmt.num(m.ultima_aprobada.dias, 0)} días` : ''}`) : null,
    !m.tono && !colores.length ? vacioLinea('Falta el manual de marca de este cliente: lo sube el account a la carpeta del cliente.', { icono: 'info' }) : null,
  ].filter(Boolean);
  return h('div', { class: 'pila', 'data-ficha-marca': cliente?.id || '', style: { gap: S[3], padding: S[4], margin: `${S[2]} 0`, border: '1px solid var(--line)', borderRadius: R.m, background: 'var(--card-2)' } }, bloques);
}
