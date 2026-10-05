// Explicación disponible a demanda; no altera datos, permisos ni acciones.
export function notaCompacta336(h,resumen,...contenido){
 return h('details',{class:'nota-compacta336',style:{fontSize:'12px',lineHeight:'1.4',border:'1px solid var(--linea,#e1e4f1)',borderRadius:'8px',padding:'0 10px',margin:'4px 0'}},
  h('summary',{style:{minHeight:'44px',display:'list-item',alignContent:'center',cursor:'pointer'},'aria-label':resumen},resumen),
  h('div',{role:'note',style:{padding:'0 0 8px',overflowWrap:'anywhere'}},...contenido));
}
