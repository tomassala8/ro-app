import { h } from '../componentes.js';

export function fechaHechoLocal(valor) {
  if (typeof valor !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(valor)) throw new Error('Indica una fecha y hora válidas.');
  const d = new Date(valor), pad = n => String(n).padStart(2, '0');
  const vuelta = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  if (!Number.isFinite(+d) || vuelta !== valor || +d > Date.now()) throw new Error('Registra únicamente hechos ya realizados, con fecha y hora válidas.');
  return d.toISOString();
}

export function permisoLecturaHechos(ctx, cid) {
  const roles = p => (p?.puestos || []).some(r => ['account','operaciones','direccion'].includes(r));
  return !!ctx.servidor && !ctx.pilotoLectura && roles(ctx.real) && roles(ctx.persona) && ctx.clientes?.some(c => c.id === cid) && ctx.ver({tipo:'cliente_detalle',cliente_id:cid}).ok === true;
}

export function permisoRegistro(ctx, cid) {
  const roles = p => (p?.puestos || []).some(r => ['account','operaciones','direccion'].includes(r));
  return !!ctx.servidor && !ctx.soloLectura && ctx.real?.id === ctx.persona?.id && roles(ctx.real) && roles(ctx.persona) &&
    ctx.clientes?.some(c => c.id === cid) && ctx.ver({tipo:'cliente_detalle',cliente_id:cid}).ok === true &&
    ctx.ver({tipo:'responder_cliente',cliente_id:cid}).ok === true;
}

// Un hecho declarado por el equipo conserva su origen; no certifica un KPI.
export function crearRegistroHechos(ctx, cid) {
  const estado = h('p',{class:'sub',role:'status'},'Consultando los hechos registrados…');
  const filas = h('div',{class:'pila',style:{gap:'8px'}});
  const formZona = h('div');
  const nodo = h('section',{class:'panel','aria-label':'Hechos registrados'},
    h('div',{class:'cuerpo pila'},h('h2',{},'Hechos registrados'),
      h('p',{class:'sub'},'Hechos declarados por el equipo. No tienen comprobación externa y no certifican por sí solos el cumplimiento de los KPIs.'),estado,filas,formZona));
  let secuencia=0, enviando=false, intento=null;
  const firmaIdentidad=JSON.stringify([ctx.real?.id || '',ctx.persona?.id || '']);
  const vivo=()=>nodo.isConnected && (!ctx.vigente || ctx.vigente()) && firmaIdentidad===JSON.stringify([ctx.real?.id || '',ctx.persona?.id || '']) && ctx.clientes?.some(c=>c.id===cid);
  const lectura=()=>{
    if(!vivo()) return false;
    if(permisoLecturaHechos(ctx,cid)) return true;
    filas.replaceChildren();formZona.replaceChildren();
    estado.textContent='El permiso de lectura ha cambiado. Vuelve a la ficha antes de consultar o registrar hechos.';
    return false;
  };
  const url=`clientes/evidencias_kpi?cliente_id=${encodeURIComponent(cid)}`;
  const etiqueta={informe_enviado:'Envío de informe declarado',contacto:'Contacto realizado',reunion:'Reunión celebrada',email:'Correo',telefono:'Teléfono',whatsapp:'WhatsApp',video:'Videollamada',presencial:'Presencial',otro:'Otro',seguimiento:'Seguimiento',soporte:'Soporte',revision:'Revisión'};
  const opciones=(items)=>items.map(v=>h('option',{value:v},etiqueta[v]));
  const actualizar=async()=>{
    const turno=++secuencia;
    if (!lectura()) return;
    estado.textContent='Consultando los hechos registrados…';
    try {
      const d=await ctx.api(url);
      if (!lectura() || turno!==secuencia) return;
      if(d.cliente_id!==cid || !Array.isArray(d.registros)) throw new Error('Respuesta de otro cliente o incompleta.');
      estado.textContent=d.registros.length ? `${d.registros.length} registros disponibles · archivo parcial` : 'Todavía no hay declaraciones en este archivo. Esto no significa que no haya habido actividad.';
      filas.replaceChildren(...d.registros.map(r=>h('div',{style:{borderTop:'1px solid var(--line)',padding:'8px 0'}},
        h('strong',{},`${etiqueta[r.tipo] || 'Hecho'} · ${r.fecha_madrid || 'Fecha por contrastar'}`),
        h('p',{class:'sub'},`${etiqueta[r.canal] || 'Canal por contrastar'} · ${etiqueta[r.motivo] || 'Motivo por contrastar'} · registrado por ${ctx.nombre?.(r.registrado_por) || r.registrado_por} · ${r.estado==='revocado'?'Revocado':'Declarado, sin comprobación externa'}`),
        r.tipo==='informe_enviado' ? h('p',{class:'sub'},`Mes del informe: ${r.periodo_informe || 'Por contrastar'}`) : null,
        r.tipo==='informe_enviado' && r.enlace ? h('a',{class:'bt mini',href:r.enlace,target:'_blank',rel:'noopener noreferrer'},'Ver referencia') : null,
        r.estado!=='revocado' && r.registrado_por===ctx.real.id && permisoRegistro(ctx,cid) ? h('button',{type:'button',class:'bt mini',on:{click:async e=>{
          if(!lectura() || !permisoRegistro(ctx,cid) || enviando) return;
          const boton=e.currentTarget;
          if(!boton?.isConnected) return;
          enviando=true;boton.disabled=true;
          try{await ctx.api('clientes/evidencias_kpi',{metodo:'POST',cuerpo:{accion:'revocar',cliente_id:cid,registro_id:r.id,clave:crypto.randomUUID(),motivo:'correccion'}});if(lectura()) await actualizar();}
          catch(_){if(vivo()) estado.textContent='No se ha podido confirmar la revocación. Recarga el archivo antes de reintentar.';}
          finally{enviando=false;if(lectura() && boton.isConnected) boton.disabled=!permisoRegistro(ctx,cid);}
        }}},'Revocar este registro') : null)));
    } catch(_){if(lectura() && turno===secuencia){estado.textContent='No se puede consultar el registro en esta vista. No se puede concluir ausencia de actividad.';filas.replaceChildren();}}
  };
  if(permisoRegistro(ctx,cid)){
    const tipo=h('select',{'aria-label':'Hecho realizado',on:{change:alCambiarTipo}},opciones(['contacto','reunion','informe_enviado']));
    const canal=h('select',{'aria-label':'Canal del hecho'},opciones(['telefono','email','whatsapp','video','presencial','otro']));
    const motivo=h('select',{'aria-label':'Motivo del hecho'},opciones(['seguimiento','soporte','revision','otro']));
    const ahora=new Date(),pad=n=>String(n).padStart(2,'0');
    const fecha=h('input',{type:'datetime-local',required:true,'aria-label':'Fecha y hora del hecho',value:`${ahora.getFullYear()}-${pad(ahora.getMonth()+1)}-${pad(ahora.getDate())}T${pad(ahora.getHours())}:${pad(ahora.getMinutes())}`});
    const periodo=h('input',{type:'month','aria-label':'Mes del informe',disabled:true});
    const referencia=h('input',{type:'url','aria-label':'Referencia del envío',disabled:true,placeholder:'Enlace al ticket o tarea'});
    const informeZona=h('div',{class:'pila',hidden:true},
      h('div',{class:'fila',style:{flexWrap:'wrap'}},h('label',{class:'campo'},'Mes del informe',periodo),h('label',{class:'campo'},'Referencia del envío',referencia)),
      h('p',{class:'sub'},'Declara un envío ya realizado. La referencia no se consulta automáticamente; no acredita recepción ni cumplimiento.'));
    function alCambiarTipo(){
      const informe=tipo.value==='informe_enviado';informeZona.hidden=!informe;
      for(const campo of [periodo,referencia]){campo.disabled=!informe;campo.required=informe;}
      if(informe){canal.value='email';motivo.value='revision';}
    }
    const guardar=h('button',{type:'submit',class:'bt pri'},'Registrar hecho');
    const form=h('form',{class:'pila',on:{submit:async e=>{
      e.preventDefault();
      if(!lectura() || !permisoRegistro(ctx,cid) || enviando) return;
      try{
        const payload={cliente_id:cid,tipo:tipo.value,canal:canal.value,motivo:motivo.value,fecha:fechaHechoLocal(fecha.value)};
        if(payload.tipo==='informe_enviado'){
          if(!/^[1-9]\d{3}-(?:0[1-9]|1[0-2])$/.test(periodo.value)) throw new Error('Indica el mes del informe.');
          if(!referencia.value.trim()) throw new Error('Añade la referencia del envío.');
          if(!['email','whatsapp','otro'].includes(payload.canal)) throw new Error('Selecciona un canal de envío del informe.');
          payload.periodo_informe=periodo.value;payload.enlace=referencia.value.trim();
        }
        if(payload.tipo==='reunion' && ['email','whatsapp'].includes(payload.canal)) throw new Error('Selecciona el canal en el que se celebró la reunión.');
        const firma=JSON.stringify(payload);if(intento?.firma!==firma) intento={firma,clave:crypto.randomUUID()};
        enviando=true;guardar.disabled=true;
        const resultado=await ctx.api('clientes/evidencias_kpi',{metodo:'POST',cuerpo:{accion:'registrar',...payload,clave:intento.clave}});
        if(!lectura()) return;
        if(resultado.registro?.cliente_id!==cid) throw new Error('No se puede confirmar este registro.');
        await actualizar();
      }catch(err){if(vivo()) estado.textContent=err.message || 'No se pudo confirmar el registro. Puedes reintentar el mismo hecho sin duplicarlo.';}
      finally{enviando=false;if(vivo()) guardar.disabled=!permisoRegistro(ctx,cid);}
    }}},
      h('div',{class:'fila',style:{flexWrap:'wrap'}},h('label',{class:'campo'},'Hecho',tipo),h('label',{class:'campo'},'Canal',canal),h('label',{class:'campo'},'Motivo',motivo),h('label',{class:'campo'},'Fecha y hora',fecha)),
      informeZona,
      h('p',{class:'sub'},`La hora corresponde a la zona de este dispositivo (${Intl.DateTimeFormat().resolvedOptions().timeZone}). Se guardará también la fecha equivalente en Madrid.`),guardar);
    formZona.append(h('details',{},h('summary',{style:{cursor:'pointer',minHeight:'44px'}},'Registrar un hecho ya realizado'),form));
  }
  nodo.append(h('div',{class:'cuerpo'},h('button',{type:'button',class:'bt mini',on:{click:actualizar}},'Recargar registros')));
  return {nodo,cargar:actualizar};
}
