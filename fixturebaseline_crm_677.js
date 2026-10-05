// Baseline mínimo de dos funciones renderer reales; sin imports/IO.
function pintarSubcuentas(zona, ctx, d, vis) {
  const todas = vis.jefatura ? d.subcuentas : vis.base;
  const cuenta = e => todas.filter(f => (e === 'pruebas' ? (f.tipo === 'prueba' || f.tipo === 'interna') : f.estado === e && f.tipo !== 'prueba' && f.tipo !== 'interna')).length;
  const opciones = [
    { valor: 'activas', texto: 'Señales y referencias', icono: 'zap', cuenta: todas.filter(f => f.estado !== 'gris'||f.motivos?.length).length },
    { valor: 'rojo', texto: 'En rojo', icono: 'fire', cuenta: cuenta('rojo'), cuentaEstado: 'rojo' },
    { valor: 'ambar', texto: 'Vigilar', icono: 'alert', cuenta: cuenta('ambar') },
    { valor: 'verde', texto: 'En verde', icono: 'ok', cuenta: cuenta('verde') },
    { valor: 'gris', texto: 'Sin dato de salud', icono: 'vacio', cuenta: cuenta('gris') },
    { valor: '', texto: 'Todas', cuenta: todas.length },
  ];
  if (vis.jefatura) opciones.splice(5, 0, { valor: 'pruebas', texto: 'Pruebas e internas', icono: 'aj', cuenta: cuenta('pruebas') });
  if (!vis.jefatura && vis.mias.length && vis.base !== vis.mias) opciones.unshift({ valor: 'mias', texto: 'Mis subcuentas', icono: 'persona', cuenta: vis.mias.length });
  const caja = h('div');
  const chips = chipsFiltro({ etiqueta: 'Estado', clave: 'crm.estado', opciones, valor: 'activas', alCambiar: () => pintar() });
  const pintar = () => {
    if(ctx.vigente&&!ctx.vigente()){caja.replaceChildren();return;}
    const v = chips.valor();
    const filas = todas.filter(f => v === '' ? true : v === 'activas' ? (f.estado !== 'gris'||f.motivos?.length>0) : v === 'pruebas' ? (f.tipo === 'prueba' || f.tipo === 'interna') : v === 'mias' ? vis.mias.includes(f) : f.estado === v && f.tipo !== 'prueba' && f.tipo !== 'interna')
      .sort((a, b) => EST[a.estado].o - EST[b.estado].o || (b.leads_30d || 0) - (a.leads_30d || 0));
    const punto = cuentagotas(filas, f => f.estado, pesoSub);
    caja.replaceChildren(tablaDensa({
      filas, buscar: { campos: ['nombre', 'especialista', 'account', 'nombre_sub'], placeholder: 'Buscar subcuenta, especialista o account' },
      filtros: vis.jefatura ? [{ clave: 'especialista', titulo: 'Especialista' }] : [],
      columnas: [
        { clave: 'nombre', titulo: 'Subcuenta', principal: true, celda: f => h('span', { class: 'celda-cli', style: { minWidth: 0 } }, logoCliente(f), h('span', { style: { display: 'grid', minWidth: 0 } }, f.nombre, f.tipo === 'sin_cliente' ? h('small', { class: 'sub', style: { fontWeight: 500, fontSize: 'var(--fs-12)' } }, 'sin cliente en la app') : null)) },
        { clave: 'estado', titulo: 'Estado', valor: f => EST[f.estado].o, celda: f => puntoEstado(punto(f), EST[f.estado].t) },
        { clave: 'especialista', titulo: 'Especialista', celda: f => h('span', {title:f.especialista||'sin asignar'}, f.especialista || 'sin asignar') },
        { clave: 'leads_30d', titulo: 'GHL30d · Meta7d', tituloCompleto:'Leads observados en GHL: 30 días; eventos lead en Meta: 7 días. Recuentos independientes', num: true, celda: f => h('span',{style:{whiteSpace:'nowrap'},title:`GHL30d: ${f.leads_30d??'Sin dato'} · Meta7d: ${f.leads_meta_7d??'Sin dato'}. Recuentos independientes, no unión por lead ni tasa de conversión`,'aria-label':`GHL30d: ${f.leads_30d??'Sin dato'}; Meta7d: ${f.leads_meta_7d??'Sin dato'}`},f.leads_30d==null?'—':numFuerte(f.leads_30d),' · ',f.leads_meta_7d==null?'—':numFuerte(f.leads_meta_7d)) },
        { clave: 'sin_tocar_24h', titulo: 'Sin intento24h', num: true, celda: f => numFuerte(f.sin_tocar_24h) },
        { clave: 'v1h', titulo: 'Intento <1h', num: true, valor: f => f.velocidad?.pct_1h, celda: f => f.velocidad?.juzgables ? h('span', { title:'Primer intento registrado, no respuesta',style: { display:'grid',gap:'2px',fontVariantNumeric:'tabular-nums' } },h('span',{},pc(f.velocidad.pct_1h)),h('span',{class:'sub'},`${f.velocidad.en_1h}/${f.velocidad.juzgables}`)) : '—' },
        { clave: 'se', titulo: 'Sin est14d · Asist30d', tituloCompleto:'Citas sin estado: 14 días; asistencia entre resultados registrados: 30 días', num: true, valor: f => f.citas_14d?.sin_estado, celda: f => h('span',{style:{whiteSpace:'nowrap'},title:`Citas sin estado14d: ${f.citas_14d?.sin_estado??'Sin dato'} · Asistencia30d: ${f.citas_30d?.asistencia_pct??'Sin dato'}. Sólo resultados registrados, no todas las citas ni ventas`,'aria-label':`Citas sin estado14d: ${f.citas_14d?.sin_estado??'Sin dato'}; Asistencia30d: ${f.citas_30d?.asistencia_pct??'Sin dato'}`},f.citas_14d?.sin_estado==null?'—':numFuerte(f.citas_14d.sin_estado),' · ',f.citas_30d?.asistencia_pct !== null && f.citas_30d?.asistencia_pct !== undefined ? pc(f.citas_30d.asistencia_pct) : '—') },
        { clave: 'ir', titulo: 'Detalle / GHL', ordenable: false, celda: f => detalleSubcuenta245(ctx,d,f) },
      ],
      porPagina: MOVIL() ? 8 : 15,
      alPulsar: f => {if(!ctx.vigente||ctx.vigente())ctx.navegar(`${ID}/${f.sub_id}`);},
      etiquetaFila: f => `${f.nombre}: ${EST[f.estado].t}${f.mot1 ? `, ${f.mot1.texto}` : ''}. Abrir`,
      vacio: { titulo: 'Ninguna subcuenta con este filtro', porque: 'Cambia el filtro de estado.' },
    }));
  };
  pintar();
  zona.append(panel({ titulo: 'Subcuentas de GoHighLevel', icono: 'base', sub: vis.jefatura ? `Las ${d.subcuentas.length} de la agencia; las de clientes con campaña, arriba. Pulsa una para ver su detalle.` : 'Tus subcuentas. Pulsa una para ver su detalle y actuar.' },
    h('div', { class: 'cuerpo', style: { padding:'4px 10px' } }, chips), caja,
    h('style',{},`@media(min-width:641px){[data-crm-subcuentas-245] table.densa{table-layout:fixed;width:100%;min-width:900px}[data-crm-subcuentas-245] table.densa th,[data-crm-subcuentas-245] table.densa td{padding:5px 6px;font-size:13px;line-height:1.3;overflow-wrap:anywhere}[data-crm-subcuentas-245] table.densa th,[data-crm-subcuentas-245] table.densa th button{white-space:normal;overflow-wrap:normal;word-break:normal;max-width:100%;min-width:0}[data-crm-subcuentas-245] table.densa th button{padding:0}[data-crm-subcuentas-245] table.densa th:first-child{width:18%}[data-crm-subcuentas-245] table.densa th:last-child{width:14%}[data-crm-subcuentas-245] table.densa th:not(:first-child):not(:last-child){width:11.333333%}[data-crm-subcuentas-245] .celda-cli{gap:4px;min-width:0}[data-crm-subcuentas-245] table.densa td .chip{max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}`)));
  zona.lastElementChild?.setAttribute('data-crm-subcuentas-245','');
}
function detalleSubcuenta245(ctx,d,f) {
  const detalle=h('div',{hidden:true,style:{marginTop:'4px',textAlign:'left'},on:{click:e=>e.stopPropagation(),keydown:e=>e.stopPropagation()}});
  const b=h('button',{type:'button',class:'bt mini','aria-expanded':'false',on:{click:e=>{
    e.stopPropagation();if(ctx.vigente&&!ctx.vigente())return;
    const abierto=detalle.hidden;detalle.hidden=!abierto;b.setAttribute('aria-expanded',String(abierto));
    if(abierto&&!detalle.childNodes.length)detalle.append(
      h('p',{},f.mot1?.texto||'Sin motivo registrado'),
      h('p',{},`Lectura GHL: ${d.fuentes?.ghl?.hora||'sin fecha'}. Lectura de Captación: ${d.fuentes?.captacion?.hora||'sin fecha'}.`),
      h('p',{},'GHL30d y Meta7d son recuentos independientes: ventanas diferentes, sin unión por lead. No acreditan cualificación, respuestas ni ventas.'),
      h('p',{},'Primer intento no equivale a respuesta. Asistencia sólo de resultados registrados; pipeline observado no constituye una cohorte de conversión.'),
      h('a',{href:`#/${ID}/${f.sub_id}`},'Abrir ficha y pipeline observado'));
  }}},'Detalle');
  return h('span',{style:{display:'grid',gap:'2px'}},b,abrirGHL(f.enlaces?.ghl,'GHL'),detalle);
}

// ------------------------------------------------------------------ pestaña: leads sin tocar

function pintarLeads(zona, ctx, d, vis, leads) {
  leads = leadsPendientes369(leads,vis.base);
  const gota = x => senalFilaCRM541('lead',x,d.fuentes?.ghl,ctx.hoy,vis.base).estado;
  const porSub = new Map(d.subcuentas.map(f => [f.sub_id, f]));
  zona.append(panel({ titulo: 'Leads señalados sin intento registrado', icono: 'phone', sub: 'Sin ninguna llamada ni mensaje de una persona en GoHighLevel. La revisión en RO no elimina el pendiente ni confirma una llamada en GHL. Los datos del lead van tapados: «Ver datos» queda en el rastro.' },
    tablaDensa({
      porPagina: MOVIL() ? 8 : 15, filas: leads, buscar: { campos: ['subcuenta', 'medio'], placeholder: 'Buscar subcuenta u origen' }, filtros: [{ clave: 'subcuenta', titulo: 'Subcuenta' }],
      orden: { clave: 'horas', dir: 'desc' },
      columnas: [
        { clave: 'subcuenta', titulo: 'Subcuenta', principal: true, celda: x => h('span', { class: 'celda-cli' }, logoCliente(porSub.get(x.sub_id) || { nombre: x.subcuenta }), x.subcuenta) },
        { clave: 'creado', titulo: 'Entró', celda: x => `${fDiaRO(x.creado)} · ${x.creado?.slice(11) || ''}` },
        { clave: 'horas', titulo: 'Edad en copia', num: true, celda: x => puntoEstado(gota(x), horasTxt(x.horas)) },
        { clave: 'medio', titulo: 'Origen', celda: x => h('span', { style: { display: 'inline-block', minWidth: '140px' } }, x.medio || '—') },
        { clave: 'automatico', titulo: 'Mensaje automático', celda: x => x.automatico ? 'Sí salió' : h('span',{class:'sub',title:'No consta mensaje automático en esta lectura parcial'},'No consta') },
        { clave: 'respondio', titulo: 'El lead escribió', celda: x => x.respondio===true ? h('span',{class:'sub',title:'Entrada registrada en la copia; no resultado de gestión acreditado'},'Sí, revisar') : 'No consta' },
        { clave: 'revision_ro', titulo: 'Revisión RO', ordenable: false, celda: x => estadoRevisionLead369(h,x,d) },
        { clave: 'acc', titulo: 'Acciones', ordenable: false, celda: x => h('span', { class: 'fila', style: { gap: 'var(--s-2)' } },
          // Ronda U: fila compacta · verbo principal (Revisado) + Ver datos + «⋯» con lo que sale fuera (GHL, nota, tarea)
          botonRevisado(ctx, x, 'lead', d), botonVerDatos(ctx, x, vis),
          masAcciones([abrirGHL(x.enlace, 'Abrir contacto en GHL'),
            accionSim(ctx, { texto: 'Nota en GHL', pregunta: '¿Poner la nota «sin contactar a las 24 h»?', tipo: 'nota', objeto: `${x.subcuenta} · lead ${x.ref}`, cliente_id: x.cliente_id,
              vista_previa: `Pondría en el contacto de GHL (${x.subcuenta}) la nota: «Sin contactar a las ${horasTxt(x.horas)} · revisado desde la app». Espera el permiso de GHL (falta un permiso de GoHighLevel).` }),
            porSub.get(x.sub_id) ? tareaAccount(ctx, porSub.get(x.sub_id), `Llamar al lead del ${fDiaRO(x.creado)} (${horasTxt(x.horas)} sin contactar)`) : null].filter(Boolean), `el lead de ${x.subcuenta}`)) },
      ],
      vacio: { titulo: 'Ningún lead sin tocar', porque: 'No hay casos en los contactos y mensajes leídos; cobertura parcial. No acredita que todos los leads hayan sido llamados.' },
    })));
}

// ------------------------------------------------------------------ pestaña: oportunidades paradas
