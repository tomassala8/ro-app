import { h, vacio } from '../componentes.js';
import { CONTADORES_ORIGINALES311, iniciarBadges311 } from './_badges_operaciones_311.js';
import { plegarConsejo } from './_plegar_consejo.js';

// Orden de navegación del artifact original (ORD), sin reducir sus 17 apartados.
export const APARTADOS_OPERACIONES = [
  ['dia','Mi día','mi-dia','mi_dia'],
  ['bandeja','Bandeja','bandeja','bandeja'],
  ['equipo','Equipo y horas','horas','horas'],
  ['produccion','Producción','produccion','produccion'],
  ['fuegos','Fuegos','produccion','produccion'],
  ['rojos','En rojo y planes','en-rojo','en_rojo'],
  ['fichas','Fichas de clientes','ficha','ficha'],
  ['clientes','Clientes','mi-dia','mi_dia'],
  ['nuevos','Clientes nuevos','clientes-nuevos','nuevos'],
  ['accounts','Accounts','mi-dia','mi_dia'],
  ['puesto','Mi puesto','mi-perfil','mi_perfil'],
  ['tomas','Para Tomás','decisiones','decisiones'],
  ['cierre','Cierre de septiembre','dinero-cliente','dinero_cliente'],
  ['rastro','Rastro','decisiones','decisiones'],
  ['hoy','Todas las alarmas','alertas','alertas'],
  ['viernes','Viernes a cero','produccion','produccion'],
  ['incongruencias','Sin dueño','incidencias','incidencias'],
  ['repartir','Para repartir','produccion','produccion'],
];
export const GRUPOS_OPERACIONES = [['Hoy',['dia','bandeja']],['Equipo',['equipo','produccion']],['Clientes',['fuegos','rojos','fichas','clientes','nuevos','accounts']],['Dirección',['puesto','tomas','cierre','rastro']],['Más',['hoy','viernes','incongruencias','repartir']]];
export const BLOQUES_EQUIPO_ORIGINAL = ['equipo-dia','alerta-personas','horas','anomalias','tipos-tarea','notas'];
export const puestos_que_lo_ven = { direccion:'todo', operaciones:'todo', account:'suyo' };

export function apartadosAutorizados(ctx) {
  if (!ctx || !ctx.persona || !ctx.veModulo) return [];
  if (!(ctx.persona.puestos || []).some(p=>['direccion','operaciones','account'].includes(p))) return [];
  return APARTADOS_OPERACIONES.filter(a=>ctx.veModulo(a[2]));
}

export default {
  id:'operaciones', titulo:'Dirección de operaciones', grupo:'Operaciones', puestos_que_lo_ven,
  async render(cont,ctx) {
    const lista=apartadosAutorizados(ctx);
    if (!lista.length) { cont.append(vacio({titulo:'Sin panel autorizado',texto:'No hay apartados disponibles para esta sesión.'})); return; }
    const actual=lista.find(a=>a[0]===ctx.params?.[0]) || lista[0];
    const [clave,titulo,id,fichero]=actual;
    const propia=(ctx.persona.puestos || []).includes('account') && !(ctx.persona.puestos || []).some(p=>['direccion','operaciones'].includes(p));
    const identidad311=JSON.stringify([ctx.real?.id,ctx.persona?.id]);
    const vigente=()=>identidad311===JSON.stringify([ctx.real?.id,ctx.persona?.id])&&cont.isConnected && (typeof ctx.vigente!=='function' || ctx.vigente());
    const badges311=new Map(),labels311=new Map();
    const badge311=a=>{if(!CONTADORES_ORIGINALES311.includes(a[0]))return null;const el=h('span',{'data-ops-contador':a[0],style:{marginLeft:'6px',padding:'0 5px',borderRadius:'99px',fontSize:'11px',background:'var(--muted-soft,#eceef7)',color:'var(--muted,#777d9b)'},title:'Contador pendiente de fuente compatible; no equivale a cero.'},'—');badges311.set(a[0],el);return el;};
    const nav=h('nav',{'aria-label':propia?'Control de mis proyectos':'Apartados de dirección de operaciones',class:'ops-apartados'}, GRUPOS_OPERACIONES.map(([grupo,claves])=>h('div',{role:'group','aria-label':grupo,style:{display:'flex',flexWrap:'wrap',gap:'2px',alignItems:'center'}},h('span',{style:{fontSize:'10px',color:'var(--muted,#777d9b)',fontWeight:'700',padding:'0 4px'}},grupo),lista.filter(a=>claves.includes(a[0])).map(a=>h('a',{
      href:`#/operaciones/${a[0]}`, 'aria-current':a[0]===clave?'page':null,
      style:{display:'inline-flex',alignItems:'center',minHeight:'44px',padding:'6px 12px',boxSizing:'border-box',borderRadius:'8px',fontWeight:a[0]===clave?'700':'500',background:a[0]===clave?'var(--accent-soft,#e9ecff)':'transparent',color:'inherit',textDecoration:'none'}
    },a[1],badge311(a))))));
    nav.style.cssText='display:flex;flex-wrap:wrap;gap:4px;border-bottom:1px solid var(--borde,#e1e4f1);padding-bottom:10px;margin-bottom:14px';
    const cuerpo=h('div',{'data-operaciones-apartado':clave});
    const selectorMovil=h('select',{'aria-label':'Apartado de operaciones',on:{change:e=>{if(vigente()&&lista.some(a=>a[0]===e.target.value))ctx.navegar(`operaciones/${e.target.value}`);}}},lista.map(a=>h('option',{value:a[0],selected:a[0]===clave},a[1])));
    selectorMovil.value=clave;
    for(const op of selectorMovil.options||selectorMovil.children||[])labels311.set(op.value||op.getAttribute?.('value'),op);
    cont.append(h('style',{},'.ops-navegacion-desktop{margin-bottom:12px}.ops-navegacion-desktop>summary{min-height:44px;padding:12px;box-sizing:border-box;cursor:pointer;border:1px solid var(--line,#e1e4f1);border-radius:8px;background:var(--card,#fff)}.ops-navegacion-desktop[open]>summary{margin-bottom:10px}.ops-selector-movil{display:none}@media(max-width:600px){.ops-navegacion-desktop{display:none}.ops-apartados{display:none!important}.ops-selector-movil{display:flex;align-items:center;gap:10px;margin:0 0 14px}.ops-selector-movil select{min-width:0;flex:1;min-height:44px;padding:8px 12px;font:inherit;color:inherit;border:1px solid var(--line,#e1e4f1);border-radius:8px;background:var(--card,#fff)}.ops-selector-movil select:focus-visible{outline:2px solid var(--accent,#6366f1);outline-offset:2px}}'),h('details',{class:'ops-navegacion-desktop'},h('summary',{},`Cambiar apartado · ${titulo}`),nav),h('label',{class:'ops-selector-movil'},'Vista',selectorMovil),cuerpo);
    const pintarBadges311=datos=>{for(const a of lista){const d=ctx.veModulo(a[2])?datos[a[0]]:null,el=badges311.get(a[0]);if(el){el.replaceChildren(d?.texto||'—');el.setAttribute('title',d?.detalle||'Contador no disponible en el ámbito actual.');el.setAttribute('aria-label',`${a[1]}: ${d?.texto||'sin dato'}. ${d?.detalle||'Ámbito cambiado; confirmar fuente.'}`);}const op=labels311.get(a[0]);if(op)op.textContent=a[1]+(d?.valor!=null?` (${d.texto})`:'');}};
    const conteos311=iniciarBadges311(ctx,{vigente,pintar:pintarBadges311});
    const navegacion311=nav.parentNode;
    navegacion311?.addEventListener('toggle',()=>conteos311.actualizar());
    selectorMovil.addEventListener('focus',()=>conteos311.actualizar());
    ctx.titulo(propia?'Control de mis proyectos':'Dirección de operaciones',titulo);
    plegarConsejo(cont,{despues:true});
    const restantes=(ctx.params || []).slice(1);
    let params=restantes;
    if ((clave==='accounts'||clave==='clientes') && !restantes.length) params=['control-cartera',propia?'account':'operaciones'];
    if (clave==='cierre' && !restantes.length) params=['cierre-septiembre'];
    if(clave==='rastro' && !restantes.length) params=['rastro'];
    const hijo={...ctx,params,vigente,operacionesVista:clave==='produccion'?'proyectos':undefined,
      titulo:(_,sub)=>{if(vigente())ctx.titulo(propia?'Control de mis proyectos':'Dirección de operaciones',`${titulo}${sub?' · '+sub:''}`);},
      navegar:ruta=>{if(!vigente())return;const [mod,...p]=ruta.split('/');ctx.navegar(mod===id?`operaciones/${clave}/${p.join('/')}`:ruta);}
    };
    try {
      if(['fichas','nuevos'].includes(clave) && !restantes.length) {
        const clientes=await import('./_operaciones_fichas_nuevos_271.js');
        if(vigente() && ctx.veModulo(id))await clientes.renderFichasNuevos271(cuerpo,hijo,clave,restantes);
        return;
      }
      if(clave==='incongruencias' && !propia) {
        const incidencias=await import('./_operaciones_incongruencias_278.js');
        if(vigente() && ctx.veModulo(id))await incidencias.renderIncongruencias278(cuerpo,hijo);
        return;
      }
      if(clave==='bandeja') {
        const bandeja=await import('./_operaciones_bandeja_270.js');
        if(vigente() && ctx.veModulo(id))await bandeja.renderBandeja270(cuerpo,hijo,restantes);
        return;
      }
      if(['dia','tomas','rastro'].includes(clave) && !propia) {
        const direccion=await import('./_operaciones_dia_direccion_265.js');
        if(vigente() && ctx.veModulo(id)) await direccion.renderDiaDireccion265(cuerpo,hijo,clave);
        return;
      }
      if(['accounts','clientes','hoy'].includes(clave)) {
        const accounts=await import('./_operaciones_accounts_263.js');
        if(vigente() && ctx.veModulo(id)) await accounts.renderAccounts263(cuerpo,hijo,clave);
        return;
      }
      if(clave==='fuegos') {
        const urgencias=await import('./_operaciones_urgencias_406.js');
        if(vigente() && ctx.veModulo(id)) await urgencias.renderUrgencias406(cuerpo,hijo);
        return;
      }
      if(clave==='rojos') {
        const fuegos=await import('./_operaciones_fuegos_268.js');
        if(vigente() && ctx.veModulo(id)) await fuegos.renderFuegos268(cuerpo,hijo,restantes);
        return;
      }
      if(clave==='equipo') {
        const equipo=await import('./_operaciones_equipo_262.js');
        if(!vigente() || !ctx.veModulo(id))return;
        const elegida=restantes[0]||'resumen';
        const opciones=[['resumen','Vista completa'],['equipo-dia','Día a día'],['horas','Horas'],['alerta-personas','Alertas de equipo'],['anomalias','Horas para revisar'],['tipos-tarea','Tipos de tarea'],['notas','Notas del equipo'],['planificacion','Planificación']];
        cuerpo.append(h('nav',{'aria-label':'Vistas de equipo y horas',style:{display:'flex',flexWrap:'wrap',gap:'8px',marginBottom:'12px'}},opciones.filter(a=>a[0]!=='alerta-personas'||ctx.veModulo('personas')).map(a=>h('a',{href:`#/operaciones/equipo/${a[0]}`,class:'bt mini','aria-current':elegida===a[0]?'page':null},a[1]))));
        if(elegida==='resumen') {
          // Orden completo original, con puertas propias por bloque y errores aislados.
          const bloques=BLOQUES_EQUIPO_ORIGINAL.filter(k=>k!=='alerta-personas'||ctx.veModulo('personas')).map(k=>({k,el:h('section',{'data-equipo-bloque':k})}));
          cuerpo.append(...bloques.map(b=>b.el));
          await Promise.all(bloques.map(async b=>{try{if(vigente()&&ctx.veModulo(id))await equipo.renderEquipo262(b.el,hijo,b.k);}catch{if(vigente())b.el.append(vacio({titulo:'Datos de esta sección no disponibles',texto:'Puedes consultar las demás secciones del equipo.'}));}}));
        } else await equipo.renderEquipo262(cuerpo,hijo,elegida);
        return;
      }
      if(['puesto','viernes','repartir'].includes(clave)) {
        const ritual=await import('./_operaciones_rituales_264.js');
        if(vigente() && ctx.veModulo(id)) await ritual.renderRituales264(cuerpo,hijo,clave);
        return;
      }
      // Helpers de recuperación especializados se integran aquí por apartado; los módulos
      // actuales mantienen sus propias puertas y reciben exclusivamente DTO recortados.
      const modulo=await import(`./${fichero}.js`);
      if (!vigente() || !ctx.veModulo(id)) return;
      await modulo.default.render(cuerpo,hijo);
    } catch(e) {
      if(vigente())cuerpo.append(vacio({titulo:'No se ha podido abrir este apartado',texto:e?.message || 'Comprueba el estado de sus datos.'}));
    }
  }
};
