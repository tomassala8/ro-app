//448 · agregados de campañas recibidas; jamás métricas de cuenta ni conversión CRM.
const propio=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const dia=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T00:00Z'))&&new Date(x+'T00:00Z').toISOString().slice(0,10)===x;
function instante(x){if(typeof x!=='string')return null;const m=/^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(Z|[+-](\d{2}):(\d{2}))$/.exec(x);if(!m||!dia(m[1])||+m[2]>23||+m[3]>59||+m[4]>59||(m[5]!=='Z'&&(+m[6]>14||+m[7]>59||(+m[6]===14&&+m[7]!==0))))return null;const n=Date.parse(x);return Number.isFinite(n)?n:null;}
const numero=(x,entero)=>x===null||typeof x==='number'&&Number.isFinite(x)&&x>=0&&(!entero||Number.isSafeInteger(x));
function sumar(rs,k,entero){if(rs.some(r=>r[k]===null))return null;const n=rs.reduce((v,r)=>v+r[k],0);return Number.isFinite(n)&&(!entero||Number.isSafeInteger(n))?n:null;}
export function metricasCampanas448(dto,ahora=Date.now()){try{
 const m=dto?.medicion,p=m?.periodo,lectura=instante(m?.fecha_fuente);
 if(dto?.version!=='385.1'||dto.estado!=='copia_observada'||m?.version!=='384.1'||m.cliente_id!==dto.cliente_id||m.nivel!=='campaign_diario'||m.cobertura!=='filas_recibidas_no_censo'||!dia(p?.desde)||!dia(p?.hasta)||p.desde>p.hasta||lectura===null||!Number.isFinite(ahora)||lectura>ahora||typeof m.paginas_completas!=='boolean'||!Array.isArray(m.errores_tipados)||!Array.isArray(m.dias))return null;
 const corteLocal=new Intl.DateTimeFormat('sv-SE',{timeZone:p.zona,year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(lectura));
 if(typeof p.zona!=='string'||p.hasta>=corteLocal)return null;
 const n=(Date.parse(p.hasta)-Date.parse(p.desde))/864e5+1,gasto=propio(m,'gasto_observado');
 if(n<1||n>366||m.dias.length!==n||gasto&&(!numero(m.gasto_observado,false)||!/^[A-Z]{3}$/.test(m.moneda)))return null;
 for(let i=0;i<n;i++){
  const r=m.dias[i],esperado=new Date(Date.parse(p.desde)+i*864e5).toISOString().slice(0,10);
  if(r?.dia!==esperado||!Number.isSafeInteger(r.filas_recibidas)||r.filas_recibidas<0||!numero(r.impresiones_observadas,true)||!numero(r.clics_observados,true)||gasto&&!numero(r.gasto_observado,false))return null;
  if(r.filas_recibidas===0&&[r.impresiones_observadas,r.clics_observados,...(gasto?[r.gasto_observado]:[])].some(v=>v!==null))return null;
 }
 const impresiones=sumar(m.dias,'impresiones_observadas',true),clics=sumar(m.dias,'clics_observados',true),importe=gasto?sumar(m.dias,'gasto_observado',false):null;
 if(gasto&&(importe===null)!==(m.gasto_observado===null)||gasto&&importe!==null&&Math.abs(importe-m.gasto_observado)>1e-8*Math.max(1,importe))return null;
 const ctr=impresiones>0&&clics!==null?100*clics/impresiones:null,cpm=impresiones>0&&importe!==null?1000*importe/impresiones:null;
 return {impresiones,clics,ctr:ctr===null||Number.isFinite(ctr)?ctr:null,gasto:importe,cpm:cpm===null||Number.isFinite(cpm)?cpm:null,permiteImporte:gasto,moneda:gasto?m.moneda:null,periodo:{...p},fecha:m.fecha_fuente,parcial:!m.paginas_completas||m.errores_tipados.length>0,cobertura:m.cobertura};
 }catch{return null;}}
