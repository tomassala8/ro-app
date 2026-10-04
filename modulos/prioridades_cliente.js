import {h,panel,chipEstado,vacioLinea,avisoFlotante} from '../componentes.js';
import {copiarInstrucciones} from './tarea_ia.js';
import {consejoCompacto} from './_trabajo.js';
import {ambitoPrioridades337,encargoPrioridades337,evidenciaEncargo337} from './_prioridades_contexto_337.js';

const AREAS={paid:'Paid',crm:'CRM y conversión',accounts:'Accounts',seo:'SEO'};
const PUESTOS={direccion:'todo',operaciones:'todo',proyectos:'todo',account:'suyo',trafficker:'suyo',jefa_publicidad:'todo',especialista_ghl:'suyo',jefa_crm:'todo',seo:'suyo',jefa_seo:'todo'};

//484: estilo local, conserva el detalle completo y los controles existentes.
const CSS484=`.ro-prioridades[data-prioridades-raiz]{min-width:0;gap:12px}
.ro-prioridades[data-prioridades-raiz] .prioridades-filtros484{display:flex;flex-wrap:wrap;gap:10px 16px;padding:12px 16px;margin:0 0 4px;border:1px solid var(--line);border-radius:14px;background:var(--card);min-width:0}
.ro-prioridades[data-prioridades-raiz] .prioridades-filtros484 label{display:flex;align-items:center;gap:8px;flex:1 1 240px;min-width:0;font-size:13px}
.ro-prioridades[data-prioridades-raiz] .prioridades-filtros484 select{flex:1;min-width:0;max-width:100%;min-height:44px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--ink);padding:8px 10px;font:inherit}
.ro-prioridades[data-prioridades-raiz] .prioridades-filtros484 select:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.ro-prioridades[data-prioridades-raiz] .ro-prioridades-tabla th{padding:8px 10px;font-size:12px}
.ro-prioridades[data-prioridades-raiz] .ro-prioridades-tabla td{padding:8px 10px;line-height:1.3}
.ro-prioridades[data-prioridades-raiz] .ro-prioridades-tabla th:nth-child(1){width:19%}
.ro-prioridades[data-prioridades-raiz] .ro-prioridades-tabla th:nth-child(2){width:26%}
.ro-prioridades[data-prioridades-raiz] .ro-prioridades-tabla th:nth-child(4){width:16%}
.ro-prioridades[data-prioridades-raiz] .ro-prioridades-tabla th:nth-child(5){width:112px}
.ro-prioridades[data-prioridades-raiz] .ro-prioridades-tabla td:nth-child(5) button{white-space:nowrap;word-break:normal;overflow-wrap:normal;min-width:82px;padding:6px 10px}
.ro-prioridades[data-prioridades-raiz] .ro-prioridades-preview{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ro-prioridades[data-prioridades-raiz] .ro-prioridades-meta{margin-top:3px;line-height:1.3}
.ro-prioridades[data-prioridades-raiz] .ro-prioridades-fila-detalle>td{padding:14px;white-space:normal}
.ro-prioridades[data-prioridades-raiz] .ro-prioridades-accion{padding:14px;gap:10px}
@media(max-width:800px){.ro-prioridades[data-prioridades-raiz] .ro-prioridades-tabla tbody>tr{padding:10px 12px}.ro-prioridades[data-prioridades-raiz] .ro-prioridades-tabla td{padding:5px 0}.ro-prioridades[data-prioridades-raiz] .ro-prioridades-fila-detalle>td{padding:12px}.ro-prioridades[data-prioridades-raiz] .prioridades-filtros484{padding:10px 12px}.ro-prioridades[data-prioridades-raiz] .prioridades-filtros484 label{flex-basis:100%}}`;


export function filtrosDesdeEnlace(hash,clientes){
  const q=new URLSearchParams(typeof hash==='string'?(hash.split('?')[1]||''):'');
  if(['cliente','area'].some(k=>q.getAll(k).length>1))return {error:'El enlace contiene filtros ambiguos. Abre Prioridades por cliente desde el menú.'};
  const cliente=q.get('cliente')||'',area=q.get('area')||'';
  if(cliente && !clientes.some(c=>c.id===cliente))return {error:'El cliente del enlace no está disponible en tu cartera autorizada.'};
  if(area && !Object.hasOwn(AREAS,area))return {error:'El área del enlace no está disponible. Abre Prioridades por cliente desde el menú.'};
  return {cliente,area};
}

export function instrucciones(r,nombre){
  return encargoPrioridades337(r,nombre,AREAS);
}

export function agruparPrioridades(recomendaciones, permitidos) {
  const grupos = new Map();
  for (const r of recomendaciones) {
    if (!r || !permitidos.has(r.cliente_id)) continue;
    if (!grupos.has(r.cliente_id)) grupos.set(r.cliente_id, []);
    grupos.get(r.cliente_id).push(r);
  }
  const prioridad = r => Number.isInteger(r.prioridad) && r.prioridad >= 1 && r.prioridad <= 3 ? r.prioridad : 99;
  return [...grupos].map(([cliente_id, acciones]) => ({ cliente_id,
    acciones: acciones.slice().sort((a,b) => prioridad(a)-prioridad(b)),
    prioridad: Math.min(...acciones.map(prioridad))
  })).sort((a,b) => a.prioridad-b.prioridad || a.cliente_id.localeCompare(b.cliente_id));
}

export default {
  id:'prioridades-cliente',titulo:'Prioridades por cliente',grupo:'Hoy',puestos_que_lo_ven:PUESTOS,
  async render(cont,ctx){
    if(typeof ctx.vigente==='function'&&!ctx.vigente())return;
    const principal=cont;
    const alcance=ambitoPrioridades337(ctx);
    const ruta=typeof location==='undefined'?null:location.hash;
    const raiz=h('div',{class:'pila ro-prioridades','data-prioridades-raiz':''});
    principal.replaceChildren(raiz);
    let soltarConsejo=()=>{};
    const vigente=()=>{
      const actual=ambitoPrioridades337(ctx),ok=!!alcance&&actual?.firma===alcance.firma&&raiz.isConnected&&raiz.parentNode===principal&&(typeof ctx.vigente!=='function'||ctx.vigente())&&(ruta===null||location.hash===ruta);
      if(!ok){soltarConsejo();raiz.replaceChildren();}return ok;
    };
    cont=raiz;
    ctx.titulo('Prioridades por cliente','Entender qué requiere atención y cuál es el siguiente paso');
    if(!ctx.servidor){cont.append(vacioLinea('Esta vista necesita datos autorizados del servidor.'));return;}
    if(!vigente())return;
    let datos={recomendaciones:[],cobertura:{clientes:[]}},metodoDatos=null,seoDatos=null;
    const filtros=filtrosDesdeEnlace(ruta,alcance.clientes);
    if(filtros.error){cont.append(vacioLinea(filtros.error));return;}
    let area=filtros.area,cliente=filtros.cliente,limite=12,abierto=null;
    const fuentes={operativo:{nombre:'Paid y CRM',ruta:'cerebro/operativo',estado:'cargando'},metodo:{nombre:'Seguimiento de reuniones',ruta:'metodo/sugerencias',estado:'cargando'}};
    if(ctx.veModulo('seo-web'))fuentes.seo={nombre:'SEO',ruta:'cerebro/seo',estado:'cargando'};
    const fuentesEstado=h('div',{class:'fila',style:{gap:'12px',flexWrap:'wrap'},role:'status','aria-live':'polite'});
    // 308: el cerebro entrega las únicas recomendaciones de cadencia validadas.
    // La lectura independiente del método sólo informa el estado de su fuente.
    const filas=()=>[...(datos.recomendaciones||[]),...(seoDatos?.recomendaciones||[])].filter(r=>alcance.ids.includes(r?.cliente_id));
    const medicion=h('div',{class:'pila'});
    const seoMedicion=h('div',{class:'pila'});
    const estados={sin_dato:'Sin dato',no_instrumentado:'Pendiente de medir',medido:'Medido',conteo_crm_no_cualificacion:'Recibidos; cualificación pendiente',eventos_del_periodo:'Eventos del periodo'};
    const etapas={paid:'Paid',recibidos:'Leads recibidos',cualificados:'Leads cualificados',citas:'Citas',cierre:'Ventas'};
    const nombres=new Map(alcance.clientes.map(c=>[c.id,c.nombre||c.cliente||c.id]));
    const clienteTxt=id=>nombres.get(id)||id;
    const caja=h('div',{class:'pila','aria-label':'Prioridades agrupadas por cliente'});
    const resumen=h('p',{class:'sub',role:'status'});
    const mas=h('button',{class:'bt',on:{click:()=>{if(!vigente())return;limite+=12;pintar();}}},'Ver más clientes');
    const selectArea=h('select',{'aria-label':'Área',on:{change:e=>{if(!vigente())return;area=e.target.value;limite=12;pintar();}}},h('option',{value:''},'Todas las áreas'),...Object.entries(AREAS).map(([k,v])=>h('option',{value:k},v)));
    const selectCliente=h('select',{'aria-label':'Cliente',style:{minHeight:'44px',maxWidth:'100%',minWidth:0},on:{change:e=>{if(!vigente())return;cliente=e.target.value;limite=12;pintar();}}});
    selectArea.style.minHeight='44px';selectArea.style.maxWidth='100%';
    mas.style.minHeight='44px';
    cont.replaceChildren(h('link',{rel:'stylesheet',href:'./modulos/prioridades_cliente.css'}),h('style',{},CSS484),h('div',{class:'prioridades-filtros484'},h('label',{},'Área ',selectArea),h('label',{},'Cliente ',selectCliente)),resumen,caja,mas,
      h('details',{},h('summary',{},'Fuentes y datos que faltan'),fuentesEstado,medicion,seoMedicion),
      h('details',{},h('summary',{},'Cómo trabajar con estas propuestas'),h('p',{class:'sub'},'Abre una propuesta para revisar el motivo, la evidencia y el responsable. Comprueba si ya existe una tarea antes de preparar el encargo. ClickUp conserva las tareas y GoHighLevel conserva las conversaciones y los flujos.')));
    if(typeof MutationObserver==='function'&&typeof raiz.closest==='function'&&vigente())soltarConsejo=consejoCompacto(raiz,raiz);
    async function copiarBloque(boton,texto,mensaje){
      if(!vigente()||!boton.isConnected||!texto?.isConnected||boton.disabled)return;
      boton.disabled=true;
      try{
        const ok=await copiarInstrucciones(texto.value,{fallback:()=>{
          if(!vigente()||!boton.isConnected||!texto.isConnected)return false;
          texto.focus();texto.select();return document.execCommand('copy');
        }});
        if(!vigente()||!boton.isConnected||!texto.isConnected)return;
        avisoFlotante(ok?mensaje:'No se pudo copiar. Selecciona el texto y cópialo manualmente.');
      }catch{
        if(vigente()&&boton.isConnected)avisoFlotante('No se pudo copiar. Selecciona el texto y cópialo manualmente.');
      }finally{if(vigente()&&boton.isConnected)boton.disabled=false;}
    }
    function borradorTarea(r){
      const cuerpo=h('div',{class:'pila'});
      const boton=h('button',{class:'bt',style:{minHeight:'44px'},on:{click:async()=>{
        if(!vigente()||!boton.isConnected||!cuerpo.isConnected||boton.disabled)return;
        boton.disabled=true;
        cuerpo.replaceChildren(h('p',{class:'sub',role:'status'},'Preparando el borrador con tus fuentes autorizadas…'));
        try{
          const b=await ctx.api(`cerebro/borrador?cliente_id=${encodeURIComponent(r.cliente_id)}&regla_id=${encodeURIComponent(r.regla_id)}`);
          if(!vigente()||!cuerpo.isConnected||!boton.isConnected)return;
          if(b.estado!=='borrador'||b.enviable!==false||!b.payload?.description)throw new Error('Borrador no disponible');
          const texto=h('textarea',{'aria-label':`Borrador de tarea de ${clienteTxt(r.cliente_id)}`,readOnly:true,rows:12,style:{width:'100%',maxWidth:'100%',minWidth:0,boxSizing:'border-box'}},`${b.payload.name}\n\n${b.payload.description}`);
          cuerpo.replaceChildren(h('p',{role:'status'},'Borrador preparado. La tarea todavía no se ha creado en ClickUp.'),texto,
            h('div',{},h('strong',{},'Antes de crear la tarea:'),...(b.bloqueos||[]).map(v=>h('p',{class:'sub'},v)),...(b.avisos||[]).map(v=>h('p',{class:'sub'},v))),
            h('button',{class:'bt pri',style:{minHeight:'44px'},'data-uso':'copiar-borrador',on:{click:async e=>{
              await copiarBloque(e.currentTarget,texto,'Borrador copiado. Comprueba los pendientes antes de crear la tarea.');
            }}},'Copiar borrador'));
          boton.textContent='Actualizar borrador';
        }catch{
          if(vigente()&&cuerpo.isConnected&&boton.isConnected)cuerpo.replaceChildren(h('p',{class:'sub',role:'status'},'No se pudo preparar el borrador. Reintenta o revisa la propuesta; no se ha creado ninguna tarea.'));
        }finally{if(vigente()&&boton.isConnected)boton.disabled=false;}
      }}},'Preparar borrador');
      return h('details',{},h('summary',{},'Preparar tarea para ClickUp'),h('p',{class:'sub'},'El borrador incluye el motivo, la evidencia y cómo comprobar la entrega. Revisa la lista, el responsable y las tareas existentes antes de crearlo.'),boton,cuerpo);
    }
    function pintar(){
      if(!vigente())return;
      fuentesEstado.replaceChildren(...Object.entries(fuentes).map(([id,f])=>h('div',{class:'fila',style:{gap:'var(--s-3)',flexWrap:'wrap'}},h('span',{class:'sub'},`${f.nombre}: ${f.estado==='cargando'?'leyendo fuentes…':f.estado==='lista'?'fuente leída':'no disponible; no se han supuesto datos'}`),...(f.estado==='error'?[h('button',{class:'bt',style:{minHeight:'44px'},'aria-label':`Reintentar ${f.nombre}`,on:{click:()=>cargar(id)}},'Reintentar')]:[]))));
      const recomendaciones=filas();
      const cobertura=(datos.cobertura?.clientes||[]).filter(c=>alcance.ids.includes(c?.cliente_id));
      // Mantiene el cliente del enlace aunque sus fuentes no tengan filas;
      // las opciones proceden de la cartera autorizada, nunca de un payload.
      const ids=[...nombres.keys()];
      selectCliente.replaceChildren(h('option',{value:''},'Todos mis clientes'),...ids.sort((a,b)=>clienteTxt(a).localeCompare(clienteTxt(b),'es')).map(id=>h('option',{value:id},clienteTxt(id))));
      selectCliente.value=cliente;
      selectArea.value=area;
      medicion.hidden=area==='seo'||area==='accounts'||fuentes.operativo.estado!=='lista';
      const visibles=cobertura.filter(c=>!cliente||c.cliente_id===cliente);
      medicion.replaceChildren(panel({titulo:'Qué podemos medir',sub:area==='paid'?'Cobertura Paid y conexión con CRM; no acredita medición completa del embudo':area==='crm'?'Cobertura CRM y conexión con Paid; no acredita medición completa del embudo':'Fuentes Paid y CRM: las ventas son el resultado final'},h('div',{class:'cuerpo pila'},h('p',{},`Cobertura conjunta de ${visibles.length} ${visibles.length===1?"cliente":"clientes"} en las fuentes Paid o CRM disponibles${area?`; no es un conteo exclusivo de ${AREAS[area]}`:""}. El seguimiento completo necesita unir cada lead con sus contactos, citas y ventas.`),...(cliente?visibles.map(c=>h('div',{},...Object.entries(etapas).map(([k,v])=>h('p',{class:'sub'},`${v}: ${estados[c.cadena?.[k]]||c.cadena?.[k]||'Sin dato'}`)),h('details',{},h('summary',{},'Datos que faltan y límites'),...(c.limites||[]).map(l=>h('p',{class:'sub'},l.texto))))):[h('p',{class:'sub'},'Selecciona un cliente para ver las etapas medidas y los datos pendientes. No calculamos porcentajes entre totales que no pertenecen a la misma cohorte.')]))));
      const seoClientes=(seoDatos?.clientes||[]).filter(c=>alcance.ids.includes(c?.cliente_id)&&(!cliente||c.cliente_id===cliente)&&(!area||area==='seo'));
      seoMedicion.replaceChildren(...(seoClientes.length?[panel({titulo:'Objetivos SEO locales',sub:'Posición 1 como aspiración; orgánico y Maps se miden por separado'},h('div',{class:'cuerpo pila'},...(cliente?seoClientes.map(c=>h('div',{},...((c.objetivos||[]).length?(c.objetivos||[]).map(o=>h('p',{class:'sub'},`${o.canal==='maps'?'Maps':'Orgánico'} · ${o.consulta_medida||o.consulta} · posición ${o.posicion??'sin dato'} · ${o.fecha||'fecha pendiente'}${!o.dispositivo||!o.ubicacion_medicion?' · verificar ubicación y dispositivo':''}`)):[h('p',{},'Ciudad y servicios reales pendientes de confirmar antes de definir consultas.')]),...((c.objetivos_historicos||[]).length?[h('details',{},h('summary',{},'Objetivos históricos para contrastar'),h('p',{class:'sub'},'Estos documentos anteriores orientan la revisión. Todavía no confirman el objetivo actual ni activan consultas o comparaciones.'),...(c.objetivos_historicos||[]).map(o=>h('div',{},h('p',{},`${o.tipo}: ${o.valor}`),h('p',{class:'sub'},`${o.fecha_documento} · ${o.fuente} · ${o.estado}`),...(o.razones||[]).map(t=>h('p',{class:'sub'},t)))) )]:[]),h('p',{class:'sub'},`Artículos publicados en 30 días: ${c.contenido?.publicados_30_dias??'sin inventario completo'} · Última publicación observada: ${c.contenido?.ultima_publicacion_observada||'sin dato'}`))):[h('p',{class:'sub'},`${seoClientes.length} clientes con SEO confirmado en tu vista. Selecciona uno para ver objetivos y mediciones disponibles.`)])))]:[]));
      const lista=recomendaciones.filter(r=>(!area||r.area===area)&&(!cliente||r.cliente_id===cliente));
      const grupos=agruparPrioridades(lista,new Set(nombres.keys()));
      const pendiente=Object.values(fuentes).some(f=>f.estado==='cargando');
      resumen.textContent=grupos.length ? `${grupos.length} clientes con recomendaciones · ${grupos.reduce((n,g)=>n+g.acciones.length,0)} acciones para revisar${pendiente?' · Actualizando fuentes…':''}` : pendiente ? 'Leyendo las fuentes de tus clientes…' : 'Sin recomendaciones en las fuentes disponibles para este filtro.';
      mas.hidden=grupos.length<=limite;
      const responsable=r=>r.responsable_id?ctx.nombre(r.responsable_id):({trafficker:'Publicidad · por asignar',account:'Account · por asignar',crm:'CRM · por asignar',seo:'SEO · por asignar'}[r.responsable_role]||'Por confirmar');
      function detalle(g){
        return h('div',{class:'ro-prioridades-detalle'},h('p',{class:'sub'},'Revisa el motivo y el trabajo existente antes de preparar una tarea.'),...g.acciones.map(r=>h('article',{class:'ro-prioridades-accion'},
          h('div',{class:'fila',style:{justifyContent:'space-between',gap:'12px',flexWrap:'wrap'}},h('h3',{},r.titulo),chipEstado('gris',AREAS[r.area]||r.area)),
          h('p',{class:'ro-prioridades-motivo'},r.motivo),
          h('p',{class:'ro-prioridades-paso'},h('strong',{},'Qué hacer: '),r.accion),
          h('p',{class:'sub'},`Responsable: ${responsable(r)} · ${r.certeza||'Revisar evidencia'}`),
          h('div',{class:'ro-prioridades-herramientas'},
            borradorTarea(r),
            h('details',{on:{toggle:()=>vigente()}},h('summary',{},'Preparar encargo para mi IA'),h('textarea',{'aria-label':`Encargo para IA de ${clienteTxt(r.cliente_id)}`,readOnly:true,rows:10,style:{width:'100%',maxWidth:'100%',minWidth:0,boxSizing:'border-box'}},instrucciones(r,clienteTxt(r.cliente_id))),h('button',{class:'bt pri','data-uso':'copiar-ia',on:{click:async e=>{await copiarBloque(e.currentTarget,e.currentTarget.parentElement.querySelector('textarea'),'Instrucciones copiadas. Revisa los accesos en tu IA.');}}},'Copiar encargo')),
            h('details',{on:{toggle:()=>vigente()}},h('summary',{},'Ver evidencia'),...(r.evidencias||[]).map(e=>h('p',{class:'sub'},evidenciaEncargo337(e))),h('p',{},r.criterio_entrega||'Confirmar el criterio de entrega antes de ejecutar.'))
          )
        )));
      }
      const cuerpo=h('tbody',{});
      for(const g of grupos.slice(0,limite)){
        const r=g.acciones[0];
        const id=`prioridad-${g.cliente_id}`;
        const expandido=abierto===g.cliente_id;
        cuerpo.append(h('tr',{class:expandido?'ro-prioridades-seleccionada':''},
          h('td',{'data-label':'Cliente'},h('a',{class:'ro-prioridades-cliente',href:`#/ficha/${encodeURIComponent(g.cliente_id)}`,on:{click:e=>{if(!vigente())e.preventDefault();}}},clienteTxt(g.cliente_id)),h('span',{class:'ro-prioridades-meta'},`${g.acciones.length} ${g.acciones.length===1?'acción':'acciones'} · ${[...new Set(g.acciones.map(a=>AREAS[a.area]||a.area))].join(', ')}`)),
          h('td',{'data-label':'Señal'},h('strong',{class:'ro-prioridades-preview',title:`${r.titulo} · ${r.motivo||'Evidencia pendiente de revisar'}`,'aria-label':`${r.titulo}. ${r.motivo||'Evidencia pendiente de revisar'}`},r.titulo),...(g.prioridad===1?[h('span',{class:'ro-prioridades-meta'},'Prioridad alta')]:[])),
          h('td',{'data-label':'Acción'},h('span',{class:'ro-prioridades-preview',title:r.accion,'aria-label':r.accion},r.accion)),
          h('td',{'data-label':'Responsable'},responsable(r)),
          h('td',{'data-label':'Acciones'},h('button',{class:'bt','aria-expanded':String(expandido),'aria-controls':id,'aria-label':`${expandido?'Cerrar':'Revisar'} acciones de ${clienteTxt(g.cliente_id)}`,on:{click:()=>{if(!vigente())return;abierto=expandido?null:g.cliente_id;pintar();}}},expandido?'Cerrar':'Revisar'))
        ));
        if(expandido)cuerpo.append(h('tr',{class:'ro-prioridades-fila-detalle'},h('td',{colspan:5,id},detalle(g))));
      }
      caja.replaceChildren(...(grupos.length?[h('div',{class:'ro-prioridades-tabla'},h('table',{},h('caption',{class:'sr-only'},'Una fila por cliente. El detalle muestra todas sus recomendaciones.'),h('thead',{},h('tr',{},...[['Cliente','Cliente'],['Señal','Qué ocurre: recomendación para revisar'],['Acción','Siguiente paso propuesto'],['Resp.','Responsable del siguiente paso'],['Abrir','Abrir todas las recomendaciones del cliente']].map(([t,full])=>h('th',{scope:'col',title:full,'aria-label':full},t)))),cuerpo))]:[vacioLinea(pendiente?'Leyendo fuentes; las propuestas disponibles se mostrarán aquí.':'No hay recomendaciones en las fuentes disponibles de este filtro. Revisa también los datos pendientes; esto no confirma que todo esté resuelto.')]));

    }
    const enCurso=new Set();
    async function cargar(id){
      if(!vigente()||!fuentesEstado.isConnected||enCurso.has(id)||!Object.hasOwn(fuentes,id))return;
      enCurso.add(id);
      const fuente=fuentes[id];
      fuente.estado='cargando';pintar();
      try{
        const resultado=await ctx.api(fuente.ruta);
        if(!vigente()||!fuentesEstado.isConnected)return;
        if(id==='operativo')datos=resultado;
        if(id==='metodo')metodoDatos=resultado;
        if(id==='seo')seoDatos=resultado;
        fuente.estado='lista';
      }catch{
        if(!vigente()||!fuentesEstado.isConnected)return;
        fuente.estado='error';
      }finally{enCurso.delete(id);}
      if(vigente())pintar();
    }
    pintar();
    await Promise.allSettled(Object.keys(fuentes).map(cargar));
  }
};
