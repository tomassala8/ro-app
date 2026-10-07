//274 · vResumen914/vAccMini951/vPasos977, lectura recortada y sin acciones externas.
import {h,chipEstado} from '../componentes.js';
import {prepararAccounts263} from './_operaciones_accounts_263.js';
import {prepararBandeja270} from './_operaciones_bandeja_270.js';
import {badgesPasos433} from './_pasos_resumen_433.js';
import {ambitoUrgencias406,proyectarUrgencias406} from './_operaciones_urgencias_406.js';
import {puestoControl239,tituloControl239} from './_control_cartera_ruta_239.js';
import {ambitoHistorial364,cargarHistorial364,historialVigente364} from './_historial_diario_364.js';
export const INDICADORES274=[
 ['Clientes con correos +48 h','bandeja'],['Horas imputadas ayer','equipo'],['Rojos sin plan o sin Coti','rojos'],
 ['Revisión +48 h','produccion'],['Tickets sin asignar','bandeja'],['Informes antes del día 5','clientes'],
 ['Nuevos fuera de plazo','nuevos'],['Semáforos sin rellenar','clientes'],['Tu cola de revisión','produccion'],
 ['Horas para revisar','equipo/anomalias'],['Decisiones para Tomás','tomas'],
];
export const PASOS274=[['equipo','El equipo'],['bandeja','Clientes esperando'],['produccion','Producción'],['fuegos','Fuegos'],['clientes','Contacto y reuniones'],['nuevos','Clientes nuevos'],['tomas','Cierre del día']];
const arr=v=>Array.isArray(v)?v:[];
const n=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0;
const dia=s=>typeof s==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&Number.isFinite(Date.parse(s+'T00:00:00Z'))&&new Date(s+'T00:00:00Z').toISOString().slice(0,10)===s;
const fecha=(s,hoy)=>typeof s==='string'&&dia(s.slice(0,10))&&s.slice(0,10)<=hoy&&Number.isFinite(Date.parse(s.replace(' ','T')))?s:null;
const fmt=v=>n(v)?new Intl.NumberFormat('es-ES',{maximumFractionDigits:1}).format(v):'—';
const unknown=detalle=>({valor:'—',estado:'gris',detalle});
const obs=(valor,detalle,estado='gris')=>({valor:String(valor),detalle,estado});
export function puertaResumen274(ctx){return ctx.servidor===true&&dia(ctx.hoy)&&ctx.veModulo?.('mi-dia')&&[ctx.real,ctx.persona].every(p=>{const ps=arr(ctx.datos?.personas).filter(x=>x?.id===p?.id);return p?.id&&p.estado==='activo'&&p.activo!==false&&ps.length===1&&ps[0].estado==='activo'&&ps[0].activo!==false&&arr(ps[0].puestos).some(r=>['direccion','operaciones','account'].includes(r));});}
function clientes274(ctx){const cs=arr(ctx.clientesVisibles);return cs.filter(c=>c?.activo_confirmado===true&&c.detalle===true&&cs.filter(x=>x.id===c.id).length===1);}
function verdad274(ctx,cid){const v=ctx.verdad?.(cid),ids=[v?.id,v?.cliente_id].filter(x=>x!=null);return ids.length&&ids.every(id=>id===cid)?v:null;}
export function comprobarPlan274(d,cid){
 if(d?.cliente_id!==cid||!Number.isSafeInteger(d.version)||d.version<0||d.origen!=='local'||d.confirmado_proveedor!==false)return null;
 if(d.plan===null&&d.version===0&&d.revision===null)return {pendiente:true,detalle:'Sin plan local registrado.'};
 const p=d.plan;if(!p||!Number.isSafeInteger(p.version)||p.version<1||p.version>d.version||typeof p.que!=='string'||typeof p.responsable_id!=='string'||!dia(p.plazo))return null;
 const r=d.revision;if(r===null)return {pendiente:true,detalle:'Plan local sin revisión registrada para esta versión.'};
 if(!r||!Number.isSafeInteger(r.version)||r.version<=p.version||r.version>d.version||r.plan_version!==p.version||r.actor_id!=='constanza'||!['visto','pedir_cambios'].includes(r.estado))return null;
 return {pendiente:r.estado!=='visto',detalle:r.estado==='visto'?'Visto local por Constanza para la versión actual; no acredita ejecución ni comunicación externa.':'Constanza pidió cambios sobre esta versión.'};
}
function ayer274(hoy){const d=new Date(hoy+'T00:00:00Z');do{d.setUTCDate(d.getUTCDate()-1);}while(d.getUTCDay()===0||d.getUTCDay()===6);return d.toISOString().slice(0,10);}
export function horasResumen517(ctx,H,hist){
 const scope=ambitoHistorial364(ctx,H),day=dia(ctx.hoy)?ayer274(ctx.hoy):null;
 if(!day||!scope||!scope.ids.length||!hist||hist.denegado||!historialVigente364(ctx,H,hist)||!(hist.series instanceof Map))return unknown('Sin historial personal válido y autorizado para el último día L–V anterior; no equivale a cero.');
 const valores=[],fuentes=new Set();
 for(const pid of scope.ids){const serie=hist.series.get(pid);if(!serie||serie.zona!=='Europe/Madrid')continue;
  const stamp=Date.parse(serie.fecha_fuente);if(!Number.isFinite(stamp))continue;
  const leido=new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(stamp));
  if(day>=leido||day<serie.desde||day>serie.hasta)continue;
  const ds=arr(serie.dias).filter(d=>d?.fecha===day);if(ds.length!==1)continue;const d=ds[0];
  if(d.estado!=='observado'||!n(d.horas)||!Number.isSafeInteger(d.entradas)||d.entradas<1)continue;
  valores.push(d.horas);fuentes.add(serie.fecha_fuente);
 }
 if(!valores.length)return unknown(`${day} · último día L–V anterior: sin registros observados de fecha completa en el historial autorizado. Ausencia de registro no significa0h ni incumplimiento; no se recupera el legado238.`);
 const total=valores.reduce((a,b)=>a+b,0);if(!Number.isFinite(total))return unknown('Suma de horas fuera de rango; no se presenta cero ni un total parcial alternativo.');
 let inferior=total;
 if(total<=Number.MAX_VALUE/10){inferior=Math.floor(total*10)/10;if(inferior>total)inferior=Math.max(0,inferior-0.1);}
 return obs(total>0&&total<0.1?'<0,1 h obs.':`≥${fmt(inferior)} h`,`${day} · último día L–V anterior (selección del artifact, no calendario laboral). ${valores.length}/${scope.ids.length} personas autorizadas con registro observado. Fuente ClickUp entradas: ${[...fuentes].join(' · ')}; zona Europe/Madrid. Duración parcial atribuida al inicio, no fin confirmado. Personas y fechas sin registro desconocidas; no8h/40h, capacidad, ausencia o desempeño.`);
}
export function modeloResumen274(ctx,F={},planes={},hist=null){
 if(!puertaResumen274(ctx))return {indicadores:INDICADORES274.map(([etiqueta,ruta])=>({etiqueta,ruta,...unknown('Sesión actual no autorizada para esta comparativa.')})),accounts:[],prioridades:[],criticos:[],cobertura:'Sin sesión autorizada.'};
 const hoy=ctx.hoy,cs=clientes274(ctx),ids=new Set(cs.map(c=>c.id)),a=prepararAccounts263(ctx,F),b=prepararBandeja270(ctx,F.bandeja_detalle,F.captacion);
 const ms=INDICADORES274.map(([etiqueta,ruta])=>({etiqueta,ruta,...unknown('No hay medición comparable acreditada en las fuentes autorizadas.')}));
 const med=a.rows.filter(r=>r.tickets?.medicion),rev=a.rows.filter(r=>r.revisiones?.medicion);
 if(med.length){const count=med.filter(r=>r.tickets.medicion.mas_48>0).length;ms[0]={...ms[0],...obs(count,`${med.length}/${cs.length} clientes medidos. Correos>48h observados al corte; puede incluir saneamiento histórico. Estado y último mensaje actuales por contrastar; no total de agencia.`),etiqueta_mostrada:'Clientes con correos +48 h · copia'};}
 const H=F.horas,ps=arr(H?.personas).filter(p=>{const actuales=arr(ctx.datos?.personas).filter(x=>x?.id===p?.persona_id);return typeof p?.persona_id==='string'&&arr(H.personas).filter(x=>x.persona_id===p.persona_id).length===1&&actuales.length===1&&actuales[0].estado==='activo'&&actuales[0].activo!==false;});
 ms[1]={...ms[1],...horasResumen517(ctx,H,hist)};
 const criticos=cs.filter(c=>verdad274(ctx,c.id)?.gravedad==='critico'),conPlanes=criticos.map(c=>comprobarPlan274(planes[c.id],c.id)).filter(Boolean);
 if(conPlanes.length){const count=conPlanes.filter(p=>p.pendiente).length;ms[2]={...ms[2],...obs(`${conPlanes.length<criticos.length?'≥':''}${count}/${criticos.length}`,`${conPlanes.length}/${criticos.length} clientes críticos con respuesta de plan validada. Falta plan o visto de versión exacta; los demás desconocidos. Visto local no prueba ejecución.`,count?'ambar':'gris')};}
 else ms[2].detalle=criticos.length?'No se pudo verificar plan/visto de los clientes críticos autorizados.':'Sin clientes críticos en el catálogo autorizado; copia de la cartera, no inventario global.';
 if(rev.length){const count=rev.reduce((s,r)=>s+r.revisiones.medicion.mas_48,0);ms[3]={...ms[3],...obs(count,`${rev.length}/${cs.length} proyectos agrupados medidos por flujo. Revisiones>48h observadas; no aceptación ni total exhaustivo.`,count?'ambar':'gris')};}
 if(b.fuentes?.desk&&!b.fuentes.desk.historica){const count=b.triaje.filter(t=>['seguro','dudoso'].includes(t.propuesta)).length;ms[4]={...ms[4],...obs(count,`Tickets con propuesta claro/dudoso presentes en copia del ${b.fuentes.desk.fecha}. Asignación actual por contrastar; una marca local no la confirma. Cobertura parcial.`),etiqueta_mostrada:'Propuestas de asignación · copia'};}
 const I=F.informes;let prev=null;if(dia(hoy)){const d=new Date(hoy+'T00:00:00Z');d.setUTCDate(0);prev=d.toISOString().slice(0,7);}
 const informes=fecha(I?._meta?.generado,hoy)?arr(I?.filas).filter(r=>ids.has(r?.cliente_id)&&r.mes===prev&&arr(I.filas).filter(x=>x.cliente_id===r.cliente_id&&x.mes===prev).length===1):[];
 if(informes.length){const limite=hoy.slice(0,7)+'-05',enviados=informes.filter(r=>fecha(r.enviado?.fecha,hoy)&&r.enviado.fecha.slice(0,10)<=limite).length;ms[5]={...ms[5],...obs(`${enviados}/${informes.length} registros`,`${prev}: envíos registrados con fecha hasta ${limite}; día5 es referencia del artifact. Denominador de filas mensuales observadas; no criterio contractual ratificado, aceptación ni cobertura de todos los clientes.`)};}
 const N=F.nuevos,altas=fecha(N?.generado,hoy)?arr(N.altas).filter(r=>ids.has(r?.cliente_id)&&arr(N.altas).filter(x=>x.cliente_id===r.cliente_id).length===1&&dia(r.alta)&&r.alta<=hoy&&typeof r.alta_prueba==='string'&&r.alta_prueba.trim()):[];
 const plazo=altas.filter(r=>['rojo','ambar','verde','gris'].includes(r.plazo?.estado));if(plazo.length){const count=plazo.filter(r=>r.plazo.estado==='rojo').length;ms[6]={...ms[6],...obs(`${count} señales`,`${plazo.length} altas con fecha/prueba y estado de plazo en la copia. Señales declaradas por productor, no una nueva regla ni aceptación de hitos. Revisar versión contractual10/12 por cliente.`,count?'ambar':'gris')};}
 ms[7].detalle='No hay inventario fechado de semáforos manuales esperados y completados. Gravedad canónica y semáforo rellenado son campos diferentes.';
 const cola=fecha(F.produccion?.fuentes?.tareas?.hora,hoy)?arr(F.produccion?.cola).filter(t=>ids.has(t.cli)&&t.persona_id==='mili'&&t.estado_determinado===true&&['revisión mili','revision mili'].includes(t.estado)):[];
 if(cola.length)ms[8]={...ms[8],...obs(cola.length,'Tareas identificadas en revisión Mili presentes en copia parcial. Sin filas no certifica cola vacía.','ambar')};
 const raras=fecha(H?.generado,hoy)?arr(H?.raras).filter(r=>ps.some(p=>p.persona_id===r?.persona_id)):[];
 if(raras.length)ms[9]={...ms[9],...obs(raras.length,'Señales de registros de horas en la copia autorizada. No se ha contrastado estado de validación durable ni implican mala imputación.','ambar')};
 const decisiones=arr(F.decisiones?.decisiones).filter(d=>d?.id!=null&&arr(F.decisiones.decisiones).filter(x=>String(x.id)===String(d.id)).length===1).filter(d=>(!d.cliente_id||ids.has(d.cliente_id))&&d.respondida===false&&d.tipo!=='para_coti');
 if(decisiones.length)ms[10]={...ms[10],...obs(decisiones.length,'Decisiones presentes sin respuesta registrada. Lista autorizada y parcial, no totalidad del historial.','ambar')};
 const prioridades=arr(F.alertas?.alertas).filter(x=>x?.cliente_id?ids.has(x.cliente_id):true).filter(x=>typeof x.titulo==='string'||typeof x.texto==='string').sort((x,y)=>({rojo:0,ambar:1,amarillo:1}[x.gravedad]??2)-({rojo:0,ambar:1,amarillo:1}[y.gravedad]??2)).slice(0,5);
 return {indicadores:ms,accounts:a.groups,prioridades,criticos:criticos.map(c=>c.id),cobertura:'Fuentes parciales recortadas por identidad; desconocido nunca se transforma en cero o verde.'};
}
export function progresoResumen274(p,ctx){
 return p?.fuente==='registro_local'&&p.persona_id===ctx.persona?.id&&p.dia===ctx.hoy&&Number.isSafeInteger(p.total)&&p.total>0&&Number.isSafeInteger(p.hechas)&&p.hechas>=0&&p.hechas<=p.total?{hechas:p.hechas,total:p.total,pct:Math.round(p.hechas/p.total*100)}:null;
}
const CSS274=`.res274{display:grid;gap:12px;color:#10132b;font-family:system-ui,sans-serif}.res274 .tiles274{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.res274 .tile274{display:grid;gap:5px;padding:11px 14px;border:1px solid #e1e4f1;background:white;border-radius:10px;text-decoration:none;color:inherit;font-size:12px;min-width:0}.res274 .tile274 b{font-size:20px}.res274 .tile274.rojo{background:#fcebeb;border-color:#f1c6c8}.res274 .tile274.ambar{background:#fff3d6;border-color:#efdcaf}.res274 .tile274.gris{color:#464b68}.res274 details{border:1px solid #e1e4f1;border-radius:10px;background:white;padding:10px 14px}.res274 summary{cursor:pointer;font-size:13px}.res274 .pasos274{display:flex;flex-wrap:wrap;gap:6px}.res274 .pasos274 a{padding:9px 12px;min-height:44px;box-sizing:border-box;text-decoration:none;color:inherit;background:#eceef7;border-radius:8px;font-size:13px}.res274 .paso-badge433{display:inline-flex;align-items:center;justify-content:center;min-width:20px;margin-left:6px;padding:2px 5px;border-radius:6px;font-size:12px;background:#e0e3ed;color:#464b68}.res274 .paso-badge433.ambar{background:#fff3d6;color:#765500}.res274 .paso-badge433.rojo{background:#fcebeb;color:#9b2830}.res274 table{width:100%;border-collapse:collapse;font-size:13px}.res274 th,.res274 td{padding:8px 10px;text-align:left;border-bottom:1px solid #eceef7}.res274 .bar274{height:5px;background:#eceef7;border-radius:4px}.res274 .bar274 i{display:block;height:5px;background:#9a94dd;border-radius:4px}.res274 h2{font-size:15px;margin:0 0 8px}@media(max-width:600px){.res274 .tiles274{grid-template-columns:repeat(2,minmax(0,1fr));}.res274 table{min-width:550px}}`;
export async function renderResumen274(cont,ctx,opciones={}){
 const root=h('div',{class:'res274'}),real=ctx.real?.id,vista=ctx.persona?.id;cont.append(root);
 const vivo=()=>root.isConnected&&real===ctx.real?.id&&vista===ctx.persona?.id&&(!ctx.vigente||ctx.vigente())&&puertaResumen274(ctx);
 if(!puertaResumen274(ctx))return;
 let F=opciones.fuentes;
 if(!F){const specs=[['bandeja','bandeja/por_cliente','bandeja'],['bandeja_detalle','bandeja/bandeja','bandeja'],['produccion','produccion/produccion','produccion'],['horas','horas/horas','horas'],['nuevos','nuevos/nuevos','clientes-nuevos'],['informes','informes/informes','informes-mensuales'],['alertas',`alertas/p_${vista}`,'alertas'],['decisiones',null,'decisiones']];
  F=Object.fromEntries(await Promise.all(specs.map(async([k,p,m])=>{if(!ctx.veModulo(m))return[k,null];try{return[k,await(p?ctx.datosModulo(p):ctx.api('decisiones'))];}catch{return[k,null];}})));}
 if(!vivo())return;
 const crit=clientes274(ctx).filter(c=>verdad274(ctx,c.id)?.gravedad==='critico'),planes={};
 if(ctx.veModulo('en-rojo'))await Promise.all(crit.map(async(c)=>{try{const d=await ctx.api(`en-rojo/planes?cliente_id=${encodeURIComponent(c.id)}`);if(vivo()&&clientes274(ctx).some(x=>x.id===c.id)&&verdad274(ctx,c.id)?.gravedad==='critico'&&comprobarPlan274(d,c.id))planes[c.id]=d;}catch{}}));
 if(!vivo())return;
 const scope517=ambitoHistorial364(ctx,F.horas);let hist517=null;
 if(scope517?.ids.length){hist517=await cargarHistorial364(ctx,F.horas);if(!vivo()){root.replaceChildren();return;}}
 const horasVigentes517=()=>vivo()&&(!scope517||ambitoHistorial364(ctx,F.horas)?.firma===scope517.firma)&&(!hist517||hist517.denegado||historialVigente364(ctx,F.horas,hist517));
 const m=modeloResumen274(ctx,F,planes,hist517);if(!vivo())return;
 const destino=(ruta)=>{const mod=({equipo:'horas',bandeja:'bandeja',fuegos:'produccion',rojos:'en-rojo',produccion:'produccion',clientes:'mi-dia',nuevos:'clientes-nuevos',tomas:'decisiones',hoy:'alertas'})[ruta.split('/')[0]];return ctx.veModulo(mod)?`#/operaciones/${ruta}`:null;};
 const subtitulos=['Incluye histórico · estado actual por contrastar','Último día L–V anterior · registros parciales','Consultar planes y visto de Coti','Entregas pendientes de revisar','Revisar propuestas de asignación','Consultar el registro mensual','Revisar altas y plazos','Actualizar el seguimiento','Revisar tareas de la cola','Contrastar registros de horas','Resolver decisiones pendientes'];
 const tile=x=>{const href=destino(x.ruta);return h(href?'a':'div',{href:href||undefined,class:`tile274 ${x.estado}`,title:x.detalle,on:x.etiqueta==='Horas imputadas ayer'?{click:e=>{if(!horasVigentes517()){e.preventDefault();root.replaceChildren();}}}:undefined},h('span',{},x.etiqueta_mostrada||x.etiqueta),h('b',{},x.valor),h('small',{},subtitulos[INDICADORES274.findIndex(([etiqueta])=>etiqueta===x.etiqueta)]));};
 root.replaceChildren(h('style',{},CSS274),h('div',{class:'tiles274'},m.indicadores.slice(0,6).map(tile)),h('details',{},h('summary',{},'Más indicadores ·5'),h('div',{class:'tiles274',style:{marginTop:'10px'}},m.indicadores.slice(6).map(tile))));
 const scope530=ambitoUrgencias406(ctx),puesto530=puestoControl239(ctx.real,ctx.persona);
 const vigente530=()=>vivo()&&scope530&&ambitoUrgencias406(ctx)?.firma===scope530.firma;
 const macro530=scope530&&puesto530&&ctx.veModulo('mi-dia')?h('a',{class:'tile274',href:`#/mi-dia/control-cartera/${puesto530}`,title:'Carteras y proyectos autorizados · control macro',on:{click:e=>{if(!vigente530()||!ctx.veModulo('mi-dia')){e.preventDefault();root.replaceChildren();}}}},tituloControl239(puesto530)):null;
 if(macro530)root.replaceChildren(h('style',{},CSS274),macro530,h('div',{class:'tiles274'},m.indicadores.slice(0,6).map(tile)),h('details',{},h('summary',{},'Más indicadores ·5'),h('div',{class:'tiles274',style:{marginTop:'10px'}},m.indicadores.slice(6).map(tile))));
 const badges=badgesPasos433(m.indicadores);
 const fuego530=h('span',{});
 const pintarFuego530=model=>{const badge=badgesPasos433(m.indicadores,model)[3],href=destino('fuegos');fuego530.replaceChildren(h(href?'a':'span',{href:href||undefined,title:`4. Fuegos · ${badge.detalle}`,'aria-label':`4. Fuegos · ${badge.detalle}`,on:{click:e=>{if(!vigente530()){e.preventDefault();root.replaceChildren();}}}},'4. Fuegos · copia',h('span',{class:'paso-badge433 gris','aria-hidden':'true'},badge.valor)));};
 pintarFuego530(null);
 const etiquetasPasos433=['Equipo','Clientes >48h','Producción','Fuegos','Contacto/reu.','Nuevos','Cierre'];
 const progreso=progresoResumen274(opciones.progreso,ctx);
 root.append(h('div',{},h('small',{},progreso?`${progreso.hechas}/${progreso.total} registros de hoy · ${progreso.pct}%`:'Avance de hoy: pendiente de registrar.'),h('div',{class:'bar274'},progreso?h('i',{style:{width:progreso.pct+'%'}}):null)));
 const fuenteCartera535=h('details',{on:{toggle:()=>{if(!vivo()||(scope530&&!vigente530()))root.replaceChildren();}}},h('summary',{},'Fuente y referencia'),h('p',{},'Clientes: cartera visible autorizada; cobertura parcial. Nota: referencia histórica0–100; sin regla y cobertura confirmadas no se calcula. Capacidad12 es referencia del artifact, no capacidad personal ratificada ni huecos calculados. Carga: no hay una medición distinta del recuento de clientes; no se repite ese número como carga.'),h('ul',{},m.accounts.map(g=>h('li',{},g.nombre+' · '+g.referenciaCarga.detalle+' '+g.nota.detalle))));
 const accounts=h('details',{open:true,on:{toggle:()=>{if(!vivo()||(scope530&&!vigente530()))root.replaceChildren();}}},h('summary',{},'Accounts de un vistazo'),h('div',{style:{overflowX:'auto'}},h('table',{},h('thead',{},h('tr',{},['Account','Clientes visibles','Nota','Carga'].map(t=>h('th',{scope:'col'},t)))),h('tbody',{},m.accounts.map(g=>h('tr',{},h('td',{},destino('accounts')?h('a',{href:'#/operaciones/accounts'},g.nombre):g.nombre),h('td',{title:'Clientes de esta cartera visibles en el ámbito autorizado; cobertura parcial.'},g.clientes),h('td',{title:g.nota.detalle},chipEstado('gris',g.nota.valor)),h('td',{},h('span',{class:'gris',title:'Sin medición de carga distinta de la cartera visible; no capacidad confirmada.','aria-label':'Carga desconocida; el recuento de clientes no mide carga ni capacidad.'},'—'))))))),fuenteCartera535);
 root.append(accounts,h('section',{},h('h2',{},'Tu ronda de hoy, en este orden'),h('div',{class:'pasos274'},PASOS274.map(([ruta,t],i)=>{if(i===3)return fuego530;const href=destino(ruta);const badge=badges[i];return href?h('a',{href,title:`${i+1}. ${t} · ${badge.detalle}`,'aria-label':`${i+1}. ${t} · ${badge.detalle}`},`${i+1}. ${etiquetasPasos433[i]}`,h('span',{class:`paso-badge433 ${badge.estado}`,'aria-hidden':'true'},badge.valor)):h('span',{title:`${i+1}. ${t} · sin acceso`,'aria-label':`${i+1}. ${t} · sin acceso`},`${i+1}. ${etiquetasPasos433[i]} · sin acceso`);}))),h('details',{},h('summary',{},'Lo primero hoy · hasta5 señales de la copia'),h('ol',{},m.prioridades.map(p=>h('li',{},h('a',{href:destino('hoy')||'#/alertas'},p.titulo||p.texto))))),h('details',{on:{toggle:()=>{if(!vivo()||!horasVigentes517())root.replaceChildren();}}},h('summary',{},'Fuentes y alcance de los once indicadores'),h('ul',{},m.indicadores.map(x=>h('li',{},h('b',{},x.etiqueta+' · '),x.detalle))),h('p',{},'El avance requiere registros locales de hoy con denominador conocido; una lista vacía no acredita100%.'),h('p',{},m.cobertura)));
 if(scope530){try{const D=await ctx.api('produccion/urgencias-observadas');if(!vigente530()){root.replaceChildren();return;}pintarFuego530(proyectarUrgencias406(ctx,D,scope530));}catch{if(!vigente530())root.replaceChildren();else pintarFuego530(null);}}
}
