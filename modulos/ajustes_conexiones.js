// modulos/ajustes_conexiones.js · «Salud del sistema» (3-oct-2026; antes «Conexiones», N11 del 2-oct).
// Encargo de Tomás: «que Agus tenga un panel de conexión con Google, con GoHighLevel, con ClickUp…; que siempre haya un
// validador cada X momentos de que esté funcionando». Lo ven Agus (técnico), Mili (operaciones) y Tomás (dirección).
// Datos: GET /api/vigia → data/vigia/estado.json, que escribe despliegue/vigia.py cada 10 min (independiente de la tubería):
// una lectura barata por herramienta y un repaso de la app por dentro (tubería, envíos, ClickUp, IA, disco, base y copia),
// con 24 h de historia por fila. Arriba un semáforo general; una fila por elemento con su color, desde cuándo, último OK,
// tiempo de respuesta, minigráfico de 24 h y QUÉ HACER en llano y quién. «Probar ahora» prueba SOLO esa fila
// (POST /api/vigia/probar { id }; regla probar_conexiones: Agus, Mili y Tomás; nunca en «ver como»).
// Si el vigía no ha pasado nunca en esta máquina, la pantalla enseña lo último de la tubería (data/conexiones/salud.json).
// Se usa en dos sitios: la pestaña de Ajustes (vistaConexiones) y, para el técnico, como módulo propio (export default).

import { fmt, chipsFiltro, chipEstado, vacio, panel, avisoParcial, icono, listaConIcono, limpiaTexto, tiles, tile } from '../componentes.js';
import { h, estilosLocales } from './personas_comun.js';
import { llevarA } from './_ir.js';

// V2 (B-M2, B-M3, A-M7) · UN dueño por conexión y en español llano. Lo leen esta pantalla y Captación (import).
// Las claves las pega Tomás (solo él tiene las cuentas de administrador); Agus comprueba después que llegan los datos.
const DUENOS = {
  google_ads: { hace: 'Tomás', comprueba: 'Agus', que: 'pegar la clave de Google Ads' },
  windsor: { hace: 'Tomás', comprueba: 'Agus', que: 'pegar la clave de Windsor (trae Google Ads y TikTok)' },
  seranking: { hace: 'Tomás', comprueba: 'Agus', que: 'pegar la clave de proyectos de SE Ranking' },
  modular: { hace: 'Tomás', comprueba: 'Agus', que: 'pegar la clave de solo lectura con modular/pegar.sh' },
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
/** L-41 · el aviso de una llave que falta sin la orden de terminal, sin «Falta la llave: Falta la llave» y sin repetir el titular que ya dice la etiqueta de la fila. */
export function detalleLlave(detalle, titular) {
  let x = String(detalle || '')
    .replace(/\s*(?:\.\s*)?Ejecuta:?\s*(?:security|python3?|bash|export)\b[\s\S]*$/i, '')
    .replace(/\s*[;,]?\s*(?:luego\s+|y\s+)?(?:python3?\s+\S+|export\s+[A-Za-z_]+=\S*)/gi, '');
  x = sinTerminal(x).limpio.replace(/(Falta la llave:?\s*)+/gi, 'Falta la llave ').replace(/\s{2,}/g, ' ').trim();
  const t = String(titular || '').trim();
  if (t && x.toLowerCase().startsWith(t.toLowerCase())) x = x.slice(t.length).replace(/^[\s·:,.\-–—]+/, '');
  return x ? x.charAt(0).toUpperCase() + x.slice(1) : '';
}
const esTomas = ctx => ctx?.real?.id === 'tomas' || ctx?.persona?.id === 'tomas';

const TXT = { verde: 'Funciona', ambar: 'Vigilar', rojo: 'No funciona', gris: 'Sin probar' };
const TOKEN = { verde: 'good', ambar: 'warn', rojo: 'bad', gris: 'off' };
const DE_COD = { v: 'verde', a: 'ambar', r: 'rojo', g: 'gris' };
const ORDEN = ['rojo', 'ambar', 'gris', 'verde'];
const TOQUE = { display: 'inline-flex', alignItems: 'center', minHeight: '32px' };
const REFRESCO_MS = 60000;      // la pantalla abierta se pone al día sola cada minuto
const ESPERA_PRUEBA_MS = 2000;  // tras «Probar ahora», mira cada 2 s si ya está el resultado
const ESPERA_PRUEBA_MAX_MS = 90000;

// ---------------------------------------------------------------- horas (siempre en hora de Madrid, como el vigía)
const madridAhora = () => new Date().toLocaleString('sv-SE', { timeZone: 'Europe/Madrid' }).slice(0, 16);
const minutos = t => (t ? Date.parse(t.replace(' ', 'T') + ':00Z') / 60000 : NaN);
const haceMin = t => Math.round(minutos(madridAhora()) - minutos(t));
function haceTexto(t) {
  const m = haceMin(t);
  if (!t || Number.isNaN(m)) return '—';
  if (m < 1) return 'ahora mismo';
  if (m < 90) return `hace ${m} min`;
  if (m < 48 * 60) return `hace ${Math.floor(m / 60)} h${m % 60 ? ` ${m % 60} min` : ''}`;
  return `hace ${Math.floor(m / 1440)} días`;
}
const hora = t => (t ? t.slice(11, 16) : '—');
const cuando = t => (!t ? '—' : t.slice(0, 10) === madridAhora().slice(0, 10) ? `hoy ${hora(t)}` : `${fmt.fecha(t)} ${hora(t)}`);
const segundos = ms => (ms === null || ms === undefined ? '—' : ms < 1000 ? `${fmt.num(ms)} ms` : `${fmt.num(ms / 1000, 1)} s`);

// ---------------------------------------------------------------- datos
async function cargar(ctx) {
  try {
    const d = await ctx.api('vigia');
    if (d && !d.vacio && Array.isArray(d.filas)) return d;
  } catch (e) {
    if (e.status === 403) return { error: e.message };
  }
  // Respaldo: el vigía no ha pasado aquí (o servidor sin vigía) → lo último de la tubería, sin minigráfico de 24 h.
  try { return deTuberia(await ctx.datosModulo('conexiones/salud')); } catch (e) { return { error: e.message }; }
}

function deTuberia(D) {
  const filas = (D.conexiones || []).map(c => ({
    ...c, grupo: 'conexiones', herramienta: c.grupo,
    h24: (c.historial || []).map(x => [minutos(x.hora), { verde: 'v', ambar: 'a', rojo: 'r' }[x.color] || 'g', x.ms]),
  }));
  const n = filas.filter(f => f.color === 'rojo').length;
  return { generado: D.generado, cada_min: null, respaldo: true, en_vivo: D.en_vivo, filas, avisos: [],
    resumen: { verde: D.resumen?.verde, ambar: D.resumen?.ambar, rojo: n, total: filas.length, fallan: n, vigilar: D.resumen?.ambar,
      titular: !n ? 'Todo funciona' : n === 1 ? '1 cosa falla' : `${n} cosas fallan` }, como: D.como };
}

// ---------------------------------------------------------------- minigráfico de 24 h (una raya por cada 10 min)
function mini24(f, generado) {
  const hs = f.h24 || [];
  const SVG = 'http://www.w3.org/2000/svg';
  const fin = Math.round(minutos(generado || madridAhora()));
  const ini = fin - 24 * 60;
  const ranuras = new Array(144).fill(null);
  for (const [t, c, ms] of hs) {
    const i = Math.floor((t - ini) / 10);
    if (i >= 0 && i < 144) {
      const peor = ranuras[i] && ORDEN.indexOf(ranuras[i].c) < ORDEN.indexOf(DE_COD[c]) ? ranuras[i] : { c: DE_COD[c] || 'gris', ms, t };
      ranuras[i] = peor;
    }
  }
  const caidas = hs.filter(x => x[1] === 'r').length;
  const vistos = hs.filter(x => x[1] !== 'g').length;
  const pct = f.pct_24h ?? (vistos ? Math.round(100 * hs.filter(x => x[1] !== 'r' && x[1] !== 'g').length / vistos) : null);
  const svg = document.createElementNS(SVG, 'svg');
  svg.setAttribute('viewBox', '0 0 144 12');
  svg.setAttribute('preserveAspectRatio', 'none');
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', hs.length ? `Últimas 24 horas: ${pct ?? '—'} % de las pruebas bien${caidas ? `, ${caidas} en rojo` : ''}.` : 'Sin historia todavía');
  Object.assign(svg.style, { width: '100%', maxWidth: '240px', height: '12px', display: 'block', borderRadius: 'var(--r-xs)', background: 'var(--line-soft)' });
  ranuras.forEach((r, i) => {
    if (!r) return;
    const rect = document.createElementNS(SVG, 'rect');
    rect.setAttribute('x', String(i));
    rect.setAttribute('y', '0');
    rect.setAttribute('width', '1');
    rect.setAttribute('height', '12');
    rect.style.fill = `var(--${TOKEN[r.c] || 'off'})`;
    const t = document.createElementNS(SVG, 'title');
    const d = new Date(r.t * 60000).toISOString().slice(11, 16);
    t.textContent = `${d} · ${TXT[r.c] || r.c}${r.ms ? ' · ' + segundos(r.ms) : ''}`;
    rect.append(t);
    svg.append(rect);
  });
  return h('span', { style: { display: 'flex', flexDirection: 'column', gap: '4px', minWidth: '0', flex: '1 1 160px', maxWidth: '240px' } },
    svg,
    h('span', { style: { font: 'var(--t-meta)', color: 'var(--dim)', display: 'flex', justifyContent: 'space-between', gap: '8px' } },
      h('span', {}, 'hace 24 h'), h('span', {}, hs.length ? `${pct ?? '—'} % bien` : 'sin historia'), h('span', {}, 'ahora')));
}

// ---------------------------------------------------------------- una fila
function filaEl(f, ctx, D, alProbar) {
  const color = f.color || 'gris';
  const Dn = DUENOS[f.id] && color !== 'verde' && f.estado !== 'sin_clave' ? duenoConexion(f.id) : null;
  const c = f;   // las órdenes de terminal nunca a la vista (pruebas_coherencia mira esta línea)
  const sq = sinTerminal(c.que_hacer);
  const queHacer = Dn ? `${Dn.texto}.` : (f.que_hacer ? sq.limpio : null);
  const quien = Dn ? `${Dn.hace} (lo comprueba ${Dn.comprueba})` : (f.quien || (f.quien_id && ctx.nombre ? ctx.nombre(f.quien_id) : null));
  const detalle = f.detalle ? (detalleLlave(String(f.detalle).replace(/\(faltan? \d+ de \d+ en el llavero o el entorno\)/g, ''), f.titular) || null) : null;
  const caduca = f.caduca ? `${fmt.fecha(f.caduca)} (en ${f.dias_para_caducar} días)` : (f.caducidad_texto || null);
  const probando = D.probando === f.id;
  const puedeProbar = D.puede_probar !== false && !ctx.soloLectura && !D.respaldo;
  const estadoBt = h('span', { class: 'sub', role: 'status', 'aria-live': 'polite', style: { font: 'var(--t-meta)' } }, probando ? 'Probando…' : '');
  const bt = puedeProbar ? h('button', { type: 'button', class: 'bt mini', disabled: probando || null, title: `Vuelve a probar solo «${f.nombre}» (lectura, sin gastar)` },
    icono('recargar'), probando ? 'Probando…' : 'Probar ahora') : null;
  if (bt) bt.addEventListener('click', () => alProbar(f, bt, estadoBt));
  const kv = (dt, dd) => [h('dt', { style: { color: 'var(--dim)' } }, dt), h('dd', { style: { margin: 0, minWidth: 0 } }, dd)];
  return h('article', {
    'data-conexion': f.id, 'data-color': color,
    style: { display: 'flex', flexDirection: 'column', gap: '8px', padding: '12px 16px', minWidth: 0, overflowWrap: 'anywhere',
      borderTop: '1px solid var(--line-soft)', borderLeft: `4px solid var(--${TOKEN[color]})` },
  },
  h('div', { style: { display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' } },
    h('span', { class: `ico-c ${color}` }, icono(f.icono || 'plug')),
    h('span', { style: { display: 'flex', flexDirection: 'column', minWidth: 0, flex: '1 1 200px' } },
      h('b', { style: { font: 'var(--t-h3)', color: 'var(--ink)' } }, f.nombre),
      f.que_da ? h('span', { style: { font: 'var(--t-meta)', color: 'var(--dim)' } }, limpiaTexto(f.que_da)) : null),
    chipEstado(color, f.titular || TXT[color]),
    bt),
  h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: '8px 24px', alignItems: 'flex-start', font: 'var(--t-meta)', color: 'var(--mid)' } },
    h('span', {}, h('b', {}, `${TXT[color]} desde `), cuando(f.desde), f.desde ? ` (${haceTexto(f.desde)})` : ''),
    h('span', {}, h('b', {}, 'Último OK: '), f.ultimo_ok ? cuando(f.ultimo_ok) : 'nunca en esta app'),
    h('span', {}, h('b', {}, 'Respuesta: '), f.ms !== null && f.ms !== undefined ? segundos(f.ms) : (f.estado === 'falta_clave' || f.estado === 'sin_clave' ? 'sin llave, no se prueba' : 'sin llamada')),
    mini24(f, D.generado), estadoBt),
  detalle && color !== 'verde' ? h('p', { style: { margin: 0, font: 'var(--t-cuerpo)', maxWidth: '80ch' } }, limpiaTexto(detalle)) : null,
  queHacer && color !== 'verde' ? avisoParcial(h('span', {}, limpiaTexto(queHacer), quien ? h('b', { style: { display: 'block', marginTop: '4px' } }, `Quién: ${quien}`) : null),
    { tipo: color === 'rojo' ? 'parcial' : 'info', titulo: 'Qué hacer:' }) : null,
  h('details', { class: 'que-es' }, h('summary', { style: TOQUE }, 'Más'),
    h('dl', { style: { display: 'grid', gridTemplateColumns: 'minmax(96px, max-content) 1fr', gap: '4px 12px', margin: '8px 0 0', font: 'var(--t-meta)' } },
      color === 'verde' && detalle ? kv('Detalle', limpiaTexto(detalle)) : null,
      kv('Última prueba', `${cuando(f.ultima_prueba)} · se prueba cada ${f.cada_min || D.cada_min || 10} min`),
      caduca ? kv('Caduca', f.dias_para_caducar !== null && f.dias_para_caducar !== undefined && f.dias_para_caducar <= 21 ? h('b', {}, caduca) : caduca) : null,
      f.limite ? kv('Cupo', limpiaTexto(f.limite)) : null,
      f.modulos ? kv('La usan', limpiaTexto(f.modulos) + (f.critica === false ? ' · hoy no es imprescindible' : '')) : null,
      f.renovar?.donde ? kv('Dónde se renueva', f.renovar.url ? h('a', { href: f.renovar.url, target: '_blank', rel: 'noopener', style: TOQUE }, `${limpiaTexto(f.renovar.donde)} ↗`) : limpiaTexto(f.renovar.donde)) : null,
      // V2: las órdenes de terminal, solo para Tomás y dentro de «Más» (nunca en la fila a la vista)
      sq.ordenes.length && esTomas(ctx) ? kv('Paso técnico', h('code', { style: { overflowWrap: 'anywhere' } }, sq.ordenes.join(' · '))) : null)));
}

// ---------------------------------------------------------------- semáforo general
function semaforo(D) {
  const R = D.resumen || {};
  const viejo = D.generado && D.cada_min && haceMin(D.generado) > 3 * D.cada_min;
  const color = viejo ? 'rojo' : R.fallan ? 'rojo' : R.vigilar ? 'ambar' : 'verde';
  const titular = viejo ? 'El vigía no está pasando' : R.titular || '—';
  const sub = viejo
    ? `Su último repaso fue ${haceTexto(D.generado)} (${cuando(D.generado)}) y debería pasar cada ${D.cada_min} min: lo de abajo puede estar viejo. Agus: arranca el vigía (en Coolify, la tarea programada «vigia»; en el Mac, el bucle del vigía).`
    : D.respaldo
      ? `El vigía aún no ha pasado en esta máquina: esto es lo último que probó la tubería (${cuando(D.generado)}).`
      : `${R.fallan ? `${(D.filas || []).filter(f => f.color === 'rojo').map(f => f.nombre).join(' · ')}. ` : ''}${R.vigilar ? `${R.vigilar} para vigilar. ` : ''}Último repaso ${haceTexto(D.generado)} (${hora(D.generado)}) · pasa cada ${D.cada_min} min${D.siguiente ? ` · el próximo hacia las ${hora(D.siguiente)}` : ''}.`;
  return h('section', {
    class: 'panel', role: 'status', 'aria-live': 'polite', 'data-semaforo': color,
    style: { display: 'flex', alignItems: 'center', gap: '16px', padding: '16px 20px', flexWrap: 'wrap',
      borderLeft: `6px solid var(--${TOKEN[color]})`, background: `var(--${TOKEN[color]}-soft)` },
  },
  h('span', { class: `ico-c ${color}`, style: { width: '48px', height: '48px' } }, icono(color === 'verde' ? 'ok' : 'alert')),
  h('span', { style: { display: 'flex', flexDirection: 'column', gap: '4px', flex: '1 1 240px', minWidth: 0 } },
    h('b', { style: { font: 'var(--t-h1)', color: `var(--${TOKEN[color]}-ink)` } }, titular),
    h('span', { style: { font: 'var(--t-cuerpo)', color: 'var(--ink)' } }, limpiaTexto(sub))),
  h('span', { style: { display: 'flex', gap: '8px', flexWrap: 'wrap' } },
    chipEstado('rojo', `${R.rojo ?? 0} no funcionan`), chipEstado('ambar', `${R.ambar ?? 0} vigilar`), chipEstado('verde', `${R.verde ?? 0} funcionan`)));
}

// ---------------------------------------------------------------- pantalla
// R15a (A2): objetivo = id de una fila (#/ajustes/conexiones/<id> o #/conexiones/<id>) → resaltada y a la vista.
export async function vistaConexiones(ctx, { objetivo = null } = {}) {
  estilosLocales();
  const D0 = await cargar(ctx);
  if (D0.error) {
    return [vacio({ icono: 'plug', titulo: 'No se pudo leer la salud del sistema', texto: D0.error, quien: 'Agus', tono: 'aviso',
      tecnico: 'La escribe el vigía cada 10 minutos (despliegue/vigia.py → data/vigia/estado.json).' })];
  }
  const raiz = h('div', { class: 'salud-sistema', style: { display: 'flex', flexDirection: 'column', gap: '16px' } });
  let filtro = null;
  const pintarTodo = (D, obj = null) => { raiz.replaceChildren(...cuerpo(ctx, D, pintarTodo, obj, v => { filtro = v; }, () => filtro)); };
  pintarTodo(D0, objetivo);
  if (objetivo) {
    if ((D0.filas || []).some(c => c.id === objetivo)) llevarA(raiz, r => r.querySelector(`[data-conexion="${CSS.escape(objetivo)}"]`));
    else raiz.prepend(avisoParcial('Esa fila ya no está en la salud del sistema.', { titulo: 'No la encuentro.' }));
  }
  // Se pone al día sola mientras está abierta (el vigía pasa cada 10 min; «Probar ahora» en cualquier momento).
  const reloj = setInterval(async () => {
    if (!raiz.isConnected) { clearInterval(reloj); return; }
    if (raiz.querySelector('button[disabled]') || raiz.querySelector('details[open]')) return;   // no repintar en mitad de algo
    const N = await cargar(ctx);
    if (!N.error && N.generado) pintarTodo(N);
  }, REFRESCO_MS);
  const avisos = await vistaAvisos(ctx).catch(() => []);
  return [raiz, ...avisos];
}

function cuerpo(ctx, D, repintar, objetivo, guardarFiltro, filtroGuardado) {
  const F = D.filas || [];
  const n = k => F.filter(c => c.color === k).length;
  const conCad = F.filter(c => c.dias_para_caducar !== null && c.dias_para_caducar !== undefined).sort((a, b) => a.dias_para_caducar - b.dias_para_caducar);
  const prox = conCad[0];
  const listaCon = h('div', {});
  const listaSis = h('div', {});
  let filtro = filtroGuardado() ?? '';

  const alProbar = async (f, bt, estado) => {
    if (ctx.soloLectura) { estado.textContent = 'Estás en «ver como»: solo lectura. «Probar ahora» lo pulsa la persona real.'; return; }
    bt.disabled = true;
    estado.textContent = 'Probando…';
    const antes = f.ultima_prueba;
    try {
      await ctx.api('vigia/probar', { metodo: 'POST', cuerpo: { id: f.id } });
    } catch (e) {
      bt.disabled = false;
      estado.textContent = e.status === 403 ? (e.message || 'Tu puesto no puede pedir la prueba. La piden Agus, Mili o Tomás.') : `No se pudo pedir la prueba: ${e.message}`;
      return;
    }
    const t0 = Date.now();
    const mirar = async () => {
      const N = await cargar(ctx);
      const nf = (N.filas || []).find(x => x.id === f.id);
      if (!N.error && nf && (nf.ultima_prueba !== antes || (!N.probando && Date.now() - t0 > 6000))) {
        repintar(N, f.id);
        const el = document.querySelector(`[data-conexion="${CSS.escape(f.id)}"] [role="status"]`);
        if (el) el.textContent = `Probado ahora: ${TXT[nf.color] || nf.color}${nf.ms ? ' · ' + segundos(nf.ms) : ''}.`;
        return;
      }
      if (Date.now() - t0 > ESPERA_PRUEBA_MAX_MS) { bt.disabled = false; estado.textContent = 'La prueba tarda: el resultado saldrá aquí en el próximo repaso.'; return; }
      setTimeout(mirar, ESPERA_PRUEBA_MS);
    };
    setTimeout(mirar, ESPERA_PRUEBA_MS);
  };

  const pintar = () => {
    const ver = c => !filtro || c.color === filtro;
    const orden = (a, b) => ORDEN.indexOf(a.color) - ORDEN.indexOf(b.color);
    for (const [caja, grupo] of [[listaCon, 'conexiones'], [listaSis, 'sistema']]) {
      const ls = F.filter(c => (c.grupo || 'conexiones') === grupo && ver(c)).sort(orden);
      // Lo que falla, a la vista; lo que funciona, plegado en una línea (a cualquier ancho: 30 filas verdes no dicen nada)
      const verdes = !filtro ? ls.filter(c => c.color === 'verde' && c.id !== objetivo) : [];
      const resto = ls.filter(c => !verdes.includes(c));
      caja.replaceChildren(...(ls.length ? [...resto.map(c => filaEl(c, ctx, D, alProbar)),
        verdes.length ? h('details', { class: 'que-es', style: { padding: '0 16px' } },
          h('summary', { style: { minHeight: '44px', display: 'flex', alignItems: 'center', fontWeight: '600' } }, `${verdes.length} funcionan bien · ver todas`),
          ...verdes.map(c => filaEl(c, ctx, D, alProbar))) : null].filter(Boolean)
        : [h('p', { class: 'sub', style: { padding: '12px 16px', margin: 0 } }, filtro ? 'Ninguna en este color.' : 'Nada que enseñar todavía.')]));
    }
  };
  const chips = chipsFiltro({ clave: 'salud.sistema', etiqueta: 'Ver', opciones: [
    { valor: '', texto: 'Todo', cuenta: F.length },
    { valor: 'rojo', texto: 'No funciona', icono: 'alert', cuenta: n('rojo'), cuentaEstado: 'rojo' },
    { valor: 'ambar', texto: 'Vigilar', icono: 'clock', cuenta: n('ambar') },
    { valor: 'verde', texto: 'Funciona', icono: 'ok', cuenta: n('verde') },
    ...(n('gris') ? [{ valor: 'gris', texto: 'Sin probar', icono: 'info', cuenta: n('gris') }] : [])],
  alCambiar: v => { filtro = v; guardarFiltro(v); pintar(); } });
  filtro = chips.valor();
  const obj = objetivo ? F.find(c => c.id === objetivo) : null;
  if (obj && filtro && obj.color !== filtro) filtro = '';
  pintar();
  const nCon = F.filter(c => (c.grupo || 'conexiones') === 'conexiones');
  const nSis = F.filter(c => c.grupo === 'sistema');
  const malos = L => L.filter(c => c.color === 'rojo').length;
  const avisos = D.avisos || [];
  return [
    semaforo(D),
    tiles([
      tile({ icono: 'plug', etiqueta: 'Herramientas conectadas', valor: nCon.filter(c => c.color === 'verde').length, unidad: `de ${nCon.length}`,
        estado: malos(nCon) ? 'rojo' : nCon.every(c => c.color === 'verde') ? 'verde' : 'ambar', contexto: `${malos(nCon)} sin funcionar · ${nCon.filter(c => c.color === 'ambar').length} para vigilar`, medible: 'hoy',
        frescura: { fuente: 'Vigía', fecha: D.generado, estado: D.respaldo ? 'viejo' : 'ok' } }),
      nSis.length ? tile({ icono: 'medidor', etiqueta: 'La app por dentro', valor: nSis.filter(c => c.color === 'verde').length, unidad: `de ${nSis.length} bien`,
        estado: malos(nSis) ? 'rojo' : nSis.every(c => c.color === 'verde') ? 'verde' : 'ambar', contexto: nSis.filter(c => c.color !== 'verde').map(c => c.nombre).join(' · ') || 'Tubería, envíos, ClickUp, IA, disco, base y copia: bien' }) : null,
      tile({ icono: 'clock', etiqueta: 'Próxima llave que caduca', valor: prox ? fmt.fecha(prox.caduca) : null, unidad: prox ? `${prox.nombre} · en ${prox.dias_para_caducar} días` : '',
        estado: !prox ? '' : prox.dias_para_caducar <= 7 ? 'rojo' : prox.dias_para_caducar <= 21 ? 'ambar' : 'verde', sinDato: 'ninguna llave con fecha',
        contexto: 'Aviso al dueño a 21 días; en rojo a 7' }),
    ].filter(Boolean)),
    h('div', { style: { padding: '0 4px' } }, chips),
    panel({ titulo: 'Conexiones con las herramientas', icono: 'plug', sub: 'Una lectura barata a cada herramienta, sin gastar créditos. La llave de GoHighLevel que rota no se usa aquí: se mira su última rotación.' }, listaCon),
    nSis.length ? panel({ titulo: 'La app por dentro', icono: 'medidor', sub: 'La propia app, la tubería de datos, lo que sale (envíos y ClickUp), la IA frente a su tope, el disco, la base y la copia del día.' }, listaSis) : null,
    avisos.length ? panel({ titulo: 'Últimos avisos en #avisos-altas', icono: 'campana', sub: 'Un aviso cuando algo cae (a Agus), otro si sigue más de 1 h (a Mili y Tomás) y otro cuando vuelve. Nunca uno cada 10 minutos.' },
      listaConIcono(avisos.slice(0, 8).map(a => ({ icono: a.tipo === 'vuelve' ? 'ok' : a.tipo === 'escalado' ? 'flag' : 'alert', estado: a.tipo === 'vuelve' ? 'verde' : 'rojo',
        texto: h('span', {}, limpiaTexto(sinTerminal(a.texto).limpio)), extra: `${cuando(a.hora)} · a ${(a.a || []).join(', ')}` })))) : null,
    avisoParcial(D.como || '', { tipo: 'info', titulo: 'Cómo se vigila.' }),
  ].filter(Boolean);
}

export async function vistaAvisos(ctx, D0) {
  estilosLocales();
  let D = D0;
  if (!D && ctx.veModulo && !ctx.veModulo('ajustes')) return [];   // R15a: el técnico no ve Ajustes → ni se pide (antes, 403 en su consola)
  if (!D) { try { D = await ctx.datosModulo('ajustes/conexiones'); } catch (e) { return []; } }
  const A = (D.avisos || []).filter(a => a.ir !== 'conexiones');   // los de cada conexión ya salen en su fila
  if (!A.length) return [];
  const rojos = A.filter(a => a.gravedad === 'rojo').length;
  return [panel({ titulo: `Otros avisos del sistema (${A.length} · ${rojos} para actuar ya)`, icono: 'campana', sub: 'Fuentes de datos rotas o viejas, puerta de secretos y seguridad. Lo más grave arriba.' },
    listaConIcono(A.map(a => ({ icono: a.icono || 'alert', estado: a.gravedad, texto: h('span', {}, h('b', {}, limpiaTexto(a.titulo)), a.texto ? h('span', { class: 'sub' }, ` · ${limpiaTexto(sinTerminal(a.texto).limpio)}`) : null),
      extra: `Lo arregla: ${a.quien || 'Agus'}${a.hora ? ' · ' + a.hora : ''}` }))))];
}

// Módulo propio (Agus no ve Ajustes). Registrado en modulos/indice.js como «Salud del sistema» (id «conexiones», N11).
export default {
  id: 'conexiones',
  titulo: 'Salud del sistema',
  grupo: 'Sistema',
  puestos_que_lo_ven: { direccion: 'todo', operaciones: 'todo', tecnico_altas: 'todo' },
  async render(cont, ctx) {
    ctx.titulo?.('Salud del sistema', 'Si todo funciona: cada herramienta y la app por dentro, desde cuándo, qué hacer y quién. El vigía pasa cada 10 minutos.');
    cont.append(...await vistaConexiones(ctx, { objetivo: ctx.params?.[0] || null }));
  },
};
