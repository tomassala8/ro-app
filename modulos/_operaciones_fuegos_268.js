import {ambitoFuegos341,horasFuego341} from './_horas_fuegos_341.js';
import {h,chipEstado} from '../componentes.js';
import {panelPlanFuego255} from './_plan_fuego_255.js';
import {metricasProyectoBaseline} from './_produccion_baseline.js';
import {semanticaMeta285} from './_meta_semantica_285.js';
import {accountFuego346,firmaAccountFuegos346} from './_account_fuegos_346.js';
import {cabeceraOperaciones423} from './_cabeceras_operaciones_423.js';

export const METRICAS_FUEGOS_268=['Leads Meta · 30 días','Gasto Meta · 30 días','Coste por lead · muestra','Anuncios nuevos · 30 días','Reuniones del mes anterior','Último correo nuestro','Días sin contestar','% horas vs pautadas','Tareas en revisión','Outreach · enviados','Outreach · respuestas','Outreach · leads'];
const numero=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0;
function unica(rows,id){const r=(Array.isArray(rows)?rows:[]).filter(x=>x?.cliente_id===id);return r.length===1?r[0]:null;}
export function muestraMeta30Fuego268(c,ventanas,cliente={},hoy) {
  const fin=ventanas?.serie?.[1];if(!/^\d{4}-\d{2}-\d{2}$/.test(fin||''))return null;
  const d=new Date(fin+'T00:00:00Z');if(!Number.isFinite(+d)||d.toISOString().slice(0,10)!==fin)return null;d.setUTCDate(d.getUTCDate()-29);const desde=d.toISOString().slice(0,10);
  const rows=(Array.isArray(c?.serie)?c.serie:[]).filter(r=>{
    if(!r||typeof r.d!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(r.d)||r.d<desde||r.d>fin)return false;
    const fecha=new Date(r.d+'T00:00:00Z');return Number.isFinite(+fecha)&&fecha.toISOString().slice(0,10)===r.d;
  });const keys=new Set();
  for(const r of rows){if(keys.has(r.d))return null;keys.add(r.d);}
  const semantica=semanticaMeta285(rows,cliente,hoy);
  // Ambos componentes del ratio deben ser campos acreditados de las mismas filas/ventana.
  const gastoAcreditado=semantica.eventos_lead_acreditados&&rows.every(r=>r.medicion.campos_observados.includes('gasto')&&numero(r.gasto_meta));
  const sum=(campo,conCeros=false,entero=false)=>{const ns=rows.map(r=>r[campo]).filter(v=>numero(v)&&(!entero||Number.isSafeInteger(v))&&(v>0||conCeros));const n=ns.reduce((a,b)=>a+b,0);return ns.length&&numero(n)&&(!entero||Number.isSafeInteger(n))?n:null;};
  const resultados=sum('leads_meta',semantica.eventos_lead_acreditados,true);
  const leads=semantica.eventos_lead_acreditados?resultados:null;
  const gasto=sum('gasto_meta',gastoAcreditado);
  const cpl=gastoAcreditado&&numero(gasto)&&numero(leads)&&leads>0?gasto/leads:null;
  return {desde,hasta:fin,gasto,resultados,leads,cpl:numero(cpl)?cpl:null,semantica,
    cpl_acreditado:gastoAcreditado&&numero(cpl),cobertura:'parcial',dias:keys.size};
}
export function motivoFuego268(v) {
  const text=x=>typeof x==='string'&&x.trim()?x.trim():null;
  const principal=text(v?.motivo);if(principal)return principal;
  for(const m of Array.isArray(v?.motivos)?v.motivos:[]){const t=text(m)||text(m?.texto);if(t)return t;}
  return 'Consulta las señales del cliente';
}
export async function renderFuegos268(cont,ctx,restantes=[]) {
  if(restantes.length){const mod=await import('./en_rojo.js');await mod.default.render(cont,{...ctx,params:restantes});return;}
  const principal=cont,inicial=ambitoFuegos341(ctx),firmaAccount=firmaAccountFuegos346(ctx);if(!inicial||firmaAccount===null)return;
  const raiz=h('div',{'data-fuegos-raiz':'341'});principal.append(raiz);cont=raiz;
  cont.append(h('style',{},`
    [data-fuegos-macro="310"] th,[data-fuegos-macro="310"] td{padding:6px!important;line-height:1.35;vertical-align:middle}
    [data-fuegos-macro="310"] thead th{white-space:normal!important;min-width:86px;max-width:125px}
    [data-fuegos-macro="310"] tbody th{min-width:172px;max-width:190px;z-index:1}
    [data-fuegos-macro="310"] tbody th>div{flex-wrap:wrap;gap:4px!important}
    [data-fuegos-macro="310"] tbody td:nth-child(2){white-space:normal!important;min-width:110px;max-width:145px}
    [data-fuegos-macro="310"] tbody td:nth-child(3) span{max-width:155px!important}
    [data-fuegos-macro="310"] button{min-height:32px}
  `));
  const vigente=()=>{const actual=ambitoFuegos341(ctx),ok=cont.isConnected&&actual?.firma===inicial.firma&&firmaAccountFuegos346(ctx)===firmaAccount;if(!ok)cont.replaceChildren();return ok;};
  const cargar=async(mod,ruta)=>{if(!vigente()||!ctx.veModulo(mod))return null;try{const d=await ctx.datosModulo(ruta);return vigente()?d:null;}catch{return null;}};
  const [C,P,PAUTA]=await Promise.all([cargar('captacion','captacion/captacion'),cargar('produccion','produccion/produccion'),inicial.pautas.length?cargar('dinero-cliente','dinero_cliente/dinero_cliente'):null]);if(!vigente())return;
  const clientes=inicial.clientes.filter(c=>ctx.verdad(c.id)?.gravedad==='critico');
  cont.append(h('p',{class:'sub'},'Todos los clientes críticos en una tabla. Desplázala horizontalmente para ver las doce métricas; abre el detalle de un cliente para consultar o registrar su plan.'));
  const fmt=v=>numero(v)?new Intl.NumberFormat('es-ES',{maximumFractionDigits:2}).format(v):'—';
  const filas=h('tbody',{});
  const cabeceras=['Cliente','Account','Motivo',...METRICAS_FUEGOS_268.map((x,i)=>i===0?'Meta · eventos / resultados · 30 días':x),'Plan y revisión'];
  const breves=['Cliente','Account','Motivo','Meta 30d','Gasto 30d','CPL','Anuncios 30d','Reu. mes ant.','Últ. correo','Espera días','% pauta','Revisión','Out. env.','Out. resp.','Out. leads','Plan'];
  if(clientes.length)cont.append(h('div',{class:'panel',style:{overflowX:'auto'},role:'region','aria-label':'Todos los fuegos de un vistazo',tabindex:'0'},
    h('table',{'data-fuegos-macro':'310',style:{width:'100%',borderCollapse:'collapse',fontSize:'12px'}},
      h('thead',{},h('tr',{},cabeceras.map((x,i)=>{const c=cabeceraOperaciones423(x);return h('th',{scope:'col',title:c.completo,'aria-label':c.completo,style:{padding:'8px',textAlign:'left',whiteSpace:'normal'}},c.breve===x?breves[i]:c.breve);}))),filas)),
    h('p',{class:'sub','data-leyenda-horas':'478'},'% pauta compara horas observadas con la pauta económica autorizada del mismo mes, como referencia; no acredita presupuesto, capacidad ni cumplimiento contractual. Sin porcentaje, se muestran sólo las horas observadas. ≥ indica mínimo observado; —, falta de evidencia compatible. Periodo y cobertura en el detalle.'));
  const detalleGrupo=h('section',{'aria-label':'Detalle y planes por cliente'});
  cont.append(detalleGrupo);
  for(const c of clientes){const v=ctx.verdad(c.id),paid=unica(C?.clientes,c.id),proy=unica(P?.proyectos,c.id),m=muestraMeta30Fuego268(paid,C?.ventanas,c,ctx.hoy),pr=proy?metricasProyectoBaseline(proy,P):null;
    const account=accountFuego346(ctx,c);
    const horas=horasFuego341(ctx,P,PAUTA,c.id);
    const rev=[pr?.account?.valor,pr?.tecnica?.valor].filter(numero);const revision=rev.length?rev.reduce((a,b)=>a+b,0):null;
    const vals=[m?.resultados!=null?`≥${fmt(m.resultados)}`:'—',m?.gasto!=null?`≥${fmt(m.gasto)} €`:'—',m?.cpl!=null?`${fmt(m.cpl)} €`:'—','—','—','—',numero(v.correos_sin_responder_dias)?fmt(v.correos_sin_responder_dias):'—',horas?.porcentaje!=null?`≥${fmt(horas.porcentaje)} %`:horas?`${fmt(horas.horas)} h`:'—',revision!=null?`≥${fmt(revision)}`:'—','—','—','—'];
    const fuenteMeta=m?`${m.desde} → ${m.hasta}; ${m.dias} días presentes en copia parcial.`:'Sin serie compatible autorizada.';
    const details=[fuenteMeta+' '+(m?.semantica.detalle||'Definición pendiente.'),fuenteMeta+' Gasto observado en esta copia.',fuenteMeta+(m?.cpl_acreditado?' Gasto por evento lead Meta de la misma muestra; no contacto único ni cualificación.':' Falta acreditar evento lead y gasto en la misma muestra; no se calcula CPL.'),'La copia no acredita fecha de creación de cada anuncio.','Pendiente de evidencia de celebración del mes anterior.','No hay evento saliente exacto acreditado en este DTO.','Días laborables de espera de la verdad única.',horas?.detalle||'Requiere horas y pauta autorizadas del mismo periodo.','Revisiones account y técnica observadas en la copia.','Sin eventos de outreach canónicos compatibles.','Sin eventos de outreach canónicos compatibles.','Sin eventos de outreach canónicos compatibles.'];
    const enlaceDetalle=`fuego-detalle-${clientes.indexOf(c)}`;
    filas.append(h('tr',{style:{borderTop:'1px solid #eceef7'}},
      h('th',{scope:'row',style:{padding:'8px',textAlign:'left',whiteSpace:'nowrap',position:'sticky',left:'0',background:'#fff'}},h('div',{style:{display:'flex',gap:'8px',alignItems:'center'}},h('a',{href:`#/operaciones/rojos/${c.id}`,on:{click:e=>{if(!vigente())e.preventDefault();}}},c.nombre),chipEstado('rojo','Crítico'))),
      h('td',{style:{padding:'8px',whiteSpace:'nowrap'}},account.texto),
      h('td',{title:motivoFuego268(v),style:{padding:'8px'}},h('span',{style:{display:'block',maxWidth:'220px',whiteSpace:'nowrap',overflow:'hidden',textOverflow:'ellipsis'}},motivoFuego268(v))),
      vals.map((valor,i)=>h('td',{title:details[i],'aria-label':`${cabeceras[i+3]}: ${valor}. ${details[i]}`,style:{padding:'8px',whiteSpace:'nowrap',color:valor==='—'?'#9298ac':'inherit'}},i===7&&horas?.porcentaje!=null?chipEstado(horas.estado,valor):i===6&&numero(v.correos_sin_responder_dias)&&v.correos_sin_responder_dias>2?chipEstado('rojo',valor):valor)),
      h('td',{style:{padding:'8px',whiteSpace:'nowrap'}},h('button',{type:'button',class:'bt mini',on:{click:()=>{
        if(!vigente())return;
        const d=detalleGrupo.querySelector?.(`#${enlaceDetalle}`);if(d){d.open=true;d.scrollIntoView({block:'start',behavior:'smooth'});}
      }}},'Ver plan'))));
    const art=h('article',{class:'panel',style:{padding:'14px 18px'}},
      h('div',{style:{display:'flex',flexWrap:'wrap',gap:'10px',alignItems:'center'}},h('h2',{style:{fontSize:'15px',margin:'0'}},h('a',{href:`#/operaciones/rojos/${c.id}`,on:{click:e=>{if(!vigente())e.preventDefault();}}},c.nombre)),chipEstado('rojo','Crítico'),h('span',{class:'sub'},account.texto)),
      h('p',{style:{fontSize:'13px',margin:'8px 0 12px'}},h('strong',{},'Motivo: '),motivoFuego268(v)),
      h('div',{style:{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(145px,1fr))',gap:'8px',marginBottom:'12px'}},METRICAS_FUEGOS_268.map((label,i)=>h('div',{title:details[i],style:{border:'1px solid #eceef7',borderRadius:'8px',padding:'8px 10px'}},h('strong',{style:{display:'block',fontSize:'17px',color:vals[i]==='—'?'#9298ac':'inherit'}},vals[i]),h('span',{style:{fontSize:'11px',color:'#777d9b'}},i===0&&m&&!m.semantica.eventos_lead_acreditados?'Resultados Meta · 30 días':label)))),
      h('p',{class:'sub'},m?`Meta ${m.desde} → ${m.hasta}: copia parcial; ≥ es el mínimo observado. ${m.semantica.detalle} ${m.cpl_acreditado?'Coste por evento lead de esta muestra.':'CPL sin acreditar.'} — indica falta de evidencia compatible.`:'Sin serie Meta autorizada compatible; — indica falta de evidencia, no cero.'),
      panelPlanFuego255(ctx,c.id));
    detalleGrupo.append(h('details',{id:enlaceDetalle,on:{toggle:()=>vigente()},style:{marginTop:'8px'}},h('summary',{style:{cursor:'pointer',padding:'12px',minHeight:'44px'}},c.nombre,' · métricas, motivo y plan'),art));
  }
  if(!clientes.length)cont.append(h('p',{},'Sin clientes críticos en la cartera autorizada.'));
}
