// Sólo presentación de la referencia leída; no calcula ni evalúa KPIs.
export function pintarNumerosSemanales449(h,filas,{vigente=()=>false,semana=''}={}){
 const root=h('div',{'data-numeros-semanales-449':'compacto'}),vivo=()=>root.isConnected&&vigente()===true;
 const tx=x=>typeof x==='string'?x:'',valor=x=>typeof x==='number'&&Number.isFinite(x)?String(x):typeof x==='string'&&x.trim()?x:'—';
 const limpiar=()=>root.replaceChildren();
 if(vigente()!==true)return root;
 root.append(h('p',{class:'sub'},[tx(semana)||'Semana sin confirmar','Referencia histórica; no acredita cumplimiento'].join(' · ')),
  h('table',{class:'densa'},h('thead',{},h('tr',{},['Indicador','Valor','Detalle'].map(t=>h('th',{scope:'col'},t)))),
   h('tbody',{},(Array.isArray(filas)?filas:[]).map(r=>{
    const etiqueta=tx(r?.etiqueta)||'Indicador sin nombre',v=valor(r?.valor),info=h('div',{});
    const details=h('details',{on:{toggle:()=>{
     if(!vivo()){limpiar();return;}info.replaceChildren();if(!details.open)return;
     info.append(h('p',{class:'sub'},'Criterio original: '+(tx(r?.referencia)||'Sin criterio confirmado.')),
      h('p',{class:'sub'},'Fuente: '+(tx(r?.detalle)||'Sin ventana y evidencia suficiente.')));
    }}},h('summary',{'aria-label':'Fuente y criterio de '+etiqueta,style:{minHeight:'44px',display:'flex',alignItems:'center',cursor:'pointer'}},'Ver'),info);
    return h('tr',{},h('td',{},etiqueta),h('td',{title:v==='—'?'Sin dato confirmado: no equivale a cero.':v+' · referencia histórica leída; no acredita cumplimiento','aria-label':etiqueta+': '+(v==='—'?'sin dato confirmado':v+'; referencia histórica')},v),h('td',{},details));
   }))));return root;
}
