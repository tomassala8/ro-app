// modulos/primera_semana.js · A10 «Tu primera semana» (R15a, 2-oct-2026). Ruta #/primera-semana[/<persona>].
// Para quien entró hace menos de 14 días (o está «por incorporar»): los 5 pasos de su puesto (de la guía del equipo,
// data/primera_semana/guias.json ← fuentes_equipo/generar_primera_semana.py), su jefe, sus clientes y enlaces a sus 3 pantallas.
// La lista se marca a mano y se guarda con ctx.accion (tipo «primera_semana_paso», solo la propia persona; en «ver como», nada).
// La ven la persona, su jefe, Mili y Tomás (operaciones y dirección). No sale en el menú: se llega desde Mi día, desde Ajustes ›
// la ficha de la persona o con ⌘K.

import { h, panel, vacio, avisoParcial, chipEstado, icono, barraProgreso, listaLoPrimero, logoCliente, avisoFlotante, fmt } from '../componentes.js';
import { sinCodigos } from './_legible.js';

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

export const ID = 'primera-semana';
export const DIAS_VENTANA = 14;
const TIPO = 'primera_semana_paso';
const PASO_OPINION = 'algo_va_mal';   // R15b: se da por hecho con la fila opinion_enviada de la persona
const MANDO = ['direccion', 'operaciones'];

const hoyISO = () => new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Madrid', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
const diasDesde = f => Math.round((Date.parse(hoyISO()) - Date.parse(String(f).slice(0, 10))) / 864e5);

/** ¿Es un alta nueva? Entró hace menos de 14 días, o está «por incorporar». Devuelve { dias, quedan } o null. */
export function altaNueva(p) {
  if (!p) return null;
  if (p.estado === 'por_incorporar') return { dias: null, quedan: DIAS_VENTANA, por_incorporar: true };
  if (p.estado && p.estado !== 'activo') return null;
  if (!p.fecha_ingreso) return null;
  const d = diasDesde(p.fecha_ingreso);
  return d >= 0 && d < DIAS_VENTANA ? { dias: d, quedan: DIAS_VENTANA - d } : null;
}

/** ¿Puede quien mira ver la primera semana de «p»? La propia persona, su jefe, Mili y Tomás. */
export function puedeVer(ctx, p) {
  if (!p) return false;
  const yo = ctx.persona;
  return p.id === yo.id || p.jefe === yo.id || (yo.puestos || []).some(x => MANDO.includes(x));
}

/** R15b · ¿Ha mandado ya «Algo va mal / Tengo una idea»? La fila opinion_enviada de esa persona: GET /api/opiniones (las
 *  propias; Mili y Tomás, todas) y, si quien mira es su jefe, el rastro si su puesto lo ve entero. → fecha de la primera o null. */
export async function opinionEnviada(ctx, pid) {
  if (!ctx.servidor) return null;
  const fechas = [];
  try {
    const r = await ctx.api('opiniones');
    for (const o of r.opiniones || []) if (o.quien === pid && o.creada) fechas.push(o.creada);
    // R16: al jefe directo el servidor le da solo el HECHO de su gente (nunca el texto): equipo[pid] = { alguna, primera }
    const eq = r.equipo?.[pid];
    if (!fechas.length && eq?.alguna) fechas.push(eq.primera || 'sí');
  } catch { /* sin acceso: se mira el rastro */ }
  if (!fechas.length && pid !== ctx.persona.id) {
    try {
      const r = await ctx.api('rastro');
      for (const f of r.registro || []) if (f.accion === 'opinion_enviada' && f.quien === pid) fechas.push(f.creada || '');
    } catch { /* sin rastro: queda a mano */ }
  }
  return fechas.length ? (fechas.sort()[0] || 'sí') : null;
}

/** Pasos hechos de una persona: la última marca de cada paso, solo las que puso ella. → Set de números de paso.
 *  R15b: el paso «Algo va mal» se da por hecho si ya mandó uno (hechos.auto = { <n>: fecha }). */
export async function pasosHechos(ctx, pid) {
  const hechos = new Set();
  hechos.auto = {};
  if (!ctx.servidor) return hechos;
  const auto = Promise.all([opinionEnviada(ctx, pid), ctx.datosModulo('primera_semana/guias').catch(() => null)]).catch(() => [null, null]);
  let filas = [];
  try { filas = (await ctx.api(`acciones?modulo=${ID}`)).acciones || []; } catch { filas = []; }
  const [envio, G] = await auto;
  if (envio) {
    const n = (G?.pasos || []).find(x => x.id === PASO_OPINION)?.n || 5;
    hechos.auto[n] = envio;
  }
  const vistos = new Set();
  for (const a of filas) {   // vienen de la más nueva a la más vieja
    if (a.tipo !== TIPO || a.quien !== pid) continue;
    const [quien, n] = String(a.objeto).split(':');
    if (quien !== pid || vistos.has(n)) continue;
    vistos.add(n);
    let vp = a.vista_previa;
    try { vp = typeof vp === 'string' ? JSON.parse(vp) : vp; } catch { vp = null; }
    if (vp?.hecho !== false) hechos.add(Number(n));
  }
  for (const n of Object.keys(hechos.auto)) hechos.add(Number(n));   // ya mandó uno: hecho aunque no lo marcara
  return hechos;
}

function clientesDe(ctx, pid) {
  const hoy = hoyISO();
  const vig = a => (!a.desde || a.desde <= hoy) && (!a.hasta || a.hasta >= hoy);
  const ids = new Set((ctx.datos?.asignaciones || []).filter(a => a.persona_id === pid && vig(a)).map(a => a.cliente_id));
  if (!ids.size && pid === ctx.persona.id) for (const c of ctx.carteraIds || []) ids.add(c);
  return (ctx.clientes || []).filter(c => ids.has(c.id)).sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
}

function contenidoPaso(paso, G, pant) {
  const g = G?.guia;
  if (paso.id === 'guia' && g) {
    return h('details', { class: 'que-es' }, h('summary', { style: { minHeight: 'var(--s-8)', cursor: 'pointer' } }, `Leer ahora: ${g.titulo}`),
      h('div', { class: 'pila', style: { gap: 'var(--s-2)', maxWidth: '72ch' } },
        g.para_que ? h('p', {}, h('b', {}, 'Para qué entras: '), sinCodigos(g.para_que)) : null,
        g.al_entrar?.length ? h('div', {}, h('b', {}, 'Qué ves al entrar'), h('ul', {}, g.al_entrar.map(x => h('li', {}, sinCodigos(x))))) : null,
        g.rutina?.length ? h('div', {}, h('b', {}, 'Tu rutina'), h('ul', {}, g.rutina.map(x => h('li', {}, sinCodigos(x))))) : null));
  }
  if (paso.id === 'pantallas') {
    return h('div', { class: 'fila' }, pant.map(p => h('a', { class: 'bt mini', href: p.ruta }, icono('derecha', { clase: 's' }), p.titulo)));
  }
  if (paso.id === 'numero' && (g?.numero_tabla?.length || g?.numero_que_manda)) return tablaNumero(g);
  return null;
}

/** R16: el número que manda llega en texto llano (numero_que_manda) y, fila a fila, en numero_tabla
 *  ([{puesto|quién, número, verde, ámbar, rojo}]): si hay filas, tabla densa común; si no, el texto. */
function tablaNumero(g) {
  const filas = (g.numero_tabla || []).filter(f => f && typeof f === 'object');
  if (!filas.length) return h('p', { style: { margin: 0, maxWidth: '72ch' } }, sinCodigos(g.numero_que_manda));
  const quien = f => f.puesto || f['quién'] || f.quien || '';
  const celda = (est, t) => h('td', {}, t ? chipEstado(est, sinCodigos(String(t)), { punto: true }) : '—');
  return h('div', { class: 'tabla-scroll' }, h('table', { class: 'densa' },
    h('thead', {}, h('tr', {}, ['Quién', 'Número', 'Verde', 'Ámbar', 'Rojo'].map(t => h('th', { scope: 'col' }, t)))),
    h('tbody', {}, filas.map(f => h('tr', {}, h('th', { scope: 'row' }, sinCodigos(quien(f))), h('td', {}, sinCodigos(String(f['número'] || f.numero || ''))),
      celda('verde', f.verde), celda('ambar', f['ámbar'] || f.ambar), celda('rojo', f.rojo))))));
}

async function pintarPersona(cont, ctx, G, p, { propia }) {
  const nueva = altaNueva(p);
  const puesto = (p.puestos || [])[0];
  const Gp = G.puestos?.[puesto] || {};
  // Con dos puestos, las 3 pantallas salen de los dos (sin repetir).
  const pant = [];
  for (const pu of p.puestos || []) for (const x of G.puestos?.[pu]?.pantallas || []) if (!pant.some(y => y.id === x.id)) pant.push(x);
  const hechos = await pasosHechos(ctx, p.id);
  const puedeMarcar = propia && !ctx.soloLectura;
  const total = (G.pasos || []).length;

  ctx.titulo(propia ? 'Tu primera semana' : `Primera semana de ${p.alias || p.nombre}`,
    nueva ? (nueva.por_incorporar ? 'Por incorporar: esto es lo primero que hará en la app' : `Día ${nueva.dias + 1} de ${DIAS_VENTANA} · cinco pasos para empezar con buen pie`)
      : 'Los primeros 14 días ya pasaron');
  if (!nueva) {
    cont.append(avisoParcial(propia ? 'Esta guía es para tus primeros 14 días en la app. La dejamos aquí por si quieres repasarla.'
      : `${p.alias || p.nombre} entró el ${p.fecha_ingreso ? fDiaRO(p.fecha_ingreso) : '—'}: su tarjeta ya no sale en Mi día. La ves para repasarla con ella.`, { tipo: 'info' }));
  }

  const cuenta = h('span', { class: 'sub', role: 'status', 'aria-live': 'polite' });
  const barra = h('div');
  const pintarCuenta = () => {
    const n = [...hechos].filter(x => x >= 1 && x <= total).length;
    cuenta.textContent = `${n} de ${total} hechos`;
    barra.replaceChildren(barraProgreso({ valor: n, max: total, estado: n === total ? 'verde' : null, etiqueta: `${n} de ${total} pasos hechos` }));
  };
  const lista = h('div');
  const pintarLista = () => {
    lista.replaceChildren(listaLoPrimero((G.pasos || []).map(paso => {
      const hecho = hechos.has(paso.n);
      const extra = contenidoPaso(paso, Gp, pant);
      const auto = hechos.auto?.[paso.n];
      const fechaAuto = auto && /^\d{4}-\d{2}-\d{2}/.test(auto)   // la base guarda la hora en UTC: el día, el de Madrid
        ? fDiaRO(new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Madrid', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(`${auto.slice(0, 19).replace(' ', 'T')}Z`))) : '';
      const bt = auto ? h('span', { title: 'Se marca solo: ya consta un «Algo va mal / Tengo una idea» de esta persona' },
        chipEstado('verde', `Hecho · ${propia ? 'mandaste uno' : 'mandó uno'}${fechaAuto ? ` el ${fechaAuto}` : ''}`))
        : puedeMarcar ? h('button', { type: 'button', class: 'bt mini', 'aria-pressed': String(hecho), title: hecho ? 'Desmarcar' : 'Marcar como hecho',
        on: { click: async e => {
          const b = e.currentTarget; b.disabled = true;
          try {
            await ctx.accion({ herramienta: 'app', tipo: TIPO, objeto: `${p.id}:${paso.n}`, texto: `Primera semana · paso ${paso.n}: ${paso.texto} (${hecho ? 'desmarcado' : 'hecho'})`,
              vista_previa: { paso: paso.n, hecho: !hecho } });
            if (hecho) hechos.delete(paso.n); else hechos.add(paso.n);
            if (!hecho && [...hechos].length === total) avisoFlotante('¡Primera semana completa!');
            pintarLista(); pintarCuenta();
          } catch (err) {
            // R16: cada uno marca solo SUS pasos (objeto «<persona real>:<paso>»); un 403 se dice en llano
            const msg = err?.status === 403 ? 'Solo la propia persona marca sus pasos.' : (err?.message || String(err));
            b.disabled = false; b.title = msg; avisoFlotante(`No se pudo guardar: ${msg}`, { icono: 'alert' });
          }
        } } }, icono(hecho ? 'ok' : 'check', { clase: 's' }), hecho ? 'Hecho' : 'Marcar hecho')
        : chipEstado(hecho ? 'verde' : 'gris', hecho ? 'Hecho' : 'Pendiente');
      return { estado: hecho ? 'gris hecho' : 'info', icono: hecho ? 'ok' : null, motivo: paso.texto,
        detalle: h('div', { class: 'pila', style: { gap: 'var(--s-2)' } }, paso.detalle, extra), botones: [bt] };
    }), { subir: false }));
  };
  pintarCuenta(); pintarLista();
  cont.append(panel({ titulo: 'Cinco pasos', icono: 'rocket', sub: Gp.guia ? `Guía de ${Gp.guia.titulo}` : 'Guía del equipo',
    acciones: cuenta }, h('div', { class: 'cuerpo pila', style: { gap: 'var(--s-2)' } }, barra,
    !puedeMarcar ? h('p', { class: 'sub', style: { margin: 0 } }, ctx.soloLectura ? 'Estás en «ver como»: lo marca la persona.' : 'Los pasos los marca la propia persona.') : null), lista));

  // Su jefe y sus clientes
  const jefe = p.jefe ? (ctx.datos?.personas || []).find(x => x.id === p.jefe) : null;
  const clientes = clientesDe(ctx, p.id);
  cont.append(h('div', { class: 'dos' },
    panel({ titulo: propia ? 'Tu equipo' : 'Su equipo', icono: 'users' }, h('div', { class: 'cuerpo pila', style: { gap: 'var(--s-2)' } },
      h('p', { style: { margin: 0 } }, h('b', {}, propia ? 'Tu jefe: ' : 'Su jefe: '), jefe ? (jefe.alias || jefe.nombre) : 'sin jefe asignado (lo pone Mili en Ajustes)'),
      h('p', { style: { margin: 0 } }, h('b', {}, 'Puesto: '), (p.puestos || []).map(x => G.puestos?.[x]?.guia?.titulo?.replace(/\s*\(.*\)$/, '') || x).join(' · ') || '—'),
      h('p', { class: 'sub', style: { margin: 0 } }, propia ? 'Si te atascas, pregunta a tu jefe. Si algo de la app falla, a Agus.' : 'Si se atasca: su jefe; si falla la app, Agus.'))),
    panel({ titulo: `${propia ? 'Tus' : 'Sus'} clientes (${clientes.length})`, icono: 'cartera' },
      clientes.length ? h('ul', { class: 'lista-i' }, clientes.map(c => h('li', {},
        logoCliente(c, 'logo-cli'),
        h('span', { class: 't' }, c.detalle ? h('a', { href: `#/ficha/${encodeURIComponent(c.id)}` }, c.nombre) : c.nombre))))
        : h('div', { class: 'cuerpo' }, vacio({ icono: 'cartera', titulo: 'Aún sin clientes asignados', texto: 'Los reparte Mili en Ajustes › Asignaciones.' })))));
}

function pintarLista(cont, ctx, G) {
  const yo = ctx.persona;
  const dir = (yo.puestos || []).some(x => MANDO.includes(x));
  const ps = (ctx.datos?.personas || []).filter(p => altaNueva(p) && p.id !== yo.id && (dir || p.jefe === yo.id));
  ctx.titulo('Primera semana', dir ? 'Altas de los últimos 14 días y por incorporar' : 'Las altas nuevas de tu equipo');
  if (!ps.length) {
    cont.append(vacio({ icono: 'users', titulo: dir ? 'Nadie ha entrado en los últimos 14 días' : 'Nadie nuevo en tu equipo', borde: true,
      texto: 'Cuando des de alta a alguien (Ajustes › Altas y bajas), su primera semana sale aquí y en su Mi día.' }));
    return;
  }
  cont.append(panel({ titulo: `Altas nuevas (${ps.length})`, icono: 'users' }, h('ul', { class: 'lista-i' }, ps.map(p => {
    const n = altaNueva(p);
    return h('li', {}, h('span', { class: 'ico-c s gris' }, icono('persona')),
      h('span', { class: 't' }, h('a', { href: `#/${ID}/${encodeURIComponent(p.id)}` }, p.alias || p.nombre),
        h('span', { class: 'sub' }, n.por_incorporar ? ' · por incorporar' : ` · día ${n.dias + 1} de ${DIAS_VENTANA}`)));
  }))));
}

export default {
  id: ID,
  titulo: 'Tu primera semana',
  grupo: 'Bienvenida',
  puestos_que_lo_ven: { '*': 'suyo', direccion: 'todo', operaciones: 'todo', proyectos: 'todo', rrhh: 'todo', jefa_publicidad: 'todo', jefa_seo: 'todo', jefa_crm: 'todo' },
  async render(cont, ctx) {
    vigilarCortes(cont);
    cont.classList.add('pila');
    let G;
    try { G = await ctx.datosModulo('primera_semana/guias'); }
    catch (e) { cont.append(vacio({ icono: 'alert', tono: 'aviso', titulo: 'No llega la guía de la primera semana', texto: e.message, quien: 'Agus' })); return; }
    const personas = ctx.datos?.personas || [];
    const pid = ctx.params[0] || ctx.persona.id;
    const p = personas.find(x => x.id === pid);
    if (!p || !puedeVer(ctx, p)) {
      cont.append(vacio({ icono: 'candado', borde: true, titulo: 'Esta primera semana no es tuya',
        texto: 'La ven la propia persona, su jefe, Mili y Tomás.' }));
      return;
    }
    const propia = p.id === ctx.persona.id;
    // Sin ruta: quien no es nueva pero manda (Mili, Tomás, jefes) ve la lista de altas nuevas de su ámbito.
    if (!ctx.params[0] && !altaNueva(p)) {
      const dir = (ctx.persona.puestos || []).some(x => MANDO.includes(x));
      if (dir || personas.some(x => x.jefe === ctx.persona.id && altaNueva(x))) { pintarLista(cont, ctx, G); return; }
    }
    await pintarPersona(cont, ctx, G, p, { propia });
  },
};
