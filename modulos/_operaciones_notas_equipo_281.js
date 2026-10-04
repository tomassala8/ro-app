import {cargarNotasHoras383,notasHorasVigentes383,serieNota383,semanaNota383,graficoNota383} from './_notas_horas_383.js';
import { h } from '../componentes.js';
import { serieHorasDiaria238 } from './_horas_diarias_238.js';
const identidad=c=>JSON.stringify([c.real?.id,c.persona?.id]);
const activa=p=>p?.estado==='activo'&&p?.activo!==false;
const fechas=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(+new Date(x+'T00:00Z'))&&new Date(x+'T00:00Z').toISOString().slice(0,10)===x;
const ACCIONES=['mantener','formar','reorientar','salida'];

export function observacionesSemana281(p,hoy,anterior=false){
  const s=serieHorasDiaria238(p,hoy);if(!s)return null;
  const d=new Date(hoy+'T00:00Z');d.setUTCDate(d.getUTCDate()-((d.getUTCDay()+6)%7)-(anterior?7:0));const desde=d.toISOString().slice(0,10);
  d.setUTCDate(d.getUTCDate()+6);const hasta=anterior?d.toISOString().slice(0,10):hoy;
  const ds=s.dias.filter(x=>x.fecha>=desde&&x.fecha<=hasta&&x.estado==='observado');
  return ds.length?{valor:ds.reduce((total,x)=>total+x.horas,0),desde,hasta,fecha_fuente:s.fecha_fuente,estado:'observado',cobertura:'parcial',dias_observados:ds.length}:null;
}

// Sólo observaciones autorizadas dentro de la semana solicitada: no extrapola días.
export function horasNotas281(ctx,pid,m,hoy,anterior=false){
  if(ctx.ver?.({tipo:'horas_persona',persona_id:pid})?.ok!==true||!fechas(hoy))return null;
  const lunes=new Date(hoy+'T00:00Z');lunes.setUTCDate(lunes.getUTCDate()-((lunes.getUTCDay()+6)%7)-(anterior?7:0));
  const desde=lunes.toISOString().slice(0,10);lunes.setUTCDate(lunes.getUTCDate()+6);const hasta=anterior?lunes.toISOString().slice(0,10):hoy;
  if(!m||m.estado!=='observado'||m.cobertura!=='parcial'||typeof m.valor!=='number'||!Number.isFinite(m.valor)||m.valor<0||m.desde!==desde||m.hasta!==hasta||!fechas(m.fecha_fuente?.slice(0,10))||m.fecha_fuente.slice(0,10)>hoy)return null;
  return {valor:m.valor,desde,hasta,fecha_fuente:m.fecha_fuente};
}

export function filaNotaEquipo281(ctx,fila,{hoy}={}){
  const pid=fila.persona_id,id=identidad(ctx),row=h('tr',{}),info=h('td',{}),nota=h('select',{'aria-label':'Nota humana 1–10',style:{minHeight:'44px'}},h('option',{value:''},'—'),Array.from({length:10},(_,i)=>h('option',{value:String(10-i)},String(10-i))));
  const prueba=h('input',{type:'text',maxlength:'300','aria-label':'Hecho que prueba la nota',placeholder:'Hecho concreto (obligatorio)',style:{minHeight:'44px',maxWidth:'100%'}});
  const accion=h('select',{'aria-label':'Acción propuesta, no ejecutada',style:{minHeight:'44px'}},h('option',{value:''},'—'),ACCIONES.map(a=>h('option',{value:a},a)));
  const cargar=h('button',{type:'button',style:{minHeight:'44px'}},'Ver nota'),guardar=h('button',{type:'button',style:{minHeight:'44px'}},'Guardar declaración'),status=h('small',{role:'status'});
  let current=null,busy=false,pending=null;nota.disabled=prueba.disabled=accion.disabled=guardar.disabled=true;
  function vive(escribir=false){
    const ps=ctx.datos?.personas||[];
    return row.isConnected&&identidad(ctx)===id&&(!ctx.vigente||ctx.vigente())&&ctx.veModulo?.('mi-dia')&&
      [ctx.real?.id,ctx.persona?.id,pid].every(p=>{const xs=ps.filter(x=>x?.id===p);return xs.length===1&&activa(xs[0]);})&&
      ctx.ver?.({tipo:'notas_persona',persona_id:pid})?.ok===true&&(!escribir||!ctx.soloLectura&&ctx.real?.id===ctx.persona?.id&&current?.puede_registrar===true);
  }
  function limpiar(){nota.value=prueba.value=accion.value='';current=null;for(const b of [nota,prueba,accion,guardar,cargar])b.disabled=true;row.replaceChildren(h('td',{colspan:'7'},'Notas fuera del ámbito actual.'));}
  function bloqueado(v){for(const b of [nota,prueba,accion,guardar,cargar])b.disabled=v||!vive(b!==cargar);if(pending){nota.disabled=prueba.disabled=accion.disabled=true;cargar.disabled=true;}}
  function pintar(){actualizarHoras();const r=current.registro;nota.value=r?.nota==null?'':String(r.nota);prueba.value=r?.prueba||'';accion.value=r?.accion_propuesta||'';
    info.replaceChildren(h('small',{},r?`${r.autor} · ${r.registrado_en}`:'Sin declaración local'),r?h('small',{},`Última declaración: ${r.periodo}`):null,h('small',{},`Período ${current.periodo_actual} para el nuevo guardado · propuesta humana`),cargar,guardar,status);bloqueado(false);}
  cargar.addEventListener('click',async()=>{
    if(busy||pending||!cargar.isConnected)return;if(!vive()){limpiar();return;}busy=true;bloqueado(true);
    try{const d=await ctx.api(`operaciones/notas-equipo?persona_id=${encodeURIComponent(pid)}`);if(!vive()){limpiar();return;}
      if(d?.version!=='281.1'||d.persona_id!==pid||!Number.isInteger(d.revision)||d.revision<0||!/^\d{4}-(0[1-9]|1[0-2])$/.test(d.periodo_actual))throw Error('formato');
      current=d;pintar();status.textContent='Declaración local; sin envío ni decisión laboral.';
    }catch{if(vive())status.textContent='No se pudo leer. Reintenta Ver nota.';else limpiar();}finally{busy=false;if(vive())bloqueado(false);}
  });
  guardar.addEventListener('click',async()=>{
    if(busy||!guardar.isConnected)return;if(!vive()){limpiar();return;}if(!vive(true))return;
    if(!pending){
      if(!prueba.value.trim()){status.textContent='Escribe un hecho concreto antes de guardar.';return;}
      const uuid=globalThis.crypto?.randomUUID?.();if(!uuid){status.textContent='No hay identificador seguro.';return;}
      pending={persona_id:pid,periodo:current.periodo_actual,nota:nota.value===''?null:Number(nota.value),prueba:prueba.value,accion_propuesta:accion.value||null,revision:current.revision,intencion_id:uuid};
    }
    busy=true;bloqueado(true);status.textContent='Guardando declaración…';
    try{const d=await ctx.api('operaciones/notas-equipo',{metodo:'POST',cuerpo:pending});if(!guardar.isConnected||!vive(true)){if(!vive())limpiar();return;}
      const r=d?.recibo;if(d.version!=='281.1'||d.intencion_id!==pending.intencion_id||r?.persona_id!==pid||r.revision!==pending.revision+1||r.autor!==ctx.real.id||r.periodo!==pending.periodo||r.nota!==pending.nota||r.accion_propuesta!==pending.accion_propuesta||r.puntuacion_automatica!==false||r.decision_laboral!==false||r.envio_realizado!==false)throw Error('recibo');
      current={...current,revision:r.revision,registro:r};pending=null;pintar();status.textContent='Declaración guardada en RO; propuesta no ejecutada.';
    }catch{if(!vive())limpiar();else if(guardar.isConnected&&vive(true))status.textContent='Sin confirmación: reintenta Guardar con la misma intención.';}
    finally{busy=false;if(guardar.isConnected&&vive())bloqueado(false);}
  });
  const horas=(m,ant)=>{const d=horasNotas281(ctx,pid,m,hoy,ant);return h('td',{},d?`${d.valor>0?'≥':''}${d.valor.toLocaleString('es-ES')} h`:'—',h('small',{title:d?`Copia ${d.fecha_fuente}; suma de observaciones de la semana, cobertura parcial`:'Sin observaciones autorizadas compatibles; no equivale a cero.'},d?`${d.desde} → ${d.hasta} · parcial`:'Sin datos'));};
  const previa=horas(fila.horas_semana_pasada,true),actual=horas(fila.horas_esta_semana,false);
  function actualizarHoras(){if(fila.guardia383&&!fila.guardia383()){grafico.replaceChildren();previa.replaceChildren('—');actual.replaceChildren('—');return;}if(ctx.ver?.({tipo:'horas_persona',persona_id:pid})?.ok!==true)grafico.replaceChildren();previa.replaceChildren(...horas(fila.horas_semana_pasada,true).childNodes);actual.replaceChildren(...horas(fila.horas_esta_semana,false).childNodes);}
  const grafico=h('span',{}),persona=h('td',{},fila.nombre||pid,grafico);
  grafico.addEventListener('mouseenter',()=>{if(!vive()||(fila.guardia383&&!fila.guardia383())||ctx.ver?.({tipo:'horas_persona',persona_id:pid})?.ok!==true){grafico.replaceChildren();previa.replaceChildren('—');actual.replaceChildren('—');}});
  row.actualizarHistoria383=serie=>{
    if(!vive()||ctx.ver?.({tipo:'horas_persona',persona_id:pid})?.ok!==true){grafico.replaceChildren();previa.replaceChildren('—');actual.replaceChildren('—');return;}
    const s=serieNota383(serie,hoy);if(!s)return;
    fila.horas_semana_pasada=semanaNota383(serie,hoy,true);fila.horas_esta_semana=semanaNota383(serie,hoy,false);
    actualizarHoras();grafico.replaceChildren(graficoNota383(h,s));
  };
  info.append(cargar,status);row.append(persona,previa,actual,h('td',{},nota),h('td',{},prueba),h('td',{},accion),info);return row;
}

export function panelEquipoNotas281(cont,ctx,filas,{hoy}={}){
  const counts=new Map();for(const p of Array.isArray(filas)?filas:[])counts.set(p?.persona_id,(counts.get(p?.persona_id)||0)+1);
  const rows=(Array.isArray(filas)?filas:[]).filter(p=>{const xs=(ctx.datos?.personas||[]).filter(x=>x?.id===p?.persona_id);return typeof p?.persona_id==='string'&&counts.get(p.persona_id)===1&&xs.length===1&&activa(xs[0])&&ctx.ver?.({tipo:'notas_persona',persona_id:p.persona_id})?.ok===true;});
  const cols=['Persona','Horas sem. pasada','Esta semana','Nota','Hecho que lo prueba','Acción',''];
  const nodos=rows.map(p=>filaNotaEquipo281(ctx,p,{hoy})),cuerpo=h('tbody',{},nodos);
  const seccion=h('section',{class:'op-notas281 oe-panel'},h('header',{},h('h2',{},'Equipo · notas humanas')),h('div',{style:{overflowX:'auto'}},h('table',{style:{width:'100%',minWidth:'1050px'}},h('thead',{},h('tr',{},cols.map(x=>h('th',{scope:'col'},x)))),cuerpo)),h('details',{},h('summary',{},'Escala y fuentes de seguimiento'),h('p',{},'Escala original: 9–10 resuelve solo y mejora; 7–8 poca supervisión; 5–6 seguimiento; 3–4 corrección; 1–2 no resuelve su rol. Referencia humana, no KPI ni decisión laboral.'),h('p',{},'Cada declaración tiene período, prueba, autor y fecha propios. Horas sólo con observaciones autorizadas de la semana correspondiente; porcentajes y capacidad no inferidos.')));
  cont.append(seccion);
  // Una lectura existente por panel, nunca por fila. No usar historiales tras perder alcance.
  const vigente=()=>seccion.isConnected!==false&&(!ctx.vigente||ctx.vigente())&&ctx.veModulo?.('mi-dia');
  const listo=(async()=>{
    const copia=await cargarNotasHoras383(ctx,rows);
    if(!vigente()||copia?.denegado){cuerpo.replaceChildren();return;}
    if(!copia)return;
    if(!notasHorasVigentes383(ctx,rows,copia)){cuerpo.replaceChildren();return;}
    rows.forEach((p,i)=>{p.guardia383=()=>vigente()&&notasHorasVigentes383(ctx,rows,copia);nodos[i].actualizarHistoria383(copia.modelo.series.get(p.persona_id));});
    seccion.append(h('small',{},'Gráfico: últimas 14 fechas del historial, copia parcial. Azul = horas observadas; puntos = sin datos; no es cumplimiento ni capacidad.'));
  })().catch(()=>{if(!vigente())cuerpo.replaceChildren();});
  return {listo};
}
