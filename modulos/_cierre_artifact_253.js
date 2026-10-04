// Cierre por account: disposición de vCierre del artifact original.
// Entrada ya autorizada. Nunca comparar dos meses distintos ni deducir asistencia.
const num=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0;
const f=v=>v===null?'—':new Intl.NumberFormat('es-ES',{maximumFractionDigits:1}).format(v);
// Un mínimo parcial no debe redondearse hacia arriba. Sin soporte floor,
// mostrar la representación exacta del número; nunca volver al redondeo normal.
const fMin553=v=>{
  if(!num(v))return '—';
  if(v>0&&v<0.1)return String(v).replace('.',',');
  const formato=new Intl.NumberFormat('es-ES',{maximumFractionDigits:1,roundingMode:'floor'});
  return formato.resolvedOptions().roundingMode==='floor'?formato.format(v):String(v).replace('.',',');
};
export function prepararCierre253(d,clientes=[]){
  const ids=new Map();for(const c of clientes)if(c?.id&&c.activo_confirmado===true)ids.set(c.id,(ids.get(c.id)||0)+1);
  const repetidos=new Map();for(const r of d?.clientes||[])if(r?.cliente_id)repetidos.set(r.cliente_id,(repetidos.get(r.cliente_id)||0)+1);
  const mes=d?.mes_horas,clave=mes==='2026-09'?'sep':mes==='2026-10'?'oct':null;
  return (d?.clientes||[]).filter(r=>ids.get(r.cliente_id)===1&&repetidos.get(r.cliente_id)===1).map(r=>{
    // Legacy zero does not prove full measurement. Positive values are observed, partial.
    const v=clave?r.coste_horas?.[clave]:null,reales=num(v)&&v>0?v:null;
    const p=d.mes_cuota===mes?r.cuota_horas?.pautadas:null,pautadas=num(p)&&p>0?p:null;
    const hist=r.historico_267;
    const valido=mes==='2026-09'&&hist?.version==='267.1'&&hist.periodo===mes&&hist.cobertura==='parcial'&&hist.verificacion_externa===false&&hist.cumplimiento===null&&hist.no_evalua_garantia===true&&hist.sha256_candidato==='4afc61a142faadf9631141c3a33109712cfd9ecfdf832a99e469731e970f5bc2';
    const llamadas=valido&&hist.fuente_llamadas==='zadarma_cache_historica'&&Number.isInteger(hist.llamadas30)&&hist.llamadas30>0?hist.llamadas30:null;
    const reuniones=valido&&hist.fuente_reuniones==='verificacion_manual_anterior_ID_exacto'&&Number.isInteger(hist.reuniones_verificadas_historicas)&&hist.reuniones_verificadas_historicas>0?hist.reuniones_verificadas_historicas:null;
    const porcentaje=reales!==null&&pautadas!==null?reales/pautadas*100:null;
    return {cliente_id:r.cliente_id,nombre:r.nombre,account_id:r.account_id||null,account:r.account||'Account por confirmar',reales,pautadas,pct:num(porcentaje)?porcentaje:null,llamadas,reuniones};
  });
}
// Subtotales de las filas ya autorizadas; la comparación usa sólo los mismos clientes.
export function resumenCierre361(filas){
  if(!Array.isArray(filas)||filas.some(r=>!r||typeof r.cliente_id!=='string')||new Set(filas.map(r=>r.cliente_id)).size!==filas.length)return null;
  const medidas=filas.filter(r=>num(r.reales)&&r.reales>0),pautas=filas.filter(r=>num(r.pautadas)&&r.pautadas>0),pares=filas.filter(r=>num(r.reales)&&r.reales>0&&num(r.pautadas)&&r.pautadas>0);
  const suma=(xs,k)=>xs.length?xs.reduce((s,r)=>s+r[k],0):null;
  const reales=suma(medidas,'reales'),pautadas=suma(pautas,'pautadas'),a=suma(pares,'reales'),b=suma(pares,'pautadas');
  if([reales,pautadas,a,b].some(v=>v!==null&&!Number.isFinite(v)))return null;
  const ratio=a!==null&&b>0?a/b*100:null;
  return {clientes:filas.length,medidos:medidas.length,pautados:pautas.length,comparables:pares.length,reales,pautadas,referencia_reales:a,referencia_pautadas:b,ratio:num(ratio)?ratio:null};
}
export function pintarCierre253({h,d,clientes,verdad,nombre,veFicha=false}){
  const rows=prepararCierre253(d,clientes),grupos=new Map();
  for(const r of rows){const k=r.account_id||'__sin';if(!grupos.has(k))grupos.set(k,[]);grupos.get(k).push(r);}
  const cont=h('div',{class:'cierre253 pila','data-cierre-artifact':'253'});
  cont.append(h('style',{},`.cierre253 .c253{background:white;border:1px solid #e1e4f1;border-radius:14px;overflow:hidden}.cierre253 header{display:flex;flex-wrap:wrap;gap:8px;justify-content:space-between;padding:14px 18px;border-bottom:1px solid #eceef7}.cierre253 h2{margin:0;font-size:15px;font-weight:600}.cierre253 .scroll253{overflow:auto}.cierre253 table{border-collapse:collapse;width:100%;min-width:760px;font-size:13px;font-variant-numeric:tabular-nums}.cierre253 th{font-size:10.5px;text-transform:uppercase;color:#777d9b;text-align:left;letter-spacing:.04em;padding:10px 12px;white-space:normal}.cierre253 td{padding:6px 12px;border-top:1px solid #eceef7}.cierre253 th:first-child,.cierre253 td:first-child{position:sticky;left:0;z-index:1;background:#fff}.cierre253 .num{text-align:right}.cierre253 .totales361{display:flex;flex-wrap:wrap;gap:4px 14px;align-items:center;font-size:12px}.cierre253 .totales361 small{color:#777d9b;font-size:11px}.cierre253 .ratio361{font-weight:600}.cierre253 .ratio361.rojo{color:#a92626}.cierre253 a{color:inherit;font-weight:600}.cierre253 .sem253{display:inline-block;padding:4px 8px;border-radius:6px;font-size:12px;font-weight:600;background:#eceef7;color:#464b68}.cierre253 .sem253.verde{background:#e5f4e9;color:#21643b}.cierre253 .sem253.ambar{background:#fff3d6;color:#7a5200}.cierre253 .sem253.rojo{background:#fcebeb;color:#a92626}.cierre253 .nota253{font-size:12px;color:#777d9b}`),
    h('p',{class:'sub'},`Horas registradas de ${d?.mes_horas||'periodo sin confirmar'}. La pauta disponible corresponde a ${d?.mes_cuota||'periodo sin confirmar'}; sólo se compara si coincide el mes. Reuniones y llamadas requieren verificación histórica. La copia de horas es parcial. % es una referencia de horas observadas / pauta del mismo mes, no cumplimiento. ≥ indica mínimo observado; — indica dato sin acreditar.`));
  for(const [id,fs] of grupos){
    const resumen=resumenCierre361(fs);
    cont.append(h('section',{class:'c253'},h('header',{},h('h2',{},id==='__sin'?'Account por confirmar':nombre?.(id)||fs[0].account),h('div',{class:'totales361','data-cierre-resumen':'361'},
        h('span',{},`${resumen?.reales!==null&&resumen?.reales!==undefined?'≥'+fMin553(resumen.reales):'—'} h observadas`,h('small',{},` · ${resumen?.medidos??0}/${fs.length} clientes`)),
        h('span',{},`${f(resumen?.pautadas??null)} h pautadas`,h('small',{},` · ${resumen?.pautados??0}/${fs.length} clientes`)),
        resumen?.ratio!==null&&resumen?.ratio!==undefined?h('span',{class:'ratio361'+(resumen.ratio>130?' rojo':''),title:`Sólo ${resumen.comparables}/${fs.length} clientes con ambas cifras del mismo mes: ≥${fMin553(resumen.referencia_reales)} h observadas / ${f(resumen.referencia_pautadas)} h pautadas. Copia parcial; no acredita bajo consumo ni cumplimiento. Más de130% supera la referencia histórica.`},`≥${fMin553(resumen.ratio)} % ref. · ${resumen.comparables}/${fs.length} comparables`):h('span',{class:'nota253'},'Sin comparación del mismo mes'))),
      h('div',{class:'scroll253',tabindex:'0','aria-label':'Cierre mensual por cliente'},h('table',{},h('thead',{},h('tr',{},...['Cliente','Pautadas','Reales','%','Semáforo actual','Reuniones del mes','Llamadas ≥30 s'].map(t=>h('th',{scope:'col'},t)))),h('tbody',{},...fs.map(r=>{
        const v=verdad?.(r.cliente_id),refs=[v?.id,v?.cliente_id].filter(x=>x!=null),valid=refs.length>0&&refs.every(x=>x===r.cliente_id),sem=valid?({critico:'Crítico',atencion:'Vigilar',bien:'Bien'}[v.gravedad]||'—'):'—';
        return h('tr',{},
          h('td',{},veFicha?h('a',{href:`#/ficha/${encodeURIComponent(r.cliente_id)}/resumen`},r.nombre):r.nombre),
          h('td',{class:'num',title:r.pautadas===null?'Pauta del mismo mes no acreditada':null,'aria-label':r.pautadas===null?'Horas pautadas: sin referencia del mismo mes':null},f(r.pautadas)),
          h('td',{class:'num',title:r.reales===null?'Horas observadas: sin medición acreditada; no equivale a cero':null,'aria-label':r.reales===null?'Horas observadas: sin dato':null},f(r.reales)),
          h('td',{class:'num',title:r.pct===null?'Sin comparación de horas observadas y pauta del mismo mes':null,'aria-label':r.pct===null?'Porcentaje: sin comparación del mismo mes':null},r.pct===null?'—':h('span',{class:'ratio361'+(r.pct>130?' rojo':''),title:'Horas observadas de copia parcial / pauta del mismo mes. Por encima de130% supera la referencia histórica; un mínimo bajo no acredita déficit ni cumplimiento.'},'≥'+fMin553(r.pct)+' %')),
          h('td',{},h('span',{class:'sem253 '+(valid?({critico:'rojo',atencion:'ambar',bien:'verde'}[v.gravedad]||'gris'):'gris'),title:sem==='—'?'Semáforo actual por confirmar':null,'aria-label':sem==='—'?'Semáforo actual: por confirmar':null},sem)),
          h('td',{class:'num',title:r.reuniones===null?'Reuniones del mes: evidencia histórica por verificar; no acredita asistencia ni cumplimiento':'Registros manuales históricos ligados por ID de tarea. Asistencia y cumplimiento sin verificar.','aria-label':r.reuniones===null?'Reuniones del mes: evidencia por verificar':null},r.reuniones===null?'—':`≥${r.reuniones}`),
          h('td',{class:'num',title:r.llamadas===null?'Llamadas registradas de al menos30 segundos: sin evidencia histórica acreditada':'Llamadas registradas ≥30 s de septiembre, enlazadas al catálogo histórico. Cobertura parcial; titular actual sin confirmar.','aria-label':r.llamadas===null?'Llamadas de al menos30 segundos: sin dato':null},r.llamadas===null?'—':`≥${r.llamadas}`));
      }))))));
  }
  if(!rows.length)cont.append(h('p',{},'No hay clientes activos autorizados con datos para este cierre.'));
  return cont;
}
