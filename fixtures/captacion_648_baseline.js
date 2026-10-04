function plegablePaid411(titulo, ...contenido) {
  return h('details', { class: 'que-es', 'data-paid-detalle': '411', style: { minWidth: '0' } },
    h('summary', { style: { minHeight: '44px', display: 'flex', alignItems: 'center', gap: S[2] } }, titulo),
    h('div', { class: 'pila', style: { marginTop: S[2], gap: S[2], minWidth: '0' } }, ...contenido));
}

// sentinel: function cabeceraPaid411(

function cifras(filas, d) {
  const activas = filas.filter(c => c.meta_activa);
  const conDinero = filas.filter(c => c.dinero);
  const tiendas = filas.filter(esTienda);
  const deLeads = filas.filter(c => !esTienda(c));       // leads de la casa: sin tiendas online
  const juzg = activas.filter(c => !esTienda(c) && c.cpl_resumen?.ref !== null && c.cpl_resumen?.ref !== undefined);
  const techo = d.parametros.techo_cpl;
  // Misma definición que Salud del CRM; fuera las subcuentas sin uso (no son fugas: GAC) y las que no tienen dato.
  const conGhl = activas.filter(c => c.ghl?.conectado && c.despacho?.leads_meta_7d && !c.despacho.subcuenta_sin_uso && c.despacho.leads_ghl_7d !== null && c.despacho.leads_ghl_7d !== undefined);
  const sumMeta = conGhl.reduce((s, c) => s + (c.despacho.leads_meta_7d || 0), 0);
  const sumGhl = conGhl.reduce((s, c) => s + (c.despacho.leads_ghl_7d || 0), 0);
  const suma = (k, v) => conDinero.reduce((s, c) => s + ((c[k] || {})[v] || 0), 0);
  return {
    activas, conDinero,
    criticos: filas.filter(c => c.gravedad === 'critico'),          // V2: gravedad del cliente (verdad única)
    atencion: filas.filter(c => c.gravedad === 'atencion'),
    pubUrgente: filas.filter(c => c.severidad === 'critico'),       // estado de la cuenta de publicidad
    juzg, enTecho: juzg.filter(c => c.cpl_resumen.ref <= techo),
    conObjetivo: activas.filter(c => c.objetivo?.cargado),
    alarmaCita: filas.filter(c => c.coste_por_cita?.alarma_100),
    gasto7: suma('gasto', '7d'), gasto7p: suma('gasto', '7d_prev'), gastoMesAnt: suma('gasto', 'mes_anterior'),
    leads7: deLeads.reduce((s, c) => s + (c.leads?.['7d'] || 0), 0), leads7p: deLeads.reduce((s, c) => s + (c.leads?.['7d_prev'] || 0), 0),
    tiendas, conversionesTienda7: tiendas.reduce((s, c) => s + (c.leads?.['7d'] || 0), 0),
    pctCrm: null, comparacionRecuentos: conGhl.length > 0, sumMeta, sumGhl, conGhl,
    cansadas: filas.reduce((s, c) => s + (c.anuncios?.cansadas || 0), 0),
    vigilar: filas.reduce((s, c) => s + (c.anuncios?.vigilar || 0), 0),
    rechazados: filas.reduce((s, c) => s + (c.anuncios?.problemas_total || 0), 0),
    paradas: activas.filter(c => (c.gasto?.ayer === 0) || (c.cuenta_meta?.ultimo_dia_con_gasto && c.cuenta_meta.ultimo_dia_con_gasto < d.datos_hasta)),
  };
}


// sentinel: // ================================================================== LISTA

function pEquipo(el, ctx, d, filas) {
  const por = new Map();
  for (const c of filas) {
    const t = c.equipo?.trafficker || '—';
    if (!por.has(t)) por.set(t, []);
    por.get(t).push(c);
  }
  const [verde, ambar] = d.parametros.rojos_trafficker;
  const filasT = [...por.entries()].map(([t, cs]) => {
    const Ct = cifras(cs, d);
    return {
      id: t, nombre: t === '—' ? 'Sin trafficker asignado' : nombre(d, t), cuentas: cs.length, activas: Ct.activas.length, cp: (d.carteras_publicidad || {})[t] || null,
      rojos: Ct.criticos.length, atencion: Ct.atencion.length, gasto7: Ct.conDinero.length ? Ct.gasto7 : null, gastoMes: Ct.conDinero.length ? Ct.gastoMesAnt : null,
      techo: Ct.juzg.length ? Math.round(Ct.enTecho.length / Ct.juzg.length * 100) : null, techoTxt: Ct.juzg.length ? `${Ct.enTecho.length} de ${Ct.juzg.length}` : '—',
      cansadas: Ct.cansadas, rechazados: Ct.rechazados, objetivos: `${Ct.conObjetivo.length} de ${Ct.activas.length}`,
    };
  }).sort((a, b) => b.rojos - a.rojos || b.activas - a.activas);
  const total = cifras(filas, d);

  const cifrasEquipo416=tiles([
    tile({ icono: 'eq', etiqueta: 'Traffickers con 5 o más cuentas en rojo', valor: filasT.filter(x => x.id !== '—' && x.rojos >= ambar + 1).length, unidad: `de ${filasT.filter(x => x.id !== '—').length}`,
      estado: filasT.some(x => x.id !== '—' && x.rojos > ambar) ? 'rojo' : filasT.some(x => x.id !== '—' && x.rojos > verde) ? 'ambar' : 'verde',
      contexto: `Verde ≤ ${verde} · ámbar ${verde + 1}-${ambar} · rojo ≥ ${ambar + 1} cuentas críticas por trafficker`, medible: 'hoy', frescura: fuenteDe(d, 'meta') }),
    total.conDinero.length ? tile({ icono: 'cartera', etiqueta: 'Inversión gestionada · septiembre', valor: eur(total.gastoMesAnt), comparacion: { texto: `${eur(total.gasto7)} en los últimos 7 días` },
      contexto: 'Solo Meta. Google Ads va aparte (muestra manual) hasta la clave de Windsor.', medible: 'medias', medibleDetalle: 'Falta Google Ads y TikTok', frescura: fuenteDe(d, 'meta') }) : null,
    tile({ icono: 'flag', etiqueta: 'Cuentas paradas sin saberlo', valor: total.paradas.length, unidad: `de ${total.activas.length} activas`,
      estado: total.paradas.length ? 'rojo' : 'verde', contexto: 'Con pauta en la semana y sin gasto ayer o desde antes del último día con datos.', medible: 'hoy', frescura: fuenteDe(d, 'meta') }),
    tile({ icono: 'rocket', etiqueta: 'Arranques con ganador en el mes 1', valor: (() => { const n = filas.filter(c => c.nuevo && c.meta_activa); return n.length ? `${n.filter(c => c.anuncios?.ganadoras).length} de ${n.length}` : null; })(),
      estado: 'gris', contexto: 'En el arranque, 3 contactos o más a 45 € o menos.', medible: 'hoy', frescura: fuenteDe(d, 'anuncios') }),
  ].filter(Boolean));

  el.append(h('section', {'data-paid-equipo':'416',style:{minWidth:'0'}},
    h('style',{},'[data-paid-equipo="416"] .tabla-scroll{overflow-x:auto;max-width:100%}[data-paid-equipo="416"] table.densa{table-layout:fixed;width:100%;min-width:940px}[data-paid-equipo="416"] table.densa th,[data-paid-equipo="416"] table.densa td{padding:5px 6px;font-size:13px;line-height:1.3;overflow-wrap:normal;word-break:normal}[data-paid-equipo="416"] table.densa th:first-child{width:180px}[data-paid-equipo="416"] table.densa th:nth-child(2){width:160px}[data-paid-equipo="416"] table.densa th{white-space:normal}[data-paid-equipo="416"] table.densa td{height:44px}[data-paid-equipo="416"] table.densa td:first-child>span{white-space:normal}'),
    panel({ titulo: 'Cuentas por trafficker', icono: 'eq', sub: 'Pulsa una fila para ver sus cuentas. Referencia de coste anterior; no objetivo acordado.' },
    tablaApilable({
      filas: filasT,
      columnas: [
        { clave: 'nombre', titulo: 'Trafficker', principal: true, celda: x => h('span', { class: 'fila', style: { gap: S[2], flexWrap: 'nowrap' } }, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(x.nombre)), x.nombre) },
        // V2 (B-A3): la misma cartera con nombre que Mi día y Personas (carteras_publicidad)
        { clave: 'cuentas', titulo: 'Cartera', num: true, celda: x => (x.cp ? h('span', { style: { display: 'inline-grid', justifyItems: 'end' } }, `${x.cp.cartera} clientes${x.cp.apoyo ? ` + ${x.cp.apoyo} de apoyo` : ''}`, h('small', { class: 'sub' }, `${x.cp.con_meta} con Meta · ${x.cp.meta_encendida} encendidas`)) : `${x.activas} encendidas de ${x.cuentas}`) },
        { clave: 'rojos', titulo: 'Críticos', num: true, celda: x => chipEstado('gris',`${x.rojos}${x.atencion?` · +${x.atencion} a vigilar`:''}`) },
        { clave: 'techo', titulo:'Ref. coste', num: true, celda: x => h('span',{title:`Referencia anterior ${d.parametros.techo_cpl} € · no objetivo: ${x.techoTxt}`},x.techoTxt) },
        { clave: 'gasto7', titulo: 'Gasto 7 d', num: true, celda: x => (x.gasto7 === null ? candado('—') : eur(x.gasto7)) },
        { clave: 'gastoMes', titulo: 'Septiembre', num: true, celda: x => (x.gastoMes === null ? candado('—') : eur(x.gastoMes)) },
        { clave: 'cansadas', titulo: 'Señales / rechazos', num: true, celda: x => h('span',{title:`${x.cansadas} anuncios con señal de cansada · ${x.rechazados} rechazados`},`${x.cansadas} / ${x.rechazados}`) },
        { clave: 'objetivos', titulo: 'Objetivos', num: true, celda:x=>h('span',{title:'Cuentas con objetivo cargado / activas; no acredita objetivo ratificado ni cumplimiento.'},x.objetivos) },
      ],
      alPulsar: x => { try { sessionStorage.setItem('captacion.filtro', JSON.stringify({ trafficker: x.id })); } catch { /* */ } ctx.navegar(`captacion/~trafficker/${x.id}`); },
      etiquetaFila: x => `${x.nombre}: ${fmt.plural(x.rojos, 'cuenta crítica', 'cuentas críticas')}. Ver sus cuentas`,
    }))));
  el.append(plegablePaid411('Cifras y referencias por trafficker',cifrasEquipo416,
    h('p',{class:'sub'},`Ref. coste: comparación anterior con ${d.parametros.techo_cpl} €; no objetivo acordado. Responsable: tabla de asignaciones, no el «PM» escrito a mano de la Torre. Señales / rechazos conserva los recuentos de anuncios; no confirma fatiga actual.`)));

  // comparativa por nicho
  const nichos = new Map();
  for (const c of filas.filter(x => x.meta_activa)) {
    const k = c.nicho || 'Sin nicho';
    if (!nichos.has(k)) nichos.set(k, []);
    nichos.get(k).push(c);
  }
  const filasN = [...nichos.entries()].map(([k, cs]) => {
    const g = cs.filter(c => c.dinero).reduce((s, c) => s + (c.gasto?.['7d'] || 0), 0), l = cs.reduce((s, c) => s + (c.leads?.['7d'] || 0), 0);
    return { nicho: k, cuentas: cs.length, nombres: cs.map(c => c.nombre).join(', '), leads: l, cpl: cs.some(c => c.dinero) && l ? g / l : null, dinero: cs.some(c => c.dinero) };
  }).sort((a, b) => b.leads - a.leads);
  el.append(plegablePaid411('Comparativa por nicho · 7 días',
    panel({ titulo: 'Comparativa por nicho · 7 días', icono: 'capas', sub: 'Solo cuentas con pauta activa. El nicho sale de la descripción del cliente.' },
      tablaApilable({ filas: filasN, columnas: [
        { clave: 'nicho', titulo: 'Nicho', principal: true, celda: x => h('span', { style: { display: 'grid' } }, h('b', {}, x.nicho), h('small', { class: 'sub' }, x.nombres)) },
        { clave: 'cuentas', titulo: 'Cuentas', num: true },
        { clave: 'leads', titulo: 'Leads', num: true, celda: x => num(x.leads) },
        { clave: 'cpl', titulo: 'Coste registrado · unidad pendiente', num: true, celda: x => (x.dinero ? eur(x.cpl) : candado('—')) },
      ] }))));
  el.append(plegablePaid411('Auditoría semanal',pAuditoria(ctx, d, filas)));
}


// sentinel: /** Auditoría semanal:

function tAnuncios(el, ctx, d, c) {
  const a = c.anuncios;
  if (!a) { el.append(vacio({ icono: 'spark', titulo: 'Sin anuncios que mirar', texto: c.meta_activa ? 'No se pudieron leer los anuncios de esta cuenta.' : 'La cuenta no tiene pauta activa: no hay anuncios con impresiones en 7 días.' })); return; }
  el.append(tiles([
    tile({ icono: 'baja', etiqueta: 'Cansadas', valor: a.cansadas, estado: a.cansadas ? 'rojo' : 'verde', contexto: 'Dos señales a la vez', medible: 'hoy' }),
    tile({ icono: 'ojo', etiqueta: 'Con una señal', valor: a.vigilar, estado: a.vigilar ? 'ambar' : 'verde', contexto: 'Vigilar: una señal sola no dispara', medible: 'hoy' }),
    tile({ icono: 'star', etiqueta: 'Ganadoras', valor: a.ganadoras, estado: '', contexto: 'Gasto ≥ 10 veces el objetivo con coste ≤ objetivo', medible: 'hoy' }),
    tile({ icono: 'alert', etiqueta: 'Rechazados o con problemas', valor: a.problemas_total, estado: a.problemas_total ? 'rojo' : 'verde', contexto: `${a.aprendizaje_limitado} de ${a.conjuntos_con_dato} conjuntos en aprendizaje limitado`, medible: 'hoy' }),
  ]));
  if (!ctx.soloLectura && ctx.nivel !== 'resumen') el.append(panel({ titulo: 'Pedir nuevas a producción', icono: 'send', sub: 'Con la cansada adjunta y el brief ya escrito.' }, h('div', { class: 'cuerpo' }, formPedido(ctx, d, c))));
  el.append(panel({ titulo: 'Anuncios · 7 días', icono: 'spark', sub: `${a.total_7d} con impresiones; ${a.sin_autor} sin iniciales de autor (desde el próximo lanzamiento)` },
    tablaApilable({ filas: a.anuncios, columnas: [
      { clave: 'nombre', titulo: 'Anuncio', principal: true, celda: x => h('span', { style: { display: 'grid' } }, h('b', {}, x.nombre), h('small', { class: 'sub' }, distingue(x))) },
      { clave: 'e', titulo: 'Estado', celda: x => h('span', { style: { display: 'grid', gap: S[1] } }, chipEstado(x.cansada ? 'rojo' : x.vigilar ? 'ambar' : x.ganadora ? 'verde' : 'gris', x.cansada ? 'Cansada' : x.vigilar ? 'Vigilar' : x.ganadora ? 'Ganadora' : 'Normal'), x.senales?.length ? h('small', { class: 'sub' }, x.senales.join(' + ')) : null) },
      { clave: 'f', titulo: 'Frecuencia', num: true, celda: x => (x.frecuencia_7d ? num(x.frecuencia_7d, 1) : '—') },
      { clave: 'ctr', titulo: '% de clics', num: true, celda: x => (x.ctr_7d === undefined ? '—' : `${num(x.ctr_7d, 2)} %${x.ctr_previo ? ` (antes ${num(x.ctr_previo, 2)})` : ''}`) },
      { clave: 'l', titulo: 'Leads 7 d', num: true, celda: x => num(x.leads_7d ?? null) },
      { clave: 'c', titulo: 'Coste registrado · unidad pendiente', num: true, celda: x => (!c.dinero || x.cpl_7d === undefined && x.cpl_30d === undefined ? candado('—') : x.cpl_7d ? eur(x.cpl_7d) : x.cpl_30d ? `${eur(x.cpl_30d)} (30 d)` : '—') },
      { clave: 'autor', titulo: 'Autor', celda: x => nombre(d, x.autor) || h('span', { class: 'dim' }, 'sin autor') },
      { clave: 'ir', titulo: 'Abrir', ordenable: false, celda: x => (x.enlace ? h('a', { class: 'bt mini', href: x.enlace, target: '_blank', rel: 'noopener', title: 'Abre el anuncio en el Administrador de anuncios; si Meta no lo selecciona, abre la cuenta' }, icono('ext'), 'Abrir en Meta') : '—') },
    ], vacio: { titulo: 'Ningún anuncio con impresiones esta semana' } })));
  if (a.problemas?.length) {
    el.append(panel({ titulo: 'Rechazados o con problemas', icono: 'alert' }, h('div', { class: 'cuerpo' }, listaConIcono(a.problemas.map(p => ({ icono: 'alert', estado: p.estado === 'DISAPPROVED' ? 'rojo' : 'ambar', texto: `${p.nombre} · ${p.estado === 'DISAPPROVED' ? 'rechazado' : 'con problemas'}`, extra: `desde ${fDiaRO(p.desde)}` }))))));
  }
}


// sentinel: function tMetas(
