// modulos/asistente_ia.js · N3 «Asistente IA» (2-oct-2026). Ruta #/asistente-ia y #/asistente-ia/<cliente>.
// Dos pestañas: «Qué haría hoy» (copiloto del account por cliente) y «Borradores de correo» (Desk).
// Todo sale de /api/ia/* (ia.py): el servidor arma el contexto con lo que ve esta persona y deja rastro.
// Nada se envía. Hoy, sin clave de Anthropic, se sirven los precalculados del 2-oct con su aviso.
// Los mismos componentes (modulos/ia_componentes.js) son los que usan la Bandeja, la ficha y Mi día.

import { h, fmt, icono, tile, tiles, chipEstado, chipsFiltro, pestanas, vacio, panel, logoCliente, iniciales, esqueleto } from '../componentes.js';
import { iaDe, botonIA, panelCopiloto, estilos as estilosIA } from './ia_componentes.js';

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

// Diseño (auditoría 30, N6): sin hoja propia. Maquetación en línea con tokens; letra y color, de las clases comunes.
const DOS = { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-4)', alignItems: 'flex-start' };
/** Fila de la lista (cliente o correo): toda la fila es el botón; la elegida, en azul suave con filete a la izquierda. */
const filaLista = sel => ({ display: 'grid', gridTemplateColumns: '36px minmax(0, 1fr) auto', gap: 'var(--s-1) var(--s-3)', alignItems: 'center', width: '100%', textAlign: 'left',
  padding: 'var(--s-3) var(--s-3) var(--s-3) var(--s-2)', border: '0', borderBottom: 'var(--borde-suave)', borderLeft: `4px solid ${sel ? 'var(--accent)' : 'transparent'}`,
  background: sel ? 'var(--accent-soft)' : 'transparent', color: 'inherit', font: 'inherit', cursor: 'pointer', minHeight: '44px' });
const marcar = (botones, id) => botones.forEach(b => { const s = b.dataset.id === id; b.setAttribute('aria-current', String(s)); Object.assign(b.style, filaLista(s)); });
const T = { font: 'var(--t-h3)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' };
const D = { gridColumn: '2 / 4', font: 'var(--t-meta)', color: 'var(--dim)', display: '-webkit-box', WebkitLineClamp: '2', WebkitBoxOrient: 'vertical', overflow: 'hidden' };
const CAB = { display: 'grid', gap: 'var(--s-1)', paddingBottom: 'var(--s-3)', borderBottom: 'var(--borde-suave)', marginBottom: 'var(--s-3)' };

export default {
  id: 'asistente-ia',
  titulo: 'Asistente IA',
  grupo: 'Hoy',
  puestos_que_lo_ven: {
    direccion: 'todo', operaciones: 'todo', proyectos: 'todo',
    jefa_publicidad: 'todo', jefa_seo: 'todo', jefa_crm: 'todo', account: 'suyo',
  },

  async render(raiz, ctx) {
    vigilarCortes(raiz);
    estilosIA();
    document.getElementById('asi-estilos')?.remove();   // hoja de antes de la guía 30
    ctx.titulo('Asistente IA', 'Qué haría hoy con cada cliente y borradores de los correos más urgentes · lo revisas tú, no se envía nada');
    raiz.replaceChildren(esqueleto({ tarjetas: 3, lineas: 4 }));
    if (!ctx.servidor) {
      raiz.replaceChildren(vacio({ icono: 'spark', tono: 'aviso', titulo: 'La IA necesita el servidor', texto: 'La IA solo funciona con la app servida desde el servidor, que arma el contexto con tus permisos. Avisa a Tomás.' }));
      return;
    }
    let L;
    try { L = await iaDe(ctx).lista(); }
    catch (e) { raiz.replaceChildren(vacio({ icono: 'candado', titulo: 'No disponible', texto: e.message })); return; }

    const est = L.estado || {};
    const quejas = L.borradores.filter(b => b.queja).length;
    const rojos = L.copiloto.filter(c => c.color === 'rojo').length;
    const huecos = L.borradores.reduce((s, b) => s + (b.huecos || 0), 0);
    const cab = tiles([
      tile({ icono: 'spark', etiqueta: 'La IA', valor: est.conectada ? 'Conectada' : 'Sin conectar', estado: est.conectada ? 'verde' : 'ambar',
        contexto: est.conectada ? `Modelo ${est.modelo}: genera al momento` : 'Se ven los borradores precalculados del 2-oct; falta la clave de Anthropic (Tomás)' }),
      tile({ icono: 'medidor', etiqueta: 'Clientes con propuesta', valor: L.copiloto.length, estado: rojos ? 'rojo' : 'verde',
        contexto: `${rojos} en crítico · ${L.copiloto.filter(c => c.color === 'ambar').length} en atención (la gravedad de la verdad única)`, alPulsar: () => tabs.elegir('copiloto'), ir: 'Ver propuestas' }),
      tile({ icono: 'mail', etiqueta: 'Borradores listos', valor: L.borradores.length, estado: quejas ? 'rojo' : 'gris',
        contexto: `${quejas} de quejas · ${huecos} datos por completar antes de enviar`, alPulsar: () => tabs.elegir('borradores'), ir: 'Ver borradores' }),
    ]);

    const elegido = ctx.params[0] ? decodeURIComponent(ctx.params[0]) : null;
    const tabs = pestanas({
      clave: 'asistente-ia', activa: elegido ? 'copiloto' : (L.copiloto.length ? 'copiloto' : 'borradores'),
      pestanas: [
        { id: 'copiloto', texto: 'Qué haría hoy', icono: 'medidor', cuenta: rojos, cuentaEstado: 'rojo' },
        { id: 'borradores', texto: 'Borradores de correo', icono: 'mail', cuenta: quejas, cuentaEstado: 'rojo' },
      ],
      pintar: (id, z) => id === 'copiloto' ? pintarCopiloto(z, ctx, L, elegido) : pintarBorradores(z, ctx, L),
    });
    if (elegido) tabs.elegir('copiloto');
    raiz.replaceChildren(cab, tabs,
      h('p', { class: 'sub', style: { marginTop: 'var(--s-4)' } }, icono('info', { clase: 's' }),
        ` ${L.generado ? `Propuestas generadas el ${fDiaHoraRO(String(L.generado).slice(0, 16))}. ` : ''}Cada propuesta y cada borrador quedan en el rastro. Solo ves los clientes que puedes abrir.`));
  },
};

// V2-B (A1): el color es la gravedad de la verdad única y se nombra igual que en En rojo y la ficha.
const COLOR = { rojo: ['rojo', 'Crítico', 0], ambar: ['ambar', 'Atención', 1], verde: ['verde', 'Bien', 2] };

function pintarCopiloto(z, ctx, L, elegido) {
  if (!L.copiloto.length) {
    z.append(vacio({ icono: 'spark', titulo: 'Sin propuestas para tus clientes', texto: L.estado?.conectada ? 'Abre un cliente en su ficha y pide «Qué haría hoy».' : 'Hoy hay propuestas precalculadas para los 11 clientes críticos y la cartera de Lucía. Con la clave de Anthropic, salen para cualquiera al momento.', quien: L.estado?.conectada ? null : 'Tomás' }));
    return;
  }
  const porId = Object.fromEntries((ctx.clientes || []).map(c => [c.id, c]));
  let actual = L.copiloto.some(c => c.cliente_id === elegido) ? elegido : L.copiloto[0].cliente_id;
  const det = h('div');
  const botones = [];
  const filtro = chipsFiltro({ clave: 'asi-color', etiqueta: 'Gravedad', opciones: [
    { valor: '', texto: 'Todos', cuenta: L.copiloto.length },
    ...['rojo', 'ambar', 'verde'].map(k => ({ valor: k, texto: COLOR[k][1], cuenta: L.copiloto.filter(c => c.color === k).length, cuentaEstado: k === 'rojo' ? 'rojo' : '' })).filter(o => o.cuenta),
  ], alCambiar: () => pintarLista() });
  const lista = h('nav', { 'aria-label': 'Clientes', style: { display: 'grid' } });
  function pintarLista() {
    const f = filtro.valor?.() || '';
    botones.length = 0;
    lista.replaceChildren(...L.copiloto.filter(c => !f || c.color === f).map(c => {
      const [cls, txt] = COLOR[c.color] || ['gris', 'Sin color'];
      const b = h('button', { type: 'button', 'aria-current': String(c.cliente_id === actual), style: filaLista(c.cliente_id === actual), on: { click: () => elegir(c.cliente_id) } },
        logoCliente({ nombre: c.nombre, logo: porId[c.cliente_id]?.logo }),
        h('span', { style: T }, c.nombre || c.cliente_id), chipEstado(cls, txt),
        h('span', { style: D }, `${c.account ? c.account + ' · ' : ''}${c.primera || ''}`));
      b.dataset.id = c.cliente_id;
      botones.push(b);
      return b;
    }));
  }
  function elegir(id) {
    actual = id;
    marcar(botones, id);
    history.replaceState(null, '', `#/asistente-ia/${encodeURIComponent(id)}`);
    const c = L.copiloto.find(x => x.cliente_id === id);
    det.replaceChildren(
      h('div', { style: CAB }, h('h3', { style: { font: 'var(--t-h2)' } }, c?.nombre || id),
        h('div', { class: 'meta-linea' }, c?.account ? h('span', {}, icono('persona', { clase: 's' }), ` ${c.account}`) : null,
          ctx.veModulo('ficha') ? h('a', { class: 'bt mini', href: `#/ficha/${encodeURIComponent(id)}/resumen` }, icono('cli', { clase: 's' }), 'Abrir la ficha') : null,
          ctx.veModulo('bandeja') ? h('a', { class: 'bt mini', href: '#/bandeja' }, icono('inbox', { clase: 's' }), 'Sus correos en la Bandeja') : null)),
      panelCopiloto(ctx, id));
    if (window.matchMedia('(max-width: 900px)').matches) det.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  pintarLista();
  det.style.cssText = 'flex: 999 1 480px; min-width: 0';
  z.append(h('div', { style: DOS }, Object.assign(panel({ titulo: 'Clientes', icono: 'cli', sub: 'Crítico arriba' }, h('div', { style: { padding: 'var(--s-3)', borderBottom: 'var(--borde-suave)' } }, filtro), lista), { style: 'flex: 1 1 300px; max-width: 360px; min-width: 0' }), det));
  elegir(actual);
}

function pintarBorradores(z, ctx, L) {
  if (!L.borradores.length) {
    z.append(vacio({ icono: 'mail', tono: 'celebrar', titulo: 'Ningún correo tuyo con borrador', texto: 'Hoy hay borradores para los 40 correos más urgentes de la Bandeja. Si no ves ninguno, es que no son de tu cartera.' }));
    return;
  }
  let actual = L.borradores[0].ticket;
  const det = h('div');
  const botones = [];
  const lista = h('nav', { 'aria-label': 'Correos', style: { display: 'grid' } }, L.borradores.map(b => {
    const bt = h('button', { type: 'button', 'aria-current': String(b.ticket === actual), style: filaLista(b.ticket === actual), on: { click: () => elegir(b.ticket) } },
      h('span', { class: `ico-c ${b.queja ? 'rojo' : (b.dias || 0) > 2 ? 'ambar' : 'gris'}`, 'aria-hidden': 'true' }, icono(b.queja ? 'alert' : 'mail')),
      h('span', { style: T }, b.cliente || b.ticket), b.queja ? chipEstado('rojo', 'Queja') : chipEstado((b.dias || 0) > 2 ? 'ambar' : 'gris', `${b.dias ?? '—'} d`),
      h('span', { style: D }, b.asunto || 'sin asunto'));
    bt.dataset.id = b.ticket;
    botones.push(bt);
    return bt;
  }));
  function elegir(t) {
    actual = t;
    marcar(botones, t);
    const b = L.borradores.find(x => x.ticket === t);
    det.replaceChildren(panel({ titulo: 'Borrador', icono: 'spark' }, h('div', { class: 'cuerpo' },
      h('div', { style: CAB }, h('h3', { style: { font: 'var(--t-h2)' } }, b.asunto || b.ticket),
        h('div', { class: 'meta-linea' },
          h('span', {}, icono('cli', { clase: 's' }), ` ${b.cliente || 'sin cliente'}`),
          b.account ? h('span', {}, icono('persona', { clase: 's' }), ` ${b.account}`) : null,
          h('span', {}, icono('clock', { clase: 's' }), ` ${b.dias ?? '—'} días laborables sin contestar`),
          b.url ? h('a', { class: 'bt mini', href: b.url, target: '_blank', rel: 'noopener noreferrer' }, icono('ext', { clase: 's' }), 'Abrir en Desk') : null)),
      botonIA(ctx, { ticket: b.ticket, abierto: true }))));
    if (window.matchMedia('(max-width: 900px)').matches) det.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  det.style.cssText = 'flex: 999 1 480px; min-width: 0';
  z.append(h('div', { style: DOS }, Object.assign(panel({ titulo: 'Correos', icono: 'inbox', sub: 'Quejas arriba; luego los que más esperan' }, lista), { style: 'flex: 1 1 300px; max-width: 360px; min-width: 0' }), det));
  elegir(actual);
}
