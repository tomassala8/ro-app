// modulos/mi_perfil.js · «Mi perfil» (3-oct-2026, encargo de Tomás: «que el equipo pueda actualizar su timezone»).
// Ruta #/mi-perfil (la tuya) y #/mi-perfil/<persona> (la de alguien a quien puedes cambiarla o ver). No sale en el menú:
// se llega desde el menú del avatar (carcasa.js) y con ⌘K.
//
// Cada persona ve su nombre, puesto, jefe y ZONA HORARIA y la cambia ella misma: lista corta de las zonas reales del equipo
// y buscador de todas las zonas IANA. La de otra persona solo la cambian su jefe directo, Mili y Tomás (a quien tiene
// puesto de mando, solo Tomás). Regla: reglas_permisos.json → zona_horaria. En «ver como» no se escribe nada.
// Servidor: GET /api/perfil?id= y POST /api/perfil/zona (altas_personas.py → perfil / cambiar_zona; historial + rastro).
//
// Qué cambia con la zona (ver LEEME › Mi perfil): las horas que se ENSEÑAN «en tu hora» (ctx.zona, ctx.fechasDe(zona)),
// la hora a la que llega tu resumen diario de la campana y el día de trabajo de tus registros de Horas. Qué NO cambia:
// «hoy», vencidas, «esta semana», plazos y meses siguen el calendario de la agencia en Madrid (V2-E).

import { h, panel, vacio, chipEstado, icono, iniciales, avisoFlotante, botonConfirmar, tablaApilable, fechasDe, fechas } from '../componentes.js';

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

export const ID = 'mi-perfil';

// Nombre corto en castellano de las zonas del equipo; el resto, la ciudad del nombre IANA («America/New_York» → «New York»).
const CIUDAD = {
  'Europe/Madrid': 'Madrid', 'Atlantic/Canary': 'Canarias', 'America/Caracas': 'Caracas', 'America/Bogota': 'Bogotá',
  'America/Argentina/Buenos_Aires': 'Buenos Aires', 'America/Mexico_City': 'Ciudad de México', 'America/Lima': 'Lima',
  'America/Santiago': 'Santiago de Chile', 'America/Montevideo': 'Montevideo', 'America/Asuncion': 'Asunción',
  'America/Santo_Domingo': 'Santo Domingo', 'Asia/Makassar': 'Bali',
};
export const ciudad = z => CIUDAD[z] || String(z || 'Europe/Madrid').split('/').pop().replace(/_/g, ' ');

/** Hora de ahora en una zona («21:14») y su día (AAAA-MM-DD). */
function ahoraEn(z) {
  const iso = new Date().toISOString();
  const f = fechasDe(z);
  return { hora: f.hora(iso), dia: f.dia(iso) };
}

/** «21:14 (Caracas) · Madrid: 03:14 del sáb 4» — para no liarse con la diferencia. */
export function relojTexto(z, { tu = 'Tu hora' } = {}) {
  const yo = ahoraEn(z), md = ahoraEn('Europe/Madrid');
  if (z === 'Europe/Madrid') return `${tu} ahora: ${yo.hora} (Madrid)`;
  const dMd = md.dia !== yo.dia ? ` del ${fechas.diaSemana(md.dia)} ${Number(md.dia.slice(8, 10))}` : '';
  return `${tu} ahora: ${yo.hora} (${ciudad(z)}) · Madrid: ${md.hora}${dMd}`;
}

/** Para quien quiera enseñar la zona de alguien en otra pantalla (Personas): «Caracas · 21:14 ahora». */
export function lineaZona(ctx, pid) {
  const z = ctx.zona(pid);
  return h('span', { class: 'sub' }, icono('clock', { clase: 's' }), ` ${ciudad(z)} · ${ahoraEn(z).hora} ahora`);
}

const norma = t => String(t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/_/g, ' ');

/** Pone la zona nueva en lo que ya tiene la carcasa en memoria: ctx.zona(), Horas y la cabecera la usan al momento. */
function aplicarEnMemoria(ctx, pid, persona) {
  const listas = [ctx.datos?.personas, window.RO?.estado?.crudo?.personas, window.RO?.estado?.datos?.personas];
  const objetos = new Set([ctx.persona, ctx.real, window.RO?.estado?.persona, window.RO?.estado?.real]);
  for (const l of listas) for (const x of l || []) objetos.add(x);
  for (const x of objetos) {
    if (x && x.id === pid) { x.zona = persona.zona; if (persona.pais) x.pais = persona.pais; x.zona_fuente = persona.zona_fuente; x.zona_a_confirmar = false; }
  }
  window.dispatchEvent(new Event('ro:avisos'));   // la campana vuelve a pedir el resumen (a su hora nueva)
}

function cabecera(r, ctx) {
  const p = r.persona;
  const reloj = h('p', { 'aria-live': 'off', style: { margin: '0', font: 'var(--t-h2)', color: 'var(--ink)', fontVariantNumeric: 'tabular-nums' } });
  const pintar = () => { reloj.textContent = relojTexto(p.zona, { tu: r.propia ? 'Tu hora' : 'Su hora' }); };
  pintar();
  const t = setInterval(() => { if (!reloj.isConnected) clearInterval(t); else pintar(); }, 30000);
  return h('div', { class: 'detalle-cab' },
    h('span', { class: 'av', 'aria-hidden': 'true', style: { width: 'var(--s-12)', height: 'var(--s-12)', font: 'var(--t-h2)' } }, iniciales(p.nombre || p.alias)),
    h('div', { style: { display: 'grid', gap: 'var(--s-1)', minWidth: '0', flex: '1 1 240px' } },
      h('h2', { style: { margin: '0', overflowWrap: 'anywhere' } }, p.nombre || p.alias),
      h('span', { class: 'sub' }, [p.puestos.join(' · ') || p.rol || 'Sin puesto', p.jefe ? `jefe: ${p.jefe.alias}` : 'sin jefe (dirección)'].join(' · ')),
      reloj),
    p.zona_a_confirmar ? chipEstado('ambar', 'zona sin confirmar') : chipEstado('verde', ciudad(p.zona)));
}

function panelZona(r, ctx, repintar) {
  const p = r.persona;
  const quien = r.propia ? 'tu' : 'su';
  let elegida = p.zona;
  const cuerpo = h('div', { class: 'cuerpo pila' });
  const vista = h('p', { class: 'sub', style: { margin: '0' } });
  const ponerVista = () => {
    vista.textContent = elegida === p.zona ? `Es ${quien} zona ahora (${p.zona}).` : `Con ${ciudad(elegida)} (${elegida}): ${relojTexto(elegida, { tu: r.propia ? 'tu hora' : 'su hora' })}.`;
    for (const b of cuerpo.querySelectorAll('button[data-zona]')) {
      const si = b.dataset.zona === elegida;
      b.setAttribute('aria-pressed', String(si));
      Object.assign(b.style, { background: si ? 'var(--accent-soft)' : '', borderColor: si ? 'var(--accent)' : '', color: si ? 'var(--accent-ink)' : '' });
    }
    guardar.hidden = elegida === p.zona;
  };
  const elegir = z => { elegida = z; ponerVista(); };
  const botonZona = (z, texto) => h('button', { type: 'button', class: 'bt', 'data-zona': z, 'aria-pressed': 'false', disabled: !r.puede || null,
    style: { justifyContent: 'space-between', gap: 'var(--s-2)', minHeight: 'var(--s-10)', height: 'auto', width: '100%', textAlign: 'left' }, on: { click: () => elegir(z) } },
  h('span', { style: { minWidth: '0', overflowWrap: 'anywhere', whiteSpace: 'normal' } }, texto), h('span', { class: 'sub', style: { fontVariantNumeric: 'tabular-nums', flex: 'none' } }, ahoraEn(z).hora));
  const corta = r.zonas_equipo.some(z => z.id === p.zona) ? r.zonas_equipo : [{ id: p.zona, texto: `${ciudad(p.zona)} (${quien} zona)` }, ...r.zonas_equipo];
  const lista = h('div', { role: 'group', 'aria-label': 'Zonas del equipo', style: { display: 'grid', gap: 'var(--s-2)', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 240px), 1fr))' } },
    corta.map(z => botonZona(z.id, z.texto)));
  // Buscador de todas las zonas IANA (en inglés, como las escribe el sistema: Tokyo, New_York, Makassar…).
  const resultados = h('div', { role: 'group', 'aria-label': 'Zonas encontradas', style: { display: 'grid', gap: 'var(--s-2)', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 240px), 1fr))' } });
  const buscar = h('input', { type: 'search', placeholder: 'Otra zona: escribe la ciudad en inglés (Tokyo, New York, Makassar…)', 'aria-label': 'Buscar zona horaria', disabled: !r.puede || null,
    on: { input: e => {
      const q = norma(e.target.value).trim();
      const hits = q.length < 2 ? [] : r.todas.filter(z => norma(z).includes(q) || norma(ciudad(z)).includes(q)).slice(0, 8);
      resultados.replaceChildren(...(q.length >= 2 && !hits.length ? [h('p', { class: 'sub', style: { margin: '0' } }, 'Ninguna zona con ese nombre. Prueba con la capital del país en inglés.')] : hits.map(z => botonZona(z, z.replace(/_/g, ' ')))));
      ponerVista();
    } } });
  const guardar = h('div', { hidden: true });
  guardar.append(botonConfirmar({ texto: 'Guardar zona', soloLectura: ctx.soloLectura,
    pregunta: '¿Guardar la zona?', confirmar: 'Sí, guardar', cancelar: 'No',
    alConfirmar: async () => {
      const res = await ctx.api('perfil/zona', { metodo: 'POST', cuerpo: { id: p.id, zona: elegida } });
      aplicarEnMemoria(ctx, p.id, res.persona);
      avisoFlotante(`Zona guardada: ${ciudad(res.persona.zona)}`);
      setTimeout(repintar, 600);
      return `Guardada: ${ciudad(res.persona.zona)}. Ya se aplica.`;
    } }));
  // La pregunta del botón se escribe al pulsarlo con la zona elegida en ese momento.
  guardar.addEventListener('click', () => {
    const pr = guardar.querySelector('.preg');
    if (pr) pr.textContent = `¿Cambiar ${r.propia ? 'tu' : `la de ${p.alias}`} zona a ${ciudad(elegida)}?`;
  });
  if (ctx.soloLectura) cuerpo.append(h('p', { class: 'sub', style: { margin: '0' } }, icono('ojo', { clase: 's' }), ' Estás en «ver como»: puedes mirar, pero no se guarda nada.'));
  if (!r.puede) cuerpo.append(h('p', { class: 'sub', style: { margin: '0' } }, icono('candado', { clase: 's' }), ` ${r.motivo}`));
  cuerpo.append(lista, h('label', { class: 'campo' }, h('span', { class: 'campo-et' }, '¿No está? Busca cualquier zona'), buscar), resultados, vista, guardar);
  ponerVista();
  return panel({ titulo: r.propia ? 'Tu zona horaria' : `Zona horaria de ${p.alias}`, icono: 'globe',
    sub: r.propia ? 'Elígela tú: sale en tu reloj, en tu resumen diario y en el día de tus horas. Queda guardado quién la cambia y cuándo.'
      : `${p.alias} también la puede cambiar. Queda guardado quién la cambia y cuándo.` }, cuerpo);
}

function panelQueCambia(r) {
  const tu = r.propia ? 'tu' : 'su', tus = r.propia ? 'tus' : 'sus';
  const fila = (ok, texto) => h('li', { style: { display: 'grid', gridTemplateColumns: 'var(--s-5) minmax(0, 1fr)', gap: 'var(--s-2)', alignItems: 'start' } },
    h('span', { style: { color: ok ? 'var(--good)' : 'var(--dim)', display: 'inline-flex' } }, icono(ok ? 'ok' : 'cerrar', { clase: 's' })), h('span', {}, texto));
  const ul = (...xs) => h('ul', { style: { listStyle: 'none', margin: '0', padding: '0', display: 'grid', gap: 'var(--s-2)' } }, xs);
  return panel({ titulo: 'Qué cambia con la zona', icono: 'info' },
    h('div', { class: 'cuerpo dos iguales' },
      h('div', { class: 'pila' }, h('b', {}, 'Va a ' + tu + ' hora'),
        ul(fila(true, `El reloj de arriba y las horas que se enseñan «en ${tu} hora».`),
          fila(true, `El resumen diario de la campana: llega a ${tu} hora del resumen en ${tu} zona.`),
          fila(true, `El día de trabajo de ${tus} registros de Horas (lo de las 23:30 cuenta para ese día, no para el siguiente).`))),
      h('div', { class: 'pila' }, h('b', {}, 'Sigue en hora de Madrid'),
        ul(fila(false, '«Hoy», «ayer», «esta semana» y lo que vence: el calendario de la agencia es uno para todos.'),
          fila(false, 'Plazos de alertas, informes del día 5, cierre de mes y el mes de las horas (como ClickUp).'),
          fila(false, 'La hora de los datos («Datos de las 23:14») y las horas del rastro.')))));
}

function panelResumen(r, ctx) {
  const x = r.resumen;
  if (!x) return null;
  const p = r.persona;
  const [hh, mm] = String(x.hora_resumen || '08:30').split(':').map(Number);
  // La hora del resumen en la zona de la persona, pasada a Madrid (para quien lo mira desde España).
  let enMadrid = '';
  if (p.zona !== 'Europe/Madrid') {
    const base = new Date();
    const f = new Intl.DateTimeFormat('en-GB', { timeZone: p.zona, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
    const [ah, am] = f.format(base).split(':').map(Number);
    const objetivo = new Date(base.getTime() + (((hh * 60 + mm) - (ah * 60 + am)) * 60000));
    enMadrid = ` (${fechasDe('Europe/Madrid').hora(objetivo.toISOString())} en Madrid)`;
  }
  const veChat = ctx.veModulo('chat-equipo');
  return panel({ titulo: r.propia ? 'Tu resumen diario y avisos' : `Resumen diario de ${p.alias}`, icono: 'campana',
    verTodo: r.propia && veChat ? { texto: 'Cambiar hora y canales', href: '#/chat-equipo' } : null },
  h('div', { class: 'cuerpo pila' },
    h('p', { style: { margin: '0' } }, `Llega a las ${x.hora_resumen} de ${ciudad(p.zona)}${enMadrid}.`),
    h('p', { class: 'sub', style: { margin: '0' } }, x.silenciados ? `${x.silenciados} ${x.silenciados === 1 ? 'canal silenciado' : 'canales silenciados'}: no cuentan en la campana.` : 'Ningún canal silenciado.'),
    r.propia ? null : h('p', { class: 'sub', style: { margin: '0' } }, 'La hora y los canales los elige cada persona en Chat del equipo.')));
}

function panelEquipo(r, ctx) {
  if (!r.equipo?.length) return null;
  const filas = r.equipo.map(x => ({ ...x, _hora: ahoraEn(x.zona).hora }));
  return panel({ titulo: r.equipo.some(x => x.jefe?.id === ctx.persona.id) && !r.equipo.every(x => x.jefe?.id === ctx.persona.id) ? 'Zonas del equipo' : 'Tu equipo', icono: 'users',
    sub: 'Su zona y su hora ahora. Puedes cambiarla si se equivocan; queda guardado que fuiste tú.' },
  h('div', { class: 'cuerpo' }, tablaApilable({ filas,
    columnas: [
      { clave: 'alias', titulo: 'Persona', principal: true, celda: x => h('a', { href: `#/mi-perfil/${encodeURIComponent(x.id)}` }, x.alias) },
      { clave: 'zona', titulo: 'Zona', celda: x => [ciudad(x.zona), x.zona_a_confirmar ? h('span', { class: 'sub' }, ' · sin confirmar') : null] },
      { clave: '_hora', titulo: 'Su hora ahora', num: true },
      { clave: 'jefe', titulo: 'Jefe', celda: x => x.jefe?.alias || '—' },
    ] })));
}

function panelCambios(r, ctx) {
  if (!r.cambios?.length) return null;
  return panel({ titulo: 'Últimos cambios de zona', icono: 'hist', sub: 'Del historial (no se borra). Hora de Madrid.' },
    h('div', { class: 'cuerpo' }, h('ul', { style: { listStyle: 'none', margin: '0', padding: '0', display: 'grid', gap: 'var(--s-2)' } },
      r.cambios.slice(0, 12).map(c => h('li', { style: { display: 'grid', gap: 'var(--s-1)' } },
        h('span', {}, `${ctx.nombre(c.persona_id)}: ${ciudad(c.antes)} → ${ciudad(c.despues)}`),
        h('span', { class: 'sub' }, `${fechas.relativo(c.cuando)}, ${fechas.hora(c.cuando)} · lo cambió ${c.quien === c.persona_id ? 'ella misma' : ctx.nombre(c.quien)}`))))));
}

async function render(cont, ctx) {
    vigilarCortes(cont);
    cont.classList.add('pila');
    if (!ctx.servidor) {
      cont.append(vacio({ icono: 'alert', titulo: 'Mi perfil necesita el servidor', texto: 'Arranca la app con servir.py para ver y cambiar tu zona horaria.', quien: 'Tomás' }));
      return;
    }
    const pid = ctx.params[0] || '';
    let r;
    try { r = await ctx.api(`perfil${pid ? `?id=${encodeURIComponent(pid)}` : ''}`); }
    catch (e) {
      cont.append(vacio({ icono: 'candado', borde: true, titulo: e.status === 403 ? 'Este perfil no es tuyo' : 'No se pudo abrir el perfil', texto: e.message,
        quien: 'Mili' }));
      return;
    }
    const repintar = () => { cont.replaceChildren(); render(cont, ctx); };
    ctx.titulo(r.propia ? 'Mi perfil' : `Perfil de ${r.persona.alias}`, r.propia ? 'Tu nombre, tu puesto, tu jefe y tu zona horaria.' : `Su puesto, su jefe y su zona horaria.`);
    cont.append(cabecera(r, ctx), panelZona(r, ctx, repintar));
    const resumen = panelResumen(r, ctx);
    if (resumen) cont.append(resumen);
    cont.append(panelQueCambia(r));
    if (r.propia) cont.append(panel({titulo: 'Cómo mejoramos la app', icono: 'info'},
      h('div', {class: 'cuerpo pila'}, h('p', {}, 'Medimos las pantallas que abres, acciones generales y tiempo de interacción para facilitar el trabajo del equipo.'),
        h('p', {class: 'sub'}, 'Se conserva en la app durante 30 días. Dirección y operaciones pueden consultar el resumen. Esta medición no guarda los textos que escribes ni graba la pantalla. El tiempo de uso no equivale a horas trabajadas.'))));
    for (const x of [panelEquipo(r, ctx), panelCambios(r, ctx)]) if (x) cont.append(x);
}

export default {
  id: ID,
  titulo: 'Mi perfil',
  grupo: 'Perfil',
  puestos_que_lo_ven: { '*': 'suyo', direccion: 'todo', operaciones: 'todo', rrhh: 'todo' },
  render,
};
