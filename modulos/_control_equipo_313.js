import { serieHorasDiaria238 } from './_horas_diarias_238.js';
const filas=v=>Array.isArray(v)?v:[];
const numero=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0;
const dia=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+'T12:00:00Z'))&&new Date(v+'T12:00:00Z').toISOString().slice(0,10)===v;
export function diaControlEquipo313(hoy){if(!dia(hoy))return null;const d=new Date(hoy+'T12:00:00Z');do{d.setUTCDate(d.getUTCDate()-1);}while([0,6].includes(d.getUTCDay()));return d.toISOString().slice(0,10);}
const referencia=(v,detalle)=>({valor:numero(v)&&v>0?v:null,estado:'gris',tipo:numero(v)&&v>0?'referencia':'sin_dato',detalle});
export function prepararControlEquipo313(ctx,control,horas){
 const objetivo=diaControlEquipo313(ctx.hoy),ps=filas(ctx.datos?.personas),cont=filas(control),hs=filas(horas?.personas),counts=new Map();
 const id=x=>typeof x?.persona_ref==='string'&&x.persona_ref?x.persona_ref:typeof x?.persona_id==='string'?x.persona_id:null;
 for(const x of cont){const p=id(x);if(p)counts.set(p,(counts.get(p)||0)+1);}
 return cont.filter(x=>{const p=id(x),catalogo=ps.filter(q=>q?.id===p);return p&&(!x.persona_ref||!x.persona_id||x.persona_ref===x.persona_id)&&counts.get(p)===1&&catalogo.length===1&&catalogo[0].estado==='activo'&&catalogo[0].activo!==false&&ctx.ver?.({tipo:'horas_persona',persona_id:p})?.ok===true;}).map(x=>{
  const p=id(x),copia=hs.filter(r=>r?.persona_id===p),serie=horas?.hoy===ctx.hoy&&copia.length===1?serieHorasDiaria238(copia[0],ctx.hoy):null,d=serie?.dias.find(r=>r.fecha===objetivo);
  const imputa=d?.estado==='observado'?{valor:d.horas,estado:'gris',tipo:'observado',fecha:objetivo,fuente:serie.fecha_fuente,detalle:`${objetivo} · ${serie.zona} · ${d.entradas} entradas válidas · lectura ${serie.fecha_fuente}. Copia parcial: no es total exhaustivo, jornada ni incumplimiento.`}:referencia(x.imputa?.ayer,'Referencia heredada sin descriptor diario compatible; fecha/periodo y completitud no acreditados. Ausencia no es cero; no se evalúa jornada ni calendario.');
  const celdas={imputa,revisa:referencia(x.revisa?.mas48,'Referencia registrada de revisiones+48h; falta descriptor de cobertura/periodo para evaluar cumplimiento.'),contesta:referencia(x.contesta?.mas48,'Referencia registrada de correos+48h; falta cobertura completa comparable.'),reunion:referencia(x.reune?.sin_reunion,'Referencia mensual antigua; falta de registro no acredita ausencia de reunión ni incumplimiento.'),correo:referencia(x.reune?.sin_correo_sem,'Referencia semanal antigua; falta de registro no acredita ausencia de contacto. No equivale a declaraciones del registro de equipo.')};
  return {...x,persona_id:p,control_313:{version:'313.1',fecha:objetivo,celdas},imputa:{...x.imputa,ayer:imputa.valor}};
 });
}
export function celdaControlEquipo313(fila,key){const c=fila?.control_313?.version==='313.1'?fila.control_313.celdas?.[key]:null;return c&&numero(c.valor)&&['observado','referencia'].includes(c.tipo)?c:{valor:null,estado:'gris',tipo:'sin_dato',detalle:c?.detalle||'Sin descriptor compatible de esta cifra; no se sustituye por cero ni cumplimiento.'};}
