// Proyección pura de referencias: no convierte registros legados en tasas vigentes.
const n=v=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=0?v:null;
export function primerIntento677(f){
 const v=f?.velocidad,numerador=n(v?.en_1h),denominador=n(v?.juzgables);
 const par=numerador!==null&&denominador!==null&&numerador<=denominador;
 return {texto:par?`${numerador}/${denominador}`:'—',estado:'gris',numerador:par?numerador:null,denominador:par?denominador:null,
  detalle:par?'Primeros intentos del registro anterior: numerador/denominador por contrastar. No tasa vigente ni respuesta acreditada.':'Sin par válido de primeros intentos; no se sustituye ausencia por cero.'};
}
export function sinIntento677(f,fuente,hoy,ahoraMs=Date.now()){
 const valor=n(f?.sin_tocar_24h),m=f?.sin_tocar_medicion,obs=n(m?.leads_observados),total=n(m?.leads_elegibles);
 const temporal=periodoSinIntento677(m,f,fuente,hoy,ahoraMs);
 const observado=temporal&&m?.fuente==='ghl_conversacion'&&m?.cobertura==='parcial'&&m?.completa===false&&obs!==null&&total!==null&&obs<=total&&(f?.leads_30d===undefined||n(f.leads_30d)!==null&&total===f.leads_30d)&&valor!==null&&valor<=obs;
 const vigente=observado&&new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(m.hasta_ms))===hoy;
 return {valor,texto:valor===null?'—':String(valor),observado,vigente,cobertura:observado?`${obs}/${total}`:null,
  detalle:observado?`${valor} sin intento registrado en ${obs}/${total} leads con lectura válida. Muestra parcial; captura ${new Date(m.hasta_ms).toISOString()}; no acredita ausencia de llamadas externas.`:'Conteo del registro anterior por contrastar; falta descriptor de lectura de intentos. No acredita ausencia de contacto.'};
}
const id=v=>typeof v==='string'&&/^[A-Za-z0-9_-]{1,160}$/.test(v);
const ms=v=>typeof v==='number'&&Number.isSafeInteger(v)&&v>0&&Number.isFinite(new Date(v).getTime())?v:null;
function dia(v){if(typeof v!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(v))return null;const d=new Date(v+'T12:00:00Z');return Number.isFinite(+d)&&d.toISOString().slice(0,10)===v?v:null;}
function instante(v){if(typeof v!=='string')return null;const m=v.match(/^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d(?:\.\d+)?)?(Z|[+-](\d{2}):(\d{2}))$/);if(!m||!dia(v.slice(0,10))||m[2]&&(Number(m[2])>14||Number(m[3])>59||Number(m[2])===14&&Number(m[3])!==0))return null;return ms(Date.parse(v));}
export function entradaLead677(x,hoy,fuente,ahoraMs=Date.now()){
 const unknown={texto:x?.respondio===true?'Por confirmar':'—',estado:'gris',fecha:null,
  detalle:x?.respondio===true?'Entrada del registro anterior por contrastar; sin descriptor no acredita que este lead escribiera desde su creación.':'Sin entrada acreditada en la lectura; no implica que el lead no respondiera por otro canal.'};
 const m=x?.respuesta_medicion676,desde=ms(m?.desde_ms),hasta=ms(m?.hasta_ms),ultima=ms(m?.ultima_entrada_ms),creado=instante(x?.creado_iso676),actual=dia(hoy);
 if(!actual||!id(x?.ref)||!id(x?.sub_id)||!id(x?.cliente_id)||x?.respondio!==true||!m||Array.isArray(m)||m.version!=='676.1'||m.fuente!=='ghl_conversacion'||m.estado!=='observado_parcial'||m.completa!==false||m.cliente_id!==x.cliente_id||m.sub_id!==x.sub_id||m.ref!==x.ref||m.respuesta_humana_confirmada!==null||m.resultado_comercial_confirmado!==null||n(m.entradas_observadas)===null||m.entradas_observadas<1||desde===null||desde!==creado||hasta===null||hasta<desde||ultima===null||ultima<desde||ultima>hasta)return unknown;
 const corte=new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(hasta));
 const leido=corteFuente677(fuente);
 if(ms(ahoraMs)===null||hasta>ahoraMs||corte>actual||leido===null||Math.floor(leido/60000)!==Math.floor(hasta/60000))return unknown;
 return {texto:'Entrada obs.',estado:'gris',fecha:new Date(ultima).toISOString(),detalle:`Entrada escrita observada desde la creación del lead, última ${new Date(ultima).toISOString()}. Muestra parcial; no confirma respuesta humana, llamada, cualificación ni venta.`};
}
export function agregarSinIntento677(filas,fuente,hoy,ahoraMs=Date.now()){
 const xs=Array.isArray(filas)?filas:[],ids=new Map();for(const f of xs){const k=f?.sub_id;ids.set(k,(ids.get(k)||0)+1);}
 const pares=xs.filter(f=>id(f?.cliente_id)&&id(f?.sub_id)&&ids.get(f.sub_id)===1&&sinIntento677(f,fuente,hoy,ahoraMs).observado);
 const sum=k=>{let t=0;for(const f of pares){t+=f.sin_tocar_medicion[k];if(!Number.isSafeInteger(t))return null;}return pares.length?t:null;};
 const obs=sum('leads_observados'),total=sum('leads_elegibles');
 let valor=pares.length?0:null;for(const f of pares){valor+=f.sin_tocar_24h;if(!Number.isSafeInteger(valor)){valor=null;break;}}
 let referencia=null;for(const f of xs){const v=n(f?.sin_tocar_24h);if(v===null)continue;referencia=(referencia??0)+v;if(!Number.isSafeInteger(referencia)){referencia=null;break;}}
 return {referencia,todoScope:valor!==null&&obs!==null&&total!==null&&xs.length>0&&pares.length===xs.length&&pares.every(f=>sinIntento677(f,fuente,hoy,ahoraMs).vigente),valor:obs!==null&&total!==null?valor:null,cobertura:valor!==null&&obs!==null&&total!==null?`${obs}/${total}`:null,detalle:valor!==null&&obs!==null&&total!==null?`${valor} sin intento registrado en ${obs}/${total} leads con lectura válida en ${pares.length}/${xs.length} subcuentas. Captura ${fuente.hora}; muestra parcial, no censo de contactos ni llamadas; referencias de filas sin descriptor excluidas de esta cifra.`:'Sin cobertura válida de lectura de intentos; los conteos guardados son referencias por contrastar.'};
}

function corteFuente677(f){
 if(f?.estado!=='bien'||f?.error||f?.errores?.length||typeof f.hora!=='string')return null;
 const aware=instante(f.hora);if(aware!==null)return aware;
 const m=f.hora.match(/^(\d{4}-\d{2}-\d{2})[ T]((?:[01]\d|2[0-3]):[0-5]\d)(?::([0-5]\d))?$/);if(!m||!dia(m[1]))return null;
 const pseudo=Date.parse(`${m[1]}T${m[2]}:${m[3]||'00'}Z`),matches=[];
 const fmt=new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'});
 for(const offset of [60,120]){const t=pseudo-offset*60000;if(fmt.format(new Date(t))===`${m[1]} ${m[2]}`)matches.push(t);}
 return matches.length===1?matches[0]:null;
}

function periodoSinIntento677(m,f,fuente,hoy,ahora){
 if(f?.error||f?.errores_lectura?.length||!m||m.version!=='676.1'||!id(f?.cliente_id)||!id(f?.sub_id)||m.cliente_id!==f.cliente_id||m.sub_id!==f.sub_id||!dia(hoy)||m.hora_fuente!==fuente?.hora)return false;
 const desde=ms(m.desde_ms),cohorte=ms(m.cohorte_hasta_ms),cut=ms(m.hasta_ms),lectura=corteFuente677(fuente);
 if(desde===null||cohorte===null||cut===null||ms(ahora)===null||desde>=cohorte||cohorte>cut||cut>ahora||lectura===null||Math.floor(lectura/60000)!==Math.floor(cut/60000))return false;
 const fmt=new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'});
 const d=fmt.format(new Date(desde)),h=fmt.format(new Date(cohorte)),c=fmt.format(new Date(cut));
 return d.slice(11)==='00:00:00'&&h.slice(11)==='00:00:00'&&c.slice(0,10)===h.slice(0,10)&&c.slice(0,10)<=hoy&&Date.parse(h.slice(0,10)+'T12:00:00Z')-Date.parse(d.slice(0,10)+'T12:00:00Z')===30*864e5;
}
