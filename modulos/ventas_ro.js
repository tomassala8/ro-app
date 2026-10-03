// modulos/ventas_ro.js · M16 «Ventas de RO» (E6): el embudo de venta de RO sin abrir GHL.
// Arriba lo de cada día (cifras y «Hoy»: reuniones, propuestas paradas y contratos sin firmar); en pestañas lo de la
// semana y el mes (embudo con ritmo, agenda de 45 min, bajas tempranas). El embudo replica calc() del panel de
// resultados (por fecha del hecho, todas las capas): septiembre cuadra exacto. En «resumen»: recuentos sin euros ni nombres.

import { h, fmt, semaforo, tile, tiles, listaLoPrimero, tablaApilable, chipEstado, pestanas, vacio, botonConfirmar,
  avisoParcial, panel, frescura, icono, embudoBarras, barraProgreso, limpiaTexto, colorCifra, variacion, hoyMadrid } from '../componentes.js';
import { pintarAnunciosYPrevision } from './dinero_m16_anuncios.js';
import { cargar, fresco, cuandoTexto, nombreLead, abrirEn, masAcciones, verDatos, encolar } from './_ventas_comun.js';

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

const pct = (a, b) => (b ? (100 * a) / b : null);
const MES = { '01': 'enero', '02': 'febrero', '03': 'marzo', '04': 'abril', '05': 'mayo', '06': 'junio', '07': 'julio', '08': 'agosto', '09': 'septiembre', '10': 'octubre', '11': 'noviembre', '12': 'diciembre' };

/** Días laborables (lunes a viernes) ya cerrados este mes, sin contar hoy. */
function laborablesCerrados(hoy) {
  let n = 0;
  for (let d = 1; d < hoy.getDate(); d++) { const x = new Date(hoy.getFullYear(), hoy.getMonth(), d).getDay(); if (x !== 0 && x !== 6) n++; }
  return n;
}
function laborablesDelMes(hoy) {
  let n = 0; const fin = new Date(hoy.getFullYear(), hoy.getMonth() + 1, 0).getDate();
  for (let d = 1; d <= fin; d++) { const x = new Date(hoy.getFullYear(), hoy.getMonth(), d).getDay(); if (x !== 0 && x !== 6) n++; }
  return n;
}

// R12 (A-A2): el generador deja una serie DIARIA (v.dias) con las mismas reglas que el panel (todo por fecha del hecho), así que
// cualquier periodo es una suma de días: septiembre entero = la columna del panel, exacto.
const CLAVES = ['inversion', 'contactos', 'piden_reunion', 'citas', 'celebradas', 'ausencias', 'sin_marcar', 'propuestas', 'acuerdos', 'firmados', 'cobrados', 'cuota_firmada'];
function sumaDias(dias, r) {
  if (!dias || !r) return null;
  const t = Object.fromEntries(CLAVES.map(k => [k, 0]));
  let n = 0;
  for (const [d, x] of Object.entries(dias)) { if (d < r.desde || d > r.hasta) continue; n++; for (const k of CLAVES) t[k] += x[k] || 0; }
  t.inversion = Math.round(t.inversion * 100) / 100;
  return n ? t : null;
}
const _M3V = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const _DSV = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'];
const fechaCorta = d => { const x = new Date(d + 'T12:00'); return `${x.getDate()}-${_M3V[x.getMonth()]}`; };   // §2.3: «2-oct»
const diaSemanaV = d => { const x = new Date(d + 'T12:00'); return `${_DSV[x.getDay()]} ${x.getDate()}-${_M3V[x.getMonth()]}`; };   // «vie 2-oct»

async function pintar(cont, ctx) {
  const [v, meta] = await Promise.all([cargar(ctx, 'ventas_ro'), cargar(ctx, 'meta')]);
  if (!v || !v.meses) {
    cont.append(vacio({ icono: 'megafono', titulo: 'Todavía no hay datos de ventas de RO', texto: 'Falta generar los datos de hoy.', quien: 'Agus', tono: 'aviso' }));
    return;
  }
  const todo = ctx.nivel === 'todo';
  const fPanel = fresco(meta, 'Panel v29 · GoHighLevel', 'Panel de resultados'), fMeta = fresco(meta, 'Panel v29 · Meta', 'Meta');
  const fGHL = fresco(meta, 'GoHighLevel (subcuenta RO)', 'GoHighLevel');
  const hoy = new Date();
  const ym = `${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, '0')}`;
  const nombreMes = MES[ym.slice(5)] || ym;
  const mesNatural = v.meses[ym] || v.meses['2026-10'];
  // periodo de la barra: suma de días; sin serie diaria (datos viejos), el mes en curso y septiembre como antes
  const p = ctx.periodo;
  const esMes = !p || p.id === 'mes';
  const mes = (p && v.dias && sumaDias(v.dias, p)) || mesNatural;
  const comp = p?.comp && v.dias ? sumaDias(v.dias, p.comp) : null;
  const sep = v.meses['2026-09'];
  const nombreP = p ? (p.id === 'mes' ? nombreMes : (p.rango || p.nombre)) : nombreMes;
  // V2: el periodo ya está en el selector de arriba: la etiqueta de la tarjeta no lo repite (a 768 partía «3-sep a 2-\noct»).
  // Solo con el mes natural se deja el nombre del mes, que es corto y no se parte.
  const etiP = t => (p && p.id !== 'mes' ? t : `${t} · ${nombreMes}`);
  const antesDeDatos = p && v.datos_desde && p.desde < v.datos_desde;
  const cmp = (a, b, o = {}) => (comp && b !== null && b !== undefined && a !== null && a !== undefined ? { delta: variacion(a, b), pct: true, mejorSi: o.mejorSi || 'alto', texto: p.comp.texto || 'frente al periodo anterior' } : undefined);
  const cerrados = laborablesCerrados(hoy), laborables = laborablesDelMes(hoy);
  const conRitmo = cerrados >= 5;
  const ritmo = conRitmo && esMes ? (mes.firmados / cerrados) * laborables : null;
  const ritmoPct = ritmo === null ? null : pct(ritmo, v.objetivo_firmados_mes);

  ctx.titulo('Ventas de RO', todo ? 'Reuniones, propuestas, contratos y ritmo del mes' : 'El embudo de venta de RO, en recuentos');

  // ---- cifras (del periodo de la barra) ----
  const pc = (a, b) => (b ? pct(a, b) : null);
  const asis = pc(mes.celebradas, mes.celebradas + mes.ausencias), asisC = comp ? pc(comp.celebradas, comp.celebradas + comp.ausencias) : null;
  const lista = [
    tile({ icono: 'flag', etiqueta: etiP('Firmados'), valor: mes.firmados, unidad: esMes ? `de ${v.objetivo_firmados_mes}` : `${fmt.eur(mes.cuota_firmada)} al mes`,
      estado: esMes && ritmoPct !== null ? semaforo(ritmoPct, { verde: 100, ambar: 85 }) : '', comparacion: cmp(mes.firmados, comp?.firmados),
      contexto: esMes ? (conRitmo ? `A este ritmo, ${fmt.num(ritmo, 0)} a fin de mes (${fmt.pct(ritmoPct)} del objetivo). Bien desde el 100 %; vigilar entre 85 y 99 %.` : `El ritmo se calcula desde el quinto día laborable (van ${cerrados}).`)
        : 'Firmado = columna «Cliente» de GHL, por el día de la firma', medible: 'hoy', frescura: fPanel }),
    // con menos de 5 celebradas no se da el %: los firmados del periodo pueden venir de reuniones de antes (2 firmas con 1 reunión = 200 %)
    tile({ icono: 'target', etiqueta: etiP('Cierre'), valor: mes.celebradas >= 5 ? fmt.pct(pct(mes.firmados, mes.celebradas)) : null,
      sinDato: mes.celebradas ? `${mes.firmados} firmado${mes.firmados === 1 ? '' : 's'} y ${mes.celebradas} reuni${mes.celebradas === 1 ? 'ón celebrada' : 'ones celebradas'}: pocas para un %` : 'ninguna reunión celebrada en el periodo',
      unidad: mes.celebradas >= 5 ? `${mes.firmados} de ${mes.celebradas} celebradas` : '', comparacion: cmp(pc(mes.firmados, mes.celebradas), comp ? pc(comp.firmados, comp.celebradas) : null),
      estado: mes.celebradas >= 5 ? semaforo(pct(mes.firmados, mes.celebradas), { verde: 33, ambar: 20 }) : '',
      contexto: mes.celebradas ? (mes.celebradas < 5 ? 'Con menos de 5 reuniones no se pinta color' : 'Bien desde 1 de cada 3') : 'Todavía sin reuniones celebradas', medible: 'medias',
      medibleDetalle: `${mes.sin_marcar} reuniones sin marcar si se celebraron${esMes && mesNatural.de_hoy_en_vivo ? ` · las de hoy, con la etapa de GHL de las ${mesNatural.de_hoy_en_vivo.hora.slice(11)}` : ''}`, frescura: fPanel }),
    tile({ icono: 'users', etiqueta: etiP('Asistencia'), valor: asis === null ? null : fmt.pct(asis), sinDato: 'ninguna reunión marcada en el periodo', unidad: `${mes.celebradas} de ${mes.celebradas + mes.ausencias} citas ya pasadas y marcadas`,
      estado: asis === null ? '' : semaforo(asis, { verde: 80, ambar: 70 }), comparacion: cmp(asis, asisC), contexto: `Bien desde el 80 % · cuenta solo las citas que ya pasaron y tienen marca (vino / no vino); ${mes.sin_marcar} sin marcar no cuentan`, medible: 'medias', frescura: fPanel }),
  ];
  if (todo && mes.inversion !== undefined) {
    const cpc = mes.firmados ? mes.inversion / mes.firmados : null, cita = mes.citas ? mes.inversion / mes.citas : null;
    const cpcC = comp?.firmados ? comp.inversion / comp.firmados : null, citaC = comp?.citas ? comp.inversion / comp.citas : null;
    const kMant = (() => { const d = new Date(hoy.getFullYear(), hoy.getMonth() - 1, 1); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`; })();
    const mant = v.meses[kMant] || {}; const nombreMant = (MES[kMant.slice(5)] || kMant).replace(/^./, c => c.toUpperCase());
    const mantCpc = mant.firmados ? mant.inversion / mant.firmados : null;
    lista.push(
      tile({ icono: 'euro', etiqueta: etiP('Coste por cliente'), valor: cpc === null ? null : fmt.eur(cpc), sinDato: 'ningún firmado en el periodo', unidad: `${fmt.eur(mes.inversion)} ÷ ${mes.firmados}`,
        estado: cpc === null ? '' : colorCifra('coste_cliente', cpc), comparacion: cmp(cpc, cpcC, { mejorSi: 'bajo' }),
        // V2 (A-M2): misma regla y misma cuenta que el Panel de dirección; si el periodo no es el del panel, se dice su cifra
        contexto: `${mantCpc !== null && p?.id !== 'mes_ant' ? `${nombreMant} entero: ${fmt.eur(mantCpc)} (${mant.firmados} firmados), la cifra que manda en el Panel de dirección. ` : ''}Bien hasta 700 €; parar por encima de 2.500 € (la misma regla en las dos pantallas)`, medible: 'hoy', frescura: fMeta }),
      tile({ icono: 'cal', etiqueta: etiP('Coste por cita'), valor: cita === null ? null : fmt.eur(cita), sinDato: 'ninguna cita en el periodo', unidad: `${mes.citas} citas agendadas`,
        estado: cita === null ? '' : semaforo(cita, { verde: 40, ambar: 60, mejorSi: 'bajo' }), comparacion: cmp(cita, citaC, { mejorSi: 'bajo' }), contexto: 'Todas las citas agendadas en el periodo (también las que aún no han pasado) · bien hasta 40 €', medible: 'hoy', frescura: fMeta }));
  }
  cont.append(tiles(lista));
  if (p) cont.append(avisoParcial(`${antesDeDatos ? `El embudo de RO empieza el ${fechaCorta(v.datos_desde)}: antes no hay datos. ` : ''}El periodo cambia las cifras de arriba y el «Embudo». No cambian: «Hoy» (reuniones, propuestas y contratos de hoy), la agenda de 45 min y las bajas tempranas (son de hoy).`, { tipo: 'info', titulo: 'Periodo.' }));

  const caja = pestanas({
    clave: 'ventas-ro.pestana', etiqueta: 'Ventas de RO',
    pestanas: [
      ...(todo ? [{ id: 'hoy', texto: 'Hoy', icono: 'hoy', cuenta: v.hoy.length + v.propuestas.filter(parada).length + v.contratos.length, cuentaEstado: 'rojo' }] : []),
      { id: 'embudo', texto: 'Embudo', icono: 'grafico' },
      ...(todo ? [{ id: 'agenda', texto: 'Agenda de 45 min', icono: 'cal' }] : []),
      { id: 'bajas', texto: 'Bajas tempranas', icono: 'alert', cuenta: v.bajas_tempranas?.n || 0, cuentaEstado: 'rojo' },
      { id: 'anuncios', texto: 'De qué anuncio', icono: 'target' },
    ],
    pintar: (id, zona) => {
      if (id === 'hoy') pintarHoy(zona, ctx, v, fGHL);
      else if (id === 'embudo') pintarEmbudo(zona, ctx, v, { mes, sep, nombreMes, nombreP, comp, compTexto: p?.comp?.rango, esMes, conRitmo, cerrados, laborables, todo, fPanel, fMeta });
      else if (id === 'agenda') pintarAgenda(zona, ctx, v, fGHL);
      else if (id === 'anuncios') { zona.classList.add('pila'); pintarAnunciosYPrevision(zona, ctx); }
      else pintarBajas(zona, v);
    },
  });
  cont.append(caja);
  for (const a of v.avisos || []) cont.append(avisoParcial(limpiaTexto(a), { tipo: 'info' }));
}

const parada = p => (!p.abierta && p.dias >= 3) || p.dias >= 7;

function filaProspecto(ctx, v, p, { tipo }) {
  const destino = h('span', {}, nombreLead(p));
  const detalle = tipo === 'reunion'
    ? [chipEstado('gris', p.calendario), ' ', chipEstado(p.etapa === 'Cita agendada' ? 'azul' : 'gris', p.etapa),
      p.resultado ? ' ' : '', p.resultado ? chipEstado(p.resultado === 'celebrada' ? 'verde' : p.resultado === 'no_se_presento' ? 'rojo' : 'ambar',
        p.resultado === 'celebrada' ? 'Celebrada' : p.resultado === 'no_se_presento' ? 'No se presentó' : 'Pasada, sin marcar') : '', p.segunda ? ' · segunda reunión' : '', p.setter_alias ? ` · la consiguió ${p.setter_alias}` : '']
    : tipo === 'contrato'
      ? `Contrato enviado ${cuandoTexto(p.desde)} · día ${Math.min(p.dias + 1, 99)} de 7 de la secuencia${p.dias >= 14 ? ' · 14 días sin moverse: casi perdido' : ''}`
      : `Propuesta enviada hace ${p.dias} días · ${p.abierta ? `abrió el correo (${cuandoTexto(p.ultima_apertura)})` : 'no ha abierto el correo'}${p.dias >= 14 ? ' · 14 días: casi perdida' : ''}`;
  return {
    estado: tipo === 'reunion' ? 'ambar' : p.dias >= 7 ? 'rojo' : 'ambar',
    icono: tipo === 'reunion' ? 'video' : tipo === 'contrato' ? 'doc' : 'send',
    motivo: tipo === 'reunion' ? [h('b', {}, cuandoTexto(p.cuando).split(' · ')[1]), ' · ', destino] : destino,
    detalle,
    botones: [
      abrirEn('GHL', p.ghl),
      abrirEn('Fathom', p.fathom, { motivo: 'Sin grabación de Fathom cruzada con este contacto' }),
      masAcciones(
        verDatos(ctx, { almacen: 'ventas_tomas', id: p.id, destino }),
        abrirEn('GHL · oportunidades', v.enlaces?.ghl_oportunidades),
        tipo !== 'reunion' ? botonConfirmar({ texto: 'Recordarme mañana', pregunta: '¿Te lo recuerdo mañana?', confirmar: 'Sí', mini: true, soloLectura: ctx.soloLectura,
          alConfirmar: async () => { await encolar(ctx, { que: 'recordatorio_seguimiento', sobre: p.id, texto: `${tipo === 'contrato' ? 'Contrato' : 'Propuesta'} sin respuesta`, vista: 'Aviso mañana en tu día' }); return 'Apuntado'; } }) : null,
        tipo !== 'reunion' ? h('button', { type: 'button', class: 'bt mini', 'aria-disabled': 'true', title: 'Espera el permiso de escritura en GHL' }, icono('flecha'), 'Mover tarjeta') : null,
      ),
    ],
  };
}

function pintarHoy(zona, ctx, v, fGHL) {
  const paradas = v.propuestas.filter(parada);
  // V2 · «hoy» real (fecha de Madrid, helper común): un sábado con datos del viernes no titula «Reuniones de hoy» a las del
  // viernes. Si la lista es de otro día, se dice de cuál y que los datos son de esa lectura.
  const hoyR = ctx.hoy || hoyMadrid();
  const diaDato = (v.hoy[0]?.cuando || v.generado || '').slice(0, 10);
  const deHoy = !v.hoy.length ? (v.generado || '').slice(0, 10) >= hoyR : v.hoy.every(r => String(r.cuando).slice(0, 10) === hoyR);
  const diaTxt = diaSemanaV;
  zona.append(
    panel({ titulo: deHoy ? `Reuniones de hoy (${v.hoy.length})` : `Reuniones del ${diaTxt(diaDato)} (${v.hoy.length}) · datos de esa lectura`, icono: 'video',
      sub: deHoy ? 'Con la etapa de la tarjeta y quién la consiguió.' : `Hoy es ${diaTxt(hoyR)}: las reuniones de hoy saldrán con la próxima lectura de GoHighLevel. Mientras, las del ${diaTxt(diaDato)} con su etapa.` },
      listaLoPrimero(v.hoy.map(r => filaProspecto(ctx, v, r, { tipo: 'reunion' })),
        { vacio: { titulo: deHoy ? 'Hoy no tienes reuniones comerciales' : 'Sin reuniones en esa lectura', porque: deHoy ? 'Ninguna reunión de 45 o 15 minutos en la agenda de hoy.' : `Los datos son del ${diaTxt(diaDato || hoyR)}: la próxima lectura trae las de hoy.` } })),
    panel({ titulo: `Propuestas paradas (${paradas.length} de ${v.propuestas.length})`, icono: 'send', sub: 'Sin abrir a las 72 h o sin respuesta a los 7 días. Lo más antiguo arriba.' },
      listaLoPrimero(paradas.slice(0, 7).map(p => filaProspecto(ctx, v, p, { tipo: 'propuesta' })),
        { vacio: { titulo: 'Ninguna propuesta parada', porque: 'Todas abiertas y con menos de 7 días.', celebrar: true } })),
    panel({ titulo: `Contratos sin firmar (${v.contratos.length})`, icono: 'doc', sub: 'Columna «Contrato enviado» de GHL. La firma en Zoho Sign aún no se lee desde la app.' },
      listaLoPrimero(v.contratos.slice(0, 7).map(p => filaProspecto(ctx, v, p, { tipo: 'contrato' })),
        { vacio: { titulo: 'Ningún contrato pendiente de firma', porque: 'No hay tarjetas en «Contrato enviado».', celebrar: true } })),
    h('div', { class: 'fila' }, frescura(fGHL), abrirEn('GHL · oportunidades', v.enlaces?.ghl_oportunidades), abrirEn('GHL · calendario', v.enlaces?.ghl_calendario)));
}

function pintarEmbudo(zona, ctx, v, o) {
  const { mes, sep, nombreMes, nombreP, comp, compTexto, esMes, conRitmo, cerrados, laborables, todo, fPanel, fMeta } = o;
  const pasos = [
    ['contactos', 'Contactos nuevos', 'users'], ['piden_reunion', 'Piden reunión', 'mail'], ['citas', 'Citas reservadas', 'cal'], ['celebradas', 'Reuniones celebradas', 'video'],
    ['propuestas', 'Propuestas o acuerdos', 'send'], ['acuerdos', 'Acuerdos enviados', 'doc'], ['firmados', 'Firmados', 'flag'], ['cobrados', 'Cobrados', 'euro'],
  ];
  const bloque = (m, titulo) => panel({ titulo, icono: 'grafico', sub: '' },
    h('div', { class: 'cuerpo' }, embudoBarras(pasos.map(([k, t, i]) => ({ etiqueta: t, valor: m[k], icono: i })))));
  const otro = comp || sep, otroT = comp ? (compTexto || 'Periodo anterior') : 'Septiembre';
  const may = t => `${t[0].toUpperCase()}${t.slice(1)}`;
  const vivo = esMes && v.meses?.[Object.keys(v.meses).sort().pop()]?.de_hoy_en_vivo;
  zona.append(h('div', { class: 'pila' },
    bloque(mes, esMes ? `${may(nombreMes)} hasta hoy` : may(nombreP)),
    bloque(otro, may(otroT)),
    panel({ titulo: 'Comparación y ritmo', icono: 'clock', sub: esMes ? (conRitmo ? `Ritmo con ${cerrados} días laborables cerrados de ${laborables}.` : `El ritmo se calcula desde el quinto día laborable (van ${cerrados}).`) : 'El ritmo solo se calcula con «Este mes».' },
      h('div', { class: 'cuerpo' }, tablaApilable({
        filas: [
          ...(todo && mes.inversion !== undefined ? [{ paso: 'Inversión en Meta', otro: fmt.eur(otro.inversion), mes: fmt.eur(mes.inversion), ritmo: '—' }] : []),
          ...pasos.map(([k, t]) => ({ paso: t, otro: fmt.num(otro[k]), mes: fmt.num(mes[k]), ritmo: esMes && conRitmo && ['citas', 'celebradas', 'firmados'].includes(k) ? fmt.num(Math.round(mes[k] / cerrados * laborables)) : '—' })),
        ],
        columnas: [{ clave: 'paso', titulo: 'Paso', principal: true }, { clave: 'otro', titulo: may(otroT), num: true }, { clave: 'mes', titulo: esMes ? 'Este mes' : 'Periodo', num: true }, { clave: 'ritmo', titulo: 'A este ritmo', num: true }],
      }),
      avisoParcial(`Septiembre cuadra con el panel de resultados (mismas reglas, foto del ${cuandoTexto((v.panel_generado || '').replace('T', ' ').slice(0, 16))}). Celebrada = marca de GHL, grabación de Fathom o llamada de Zadarma; ${sep.sin_marcar} reuniones de septiembre siguen sin marcar.${vivo ? ` Las reuniones de hoy ya pasadas se cuentan con la etapa de GHL en vivo (${vivo.celebradas} celebrada${vivo.celebradas === 1 ? '' : 's'}, ${vivo.ausencias} sin presentarse, ${vivo.sin_marcar} sin marcar).` : ''}`, { tipo: 'info', titulo: 'Cuadre.' }),
      h('div', { class: 'fila' }, frescura(fPanel), frescura(fMeta)))),
    v.circuito ? panel({ titulo: 'El circuito, persona a persona', icono: 'capas', sub: 'Cuántas pasaron de un paso al siguiente, cuántas siguen en curso y cuántas se quedaron.' },
      h('div', { class: 'cuerpo' }, tablaApilable({ filas: v.circuito.pasos.map(p => ({ ...p, pc: fmt.pct(pct(p.pasaron, p.de)) })), columnas: [
        { clave: 't', titulo: 'Paso', principal: true }, { clave: 'de', titulo: 'Personas', num: true }, { clave: 'pasaron', titulo: 'Pasaron', num: true },
        { clave: 'pc', titulo: '% que pasa', num: true }, { clave: 'en_curso', titulo: 'En curso', num: true }, { clave: 'se_quedaron', titulo: 'Se quedaron', num: true }] }))) : null,
    v.tablero_hoy ? panel({ titulo: 'Tablero de «Ventas RO» hoy', icono: 'capas', sub: 'Tarjetas abiertas por columna.' },
      h('div', { class: 'cuerpo fila' }, Object.entries(v.tablero_hoy).map(([k, n]) => chipEstado('gris', `${k}: ${n}`)))) : null));
}

function pintarAgenda(zona, ctx, v, fGHL) {
  if (!v.huecos?.por_dia) { zona.append(vacio({ icono: 'cal', titulo: 'Sin dato de huecos', texto: 'No se pudo leer el calendario de 45 min de GHL.', quien: 'Agus', tono: 'aviso' })); return; }
  const dias = Object.entries(v.huecos.por_dia);
  const libres = dias.reduce((a, [, n]) => a + n, 0);
  const citasMes = Math.ceil(v.objetivo_firmados_mes * 3 / 0.8);      // cierre 1 de 3 y asistencia del 80 %
  const necesarias14 = Math.ceil(citasMes * 14 / 31);
  const faltan = Math.max(0, necesarias14 - (v.huecos.citas_ya || 0));
  const ocup = libres ? pct(faltan, libres) : (faltan ? 999 : 0);
  zona.append(panel({ titulo: 'Huecos libres de 45 min · próximos 14 días', icono: 'cal', sub: `Para ${v.objetivo_firmados_mes} firmados al mes hacen falta unas ${citasMes} citas (1 de cada 3 cierra y viene el 80 %): unas ${necesarias14} en 14 días.` },
    h('div', { class: 'cuerpo pila' },
      tiles([
        tile({ icono: 'cal', etiqueta: 'Huecos libres', valor: libres, unidad: `en ${dias.length} día${dias.length === 1 ? '' : 's'}`, frescura: fGHL }),
        tile({ icono: 'target', etiqueta: 'Citas que faltan', valor: faltan, unidad: `ya hay ${v.huecos.citas_ya}`, contexto: `Necesarias en 14 días: ${necesarias14}` }),
        tile({ icono: 'alert', etiqueta: '¿Caben?', valor: libres ? fmt.pct(Math.min(ocup, 999)) : null, estado: semaforo(ocup, { verde: 80, ambar: 100, mejorSi: 'bajo' }),
          contexto: ocup > 100 ? 'No caben: abrir huecos o subir setters' : 'Bien hasta el 80 % de los huecos', medible: 'hoy' }),
      ]),
      tablaApilable({ filas: dias.map(([d, n]) => ({ dia: d, n })), columnas: [
        { clave: 'dia', titulo: 'Día', principal: true, celda: f => diaSemanaV(f.dia) },
        { clave: 'n', titulo: 'Huecos libres', num: true }, { clave: 'b', titulo: 'En barra', ordenable: false, celda: f => barraProgreso({ valor: f.n, max: Math.max(...dias.map(x => x[1]), 1) }) }],
        vacio: { titulo: 'Sin huecos libres en 14 días', texto: 'La agenda de 45 min está llena o cerrada.' } }),
      h('div', { class: 'fila' }, abrirEn('GHL · calendario', v.enlaces?.ghl_calendario)))));
}

function pintarBajas(zona, v) {
  const b = v.bajas_tempranas;
  zona.append(panel({ titulo: 'Bajas en los primeros 90 días de lo vendido', icono: 'alert', sub: 'Clientes firmados desde agosto que aparecen como baja en el libro de clientes.' },
    h('div', { class: 'cuerpo pila' },
      tiles([tile({ icono: 'alert', etiqueta: 'Bajas tempranas este trimestre', valor: b ? b.n : null, unidad: b ? `de ${b.firmados_desde_agosto} firmados` : '',
        estado: !b ? '' : b.n === 0 ? 'verde' : b.n === 1 ? 'ambar' : 'rojo', contexto: 'Bien: ninguna. Rojo desde 2 al trimestre (propuesta sin firmar)', medible: 'medias',
        medibleDetalle: `Cruce por nombre con el libro de clientes (leído ${b?.libro_leido || '—'})` })]),
      b?.detalle?.length ? avisoParcial(`Coincidencia por nombre que hay que comprobar: ${b.detalle.map(x => `${x.cliente} (${x.mes})`).join(', ')}. Puede ser un cliente antiguo con un nombre parecido.`, { titulo: 'Revisar.' })
        : vacio({ icono: 'ok', titulo: 'Ninguna baja temprana', tono: 'celebrar' }))));
}

export default {
  id: 'ventas-ro',
  titulo: 'Ventas de RO',
  grupo: 'Ventas de RO',
  puestos_que_lo_ven: { direccion: 'todo', ventas_ro: 'todo', operaciones: 'resumen', proyectos: 'resumen', jefa_crm: 'resumen', outreach: 'resumen' },
  // R12 (A-A2): serie diaria → cualquier periodo; «Hoy», agenda y bajas tempranas no dependen del periodo (se dice en pantalla)
  usa_periodo: ['7d', '30d', 'mes', 'mes_ant', 'trim', 'anio', 'medida'],
  async render(contenedor, ctx) { vigilarCortes(contenedor); await pintar(contenedor, ctx); },
};
