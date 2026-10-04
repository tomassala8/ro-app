// Agregados de observaciones autorizadas. Nunca interpreta importes ni deriva presupuestos/capacidad.
const arr=x=>Array.isArray(x)?x:[];
const activo=p=>p?.estado==='activo'&&p.activo!==false;
const id=x=>typeof x==='string'&&/^[a-zA-Z0-9_-]{1,200}$/.test(x);
const dia=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T00:00Z'))&&new Date(x+'T00:00Z').toISOString().slice(0,10)===x;
const mes=x=>typeof x==='string'&&/^\d{4}-(0[1-9]|1[0-2])$/.test(x);
const num=x=>typeof x==='number'&&Number.isFinite(x)&&x>=0;
const roles=(a,b)=>Array.isArray(a)&&Array.isArray(b)&&a.length>0&&a.every(id)&&b.every(id)&&new Set(a).size===a.length&&new Set(b).size===b.length&&JSON.stringify([...a].sort())===JSON.stringify([...b].sort());
const sello=(x,hoy)=>{if(typeof x!=='string'||!/^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?)?$/.test(x)||!dia(x.slice(0,10))||x.slice(0,10)>hoy)return null;const hora=/[T ](\d{2}):(\d{2})(?::(\d{2}))?/.exec(x);if(hora&&(+hora[1]>23||+hora[2]>59||+(hora[3]||0)>59))return null;return Number.isFinite(Date.parse(x.length===10?x+'T00:00Z':x.replace(' ','T')))?x:null;};
const formato=x=>new Intl.NumberFormat('es-ES',{maximumFractionDigits:1}).format(x);
function ambito349(ctx,rows){try{
 const ps=arr(ctx.datos?.personas),actores=[ctx.real,ctx.persona],cs=arr(ctx.clientesVisibles);
 if(ctx.vigente?.()===false||!ctx.servidor||!dia(ctx.hoy)||typeof ctx.ver!=='function'||!Array.isArray(rows)||!actores.every(p=>id(p?.id)&&activo(p)&&ps.filter(x=>x?.id===p.id).length===1&&ps.some(x=>x.id===p.id&&activo(x)&&roles(p.puestos,x.puestos))&&p.puestos.some(r=>['account','operaciones','direccion'].includes(r))))return null;
 const ids=rows.map(r=>r?.cliente_id),propia=ctx.persona.puestos.includes('account')&&!ctx.persona.puestos.some(r=>['operaciones','direccion'].includes(r)),cartera=new Set(ctx.carteraPorSilla?.account||[]);
 if(new Set(ids).size!==ids.length||!ids.every(cid=>id(cid)&&cs.filter(c=>c?.id===cid).length===1&&cs.some(c=>c.id===cid&&c.activo_confirmado===true&&c.detalle===true)&&(!propia||cartera.has(cid))&&ctx.ver({tipo:'cliente_detalle',cliente_id:cid})?.ok===true))return null;
 const pautaIds=ctx.real.id===ctx.persona.id&&ctx.veModulo?.('dinero-cliente')?ids.filter(cid=>ctx.ver({tipo:'horas_pautadas',cliente_id:cid})?.ok===true):[];
 return {ids,pautaIds,horas:ctx.veModulo?.('produccion')===true,firma:JSON.stringify([actores.map(p=>[p.id,p.estado,p.activo,p.puestos]),ctx.hoy,ids,pautaIds,ctx.veModulo?.('produccion')===true,ctx.veModulo?.('dinero-cliente')===true,ps.map(p=>[p.id,p.estado,p.activo,p.puestos]),[...cartera].sort(),ids.map(cid=>{const c=cs.find(c=>c.id===cid);return [c.id,c.activo_confirmado,c.detalle];})])};
 }catch{return null;}}
function huellaFuente349(rows,scope){return JSON.stringify(arr(rows).map(r=>{const h=scope.horas?r?.horas:null,p=scope.pautaIds.includes(r?.cliente_id)?r?.pauta_horas:null;return [r?.cliente_id,h?.fuente,h?.fecha,h?.medicion?.total,h?.medicion?.periodo,p?.horas,p?.periodo,p?.fecha,p?.fuente,p?.origen,p?.cobertura,p?.presupuesto_confirmado];}));}
const desconocido=detalle=>({valor:'—',estado:'gris',detalle,total:null,medidos:0});
export function agregarHorasCartera349(ctx,rows){
 const scope=ambito349(ctx,rows),N=arr(rows).length;
 if(!scope)return {horas:desconocido('Ámbito actual sin acreditar; no se suma información de clientes ajenos o ambiguos.'),referencia:desconocido('Referencia no disponible en el ámbito actual.')};
 const token={ambito349:scope.firma,fuente349:huellaFuente349(rows,scope)};
 function sumar(xs,tipo,ancla=null){
  if(!xs.length)return {...desconocido(tipo==='horas'?'Sin horas registradas con descriptor acreditado; copias positivas o ceros heredados no se agregan.':'Sin pauta mensual autorizada compatible; no equivale a cero ni presupuesto contractual.'),...token};
  const periodos=new Set(xs.map(x=>x.periodo)),cortes=new Set(xs.map(x=>x.fecha));
  if(periodos.size!==1||cortes.size!==1||(ancla&&xs[0].periodo!==ancla))return {...desconocido('Sin agregado: los registros no comparten mes/corte compatible. Se conservan por cliente; no se mezclan periodos.'),...token};
  const total=xs.reduce((s,x)=>s+x.horas,0);if(!Number.isFinite(total))return {...desconocido('Total numérico fuera de rango; no se presenta una cifra.'),...token};
  const periodo=xs[0].periodo,fecha=xs[0].fecha,medidos=xs.length;
  return {valor:`${tipo==='horas'?'≥':''}${formato(total)} h ${tipo==='horas'?'registradas':'de referencia'} · ${periodo} · ${medidos}/${N} clientes`,estado:'gris',total,medidos,clientes:N,periodo,fecha,...token,
   detalle:`${tipo==='horas'?'Suma mínima de observaciones de horas acreditadas':'Suma de referencias horarias ya autorizadas'} del mes ${periodo}, lectura ${fecha}. ${medidos}/${N} clientes con valor compatible; el resto desconocido. Copia parcial incluso con todos los clientes presentes. ${tipo==='horas'?'Cero explícito sólo acredita lo observado en esos registros; no ausencia de trabajo.':'No es presupuesto aprobado, cuota agregada ni capacidad contractual.'} No calcula porcentaje ni desviación ni declara cumplimiento.`};
 }
 const horas=scope.horas?rows.flatMap(r=>{const h=r.horas,m=h?.medicion,fecha=sello(h?.fecha,ctx.hoy);return h?.fuente==='ClickUp · horas'&&fecha&&num(m?.total)&&mes(m?.periodo)&&m.periodo<=ctx.hoy.slice(0,7)&&m.periodo<=fecha.slice(0,7)?[{horas:m.total,periodo:m.periodo,fecha}]:[];}):[];
 const h=sumar(horas,'horas');
 const refs=rows.flatMap(r=>{const p=r.pauta_horas,fecha=sello(p?.fecha,ctx.hoy);return scope.pautaIds.includes(r.cliente_id)&&p?.fuente==='Pauta mensual · copia autorizada'&&p.origen==='referencia_economica'&&p.presupuesto_confirmado===false&&p.cobertura==='parcial'&&fecha&&num(p.horas)&&mes(p.periodo)&&p.periodo<=ctx.hoy.slice(0,7)&&p.periodo<=fecha.slice(0,7)?[{horas:p.horas,periodo:p.periodo,fecha}]:[];});
 const referencia=horas.length&&!h.periodo?{...desconocido('Horas de meses/cortes incompatibles: no se agrupa una pauta para compararlas.'),...token}:sumar(refs,'referencia',h.periodo||null);
 return {horas:h,referencia};
}
export function celdaHorasCarteraVigente349(ctx,rows,c){const a=ambito349(ctx,rows);return !c?.ambito349?c?.total===null:!!a&&a.firma===c.ambito349&&huellaFuente349(rows,a)===c.fuente349;}
