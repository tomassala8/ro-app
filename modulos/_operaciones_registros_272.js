import { h, panel, tablaDensa } from '../componentes.js';
const firma=ctx=>JSON.stringify([ctx.real?.id,ctx.persona?.id]);
const actuales=ctx=>ctx.datos?.personas||[];
const activo=p=>p?.estado==='activo'&&p?.activo!==false;
function vigente(ctx,node,id,escribir=false){
  return node.isConnected && firma(ctx)===id && (!ctx.vigente||ctx.vigente()) && ctx.veModulo?.('mi-dia') &&
    [ctx.real,ctx.persona].every(p=>{const xs=actuales(ctx).filter(x=>x?.id===p?.id);return xs.length===1&&activo(xs[0]);}) &&
    (!escribir||!ctx.soloLectura&&ctx.real?.id===ctx.persona?.id);
}
const fecha=x=>typeof x==='string'?x.slice(0,10):'—';
const tabla=(filas,columnas)=>tablaDensa({filas,columnas,porPagina:Math.max(12,filas.length),vacio:{titulo:'Sin registros autorizados.',celebrar:false}});
function control(ctx,box,id,{texto,cuerpo,recibo,alGuardar,validar=()=>true,bloquear=()=>{}}){
  const button=h('button',{type:'button',class:'bt',style:{minHeight:'44px'}},texto);
  const status=h('span',{class:'sub',role:'status'});let pending=null,busy=false;
  const vivo=()=>button.isConnected&&vigente(ctx,box,id,true);
  button.disabled=!!ctx.soloLectura||ctx.real?.id!==ctx.persona?.id;
  button.addEventListener('click',async()=>{
    if(busy||!vivo())return;
    if(!pending){const body=cuerpo();if(!validar(body)){status.textContent='Completa el encargo o la prueba antes de guardar.';return;}const uuid=globalThis.crypto?.randomUUID?.();if(!uuid){status.textContent='No hay identificador seguro para guardar.';return;}pending={...body,intencion_id:uuid};}
    bloquear(true);
    busy=true;button.disabled=true;status.textContent='Guardando en RO…';
    try {
      const r=await ctx.api('operaciones/control',{metodo:'POST',cuerpo:pending});
      if(!vivo())return;
      if(r?.version!=='272.1'||r.intencion_id!==pending.intencion_id||!r.recibo||r.recibo.registrado_por!==ctx.real.id||!recibo(r.recibo,pending))throw Error('recibo');
      const guardado=r.recibo;pending=null;status.textContent=`Guardado en RO · ${guardado.registrado_en}`;
      alGuardar?.(guardado);
    } catch {if(vivo()){status.textContent='Sin confirmación. Reintenta la misma intención o vuelve a abrir para actualizar.';button.textContent='Reintentar guardado';}}
    finally{busy=false;if(vivo()){button.disabled=false;bloquear(!!pending);}}
  });
  return h('span',{style:{display:'inline-flex',alignItems:'center',gap:'var(--s-2)',flexWrap:'wrap'}},button,status);
}
async function cargar(ctx,box,id,preleido){
  if(!vigente(ctx,box,id))return null;
  const r=preleido===undefined?await ctx.api('operaciones/control'):preleido;
  if(!vigente(ctx,box,id))return null;
  if(r?.version!=='272.1'||r.propietario!==ctx.persona.id||!Array.isArray(r.registros))throw Error('formato');
  if(preleido!==undefined||Object.hasOwn(r,'scope_foto_actual')){
    const scope=r.scope_foto_actual;
    if(scope!==null&&!(typeof scope==='string'&&/^[a-f0-9]{64}$/.test(scope)))throw Error('ámbito');
    return {...r,registros:r.registros.filter(f=>f?.tipo!=='foto'||scope!==null&&f.scope_hash===scope&&f.registrado_por===ctx.persona.id)};
  }
  return r;
}

export async function panelEncargos272(cont,ctx){
  const id=firma(ctx),box=h('div',{class:'pila'});cont.append(panel({titulo:'Encargos de Tomás',sub:'Encargos propios y asignados que puedes leer. Marcar hecho exige una prueba; no envía mensajes.'},box));
  if(!vigente(ctx,box,id))return;
  box.append(h('p',{role:'status'},'Leyendo encargos…'));
  try {
    const res=await cargar(ctx,box,id);if(!res)return;box.replaceChildren();
    const filas=res.registros.filter(r=>r.tipo==='encargo');
    const titulo=h('input',{type:'text',maxlength:'400',placeholder:'Qué hay que hacer','aria-label':'Encargo',style:{minWidth:'0',width:'100%'}});
    const limite=h('input',{type:'date','aria-label':'Fecha límite'});
    const asignado=h('select',{'aria-label':'Responsable del encargo'});
    const candidatas=actuales(ctx).filter(p=>activo(p)&&actuales(ctx).filter(x=>x?.id===p.id).length===1&&
      (p.id===ctx.persona.id||ctx.persona.puestos?.includes('direccion')&&ctx.ver?.({tipo:'notas_persona',persona_id:p.id})?.ok));
    for(const p of candidatas)asignado.append(h('option',{value:p.id,selected:p.id===ctx.persona.id},ctx.nombre?.(p.id)||p.alias||p.nombre||p.id));
    const cliente=h('select',{'aria-label':'Cliente del encargo'});cliente.append(h('option',{value:''},'Equipo · sin cliente'));
    const clientes=(ctx.clientesVisibles||[]).filter(c=>c?.activo_confirmado===true&&ctx.ver?.({tipo:'cliente_detalle',cliente_id:c.id})?.ok);
    for(const c of clientes)cliente.append(h('option',{value:c.id},c.nombre||c.id));
    const form=h('div',{class:'rango',style:{display:'flex',gap:'var(--s-2)',flexWrap:'wrap'}});
    form.append(titulo,asignado,cliente,limite,control(ctx,box,id,{texto:'Añadir encargo',
      cuerpo:()=>({tipo:'encargo',operacion:'crear',revision:0,titulo:titulo.value||'',asignado:asignado.value||ctx.persona.id,cliente_id:cliente.value||null,limite:limite.value||null}),
      validar:b=>!!b.titulo.trim()&&b.titulo.length<=400,
      bloquear:estado=>{for(const el of [titulo,asignado,cliente,limite])el.disabled=estado;},
      recibo:(r,b)=>r.tipo==='encargo'&&r.autor===ctx.real.id&&r.asignado===b.asignado&&r.revision===1,
      alGuardar:r=>{filas.unshift(r);titulo.value='';pintar();}}));
    if(res.puede_registrar===true&&!ctx.soloLectura)box.append(form);
    const zona=h('div',{});box.append(zona);
    function pintar(){
      if(!vigente(ctx,box,id))return;
      zona.replaceChildren(tabla(filas,[{clave:'titulo',titulo:'Encargo',principal:true},
        {clave:'asignado',titulo:'Responsable',celda:r=>ctx.nombre?.(r.asignado)||r.asignado},
        {clave:'limite',titulo:'Límite',celda:r=>fecha(r.limite)},
        {clave:'hecho',titulo:'Estado / prueba',celda:r=>h('span',{},r.hecho?'Hecho declarado':'Abierto',r.prueba?h('span',{class:'sub'},r.prueba):null)},
        {clave:'registrado_en',titulo:'Registro',celda:r=>h('span',{class:'sub'},`${ctx.nombre?.(r.registrado_por)||r.registrado_por} · ${r.registrado_en}`)},
        {clave:'accion',titulo:'',celda:r=>{
          const proof=h('input',{type:'text',maxlength:'500',value:r.prueba||'',placeholder:'Prueba de lo hecho','aria-label':'Prueba del encargo',style:{maxWidth:'100%',minWidth:'0'}});
          return h('details',{},h('summary',{style:{minHeight:'44px'}},r.hecho?'Deshacer':'Marcar hecho'),proof,
            control(ctx,box,id,{texto:r.hecho?'Deshacer registro':'Guardar hecho',cuerpo:()=>({tipo:'encargo',operacion:'actualizar',objeto:r.objeto,revision:r.revision,hecho:!r.hecho,prueba:proof.value||''}),
              validar:b=>!b.hecho||!!b.prueba.trim(),bloquear:estado=>{proof.disabled=estado;},
              recibo:(d,b)=>d.tipo==='encargo'&&d.objeto===r.objeto&&d.revision===b.revision+1&&d.hecho===b.hecho,
              alGuardar:d=>{Object.assign(r,d);pintar();}}));
        }}]));
    }
    pintar();
  } catch {if(vigente(ctx,box,id))box.replaceChildren(h('p',{role:'status'},'No se pudieron leer los encargos. Vuelve a abrir para reintentar.'));}
}

export async function panelFotosControl272(cont,ctx,preleido){
  const id=firma(ctx),box=h('div',{class:'pila'});cont.append(panel({titulo:'Fotos de los miércoles y viernes',sub:'Puedes guardar una foto ahora. El servidor conserva el corte de cada fuente; no es una recarga ni una medición nueva.'},box));
  if(!vigente(ctx,box,id))return;
  try {
    const res=await cargar(ctx,box,id,preleido);if(!res)return;
    const fotos=res.registros.filter(r=>r.tipo==='foto');
    const roles=[ctx.real,ctx.persona].every(p=>p?.puestos?.some(x=>['operaciones','direccion'].includes(x)));
    const zona=h('div',{});
    if(roles&&res.puede_registrar===true)box.append(control(ctx,box,id,{texto:'Guardar foto de ahora',cuerpo:()=>({tipo:'foto',revision:0}),
      recibo:r=>r.tipo==='foto'&&Array.isArray(r.metricas)&&r.metricas.length===7&&r.cumplimiento===null&&r.exhaustiva===false,
      alGuardar:r=>{fotos.unshift(r);pintar();}}));
    box.append(zona);
    function pintar(){
      if(!vigente(ctx,box,id))return;
      const etiquetas=['Clientes +48 h sin respuesta','Alarmas en rojo','% horas imputadas','Tareas en revisión +48 h','Nota media de accounts','Semáforos sin rellenar','Acciones con rastro (acumulado)'];
      zona.replaceChildren(tabla(fotos,[{clave:'registrado_en',titulo:'Foto guardada',celda:r=>r.registrado_en},
        ...etiquetas.map((et,i)=>({clave:'m'+i,titulo:et,celda:r=>h('span',{title:`${r.metricas[i]?.detalle||'Sin medición'} · fuente ${r.metricas[i]?.fecha_fuente||'sin fecha'}`},r.metricas[i]?.valor==null?'—':String(r.metricas[i].valor))})),
        {clave:'detalle',titulo:'Fuentes',celda:r=>h('details',{},h('summary',{style:{minHeight:'44px'}},'Cortes y cobertura'),
          ...r.metricas.map(m=>h('p',{class:'sub'},`${m.etiqueta}: ${m.estado} · ${m.fecha_fuente||'sin fecha'} · ${m.detalle}`)))}]));
    }
    pintar();
  } catch {if(vigente(ctx,box,id))box.replaceChildren(h('p',{role:'status'},'No se pudieron leer las fotos de control.'));}
}
