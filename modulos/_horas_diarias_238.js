const fecha = v => typeof v==='string' && /^\d{4}-\d{2}-\d{2}$/.test(v) && Number.isFinite(Date.parse(v+'T00:00:00Z')) && new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v;
export function serieHorasDiaria238(persona, hoy) {
  const s=persona?.diario_238;
  if(!fecha(hoy)||!['238.1','238.2'].includes(s?.version)||s.fuente!=='ClickUp entradas'||s.cobertura!=='parcial'||s.zona_confirmada!==true||typeof s.zona!=='string'||typeof s.fecha_fuente!=='string')return null;
  const origen=s.fecha_fuente.slice(0,10);
  if(!fecha(origen)||origen>hoy||!Number.isFinite(Date.parse(s.fecha_fuente.replace(' ','T'))))return null;
  try{new Intl.DateTimeFormat('es-ES',{timeZone:s.zona});}catch{return null;}
  const longitud=s.version==='238.2'?7:5;
  if(s.version==='238.2'&&(s.corte_fecha!==hoy||s.criterio_corte!=='anterior_fecha_referencia'))return null;
  const dias=Array.from({length:longitud},(_,i)=>new Date(Date.parse(hoy+'T00:00:00Z')-(longitud-i)*864e5).toISOString().slice(0,10));
  if(s.desde!==dias[0]||s.hasta!==dias.at(-1)||!Array.isArray(s.dias)||s.dias.length!==longitud)return null;
  for(let i=0;i<longitud;i++){
    const d=s.dias[i];if(!d||d.fecha!==dias[i])return null;
    if(d.estado==='observado'){
      if(typeof d.horas!=='number'||!Number.isFinite(d.horas)||d.horas<0||!Number.isSafeInteger(d.entradas)||d.entradas<1)return null;
    }else if(d.estado!=='sin_dato'||d.horas!==null||d.entradas!==null)return null;
  }
  return {dias:s.dias,zona:s.zona,fecha_fuente:s.fecha_fuente};
}
export function matrizHorasDiaria238(personas, hoy) {
  const ps=Array.isArray(personas)?personas:[],counts=new Map();for(const p of ps)counts.set(p?.persona_id,(counts.get(p?.persona_id)||0)+1);
  const filas=ps.filter(p=>typeof p?.persona_id==='string'&&counts.get(p.persona_id)===1).map(p=>({persona_id:p.persona_id,nombre:p.nombre||p.alias||p.persona_id,serie:serieHorasDiaria238(p,hoy)}));
  const primera=filas.find(p=>p.serie);
  return primera?{fechas:primera.serie.dias.map(d=>d.fecha),filas}:null;
}
