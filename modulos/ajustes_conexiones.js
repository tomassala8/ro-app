// modulos/ajustes_conexiones.js · M22 Ajustes › Conexiones (N11, 2-oct-2026: «sin fallos de conexión por API»).
// Lo ven dirección, operaciones y el técnico (Agus). Datos: data/conexiones/salud.json, que escribe
// despliegue/salud_conexiones.py al EMPEZAR cada vuelta de la tubería: una lectura barata por conexión (26), su tiempo,
// la caducidad si se sabe, desde cuándo está en su color, el último OK, el error en llano y QUÉ HACER con su dueño.
// «Probar ahora» pide SOLO la prueba de conexiones (POST /api/recarga { modo: 'conexiones' }, solo lectura de las
// herramientas; R15b): igual para Agus, Mili y Tomás. La recarga entera sigue en su botón propio («Actualizar ahora», arriba,
// solo Mili y Tomás). Esta pantalla espera al resultado nuevo y lo pinta.
// Se usa en dos sitios: la pestaña «Conexiones y caducidad» de Ajustes (vistaConexiones) y, para el técnico, que no ve
// Ajustes, como módulo propio (export default) cuando el coordinador lo registre en indice.js.

import { fmt, tile, tiles, chipsFiltro, chipEstado, vacio, panel, avisoParcial, icono, listaConIcono, limpiaTexto } from '../componentes.js';
import { h, estilosLocales } from './personas_comun.js';
import { llevarA } from './_ir.js';

// V2 (B-M2, B-M3, A-M7) · UN dueño por conexión y en español llano. Lo leen Conexiones y Captación (import), nunca otro texto.
// Las claves las pega Tomás (solo él tiene las cuentas de administrador); Agus comprueba después que llegan los datos.
const DUENOS = {
  google_ads: { hace: 'Tomás', comprueba: 'Agus', que: 'pegar la clave de Google Ads' },
  windsor: { hace: 'Tomás', comprueba: 'Agus', que: 'pegar la clave de Windsor (trae Google Ads y TikTok)' },
  seranking: { hace: 'Tomás', comprueba: 'Agus', que: 'pegar la clave de proyectos de SE Ranking' },
  modular: { hace: 'Tomás', comprueba: 'Agus', que: 'pegar la clave de Modular DS' },
  anthropic: { hace: 'Tomás', comprueba: 'Agus', que: 'pegar la clave de la IA (Anthropic)' },
};
/** duenoConexion(id) → { hace, comprueba, que, texto: «Lo hace Tomás: pegar la clave de X; después Agus comprueba que llegan los datos» }. */
export function duenoConexion(id, quien = null) {
  const d = DUENOS[id] || { hace: quien || 'Agus', comprueba: null, que: null };
  return { ...d, texto: d.que ? `Lo hace ${d.hace}: ${d.que}; después ${d.comprueba} comprueba que llegan los datos` : `Lo arregla: ${d.hace}` };
}
/** Quita del texto las órdenes de terminal («con bash ~/…/pegar.sh», «security add-generic-password …»): van en «Más». */
function sinTerminal(t) {
  const ordenes = [];
  const limpio = String(t || '')
    .replace(/\s*(?:y\s+)?(?:pégala|pégalo|guárdala)?\s*con\s+(bash\s+\S+)/gi, (m, o) => { ordenes.push(o); return ''; })
    .replace(/:\s*(security\s+add-generic-password[^.]*)/gi, (m, o) => { ordenes.push(o); return ''; })
    .replace(/\(botón «Consola de la llave»\)\s*/g, '')
    .replace(/\s+y\s*\./g, '.').replace(/\s+\./g, '.').replace(/\s{2,}/g, ' ').trim();
  return { limpio, ordenes };
}
const esTomas = ctx => ctx?.real?.id === 'tomas' || ctx?.persona?.id === 'tomas';

const COLOR = { verde: ['verde', 'Funciona'], ambar: ['ambar', 'Vigilar'], rojo: ['rojo', 'No funciona'], gris: ['gris', 'Sin probar'] };
const ORDEN = ['rojo', 'ambar', 'gris', 'verde'];
const ESPERA_MS = 10000;
const TOQUE = { display: 'inline-flex', alignItems: 'center', minHeight: '32px' };   // V2: enlaces de 16 px → zona de toque de 32 px      // cada cuánto mira si ya hay prueba nueva tras «Probar ahora»
const ESPERA_MAX_MS = 240000; // 4 min: la prueba va al principio de la vuelta y tarda ~10-30 s

async function cargar(ctx) {
  try { return await ctx.datosModulo('conexiones/salud'); } catch (e) { return { error: e.message }; }
}

const segundos = ms => (ms === null || ms === undefined ? '—' : ms < 1000 ? `${fmt.num(ms)} ms` : `${fmt.num(ms / 1000, 1)} s`);
const cuando = t => (t ? `${fmt.fecha(t)} ${t.slice(11, 16)}` : '—');

function historial(c) {
  const hs = c.historial || [];
  if (!hs.length) return null;
  return h('span', { class: 'fila', style: { gap: '3px', alignItems: 'center' }, title: 'Últimas pruebas (la más nueva a la derecha)' },
    ...hs.map(x => h('span', {
      'aria-label': `${cuando(x.hora)}: ${COLOR[x.color]?.[1] || x.color}${x.ms ? ' · ' + segundos(x.ms) : ''}`,
      title: `${cuando(x.hora)} · ${COLOR[x.color]?.[1] || x.color}${x.ms ? ' · ' + segundos(x.ms) : ''}`,
      style: { display: 'inline-block', width: '10px', height: '10px', borderRadius: '50%',
        background: `var(--${{ verde: 'good', ambar: 'warn', rojo: 'bad' }[x.color] || 'off'})` },
    })));
}

function tarjeta(c, ctx) {
  const [color, txt] = COLOR[c.color] || ['gris', c.color];
  const caduca = c.caduca
    ? `${fmt.fecha(c.caduca)} (en ${c.dias_para_caducar} días)`
    : (c.caducidad_texto || '—');
  const D = DUENOS[c.id] && c.color !== 'verde' ? duenoConexion(c.id) : null;
  const sq = sinTerminal(c.que_hacer);
  const queHacer = D ? `${D.texto}.` : (c.que_hacer ? sq.limpio : null);
  const detalle = c.detalle ? sinTerminal(c.detalle).limpio.replace(/\(faltan? \d+ de \d+ en el llavero o el entorno\)/g, '').replace(/\s{2,}/g, ' ') : null;
  return h('article', { class: `pm-tarjeta ${color}`, 'data-conexion': c.id, style: { minWidth: 0, overflowWrap: 'anywhere' } },
    h('div', { class: 'pm-cab' }, h('span', { class: `ico-c ${color}` }, icono(c.icono || 'plug')),
      h('span', { class: 't' }, h('b', {}, c.nombre), h('span', {}, limpiaTexto(c.que_da || ''))),
      h('span', { class: 'der' }, chipEstado(color, c.titular || txt))),
    detalle ? h('p', { style: { margin: 0, font: 'var(--t-cuerpo)', maxWidth: '72ch' } }, limpiaTexto(detalle)) : null,
    queHacer ? avisoParcial(queHacer, { tipo: c.color === 'rojo' ? 'parcial' : 'info', titulo: 'Qué hacer:' }) : null,
    h('dl', { class: 'pm-kv' },
      h('dt', {}, 'Desde'), h('dd', {}, `${COLOR[c.color]?.[1] || ''} desde ${cuando(c.desde)}`),
      c.color !== 'verde' ? [h('dt', {}, 'Último OK'), h('dd', {}, c.ultimo_ok ? cuando(c.ultimo_ok) : 'nunca en esta app')] : null,
      h('dt', {}, 'Respuesta'), h('dd', {}, c.ms ? segundos(c.ms) : (c.estado === 'falta_clave' ? 'sin llave, no se prueba' : 'sin llamada en vivo')),
      h('dt', {}, 'Caduca'), h('dd', {}, c.dias_para_caducar !== null && c.dias_para_caducar !== undefined && c.dias_para_caducar <= 21 ? h('b', {}, caduca) : caduca),
      c.historial?.length > 1 ? [h('dt', {}, 'Últimas'), h('dd', {}, historial(c))] : null),
    h('details', { class: 'que-es' }, h('summary', {}, 'Más: cupo, llaves y quién la usa'),
      h('dl', { class: 'pm-kv' },
        c.color === 'verde' ? [h('dt', {}, 'Último OK'), h('dd', {}, cuando(c.ultimo_ok))] : null,
        c.limite ? [h('dt', {}, 'Cupo'), h('dd', {}, limpiaTexto(c.limite))] : null,
        h('dt', {}, 'Llaves'), h('dd', {}, `${(c.llaves_total || 0) - (c.llaves_faltan || 0)} de ${c.llaves_total || 0}`),
        c.modulos ? [h('dt', {}, 'La usan'), h('dd', {}, limpiaTexto(c.modulos) + (c.critica ? '' : ' · hoy no es imprescindible'))] : null,
        c.renovar?.donde ? [h('dt', {}, 'Dónde se renueva'), h('dd', {}, c.renovar.url ? h('a', { href: c.renovar.url, target: '_blank', rel: 'noopener', style: TOQUE }, `${limpiaTexto(c.renovar.donde)} ↗`) : limpiaTexto(c.renovar.donde))] : null,
        // V2: las órdenes de terminal, solo para Tomás y dentro de «Más» (nunca en la tarjeta a la vista)
        sq.ordenes.length && esTomas(ctx) ? [h('dt', {}, 'Paso técnico'), h('dd', {}, h('code', { style: { overflowWrap: 'anywhere' } }, sq.ordenes.join(' · ')))] : null)),
    c.renovar?.url && c.color !== 'verde' ? h('div', { class: 'fila' },
      h('a', { class: 'bt mini pri', href: c.renovar.url, target: '_blank', rel: 'noopener', title: c.renovar.donde }, icono('key'), 'Consola de la llave ↗')) : null,
    D ? h('span', { class: 'quien' }, icono('persona', { clase: 's' }), ` Lo hace: ${D.hace} · lo comprueba: ${D.comprueba}`)
      : c.quien ? h('span', { class: 'quien' }, icono('persona', { clase: 's' }), ` Lo arregla: ${c.quien}`) : null);
}

function botonProbar(ctx, D, alTerminar) {
  const estado = h('span', { class: 'sub', role: 'status', 'aria-live': 'polite' });
  const bt = h('button', { type: 'button', class: 'bt pri', title: 'Vuelve a probar todas las conexiones (solo lectura)' }, icono('recargar'), 'Probar ahora');
  bt.addEventListener('click', async () => {
    if (ctx.soloLectura) { estado.textContent = 'Estás en «ver como»: solo lectura. «Probar ahora» lo pulsa la persona real.'; return; }
    bt.disabled = true;
    estado.textContent = 'Pidiendo la prueba…';
    try {
      const r = await ctx.api('recarga', { metodo: 'POST', cuerpo: { modo: 'conexiones' } });
      estado.textContent = r.nueva ? 'Prueba pedida: se vuelven a probar las conexiones (unos 30 s).'
        : 'Ya había una prueba o una recarga en marcha: el resultado sale aquí en cuanto termine.';
    } catch (e) {
      bt.disabled = false;
      estado.textContent = e.status === 403
        ? (e.message || 'Tu puesto no puede pedir la prueba de conexiones. La piden Agus, Mili o Tomás.')
        : `No se pudo pedir la prueba: ${e.message}`;
      return;
    }
    const antes = D.generado;
    const t0 = Date.now();
    const mirar = async () => {
      const N = await cargar(ctx);
      if (!N.error && N.generado && N.generado !== antes) {
        estado.textContent = `Probado ${cuando(N.generado)}: ${N.resumen.verde} en verde, ${N.resumen.ambar} en ámbar y ${N.resumen.rojo} en rojo.`;
        bt.disabled = false;
        alTerminar(N);
        return;
      }
      if (Date.now() - t0 > ESPERA_MAX_MS) {
        estado.textContent = 'La prueba sigue en marcha; el resultado saldrá aquí al recargar la página.';
        bt.disabled = false;
        return;
      }
      setTimeout(mirar, ESPERA_MS);
    };
    setTimeout(mirar, ESPERA_MS);
  });
  return h('div', { class: 'fila', style: { alignItems: 'center', gap: '12px', flexWrap: 'wrap' } }, bt, estado);
}

// R15a (A2): objetivo = id de una conexión (#/ajustes/conexiones/<id> o #/conexiones/<id>) → su tarjeta resaltada y a la vista.
export async function vistaConexiones(ctx, { objetivo = null } = {}) {
  estilosLocales();
  const D0 = await cargar(ctx);
  if (D0.error) {
    return [vacio({ icono: 'plug', titulo: 'No se pudo leer la salud de las conexiones', texto: D0.error, quien: 'Agus', tono: 'aviso',
      tecnico: 'La escribe despliegue/salud_conexiones.py al empezar cada vuelta de la tubería (data/conexiones/salud.json).' })];
  }
  const raiz = h('div', { class: 'pm-conexiones' });
  const pintarTodo = (D, obj = null) => { raiz.replaceChildren(...cuerpo(ctx, D, pintarTodo, obj)); };
  pintarTodo(D0, objetivo);
  if (objetivo) {
    if ((D0.conexiones || []).some(c => c.id === objetivo)) llevarA(raiz, r => r.querySelector(`[data-conexion="${CSS.escape(objetivo)}"]`));
    else raiz.prepend(avisoParcial('Esa conexión ya no está en la lista de pruebas.', { titulo: 'No la encuentro.' }));
  }
  const avisos = await vistaAvisos(ctx).catch(() => []);
  return [raiz, ...avisos];
}

function cuerpo(ctx, D, repintar, objetivo = null) {
  const C = D.conexiones || [];
  const n = k => C.filter(c => c.color === k).length;
  const conCaducidad = C.filter(c => c.dias_para_caducar !== null && c.dias_para_caducar !== undefined).sort((a, b) => a.dias_para_caducar - b.dias_para_caducar);
  const prox = conCaducidad[0];
  const lentas = C.filter(c => c.ms).sort((a, b) => b.ms - a.ms);
  const caja = h('div', { class: 'pm-conex' });
  let filtro = '';
  const pintar = () => {
    const ls = C.filter(c => !filtro || c.color === filtro).sort((a, b) => ORDEN.indexOf(a.color) - ORDEN.indexOf(b.color));
    const movil = typeof matchMedia === 'function' && matchMedia('(max-width: 640px)').matches;
    const verdes = movil && !filtro ? ls.filter(c => c.color === 'verde' && c.id !== objetivo) : [];
    const resto = ls.filter(c => !verdes.includes(c));
    // V2 (B-M3): a 390 la pantalla medía 11.000 px: las que funcionan van plegadas en una línea
    caja.replaceChildren(...(ls.length ? [...resto.map(c => tarjeta(c, ctx)),
      verdes.length ? h('details', { class: 'que-es', style: { gridColumn: '1 / -1' } }, h('summary', { style: { minHeight: '44px', display: 'flex', alignItems: 'center', fontWeight: '600' } }, `${verdes.length} conexiones funcionan · ver`),
        h('div', { class: 'pm-conex' }, verdes.map(c => tarjeta(c, ctx)))) : null].filter(Boolean) : [vacio({ icono: 'ok', tono: 'celebrar', titulo: 'Ninguna en este color' })]));
  };
  const chips = chipsFiltro({ clave: 'ajustes.conexiones.n11', etiqueta: 'Ver', opciones: [
    { valor: '', texto: 'Todas', cuenta: C.length },
    { valor: 'rojo', texto: 'No funcionan', icono: 'alert', cuenta: n('rojo'), cuentaEstado: 'rojo' },
    { valor: 'ambar', texto: 'Vigilar', icono: 'clock', cuenta: n('ambar') },
    { valor: 'verde', texto: 'Funcionan', icono: 'ok', cuenta: n('verde') },
    ...(n('gris') ? [{ valor: 'gris', texto: 'Sin probar', icono: 'info', cuenta: n('gris') }] : [])],
  alCambiar: v => { filtro = v; pintar(); } });
  filtro = chips.valor();
  const obj = objetivo ? C.find(c => c.id === objetivo) : null;
  if (obj && filtro && obj.color !== filtro) filtro = '';   // que el filtro guardado no la esconda
  pintar();
  const ren = Object.entries(D.renovacion_acceso || {});
  const alertas = D.alertas || [];
  return [
    tiles([
      tile({ icono: 'plug', etiqueta: 'Conexiones que funcionan', valor: n('verde'), unidad: `de ${C.length}`,
        estado: n('rojo') ? 'rojo' : n('verde') === C.length ? 'verde' : 'ambar',
        contexto: `${n('rojo')} en rojo · ${n('ambar')} en ámbar${n('gris') ? ` · ${n('gris')} sin probar` : ''}`, medible: 'hoy',
        frescura: { fuente: 'Prueba de conexiones', fecha: D.generado, estado: D.en_vivo ? 'ok' : 'viejo' } }),
      tile({ icono: 'alert', etiqueta: 'Para arreglar ya', valor: n('rojo'), unidad: n('rojo') === 1 ? 'conexión' : 'conexiones',
        estado: n('rojo') ? 'rojo' : 'verde', contexto: n('rojo') ? C.filter(c => c.color === 'rojo').map(c => c.nombre).join(' · ') : 'Ninguna conexión que la app usa está caída' }),
      tile({ icono: 'clock', etiqueta: 'Próxima llave que caduca', valor: prox ? fmt.fecha(prox.caduca) : null, unidad: prox ? `${prox.nombre} · en ${prox.dias_para_caducar} días` : '',
        estado: !prox ? '' : prox.dias_para_caducar <= 7 ? 'rojo' : prox.dias_para_caducar <= 21 ? 'ambar' : 'verde', sinDato: 'ninguna llave con fecha',
        contexto: 'Aviso al dueño a 21 días; en rojo a 7' }),
      tile({ icono: 'medidor', etiqueta: 'La más lenta', valor: lentas[0] ? segundos(lentas[0].ms) : null, unidad: lentas[0]?.nombre || '',
        estado: lentas[0]?.ms > 5000 ? 'ambar' : '', contexto: 'Más de 5 s = ámbar «lenta»' }),
    ]),
    panel({ titulo: 'Estado de cada conexión', icono: 'plug',
      sub: `Probado ${cuando(D.generado)}${D.en_vivo ? '' : ' (vuelta sin red: se enseña lo último probado)'} · ${D.segundos ?? '—'} s. Cada tarjeta dice desde cuándo, qué hacer y quién lo arregla.`,
      acciones: botonProbar(ctx, D, repintar) },
    h('div', { class: 'pm-pad' }, chips), caja),
    alertas.length ? panel({ titulo: `Alertas a su dueño (${alertas.length})`, icono: 'campana', sub: 'Las recibe el dueño; si no dice «Lo tengo» en su plazo, sube a su jefe y luego a Tomás.' },
      listaConIcono(alertas.map(a => ({ icono: 'alert', estado: a.gravedad === 'alta' ? 'rojo' : 'ambar',
        texto: h('span', {}, h('b', {}, limpiaTexto(a.titulo)), a.que_hacer ? h('span', { class: 'sub' }, ` · ${limpiaTexto(sinTerminal(a.que_hacer).limpio)}`) : null),
        extra: `Dueño: ${ctx.nombre ? ctx.nombre(a.dueno_id) : a.dueno_id} · desde ${cuando(a.desde)} · plazo ${a.plazo_h} h` })))) : null,
    ren.length ? panel({ titulo: 'Tokens de acceso de 1 hora', icono: 'key', sub: 'Se renuevan solos al empezar cada vuelta si les quedan menos de 20 min (caché compartida entre procesos). Nunca se enseñan.' },
      listaConIcono(ren.map(([srv, r]) => ({ icono: r.estado === 'error' ? 'alert' : 'key', estado: r.estado === 'error' ? 'rojo' : r.estado === 'sin_llave' ? 'ambar' : 'verde',
        texto: h('span', {}, h('b', {}, { zoho: 'Zoho', google: 'Google', zoom: 'Zoom', snov: 'Snov.io' }[srv] || srv), h('span', { class: 'sub' }, ` · ${limpiaTexto(r.detalle || '')}`)),
        extra: r.quedan_min ? `quedan ${r.quedan_min} min` : '' })))) : null,
    avisoParcial(D.como || '', { tipo: 'info', titulo: 'Cómo se prueba.' }),
  ].filter(Boolean);
}

export async function vistaAvisos(ctx, D0) {
  estilosLocales();
  let D = D0;
  if (!D && ctx.veModulo && !ctx.veModulo('ajustes')) return [];   // R15a: el técnico no ve Ajustes → ni se pide (antes, 403 en su consola)
  if (!D) { try { D = await ctx.datosModulo('ajustes/conexiones'); } catch (e) { return []; } }   // el técnico no ve Ajustes: sin avisos, sin error
  const A = (D.avisos || []).filter(a => a.ir !== 'conexiones');   // los de cada conexión ya salen en su tarjeta
  if (!A.length) return [];
  const rojos = A.filter(a => a.gravedad === 'rojo').length;
  return [panel({ titulo: `Otros avisos del sistema (${A.length} · ${rojos} para actuar ya)`, icono: 'campana', sub: 'Fuentes de datos rotas o viejas, puerta de secretos y seguridad. Lo más grave arriba.' },
    listaConIcono(A.map(a => ({ icono: a.icono || 'alert', estado: a.gravedad, texto: h('span', {}, h('b', {}, limpiaTexto(a.titulo)), a.texto ? h('span', { class: 'sub' }, ` · ${limpiaTexto(sinTerminal(a.texto).limpio)}`) : null),
      extra: `Lo arregla: ${a.quien || 'Agus'}${a.hora ? ' · ' + a.hora : ''}` }))))];
}

// Módulo propio para el técnico (no ve Ajustes). Lo registra el coordinador en modulos/indice.js con
// { id: 'conexiones', num: 'N11', titulo: 'Conexiones', grupo: 'Sistema', fase: 0, estado: 'hecho', fichero: './ajustes_conexiones.js' }.
export default {
  id: 'conexiones',
  titulo: 'Conexiones',
  grupo: 'Sistema',
  puestos_que_lo_ven: { direccion: 'todo', operaciones: 'todo', tecnico_altas: 'todo' },
  async render(cont, ctx) {
    ctx.titulo?.('Conexiones', 'Salud de cada conexión con las herramientas: qué funciona, desde cuándo y qué hacer');
    cont.append(...await vistaConexiones(ctx, { objetivo: ctx.params?.[0] || null }));
  },
};
