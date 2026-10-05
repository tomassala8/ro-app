//539 · orden original por observaciones compatibles, no jornada ni desempeño.
const dia=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T00:00:00Z'))&&new Date(x+'T00:00:00Z').toISOString().slice(0,10)===x;
const numero=x=>typeof x==='number'&&Number.isFinite(x)&&x>=0;
export function ordenarEquipoDia539(filas,fechas,hoy){
 if(!Array.isArray(filas))return [];
 const ventana=Array.isArray(fechas)&&fechas.length===5&&fechas.every(dia)&&new Set(fechas).size===5&&fechas.every((f,i)=>f<hoy&&(!i||f>fechas[i-1]))&&dia(hoy);
 const counts=new Map();for(const f of filas)counts.set(f?.persona?.persona_id,(counts.get(f?.persona?.persona_id)||0)+1);
 const xs=filas.map((fila,i)=>{
  const s=fila?.serie,pid=fila?.persona?.persona_id;let ultimo=null,suma=null,firma=null;
  if(ventana&&typeof pid==='string'&&counts.get(pid)===1&&s?.zona==='Europe/Madrid'&&(!s.persona_id||s.persona_id===pid)&&Array.isArray(s.dias)&&typeof s.fecha_fuente==='string'){
   const stamp=Date.parse(s.fecha_fuente.replace(' ','T')),aware=/(?:Z|[+-]\d{2}:\d{2})$/.test(s.fecha_fuente),leido=aware&&Number.isFinite(stamp)?new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(stamp)):s.fecha_fuente.slice(0,10);
   if(Number.isFinite(stamp)&&dia(leido)&&leido<=hoy&&fechas.at(-1)<leido){
    const valores=fechas.map(fecha=>{const ds=s.dias.filter(d=>d?.fecha===fecha);return ds.length===1&&ds[0].estado==='observado'&&numero(ds[0].horas)&&Number.isSafeInteger(ds[0].entradas)&&ds[0].entradas>0?ds[0].horas:null;});
    ultimo=valores.at(-1);const total=valores.every(numero)?valores.reduce((a,b)=>a+b,0):null;suma=numero(total)?total:null;
    firma=JSON.stringify([s.zona,s.fecha_fuente,fechas]);
   }
  }
  return {fila,i,ultimo,suma,firma};
 });
 // No comparar cortes distintos como si formaran una misma clasificación.
 const firmas=new Set(xs.filter(x=>x.ultimo!==null).map(x=>x.firma));if(firmas.size>1)return filas.slice();
 return xs.sort((a,b)=>a.ultimo===null?(b.ultimo===null?a.i-b.i:1):b.ultimo===null?-1:a.ultimo-b.ultimo||(a.suma===null?(b.suma===null?a.i-b.i:1):b.suma===null?-1:a.suma-b.suma||a.i-b.i)).map(x=>x.fila);
}
