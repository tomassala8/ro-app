// modulos/dinero_cliente.js · M18 «Dinero por cliente» (E10).
// Cuota, horas consumidas frente a pautadas y rentabilidad, cliente a cliente. Cuota: UNA fuente (Airtable de octubre; si no, factura de
// octubre en Holded), la misma de fuentes_dinero/cuotas.json. Pautadas = cuota ÷ 31,47 €/h y solo llegan a quien ve la cuota (claves cuota_*).
//   · Tomás: cuota, horas, rentabilidad a tarifa (31,47 €/h) y con el coste real por hora (de M19, solo él).
//   · Mili y Coti (operaciones y proyectos): cuota, horas y rentabilidad a 31,47 €/h (D-85). Sin caja ni beneficio.
//   · Sofía (administración): la cuota de todos y si tiene línea en facturación; sin horas ni rentabilidad.
//   · Account: la cuota y las horas de SUS clientes (D-80). Jefa de publicidad y trafficker: horas frente a pautadas, sin euros (D-87).
// Quién recibe qué lo decide servir.py (filas por cliente, claves de dinero por puesto, listas «solo todo»): aquí no se esconde nada con CSS.
// Datos: data/dinero_cliente/dinero_cliente.json ← fuentes_dinero/generar_dinero.py (Airtable y libro en lectura, horas de ClickUp de E1).

import { plegarSecundarias } from '../componentes.js';   // V2-E (M17): plegado común en el móvil
import { h, fmt, semaforo, grafico, tile, tiles, chipEstado, chipsFiltro, tablaDensa, panel, avisoParcial, vacio, logoCliente,
  icono, barraProgreso, listaLoPrimero, botonConfirmar, variacion } from '../componentes.js';
import { cargarDatos, pieFuentes, fresco, eurS, pctS, encolar, quinceFilas, mesesPeriodo, textoMeses } from './dinero_comun.js';

const BANDA = { verde: 100, ambar: 130 };   // horas consumidas ÷ pautadas: ≤ 100 % · 100-130 % aviso · > 130 % (solo aviso)

function estadoHoras(pct) {
  if (pct === null || pct === undefined) return 'gris';
  return pct <= BANDA.verde ? 'verde' : pct <= BANDA.ambar ? 'ambar' : 'rojo';
}
const estadoMargen = p => (p === null || p === undefined ? 'gris' : p >= 30 ? 'verde' : p >= 10 ? 'ambar' : 'rojo');

async function pintar(cont, ctx) {
  cont.classList.add('pila');
  const { d, error } = await cargarDatos(ctx, 'dinero_cliente/dinero_cliente');
  if (!d) {
    cont.append(vacio({ icono: 'euro', titulo: 'Sin datos de dinero por cliente', texto: error || 'Lanza fuentes_dinero/generar_dinero.py y recarga.', quien: 'Agus' }));
    return;
  }
  const todo = ctx.nivel === 'todo';
  const logos = new Map(ctx.clientes.map(c => [c.id, c]));
  const filas = (d.clientes || []).map(f => ({ ...f, coste_horas: f.coste_horas ? { ...f.coste_horas, ...(f.cuota_horas || {}),
      pct_sep: f.cuota_horas?.pautadas && f.coste_horas.sep != null ? Math.round((100 * f.coste_horas.sep) / f.cuota_horas.pautadas) : null } : undefined,
    nombre: f.nombre, logo: logos.get(f.cliente_id)?.logo, salud: logos.get(f.cliente_id)?.salud }));
  const veCuota = filas.some(f => 'cuota' in f);
  const veHoras = filas.some(f => f.coste_horas);   // R12: la clave existe siempre (undefined): sin horas para el puesto no hay tiles de horas
  const vePautadas = veHoras && filas.some(f => f.cuota_horas?.pautadas);
  // La rentabilidad va en su propio fichero, que el servidor solo da a dirección, operaciones y proyectos.
  // Los ficheros de dirección solo se piden si el puesto los puede recibir (así no hay 403 en la consola; decide el servidor)
  const puestos = ctx.persona?.puestos || [];
  const tiene = lista => puestos.some(x => lista.includes(x));
  const rentD = todo && tiene(['direccion', 'finanzas_direccion', 'operaciones', 'proyectos']) ? (await cargarDatos(ctx, 'dinero_cliente/rentabilidad')).d : null;
  const rent = (rentD?.rentabilidad || []).filter(r => r.coste);
  const veRent = rent.length > 0;
  const rentPor = new Map(rent.map(r => [r.cid, r.coste]));

  // Coste real por cliente (solo Tomás: viene de M19, que nadie más recibe)
  let real = null;
  if (ctx.veModulo?.('finanzas') && todo && tiene(['direccion', 'finanzas_direccion'])) {
    const f = await cargarDatos(ctx, 'finanzas/direccion');
    const dir = f.d?.direccion?.[0];
    if (dir?.rentabilidad_real?.length) real = { porCliente: new Map(dir.rentabilidad_real.map(r => [r.cid, r])), hora: dir.coste_hora_real, texto: dir.coste_hora_texto };
  }

  const quien = veRent ? (real ? 'Tú ves la rentabilidad a tarifa y con el coste real.' : 'Rentabilidad con la tarifa de 31,47 €/h.')
    : veCuota && !veHoras ? 'Cuota de cada cliente y si tiene línea en facturación.'
      : veCuota ? 'La cuota y las horas de tus clientes.' : 'Horas consumidas por cliente, sin euros.';
  ctx.titulo('Dinero por cliente', `${filas.length} clientes · ${quien}`);

  if (!filas.length) {
    cont.append(vacio({ icono: 'cli', titulo: 'No tienes clientes asignados', texto: 'Esta pantalla enseña los clientes de tu cartera. Las asignaciones las mantiene Mili.', quien: 'Mili' }));
    return;
  }

  // ------------------------------------------------ 1 · cifras (lo de cada día arriba)
  const conHoras = filas.filter(f => f.coste_horas?.pautadas && f.coste_horas?.sep !== null && f.coste_horas?.sep !== undefined && !f.nuevo);
  const hSep = conHoras.reduce((a, f) => a + f.coste_horas.sep, 0), hPaut = conHoras.reduce((a, f) => a + f.coste_horas.pautadas, 0);
  const pctH = hPaut ? Math.round((100 * hSep) / hPaut) : null;
  const pasados = conHoras.filter(f => (f.coste_horas.pct_sep ?? 0) > BANDA.ambar);
  const cuotaTotal = filas.reduce((a, f) => a + (f.cuota || 0), 0);
  const fHoras = fresco(d, 'ClickUp'), fCuota = fresco(d, 'Airtable');
  const lista = [];
  if (veCuota) lista.push(tile({ icono: 'euro', etiqueta: 'Cuota de octubre', valor: fmt.eur(cuotaTotal),
    contexto: `${filas.filter(f => f.cuota).length} clientes · Airtable de Sofía, firmados sin ficha y proyectos con fin${todo ? ' (la misma cifra que Finanzas)' : ''}`, medible: 'hoy', frescura: fCuota,
    ir: 'Ver la tabla', alPulsar: () => document.getElementById('dinero-tabla')?.scrollIntoView({ behavior: 'smooth' }) }));
  if (veHoras && !vePautadas) {
    const tot = filas.reduce((a, f) => a + (f.coste_horas?.sep || 0), 0);
    lista.push(tile({ icono: 'clock', etiqueta: 'Horas de septiembre en tus clientes', valor: fmt.num(tot), unidad: 'h', contexto: `${filas.length} clientes · sin pautadas ni euros para tu puesto`,
      medible: 'medias', medibleDetalle: d.imputacion?.texto || 'Horas incompletas', frescura: fHoras }));
  }
  if (veHoras && vePautadas) {
    lista.push(tile({ icono: 'clock', etiqueta: 'Horas de septiembre frente a pautadas', valor: pctH === null ? null : fmt.pct(pctH),
      unidad: `${fmt.num(hSep)} de ${fmt.num(hPaut)} h`, estado: estadoHoras(pctH),
      contexto: 'Aviso: hasta 100 % bien · 100-130 % vigilar · más de 130 % se decide', medible: 'medias',
      medibleDetalle: d.imputacion?.texto, frescura: fHoras }));
    lista.push(tile({ icono: 'alert', etiqueta: 'Clientes por encima del 130 %', valor: pasados.length, unidad: `de ${conHoras.length}`,
      estado: pasados.length === 0 ? 'verde' : pasados.length <= 3 ? 'ambar' : 'rojo', contexto: 'Consumen más horas de las que pagan',
      medible: 'medias', medibleDetalle: 'Horas incompletas: solo se imputa el 51,7 %', frescura: fHoras,
      ir: 'Ver cuáles', alPulsar: () => filtro?.elegir?.('pasados') }));
  }
  if (veRent) {
    const base = rent.reduce((a, r) => a + r.coste.cuota_mes, 0), marg = rent.reduce((a, r) => a + r.coste.margen, 0);
    const pm = base ? Math.round((100 * marg) / base) : null;
    const perdida = rent.filter(r => r.coste.margen < 0);
    lista.push(tile({ icono: 'grafico', etiqueta: 'Rentabilidad a 31,47 €/h', valor: pctS(pm), unidad: `${eurS(marg)} al mes`, estado: estadoMargen(pm),
      contexto: '(Cuota − horas × 31,47 €) ÷ cuota · verde ≥ 30 % · rojo < 10 %', medible: 'medias', medibleDetalle: 'Septiembre; con horas incompletas sale inflada', frescura: fHoras }));
    lista.push(tile({ icono: 'baja', etiqueta: 'Clientes en pérdida a tarifa', valor: perdida.length, unidad: `de ${rent.length}`,
      estado: perdida.length === 0 ? 'verde' : perdida.length <= 2 ? 'ambar' : 'rojo', contexto: 'Verde 0 · rojo 3 o más (2 meses seguidos; umbral propuesto)',
      medible: 'medias', medibleDetalle: 'Un solo mes medido: falta el segundo para la alarma', frescura: fHoras }));
  }
  if (real) {
    const base = [...real.porCliente.values()].reduce((a, r) => a + r.cuota_mes, 0), marg = [...real.porCliente.values()].reduce((a, r) => a + r.margen_real, 0);
    lista.push(tile({ icono: 'cartera', etiqueta: 'Rentabilidad con el coste real', valor: pctS(base ? (100 * marg) / base : null), unidad: `${fmt.num(real.hora, 2)} €/h`,
      estado: '', contexto: real.texto, medible: 'medias', medibleDetalle: 'Coste real por hora = equipo agregado ÷ horas disponibles; solo lo ves tú' }));
  }
  if (veCuota && !veHoras) {
    // V2 (A-M3): UN recuento de «sin línea en facturación», el mismo que el chip de la tabla, partido por su porqué. Las altas
    // firmadas son las mismas que «Firmados sin alta en facturación» de Finanzas.
    const sinLinea = filas.filter(f => !f.cuota_en_facturacion && 'cuota_en_facturacion' in f);
    const porque = [['Firmado, sin libro', 'altas firmadas (las de Finanzas › Cobros)'], ['Proyecto', 'proyectos con fin'], ['Extras sueltos', 'extras sueltos'], ['Activo', 'activos']]
      .map(([e, t]) => [sinLinea.filter(f => f.estado_libro === e).length, t]).filter(([n]) => n);
    const otros = sinLinea.length - porque.reduce((a, [n]) => a + n, 0);
    lista.push(tile({ icono: 'doc', etiqueta: 'Sin línea de octubre en facturación', valor: sinLinea.length, unidad: `de ${filas.length}`,
      estado: sinLinea.some(f => f.estado_libro === 'Activo' || f.nuevo) ? 'ambar' : 'verde',
      contexto: `${[...porque.map(([n, t]) => `${n} ${t}`), otros ? `${otros} sin estado en el libro` : null].filter(Boolean).join(' · ') || 'Ninguno'} · activos sin línea: ${sinLinea.filter(f => f.estado_libro === 'Activo').length}`, medible: 'hoy', frescura: fCuota,
      ir: 'Ver cuáles', alPulsar: () => filtro?.elegir?.('sin_linea') }));
  }
  // R12 (A-A2): lo facturado en el periodo de la barra (Holded, por meses enteros). Horas y rentabilidad no cambian: son de
  // septiembre, el único mes cerrado con horas imputadas; la cuota es la de octubre. Se dice en el tile.
  const per = ctx.periodo ? mesesPeriodo(ctx.periodo) : null;
  // V2 (A-M3): «▲ 19 %» aquí frente a «▲ 12 %» en Finanzas para el mismo facturado. Misma cifra, otra base: aquí, estos clientes
  // en los dos periodos; allí, toda la empresa (con los que ya se fueron). Se dicen las dos en pantalla.
  let FA = null; try { FA = (todo && veCuota) ? await ctx.datosModulo('finanzas/finanzas') : null; } catch { FA = null; }
  const empTxt = pp => {
    const fm = FA?.admin?.facturado_mes; if (!fm || !pp?.comp?.length) return '';
    const sum = ms => fm.filter(x => ms.includes(x.m)).reduce((a, x) => a + (x.total || 0), 0);
    const a = sum(pp.meses), b = sum(pp.comp); if (!a || !b) return '';
    const v = variacion(a, b);
    return `; toda la empresa, con las bajas: ${fmt.eur(a)} (${v >= 0 ? '▲' : '▼'} ${fmt.num(Math.abs(v), 0)} %), la cifra de Finanzas`;
  };
  const veFact = veCuota && filas.some(f => f.cuota_facturado_mes);
  const factDe = (f, meses) => { let t = null; for (const m of meses) { const v = f.cuota_facturado_mes?.[m]; if (typeof v === 'number') t = (t || 0) + v; } return t; };
  if (veFact && per) {
    const tot = filas.reduce((a, f) => a + (factDe(f, per.meses) || 0), 0);
    const totC = per.comp.length ? filas.reduce((a, f) => a + (factDe(f, per.comp) || 0), 0) : null;
    const antes = per.meses.every(m => m < (d.facturado_desde || '2026-04'));
    lista.unshift(tile({ icono: 'euro', etiqueta: 'Facturado a estos clientes', valor: antes ? null : fmt.eur(tot), sinDato: `Holded se lee desde ${textoMeses([d.facturado_desde || '2026-04'])}`,
      comparacion: totC === null || antes ? undefined : { delta: variacion(tot, totC), pct: true, mejorSi: 'alto', texto: `frente a ${textoMeses(per.comp)}` },
      contexto: `${textoMeses(per.meses)} · Holded sin IVA · la comparación es con lo facturado a ESTOS MISMOS clientes en ${textoMeses(per.comp)}${empTxt(per)} · horas y rentabilidad no cambian: son de septiembre`, medible: 'hoy', frescura: fresco(d, 'Holded') }));
  }
  cont.append(tiles(lista));
  if (per && !veFact) cont.append(avisoParcial('En esta pantalla el periodo no cambia nada para tu puesto: las horas son las de septiembre, el único mes cerrado con horas imputadas.', { tipo: 'info', titulo: 'Periodo.' }));

  if (veHoras) cont.append(avisoParcial(d.imputacion?.texto || 'Horas incompletas.', { titulo: 'Horas incompletas.' }));

  // ------------------------------------------------ 2 · lo primero: dónde se pierde dinero (o tiempo)
  if (veRent || vePautadas) {
    const peores = veRent
      ? rent.filter(r => r.coste.margen_pct < 10).slice(0, 7).map(r => {
        const f = filas.find(x => x.cliente_id === r.cid);
        return { estado: r.coste.margen < 0 ? 'rojo' : 'ambar', icono: 'baja', motivo: `${r.nombre} · ${pctS(r.coste.margen_pct)} a tarifa`,
          detalle: `${fmt.num(r.coste.horas)} h en septiembre × 31,47 € = ${fmt.eur(r.coste.eur)} frente a ${fmt.eur(r.coste.cuota_mes)} de cuota${r.account ? ` · ${r.account}` : ''}${real?.porCliente.get(r.cid) ? ` · con coste real ${pctS(real.porCliente.get(r.cid).margen_real_pct)}` : ''}`,
          botones: [f && ctx.veModulo?.('ficha') ? h('a', { class: 'bt mini', href: `#/ficha/${r.cid}/trabajo` }, icono('clock'), 'Ver el trabajo') : null,
            botonConfirmar({ texto: 'Pedir revisión a Coti', pregunta: '¿Pedir a Coti que revise la oferta de este cliente?', confirmar: 'Sí', mini: true, soloLectura: ctx.soloLectura,
              alConfirmar: async () => { await encolar(ctx, { herramienta: 'app', tipo: 'revisar_oferta', objeto: r.cid, cliente_id: r.cid, texto: `Revisar la oferta de ${r.nombre}: ${pctS(r.coste.margen_pct)} a tarifa`, vista_previa: { para: 'Coti', aviso: 'en su Mi día' } }); return 'En la cola (simulado)'; } })].filter(Boolean) };
      })
      : pasados.sort((a, b) => b.coste_horas.pct_sep - a.coste_horas.pct_sep).slice(0, 7).map(f => ({
        estado: 'rojo', icono: 'clock', motivo: `${f.nombre} · ${fmt.pct(f.coste_horas.pct_sep)} de las horas pautadas`,
        detalle: `${fmt.num(f.coste_horas.sep)} h en septiembre de ${fmt.num(f.coste_horas.pautadas)} pautadas${f.account ? ` · ${f.account}` : ''}`,
        botones: [ctx.veModulo?.('ficha') ? h('a', { class: 'bt mini', href: `#/ficha/${f.cliente_id}/trabajo` }, icono('clock'), 'Ver el trabajo') : null].filter(Boolean) }));
    cont.append(panel({ titulo: veRent ? 'Dónde se pierde dinero' : 'Dónde se van las horas', icono: 'zap',
      sub: veRent ? 'Clientes por debajo del 10 % de rentabilidad a tarifa, el peor arriba (máximo 7)' : 'Clientes por encima del 130 % de sus horas (máximo 7)' },
      listaLoPrimero(peores, { vacio: { titulo: 'Ningún cliente por debajo del umbral', porque: 'Todos dejan al menos un 10 % a tarifa.', celebrar: true } })));
  }

  // ------------------------------------------------ 3 · la tabla cliente a cliente, con chips que se quedan
  const nCuenta = pred => filas.filter(pred).length;
  const PRED = {
    '': () => true,
    pasados: f => (f.coste_horas?.pct_sep ?? 0) > BANDA.ambar && !f.nuevo,
    perdida: f => (rentPor.get(f.cliente_id)?.margen ?? 1) < 0,
    nuevos: f => f.nuevo,
    sin_linea: f => !f.cuota_en_facturacion && 'cuota_en_facturacion' in f,
    sin_account: f => !f.account_id,
  };
  const opciones = [{ valor: '', texto: 'Todos', cuenta: filas.length, icono: 'cli' }];
  if (vePautadas) opciones.push({ valor: 'pasados', texto: 'Más de 130 % de horas', cuenta: nCuenta(PRED.pasados), cuentaEstado: 'rojo', icono: 'clock' });
  if (veRent) opciones.push({ valor: 'perdida', texto: 'En pérdida a tarifa', cuenta: nCuenta(PRED.perdida), cuentaEstado: 'rojo', icono: 'baja' });
  opciones.push({ valor: 'nuevos', texto: 'Nuevos (90 días)', cuenta: nCuenta(PRED.nuevos), icono: 'rocket' });
  if (veCuota && todo) opciones.push({ valor: 'sin_linea', texto: 'Sin línea en facturación', cuenta: nCuenta(PRED.sin_linea), cuentaEstado: 'rojo', icono: 'doc' });
  if (todo) opciones.push({ valor: 'sin_account', texto: 'Sin account', cuenta: nCuenta(PRED.sin_account), icono: 'persona' });

  const zonaTabla = h('div', { id: 'dinero-tabla' });
  const columnas = [
    { clave: 'nombre', titulo: 'Cliente', principal: true, minAncho: '200px', celda: f => h('span', { class: 'celda-cli' }, logoCliente(f),
      h('span', { class: 'pila', style: { gap: 'var(--s-1)', minWidth: '0' } }, h('b', {}, f.nombre), h('span', { class: 'sub' }, [f.account || 'sin account', f.nuevo ? 'nuevo' : null, f.estado_libro && f.estado_libro !== 'Activo' ? f.estado_libro.toLowerCase() : null].filter(Boolean).join(' · ')))) },
  ];
  if (veCuota) columnas.push({ clave: 'cuota', titulo: 'Cuota', num: true, celda: f => f.cuota ? h('span', { title: f.cuota_fuente || '' }, fmt.eur(f.cuota)) : '—' });
  if (veFact && per) columnas.push({ clave: 'fact_periodo', titulo: per.meses.length === 1 ? `Facturado ${textoMeses(per.meses).split(' de ')[0]}` : 'Facturado en el periodo', num: true,
    valor: f => factDe(f, per.meses), celda: f => { const v = factDe(f, per.meses); return v === null ? h('span', { class: 'dim' }, 'sin factura') : fmt.eur(v); } });
  if (veHoras) columnas.push(
    { clave: 'horas', titulo: vePautadas ? 'Horas sep. / pautadas' : 'Horas de septiembre', valor: f => f.coste_horas?.sep ?? null, celda: f => {
      const c = f.coste_horas || {};
      if (c.sep === null || c.sep === undefined) return h('span', { class: 'dim' }, 'sin horas');
      return h('div', { class: 'pila' }, h('span', {}, `${fmt.num(c.sep, 1)} h de ${c.pautadas ? fmt.num(c.pautadas, 1) : '—'}`),
        c.aviso_cartera ? h('span', { class: 'sub', title: 'Las pautadas salen de la cuota de facturación' }, c.aviso_cartera) : null,
        c.pautadas ? barraProgreso({ valor: Math.min(c.sep, c.pautadas * 2), max: c.pautadas * 2, marca: c.pautadas, estado: estadoHoras(c.pct_sep), etiqueta: `${fmt.num(c.sep)} de ${fmt.num(c.pautadas)} horas` }) : null);
    } },
    ...(vePautadas ? [] : [{ __quitar: true }]),
    { clave: 'pct', titulo: '% horas', num: true, valor: f => f.coste_horas?.pct_sep ?? null, celda: f => f.coste_horas?.pct_sep === null || f.coste_horas?.pct_sep === undefined ? '—'
      : chipEstado(f.nuevo ? 'gris' : estadoHoras(f.coste_horas.pct_sep), fmt.pct(f.coste_horas.pct_sep)) });
  if (veRent) columnas.push({ clave: 'margen', titulo: 'Rentab. a tarifa', num: true, valor: f => rentPor.get(f.cliente_id)?.margen_pct ?? null,
    celda: f => { const r = rentPor.get(f.cliente_id); return r ? chipEstado(estadoMargen(r.margen_pct), `${pctS(r.margen_pct)} · ${eurS(r.margen)}`) : h('span', { class: 'dim' }, f.nuevo ? 'nuevo' : '—'); } });
  if (real) columnas.push({ clave: 'real', titulo: 'Con coste real', num: true, valor: f => real.porCliente.get(f.cliente_id)?.margen_real_pct ?? null,
    celda: f => { const r = real.porCliente.get(f.cliente_id); return r ? h('span', { title: `Coste real ${fmt.eur(r.coste_real)}` }, `${pctS(r.margen_real_pct)} · ${eurS(r.margen_real)}`) : '—'; } });
  if (veCuota && todo) columnas.push({ clave: 'vida', titulo: 'Valor de vida', num: true, valor: f => f.cuota_valor_vida ?? null,
    celda: f => f.cuota_valor_vida ? h('span', { title: `${fmt.num(f.cuota_vida_meses, 1)} meses de cliente` }, fmt.eur(f.cuota_valor_vida)) : '—' });
  if (veCuota && todo) columnas.push({ clave: 'cuota_en_facturacion', titulo: 'Facturación', celda: f => f.cuota_en_facturacion ? chipEstado('verde', 'línea de octubre') : f.cuota ? chipEstado('ambar', 'solo en Holded') : chipEstado('gris', 'sin cuota') });
  if (filas.some(f => f.facturas_holded_url || f.facturas_airtable_url)) columnas.push({ clave: 'atajos', titulo: 'Abrir en', ordenable: false, celda: f => h('span', { class: 'fila' },
    f.facturas_holded_url ? h('a', { class: 'bt mini', href: f.facturas_holded_url, target: '_blank', rel: 'noopener', title: `Factura ${f.facturas_holded_doc || ''} en Holded` }, icono('ext', { clase: 's' }), 'Holded') : null,
    f.facturas_airtable_url ? h('a', { class: 'bt mini', href: f.facturas_airtable_url, target: '_blank', rel: 'noopener', title: 'Línea de octubre en el Airtable de facturación (solo lectura)' }, icono('ext', { clase: 's' }), 'Airtable') : null) });

  for (let i = columnas.length - 1; i >= 0; i--) if (columnas[i].__quitar) columnas.splice(i, 2);   // sin pautadas no hay «% horas»
  const pintarTabla = v => {
    const sel = filas.filter(PRED[v] || PRED['']);
    zonaTabla.replaceChildren(tablaDensa({
      filas: sel, columnas, apilable: true, buscar: { placeholder: 'Buscar cliente o account…', campos: ['nombre', 'account'] },
      orden: veRent ? { clave: 'margen', dir: 'asc' } : veHoras ? { clave: 'pct', dir: 'desc' } : { clave: 'cuota', dir: 'desc' },
      alPulsar: ctx.veModulo?.('ficha') ? f => ctx.navegar(`ficha/${f.cliente_id}`) : null,
      puedePulsar: f => !!logos.get(f.cliente_id)?.detalle, etiquetaFila: f => `Abrir la ficha de ${f.nombre}`,
      vacio: { titulo: 'Ningún cliente en esta vista', porque: 'Cambia el filtro de arriba.' } }));
    quinceFilas(zonaTabla);
  };
  const filtro = chipsFiltro({ opciones, clave: `dinero-cliente-${ctx.persona.id}`, etiqueta: 'Ver', alCambiar: pintarTabla });
  filtro.elegir = v => { const b = [...filtro.querySelectorAll('button')].find(x => x.textContent.startsWith(opciones.find(o => o.valor === v)?.texto || '¬')); b?.click(); zonaTabla.scrollIntoView({ behavior: 'smooth' }); };
  cont.append(panel({ titulo: 'Cliente a cliente', icono: 'cli', sub: veRent ? 'Ordenado del que menos deja al que más. Pulsa una fila para abrir su ficha.' : 'Pulsa una fila para abrir su ficha.' },
    h('div', { class: 'cuerpo pila' }, filtro, zonaTabla)));
  pintarTabla(filtro.valor());

  // ------------------------------------------------ 4 · los que más dejan (Tomás, Mili, Coti)
  if (veRent) {
    const orden = [...rent].sort((a, b) => a.coste.margen_pct - b.coste.margen_pct);
    cont.append(panel({ titulo: 'Rentabilidad cliente a cliente', icono: 'grafico', sub: 'Cuota frente a horas × 31,47 € en septiembre, del que menos deja al que más. Pasa el ratón para ver cada cliente.' },
      h('div', { class: 'cuerpo' }, grafico({ x: orden.map(r => r.nombre), formatoX: v => v, formato: v => fmt.pct(v),
        barras: { nombre: 'Rentabilidad a tarifa', y: orden.map(r => r.coste.margen_pct), formato: v => fmt.pct(v) },
        umbral: { y: 10, texto: 'umbral 10 %' }, alto: 200 }))));
    const mejores = [...rent].sort((a, b) => b.coste.margen - a.coste.margen).slice(0, 10);
    cont.append(panel({ titulo: 'Los 10 que más dejan', icono: 'star', sub: 'Margen a tarifa en euros de septiembre (cuota − horas × 31,47 €)' },
      h('div', { class: 'cuerpo' }, tablaDensa({ filas: mejores.map(r => ({ ...r, m: r.coste.margen, p: r.coste.margen_pct, horas: r.coste.horas, cuota: r.coste.cuota_mes })), apilable: true, columnas: [
        { clave: 'nombre', titulo: 'Cliente', principal: true },
        { clave: 'account', titulo: 'Account', celda: r => r.account || '—' },
        { clave: 'cuota', titulo: 'Cuota', num: true, celda: r => fmt.eur(r.cuota) },
        { clave: 'horas', titulo: 'Horas sep.', num: true, celda: r => fmt.num(r.horas, 1) },
        { clave: 'm', titulo: 'Deja al mes', num: true, celda: r => chipEstado(estadoMargen(r.p), `${eurS(r.m)} · ${pctS(r.p)}`) }] }))));
  }

  // ------------------------------------------------ 5 · por account (solo quien lo ve todo)
  const pa = (d.por_account || []);
  if (todo && pa.length) {
    cont.append(panel({ titulo: 'Por account', icono: 'eq', sub: `Clientes, cuota y horas de cada cartera · tope de ${d.tope_account} clientes por account` },
      h('div', { class: 'cuerpo' }, tablaDensa({ filas: pa.map(p => ({ ...p, hs: p.coste_horas?.sep, hp: p.cuota_horas?.pautadas })), apilable: true, columnas: [
        { clave: 'account', titulo: 'Account', principal: true },
        { clave: 'clientes', titulo: 'Clientes', num: true, celda: p => h('div', { class: 'pila' }, h('span', {}, `${p.clientes} de ${d.tope_account}${p.nuevos ? ` · ${p.nuevos} nuevos` : ''}`),
          barraProgreso({ valor: p.clientes, max: d.tope_account, estado: p.clientes >= d.tope_account ? 'rojo' : p.huecos <= 5 ? 'ambar' : 'verde' })) },
        ...(pa.some(p => 'cuota' in p) ? [{ clave: 'cuota', titulo: 'Cuota', num: true, celda: p => fmt.eur(p.cuota) }] : []),
        ...(pa.some(p => p.coste_horas) ? [{ clave: 'hs', titulo: 'Horas sep. / pautadas', num: true, celda: p => p.hs === undefined ? '—' : `${fmt.num(p.hs)} / ${fmt.num(p.hp)} h` }] : []),
        { clave: 'huecos', titulo: 'Huecos', num: true, celda: p => chipEstado(p.huecos <= 0 ? 'rojo' : p.huecos <= 5 ? 'ambar' : 'verde', String(Math.max(0, p.huecos))) }] }))));
  }

  // ------------------------------------------------ 6 · fase 2 y fuentes
  cont.append(panel({ titulo: 'Todavía no se mide', icono: 'medidor', sub: 'Va a la fase 2: no se pinta como número (R5)' },
    h('ul', { class: 'cuerpo pila' },
      h('li', {}, 'Rentabilidad por servicio y por nicho: falta el dato «servicio contratado por cliente».'),
      h('li', {}, 'Herramientas por cliente (GHL, Meta, Metricool) en el coste: hoy solo cuentan las horas.'),
      h('li', {}, 'Clientes en pérdida dos meses seguidos: hace falta un segundo mes con horas imputadas de verdad.'))),
    pieFuentes(d));
  // V2-E (M17): en el móvil, gráficos, rankings y desgloses van plegados con una línea; «Dónde se pierde» y la tabla, abiertos
  plegarSecundarias(cont, { titulos: /^(Rentabilidad cliente a cliente|Los 10 que más dejan|Por account|Todavía no se mide)/ });
}

export default {
  id: 'dinero-cliente',
  titulo: 'Dinero por cliente',
  grupo: 'Dinero',
  puestos_que_lo_ven: { direccion: 'todo', finanzas_direccion: 'todo', operaciones: 'todo', proyectos: 'todo', administracion: 'todo', account: 'suyo', jefa_publicidad: 'resumen', trafficker: 'resumen' },
  // R12 (A-A2): lo facturado se mira por meses enteros; horas y rentabilidad son de septiembre (no cambian con el periodo)
  usa_periodo: ['mes', 'mes_ant', 'trim', 'anio', 'medida'],
  async render(contenedor, ctx) { await pintar(contenedor, ctx); },
};
