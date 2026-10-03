// modulos/ficha.js · M4 «Ficha del cliente» (2-oct-2026).
// Porta la ficha v3 de «Panel de operaciones para Mili» (~/Downloads/HERRAMIENTA_RO_2026-10-02/plantilla.html), la que
// Tomás vio y le gusta, «mejorable», al contrato de módulo de la app. Ruta: #/ficha/<cliente>/<pestaña>.
//
// Datos (nada se lee de data/ a mano; todo sale recortado del servidor):
//   · ctx.clientes / ctx.datos.alarmas ............ lo común ya recortado (cuota solo si la ve; alarmas con detalle si toca)
//   · ctx.api('cliente/<id>') ...................... data/clientes/<id>.json de E1 (sin claves de dinero que no le tocan)
//   · ctx.datosModulo('ficha/portal' | 'ficha/web') . recursos del portal, búsquedas de Search Console (fuentes_ficha/)
//   · ctx.verDato(ficha/_privado/contactos | chat) . teléfonos, correos y chat de ClickUp: solo quien puede, y queda en el rastro
//   · ctx.api('acciones?modulo=ficha') y ('rastro') . lo que se ha pulsado en la ficha (cola simulada hasta W1)
//   · cargarObjetivos(ctx) (objetivos_comun.js) .... A4: objetivo del cliente y semáforo del lunes, de la base de la app
//                                                    (la misma lectura que Clientes nuevos, Captación y Mi día)
// Permisos que se miran aquí con ctx.ver (además del recorte del servidor): contactos_cliente, chat_cliente, inversion,
// cuota, cobros, horas_cliente. Lo que el servidor todavía deja pasar (ver dudas_pintura.md D-P10) se tapa también aquí.
//
// Mejoras sobre la v3: no se sale por la derecha a 1440 px (rejillas con minmax(0, 1fr) y tablas con su propio scroll),
// pestañas ordenadas por lo que más abre cada puesto, tiles que llevan a su pestaña, periodo único con comparación,
// contactos ordenados por uso (veces en Desk, GHL, CRM y portal), chat con caja de escribir (simulado hasta W1),
// llamar (sip: con la app de Zadarma), WhatsApp (wa.me) y correo en un clic, y rastro de la ficha.

import {
  h, fmt, semaforo, tile, tiles, chipEstado, chipsFiltro, selectorCliente, pestanas, barraEtapas,
  lineaTiempo, vacio, botonConfirmar, avisoParcial, logoCliente, candado, panel, frescura, icono, iniciales,
  listaLoPrimero, listaConIcono, tablaApilable, graficoSerie, botonesContacto, normalizarTelefono, copiar, avisoFlotante,
  variacion, esqueleto, rejillaTarjetas, vacioLinea, campoTexto,
} from '../componentes.js';
import { cargarObjetivos, puedeEditar, lunesDeHoy, RE_IMPORTE, TIPO_OBJETIVO, TIPO_SEMAFORO } from './objetivos_comun.js';
import { botonIA, panelCopiloto, estilos as estilosIA } from './ia_componentes.js';
import { conTickets } from './_legible.js';

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
/** F3: fechas sueltas en textos del panel de Mili («desde el lunes 28-09. Último: 25 sept.») → «28-sep», «25-sep». */
const fechasEnTexto = t => (typeof t === 'string' ? t.replace(/\b(\d{1,2})-(0[1-9]|1[0-2])\b(?![-/\d])/g, (m, d, mm) => `${+d}-${_MES3[+mm - 1]}`).replace(/\b(\d{1,2}) sept\.?(?=[\s,.;)]|$)/g, '$1-sep').replace(/\blunes (\d)/g, 'lun $1') : t);
const fDiaRO = iso => { const d = _fechaDe(iso); return !d ? '—' : Number.isNaN(+d) ? String(iso) : `${d.getDate()}-${_MES3[d.getMonth()]}`; };
const fDiaHoraRO = iso => { const d = _fechaDe(iso); return !d ? '—' : Number.isNaN(+d) ? String(iso) : `${d.getDate()}-${_MES3[d.getMonth()]}, ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; };
/** V2 · «… a rladrero/[correo]» (enmascarado a medias del dato) → «… al cliente». */
// V2 (B-M7) · UNA frase para las pantallas vacías por falta de cartera (ficha, Captación, Salud del CRM): el motivo exacto.
const NOMBRE_SILLA = { crm: 'GoHighLevel', web: 'web', trafficker: 'publicidad', account: 'account', redes: 'redes', seo: 'SEO', outreach: 'outreach', ficha_google: 'ficha de Google' };
const SILLA_PUESTO = { especialista_ghl: 'crm', jefa_crm: 'crm', trafficker: 'trafficker', jefa_publicidad: 'trafficker', account: 'account', web: 'web', redes: 'redes', seo: 'seo', jefa_seo: 'seo', outreach: 'outreach', ficha_google: 'ficha_google' };
/** motivoSinCartera(ctx) → «Tus 17 clientes están asignados como web; falta que Mili o Tomás te asignen GoHighLevel.» */
export function motivoSinCartera(ctx) {
  const silla = (ctx.persona?.puestos || []).map(p => SILLA_PUESTO[p]).find(Boolean);
  const mias = (ctx.datos?.asignaciones || []).filter(a => a.persona_id === ctx.persona?.id && !a.hasta);
  const otras = [...new Set(mias.filter(a => a.silla !== silla).map(a => a.silla))];
  const n = new Set(mias.filter(a => a.silla !== silla).map(a => a.cliente_id)).size;
  const quiero = NOMBRE_SILLA[silla] || 'tu puesto';
  if (n) return `Tus ${n} ${n === 1 ? 'cliente está asignado' : 'clientes están asignados'} como ${otras.map(x => NOMBRE_SILLA[x] || x).join(' y ')}; falta que Mili o Tomás te asignen clientes de ${quiero}.`;
  return `Todavía no tienes clientes asignados de ${quiero}. Te los asignan Mili o Tomás.`;
}
/** V2 (B-A4): a 390 la barra de arriba no cabe «Ficha del cliente» entero: «Ficha» (el selector ya dice el cliente). */
const TITULO_CORTO = () => typeof matchMedia === 'function' && matchMedia('(max-width: 480px)').matches;
const sinCorreoTapado = t => String(t ?? '').replace(/\s+a\s+[\w.+-]+\/\[correo\]/g, ' al cliente').replace(/[\w.+-]+\/\[correo\]/g, 'el cliente');

// ------------------------------------------------------------------ constantes
const PESTANAS = {
  resumen: { texto: 'Resumen', icono: 'res' },
  contactos: { texto: 'Contactos', icono: 'users' },
  resultados: { texto: 'Resultados', icono: 'target' },
  web: { texto: 'Web y SEO', icono: 'globe' },
  redes: { texto: 'Redes', icono: 'heart' },
  comunicacion: { texto: 'Comunicación', icono: 'mail' },
  chat: { texto: 'Chat', icono: 'chat' },
  trabajo: { texto: 'Trabajo', icono: 'check' },
  informes: { texto: 'Informes', icono: 'doc' },
  accesos: { texto: 'Accesos y contrato', icono: 'key' },
  rastro: { texto: 'Rastro', icono: 'hist' },
};
// «Que cada uno tenga la información ordenada de lo que más va a visitar a lo que menos» (Tomás, 2-oct).
// Resumen siempre primero y Rastro siempre último; en medio, lo que más abre cada puesto.
const ORDEN = {
  account: ['resumen', 'comunicacion', 'chat', 'contactos', 'trabajo', 'informes', 'resultados', 'web', 'redes', 'accesos', 'rastro'],
  publicidad: ['resumen', 'resultados', 'chat', 'trabajo', 'informes', 'comunicacion', 'contactos', 'web', 'redes', 'accesos', 'rastro'],
  crm: ['resumen', 'resultados', 'chat', 'trabajo', 'informes', 'comunicacion', 'contactos', 'web', 'redes', 'accesos', 'rastro'],
  seo: ['resumen', 'web', 'chat', 'trabajo', 'informes', 'resultados', 'comunicacion', 'contactos', 'redes', 'accesos', 'rastro'],
  redes: ['resumen', 'redes', 'chat', 'trabajo', 'informes', 'web', 'resultados', 'comunicacion', 'contactos', 'accesos', 'rastro'],
  resumen: ['resumen', 'redes', 'trabajo', 'informes', 'web', 'accesos', 'rastro'],
  admin: ['accesos', 'rastro'],          // administración (Sofía): cabecera, accesos y contrato, y rastro (I-02)
  direccion: ['resumen', 'comunicacion', 'resultados', 'contactos', 'chat', 'trabajo', 'informes', 'web', 'redes', 'accesos', 'rastro'],
};
const PERFIL_DE_PUESTO = {
  direccion: 'direccion', finanzas_direccion: 'direccion', operaciones: 'direccion', proyectos: 'direccion', tecnico_altas: 'direccion',
  account: 'account', jefa_publicidad: 'publicidad', trafficker: 'publicidad', jefa_crm: 'crm', especialista_ghl: 'crm',
  jefa_seo: 'seo', seo: 'seo', ficha_google: 'seo', web: 'seo', redes: 'redes', produccion: 'resumen', administracion: 'resumen',
};
const ICONO_RECURSO = { clickup: 'check', clickupFolder: 'capas', drive: 'drive', metaAds: 'target', statusSheet: 'doc', reports: 'doc',
  analytics: 'grafico', searchConsole: 'buscar', googleAds: 'megafono', looker: 'res' };
const RECURSO_DE_PESTANA = { resultados: 'metaAds', web: 'analytics', trabajo: 'clickup', accesos: 'drive' };
const SILLAS = { account: 'Account', trafficker: 'Publicidad', crm: 'CRM', seo: 'SEO', web: 'Web', redes: 'Redes', outreach: 'Outreach' };
const ESPACIO_CLICKUP = '90152357276';
const CLAVE_ULTIMO = 'ro.ficha.ultimo';

// Caché de la sesión: cambiar de cliente o de pestaña es instantáneo (regla 10 del sistema visual).
const CACHE = { cliente: new Map(), contactos: new Map(), chat: new Map(), portal: null, web: null };

const ses = { leer: k => { try { return sessionStorage.getItem(k); } catch { return null; } }, poner: (k, v) => { try { sessionStorage.setItem(k, v); } catch { /* nada */ } } };
const num = v => (v === null || v === undefined || Number.isNaN(+v) ? null : +v);
const suma = xs => xs.reduce((a, b) => a + (num(b) || 0), 0);
const isoDe = s => (/^\d{8}$/.test(s) ? `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6)}` : s);
const fFecha = iso => (iso ? `${fDiaRO(iso)}${String(iso).slice(0, 4) !== '2026' ? ' ' + String(iso).slice(0, 4) : ''}` : '—');
const corto = n => String(n || '').trim().split(/\s+/)[0] || '';

// ------------------------------------------------------------------ guía de diseño (auditoría 30)
// Sin hoja de estilos propia: solo clases y piezas comunes de E0 (rejillaTarjetas, esqueleto, .campo, pestanas en una fila).
const rejilla = lista => rejillaTarjetas(lista.filter(Boolean));

// Pestañas en una fila con «Más (n) ▾» y menú «Más»: piezas comunes de la ronda 10 de E0 (pestanas({ unaFila: true }), menuMas()).

// ------------------------------------------------------------------ utilidades de datos
// Textos del portal con importe (ronda 11): «descripcion»/«duda» vienen siempre sin cifra; «…_completa» lleva el original
// y el servidor le quita el importe a quien no ve ese dinero (P.sin_importes). Nunca «[importe]».
const descripcionDe = (portal, c) => portal?.descripcion_completa || portal?.descripcion || c?.descripcion || null;
const fuente = (doc, id) => doc?.fuentes?.[id] || null;
const pintable = f => !!f && ['bien', 'dato_viejo', 'a_cero'].includes(f.estado) && f.medicion !== 'no';
// frescuraDe(f) → objeto para tile({ frescura }); frescuraEl(f) → el sello «Desk · hoy» para pintar suelto.
const frescuraDe = f => (f && f.hora ? { fuente: f.fuente || 'Dato', fecha: f.hora, estado: f.estado === 'dato_viejo' ? 'viejo' : f.estado === 'rota' ? 'roto' : 'ok' } : null);
const frescuraEl = f => { const o = frescuraDe(f); return o ? frescura(o) : null; };

/** Hueco con estado vacío útil para una fuente que no se puede pintar (R5: rota y sin conectar a vacío con su nota). */
function huecoFuente(f, { icono: ico = 'plug', titulo, quien = 'Agus (conexiones)' } = {}) {
  if (!f) return vacio({ icono: ico, titulo: titulo || 'Sin dato de esta fuente', texto: 'La capa de datos no trae este bloque para el cliente.', quien });
  if (f.estado === 'no_aplica') return vacio({ icono: ico, titulo: titulo || `${f.fuente}: no aplica`, texto: f.nota || 'No aplica a este cliente.' });
  const t = { sin_conectar: `${f.fuente}: sin conectar`, rota: `${f.fuente}: la conexión falla`, a_cero: `${f.fuente}: a cero` }[f.estado] || `${f.fuente}: todavía no se mide`;
  return vacio({ icono: ico, titulo: titulo || t, texto: f.nota || 'Sin dato para este cliente.', quien, tono: f.estado === 'rota' ? 'aviso' : 'neutro' });
}

function barras(filas, { formato = v => fmt.num(v), estado } = {}) {
  if (!filas.length) return vacio({ icono: 'vacio', titulo: 'Sin datos de esta fuente', texto: 'La herramienta no trae nada de este cliente en estas fechas. Si esperabas datos, avisa a su account.' });   // §3: con porqué y quién
  const mx = Math.max(1, ...filas.map(f => f[1] || 0));
  return h('div', { class: 'embudo-barras' }, filas.map(([t, v, est]) => h('div', { class: 'et' },
    h('span', { title: t }, h('span', { style: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, t)),
    h('span', { class: 'barra-prog', 'aria-hidden': 'true' }, h('i', { class: est || estado || null, style: { width: `${Math.max(2, (v || 0) / mx * 100)}%` } })),
    h('span', { class: 'n' }, formato(v)))));
}

function etapa(c) {
  if (!c.alta) return -1;
  const d = (Date.now() - new Date(c.alta + 'T12:00:00')) / 864e5;
  return d < 14 ? 0 : d < 30 ? 1 : d < 90 ? 2 : 3;
}

function perfil(ctx) {
  if (ctx.persona.puestos.every(p => p === 'administracion')) return 'admin';
  if (ctx.nivel === 'resumen') return 'resumen';
  for (const p of ctx.persona.puestos) if (PERFIL_DE_PUESTO[p]) return PERFIL_DE_PUESTO[p];
  return 'direccion';
}

/** Ventana de una serie diaria: los últimos n puntos y los n anteriores (para comparar). */
function ventana(serie, n, valor = x => x[1]) {
  const v = serie.map(valor);
  const act = v.slice(-n), ant = v.slice(-2 * n, -n);
  return { actual: suma(act), anterior: ant.length === n ? suma(ant) : null, dias: act.length };
}

// ------------------------------------------------------------------ carga
async function cargarCliente(ctx, id) {
  if (CACHE.cliente.has(id)) return CACHE.cliente.get(id);
  let doc = null;
  if (ctx.servidor) doc = (await ctx.api(`cliente/${id}`)).fuentes;
  else doc = await (await fetch(`data/clientes/${id}.json`, { cache: 'no-cache' })).json();   // modo de respaldo sin permisos (LEEME)
  CACHE.cliente.set(id, doc);
  return doc;
}
async function cargarModulo(ctx, nombre) {
  const k = nombre.split('/')[1];
  if (CACHE[k]) return CACHE[k];
  try { CACHE[k] = await ctx.datosModulo(nombre); } catch { CACHE[k] = { filas: [] }; }
  return CACHE[k];
}
/** Contactos o chat del almacén privado. Solo si la regla lo deja (se pregunta antes: así no hay 403 en la consola). */
async function cargarPrivado(ctx, cual, id) {
  const tipo = cual === 'contactos' ? 'contactos_cliente' : 'chat_cliente';
  const v = ctx.ver({ tipo, cliente_id: id });
  if (!v.ok) return { negado: v.motivo || 'No visible para tu puesto.' };
  if (!ctx.servidor) return { negado: 'Sin servidor: arranca «python3 servir.py» para abrir contactos y chat (van en almacén privado).' };
  if (ctx.soloLectura) return { negado: 'En «ver como» no se abren teléfonos, correos ni chat: abrirlos deja rastro a tu nombre. Entra como esa persona para probarlo.' };
  const cache = CACHE[cual];
  if (cache.has(id)) return cache.get(id);
  let r;
  const cuerpo = { almacen: `ficha/_privado/${cual}`, ref: id, campo: 'datos', cliente_id: id };
  // Mismo /api/ver_dato que ctx.verDato, con la cabecera X-RO-App que exige servir.py desde la ronda 6 de E0
  // (así no hay un 403 en consola mientras datos.js no la mande; con un servidor antiguo la cabecera se ignora).
  try {
    const resp = await fetch('api/ver_dato', { method: 'POST', cache: 'no-store', body: JSON.stringify(cuerpo),
      headers: { 'Content-Type': 'application/json', 'X-RO-App': '1', 'X-RO-Yo': ctx.real.id, ...(ctx.persona.id !== ctx.real.id ? { 'X-RO-Como': ctx.persona.id } : {}) } });
    const d = await resp.json().catch(() => ({}));
    r = resp.ok ? { valor: d.valor } : resp.status === 404 ? { valor: null } : { negado: d.error || `Error ${resp.status}` };
  } catch (e) { r = { negado: e.message }; }
  cache.set(id, r);
  return r;
}

// =================================================================== render
export default {
  id: 'ficha',
  titulo: 'Ficha del cliente',
  grupo: 'Clientes',
  usa_periodo: ['7d', '30d'],
  async render(cont, ctx) {
    vigilarCortes(cont);
    estilosIA();
    const [idParam, tabParam] = ctx.params;
    // R15b: #/ficha/<id>?semaforo=1 (o ?objetivo=1) abre el editor del lunes (o el del objetivo) ya desplegado y a la vista.
    const consulta = new URLSearchParams((location.hash || '').split('?')[1] || '');
    const abrirA4 = consulta.get('semaforo') === '1' ? 'semaforo' : consulta.get('objetivo') === '1' ? 'objetivo' : null;
    const vis = ctx.clientesVisibles;
    const raiz = h('div', { class: 'pila' });
    cont.append(raiz);

    if (!vis.length && ctx.nivel === 'resumen') { await pintarBasica(raiz, ctx, idParam); return; }
    if (!vis.length) {
      ctx.titulo('Ficha del cliente', 'Ningún cliente que abrir');
      raiz.append(vacio({ icono: 'candado', borde: true, titulo: 'No tienes clientes que abrir',
        texto: ctx.ambito === 'cartera' ? motivoSinCartera(ctx) : 'Tu puesto no abre fichas de clientes. La lista común está en «En rojo».',
        quien: 'Mili (asignaciones)', accion: h('a', { class: 'bt', href: '#/en-rojo' }, icono('fire'), 'Ir a En rojo') }));
      return;
    }

    // Cliente: el de la ruta; si no, el último que abriste; si no, el de tu cartera con peor salud.
    let id = idParam;
    if (!id) {
      const ult = ses.leer(CLAVE_ULTIMO);
      const mios = vis.filter(c => c.enCartera).sort((a, b) => (a.salud ?? 100) - (b.salud ?? 100));
      id = (vis.some(c => c.id === ult) && ult) || (mios[0] || [...vis].sort((a, b) => (a.salud ?? 100) - (b.salud ?? 100))[0]).id;
      history.replaceState(null, '', `#/ficha/${id}`);
    }
    const c = ctx.clientes.find(x => x.id === id);
    if (!c) {
      raiz.append(vacio({ icono: 'buscar', borde: true, titulo: 'No encuentro ese cliente', texto: `No hay ningún cliente con el identificador «${id}».`, accion: h('a', { class: 'bt', href: '#/ficha' }, icono('volver'), 'Volver a mis fichas') }));
      return;
    }
    if (!c.detalle) {
      ctx.titulo(c.nombre, 'Ficha del cliente');
      raiz.append(vacio({ icono: 'candado', borde: true, titulo: 'La ficha de este cliente no es de tu puesto',
        texto: `Ves su motivo y su responsable en «En rojo»; la ficha, los contactos y el dinero solo los ve quien lo lleva. Si necesitas algo de ${c.nombre}, habla con ${c.responsable}.`,
        quien: c.responsable, accion: h('a', { class: 'bt', href: `#/en-rojo` }, icono('fire'), 'Ir a En rojo') }));
      return;
    }
    ses.poner(CLAVE_ULTIMO, id);

    // ---- selector de cliente (logo, account, buscador). El periodo es el común de la carcasa (usa_periodo, ronda 9). ----
    const orden = ORDEN[perfil(ctx)];
    let tabActual = orden.includes(tabParam) ? tabParam : (orden.includes(ses.leer('ro.pestana.ficha')) ? ses.leer('ro.pestana.ficha') : orden[0]);
    const selector = selectorCliente({
      clientes: [...vis].sort((a, b) => Number(b.enCartera) - Number(a.enCartera) || a.nombre.localeCompare(b.nombre, 'es')),
      actual: id, etiqueta: 'Cambiar de cliente',
      detalle: x => detalleSelector(ctx, x),
      alElegir: x => ctx.navegar(`ficha/${x.id}/${tabActual}`),     // al cambiar de cliente te quedas en la misma pestaña
    });
    // El nombre del cliente sale una vez: el selector ES el título (guía 3.6); sin migas ni nombre repetido.
    const barra = { selector };
    let periodoId = ctx.periodo?.id || '7d';
    // Atajo: «c» abre el selector de clientes (⌘K es el buscador de toda la app).
    const atajo = e => {
      if (!raiz.isConnected) { document.removeEventListener('keydown', atajo); return; }
      if (e.key === 'c' && !e.metaKey && !e.ctrlKey && !e.altKey && !/input|textarea|select/i.test(document.activeElement?.tagName || '') && !document.activeElement?.isContentEditable) { e.preventDefault(); selector.abrir(); }
    };
    document.addEventListener('keydown', atajo);

    const zona = h('div', { class: 'pila' }, h('div', { class: 'fila' }, selector), esqueleto({ tarjetas: 4, lineas: 3 }));
    raiz.append(zona);
    const accVerdad = ctx.verdad ? ctx.verdad(id)?.account : undefined;
    ctx.titulo(TITULO_CORTO() ? 'Ficha' : 'Ficha del cliente', `Lleva el cliente ${accVerdad ? ctx.nombre(accVerdad) : (c.responsable || 'sin account')}`);

    let doc, portal, web, contactos, correos, porCliente, objetivos, hallazgos;
    const admin = perfil(ctx) === 'admin';
    try {
      // Correos sin contestar: la regla única de la Bandeja (data/bandeja/por_cliente.json); la lista, su copia del mismo minuto.
      // Administración no recibe correos (I-02).
      [doc, portal, web, contactos, correos, porCliente, objetivos, hallazgos] = await Promise.all([cargarCliente(ctx, id), cargarModulo(ctx, 'ficha/portal'),
        admin ? { filas: [] } : cargarModulo(ctx, 'ficha/web'), cargarPrivado(ctx, 'contactos', id), admin ? null : cargarModulo(ctx, 'ficha/correos'),
        admin ? null : cargarModulo(ctx, 'bandeja/por_cliente'), admin ? null : cargarObjetivos(ctx),
        admin ? null : cargarModulo(ctx, 'fuentes/hallazgos_medicion')]);
    } catch (e) {
      zona.replaceChildren(vacio({ icono: 'alert', tono: 'aviso', borde: true, titulo: 'No he podido cargar la ficha', texto: String(e.message || e), quien: 'quien mantiene la app' }));
      return;
    }
    const F = {
      c, doc: doc || { fuentes: {} },
      portal: (portal.filas || []).find(x => x.cliente_id === id) || null,
      web: (web.filas || []).find(x => x.cliente_id === id) || null,
      contactos,
      correos: correos && correos.correos ? { generado: correos._meta?.generado, horas: correos._meta?.horas,
        lista: correos.correos.filter(x => x.cliente_id === id), llamadas: (correos.llamadas || []).filter(x => x.cliente_id === id) } : null,
      porCliente: porCliente && Array.isArray(porCliente.clientes) ? { generado: porCliente.generado, fuentes: porCliente.fuentes || {},
        fila: porCliente.clientes.find(x => x.cliente_id === id) || null } : null,
      admin,
      obj: objetivos ? (objetivos.get(id) || {}) : null,   // A4: objetivo y semáforo del lunes (null = administración, no lo ve)
      verdad: ctx.verdad ? ctx.verdad(id) : null,
      medicion: admin ? [] : medicionDe(doc, hallazgos, id),   // N14: fallos de medición y accesos que faltan, con dueño
      alarmas: ctx.datos.alarmas.filter(a => a.ambito === 'cliente' && a.cliente_id === id)
        .sort((a, b) => (a.gravedad === b.gravedad ? 0 : a.gravedad === 'rojo' ? -1 : 1)),
      ve: {
        inversion: ctx.ver({ tipo: 'inversion', cliente_id: id }).ok,
        cuota: c.cuota !== undefined,          // la cuota que se pinta sale de la fuente única (Airtable, como Dinero por cliente)
        cobros: ctx.ver({ tipo: 'cobros', cliente_id: id }).ok,
        horas: ctx.ver({ tipo: 'horas_cliente', cliente_id: id }),
        responder: ctx.ver({ tipo: 'responder_cliente', cliente_id: id }).ok,
      },
      // Periodo común (ctx.periodo): la ficha tiene cifras de 7 y de 30 días (usa_periodo: ['7d', '30d']).
      periodo: () => (periodoId === '30d' ? '30' : '7'),
    };

    function repintar() {
      zona.replaceChildren(cabecera(ctx, F, barra));
      const cuentas = contadores(F);
      let caja = null;
      const irA = k => { if (caja && orden.includes(k)) { caja.elegir(k); caja.querySelector('[role=tablist]')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); } };
      F.irA = irA;
      caja = pestanas({
        etiqueta: `Ficha de ${c.nombre}`, activa: tabActual, unaFila: true,
        pestanas: orden.map(k => ({ id: k, texto: PESTANAS[k].texto, icono: PESTANAS[k].icono, ...(cuentas[k] || {}) })),
        alCambiar: k => { tabActual = k; ses.poner('ro.pestana.ficha', k); history.replaceState(null, '', `#/ficha/${id}/${k}`); },
        pintar: (k, z) => {
          // N14: los fallos de medición de las fuentes de esta pestaña, arriba y con dueño (la pestaña se pinta debajo)
          const med = bloqueMedicion(ctx, F, k);
          if (med) { const dentro = h('div', { class: 'pila', style: { minWidth: '0' } }); z.replaceChildren(med, dentro); z = dentro; }
          try { PINTAR[k](z, ctx, F, irA); }
          catch (e) { console.error(e); z.replaceChildren(vacio({ icono: 'alert', tono: 'aviso', titulo: 'Esta pestaña ha fallado al pintarse', texto: String(e.message || e) })); }
        },
      });
      zona.append(caja);
    }
    // ctx.periodo es el del momento de pintar; el oyente trae el nuevo y se repinta la ficha en la misma pestaña.
    ctx.alCambiarPeriodo?.(v => { periodoId = v?.id; if (raiz.isConnected) repintar(); });
    if (abrirA4 && F.obj) F.a4 = abrirA4;
    repintar();
    if (abrirA4 && F.obj) {
      // El editor ya sale abierto (su botón, pulsado): basta con llevarlo al centro y dar el foco a su primer campo.
      const aLaVista = (n = 0) => {
        const ed = zona.querySelector('[data-a4-editor]');
        if (!ed || !ed.isConnected) { if (n < 40) setTimeout(() => aLaVista(n + 1), 75); return; }
        const campo = ed.querySelector(abrirA4 === 'semaforo' ? 'input, button' : 'input');
        ed.scrollIntoView({ block: 'center' });
        if (campo) campo.focus({ preventScroll: true });
        else { ed.setAttribute('tabindex', '-1'); ed.focus({ preventScroll: true }); }
      };
      aLaVista();
    } else if (abrirA4) {
      zona.prepend(avisoParcial('El semáforo del lunes y el objetivo no se ven desde tu puesto.', { tipo: 'info' }));
    }
  },
};

// =================================================================== cabecera
function cabecera(ctx, F, barra = {}) {
  const { c, doc, portal } = F;
  const v = F.verdad || {};
  const libro = fuente(doc, 'libro')?.datos || {};
  const sem = c.semaforo === 'crítico' ? 'rojo' : ['excelente', 'normal', 'bien'].includes(c.semaforo) ? 'verde' : c.semaforo && c.semaforo !== 'definir' ? 'ambar' : 'gris';
  const textoSem = !c.semaforo || c.semaforo === 'definir' ? 'Semáforo sin poner' : `Semáforo: ${c.semaforo}`;
  const web = c.web ? c.web.replace(/^https?:\/\//, '').replace(/\/$/, '') : null;
  const e = etapa(c);
  const grav = { critico: ['rojo', 'Crítico'], atencion: ['ambar', 'Vigilar'], bien: ['verde', 'Bien'] }[v.gravedad];
  const salud = v.salud ?? c.salud;
  const especialidad = (libro.espec || '').replace(/\s*\([A-ZÁÉÍÓÚ]{2,6}\)\s*/g, ' ').trim();   // «Ley de Segunda Oportunidad (LSO)» → sin la sigla
  const cuota = cuotaFicha(F);

  // «Llamar a…» y WhatsApp: la persona principal (la que más interactúa) con móvil; si no, la primera con móvil.
  const contacto = contactoPrincipal(F.contactos?.valor);
  const contactoCab = contacto
    ? botonesContacto({ ...contacto, modo: 'cabecera' })
    : F.contactos?.negado ? h('span', { class: 'candado', title: F.contactos.negado, style: { flex: '1 1 240px', minWidth: '0', whiteSpace: 'normal' } }, 'Contactos: su account, operaciones y dirección') : null;
  contactoCab?.querySelectorAll('a').forEach(a => a.addEventListener('click', () => ctx.rastro({ accion: /^sip:/.test(a.href) ? 'llamar' : /wa\.me/.test(a.href) ? 'whatsapp' : 'correo', objeto: c.id, detalle: 'desde la cabecera de la ficha' })));

  // Atajos «Abrir en …»: los del portal + subcuenta de GoHighLevel, Metricool y SE Ranking. Si falta el identificador, deshabilitado con el porqué.
  const recursos = (portal?.recursos || []).filter(r => r.url);
  const directos = ['clickup', 'drive', 'metaAds', 'analytics', 'searchConsole'].map(k => recursos.find(r => r.k === k)).filter(Boolean);
  const extra = (portal?.atajos || []);
  const deskUrl = F.admin ? null : (F.porCliente?.fila?.mas_antiguo?.url || (F.correos?.lista || [])[0]?.url || null);
  const atajo = (url, ico, texto) => { const a = h('a', { class: 'bt mini', href: url, target: '_blank', rel: 'noopener', title: `Abrir en ${texto} ↗` }, icono(ico), texto);
    a.addEventListener('click', () => ctx.rastro({ accion: 'abrir_atajo', objeto: c.id, detalle: texto })); return a; };
  const ICO_EXTRA = { ghl: 'cap', metricool: 'heart', seranking: 'star' };
  const NOMBRE_CORTO = { ghl: 'GoHighLevel', metricool: 'Metricool', seranking: 'SE Ranking' };
  const fila100 = { flexBasis: '100%', minWidth: '0' };

  // Copiloto de la IA («Qué haría hoy») en la cabecera: quien abre el detalle del cliente; nunca administración (I-02).
  const veCopiloto = !F.admin && ctx.ver({ tipo: 'cliente_detalle', cliente_id: c.id }).ok;
  let copiloto = null;
  if (veCopiloto) {
    copiloto = panelCopiloto(ctx, c.id, { compacto: !!ctx.veModulo?.('asistente-ia') });
    copiloto.style.flexBasis = '100%';
    copiloto.style.minWidth = '0';
  }

  return h('section', { class: 'detalle-cab', 'aria-label': 'Cabecera del cliente' },
    // 1 · el selector de cliente es el título (el periodo está en la barra común, bajo la cabecera)
    h('div', { class: 'fila', style: fila100 }, barra.selector || h('b', {}, c.nombre)),
    // 2 · datos y estado del cliente · contacto
    h('div', { class: 'fila', style: { ...fila100, justifyContent: 'space-between', alignItems: 'flex-start' } },
      h('div', { class: 'pila', style: { flex: '1 1 260px', minWidth: '0' } },   // V2 (B-A4): con poco ancho, el contacto baja de línea
        portal?.nombre_portal && portal.nombre_portal !== c.nombre ? h('p', { class: 'sub' }, portal.nombre_portal) : null,
        h('div', { class: 'meta-linea' },
          c.alta ? h('span', {}, icono('cal'), `Cliente desde ${fFecha(c.alta)}`) : null,
          cuota ? h('span', { title: `Cuota mensual sin IVA · ${cuota.fuente}` }, icono('euro'), `${fmt.eur(cuota.valor)}/mes`) : null,
          especialidad ? h('span', {}, icono('maletin'), especialidad) : descripcionDe(portal, c) ? h('span', {}, icono('maletin'), descripcionDe(portal, c)) : null,
          web ? h('span', {}, icono('link'), h('a', { href: c.web, target: '_blank', rel: 'noopener' }, web)) : null),
        h('div', { class: 'fila' },
          grav ? h('span', { class: `chip ${grav[0]}`, title: (v.motivos || []).join(' · ') || 'Gravedad única del cliente' }, `Estado: ${grav[1]}`) : null,
          F.obj ? null : chipEstado(sem, textoSem),   // A4: con el semáforo del lunes, va en su fila (abajo)
          salud !== undefined && salud !== null ? h('span', { class: `chip ${semaforo(salud, { verde: 60, ambar: 40 })}`, title: 'Salud provisional (40 resultados + 30 atención + 30 arranque), a medias' }, `Salud ${salud}`) : chipEstado('gris', 'Salud sin dato'),
          (v.nuevo ?? c.nuevo) ? chipEstado('azul', 'Cliente nuevo') : null,
          F.alarmas.some(a => a.gravedad === 'rojo') ? h('a', { href: `#/en-rojo/${c.id}`, class: 'chip rojo', title: 'Ver los avisos rojos en «En rojo»' }, fmt.plural(F.alarmas.filter(a => a.gravedad === 'rojo').length, 'aviso rojo', 'avisos rojos')) : null,
          chipMedicion(F))),
      contactoCab),
    // 2b · A4: semáforo del lunes y objetivo del cliente (≤ 2 clics: abrir y elegir color / guardar)
    F.obj ? zonaA4(ctx, F, { sem, textoSem }) : null,
    // 3 · atajos
    h('div', { class: 'fila', style: fila100 },
      h('span', { class: 'titulo-seccion' }, 'Abrir en'),
      directos.map(r => atajo(r.url, ICONO_RECURSO[r.k] || 'ext', r.t.replace('Lista de ', ''))),
      extra.map(x => x.url ? atajo(x.url, ICO_EXTRA[x.k] || 'ext', NOMBRE_CORTO[x.k] || x.t)
        : h('span', { class: 'bt mini', 'aria-disabled': 'true', title: `${x.t}: falta emparejar el cliente con su cuenta. Lo arregla Mili.` }, icono(ICO_EXTRA[x.k] || 'ext'), `${NOMBRE_CORTO[x.k] || x.t} · falta emparejar`)),
      deskUrl ? atajo(deskUrl, 'inbox', 'Desk') : null),
    e >= 0 ? (() => { const b = barraEtapas(null, e); b.style.flexBasis = '100%'; return b; })() : null,
    copiloto);
}

// =================================================================== N14 · fallos de medición por fuente
// data/fuentes/hallazgos_medicion.json (auditoría de fuentes, N14), recortado por cliente en el servidor. Sin ese fichero,
// las alertas «Medición: …» del bloque de cada fuente de la ficha de E1. Rojo = la cifra es falsa o no existe; ámbar = parcial
// o cuenta doble; gris = falta un acceso (no engaña). Cada uno con su dueño y qué hacer.
const PESTANA_DE_FUENTE = { ga4: 'web', gsc: 'web', web: 'web', seranking: 'web', meta: 'resultados', ghl: 'resultados', captacion_ghl: 'resultados',
  google_ads: 'resultados', chat: 'chat', zadarma: 'comunicacion', desk: 'comunicacion', metricool: 'redes' };
const NOMBRE_FUENTE = { ga4: 'Analytics', gsc: 'Search Console', web: 'Web', seranking: 'SE Ranking', meta: 'Meta', ghl: 'GoHighLevel', captacion_ghl: 'GoHighLevel',
  google_ads: 'Google Ads', chat: 'Chat de ClickUp', zadarma: 'Zadarma', desk: 'Desk', metricool: 'Metricool' };
const DUENO_MEDICION = { web: 'Web', Agus: 'Agus', trafficker: 'Publicidad', SEO: 'SEO', E1: 'quien mantiene los datos' };   // F2: el equipo, con mayúscula
const QUE_HACER_MEDICION = {
  sin_acceso: 'Pedir acceso de lector para la cuenta de la app.',
  sin_etiqueta: 'Poner la etiqueta de Analytics en la web (o en su Tag Manager) y comprobar que llegan visitas.',
  doble_analytics: 'Dejar una sola etiqueta de Analytics en la web: quitar la sobrante y la antigua.',
  doble_conteo: 'Dejar una sola etiqueta que cuente cada visita.',
  consentimiento: 'Configurar el banner de cookies para que Analytics mida cuando la persona acepta.',
  web_caida: 'Arreglar la web (no abre o falla el certificado) y poner en la ficha la dirección buena.',
  pixel: 'Revisar el píxel de Meta en la web y en el administrador de eventos.',
  mal_emparejada: 'Emparejar el cliente con su cuenta correcta.',
  mezcla_webs: 'Separar las webs para que cada cifra sea de una sola.',
  dato_web: 'Corregir la web del cliente en su ficha.',
  subcuenta_duplicada: 'Quedarse con una subcuenta de GoHighLevel y archivar la otra.',
  cruce_probable: 'Confirmar que el emparejamiento es el bueno.',
  consultas_falsas: 'Revisar las búsquedas falsas antes de leer Search Console.',
};
const RANGO_MED = { rojo: 0, ambar: 1, gris: 2 };

function medicionDe(doc, hallazgos, id) {
  const lista = (hallazgos?.hallazgos || []).filter(x => x.cliente_id === id && x.estado === 'abierto');
  if (lista.length) return lista.map(x => ({ ...x })).sort((a, b) => (RANGO_MED[a.gravedad] ?? 3) - (RANGO_MED[b.gravedad] ?? 3));
  const out = [];   // sin el fichero: las alertas «Medición: …» de cada fuente de la ficha de E1
  for (const [k, f] of Object.entries(doc?.fuentes || {})) {
    for (const a of (f && f.alertas) || []) if (/^Medición:/.test(a.texto || '')) out.push({ id: a.id || `${k}-${out.length}`, fuente: a.fuente || k, texto: a.texto, dueno: a.dueno, gravedad: a.gravedad || 'ambar' });
  }
  return out.sort((a, b) => (RANGO_MED[a.gravedad] ?? 3) - (RANGO_MED[b.gravedad] ?? 3));
}
const duenoMed = x => DUENO_MEDICION[x.dueno] || x.dueno || 'sin dueño';

/** Resumen en la cabecera: «2 fallos de medición · lo arregla Web». Lleva a la pestaña de la fuente más grave. */
function chipMedicion(F) {
  const L = F.medicion || [];
  if (!L.length) return null;
  const fallos = L.filter(x => x.gravedad !== 'gris'), accesos = L.filter(x => x.gravedad === 'gris');
  const base = fallos.length ? fallos : accesos;
  const duenos = [...new Set(base.map(duenoMed))];
  const texto = fallos.length
    ? `${fallos.length} ${fallos.length === 1 ? 'fallo' : 'fallos'} de medición · lo arregla ${duenos.join(' y ')}`
    : `${accesos.length} ${accesos.length === 1 ? 'acceso' : 'accesos'} por pedir · ${duenos.join(' y ')}`;
  const ir = PESTANA_DE_FUENTE[base[0].fuente] || 'web';
  return h('button', { type: 'button', class: `chip ${fallos.some(x => x.gravedad === 'rojo') ? 'rojo' : fallos.length ? 'ambar' : 'gris'}`,
    title: `${base.map(x => `${NOMBRE_FUENTE[x.fuente] || x.fuente}: ${String(x.texto).replace(/^Medición:\s*/, '')}`).join('\n')}${fallos.length && accesos.length ? `\nAdemás, ${accesos.length} acceso${accesos.length === 1 ? '' : 's'} por pedir.` : ''}`,
    on: { click: () => F.irA?.(ir) } }, texto);
}

/** Arriba de la pestaña de cada fuente: los fallos de esa fuente, con dueño y qué hacer. */
function bloqueMedicion(ctx, F, pestana) {
  const L = (F.medicion || []).filter(x => (PESTANA_DE_FUENTE[x.fuente] || 'web') === pestana);
  if (!L.length) return null;
  const n = L.filter(x => x.gravedad !== 'gris').length;
  return panel({ titulo: n ? `Fallos de medición · ${n}` : 'Accesos por pedir', icono: 'alert',
    sub: 'Rojo: la cifra es falsa o no existe · ámbar: parcial o cuenta doble · gris: falta un acceso, no engaña. No se arreglan desde la app.' },
  h('div', { class: 'cuerpo pila' }, L.map(x => h('div', { class: 'pila', style: { gap: '4px', minWidth: '0' } },
    h('div', { class: 'fila', style: { minWidth: '0', flexWrap: 'wrap' } },
      chipEstado(x.gravedad === 'gris' ? 'gris' : x.gravedad, NOMBRE_FUENTE[x.fuente] || x.fuente),
      h('span', { style: { minWidth: '0', overflowWrap: 'anywhere' } }, String(x.texto).replace(/^Medición:\s*/, ''))),
    h('div', { class: 'meta-linea' },
      h('span', {}, icono('persona'), `Lo arregla: ${duenoMed(x)}`),
      h('span', {}, icono('check'), `Qué hacer: ${QUE_HACER_MEDICION[x.tipo] || 'Ver el detalle y arreglarlo en la herramienta de origen.'}`),
      x.prueba ? h('span', { title: x.prueba, style: { minWidth: '0', overflowWrap: 'anywhere' } }, icono('info'), `Prueba: ${x.prueba}`) : null)))));
}

// =================================================================== A4 · semáforo del lunes y objetivo del cliente
// Desde la cabecera, en dos clics: abrir y elegir el color (el color ES el botón de guardar) · abrir y «Guardar objetivo».
// Se guarda en la base de la app (cola «acciones», modo simulación, con rastro): no se escribe en ninguna herramienta.
// Pueden cargarlo su account, operaciones (su jefa) y dirección (regla «editar_objetivo_cliente», la misma en el servidor);
// el resto lo ve si ve la ficha, sin editar. Los costes solo los ve quien ve la inversión del cliente.
const COLOR_TXT = { verde: 'Verde', ambar: 'Ámbar', rojo: 'Rojo' };
const DESDE_TXT = { ficha: 'desde la ficha', 'clientes-nuevos': 'desde Clientes nuevos' };
const CAMPOS_FICHA = [
  { k: 'leads_mes', et: 'Leads al mes', dinero: false },
  { k: 'coste_lead', et: 'Coste por lead (€)', dinero: true },
  { k: 'coste_cita', et: 'Coste por cita (€)', dinero: true },
  { k: 'ventas_mes', et: 'Ventas al mes', dinero: false },
];
const quienCuando = (ctx, x) => (x ? `${ctx.nombre(x.quien) || x.quien} · ${fDiaHoraRO(x.cuando)}` : '');
const horaSeg = () => new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

function resumenObjetivo(o, veDinero) {
  if (!o?.cargado) return null;
  const partes = [o.leads_mes != null ? `${fmt.num(o.leads_mes)} leads/mes` : null,
    veDinero && o.coste_lead != null ? `${fmt.eur(o.coste_lead, o.coste_lead % 1 ? 2 : 0)} por lead` : null,
    veDinero && o.coste_cita != null ? `${fmt.eur(o.coste_cita, o.coste_cita % 1 ? 2 : 0)} por cita` : null,
    o.ventas_mes != null ? `${fmt.num(o.ventas_mes)} ventas/mes` : null].filter(Boolean);
  return partes.length ? partes.join(' · ') : 'cargado (costes solo para quien ve la inversión)';
}

function zonaA4(ctx, F, previo) {
  const caja = h('div', { class: 'pila', style: { flexBasis: '100%', minWidth: '0' } });
  F.pintarA4 = () => pintarA4(caja, ctx, F, previo);
  F.pintarA4();
  return caja;
}

async function guardarA4(ctx, F, cuerpo, aviso) {
  const r = await ctx.accion({ herramienta: 'app', objeto: F.c.id, cliente_id: F.c.id, ...cuerpo });
  F.obj = (await cargarObjetivos(ctx)).get(F.c.id) || {};
  F.a4msg = r?.local ? 'Guardado solo en este navegador (sin servidor)' : `${aviso} · queda en la base de la app y en el rastro (n.º ${r?.id ?? '—'})`;
  F.pintarA4();
  avisoFlotante(aviso);
}

function pintarA4(caja, ctx, F, previo) {
  const { c } = F;
  const O = F.obj || {};
  const edita = puedeEditar(ctx, c.id);                    // semáforo: su account, operaciones y dirección
  const editaObj = puedeEditar(ctx, c.id, 'objetivo');     // objetivo: además, proyectos y altas en los clientes en alta
  const lunes = lunesDeHoy();
  const s = O.semaforo;
  const s_hoy = s && s.semana === lunes ? s : null;
  const o = O.objetivo;
  const resumen = resumenObjetivo(o, F.ve.inversion);
  const abrir = cual => { F.a4 = F.a4 === cual ? null : cual; F.a4msg = null; F.pintarA4(); };
  const boton = (cual, ico, titulo, chip, detalle, tit, puede = edita) => (chip && Object.assign(chip.style, { whiteSpace: 'normal', minWidth: '0' }), h('button', {
    type: 'button', class: 'bt', 'aria-expanded': String(F.a4 === cual), title: tit,
    style: { whiteSpace: 'normal', textAlign: 'left', minWidth: '0', maxWidth: '100%', flexWrap: 'wrap' }, on: { click: () => abrir(cual) } },
  icono(ico), h('span', {}, titulo), chip, detalle ? h('span', { class: 'sub', style: { fontWeight: '400' } }, detalle) : null, icono(puede ? 'editar' : 'ojo')));

  const antes = previo?.textoSem && previo.textoSem !== 'Semáforo sin poner' ? ` Antes de la app: «${previo.textoSem.replace('Semáforo: ', '')}».` : '';
  const bSem = boton('semaforo', 'flag', 'Semáforo del lunes',
    s_hoy ? chipEstado(s_hoy.color, COLOR_TXT[s_hoy.color]) : chipEstado('gris', s ? 'Sin poner esta semana' : 'Sin poner'),
    s ? quienCuando(ctx, s) : null,
    `${s ? `Último: ${COLOR_TXT[s.color]}, puesto por ${quienCuando(ctx, s)}.` : 'Nadie lo ha puesto todavía.'}${antes} ${edita ? 'Pulsa para ponerlo.' : 'Pulsa para ver el historial.'}`);
  const bObj = boton('objetivo', 'target', 'Objetivo',
    o?.cargado ? chipEstado('azul', resumen) : chipEstado('ambar', editaObj ? 'Sin cargar · cargar' : 'Sin cargar'),
    o?.cargado ? quienCuando(ctx, o) : null,
    o?.cargado ? `Cargado por ${quienCuando(ctx, o)} ${DESDE_TXT[o.desde] || ''}. Lo leen Captación, Mi día y Clientes nuevos.` : 'Sin objetivo, Captación y Mi día juzgan con el techo general. Pulsa para cargarlo.', editaObj);

  const partes = [h('div', { class: 'fila', style: { minWidth: '0' } }, bSem, bObj)];
  if (F.a4 === 'semaforo') partes.push(editorSemaforo(ctx, F, edita, s, s_hoy, lunes));
  if (F.a4 === 'objetivo') partes.push(editorObjetivo(ctx, F, editaObj, o));
  caja.replaceChildren(...partes);
}

function cajaEditor(...hijos) {
  return h('div', { class: 'pila', role: 'region', 'data-a4-editor': '1', 'aria-label': 'Editor', style: { borderTop: '1px solid var(--line)', paddingTop: '12px', minWidth: '0' } }, ...hijos);
}
const lineaMeta = texto => h('p', { class: 'sub', style: { margin: '0' } }, texto);

function editorSemaforo(ctx, F, edita, s, sHoy, lunes) {
  const { c } = F;
  const hijos = [];
  if (edita) {
    const campo = campoTexto({ etiqueta: 'Una línea para el lunes (opcional)', placeholder: 'Qué ha pasado, el reto y el siguiente paso', valor: sHoy?.nota || '' });
    const input = campo.querySelector('input');
    input.maxLength = 140;
    const estado = h('span', { class: 'sub', role: 'status' }, F.a4msg || '');
    const elegir = color => h('button', { type: 'button', class: `bt${sHoy?.color === color ? ' pri' : ''}`, title: `Guardar el semáforo en ${COLOR_TXT[color].toLowerCase()} con la nota`,
      on: { click: async e => {
        const nota = input.value.trim();
        if (RE_IMPORTE.test(nota)) { RE_IMPORTE.lastIndex = 0; estado.textContent = 'Sin importes en la nota: la ve todo el que abre la ficha.'; return; }
        RE_IMPORTE.lastIndex = 0;
        e.currentTarget.disabled = true;
        try {
          await guardarA4(ctx, F, { tipo: TIPO_SEMAFORO, texto: `Semáforo del lunes de ${c.nombre}: ${COLOR_TXT[color]} (${horaSeg()})`, vista_previa: { color, nota } },
            `Semáforo en ${COLOR_TXT[color].toLowerCase()}`);
        } catch (err) { estado.textContent = `No se ha guardado: ${err?.message || err}`; e.currentTarget.disabled = false; }
      } } }, chipEstado(color, COLOR_TXT[color]));
    hijos.push(campo, h('div', { class: 'fila' }, h('span', { class: 'titulo-seccion' }, 'Ponlo en'), ['verde', 'ambar', 'rojo'].map(elegir)), estado);
  } else {
    hijos.push(vacioLinea('Lo ponen su account, operaciones y dirección. Tú lo ves, sin editar.', { icono: 'ojo' }));
  }
  hijos.push(lineaMeta(sHoy ? `Esta semana: ${COLOR_TXT[sHoy.color]}, puesto por ${quienCuando(ctx, sHoy)}.` : s ? `Esta semana está sin poner. El último lo puso ${quienCuando(ctx, s)}.` : 'Todavía nadie lo ha puesto.'));
  // Historial semanal: las 8 últimas semanas (lunes), con las que quedaron sin poner.
  const porSemana = new Map((F.obj?.semanas || []).map(x => [x.semana, x]));
  const semanas = [];
  const d = new Date(`${lunes}T12:00:00Z`);
  for (let i = 0; i < 8; i++) { semanas.push(d.toISOString().slice(0, 10)); d.setUTCDate(d.getUTCDate() - 7); }
  hijos.push(h('span', { class: 'titulo-seccion' }, 'Historial por semana'),
    h('div', { class: 'pila', style: { gap: '4px' } }, semanas.map(sem => {
      const x = porSemana.get(sem);
      return h('div', { class: 'fila', style: { minWidth: '0', flexWrap: 'wrap' } },
        h('span', { class: 'sub', style: { minWidth: '112px' } }, `Lunes ${fDiaRO(sem)}`),
        x ? chipEstado(x.color, COLOR_TXT[x.color]) : chipEstado('gris', 'Sin poner'),
        x?.nota ? h('span', { style: { minWidth: '0', overflowWrap: 'anywhere' } }, x.nota) : null,
        x ? h('span', { class: 'sub' }, quienCuando(ctx, x)) : null);
    })));
  return cajaEditor(...hijos);
}

function editorObjetivo(ctx, F, edita, o) {
  const { c } = F;
  const hijos = [];
  const veDinero = F.ve.inversion;
  if (edita) {
    const campos = CAMPOS_FICHA.map(x => {
      const el = campoTexto({ etiqueta: x.et, tipo: 'number', valor: o?.[x.k] ?? '' });
      const inp = el.querySelector('input');
      inp.min = '0'; inp.step = x.dinero ? '0.01' : '1'; inp.setAttribute('inputmode', 'decimal'); inp.dataset.k = x.k;
      return el;
    });
    const estado = h('span', { class: 'sub', role: 'status' }, F.a4msg || '');
    const guardar = h('button', { type: 'button', class: 'bt pri', on: { click: async () => {
      const v = Object.fromEntries(campos.map(el => { const i = el.querySelector('input'); return [i.dataset.k, i.value === '' ? null : Number(i.value)]; }));
      if (Object.values(v).some(x => x !== null && (!Number.isFinite(x) || x < 0))) { estado.textContent = 'Solo números de 0 en adelante.'; return; }
      if (Object.values(v).every(x => x === null) && !o?.cargado) { estado.textContent = 'Rellena al menos un campo.'; return; }
      if (CAMPOS_FICHA.every(x => (v[x.k] ?? null) === (o?.[x.k] ?? null))) { estado.textContent = 'No has cambiado nada.'; return; }
      guardar.disabled = true;
      try { await guardarA4(ctx, F, { tipo: TIPO_OBJETIVO, texto: `Objetivo de ${c.nombre} (${horaSeg()})`, vista_previa: v }, 'Objetivo guardado'); }
      catch (err) { estado.textContent = `No se ha guardado: ${err?.message || err}`; guardar.disabled = false; }
    } } }, icono('ok'), 'Guardar objetivo');
    hijos.push(h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(144px, 1fr))', gap: '12px', minWidth: '0' } }, campos),
      h('div', { class: 'fila' }, guardar, estado));
  } else {
    hijos.push(vacioLinea('Lo cargan su account, operaciones y dirección (en los clientes en alta, también proyectos y el técnico de altas). Tú lo ves, sin editar.', { icono: 'ojo' }));
    if (o?.cargado) hijos.push(h('div', { class: 'meta-linea' }, CAMPOS_FICHA.filter(x => !x.dinero || veDinero).map(x => h('span', {}, `${x.et.replace(' (€)', '')}: ${o[x.k] == null ? 'sin dato' : x.dinero ? fmt.eur(o[x.k], o[x.k] % 1 ? 2 : 0) : fmt.num(o[x.k])}`)),
      veDinero ? null : h('span', {}, 'Costes: solo quien ve la inversión')));
  }
  const extra = [o?.citas_mes != null ? `${fmt.num(o.citas_mes)} citas al mes` : null, veDinero && o?.inversion_mes != null ? `inversión de ${fmt.eur(o.inversion_mes)} al mes` : null].filter(Boolean);
  if (extra.length) hijos.push(lineaMeta(`Además, de Clientes nuevos: ${extra.join(' y ')}.`));
  hijos.push(lineaMeta(o?.cargado ? `Cargado por ${quienCuando(ctx, o)} ${DESDE_TXT[o.desde] || ''}.` : 'Sin objetivo cargado: Captación y Mi día juzgan con el techo general (35 € por lead y red de seguridad de 100 € por cita).'),
    lineaMeta('Una sola fuente: lo leen Captación, Mi día (el número que manda) y Clientes nuevos. Captación y Mi día lo usan desde la próxima actualización de datos.'));
  const hist = (F.obj?.historial_objetivo || []).slice(0, 5);
  if (hist.length > 1 || (hist.length && edita)) {
    hijos.push(h('span', { class: 'titulo-seccion' }, 'Cambios'), h('div', { class: 'pila', style: { gap: '4px' } }, hist.map(x => h('div', { class: 'fila', style: { minWidth: '0', flexWrap: 'wrap' } },
      h('span', { class: 'sub' }, `${quienCuando(ctx, x)} ${DESDE_TXT[x.desde] || ''}`),
      h('span', { style: { minWidth: '0', overflowWrap: 'anywhere' } }, Object.entries(x.campos || {}).filter(([k]) => veDinero || !/^(coste|inversion)/.test(k))
        .map(([k, v]) => `${({ leads_mes: 'leads/mes', coste_lead: 'por lead', coste_cita: 'por cita', ventas_mes: 'ventas/mes', citas_mes: 'citas/mes', inversion_mes: 'inversión/mes' })[k]}: ${v == null ? 'vacío' : /^(coste|inversion)/.test(k) ? fmt.eur(v, v % 1 ? 2 : 0) : fmt.num(v)}`).join(' · ') || 'sin cambios visibles')))));
  }
  return cajaEditor(...hijos);
}

/** Correos del cliente sin contestar: la regla ÚNICA de la Bandeja (data/bandeja/por_cliente.json: sin automáticos ni
 *  ruido, horas y días laborables). La lista de cada correo sale de su copia del mismo minuto (data/ficha/correos.json).
 *  Ya no se cae al bloque de Desk de las 07:00 (auditoría 28, E-07): sin ese fichero, «sin dato» en gris. */
function correosCliente(F) {
  if (F.admin || !F.porCliente) return null;
  const pc = F.porCliente.fila;             // sin fila = el cliente no tiene nada sin contestar
  const lista = (F.correos?.lista || []).map(x => ({ numero: x.numero, asunto: x.asunto, horas: x.horas,
    dias: x.dias_laborables ?? Math.floor((x.horas || 0) / 24), url: x.url, auto: x.auto, queja: x.queja, desde: x.desde, gravedad: x.gravedad }))
    .sort((a, b) => (b.queja - a.queja) || b.horas - a.horas);
  const del_cliente = lista.filter(x => !x.auto);
  // Si la copia no casa con el resumen (horas distintas), manda el resumen: la lista se avisa como «de las HH:MM».
  const desfase = F.correos?.generado && F.porCliente.generado && F.correos.generado !== F.porCliente.generado;
  const desk = F.porCliente.fuentes?.desk;
  return {
    fuente: 'Bandeja', hora: F.porCliente.generado, viejo: desk?.estado === 'dato_viejo', notaFuente: desk?.estado === 'dato_viejo' ? desk.nota : null,
    total: pc ? pc.sin_contestar : 0, mas48: pc ? pc.mas_48 : 0, entre24y48: pc ? pc.entre_24_48 : 0, quejas: pc ? pc.quejas : 0,
    horasMax: pc ? pc.horas_max : 0, diasMax: pc ? pc.dias_laborables_max : 0, masAntiguo: pc?.mas_antiguo || null,
    llamadasSinDevolver: pc ? pc.llamadas_sin_devolver : 0,
    del_cliente, automaticos: lista.filter(x => x.auto), llamadas: F.correos?.llamadas || [],
    listaHora: desfase ? F.correos.generado : null,
  };
}

/** Ventana de Meta para el periodo elegido: 7 días cerrados (sin hoy) frente a los 7 anteriores, o los 30 últimos días de la serie. */
function ventanaMeta(md, n, inversion) {
  const serie = (md.serie || []).filter(x => Array.isArray(x.meta));
  if (n === 7) return { leads: md.leads['7d'], leadsAnt: md.leads['7d_prev'], gasto: md.gasto?.['7d'], gastoAnt: md.gasto?.['7d_prev'], cpl: md.cpl?.['7d'], cplAnt: md.cpl?.['7d_prev'], comp: 'frente a los 7 anteriores' };
  const l = ventana(serie, 30, x => x.meta[1]); const g = inversion ? ventana(serie, 30, x => x.meta[0]) : {};
  return { leads: l.actual, leadsAnt: null, gasto: g.actual, cpl: l.actual && g.actual ? g.actual / l.actual : null,
    comp: `Septiembre completo: ${fmt.num(md.leads.mes_anterior)} leads${inversion && md.gasto ? ` · ${fmt.eur(md.gasto.mes_anterior)}` : ''}` };
}

/** Cuota: la de la fuente única (Airtable de octubre, la misma que Dinero por cliente); si no la hay, la del libro. Solo si la ve. */
function cuotaFicha(F) {
  if (!F.ve.cuota) return null;
  // Ronda 8 (E0): fuente única de la cuota = fuentes_dinero/cuotas.json, que build_data deja en el cliente (c.cuota_fuente).
  if (String(F.c.cuota_fuente || '').startsWith('fuentes_dinero/cuotas.json')) return F.c.cuota != null ? { valor: F.c.cuota, fuente: F.c.cuota_fuente.replace('fuentes_dinero/cuotas.json · ', '') } : null;
  if (F.portal?.cuota != null) return { valor: F.portal.cuota, fuente: F.portal.cuota_fuente || 'Airtable' };
  if (F.c.cuota != null) return { valor: F.c.cuota, fuente: 'libro de clientes (sin línea en Airtable)' };
  return null;
}

/** Segunda línea del selector: «Account: Lucía · tú llevas la publicidad» (nunca «Lucía · tuyo» para quien no es su account). */
function detalleSelector(ctx, x) {
  const v = ctx.verdad ? ctx.verdad(x.id) : null;
  const acc = v?.account ? ctx.nombre(v.account) : (x.responsable || 'sin account');
  const SILLA = { account: 'eres su account', trafficker: 'tú llevas la publicidad', crm: 'tú llevas el CRM', seo: 'tú llevas el SEO', web: 'tú llevas la web', redes: 'tú llevas las redes', outreach: 'tú llevas el outreach' };
  const mias = Object.entries(ctx.carteraPorSilla || {}).filter(([, set]) => set?.has?.(x.id)).map(([s]) => SILLA[s]).filter(Boolean);
  return `Account: ${acc}${mias.length ? ' · ' + mias.join(', ') : ''}`;
}

function contadores(F) {
  const t = fuente(F.doc, 'tareas')?.datos || {};
  const rojas = F.alarmas.filter(a => a.gravedad === 'rojo').length;
  const cc = correosCliente(F);
  const pend = cc ? cc.total : 0;
  const v = F.contactos?.valor;
  const nCont = v ? (v.personas || []).filter(p => !p.externo).length : 0;
  const faltan = (F.portal?.recursos || []).filter(r => !r.url).length;
  return {
    resumen: rojas ? { cuenta: rojas, cuentaEstado: 'rojo' } : {},
    comunicacion: pend ? { cuenta: pend, cuentaEstado: cc.mas48 ? 'rojo' : '' } : {},
    trabajo: t.revision_mas_48h ? { cuenta: t.revision_mas_48h, cuentaEstado: 'rojo' } : {},
    contactos: nCont ? { cuenta: nCont, cuentaEstado: v.sin_movil ? 'rojo' : '' } : {},
    accesos: faltan ? { cuenta: faltan } : {},
  };
}

/** Tarjeta «Correos del cliente sin contestar» (Resumen y Comunicación): cifras de la Bandeja, la misma regla. */
function tileCorreos(cc, extra = {}) {
  if (!cc) return tile({ icono: 'mail', etiqueta: 'Correos sin contestar', valor: null, contexto: 'Sin dato: falta el resumen de la Bandeja', ...extra });
  return tile({ icono: 'mail', etiqueta: 'Correos sin contestar', valor: fmt.num(cc.total),
    unidad: cc.total ? `el más antiguo, ${cc.diasMax} ${cc.diasMax === 1 ? 'día laborable' : 'días laborables'}` : '',
    estado: !cc.total ? 'verde' : cc.mas48 ? 'rojo' : cc.entre24y48 ? 'ambar' : 'verde',
    contexto: cc.total ? `${cc.mas48} de más de 48 h${cc.quejas ? ` · ${cc.quejas} ${cc.quejas === 1 ? 'queja' : 'quejas'}` : ''}` : 'Al día',
    frescura: { fuente: cc.fuente, fecha: cc.hora, estado: cc.viejo ? 'viejo' : 'ok' }, ...extra });
}

// =================================================================== pestañas
const PINTAR = {
  // ------------------------------------------------------------- Resumen
  resumen(z, ctx, F, irA) {
    const { c, doc } = F;
    const desk = fuente(doc, 'desk'), meta = fuente(doc, 'meta'), capt = fuente(doc, 'captacion_ghl'), tar = fuente(doc, 'tareas'),
      reu = fuente(doc, 'reuniones'), ga = fuente(doc, 'ga4'), hor = fuente(doc, 'horas'), cart = fuente(doc, 'cartera');
    const L = [];
    // 1 · lo de cada día: correos del cliente sin contestar (los de la Bandeja: verde < 24 h, ámbar 24-48 h, rojo > 48 h)
    const cc = correosCliente(F);
    const pend = cc ? cc.del_cliente : [];
    if (!F.admin) L.push(tileCorreos(cc, { ir: 'Ver correos', alPulsar: () => irA('comunicacion') }));
    // 2 · resultados del cliente (cliente primero), con el periodo elegido arriba
    const n = +F.periodo();
    const md = meta?.datos || {};
    if (pintable(meta) && md.leads) {
      const W = ventanaMeta(md, n, F.ve.inversion);
      L.push(tile({ icono: 'target', etiqueta: `Leads · ${n} días`, valor: fmt.num(W.leads), comparacion: W.leadsAnt != null ? { delta: variacion(W.leads, W.leadsAnt), pct: true, texto: W.comp } : { texto: W.comp },
        frescura: frescuraDe(meta), ir: 'Ver resultados', alPulsar: () => irA('resultados') }));
      if (F.ve.inversion && md.cpl) {
        const obj = F.obj?.objetivo?.coste_lead;   // A4: el objetivo del cliente, de un solo sitio
        L.push(tile({ icono: 'euro', etiqueta: `Coste por lead · ${n} días`, valor: W.cpl != null ? `${fmt.num(W.cpl, 2)} €` : null,
          estado: W.cpl == null ? 'gris' : semaforo(W.cpl, { verde: obj || 45, ambar: obj ? obj * 1.3 : 100, mejorSi: 'bajo' }),
          comparacion: W.cplAnt != null ? { delta: variacion(W.cpl, W.cplAnt), pct: true, texto: 'frente a los 7 anteriores', mejorSi: 'bajo' } : null,
          contexto: obj ? `Objetivo del cliente: ${fmt.num(obj, 2)} €` : 'Sin objetivo del cliente: rojo si pasa de 100 €', frescura: frescuraDe(meta), alPulsar: () => irA('resultados') }));
      }
    } else L.push(tile({ icono: 'target', etiqueta: `Leads · ${n} días`, valor: null, contexto: meta?.nota || 'Sin cuenta de Meta enlazada', alPulsar: () => irA('resultados') }));
    const ci = capt?.datos?.citas;
    const kc = n === 7 ? '7d' : 'mes_anterior';
    if (pintable(capt) && ci) L.push(tile({ icono: 'cal', etiqueta: n === 7 ? 'Citas · 7 días' : 'Citas · septiembre', valor: fmt.num(ci[kc]?.agendadas), estado: (ci[kc]?.agendadas || 0) === 0 && (md.leads?.[n === 7 ? '7d' : 'mes_anterior'] || 0) > 0 ? 'ambar' : '',
      contexto: ci[kc]?.asistencia_pct != null ? `Asistencia ${fmt.pct(ci[kc].asistencia_pct)} · verde desde el 75 %` : 'En su calendario de GoHighLevel', frescura: frescuraDe(capt), alPulsar: () => irA('resultados') }));
    // 3 · trabajo
    const td = tar?.datos || {};
    L.push(tile({ icono: 'clock', etiqueta: 'Revisiones de más de 48 h', valor: pintable(tar) ? fmt.num(td.revision_mas_48h || 0) : null, unidad: td.revision_total ? `de ${td.revision_total} en revisión` : '',
      estado: semaforo(td.revision_mas_48h || 0, { verde: 0, ambar: 3, mejorSi: 'bajo' }), contexto: `${fmt.num(td.vencidas)} tareas vencidas`, frescura: frescuraDe(tar), ir: 'Ver trabajo', alPulsar: () => irA('trabajo') }));
    const rd = reu?.datos || {};
    L.push(tile({ icono: 'video', etiqueta: 'Días sin reunión', valor: rd.dias_sin_reunion ?? null, estado: rd.dias_sin_reunion == null ? 'gris' : semaforo(rd.dias_sin_reunion, { verde: 30, ambar: 35, mejorSi: 'bajo' }),
      contexto: rd.ult_reunion ? `Última: ${fDiaRO(rd.ult_reunion)} · rojo > 35 días` : 'Sin reuniones registradas', frescura: frescuraDe(reu), alPulsar: () => irA('comunicacion') }));
    if (pintable(ga)) L.push(tile({ icono: 'users', etiqueta: 'Visitas a la web · 30 días', valor: fmt.num(ga.datos.actual?.usuarios), unidad: 'usuarios',
      comparacion: { delta: variacion(ga.datos.actual?.usuarios, ga.datos.anterior?.usuarios), pct: true, texto: 'frente a los 30 anteriores' }, frescura: frescuraDe(ga), alPulsar: () => irA('web') }));
    if (F.ve.horas.ok && hor?.datos && F.ve.horas.nivel !== 'resumen') {
      const hd = hor.datos;
      L.push(tile({ icono: 'clock', etiqueta: 'Horas · septiembre', valor: fmt.num(hd.horas_mes_ant, 1), unidad: hd.horas_presup_mes ? `de ${fmt.num(hd.horas_presup_mes)} h pautadas` : 'h',
        estado: hd.pct_horas == null ? '' : hd.pct_horas > 130 ? 'ambar' : '', contexto: hd.pct_horas != null ? `${fmt.pct(hd.pct_horas)} de lo pautado · solo como aviso` : 'Sin horas pautadas',
        medible: 'medias', medibleDetalle: hor.nota, frescura: frescuraDe(hor), alPulsar: () => irA('trabajo') }));
    }
    z.append(rejilla(L));

    // La cuenta de Meta no está activa (Concilia: «pago pendiente»): sale aquí, no solo en Captación
    if (pintable(meta) && md.estado_cuenta && md.estado_cuenta !== 'activa')
      z.append(panel({ titulo: 'Lo primero hoy', icono: 'alert' }, listaLoPrimero([{ estado: 'rojo', icono: 'alert',
        motivo: `La cuenta de Meta está en «${md.estado_cuenta}»: los anuncios no salen`, detalle: 'Hasta que se pague o se reactive, el cliente no recibe leads.',
        botones: [recursoBoton(F, 'metaAds', 'Abrir en Meta')] }])));
    // Cifras del mismo cliente tomadas a horas muy distintas: se avisa (más de 6 h entre fuentes)
    const horas = ['desk', 'meta', 'tareas', 'ga4', 'captacion_ghl', 'zadarma'].map(k => fuente(doc, k)).filter(f => pintable(f) && f.hora).map(f => ({ f: f.fuente, t: new Date(f.hora.replace(' ', 'T')) }));
    if (cc?.hora) horas.push({ f: 'Bandeja', t: new Date(String(cc.hora).replace(' ', 'T')) });
    if (horas.length > 1) {
      const ord = horas.sort((a, b) => a.t - b.t); const dif = (ord.at(-1).t - ord[0].t) / 36e5;
      if (dif > 6) z.append(avisoParcial(`Las cifras de esta ficha se tomaron a horas distintas: ${ord[0].f} a las ${ord[0].t.toTimeString().slice(0, 5)} y ${ord.at(-1).f} a las ${ord.at(-1).t.toTimeString().slice(0, 5)}. La hora va al pie de cada cifra.`, { tipo: 'info' }));
    }
    // Nota de Tomás o de Mili si el cliente está en rojo a mano
    const rm = cart?.datos?.rojo_manual;
    if (rm) z.append(avisoParcial(`${rm.motivo}${rm.nota_tomas ? ` Tomás: «${rm.nota_tomas}»` : ''}`, { titulo: `En rojo a mano (${rm.fuente || 'Mili'}).` }));
    // Finanzas v3 (3-oct): si el cliente tiene un impago, su equipo lo sabe; el importe solo llega a quien ve la cuota (servir.py)
    const avImp = h('div', { hidden: true }); z.append(avImp);
    cargarModulo(ctx, 'finanzas/impagos_clientes').then(di => {
      const x = (di?.clientes || []).find(y => y.cliente_id === c.id);
      if (!x) return avImp.remove();
      avImp.replaceWith(avisoParcial(`${x.vencidas === 1 ? 'Tiene 1 factura vencida' : `Tiene ${x.vencidas} facturas vencidas`} sin cobrar (la más antigua, de hace ${x.dias_max} días)${typeof x.cuota_vencida === 'number' ? ` · ${fmt.eur(x.cuota_vencida)}` : ''}. ${x.texto}`, { titulo: 'Impago.' }));
    });

    // Qué hay que mover hoy + últimos movimientos
    const movs = [];
    for (const x of pend.slice(0, 3)) movs.push({ f: x.desde || '', icono: 'mail', estado: x.horas > 48 ? 'rojo' : 'ambar', texto: h('span', { title: `${x.numero} · ${x.asunto}` }, `${x.numero} · ${x.asunto}`), extra: h('span', { title: `${x.dias} días laborables sin respuesta` }, `${x.dias} días sin respuesta`), href: x.url });   // F7: cabe en la fila a 1024
    for (const r of (rd.historial || []).slice(-4)) movs.push({ f: r.fecha, icono: 'video', texto: h('span', { title: r.asunto || '' }, r.asunto), extra: `${fDiaRO(r.fecha)} · ${r.quien || r.fuente}` });
    const inf = fuente(doc, 'informes')?.datos || {};
    for (const [mes, x] of Object.entries(inf)) if (x?.fecha_envio) movs.push({ f: x.fecha_envio, icono: 'doc', estado: 'verde', texto: `Informe de ${mes === 'ago' ? 'agosto' : mes === 'sep' ? 'septiembre' : mes} enviado`, extra: fDiaRO(x.fecha_envio), href: x.url });
    for (const t of (fuente(doc, 'tareas')?.datos?.en_revision_detalle || []).slice(0, 2)) movs.push({ f: '', icono: 'check', estado: t.dias > 2 ? 'ambar' : 'gris', texto: h('span', { title: t.nombre || '' }, t.nombre), extra: `${t.estado} · ${t.dias} d`, href: t.url });
    movs.sort((a, b) => String(b.f).localeCompare(String(a.f)));

    z.append(h('div', { class: 'dos' },
      panel({ titulo: 'Qué hay que mover hoy', icono: 'zap', sub: F.alarmas.length ? `${F.alarmas.length} ${F.alarmas.length === 1 ? 'aviso' : 'avisos'}: lo más grave arriba` : 'Avisos del panel de Mili para este cliente' },
        h('div', { class: 'cuerpo' }, listaLoPrimero(F.alarmas.slice(0, 7).map(a => ({
          estado: a.gravedad, icono: a.gravedad === 'rojo' ? 'alert' : 'clock', motivo: a.tipo,
          // F1: el detalle va en un solo <span> (en la fila flexible, los «…» sueltos se comían los espacios); F9: «Escalar a Mili:».
          detalle: h('span', {}, a.texto !== undefined ? `${fechasEnTexto(a.texto)}${a.accion ? ` — ${String(a.accion).replace(/^Escalar:\s*([^:]{2,30}):\s*/, 'Escalar a $1: ')}` : ''}` : 'El detalle lo ve quien lleva el cliente.'),
          botones: [
            a.enlace ? h('a', { class: 'bt mini', href: a.enlace, target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir la prueba') : null,
            botonConfirmar({ texto: 'Marcar visto', pregunta: '¿Lo has visto?', confirmar: 'Sí, visto', mini: true, soloLectura: ctx.soloLectura,
              alConfirmar: async () => { await ctx.rastro({ accion: 'alarma_vista', objeto: a.id, detalle: `${F.c.id} · ${a.tipo}` }); return 'Visto · queda en el rastro'; } }),
          ],
        })), { vacio: { titulo: 'Todo en orden', porque: 'Este cliente no tiene avisos hoy.', celebrar: true } }))),
      h('div', { class: 'pila' },
        panel({ titulo: 'Últimos movimientos', icono: 'hist', sub: 'Correos, reuniones, informes y revisiones' },
          h('div', { class: 'cuerpo' }, listaConIcono(movs.slice(0, 7), { vacio: { icono: 'hist', titulo: 'Sin movimientos registrados' } }))),
        panelEquipo(ctx, F))));
    // V2 (B-A4): a 390 la frescura más larga («Reuniones (CRM, Fathom y verificación manual)») desbordaba 1 px: que parta línea
    z.append(h('div', { class: 'fila', style: { minWidth: '0' } }, h('span', { class: 'sub' }, 'Hora del dato:'), ...['desk', 'meta', 'tareas', 'reuniones', 'ga4'].map(k => { const el = frescuraEl(fuente(doc, k)); if (el) { el.style.whiteSpace = 'normal'; el.style.maxWidth = '100%'; } return el; }).filter(Boolean)));
  },

  // ------------------------------------------------------------- Contactos
  contactos(z, ctx, F) { pintarContactos(z, ctx, F); },

  // ------------------------------------------------------------- Resultados
  resultados(z, ctx, F) {
    const { doc } = F;
    const p = F.periodo(), n = +p;
    const meta = fuente(doc, 'meta'), capt = fuente(doc, 'captacion_ghl'), ghl = fuente(doc, 'ghl'), snov = fuente(doc, 'snov'), gads = fuente(doc, 'google_ads');
    // ---- Meta ----
    const bloqueMeta = [];
    if (pintable(meta) && meta.datos?.leads) {
      const md = meta.datos;
      const serie = (md.serie || []).filter(x => Array.isArray(x.meta));
      const L = ventanaMeta(md, n, F.ve.inversion);
      let metrica = 'leads';
      const grafico = h('div');
      const pintarGrafico = () => grafico.replaceChildren(graficoSerie({ titulo: metrica === 'leads' ? 'Leads por día (Meta)' : 'Gasto por día (Meta)', alto: 160,
        puntos: serie.slice(-Math.max(n, 14)).map(x => ({ x: x.d, y: metrica === 'leads' ? x.meta[1] : x.meta[0] })), formato: metrica === 'leads' ? (v => fmt.num(v)) : (v => `${fmt.num(v)} €`) }));
      const tl = [];
      const tLeads = tile({ icono: 'target', etiqueta: `Leads · ${n} días`, valor: fmt.num(L.leads), activo: true,
        comparacion: L.leadsAnt != null ? { delta: variacion(L.leads, L.leadsAnt), pct: true, texto: L.comp } : { texto: L.comp }, frescura: frescuraDe(meta),
        alPulsar: () => { metrica = 'leads'; tLeads.setAttribute('aria-pressed', 'true'); tGasto?.setAttribute('aria-pressed', 'false'); pintarGrafico(); } });
      tl.push(tLeads);
      let tGasto = null;
      if (F.ve.inversion && md.gasto) {
        tGasto = tile({ icono: 'euro', etiqueta: `Gasto · ${n} días`, valor: fmt.eur(L.gasto), activo: false,
          comparacion: L.gastoAnt != null ? { delta: variacion(L.gasto, L.gastoAnt), pct: true, texto: 'frente a los 7 anteriores', mejorSi: 'bajo' } : null,
          contexto: md.presupuesto?.aprobado ? `Presupuesto del mes: ${fmt.eur(md.presupuesto.aprobado)} (${md.presupuesto.origen})` : null,
          alPulsar: () => { metrica = 'gasto'; tGasto.setAttribute('aria-pressed', 'true'); tLeads.setAttribute('aria-pressed', 'false'); pintarGrafico(); } });
        tl.push(tGasto);
        const obj = F.obj?.objetivo?.coste_lead;   // A4: el objetivo del cliente, de un solo sitio
        tl.push(tile({ icono: 'zap', etiqueta: `Coste por lead · ${n} días`, valor: L.cpl != null ? `${fmt.num(L.cpl, 2)} €` : null,
          estado: L.cpl == null ? 'gris' : semaforo(L.cpl, { verde: obj || 45, ambar: obj ? obj * 1.3 : 100, mejorSi: 'bajo' }),
          comparacion: L.cplAnt != null ? { delta: variacion(L.cpl, L.cplAnt), pct: true, texto: 'frente a los 7 anteriores', mejorSi: 'bajo' } : null,
          contexto: obj ? `Objetivo del cliente: ${fmt.num(obj, 2)} €` : 'Sin objetivo del cliente: rojo si pasa de 100 €' }));
      }
      const meta1 = (md.metas || [])[0];
      if (meta1) tl.push(tile({ icono: 'flag', etiqueta: 'Meta de leads del mes', valor: fmt.num(meta1.logrado), unidad: `de ${fmt.num(meta1.cantidad)}`, estado: meta1.pct >= (new Date().getDate() / 30 * 100) ? 'verde' : 'ambar',
        contexto: `Septiembre: ${fmt.pct(meta1.septiembre_pct)} de la meta · ${meta1.origen}` }));
      pintarGrafico();
      const campanas = md.campanas || [];
      bloqueMeta.push(rejilla(tl), h('div', { class: 'dos' },
        panel({ titulo: 'Meta Ads por día', icono: 'grafico', sub: 'Pulsa «Leads» o «Gasto» arriba para cambiar el gráfico', acciones: recursoBoton(F, 'metaAds', 'Abrir en Meta') }, h('div', { class: 'cuerpo' }, grafico)),
        panel({ titulo: 'Campañas', icono: 'megafono', sub: `${campanas.length} con actividad · últimos 7 días` },
          tablaApilable({ filas: campanas, vacio: { titulo: 'Ninguna campaña de Meta gastó en este periodo', texto: 'Si debería haber anuncios en marcha, lo revisa su trafficker.' }, columnas: [
            { clave: 'campana', titulo: 'Campaña', principal: true },
            { clave: 'leads_7d', titulo: 'Leads', num: true, celda: x => fmt.num(x.leads_7d) },
            ...(F.ve.inversion ? [{ clave: 'cpl_7d', titulo: 'Coste/lead', num: true, celda: x => (x.cpl_7d != null ? `${fmt.num(x.cpl_7d, 2)} €` : '—') }] : []),
            { clave: 'leads_mes_anterior', titulo: 'Septiembre', num: true, celda: x => fmt.num(x.leads_mes_anterior) },
          ] }))));
      const avisos = md.avisos || [];
      if (avisos.length) bloqueMeta.push(panel({ titulo: 'Avisos de captación', icono: 'alert', sub: 'De la Torre de control (captacion.json)' },
        h('div', { class: 'cuerpo' }, listaConIcono(avisos.map(a => ({ icono: a.clase_id === 'integracion' ? 'plug' : a.clase_id === 'dato' ? 'info' : 'alert', estado: a.clase_id === 'integracion' ? 'rojo' : 'ambar', texto: a.texto, extra: a.clase }))))));
    } else bloqueMeta.push(panel({ titulo: 'Meta Ads', icono: 'target' }, h('div', { class: 'cuerpo' }, huecoFuente(meta, { icono: 'target', quien: 'Vale (publicidad)' }))));
    z.append(...bloqueMeta);

    // ---- Embudo del CRM del cliente (GHL) ----
    const col = [];
    if (pintable(capt) && capt.datos?.embudo) {
      const e = capt.datos.embudo, fu = e.funnel || {}, ci = capt.datos.citas || {};
      const v = n === 7 ? ci['7d'] || {} : ci['mes_anterior'] || {};
      col.push(panel({ titulo: 'Embudo en su GoHighLevel', icono: 'cap', sub: `${fmt.num(e.contactos_90d)} contactos en 90 días · ${fmt.num(e.abiertas_total)} oportunidades abiertas` },
        h('div', { class: 'cuerpo pila' },
          barras([['Nuevo', fu.nuevo], ['Seguimiento', fu.seguimiento], ['Cita', fu.cita], ['Presupuesto', fu.presupuesto], ['Cerrado', fu.cerrado, 'verde'], ['Descartado', fu.descartado, 'rojo']]),
          h('div', { class: 'meta-linea' },
            h('span', {}, icono('cal'), `Citas ${n === 7 ? '7 días' : 'septiembre'}: ${fmt.num(v.agendadas)} agendadas · ${fmt.num(v.celebradas)} celebradas`),
            v.asistencia_pct != null ? h('span', {}, icono('users'), `Asistencia ${fmt.pct(v.asistencia_pct)}`) : null,
            e.estancados_72h ? h('span', {}, icono('clock'), `${e.estancados_72h} parados más de 72 h`) : null),
          capt.datos.coste_por_cita?.nota ? h('p', { class: 'sub' }, capt.datos.coste_por_cita.nota) : null,
          frescuraEl(capt))));
    } else if (pintable(ghl)) {
      const g = ghl.datos;
      col.push(panel({ titulo: 'Su GoHighLevel', icono: 'cap' }, h('div', { class: 'cuerpo' }, barras([['Contactos', g.contactos], ['Abiertas', g.opp_open, 'ambar'], ['Ganadas', g.opp_won, 'verde'], ['Perdidas', g.opp_lost, 'rojo']]))));
    } else col.push(panel({ titulo: 'Su GoHighLevel', icono: 'cap' }, h('div', { class: 'cuerpo' }, huecoFuente(capt || ghl, { icono: 'cap', quien: 'Yessica (CRM)' }))));

    // ---- Google Ads (muestra de septiembre) ----
    if (pintable(gads) && gads.datos?.total) {
      const t = gads.datos.total;
      col.push(panel({ titulo: 'Google Ads · septiembre', icono: 'megafono', sub: gads.nota || '' }, h('div', { class: 'cuerpo pila' },
        barras([['Impresiones', t.impresiones], ['Clics', t.clics], ['Conversiones', t.conversiones, 'verde']]),
        F.ve.inversion && t.coste != null ? h('p', { class: 'sub' }, `Coste: ${fmt.eur(t.coste)}`) : null, frescuraEl(gads))));
    }
    z.append(h('div', { class: 'dos' }, col));

    // ---- Outreach por correo (Snov.io) ----
    if (pintable(snov) && snov.datos?.actual) {
      const a = snov.datos.actual, b = snov.datos.anterior || {};
      const r = (x, y) => (y ? Math.round(x / y * 1000) / 10 : null);
      const resp = r(a.email_replies, a.delivered);
      z.append(panel({ titulo: 'Outreach por correo', icono: 'send', sub: `Snov.io · ${snov.datos.campanas?.length || 0} campañas · siempre 30 días (Snov no da 7)` },
        h('div', { class: 'cuerpo pila' }, tiles([
          tile({ icono: 'send', etiqueta: 'Enviados · 30 días', valor: fmt.num(a.emails_sent), comparacion: { delta: variacion(a.emails_sent, b.emails_sent), pct: true, texto: 'frente a los 30 anteriores' } }),
          tile({ icono: 'ojo', etiqueta: 'Aperturas', valor: fmt.num(a.email_opens), contexto: `${fmt.num(r(a.email_opens, a.delivered), 1)} % de los entregados` }),
          tile({ icono: 'chat', etiqueta: 'Respuestas', valor: fmt.num(a.email_replies), estado: resp == null ? 'gris' : semaforo(resp, { verde: 5.5, ambar: 2 }), contexto: `${fmt.num(resp, 1)} % · verde desde el 5,5 %`, comparacion: { delta: variacion(a.email_replies, b.email_replies), pct: true, texto: 'frente a los 30 anteriores' } }),
          tile({ icono: 'alert', etiqueta: 'Rebotes', valor: fmt.num(a.bounced), estado: (r(a.bounced, a.emails_sent) || 0) > 5 ? 'rojo' : '', contexto: `${fmt.num(r(a.bounced, a.emails_sent), 1)} % de los enviados` }),
        ]), tablaApilable({ filas: snov.datos.campanas || [], columnas: [
          { clave: 'nombre', titulo: 'Campaña', principal: true, celda: x => h('span', { class: 'fila', style: { flexWrap: 'nowrap' } }, chipEstado(x.estado === 'Active' ? 'verde' : x.estado === 'Paused' ? 'ambar' : 'gris', x.estado === 'Active' ? 'Activa' : x.estado === 'Paused' ? 'Pausada' : x.estado), x.nombre) },
          { clave: 'env', titulo: 'Enviados', num: true, celda: x => fmt.num(x.actual?.emails_sent) },
          { clave: 'ap', titulo: 'Aperturas', num: true, celda: x => fmt.num(x.actual?.email_opens) },
          { clave: 're', titulo: 'Respuestas', num: true, celda: x => fmt.num(x.actual?.email_replies) },
        ] }), frescuraEl(snov))));
    }
  },

  // ------------------------------------------------------------- Web y SEO
  web(z, ctx, F) {
    const { doc } = F;
    const n = +F.periodo();
    const ga = fuente(doc, 'ga4'), gsc = fuente(doc, 'gsc'), sr = fuente(doc, 'seranking');
    if (!pintable(ga) && !pintable(gsc)) {
      z.append(vacio({ icono: 'globe', borde: true, titulo: 'Sin Analytics ni Search Console emparejados', texto: `${ga?.nota || 'No hay propiedad de Analytics.'} ${gsc?.nota || ''} Hay que dar acceso a gmb1@ o decir cuál es.`, quien: 'Constanza (SEO) y Agus' }));
      return;
    }
    // Qué propiedad y qué sitio se leen (para ver de un vistazo si el emparejamiento es la web buena o una landing)
    const emp = [pintable(ga) && ga.emparejado ? `Analytics: ${ga.emparejado.nombre}` : null, pintable(gsc) && gsc.emparejado ? `Search Console: ${gsc.emparejado.nombre}` : null].filter(Boolean);
    if (emp.length) z.append(h('p', { class: 'sub' }, `Se lee ${emp.join(' · ')}. Si no es su web, avisa a Agus.`));
    // La etiqueta de Analytics dejó de medir: el periodo anterior tenía visitas y el actual, ninguna → rojo con dueño, no «a cero» gris
    if (ga && (ga.datos?.anterior?.usuarios || 0) > 50 && !(ga.datos?.actual?.usuarios))
      z.append(vacio({ icono: 'alert', tono: 'aviso', borde: true, titulo: 'Analytics ha dejado de medir', texto: `El periodo anterior tuvo ${fmt.num(ga.datos.anterior.usuarios)} usuarios y este, ninguno: lo normal es que la etiqueta se haya caído de la web.`, quien: 'quien lleva la web' }));
    const L = [];
    let serieGa = [], serieGsc = [];
    if (pintable(ga)) {
      const a = ga.datos.actual || {}, b = ga.datos.anterior || {};
      serieGa = (ga.datos.serie_usuarios || []).map(([d, v]) => ({ x: isoDe(d), y: v }));
      const w = n === 7 ? ventana(serieGa.map(p => [p.x, p.y]), 7) : { actual: a.usuarios, anterior: b.usuarios };
      L.push(tile({ icono: 'users', etiqueta: `Usuarios · ${n} días`, valor: fmt.num(w.actual), comparacion: { delta: variacion(w.actual, w.anterior), pct: true, texto: `frente a los ${n} anteriores` }, frescura: frescuraDe(ga) }));
      L.push(tile({ icono: 'spark', etiqueta: 'Usuarios nuevos · 30 días', valor: fmt.num(a.nuevos), comparacion: { delta: variacion(a.nuevos, b.nuevos), pct: true, texto: 'frente a los 30 anteriores' } }));
      L.push(tile({ icono: 'zap', etiqueta: 'Sesiones · 30 días', valor: fmt.num(a.sesiones), comparacion: { delta: variacion(a.sesiones, b.sesiones), pct: true, texto: 'frente a los 30 anteriores' }, contexto: a.interaccion != null ? `${fmt.pct(a.interaccion * 100)} con interacción` : null }));
      L.push(tile({ icono: 'target', etiqueta: 'Conversiones · 30 días', valor: fmt.num(a.conversiones), comparacion: { delta: variacion(a.conversiones, b.conversiones), pct: true, texto: 'frente a los 30 anteriores' } }));
    }
    if (pintable(gsc)) {
      const a = gsc.datos.actual || {}, b = gsc.datos.anterior || {};
      serieGsc = (gsc.datos.serie_clics_impresiones || []).map(([d, cl]) => ({ x: d, y: cl }));
      const w = n === 7 ? ventana(serieGsc.map(p => [p.x, p.y]), 7) : { actual: a.clics, anterior: b.clics };
      L.push(tile({ icono: 'sube', etiqueta: `Clics en Google · ${n} días`, valor: fmt.num(w.actual), comparacion: { delta: variacion(w.actual, w.anterior), pct: true, texto: `frente a los ${n} anteriores` }, frescura: frescuraDe(gsc) }));
      L.push(tile({ icono: 'ojo', etiqueta: 'Impresiones · 30 días', valor: fmt.num(a.impresiones), comparacion: { delta: variacion(a.impresiones, b.impresiones), pct: true, texto: 'frente a los 30 anteriores' } }));
      L.push(tile({ icono: 'star', etiqueta: 'Posición media', valor: fmt.num(a.posicion, 1), comparacion: { delta: a.posicion != null && b.posicion != null ? Math.round((a.posicion - b.posicion) * 10) / 10 : null, dec: 1, texto: 'puestos frente a los 30 anteriores', mejorSi: 'bajo' }, contexto: a.ctr != null ? `${fmt.num(a.ctr * 100, 1)} % de clics sobre impresiones` : null }));
    }
    z.append(rejilla(L));
    if (pintable(gsc)) {
      const conDato = (gsc.datos.serie_clics_impresiones || []).filter(x => (x[1] || 0) + (x[2] || 0) > 0).map(x => x[0]);
      const ult = conDato.at(-1), fin = gsc.datos.periodo?.[1];
      if (ult && fin && ult < fin) z.append(avisoParcial(`Search Console tiene datos hasta el ${fDiaRO(ult)} (Google va 2 o 3 días por detrás): la comparación con el periodo anterior sale algo a la baja.`, { tipo: 'info' }));
    }
    const cortar = s => s.slice(-Math.max(n, 14));
    z.append(h('div', { class: 'dos' },
      pintable(ga) ? panel({ titulo: 'Usuarios por día', icono: 'grafico', sub: 'Google Analytics', acciones: recursoBoton(F, 'analytics', 'Abrir Analytics') },
        h('div', { class: 'cuerpo pila' }, graficoSerie({ puntos: cortar(serieGa), alto: 160 }),
          h('h3', { class: 'titulo-seccion' }, icono('doc', { clase: 's' }), 'Páginas más vistas'),
          tablaApilable({ filas: (ga.datos.paginas || []).map(([p, v]) => ({ p, v })), columnas: [{ clave: 'p', titulo: 'Página', principal: true }, { clave: 'v', titulo: 'Usuarios', num: true, celda: x => fmt.num(x.v) }] }))) : panel({ titulo: 'Google Analytics', icono: 'grafico' }, h('div', { class: 'cuerpo' }, huecoFuente(ga, { icono: 'grafico', quien: 'Agus' }))),
      pintable(gsc) ? panel({ titulo: 'Clics en Google por día', icono: 'sube', sub: 'Search Console', acciones: recursoBoton(F, 'searchConsole', 'Abrir Search Console') },
        h('div', { class: 'cuerpo pila' }, graficoSerie({ puntos: cortar(serieGsc), alto: 160 }),
          h('h3', { class: 'titulo-seccion' }, icono('buscar', { clase: 's' }), 'Búsquedas que traen clics'),
          tablaApilable({ filas: F.web?.consultas || [], vacio: { titulo: 'Sin búsquedas con clics', texto: 'Search Console no da búsquedas con clics para este sitio en 30 días.' }, columnas: [
            { clave: 'q', titulo: 'Búsqueda', principal: true }, { clave: 'clics', titulo: 'Clics', num: true, celda: x => fmt.num(x.clics) },
            { clave: 'posicion', titulo: 'Posición', num: true, celda: x => fmt.num(x.posicion, 1) }] }))) : panel({ titulo: 'Search Console', icono: 'sube' }, h('div', { class: 'cuerpo' }, huecoFuente(gsc, { icono: 'buscar', quien: 'Constanza (SEO)' })))));
    const canales = pintable(ga) ? (ga.datos.canales || []) : [];
    const TRAD = { 'Organic Search': 'Google y buscadores', Direct: 'Directo', Display: 'Anuncios de display', 'Paid Video': 'Vídeo de pago', 'Paid Search': 'Google Ads', Referral: 'Otras webs', 'Organic Social': 'Redes', 'Paid Social': 'Redes de pago', Email: 'Correo', Unassigned: 'Sin asignar', 'Cross-network': 'Varias redes' };
    z.append(h('div', { class: 'dos' },
      panel({ titulo: 'De dónde llegan las visitas', icono: 'zap', sub: 'Usuarios por canal · 30 días' }, h('div', { class: 'cuerpo' }, canales.length ? barras(canales.map(([k, v]) => [TRAD[k] || k, v])) : vacio({ icono: 'zap', titulo: 'Sin visitas por canal', texto: 'Analytics no trae visitas de esta web en los últimos 30 días. Si la web tiene tráfico, falta la etiqueta de Analytics: lo revisa Web.' }))),
      panel({ titulo: 'Posiciones de palabras clave', icono: 'star', sub: 'SE Ranking' }, h('div', { class: 'cuerpo pila' },
        sr?.datos?.palabras_seguidas ? h('p', { class: 'sub' }, `${fmt.num(sr.datos.palabras_seguidas)} palabras seguidas en ${sr.datos.dominio}`) : null,
        pintable(sr) ? h('p', {}, 'Posiciones disponibles') : huecoFuente(sr, { icono: 'star', titulo: 'Posiciones: la clave de proyectos de SE Ranking no funciona', quien: 'Tomás' })))));
  },

  // ------------------------------------------------------------- Redes
  redes(z, ctx, F) {
    const m = fuente(F.doc, 'metricool');
    if (!pintable(m)) { z.append(vacio({ icono: 'heart', borde: true, titulo: 'Sin marca de Metricool emparejada', texto: m?.nota || 'No he encontrado la marca de este cliente entre las 25 de Metricool.', quien: 'Redes y Agus' })); return; }
    const d = m.datos;
    const NET = { instagram: 'Instagram', linkedin: 'LinkedIn', facebook: 'Facebook' };
    const L = Object.keys(NET).filter(k => d[k]).map(k => tile({ icono: k === 'linkedin' ? 'maletin' : 'heart', etiqueta: `${NET[k]} · seguidores`, valor: fmt.num(d[k].seguidores),
      comparacion: { delta: d[k].hace30 != null ? d[k].seguidores - d[k].hace30 : null, texto: 'en 30 días' }, frescura: frescuraDe(m) }));
    if (L.length) z.append(rejilla(L));
    const NOMBRE = { linkedinCompany: 'LinkedIn', gmb: 'Ficha de Google', twitter: 'X', instagram: 'Instagram', facebook: 'Facebook', tiktok: 'TikTok', youtube: 'YouTube', pinterest: 'Pinterest', threads: 'Threads', bluesky: 'Bluesky' };
    z.append(h('div', { class: 'dos' },
      panel({ titulo: 'Redes conectadas en Metricool', icono: 'heart', sub: `${(d.redes || []).length} redes en su marca de Metricool` },
        h('div', { class: 'cuerpo fila' }, (d.redes || []).map(r => chipEstado('azul', NOMBRE[r] || r, { punto: false })))),
      panel({ titulo: 'Publicaciones programadas', icono: 'cal' }, h('div', { class: 'cuerpo' },
        vacio({ icono: 'cal', titulo: 'Todavía no se mide', texto: m.nota || 'Los próximos 14 días cubiertos y los huecos llegan con la pantalla de Redes.', quien: 'quien lleva redes' })))));
  },

  // ------------------------------------------------------------- Comunicación
  comunicacion(z, ctx, F) {
    const { doc } = F;
    const zad = fuente(doc, 'zadarma'), reu = fuente(doc, 'reuniones'), zoom = fuente(doc, 'zoom'), desk = fuente(doc, 'desk');
    const dd = desk?.datos || {}, zd = zad?.datos || {}, rd = reu?.datos || {};
    const cc = correosCliente(F);
    const pend = cc ? cc.del_cliente : [];
    const oct = zd.octubre || {}, sep = zd.septiembre || {};
    z.append(rejilla([
      tileCorreos(cc),
      tile({ icono: 'send', etiqueta: 'Último correo nuestro', valor: dd.ult_correo_saliente ? fDiaRO(dd.ult_correo_saliente) : null, estado: dd.ult_correo_saliente ? (dd.correo_esta_semana ? 'verde' : 'ambar') : 'gris', contexto: dd.ult_correo_saliente ? (dd.correo_esta_semana ? 'Ya hay correo esta semana' : 'Sin correo nuestro esta semana') : 'Sin dato', frescura: frescuraDe(desk) }),
      tile({ icono: 'phone', etiqueta: 'Llamadas · octubre', valor: pintable(zad) ? fmt.num(oct.contestadas) : null, unidad: 'contestadas', contexto: `${fmt.num(oct.contestadas_30s_o_mas)} de 30 s o más · ${fmt.num(oct.intentos_sin_contestar)} sin contestar · septiembre: ${fmt.num(sep.contestadas)}${oct.confianza_cruce && oct.confianza_cruce !== 'seguro' ? ' · cruce del número con el cliente probable, sin confirmar' : ''}`, frescura: frescuraDe(zad) }),
      tile({ icono: 'video', etiqueta: 'Reuniones · septiembre', valor: rd.reuniones_mes_anterior ?? null, contexto: rd.ult_reunion ? `Última: ${fDiaRO(rd.ult_reunion)} · hace ${rd.dias_sin_reunion} días` : 'Sin reuniones registradas', estado: rd.dias_sin_reunion == null ? 'gris' : semaforo(rd.dias_sin_reunion, { verde: 30, ambar: 35, mejorSi: 'bajo' }), medible: reu?.medicion, medibleDetalle: reu?.nota, frescura: frescuraDe(reu) }),
    ]));
    // Cada correo con «Sugerir respuesta» (IA): el borrador se revisa y se copia o se contesta en la Bandeja; nunca sale solo.
    const veIA = F.ve.responder && !F.admin;
    const filaCorreo = x => {
      const est = x.horas > 48 ? 'rojo' : x.horas > 24 ? 'ambar' : 'verde';
      const zonaIA = h('div', { style: { flexBasis: '100%', minWidth: '0' } });
      const bt = veIA && !x.auto ? h('button', { type: 'button', class: 'bt mini', 'aria-expanded': 'false',
        on: { click: () => {
          const abierto = bt.getAttribute('aria-expanded') === 'true';
          bt.setAttribute('aria-expanded', String(!abierto));
          zonaIA.replaceChildren(abierto ? '' : botonIA(ctx, { ticket: x.numero, abierto: true }));
        } } }, icono('spark'), 'Sugerir respuesta') : null;
      return h('li', { style: { flexWrap: 'wrap' } },
        h('span', { class: `ico-c s ${est}` }, icono(x.queja ? 'alert' : 'mail')),
        h('span', { class: 't' }, x.url ? h('a', { href: x.url, target: '_blank', rel: 'noopener', title: 'Abrir en Desk' }, `${x.numero} · ${x.asunto}`) : `${x.numero} · ${x.asunto}`),
        x.queja ? chipEstado('rojo', 'Queja') : null,
        h('span', { class: 'x' }, `${x.dias} ${x.dias === 1 ? 'día laborable' : 'días laborables'}`),
        bt, zonaIA);
    };
    const listaCorreos = xs => h('ul', { class: 'lista-i' }, xs.map(filaCorreo));
    const cuadra = cc && cc.del_cliente.length === cc.total;
    const cajaCorreos = h('div', { class: 'cuerpo pila' },
      !cc ? vacio({ icono: 'inbox', titulo: 'Sin dato de correos', texto: F.admin ? 'Administración no ve los correos de los clientes.' : 'Falta el resumen de la Bandeja (data/bandeja/por_cliente.json).', quien: F.admin ? null : 'Tomás (recarga de la Bandeja)' })
        : cc.del_cliente.length ? listaCorreos(cc.del_cliente)
          : cc.total ? h('p', { class: 'sub' }, `${cc.total} sin contestar; el más antiguo, ${cc.masAntiguo?.numero || ''} · ${cc.masAntiguo?.asunto || ''}. La lista de cada correo está en la Bandeja.`)
            : vacioLinea('Nada pendiente del cliente: todo contestado.', { icono: 'ok' }),
      cc && cc.automaticos.length ? h('details', { class: 'que-es' }, h('summary', {}, `Avisos automáticos (Zapier, alertas…): ${cc.automaticos.length}`), listaConIcono(cc.automaticos.map(x => ({ icono: 'zap', estado: 'gris', texto: `${x.numero} · ${x.asunto}`, extra: `${x.dias} días laborables`, href: x.url })))) : null,
      cc ? h('p', { class: 'sub' }, `La misma regla que la Bandeja: sin avisos automáticos, horas de lunes a viernes desde el último correo del cliente. Dato de la Bandeja de las ${String(cc.hora || '').slice(11, 16) || '—'}${cc.listaHora && !cuadra ? ` (la lista es de las ${String(cc.listaHora).slice(11, 16)})` : ''}.${cc.notaFuente ? ` ${cc.notaFuente}` : ''}`) : null,
      cc && cc.llamadas.length ? panel({ titulo: 'Llamadas sin devolver', icono: 'phone' }, h('div', { class: 'cuerpo' }, listaConIcono(cc.llamadas.map(l => ({ icono: 'phone', estado: l.gravedad === 'rojo' ? 'rojo' : 'ambar', texto: `${l.llamadas} llamadas de ${l.numero_oculto}`, extra: `última ${fDiaRO(l.ultima)}`, href: 'https://my.zadarma.com/mystatistics/' }))))) : null);
    z.append(h('div', { class: 'dos' },
      panel({ titulo: 'Correos del cliente sin contestar', icono: 'inbox', sub: 'Zoho Desk · las quejas y el más antiguo arriba', acciones: !F.ve.responder ? candado('Contestan su account, las jefas, operaciones y dirección') : (ctx.veModulo && ctx.veModulo('bandeja') ? h('a', { class: 'bt mini', href: '#/bandeja' }, icono('inbox'), 'Contestar en la Bandeja') : null) },
        cajaCorreos),
      h('div', { class: 'pila' },
        panel({ titulo: 'Reuniones', icono: 'video', sub: 'CRM y Fathom; la más reciente arriba' }, h('div', { class: 'cuerpo' },
          listaConIcono([...(rd.historial || [])].reverse().slice(0, 8).map(r => ({ icono: 'video', texto: r.asunto, extra: `${fDiaRO(r.fecha)} · ${r.quien || r.fuente}` })), { vacio: { icono: 'video', titulo: 'Sin reuniones en 75 días' } }))),
        panel({ titulo: 'Llamadas por persona', icono: 'auricular', sub: 'Zadarma · octubre y septiembre (sin números)' }, h('div', { class: 'cuerpo' },
          pintable(zad) ? barras(Object.entries({ ...(sep.por_persona || {}), ...(oct.por_persona || {}) }).map(([k]) => [k, ((oct.por_persona || {})[k]?.contestadas || 0) + ((sep.por_persona || {})[k]?.contestadas || 0)])) : huecoFuente(zad, { icono: 'phone' }))),
        panel({ titulo: 'Grabaciones de Zoom', icono: 'video', sub: '30 días · sin enlaces ni códigos' }, h('div', { class: 'cuerpo' },
          pintable(zoom) && zoom.datos?.reuniones?.length ? listaConIcono(zoom.datos.reuniones.map(r => ({ icono: 'video', texto: r.tema, extra: `${fDiaRO(r.fecha)} · ${r.minutos} min` }))) : huecoFuente(zoom, { icono: 'video', titulo: 'Sin grabaciones con su nombre', quien: 'quien convoca (con el nombre del cliente en el título)' }))))));
  },

  // ------------------------------------------------------------- Chat (canal de ClickUp)
  chat(z, ctx, F) {
    const caja = h('div', { class: 'pila' }, esqueleto({ lineas: 4 }));
    z.append(caja);
    cargarPrivado(ctx, 'chat', F.c.id).then(r => pintarChat(caja, ctx, F, r));
  },

  // ------------------------------------------------------------- Trabajo
  trabajo(z, ctx, F) {
    const { doc } = F;
    const tar = fuente(doc, 'tareas'), hor = fuente(doc, 'horas'), inf = fuente(doc, 'informes');
    const td = tar?.datos || {};
    const L = [];
    if (F.ve.horas.ok && pintable(hor) && F.ve.horas.nivel !== 'resumen') {
      const hd = hor.datos;
      L.push(tile({ icono: 'clock', etiqueta: 'Horas · octubre', valor: fmt.num(hd.horas_mes, 1), unidad: 'h', contexto: 'Mes en curso', medible: 'medias', medibleDetalle: hor.nota, frescura: frescuraDe(hor) }));
      L.push(tile({ icono: 'clock', etiqueta: 'Horas · septiembre', valor: fmt.num(hd.horas_mes_ant, 1), unidad: hd.horas_presup_mes ? `de ${fmt.num(hd.horas_presup_mes)} h pautadas` : 'h',
        estado: hd.pct_horas > 130 ? 'ambar' : '', contexto: hd.pct_horas != null ? `${fmt.pct(hd.pct_horas)} de lo pautado · solo como aviso` : null, medible: 'medias', medibleDetalle: hor.nota }));
    }
    L.push(tile({ icono: 'alert', etiqueta: 'Revisiones de más de 48 h', valor: fmt.num(td.revision_mas_48h || 0), unidad: `de ${fmt.num(td.revision_total || 0)}`, estado: semaforo(td.revision_mas_48h || 0, { verde: 0, ambar: 3, mejorSi: 'bajo' }), frescura: frescuraDe(tar) }));
    L.push(tile({ icono: 'cal', etiqueta: 'Tareas vencidas', valor: fmt.num(td.vencidas || 0), estado: (td.vencidas || 0) > 10 ? 'ambar' : '', contexto: `${fmt.num(td.sin_fecha)} sin fecha` }));
    L.push(tile({ icono: 'capas', etiqueta: 'No planificadas · semana', valor: fmt.num(td.no_planificadas_semana || 0), estado: semaforo(td.no_planificadas_semana || 0, { verde: 4, ambar: 4, mejorSi: 'bajo' }), contexto: 'Aviso con 5 o más por proyecto y semana' }));
    L.push(tile({ icono: 'check', etiqueta: 'Cerradas · semana', valor: fmt.num(td.cerradas_semana || 0), contexto: `${fmt.num(td.creadas_mes)} creadas este mes · ${fmt.num(td.creadas_mes_ant)} en septiembre` }));
    z.append(rejilla(L));
    if (F.ve.horas.ok && F.ve.horas.nivel === 'resumen') z.append(avisoParcial(F.ve.horas.motivo || 'Horas del cliente en agregado.', { tipo: 'info' }));
    const estados = Object.entries(td.abiertas_por_estado || {}).sort((a, b) => b[1] - a[1]);
    const rev = [...(td.en_revision_detalle || [])].sort((a, b) => b.dias - a.dias);
    z.append(h('div', { class: 'dos' },
      panel({ titulo: 'Revisiones más antiguas', icono: 'alert', sub: 'La de más días arriba · un clic abre la tarea', acciones: recursoBoton(F, 'clickup', 'Abrir en ClickUp') },
        h('div', { class: 'cuerpo' }, listaConIcono(rev.map(r => ({ icono: 'check', estado: r.dias > 2 ? 'rojo' : 'ambar', texto: r.nombre, extra: `${r.estado} · ${fmt.num(r.dias)} d`, href: r.url })), { vacio: { icono: 'ok', titulo: 'Ninguna tarea de este cliente espera revisión', tono: 'celebrar' } }))),
      h('div', { class: 'pila' },
        panel({ titulo: 'Tareas abiertas por estado', icono: 'capas', sub: 'ClickUp' }, h('div', { class: 'cuerpo' }, pintable(tar) ? barras(estados.map(([k, v]) => [k, v, /bloque/.test(k) ? 'rojo' : /revisi/.test(k) ? 'ambar' : null])) : huecoFuente(tar))),
        panel({ titulo: 'Informes mensuales', icono: 'doc', sub: 'Enviado el día 5; el día 6, aviso a Mili' }, h('div', { class: 'cuerpo' },
          listaConIcono(['sep', 'ago'].filter(k => inf?.datos?.[k]).map(k => { const x = inf.datos[k]; return {
            icono: 'doc', estado: x.estado === 'enviado' ? 'verde' : x.estado === 'en curso' ? 'ambar' : 'gris',
            texto: `${k === 'sep' ? 'Septiembre' : 'Agosto'}: ${x.estado}${x.fecha_envio ? ` el ${fDiaRO(x.fecha_envio)}` : ''}`, extra: x.responsable, href: x.url }; }),
          { vacio: { icono: 'doc', titulo: 'Sin informes registrados' } }))))));
  },

  // ------------------------------------------------------------- Accesos y contrato
  accesos(z, ctx, F) {
    const { c, doc, portal } = F;
    const R = portal?.recursos || [];
    const ok = R.filter(r => r.url).length;
    const libro = fuente(doc, 'libro')?.datos || {};
    const e = etapa(c);
    z.append(rejilla([
      F.ve.cuota ? tile({ icono: 'euro', etiqueta: 'Cuota mensual', valor: cuotaFicha(F) ? fmt.eur(cuotaFicha(F).valor) : null, contexto: cuotaFicha(F) ? `Sin IVA · la misma que Dinero por cliente · ${cuotaFicha(F).fuente}` : 'Sin cuota en Airtable ni en el libro' })
        : h('div', { class: 'tile gris' }, h('span', { class: 'tt' }, h('span', { class: 'ico-c gris' }, icono('euro')), h('span', {}, 'Cuota mensual')), candado('Solo dirección, operaciones, administración y su account')),
      tile({ icono: 'cal', etiqueta: 'Fecha de alta', valor: c.alta ? fFecha(c.alta) : null, contexto: e >= 0 ? ['En arranque', 'En arranque', 'En optimización', 'Cliente consolidado'][e] : null }),
      tile({ icono: 'key', etiqueta: 'Accesos en el portal', valor: `${ok} de ${R.length || 10}`, estado: ok < (R.length || 10) ? 'ambar' : 'verde', contexto: `${(R.length || 10) - ok} pendientes (en gris abajo)` }),
      libro.segmento ? tile({ icono: 'maletin', etiqueta: 'Segmento', valor: libro.segmento, contexto: [libro.tipo, libro.clasif, libro.sector].filter(Boolean).join(' · ') }) : null,
      F.ve.cobros && libro.ltv ? tile({ icono: 'cartera', etiqueta: 'Facturado en total', valor: fmt.eur(libro.ltv), contexto: `${fmt.num(libro.vida_meses, 1)} meses de vida · primera factura ${fFecha(libro.primera)}` }) : null,
    ].filter(Boolean)));
    if (portal?.duda) z.append(avisoParcial(portal.duda_completa || portal.duda, { titulo: 'Duda abierta en el portal.' }));
    z.append(panel({ titulo: 'Accesos del cliente', icono: 'key', sub: 'Los 10 recursos del portal, el más usado primero; en gris, los que faltan. Nunca contraseñas: aquí solo «dado» o «falta».' },
      h('div', { class: 'cuerpo' }, R.length ? h('div', { class: 'rejilla' }, R.map(r => r.url
        ? h('div', { class: 'contacto' },
          h('a', { class: 'main', href: r.url, target: '_blank', rel: 'noopener', title: r.url }, h('span', { class: 'ico-c s' }, icono(ICONO_RECURSO[r.k] || 'ext')), h('span', {}, r.t)),
          h('button', { type: 'button', class: 'sq', title: `Copiar el enlace de ${r.t}`, 'aria-label': `Copiar el enlace de ${r.t}`, on: { click: () => copiar(r.url, 'Enlace copiado') } }, icono('copy')))
        : h('div', { class: 'contacto' }, h('span', { class: 'main', 'aria-disabled': 'true', title: 'Pendiente: falta en el portal. Lo arregla Mili.' }, h('span', { class: 'ico-c s gris' }, icono(ICONO_RECURSO[r.k] || 'ext')), h('span', {}, r.t), chipEstado('gris', 'Falta'))))) :
        vacio({ icono: 'key', titulo: 'Este cliente no está en el portal', texto: 'Sin recursos que enseñar.', quien: 'Mili' }))));
    const arr = fuente(doc, 'arranque');
    z.append(h('div', { class: 'dos' },
      panel({ titulo: 'Contrato e hitos', icono: 'doc', sub: 'Alta, firma y arranque (firma → día 90)' }, h('div', { class: 'cuerpo' },
        lineaTiempo([
          ...((pintable(arr) && arr.datos?.hitos) || []).map(x => ({ fecha: x.fecha, titulo: x.titulo || x.nombre || x.hito, estado: x.estado === 'hecho' ? 'verde' : x.estado })),
          libro.ultima ? { fecha: libro.ultima, titulo: 'Última factura', detalle: 'Holded' } : null,
          c.alta ? { fecha: c.alta, titulo: 'Alta del cliente', detalle: 'Portal de clientes' } : null,
          libro.primera ? { fecha: libro.primera, titulo: 'Primera factura', detalle: 'Libro de clientes' } : null,
        ].filter(Boolean)),
        h('p', { class: 'sub' }, 'El contrato firmado (Zoho Sign) se enlaza aquí cuando la capa de datos lo traiga.'))),
      panelEquipo(ctx, F)));
    if (portal?.descripcion) z.append(h('p', { class: 'sub' }, portal.descripcion_completa || portal.descripcion));
  },

  // ------------------------------------------------------------- Rastro
  informes(z, ctx, F) {
    const caja = h('div', { class: 'pila' }, esqueleto({ lineas: 4 }));
    z.append(caja);
    pintarInformes(caja, ctx, F);
  },

  rastro(z, ctx, F) {
    const caja = h('div', { class: 'pila' }, esqueleto({ lineas: 4 }));
    z.append(caja);
    pintarRastro(caja, ctx, F);
  },
};

// =================================================================== piezas
// =================================================================== contactos (personas unidas, rol con su fuente)
function pintarContactos(z, ctx, F) {
  const r = F.contactos;
  if (!r || r.negado) { z.append(vacio({ icono: 'candado', borde: true, titulo: 'Los contactos de este cliente no son de tu puesto', texto: r?.negado || 'Solo los ven su account, operaciones y dirección.', quien: F.c.responsable })); return; }
  if (!r.valor) { z.append(vacio({ icono: 'users', borde: true, titulo: 'Sin contactos todavía', texto: 'Ni el portal de clientes ni el documento de móviles y correos del 2-oct tienen a nadie de este cliente.', quien: F.c.responsable })); return; }
  const v = r.valor;
  const P = (v.personas || []).map((p, i) => ({ ...p, _i: i }));
  const gente = P.filter(p => !p.generico && !p.externo);
  const marcar = (cont, quien) => cont.querySelectorAll('a').forEach(a => a.addEventListener('click', () => ctx.rastro({ accion: /^sip:/.test(a.href) ? 'llamar' : /wa\.me/.test(a.href) ? 'whatsapp' : 'correo', objeto: F.c.id, detalle: quien })));

  // Aviso «pedir móvil» (Accompany, Bonet, J&D, Oteca…): con el fijo si lo hay
  if (v.sin_movil) {
    const fijos = (v.fijos || []).map(f => normalizarTelefono(f)).filter(Boolean);
    const caja = h('div', { class: 'aviso', role: 'note', style: { flexWrap: 'wrap' } },
      h('div', { class: 'pila', style: { flex: '1 1 0', minWidth: '0' } }, h('b', { class: 'fila' }, icono('phone'), 'Sin móvil de este cliente: pídeselo'), h('p', {}, (v.notas || []).join(' ') || 'Ni el portal, ni el Excel de cartera, ni GHL ni WhatsApp tienen un móvil.')),
      h('div', { class: 'fila' }, fijos.map(t => h('a', { class: 'bt', href: `sip:${t.intl}@sip.zadarma.com`, title: 'Llamar al fijo con Zadarma' }, icono('phone'), `Fijo ${t.mostrar}`)),
        botonConfirmar({ texto: 'Pedir el móvil', pregunta: `¿Dejar a ${F.c.responsable} la tarea de pedirlo?`, confirmar: 'Sí, pedirlo', soloLectura: ctx.soloLectura,
          alConfirmar: async () => { await ctx.accion({ herramienta: 'clickup', tipo: 'pedir_movil', objeto: F.c.id, cliente_id: F.c.id, texto: `Pedir a ${F.c.nombre} un móvil de contacto (no hay ninguno en portal, Excel, GHL ni WhatsApp)`, vista_previa: { tarea: `Pedir móvil · ${F.c.nombre}`, para: F.c.responsable } }); return 'En cola (simulado de momento)'; } })));
    marcar(caja, 'fijo'); z.append(caja);
  }

  // Dudas de contactos que solo decide Tomás (p. ej. Centro Consulting: «Gemma Gregorio» y «Gema Gregorio»). No se unen
  // hasta que él lo confirme; la duda solo la ve dirección.
  const esDireccion = (ctx.persona.puestos || []).includes('direccion');
  const dudas = esDireccion ? (v.dudas || []) : [];
  const enDuda = new Set(dudas.flatMap(d => d.nombres || []));
  if (dudas.length) {
    z.append(avisoParcial(h('span', {}, dudas.map((d, i) => h('span', {}, i ? ' · ' : '',
      d.tipo === '¿la misma persona escrita de dos formas?'
        ? `¿«${d.nombres[0]}» y «${d.nombres[1]}» son la misma persona?${d.correos?.length ? ` (${d.correos.join(', ')})` : ''} No se unen hasta que lo confirmes.`
        : `${d.tipo}: ${(d.nombres || []).join(' / ')}. No se toca hasta que lo confirmes.`))),
      { titulo: dudas.length === 1 ? 'Duda para Tomás (solo la ve dirección).' : `${dudas.length} dudas para Tomás (solo las ve dirección).` }));
  }

  const total = (pred) => P.filter(pred).length;
  const chips = chipsFiltro({ etiqueta: 'Ver', clave: 'ficha.personas', opciones: [
    { valor: '', texto: 'Personas', icono: 'users', cuenta: gente.length },
    { valor: 'movil', texto: 'Con móvil', icono: 'phone', cuenta: total(p => !p.externo && p.telefonos.length) },
    { valor: 'decisor', texto: 'Decisores', icono: 'crown', cuenta: total(p => p.decisor && !p.externo) },
    { valor: 'dia', texto: 'Día a día', icono: 'chat', cuenta: total(p => p.dia_a_dia && !p.externo) },
    { valor: 'buzon', texto: 'Buzones', icono: 'inbox', cuenta: total(p => p.generico) },
    { valor: 'externo', texto: 'Externos', icono: 'maletin', cuenta: total(p => p.externo) },
    { valor: 'todo', texto: 'Todo', cuenta: P.length },
  ], alCambiar: () => pintar() });
  const buscar = h('input', { type: 'search', placeholder: 'Buscar nombre, cargo, teléfono o correo', 'aria-label': 'Buscar contacto' });
  const caja = h('div', { class: 'dos' });
  const pintar = () => {
    const f = chips.valor(), q = buscar.value.trim().toLowerCase();
    const xs = P.filter(p => (f === 'todo' ? true : f === 'movil' ? !p.externo && p.telefonos.length : f === 'decisor' ? p.decisor && !p.externo : f === 'dia' ? p.dia_a_dia && !p.externo
      : f === 'buzon' ? p.generico : f === 'externo' ? p.externo : !p.generico && !p.externo))
      .filter(p => !q || [p.nombre, p.rol, ...(p.tambien || []), ...p.telefonos.map(t => t.tel), ...p.correos.map(m => m.correo)].join(' ').toLowerCase().includes(q));
    caja.replaceChildren(...(xs.length ? xs.map(p => tarjetaPersona(p, marcar, enDuda.has(p.nombre))) : [vacio({ icono: 'buscar', titulo: 'Nadie con ese filtro' })]));
  };
  buscar.addEventListener('input', pintar);
  const sinRol = gente.filter(p => !p.rol).length;
  z.append(h('div', { class: 'tabla-ctl', style: { padding: '0', borderBottom: '0' } }, chips, buscar), caja,
    h('p', { class: 'sub' }, `${gente.length} personas, ${total(p => p.generico)} buzones y ${total(p => p.externo)} externos. Cada persona sale una vez con un solo nombre; las otras formas en que aparece van en «También aparece como». `,
      sinRol ? `${sinRol} sin cargo en ninguna fuente («Rol sin confirmar»). ` : '',
      'Fuentes: documento de móviles y correos del 2-oct, portal de clientes, Zoho CRM, Zoho Desk (firma de sus correos) y nombres de WhatsApp. Llamar abre la app de Zadarma; el «te llamo y te conecto» llega cuando la app esté publicada. Abrir esta pestaña queda en el rastro.'));
  pintar();
}

function tarjetaPersona(p, marcar, duda = false) {
  const marcas = [
    p.principal ? chipEstado('azul', 'Principal · el que más interactúa') : null,
    p.decisor ? h('span', { class: 'chip verde', title: `Por qué: ${p.decisor.por}` }, 'Decisor') : null,
    p.dia_a_dia ? h('span', { class: 'chip azul', title: `Por qué: ${p.dia_a_dia.por}` }, 'Día a día') : null,
    p.generico ? chipEstado('gris', 'Buzón general') : null,
    p.externo ? chipEstado('gris', 'Externo al despacho') : null,
    p.nombre_por_confirmar ? h('span', { class: 'chip ambar', title: 'Aparece con dos nombres distintos: está en las dudas para Tomás' }, 'Nombre por confirmar') : null,
    duda ? h('span', { class: 'chip ambar', title: 'Duda para Tomás: puede ser la misma persona que otra ficha. No se une hasta que lo confirme.' }, '¿Misma persona? · duda para Tomás') : null,
    p.solo_portal && !p.externo ? h('span', { class: 'chip gris sin-punto', title: 'No sale en el documento de móviles y correos; sale del portal de clientes' }, 'Solo en el portal') : null,
  ].filter(Boolean);
  const rolPrincipal = (p.roles || []).find(r => !r.solo_nombre);
  // Tarjeta = panel común (borde, radio y sombra de la guía); buzones y externos en el fondo secundario.
  const card = h('article', { class: 'panel', style: p.generico || p.externo ? { background: 'var(--card-2)' } : null },
    h('div', { class: 'cuerpo pila' },
      h('div', { class: 'fila', style: { flexWrap: 'nowrap', alignItems: 'flex-start' } },
        h('span', { class: 'av', 'aria-hidden': 'true', style: p.principal ? { background: 'var(--accent)' } : p.generico || p.externo ? { background: 'var(--off-soft)', color: 'var(--mid)' } : null },
          p.generico ? icono('inbox', { clase: 's' }) : p.sin_nombre ? '?' : iniciales(p.nombre)),
        h('div', { class: 'pila', style: { flex: '1 1 0', minWidth: '0' } },
          h('div', {}, h('b', {}, p.nombre),
            p.rol ? h('p', { class: 'sub', title: rolPrincipal ? `Fuente: ${rolPrincipal.fuente}` : null }, p.rol) : h('p', { class: 'sub' }, 'Rol sin confirmar')),
          marcas.length ? h('div', { class: 'fila' }, marcas) : null)),
      (p.telefonos.length || p.correos.length) ? h('div', { class: 'contactos' },
        p.telefonos.map(t => h('div', { class: 'pila' }, botonesContacto({ telefono: t.tel }),
          (t.etiqueta && t.etiqueta !== p.nombre) || t.whatsapp || t.compartido ? h('p', { class: 'sub' }, [t.compartido || null, t.etiqueta && t.etiqueta !== p.nombre ? `Guardado como «${t.etiqueta}»` : null, t.whatsapp ? `En WhatsApp: «${t.whatsapp}»` : null].filter(Boolean).join(' · ')) : null)),
        p.correos.map(m => h('div', { class: 'fila', style: { flexWrap: 'nowrap' } }, h('div', { style: { flex: '1 1 0', minWidth: '0' } }, botonesContacto({ correo: m.correo })),
          m.veces ? h('span', { class: 'chip gris sin-punto', title: `Aparece ${m.veces} veces en ${m.donde.join(', ')}${m.copia ? ` · ${m.copia} en copia` : ''}` }, `${fmt.num(m.veces)}×`) : null)))
        : h('p', { class: 'sub' }, 'Sin teléfono ni correo.'),
      p.veces || p.ultimo ? h('div', { class: 'meta-linea' },
        p.veces ? h('span', {}, icono('mail'), `${fmt.num(p.veces)} apariciones${p.copia ? ` · ${fmt.num(p.copia)} en copia` : ''}`) : null,
        p.ultimo ? h('span', { title: 'Último correo que ha escrito él (Zoho Desk)' }, icono('clock'), `Último correo suyo: ${fDiaRO(p.ultimo)} ${p.ultimo.slice(0, 4) !== '2026' ? p.ultimo.slice(0, 4) : ''}`) : null) : null,
      p.nota ? h('div', { class: 'aviso' }, p.nota) : null,
      (p.roles || []).length || (p.tambien || []).length ? h('details', { class: 'que-es' },
        h('summary', {}, 'De dónde sale'),
        h('ul', {},
          (p.roles || []).map(r => h('li', {}, `${r.texto} — ${r.fuente}`)),
          (p.tambien || []).length ? h('li', {}, `${p.generico ? 'Escriben desde aquí' : 'También aparece como'}: ${p.tambien.join(' · ')}`) : null,
          h('li', {}, `Fuentes: ${(p.fuentes || []).join(', ')}`))) : null));
  marcar(card, p.nombre);
  return card;
}

// =================================================================== ficha básica (producción: solo lectura, sin dinero ni contactos)
async function pintarBasica(raiz, ctx, idParam) {
  let d = null;
  try { d = await ctx.datosModulo('ficha/basica'); } catch { d = null; }
  const fila = (d?.filas || []).find(x => x.persona_id === ctx.persona.id);
  const lista = fila?.clientes || [];
  if (!lista.length) {
    ctx.titulo('Ficha del cliente', 'Ningún cliente con tareas tuyas');
    raiz.append(vacio({ icono: 'cli', borde: true, titulo: 'No tienes tareas abiertas de ningún cliente', texto: 'Aquí verás la ficha básica (web, redes, carpeta de materiales y tus tareas) de los clientes con los que trabajas.', quien: 'tu jefa de producción' }));
    return;
  }
  const comun = new Map(ctx.clientes.map(c => [c.id, c]));
  const items = lista.map(x => ({ ...(comun.get(x.ref) || {}), id: x.ref, nombre: comun.get(x.ref)?.nombre || x.nombre, basica: x }));
  // V2 (C-16): un cliente pedido que no está en tu lista NUNCA salta a otro cliente sin avisar.
  if (idParam && !items.some(x => x.id === idParam)) {
    const otro = comun.get(idParam);
    ctx.titulo(otro?.nombre || 'Ficha del cliente', 'Ficha del cliente');
    raiz.append(vacio({ icono: 'candado', borde: true, titulo: otro ? 'La ficha de este cliente no es de tu puesto' : 'No encuentro ese cliente',
      texto: otro ? `No tienes tareas abiertas de ${otro.nombre}: su ficha la ve quien lo lleva${otro.responsable ? ` (${otro.responsable})` : ''}. Tus fichas son las de los clientes con tareas tuyas.` : `No hay ningún cliente con el identificador «${idParam}».`,
      quien: otro?.responsable || null, accion: h('a', { class: 'bt', href: `#/ficha/${items[0].id}` }, icono('volver'), `Ver mis fichas (${items.length})`) }));
    return;
  }
  const actual = items.find(x => x.id === idParam) || items[0];
  if (!idParam) history.replaceState(null, '', `#/ficha/${actual.id}`);
  const b = actual.basica;
  ctx.titulo('Ficha del cliente', 'Ficha básica · solo lectura');
  // V2 (C-31): nada de la ficha básica depende del periodo: fuera la barra de periodo de la carcasa.
  const barraP = document.getElementById('barra-ctx'); if (barraP) barraP.hidden = true;
  const selector = selectorCliente({ clientes: items, actual: actual.id, etiqueta: 'Cambiar de cliente', detalle: x => `${x.basica.tareas.length} tareas tuyas`, insignia: () => null, alElegir: x => ctx.navegar(`ficha/${x.id}`) });
  const web = b.web ? b.web.replace(/^https?:\/\//, '').replace(/\/$/, '') : null;
  const NOMBRE = { linkedinCompany: 'LinkedIn', gmb: 'Ficha de Google', instagram: 'Instagram', facebook: 'Facebook', tiktok: 'TikTok', youtube: 'YouTube', twitter: 'X' };
  raiz.append(
    h('section', { class: 'detalle-cab', 'aria-label': 'Cabecera del cliente' },
      h('div', { class: 'pila', style: { flexBasis: '100%', minWidth: '0' } }, h('div', {}, selector),
        h('div', { class: 'pila' },
          h('div', { class: 'meta-linea' },
            actual.responsable ? h('span', {}, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(actual.responsable)), `Account: ${actual.responsable}`) : null,
            b.descripcion ? h('span', {}, icono('maletin'), b.descripcion) : null,
            web ? h('span', {}, icono('link'), h('a', { href: b.web, target: '_blank', rel: 'noopener' }, web)) : null),
          h('div', { class: 'fila' }, chipEstado('gris', 'Ficha básica · sin dinero ni contactos', { punto: false })))),
      h('div', { class: 'fila', style: { flexBasis: '100%' } }, h('span', { class: 'titulo-seccion' }, 'Abrir en'),
        b.drive ? h('a', { class: 'bt mini', href: b.drive, target: '_blank', rel: 'noopener' }, icono('drive'), 'Drive (materiales)') : h('span', { class: 'bt mini', 'aria-disabled': 'true', title: 'Sin carpeta en el portal. Lo arregla Mili.' }, icono('drive'), 'Drive · falta'),
        b.metricool ? h('a', { class: 'bt mini', href: b.metricool, target: '_blank', rel: 'noopener' }, icono('heart'), 'Metricool') : null)),
    h('div', { class: 'dos' },
      panel({ titulo: 'Tus tareas en este cliente', icono: 'check', sub: `${b.tareas.length} abiertas · la vencida arriba` },
        h('div', { class: 'cuerpo' }, listaConIcono(b.tareas.slice().sort((x, y) => Number(!!y.vencida) - Number(!!x.vencida)).map(t => ({ icono: 'check', estado: t.vencida ? 'rojo' : 'gris', texto: t.tarea, extra: `${t.estado}${t.vence ? ' · vence ' + fDiaRO(t.vence) : ''}`, href: t.url }))))),
      panel({ titulo: 'Marca y redes', icono: 'heart', sub: 'Dónde publica el cliente' },
        h('div', { class: 'cuerpo fila' }, (b.redes || []).length ? b.redes.map(r => chipEstado('azul', NOMBRE[r] || r, { punto: false })) : h('p', { class: 'sub' }, 'Sin redes conectadas en Metricool.')))));
}

// =================================================================== informes del pasado (N2)
async function pintarInformes(caja, ctx, F) {
  let d = null;
  try { d = await cargarModulo(ctx, 'ficha/informes'); } catch { d = null; }
  const fila = (d?.filas || []).find(x => x.cliente_id === F.c.id);
  const meta = d?._meta || {};
  if (!fila) { caja.replaceChildren(vacio({ icono: 'doc', borde: true, titulo: 'Sin histórico de informes', texto: 'Este cliente no está en la hoja «Informes mensuales» ni en el seguimiento de informes.', quien: F.c.responsable })); return; }
  const veApp = ctx.veModulo ? ctx.veModulo('informe-cliente') : false;
  const MES = m => { const [a, n] = m.split('-'); return `${['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'][+n - 1]} ${a}`; };
  const ESTADO = { enviado: ['verde', 'Enviado'], en_curso: ['ambar', 'En curso'], hecho_sin_enviar: ['ambar', 'Hecho, sin enviar'], pendiente: ['rojo', 'Pendiente'], no_aplica: ['gris', 'No aplica'], exento: ['gris', 'Exento'] };
  const meses = fila.meses;
  const conInforme = meses.filter(m => m.enlace_informe).length;
  const enviados = meses.filter(m => m.enviado === true || m.estado === 'enviado').length;
  const enReunion = meses.filter(m => m.informado_en_reunion).length;
  const buscar = h('input', { type: 'search', placeholder: 'Buscar mes («agosto», «2026-07»…)', 'aria-label': 'Buscar mes' });
  const chips = chipsFiltro({ etiqueta: 'Ver', clave: 'ficha.informes', opciones: [
    { valor: '', texto: 'Todos', cuenta: meses.length },
    { valor: 'informe', texto: 'Con informe', icono: 'doc', cuenta: conInforme },
    { valor: 'sin', texto: 'Sin informe', icono: 'alert', cuenta: meses.length - conInforme, cuentaEstado: 'rojo' },
    { valor: 'enviado', texto: 'Enviados', icono: 'send', cuenta: enviados },
  ], alCambiar: () => pintar() });
  const lista = h('div', { class: 'cuerpo' });
  const enlace = (url, ico, texto) => url ? h('a', { class: 'bt mini', href: url, target: /^#/.test(url) ? null : '_blank', rel: /^#/.test(url) ? null : 'noopener',
    on: { click: () => ctx.rastro({ accion: 'abrir_atajo', objeto: F.c.id, detalle: texto }) } }, icono(ico), texto) : null;
  const pintar = () => {
    const q = buscar.value.trim().toLowerCase(), f = chips.valor();
    const xs = meses.filter(m => (!q || `${m.mes} ${MES(m.mes)}`.includes(q)) && (f === 'informe' ? m.enlace_informe : f === 'sin' ? !m.enlace_informe : f === 'enviado' ? (m.enviado === true || m.estado === 'enviado') : true));
    lista.replaceChildren(xs.length ? h('ul', { class: 'lista-i' }, xs.map(m => {
      const est = m.estado ? ESTADO[m.estado] || ['gris', m.estado.replace(/_/g, ' ')] : m.enviado ? ['verde', 'Enviado'] : m.enlace_informe ? ['ambar', 'Hecho'] : ['gris', 'Sin informe en la hoja'];
      return h('li', { style: { flexWrap: 'wrap', alignItems: 'flex-start' } },
        h('span', { class: `ico-c s ${est[0]}` }, icono('doc')),
        h('span', { class: 't', style: { flex: '1 1 0', whiteSpace: 'normal' } }, h('b', { style: { textTransform: 'capitalize' } }, MES(m.mes)), ' ', chipEstado(est[0], est[1]),
          m.informado_en_reunion ? [' ', chipEstado('azul', 'Contado en reunión')] : null,
          m.dias_retraso ? h('span', { class: 'sub' }, ` · ${m.dias_retraso} días tarde`) : null,
          m.envio_fecha ? h('span', { class: 'sub', style: { display: 'inline-flex', flexWrap: 'wrap', alignItems: 'center', gap: '0 4px' } }, ` · enviado el ${fDiaRO(m.envio_fecha)}`, m.envio_ticket ? conTickets(m.envio_ticket, { boton: true }) : null) : null),
        h('span', { class: 'fila' },
          enlace(m.enlace_informe, 'doc', 'Informe'), enlace(m.enlace_estadisticas, 'grafico', 'Estadísticas'),
          enlace(m.envio, 'inbox', 'Correo del envío'), enlace(m.tarea, 'check', 'Tarea'),
          m.informe_app && veApp ? enlace(m.informe_app, 'res', 'Informe de la app') : null));
    })) : vacio({ icono: 'buscar', titulo: 'Ningún mes con ese filtro' }));
  };
  buscar.addEventListener('input', pintar);
  pintar();
  caja.replaceChildren(
    tiles([
      tile({ icono: 'doc', etiqueta: 'Meses con informe', valor: conInforme, unidad: `de ${meses.length}`, estado: conInforme === meses.length ? 'verde' : 'ambar', contexto: 'En la hoja «Informes mensuales» o en el seguimiento' }),
      tile({ icono: 'send', etiqueta: 'Enviados', valor: enviados, unidad: `de ${meses.length}` }),
      tile({ icono: 'video', etiqueta: 'Contados en reunión', valor: enReunion, unidad: `de ${meses.length}` }),
    ]),
    h('div', { class: 'tabla-ctl', style: { padding: '0', borderBottom: '0' } }, chips, buscar),
    panel({ titulo: 'Informes mes a mes', icono: 'doc', sub: 'El más reciente arriba · cada mes con su informe, sus estadísticas, el correo con que se envió y el informe de la app',
      acciones: h('span', { class: 'fila' }, enlace(fila.looker, 'res', 'Looker Studio'), enlace(fila.carpeta_informes, 'drive', 'Carpeta de informes'),
        !fila.looker ? h('span', { class: 'bt mini', 'aria-disabled': 'true', title: 'Sin Looker en el portal' }, icono('res'), 'Looker · no hay') : null) }, lista),
    h('p', { class: 'sub' }, `Hoja de Zoho importada el ${meta.hoja_importada ? fDiaRO(meta.hoja_importada) + ' a las ' + String(meta.hoja_importada).slice(11, 16) : '—'}. `,
      (meta.fotos_diarias || []).length ? `Fotos diarias de la app guardadas: ${meta.fotos_diarias.map(x => fDiaRO(x)).join(', ')} (se consultan en el servidor; no se abren desde aquí). ` : 'Aún no hay fotos diarias de la app. ',
      veApp ? '' : 'El informe de la app por mes lo abren su account, publicidad, SEO, sus jefas y dirección.'));
}

/** La persona a la que se llama desde la cabecera y el chat: la principal con móvil; si no, la primera con móvil; si no, solo correo. */
function contactoPrincipal(v) {
  if (!v?.personas) return null;
  const gente = v.personas.filter(p => !p.externo);
  const conTel = gente.filter(p => (p.telefonos || []).length);
  const p = conTel.find(x => x.principal) || conTel.find(x => !x.generico) || conTel[0];
  const pc = gente.find(x => x.principal) || gente[0];
  const correo = (pc?.correos || [])[0]?.correo;
  if (p) return { nombre: p.sin_nombre || p.generico ? (p.telefonos[0].etiqueta || 'el cliente') : p.nombre, telefono: p.telefonos[0].tel, correo };
  return correo ? { nombre: '', correo } : null;
}

const alias = (ctx, id) => (ctx.nombre ? ctx.nombre(id) : id);

function recursoBoton(F, k, texto) {
  const r = (F.portal?.recursos || []).find(x => x.k === k && x.url);
  return r ? h('a', { class: 'bt mini', href: r.url, target: '_blank', rel: 'noopener' }, icono('ext'), texto) : null;
}

function panelEquipo(ctx, F) {
  // Equipo por silla de la verdad única (asignaciones vigentes, sin personas de baja); nombres con ctx.nombre().
  const eq = F.verdad?.equipo || null;
  const sillasViejas = fuente(F.doc, 'asignaciones')?.datos?.sillas || {};
  const filas = Object.entries(SILLAS).map(([k, t]) => {
    const ids = eq ? (eq[k] || []).map(x => x.persona_id) : (sillasViejas[k] ? [sillasViejas[k]] : []);
    return ids.length ? { icono: 'persona', texto: `${t}: ${ids.map(i => ctx.nombre(i)).join(', ')}`, extra: k === 'account' ? 'responsable' : '' } : null;
  }).filter(Boolean);
  // F4: si la verdad única no trae sillas pero hay asignación vieja o responsable en la cabecera, se enseña esa (el vacío,
  // «Sin equipo asignado», solo cuando no hay nadie).
  if (!filas.length) {
    for (const [k, t] of Object.entries(SILLAS)) if (sillasViejas[k]) filas.push({ icono: 'persona', texto: `${t}: ${ctx.nombre(sillasViejas[k])}`, extra: k === 'account' ? 'responsable' : '' });
    if (!filas.length && F.c.responsable) filas.push({ icono: 'persona', texto: `Account: ${F.c.responsable}`, extra: 'responsable' });
  }
  // Servicios: la publicidad es «sí» si hay cuenta de Meta emparejada con gasto o leads en 35 días, sea alta o no (Concilia).
  const meta = fuente(F.doc, 'meta');
  const conMeta = pintable(meta) && ((meta.datos?.leads?.['35d'] || 0) > 0 || (meta.datos?.gasto?.['35d'] || 0) > 0 || (meta.datos?.estado_cuenta && meta.datos.estado_cuenta !== 'activa'));
  const sv = F.c.servicios || {};
  const SERV = [['publicidad', 'Publicidad'], ['crm_ghl', 'CRM en GoHighLevel'], ['seo', 'SEO'], ['outreach', 'Outreach'], ['mantenimiento', 'Mantenimiento']];
  const servicios = SERV.map(([k, t]) => {
    const val = k === 'publicidad' && conMeta ? 'sí' : sv[k];
    return val ? chipEstado(val === 'sí' ? 'verde' : val === 'no' ? 'gris' : 'ambar', `${t}: ${val}`) : null;
  }).filter(Boolean);
  return panel({ titulo: 'Equipo y servicios', icono: 'eq', sub: 'Quién lleva cada parte y qué tiene contratado' },
    h('div', { class: 'cuerpo pila' }, listaConIcono(filas, { vacio: { icono: 'persona', titulo: 'Sin equipo asignado', texto: 'Las asignaciones las mantiene Mili.' } }),
      servicios.length ? h('div', { class: 'fila' }, servicios) : null));
}

function pintarChat(caja, ctx, F, r) {
  const c = F.c;
  if (!r || r.negado) { caja.replaceChildren(vacio({ icono: 'candado', borde: true, titulo: 'El chat de este cliente no se puede abrir', texto: r?.negado || 'No visible para tu puesto.', quien: c.responsable })); return; }
  if (!r.valor) { caja.replaceChildren(vacio({ icono: 'chat', borde: true, titulo: 'Este cliente no tiene canal de chat', texto: 'No hay un canal de ClickUp con su nombre. Cuando se cree, sus mensajes aparecerán aquí y se podrá escribir desde la ficha.', quien: 'Mili' })); return; }
  const ch = r.valor;
  const url = `https://app.clickup.com/${ESPACIO_CLICKUP}/chat/r/${ch.canal}`;
  const tel = normalizarTelefono(contactoPrincipal(F.contactos?.valor)?.telefono);
  // Mensajes en la lista común (.lista-i) dentro de un panel con su propio desplazamiento (sin burbujas propias).
  const ul = h('ul', { class: 'lista-i' });
  const msgs = h('div', { class: 'cuerpo', role: 'log', 'aria-label': `Mensajes de #${ch.nombre || 'canal'}`, tabindex: '0', style: { maxHeight: '60vh', overflowY: 'auto' } }, ul);
  const pintarMsg = (m, mio = false, pendiente = false) => h('li', { style: { alignItems: 'flex-start', ...(mio ? { background: 'var(--accent-soft)' } : {}) } },
    h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(m.quien)),
    h('div', { class: 'pila', style: { flex: '1 1 0', minWidth: '0' } },
      h('div', { class: 'meta-linea' }, h('b', {}, m.quien), h('span', {}, fDiaHoraRO(new Date(+m.fecha).toISOString())),
        m.respuestas ? h('span', {}, `${m.respuestas} respuestas`) : null, pendiente ? chipEstado('ambar', 'Simulado: aún no se envía') : null),
      h('p', { class: m.oculto ? 'sub' : null, style: { whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' } }, m.texto)));
  let ultimoDia = '';
  const conDia = m => { const d0 = new Date(+m.fecha); const d = `${['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'][d0.getDay()]} ${d0.getDate()}-${_MES3[d0.getMonth()]}`; const out = d !== ultimoDia ? [h('li', {}, h('span', { class: 'titulo-seccion' }, d))] : []; ultimoDia = d; return out; };
  for (const m of ch.mensajes || []) ul.append(...conDia(m), pintarMsg(m));
  if (!(ch.mensajes || []).length) msgs.append(vacio({ icono: 'chat', titulo: 'Sin mensajes recientes', texto: 'Escribe el primero.' }));

  // Campo común (.campo, ronda 9); una línea: Intro envía.
  const area = h('input', { type: 'text', id: 'fx-chat-msg', placeholder: ctx.soloLectura ? 'En «ver como» no se escribe' : `Escribir en #${ch.nombre || 'canal'}…`, title: 'Intro envía', 'aria-label': 'Mensaje', disabled: ctx.soloLectura || null });
  const enviar = h('button', { type: 'button', class: 'bt pri', disabled: true }, icono('send'), 'Enviar');
  const ajustar = () => { enviar.disabled = !area.value.trim() || ctx.soloLectura; };
  const mandar = async () => {
    const texto = area.value.trim(); if (!texto || ctx.soloLectura) return;
    if (/contrase|password|clave\s*[:=]|token/i.test(texto)) { avisoFlotante('No mandes claves ni contraseñas por el chat', { icono: 'alert' }); return; }
    enviar.disabled = true;
    try {
      await ctx.accion({ herramienta: 'clickup', tipo: 'mensaje_chat', objeto: ch.canal, cliente_id: c.id, texto, vista_previa: { canal: `#${ch.nombre}`, texto } });
      const m = { quien: ctx.real.alias || ctx.real.nombre, fecha: Date.now(), texto };
      ul.append(...conDia(m), pintarMsg(m, true, true));
      msgs.scrollTop = msgs.scrollHeight;
      area.value = ''; ajustar();
      avisoFlotante('En cola (simulado). Se enviará a ClickUp cuando la app esté publicada');
    } catch (e) { avisoFlotante(`No se pudo: ${e.message}`, { icono: 'alert' }); enviar.disabled = false; }
  };
  area.addEventListener('input', ajustar);
  area.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); mandar(); } });
  enviar.addEventListener('click', mandar);

  const zoomBt = h('button', { type: 'button', class: 'bt mini', disabled: ctx.soloLectura || null, title: 'Crear una videollamada de Zoom (cuando se conecte la escritura de Zoom)', on: { click: async () => {
    try { await ctx.accion({ herramienta: 'zoom', tipo: 'crear_reunion', objeto: c.id, cliente_id: c.id, texto: `Videollamada con ${c.nombre}`, vista_previa: { tema: `${c.nombre} + Ranking Online` } }); avisoFlotante('Videollamada en cola (simulada): se creará cuando se conecte Zoom'); }
    catch (e) { avisoFlotante(e.message, { icono: 'alert' }); } } } }, icono('video'), 'Abrir la videollamada');
  caja.replaceChildren(
    panel({ titulo: `#${ch.nombre || 'canal'}`, icono: 'chat', sub: `ClickUp · últimos ${(ch.mensajes || []).length} mensajes`,
      acciones: h('div', { class: 'fila' },
          tel ? h('a', { class: 'bt mini', href: `sip:${tel.intl}@sip.zadarma.com`, title: `Llamar al cliente (${tel.mostrar}) con Zadarma`, on: { click: () => ctx.rastro({ accion: 'llamar', objeto: c.id, detalle: 'desde el chat' }) } }, icono('phone'), 'Llamar') : null,
          zoomBt,
          h('a', { class: 'bt mini', href: url, target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir en ClickUp')) },
      msgs,
      h('div', { class: 'tabla-ctl fila', style: { flexWrap: 'nowrap', alignItems: 'flex-end', borderBottom: '0', borderTop: 'thin solid var(--line-soft)' } },
        h('label', { class: 'campo', for: 'fx-chat-msg', style: { flex: '1 1 0' } }, h('span', { class: 'sr' }, 'Mensaje'), area), enviar)),
    h('p', { class: 'sub' }, 'Lectura real del canal de ClickUp (2-oct). Enviar deja el mensaje en la cola simulada con su vista previa: se manda de verdad cuando la app esté publicada con su llave en el servidor. Los mensajes con claves o contraseñas se ocultan.'));
  // Mensajes ya puestos en cola desde esta ficha (simulados)
  if (ctx.servidor) ctx.api('acciones?modulo=ficha').then(d => {
    // Fuera los envíos de prueba de la construcción (la cola es imborrable: se filtran aquí; ver dudas_pintura.md)
    const mios = (d.acciones || []).filter(a => a.tipo === 'mensaje_chat' && a.cliente_id === c.id && !/^prueba de la ficha/i.test(a.texto || '')).reverse();
    for (const a of mios) { const m = { quien: alias(ctx, a.quien), fecha: Date.parse(String(a.creada || '').replace(' ', 'T') + 'Z') || Date.now(), texto: a.texto }; ul.append(...conDia(m), pintarMsg(m, a.quien === ctx.real.id, true)); }
    msgs.scrollTop = msgs.scrollHeight;
  }).catch(() => {});
  requestAnimationFrame(() => { msgs.scrollTop = msgs.scrollHeight; });
}

async function pintarRastro(caja, ctx, F) {
  const c = F.c, doc = F.doc;
  const ev = [];
  // Lo que se ha pulsado en la ficha y en el resto de la app sobre este cliente
  if (ctx.servidor) {
    try {
      const [acc, ras] = await Promise.all([ctx.api('acciones?modulo=ficha'), ctx.api('rastro')]);
      for (const a of acc.acciones || []) if (a.cliente_id === c.id && !/^prueba de la ficha/i.test(a.texto || '')) ev.push({ fecha: a.creada, titulo: `${alias(ctx, a.quien)}: ${a.tipo === 'mensaje_chat' ? 'mensaje al chat' : a.tipo.replace(/_/g, ' ')} (simulado)`, detalle: a.texto, estado: 'ambar' });
      for (const r of ras.registro || []) {
        if (!String(r.clave || r.objeto || '').includes(c.id) && !String(r.datos || '').includes(c.id)) continue;
        if (r.accion === 'accion_simulada') continue;
        const que = { ver_lead: 'abrió los contactos o el chat', ver_dato: 'abrió datos protegidos (contactos, chat o mensajes)', ver_dato_denegado: 'intentó abrir datos protegidos sin permiso', alarma_vista: 'marcó un aviso como visto', llamar: 'pulsó «Llamar»', whatsapp: 'abrió WhatsApp', correo: 'abrió un correo', denegado: 'intentó abrir la ficha sin permiso' }[r.accion] || r.accion;
        ev.push({ fecha: r.creada, titulo: `${alias(ctx, r.quien)}: ${que}`, detalle: r.coleccion, estado: r.accion === 'denegado' ? 'rojo' : null });
      }
    } catch { /* sin rastro del servidor */ }
  }
  // La historia del cliente (de las fuentes)
  const rd = fuente(doc, 'reuniones')?.datos || {};
  for (const r of rd.historial || []) ev.push({ fecha: r.fecha, titulo: `Reunión: ${r.asunto}`, detalle: `${r.quien || ''} · ${r.fuente}` });
  for (const [mes, x] of Object.entries(fuente(doc, 'informes')?.datos || {})) if (x?.fecha_envio) ev.push({ fecha: x.fecha_envio, titulo: `Informe de ${mes === 'ago' ? 'agosto' : 'septiembre'} enviado`, detalle: x.prueba ? h('span', {}, conTickets(sinCorreoTapado(x.prueba), { boton: true })) : null, estado: 'verde' });
  for (const a of F.alarmas) ev.push({ fecha: a.desde, titulo: `Aviso: ${a.tipo}`, estado: a.gravedad });
  if (c.alta) ev.push({ fecha: c.alta, titulo: 'Alta del cliente' });
  ev.sort((a, b) => String(b.fecha || '').localeCompare(String(a.fecha || '')));
  const chips = chipsFiltro({ etiqueta: 'Ver', opciones: [{ valor: '', texto: 'Todo', cuenta: ev.length }, { valor: 'app', texto: 'Lo hecho en la app', icono: 'hist', cuenta: ev.filter(e => e.titulo.includes(':') && !/^(Reunión|Informe|Aviso)/.test(e.titulo)).length }], alCambiar: () => pintar() });
  const lista = h('div', { class: 'cuerpo' });
  const pintar = () => { const v = chips.valor(); const xs = v === 'app' ? ev.filter(e => !/^(Reunión|Informe|Aviso|Alta)/.test(e.titulo)) : ev;
    lista.replaceChildren(xs.length ? lineaTiempo(xs.slice(0, 60)) : vacio({ icono: 'hist', titulo: 'Nada todavía', texto: 'Lo que se marque, se pida o se escriba sobre este cliente desde la app queda aquí con quién y cuándo.' })); };
  pintar();
  caja.replaceChildren(panel({ titulo: 'Rastro del cliente', icono: 'hist', sub: 'Quién hizo qué y cuándo, y la historia del cliente. Nada se borra.', acciones: chips }, lista),
    ...(ctx.servidor ? [] : [avisoParcial('Sin servidor solo se ve la historia del cliente; el rastro de la app sale de servir.py.', { tipo: 'info' })]));
}
