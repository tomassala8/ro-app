// modulos/bandeja.js · M3 «Bandeja» (E3 del plan v2 · ficha G2 del account).
// Correos de clientes sin contestar (ámbar a las 24 h, rojo a las 48 h, D-29) y llamadas de clientes sin devolver,
// quejas arriba, agrupado por account y por día. Se contesta aquí con la firma de quien envía (sale desde marketing@
// con nota interna «Enviado desde el panel por X», como servidor_panel/worker.js); en el prototipo todo va a la cola
// SIMULADA (ctx.accion): nada se escribe en Desk ni en Zadarma. Triaje de tickets sin agente para Operaciones.
// Hueco preparado para WhatsApp uno a uno (W6, no antes del 16-oct).
// Datos: data/bandeja/bandeja.json (fuentes_bandeja/generar_bandeja.py), recortado por servir.py: cada account solo
// recibe las filas de sus clientes; las filas sin cliente llevan persona_id = mili (solo Operaciones y Dirección).

import {
  h, fmt, icono, tile, tiles, chipEstado, chipsFiltro, pestanas, vacio, avisoParcial, panel, frescura, logoCliente,
  iniciales, selloMedible, botonConfirmar, avisoFlotante, pieFase2, limpiaTexto, menuMas, rejillaTarjetas,
} from '../componentes.js';
import { MODULOS } from './indice.js';
import { botonIA, estilos as estilosIA } from './ia_componentes.js';

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

const ID = 'bandeja';

const PLANTILLAS = [
  { id: 'recibido', texto: 'Recibido', cuerpo: n => `Hola${n ? ' ' + n : ''},\n\nRecibido, gracias. Lo estoy mirando y te digo algo antes de que acabe el día.\n\nUn saludo,` },
  { id: 'datos', texto: 'Pedir un dato', cuerpo: n => `Hola${n ? ' ' + n : ''},\n\nPara avanzar con esto me falta un dato: \n\nEn cuanto lo tenga, lo dejo hecho.\n\nUn saludo,` },
  { id: 'resuelto', texto: 'Resuelto', cuerpo: n => `Hola${n ? ' ' + n : ''},\n\nYa está resuelto: \n\nSi ves cualquier cosa rara, me dices y lo miramos.\n\nUn saludo,` },
  { id: 'llamada', texto: 'Mejor por teléfono', cuerpo: n => `Hola${n ? ' ' + n : ''},\n\nEsto lo vemos mejor en una llamada de diez minutos. ¿Te va bien hoy o mañana por la mañana?\n\nUn saludo,` },
];
const MOTIVOS_NO_APLICA = ['Ya contestado por otra vía (WhatsApp o teléfono)', 'No pide respuesta (agradecimiento, acuse, «ok»)', 'Es ruido o un aviso automático', 'No es de este cliente', 'Ex cliente o baja', 'Otro motivo'];

const ahora = () => Date.now();
const relojTxt = horas => {
  if (horas === null || horas === undefined) return '—';
  const hr = Math.round(horas);
  return hr < 24 ? `${hr} h` : `${Math.floor(hr / 24)} d ${hr % 24} h`;
};
const diaTxt = iso => {
  if (!iso) return 'Sin fecha';
  const d = new Date(iso.slice(0, 10) + 'T12:00:00');
  const hoy = new Date(); hoy.setHours(12, 0, 0, 0);
  const dias = Math.round((hoy - d) / 864e5);
  if (dias === 0) return 'Hoy';
  if (dias === 1) return 'Ayer';
  const ds = d.toLocaleDateString('es-ES', { weekday: 'long' });
  return `${ds[0].toUpperCase()}${ds.slice(1)} ${d.getDate()}-${_MES3[d.getMonth()]}`;   // §2.3: «Miércoles 2-sep», no «MIÉRCOLES, 2 SEPT»
};
const normal = t => String(t ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const nom1 = t => String(t || '').trim().split(/\s+/)[0] || '';

function edadH(fecha) {
  if (!fecha) return null;
  const d = new Date(fecha.replace(' ', 'T'));
  return Number.isNaN(+d) ? null : Math.max(0, (ahora() - d) / 36e5);
}
const fres = (f, nombre) => f ? { fuente: nombre, edad_h: edadH(f.hora), estado: f.estado === 'bien' ? 'ok' : 'viejo' } : { fuente: nombre, estado: 'sin datos' };

// Guía de diseño (auditoría 30): sin hoja de estilos propia; solo clases y piezas comunes (ronda 9 de E0: menuMas,
// rejillaTarjetas, .campo). El «null» suelto venía de Element.append(null): lo opcional va siempre filtrado.
const rejilla = lista => rejillaTarjetas(lista.filter(Boolean));

/** menuMas() común: hoy escribe «null» con el menú cerrado (replaceChildren(btn, null)); pedido a E0 (D-P-DS-FB 5).
 *  Mientras, se quita ese texto suelto aquí. */
function menuMasLimpio(o) {
  const m = menuMas(o);
  const limpiar = () => [...m.childNodes].forEach(n => { if (n.nodeType === 3 && n.textContent === 'null') n.remove(); });
  limpiar();
  new MutationObserver(limpiar).observe(m, { childList: true });
  return m;
}

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
    // acciones ya en la cola (simuladas) de esta pantalla → marcan las filas como hechas
    const cola = new Map();
    if (ctx.servidor) {
      try {
        const r = await ctx.api(`acciones?modulo=${ID}`);
        for (const a of (r.acciones || []).slice().reverse()) cola.set(String(a.objeto), a);
      } catch { /* sin cola: no pasa nada */ }
    }
    const S = crearEstado(ctx, D, cola);
    S.rehacer = () => {
      cont.replaceChildren();
      const ancho = window.matchMedia('(min-width: 1101px)').matches;
      if (ctx.params[0] && !ancho) pintarSolo(cont, ctx, S, ctx.params[0]);
      else {
        if (ctx.params[0] && !S._abierto) {
          S._abierto = true;
          const id = decodeURIComponent(ctx.params[0]);
          const x = S.items.find(y => y.id === id);
          if (x) { S.sel = x.id; S.vista = VISTAS.find(v => v.valor !== 'todo' && v.f(x))?.valor || 'todo'; }
          else S.aviso = 'Ese correo ya no está pendiente o es de un cliente que no llevas.';
        }
        pintar(cont, ctx, S);
      }
      // R15a (A2): al llegar por #/bandeja/<id>, la caja de respuesta queda a la vista y con el foco (solo la primera vez)
      if (ctx.params[0] && !S._cajaVista) {
        S._cajaVista = true;
        let n = 0;
        const llevar = () => {
          const ta = cont.querySelector('#bdj-texto');
          if (ta?.isConnected) { ta.scrollIntoView({ block: 'center' }); try { ta.focus({ preventScroll: true }); } catch { /* sin foco */ } return; }
          if (++n < 15) { setTimeout(llevar, 100); return; }
          // sin caja (ya contestado en la cola, o lo contesta su account): el detalle del correo, arriba y con el foco
          const det = cont.querySelector('[data-bdj-detalle]');
          if (det) { det.setAttribute('tabindex', '-1'); det.scrollIntoView({ block: 'start' }); try { det.focus({ preventScroll: true }); } catch { /* sin foco */ } }
        };
        requestAnimationFrame(llevar);
      }
    };
    S.rehacer();
  },
};

function crearEstado(ctx, D, cola) {
  const cliPorId = new Map(ctx.clientes.map(c => [c.id, c]));
  const correos = (D.correos || []).map(x => ({ ...x, tipo: 'correo', dia: (x.desde || '').slice(0, 10) }));
  const llamadas = (D.llamadas || []).map(x => ({ ...x, tipo: 'llamada', numero: x.id }));
  // el account siempre de la verdad única (aunque el fichero se generase antes de un cambio de asignación)
  for (const x of [...correos, ...llamadas]) {
    const v = x.cliente_id ? ctx.verdad?.(x.cliente_id) : null;
    if (v && 'account' in v) x.account_id = v.account || null;
  }
  const items = [...correos, ...llamadas].map(x => ({
    ...x,
    cli: x.cliente_id ? cliPorId.get(x.cliente_id) : null,
    hecho: cola.get(String(x.numero)) || null,
    grupo: x.cliente_id ? (x.account_id ? ctx.nombre(x.account_id) : 'Sin account') : 'Correos sin cliente',
    account: x.account_id ? ctx.nombre(x.account_id) : (x.cliente_id ? 'Sin account' : 'sin cliente'),
  }));
  const todo = ctx.nivel === 'todo';
  return { D, items, cola, todo, triaje: D.triaje || [], sel: null, filtros: {}, vista: null };
}

// ---------------------------------------------------------------- pantalla
function pintar(cont, ctx, S) {
  const { D } = S;
  const vivos = S.items.filter(x => !x.hecho);
  const paraHoy = vivos.filter(x => !x.auto && !x.viejo);
  const rojo = paraHoy.filter(x => x.gravedad === 'rojo');
  const ambar = paraHoy.filter(x => x.gravedad === 'ambar');
  const quejas = paraHoy.filter(x => x.queja);
  const llam = paraHoy.filter(x => x.tipo === 'llamada');
  const clientesRojo = new Set(rojo.filter(x => x.cliente_id).map(x => x.cliente_id));
  const misClientes = S.todo ? ctx.clientes.length : ctx.clientesVisibles.length;

  // B2/K6: subtítulo corto, con las dos cifras que mandan delante (antes «… · 0 ll…» cortado a 1024).
  ctx.titulo('Bandeja', `${fmt.plural(paraHoy.filter(x => x.tipo === 'correo').length, 'correo', 'correos')} y ${fmt.plural(llam.length, 'llamada', 'llamadas')} por atender${S.todo ? ' · toda la casa' : ''}`);

  // ---- 1 · cifras del día ----
  const ir = v => () => { S.vista = v; S.pts?.elegir?.('lista'); S.repintar?.(true); cont.querySelector('[aria-label="Vista"]')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); };
  const deskOk = !!D.fuentes?.desk, zadOk = !!D.fuentes?.zadarma;
  const ind = ctx.indicador('account.respuesta_al_cliente');
  cont.append(rejilla([
    tile({ icono: 'mail', etiqueta: 'Sin contestar más de 48 h', valor: deskOk ? rojo.filter(x => x.tipo === 'correo').length : null,
      unidad: `en ${clientesRojo.size} clientes`, estado: rojo.length ? 'rojo' : 'verde',
      contexto: 'Bien: todo contestado en menos de 24 h laborables. Rojo a partir de 48 h.', frescura: fres(D.fuentes?.desk, 'Desk'),
      ir: 'Ver cuáles', alPulsar: ir('48') }),
    tile({ icono: 'clock', etiqueta: 'Entre 24 y 48 h', valor: deskOk ? ambar.filter(x => x.tipo === 'correo').length : null, unidad: 'correos',
      estado: ambar.length ? 'ambar' : 'verde', contexto: 'Pasan a rojo si no se contestan hoy', frescura: fres(D.fuentes?.desk, 'Desk'),
      ir: 'Ver cuáles', alPulsar: ir('24') }),
    tile({ icono: 'alert', etiqueta: 'Quejas abiertas',   // §4: el 🔥 es de «En rojo» valor: quejas.length, unidad: 'sin contestar',
      estado: quejas.length ? 'rojo' : 'verde', contexto: 'Señal de baja: se llama el mismo día, antes que escribir', medible: 'medias',
      medibleDetalle: 'Se detectan por el asunto (sin leads, urgente, baja, problema…): puede haber quejas con otro asunto',
      ir: 'Ver quejas', alPulsar: ir('quejas') }),
    tile({ icono: 'phone', etiqueta: 'Llamadas sin devolver', valor: zadOk ? llam.length : null, unidad: llam.length === 1 ? 'llamada' : 'llamadas',   // B1
      estado: llam.some(x => x.gravedad === 'rojo') ? 'rojo' : llam.length ? 'ambar' : 'verde',
      contexto: 'Perdidas de los últimos 5 días laborables sin ninguna llamada contestada después', frescura: fres(D.fuentes?.zadarma, 'Zadarma'),
      ir: 'Ver llamadas', alPulsar: ir('llamadas') }),
    S.todo ? tile({ icono: 'persona', etiqueta: 'Correos sin responsable', valor: S.triaje.filter(t => !S.cola.has(t.numero)).length,
      unidad: 'por repartir', estado: S.triaje.length ? 'ambar' : 'verde',
      contexto: `${S.triaje.filter(t => t.propuesta === 'seguro').length} con el account claro`,
      ir: 'Repartir', alPulsar: () => S.pts?.elegir('triaje') }) : null,
    S.todo ? null : tile({ icono: 'wa', etiqueta: 'WhatsApp uno a uno', valor: null, contexto: 'Llega cuando se conecte WhatsApp Business, no antes del 16-oct',
      medible: 'no', medibleDetalle: 'Mientras, «sin contestar» cuenta solo el correo', alPulsar: () => S.pts?.elegir('whatsapp'), ir: 'Qué falta' }),
  ].filter(Boolean)));

  if (!S.todo && !ctx.clientesVisibles.length) {
    cont.append(avisoParcial('Todavía no tienes clientes asignados en la tabla de asignaciones: la bandeja sale vacía. Las asignaciones las mantiene Mili.', { titulo: 'Sin cartera.' }));
  }

  // ---- 2 · pestañas: lo de cada día primero ----
  const pts = [
    { id: 'lista', texto: 'Correos y llamadas', icono: 'inbox', cuenta: paraHoy.length, cuentaEstado: rojo.length ? 'rojo' : null },
    S.todo ? { id: 'triaje', texto: 'Sin responsable', icono: 'persona', cuenta: S.triaje.filter(t => !S.cola.has(t.numero)).length } : null,
    { id: 'whatsapp', texto: 'WhatsApp', icono: 'wa' },
    { id: 'como', texto: 'De dónde sale', icono: 'info' },
  ].filter(Boolean);
  S.pts = pestanas({ pestanas: pts, clave: 'bandeja.vista', etiqueta: 'Bandeja', activa: S.sel ? 'lista' : undefined, pintar: (id, z) => {
    if (id === 'lista') pintarLista(z, ctx, S, misClientes);
    else if (id === 'triaje') pintarTriaje(z, ctx, S);
    else if (id === 'whatsapp') pintarWhatsapp(z);
    else pintarComo(z, ctx, S);
  } });
  if (S.sel) S.pts.elegir('lista');
  cont.append(S.pts);
  const f2 = pieFase2([ctx.indicador('account.opinion_del_cliente_sobre_sus_leads') || { nombre: 'Opinión del cliente sobre sus leads', medible: 'no', medible_porque: 'no hay campo único «calidad del lead»; se pedirá en la bandeja cuando exista' },
    { nombre: 'WhatsApp uno a uno sin contestar', medible: 'no', medible_porque: 'llega cuando se conecte WhatsApp Business, no antes del 16-oct' }]);
  if (f2) cont.append(f2);
}

// ---------------------------------------------------------------- lista
// 4 vistas a la vista (lo de cada día) y el resto en «Más vistas». Las quejas nunca se esconden en «Más de un mes».
const VISTAS = [
  { valor: 'hoy', texto: 'Para hoy', icono: 'zap', f: x => !x.hecho && !x.auto && !x.viejo, principal: true },
  { valor: 'quejas', texto: 'Quejas', icono: 'alert', f: x => !x.hecho && x.queja, rojo: true, principal: true },
  { valor: 'llamadas', texto: 'Llamadas', icono: 'phone', f: x => !x.hecho && x.tipo === 'llamada', principal: true },
  { valor: 'todo', texto: 'Todo', icono: 'inbox', f: x => !x.hecho, principal: true },
  { valor: '48', texto: 'Más de 48 h', f: x => !x.hecho && x.tipo === 'correo' && !x.auto && !x.viejo && x.gravedad === 'rojo' },
  { valor: '24', texto: 'Entre 24 y 48 h', f: x => !x.hecho && x.tipo === 'correo' && !x.auto && !x.viejo && x.gravedad === 'ambar' },
  { valor: 'auto', texto: 'Avisos automáticos y reenvíos', f: x => !x.hecho && x.auto },
  { valor: 'viejos', texto: 'Más de un mes sin respuesta', f: x => !x.hecho && x.viejo },
  { valor: 'hechos', texto: 'Ya hechos (en cola)', f: x => !!x.hecho },
];

function pintarLista(z, ctx, S, misClientes) {
  const ancho = window.matchMedia('(min-width: 1101px)').matches;
  const izq = h('div', { class: 'panel' });
  const der = h('div', {});
  z.append(ancho ? h('div', { class: 'dos' }, izq, der) : izq);
  const leer = k => { try { return sessionStorage.getItem(k); } catch { return null; } };
  const guardar = (k, v) => { try { sessionStorage.setItem(k, v); } catch { /* nada */ } };
  if (!S.vista) S.vista = leer('ro.bandeja.vista2') || 'hoy';
  if (!VISTAS.some(v => v.valor === S.vista)) S.vista = 'hoy';

  // vistas: 4 chips (lo de cada día) + chip «Más ▾» con el resto
  const vistas = h('div', { class: 'chips-f', role: 'group', 'aria-label': 'Vista' });
  const masVistas = h('div', {});                 // fuera de .chips-f: el menú común no hereda el estilo de chip
  const ponerVista = v => { S.vista = v; guardar('ro.bandeja.vista2', v); repintar(); };
  const pintarVistas = () => {
    const otra = VISTAS.find(v => v.valor === S.vista && !v.principal);
    vistas.replaceChildren(
      ...VISTAS.filter(v => v.principal).map(v => {
        const n = S.items.filter(v.f).length;
        return h('button', { type: 'button', 'data-v': v.valor, 'aria-pressed': String(S.vista === v.valor), on: { click: () => ponerVista(v.valor) } },
          icono(v.icono), v.texto, h('span', { class: `cu${v.rojo && n ? ' rojo' : ''}` }, fmt.num(n)));
      }));
    masVistas.replaceChildren(
      menuMasLimpio({ texto: otra ? otra.texto : 'Más vistas', etiqueta: 'Más vistas', activo: !!otra,
        items: VISTAS.filter(v => !v.principal).map(v => ({ texto: `${v.texto} (${fmt.num(S.items.filter(v.f).length)})`, activo: S.vista === v.valor, alPulsar: () => ponerVista(v.valor) })) }));
  };

  // agrupar (account | día | cliente) y account (solo quien ve toda la casa)
  const agrupar = h('div', { class: 'segm', role: 'group', 'aria-label': 'Agrupar' });
  let modo = leer('ro.bandeja.agrupar') || (S.todo ? 'account' : 'dia');
  const pintarAgrupar = () => agrupar.replaceChildren(...[['account', 'Por account'], ['dia', 'Por día'], ['cliente', 'Por cliente']]
    .filter(([v]) => S.todo || v !== 'account')
    .map(([v, t]) => h('button', { type: 'button', 'aria-pressed': String(modo === v), on: { click: () => { modo = v; guardar('ro.bandeja.agrupar', v); pintarAgrupar(); repintar(); } } }, t)));
  if (!S.todo && modo === 'account') modo = 'dia';
  pintarAgrupar();

  const buscar = h('input', { type: 'search', placeholder: 'Buscar cliente, asunto o número', 'aria-label': 'Buscar en la bandeja' });
  buscar.addEventListener('input', () => repintar());

  let selAcc = null;
  if (S.todo) {
    const cuenta = new Map();
    for (const x of S.items.filter(VISTAS[0].f)) cuenta.set(x.grupo, (cuenta.get(x.grupo) || 0) + 1);
    const accs = [...cuenta.entries()].sort((a, b) => (a[0] === 'Correos sin cliente') - (b[0] === 'Correos sin cliente') || b[1] - a[1]);
    selAcc = h('select', { 'aria-label': 'Account', on: { change: () => { guardar('ro.bandeja.account2', selAcc.value); repintar(); } } },
      h('option', { value: '' }, 'Todos los accounts'), accs.map(([a, n]) => h('option', { value: a }, `${a} (${n})`)));
    selAcc.value = leer('ro.bandeja.account2') || '';
  }

  const lista = h('div', { role: 'list', 'aria-label': 'Correos y llamadas' });
  // (append() escribe «null» si recibe null: todo lo opcional va filtrado — auditoría 30, Bandeja 1)
  izq.append(...[
    h('header', {}, h('div', {}, h('h2', {}, icono('inbox'), 'Correos y llamadas de clientes'),
      h('p', { class: 'sub' }, 'Primero las quejas y después lo que más tiempo lleva esperando. Sin avisos automáticos.')),
      agrupar),
    h('div', { class: 'tabla-ctl' }, vistas, masVistas),
    h('div', { class: 'tabla-ctl' }, buscar, selAcc,
      h('span', { class: 'cuenta fila' }, frescura(fres(S.D.fuentes?.desk, 'Desk')), frescura(fres(S.D.fuentes?.zadarma, 'Zadarma')))),
    S.aviso ? h('div', { class: 'cuerpo' }, avisoParcial(S.aviso, { tipo: 'info' })) : null,
    lista].filter(Boolean));

  const marcarSel = id => lista.querySelectorAll('[data-id]').forEach(b => {
    const on = b.dataset.id === id;
    b.setAttribute('aria-current', String(on));
    b.style.background = on ? 'var(--accent-soft)' : '';
  });
  const elegir = x => {
    S.sel = x.id;
    marcarSel(x.id);
    if (ancho) { der.replaceChildren(detalle(ctx, S, x, () => S.rehacer())); }
    else ctx.navegar(`${ID}/${encodeURIComponent(x.id)}`);
  };

  let limite = 60;
  function repintar() {
    pintarVistas();
    const v = VISTAS.find(w => w.valor === S.vista) || VISTAS[0];
    const acc = selAcc ? selAcc.value : '';
    const q = normal(buscar.value);
    const filas = S.items.filter(v.f)
      .filter(x => !acc || x.grupo === acc)
      .filter(x => !q || normal(`${x.cliente || ''} ${x.asunto || ''} ${x.numero || ''} ${x.numero_oculto || ''} ${x.grupo || ''}`).includes(q))
      .sort((a, b) => (b.queja - a.queja) || (b.horas || 0) - (a.horas || 0));
    // el elemento abierto por la ruta siempre entra en lo que se pinta
    const iSel = filas.findIndex(x => x.id === S.sel);
    if (iSel >= limite) limite = iSel + 1;
    lista.replaceChildren();
    if (!filas.length) {
      const celebrar = ['hoy', '48', 'quejas'].includes(v.valor);
      lista.append(h('div', { class: 'cuerpo' }, vacio({ icono: celebrar ? 'ok' : 'inbox', tono: celebrar && !q ? 'celebrar' : 'neutro',
        titulo: q ? 'Nada coincide con la búsqueda' : celebrar ? 'Bandeja a cero en esta vista' : 'Nada en esta vista',
        texto: q ? 'Prueba con el nombre del cliente o el número del ticket (RO-…).' : v.valor === 'hechos' ? 'Lo que contestes, cierres o marques aparece aquí hasta que el envío salga de verdad.' : `Ningún correo ni llamada de ${S.todo ? 'la casa' : 'tus clientes'} espera respuesta aquí.` })));
      if (ancho) der.replaceChildren(panelVacioDetalle());
      return;
    }
    const clave = x => modo === 'account' ? x.grupo : modo === 'cliente' ? (x.cliente || 'Correos sin cliente') : (x.tipo === 'llamada' ? (x.ultima || '').slice(0, 10) : x.dia);
    const grupos = new Map();
    for (const x of filas.slice(0, limite)) { const k = clave(x); if (!grupos.has(k)) grupos.set(k, []); grupos.get(k).push(x); }
    const orden = [...grupos.entries()];
    const sinCli = k => /sin cliente/i.test(k) ? 1 : 0;
    // «Por día»: del más antiguo al más nuevo (lo que más espera, arriba)
    if (modo === 'dia') orden.sort((a, b) => String(a[0]).localeCompare(String(b[0])));
    else orden.sort((a, b) => sinCli(a[0]) - sinCli(b[0]) || b[1].filter(x => x.gravedad === 'rojo').length - a[1].filter(x => x.gravedad === 'rojo').length || b[1].length - a[1].length);
    for (const [k, xs] of orden) {
      const r = xs.filter(x => x.gravedad === 'rojo').length, a = xs.filter(x => x.gravedad === 'ambar').length;
      const ico = modo === 'dia' ? h('span', { class: 'ico-c s' }, icono('cal'))
        : modo === 'cliente' ? (xs[0].cli ? logoCliente(xs[0].cli) : h('span', { class: 'ico-c s gris' }, icono('alert')))
          : sinCli(k) ? h('span', { class: 'ico-c s gris' }, icono('alert')) : h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(k));
      const nombre = modo === 'dia' ? diaTxt(k) : k;
      const cab = h('div', { class: 'cuerpo fila', role: 'heading', 'aria-level': '3', style: { borderTop: 'var(--borde, thin solid var(--line))' } },
        ico, h('b', {}, nombre), modo === 'cliente' && xs[0].cliente_id ? h('span', { class: 'sub' }, xs[0].account) : null,
        h('span', { class: 'fila', style: { marginLeft: 'auto' } }, r ? chipEstado('rojo', `${r} más de 48 h`) : null, a ? chipEstado('ambar', `${a} de 24-48 h`) : null, !r && !a ? chipEstado('gris', `${xs.length}`) : null));
      const g = h('section', { 'aria-label': nombre }, cab);
      // dentro de cada account o cliente, separados por día (lo más antiguo primero)
      let diaAnt = null;
      let ul = null;
      const xsOrd = modo === 'dia' ? xs : xs.slice().sort((p, q2) => (q2.queja - p.queja) || String(p.tipo === 'llamada' ? p.ultima : p.dia).localeCompare(String(q2.tipo === 'llamada' ? q2.ultima : q2.dia)));
      for (const x of xsOrd) {
        const d = x.tipo === 'llamada' ? (x.ultima || '').slice(0, 10) : x.dia;
        if (!ul || (modo !== 'dia' && d !== diaAnt)) {
          if (modo !== 'dia') g.append(h('p', { class: 'cuerpo titulo-seccion', style: { paddingBottom: '0' } }, diaTxt(d)));
          ul = h('ul', { class: 'primero' }); g.append(ul); diaAnt = d;
        }
        ul.append(fila(x, ctx, S, () => elegir(x)));
      }
      lista.append(g);
    }
    if (filas.length > limite) {
      lista.append(h('div', { class: 'tabla-mas' }, h('button', { type: 'button', class: 'bt', on: { click: () => { limite += 80; repintar(); } } }, icono('mas'), `Ver ${Math.min(80, filas.length - limite)} más (de ${filas.length})`)));
    }
    if (ancho) {
      const actual = filas.find(x => x.id === S.sel) || filas[0];
      S.sel = actual.id;
      marcarSel(actual.id);
      der.replaceChildren(detalle(ctx, S, actual, () => S.rehacer()));
      if (S._abierto && !S._visto) { S._visto = true; lista.querySelector(`[data-id="${CSS.escape(actual.id)}"]`)?.scrollIntoView({ block: 'center' }); }
    }
  }
  S.repintar = repintar;
  repintar();
}

function panelVacioDetalle() {
  return panel({ titulo: 'Detalle', icono: 'mail' }, h('div', { class: 'cuerpo' }, vacio({ icono: 'mail', titulo: 'Elige un correo o una llamada', texto: 'Aquí se contesta con tu firma, se deja nota interna, se asigna o se cierra.' })));
}

/** Una fila de la bandeja: el patrón común «Lo primero hoy» (.primero), entera pulsable. */
function fila(x, ctx, S, alPulsar) {
  const ico = x.queja ? 'alert' : x.tipo === 'llamada' ? 'phone' : x.auto ? 'zap' : 'mail';
  const est = x.hecho ? 'gris' : x.gravedad;
  const titulo = x.tipo === 'llamada'
    ? `${x.cliente ? 'Llamada perdida de ' + x.cliente : 'Número desconocido ' + x.numero_oculto} · ${x.llamadas} ${x.llamadas === 1 ? 'llamada' : 'llamadas'}`
    : x.asunto || '(sin asunto)';
  return h('li', { role: 'listitem', tabindex: '0', 'data-id': x.id, class: x.hecho ? 'hecho' : null, style: { cursor: 'pointer' },
    'aria-label': `${x.cliente || 'Sin cliente'}: ${titulo}. Esperando ${relojTxt(x.horas)}`,
    on: { click: alPulsar, keydown: e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); alPulsar(); } } } },
    h('span', { class: `ico-c s ${est}` }, icono(ico)),
    h('div', {},
      h('div', { class: 'mot' }, titulo),
      h('div', { class: 'det meta-linea' },
        x.cli ? h('span', { class: 'celda-cli' }, logoCliente(x.cli), x.cliente) : h('span', {}, x.cliente || 'Sin cliente'),
        x.tipo === 'llamada' && x.sono_a ? h('span', {}, `sonó a ${nom1(x.sono_a)}`) : null,
        x.asignado && x.tipo === 'correo' ? h('span', {}, icono('persona', { clase: 's' }), nom1(x.asignado)) : x.tipo === 'correo' ? chipEstado('ambar', 'sin responsable') : null)),
    h('div', { class: 'acc' },
      x.hecho ? chipEstado('azul', 'En cola') : h('span', { class: `chip ${x.gravedad || 'gris'}`, title: 'Tiempo esperando, en horas laborables (de lunes a viernes)' }, relojTxt(x.horas)),
      x.queja ? chipEstado('rojo', 'Queja') : x.boletin ? chipEstado('gris', 'Boletín: no cuenta') : x.auto ? chipEstado('gris', 'Automático') : null));
}

// ---------------------------------------------------------------- detalle
/** Número de ticket de Desk: siempre con enlace al ticket (fuera de la lista principal; aquí, en el detalle). */
function numTicket(x) {
  return x.url ? h('a', { href: x.url, target: '_blank', rel: 'noopener', title: 'Abre el ticket en Zoho Desk', style: { display: 'inline-flex', alignItems: 'center', minHeight: 'var(--s-8)' } }, `ticket ${x.numero} ↗`) : h('span', { class: 'dim' }, 'ticket de Desk');
}
function pintarSolo(cont, ctx, S, idRuta) {
  const id = decodeURIComponent(idRuta);
  const x = S.items.find(y => y.id === id);
  cont.append(h('a', { class: 'bt', href: `#/${ID}` }, icono('volver'), 'Volver a la bandeja'));
  if (!x) {
    cont.append(vacio({ icono: 'candado', borde: true, titulo: 'Este elemento no está en tu bandeja', texto: 'O ya no está pendiente, o es de un cliente que no llevas.' }));
    return;
  }
  ctx.titulo('Bandeja', `${x.cliente || 'Sin cliente'} · ${x.tipo === 'correo' ? 'correo sin contestar' : 'llamada sin devolver'}`);
  cont.append(detalle(ctx, S, x, () => ctx.navegar(ID)));
}

function detalle(ctx, S, x, alHacer) {
  const real = ctx.real || ctx.persona;
  const puedeResponder = x.cliente_id ? ctx.ver({ tipo: 'responder_cliente', cliente_id: x.cliente_id }).ok : ctx.persona.puestos.some(p => ['direccion', 'operaciones'].includes(p));
  const cuerpo = h('div', { class: 'cuerpo pila' });
  const p = panel({ titulo: x.tipo === 'correo' ? 'Correo del cliente' : 'Llamada sin devolver', icono: x.tipo === 'correo' ? 'mail' : 'phone',
    acciones: x.url ? h('a', { class: 'bt mini', href: x.url, target: '_blank', rel: 'noopener', title: x.tipo === 'correo' ? 'Abre el ticket en Zoho Desk' : 'Estadísticas de Zadarma (no hay enlace a una llamada concreta): filtra por la fecha' }, icono('ext'), x.tipo === 'correo' ? 'Abrir en Desk' : 'Ver en Zadarma') : null }, cuerpo);
  p.dataset.bdjDetalle = x.id;   // R15a (A2): para llevarlo a la vista al llegar por ruta si no hay caja de respuesta

  // cabecera
  cuerpo.append(h('div', { class: 'fila', style: { flexWrap: 'nowrap', alignItems: 'flex-start' } },
    x.cli ? logoCliente(x.cli) : h('span', { class: `ico-c ${x.gravedad}` }, icono(x.tipo === 'llamada' ? 'phone' : 'mail')),
    h('div', { class: 'pila', style: { minWidth: '0' } }, h('b', {}, x.tipo === 'correo' ? (x.asunto || '(sin asunto)') : (x.cliente ? `${x.cliente} ha llamado ${x.llamadas} ${x.llamadas === 1 ? 'vez' : 'veces'}` : `Número desconocido ${x.numero_oculto}`)),
      h('div', { class: 'meta-linea' },
        h('span', {}, icono('cli'), x.cliente || 'Sin cliente'),
        x.tipo === 'correo' ? numTicket(x) : h('span', { class: 'dim' }, x.numero_oculto),
        h('span', {}, icono('persona'), x.account_id ? `Account: ${x.account}` : x.account)))));
  cuerpo.append(h('div', { class: 'meta-linea' },
    x.hecho ? chipEstado('azul', `En cola: ${etiquetaTipo(x.hecho.tipo)}`) : chipEstado(x.gravedad, `${relojTxt(x.horas)} laborables esperando`),
    x.queja ? chipEstado('rojo', 'Queja: llamar hoy, no contestar solo por correo') : null,
    x.tipo === 'correo' ? h('span', {}, icono('cal'), `Último correo del cliente: ${x.desde ? fDiaRO(x.desde) + ' ' + x.desde.slice(11, 16) : '—'}`) : h('span', {}, icono('cal'), `Primera sin devolver: ${fDiaRO(x.primera)} ${(x.primera || '').slice(11, 16)} · última: ${fDiaRO(x.ultima)} ${(x.ultima || '').slice(11, 16)}`),
    x.tipo === 'correo' ? h('span', {}, icono('persona'), x.asignado ? `En Desk: ${x.asignado}` : 'Sin responsable en Desk') : h('span', {}, icono('phone'), x.intentos_nuestros ? `${x.intentos_nuestros} ${x.intentos_nuestros === 1 ? 'intento nuestro' : 'intentos nuestros'} sin respuesta` : 'Nadie ha intentado devolverla'),
    x.tipo === 'correo' && x.estado_desk ? h('span', {}, icono('flag'), `${x.estado_desk} · ${String(x.departamento || 'Marketing Clientes').replace(/\.$/, '')}`) : null));
  if (x.cli && x.cliente_id) {
    const ficha = MODULOS.find(m => (m.id === 'ficha' || m.id === 'ficha-cliente') && m.estado === 'hecho');
    cuerpo.append(h('div', { class: 'fila' },
      h('a', { class: 'bt mini', href: ficha ? `#/${ficha.id}/${x.cliente_id}` : `#/en-rojo/${x.cliente_id}` }, icono('cli'), 'Ver el cliente')));
  }

  if (x.hecho) {
    cuerpo.append(h('div', { class: 'aviso info', role: 'status' }, icono('ok'), `${etiquetaTipo(x.hecho.tipo)} preparada por ${nombrePersona(ctx, x.hecho.quien)} · ${(x.hecho.hora || x.hecho.creada || '').slice(0, 16)}. Saldrá por Desk cuando se active el envío real.`));
    return p;
  }
  if (ctx.soloLectura) cuerpo.append(avisoParcial('Estás en «ver como»: puedes mirar, pero no contestar ni cambiar nada.', { tipo: 'info' }));

  // acciones
  const zona = h('div', { class: 'pila' });
  const modos = x.tipo === 'correo'
    ? [['responder', 'Contestar', 'send'], ['nota', 'Nota interna', 'editar'], ...(puedeAsignar(ctx) ? [['asignar', 'Asignar', 'persona']] : []), ['cerrar', 'Cerrar', 'ok'], ['no_aplica', 'No aplica', 'cerrar']]
    : [['llamar', 'Devolver la llamada', 'phone'], ['nota', 'Nota interna', 'editar'], ['no_aplica', 'No aplica', 'cerrar']];
  const seg = h('div', { class: 'chips-f', role: 'group', 'aria-label': 'Qué hacer' });
  let modo = x.tipo === 'correo' ? (puedeResponder ? 'responder' : 'nota') : 'llamar';
  const pintarSeg = () => seg.replaceChildren(...modos.map(([v, t, ic]) => h('button', { type: 'button', 'aria-pressed': String(modo === v), on: { click: () => { modo = v; pintarSeg(); pintarZona(); } } }, icono(ic, { clase: 's' }), t)));
  const enviar = async (tipo, texto, vista_previa, herramienta = x.tipo === 'llamada' ? 'zadarma' : 'desk') => {
    const r = await ctx.accion({ herramienta, tipo, objeto: x.numero, cliente_id: x.cliente_id || null, texto, vista_previa });
    const a = { tipo, quien: real.id, texto, hora: new Date().toISOString().replace('T', ' ').slice(0, 16), id: r?.id };
    S.cola.set(String(x.numero), a); x.hecho = a;
    avisoFlotante(`${etiquetaTipo(tipo)} en la cola simulada: no se ha enviado nada`);
    setTimeout(alHacer, 900);
    return `${etiquetaTipo(tipo)} en la cola (simulada). Todavía no sale de verdad.`;
  };
  function pintarZona() {
    zona.replaceChildren();
    if (modo === 'responder') {
      if (!puedeResponder) {
        zona.append(vacio({ icono: 'candado', titulo: 'Contesta su account', texto: 'Al cliente le contestan desde la app su account, las jefas, Operaciones y Dirección. Puedes dejar una nota interna.' }));
        return;
      }
      const saludo = '';
      const ta = h('textarea', { id: 'bdj-texto', rows: '8', 'aria-label': 'Respuesta al cliente', spellcheck: 'true' });
      ta.value = PLANTILLAS[0].cuerpo(saludo);
      const prevCaja = h('div', { class: 'cuerpo pila', 'aria-live': 'polite' });
      const prev = h('div', { class: 'panel' }, prevCaja);
      const pintarPrev = () => prevCaja.replaceChildren(
        h('dl', { class: 'dl' },
          h('dt', {}, 'De'), h('dd', { style: { overflowWrap: 'anywhere', minWidth: '0' } }, 'marketing@rankingonline.com (Marketing Clientes)'),   // B3: parte la línea, no se sale
          h('dt', {}, 'Para'), h('dd', {}, 'el contacto del ticket ', numTicket(x), x.dominio ? ` (@${x.dominio})` : ''),
          h('dt', {}, 'Asunto'), h('dd', {}, `RE: ${x.asunto || ''}`)),
        h('p', { style: { whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' } }, ta.value || '…'),
        firma(ctx, S, real),
        h('div', { class: 'aviso' }, icono('editar', { clase: 's' }), `Nota interna en Desk: «Enviado desde el panel por ${real.nombre}.»`));
      ta.addEventListener('input', pintarPrev);
      pintarPrev();
      zona.append(
        // IA: «Sugerir respuesta» → borrador editable; «Usar» solo lo pasa a la caja. Enviar sigue pidiendo confirmación.
        botonIA(ctx, { ticket: x.numero, destino: ta }),
        h('div', { class: 'fila' }, h('span', { class: 'sub' }, 'Plantilla:'), PLANTILLAS.map(pl => h('button', { type: 'button', class: 'bt mini', on: { click: () => { ta.value = pl.cuerpo(saludo); pintarPrev(); ta.focus(); } } }, pl.texto))),
        h('label', { class: 'campo', for: 'bdj-texto' }, h('span', { class: 'campo-et' }, 'Tu respuesta (tuteo, frases cortas; la firma se pone sola)'), ta),
        h('p', { class: 'titulo-seccion' }, 'Vista previa: así le llega al cliente'), prev,
        x.queja ? avisoParcial('Es una queja: llama hoy y luego confírmalo por escrito.', { titulo: 'Antes de enviar.' }) : '',
        h('div', { class: 'fila' },
          botonConfirmar({ texto: h('span', { class: 'fila' }, icono('send', { clase: 's' }), 'Enviar con mi firma'), pregunta: '¿Enviar? (en el prototipo va a la cola simulada)', confirmar: 'Sí, enviar', soloLectura: ctx.soloLectura,
            alConfirmar: async () => {
              if (!ta.value.trim()) throw new Error('la respuesta está vacía');
              return enviar('responder', ta.value.trim(), { de: 'marketing@rankingonline.com', asunto: `RE: ${x.asunto || ''}`, firma_de: real.id, nota_interna: `Enviado desde el panel por ${real.nombre}.`, ticket: x.numero });
            } }),
          h('span', { class: 'sub' }, 'Prueba: este envío todavía no sale de verdad.')));
    } else if (modo === 'nota') {
      const ta = h('textarea', { id: 'bdj-nota', rows: '4', 'aria-label': 'Nota interna' });
      zona.append(h('label', { class: 'campo', for: 'bdj-nota' }, h('span', { class: 'campo-et' }, x.tipo === 'correo' ? 'Nota interna en el ticket (el cliente no la ve)' : 'Nota interna (queda en el rastro)'), ta),
        h('div', { class: 'fila' }, botonConfirmar({ texto: h('span', { class: 'fila' }, icono('editar', { clase: 's' }), 'Guardar nota'), pregunta: '¿Guardar la nota?', confirmar: 'Sí', soloLectura: ctx.soloLectura,
          alConfirmar: async () => { if (!ta.value.trim()) throw new Error('la nota está vacía'); return enviar('nota_interna', ta.value.trim(), { privada: true, ticket: x.numero }); } })));
    } else if (modo === 'asignar') {
      const gente = (ctx.datos.personas || []).filter(q => (q.puestos || []).some(pu => ['account', 'operaciones', 'direccion', 'jefa_crm', 'jefa_publicidad'].includes(pu)) && q.estado !== 'baja' && !String(q.id).startsWith('setter'));
      const sel = h('select', { id: 'bdj-asig', 'aria-label': 'Asignar a' }, gente.map(q => h('option', { value: q.id, selected: q.id === (x.account_id || x.asignado_id) || null }, q.nombre + (q.id === x.account_id ? ' · account del cliente' : ''))));
      zona.append(h('label', { class: 'campo', for: 'bdj-asig' }, h('span', { class: 'campo-et' }, 'Asignar el ticket en Desk a'), sel),
        h('div', { class: 'fila' }, botonConfirmar({ texto: h('span', { class: 'fila' }, icono('persona', { clase: 's' }), 'Asignar'), pregunta: '¿Asignar?', confirmar: 'Sí, asignar', soloLectura: ctx.soloLectura,
          alConfirmar: () => enviar('asignar', `Asignar a ${sel.selectedOptions[0]?.textContent}`, { a: sel.value, ticket: x.numero }) })));
    } else if (modo === 'cerrar') {
      zona.append(h('p', { class: 'sub' }, 'Cierra el ticket en Desk sin contestar (por ejemplo, ya se resolvió por teléfono). Si lo que falta es un motivo, usa «No aplica».'),
        h('div', { class: 'fila' }, botonConfirmar({ texto: h('span', { class: 'fila' }, icono('ok', { clase: 's' }), 'Cerrar el ticket'), pregunta: '¿Cerrar?', confirmar: 'Sí, cerrar', soloLectura: ctx.soloLectura,
          alConfirmar: () => enviar('cerrar', `Cerrar ${x.numero}`, { estado: 'Cerrado', ticket: x.numero }) })));
    } else if (modo === 'llamar') {
      zona.append(
        h('p', { class: 'sub' }, x.cliente ? `Devuelve la llamada a ${x.cliente} desde tu extensión. El teléfono completo no viaja a la app: búscalo en la ficha del cliente o en Zadarma.` : 'Número que no está en ninguna ficha: puede ser un cliente con otro móvil, un lead o publicidad. Si es de un cliente, apúntalo en su ficha.'),
        h('div', { class: 'fila' },
          h('button', { type: 'button', class: 'bt pri', 'aria-disabled': 'true', title: 'Llamar con un clic (suena tu teléfono y te conecta) llega cuando la app esté en el servidor' }, icono('phone'), 'Llamar con un clic · pronto'),
          botonConfirmar({ texto: h('span', { class: 'fila' }, icono('ok', { clase: 's' }), 'Ya la he devuelto'), pregunta: '¿La has devuelto?', confirmar: 'Sí', soloLectura: ctx.soloLectura,
            alConfirmar: () => enviar('llamada_devuelta', `Devuelta: ${x.cliente || x.numero_oculto}`, { llamadas: x.llamadas }) })));
    } else if (modo === 'no_aplica') {
      const sel = h('select', { id: 'bdj-motivo', 'aria-label': 'Motivo' }, h('option', { value: '' }, 'Elige el motivo…'), MOTIVOS_NO_APLICA.map(m => h('option', { value: m }, m)));
      const det = h('input', { type: 'text', id: 'bdj-motivo-txt', placeholder: 'Detalle (obligatorio si eliges «Otro motivo»)', 'aria-label': 'Detalle del motivo' });
      zona.append(h('label', { class: 'campo', for: 'bdj-motivo' }, h('span', { class: 'campo-et' }, 'Motivo (obligatorio: queda en el historial)'), sel), h('label', { class: 'campo' }, det),
        h('div', { class: 'fila' }, botonConfirmar({ texto: h('span', { class: 'fila' }, icono('cerrar', { clase: 's' }), 'Marcar «No aplica»'), pregunta: '¿Sacarlo de la bandeja?', confirmar: 'Sí', soloLectura: ctx.soloLectura,
          alConfirmar: () => {
            if (!sel.value) throw new Error('falta el motivo');
            if (sel.value === 'Otro motivo' && !det.value.trim()) throw new Error('escribe el motivo');
            return enviar('no_aplica', `${sel.value}${det.value.trim() ? ': ' + det.value.trim() : ''}`, { motivo: sel.value, detalle: det.value.trim() || null });
          } })));
    }
  }
  pintarSeg(); pintarZona();
  cuerpo.append(seg, zona);
  return p;
}

const ETQ = { responder: 'Respuesta', nota_interna: 'Nota interna', asignar: 'Asignación', cerrar: 'Cierre', no_aplica: '«No aplica»', llamada_devuelta: 'Llamada devuelta' };
const etiquetaTipo = t => ETQ[t] || t;
function nombrePersona(ctx, id) {
  if (!id) return '—';
  if (id === (ctx.real || ctx.persona).id) return 'ti';
  return (ctx.datos.personas || []).find(q => q.id === id)?.nombre || id;
}

/** La firma de quien envía, como la pone worker.js (en Desk sale su imagen de firma). */
function firma(ctx, S, persona) {
  const tiene = S.D.firmas?.[persona.id];
  const puesto = (ctx.datos.personas || []).find(q => q.id === persona.id);
  const cargo = (puesto?.puestos || persona.puestos || []).includes('account') ? 'Account Manager'
    : (puesto?.puestos || persona.puestos || []).includes('direccion') ? 'Dirección' : (puesto?.puestos || persona.puestos || []).includes('operaciones') ? 'Operaciones' : 'Ranking Online';
  return h('div', { class: 'pila' },
    h('div', { class: 'fila', style: { flexWrap: 'nowrap' } }, h('span', { class: 'av', 'aria-hidden': 'true' }, iniciales(persona.nombre)),
      h('div', { style: { minWidth: '0' } }, h('b', {}, persona.nombre), h('p', { class: 'sub' }, `${cargo} · Ranking Online · marketing@rankingonline.com`))),
    tiene === false || tiene === undefined
      ? avisoParcial('No tienes firma de imagen en Desk: el correo saldría solo con tu nombre. Pídesela a Agus.')
      : h('p', { class: 'sub' }, 'En el correo va tu firma de Desk (imagen con foto, extensión y logo de RO).'));
}

// ---------------------------------------------------------------- triaje
/** R16: «Asignar a…» (desk/asignar) solo para dirección, operaciones y proyectos; el servidor da 403 al resto. */
const PUESTOS_ASIGNAR = ['direccion', 'operaciones', 'proyectos'];
function puedeAsignar(ctx) { return (ctx.persona?.puestos || []).some(p => PUESTOS_ASIGNAR.includes(p)); }

function pintarTriaje(z, ctx, S) {
  const pend = S.triaje.filter(t => !S.cola.has(t.numero));
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
            alConfirmar: async () => { await ctx.accion({ herramienta: 'desk', tipo: 'asignar', objeto: t.numero, cliente_id: t.cliente_id || null, texto: `Asignar a ${t.agente_propuesto}`, vista_previa: { a: t.agente_propuesto_id, ticket: t.numero, origen: 'triaje' } }); S.cola.set(t.numero, { tipo: 'asignar' }); setTimeout(pintarL, 900); return 'En la cola simulada'; } }) : null,
          botonConfirmar({ texto: 'Cerrar sin contestar', pregunta: '¿Cerrar (antiguo o ya resuelto)?', confirmar: 'Sí', mini: true, soloLectura: ctx.soloLectura,
            alConfirmar: async () => { await ctx.accion({ herramienta: 'desk', tipo: 'cerrar', objeto: t.numero, cliente_id: t.cliente_id || null, texto: `Cerrar ${t.numero} desde el reparto (sin responsable, ${t.dias} días)`, vista_previa: { estado: 'Cerrado', ticket: t.numero } }); S.cola.set(t.numero, { tipo: 'cerrar' }); setTimeout(pintarL, 900); return 'En la cola simulada'; } }))));
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
  if (ruido.length) z.append((panel({ titulo: 'Fuera de la bandeja', icono: 'filtro', sub: 'No son correos de clientes' },
    h('div', { class: 'cuerpo' }, h('ul', { class: 'lista-i' }, ruido.map(([k, n]) => h('li', {}, h('span', { class: 'ico-c s gris' }, icono('filtro')), h('span', { class: 't' }, NOMBRE_RUIDO[k] || (k.charAt(0).toUpperCase() + k.slice(1))), h('span', { class: 'x' }, fmt.num(n)))))))));
}
