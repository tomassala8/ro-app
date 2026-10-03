// modulos/_modular.js · N5 «Modular DS» en la app (3-oct-2026). No es un módulo: lo común que usan la ficha del cliente
// (pestaña «Web y SEO», bloque «Estado de la web (Modular)») y «SEO, ficha y webs» (pestaña «Webs», tablero del equipo web).
//
// Datos (solo lectura, ver fuentes_modular/FORMATO.md):
//   · ctx.datosModulo('modular/webs')    filas con cliente_id → el servidor solo manda los clientes que la persona abre
//   · ctx.datosModulo('modular/tablero') TODAS las webs (clave «cliente», sin cliente_id) → solo web, jefe de SEO y web,
//                                         operaciones y dirección (reglas_permisos.json → datos_de_modulo)
// Acciones: «Crear tarea» (clickup/tarea, sincronía simulada), «Avisar al account» (app/aviso_account) y «Marcar revisado»
// (app/web_revisado, con «Deshacer» 8 s). «Entrar al WordPress» pide al servidor un enlace de un clic (POST
// /api/modular/acceso, fuentes_modular/acceso.py): solo web, jefe de SEO y web y dirección, con rastro; apagado mientras
// la clave de Modular sea de solo lectura. «Abrir en Modular ↗» lleva al panel (la API no da la dirección de cada web).
//
//   cargarModular(ctx)                          → doc de modular/webs (o { _meta: { estado: 'sin_conectar' } })
//   cargarTablero(ctx)                          → doc de modular/tablero o null si el puesto no lo ve
//   bloqueEstadoWeb(ctx, clienteId, { web })    → <section> «Estado de la web (Modular)» (se rellena solo)
//   estadoWeb(ctx, w, { compacto })              → el cuerpo con cifras, problemas con acción y dueño, y listas
//   accionesWeb(ctx, w, { modulo, revisado })    → botones de una web (Abrir · Entrar · Crear tarea · Avisar · Revisado)
//   revisadas(ctx)                              → Map modular_id → { quien, cuando } de «Marcar revisado» de las últimas 24 h
//
// Diseño estricto: solo componentes y clases comunes (panel, tiles, primero, lista-i, que-es, bt, chip, sub) y tokens.

import {
  h, fmt, tile, tiles, panel, vacio, vacioLinea, chipEstado, frescura, icono, listaLoPrimero, botonConfirmar,
  avisoFlotante, enlaceFuente, tablaApilable,
} from '../componentes.js';
import { botonDeshacer } from './_deshacer.js';

const MES3 = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const aFecha = iso => { if (!iso) return null; const d = new Date(String(iso).length <= 10 ? `${iso}T12:00:00` : String(iso).replace(' ', 'T')); return Number.isNaN(+d) ? null : d; };
export const fDia = iso => { const d = aFecha(iso); return d ? `${d.getDate()}-${MES3[d.getMonth()]}` : '—'; };
export const fDiaHora = iso => { const d = aFecha(iso); return d ? `${d.getDate()}-${MES3[d.getMonth()]}, ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}` : '—'; };
const diasDe = n => `${fmt.num(n)} ${Math.round(n) === 1 ? 'día' : 'días'}`;
const pct = v => (v === null || v === undefined ? null : `${fmt.num(v, v >= 99.95 || v === 0 ? 0 : 2)} %`);
const ICONO_PROB = { caida: 'mundo_web', caida_fuera: 'mundo_web', sin_copia: 'drive', copia_atrasada: 'drive', copia_fallida: 'drive', malware: 'escudo',
  vulnerabilidad: 'escudo', certificado: 'candado', desconectada: 'plug', salud: 'medidor', enlaces: 'link', actualizaciones: 'recargar' };
const TXT_EST = { rojo: 'Actuar', ambar: 'Vigilar', verde: 'Bien', gris: 'Sin dato' };
export const PASO_SIN_CLAVE = 'Falta un paso de Tomás: en Modular DS, crear una clave de solo lectura (Mi perfil → API) y ejecutar pegar.sh.';

// =================================================================== datos
export async function cargarModular(ctx) {
  try { return await ctx.datosModulo('modular/webs'); } catch (e) { return { _meta: { estado: 'sin_conectar', motivo: e.message }, webs: [], clientes_sin_modular: [] }; }
}
const PUESTOS_TABLERO = ['web', 'jefa_seo', 'direccion', 'operaciones'];   // = reglas_permisos.json › datos_de_modulo › modular/tablero
export async function cargarTablero(ctx) {
  if (!ctx.servidor || !(ctx.persona?.puestos || []).some(p => PUESTOS_TABLERO.includes(p))) return null;   // sin 403 en la consola
  try { return await ctx.datosModulo('modular/tablero'); } catch { return null; }   // 403: el puesto no ve el tablero
}
/** «Marcar revisado» de las últimas 24 h (acciones del módulo seo-web): modular_id → { quien, cuando }. */
export async function revisadas(ctx) {
  const out = new Map();
  if (!ctx.servidor || !ctx.api) return out;
  try {
    const r = await ctx.api('acciones?modulo=seo-web');
    const limite = Date.now() - 24 * 3600 * 1000;
    for (const a of r.acciones || []) {
      if (a.tipo !== 'web_revisado' || !String(a.objeto || '').startsWith('modular:')) continue;
      const t = new Date(String(a.creada).replace(' ', 'T') + 'Z');
      if (+t < limite) continue;
      const id = String(a.objeto).split(':')[1];
      if (!out.has(id)) out.set(id, { quien: a.quien, cuando: t.toISOString() });
    }
  } catch { /* sin acciones: nada revisado */ }
  return out;
}
export const puedeEntrar = ctx => !!(ctx.servidor && !ctx.soloLectura && ctx.ver({ tipo: 'modular_acceso' }).ok);
const ve = (ctx, cid) => !!(cid && (ctx.clientesVisibles || []).some(c => c.id === cid));
const idCli = w => w.cliente_id || (w.sin_cliente ? null : w.cliente) || null;
const nombreWeb = w => w.cliente_nombre || (typeof w.cliente === 'string' && w.cliente_id ? w.cliente : null) || w.nombre || w.dominio;

// =================================================================== acciones
/** «Abrir en Modular ↗»: el panel de Modular (la API no da la dirección de cada web dentro del panel). */
export function botonAbrirModular(w, { mini = true } = {}) {
  return h('a', { class: `bt${mini ? ' mini' : ''}`, href: w.enlace_modular || 'https://app.modulards.com/', target: '_blank', rel: 'noopener',
    title: `Abre el panel de Modular DS: busca «${w.nombre || w.dominio}». ${w.enlace_nota || ''}`.trim() }, icono('ext', { clase: 's' }), 'Abrir en Modular ↗');
}

/** «Entrar al WordPress»: enlace de un clic que pide el SERVIDOR (solo web, jefe de SEO y web, dirección; con rastro). */
export function botonEntrar(ctx, w) {
  if (!puedeEntrar(ctx)) return null;
  const caja = h('span', { class: 'confirmar' });
  const b = h('button', { type: 'button', class: 'bt mini', title: 'Enlace de un solo uso al escritorio del WordPress (lo pide el servidor y queda en el rastro)', on: { click: async () => {
    b.disabled = true;
    caja.querySelector('.estado')?.remove();
    try {
      const r = await ctx.api('modular/acceso', { metodo: 'POST', cuerpo: { modular_id: String(w.modular_id) } });
      if (r.url) { window.open(r.url, '_blank', 'noopener'); caja.append(h('span', { class: 'estado', role: 'status' }, '✓ Abierto (caduca en 10 min)')); }
      else caja.append(h('span', { class: 'estado', role: 'status', title: r.texto || '' }, r.corto || 'Acceso de un clic apagado'));
      if (!r.url && r.texto) avisoFlotante(r.texto, { icono: 'candado' });
    } catch (e) { caja.append(h('span', { class: 'estado error', role: 'alert' }, e.message)); }
    b.disabled = false;
  } } }, icono('key', { clase: 's' }), 'Entrar al WordPress');
  caja.append(b);
  return caja;
}

function textoProblema(w) {
  const p = (w.problemas || []).find(x => x.gravedad !== 'verde');
  return p ? `${p.titulo}: ${p.detalle}` : (w.motivos || [])[0] || 'Revisión de la web';
}

/** «Crear tarea» para la persona de web (ClickUp, sincronía simulada) · confirmación porque acabará en ClickUp. */
export function botonCrearTarea(ctx, w, { modulo = 'seo-web', problema = null, texto = 'Crear tarea' } = {}) {
  const cid = idCli(w);
  const p = problema || (w.problemas || []).find(x => x.gravedad !== 'verde') || null;
  const que = p ? `${p.titulo}` : 'Revisar la web';
  const dueno = (p && p.dueno) || w.dueno || 'web';
  return botonConfirmar({ texto, pregunta: `¿Tarea en ClickUp para ${dueno}?`, confirmar: 'Sí, crear', mini: true, soloLectura: ctx.soloLectura,
    alConfirmar: async () => {
      const r = await ctx.accion({ herramienta: 'clickup', tipo: 'tarea', objeto: `Web · ${nombreWeb(w)} · ${que}`.slice(0, 200), cliente_id: ve(ctx, cid) ? cid : undefined,
        texto: p ? `${p.detalle} Qué hacer: ${p.accion}` : textoProblema(w),
        vista_previa: `Tarea en la lista de web${cid ? ` de ${nombreWeb(w)}` : ''}: «${que}». Responsable: ${dueno}. Plazo: ${p && p.gravedad === 'rojo' ? '24 h' : '72 h'}. Fuente: Modular DS (${w.dominio}).` });
      return r?.sincronia?.texto || 'Hecho en la app · pendiente de ClickUp (simulado)';
    } });
}

export function botonAvisarAccount(ctx, w, { modulo = 'seo-web' } = {}) {
  const cid = idCli(w);
  const quien = w.account_nombre || 'su account';
  return botonDeshacer({ texto: 'Avisar al account', hecho: 'Account avisado', icono: 'send', soloLectura: ctx.soloLectura || (!cid),
    titulo: cid ? `Aviso interno a ${quien}: nada sale al cliente` : 'Esta web no es de un cliente',
    alHacer: async () => { await ctx.accion({ herramienta: 'app', tipo: 'aviso_account', objeto: nombreWeb(w), cliente_id: ve(ctx, cid) ? cid : undefined, texto: textoProblema(w).slice(0, 400),
      vista_previa: `Aviso interno a ${quien} (${nombreWeb(w)}): «${textoProblema(w).slice(0, 240)}». Lo lleva ${w.dueno || 'web'}. Nada sale al cliente.` }); return `${quien} avisado`; } });
}

export function botonRevisado(ctx, w, { alHacer } = {}) {
  return botonDeshacer({ texto: 'Marcar revisado', hecho: 'Revisado', icono: 'ok', soloLectura: ctx.soloLectura,
    titulo: 'La web sale del tablero durante 24 h (si aparece algo nuevo, vuelve a subir)',
    alHacer: async () => { await ctx.accion({ herramienta: 'app', tipo: 'web_revisado', objeto: `modular:${w.modular_id}`, cliente_id: ve(ctx, idCli(w)) ? idCli(w) : undefined,
      texto: `Revisada: ${(w.motivos || []).slice(0, 3).join(' · ')}`.slice(0, 300), vista_previa: { web: w.dominio, urgencia: w.urgencia, problemas: (w.problemas || []).map(p => p.clave) } });
    alHacer?.(); return 'Revisada · sale 24 h'; } });
}

/** Una acción principal a la vista y el resto en «⋯» (menú común), para que en el móvil no salgan tres filas de botones. */
function conMas(visibles, resto) {
  resto = resto.filter(Boolean);
  if (!resto.length) return visibles.filter(Boolean);
  return [...visibles.filter(Boolean), h('details', { style: { position: 'relative', display: 'flex' } },
    h('summary', { class: 'bt mini', 'aria-label': 'Más acciones', title: 'Más acciones', style: { listStyle: 'none', cursor: 'pointer', minWidth: 'var(--s-8)', justifyContent: 'center' } }, '⋯'),
    h('div', { class: 'menu-flot', role: 'menu', style: { left: 'auto', right: '0', minWidth: '220px', display: 'grid', gap: 'var(--s-2)', padding: 'var(--s-2)' } }, resto))];
}

export function accionesWeb(ctx, w, { revisado = null, alRevisar, verDetalle } = {}) {
  return conMas([botonAbrirModular(w), revisado ? chipEstado('verde', `Revisada · ${ctx.nombre ? ctx.nombre(revisado.quien) : revisado.quien}`) : botonRevisado(ctx, w, { alHacer: alRevisar })],
    [verDetalle ? h('button', { type: 'button', class: 'bt mini', on: { click: verDetalle } }, icono('ojo', { clase: 's' }), 'Ver detalle') : null,
      botonEntrar(ctx, w), botonCrearTarea(ctx, w), botonAvisarAccount(ctx, w)]);
}

// =================================================================== estado de una web
function tilesEstado(w, { estrecho = false } = {}) {
  const d = w.disponibilidad || {}, c = w.copias, act = w.actualizaciones || {}, v = w.vulnerabilidades || {};
  const cert = w.certificado, sal = w.salud, mal = w.malware, en = w.enlaces_rotos;
  const caida = (w.problemas || []).find(p => p.clave === 'caida' || p.clave === 'caida_fuera');
  const ventanas = [['24 h', d.dia], ['7 días', d.semana], ['30 días', d.mes]].filter(x => x[1] !== null && x[1] !== undefined);
  const t = [];
  t.push(tile({ icono: 'mundo_web', etiqueta: 'Disponibilidad', valor: d.estado === 'down' ? (caida?.clave === 'caida' ? 'Caída' : 'Caída fuera') : d.estado === 'up' ? (ventanas.length ? pct(d.mes ?? d.semana ?? d.dia) : 'Arriba') : null,
    unidad: d.estado === 'up' && ventanas.length ? '30 días' : null,
    estado: d.estado === 'down' ? (caida?.gravedad || 'rojo') : d.estado === 'up' ? ((d.mes ?? 100) < 99 ? 'ambar' : 'verde') : 'gris', sinDato: d.monitor === false ? 'monitor apagado en Modular' : 'sin monitor en Modular',
    contexto: [ventanas.length ? ventanas.map(x => `${x[0]}: ${pct(x[1])}`).join(' · ') : 'Por ventanas: llega en la siguiente lectura por turnos',
      d.estado === 'down' && d.ultima_caida ? `caída desde ${fDiaHora(d.ultima_caida)}` : d.desde ? `arriba desde ${fDia(d.desde)}` : null,
      w.monitor_ro ? (w.monitor_ro.responde ? 'desde RO responde' : 'desde RO no responde') : null].filter(Boolean).join(' · ') }));
  t.push(tile({ icono: 'drive', etiqueta: 'Última copia buena', valor: !c ? null : !c.ultima_buena ? 'Nunca' : (c.dias_sin_copia_buena ?? 0) < 1 ? 'Hoy' : diasDe(Math.floor(c.dias_sin_copia_buena)),
    unidad: c?.ultima_buena && (c.dias_sin_copia_buena ?? 0) >= 1 ? 'de antigüedad' : null, sinDato: 'la clave de Modular no ve las copias',
    estado: !c ? 'gris' : !c.ultima_buena ? 'rojo' : c.dias_sin_copia_buena >= 7 ? 'rojo' : c.dias_sin_copia_buena >= 2 ? 'ambar' : 'verde',
    contexto: c ? [c.ultima_buena ? fDiaHora(c.ultima_buena) : null, c.fase_ultima === 'failed' ? 'la última falló' : null, c.total ? `${fmt.num(c.total)} copias guardadas` : null].filter(Boolean).join(' · ') || 'Sin copias en Modular' : null }));
  t.push(tile({ icono: 'recargar', etiqueta: 'Actualizaciones pendientes', valor: act.pendientes ?? null, estado: (act.pendientes ?? 0) >= 5 ? 'ambar' : act.pendientes === null || act.pendientes === undefined ? 'gris' : 'verde',
    contexto: act.pendientes ? `${fmt.num(act.nucleo || 0)} de WordPress · ${fmt.num(act.plugins || 0)} plugins · ${fmt.num(act.temas || 0)} temas` : 'Al día' }));
  t.push(tile({ icono: 'escudo', etiqueta: 'Vulnerabilidades', valor: v.total ?? null, estado: v.criticas ? 'rojo' : v.altas ? 'ambar' : 'verde',
    contexto: v.total ? `${fmt.num(v.criticas || 0)} críticas · ${fmt.num(v.altas || 0)} altas · ${fmt.num(v.medias || 0)} medias · ${fmt.num(v.bajas || 0)} bajas${v.sin_parche ? ` · ${fmt.num(v.sin_parche)} sin parche` : ''}` : 'Ninguna conocida' }));
  t.push(tile({ icono: 'candado', etiqueta: 'Certificado', valor: cert ? diasDe(cert.dias) : null, unidad: cert ? 'para caducar' : null, sinDato: 'no se ha podido leer',
    estado: !cert ? 'gris' : cert.dias <= 3 ? 'rojo' : cert.dias <= 14 ? 'ambar' : 'verde', contexto: cert ? `Caduca el ${fDia(cert.caduca)} · ${cert.fuente}` : null }));
  t.push(tile({ icono: 'medidor', etiqueta: 'Salud de WordPress', valor: sal ? sal.criticas : null, unidad: sal ? 'críticas' : null, sinDato: 'llega en la lectura por turnos',
    estado: !sal ? 'gris' : sal.criticas ? 'ambar' : 'verde', contexto: sal ? `${fmt.num(sal.recomendadas)} recomendaciones` : null }));
  t.push(tile({ icono: 'escudo', etiqueta: 'Malware', valor: mal ? (mal.amenazas ? fmt.num(mal.amenazas) : mal.veredicto) : null, unidad: mal?.amenazas ? 'amenazas' : null,
    sinDato: 'Modular no tiene ningún análisis', estado: !mal ? 'gris' : mal.amenazas ? 'rojo' : mal.veredicto === 'limpia' ? 'verde' : 'gris', contexto: mal ? `Último análisis: ${fDia(mal.fecha)}` : null }));
  t.push(tile({ icono: 'link', etiqueta: 'Enlaces rotos', valor: en && en.ultimo_escaneo ? en.abiertos ?? 0 : null, sinDato: en ? 'nunca se han revisado' : 'llega en la lectura por turnos',
    estado: !en || !en.ultimo_escaneo ? 'gris' : (en.abiertos || 0) >= 10 ? 'ambar' : 'verde',
    contexto: en && en.ultimo_escaneo ? `${fmt.num(en.rotos || 0)} rotos · ${fmt.num(en.contenido_mixto || 0)} sin https · revisión del ${fDia(en.ultimo_escaneo)}` : null }));
  const rej = tiles(t);
  if (estrecho) rej.style.gridTemplateColumns = 'repeat(2, minmax(0, 1fr))';   // en la columna del detalle (1/3), de dos en dos
  return rej;
}

function listaProblemas(ctx, w) {
  const ps = (w.problemas || []).filter(p => p.gravedad !== 'verde');
  if (!ps.length) return vacioLinea('Ningún problema abierto según Modular.', { icono: 'ok' });
  return listaLoPrimero(ps.map(p => ({
    estado: p.gravedad, icono: ICONO_PROB[p.clave] || 'alert', motivo: p.titulo,
    detalle: h('span', {}, `${p.detalle} `, h('b', {}, 'Qué hacer: '), `${p.accion} `, h('span', { class: 'sub' }, `· Lo hace: ${p.dueno || 'web'} (web)`)),
    botones: [botonCrearTarea(ctx, w, { problema: p }), botonAbrirModular(w)],
  })), { subir: false });
}

function listasPlegadas(w) {
  const act = (w.actualizaciones || {}).detalle || [];
  const vul = (w.vulnerabilidades || {}).lista || [];
  const sal = (w.salud || {}).lista || [];
  const TIPO = { core: 'WordPress', plugin: 'Plugin', theme: 'Tema' };
  const out = [];
  if (act.length) out.push(h('details', { class: 'que-es' }, h('summary', {}, `Actualizaciones pendientes (${fmt.num(w.actualizaciones.pendientes ?? act.length)})`),
    tablaApilable({ filas: act, columnas: [
      { clave: 'nombre', titulo: 'Componente', principal: true, celda: x => h('span', {}, x.nombre, x.con_vulnerabilidad ? h('span', { class: 'sub' }, ' · corrige una vulnerabilidad') : null) },
      { clave: 'tipo', titulo: 'Tipo', celda: x => TIPO[x.tipo] || x.tipo },
      { clave: 'de', titulo: 'Versión', celda: x => `${x.de || '?'} → ${x.a || '?'}` }] })));
  if (vul.length) out.push(h('details', { class: 'que-es' }, h('summary', {}, `Vulnerabilidades (${fmt.num(w.vulnerabilidades.total)}${w.vulnerabilidades.total > vul.length ? `, las ${vul.length} más graves` : ''})`),
    h('ul', { class: 'lista-i' }, vul.map(x => h('li', {}, h('span', { class: `ico-c s ${x.gravedad === 'crítica' ? 'rojo' : x.gravedad === 'alta' ? 'ambar' : 'gris'}` }, icono('escudo')),
      h('span', { class: 't' }, h('b', {}, `${x.gravedad} · ${x.componente || '?'}`), ` · ${x.nombre}${x.sin_parche ? ' · sin parche' : ''} `),
      x.fuente ? h('span', { class: 'x' }, enlaceFuente(x.fuente)) : null)))));
  if (sal.length) out.push(h('details', { class: 'que-es' }, h('summary', {}, `Salud de WordPress (${fmt.num(w.salud.criticas)} críticas · ${fmt.num(w.salud.recomendadas)} recomendaciones)`),
    h('ul', { class: 'lista-i' }, sal.map(x => h('li', {}, h('span', { class: `ico-c s ${x.estado === 'crítica' ? 'ambar' : 'gris'}` }, icono('medidor')),
      h('span', { class: 't' }, `${x.etiqueta} `), h('span', { class: 'x' }, `${x.categoria} · ${x.estado}`))))));
  return out;
}

/** Cuerpo del estado de una web de Modular: línea de cabecera, cifras, problemas con acción y dueño, y listas plegadas. */
export function estadoWeb(ctx, w, { meta = {}, conAcciones = true, estrecho = false } = {}) {
  const cab = h('div', { class: 'fila', style: { gap: 'var(--s-2)', justifyContent: 'space-between' } },
    h('span', { class: 'fila', style: { gap: 'var(--s-2)' } }, chipEstado(w.estado, TXT_EST[w.estado] || w.estado),
      h('a', { class: 'sub enlace', href: w.url, target: '_blank', rel: 'noopener' }, w.dominio),
      w.wordpress ? h('span', { class: 'sub' }, `WordPress ${w.wordpress} · PHP ${w.php || '?'}`) : null,
      h('span', { class: 'sub' }, `Lleva la web: ${w.dueno || 'sin asignar'}${w.web_id ? '' : ' (jefe de web, sin persona asignada)'}`)),
    conAcciones ? h('span', { class: 'fila', style: { gap: 'var(--s-2)' } }, botonAbrirModular(w), botonEntrar(ctx, w)) : null);
  const pie = h('p', { class: 'sub', style: { margin: '0' } }, frescura({ fuente: 'Modular DS', fecha: meta.leido || meta.generado }),
    w.detalle_leido ? ` · disponibilidad por ventanas, salud y enlaces leídos el ${fDiaHora(w.detalle_leido)} (por turnos)` : ' · disponibilidad por ventanas, salud y enlaces: en la siguiente lectura por turnos',
    meta.dato_viejo ? ` · ${meta.dato_viejo}` : '');
  return h('div', { class: 'pila', style: { gap: 'var(--s-3)', minWidth: '0' } }, cab, tilesEstado(w, { estrecho }),
    h('h3', { class: 'titulo-seccion' }, icono('zap', { clase: 's' }), 'Qué hay que hacer'), listaProblemas(ctx, w), ...listasPlegadas(w), pie);
}

// =================================================================== bloque de la ficha del cliente
/** Bloque «Estado de la web (Modular)» de la ficha (pestaña Web y SEO). Se pinta al momento con un hueco y se rellena. */
export function bloqueEstadoWeb(ctx, clienteId, { web = null } = {}) {
  const cuerpo = h('div', { class: 'cuerpo pila', style: { gap: 'var(--s-3)' } }, vacioLinea('Leyendo el estado de la web en Modular…', { icono: 'mundo_web' }));
  const caja = panel({ titulo: 'Estado de la web (Modular)', icono: 'mundo_web', sub: 'Caídas, copias, actualizaciones y seguridad del WordPress, desde Modular DS (solo lectura). Cada problema, con qué hacer y quién.' }, cuerpo);
  caja.setAttribute('data-modular', clienteId || '');
  (async () => {
    const doc = await cargarModular(ctx);
    const meta = doc?._meta || {};
    if (meta.estado !== 'conectado') {
      cuerpo.replaceChildren(vacioLinea(`Modular sin conectar. ${meta.que_hacer || PASO_SIN_CLAVE}`, { icono: 'plug', quien: 'Tomás' }));
      return;
    }
    const w = (doc.webs || []).find(x => x.cliente_id === clienteId);
    if (w) { cuerpo.replaceChildren(estadoWeb(ctx, w, { meta })); return; }
    const fuera = (doc.clientes_sin_modular || []).find(x => x.cliente_id === clienteId);
    const dom = fuera?.web || web;
    if (!dom) { cuerpo.replaceChildren(vacioLinea('Este cliente no tiene web en su ficha: no hay nada que vigilar en Modular.', { icono: 'mundo_web' })); return; }
    const fila = { modular_id: null, nombre: fuera?.cliente || clienteId, dominio: String(dom).replace(/^https?:\/\//, '').replace(/\/.*$/, ''), cliente_id: clienteId,
      dueno: fuera?.dueno, problemas: [{ clave: 'fuera', gravedad: 'ambar', titulo: 'Añadir a Modular', detalle: `${String(dom).replace(/^https?:\/\//, '').replace(/\/$/, '')} no está en Modular DS: no hay copias, actualizaciones vigiladas ni aviso de caídas desde fuera.`,
        accion: fuera?.accion || 'Añadir la web a Modular (instalar Modular Connector).', dueno: fuera?.dueno }] };
    const mon = fuera?.monitor_ro;
    cuerpo.replaceChildren(vacio({ icono: 'mundo_web', tono: 'aviso', titulo: 'Esta web no está en Modular',
      texto: `${fila.problemas[0].detalle}${mon ? ` Hoy, desde la IP de RO, ${mon.responde ? `responde (${mon.codigo})` : 'no responde'}${typeof mon.cert_dias === 'number' ? ` y el certificado caduca en ${diasDe(mon.cert_dias)}` : ''}.` : ''}`,
      quien: fuera?.dueno ? `${fuera.dueno} (web)` : 'el equipo web',
      accion: botonCrearTarea(ctx, fila, { modulo: 'ficha', problema: fila.problemas[0], texto: 'Añadir a Modular' }) }));
  })();
  return caja;
}
