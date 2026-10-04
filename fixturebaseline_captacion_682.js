function pCreatividades(el, ctx, d, filas) {
  const ads = [];
  for (const c of filas) for (const a of c.anuncios?.anuncios || []) ads.push({ ...a, cliente: c.nombre, cliente_id: c.cliente_id, dinero: c.dinero, logo: c.logo,
    estado: a.cansada ? 'cansada' : a.vigilar ? 'vigilar' : a.ganadora ? 'ganadora' : 'normal' });
  const prob = filas.flatMap(c => (c.anuncios?.problemas || []).map(p => ({ ...p, cliente: c.nombre, cliente_id: c.cliente_id })));
  const cnt = k => ads.filter(a => a.estado === k).length;
  const chips = chipsFiltro({
    etiqueta: 'Estado', clave: 'captacion.anuncios',
    opciones: [{ valor: 'aviso', texto: 'Con señales', icono: 'alert', cuenta: cnt('cansada') + cnt('vigilar'), cuentaEstado: 'gris' },
      { valor: 'cansada', texto: 'Cansadas', icono: 'baja', cuenta: cnt('cansada'), cuentaEstado: 'gris' },
      { valor: 'ganadora', texto: 'Ganadoras', icono: 'star', cuenta: cnt('ganadora') }, { valor: '', texto: 'Todas', cuenta: ads.length }],
    alCambiar: () => pintar(),
  });
  const caja = h('div');
  const pintar = () => {
    if(ctx.vigente?.()===false){caja.replaceChildren();return;}
    const v = chips.valor();
    const base = ads.filter(a => !v || (v === 'aviso' ? ['cansada', 'vigilar'].includes(a.estado) : a.estado === v));
    caja.replaceChildren(tablaDensa({
      filas: base, orden: { clave: 'frecuencia_7d', dir: 'desc' },
      buscar: { campos: ['nombre', 'cliente', 'campana'], placeholder: 'Buscar anuncio o cliente' },
      filtros: [{ clave: 'cliente', titulo: 'Cliente' }],
      columnas: [
        { clave: 'nombre', titulo: 'Anuncio', principal: true, celda: a => h('span', { title:`${a.nombre||'Sin nombre'} · ${a.cliente} · ${distingue(a)}`, style: { display: 'grid', gap: S[1] } }, h('b', {}, a.nombre || '—'), h('small', { class: 'sub' }, a.cliente)) },
        { clave: 'estado', titulo: 'Estado', celda: a => h('span', { style: { display: 'grid', gap: S[1] } },
          chipEstado('gris', a.estado === 'cansada' ? 'Cansada' : a.estado === 'vigilar' ? 'Vigilar' : a.estado === 'ganadora' ? 'Ganadora' : 'Normal'),
          a.senales?.length ? h('span', { title:a.senales.join(' + '),class:'sub' }, `${a.senales.length} ${a.senales.length===1?'señal':'señales'}`) : null) },
        { clave: 'frecuencia_7d', titulo: 'Frec.', tituloCompleto:'Frecuencia de impresión · 7 días', num: true, celda: a => (typeof a.frecuencia_7d!=='number'||!Number.isFinite(a.frecuencia_7d)||a.frecuencia_7d<0 ? '—' : h('span',{title:'Frecuencia registrada en la copia; referencia sin evaluación de fatiga.'},chipEstado('gris', num(a.frecuencia_7d, 1), { punto: false }))) },
        { clave: 'ctr_7d', titulo: 'CTR', tituloCompleto:'Porcentaje de clics · 7 días; caída frente al periodo anterior', num: true, celda: a => (typeof a.ctr_7d!=='number'||!Number.isFinite(a.ctr_7d)||a.ctr_7d<0 ? '—' : h('span', { style: NOWRAP }, `${num(a.ctr_7d, 2)} %`, a.caida_ctr_pct !== null && a.caida_ctr_pct !== undefined ? h('small', { class: 'sub' }, ` (${a.caida_ctr_pct > 0 ? '−' : '+'}${num(Math.abs(a.caida_ctr_pct))} %)`) : null)) },
        { clave: 'leads_7d', titulo: 'Meta 7d', tituloCompleto:'Contador Meta · 7 días; tipo de evento y cualificación pendientes', num: true, celda: a => a.leads_7d==null?'—':num(a.leads_7d) },
        { clave: 'cpl_7d', titulo: 'Coste†', tituloCompleto:'Coste registrado · unidad pendiente; no acredita CPL real', num: true, celda: a => {
          if(!a.dinero)return candado('—');
          const valido=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0;
          return valido(a.cpl_7d)?h('span',{title:'Referencia de coste registrada · 7 días; unidad pendiente.'},`${eur(a.cpl_7d)}†`):valido(a.cpl_30d)?h('span',{title:'Referencia de coste registrada · 30 días; unidad pendiente.'},`${eur(a.cpl_30d)}† · 30d`):'—';
        } },
        { clave: 'ir', titulo: 'Abrir', ordenable: false, celda: a => (a.enlace ? h('a', { class: 'bt mini', href: a.enlace, target: '_blank', rel: 'noopener' }, icono('ext'), 'Meta') : '—') },
        { clave: 'autor', titulo: 'Autor', celda: a => (a.autor ? nombre(d, a.autor) : h('span', { class: 'dim', title: 'Iniciales del autor en el nombre del anuncio desde el próximo lanzamiento' }, 'sin autor')) },
      ],
      alPulsar: a => {if(ctx.vigente?.()!==false)ctx.navegar(`captacion/${a.cliente_id}`);},
      etiquetaFila: a => `${a.nombre} de ${a.cliente}: ${a.estado}. Abrir tarjeta del cliente`,
      vacio: { titulo: 'Ningún anuncio con estas señales', porque: 'No hay anuncios en este filtro de la copia disponible; no acredita ausencia de señales ni necesidad de cambios.', celebrar: false },
    }));
  };
  pintar();
  el.append(panel({ titulo: 'Anuncios de las cuentas activas · 7 días', icono: 'spark', sub: 'Señales de la copia; abre una cuenta para revisar fuentes y acciones.' },
    h('div', { class: 'cuerpo' },typeof matchMedia==='function'&&matchMedia('(max-width:640px)').matches?h('details',{class:'que-es'},h('summary',{},'Filtros de esta vista'),chips):chips), caja,h('details',{class:'que-es',style:{padding:'8px 16px'}},h('summary',{},'Reglas de referencia'),h('p',{},'Cansada: dos señales a la vez. Ganadora: gasto ≥ 10 veces el objetivo con coste ≤ objetivo; regla anterior de arranque: 3 contactos a ≤ 45 €. Son etiquetas de la copia, pendientes de contraste; no acreditan rendimiento actual ni cualificación.')),h('p',{class:'sub',style:{padding:'8px 16px'}},`Muestra parcial de anuncios recibidos; no inventario completo. Lectura de anuncios: ${lecturaAnunciosPaid4(d,ctx.hoy||hoyMadrid())||'sin fecha válida'}. Antigüedad del creativo: sin dato. Señales de la copia, pendientes de contraste. † Coste registrado con unidad pendiente; no CPL real ni compras. Meta7d no acredita cualificación. Abre la cuenta para revisar fuentes y acciones.`)));
  el.lastElementChild?.setAttribute('data-paid-creatividades-425','');
  el.append(h('style',{},`@media(min-width:641px){[data-paid-creatividades-425] table.densa{table-layout:fixed;width:100%;min-width:900px}[data-paid-creatividades-425] table.densa th:first-child{width:25%}[data-paid-creatividades-425] table.densa th,[data-paid-creatividades-425] table.densa td{padding-left:6px;padding-right:6px;overflow-wrap:anywhere}[data-paid-creatividades-425] table.densa th button{padding-left:6px;padding-right:6px;white-space:normal}[data-paid-creatividades-425] table.densa td .chip{max-width:100%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}`));
  const lim = filas.filter(c => c.anuncios?.conjuntos_con_dato).map(c => ({ ...c, lim: c.anuncios.aprendizaje_limitado, con: c.anuncios.conjuntos_con_dato }));
  el.append(h('div', { class: 'dos' },
    panel({ titulo: 'Rechazados o con problemas', icono: 'alert', sub: 'Señales de rechazo guardadas; fechas y cobertura por contrastar.' },
      tablaApilable({ filas: prob, columnas: [
        { clave: 'nombre', titulo: 'Anuncio', principal: true, celda: p => h('span', { style: { display: 'grid' } }, h('b', {}, p.nombre), h('small', { class: 'sub' }, p.cliente)) },
        { clave: 'estado', titulo: 'Estado', celda: p => chipEstado(p.estado === 'DISAPPROVED' ? 'rojo' : 'ambar', p.estado === 'DISAPPROVED' ? 'Rechazado' : 'Con problemas') },
        { clave: 'desde', titulo: 'Desde', celda: p => fDiaRO(p.desde) },
        { clave: 'motivo', titulo: 'Motivo de Meta', celda: p => h('span', { class: 'sub' }, (p.motivo || 'Sin motivo en la respuesta').slice(0, 140)) },
      ], vacio: { titulo: 'Sin rechazos en esta copia', texto: 'La cobertura parcial no acredita ausencia de problemas actuales.',celebrar:false } })),
    panel({ titulo: 'Conjuntos en aprendizaje limitado', icono: 'medidor', sub: 'Recuento de la copia; fechas y cobertura pendientes de contraste.' },
      tablaApilable({ filas: lim, columnas: [
        { clave: 'nombre', titulo: 'Cliente', principal: true, celda: c => h('span', { class: 'celda-cli' }, logoCliente(c), c.nombre) },
        { clave: 'lim', titulo: 'Limitados', num: true, celda: c => { const p = Math.round(c.lim / c.con * 100); return chipEstado('gris', `${c.lim} de ${c.con} · ${p} %`); } },
      ], vacio: { titulo: 'Meta no da el dato de aprendizaje', texto: 'Ningún conjunto activo trae «learning_stage_info» en estas cuentas.' } }))));
}

// ------------------------------------------------------------------ pestaña · el despacho (M6 · D-45, D-46)
function pDespacho(el, ctx, d, filas) {
  const f = filtroPendiente();
  const conGhl = filas.filter(c => c.despacho && (c.ghl?.conectado || c.meta_activa));
  const filasT = conGhl.map(c => { const m=medirEmbudoCRM(c.ghl,(d.fuentes||[]).find(x=>x.id==='ghl'),ctx.hoy||hoyMadrid()); return ({
    ...c, llegan: null, estanc:m.parados,cohorte:m.cohorte,sinEstado:m.sinEstado,
    asis:m.asistencia,citas:m.agendadas,lecturaCRM:m,
    fuga: false, // Sin unión por identidad/cohorte: el ratio legado no prueba pérdidas.
    sinGhl: !c.ghl?.conectado,
  }); });
  const chips = chipsFiltro({
    etiqueta: 'Mirar', clave: f ? null : 'captacion.despacho', valor: f?.fuga ? '' : undefined,
    opciones: [{ valor: '', texto: 'Todas', cuenta: filasT.length },
      { valor: 'estanc', texto: 'Estancados > 72 h', icono: 'clock', cuenta: filasT.filter(x => x.estanc).length, cuentaEstado:'ambar' },
      { valor: 'sinestado', texto: 'Citas sin estado', icono: 'cal', cuenta: filasT.filter(x => x.sinEstado).length, cuentaEstado:'ambar' },
      { valor: 'sincita', texto:'Sin avance de cita observado', icono: 'alert', cuenta: filasT.filter(x => x.cuello?.includes('seguimiento') && x.despacho?.sin_avance_90d === true).length },
      { valor: 'singhl', texto: 'Sin GHL', icono: 'base', cuenta: filasT.filter(x => x.sinGhl).length }],
    alCambiar: () => pintar(),
  });
  const caja = h('div');
  const pintar = () => {
    if(ctx.vigente?.()===false){caja.replaceChildren();return;}
    const elegido = chips.valor(), v=['estanc','sinestado','singhl','sincita'].includes(elegido)?elegido:'';
    const base = filasT.filter(x => !v || (v === 'estanc' && x.estanc) || (v === 'sinestado' && x.sinEstado) || (v === 'singhl' && x.sinGhl)
      || (v === 'sincita' && x.cuello?.includes('seguimiento') && x.despacho?.sin_avance_90d === true));
    caja.replaceChildren(tablaDensa({
      filas: base, orden: { clave: 'llegan', dir: 'asc' },
      buscar: { campos: ['nombre'], placeholder: 'Buscar cliente' },
      columnas: [
        { clave: 'nombre', titulo: 'Cliente', principal: true, celda: c => h('span', { class: 'celda-cli' }, logoCliente(c), c.nombre) },
        { clave: 'llegan', titulo: 'Meta / CRM', tituloCompleto:'Recuentos independientes Meta y CRM · 7 días; sin unión por identidad', num: true, celda: c => (c.sinGhl ? chipEstado('gris', 'sin GHL') : h('span', { title:`Recuentos de 7 días independientes, sin unión por identidad${c.despacho.subcuenta_sin_uso?' · uso de subcuenta por confirmar':''}.`, style:NOWRAP }, `${c.despacho.leads_meta_7d==null?'—':num(c.despacho.leads_meta_7d)} / ${c.despacho.leads_ghl_7d==null?'—':num(c.despacho.leads_ghl_7d)}`)) },
        { clave: 'estanc', titulo:'Parados >72h',tituloCompleto:'Leads sin avance observado en la etapa durante más de 72 horas; no ausencia de trabajo', num: true, celda: c => (c.sinGhl ? '—' : h('span', {title:`Sin avance observado / cohorte registrada; no ausencia de trabajo. Mayor espera registrada: ${c.despacho.horas_max_parado?num(Math.round(c.despacho.horas_max_parado/24))+' días':'sin dato'}.`,style:NOWRAP}, `${c.estanc==null?'—':num(c.estanc)} / ${c.cohorte==null?'—':num(c.cohorte)}`)) },
        { clave: 'citas', titulo: 'Citas 14d',tituloCompleto:'Citas agendadas observadas · 14 días', num: true, celda: c => (c.sinGhl ? '—' : num(c.citas)) },
        { clave: 'sinEstado', titulo: 'Sin estado', num: true, celda: c => (c.sinGhl ? '—' : c.sinEstado===null?'—':chipEstado('gris',num(c.sinEstado))) },
        { clave: 'asis', titulo: 'Asist. 14d',tituloCompleto:'Asistencia sobre resultados registrados · 14 días; no conversión', num: true, celda: c => (c.asis === null || c.asis === undefined ? h('span', { class: 'dim' }, '—') : chipEstado('gris',pct(c.asis))) },
      ],
      alPulsar: c => {if(ctx.vigente?.()!==false)ctx.navegar(`captacion/${c.cliente_id}`);},
      etiquetaFila: c => `${c.nombre}. Abrir tarjeta`,
      vacio: { titulo: 'Nada que mirar aquí', porque: 'No hay casos en el filtro de la lectura disponible; no acredita ausencia de problemas.', celebrar:false },
    }));
  };
  pintar();
  el.append(panel({ titulo: 'Qué hace el despacho con los leads', icono: 'phone', sub:'Recuentos observados, con cobertura parcial. Asistencia sólo sobre resultados registrados; no mide conversión ni ventas.' },
    h('div', { class: 'cuerpo' },typeof matchMedia==='function'&&matchMedia('(max-width:640px)').matches?h('details',{class:'que-es'},h('summary',{},'Filtros de esta vista'),chips):chips), caja,h('p',{class:'sub',style:{padding:'8px 16px'}},'Meta / CRM: recuentos independientes de 7 días, sin unión por lead. Parados: sin avance observado / cohorte; no acredita ausencia de trabajo. — sin dato.')));
  el.append(avisoParcial('Esta copia no acredita llamadas, respuesta real ni cuatro intentos por lead. Contrasta conversaciones y registros del despacho; «sin avance observado >72 h» es sólo una señal de la etapa, no de ausencia de trabajo.', { titulo: 'Todavía no se mide:' }));
}

function tAnuncios(el, ctx, d, c) {
  const a = c.anuncios;
  if (!a) { el.append(vacio({ icono: 'spark', titulo: 'Sin anuncios que mirar', texto: c.meta_activa ? 'No se pudieron leer los anuncios de esta cuenta.' : 'La cuenta no tiene pauta activa: no hay anuncios con impresiones en 7 días.' })); return; }
  el.append(tiles([
    tile({ icono: 'baja', etiqueta: 'Cansadas', valor: contadorObservado648(a.cansadas), estado: contadorObservado648(a.cansadas) > 0 ? 'rojo' : 'gris', contexto: 'Dos señales guardadas a la vez; cobertura no exhaustiva, cero no acredita ausencia.', medible: 'medias' }),
    tile({ icono: 'ojo', etiqueta: 'Con una señal', valor: contadorObservado648(a.vigilar), estado: contadorObservado648(a.vigilar) > 0 ? 'ambar' : 'gris', contexto: 'Una señal guardada para revisar; cobertura no exhaustiva, cero no acredita ausencia.', medible: 'medias' }),
    tile({ icono: 'star', etiqueta: 'Ganadoras', valor: a.ganadoras, estado: '', contexto: 'Gasto ≥ 10 veces el objetivo con coste ≤ objetivo', medible: 'hoy' }),
    tile({ icono: 'alert', etiqueta: 'Rechazados o con problemas', valor: contadorObservado648(a.problemas_total), estado: contadorObservado648(a.problemas_total) > 0 ? 'rojo' : 'gris', contexto: 'Rechazos o problemas guardados; cobertura no exhaustiva, cero no acredita ausencia.', medible: 'medias' }),
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

