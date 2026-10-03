// ayudas.js · R15 «facilidad de uso» (E0, 2-oct noche). Fichero común de la carcasa; lo carga app.js con el navegador libre
// (no frena la entrada) y al momento si alguien pulsa ⌘K, «/» o la lupa antes.
//   A5 · buscador que busca DENTRO (clientes, personas, pantallas, tareas, correos, alertas, webs, campañas, reuniones,
//        decisiones e incidencias) y hace cosas («Contestar el correo de…», «Ir a la ficha de…», «Crear grupo», «Posponer
//        alerta…», «Semáforo de…», «Fijar…»), con el índice por persona que da el servidor (GET /api/buscar/indice: solo lo
//        que esa persona ya recibe recortado por la puerta de cada fichero). Teclado completo.
//   A6 · contadores del menú con la MISMA definición que «Lo mío» y Alertas (funciones puras de modulos/mi_dia_bloques.js)
//        y «Mis clientes» fijados (GET/POST /api/preferencias, por persona, con rastro).
//   A7 · «Algo va mal / Tengo una idea» en la cabecera (POST /api/opinion: quién y cuándo los pone el servidor; aviso en
//        #avisos-dirección; nada sale de la app). Mili y Tomás ven la lista en el mismo diálogo («Recibidos»).
//   A9 · atajos: «?» chuleta · «/» y ⌘K buscar · g+d Mi día · g+b Bandeja · g+a Alertas · g+c Chat · g+f Ficha (la chuleta solo enseña los de pantallas que ve) ·
//        j / k moverse por las filas · ↵ abrir la fila · e «Hecho» donde lo haya. Nunca dentro de un campo de texto.
import { h, icono, avisoFlotante, ICONO_MODULO, ICONO_GRUPO, fechas, sumarDias } from './componentes.js';

let A = null;          // ganchos de app.js
const $ = s => document.querySelector(s);
const normal = t => String(t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const enCampo = () => /^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement?.tagName) || !!document.activeElement?.isContentEditable;
const viendoComo = () => A.estado.persona?.id !== A.estado.real?.id;
const veo = id => A.modulosVisibles().some(m => m.id === id && m.estado === 'hecho');
const libre = fn => (self.requestIdleCallback ? requestIdleCallback(fn, { timeout: 3000 }) : setTimeout(fn, 300));

export function iniciar(ganchos) {
  if (A) return;
  A = ganchos;
  conectarPaleta();
  conectarAtajos();
  pintarBotonOpinion();
  vigilarRuta();
  libre(() => { refrescarContadores(); cargarFijados(); });
  setTimeout(() => libre(() => cargarIndice()), 2500);
  setInterval(() => { if (!document.hidden) refrescarContadores(); }, 60000);
  window.addEventListener('ro:avisos', () => refrescarContadores());
}

/** app.js avisa al entrar como otra persona («ver como») o al volver: contadores, fijados e índice son de la persona vista. */
export function alCambiarPersona() {
  PAL.indice = null; PAL.cargando = null;
  A.estado.contadores = {}; A.estado.fijados = undefined;
  refrescarContadores(); cargarFijados();
  pintarBotonOpinion();
}
/** Tras un POST (acción, alerta, «Lo tengo»…), los contadores se vuelven a contar (una vez cada 2 s como mucho). */
let _tras = null;
export function trasCambio() { clearTimeout(_tras); _tras = setTimeout(refrescarContadores, 1200); }

// ===================================================================== A6 · contadores y «Mis clientes»
let _contando = null;
/** Cuenta lo pendiente de cada pantalla con la definición de «Lo mío» (alertas «mías», correos de tu cartera, decisiones
 *  que esperan tu sí), la de Producción (vencidas en tu mano) y la de la campana (menciones sin leer). */
export async function contar() {
  const est = A.estado, yo = est.persona.id, real = !viendoComo();
  const LM = await import('./modulos/mi_dia_bloques.js').catch(() => null);
  const C = {};
  const ctx = A.ctxPara('mi-dia');
  const D = F => ({ dato: n => F[n], opcional: n => F[n] || null });
  const trabajos = [];
  if (veo('alertas') && real && LM?.alertasMias) {
    trabajos.push(Promise.all([A.api(`modulo/alertas/p_${yo}`), A.api('acciones?modulo=alertas').catch(() => ({ acciones: [] }))])
      .then(([Al, acc]) => { C.alertas = LM.alertasMias(Al, acc.acciones || [], { yo, personas: est.datos.personas || [] }).length; }).catch(() => {}));
  }
  if (veo('bandeja') && LM?.correosLoMio) {
    trabajos.push(Promise.all([A.api('modulo/bandeja/bandeja'), A.api('acciones?modulo=bandeja').catch(() => ({ acciones: [] }))])
      .then(([bj, acc]) => { C.bandeja = LM.correosLoMio(ctx, D({ 'bandeja/bandeja': bj }), { acciones: acc.acciones || [] }).reduce((s, x) => s + (x.n || 0), 0); })
      .catch(() => {}));
  }
  if (veo('decisiones') && LM?.decisionesMias) {
    trabajos.push(A.api('modulo/decisiones/reloj').then(r => { C.decisiones = LM.decisionesMias(ctx, D({ 'decisiones/reloj': r })).length; }).catch(() => {}));
  }
  if (veo('produccion')) trabajos.push(A.api('contadores').then(r => { if (typeof r.produccion === 'number') C.produccion = r.produccion; }).catch(() => {}));
  if (veo('chat-equipo')) trabajos.push(A.api('canales/campana').then(r => { C['chat-equipo'] = r.menciones || 0; }).catch(() => {}));
  await Promise.all(trabajos);
  return C;
}
export function refrescarContadores() {
  if (!A || !A.estado.servidor || _contando) return _contando;
  const quien = `${A.estado.real.id}|${A.estado.persona.id}`;
  _contando = contar().then(C => {
    if (quien === `${A.estado.real.id}|${A.estado.persona.id}`) { A.estado.contadores = C; A.pintarMenu(); }
    return C;
  }).finally(() => { _contando = null; });
  return _contando;
}

async function cargarFijados() {
  if (!A.estado.servidor) return;
  try { const r = await A.api('preferencias'); A.estado.fijados = Array.isArray(r.fijados) ? r.fijados : null; }
  catch { A.estado.fijados = null; }
  A.pintarMenu();
  pintarFijar();
}
/** Los ids de «Mis clientes» que se pintan: los fijados o, si nunca ha fijado nada, su cartera (lo calcula app.js). */
const idsMisClientes = () => A.idsMisClientes();
const estaFijado = id => idsMisClientes().includes(id);
async function fijar(id, si) {
  if (viendoComo()) { avisoFlotante('«Ver como» es solo lectura: no se fija nada.', { icono: 'alert' }); return; }
  const antes = idsMisClientes();
  const lista = si ? [...antes.filter(x => x !== id), id] : antes.filter(x => x !== id);
  try {
    const r = await A.api('preferencias', { metodo: 'POST', cuerpo: { fijados: lista } });
    A.estado.fijados = r.fijados;
    const nom = A.estado.datos.clientes.find(c => c.id === id)?.nombre || id;
    avisoFlotante(si ? `${nom} fijado en «Mis clientes»` : `${nom} fuera de «Mis clientes»`, { icono: si ? 'fijar' : 'ok' });
  } catch (e) { avisoFlotante(`No se pudo: ${e.message}`, { icono: 'alert' }); }
  A.pintarMenu();
  pintarFijar();
}

// Botón «Fijar» en la cabecera cuando la pantalla es de un cliente (ficha, En rojo…).
const CON_CLIENTE = new Set(['ficha', 'en-rojo', 'captacion', 'seo-web', 'redes', 'clientes-nuevos', 'informe-cliente', 'paneles', 'dinero-cliente']);
function clienteDeRuta() {
  const [, id, p0] = (location.hash || '').replace(/^#/, '').split('?')[0].split('/');
  let cid = null;
  try { cid = CON_CLIENTE.has(id) && p0 ? decodeURIComponent(p0) : null; } catch { cid = null; }
  return cid && A.estado.datos?.clientes?.some(c => c.id === cid && c.detalle) ? cid : null;
}
function pintarFijar() {
  const acc = $('#topbar-acc');
  if (!acc) return;
  let bt = $('#fijar-btn');
  const cid = clienteDeRuta();
  if (!cid || !A.estado.servidor) { bt?.remove(); return; }
  const si = estaFijado(cid);
  const nom = A.estado.datos.clientes.find(c => c.id === cid)?.nombre || cid;
  const etq = si ? `Quitar a ${nom} de «Mis clientes»` : `Fijar a ${nom} en «Mis clientes» (menú)`;
  if (!bt) {
    bt = h('button', { type: 'button', class: 'bt icono fijar-btn solo-ancho', id: 'fijar-btn' }, icono('fijar'));
    bt.addEventListener('click', () => fijar(bt.dataset.cli, bt.getAttribute('aria-pressed') !== 'true'));
    acc.prepend(bt);
  }
  bt.dataset.cli = cid;
  bt.setAttribute('aria-pressed', String(si));
  bt.setAttribute('aria-label', etq);
  bt.title = etq;
  bt.disabled = viendoComo();
}
function vigilarRuta() {
  window.addEventListener('hashchange', () => { setTimeout(pintarFijar, 50); quitarFoco(); });
  const t = $('#titulo');
  if (t) new MutationObserver(() => pintarFijar()).observe(t, { childList: true, characterData: true, subtree: true });
}

// ===================================================================== A5 · buscador que busca dentro y hace cosas
const PAL = { lista: [], sel: 0, indice: null, cargando: null, previo: null, q: '', vivos: null };
const ORDEN_GRUPOS = ['Acciones', 'Pantallas', 'Mis clientes', 'Clientes', 'Personas', 'Correos', 'Tareas', 'Alertas', 'Incidencias', 'Decisiones', 'Campañas', 'Webs', 'Reuniones'];
const ICONO_GRUPO_PAL = { Acciones: 'zap', 'Mis clientes': 'fijar', Clientes: 'cli', Personas: 'persona', Correos: 'mail', Tareas: 'check', Alertas: 'campana', Incidencias: 'alert', Decisiones: 'flag', Campañas: 'target', Webs: 'globe', Reuniones: 'video' };
const TIPO_FILA = { Pantallas: 'pantalla', 'Mis clientes': 'tu cliente', Clientes: 'cliente', Personas: 'persona', Correos: 'correo', Tareas: 'tarea', Alertas: 'alerta',
  Incidencias: 'incidencia', Decisiones: 'decisión', Campañas: 'campañas', Webs: 'web', Reuniones: 'reunión' };
const TOPE_GRUPO = { Acciones: 6, Pantallas: 8, 'Mis clientes': 8, Clientes: 6, Personas: 5 };

function cargarIndice() {
  if (!A.estado.servidor) return Promise.resolve([]);
  if (PAL.indice) return Promise.resolve(PAL.indice);
  if (!PAL.cargando) {
    const quien = `${A.estado.real.id}|${A.estado.persona.id}`;
    PAL.cargando = Promise.all([A.api('buscar/indice'), correosVivos()]).then(([r, vivos]) => {
      if (quien !== `${A.estado.real.id}|${A.estado.persona.id}`) return [];
      PAL.vivos = vivos;
      PAL.indice = (r.filas || []).map(x => ({ ...x, ir: rutaExacta(x), _n: normal(`${x.t} ${x.s || ''} ${x.k || ''}`), _t: normal(x.t) }));
      return PAL.indice;
    }).catch(() => { PAL.cargando = null; return []; });
  }
  return PAL.cargando;
}

/** V2-B (M11): los correos que cuentan como «pendientes» con la MISMA regla que la pantalla Bandeja y «Lo mío» de Mi día
 *  (sin automáticos ni boletines, sin los viejos y sin lo ya despachado en la cola de la Bandeja). Así «Contestar el correo
 *  más antiguo» abre el mismo correo que Mi día da como más antiguo (el que más horas lleva). null = no se pudo leer. */
function correosVivos() {
  if (!veo('bandeja')) return Promise.resolve(null);
  return Promise.all([A.api('modulo/bandeja/bandeja'), A.api('acciones?modulo=bandeja').catch(() => ({ acciones: [] }))])
    .then(([bj, acc]) => {
      const hechos = new Set((acc?.acciones || []).filter(a => !a.modulo || a.modulo === 'bandeja').map(a => String(a.objeto)));
      return new Set((bj?.correos || []).filter(x => !x.auto && !x.boletin && !x.viejo && !hechos.has(String(x.numero ?? x.id))).map(x => String(x.id)));
    }).catch(() => null);
}

/** R15b: las reuniones del índice llegan con «#/reuniones» (sin id): se lleva a la reunión exacta, por su id si viene
 *  o por su fecha y hora («AAAA-MM-DD · HH:MM · cliente» → #/reuniones/AAAA-MM-DD_HHMM). */
function rutaExacta(x) {
  if (x.g !== 'Reuniones' || x.ir !== '#/reuniones') return x.ir;
  if (x.id) return `#/reuniones/${encodeURIComponent(x.id)}`;
  const m = String(x.s || '').match(/(\d{4}-\d{2}-\d{2}) · (\d{2}):(\d{2})/);
  return m ? `#/reuniones/${m[1]}_${m[2]}${m[3]}` : x.ir;
}

function base() {
  const est = A.estado;
  const items = A.modulosVisibles().map(m => ({ g: 'Pantallas', t: m.titulo, s: m.estado === 'hecho' ? '' : 'prevista', ir: `#/${m.id}`, ico: ICONO_MODULO[m.id] || ICONO_GRUPO[m.grupo] || 'res' }));
  const veFicha = veo('ficha');
  const ruta = c => (veFicha ? `#/ficha/${c.id}` : `#/en-rojo/${c.id}`);
  const mis = new Set(idsMisClientes());
  for (const c of est.datos.clientes.filter(c => c.detalle)) {
    items.push({ g: mis.has(c.id) ? 'Mis clientes' : 'Clientes', t: c.nombre, s: c.enCartera ? 'de tu cartera' : '', ir: ruta(c), cli: c, ico: 'cli' });
  }
  const vePersonas = veo('personas'), veAjustes = veo('ajustes');
  if (vePersonas || veAjustes) {
    for (const p of est.datos.personas || []) {
      if (p.estado && p.estado !== 'activo') continue;
      items.push({ g: 'Personas', t: p.alias || p.nombre, s: (p.puestos || []).map(x => A.PUESTO[x]?.nombre).filter(Boolean).join(', '), k: p.nombre,
        ir: vePersonas ? `#/personas/${encodeURIComponent(p.id)}` : '#/ajustes', ico: 'persona' });
    }
  }
  return items.map(x => ({ ...x, _n: normal(`${x.t} ${x.s || ''} ${x.k || ''}`), _t: normal(x.t) }));
}

/** Día laborable siguiente a las 9:00 (para «Posponer hasta…»). V2-E: con el calendario de Madrid (ctx.hoy), no la zona del Mac. */
function siguienteLaborable() {
  const hoy = fechas.hoy();
  let d = sumarDias(hoy, 1);
  for (let i = 0; i < 7 && !fechas.laborable(d); i++) d = sumarDias(d, 1);
  const salta = fechas.diaSemana(d) === 'lun' && ['vie', 'sáb'].includes(fechas.diaSemana(hoy));
  return { hasta: `${d} 09:00`, texto: salta ? 'el lunes a las 9' : 'mañana a las 9' };
}

const VERBOS = [
  ['contestar', /^(contestar|contesta|responder|responde|correo)$/],
  ['ficha', /^(ficha|ir|abrir|abre)$/],
  ['semaforo', /^(semaforo|semaforos)$/],
  ['posponer', /^(posponer|pospon|aplazar)$/],
  ['fijar', /^(fijar|fija)$/],
  ['quitar', /^(quitar|desfijar|quita)$/],
  ['grupo', /^(grupo|crear|nuevo)$/],
  ['opinion', /^(algo|fallo|error|idea|mal|problema)$/],
  ['atajos', /^(atajos|atajo|teclado|ayuda)$/],
  ['vercomo', /^(ver)$/],
];

function acciones(q, palabras, clientesQ, indice) {
  const out = [];
  const est = A.estado;
  const verbo = VERBOS.find(([, re]) => re.test(palabras[0] || ''))?.[0] || null;
  const resto = verbo ? palabras.slice(1) : palabras;
  const cumple = x => resto.every(w => x._n.includes(w));
  const cliMatch = verbo ? clientesQ(resto) : clientesQ(palabras);
  const correos = (indice || []).filter(x => x.g === 'Correos' && (!PAL.vivos || PAL.vivos.has(String(x.id))));
  const masViejo = l => l.slice().sort((a, b) => (b.h || 0) - (a.h || 0))[0];
  const add = (t, s, extra) => out.push({ g: 'Acciones', t, s, ico: 'zap', accion: true, ...extra });
  const solo = !verbo && !palabras.length;
  // Contestar
  if (veo('bandeja') && (verbo === 'contestar' || solo || (!verbo && cliMatch.length))) {
    const objetivos = (verbo === 'contestar' && !resto.length) || solo ? [null] : cliMatch.slice(0, 3);
    for (const c of objetivos) {
      const l = c ? correos.filter(x => x.cid === c.id) : correos.filter(x => x.mia);
      const x = masViejo(l.length ? l : (c ? [] : correos));
      if (x) add(c ? `Contestar el correo más antiguo de ${c.nombre}` : 'Contestar el correo más antiguo', `«${x.t}» · ${x.s}`, { ir: `${x.ir}?contestar=1`, ico: 'mail' });
    }
    if (verbo === 'contestar' && resto.length && !cliMatch.length) {
      for (const x of correos.filter(cumple).slice(0, 3)) add(`Contestar «${x.t}»`, x.s, { ir: `${x.ir}?contestar=1`, ico: 'mail' });
    }
  }
  // Ficha, semáforo y fijar de un cliente
  const veFicha = veo('ficha');
  const cliAcc = verbo ? cliMatch.slice(0, 3) : cliMatch.slice(0, 1);
  if (veFicha && (verbo === 'ficha' || (!verbo && cliAcc.length))) for (const c of cliAcc) add(`Ir a la ficha de ${c.nombre}`, 'Resumen, contactos, resultados, trabajo…', { ir: `#/ficha/${c.id}`, ico: 'cli' });
  if (veFicha && (verbo === 'semaforo' || (!verbo && cliAcc.length && c_en_cartera(cliAcc[0])))) {
    for (const c of cliAcc) add(`Semáforo del lunes de ${c.nombre}`, 'Abre la ficha con el semáforo y la nota de 3 líneas', { ir: `#/ficha/${c.id}?semaforo=1`, ico: 'flag' });
  }
  if (est.servidor && !viendoComo() && (verbo === 'fijar' || verbo === 'quitar' || (!verbo && cliAcc.length))) {
    for (const c of cliAcc) {
      const si = estaFijado(c.id);
      if (verbo === 'fijar' && si) continue;
      if (verbo === 'quitar' && !si) continue;
      add(si ? `Quitar a ${c.nombre} de «Mis clientes»` : `Fijar a ${c.nombre} en «Mis clientes»`, 'Sale arriba del menú', { hacer: () => fijar(c.id, !si), ico: 'fijar' });
    }
  }
  // Posponer una alerta (solo las que puede posponer: suyas o de su departamento)
  if (verbo === 'posponer' && veo('alertas') && !viendoComo()) {
    const { hasta, texto } = siguienteLaborable();
    for (const x of (indice || []).filter(y => y.g === 'Alertas' && y.pos && cumple(y)).slice(0, 5)) {
      add(`Posponer hasta ${texto}: ${x.t}`, x.s, { hacer: () => posponer(x, hasta, texto), ico: 'clock' });
    }
  }
  // Generales
  const generales = [
    veo('chat-equipo') && !viendoComo() ? { v: 'grupo', t: 'Crear un grupo en el chat', s: 'Nombre y personas; queda en la app con rastro', ir: '#/chat-equipo/nuevo', ico: 'eq', n: 'crear grupo nuevo grupo chat' } : null,
    est.servidor ? { v: 'opinion', t: 'Algo va mal / Tengo una idea', s: 'Lo leen Mili y Tomás; se guarda la pantalla y la hora', hacer: () => abrirOpinion(), ico: 'opinion', n: 'algo va mal fallo error idea opinion avisar' } : null,
    { v: 'atajos', t: 'Ver los atajos de teclado', s: 'También con «?»', hacer: () => abrirChuleta(), ico: 'teclado', n: 'atajos teclado ayuda chuleta' },
    A.puedeVerComo() ? { v: 'vercomo', t: 'Ver como…', s: 'Solo lectura y queda en el rastro', hacer: () => abrirVerComo(), ico: 'ojo', n: 'ver como persona' } : null,
  ].filter(Boolean);
  for (const x of generales) {
    if (solo || verbo === x.v || (!verbo && palabras.every(w => normal(`${x.t} ${x.n}`).includes(w)))) add(x.t, x.s, x);
  }
  return out;
}
function c_en_cartera(c) { return !!A.estado.datos.carteraIds?.has?.(c.id); }

async function posponer(x, hasta, texto) {
  try {
    await A.api('acciones', { metodo: 'POST', cuerpo: { modulo: 'alertas', herramienta: 'app', tipo: 'alerta_posponer', objeto: x.id, texto: `Pospuesta hasta ${texto} (desde el buscador)`,
      vista_previa: { alerta: x.id, hasta, cuando: 'siguiente_laborable', desde: 'buscador' } } });
    avisoFlotante(`Pospuesta hasta ${texto}. Vuelve sola con el plazo de nuevo.`, { icono: 'clock' });
    PAL.indice = PAL.indice?.filter(y => y.id !== x.id) || null;
    refrescarContadores();
  } catch (e) { avisoFlotante(`No se pudo posponer: ${e.message}`, { icono: 'alert' }); }
}

function filtrar() {
  const q = $('#paleta-q').value.trim();
  PAL.q = q;
  const palabras = normal(q).split(/\s+/).filter(Boolean);
  const todos = [...base(), ...(PAL.indice || [])];
  const clientes = A.estado.datos.clientes.filter(c => c.detalle);
  const clientesQ = ws => (ws.length ? clientes.filter(c => ws.every(w => normal(c.nombre).includes(w))) : []).slice(0, 5);
  const puntos = x => (!palabras.length ? 0 : x._t === palabras.join(' ') ? 0 : x._t.startsWith(palabras[0]) ? 1 : ` ${x._t}`.includes(` ${palabras[0]}`) ? 2 : 3);
  const hallados = palabras.length ? todos.filter(x => palabras.every(w => x._n.includes(w))) : todos.filter(x => ['Pantallas', 'Mis clientes'].includes(x.g));
  const acc = acciones(q, palabras, clientesQ, PAL.indice);
  const porGrupo = new Map();
  for (const x of [...acc, ...hallados.sort((a, b) => puntos(a) - puntos(b))]) {
    const l = porGrupo.get(x.g) || porGrupo.set(x.g, []).get(x.g);
    if (l.length < (TOPE_GRUPO[x.g] || (palabras.length ? 5 : 0))) l.push(x);
  }
  // Con un verbo, primero las acciones; sin él, lo que más se parece (pantalla, cliente, persona) y luego el resto.
  const verbo = VERBOS.some(([, re]) => re.test(palabras[0] || ''));
  const orden = verbo || !palabras.length ? ORDEN_GRUPOS : ['Pantallas', 'Mis clientes', 'Clientes', 'Personas', 'Acciones', ...ORDEN_GRUPOS.slice(5)];
  PAL.lista = orden.flatMap(g => (porGrupo.get(g) || []).map(x => x));
  PAL.sel = 0;
  pintarLista();
}

function pintarLista() {
  const ul = $('#paleta-lista'), q = $('#paleta-q');
  const filas = [];
  let grupo = null;
  PAL.lista.forEach((it, i) => {
    if (it.g !== grupo) { grupo = it.g; filas.push(h('li', { class: 'grupo', role: 'presentation', 'aria-hidden': 'true' }, grupo)); }
    filas.push(h('li', { id: `pal-${i}`, role: 'option', class: it.accion ? 'accion' : null, 'aria-selected': i === PAL.sel ? 'true' : 'false',
      'aria-label': `${it.t}${it.s ? `, ${it.s}` : ''} · ${it.g}`,
      on: { click: () => ir(i), mousemove: () => { if (PAL.sel !== i) { PAL.sel = i; marcar(); } } } },
    h('span', { class: 'ico-c', 'aria-hidden': 'true' }, icono(it.ico || ICONO_GRUPO_PAL[it.g] || 'res', { clase: 's' })),
    h('span', { class: 'pal-t' }, h('span', { class: 'pal-1' }, it.t), it.s ? h('small', { class: 'pal-2' }, it.s) : null),
    h('span', { class: 'tipo' }, it.accion ? 'acción' : TIPO_FILA[it.g] || it.g.toLowerCase())));
  });
  if (!PAL.indice && A.estado.servidor && PAL.q) filas.push(h('li', { class: 'cargando', role: 'presentation' }, 'Buscando también en correos, tareas y alertas…'));
  if (!PAL.lista.length && (PAL.indice || !A.estado.servidor)) {
    filas.push(h('li', { class: 'nada', role: 'option', 'aria-disabled': 'true' }, 'Nada con eso entre lo que tu puesto puede ver. Prueba con un cliente, un asunto, una tarea o «contestar», «fijar», «posponer».'));
  }
  ul.replaceChildren(...filas);
  q.setAttribute('aria-activedescendant', PAL.lista.length ? `pal-${PAL.sel}` : '');
  $('#paleta-estado').textContent = PAL.q ? `${PAL.lista.length} resultados` : '';
  document.getElementById(`pal-${PAL.sel}`)?.scrollIntoView({ block: 'nearest' });
}
function marcar() {
  document.querySelectorAll('#paleta-lista li[role=option]').forEach(li => li.setAttribute('aria-selected', li.id === `pal-${PAL.sel}` ? 'true' : 'false'));
  $('#paleta-q').setAttribute('aria-activedescendant', `pal-${PAL.sel}`);
  document.getElementById(`pal-${PAL.sel}`)?.scrollIntoView({ block: 'nearest' });
}
function saltarGrupo(dir) {
  const g = PAL.lista[PAL.sel]?.g;
  let i = PAL.sel;
  if (dir > 0) { while (i < PAL.lista.length && PAL.lista[i].g === g) i++; if (i >= PAL.lista.length) i = 0; }
  else { while (i > 0 && PAL.lista[i - 1].g === g) i--; i = i > 0 ? i - 1 : PAL.lista.length - 1; const g2 = PAL.lista[i]?.g; while (i > 0 && PAL.lista[i - 1].g === g2) i--; }
  PAL.sel = Math.max(0, i);
  marcar();
}

export function abrirPaleta() {
  const fondo = $('#paleta');
  if (!fondo.hidden) { $('#paleta-q').focus(); return; }
  PAL.previo = document.activeElement;
  fondo.hidden = false;
  $('#paleta-q').value = '';
  filtrar();
  $('#paleta-q').focus();
  if (!PAL.indice) cargarIndice().then(() => { if (!$('#paleta').hidden) { const s = PAL.sel; filtrar(); PAL.sel = Math.min(s, Math.max(0, PAL.lista.length - 1)); marcar(); } });
}
export function cerrarPaleta() { $('#paleta').hidden = true; PAL.previo?.focus?.(); }
export function alternarPaleta() { $('#paleta').hidden ? abrirPaleta() : cerrarPaleta(); }

/** Abre lo elegido: va a la ruta exacta (la pantalla abre sola el objeto, el editor o el formulario) o hace la acción. */
async function ir(i) {
  const it = PAL.lista[i];
  if (!it) return;
  $('#paleta').hidden = true;
  A.apuntar({ accion: 'paleta', objeto: it.g, datos: { grupo: it.g, accion: !!it.accion, con_texto: !!PAL.q } });
  if (it.hacer) { await it.hacer(); return; }
  if (!it.ir) return;
  if (location.hash === it.ir) window.dispatchEvent(new HashChangeEvent('hashchange'));
  else location.hash = it.ir;
  $('#main').focus({ preventScroll: true });
}
function conectarPaleta() {
  const q = $('#paleta-q');
  q.placeholder = 'Busca un cliente, un correo, una tarea… o escribe «contestar», «fijar», «posponer»';
  q.setAttribute('aria-describedby', 'paleta-ayuda');
  const pal = $('#paleta .paleta');
  if (!$('#paleta-estado')) pal.append(h('span', { id: 'paleta-estado', class: 'sr', role: 'status', 'aria-live': 'polite' }));
  if (!$('#paleta-ayuda')) pal.append(h('span', { id: 'paleta-ayuda', class: 'sr' }, 'Flechas para moverse, Tab para cambiar de grupo, Intro para abrir, Escape para cerrar.'));
  const pie = $('#paleta .pie');
  if (pie) pie.replaceChildren(h('span', {}, h('kbd', {}, '↑'), ' ', h('kbd', {}, '↓'), ' moverse'), h('span', {}, h('kbd', {}, 'Tab'), ' grupo'),
    h('span', {}, h('kbd', {}, '↵'), ' abrir o hacer'), h('span', {}, h('kbd', {}, 'Esc'), ' cerrar'), h('span', {}, h('kbd', {}, '?'), ' atajos'), h('span', {}, 'Solo lo que tu puesto puede ver'));
  q.addEventListener('input', filtrar);
  q.addEventListener('keydown', e => {
    const n = PAL.lista.length;
    if (e.key === 'ArrowDown') { e.preventDefault(); if (n) { PAL.sel = (PAL.sel + 1) % n; marcar(); } }
    else if (e.key === 'ArrowUp') { e.preventDefault(); if (n) { PAL.sel = (PAL.sel - 1 + n) % n; marcar(); } }
    else if (e.key === 'PageDown' || (e.key === 'Tab' && !e.shiftKey)) { e.preventDefault(); if (n) saltarGrupo(1); }
    else if (e.key === 'PageUp' || (e.key === 'Tab' && e.shiftKey)) { e.preventDefault(); if (n) saltarGrupo(-1); }
    else if ((e.key === 'Home' || e.key === 'End') && (e.ctrlKey || e.metaKey)) { e.preventDefault(); if (n) { PAL.sel = e.key === 'Home' ? 0 : n - 1; marcar(); } }
    else if (e.key === 'Enter') { e.preventDefault(); ir(PAL.sel); }
    else if (e.key === 'Escape') { e.preventDefault(); if (q.value) { q.value = ''; filtrar(); } else cerrarPaleta(); }
  });
  $('#paleta').addEventListener('click', e => { if (e.target.id === 'paleta') cerrarPaleta(); });
}

// ===================================================================== A9 · atajos de teclado y chuleta
const IR_G = { d: 'mi-dia', b: 'bandeja', a: 'alertas', c: 'chat-equipo', f: 'ficha', p: 'produccion' };
/** «g d» va a Mi día o, si su puesto tiene otro inicio, a su primera pantalla. La misma regla en el atajo y en la chuleta. */
const destinoG = id => (id === 'mi-dia' && !veo('mi-dia') ? A.modulosVisibles().find(m => m.estado === 'hecho')?.id : id);
let _g = 0;
function conectarAtajos() {
  document.addEventListener('keydown', e => {
    if (e.defaultPrevented || e.metaKey || e.ctrlKey || e.altKey || enCampo()) return;
    if (!$('#paleta').hidden || document.querySelector('.dialogo-fondo:not([hidden])')) return;
    const k = e.key;
    if (k === '?' || (e.shiftKey && e.code === 'Slash' && k !== '/')) { e.preventDefault(); abrirChuleta(); return; }
    if (_g && Date.now() - _g < 1500 && IR_G[k.toLowerCase()]) {
      e.preventDefault(); _g = 0;
      const id = IR_G[k.toLowerCase()];
      const destino = destinoG(id);
      if (destino && veo(destino)) { A.apuntar({ accion: 'atajo', objeto: `g ${k.toLowerCase()}` }); location.hash = `#/${destino}`; }
      else avisoFlotante('Esa pantalla no es de tu puesto.', { icono: 'alert' });
      return;
    }
    _g = 0;
    if (k === 'g') { _g = Date.now(); return; }
    if (k === 'j' || k === 'k') { e.preventDefault(); moverFila(k === 'j' ? 1 : -1); return; }
    if (k === 'e' && FOCO.el) { e.preventDefault(); hechoEnFila(); return; }
    if (k === 'Enter' && FOCO.el && document.activeElement === FOCO.el) { e.preventDefault(); abrirFila(); }
  });
}
// Filas: las de las tablas, «Lo primero», las listas de módulos ([data-fila]) y las filas de lista con rol.
const FILAS = '#main tbody tr, #main .primero > li, #main [data-fila], #main [role="listitem"]:not(.tile):not(.tiles > *), #main .lista-filas > li';
const FOCO = { el: null };
function filasVisibles() { return [...document.querySelectorAll(FILAS)].filter(el => el.offsetParent !== null && !el.closest('[hidden], details:not([open]) > :not(summary)')); }
function quitarFoco() { FOCO.el?.classList.remove('fila-foco'); FOCO.el = null; }
function moverFila(d) {
  const filas = filasVisibles();
  if (!filas.length) { avisoFlotante('Aquí no hay filas que recorrer.', { icono: 'info' }); return; }
  let i = filas.indexOf(FOCO.el);
  i = i < 0 ? (d > 0 ? 0 : filas.length - 1) : Math.min(filas.length - 1, Math.max(0, i + d));
  quitarFoco();
  const el = filas[i];
  FOCO.el = el;
  if (!el.hasAttribute('tabindex')) el.setAttribute('tabindex', '-1');
  el.classList.add('fila-foco');
  el.focus({ preventScroll: true });
  el.scrollIntoView({ block: 'nearest' });
}
const RE_HECHO = /^\s*(hecho|lo tengo|marcar hecho|hecha|resuelta|resuelto)\s*$/i;
function hechoEnFila() {
  const b = FOCO.el.querySelector('[data-atajo="e"]') || [...FOCO.el.querySelectorAll('button')].find(x => RE_HECHO.test(x.textContent || '') && !x.disabled);
  if (!b) { avisoFlotante('En esta fila no hay «Hecho».', { icono: 'info' }); return; }
  A.apuntar({ accion: 'atajo', objeto: 'e' });
  b.click();
}
function abrirFila() {
  const a = FOCO.el.querySelector('a[href]:not([target="_blank"])') || FOCO.el.querySelector('a[href], button:not([disabled])');
  (a || FOCO.el).click();
}

/** Diálogo modal común de la carcasa (chuleta y «Algo va mal»): mismo aspecto que el buscador, foco atrapado, Esc cierra. */
function dialogo(id, titulo, sub, cuerpo) {
  let fondo = document.getElementById(id);
  const previo = document.activeElement;
  fondo?.remove();
  const tit = h('h2', { id: `${id}-t` }, titulo);
  const cerrar = () => { fondo.hidden = true; fondo.remove(); previo?.focus?.(); };
  const caja = h('div', { class: 'paleta dialogo', role: 'dialog', 'aria-modal': 'true', 'aria-labelledby': `${id}-t` },
    h('div', { class: 'dialogo-cab' }, h('div', {}, tit, sub ? h('p', {}, sub) : null),
      h('button', { type: 'button', class: 'bt icono', 'aria-label': 'Cerrar', on: { click: cerrar } }, icono('cerrar'))),
    cuerpo);
  fondo = h('div', { class: 'paleta-fondo dialogo-fondo', id }, caja);
  fondo.addEventListener('click', e => { if (e.target === fondo) cerrar(); });
  fondo.addEventListener('keydown', e => {
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); cerrar(); return; }
    if (e.key !== 'Tab') return;
    const foc = [...caja.querySelectorAll('button, a[href], input, textarea, select, [tabindex]:not([tabindex="-1"])')].filter(x => !x.disabled && x.offsetParent !== null);
    if (!foc.length) return;
    if (e.shiftKey && document.activeElement === foc[0]) { e.preventDefault(); foc[foc.length - 1].focus(); }
    else if (!e.shiftKey && document.activeElement === foc[foc.length - 1]) { e.preventDefault(); foc[0].focus(); }
  });
  document.body.append(fondo);
  (caja.querySelector('[autofocus], textarea, input') || caja.querySelector('button'))?.focus();
  return { fondo, caja, cerrar };
}

export function abrirChuleta() {
  const mac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
  const k = (...t) => h('dt', {}, t.map(x => h('kbd', {}, x)));
  const fila = (teclas, que) => [k(...teclas), h('dd', {}, que)];
  // V2-E (40_A B10): solo los «g + letra» de pantallas que esta persona ve (en «ver como», las de la persona vista). «g d»
  // lleva a Mi día o, si su puesto tiene otro inicio, a esa pantalla (con su nombre, no «tu inicio»).
  const ir = Object.entries(IR_G).map(([l, id]) => [l, destinoG(id)]).filter(([, id]) => id && veo(id))
    .map(([l, id]) => fila(['g', l], `Ir a ${A.modulosVisibles().find(m => m.id === id)?.titulo || id}`));
  dialogo('chuleta', 'Atajos de teclado', 'No funcionan mientras escribes en un campo.', h('div', { class: 'pila' },
    h('p', { class: 'atajos-t' }, 'Buscar y moverse'),
    h('dl', { class: 'atajos' }, fila([mac ? '⌘' : 'Ctrl', 'K'], `Buscar o hacer algo (${queBusca()})`), fila(['/'], 'Lo mismo'), fila(['?'], 'Esta chuleta'), ...ir),
    h('p', { class: 'atajos-t' }, 'En las listas'),
    h('dl', { class: 'atajos' }, fila(['j'], 'Fila siguiente'), fila(['k'], 'Fila anterior'), fila(['↵'], 'Abrir la fila'), fila(['e'], 'Marcar «Hecho» o «Lo tengo» donde lo haya')),
    h('p', { class: 'atajos-t' }, 'En el buscador'),
    h('dl', { class: 'atajos' }, fila(['↑', '↓'], 'Moverse'), fila(['Tab'], 'Siguiente grupo'), fila(['↵'], 'Abrir o hacer'), fila(['Esc'], 'Borrar y cerrar')),
    h('p', { class: 'sub' }, `Prueba en el buscador: ${pruebasBuscador()}.`)));
  A.apuntar({ accion: 'atajo', objeto: '?' });
}
/** Lo que encuentra el buscador, dicho solo con lo que su puesto ve (nada de «correos» a quien no tiene Bandeja). */
function queBusca() {
  const q = ['clientes'];
  if (veo('bandeja')) q.push('correos');
  if (veo('produccion') || veo('mi-dia')) q.push('tareas');
  if (veo('alertas')) q.push('alertas');
  return `${q.join(', ')}…`;
}
function pruebasBuscador() {
  const p = [];
  if (veo('bandeja')) p.push('«contestar gac»');
  p.push('«fijar»');
  if (veo('alertas')) p.push('«posponer»', '«semáforo»');
  if (veo('chat-equipo')) p.push('«crear grupo»');
  return p.join(', ');
}
function abrirVerComo() {
  const btn = $('#yo-btn');
  if (btn?.getAttribute('aria-expanded') !== 'true') btn?.click();
  setTimeout(() => $('#vercomo-sel')?.focus(), 30);
}

// ===================================================================== A7 · «Algo va mal / Tengo una idea»
function pintarBotonOpinion() {
  if (!A.estado.servidor || $('#opinion-btn')) return;
  const b = h('button', { type: 'button', class: 'bt icono', id: 'opinion-btn', 'aria-haspopup': 'dialog', 'aria-label': 'Algo va mal o tengo una idea', title: 'Algo va mal / Tengo una idea' }, icono('opinion'));
  b.addEventListener('click', () => abrirOpinion());
  $('#buscar')?.before(b);
}

/** V2-E (40_A B12): la MISMA hora de datos que la cabecera (app.js › #frescura): meta.generado con fechas.hora() y, si
 *  los datos no son de hoy, el día («datos de ayer, 23:14»). Antes cortaba el texto y salía otra hora. */
function frescuraTexto() {
  const meta = A.estado.datos?.meta || A.estado.crudo?.meta || {};
  const malas = (meta.fuentes || []).filter(x => x.estado !== 'ok').map(x => x.fuente);
  const gen = String(meta.generado || '');
  const dd = fechas.diaDatos(gen), hh = fechas.hora(gen) || gen.slice(-5);
  const base = !gen ? 'datos sin hora' : dd.esHoy || !dd.dia ? `datos de las ${hh}`
    : `datos ${dd.texto.startsWith('datos de ayer') ? 'de ayer' : `del ${fechas.diaSemana(dd.dia)} ${Number(dd.dia.slice(8, 10))}`}, ${hh}`;
  return `${base}${malas.length ? ` · con aviso: ${malas.slice(0, 4).join(', ')}` : ''}`;
}

/** Captura de la pantalla, opcional: el navegador pregunta qué compartir (getDisplayMedia); se baja a ≤ 1.280 px en JPEG. */
async function capturar(fondo) {
  if (!navigator.mediaDevices?.getDisplayMedia) throw new Error('Este navegador no deja hacer capturas desde la página.');
  const flujo = await navigator.mediaDevices.getDisplayMedia({ video: { displaySurface: 'browser' }, audio: false, preferCurrentTab: true, selfBrowserSurface: 'include' });
  try {
    fondo.style.visibility = 'hidden';
    await new Promise(r => setTimeout(r, 350));
    const v = document.createElement('video');
    v.srcObject = flujo; v.muted = true;
    await v.play();
    await new Promise(r => setTimeout(r, 150));
    const esc = Math.min(1, 1280 / (v.videoWidth || 1280));
    const c = document.createElement('canvas');
    c.width = Math.round((v.videoWidth || 1280) * esc); c.height = Math.round((v.videoHeight || 720) * esc);
    c.getContext('2d').drawImage(v, 0, 0, c.width, c.height);
    let q = 0.7, url = c.toDataURL('image/jpeg', q);
    while (url.length > 185000 && q > 0.25) { q -= 0.1; url = c.toDataURL('image/jpeg', q); }
    if (url.length > 185000) { const c2 = document.createElement('canvas'); c2.width = c.width / 2; c2.height = c.height / 2; c2.getContext('2d').drawImage(c, 0, 0, c2.width, c2.height); url = c2.toDataURL('image/jpeg', 0.6); }
    return url;
  } finally {
    flujo.getTracks().forEach(t => t.stop());
    fondo.style.visibility = '';
  }
}

export function abrirOpinion() {
  const est = A.estado;
  const pantalla = $('#titulo')?.textContent || '';
  const ruta = (location.hash || '#/').slice(0, 200);
  const datos = { tipo: 'fallo', prioridad: 'ambar', captura: null };
  const soloLectura = viendoComo();
  const esLector = (est.real.puestos || []).some(x => x === 'direccion' || x === 'operaciones');
  const zona = h('div', { class: 'pila' });
  const pestanas = h('div', { class: 'segm', role: 'tablist', 'aria-label': 'Secciones' });
  const d = dialogo('opinion', 'Algo va mal / Tengo una idea', 'Lo leen Mili y Tomás. Se guarda con la pantalla, tu nombre, el ancho y la hora; no sale de la app.', h('div', { class: 'pila' }, pestanas, zona));
  const tabs = [['enviar', 'Enviar'], ['mios', 'Los míos'], ...(esLector ? [['recibidos', 'Recibidos']] : [])];
  const elegir = id => {
    pestanas.querySelectorAll('button').forEach(b => b.setAttribute('aria-selected', String(b.dataset.id === id)));
    pestanas.querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.id === id)));
    zona.replaceChildren();
    if (id === 'enviar') { zona.append(formulario()); zona.querySelector('textarea')?.focus(); }
    else zona.append(vistaOpiniones({ api: A.api, todas: id === 'recibidos', soloLectura }));
  };
  pestanas.append(...tabs.map(([id, t]) => h('button', { type: 'button', role: 'tab', 'data-id': id, on: { click: () => elegir(id) } }, t)));

  function formulario() {
    const f = h('form', { class: 'pila', novalidate: true });
    const tipoBt = (v, t, ico) => h('button', { type: 'button', class: 'bt', 'aria-pressed': String(datos.tipo === v), on: { click: () => { datos.tipo = v; repintar(); } } }, icono(ico), t);
    const prioBt = (v, t) => h('button', { type: 'button', class: 'bt mini', 'aria-pressed': String(datos.prioridad === v), on: { click: () => { datos.prioridad = v; repintar(); } } }, t);
    const texto = h('textarea', { id: 'op-texto', rows: 4, maxlength: 2000, required: true, autofocus: true,
      placeholder: datos.tipo === 'fallo' ? (veo('bandeja') ? 'Qué has visto (por ejemplo: «En la Bandeja no sale el correo de GAC de ayer»)' : `Qué has visto (por ejemplo: «En ${pantalla || 'esta pantalla'} falta un cliente»)`) : 'Qué cambiarías y para qué' });
    const esperaba = h('textarea', { id: 'op-esperaba', rows: 2, maxlength: 1000, placeholder: 'Qué esperabas ver (opcional)' });
    const estado = h('p', { class: 'sub', role: 'status', 'aria-live': 'polite' });
    const miniatura = h('span', { class: 'opinion-captura' });
    const btCap = h('button', { type: 'button', class: 'bt mini', on: { click: async () => {
      try { datos.captura = await capturar(d.fondo); estado.textContent = 'Captura lista.'; pintarCaptura(); }
      catch (e) { estado.textContent = e?.name === 'NotAllowedError' ? 'Sin captura (no se ha dado permiso). Se puede enviar igual.' : `Sin captura: ${e.message}`; }
    } } }, icono('ojo'), 'Añadir una captura');
    const pintarCaptura = () => miniatura.replaceChildren(...(datos.captura ? [h('img', { src: datos.captura, alt: 'Captura que se enviará' }),
      h('button', { type: 'button', class: 'bt mini', on: { click: () => { datos.captura = null; pintarCaptura(); } } }, 'Quitar')] : [btCap]));
    pintarCaptura();
    const enviar = h('button', { type: 'submit', class: 'bt pri', disabled: soloLectura || null }, icono('send'), 'Enviar a Mili y Tomás');
    const repintar = () => { const v = texto.value, v2 = esperaba.value; zona.replaceChildren(formulario()); $('#op-texto').value = v; const e2 = $('#op-esperaba'); if (e2) e2.value = v2; $('#op-texto').focus(); };
    f.addEventListener('submit', async e => {
      e.preventDefault();
      if (soloLectura) { estado.textContent = 'Estás en «ver como»: solo lectura. Lo envía la persona real.'; return; }
      if (texto.value.trim().length < 3) { estado.textContent = 'Cuenta en una frase qué ha pasado.'; texto.focus(); return; }
      enviar.disabled = true; estado.textContent = 'Enviando…';
      try {
        const r = await A.api('opinion', { metodo: 'POST', cuerpo: { tipo: datos.tipo, prioridad: datos.tipo === 'fallo' ? datos.prioridad : 'gris', texto: texto.value.trim(),
          esperaba: datos.tipo === 'fallo' ? esperaba.value.trim() : '', ruta, pantalla, ancho: innerWidth, alto: innerHeight, frescura: frescuraTexto(), captura: datos.captura || undefined } });
        zona.replaceChildren(h('div', { class: 'pila' },
          h('p', {}, h('b', {}, `Recibido (n.º ${r.id}).`), ` ${r.avisado ? 'Mili y Tomás lo tienen en #avisos-dirección.' : 'Queda guardado; Mili y Tomás lo ven en «Recibidos».'} Los rojos se contestan el mismo día.`),
          h('div', { class: 'fila' }, h('button', { type: 'button', class: 'bt', on: { click: () => elegir('mios') } }, 'Ver los míos'), h('button', { type: 'button', class: 'bt pri', on: { click: d.cerrar } }, 'Cerrar'))));
      } catch (err) { enviar.disabled = false; estado.textContent = `No se pudo enviar: ${err.message}`; }
    });
    f.append(
      h('div', { class: 'fila', role: 'group', 'aria-label': 'Tipo' }, tipoBt('fallo', 'Algo va mal', 'alert'), tipoBt('idea', 'Tengo una idea', 'spark')),
      h('label', { class: 'campo', for: 'op-texto' }, h('span', { class: 'campo-et' }, datos.tipo === 'fallo' ? 'Qué ha pasado' : 'La idea'), texto),
      datos.tipo === 'fallo' ? h('label', { class: 'campo', for: 'op-esperaba' }, h('span', { class: 'campo-et' }, 'Qué esperabas'), esperaba) : null,
      datos.tipo === 'fallo' ? h('div', { class: 'fila', role: 'group', 'aria-label': 'Prioridad' }, h('span', { class: 'campo-et' }, 'Prioridad'),
        prioBt('rojo', 'Rojo · no puedo trabajar'), prioBt('ambar', 'Ámbar · molesta'), prioBt('gris', 'Gris · detalle')) : null,
      miniatura,
      h('p', { class: 'opinion-meta' }, `Se guarda: la pantalla «${pantalla}» · ${est.real.alias || est.real.nombre} · ${innerWidth} px de ancho · la hora · ${frescuraTexto()}`),
      h('div', { class: 'fila' }, enviar, estado));
    return f;
  }
  elegir('enviar');
}

/** Lista de «Algo va mal / Tengo una idea». todas = Mili y Tomás («Recibidos»); si no, los propios. La puede montar
 *  Ajustes tal cual: import { vistaOpiniones } from '../ayudas.js' → vistaOpiniones({ api: ctx.api, todas: true, soloLectura }). */
export function vistaOpiniones({ api, todas = false, soloLectura = false } = {}) {
  const caja = h('div', { class: 'pila' }, h('p', { class: 'sub' }, 'Cargando…'));
  const hora = s => { try { return new Date(String(s).replace(' ', 'T') + 'Z').toLocaleString('es-ES', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }); } catch { return s; } };
  const chip = (c, t) => h('span', { class: `chip ${c}` }, t);
  api('opiniones').then(r => {
    const l = r.opiniones || [];
    const lista = todas ? l : l.filter(x => x.quien === A?.estado?.real?.id || !r.todas);
    if (!lista.length) { caja.replaceChildren(h('p', { class: 'sub' }, todas ? 'Nadie ha mandado nada todavía.' : 'Todavía no has mandado nada.')); return; }
    caja.replaceChildren(h('ul', { class: 'opiniones' }, lista.map(o => {
      const img = h('div', {});
      const estado = h('span', { class: 'sub', role: 'status' });
      const cambiar = est => api('opiniones/estado', { metodo: 'POST', cuerpo: { id: o.id, estado: est } })
        .then(() => { estado.textContent = est === 'resuelta' ? 'Marcada resuelta.' : 'Marcada vista.'; }).catch(e => { estado.textContent = e.message; });
      return h('li', {},
        h('div', { class: 'op-cab' },
          chip(o.tipo === 'fallo' ? (o.prioridad === 'rojo' ? 'rojo' : o.prioridad === 'ambar' ? 'ambar' : 'gris') : 'azul', o.tipo === 'fallo' ? `Algo va mal · ${o.prioridad}` : 'Idea'),
          h('b', {}, o.quien_alias), h('span', {}, `${hora(o.creada)} · «${o.pantalla || o.ruta || 'app'}» · ${o.ancho || '?'} px`), chip(o.estado === 'resuelta' ? 'verde' : 'gris', o.estado)),
        h('div', { class: 'op-txt' }, o.texto), o.esperaba ? h('div', { class: 'sub' }, `Esperaba: ${o.esperaba}`) : null,
        h('div', { class: 'fila' },
          o.ruta ? h('a', { class: 'bt mini', href: o.ruta }, 'Abrir esa pantalla') : null,
          o.tiene_captura ? h('button', { type: 'button', class: 'bt mini', on: { click: () => api(`opiniones/captura?id=${o.id}`).then(x => img.replaceChildren(h('img', { src: x.captura, alt: `Captura de ${o.quien_alias}` }))).catch(e => img.replaceChildren(h('span', { class: 'sub' }, e.message))) } }, 'Ver captura') : null,
          todas && r.todas && !soloLectura && o.estado !== 'resuelta' ? h('button', { type: 'button', class: 'bt mini', on: { click: () => cambiar('vista') } }, 'Vista') : null,
          todas && r.todas && !soloLectura && o.estado !== 'resuelta' ? h('button', { type: 'button', class: 'bt mini pri', on: { click: () => cambiar('resuelta') } }, 'Resuelta') : null,
          estado),
        img);
    })));
  }).catch(e => caja.replaceChildren(h('p', { class: 'sub' }, `No se pudo leer: ${e.message}`)));
  return caja;
}
