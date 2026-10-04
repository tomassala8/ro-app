//278 · vInc original: grupos por frecuencia; lectura, sin resolver ni enviar cambios.
import {h} from '../componentes.js';
const array=v=>Array.isArray(v)?v:[];
const herramientas={clickup:'ClickUp',desk:'Desk',crm:'CRM',sign:'Zoho Sign',app:'RO',airtable:'Airtable',holded:'Holded',hojas:'Hojas',windsor:'Windsor'};
const texto=s=>typeof s==='string'?s.split(/\r?\n/).filter(l=>!/(?:password|contrase(?:ña|na)|secret|api[_ -]?key|bearer|access[_ -]?token|refresh[_ -]?token)\s*[:=]/i.test(l)).join(' ').replace(/<[^>]*>/g,'').slice(0,4000):'';
export function puertaIncongruencias278(ctx){return ctx.servidor===true&&ctx.veModulo?.('incidencias')===true&&[ctx.real,ctx.persona].every(p=>{const ps=array(ctx.datos?.personas).filter(x=>x?.id===p?.id);return ps.length===1&&ps[0].estado==='activo'&&ps[0].activo!==false&&array(ps[0].puestos).some(r=>['direccion','operaciones'].includes(r));});}
export function prepararIncongruencias278(ctx,D){
 if(!puertaIncongruencias278(ctx))return {grupos:[],filas:[],fecha:null,disponible:false};
 const cs=array(ctx.clientesVisibles),ps=array(ctx.datos?.personas),rs=array(D?.incongruencias);
 const clientes=new Map(cs.filter(c=>c?.activo_confirmado===true&&c.detalle===true&&cs.filter(x=>x.id===c.id).length===1).map(c=>[c.id,c]));
 const filas=rs.filter(r=>typeof r?.id==='string'&&rs.filter(x=>x.id===r.id).length===1).filter(r=>{
  if(r.cliente_id)return clientes.has(r.cliente_id)&&!r.persona_id&&ctx.ver?.({tipo:'cliente_detalle',cliente_id:r.cliente_id})?.ok===true;
  if(!r.persona_id)return false;
  const personas=ps.filter(p=>p.id===r.persona_id);return personas.length===1&&personas[0].estado==='activo'&&personas[0].activo!==false&&ctx.ver?.({tipo:'alarma_persona',persona_id:r.persona_id})?.ok===true;
 }).map(r=>({id:r.id,cliente_id:r.cliente_id||null,persona_id:r.persona_id||null,nombre:clientes.get(r.cliente_id)?.nombre||ps.find(p=>p.id===r.persona_id)?.nombre||'Persona',tipo:texto(r.tipo)||'Sin tipo acreditado',detalle:texto(r.detalle)||'Sin detalle registrado',decide:texto(r.decide)||'Por confirmar',origen:texto(r.origen)||'Sin origen registrado',herramientas:[...new Set(array(r.herramientas).filter(t=>Object.hasOwn(herramientas,t)))].map(t=>({id:t,nombre:herramientas[t],fecha:D?.fuentes?.[t]?.hora||null}))}));
 const grupos=new Map();for(const r of filas){if(!grupos.has(r.tipo))grupos.set(r.tipo,[]);grupos.get(r.tipo).push(r);}
 return {filas,grupos:[...grupos].map(([tipo,filas])=>({tipo,filas,deciden:[...new Set(filas.map(r=>r.decide))]})).sort((a,b)=>b.filas.length-a.filas.length),fecha:typeof D?.generado==='string'?D.generado:null,disponible:Array.isArray(D?.incongruencias)};
}
export async function renderIncongruencias278(cont,ctx){
 const root=h('div',{class:'inc278'}),real=ctx.real?.id,vista=ctx.persona?.id;cont.append(root);
 const vivo=()=>root.isConnected&&real===ctx.real?.id&&vista===ctx.persona?.id&&(!ctx.vigente||ctx.vigente())&&puertaIncongruencias278(ctx);
 if(!puertaIncongruencias278(ctx))return;
 let D;try{D=await ctx.datosModulo('incidencias/incidencias');}catch{if(vivo())root.append(h('p',{},'No se pudo cargar el registro. Abre Incidencias para revisar el estado.'));return;}
 if(!vivo())return;const m=prepararIncongruencias278(ctx,D);
 root.append(h('style',{},'.inc278{display:grid;gap:10px}.inc278 h2{font-size:17px;margin:0}.inc278 details{background:var(--card,#fff);border:1px solid var(--line,#e1e4f1);border-radius:9px;padding:10px}.inc278 summary{cursor:pointer;font-size:13px}.inc278 table{width:100%;border-collapse:collapse;font-size:13px}.inc278 td{padding:8px;border-bottom:1px solid var(--line,#e1e4f1);vertical-align:top}.inc278 small{color:var(--dim,#666);display:block}.inc278 a{color:inherit}.inc278 .scroll278{overflow-x:auto}.inc278 table{min-width:550px}'),h('h2',{},'Lo que no cuadra'),h('small',{},`${m.filas.length} casos visibles en ${m.grupos.length} tipos · copia parcial`));
 if(!m.filas.length)root.append(h('p',{},m.disponible?'No hay casos visibles en esta copia. No confirma que todas las fuentes coincidan.':'Registro no disponible; pendiente de comprobar.'));
 for(const g of m.grupos){
  const tbody=h('tbody',{});
  for(const r of g.filas){
   const evidence=h('details',{},h('summary',{},'Fuentes y seguimiento'),h('small',{},`Origen: ${r.origen} · lectura del registro: ${m.fecha||'sin fecha'}`));
   if(r.herramientas.length)for(const t of r.herramientas)evidence.append(h('small',{},`${t.nombre}: ${t.fecha||'fecha de lectura no disponible'}`));
   else evidence.append(h('small',{},'Herramientas no identificadas en el registro.'));
   evidence.append(h('small',{},'Referencia por contrastar; no acredita diferencia vigente ni corrección en las herramientas.'),h('a',{href:`#/incidencias/${encodeURIComponent(r.id)}`},'Abrir seguimiento en Incidencias'));
   tbody.append(h('tr',{},h('td',{style:{width:'30%'}},r.cliente_id?h('a',{href:`#/ficha/${encodeURIComponent(r.cliente_id)}`},r.nombre):r.nombre),h('td',{},r.detalle,evidence)));
  }
  root.append(h('details',{},h('summary',{},g.tipo+' · '+g.filas.length+' · decide '+g.deciden.join(', ')),h('div',{class:'scroll278'},h('table',{},tbody))));
 }
 root.append(h('details',{},h('summary',{},'Alcance'),h('p',{},'Agrupado por tipo y número de casos, como el panel de referencia. Sólo identificadores únicos autorizados y clientes activos confirmados. Las fuentes enumeradas son las del registro: no se inventan valores A/B ni nuevas lecturas. Las decisiones se consultan en Incidencias; esta pantalla no modifica ni envía nada.')));
}
