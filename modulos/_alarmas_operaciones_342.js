import {modeloTop388} from './_top_alarmas_388.js';
import {crearMensajeAlarma345} from './_mensaje_alarma_345.js';
//342 · Colección de alertas ya autorizada. No reconstruye KPI ni escribe estados.
import {h,chipEstado} from '../componentes.js';
const arr=x=>Array.isArray(x)?x:[];
const id=x=>typeof x==='string'&&x.length>0&&x.length<=300;
const activo=p=>p?.estado==='activo'&&p.activo!==false;
// Nombres del catálogo local REGLAS: sólo presentación, no copia de sus umbrales.
const etiquetasTipo={"web_caida":"Web caída","web_spam":"Enlaces de spam en la web","web_certificado":"Certificado que caduca","web_lenta":"Web lenta","web_medicion":"Fallo de medición de Analytics","modular_caida":"Web caída (Modular)","modular_copia":"Copia de seguridad atrasada (Modular)","modular_vulnerabilidad":"Vulnerabilidad crítica en la web (Modular)","modular_certificado":"Certificado a punto de caducar (Modular)","web_hosting":"Incidencia del hosting (Hostinger)","seo_rojo":"Posiciones fuera del top 10 o caída de clics","seo_ambar":"SEO a vigilar","gbp_resena":"Reseña de 1-3 estrellas sin responder (ficha de Google)","gbp_caida":"Caída de llamadas o rutas desde la ficha de Google","gbp_perfil":"Ficha de Google suspendida, sin control o cambiada por Google","crm_sin_tocar":"Leads sin tocar más de 24 h","crm_citas_sin_estado":"Citas sin estado","crm_sin_usar":"Subcuenta sin usar","crm_whatsapp":"WhatsApp que falla","pub_critico":"Captación en crítico","pub_atencion":"Captación a vigilar","pub_cuenta":"Cuenta publicitaria parada","redes_hueco":"Hueco en los próximos 7 días","redes_fallida":"Publicación fallida o red desconectada","acc_critico":"Cliente en crítico","acc_correos":"Correos sin contestar más de 48 h","acc_llamadas":"Llamada sin devolver","acc_sin_reunion":"Sin reunión el mes pasado","acc_informe":"Informe mensual sin enviar el día 6","acc_sin_agente":"Ticket sin agente","acc_config":"Fallo de configuración de Desk o Zadarma","alta_fuera_plazo":"Alta fuera del día 12","alta_sin_lista":"Alta sin lista de arranque a las 48 h de la firma","adm_impago":"Factura vencida sin cobrar","adm_sepa":"Recibo SEPA devuelto","adm_sin_alta":"Firmado sin alta en facturación","rrhh_alerta":"Persona en alerta","rrhh_no_imputa":"No imputó horas ayer","rrhh_cumple":"Cumpleaños","rrhh_aniversario":"Aniversario de entrada","dir_decision":"Decisión con reloj","dir_sin_account":"Cliente sin account","hosting_cuenta":"Renovación o dominio de RO en Hostinger","hosting_vps":"Servidor (VPS) de Hostinger con problemas","conexion_caida":"Conexión caída o a punto de caducar"};
export const etiquetaTipoAlarma342=tipo=>Object.hasOwn(etiquetasTipo,tipo)?etiquetasTipo[tipo]:'Otro tipo de alarma';
const rolesIguales=(a,b)=>Array.isArray(a)&&Array.isArray(b)&&a.length>0&&a.every(x=>typeof x==='string'&&x.length>0)&&b.every(x=>typeof x==='string'&&x.length>0)&&new Set(a).size===a.length&&new Set(b).size===b.length&&JSON.stringify([...a].sort())===JSON.stringify([...b].sort());
const tx=x=>typeof x==='string'?x.slice(0,4000):'';
const dia=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T00:00Z'))&&new Date(x+'T00:00Z').toISOString().slice(0,10)===x;
const tonos={alta:'rojo',rojo:'rojo',critico:'rojo',media:'ambar',ambar:'ambar',amarillo:'ambar',baja:'gris',gris:'gris'};
export function ambitoAlarmas342(ctx){
 try{
  const ps=arr(ctx.datos?.personas),actores=[ctx.real,ctx.persona];
  if(!actores.every(p=>/^[a-zA-Z0-9_-]+$/.test(p?.id||''))||!ctx.servidor||!ctx.veModulo?.('alertas')||!dia(ctx.hoy)||typeof ctx.ver!=='function'||!actores.every(p=>id(p?.id)&&activo(p)&&ps.filter(x=>x?.id===p.id).length===1&&ps.some(x=>x.id===p.id&&activo(x)&&rolesIguales(p.puestos,x.puestos))))return null;
  const ops=actores.every(p=>arr(p.puestos).some(r=>['direccion','operaciones'].includes(r))&&arr(ps.find(x=>x.id===p.id).puestos).some(r=>['direccion','operaciones'].includes(r)));
  const propia=arr(ctx.persona?.puestos).includes('account')&&!arr(ctx.persona?.puestos).some(r=>['direccion','operaciones'].includes(r));
  const cartera=new Set(ctx.carteraPorSilla?.account||[]);
  const cs=arr(ctx.clientesVisibles).filter(c=>(!propia||cartera.has(c?.id))&&id(c?.id)&&arr(ctx.clientesVisibles).filter(x=>x?.id===c.id).length===1&&c.activo_confirmado===true&&c.detalle===true&&ctx.ver({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true);
  const personas=ps.filter(p=>id(p?.id)&&ps.filter(x=>x?.id===p.id).length===1&&activo(p)&&ctx.ver({tipo:'alarma_persona',persona_id:p.id})?.ok===true).map(p=>p.id);
  const clientes=cs.map(c=>c.id).sort(),detalle=clientes.filter(cid=>ctx.ver({tipo:'alarma_detalle',cliente_id:cid})?.ok===true);
  return {ops,clientes,personas,detalle,ruta:ops?'alertas/alertas':`alertas/p_${ctx.persona.id}`,firma:JSON.stringify([actores,ctx.hoy,ops,clientes,detalle,personas,ps,arr(ctx.datos?.asignaciones),cs.map(c=>c.equipo),[...(ctx.carteraPorSilla?.account||[])].sort()])};
 }catch{return null;}
}
export function proyectarAlarmas342(ctx,D,rows=[]){
 const scope=ambitoAlarmas342(ctx);if(!scope||!Array.isArray(D?.alertas))return null;
 const gen=typeof D.generado==='string'?D.generado: D._meta?.generado;
 if(!dia(gen?.slice(0,10))||gen.slice(0,10)>ctx.hoy||!Number.isFinite(Date.parse(gen.replace(' ','T'))))return null;
 const clientes=new Map(arr(ctx.clientesVisibles).map(c=>[c.id,c])),cuentas=new Map();for(const a of D.alertas)if(id(a?.id))cuentas.set(a.id,(cuentas.get(a.id)||0)+1);
 const owners=new Map();for(const r of rows)if(scope.clientes.includes(r?.cliente_id)){const rs=rows.filter(x=>x?.cliente_id===r.cliente_id),ps=arr(ctx.datos?.personas).filter(p=>p?.id===r.account_id);if(rs.length===1&&ps.length===1&&activo(ps[0]))owners.set(r.cliente_id,r.account_id);}
 const filas=[];for(const a of D.alertas){
  if(!id(a?.id)||cuentas.get(a.id)!==1||!id(a.tipo))continue;
  const cid=a.cliente_id,pid=a.persona_id;
  if(cid!=null&&(!id(cid)||!scope.clientes.includes(cid)))continue;
  if(pid!=null&&(!id(pid)||!scope.personas.includes(pid)))continue;
  if(!cid&&!scope.ops)continue;
  const detalle=!cid||scope.detalle.includes(cid),account_id=cid?owners.get(cid)||null:null;
  const ir=tx(a.ir||a.enlace);const ruta=/^#\/[a-z0-9_-]+(?:\/[a-zA-Z0-9_.%:-]+)*$/.test(ir)&&!ir.includes('..')&&!/%(?:2e|2f|5c)/i.test(ir)&&ctx.veModulo(ir.slice(2).split('/')[0])?ir:null;
  filas.push({id:a.id,cliente_id:cid||null,persona_id:pid||null,account_id,cliente:cid?(clientes.get(cid).nombre||cid):pid?ctx.nombre?.(pid)||'Persona autorizada':'Equipo',tipo:a.tipo,tipo_label:etiquetaTipoAlarma342(a.tipo),titulo:detalle?tx(a.titulo)||etiquetaTipoAlarma342(a.tipo):etiquetaTipoAlarma342(a.tipo),texto:detalle?tx(a.motivo||a.texto):'Detalle fuera del permiso actual.',gravedad:tonos[a.gravedad]||'gris',desde:tx(a.desde),ruta:detalle?ruta:null});
 }
 const orden={rojo:0,ambar:1,gris:2};filas.sort((a,b)=>orden[a.gravedad]-orden[b.gravedad]||a.cliente.localeCompare(b.cliente,'es')||a.id.localeCompare(b.id));
 return {filas,fecha:gen,cobertura:'parcial',scope};
}
export function pintarAlarmas342(cont,ctx,D,rows=[],vigente=()=>true){
 const inicial=ambitoAlarmas342(ctx),root=h('section',{'data-alarmas-completas':'342',class:'panel'});cont.append(root);
 const vivo=()=>root.isConnected&&vigente()&&!!inicial&&ambitoAlarmas342(ctx)?.firma===inicial.firma;
 const limpiar=()=>root.replaceChildren(h('p',{role:'status'},'La colección de alarmas no está disponible en el ámbito actual.'));
 if(!vivo()){limpiar();return root;}
 const modelo=proyectarAlarmas342(ctx,D,rows);
 if(!modelo){root.append(h('h2',{},'Todas las alarmas · colección'),h('p',{role:'status'},'Fuente no disponible o corte incompatible; las siete reglas anteriores se conservan. No se acredita una lista vacía.'));return root;}
 let account='',cliente='',tipo='',gravedad='';const zona=h('div',{});
 const select=(label,options,changed)=>h('label',{style:{display:'flex',flexDirection:'column',gap:'4px'}},label,h('select',{'aria-label':label,style:{minHeight:'44px'},on:{change:e=>{if(!vivo()){limpiar();return;}changed(e.target.value);pintar();}}},h('option',{value:''},'Todos'),options.map(([k,v])=>h('option',{value:k},v))));
 const accounts=[...new Set(modelo.filas.map(a=>a.account_id||'__sin'))].map(k=>[k,k==='__sin'?'Sin account confirmado':ctx.nombre?.(k)||k]);
 const clientes=[...new Set(modelo.filas.map(a=>a.cliente_id).filter(Boolean))].map(k=>[k,modelo.filas.find(a=>a.cliente_id===k).cliente]);
 const tipos=[...new Set(modelo.filas.map(a=>a.tipo))].map(k=>[k,etiquetaTipoAlarma342(k)]);
 const filtros=[select('Account de las alarmas',accounts,v=>account=v),select('Cliente de las alarmas',clientes,v=>cliente=v),select('Tipo de alarma',tipos,v=>tipo=v),select('Severidad de la alarma',[['rojo','Crítica'],['ambar','Vigilar'],['gris','Aviso / por confirmar']],v=>gravedad=v)];
 const reset=h('button',{type:'button',class:'bt',style:{minHeight:'44px'},on:{click:()=>{if(!vivo()){limpiar();return;}account=cliente=tipo=gravedad='';for(const l of filtros){const s=l.querySelector?.('select')||arr(l.children).find(x=>x?.tag==='select');if(s)s.value='';}pintar();}}},'Restablecer alarmas');
 root.append(h('h2',{},'Todas las alarmas · colección'),h('small',{},`Corte ${modelo.fecha} · ${modelo.filas.length} registros autorizados de la copia parcial; no inventario completo ni ausencia de incidencias.`),h('div',{style:{display:'flex',gap:'8px',flexWrap:'wrap',padding:'8px'}},filtros,reset),zona);
 const vigenteMensaje=()=>{if(!vivo()){limpiar();return false;}return true;};
 const fila=a=>h('li',{style:{padding:'8px',borderBottom:'1px solid #eceef7'}},h('div',{},chipEstado(a.gravedad,a.tipo_label),' ',h('strong',{},a.cliente),a.titulo===a.tipo_label?'':' · '+a.titulo),h('div',{},a.texto),h('small',{},a.desde?`Desde ${a.desde} · copia`:'Fecha del hecho sin confirmar'),a.ruta?h('a',{href:a.ruta,style:{marginLeft:'8px'},on:{click:e=>{if(!vivo()){e.preventDefault();limpiar();}}}},'Abrir origen'):null,a.cliente_id&&modelo.scope.detalle.includes(a.cliente_id)?crearMensajeAlarma345(h,ctx,()=>({...a,corte:modelo.fecha}),a.tipo_label,vigenteMensaje).elemento:null);
 function pintar(){if(!vivo()){limpiar();return;}const fs=modelo.filas.filter(a=>(!account||(a.account_id||'__sin')===account)&&(!cliente||a.cliente_id===cliente)&&(!tipo||a.tipo===tipo)&&(!gravedad||a.gravedad===gravedad));
 const top=modeloTop388(ctx,D,rows,{account,cliente,tipo,gravedad})?.top||[],idsTop=new Set(top.map(x=>x.id)),resto=fs.filter(x=>!idsTop.has(x.id));
 zona.replaceChildren(h('p',{},`${fs.length} registros visibles · ${modelo.filas.length} autorizados en esta copia`),fs.length?h('div',{},top.length?h('div',{},h('h3',{},'Lo primero · hasta 6 clientes'),h('ol',{},top.map(fila))):null,resto.length?h('details',{on:{toggle:()=>{if(!vivo())limpiar();}}},h('summary',{},`Resto de la colección · ${resto.length}`),h('ol',{start:top.length+1},resto.map(fila))):null):h('p',{},'Sin registros con estos filtros; no acredita que no existan alarmas.'));

 }
 pintar();return root;
}
