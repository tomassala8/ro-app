import { bloqueTareaIA } from './tarea_ia.js';
import { h, icono, vacioLinea } from '../componentes.js';
import { tarjetasUnicas, filtrarTarjetas, estadosDeLista, columnasDeLista, textoSincronia, puedeMover, gestorMovimientos } from './_tablero_tareas.js';

export default { id: 'tablero-tareas', titulo: 'Mi diario y daily', async render(cont, ctx) {
  ctx.titulo('Mi diario y daily', 'Elige Daily o inventario completo y usa los estados exactos de cada lista.');
  cont.replaceChildren(vacioLinea('Leyendo tareas y estados…', { icono: 'clock' }));
  if (!ctx.servidor) { cont.replaceChildren(vacioLinea('Este tablero necesita el servidor con permisos de la app.', { icono: 'candado' })); return; }
  const vigente = () => cont.isConnected && (typeof ctx.vigente !== 'function' || ctx.vigente());
  let datos;
  try { datos = await ctx.api('tareas/tablero'); }
  catch (e) { if (!vigente()) return; cont.replaceChildren(vacioLinea(`No se pudo leer el tablero: ${e?.message || e}`, { icono: 'alert' })); return; }
  if (!vigente()) return;
  const tareas = tarjetasUnicas(datos.tareas || []);
  for (const t of tareas) {
    const ultimos=(datos.cambios || []).filter(c=>String(c.tarea)===t.id && c.campo==='estado' && c.estado!=='descartado').sort((a,b)=>String(a.creado||'').localeCompare(String(b.creado||'')) || (a.id||0)-(b.id||0));
    const ultimo=ultimos.at(-1);
    if (!t.estado_app && ultimo && typeof ultimo.valor==='string') {t.estado_clickup=t.estado_clickup||t.estado;t.estado_app=ultimo.valor;t.cambio_estado=ultimo.estado;}
    if (t.sincronia?.estado) t.cambio_estado=t.sincronia.estado;
  }
  const nombres = Object.fromEntries((datos.personas || []).map(p => [p.id, p.nombre || p.id]));
  const yo = ctx.persona.id;
  let vista = 'mia', lista = '', asignado = '', cliente = '', buscar = '', proyecto = '', prioridad = '', etiqueta = '', preset = 'daily', arrastrada = null;
  let vistasGuardadas = [], vistaGuardadaId = '', nombreVista = '', mensajeVista = '', ocupadoVista = false, leyendoVistas = true;
  const vistasPanel = h('section', { 'aria-label': 'Vistas privadas guardadas', class: 'panel', style: { padding: 'var(--s-3)', minWidth: '0' } });
  const errores = new Map();
  const gestor = gestorMovimientos({ api: (...args) => ctx.api(...args), alCambiar: () => pintarColumnas() });
  const filtros = h('div', { class: 'pila', style: { gap: 'var(--s-2)' } });
  const aviso = h('p', { class: 'sub', role: 'status', style: { margin: '0' } });
  const columnas = h('div', { style: { minWidth: '0' } });
  const seleccionar = (etiqueta, opciones, valor, cambiar, todos = 'Todos') => {
    const select = h('select', { 'aria-label': etiqueta, style: { minHeight: '44px', maxWidth: '100%', minWidth: '0' }, on: { change: e => cambiar(e.target.value) } },
      h('option', { value: '' }, todos), opciones.map(o => h('option', { value: o.id }, o.nombre)));
    if (valor && !opciones.some(o => o.id === valor)) select.append(h('option', { value: valor }, 'Referencia no disponible · filtro conservado'));
    select.value = valor;
    return h('label', { class: 'pila', style: { gap: '2px', flex: '1 1 180px', minWidth: '0' } }, h('span', { class: 'sub' }, etiqueta), select);
  };
  const puedeEquipo = datos.ve_equipo === true || tareas.some(t => !t.asignados.includes(yo));
  const btnVista = v => h('button', { type: 'button', class: `bt${vista === v ? ' pri' : ''}`, 'aria-pressed': String(vista === v), 'data-uso': 'vista-daily', on: { click: () => { vista = v; asignado = ''; lista = ''; pintarFiltros(); pintarColumnas(); } } }, v === 'mia' ? 'Mi diario' : 'Daily del equipo');
  function pintarFiltros() {
    if (!vigente()) return;
    const base = filtrarTarjetas(tareas, { vista, yo, asignado, cliente, buscar, proyecto, prioridad, etiqueta, preset });
    const porLista = new Map();
    for (const t of base) if (t.lista_id) {
      const l=porLista.get(t.lista_id) || {id:t.lista_id,nombre:t.lista || 'Lista '+t.lista_id,n:0};l.n++;porLista.set(t.lista_id,l);
    }
    const listas = [...porLista.values()].map(l=>({id:l.id,nombre:`${l.nombre} · ${l.n}`})).sort((a,b)=>a.nombre.localeCompare(b.nombre));
    // Un filtro guardado obsoleto conserva cero resultados; nunca se amplía al desaparecer su referencia.
    if (!lista && listas.length === 1) lista = listas[0].id;
    const visible = filtrarTarjetas(tareas, { vista, yo });
    const personas = [...new Set(visible.flatMap(t => t.asignados))].map(id => ({ id, nombre: nombres[id] || ctx.nombre(id) })).sort((a,b)=>a.nombre.localeCompare(b.nombre));
    if (visible.some(t => !t.asignados.length)) personas.unshift({ id: '__sin_asignar', nombre: 'Sin asignar' });
    const clientes = [...new Map(visible.filter(t => t.cli).map(t => [t.cli, { id: t.cli, nombre: t.cliente || 'Cliente ' + t.cli }])).values()].sort((a,b)=>a.nombre.localeCompare(b.nombre));
    if (visible.some(t => !t.cli)) clientes.unshift({ id: '__sin_cliente', nombre: 'Sin cliente registrado' });
    const entrada = h('input', { type: 'search', value: buscar, placeholder: 'Buscar tarea o cliente', 'aria-label': 'Buscar en las tareas', style: { minHeight: '44px', width: '100%', minWidth: '0' }, on: { change: e => { buscar = e.target.value; pintarFiltros(); pintarColumnas(); } } });
    const proyectos = [...new Set(visible.map(t=>t.proyecto || t.carpeta).filter(Boolean))].sort().map(x=>({id:x,nombre:x}));
    const prioridades = [...new Set(visible.map(t=>String(t.prio_n || t.prioridad || '')).filter(Boolean))].sort().map(x=>({id:x,nombre:({'1':'Urgente','2':'Alta','3':'Normal','4':'Baja','5':'Sin prioridad',urgent:'Urgente',high:'Alta',normal:'Normal',low:'Baja'})[x]||x}));
    const etiquetas = [...new Set(visible.flatMap(t=>t.etiquetas || []).filter(x=>typeof x==='string'))].sort().map(x=>({id:x,nombre:x}));
    filtros.replaceChildren(h('div', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'wrap' } }, btnVista('mia'), puedeEquipo ? btnVista('equipo') : null,
        h('button', {type:'button',class:`bt${preset==='daily'?' pri':''}`,'aria-pressed':String(preset==='daily'),'data-uso':'filtro-daily',on:{click:()=>{preset='daily';pintarFiltros();pintarColumnas();}}},'Daily: estados de trabajo'),
        h('button', {type:'button',class:`bt${preset==='todo'?' pri':''}`,'aria-pressed':String(preset==='todo'),'data-uso':'filtro-daily',on:{click:()=>{preset='todo';pintarFiltros();pintarColumnas();}}},'Inventario completo')),
      h('div', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'wrap', alignItems: 'end' } },
        seleccionar('Lista y flujo de trabajo', listas, lista, v => { lista = v; pintarColumnas(); }, 'Elige una lista'),
        vista === 'equipo' ? seleccionar('Asignación', personas, asignado, v => { asignado = v; pintarFiltros(); pintarColumnas(); }, 'Todas las personas que puedo ver') : null,
        seleccionar('Cliente', clientes, cliente, v => { cliente = v; pintarFiltros(); pintarColumnas(); }, 'Todos mis clientes visibles')),
      h('div',{class:'fila',style:{gap:'var(--s-2)',flexWrap:'wrap'}},
        seleccionar('Proyecto',proyectos,proyecto,v=>{proyecto=v;pintarFiltros();pintarColumnas();}),
        seleccionar('Prioridad',prioridades,prioridad,v=>{prioridad=v;pintarFiltros();pintarColumnas();}),
        seleccionar('Etiqueta',etiquetas,etiqueta,v=>{etiqueta=v;pintarFiltros();pintarColumnas();})),
      entrada, preset==='daily'?h('p',{class:'sub'},'Daily incluye Planning semanal, Próximo sprint, Diario y En curso. Para backlog, revisiones y estados terminados, abre Inventario completo.'):null);
  }
  async function mover(t, destino) {
    if (!vigente()) return;
    errores.delete(t.id);
    try { await gestor.mover(t, destino, datos, estadosDeLista(datos, t.lista_id)); }
    catch (e) { errores.set(t.id, e?.message || 'No se pudo confirmar el cambio.'); }
    if (!vigente()) return;
    pintarColumnas();
  }
  function tarjeta(t, estados) {
    const editable = puedeMover(t, datos, estados), pendiente = gestor.pendientes.has(t.id);
    let destino = '';
    const selector = h('select', { 'aria-label': `Mover ${t.tarea} al estado`, disabled: !editable || pendiente, style: { minHeight: '44px', width: '100%', minWidth: '0' }, on: { change: e => { destino = e.target.value; } } },
      h('option', { value: '' }, 'Elige estado'), estados.filter(s => s.estado !== (t.estado_app || t.estado)).map(s => h('option', { value: s.estado }, s.estado)));
    const card = h('article', { class: 'panel', 'data-tarjeta-tarea': t.id, draggable: editable && !pendiente, 'aria-label': t.tarea || t.id,
      style: { padding: 'var(--s-3)', minWidth: '0', overflowWrap: 'anywhere' }, on: {
        dragstart: e => { if (!editable || pendiente) { e.preventDefault(); return; } arrastrada = t.id; e.dataTransfer?.setData('text/plain', t.id); },
        dragend: () => { arrastrada = null; },
      } },
      h('b', {}, t.tarea || `Tarea ${t.id}`),
      h('p', { class: 'sub', style: { margin: '4px 0' } }, t.cliente || 'Sin cliente registrado', t.vence ? ` · fecha límite ${t.vence}` : ' · sin fecha límite'),
      h('p', { class: 'sub', style: { margin: '4px 0' } }, t.asignados.length ? t.asignados.map(id => nombres[id] || ctx.nombre(id)).join(' · ') : 'Sin asignar'),
      t.descripcion ? h('details', {}, h('summary', {class:'bt mini'}, 'Descripción de la tarea'), h('p', {class:'sub',style:{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}, t.descripcion)) : null,
      t.asignados.length ? bloqueTareaIA({ctx,D:{tareas:[{...t,persona_id:t.asignados.includes(yo)?yo:t.asignados[0]}],generado:datos.generado}}, {...t,persona_id:t.asignados.includes(yo)?yo:t.asignados[0]}) : null,
      t.padre ? h('p', { class: 'sub' }, `Subtarea de ${t.padre}`) : null,
      h('p', { class: 'sub', role: 'status', style: { margin: '4px 0' } }, pendiente ? 'Guardando el cambio…' : textoSincronia(t)),
      t.estado_app && (t.estado_clickup || t.estado) !== t.estado_app ? h('p', { class: 'sub' }, `Copia de ClickUp: ${t.estado_clickup || t.estado} · app: ${t.estado_app}`) : null,
      t.inconsistente ? h('p', { class: 'sub', role: 'alert' }, 'Las referencias de esta tarea no coinciden. Actualiza los datos antes de moverla.') : null,
      errores.has(t.id) ? h('p', { class: 'sub', role: 'alert' }, errores.get(t.id)) : null,
      editable ? h('div', { class: 'pila', style: { gap: 'var(--s-2)' } }, selector, h('button', { type: 'button', class: 'bt', disabled: pendiente, 'data-uso': 'mover-tarea', 'aria-label': `Mover la tarea ${t.tarea}`, on: { click: () => { if (!destino) { errores.set(t.id, 'Elige el estado de destino.'); pintarColumnas(); return; } mover(t, destino); } } }, icono('arrow'), 'Mover')) : h('p', { class: 'sub' }, 'Solo lectura · permisos o catálogo de estados sin confirmar'),
      h('a', { class: 'bt mini', href: `https://app.clickup.com/t/${encodeURIComponent(t.id)}`, target: '_blank', rel: 'noopener', 'aria-label': `Abrir ${t.tarea} en ClickUp` }, icono('ext'), 'Abrir en ClickUp'));
    return card;
  }
  function pintarColumnas() {
    if (!vigente()) return;
    if (!lista) { columnas.replaceChildren(vacioLinea('Elige una lista para usar sus estados exactos sin mezclar flujos.', { icono: 'info' })); return; }
    const visibles = filtrarTarjetas(tareas, { vista, yo, asignado, cliente, lista, buscar, proyecto, prioridad, etiqueta, preset });
    const estados = estadosDeLista(datos, lista);
    const { columnas: grupos, fuera } = columnasDeLista(visibles, estados);
    const grid = h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 250px), 1fr))', alignItems: 'start', gap: 'var(--s-3)', minWidth: '0' } });
    for (const g of grupos) {
      const contenido = h('div', { class: 'pila', style: { gap: 'var(--s-2)' } });
      let limite = 25;
      const pintar = () => { contenido.replaceChildren(...g.tareas.slice(0,limite).map(t=>tarjeta(t,estados)), g.tareas.length > limite ? h('button', { type: 'button', class: 'bt', on: { click: () => { limite += 25; pintar(); } } }, `Ver más (${g.tareas.length - limite} quedan)`) : null); };
      pintar();
      const col = h('section', { class: 'pila', 'aria-label': `Estado ${g.estado}`, style: { gap: 'var(--s-2)', minWidth: '0', padding: 'var(--s-2)', border: 'var(--borde-suave)', borderRadius: 'var(--r-m)' }, on: {
        dragover: e => { if (arrastrada && estados.some(s=>s.estado===g.estado)) e.preventDefault(); },
        drop: e => { e.preventDefault(); const t = tareas.find(x=>x.id===arrastrada && x.lista_id===lista); arrastrada=null; if(t) mover(t,g.estado); },
      } }, h('h2', { style: { font: 'var(--t-h3)', overflowWrap: 'anywhere' } }, `${g.estado} · ${g.tareas.length}`), contenido);
      grid.append(col);
    }
    columnas.replaceChildren(h('p', { class: 'sub' }, `${visibles.length} tareas en esta lista. Arrastra una tarjeta o usa «Mover»; el botón funciona con teclado y móvil.`),
      grid, fuera.length ? h('section', { class: 'pila' }, h('h2', { style: { font: 'var(--t-h3)' } }, `Fuera del catálogo confirmado · ${fuera.length}`), h('p', { class: 'sub' }, 'Se muestran sin inventar columnas. Confirma los estados de esta lista antes de moverlas.'), ...fuera.map(t=>tarjeta(t,[]))) : null,
      !visibles.length ? vacioLinea('No hay tareas con estos filtros.', { icono: 'ok' }) : null);
  }
  const misFiltros = () => ({ vista, preset, asignado, cliente, lista, proyecto, prioridad, etiqueta });
  const puedeGuardarVistas = () => !datos.solo_lectura && !ctx.soloLectura;
  function pintarVistas() {
    if (!vigente()) return;
    const seleccion = h('select', { 'aria-label': 'Elegir vista privada guardada', disabled: ocupadoVista || leyendoVistas || !puedeGuardarVistas(),
      style: { minHeight: '44px', minWidth: '0', maxWidth: '100%', flex: '1 1 220px' }, on: { change: e => {
        if (!vigente() || !e.target.isConnected) return;
        vistaGuardadaId = e.target.value;
        const guardada = vistasGuardadas.find(v => v.id === vistaGuardadaId);
        if (guardada) {
          ({ vista, preset, asignado, cliente, lista, proyecto, prioridad, etiqueta } = guardada.filtros);
          buscar = ''; nombreVista = guardada.nombre;
          mensajeVista = 'Vista aplicada a la copia autorizada actual. Las referencias ausentes conservan el filtro y no amplían resultados.';
          pintarFiltros(); pintarColumnas();
        } else { nombreVista = ''; mensajeVista = 'Los filtros actuales se conservan; puedes guardarlos como una vista nueva.'; }
        pintarVistas();
      } } }, h('option', { value: '' }, 'Nueva vista · filtros actuales'), ...vistasGuardadas.map(v => h('option', { value: v.id }, v.nombre)));
    seleccion.value = vistaGuardadaId;
    const nombre = h('input', { type: 'text', maxLength: 60, value: nombreVista, placeholder: 'Nombre de la vista', 'aria-label': 'Nombre de la vista privada',
      disabled: ocupadoVista || !puedeGuardarVistas(), style: { minHeight: '44px', minWidth: '0', flex: '1 1 180px', maxWidth: '100%' },
      on: { input: e => { if (vigente() && e.target.isConnected) nombreVista = e.target.value; } } });
    const guardar = h('button', { type: 'button', class: 'bt', disabled: ocupadoVista || leyendoVistas || !puedeGuardarVistas() || (!vistaGuardadaId && vistasGuardadas.length >= 20),
      style: { minHeight: '44px' }, on: { click: e => cambiarVista('guardar', e.currentTarget) } }, vistaGuardadaId ? 'Actualizar esta vista' : 'Guardar vista');
    const eliminar = h('button', { type: 'button', class: 'bt', disabled: ocupadoVista || !vistaGuardadaId || !puedeGuardarVistas(),
      style: { minHeight: '44px' }, on: { click: e => cambiarVista('eliminar', e.currentTarget) } }, 'Eliminar vista');
    vistasPanel.replaceChildren(h('h2', { style: { font: 'var(--t-h3)' } }, 'Mis vistas guardadas'),
      h('div', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'wrap', minWidth: '0' } }, seleccion, nombre, guardar, eliminar,
        h('button', { type: 'button', class: 'bt', disabled: ocupadoVista || leyendoVistas || !puedeGuardarVistas(), style: { minHeight: '44px' },
          on: { click: e => { if (vigente() && e.currentTarget.isConnected) cargarVistas(); } } }, 'Recargar vistas')),
      h('p', { class: 'sub', role: 'status', style: { overflowWrap: 'anywhere' } }, !puedeGuardarVistas() ? 'Las vistas privadas se usan en tu sesión real. Aquí no se leen ni cambian.' : leyendoVistas ? 'Leyendo tus vistas…' : ocupadoVista ? 'Guardando preferencia local…' : mensajeVista || `${vistasGuardadas.length} de 20 vistas. Solo filtros; la búsqueda escrita no se guarda. No se aplica ninguna vista automáticamente.`));
  }
  async function cargarVistas() {
    if (!vigente() || !puedeGuardarVistas() || ocupadoVista) return;
    leyendoVistas = true; pintarVistas();
    try {
      const r = await ctx.api('tareas/vistas');
      if (!vigente()) return;
      vistasGuardadas = Array.isArray(r?.vistas) ? r.vistas : [];
      mensajeVista = r?.invalidas ? 'Hay preferencias almacenadas que no se pueden leer; se conservan sin aplicarlas.' : '';
      if (vistaGuardadaId && !vistasGuardadas.some(v => v.id === vistaGuardadaId)) vistaGuardadaId = '';
    } catch (_) { if (!vigente()) return; mensajeVista = 'No se pudieron leer las vistas. Tus filtros actuales se conservan; puedes reintentar.'; }
    if (!vigente()) return;
    leyendoVistas = false; pintarVistas();
  }
  async function cambiarVista(accion, control) {
    if (!vigente() || !control?.isConnected || !puedeGuardarVistas() || ocupadoVista || leyendoVistas) return;
    const actual = vistasGuardadas.find(v => v.id === vistaGuardadaId);
    if (accion === 'guardar' && !nombreVista.trim()) { mensajeVista = 'Pon un nombre a la vista.'; pintarVistas(); return; }
    if (accion === 'eliminar' && !actual) return;
    const cuerpo = { accion, ...(actual ? { id: actual.id, revision: actual.revision } : {}),
      ...(accion === 'guardar' ? { nombre: nombreVista.trim(), filtros: misFiltros() } : {}) };
    ocupadoVista = true; pintarVistas();
    try {
      if (!vigente()) return;
      const r = await ctx.api('tareas/vistas', { metodo: 'POST', cuerpo });
      if (!vigente()) return;
      if (!r?.ok) throw new Error('Preferencia sin confirmar');
      if (accion === 'guardar') {
        vistasGuardadas = [...vistasGuardadas.filter(v => v.id !== r.vista.id), r.vista];
        vistaGuardadaId = r.vista.id; nombreVista = r.vista.nombre;
        mensajeVista = 'Vista guardada solo para ti. No se modifica ninguna tarea.';
      } else {
        vistasGuardadas = vistasGuardadas.filter(v => v.id !== actual.id);
        vistaGuardadaId = ''; nombreVista = ''; mensajeVista = 'Vista eliminada. Los filtros actuales se conservan.';
      }
    } catch (_) { if (!vigente()) return; mensajeVista = 'No se confirmó el cambio. Recarga las vistas antes de reintentar.'; }
    if (!vigente()) return;
    ocupadoVista = false; pintarVistas();
  }
  const cobertura = datos.cobertura_tareas || {};
  aviso.textContent = `${cobertura.completa ? 'Inventario leído de ClickUp' : 'Copia parcial: no confirma todo el histórico de ClickUp'}. ${cobertura.nota || ''} Datos de ${datos.generado || 'fecha no disponible'}. ${datos.solo_lectura ? 'Ver como: solo lectura.' : ''}`;
  cont.replaceChildren(h('div', { class: 'pila', style: { gap: 'var(--s-3)', minWidth: '0' } }, vistasPanel, filtros, aviso, columnas));
  pintarFiltros(); pintarColumnas(); pintarVistas();
  if (puedeGuardarVistas()) cargarVistas(); else { leyendoVistas = false; pintarVistas(); }
} };
