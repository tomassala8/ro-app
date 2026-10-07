// Orden del artifact, sobre ratios de referencia comparables ya autorizados.
// No carga fuentes, no amplía permisos ni considera la pauta presupuesto contractual.
const numero555=x=>typeof x==='number'&&Number.isFinite(x)&&x>=0;
const fecha555=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T00:00:00Z'))&&new Date(x+'T00:00:00Z').toISOString().slice(0,10)===x;
function sello555(x,hoy){
 if(typeof x!=='string'||!/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d{1,9})?)?(?:Z|[+-]\d{2}:\d{2})?$/.test(x)||!fecha555(x.slice(0,10))||x.slice(0,10)>hoy)return false;
 const t=/[T ](\d{2}):(\d{2})(?::(\d{2}))?/.exec(x),z=/([+-])(\d{2}):(\d{2})$/.exec(x);
 return +t[1]<24&&+t[2]<60&&+(t[3]||0)<60&&(!z||(+z[2]<=14&&+z[3]<60&&(+z[2]<14||+z[3]===0)))&&Number.isFinite(Date.parse(x.replace(' ','T')));
}
export function ordenarHorasCliente555(filas,rango,hoy){
 const originales=Array.isArray(filas)?filas.slice():[],sinOrden=detalle=>({filas:originales,ordenado:false,detalle});
 if(!fecha555(hoy)||!fecha555(rango?.desde)||!fecha555(rango?.hasta)||rango.desde>rango.hasta||rango.hasta>hoy||rango.desde.slice(0,7)!==rango.hasta.slice(0,7))return sinOrden('Orden de la fuente: rango no comparable.');
 const ids=originales.map(x=>x?.proyecto?.cliente_id);
 if(ids.some(x=>typeof x!=='string'||!x.trim())||new Set(ids).size!==ids.length)return sinOrden('Orden de la fuente: identidades ausentes o duplicadas; no se eliminan filas.');
 const claves=originales.map((fila,i)=>{
  const m=fila.medicion,p=fila.pauta,periodo=rango.desde.slice(0,7);
  if((m?.unidad!==undefined&&m.unidad!=='h')||(p?.unidad!==undefined&&p.unidad!=='h')||fila.autorizada!==true||!numero555(m?.valor)||m.parcial!==true||m.periodo!==periodo||!sello555(m.fecha,hoy)||typeof m.fuente!=='string'||!m.fuente.trim()||
    !p||p.origen!=='referencia_economica'||p.presupuesto_confirmado!==false||p.cobertura!=='parcial'||p.periodo!==periodo||!numero555(p.horas)||p.horas<=0||!sello555(p.fecha,hoy)||typeof p.fuente!=='string'||!p.fuente.trim()||!numero555(p.mensual_ref)||p.mensual_ref<=0||!Number.isSafeInteger(p.laborables)||p.laborables<=0)return {fila,i,clave:null};
  let laborables=0;const d=new Date(rango.desde+'T00:00:00Z'),fin=new Date(rango.hasta+'T00:00:00Z');for(;d<=fin;d.setUTCDate(d.getUTCDate()+1))if(d.getUTCDay()>0&&d.getUTCDay()<6)laborables++;
  const esperado=p.mensual_ref*laborables/21,ratio=m.valor/p.horas*100;
  if(laborables!==p.laborables||!numero555(esperado)||esperado!==p.horas||!numero555(ratio)||ratio!==p.porcentaje)return {fila,i,clave:null};
  return {fila,i,clave:ratio,firma:JSON.stringify([rango.desde,rango.hasta,periodo,m.fecha,m.fuente,'h',m.parcial,p.fecha,p.fuente,p.cobertura,p.origen,p.presupuesto_confirmado,laborables,'pauta_mensual_por_laborables_dividido_21'])};
 });
 const conocidas=claves.filter(x=>x.clave!==null);
 if(!conocidas.length)return sinOrden('Orden de la fuente: sin ratios observados y pautas compatibles autorizadas.');
 if(new Set(conocidas.map(x=>x.firma)).size!==1)return sinOrden('Orden de la fuente: cortes, fuentes o cobertura diferentes; no se comparan ratios.');
 return {filas:claves.sort((a,b)=>a.clave===null?(b.clave===null?a.i-b.i:1):b.clave===null?-1:b.clave-a.clave||a.i-b.i).map(x=>x.fila),ordenado:true,detalle:'Mayor → menor porcentaje observado de referencia del mismo rango y fuentes; sin dato al final. Copia parcial, no capacidad ni cumplimiento contractual.'};
}

// El mínimo observado nunca se redondea por encima del dato original.
export function porcentajeMinimo555(x){
 if(!numero555(x))return '—';
 if(x>0&&x<0.1)return '≥'+String(x).replace('.',',')+' %';
 let minimo=x>Number.MAX_VALUE/10?x:Math.floor(x*10)/10;
 if(minimo>x)minimo=Math.max(0,minimo-0.1);
 return '≥'+new Intl.NumberFormat('es-ES',{maximumFractionDigits:1}).format(minimo)+' %';
}
