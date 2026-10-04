import {ambitoResumenInformes612,proyectarResumenInformes612,celdaInformeDeclarado612,agregarInformesDeclarados615} from './_informes_declarados_612.js';
import {celdaKpiCompacta396,LEYENDA_KPIS_396} from './_kpis_compactos_396.js';
import {cabeceraOperaciones423} from './_cabeceras_operaciones_423.js';
import {COLUMNAS_SEGUIMIENTO_404,LEYENDA_SEGUIMIENTO_404,ambitoSeguimiento404,proyectarSeguimiento404,seguimientoVigente404} from './_seguimiento_accounts_404.js';
import {CABECERAS_SCORE_408,cabecerasScore408,renderReferenciaScore408} from './_referencia_score_408.js';
import {cargarImputa390,celdaImputa390,imputaVigente390} from './_imputa_personal_390.js';
import {ambitoLlamadas353,proyectarLlamadas353,celdaLlamadas353,celdaLlamadasVigente353} from './_llamadas_historicas_353.js';
import {agregarHorasCartera349,celdaHorasCarteraVigente349} from './_horas_cartera_349.js';
import {COLUMNAS_ORDEN_348,disponibilidadOrden348,siguienteOrden348,ordenarClientes348} from './_orden_clientes_348.js';
import {ambitoPedidos344,proyectarPedidos344,celdaPedidos344,celdaPedidosVigente344,receptoresSinCartera344} from './_pedidos_macro_344.js';
import {ambitoAlarmas342,pintarAlarmas342} from './_alarmas_operaciones_342.js';
import {pintarTop388} from './_top_alarmas_388.js';
//263 · Recupera vAccounts/vControl/vScore/vClientes/vHoy del artifact.
// Sólo fuentes recortadas. No importa snapshots antiguos ni escribe en proveedores.
import { h, chipEstado, panel, logoCliente } from '../componentes.js';
import { prepararControlCartera, resumirAccountsControl } from './control_cartera.js';
import { pintarMapaControl250, COLUMNAS_CONTROL_250 } from './_control_artifact_250.js';
import { puestoControl239 } from './_control_cartera_ruta_239.js';
import { prepararResumenEvidencias } from './_evidencias_resumen.js';

export const KPIS263=Object.freeze(['Informe mensual','Reunión mensual','Correo semanal','Respuesta <48h','Revisión <48h','Semáforo al día','Horas en lo pautado','Nuevos en plazo']);
export const CLIENTES263=Object.freeze(['Cliente','Riesgo','Reglas','Semáforo','Sin responder','Última reunión','Llamadas (sep2026)','Horas / presup.','Tickets']);
export const REGLAS263=Object.freeze([
  {id:'resp',titulo:'Sin responder',sub:'+48h'}, {id:'sem',titulo:'Semáforo',sub:'sin rellenar'},
  {id:'rojo',titulo:'Semáforo',sub:'en rojo'}, {id:'reu',titulo:'Sin reunión',sub:'periodo de referencia'},
  {id:'mail',titulo:'Sin correo',sub:'esta semana'}, {id:'rev',titulo:'Revisión',sub:'tareas +48h'},
  {id:'new',titulo:'Nuevos',sub:'fuera de plazo'},
]);
const array=v=>Array.isArray(v)?v:[];
const numero=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0;
const fecha=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+'T00:00:00Z'))&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v;
const sello=(v,hoy)=>typeof v==='string'&&fecha(v.slice(0,10))&&v.slice(0,10)<=hoy&&Number.isFinite(Date.parse(v.replace(' ','T')))?v:null;
const sinDato=detalle=>({valor:'—',estado:'gris',detalle:detalle||'Sin evidencia suficiente en las fuentes autorizadas.'});
const observacion=(valor,detalle,estado='gris')=>({valor:String(valor),estado,detalle});
const nombres=ctx=>id=>id?(ctx.nombre?.(id)||'Persona por confirmar'):'Account por confirmar';
const unico=(filas,id,campo='cliente_id')=>{const fs=array(filas).filter(r=>r?.[campo]===id);return fs.length===1?fs[0]:null;};
const info=c=>[c?.detalle,c?.fuente?`Fuente: ${c.fuente}.`:'',c?.fecha?`Lectura: ${c.fecha_texto||c.fecha}.`:''].filter(Boolean).join(' ');

// Captura de ámbito actual: el DTO detalle antiguo no concede acceso tras revocación.
export function ambitoAccounts316(ctx){
 try{
 const puesto=puestoControl239(ctx.real,ctx.persona);
 if(!ctx.servidor||!puesto||ctx.real?.activo===false||ctx.persona?.activo===false||typeof ctx.ver!=='function'||!Array.isArray(ctx.clientes))return null;
 // clientesVisibles puede ser una selección antigua. El catálogo actual del
 // contexto es quien ratifica ACT/detalle; un duplicado nunca elige un ganador.
 const canon=ctx.clientes,canonCounts=new Map();for(const c of canon)canonCounts.set(c?.id,(canonCounts.get(c?.id)||0)+1);
 const cs=array(ctx.clientesVisibles),counts=new Map();for(const c of cs)counts.set(c?.id,(counts.get(c?.id)||0)+1);
 const ids=cs.filter(c=>typeof c?.id==='string'&&counts.get(c.id)===1&&c.activo_confirmado===true&&c.activo!==false&&c.estado!=='baja'&&c.detalle===true&&canonCounts.get(c.id)===1&&canon.some(a=>a?.id===c.id&&a.activo_confirmado===true&&a.activo!==false&&a.estado!=='baja'&&a.detalle===true)&&ctx.ver({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true).map(c=>c.id).sort();
 const mods=['mi-dia','bandeja','produccion','reuniones','clientes-nuevos','horas','informes-mensuales','dinero-cliente'].map(m=>[m,ctx.veModulo?.(m)===true]);
 return {ids,firma:JSON.stringify([ctx.real.id,ctx.persona.id,ctx.real.estado,ctx.persona.estado,ctx.real.puestos,ctx.persona.puestos,puesto,!!ctx.soloLectura,ctx.hoy,ids,mods,
  ids.map(id=>[id,ctx.ver({tipo:'horas_pautadas',cliente_id:id})?.ok===true]),canon.map(c=>[c?.id,c?.activo_confirmado,c?.detalle]),
  array(ctx.datos?.personas).map(p=>[p?.id,p?.estado,p?.activo,p?.puestos]),array(ctx.datos?.asignaciones).map(a=>[a?.cliente_id,a?.persona_id,a?.silla,a?.desde,a?.hasta,a?.principal,a?.confianza,a?.duda,a?.suplencia]),[...(ctx.carteraPorSilla?.account||[])].sort()])};
 }catch(_){return null;}
}

function gravedad263(ctx,id) {
  const d=ctx.verdad?.(id),ids=[d?.id,d?.cliente_id].filter(x=>x!=null);
  if(!ids.length||ids.some(x=>x!==id))return sinDato('No hay gravedad canónica inequívoca del cliente autorizado.');
  const g=d?.gravedad;
  return g==='critico'?{valor:'Crítico',estado:'rojo',detalle:'Gravedad canónica actual; no es la puntuación numérica de riesgo del artifact.'}:
    g==='atencion'?{valor:'Vigilar',estado:'ambar',detalle:'Gravedad canónica actual; no es la puntuación numérica de riesgo del artifact.'}:
    g==='bien'?{valor:'Bien',estado:'verde',detalle:'Estado canónico actual; no acredita cumplimiento de todos los KPIs.'}:sinDato('Estado canónico no disponible; no se reconstruye sumando alertas parciales.');
}

export function informe263(docs,cid,hoy) {
  if(!fecha(hoy))return sinDato('Fecha de consulta no válida.');
  const f=sello(docs.informes?._meta?.generado,hoy);
  const anterior=new Date(Date.parse(hoy+'T00:00:00Z'));anterior.setUTCDate(0);const mes=anterior.toISOString().slice(0,7);
  const filas=array(docs.informes?.filas).filter(r=>r?.cliente_id===cid&&r.mes===mes);
  if(filas.length!==1||!f)return sinDato('Sin fila mensual inequívoca y fecha de fuente de informes.');
  const r=filas[0],enviado=r.enviado;
  const dia=enviado&&fecha(enviado.fecha)?enviado.fecha:null;
  let prueba=false;
  try {
    const u=new URL(enviado?.url);
    prueba=u.protocol==='https:'&&['desk.zoho.eu','desk.zoho.com'].includes(u.hostname)&&!u.username&&!u.password&&!u.search&&!u.hash&&u.pathname!=='/'&&u.href.length<=2048;
  }catch(_){}
  const ticket=typeof enviado?.ticket==='number'?Number.isSafeInteger(enviado.ticket)&&enviado.ticket>0:
    typeof enviado?.ticket==='string'&&/^[1-9]\d{0,19}$/.test(enviado.ticket);
  const asunto=typeof enviado?.asunto==='string'?enviado.asunto:'';
  const meses=['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];
  const mesesNombrados=meses.map((m,i)=>new RegExp('\\b'+m+'\\b','i').test(asunto)?i+1:null).filter(x=>x!==null);
  // Contrato del productor: thread EMAIL saliente, asunto mensual y ticket.
  // La copia no conserva autor del envío ni prueba de recepción del cliente.
  const mensual=/informe|resultados|reporte|report/i.test(asunto)&&(/mensual/i.test(asunto)||mesesNombrados.length===1)&&mesesNombrados.every(m=>m===Number(mes.slice(5)))&&!/semanal|newsletter/i.test(asunto);
  if(r.estado==='enviado'&&enviado?.metodo==='Desk en vivo'&&dia&&dia>=mes+'-01'&&dia<=hoy&&dia<=f.slice(0,10)&&ticket&&prueba&&mensual&&typeof enviado.pdf==='boolean') {
    return {...observacion('1 obs.',`Un envío mensual observado en la copia Desk para ${mes}, fechado ${dia}; ticket ${enviado.ticket}. Prueba: ${enviado.url}. Lectura ${f}. La identidad cliente procede del productor; no se revalida aquí el destinatario original. No acredita recepción, cumplimiento de plazo ni autor del envío; el account actual no se atribuye como autor.`),medicion:{tipo:'envio_observado',periodo:mes,observados:1,fecha:dia,fuente:'Desk en vivo',autor:null,cobertura:'parcial',cumplimiento:null}};
  }
  return observacion(`Registro ${mes}`,`Registro de informe en copia del ${f}${dia?`; fecha registrada ${dia}`:''}. Envío por contrastar: no hay evidencia completa de salida mensual. Preparado, tarea hecha, fecha sola o verificación histórica manual no se cuentan como envío observado. No se atribuye al account actual ni se juzga cumplimiento.`);
}

// Registros manuales y salida Desk conservan procedencia separada; nunca se suman.
export function combinarInformeDeclarado614(observado,declarado) {
  if(!Number.isSafeInteger(declarado?.informes_declarados)||declarado.informes_declarados<0||declarado.estado!=='gris'||typeof declarado.vigente!=='function'||!declarado.vigente())return observado;
  if(observado?.medicion?.tipo==='envio_observado')return {...observado,detalle:`${info(observado)} Registro manual separado: ${declarado.valor}. ${declarado.detalle}`,vigente:declarado.vigente};
  return {...declarado,detalle:`${declarado.detalle} ${info(observado)}`,cumplimiento:null};
}

export function combinarInformesCartera617(rows,manual,anterior) {
  if(!Array.isArray(rows)||!rows.length||rows.some(r=>typeof r?.cliente_id!=='string')||new Set(rows.map(r=>r.cliente_id)).size!==rows.length)return anterior;
  const observados=rows.filter(r=>r.kpis?.[0]?.medicion?.tipo==='envio_observado');
  if(!observados.length)return combinarInformeDeclarado614(anterior,manual);
  const celda={...observacion(`${observados.length} obs.`,`${observados.length}/${rows.length} proyectos de la cartera visible tienen salida mensual observada en Desk. No es total de envíos ni cumplimiento; no se atribuye al account actual. ${observados.map(r=>info(r.kpis[0])).join(' ')}`),medicion:{tipo:'envio_observado',cobertura:'parcial',cumplimiento:null,autor:null}};
  return combinarInformeDeclarado614(celda,manual);
}

function agregar263(rows,fn,detalle) {
  const xs=rows.map(fn),medidas=xs.filter(x=>numero(x));
  return medidas.length?observacion(medidas.reduce((a,b)=>a+b,0),`${detalle} ${medidas.length}/${rows.length} clientes medidos; el resto sin dato. Copia parcial.`):sinDato(detalle+' Ningún cliente tiene medición acreditada.');
}

function horasPauta263(r) {
 const horas=r.horas.valor.replace(' h registradas',' h').replace('Sin dato','—'),p=r.pauta_horas,mes=r.horas.medicion?.periodo;
 const mesValido=v=>typeof v==='string'&&/^\d{4}-(?:0[1-9]|1[0-2])$/.test(v);
 const etiqueta=v=>new Intl.DateTimeFormat('es-ES',{timeZone:'UTC',month:'short',year:'numeric'}).format(new Date(v+'-01T00:00Z')).replace(/\./g,'');
 const ref=p&&numero(p.horas)&&mesValido(p.periodo)?p:null;
 const mismo=ref&&mesValido(mes)&&mes===ref.periodo;
 const valor=mismo?`${horas} / ${ref.horas} h ref. · ${etiqueta(mes)}`:
  `${horas}${mesValido(mes)?` · ${etiqueta(mes)}`:''}${ref?` · pauta ${ref.horas} h ref. · ${etiqueta(ref.periodo)}`:' · pauta —'}`;
 return observacion(valor,`${info(r.horas)} ${ref?info(ref):info(r.presupuesto)} La pauta es referencia económica, no objetivo ni presupuesto confirmado. ${mismo?'Mismo mes; no se calcula porcentaje de cumplimiento.':'Periodos separados; no se emparejan ni comparan observación y pauta de meses distintos.'}`);
}

// Sólo presentación: el DTO y sus pruebas de periodo/grants conservan horasPauta263.
export function horasDisplay413(r) {
 const base=r.horasPauta,mes=r.horas.medicion?.periodo,p=r.pauta_horas;
 const valido=v=>typeof v==='string'&&/^\d{4}-(?:0[1-9]|1[0-2])$/.test(v);
 const etiqueta=v=>new Intl.DateTimeFormat('es-ES',{timeZone:'UTC',month:'short',year:'2-digit'}).format(new Date(v+'-01T00:00Z')).replace(/\./g,'');
 const observado=r.horas.valor.replace(' h registradas',' h').replace('Sin dato','—');
 const ref=p&&numero(p.horas)&&valido(p.periodo)?p:null;
 const pauta=ref?`${ref.horas.toLocaleString('es-ES',{maximumFractionDigits:20})} h†`:null;
 const mismo=ref&&valido(mes)&&mes===ref.periodo;
 const valor=mismo?`${observado} / ${pauta}`:`${observado}${valido(mes)?` (${etiqueta(mes)})`:''}${ref?` · ${pauta} (${etiqueta(ref.periodo)})`:''}`;
 return {...base,valor,detalle:`${base.valor}. ${info(base)}`};
}

function contactoDisplay413(celda) {
 const original=String(celda.valor),valor=original.replace(/^(\d+) declarados?$/, '$1 decl.');
 return valor===original?celda:{...celda,valor,detalle:`${original}. ${info(celda)}`};
}

export function prepararAccounts263(ctx,docs={}) {
  const puesto=ctx.real?.activo===false||ctx.persona?.activo===false?null:puestoControl239(ctx.real,ctx.persona),ops=['direccion','operaciones'].includes(puesto);
  const hoy=ctx.hoy,cuentas=new Map();
  for(const c of array(ctx.clientesVisibles))if(c?.id)cuentas.set(c.id,(cuentas.get(c.id)||0)+1);
  const permitido=ambitoAccounts316(ctx);
  const clientes=array(ctx.clientesVisibles).filter(c=>c?.activo_confirmado===true&&cuentas.get(c.id)===1&&c.detalle===true&&permitido?.ids.includes(c.id));
  const activos=array(ctx.datos?.personas); // El helper comprueba unicidad también frente a bajas duplicadas.
  const pautaPermitida=ctx.servidor&&ctx.real?.id===ctx.persona?.id&&ctx.veModulo?.('dinero-cliente')&&typeof ctx.ver==='function';
  const permisosPautaIds=pautaPermitida?clientes.filter(c=>ctx.ver({tipo:'horas_pautadas',cliente_id:c.id}).ok===true).map(c=>c.id):[];
  const rows=puesto&&fecha(hoy)?prepararControlCartera({clientes,persona_id:ctx.persona.id,esOps:ops,carteraIds:[...(ctx.carteraPorSilla?.account||[])],asignaciones:ctx.datos?.asignaciones||[],personas:activos,fuentes:docs,hoy,permisosPautaIds}):[];
  const base=rows.map(original=>{
    const ps=activos.filter(p=>p?.id===original.account_id);
    // La asignación vigente inequívoca puede tener confianza alta sin estar ratificada.
    // Conservamos su identidad, junto a owner_confirmado, sin convertirla en responsabilidad histórica.
    const responsable=!!original.account_id&&ps.length===1&&ps[0].estado==='activo'&&ps[0].activo!==false;
    const r={...original,account_id:responsable?original.account_id:null};
    const c=clientes.find(x=>x.id===r.cliente_id),g=gravedad263(ctx,r.cliente_id),ticket=r.tickets.medicion,rev=r.revisiones.medicion;
    const informe=informe263(docs,r.cliente_id,hoy);
    const mensual=r.reunion_historica;
    const kpis=[informe,mensual||sinDato('Sin registro mensual con fecha; la cadencia15d del trafficker es otra regla.'),r.contacto,r.tickets,r.revisiones,sinDato('Sin registro fechado que acredite la actualización del semáforo de este cliente.'),r.horas,sinDato('Alta observada no acredita cumplimiento de hitos/plazos del cliente.')];
    const observadosKpi=[informe.valor!=='—',!!mensual,false,!!ticket,!!rev,false,!!r.horas.medicion,false];
    // Ausencia de registro no acredita incumplimiento mensual vigente. Se conserva referencia.
    const reglas={resp:numero(ticket?.mas_48)?observacion(ticket.mas_48,info(r.tickets),ticket.mas_48>0?'rojo':'gris'):sinDato(info(r.tickets)),
      sem:sinDato('No hay un campo fechado que acredite cuándo se rellenó el semáforo.'),
      rojo:['verde','ambar','rojo'].includes(g.estado)?observacion(g.estado==='rojo'?1:0,g.detalle,g.estado==='rojo'?'rojo':'gris'):sinDato(g.detalle),
      reu:sinDato(mensual?info(mensual):info(r.reuniones)),mail:sinDato(info(r.contacto)),
      rev:numero(rev?.mas_48)?observacion(rev.mas_48,info(r.revisiones),rev.mas_48>0?'ambar':'gris'):sinDato(info(r.revisiones)),
      new:sinDato(info(r.altas))};
    const reglaDots=[{id:'R',titulo:'Respuesta',celda:reglas.resp},{id:'S',titulo:'Semáforo rellenado',celda:reglas.sem},{id:'M',titulo:'Reunión mensual',celda:reglas.reu},{id:'C',titulo:'Correo semanal',celda:reglas.mail},{id:'V',titulo:'Revisión',celda:reglas.rev},{id:'H',titulo:'Horas comparables',celda:sinDato(info(r.horas))}];
    const b=unico(docs.bandeja?.clientes,r.cliente_id),fechaDesk=r.tickets.fecha;
    const espera=b&&r.tickets.medicion&&numero(b.dias_laborables_max)?observacion(`${b.dias_laborables_max} días lab.`,info(r.tickets),r.tickets.estado):sinDato('Sin antigüedad de correo acreditada; cero pendientes no equivale a una cobertura completa.');
    if(b&&r.tickets.medicion&&numero(b.dias_laborables_max))espera.medicion={dias_laborables:b.dias_laborables_max,fuente:'Desk',fecha:r.tickets.fecha};
    return {...r,c,g,kpis,observadosKpi,reglas,reglaDots,informe,espera,ultima:mensual?observacion(mensual.fecha_registro,info(mensual)):sinDato(info(r.reuniones)),
      llamadas:sinDato('No hay serie de llamadas por cliente/periodo con identidad confirmada en estas fuentes scoped. La fuente histórica Zadarma existe, pendiente DTO autorizado; no se copia raw ni se confunde llamada perdida con saliente.'),
      horasPauta:horasPauta263(r),
      ticketsTotal:numero(ticket?.total)?observacion(ticket.total,info(r.tickets),r.tickets.estado):sinDato(info(r.tickets))};
  });
  const groups=resumirAccountsControl(base).map(g=>{
    const rs=base.filter(r=>r.account_id===g.account_id),id=g.account_id||'__sin';
    const sumar=(key)=>agregar263(rs,r=>/^\d+$/.test(r.reglas[key]?.valor||'')?Number(r.reglas[key].valor):null,`Regla ${REGLAS263.find(x=>x.id===key)?.titulo||key}.`);
    const obs=(v,key)=>v?.valor===null?sinDato('Copia parcial: sin medición suficiente.'):observacion(v.valor,`${v.medidos}/${rs.length} clientes medidos; no total de toda la agencia. ${rs.map(r=>info(r[key])).filter(Boolean).join(' ')}`,
      v.valor>0&&rs.some(r=>r[key]?.estado==='rojo')?'rojo':v.valor>0&&rs.some(r=>r[key]?.estado==='ambar')?'ambar':'gris');
    const can=sinDato('Capacidad confirmada por account no disponible. Referencia histórica12 proyectos, no capacidad contractual ni permiso de carga actual.');
    const pendientesAsignacion=rs.filter(r=>r.owner_confirmado!==true).length;
    const revisa=obs(g.revisiones48,'revisiones');
    // Mismo umbral del mapa original y MiDía389, sólo sobre sumas medidas.
    if(numero(g.revisiones48?.valor))revisa.estado=g.revisiones48.valor>=6?'rojo':g.revisiones48.valor>0?'ambar':'gris';
    revisa.detalle+=' Mapa original: rojo desde6 tareas observadas >48h; amarillo de1 a5. Cero observado no acredita ausencia completa.';
    return {id,account_id:g.account_id,nombre:nombres(ctx)(g.account_id),clientes:rs.length,rows:rs,capacidad:can,
      asignaciones_por_confirmar:pendientesAsignacion,
      referenciaCarga:{valor:String(rs.length),estado:'gris',detalle:'Clientes/proyectos agrupados visibles de esta cartera, no inventario completo ni subproyectos.12 es referencia del artifact; no capacidad personal ratificada.'},
      kpis:KPIS263.map((k,i)=>{
        const conocidos=rs.filter(r=>r.observadosKpi[i]===true);
        const confirmar=sinDato(`${k}: cobertura ${conocidos.length}/${rs.length} clientes con alguna observación. No se calcula porcentaje de cumplimiento omitiendo desconocidos.`);
        return conocidos.length?observacion(`${conocidos.length}/${rs.length} registros`,confirmar.detalle,conocidos.some(r=>r.kpis[i].estado==='rojo')?'rojo':conocidos.some(r=>r.kpis[i].estado==='ambar')?'ambar':'gris'):confirmar;
      }),
      nota:sinDato('Nota ponderada histórica0–100 no vigente: falta cobertura y regla ratificada de los ocho KPIs. No renormalizar omitiendo desconocidos.'),empujes:sinDato('No hay registro vigente autorizado de empujes de Operaciones por account.'),
      reglas:Object.fromEntries(REGLAS263.map(r=>[r.id,sumar(r.id)])),
      celdas:{imputa:celdaImputa390(ctx,docs.imputa390,g.account_id),revisa,
        llama:sinDato('Sin serie saliente7d por persona. Referencias históricas de llamadas no cubren esta ventana.'),contesta:obs(g.tickets48,'tickets'),
        reune:sinDato('Registro histórico no confirma reunión mensual ni celebración; cadencia15d se consulta por cliente/trafficker.'),contacto:sinDato('No hay contacto semanal verificado; cero declaraciones no implica ausencia de contacto.'),
        abandonados:sinDato('No se acredita ausencia conjunta de horas/contactos14d.'),planifica:sinDato('No hay identidad canónica y transiciones completas de planning semanal en esta copia.'),tarde:sinDato('Sin serie verificada de reuniones celebradas tras15h durante45d.')},
    };
  });
  return {puesto,rows:base,groups,hoy};
}

// 301: declaraciones semanales separadas del cumplimiento de los ocho KPIs.
export function semanaDeclaracionesAccounts301(hoy) {
  if(!fecha(hoy))return null;
  const d=new Date(hoy+'T12:00:00Z');d.setUTCDate(d.getUTCDate()-((d.getUTCDay()+6)%7));
  return d.toISOString().slice(0,10);
}
export function ambitoDeclaracionesAccounts301(ctx,semana) {
  const roles=p=>p?.estado==='activo'&&p.activo!==false&&typeof p.id==='string'&&array(p.puestos).some(x=>['account','operaciones','direccion'].includes(x));
  if(!ctx.servidor||!roles(ctx.real)||!roles(ctx.persona)||!semana||typeof ctx.ver!=='function'||!ctx.veModulo?.('mi-trabajo'))return null;
  const cs=array(ctx.clientes||ctx.clientesVisibles),counts=new Map();
  for(const c of cs)if(c?.id)counts.set(c.id,(counts.get(c.id)||0)+1);
  if(cs.some(c=>typeof c?.id!=='string'||counts.get(c.id)!==1))return null;
  const ids=cs.filter(c=>c.activo_confirmado===true&&ctx.ver({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true).map(c=>c.id).sort();
  return {ids,real_id:ctx.real.id,vista_id:ctx.persona.id,
    firma:JSON.stringify([ctx.real.id,ctx.persona.id,ctx.real.estado,ctx.persona.estado,ctx.real.activo,ctx.persona.activo,ctx.real.puestos,ctx.persona.puestos,semana,ids])};
}
export function proyectarDeclaracionesAccounts301(respuesta,semana,antes,actual,matrizIds,vigente) {
  if(!antes||actual?.firma!==antes.firma||vigente!==true||!Array.isArray(matrizIds)||new Set(matrizIds).size!==matrizIds.length)return new Map();
  const identidad={real_id:antes.real_id,vista_id:antes.vista_id,generacion:0};
  const d=prepararResumenEvidencias({respuesta,semana_inicio:semana,cliente_ids:antes.ids,
    identidad,identidad_actual:identidad,vigente:true});
  const permitidos=new Set(matrizIds.filter(id=>antes.ids.includes(id)));
  return new Map(d.filas.filter(f=>permitidos.has(f.cliente_id)&&f.estado==='declarado').map(f=>[f.cliente_id,f]));
}
export function contactoDeclaradoAccounts301(rows,declaraciones,semana,anterior) {
  const fs=rows.map(r=>declaraciones.get(r.cliente_id)).filter(f=>f?.estado==='declarado'&&f.source_kind==='registro_equipo'&&f.verificacion_externa===false&&f.cumplimiento===null&&Number.isSafeInteger(f.contactos_declarados)&&f.contactos_declarados>=0);
  if(!fs.length)return anterior;
  const count=fs.reduce((n,f)=>n+f.contactos_declarados,0);
  const celda={valor:`${count} declarado${count===1?'':'s'}`,estado:'gris',
    detalle:`${fs.length}/${rows.length} clientes con fila autorizada. Semana desde ${semana} (Europe/Madrid). Registro manual del equipo, no verificación externa. Cero sólo significa cero declaraciones en el registro, no ausencia de actividad. No acredita correo semanal ni cumplimiento.`,
    cumplimiento:null,verificacion_externa:false,source_kind:'registro_equipo'};
  // Una declaración no sustituye un dato observado de una fuente distinta ni su evaluación.
  if(anterior&&typeof anterior.valor==='string'&&!['—','Sin dato','-',''].includes(anterior.valor)&&anterior.source_kind!=='registro_equipo')
    return {...anterior,detalle:`${info(anterior)} ${celda.valor}. ${celda.detalle}`};
  return celda;
}

const diaImputa393=f=>new Intl.DateTimeFormat('es-ES',{timeZone:'UTC',day:'numeric',month:'short'}).format(new Date(f+'T00:00Z')).replace(/\./g,'');
const CSS=`.oa263{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;color:#10132b;font-variant-numeric:tabular-nums;display:grid;gap:16px;min-width:0}.oa263>*{min-width:0}.oa263 .o263{min-width:0;background:white;border:1px solid #e1e4f1;border-radius:14px;overflow:hidden}.oa263 .o263>header{padding:14px 18px;border-bottom:1px solid #eceef7}.oa263 h2{font-size:16px;margin:0}.oa263 .scroll263{overflow:auto;padding:4px 14px 10px}.oa263 table{border-collapse:collapse;width:100%;min-width:960px;font-size:13px}.oa263 th{text-align:left;font-size:11px;letter-spacing:.035em;text-transform:uppercase;color:#777d9b;font-weight:700;padding:10px 8px;border-bottom:1px solid #eceef7;white-space:normal;word-break:normal}.oa263 td{padding:6px 8px;border-bottom:1px solid #eceef7;vertical-align:middle;line-height:1.3}.oa263 td button,.oa263 td a{font:inherit}.oa263 .dato263{border:0;background:transparent;min-height:44px;padding:2px 4px;cursor:pointer;text-align:left}.oa263 .carteras263{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(290px,100%),1fr));gap:14px}.oa263 .cartera263{border:1px solid #e1e4f1;border-radius:14px;padding:16px;background:white}.oa263 .cartera263{min-width:0}.oa263 .cartera263 dd{margin-left:0}.oa263 .cartera263 .dato263{max-width:100%;box-sizing:border-box}.oa263 .cartera263 .chip{white-space:normal;overflow-wrap:anywhere;max-width:100%;box-sizing:border-box}.oa263 .cartera263 h3{font-size:17px;margin:0 0 10px}.oa263 .refs263{font-size:12px;color:#777d9b}.oa263 .cli263{display:flex;gap:6px;flex-wrap:wrap}.oa263 .detalle263{padding:14px 18px;background:#f5f6fb;border:1px solid #e1e4f1;border-radius:12px}.oa263 .detalle263 p{white-space:pre-wrap;margin:8px 0;font-size:13px}.oa263 .filtros263{display:flex;flex-wrap:wrap;gap:8px;align-items:center}.oa263 .filtros263 select,.oa263 .filtros263 input[type=search]{min-height:44px;max-width:100%;min-width:0;border:1px solid #e1e4f1;border-radius:8px;background:white;padding:8px 10px;font:inherit;color:inherit}.oa263 .filtros263 label{display:flex;align-items:center;gap:5px;min-height:44px;font-size:13px}.oa263 .filtros263 input[type=checkbox]{width:18px;height:18px}.oa263 .filtros263 input:focus-visible,.oa263 .filtros263 select:focus-visible{outline:2px solid #6366f1;outline-offset:2px}.oa263 .reglas263{display:flex;gap:3px}.oa263 .reglas263 button{padding:2px 5px;min-height:44px}.oa263 td:first-child{min-width:170px}.oa263 .refs263 summary{cursor:pointer}.oa263 .proyectos315 .scroll263{max-height:65vh}.oa263 .proyectos315 table{min-width:960px;table-layout:fixed;font-size:12px}.oa263 .proyectos315 td,.oa263 .proyectos315 th{padding:6px 4px}.oa263 .proyectos315 td:first-child,.oa263 .proyectos315 th:first-child{width:140px;min-width:140px}.oa263 .proyectos315 th:nth-child(2){width:95px}.oa263 .proyectos315 .chip{white-space:normal;padding:4px 6px;font-size:11px;max-width:100%;box-sizing:border-box;overflow-wrap:anywhere}.oa263 .proyectos315 th{font-size:10px}.oa263 .proyectos315 th{position:sticky;top:0;background:#fff;z-index:2}.oa263 .proyectos315 td:first-child,.oa263 .proyectos315 th:first-child{position:sticky;left:0;background:#fff;z-index:3}.oa263 .proyectos315 th:first-child{z-index:4}.oa263 .proyectos315 .dato263{white-space:normal;max-width:100%;padding:2px 0}.oa263 .proyectos315 td:nth-child(2){min-width:0}.oa263 [data-clientes-orden="348"] td:first-child,.oa263 [data-clientes-orden="348"] th:first-child{position:sticky;left:0;background:#fff;z-index:2;min-width:170px;box-shadow:2px 0 0 #eceef7}.oa263 [data-clientes-orden="348"] th:first-child{z-index:3}`;

function tabla263(titulo,columnas,rows,celda,atributos={},cabeceras=[]) {
  return h('section',{class:'o263',...atributos},h('header',{},h('h2',{},titulo)),h('div',{class:'scroll263',tabindex:0,'aria-label':`${titulo}: tabla desplazable`},
    h('table',{},h('thead',{},h('tr',{},columnas.map((t,i)=>{const m=cabeceraOperaciones423(t),attrs=cabeceras[i]?.attrs||{},completo=attrs.title||m.completo;const elemento=cabeceras[i]?.elemento;return h('th',{scope:'col',title:completo||null,'aria-label':completo||null,...attrs},typeof elemento==='string'?cabeceraOperaciones423(elemento).breve:elemento||m.breve);}))),h('tbody',{},rows.map(r=>h('tr',{},columnas.map((_,i)=>h('td',{},celda(r,i))))),
      rows.length?null:h('tr',{},h('td',{colspan:columnas.length},'Sin filas autorizadas con estos filtros. No acredita ausencia de actividad.'))))));
}

export async function renderAccounts263(cont,ctx,subruta='accounts') {
  const root=h('div',{class:'oa263','data-operaciones-accounts-263':subruta});cont.append(root);
  const inicial=ambitoAccounts316(ctx);
  const vigente=()=>{
    if(!root.isConnected)return false;
    if(typeof ctx.vigente==='function'&&!ctx.vigente()){root.replaceChildren(h('p',{role:'status'},'La sesión ha cambiado. Abre de nuevo esta comparativa.'));return false;}
    if(!inicial||ambitoAccounts316(ctx)?.firma!==inicial.firma){root.replaceChildren(h('p',{role:'status'},'El acceso ha cambiado. Abre de nuevo esta comparativa.'));return false;}
    return true;
  };
  const puesto=ctx.real?.activo===false||ctx.persona?.activo===false?null:puestoControl239(ctx.real,ctx.persona);
  if(!puesto||!ctx.servidor||!inicial){root.append(h('p',{class:'sub'},'Esta comparativa requiere una sesión autorizada y fuentes recortadas del servidor.'));return;}
  if(!vigente())return;
  const disponibles=[['bandeja','bandeja/por_cliente','bandeja'],['produccion','produccion/produccion','produccion'],['reuniones','reuniones/reuniones','reuniones'],['metodo','metodo/sugerencias','reuniones'],['nuevos','nuevos/nuevos','clientes-nuevos'],['informes','informes/informes','informes-mensuales']];
  const pauta=ctx.real?.id===ctx.persona?.id&&ctx.veModulo?.('dinero-cliente')&&typeof ctx.ver==='function'&&array(ctx.clientesVisibles).some(c=>c?.activo_confirmado===true&&c.detalle===true&&ctx.ver({tipo:'horas_pautadas',cliente_id:c.id}).ok===true);
  if(pauta)disponibles.push(['dinero_cliente','dinero_cliente/dinero_cliente','dinero-cliente']);
  root.append(h('p',{class:'sub',role:'status'},'Leyendo fuentes autorizadas…'));
  const parejas=await Promise.all(disponibles.map(async([key,ruta,mod])=>{
    if(!ctx.veModulo?.(mod))return [key,null];
    if(key==='metodo'&&!ambitoSeguimiento404(ctx))return [key,null];
    try{return [key,await(ruta==='metodo/sugerencias'?ctx.api(ruta):ctx.datosModulo(ruta))];}catch{return [key,null];}
  }));
  if(!vigente())return;
  const docs=Object.fromEntries(parejas),d=prepararAccounts263(ctx,docs);
  const scopeLlamadas353=['accounts','control','clientes'].includes(subruta)?ambitoLlamadas353(ctx):null;let modeloLlamadas353=null;
  const scopePedidos344=['accounts','control'].includes(subruta)?ambitoPedidos344(ctx):null;let modeloPedidos344=null;
  const semana=semanaDeclaracionesAccounts301(ctx.hoy);let declaraciones=new Map(),firmaDeclaraciones=null,modeloImputa393=null;
  const ctxInformes612=Object.create(ctx);ctxInformes612.vigente=vigente;
  const fechaMes614=new Date(ctx.hoy+'T00:00:00Z');fechaMes614.setUTCDate(0);
  const periodoInformes614=fechaMes614.toISOString().slice(0,7);
  const scopeInformes612=['accounts','control'].includes(subruta)?ambitoResumenInformes612(ctxInformes612,periodoInformes614):null;
  if(scopeInformes612)scopeInformes612.vigente=vigente;
  let modeloInformes612=null;
  if(!vigente())return;
  root.replaceChildren(h('style',{},CSS));
  const detalle=h('section',{class:'detalle263',hidden:true,'aria-label':'Evidencia del indicador',tabindex:-1});
  const abrir=(titulo,c,volver)=>{if(!vigente())return;detalle.hidden=false;detalle.replaceChildren(h('strong',{},titulo),h('p',{},info(c)),h('button',{type:'button',class:'bt',on:{click:()=>{if(vigente()){detalle.hidden=true;volver?.focus?.();}}}},'Cerrar detalle'));detalle.focus?.();};
  const dato=(c,titulo,validar=()=>true)=>{let b;b=h('button',{type:'button',class:'dato263',title:info(c),'aria-label':`${titulo}: ${c?.valor||'Sin dato'}`,on:{click:()=>{if(!b.isConnected)return;if(!validar()||!celdaPedidosVigente344(ctx,c)){detalle.hidden=true;detalle.replaceChildren();pintar();return;}abrir(titulo,c,b);}}},chipEstado(c?.estado||'gris',c?.valor||'—'));return b;};
  let filtroAccount='',filtroRegla='',q='',soloRiesgo=false,soloNuevos=false;
  let ordenClientes348={key:'riesgo',direccion:'desc'},botonesOrden348=new Map();
  const selector=h('select',{'aria-label':'Account'},h('option',{value:''},'Todos los accounts autorizados'),d.groups.map(g=>h('option',{value:g.id},g.nombre)));
  const buscar=h('input',{type:'search',placeholder:'Buscar cliente','aria-label':'Buscar cliente'});
  const riesgo=h('input',{type:'checkbox','aria-label':'Solo riesgo alto'}),nuevos=h('input',{type:'checkbox','aria-label':'Solo nuevos con alta registrada'});
  const reset=h('button',{type:'button',class:'bt',on:{click:()=>{if(vigente()){filtroAccount='';filtroRegla='';q='';ordenClientes348={key:'riesgo',direccion:'desc'};selector.value='';buscar.value='';soloRiesgo=false;soloNuevos=false;riesgo.checked=false;nuevos.checked=false;pintar();}}}},'Restablecer filtros');
  const cuerpo=h('div',{style:{display:'grid',gridTemplateColumns:'minmax(0, 1fr)',gap:'16px',minWidth:'0'}});
  const scopeAlarmas=subruta==='hoy'?ambitoAlarmas342(ctx):null;
  let fuenteAlarmas342=null,cargadasAlarmas342=false;
  selector.addEventListener?.('change',()=>{if(vigente()){filtroAccount=selector.value;filtroRegla='';pintar();}});
  buscar.addEventListener?.('input',()=>{if(vigente()){q=buscar.value.trim().toLocaleLowerCase('es');pintar();}});
  riesgo.addEventListener?.('change',()=>{if(vigente()){soloRiesgo=riesgo.checked;pintar();}});
  nuevos.addEventListener?.('change',()=>{if(vigente()){soloNuevos=nuevos.checked;pintar();}});
  const cli=r=>ctx.veModulo?.('ficha')?h('a',{href:`#/ficha/${r.cliente_id}`,class:'celda-cli'},logoCliente(r.c),r.nombre):h('span',{},r.nombre);
  function pintarClientes(rows) {
    const disponibles=disponibilidadOrden348(rows,ctx.hoy),etiquetas={cliente:'cliente',riesgo:'riesgo canónico (no puntuación del artifact)',espera:'antigüedad de correo acreditada',registro:'último registro histórico (no celebración confirmada)',horas:'horas registradas del mismo mes (no pauta ni presupuesto)',tickets:'tickets observados del mismo corte'};
    botonesOrden348=new Map();
    const cabeceras=CLIENTES263.map((titulo,i)=>{const key=COLUMNAS_ORDEN_348[i];if(!key)return null;
      const seleccionado=ordenClientes348.key===key,dir=ordenClientes348.direccion==='asc'?'ascending':'descending';
      const b=h('button',{type:'button',class:'bt mini','data-orden-clientes':key,disabled:!disponibles[key],style:{minHeight:'44px'},title:`${titulo}. ${disponibles[key]?'Ordena sólo valores acreditados; desconocidos al final.':'Sin valores comparables acreditados para ordenar esta columna.'}`,
        'aria-label':`Ordenar por ${etiquetas[key]}${seleccionado?` · ${ordenClientes348.direccion==='asc'?'ascendente':'descendente'}`:''}`,
        on:{click:()=>{if(!vigente())return;if(!disponibilidadOrden348(rows,ctx.hoy)[key])return;ordenClientes348=siguienteOrden348(ordenClientes348,key);pintar();botonesOrden348.get(key)?.focus?.();}}},cabeceraOperaciones423(titulo).breve,h('span',{'aria-hidden':'true'},seleccionado?(ordenClientes348.direccion==='asc'?' ↑':' ↓'):''));
      botonesOrden348.set(key,b);return {attrs:{'aria-sort':seleccionado&&disponibles[key]?dir:'none'},elemento:b};
    });
    const ordenadas=ordenarClientes348(rows,ctx.hoy,ordenClientes348);
    const tabla=tabla263('Clientes activos',CLIENTES263,ordenadas,(r,i)=>[
      ()=>h('div',{},cli(r),h('small',{class:'refs263',title:r.owner_detalle},nombres(ctx)(r.account_id)+(r.account_id&&!r.owner_confirmado?' · asignación por confirmar':''))),()=>dato(r.g,'Riesgo canónico'),
      ()=>h('div',{class:'reglas263'},r.reglaDots.map(x=>{const f=declaraciones.get(r.cliente_id),detalle=x.id==='C'&&f?`${info(x.celda)} ${f.contacto_texto}. Semana desde ${semana}: registro declarado, no correo verificado ni cumplimiento.`:info(x.celda);return dato({...x.celda,detalle,valor:x.id.toUpperCase()},`${x.titulo} · ${r.nombre}`);})),
      ()=>dato(sinDato('Semáforo manual sin registro fechado confirmado en este DTO; el riesgo canónico se conserva en su columna.'),'Semáforo manual'),()=>dato(r.espera,'Antigüedad registrada'),()=>dato(r.ultima,'Última reunión registrada'),
      ()=>{const c=celdaLlamadas353(ctx,modeloLlamadas353,[r.cliente_id]);return dato(c,'Llamadas históricas · septiembre2026',()=>celdaLlamadasVigente353(ctx,modeloLlamadas353,c));},()=>dato(horasDisplay413(r),'Horas y referencia mensual'),()=>dato(r.ticketsTotal,'Tickets pendientes registrados'),
    ][i](),{'data-clientes-orden':'348'},cabeceras);
    return h('div',{},tabla,h('small',{class:'refs263','data-leyenda-horas':'413'},'† Pauta de referencia, no objetivo ni presupuesto confirmado. Periodos y cobertura en el detalle.'));
  }
  function pintar() {
    if(!vigente())return;
    if(firmaDeclaraciones&&(semanaDeclaracionesAccounts301(ctx.hoy)!==semana||ambitoDeclaracionesAccounts301(ctx,semana)?.firma!==firmaDeclaraciones)){declaraciones=new Map();firmaDeclaraciones=null;}
    const gs=d.groups.filter(g=>!filtroAccount||g.id===filtroAccount).map(g=>({...g,celdas:{...g.celdas,imputa:celdaImputa390(ctx,modeloImputa393,g.account_id),contacto:contactoDeclaradoAccounts301(g.rows,declaraciones,semana,g.celdas.contacto)}})),rows=d.rows.filter(r=>(!filtroAccount||(r.account_id||'__sin')===filtroAccount)&&(!q||r.nombre.toLocaleLowerCase('es').includes(q))&&(!soloRiesgo||r.g.estado==='rojo')&&(!soloNuevos||array(docs.nuevos?.altas).filter(a=>a?.cliente_id===r.cliente_id).length===1)).sort((a,b)=>({rojo:0,ambar:1,verde:2,gris:3}[a.g.estado]-{rojo:0,ambar:1,verde:2,gris:3}[b.g.estado])||a.nombre.localeCompare(b.nombre,'es'));
    if(subruta==='clientes'){cuerpo.replaceChildren(pintarClientes(rows));return;}
    if(subruta==='hoy') {
      const matriz=tabla263('Quién tiene registros en cada regla',['Account','Proyectos',...REGLAS263.map(r=>`${r.titulo} · ${r.sub}`)],gs,(g,i)=>{
        if(i===0)return g.nombre;if(i===1)return dato(g.referenciaCarga,'Proyectos visibles / referencia12');
        const regla=REGLAS263[i-2];let b;b=h('button',{type:'button',class:'dato263',on:{click:()=>{if(vigente()){filtroAccount=g.id;filtroRegla=regla.id;pintar();}}}},chipEstado(g.reglas[regla.id].estado,g.reglas[regla.id].valor));return b;
      });
      const detalleRows=filtroRegla?rows.filter(r=>r.reglas[filtroRegla]?.valor!=='—'):rows;
      const alarmas=tabla263('Registros de alarmas · copia autorizada',['Cliente','Account','Regla','Estado / evidencia'],detalleRows.flatMap(r=>REGLAS263.filter(x=>!filtroRegla||x.id===filtroRegla).filter(x=>r.reglas[x.id].valor!=='—').map(x=>({r,x}))),({r,x},i)=>[()=>cli(r),()=>nombres(ctx)(r.account_id),()=>x.titulo,()=>dato(r.reglas[x.id],`${r.nombre} · ${x.titulo}`)][i]());
      const primero=h('div',{'data-hoy-principal':'414'});
      const coleccion=h('div',{'data-coleccion-alarmas':'342'});
      const resto=h('details',{'data-hoy-coleccion':'414',on:{toggle:()=>{if(!vigente())cuerpo.replaceChildren();}}},
        h('summary',{style:{minHeight:'44px',display:'flex',alignItems:'center',cursor:'pointer'}},'Todas las alarmas y detalle por regla'),alarmas,coleccion);
      cuerpo.replaceChildren(primero,matriz,resto);
      if(!cargadasAlarmas342){
        const texto=scopeAlarmas?'Leyendo colección de alarmas autorizadas…':'Colección sin acceso en esta sesión.';
        primero.append(h('p',{role:'status'},texto));coleccion.append(h('p',{role:'status'},texto));
      }else{
        pintarTop388(primero,ctx,fuenteAlarmas342,d.rows,vigente);
        pintarAlarmas342(coleccion,ctx,fuenteAlarmas342,d.rows,vigente);
      }
      return;
    }
    const macro=pintarMapaControl250({h,filas:gs.map(g=>({...g,celdas:{...g.celdas,contacto:contactoDisplay413(g.celdas.contacto)}})),alSeleccionar:id=>{if(vigente()){filtroAccount=id;selector.value=id;pintar();}},titulo:'Control de accounts',vigente,celdaVigente:(_r,k)=>k!=='imputa'||!modeloImputa393||imputaVigente390(ctx,modeloImputa393),
      columnas:COLUMNAS_CONTROL_250.map(c=>c.key==='imputa'?{...c,sub:modeloImputa393&&imputaVigente390(ctx,modeloImputa393)?`horas · ${diaImputa393(modeloImputa393.desde)}–${diaImputa393(modeloImputa393.hasta)}`:'horas · 7 días'}:c.key==='contesta'?{...c,sub:'tickets abiertos +48h'}:c)});
    const score=tabla263('KPIs por account',['Account','Nota',...CABECERAS_SCORE_408,'Empujes de Mili'],gs,(g,i)=>{
      if(i===0)return g.nombre;if(i===1)return dato(g.nota,'Nota de cumplimiento');
      if(i===10)return dato(celdaPedidos344(ctx,modeloPedidos344,g.account_id),'Empujes de Mili · pedidos locales');
      const k=i-2,celda=k===0?combinarInformesCartera617(g.rows,agregarInformesDeclarados615(modeloInformes612,g.rows.map(r=>r.cliente_id)),g.kpis[k]):g.kpis[k];
      return dato(celdaKpiCompacta396(celda,{tabla:'account',indice:k}),KPIS263[k],()=>typeof celda?.vigente!=='function'||celda.vigente());
    },{},[null,null,...cabecerasScore408(),null]);
    const historicos344=receptoresSinCartera344(ctx,modeloPedidos344,d.groups.map(g=>g.account_id)).filter(f=>!filtroAccount||f.receptor_id===filtroAccount);
    const pedidosHistoricos344=historicos344.length?tabla263('Pedidos a receptores sin cartera actual visible',['Receptor','Pedidos semana','Pendientes','Última declaración','Evidencia'],historicos344,(f,i)=>{
      const c=celdaPedidos344(ctx,modeloPedidos344,f.receptor_id);
      const valores=[nombres(ctx)(f.receptor_id),String(f.pedidos_semana),String(f.pendientes),f.ultima_declaracion||'Sin declaración','Registro local'];
      return dato({...c,valor:valores[i]},`${nombres(ctx)(f.receptor_id)} · ${['Receptor histórico','Pedidos semana','Pendientes al corte','Última declaración','Evidencia'][i]}`);
    },{'data-pedidos-historicos':'344'}):null;
    const carteras=h('div',{class:'carteras263'},gs.map(g=>h('article',{class:'cartera263'},h('h3',{},g.nombre),g.asignaciones_por_confirmar?h('p',{class:'refs263'},`${g.asignaciones_por_confirmar} asignaciones vigentes por confirmar`):null,
      h('div',{class:'fila'},dato(g.referenciaCarga,'Carga y referencia'),dato(g.capacidad,'Capacidad confirmada')),
      h('dl',{},h('dt',{},'Tareas en revisión >48h'),h('dd',{},dato(g.celdas.revisa,'Revisiones registradas')),
        h('dt',{},'Sin respuesta >48h'),h('dd',{},dato(g.celdas.contesta,'Tickets pendientes registrados')),
        h('dt',{},'Contacto declarado · esta semana'),h('dd',{},dato(g.celdas.contacto,'Contacto declarado, no correo verificado')),
        h('dt',{},'Llamadas · septiembre2026'),h('dd',{},(()=>{const c=celdaLlamadas353(ctx,modeloLlamadas353,g.rows.map(r=>r.cliente_id));return dato(c,'Llamadas históricas · cartera actual',()=>celdaLlamadasVigente353(ctx,modeloLlamadas353,c));})()),
        h('dt',{},'Horas registradas · mes'),h('dd',{},(()=>{const c=agregarHorasCartera349(ctx,g.rows).horas;return dato(c,'Horas registradas de la cartera',()=>celdaHorasCarteraVigente349(ctx,g.rows,c));})()),
        h('dt',{},'Pauta horaria de referencia · mes'),h('dd',{},(()=>{const c=agregarHorasCartera349(ctx,g.rows).referencia;return dato(c,'Referencia horaria de la cartera',()=>celdaHorasCarteraVigente349(ctx,g.rows,c));})()),
        h('dt',{},'Cuota que lleva'),h('dd',{},dato(sinDato('Sin agregado financiero autorizado en este panel; no se deduce desde cantidad de proyectos.'),'Cuota'))),
      h('div',{class:'cli263'},g.rows.map(r=>h('button',{type:'button',class:'bt mini',on:{click:()=>{if(vigente()&&ctx.veModulo?.('ficha'))ctx.navegar?.(`ficha/${r.cliente_id}`);}}},r.nombre))))));
    const proyectos=tabla263('KPIs por proyecto',['Proyecto','Account','Riesgo',...CABECERAS_SCORE_408],rows,(r,i)=>{
      if(i===0)return cli(r);
      if(i===1)return h('span',{title:r.owner_detalle},nombres(ctx)(r.account_id)+(r.account_id&&!r.owner_confirmado?' · por confirmar':''));
      if(i===2)return dato(r.g,`Riesgo · ${r.nombre}`);
      const k=i-3,f=declaraciones.get(r.cliente_id);
      const celda=k===0?combinarInformeDeclarado614(r.kpis[k],celdaInformeDeclarado612(modeloInformes612,r.cliente_id)):k===2&&f?contactoDeclaradoAccounts301([r],declaraciones,semana,r.observadosKpi[k]===true?r.kpis[k]:sinDato(info(r.kpis[k]))):r.kpis[k];
      let valor=celda.valor;
      if(k===0&&typeof valor==='string'){valor=valor.replace(/ · \d{4}-\d{2}$/, '');valor=({'no_aplica':'No aplica','en_curso':'En curso','sin_tarea':'Sin tarea','hecho':'Tarea hecha'})[valor]||valor;}
      if(k===1&&typeof r.ultima?.valor==='string'&&fecha(r.ultima.valor))valor=r.ultima.valor;
      if(k===2&&typeof valor==='string')valor=valor.replace(' declarados',' decl.').replace(' declarado',' decl.');
      if(k===6&&typeof valor==='string')valor=valor.replace(' registradas','');
      if(k===3&&numero(r.tickets.medicion?.total)&&numero(r.tickets.medicion?.mas_48))valor=`${r.tickets.medicion.total} · ${r.tickets.medicion.mas_48} >48h`;
      if(k===4&&numero(r.revisiones.medicion?.total)&&numero(r.revisiones.medicion?.mas_48))valor=`${r.revisiones.medicion.total} · ${r.revisiones.medicion.mas_48} >48h`;
      return dato(celdaKpiCompacta396({...celda,valor,detalle:`${celda.valor}. ${info(celda)}`},{tabla:'proyecto',indice:k}),`${KPIS263[k]} · ${r.nombre}`,()=>typeof celda.vigente!=='function'||celda.vigente());
    },{class:'o263 proyectos315','data-kpis-proyecto':'315'},[null,null,null,...cabecerasScore408()]);
    const individuales=h('details',{class:'refs263','data-carteras-detalle':'315',...(cuerpo.querySelector?.('[data-carteras-detalle]')?.open===true?{open:true}:{})},h('summary',{},'Detalle por account · cartera y referencias'),carteras);
    const seguimientos=proyectarSeguimiento404(ctx,rows,{declaraciones,semana,metodo:docs.metodo});
    const seguimiento=tabla263('Reuniones y seguimiento',COLUMNAS_SEGUIMIENTO_404,seguimientos,(f,i)=>i===0?cli(rows.find(r=>r.cliente_id===f.cliente_id)):dato(f.celdas[i-1],`${COLUMNAS_SEGUIMIENTO_404[i]} · ${rows.find(r=>r.cliente_id===f.cliente_id)?.nombre||f.cliente_id}`,()=>seguimientoVigente404(ctx,d.rows,f.firma404)),{'data-seguimiento-accounts':'404'});
    cuerpo.replaceChildren(macro,score,h('p',{class:'refs263'},LEYENDA_KPIS_396.account),renderReferenciaScore408(h,vigente),...(pedidosHistoricos344?[pedidosHistoricos344]:[]),proyectos,h('p',{class:'refs263'},LEYENDA_KPIS_396.proyecto),seguimiento,h('p',{class:'refs263'},`Semana desde ${semana||'sin confirmar'}. ${LEYENDA_SEGUIMIENTO_404}`),pintarClientes(rows),h('p',{class:'refs263'},'Carga:12 proyectos/account es una referencia histórica. Horas personales:7 fechas anteriores a hoy; copia parcial. Los colores comparan con8h × días L–V, no jornada confirmada.'),individuales);
  }
  root.append(h('div',{class:'filtros263'},selector,buscar,h('label',{},riesgo,'Solo riesgo alto'),h('label',{},nuevos,'Solo nuevos'),reset),detalle,cuerpo,
    h('details',{class:'refs263'},h('summary',{},'Fuentes y alcance'),h('p',{},'Copia autorizada por identidad y cliente activo. Columnas originales conservadas. Gris: evidencia insuficiente o referencia histórica. Cifras observadas no acreditan cobertura completa, trabajo no registrado ni cumplimiento contractual. Pulsa una celda para ver su evidencia.')));
  pintar();
  const cargarImputa393=(async()=>{
    if(!['accounts','control'].includes(subruta)||!vigente())return;
    const ids=d.groups.map(g=>g.account_id).filter(x=>typeof x==='string'&&x);
    modeloImputa393=await cargarImputa390(ctx,ids);
    if(vigente())pintar();
  })();
  const cargarLlamadas353=(async()=>{
    if(!scopeLlamadas353||!vigente()||typeof ctx.api!=='function')return;
    try{const respuesta=await ctx.api('operaciones/llamadas/historico?periodo=2026-09');
      if(!vigente())return;modeloLlamadas353=proyectarLlamadas353(ctx,respuesta,scopeLlamadas353);
    }catch{if(!vigente())return;modeloLlamadas353=null;}
    if(vigente())pintar();
  })();
  // Lectura independiente de declaraciones301/colección342, sin esperar sus permisos o errores.
  const cargarPedidos344=(async()=>{
    if(!scopePedidos344||!vigente()||typeof ctx.api!=='function')return;
    try{const respuesta=await ctx.api('operaciones/pedidos-account/resumen');
      if(!vigente())return;
      modeloPedidos344=proyectarPedidos344(ctx,respuesta,scopePedidos344);
      const extras=receptoresSinCartera344(ctx,modeloPedidos344,d.groups.map(g=>g.account_id));
      const elegido=filtroAccount;
      selector.replaceChildren(h('option',{value:''},'Todos los accounts autorizados'),...d.groups.map(g=>h('option',{value:g.id},g.nombre)),...extras.map(f=>h('option',{value:f.receptor_id},`${nombres(ctx)(f.receptor_id)} · receptor sin cartera visible`)));
      selector.value=elegido;
    }catch{if(!vigente())return;modeloPedidos344=null;}
    if(vigente())pintar();
  })();
  const cargarInformes612=(async()=>{
    if(!scopeInformes612||!vigente()||typeof ctx.api!=='function')return;
    try{const respuesta=await ctx.api(`clientes/evidencias_kpi/informes?periodo_informe=${encodeURIComponent(periodoInformes614)}`);
      if(!vigente())return;
      modeloInformes612=proyectarResumenInformes612(ctxInformes612,respuesta,scopeInformes612);
    }catch{modeloInformes612=null;}
    if(vigente())pintar();
  })();
  // Una lectura para el ámbito completo antes de filtros; ninguna escritura ni ampliación de acceso.
  const antes=ambitoDeclaracionesAccounts301(ctx,semana);
  if(antes&&vigente()&&typeof ctx.api==='function'){
    try{
      const respuesta=await ctx.api(`clientes/evidencias_kpi/resumen?semana_inicio=${encodeURIComponent(semana)}`);
      if(!vigente()||semanaDeclaracionesAccounts301(ctx.hoy)!==semana)return;
      const actual=ambitoDeclaracionesAccounts301(ctx,semana);
      declaraciones=proyectarDeclaracionesAccounts301(respuesta,semana,antes,actual,d.rows.map(r=>r.cliente_id),vigente());
      firmaDeclaraciones=actual?.firma===antes.firma?antes.firma:null;
      if(!vigente()||ambitoDeclaracionesAccounts301(ctx,semana)?.firma!==antes.firma)return;
      pintar();
    }catch(_){/* Mantener fuentes observadas y desconocidos; nunca reutilizar una respuesta anterior. */}
  }
  // La colección es independiente del registro de declaraciones y sus permisos.
  if(subruta==='hoy') {
    if(scopeAlarmas) {
      try {const fuente=await ctx.datosModulo(scopeAlarmas.ruta);
        if(!vigente())return;
        if(ambitoAlarmas342(ctx)?.firma!==scopeAlarmas.firma){cargadasAlarmas342=true;fuenteAlarmas342=null;pintar();return;}
        fuenteAlarmas342=fuente;
      } catch {if(!vigente())return;if(ambitoAlarmas342(ctx)?.firma!==scopeAlarmas.firma){cargadasAlarmas342=true;fuenteAlarmas342=null;pintar();return;}}
    }
    cargadasAlarmas342=true;if(vigente())pintar();
  }

  await Promise.all([cargarPedidos344,cargarLlamadas353,cargarImputa393,cargarInformes612]);
}
