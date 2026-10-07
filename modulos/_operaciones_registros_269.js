import { h, panel } from '../componentes.js';
const RITUALES = [['manana','Ronda de la mañana'],['cierre','Cierre del día'],['lunes','Lunes · semáforos'],['viernes','Viernes · todo a cero y 3 números'],['mes','Primer día del mes']];
const firma = ctx => JSON.stringify([ctx.real?.id,ctx.persona?.id]);
function puertas(ctx,node,identidad,escribir=false) {
  return node.isConnected && (!ctx.vigente || ctx.vigente()) && firma(ctx)===identidad && ctx.veModulo?.('mi-dia') &&
    (!escribir || (!ctx.soloLectura && ctx.real?.id===ctx.persona?.id));
}
function fila(ctx,{ritual,periodo,registro,personaId,puede},estadoLectura) {
  const ident=firma(ctx),fila=h('div',{class:'rango',style:{display:'flex',gap:'var(--s-2)',alignItems:'center',flexWrap:'wrap'}});
  const status=h('span',{class:'sub',role:'status'},registro ? `Declarado por ${registro.autor} · ${registro.registrado_en}` : 'Sin registro');
  const nota=h('input',{type:'text',maxlength:'300','aria-label':'Nota del registro',placeholder:'Nota opcional',value:registro?.nota||'',style:{minWidth:'0',maxWidth:'100%'}});
  const boton=h('button',{type:'button',class:'bt',style:{minHeight:'44px'}},personaId?'Registrar avisado':registro?.hecho?'Deshacer registro':'Marcar hecho');
  let revision=registro?.revision||0,hecho=registro?.hecho===true,enCurso=false,pendiente=null;
  const vigente=escribir=>puertas(ctx,fila,ident,escribir) && estadoLectura();
  // La fila aún no está montada aquí; el callback comprueba conexión al actuar.
  boton.disabled=!puede || !!ctx.soloLectura || ctx.real?.id!==ctx.persona?.id;nota.disabled=boton.disabled;
  boton.addEventListener('click',async()=>{
    if(enCurso || !puede || !vigente(true))return;
    if(!pendiente) {
      const id=globalThis.crypto?.randomUUID?.();
      if(!id){status.textContent='Este navegador no permite un registro seguro.';return;}
      pendiente={tipo:personaId?'avisado':'ritual',revision,intencion_id:id,nota:nota.value||'',
        ...(personaId?{persona_id:personaId}:{ritual,periodo,hecho:!hecho})};
    }
    enCurso=true;boton.disabled=true;nota.disabled=true;status.textContent='Guardando en RO…';
    try {
      const res=await ctx.api('operaciones/registros',{metodo:'POST',cuerpo:pendiente});
      if(!vigente(true))return;
      const r=res?.recibo;
      if(res.version!=='269.1' || res.intencion_id!==pendiente.intencion_id || !r || r.autor!==ctx.real.id ||
          r.tipo!==pendiente.tipo || r.revision!==revision+1 || r.envio_realizado!==false ||
          (personaId ? r.persona_id!==personaId : r.ritual!==ritual || r.periodo!==periodo || r.hecho!==pendiente.hecho)) throw Error('recibo');
      revision=r.revision;hecho=r.hecho===true;pendiente=null;
      status.textContent=`Guardado en RO · ${r.registrado_en} · declaración propia${personaId?' · no envía ningún mensaje':''}`;
      boton.textContent=personaId?'Registrar otro aviso':hecho?'Deshacer registro':'Marcar hecho';
    } catch {
      if(!vigente(true))return;
      status.textContent='Sin confirmación de guardado. Reintenta la misma intención o vuelve a abrir para actualizar.';
      boton.textContent='Reintentar guardado';
    } finally {
      enCurso=false;
      if(vigente(true)){boton.disabled=!puede;nota.disabled=!!pendiente || !puede;}
    }
  });
  fila.append(nota,boton,status);return fila;
}

export async function panelRituales269(cont,ctx) {
  const id=firma(ctx),box=h('div',{class:'pila'});
  const vigente=()=>puertas(ctx,box,id);
  cont.append(panel({titulo:'Rituales',sub:'Registro propio local, con autor y fecha. No certifica una acción externa.'},box));
  if(!vigente())return;
  box.append(h('p',{role:'status'},'Leyendo registros…'));
  try {
    const r=await ctx.api('operaciones/registros');
    if(!vigente()){box.replaceChildren();return;}
    if(r?.version!=='269.1' || r.propietario!==ctx.persona.id || !Array.isArray(r.registros) || !r.periodos)throw Error('formato');
    box.replaceChildren();
    for(const [ritual,titulo] of RITUALES) {
      const periodo=r.periodos[ritual],xs=r.registros.filter(x=>x.tipo==='ritual' && x.ritual===ritual && x.periodo===periodo);
      if(typeof periodo!=='string' || xs.length>1)throw Error('periodo');
      box.append(h('div',{},h('b',{},titulo),h('span',{class:'sub'},periodo),
        fila(ctx,{ritual,periodo,registro:xs[0],puede:r.puede_registrar===true},vigente)));
    }
  } catch {if(vigente())box.replaceChildren(h('p',{role:'status'},'No se pudo leer el registro de rituales. Vuelve a abrir para reintentar.'));}
}

export function filaAvisado269(ctx,personaId) {
  const contenido=h('div',{class:'pila'}),box=h('details',{},h('summary',{style:{minHeight:'44px',display:'flex',alignItems:'center',cursor:'pointer'},'aria-label':'Consultar o registrar un aviso; no confirma un aviso enviado'},'Aviso'),contenido),id=firma(ctx);
  const vigente=()=>puertas(ctx,box,id);
  contenido.append(h('p',{class:'sub'},'Declaración propia, con autor y fecha.'));
  const cargar=async()=>{
    if(!vigente())return;
    try {
      const r=await ctx.api('operaciones/registros');
      if(!vigente())return;
      if(r?.version!=='269.1' || r.propietario!==ctx.persona.id || !Array.isArray(r.registros))throw Error('formato');
      const registro=r.registros.find(x=>x.tipo==='avisado' && x.persona_id===personaId && x.periodo===r.periodos.manana);
      const ps=ctx.datos?.personas?.filter(x=>x?.id===personaId)||[];
      const permiso=ps.length===1 && ps[0].estado==='activo' && ps[0].activo!==false &&
        [ctx.real,ctx.persona].every(p=>p?.puestos?.some(x=>['direccion','operaciones'].includes(x))) && ctx.ver?.({tipo:'horas_persona',persona_id:personaId})?.ok===true;
      contenido.append(fila(ctx,{personaId,registro,puede:permiso&&r.puede_registrar===true},vigente));
    } catch {if(vigente())contenido.append(h('p',{role:'status'},'No se pudo leer el registro de avisos.'));}
  };
  // Se devuelve antes de montar el nodo: primera lectura cuando ya está conectado.
  let cargado=false;
  box.addEventListener('toggle',()=>{if(box.open&&!cargado&&vigente()){cargado=true;cargar();}});return box;
}
