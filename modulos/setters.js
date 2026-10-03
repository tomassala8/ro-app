// modulos/setters.js · «Mi día del setter» (E6). Móvil a 390 px primero y con una mano.
// Orden: tu siguiente llamada → cifras del día → pestañas (Llamar ya · Segundas · Citas · Sin resultado) →
// marcador → llamadas perdidas → informe de fin de día. Solo la subcuenta de RO: nada de clientes de la agencia.
// El setter recibe el nombre de sus leads (servidor, D-88); teléfono y correo, en el clic de Llamar/WhatsApp/correo.

import { h, fmt, semaforo, tile, vacioLinea, listaLoPrimero, tablaApilable, chipEstado, chipsFiltro, pestanas, vacio,
  botonConfirmar, avisoParcial, panel, frescura, icono, limpiaTexto, hoyMadrid, sumarDias, fechaCorta } from '../componentes.js';
import { cargar, setterDe, nombreSetter, fresco, duracionTexto, cuandoTexto, minutosDesde, nombreLead, encolar, leerCola,
  vistaPrevia, abrirEn, masAcciones, contactoLead, verDatos, chipGrupo, campo } from './_ventas_comun.js';
import { pantallaTrabajo, franjaCifras } from './_trabajo.js';
import { franjaEnLinea } from './_trabajo_ancho.js';
import { conDeshacer, botonDeshacer } from './_deshacer.js';

/** V2 · «hoy» real: el día de la cita se cuenta con la fecha de Madrid de hoy (helper común), no con el día en que se
 *  leyó GoHighLevel (un sábado, «mañana» del viernes ya es hoy). */
const DIAS_S = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
function diaRel(cuando, hoy = hoyMadrid()) {
  const d = String(cuando || '').slice(0, 10);
  if (!d) return '';
  if (d === hoy) return 'hoy';
  if (d === sumarDias(hoy, 1)) return 'mañana';
  if (d < hoy) return `el ${DIAS_S[new Date(d + 'T12:00').getDay()]} (ya pasó)`;
  return `el ${DIAS_S[new Date(d + 'T12:00').getDay()]}`;
}
const relojLead = min => semaforo(min, { verde: 5, ambar: 60, mejorSi: 'bajo' });   // primer intento: < 5 min · 5-60 · > 1 h

// ----------------------------------------------------------------- piezas de presentación (solo tokens y clases comunes)
/** Rejilla de tarjetas: 3 + 3 en el ordenador y 2 + 2 + 2 en el móvil (sin carrusel cortado ni tarjeta suelta). */
const rejilla2a3 = lista => h('div', { role: 'list', style: { display: 'grid', gap: 'var(--s-4)',
  gridTemplateColumns: 'repeat(auto-fit, minmax(max(150px, calc((100% - 2 * var(--s-4)) / 3)), 1fr))' } },
lista.map(x => { x.setAttribute('role', x.getAttribute('role') || 'listitem'); x.style.minWidth = '0'; return x; }));
/** tile() sin «—» gigante: sin dato, la cifra pasa a una línea gris («Sin dato · …») en letra de metadatos (guía 3.7). */
function tileSD(o) {
  const t = tile(o);
  if (o.valor === null || o.valor === undefined || o.valor === '') {
    const tv = t.querySelector('.tv');
    if (tv) tv.replaceChildren(h('span', { style: { font: 'var(--t-meta)', color: 'var(--dim)', letterSpacing: '0' } }, o.sinDato || 'Sin dato'));
  }
  return t;
}
/** Botones de contacto a todo el ancho en el móvil (48 px, con una mano) y en fila en el ordenador. */
function aTodoElAncho(el) {
  if (el && el.classList?.contains('fila')) Object.assign(el.style, { display: 'grid', gap: 'var(--s-2)', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 140px), 1fr))' });
  el?.querySelectorAll?.('button, a').forEach(b => { b.style.minHeight = 'var(--s-12)'; b.style.justifyContent = 'center'; });
  return el;
}
/** «2-oct, 17:34» (44 §2.3), con la hora de Madrid. */
const fechaHora = t => {
  const d = t ? new Date(t) : null;
  if (!d || Number.isNaN(+d)) return '';
  const p = Object.fromEntries(new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Madrid', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
    .formatToParts(d).map(x => [x.type, x.value]));
  return `${fechaCorta(`${p.year}-${p.month}-${p.day}`)}, ${p.hour}:${p.minute}`;
};
/** V5 · «Más acciones» con el nombre del lead en aria-label (antes «Más» a secas, 94 por pantalla). V4: el menú parte línea. */
function masDe(nombre, ...botones) {
  const m = masAcciones(...botones);
  const s = m?.querySelector(':scope > summary');
  if (s) { s.lastChild.textContent = 'Más acciones'; s.setAttribute('aria-label', `Más acciones de ${nombre || 'este lead'}`); }
  const f = m?.querySelector(':scope > .fila');
  if (f) Object.assign(f.style, { flexWrap: 'wrap', minWidth: '0', maxWidth: '100%' });
  return m;
}

// ----------------------------------------------------------------- apuntar resultado
// Ronda U (3-oct, cambio #6 del 50): el resultado se apunta EN LA MISMA TARJETA donde se llama, con un botón por resultado
// (un clic = guardado). Es interno (queda en la app y, con permiso de GoHighLevel, irá como nota): sin «¿Seguro?», con
// «Deshacer» 8 s (modulos/_deshacer.js). Al guardar, la tarjeta pasa sola al siguiente lead.
const OPCIONES = {
  cita: ['Confirmada por teléfono', 'Confirmada por WhatsApp', 'No contesta: vuelvo a llamar', 'Quiere cambiar la hora', 'Cancela'],
  pasada: ['Se celebró', 'No se presentó', 'Se reprogramó', 'No lo sé: pregunto a Tomás'],
  lead: ['No contesta', 'Hablado: reserva por la web', 'Hablado: volver a llamar', 'Hablado: no encaja', 'Número erróneo'],
};
// Se guarda en la app (herramienta «app»): con «ghl» el servidor lo rechazaba (los leads de RO no son de un cliente) y el
// resultado se perdía. La nota en GoHighLevel llega con el permiso de escritura. Citas pasadas: «resultado» (resultado_cita
// es una acción que sale fuera y exige cliente).
const queDe = tipo => (tipo === 'pasada' ? 'resultado' : tipo === 'cita' ? 'confirmacion_cita' : 'resultado_llamada');
const ICO_RES = r => (/^No contesta|erróneo|Cancela|No se presentó|no encaja/.test(r) ? 'cerrar' : /reserva|Confirmada|Se celebró/.test(r) ? 'ok' : 'clock');

/** Botonera de resultados: un botón por resultado + nota opcional. alGuardar(resultado, nota) hace el resto. */
function botoneraResultado(ctx, { tipo, nombre, alGuardar, grande }) {
  const nota = h('input', { type: 'text', class: 'campo', maxlength: '300', placeholder: 'Nota (opcional): lo que pasaría a la ficha',
    'aria-label': `Nota sobre ${nombre || 'el lead'} (opcional)`, style: { width: '100%', minHeight: grande ? 'var(--s-12)' : 'var(--s-10)', padding: 'var(--s-2) var(--s-3)',
      border: '1px solid var(--line)', borderRadius: 'var(--r-s)', background: 'var(--card)', font: 'var(--t-cuerpo)' } });
  const botones = OPCIONES[tipo].map(o => h('button', { type: 'button', class: `bt${grande ? '' : ' mini'}`, 'data-resultado': o,
    'aria-disabled': ctx.soloLectura ? 'true' : null, title: ctx.soloLectura ? 'Estás en «ver como»: solo lectura' : `Apuntar «${o}»`,
    style: grande ? { minHeight: 'var(--s-12)', justifyContent: 'center', textAlign: 'center', whiteSpace: 'normal', lineHeight: '1.2' } : null,
    on: { click: () => { if (!ctx.soloLectura) alGuardar(o, nota.value.trim()); } } }, icono(ICO_RES(o)), o));
  return h('div', { class: 'pila', role: 'group', 'aria-label': `Resultado de ${nombre || 'la llamada'}`, style: { gap: 'var(--s-2)' } },
    h('div', { style: grande ? { display: 'grid', gap: 'var(--s-2)', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 140px), 1fr))' } : { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-2)' } }, botones),
    nota,
    h('p', { class: 'sub', style: { margin: 0 } }, tipo === 'lead' ? 'Un clic y se guarda (8 s para deshacer). La cita la reserva el titular en la web de RO, nunca a mano en GoHighLevel.'
      : tipo === 'pasada' ? 'Un clic y se guarda. «No se presentó» movería la tarjeta sin tocar el estado de la cita (manda WhatsApp).'
        : 'Un clic y se guarda. Nunca se cambia el estado de la cita en GoHighLevel.'));
}

/** Un lead como elemento de «Lo primero»: contacto en un clic, resultado en la fila y «Más acciones». */
function itemLead(ctx, d, x, { tipo, almacen, estado, icono: ico, detalle, guardar }) {
  const destino = h('span', {}, nombreLead(x));
  const hueco = h('div', { hidden: true, style: { gridColumn: '1 / -1' } });
  const apuntar = h('button', { type: 'button', class: 'bt', 'aria-expanded': 'false', style: { minHeight: '44px' },
    'aria-disabled': ctx.soloLectura ? 'true' : null, title: ctx.soloLectura ? 'Estás en «ver como»: solo lectura' : null },
  icono('editar'), tipo === 'cita' ? 'Apuntar' : 'Resultado');
  apuntar.addEventListener('click', () => {
    if (ctx.soloLectura) return;
    const abrir = hueco.hidden; hueco.hidden = !abrir; apuntar.setAttribute('aria-expanded', String(abrir));
    if (abrir && !hueco.childNodes.length) hueco.append(botoneraResultado(ctx, { tipo, nombre: nombreLead(x), alGuardar: (r, n) => guardar(x, tipo, r, n) }));
  });
  return {
    estado, icono: ico, motivo: h('span', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'wrap', minWidth: '0', maxWidth: '100%' } }, destino, tipo === 'lead' ? chipGrupo(x.grupo) : null),
    detalle: [detalle, hueco],
    botones: [
      tipo !== 'pasada' ? contactoLead(ctx, { almacen, x }) : null,
      apuntar,
      masDe(nombreLead(x),
        abrirEn('GHL', x.ghl),
        abrirEn('GHL · oportunidades', d.enlaces?.ghl_oportunidades),
        abrirEn('Zadarma', d.enlaces?.zadarma_estadisticas),
        verDatos(ctx, { almacen, id: x.id, destino }),
      ),
    ],
  };
}

/** La hora de la cola de acciones viene en UTC («2026-10-03 03:36:12»): día y hora en Madrid. */
const madridDe = t => {
  const s = String(t || '');
  const d = new Date(s.replace(' ', 'T') + (/[zZ]$|[+-]\d\d:?\d\d$/.test(s) ? '' : 'Z'));
  if (!s || Number.isNaN(+d)) return { dia: s.slice(0, 10), hora: s.slice(11, 16) };
  const p = Object.fromEntries(new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Madrid', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
    .formatToParts(d).map(x => [x.type, x.value]));
  return { dia: `${p.year}-${p.month}-${p.day}`, hora: `${p.hour}:${p.minute}` };
};
const horaMadrid = () => Number(new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Madrid', hour: '2-digit', hourCycle: 'h23' }).format(new Date()));

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
  // R12 (C-A1): en «Los dos» cada lead abre el almacén de SU setter (antes pedía setter_null → 404).
  const almacenDe = l => `setter_${ver || l?.setter}`;
  const mio = l => !ver || l.setter === ver;
  const fGHL = fresco(meta, 'GoHighLevel (subcuenta RO)', 'GoHighLevel');
  const fZD = fresco(meta, 'Zadarma');

  ctx.titulo(yo ? `Mi día · ${ctx.nombre(ctx.persona.id)}` : 'Setters', yo
    ? 'A quién llamar, qué confirmar y qué apuntar. Solo leads de Ranking Online.'
    : `El día de los setters${ver ? ' · ' + nombreSetter(ctx, ver) : ''}`);

  if (ctx.persona.puestos.includes('setters') && !yo) {
    cont.append(vacio({ icono: 'persona', titulo: 'No estás en el reparto', texto: 'Tu usuario tiene el puesto de setter pero no tiene leads asignados.', quien: 'Tomás', tono: 'aviso' }));
    return;
  }
  let chipsVer = null;
  if (!yo && !resumen) {
    chipsVer = chipsFiltro({ etiqueta: 'Ver', clave: 'setters.vista', valor: vista || '',
      opciones: [{ valor: '', texto: 'Los dos', icono: 'users' }, ...['ana', 'javier'].map(s => ({ valor: s, texto: nombreSetter(ctx, s), icono: 'persona',
        cuenta: (d.leads || []).filter(l => l.setter === s && l.lista === 'llamar_ya').length, cuentaEstado: 'rojo' }))],
      alCambiar: v => { cont.replaceChildren(); pintar(cont, ctx, v || null); } });
    if (vista === undefined) { const recordado = chipsVer.valor?.(); if (recordado) return pintar(cont, ctx, recordado); }
  }

  // Lo ya apuntado HOY (de la cola de acciones del módulo) sale de las listas: así la lista baja de verdad.
  const hoy = hoyMadrid();
  const apuntados = new Map();   // id → resultado
  for (const a of cola) if (['resultado_llamada', 'confirmacion_cita', 'resultado_cita', 'resultado'].includes(a.que) && madridDe(a.hora).dia === hoy) apuntados.set(a.sobre, a.texto);
  const saltados = [];           // «Siguiente» sin apuntar: van al final de la tarjeta

  const leadsT = (d.leads || []).filter(mio).map(l => ({ ...l, min: minutosDesde(l.entro) }));
  const citasT = (d.citas || []).filter(mio).map(c => ({ ...c, dia: diaRel(c.cuando) || c.dia }));
  const pasadasT = (d.pasadas || []).filter(mio);
  const hoyDe = s => (d.marcador || []).find(m => m.setter === s && m.periodo === 'hoy') || {};
  const semDe = s => (d.marcador || []).find(m => m.setter === s && m.periodo === 'semana') || {};
  const listas = () => {
    const vivo = x => !apuntados.has(x.id);
    return {
      llamarYa: leadsT.filter(l => l.lista === 'llamar_ya' && vivo(l)).sort((a, b) => (!!a.sin_tel - !!b.sin_tel) || a.min - b.min),
      segundas: leadsT.filter(l => l.lista === 'segunda' && vivo(l)).sort((a, b) => (a.segunda_vence || '').localeCompare(b.segunda_vence || '')),
      citas: citasT.filter(vivo),
      pasadas: pasadasT.filter(vivo),
    };
  };

  // Guardar un resultado (tarjeta o fila): la fila sale al momento, «Deshacer» 8 s, y se encola al acabar el plazo.
  const guardar = (x, tipo, resultado, nota) => {
    conDeshacer({
      mensaje: `«${resultado}» apuntado a ${nombreLead(x)}`,
      optimista: () => { apuntados.set(x.id, resultado); dibujar(); },
      revertir: () => { apuntados.delete(x.id); dibujar(); },
      hacer: () => encolar(ctx, { que: queDe(tipo), sobre: x.id, texto: `${resultado}${nota ? ' · ' + nota : ''}`, herramienta: 'app',
        vista: 'Queda en la app; con el permiso de GoHighLevel irá como nota en la ficha del lead' }),
    });
  };

  const raiz = h('div', { class: 'pila', style: { gap: 'var(--s-3)', minWidth: '0' } });
  cont.append(raiz);
  let pestanaActual = null;

  function dibujar() {
    const { llamarYa, segundas, citas, pasadas } = listas();
    const quien = l => (!ver ? ` · ${nombreSetter(ctx, l.setter)}` : '');
    let caja = null;

    // ---- franja de cifras: son los filtros (las pestañas) de la lista ----
    const quienes = ver ? [ver] : ['ana', 'javier'];
    const sumar = (k, f = hoyDe) => (quienes.some(s => f(s)[k] === null || f(s)[k] === undefined) ? null : quienes.reduce((t, s) => t + f(s)[k], 0));
    const marc = sumar('marcaciones'), conv = sumar('conversaciones');
    const pct = marc ? Math.round(100 * conv / marc) : null;
    const citasMedibles = quienes.every(s => hoyDe(s).citas_medibles);
    const citasHoy = citasMedibles ? sumar('citas') : null;
    // Franja de 48 px con el marcador del día (las listas ya llevan su cuenta en las pestañas, justo debajo de la tarjeta).
    const franja = franjaCifras([
      { etiqueta: 'Apuntados hoy', valor: apuntados.size, titulo: 'Resultados guardados hoy desde la app' },
      { etiqueta: 'Llamadas', valor: marc === null ? 'sin dato' : marc, titulo: marc === null ? 'Falta confirmar la extensión de Zadarma' : 'Llamadas de hoy por tu extensión de Zadarma' },
      { etiqueta: 'Pasan del minuto', valor: pct === null ? 'sin dato' : `${pct} %`, estado: pct !== null && pct < 10 ? 'rojo' : '', titulo: marc === null ? 'Falta confirmar la extensión de Zadarma' : `${conv} de ${marc} llamadas · bien desde el 17 %` },
      { etiqueta: 'Citas hoy', valor: citasHoy === null ? 'sin dato' : citasHoy, titulo: citasHoy === null ? 'Sin dato hasta que cada lead lleve la etiqueta de su setter' : 'Bien con 2 citas al día o más' },
    ], { etiqueta: 'Tu marcador de hoy' });
    franjaEnLinea(franja);

    // ---- 0 · tu siguiente llamada, con el resultado en la misma tarjeta ----
    let tarjeta = null;
    if (yo) {
      // V2 (C-11): la siguiente es la MÁS URGENTE (lead nuevo, primer intento en < 5 min); una confirmación pasa delante si
      // la reunión es hoy. «Siguiente» sin apuntar la manda al final.
      const sinConf = citas.filter(c => !c.confirmada_tel && !c.sin_tel);
      const candidatos = [...sinConf.filter(c => c.dia === 'hoy'), ...llamarYa.filter(l => !l.sin_tel), ...sinConf.filter(c => c.dia !== 'hoy'), ...segundas];
      const orden = [...candidatos.filter(x => !saltados.includes(x.id)), ...saltados.map(id => candidatos.find(x => x.id === id)).filter(Boolean)];
      const sig = orden[0];
      if (sig) {
        const esCita = !!sig.cita_id;
        const tipo = esCita ? 'cita' : 'lead';
        const verCompleto = (() => { const dest = h('span'); const b = verDatos(ctx, { almacen: almacenDe(sig), id: sig.id, destino: dest }); if (b) b.lastChild && (b.lastChild.textContent = 'Ver los datos del lead'); return b ? h('span', { class: 'fila', style: { gap: 'var(--s-2)' } }, b, dest) : null; })();
        tarjeta = h('section', { class: 'panel', 'aria-label': 'Tu siguiente llamada', 'data-lead': sig.id, style: { borderColor: 'var(--accent)' } },
          h('div', { class: 'cuerpo pila', style: { gap: 'var(--s-3)' } },
            h('div', { class: 'fila', style: { gap: 'var(--s-3)', flexWrap: 'nowrap', alignItems: 'flex-start' } },
              h('div', { class: 'fila', style: { gap: 'var(--s-3)', flexWrap: 'nowrap', minWidth: 0 } },
                h('span', { class: 'ico-c' }, icono(esCita ? 'cal' : 'phone')),
                h('div', { style: { minWidth: 0 } },
                  h('div', { class: 'titulo-seccion' }, esCita ? `Confirmar · ${sig.dia === 'hoy' ? 'hoy' : sig.dia === 'mañana' ? 'mañana' : sig.dia.replace(/^el /, '')} ${cuandoTexto(sig.cuando).split(' · ')[1]}` : `Tu siguiente llamada · quedan ${orden.length}`),
                  h('div', { style: { font: 'var(--t-h1)', letterSpacing: '-.01em', overflowWrap: 'anywhere' } }, nombreLead(sig)),
                  h('div', { class: 'sub' }, limpiaTexto(esCita ? `Cita de 45 min ${cuandoTexto(sig.cuando)}` : `${sig.motivo} · esperando ${duracionTexto(sig.min)}`))))),
            aTodoElAncho(contactoLead(ctx, { almacen: almacenDe(sig), x: sig })),
            botoneraResultado(ctx, { tipo, nombre: nombreLead(sig), grande: true, alGuardar: (r, n) => guardar(sig, tipo, r, n) }),
            h('div', { class: 'fila' }, verCompleto, abrirEn('GHL', sig.ghl),
              orden.length > 1 ? h('button', { type: 'button', class: 'bt mini', title: 'Pasar al siguiente sin apuntar (este vuelve al final)',
                on: { click: () => { saltados.push(sig.id); dibujar(); } } }, 'Siguiente sin apuntar', icono('derecha', { clase: 's' })) : null)));
      } else {
        tarjeta = vacio({ icono: 'ok', titulo: 'Nadie esperando una llamada', texto: apuntados.size ? `Lista al día: ${apuntados.size} apuntados hoy.` : 'Tienes la lista al día.', tono: 'celebrar', borde: true });
      }
    }

    if (resumen) {
      raiz.replaceChildren(pantallaTrabajo({ id: 'setters', filtros: franja, consejo: true,
        lista: panel({ titulo: 'Recuento por setter', icono: 'users', sub: 'Cuántos hay en cada lista, sin datos de los leads.' },
          h('div', { class: 'cuerpo' }, tablaApilable({ filas: (d.recuento || []).map(r => ({ ...r, setter: nombreSetter(ctx, r.quien), llamadas: hoyDe(r.quien).marcaciones })),
            columnas: [{ clave: 'setter', titulo: 'Setter', principal: true }, { clave: 'llamar_ya', titulo: 'Para llamar ya', num: true }, { clave: 'segundas', titulo: 'Segundas', num: true },
              { clave: 'citas', titulo: 'Por confirmar', num: true }, { clave: 'pasadas', titulo: 'Sin resultado', num: true },
              { clave: 'llamadas', titulo: 'Llamadas hoy', num: true, celda: r => r.llamadas ?? 'sin dato' }] }))),
        contexto: [pie(null, ctx, d, meta)] }));
      return;
    }

    // ---- pestañas: lo que hay que hacer ----
    const lista = (items, vacioO) => listaLoPrimero(items, { vacio: vacioO, subir: false });   // la tarjeta va primero: la lista no «sube»
    caja = pestanas({
      clave: 'setters.pestana', etiqueta: 'Listas del día',
      pestanas: [
        { id: 'llamar', texto: 'Llamar ya', icono: 'phone', cuenta: llamarYa.length, cuentaEstado: 'rojo' },
        { id: 'segundas', texto: 'Segundas', icono: 'clock', cuenta: segundas.length, cuentaEstado: 'rojo' },
        { id: 'citas', texto: 'Confirmar', icono: 'cal', cuenta: citas.filter(c => !c.confirmada_tel).length, cuentaEstado: 'rojo' },
        { id: 'pasadas', texto: 'Sin resultado', icono: 'check', cuenta: pasadas.length, cuentaEstado: 'rojo' },
      ],
      pintar: (id, zona) => {
        pestanaActual = id;
        if (id === 'llamar') {
          const items = llamarYa.map(l => itemLead(ctx, d, l, { tipo: 'lead', guardar, almacen: almacenDe(l), icono: l.sin_tel ? 'mail' : 'phone', estado: l.min < 60 ? 'ambar' : 'rojo',
            detalle: `${l.motivo} · esperando ${duracionTexto(l.min)}${l.sin_tel ? ' · no dejó teléfono' : ''}${l.aviso_tel && !l.sin_tel ? ' · teléfono raro: revísalo en GoHighLevel' : ''}${quien(l)}` }));
          zona.append(panel({ titulo: 'Para llamar ya', icono: 'phone', sub: 'Sin ningún intento todavía. Primero los que tienen teléfono; dentro, el más nuevo arriba.' },
            lista(items.slice(0, 7), { titulo: 'Nadie esperando una llamada', porque: 'Todos tienen al menos un intento o un resultado apuntado hoy.', celebrar: true }),
            items.length > 7 ? masLista(items.slice(7), items.length === 8 ? 'Ver el otro lead' : `Ver los otros ${items.length - 7} leads`) : null));
        } else if (id === 'segundas') {
          zona.append(panel({ titulo: 'Segundas llamadas', icono: 'clock', sub: 'Primer intento sin conversación: la segunda, en 48 horas como mucho.' },
            lista(segundas.map(l => {
              const quedan = l.segunda_vence ? Math.round((new Date(l.segunda_vence.replace(' ', 'T')) - Date.now()) / 36e5) : null;
              return itemLead(ctx, d, l, { tipo: 'lead', guardar, almacen: almacenDe(l), icono: 'clock', estado: quedan !== null && quedan < 0 ? 'rojo' : 'ambar',
                detalle: `${l.intentos} intento${l.intentos === 1 ? '' : 's'} · último ${cuandoTexto(l.ultima_llamada)} · ${quedan === null ? '' : quedan < 0 ? `vencida hace ${-quedan} h` : `vence en ${quedan} h`}${quien(l)}` });
            }), { titulo: 'Ninguna segunda llamada pendiente', porque: 'No hay leads con un intento sin conversación.', celebrar: true })));
        } else if (id === 'citas') {
          zona.append(panel({ titulo: 'Citas por confirmar', icono: 'cal', sub: 'Las de 45 min de hoy y del siguiente día laborable. Confirmar por teléfono o WhatsApp; nunca cambiar el estado de la cita en GoHighLevel.' },
            lista(citas.map(c => itemLead(ctx, d, c, { tipo: 'cita', guardar, almacen: almacenDe(c), icono: c.confirmada_tel ? 'ok' : 'cal', estado: c.confirmada_tel ? 'ambar' : 'rojo',
              detalle: [chipEstado(c.confirmada_tel ? 'verde' : 'rojo', c.confirmada_tel ? 'Hablado por teléfono' : 'Sin confirmar'), ` ${c.dia} · ${cuandoTexto(c.cuando)}${quien(c)}`] })),
            { titulo: 'Nada que confirmar hoy ni el siguiente día laborable', porque: 'Las citas de 45 min salen aquí 24-48 h antes.' })));
        } else {
          zona.append(panel({ titulo: 'Citas sin resultado', icono: 'check', sub: 'GoHighLevel casi nunca marca la cita: el resultado se apunta aquí el mismo día.' },
            lista(pasadas.map(c => itemLead(ctx, d, c, { tipo: 'pasada', guardar, almacen: almacenDe(c), icono: 'check', estado: 'rojo',
              detalle: `${cuandoTexto(c.cuando)} · tarjeta: ${c.etapa}${c.grabada_zadarma ? ' · hubo llamada contestada ese día' : ''}${quien(c)}` })),
            { titulo: 'Todas las citas tienen resultado', porque: 'Nada pendiente de apuntar.', celebrar: true })));
        }
      },
    });

    // ---- contexto (a un lado en el ordenador, debajo y plegado en el móvil): marcador, perdidas, informe y pie ----
    const comparar = ctx.ver({ tipo: 'comparar_personas' }).nivel === 'completo';
    const filasM = ['ana', 'javier'].filter(s => !yo || s === yo || comparar).map(s => ({
      setter: nombreSetter(ctx, s), hoy: hoyDe(s).marcaciones, conv: hoyDe(s).conversaciones, citas: hoyDe(s).citas_medibles ? hoyDe(s).citas : null, semana: semDe(s).marcaciones }));
    const sd = v => (v === null || v === undefined ? h('span', { class: 'sub' }, 'sin dato') : fmt.num(v));
    const marcador = panel({ titulo: 'Marcador', icono: 'grafico', sub: yo ? 'Tus llamadas y citas. El de los demás setters, solo citas celebradas cuando se midan.' : 'Llamadas por extensión de Zadarma y citas con la etiqueta de cada setter.' },
      h('div', { class: 'cuerpo' }, tablaApilable({ filas: filasM, columnas: [
        { clave: 'setter', titulo: 'Setter', principal: true }, { clave: 'hoy', titulo: 'Llamadas hoy', num: true, celda: r => sd(r.hoy) },
        { clave: 'conv', titulo: 'Pasan del minuto', num: true, celda: r => sd(r.conv) }, { clave: 'citas', titulo: 'Citas hoy', num: true, celda: r => sd(r.citas) },
        { clave: 'semana', titulo: 'Llamadas semana', num: true, celda: r => sd(r.semana) }] }),
      h('div', { class: 'fila', style: { marginTop: 'var(--s-3)' } }, frescura(fZD), frescura(fGHL), abrirEn('Zadarma', d.enlaces?.zadarma_estadisticas))));
    const perdidas = d.perdidas || [];
    const panelPerdidas = panel({ titulo: 'Llamadas perdidas o sin ficha', icono: 'phone', sub: yo ? 'Las que entraron por tu extensión en 48 h.' : 'Entrantes de 48 h sin contestar o de números sin ficha en GoHighLevel (sin clientes de la agencia).' },
      perdidas.length ? h('div', { class: 'cuerpo' }, tablaApilable({ filas: perdidas, columnas: [
        { clave: 'cuando', titulo: 'Cuándo', principal: true, celda: p => cuandoTexto(p.cuando) },
        { clave: 'tel_m', titulo: 'Número', celda: p => h('span', { style: { color: 'var(--mid)', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' } }, p.tel_m) },
        { clave: 'perdida', titulo: 'Qué pasó', celda: p => [p.perdida ? chipEstado('rojo', 'Sin contestar') : chipEstado('gris', `${p.seg} s`), ' ', p.sin_ficha ? chipEstado('ambar', 'Sin ficha') : null] },
        { clave: 'ghl', titulo: 'Atajo', celda: p => p.ghl ? abrirEn('GHL', p.ghl) : abrirEn('Zadarma', d.enlaces?.zadarma_estadisticas) },
      ] })) : h('div', { class: 'cuerpo' }, vacioLinea(yo ? 'Ninguna llamada perdida. Cuando tu extensión de Zadarma esté confirmada, aquí saldrán las que no cojas.' : 'Ninguna llamada perdida: nada sin contestar ni sin ficha en 48 h.', { icono: 'ok' })));
    const informe = (yo || ver) ? informeFinDeDia(ctx, { yo: ver, mh: hoyDe(ver), pasadas: pasadas.length, cola }) : null;
    if (informe) informe.id = 'setters-informe';

    // «Informe de fin de día» fijo abajo a partir de las 17:00 (antes, a 3.966 px en el móvil)
    const irInforme = informe && horaMadrid() >= 17 ? h('div', { style: { position: 'sticky', bottom: 'var(--s-3)', zIndex: '4', display: 'flex', justifyContent: 'center' } },
      h('button', { type: 'button', class: 'bt pri', style: { minHeight: 'var(--s-12)', boxShadow: 'var(--shadow-up)' }, on: { click: () => {
        const det = informe.closest('details'); if (det) det.open = true;
        informe.scrollIntoView({ behavior: 'smooth', block: 'start' });
        informe.querySelector('input, textarea')?.focus({ preventScroll: true });
      } } }, icono('doc'), 'Informe de fin de día')) : null;

    raiz.replaceChildren(pantallaTrabajo({
      id: 'setters', filtros: h('div', { class: 'pila', style: { gap: 'var(--s-2)' } }, chipsVer, franja),
      lista: h('div', { class: 'pila', style: { gap: 'var(--s-3)', minWidth: '0' } }, tarjeta, caja, irInforme),
      contexto: [informe, marcador, panelPerdidas, pie(null, ctx, d, meta)].filter(Boolean),
      tituloContexto: 'Informe del día, marcador y llamadas perdidas',
    }));
  }
  dibujar();
}

/** «Ver los otros N»: el resto de la lista, plegado. 3-oct: el relleno va en el botón, no en el plegable: así las filas
 *  desplegadas quedan alineadas con las de arriba (antes salían desplazadas a la derecha por el relleno del details). */
function masLista(items, texto) {
  const det = h('details', { class: 'mas-lista' }, h('summary', { class: 'bt', style: { listStyle: 'none', cursor: 'pointer', display: 'inline-flex', minHeight: 'var(--s-10)', margin: '0 var(--relleno) var(--s-4)' } }, icono('mas'), texto));
  det.addEventListener('toggle', () => {
    if (det.open && det.childNodes.length === 1) { const l = listaLoPrimero(items, { subir: false }); l.style.borderTop = '1px solid var(--line-soft)'; det.append(l); }
  });
  return det;
}

function informeFinDeDia(ctx, { yo, mh, pasadas, cola }) {
  const mios = cola.filter(a => a.que === 'informe_fin_de_dia').slice(-3).reverse();
  const n = v => (v === null || v === undefined ? '' : String(v));
  const f = {
    marc: campo({ etiqueta: 'Llamadas hechas', nombre: 'marc', tipo: 'number', valor: n(mh.marcaciones), min: 0 }),
    conv: campo({ etiqueta: 'Pasan del minuto', nombre: 'conv', tipo: 'number', valor: n(mh.conversaciones), min: 0 }),
    citas: campo({ etiqueta: 'Citas agendadas', nombre: 'citas', tipo: 'number', valor: n(mh.citas_medibles ? mh.citas : ''), min: 0 }),
    conf: campo({ etiqueta: 'Citas confirmadas', nombre: 'conf', tipo: 'number', valor: '', min: 0 }),
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
      // Ronda U (#4): el informe se queda en la app (no sale fuera): sin «¿Seguro?», con «Deshacer» 8 s.
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

function pie(cont, ctx, d, meta) {
  const avisos = [...(d.avisos || [])];
  if ((d.leads || []).some(l => l.reparto === 'simulado')) avisos.unshift('El reparto entre los dos setters es todavía una simulación: cuando cada lead lleve su etiqueta en GoHighLevel, manda la etiqueta.');
  const el = (h('details', { class: 'panel' },
    h('summary', { class: 'cuerpo fila', style: { cursor: 'pointer', minHeight: 'var(--s-12)', font: 'var(--t-h2)', color: 'var(--mid)' } },
      icono('info'), 'Lo que falta para que funcione del todo'),
    h('ul', { class: 'cuerpo', style: { margin: 0, paddingTop: 0, paddingLeft: 'var(--s-10)', display: 'grid', gap: 'var(--s-1)', maxWidth: '72ch' } },
      avisos.map(a => h('li', {}, limpiaTexto(a))),
      h('li', {}, 'Llamar y WhatsApp abren la app del móvil y el intento queda apuntado. Agendar, escribir desde GoHighLevel o mover la tarjeta esperan el permiso de escritura en GoHighLevel.'),
      h('li', {}, 'Todavía no se mide: citas celebradas por setter, minutos exactos hasta el primer intento y la nota de calidad de cada llamada.')),
    h('div', { class: 'fila', style: { padding: '0 var(--relleno) var(--s-4)' } }, frescura(fresco(meta, 'GoHighLevel (subcuenta RO)', 'GoHighLevel')), frescura(fresco(meta, 'Zadarma')),
      abrirEn('GHL · calendario', d.enlaces?.ghl_calendario), abrirEn('GHL · conversaciones', d.enlaces?.ghl_conversaciones))));
  if (cont) cont.append(el);
  return el;
}

export default {
  id: 'setters',
  titulo: 'Mi día del setter',
  grupo: 'Ventas de RO',
  puestos_que_lo_ven: { setters: 'suyo', direccion: 'todo', ventas_ro: 'todo', jefa_crm: 'resumen', operaciones: 'resumen' },
  async render(contenedor, ctx) { await pintar(contenedor, ctx, undefined); },
};
