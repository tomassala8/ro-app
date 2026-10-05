// Orden visual del artifact: observaciones del mismo rango, nunca capacidad ni evaluación.
const fecha447=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T00:00:00Z'))&&new Date(x+'T00:00:00Z').toISOString().slice(0,10)===x;
const rango447=r=>fecha447(r?.desde)&&fecha447(r?.hasta)&&r.desde<=r.hasta;
export function ordenarHorasArtifact447(filas,rango){
 if(!Array.isArray(filas))return [];
 const clave=f=>rango447(rango)&&rango447(f?.rango)&&f.rango.desde===rango.desde&&f.rango.hasta===rango.hasta&&
 ['observado_diario','observado_historial_90d'].includes(f?.medicion?.tipo)&&typeof f.medicion.valor==='number'&&Number.isFinite(f.medicion.valor)&&f.medicion.valor>=0?f.medicion.valor:null;
 return filas.map((fila,i)=>({fila,i,valor:clave(fila)})).sort((a,b)=>a.valor===null?(b.valor===null?a.i-b.i:1):b.valor===null?-1:a.valor-b.valor||a.i-b.i).map(x=>x.fila);
}
