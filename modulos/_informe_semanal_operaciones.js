// Borrador local del informe original: texto editable, sin envío, persistencia ni evaluación automática.
const diaIS=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T00:00:00Z'))&&new Date(x+'T00:00:00Z').toISOString().slice(0,10)===x;
const textoIS=x=>typeof x==='string'?x.split(/[\r\n]+/).filter(l=>!/(?:password|contrase[ñn]a|bearer|api[_ -]?key|guest_link|start_url|(?:token|secret)\s*[:=]|\b\d[\d., ]*\s*(?:€|EUR\b|euros\b))/i.test(l)).join(' ').replace(/https?:\/\/\S+|\b[^\s@]+@[^\s@]+\.[^\s@]+\b/g,'[dato reservado]').replace(/\+?\d[\d ()-]{7,}\d/g,'[contacto reservado]').trim().slice(0,500):'';
const numIS=x=>typeof x==='number'&&Number.isFinite(x)&&x>=0;
const valorIS=(x,periodo)=>{
 const v=x?.valor;const limpio=typeof v==='string'?textoIS(v):numIS(v)?String(v):'';
 if(!limpio||!/^\d/.test(limpio)||/[€@]|reservado/.test(limpio))return 'Sin dato confirmado';
 const primera=Number(/^\d+(?:[.,]\d+)?/.exec(limpio)?.[0]?.replace(',','.'));
 const m=x?.medicion;
 const ceroMedido=m?.estado==='medido'&&typeof m.fuente==='string'&&textoIS(m.fuente)&&m.desde===periodo?.desde&&m.hasta===periodo?.hasta&&diaIS(m.fecha?.slice(0,10))&&m.fecha.slice(0,10)>=periodo.hasta&&m.fecha.slice(0,10)<=periodo.hoy;
 return primera===0&&!ceroMedido?'Sin dato confirmado (cero sin medición acreditada)':limpio;
};
export function periodoInformeSemanalOperaciones(informe,hoy,corte){
 const m=/^(\d{4}-\d{2}-\d{2})\s*→\s*(\d{4}-\d{2}-\d{2})$/.exec(informe?.semana||'');
 if(!m||!diaIS(hoy)||!diaIS(corte)||!diaIS(m[1])||!diaIS(m[2])||m[1]>m[2]||m[2]>hoy||corte<m[1]||corte>m[2])return null;
 return {desde:m[1],hasta:m[2],corte,hoy};
}
export function textoInformeSemanalOperaciones(ctx,m,fuentes={}){
 const informe=fuentes.direccion?.informe_semanal,p=periodoInformeSemanalOperaciones(informe,ctx.hoy,m.corte);
 const base=Array.isArray(informe?.numeros)?informe.numeros:[];
 const numero=(nombre)=>{const xs=base.filter(x=>x?.nombre===nombre);return p&&xs.length===1?`${valorIS(xs[0],p)} · fuente: ${textoIS(xs[0].fuente)||'copia autorizada de dirección'}`:'Sin dato confirmado; falta ventana/fuente compatible';};
 const current=Array.isArray(ctx.clientesVisibles)?ctx.clientesVisibles:[],ids=new Map();for(const c of current)if(c?.activo_confirmado===true&&c.detalle!==false)ids.set(c.id,(ids.get(c.id)||0)+1);
 const cliOK=id=>typeof id==='string'&&ids.get(id)===1&&ctx.ver?.({tipo:'cliente_detalle',cliente_id:id})?.ok===true;
 const cliNombre=id=>textoIS(current.find(c=>c.id===id)?.nombre)||id;
 const rojos=(Array.isArray(m.rojos)?m.rojos:[]).filter(r=>cliOK(r.cliente_id));
 const registros=(Array.isArray(m.registro)?m.registro:[]).filter(r=>(!r.cliente_id||cliOK(r.cliente_id))&&p&&diaIS(r.creada?.slice(0,10))&&r.creada.slice(0,10)>=p.desde&&r.creada.slice(0,10)<=p.hasta);
 const decisiones=(Array.isArray(m.decisiones)?m.decisiones:[]).filter(d=>!d.respondida&&(!d.cliente_id||cliOK(d.cliente_id))&&diaIS(d.creada?.slice(0,10))&&d.creada.slice(0,10)<=ctx.hoy);
 const lineas=[`Semana ${p?`${p.desde} → ${p.hasta}`:'por confirmar'} · Operaciones`,
  `Borrador para revisión. ${p?`Corte de la copia: ${p.corte}; cobertura parcial.`:'Periodo y fecha de fuente pendientes.'} Los registros no prueban ejecución ni envío.`,
  `1. Altas en plazo: ${numero('Altas en plazo (encendidas el día 10, límite 12)')}.`,
  `2. Horas por cuenta nueva: ${numero('Horas por cuenta nueva (media al mes)')}.`,
  `3. Compromisos vencidos sin aviso: ${numero('Compromisos vencidos sin aviso')}.`,
  'Horas imputadas (% de capacidad): Sin dato confirmado. Informes enviados del periodo: Sin dato confirmado. Nota media de accounts: Sin dato confirmado.',
  'Clientes con +48 h sin respuesta y revisión +48 h: consultar las observaciones de Bandeja / Producción; comparación semanal sin dato confirmado.',
  `Clientes críticos observados en la cartera: ${rojos.length?rojos.map(r=>cliNombre(r.cliente_id)).join(', '):'Sin registros compatibles; no acredita ausencia'}. Plan y visto de Coti: consultar Fuegos; sin comprobar en esta copia.`,
  `Declaraciones con rastro en la semana: ${p&&registros.length?'≥'+registros.length:'Sin dato confirmado'}; no acredita tareas ejecutadas.`,
  `Decisiones pendientes observadas para revisión: ${decisiones.length?decisiones.slice(0,4).map(d=>textoIS(d.texto)||textoIS(d.titulo)||'Consultar decisión autorizada').join(' · '):'Sin registros compatibles; no acredita que no haya decisiones'}.`];
 return lineas.join('\n');
}
export function panelInformeSemanalOperaciones({h,ctx,modelo,fuentes,vigente}){
 const sello=()=>JSON.stringify([ctx.real?.id,ctx.persona?.id,(ctx.clientesVisibles||[]).map(c=>[c.id,c.activo_confirmado,c.detalle,ctx.ver?.({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true]).sort()]);
 const initial=sello();const ok=()=>area.isConnected===true&&vigente()&&ctx.veModulo?.('decisiones')&&sello()===initial;
 const area=h('textarea',{'aria-label':'Informe semanal',rows:'10',maxlength:'12000',style:{width:'100%',boxSizing:'border-box',font:'inherit',fontSize:'13px',lineHeight:'1.5',minHeight:'210px',padding:'12px',border:'1px solid var(--linea,#d9dce5)',borderRadius:'8px',background:'var(--papel,#fff)',color:'inherit',resize:'vertical'}});
 area.value=textoInformeSemanalOperaciones(ctx,modelo,fuentes);
 const status=h('span',{role:'status','aria-live':'polite',style:{fontSize:'12px'}});
 const copiar=h('button',{type:'button',class:'bt',on:{click:async()=>{
  if(!ok()){area.value='';status.textContent='La sesión o la cartera ha cambiado. Vuelve a abrir el informe.';return;}
  try{await navigator.clipboard.writeText(area.value);if(ok())status.textContent='Copiado.';}
  catch{if(ok()){area.focus();area.select();status.textContent='Selecciona el texto y cópialo con ⌘C o Ctrl+C.';}}
 }}},'Copiar');
 return h('details',{'data-informe-semanal':'editable',style:{marginTop:'8px'}},h('summary',{style:{cursor:'pointer',minHeight:'44px',display:'flex',alignItems:'center',padding:'0 20px',fontWeight:'600',fontSize:'13px'}},'Editar y copiar el informe semanal'),
  h('div',{style:{display:'grid',gap:'12px',padding:'8px 20px 16px'}},h('label',{style:{display:'grid',gap:'8px',fontSize:'13px'}},'Informe semanal · borrador editable',area),h('div',{style:{display:'flex',gap:'10px',alignItems:'center'}},copiar,status),h('small',{},'Edición local. Copiar no envía el informe ni guarda los cambios.')));
}
