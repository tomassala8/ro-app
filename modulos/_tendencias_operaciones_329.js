//329: puro, sin GET/DOM. El caller revalida autorización real∩vista y alcance.
export const METRICAS329=Object.freeze([
 ['pend48','Clientes +48 h sin respuesta','clientes','sube'],
 ['rojas','Alarmas en rojo','alarmas','sube'],
 ['imputacion','% horas imputadas','porcentaje','baja'],
 ['revision48','Tareas en revisión +48 h','tareas','sube'],
 ['nota_accounts','Nota media de accounts','nota_0_100','baja'],
 ['semaforo_sin','Semáforos sin rellenar','clientes','sube'],
 ['rastro','Acciones con rastro (acumulado)','acciones','baja'],
]);
const hash=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
const diaValido=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T00:00:00Z'))&&new Date(x+'T00:00:00Z').toISOString().slice(0,10)===x;
const instante=x=>{
 if(typeof x!=='string')return null;
 const m=/^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|[+-](\d{2}):(\d{2}))$/.exec(x);
 if(!m||!diaValido(m[1])||+m[2]>23||+m[3]>59||+m[4]>59||(m[5]&&(+m[5]>14||+m[6]>59||(+m[5]===14&&+m[6]!==0))))return null;
 const d=Date.parse(x);return Number.isFinite(d)?d:null;
};
const desconocido=(id,motivo)=>({id,actual:null,anterior:null,delta:null,direccion:'sin_comparacion',estado:'desconocido',motivo});
// Contrato separado de272.1. NO añadir estos descriptores a una foto heredada.
export function compararMediciones329(anterior,actual,{scopeHash,ahora}={}){
 const id=actual?.id,regla=METRICAS329.find(x=>x[0]===id),now=instante(ahora);
 const no=motivo=>desconocido(typeof id==='string'?id:null,motivo);
 if(!regla||!hash(scopeHash)||now===null)return no('Contrato o ámbito no acreditados.');
 const valido=m=>{
   if(!m||m.version!=='329.1'||m.id!==id||m.validado_servidor!==true||m.origen!=='medicion_copia'||m.scope_hash!==scopeHash||!hash(m.cohorte_hash)||!hash(m.definicion_hash)||m.unidad!==regla[2]||typeof m.completa!=='boolean')return false;
   const corte=instante(m.corte),leido=instante(m.leido),v=m.valor;
   if(corte===null||leido===null||corte>leido||leido>now||typeof v!=='number'||!Number.isFinite(v)||v<0||(['porcentaje','nota_0_100'].includes(m.unidad)?v>100:!Number.isSafeInteger(v)))return false;
   const p=m.periodo;
   if(!p||p.tipo!=='stock'||Object.keys(p).length!==1)return false;
   return true;
 };
 if(!valido(anterior)||!valido(actual))return no('Falta definición, unidad, corte o población medida compatible.');
 if(anterior.cohorte_hash!==actual.cohorte_hash||anterior.definicion_hash!==actual.definicion_hash||anterior.completa!==actual.completa)return no('Cambió la población medida, definición o cobertura.');
 if(instante(anterior.corte)>=instante(actual.corte))return no('Los cortes no son dos mediciones sucesivas.');
 const delta=actual.valor-anterior.valor;
 if(!Number.isFinite(delta))return no('Variación fuera de rango.');
 return {id,actual:actual.valor,anterior:anterior.valor,delta,direccion:delta===0?'igual':delta>0?'sube':'baja',
   estado:'comparacion_observada',motivo:'Comparación de mediciones de copia; no acredita ejecución ni cumplimiento.',
   parcial:!actual.completa,cortes:{anterior:anterior.corte,actual:actual.corte},unidad:actual.unidad,
   // El sentido del original es referencia, no un semáforo de desempeño personal.
   referencia_desfavorable:regla[3]};
}

//272 sólo autoriza referencias: no contiene cohorte/unidad/ventana por métrica.
export function tendenciasFotos329(dto,{scopeHash,actorId,ahora}={}){
 const now=instante(ahora),permitido=now!==null&&hash(scopeHash)&&typeof actorId==='string'&&actorId&&dto?.version==='272.1'&&Array.isArray(dto.registros);
 const rows=METRICAS329.map(([id,etiqueta])=>({...desconocido(id,'Las fotos actuales no acreditan población medida, unidad y periodo comparables.'),etiqueta,referencias:[]}));
 const medidas=new Map(METRICAS329.map(([id])=>[id,[]]));
 if(!permitido)return rows;
 const counts=new Map();for(const r of dto.registros)if(typeof r?.objeto==='string')counts.set(r.objeto,(counts.get(r.objeto)||0)+1);
 for(const f of dto.registros){
   const fecha=instante(f?.registrado_en);
   if(f?.tipo!=='foto'||f.scope_hash!==scopeHash||f.registrado_por!==actorId||counts.get(f.objeto)!==1||fecha===null||fecha>now||f.cumplimiento!==null||f.exhaustiva!==false||!Array.isArray(f.metricas)||f.metricas.length!==7)continue;
   if(!METRICAS329.every(([id,et],i)=>f.metricas[i]?.id===id&&f.metricas[i]?.etiqueta===et))continue;
   for(let i=0;i<rows.length;i++){
     const m=f.metricas[i],v=m.valor;
     if(m.estado!=='observado_copia'||!['rojas','revision48'].includes(m.id)||!Number.isSafeInteger(v)||v<0)continue;
     // Un sello sin zona se conserva literalmente, nunca se convierte aUTC.
     const s=m.fecha_fuente;
     if(typeof s!=='string'||!/^\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?$/.test(s)||!diaValido(s.slice(0,10))||!Number.isFinite(Date.parse(s.replace(' ','T')))||s.slice(0,10)>ahora.slice(0,10)||(instante(s)!==null&&instante(s)>fecha))continue;
     rows[i].referencias.push({valor:v,fecha_fuente:s,guardada_en:f.registrado_en,comparable:false});
     const ms=Array.isArray(f.mediciones_329)?f.mediciones_329.filter(x=>x?.id===m.id):[];
     if(ms.length===1&&ms[0].valor===v&&ms[0].scope_hash===scopeHash&&instante(ms[0].leido)!==null&&instante(ms[0].leido)<=fecha&&instante(ms[0].corte)!==null&&s===ms[0].corte)medidas.get(m.id).push(ms[0]);
   }
 }
 for(const r of rows){
   r.referencias.sort((a,b)=>Date.parse(b.guardada_en)-Date.parse(a.guardada_en));
   const ms=medidas.get(r.id).sort((a,b)=>instante(b.corte)-instante(a.corte));
   if(ms.length>=2){
     Object.assign(r,compararMediciones329(ms[1],ms[0],{scopeHash,ahora}));
     if(r.estado==='comparacion_observada'){
       const cuentas=new Map();for(const m of ms)cuentas.set(m.corte,(cuentas.get(m.corte)||0)+1);
       const compatibles=ms.slice(1).filter(m=>cuentas.get(m.corte)===1&&compararMediciones329(m,ms[0],{scopeHash,ahora}).estado==='comparacion_observada');
       r.serie=[...compatibles.slice(0,11).reverse(),ms[0]].map(m=>({valor:m.valor,corte:m.corte,leido:m.leido}));
     }
   }
 }
 return rows;
}
