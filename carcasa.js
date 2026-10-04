// carcasa.js · capa visual de la carcasa (ola 0, 2-oct-2026). Fichero común: lo mantiene E0 / ola 0.
//
// Por qué un fichero aparte: app.js (identidad, menú, router, ⌘K) lo está tocando E0 a la vez. Para no pisarnos,
// esto NO cambia app.js: observa lo que app.js pinta y le añade lo visual:
//   · un icono a cada entrada del menú (ICONO_MODULO por id; si falta, el de su grupo),
//   · un icono a cada resultado de ⌘K (pantalla, cliente o persona),
//   · el avatar con iniciales de quien se está viendo (menú y barra superior),
//   · N12 (2-oct): el bloque plegable «Qué haría yo hoy aquí» arriba de cada pantalla que tenga consejos (lo oculta si no
//     hay nada útil) y «Qué hacer» en los vacíos, «Sin dato» y errores que no lo traen (piezas de ia_componentes.js),
//   · N15 (2-oct): la campana de avisos junto al avatar (/api/canales/campana de avisos.py): menciones, avisos con tu nombre
//     y el resumen diario. Mismas clases que el menú de la persona (yo-menu, yo-btn, yo-pop); solo tokens.
//   · 3-oct: botón «Pedir ayuda» en la cabecera de TODAS las pantallas (orden de escalado oficial, modulos/_escalar.js),
//     con la pantalla y el cliente de la ruta; y avisos del navegador (si la persona los activó en el chat) al refrescar la
//     campana: menciones, mensajes directos y peticiones de ayuda nuevas.
// Si un día app.js pinta los iconos él mismo, esto no duplica: solo actúa donde falta el <svg>.

import { h, icono, iniciales, ICONO_MODULO, ICONO_GRUPO, fechas, fechasDe } from './componentes.js';
import { MODULOS } from './modulos/indice.js';
import { bloqueConsejo, enriquecerErrores } from './modulos/ia_componentes.js';
import { abrirPedirAyuda, contextoActual } from './modulos/_escalar.js';

const porTitulo = new Map(MODULOS.map(m => [m.titulo, m]));
const porId = new Map(MODULOS.map(m => [m.id, m]));

function decorarMenu(nav) {
  agruparNavegacionRO(nav);
  for (const a of nav.querySelectorAll('a[data-id]')) {
    const prev = a.querySelector('.prev');
    if (prev && !prev.title) prev.title = prev.textContent === 'error' ? 'Error al cargar' : 'Previsto: todavía sin construir';
    if (a.firstElementChild?.matches('svg.i')) continue;
    const m = porId.get(a.dataset.id);
    a.prepend(icono(ICONO_MODULO[a.dataset.id] || ICONO_GRUPO[m?.grupo] || 'res'));
  }
}

function decorarPaleta(ul) {
  for (const li of ul.querySelectorAll('li[role=option]:not(.nada)')) {
    if (li.querySelector('.ico-c')) continue;
    const tipo = li.querySelector('.tipo')?.textContent || '';
    const texto = li.firstElementChild?.textContent || '';
    let ico = 'res';
    if (tipo.startsWith('Pantalla')) { const m = porTitulo.get(texto); ico = ICONO_MODULO[m?.id] || ICONO_GRUPO[m?.grupo] || 'res'; }
    else if (/cliente/i.test(tipo)) ico = 'cli';
    else if (/persona/i.test(tipo)) ico = 'persona';
    li.prepend(Object.assign(document.createElement('span'), { className: 'ico-c' }));
    li.firstElementChild.append(icono(ico));
  }
}

function decorarYo() {
  const alias = document.getElementById('quien')?.textContent || '';
  if (!alias || alias === '…') return;
  // nombre completo si app.js lo expone (window.RO, solo prototipo); si no, el alias
  const p = window.RO?.estado?.persona;
  const nombre = p && p.alias === alias && p.nombre ? p.nombre : alias;
  const ini = iniciales(nombre);
  for (const id of ['yo-av', 'av-top']) {
    const el = document.getElementById(id);
    if (el && el.textContent !== ini) { el.textContent = ini; el.title = nombre; }
  }
}

function observar(id, fn) {
  const el = document.getElementById(id);
  if (!el) return;
  fn(el);
  new MutationObserver(() => fn(el)).observe(el, { childList: true, subtree: true, characterData: true });
}

//418 · contraer el menú completo sólo en escritorio; no cambia el menú móvil ni sus accesos.
function iniciarMenuEscritorio418() {
  const app=document.querySelector('.app'),side=document.querySelector('.app > .side'),barra=document.querySelector('.topbar-in');
  if(!app||!side||!barra||typeof matchMedia!=='function')return null;
  const existente=document.getElementById('menu-escritorio-btn');if(existente)return existente;
  const escritorio=matchMedia('(min-width: 901px)');
  let plegado=false;try{plegado=localStorage.getItem('ro.menu.escritorio.plegado')==='1';}catch{/* preferencia opcional */}
  if(!side.id)side.id='menu-principal-escritorio';
  const texto=h('span',{class:'menu-escritorio-texto'},''),boton=h('button',{id:'menu-escritorio-btn',type:'button',class:'bt menu-escritorio-btn','aria-controls':side.id,'aria-expanded':'true'},icono('menu'),texto);
  barra.prepend(boton);
  const pintar=()=>{
    const contraido=escritorio.matches&&plegado;
    if(escritorio.matches)boton.hidden=false;
    if(contraido&&side.contains(document.activeElement))boton.focus();
    if(!escritorio.matches&&document.activeElement===boton)document.getElementById('menu-btn')?.focus();
    app.classList.toggle('menu-contraido',contraido);
    side.inert=contraido;
    if(contraido)side.setAttribute('aria-hidden','true');else side.removeAttribute('aria-hidden');
    boton.hidden=!escritorio.matches;
    const accion=contraido?'Expandir menú':'Contraer menú';
    texto.textContent=accion;boton.title=accion;boton.setAttribute('aria-label',accion);boton.setAttribute('aria-expanded',String(!contraido));
  };
  boton.addEventListener('click',()=>{
    if(!escritorio.matches)return;
    plegado=!plegado;try{localStorage.setItem('ro.menu.escritorio.plegado',plegado?'1':'0');}catch{/* sigue funcionando sin almacenamiento */}
    pintar();
  });
  if(escritorio.addEventListener)escritorio.addEventListener('change',pintar);else escritorio.addListener?.(pintar);
  pintar();return boton;
}

// ------------------------------------------------------------------ N12 · consejo por pantalla y «Qué hacer»
// Pide /api/ia/consejo (reglas, rápido) al cambiar de pantalla, persona o cliente; si hay IA y no es «ver como», pide
// también la versión redactada por la IA (POST) y la cambia cuando llega. Si el módulo repinta #main, vuelve a ponerlo.
const CON_CLIENTE = new Set(['ficha', 'en-rojo', 'captacion', 'seo-web', 'redes', 'clientes-nuevos', 'informe-cliente', 'paneles', 'dinero-cliente']);
const CONSEJO = { clave: null, r: null };

function rutaActual() {
  const [, id, ...resto] = (location.hash || '').replace(/^#/, '').split('?')[0].split('/');
  let cliente = null, puesto = null;
  try { cliente = CON_CLIENTE.has(id) && resto[0] ? decodeURIComponent(resto[0]) : null; } catch { cliente = null; }
  // V2-E (de V2-B): pestaña de puesto activa (#/mi-dia/<puesto>, Jerónimo: SEO / Ficha de Google) → &puesto= al consejo
  const misPuestos = window.RO?.estado?.persona?.puestos || [];
  if (!cliente && resto[0] && misPuestos.includes(resto[0])) puesto = resto[0];
  return { id, cliente, puesto, control: id === 'mi-dia' && resto[0] === 'control-cartera' };
}
function leerPlegado() {
  try { const v = localStorage.getItem('ro.consejo.plegado'); if (v !== null) return v === '1'; } catch { /* sin almacenamiento */ }
  return window.innerWidth < 640 || (window.RO?.estado?.persona?.puestos || []).some(p => ['operaciones', 'account', 'trafficker', 'jefa_publicidad'].includes(p));          // en el móvil, plegado de entrada: una línea con lo primero
}
function guardarPlegado(p) { try { localStorage.setItem('ro.consejo.plegado', p ? '1' : '0'); } catch { /* da igual */ } }
const quitarConsejo = () => document.querySelectorAll('#main [data-ia="consejo"]').forEach(x => x.remove());

function pintarConsejo(main) {
  const r = CONSEJO.r;
  if (!r) return;
  const hayModulo = [...main.children].some(x => !x.matches('.esqueleto, [data-ia="consejo"]'));
  if (hayModulo && !main.querySelector(':scope > [data-ia="consejo"]')) {
    const est = window.RO?.estado;
    const b = bloqueConsejo(r, {
      soloLectura: !!r.solo_lectura || est?.persona?.id !== est?.real?.id, plegado: rutaActual().control || leerPlegado(), alPlegar: guardarPlegado,
      alAccion: c => window.RO.api('acciones', { metodo: 'POST', cuerpo: {
        modulo: 'alertas', herramienta: 'app', tipo: c.accion.tipo, objeto: c.accion.objeto, cliente_id: c.cliente_id || null,
        texto: `Lo tengo: ${c.porque}`, vista_previa: { alerta: c.accion.objeto, motivo: c.porque, estado: 'lo_tengo', desde: 'consejo' } } }),
    });
    if (b) main.prepend(b);
  }
  enriquecerErrores(main, r.que_hacer);
}

async function consejo(main) {
  const RO = window.RO, est = RO?.estado;
  if (!RO?.api || !est?.servidor || !est.persona || !est.real) return;
  const { id, cliente, puesto, control } = rutaActual();
  if (!id || !document.querySelector(`#nav a[data-id="${CSS.escape(id)}"]`)) { CONSEJO.clave = null; CONSEJO.r = null; return; }
  const clave = `${est.real.id}|${est.persona.id}|${id}|${cliente || ''}|${puesto || ''}|${control ? 'control' : ''}`;
  if (CONSEJO.clave === clave) { pintarConsejo(main); return; }
  CONSEJO.clave = clave; CONSEJO.r = null; quitarConsejo();
  const q = `ia/consejo?pantalla=${encodeURIComponent(id)}${cliente ? `&cliente=${encodeURIComponent(cliente)}` : ''}${puesto ? `&puesto=${encodeURIComponent(puesto)}` : ''}`;
  try { CONSEJO.r = await RO.api(q); } catch { CONSEJO.r = { consejos: [], que_hacer: [] }; }
  if (CONSEJO.clave !== clave) return;
  pintarConsejo(main);
  if (CONSEJO.r?.ia?.conectada && !CONSEJO.r.solo_lectura && CONSEJO.r.consejos?.length) {
    RO.api('ia/consejo', { metodo: 'POST', cuerpo: { pantalla: id, cliente, ...(puesto ? { puesto } : {}) } })
      .then(r2 => { if (CONSEJO.clave === clave && r2?.origen === 'vivo') { CONSEJO.r = r2; quitarConsejo(); pintarConsejo(main); } })
      .catch(() => { /* se quedan las reglas */ });
  }
}

let _consejoPend = null, _cortadosPend = null;
function vigilarMain() {
  const main = document.getElementById('main');
  if (!main) return;
  new MutationObserver(() => {
    clearTimeout(_consejoPend); _consejoPend = setTimeout(() => consejo(main), 150);
    clearTimeout(_cortadosPend); _cortadosPend = setTimeout(titulosCortados, 400);
  }).observe(main, { childList: true, subtree: true });
  addEventListener('resize', () => { clearTimeout(_cortadosPend); _cortadosPend = setTimeout(titulosCortados, 400); });
}

// V3a (44 §0.7): todo texto cortado con «…» (por CSS o por line-clamp) lleva en el title el texto entero, para que se pueda
// leer al pasar el ratón (y los lectores de pantalla lo tengan). Solo donde de verdad se corta y no hay ya un title.
const CORTABLES = ['.tile .tx', '.tile .tt span', '.ind .umbral', '.topbar h1', '.topbar .sub', '.lista-i .t', '.selcli .t b', '.selcli .t span',
  '.contacto .main span', '.etapas > li span', '.pleg-movil .pm-t', '.pleg-movil .pm-r', '.periodo-movil .pm-txt', '.menu-elegir .bt b',
  '.paleta li > span', '.chip', '#main [style*="line-clamp"]', '#main [style*="ellipsis"]'].join(', ');
function titulosCortados() {
  for (const el of document.querySelectorAll(CORTABLES)) {
    const auto = el.dataset.tituloAuto === '1';
    if (el.title && !auto) continue;
    const cortado = el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1;
    const texto = (el.textContent || '').replace(/\s+/g, ' ').trim();
    if (cortado && texto) { if (el.title !== texto) { el.title = texto; el.dataset.tituloAuto = '1'; } }
    else if (auto) { el.removeAttribute('title'); delete el.dataset.tituloAuto; }
  }
}

// ------------------------------------------------------------------ N15 · campana de avisos en la cabecera
const CAMPANA = { caja: null, btn: null, pop: null, cuenta: null, datos: null, quien: null, reloj: null };
const ICONO_AVISO = { aviso: 'alert', escalado: 'flag', evento: 'campana', mencion: 'persona', directo: 'chat', ayuda: 'sube' };
const QUE_AVISO = { aviso: ' · con tu nombre', evento: ' · con tu nombre', escalado: ' · te sube a ti', directo: ' · mensaje directo', ayuda: ' · te pide ayuda' };
// V2-E: la hora y el día de los avisos con el calendario común (Madrid): «hoy, 9:40», «ayer, 18:02», «el jue 1, 10:15».
function horaCorta(iso) {
  if (!iso) return '';
  const s = String(iso), conZona = /T.*(Z|[+-]\d\d:?\d\d)$/.test(s) ? s : (/^\d{4}-\d\d-\d\d[ T]\d\d:\d\d/.test(s) ? s : null);
  if (!conZona) return '';
  const dia = fechas.relativo(conZona), hora = fechas.hora(conZona);
  return dia === 'hoy' ? hora : `${dia}, ${hora}`;
}

function pintarCampana() {
  const c = CAMPANA.datos;
  if (!CAMPANA.caja) return;
  const n = c ? c.nuevas || 0 : 0;
  CAMPANA.cuenta.textContent = n > 99 ? '99+' : String(n);
  CAMPANA.cuenta.hidden = !n;
  CAMPANA.btn.setAttribute('aria-label', c ? `Avisos: ${n} nuevos, ${c.menciones} menciones, ${c.avisos_para_ti} con tu nombre` : 'Avisos');
  if (CAMPANA.pop.hidden || !c) return;
  const lista = h('div', { style: { display: 'grid', gap: 'var(--s-1)', maxHeight: '360px', overflowY: 'auto' } },
    c.items.length ? c.items.slice(0, 12).map(x => h('a', { class: 'yo-pop-l', href: `#/chat-equipo/${encodeURIComponent(x.canal_id)}`,
      style: { display: 'grid', gridTemplateColumns: '20px minmax(0, 1fr)', gap: 'var(--s-2)', font: 'var(--t-cuerpo)', fontWeight: x.nueva ? '700' : '400', color: 'var(--ink)' },
      on: { click: () => cerrarCampana() } },
    h('span', { style: { color: x.tipo === 'aviso' || x.tipo === 'escalado' ? 'var(--bad)' : 'var(--accent)', display: 'inline-flex' } }, icono(ICONO_AVISO[x.tipo] || 'campana', { clase: 's' })),
    h('span', { style: { minWidth: '0', overflowWrap: 'anywhere' } }, x.texto,
      h('small', { style: { display: 'block', font: 'var(--t-meta)', color: 'var(--dim)', fontWeight: '400' } },
        `${x.canal} · ${horaCorta(x.hora)}${QUE_AVISO[x.tipo] || ' · te mencionan'}`))))
      : h('p', { style: { margin: '0', font: 'var(--t-meta)', color: 'var(--dim)' } }, 'Nada con tu nombre. Cuando te mencionen o te llegue un aviso, sale aquí.'));
  CAMPANA.pop.replaceChildren(...[
    h('div', { class: 'yo-pop-cab' }, h('b', {}, 'Avisos'), h('small', {}, `${c.no_leidos} sin leer · ${c.menciones} menciones · ${c.directos || 0} directos · ${c.avisos_para_ti} con tu nombre`)),
    c.resumen ? h('div', { style: { display: 'grid', gap: 'var(--s-1)', background: 'var(--card-2)', border: 'var(--borde-suave)', borderRadius: 'var(--r-m)', padding: 'var(--s-2) var(--s-3)' } },
      h('span', { class: 'yo-pop-t' }, 'Tu resumen de hoy'), h('span', { style: { font: 'var(--t-cuerpo)', color: 'var(--ink)', whiteSpace: 'pre-wrap' } }, c.resumen.texto)) : null,
    lista,
    h('a', { class: 'yo-pop-l', href: '#/chat-equipo', on: { click: () => cerrarCampana() } }, 'Abrir canales y preferencias')].filter(Boolean));
}

async function refrescarCampana() {
  const RO = window.RO, est = RO?.estado;
  if (!RO?.api || !est?.servidor || !CAMPANA.caja) return;
  try { CAMPANA.datos = await RO.api('canales/campana'); } catch { CAMPANA.datos = null; }
  pintarCampana();
  avisarNavegador(CAMPANA.datos);
}

// 3-oct · avisos del navegador: solo si la persona los activó (chat › «Tus avisos») y el navegador los permite; nunca en
// «ver como». Uno por mensaje nuevo (el id más alto ya avisado se guarda en este navegador), como mucho 3 de golpe.
function avisarNavegador(c) {
  const est = window.RO?.estado;
  if (!c || !est?.persona || est.persona.id !== est.real?.id || typeof Notification === 'undefined' || Notification.permission !== 'granted') return;
  let activo = false, visto = 0;
  const k = `ro.notif.${est.persona.id}`, kv = `ro.notif.visto.${est.persona.id}`;
  try { activo = localStorage.getItem(k) === '1'; visto = Number(localStorage.getItem(kv) || 0); } catch { return; }
  if (!activo) return;
  const nuevos = (c.items || []).filter(x => x.nueva && x.id > visto && ['mencion', 'directo', 'ayuda', 'aviso', 'escalado'].includes(x.tipo));
  const max = Math.max(visto, ...(c.items || []).map(x => x.id || 0));
  try { localStorage.setItem(kv, String(max)); } catch { /* nada */ }
  if (!visto) return;                          // la primera vez solo apunta dónde está: no avisa de lo viejo
  for (const x of nuevos.slice(0, 3)) {
    try {
      const n = new Notification(x.tipo === 'ayuda' ? 'Te piden ayuda' : x.tipo === 'directo' ? `Mensaje de ${(est.datos?.personas || []).find(q => q.id === x.quien)?.alias || 'alguien del equipo'}` : `Ranking Online · ${x.canal}`,
        { body: String(x.texto || '').slice(0, 140), tag: `ro-${x.id}` });
      n.onclick = () => { window.focus(); location.hash = `#/chat-equipo/${encodeURIComponent(x.canal_id)}`; n.close(); };
    } catch { /* el navegador no deja */ }
  }
}

// ------------------------------------------------------------------ 3-oct · «Pedir ayuda» en la cabecera de todas las pantallas
function botonAyuda() {
  const est = window.RO?.estado;
  if (!est?.servidor || document.getElementById('ayuda-btn')) return;
  const ancla = document.getElementById('opinion-btn') || document.getElementById('buscar');
  if (!ancla) return;
  const b = h('button', { type: 'button', class: 'bt icono', id: 'ayuda-btn', 'aria-haspopup': 'dialog', 'aria-label': 'Pedir ayuda o escalar a quien toca', title: 'Pedir ayuda / Escalar' }, icono('sube'));
  b.addEventListener('click', () => {
    const e = window.RO?.estado;
    const ctx = contextoActual();
    const cli = ctx.cliente_id ? (e?.datos?.clientes || []).find(c => c.id === ctx.cliente_id) : null;
    abrirPedirAyuda({ api: window.RO.api, soloLectura: e?.persona?.id !== e?.real?.id, contexto: { ...ctx, cliente_id: cli ? cli.id : null, cliente: cli?.nombre || null } });
  });
  ancla.before(b);
}

function cerrarCampana() {
  if (!CAMPANA.pop || CAMPANA.pop.hidden) return;
  CAMPANA.pop.hidden = true;
  CAMPANA.btn.setAttribute('aria-expanded', 'false');
}

async function abrirCampana() {
  // En el móvil la cabecera es estrecha: la ventana va a lo ancho, con margen a los lados.
  Object.assign(CAMPANA.pop.style, innerWidth < 640
    ? { position: 'fixed', left: 'var(--s-4)', right: 'var(--s-4)', top: '72px', width: 'auto', maxWidth: 'none' }
    : { position: '', left: '', right: '', top: '', width: '', maxWidth: '' });
  CAMPANA.pop.hidden = false;
  CAMPANA.btn.setAttribute('aria-expanded', 'true');
  await refrescarCampana();
  const est = window.RO?.estado, c = CAMPANA.datos;
  // Abrir la campana la da por vista (no en «ver como», que es solo lectura).
  if (c && c.nuevas && est?.persona?.id === est?.real?.id) {
    window.RO.api('canales/campana_vista', { metodo: 'POST', cuerpo: { hasta_id: c.hasta_id } })
      .then(() => { c.nuevas = 0; c.items.forEach(x => { x.nueva = false; }); if (c.resumen) c.resumen.nuevo = false; CAMPANA.cuenta.hidden = true; })
      .catch(() => { /* se queda como estaba */ });
  }
}

function iniciarCampana() {
  const est = window.RO?.estado;
  const yo = document.getElementById('yo-menu');
  if (!est?.servidor || !yo) return;
  if (!CAMPANA.caja) {
    CAMPANA.cuenta = h('span', { hidden: true, 'aria-hidden': 'true', style: { position: 'absolute', top: '0', right: '0', font: 'var(--t-meta)', fontWeight: '700', lineHeight: '16px',
      background: 'var(--bad)', color: 'var(--card)', borderRadius: 'var(--r-full)', padding: '0 var(--s-1)', minWidth: '16px', textAlign: 'center', fontVariantNumeric: 'tabular-nums' } });
    CAMPANA.btn = h('button', { class: 'yo-btn', type: 'button', id: 'campana-btn', 'aria-haspopup': 'true', 'aria-expanded': 'false', 'aria-controls': 'campana-pop', 'aria-label': 'Avisos',
      style: { position: 'relative', width: '40px', justifyContent: 'center' },
      on: { click: e => { e.stopPropagation(); CAMPANA.pop.hidden ? abrirCampana() : cerrarCampana(); } } }, icono('campana'), CAMPANA.cuenta);
    CAMPANA.pop = h('div', { class: 'yo-pop', id: 'campana-pop', hidden: true, role: 'dialog', 'aria-label': 'Avisos' });
    CAMPANA.caja = h('div', { class: 'yo-menu', id: 'campana' }, CAMPANA.btn, CAMPANA.pop);
    yo.before(CAMPANA.caja);
    // En el móvil la cabecera va justa (con «Actualizar» no cabía por 11 px): campana de 32 px y más pegada al avatar.
    const estrecha = matchMedia('(max-width: 640px)');
    const ajustar = () => { CAMPANA.btn.style.width = estrecha.matches ? 'var(--s-8)' : '40px'; CAMPANA.caja.style.marginLeft = estrecha.matches ? 'calc(-1 * var(--s-2))' : ''; };
    estrecha.addEventListener('change', ajustar);
    ajustar();
    document.addEventListener('click', e => { if (!CAMPANA.caja.contains(e.target)) cerrarCampana(); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && !CAMPANA.pop.hidden) { cerrarCampana(); CAMPANA.btn.focus(); } });
    window.addEventListener('ro:avisos', refrescarCampana);
    CAMPANA.reloj = setInterval(refrescarCampana, 60000);
  }
  const quien = `${est.real?.id}|${est.persona?.id}`;
  if (CAMPANA.quien !== quien) { CAMPANA.quien = quien; refrescarCampana(); }
}

// ------------------------------------------------------------------ Mi perfil (3-oct) · entrada en el menú del avatar
// «Mi perfil» bajo el nombre: nombre, puesto, jefe y zona horaria (modulos/mi_perfil.js, #/mi-perfil). Enseña la ciudad y la
// hora de quien se está viendo para que nadie se líe con la diferencia con Madrid.
function entradaPerfil() {
  const cab = document.querySelector('#yo-pop .yo-pop-cab');
  if (!cab) return;
  let a = document.getElementById('yo-pop-perfil');
  if (!a) {
    a = h('a', { class: 'yo-pop-l', id: 'yo-pop-perfil', href: '#/mi-perfil',
      on: { click: () => { const pop = document.getElementById('yo-pop'); if (pop) pop.hidden = true; document.getElementById('yo-btn')?.setAttribute('aria-expanded', 'false'); } } },
    icono('persona', { clase: 's' }), ' Mi perfil y zona horaria', h('small', { id: 'yo-pop-perfil-z', style: { display: 'block', font: 'var(--t-meta)', color: 'var(--dim)', fontWeight: '400' } }));
    cab.after(a);
  }
  const z = window.RO?.estado?.persona?.zona;
  const t = document.getElementById('yo-pop-perfil-z');
  if (t && z) t.textContent = `${z.split('/').pop().replace(/_/g, ' ')} · ${fechasDe(z).hora(new Date().toISOString())} ahora`;
}

observar('nav', decorarMenu);
iniciarMenuEscritorio418();
observar('paleta-lista', decorarPaleta);
observar('vercomo', unificarVerComoRO);
observar('quien', () => { decorarYo(); iniciarCampana(); entradaPerfil(); botonAyuda(); });
document.getElementById('yo-btn')?.addEventListener('click', () => setTimeout(entradaPerfil, 0));
vigilarMain();

// Agrupación visual: sólo enlaces ya autorizados por app.js; nunca crea rutas ni permisos.
function agruparNavegacionRO(nav) {
  const puestos = window.RO?.estado?.persona?.puestos;
  const prioridades = {
    // Prioridades por función canónica: seleccionar sólo de los enlaces que ya pintó app.js.
    direccion: ['operaciones', 'mi-dia', 'en-rojo', 'decisiones', 'panel-direccion', 'finanzas', 'ventas-ro', 'produccion', 'personas', 'horas', 'alertas', 'chat-equipo'],
    finanzas_direccion: ['finanzas', 'dinero-cliente', 'mi-dia', 'en-rojo', 'decisiones', 'personas', 'agenda', 'chat-equipo', 'alertas', 'envios', 'avisos-automaticos', 'reuniones'],
    administracion: ['finanzas', 'dinero-cliente', 'mi-dia', 'clientes-nuevos', 'ficha', 'en-rojo', 'agenda', 'alertas', 'chat-equipo', 'decisiones', 'envios', 'avisos-automaticos'],
    rrhh: ['personas', 'horas', 'ajustes', 'mi-dia', 'mi-trabajo', 'produccion', 'agenda', 'alertas', 'chat-equipo', 'decisiones', 'reuniones', 'incidencias'],
    seo: ['seo-web', 'mi-dia', 'mi-trabajo', 'prioridades-cliente', 'ficha', 'en-rojo', 'informe-cliente', 'produccion', 'horas', 'alertas', 'chat-equipo', 'paneles'],
    jefa_seo: ['seo-web', 'mi-dia', 'mi-trabajo', 'prioridades-cliente', 'ficha', 'en-rojo', 'produccion', 'horas', 'personas', 'bandeja', 'alertas', 'chat-equipo'],
    ficha_google: ['seo-web', 'mi-dia', 'mi-trabajo', 'ficha', 'en-rojo', 'informe-cliente', 'produccion', 'horas', 'alertas', 'chat-equipo', 'paneles', 'agenda'],
    web: ['seo-web', 'mi-dia', 'mi-trabajo', 'produccion', 'ficha', 'en-rojo', 'horas', 'alertas', 'chat-equipo', 'paneles', 'agenda', 'incidencias'],
    produccion: ['produccion', 'mi-trabajo', 'mi-dia', 'captacion', 'redes', 'ficha', 'en-rojo', 'horas', 'alertas', 'chat-equipo', 'agenda', 'incidencias'],
    especialista_ghl: ['salud-crm', 'mi-dia', 'mi-trabajo', 'prioridades-cliente', 'ficha', 'clientes-nuevos', 'bandeja', 'en-rojo', 'produccion', 'alertas', 'chat-equipo', 'paneles'],
    jefa_crm: ['salud-crm', 'mi-dia', 'mi-trabajo', 'prioridades-cliente', 'prospeccion', 'ficha', 'clientes-nuevos', 'en-rojo', 'produccion', 'horas', 'alertas', 'chat-equipo'],
    operaciones: ['operaciones', 'mi-dia', 'prioridades-cliente', 'en-rojo', 'mi-trabajo', 'bandeja', 'alertas', 'chat-equipo', 'produccion', 'personas', 'agenda', 'decisiones'],
    account: ['operaciones', 'mi-dia', 'prioridades-cliente', 'en-rojo', 'bandeja', 'ficha', 'clientes-nuevos', 'mi-trabajo', 'alertas', 'chat-equipo', 'reuniones', 'agenda'],
    trafficker: ['mi-dia', 'prioridades-cliente', 'captacion', 'en-rojo', 'ficha', 'mi-trabajo', 'bandeja', 'alertas', 'chat-equipo', 'agenda', 'creativos', 'paneles'],
    jefa_publicidad: ['mi-dia', 'prioridades-cliente', 'captacion', 'en-rojo', 'ficha', 'mi-trabajo', 'bandeja', 'alertas', 'chat-equipo', 'produccion', 'agenda', 'personas']
  };
  const roles = Array.isArray(puestos) ? puestos.filter(p => typeof p === 'string' && Object.hasOwn(prioridades, p)) : [];
  if (!roles.length) return;
  const existente = nav.querySelector('[data-ro-mas]');
  if (existente) { revelarActualRO(nav); return; }
  // Respetar una agrupación Más ya instalada por otro renderer.
  if ([...nav.querySelectorAll('summary')].some(s => /^Más(?:\s|$)/.test(s.textContent.trim()))) return;
  const enlaces = [...nav.querySelectorAll('a[data-id]')];
  if (enlaces.length <= 12) return;
  const preferidos = new Set(roles.flatMap(p => prioridades[p]));
  const principales = new Set([...new Set([...enlaces.filter(a => preferidos.has(a.dataset.id)), ...enlaces])].slice(0, 12));
  const mas = h('details', { class: 'nav-mas-ro', 'data-ro-mas': '1' }, h('summary', {}, 'Más'));
  for (const grupo of [...nav.children]) {
    const secundarios = [...grupo.querySelectorAll('a[data-id]')].filter(a => !principales.has(a));
    if (!secundarios.length) continue;
    const titulo = grupo.querySelector('.ngt');
    const label = titulo?.textContent || 'Pantallas';
    const cab = h('div', { class: 'ngt', id: `ro-mas-${mas.children.length}` }, label);
    const caja = h('div', { class: 'ng', role: 'group', 'aria-labelledby': cab.id }, cab);
    secundarios.forEach(a => caja.append(a));
    mas.append(caja);
    if (!grupo.querySelector('a')) grupo.hidden = true;
  }
  nav.append(mas);
  revelarActualRO(nav);
}
function revelarActualRO(nav) {
  const mas = nav?.querySelector('[data-ro-mas]');
  if (mas?.querySelector('a[aria-current]')) mas.open = true;
}
addEventListener('hashchange', () => setTimeout(() => revelarActualRO(document.getElementById('nav')), 0));

// Una opción por identidad; conserva las etiquetas de todos sus puestos y la selección.
function unificarVerComoRO(caja) {
  const sel = caja.querySelector('#vercomo-sel');
  if (!sel) return;
  const valor = sel.value, vistos = new Map();
  for (const opcion of [...sel.options]) {
    const previa = vistos.get(opcion.value);
    if (!previa) { vistos.set(opcion.value, opcion); continue; }
    const puesto = opcion.textContent.split(' — ').slice(1).join(' — ');
    if (puesto && !previa.textContent.split(' — ').slice(1).join(' — ').split(' · ').includes(puesto)) previa.textContent += ` · ${puesto}`;
    opcion.remove();
  }
  for (const grupo of [...sel.querySelectorAll('optgroup')]) if (!grupo.children.length) grupo.remove();
  sel.value = valor;
}
