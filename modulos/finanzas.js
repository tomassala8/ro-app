// modulos/finanzas.js · M19 «Finanzas de la empresa» (E10).
//   · Tomás (dirección y finanzas de dirección): beneficio del mes (el número que manda), margen, cuota recurrente acumulada
//     en grande con el escenario «si firman los pendientes», caja y meses de reserva, ingresos y altas/bajas mes a mes desde
//     la primera factura (dic-2022), los 20 clientes y los 20 proveedores principales, equipo SOLO agregado por áreas de 3 o más
//     personas (D-89), coste por hora real, y todo lo de cobros.
//   · Sofía (administración): su «Mi día» administrativo: calendario, cobros y devueltos, impagos por antigüedad, altas firmadas sin
//     alta en facturación, bajas y cambios de cuota, Meta sin factura y conciliación, con la caja por banco (D-86). Sin margen,
//     beneficio ni coste del equipo: la lista «direccion» le llega vacía desde servir.py (solo_todo_sin_cliente), no se esconde aquí.
// Botones: dejan la acción en la cola simulada (R9). Emitir, cobrar, pagar o tocar Airtable: nunca.
// Datos: data/finanzas/finanzas.json ← fuentes_dinero/generar_dinero.py (Holded en vivo, Airtable en lectura, panel financiero v29).

import { plegarSecundarias, grafico, plegadoMovil } from '../componentes.js';
import { h, fmt, tile, tiles, chipEstado, chipsFiltro, tablaDensa, panel, avisoParcial, vacio, icono, barraProgreso,
  listaLoPrimero, botonConfirmar, pestanas, avisoFlotante, colorCifra, campoTexto, variacion, hoyMadrid } from '../componentes.js';
import { llevarA, filaConTexto } from './_ir.js';
import { cargarDatos, filasConBarra, pieFuentes, fresco, eurS, pctS, encolar, barrasMes, numeroGrande, mesLargo, mesCorto,
  mesesPeriodo, textoMeses, sumaMeses, quinceFilas } from './dinero_comun.js';

const PRESUPUESTO_EQUIPO = 40000;

// ===================================================================== bloques de cobros (Sofía y Tomás)
function botonCola(ctx, { texto, pregunta, tipo, objeto, cliente_id, detalle, herramienta = 'app', vista, hecho = 'En la cola (simulado)' }) {
  return botonConfirmar({ texto, pregunta, confirmar: 'Sí', mini: true, soloLectura: ctx.soloLectura,
    alConfirmar: async () => { await encolar(ctx, { herramienta, tipo, objeto, cliente_id, texto: detalle, vista_previa: vista || null }); return hecho; } });
}

function formPlan(ctx, f) {
  const caja = h('span', { class: 'fila' });
  const abrir = h('button', { type: 'button', class: 'bt mini', 'aria-disabled': ctx.soloLectura ? 'true' : null, title: ctx.soloLectura ? 'Estás en «ver como»: solo lectura' : null,
    on: { click: () => {
      if (ctx.soloLectura) return;
      const cFecha = campoTexto({ etiqueta: 'Fecha del plan', tipo: 'date', valor: new Date(Date.now() + 7 * 864e5).toISOString().slice(0, 10) });
      const cNota = campoTexto({ etiqueta: 'Nota', placeholder: 'p. ej. 2 pagos' });
      const fecha = cFecha.querySelector('input'), nota = cNota.querySelector('input');
      const ok = h('button', { type: 'button', class: 'bt mini pri', on: { click: async () => {
        ok.disabled = true;
        try { await encolar(ctx, { herramienta: 'app', tipo: 'plan_de_cobro', objeto: f.doc, cliente_id: f.cliente_id, texto: `Plan de cobro de ${f.doc} (${fmt.eur(f.importe)}) para el ${fecha.value}${nota.value ? ' · ' + nota.value : ''}`, vista_previa: { fecha: fecha.value, nota: nota.value } });
          caja.replaceChildren(h('span', { class: 'estado', role: 'status' }, `✓ Plan para el ${fmt.fecha(fecha.value)} (simulado)`)); }
        catch (e) { caja.replaceChildren(h('span', { class: 'estado error', role: 'alert' }, 'No se pudo: ' + e.message)); }
      } } }, 'Guardar');
      caja.replaceChildren(cFecha, cNota, ok); fecha.focus();
    } } }, icono('cal', { clase: 's' }), 'Plan de cobro');
  caja.append(abrir);
  return caja;
}

function bloqueCalendario(a) {
  // V2 · «hoy» real (fecha de Madrid, helper común): un día 3 no puede decir «Día 2 · Cargo SEPA · hoy». El estado de cada
  // día se cuenta con la fecha de hoy; si el dato es de otro día, se dice.
  const hoy = hoyMadrid();
  const cal = (a.calendario || []).map(c => ({ ...c, estado: !c.fecha ? c.estado : c.fecha < hoy ? 'hecho' : c.fecha === hoy ? 'hoy' : 'proximo' }));
  const sub = `Hoy, ${new Date(hoy + 'T12:00').toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long' })}${a.hoy && a.hoy < hoy ? ` · lo hecho, según el calendario (datos del ${new Date(a.hoy + 'T12:00').toLocaleDateString('es-ES', { weekday: 'short', day: 'numeric' })})` : ''}`;
  return panel({ titulo: 'Calendario administrativo', icono: 'cal', sub },
    h('div', { class: 'cuerpo' }, tiles(cal.map(c => tile({ icono: c.estado === 'hecho' ? 'ok' : 'cal', etiqueta: c.estado === 'hoy' ? 'Hoy' : c.estado === 'hecho' ? 'Hecho' : `Día ${c.dia}`,
      valor: c.dia, estado: c.estado === 'hecho' ? 'gris' : c.estado === 'hoy' ? 'ambar' : '', contexto: [c.que, c.donde].filter(Boolean).join(' · ') })))));
}

function bloqueImpagos(ctx, a, { compacto, objetivo } = {}) {
  const imp = a.impagos || {};
  const vencidas = (imp.filas || []).filter(f => f.tramo !== 'Sin vencer');
  // R15a (A2): si se llega por #/finanzas/cobros/<doc> y esa factura queda fuera de las primeras, entra la última de la lista
  const tope = compacto ? 5 : 7;
  const iObj = objetivo ? vencidas.findIndex(f => f.doc === objetivo) : -1;
  const vistas = iObj >= tope ? [...vencidas.slice(0, tope - 1), vencidas[iObj]] : vencidas.slice(0, tope);
  const tramos = (imp.tramos || []).filter(t => t.tramo !== 'Sin vencer');
  const maxT = Math.max(1, ...tramos.map(t => t.importe));
  const lista = listaLoPrimero(vistas.map(f => ({
    estado: f.dias > 30 ? 'rojo' : 'ambar', icono: f.devuelto ? 'alert' : 'euro',
    motivo: `${f.nombre} · ${fmt.eur(f.importe)} · ${f.dias} días`,
    detalle: h('div', { class: 'pila' }, `${f.doc} del ${fmt.fecha(f.fecha)} · vencía el ${fmt.fecha(f.vence)}${f.aviso ? ' · ' + f.aviso : ''}${f.devuelto ? ' · recibo devuelto' : ''}`, h('div', { class: 'fila' }, [
      h('a', { class: 'bt mini', href: f.holded, target: '_blank', rel: 'noopener' }, icono('ext', { clase: 's' }), 'Holded'),
      botonCola(ctx, { texto: 'Reclamado', pregunta: '¿Marcar como reclamado?', tipo: 'cobro_reclamado', objeto: f.doc, cliente_id: f.cliente_id, detalle: `Cobro reclamado: ${f.doc} · ${f.nombre} · ${fmt.eur(f.importe)}` }),
      formPlan(ctx, f),
      f.cliente_id ? botonCola(ctx, { texto: 'Avisar al account', pregunta: '¿Avisar a su account del impago?', tipo: 'aviso_impago_account', objeto: f.doc, cliente_id: f.cliente_id, detalle: `Impago de ${f.nombre}: ${fmt.eur(f.importe)} (${f.dias} días). No le hables de dinero: lo lleva administración.`, vista: { aviso: 'en la ficha del cliente y en su Mi día' } }) : null,
      botonCola(ctx, { texto: 'Recordatorio por Desk', pregunta: '¿Dejar el recordatorio en la cola? Sale con la plantilla aprobada por Tomás y lo firma administración.', tipo: 'recordatorio_impago', herramienta: 'desk', objeto: f.doc, cliente_id: f.cliente_id,
        detalle: `Hola, te escribo de administración de Ranking Online. Nos consta pendiente la factura ${f.doc} de ${fmt.eur(f.importe)}, vencida el ${fmt.fecha(f.vence)}. ¿Nos confirmas cuándo podréis abonarla? Gracias.`,
        vista: { plantilla: 'recordatorio de impago (pendiente de aprobar por Tomás)', firma: 'Administración' } }),
    ].filter(Boolean))),
  })), { vacio: { titulo: 'Ningún recibo vencido', porque: 'Todo lo emitido está cobrado o dentro de plazo.', celebrar: true } });
  return panel({ titulo: `Impagos por antigüedad (${vencidas.length})`, icono: 'alert', sub: 'Aviso al account a 30 días, decisión de Tomás a 60, nunca más de 2 cuotas' },
    h('div', { class: 'cuerpo pila' },
      filasConBarra(tramos.map(t => ({ etiqueta: `${t.tramo} · ${t.n} factura${t.n === 1 ? '' : 's'}`, valor: fmt.eur(t.importe), actual: t.importe, max: maxT,
        estado: /61|90/.test(t.tramo) ? 'rojo' : /31/.test(t.tramo) ? 'ambar' : null })), { titulos: ['Antigüedad', '', 'Importe'] }),
      avisoParcial(`Holded marca como pendiente lo que no está conciliado: hay ${fmt.num(a.caja?.sin_conciliar_total)} movimientos de banco sin casar que pueden inflar esta lista. Comprueba antes de reclamar.`, { titulo: 'A medias.' })),
    lista);
}

function bloqueFirmas(ctx, a) {
  const f = a.firmas_sin_alta || [];
  return panel({ titulo: `Altas firmadas sin alta en facturación (${f.length})`, icono: 'doc', sub: `Firmados en Zoho Sign o en la columna «Cliente» de GHL sin línea de octubre en Airtable · revisados ${a.firmas_revisadas}` },
    listaLoPrimero(f.map(x => ({
      estado: x.dia0_pasado ? 'rojo' : 'ambar', icono: 'rocket', motivo: `${x.nombre}${x.firma ? ` · firmado el ${fmt.fecha(x.firma)}` : ''}`,
      detalle: `${x.alta ? `Día 0: ${fmt.fecha(x.alta)}` : 'Sin fecha de alta'}${x.account ? ` · ${x.account}` : ''}${x.nota ? ' · ' + x.nota : ''}`,
      botones: [botonCola(ctx, { texto: 'Alta hecha en facturación', pregunta: '¿Ya está dado de alta en Airtable y Holded?', tipo: 'alta_facturacion', objeto: x.cliente_id, cliente_id: x.cliente_id, detalle: `Alta en facturación hecha: ${x.nombre}` })],
    })), { vacio: { titulo: 'Todas las firmas tienen su línea', porque: 'Cada cliente firmado está en el Airtable de octubre.', celebrar: true } }));
}

function bloqueCambios(a) {
  const c = a.bajas_cambios || [];
  return panel({ titulo: `Bajas y cambios de cuota (${c.length})`, icono: 'capas', sub: 'Lo que hay que reflejar este mes en la facturación (doc de octubre para Sofía + Airtable)' },
    c.length ? h('div', { class: 'cuerpo' }, tablaDensa({ filas: c, apilable: true, columnas: [
      { clave: 'nombre', titulo: 'Qué', principal: true },
      { clave: 'importe', titulo: 'Efecto en la cuota', num: true, celda: x => chipEstado(x.importe < 0 ? 'rojo' : 'verde', eurS(x.importe)) },
      { clave: 'fuente', titulo: 'De dónde sale', celda: x => h('span', { class: 'sub' }, x.fuente || '—') }] }))
      : vacio({ icono: 'ok', titulo: 'Sin cambios este mes', tono: 'celebrar' }));
}

function bloqueCaja(a, { conMeses } = {}) {
  const c = a.caja || {};
  return panel({ titulo: 'Caja por banco', icono: 'cartera', sub: `Holded en vivo · el dólar a ${fmt.num(c.cambio_usd, 4)} € (BCE, media de septiembre)` },
    h('div', { class: 'cuerpo pila' },
      tablaDensa({ filas: c.cuentas || [], apilable: true, columnas: [
        { clave: 'banco', titulo: 'Cuenta', principal: true },
        { clave: 'saldo', titulo: 'Saldo', num: true, celda: x => x.moneda === 'USD' ? `${fmt.num(x.saldo, 2)} $` : fmt.eur(x.saldo) },
        { clave: 'eur', titulo: 'En euros', num: true, celda: x => fmt.eur(x.eur) },
        { clave: 'sc', titulo: 'Sin conciliar', num: true, valor: x => (c.sin_conciliar || {})[Object.keys(c.sin_conciliar || {}).find(k => k.toLowerCase().replace(/\s/g, '') === x.banco.toLowerCase().replace(/\s/g, '')) || ''] ?? null,
          celda: x => { const k = Object.keys(c.sin_conciliar || {}).find(k2 => k2.toLowerCase().replace(/\s/g, '') === x.banco.toLowerCase().replace(/\s/g, '')); const n = k ? c.sin_conciliar[k] : null; return n === null ? '—' : chipEstado(n >= 50 ? 'rojo' : n > 0 ? 'ambar' : 'verde', `${n} mov.`); } }] }),
      h('p', { class: 'fila sub' }, h('b', {}, `Total: ${fmt.eur(c.total_eur)}`), `· ${c.sin_conciliar_total ?? '—'} movimientos sin conciliar (meta: 0 al cierre) · conciliación del 30-sep`),
      conMeses || null));
}

function cifrasCobros(a, d, fH, fA) {
  const t = a.cuota_tres || {};
  const imp = a.impagos || {};
  const sinPlan = (imp.filas || []).filter(f => f.tramo !== 'Sin vencer').length;
  return [
    tile({ icono: 'euro', etiqueta: `Cuota cobrada · ${mesLargo(t.mes).split(' ')[0]}`, valor: t.cobrado_pct === null ? null : fmt.pct(t.cobrado_pct),
      unidad: `${fmt.eur(t.cobrada)} de ${fmt.eur(t.facturada)}`, estado: new Date().getDate() >= 10 ? (t.cobrado_pct >= 95 ? 'verde' : t.cobrado_pct >= 85 ? 'ambar' : 'rojo') : 'gris',
      comparacion: { texto: `septiembre: ${fmt.pct(t.cobrado_pct_sep)}` }, contexto: 'Verde ≥ 95 % el día 10 · rojo < 85 % (el color sale el día 10)', medible: 'medias',
      medibleDetalle: 'El cargo SEPA del día 2 aún no ha entrado; 529 movimientos sin conciliar', frescura: fH }),
    tile({ icono: 'alert', etiqueta: 'Recibos vencidos sin plan', valor: sinPlan, unidad: fmt.eur(imp.vencido_total), estado: sinPlan ? 'rojo' : 'verde',
      contexto: `${imp.mas_30 || 0} con más de 30 días · ${imp.mas_60 || 0} con más de 60`, medible: 'hoy', frescura: fH,
      ir: 'Ver cuáles', alPulsar: () => document.querySelector('[data-bloque=impagos]')?.scrollIntoView({ behavior: 'smooth' }) }),
    tile({ icono: 'doc', etiqueta: 'Firmados sin alta en facturación', valor: (a.firmas_sin_alta || []).length, estado: (a.firmas_sin_alta || []).length ? 'rojo' : 'verde',
      contexto: 'Antes del día 0 del cliente', medible: 'hoy', frescura: fA, ir: 'Ver cuáles', alPulsar: () => document.querySelector('[data-bloque=firmas]')?.scrollIntoView({ behavior: 'smooth' }) }),
    tile({ icono: 'alert', etiqueta: 'Recibos devueltos', valor: (a.devueltos || []).length, estado: (a.devueltos || []).length ? 'rojo' : 'verde', contexto: 'SEPA o tarjeta devueltos (Holded)', medible: 'medias',
      medibleDetalle: 'Holded ve el cobro, no siempre el motivo de la devolución', frescura: fH }),
    tile({ icono: 'clock', etiqueta: 'Días de cobro', valor: a.dias_cobro?.valor ?? null, unidad: 'días', estado: (a.dias_cobro?.valor ?? 99) <= 15 ? 'verde' : (a.dias_cobro?.valor ?? 0) <= 60 ? 'ambar' : 'rojo',
      contexto: 'Verde ≤ 15 · rojo > 60 (tope legal, Ley 15/2010)', medible: 'hoy', medibleDetalle: a.dias_cobro?.texto }),
    tile({ icono: 'users', etiqueta: 'Cliente que más pesa', valor: pctS(a.concentracion?.uno, 1), unidad: 'de la cuota', estado: (a.concentracion?.uno ?? 0) < 20 ? 'verde' : a.concentracion.uno <= 25 ? 'ambar' : 'rojo',
      contexto: `Los 10 mayores: ${pctS(a.concentracion?.diez, 1)} · verde < 20 % (referencia de mercado)`, medible: 'hoy' }),
  ];
}

function bloqueCuota(a) {
  const t = a.cuota_tres || {};
  if (!t.desglose) return null;
  return panel({ titulo: 'Cuota de octubre, línea a línea', icono: 'euro', sub: 'Airtable (solo lectura) + firmados sin ficha + proyectos ± cambios del mes. Debajo, lo que ya está emitido en Holded.' },
    h('div', { class: 'cuerpo pila' },
      tiles([
        tile({ icono: 'sube', etiqueta: 'Cuota recurrente firmada', valor: fmt.eur(t.recurrente), contexto: 'Lo que se cobra cada mes', medible: 'hoy' }),
        tile({ icono: 'doc', etiqueta: 'Facturable en octubre', valor: fmt.eur(t.facturable), contexto: `Cuota de octubre ${fmt.eur(t.cuota_mes)} con proyectos y cambios`, medible: 'hoy' }),
        tile({ icono: 'euro', etiqueta: 'Emitido en Holded', valor: fmt.eur(t.facturada), contexto: `${t.facturas_n} facturas sin IVA · cobrado ${fmt.eur(t.cobrada)}`, medible: 'hoy' }),
      ]),
      tablaDensa({ filas: t.desglose, apilable: true, columnas: [
        { clave: 'concepto', titulo: 'Concepto', principal: true, celda: x => x.tipo === 'total' ? h('b', {}, x.concepto) : x.tipo === 'info' ? h('span', { class: 'sub' }, x.concepto) : x.concepto },
        { clave: 'importe', titulo: 'Importe', num: true, celda: x => x.tipo === 'info' ? '—' : x.tipo === 'total' ? h('b', {}, fmt.eur(x.importe)) : `${x.importe < 0 ? '−' : '+'}${fmt.eur(Math.abs(x.importe))}` }] }),
      (t.contraste_holded || []).length ? h('div', { class: 'pila' }, h('div', { class: 'titulo-seccion' }, icono('alert', { clase: 's' }), 'Diferencias con lo emitido en Holded'),
        tablaDensa({ filas: t.contraste_holded, apilable: true, columnas: [
          { clave: 'nombre', titulo: 'Cliente', principal: true },
          { clave: 'facturable', titulo: 'Facturable', num: true, celda: x => fmt.eur(x.facturable) },
          { clave: 'emitido_holded', titulo: 'Emitido en Holded', num: true, celda: x => fmt.eur(x.emitido_holded) },
          { clave: 'diferencia', titulo: 'Diferencia', num: true, celda: x => chipEstado(x.diferencia > 0 ? 'ambar' : 'rojo', eurS(x.diferencia)) }] })) : null,
      (t.pendientes_esperados || []).length ? h('p', { class: 'sub' }, `Pendientes de firmar que se esperan: ${t.pendientes_esperados.join(' y ')} (no cuentan hasta que firmen).`) : null));
}

// R15a (A2): #/finanzas/cobros/<documento o cliente> → la factura vencida, el recibo devuelto o el alta firmada, resaltada
function irAlCobro(cont, a, obj) {
  if (!obj) return;
  const imp = (a.impagos?.filas || []).find(f => f.doc === obj);
  const dev = (a.devueltos || []).find(f => f.doc === obj);
  const fir = (a.firmas_sin_alta || []).find(f => f.cliente_id === obj);
  const donde = imp ? '[data-bloque=impagos]' : fir ? '[data-bloque=firmas]' : dev ? '[data-bloque=devueltos]' : null;
  const texto = imp ? obj : fir ? fir.nombre : dev ? obj : null;
  if (!donde) return;
  llevarA(cont, r => { const z = r.querySelector(donde); return z ? filaConTexto(z, texto, 'li') : null; });
}

function pintarCobros(cont, ctx, d, { tomas, objetivo } = {}) {
  const a = d.admin;
  const fH = fresco(d, 'Holded'), fA = fresco(d, 'Airtable');
  if (!tomas) cont.append(tiles(cifrasCobros(a, d, fH, fA)));
  cont.append(bloqueCalendario(a));
  const bc = bloqueCuota(a); if (bc) cont.append(bc);
  const impP = bloqueImpagos(ctx, a, { objetivo }); impP.dataset.bloque = 'impagos';
  const firP = bloqueFirmas(ctx, a); firP.dataset.bloque = 'firmas';
  const dev = a.devueltos || [];
  const devP = panel({ titulo: `Cobros de ayer y devueltos`, icono: 'recargar', sub: 'Recibos SEPA y tarjetas devueltos, cliente por cliente' },
      dev.length ? listaLoPrimero(dev.map(x => ({ estado: 'rojo', icono: 'alert', motivo: `${x.nombre} · ${fmt.eur(x.importe)}`, detalle: `${x.doc} · ${x.dias} días`,
        botones: [h('a', { class: 'bt mini', href: x.holded, target: '_blank', rel: 'noopener' }, icono('ext', { clase: 's' }), 'Holded')] })))
        : vacio({ icono: 'ok', tono: 'celebrar', titulo: 'Ningún recibo devuelto', texto: `El cargo SEPA de octubre entra el día 2: cuota cobrada en septiembre ${fmt.pct(a.cuota_tres?.cobrado_pct_sep)}.` }));
  devP.dataset.bloque = 'devueltos';
  cont.append(h('div', { class: 'dos' }, impP, h('div', { class: 'pila' }, firP, devP)));
  cont.append(h('div', { class: 'dos' }, bloqueCambios(a), h('div', { class: 'pila' },
    panel({ titulo: 'Facturas de Meta fuera de la contabilidad', icono: 'target', sub: a.meta_sin_factura?.texto },
      h('div', { class: 'cuerpo' }, tiles([tile({ icono: 'target', etiqueta: 'Gasto de Meta sin factura', valor: a.meta_sin_factura?.gasto_meta == null ? null : fmt.eur(a.meta_sin_factura.gasto_meta), estado: a.meta_sin_factura?.gasto_meta == null ? '' : 'rojo', sinDato: 'No ves este dato por tu puesto: el importe de Meta lo ve dirección. Pídele la cifra a Tomás para contabilizarla.',
        comparacion: { texto: 'septiembre sin factura' }, contexto: 'Meta factura por tarjeta: hay que bajar las facturas del administrador de anuncios y subirlas a Holded.' })]))),
    bloqueCaja(a))));
  irAlCobro(cont, a, objetivo);
}

// ===================================================================== periodo (R12, A-A2)
// Los datos de Finanzas son MENSUALES: el periodo de la barra se lee por meses enteros (dinero_comun.mesesPeriodo). Lo de hoy
// (caja, cobros, impagos, cuota de octubre, los 20 principales) no cambia con el periodo, y se dice.
const NO_CAMBIA = 'No cambian con el periodo: la caja, los cobros, los impagos, la cuota de octubre y los 20 principales (son de hoy).';
function comp(actual, anterior, p, { mejorSi = 'alto', pct = true } = {}) {
  if (!p?.comp || actual === null || anterior === null || anterior === undefined) return undefined;
  return pct ? { delta: variacion(actual, anterior), pct: true, mejorSi, texto: `frente a ${textoMeses(mesesPeriodo(p).comp)}` }
    : { delta: actual - anterior, mejorSi, texto: `frente a ${textoMeses(mesesPeriodo(p).comp)}` };
}
function bloquePeriodo(ctx, d, { tomas }) {
  const p = ctx.periodo;
  if (!p) return null;
  const { meses, comp: mc } = mesesPeriodo(p);
  const fact = d.admin?.facturado_mes || [];
  const enCurso = fact.filter(x => x.curso && meses.includes(x.m)).map(x => mesLargo(x.m).split(' de ')[0]);
  const ing = sumaMeses(fact, meses, 'total'), ingC = mc.length ? sumaMeses(fact, mc, 'total') : null;
  const cuota = sumaMeses(fact, meses, 'cuota');
  const cobrado = sumaMeses(fact.filter(x => !x.curso), meses, x => (x.total || 0) * (x.cobrado_pct || 0) / 100);
  const baseCob = sumaMeses(fact.filter(x => !x.curso), meses, 'total');
  const lista = [
    tile({ icono: 'euro', etiqueta: 'Facturado en el periodo', valor: ing === null ? null : fmt.eur(ing), sinDato: 'Holded empieza en diciembre de 2022',
      comparacion: comp(ing, ingC, p), contexto: `${textoMeses(meses)} · toda la empresa, también lo facturado a clientes que ya se fueron (en Dinero por cliente, solo los de hoy) · cuota ${fmt.eur(cuota)}${enCurso.length ? ` · ${enCurso.join(' y ')} en curso` : ''} · sin IVA`, medible: 'hoy', frescura: fresco(d, 'Holded') }),
    tile({ icono: 'check', etiqueta: 'Cobrado de lo facturado', valor: baseCob ? fmt.pct((100 * cobrado) / baseCob) : null, sinDato: 'Solo meses cerrados: el del periodo está en curso',
      unidad: baseCob ? `${fmt.eur(cobrado)} de ${fmt.eur(baseCob)}` : '', contexto: 'Meses cerrados del periodo · Holded', medible: 'medias', medibleDetalle: 'El cobro sale de Holded; hay movimientos sin conciliar' }),
  ];
  if (tomas) {
    const dir = d.direccion[0] || {};
    const pyg = dir.pyg || [];
    const cerrados = meses.filter(m => pyg.some(x => x.m === m));
    const cerradosC = mc.filter(m => pyg.some(x => x.m === m));
    const ultimo = pyg[pyg.length - 1]?.m;
    const bai = cerrados.length ? sumaMeses(pyg, cerrados, 'bai') : null, baiC = cerradosC.length ? sumaMeses(pyg, cerradosC, 'bai') : null;
    const ingP = cerrados.length ? sumaMeses(pyg, cerrados, 'ing') : null, mb = cerrados.length ? sumaMeses(pyg, cerrados, 'mb') : null;
    const mbC = cerradosC.length ? sumaMeses(pyg, cerradosC, 'mb') : null, ingPC = cerradosC.length ? sumaMeses(pyg, cerradosC, 'ing') : null;
    const mbPct = ingP ? (100 * mb) / ingP : null, mbPctC = ingPC ? (100 * mbC) / ingPC : null;
    const sinCierre = `Sin mes cerrado en este periodo: el último cierre de Sofía es ${ultimo ? mesLargo(ultimo).split(' de ')[0] : '—'}`;
    const faltan = meses.filter(m => !cerrados.includes(m) && m > (ultimo || ''));
    const ab = dir.altas_bajas || [];
    const altas = sumaMeses(ab, meses, 'altas'), bajas = sumaMeses(ab, meses, 'bajas');
    lista.push(
      tile({ icono: 'grafico', etiqueta: 'Beneficio en el periodo', valor: bai === null ? null : eurS(bai), sinDato: sinCierre, estado: bai === null ? '' : colorCifra('beneficio', bai),
        comparacion: comp(bai, baiC, p, { pct: false }), contexto: bai === null ? null : `${textoMeses(cerrados)}${faltan.length ? ` · sin cerrar: ${faltan.map(m => mesLargo(m).split(' de ')[0]).join(' y ')}` : ''} · gastos convertidos a euros`, medible: 'hoy' }),
      tile({ icono: 'sube', etiqueta: 'Margen bruto en el periodo', valor: mbPct === null ? null : pctS(mbPct, 1), sinDato: sinCierre,
        estado: mbPct === null ? '' : mbPct >= 35 ? 'verde' : mbPct >= 25 ? 'ambar' : 'rojo', comparacion: mbPct === null || mbPctC === null || !p.comp ? undefined : { delta: Math.round((mbPct - mbPctC) * 10) / 10, unidad: ' puntos', mejorSi: 'alto', texto: `frente a ${textoMeses(cerradosC)}` },
        contexto: mbPct === null ? null : `Ingresos menos equipo y entrega · ${textoMeses(cerrados)} · verde ≥ 35 %`, medible: 'hoy' }),
      tile({ icono: 'users', etiqueta: 'Altas y bajas en el periodo', valor: altas === null ? null : `+${altas} / −${bajas || 0}`, sinDato: 'Sin meses en el libro de clientes',
        contexto: `${textoMeses(meses)} · libro de clientes`, medible: 'hoy' }));
  }
  return panel({ titulo: `En el periodo · ${textoMeses(meses)}`, icono: 'cal', sub: `${p.texto || p.nombre}. Cuenta por meses enteros: los datos de la empresa son mensuales. ${NO_CAMBIA}` },
    h('div', { class: 'cuerpo' }, tiles(lista)));
}

// ===================================================================== Finanzas v3 (3-oct): beneficio, equipo, impagos y cuadre
// Datos: data/finanzas/cuadre.json (solo dirección), cuadre_facturacion.json (dirección y administración), impagos.json e
// impagos_clientes.json ← fuentes_dinero/generar_cuadre.py. El beneficio de 2026 es EL MISMO número que Mi día y el Panel.
const MESES_C = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const ejeMes = m => { const [y, mm] = String(m).split('-'); return `${MESES_C[Number(mm) - 1]} ${y.slice(2)}`; };
const eur2 = v => (v === null || v === undefined ? '—' : `${v < 0 ? '−' : ''}${fmt.eur(Math.abs(v), 2)}`);
const nomMes = m => mesLargo(m).split(' de ')[0];

function bloqueBeneficio(ctx, cu) {
  const B = cu?.beneficio;
  if (!B?.meses?.length) return null;
  const L = B.meses;
  const zona = h('div', { class: 'pila' });
  const pintarB = modo => {
    const con = modo === 'con';
    const val = x => (con && typeof x.real === 'number' ? x.real : x.bai);
    const mar = x => (con && typeof x.margen_real_pct === 'number' ? x.margen_real_pct : x.margen_pct);
    const cerrados = L.filter(x => !x.estimado);
    const ult = cerrados.at(-1) || {};
    const a26 = B.anios?.['2026'] || {}, a25 = B.anios?.['2025'] || {};
    const anio = con ? a26.real : a26.bai;
    const mejor = [...cerrados].sort((a, b) => val(b) - val(a))[0], peor = [...cerrados].sort((a, b) => val(a) - val(b))[0];
    zona.replaceChildren(
      tiles([
        tile({ icono: 'grafico', etiqueta: `Beneficio de ${nomMes(ult.m)}${con ? ' · con gasto sin factura' : ''}`, valor: eur2(val(ult)), estado: colorCifra('beneficio', val(ult)),
          contexto: `Margen ${pctS(mar(ult), 1)} sobre ${fmt.eur(ult.ing)} · ${con ? `según facturas: ${eur2(ult.bai)}` : `con el gasto sin factura: ${eur2(ult.real)}`}`, medible: 'hoy' }),
        tile({ icono: 'sube', etiqueta: `Beneficio de ${nomMes(a26.desde || '2026-01')} a ${nomMes(a26.hasta || ult.m)} de 2026${con ? ' · con gasto sin factura' : ''}`, valor: eurS(anio), estado: colorCifra('beneficio', anio),
          contexto: `${pctS(con ? (100 * a26.real) / a26.ing : a26.margen_pct, 1)} de los ingresos · ${con ? `según facturas: ${eurS(a26.bai)}` : `con el gasto sin factura: ${eurS(a26.real)}`}`, medible: 'hoy' }),
        tile({ icono: 'flag', etiqueta: 'Mejor y peor mes de 2026', valor: `${nomMes(mejor.m)} · ${nomMes(peor.m)}`, contexto: `${eurS(val(mejor))} y ${eurS(val(peor))}`, medible: 'hoy' }),
        tile({ icono: 'cal', etiqueta: 'Beneficio de 2025 (estimado)', valor: eurS(a25.bai), estado: 'gris', contexto: `${pctS(a25.margen_pct, 1)} de los ingresos · sin la nómina de España: va alto`, medible: 'medias',
          medibleDetalle: 'Holded tiene el equipo de 2025 mal fechado y no lleva la nómina de España: decide Tomás en «Cuadre de fuentes»' }),
      ]),
      grafico({ x: L.map(x => x.m), formatoX: ejeMes, alto: 240, barrasPrimero: true, etiquetaUltimo: false, formato: v => eurS(v),
        barras: { nombre: 'Beneficio', y: L.map(val), formato: v => eurS(v), clase: (i, v) => (L[i].estimado ? 'est' : v >= 0 ? 'pos' : 'neg'),
          nombreDe: (i, v) => (L[i].estimado ? 'Beneficio estimado' : v < 0 ? 'Pérdida' : 'Beneficio'),
          leyenda: [{ nombre: 'Beneficio', clase: 'pos' }, { nombre: 'Pérdida', clase: 'neg' }, { nombre: '2025, estimado', clase: 'est' }] },
        series: [{ nombre: 'Margen sobre ingresos', y: L.map(mar), escalaPropia: true, formato: v => pctS(v, 1), color: 'var(--accent)' }],
        detalle: i => { const x = L[i]; return [`Ingresos ${fmt.eur(x.ing)}`, `− Equipo y colaboradores ${fmt.eur(x.equipo)}`, `− Publicidad propia ${fmt.eur(x.publicidad)}`,
          `− Herramientas ${fmt.eur(x.herramientas)}`, `− Otros gastos ${fmt.eur(x.otros)}`, con && typeof x.sin_factura === 'number' ? `− Gasto sin factura ${fmt.eur(x.sin_factura)}` : null,
          x.estimado ? (con ? 'Estimado; en 2025 no hay dato de gasto sin factura' : 'Estimado: equipo y herramientas repartidos en el año') : null].filter(Boolean); } }),
      h('p', { class: 'sub' }, `Barras: beneficio de cada mes (verde, se gana; rojo, se pierde; gris, 2025 estimado). Línea: margen sobre los ingresos, con su escala a la derecha. ${(() => { const [y, mm] = ult.m.split('-').map(Number); const sig = mm === 12 ? `${y + 1}-01` : `${y}-${String(mm + 1).padStart(2, '0')}`; return `${nomMes(sig).replace(/^./, c => c.toUpperCase())} se cierra el día 10.`; })()} Pasa el ratón por un mes para ver ingresos, equipo, publicidad, herramientas y otros.`));
  };
  const modo = chipsFiltro({ opciones: [{ valor: 'sin', texto: 'Según facturas', icono: 'doc' }, { valor: 'con', texto: 'Con el gasto sin factura', icono: 'alert' }],
    clave: 'finanzas-beneficio-modo', etiqueta: 'Qué beneficio', alCambiar: pintarB });
  pintarB(modo.valor());
  return panel({ titulo: 'Beneficio mes a mes', icono: 'grafico', sub: `${nomMes(L[0].m)} de ${L[0].m.slice(0, 4)} a ${mesLargo(B.ultimo_cerrado)} · el mismo beneficio que Mi día y el Panel de dirección` },
    h('div', { class: 'cuerpo pila' }, modo, zona));
}

/** Coste del equipo mes a mes, fuente a fuente (solo totales: nunca lo de una persona). */
const EST_EQ = { ok: ['verde', 'Cargado'], falta: ['rojo', 'Faltan facturas'], paquete: ['ambar', 'Facturas de otros meses'], provisional: ['gris', 'Sin cerrar'] };
function bloqueEquipoMes(cu) {
  const E = cu?.equipo_mes || [];
  if (!E.length) return null;
  const R0 = cu.equipo_resumen || {};
  const est = x => x.m.startsWith('2025') || x.estado === 'provisional';
  const tabla = quinceFilas(tablaDensa({ filas: [...E].reverse(), apilable: true, orden: null, porPagina: 0, columnas: [
    { clave: 'm', titulo: 'Mes', principal: true, celda: x => mesLargo(x.m) },
    { clave: 'holded', titulo: 'Holded tal cual', num: true, celda: x => fmt.eur(x.holded) },
    { clave: 'excel_equipo', titulo: 'Excel de sueldos', num: true, celda: x => fmt.eur(x.excel_equipo) },
    { clave: 'usado', titulo: 'El que vale', num: true, celda: x => h('b', {}, fmt.eur(x.usado)) },
    { clave: 'estado', titulo: 'Estado', celda: x => chipEstado(...(EST_EQ[x.estado] || ['gris', x.estado])) },
    { clave: 'nota', titulo: 'Por qué', celda: x => h('span', { class: 'sub' }, x.nota || x.de_donde) }] }));
  return panel({ titulo: 'Coste del equipo mes a mes', icono: 'eq', sub: `Equipo, colaboradores y nómina de España, en euros. ${R0.regla || ''}` },
    h('div', { class: 'cuerpo pila' },
      grafico({ x: E.map(x => x.m), formatoX: ejeMes, alto: 220, barrasPrimero: true, etiquetaUltimo: false, formato: v => fmt.eur(v), leyenda: true,
        barras: { nombre: 'El que vale', y: E.map(x => x.usado), formato: v => fmt.eur(v), clase: i => (est(E[i]) ? 'est' : ''),
          leyenda: [{ nombre: 'El que vale (cierre de Sofía en euros)' }, { nombre: 'Estimado o sin cerrar', clase: 'est' }] },
        series: [{ nombre: 'Holded tal cual', y: E.map(x => x.holded), color: 'var(--serie-2)' }, { nombre: 'Excel de sueldos', y: E.map(x => x.excel_equipo ?? null), color: 'var(--serie-3)' }],
        detalle: i => [EST_EQ[E[i].estado]?.[1], E[i].nota].filter(Boolean) }),
      R0.meses_falta?.length ? avisoParcial(`En Holded faltan las facturas del equipo de ${R0.meses_falta.map(nomMes).join(', ')} de 2025 y el ${Number(String(R0.paquete_dia).slice(8, 10))} de ${nomMes(String(R0.paquete_dia).slice(0, 7))} se subieron ${R0.paquete_n} de golpe. Propuesta: repartir el equipo de 2025 (${fmt.eur(R0.total_2025_holded)} en el año) según los ingresos de cada mes. Lo decides en «Cuadre de fuentes».`, { titulo: 'Equipo de 2025 mal fechado.' }) : null,
      tabla));
}

// ---------------------------------------------------------------- impagos (Tomás y Sofía: completo)
const EST_IMP = { 'pendiente': 'gris', 'aviso al account': 'ambar', 'reclamado': 'ambar', 'plan de pago': 'azul', 'monitorio': 'rojo', 'decide Tomás': 'rojo', 'recibo devuelto': 'rojo', 'baja': 'gris' };
const TIPO_ACC = { cobro_reclamado: 'Reclamado', plan_de_cobro: 'Plan de pago', recordatorio_impago: 'Recordatorio por Desk', aviso_impago_account: 'Aviso al account', impago_estado: 'Estado cambiado' };
async function accionesCobro(ctx) {
  if (!ctx.servidor || !ctx.api) return [];
  try { return ((await ctx.api('acciones?modulo=finanzas')).acciones || []).filter(a => TIPO_ACC[a.tipo]); } catch { return []; }
}
function pintarImpagos(cont, ctx, imp, { acciones = [] } = {}) {
  if (!imp?.filas) { cont.append(vacio({ icono: 'alert', titulo: 'Sin el mapa de impagos', texto: 'Falta lanzar el lector de cuadre e impagos.', quien: 'Agus' })); return; }
  const R0 = imp.resumen || {};
  const porDoc = {};
  for (const a of acciones) (porDoc[a.objeto] = porDoc[a.objeto] || []).push(a);
  const filas = imp.filas.map(f => {
    const acc = (porDoc[f.doc] || []).sort((a, b) => String(b.creada).localeCompare(String(a.creada)));
    const ultApp = acc[0];
    const estApp = ultApp?.tipo === 'impago_estado' ? (JSON.parse(ultApp.vista_previa || '{}') || {}).estado : ultApp?.tipo === 'plan_de_cobro' ? 'plan de pago' : ultApp?.tipo === 'cobro_reclamado' ? 'reclamado' : null;
    return { ...f, intentos: (f.devoluciones || 0) + acc.length, estado: estApp || f.estado,
      ultima: ultApp ? `${TIPO_ACC[ultApp.tipo]} · ${fmt.fechaHora(ultApp.creada)} (en la cola, simulado)` : f.ultima_accion ? `${f.ultima_accion}${f.ultima_fecha ? ` · ${fmt.fecha(f.ultima_fecha)}` : ''}` : 'Ninguna anotada' };
  });
  cont.append(tiles([
    tile({ icono: 'alert', etiqueta: 'Vencido sin cobrar', valor: fmt.eur(R0.vencido), unidad: `${R0.facturas} facturas`, estado: R0.mas_60 ? 'rojo' : R0.vencido ? 'ambar' : 'verde', contexto: 'Holded en vivo, sin IVA descontado (importe pendiente de cada factura)', medible: 'hoy', frescura: fresco(imp, 'Holded') }),
    tile({ icono: 'users', etiqueta: 'Clientes con impago', valor: R0.clientes, estado: R0.clientes ? 'ambar' : 'verde', contexto: `${filas.filter(f => f.ex_cliente || !f.cliente_id).length} ya no son clientes`, medible: 'hoy' }),
    tile({ icono: 'clock', etiqueta: 'Antigüedad media', valor: R0.antiguedad_media, unidad: 'días', estado: R0.antiguedad_media > 60 ? 'rojo' : R0.antiguedad_media > 30 ? 'ambar' : 'verde', contexto: `Por importe: ${R0.antiguedad_media_ponderada} días (las facturas viejas son pequeñas)`, medible: 'hoy' }),
    tile({ icono: 'flag', etiqueta: 'Más de 60 días', valor: R0.mas_60, estado: R0.mas_60 ? 'rojo' : 'verde', contexto: 'A 60 días decide Tomás: cortar, plan de pago, monitorio o darla por perdida', medible: 'hoy' }),
  ]));
  const maxT = Math.max(1, ...(imp.tramos || []).map(t => t.importe));
  const ev = imp.evolucion || [];
  cont.append(h('div', { class: 'pila' },
    panel({ titulo: 'Por antigüedad', icono: 'capas', sub: 'Aviso al account a 30 días, decisión de Tomás a 60, nunca más de 2 cuotas' },
      h('div', { class: 'cuerpo' }, filasConBarra((imp.tramos || []).map(t => ({ etiqueta: `${t.tramo} · ${fmt.plural ? fmt.plural(t.n, 'factura') : `${t.n} facturas`}`, valor: fmt.eur(t.importe), actual: t.importe, max: maxT,
        estado: /61|90/.test(t.tramo) ? 'rojo' : /31/.test(t.tramo) ? 'ambar' : null })), { titulos: ['Antigüedad', '', 'Importe'] }))),
    panel({ titulo: 'Vencido sin cobrar, mes a mes', icono: 'grafico', sub: 'Lo que quedaba vencido y sin cobrar al final de cada mes (con las fechas de cobro de Holded); el último, hoy' },
      h('div', { class: 'cuerpo' }, grafico({ x: ev.map(x => x.m), formatoX: ejeMes, alto: 200, formato: v => fmt.eur(v),
        barras: { nombre: 'Vencido sin cobrar', y: ev.map(x => x.vencido), formato: v => fmt.eur(v), clase: (i, v) => (v > 15000 ? 'neg' : '') },
        detalle: i => [`${ev[i].facturas} facturas`, ev[i].curso ? 'Hoy' : null].filter(Boolean) })))));
  const botones = f => h('div', { class: 'fila' }, [
    botonCola(ctx, { texto: 'Reclamar', pregunta: '¿Anotar que se ha reclamado? (simulado: no se manda nada)', tipo: 'cobro_reclamado', objeto: f.doc, cliente_id: f.cliente_id, detalle: `Cobro reclamado: ${f.doc} · ${f.nombre} · ${fmt.eur(f.importe)}` }),
    formPlan(ctx, f),
    f.dias > 60 ? botonCola(ctx, { texto: 'Pasar a monitorio', pregunta: '¿Anotar que pasa a monitorio? Lo decide Tomás (simulado).', tipo: 'impago_estado', objeto: f.doc, cliente_id: f.cliente_id, detalle: `${f.doc} · ${f.nombre}: pasa a monitorio`, vista: { estado: 'monitorio' } }) : null,
  ].filter(Boolean));
  const tabla = tablaDensa({ filas, apilable: true, porPagina: 0, buscar: { campos: ['nombre', 'doc'], placeholder: 'Buscar cliente o factura' },
    filtros: [{ clave: 'estado', titulo: 'Estado' }, { clave: 'tramo', titulo: 'Antigüedad' }],
    columnas: [
      { clave: 'nombre', titulo: 'Cliente y factura', principal: true, celda: x => h('span', { class: 'pila' }, h('b', {}, x.nombre),
        h('span', { class: 'sub' }, x.holded ? h('a', { href: x.holded, target: '_blank', rel: 'noopener' }, x.doc) : x.doc, x.ex_cliente || !x.cliente_id ? ' · ya no es cliente' : '')) },
      { clave: 'importe', titulo: 'Importe', num: true, celda: x => fmt.eur(x.importe, 2) },
      { clave: 'dias', titulo: 'Días de retraso', num: true, celda: x => chipEstado(x.dias > 60 ? 'rojo' : x.dias > 30 ? 'ambar' : 'gris', fmt.num(x.dias)) },
      { clave: 'estado', titulo: 'Estado', celda: x => chipEstado(EST_IMP[x.estado] || 'gris', x.estado) },
      { clave: 'account_id', titulo: 'Account', celda: x => (x.account_id ? ctx.nombre(x.account_id) : '—') },
      { clave: 'intentos', titulo: 'Intentos y última acción', valor: x => x.intentos, celda: x => h('span', { class: 'pila' }, h('span', {}, `${fmt.num(x.intentos)} ${x.intentos === 1 ? 'intento' : 'intentos'}`), h('span', { class: 'sub' }, x.ultima)) },
      { clave: 'siguiente', titulo: 'Siguiente paso', celda: x => h('span', { class: 'pila' }, h('span', { class: 'sub' }, x.siguiente), botones(x)) }] });
  cont.append(panel({ titulo: `Cada factura vencida (${filas.length})`, icono: 'alert', sub: `${imp.regla} Los botones dejan la acción en la cola (simulado) y en el rastro.` },
    h('div', { class: 'cuerpo' }, tabla)));
}

// ---------------------------------------------------------------- cuadre de fuentes (Tomás todo; Sofía lo facturado)
const GRAV = { alta: 'rojo', media: 'ambar', baja: 'gris' };
function pintarCuadre(cont, ctx, cu, { completo } = {}) {
  if (!cu?.cuadre) { cont.append(vacio({ icono: 'capas', titulo: 'Sin el cuadre de fuentes', texto: 'Falta lanzar el lector de cuadre e impagos.', quien: 'Agus' })); return; }
  const inc = cu.incongruencias || [];
  const n = g => inc.filter(i => i.gravedad === g).length;
  cont.append(tiles([
    tile({ icono: 'flag', etiqueta: 'Incongruencias para decidir', valor: inc.length, estado: n('alta') ? 'rojo' : inc.length ? 'ambar' : 'verde', contexto: `${n('alta')} altas · ${n('media')} medias · ${n('baja')} bajas · decide Tomás`, medible: 'hoy' }),
    ...(cu.comprobado || []).slice(0, completo ? 3 : 2).map(t => tile({ icono: 'ok', etiqueta: 'Comprobado', valor: 'Cuadra', estado: 'verde', contexto: t, medible: 'hoy' })),
  ]));
  cont.append(panel({ titulo: 'Qué no cuadra y qué proponemos', icono: 'flag', sub: completo ? 'Holded, el Excel de cierre de Sofía, el Excel de sueldos (solo totales) y el Airtable de facturación (solo lectura). Para cada una, la cifra que proponemos dar por buena y por qué.' : 'Lo facturado: Holded, el cierre de Sofía y el Airtable de facturación (solo lectura). Lo decide Tomás.' },
    listaLoPrimero(inc.map(i => ({ estado: GRAV[i.gravedad] || 'gris', icono: i.ambito === 'equipo' ? 'eq' : i.ambito === 'gastos' ? 'capas' : 'euro',
      motivo: i.que,
      detalle: h('div', { class: 'pila' },
        h('p', {}, h('b', {}, 'Propuesta: '), i.propuesta),
        h('p', { class: 'sub' }, h('b', {}, 'Por qué: '), i.por_que),
        i.alternativa ? h('p', { class: 'sub' }, h('b', {}, 'Otra opción: '), i.alternativa) : null,
        h('div', { class: 'fila' }, chipEstado('azul', `Decide ${i.decide}`), i.impacto != null ? chipEstado('gris', `Efecto: ${fmt.eurSigno(i.impacto)}`) : null, h('span', { class: 'sub' }, i.mes))),
      botones: completo ? [botonCola(ctx, { texto: 'Vale la propuesta', pregunta: '¿Apuntar que das por buena la propuesta? (simulado; no cambia ninguna cifra hasta aplicarlo)', tipo: 'cuadre_decision', objeto: i.id, detalle: `Cuadre · ${i.que} → vale la propuesta`, vista: { decision: 'propuesta', id: i.id } })] : [],
    })), { vacio: { titulo: 'Todo cuadra', porque: 'Las fuentes dicen lo mismo.', celebrar: true } })));
  const C = (cu.cuadre || []).slice().reverse();
  const colFact = [
    { clave: 'm', titulo: 'Mes', principal: true, celda: x => `${mesLargo(x.m)}${x.curso ? ' (en curso)' : ''}` },
    { clave: 'facturado_holded', titulo: 'Holded', num: true, celda: x => fmt.eur(x.facturado_holded) },
    { clave: 'facturado_cierre', titulo: 'Cierre de Sofía', num: true, celda: x => fmt.eur(x.facturado_cierre) },
    { clave: 'facturado_panel', titulo: 'Panel', num: true, celda: x => fmt.eur(x.facturado_panel) },
    { clave: 'facturado_airtable', titulo: 'Airtable', num: true, celda: x => fmt.eur(x.facturado_airtable) },
    { clave: 'dif', titulo: 'Diferencia', num: true, valor: x => Math.abs(x.dif_facturado_airtable_holded || 0) + Math.abs(x.dif_facturado_holded_panel || 0),
      celda: x => { const d = x.dif_facturado_airtable_holded ?? null, e = x.dif_facturado_holded_panel; const parts = [];
        if (e && Math.abs(e) >= 1) parts.push(chipEstado('ambar', `Holded − panel ${fmt.eurSigno(e, 2)}`));
        if (d !== null && Math.abs(d) >= 1) parts.push(chipEstado(Math.abs(d) > 1000 ? 'ambar' : 'gris', `Airtable − Holded ${fmt.eurSigno(d)}`));
        return parts.length ? h('span', { class: 'pila' }, parts) : chipEstado('verde', 'cuadra'); } }];
  cont.append(panel({ titulo: 'Lo facturado mes a mes, según cada fuente', icono: 'euro', sub: 'Sin IVA y con las rectificativas restadas. Airtable solo tiene agosto, septiembre y octubre; el cierre de Sofía, de enero a agosto de 2026.' },
    h('div', { class: 'cuerpo' }, quinceFilas(tablaDensa({ filas: C, apilable: true, orden: null, porPagina: 0, columnas: colFact })))));
  const AD = cu.airtable_diferencias || [];
  if (AD.length) cont.append(panel({ titulo: 'Airtable frente a Holded, cliente a cliente', icono: 'capas', sub: 'Lo que explica la diferencia de cada mes: extras, prorrateos y cambios de cuota que Airtable no recoge' },
    h('div', { class: 'cuerpo' }, quinceFilas(tablaDensa({ filas: AD, apilable: true, porPagina: 0, columnas: [
      { clave: 'm', titulo: 'Mes', celda: x => nomMes(x.m) },
      { clave: 'nombre', titulo: 'Cliente', principal: true },
      { clave: 'airtable', titulo: 'Airtable', num: true, celda: x => fmt.eur(x.airtable) },
      { clave: 'holded', titulo: 'Holded', num: true, celda: x => fmt.eur(x.holded) },
      { clave: 'dif', titulo: 'Diferencia', num: true, celda: x => chipEstado(x.dif > 0 ? 'ambar' : 'rojo', fmt.eurSigno(x.dif)) }] })))));
  if (!completo) return;
  cont.append(panel({ titulo: 'Los gastos mes a mes, según cada fuente', icono: 'libro', sub: 'Holded convertido a euros con el tipo de cada factura; el cierre de Sofía tal cual (dólares como euros) y corregido. El corregido es el que usan Finanzas, Mi día y el Panel.' },
    h('div', { class: 'cuerpo' }, quinceFilas(tablaDensa({ filas: C.filter(x => x.gasto_holded != null || x.gasto_corregido != null), apilable: true, orden: null, porPagina: 0, columnas: [
      { clave: 'm', titulo: 'Mes', principal: true, celda: x => mesLargo(x.m) },
      { clave: 'gasto_holded', titulo: 'Holded', num: true, celda: x => fmt.eur(x.gasto_holded) },
      { clave: 'gasto_cierre_tal_cual', titulo: 'Cierre tal cual', num: true, celda: x => (x.gasto_cierre_tal_cual == null ? '—' : h('span', { class: 'dim' }, fmt.eur(x.gasto_cierre_tal_cual))) },
      { clave: 'gasto_corregido', titulo: 'Cierre corregido (vale)', num: true, celda: x => (x.gasto_corregido == null ? '—' : h('b', {}, fmt.eur(x.gasto_corregido))) },
      { clave: 'gasto_sin_factura', titulo: 'Gasto sin factura', num: true, celda: x => fmt.eur(x.gasto_sin_factura) },
      { clave: 'dif_gasto_corregido_holded', titulo: 'Corregido − Holded', num: true, celda: x => (x.dif_gasto_corregido_holded == null ? '—' : fmt.eurSigno(x.dif_gasto_corregido_holded)) }] })))));
  const be = bloqueEquipoMes(cu); if (be) cont.append(be);
}

// ===================================================================== Tomás
function pintarResumen(cont, ctx, d) {
  const dir = d.direccion[0], a = d.admin;
  const bb = bloqueBeneficio(ctx, d.cuadre); if (bb) cont.append(bb);     // v3: el beneficio de cada mes, lo primero
  const bp = bloquePeriodo(ctx, d, { tomas: true }); if (bp) cont.append(bp);
  const n = dir.numero || {}, cr = dir.cuota_recurrente || {}, cj = dir.caja || {};
  // regla común (auditoría 30): beneficio positivo = verde en todas las pantallas (el mismo que en Mi día)
  const estBen = colorCifra('beneficio', n.beneficio);
  // escenario: hoy o si firman los pendientes
  const zonaCuota = h('div');
  const pintarCuota = esc => {
    const v = esc === 'firman' ? cr.si_firman_mes : cr.cuota_mes;
    zonaCuota.replaceChildren(numeroGrande({ secundaria: true, icono: 'sube', etiqueta: 'Cuota de octubre', valor: fmt.eur(v), unidad: 'al mes', estado: '',
      texto: esc === 'firman' ? `Si firman los ${cr.pendientes.length} contratos enviados (${fmt.eur(cr.si_firman_mes - cr.cuota_mes)} más).` : `Recurrente firmada ${fmt.eur(cr.actual)} + proyectos con fin. Facturable en octubre: ${fmt.eur(cr.facturable)}.`,
      lineas: [...(cr.desglose || []).filter(x => x.tipo !== 'info').map(x => [x.concepto, x.tipo === 'total' ? fmt.eur(x.importe) : `${x.importe < 0 ? '−' : '+'}${fmt.eur(Math.abs(x.importe))}`]),
        ...(esc === 'firman' ? cr.pendientes.map(p => [`${p.nombre_m} · contrato enviado hace ${p.dias} días${p.abierta ? ' · abierto' : ''}`, `+${fmt.eur(p.cuota)}`]) : [])],
      extra: h('div', { class: 'pila' }, h('p', { class: 'fila' }, h('span', { class: 'sub' }, 'Hacia el objetivo de diciembre'), h('b', {}, `${fmt.pct((100 * v) / cr.objetivo_dic)} de ${fmt.eur(cr.objetivo_dic)}`)),
        barraProgreso({ valor: v, max: cr.objetivo_dic, estado: null, etiqueta: `${fmt.eur(v)} de ${fmt.eur(cr.objetivo_dic)}` }), h('span', { class: 'sub' }, cr.plan_texto)) }));
  };
  const esc = chipsFiltro({ opciones: [{ valor: 'hoy', texto: 'Hoy', icono: 'ok' }, { valor: 'firman', texto: `Si firman los ${cr.pendientes.length} pendientes`, icono: 'rocket', cuenta: cr.pendientes.length }],
    clave: 'finanzas-escenario', etiqueta: 'Escenario', alCambiar: pintarCuota });
  pintarCuota(esc.valor());
  cont.append(h('div', { class: 'dos' },
    numeroGrande({ icono: 'grafico', etiqueta: `Beneficio de ${mesLargo(n.mes || '2026-08').split(' ')[0]} · el número que manda`, valor: eurS(n.beneficio), estado: estBen, colorValor: true,
      texto: `Margen ${pctS(n.margen_pct, 1)} sobre ${fmt.eur(n.ingresos)} de ingresos · último mes cerrado por Sofía. Norte: ${n.objetivo_texto}.`,
      lineas: [['Con el gasto sin factura (techo, puede contar dos veces)', eurS(n.beneficio_real)], ['Plan del mes', eurS(n.plan_res)],
        ['El cierre de Sofía decía (dólares como euros)', eurS(dir.correccion_cierre?.mes_beneficio_cierre)],
        ['En 2026 (ene-ago): beneficio · real', `${eurS(dir.anio?.bai)} · ${eurS(dir.anio?.real)}`]],
      extra: h('p', { class: 'sub' }, 'Gastos convertidos a euros factura a factura con el tipo de Holded (auditoría del cierre, 2-oct). ', n.sin_factura_texto || '', ' Septiembre aún sin cerrar (día 10).') }),
    h('div', { class: 'pila' }, esc, zonaCuota)));

  const mesesCaja = cj.meses;
  const ingSep = (dir.ingresos || []).find(x => x.m === '2026-09');
  const ingAgo = (dir.ingresos || []).find(x => x.m === '2026-08');
  const eq = dir.equipo || {};
  cont.append(tiles([
    tile({ icono: 'cartera', etiqueta: 'Caja hoy', valor: fmt.eur(cj.total), comparacion: { delta: cj.total - cj.cierre_31ago, unidad: ' €', texto: 'frente al 31-ago' },
      contexto: 'Sabadell, BBVA, Wise en euros y dólares', medible: 'hoy', frescura: fresco(d, 'Holded'), ir: 'Ver por banco', alPulsar: () => tabs.elegir('cobros') }),
    tile({ icono: 'escudo', etiqueta: 'Meses de reserva', valor: fmt.num(mesesCaja, 1), unidad: 'meses', estado: mesesCaja >= 2 ? 'verde' : mesesCaja >= 1 ? 'ambar' : 'rojo',
      contexto: `Si no entrara nada: caja ÷ gasto medio corregido (${fmt.eur(cj.gasto_medio)}/mes) · el flujo del año es +${fmt.eur(cj.flujo_neto_anio)}`, medible: 'hoy', medibleDetalle: cj.texto }),
    tile({ icono: 'euro', etiqueta: 'Ingresos de septiembre', valor: fmt.eur(ingSep?.total), comparacion: { delta: ingSep && ingAgo ? ((ingSep.total - ingAgo.total) / ingAgo.total) * 100 : null, pct: true, texto: 'frente a agosto' },
      contexto: `Cuota ${fmt.eur(ingSep?.cuota)} + puntual ${fmt.eur(ingSep?.puntual)} − rectificativas ${fmt.eur(Math.abs(ingSep?.rect || 0))}`, medible: 'hoy', ir: 'Ver mes a mes', alPulsar: () => tabs.elegir('ingresos') }),
    tile({ icono: 'grafico', etiqueta: 'Margen bruto 2026', valor: pctS(dir.kpi?.mb, 1), estado: dir.kpi?.mb >= 35 ? 'verde' : dir.kpi?.mb >= 25 ? 'ambar' : 'rojo',
      contexto: 'Verde ≥ 35 % · rojo < 25 %', medible: 'hoy', ir: 'Ver resultados', alPulsar: () => tabs.elegir('resultados') }),
    tile({ icono: 'eq', etiqueta: 'Peso del equipo sobre ingresos', valor: pctS(eq.peso_ingresos, 1), estado: eq.peso_ingresos <= 55 ? 'verde' : eq.peso_ingresos <= 65 ? 'ambar' : 'rojo',
      contexto: `${mesLargo(eq.cierre_mes || '2026-08')}: ${fmt.eur(eq.coste_equipo_cierre)} · verde ≤ 55 % (referencia de mercado)`, medible: 'hoy', medibleDetalle: 'Equipo + colaboradores del cierre de Sofía; agregado, sin sueldos' }),
    tile({ icono: 'baja', etiqueta: 'Retención neta (trimestre)', valor: pctS(dir.kpi?.nrr, 1), estado: dir.kpi?.nrr >= 90 ? 'verde' : dir.kpi?.nrr >= 85 ? 'ambar' : 'rojo',
      contexto: `Verde ≥ 90 % · rojo < 85 % · bajas al mes ${pctS(dir.kpi?.churn_n, 1)}`, medible: 'medias', medibleDetalle: 'Falta la fórmula única de Sofía (74 % frente a 80 %)' }),
    tile({ icono: 'alert', etiqueta: 'Recibos vencidos', valor: fmt.eur(a.impagos?.vencido_total), unidad: `${a.impagos?.vencido_n} facturas`, estado: a.impagos?.mas_60 ? 'rojo' : a.impagos?.vencido_n ? 'ambar' : 'verde',
      contexto: `${a.impagos?.mas_30} con más de 30 días · ${a.impagos?.mas_60} con más de 60 (te toca decidir)`, medible: 'medias', medibleDetalle: '529 movimientos sin conciliar', ir: 'Ver cobros', alPulsar: () => tabs.elegir('cobros') }),
    tile({ icono: 'users', etiqueta: 'Concentración', valor: pctS(dir.concentracion?.cuota?.uno ?? a.concentracion?.uno, 1), unidad: 'el mayor',
      estado: (a.concentracion?.uno ?? 0) < 20 ? 'verde' : 'ambar', contexto: `12 meses: el mayor ${pctS(dir.concentracion?.uno, 1)} (${dir.concentracion?.primero}) · 10 mayores ${pctS(dir.concentracion?.diez, 1)}`, medible: 'hoy' }),
  ]));

  // v3: el beneficio mes a mes va arriba (bloqueBeneficio); aquí, lo que pide decisión
  const incN = (d.cuadre?.incongruencias || []).filter(i => i.gravedad === 'alta').length;
  cont.append(h('div', {},
    panel({ titulo: 'Lo que pide tu decisión', icono: 'flag', sub: 'Del dinero, lo que no se arregla solo' },
      listaLoPrimero([
        a.impagos?.mas_60 ? { estado: 'rojo', icono: 'alert', motivo: `${a.impagos.mas_60} recibo${a.impagos.mas_60 === 1 ? '' : 's'} con más de 60 días`, detalle: 'A 60 días decides tú: cortar, plan de pago o darlo por perdido.', botones: [h('button', { type: 'button', class: 'bt mini', on: { click: () => tabs.elegir('cobros') } }, 'Ver')] } : null,
        (a.firmas_sin_alta || []).length ? { estado: 'rojo', icono: 'doc', motivo: `${a.firmas_sin_alta.length} firmados sin línea en facturación`, detalle: a.firmas_sin_alta.map(x => x.nombre).join(', ') + ': no entran en la cuota que factura Sofía.' } : null,
        mesesCaja < 2 ? { estado: mesesCaja < 1 ? 'rojo' : 'ambar', icono: 'escudo', motivo: `Caja para ${fmt.num(mesesCaja, 1)} meses si no entrara nada`, detalle: 'Referencia: mínimo 2 meses. El flujo del año es positivo, pero conviene fijar tu colchón.' } : null,
        (n.beneficio_real ?? 0) < 0 && n.beneficio >= 0 ? { estado: 'ambar', icono: 'doc', motivo: `${mesLargo(n.mes).split(' ')[0]}: ${eurS(n.beneficio)} según facturas, ${eurS(n.beneficio_real)} con el gasto sin factura`, detalle: `Hay ${fmt.eur(n.sin_factura)} de cargos sin factura (techo). Que Sofía los cierre con la conciliación de Holded.` } : null,
        n.beneficio < 0 ? { estado: 'rojo', icono: 'grafico', motivo: `${mesLargo(n.mes).split(' ')[0]} en pérdidas: ${eurS(n.beneficio)}`, detalle: `Real ${eurS(n.beneficio_real)} con ${fmt.eur(n.sin_factura)} de gasto sin factura.` } : null,
        eq.peso_ingresos > 65 ? { estado: 'rojo', icono: 'eq', motivo: `El equipo pesa el ${pctS(eq.peso_ingresos, 0)} de los ingresos`, detalle: 'Referencia de mercado: 55 %. Más altas con el mismo equipo o revisar cuotas.' } : null,
        incN ? { estado: 'rojo', icono: 'capas', motivo: `${incN} ${incN === 1 ? 'cifra que no cuadra' : 'cifras que no cuadran'} entre Holded, el cierre y Airtable`, detalle: 'Con la propuesta de cuál vale y por qué.', botones: [h('button', { type: 'button', class: 'bt mini', on: { click: () => tabs.elegir('cuadre') } }, 'Ver el cuadre')] } : null,
      ].filter(Boolean)))));
}

function pintarIngresos(cont, ctx, d) {
  const dir = d.direccion[0];
  const ing = dir.ingresos || [];
  cont.append(panel({ titulo: 'Ingresos mes a mes desde la primera factura', icono: 'euro', sub: `${mesLargo(ing[0]?.m || '2022-12')} → hoy · Selfconta, Zoho Books y Holded · sin IVA` },
    h('div', { class: 'cuerpo' }, barrasMes({ meses: ing.map(x => ({ m: x.m, valores: [x.cuota, (x.puntual || 0) + (x.extra || 0), x.rect || 0] })),
      nombres: ['Cuota recurrente', 'Puntual y extras', 'Rectificativas'], total: 'Facturado', formato: v => fmt.eur(v) }))));
  const anios = dir.anios || [];
  const mp = ctx.periodo ? mesesPeriodo(ctx.periodo).meses : [];
  const enP = L => { const f = (L || []).filter(x => mp.includes(x.m)); return f.length ? f : (L || []).slice(-12); };
  const notaP = mp.length ? ` Tablas: ${textoMeses(mp)} (si el periodo no tiene meses, los 12 últimos). Los gráficos enseñan toda la historia.` : '';
  cont.append(h('div', { class: 'pila' },
    panel({ titulo: 'Por año', icono: 'cal' }, h('div', { class: 'cuerpo' }, tablaDensa({ filas: anios, apilable: true, columnas: [
      { clave: 'y', titulo: 'Año', principal: true, celda: x => `${x.y}${x.parcial ? ' (parcial)' : ''}` },
      { clave: 'total', titulo: 'Ingresos', num: true, celda: x => fmt.eur(x.total) },
      { clave: 'cuota', titulo: 'De cuota', num: true, celda: x => `${fmt.eur(x.cuota)} · ${fmt.pct(x.peso_cuota)}` },
      { clave: 'crec', titulo: 'Crecimiento', num: true, celda: x => x.crec === null || x.crec === undefined ? '—' : chipEstado(colorCifra('delta', x.crec), pctS(x.crec)) }] }))),
    panel({ titulo: 'Cuota mensual: el puente', icono: 'capas', sub: `Mes anterior + altas + subidas − bajadas − bajas = mes actual. Cierra al euro.${notaP}` },
      h('div', { class: 'cuerpo' }, tablaDensa({ filas: [...enP(dir.puente)].reverse(), apilable: true, columnas: [
        { clave: 'm', titulo: 'Mes', principal: true, celda: x => mesLargo(x.m) },
        { clave: 'altas', titulo: 'Altas', num: true, celda: x => x.altas ? h('span', { title: (x.qa || []).map(q => q[0]).join(', ') }, `+${fmt.eur(x.altas)}`) : '—' },
        { clave: 'bajas', titulo: 'Bajas', num: true, celda: x => x.bajas ? h('span', { title: (x.qb || []).map(q => q[0]).join(', ') }, eurS(x.bajas)) : '—' },
        { clave: 'fin', titulo: 'Cuota al cierre', num: true, celda: x => fmt.eur(x.fin) },
        { clave: 'cuadra', titulo: '¿Cierra?', celda: x => chipEstado(x.cuadra ? 'verde' : 'rojo', x.cuadra ? 'sí' : 'no') }] })))));
  // v3 (3-oct): altas y bajas en su propio gráfico (altas arriba en verde, bajas abajo en rojo, el neto en línea) y los
  // clientes activos aparte, con su escala: en el mismo gráfico los activos aplastaban las altas y las bajas.
  const ab = dir.altas_bajas || [];
  const neto = x => (x.altas || 0) - (x.bajas || 0);
  cont.append(panel({ titulo: 'Altas y bajas de clientes, mes a mes', icono: 'users', sub: 'Libro de clientes cerrado con Tomás el 1-oct. Verde: clientes que entran; rojo: los que se van; la línea es el neto del mes. Pasa el ratón para ver la cuota que entra y la que sale.' },
    h('div', { class: 'cuerpo pila' },
      grafico({ x: ab.map(x => x.m), formatoX: ejeMes, alto: 220, barrasPrimero: true, etiquetaUltimo: false, formato: v => fmt.num(v),
        barras: { nombre: 'Altas', y: ab.map(x => x.altas || 0), clase: () => 'pos', formato: v => `+${fmt.num(v)}`, leyenda: [{ nombre: 'Altas', clase: 'pos' }] },
        barras2: { nombre: 'Bajas', y: ab.map(x => -(x.bajas || 0)), clase: () => 'neg', formato: v => `−${fmt.num(Math.abs(v))}`, leyenda: [{ nombre: 'Bajas', clase: 'neg' }] },
        series: [{ nombre: 'Neto del mes', y: ab.map(neto), color: 'var(--accent)' }],
        detalle: i => [`Cuota nueva ${fmt.eur(ab[i].entra)} · cuota perdida ${fmt.eur(ab[i].sale)}`, ab[i].curso ? 'Mes en curso' : null].filter(Boolean) }))));
  cont.append(panel({ titulo: 'Clientes activos al cierre de cada mes', icono: 'grafico', sub: 'Su propia escala: lo que suma el neto de altas y bajas mes a mes' },
    h('div', { class: 'cuerpo' }, grafico({ x: ab.map(x => x.m), formatoX: ejeMes, alto: 180, formato: v => fmt.num(v),
      series: [{ nombre: 'Clientes activos', y: ab.map(x => x.fin) }] }))));
  cont.append(panel({ titulo: 'Altas y bajas, mes a mes en tabla', icono: 'libro', sub: `Recuentos y euros en columnas separadas.${notaP}` },
    h('div', { class: 'cuerpo pila' },
      tablaDensa({ filas: [...enP(ab)].reverse(), apilable: true, columnas: [
        { clave: 'm', titulo: 'Mes', principal: true, celda: x => `${mesLargo(x.m)}${x.curso ? ' (en curso)' : ''}` },
        { clave: 'altas', titulo: 'Altas', num: true, celda: x => (x.altas ? h('span', { title: (x.qa || []).join(', ') }, `+${fmt.num(x.altas)}`) : '0') },
        { clave: 'entra', titulo: 'Cuota nueva', num: true, celda: x => (x.entra ? `+${fmt.eur(x.entra)}` : '—') },
        { clave: 'bajas', titulo: 'Bajas', num: true, celda: x => (x.bajas ? h('span', { title: (x.qb || []).join(', ') }, `−${fmt.num(x.bajas)}`) : '0') },
        { clave: 'sale', titulo: 'Cuota perdida', num: true, celda: x => (x.sale ? `−${fmt.eur(x.sale)}` : '—') },
        { clave: 'neto', titulo: 'Neto', num: true, valor: neto, celda: x => chipEstado(neto(x) > 0 ? 'verde' : neto(x) < 0 ? 'rojo' : 'gris', `${neto(x) > 0 ? '+' : neto(x) < 0 ? '−' : ''}${fmt.num(Math.abs(neto(x)))}`) },
        { clave: 'fin', titulo: 'Activos al cierre', num: true },
        { clave: 'pct', titulo: '% bajas', num: true, celda: x => x.pct === null || x.pct === undefined ? '—' : chipEstado(x.pct <= 3 ? 'verde' : x.pct <= 5 ? 'ambar' : 'rojo', pctS(x.pct, 1)) },
        { clave: 'qb', titulo: 'Quién se fue', celda: x => h('span', { class: 'sub' }, (x.qb || []).join(', ') || '—') }] }),
      h('details', { class: 'que-es' }, h('summary', {}, `Ver los ${ab.length} meses con nombres`),
        tablaDensa({ filas: [...ab].reverse(), apilable: true, orden: null, columnas: [
          { clave: 'm', titulo: 'Mes', principal: true, celda: x => mesLargo(x.m) },
          { clave: 'qa', titulo: 'Altas', celda: x => `+${x.altas}${x.qa?.length ? ` · ${x.qa.join(', ')}` : ''}` },
          { clave: 'qb', titulo: 'Bajas', celda: x => `−${x.bajas}${x.qb?.length ? ` · ${x.qb.join(', ')}` : ''}` },
          { clave: 'fin', titulo: 'Activos', num: true }] })))));
}

function pintarTop(cont, ctx, d) {
  const dir = d.direccion[0];
  const zona = h('div');
  const COL = [
    { clave: 'pos', titulo: '#', num: true },
    { clave: 'n', titulo: 'Cliente', principal: true, celda: x => h('span', { class: 'pila', style: { gap: 'var(--s-1)', minWidth: '0' } }, h('b', {}, x.n), h('span', { class: 'sub' }, `${x.sector} · ${x.tramo}`)) },
    { clave: 'total', titulo: 'Facturado en total', num: true, celda: x => fmt.eur(x.total) },
    { clave: 'cuota', titulo: 'Cuota hoy', num: true, celda: x => x.cuota ? fmt.eur(x.cuota) : '—' },
    { clave: 'meses', titulo: 'Meses', num: true, celda: x => fmt.num(x.meses, 0) },
    { clave: 'peso12', titulo: 'Peso 12 meses', num: true, celda: x => pctS(x.peso12, 1) },
    { clave: 'estado', titulo: 'Estado', celda: x => chipEstado(x.estado === 'Activo' ? 'verde' : x.estado === 'Baja' ? 'gris' : 'azul', x.estado) },
  ];
  const pintarL = v => {
    const L = (v === 'cuota' ? dir.top_cuota : v === 'antig' ? dir.top_antig || dir.top_total : dir.top_total) || [];
    zona.replaceChildren(tablaDensa({ filas: L.map((x, i) => ({ ...x, pos: i + 1 })), columnas: COL, apilable: true }));
  };
  const ch = chipsFiltro({ opciones: [{ valor: 'total', texto: 'Por lo facturado desde el inicio', icono: 'euro' }, { valor: 'cuota', texto: 'Por cuota de hoy', icono: 'sube' }], clave: 'finanzas-top', alCambiar: pintarL });
  cont.append(panel({ titulo: 'Los 20 clientes principales', icono: 'crown', sub: `Concentración: el mayor pesa ${pctS(dir.concentracion?.uno, 1)} de los últimos 12 meses; los 5 mayores ${pctS(dir.concentracion?.cinco, 1)}; los 10 mayores ${pctS(dir.concentracion?.diez, 1)}` },
    h('div', { class: 'cuerpo pila' }, ch, zona)));
  pintarL(ch.valor());
  const prov = dir.proveedores_12m || [];
  cont.append(panel({ titulo: 'Los 20 proveedores principales · últimos 12 meses', icono: 'maletin', sub: `Total ${fmt.eur(dir.proveedores_12m_total)}. Las personas van siempre juntas (equipo y colaboradores): nunca el coste de una persona.` },
    h('div', { class: 'cuerpo' }, tablaDensa({ filas: prov.map((x, i) => ({ ...x, pos: i + 1 })), apilable: true, columnas: [
      { clave: 'pos', titulo: '#', num: true },
      { clave: 'n', titulo: 'Proveedor', principal: true },
      { clave: 'cat', titulo: 'Partida' },
      { clave: 'v', titulo: '12 meses', num: true, celda: x => fmt.eur(x.v) },
      { clave: 'peso', titulo: 'Peso', num: true, celda: x => h('div', { class: 'pila' }, h('span', {}, pctS(x.peso, 1)), barraProgreso({ valor: x.peso, max: Math.max(...prov.map(p => p.peso)) })) },
      { clave: 'tipo', titulo: 'Tipo', celda: x => chipEstado(x.tipo === 'recurrente' ? 'azul' : 'gris', `${x.tipo} · ${x.meses} de ${x.de} meses`) }] }))));
}

function bloqueFiabilidad(f, { tomas, dir } = {}) {
  if (!f) return null;
  const EST = { fiable: ['verde', 'Fiable'], errores: ['ambar', 'Con errores'], no_fiable: ['rojo', 'No fiable'] };
  const conv = f.conversion || {};
  return panel({ titulo: 'Fiabilidad del cierre de agosto', icono: 'escudo', sub: `Qué se puede usar tal cual y qué no · ${f.fuente}` },
    h('div', { class: 'cuerpo pila' },
      avisoParcial(`El cierre sumaba las facturas en dólares como si fueran euros. Aquí se corrige factura a factura con el tipo de Holded. Sobraba: ${fmt.eur(conv.usd)} por los dólares, ${fmt.eur(conv.repetidas)} de facturas repetidas y ${fmt.eur(conv.iva_cargado)} de una factura cargada con IVA. Faltaba: ${fmt.eur(-conv.gbp)} por las libras y ${fmt.eur(-conv.faltan_agosto)} de facturas de agosto que no estaban. En total, ${fmt.eur(conv.total)} menos de gasto de enero a agosto.`, { titulo: 'Gastos inflados.' }),
      tomas && dir?.correccion_cierre ? h('p', { class: 'sub' }, `Ene-ago: gastos ${fmt.eur(dir.correccion_cierre.gastos_cierre)} → ${fmt.eur(dir.correccion_cierre.gastos)} · beneficio ${eurS(dir.correccion_cierre.beneficio_cierre)} → ${eurS(dir.correccion_cierre.beneficio)}`) : null,
      tablaDensa({ filas: f.hojas, apilable: true, orden: null, columnas: [
        { clave: 'hoja', titulo: 'Hoja', principal: true },
        { clave: 'veredicto', titulo: 'Veredicto', celda: x => chipEstado(...(EST[x.veredicto] || ['gris', x.veredicto])) },
        { clave: 'por_que', titulo: 'Por qué', celda: x => h('span', { class: 'sub' }, x.por_que) }] }),
      h('div', { class: 'dos' },
        h('div', { class: 'pila' }, h('div', { class: 'titulo-seccion' }, icono('capas', { clase: 's' }), `Facturas repetidas también en Holded (${f.repetidas.length})`),
          listaLoPrimero(f.repetidas.map(x => ({ estado: 'ambar', icono: 'copy', motivo: `${x.proveedor} · ${x.doc}`, detalle: `${mesLargo(x.mes)} · ${fmt.num(x.importe, 2)} (borrar la copia en Holded)` })), { vacio: { titulo: 'Ninguna repetida', porque: '', celebrar: true } })),
        h('div', { class: 'pila' }, h('div', { class: 'titulo-seccion' }, icono('alert', { clase: 's' }), `Facturas dudosas (${f.dudosas.length}) · ${fmt.eur(f.dudosas_importe)}`),
          listaLoPrimero(f.dudosas.map(x => ({ estado: 'ambar', icono: 'info', motivo: `${x.divisa === 'ARS' ? 'Pesos argentinos' : x.divisa === 'IDR' ? 'Rupias' : x.divisa} · ${x.doc}`, detalle: `${mesLargo(x.mes)} · Holded dice esa divisa, pero el importe parece en euros o dólares: mirar el original` }))))),
      (f.euros_a_confirmar || []).length ? h('div', { class: 'pila' }, h('div', { class: 'titulo-seccion' }, icono('info', { clase: 's' }), `En euros, a confirmar con el PDF (${f.euros_a_confirmar.length})`),
        listaLoPrimero(f.euros_a_confirmar.map(x => ({ estado: 'ambar', icono: 'doc', motivo: `${x.proveedor} · ${x.doc}`, detalle: `${mesLargo(x.mes)} · ${x.texto}` })))) : null,
      h('div', { class: 'pila' }, h('div', { class: 'titulo-seccion' }, icono('flag', { clase: 's' }), 'Para el cierre de septiembre'),
        avisoParcial(f.recomendacion, { tipo: 'info', titulo: 'Conversión.' }),
        h('ul', {}, (f.otras || []).map(t => h('li', { class: 'sub' }, t))))));
}

function bloqueComparacion(dir) {
  const c = dir.comparacion_2025_2026 || [];
  if (c.length < 2) return null;
  return panel({ titulo: '2025 frente a 2026, en euros los dos', icono: 'grafico', sub: 'Enero a agosto de cada año, con los gastos en dólares convertidos a euros en los dos (antes 2026 iba sin convertir y parecía más caro)' },
    h('div', { class: 'cuerpo' }, tablaDensa({ filas: c, apilable: true, columnas: [
      { clave: 'anio', titulo: 'Ene-ago', principal: true },
      { clave: 'ingresos', titulo: 'Ingresos', num: true, celda: x => fmt.eur(x.ingresos) },
      { clave: 'gastos', titulo: 'Gastos', num: true, celda: x => fmt.eur(x.gastos) },
      { clave: 'beneficio', titulo: 'Beneficio', num: true, celda: x => chipEstado(colorCifra('beneficio', x.beneficio), eurS(x.beneficio)) },
      { clave: 'peso_equipo', titulo: 'Equipo sobre ingresos', num: true, celda: x => pctS(x.peso_equipo, 1) }] }),
      h('p', { class: 'sub' }, 'Ojo: los gastos de 2025 en Holded están incompletos (panel financiero): parte del equipo no facturaba por Holded. Compara los ingresos con seguridad; los gastos y el beneficio de 2025, solo como tendencia.')));
}

function pintarResultados(cont, ctx, d) {
  const dir = d.direccion[0];
  const pygTodo = dir.pyg || [];
  const mp = ctx.periodo ? mesesPeriodo(ctx.periodo).meses : [];
  const pygP = pygTodo.filter(x => mp.includes(x.m));
  const pyg = pygP.length ? pygP : pygTodo;
  const notaP = !ctx.periodo ? '' : pygP.length ? ` Meses del periodo: ${textoMeses(pygP.map(x => x.m))}.` : ` El periodo elegido no tiene meses cerrados: se ven todos los de 2026.`;
  cont.append(panel({ titulo: 'Cuenta de resultados · 2026', icono: 'libro', sub: `Ingresos del cierre de Sofía (fiables); gastos del cierre convertidos a euros factura a factura con el tipo de Holded. «Con gasto sin factura» es un techo (hay doble conteo).${notaP}` },
    h('div', { class: 'cuerpo' }, tablaDensa({ filas: [...pyg].reverse(), apilable: true, columnas: [
      { clave: 'm', titulo: 'Mes', principal: true, celda: x => mesLargo(x.m) },
      { clave: 'ing', titulo: 'Ingresos', num: true, celda: x => fmt.eur(x.ing) },
      { clave: 'gas', titulo: 'Gastos', num: true, celda: x => fmt.eur(x.gas) },
      { clave: 'mb', titulo: 'Margen bruto', num: true, celda: x => `${fmt.eur(x.mb)} · ${pctS(x.ing ? (100 * x.mb) / x.ing : null)}` },
      { clave: 'bai', titulo: 'Beneficio', num: true, celda: x => chipEstado(colorCifra('beneficio', x.bai), eurS(x.bai)) },
      { clave: 'real', titulo: 'Con gasto sin factura (techo)', num: true, celda: x => eurS(x.real) },
      { clave: 'bai_cierre', titulo: 'Decía el cierre', num: true, celda: x => h('span', { class: 'dim' }, eurS(x.bai_cierre)) },
      { clave: 'plan_res', titulo: 'Plan', num: true, celda: x => eurS(x.plan_res) }] }))));
  const gm = (dir.gastos_por_mes || []).filter(x => x.m >= '2025-10');
  const CATS = ['Equipo', 'Colaboradores', 'Herramientas', 'Publicidad propia', 'Estructura'];
  cont.append(panel({ titulo: 'Gastos por partida, mes a mes', icono: 'capas', sub: 'Último año. Septiembre, provisional (Holded sin cierre de Sofía).' },
    h('div', { class: 'cuerpo' }, barrasMes({ meses: gm.map(x => ({ m: x.m, valores: [x.Equipo + x.Colaboradores, x.Herramientas, (x['Publicidad propia'] || 0) + (x.Estructura || 0) + (x.Eventos || 0)] })),
      nombres: ['Equipo y colaboradores', 'Herramientas', 'Publicidad propia y estructura'], total: 'Gasto total', formato: v => fmt.eur(v) }))));
  const beq = bloqueEquipoMes(d.cuadre); if (beq) cont.append(beq);      // v3: que cada mes tenga su coste del equipo
  const eq = dir.equipo || {};
  const maxA = Math.max(1, ...(eq.areas || []).map(x => x.coste_mes));
  const formCoste = h('div', { class: 'fila', style: { flexWrap: 'wrap', minWidth: '0' } });   // v3: a 1.024 px el formulario bajaba de línea y desbordaba
  const cCoste = campoTexto({ etiqueta: 'Coste total del equipo (€)', tipo: 'number', placeholder: 'Coste del mes' });
  const inp = cCoste.querySelector('input'); inp.min = '0'; inp.step = '100';
  const mesSel = h('select', {}, ['2026-09', '2026-10'].map(m => h('option', { value: m }, mesLargo(m))));
  formCoste.append(h('label', { class: 'campo' }, h('span', { class: 'campo-et' }, 'Mes'), mesSel), cCoste, h('button', { type: 'button', class: 'bt mini pri', 'aria-disabled': ctx.soloLectura ? 'true' : null, on: { click: async () => {
    if (ctx.soloLectura) return avisoFlotante('Estás en «ver como»: solo lectura');
    if (!inp.value) return inp.focus();
    try { await encolar(ctx, { herramienta: 'app', tipo: 'coste_equipo_mes', objeto: mesSel.value, texto: `Coste agregado del equipo de ${mesLargo(mesSel.value)}: ${fmt.eur(Number(inp.value))}`, vista_previa: { mes: mesSel.value, total: Number(inp.value), regla: 'solo total y áreas de 3 o más' } }); avisoFlotante('Coste cargado (simulado)'); inp.value = ''; }
    catch (e) { avisoFlotante('No se pudo: ' + e.message, { icono: 'alert' }); }
  } } }, icono('mas', { clase: 's' }), 'Cargar coste del mes'));
  cont.append(h('div', { class: 'dos' },
    panel({ titulo: 'Equipo por área (agregado)', icono: 'eq', sub: eq.nota },
      h('div', { class: 'cuerpo pila' },
        filasConBarra((eq.areas || []).map(x => ({ etiqueta: `${x.area} · ${x.personas} personas`, valor: fmt.eur(x.coste_mes), actual: x.coste_mes, max: maxA })), { titulos: ['Área', '', 'Coste al mes'] }),
        h('p', { class: 'fila sub' }, h('b', {}, `Total: ${fmt.eur(eq.total_mes)} al mes`), `· presupuesto ${fmt.eur(eq.presupuesto || PRESUPUESTO_EQUIPO)} · ${eq.personas} personas`),
        formCoste)),
    h('div', { class: 'pila' },
      tiles([
        tile({ icono: 'eq', etiqueta: 'Coste del equipo frente a presupuesto', valor: fmt.eur(eq.coste_equipo_cierre), unidad: `de ${fmt.eur(eq.presupuesto)}`,
          estado: eq.coste_equipo_cierre <= 40000 ? 'verde' : eq.coste_equipo_cierre <= 42000 ? 'ambar' : 'rojo', contexto: `${mesLargo(eq.cierre_mes)} · equipo + colaboradores`, medible: 'hoy' }),
        tile({ icono: 'clock', etiqueta: 'Coste real por hora', valor: fmt.num(dir.coste_hora_real, 2), unidad: '€/h', contexto: dir.coste_hora_texto, medible: 'medias', medibleDetalle: 'Horas disponibles, no imputadas: el coste por hora imputada sería casi el doble' }),
        tile({ icono: 'users', etiqueta: 'Ingresos por persona', valor: fmt.eur(dir.kpi?.ing_persona / 12), unidad: 'al mes', contexto: `${dir.kpi?.personas} personas · norte ~2.400 € (jun-27) → 3.300-3.500 € (dic-27)`,
          estado: dir.kpi?.ing_persona / 12 >= 2400 ? 'verde' : 'ambar', medible: 'medias', medibleDetalle: 'Facturación de 12 meses ÷ personas de hoy' }),
      ]),
      ctx.veModulo?.('dinero-cliente') ? h('a', { class: 'bt', href: '#/dinero-cliente', style: { whiteSpace: 'normal' } }, icono('euro'), 'Ver la rentabilidad cliente a cliente') : null)));
  cont.append(bloqueComparacion(dir) || '', bloqueFiabilidad(d.admin.fiabilidad, { tomas: true, dir }) || '');
}

async function pintar(cont, ctx) {
  cont.classList.add('pila');
  const { d, error } = await cargarDatos(ctx, 'finanzas/finanzas');
  if (!d) {
    cont.append(vacio({ icono: 'cartera', titulo: 'Sin datos de finanzas', texto: error || 'Lanza fuentes_dinero/generar_dinero.py y recarga.', quien: 'Agus' }));
    return;
  }
  // Lo de dirección va en su propio fichero (solo puestos de dirección, auditoría 27 M5): a Sofía el servidor le da 403.
  // solo se pide si el puesto lo puede ver (evita un 403 en la consola de Sofía; el servidor sigue siendo quien decide)
  const veDireccion = (ctx.persona?.puestos || []).some(x => x === 'direccion' || x === 'finanzas_direccion');
  const [dd, cuD, cuF, imD] = await Promise.all([
    veDireccion ? cargarDatos(ctx, 'finanzas/direccion') : Promise.resolve({}),
    veDireccion ? cargarDatos(ctx, 'finanzas/cuadre') : Promise.resolve({}),         // v3: solo dirección (beneficio y equipo)
    veDireccion ? Promise.resolve({}) : cargarDatos(ctx, 'finanzas/cuadre_facturacion'),   // v3: Sofía, solo lo facturado
    cargarDatos(ctx, 'finanzas/impagos')]);
  d.direccion = dd?.d?.direccion || [];
  d.cuadre = cuD?.d || cuF?.d || null;
  d.impagos = imD?.d || null;
  const tomas = d.direccion.length > 0;
  if (!d.admin) {
    cont.append(vacio({ icono: 'candado', titulo: 'No es de tu puesto', texto: 'Las finanzas de la empresa las ve Tomás; los cobros, Sofía.' }));
    return;
  }
  const acciones = await accionesCobro(ctx);
  const nImp = d.impagos?.filas?.length || 0;
  const nInc = (d.cuadre?.incongruencias || []).length;
  if (!tomas) {
    ctx.titulo('Finanzas · Mi día administrativo', 'Cobros, impagos, altas en facturación y caja por banco. Sin margen ni coste del equipo.');
    tabs = pestanas({ pestanas: [
      { id: 'dia', texto: 'Mi día administrativo', icono: 'hoy' },
      { id: 'impagos', texto: 'Impagos', icono: 'alert', cuenta: nImp, cuentaEstado: 'rojo' },
      { id: 'cuadre', texto: 'Cuadre de facturación', icono: 'capas', cuenta: nInc, cuentaEstado: 'ambar' },
    ], clave: 'finanzas-sofia', etiqueta: 'Finanzas', pintar: (id, z) => {
      z.classList.add('pila');
      if (id === 'impagos') { pintarImpagos(z, ctx, d.impagos, { acciones }); z.append(pieFuentes(d.impagos || d)); plegarSecundarias(z, { titulos: /^(Por antigüedad|Vencido sin cobrar)/ }); return; }
      if (id === 'cuadre') { pintarCuadre(z, ctx, d.cuadre, { completo: false }); z.append(pieFuentes(d.cuadre || d)); plegarSecundarias(z, { desde: 1 }); return; }
      pintarCobros(z, ctx, d, { objetivo: ctx.params?.[0] === 'cobros' ? ctx.params[1] : null });
      const bp = bloquePeriodo(ctx, d, { tomas: false }); if (bp) z.append(bp);
      z.append(bloqueFiabilidad(d.admin.fiabilidad));
      z.append(pieFuentes(d));
      plegarSecundarias(z, { titulos: PLEGAR_COBROS });   // V2-E (M17): en el móvil, lo que no pide acción va plegado
    } });
    cont.append(tabs);
    if (ctx.params?.[0] === 'cobros') tabs.elegir('dia');
    if (ctx.params?.[0] === 'impagos') tabs.elegir('impagos');
    return;
  }
  ctx.titulo('Finanzas de la empresa', 'Solo tú: beneficio, cuota, caja, historia y equipo agregado. Sin sueldos individuales.');
  const vencidas = (d.admin.impagos?.filas || []).filter(f => f.tramo !== 'Sin vencer').length;
  // eslint-disable-next-line no-use-before-define
  tabs = pestanas({ pestanas: [
    { id: 'resumen', texto: 'Resumen', icono: 'hoy' },
    { id: 'ingresos', texto: 'Ingresos y clientes', icono: 'euro' },
    { id: 'top', texto: 'Los 20 principales', icono: 'crown' },
    { id: 'resultados', texto: 'Resultados y equipo', icono: 'libro' },
    { id: 'impagos', texto: 'Impagos', icono: 'alert', cuenta: nImp, cuentaEstado: 'rojo' },
    { id: 'cobros', texto: 'Cobros y caja', icono: 'cartera', cuenta: vencidas + (d.admin.firmas_sin_alta || []).length, cuentaEstado: 'rojo' },
    { id: 'cuadre', texto: 'Cuadre de fuentes', icono: 'capas', cuenta: nInc, cuentaEstado: 'ambar' },
  ], clave: 'finanzas', etiqueta: 'Finanzas', pintar: (id, z) => {
    z.classList.add('pila');
    ({ resumen: pintarResumen, ingresos: pintarIngresos, top: pintarTop, resultados: pintarResultados,
      impagos: (c, x) => pintarImpagos(c, x, d.impagos, { acciones }),
      cuadre: (c, x) => pintarCuadre(c, x, d.cuadre, { completo: true }),
      cobros: (c, x, dd2) => pintarCobros(c, x, dd2, { tomas: true, objetivo: ctx.params?.[0] === 'cobros' ? ctx.params[1] : null }) })[id](z, ctx, d);
    z.append(pieFuentes(id === 'cuadre' ? d.cuadre || d : id === 'impagos' ? d.impagos || d : d));
    plegarSecundarias(z, id === 'cobros' ? { titulos: PLEGAR_COBROS } : id === 'impagos' ? { titulos: /^(Por antigüedad|Vencido sin cobrar)/ } : { desde: 2 });   // V2-E (M17): plegado común en el móvil
  } });
  cont.append(h('div', { class: 'fila' }, h('a', { class: 'bt pri', href: '#/panel-direccion' }, icono('dir'), 'Ver el panel de dirección completo'),
    h('span', { class: 'sub' }, 'Empresa, captación de RO y clientes del panel de resultados.')), tabs);
  if (ctx.params?.[0] === 'cobros') tabs.elegir('cobros');   // R15a (A2): la ruta manda sobre la pestaña recordada
  if (ctx.params?.[0] === 'impagos' || ctx.params?.[0] === 'cuadre') tabs.elegir(ctx.params[0]);
}
let tabs = { elegir: () => {} };
// V2-E (M17): en Cobros, lo que NO pide acción (impagos, firmados sin alta, devueltos y Meta se quedan abiertos)
const PLEGAR_COBROS = /^(Calendario administrativo|Cuota de octubre|Bajas y cambios|Caja por banco|En el periodo|Fiabilidad)/;

export default {
  id: 'finanzas',
  titulo: 'Finanzas de la empresa',
  grupo: 'Dinero',
  puestos_que_lo_ven: { direccion: 'todo', finanzas_direccion: 'todo', administracion: 'todo' },
  // R12 (A-A2): datos mensuales → mes, mes anterior, trimestre, año y a medida (por meses enteros)
  usa_periodo: ['mes', 'mes_ant', 'trim', 'anio', 'medida'],
  async render(contenedor, ctx) { await pintar(contenedor, ctx); },
};
