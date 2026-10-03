// modulos/envios.js · Envíos verificados (3-oct-2026). Encargo de Tomás: «cualquier correo que se envíe, asegurarnos de que se
// está enviando bien; también desde la parte de atrás, para asegurarnos de que el sistema nunca está fallando».
// Lo ven dirección, operaciones y el técnico (Agus). Datos: GET /api/envios (envios.py, en vivo de la base de la app):
// cada envío con su estado (simulado → pendiente → enviado → confirmado | fallido | rebotado), la hora de cada paso, el canal,
// el destinatario que resolvió el servidor, quién lo pidió y sus avisos. El texto solo llega si además puede abrir ese cliente.
// «Reintentar»: POST /api/envios/reintentar { id } — SIMULADO hasta que Tomás active los envíos (deja el paso y el rastro).
// El navegador nunca fija estado, destinatario ni remitente.

import { fmt, tile, tiles, chipsFiltro, chipEstado, vacio, panel, avisoParcial, avisoFlotante, icono } from '../componentes.js';
import { h } from './personas_comun.js';
import { llevarA } from './_ir.js';

const ESTADO = {
  fallido: ['rojo', 'Fallido'], rebotado: ['rojo', 'Rebotado'], pendiente: ['ambar', 'En cola'], enviado: ['ambar', 'Enviado · comprobando'],
  simulado: ['gris', 'Simulado'], confirmado: ['verde', 'Confirmado'],
};
const ORDEN = ['fallido', 'rebotado', 'pendiente', 'enviado', 'simulado', 'confirmado'];
const EVENTO = {
  creado: 'Pedido (simulado: no sale nada)', en_cola: 'En cola para salir', enviado: 'La herramienta lo acepta', ya_estaba: 'Ya estaba en el hilo: no se duplica',
  error_envio: 'Error al mandarlo', verificado: 'Comprobado en el hilo', rebote: 'Rebote detectado', no_aparece: 'No aparece en el hilo',
  distinto: 'En el hilo con otros datos', apagado: 'Canal sin envío real', aviso: 'Aviso a quien lo mandó y a Agus',
  reintento_simulado: 'Reintento simulado', reintento_pedido: 'Reintento pedido',
};
const ICONO_CANAL = { desk: 'mail', whatsapp: 'wa', ghl: 'base' };
const FILTROS = {
  problemas: x => x.estado === 'fallido' || x.estado === 'rebotado',
  curso: x => x.estado === 'pendiente' || x.estado === 'enviado',
  confirmado: x => x.estado === 'confirmado',
  simulado: x => x.estado === 'simulado',
  '': () => true,
};

const cuando = t => (t ? `${fmt.fecha(t)} ${new Date(t).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Madrid' })}` : '—');

function cartel(D) {
  const reales = D.modo?.reales;
  return h('div', { class: `aviso${reales ? ' info' : ''}`, role: 'note', 'data-cartel': 'envios', style: { padding: '16px 20px', alignItems: 'center', gap: '16px' } },
    h('span', { class: 'ico', 'aria-hidden': 'true' }, icono(reales ? 'send' : 'escudo')),
    h('div', {},
      h('b', { style: { font: 'var(--t-h2)', display: 'block' } }, reales ? D.modo.texto : 'Envíos en simulación · los activa Tomás'),
      h('p', { style: { margin: '4px 0 0', font: 'var(--t-cuerpo)', maxWidth: '80ch' } },
        reales ? 'Cada envío sale, se comprueba en la herramienta al momento y, si falla, avisa a quien lo mandó y a Agus.'
          : 'Hoy no sale nada de la app: cada correo, WhatsApp o mensaje de GHL queda aquí como «simulado», con quién lo pidió y a quién iría. El día que Tomás los active, cada uno se comprobará en la herramienta (que está en el hilo, con el texto y el destinatario correctos) y, si falla o rebota, avisará a quien lo mandó y a Agus.')));
}

function tilesResumen(D) {
  const t7 = D.tasas?.['7'] || {};
  const t30 = D.tasas?.['30'] || {};
  const malos = (D.por_estado?.fallido || 0) + (D.por_estado?.rebotado || 0);
  const s = D.salud;
  const colorSalud = s ? ({ verde: 'verde', ambar: 'ambar', rojo: 'rojo' }[s.color] || '') : '';
  const pctTile = (t, dias) => tile({ icono: 'ok', etiqueta: `Confirmados · ${dias} días`, valor: t.pct === null || t.pct === undefined ? null : `${fmt.num(t.pct, 1)} %`,
    unidad: t.terminados ? `${t.confirmados} de ${t.terminados}` : '', estado: t.pct === null || t.pct === undefined ? '' : t.pct >= 98 ? 'verde' : t.pct >= 90 ? 'ambar' : 'rojo',
    sinDato: D.modo?.reales ? 'ningún envío terminado' : 'aún no sale ningún envío real',
    contexto: `${fmt.plural(t.simulados || 0, 'simulado')} en ${dias} días${t.en_curso ? ` · ${t.en_curso} en curso` : ''}`, medible: D.modo?.reales ? 'hoy' : 'no',
    medibleDetalle: D.modo?.reales ? null : 'Se medirá cuando Tomás active los envíos reales' });
  return tiles([
    pctTile(t7, 7), pctTile(t30, 30),
    tile({ icono: 'alert', etiqueta: 'Fallidos y rebotados', valor: malos, unidad: malos === 1 ? 'envío' : 'envíos', estado: malos ? 'rojo' : 'verde',
      contexto: malos ? 'Arriba en la lista, con el motivo en llano' : 'Ninguno: nada que mirar' }),
    tile({ icono: 'send', etiqueta: 'Envío de correos (Desk)', valor: s ? s.titular : null, estado: colorSalud, sinDato: 'falta la prueba de conexiones',
      contexto: s ? `Probado ${cuando(s.ultima_prueba ? s.ultima_prueba.replace(' ', 'T') : null)}` : 'Llave de escritura, departamento, dirección de envío y firmas',
      href: '#/conexiones/envio_correos', ir: 'Ver la conexión' }),
  ]);
}

function pasosDe(x) {
  return h('ol', { class: 'tiempo', style: { margin: '8px 0 0' } }, (x.pasos || []).map(p =>
    h('li', { class: ESTADO[p.estado]?.[0] || '' },
      h('div', { class: 'f' }, cuando(p.hora)),
      h('div', { class: 't' }, `${EVENTO[p.evento] || p.evento} · ${ESTADO[p.estado]?.[1] || p.estado}${p.intento ? ` · intento ${p.intento + 1}` : ''}`),
      p.motivo ? h('div', { class: 'd' }, p.motivo) : null)));
}

function tarjeta(x, ctx, D, alCambiar) {
  const [color, texto] = ESTADO[x.estado] || ['gris', x.estado];
  const estado = h('span', { class: 'sub', role: 'status', 'aria-live': 'polite' });
  const puede = x.puede_reintentar && (x.estado === 'simulado' || (x.estado === 'fallido' && (x.seguro_reintentar || !D.modo?.reales)));
  const bt = puede ? h('button', { type: 'button', class: 'bt mini', 'data-atajo': 'e', title: D.modo?.reales ? 'Lo vuelve a mandar, mirando antes si ya llegó (nunca duplica)' : 'Simulado: deja constancia, no sale nada' },
    icono('recargar'), D.modo?.reales ? 'Reintentar' : 'Reintentar (simulado)') : null;
  bt?.addEventListener('click', async () => {
    if (ctx.soloLectura) { estado.textContent = 'Estás en «ver como»: solo lectura.'; return; }
    bt.disabled = true;
    estado.textContent = 'Pidiendo el reintento…';
    try {
      const r = await ctx.api('envios/reintentar', { metodo: 'POST', cuerpo: { id: x.id } });
      estado.textContent = r.mensaje || 'Hecho.';
      avisoFlotante(r.mensaje || 'Hecho.', { icono: r.simulado ? 'escudo' : 'ok' });   // queda a la vista aunque la lista se repinte
      alCambiar?.();
    } catch (e) {
      bt.disabled = false;
      estado.textContent = `No se pudo: ${e.message}`;
    }
  });
  return h('article', { class: `pm-tarjeta ${color}`, 'data-envio': String(x.id), 'data-fila': '', style: { minWidth: 0, overflowWrap: 'anywhere' } },
    h('div', { class: 'pm-cab' }, h('span', { class: `ico-c ${color}` }, icono(ICONO_CANAL[x.canal] || 'send')),
      h('span', { class: 't' }, h('b', {}, x.destinatario?.nombre || '—'),
        h('span', {}, `${x.canal_nombre}${x.cliente ? ' · ' + x.cliente : ''} · pedido por ${x.quien_alias} ${fmt.hace(x.creado)}`)),
      h('span', { class: 'der' }, chipEstado(color, texto))),
    x.motivo ? h('p', { style: { margin: 0, font: 'var(--t-cuerpo)', maxWidth: '72ch' } }, x.motivo) : null,
    h('dl', { class: 'pm-kv' },
      h('dt', {}, 'Envío'), h('dd', {}, `n.º ${x.id} · ${x.modo === 'simulado' ? 'simulado' : x.modo}`),
      h('dt', {}, 'Desde'), h('dd', {}, `${texto} desde ${cuando(x.desde)}`),
      x.intentos ? [h('dt', {}, 'Intentos'), h('dd', {}, String(x.intentos))] : null,
      x.asunto ? [h('dt', {}, 'Asunto'), h('dd', {}, x.asunto)] : null,
      x.avisado ? [h('dt', {}, 'Aviso'), h('dd', {}, `Avisados ${x.quien_alias} y Agus`)] : null),
    h('details', { class: 'que-es' }, h('summary', {}, `Pasos (${(x.pasos || []).length}) y mensaje`),
      pasosDe(x),
      x.texto_oculto ? h('p', { class: 'sub' }, 'El texto no se enseña: no llevas este cliente.')
        : x.texto ? h('p', { style: { whiteSpace: 'pre-wrap', margin: '8px 0 0', font: 'var(--t-cuerpo)', maxWidth: '72ch' } }, x.texto) : null),
    bt ? h('div', { class: 'fila', style: { alignItems: 'center', gap: '12px', flexWrap: 'wrap' } }, bt, estado) : null);
}

async function cargar(ctx) {
  try { return await ctx.api('envios'); } catch (e) { return { error: e.message, status: e.status }; }
}

function cuerpo(ctx, D, repintar, objetivo) {
  const L = D.envios || [];
  const n = f => L.filter(FILTROS[f]).length;
  const caja = h('div', { class: 'pm-conex' });
  let filtro = '';
  const pintar = () => {
    const ls = L.filter(FILTROS[filtro] || FILTROS['']).sort((a, b) => ORDEN.indexOf(a.estado) - ORDEN.indexOf(b.estado) || String(b.creado).localeCompare(String(a.creado)));
    caja.replaceChildren(...(ls.length ? ls.map(x => tarjeta(x, ctx, D, repintar))
      : [vacio({ icono: filtro === 'problemas' ? 'ok' : 'send', tono: filtro === 'problemas' ? 'celebrar' : 'neutro',
        titulo: filtro === 'problemas' ? 'Ningún envío fallido ni rebotado' : 'Ningún envío aquí',
        texto: L.length ? 'Cambia el filtro para ver el resto.' : 'Cuando alguien conteste un correo, un WhatsApp o un contacto de GHL desde la app, saldrá aquí.' })]));
  };
  const chips = chipsFiltro({ clave: 'envios.filtro', etiqueta: 'Ver', valor: n('problemas') ? 'problemas' : '', opciones: [
    { valor: 'problemas', texto: 'Fallidos primero', icono: 'alert', cuenta: n('problemas'), cuentaEstado: 'rojo' },
    { valor: '', texto: 'Todos', cuenta: L.length },
    { valor: 'curso', texto: 'En curso', icono: 'clock', cuenta: n('curso') },
    { valor: 'confirmado', texto: 'Confirmados', icono: 'ok', cuenta: n('confirmado') },
    { valor: 'simulado', texto: 'Simulados', icono: 'escudo', cuenta: n('simulado') }],
  alCambiar: v => { filtro = v; pintar(); } });
  filtro = chips.valor();
  const obj = objetivo ? L.find(x => String(x.id) === String(objetivo)) : null;
  if (obj && !(FILTROS[filtro] || FILTROS[''])(obj)) filtro = '';
  pintar();
  return [
    cartel(D),
    tilesResumen(D),
    panel({ titulo: 'Cola de envíos', icono: 'send',
      sub: `${D.ve_todos ? 'Los de todo el equipo' : 'Los tuyos'} · lo que falla, arriba y con el motivo en llano. Cada paso lleva su hora.`,
      acciones: h('button', { type: 'button', class: 'bt mini', on: { click: () => repintar() } }, icono('recargar'), 'Actualizar') },
    h('div', { class: 'pm-pad' }, chips), caja),
    panel({ titulo: 'Cómo se comprueba cada envío', icono: 'escudo', sub: 'Lo hace el servidor, al momento y en cada vuelta de la tubería. Nada sale hasta que Tomás lo active.' },
      h('ol', { class: 'tiempo', style: { margin: '0', padding: '12px var(--relleno)' } },
        [['Se pide', 'Alguien contesta desde la app. El servidor pone el destinatario (el contacto del ticket, el grupo o el contacto del CRM) y la dirección de envío: nunca las escribe el navegador.'],
          ['Sale', 'Una clave única por envío: si algo se corta a medias, antes de reintentar se mira si ya llegó. Nunca se manda dos veces.'],
          ['Se comprueba', 'Se relee en la herramienta que está en el hilo con el texto y el destinatario correctos. Los rebotes se siguen mirando 48 h.'],
          ['Si falla', 'Un reintento solo si es seguro (fallo de red). Si no, «fallido» con el motivo y aviso a quien lo mandó y a Agus en #avisos-dirección.'],
          ['Canario', D.canario?.texto || 'Un correo de prueba diario a un buzón interno. Solo se enciende con el sí de Tomás.']]
          .map(([t, d]) => h('li', {}, h('div', { class: 't' }, t), h('div', { class: 'd' }, d))))),
    D.solo_lectura ? avisoParcial('Estás en «ver como»: ves lo que verían las dos personas y no se puede reintentar.', { tipo: 'info' }) : null,
  ].filter(Boolean);
}

export default {
  id: 'envios',
  titulo: 'Envíos',
  grupo: 'Sistema',
  puestos_que_lo_ven: { direccion: 'todo', operaciones: 'todo', tecnico_altas: 'todo' },
  async render(cont, ctx) {
    ctx.titulo?.('Envíos', 'Cada correo, WhatsApp o mensaje de GHL que sale de la app: si salió, si llegó y quién lo pidió');
    const objetivo = ctx.params?.[0] || null;
    const raiz = h('div', { class: 'envios' });
    cont.append(raiz);
    const pintar = async (obj = null) => {
      const D = await cargar(ctx);
      if (D.error) {
        raiz.replaceChildren(vacio({ icono: 'send', tono: 'aviso', titulo: 'No se pudo leer la cola de envíos', texto: D.error, quien: 'Agus' }));
        return;
      }
      raiz.replaceChildren(...cuerpo(ctx, D, () => pintar(), obj));
      if (obj) {
        if ((D.envios || []).some(x => String(x.id) === String(obj))) llevarA(raiz, r => r.querySelector(`[data-envio="${CSS.escape(String(obj))}"]`));
        else raiz.prepend(avisoParcial('Ese envío no está en tu lista (no es tuyo o ya no existe).', { titulo: 'No lo encuentro.' }));
      }
    };
    await pintar(objetivo);
  },
};
