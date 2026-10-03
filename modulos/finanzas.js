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

import { plegarSecundarias, grafico, plegadoMovil, tarjetaKpi, selectorComparar, lineaComparacion, cifraPrincipal, minilinea, cascada,
  barrasGanadoPerdido, barraObjetivo, previsionCaja, barraApilada, estadoObjetivo, enlaceFuente } from '../componentes.js';
import { FUENTES, UMBRALES, ESTADO, fuentesAlPie, mesMas, puenteCuota, puntosPrevisionCaja, notaSupuestos, separador } from './dinero_v4.js';
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
  // Paneles v4 (3-oct): las cifras de cobro de Sofía con su línea de 12 meses, su umbral con fuente y «Ver fuente ↗».
  // Sin margen, beneficio ni equipo (su puesto no los ve; el servidor ni se los manda).
  const t = a.cuota_tres || {};
  const imp = a.impagos || {};
  const sinPlan = (imp.filas || []).filter(f => f.tramo !== 'Sin vencer').length;
  const fact = (a.facturado_mes || []).filter(x => !x.curso && typeof x.cobrado_pct === 'number');
  const fx = fact.slice(-12);
  const ev = d.impagos?.evolucion || [];
  const evX = ev.slice(-12);
  const dia10 = Number(String(hoyMadrid()).slice(8, 10)) >= 10;
  const mesT = mesLargo(t.mes).split(' ')[0];
  return [
    tarjetaKpi({ icono: 'euro', etiqueta: `Cuota cobrada · ${mesT}`, valor: t.cobrado_pct === null || t.cobrado_pct === undefined ? null : fmt.pct(t.cobrado_pct), unidad: `${fmt.eur(t.cobrada)} de ${fmt.eur(t.facturada)}`,
      num: t.cobrado_pct, estado: dia10 ? ESTADO.cobrada_dia10(t.cobrado_pct) : 'gris', mejorSi: 'alto',
      serie: fx.map(x => x.cobrado_pct), serieX: fx.map(x => x.m), formatoSerie: v => fmt.pct(v), umbralSerie: 95,
      comparaciones: { mes_ant: { ref: t.cobrado_pct_sep, texto: `frente a septiembre (${fmt.pct(t.cobrado_pct_sep)})`, modo: 'puntos' } },
      contexto: dia10 ? 'Cobrado frente a lo emitido este mes' : 'El color sale el día 10: el cargo SEPA del día 2 tarda en verse en el banco',
      umbral: UMBRALES.cobrada_dia10, fuente: { texto: 'Holded', href: '#/finanzas/cobros' }, medible: 'medias', medibleDetalle: 'El cargo SEPA del día 2 aún no ha entrado; hay movimientos sin conciliar', frescura: fH }),
    tarjetaKpi({ icono: 'alert', etiqueta: 'Recibos vencidos sin plan', valor: sinPlan, unidad: fmt.eur(imp.vencido_total), num: imp.vencido_total, estado: imp.mas_60 ? 'rojo' : sinPlan ? 'ambar' : 'verde', mejorSi: 'bajo',
      serie: evX.map(x => x.vencido), serieX: evX.map(x => x.m), formatoSerie: v => fmt.eur(v),
      comparaciones: { mes_ant: { ref: ev.at(-2)?.vencido, texto: `importe frente al cierre de ${ev.at(-2) ? mesLargo(ev.at(-2).m).split(' ')[0] : 'el mes anterior'}` } },
      contexto: `${imp.mas_30 || 0} con más de 30 días · ${imp.mas_60 || 0} con más de 60`, umbral: UMBRALES.vencido, fuente: { texto: 'Holded', href: '#/finanzas/impagos' }, frescura: fH,
      ir: 'Ver cuáles', alPulsar: () => document.querySelector('[data-bloque=impagos]')?.scrollIntoView({ behavior: 'smooth' }) }),
    tarjetaKpi({ icono: 'doc', etiqueta: 'Firmados sin alta en facturación', valor: (a.firmas_sin_alta || []).length, estado: (a.firmas_sin_alta || []).length ? 'rojo' : 'verde',
      contexto: 'Antes del día 0 del cliente · Zoho Sign y la columna «Cliente» de GHL frente al Airtable de octubre', fuente: { texto: 'Airtable de facturación (solo lectura)' }, frescura: fA,
      ir: 'Ver cuáles', alPulsar: () => document.querySelector('[data-bloque=firmas]')?.scrollIntoView({ behavior: 'smooth' }) }),
    tarjetaKpi({ icono: 'alert', etiqueta: 'Recibos devueltos', valor: (a.devueltos || []).length, estado: (a.devueltos || []).length ? 'rojo' : 'verde', contexto: 'SEPA o tarjeta devueltos',
      fuente: { texto: 'Holded' }, medible: 'medias', medibleDetalle: 'Holded ve el cobro, no siempre el motivo de la devolución', frescura: fH }),
    tarjetaKpi({ icono: 'clock', etiqueta: 'Días de cobro', valor: a.dias_cobro?.valor ?? null, unidad: 'días', num: a.dias_cobro?.valor, estado: ESTADO.dias_cobro(a.dias_cobro?.valor), mejorSi: 'bajo',
      contexto: a.dias_cobro?.texto, umbral: { ...UMBRALES.dias_cobro, texto: 'verde ≤ 60 días (máximo legal entre empresas) · media real en España: 67 días (2025) · sin dato de agencias' }, fuente: { texto: 'Holded' } }),
    tarjetaKpi({ icono: 'users', etiqueta: 'Cliente que más pesa', valor: pctS(a.concentracion?.uno, 1), unidad: 'de la cuota', num: a.concentracion?.uno, estado: ESTADO.concentracion(a.concentracion?.uno), mejorSi: 'bajo',
      contexto: `Los 5 mayores: ${pctS(a.concentracion?.cinco, 1)} · los 10 mayores: ${pctS(a.concentracion?.diez, 1)} (sin umbral fiable: no colorean)`, umbral: UMBRALES.concentracion, fuente: { texto: 'Airtable de octubre' } }),
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
      h('div', { class: 'cuerpo pila' },
        barraApilada({ etiqueta: 'Vencido por antigüedad', formato: v => fmt.eur(v), partes: (imp.tramos || []).map(t => ({ valor: t.importe, texto: t.tramo,
          estado: /^0-30/.test(t.tramo) ? 'gris' : /31-60/.test(t.tramo) ? 'ambar' : /61-90/.test(t.tramo) ? 'rojo-claro' : 'rojo' })) }),
        h('p', { class: 'kpi-pie' }, h('span', {}, 'Tramos como los de QuickBooks: '), enlaceFuente(FUENTES.quickbooks_tramos.href, FUENTES.quickbooks_tramos.fuente)),
        filasConBarra((imp.tramos || []).map(t => ({ etiqueta: `${t.tramo} · ${fmt.plural ? fmt.plural(t.n, 'factura') : `${t.n} facturas`}`, valor: fmt.eur(t.importe), actual: t.importe, max: maxT,
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

// ===================================================================== Tomás · Resumen (paneles v4, 3-oct)
// 48 §4.2 «¿cuánto gano, cuánto cobro y cuánto aguanto?»: arriba la cifra que manda (beneficio del último mes cerrado) con
// «Comparar con» (mes anterior · mismo mes de 2025 · plan); al lado, la cuota contra el plan y el objetivo de diciembre; debajo
// seis tarjetas con su línea de 12 meses, su umbral y su fuente; lo que pide tu decisión; y el porqué: cascada del beneficio
// (real y frente al plan), puente de la cuota con las rebajas a la vista, caja a 90 días con el mínimo de 2 meses, cobros por
// antigüedad y peso del equipo. Las cifras son las fijadas (beneficio ene-ago 93.492 €, agosto 3.859,87 €…): no se recalculan.
const planDe = t => { const m = /([\d.]+)\s*→\s*([\d.]+)\s*→\s*([\d.]+)/.exec(t || ''); return m ? m.slice(1, 4).map(x => Number(x.replace(/\./g, ''))) : []; };
const fmtMeses = v => `${fmt.num(v, 1)} meses`;

function pintarResumen(cont, ctx, d) {
  const dir = d.direccion[0], a = d.admin, cu = d.cuadre || {};
  const n = dir.numero || {}, cr = dir.cuota_recurrente || {}, cj = dir.caja || {}, eq = dir.equipo || {}, kpi = dir.kpi || {};
  const imp = d.impagos?.resumen || {};
  const B = cu.beneficio?.meses || [];
  const porMes = new Map(B.map(x => [x.m, x]));
  const ultM = n.mes || B.filter(x => !x.estimado).at(-1)?.m || '2026-08';
  const prevM = mesMas(ultM, -1), anioM = mesMas(ultM, -12);
  const m12 = Array.from({ length: 12 }, (_, i) => mesMas(ultM, i - 11));
  const pyg = dir.pyg || [];
  const pygDe = new Map(pyg.map(x => [x.m, x]));
  const pygU = pygDe.get(ultM) || {};
  const mb3 = m => { const w = [mesMas(m, -2), mesMas(m, -1), m].map(x => pygDe.get(x)).filter(Boolean); return w.length === 3 ? (100 * w.reduce((s, x) => s + x.mb, 0)) / w.reduce((s, x) => s + x.ing, 0) : null; };
  const eqDe = new Map((cu.equipo_mes || []).map(x => [x.m, x]));
  const pesoDe = m => { const e = eqDe.get(m), b = porMes.get(m); return e && b?.ing && !b.estimado && e.estado !== 'provisional' ? (100 * e.usado) / b.ing : null; };
  const [planOct, planNov] = planDe(cr.plan_texto);
  const serieCuota = cr.serie || [];
  const cuotaDe = new Map(serieCuota.map(x => [x.m, x.cuota]));
  const mCuota = serieCuota.at(-1)?.m || '2026-10';
  const evol = d.impagos?.evolucion || [];
  const evolDe = new Map(evol.map(x => [x.m, x.vencido]));
  const mImp = evol.at(-1)?.m || mCuota;

  // ---------------------------------------------------------- 1 · cifra que manda + cuota hacia el objetivo
  const comp = selectorComparar({ clave: 'finanzas-comparar', alCambiar: v => pintarCifras(v) });
  const zonaCifras = h('div', { class: 'pila' });
  const cifraQueManda = c => {
    const ref = c === 'mes_ant' ? { ref: porMes.get(prevM)?.bai, texto: `frente a ${nomMes(prevM)}` }
      : c === 'anio_ant' ? { ref: porMes.get(anioM)?.bai, texto: `frente a ${mesLargo(anioM)} (estimado: a 2025 le falta la nómina de España)` }
        : { ref: n.plan_res, texto: `frente al plan del mes (${eurS(n.plan_res)})` };
    return panel({ titulo: `Beneficio de ${nomMes(ultM)} · la cifra que manda`, icono: 'grafico', sub: 'Último mes cerrado por Sofía, con los gastos convertidos a euros factura a factura. El mismo número que Mi día y el Panel de dirección.' },
      h('div', { class: 'cuerpo pila' },
        cifraPrincipal({ etiqueta: `Margen ${pctS(n.margen_pct, 1)} sobre ${fmt.eur(n.ingresos)} de ingresos`, valor: eur2(n.beneficio), estado: colorCifra('beneficio', n.beneficio),
          comparacion: lineaComparacion({ num: n.beneficio, ...ref, modo: 'abs', formato: v => fmt.eur(v), mejorSi: 'alto' }) || h('span', { class: 'tc' }, h('em', {}, 'sin dato para comparar')) }),
        h('p', { class: 'cifra-gris' }, `Con el gasto sin factura: ${eur2(n.beneficio_real)} (techo: puede contar dos veces). Enero-agosto: ${eurS(dir.anio?.bai)} · ${eurS(dir.anio?.real)} con el gasto sin factura.`),
        minilinea(m12.map(m => porMes.get(m)?.bai ?? null), { x: m12, formato: v => eurS(v), etiqueta: 'Beneficio de los 12 últimos meses (2025, estimado)', alto: 40 }),
        h('p', { class: 'kpi-pie' }, h('span', {}, `Norte: ${n.objetivo_texto || '30.000 € de beneficio al mes a final de 2027'}`), h('span', {}, 'Dato: ', enlaceFuente('#/finanzas/cuadre', 'cierre de Sofía y Holded')))));
  };
  const zonaCuota = h('div', { class: 'pila' });
  const pintarCuota = esc => {
    const v = esc === 'firman' ? cr.si_firman_mes : cr.cuota_mes;
    zonaCuota.replaceChildren(
      h('p', { class: 'fila' }, h('b', {}, `${fmt.eur(v)} al mes`), h('span', { class: 'sub' }, `${fmt.pct((100 * v) / (planOct || 1))} del plan de ${nomMes(mCuota)} · ${fmt.pct((100 * v) / cr.objetivo_dic)} del objetivo de diciembre`)),
      barraObjetivo({ etiqueta: `Cuota de ${nomMes(mCuota)}`, valor: v, objetivo: planOct || cr.objetivo_dic, max: Math.max(cr.objetivo_dic, planNov || 0) * 1.04, formato: v2 => fmt.eur(v2),
        etiquetaValor: esc === 'firman' ? 'Si firman' : 'Hoy', etiquetaObjetivo: `Plan de ${nomMes(mCuota)}`,
        extra: esc === 'firman' ? [{ valor: cr.cuota_mes, texto: 'Hoy' }] : [{ valor: cr.si_firman_mes, texto: `Si firman los ${(cr.pendientes || []).length}` }],
        marcas: [planNov ? { valor: planNov, texto: 'Plan de noviembre' } : null, { valor: cr.objetivo_dic, texto: 'Objetivo de diciembre' }].filter(Boolean) }),
      h('p', { class: 'kpi-umbral' }, h('span', {}, `Umbral: ${UMBRALES.cuota_objetivo.texto}`), ' · ', enlaceFuente(FUENTES.databox.href, FUENTES.databox.fuente)),
      ctx.veModulo?.('ventas-ro') && (cr.pendientes || []).length ? h('div', { class: 'fila' }, h('a', { class: 'bt mini', href: '#/ventas-ro' }, icono('rocket', { clase: 's' }), `Ver los ${cr.pendientes.length} contratos pendientes`)) : null,
      h('details', { class: 'que-es' }, h('summary', {}, 'Ver la cuota línea a línea'),
        h('dl', { class: 'dl' }, [...(cr.desglose || []).filter(x => x.tipo !== 'info').map(x => [x.concepto, x.tipo === 'total' ? fmt.eur(x.importe) : `${x.importe < 0 ? '−' : '+'}${fmt.eur(Math.abs(x.importe))}`]),
          ...(cr.pendientes || []).map(p => [`${p.nombre_m} · contrato enviado hace ${p.dias} días${p.abierta ? ' · abierto' : ''} (si firma)`, `+${fmt.eur(p.cuota)}`])].map(([tx, vv]) => [h('dt', {}, tx), h('dd', {}, h('b', {}, vv))]))));
  };
  const escCuota = chipsFiltro({ opciones: [{ valor: 'hoy', texto: 'Hoy', icono: 'ok' }, { valor: 'firman', texto: `Si firman los ${(cr.pendientes || []).length} pendientes`, icono: 'rocket', cuenta: (cr.pendientes || []).length }],
    clave: 'finanzas-escenario', etiqueta: 'Escenario', alCambiar: pintarCuota });
  pintarCuota(escCuota.valor());
  const panelCuota = panel({ titulo: 'Cuota hacia el objetivo de diciembre', icono: 'sube', sub: cr.plan_texto }, h('div', { class: 'cuerpo pila' }, escCuota, zonaCuota));

  // ---------------------------------------------------------- 2 · seis tarjetas
  const tarjetas = c => {
    const mbU = mb3(ultM), mbP = mb3(prevM);
    const pesoU = eq.peso_ingresos ?? pesoDe(ultM), pesoP = pesoDe(prevM);
    const nrrS = kpi.nrr_serie || [];
    const mNrr = Array.from({ length: nrrS.length }, (_, i) => mesMas(mCuota === '2026-10' ? '2026-09' : mCuota, i - nrrS.length + 1));
    const mesesImp = Array.from({ length: 12 }, (_, i) => mesMas(mImp, i - 11));
    const mesesCuo = Array.from({ length: 12 }, (_, i) => mesMas(mCuota, i - 11));
    return h('div', { class: 'tiles' },
      tarjetaKpi({ icono: 'sube', etiqueta: 'Margen bruto · media de 3 meses', valor: pctS(mbU, 1), num: mbU, estado: ESTADO.margen_bruto(mbU), mejorSi: 'alto', comparar: c,
        serie: m12.map(mb3), serieX: m12, formatoSerie: v => pctS(v, 1), umbralSerie: 35,
        comparaciones: { mes_ant: { ref: mbP, texto: `frente a la media hasta ${nomMes(prevM)}`, modo: 'puntos' }, anio_ant: { sinDato: '2025 no tiene el coste de entrega fiable' }, objetivo: { ref: 35, texto: 'frente al 35 % de la regla', modo: 'puntos' } },
        contexto: `Ingresos menos el equipo de entrega · ${nomMes(ultM)} solo: ${pctS(pygU.ing ? (100 * pygU.mb) / pygU.ing : null, 1)} · enero-agosto: ${pctS(kpi.mb, 1)}`,
        umbral: UMBRALES.margen_bruto, fuente: { texto: 'cierre de Sofía', href: '#/finanzas/cuadre' }, alPulsar: () => tabs.elegir('resultados'), ir: 'Ver resultados' }),
      tarjetaKpi({ icono: 'escudo', etiqueta: 'Meses de caja', valor: fmt.num(cj.meses, 1), unidad: 'meses', num: cj.meses, estado: ESTADO.meses_caja(cj.meses), mejorSi: 'alto', comparar: c,
        comparaciones: { mes_ant: { ref: cj.meses_31ago, texto: 'frente al 31-ago', modo: 'abs', formato: fmtMeses }, anio_ant: { sinDato: 'Sin saldo de bancos de hace un año en la app' }, objetivo: { ref: 2, texto: 'frente al mínimo de 2 meses', modo: 'abs', formato: fmtMeses } },
        contexto: `Caja de hoy ${fmt.eur(cj.total)} ÷ gasto medio ${fmt.eur(cj.gasto_medio)} al mes, si no entrara nada · el flujo del año es +${fmt.eur(cj.flujo_neto_anio)}`,
        umbral: UMBRALES.meses_caja, fuente: { texto: 'Holded en vivo', href: '#/finanzas/cobros' }, frescura: fresco(d, 'Holded'), alPulsar: () => document.querySelector('[data-bloque=prevision]')?.scrollIntoView({ behavior: 'smooth' }), ir: 'Ver la caja a 90 días' }),
      tarjetaKpi({ icono: 'alert', etiqueta: 'Vencido sin cobrar', valor: fmt.eur(imp.vencido ?? a.impagos?.vencido_total), unidad: `${imp.facturas ?? a.impagos?.vencido_n} facturas`, num: imp.vencido ?? a.impagos?.vencido_total,
        estado: (imp.mas_60 ?? a.impagos?.mas_60) ? 'rojo' : (imp.vencido ?? a.impagos?.vencido_total) ? 'ambar' : 'verde', mejorSi: 'bajo', comparar: c,
        serie: mesesImp.map(m => evolDe.get(m) ?? null), serieX: mesesImp, formatoSerie: v => fmt.eur(v),
        comparaciones: { mes_ant: { ref: evolDe.get(mesMas(mImp, -1)), texto: `frente al cierre de ${nomMes(mesMas(mImp, -1))}` }, anio_ant: { ref: evolDe.get(mesMas(mImp, -12)), texto: `frente a ${mesLargo(mesMas(mImp, -12))}` }, objetivo: { sinDato: 'Sin objetivo de vencido: manda la regla de 30 y 60 días' } },
        contexto: `${imp.mas_60 ?? a.impagos?.mas_60} con más de 60 días (te toca decidir) · días de cobro: ${a.dias_cobro?.valor ?? '—'} con el SEPA`,
        umbral: UMBRALES.vencido, fuente: { texto: 'Holded en vivo', href: '#/finanzas/impagos' }, alPulsar: () => tabs.elegir('impagos'), ir: 'Ver los impagos' }),
      tarjetaKpi({ icono: 'euro', etiqueta: 'Cuota recurrente firmada', valor: fmt.eur(cr.actual), unidad: 'al mes', num: cr.actual, estado: planOct ? estadoObjetivo(cr.cuota_mes, planOct) : '', mejorSi: 'alto', comparar: c,
        serie: mesesCuo.map(m => cuotaDe.get(m) ?? null), serieX: mesesCuo, formatoSerie: v => fmt.eur(v),
        comparaciones: { mes_ant: { num: cuotaDe.get(mCuota), ref: cuotaDe.get(mesMas(mCuota, -1)), texto: `cuota facturada: ${nomMes(mCuota)} frente a ${nomMes(mesMas(mCuota, -1))}` },
          anio_ant: { num: cuotaDe.get(mCuota), ref: cuotaDe.get(mesMas(mCuota, -12)), texto: `cuota facturada: frente a ${mesLargo(mesMas(mCuota, -12))}` },
          objetivo: { num: cr.cuota_mes, ref: planOct, texto: `cuota de ${nomMes(mCuota)} (${fmt.eur(cr.cuota_mes)}) frente al plan (${fmt.eur(planOct)})` } },
        contexto: `Cuota de ${nomMes(mCuota)} ${fmt.eur(cr.cuota_mes)} con proyectos · facturable ${fmt.eur(cr.facturable)} · ${cr.clientes} clientes · línea: cuota facturada de cada mes`,
        umbral: UMBRALES.cuota_objetivo, fuente: { texto: 'Airtable de Sofía y Holded', href: '#/finanzas/cobros' } }),
      tarjetaKpi({ icono: 'eq', etiqueta: 'Peso del equipo sobre ingresos', valor: pctS(pesoU, 1), num: pesoU, estado: ESTADO.peso_equipo(pesoU), mejorSi: 'bajo', comparar: c,
        serie: m12.map(m => (m >= '2026-01' ? pesoDe(m) : null)), serieX: m12, formatoSerie: v => pctS(v, 1), umbralSerie: 55,
        comparaciones: { mes_ant: { ref: pesoP, texto: `frente a ${nomMes(prevM)}`, modo: 'puntos' }, anio_ant: { sinDato: '2025: el equipo va repartido por ingresos, no es comparable' }, objetivo: { ref: 55, texto: 'frente al 55 %', modo: 'puntos' } },
        contexto: `${nomMes(ultM)}: ${fmt.eur(eq.coste_equipo_cierre)} de equipo y colaboradores · año: ${pctS(kpi.peso_equipo_anio, 1)} (${fmt.num(100 / (kpi.peso_equipo_anio || 100), 2)} € de ingresos por euro de equipo) · nunca sueldos de una persona`,
        umbral: UMBRALES.peso_equipo, fuente: { texto: 'cierre de Sofía, solo totales', href: '#/finanzas/cuadre' } }),
      tarjetaKpi({ icono: 'baja', etiqueta: 'Retención neta de la cuota', valor: pctS(kpi.nrr, 1), num: kpi.nrr, estado: ESTADO.retencion_neta(kpi.nrr), mejorSi: 'alto', comparar: c,
        serie: nrrS, serieX: mNrr, formatoSerie: v => pctS(v, 1), umbralSerie: 90,
        comparaciones: { mes_ant: { ref: nrrS.at(-2), texto: 'frente al trimestre anterior (un mes antes)', modo: 'puntos' }, anio_ant: { sinDato: 'Sin la serie de hace un año' }, objetivo: { ref: 90, texto: 'frente al 90 % de RO', modo: 'puntos' } },
        contexto: 'Cuota de hoy de los clientes que ya estaban hace 12 meses ÷ su cuota de entonces (por trimestres, para que no la deformen los desfases de facturación). Sin clientes nuevos.',
        nota: 'Fórmula pendiente de confirmar por Tomás (Sofía calculaba 74-80 %).', medible: 'medias', medibleDetalle: 'Fórmula pendiente de confirmar por Tomás',
        umbral: UMBRALES.retencion_neta, fuente: { texto: 'facturas de Holded, cliente a cliente' } }));
  };
  const pintarCifras = c => zonaCifras.replaceChildren(h('div', { class: 'dos iguales' }, cifraQueManda(c), panelCuota), tarjetas(c));
  cont.append(h('div', { class: 'fila' }, comp), zonaCifras);
  pintarCifras(comp.valor());

  // ---------------------------------------------------------- 3 · lo que pide tu decisión (nunca se pliega)
  const mesesCaja = cj.meses;
  const incN = (d.cuadre?.incongruencias || []).filter(i => i.gravedad === 'alta').length;
  cont.append(panel({ titulo: 'Lo que pide tu decisión', icono: 'flag', sub: 'Del dinero, lo que no se arregla solo' },
    listaLoPrimero([
      a.impagos?.mas_60 ? { estado: 'rojo', icono: 'alert', motivo: `${a.impagos.mas_60} recibo${a.impagos.mas_60 === 1 ? '' : 's'} con más de 60 días`, detalle: 'A 60 días decides tú: cortar, plan de pago o darlo por perdido.', botones: [h('button', { type: 'button', class: 'bt mini', on: { click: () => tabs.elegir('impagos') } }, 'Ver los impagos')] } : null,
      (a.firmas_sin_alta || []).length ? { estado: 'rojo', icono: 'doc', motivo: `${a.firmas_sin_alta.length} firmados sin línea en facturación`, detalle: a.firmas_sin_alta.map(x => x.nombre).join(', ') + ': no entran en la cuota que factura Sofía.' } : null,
      mesesCaja < 2 ? { estado: mesesCaja < 1 ? 'rojo' : 'ambar', icono: 'escudo', motivo: `Caja para ${fmt.num(mesesCaja, 1)} meses si no entrara nada`, detalle: 'Referencia de agencias: mínimo 2 meses de gasto fijo (3-4 si hay concentración). El flujo del año es positivo, pero conviene fijar tu colchón.' } : null,
      (n.beneficio_real ?? 0) < 0 && n.beneficio >= 0 ? { estado: 'ambar', icono: 'doc', motivo: `${nomMes(n.mes)}: ${eurS(n.beneficio)} según facturas, ${eurS(n.beneficio_real)} con el gasto sin factura`, detalle: `Hay ${fmt.eur(n.sin_factura)} de cargos sin factura (techo). Que Sofía los cierre con la conciliación de Holded.` } : null,
      n.beneficio < 0 ? { estado: 'rojo', icono: 'grafico', motivo: `${nomMes(n.mes)} en pérdidas: ${eurS(n.beneficio)}`, detalle: `Real ${eurS(n.beneficio_real)} con ${fmt.eur(n.sin_factura)} de gasto sin factura.` } : null,
      eq.peso_ingresos > 65 ? { estado: 'rojo', icono: 'eq', motivo: `El equipo pesa el ${pctS(eq.peso_ingresos, 0)} de los ingresos`, detalle: 'Referencia de agencias: 55 %. Más altas con el mismo equipo o revisar las rebajas de cuota (la mayor fuga, abajo).' } : null,
      kpi.nrr ? { estado: 'ambar', icono: 'baja', motivo: 'Fijar la fórmula de la retención neta', detalle: `Propuesta: cuota de hoy de los clientes de hace 12 meses ÷ su cuota de entonces (hoy ${pctS(kpi.nrr, 1)}). Sofía la calculaba en 74-80 %: una sola fórmula antes de colorearla en todas las pantallas.` } : null,
      incN ? { estado: 'rojo', icono: 'capas', motivo: `${incN} ${incN === 1 ? 'cifra que no cuadra' : 'cifras que no cuadran'} entre Holded, el cierre y Airtable`, detalle: 'Con la propuesta de cuál vale y por qué.', botones: [h('button', { type: 'button', class: 'bt mini', on: { click: () => tabs.elegir('cuadre') } }, 'Ver el cuadre')] } : null,
    ].filter(Boolean).slice(0, 7))));

  // ---------------------------------------------------------- 4 · el porqué
  cont.append(separador('El porqué de las cifras'));
  const plan = { ing: pygU.plan_ing, gas: pygU.plan_gas, res: pygU.plan_res ?? n.plan_res };
  const difIng = (pygU.ing ?? 0) - (plan.ing ?? 0), difGas = (plan.gas ?? 0) - (pygU.gas ?? 0);
  cont.append(h('div', { class: 'dos iguales' },
    panel({ titulo: `Cuenta de ${nomMes(ultM)} en cascada`, icono: 'capas', sub: 'Ingresos − equipo de entrega = margen bruto − resto de gastos = beneficio' },
      h('div', { class: 'cuerpo pila' }, cascada({ formato: v => fmt.eur(v), pasos: [
        { texto: 'Ingresos', valor: pygU.ing, tipo: 'total' }, { texto: 'Equipo de entrega', valor: -(pygU.entrega || 0) },
        { texto: 'Margen bruto', valor: pygU.mb, tipo: 'total' }, { texto: 'Resto de gastos', valor: -(pygU.estructura || 0) },
        { texto: 'Beneficio', valor: pygU.bai, tipo: 'total' }] }),
        h('p', { class: 'kpi-pie' }, h('span', {}, 'Cómo se dibuja: '), enlaceFuente(FUENTES.pigment.href, FUENTES.pigment.fuente), h('span', {}, 'Dato: '), enlaceFuente('#/finanzas/cuadre', 'cierre de Sofía')))),
    panel({ titulo: `Del plan al real · ${nomMes(ultM)}`, icono: 'flag', sub: 'Verde: lo que salió mejor que el plan; rojo: lo que salió peor' },
      h('div', { class: 'cuerpo pila' }, cascada({ formato: v => fmt.eur(v), pasos: [
        { texto: 'Plan del mes', valor: plan.res, tipo: 'total' },
        { texto: difIng >= 0 ? 'Más ingresos' : 'Menos ingresos', valor: difIng },
        { texto: difGas >= 0 ? 'Menos gasto' : 'Más gasto', valor: difGas },
        { texto: 'Real', valor: pygU.bai, tipo: 'total' }] }),
        h('p', { class: 'sub' }, `Plan: ${fmt.eur(plan.ing)} de ingresos y ${fmt.eur(plan.gas)} de gasto · real: ${fmt.eur(pygU.ing)} y ${fmt.eur(pygU.gas)}.`)))));

  cont.append(bloquePuente(dir, ctx));

  const prev = puntosPrevisionCaja({ caja: cj.total, fecha: String(a.caja?.fecha || ctx.hoy || '').slice(0, 10), gastoMedio: cj.gasto_medio,
    cobroPendiente: Math.max(0, (a.cuota_tres?.facturada || 0) - (a.cuota_tres?.cobrada || 0)), cuotaMes: cr.actual, tasaCobro: (a.cuota_tres?.cobrado_pct_sep ?? 100) / 100 });
  const minimo = 2 * (cj.gasto_medio || 0);
  const bajo = prev.puntos.filter(p => p.saldo < minimo).length;
  const panelCaja = panel({ titulo: 'Caja a 90 días', icono: 'cartera', sub: `Estimación con el mínimo de 2 meses de gasto (${fmt.eur(minimo)}): ${bajo} de ${prev.puntos.length} días por debajo` },
    h('div', { class: 'cuerpo pila' },
      previsionCaja({ puntos: prev.puntos, minimo, eventos: prev.eventos, formato: v => fmt.eur(v), textoMinimo: `Mínimo: 2 meses de gasto (${fmt.eur(minimo)})` }),
      h('p', { class: 'kpi-umbral' }, h('span', {}, `Umbral: ${UMBRALES.meses_caja.texto}`), ...UMBRALES.meses_caja.fuentes.map(f => [' · ', enlaceFuente(f.href, f.fuente)]),
        ' · Cómo se dibuja: ', enlaceFuente(FUENTES.quickbooks_caja.href, FUENTES.quickbooks_caja.fuente)),
      h('div', { class: 'fila' },
        h('button', { type: 'button', class: 'bt mini', on: { click: () => tabs.elegir('cobros') } }, icono('cartera', { clase: 's' }), 'Ver cobros pendientes'),
        h('button', { type: 'button', class: 'bt mini', on: { click: () => tabs.elegir('impagos') } }, icono('alert', { clase: 's' }), 'Reclamar lo vencido')),
      notaSupuestos(prev.supuestos)));
  panelCaja.dataset.bloque = 'prevision';
  cont.append(panelCaja);

  const tramos = d.impagos?.tramos || (a.impagos?.tramos || []).filter(t => t.tramo !== 'Sin vencer');
  const estT = t => (/^0-30/.test(t) ? 'gris' : /31-60/.test(t) ? 'ambar' : /61-90/.test(t) ? 'rojo-claro' : 'rojo');
  const t3 = a.cuota_tres || {};
  const pesoX = (cu.equipo_mes || []).map(x => x.m).filter(m => porMes.get(m));
  cont.append(h('div', { class: 'dos iguales' },
    panel({ titulo: 'Cobros por antigüedad', icono: 'alert', sub: 'Lo vencido sin cobrar, por días de retraso (0-30 gris, 31-60 ámbar, 61-90 rojo claro, más de 90 rojo)' },
      h('div', { class: 'cuerpo pila' },
        barraApilada({ etiqueta: 'Vencido por antigüedad', formato: v => fmt.eur(v), partes: tramos.map(t => ({ valor: t.importe, texto: `${t.tramo} · ${fmt.plural(t.n, 'factura')}`, estado: estT(t.tramo) })) }),
        h('p', { class: 'sub' }, `Cuota cobrada en ${nomMes(mesMas(t3.mes || mCuota, -1))}: ${fmt.pct(t3.cobrado_pct_sep)} el día 10 (verde ≥ 95 %, rojo < 85 %, regla de RO). La de ${nomMes(t3.mes || mCuota)} entra con el cargo SEPA del día 2.`),
        h('p', { class: 'kpi-pie' }, h('span', {}, 'Cómo se dibuja: '), enlaceFuente(FUENTES.quickbooks_tramos.href, FUENTES.quickbooks_tramos.fuente),
          h('button', { type: 'button', class: 'bt mini', on: { click: () => tabs.elegir('impagos') } }, icono('alert', { clase: 's' }), 'Reclamar en Impagos')))),
    panel({ titulo: 'Peso del equipo, mes a mes', icono: 'eq', sub: 'Coste del equipo y colaboradores ÷ ingresos · 2025 en gris (estimado) · línea roja: 55 %' },
      h('div', { class: 'cuerpo pila' },
        grafico({ x: pesoX, formatoX: ejeMes, alto: 200, formato: v => pctS(v, 0), etiquetaUltimo: false, umbral: { y: 55, texto: '55 %' },
          barras: { nombre: 'Peso del equipo', y: pesoX.map(m => { const e = eqDe.get(m), b = porMes.get(m); return e && b?.ing ? Math.round((1000 * e.usado) / b.ing) / 10 : null; }), formato: v => pctS(v, 1),
            clase: (i, v) => (porMes.get(pesoX[i])?.estimado || eqDe.get(pesoX[i])?.estado === 'provisional' ? 'est' : v > 65 ? 'neg' : v > 55 ? 'amb' : 'pos'),
            leyenda: [{ nombre: '≤ 55 %', clase: 'pos' }, { nombre: '55-65 %', clase: 'amb' }, { nombre: '> 65 %', clase: 'neg' }, { nombre: 'Estimado o sin cerrar', clase: 'est' }] } }),
        h('p', { class: 'kpi-umbral' }, h('span', {}, `Umbral: ${UMBRALES.peso_equipo.texto}`), ' · ', enlaceFuente(FUENTES.ami_personal.href, FUENTES.ami_personal.fuente)),
        h('div', { class: 'fila' }, h('button', { type: 'button', class: 'bt mini', on: { click: () => tabs.elegir('resultados') } }, icono('eq', { clase: 's' }), 'Ver el coste del equipo por área'))))));

  const bb = bloqueBeneficio(ctx, d.cuadre); if (bb) cont.append(bb);
  const bp = bloquePeriodo(ctx, d, { tomas: true }); if (bp) cont.append(bp);
  cont.append(fuentesAlPie(['baker', 'ami', 'ami_personal', 'parakeeto', 'scoro', 'promethean', 'saascapital', 'chartmogul_ret', 'sakas_rot', 'databox', 'pmcm', 'quickbooks_caja', 'quickbooks_tramos', 'chartmogul_mov', 'pigment', 'baremetrics']));
}

/** «Pedir a Mili que revise las rebajas»: acción interna a la cola (simulada), sin «¿Seguro?»: se hace y se puede deshacer
 *  (patrón «Hecho · Deshacer»; cuando exista modulos/_deshacer.js del carril U1, este botón pasa a usarlo). */
function pedirRevisionRebajas(ctx, S) {
  const caja = h('span', { class: 'fila' });
  const pintar = hecho => caja.replaceChildren(hecho
    ? h('span', { class: 'estado', role: 'status' }, icono('ok', { clase: 's' }), ' Pedido a Mili (simulado) · ', h('button', { type: 'button', class: 'bt mini', on: { click: async () => {
      try { await encolar(ctx, { herramienta: 'app', tipo: 'revisar_rebajas_deshecho', objeto: 'rebajas_cuota', texto: 'Deshecho: revisar las rebajas de cuota' }); } catch { /* ver como */ } pintar(false); } } }, 'Deshacer'))
    : h('button', { type: 'button', class: 'bt mini', 'aria-disabled': ctx.soloLectura ? 'true' : null, title: ctx.soloLectura ? 'Estás en «ver como»: solo lectura' : null, on: { click: async () => {
      if (ctx.soloLectura) return avisoFlotante('Estás en «ver como»: solo lectura');
      try { await encolar(ctx, { herramienta: 'app', tipo: 'revisar_rebajas', objeto: 'rebajas_cuota', texto: `Revisar con los accounts las rebajas de cuota: ${pctS(S.rebajas_pct, 1)} al mes, −${fmt.eur(S.rebajas_12)} en 12 meses. ¿Reales o ruido?`, vista_previa: { para: 'Mili', aviso: 'en su Mi día' } }); pintar(true); }
      catch (e) { avisoFlotante('No se pudo: ' + e.message, { icono: 'alert' }); } } } }, icono('users', { clase: 's' }), 'Pedir a Mili que lo revise con los accounts'));
  pintar(false);
  return caja;
}

/** Puente de la cuota (48 §4.1-4.2): cascada del mes elegido (últimos 6), movimientos de 12 meses con el mes en curso rayado y
 *  la fuga a la vista (las rebajas pesan más que las bajas). Mismo puente que la tabla de «Ingresos y clientes» (cuadra al euro). */
function bloquePuente(dir, ctx) {
  const P = dir.puente || [];
  if (P.length < 2) return '';
  const ab = dir.altas_bajas || [];
  const kpi = dir.kpi || {};
  const ult6 = P.slice(-6);
  const zona = h('div', { class: 'pila' });
  const pintarMes = m => {
    const x = P.find(z => z.m === m) || P.at(-1);
    zona.replaceChildren(cascada({ zoom: true, formato: v => fmt.eur(v), titulo: `${mesLargo(x.m)} · ${x.cuadra ? 'cuadra al euro' : 'no cuadra'}`, pasos: [
      { texto: `Cuota de ${nomMes(mesMas(x.m, -1))}`, valor: x.ini, tipo: 'total' }, { texto: 'Altas', valor: x.altas || 0 }, { texto: 'Subidas', valor: x.subidas || 0, estado: 'sube2' },
      { texto: 'Rebajas', valor: x.bajadas || 0, estado: 'ambar' }, { texto: 'Bajas', valor: x.bajas || 0 }, { texto: `Cuota de ${nomMes(x.m)}`, valor: x.fin, tipo: 'total' }] }),
    h('p', { class: 'sub' }, [(x.qa || []).length ? `Altas: ${x.qa.slice(0, 4).map(q => q[0]).join(', ')}${x.qa.length > 4 ? ` y ${x.qa.length - 4} más` : ''}.` : '', (x.qb || []).length ? ` Bajas: ${x.qb.map(q => q[0]).join(', ')}.` : ''].join('')));
  };
  const chips = chipsFiltro({ opciones: ult6.map(x => ({ valor: x.m, texto: nomMes(x.m) })), valor: P.at(-1).m, clave: 'finanzas-puente-mes', etiqueta: 'Mes', alCambiar: pintarMes });
  pintarMes(chips.valor());
  const d12 = P.slice(-12);
  const curso = ab.find(z => z.curso && z.m > P.at(-1).m);
  const x = [...d12.map(z => z.m), ...(curso ? [curso.m] : [])];
  const S = puenteCuota(P, 6);
  const sakas = (kpi.churn_n ?? 0) <= 1.8 ? 'verde' : 'rojo';
  return panel({ titulo: 'De dónde sale el cambio de la cuota', icono: 'capas', sub: 'Cuota del mes anterior + altas + subidas − rebajas − bajas = cuota del mes. Las rebajas, en ámbar: hoy son la mayor fuga.' },
    h('div', { class: 'cuerpo pila' },
      chips, zona,
      h('div', { class: 'titulo-seccion' }, icono('grafico', { clase: 's' }), 'Los 12 últimos meses'),
      barrasGanadoPerdido({ x, formato: v => fmt.eur(v), formatoX: ejeMes, enCurso: curso ? 1 : 0, notaCurso: curso ? `${nomMes(curso.m)} en curso: solo las altas del libro` : undefined,
        ganado: [{ nombre: 'Altas', clase: 'sube', y: [...d12.map(z => z.altas || 0), ...(curso ? [curso.entra || 0] : [])] }, { nombre: 'Subidas', clase: 'sube2', y: [...d12.map(z => z.subidas || 0), ...(curso ? [0] : [])] }],
        perdido: [{ nombre: 'Rebajas', clase: 'ambar', y: [...d12.map(z => z.bajadas || 0), ...(curso ? [0] : [])] }, { nombre: 'Bajas', clase: 'baja', y: [...d12.map(z => z.bajas || 0), ...(curso ? [curso.sale || 0] : [])] }],
        detalle: i => { const z = d12[i]; return z ? [`Cuota al cierre: ${fmt.eur(z.fin)}`] : ['Estimado: en curso']; } }),
      h('div', { class: 'fuga', role: 'group', 'aria-label': 'La fuga de la cuota, media de los 6 últimos meses' },
        h('div', { class: 'mayor' }, h('span', {}, 'Rebajas de cuota · al mes'), h('b', {}, pctS(S.rebajas_pct, 1)), h('span', {}, `12 meses: −${fmt.eur(S.rebajas_12)} · la mayor fuga`)),
        h('div', {}, h('span', {}, 'Bajas de clientes · al mes'), h('b', {}, pctS(S.bajas_pct, 1)), h('span', {}, `12 meses: −${fmt.eur(S.bajas_12)}`)),
        h('div', {}, h('span', {}, 'Subidas · al mes'), h('b', {}, pctS(S.subidas_pct, 1)), h('span', {}, `12 meses: +${fmt.eur(S.subidas_12)}`)),
        h('div', {}, h('span', {}, 'Pérdida bruta · al mes'), h('b', {}, pctS(S.perdida_pct, 1)), h('span', {}, 'rebajas + bajas sobre la cuota al empezar el mes'))),
      h('p', { class: 'sub' }, `Media de ${textoMeses(S.meses)} sobre la cuota con la que empieza cada mes. Antes de nada: mirar si las rebajas son reales (descuentos, cambios de plan) o ruido (prorrateos, proyectos que entran y salen del recurrente).`),
      h('div', { class: 'fila' },
        h('button', { type: 'button', class: 'bt mini', on: { click: () => tabs.elegir('ingresos') } }, icono('capas', { clase: 's' }), 'Ver por qué, mes a mes'),
        pedirRevisionRebajas(ctx, S)),
      h('p', { class: 'kpi-umbral ref' }, h('span', {}, `Referencia, no colorea: ${UMBRALES.perdida_cuota.texto}`), ' · ', enlaceFuente(FUENTES.saascapital.href, FUENTES.saascapital.fuente)),
      h('p', { class: 'kpi-umbral' }, chipEstado(sakas, `Bajas de clientes: ${pctS(kpi.churn_n, 1)} al mes`), h('span', {}, ` Umbral: ${UMBRALES.bajas_mes.texto}`), ' · ', enlaceFuente(FUENTES.sakas_rot.href, FUENTES.sakas_rot.fuente)),
      h('p', { class: 'kpi-pie' }, h('span', {}, 'Cómo se dibuja: '), enlaceFuente(FUENTES.chartmogul_mov.href, FUENTES.chartmogul_mov.fuente), enlaceFuente(FUENTES.baremetrics.href, FUENTES.baremetrics.fuente), h('span', {}, 'Dato: puente de Holded')),
      h('details', { class: 'que-es' }, h('summary', {}, 'Ver el puente mes a mes en tabla (12 meses)'),
        tablaDensa({ filas: [...d12].reverse(), apilable: true, orden: null, columnas: [
          { clave: 'm', titulo: 'Mes', principal: true, celda: z => mesLargo(z.m) },
          { clave: 'ini', titulo: 'Al empezar', num: true, celda: z => fmt.eur(z.ini) },
          { clave: 'altas', titulo: 'Altas', num: true, celda: z => (z.altas ? `+${fmt.eur(z.altas)}` : '—') },
          { clave: 'subidas', titulo: 'Subidas', num: true, celda: z => (z.subidas ? `+${fmt.eur(z.subidas)}` : '—') },
          { clave: 'bajadas', titulo: 'Rebajas', num: true, celda: z => (z.bajadas ? eurS(z.bajadas) : '—') },
          { clave: 'bajas', titulo: 'Bajas', num: true, celda: z => (z.bajas ? eurS(z.bajas) : '—') },
          { clave: 'fin', titulo: 'Al cierre', num: true, celda: z => fmt.eur(z.fin) },
          { clave: 'cuadra', titulo: '¿Cierra?', celda: z => chipEstado(z.cuadra ? 'verde' : 'rojo', z.cuadra ? 'sí' : 'no') }] }))));
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
    ], clave: 'finanzas-sofia', etiqueta: 'Finanzas', unaFila: true, pintar: (id, z) => {
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
  ], clave: 'finanzas', etiqueta: 'Finanzas', unaFila: true, pintar: (id, z) => {
    z.classList.add('pila');
    ({ resumen: pintarResumen, ingresos: pintarIngresos, top: pintarTop, resultados: pintarResultados,
      impagos: (c, x) => pintarImpagos(c, x, d.impagos, { acciones }),
      cuadre: (c, x) => pintarCuadre(c, x, d.cuadre, { completo: true }),
      cobros: (c, x, dd2) => pintarCobros(c, x, dd2, { tomas: true, objetivo: ctx.params?.[0] === 'cobros' ? ctx.params[1] : null }) })[id](z, ctx, d);
    z.append(pieFuentes(id === 'cuadre' ? d.cuadre || d : id === 'impagos' ? d.impagos || d : d));
    plegarSecundarias(z, id === 'cobros' ? { titulos: PLEGAR_COBROS } : id === 'impagos' ? { titulos: /^(Por antigüedad|Vencido sin cobrar)/ }
      : id === 'resumen' ? { titulos: PLEGAR_RESUMEN } : { desde: 2 });   // V2-E (M17): plegado común en el móvil
  } });
  cont.append(h('div', { class: 'fila' }, h('a', { class: 'bt pri', href: '#/panel-direccion' }, icono('dir'), 'Ver el panel de dirección completo'),
    h('span', { class: 'sub' }, 'Empresa, captación de RO y clientes del panel de resultados.')), tabs);
  if (ctx.params?.[0] === 'cobros') tabs.elegir('cobros');   // R15a (A2): la ruta manda sobre la pestaña recordada
  if (ctx.params?.[0] === 'impagos' || ctx.params?.[0] === 'cuadre') tabs.elegir(ctx.params[0]);
}
let tabs = { elegir: () => {} };
// V2-E (M17): en Cobros, lo que NO pide acción (impagos, firmados sin alta, devueltos y Meta se quedan abiertos)
const PLEGAR_COBROS = /^(Calendario administrativo|Cuota de octubre|Bajas y cambios|Caja por banco|En el periodo|Fiabilidad)/;
// Paneles v4: en el Resumen se pliega el porqué (gráficos e históricos); la cifra que manda, la cuota, las tarjetas, «Lo que pide
// tu decisión» y los cobros por antigüedad (impagos) se quedan abiertos.
const PLEGAR_RESUMEN = /^(Cuenta de|Del plan al real|De dónde sale|Caja a 90|Peso del equipo|Beneficio mes a mes|En el periodo)/;

export default {
  id: 'finanzas',
  titulo: 'Finanzas de la empresa',
  grupo: 'Dinero',
  puestos_que_lo_ven: { direccion: 'todo', finanzas_direccion: 'todo', administracion: 'todo' },
  // R12 (A-A2): datos mensuales → mes, mes anterior, trimestre, año y a medida (por meses enteros)
  usa_periodo: ['mes', 'mes_ant', 'trim', 'anio', 'medida'],
  async render(contenedor, ctx) { await pintar(contenedor, ctx); },
};
