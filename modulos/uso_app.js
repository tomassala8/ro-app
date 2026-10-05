import { MODULOS } from './indice.js';
import {h,panel,tiles,tile,tablaApilable,fmt,vacioLinea} from '../componentes.js';
export function agruparUso(filas, incluirRevision=false) {
  const reales=filas.filter(f=>incluirRevision || f.actor===f.visto);
  const pantallas=new Map(), personas=new Map(), controles=new Map();
  for (const f of reales) {
    const sumar=(map,k)=>{if(!map.has(k))map.set(k,{id:k,activo_ms:0,aperturas:0,interacciones:0,errores:0});const x=map.get(k);x.activo_ms+=f.activo_ms||0;x.aperturas+=f.accion==='abrir'?f.eventos:0;x.interacciones+=f.accion==='interaccion'?f.eventos:0;x.errores+=f.accion==='error'?f.eventos:0;};
    sumar(pantallas,f.pantalla);sumar(personas,f.actor);sumar(controles,f.control);
  }
  return {pantallas:[...pantallas.values()].sort((a,b)=>a.id.localeCompare(b.id)),personas:[...personas.values()].sort((a,b)=>a.id.localeCompare(b.id)),controles:[...controles.values()].sort((a,b)=>a.id.localeCompare(b.id))};
}
const tiempo=n=>n>=60000?`${fmt.num(n/60000,1)} min`:`${Math.floor(n/1000)} s`;
const CONTROL={'copiar-ia':'Copiar instrucciones para IA','preparar-ia':'Preparar tarea con IA','abrir-tarea':'Abrir una tarea',boton:'Botones',enlace:'Enlaces',pestana:'Pestañas',filtro:'Filtros',campo:'Campos',guardar:'Guardado',buscar:'Buscador',menu:'Menú',periodo:'Periodo',volver:'Volver',exportar:'Exportar','cambiar-vista':'Cambiar vista',ninguno:'Sin control'};
export default {
  id:'uso-app', titulo:'Uso y mejoras', grupo:'Equipo', puestos_que_lo_ven:{direccion:'todo',operaciones:'todo'},
  async render(cont,ctx) {
    ctx.titulo('Uso y mejoras','Detectar qué facilita el trabajo y dónde cuesta avanzar');
    if(!ctx.servidor){cont.append(vacioLinea('La medición necesita el servidor de la app.'));return;}
    let dias=7,revision=false,carga=0;
    const barra=h('div',{class:'fila',style:{flexWrap:'wrap',gap:'var(--s-3)'}},h('label',{},'Periodo ',h('select',{'aria-label':'Periodo de uso',on:{change:e=>{dias=Number(e.target.value);pintar();}}},h('option',{value:7},'Últimos 7 días'),h('option',{value:30},'Últimos 30 días'))),h('label',{class:'fila'},h('input',{type:'checkbox',on:{change:e=>{revision=e.target.checked;pintar();}}}),'Incluir revisiones en «ver como»'));
    const cuerpo=h('div',{class:'pila'});cont.append(barra,cuerpo);
    async function pintar(){
      const token=++carga;cuerpo.replaceChildren(vacioLinea('Leyendo el uso de la app…'));
      try {
        const r=await ctx.api(`uso?dias=${dias}`);
        if(token!==carga || !cont.isConnected)return;
        const g=agruparUso(r.filas||[],revision);g.personas.sort((a,b)=>ctx.nombre(a.id).localeCompare(ctx.nombre(b.id),'es'));const suma=k=>g.pantallas.reduce((n,x)=>n+x[k],0);
        const nombres={app:'Entrada a la app',...Object.fromEntries(MODULOS.map(m=>[m.id,m.titulo]))};
        const tabla=(filas,nombre)=>tablaApilable({filas,columnas:[{clave:'id',titulo:nombre,principal:true,celda:x=>nombre==='Persona'?ctx.nombre(x.id):(nombres[x.id]||x.id)},{clave:'activo_ms',titulo:'Tiempo activo',num:true,celda:x=>tiempo(x.activo_ms)},{clave:'aperturas',titulo:'Aperturas',num:true},{clave:'interacciones',titulo:'Interacciones',num:true},{clave:'errores',titulo:'Errores al guardar o cargar',num:true}]});
        cuerpo.replaceChildren(h('p',{class:'sub'},'Uso de pantallas y acciones; la pestaña abierta sin interacción deja de sumar tiempo. Más información en Mi perfil.'),tiles([tile({etiqueta:'Personas que entraron',valor:g.personas.length,icono:'users'}),tile({etiqueta:'Tiempo activo en la app',valor:tiempo(suma('activo_ms')),icono:'clock'}),tile({etiqueta:'Interacciones',valor:fmt.num(suma('interacciones')),icono:'ok'}),tile({etiqueta:'Errores detectados',valor:fmt.num(suma('errores')),icono:'alert'})]),
          panel({titulo:'Por pantalla',sub:'Una apertura cuenta al entrar en una pantalla. La actividad reciente cuenta; dejar la pestaña abierta no.'},h('div',{class:'cuerpo'},g.pantallas.length?tabla(g.pantallas,'Pantalla'):vacioLinea('Todavía no hay uso registrado en este periodo.'))),
          panel({titulo:'Acciones que se utilizan',sub:'Categorías de controles. No se guarda el contenido de las tareas ni lo escrito.'},h('div',{class:'cuerpo'},tablaApilable({filas:g.controles.filter(x=>x.interacciones||x.errores),columnas:[{clave:'id',titulo:'Acción',principal:true,celda:x=>CONTROL[x.id]||'Control'},{clave:'interacciones',titulo:'Interacciones',num:true},{clave:'errores',titulo:'Errores',num:true}]}))),
          panel({titulo:'Uso del equipo',sub:'Orden alfabético. Sirve para acompañar la adopción y mejorar la herramienta.'},h('div',{class:'cuerpo'},tabla(g.personas,'Persona'))),h('p',{class:'sub'},r.limites),h('p',{class:'sub'},r.aviso),h('p',{class:'sub'},'Los mapas de calor y las grabaciones de Clarity no están activados. Esta vista usa únicamente medición propia.'));
      }catch(e){if(token===carga)cuerpo.replaceChildren(vacioLinea(e.status===403?'Esta vista solo está disponible para dirección y operaciones en su propia sesión.':`No se pudo leer el uso: ${e.message}`,{icono:'alert'}));}
    }
    await pintar();
  }
};
