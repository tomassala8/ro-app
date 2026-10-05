// 117 · Motor puro. Recibe exclusivamente fuentes ya recortadas; no carga ni escribe.
const lista = v => Array.isArray(v) ? v : [];
const numero = v => typeof v === 'number' && Number.isFinite(v) && v >= 0 ? v : null;
const texto = (v, max = 160) => typeof v === 'string' && !/[\w.+-]+@[\w-]+\.[\w.-]+|\b(token|secret|password|authorization)\s*[:=]/i.test(v) ? v.slice(0, max) : '';
const fechaFuente = d => { const f = d?.generado || d?._meta?.generado || d?.meta?.generado; return typeof f === 'string' && /^\d{4}-\d{2}-\d{2}/.test(f) ? f.slice(0, 40) : null; };
const celda = (valor, estado, fuente, doc, detalle = '') => ({ valor, estado, fuente, fecha: fechaFuente(doc), detalle });
const unico = (doc, key, id) => { const rows = lista(doc?.[key]).filter(r => r?.cliente_id === id); return rows.length === 1 ? rows[0] : null; };
const SERVICIOS_CONTROL = [['publicidad','Paid'],['crm_ghl','CRM'],['seo','SEO'],['mantenimiento','Web / mantenimiento'],['web','Web'],['redes','Redes'],['social_media','Redes'],['outreach','Outreach']];
const siServicio = v => v === true || (typeof v === 'string' && ['sí','si'].includes(v.trim().toLowerCase()));
const fechaValidaControl = v => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v) && !Number.isNaN(Date.parse(v + 'T00:00:00Z')) && new Date(v + 'T00:00:00Z').toISOString().slice(0,10) === v;
export function seguimientoControl474(doc,cid,personas,hoy) {
  const xs=lista(doc?.sugerencias).filter(r=>r?.cliente_id===cid);
  if(xs.length!==1||doc.hoy!==hoy||!fechaValidaControl(hoy))return null;
  const r=xs[0];
  if(r.regla_id!=='seguimiento_quincenal_especialista'||r.cadencia_dias!==15||r.responsable_role!=='trafficker'||r.incumplimiento!==null||!['sin_dato','confirmar_responsable','en_cadencia','revisar_cadencia','confirmar_recencia'].includes(r.estado))return null;
  const ps=lista(personas).filter(p=>p?.id===r.responsable_id),owners=lista(r.responsables_ids);
  const idValido=v=>typeof v==='string'&&/^[A-Za-z0-9_-]{1,100}$/.test(v),roles=ps.length===1?ps[0].puestos:null;
  const owner=idValido(r.responsable_id)&&owners.length===1&&owners[0]===r.responsable_id&&ps.length===1&&ps[0].estado==='activo'&&ps[0].activo!==false&&Array.isArray(roles)&&roles.every(idValido)&&new Set(roles).size===roles.length&&roles.includes('trafficker');
  const ultima=fechaValidaControl(r.ultima_confirmada)&&r.ultima_confirmada<=hoy&&lista(r.fuentes_operativas).some(e=>e?.tipo==='reunion_celebrada'&&e.fecha===r.ultima_confirmada&&['zoom','fathom','ghl','registro_local','evidencia interna verificada'].includes(e.fuente))?r.ultima_confirmada:null;
  const proxima=ultima&&r.proxima_revision===new Date(Date.parse(ultima+'T12:00:00Z')+15*864e5).toISOString().slice(0,10)?r.proxima_revision:null;
  const completa=doc.cobertura_reuniones?.completa===true&&fechaValidaControl(doc.cobertura_reuniones.desde)&&doc.cobertura_reuniones.desde<=ultima&&doc.cobertura_reuniones.hasta===hoy;
  const estado=r.estado==='en_cadencia'?(owner&&ultima&&proxima&&hoy<=proxima?'en_cadencia':'sin_dato'):r.estado==='revisar_cadencia'?(owner&&ultima&&proxima&&hoy>proxima&&completa?'revisar_cadencia':'confirmar_recencia'):r.estado;
  return {ultima_confirmada:ultima,proxima_revision:proxima,estado,responsable_id:owner?r.responsable_id:null};
}
// 241: DTOs aditivos desde documentos YA autorizados. Los permisos de pauta
// llegan explícitamente del llamador; nunca se deducen de cartera, rol o importe.
function selloEvidenciaControl(doc) {
  const f = doc?.generado || doc?._meta?.generado || doc?.meta?.generado;
  if (typeof f !== 'string' || !/^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?)?$/.test(f) || !fechaValidaControl(f.slice(0,10))) return null;
  const hora = /[T ](\d{2}):(\d{2})(?::(\d{2}))?/.exec(f);
  if (hora && (Number(hora[1]) > 23 || Number(hora[2]) > 59 || Number(hora[3] || 0) > 59)) return null;
  const zona=/(Z|[+-](\d{2}):(\d{2}))$/.exec(f);
  if(zona&&zona[1]!=='Z'&&(+zona[2]>14||+zona[3]>59||(+zona[2]===14&&+zona[3]!==0)))return null;
  if(!Number.isFinite(Date.parse(f.length===10?f+'T00:00Z':f.replace(' ','T'))))return null;
  return f;
}
export function pautaHorasControl(doc, cid, hoy, permisosPautaIds = []) {
  if (!lista(permisosPautaIds).includes(cid) || !fechaValidaControl(hoy)) return null;
  const r = unico(doc, 'clientes', cid), periodo = doc?.mes_cuota, sello = selloEvidenciaControl(doc);
  const horas = numero(r?.cuota_horas?.pautadas);
  if (!r || horas === null || typeof periodo !== 'string' || !/^\d{4}-(0[1-9]|1[0-2])$/.test(periodo) ||
      periodo > hoy.slice(0,7) || !fechaValidaControl(sello?.slice(0,10)) || sello.slice(0,10) > hoy) return null;
  return { valor: `${horas} h de referencia`, estado: 'gris', fuente: 'Pauta mensual · copia autorizada', fecha: sello,
    horas, periodo, cobertura: 'parcial', origen: 'referencia_economica', presupuesto_confirmado: false,
    detalle: `Referencia mensual ${periodo}; no acredita presupuesto aprobado por proyecto. Se muestra separada de las horas consumidas y no calcula desviación entre meses.` };
}
export function reunionHistoricaControl(doc, cid, hoy) {
  const r = unico(doc, 'clientes', cid), sello = selloEvidenciaControl(doc), periodo = r?.mes;
  if (!fechaValidaControl(hoy) || !fechaValidaControl(r?.ultima) || r.ultima > hoy ||
      !fechaValidaControl(sello?.slice(0,10)) || sello.slice(0,10) > hoy ||
      typeof periodo !== 'string' || !/^\d{4}-(0[1-9]|1[0-2])$/.test(periodo) || periodo > hoy.slice(0,7)) return null;
  if (r.ultima > sello.slice(0,10)) return null;
  return { valor: `Último registro: ${r.ultima}`, estado: 'gris', fuente: 'Reuniones · copia histórica', fecha: sello,
    fecha_registro: r.ultima, periodo_fuente: periodo, cobertura: 'parcial', celebrada_confirmada: false,
    responsable_confirmado: false,
    detalle: `Última fecha registrada en la copia; periodo de referencia ${periodo}. No confirma celebración, asistencia, responsable histórico ni cumplimiento de una cadencia vigente.` };
}
// El timestamp de construcción no acredita la lectura de Desk. Sin hora actual explícita sólo se compara por día.
export function fuenteDeskControl(doc,hoy) {
  const sello=v=>{
    if(typeof v!=='string'||!/^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?)?$/.test(v)||!fechaValidaControl(v.slice(0,10)))return null;
    const hora=/[T ](\d{2}):(\d{2})(?::(\d{2}))?/.exec(v);
    if(hora&&(Number(hora[1])>23||Number(hora[2])>59||Number(hora[3]||0)>59))return null;
    const valor=Date.parse(v.length===10?v+'T00:00:00':v.replace(' ','T'));
    return Number.isFinite(valor)?{texto:v,dia:v.slice(0,10),valor}:null;
  };
  const d=doc?.fuentes?.desk,lectura=sello(d?.hora),construccion=sello(doc?.generado);
  if(!fechaValidaControl(hoy)||!lectura||!construccion||lectura.dia>hoy||construccion.dia>hoy||lectura.valor>construccion.valor||!['bien','dato_viejo'].includes(d?.estado))return null;
  if(d.estado==='bien'&&(d.error||(Array.isArray(d.errores)&&d.errores.length)))return null;
  return {fecha:lectura.texto,calculado:construccion.texto,anterior:d.estado==='dato_viejo'};
}
// La cola es una copia parcial por persona, no inventario completo de proyectos.
function pendientesControl(doc, cid, hoy) {
  const sello = doc?.fuentes?.tareas?.hora;
  if (!Array.isArray(doc?.cola) || !fechaValidaControl(sello?.slice(0,10)) || sello.slice(0,10) > hoy) return celda('Sin dato', 'gris', 'ClickUp · cola visible', null, 'Sin cola y fecha de origen válidas; no se acredita que no haya pendientes.');
  const filas = doc.cola.filter(t => t?.cli === cid);
  const tareas = new Map(); let ambiguas = false;
  for (const t of filas) {
    if (typeof t.id !== 'string' || !/^[\w-]+$/.test(t.id)) { ambiguas = true; continue; }
    const vence = t.vence == null || t.vence === '' ? null : fechaValidaControl(t.vence) ? t.vence : 'invalida';
    const previa = tareas.get(t.id);
    if (vence === 'invalida' || (previa && previa.vence !== vence)) ambiguas = true;
    tareas.set(t.id, { vence });
  }
  if (ambiguas) return celda('Por contrastar', 'gris', 'ClickUp · cola visible', {generado:sello}, 'Identificadores o fechas ausentes/incoherentes; no se calcula un plazo ni un total fiable.');
  const fechas = [...tareas.values()].map(t => t.vence).filter(Boolean).sort();
  const vencidas = fechas.filter(f => f < hoy).length;
  const proximas = fechas.filter(f => f >= hoy);
  const proxima = proximas[0] || null;
  const sinFecha = tareas.size - fechas.length;
  return { ...celda(tareas.size ? `${tareas.size} en cola visible${vencidas ? ` · ${vencidas} con fecha pasada` : ''}` : 'Sin filas en esta cola', vencidas ? 'ambar' : 'gris', 'ClickUp · cola visible', {generado:sello}, `${proxima ? `Próximo plazo registrado: ${proxima}. ` : 'Sin próximo plazo registrado. '}${sinFecha} sin fecha. Una tarea compartida cuenta una vez; fecha pasada no demuestra incumplimiento ni entrega pendiente. Copia parcial, sin cobertura de todos los proyectos.`), total_visible:tareas.size, fechas_pasadas:vencidas, proxima_fecha:proxima, sin_fecha:sinFecha };
}
export function prepararControlCartera({ clientes, persona_id, esOps, carteraIds, asignaciones, personas = [], fuentes = {}, hoy, permisosPautaIds = [] }) {
  const idsCuenta = new Set(lista(carteraIds));
  const activos = lista(clientes).filter(c => c?.activo_confirmado === true && typeof c.id === 'string' && /^[\w-]+$/.test(c.id) && (esOps || idsCuenta.has(c.id)));
  return activos.map(c => {
    const cid = c.id;
    const serviciosLista = [...new Set(SERVICIOS_CONTROL.filter(([key]) => siServicio(c.servicios?.[key])).map(([,nombre]) => nombre))];
    const asignacionesElegibles = lista(asignaciones).filter(a => a.cliente_id === cid && a.silla === 'account' && a.principal === true && a.persona_id && (!a.desde || (fechaValidaControl(a.desde) && a.desde <= hoy)) && (!a.hasta || (fechaValidaControl(a.hasta) && a.hasta >= hoy)) && !a.duda && !a.suplencia);
    const owners = [...new Set(asignacionesElegibles.map(a => a.persona_id))];
    // El núcleo contiene el equipo vigente autorizado; ctx.datos.asignaciones sólo incluye filas de la persona vista.
    const personaConfirmada = id => { const ps = lista(personas).filter(p=>p?.id===id); return ps.length===1 && ps[0].estado==='activo' && ps[0].activo!==false; };
    const equipoElegible = lista(c.equipo?.account).filter(a => a?.principal === true && !a.suplencia && !a.duda && ['confirmada','alta'].includes(a.confianza) && typeof a.persona_id === 'string' && personaConfirmada(a.persona_id)
      && (!a.desde || (fechaValidaControl(a.desde) && a.desde<=hoy)) && (!a.hasta || (fechaValidaControl(a.hasta) && a.hasta>=hoy)));
    const equipoOwners = [...new Set(equipoElegible.map(a=>a.persona_id))];
    const candidatos = [...new Set([...owners,...equipoOwners])];
    const owner = candidatos.length === 1 ? candidatos[0] : null;
    const ownerConfirmado = !!owner && (equipoElegible.some(a=>a.persona_id===owner && a.confianza==='confirmada') || asignacionesElegibles.some(a=>a.persona_id===owner && a.confianza==='confirmada'));
    const ownerDetalle = owner ? (ownerConfirmado ? 'Asignación confirmada en la proyección vigente autorizada.' : 'Asignación por confirmar: confianza alta en la proyección vigente autorizada; no se atribuye responsabilidad histórica.') : 'Sin responsable inequívoco en las fuentes autorizadas; ausencia o conflicto no se resuelven eligiendo la última fila.';
    const docs = fuentes;
    const b = unico(docs.bandeja, 'clientes', cid), p = unico(docs.produccion, 'proyectos', cid), r = unico(docs.reuniones, 'clientes', cid), a = unico(docs.nuevos, 'altas', cid);
    const metodos = lista(docs.metodo?.sugerencias).filter(s => s.cliente_id === cid && s.regla_id === 'seguimiento_quincenal_especialista' && s.cadencia_dias === 15 && s.responsable_role === 'trafficker');
    const seguimiento = seguimientoControl474(docs.metodo,cid,personas,hoy);
    const sinDato = (fuente, doc) => celda('Sin dato', 'gris', fuente, doc, 'Copia ausente, fila ambigua o medición no disponible; no acredita cumplimiento.');
    let reuniones = sinDato('Reuniones', docs.reuniones);
    if (metodos.length > 1) reuniones = sinDato('Método vigente: cadencia ambigua', docs.metodo);
    else if (seguimiento) reuniones = celda('Trafficker · 15 días', seguimiento.estado === 'en_cadencia' ? 'verde' : seguimiento.estado === 'revisar_cadencia' ? 'ambar' : 'gris', 'Método vigente', docs.metodo,
      `${seguimiento.ultima_confirmada ? `Última confirmada: ${texto(seguimiento.ultima_confirmada, 40)}.` : 'Última celebrada sin confirmar.'} ${seguimiento.proxima_revision ? `Revisar cadencia: ${texto(seguimiento.proxima_revision, 40)}; no es cita agendada.` : ''}`);
    else if (r) reuniones = celda(r.estado === 'ok' ? 'Registro histórico presente' : r.estado === 'sin_reunion' ? 'Sin registro mensual' : r.estado === 'exento' ? 'Exención registrada' : r.estado === 'no_aplica' ? 'No aplica según copia' : 'Por contrastar', 'gris', 'Zoom/CRM/Fathom', docs.reuniones,
      `Periodo ${texto(r.mes, 20) || 'sin fecha'}; ${r.ultima ? `última ${texto(r.ultima, 40)}` : 'última sin confirmar'}. Registro histórico: sin regla mensual vigente versionada no acredita cumplimiento actual ni exige reunión este mes. Fuentes parciales.`);
    const desk=fuenteDeskControl(docs.bandeja,hoy);
    let tickets=sinDato('Desk',null);
    if(b&&desk&&[b.sin_contestar,b.mas_48,b.entre_24_48].every(v=>numero(v)!==null&&Number.isSafeInteger(v))&&b.mas_48+b.entre_24_48<=b.sin_contestar) {
      tickets=celda(`${desk.anterior?'Última copia: ':''}${b.sin_contestar} pendientes · ${b.entre_24_48} entre 24–48h · ${b.mas_48} >48h`,desk.anterior?'gris':b.mas_48>0?'rojo':b.entre_24_48>0?'ambar':'gris','Desk',{generado:desk.fecha},
        `Lectura Desk ${desk.fecha}; edades calculadas en copia ${desk.calculado}. ${desk.anterior?'Último dato bueno: no confirma que sigan pendientes ni cero actual; no se agrega como medición vigente. ':'Antigüedad del registro, no prioridad asignada al ticket. '}Copia parcial; sin umbral adicional de frescura inventado.`);
      if(!desk.anterior)tickets.medicion={total:b.sin_contestar,entre_24_48:b.entre_24_48,mas_48:b.mas_48};
    }
    let revisiones = sinDato('ClickUp', docs.produccion);
    const medicionRevision = p?.revisiones_account;
    const selloFlujo = docs.produccion?.fuentes?.flujo?.hora;
    const revisionMedida = medicionRevision?.estado === 'medido' && medicionRevision.fuente === 'flujo' && fechaValidaControl(hoy) && selloEvidenciaControl({generado:medicionRevision.fecha}) !== null && medicionRevision.fecha === selloFlujo && medicionRevision.fecha.slice(0,10) <= hoy;
    if (p && revisionMedida && numero(p.rev_account) !== null && numero(p.rev_account_48) !== null && Number.isSafeInteger(p.rev_account) && Number.isSafeInteger(p.rev_account_48) && p.rev_account_48 <= p.rev_account) revisiones = celda(`${p.rev_account} en revisión · ${p.rev_account_48} >48h`, p.rev_account_48 > 0 ? 'ambar' : 'gris', 'ClickUp · flujo', { generado: selloFlujo }, 'Finalizar flujo no acredita aprobación. Esta copia no aporta un conteo exacto de 24–48h ni prioridad urgente de la tarea.');
    const selloHoras = docs.produccion?.fuentes?.horas?.hora;
    const horasLeidas = selloEvidenciaControl({generado:selloHoras}) !== null && fechaValidaControl(selloHoras?.slice(0,10)) && selloHoras.slice(0,10) <= hoy;
    const periodoHoras = fechaValidaControl(docs.produccion?.hoy) && docs.produccion.hoy <= hoy ? docs.produccion.hoy.slice(0,7) : null;
    const hm = p?.horas_medicion;
    const horasMedidas = p && horasLeidas && periodoHoras && selloHoras.slice(0,7)>=periodoHoras && hm?.estado==='medido' && hm.fuente==='horas' && hm.periodo===periodoHoras && hm.fecha===selloHoras && numero(p.horas_mes)!==null;
    const horas = horasMedidas ? celda(`${p.horas_mes} h registradas`, 'gris', 'ClickUp · horas', {generado:selloHoras}, `Periodo de imputación ${periodoHoras}; medición de horas acreditada por su descriptor. Total por cliente, no desglose por proyecto. La fecha de lectura no define el mes imputado. Previsión/capacidad no confirmadas.`)
      : p && horasLeidas && numero(p.horas_mes)>0 ? celda(`${p.horas_mes} h observadas`, 'gris', 'ClickUp · copia anterior', {generado:selloHoras}, 'Valor positivo de copia sin descriptor de medición válido por cliente/periodo. No se incluye como horas medidas ni se calcula una desviación; confirmar registro de origen.') : sinDato('ClickUp · horas', null);
    const altas = a ? celda(texto(a.siguiente?.nombre) || 'Hitos por contrastar', 'gris', 'Alta/onboarding', docs.nuevos, `${a.plazo?.limite ? `Límite registrado: ${texto(String(a.plazo.limite), 40)}. ` : ''}El hito y su fecha deben contrastarse con su evidencia; no implica entrega aceptada.`) : celda('Sin alta en esta copia', 'gris', 'Alta/onboarding', docs.nuevos, 'No significa que no sea cliente nuevo ni que el onboarding esté completo.');
    if (revisionMedida && revisiones.valor !== 'Sin dato') revisiones.medicion = {total:p.rev_account,mas_48:p.rev_account_48};
    if (horasMedidas) horas.medicion = {total:p.horas_mes,periodo:periodoHoras};
    const pendientes = pendientesControl(docs.produccion, cid, hoy);
    const presupuesto = celda('Sin presupuesto confirmado', 'gris', 'Planificación de horas', null, 'No hay una fuente vigente de horas presupuestadas por proyecto en los documentos autorizados de esta matriz. No se calcula desviación, margen ni horas disponibles.');
    const servicios = celda(serviciosLista.join(' · ') || 'Servicios por confirmar', 'gris', 'Catálogo autorizado', null, 'Sólo servicios explícitos marcados sí. Una asignación o actividad no demuestra contratación; sin fecha de contrato confirmada en esta matriz.');
    return { cliente_id: cid, nombre: texto(c.nombre) || cid, account_id: owner, owner_confirmado: ownerConfirmado, owner_detalle:ownerDetalle, servicios_lista: serviciosLista, servicios, pendientes, presupuesto, alcance_proyecto:'cliente_agrupado',
      pauta_horas: pautaHorasControl(docs.dinero_cliente, cid, hoy, permisosPautaIds),
      reunion_historica: reunionHistoricaControl(docs.reuniones, cid, hoy),
      contacto: celda('Pendiente de medir', 'gris', 'Contacto semanal', null, 'No hay una fuente confirmada de contacto semanal en esta matriz; no equivale a cero ni a cumplimiento.'),
      reuniones, tickets, revisiones, horas, altas };
  });
}

// Agrega sólo lo que la matriz autorizada ya muestra. Los parciales nunca se presentan como total completo.
export function resumirAccountsControl(filas) {
  const grupos = new Map();
  for (const fila of lista(filas)) {
    const id = fila.account_id || null;
    if (!grupos.has(id)) grupos.set(id, []);
    grupos.get(id).push(fila);
  }
  return [...grupos].map(([account_id, rows]) => {
    const agregar = (key, campo) => {
      const valido=v=>key==='horas'?numero(v)!==null&&v<=Number.MAX_SAFE_INTEGER:Number.isSafeInteger(v)&&v>=0;
      const medidas = rows.map(r => r[key]?.medicion?.[campo]).filter(valido);
      const suma=medidas.reduce((a,b)=>a+b,0);
      const representable=Number.isFinite(suma)&&suma<=Number.MAX_SAFE_INTEGER&&(key==='horas'||Number.isSafeInteger(suma));
      return {valor:medidas.length&&representable?suma:null, medidos:medidas.length, sin_dato:rows.length-medidas.length};
    };
    const horasRows = rows.filter(r => numero(r.horas?.medicion?.total) !== null&&r.horas.medicion.total<=Number.MAX_SAFE_INTEGER);
    const periodos = [...new Set(horasRows.map(r=>r.horas.medicion.periodo))];
    const horas = periodos.length === 1 ? {...agregar('horas','total'),periodo:periodos[0]} : {valor:null,medidos:0,sin_dato:rows.length,periodo:null};
    return {account_id,clientes:rows.length,asignaciones_confirmadas:rows.filter(r=>r.owner_confirmado).length,asignaciones_por_confirmar:rows.filter(r=>r.account_id&&!r.owner_confirmado).length,contacto_sin_dato:rows.length,
      tickets:agregar('tickets','total'),tickets24:agregar('tickets','entre_24_48'),tickets48:agregar('tickets','mas_48'),
      revisiones:agregar('revisiones','total'),revisiones48:agregar('revisiones','mas_48'),horas,
      reuniones15:rows.filter(r=>r.reuniones?.valor==='Trafficker · 15 días').length,
      reuniones_revisar:rows.filter(r=>r.reuniones?.valor==='Trafficker · 15 días' && r.reuniones.estado==='ambar').length,
      reuniones_confirmar:rows.filter(r=>r.reuniones?.valor==='Trafficker · 15 días' && r.reuniones.estado==='gris').length,
      reuniones_historicas:rows.filter(r=>r.reuniones?.fuente==='Zoom/CRM/Fathom').length,
      presupuesto_sin_dato:rows.length};
  });
}
