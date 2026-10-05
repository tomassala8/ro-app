import { h } from '../componentes.js';
const LABELS={correcto:'Correcto',hablar:'Hablar con la persona',error:'Error: revisar horas'};
const identidad=ctx=>JSON.stringify([ctx.real?.id,ctx.persona?.id]);
const activa=p=>p?.estado==='activo'&&p?.activo!==false;

export function controlAnomalia276(ctx,fila,{alGuardar}={}){
  const details=h('details',{style:{minWidth:'0',maxWidth:'100%'}});
  const summary=h('summary',{style:{minHeight:'44px',display:'flex',alignItems:'center',cursor:'pointer'},'aria-label':`Revisión local del registro ${fila.id||'sin ID'}`},'Revisar');
  const zona=h('div',{class:'pila',style:{gap:'var(--s-2)',maxWidth:'100%'}});
  const id=identidad(ctx);let reading=false,loaded=false,current=null,pending=null,busy=false;
  function vive(escribir=false){
    const ps=ctx.datos?.personas||[],target=ps.filter(p=>p?.id===fila.persona_id);
    return details.isConnected&&identidad(ctx)===id&&(!ctx.vigente||ctx.vigente())&&ctx.veModulo?.('horas')&&
      [ctx.real,ctx.persona].every(p=>{const xs=ps.filter(x=>x?.id===p?.id);return xs.length===1&&activa(xs[0]);})&&
      target.length===1&&activa(target[0])&&ctx.ver?.({tipo:'horas_persona',persona_id:fila.persona_id})?.ok===true&&
      (!escribir||!ctx.soloLectura&&ctx.real?.id===ctx.persona?.id&&current?.puede_registrar===true);
  }
  function limpiar(){zona.replaceChildren();summary.textContent='Revisar';current=null;loaded=false;}
  async function cargar(){
    if(reading||loaded||!details.open)return;
    if(!vive()){limpiar();return;}
    reading=true;zona.replaceChildren(h('span',{class:'sub',role:'status'},'Leyendo revisión…'));
    try{
      const r=await ctx.api(`operaciones/anomalias?id=${encodeURIComponent(fila.id)}`);
      if(!vive()){limpiar();return;}
      if(r?.version!=='276.1'||r.origen?.id!==fila.id||r.origen?.persona_id!==fila.persona_id||
         !/^[a-f0-9]{64}$/.test(r.origen?.huella_origen||'')||!Number.isInteger(r.revision)||r.revision<0)throw Error('formato');
      current=r;loaded=true;pintar();
    }catch{if(vive()){zona.replaceChildren(h('span',{class:'sub',role:'status'},'No se pudo leer la revisión. Cierra y abre para reintentar.'));loaded=false;}else limpiar();}
    finally{reading=false;}
  }
  function pintar(){
    if(!vive()){limpiar();return;}
    const estado=current.registro;
    summary.textContent=estado ? `${LABELS[estado.decision]||'Revisión'} · registrado en RO` : 'Revisar';
    const status=h('span',{class:'sub',role:'status'},estado?`Declarado por ${estado.registrado_por} · ${estado.registrado_en}. Entrada no modificada.`:
      current.anterior_incompatible?'La entrada cambió desde la revisión anterior; rectificar exige prueba.':'Registro local; no modifica ClickUp ni envía mensajes.');
    const prueba=h('input',{type:'text',maxlength:'500','aria-label':'Prueba de la revisión de horas',placeholder:'Prueba (obligatoria para Error o rectificar)',value:'',style:{minWidth:'0',maxWidth:'100%'}});
    const botones=Object.entries(LABELS).map(([decision,label])=>{
      const boton=h('button',{type:'button',class:'bt mini',style:{minHeight:'44px'},'aria-label':label},label);
      boton.disabled=!!ctx.soloLectura||current.puede_registrar!==true||ctx.real?.id!==ctx.persona?.id;
      boton.addEventListener('click',async()=>{
        if(busy||!boton.isConnected||!vive(true))return;
        if(!pending){
          const necesita=decision==='error'||current.anterior_incompatible||estado&&estado.decision!==decision;
          if(necesita&&!prueba.value.trim()){status.textContent='Escribe una prueba antes de Error o de rectificar la revisión.';return;}
          const uuid=globalThis.crypto?.randomUUID?.();if(!uuid){status.textContent='No hay identificador seguro para guardar.';return;}
          pending={anomalia_id:fila.id,decision,prueba:prueba.value||'',revision:current.revision,intencion_id:uuid,huella_origen:current.origen.huella_origen};
        }
        if(pending.decision!==decision){status.textContent='Hay un guardado pendiente: reintenta esa decisión o vuelve a abrir la vista.';return;}
        busy=true;prueba.disabled=true;for(const b of botones)b.disabled=true;status.textContent='Guardando revisión en RO…';
        try{
          const r=await ctx.api('operaciones/anomalias',{metodo:'POST',cuerpo:pending});
          if(!boton.isConnected||!vive(true)){if(!vive())limpiar();return;}
          const rec=r?.recibo;
          if(r.version!=='276.1'||r.intencion_id!==pending.intencion_id||!rec||rec.anomalia_id!==fila.id||rec.persona_id!==fila.persona_id||
             rec.huella_origen!==pending.huella_origen||rec.revision!==pending.revision+1||rec.registrado_por!==ctx.real.id||
             rec.decision!==pending.decision||rec.entrada_modificada!==false||rec.envio_realizado!==false)throw Error('recibo');
          current={...current,revision:rec.revision,registro:rec,anterior_incompatible:false};pending=null;pintar();alGuardar?.(rec);
        }catch{if(!vive())limpiar();else if(boton.isConnected&&vive(true)){status.textContent='Sin confirmación. Reintenta el mismo guardado o vuelve a abrir la vista para actualizar.';boton.textContent='Reintentar guardado';}}
        finally{
          busy=false;
          if(boton.isConnected&&vive(true)){prueba.disabled=!!pending;for(const b of botones)b.disabled=!!pending&&b!==boton;}
        }
      });return boton;
    });
    zona.replaceChildren(status,h('div',{class:'fila',style:{display:'flex',gap:'var(--s-1)',flexWrap:'wrap'}},...botones),prueba);
  }
  details.append(summary,zona);details.addEventListener('toggle',()=>{if(!vive()){limpiar();return;}if(details.open)cargar();else if(!busy&&!pending)loaded=false;});
  return details;
}
