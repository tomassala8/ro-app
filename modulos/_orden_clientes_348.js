// Sólo claves tipadas de las filas autorizadas. No interpreta etiquetas, pautas ni puntuaciones históricas.
export const COLUMNAS_ORDEN_348=Object.freeze({0:'cliente',1:'riesgo',4:'espera',5:'registro',7:'horas',8:'tickets'});
const dia=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T00:00Z'))&&new Date(x+'T00:00Z').toISOString().slice(0,10)===x;
const mes=x=>typeof x==='string'&&/^\d{4}-(0[1-9]|1[0-2])$/.test(x);
const sello=(x,hoy)=>typeof x==='string'&&dia(x.slice(0,10))&&x.slice(0,10)<=hoy&&Number.isFinite(Date.parse(x.length===10?x+'T00:00Z':x.replace(' ','T')))?x:null;
const num=x=>typeof x==='number'&&Number.isFinite(x)&&x>=0;
const texto=x=>typeof x==='string'&&x.trim()?x.trim():null;
const collator=new Intl.Collator('es',{sensitivity:'base',numeric:true});
export function clavesClientes348(rows,hoy){
 const fs=Array.isArray(rows)?rows:[];if(!dia(hoy))return fs.map(()=>({}));
 const keys=fs.map(r=>{
  const ticket=r?.tickets,horas=r?.horas,reg=r?.reunion_historica,espera=r?.espera?.medicion;
  const tf=sello(ticket?.fecha,hoy),hf=sello(horas?.fecha,hoy),rf=sello(reg?.fecha,hoy),hm=horas?.medicion;
  return {cliente:texto(r?.nombre),riesgo:({rojo:3,ambar:2,verde:1})[r?.g?.estado]??null,
   tickets:ticket?.fuente==='Desk'&&tf&&Number.isSafeInteger(ticket?.medicion?.total)&&ticket.medicion.total>=0?ticket.medicion.total:null,
   espera:espera?.fuente==='Desk'&&espera.fecha===tf&&tf&&num(espera.dias_laborables)?espera.dias_laborables:null,
   registro:rf&&dia(reg?.fecha_registro)&&reg.fecha_registro<=rf.slice(0,10)&&reg.fecha_registro<=hoy&&mes(reg.periodo_fuente)&&reg.periodo_fuente<=hoy.slice(0,7)?reg.fecha_registro:null,
   horas:horas?.fuente==='ClickUp · horas'&&hf&&num(hm?.total)&&mes(hm.periodo)&&hm.periodo<=hoy.slice(0,7)?hm.total:null,
   periodo_horas:hm?.periodo,corte_tickets:tf};
 });
 // No compara stocks de cortes distintos ni horas mensuales de meses diferentes.
 for(const [key,campo] of [['tickets','corte_tickets'],['espera','corte_tickets'],['horas','periodo_horas']]){
  const periodos=new Set(keys.filter(k=>k[key]!==null).map(k=>k[campo]));if(periodos.size>1)for(const k of keys)k[key]=null;
 }
 return keys;
}
export function disponibilidadOrden348(rows,hoy){const ks=clavesClientes348(rows,hoy);return Object.fromEntries(Object.values(COLUMNAS_ORDEN_348).map(key=>[key,ks.some(k=>k[key]!=null)]));}
export function siguienteOrden348(actual,key){if(!Object.values(COLUMNAS_ORDEN_348).includes(key))return actual;return {key,direccion:actual?.key===key&&actual.direccion==='asc'?'desc':actual?.key===key?'asc':key==='cliente'?'asc':'desc'};}
export function ordenarClientes348(rows,hoy,orden={key:'riesgo',direccion:'desc'}){
 const fs=Array.isArray(rows)?rows:[],key=Object.values(COLUMNAS_ORDEN_348).includes(orden?.key)?orden.key:'riesgo',dir=orden?.direccion==='asc'?1:-1,keys=clavesClientes348(fs,hoy);
 return fs.map((row,i)=>({row,key:keys[i][key]??null})).sort((a,b)=>{
  if(a.key===null&&b.key!==null)return 1;if(b.key===null&&a.key!==null)return -1;
  const c=a.key===null?0:typeof a.key==='string'?collator.compare(a.key,b.key):a.key-b.key;
  return c*dir||collator.compare(texto(a.row?.nombre)||'',texto(b.row?.nombre)||'')||collator.compare(String(a.row?.cliente_id||''),String(b.row?.cliente_id||''));
 }).map(x=>x.row);
}
