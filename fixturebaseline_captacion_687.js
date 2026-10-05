function pCuentas(el, ctx, d, filas, C, K) {
  const f = filtroPendiente();
  const n = k => filas.filter(c => (c.gravedad || 'sin') === k).length;
  const chipsG = chipsFiltro({
    etiqueta: 'Gravedad del cliente', clave: f ? null : 'captacion.gravedad.v2', valor: f?.gravedad ?? (f ? '' : undefined),
    opciones: [{ valor: '', texto: 'Todas', cuenta: filas.length }, ...['critico', 'atencion', 'bien'].map(k => ({ valor: k, texto: GRAV_CLI[k].t, icono: GRAV_CLI[k].i, cuenta: n(k), cuentaEstado: k === 'critico' ? 'rojo' : null })),
      ...(n('sin') ? [{ valor: 'sin', texto: 'Sin dato', icono: 'vacio', cuenta: n('sin') }] : [])],
    alCambiar: () => pintar(),
  });
  const chipsC = chipsFiltro({
    etiqueta: 'Dónde se rompe', clave: 'captacion.cuello', multiple: true,
    opciones: ['paid', 'seguimiento', 'integracion'].map(k => ({ valor: k, texto: CUELLO[k].t, icono: CUELLO[k].i, cuenta: filas.filter(c => c.cuello?.includes(k)).length })),
    alCambiar: () => pintar(),
  });
  const chipsP = chipsFiltro({
    etiqueta: 'Plataforma', clave: 'captacion.plataforma',
    opciones: [{ valor: '', texto: 'Todas' }, { valor: 'meta', texto: 'Meta', cuenta: filas.filter(c => c.plataformas?.includes('meta')).length },
      { valor: 'google', texto: 'Google Ads', cuenta: filas.filter(c => c.plataformas?.includes('google')).length }, { valor: 'tiktok', texto: 'TikTok', cuenta: 0 }],
    alCambiar: () => pintar(),
  });
  const caja = h('div');
  const detalleCuenta243=h('section',{'aria-label':'Detalle de la cuenta Paid',tabindex:-1,style:{scrollMarginTop:'90px'}});
  const cerrarDetalle415=()=>{detalleCuenta243._cerrar243?.();detalleCuenta243.replaceChildren();};
  // Los controles de tablaDensa repintan dentro de caja, sin llamar pintar().
  caja.addEventListener('input',cerrarDetalle415);
  caja.addEventListener('change',cerrarDetalle415);
  caja.addEventListener('click',e=>{if(e.target?.closest?.('.tabla-ctl,.tabla-filtros,.tabla-mas,thead'))cerrarDetalle415();});
  const techo = d.parametros.techo_cpl;
  // Móvil (< 641 px): los filtros (chips y desplegables de la tabla) van en un plegable de una fila «Filtros (n activos)».
  const movil = typeof matchMedia === 'function' && matchMedia('(max-width: 640px)').matches;
  const hueSel = h('div', { class: 'fila', style: { gap: S[2] } });
  const resumen = h('span', {}, 'Filtros');
  const contarActivos = () => {
    const sel = [...caja.querySelectorAll('.tabla-ctl select'), ...hueSel.querySelectorAll('select')].filter(x => x.value).length;
    const n = (chipsG.valor() ? 1 : 0) + chipsC.valor().length + (chipsP.valor() ? 1 : 0) + sel;
    resumen.textContent = n ? `Filtros (${n} ${n === 1 ? 'activo' : 'activos'})` : 'Filtros';
  };
  const pintar = () => {
    detalleCuenta243._cerrar243?.();detalleCuenta243.replaceChildren();
    const g = chipsG.valor(), cu = chipsC.valor(), p = chipsP.valor();
    let base = filas.filter(c => (!g || (c.gravedad || 'sin') === g) && (!cu.length || cu.every(k => c.cuello?.includes(k))) && (!p || c.plataformas?.includes(p)));
    if (f?.aviso === 'objetivo') base = base.filter(c => c.meta_activa && !c.objetivo?.cargado);
    if (f?.sinHoy) base = base.filter(c => c.meta_activa && !hoyBit(ctx, d, c.cliente_id));
    const filasT = base.map(c => ({
      ...c, panelEspecialista:{...panelPaid(c,d,ctx.hoy||hoyMadrid()),real:medirCplPaid(c,d,ctx.hoy||hoyMadrid()).real,referenciaAnterior:medirCplPaid(c,d,ctx.hoy||hoyMadrid()).referenciaAnterior}, grav: gc(c).o * 10 + GRAV[c.severidad].o, pub: GRAV[c.severidad].o, motivo: (c.motivos || [])[0] ? textoMot(c.motivos[0]) : ((c.avisos || []).find(a => a.clase_id === 'integracion') ? textoMot(c.avisos.find(a => a.clase_id === 'integracion')) : ''),
      trafficker: nombre(d, c.equipo?.trafficker) || 'sin trafficker', account: nombre(d, c.equipo?.account) || 'sin account',
      leads7: cuentaMetaError508(c)?null:conteoMeta508(c.leads?.['7d']), deltaMeta508:deltaMeta508(c,d,ctx.hoy||hoyMadrid()), creativos508:creativosMatriz508(c,d,ctx.hoy||hoyMadrid()), gasto7: c.gasto?.['7d'] ?? null, cplref: c.cpl_resumen?.ref ?? null, cita: c.coste_por_cita?.coste_por_cita_14d ?? null,
    }));
    const soloUnTrafficker = new Set(filasT.map(c => c.trafficker)).size <= 1;
    caja.replaceChildren(tablaDensa({
      filas: filasT, orden: { clave: 'grav', dir: 'asc' }, porPagina: 12, apilable:true,
      buscar: { campos: ['nombre', 'trafficker', 'account', 'motivo'], placeholder: 'Buscar cliente, trafficker o motivo' },
      filtros: [new Set(filasT.map(c => c.trafficker)).size > 1 ? { clave: 'trafficker', titulo: 'Trafficker' } : null, { clave: 'account', titulo: 'Account' }].filter(Boolean),
      columnas: [
        { clave: 'nombre', titulo: 'Cliente', principal: true, celda: c => h('span', { class: 'celda-cli' }, logoCliente(c), h('span',{class:'paid-nombre-401'},c.nombre), esTienda(c) ? h('span', { class: 'chip gris sin-punto', title: NOTA_TIENDA }, 'tienda online') : null) },
        { clave: 'grav', titulo: 'Estado', tituloCompleto:'Semáforo del cliente', celda: c => h('span', { title: `Gravedad del cliente; Paid: ${GRAV[c.severidad]?.t || 'Sin dato'}. Consulta el detalle para la evidencia de publicidad.` }, chipCli(c)) },
        { clave: 'trafficker', titulo: 'Traf.', tituloCompleto:'Trafficker responsable', celda: c => c.equipo?.trafficker ? h('span', {title:c.trafficker}, c.trafficker) : chipEstado('ambar', 'sin trafficker') },
        { clave: 'leads7', titulo: 'Meta 7d', tituloCompleto:'Contador de resultados Meta · 7 días; no acredita cualificación', num: true, celda: c => c.panelEspecialista.cuentaError ? '—' : c.leads7 === null ? '—' : h('span', { style: NOWRAP, title:'Contador Meta de siete días; tipo de evento y cualificación en el detalle.' }, num(c.leads7), c.deltaMeta508===null?null:h('span',{class:'sub',title:'Variación de eventos Meta del mismo tipo, dos ventanas de siete días consecutivas acreditadas; no cualificación ni conversión CRM.'},` ${c.deltaMeta508>0?'▲':c.deltaMeta508<0?'▼':'='} ${num(Math.abs(c.deltaMeta508))} %`)) },
        { clave: 'gasto7', titulo:'Gasto', tituloCompleto:'Gasto Meta · 7 días, moneda de la cuenta', num:true, celda:c=>{
          if(!c.dinero)return candado('Reservado');
          const v=c.gasto7,moneda=c.cuenta_meta?.moneda;
          if(c.panelEspecialista.cuentaError||typeof v!=='number'||!Number.isFinite(v)||v<0)return '—';
          return h('span',{style:NOWRAP,title:`Gasto Meta · ${d.ventanas?.['7d']?.join(' a ')||'ventana de siete días'} · moneda ${moneda||'por confirmar'}`},moneda==='EUR'?eur(v):`${num(v,2)}${typeof moneda==='string'&&/^[A-Z]{3}$/.test(moneda)?' '+moneda:''}`);
        } },
        { clave: 'cplref', titulo: 'CPL', tituloCompleto:'Coste por lead · objetivo y evidencia en el detalle', num:true, celda:c=>{
          if(!c.dinero)return candado('Reservado');
          const p=c.panelEspecialista,m=c._cplMedicion;
          const valor=p.real===null?(p.referenciaAnterior==null?'—':`${eur(p.referenciaAnterior)}†`):eur(p.real);
          const objetivo=p.objetivo===null?'—':`${eur(p.objetivo)}${m?.objetivoVigente?'':'‡'}`;
          return h('span',{class:`chip ${m?.evaluable?m.estado:'gris'} sin-punto`,title:`${m?.nota||'CPL sin comparación acreditada'}. Objetivo: ${objetivo}. Datos hasta ${p.hasta||'sin fecha'}. † Referencia anterior: unidad pendiente, no CPL real. ‡ Objetivo pendiente de ratificar. — Sin dato.`},`${valor}`);
        } },
        { clave:'cpm',titulo:'CPM',tituloCompleto:'Coste por mil impresiones · referencia de cuenta en copia local',num:true,ordenable:false,celda:c=>{
          if(!c.dinero)return candado('Reservado');
          const r=referenciaCpm417(c,d);
          return r?h('span',{class:'chip gris sin-punto',title:`CPM de cuenta en copia local: ${r.desde} a ${r.hasta}. Lectura ${r.fecha_lectura}; zona y cobertura originales pendientes. § Referencia histórica, no medición actual ni cumplimiento.`},`${eur(r.coste_por_mil)}§`):h('span',{title:'Sin referencia CPM válida para esta cuenta y ventana.'},'—');
        } },
        { clave:'objetivoCpl',titulo:'Obj. CPL',tituloCompleto:'Objetivo propio de coste por lead; vigencia y evidencia en el detalle',num:true,ordenable:false,celda:c=>{
          if(!c.dinero)return candado('Reservado');
          const m=c._cplMedicion,v=m?.objetivo;
          if(typeof v!=='number'||!Number.isFinite(v)||v<=0)return h('span',{title:'Sin objetivo propio válido; no se aplica un objetivo por defecto.'},'—');
          return h('span',{class:'chip gris sin-punto',title:m.objetivoVigente?'Objetivo propio con vigencia acreditada; no acredita cumplimiento del CPL.':'‡ Objetivo registrado pendiente de ratificar vigencia; no acredita cumplimiento del CPL.'},`${eur(v)}${m.objetivoVigente?'':'‡'}`);
        } },
        { clave:'creativos',titulo:'Señ.',tituloCompleto:'Señales observadas en muestra parcial de anuncios; no antigüedad del creativo',ordenable:false,celda:c=>h('span',{title:`Señales observadas en la muestra del generador, cobertura parcial; no confirma fatiga ni inventario completo. Lectura de anuncios: ${lecturaAnunciosPaid4(d,ctx.hoy||hoyMadrid())||'sin fecha válida'}. Antigüedad del creativo: sin dato.`},c.creativos508===null?'—':num(c.creativos508.valor)) },
        { clave:'pendiente',titulo:'Ver',tituloCompleto:'Detalle de cuenta y registro de trabajo',ordenable:false,celda:c=>celdaRevisionCompacta243(ctx,d,c,detalleCuenta243) },
      ].filter(Boolean).filter(col => !(col.clave === 'trafficker' && soloUnTrafficker)),
      alPulsar: c => ctx.navegar(`captacion/${c.cliente_id}`),
      etiquetaFila: c => `${c.nombre}: cliente ${gc(c).t.toLowerCase()}, ${GRAV[c.severidad].t.toLowerCase()}. ${c.motivo}. Abrir tarjeta`,
      vacio: { titulo: 'Ninguna cuenta con estos filtros', porque: 'Cambia la gravedad o quita un filtro.' },
    }));
    if (movil) {
      const sels = [...caja.querySelectorAll('.tabla-ctl label')].filter(l => l.querySelector('select'));
      hueSel.replaceChildren(...sels);
      for (const sl of hueSel.querySelectorAll('select')) sl.addEventListener('change', contarActivos);
    }
    contarActivos();
  };
  pintar();
  const filtros = [chipsG, h('div', { class: 'fila', style: { gap: S[4] } }, chipsC, chipsP)];
  el.append(h('div', { class: 'panel' },
    h('div', { class: 'pila', style: { gap: S[2], padding: `${S[2]} var(--relleno) 0` } },
      h('small',{class:'sub',title:'Esta matriz conserva su ventana de siete días de la copia; el selector general de periodo no cambia sus cifras. CPL y CPM pueden ser referencias con otra cobertura: consulta el detalle.'},'Matriz Meta · 7 días de la copia · periodo fijo'),
      // Ronda U: los filtros, en una línea plegada también en el ordenador (antes 3 filas de chips encima de la tabla)
      h('details', { class: 'que-es' },
        h('summary', { style: { display: 'flex', alignItems: 'center', gap: S[2], minHeight: '36px', fontWeight: '600' } }, icono('filtro', { clase: 's' }), resumen,
          h('span', { class: 'sub', style: { fontWeight: '400' } }, '· gravedad, dónde se rompe y plataforma')),
        h('div', { class: 'pila', style: { gap: S[2], marginTop: S[2] } }, ...filtros, movil ? hueSel : null)),
      f?.aviso === 'objetivo' ? avisoParcial('Solo las cuentas activas sin objetivo de coste por cita cargado. Vuelve a «Captación» para quitar el filtro.', { tipo: 'info' }) : null),
    caja,detalleCuenta243,
    h('p',{class:'sub',style:{padding:'10px 16px',margin:'0',fontSize:'12px'}},`Copia hasta ${fDiaRO(d.datos_hasta)} · Gasto: inversión Meta · CPL: coste por evento lead · CPM: coste por mil impresiones · Obj. CPL: objetivo propio · Señ.: señales en muestra parcial · — sin dato · † referencia anterior, unidad pendiente · ‡ objetivo por confirmar · § CPM histórico, zona y cobertura pendientes. Creativos: señales por contrastar. Abre una fila para revisar fuentes y acciones.`),
    h('style',{}, `@media(min-width:641px){[data-paid-cuentas-243] .tabla-densa table{table-layout:fixed;width:100%;min-width:900px}[data-paid-cuentas-243] table.densa th,[data-paid-cuentas-243] table.densa td{padding:5px 6px;font-size:13px;line-height:1.3;overflow-wrap:anywhere}[data-paid-cuentas-243] table.densa th{white-space:normal;overflow-wrap:normal;word-break:normal}[data-paid-cuentas-243] table.densa th button{display:block;padding:0;white-space:normal;max-width:100%;min-width:0;font-size:inherit;letter-spacing:0;line-height:1.3;overflow-wrap:normal;word-break:normal}[data-paid-cuentas-243] table.densa th:first-child{width:18%}[data-paid-cuentas-243] table.densa th:last-child{width:10%}[data-paid-cuentas-243] .celda-cli{gap:4px;min-width:0;flex-wrap:wrap}[data-paid-cuentas-243] .paid-nombre-401{min-width:80px;flex:1;overflow-wrap:normal;word-break:normal}[data-paid-cuentas-243] table.densa td .chip{max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}[data-paid-cuentas-243] .tabla-ctl{padding:12px 16px;gap:10px}[data-paid-cuentas-243] .tabla-ctl input,[data-paid-cuentas-243] .tabla-ctl select{border-radius:10px;min-height:42px}[data-paid-cuentas-243] table.densa td{height:42px}}`)));
  el.lastElementChild?.setAttribute('data-paid-cuentas-243','');
}
// Fecha de lectura del generador; no fecha de publicación ni antigüedad del creativo.
function lecturaAnunciosPaid4(d,hoy) {
  const stamp=d?.anuncios_generado||d?.fuentes?.find?.(f=>f.id==='anuncios')?.hora;
  const dia=fechaPaid549(stamp),actual=fechaPaid549(hoy);
  return dia&&actual&&dia<=actual?stamp:null;
}
//417 · nunca convierte un agregado legacy en medición actual ni en semáforo de rendimiento.
function referenciaCpm417(c,d){
  const r=c.coste_cpm_referencia_7d,w=d.ventanas?.['7d'];
  if(!c.dinero||c.panelEspecialista?.cuentaError||c.cuenta_meta?.error||!r||r.version!=='417.1'||r.cliente_id!==c.cliente_id||r.moneda!=='EUR'||c.cuenta_meta?.moneda!=='EUR'||r.fuente!=='cache_legacy'||r.nivel!=='account_agregado_legacy'||r.estado!=='referencia_observada'||r.medicion_actual!==false||r.zona!==null||r.cobertura!=='presencia_original_no_acreditada'||!Array.isArray(w)||w.length!==2||r.desde!==w[0]||r.hasta!==w[1])return null;
  const n=x=>typeof x==='number'&&Number.isFinite(x)&&x>=0;
  if(!n(r.gasto_observado)||!Number.isSafeInteger(r.impresiones_observadas)||r.impresiones_observadas<=0||!n(r.coste_por_mil)||typeof r.fecha_lectura!=='string'||!/^\d{4}-\d{2}-\d{2}[T ]/.test(r.fecha_lectura)||typeof r.cuenta_id!=='string'||!/^[1-9][0-9]{0,29}$/.test(r.cuenta_id))return null;
  const dia=x=>{if(typeof x!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(x))return null;const t=Date.parse(x+'T00:00:00Z');return Number.isFinite(t)&&new Date(t).toISOString().slice(0,10)===x?t:null;};
  const desde=dia(r.desde),hasta=dia(r.hasta),m=/^(\d{4}-\d{2}-\d{2})[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.\d{1,6})?)?(?:Z|([+-])(\d{2}):(\d{2}))?$/.exec(r.fecha_lectura);
  if(desde===null||hasta===null||hasta-desde!==6*86400000||!m||dia(m[1])===null||dia(m[1])<=hasta||+m[2]>23||+m[3]>59||+(m[4]||0)>59||m[5]&&(+m[6]>14||+m[7]>59||+m[6]===14&&+m[7]!==0))return null;
  const calculado=1000*r.gasto_observado/r.impresiones_observadas;
  if(!Number.isFinite(calculado)||Math.abs(calculado-r.coste_por_mil)>Math.max(1,calculado)*1e-10)return null;
  return r;
}
/** Ámbito del detalle Paid: no requiere mediciones Meta ni permiso de inversión. */
function ambitoDetallePaid415(ctx,cid) {
  try {
    const ids=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,100}$/.test(x);
    if(ctx.vigente?.()===false||ctx.veModulo?.('captacion')!==true||!ids(cid))return null;
    const ps=Array.isArray(ctx.datos?.personas)?ctx.datos.personas:[];
    for(const p of [ctx.real,ctx.persona]) {
      const xs=ps.filter(x=>x?.id===p?.id);
      if(!ids(p?.id)||xs.length!==1||p.estado!=='activo'||p.activo===false||xs[0].estado!=='activo'||xs[0].activo===false||!Array.isArray(p.puestos)||!p.puestos.length||!p.puestos.every(ids)||new Set(p.puestos).size!==p.puestos.length||!Array.isArray(xs[0].puestos)||JSON.stringify([...p.puestos].sort())!==JSON.stringify([...xs[0].puestos].sort()))return null;
    }
    const cs=[ctx.clientes,ctx.clientesVisibles].map(xs=>Array.isArray(xs)?xs.filter(x=>x?.id===cid):[]);
    if(cs.some(xs=>xs.length!==1||xs[0].activo_confirmado!==true||xs[0].detalle===false)||ctx.ver?.({tipo:'cliente_detalle',cliente_id:cid})?.ok!==true)return null;
    return JSON.stringify([ctx.real,ctx.persona,ps,ctx.clientes,ctx.clientesVisibles,ctx.nivel,ctx.soloLectura,ctx.ver({tipo:'cliente_detalle',cliente_id:cid}),ctx.ver({tipo:'inversion',cliente_id:cid}),ctx.veModulo('captacion')]);
  } catch {return null;}
}
/** Detalle bajo demanda: el botón conserva teclado y evita la navegación de la fila. */
function celdaRevisionCompacta243(ctx,d,c,destino=null) {
  const p=c.panelEspecialista;
  const firma415=ctx.servidor===true?ambitoDetallePaid415(ctx,c.cliente_id):null;
  const vigente415=()=>ctx.vigente?.()!==false&&(ctx.servidor!==true||(firma415&&ambitoDetallePaid415(ctx,c.cliente_id)===firma415));
  const guard415=e=>{if(vigente415())return true;destino?._cerrar243?.();destino?.replaceChildren();detalle.replaceChildren();detalle.hidden=true;boton.setAttribute('aria-expanded','false');e?.preventDefault?.();e?.stopPropagation?.();return false;};
  const detalle=h('div',{hidden:true,style:{marginTop:'6px',minWidth:'0',textAlign:'left'},on:{click:e=>e.stopPropagation(),keydown:e=>e.stopPropagation()}});
  const boton=h('button',{type:'button',class:'bt mini','aria-expanded':'false',on:{click:e=>{
    if(!guard415(e))return;
    e.stopPropagation();const abierto=detalle.hidden;detalle.hidden=!abierto;boton.setAttribute('aria-expanded',String(abierto));
    if(abierto&&!detalle.childNodes.length)detalle.append(
      h('b',{},'Por qué'),h('p',{},c.motivo||'Sin motivo registrado'),
      h('span',{class:'fila'},(c.cuello||[]).map(k=>chipCuello(k))),
      h('p',{},p.accion),
      c.dinero?h('p',{},`CPL: datos hasta ${p.hasta||'sin fecha'}${p.datoVigente?'':' · lectura anterior'}. Objetivo ${p.objetivo===null?'sin confirmar':`${eur(p.objetivo)} · ${c.objetivo?.cuando||'fecha por confirmar'} · ${c._cplMedicion?.objetivoVigente?'vigente acreditado':'pendiente de ratificar'}`}`):null,
      (r=>r?h('p',{},`CPM histórico: ${eur(r.coste_por_mil)} · ${num(r.impresiones_observadas)} impresiones · gasto ${eur(r.gasto_observado)} · ${r.desde} a ${r.hasta}. Lectura ${r.fecha_lectura}; zona y cobertura pendientes. No medición actual.`):null)(referenciaCpm417(c,d)),
      h('p',{},`Días sin resultados Meta: ${p.racha==null||cuentaMetaError508(c)?'sin dato':`${p.racha.completa?'':'≥ '}${p.racha.dias}`} · hasta ${p.racha?.hasta||'sin fecha'}. Contador de la copia; no acredita ausencia de leads.`),
      h('p',{},`Lectura de anuncios: ${lecturaAnunciosPaid4(d,ctx.hoy||hoyMadrid())||'sin fecha válida'}. Antigüedad del creativo: sin dato. Muestra parcial del generador; contrastar, no certifica fatiga.`),
      h('p',{},'CPC y CTR de cuenta: sin fuente compatible en esta matriz. CPC: coste por clic; CTR: porcentaje de clics. No se reconstruyen a partir de anuncios ni de otra cuenta.'),
      h('p',{},'Leads recibidos; cualificación no instrumentada aquí.'),
      ctx.nivel==='resumen'?null:celdaHoy(ctx,d,c),
      h('a',{href:`#/captacion/${c.cliente_id}`},'Abrir cuenta y fuentes'));
    if(destino){
      if(abierto){
        destino._cerrar243?.();detalle.hidden=false;boton.setAttribute('aria-expanded','true');
        const cerrar=()=>{detalle.hidden=true;boton.setAttribute('aria-expanded','false');destino.replaceChildren();destino._cerrar243=null;};
        destino._cerrar243=cerrar;
        destino.replaceChildren(h('div',{class:'pila',style:{padding:'16px',borderTop:'1px solid var(--line)',gap:'12px'}},h('div',{class:'fila',style:{justifyContent:'space-between'}},h('h3',{},c.nombre),h('button',{type:'button',class:'bt mini',on:{click:()=>{cerrar();boton.focus?.();}}},'Cerrar detalle')),detalle));
        destino.focus?.({preventScroll:true});destino.scrollIntoView?.({block:'start',behavior:'smooth'});
      }else{destino._cerrar243?.();}
    }
  }}},ctx.nivel!=='resumen'&&c.meta_activa&&!ctx.soloLectura?'Ver':'Ver');
  boton.setAttribute('title',p.accion);
  detalle.addEventListener('click',e=>guard415(e),true);
  detalle.addEventListener('keydown',e=>guard415(e),true);
  return h('span',{class:'pila',style:{gap:'2px'}},boton,destino?null:detalle);
}
/** Celda «Qué cambió hoy»: lo apuntado hoy o el último apunte, y «Apuntar» (editor en la propia fila, sin abrir la tarjeta). */
function celdaHoy(ctx, d, c) {
  const caja = h('span', { style: { display: 'grid', gap: S[1], minWidth: '200px', maxWidth: '280px' }, on: { click: e => e.stopPropagation(), keydown: e => e.stopPropagation() } });
  const pintar = () => {
    const l = d.bitacora?.get(c.cliente_id) || [];
    const hoyA = l.find(a => !a._recibo516 && diaDe(a) && ctx.fechas?.esHoy?.(diaDe(a)));
    const ult = hoyA || l[0];
    const texto = ult ? h('span', { class: hoyA ? null : 'sub', style: { whiteSpace: 'normal', overflowWrap: 'anywhere' } }, hoyA ? '✓ ' : '', ult.texto, h('span', { class: 'sub' }, ` · ${cuandoBit(ctx, ult)}`))
      : h('span', { class: 'sub' }, c.meta_activa ? 'Sin apuntar hoy' : 'Sin pauta');
    const ed = h('div', { hidden: true });
    const b = c.meta_activa && !ctx.soloLectura ? h('button', { type: 'button', class: 'bt mini', 'aria-expanded': 'false', on: { click: () => {
      const abrir = ed.hidden; ed.hidden = !abrir; b.setAttribute('aria-expanded', String(abrir));
      if (abrir && !ed.childNodes.length) ed.append(editorBitacora(ctx, d, c, { compacto: true, alHecho: pintar }));
      if (abrir) ed.querySelector('input')?.focus();
    } } }, icono('editar'), hoyA ? 'Añadir' : 'Apuntar') : null;
    caja.replaceChildren(texto, ...(b ? [h('span', {}, b)] : []), ed);
  };
  pintar();
  return caja;
}
