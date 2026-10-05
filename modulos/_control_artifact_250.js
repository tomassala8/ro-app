// Presentación únicamente: el llamador entrega filas ya autorizadas y métricas acreditadas.
// Disposición de plantilla.html vControl960/CSS305–315 + override391–394.
export const COLUMNAS_CONTROL_250 = Object.freeze([
  {key:'imputa',titulo:'Imputa',sub:'horas · 7 días'},
  {key:'revisa',titulo:'Revisa',sub:'tareas +48 h'},
  {key:'llama',titulo:'Llama',sub:'salientes · 7 días'},
  {key:'contesta',titulo:'Contesta',sub:'pendientes +48 h'},
  {key:'reune',titulo:'Se reúne',sub:'registro del periodo'},
  {key:'contacto',titulo:'Contacto',sub:'esta semana'},
  {key:'abandonados',titulo:'Abandonados',sub:'evidencia por confirmar'},
  {key:'planifica',titulo:'Planifica',sub:'registro semanal'},
  {key:'tarde',titulo:'Reuniones tarde',sub:'horario registrado'}
]);
const texto = (v,max=400) => typeof v==='string'?v.slice(0,max):'';
const numero = v => typeof v==='number' && Number.isFinite(v) && v>=0;
export function celdaControl250(c) {
  const x=c && typeof c==='object'?c:{};
  const desconocido=['sin_dato','desconocido','unknown'].includes(x.estado);
  const valor=desconocido?null:numero(x.valor)?new Intl.NumberFormat('es-ES',{maximumFractionDigits:1}).format(x.valor):texto(x.valor,50).trim()||null;
  const observado=valor!==null && !['—','-','Sin dato'].includes(valor);
  // Sin umbral nuevo: sólo estados explícitos enviados por el adaptador de la fuente.
  const estado=observado && (['ambar','rojo'].includes(x.estado) || (x.estado==='verde' && x.cumplimiento_confirmado===true))?x.estado:'gris';
  const referencia=observado&&['rojo','ambar','verde'].includes(x.banda_referencia?.color)&&typeof x.banda_referencia?.detalle==='string'?x.banda_referencia.color:null;
  return {referencia,valor:observado?valor:'—',sub:observado?texto(x.sub,100):'Sin dato',estado,
    detalle:texto(x.detalle,4000) || (observado?'Dato observado en la copia autorizada.':'No hay evidencia suficiente disponible para este indicador.')};
}
const CSS_CONTROL_250 = `
.ro-control-artifact250{--c250-line:#e1e4f1;--c250-soft:#eceef7;--c250-mid:#464b68;--c250-dim:#777d9b;--c250-ink:#10132b;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--c250-ink);font-variant-numeric:tabular-nums;background:#fff;border:1px solid var(--c250-line);border-radius:14px;overflow:hidden;box-shadow:0 1px 2px rgba(16,19,43,.04),0 8px 24px -14px rgba(16,19,43,.16)}
.ro-control-artifact250>header{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:6px 16px;padding:14px 18px;border-bottom:1px solid var(--c250-soft)}
.ro-control-artifact250>header h2{margin:0;font-size:15px;font-weight:600;letter-spacing:-.015em}
.ro-control-artifact250 .ctl250{overflow-x:auto;padding:4px 14px 10px}
.ro-control-artifact250 .ctl250 table{border-collapse:separate;border-spacing:4px;width:100%;min-width:900px;font-size:12.5px;table-layout:fixed}
.ro-control-artifact250 .ctl250 th{font-size:10.5px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--c250-dim);text-align:center;padding:6px 4px;line-height:1.25;white-space:normal;word-break:normal}
.ro-control-artifact250 .ctl250 th small{display:block;font-weight:500;letter-spacing:0;text-transform:none;font-size:10.5px}
.ro-control-artifact250 .ctl250 th:first-child{text-align:left;width:142px}
.ro-control-artifact250 .ctl250 td{padding:0;vertical-align:middle;border:0}
.ro-control-artifact250 .ctl250 td.p250{font-weight:700;padding-right:10px}
.ro-control-artifact250 .p250 button{all:unset;box-sizing:border-box;cursor:pointer;min-height:44px;width:100%;font-size:12.5px;font-weight:700;line-height:1.2;overflow-wrap:anywhere}
.ro-control-artifact250 .p250 small{display:block;font-weight:500;color:var(--c250-dim);font-size:11.5px;margin-top:3px}
.ro-control-artifact250 .c250{all:unset;box-sizing:border-box;display:grid;place-items:center;width:100%;min-height:44px;border-radius:8px;font-weight:700;font-size:14px;cursor:pointer;background:var(--c250-soft);color:var(--c250-mid);text-align:center;line-height:1.1;padding:5px 3px;gap:3px}
.ro-control-artifact250 .c250 small{font-weight:600;font-size:10.5px;opacity:.85;line-height:1.15;overflow-wrap:anywhere}
.ro-control-artifact250 .c250.verde{background:#e5f4e9;color:#21643b}
.ro-control-artifact250 .c250.ambar{background:#fff3d6;color:#7a5200}
.ro-control-artifact250 .c250.rojo{background:#fcebeb;color:#a92626}
.ro-control-artifact250 .c250.ref390-rojo{background:#fcebeb;color:#a92626}.ro-control-artifact250 .c250.ref390-ambar{background:#fff3d6;color:#7a5200}.ro-control-artifact250 .c250.ref390-verde{background:#e5f4e9;color:#21643b}
.ro-control-artifact250 button:focus-visible{outline:2px solid #3040b5;outline-offset:2px;border-radius:8px}
.ro-control-artifact250 .detalle250{border-top:1px solid var(--c250-soft);padding:12px 18px;font-size:13px;white-space:pre-wrap;overflow-wrap:anywhere}
.ro-control-artifact250 .detalle250 p{margin:8px 0}
.ro-control-artifact250 .cerrar250{min-height:44px;border:1px solid var(--c250-line);border-radius:8px;background:white;font:inherit;color:var(--c250-mid);padding:5px 12px;cursor:pointer}
.ro-control-artifact250 .vacio250{padding:12px 18px;font-size:13px;color:var(--c250-dim)}
`;
export function pintarMapaControl250({h,filas=[],columnas=COLUMNAS_CONTROL_250,vigente=()=>true,celdaVigente=()=>true,alSeleccionar,alDetalle,titulo='Mapa de control por persona'}={}) {
  if(typeof h!=='function')throw new TypeError('Falta constructor de elementos');
  const claves=new Set(COLUMNAS_CONTROL_250.map(c=>c.key));
  const especificadas=new Map((Array.isArray(columnas)?columnas:[]).filter(c=>c && claves.has(c.key)).map(c=>[c.key,c]));
  // Siempre diez columnas, con orden fijo de la referencia. Sin catálogo ad hoc.
  const cols=COLUMNAS_CONTROL_250.map(c=>({...c,...especificadas.get(c.key),key:c.key}));
  const fs=vigente()!==false && Array.isArray(filas)?filas:[],ids=new Map();
  for(const f of fs)if(f && typeof f.id==='string' && f.id)ids.set(f.id,(ids.get(f.id)||0)+1);
  const rows=fs.filter(f=>f && ids.get(f.id)===1 && typeof f.nombre==='string');
  const frame=h('section',{class:'ro-control-artifact250','data-control-artifact':'250'});
  let detalle=null,origen=null,detalleCelda=null;
  const botones=[];
  const limpiarRevocadas=()=>{
    for(const {row,col,boton} of botones){
      if(celdaVigente(row,col.key)!==false)continue;
      boton.replaceChildren(h('span',{},'—'));boton.className='c250 gris';boton.setAttribute('aria-label',`${row.nombre} · ${texto(col.titulo)} · Sin dato`);
      if(detalleCelda?.row===row&&detalleCelda?.key===col.key){detalle?.remove();detalle=null;detalleCelda=null;}
    }
  };
  const vivo=()=>vigente()!==false && frame.isConnected;
  const cerrar=()=>{if(detalle){detalle.remove();detalle=null;}if(vivo())origen?.focus();};
  const abrir=(row,col,cel,boton)=>{
    if(!vivo())return;
    limpiarRevocadas();
    if(celdaVigente(row,col.key)===false)return;
    if(typeof alDetalle==='function'){alDetalle(row,col.key);return;}
    if(detalle)detalle.remove();origen=boton;detalleCelda={row,key:col.key};
    detalle=h('section',{class:'detalle250',role:'region','aria-label':`${row.nombre}: ${texto(col.titulo)}`,tabindex:'-1'},
      h('strong',{},`${row.nombre} · ${texto(col.titulo)}`),h('p',{},cel.detalle),
      h('button',{type:'button',class:'cerrar250',on:{click:()=>{if(vivo()){limpiarRevocadas();cerrar();}}}},'Cerrar detalle'));
    frame.append(detalle);detalle.focus();
  };
  frame.append(h('style',{},CSS_CONTROL_250),h('header',{},h('h2',{},texto(titulo,120))));
  if(!rows.length){frame.append(h('p',{class:'vacio250'},'No hay accounts disponibles en este ámbito.'));return frame;}
  const tbody=h('tbody',{});
  for(const row of rows){
    const nombre=h('button',{type:'button','aria-label':`Ver proyectos de ${row.nombre}`,on:{click:()=>{if(vivo()){limpiarRevocadas();if(typeof alSeleccionar==='function')alSeleccionar(row.id);}}}},row.nombre,
      h('small',{},Number.isSafeInteger(row.clientes)&&row.clientes>=0?`${row.clientes} clientes`:'Clientes por confirmar'));
    const tr=h('tr',{},h('td',{class:'p250'},nombre));
    for(const col of cols){
      const cel=celdaControl250(row.celdas?.[col.key]);let boton;
      boton=h('button',{type:'button',class:`c250 ${cel.estado}${col.key==='imputa'&&cel.referencia?' ref390-'+cel.referencia:''}`,'aria-label':`${row.nombre} · ${texto(col.titulo)} · ${cel.valor==='—'?'Sin dato':cel.valor}${cel.sub && cel.sub!=='Sin dato'?' · '+cel.sub:''}`,
        on:{click:()=>abrir(row,col,cel,boton)}},h('span',{},cel.valor));
      botones.push({row,col,boton});
      tr.append(h('td',{},boton));
    }
    tbody.append(tr);
  }
  frame.append(h('div',{class:'ctl250',role:'region','aria-label':'Mapa de control: desplaza para ver todos los indicadores',tabindex:'0'},
    h('table',{},h('thead',{},h('tr',{},h('th',{scope:'col'},'Account'),cols.map(c=>h('th',{scope:'col',title:`${texto(c.titulo,60)} · ${texto(c.sub,100)}`,'aria-label':`${texto(c.titulo,60)} · ${texto(c.sub,100)}`},c.key==='abandonados'?'Aband.':c.key==='tarde'?'Reu. tarde':texto(c.titulo,60),h('small',{},texto(c.sub,100)))))),tbody)));
  frame.append(h('p',{class:'vacio250'},'Pendientes: rojo crítico · amarillo revisar · — sin dato. Horas: colores de referencia, 8h × laborables; no jornada confirmada. Pulsa una cifra para ver su fuente.'));
  return frame;
}
