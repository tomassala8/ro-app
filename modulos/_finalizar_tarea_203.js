// Final de flujo tipado en su lista; nunca aceptación del entregable ni nombre supuesto.
export function destinosFinales203(t,permiso,resolver) {
  if(!permiso?.ok || !Array.isArray(permiso.destinos))return {ok:false,destinos:[],motivo:permiso?.motivo || 'No se confirmó permiso para cambiar esta tarea.'};
  const destinos=[...new Set(permiso.destinos)].filter(e=>{
    const r=resolver(t,e,true);
    return r?.estado==='verificado' && (r.tipo==='done' || r.tipo==='closed') && r.final_flujo===true;
  });
  return destinos.length?{ok:true,destinos,motivo:'Estado final de esta lista; no acredita entrega aceptada.'}:{ok:false,destinos:[],motivo:'No hay un destino final tipado y verificado en esta lista. Consulta ClickUp.'};
}
