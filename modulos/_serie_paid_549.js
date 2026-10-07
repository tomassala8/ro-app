// Observaciones de la copia; cobertura de días no es exhaustividad del proveedor.
const count=v=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=0?v:null;
const amount=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0?v:null;
const id=v=>typeof v==='string'&&/^[A-Za-z0-9_-]{1,120}$/.test(v);
const day=v=>{if(typeof v!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(v))return null;const t=Date.parse(v+'T12:00:00Z');return Number.isFinite(t)&&new Date(t).toISOString().slice(0,10)===v?t:null;};
export function fechaPaid549(v){
 if(typeof v!=='string')return null;const m=/^(\d{4}-\d{2}-\d{2})(?:[T ]([01]\d|2[0-3]):([0-5]\d)(?::([0-5]\d)(?:\.\d{1,6})?)?(?:Z|[+-](\d{2}):(\d{2}))?)?$/.exec(v);
 if(!m||day(m[1])===null||m[5]&&(+m[5]>14||+m[6]>59||+m[5]===14&&+m[6]!==0))return null;
 if(m[2]&&/(Z|[+-]\d{2}:\d{2})$/.test(v)&&Date.parse(v.replace(' ','T'))>Date.now())return null;
 if(m[2]&&!/(Z|[+-]\d{2}:\d{2})$/.test(v)){const f=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}),a=Object.fromEntries(f.formatToParts(new Date()).map(p=>[p.type,p.value]));if(`${m[1]}T${m[2]}:${m[3]}`>`${a.year}-${a.month}-${a.day}T${a.hour}:${a.minute}`)return null;}
 return m[1];
}
const error=c=>!!c?.error||!!c?.errores?.length||!!c?.errores_lectura?.length||!!c?.cuenta_meta?.error||!!c?.cuenta_meta?.errores?.length;
const events=new Set(['lead','onsite_conversion.lead_grouped','offsite_conversion.fb_pixel_lead','onsite_web_lead']);
export function sumaSeriePaid549(filas,desde,hasta,hoy,corte){
 const a=day(desde),b=day(hasta),now=day(hoy),cut=day(corte),empty={leads:null,gasto:null,moneda:null,gastoCompleto:false,completo:false,tipado:false,firma:null,desde,hasta,dias_observados:0,dias_esperados:null,cobertura:'observaciones_parciales_no_exhaustivas'};
 if(a===null||b===null||now===null||a>b||b-a>365*864e5||!Array.isArray(filas))return empty;
 const cs=filas.filter(c=>c?.tipo_negocio!=='tienda_online'&&c?.tienda_online!==true),expected=((b-a)/864e5+1)*cs.length;
 let n=null,g=null,moneda=null,observados=0,complete=cs.length>0&&cut!==null&&b<=cut&&cut<now,typed=true,moneyValid=true;const signature=[],seen=new Set(),freq=new Map(),accountClients=new Map();for(const c of cs){freq.set(c?.cliente_id,(freq.get(c?.cliente_id)||0)+1);for(const uid of new Set((Array.isArray(c?.serie)?c.serie:[]).map(r=>r?.medicion?.cuenta_id).filter(v=>typeof v==='string'&&/^[1-9][0-9]{0,29}$/.test(v)))){if(!accountClients.has(uid))accountClients.set(uid,new Set());accountClients.get(uid).add(c?.cliente_id);}}let moneyComplete=cs.length>0;
 for(const c of cs){
  if(!id(c?.cliente_id)||seen.has(c.cliente_id)||freq.get(c.cliente_id)!==1||(Array.isArray(c.serie)?c.serie:[]).some(r=>accountClients.get(r?.medicion?.cuenta_id)?.size>1)||error(c)){complete=false;typed=false;moneyComplete=false;continue;}seen.add(c.cliente_id);
  const rs=Array.isArray(c.serie)?c.serie:[],sig={id:c.cliente_id,cuenta:null,tipo:null,moneda:null};
  for(let t=a;t<=b;t+=864e5){
   const d=new Date(t).toISOString().slice(0,10),xs=rs.filter(x=>x?.d===d);
   if(xs.length!==1||t>=now||cut!==null&&t>cut||error(xs[0])){complete=false;typed=false;moneyComplete=false;continue;}
   const x=xs[0],v=count(x.leads_meta),m=x.medicion;
   const read=fechaPaid549(m?.fecha_lectura);if(m&&(!read||read<d||read>hoy)){complete=false;typed=false;moneyComplete=false;continue;}
   if(v===null){complete=false;typed=false;}else{n=(n??0)+v;observados++;}
   const stamp=fechaPaid549(m?.fecha_lectura),unit=m?.tipo_lead;
   if(v===null||m?.version!=='220.1'||m.fuente!=='meta_insights'||m.nivel!=='account'||m.periodo_valido!==true||m.desde!==d||m.hasta!==d||m.cohorte!=='resultados_meta_sin_union_crm_ni_cualificacion_ro'||!events.has(unit)||!Array.isArray(m.campos_observados)||!m.campos_observados.includes('leads')||!stamp||stamp<d||stamp>hoy||typeof m.cuenta_id!=='string'||!/^[1-9][0-9]{0,29}$/.test(m.cuenta_id)||typeof m.moneda!=='string'||!/^[A-Z]{3}$/.test(m.moneda)||sig.cuenta!==null&&sig.cuenta!==m.cuenta_id||sig.tipo!==null&&sig.tipo!==unit||sig.moneda!==null&&sig.moneda!==m.moneda)typed=false;
   else{sig.cuenta=m.cuenta_id;sig.tipo=unit;sig.moneda=m.moneda;}
   // No leer dinero de una cuenta cuya concesión fue eliminada del DTO.
   if(c.dinero===true){const value=amount(x.gasto_meta),currency=c.cuenta_meta?.moneda;
    if(value===null)moneyComplete=false;if(value!==null){if(typeof currency!=='string'||!/^[A-Z]{3}$/.test(currency)||m?.moneda!==undefined&&m.moneda!==currency||moneda!==null&&moneda!==currency)moneyValid=false;else{moneda=currency;g=(g??0)+value;}}
   }else moneyComplete=false;
  }
  signature.push(sig);
 }
 if(new Set(signature.map(s=>s.tipo)).size>1)typed=false;if(count(n)===null)n=null;if(amount(g)===null||!moneyValid){g=null;moneda=null;}
 return {...empty,leads:n,gasto:g,moneda,gastoCompleto:complete&&moneyComplete&&g!==null,completo:complete&&observados===expected&&n!==null,tipado:typed&&n!==null,firma:typed&&n!==null?JSON.stringify(signature.sort((x,y)=>x.id.localeCompare(y.id))):null,dias_observados:observados,dias_esperados:expected};
}
export function compararSeriesPaid549(actual,anterior){
 if(!actual?.completo||!anterior?.completo||!actual.tipado||!anterior.tipado||actual.firma!==anterior.firma||count(actual.leads)===null||count(anterior.leads)===null||anterior.leads===0)return null;
 const a=day(actual.desde),b=day(actual.hasta),p=day(anterior.desde),q=day(anterior.hasta);
 if([a,b,p,q].some(t=>t===null)||b-a!==q-p||a-q!==864e5)return null;const v=(actual.leads-anterior.leads)/anterior.leads*100;return Number.isFinite(v)?v:null;
}
//554 · céntimos truncados sobre el valor binario exacto: nunca elevar un mínimo.
export function minimoGastoPaid554(v){
 if(amount(v)===null)return null;
 const buffer=new ArrayBuffer(8),bits=new DataView(buffer);bits.setFloat64(0,v,false);
 const high=bits.getUint32(0,false),low=bits.getUint32(4,false),exp=(high>>>20)&2047;
 const significando=(BigInt(high&0xfffff)<<32n)+BigInt(low)+(exp?1n<<52n:0n),power=exp?exp-1023-52:-1074;
 const scaled=significando*100n,centimos=power>=0?scaled<<BigInt(power):scaled>>BigInt(-power);
 const entero=(centimos/100n).toString().replace(/\B(?=(\d{3})+(?!\d))/g,'.');
 return `${entero},${(centimos%100n).toString().padStart(2,'0')}`;
}
