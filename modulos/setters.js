// modulos/setters.js · «Mi día del setter» (E6). Móvil a 390 px primero y con una mano.
// Orden: tu siguiente llamada → cifras del día → pestañas (Llamar ya · Segundas · Citas · Sin resultado) →
// marcador → llamadas perdidas → informe de fin de día. Solo la subcuenta de RO: nada de clientes de la agencia.
// El setter recibe el nombre de sus leads (servidor, D-88); teléfono y correo, en el clic de Llamar/WhatsApp/correo.

import { h, fmt, semaforo, tile, vacioLinea, listaLoPrimero, tablaApilable, chipEstado, chipsFiltro, pestanas, vacio,
  botonConfirmar, avisoParcial, panel, frescura, icono, limpiaTexto, hoyMadrid, sumarDias } from '../componentes.js';
import { cargar, setterDe, nombreSetter, fresco, duracionTexto, cuandoTexto, minutosDesde, nombreLead, encolar, leerCola,
  vistaPrevia, abrirEn, masAcciones, contactoLead, verDatos, chipGrupo, campo } from './_ventas_comun.js';

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
  if (el && el.classList?.contains('fila')) Object.assign(el.style, { display: 'grid', gap: 'var(--s-2)', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 180px), 1fr))' });
  el?.querySelectorAll?.('button, a').forEach(b => { b.style.minHeight = 'var(--s-12)'; b.style.justifyContent = 'center'; });
  return el;
}
const fechaHora = t => (t ? new Date(t).toLocaleString('es-ES', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }).replace('.', '') : '');

// ----------------------------------------------------------------- apuntar resultado
function apuntarResultado(ctx, { id, nombre, tipo }) {
  const opciones = tipo === 'cita'
    ? ['Confirmada por teléfono', 'Confirmada por WhatsApp', 'No contesta: vuelvo a llamar', 'Quiere cambiar la hora', 'Cancela']
    : tipo === 'pasada'
      ? ['Se celebró', 'No se presentó', 'Se reprogramó', 'No lo sé: pregunto a Tomás']
      : ['No contesta', 'Hablado: reserva por la web', 'Hablado: volver a llamar', 'Hablado: no encaja', 'Número erróneo'];
  let elegido = opciones[0];
  const previa = h('div');
  const pintarPrevia = () => {
    const extra = tipo === 'pasada'
      ? (elegido === 'No se presentó' ? ' y movería la tarjeta a «No se presentó» (sin tocar el estado de la cita, que manda WhatsApp)' : elegido === 'Se celebró' ? ' y dejaría a Tomás la tarea de mover la tarjeta' : '')
      : elegido.startsWith('Hablado: reserva') ? '. La reunión la reserva el titular en la web de RO, nunca a mano en GHL' : '';
    previa.replaceChildren(vistaPrevia(`queda «${elegido}» en tu día; cuando haya permiso de escritura, dejará una nota en la ficha de ${nombre} en GHL${extra}.`));
  };
  const chips = chipsFiltro({ etiqueta: 'Resultado', opciones: opciones.map(o => ({ valor: o, texto: o })), valor: elegido, alCambiar: v => { elegido = v; pintarPrevia(); } });
  const nota = campo({ etiqueta: 'Nota', nombre: 'nota', tipo: 'textarea', filas: 2, ayuda: 'Lo que pasaría a la ficha de GHL.' });
  pintarPrevia();
  return h('div', { class: 'pila', style: { gap: 'var(--s-2)', marginTop: 'var(--s-2)' } }, chips, nota, previa, botonConfirmar({
    texto: 'Guardar resultado', pregunta: '¿Lo guardas?', confirmar: 'Sí, guardar', soloLectura: ctx.soloLectura,
    alConfirmar: async () => {
      const n = nota.querySelector('textarea').value.trim();
      await encolar(ctx, { que: tipo === 'pasada' ? 'resultado_cita' : tipo === 'cita' ? 'confirmacion_cita' : 'resultado_llamada', sobre: id,
        texto: `${elegido}${n ? ' · ' + n : ''}`, herramienta: 'ghl', vista: 'Nota en la ficha de GHL' });
      return 'Guardado · queda en el rastro';
    },
  }));
}

/** Un lead como elemento de «Lo primero»: contacto en un clic, apuntar y «Más» (ficha, datos, oportunidad). */
function itemLead(ctx, d, x, { tipo, almacen, estado, icono: ico, detalle }) {
  const destino = h('span', {}, nombreLead(x));
  const hueco = h('div', { hidden: true, style: { gridColumn: '1 / -1' } });
  const apuntar = h('button', { type: 'button', class: 'bt', 'aria-expanded': 'false', style: { minHeight: '44px' },
    'aria-disabled': ctx.soloLectura ? 'true' : null, title: ctx.soloLectura ? 'Estás en «ver como»: solo lectura' : null },
  icono('editar'), tipo === 'cita' ? 'Apuntar' : 'Resultado');
  apuntar.addEventListener('click', () => {
    if (ctx.soloLectura) return;
    const abrir = hueco.hidden; hueco.hidden = !abrir; apuntar.setAttribute('aria-expanded', String(abrir));
    if (abrir && !hueco.childNodes.length) hueco.append(apuntarResultado(ctx, { id: x.id, nombre: x.nombre_m, tipo }));
  });
  return {
    estado, icono: ico, motivo: h('span', { class: 'fila', style: { gap: 'var(--s-2)' } }, destino, tipo === 'lead' ? chipGrupo(x.grupo) : null),
    detalle: [detalle, hueco],
    botones: [
      tipo !== 'pasada' ? contactoLead(ctx, { almacen, x }) : null,
      apuntar,
      masAcciones(
        abrirEn('GHL', x.ghl),
        abrirEn('GHL · oportunidades', d.enlaces?.ghl_oportunidades),
        abrirEn('Zadarma', d.enlaces?.zadarma_estadisticas),
        verDatos(ctx, { almacen, id: x.id, destino }),
      ),
    ],
  };
}

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
  if (!yo && !resumen) {
    cont.append(chipsFiltro({ etiqueta: 'Ver', clave: 'setters.vista', valor: vista || '',
      opciones: [{ valor: '', texto: 'Los dos', icono: 'users' }, ...['ana', 'javier'].map(s => ({ valor: s, texto: nombreSetter(ctx, s), icono: 'persona',
        cuenta: (d.leads || []).filter(l => l.setter === s && l.lista === 'llamar_ya').length, cuentaEstado: 'rojo' }))],
      alCambiar: v => { cont.replaceChildren(); pintar(cont, ctx, v || null); } }));
    if (vista === undefined) { const recordado = cont.lastChild.valor?.(); if (recordado) { cont.replaceChildren(); return pintar(cont, ctx, recordado); } }
  }

  const leads = (d.leads || []).filter(mio).map(l => ({ ...l, min: minutosDesde(l.entro) }));
  const llamarYa = leads.filter(l => l.lista === 'llamar_ya').sort((a, b) => (!!a.sin_tel - !!b.sin_tel) || a.min - b.min);
  const segundas = leads.filter(l => l.lista === 'segunda').sort((a, b) => (a.segunda_vence || '').localeCompare(b.segunda_vence || ''));
  const citas = (d.citas || []).filter(mio).map(c => ({ ...c, dia: diaRel(c.cuando) || c.dia }));
  const pasadas = (d.pasadas || []).filter(mio);
  const hoyDe = s => (d.marcador || []).find(m => m.setter === s && m.periodo === 'hoy') || {};
  const semDe = s => (d.marcador || []).find(m => m.setter === s && m.periodo === 'semana') || {};

  // ---- 0 · tu siguiente llamada ----
  const verCompleto = x => { const dest = h('span'); const b = verDatos(ctx, { almacen: almacenDe(x), id: x.id, destino: dest }); if (b) b.lastChild && (b.lastChild.textContent = 'Ver completo'); return b ? h('span', { class: 'fila', style: { gap: 'var(--s-2)' } }, b, dest) : null; };
  if (yo) {
    // V2 (C-11): la siguiente llamada es la MÁS URGENTE con la regla de la guía (el lead nuevo, primer intento en < 5 min):
    // una confirmación solo pasa delante si la reunión es hoy; la del lunes espera a que no quede nadie en «Llamar ya».
    const sinConf = citas.filter(c => !c.confirmada_tel && !c.sin_tel);
    const sig = sinConf.find(c => c.dia === 'hoy') || llamarYa.find(l => !l.sin_tel) || sinConf[0] || segundas[0];
    if (sig) {
      const esCita = !!sig.cita_id;
      cont.append(h('section', { class: 'panel', 'aria-label': 'Tu siguiente llamada', style: { borderColor: 'var(--accent)' } },
        h('div', { class: 'cuerpo pila', style: { gap: 'var(--s-3)' } },
          h('div', { class: 'fila', style: { gap: 'var(--s-3)', flexWrap: 'nowrap' } },
            h('span', { class: 'ico-c' }, icono(esCita ? 'cal' : 'phone')),
            h('div', { style: { minWidth: 0 } },
              h('div', { class: 'titulo-seccion' }, esCita ? `Confirmar · ${sig.dia === 'hoy' ? 'hoy' : sig.dia === 'mañana' ? 'mañana' : sig.dia.replace(/^el /, '')} ${cuandoTexto(sig.cuando).split(' · ')[1]}` : 'Tu siguiente llamada'),
              h('div', { style: { font: 'var(--t-h1)', letterSpacing: '-.01em', overflowWrap: 'anywhere' } }, nombreLead(sig)),
              h('div', { class: 'sub' }, limpiaTexto(esCita ? `Reunión de 45 min ${cuandoTexto(sig.cuando)}` : `${sig.motivo} · esperando ${duracionTexto(sig.min)}`)))),
          aTodoElAncho(contactoLead(ctx, { almacen: almacenDe(sig), x: sig })),
          // V2 (C-32): «Ver completo» (lo promete la guía 14): nombre, despacho, teléfono y correo, por ver_dato y con rastro
          h('div', { class: 'fila' }, verCompleto(sig), abrirEn('GHL', sig.ghl),
            // V2 (C-11): en el móvil «Llamar ya» quedaba a 1.175 px: un botón lleva a la lista sin desplazarse
            llamarYa.length ? h('button', { type: 'button', class: 'bt mini', on: { click: () => { caja?.elegir?.('llamar'); caja?.scrollIntoView({ behavior: 'smooth', block: 'start' }); } } }, icono('phone'), `Ver los ${llamarYa.length} de «Llamar ya»`) : null))));
    } else {
      cont.append(vacio({ icono: 'ok', titulo: 'Nadie esperando una llamada', texto: 'Tienes la lista al día.', tono: 'celebrar', borde: true }));
    }
  }

  // ---- cifras del día ----
  let caja = null;
  const quienes = ver ? [ver] : ['ana', 'javier'];
  const sumar = (k, f = hoyDe) => (quienes.some(s => f(s)[k] === null || f(s)[k] === undefined) ? null : quienes.reduce((t, s) => t + f(s)[k], 0));
  const marc = sumar('marcaciones'), conv = sumar('conversaciones');
  const pct = marc ? Math.round(100 * conv / marc) : null;
  const citasMedibles = quienes.every(s => hoyDe(s).citas_medibles);
  const citasHoy = citasMedibles ? sumar('citas') : null;
  cont.append(rejilla2a3([
    tile({ icono: 'phone', etiqueta: 'Para llamar ya', valor: llamarYa.length, estado: llamarYa.length ? relojLead(llamarYa[0]?.min) : 'verde',
      contexto: llamarYa.length ? `El primero lleva ${duracionTexto(llamarYa[0].min)} esperando` : 'Nadie esperando', medible: 'medias',
      medibleDetalle: 'Intento = llamada de Zadarma a su número desde que entró en la lista', frescura: fGHL, alPulsar: () => caja.elegir?.('llamar') }),
    tile({ icono: 'cal', etiqueta: 'Reuniones por confirmar', valor: citas.length, estado: citas.some(c => !c.confirmada_tel) ? 'ambar' : (citas.length ? 'verde' : ''),
      contexto: 'Hoy y el siguiente día laborable', frescura: fGHL, alPulsar: () => caja.elegir?.('citas') }),
    tile({ icono: 'check', etiqueta: 'Reuniones sin resultado', valor: pasadas.length, estado: pasadas.length ? 'rojo' : 'verde',
      contexto: 'Se apuntan el mismo día', frescura: fGHL, alPulsar: () => caja.elegir?.('pasadas') }),
    tileSD({ icono: 'chat', etiqueta: 'Conversaciones hoy', valor: pct === null ? null : `${pct} %`, unidad: marc ? `${conv} de ${marc} llamadas` : '',
      estado: pct === null ? '' : semaforo(pct, { verde: 17, ambar: 10 }), contexto: marc === null ? 'Sin dato: falta confirmar la extensión de Zadarma' : 'Bien: 17 % o más pasan del minuto',
      medible: 'medias', frescura: fZD }),
    tileSD({ icono: 'cal', etiqueta: 'Reuniones conseguidas hoy', valor: citasHoy, estado: citasHoy === null ? '' : semaforo(citasHoy, { verde: 2, ambar: 1 }),
      contexto: citasHoy === null ? 'Sin dato hasta que cada lead lleve la etiqueta de su setter' : 'Bien: 2 o más al día', medible: 'medias', frescura: fGHL }),
    tileSD({ icono: 'target', etiqueta: 'Reuniones celebradas', valor: null, sinDato: 'Se mide desde el lunes 5', contexto: 'Las de este mes', medible: 'no' }),
  ]));

  if (resumen) {
    cont.append(panel({ titulo: 'Recuento por setter', icono: 'users', sub: 'Cuántos hay en cada lista, sin datos de los leads.' },
      h('div', { class: 'cuerpo' }, tablaApilable({ filas: (d.recuento || []).map(r => ({ ...r, setter: nombreSetter(ctx, r.quien), llamadas: hoyDe(r.quien).marcaciones })),
        columnas: [{ clave: 'setter', titulo: 'Setter', principal: true }, { clave: 'llamar_ya', titulo: 'Para llamar ya', num: true }, { clave: 'segundas', titulo: 'Segundas', num: true },
          { clave: 'citas', titulo: 'Por confirmar', num: true }, { clave: 'pasadas', titulo: 'Sin resultado', num: true },
          { clave: 'llamadas', titulo: 'Llamadas hoy', num: true, celda: r => r.llamadas ?? 'sin dato' }] }))));
    pie(cont, ctx, d, meta);
    return;
  }

  // ---- pestañas: lo que hay que hacer ----
  const quien = l => (!ver ? ` · ${nombreSetter(ctx, l.setter)}` : '');
  const lista = (items, vacioO) => listaLoPrimero(items, { vacio: vacioO });
  caja = pestanas({
    clave: 'setters.pestana', etiqueta: 'Listas del día',
    pestanas: [
      { id: 'llamar', texto: 'Llamar ya', icono: 'phone', cuenta: llamarYa.length, cuentaEstado: 'rojo' },
      { id: 'segundas', texto: 'Segundas', icono: 'clock', cuenta: segundas.length, cuentaEstado: 'rojo' },
      { id: 'citas', texto: 'Confirmar', icono: 'cal', cuenta: citas.filter(c => !c.confirmada_tel).length, cuentaEstado: 'rojo' },
      { id: 'pasadas', texto: 'Sin resultado', icono: 'check', cuenta: pasadas.length, cuentaEstado: 'rojo' },
    ],
    pintar: (id, zona) => {
      if (id === 'llamar') {
        const items = llamarYa.map(l => itemLead(ctx, d, l, { tipo: 'lead', almacen: almacenDe(l), icono: l.sin_tel ? 'mail' : 'phone', estado: l.min < 60 ? 'ambar' : 'rojo',
          detalle: `${l.motivo} · esperando ${duracionTexto(l.min)}${l.sin_tel ? ' · no dejó teléfono' : ''}${l.aviso_tel && !l.sin_tel ? ' · teléfono raro: revísalo en GHL' : ''}${quien(l)}` }));
        zona.append(panel({ titulo: 'Para llamar ya', icono: 'phone', sub: 'Sin ningún intento todavía. Primero los que tienen teléfono; dentro, el más nuevo arriba.' },
          lista(items.slice(0, 7), { titulo: 'Nadie esperando una llamada', porque: 'Todos tienen al menos un intento.', celebrar: true }),
          items.length > 7 ? masLista(items.slice(7), `Ver los otros ${items.length - 7}`) : null));
      } else if (id === 'segundas') {
        zona.append(panel({ titulo: 'Segundas llamadas', icono: 'clock', sub: 'Primer intento sin conversación: la segunda, en 48 horas como mucho.' },
          lista(segundas.map(l => {
            const quedan = l.segunda_vence ? Math.round((new Date(l.segunda_vence.replace(' ', 'T')) - Date.now()) / 36e5) : null;
            return itemLead(ctx, d, l, { tipo: 'lead', almacen: almacenDe(l), icono: 'clock', estado: quedan !== null && quedan < 0 ? 'rojo' : 'ambar',
              detalle: `${l.intentos} intento${l.intentos === 1 ? '' : 's'} · último ${cuandoTexto(l.ultima_llamada)} · ${quedan === null ? '' : quedan < 0 ? `vencida hace ${-quedan} h` : `vence en ${quedan} h`}${quien(l)}` });
          }), { titulo: 'Ninguna segunda llamada pendiente', porque: 'No hay leads con un intento sin conversación.', celebrar: true })));
      } else if (id === 'citas') {
        zona.append(panel({ titulo: 'Reuniones por confirmar', icono: 'cal', sub: 'Las de 45 min de hoy y del siguiente día laborable. Confirmar por teléfono o WhatsApp; nunca cambiar el estado de la cita en GHL.' },
          lista(citas.map(c => itemLead(ctx, d, c, { tipo: 'cita', almacen: almacenDe(c), icono: c.confirmada_tel ? 'ok' : 'cal', estado: c.confirmada_tel ? 'ambar' : 'rojo',
            detalle: [chipEstado(c.confirmada_tel ? 'verde' : 'rojo', c.confirmada_tel ? 'Hablado por teléfono' : 'Sin confirmar'), ` ${c.dia} · ${cuandoTexto(c.cuando)}${quien(c)}`] })),
          { titulo: 'Nada que confirmar hoy ni el siguiente día laborable', porque: 'Las reuniones de 45 min salen aquí 24-48 h antes.' })));
      } else {
        zona.append(panel({ titulo: 'Reuniones sin resultado', icono: 'check', sub: 'GHL casi nunca marca la cita: el resultado se apunta aquí el mismo día.' },
          lista(pasadas.map(c => itemLead(ctx, d, c, { tipo: 'pasada', almacen: almacenDe(c), icono: 'check', estado: 'rojo',
            detalle: `${cuandoTexto(c.cuando)} · tarjeta: ${c.etapa}${c.grabada_zadarma ? ' · hubo llamada contestada ese día' : ''}${quien(c)}` })),
          { titulo: 'Todas las reuniones tienen resultado', porque: 'Nada pendiente de apuntar.', celebrar: true })));
      }
    },
  });
  cont.append(caja);

  // ---- marcador (setters ven el suyo; Tomás compara) ----
  const comparar = ctx.ver({ tipo: 'comparar_personas' }).nivel === 'completo';
  const filasM = ['ana', 'javier'].filter(s => !yo || s === yo || comparar).map(s => ({
    setter: nombreSetter(ctx, s), hoy: hoyDe(s).marcaciones, conv: hoyDe(s).conversaciones, citas: hoyDe(s).citas_medibles ? hoyDe(s).citas : null, semana: semDe(s).marcaciones }));
  const sd = v => (v === null || v === undefined ? h('span', { class: 'sub' }, 'sin dato') : fmt.num(v));
  cont.append(panel({ titulo: 'Marcador', icono: 'grafico', sub: yo ? 'Tus llamadas y reuniones. El de los demás setters, solo reuniones celebradas cuando se midan.' : 'Llamadas por extensión de Zadarma y reuniones con la etiqueta de cada setter.' },
    h('div', { class: 'cuerpo' }, tablaApilable({ filas: filasM, columnas: [
      { clave: 'setter', titulo: 'Setter', principal: true }, { clave: 'hoy', titulo: 'Llamadas hoy', num: true, celda: r => sd(r.hoy) },
      { clave: 'conv', titulo: 'Pasan del minuto', num: true, celda: r => sd(r.conv) }, { clave: 'citas', titulo: 'Reuniones hoy', num: true, celda: r => sd(r.citas) },
      { clave: 'semana', titulo: 'Llamadas semana', num: true, celda: r => sd(r.semana) }] }),
    h('div', { class: 'fila', style: { marginTop: 'var(--s-3)' } }, frescura(fZD), frescura(fGHL), abrirEn('Zadarma', d.enlaces?.zadarma_estadisticas)))));

  // ---- llamadas perdidas o sin ficha ----
  const perdidas = d.perdidas || [];
  cont.append(panel({ titulo: 'Llamadas perdidas o sin ficha', icono: 'phone', sub: yo ? 'Las que entraron por tu extensión en 48 h.' : 'Entrantes de 48 h sin contestar o de números sin ficha en GHL (sin clientes de la agencia).' },
    perdidas.length ? h('div', { class: 'cuerpo' }, tablaApilable({ filas: perdidas, columnas: [
      { clave: 'cuando', titulo: 'Cuándo', principal: true, celda: p => cuandoTexto(p.cuando) },
      { clave: 'tel_m', titulo: 'Número', celda: p => h('span', { style: { color: 'var(--mid)', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' } }, p.tel_m) },
      { clave: 'perdida', titulo: 'Qué pasó', celda: p => [p.perdida ? chipEstado('rojo', 'Sin contestar') : chipEstado('gris', `${p.seg} s`), ' ', p.sin_ficha ? chipEstado('ambar', 'Sin ficha') : null] },
      { clave: 'ghl', titulo: 'Atajo', celda: p => p.ghl ? abrirEn('GHL', p.ghl) : abrirEn('Zadarma', d.enlaces?.zadarma_estadisticas) },
    ] })) : h('div', { class: 'cuerpo' }, vacioLinea(yo ? 'Ninguna llamada perdida. Cuando tu extensión de Zadarma esté confirmada, aquí saldrán las que no cojas.' : 'Ninguna llamada perdida: nada sin contestar ni sin ficha en 48 h.', { icono: 'ok' }))));

  // ---- informe de fin de día ----
  if (yo || ver) cont.append(informeFinDeDia(ctx, { yo: ver, mh: hoyDe(ver), pasadas: pasadas.length, cola }));
  pie(cont, ctx, d, meta);
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
    citas: campo({ etiqueta: 'Reuniones conseguidas', nombre: 'citas', tipo: 'number', valor: n(mh.citas_medibles ? mh.citas : ''), min: 0 }),
    conf: campo({ etiqueta: 'Reuniones confirmadas', nombre: 'conf', tipo: 'number', valor: '', min: 0 }),
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
      pasadas ? avisoParcial(`Te quedan ${pasadas} reunión${pasadas === 1 ? '' : 'es'} sin resultado: apúntalas antes de cerrar el día.`, { titulo: 'Antes de enviar.' }) : null,
      vistaPrevia('el informe queda guardado con tu nombre y la hora; lo ven Tomás y quien dirija a los setters.'),
      botonConfirmar({ texto: 'Enviar informe de hoy', pregunta: '¿Lo envías?', confirmar: 'Sí, enviar', soloLectura: ctx.soloLectura,
        alConfirmar: async () => {
          const nt = notaDia;
          if (!nt) throw new Error('falta la nota del día');
          await encolar(ctx, { que: 'informe_fin_de_dia', sobre: yo || ctx.persona.id, herramienta: 'app',
            texto: `llamadas ${val('marc') || '—'} · pasan del minuto ${val('conv') || '—'} · reuniones ${val('citas') || '—'} · confirmadas ${val('conf') || '—'} · nota ${nt}${val('dudas') ? ' · dudas: ' + val('dudas') : ''}` });
          return 'Informe guardado · queda en el rastro';
        } }),
      mios.length ? h('div', {}, h('p', { class: 'titulo-seccion' }, icono('hist'), 'Tus últimos informes'),
        h('ul', { class: 'lista-i', style: { marginTop: 'var(--s-1)' } }, mios.map(a => h('li', {}, h('span', { class: 'ico-c s gris' }, icono('doc')), h('span', { class: 't', style: { whiteSpace: 'normal' } }, h('b', {}, fechaHora(a.hora)), ` · ${a.texto}`))))) : null));
}

function pie(cont, ctx, d, meta) {
  const avisos = [...(d.avisos || [])];
  if ((d.leads || []).some(l => l.reparto === 'simulado')) avisos.unshift('El reparto entre los dos setters es todavía una simulación: cuando cada lead lleve su etiqueta en GHL, manda la etiqueta.');
  cont.append(h('details', { class: 'panel' },
    h('summary', { class: 'cuerpo fila', style: { cursor: 'pointer', minHeight: 'var(--s-12)', font: 'var(--t-h2)', color: 'var(--mid)' } },
      icono('info'), 'Lo que falta para que funcione del todo'),
    h('ul', { class: 'cuerpo', style: { margin: 0, paddingTop: 0, paddingLeft: 'var(--s-10)', display: 'grid', gap: 'var(--s-1)', maxWidth: '72ch' } },
      avisos.map(a => h('li', {}, limpiaTexto(a))),
      h('li', {}, 'Llamar y WhatsApp abren la app del móvil y el intento queda apuntado. Agendar, escribir desde GHL o mover la tarjeta esperan el permiso de escritura en GHL.'),
      h('li', {}, 'Todavía no se mide: reuniones celebradas por setter, minutos exactos hasta el primer intento y la nota de calidad de cada llamada.')),
    h('div', { class: 'fila', style: { padding: '0 var(--relleno) var(--s-4)' } }, frescura(fresco(meta, 'GoHighLevel (subcuenta RO)', 'GoHighLevel')), frescura(fresco(meta, 'Zadarma')),
      abrirEn('GHL · calendario', d.enlaces?.ghl_calendario), abrirEn('GHL · conversaciones', d.enlaces?.ghl_conversaciones))));
}

export default {
  id: 'setters',
  titulo: 'Mi día del setter',
  grupo: 'Ventas de RO',
  puestos_que_lo_ven: { setters: 'suyo', direccion: 'todo', ventas_ro: 'todo', jefa_crm: 'resumen', operaciones: 'resumen' },
  async render(contenedor, ctx) { await pintar(contenedor, ctx, undefined); },
};
