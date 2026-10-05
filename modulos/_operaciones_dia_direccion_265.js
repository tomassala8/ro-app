import {pintarNumerosSemanales449} from './_numeros_semanales_449.js';
import {renderRastroDeclarativo392} from './_rastro_declarativo_392.js';
import {renderDecisiones387} from './_operaciones_decisiones_387.js';
import { leerPlanes327 } from './_planes_pendientes_327.js';
import { pintarMiniserie439 } from './_miniserie_operaciones_439.js';
import { tendenciasFotos329 } from './_tendencias_operaciones_329.js';
import {renderPrioridades300} from './_operaciones_prioridades_300.js';
import { panelInformeSemanalOperaciones } from './_informe_semanal_operaciones.js';
import { renderResumen274 } from './_operaciones_resumen_274.js';
import { panelEncargos272, panelFotosControl272 } from './_operaciones_registros_272.js';
import { panelRituales269 } from './_operaciones_registros_269.js';
// Recuperación de vDia/vTomas/vRastro. Sólo DTOs recortados; no V7 ni almacenamiento paralelo.
import { h, panel, tablaDensa, chipEstado } from '../componentes.js';

const lista = x => Array.isArray(x) ? x : [];
const tx = x => typeof x === 'string' ? x : '';
const dato = x => x == null ? 'Sin dato confirmado' : String(x);
export function nombreCliente265(ctx,id){
  const filas=lista(ctx.clientesVisibles).filter(c=>c?.id===id&&c.activo_confirmado===true&&c.detalle!==false);
  return filas.length===1&&ctx.ver?.({tipo:'cliente_detalle',cliente_id:id})?.ok===true&&tx(filas[0].nombre).trim()?filas[0].nombre:'Cliente por confirmar';
}
const fecha = x => {
  const s=tx(x),m=/^(\d{2})-(\d{2})-(\d{4})(?: |$)/.exec(s);
  const d=m?`${m[3]}-${m[2]}-${m[1]}`:s.slice(0,10);
  return /^\d{4}-\d{2}-\d{2}$/.test(d)&&Number.isFinite(Date.parse(d+'T00:00:00Z'))&&new Date(d+'T00:00:00Z').toISOString().slice(0,10)===d?d:'Fecha sin confirmar';
};
const firma = ctx => JSON.stringify([ctx.real?.id, ctx.persona?.id]);
const identidadActiva = p => p?.estado === 'activo' && p?.activo !== false;

export function puerta265(ctx, clave) {
  if (!['dia','tomas','rastro'].includes(clave) || !identidadActiva(ctx.real) || !identidadActiva(ctx.persona)) return false;
  if (![ctx.real,ctx.persona].every(p => lista(p.puestos).some(r => ['direccion','operaciones'].includes(r)))) return false;
  if (!ctx.veModulo?.('mi-dia') || (ctx.vigente && !ctx.vigente())) return false;
  const ps = ctx.datos?.personas;
  if (!Array.isArray(ps)) return false;
  return [ctx.real,ctx.persona].every(p => {
    const xs = ps.filter(x => x?.id === p.id);
    return xs.length === 1 && identidadActiva(xs[0]) && lista(xs[0].puestos).some(r => ['direccion','operaciones'].includes(r));
  });
}

// Rastro 379: sólo las columnas técnicas existentes; nunca payloads de auditoría.
function firmaRastro379(ctx) {
  try { return JSON.stringify([ctx.real,ctx.persona,ctx.datos?.personas,
    ctx.veModulo?.('mi-dia'),ctx.veModulo?.('decisiones'),
    lista(ctx.clientes).map(c=>[c?.id,c?.activo_confirmado,c?.detalle]),
    lista(ctx.clientesVisibles).map(c=>[c?.id,c?.activo_confirmado,c?.detalle,
      ctx.ver?.({tipo:'cliente_detalle',cliente_id:c?.id})?.ok===true])]); }
  catch { return null; }
}
function puertaRastro379(ctx) {
  return [ctx.real,ctx.persona].every(p=>typeof p?.id==='string'&&p.id.trim()===p.id&&p.id.length>0) &&
    puerta265(ctx,'rastro') && ctx.veModulo?.('decisiones')===true &&
    [ctx.real,ctx.persona].every(p=>{
      const rows=lista(ctx.datos?.personas).filter(x=>x?.id===p.id),roles=p.puestos;
      return rows.length===1&&Array.isArray(roles)&&roles.length>0&&roles.every(x=>typeof x==='string')&&
        new Set(roles).size===roles.length&&Array.isArray(rows[0].puestos)&&
        JSON.stringify([...roles].sort())===JSON.stringify([...rows[0].puestos].sort());
    });
}
export function porDia379(ctx, rows, ahora=Date.now()) {
  const clientes=lista(ctx.clientes).length?lista(ctx.clientes):lista(ctx.clientesVisibles);
  const permitido=id=>typeof id==='string' && clientes.filter(c=>c?.id===id).length===1 &&
    clientes.some(c=>c?.id===id&&c.activo_confirmado===true&&c.detalle!==false) &&
    lista(ctx.clientesVisibles).filter(c=>c?.id===id&&c.activo_confirmado===true&&c.detalle!==false).length===1 &&
    ctx.ver?.({tipo:'cliente_detalle',cliente_id:id})?.ok===true;
  const seguro=x=>typeof x==='string'&&/^[a-zA-Z][a-zA-Z0-9_/-]{0,79}$/.test(x)?x:'Sin dato confirmado';
  const dias=new Map();
  for(const r of lista(rows)) {
    if(!r || typeof r!=='object')continue;
    // La API actual guarda cliente_id dentro de datos (JSON). Sólo se lee esa clave.
    let datos={};
    if(typeof r.datos==='string') {try { datos=JSON.parse(r.datos); } catch {continue;} }
    else if(r.datos!=null) {if(typeof r.datos!=='object'||Array.isArray(r.datos))continue;datos=r.datos;}
    if(datos==null||typeof datos!=='object'||Array.isArray(datos))continue;
    const ids=[r.cliente_id,datos?.cliente_id].filter(x=>x!=null);
    if(ids.some(x=>typeof x!=='string'||!x)||new Set(ids).size>1||ids.some(x=>!permitido(x)))continue;
    const stamp=tx(r.creada);
    const dateOnly=/^\d{4}-\d{2}-\d{2}$/.test(stamp);
    const sql=/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(stamp);
    const zoned=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$/.test(stamp);
    const day=stamp.slice(0,10), validDay=fecha(day)===day;
    const instant=Date.parse(dateOnly?stamp+'T00:00:00Z':sql?stamp.replace(' ','T')+'Z':stamp);
    const reloj=/[ T](\d{2}):(\d{2}):(\d{2})/.exec(stamp);
    const horaOK=dateOnly||(reloj&&Number(reloj[1])<24&&Number(reloj[2])<60&&Number(reloj[3])<60);
    const valid=validDay&&horaOK&&(dateOnly||sql||zoned)&&Number.isFinite(instant)&&instant<=ahora &&
      (!sql || new Date(instant).toISOString().slice(0,19)===stamp.replace(' ','T'));
    const dia=valid?new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(instant)):'Fecha sin confirmar';
    if(!dias.has(dia))dias.set(dia,{dia,n:0,filas:[]});
    const grupo=dias.get(dia);grupo.n++;
    // Fechas malformadas/futuras sólo cuentan como filas sin fecha, sin detalle atribuible.
    if(!valid)continue;
    const autores=lista(ctx.datos?.personas).filter(p=>typeof r.quien==='string'&&p?.id===r.quien);
    const quien=autores.length===1&&identidadActiva(autores[0])?tx(autores[0].nombre)||r.quien:'Autor sin confirmar';
    grupo.filas.push({cliente_id:ids[0]||null,cuando:dateOnly?dia:new Intl.DateTimeFormat('es-ES',{timeZone:'Europe/Madrid',day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date(instant))+' · Madrid',quien,que:seguro(r.accion),donde:seguro(r.coleccion)});
  }
  return [...dias.values()].sort((a,b)=>a.dia==='Fecha sin confirmar'?1:b.dia==='Fecha sin confirmar'?-1:b.dia.localeCompare(a.dia));
}
function tablaClientes379(ctx,rows) {
  const cuentas=new Map();
  for(const d of porDia379(ctx,rows))for(const r of d.filas)if(r.cliente_id){
    if(!cuentas.has(r.cliente_id))cuentas.set(r.cliente_id,{n:0,tipos:new Map()});
    const c=cuentas.get(r.cliente_id);c.n++;c.tipos.set(r.que,(c.tipos.get(r.que)||0)+1);
  }
  return h('table',{class:'densa'},h('thead',{},h('tr',{},['Cliente','Acciones leídas','Cómo'].map(t=>h('th',{},t)))),
    h('tbody',{},cuentas.size?[...cuentas].map(([id,c])=>h('tr',{},h('td',{},nombreCliente265(ctx,id)),h('td',{},String(c.n)),
      h('td',{},[...c.tipos].map(([t,n])=>`${t}: ${n}`).join(' · ')))):
      h('tr',{},h('td',{colspan:3},'Sin registros con cliente y fecha confirmados.'))));
}
function tablaPorDia379(ctx,rows,vigente,limpiar) {
  const dias=porDia379(ctx,rows);
  const filas=dias.map(d=>{
    const detalle=h('div',{});
    const desplegable=h('details',{},h('summary',{style:'min-height:44px;display:flex;align-items:center'},'Ver registros'),detalle);
    desplegable.addEventListener('toggle',()=>{
      if(!vigente()){limpiar();return;}
      detalle.replaceChildren();
      if(!desplegable.open)return;
      // No paginación ni callbacks que conserven una proyección anterior.
      detalle.append(h('table',{class:'densa'},h('thead',{},h('tr',{},['Cuándo','Cliente','Quién','Qué','Dónde'].map(t=>h('th',{},t)))),
        h('tbody',{},d.filas.map(r=>h('tr',{},[r.cuando,r.cliente_id?nombreCliente265(ctx,r.cliente_id):'Sin cliente indicado',r.quien,r.que,r.donde].map(x=>h('td',{},x)))))));
    });
    return h('tr',{},h('td',{},d.dia),h('td',{},String(d.n)),h('td',{},d.filas.length?desplegable:'Filas sin fecha confirmada; detalle no atribuible'));
  });
  return h('table',{class:'densa'},h('thead',{},h('tr',{},['Día','Acciones leídas','Detalle'].map(t=>h('th',{},t)))),
    h('tbody',{},filas.length?filas:h('tr',{},h('td',{colspan:3},'Sin registros disponibles en la fuente autorizada.'))));
}

export const REFERENCIAS_265 = Object.freeze({
  indicadores: ['Bajas de clientes','Informes antes del día 5','Horas','Tu cola de revisión','Huecos en accounts','Accounts que cumplen'],
  numeros: ['Altas en plazo','Compromisos vencidos sin aviso','Horas por cuenta nueva'],
  tendencias: ['Clientes +48 h sin respuesta','Alarmas en rojo','% horas imputadas','Tareas en revisión +48 h','Nota media de accounts','Semáforos sin rellenar','Acciones con rastro (acumulado)'],
  rituales: ['Ronda de la mañana','Cierre del día','Lunes · semáforos','Viernes · todo a cero y 3 números','Primer día del mes'],
});

function horasDesde(iso, ahora, utcServidor=false) {
  if (!/^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}/.test(tx(iso))) return null;
  const s = iso.replace(' ','T');
  if (!utcServidor && !/Z$|[+-]\d\d:?\d\d$/.test(s)) return null;
  const d = Date.parse(s + (/Z$|[+-]\d\d:?\d\d$/.test(s) ? '' : 'Z'));
  const n = (ahora - d) / 36e5;
  return Number.isFinite(n) && n >= 0 ? n : null;
}

export function modelo265(ctx, fuentes, ahora = Date.now()) {
  const actuales = lista(ctx.clientesVisibles).filter(c=>c?.activo_confirmado===true && c.detalle!==false);
  const cuentas = new Map();
  for (const c of actuales) if (typeof c?.id === 'string') cuentas.set(c.id, (cuentas.get(c.id) || 0) + 1);
  const cliOK = id => typeof id === 'string' && cuentas.get(id) === 1 &&
    ctx.ver?.({tipo:'cliente_detalle',cliente_id:id})?.ok === true;
  const filasCli = rows => lista(rows).filter(x => cliOK(x?.cliente_id || x?.cli));
  const alertas = lista(fuentes.alertas?.alertas).filter(a => !a.cliente_id || cliOK(a.cliente_id));
  const prioridades = alertas.slice().sort((a,b) => ({rojo:0,alta:0,critico:0,ambar:1,amarillo:1,media:1,baja:2}[a.gravedad] ?? 3) -
    ({rojo:0,alta:0,critico:0,ambar:1,amarillo:1,media:1,baja:2}[b.gravedad] ?? 3) || tx(a.vence).localeCompare(tx(b.vence)));
  const dVivas = lista(fuentes.decisiones?.decisiones);
  const clavesVivas = new Set(dVivas.map(x => x.clave).filter(Boolean));
  const decisiones = [...lista(fuentes.reloj?.decisiones).filter(x => !clavesVivas.has(x.clave) && !dVivas.some(v => v.id === x.id)),...dVivas]
    .filter(x => !x.cliente_id || cliOK(x.cliente_id)).map(x => {
      const reloj = x.tipo === 'para_coti' ? 24 : 48;
      const horas = horasDesde(x.creada, ahora, true); // creado de decisiones: reloj UTC del servidor.
      return {...x,reloj,horas,estado265:x.respondida ? 'Contestada' : horas == null ? 'Reloj sin fecha' : horas > reloj ? 'Fuera de plazo' : 'En plazo'};
    });
  const registro = lista(fuentes.rastro?.registro).filter(x => !x.cliente_id || cliOK(x.cliente_id));
  const porDia = new Map(), porCliente = new Map(), comoCliente = new Map();
  for (const r of registro) {
    const dia = fecha(r.creada); porDia.set(dia,(porDia.get(dia)||0)+1);
    if (cliOK(r.cliente_id)) {
      porCliente.set(r.cliente_id,(porCliente.get(r.cliente_id)||0)+1);
      if(!comoCliente.has(r.cliente_id))comoCliente.set(r.cliente_id,new Map());
      const tipos=comoCliente.get(r.cliente_id),tipo=tx(r.accion)||'Tipo sin dato';
      tipos.set(tipo,(tipos.get(tipo)||0)+1);
    }
  }
  const revMili = filasCli(fuentes.produccion?.cola).filter(x => x.persona_id === 'mili' &&
    x.estado_determinado === true && ['revisión mili','revision mili'].includes(x.estado));
  const informe = fuentes.direccion?.informe_semanal;
  const cierre = fuentes.direccion?.cierre_mes;
  return {prioridades,decisiones,registro,porDia:porDia379(ctx,lista(fuentes.rastro?.registro),ahora),
    porCliente:[...porCliente].map(([cliente_id,n])=>({cliente_id,n,como:[...comoCliente.get(cliente_id)].map(([tipo,n])=>`${tipo}: ${n}`).join(' · ')})),revMili,
    rojos:filasCli(fuentes.verdad?.clientes).filter(x => ['critico','crítico','grave'].includes(x.gravedad)),
    numeros:lista(informe?.numeros).map(x=>({nombre:tx(x.nombre),valor:x.valor,detalle:tx(x.detalle),umbral:tx(x.umbral)})),
    bajas:lista(cierre?.bajas).map(x=>({cliente:tx(x.cliente),fecha:fecha(x.fecha_baja),motivo:tx(x.motivo)})),
    corte:fecha(informe?.corte),semana:tx(informe?.semana),
    informes:cierre?.informes && typeof cierre.informes === 'object' ? cierre.informes : null,
    // Estas fuentes actuales no certifican cumplimiento día5, capacidad12, nota ni porcentaje contractual.
    indicadores:REFERENCIAS_265.indicadores.map((etiqueta,i)=>({etiqueta,valor:i===3 && revMili.length ? revMili.length : null,
      detalle:i===3 ? 'Tareas identificadas en revisión Mili presentes en la copia. Sin filas no se acredita una cola vacía.' :
        ['Histórico de bajas: consultar abajo. No son clientes operativos.', 'Referencia del panel original: día 5; falta evidencia de envío y período.',
         'Referencia original: banda 50–130 %. Falta capacidad/pauta confirmada para calcular cumplimiento.', '',
         'Referencia original: 12 cuentas por account. No es capacidad contractual acreditada.',
         'Referencia original: nota 0–100. No se calcula una evaluación sin criterio confirmado.'][i]})),
    tendencias:REFERENCIAS_265.tendencias.map(etiqueta=>({etiqueta,actual:null,anterior:null,detalle:'Serie comparable fechada pendiente; no se infiere tendencia desde una foto.'})),
  };
}

function tabla(filas,columnas,vacio='Sin registros disponibles en la fuente autorizada.') {
  return tablaDensa({filas,columnas,porPagina:20,vacio:{titulo:vacio,celebrar:false}});
}
const textoCol = (clave,titulo) => ({clave,titulo,celda:r=>h('span',{},dato(r[clave]))});
const enlace = (ctx,href,texto,vigente) => h('a',{class:'bt',href, on:{click:e=>{if(!vigente())e.preventDefault();}}},texto);
function bloque(titulo,contenido,sub='') {return panel({titulo,sub},contenido);}
function pendientesRituales(ctx,vigente) {
  const ref = ['Empujar lo de hoy antes de 15:00 (10:00 Argentina)', 'Una línea: qué queda abierto y por qué',
    'Semáforos del lunes antes de 12:00', 'Confirmar los 3 números antes de 18:00', 'Revisar reuniones y horas del mes anterior'];
  return bloque('Rituales',tabla(REFERENCIAS_265.rituales.map((etiqueta,i)=>({etiqueta,estado:'Sin registro confirmado',
    referencia:`Referencia original por confirmar: ${ref[i]}`})),
    [textoCol('etiqueta','Ritual'),textoCol('estado','Registro'),textoCol('referencia','Pauta')]),'Los cinco rituales siguen visibles. No hay una casilla que simule guardado.');
}

export async function renderDiaDireccion265(cont,ctx,clave='dia') {
  if (!puerta265(ctx,clave)) { cont.replaceChildren(h('p',{},'Esta vista no está disponible para tu sesión.')); return; }
  const original = firma(ctx);
  const firmaControl329=()=>{
    try{return JSON.stringify([ctx.real,ctx.persona,ctx.datos?.personas,ctx.clientes,ctx.veModulo?.('mi-dia'),lista(ctx.clientesVisibles).map(c=>[c?.id,c?.activo_confirmado,c?.detalle,ctx.ver?.({tipo:'cliente_detalle',cliente_id:c?.id})?.ok===true])]);}catch{return null;}
  };
  const firmaNumeros449=()=>JSON.stringify([firmaControl329(),ctx.veModulo?.('decisiones')===true]);
  const numerosInicial449=clave==='dia'?firmaNumeros449():null;
  const informeInicial498=clave==='tomas'?firmaNumeros449():null;
  const vigenteNumeros449=()=>vigente()&&numerosInicial449!==null&&firmaNumeros449()===numerosInicial449;
  const controlInicial329=clave==='tomas'?firmaControl329():null;
  const vigenteTendencia439=()=>vigente()&&controlInicial329!==null&&controlInicial329===firmaControl329();
  const control379=clave==='rastro'?firmaRastro379(ctx):null;
  if(clave==='rastro'&&(!control379||!puertaRastro379(ctx))){cont.replaceChildren(h('p',{},'Esta vista no está disponible para tu sesión.'));return;}
  const vigente = () => cont.isConnected && firma(ctx) === original && puerta265(ctx,clave) &&
    (clave!=='rastro'||(puertaRastro379(ctx)&&firmaRastro379(ctx)===control379));
  const base = h('div',{class:'pila','data-operaciones-265':clave});cont.append(base);
  base.append(h('p',{class:'sub'},'Leyendo las fuentes autorizadas…'));
  const spec = [
    ['alertas','alertas',`alertas/p_${ctx.persona.id}`],['produccion','produccion','produccion/produccion'],
    ['direccion','decisiones','decisiones/direccion'],['reloj','decisiones','decisiones/reloj'],['verdad','en-rojo','verdad/clientes'],
    ['decisiones','decisiones',null],['rastro','decisiones',null],
  ];
  if(clave==='tomas')spec.push(['control','mi-dia',null]);
  if(clave==='dia')spec.push(['bandeja','bandeja','bandeja/por_cliente'],['bandeja_detalle','bandeja','bandeja/bandeja'],['horas','horas','horas/horas'],['nuevos','clientes-nuevos','nuevos/nuevos'],['informes','informes-mensuales','informes/informes']);
  const resultados = await Promise.allSettled(spec.map(async ([nombre,mod,ruta])=>{
    if ((clave==='rastro'&&!vigente()) || !ctx.veModulo?.(mod)) return {nombre,denegada:true};
    if (ruta) return {nombre,doc:await ctx.datosModulo(ruta)};
    if (!ctx.servidor) return {nombre,denegada:true};
    return {nombre,doc:await ctx.api(nombre==='control'?'operaciones/control':nombre)};
  }));
  if (!vigente()) { base.replaceChildren(); return; }
  const fuentes={}, errores=[];
  resultados.forEach((r,i)=>{if(r.status==='fulfilled' && r.value.doc) fuentes[r.value.nombre]=r.value.doc;
    else if(r.status==='rejected') errores.push(spec[i][0]);});
  const m = modelo265(ctx,fuentes);
  const filasPrioridades = m.prioridades.map(a=>({titulo:tx(a.titulo)||tx(a.tipo),cliente:a.cliente_id ? nombreCliente265(ctx,a.cliente_id) : 'Equipo',
    fecha:fecha(a.desde),seguimiento:horasDesde(a.desde,Date.now()) >= 48 ? 'Abierta ≥2 días en la copia; falta rastro de seguimiento' : 'Seguimiento no confirmado',
    abrir: /^#\/[\w\-/]+$/.test(tx(a.ir)) ? a.ir : '#/alertas'}));
  const indicadorTabla = () => tabla(m.indicadores,[textoCol('etiqueta','Indicador'),{clave:'valor',titulo:'Medición',celda:r=>r.valor==null?h('span',{title:'Sin dato confirmado','aria-label':'Sin dato confirmado'},'—'):h('span',{},String(r.valor))},{clave:'detalle',titulo:'Fuente',celda:r=>h('details',{'data-indicador-fuente':'427',on:{toggle:()=>{if(!vigente())base.replaceChildren();}}},h('summary',{title:'Fuente y referencia del indicador',style:{minHeight:'44px',boxSizing:'border-box',paddingTop:'10px',cursor:'pointer'}},'Detalle'),h('p',{class:'sub'},dato(r.detalle)))}]);
  const relojTabla = () => tabla(m.decisiones,[textoCol('titulo','Problema'),textoCol('recomendacion','Recomendación'),
    {clave:'reloj',titulo:'Reloj',celda:r=>chipEstado(r.estado265==='Fuera de plazo'?'rojo':r.horas==null?'gris':'azul',`${r.reloj} h · ${r.estado265}`)},
    {clave:'abrir',titulo:'',celda:r=>enlace(ctx,`#/decisiones/reloj/${encodeURIComponent(r.id)}`,'Abrir decisión',vigente)}]);
  const nombresFuente = ['Altas en plazo (encendidas el día 10, límite 12)','Compromisos vencidos sin aviso','Horas por cuenta nueva (media al mes)'];
  const semanales = REFERENCIAS_265.numeros.map((etiqueta,i)=>{
    const xs = m.numeros.filter(x=>x.nombre===nombresFuente[i]);
    const n = xs.length===1 ? xs[0] : null;
    return {etiqueta,valor:n?.valor ?? null,
      detalle:n ? `${n.nombre} · ${n.detalle} · fuente histórica ${m.corte}` : 'Falta ventana y evidencia suficiente.',
      referencia:['Día 12, referencia original por confirmar','Sin movimiento/comentario 48 h; no medir con stock parcial','45 h/mes, referencia original por confirmar'][i]};
  });
  const planes327=clave==='tomas'?await leerPlanes327(ctx,m.rojos,vigente):[];
  if(!vigente()||planes327===null){base.replaceChildren();return;}
  if(clave==='tomas'){
    const control=fuentes.control;
    const autorizado=controlInicial329!==null&&controlInicial329===firmaControl329()&&control?.version==='272.1'&&control.propietario===ctx.persona.id&&Array.isArray(control.registros);
    if(!autorizado)fuentes.control=null;
    m.tendencias=tendenciasFotos329(autorizado?control:null,{scopeHash:autorizado?control.scope_foto_actual:null,actorId:ctx.persona.id,ahora:new Date().toISOString()});
  }
  const rastroDestino392=h('div',{'data-rastro-392':'montaje'});
  const decisionesDestino=h('div',{'data-decisiones-387':'montaje'});
  const prioridadesDestino=h('div',{'data-prioridades-300':'montaje'});
  const resumenDestino=h('div',{'data-resumen-274':'montaje'}),ritualesDestino=h('div',{'data-rituales-269':'montaje'}),encargosDestino=h('div',{'data-encargos-272':'montaje'}),fotosDestino=h('div',{'data-fotos-272':'montaje'});
  base.replaceChildren();
  if (errores.length) base.append(h('p',{class:'sub',role:'status'},`Fuentes no disponibles: ${errores.join(', ')}. Las demás lecturas se conservan.`));
  if (clave==='dia') {
    base.append(resumenDestino,prioridadesDestino,
      bloque('Tus indicadores',indicadorTabla()),
      bloque('Los 3 números de esta semana',pintarNumerosSemanales449(h,semanales,{vigente:vigenteNumeros449,semana:m.semana})),
      ritualesDestino,encargosDestino);
  } else if(clave==='tomas') {
    const informe498=h('div',{'data-informe-semanal-498':''});
    const vigenteInforme498=()=>informe498.isConnected&&vigente()&&ctx.veModulo?.('decisiones')===true&&informeInicial498!==null&&firmaNumeros449()===informeInicial498;
    if(vigente()&&ctx.veModulo?.('decisiones')===true&&firmaNumeros449()===informeInicial498)informe498.append(tabla(semanales,[
      {clave:'etiqueta',titulo:'Indicador',celda:r=>{
        const cuerpo=h('div',{}),d=h('details',{on:{toggle:()=>{if(!vigenteInforme498()){informe498.replaceChildren();return;}cuerpo.replaceChildren();if(d.open)cuerpo.append(h('p',{class:'sub'},`Criterio original: ${r.referencia}`),h('p',{class:'sub'},`Fuente y explicación: ${r.detalle}`));}}},
          h('summary',{'aria-label':`Fuente y criterio de ${r.etiqueta}`,title:'Abrir fuente histórica y criterio; no es una medición actual',style:{minHeight:'44px',display:'flex',alignItems:'center',cursor:'pointer'}},r.etiqueta),cuerpo);return d;}},
      {clave:'valor',titulo:'Valor',celda:r=>{const v=typeof r.valor==='number'&&Number.isFinite(r.valor)?String(r.valor):typeof r.valor==='string'&&r.valor.trim()?r.valor:'—';return h('span',{title:v==='—'?'Sin dato confirmado; no equivale a cero.':`${v} · referencia histórica leída, no acredita cumplimiento actual.`,'aria-label':`${r.etiqueta}: ${v==='—'?'sin dato confirmado':v+'; referencia histórica'}`},v);}}
    ]));
    base.append(decisionesDestino,h('details',{},h('summary',{},'Referencias de decisiones de la copia anterior'),relojTabla()),
      bloque('¿Mejora o empeora?',tabla(m.tendencias,[textoCol('etiqueta','Indicador'),...['actual','anterior'].map(clave=>({clave,titulo:clave==='actual'?'Última':'Antes',celda:r=>h('span',{title:r[clave]==null?'Sin medición comparable confirmada':null,'aria-label':r[clave]==null?'Sin medición comparable confirmada':null},r[clave]==null?'—':String(r[clave]))})),
        {clave:'comparacion',titulo:'Cambio / fuente',celda:r=>h('div',{},pintarMiniserie439(h,r,vigenteTendencia439),r.estado==='comparacion_observada'?`${r.delta>0?'+':''}${r.delta} · ${r.direccion} · copia${r.parcial?' parcial':''}`:h('span',{title:'Sin comparación acreditada','aria-label':'Sin comparación acreditada'},'—'),
          h('details',{on:{toggle:()=>{if(!vigenteTendencia439())base.replaceChildren();}}},h('summary',{},'Fuentes y cortes'),h('p',{class:'sub'},r.motivo),
            r.cortes?h('p',{class:'sub'},`${r.cortes.anterior} → ${r.cortes.actual}`):null,
            ...(r.referencias||[]).map(x=>h('p',{class:'sub'},`Referencia de copia: ${x.valor} · fuente ${x.fecha_fuente} · foto guardada ${x.guardada_en}. No acredita por sí sola una variación.`))))}]),'— sin medición o comparación acreditada. Abre Fuentes y cortes para consultar las lecturas disponibles.'),
      bloque('Rojos sin plan o sin visto de Coti',(()=>{
        const caja500=h('div',{'data-planes-pendientes-500':''});
        const actual500=cid=>{const cs=lista(ctx.clientesVisibles).filter(c=>c?.id===cid),core=lista(ctx.clientes).filter(c=>c?.id===cid);return vigenteTendencia439()&&ctx.veModulo?.('en-rojo')===true&&cs.length===1&&cs[0].activo_confirmado===true&&cs[0].detalle===true&&core.length===1&&core[0].activo_confirmado!==false&&core[0].activo!==false&&core[0].estado!=='baja'&&ctx.ver?.({tipo:'cliente_detalle',cliente_id:cid})?.ok===true;};
        const vigente500=cid=>{const ok=caja500.isConnected&&actual500(cid);if(!ok)caja500.replaceChildren();return ok;};
        const filas500=m.rojos.filter(x=>planes327.some(p=>p.cliente_id===x.cliente_id&&p.estado!=='visto')&&actual500(x.cliente_id)).map(x=>({cliente_id:x.cliente_id,estadoPlan:planes327.find(p=>p.cliente_id===x.cliente_id)?.estado||'desconocido',cliente:nombreCliente265(ctx,x.cliente_id),
          motivos500:[tx(x.motivo),...lista(x.motivos).filter(y=>typeof y==='string')].filter(Boolean),plan:planes327.find(p=>p.cliente_id===x.cliente_id)?.texto||'Plan / visto no comprobados'}));
        caja500.append(tabla(filas500,[{clave:'cliente',titulo:'Cliente',celda:r=>h('span',{style:{whiteSpace:'nowrap'}},r.cliente)},
          {clave:'motivo',titulo:'Motivo registrado',celda:r=>{
            const contenido=h('div',{}),d=h('details',{'data-motivos-plan500':'',on:{toggle:()=>{if(!vigente500(r.cliente_id))return;contenido.replaceChildren();if(!d.open)return;contenido.append(...r.motivos500.map(t=>h('p',{class:'sub'},t)),h('p',{class:'sub'},`Fuente de motivos: verdad operativa · ${fecha(fuentes.verdad?.generado)}. Motivos registrados en la copia; no acreditan ejecución del plan.`));}}},
              h('summary',{'aria-label':`Motivos completos de ${r.cliente}`,title:r.motivos500.join(' · ')||'Sin motivo registrado',style:{minHeight:'44px',display:'flex',alignItems:'center',cursor:'pointer',minWidth:'0',maxWidth:'min(480px,48vw)'}},
                h('span',{style:{display:'block',minWidth:'0',maxWidth:'100%',overflow:'hidden',whiteSpace:'nowrap',textOverflow:'ellipsis'}},r.motivos500[0]||'—')),contenido);return d;}},
          {clave:'plan',titulo:'Plan',celda:r=>chipEstado(r.estadoPlan==='desconocido'?'gris':'ambar',r.plan)},
          {clave:'abrir',titulo:'',celda:r=>enlace(ctx,`#/en-rojo/${r.cliente_id}`,'Abrir plan',()=>vigente500(r.cliente_id))}]),
          enlace(ctx,'#/en-rojo','Abrir planes actuales',()=>{const ok=caja500.isConnected&&vigenteTendencia439()&&ctx.veModulo?.('en-rojo')===true;if(!ok)caja500.replaceChildren();return ok;}));return caja500;
      })(),`${planes327.filter(p=>p.estado!=='visto').length} pendientes de comprobar o revisar de ${planes327.length} clientes leídos. ${planes327.filter(p=>p.estado==='visto').length} con plan vigente visto por Coti. Lectura local: no acredita ejecución. Los fallos de lectura no se convierten en falta de plan.`),
      bloque('Informe de la semana para Tomás',h('div',{},informe498,ctx.veModulo('decisiones')?panelInformeSemanalOperaciones({h,ctx,modelo:m,fuentes,vigente}):null),`Fuente histórica de Dirección · ${m.corte} · no son métricas actuales`),
      fotosDestino,
      bloque('Bajas con su motivo',tabla(m.bajas,[textoCol('cliente','Cliente histórico'),textoCol('fecha','Fecha'),textoCol('motivo','Motivo')]),'Consulta histórica explícita; no se añade a prioridades ni carteras activas.'));
  } else {
    base.append(rastroDestino392,bloque('Acciones registradas',h('p',{},'Registros técnicos leídos; no acreditan acciones cumplidas, estado ni nota operativa.'),'Últimas filas de la respuesta autorizada; no el total histórico completo.'),
      bloque('Por día',tablaPorDia379(ctx,fuentes.rastro?.registro,vigente,()=>base.replaceChildren())),
      bloque('Por cliente',tablaClientes379(ctx,fuentes.rastro?.registro),'Registros con fecha y cliente activos autorizados. Tipos leídos, no ejecución confirmada; no se deduce cliente del texto.'));
  }
  if(clave==='rastro')await renderRastroDeclarativo392(rastroDestino392,ctx,{vigente});
  if(!vigente())return;
  if(clave==='dia')await renderPrioridades300(prioridadesDestino,ctx,m.prioridades,id=>nombreCliente265(ctx,id),vigente);
  if(!vigente())return;
  if(clave==='dia')await renderResumen274(resumenDestino,ctx,{fuentes});
  if(!vigente())return;
  if(clave==='dia'||clave==='rastro')await panelRituales269(clave==='dia'?ritualesDestino:base,ctx);
  if(clave==='rastro'&&!vigente()){base.replaceChildren();return;}
  if(vigente()&&clave==='dia')await panelEncargos272(encargosDestino,ctx);
  if(vigente()&&clave==='tomas')await renderDecisiones387(decisionesDestino,ctx,{vigente});
  if(vigente()&&clave==='tomas')await panelFotosControl272(fotosDestino,ctx,fuentes.control||null);
  return {clave,fuentes:Object.keys(fuentes),errores};
}
