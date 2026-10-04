// Lectura bajo demanda del DTO219. Sin POST, enlaces privados ni permisos propios.
const id225 = v => typeof v === 'string' && /^[A-Za-z0-9_-]{1,120}$/.test(v);
const n225 = v => Number.isInteger(v) && v >= 0;
const fecha225 = v => {
  if (typeof v !== 'string') return null;
  const fecha = new Date(v);
  return Number.isFinite(+fecha) ? new Intl.DateTimeFormat('es-ES', {timeZone:'UTC',day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(fecha) + ' UTC' : null;
};
export function renderMetadatosTarea225(E,t,h) {
  const ctx=E.ctx, identidad=JSON.stringify([ctx.real?.id,ctx.persona?.id,!!ctx.pilotoLectura]);
  const caja=h('section',{'aria-label':'Checklist y entregable de la copia',class:'pila',style:{gap:'8px',minWidth:'0',overflowWrap:'anywhere'}});
  const vigente=()=>(!E.vigente||E.vigente())&&(!ctx.vigente||ctx.vigente())&&identidad===JSON.stringify([ctx.real?.id,ctx.persona?.id,!!ctx.pilotoLectura]);
  const vivo=()=>vigente()&&caja.isConnected;
  let curso=false;
  const disponible=()=>ctx.servidor&&typeof ctx.api==='function'&&!ctx.pilotoLectura&&id225(t.id)&&typeof t.cli==='string'&&typeof t.lista_id==='string';
  const mensaje=h('p',{class:'sub',role:'status'},ctx.pilotoLectura?'Esta consulta aún no está habilitada en el piloto de lectura. Consulta la tarea original.':!disponible()?'La checklist requiere la lectura autorizada del servidor; esta vista no tiene ese acceso.':'Consulta sólo la copia local autorizada de esta tarea; no lee ClickUp en directo.');
  const contenido=h('div',{class:'pila',style:{gap:'8px'}});
  const boton=h('button',{type:'button',class:'bt mini',disabled:!disponible(),style:{minHeight:'44px',whiteSpace:'normal'},on:{click:async()=>{
    if(!vivo()||curso||!disponible())return;
    curso=true;boton.disabled=true;mensaje.replaceChildren('Leyendo la copia autorizada…');contenido.replaceChildren();
    try{
      const d=await ctx.api(`mi_trabajo/metadatos?tarea=${encodeURIComponent(t.id)}`);
      if(!vivo())return;
      if(!d||d.tarea_id!==t.id||d.cliente_id!==t.cli||d.lista_id!==t.lista_id||d.fuente!=='copia_local_clickup')throw Error('scope');
      const fecha = fecha225(d.estado_leido_utc);
      mensaje.replaceChildren(fecha?`Copia local · lectura de tarea ${fecha}.`:'Copia local · fecha de lectura no acreditada.');
      const c=d.checklists, medido=c?.estado==='observado'&&n225(c.total_confirmado)&&n225(c.resueltos_observados)&&c.resueltos_observados<=c.total_confirmado;
      contenido.append(h('p',{class:'sub'},medido?`${c.resueltos_observados} de ${c.total_confirmado} elementos observados resueltos. Una resolución no acredita entrega ni aceptación.`:c?.estado==='parcial'?`Checklist parcial: ${n225(c.items_observados)?c.items_observados:'cantidad desconocida'} elementos conservados. Total sin confirmar.`:'Checklist sin dato: esta copia no permite concluir que no exista en ClickUp.'));
      const listas=Array.isArray(c?.listas)?c.listas:[];
      for(const lista of listas.slice(0,5)){
        if(!id225(lista?.id))continue;
        const items=Array.isArray(lista.items)?lista.items:[];
        const validos=items.filter(i=>id225(i?.id)&&typeof i.resuelto==='boolean');
        contenido.append(h('details',{},h('summary',{style:{minHeight:'44px',cursor:'pointer',overflowWrap:'anywhere'}},`Lista sin título conservado · ID ${lista.id}`),
          h('p',{class:'sub'},lista.cobertura==='observado'?'Elementos conservados de esta lista.':'Lista parcial o cobertura desconocida; no se acredita el total.'),
          h('ul',{},validos.slice(0,20).map(i=>h('li',{},`${i.resuelto?'Resuelto':'Sin resolver'} · ID ${i.id}`))),
          validos.length>20?h('p',{class:'sub'},`Se muestran 20 de ${validos.length} elementos conservados de esta lista.`):null));
      }
      if(listas.length>5)contenido.append(h('p',{class:'sub'},`Se muestran 5 de ${listas.length} listas conservadas; consulta el original para el resto.`));
      const adj=d.adjuntos?.estado==='observado'&&n225(d.adjuntos.cantidad)?`${d.adjuntos.cantidad} adjuntos observados; enlaces no disponibles.`:'Adjuntos sin dato; no significa cero adjuntos en ClickUp.';
      contenido.append(h('p',{class:'sub'},'Entregable final sin dato: falta un campo y valor verificados. No se infiere de estados, comentarios ni checklist.'),h('p',{class:'sub'},adj),h('p',{class:'sub'},'Copia de alcance limitado. Los elementos sólo se consultan; no se modifican aquí.'));
    }catch{
      if(vivo()){mensaje.replaceChildren('No se pudo consultar esta tarea en el contexto autorizado. Puede faltar acceso o evidencia en la copia. Consulta el original.');contenido.replaceChildren();}
    }finally{curso=false;if(vivo())boton.disabled=!disponible();}
  }}},'Consultar checklist de la copia');
  caja.append(h('b',{},'Checklist y entregable'),mensaje,boton,contenido);return caja;
}
