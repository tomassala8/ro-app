import { pintarCierre253 } from './_cierre_artifact_253.js';
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
import { cargarDatos, pieFuentes, fresco, eurS, pctS, encolar, quinceFilas, mesesPeriodo, textoMeses, mesCorto } from './dinero_comun.js';
import { tarjetaKpi, cifraPrincipal, barrasDivergentes, barraApilada, mapaCalor, enlaceFuente, minilinea, colorCifra } from '../componentes.js';
import { FUENTES, UMBRALES, ESTADO, fuentesAlPie, mesMas, separador } from './dinero_v4.js';

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
  if (ctx.params?.[0] === 'cierre-septiembre') {
    if (ctx.vigente && !ctx.vigente()) return;
    ctx.titulo('Cierre de septiembre', 'Por account y por cliente · horas registradas');
    cont.replaceChildren(pintarCierre253({h,d,clientes:ctx.clientesVisibles || ctx.clientes || [],verdad:ctx.verdad,nombre:ctx.nombre,veFicha:ctx.veModulo?.('ficha')}));
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
  let real = null, dirD = null;
  if (ctx.veModulo?.('finanzas') && todo && tiene(['direccion', 'finanzas_direccion'])) {
    const f = await cargarDatos(ctx, 'finanzas/direccion');
    const dir = f.d?.direccion?.[0];
    dirD = dir || null;
    if (dir?.rentabilidad_real?.length) real = { porCliente: new Map(dir.rentabilidad_real.map(r => [r.cid, r])), hora: dir.coste_hora_real, texto: dir.coste_hora_texto };
  }
  // Paneles v4: retención por mes de alta (dirección, operaciones y proyectos; el servidor decide) y coste de captar (Ventas de RO)
  const cohD = todo && tiene(['direccion', 'finanzas_direccion', 'operaciones', 'proyectos']) ? (await cargarDatos(ctx, 'dinero_cliente/cohortes')).d : null;
  const ventasD = dirD && ctx.veModulo?.('ventas-ro') ? (await cargarDatos(ctx, 'ventas_ro/ventas_ro')).d : null;

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
  if (veRent) cont.append(...cabezaV4({ ctx, d, filas, rent, real, dirD, fHoras, tileFact: veFact && per ? lista[0] : null, cuotaTotal, verPerdida: () => filtro?.elegir?.('perdida') }));
  else cont.append(tiles(lista));
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
      listaLoPrimero(peores, { subir: !veRent, vacio: { titulo: 'Ningún cliente por debajo del umbral', porque: 'Todos dejan al menos un 10 % a tarifa.', celebrar: true } })));   // paneles v4: la cifra que manda va primero
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
  // Paneles v4 (48 §4: «al final, tablas y detalle plegados»): para quien ve la rentabilidad, la tabla va plegada debajo de
  // los gráficos; «Ver cuáles» de las tarjetas la abre. Para los demás puestos es su pantalla y sigue abierta.
  const panelTabla = panel({ titulo: 'Cliente a cliente', icono: 'cli', sub: veRent ? 'Ordenado del que menos deja al que más. Pulsa una fila para abrir su ficha.' : 'Pulsa una fila para abrir su ficha.' },
    h('div', { class: 'cuerpo pila' }, filtro, zonaTabla));
  const plegTabla = veRent ? h('details', { class: 'tabla-plegada', id: 'dinero-tabla-pleg' }, h('summary', { class: 'bt' }, icono('cli', { clase: 's' }), `Ver la tabla cliente a cliente (${filas.length})`), panelTabla) : panelTabla;
  if (veRent) { const el0 = filtro.elegir; filtro.elegir = v => { plegTabla.open = true; el0(v); }; }
  else cont.append(panelTabla);
  pintarTabla(filtro.valor());

  // ------------------------------------------------ 4 · paneles v4: margen por cliente, concentración, valor de vida y cohortes
  if (veRent) {
    cont.append(separador('El porqué de las cifras'));
    let modoR = 'tarifa';
    const ordDe = modo => [...rent].map(r => { const rr = real?.porCliente.get(r.cid); const conReal = modo === 'real' && rr; return { r, v: conReal ? rr.margen_real : r.coste.margen, pct: conReal ? rr.margen_real_pct : r.coste.margen_pct }; }).sort((a, b) => a.v - b.v);
    let ord = ordDe(modoR);
    const filaDe = x => ({ etiqueta: x.r.nombre, sub: `${x.r.account || 'sin account'} · ${pctS(x.pct)} · ${fmt.num(x.r.coste.horas, 1)} h`, valor: x.v, cid: x.r.cid,
      titulo: `${x.r.nombre}: cuota ${fmt.eur(x.r.coste.cuota_mes)}, ${fmt.num(x.r.coste.horas, 1)} h en septiembre` });
    const abrir = ctx.veModulo?.('ficha') ? f => ctx.navegar(`ficha/${f.cid}`) : null;
    const zonaRank = h('div', { class: 'pila' });
    const pintarRank = todos => zonaRank.replaceChildren(
      barrasDivergentes({ formato: v => eurS(v), etiqueta: 'Margen por cliente al mes', alPulsar: abrir,
        filas: (todos || ord.length <= 20 ? ord : [...ord.slice(0, 10), ...ord.slice(-10)]).map(filaDe) }),
      !todos && ord.length > 20 ? h('button', { type: 'button', class: 'bt', on: { click: () => pintarRank(true) } }, `Ver los ${ord.length} clientes (aquí, los 10 que menos dejan y los 10 que más)`) : null);
    pintarRank(false);
    const chipsR = real ? chipsFiltro({ opciones: [{ valor: 'tarifa', texto: 'A la tarifa (31,47 €/h)', icono: 'clock' }, { valor: 'real', texto: `Con el coste real (${fmt.num(real.hora, 2)} €/h)`, icono: 'cartera' }],
      clave: 'dinero-ranking-modo', etiqueta: 'Coste de la hora', alCambiar: v => { modoR = v; ord = ordDe(v); pintarRank(false); } }) : null;
    if (chipsR && chipsR.valor() !== 'tarifa') { modoR = chipsR.valor(); ord = ordDe(modoR); pintarRank(false); }
    cont.append(panel({ titulo: 'Margen por cliente, del que menos deja al que más', icono: 'grafico',
      sub: real ? 'Cuota − horas de septiembre × el coste de la hora: a la tarifa (31,47 €/h) o con el coste real (solo lo ves tú). Negativo: cuesta más de lo que paga.' : 'Cuota − horas de septiembre × 31,47 € (la tarifa). Negativo: cuesta más de lo que paga.' },
      h('div', { class: 'cuerpo pila' }, chipsR, zonaRank,
        h('p', { class: 'kpi-umbral ref' }, h('span', {}, `Referencia, no colorea al cliente: ${UMBRALES.horas_imputadas.texto}. Solo se imputa el ${fmt.pct(d.imputacion?.pct, 1)} de la jornada.`)),
        h('p', { class: 'kpi-pie' }, h('span', {}, 'Cómo se dibuja: rentabilidad por cliente como Scoro y Productive · '), enlaceFuente(FUENTES.productive.href, FUENTES.productive.fuente)))));
  }
  if (veCuota && todo) cont.append(h('div', { class: 'dos iguales' }, panelConcentracion(filas), panelValorVida({ filas, dirD, ventasD })));
  if (cohD?.clientes?.filas?.length) cont.append(panelCohortes(cohD, ctx));

  if (veRent) cont.append(plegTabla);
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
    veRent || (veCuota && todo) ? fuentesAlPie(['productive', 'ami', 'sakas_conc', 'baker', 'geckoboard', 'chartmogul_ltv', 'chartmogul_coh']) : '',
    pieFuentes(d));
  // V2-E (M17): en el móvil, gráficos, rankings y desgloses van plegados con una línea; «Dónde se pierde» y la tabla, abiertos
  plegarSecundarias(cont, { titulos: /^(Margen por cliente|Concentración|Valor de vida|Cuántos se quedan|Por account|Todavía no se mide)/ });
}

// ===================================================================== paneles v4 (3-oct) · 48 §4.3
// «¿Qué clientes nos dejan dinero, cuáles nos cuestan y cuáles se van a ir?»: arriba la cifra que manda (margen de la cartera
// al mes) y cuatro tarjetas; debajo, el margen cliente a cliente en barras ordenadas, la concentración, el valor de vida con
// la recuperación de la captación y las cohortes de retención; la tabla, plegada al final.
function cabezaV4({ ctx, d, filas, rent, real, dirD, fHoras, tileFact, cuotaTotal, verPerdida }) {
  const base = rent.reduce((a, r) => a + r.coste.cuota_mes, 0), horas = rent.reduce((a, r) => a + (r.coste.horas || 0), 0);
  const margenT = rent.reduce((a, r) => a + r.coste.margen, 0);
  const margenR = real ? [...real.porCliente.values()].reduce((a, r) => a + r.margen_real, 0) : null;
  const v = real ? margenR : margenT;
  const enPerdida = rent.filter(r => r.coste.margen < 0).length;
  const conCuota = filas.filter(f => f.cuota > 0);
  const media = conCuota.length ? cuotaTotal / conCuota.length : null;
  // cuota media mes a mes (solo Tomás: cuota facturada del puente ÷ clientes activos del libro)
  let serieMedia = null, xMedia = null, compMedia = {};
  if (dirD?.puente?.length && dirD?.altas_bajas?.length) {
    const act = new Map(dirD.altas_bajas.map(z => [z.m, z.fin]));
    const L = dirD.puente.slice(-12).filter(z => act.get(z.m));
    xMedia = L.map(z => z.m); serieMedia = L.map(z => z.fin / act.get(z.m));
    if (L.length >= 2) compMedia = { mes_ant: { num: serieMedia.at(-1), ref: serieMedia.at(-2), texto: `cuota facturada por cliente: ${mesCorto(xMedia.at(-1))} frente a ${mesCorto(xMedia.at(-2))}` } };
  }
  const tarifa = horas ? base / horas : null;
  const cifra = panel({ titulo: 'Margen de la cartera al mes · la cifra que manda', icono: 'cartera',
    sub: real ? `Cuota − horas de septiembre × coste real por hora (${fmt.num(real.hora, 2)} €/h). Solo lo ves tú.` : 'Cuota − horas de septiembre × 31,47 € (la tarifa). Sin caja ni beneficio de la empresa.' },
    h('div', { class: 'cuerpo pila' },
      cifraPrincipal({ etiqueta: `${rent.length} clientes con horas en septiembre · ${fmt.eur(base)} de cuota`, valor: eurS(v), estado: colorCifra('beneficio', v),
        comparacion: h('span', { class: 'tc' }, h('em', {}, 'Un solo mes con horas imputadas (septiembre): la comparación llega con octubre')) }),
      real ? h('p', { class: 'cifra-gris' }, `A la tarifa de 31,47 €/h: ${eurS(margenT)} al mes (${pctS(base ? (100 * margenT) / base : null)}).`) : null,
      h('p', { class: 'kpi-pie' }, h('span', {}, `Con el ${fmt.pct(d.imputacion?.pct, 1)} de las horas imputadas: el margen sale inflado. Aviso, no prueba.`),
        h('span', {}, 'Dato: '), enlaceFuente(ctx.veModulo?.('horas') ? '#/horas' : null, 'horas de ClickUp y cuota de Airtable'))));
  const tarjetas = h('div', { class: 'tiles' },
    tarjetaKpi({ icono: 'euro', etiqueta: 'Cuota media por cliente', valor: fmt.eur(media), unidad: 'al mes', num: media, mejorSi: 'alto',
      serie: serieMedia, serieX: xMedia, formatoSerie: x => fmt.eur(x), comparaciones: compMedia,
      contexto: `Cuota de octubre ${fmt.eur(cuotaTotal)} entre ${conCuota.length} clientes${serieMedia ? ' · línea: cuota facturada ÷ clientes activos de cada mes' : ''}`, fuente: { texto: 'Airtable de Sofía y Holded' } }),
    tarjetaKpi({ icono: 'clock', etiqueta: 'Tarifa efectiva por hora', valor: tarifa === null ? null : fmt.num(tarifa, 2), unidad: '€/h', num: tarifa, mejorSi: 'alto',
      comparaciones: { objetivo: { ref: 31.47, texto: 'frente a la tarifa de 31,47 €/h', modo: 'pct' } }, comparar: 'objetivo',
      contexto: `Cuota ÷ horas de septiembre de los ${rent.length} clientes con horas (${fmt.num(horas)} h)`, medible: 'medias', medibleDetalle: 'Con las horas a medias, sale alta', fuente: { texto: 'ClickUp' }, frescura: fHoras }),
    tarjetaKpi({ icono: 'baja', etiqueta: 'Clientes en pérdida a tarifa', valor: enPerdida, unidad: `de ${rent.length}`, estado: '',
      contexto: 'Cuestan más horas × 31,47 € de lo que pagan · aviso, no prueba (un solo mes)', medible: 'medias', medibleDetalle: 'Un solo mes medido: falta el segundo para la alarma',
      alPulsar: verPerdida, ir: 'Ver cuáles' }),
    tarjetaKpi({ icono: 'medidor', etiqueta: 'Horas imputadas', valor: fmt.pct(d.imputacion?.pct, 1), num: d.imputacion?.pct, estado: 'gris', mejorSi: 'alto',
      contexto: `${d.imputacion?.periodo || ''} · por debajo del 70 % el margen no es fiable`, umbral: UMBRALES.horas_imputadas, fuente: { texto: 'ClickUp' } }),
    tileFact || null);
  return [cifra, tarjetas];
}

/** Concentración de la cuota (48 §3): el mayor, del 2.º al 5.º, del 6.º al 10.º y el resto, sobre la cuota recurrente que
 *  factura Sofía (los clientes con línea de octubre: 64.351 €, la misma base que Finanzas). */
function panelConcentracion(filas) {
  const cs = filas.filter(f => f.cuota_en_facturacion && f.cuota > 0).sort((a, b) => b.cuota - a.cuota);
  const T = cs.reduce((a, f) => a + f.cuota, 0);
  if (!T) return '';
  const suma = (i, j) => cs.slice(i, j).reduce((a, f) => a + f.cuota, 0);
  const uno = (100 * suma(0, 1)) / T, cinco = (100 * suma(0, 5)) / T, diez = (100 * suma(0, 10)) / T;
  const empate = cs.filter(f => f.cuota === cs[0].cuota).length;
  return panel({ titulo: 'Concentración de la cuota', icono: 'users', sub: `${cs.length} clientes con línea de octubre · ${fmt.eur(T)} (la base de Finanzas)` },
    h('div', { class: 'cuerpo pila' },
      tarjetaKpi({ icono: 'users', etiqueta: 'El cliente que más pesa', valor: pctS(uno, 1), unidad: 'de la cuota', num: uno, estado: ESTADO.concentracion(uno), mejorSi: 'bajo',
        contexto: `${empate > 1 ? `${empate} clientes empatan a ${fmt.eur(cs[0].cuota)}` : `${cs[0].nombre}, ${fmt.eur(cs[0].cuota)}`} · los 5 mayores: ${pctS(cinco, 1)} · los 10 mayores: ${pctS(diez, 1)} (sin umbral fiable: no colorean)`, umbral: UMBRALES.concentracion, fuente: { texto: 'Airtable de octubre' } }),
      barraApilada({ etiqueta: 'Reparto de la cuota', formato: v => fmt.eur(v), partes: [
        { valor: suma(0, 1), texto: 'El mayor', estado: 'azul' }, { valor: suma(1, 5), texto: 'Del 2.º al 5.º' }, { valor: suma(5, 10), texto: 'Del 6.º al 10.º' }, { valor: suma(10), texto: `El resto (${Math.max(0, cs.length - 10)})`, estado: 'gris' }] })));
}

/** Valor de vida y recuperación de la captación (48 §3). Tomás: el de todos los clientes (también los que se fueron) y el coste
 *  de captar de Ventas de RO; los demás: el valor de vida hasta hoy de los clientes que siguen. */
function panelValorVida({ filas, dirD, ventasD }) {
  const k = dirD?.kpi || {};
  const vv = filas.map(f => f.cuota_valor_vida).filter(x => x > 0).sort((a, b) => a - b);
  const medianaHoy = vv.length ? (vv.length % 2 ? vv[(vv.length - 1) / 2] : (vv[vv.length / 2 - 1] + vv[vv.length / 2]) / 2) : null;
  const tiles = [];
  if (k.ltv_media) {
    tiles.push(tarjetaKpi({ icono: 'star', etiqueta: 'Valor de vida medio', valor: fmt.eur(k.ltv_media), num: k.ltv_media,
      contexto: `Lo cobrado a cada cliente desde el primer día, también a los que se fueron · mediana ${fmt.eur(k.ltv_mediana)} · los que se van duran ${fmt.num(k.vida_baja_mediana, 1)} meses (mediana)`, fuente: { texto: 'facturas de Holded' } }));
  } else if (medianaHoy) {
    tiles.push(tarjetaKpi({ icono: 'star', etiqueta: 'Valor de vida de los clientes de hoy', valor: fmt.eur(medianaHoy), unidad: 'mediana', num: medianaHoy,
      contexto: `Lo cobrado hasta hoy a los ${vv.length} clientes que siguen (no cuenta a los que se fueron)`, fuente: { texto: 'Airtable y Holded' } }));
  }
  const sep = ventasD?.meses?.['2026-09'];
  const cac = sep?.inversion && sep?.firmados ? Math.round(sep.inversion / sep.firmados) : null;   // en euros enteros, como se enseña (735 €)
  if (cac && k.mb) {
    const cuotaNueva = sep.cuota_firmada && sep.firmados ? sep.cuota_firmada / sep.firmados : k.cuota_media;
    const meses = cac / (cuotaNueva * (k.mb / 100));
    const veces = (k.ltv_media * (k.mb / 100)) / cac;
    tiles.push(tarjetaKpi({ icono: 'clock', etiqueta: 'Meses para recuperar la captación', valor: fmt.num(meses, 1), unidad: 'meses', num: meses, estado: 'gris', mejorSi: 'bajo',
      contexto: `Coste de captar en septiembre ${fmt.eur(cac)} (solo publicidad: ${fmt.eur(sep.inversion)} ÷ ${sep.firmados} firmados) ÷ (cuota nueva ${fmt.eur(cuotaNueva)} × margen bruto ${pctS(k.mb, 1)})`,
      umbral: UMBRALES.recuperacion, fuente: { texto: 'Ventas de RO y cierre de Sofía', href: '#/ventas-ro' } }));
    tiles.push(tarjetaKpi({ icono: 'sube', etiqueta: 'Valor de vida en margen ÷ coste de captar', valor: fmt.num(veces, 1), unidad: 'veces', num: veces, estado: 'gris', mejorSi: 'alto',
      contexto: `${fmt.eur(k.ltv_media)} × ${pctS(k.mb, 1)} de margen bruto ÷ ${fmt.eur(cac)} · en ingresos, ${fmt.num(k.ltv_media / cac, 1)} veces`,
      umbral: UMBRALES.ltv_cac }));
  }
  if (!tiles.length) return '';
  return panel({ titulo: 'Valor de vida y recuperación', icono: 'star', sub: cac ? 'La captación se recupera rápido; lo que falla es cuánto dura y cuánto se rebaja el cliente.' : 'Lo cobrado a cada cliente desde su alta.' },
    h('div', { class: 'cuerpo pila' }, ...tiles));
}

/** Cohortes de retención (48 §4.1): filas = mes de alta, columnas = meses de vida, % de clientes o % de la cuota de entrada. */
function panelCohortes(c, ctx) {
  const cols = Array.from({ length: c.columnas || 13 }, (_, i) => `Mes ${i}`);
  const MES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
  const etq = m => `${MES[Number(m.slice(5, 7)) - 1]} ${m.slice(2, 4)}`;   // «jul 24»: siempre con el año
  const filasDe = L => (L.filas || []).map(r => ({ etiqueta: etq(r.m), n: r.n, valores: r.pct }));
  const m12 = c.clientes.media?.[12];
  return panel({ titulo: 'Cuántos se quedan, por mes de alta', icono: 'users',
    sub: `Cada fila, los clientes que entraron ese mes; cada columna, los meses que llevan. ${m12 !== null && m12 !== undefined ? `De media, al año sigue el ${fmt.pct(m12)} de los clientes.` : ''}` },
    h('div', { class: 'cuerpo pila' },
      mapaCalor({ clave: 'dinero-cohortes', columnas: cols, titulo: 'Retención por mes de alta', vistas: [
        { valor: 'clientes', texto: '% de clientes', icono: 'users', filas: filasDe(c.clientes), media: c.clientes.media, nota: c.clientes.texto },
        { valor: 'cuota', texto: '% de la cuota de entrada', icono: 'euro', filas: filasDe(c.cuota_entrada || {}), media: c.cuota_entrada?.media, nota: c.cuota_entrada?.texto }] }),
      h('p', { class: 'sub' }, `${c.regla} ${c.fuente}. Último mes cerrado: ${etq(c.ultimo_mes)}.`),
      h('p', { class: 'kpi-pie' }, h('span', {}, 'Escala de un solo color, sin rojo ni verde · cómo se dibuja: '), enlaceFuente(FUENTES.chartmogul_coh.href, FUENTES.chartmogul_coh.fuente)),
      h('div', { class: 'fila' }, ctx?.veModulo?.('en-rojo') ? h('a', { class: 'bt mini', href: '#/en-rojo' }, icono('alert', { clase: 's' }), 'Ver los clientes en riesgo hoy') : null,
        ctx?.veModulo?.('finanzas') ? h('a', { class: 'bt mini', href: '#/finanzas' }, icono('users', { clase: 's' }), 'Ver quién se fue cada mes (Finanzas)') : null)));
}

export default {
  id: 'dinero-cliente',
  titulo: 'Dinero por cliente',
  grupo: 'Dinero',
  puestos_que_lo_ven: { direccion: 'todo', finanzas_direccion: 'todo', operaciones: 'todo', proyectos: 'todo', administracion: 'todo', account: 'suyo', jefa_publicidad: 'resumen', trafficker: 'resumen' },
  // R12 (A-A2): lo facturado se mira por meses enteros; horas y rentabilidad son de septiembre (no cambian con el periodo)
  usa_periodo: params => params?.[0] === 'cierre-septiembre' ? false : ['mes', 'mes_ant', 'trim', 'anio', 'medida'],
  async render(contenedor, ctx) { await pintar(contenedor, ctx); },
};
