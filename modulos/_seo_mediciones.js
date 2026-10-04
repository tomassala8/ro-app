// Proyecciones puras SEO: no red, permisos, objetivos inferidos ni modificaciones.
export const posicionSEO=v=>typeof v==='number'&&Number.isSafeInteger(v)&&v>0?v:null;
export const numeroSEO=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0?v:null;
export const conteoSEO=v=>numeroSEO(v)!==null&&Number.isSafeInteger(v)?v:null;
export function fechaSEO(v){
  if(typeof v!=='string'||!/^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?)?$/.test(v))return null;
  if(v.length>10&&(Number(v.slice(11,13))>23||Number(v.slice(14,16))>59||(v.length>=19&&Number(v.slice(17,19))>59)))return null;
  const dia=v.slice(0,10),d=new Date(dia+'T12:00:00Z');
  return Number.isFinite(+d)&&d.toISOString().slice(0,10)===dia&&Number.isFinite(Date.parse(v.length===10?v+'T12:00:00Z':v.replace(' ','T')))?dia:null;
}
export function cambioPosicionSEO(antes,hoy){const a=posicionSEO(antes),b=posicionSEO(hoy);return a===null||b===null?null:a-b;}
export function filasSeoAutorizadas(filas,clientes){
  const ids=new Set((Array.isArray(clientes)?clientes:[]).filter(c=>c?.activo_confirmado===true&&typeof c.id==='string').map(c=>c.id));
  return (Array.isArray(filas)?filas:[]).filter(f=>typeof f?.cliente_id==='string'&&ids.has(f.cliente_id));
}
export function contextoMotoresSEO(f){
  return (Array.isArray(f?.seranking?.motores_contexto)?f.seranking.motores_contexto:[]).map(m=>({
    buscador:typeof m.buscador==='string'?m.buscador:null,
    dispositivo:['mobile','desktop'].includes(m.dispositivo)&&m.dispositivo_estado==='confirmado'?m.dispositivo:null,
    region:typeof m.region==='string'&&m.region.trim()?m.region:null,
    fecha:fechaSEO(m.fecha_contexto),principal:m.principal===true,
  }));
}
export function configuracionActualMotoresSEO(f,hoy){
 const limite=fechaSEO(hoy),rows=Array.isArray(f?.seranking?.motores_contexto)?f.seranking.motores_contexto:[];
 const id=x=>Number.isSafeInteger(x)&&x>0?x:null;
 const texto=x=>typeof x==='string'&&x.trim()&&x.length<=200&&!/[\x00-\x1f]|https?:\/\/|@|password|secret|token|guest_link/i.test(x)?x.trim():null;
 return rows.filter(m=>{
  const a=m?.configuracion_actual,sid=id(m?.site_engine_id),fecha=fechaSEO(a?.fecha_contexto);
  return limite&&sid&&rows.filter(x=>id(x?.site_engine_id)===sid).length===1&&a&&id(a.site_engine_id)===sid&&id(a.search_engine_id)&&fecha&&fecha<=limite&&a.fecha_contexto===m.fecha_contexto&&m.contexto_posicion_confirmado===false&&m.objetivo_ciudad_confirmado===false&&m.aplica_fecha_distinta===false&&a.fuente==='SE Ranking /sites/search-engines + /system/search-engines';
 }).map(m=>{const a=m.configuracion_actual;return {motor:m.site_engine_id,buscador:texto(a.buscador),region:texto(a.region),idioma:texto(a.idioma),dispositivo:a.dispositivo_estado==='confirmado'&&['mobile','desktop'].includes(a.dispositivo)?a.dispositivo:null,fecha:fechaSEO(a.fecha_contexto),maps:({0:'Sin Maps',1:'Maps incluidos en los resultados',2:'Maps presentados por separado'})[a.maps_modo]||'Maps sin confirmar'};});
}
export function paginasSEO(f,meta,hoy){
  const lectura=fechaSEO(meta?.gsc?.leido),actual=fechaSEO(hoy);
  const error=!!f?.gsc?.error||(Array.isArray(f?.gsc?.errores)&&f.gsc.errores.length>0);
  const fuenteValida=!error&&['bien','a_cero'].includes(f?.gsc_estado)&&lectura&&actual&&lectura<=actual;
  const v=f?.clics?.ventanas?.mes,desde=fechaSEO(v?.[0]),hasta=fechaSEO(v?.[1]);
  const ventana=desde&&hasta&&desde<=hasta&&actual&&hasta<actual?{desde,hasta}:null;
  const filas=fuenteValida&&Array.isArray(f?.gsc?.paginas)?f.gsc.paginas:[];
  return {lectura,ventana,medido:!!fuenteValida,filas:filas.filter(x=>Array.isArray(x)&&typeof x[0]==='string').map(([url,cl,im,ps,ant])=>{
    let enlace=null;try{const u=new URL(url);if(['http:','https:'].includes(u.protocol)&&!u.username&&!u.password)enlace=u.href;}catch{}
    const clics=conteoSEO(cl),impresiones=conteoSEO(im),anterior=ventana&&ventanasComparablesSEO(f?.clics?.ventanas,'mes','mes_ant',28,hoy)?conteoSEO(ant):null,posicion=numeroSEO(ps)>0?numeroSEO(ps):null;
    const perdidos=clics!==null&&anterior!==null?Math.max(0,anterior-clics):null;
    const accion=!ventana?'Confirmar ventana de Search Console antes de comparar.'
      :clics===null||impresiones===null?'Completar la medición de esta URL.'
      :perdidos>0?'Revisar consultas y cambios de esta página; confirmar intención y objetivo antes de editar.'
      :impresiones>0&&clics===0?'Contrastar consultas, título e intención: impresiones observadas sin clics.'
      :'Revisar consultas e intención de esta página; no acredita objetivo cumplido.';
    return {url,enlace,clics,impresiones,posicion,anterior,perdidos,accion};
  }).sort((a,b)=>(b.perdidos??-1)-(a.perdidos??-1)||(b.impresiones??-1)-(a.impresiones??-1))};
}

const motorSEO=v=>(typeof v==='number'&&Number.isSafeInteger(v)&&v>0)||(typeof v==='string'&&/^\d+$/.test(v)&&Number.isSafeInteger(Number(v))&&Number(v)>0)?String(Number(v)):null;
export function parPosicionSEO(p,hoy,dias=7){
  const antes=posicionSEO(dias===30?p?.mes:p?.sem),actual=posicionSEO(p?.hoy),motor=motorSEO(p?.motor_id);
  const fa=fechaSEO(p?.fechas?.[dias===30?'mes':'sem']),fb=fechaSEO(p?.fechas?.hoy),limite=fechaSEO(hoy);
  if(antes===null||actual===null||!motor||!fa||!fb||!limite||fb>limite||(Date.parse(fb+'T00:00:00Z')-Date.parse(fa+'T00:00:00Z'))!==dias*864e5)return null;
  return {antes,actual,motor,desde:fa,hasta:fb,delta:antes-actual};
}
export function ventanasComparablesSEO(v,actual,anterior,n,hoy){
  const a=v?.[actual],b=v?.[anterior],limite=fechaSEO(hoy);
  if(!Array.isArray(a)||a.length!==2||!Array.isArray(b)||b.length!==2||!limite)return false;
  const [da,ha,db,hb]=[a[0],a[1],b[0],b[1]].map(fechaSEO);
  return !!da&&!!ha&&!!db&&!!hb&&ha<limite&&[ha,da,hb,db].every(x=>typeof x==='string')&&
    Date.parse(ha+'T00:00:00Z')-Date.parse(da+'T00:00:00Z')===(n-1)*864e5&&
    Date.parse(hb+'T00:00:00Z')-Date.parse(db+'T00:00:00Z')===(n-1)*864e5&&
    Date.parse(da+'T00:00:00Z')-Date.parse(hb+'T00:00:00Z')===864e5;
}
export function medicionClicsSEO(f,meta,hoy){
  const medido=paginasSEO(f,meta,hoy).medido,c=f?.clics||{},hasta=fechaSEO(c.hasta);
  const semana=medido&&ventanasComparablesSEO(c.ventanas,'semana','semana_ant',7,hoy)&&hasta===c.ventanas.semana[1]&&conteoSEO(c.semana)!==null&&conteoSEO(c.semana_ant)!==null;
  const mes=medido&&ventanasComparablesSEO(c.ventanas,'mes','mes_ant',28,hoy)&&hasta===c.ventanas.mes[1]&&conteoSEO(c.mes)!==null&&conteoSEO(c.mes_ant)!==null;
  const variacion=(a,b)=>b>0?100*(a-b)/b:null;
  return {medido,semana:!!semana,mes:!!mes,var_sem:semana?variacion(c.semana,c.semana_ant):null,var_mes:mes?variacion(c.mes,c.mes_ant):null};
}
export function visibilidadAcreditadaSEO(f,hoy){
  const v=f?.visibilidad,pares=v?.pares;
  if(v?.fiable===false||!Array.isArray(pares)||!pares.length)return null;
  const vistos=new Set(),validos=[];
  for(const p of pares){
    const par=parPosicionSEO(p,hoy),vol=numeroSEO(p?.vol),k=typeof p?.k==='string'&&p.k.trim()?p.k:null;
    if(!par||vol===null||!k)return null;
    const id=JSON.stringify([k,par.motor]);if(vistos.has(id))return null;vistos.add(id);validos.push({p,par,vol});
  }
  const ventanas=new Set(validos.map(x=>JSON.stringify([x.par.desde,x.par.hasta])));if(ventanas.size!==1)return null;
  const ctr={1:.30,2:.15,3:.10,4:.07,5:.05,6:.04,7:.03,8:.025,9:.02,10:.02};
  const peso=n=>ctr[n]??(n<=20?.01:0);
  const anterior=validos.reduce((s,x)=>s+x.vol*peso(x.par.antes),0),actual=validos.reduce((s,x)=>s+x.vol*peso(x.par.actual),0);
  return {var:anterior>0?100*(actual-anterior)/anterior:null,pares:validos.length,desde:validos[0].par.desde,hasta:validos[0].par.hasta};
}
export function normalizarAlertasSEO(f,meta,hoy){
  if(f?._medicionSEO?.normalizacion===177)f={...f,estado:f.estado_original,motivo:f.motivo_original,alertas:f.alertas_originales,reparto:f.reparto_original,visibilidad:f.visibilidad_original,clics:f.clics_original};
  const palabras=Array.isArray(f?.informe15)?f.informe15:[],origen=Array.isArray(f?.alertas)?f.alertas:[];
  const lectura=fechaSEO(f?.seranking?.ultima),limite=fechaSEO(hoy),sr=!!lectura&&!!limite&&lectura<=limite&&!f?.seranking?.error&&!['error','sin_conectar'].includes(meta?.seranking?.estado);
  const clics=medicionClicsSEO(f,meta,hoy),vis=visibilidadAcreditadaSEO(f,hoy);
  const alertas=origen.map(a=>{
    let evidencia=null,texto=null;
    if(sr&&['fuera_top10','cae'].includes(a?.tipo)&&typeof a.palabra==='string'){
      const rows=palabras.filter(p=>p?.k===a.palabra);const p=rows.length===1?rows[0]:null,par=parPosicionSEO(p,hoy);
      if(par&&par.hasta<=lectura&&a.antes===par.antes&&a.hoy===par.actual&&(a.motor_id==null||motorSEO(a.motor_id)===par.motor)&&
        (a.tipo==='fuera_top10'?par.antes<=10&&par.actual>10:par.actual>par.antes)){
        evidencia=par;texto=`«${a.palabra}»: posición observada ${par.antes} → ${par.actual} entre ${par.desde} y ${par.hasta} · motor ${par.motor}. Revisar; no acredita un objetivo contratado.`;
      }
    }else if(a?.tipo==='clics'&&clics.semana&&clics.var_sem!==null&&clics.var_sem<0){
      evidencia={fuente:'GSC',ventana:f.clics.ventanas.semana};texto=`GSC: ${f.clics.semana_ant} → ${f.clics.semana} clics en ventanas cerradas comparables de 7 días, hasta ${f.clics.hasta}. No son leads ni cumplimiento de objetivo.`;
    }else if(a?.tipo==='visibilidad'&&sr&&vis&&vis.hasta<=lectura&&vis.var!==null&&vis.var<0){
      evidencia=vis;texto=`Visibilidad estimada ${vis.var.toFixed(1)} % en ${vis.pares} pares observados ${vis.desde}–${vis.hasta}; no es tráfico real ni cumplimiento de objetivo.`;
    }
    return {...a,texto:texto||`Señal anterior por contrastar: ${typeof a?.texto==='string'?a.texto:'aviso sin detalle'}`,gravedad:evidencia?(a.tipo==='clics'?'ambar':['rojo','ambar'].includes(a.gravedad)?a.gravedad:'ambar'):'gris',acreditada:!!evidencia,evidencia};
  });
  const actuales=alertas.filter(a=>a.acreditada),estado=actuales.some(a=>a.gravedad==='rojo')?'rojo':actuales.length?'ambar':'gris';
  const reparto=f?.reparto?Object.fromEntries(Object.entries(f.reparto).map(([k,v])=>[k,v&&typeof v==='object'?{...v,mes:null}:v])):null;
  // Un mes agregado sólo se compara si todas las posiciones actuales de la muestra tienen par exacto de 30 días.
  const observadas=palabras.filter(p=>posicionSEO(p?.hoy)!==null),paresMes=observadas.map(p=>parPosicionSEO(p,hoy,30));
  const mesComparable=sr&&observadas.length>0&&paresMes.every(p=>p&&p.hasta<=lectura)&&new Set(observadas.map(p=>JSON.stringify([p.k,motorSEO(p.motor_id)]))).size===observadas.length&&new Set(paresMes.filter(Boolean).map(p=>JSON.stringify([p.desde,p.hasta]))).size===1;
  if(reparto&&mesComparable)for(const [k,n] of [['top1',1],['top3',3],['top5',5],['top10',10],['fuera',Infinity]]){
    if(reparto[k])reparto[k].mes=k==='fuera'?paresMes.filter(p=>p.antes>10).length:paresMes.filter(p=>p.antes<=n).length;
  }
  return {...f,estado_original:f.estado,motivo_original:f.motivo,alertas_originales:origen,reparto_original:f.reparto,visibilidad_original:f.visibilidad,clics_original:f.clics,
    estado,motivo:actuales[0]?.texto||'Sin alertas actuales acreditadas; las señales anteriores requieren contraste de fuente, fecha y motor.',alertas,
    n_alertas:{rojo:actuales.filter(a=>a.gravedad==='rojo').length,ambar:actuales.filter(a=>a.gravedad==='ambar').length},
    reparto,visibilidad:f.visibilidad?{...f.visibilidad,var:vis?.var??null}:null,clics:f.clics?{...f.clics,var_sem:clics.var_sem,var_mes:clics.var_mes,var_impr:null}:null,
    _medicionSEO:{normalizacion:177,sr,clics,visibilidad:vis,mesComparable,historicas:alertas.length-actuales.length},
  };
}

// Una cifra de cartera sólo suma una cohorte con la misma ventana cerrada.
export function resumenClicsCarteraSEO(filas,meta,hoy){
  const rows=Array.isArray(filas)?filas:[],ids=new Map();
  for(const f of rows)if(typeof f?.cliente_id==='string')ids.set(f.cliente_id,(ids.get(f.cliente_id)||0)+1);
  const limite=fechaSEO(hoy);
  const validas=rows.filter(f=>{
    const w=f?.clics?.ventanas?.semana,desde=fechaSEO(w?.[0]),hasta=fechaSEO(w?.[1]);
    return ids.get(f?.cliente_id)===1&&paginasSEO(f,meta,hoy).medido&&Array.isArray(w)&&w.length===2&&desde&&hasta&&limite&&hasta<limite&&
      Date.parse(hasta+'T00:00:00Z')-Date.parse(desde+'T00:00:00Z')===6*864e5&&fechaSEO(f.clics.hasta)===hasta&&conteoSEO(f.clics.semana)!==null;
  });
  const grupos=new Map();
  for(const f of validas){const k=JSON.stringify(f.clics.ventanas.semana);if(!grupos.has(k))grupos.set(k,[]);grupos.get(k).push(f);}
  const cohortes=[...grupos.values()].sort((a,b)=>b[0].clics.ventanas.semana[1].localeCompare(a[0].clics.ventanas.semana[1])||b.length-a.length||JSON.stringify(a[0].clics.ventanas).localeCompare(JSON.stringify(b[0].clics.ventanas)));
  const cohorte=cohortes[0]||[],suma=campo=>{if(!cohorte.length)return null;const n=cohorte.reduce((a,f)=>a+f.clics[campo],0);return Number.isSafeInteger(n)&&n>=0?n:null;};
  const comparable=cohorte.length>0&&cohorte.every(f=>medicionClicsSEO(f,meta,hoy).semana)&&new Set(cohorte.map(f=>JSON.stringify(f.clics.ventanas.semana_ant))).size===1;
  return {actual:suma('semana'),anterior:comparable?suma('semana_ant'):null,ventana:cohorte[0]?.clics.ventanas.semana||null,
    ventana_anterior:comparable?cohorte[0]?.clics.ventanas.semana_ant:null,clientes:cohorte.length,visibles:rows.length,
    otras_ventanas:validas.length-cohorte.length,cliente_ids:cohorte.map(f=>f.cliente_id)};
}
