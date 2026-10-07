import { fechas as FECHAS_RO } from '../componentes.js';
// modulos/setters.js · «Mi día» del setter (E6; rehecho el 3-oct con el feedback de Tomás, ../58_FEEDBACK_TOMAS_03OCT.md).
// La setter entra DIRECTA aquí (app.js, INICIO_POR_PUESTO): su Mi día ES esta pantalla. Móvil a 390 px primero.
// Orden de trabajo, así de claro en pantalla:
//   1 · Confirmar las reuniones de HOY (hora en tu zona y en la del lead, Llamar con Zadarma, WhatsApp, y
//       «Confirmada / No contesta / Reagendar / Cancela» con un clic y «Hecho · Deshacer»). «Confirmadas X de Y hoy».
//   2 · Meter en agenda a quien todavía no tiene cita (por probabilidad y antigüedad): Llamar, WhatsApp, nota rápida,
//       resultado y «Agendar cita» (huecos libres del calendario de 45 min de Tomás, ayuda opcional de Claude). La cita
//       va a la cola en SIMULACIÓN («Crear cita en GoHighLevel»): no se crea nada en GoHighLevel. Alternativa: «Abrir en GoHighLevel».
//   3 · Citas que ya pasaron sin resultado (solo si hay).
// Solo la subcuenta de RO: nada de clientes de la agencia. El servidor (servir.py + setters_srv.py) da a cada setter SOLO
// sus leads y citas y rechaza cualquier acción sobre las de otra. Teléfono y correo, en el clic de Llamar/WhatsApp (ver_dato).

import { h, fmt, vacioLinea, listaLoPrimero, tablaApilable, chipEstado, chipsFiltro, vacio, avisoParcial, panel, frescura,
  icono, limpiaTexto, hoyMadrid, sumarDias, fechaCorta, avisoFlotante } from '../componentes.js';
import { cargar, setterDe, nombreSetter, fresco, duracionTexto, cuandoTexto, minutosDesde, nombreLead, encolar, leerCola,
  vistaPrevia, abrirEn, masAcciones, contactoLead, verDatos, chipGrupo, campo } from './_ventas_comun.js';
import { pantallaTrabajo, franjaCifras } from './_trabajo.js';
import { franjaEnLinea } from './_trabajo_ancho.js';
import { conDeshacer, botonDeshacer } from './_deshacer.js';

const DIAS_S = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
const ZONA_RO = 'Europe/Madrid';

// ----------------------------------------------------------------- horas y zonas
/** «2026-10-05 11:00» (hora de Madrid, como vienen del generador) → instante real (Date). */
const instanteMadrid = s => FECHAS_RO.instante(s);
const zonaValida = z => { try { new Intl.DateTimeFormat('es-ES', { timeZone: z }); return !!z; } catch { return false; } };
/** «11:00» en esa zona. */
const horaEn = (d, zona) => (d ? new Intl.DateTimeFormat('es-ES', { timeZone: zonaValida(zona) ? zona : ZONA_RO, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(d) : '');
const NOMBRE_ZONA = { 'Europe/Madrid': 'España', 'Atlantic/Canary': 'Canarias', 'America/Argentina/Buenos_Aires': 'Argentina' };
const nombreZona = z => NOMBRE_ZONA[z] || String(z || '').split('/').pop().replace(/_/g, ' ');
/** Día relativo con el «hoy» de Madrid (?hoy= en local para probar un lunes). */
function diaRel(cuando, hoy = hoyMadrid()) {
  const d = FECHAS_RO.dia(cuando);
  if (!d) return '';
  if (d === hoy) return 'hoy';
  if (d === sumarDias(hoy, 1)) return 'mañana';
  if (d < hoy) return `el ${FECHAS_RO.diaSemana(d, true)} (ya pasó)`;
  return `el ${FECHAS_RO.diaSemana(d, true)}`;
}
const diaLargo = d => { const dia = FECHAS_RO.dia(d); return dia ? `${FECHAS_RO.diaSemana(dia, true)} ${Number(dia.slice(8))}` : 'Fecha por contrastar'; };
const horaMadridAhora = () => Number(FECHAS_RO.hora(new Date()).slice(0, 2));
/** La hora de la cola viene en UTC; solo se añade Z a un datetime completo válido, nunca a fecha civil. */
const madridDe = t => {
  const s = String(t || '').trim();
  const conZona = /(?:[zZ]|[+-]\d{2}:?\d{2})$/.test(s);
  const d = FECHAS_RO.instante(conZona ? s : /^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?$/.test(s) ? `${s.replace(' ', 'T')}Z` : null);
  return d ? { dia:FECHAS_RO.dia(d), hora:FECHAS_RO.hora(d) } : { dia:null,hora:null };
};
const fechaHora = t => { const m = madridDe(t); return m.dia ? `${fechaCorta(m.dia)}, ${m.hora}` : ''; };
const horasSegundaRO = t => { const h = FECHAS_RO.horasHasta(t); return h === null ? null : Math.round(h); };

// ----------------------------------------------------------------- piezas
/** Botones a todo el ancho en el móvil (48 px, con una mano) y en fila en el ordenador. */
function aTodoElAncho(el) {
  if (el && el.classList?.contains('fila')) Object.assign(el.style, { display: 'grid', gap: 'var(--s-2)', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 130px), 1fr))' });
  el?.querySelectorAll?.('button, a').forEach(b => { b.style.minHeight = 'var(--s-12)'; b.style.justifyContent = 'center'; });
  return el;
}
/** Llamar SIEMPRE con Zadarma (sip:+34…@sip.zadarma.com, regla de _telefono.js) y WhatsApp; con la extensión si consta. */
function contactoZadarma(ctx, { almacen, x, ext }) {
  const c = contactoLead(ctx, { almacen, x });
  const b = c?.querySelector?.('button.pri');
  if (b && /Llamar/.test(b.textContent)) {
    b.title = `Llamar con Zadarma${ext ? ` desde tu extensión ${ext}` : ' (tu extensión está por confirmar)'}: abre la app de Zadarma con el número`;
    b.setAttribute('aria-label', `Llamar con Zadarma a ${nombreLead(x)}`);
  }
  return c;
}
function masDe(nombre, ...botones) {
  const m = masAcciones(...botones);
  const s = m?.querySelector(':scope > summary');
  if (s) { s.lastChild.textContent = 'Más acciones'; s.setAttribute('aria-label', `Más acciones de ${nombre || 'este lead'}`); }
  const f = m?.querySelector(':scope > .fila');
  if (f) Object.assign(f.style, { flexWrap: 'wrap', minWidth: '0', maxWidth: '100%' });
  return m;
}
const titulo2 = (num, texto, sub) => h('div', { class: 'fila', style: { gap: 'var(--s-3)', alignItems: 'flex-start', flexWrap: 'nowrap' } },
  h('span', { 'aria-hidden': 'true', style: { flex: '0 0 auto', width: '32px', height: '32px', borderRadius: '50%', display: 'grid', placeItems: 'center', background: 'var(--accent)', color: 'var(--card)', font: 'var(--t-h2)' } }, String(num)),
  h('div', { style: { minWidth: 0 } }, h('h2', { style: { margin: 0, font: 'var(--t-h1)' } }, texto), sub ? h('p', { class: 'sub', style: { margin: 0 } }, sub) : null));

// ----------------------------------------------------------------- 1 · confirmar las reuniones de hoy
const ESTADOS_CITA = [
  { t: 'Confirmada', ico: 'ok', est: 'verde' },
  { t: 'No contesta', ico: 'phone', est: 'ambar' },
  { t: 'Reagendar', ico: 'clock', est: 'ambar' },
  { t: 'Cancela', ico: 'cerrar', est: 'rojo' },
];
/** Estado de una cita a partir de lo apuntado (también lo del modelo anterior: «Confirmada por teléfono», «Quiere cambiar la hora»). */
function estadoCita(texto) {
  const t = String(texto || '');
  if (/^Confirmada/.test(t)) return ESTADOS_CITA[0];
  if (/^No contesta/.test(t)) return ESTADOS_CITA[1];
  if (/^Reagendar|^Quiere cambiar/.test(t)) return ESTADOS_CITA[2];
  if (/^Cancela/.test(t)) return ESTADOS_CITA[3];
  return null;
}

// ----------------------------------------------------------------- 2 · resultado de la llamada a un lead sin cita
const OPCIONES_LEAD = ['No contesta', 'Hablado: volver a llamar', 'Hablado: reserva él por la web', 'Hablado: no encaja', 'Número erróneo'];
const OPCIONES_PASADA = ['Se celebró', 'No se presentó', 'Se reprogramó', 'No lo sé: pregunto a Tomás'];
const ICO_RES = r => (/^No contesta|erróneo|no encaja|No se presentó/.test(r) ? 'cerrar' : /reserva|Se celebró/.test(r) ? 'ok' : 'clock');
/** Probabilidad: pidió reunión y no encontró hueco (b) antes que «no se presentó» (c); dentro, el más reciente. */
const RANGO_GRUPO = { b: 0, a: 1, c: 2 };

// ----------------------------------------------------------------- pantalla
async function pintar(cont, ctx, vista) {
  const [d, meta] = await Promise.all([cargar(ctx, 'setters'), cargar(ctx, 'meta')]);
  if (!d) {
    cont.append(vacio({ icono: 'phone', titulo: 'Todavía no hay lista de llamadas', texto: 'Falta generar los datos de ventas de RO de hoy.', quien: 'Agus', tono: 'aviso' }));
    return;
  }
  const cola = await leerCola(ctx, 'setters');
  const yo = setterDe(ctx.persona);
  const resumen = ctx.nivel === 'resumen' && !yo;
  const ver = yo || vista || null;
  const almacenDe = l => `setter_${ver || l?.setter}`;
  const mio = l => !ver || l.setter === ver;
  const fGHL = fresco(meta, 'GoHighLevel (subcuenta RO)', 'GoHighLevel');
  const fZD = fresco(meta, 'Zadarma');
  const zonaYo = zonaValida(ctx.persona?.zona) ? ctx.persona.zona : ZONA_RO;
  const extDe = s => (d.setters || []).find(x => x.clave === s && x.ext_confirmada)?.ext || null;

  ctx.titulo(yo ? `Mi día · ${ctx.nombre(ctx.persona.id)}` : 'Setters', yo
    ? 'Primero confirma las reuniones de hoy; después mete en agenda a quien todavía no tiene cita.'
    : `El día de los setters${ver ? ' · ' + nombreSetter(ctx, ver) : ''}`);

  if (ctx.persona.puestos.includes('setters') && !yo) {
    cont.append(vacio({ icono: 'persona', titulo: 'No estás en el reparto', texto: 'Tu usuario tiene el puesto de setter pero no tiene leads asignados.', quien: 'Tomás', tono: 'aviso' }));
    return;
  }
  let chipsVer = null;
  if (!yo && !resumen) {
    chipsVer = chipsFiltro({ etiqueta: 'Ver', clave: 'setters.vista', valor: vista || '',
      opciones: [{ valor: '', texto: 'Los dos', icono: 'users' }, ...['ana', 'javier'].map(s => ({ valor: s, texto: nombreSetter(ctx, s), icono: 'persona' }))],
      alCambiar: v => { cont.replaceChildren(); pintar(cont, ctx, v || null); } });
    if (vista === undefined) { const recordado = chipsVer.valor?.(); if (recordado) return pintar(cont, ctx, recordado); }
  }

  // Lo apuntado HOY (cola de acciones de la pantalla): estado de cada cita, resultado de cada lead y citas pedidas.
  const hoy = hoyMadrid();
  const apuntados = new Map();   // id → texto del resultado
  const pedidas = new Map();     // id → texto de la cita pedida (simulada)
  for (const a of cola) {
    // La confirmación de una reunión vale hasta la reunión (sale aquí 24-48 h antes); el resultado de un lead, solo hoy.
    if (a.que === 'confirmacion_cita' || (['resultado_llamada', 'resultado_cita', 'resultado'].includes(a.que) && madridDe(a.hora).dia === hoy)) apuntados.set(a.sobre, a.texto);
    if (a.que === 'crear_cita_ghl') pedidas.set(a.sobre, a.texto);
  }
  const notas = new Map();
  for (const a of cola) if (a.que === 'nota') notas.set(a.sobre, a.texto);

  const leadsT = (d.leads || []).filter(mio).map(l => ({ ...l, min: minutosDesde(l.entro) }));
  const citasT = (d.citas || []).filter(mio).map(c => ({ ...c, dia: diaRel(c.cuando), t: instanteMadrid(c.cuando) }));
  const pasadasT = (d.pasadas || []).filter(mio);
  const hoyDe = s => (d.marcador || []).find(m => m.setter === s && m.periodo === 'hoy') || {};
  const semDe = s => (d.marcador || []).find(m => m.setter === s && m.periodo === 'semana') || {};
  const quien = l => (!ver ? ` · ${nombreSetter(ctx, l.setter)}` : '');
  const pendientesApunte = new Set(); // impide dos resultados concurrentes sobre la misma cita o lead
  const borradoresNotas = new Map(); // una escritura fallida no borra la nota al reconstruir la fila
  const abiertos = new Set();    // filas con el formulario de agendar abierto (sobreviven a un repintado)

  const raiz = h('div', { class: 'pila', style: { gap: 'var(--s-4)', minWidth: '0' } });
  cont.append(raiz);

  function listas() {
    const citasHoy = citasT.filter(c => c.dia === 'hoy').sort((a, b) => a.cuando.localeCompare(b.cuando));
    const citasLuego = citasT.filter(c => c.dia !== 'hoy' && !/ya pasó/.test(c.dia)).sort((a, b) => a.cuando.localeCompare(b.cuando));
    const sinCita = leadsT.filter(l => ['llamar_ya', 'segunda', 'hablado'].includes(l.lista) && !apuntados.has(l.id))
      .sort((a, b) => (!!a.sin_tel - !!b.sin_tel) || (!!pedidas.has(a.id) - !!pedidas.has(b.id))
        || ((RANGO_GRUPO[a.grupo] ?? 3) - (RANGO_GRUPO[b.grupo] ?? 3)) || ((a.min ?? 1e9) - (b.min ?? 1e9)));
    const hechosHoy = leadsT.filter(l => apuntados.has(l.id));
    return { citasHoy, citasLuego, sinCita, hechosHoy, pasadas: pasadasT.filter(c => !apuntados.has(c.id)) };
  }

  // Apuntar (cita o lead): se ve al momento, «Hecho · Deshacer» 8 s, y se encola al acabar el plazo (interno: queda en la app).
  const apuntar = (x, que, texto, nota) => {
    if (ctx.soloLectura || pendientesApunte.has(x.id)) return;
    const habia = apuntados.has(x.id), anterior = apuntados.get(x.id);
    pendientesApunte.add(x.id);
    return conDeshacer({
      mensaje: `«${texto}» · ${nombreLead(x)}`,
      optimista: () => { apuntados.set(x.id, texto); dibujar(); },
      revertir: () => {
        if (habia) apuntados.set(x.id, anterior); else apuntados.delete(x.id);
        pendientesApunte.delete(x.id); dibujar();
      },
      hacer: async () => {
        await encolar(ctx, { que, sobre: x.id, texto: `${texto}${nota ? ' · ' + nota : ''}`, herramienta: 'app',
          vista: 'Queda en la app; con el permiso de escritura de GoHighLevel irá como nota en la ficha del lead' });
        pendientesApunte.delete(x.id); borradoresNotas.delete(x.id); dibujar();
      },
    });
  };

  // ---------------------------------------------------------------- fila de una reunión (sección 1)
  function filaCita(c) {
    const est = estadoCita(apuntados.get(c.id));
    const zonaLead = zonaValida(c.zona) ? c.zona : ZONA_RO;
    const horaYo = horaEn(c.t, zonaYo), horaLead = horaEn(c.t, zonaLead);
    const mismaHora = zonaYo === zonaLead || horaYo === horaLead;
    const chip = est ? chipEstado(est.est, est.t) : c.confirmada_tel ? chipEstado('azul', 'Hablado por teléfono · sin marcar') : chipEstado('rojo', 'Sin confirmar');
    const botones = h('div', { role: 'group', 'aria-label': `Marcar la reunión de ${nombreLead(c)}`, style: { display: 'grid', gap: 'var(--s-2)', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 120px), 1fr))' } },
      ESTADOS_CITA.map(o => h('button', { type: 'button', class: `bt${est?.t === o.t ? ' pri' : ''}`, 'aria-pressed': String(est?.t === o.t), 'data-estado-cita': o.t,
        'aria-disabled': ctx.soloLectura ? 'true' : null, title: ctx.soloLectura ? 'Estás en «ver como»: solo lectura' : `Marcar «${o.t}» (8 s para deshacer)`,
        style: { minHeight: 'var(--s-12)', justifyContent: 'center' },
        on: { click: () => { if (!ctx.soloLectura && est?.t !== o.t) apuntar(c, 'confirmacion_cita', o.t); } } }, icono(o.ico), o.t)));
    const hueco = h('div', { hidden: !abiertos.has(c.id) });
    if (abiertos.has(c.id)) hueco.append(formAgendar(c, { reagenda: c.cita_id }));
    const reag = est?.t === 'Reagendar' ? h('button', { type: 'button', class: 'bt', style: { minHeight: 'var(--s-10)' },
      on: { click: () => { abiertos.add(c.id); hueco.hidden = false; if (!hueco.childNodes.length) hueco.append(formAgendar(c, { reagenda: c.cita_id })); } } }, icono('cal'), 'Proponer la nueva hora') : null;
    return h('li', { class: 'panel', 'data-cita': c.id, style: { listStyle: 'none', borderColor: est?.t === 'Confirmada' ? 'var(--line)' : 'var(--accent)' } },
      h('div', { class: 'cuerpo pila', style: { gap: 'var(--s-3)' } },
        h('div', { class: 'fila', style: { gap: 'var(--s-3)', flexWrap: 'nowrap', alignItems: 'flex-start' } },
          h('div', { style: { flex: '0 0 auto', textAlign: 'center', minWidth: '64px' } },
            h('div', { style: { font: 'var(--t-h1)', fontVariantNumeric: 'tabular-nums' } }, horaYo),
            h('div', { class: 'sub', style: { fontSize: '12px' } }, 'tu hora')),
          h('div', { style: { minWidth: 0, flex: '1 1 auto' } },
            h('div', { style: { font: 'var(--t-h2)', overflowWrap: 'anywhere' } }, nombreLead(c)),
            h('div', { class: 'sub' }, mismaHora ? `Reunión de 45 min con Tomás · ${horaLead} en ${nombreZona(zonaLead)}`
              : `Reunión de 45 min con Tomás · para el lead son las ${horaLead} (${nombreZona(zonaLead)})`, quien(c)),
            h('div', { style: { marginTop: 'var(--s-1)' } }, chip))),
        aTodoElAncho(contactoZadarma(ctx, { almacen: almacenDe(c), x: c, ext: extDe(c.setter) })),
        botones, reag, hueco,
        h('div', { class: 'fila', style: { gap: 'var(--s-2)' } }, abrirEn('GoHighLevel', c.ghl), verCompleto(c))));
  }
  const verCompleto = x => {
    const dest = h('span');
    const b = verDatos(ctx, { almacen: almacenDe(x), id: x.id, destino: dest });
    return b ? h('span', { class: 'fila', style: { gap: 'var(--s-2)' } }, b, dest) : null;
  };

  // ---------------------------------------------------------------- formulario «Agendar cita»
  function formAgendar(x, { reagenda } = {}) {
    const huecos = d.huecos?.dias || {};
    const dias = Object.keys(huecos).filter(k => k >= hoy).sort();
    let elegido = null;   // 'AAAA-MM-DD HH:MM'
    let ayuda = null;
    const caja = h('div', { class: 'pila', role: 'group', 'aria-label': `Agendar cita para ${nombreLead(x)}`,
      style: { gap: 'var(--s-3)', padding: 'var(--s-3)', border: '1px solid var(--line)', borderRadius: 'var(--r-m)', background: 'var(--bg)' } });
    const notasLlamada = h('textarea', { class: 'campo', rows: 3, maxlength: '1500', placeholder: 'Notas de la llamada: qué necesita, qué día le va bien (p. ej. «el jueves por la tarde»)…',
      'aria-label': 'Notas de la llamada', style: { width: '100%', padding: 'var(--s-2) var(--s-3)', border: '1px solid var(--line)', borderRadius: 'var(--r-s)', background: 'var(--card)', font: 'var(--t-cuerpo)' } });
    const titulo = h('input', { type: 'text', class: 'campo', maxlength: '140', value: `Reunión de 45 min con Tomás · ${nombreLead(x)}`, 'aria-label': 'Título de la cita',
      style: { width: '100%', minHeight: 'var(--s-10)', padding: 'var(--s-2) var(--s-3)', border: '1px solid var(--line)', borderRadius: 'var(--r-s)', background: 'var(--card)', font: 'var(--t-cuerpo)' } });
    const resumen = h('p', { class: 'sub', 'aria-live': 'polite', style: { margin: 0 } }, 'Elige un hueco.');
    const porque = h('p', { class: 'sub', 'aria-live': 'polite', style: { margin: 0 } });
    const chips = h('div', { class: 'pila', style: { gap: 'var(--s-2)' } });
    const marcar = v => {
      elegido = v;
      chips.querySelectorAll('button[data-hueco]').forEach(b => { const on = b.dataset.hueco === v; b.classList.toggle('pri', on); b.setAttribute('aria-pressed', String(on)); });
      const t = instanteMadrid(v);
      resumen.textContent = v ? `${diaLargo(v.slice(0, 10))} a las ${v.slice(11)} en España${zonaYo !== ZONA_RO ? ` (tus ${horaEn(t, zonaYo)})` : ''} · 45 min con Tomás` : 'Elige un hueco.';
    };
    if (dias.length) {
      for (const dia of dias) {
        chips.append(h('div', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'wrap', alignItems: 'center' } },
          h('b', { style: { minWidth: '92px', font: 'var(--t-meta)', textTransform: 'capitalize' } }, diaLargo(dia)),
          huecos[dia].map(hh => { const v = `${dia} ${hh}`; return h('button', { type: 'button', class: 'bt mini', 'data-hueco': v, 'aria-pressed': 'false',
            title: zonaYo !== ZONA_RO ? `${hh} en España · tus ${horaEn(instanteMadrid(v), zonaYo)}` : `${hh} en España`, on: { click: () => marcar(v) } }, hh); })));
      }
    } else {
      const fd = h('input', { type: 'date', class: 'campo', min: hoy, 'aria-label': 'Día de la cita' });
      const fh = h('input', { type: 'time', class: 'campo', step: '900', 'aria-label': 'Hora de la cita (España)' });
      const alCambiar = () => marcar(fd.value && fh.value ? `${fd.value} ${fh.value}` : null);
      fd.addEventListener('change', alCambiar); fh.addEventListener('change', alCambiar);
      chips.append(avisoParcial('No tengo los huecos libres del calendario de Tomás: pon día y hora (de España) a mano y compruébalo en GoHighLevel.', { titulo: 'A mano.' }),
        h('div', { class: 'fila', style: { gap: 'var(--s-2)' } }, fd, fh));
    }
    const notasCita = h('textarea', { class: 'campo', rows: 3, maxlength: '1500', 'aria-label': 'Notas de la cita para Tomás', placeholder: 'Notas para Tomás (las verá en la cita)',
      style: { width: '100%', padding: 'var(--s-2) var(--s-3)', border: '1px solid var(--line)', borderRadius: 'var(--r-s)', background: 'var(--card)', font: 'var(--t-cuerpo)' } });
    const botonIA = h('button', { type: 'button', class: 'bt', style: { minHeight: 'var(--s-10)' }, title: 'Propone hueco, título y notas a partir de tus notas de la llamada. Lo revisas tú.',
      'aria-disabled': ctx.soloLectura ? 'true' : null }, icono('spark'), 'Claude te lo rellena');
    botonIA.addEventListener('click', async () => {
      if (ctx.soloLectura) return;
      botonIA.disabled = true; botonIA.lastChild.textContent = 'Pensando…';
      try {
        const r = await ctx.api('setters/propuesta_cita', { metodo: 'POST', cuerpo: { lead: x.id, notas: notasLlamada.value } });
        if (r.dia && r.hora) marcar(`${r.dia} ${r.hora}`);
        if (r.titulo) titulo.value = r.titulo;
        if (r.notas) notasCita.value = r.notas;
        ayuda = r.origen;
        porque.replaceChildren(icono('info', { clase: 's' }), ` ${r.origen === 'ia' ? 'Propuesta de Claude' : 'Propuesta por reglas (sin IA)'}: ${r.porque || ''}. Revísalo antes de guardar.${r.aviso ? ' ' + r.aviso : ''}`);
      } catch (e) { porque.textContent = `No se pudo proponer: ${e.message || e}`; }
      botonIA.disabled = false; botonIA.lastChild.textContent = 'Claude te lo rellena';
    });
    const resultado = h('div', { 'aria-live': 'polite' });
    const guardar = h('button', { type: 'button', class: 'bt pri', style: { minHeight: 'var(--s-12)', justifyContent: 'center' }, 'aria-disabled': ctx.soloLectura ? 'true' : null },
      icono('cal'), reagenda ? 'Guardar la nueva hora' : 'Guardar cita');
    guardar.addEventListener('click', async () => {
      if (ctx.soloLectura || guardar.disabled) return;
      if (!elegido) { resultado.replaceChildren(avisoParcial('Falta elegir el día y la hora.', { titulo: 'Antes de guardar.' })); return; }
      guardar.disabled = true;
      try {
        const r = await encolar(ctx, { que: 'crear_cita_ghl', sobre: x.id, herramienta: 'ghl', texto: `Cita ${elegido}`,
          vista: { inicio: elegido, titulo: titulo.value, notas: [notasCita.value, notasLlamada.value && notasCita.value.indexOf(notasLlamada.value) < 0 ? `Llamada: ${notasLlamada.value}` : ''].filter(Boolean).join('\n'), ayuda_ia: ayuda, reagenda: reagenda || null } });
        pedidas.set(x.id, r?.texto || `Cita ${elegido}`);
        resultado.replaceChildren(h('div', { class: 'pila', style: { gap: 'var(--s-2)', padding: 'var(--s-3)', borderRadius: 'var(--r-s)', background: 'var(--card)', border: '1px solid var(--line)' } },
          h('b', { class: 'fila', style: { gap: 'var(--s-2)' } }, icono('ok'), r?.pendiente || 'Guardada en la app · pendiente de GoHighLevel (simulación)'),
          h('span', { class: 'sub' }, `${r?.texto || elegido}. Hoy NO se crea en GoHighLevel: queda en la cola hasta que Tomás active la escritura. Si la necesitas ya, créala a mano con «Abrir en GoHighLevel».`)));
        guardar.replaceChildren(icono('ok'), 'Guardada');
        avisoFlotante('Cita guardada · pendiente de GoHighLevel');
      } catch (e) {
        guardar.disabled = false;
        resultado.replaceChildren(avisoParcial(e.message || String(e), { titulo: 'No se ha guardado.' }));
      }
    });
    caja.append(
      h('div', { class: 'fila', style: { justifyContent: 'space-between', gap: 'var(--s-2)' } }, h('b', {}, icono('cal'), reagenda ? ' Nueva hora para la reunión' : ' Agendar cita'),
        h('span', { class: 'sub' }, `${d.huecos?.calendario || 'Reunión de 45 min'} · con Tomás`)),
      notasLlamada, h('div', { class: 'fila', style: { gap: 'var(--s-2)' } }, botonIA), porque,
      h('div', { class: 'pila', style: { gap: 'var(--s-1)' } }, h('span', { class: 'titulo-seccion' }, 'Día y hora (España)'), chips, resumen),
      h('label', { class: 'pila', style: { gap: 'var(--s-1)' } }, h('span', { class: 'titulo-seccion' }, 'Tipo y título'), titulo),
      notasCita,
      vistaPrevia('al guardar va a la cola como «Crear cita en GoHighLevel»; no se crea nada en GoHighLevel hasta que Tomás active la escritura.'),
      h('div', { class: 'fila', style: { gap: 'var(--s-2)' } }, guardar, abrirEn('GoHighLevel', x.ghl, { mini: false })),
      resultado);
    return caja;
  }

  // ---------------------------------------------------------------- fila de un lead sin cita (sección 2)
  function filaLead(l) {
    const pedida = pedidas.get(l.id);
    const quedan = horasSegundaRO(l.segunda_vence);
    const detalle = l.lista === 'segunda'
      ? `${l.intentos} intento${l.intentos === 1 ? '' : 's'} · último ${cuandoTexto(l.ultima_llamada)}${quedan === null ? '' : quedan < 0 ? ` · segunda llamada vencida hace ${-quedan} h` : ` · segunda llamada en ${quedan} h`}`
      : `${limpiaTexto(l.motivo || '')} · esperando ${duracionTexto(l.min)}`;
    const hueco = h('div', { hidden: !abiertos.has(l.id) });
    if (abiertos.has(l.id)) hueco.append(formAgendar(l));
    const agendar = h('button', { type: 'button', class: `bt${pedida ? '' : ' pri'}`, 'aria-expanded': String(abiertos.has(l.id)), style: { minHeight: 'var(--s-12)', justifyContent: 'center' },
      'aria-disabled': ctx.soloLectura ? 'true' : null, title: ctx.soloLectura ? 'Estás en «ver como»: solo lectura' : 'Abre el formulario corto con los huecos libres de Tomás' },
    icono('cal'), pedida ? 'Cita pedida · cambiar' : 'Agendar cita');
    agendar.addEventListener('click', () => {
      if (ctx.soloLectura) return;
      const abrir = hueco.hidden; hueco.hidden = !abrir; agendar.setAttribute('aria-expanded', String(abrir));
      if (abrir) { abiertos.add(l.id); if (!hueco.childNodes.length) hueco.append(formAgendar(l)); } else abiertos.delete(l.id);
    });
    // resultado (un clic) + nota rápida
    const resHueco = h('div', { hidden: true });
    const resBtn = h('button', { type: 'button', class: 'bt', 'aria-expanded': 'false', style: { minHeight: 'var(--s-12)', justifyContent: 'center' },
      'aria-disabled': ctx.soloLectura ? 'true' : null }, icono('editar'), 'Resultado o nota');
    resBtn.addEventListener('click', () => {
      if (ctx.soloLectura) return;
      const abrir = resHueco.hidden; resHueco.hidden = !abrir; resBtn.setAttribute('aria-expanded', String(abrir));
      if (abrir && !resHueco.childNodes.length) resHueco.append(botoneraLead(l));
    });
    const contacto = aTodoElAncho(contactoZadarma(ctx, { almacen: almacenDe(l), x: l, ext: extDe(l.setter) }));
    return h('li', { class: 'panel', 'data-lead': l.id, style: { listStyle: 'none' } },
      h('div', { class: 'cuerpo pila', style: { gap: 'var(--s-3)' } },
        h('div', { style: { minWidth: 0 } },
          h('div', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'wrap' } }, h('span', { style: { font: 'var(--t-h2)', overflowWrap: 'anywhere' } }, nombreLead(l)), chipGrupo(l.grupo),
            l.lista === 'segunda' ? chipEstado(quedan !== null && quedan < 0 ? 'rojo' : 'ambar', 'Segunda llamada') : null,
            pedida ? chipEstado('azul', 'Cita pedida · pendiente de GoHighLevel') : null),
          h('div', { class: 'sub' }, detalle, l.sin_tel ? ' · no dejó teléfono' : '', l.aviso_tel && !l.sin_tel ? ' · teléfono raro: revísalo en GoHighLevel' : '', quien(l)),
          notas.get(l.id) ? h('div', { class: 'sub', style: { marginTop: 'var(--s-1)' } }, icono('editar', { clase: 's' }), ` Tu nota: ${notas.get(l.id)}`) : null),
        contacto,
        h('div', { style: { display: 'grid', gap: 'var(--s-2)', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 130px), 1fr))' } }, agendar, resBtn),
        hueco, resHueco,
        h('div', { class: 'fila', style: { gap: 'var(--s-2)' } }, abrirEn('GoHighLevel', l.ghl), masDe(nombreLead(l), verCompleto(l), abrirEn('Zadarma', d.enlaces?.zadarma_estadisticas)))));
  }
  function botoneraLead(l) {
    const nota = h('input', { type: 'text', class: 'campo', maxlength: '300', value: borradoresNotas.get(l.id) || '', placeholder: 'Nota rápida (opcional)', 'aria-label': `Nota sobre ${nombreLead(l)}`,
      style: { width: '100%', minHeight: 'var(--s-10)', padding: 'var(--s-2) var(--s-3)', border: '1px solid var(--line)', borderRadius: 'var(--r-s)', background: 'var(--card)', font: 'var(--t-cuerpo)' } });
    nota.addEventListener('input', () => borradoresNotas.set(l.id, nota.value));
    const soloNota = h('button', { type: 'button', class: 'bt mini' }, icono('editar'), 'Guardar solo la nota');
    soloNota.addEventListener('click', async () => {
      if (ctx.soloLectura || soloNota.disabled || pendientesApunte.has(l.id)) return;
      const t = nota.value.trim();
      if (!t) { nota.focus(); return; }
      soloNota.disabled = true;
      try { await encolar(ctx, { que: 'nota', sobre: l.id, herramienta: 'app', texto: t, vista: 'Nota interna del lead (queda en la app)' }); notas.set(l.id, t); borradoresNotas.delete(l.id); dibujar(); avisoFlotante('Nota guardada'); }
      catch (e) { soloNota.disabled = false; avisoFlotante(e.message || 'No se pudo guardar', { icono: 'alert' }); }
    });
    return h('div', { class: 'pila', style: { gap: 'var(--s-2)' } },
      h('div', { style: { display: 'grid', gap: 'var(--s-2)', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 140px), 1fr))' } },
        OPCIONES_LEAD.map(o => h('button', { type: 'button', class: 'bt', 'data-resultado': o, style: { minHeight: 'var(--s-12)', justifyContent: 'center', whiteSpace: 'normal', lineHeight: '1.2' },
          on: { click: () => apuntar(l, 'resultado_llamada', o, nota.value.trim()) } }, icono(ICO_RES(o)), o))),
      h('div', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'nowrap' } }, nota, soloNota),
      h('p', { class: 'sub', style: { margin: 0 } }, 'Un clic y se guarda (8 s para deshacer). El lead sale de la lista hasta mañana.'));
  }
  function filaPasada(c) {
    return h('li', { class: 'panel', style: { listStyle: 'none' } }, h('div', { class: 'cuerpo pila', style: { gap: 'var(--s-2)' } },
      h('div', {}, h('b', {}, nombreLead(c)), h('div', { class: 'sub' }, `${cuandoTexto(c.cuando)} · tarjeta: ${c.etapa}${c.grabada_zadarma ? ' · hubo llamada contestada ese día' : ''}${quien(c)}`)),
      h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-2)' } }, OPCIONES_PASADA.map(o => h('button', { type: 'button', class: 'bt mini', 'aria-disabled': ctx.soloLectura ? 'true' : null,
        on: { click: () => { if (!ctx.soloLectura) apuntar(c, 'resultado', o); } } }, icono(ICO_RES(o)), o))),
      h('div', { class: 'fila' }, abrirEn('GoHighLevel', c.ghl))));
  }

  // ---------------------------------------------------------------- dibujo
  function dibujar() {
    const { citasHoy, citasLuego, sinCita, hechosHoy, pasadas } = listas();
    const quienes = ver ? [ver] : ['ana', 'javier'];
    const sumar = (k, f = hoyDe) => (quienes.some(s => f(s)[k] === null || f(s)[k] === undefined) ? null : quienes.reduce((t, s) => t + f(s)[k], 0));
    const marc = sumar('marcaciones');
    const confirmadas = citasHoy.filter(c => estadoCita(apuntados.get(c.id))?.t === 'Confirmada').length;
    const pedidasHoy = [...pedidas.keys()].filter(id => leadsT.some(l => l.id === id)).length;

    if (resumen) {
      raiz.replaceChildren(pantallaTrabajo({ id: 'setters', consejo: true,
        lista: panel({ titulo: 'Recuento por setter', icono: 'users', sub: 'Cuántos hay en cada lista, sin datos de los leads.' },
          h('div', { class: 'cuerpo' }, tablaApilable({ filas: (d.recuento || []).map(r => ({ ...r, setter: nombreSetter(ctx, r.quien), llamadas: hoyDe(r.quien).marcaciones })),
            columnas: [{ clave: 'setter', titulo: 'Setter', principal: true }, { clave: 'citas', titulo: 'Reuniones por confirmar', num: true },
              { clave: 'llamar_ya', titulo: 'Sin cita (para llamar)', num: true }, { clave: 'segundas', titulo: 'Segundas', num: true },
              { clave: 'pasadas', titulo: 'Sin resultado', num: true }, { clave: 'llamadas', titulo: 'Llamadas hoy', num: true, celda: r => r.llamadas ?? 'sin dato' }] }))),
        contexto: [pie(ctx, d, meta)] }));
      return;
    }

    const franja = franjaCifras([
      { etiqueta: 'Confirmadas hoy', valor: citasHoy.length ? `${confirmadas} de ${citasHoy.length}` : '0', estado: confirmadas < citasHoy.length ? 'rojo' : '', titulo: 'Reuniones de hoy marcadas «Confirmada»' },
      { etiqueta: 'Sin cita', valor: sinCita.length, estado: sinCita.length ? 'rojo' : '', titulo: 'Leads que todavía no tienen cita' },
      { etiqueta: 'Citas pedidas', valor: pedidasHoy, titulo: 'Citas guardadas desde la app (pendientes de GoHighLevel)' },
      { etiqueta: 'Llamadas', valor: marc === null ? 'sin dato' : marc, titulo: marc === null ? 'Falta confirmar tu extensión de Zadarma' : 'Llamadas de hoy por tu extensión de Zadarma' },
    ], { etiqueta: 'Tu marcador de hoy' });
    franjaEnLinea(franja);

    // 1 · confirmar las reuniones de hoy
    const sec1 = h('section', { class: 'pila', 'aria-label': 'Paso 1: confirmar las reuniones de hoy', 'data-paso': '1', style: { gap: 'var(--s-3)' } },
      titulo2(1, `Confirma las reuniones de hoy${citasHoy.length ? ` · ${confirmadas} de ${citasHoy.length}` : ''}`,
        citasHoy.length ? 'Llama (o escribe por WhatsApp) y marca cómo ha ido. Nunca cambies el estado de la cita en GoHighLevel.' : null),
      citasHoy.length
        ? h('ul', { class: 'pila', style: { gap: 'var(--s-3)', margin: 0, padding: 0 } }, citasHoy.map(filaCita))
        : vacio({ icono: 'ok', titulo: 'Hoy no hay reuniones que confirmar', texto: citasLuego.length ? 'Puedes adelantar las del siguiente día laborable (abajo) o pasar al paso 2.' : 'Pasa al paso 2: meter en agenda a quien no tiene cita.', tono: 'celebrar', borde: true }),
      citasLuego.length ? (() => {
        const det = h('details', { class: 'panel' }, h('summary', { class: 'cuerpo', style: { cursor: 'pointer', minHeight: 'var(--s-12)', font: 'var(--t-h2)' } },
          `Adelantar: ${citasLuego.length} ${citasLuego.length === 1 ? 'reunión' : 'reuniones'} del ${diaLargo(citasLuego[0].cuando.slice(0, 10))}`));
        det.addEventListener('toggle', () => { if (det.open && det.childNodes.length === 1) det.append(h('ul', { class: 'pila cuerpo', style: { gap: 'var(--s-3)', margin: 0 } }, citasLuego.map(filaCita))); });
        return det;
      })() : null);

    // 2 · meter en agenda a quien no tiene cita
    const visibles = sinCita.slice(0, 8);
    const sec2 = h('section', { class: 'pila', 'aria-label': 'Paso 2: meter en agenda a quien no tiene cita', 'data-paso': '2', style: { gap: 'var(--s-3)' } },
      titulo2(2, `Mete en agenda a quien no tiene cita · ${sinCita.length}`, 'Primero quien pidió reunión y no encontró hueco; dentro, el más reciente. Cuando diga que sí: «Agendar cita».'),
      sinCita.length
        ? h('ul', { class: 'pila', style: { gap: 'var(--s-3)', margin: 0, padding: 0 } }, visibles.map(filaLead))
        : vacio({ icono: 'ok', titulo: 'Nadie sin cita esperando', texto: hechosHoy.length ? `Lista al día: ${hechosHoy.length} con resultado hoy.` : 'Tienes la lista al día.', tono: 'celebrar', borde: true }),
      sinCita.length > visibles.length ? masLista(sinCita.slice(visibles.length).map(filaLead), `Ver los otros ${sinCita.length - visibles.length}`) : null,
      hechosHoy.length ? h('p', { class: 'sub', style: { margin: 0 } }, `${hechosHoy.length} con resultado apuntado hoy (vuelven mañana si toca).`) : null);

    // 3 · citas pasadas sin resultado (solo si hay)
    const sec3 = pasadas.length ? h('section', { class: 'pila', 'aria-label': 'Citas que ya pasaron sin resultado', style: { gap: 'var(--s-3)' } },
      titulo2(3, `Apunta cómo fueron · ${pasadas.length}`, 'Citas que ya pasaron y GoHighLevel no marcó.'),
      h('ul', { class: 'pila', style: { gap: 'var(--s-2)', margin: 0, padding: 0 } }, pasadas.map(filaPasada))) : null;

    // contexto: informe de fin de día, marcador y llamadas perdidas
    const comparar = ctx.ver({ tipo: 'comparar_personas' }).nivel === 'completo';
    const filasM = ['ana', 'javier'].filter(s => !yo || s === yo || comparar).map(s => ({
      setter: nombreSetter(ctx, s), hoy: hoyDe(s).marcaciones, conv: hoyDe(s).conversaciones, citas: hoyDe(s).citas_medibles ? hoyDe(s).citas : null, semana: semDe(s).marcaciones }));
    const sd = v => (v === null || v === undefined ? h('span', { class: 'sub' }, 'sin dato') : fmt.num(v));
    const marcador = panel({ titulo: 'Marcador', icono: 'grafico', sub: 'Llamadas por extensión de Zadarma y citas con la etiqueta de cada setter.' },
      h('div', { class: 'cuerpo' }, tablaApilable({ filas: filasM, columnas: [
        { clave: 'setter', titulo: 'Setter', principal: true }, { clave: 'hoy', titulo: 'Llamadas hoy', num: true, celda: r => sd(r.hoy) },
        { clave: 'conv', titulo: 'Pasan del minuto', num: true, celda: r => sd(r.conv) }, { clave: 'citas', titulo: 'Citas hoy', num: true, celda: r => sd(r.citas) },
        { clave: 'semana', titulo: 'Llamadas semana', num: true, celda: r => sd(r.semana) }] }),
      h('div', { class: 'fila', style: { marginTop: 'var(--s-3)' } }, frescura(fZD), frescura(fGHL), abrirEn('Zadarma', d.enlaces?.zadarma_estadisticas))));
    const perdidas = d.perdidas || [];
    const panelPerdidas = panel({ titulo: 'Llamadas perdidas o sin ficha', icono: 'phone', sub: yo ? 'Las que entraron por tu extensión en 48 h.' : 'Entrantes de 48 h sin contestar o de números sin ficha en GoHighLevel.' },
      perdidas.length ? h('div', { class: 'cuerpo' }, tablaApilable({ filas: perdidas, columnas: [
        { clave: 'cuando', titulo: 'Cuándo', principal: true, celda: p => cuandoTexto(p.cuando) },
        { clave: 'tel_m', titulo: 'Número', celda: p => h('span', { style: { color: 'var(--mid)', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' } }, p.tel_m) },
        { clave: 'perdida', titulo: 'Qué pasó', celda: p => [p.perdida ? chipEstado('rojo', 'Sin contestar') : chipEstado('gris', `${p.seg} s`), ' ', p.sin_ficha ? chipEstado('ambar', 'Sin ficha') : null] },
        { clave: 'ghl', titulo: 'Atajo', celda: p => (p.ghl ? abrirEn('GoHighLevel', p.ghl) : abrirEn('Zadarma', d.enlaces?.zadarma_estadisticas)) },
      ] })) : h('div', { class: 'cuerpo' }, vacioLinea(yo ? 'Ninguna llamada perdida. Cuando tu extensión de Zadarma esté confirmada, aquí saldrán las que no cojas.' : 'Ninguna llamada perdida en 48 h.', { icono: 'ok' })));
    const informe = (yo || ver) ? informeFinDeDia(ctx, { yo: ver, mh: hoyDe(ver), pasadas: pasadas.length, cola, confirmadas, citasHoy: citasHoy.length, pedidas: pedidasHoy }) : null;
    if (informe) informe.id = 'setters-informe';
    const irInforme = informe && horaMadridAhora() >= 17 ? h('div', { style: { position: 'sticky', bottom: 'var(--s-3)', zIndex: '4', display: 'flex', justifyContent: 'center' } },
      h('button', { type: 'button', class: 'bt pri', style: { minHeight: 'var(--s-12)', boxShadow: 'var(--shadow-up)' }, on: { click: () => {
        const det = informe.closest('details'); if (det) det.open = true;
        informe.scrollIntoView({ behavior: 'smooth', block: 'start' });
      } } }, icono('doc'), 'Informe de fin de día')) : null;

    raiz.replaceChildren(pantallaTrabajo({
      id: 'setters', filtros: h('div', { class: 'pila', style: { gap: 'var(--s-2)' } }, chipsVer, franja),
      lista: h('div', { class: 'pila', style: { gap: 'var(--s-6)', minWidth: '0' } }, sec1, sec2, sec3, irInforme),
      contexto: [informe, marcador, panelPerdidas, pie(ctx, d, meta)].filter(Boolean),
      tituloContexto: 'Informe del día, marcador y llamadas perdidas',
    }));
  }
  dibujar();
}

/** «Ver los otros N»: el resto de la lista, plegado. */
function masLista(items, texto) {
  const det = h('details', { class: 'mas-lista' }, h('summary', { class: 'bt', style: { listStyle: 'none', cursor: 'pointer', display: 'inline-flex', minHeight: 'var(--s-10)' } }, icono('mas'), texto));
  det.addEventListener('toggle', () => {
    if (det.open && det.childNodes.length === 1) det.append(h('ul', { class: 'pila', style: { gap: 'var(--s-3)', margin: 'var(--s-3) 0 0', padding: 0 } }, items));
  });
  return det;
}

function informeFinDeDia(ctx, { yo, mh, pasadas, cola, confirmadas, citasHoy, pedidas }) {
  const mios = cola.filter(a => a.que === 'informe_fin_de_dia').slice(-3).reverse();
  const n = v => (v === null || v === undefined ? '' : String(v));
  const f = {
    marc: campo({ etiqueta: 'Llamadas hechas', nombre: 'marc', tipo: 'number', valor: n(mh.marcaciones), min: 0 }),
    conv: campo({ etiqueta: 'Pasan del minuto', nombre: 'conv', tipo: 'number', valor: n(mh.conversaciones), min: 0 }),
    citas: campo({ etiqueta: 'Citas agendadas', nombre: 'citas', tipo: 'number', valor: n(pedidas || (mh.citas_medibles ? mh.citas : '')), min: 0 }),
    conf: campo({ etiqueta: `Confirmadas (de ${citasHoy || 0})`, nombre: 'conf', tipo: 'number', valor: n(confirmadas), min: 0 }),
    dudas: campo({ etiqueta: 'Dudas y bloqueos', nombre: 'dudas', tipo: 'textarea', filas: 3, ayuda: 'Lo que necesitas de Tomás o de quien te dirija.' }),
  };
  let notaDia = '';
  const chipsNota = chipsFiltro({ etiqueta: 'Nota del día', opciones: [{ valor: '', texto: 'Sin elegir' }, ...Array.from({ length: 10 }, (_, i) => ({ valor: String(i + 1), texto: String(i + 1) }))],
    valor: '', alCambiar: v => { notaDia = v || ''; } });
  const val = k => f[k].querySelector('input,textarea').value.trim();
  return panel({ titulo: 'Informe de fin de día', icono: 'doc', sub: 'Números, dudas y nota del 1 al 10, el mismo día.' },
    h('div', { class: 'cuerpo pila' },
      h('div', { style: { display: 'grid', gap: 'var(--s-3)', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 150px), 1fr))' } }, f.marc, f.conv, f.citas, f.conf),
      f.dudas, chipsNota,
      pasadas ? avisoParcial(`Te ${pasadas === 1 ? 'queda 1 cita' : `quedan ${pasadas} citas`} sin resultado: ${pasadas === 1 ? 'apúntala' : 'apúntalas'} antes de cerrar el día.`, { titulo: 'Antes de enviar.' }) : null,
      vistaPrevia('el informe queda guardado con tu nombre y la hora; lo ven Tomás y quien dirija a los setters.'),
      botonDeshacer({ texto: 'Enviar informe de hoy', hecho: 'Informe enviado', mini: false, pri: true, icono: 'send', soloLectura: ctx.soloLectura,
        validar: () => (notaDia ? null : 'Falta la nota del día'),
        alHacer: async () => {
          const nt = notaDia;
          await encolar(ctx, { que: 'informe_fin_de_dia', sobre: yo || ctx.persona.id, herramienta: 'app',
            texto: `llamadas ${val('marc') || '—'} · pasan del minuto ${val('conv') || '—'} · citas ${val('citas') || '—'} · confirmadas ${val('conf') || '—'} · nota ${nt}${val('dudas') ? ' · dudas: ' + val('dudas') : ''}` });
          return 'Informe guardado · queda en el rastro';
        } }),
      mios.length ? h('div', {}, h('p', { class: 'titulo-seccion' }, icono('hist'), 'Tus últimos informes'),
        h('ul', { class: 'lista-i', style: { marginTop: 'var(--s-1)' } }, mios.map(a => h('li', {}, h('span', { class: 'ico-c s gris' }, icono('doc')), h('span', { class: 't', style: { whiteSpace: 'normal' } }, h('b', {}, fechaHora(a.hora)), ` · ${a.texto}`))))) : null));
}

function pie(ctx, d, meta) {
  const avisos = [...(d.avisos || [])];
  if ((d.leads || []).some(l => l.reparto === 'simulado')) avisos.unshift('El reparto entre los dos setters es todavía una simulación: cuando cada lead lleve su etiqueta en GoHighLevel, manda la etiqueta.');
  if (!d.huecos?.dias || !Object.keys(d.huecos.dias).length) avisos.push('Sin huecos libres leídos del calendario de 45 min: «Agendar cita» pide día y hora a mano.');
  return h('details', { class: 'panel' },
    h('summary', { class: 'cuerpo fila', style: { cursor: 'pointer', minHeight: 'var(--s-12)', font: 'var(--t-h2)', color: 'var(--mid)' } },
      icono('info'), 'Lo que falta para que funcione del todo'),
    h('ul', { class: 'cuerpo', style: { margin: 0, paddingTop: 0, paddingLeft: 'var(--s-10)', display: 'grid', gap: 'var(--s-1)', maxWidth: '72ch' } },
      avisos.map(a => h('li', {}, limpiaTexto(a))),
      h('li', {}, 'Llamar abre la app de Zadarma con el número (nunca otra app) y el intento queda apuntado. WhatsApp abre WhatsApp; el mensaje lo escribes tú.'),
      h('li', {}, `«Agendar cita» guarda la cita en la app y la deja en la cola como «Crear cita en GoHighLevel»: hoy no se crea nada allí (simulación). Huecos leídos ${d.huecos?.leido ? `el ${fechaCorta(d.huecos.leido.slice(0, 10))} a las ${d.huecos.leido.slice(11)}` : 'nunca'}.`),
      h('li', {}, 'Todavía no se mide: citas celebradas por setter, minutos exactos hasta el primer intento y la nota de calidad de cada llamada.')),
    h('div', { class: 'fila', style: { padding: '0 var(--relleno) var(--s-4)' } }, frescura(fresco(meta, 'GoHighLevel (subcuenta RO)', 'GoHighLevel')), frescura(fresco(meta, 'Zadarma')),
      abrirEn('GoHighLevel · calendario', d.enlaces?.ghl_calendario), abrirEn('GoHighLevel · conversaciones', d.enlaces?.ghl_conversaciones)));
}

export default {
  id: 'setters',
  titulo: 'Mi día del setter',
  grupo: 'Ventas de RO',
  puestos_que_lo_ven: { setters: 'suyo', direccion: 'todo', ventas_ro: 'todo', jefa_crm: 'resumen', operaciones: 'resumen' },
  async render(contenedor, ctx) { await pintar(contenedor, ctx, undefined); },
};
