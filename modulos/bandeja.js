// modulos/bandeja.js · M3 «Bandeja» v5 (3-oct-2026): una pantalla para TRABAJAR la bandeja, no para mirarla.
// Encargo de Tomás: «¿cómo puede ser que la parte de responder correos sea pequeñita y esté a la derecha?».
//
// Escritorio (contenido ≥ 1000 px): tres zonas, como Front, Zendesk, Missive o Superhuman:
//   · izquierda, lista compacta y estrecha con filtros (Míos · Sin responder · Quejas · Esperando al cliente · Todos) y orden
//     por urgencia o por antigüedad;
//   · centro, la CONVERSACIÓN (hilo legible, mensajes plegables) y debajo el EDITOR, grande y siempre a la vista, con el
//     borrador de la IA ya cargado, su calidad y lo que falta, plantillas, adjuntos (simulados), firma, «Enviar» y
//     «Enviar y siguiente»;
//   · derecha, el contexto del cliente, plegable (gravedad, account, campaña y leads, tareas, reunión, impago si lo ve).
// 1024 (contenido 700-999): lista + conversación; el contexto pasa a pestaña. 390: lista → conversación a pantalla completa
// (ruta #/bandeja/<id>) con el editor fijo abajo.
// Procesar la bandeja: al enviar se abre el siguiente; j/k moverse, r responder, e despachado, a asignar, p esperando al
// cliente, ⌘↵ enviar y siguiente, z deshacer. Lo que saca un correo de la bandeja (enviar, despachado, esperando) se puede
// deshacer durante 5 s y después va a la cola SIMULADA (ctx.accion → envios.py): nada sale de la app. El estado de cada
// envío (simulado / pendiente / confirmado) se ve en el hilo (/api/envios).
// Datos: data/bandeja/bandeja.json (generar_bandeja.py) y data/bandeja/hilos.json (generar_hilos.py), recortados por servir.py.
// Guía de diseño: sin hoja propia; solo tokens (var(--…)) y clases comunes. El borrador lo da ia.py (/api/ia/borrador).

import {
  h, fmt, icono, chipEstado, chipsFiltro, vacio, avisoParcial, panel, frescura, logoCliente, iniciales, avisoFlotante,
  pieFase2, menuMas, botonConfirmar,
} from '../componentes.js';
import { MODULOS } from './indice.js';
import { iaDe, estilos as estilosIA, ETIQUETA_GRAVEDAD } from './ia_componentes.js';
import { conDeshacer } from './_deshacer.js';
import { plegarConsejo } from './_plegar_consejo.js';

const ID = 'bandeja';

// Revisión 44 (textos cortados): lo que la pantalla corta con «…» lleva el texto entero en el title.
const _SEL_CORTE = '.det, .mot, .sub, .t, .chip, summary, b, small';
function vigilarCortes(raiz) {
  if (!raiz || raiz.__cortes) return;
  raiz.__cortes = true;
  let t = 0;
  const mirar = () => { t = 0; for (const el of raiz.querySelectorAll(_SEL_CORTE)) {
    if (el.title || (el.closest('[title]') !== null && el.closest('[title]') !== el) || !el.isConnected) continue;
    if (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 2) { const s = el.textContent.trim(); if (s && s.length > 8) el.title = s; } } };
  new MutationObserver(() => { if (!t) t = setTimeout(mirar, 400); }).observe(raiz, { childList: true, subtree: true });
}

// §2.3: fechas con el formato único de la app: «2-oct» y «2-oct, 17:34».
const _MES3 = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const _fechaDe = iso => (iso ? new Date(String(iso).length <= 10 ? `${iso}T12:00:00` : String(iso).replace(' ', 'T')) : null);
const fDiaRO = iso => { const d = _fechaDe(iso); return !d ? '—' : Number.isNaN(+d) ? String(iso) : `${d.getDate()}-${_MES3[d.getMonth()]}`; };
const fDiaHoraRO = iso => { const d = _fechaDe(iso); return !d ? '—' : Number.isNaN(+d) ? String(iso) : `${d.getDate()}-${_MES3[d.getMonth()]}, ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; };

const PLANTILLAS = [
  { id: 'recibido', texto: 'Recibido', cuerpo: n => `Hola${n ? ' ' + n : ''},\n\nRecibido, gracias. Lo estoy mirando y te digo algo antes de que acabe el día.\n\nUn saludo,` },
  { id: 'datos', texto: 'Pedir un dato', cuerpo: n => `Hola${n ? ' ' + n : ''},\n\nPara avanzar con esto me falta un dato: [qué dato]\n\nEn cuanto lo tenga, lo dejo hecho.\n\nUn saludo,` },
  { id: 'resuelto', texto: 'Resuelto', cuerpo: n => `Hola${n ? ' ' + n : ''},\n\nYa está resuelto: [qué se ha hecho]\n\nSi ves cualquier cosa rara, me dices y lo miramos.\n\nUn saludo,` },
  { id: 'llamada', texto: 'Mejor por teléfono', cuerpo: n => `Hola${n ? ' ' + n : ''},\n\nEsto lo vemos mejor en una llamada de diez minutos. ¿Te va bien hoy o mañana por la mañana?\n\nUn saludo,` },
  { id: 'queja', texto: 'Queja: te llamo hoy', cuerpo: n => `Hola${n ? ' ' + n : ''},\n\nTienes razón en escribirnos y siento la espera. Te llamo hoy [hora] para verlo contigo y te dejo por escrito lo que acordemos.\n\nUn saludo,` },
];
const MOTIVOS_NO_APLICA = ['Ya contestado por otra vía (WhatsApp o teléfono)', 'No pide respuesta (agradecimiento, acuse, «ok»)', 'Es ruido o un aviso automático', 'No es de este cliente', 'Ex cliente o baja', 'Otro motivo'];
// lo que saca el correo de la bandeja; «esperando_cliente» lo pasa a «Esperando al cliente»; lo demás (nota, tarea, aviso, asignar) no lo saca
const TERMINALES = new Set(['responder', 'cerrar', 'no_aplica', 'despachado', 'llamada_devuelta']);
const ETQ = { responder: 'Respuesta', nota_interna: 'Nota interna', asignar: 'Asignación', cerrar: 'Cierre', no_aplica: '«No aplica»', llamada_devuelta: 'Llamada devuelta',
  despachado: 'Despachado', esperando_cliente: 'Esperando al cliente', tarea: 'Tarea en ClickUp', aviso_account: 'Aviso al account' };
const etiquetaTipo = t => ETQ[t] || t;
const ESTADO_ENVIO = { simulado: ['gris', 'Simulado: no ha salido'], pendiente: ['ambar', 'Pendiente de salir'], enviado: ['azul', 'Enviado: comprobando'],
  confirmado: ['verde', 'Confirmado en Desk'], fallido: ['rojo', 'Ha fallado'], rebotado: ['rojo', 'Rebotado'] };
const PUESTOS_ASIGNAR = ['direccion', 'operaciones', 'proyectos'];   // R16
const puedeAsignar = ctx => (ctx.persona?.puestos || []).some(p => PUESTOS_ASIGNAR.includes(p));

const relojTxt = horas => {
  if (horas === null || horas === undefined) return '—';
  const hr = Math.round(horas);
  return hr < 24 ? `${hr} h` : `${Math.floor(hr / 24)} d ${hr % 24} h`;
};
const normal = t => String(t ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const nom1 = t => String(t || '').trim().split(/\s+/)[0] || '';
const yoDe = ctx => (ctx.persona || {}).id;
const leerS = k => { try { return localStorage.getItem(k); } catch { return null; } };
const guardarS = (k, v) => { try { localStorage.setItem(k, v); } catch { /* sin almacenamiento */ } };
function edadH(fecha) {
  if (!fecha) return null;
  const d = new Date(String(fecha).replace(' ', 'T'));
  return Number.isNaN(+d) ? null : Math.max(0, (Date.now() - d) / 36e5);
}
const fres = (f, nombre) => f ? { fuente: nombre, edad_h: edadH(f.hora), estado: f.estado === 'bien' ? 'ok' : 'viejo' } : { fuente: nombre, estado: 'sin datos' };
const RX_HUECO = /\[[^\]\n]{1,80}\]/g;
/** «2026-10-03T03:22:10Z» (UTC) → «2026-10-03 05:22» en la hora del navegador. */
const horaLocal = iso => { const s = String(iso || ''); if (!/Z$|[+-]\d\d:?\d\d$/.test(s)) return s; const d = new Date(s); if (Number.isNaN(+d)) return s;
  const p2 = n => String(n).padStart(2, '0'); return `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())} ${p2(d.getHours())}:${p2(d.getMinutes())}`; };
const conTitulo = (el, t) => { if (t) el.title = t; return el; };
const origenTxt = r => (r.origen === 'vivo' ? `IA · ${String(r.generado || '').slice(11, 16)}` : r.origen === 'precalculado' ? `Propuesta del ${fDiaRO(r.generado)}` : '');
const kbd = t => h('kbd', { style: { font: 'var(--t-meta)', border: 'var(--borde)', borderRadius: 'var(--r-s)', padding: '0 var(--s-1)', background: 'var(--card)', color: 'var(--mid)' } }, t);

// =============================================================== render
export default {
  id: ID,
  titulo: 'Bandeja',
  grupo: 'Hoy',
  async render(cont, ctx) {
    vigilarCortes(cont);
    estilosIA();
    let D;
    try { D = await ctx.datosModulo('bandeja/bandeja'); }
    catch (e) {
      cont.append(vacio({ icono: 'inbox', tono: 'aviso', borde: true, titulo: 'No se pudo leer la bandeja', texto: String(e?.message || e), quien: 'Tomás (regenerar con fuentes_bandeja/generar_bandeja.py)' }));
      return;
    }
    let acciones = [];
    if (ctx.servidor) {
      try { acciones = (await ctx.api(`acciones?modulo=${ID}`)).acciones || []; } catch { /* sin cola: no pasa nada */ }
    }
    // el estado sigue vivo entre rutas (#/bandeja ↔ #/bandeja/<id> en el móvil) y al volver: borradores, envíos con
    // «Deshacer» en marcha y lo escrito no se pierden
    const clave = `${(ctx.real || ctx.persona).id}|${ctx.persona.id}|${D.generado}`;
    let S;
    if (MEM && MEM.clave === clave) { S = MEM.S; S.D = D; refrescarAcciones(S, acciones); aplicarRuta(ctx, S); }
    else { S = crearEstado(ctx, D, acciones); MEM = { clave, S }; }
    S.cont = cont;
    S.rehacer = () => { cont.replaceChildren(); pintar(cont, ctx, S); };
    S.rehacer();
    plegarConsejo(cont);   // molde común (U2): el «Qué haría yo hoy aquí» en su línea, sin empujar la zona de trabajo
    cargarEnvios(ctx, S);
    instalarEscuchas(ctx, S);
  },
};

let MEM = null;
const ESCUCHAS = {};
function instalarEscuchas(ctx, S) {
  for (const [ev, fn, opc] of Object.values(ESCUCHAS)) window.removeEventListener(ev, fn, opc);
  // al cambiar de anchura de verdad (no al abrir el teclado del móvil) se rehace con la distribución que toque
  let ultimo = modoDe(S.cont);
  const alCambiar = () => {
    if (!S.cont.isConnected) return;
    const m = modoDe(S.cont);
    if (m !== ultimo) { ultimo = m; guardarTexto(S); S.rehacer(); } else S.ajustar?.();
  };
  const tecla = teclado(ctx, S);   // lo pendiente de «Deshacer» lo encola _deshacer.js al cambiar de pantalla
  Object.assign(ESCUCHAS, { resize: ['resize', alCambiar, false], tecla: ['keydown', tecla, true] });
  for (const [ev, fn, opc] of Object.values(ESCUCHAS)) window.addEventListener(ev, fn, opc);   // teclado en captura: antes que j/k/e de ayudas.js
}
function refrescarAcciones(S, acciones) {
  const porObjeto = agrupar(acciones);
  S.porObjeto = porObjeto;
  for (const x of S.items) {
    const srv = porObjeto.get(String(x.numero)) || [];
    if (srv.length >= x.acciones.length) x.acciones = srv;
    marcarDeAcciones(x);
  }
}
function aplicarRuta(ctx, S) {
  S.aviso = null;
  S.vistaMovil = ctx.params[0] ? 'conv' : 'lista';
  if (!ctx.params[0]) return;
  const id = decodeURIComponent(ctx.params[0]);
  const x = S.items.find(y => y.id === id);
  if (!x) { S.aviso = 'Ese correo ya no está pendiente o es de un cliente que no llevas.'; return; }
  S.sel = x.id;
  if (!filtrar(ctx, S).some(y => y.id === id)) S.filtro = x.hecho ? 'hechos' : x.esperando ? 'esperando' : x.auto ? 'auto' : x.viejo ? 'viejos' : 'todos';
}
function agrupar(acciones) {
  const porObjeto = new Map();
  for (const a of acciones.slice().sort((p, q) => String(p.creada || p.hora || p.id).localeCompare(String(q.creada || q.hora || q.id)))) {
    const k = String(a.objeto);
    if (!porObjeto.has(k)) porObjeto.set(k, []);
    porObjeto.get(k).push(a);
  }
  return porObjeto;
}

function modoDe(cont) {
  const w = cont.getBoundingClientRect().width || window.innerWidth;
  return w >= 1000 ? 'tres' : w >= 680 ? 'dos' : 'uno';
}

function crearEstado(ctx, D, acciones) {
  const cliPorId = new Map(ctx.clientes.map(c => [c.id, c]));
  const correos = (D.correos || []).map(x => ({ ...x, tipo: 'correo', dia: (x.desde || '').slice(0, 10) }));
  const llamadas = (D.llamadas || []).map(x => ({ ...x, tipo: 'llamada', numero: x.id }));
  for (const x of [...correos, ...llamadas]) {   // el account siempre de la verdad única
    const v = x.cliente_id ? ctx.verdad?.(x.cliente_id) : null;
    if (v && 'account' in v) x.account_id = v.account || null;
  }
  const porObjeto = agrupar(acciones);
  const items =[...correos, ...llamadas].map(x => {
    const it = { ...x, cli: x.cliente_id ? cliPorId.get(x.cliente_id) : null, acciones: porObjeto.get(String(x.numero)) || [],
      account: x.account_id ? ctx.nombre(x.account_id) : (x.cliente_id ? 'Sin account' : 'sin cliente') };
    marcarDeAcciones(it);
    return it;
  });
  const todo = ctx.nivel === 'todo';
  const esAccount = (ctx.persona?.puestos || []).includes('account');
  const S = { D, items, todo, triaje: D.triaje || [], porObjeto, sel: null, q: '', acc: leerS('ro.bandeja.account2') || '',
    filtro: null, orden: leerS('ro.bandeja.orden') || 'urgencia', alt: null, pestCentro: 'conv',
    ctxAbierto: leerS('ro.bandeja.contexto') === null ? null : leerS('ro.bandeja.contexto') === '1', ampliado: false, textos: new Map(), borradores: new Map(),
    clientes: new Map(), hilos: null, envios: new Map(), pendientes: new Map(), adjuntos: new Map(), esAccount };
  const mios = items.filter(FILTROS[0].f.bind(null, ctx)).length;
  S.filtro = sessionGet('ro.bandeja.filtro') || (esAccount && mios ? 'mios' : 'sin_responder');
  aplicarRuta(ctx, S);
  return S;
}
function marcarDeAcciones(it) {
  it.hecho = null; it.esperando = null; it.asignadoCola = null;
  for (const a of it.acciones) {
    if (TERMINALES.has(a.tipo)) it.hecho = a;
    else if (a.tipo === 'esperando_cliente') it.esperando = a;
    else if (a.tipo === 'asignar') it.asignadoCola = a;
  }
}
function sessionGet(k) { try { return sessionStorage.getItem(k); } catch { return null; } }
function sessionSet(k, v) { try { sessionStorage.setItem(k, v); } catch { /* nada */ } }

// ---------------------------------------------------------------- filtros y orden
const vivo = x => !x.hecho && !x.esperando && !x.auto && !x.viejo && !x.pendiente;
const FILTROS = [
  { id: 'mios', texto: 'Míos', icono: 'persona', f: (ctx, x) => vivo(x) && [x.account_id, x.asignado_id, x.sono_a_id].includes(yoDe(ctx)) },
  { id: 'sin_responder', texto: 'Sin responder', icono: 'mail', f: (ctx, x) => vivo(x) },
  { id: 'quejas', texto: 'Quejas', icono: 'alert', f: (ctx, x) => !x.hecho && !x.pendiente && x.queja, rojo: true },
  { id: 'esperando', texto: 'Esperando al cliente', corto: 'Esperando', icono: 'clock', f: (ctx, x) => !x.hecho && !x.pendiente && !!x.esperando },
  { id: 'todos', texto: 'Todos', icono: 'inbox', f: (ctx, x) => !x.hecho && !x.pendiente && !x.auto && !x.viejo },   // automáticos y de más de un mes, en «Más»
];
const MAS_FILTROS = [
  { id: 'auto', texto: 'Avisos automáticos y reenvíos', f: (ctx, x) => !x.hecho && x.auto },
  { id: 'viejos', texto: 'Más de un mes sin respuesta', f: (ctx, x) => !x.hecho && x.viejo },
  { id: 'hechos', texto: 'Ya hechos (en la cola)', f: (ctx, x) => !!x.hecho },
];
const RANGO = { rojo: 0, ambar: 1, verde: 2 };
function filtrar(ctx, S, id = S.filtro) {
  const f = [...FILTROS, ...MAS_FILTROS].find(y => y.id === id) || FILTROS[1];
  const q = normal(S.q);
  return S.items.filter(x => f.f(ctx, x))
    .filter(x => !S.acc || (x.cliente_id ? (x.account_id ? ctx.nombre(x.account_id) : 'Sin account') : 'Correos sin cliente') === S.acc)
    .filter(x => !q || normal(`${x.cliente || ''} ${x.asunto || ''} ${x.numero || ''} ${x.numero_oculto || ''} ${x.account || ''}`).includes(q))
    .sort(S.orden === 'antiguo'
      ? (a, b) => (!a.cliente_id - !b.cliente_id) || (b.horas || 0) - (a.horas || 0)   // los sin cliente (no se contestan), al final
      : (a, b) => (!a.cliente_id - !b.cliente_id) || (b.queja - a.queja) || ((RANGO[a.gravedad] ?? 3) - (RANGO[b.gravedad] ?? 3)) || (b.horas || 0) - (a.horas || 0));
}

// ---------------------------------------------------------------- pantalla
function pintar(cont, ctx, S) {
  const vivos = S.items.filter(vivo);
  const rojo = vivos.filter(x => x.gravedad === 'rojo');
  const nC = vivos.filter(x => x.tipo === 'correo').length, nL = vivos.filter(x => x.tipo === 'llamada').length;
  const deskOk = !!S.D.fuentes?.desk;
  ctx.titulo('Bandeja', `${fmt.plural(nC, 'correo', 'correos')} y ${fmt.plural(nL, 'llamada', 'llamadas')} por atender${deskOk && rojo.length ? ` · ${rojo.length} con más de 48 h` : ''}${S.todo ? ' · toda la casa' : ''}`);
  S.modo = modoDe(cont);

  // otras vistas (reparto, WhatsApp, de dónde sale): en el menú «Más» de la lista; la barra de arriba solo al estar en una de ellas
  const pendTriaje = S.triaje.filter(t => !S.porObjeto.has(String(t.numero))).length;
  const otras = S.otras = [
    S.todo ? { id: 'triaje', texto: `Correos sin responsable (${fmt.num(pendTriaje)})`, icono: 'persona' } : null,
    { id: 'whatsapp', texto: 'WhatsApp uno a uno', icono: 'wa' },
    { id: 'como', texto: 'De dónde sale cada correo', icono: 'info' },
  ].filter(Boolean);
  const barra = h('div', { class: 'fila', 'data-bdj': 'barra', style: { justifyContent: 'space-between', marginBottom: 'var(--s-3)' } },
    h('div', { class: 'fila' },
      S.alt ? h('button', { type: 'button', class: 'bt mini', on: { click: () => { S.alt = null; S.rehacer(); } } }, icono('volver', { clase: 's' }), 'Volver a la bandeja') : null,
      deskOk ? chipEstado(rojo.length ? 'rojo' : 'verde', rojo.length ? `${rojo.length} con más de 48 h` : 'Nada de más de 48 h') : chipEstado('gris', 'Desk sin dato'),
      vivos.some(x => x.queja) ? chipEstado('rojo', `${vivos.filter(x => x.queja).length} ${vivos.filter(x => x.queja).length === 1 ? 'queja' : 'quejas'}`) : null,
      frescura(fres(S.D.fuentes?.desk, 'Desk')), frescura(fres(S.D.fuentes?.zadarma, 'Zadarma'))),
    h('div', { class: 'fila' },
      S.modo === 'uno' ? null : h('span', { class: 'sub fila', style: { gap: 'var(--s-1)' }, title: 'Atajos de la Bandeja (con el foco fuera de la caja de texto)' },
        kbd('j'), kbd('k'), 'moverse', kbd('r'), 'responder', kbd('e'), 'despachado', kbd('⌘↵'), 'enviar y siguiente'),
      menuMas({ texto: 'Más', etiqueta: 'Otras vistas de la bandeja', items: otras.map(o => ({ texto: o.texto, icono: o.icono, activo: S.alt === o.id, alPulsar: () => { guardarTexto(S); S.alt = o.id; S.rehacer(); } })) })));
  const convMovil = S.modo === 'uno' && S.sel && S.vistaMovil === 'conv' && !S.alt;
  if (S.alt) cont.append(barra);   // en la zona de trabajo no hay barra: todo el alto para leer y escribir

  if (!S.todo && !ctx.clientesVisibles.length) {
    cont.append(avisoParcial('Todavía no tienes clientes asignados en la tabla de asignaciones: la bandeja sale vacía. Las asignaciones las mantiene Mili.', { titulo: 'Sin cartera.' }));
  }
  if (S.alt) {
    const z = h('div', {});
    cont.append(z);
    if (S.alt === 'triaje') pintarTriaje(z, ctx, S);
    else if (S.alt === 'whatsapp') pintarWhatsapp(z);
    else pintarComo(z, ctx, S);
    return;
  }
  if (convMovil) pintarConvMovil(cont, ctx, S);
  else pintarTrabajo(cont, ctx, S);

  const f2 = pieFase2([ctx.indicador('account.opinion_del_cliente_sobre_sus_leads') || { nombre: 'Opinión del cliente sobre sus leads', medible: 'no', medible_porque: 'no hay campo único «calidad del lead»; se pedirá en la bandeja cuando exista' },
    { nombre: 'WhatsApp uno a uno sin contestar', medible: 'no', medible_porque: 'llega cuando se conecte WhatsApp Business, no antes del 16-oct' }]);
  if (f2) { f2.style.marginTop = 'var(--s-6)'; cont.append(f2); }
}

// ---------------------------------------------------------------- zona de trabajo (escritorio y 1024)
function pintarTrabajo(cont, ctx, S) {
  const tres = S.modo === 'tres', uno = S.modo === 'uno';
  const colLista = h('section', { class: 'panel', 'data-bdj': 'lista-col', 'aria-label': 'Correos y llamadas',
    style: { display: 'flex', flexDirection: 'column', minHeight: '0', minWidth: '0' } });
  const colCentro = h('section', { class: 'panel', 'data-bdj': 'conversacion', 'aria-label': 'Conversación y respuesta',
    style: { display: 'flex', flexDirection: 'column', minHeight: '0', minWidth: '0' } });
  const colCtx = h('aside', { class: 'panel', 'data-bdj': 'contexto', 'aria-label': 'Contexto del cliente',
    style: { display: 'flex', flexDirection: 'column', minHeight: '0', minWidth: '0' } });
  // el contexto del cliente, abierto si hay sitio para que la conversación siga siendo lo grande (contenido ≥ 1.280 px); si no, plegado
  if (S.ctxAbierto === null) S.ctxAbierto = (cont.getBoundingClientRect().width || 0) >= 1280;
  const cols = uno ? 'minmax(0, 1fr)'
    : tres ? `minmax(260px, 300px) minmax(0, 1fr) ${S.ctxAbierto ? 'minmax(240px, 288px)' : '48px'}`
      : 'minmax(232px, 272px) minmax(0, 1fr)';
  const raiz = h('div', { 'data-bdj': 'trabajo', style: { display: 'grid', gap: 'var(--s-3)', gridTemplateColumns: cols, alignItems: 'stretch' } },
    colLista, uno ? null : colCentro, tres ? colCtx : null);
  cont.append(raiz);
  S.raiz = raiz; S.colLista = colLista; S.colCentro = colCentro; S.colCtx = colCtx;

  if (!uno) asegurarSel(ctx, S);
  pintarColLista(ctx, S);
  if (!uno) { pintarCentro(ctx, S); if (tres) pintarContexto(ctx, S); }

  // la zona ocupa lo que queda de pantalla: el editor siempre a la vista sin desplazarse
  // Si «Qué haría yo hoy aquí» está desplegado y no deja sitio, la zona ocupa la pantalla entera (menos la cabecera) y la
  // app la sube una vez (el consejo queda encima, a un desplazamiento hacia arriba).
  let subida = false;
  S.ajustar = () => {
    if (!raiz.isConnected) return;
    if (uno) { raiz.style.height = ''; return; }
    const top = raiz.getBoundingClientRect().top + window.scrollY;
    const cabecera = (document.querySelector('.topbar')?.getBoundingClientRect().height) || 64;
    const cabe = window.innerHeight - top - 16;
    const alto = cabe >= 560 ? cabe : Math.max(480, window.innerHeight - cabecera - 24);
    raiz.style.height = `${Math.round(alto)}px`;
    // la subida espera un poco: el consejo llega tarde y se pliega solo (_plegar_consejo.js); solo si aun así no cabe
    if (cabe < 560 && !subida && window.scrollY < 4) {
      subida = true;
      setTimeout(() => {
        const t2 = raiz.getBoundingClientRect().top + window.scrollY;
        if (raiz.isConnected && window.innerHeight - t2 - 16 < 560 && window.scrollY < 4) window.scrollTo({ top: Math.max(0, t2 - cabecera - 12) });
        else S.ajustar();
      }, 900);
    }
    ajustarEditor(S);
  };
  S.ajustar();
  requestAnimationFrame(() => S.ajustar());
  // la carcasa mete «Qué haría yo hoy aquí» encima después de pintar: se vuelve a medir
  const main = cont.closest('main') || cont.parentElement;
  if (main && typeof ResizeObserver !== 'undefined') {
    const ro = new ResizeObserver(() => { if (!raiz.isConnected) { ro.disconnect(); return; } S.ajustar(); });
    for (const el of main.children) if (el !== cont) ro.observe(el);
    new MutationObserver(() => { if (!raiz.isConnected) return; for (const el of main.children) if (el !== cont) ro.observe(el); S.ajustar(); }).observe(main, { childList: true });
  }
}

function asegurarSel(ctx, S) {
  const filas = filtrar(ctx, S);
  if (!filas.some(x => x.id === S.sel)) S.sel = filas[0]?.id || (S.items.find(x => x.id === S.sel) ? S.sel : null);
}

// ---------------------------------------------------------------- lista (izquierda)
function pintarColLista(ctx, S) {
  const col = S.colLista;
  col.replaceChildren();
  const cuenta = id => filtrar(ctx, { ...S, q: '' }, id).length;
  const chips = h('div', { class: 'chips-f', role: 'group', 'aria-label': 'Filtro' }, FILTROS.map(f => {
    const n = cuenta(f.id);
    return h('button', { type: 'button', 'data-filtro': f.id, 'aria-pressed': String(S.filtro === f.id), title: f.texto, on: { click: () => ponerFiltro(ctx, S, f.id) } },
      f.corto || f.texto, h('span', { class: `cu${f.rojo && n ? ' rojo' : ''}` }, fmt.num(n)));
  }));
  const otra = MAS_FILTROS.find(f => f.id === S.filtro);
  const mas = menuMas({ texto: otra ? otra.texto : 'Más', etiqueta: 'Más filtros y vistas', activo: !!otra,
    items: [...MAS_FILTROS.map(f => ({ texto: `${f.texto} (${fmt.num(cuenta(f.id))})`, icono: 'filtro', activo: S.filtro === f.id, alPulsar: () => ponerFiltro(ctx, S, f.id) })),
      ...(S.otras || []).map(o => ({ texto: o.texto, icono: o.icono, alPulsar: () => { guardarTexto(S); S.alt = o.id; S.rehacer(); } }))] });
  mas.dataset.bdj = 'mas';
  const orden = h('div', { class: 'segm', role: 'group', 'aria-label': 'Orden' },
    [['urgencia', 'Urgencia'], ['antiguo', 'Más antiguo']].map(([v, t]) => h('button', { type: 'button', 'data-orden': v, 'aria-pressed': String(S.orden === v),
      on: { click: () => { S.orden = v; guardarS('ro.bandeja.orden', v); if (S.modo !== 'uno') { const f = filtrar(ctx, S); if (f.length) S.sel = f[0].id; } pintarColLista(ctx, S); if (S.modo !== 'uno') { pintarCentro(ctx, S); pintarContexto(ctx, S); } } } }, t)));
  const buscar = h('input', { type: 'search', placeholder: 'Buscar cliente, asunto o RO-…', 'aria-label': 'Buscar en la bandeja', value: S.q, style: { width: '100%' } });
  buscar.addEventListener('input', () => { S.q = buscar.value; pintarFilas(ctx, S); });
  let selAcc = null;
  if (S.todo) {
    const c = new Map();
    for (const x of S.items.filter(vivo)) { const g = x.cliente_id ? (x.account_id ? ctx.nombre(x.account_id) : 'Sin account') : 'Correos sin cliente'; c.set(g, (c.get(g) || 0) + 1); }
    const accs = [...c.entries()].sort((a, b) => (a[0] === 'Correos sin cliente') - (b[0] === 'Correos sin cliente') || b[1] - a[1]);
    selAcc = h('select', { 'aria-label': 'Account', style: { width: '100%' }, on: { change: () => { S.acc = selAcc.value; guardarS('ro.bandeja.account2', S.acc); pintarColLista(ctx, S); } } },
      h('option', { value: '' }, 'Todos los accounts'), accs.map(([a, n]) => h('option', { value: a }, `${a} (${n})`)));
    selAcc.value = S.acc;
  }
  const cab = h('div', { class: 'pila', style: { padding: 'var(--s-3)', gap: 'var(--s-2)', borderBottom: 'var(--borde-suave)', flex: 'none' } },
    chips,
    (orden.style.justifySelf = 'start', orden),
    h('div', { class: 'tabla-ctl', style: { display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: 'var(--s-2)', alignItems: 'center' } }, buscar, mas),
    selAcc ? h('div', { class: 'tabla-ctl' }, selAcc) : null);
  const lista = h('div', { role: 'list', 'aria-label': 'Correos y llamadas', 'data-bdj': 'lista', style: { flex: '1 1 auto', minHeight: '0', overflowY: S.modo === 'uno' ? 'visible' : 'auto' } });
  const pie = h('div', { 'data-bdj': 'pie', style: { flex: 'none', borderTop: 'var(--borde-suave)' } });
  col.append(...[cab, S.aviso ? h('div', { style: { padding: 'var(--s-3)' } }, avisoParcial(S.aviso, { tipo: 'info' })) : null, lista, pie].filter(Boolean));
  S.lista = lista; S.pie = pie;
  pintarFilas(ctx, S);
  pintarPie(ctx, S);
}

function ponerFiltro(ctx, S, id) {
  S.filtro = id; sessionSet('ro.bandeja.filtro', id);
  if (S.modo !== 'uno') { const f = filtrar(ctx, S); if (!f.some(x => x.id === S.sel)) S.sel = f[0]?.id || null; }
  pintarColLista(ctx, S);
  if (S.modo !== 'uno') { pintarCentro(ctx, S); pintarContexto(ctx, S); }
}

function pintarFilas(ctx, S) {
  const filas = filtrar(ctx, S);
  S.filas = filas;
  const lista = S.lista;
  lista.replaceChildren();
  if (!filas.length) {
    const celebrar = ['mios', 'sin_responder', 'quejas'].includes(S.filtro) && !S.q;
    lista.append(h('div', { style: { padding: 'var(--s-4)' } }, vacio({ icono: celebrar ? 'ok' : 'inbox', tono: celebrar ? 'celebrar' : 'neutro',
      titulo: S.q ? 'Nada coincide con la búsqueda' : celebrar ? 'Bandeja a cero aquí' : 'Nada en este filtro',
      texto: S.q ? 'Prueba con el nombre del cliente o el número del ticket (RO-…).' : S.filtro === 'hechos' ? 'Lo que contestes o despaches aparece aquí hasta que salga de verdad.' : S.filtro === 'esperando' ? 'Cuando marques «Esperando al cliente», el correo espera aquí su respuesta.' : `Nada de ${S.todo ? 'la casa' : 'tus clientes'} espera aquí.` })));
    return;
  }
  const limite = Math.max(80, filas.findIndex(x => x.id === S.sel) + 1);
  for (const x of filas.slice(0, limite)) lista.append(fila(x, ctx, S));
  if (filas.length > limite) lista.append(h('p', { class: 'sub', style: { padding: 'var(--s-3)' } }, `Y ${filas.length - limite} más: busca por cliente o número.`));
}

/** Una fila compacta: cliente y espera arriba, asunto debajo. Toda ella pulsable (y con teclado). */
function fila(x, ctx, S) {
  const sel = x.id === S.sel && S.modo !== 'uno';
  const titulo = x.tipo === 'llamada' ? `Llamada perdida · ${x.llamadas} ${x.llamadas === 1 ? 'vez' : 'veces'}` : (x.asunto || '(sin asunto)');
  const est = x.hecho ? 'gris' : x.gravedad || 'gris';
  const abrir = () => abrirItem(ctx, S, x.id);
  return h('div', { role: 'listitem', tabindex: '0', 'data-id': x.id, 'data-fila': '', 'aria-current': String(sel),
    'aria-label': `${x.cliente || 'Sin cliente'}: ${titulo}. Esperando ${relojTxt(x.horas)}`,
    style: { display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: 'var(--s-1) var(--s-2)', padding: 'var(--s-2) var(--s-3)', cursor: 'pointer',
      borderBottom: 'var(--borde-suave)', borderLeft: `4px solid ${sel ? 'var(--accent)' : x.queja ? 'var(--bad)' : 'transparent'}`, background: sel ? 'var(--accent-soft)' : null },
    on: { click: abrir, keydown: e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); abrir(); } } } },
    h('b', { class: 't', style: { whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', minWidth: '0', font: 'var(--t-h3)' } },
      x.tipo === 'llamada' ? icono('phone', { clase: 's' }) : null, ' ', x.cliente || (x.numero_oculto ? `Número ${x.numero_oculto}` : 'Sin cliente')),
    x.hecho ? chipEstado('azul', 'En cola') : x.pendiente ? chipEstado('azul', 'Saliendo…') : h('span', { class: `chip ${est}`, title: 'Tiempo esperando, en horas laborables (de lunes a viernes)' }, relojTxt(x.horas)),
    h('span', { class: 'det', style: { whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', minWidth: '0', font: 'var(--t-meta)', color: 'var(--mid)' } }, titulo),
    h('span', { class: 'fila', style: { gap: 'var(--s-1)', justifyContent: 'flex-end' } },
      x.queja ? chipEstado('rojo', 'Queja') : x.boletin ? chipEstado('gris', 'Boletín') : x.auto ? chipEstado('gris', 'Automático') : null,
      x.esperando ? chipEstado('gris', 'Esperando') : null,
      S.todo && x.account_id ? h('span', { class: 'av s', title: `Account: ${x.account}`, 'aria-label': `Account: ${x.account}` }, iniciales(x.account)) : null));
}

function abrirItem(ctx, S, id, { foco = false } = {}) {
  guardarTexto(S);
  S.sel = id;
  if (S.modo === 'uno') { irMovil(ctx, S, id, { empujar: S.vistaMovil !== 'conv' }); return; }
  S.lista?.querySelectorAll('[data-id]').forEach(el => {
    const on = el.dataset.id === id;
    el.setAttribute('aria-current', String(on));
    el.style.background = on ? 'var(--accent-soft)' : '';
    const x = S.items.find(y => y.id === el.dataset.id);
    el.style.borderLeft = `4px solid ${on ? 'var(--accent)' : x?.queja ? 'var(--bad)' : 'transparent'}`;
    if (on) el.scrollIntoView({ block: 'nearest' });
  });
  pintarCentro(ctx, S);
  pintarContexto(ctx, S);
  if (foco) S.colCentro.querySelector('#bdj-texto')?.focus();
}

/** j / k y «siguiente» tras enviar: el de después en la lista que se ve (o el de antes si era el último). */
function mover(ctx, S, d) {
  const filas = filtrar(ctx, S);
  if (!filas.length) return;
  const i = filas.findIndex(x => x.id === S.sel);
  const j = i < 0 ? 0 : Math.min(filas.length - 1, Math.max(0, i + d));
  abrirItem(ctx, S, filas[j].id);
}

// ---------------------------------------------------------------- «Hecho · Deshacer» (_deshacer.js) y cola simulada
function pintarPie(ctx, S) {
  if (!S.pie) return;
  S.pie.replaceChildren(h('div', { class: 'pila', style: { padding: 'var(--s-2) var(--s-3)', gap: 'var(--s-1)' } },
    S.modo === 'uno' ? null : h('p', { class: 'sub fila', style: { gap: 'var(--s-1)', margin: '0' }, title: 'Atajos (con el foco fuera de la caja de texto): j / k moverse · r responder · e despachado · a asignar · p esperando al cliente · z deshacer · ⌘↵ enviar y siguiente · ? todos los atajos' },
      kbd('j'), kbd('k'), 'moverse', kbd('r'), 'responder', kbd('z'), 'deshacer', kbd('?'), 'todos'),
    h('div', { class: 'fila', style: { gap: 'var(--s-2)' } }, frescura(fres(S.D.fuentes?.desk, 'Desk')), frescura(fres(S.D.fuentes?.zadarma, 'Zadarma')))));
}

/** Lo que SACA el correo de la bandeja (responder en simulación, despachado, esperando al cliente, no aplica, cerrar): se ve
 *  hecho al momento y se abre el siguiente; «Hecho · Deshacer» (8 s, modulos/_deshacer.js) y después a la cola simulada.
 *  El «¿Seguro?» queda solo para el envío real (S.reales). */
function programar(ctx, S, x, tipo, texto, vista_previa, { herramienta, siguiente = true } = {}) {
  if (ctx.soloLectura) { avisoFlotante('Estás en «ver como»: no se cambia nada.', { icono: 'candado' }); return false; }
  guardarTexto(S);
  const filasAntes = filtrar(ctx, S);
  const i = filasAntes.findIndex(y => y.id === x.id);
  const p = { x, tipo, texto, vista_previa, herramienta: herramienta || (x.tipo === 'llamada' ? 'zadarma' : 'desk') };
  S.pendientes.set(x.id, p);
  const volver = () => {          // «Deshacer» o fallo: el correo vuelve, con lo escrito
    S.pendientes.delete(x.id); x.pendiente = null;
    guardarTexto(S);
    S.sel = x.id;
    if (S.modo === 'uno') irMovil(ctx, S, x.id); else refrescar(ctx, S, { centro: true });
  };
  S.ultimo = conDeshacer({
    mensaje: `${etiquetaTipo(tipo)} · ${x.cliente || 'sin cliente'}${tipo === 'responder' ? ' (simulado: no sale de verdad)' : ''}`,
    optimista: () => { x.pendiente = { tipo }; },
    revertir: volver,
    hacer: () => ejecutar(ctx, S, x.id),
  });
  if (siguiente) {
    const resto = filasAntes.filter(y => y.id !== x.id);
    const sig = resto[Math.min(Math.max(i, 0), resto.length - 1)];
    S.sel = sig ? sig.id : null;
  }
  if (S.modo === 'uno') irMovil(ctx, S, siguiente ? S.sel : x.id);
  else { pintarColLista(ctx, S); pintarCentro(ctx, S); pintarContexto(ctx, S); }
  return true;
}
/** En el móvil se pasa de un correo a otro sin cambiar de ruta (replaceState): un cambio de ruta encolaría ya lo que tiene
 *  «Deshacer» en marcha (_deshacer.js escribe todo al cambiar de pantalla). */
function irMovil(ctx, S, id, { empujar = false } = {}) {
  S.vistaMovil = id ? 'conv' : 'lista';
  S.sel = id || S.sel;
  try {
    const url = id ? `#/${ID}/${encodeURIComponent(id)}` : `#/${ID}`;
    if (empujar) { history.pushState(history.state, '', url); S._empujado = true; }   // «atrás» del navegador vuelve a la lista
    else history.replaceState(history.state, '', url);
  } catch { /* sin historial */ }
  guardarTexto(S);
  S.rehacer();
  window.scrollTo({ top: 0 });
}
async function ejecutar(ctx, S, id) {
  const p = S.pendientes.get(id);
  if (!p) return;
  const { x } = p;
  try {
    const r = await ctx.accion({ herramienta: p.herramienta, tipo: p.tipo, objeto: x.numero, cliente_id: x.cliente_id || null, texto: p.texto, vista_previa: p.vista_previa });
    S.pendientes.delete(id);
    const a = { tipo: p.tipo, quien: (ctx.real || ctx.persona).id, texto: p.texto, hora: horaLocal(new Date().toISOString()), id: r?.id, objeto: x.numero };
    x.acciones.push(a); S.porObjeto.set(String(x.numero), x.acciones);
    x.pendiente = null; marcarDeAcciones(x);
    S.textos.delete(x.id);
    cargarEnvios(ctx, S);
    if (S.cont?.isConnected) refrescar(ctx, S);
  } catch (e) {
    throw new Error(`no ha entrado en la cola (${e?.message || e})`);   // _deshacer.js lo dice y llama a «revertir»
  }
}
function deshacer() {
  if (!S_ULTIMO()) { avisoFlotante('No hay nada que deshacer.', { icono: 'info' }); return; }
  S_ULTIMO().deshacer();
}
const S_ULTIMO = () => (MEM?.S?.ultimo && MEM.S.pendientes.size ? MEM.S.ultimo : null);
/** Tras salir algo a la cola: la lista y los contadores se rehacen; el centro solo si cambia lo abierto (no se pierde lo que escribes). */
function refrescar(ctx, S, { centro = false } = {}) {
  if (!S.cont?.isConnected || S.alt) return;
  if (S.modo === 'uno') { if (S.vistaMovil !== 'conv' || centro) { guardarTexto(S); S.rehacer(); } return; }
  if (!S.colLista) return;
  pintarColLista(ctx, S);
  if (centro) { guardarTexto(S); pintarCentro(ctx, S); pintarContexto(ctx, S); }
}
// ---------------------------------------------------------------- centro: conversación + editor
function pintarCentro(ctx, S) {
  const col = S.colCentro;
  if (!col) return;
  col.replaceChildren();
  const x = S.items.find(y => y.id === S.sel);
  if (!x || x.pendiente) {
    col.append(h('div', { style: { padding: 'var(--s-6)', margin: 'auto 0' } }, vacio({ icono: 'ok', tono: S.items.some(vivo) ? 'neutro' : 'celebrar',
      titulo: S.items.some(vivo) ? 'Elige un correo de la lista' : 'Bandeja a cero',
      texto: S.items.some(vivo) ? 'Se abre aquí con el borrador listo para revisar y enviar.' : 'Ningún correo ni llamada espera respuesta.' })));
    return;
  }
  const dos = S.modo === 'dos';
  const cab = cabeceraConv(ctx, S, x);
  col.append(cab);
  if (dos) {
    const seg = h('div', { class: 'segm', role: 'tablist', 'aria-label': 'Vista', style: { marginLeft: 'auto' } },
      [['conv', 'Conversación', 'mail'], ['cliente', 'Cliente', 'cli']].map(([v, t, ic]) => h('button', { type: 'button', role: 'tab', 'aria-selected': String(S.pestCentro === v), 'aria-pressed': String(S.pestCentro === v),
        on: { click: () => { guardarTexto(S); S.pestCentro = v; pintarCentro(ctx, S); } } }, icono(ic, { clase: 's' }), ' ', t)));
    (cab.querySelector('[role="toolbar"]') || cab).append(seg);
    if (S.pestCentro === 'cliente') {
      const z = h('div', { style: { flex: '1 1 auto', minHeight: '0', overflowY: 'auto' } });
      col.append(z);
      pintarContextoEn(z, ctx, S, x);
      return;
    }
  }
  const hilo = h('div', { 'data-bdj': 'hilo', tabindex: '0', 'aria-label': 'Hilo del correo', style: { flex: '1 1 auto', minHeight: '0', overflowY: 'auto', padding: 'var(--s-3) var(--s-4)', background: 'var(--card-2)', borderTop: 'var(--borde-suave)', borderBottom: 'var(--borde-suave)' } });
  col.append(hilo);
  pintarHilo(hilo, ctx, S, x);
  const ed = x.tipo === 'llamada' ? editorLlamada(ctx, S, x) : editor(ctx, S, x);
  col.append(ed);
  ajustarEditor(S);
}

function cabeceraConv(ctx, S, x) {
  const yo = yoDe(ctx);
  const filasLista = filtrar(ctx, S);
  const i = filasLista.findIndex(y => y.id === x.id);
  const cab = h('div', { style: { flex: 'none', padding: 'var(--s-3) var(--s-4)', display: 'grid', gridTemplateColumns: 'minmax(0, 1fr)', gap: 'var(--s-2)' } });
  const tit = x.tipo === 'correo' ? (x.asunto || '(sin asunto)') : (x.cliente ? `${x.cliente} ha llamado ${x.llamadas} ${x.llamadas === 1 ? 'vez' : 'veces'}` : `Número desconocido ${x.numero_oculto}`);
  const conChip = (c, titulo) => { c.title = titulo; return c; };
  cab.append(
    // 1 · quién y qué, con «1 de 13 ‹ ›»
    h('div', { class: 'fila', style: { flexWrap: 'nowrap', alignItems: 'flex-start' } },
      x.cli ? logoCliente(x.cli) : h('span', { class: `ico-c ${x.gravedad || 'gris'}` }, icono(x.tipo === 'llamada' ? 'phone' : 'mail')),
      h('h2', { style: { font: 'var(--t-h2)', margin: '0', overflowWrap: 'anywhere', minWidth: '0', flex: '1 1 auto' } }, tit),
      h('div', { class: 'fila', style: { flex: 'none', gap: 'var(--s-1)' } },
        i >= 0 ? h('span', { class: 'sub' }, `${i + 1} de ${filasLista.length}`) : null,
        h('button', { type: 'button', class: 'bt mini icono', title: 'Anterior (k)', 'aria-label': 'Anterior', disabled: i <= 0 || null, on: { click: () => mover(ctx, S, -1) } }, icono('izquierda', { clase: 's' })),
        h('button', { type: 'button', class: 'bt mini icono', title: 'Siguiente (j)', 'aria-label': 'Siguiente', disabled: i < 0 || i >= filasLista.length - 1 || null, on: { click: () => mover(ctx, S, 1) } }, icono('derecha', { clase: 's' })))),
    // 2 · datos y estado en una sola línea que se parte si hace falta
    h('div', { class: 'meta-linea fila', style: { font: 'var(--t-meta)', color: 'var(--mid)', gap: 'var(--s-1) var(--s-3)' } },
      x.hecho ? chipEstado('azul', `En cola: ${etiquetaTipo(x.hecho.tipo)}`) : conChip(chipEstado(x.gravedad || 'gris', `${relojTxt(x.horas)} esperando`), 'Tiempo esperando, en horas laborables (de lunes a viernes)'),
      x.queja ? conChip(chipEstado('rojo', 'Queja: llama hoy'), 'Es una queja: llama hoy y luego confírmalo por escrito') : null,
      x.esperando ? chipEstado('gris', `Esperando al cliente desde ${fDiaRO(x.esperando.hora || (x.esperando.creada ? horaLocal(`${String(x.esperando.creada).replace(' ', 'T')}Z`) : ''))}`) : null,
      x.asignadoCola ? chipEstado('azul', `${x.asignadoCola.texto || 'Asignado'} (en cola)`) : null,
      h('span', {}, icono('cli', { clase: 's' }), ' ', x.cliente || 'Sin cliente'),
      x.tipo === 'correo' && x.url ? h('a', { href: x.url, target: '_blank', rel: 'noopener', title: 'Abre el ticket en Zoho Desk' }, `${x.numero} ↗`) : h('span', {}, x.numero_oculto || x.numero || ''),
      h('span', {}, icono('persona', { clase: 's' }), ' ', x.account_id ? (x.account_id === yo ? 'Account: tú' : `Account: ${nom1(x.account)}`) : x.account),
      x.tipo === 'correo' ? h('span', { title: 'Responsable del ticket en Desk' }, x.asignado ? `En Desk: ${nom1(x.asignado)}` : 'Sin responsable en Desk') : null,
      x.tipo === 'correo' && x.estado_desk ? h('span', { title: 'Estado en Desk' }, x.estado_desk) : null));
  if (!x.hecho) cab.append(barraAcciones(ctx, S, x));
  return cab;
}

function barraAcciones(ctx, S, x) {
  const yo = yoDe(ctx);
  const ro = ctx.soloLectura;
  const tit = ro ? 'En «ver como» no se cambia nada' : null;
  const estrecho = S.modo !== 'tres';   // 1024 y móvil: solo el icono (el nombre, en el title y para el lector de pantalla)
  const bt = (ic, txt, atajo, fn, extra = {}) => h('button', { type: 'button', class: 'bt mini', disabled: ro || extra.disabled || null, title: extra.title || tit || (atajo ? `${txt} (${atajo})` : txt),
    'aria-label': estrecho ? txt : null, 'data-bdj-acc': extra.id || null, on: { click: fn } }, icono(ic, { clase: 's' }), estrecho ? null : txt, atajo && !estrecho ? h('span', { class: 'dim', 'aria-hidden': 'true' }, ` ${atajo}`) : null);
  const items = [];
  if (x.tipo === 'correo') {
    items.push(bt('ok', 'Despachado', 'e', () => despachar(ctx, S, x), { id: 'despachado', title: 'Ya está atendido (por teléfono, WhatsApp o no pide respuesta): sale de la bandeja sin contestar (e)' }));
    items.push(bt('clock', 'Esperando', 'p', () => esperar(ctx, S, x), { id: 'esperando', disabled: !!x.esperando, title: 'Le toca al cliente: pasa a «Esperando al cliente» y deja de contar (p)' }));
  }
  if (puedeAsignar(ctx)) {
    const gente = (ctx.datos.personas || []).filter(q => (q.puestos || []).some(pu => ['account', 'operaciones', 'direccion', 'jefa_crm', 'jefa_publicidad'].includes(pu)) && q.estado !== 'baja' && !String(q.id).startsWith('setter'));
    const m = menuMas({ texto: h('span', { class: 'fila', style: { gap: 'var(--s-1)' } }, icono('persona', { clase: 's' }), estrecho ? null : 'Asignar', estrecho ? null : h('span', { class: 'dim', 'aria-hidden': 'true' }, ' a')), etiqueta: 'Asignar a',
      items: gente.slice().sort((a, b) => (b.id === x.account_id) - (a.id === x.account_id) || String(a.nombre).localeCompare(String(b.nombre))).map(q => ({
        texto: q.nombre + (q.id === x.account_id ? ' · account del cliente' : ''), activo: q.id === (x.asignado_id || null),
        alPulsar: () => accionDirecta(ctx, S, x, 'asignar', `Asignar a ${q.nombre}`, { a: q.id, ticket: x.numero }) })) });
    m.dataset.bdjAsignar = '1';
    if (ro) m.querySelector('button')?.setAttribute('disabled', '');
    items.push(m);
  }
  items.push(bt('flag', estrecho ? 'Tarea en ClickUp' : 'Tarea', null, () => accionDirecta(ctx, S, x, 'tarea', `Tarea para ${x.cliente || 'sin cliente'}: ${x.asunto || 'llamada sin devolver'}`,
    { lista: 'tareas del cliente', titulo: x.asunto || 'Devolver llamada', desde_ticket: x.numero, enlace: x.url || null }, 'clickup'),
  { id: 'tarea', disabled: !x.cliente_id, title: x.cliente_id ? 'Crea una tarea en la lista del cliente en ClickUp (simulado: va a la cola)' : 'Sin cliente no hay lista de ClickUp' }));
  if (x.account_id && x.account_id !== yo) {
    items.push(bt('campana', `Avisar a ${nom1(x.account)}`, null, () => accionDirecta(ctx, S, x, 'aviso_account', `Aviso a ${x.account}: ${x.cliente} espera respuesta (${x.numero}, ${relojTxt(x.horas)})`,
      { para: x.account_id, ticket: x.numero }, 'app'), { id: 'avisar', title: `Le llega a ${x.account} en la app (simulado: va a la cola)` }));
  }
  const mas = menuMas({ texto: 'Más', etiqueta: 'Más acciones', items: [
    ...(x.tipo === 'correo' ? MOTIVOS_NO_APLICA.slice(0, 5).map(mo => ({ texto: `No aplica: ${mo}`, alPulsar: () => programar(ctx, S, x, 'no_aplica', mo, { motivo: mo }) })) : []),
    x.tipo === 'correo' ? { texto: 'Cerrar el ticket sin contestar', alPulsar: () => programar(ctx, S, x, 'cerrar', `Cerrar ${x.numero}`, { estado: 'Cerrado', ticket: x.numero }) } : null,
    x.url ? { texto: x.tipo === 'correo' ? 'Abrir en Desk ↗' : 'Ver en Zadarma ↗', href: x.url } : null,
  ].filter(Boolean) });
  if (ro) mas.querySelector('button')?.setAttribute('disabled', '');
  items.push(mas);
  return h('div', { class: 'fila', role: 'toolbar', 'aria-label': 'Acciones de un clic', style: { gap: 'var(--s-1)' } }, items);
}

async function accionDirecta(ctx, S, x, tipo, texto, vista_previa, herramienta = 'desk') {
  if (ctx.soloLectura) { avisoFlotante('Estás en «ver como»: no se cambia nada.', { icono: 'candado' }); return; }
  try {
    const r = await ctx.accion({ herramienta, tipo, objeto: x.numero, cliente_id: x.cliente_id || null, texto, vista_previa });
    x.acciones.push({ tipo, texto, quien: (ctx.real || ctx.persona).id, hora: horaLocal(new Date().toISOString()), id: r?.id });
    marcarDeAcciones(x);
    avisoFlotante(`${etiquetaTipo(tipo)} en la cola simulada: no ha salido nada`);
    if (S.modo === 'uno') S.rehacer(); else { pintarColLista(ctx, S); pintarCentro(ctx, S); }
  } catch (e) { avisoFlotante(`No se ha podido: ${e?.message || e}`, { icono: 'alert' }); }
}
const despachar = (ctx, S, x) => programar(ctx, S, x, 'despachado', `Despachado sin respuesta (${x.numero})`, { ticket: x.numero, motivo: 'atendido por otra vía o no pide respuesta' });
const esperar = (ctx, S, x) => programar(ctx, S, x, 'esperando_cliente', `Esperando al cliente (${x.numero})`, { ticket: x.numero });

// ---------------------------------------------------------------- hilo
async function cargarHilos(ctx, S) {
  if (S.hilos) return S.hilos;
  if (!S._hilosP) {
    S._hilosP = ctx.datosModulo('bandeja/hilos')
      .then(d => { S.hilos = new Map((d.hilos || []).map(x => [x.numero, x])); return S.hilos; })
      .catch(() => { S.hilos = new Map(); return S.hilos; });
  }
  return S._hilosP;
}
async function cargarEnvios(ctx, S) {
  if (!ctx.servidor) return;
  try {
    const r = await ctx.api('envios');
    S.reales = !!r.modo?.reales;      // con los envíos reales activados, «Enviar» pide un «Sí» (lo único que sale fuera)
    const x0 = S.items.find(y => y.id === S.sel);
    const antes = x0 ? JSON.stringify(S.envios.get(String(x0.numero)) || []) : '';
    S.envios = new Map();
    for (const e of r.envios || []) {
      if (e.modulo && e.modulo !== ID) continue;
      const k = String(e.destinatario?.ref || '');
      if (!S.envios.has(k)) S.envios.set(k, []);
      S.envios.get(k).push(e);
    }
    const hilo = S.cont?.querySelector('[data-bdj="hilo"]');
    const x = S.items.find(y => y.id === S.sel);
    if (hilo && x && JSON.stringify(S.envios.get(String(x.numero)) || []) !== antes) pintarHilo(hilo, ctx, S, x);
  } catch { /* sin envíos: el hilo enseña la cola */ }
}

function pintarHilo(z, ctx, S, x) {
  z.replaceChildren();
  if (x.tipo === 'llamada') {
    z.append(h('div', { class: 'pila' },
      h('p', {}, x.cliente ? `${x.cliente} ha llamado ${x.llamadas} ${x.llamadas === 1 ? 'vez' : 'veces'} sin que nadie lo coja ni le devuelva la llamada.` : 'Número que no está en ninguna ficha: puede ser un cliente con otro móvil, un lead o publicidad.'),
      h('ul', { class: 'lista-i' },
        h('li', {}, icono('cal', { clase: 's' }), ` Primera sin devolver: ${fDiaHoraRO(x.primera)} · última: ${fDiaHoraRO(x.ultima)}`),
        h('li', {}, icono('phone', { clase: 's' }), ` ${x.intentos_nuestros ? `${x.intentos_nuestros} ${x.intentos_nuestros === 1 ? 'intento nuestro' : 'intentos nuestros'} sin respuesta` : 'Nadie ha intentado devolverla'}`),
        x.sono_a ? h('li', {}, icono('persona', { clase: 's' }), ` Sonó a ${x.sono_a}`) : null),
      enviosDe(ctx, S, x)));
    return;
  }
  const hl = S.hilos?.get(x.numero);
  if (!S.hilos) {
    z.append(h('div', { class: 'ia-cargando', role: 'status' }, h('i'), h('i'), h('i'), 'Leyendo el hilo…'));
    cargarHilos(ctx, S).then(() => { if (z.isConnected && S.sel === x.id) pintarHilo(z, ctx, S, x); });
    return;
  }
  const msgs = (hl?.mensajes || []).slice();
  if (!msgs.length) {
    z.append(h('div', { class: 'pila', style: { maxWidth: '72ch' } },
      h('div', { class: 'aviso info' }, icono('info', { clase: 's' }), h('span', {}, h('b', {}, 'El texto de este correo todavía no está en la app. '),
        'La app lee los hilos de Desk por tandas (los más urgentes primero) y este aún no ha llegado; mientras, se lee en Desk. El borrador de abajo sale del asunto y del estado del cliente.')),
      h('dl', { class: 'dl' },
        h('dt', {}, 'Asunto'), h('dd', {}, x.asunto || '(sin asunto)'),
        h('dt', {}, 'Último correo del cliente'), h('dd', {}, x.desde ? fDiaHoraRO(x.desde) : '—'),
        h('dt', {}, 'Estado en Desk'), h('dd', {}, `${x.estado_desk || '—'} · ${String(x.departamento || 'Marketing Clientes').replace(/\.$/, '')}`)),
      x.url ? h('div', {}, h('a', { class: 'bt', href: x.url, target: '_blank', rel: 'noopener' }, icono('ext', { clase: 's' }), 'Leer el hilo en Desk')) : null,
      enviosDe(ctx, S, x)));
    return;
  }
  // plegados todos menos los dos últimos; «Desplegar todo» para leerlo de corrido
  const abiertos = new Set([msgs.length - 1, msgs.length - 2]);
  const lista = h('div', { class: 'pila', style: { gap: 'var(--s-2)', maxWidth: '80ch' } });
  const pleg = h('button', { type: 'button', class: 'bt mini', on: { click: () => { const todos = [...lista.querySelectorAll('details')]; const abrir = todos.some(d => !d.open); todos.forEach(d => { d.open = abrir; }); pleg.lastChild.textContent = abrir ? 'Plegar los antiguos' : 'Desplegar todo'; } } },
    icono('chev', { clase: 's' }), h('span', {}, 'Desplegar todo'));
  z.append(h('div', { class: 'fila', style: { justifyContent: 'space-between', marginBottom: 'var(--s-2)' } },
    h('span', { class: 'titulo-seccion' }, `${msgs.length} ${msgs.length === 1 ? 'mensaje' : 'mensajes'}`), msgs.length > 2 ? pleg : null));
  msgs.forEach((m, i) => {
    const ent = m.direccion !== 'saliente';
    const resumen = m.texto.replace(/\s+/g, ' ').slice(0, 110);
    lista.append(h('details', { open: abiertos.has(i) || null, 'data-msg': String(i),
      style: { background: 'var(--card)', border: 'var(--borde)', borderLeft: `4px solid ${ent ? 'var(--accent)' : 'var(--line)'}`, borderRadius: 'var(--r-m)', padding: 'var(--s-2) var(--s-3)' } },
      h('summary', { style: { cursor: 'pointer', minHeight: 'var(--s-8)', display: 'flex', gap: 'var(--s-2)', alignItems: 'center', flexWrap: 'wrap' } },
        h('span', { class: `ico-c s${ent ? '' : ' gris'}` }, icono(ent ? 'mail' : 'send')),
        h('b', {}, m.de || (ent ? 'Cliente' : 'Nosotros')), h('span', { class: 'sub' }, `${ent ? 'escribió' : 'contestamos'} · ${fDiaHoraRO(m.fecha)}`),
        h('span', { class: 'sub', style: { flexBasis: '100%', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }, 'data-resumen': '' }, resumen)),
      h('div', { style: { whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', paddingTop: 'var(--s-2)', lineHeight: '1.6' } }, m.texto,
        m.cortado ? h('p', { class: 'sub' }, 'El mensaje sigue en Desk (aquí llega cortado). ', x.url ? h('a', { href: x.url, target: '_blank', rel: 'noopener' }, 'Verlo entero ↗') : null) : null)));
  });
  // el resumen de una línea solo con el mensaje plegado
  lista.addEventListener('toggle', e => { const r = e.target.querySelector('[data-resumen]'); if (r) r.hidden = e.target.open; }, true);
  lista.querySelectorAll('details').forEach(d => { const r = d.querySelector('[data-resumen]'); if (r) r.hidden = d.open; });
  z.append(lista);
  const env = enviosDe(ctx, S, x);
  if (env) z.append(env);
  requestAnimationFrame(() => { if (z.isConnected) z.scrollTop = z.scrollHeight; });   // lo último, a la vista (como Front o Gmail)
}

/** Lo que ya ha salido desde la app para este ticket: la cola y el estado del envío (simulado, pendiente, confirmado…). */
function enviosDe(ctx, S, x) {
  const env = S.envios.get(String(x.numero)) || [];
  const resp = x.acciones.filter(a => ['responder', 'nota_interna'].includes(a.tipo));
  if (!env.length && !resp.length) return null;
  const vistos = new Set();
  const filas = env.map(e => {
    vistos.add(String(e.texto || '').trim());
    const [cls, txt] = ESTADO_ENVIO[e.estado] || ['gris', e.estado];
    return { cuando: horaLocal(e.creado), de: e.quien_alias || ctx.nombre(e.quien), texto: e.texto_oculto ? '(texto solo para quien lleva el cliente)' : e.texto, chip: chipEstado(cls, txt), nota: e.motivo };
  });
  for (const a of resp) {
    if (vistos.has(String(a.texto || '').trim())) continue;
    filas.push({ cuando: a.hora || (a.creada ? horaLocal(`${String(a.creada).replace(' ', 'T')}Z`) : ''), de: ctx.nombre(a.quien) || a.quien, texto: a.texto,
      chip: a.tipo === 'nota_interna' ? chipEstado('gris', 'Nota interna: el cliente no la ve') : chipEstado('gris', 'Simulado: no ha salido') });
  }
  return h('div', { class: 'pila', style: { gap: 'var(--s-2)', marginTop: 'var(--s-3)', maxWidth: '80ch' }, 'data-bdj': 'envios' },
    h('span', { class: 'titulo-seccion' }, icono('send', { clase: 's' }), 'Desde la app'),
    filas.map(f => h('div', { style: { background: 'var(--card)', border: 'var(--borde)', borderLeft: '4px solid var(--good)', borderRadius: 'var(--r-m)', padding: 'var(--s-2) var(--s-3)' } },
      h('div', { class: 'fila', style: { gap: 'var(--s-2)' } }, h('b', {}, f.de || '—'), h('span', { class: 'sub' }, fDiaHoraRO(String(f.cuando || '').replace('T', ' ').replace('Z', ''))), f.chip),
      h('div', { style: { whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', paddingTop: 'var(--s-1)' } }, f.texto || ''),
      f.nota ? h('p', { class: 'sub' }, f.nota) : null)));
}

// ---------------------------------------------------------------- editor
function guardarTexto(S) {
  const ta = S.cont?.querySelector('#bdj-texto');
  const id = ta?.dataset.item;
  if (!ta || !id) return;
  const t = S.textos.get(id) || {};
  if (ta.dataset.modo === 'nota') S.textos.set(id, { ...t, textoNota: ta.value });
  else S.textos.set(id, { ...t, texto: ta.value, editado: t.editado || ta.value !== t.original });
}

function editor(ctx, S, x) {
  const real = ctx.real || ctx.persona;
  // sin cliente no se contesta desde la app (el servidor no sabe a quién va: 403); se asigna, se despacha o se deja nota
  const puedeResponder = !!x.cliente_id && ctx.ver({ tipo: 'responder_cliente', cliente_id: x.cliente_id }).ok;
  const caja = h('div', { 'data-bdj': 'editor', style: { flex: 'none', padding: S.modo === 'uno' ? 'var(--s-3)' : 'var(--s-3) var(--s-4)', display: 'grid', gridTemplateColumns: 'minmax(0, 1fr)', gap: 'var(--s-2)', background: 'var(--card)' } });
  if (x.hecho) {
    caja.append(h('div', { class: 'aviso info', role: 'status' }, icono('ok', { clase: 's' }),
      h('span', {}, `${etiquetaTipo(x.hecho.tipo)} preparada por ${nombrePersona(ctx, x.hecho.quien)} · ${fDiaHoraRO(x.hecho.hora || (x.hecho.creada ? horaLocal(`${String(x.hecho.creada).replace(' ', 'T')}Z`) : ''))}. Saldrá por Desk cuando se active el envío real.`)));
    return caja;
  }
  const t0 = S.textos.get(x.id) || { modo: puedeResponder ? 'responder' : 'nota' };
  let modo = t0.modo;
  const ta = h('textarea', { id: 'bdj-texto', 'data-item': x.id, 'data-modo': modo, 'aria-label': 'Respuesta al cliente', spellcheck: 'true',
    style: { display: 'block', position: 'relative', width: '100%', resize: 'none', border: 'var(--borde)', borderRadius: 'var(--r-m)', padding: 'var(--s-3)', font: 'var(--t-cuerpo)', lineHeight: '1.6', background: 'transparent', color: 'var(--ink)', minHeight: '96px', scrollbarGutter: 'stable', overflowY: 'auto' } });
  // los [completar: …] resaltados: una capa detrás con el mismo texto (transparente) y los huecos en ámbar
  const fondo = h('div', { 'aria-hidden': 'true', style: { position: 'absolute', inset: '0', padding: 'var(--s-3)', border: '1px solid transparent', font: 'var(--t-cuerpo)', lineHeight: '1.6',
    whiteSpace: 'pre-wrap', overflowWrap: 'break-word', color: 'transparent', overflowY: 'hidden', scrollbarGutter: 'stable', pointerEvents: 'none' } });
  const marco = h('div', { style: { position: 'relative', background: 'var(--card)', borderRadius: 'var(--r-m)' } }, fondo, ta);
  const pintarMarcas = () => {
    const v = ta.value, partes = [];
    let k = 0;
    for (const m of v.matchAll(RX_HUECO)) { partes.push(v.slice(k, m.index), h('mark', { style: { background: 'var(--warn-soft)', color: 'transparent', borderRadius: 'var(--r-s)', boxShadow: '0 0 0 1px var(--warn-line)' } }, m[0])); k = m.index + m[0].length; }
    partes.push(v.slice(k) + '\n');
    fondo.replaceChildren(...partes);
    fondo.scrollTop = ta.scrollTop;
  };
  ta.addEventListener('scroll', () => { fondo.scrollTop = ta.scrollTop; });
  const estadoIA = h('div', { class: 'fila', style: { gap: 'var(--s-2)', minWidth: '0' }, 'data-bdj': 'calidad' });
  const falta = h('div', {});
  const aviso = h('div', { 'aria-live': 'polite' });
  const adj = h('div', { class: 'fila', style: { gap: 'var(--s-1)' } });
  const sugerencias = h('div', { class: 'fila', style: { gap: 'var(--s-1)' }, hidden: true });

  // cabecera: Responder | Nota interna · De / Para / Asunto en una línea · ampliar
  const seg = h('div', { class: 'segm', role: 'group', 'aria-label': 'Qué escribes', style: { flex: 'none' } },
    [['responder', 'Responder', 'send'], ['nota', S.modo === 'tres' ? 'Nota interna' : 'Nota', 'editar']].map(([v, txt, ic]) => h('button', { type: 'button', 'aria-pressed': String(modo === v), style: { whiteSpace: 'nowrap' },
      disabled: (v === 'responder' && !puedeResponder) || null, title: v === 'responder' && !puedeResponder ? (x.cliente_id ? 'Al cliente le contestan su account, las jefas, Operaciones y Dirección' : 'Correo sin cliente: asígnalo a su account o despáchalo; desde la app solo se contesta a un cliente') : null,
      on: { click: () => { guardarTexto(S); modo = v; S.textos.set(x.id, { ...(S.textos.get(x.id) || {}), modo: v }); pintarCentro(ctx, S); } } }, icono(ic, { clase: 's' }), ' ', txt)));
  const asuntoTxt = (t0.asunto || `RE: ${x.asunto || ''}`).trim();
  const linea = modo === 'responder'
    ? h('span', { class: 'sub', style: { minWidth: '0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: '1 1 160px' }, title: `De marketing@rankingonline.com · Para el contacto del ticket ${x.numero}${x.dominio ? ` (@${x.dominio})` : ''} · Asunto: ${asuntoTxt}` },
      `Para: contacto de ${x.numero}${x.dominio ? ` (@${x.dominio})` : ''} · ${asuntoTxt}`)
    : h('span', { class: 'sub', style: { flex: '1 1 160px' } }, 'Nota interna en el ticket: el cliente no la ve');
  const ampliar = h('button', { type: 'button', class: 'bt mini icono', 'aria-pressed': String(!!S.ampliado), title: S.ampliado ? 'Editor normal' : 'Ampliar el editor (para textos largos)', 'aria-label': 'Ampliar el editor',
    on: { click: () => { S.ampliado = !S.ampliado; ampliar.setAttribute('aria-pressed', String(S.ampliado)); ajustarEditor(S); ta.focus(); } } }, icono('capas', { clase: 's' }));
  const movil = S.modo === 'uno';
  caja.append(h('div', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'nowrap', minWidth: '0', justifyContent: 'space-between' } }, seg, movil ? null : linea, ampliar));

  if (modo === 'responder') caja.append(h('div', { class: 'fila', style: { gap: 'var(--s-2)', justifyContent: 'space-between' } }, estadoIA, falta));
  caja.append(marco, sugerencias, aviso);

  // pie: plantillas, adjuntar, firma · enviar
  const plantillas = menuMas({ texto: h('span', { class: 'fila', style: { gap: 'var(--s-1)' } }, icono('doc', { clase: 's' }), movil ? null : 'Plantillas'), etiqueta: 'Plantillas (también con «/» al empezar una línea)',
    items: PLANTILLAS.map(pl => ({ texto: pl.texto, alPulsar: () => ponerPlantilla(pl) })) });
  const fichero = h('input', { type: 'file', multiple: true, hidden: true, 'aria-label': 'Adjuntar archivos' });
  fichero.addEventListener('change', () => { const l = S.adjuntos.get(x.id) || []; for (const f of fichero.files) l.push({ nombre: f.name, kb: Math.round(f.size / 1024) }); S.adjuntos.set(x.id, l); pintarAdj(); fichero.value = ''; });
  const btAdj = h('button', { type: 'button', class: 'bt mini', title: 'Adjuntar (simulado: el archivo no se sube; solo queda su nombre en la cola)', on: { click: () => fichero.click() } }, icono('link', { clase: 's' }), 'Adjuntar');
  const conFirma = h('input', { type: 'checkbox', id: 'bdj-firma', checked: t0.sinFirma ? null : true });
  const tieneFirma = S.D.firmas?.[real.id];
  const firma = h('label', { class: 'sub fila', for: 'bdj-firma', style: { gap: 'var(--s-1)', cursor: 'pointer' }, title: tieneFirma ? 'Tu firma de Desk (imagen con foto, extensión y logo de RO)' : 'No tienes firma de imagen en Desk: saldría solo tu nombre. Pídesela a Agus.' },
    conFirma, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(real.nombre)), `Firma de ${nom1(real.nombre)}${tieneFirma ? '' : ' (sin imagen)'}`);
  conFirma.addEventListener('change', () => S.textos.set(x.id, { ...(S.textos.get(x.id) || {}), sinFirma: !conFirma.checked }));
  const ro = ctx.soloLectura;
  const btEnviar = h('button', { type: 'button', class: 'bt', 'data-bdj-enviar': 'uno', disabled: ro || null, title: ro ? 'En «ver como» no se envía nada' : 'Enviar y quedarse en este correo',
    on: { click: () => enviar(false) } }, icono(modo === 'nota' ? 'editar' : 'send', { clase: 's' }), modo === 'nota' ? 'Guardar nota' : 'Enviar');
  const btSig = h('button', { type: 'button', class: 'bt pri', 'data-bdj-enviar': 'siguiente', disabled: ro || null, title: ro ? 'En «ver como» no se envía nada' : `${modo === 'nota' ? 'Guardar la nota' : 'Enviar'} y abrir el siguiente (⌘↵ / Ctrl ↵)`,
    on: { click: () => enviar(true) } }, icono('send', { clase: 's' }), modo === 'nota' ? 'Guardar y siguiente' : 'Enviar y siguiente', h('span', { 'aria-hidden': 'true', style: { opacity: '0.8' } }, ' ⌘↵'));
  const btCerrar = h('button', { type: 'button', class: 'bt pri', 'data-bdj-enviar': 'cerrar', hidden: true, disabled: ro || null,
    title: 'El borrador dice que no hace falta responder: cierra el ticket en Desk y abre el siguiente (⌘↵). Va a la cola simulada con «Deshacer».',
    on: { click: () => cerrarSinResponder() } }, icono('ok', { clase: 's' }), 'Cerrar sin responder');
  if (movil) {
    // móvil: una fila (plantillas · adjuntar · enviar · enviar y siguiente); la firma va siempre (está en el title)
    btAdj.replaceChildren(icono('link', { clase: 's' })); btAdj.setAttribute('aria-label', 'Adjuntar (simulado)');
    btEnviar.replaceChildren(icono(modo === 'nota' ? 'editar' : 'send', { clase: 's' })); btEnviar.setAttribute('aria-label', modo === 'nota' ? 'Guardar nota' : 'Enviar y quedarse');
    btSig.style.flex = '1 1 auto'; btSig.style.justifyContent = 'center'; btSig.lastChild?.remove();   // sin «⌘↵» en el móvil
    btSig.title = `${btSig.title} · con la firma de Desk de ${real.nombre} · prueba: no sale de verdad`;
    btCerrar.style.flex = '1 1 100%'; btCerrar.style.justifyContent = 'center';
    caja.append(h('div', { class: 'fila', style: { gap: 'var(--s-2)' } }, modo === 'responder' ? plantillas : null, modo === 'responder' ? btAdj : null, fichero, btEnviar, btSig, btCerrar), adj);
  } else caja.append(h('div', { class: 'fila', style: { justifyContent: 'space-between', gap: 'var(--s-2)' } },
    h('div', { class: 'fila', style: { gap: 'var(--s-1)' } }, modo === 'responder' ? plantillas : null, modo === 'responder' ? btAdj : null, fichero, modo === 'responder' ? firma : null, adj),
    h('div', { class: 'fila', style: { gap: 'var(--s-2)', marginLeft: 'auto' } },
      S.modo === 'tres' ? h('span', { class: 'sub' }, 'Prueba: no sale de verdad') : (c => { c.title = 'Prueba: este envío todavía no sale de verdad'; return c; })(chipEstado('gris', 'Simulado')), btEnviar, btSig, btCerrar)));

  function pintarAdj() {
    adj.replaceChildren(...(S.adjuntos.get(x.id) || []).map((a, i) => h('span', { class: 'chip gris sin-punto', title: 'Simulado: no se sube' }, icono('link', { clase: 's' }), a.nombre,
      h('button', { type: 'button', class: 'bt mini icono', 'aria-label': `Quitar ${a.nombre}`, style: { minHeight: '0', padding: '0', border: '0', background: 'none' },
        on: { click: () => { const l = S.adjuntos.get(x.id) || []; l.splice(i, 1); pintarAdj(); } } }, icono('cerrar', { clase: 's' })))));
  }
  pintarAdj();
  const saludo = '';
  function ponerPlantilla(pl) {
    const actual = ta.value.replace(/(^|\n)\/[^\n]*$/, '$1').trim();
    ta.value = actual && !S.textos.get(x.id)?.esPlantilla ? `${actual}\n\n${pl.cuerpo(saludo)}` : pl.cuerpo(saludo);
    S.textos.set(x.id, { ...(S.textos.get(x.id) || {}), texto: ta.value, esPlantilla: true, editado: true });
    sugerencias.hidden = true;
    calidad();
    ta.focus();
    const m = ta.value.search(RX_HUECO); if (m >= 0) { const f = ta.value.slice(m).match(RX_HUECO)[0]; ta.setSelectionRange(m, m + f.length); }
  }
  // «/» al empezar una línea: las plantillas como sugerencias (patrón de Front, Help Scout y Zendesk)
  ta.addEventListener('input', () => {
    const m = ta.value.slice(0, ta.selectionStart).match(/(^|\n)\/([^\n]*)$/);
    if (m && modo === 'responder') {
      const q = normal(m[2]);
      const pls = PLANTILLAS.filter(pl => !q || normal(pl.texto).includes(q));
      sugerencias.hidden = !pls.length;
      sugerencias.replaceChildren(h('span', { class: 'sub' }, 'Plantillas:'), ...pls.map(pl => h('button', { type: 'button', class: 'bt mini', on: { click: () => ponerPlantilla(pl) } }, pl.texto)));
    } else sugerencias.hidden = true;
    calidad();
    pedirAjuste();
  });
  ta.addEventListener('focus', () => ajustarEditor(S));
  ta.addEventListener('blur', () => setTimeout(() => ajustarEditor(S), 150));
  let _aj = 0;
  const pedirAjuste = () => { if (!_aj) _aj = requestAnimationFrame(() => { _aj = 0; ajustarEditor(S); }); };
  ta.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { e.preventDefault(); if (!btCerrar.hidden) cerrarSinResponder(); else enviar(true); }
    else if (e.key === 'Escape') { e.preventDefault(); ta.blur(); S.lista?.querySelector('[aria-current="true"]')?.focus({ preventScroll: true }); }
  });

  // ---- calidad del borrador y lo que falta (contrato del cerebro de respuestas: ia.py → calidad, tipo, recomendación…)
  const irAHueco = hh => { const v = ta.value; const i = hh ? v.indexOf(hh) : v.search(RX_HUECO); if (i < 0) { ta.focus(); return; } const f = hh || v.slice(i).match(RX_HUECO)[0]; ta.focus(); ta.setSelectionRange(i, i + f.length); };
  function calidad() {
    pintarMarcas();
    if (modo !== 'responder') return;
    const r = S.borradores.get(x.id);
    const huecosTexto = [...new Set(ta.value.match(RX_HUECO) || [])];
    const tachados = S.textos.get(x.id)?.hechos || [];
    const huecos = (r?.ok ? (r.huecos || []) : []).filter(Boolean);
    const pendientes = huecos.filter((_, i) => !tachados.includes(i));
    const n = huecosTexto.length + pendientes.length;
    const c = r?.ok ? r.calidad : null;
    let cls, txt;
    if (c && typeof c.nota === 'number') {
      // la nota la pone el servidor; los huecos se cuentan en vivo (al rellenarlos, «revisar» pasa a «lista»)
      const bloqueo = (c.bloqueos || []).length > 0;
      const nivel = bloqueo ? 'rehacer' : huecosTexto.length ? (c.nivel === 'lista' ? 'revisar' : c.nivel) : (c.nota >= 85 ? 'lista' : c.nivel);
      cls = nivel === 'lista' ? 'verde' : nivel === 'revisar' ? 'ambar' : 'rojo';
      txt = `${c.nota}/100 · ${nivel === 'lista' ? 'lista' : nivel === 'revisar' ? 'revisar' : 'rehacer'}${huecosTexto.length ? ` · ${huecosTexto.length} por completar` : ''}`;
    } else if (!r) { cls = 'gris'; txt = 'Preparando el borrador…'; }
    else if (!r.ok) { cls = 'gris'; txt = S.textos.get(x.id)?.esPlantilla ? 'Plantilla: revísala' : 'Sin borrador de la IA'; }
    else { cls = n ? 'ambar' : 'verde'; txt = n ? `Casi listo: ${n === 1 ? 'falta 1 cosa' : `faltan ${n} cosas`}` : 'Listo para enviar'; }
    const tipo = r?.ok && (r.tipo_nombre || r.clasificacion?.nombre);
    const tipoCorto = tipo ? String(tipo).split(/\s*[(«]/)[0].trim() : '';
    estadoIA.replaceChildren(...[
      h('span', { class: 'sub' }, S.modo === 'tres' ? 'Calidad del borrador:' : 'Borrador:'), conTitulo(chipEstado(cls, txt), r?.ok ? `${origenTxt(r)}${r.aviso ? ` · ${r.aviso}` : ''}` : (r?.motivo || '')),
      tipoCorto ? conTitulo(chipEstado('azul', tipoCorto), `Tipo de correo: ${tipo}${r.clasificacion?.confianza ? ` (confianza ${r.clasificacion.confianza})` : ''}`) : null,
      r?.ok && S.modo === 'tres' ? h('span', { class: 'sub', title: r.aviso || '' }, origenTxt(r)) : null,
      r && !r.ok && r.motivo ? h('span', { class: 'sub', title: r.motivo, style: { cursor: 'help', textDecoration: 'underline dotted' } }, 'por qué') : null,
      r?.ok && r.conectada && !ctx.soloLectura ? h('button', { type: 'button', class: 'bt mini', on: { click: () => pedirBorrador(true) } }, icono('recargar', { clase: 's' }), 'Otra versión') : null].filter(Boolean));
    // recomendación interna (solo el equipo la ve) y «Cerrar sin responder» como botón principal si no hace falta responder
    const rec = r?.ok ? String(r.recomendacion || '').trim() : '';
    const noResponder = /no hace falta (responder|contestar)/i.test(rec);
    btCerrar.hidden = !noResponder;
    btSig.classList.toggle('pri', !noResponder);
    const faltas = (c?.faltas || []).filter(Boolean);
    const puntos = (r?.ok ? (r.puntos_del_cliente || []) : []).filter(p => p?.punto);
    const datos = (r?.ok ? (r.datos_citados || []) : []).filter(d => d?.dato);
    const paso = r?.ok && r.siguiente_paso && r.siguiente_paso.que ? r.siguiente_paso : null;
    const nFaltan = huecosTexto.length + pendientes.length + faltas.filter(f => !/por completar/i.test(f)).length;
    if (!nFaltan && !puntos.length && !rec && !datos.length && !paso) { falta.replaceChildren(); return; }
    const det = h('details', { open: S._faltaAbierto || null, style: { minWidth: '0' } },
      h('summary', { class: 'sub', style: { cursor: 'pointer', minHeight: 'var(--s-8)', display: 'flex', alignItems: 'center', gap: 'var(--s-1)' } },
        icono(nFaltan ? 'alert' : 'info', { clase: 's' }), nFaltan ? `Lo que falta (${nFaltan})` : rec ? 'Recomendación y datos' : `Qué pedía el cliente (${puntos.length})`),
      h('div', { class: 'pila', style: { gap: 'var(--s-2)', maxHeight: '180px', overflowY: 'auto', padding: 'var(--s-2) 0' } },
        huecosTexto.length ? h('div', {}, h('p', { class: 'sub' }, 'Por completar en el texto (Enviar no sale con corchetes): pulsa para ir'),
          h('div', { class: 'fila', style: { gap: 'var(--s-1)' } }, huecosTexto.map(hh => h('button', { type: 'button', class: 'bt mini', title: 'Ir a ese hueco', on: { click: () => irAHueco(hh) } }, hh)))) : null,
        faltas.length ? h('ul', { class: 'lista-i', style: { margin: '0' } }, faltas.map(f => h('li', {},
          h('button', { type: 'button', class: 'bt mini', style: { whiteSpace: 'normal', textAlign: 'left' }, title: 'Ir al primer hueco', on: { click: () => irAHueco() } }, icono('alert', { clase: 's' }), f)))) : null,
        huecos.length ? h('ul', { class: 'lista-i', style: { margin: '0' } }, huecos.map((hh, i) => {
          const cb = h('input', { type: 'checkbox', id: `bdj-h-${i}`, checked: tachados.includes(i) || null });
          cb.addEventListener('change', () => { const t2 = S.textos.get(x.id) || {}; const l = new Set(t2.hechos || []); cb.checked ? l.add(i) : l.delete(i); S.textos.set(x.id, { ...t2, hechos: [...l] }); S._faltaAbierto = true; calidad(); });
          return h('li', {}, h('label', { for: `bdj-h-${i}`, class: 'fila', style: { flexWrap: 'nowrap', alignItems: 'flex-start', gap: 'var(--s-2)', cursor: 'pointer' } }, cb, h('span', { style: { whiteSpace: 'normal' } }, hh)));
        })) : null,
        rec ? h('div', { class: 'aviso info', role: 'note' }, icono('info', { clase: 's' }), h('span', { style: { whiteSpace: 'normal' } }, h('b', {}, 'Recomendación (solo la ve el equipo): '), rec)) : null,
        paso ? h('p', { style: { margin: '0', whiteSpace: 'normal' } }, h('b', {}, 'Siguiente paso: '), `${paso.que}${paso.quien ? ` · ${paso.quien}` : ''}${paso.cuando ? ` · ${paso.cuando}` : ''}`) : null,
        datos.length ? h('div', {}, h('p', { class: 'sub' }, 'Datos que cita:'), h('ul', { class: 'lista-i', style: { margin: '0' } }, datos.map(d => h('li', {}, h('span', { style: { whiteSpace: 'normal' } }, d.dato, h('span', { class: 'sub' }, ` · ${d.fuente || ''}${d.fecha ? ` · ${fDiaRO(d.fecha)}` : ''}`)))))) : null,
        puntos.length ? h('div', {}, h('p', { class: 'sub' }, 'Qué pedía el cliente y cómo queda:'),
          h('ul', { class: 'lista-i', style: { margin: '0' } }, puntos.map(p => h('li', {}, h('span', { style: { whiteSpace: 'normal' } }, h('b', {}, p.punto), ` → ${p.como_queda || ''}`))))) : null));
    det.addEventListener('toggle', () => { S._faltaAbierto = det.open; ajustarEditor(S); });
    falta.replaceChildren(det);
  }
  function cerrarSinResponder() {
    const r = S.borradores.get(x.id);
    const rec = String(r?.recomendacion || 'no hace falta responder').slice(0, 300);
    programar(ctx, S, x, 'cerrar', `Cerrar ${x.numero} sin responder: ${rec}`, { estado: 'Cerrado', ticket: x.numero, motivo: rec, desde: 'recomendación del borrador' });
  }

  // ---- el borrador de la IA, ya cargado dentro (o la plantilla si no hay)
  const ia = iaDe(ctx);
  async function pedirBorrador(nuevo = false) {
    estadoIA.replaceChildren(h('span', { class: 'ia-cargando', role: 'status' }, h('i'), h('i'), h('i'), nuevo ? 'Pidiendo otra versión…' : 'Cargando el borrador de la IA…'));
    let r;
    try { r = await ia.borrador(x.numero, nuevo); } catch (e) { r = { ok: false, motivo: e?.status === 403 ? e.message : `No se ha podido pedir: ${e?.message || e}` }; }
    S.borradores.set(x.id, r);
    if (S.sel !== x.id || !ta.isConnected) return;
    const t = S.textos.get(x.id) || {};
    if (!t.editado || nuevo) {
      if (r.ok && r.cuerpo) { ta.value = r.cuerpo; S.textos.set(x.id, { ...t, modo: 'responder', texto: r.cuerpo, original: r.cuerpo, asunto: r.asunto, esPlantilla: false, editado: false }); }
      else if (!ta.value.trim()) {
        const pl = x.queja ? PLANTILLAS.find(p => p.id === 'queja') : PLANTILLAS[0];
        ta.value = pl.cuerpo(saludo);
        S.textos.set(x.id, { ...t, modo: 'responder', texto: ta.value, original: ta.value, esPlantilla: true, editado: false });
      }
      ajustarEditor(S);
    }
    calidad();
  }
  if (modo === 'responder') {
    if (t0.texto !== undefined) { ta.value = t0.texto; calidad(); if (!S.borradores.has(x.id)) pedirBorrador(false); }
    else if (S.borradores.has(x.id)) { const r = S.borradores.get(x.id); ta.value = r.ok && r.cuerpo ? r.cuerpo : (x.queja ? PLANTILLAS[4] : PLANTILLAS[0]).cuerpo(saludo); S.textos.set(x.id, { modo, texto: ta.value, original: ta.value, esPlantilla: !(r.ok && r.cuerpo), asunto: r.asunto }); calidad(); }
    else pedirBorrador(false);
    if (!puedeResponder) aviso.append(avisoParcial('Al cliente le contestan su account, las jefas, Operaciones y Dirección. Tú puedes dejar una nota interna.', { tipo: 'info' }));
  } else {
    if (!x.cliente_id) aviso.append(avisoParcial('Correo sin cliente: desde la app solo se contesta a un cliente. Asígnalo a su account, despáchalo o deja una nota.', { tipo: 'info' }));
    ta.value = t0.textoNota || '';
    ta.setAttribute('aria-label', 'Nota interna');
    ta.placeholder = 'Lo que sabe el equipo y el cliente no ve (queda en el ticket y en el rastro)';
    ta.addEventListener('input', () => S.textos.set(x.id, { ...(S.textos.get(x.id) || {}), textoNota: ta.value }));
  }

  function enviar(siguiente) {
    aviso.querySelector('[data-error]')?.remove();
    const err = m => { aviso.prepend(h('div', { class: 'aviso', role: 'alert', 'data-error': '' }, icono('alert', { clase: 's' }), h('span', {}, m))); ajustarEditor(S); };
    const texto = ta.value.trim();
    if (!texto) { err(modo === 'nota' ? 'La nota está vacía.' : 'La respuesta está vacía.'); ta.focus(); return; }
    if (modo === 'nota') {
      S.textos.set(x.id, { ...(S.textos.get(x.id) || {}), textoNota: '' });
      if (siguiente) { accionDirecta(ctx, S, x, 'nota_interna', texto, { privada: true, ticket: x.numero }).then(() => mover(ctx, S, 1)); }
      else accionDirecta(ctx, S, x, 'nota_interna', texto, { privada: true, ticket: x.numero });
      return;
    }
    if (!puedeResponder) { err('Este cliente no lo llevas: deja una nota interna.'); return; }
    const huecos = texto.match(RX_HUECO);
    if (huecos) {
      err(`Completa lo que falta antes de enviar: ${[...new Set(huecos)].join(', ')}`);
      const i = ta.value.indexOf(huecos[0]); ta.focus(); ta.setSelectionRange(i, i + huecos[0].length);
      return;
    }
    if (S.reales && !caja.__confirmado) {
      caja.__confirmado = true;
      aviso.prepend(h('div', { class: 'aviso', role: 'alert', 'data-error': '' }, icono('alert', { clase: 's' }), h('span', {}, h('b', {}, 'Los envíos reales están activados: '), 'este correo sale de verdad. Pulsa otra vez para enviarlo.')));
      (siguiente ? btSig : btEnviar).replaceChildren(icono('send', { clase: 's' }), 'Sí, enviar de verdad');
      ajustarEditor(S);
      return;
    }
    const t = S.textos.get(x.id) || {};
    const r = S.borradores.get(x.id);
    const ok = programar(ctx, S, x, 'responder', texto, { de: 'marketing@rankingonline.com', asunto: t.asunto || `RE: ${x.asunto || ''}`, firma_de: real.id, con_firma: !t.sinFirma,
      nota_interna: `Enviado desde el panel por ${real.nombre}.`, ticket: x.numero, adjuntos_simulados: (S.adjuntos.get(x.id) || []).map(a => a.nombre),
      borrador_ia: r?.ok ? { origen: r.origen, editado: texto !== String(r.cuerpo || '').trim() } : null }, { siguiente });
    if (ok && r?.ok) ctx.rastro?.({ accion: 'ia_usar', objeto: x.numero, detalle: { origen: r.origen, editado: texto !== String(r.cuerpo || '').trim() } });
    if (ok && !siguiente && S.modo !== 'uno') { S.sel = x.id; pintarColLista(ctx, S); pintarCentro(ctx, S); }
  }
  caja.__enviar = enviar;
  return caja;
}

function editorLlamada(ctx, S, x) {
  const caja = h('div', { 'data-bdj': 'editor', style: { flex: 'none', padding: 'var(--s-3) var(--s-4)', display: 'grid', gridTemplateColumns: 'minmax(0, 1fr)', gap: 'var(--s-2)' } });
  if (x.hecho) { caja.append(h('div', { class: 'aviso info', role: 'status' }, icono('ok', { clase: 's' }), `${etiquetaTipo(x.hecho.tipo)} · en la cola simulada`)); return caja; }
  const ta = h('textarea', { id: 'bdj-texto', 'data-item': x.id, 'aria-label': 'Nota de la llamada', placeholder: 'Qué habéis hablado (queda en el rastro; opcional)',
    style: { width: '100%', resize: 'none', border: 'var(--borde)', borderRadius: 'var(--r-m)', padding: 'var(--s-3)', font: 'var(--t-cuerpo)', minHeight: '72px', background: 'var(--card)', color: 'var(--ink)' } });
  ta.value = S.textos.get(x.id)?.texto || '';
  const ro = ctx.soloLectura;
  const devuelta = siguiente => programar(ctx, S, x, 'llamada_devuelta', ta.value.trim() || `Devuelta: ${x.cliente || x.numero_oculto}`, { llamadas: x.llamadas, nota: ta.value.trim() || null }, { siguiente });
  ta.addEventListener('keydown', e => { if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { e.preventDefault(); devuelta(true); } });
  caja.append(
    h('p', { class: 'sub' }, x.cliente ? `Devuelve la llamada a ${x.cliente} desde tu extensión. El teléfono completo no viaja a la app: está en la ficha del cliente o en Zadarma.` : 'Si es de un cliente, apunta el número en su ficha.'),
    ta,
    h('div', { class: 'fila', style: { justifyContent: 'flex-end', gap: 'var(--s-2)' } },
      h('button', { type: 'button', class: 'bt', 'aria-disabled': 'true', title: 'Llamar con un clic (suena tu teléfono y te conecta) llega cuando la app esté en el servidor' }, icono('phone', { clase: 's' }), 'Llamar con un clic · pronto'),
      h('button', { type: 'button', class: 'bt pri', 'data-bdj-enviar': 'siguiente', disabled: ro || null, on: { click: () => devuelta(true) } }, icono('ok', { clase: 's' }), 'Ya la he devuelto y siguiente')));
  caja.__enviar = devuelta;
  return caja;
}

/** El editor crece con el texto (quejas de ~160 palabras, resultados de ~200) sin echar el hilo: como mucho deja 160 px de
 *  hilo (ampliado, el 85 % del centro); nunca menos de 6 líneas. En el móvil, 4 líneas (ampliado, media pantalla). */
function ajustarEditor(S) {
  const col = S.modo === 'uno' ? null : S.colCentro;
  const ta = (col || S.cont)?.querySelector('#bdj-texto');
  if (!ta) return;
  if (S.modo === 'uno') { ta.style.height = S.ampliado ? '50vh' : '96px'; return; }
  const alto = col.getBoundingClientRect().height;
  if (!alto) return;
  const ed = col.querySelector('[data-bdj="editor"]');
  const resto = ed ? ed.getBoundingClientRect().height - ta.getBoundingClientRect().height : 120;
  const cab = col.firstElementChild?.getBoundingClientRect().height || 0;
  const libre = alto - cab - resto;
  const antes = ta.style.height;
  ta.style.height = 'auto';
  const desea = ta.scrollHeight + 2;
  // escribiendo (foco en el texto), el hilo cede: se queda en 96 px; leyendo, en 160 px
  const tope = S.ampliado ? libre * 0.85 : Math.max(120, libre - (document.activeElement === ta ? 96 : 160));
  ta.style.height = `${Math.round(Math.max(120, Math.min(desea, tope)))}px`;
  if (antes !== ta.style.height) ta.dispatchEvent(new Event('scroll'));
}

// ---------------------------------------------------------------- teclado
function teclado(ctx, S) {
  return e => {
    if (!S.cont?.isConnected) return;
    if (!String(location.hash).startsWith(`#/${ID}`) || S.alt) return;
    const el = document.activeElement;
    const enCampo = /^(INPUT|SELECT|TEXTAREA)$/.test(el?.tagName) || el?.isContentEditable;
    const pal = document.getElementById('paleta');
    if (e.metaKey || e.ctrlKey || e.altKey || enCampo || document.querySelector('.menu-flot') || (pal && !pal.hidden)) return;
    const x = S.items.find(y => y.id === S.sel);
    const k = e.key;
    const hecho = () => { e.preventDefault(); e.stopPropagation(); };
    if (k === 'j' || k === 'k' || k === 'ArrowDown' && el?.closest?.('[data-bdj="lista"]') || k === 'ArrowUp' && el?.closest?.('[data-bdj="lista"]')) {
      hecho();
      if (S.modo === 'uno' && !ctx.params[0]) { const f = [...S.cont.querySelectorAll('[data-bdj="lista"] [data-id]')]; const i = f.indexOf(el); (f[Math.min(f.length - 1, Math.max(0, i + (k === 'j' || k === 'ArrowDown' ? 1 : -1)))] || f[0])?.focus(); return; }
      mover(ctx, S, k === 'j' || k === 'ArrowDown' ? 1 : -1);
      S.lista?.querySelector('[aria-current="true"]')?.focus({ preventScroll: true });
      return;
    }
    if (k === 'z') { hecho(); deshacer(); return; }
    if (!x || x.hecho || x.pendiente) return;
    if (k === 'r') { hecho(); const ta = S.cont.querySelector('#bdj-texto'); if (ta) { ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length); } }
    else if (k === 'e' && x.tipo === 'correo') { hecho(); despachar(ctx, S, x); }
    else if (k === 'p' && x.tipo === 'correo' && !x.esperando) { hecho(); esperar(ctx, S, x); }
    else if (k === 'a') {
      hecho();
      const b = S.cont.querySelector('[data-bdj-asignar] button');
      if (b) b.click(); else avisoFlotante('Asignar es de Operaciones, Proyectos y Dirección. Puedes avisar al account.', { icono: 'info' });
    }
  };
}

// ---------------------------------------------------------------- contexto del cliente (derecha / pestaña «Cliente»)
function pintarContexto(ctx, S) {
  const col = S.colCtx;
  if (!col || S.modo !== 'tres') return;
  col.replaceChildren();
  const x = S.items.find(y => y.id === S.sel);
  const plegar = h('button', { type: 'button', class: 'bt mini icono', 'aria-expanded': String(S.ctxAbierto), 'aria-label': S.ctxAbierto ? 'Plegar el contexto del cliente' : 'Ver el contexto del cliente',
    title: S.ctxAbierto ? 'Plegar (más sitio para escribir)' : 'Ver el contexto del cliente',
    on: { click: () => { S.ctxAbierto = !S.ctxAbierto; guardarS('ro.bandeja.contexto', S.ctxAbierto ? '1' : '0'); guardarTexto(S); S.rehacer(); } } }, icono(S.ctxAbierto ? 'derecha' : 'izquierda', { clase: 's' }));
  if (!S.ctxAbierto) {
    col.append(h('div', { style: { display: 'grid', justifyItems: 'center', gap: 'var(--s-2)', padding: 'var(--s-2) 0' } }, plegar,
      x?.cliente_id ? h('span', { class: `ico-c s ${claseGravedad(ctx, x)}`, title: `Cliente: ${x.cliente}` }, icono('cli')) : null));
    return;
  }
  col.append(h('header', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 'var(--s-2)', padding: 'var(--s-3)', borderBottom: 'var(--borde-suave)', flex: 'none' } },
    h('h2', { style: { font: 'var(--t-h2)', margin: '0', display: 'flex', gap: 'var(--s-2)', alignItems: 'center' } }, icono('cli'), 'El cliente'), plegar));
  const z = h('div', { style: { flex: '1 1 auto', minHeight: '0', overflowY: 'auto' } });
  col.append(z);
  if (x) pintarContextoEn(z, ctx, S, x);
}
const claseGravedad = (ctx, x) => { const g = ctx.verdad?.(x.cliente_id)?.gravedad; return g === 'critico' ? 'rojo' : g === 'atencion' ? 'ambar' : g === 'bien' ? 'verde' : 'gris'; };

function pintarContextoEn(z, ctx, S, x) {
  z.replaceChildren();
  const sec = (ic, tit, ...hijos) => h('section', { style: { padding: 'var(--s-3)', borderBottom: 'var(--borde-suave)', display: 'grid', gap: 'var(--s-2)' } },
    h('span', { class: 'titulo-seccion' }, icono(ic, { clase: 's' }), tit), ...hijos);
  if (!x.cliente_id) {
    z.append(sec('alert', 'Sin cliente', h('p', { class: 'sub' }, x.tipo === 'llamada' ? 'Número que no está en ninguna ficha.' : 'El remitente no es de ninguna cuenta de cliente. Si lo es, asígnalo a su account o apúntalo en su ficha.')));
    return;
  }
  const v = ctx.verdad?.(x.cliente_id) || {};
  const yo = yoDe(ctx);
  const [cls, txt] = ETIQUETA_GRAVEDAD[{ critico: 'rojo', atencion: 'ambar', bien: 'verde' }[v.gravedad]] || ['gris', 'Sin dato'];
  const ficha = MODULOS.find(m => (m.id === 'ficha' || m.id === 'ficha-cliente') && m.estado === 'hecho');
  z.append(...[
    h('div', { class: 'fila', style: { padding: 'var(--s-3)', flexWrap: 'nowrap', borderBottom: 'var(--borde-suave)' } }, x.cli ? logoCliente(x.cli) : null,
      h('div', { style: { minWidth: '0' } }, h('b', {}, x.cliente), h('div', { class: 'fila', style: { gap: 'var(--s-1)' } }, chipEstado(cls, txt), v.nuevo ? chipEstado('azul', 'Cliente nuevo') : null))),
    (v.motivos || []).length ? sec('flag', 'Por qué', h('ul', { class: 'lista-i', style: { margin: '0' } }, [...new Set(v.motivos)].slice(0, 3).map(m => h('li', {}, h('span', { style: { whiteSpace: 'normal' } }, m))))) : null,
    sec('persona', 'Equipo',
      h('div', { class: 'fila', style: { flexWrap: 'nowrap' } }, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(x.account)),
        h('span', {}, v.account ? (v.account === yo ? 'Tú eres su account' : `Account: ${ctx.nombre(v.account)}`) : (v.sin_account || 'Sin account'))),
      (v.equipo?.trafficker || []).length ? h('span', { class: 'sub' }, `Publicidad: ${(v.equipo.trafficker || []).map(p => nom1(ctx.nombre(p.persona_id))).join(', ')}`) : null),
  ].filter(Boolean));
  // otros correos del mismo cliente en la bandeja
  const otros = S.items.filter(y => y.cliente_id === x.cliente_id && y.id !== x.id && !y.hecho && !y.pendiente && !y.auto);
  if (otros.length) z.append(sec('inbox', `Más correos de ${x.cliente} (${otros.length})`,
    h('div', { class: 'pila', style: { gap: 'var(--s-1)' } }, otros.slice(0, 4).map(y => h('button', { type: 'button', class: 'bt mini', style: { justifyContent: 'space-between', whiteSpace: 'normal', textAlign: 'left' },
      on: { click: () => { if (!filtrar(ctx, S).some(f => f.id === y.id)) { S.filtro = 'todos'; pintarColLista(ctx, S); } abrirItem(ctx, S, y.id); } } }, h('span', { style: { minWidth: '0' } }, y.asunto || 'Llamada'), h('span', { class: `chip ${y.gravedad || 'gris'}` }, relojTxt(y.horas)))))));
  // lo que viene de la ficha (servidor, recortado): campaña y leads, tareas, reuniones; impago si lo puede ver
  const resto = h('div', {}, h('div', { class: 'ia-cargando', role: 'status', style: { padding: 'var(--s-3)' } }, h('i'), h('i'), h('i'), 'Leyendo la ficha…'));
  z.append(resto);
  cargarCliente(ctx, S, x.cliente_id).then(({ doc, impago }) => {
    if (!resto.isConnected) return;
    const F = doc?.fuentes || {};
    const meta = F.meta?.datos, tareas = F.tareas?.datos, reu = F.reuniones?.datos;
    const leads = meta?.leads;
    const sube = leads && leads['7d_prev'] ? Math.round((leads['7d'] - leads['7d_prev']) / leads['7d_prev'] * 100) : null;
    resto.replaceChildren(...[
      impago ? sec('cartera', 'Impago', h('div', { class: 'aviso' }, icono('alert', { clase: 's' }), h('span', {}, impago.texto || 'Tiene facturas vencidas.',
        impago.cuota_vencida ? ` (${fmt.eur ? fmt.eur(impago.cuota_vencida) : impago.cuota_vencida + ' €'}, ${impago.dias_max} días)` : ''))) : null,
      sec('megafono', 'Campaña y leads',
        h('div', { class: 'fila' }, chipEstado(v.campana_activa ? 'verde' : 'gris', v.campana_activa ? 'Campaña de Meta activa' : 'Sin campaña de Meta activa')),
        leads ? h('p', { style: { margin: '0' } }, h('b', {}, fmt.num(leads['7d'] || 0)), ` leads de Meta en 7 días${sube !== null ? ` (${sube >= 0 ? '+' : ''}${sube} % frente a la semana anterior)` : ''} · ayer ${fmt.num(leads.ayer || 0)}`)
          : v.leads_meta_7d !== null && v.leads_meta_7d !== undefined ? h('p', { style: { margin: '0' } }, h('b', {}, fmt.num(v.leads_meta_7d)), ' leads de Meta en 7 días') : h('p', { class: 'sub' }, 'Sin dato de leads'),
        v.fuga_integracion ? chipEstado(v.fuga_integracion === 'grave' ? 'rojo' : 'ambar', `Fuga ${v.fuga_integracion}: no llegan todos a GoHighLevel`) : null),
      sec('casilla', 'Tareas en curso',
        v.bloqueos?.tareas ? h('p', { style: { margin: '0' } }, chipEstado('rojo', 'Bloqueada'), ` ${v.bloqueos.tarea || ''} · ${fmt.num(v.bloqueos.dias_max, 1)} días`) : null,
        (tareas?.en_revision_detalle || []).length ? h('ul', { class: 'lista-i', style: { margin: '0' } }, tareas.en_revision_detalle.slice(0, 3).map(t => h('li', {},
          h('span', { style: { whiteSpace: 'normal' } }, t.url ? h('a', { href: t.url, target: '_blank', rel: 'noopener' }, t.nombre) : t.nombre, h('span', { class: 'sub' }, ` · ${t.estado} desde hace ${t.dias} días`))))) : null,
        tareas ? h('p', { class: 'sub' }, `${fmt.num(tareas.vencidas || 0)} vencidas · ${fmt.num(tareas.revision_total || 0)} en revisión · ${fmt.num(tareas.cerradas_semana || 0)} cerradas esta semana`) : h('p', { class: 'sub' }, 'Sin dato de tareas')),
      sec('cal', 'Reuniones',
        h('p', { style: { margin: '0' } }, `Última: ${fDiaRO(reu?.ult_reunion || v.ultima_reunion)}${reu?.dias_sin_reunion !== undefined ? ` (hace ${reu.dias_sin_reunion} días)` : ''}`),
        h('p', { class: 'sub' }, reu?.prox_reunion ? `Próxima: ${fDiaHoraRO(reu.prox_reunion)}` : 'Sin próxima reunión en el calendario'),
        v.sin_reunion_mes_pasado ? chipEstado('ambar', 'Sin reunión el mes pasado') : null),
      sec('link', 'Abrir',
        h('div', { class: 'fila', style: { gap: 'var(--s-1)' } },
          h('a', { class: 'bt mini', href: ficha ? `#/${ficha.id}/${x.cliente_id}` : `#/en-rojo/${x.cliente_id}` }, icono('cli', { clase: 's' }), 'Ficha'),
          x.url ? h('a', { class: 'bt mini', href: x.url, target: '_blank', rel: 'noopener' }, icono('ext', { clase: 's' }), 'Desk') : null,
          F.chat?.abrir?.url ? h('a', { class: 'bt mini', href: F.chat.abrir.url, target: '_blank', rel: 'noopener' }, icono('chat', { clase: 's' }), 'Canal') : null,
          F.ghl?.abrir?.url ? h('a', { class: 'bt mini', href: F.ghl.abrir.url, target: '_blank', rel: 'noopener' }, icono('ext', { clase: 's' }), 'GHL') : null)),
    ].filter(Boolean));
  });
}
async function cargarCliente(ctx, S, cid) {
  if (S.clientes.has(cid)) return S.clientes.get(cid);
  const p = (async () => {
    let doc = null, impago = null;
    if (ctx.servidor) { try { doc = await ctx.api(`cliente/${cid}`); } catch { doc = null; } }
    if (ctx.veModulo?.('ficha') || ctx.veModulo?.('finanzas')) {
      if (!S._impagos) S._impagos = ctx.datosModulo('finanzas/impagos_clientes').catch(() => ({ clientes: [] }));
      try { impago = ((await S._impagos).clientes || []).find(c => c.cliente_id === cid) || null; } catch { impago = null; }
    }
    return { doc, impago };
  })();
  S.clientes.set(cid, p);
  return p;
}

// ---------------------------------------------------------------- móvil: conversación a pantalla completa
function pintarConvMovil(cont, ctx, S) {
  const x = S.items.find(y => y.id === S.sel);
  if (!x) {
    cont.append(h('a', { class: 'bt', href: `#/${ID}` }, icono('volver'), 'Volver a la bandeja'),
      vacio({ icono: 'candado', borde: true, titulo: 'Este elemento no está en tu bandeja', texto: 'O ya no está pendiente, o es de un cliente que no llevas.' }));
    return;
  }
  ctx.titulo('Bandeja', `${x.cliente || 'Sin cliente'} · ${x.tipo === 'correo' ? 'correo sin contestar' : 'llamada sin devolver'}`);
  const caja = h('section', { class: 'panel', 'data-bdj': 'conversacion', style: { display: 'flex', flexDirection: 'column', overflow: 'visible' } });
  S.colCentro = caja;
  const volver = () => { if (S._empujado) { S._empujado = false; history.back(); } else irMovil(ctx, S, null); };
  cont.append(h('div', { class: 'fila', style: { marginBottom: 'var(--s-2)' } }, h('button', { type: 'button', class: 'bt mini', on: { click: volver } }, icono('volver', { clase: 's' }), 'Bandeja')), caja);
  const cab = cabeceraConv(ctx, S, x);
  caja.append(cab);
  const seg = h('div', { class: 'segm', role: 'tablist', 'aria-label': 'Vista', style: { justifySelf: 'start' } },
    [['conv', 'Conversación', 'mail'], ['cliente', 'Cliente', 'cli']].map(([v, t, ic]) => h('button', { type: 'button', role: 'tab', 'aria-selected': String(S.pestCentro === v), 'aria-pressed': String(S.pestCentro === v),
      on: { click: () => { guardarTexto(S); S.pestCentro = v; S.rehacer(); } } }, icono(ic, { clase: 's' }), ' ', t)));
  (cab.querySelector('[role="toolbar"]') || cab).append(seg);
  if (S.pestCentro === 'cliente') { const z = h('div', {}); caja.append(z); pintarContextoEn(z, ctx, S, x); pintarPie(ctx, S); return; }
  const hilo = h('div', { 'data-bdj': 'hilo', style: { padding: 'var(--s-3)', background: 'var(--card-2)', borderTop: 'var(--borde-suave)' } });
  caja.append(hilo);
  pintarHilo(hilo, ctx, S, x);
  const ed = x.tipo === 'llamada' ? editorLlamada(ctx, S, x) : editor(ctx, S, x);
  // el editor, fijo abajo mientras se lee el hilo
  Object.assign(ed.style, { position: 'sticky', bottom: '0', zIndex: '2', borderTop: 'var(--borde)', boxShadow: 'var(--sombra-3)' });
  caja.append(ed);
  ajustarEditor(S);
  pintarPie(ctx, S);
}

function nombrePersona(ctx, id) {
  if (!id) return '—';
  if (id === (ctx.real || ctx.persona).id) return 'ti';
  return (ctx.datos.personas || []).find(q => q.id === id)?.nombre || id;
}

// ---------------------------------------------------------------- triaje (correos sin responsable)
function pintarTriaje(z, ctx, S) {
  const pend = S.triaje.filter(t => !S.porObjeto.has(String(t.numero)));
  const chips = chipsFiltro({ etiqueta: 'Propuesta', clave: 'bandeja.triaje', opciones: [
    { valor: 'seguro', texto: 'Cliente seguro', icono: 'ok', cuenta: pend.filter(t => t.propuesta === 'seguro').length },
    { valor: 'dudoso', texto: 'Dudoso', icono: 'info', cuenta: pend.filter(t => t.propuesta === 'dudoso').length },
    { valor: 'sin_cliente', texto: 'Sin cliente', icono: 'alert', cuenta: pend.filter(t => t.propuesta === 'sin_cliente').length },
  ], alCambiar: () => pintarL() });
  const caja = h('ul', { class: 'primero' });
  const mas = h('div', { class: 'tabla-mas' });
  const cab = h('div', { class: 'cuerpo pila' }, h('p', { class: 'sub' },
    `Correos abiertos en Desk sin nadie asignado. Propuesta: el account del cliente si el remitente es de una cuenta de cliente. Muchos son de nov-2025 a jul-2026: probablemente baste con cerrarlos. Fuera quedan ${fmt.num(S.D.ruido?.['triaje · ruido'] || 0)} avisos que no son de clientes.`), chips);
  z.append(h('div', { class: 'panel' }, h('header', {}, h('div', {}, h('h2', {}, icono('persona'), 'Correos sin responsable'), h('p', { class: 'sub' }, 'Repartir: asignar al account propuesto o cerrar'))), cab, caja, mas));
  let limite = 40;
  function pintarL() {
    const v = chips.valor();
    const xs = pend.filter(t => t.propuesta === v).sort((a, b) => (a.dias ?? 9e9) - (b.dias ?? 9e9));
    caja.replaceChildren(); mas.replaceChildren();
    if (!xs.length) { caja.append(h('li', { style: { display: 'block' } }, vacio({ icono: 'ok', tono: 'celebrar', titulo: 'Nada por repartir aquí' }))); return; }
    for (const t of xs.slice(0, limite)) {
      caja.append(h('li', {},
        h('span', { class: `ico-c s ${t.propuesta === 'seguro' ? '' : t.propuesta === 'dudoso' ? 'ambar' : 'gris'}` }, icono(t.propuesta === 'seguro' ? 'persona' : t.propuesta === 'dudoso' ? 'info' : 'alert')),
        h('div', {}, h('div', { class: 'mot' }, t.asunto || '(sin asunto)'),
          h('div', { class: 'det meta-linea' }, h('span', {}, t.cliente || 'sin cliente'), h('span', {}, `desde ${fDiaRO(t.fecha)} (${t.dias ?? '—'} días laborables)`), h('span', {}, t.motivo))),
        h('div', { class: 'acc' },
          t.url ? h('a', { class: 'bt mini', href: t.url, target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir en Desk') : null,
          t.agente_propuesto_id && puedeAsignar(ctx) ? botonConfirmar({ texto: `Asignar a ${ctx.nombre(t.agente_propuesto_id)}`, pregunta: `¿Asignar a ${ctx.nombre(t.agente_propuesto_id)}?`, confirmar: 'Sí', mini: true, soloLectura: ctx.soloLectura,
            alConfirmar: async () => { await ctx.accion({ herramienta: 'desk', tipo: 'asignar', objeto: t.numero, cliente_id: t.cliente_id || null, texto: `Asignar a ${t.agente_propuesto}`, vista_previa: { a: t.agente_propuesto_id, ticket: t.numero, origen: 'triaje' } }); S.porObjeto.set(String(t.numero), [{ tipo: 'asignar' }]); setTimeout(pintarL, 900); return 'En la cola simulada'; } }) : null,
          botonConfirmar({ texto: 'Cerrar sin contestar', pregunta: '¿Cerrar (antiguo o ya resuelto)?', confirmar: 'Sí', mini: true, soloLectura: ctx.soloLectura,
            alConfirmar: async () => { await ctx.accion({ herramienta: 'desk', tipo: 'cerrar', objeto: t.numero, cliente_id: t.cliente_id || null, texto: `Cerrar ${t.numero} desde el reparto (sin responsable, ${t.dias} días)`, vista_previa: { estado: 'Cerrado', ticket: t.numero } }); S.porObjeto.set(String(t.numero), [{ tipo: 'cerrar' }]); setTimeout(pintarL, 900); return 'En la cola simulada'; } }))));
    }
    if (xs.length > limite) mas.append(h('button', { type: 'button', class: 'bt', on: { click: () => { limite += 60; pintarL(); } } }, icono('mas'), `Ver más (${xs.length - limite})`));
  }
  pintarL();
}

// ---------------------------------------------------------------- WhatsApp (W6)
function pintarWhatsapp(z) {
  z.append(panel({ titulo: 'WhatsApp uno a uno', icono: 'wa', sub: 'Hueco preparado: llega con WhatsApp Business conectado' },
    h('div', { class: 'cuerpo pila' },
      vacio({ icono: 'wa', titulo: 'Aún sin conectar', quien: 'Tomás (con su móvil)',
        texto: 'Con la coexistencia de WhatsApp Business los chats uno a uno con clientes entrarán aquí, mezclados con los correos y con la misma cuenta atrás de 24 y 48 h. Los grupos («Concilia-Ranking» y parecidos) siguen en el móvil. No antes del 16-oct (cambio del alta de Meta del 15-oct).' }),
      h('div', {}, h('b', {}, 'Lo que hace Tomás (7 pasos):'),
        h('ol', {}, ['Actualizar WhatsApp Business y hacer copia de seguridad', 'Cartera de negocio verificada en Meta', 'Subcuenta de GHL aparte «Clientes RO», sin flujos', 'Dar de alta el número con su móvil (coexistencia)', 'Volver a vincular WhatsApp Web', 'Permiso de GHL para leer y escribir conversaciones', 'Abrir la app del móvil cada 13 días (la app avisará a los 12)'].map(t => h('li', {}, t)))),
      h('div', { class: 'fila' }, h('button', { type: 'button', class: 'bt', 'aria-disabled': 'true', title: 'Llega con WhatsApp Business conectado' }, icono('wa'), 'Contestar por WhatsApp · todavía no')))));
}

// ---------------------------------------------------------------- de dónde sale
function pintarComo(z, ctx, S) {
  const D = S.D;
  const deps = D.departamentos || [];
  const legibles = deps.filter(d => d.legible);
  const sinPermiso = deps.filter(d => d.activo && !d.legible);
  const reglas = [
    ['mail', 'Correo sin contestar', 'El último mensaje del ticket es del cliente y el ticket no está cerrado (cualquier estado abierto o en espera de Desk: Abierto, En espera, Escalado, Por resolver, Por responder, En seguimiento).'],
    ['clock', 'Tiempo esperando', 'En horas y días laborables (de lunes a viernes), desde el último mensaje del cliente. Ámbar a las 24 h y rojo a las 48 h.'],
    ['alert', 'Queja', 'El asunto habla de pocos leads, urgencia, baja, cancelar, reclamar, errores o problemas. Las quejas nunca se esconden por antiguas.'],
    ['zap', 'Avisos automáticos y reenvíos', 'Zapier, boletines y circulares de marketing («¿Sabes…? Descúbrelo en esta guía», «Nota informativa»: no cuentan como correo de cliente sin contestar), reenvíos, avisos de Drive y de calendario («Cancelado:», «Invitación:», «Elemento compartido»…). Van aparte.'],
    ['filtro', 'Fuera de la bandeja', 'Correos del propio equipo, avisos de reuniones agendadas, candidaturas, respuestas automáticas, alertas y plataformas.'],
    ['phone', 'Llamada sin devolver', 'Entrante perdida (también las de 0 segundos) de los últimos 5 días laborables sin ninguna llamada contestada después con ese número. Un intento nuestro sin respuesta no cuenta como devuelta.'],
    ['clock', 'Esperando al cliente', 'Lo marcas tú cuando le toca al cliente: deja de contar como «sin responder» y espera en su filtro.'],
    ['doc', 'Hilo del correo', 'Se lee aquí cuando la app ya tiene el hilo (los correos que ha leído la IA); si no, «Leer el hilo en Desk».'],
    ['candado', 'Correos sin cliente', 'Proveedores y números desconocidos: solo los ven Operaciones y Dirección.'],
  ];
  z.append(h('div', { class: 'dos' },
    panel({ titulo: 'Cómo se cuenta', icono: 'info', sub: 'Las mismas reglas en la Bandeja, la ficha del cliente y Mi día' },
      h('div', { class: 'cuerpo pila' }, h('ul', { class: 'lista-i' }, reglas.map(([ic, k, v]) => h('li', {}, h('span', { class: 'ico-c s' }, icono(ic)), h('span', { class: 't', style: { whiteSpace: 'normal' } }, h('b', {}, k + ': '), v)))),
        h('div', { class: 'fila' }, frescura(fres(D.fuentes?.desk, 'Desk')), frescura(fres(D.fuentes?.zadarma, 'Zadarma')),
          h('a', { class: 'bt mini', href: 'https://my.zadarma.com/mystatistics/', target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir Zadarma')))),
    panel({ titulo: 'Departamentos de Desk', icono: 'inbox', sub: `${legibles.length} de ${deps.length} se pueden leer` },
      h('div', { class: 'cuerpo pila' },
        sinPermiso.length ? avisoParcial(`La app solo puede abrir los correos de ${legibles.map(d => d.nombre.replace(/\.$/, '')).join(', ')}. Faltan ${sinPermiso.length} departamentos activos (${sinPermiso.map(d => d.nombre).join(', ')}): hay que dar acceso a esos departamentos en Desk al usuario con el que lee la app.`, { titulo: 'Falta un permiso.' }) : null,
        h('ul', { class: 'lista-i' }, deps.slice().sort((a, b) => (b.legible - a.legible) || (b.activo - a.activo)).map(d =>
          h('li', {}, h('span', { class: `ico-c s ${d.legible ? 'verde' : d.activo ? 'ambar' : 'gris'}` }, icono(d.legible ? 'ok' : d.activo ? 'candado' : 'vacio')),
            h('span', { class: 't' }, String(d.nombre).replace(/\.$/, '')), h('span', { class: 'x' }, d.legible ? `${fmt.num(d.abiertos)} abiertos` : d.activo ? 'sin permiso' : 'desactivado')))))),
  ));
  const NOMBRE_RUIDO = { 'remitente @rankingonline': 'Del propio equipo', 'tomas@': 'Reenviados por Tomás', 'triaje · ruido': 'Sin responsable y sin cliente', 'aviso de reunión agendada/BOFU': 'Avisos de reunión agendada' };
  const ruido = Object.entries(D.ruido || {});
  if (ruido.length) z.append(panel({ titulo: 'Fuera de la bandeja', icono: 'filtro', sub: 'No son correos de clientes' },
    h('div', { class: 'cuerpo' }, h('ul', { class: 'lista-i' }, ruido.map(([k, n]) => h('li', {}, h('span', { class: 'ico-c s gris' }, icono('filtro')), h('span', { class: 't' }, NOMBRE_RUIDO[k] || (k.charAt(0).toUpperCase() + k.slice(1))), h('span', { class: 'x' }, fmt.num(n))))))));
}
