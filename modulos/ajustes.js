// modulos/ajustes.js · M22 Ajustes (E0): Personas · Asignaciones · Para confirmar · Ver como.
// Lo mantienen Mili y Tomás (D-01). Todo cambio va a local.db (historial + rastro, imborrables) vía servir.py.
// En «ver como» o sin servidor, es de solo lectura.

import { tablaDensa, chipEstado, estadoVacio, avisoParcial, panel, botonConfirmar, fmt, pestanas, tablaApilable, selectorPersona, icono, poner, chipsFiltro, vacioLinea, avisoFlotante } from '../componentes.js';
import { vistaOpiniones } from '../ayudas.js';
import { PUESTOS, PUESTO } from '../permisos.js';
import { vistaConexiones } from './ajustes_conexiones.js';
import { h, campo, elegir } from './personas_comun.js';
import { llevarA, filaConTexto } from './_ir.js';
import { altaNueva, puedeVer as puedeVerPrimera, pasosHechos, DIAS_VENTANA } from './primera_semana.js';

const PESTANAS = [
  { id: 'personas', texto: 'Personas', icono: 'users' },
  { id: 'altas', texto: 'Altas y bajas', icono: 'mas' },   // N9 (2-oct noche): altas_personas.py
  { id: 'asignaciones', texto: 'Asignaciones', icono: 'cartera' },
  { id: 'confirmar', texto: 'Para confirmar', icono: 'flag' },
  { id: 'ver-como', texto: 'Ver como', icono: 'ojo' },
  { id: 'avisos', texto: 'Avisos y recargas', icono: 'campana' },
  { id: 'conexiones', texto: 'Salud del sistema', icono: 'plug' },   // M22 (agente M20-M22): modulos/ajustes_conexiones.js
  { id: 'opiniones', texto: 'Algo va mal', icono: 'opinion' },             // R15b: lo que manda el equipo con el botón de la cabecera
];
const SILLAS_NOMBRE = { account: 'Account', trafficker: 'Trafficker', crm: 'CRM (GHL)', ghl: 'CRM (GHL)', seo: 'SEO', web: 'Web', redes: 'Redes', produccion: 'Producción', outreach: 'Outreach' };
const CONFIANZA = { confirmada: 'verde', alta: 'verde', media: 'ambar', baja: 'rojo' };

export default {
  id: 'ajustes',
  titulo: 'Ajustes',
  grupo: 'Sistema',
  puestos_que_lo_ven: { direccion: 'todo', operaciones: 'todo', rrhh: 'resumen' },
  async render(cont, ctx) {
    const pest = PESTANAS.some(p => p.id === ctx.params[0]) ? ctx.params[0] : 'personas';
    if (!ctx.servidor) {
      cont.append(estadoVacio({
        titulo: 'Ajustes necesita el servidor local',
        porque: 'Personas y asignaciones se guardan en local.db con su rastro; sin servidor no hay dónde guardarlas.',
        que_hacer: 'Abre la app desde su servidor local (lo arranca Agus).',
      }));
      return;
    }
    let A;
    try { A = await ctx.api('ajustes'); }
    catch (e) { cont.append(estadoVacio({ titulo: 'Sin acceso a Ajustes', porque: e.message })); return; }
    const editar = A.puedeEditar && !ctx.soloLectura;
    const nombre = Object.fromEntries(A.personas.map(p => [p.id, p.alias || p.nombre]));
    const nomCli = Object.fromEntries(A.clientes.map(c => [c.id, c.nombre]));

    // Ronda 8 (D-P-PER2 c): pestañas con icono y contador, el mismo componente que la ficha; la ruta sigue en el hash.
    const pend = A.para_confirmar.filter(d => !d.respondida).length;
    // N9: las altas y bajas tienen su propia ruta en el servidor (/api/altas); solo se piden en su pestaña.
    let Al = null;
    if (pest === 'altas') {
      try { Al = await ctx.api('altas'); }
      catch (e) { Al = { error: e.message }; }
    }
    // R15b: «Algo va mal / ideas» (solo Mili y Tomás: dirección y operaciones). El número de la pestaña = los nuevos.
    let Op = null;
    if (ctx.nivel === 'todo') {
      try { Op = await ctx.api('opiniones'); }
      catch (e) { Op = { error: e.message, opiniones: [] }; }
    }
    const opNuevas = Op?.todas ? (Op.opiniones || []).filter(o => (o.estado || 'nueva') === 'nueva').length : 0;
    const barra = pestanas({
      etiqueta: 'Secciones de Ajustes', activa: pest,
      pestanas: PESTANAS.filter(p => ctx.nivel === 'todo' || p.id === 'personas')
        .filter(p => p.id !== 'opiniones' || Op?.todas)
        .map(p => ({ ...p, cuenta: p.id === 'confirmar' ? pend : p.id === 'opiniones' ? opNuevas : p.id === 'altas' && Al?.tareas ? Al.tareas.filter(x => x.estado === 'pendiente').length : 0,
          cuentaEstado: (p.id === 'confirmar' && pend) || (p.id === 'opiniones' && opNuevas) ? 'rojo' : '' })),
      alCambiar: id => { location.hash = `#/ajustes/${id}`; },
    });
    cont.append(barra);
    // R15b: con 8 pestañas la fila se desliza; la elegida, siempre a la vista (sin mover la página).
    const verActiva = (n = 0) => {
      const tl = barra.matches('[role=tablist]') ? barra : barra.querySelector('[role=tablist]'), a = tl?.querySelector('[aria-selected="true"]');
      if (!tl || !a) return;
      if (!tl.isConnected || !tl.clientWidth) { if (n < 40) setTimeout(() => verActiva(n + 1), 50); return; }
      const ra = a.getBoundingClientRect(), rt = tl.getBoundingClientRect();
      if (ra.right > rt.right) tl.scrollLeft += ra.right - rt.right + 16;
    };
    verActiva();
    if (!editar) cont.append(avisoParcial(ctx.soloLectura ? 'Estás en «ver como»: solo lectura.' : 'Solo lectura: los cambios los hacen Mili y Tomás.', { tipo: 'info' }));

    if (pest === 'personas') cont.append(...vistaPersonas(A, ctx, editar, nombre));
    if (pest === 'altas') cont.append(...(Al.error ? [estadoVacio({ titulo: 'Sin acceso a altas y bajas', porque: Al.error })] : vistaAltas(Al, ctx, editar, nombre)));
    if (pest === 'asignaciones') cont.append(...vistaAsignaciones(A, ctx, editar, nombre, nomCli));
    if (pest === 'confirmar') cont.append(...vistaConfirmar(A, ctx, editar, nombre, nomCli));
    if (pest === 'ver-como') cont.append(...vistaVerComo(A, ctx));
    if (pest === 'avisos') cont.append(...await vistaAvisos(ctx));
    if (pest === 'conexiones' && ctx.nivel === 'todo') cont.append(...await vistaConexiones(ctx, { objetivo: ctx.params[1] || null }));
    if (pest === 'opiniones') {
      if (Op?.todas) cont.append(...vistaOpinionesAjustes(Op.opiniones || [], ctx, { objetivo: ctx.params[1] || null }));
      else cont.append(estadoVacio({ titulo: 'Esta lista es de Mili y Tomás', porque: Op?.error || 'Los «Algo va mal / Tengo una idea» de todo el equipo los leen dirección y operaciones.',
        que_hacer: 'Los tuyos los ves en el botón «Algo va mal» de la cabecera › «Los míos».' }));
    }
  },
};

// ---------------------------------------------------------------- Algo va mal / ideas (R15b)
// La lista es la de ayudas.js (vistaOpiniones, la misma del diálogo «Recibidos»); aquí se filtra por estado y cada fila lleva
// «Nuevo / Visto / Hecho». El cambio se guarda con ctx.accion (cola de acciones de Ajustes, con rastro) y se copia al estado
// de la opinión (POST /api/opiniones/estado) para que el diálogo diga lo mismo. Ruta: #/ajustes/opiniones[/<n.º>].
const EST_OP = [
  { valor: 'nueva', texto: 'Nuevo', chip: 'nuevo', icono: 'campana' },
  { valor: 'vista', texto: 'Visto', chip: 'visto', icono: 'ojo' },
  { valor: 'resuelta', texto: 'Hecho', chip: 'hecho', icono: 'ok' },
];
const horaOp = t => { try { return new Date(String(t).replace(' ', 'T') + 'Z').toLocaleString('es-ES', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }); } catch { return t || ''; } };

function vistaOpinionesAjustes(lista, ctx, { objetivo = null } = {}) {
  const ops = lista.map(o => ({ ...o, estado: o.estado || 'nueva' }));
  const n = v => ops.filter(o => o.estado === v).length;
  const obj = objetivo ? ops.find(o => String(o.id) === String(objetivo)) : null;
  const caja = h('div', { class: 'pila' });
  let filtro = '';
  const chips = chipsFiltro({ clave: 'ajustes.opiniones', etiqueta: 'Ver', opciones: [
    { valor: 'nueva', texto: 'Nuevos', icono: 'campana', cuenta: n('nueva'), cuentaEstado: 'rojo' },
    { valor: 'vista', texto: 'Vistos', icono: 'ojo', cuenta: n('vista') },
    { valor: 'resuelta', texto: 'Hechos', icono: 'ok', cuenta: n('resuelta') },
    { valor: '', texto: 'Todos', cuenta: ops.length }],
  alCambiar: v => { filtro = v; pintar(); } });
  filtro = chips.valor();
  if (obj && filtro && obj.estado !== filtro) filtro = '';   // que el filtro guardado no esconda la que se pidió
  const repintarChips = () => chips.querySelectorAll('button').forEach((b, i) => {
    const cu = b.querySelector('.cu'); const v = ['nueva', 'vista', 'resuelta', ''][i];
    if (cu) { const k = v ? n(v) : ops.length; cu.textContent = fmt.num(k); cu.classList.toggle('rojo', v === 'nueva' && k > 0); }
  }) || pestanaNuevos();
  // El número de la pestaña «Algo va mal» (los nuevos) también se pone al día.
  const pestanaNuevos = () => document.querySelectorAll('[role=tab][id$="-opiniones"] .c').forEach(c => {
    c.textContent = fmt.num(n('nueva')); c.setAttribute('aria-label', `${n('nueva')} pendientes`); c.hidden = !n('nueva');
  });

  async function guardar(o, est, b) {
    if (ctx.soloLectura) return;
    b.disabled = true;
    const ETQ = EST_OP.find(x => x.valor === est);
    try {
      const r = await ctx.accion({ herramienta: 'app', tipo: 'marcar', objeto: `opinion:${o.id}`,
        texto: `${o.tipo === 'idea' ? 'Idea' : 'Algo va mal'} n.º ${o.id} de ${o.quien_alias}: ${ETQ.chip}`,
        vista_previa: { opinion_id: o.id, estado: ETQ.chip, antes: (EST_OP.find(x => x.valor === o.estado) || EST_OP[0]).chip } });
      await ctx.api('opiniones/estado', { metodo: 'POST', cuerpo: { id: o.id, estado: est } });
      o.estado = est; o.estado_por = ctx.real.id; o.estado_hora = `${ctx.hoy} ${ctx.fechas.hora(new Date().toISOString())}`;   // V2-E: hora de Madrid, no UTC
      avisoFlotante(`Marcado «${ETQ.chip}» · queda en el rastro${r?.id ? ` (n.º ${r.id})` : ''}`);
      repintarChips(); pintar(o.id);
    } catch (e) { b.disabled = false; avisoFlotante(`No se ha guardado: ${e.message}`, { icono: 'alert' }); }
  }

  async function pintar(foco = null) {
    const vis = ops.filter(o => !filtro || o.estado === filtro);
    if (!vis.length) {
      caja.replaceChildren(h('div', { class: 'cuerpo' }, vacioLinea(ops.length
        ? (filtro === 'nueva' ? 'Nada nuevo: todo lo que ha mandado el equipo está visto o hecho.' : 'Ninguno en este estado: cambia el filtro para ver el resto.')
        : 'Nadie ha mandado nada todavía. Sale aquí lo que el equipo mande con «Algo va mal / Tengo una idea».', { icono: 'ok' })));
      return;
    }
    // La lista de ayudas.js con lo ya leído (sin volver a pedirlo) y en solo lectura: los botones de estado los pone Ajustes.
    let leer;
    const api = (ruta, op) => (ruta === 'opiniones' ? (leer = Promise.resolve({ todas: true, opiniones: vis.map(o => ({ ...o, estado: (EST_OP.find(x => x.valor === o.estado) || EST_OP[0]).chip })) }))
      : ctx.api(ruta, op));
    const lista = vistaOpiniones({ api, todas: true, soloLectura: true });
    caja.replaceChildren(lista);
    await leer;
    const filas = [...lista.querySelectorAll('ul.opiniones > li')];
    filas.forEach((li, i) => {
      const o = vis[i];
      if (!o) return;
      li.dataset.opinion = String(o.id);
      li.setAttribute('data-fila', '');
      const zona = li.querySelector('.fila') || li.appendChild(h('div', { class: 'fila' }));
      const grupo = h('span', { class: 'fila', role: 'group', 'aria-label': `Estado del n.º ${o.id}`, style: { gap: 'var(--s-1)' } },
        EST_OP.map(x => h('button', { type: 'button', class: `bt mini${x.valor === o.estado ? ' pri' : ''}`, 'aria-pressed': String(x.valor === o.estado),
          'data-atajo': x.valor === 'resuelta' ? 'e' : null, disabled: ctx.soloLectura || null,
          title: ctx.soloLectura ? 'Estás en «ver como»: solo lectura' : `Marcar como ${x.chip}`,
          on: { click: e => { if (x.valor !== o.estado) guardar(o, x.valor, e.currentTarget); } } }, icono(x.icono, { clase: 's' }), x.texto)));
      zona.prepend(grupo);
      if (o.estado_por && o.estado !== 'nueva') zona.append(h('span', { class: 'sub' }, `${(EST_OP.find(x => x.valor === o.estado) || {}).texto} por ${ctx.nombre ? ctx.nombre(o.estado_por) : o.estado_por} · ${horaOp(o.estado_hora)}`));
    });
    if (foco) caja.querySelector(`[data-opinion="${foco}"] button[aria-pressed="true"]`)?.focus({ preventScroll: true });
  }
  pintar().then(() => {
    if (objetivo && obj) llevarA(caja, r => r.querySelector(`[data-opinion="${CSS.escape(String(obj.id))}"]`));
    else if (objetivo) caja.prepend(avisoParcial('Ese aviso ya no está en la lista (se guardan los 300 últimos).', { titulo: 'No lo encuentro.' }));
  });
  return [panel({ titulo: 'Algo va mal / Tengo una idea', icono: 'opinion',
    sub: 'Lo que manda el equipo con el botón de la cabecera, lo más nuevo arriba. Nuevo → Visto (lo has leído) → Hecho (arreglado o descartado). Cada cambio queda en el rastro.' },
  h('div', { class: 'cuerpo pila' }, chips, ctx.soloLectura ? avisoParcial('Estás en «ver como»: solo lectura.', { tipo: 'info' }) : null), caja)];
}

// ---------------------------------------------------------------- Personas
function vistaPersonas(A, ctx, editar, nombre) {
  const activas = A.personas.filter(p => p.estado === 'activo');
  const sinPuesto = activas.filter(p => !(p.puestos || []).length);
  const resumen = h('div', { class: 'fila' },
    chipEstado('verde', `${activas.length} activas`),
    chipEstado(sinPuesto.length ? 'rojo' : 'verde', sinPuesto.length ? `${sinPuesto.length} activas sin puesto` : 'todas con al menos un puesto'),
    chipEstado('gris', `${A.personas.filter(p => p.estado === 'dudoso').length} dudosas`),
    chipEstado('gris', `${A.personas.filter(p => p.estado === 'por_incorporar').length} por incorporar`),
    chipEstado('gris', `${A.personas.filter(p => p.estado === 'baja').length} de baja`));
  const editor = h('div');
  const filas = A.personas.map(p => ({
    ...p,
    puestos_txt: (p.puestos || []).map(x => PUESTO[x]?.nombre || x).join(' · '),
    jefe_txt: p.jefe ? nombre[p.jefe] || p.jefe : '—',
  }));
  const tabla = tablaDensa({
    filas,
    buscar: { campos: ['nombre', 'alias', 'puestos_txt'], placeholder: 'Buscar persona o puesto' },
    filtros: [{ clave: 'estado', titulo: 'Estado' }],
    orden: { clave: 'estado', dir: 'asc' },
    columnas: [
      { clave: 'alias', titulo: 'Persona', principal: true, celda: p => h('span', {}, h('b', {}, p.alias), h('span', { class: 'sub' }, ` ${p.nombre}`)) },
      { clave: 'puestos_txt', titulo: 'Puestos' },
      { clave: 'jefe_txt', titulo: 'Jefe' },
      { clave: 'horas_mes', titulo: 'h/mes', num: true },
      { clave: 'imputa_horas', titulo: '¿Imputa?' },
      ...(A.puedeEditar ? [{ clave: 'correo', titulo: 'Correo de RO', celda: p => p.correo || chipEstado('ambar', 'sin correo: no puede entrar') }] : []),
      { clave: 'estado', titulo: 'Estado', celda: p => chipEstado({ activo: 'verde', dudoso: 'ambar', por_incorporar: 'azul', baja: 'gris' }[p.estado] || 'gris', p.estado.replace('_', ' ')) },
    ],
    alPulsar: p => { editor.replaceChildren(editorPersona(p, A, ctx, editar, nombre)); editor.scrollIntoView({ block: 'nearest' }); },
    etiquetaFila: p => `${p.alias}, ${p.puestos_txt}. Abrir`,
  });
  const alta = ctx.nivel === 'todo' ? h('a', { class: 'bt pri', href: '#/ajustes/altas' }, icono('mas'), 'Añadir persona') : null;
  return [panel({ titulo: 'Personas', icono: 'eq', sub: 'Varios puestos por persona · 128 h al mes para medir la carga · los sueldos no se ven aquí', acciones: alta }, resumen, tabla), editor];
}

function editorPersona(p, A, ctx, editar, nombre) {
  const marcados = new Set(p.puestos || []);
  // Ronda 11 (A3): los puestos de mando, y puestos, jefe y estado de quien ya tiene uno, solo los cambia Tomás (el servidor
  // lo comprueba igual; aquí solo no se ofrece).
  const soloTomas = new Set(A.puestos_solo_tomas || []);
  const esTomas = !!A.realEsDireccion;
  const blindada = !esTomas && (p.puestos || []).some(x => soloTomas.has(x) || x === 'direccion');
  const fijo = x => !editar || blindada || (!esTomas && soloTomas.has(x));
  const grupos = [...new Set(PUESTOS.map(x => x.grupo))];
  const casillas = grupos.map(g => h('fieldset', { class: 'fila', style: { border: '0', padding: '0', margin: '0 0 var(--s-2)' } },
    h('legend', { class: 'sub' }, g),
    PUESTOS.filter(x => x.grupo === g).map(x => h('label', { class: 'chip gris sin-punto', style: { minHeight: '32px', cursor: editar ? 'pointer' : 'default' } },
      h('input', { type: 'checkbox', value: x.id, checked: marcados.has(x.id), disabled: fijo(x.id),
        on: { change: e => (e.target.checked ? marcados.add(x.id) : marcados.delete(x.id)) } }), ' ', x.nombre))));
  const jefe = h('select', { disabled: !editar || blindada }, h('option', { value: '' }, '— sin jefe —'),
    A.personas.filter(x => x.id !== p.id && x.estado !== 'baja').map(x => h('option', { value: x.id, selected: x.id === p.jefe }, nombre[x.id])));
  const horas = h('input', { type: 'number', min: '0', max: '200', value: p.horas_mes ?? 128, disabled: !editar, style: { width: 'calc(var(--s-16) + var(--s-6))', minHeight: 'var(--s-8)' } });
  const imputa = elegir([{ valor: 'sí', texto: 'Sí' }, { valor: 'no', texto: 'No' }], { valor: p.imputa_horas === 'no' ? 'no' : 'sí', desactivado: !editar });
  const est = elegir(['activo', 'dudoso', 'por_incorporar', 'baja'].map(v => ({ valor: v, texto: v[0].toUpperCase() + v.slice(1).replace('_', ' ') })), { valor: p.estado || 'activo', desactivado: !editar || blindada });
  return h('div', { class: 'pila' }, tarjetaPrimeraSemana(ctx, p), panel({ titulo: `${p.alias} · ${p.nombre}`, icono: 'editar', sub: p.nota || (p.puestos_sin_equivalencia?.length ? `Sin equivalencia: ${p.puestos_sin_equivalencia.join(', ')}` : 'Cada cambio queda en el historial con el antes y el después.') },
    h('div', { class: 'cuerpo pila' },
      h('div', {}, h('b', {}, 'Puestos'), casillas,
        editar && !esTomas ? h('p', { class: 'sub' }, blindada
          ? 'Tiene un puesto de mando: sus puestos, su jefe y su estado solo los cambia Tomás.'
          : 'Dirección, finanzas de dirección, RRHH, operaciones, ventas de RO y administración solo los da o quita Tomás.') : null),
      h('div', { class: 'pm-form' }, campo('Jefe', jefe), campo('Horas al mes', horas), campo('¿Imputa horas?', imputa), campo('Estado', est, { ancho: true })),
      p.puestos_fase0 ? h('p', { class: 'sub' }, `Organigrama (fase 0): ${p.puestos_fase0.join(', ') || '—'} · fuente: ${p.fuente || '—'}`) : null,
      editar ? botonConfirmar({
        texto: 'Guardar cambios', pregunta: `¿Guardar los cambios de ${p.alias}?`, confirmar: 'Sí, guardar',
        alConfirmar: async () => {
          const cambios = { puestos: [...marcados], jefe: jefe.value || null, horas_mes: Number(horas.value), imputa_horas: imputa.value, estado: est.value };
          await ctx.api('ajustes/persona', { metodo: 'POST', cuerpo: { id: p.id, cambios } });
          setTimeout(() => location.reload(), 600);
          return 'Guardado en el historial';
        },
      }) : null)));
}

// A10 (R15a): «Su primera semana» en la ficha de quien entró hace menos de 14 días (o está por incorporar). La ven su jefe,
// Mili y Tomás; RRHH no (regla de A10). El avance sale de lo que marca la propia persona en #/primera-semana.
function tarjetaPrimeraSemana(ctx, p0) {
  const p = (ctx.datos?.personas || []).find(x => x.id === p0.id) || p0;
  const n = altaNueva(p);
  if (!n || !puedeVerPrimera(ctx, p)) return null;
  const cuenta = h('span', { class: 'sub' }, 'Mirando su avance…');
  pasosHechos(ctx, p.id).then(hs => { cuenta.textContent = `${hs.size} de 5 pasos hechos`; }).catch(() => { cuenta.textContent = ''; });
  return panel({ titulo: `Su primera semana · ${p.alias || p.nombre}`, icono: 'rocket',
    sub: n.por_incorporar ? 'Por incorporar: la verá en Mi día en cuanto entre' : `Día ${n.dias + 1} de ${DIAS_VENTANA} desde su alta`,
    acciones: h('a', { class: 'bt pri', href: `#/primera-semana/${encodeURIComponent(p.id)}` }, icono('derecha', { clase: 's' }), 'Ver su primera semana') },
  h('div', { class: 'cuerpo' }, cuenta));
}

// ---------------------------------------------------------------- Asignaciones
function vistaAsignaciones(A, ctx, editar, nombre, nomCli) {
  // R15a (A2): #/ajustes/asignaciones/<cliente> → la tabla filtrada por ese cliente y, si no tiene account, el formulario
  // con el cliente y la silla «account» ya elegidos (para «Cliente sin account»).
  const objetivo = ctx.params[1] && nomCli[ctx.params[1]] ? ctx.params[1] : null;
  const hoy = ctx.hoy;   // V2-E: hoy en Madrid (no UTC)
  const vig = a => (!a.desde || a.desde <= hoy) && (!a.hasta || a.hasta >= hoy);
  const filas = A.asignaciones.map((a, i) => ({
    ...a, i, cliente: nomCli[a.cliente_id] || a.cliente_id, persona: nombre[a.persona_id] || a.persona_id,
    silla_txt: SILLAS_NOMBRE[a.silla] || a.silla, vigente: vig(a) ? 'vigente' : 'cerrada',
    tipo: a.suplencia ? 'suplencia' : a.principal === false ? 'apoyo' : 'responsable', confianza: a.confianza || '—',
  }));
  const vigentes = filas.filter(f => f.vigente === 'vigente');
  const sinAccount = A.clientes.filter(c => c.sin_account);
  const resumen = h('div', { class: 'fila' },
    chipEstado('verde', `${vigentes.length} vigentes`),
    chipEstado('rojo', `${vigentes.filter(f => f.confianza === 'baja').length} de confianza baja`),
    chipEstado('ambar', `${vigentes.filter(f => f.confianza === 'media').length} media`),
    chipEstado('verde', `${vigentes.filter(f => f.confianza === 'confirmada').length} confirmadas`),
    chipEstado(sinAccount.length ? 'ambar' : 'verde', `${sinAccount.length} clientes sin account`));
  const tabla = tablaDensa({
    filas,
    buscar: { campos: ['cliente', 'persona', 'fuente'], placeholder: 'Buscar cliente o persona' },
    filtros: [{ clave: 'silla_txt', titulo: 'Silla' }, { clave: 'confianza', titulo: 'Confianza' }, { clave: 'vigente', titulo: 'Vigencia' }, { clave: 'persona', titulo: 'Persona' }],
    orden: { clave: 'cliente', dir: 'asc' },
    columnas: [
      { clave: 'cliente', titulo: 'Cliente', principal: true },
      { clave: 'silla_txt', titulo: 'Silla' },
      { clave: 'persona', titulo: 'Persona' },
      { clave: 'tipo', titulo: 'Papel', celda: f => f.tipo === 'suplencia' ? chipEstado('azul', `suplencia hasta ${fmt.fecha(f.hasta)}`) : f.tipo },
      { clave: 'confianza', titulo: 'Confianza', celda: f => chipEstado(CONFIANZA[f.confianza] || 'gris', f.confianza) },
      { clave: 'fuente', titulo: 'De dónde sale', celda: f => h('span', { class: 'sub' }, f.fuente || '—') },
      { clave: 'vigente', titulo: 'Desde / hasta', celda: f => `${f.desde ? fmt.fecha(f.desde) : 'carga inicial'} → ${f.hasta ? fmt.fecha(f.hasta) : 'vigente'}` },
      ...(editar ? [{ clave: 'acc', titulo: '', ordenable: false, celda: f => f.vigente !== 'vigente' ? '' : h('span', { class: 'fila' },
        f.confianza !== 'confirmada' ? botonConfirmar({ texto: 'Confirmar', mini: true, pregunta: '¿Confirmar?', confirmar: 'Sí',
          alConfirmar: () => post(ctx, 'ajustes/asignacion', { operacion: 'confirmar', cliente_id: f.cliente_id, persona_id: f.persona_id, silla: f.silla }) }) : null,
        botonConfirmar({ texto: 'Cerrar', mini: true, peligro: true, pregunta: `¿Cerrar hoy ${f.persona} en ${f.cliente}?`, confirmar: 'Sí, cerrar',
          alConfirmar: () => post(ctx, 'ajustes/asignacion', { operacion: 'cerrar', cliente_id: f.cliente_id, persona_id: f.persona_id, silla: f.silla }) })) }] : []),
    ],
  });
  const out = [panel({ titulo: 'Asignaciones', icono: 'cartera', sub: 'Cliente × persona × silla. Nada se borra: cerrar pone fecha de fin. Las suplencias caducan solas.' }, resumen, tabla)];
  const form = editar ? formNueva(A, ctx, nombre, objetivo ? { cliente: objetivo, silla: A.clientes.find(c => c.id === objetivo)?.sin_account ? 'account' : null } : {}) : null;
  if (form) out.push(form);
  if (objetivo) {
    const buscador = tabla.querySelector('input[type=search]');
    if (buscador) { buscador.value = nomCli[objetivo]; buscador.dispatchEvent(new Event('input')); }
    const sinAcc = A.clientes.find(c => c.id === objetivo)?.sin_account;
    out.unshift(avisoParcial(sinAcc ? `${nomCli[objetivo]} no tiene account.${form ? ' El formulario de abajo ya lo tiene elegido: escoge la persona y guarda.' : ' Lo asignan Mili o Tomás.'}`
      : `Ves solo las asignaciones de ${nomCli[objetivo]}. Borra la búsqueda para ver todas.`, { tipo: sinAcc ? undefined : 'info', titulo: sinAcc ? 'Sin account.' : undefined }));
    llevarA(tabla.parentElement || tabla, () => (sinAcc && form) ? form : filaConTexto(tabla, nomCli[objetivo], 'tbody tr'), { foco: true });
  }
  return out;
}

function formNueva(A, ctx, nombre, pre = {}) {
  const cli = h('select', {}, A.clientes.slice().sort((a, b) => a.nombre.localeCompare(b.nombre, 'es')).map(c => h('option', { value: c.id, selected: c.id === pre.cliente }, c.nombre + (c.sin_account ? ' · sin account' : ''))));
  const silla = h('select', {}, A.sillas.map(s => h('option', { value: s, selected: s === pre.silla }, SILLAS_NOMBRE[s] || s)));
  const per = h('select', {}, A.personas.filter(p => p.estado !== 'baja').map(p => h('option', { value: p.id }, nombre[p.id])));
  const desde = h('input', { type: 'date', value: ctx.hoy });
  const hasta = h('input', { type: 'date' });
  const supl = h('input', { type: 'checkbox' });
  const titular = h('select', {}, h('option', { value: '' }, '—'), A.personas.filter(p => p.estado === 'activo').map(p => h('option', { value: p.id }, nombre[p.id])));
  return panel({ titulo: 'Nueva asignación o suplencia', icono: 'mas', sub: 'Una asignación nueva de responsable en una silla no cierra la anterior: ciérrala en la tabla. Una suplencia necesita fecha de fin.' },
    h('div', { class: 'pm-form' },
      campo('Cliente', cli), campo('Silla', silla), campo('Persona', per),
      campo('Desde', desde), campo('Hasta', hasta), campo('Titular (si es suplencia)', titular),
      h('label', { class: 'fila', style: { minHeight: 'var(--s-10)', cursor: 'pointer' } }, supl, 'Es una suplencia'),
      botonConfirmar({ texto: 'Guardar', pregunta: '¿Guardar la asignación?', confirmar: 'Sí, guardar',
        alConfirmar: () => post(ctx, 'ajustes/asignacion', {
          operacion: 'crear', cliente_id: cli.value, silla: silla.value, persona_id: per.value, desde: desde.value || null,
          hasta: hasta.value || null, suplencia: supl.checked, titular_id: titular.value || null, principal: !supl.checked,
        }) })));
}

// ---------------------------------------------------------------- Para confirmar
function vistaConfirmar(A, ctx, editar, nombre, nomCli) {
  const bloques = { A: 'Dudas del portal de clientes', B: 'Otras dudas de account', C: 'Personas sin puesto claro', D: 'Publicidad sin trafficker o sin CRM' };
  const ultima = {};
  for (const d of A.decisiones) if (!(d.clave in ultima) && d.respuesta) ultima[d.clave] = d;
  const accounts = A.personas.filter(p => (p.puestos || []).includes('account') && p.estado === 'activo');
  const pendientes = A.para_confirmar.filter(d => !d.respondida).length;
  const out = [h('div', { class: 'fila' },
    chipEstado(pendientes ? 'ambar' : 'verde', `${pendientes} de ${A.para_confirmar.length} sin responder`),
    h('a', { class: 'bt', href: 'api/respuestas_mili', target: '_blank', rel: 'noopener' }, 'Descargar las respuestas de Mili'),
    h('span', { class: 'sub' }, 'Las respuestas que Mili mande por la página aparte se cargan en la siguiente recarga de datos.'))];
  for (const [b, titulo] of Object.entries(bloques)) {
    const ds = A.para_confirmar.filter(d => d.bloque === b);
    if (!ds.length) continue;
    out.push(panel({ titulo, icono: 'info', sub: `${ds.length} dudas` }, h('div', { class: 'cuerpo pila', style: { gap: 'var(--s-3)' } }, ds.map(d => tarjetaDuda(d, ctx, editar, nombre, nomCli, accounts, A, ultima[d.id])))));
  }
  return out;
}

function tarjetaDuda(d, ctx, editar, nombre, nomCli, accounts, A, previa) {
  const clientes = d.clientes?.length ? d.clientes : d.cliente_id ? [d.cliente_id] : [];
  let control = null, respuesta = null;
  if (d.tipo === 'asignacion' && clientes.length) {
    const candidatos = d.silla === 'account' ? accounts : A.personas.filter(p => p.estado === 'activo');
    const sel = h('select', { disabled: !editar, 'aria-label': `Persona para ${d.id}` },
      h('option', { value: '' }, '— elegir —'),
      candidatos.map(p => h('option', { value: p.id, selected: p.id === d.persona_propuesta }, `${nombre[p.id]}${p.id === d.persona_propuesta ? ' (propuesta)' : ''}`)));
    control = campo(`${SILLAS_NOMBRE[d.silla] || 'Account'} de ${clientes.map(c => nomCli[c] || c).join(', ')}`, sel);
    respuesta = () => sel.value ? clientes.map(c => ({ duda: d.id, tipo: 'asignacion', cliente_id: c, silla: d.silla || 'account', persona_id: sel.value, accion: 'poner' })) : null;
  } else if (d.tipo === 'persona' && d.persona_id) {
    const sel = h('select', { disabled: !editar, 'aria-label': `Estado de ${nombre[d.persona_id]}` },
      h('option', { value: '' }, '— solo nota —'), ['activo', 'dudoso'].map(v => h('option', { value: v }, `${nombre[d.persona_id]}: ${v}`)));
    control = campo('Estado', sel);
    respuesta = () => sel.value ? { duda: d.id, tipo: 'persona', persona_id: d.persona_id, cambios: { estado: sel.value } } : null;
  }
  const nota = h('input', { type: 'text', placeholder: 'Opcional; obligatoria si no eliges nada', disabled: !editar });
  return h('article', { class: 'panel pila', style: { padding: 'var(--s-4) var(--relleno)', gap: 'var(--s-2)', boxShadow: 'none' } },
    h('div', { class: 'fila', style: { justifyContent: 'space-between' } },
      h('b', { title: d.id, style: { font: 'var(--t-h3)', fontWeight: '700' } }, d.objeto),
      d.respondida || previa ? chipEstado('verde', `respondida${previa ? ` por ${nombre[previa.respondida_por] || previa.respondida_por} · ${fmt.fecha(previa.respondida)}` : ''}`) : chipEstado('ambar', 'sin responder')),
    d.ahora ? h('p', { class: 'sub' }, `Ahora: ${d.ahora}`) : null,
    h('p', { style: { maxWidth: '72ch' } }, d.choque),
    h('p', { style: { maxWidth: '72ch' } }, h('b', {}, 'Propuesta: '), d.propuesta || '—'),
    editar ? h('div', { class: 'pm-form' }, control, campo('Nota', nota), botonConfirmar({
      texto: d.respondida ? 'Cambiar respuesta' : 'Guardar respuesta', pregunta: `¿Guardar la respuesta a ${d.id}?`, confirmar: 'Sí, guardar',
      alConfirmar: async () => {
        let r = respuesta ? respuesta() : null;
        if (!r) {
          if (!nota.value.trim()) throw new Error('elige una opción o escribe una nota');
          r = { duda: d.id, tipo: 'nota', nota: nota.value.trim() };
        } else if (nota.value.trim()) (Array.isArray(r) ? r : [r]).forEach(x => { x.nota = nota.value.trim(); });
        return post(ctx, 'ajustes/confirmar', { respuesta: r });
      },
    })) : control);
}

// ---------------------------------------------------------------- Ver como
function vistaVerComo(A, ctx) {
  const puede = ctx.ver({ tipo: 'ver_como' }).ok && !ctx.soloLectura;
  const grupos = PUESTOS.map(pu => {
    const ps = A.personas.filter(p => (p.puestos || []).includes(pu.id) && p.estado !== 'baja');
    return h('div', { class: 'fila' }, h('b', { style: { minWidth: 'min(100%, 210px)' } }, pu.nombre),
      ps.length ? ps.map(p => h('button', { type: 'button', class: 'bt mini', disabled: !puede, on: { click: () => verComo(p.id) } }, p.alias || p.nombre))
        : chipEstado('ambar', 'sin persona'));
  });
  return [panel({ titulo: 'Ver como', icono: 'ojo', sub: 'Solo lectura. Cada «ver como» queda en el rastro del servidor con la hora. Mili y Tomás.' },
    h('div', { class: 'cuerpo pila' }, grupos))];
}

function verComo(id) {
  const sel = document.getElementById('vercomo-sel');
  if (!sel) return;
  sel.value = id;
  sel.dispatchEvent(new Event('change'));
}

async function post(ctx, ruta, cuerpo) {
  await ctx.api(ruta, { metodo: 'POST', cuerpo });
  setTimeout(() => location.reload(), 700);
  return 'Guardado. Queda en el historial y en el rastro.';
}

// ---------------------------------------------------------------- Avisos y recargas (E0 ronda 3)
async function vistaAvisos(ctx) {
  let Av, Rc;
  try { [Av, Rc] = await Promise.all([ctx.api('avisos'), ctx.api('recarga')]); }
  catch (e) { return [estadoVacio({ titulo: 'Sin acceso a los avisos', porque: e.message })]; }
  const hoy = ctx.hoy;
  const deHoy = Av.avisos.filter(a => a.dia === hoy && a.estado === 'para_avisar').length;
  const tabla = tablaDensa({
    filas: Av.avisos,
    orden: { clave: 'id', dir: 'desc' },
    filtros: [{ clave: 'tipo', titulo: 'Tipo' }, { clave: 'estado', titulo: 'Estado' }],
    columnas: [
      { clave: 'dia', titulo: 'Día' },
      { clave: 'texto', titulo: 'Aviso', principal: true },
      { clave: 'tipo', titulo: 'Tipo', celda: a => chipEstado(a.tipo === 'fuente_rota' ? 'rojo' : a.tipo === 'recarga_fallida' ? 'rojo' : 'ambar', a.tipo.replace('_', ' ')) },
      { clave: 'estado', titulo: 'Estado', celda: a => chipEstado(a.estado === 'para_avisar' ? 'azul' : 'gris', a.estado === 'para_avisar' ? 'para avisar' : 'retenido (tope de 3)') },
      { clave: 'visto', titulo: 'Visto', ordenable: false, celda: a => a.visto ? `${a.visto_por} · ${a.visto} UTC`
        : ctx.soloLectura ? '—' : botonConfirmar({ texto: 'Visto', mini: true, pregunta: '¿Marcar como visto?', confirmar: 'Sí',
          alConfirmar: async () => { await ctx.api('avisos/visto', { metodo: 'POST', cuerpo: { id: a.id } }); return 'Visto'; } }) },
    ],
    vacio: { titulo: 'Ningún aviso', porque: 'Ninguna fuente rota, vieja de más ni recarga que falle dos veces seguidas.', celebrar: true },
  });
  // N16: `recargas` de local.db guarda pedida/terminada en UTC («AAAA-MM-DD HH:MM:SS»); se enseñan en hora de Madrid.
  const enMadrid = t => {
    if (!t) return '—';
    const s = String(t).trim().replace(' ', 'T');
    const iso = /(Z|[+-]\d\d:?\d\d)$/.test(s) ? s : `${s}Z`;
    const d = ctx.fechas.dia(iso), hm = ctx.fechas.hora(iso);
    return d && hm ? `${d} ${hm}` : String(t);
  };
  const recargas = tablaDensa({
    filas: Rc.recargas.map(r => ({ ...r, fallos: (r.pasos || []).filter(p => !p.ok).map(p => p.id).join(', ') || '—', n: (r.pasos || []).length })),
    orden: { clave: 'id', dir: 'desc' },
    columnas: [
      { clave: 'pedida', titulo: 'Pedida (Madrid)', celda: r => enMadrid(r.pedida) }, { clave: 'quien', titulo: 'Quién' },
      { clave: 'estado', titulo: 'Estado', celda: r => chipEstado({ ok: 'verde', con_fallos: 'rojo', en_curso: 'azul', pendiente: 'gris' }[r.estado] || 'gris', r.estado.replace('_', ' ')) },
      { clave: 'n', titulo: 'Pasos', num: true }, { clave: 'fallos', titulo: 'Fallaron', principal: true },
      { clave: 'terminada', titulo: 'Terminada (Madrid)', celda: r => r.terminada ? enMadrid(r.terminada) : '—' },
    ],
    vacio: { titulo: 'Nadie ha pedido una recarga', porque: 'El botón «Actualizar ahora» está arriba, junto al buscador (solo Mili y Tomás).' },
  });
  return [
    avisoParcial(`${Av.nota} Como mucho ${Av.tope_dia} avisos al día; el resto queda «retenido». Hoy: ${deHoy} de ${Av.tope_dia}.`, { tipo: 'info' }),
    panel({ titulo: 'Avisos a Tomás', icono: 'campana', sub: 'Fuente rota · fuente con el dato más viejo del doble de su límite · recarga que falla dos veces seguidas ' }, tabla),
    panel({ titulo: 'Recargas pedidas', icono: 'recargar', sub: 'Cola de «Actualizar ahora»: una a la vez' }, recargas),
  ];
}

// ---------------------------------------------------------------- Altas y bajas (N9, 2-oct noche)
// Dar de alta, cambiar o dar de baja a una persona en menos de 2 minutos y sin tocar código. El servidor (altas_personas.py)
// valida todo (puestos solo de Tomás, correo de entrada privado, sin teléfonos ni direcciones), lo guarda en el historial y
// devuelve la comprobación de permisos en llano. Cloudflare Access no se toca: queda la tarea para Tomás.
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const PAISES = ['España', 'Argentina', 'Venezuela', 'Colombia', 'México', 'Uruguay', 'Chile', 'Perú'];
const SUBS = [
  { valor: 'alta', texto: 'Añadir persona', icono: 'mas' },
  { valor: 'cambio', texto: 'Cambiar puesto, jefe o cartera', icono: 'editar' },
  { valor: 'baja', texto: 'Dar de baja', icono: 'baja' },
  { valor: 'tareas', texto: 'Tareas de acceso', icono: 'key' },
  { valor: 'departamentos', texto: 'Jefes de departamento', icono: 'eq' },
  { valor: 'dudas', texto: 'Dudas de Tomás', icono: 'flag' },
];

function vistaAltas(Al, ctx, editar) {
  const sub = SUBS.some(s => s.valor === ctx.params[1]) ? ctx.params[1] : 'alta';
  const pend = Al.tareas.filter(x => x.estado === 'pendiente').length;
  const dudas = Al.dudas.filter(d => !d.contestada).length;
  const chips = elegir(SUBS.map(s => ({ ...s, cuenta: s.valor === 'tareas' ? pend : s.valor === 'dudas' ? dudas : undefined, cuentaEstado: s.valor === 'tareas' && pend ? 'rojo' : '' })),
    { valor: sub, etiqueta: 'Qué quieres hacer', alCambiar: v => { location.hash = `#/ajustes/altas/${v}`; } });
  const pinta = { alta: altaPersona, cambio: cambioPersona, baja: bajaPersona, tareas: tareasAcceso, departamentos: jefesDepartamento, dudas: dudasTomas }[sub];
  return [h('div', { class: 'fila' }, chips), ...pinta(Al, ctx, editar)];
}

const plural = (n, s, p) => `${n} ${n === 1 ? s : (p || s + 's')}`;
const nomPer = Al => Object.fromEntries(Al.personas.map(p => [p.id, p.alias]));
const sillaTxt = s => SILLAS_NOMBRE[s] || s;
function selectorSimple(opciones, { valor, vacio, etiqueta, desactivado } = {}) {
  return h('select', { 'aria-label': etiqueta || null, disabled: desactivado || null },
    vacio !== undefined ? h('option', { value: '' }, vacio) : null,
    opciones.map(o => h('option', { value: o.valor, selected: String(o.valor) === String(valor ?? '') }, o.texto)));
}
function selectorCumple(valor) {
  const [mm, dd] = (valor || '').split('-');
  const dia = selectorSimple(Array.from({ length: 31 }, (_, i) => ({ valor: String(i + 1).padStart(2, '0'), texto: String(i + 1) })), { valor: dd, vacio: 'Día', etiqueta: 'Día del cumpleaños' });
  const mes = selectorSimple(MESES.map((m, i) => ({ valor: String(i + 1).padStart(2, '0'), texto: m })), { valor: mm, vacio: 'Mes', etiqueta: 'Mes del cumpleaños' });
  const caja = h('div', { class: 'fila', role: 'group', 'aria-label': 'Cumpleaños, día y mes' }, dia, mes);
  [dia, mes].forEach(s => Object.assign(s.style, { minHeight: 'var(--s-10)', flex: '1 1 0', minWidth: '0', width: 'auto' }));
  caja.style.flexWrap = 'nowrap';
  Object.defineProperty(caja, 'value', { get: () => (dia.value && mes.value ? `${mes.value}-${dia.value}` : '') });
  return caja;
}
function chipsPuestos(Al, marcados, { alCambiar, bloquear } = {}) {
  const grupos = [...new Set(PUESTOS.map(x => x.grupo))];
  return h('div', { class: 'pila', style: { gap: 'var(--s-2)' } }, grupos.map(g => h('fieldset', { class: 'fila', style: { border: '0', padding: '0', margin: '0' } },
    h('legend', { class: 'sub' }, g),
    PUESTOS.filter(x => x.grupo === g).map(x => {
      const fijo = !Al.puede_dar.includes(x.id) || bloquear;
      return h('label', { class: 'chip gris sin-punto', title: fijo && !bloquear ? 'Este puesto solo lo da Tomás' : null, style: { minHeight: '32px', cursor: fijo ? 'not-allowed' : 'pointer' } },
        h('input', { type: 'checkbox', value: x.id, checked: marcados.has(x.id), disabled: fijo,
          on: { change: e => { e.target.checked ? marcados.add(x.id) : marcados.delete(x.id); alCambiar?.(); } } }), ' ', x.nombre, fijo && !bloquear ? h('span', { class: 'sr' }, ' (solo Tomás)') : null);
    }))));
}

// Plantilla del puesto: qué hace y qué ve (lo calcula el servidor con las mismas reglas que aplica).
function tarjetaPlantilla(Al, puestos, nombre) {
  if (!puestos.length) return avisoParcial('Elige un puesto y aquí verás qué hace y qué verá.', { tipo: 'info' });
  const pls = puestos.map(p => Al.plantillas[p]).filter(Boolean);
  const pantallas = [...new Set(pls.flatMap(p => p.pantallas))];
  return h('div', { class: 'pm-tarjeta azul' },
    h('b', {}, pls.map(p => p.nombre).join(' + ')),
    h('dl', { class: 'pm-kv' },
      ...pls.flatMap(p => [h('dt', {}, `Qué hace (${p.nombre})`), h('dd', {}, p.que_hace)]),
      h('dt', {}, 'Clientes'), h('dd', {}, pls.map(p => p.clientes).join(' · ')),
      h('dt', {}, 'Pantallas'), h('dd', {}, `${pantallas.length}: ${pantallas.join(', ')}`),
      h('dt', {}, 'Jefe habitual'), h('dd', {}, pls.map(p => nombre[p.jefe_sugerido]).filter(Boolean).join(' · ') || 'sin uno fijo'),
      h('dt', {}, 'Guía de bienvenida'), h('dd', {}, [...new Set(pls.map(p => p.guia).filter(Boolean))].map(g => g.replace(/^\d+_|\.md$/g, '').replace(/_/g, ' ').toLowerCase()).join(' · ') || 'sin guía')),
    pls.some(p => p.solo_tomas) ? chipEstado('ambar', 'Puesto de mando: solo lo da Tomás') : null);
}

// Cartera por silla: cliente + silla + papel. Devuelve el editor y una función que da la lista.
function editorCartera(Al, sillas, inicial = []) {
  const filas = [...inicial];
  const nomCli = Object.fromEntries(Al.clientes.map(c => [c.id, c]));
  const lista = h('div', { class: 'fila' });
  const pintar = () => poner(lista, filas.length ? filas.map((x, i) => h('span', { class: 'chip azul sin-punto' },
    `${nomCli[x.cliente_id]?.nombre} · ${sillaTxt(x.silla)} · ${x.papel}`,
    h('button', { type: 'button', class: 'bt mini', 'aria-label': `Quitar ${nomCli[x.cliente_id]?.nombre}`, on: { click: () => { filas.splice(i, 1); pintar(); } } }, icono('cerrar', { clase: 's' }))))
    : h('span', { class: 'sub' }, 'Sin clientes todavía (es opcional: se pueden asignar luego).'));
  const silla = selectorSimple(sillas.map(s => ({ valor: s, texto: sillaTxt(s) })), { etiqueta: 'Silla' });
  const ahora = c => { const eq = nomCli[c]?.equipo?.[silla.value] || []; return eq.length ? ` · ahora: ${eq.join(', ')}` : ` · sin ${sillaTxt(silla.value)}`; };
  const cli = h('select', { 'aria-label': 'Cliente' });
  const pintarClientes = () => poner(cli, h('option', { value: '' }, 'Elige cliente…'),
    Al.clientes.slice().sort((a, b) => a.nombre.localeCompare(b.nombre, 'es')).map(c => h('option', { value: c.id }, c.nombre + ahora(c.id))));
  silla.addEventListener('change', pintarClientes);
  pintarClientes();
  const papel = selectorSimple([{ valor: 'responsable', texto: 'Responsable (sustituye al actual)' }, { valor: 'apoyo', texto: 'Apoyo (se suma)' }], { etiqueta: 'Papel' });
  const anadir = h('button', { type: 'button', class: 'bt', on: { click: () => {
    if (!cli.value || filas.some(x => x.cliente_id === cli.value && x.silla === silla.value)) return;
    filas.push({ cliente_id: cli.value, silla: silla.value, papel: papel.value }); pintar();
  } } }, icono('mas'), 'Añadir a su cartera');
  pintar();
  const caja = sillas.length
    ? h('div', { class: 'pila', style: { gap: 'var(--s-2)' } }, h('div', { class: 'pm-form' }, campo('Silla', silla), campo('Cliente', cli), campo('Papel', papel), h('div', {}, anadir)), lista)
    : h('p', { class: 'sub' }, 'Este puesto no trabaja por cartera de clientes.');
  return { caja, lista: () => filas.slice() };
}

// Resultado de la comprobación de permisos: qué verá, qué no, pruebas y 3 pantallas en «ver como».
function resultadoComprobacion(R, ctx, { titulo, diferencia, extra } = {}) {
  const verComoOk = ctx.ver({ tipo: 'ver_como' }).ok && R.persona.estado === 'activo';
  const pruebas = R.pruebas.map(p => ({ icono: p.ok ? 'ok' : p.aviso ? 'alert' : 'cerrar', estado: p.ok ? 'verde' : p.aviso ? 'ambar' : 'rojo', texto: p.texto }));
  const muestras = h('div', { class: 'fila' }, R.muestras.map(m => h('a', {
    class: 'bt', style: { whiteSpace: 'normal', maxWidth: '100%', height: 'auto', textAlign: 'left' }, href: verComoOk ? `?como=${encodeURIComponent(R.persona.id)}${m.ruta}` : null, 'aria-disabled': verComoOk ? null : 'true',
    title: m.espera }, icono('ojo'), `Ver como ${R.persona.alias}: ${m.titulo}`)));
  const guia = h('div');
  const botonesGuia = h('div', { class: 'fila' }, (R.guias || []).map(g => h('button', { type: 'button', class: 'bt', on: { click: async () => {
    try {
      const r = await ctx.api(`altas/guia?puesto=${encodeURIComponent(guiaPuesto(R, g))}`);
      poner(guia, r.texto ? h('div', { class: 'pm-texto pila', tabindex: '0', 'aria-label': `Guía ${g}` }, guiaLegible(r.texto)) : avisoParcial(r.motivo || 'Sin guía.', { tipo: 'info' }));
    } catch (e) { poner(guia, avisoParcial(e.message, { tipo: 'info' })); }
  } } }, icono('libro'), `Guía de bienvenida: ${g.replace(/^\d+_|\.md$/g, '').replace(/_/g, ' ').toLowerCase()}`)));
  return panel({ titulo: titulo || `Comprobación de ${R.persona.alias}`, icono: 'escudo', sub: R.resumen },
    h('div', { class: 'cuerpo pila' },
      h('div', { class: 'fila' }, chipEstado(R.todo_bien ? 'verde' : 'rojo', R.todo_bien ? 'Permisos comprobados: todo bien' : 'Hay algo que revisar'),
        chipEstado('gris', plural(R.pantallas.length, 'pantalla')), chipEstado('gris', `${plural(R.detalle.length, 'cliente')} con detalle`)),
      extra || null,
      diferencia ? avisoParcial(diferencia.join(' '), { tipo: 'info', titulo: 'Qué cambia' }) : null,
      h('div', { class: 'pm-tarjetas' },
        h('div', { class: 'pm-tarjeta verde' }, h('b', {}, 'Verá'), listaLarga(R.ve)),
        h('div', { class: 'pm-tarjeta gris' }, h('b', {}, 'No verá'), listaLarga(R.no_ve))),
      h('div', {}, h('b', {}, 'Comprobación automática'), listaIconos(pruebas)),
      h('div', {}, h('b', {}, 'Tres pantallas de muestra en «ver como»'),
        h('p', { class: 'sub' }, verComoOk ? 'Se abren en solo lectura y quedan en el rastro. La tercera tiene que decir que ese cliente no es suyo.' : 'Se podrán abrir cuando esté activa (el día de su entrada).'), muestras),
      R.guias?.length ? h('div', {}, h('b', {}, 'Guía de bienvenida de su puesto'), h('p', { class: 'sub' }, 'Mándasela el primer día; está en la carpeta de la guía del equipo.'), botonesGuia, guia) : null));
}
// Lista con icono que no corta el texto (listaConIcono lo recorta a una línea).
const listaIconos = items => h('ul', { class: 'pila', style: { margin: '0', padding: '0', listStyle: 'none', gap: 'var(--s-2)' } }, items.map(it => h('li', { class: 'fila', style: { flexWrap: 'nowrap', alignItems: 'flex-start' } },
  h('span', { class: `ico-c s ${it.estado || 'gris'}`, style: { flex: 'none' } }, icono(it.icono || 'info')), h('span', { style: { minWidth: '0', overflowWrap: 'anywhere' } }, it.texto))));
// Listas largas sin cortar el texto (listaConIcono recorta a una línea).
const listaLarga = textos => h('ul', { class: 'pila', style: { margin: '0', paddingLeft: 'var(--s-4)', gap: 'var(--s-1)' } }, textos.map(t => h('li', {}, t)));
// La guía es Markdown: títulos en negrita, tablas en líneas con «·», sin asteriscos.
function guiaLegible(md) {
  return md.split('\n').filter(l => l.trim() && !/^\|?\s*-{3,}/.test(l.trim())).map(l => {
    const limpio = l.replace(/\*\*/g, '').replace(/`/g, '');
    if (/^#+\s/.test(limpio)) return h('b', {}, limpio.replace(/^#+\s*/, ''));
    if (limpio.trim().startsWith('|')) return h('span', {}, limpio.trim().replace(/^\||\|$/g, '').split('|').map(x => x.trim()).filter(Boolean).join(' · '));
    return h('span', {}, limpio.replace(/^\s*[-*]\s+/, '• '));
  });
}
function guiaPuesto(R, g) {
  const mapa = { '06_ACCOUNTS.md': 'account', '07_PUBLICIDAD.md': 'trafficker', '08_CRM.md': 'especialista_ghl', '09_ALTAS_AGUS.md': 'tecnico_altas',
    '10_SEO_Y_FICHA_DE_GOOGLE.md': 'seo', '11_WEB.md': 'web', '12_REDES.md': 'redes', '13_PRODUCCION.md': 'produccion', '14_SETTERS.md': 'setters',
    '15_OUTREACH.md': 'outreach', '01_DIRECCION_TOMAS.md': 'direccion', '02_ADMINISTRACION_SOFIA.md': 'administracion', '03_OPERACIONES_MILI.md': 'operaciones',
    '04_PROYECTOS_Y_SEO_COTI.md': 'proyectos', '05_RRHH_CECILIA.md': 'rrhh' };
  return mapa[g] || R.persona.puestos[0];
}

// -- Añadir persona
function altaPersona(Al, ctx, editar) {
  const nombre = nomPer(Al);
  const activas = Al.personas.filter(p => p.estado === 'activo');
  const marcados = new Set();
  const resultado = h('div');
  const nom = h('input', { type: 'text', autocomplete: 'off', placeholder: 'Nombre y apellido', maxlength: '80' });
  const entrada = h('input', { type: 'date', value: Al.hoy });
  const cumple = selectorCumple('');
  const zona = selectorSimple(Al.zonas.map(z => ({ valor: z.id, texto: z.texto })), { valor: 'America/Argentina/Buenos_Aires', etiqueta: 'Zona horaria' });
  const jefe = selectorSimple(activas.map(p => ({ valor: p.id, texto: p.alias })).sort((a, b) => a.texto.localeCompare(b.texto, 'es')), { vacio: 'Elige su jefe…', etiqueta: 'Jefe' });
  const correo = h('input', { type: 'email', autocomplete: 'off', placeholder: `nombre${Al.dominios[0]}` });
  const plantilla = h('div');
  const carteraZona = h('div');
  let cartera = editorCartera(Al, []);
  const alCambiarPuesto = () => {
    const pu = [...marcados];
    poner(plantilla, tarjetaPlantilla(Al, pu, nombre));
    const sug = pu.map(x => Al.plantillas[x]?.jefe_sugerido).find(Boolean);
    if (sug && !jefe.dataset.tocado) jefe.value = sug;
    const sillas = [...new Set(pu.flatMap(x => Al.plantillas[x]?.sillas || []))];
    cartera = editorCartera(Al, sillas, cartera.lista().filter(x => sillas.includes(x.silla)));
    poner(carteraZona, cartera.caja);
  };
  jefe.addEventListener('change', () => { jefe.dataset.tocado = '1'; });
  alCambiarPuesto();
  const paso = (n, titulo, sub, ...cuerpo) => h('div', { class: 'pila', style: { gap: 'var(--s-2)' } },
    h('b', {}, `${n}. ${titulo}`), sub ? h('p', { class: 'sub' }, sub) : null, ...cuerpo);
  const form = panel({ titulo: 'Añadir persona', icono: 'mas', sub: 'Cuatro pasos. Solo se guardan nombre, puesto, jefe, zona, fechas y cumpleaños (día y mes); nunca teléfonos, direcciones ni correos personales.' },
    h('div', { class: 'cuerpo pila' },
      paso(1, 'Quién es', null, h('div', { class: 'pm-form' }, campo('Nombre y apellido', nom), campo('Fecha de entrada', entrada), campo('Cumpleaños (día y mes)', cumple), campo('Zona horaria', zona))),
      paso(2, 'Puesto y jefe', Al.esTomas ? 'Puede tener varios puestos: la app le suma las vistas.' : 'Los puestos de mando (dirección, finanzas, RRHH, operaciones, ventas de RO y administración) solo los da Tomás.',
        chipsPuestos(Al, marcados, { alCambiar: alCambiarPuesto, bloquear: !editar }), plantilla, h('div', { class: 'pm-form' }, campo('Jefe', jefe))),
      paso(3, 'Cartera inicial (opcional)', 'Por silla. «Responsable» sustituye a quien la lleva hoy (se cierra con fecha de ayer, no se borra).', carteraZona),
      paso(4, 'Correo de entrada', `El de la empresa (${Al.dominios.join(' o ')})${Al.esTomas ? '; otro, si lo decides tú' : '; otro, solo si lo dice Tomás'}. Es privado: no lo ve el equipo. Se crea la tarea para que Tomás lo añada a Cloudflare Access.`,
        h('div', { class: 'pm-form' }, campo('Correo de entrada', correo))),
      editar ? h('div', { class: 'fila' }, botonConfirmar({
        texto: 'Dar de alta', pregunta: '¿Dar de alta con estos datos?', confirmar: 'Sí, dar de alta',
        alConfirmar: async () => {
          const r = await ctx.api('altas/alta', { metodo: 'POST', cuerpo: {
            nombre: nom.value, puestos: [...marcados], jefe: jefe.value || null, zona: zona.value, fecha_entrada: entrada.value || null,
            cumple: cumple.value || null, correo_entrada: correo.value.trim() || null, cartera: cartera.lista() } });
          poner(resultado, resultadoComprobacion(r.comprobacion, ctx, { titulo: `${r.alias} ya está dada de alta`,
            extra: listaIconos([
              { icono: 'cartera', estado: 'azul', texto: r.asignaciones ? `${plural(r.asignaciones, 'cliente')} en su cartera${r.sustituidas ? ` (sustituye en ${r.sustituidas})` : ''}.` : 'Sin cartera todavía.' },
              { icono: 'key', estado: r.tarea_access ? 'ambar' : 'rojo', texto: r.tarea_access ? 'Tarea guardada para Tomás: añadir su correo a Cloudflare Access. El acceso externo está pendiente de confirmación.' : 'Sin correo de entrada: no podrá entrar hasta que se lo pongáis.' },
              ...(r.pendientes_locales?.length ? [{ icono: 'hist', estado: 'ambar', texto: 'Alta guardada; quedan actualizaciones locales pendientes. Reintenta con los mismos datos para completarlas sin duplicar la persona.' }] : []),
              { icono: 'hist', estado: 'gris', texto: r.recarga_pedida ? 'Queda en el historial y en el rastro. Recarga de datos pedida: sus alertas, chat y agenda llegan cuando termine.' : 'Queda en el historial y en el rastro. Sus datos de cada pantalla llegan con la próxima recarga.' },
            ]) }));
          resultado.scrollIntoView({ block: 'start', behavior: 'smooth' });
          return `${r.alias} dada de alta`;
        },
      })) : avisoParcial('Solo lectura: las altas las hacen Mili y Tomás.', { tipo: 'info' })));
  return [form, resultado];
}

// -- Cambiar puesto, jefe, zona, datos básicos, correo de entrada o cartera
function cambioPersona(Al, ctx, editar) {
  const nombre = nomPer(Al);
  const zona = h('div');
  const lista = Al.personas.filter(p => p.estado !== 'baja').sort((a, b) => a.alias.localeCompare(b.alias, 'es'));
  const sel = selectorPersona({ personas: lista.map(p => ({ ...p, nombre: p.alias, puesto: p.puestos.map(x => PUESTO[x]?.nombre || x).join(' · ') })),
    actual: null, etiqueta: 'Elegir persona', alElegir: p => poner(zona, formCambio(Al, ctx, editar, p, nombre)) });
  return [panel({ titulo: 'Cambiar puesto, jefe o cartera', icono: 'editar', sub: 'Al guardar se vuelve a comprobar qué verá y qué deja de ver. A quien tiene un puesto de mando solo lo cambia Tomás.' },
    h('div', { class: 'cuerpo pila' }, campo('Persona', sel), zona))];
}
function formCambio(Al, ctx, editar, p, nombre) {
  const bloqueada = !editar || (p.mando && !Al.esTomas);
  const marcados = new Set(p.puestos);
  const resultado = h('div');
  const jefe = selectorSimple(Al.personas.filter(x => x.estado === 'activo' && x.id !== p.id).map(x => ({ valor: x.id, texto: x.alias })).sort((a, b) => a.texto.localeCompare(b.texto, 'es')),
    { valor: p.jefe, vacio: '— sin jefe —', etiqueta: 'Jefe', desactivado: bloqueada });
  const zonaSel = selectorSimple(Al.zonas.map(z => ({ valor: z.id, texto: z.texto })), { valor: p.zona, etiqueta: 'Zona horaria', desactivado: bloqueada });
  const pais = selectorSimple(PAISES.map(x => ({ valor: x, texto: x })), { valor: '', vacio: 'Sin cambiar', etiqueta: 'País', desactivado: bloqueada });
  const ingreso = h('input', { type: 'date', value: p.fecha_ingreso || '', disabled: bloqueada || null });
  const cumple = selectorCumple(p.cumple_dia_mes);
  const rol = h('input', { type: 'text', maxlength: '80', placeholder: 'Rol de la plantilla (texto)', disabled: bloqueada || null });
  const correo = h('input', { type: 'email', autocomplete: 'off', placeholder: p.tiene_correo_entrada ? 'Tiene correo: escribe uno nuevo solo para cambiarlo' : 'Sin correo de entrada: escríbelo', disabled: bloqueada || null });
  const actuales = Al.asignaciones.filter(a => a.persona_id === p.id);
  const quitar = new Set();
  const nomCli = Object.fromEntries(Al.clientes.map(c => [c.id, c.nombre]));
  const carteraActual = actuales.length ? h('div', { class: 'fila' }, actuales.map(a => h('label', { class: 'chip gris sin-punto', style: { minHeight: '32px', cursor: bloqueada ? 'default' : 'pointer' } },
    h('input', { type: 'checkbox', disabled: bloqueada || null, on: { change: e => { const k = `${a.cliente_id}|${a.silla}`; e.target.checked ? quitar.add(k) : quitar.delete(k); } } }),
    ` Quitar ${nomCli[a.cliente_id] || a.cliente_id} · ${sillaTxt(a.silla)}`))) : h('p', { class: 'sub' }, 'Sin cartera vigente.');
  const zonaCartera = h('div');
  let cartera;
  const alCambiarPuesto = () => {
    const sillas = [...new Set([...marcados].flatMap(x => Al.plantillas[x]?.sillas || []))];
    cartera = editorCartera(Al, sillas, cartera ? cartera.lista().filter(x => sillas.includes(x.silla)) : []);
    poner(zonaCartera, cartera.caja);
  };
  alCambiarPuesto();
  const comprobar = async () => {
    try { poner(resultado, resultadoComprobacion(await ctx.api(`altas/comprobar?id=${encodeURIComponent(p.id)}`), ctx)); }
    catch (e) { poner(resultado, avisoParcial(e.message)); }
  };
  return h('div', { class: 'pila' },
    bloqueada && editar ? avisoParcial('Tiene un puesto de mando: sus datos solo los cambia Tomás. Puedes comprobar sus permisos.', { tipo: 'info' }) : null,
    h('b', {}, 'Puestos'), chipsPuestos(Al, marcados, { alCambiar: alCambiarPuesto, bloquear: bloqueada }),
    h('div', { class: 'pm-form' }, campo('Jefe', jefe), campo('Zona horaria', zonaSel), campo('País', pais), campo('Fecha de ingreso', ingreso), campo('Cumpleaños (día y mes)', cumple), campo('Rol', rol), campo('Correo de entrada (privado)', correo)),
    h('b', {}, 'Cartera'), carteraActual, h('p', { class: 'sub' }, 'Al cambiar de puesto, la cartera de las sillas que ya no son suyas se cierra sola (con fecha) y te propongo a quién pasa.'), zonaCartera,
    h('div', { class: 'fila' },
      h('button', { type: 'button', class: 'bt', on: { click: comprobar } }, icono('escudo'), 'Comprobar sus permisos'),
      !bloqueada ? botonConfirmar({ texto: 'Guardar cambios', pregunta: `¿Guardar los cambios de ${p.alias}?`, confirmar: 'Sí, guardar',
        alConfirmar: async () => {
          const cuerpo = { id: p.id, puestos: [...marcados], jefe: jefe.value || null, zona: zonaSel.value, cartera_anadir: cartera.lista(),
            cartera_quitar: [...quitar].map(k => { const [cliente_id, silla] = k.split('|'); return { cliente_id, silla }; }) };
          if (pais.value) cuerpo.pais = pais.value;
          if (ingreso.value) cuerpo.fecha_ingreso = ingreso.value;
          if (cumple.value) cuerpo.cumple = cumple.value;
          if (rol.value.trim()) cuerpo.rol = rol.value.trim();
          if (correo.value.trim()) cuerpo.correo_entrada = correo.value.trim();
          const r = await ctx.api('altas/cambio', { metodo: 'POST', cuerpo });
          poner(resultado, resultadoComprobacion(r.comprobacion, ctx, { titulo: `${p.alias}: cambios guardados`, diferencia: r.diferencia,
            extra: r.propuesta?.length ? tablaReparto(Al, ctx, p, r.propuesta) : null }));
          return 'Guardado en el historial';
        } }) : null),
    resultado);
}

// Propuesta de reparto (baja o cambio de puesto): Mili o Tomás eligen y reparten.
function tablaReparto(Al, ctx, p, propuesta) {
  const sinNadie = propuesta.filter(x => !x.ya_tiene.length);
  const selects = {};
  const tabla = tablaApilable({
    filas: propuesta,
    columnas: [
      { clave: 'cliente', titulo: 'Cliente', principal: true },
      { clave: 'silla_txt', titulo: 'Silla' },
      { clave: 'propuesta', titulo: 'Pasa a', celda: x => x.ya_tiene.length ? h('span', { class: 'sub' }, `Sigue con ${x.ya_tiene.join(', ')}: no hace falta`)
        : (selects[`${x.cliente_id}|${x.silla}`] = selectorSimple(x.candidatos.map(c => ({ valor: c.id, texto: `${c.alias} (lleva ${c.lleva})` })), { valor: x.propuesta, vacio: 'Elegir…', etiqueta: `Quién lleva ${x.cliente}` })) },
    ],
  });
  return h('div', { class: 'pila' },
    h('b', {}, `Propuesta de reparto de la cartera de ${p.alias}`),
    h('p', { class: 'sub' }, 'Misma silla, mismo jefe primero y, entre ellos, quien menos clientes lleva. Lo decides tú.'),
    tabla,
    sinNadie.length && !ctx.soloLectura ? botonConfirmar({ texto: 'Repartir', pregunta: `¿Repartir ${plural(sinNadie.length, 'cliente')} así?`, confirmar: 'Sí, repartir',
      alConfirmar: async () => {
        const filas = sinNadie.map(x => ({ cliente_id: x.cliente_id, silla: x.silla, persona_id: selects[`${x.cliente_id}|${x.silla}`]?.value })).filter(x => x.persona_id);
        if (!filas.length) throw new Error('elige a quién pasa cada cliente');
        const r = await ctx.api('altas/repartir', { metodo: 'POST', cuerpo: { de: p.id, filas } });
        return `${plural(r.repartidas, 'cliente repartido', 'clientes repartidos')}`;
      } }) : chipEstado('verde', 'Ningún cliente se queda sin nadie'));
}

// -- Dar de baja
function bajaPersona(Al, ctx, editar) {
  const zona = h('div');
  const lista = Al.personas.filter(p => p.estado !== 'baja' && p.id !== ctx.real?.id).sort((a, b) => a.alias.localeCompare(b.alias, 'es'));
  const sel = selectorPersona({ personas: lista.map(p => ({ ...p, nombre: p.alias, puesto: p.puestos.map(x => PUESTO[x]?.nombre || x).join(' · ') })),
    actual: null, etiqueta: 'Elegir persona', alElegir: p => {
      const bloqueada = !editar || (p.mando && !Al.esTomas);
      const fecha = h('input', { type: 'date', value: Al.hoy, disabled: bloqueada || null });
      const resultado = h('div');
      const n = Al.asignaciones.filter(a => a.persona_id === p.id).length;
      poner(zona, h('div', { class: 'pila' },
        listaIconos([
          { icono: 'key', estado: 'ambar', texto: 'Se le quita la entrada a la app al momento y queda la tarea para Tomás de quitarla de Cloudflare Access.' },
          { icono: 'cartera', estado: 'azul', texto: `${plural(n, 'asignación vigente', 'asignaciones vigentes')}: se cierran con la fecha de baja (no se borran) y te propongo a quién pasan.` },
          { icono: 'hist', estado: 'gris', texto: 'Su historia (horas, notas, rastro) se queda.' },
        ]),
        h('div', { class: 'pm-form' }, campo('Fecha de baja', fecha)),
        bloqueada ? avisoParcial(editar ? 'Tiene un puesto de mando: su baja la da Tomás.' : 'Solo lectura.', { tipo: 'info' })
          : botonConfirmar({ texto: `Dar de baja a ${p.alias}`, peligro: true, pregunta: `¿Dar de baja a ${p.alias} el ${fmt.fecha(fecha.value)}?`, confirmar: 'Sí, dar de baja',
            alConfirmar: async () => {
              const r = await ctx.api('altas/baja', { metodo: 'POST', cuerpo: { id: p.id, fecha: fecha.value } });
              poner(resultado, panel({ titulo: `${p.alias} está de baja`, icono: 'baja', sub: `${plural(r.cerradas, 'asignación cerrada', 'asignaciones cerradas')} con fecha` },
                h('div', { class: 'cuerpo pila' },
                  listaIconos([{ icono: 'key', estado: 'ambar', texto: 'Tarea para Tomás: quitarla de Cloudflare Access (lista de acceso actualizada).' },
                    r.tarea_reparto ? { icono: 'cartera', estado: 'ambar', texto: 'Tarea: repartir su cartera (abajo, la propuesta).' } : { icono: 'ok', estado: 'verde', texto: 'Ningún cliente se queda sin nadie.' }]),
                  r.propuesta?.length ? tablaReparto(Al, ctx, p, r.propuesta) : null)));
              return 'Baja guardada';
            } }),
        resultado));
    } });
  return [panel({ titulo: 'Dar de baja', icono: 'baja', sub: 'Quitar accesos y repartir la cartera. Nada se borra.' }, h('div', { class: 'cuerpo pila' }, campo('Persona', sel), zona))];
}

// -- Tareas de acceso (Cloudflare Access) y de reparto
function tareasAcceso(Al, ctx) {
  const TXT = { access_anadir: 'Añadir a Cloudflare Access', access_quitar: 'Quitar de Cloudflare Access', repartir_cartera: 'Repartir la cartera' };
  return [
    avisoParcial(Al.esTomas ? 'La app no toca Cloudflare: añade o quita el correo en Cloudflare Access y marca la tarea como hecha. La lista completa está en despliegue/lista_access.txt.'
      : 'Las tareas de Cloudflare Access las hace y las marca Tomás. El correo se ve tapado.', { tipo: 'info' }),
    panel({ titulo: 'Tareas de acceso y reparto', icono: 'key', sub: 'Se crean solas al dar de alta, cambiar el correo o dar de baja' },
      tablaApilable({
        filas: Al.tareas,
        vacio: { titulo: 'Ninguna tarea', porque: 'No hay altas ni bajas pendientes de pasar a Cloudflare Access.', celebrar: true },
        columnas: [
          { clave: 'tipo', titulo: 'Qué', principal: true, celda: t => TXT[t.tipo] || t.tipo },
          { clave: 'persona', titulo: 'Persona' },
          { clave: 'correo', titulo: 'Correo de entrada', celda: t => t.correo || '—' },
          { clave: 'texto', titulo: 'Detalle', celda: t => h('span', { class: 'sub' }, t.texto) },
          { clave: 'creada', titulo: 'Creada', celda: t => fmt.fecha(t.creada?.slice(0, 10)) },
          { clave: 'estado', titulo: 'Estado', celda: t => t.estado === 'hecha' ? chipEstado('verde', `hecha · ${fmt.fecha(t.hecha?.slice(0, 10))}`)
            : (t.tipo.startsWith('access') && Al.esTomas && !ctx.soloLectura) ? botonConfirmar({ texto: 'Hecha', mini: true, pregunta: '¿Ya está en Cloudflare?', confirmar: 'Sí',
              alConfirmar: async () => { await ctx.api('altas/tarea_hecha', { metodo: 'POST', cuerpo: { id: t.id } }); return 'Hecha'; } })
            : chipEstado('ambar', t.tipo === 'repartir_cartera' ? 'pendiente: reparte en «Dar de baja»' : 'pendiente de Tomás') },
        ],
      })),
  ];
}

// -- Jefes de departamento (data/departamentos.json): a quién suben las alertas. Solo Tomás los cambia.
function jefesDepartamento(Al, ctx) {
  const nombre = nomPer(Al);
  const activas = Al.personas.filter(p => p.estado === 'activo').sort((a, b) => a.alias.localeCompare(b.alias, 'es'));
  const filas = Object.entries(Al.departamentos).map(([id, d]) => ({ id, ...d }));
  return [panel({ titulo: 'Jefes de departamento', icono: 'eq', sub: 'A quién suben las alertas de cada departamento. Antes estaban escritos en el código; ahora se cambian aquí (solo Tomás) y queda en el historial.' },
    tablaApilable({
      filas,
      columnas: [
        { clave: 'nombre', titulo: 'Departamento', principal: true },
        { clave: 'jefe', titulo: 'Jefe', celda: d => {
          if (!Al.esTomas || ctx.soloLectura) return nombre[d.jefe] || d.jefe;
          const s = selectorSimple(activas.map(p => ({ valor: p.id, texto: p.alias })), { valor: d.jefe, etiqueta: `Jefe de ${d.nombre}` });
          return h('span', { class: 'fila' }, s, botonConfirmar({ texto: 'Guardar', mini: true, pregunta: `¿Cambiar el jefe de ${d.nombre}?`, confirmar: 'Sí',
            alConfirmar: () => post(ctx, 'altas/departamento', { departamento: d.id, jefe: s.value }) }));
        } },
        { clave: 'jefe_origen', titulo: 'De dónde sale', celda: d => d.pendiente ? chipEstado('ambar', d.pendiente) : h('span', { class: 'sub' }, d.jefe_origen || '—') },
      ],
    }))];
}

// -- Dudas que solo decide Tomás (auditoría 36): no se tocan aquí; se suben a Decisiones con un clic.
function dudasTomas(Al, ctx) {
  return [avisoParcial('Estas decisiones son de Tomás: la app no cambia nada hasta que decida. Súbelas a «Decisiones» para que le llegue con tu recomendación.', { tipo: 'info' }),
    h('div', { class: 'pm-tarjetas' }, Al.dudas.map(d => h('article', { class: `pm-tarjeta ${d.contestada ? 'verde' : 'ambar'}` },
      h('b', {}, d.titulo),
      h('p', {}, d.problema),
      h('p', {}, h('b', {}, 'Recomendación: '), d.recomendacion),
      h('p', { class: 'sub' }, d.fuente),
      d.contestada ? chipEstado('verde', 'Contestada en Decisiones') : d.subida ? h('a', { class: 'bt', href: '#/decisiones' }, icono('flag'), 'Subida: ver en Decisiones')
        : ctx.soloLectura ? null : botonConfirmar({ texto: 'Subir a Decisiones de Tomás', pregunta: '¿Subirla con esta recomendación?', confirmar: 'Sí, subir',
          alConfirmar: () => post(ctx, 'decisiones', { operacion: 'nueva', tipo: 'para_tomas', clave: d.clave, titulo: d.titulo, problema: d.problema, recomendacion: d.recomendacion }) }))))];
}
