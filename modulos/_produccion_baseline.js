// Baseline visual vProduccion/vPlanificacion. Sólo copia autorizada; no llamadas ni acciones.
const entero=v=>Number.isSafeInteger(v)&&v>=0;
const fecha=(s,hoy)=>{if(typeof s!=='string'||typeof hoy!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(hoy)||!/^\d{4}-\d{2}-\d{2}/.test(s)||s.slice(0,10)>hoy)return false;const d=new Date(s.slice(0,10)+'T00:00:00Z');return !Number.isNaN(+d)&&d.toISOString().slice(0,10)===s.slice(0,10)&&!Number.isNaN(+new Date(s.replace(' ','T')));};
const desconocido=detalle=>({valor:null,referencia:false,detalle:detalle||'Sin medición específica disponible. No equivale a cero.'});
const hashes256=e=>['sha256_tareas','sha256_catalogo','sha256_candidato'].every(k=>typeof e[k]==='string'&&/^[a-f0-9]{64}$/.test(e[k]));
const calendario256=s=>{try{const ps=new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).formatToParts(new Date(s));return Object.fromEntries(ps.map(p=>[p.type,p.value]));}catch{return null;}};
const dia256=p=>p?`${p.year}-${p.month}-${p.day}`:null;
export function descriptorProduccion256(p,D) {
  const e=p?._evidencia_produccion_256;
  if(!e||e.version!=='256.1'||e.fuente!=='clickup_cache_local'||e.cliente_id!==p.cliente_id||e.zona!=='Europe/Madrid'||e.cobertura!=='parcial'||!hashes256(e)||!fecha(e.corte,D?.hoy)||!e.corte.endsWith('Z'))return null;
  if(!Array.isArray(D?.proyectos)||D.proyectos.filter(x=>x?.cliente_id===p.cliente_id).length!==1)return null;
  const cal=calendario256(e.corte),dia=dia256(cal),lun=dia?new Date(dia+'T00:00:00Z'):null;
  if(!lun)return null;lun.setUTCDate(lun.getUTCDate()-((lun.getUTCDay()+6)%7));
  if(dia>D.hoy||e.lunes!==lun.toISOString().slice(0,10)||e.mes!==dia.slice(0,7)||e.fecha_original!==`${dia} ${cal.hour}:${cal.minute}`||!e.metricas||typeof e.metricas!=='object')return null;
  return e;
}
export function metricaProduccion256(p,D,key) {
  const e=descriptorProduccion256(p,D);if(!e)return null;
  const base={...desconocido('Descriptor de métrica incompatible; no se revive la cifra heredada.'),mas48:null,cohorte:`256:${e.sha256_tareas}:${e.corte}:${key}`,fecha:e.corte};
  const m=e.metricas[key],snapshot=['account','tecnica','bloqueadas','cliente'].includes(key);
  if(['no_plan','sin_mes'].includes(key))return {...base,detalle:'La nueva copia no acredita estado inicial ni ausencia exhaustiva de tareas; no se restaura un indicador histórico como cumplimiento actual.'};
  if(!m||m.cobertura!=='parcial'||!entero(m.observaciones)||m.valor!==(m.observaciones?m.observaciones:null)||m.estado!==(m.observaciones?'observado_parcial':'sin_observaciones')||m.tipo!==(snapshot?'snapshot':'eventos_fechados'))return base;
  if(snapshot && m.mas48!==null)return base;
  if(!snapshot){
    const start=calendario256(m.desde),esperado=key==='creadas_mes'?e.mes+'-01':e.lunes;
    const campos={creadas_mes:'date_created',creadas_semana:'date_created',cerradas_semana:'date_done_or_closed+catalogo_actual_terminal'};
    if(!(key in campos)||m.campo!==campos[key]||m.hasta!==e.corte||!fecha(m.desde,D.hoy)||dia256(start)!==esperado||start.hour!=='00'||start.minute!=='00'||start.second!=='00'||new Date(m.desde)>new Date(e.corte))return base;
    base.cohorte+=`:${m.desde}:${m.hasta}`;
  }
  return {...base,valor:m.valor,observaciones:m.observaciones,detalle:`ClickUp · copia ${e.fecha_original} Europe/Madrid. ${snapshot?'Estado observado y catálogo exacto de lista; edad +48h no acreditada.':`Eventos ${m.campo} del ${m.desde} al ${m.hasta}.`} Cobertura parcial${m.valor===null?': sin observaciones no prueba ausencia':''}. No acredita entrega aceptada.`};
}
export function fuenteProduccionBaseline(proyectos,D){
  const fechas=[...new Set((Array.isArray(proyectos)?proyectos:[]).map(p=>descriptorProduccion256(p,D)?.fecha_original).filter(Boolean))];
  return fechas.length?`ClickUp: ${fechas.join(' · ')} Madrid · referencias anteriores: ${D?.fuentes?.flujo?.hora||'sin fecha'}`:`Copia de flujo · ${D?.fuentes?.flujo?.hora||'sin fecha'}`;
}
// Contrato emitido por generar_produccion: contadores y edades de UNA lectura de flujo.
export function revisionAccount633(p,D) {
  const m=p?.revisiones_account,s=m?.fecha;
  if(m?.estado!=='medido'||m.fuente!=='flujo'||typeof s!=='string'||s!==D?.fuentes?.flujo?.hora||!fecha(s,D?.hoy)||!entero(p.rev_account)||!entero(p.rev_account_48)||p.rev_account_48>p.rev_account)return null;
  const partes=s.match(/^\d{4}-\d{2}-\d{2}(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.\d{1,6})?)?(Z|[+-](\d{2}):(\d{2}))?)?$/);
  if(!partes||Number(partes[1]||0)>23||Number(partes[2]||0)>59||Number(partes[3]||0)>59||Number(partes[5]||0)>14||Number(partes[6]||0)>59||(Number(partes[5])===14&&Number(partes[6])!==0))return null;
  if(typeof p.cliente_id!=='string'||!p.cliente_id||!Array.isArray(D?.proyectos)||D.proyectos.filter(x=>x?.cliente_id===p.cliente_id).length!==1)return null;
  return {valor:p.rev_account,mas48:p.rev_account_48,referencia:false,fecha:s,cohorte:`legacy:${s}:account`,detalle:`Flujo · ${s}: revisión account y antigüedad >48 h de la misma lectura. Cobertura parcial; cero observado no acredita inventario exhaustivo ni entrega aprobada.`};
}
export function metricasProyectoBaseline(p,D) {
  const hoy=D?.hoy,flujo=D?.fuentes?.flujo?.hora;
  const referencia=campo=>fecha(flujo,hoy)&&entero(p?.[campo])&&p[campo]>0?{valor:p[campo],referencia:true,detalle:`Referencia heredada de la copia de flujo ${flujo}. Sin descriptor específico de periodo/cobertura; no es medición actual completa.`}:desconocido('El campo heredado puede contener un cero por defecto. Falta descriptor específico de periodo/cobertura.');
  const revision=tipo=>{
    if(tipo==='account'){const actual=revisionAccount633(p,D);if(actual)return actual;}
    const m=p?.['_revision_'+tipo];
    return m&&entero(m.n)&&entero(m.mas48)&&m.mas48<=m.n&&fecha(m.fecha,hoy)?{valor:m.n,mas48:m.mas48,referencia:false,detalle:`${m.fecha}: filas de revisión observadas, cobertura parcial.`}:tipo==='tecnica'?{...referencia('rev_tecnica'),mas48:entero(p?.rev_tecnica_48)&&p.rev_tecnica_48>0&&p.rev_tecnica_48<=p.rev_tecnica?p.rev_tecnica_48:null}:desconocido();
  };
  const rs=Array.isArray(D?.revisiones)?D.revisiones:[],ids=new Map();
  for(const r of rs)if(r?.id)ids.set(r.id,(ids.get(r.id)||0)+1);
  const bl=rs.filter(r=>r?.cliente_id===p.cliente_id && r.estado==='bloqueado' && ids.get(r.id)===1 && typeof r.dias==='number' && Number.isFinite(r.dias) && r.dias>=0 && typeof r.mas48==='boolean');
  const bloqueadas=fecha(D?.fuentes?.tareas?.hora,hoy)&&bl.length?{valor:bl.length,mas48:bl.filter(r=>r.mas48).length,referencia:false,detalle:`${D.fuentes.tareas.hora}: bloqueos visibles con ID único; no inventario exhaustivo.`}:desconocido('No hay bloqueos observados con evidencia suficiente en este ámbito. No acredita que no existan otros.');
  const legacy={account:revision('account'),tecnica:revision('tecnica'),bloqueadas,cliente:desconocido('La proyección no incluye revisión del cliente ni pendientes de envío como inventario acreditado.'),
    sin_mes:desconocido('El booleano heredado no acredita ausencia de tareas del mes.'),creadas_mes:referencia('creadas_mes'),creadas_semana:referencia('creadas_semana'),
    no_plan:referencia('no_planificadas'),cerradas_semana:referencia('cerradas_semana')};
  for(const key of Object.keys(legacy)){const typed=metricaProduccion256(p,D,key);if(typed)legacy[key]=typed;else legacy[key].cohorte=`legacy:${['account','tecnica'].includes(key)?p?.['_revision_'+key]?.fecha||flujo:key==='bloqueadas'?D?.fuentes?.tareas?.hora:flujo}:${key}`;}
  return legacy;
}
export function sumarMetricaBaseline(ms,total,campo='valor') {
  const cohortes=new Set(ms.map(m=>m?.cohorte).filter(Boolean));
  if(cohortes.size>1)return {...desconocido('Fuentes o ventanas distintas: consulta el proyecto; no se suman estos periodos.'),medidos:0,total};
  const conocidos=ms.filter(m=>entero(m?.[campo])),valor=conocidos.reduce((s,m)=>s+m[campo],0);
  return {valor:conocidos.length&&entero(valor)?valor:null,medidos:conocidos.length,total,cohorte:cohortes.size===1?[...cohortes][0]:null,referencia:conocidos.some(m=>m.referencia),
    detalle:`${conocidos.length}/${total} proyectos con dato disponible. ${conocidos.some(m=>m.referencia)?'Incluye referencias heredadas sin periodo específico acreditado.':'Suma de la copia parcial; no acredita inventario completo.'}`};
}
export function planificacionBaseline(D,personas) {
  const c=D?.no_planificado_cobertura,counts=new Map();
  for(const p of Array.isArray(personas)?personas:[])if(p?.id)counts.set(p.id,(counts.get(p.id)||0)+1);
  const hoy=D?.hoy,sello=c?.fecha;
  const dia=fecha(sello,hoy)?sello.slice(0,10):null;
  const lunes=dia?new Date(dia+'T00:00:00Z'):null;
  if(lunes)lunes.setUTCDate(lunes.getUTCDate()-((lunes.getUTCDay()+6)%7));
  const valido=c?.estado==='referencia_de_copia' && c.alcance==='filas_con_persona_id_explicito_unico' && lunes?.toISOString().slice(0,10)===D.lunes;
  const filas=Array.isArray(D?.no_planificado)?D.no_planificado:[],ids=new Map();for(const f of filas)if(f?.persona_id)ids.set(f.persona_id,(ids.get(f.persona_id)||0)+1);
  return {filas:valido?filas.filter(f=>counts.get(f?.persona_id)===1&&ids.get(f.persona_id)===1&&entero(f.creadas)&&entero(f.semana)&&f.semana<=f.creadas).map(f=>({...f,referencia:true,ejemplos:Array.isArray(f.ejemplos)?f.ejemplos.filter(e=>e&&typeof e.tarea==='string').map(e=>({tarea:e.tarea.slice(0,300)})):[]})):[],
    fecha:sello||null,lunes:D?.lunes||null,faltan_identidades:entero(c?.filas_sin_identidad)?c.filas_sin_identidad:null,
    detalle:valido?'Referencia de filas con identidad canónica en la copia; no acredita clasificación de todos los creadores.':'No hay planificación atribuible y con semana compatible en esta proyección. No permite concluir que nadie haya roto el semanal.'};
}
export const CSS_PRODUCCION_BASELINE=`
.prod-baseline .pb-panel{background:#fff;border:1px solid #e1e4f1;border-radius:14px;overflow:hidden;box-shadow:0 1px 2px rgba(16,19,43,.04),0 8px 24px -14px rgba(16,19,43,.16)}
.prod-baseline .pb-panel>header{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:6px 16px;padding:14px 18px;border-bottom:1px solid #eceef7}
.prod-baseline h2{margin:0;font-size:15px;font-weight:600;letter-spacing:-.015em}
.prod-baseline .pb-scroll{overflow-x:auto}.prod-baseline table.pb-table{border-collapse:collapse;width:100%;font-size:13px;min-width:960px;table-layout:fixed;font-variant-numeric:tabular-nums}
.prod-baseline .pb-table th{background:#f7f8fc;text-align:left;font-size:10.5px;font-weight:700;letter-spacing:.02em;line-height:1.25;text-transform:uppercase;color:#777d9b;padding:9px 12px;border-bottom:1px solid #e1e4f1;white-space:normal;overflow-wrap:normal}
.prod-baseline .pb-table td{padding:6px 12px;border-bottom:1px solid #eceef7;vertical-align:middle;white-space:normal;line-height:1.25}
.prod-baseline .pb-table th:first-child{width:140px}.prod-baseline .pb-table th:first-child,.prod-baseline .pb-table td:first-child{position:sticky;left:0;z-index:1;box-shadow:1px 0 #e1e4f1}.prod-baseline .pb-table td:first-child{background:#fff}.prod-baseline .pb-table th:first-child{z-index:2}.prod-baseline .pb-table tr:last-child td{border-bottom:0}.prod-baseline .pb-table .num{text-align:right}
.prod-baseline .pb-table small{display:block;font-size:11px;font-weight:400;color:#777d9b;margin-top:3px}
.prod-baseline .pb-table .pb-unknown{color:#777d9b;font-size:12px}.prod-baseline .pb-table .pb-reference{color:#464b68}
.prod-baseline .pb-table .pb-age{color:#7a5200;font-weight:600}
.prod-baseline .pb-cell{display:inline-block;border-radius:7px;padding:5px 7px;line-height:1.2;white-space:nowrap;background:#f4f5f8}
.prod-baseline .pb-cell-rojo{background:#fde6e9;color:#a1243d}
.prod-baseline .pb-cell-ambar{background:#fff2cc;color:#805500}
.prod-baseline .pb-table .pb-cell small{font-size:10px;margin-top:2px}
.prod-baseline .pb-link{all:unset;box-sizing:border-box;cursor:pointer;font:inherit;color:#3040b5;min-height:44px;display:inline-flex;align-items:center;font-weight:600}
.prod-baseline button:focus-visible{outline:2px solid #3040b5;outline-offset:2px;border-radius:6px}
.prod-baseline .pb-filtros{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;padding:12px 18px;border-bottom:1px solid #eceef7}
.prod-baseline .pb-filtros input,.prod-baseline .pb-filtros select{font:inherit;border:1px solid #e1e4f1;border-radius:8px;background:white;padding:5px 8px;min-height:44px;max-width:100%}
.prod-baseline .pb-nota{padding:10px 18px;font-size:12px;color:#777d9b;line-height:1.4}
`;
// Rangos visuales originales; no certifican cumplimiento ni inventario completo.
export function bandaProduccion409(m,clave,ambito) {
  if(!m||!entero(m.valor)||m.valor===0||m.referencia||typeof m.cohorte!=='string'||!/^(256:|legacy:)/.test(m.cohorte)||!['account','proyecto'].includes(ambito))return null;
  if(m.medidos!==undefined&&(!entero(m.medidos)||m.medidos===0||!entero(m.total)||m.medidos>m.total))return null;
  if(ambito==='account'){
    const bandas={account_48:[1,6],tecnica_48:[3,10],bloqueadas:[1,5],sin_mes:[1,2],no_plan:[3,8]};
    const b=bandas[clave];if(!b)return null;
    return m.valor>=b[1]?'rojo':m.valor>=b[0]?'ambar':null;
  }
  if(['account','tecnica','bloqueadas'].includes(clave)&&entero(m.mas48)&&m.mas48>0&&m.mas48<=m.valor)return 'rojo';
  if(clave==='no_plan'&&m.valor>=5)return 'ambar';
  return null;
}
// Construye la misma tabla simple de la referencia; llamadas/navegación siempre responsabilidad del caller.
export function tablaProduccionBaseline({h,titulo,sub,columnas,filas,alFila,vigente=()=>true,filtros=null,ambito=null}) {
  const cabecera=c=>{
    const nombres={'Bloqueadas':'Bloq.','En el cliente':'En cliente','Sin tareas este mes':'Sin tareas mes','Creadas semana':'Creadas sem.','No planificadas':'No planif.','Cerradas semana':'Cerradas sem.'};
    const edad=c.titulo==='+48 h'?({account_48:'Revisión account · +48 h',tecnica_48:'Revisión técnica · +48 h'})[c.clave]:null;
    return {visible:typeof c.titulo==='string'?(nombres[c.titulo]||c.titulo):c.titulo,completo:c.tituloCompleto||edad||(typeof c.titulo==='string'?c.titulo:undefined)};
  };

  const cell=(v,clave)=>{const m=v&&typeof v==='object'&&'valor'in v?v:null;
    if(!m)return v;
    const conocido=entero(m.valor),aviso=conocido&&!m.referencia&&entero(m.mas48)&&m.mas48>0&&m.mas48<=m.valor;
    const banda=ambito?bandaProduccion409(m,clave,ambito):aviso?'ambar':null;
    const cobertura=m.medidos!==undefined?`${m.medidos}/${m.total} proyectos con dato. `:'';
    const label=`${conocido?m.valor:'Sin dato'}. ${cobertura}${m.referencia?'Referencia de copia. ':''}${aviso?'Filas observadas con más de 48 horas: aviso de revisión; no certifica incumplimiento. ':''}${banda?'Color de referencia del artifact original; no certifica incumplimiento. ':''}${m.detalle||''}`;
    return h('span',{class:`pb-cell ${banda?`pb-cell-${banda} `:''}${!conocido?'pb-unknown':m.referencia?'pb-reference':''}`,title:label,'aria-label':label},
      conocido?new Intl.NumberFormat('es-ES',{maximumFractionDigits:1}).format(m.valor):'—',
      aviso?h('small',{class:'pb-age'},`${m.mas48} +48 h`):null);
  };
  return h('section',{class:'pb-panel'},h('header',{},h('h2',{},titulo),sub?h('span',{class:'sub'},sub):null),filtros,
    h('div',{class:'pb-scroll',role:'region','aria-label':titulo,tabindex:'0'},h('table',{class:'pb-table'},
      h('thead',{},h('tr',{},columnas.map(c=>{const cab=cabecera(c);return h('th',{scope:'col',class:c.num?'num':'',title:cab.completo,'aria-label':cab.completo},cab.visible);}))),
      h('tbody',{},filas.length?filas.map(f=>h('tr',{},columnas.map((c,i)=>h('td',{class:c.num?'num':''},i===0 && alFila?h('button',{type:'button',class:'pb-link','aria-label':`Ver ${String(c.valor(f))}`,on:{click:()=>{if(vigente())alFila(f);}}},c.valor(f)):cell(c.valor(f),c.clave))))):
        h('tr',{},h('td',{colspan:String(columnas.length),class:'pb-unknown'},'Sin filas acreditadas en esta proyección.'))))));
}
