// modulos/informes_mensuales.js · M13 «Informes mensuales» (E3 del plan v2 · punto 2 de Mili · D-09).
// Por cliente y mes: HECHO (tarea del informe cerrada en ClickUp), ENVIADO (correo saliente en Desk al cliente con
// «informe/resultados/reporte» y el mes en el asunto), PENDIENTE (lo demás). Plazo: verde si sale el día 5 incluido;
// desde el día 6, rojo con aviso a Mili. Exentos: mantenimiento. Botón «Enviado por otra vía» con motivo (cola simulada).
// Datos: data/informes/informes.json (fuentes_informes/generar_informes.py), recortado por servir.py: cada account solo
// recibe las filas de sus clientes (cliente_id). Histórico de la hoja de Zoho Sheet: llega con W5 (importador preparado).

import {
  h, fmt, icono, tile, tiles, chipEstado, chipsFiltro, vacio, vacioLinea, avisoParcial, panel, frescura,
  logoCliente, iniciales, tablaDensa, tablaApilable, avisoFlotante, campoTexto,
} from '../componentes.js';

// Revisión 44 (textos cortados): lo que la pantalla corta con «…» (una línea o el límite de líneas) lleva el texto entero
// en el title, para que la regla de la tarjeta o el nombre largo no se pierdan. Mira el contenedor mientras se pinta.
const _SEL_CORTE = '.tile .tx, .tile .tt span, .tile em, .det, .mot, .sub, .t, td, .chip, summary, b, small';
function vigilarCortes(raiz) {
  if (!raiz || raiz.__cortes) return;
  raiz.__cortes = true;
  let t = 0;
  const mirar = () => { t = 0; for (const el of raiz.querySelectorAll(_SEL_CORTE)) {
    if (el.title || el.closest('[title]') !== null && el.closest('[title]') !== el || !el.isConnected) continue;
    if (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 2) { const s = el.textContent.trim(); if (s && s.length > 8) el.title = s; } } };
  new MutationObserver(() => { if (!t) t = setTimeout(mirar, 400); }).observe(raiz, { childList: true, subtree: true });
  if (typeof ResizeObserver !== 'undefined') new ResizeObserver(() => { if (!t) t = setTimeout(mirar, 400); }).observe(raiz);
}

// Revisión 44 (§2.3): fechas con el formato único de la app: «2-oct» y «2-oct, 17:34» (nunca «2 oct» ni «sept»).
const _MES3 = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const _fechaDe = iso => (iso ? new Date(String(iso).length <= 10 ? `${iso}T12:00:00` : String(iso).replace(' ', 'T')) : null);
const fDiaRO = iso => { const d = _fechaDe(iso); return !d ? '—' : Number.isNaN(+d) ? String(iso) : `${d.getDate()}-${_MES3[d.getMonth()]}`; };
const fDiaHoraRO = iso => { const d = _fechaDe(iso); return !d ? '—' : Number.isNaN(+d) ? String(iso) : `${d.getDate()}-${_MES3[d.getMonth()]}, ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; };

const ID = 'informes-mensuales';
const MES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const Mayus = t => (t ? t[0].toUpperCase() + t.slice(1) : t);
const nombreMes = m => MES[Number(m.slice(5, 7)) - 1] || m;
const mesSiguiente = m => { const [a, b] = m.split('-').map(Number); return b === 12 ? `${a + 1}-01` : `${a}-${String(b + 1).padStart(2, '0')}`; };
const diaSemana = iso => new Date(iso + 'T12:00:00').toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long' });

// Estado → chip, icono y orden (lo que pide acción, arriba)
const EST = {
  sin_tarea: { texto: 'Sin tarea', icono: 'alert', orden: 0 },
  en_curso: { texto: 'En curso', icono: 'clock', orden: 1 },
  hecho: { texto: 'Hecho, sin enviar', icono: 'send', orden: 2 },
  enviado: { texto: 'Enviado', icono: 'ok', orden: 3 },
  otra_via: { texto: 'Enviado por otra vía', icono: 'ok', orden: 4 },
  exento: { texto: 'Exento', icono: 'escudo', orden: 5 },
  no_aplica: { texto: 'No aplica', icono: 'info', orden: 6 },
};
const PENDIENTES = new Set(['sin_tarea', 'en_curso', 'hecho']);
const MOTIVOS = ['Por WhatsApp', 'Desde un correo personal', 'En la reunión con el cliente', 'Dentro de otro hilo de Desk (otro asunto)', 'Otro motivo'];

// Sin hoja propia (N6, auditoría 30): solo clases comunes de estilos.css y atributos style con tokens.
const MOVIL = () => matchMedia('(max-width: 640px)').matches;
const ALTO_CLIC = () => (MOVIL() ? 'calc(var(--s-10) + var(--s-1))' : 'var(--s-8)');
const META = { font: 'var(--t-meta)', color: 'var(--dim)' };
const sub = (texto, extra = {}) => h('span', { style: { ...META, ...extra } }, texto);
/** Enlace a una herramienta de fuera con forma de botón pequeño (objetivo de clic ≥ 32 px; 44 en el móvil). */
const enlaceBt = (href, ico, texto, title) => h('a', { class: 'bt mini', href, target: '_blank', rel: 'noopener', title: title || null, style: { minHeight: ALTO_CLIC() } }, icono(ico), texto);
const celda = (...hijos) => h('div', { style: { display: 'grid', gap: 'var(--s-1)', justifyItems: 'start', minWidth: '0' } }, ...hijos);
/** Meses de informe que caen en el periodo común: el informe del mes M se envía en M+1 (límite, día 5 de M+1). */
const mesesEnVentana = (meses, r) => (!r ? [] : meses.filter(m => { const e = mesSiguiente(m); return e >= r.desde.slice(0, 7) && e <= r.hasta.slice(0, 7); }));
/** Lista de filas con icono que parte las líneas largas (la .lista-i común es de una línea con puntos suspensivos). */
const listaFilas = items => h('ul', { style: { listStyle: 'none', margin: '0', padding: '0', display: 'grid' } }, items.map((it, i) =>
  h('li', { style: { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 'var(--s-2) var(--s-3)', padding: 'var(--s-2) 0', borderTop: i ? 'var(--borde-suave)' : '0', minWidth: '0' } },
    h('span', { class: `ico-c s ${it.estado || ''}`.trim() }, icono(it.icono || 'doc')),
    h('span', { style: { flex: '1 1 200px', minWidth: '0', display: 'grid', gap: 'var(--s-1)' } },
      h('span', { style: { overflowWrap: 'anywhere' } }, it.texto), it.extra ? sub(it.extra, { overflowWrap: 'anywhere' }) : null),
    it.href ? enlaceBt(it.href, it.iconoEnlace || 'ext', it.textoEnlace || 'Abrir el enlace') : null)));
const listaMeses = ms => ms.length <= 1 ? nombreMes(ms[0] || '') : `${nombreMes(ms[0])} a ${nombreMes(ms[ms.length - 1])}`;

// ===================================================================== datos
function preparar(D, cola, ctx) {
  const cli = new Map(ctx.clientes.map(c => [c.id, c]));
  return (D.filas || []).map(f => {
    const otra = cola.get(f.id);
    const estado = f.estado !== 'enviado' && otra ? 'otra_via' : f.estado;
    return { ...f, estado, otra, cli: cli.get(f.cliente_id) || { id: f.cliente_id, nombre: f.cliente } };
  });
}

/** Plazo de una fila respecto al límite del día 5 (D-09), con lo marcado «por otra vía» como enviado. */
function plazoDe(f, hoy) {
  if (f.estado === 'exento' || f.estado === 'no_aplica') return 'gris';
  if (f.estado === 'otra_via') return ((f.otra?.creada || '').slice(0, 10) || hoy) <= f.limite ? 'verde' : 'ambar';
  return f.plazo;
}

function resumenMes(filas, hoy) {
  const aplican = filas.filter(f => f.estado !== 'exento' && f.estado !== 'no_aplica');
  const enviados = aplican.filter(f => f.estado === 'enviado' || f.estado === 'otra_via');
  const aTiempo = enviados.filter(f => plazoDe(f, hoy) === 'verde');
  const pend = aplican.filter(f => PENDIENTES.has(f.estado));
  return {
    aplican: aplican.length, enviados: enviados.length, aTiempo: aTiempo.length,
    pct: aplican.length ? Math.round(aTiempo.length / aplican.length * 100) : null,
    pend: pend.length, hechos: aplican.filter(f => f.estado === 'hecho').length,
    sinTarea: aplican.filter(f => f.estado === 'sin_tarea').length, enCurso: aplican.filter(f => f.estado === 'en_curso').length,
    exentos: filas.filter(f => f.estado === 'exento').length, noAplica: filas.filter(f => f.estado === 'no_aplica').length,
  };
}

// ===================================================================== render
export default {
  id: ID,
  titulo: 'Informes mensuales',
  grupo: 'Clientes',
  // Periodo común (ronda 9): se trabaja por meses. «Este mes» enseña el informe que se envía este mes (el del mes pasado).
  usa_periodo: ['mes', 'mes_ant', 'trim', 'anio'],
  async render(cont, ctx) {
    vigilarCortes(cont);
    let D;
    try { D = await ctx.datosModulo('informes/informes'); }
    catch (e) {
      cont.append(vacio({ icono: 'doc', tono: 'aviso', borde: true, titulo: 'No se pudieron leer los informes', texto: String(e?.message || e), quien: 'Tomás (regenerar con fuentes_informes/generar_informes.py)' }));
      return;
    }
    const cola = new Map();
    if (ctx.servidor) {
      try {
        const r = await ctx.api(`acciones?modulo=${ID}`);
        for (const a of (r.acciones || []).slice().reverse()) if (a.tipo === 'enviado_otra_via') cola.set(String(a.objeto), a);
      } catch { /* sin cola: no pasa nada */ }
    }
    const raiz = h('div', { class: 'pila', style: { gap: 'var(--s-5)', minWidth: '0' } });
    cont.append(raiz);
    const S = { D, cola, filas: preparar(D, cola, ctx), hoy: ctx.hoy,   /* V2-E: hoy en Madrid (no el día en que se leyó la fuente ni UTC) */ filtroAccount: '', periodo: ctx.periodo };
    S.rehacer = () => { S.filas = preparar(D, S.cola, ctx); raiz.replaceChildren(); pintar(raiz, ctx, S); };
    ctx.alCambiarPeriodo?.(p => { if (!raiz.isConnected) return; S.periodo = p; S.filtroAccount = ''; raiz.replaceChildren(); pintar(raiz, ctx, S); });
    pintar(raiz, ctx, S);
  },
};

// ===================================================================== pantalla
function pintar(raiz, ctx, S) {
  const { D } = S;
  const meta = D._meta || {};
  const meses = (meta.meses || []).slice();
  const ciclo = meta.ciclo?.mes || meses[meses.length - 1];
  const fresco = { fuente: 'ClickUp + Desk', fecha: meta.generado, estado: (meta.plan || '').startsWith('A') ? 'ok' : 'viejo' };

  if (!S.filas.length) {
    ctx.titulo('Informes mensuales', 'Hecho · enviado · pendiente, por cliente y mes');
    raiz.append(vacio({ icono: 'doc', borde: true, titulo: 'No tienes clientes con informe mensual',
      texto: 'Aquí salen los informes de los clientes que llevas como account. Si crees que falta alguno, revisa tus asignaciones.', quien: 'Mili (asignaciones)' }));
    return;
  }

  // ---- periodo común → meses de informe que se envían en esa ventana (y los de la comparación) ----
  const sel = S.periodo ? mesesEnVentana(meses, S.periodo) : [ciclo];
  const comp = S.periodo ? (S.periodo.comp ? mesesEnVentana(meses, S.periodo.comp) : null) : meses.slice(0, -1).slice(-1);
  const cuerpo = h('div', { class: 'pila', style: { gap: 'var(--s-5)', minWidth: '0' } });
  raiz.append(cuerpo);
  if (!sel.length) {
    ctx.titulo('Informes mensuales', `${S.periodo?.texto || ''} · sin informes medidos`);
    cuerpo.append(h('div', { class: 'panel' }, h('div', { class: 'cuerpo' },
      vacioLinea(`La app mide los informes de ${listaMeses(meses)} (se envían en ${listaMeses(meses.map(mesSiguiente))}). Elige «Este mes» o «Mes anterior» arriba.`, { icono: 'cal' }))));
  } else pintarMes(cuerpo, ctx, S, sel, comp, fresco);

  // ---- abajo: correos para mirar a mano, histórico y reglas (plegadas) ----
  const posibles = S.filas.filter(f => f.posibles?.length && PENDIENTES.has(f.estado) && sel.includes(f.mes));
  if (posibles.length) {
    raiz.append(panel({ titulo: 'Correos para mirar a mano', icono: 'buscar', sub: 'Salieron de Desk con «informe», «reporte» o «resultados», pero el asunto no dice el mes: no cuentan como «enviado» hasta que alguien lo confirme' },
      h('div', { class: 'cuerpo' }, listaFilas(posibles.flatMap(f => f.posibles.map(p => ({
        icono: 'mail', estado: 'ambar', href: p.url, iconoEnlace: 'mail', textoEnlace: 'Abrir en Desk',
        texto: `${f.cliente} · «${p.asunto}»`,
        extra: `${fDiaRO(p.fecha)} · informe de ${nombreMes(f.mes)}${p.pdf ? ' · con PDF' : ''}`,
      }))).slice(0, 12)))));
  }
  raiz.append(pintarHistorico(D.historico, ctx, D.cuadre));
  raiz.append(h('details', { class: 'que-es panel', id: 'inf-reglas', style: { padding: 'var(--s-3) var(--relleno)' } },
    h('summary', { style: { minHeight: ALTO_CLIC(), display: 'flex', alignItems: 'center', gap: 'var(--s-2)' } }, icono('info', { clase: 's' }), 'Cómo se cuenta · reglas firmadas el 2-oct y límites de la medición'),
    h('div', { class: 'pila', style: { marginTop: 'var(--s-2)' } },
      listaFilas([
        { icono: 'check', texto: h('span', {}, h('b', {}, 'Hecho: '), meta.reglas?.hecho) },
        { icono: 'send', texto: h('span', {}, h('b', {}, 'Enviado: '), meta.reglas?.enviado) },
        { icono: 'cal', texto: h('span', {}, h('b', {}, 'Plazo: '), meta.reglas?.plazo) },
        { icono: 'escudo', texto: h('span', {}, h('b', {}, 'Exentos: '), meta.reglas?.exentos) },
      ]),
      avisoParcial(meta.limites, { titulo: 'Lo que no se ve.' }),
      h('p', { style: META }, `Lectura de ${meta.generado ? fDiaHoraRO(meta.generado) : 'sin fecha'}${meta.lectura?.clickup ? ` · ClickUp: ${fmt.num(meta.lectura.clickup.tareas_de_informe)} tareas de informe entre ${fmt.num(meta.lectura.clickup.tareas_leidas)} actualizadas desde el 1-ago` : ''}${meta.lectura?.desk ? ` · Desk: ${fmt.num(meta.lectura.desk.tickets_candidatos)} correos candidatos en los 30 departamentos` : ''}.`))));
}

function pintarMes(cont, ctx, S, sel, compMeses, fresco) {
  const meta = S.D._meta || {};
  const todo = ctx.nivel === 'todo';
  const ciclo = meta.ciclo?.mes;
  const varios = sel.length > 1;
  const conCiclo = sel.includes(ciclo);
  const delMes = S.filas.filter(f => sel.includes(f.mes));
  const anterior = compMeses ? S.filas.filter(f => compMeses.includes(f.mes)) : [];
  const r = resumenMes(delMes, S.hoy);
  const rA = anterior.length ? resumenMes(anterior, S.hoy) : null;
  const filasCiclo = conCiclo ? delMes.filter(f => f.mes === ciclo) : [];
  const rC = conCiclo ? resumenMes(filasCiclo, S.hoy) : null;
  const mesRef = conCiclo ? ciclo : sel[sel.length - 1];
  const limite = S.filas.find(f => f.mes === mesRef)?.limite || `${mesSiguiente(mesRef)}-05`;
  const vencido = S.hoy > limite;
  const dias = Math.round((new Date(limite + 'T12:00:00') - new Date(S.hoy + 'T12:00:00')) / 864e5);
  const mios = !todo;
  const enPlazo = conCiclo && !vencido;                 // los pendientes del ciclo aún están en plazo (ámbar, no rojo)
  const enPlazoDe = f => f.mes === ciclo && !vencido;
  const nombreComp = compMeses?.length ? listaMeses(compMeses) : '';

  ctx.titulo('Informes mensuales', varios
    ? `Informes de ${listaMeses(sel)} · límite el día 5 del mes siguiente · ${mios ? 'tus clientes' : `${fmt.num(r.aplican)} informes`}`
    : `Informe de ${nombreMes(sel[0])} · límite ${diaSemana(limite)} · ${mios ? 'tus clientes' : `${fmt.num(r.aplican)} clientes con informe`}`
    // R12 (A2): solo «Este mes» está a la vista y ya está elegido; lo que cambia la tabla está en «Más».
    + (S.periodo?.id === 'mes' ? ' · otros meses, el trimestre o el año: «Más», arriba' : ''));

  // ---- franja del plazo del ciclo en curso (día 5 verde; día 6 rojo con aviso a Mili) ----
  if (conCiclo) {
    const rojo = vencido && rC.pend;
    cont.append(h('div', { class: rojo ? 'aviso' : rC.pend ? 'aviso' : 'aviso info', role: 'status',
      style: rojo ? { borderColor: 'var(--bad-line)', background: 'var(--bad-soft)', color: 'var(--bad-ink)', alignItems: 'center', flexWrap: 'wrap' } : { alignItems: 'center', flexWrap: 'wrap' } },
      h('span', { class: 'ico' }, icono(rojo ? 'campana' : 'cal')),
      vencido
        ? h('span', { style: { flex: '1 1 240px' } }, rC.pend ? h('b', {}, `Pasado el día 5: ${fmt.plural(rC.pend, 'informe sin enviar', 'informes sin enviar')}. `) : h('b', {}, 'Todos los informes salieron a tiempo. '),
          rC.pend ? 'Están en rojo y llevan aviso a Mili.' : '')
        : h('span', { style: { flex: '1 1 240px' } }, h('b', {}, dias === 0 ? 'Hoy es el último día. ' : `Quedan ${fmt.plural(dias, 'día', 'días')} para el día 5. `),
          rC.pend ? `${fmt.plural(rC.pend, 'informe pendiente', 'informes pendientes')} de ${nombreMes(ciclo)}: si el día 6 sigue sin salir, pasa a rojo y se avisa a Mili.` : 'Todo enviado. Buen trabajo.'),
      rojo && todo ? botonAvisoMili(ctx, filasCiclo.filter(f => PENDIENTES.has(f.estado)), ciclo) : null));
  }

  // ---- tiles: lo que se mira cada día del 1 al 5 ----
  const estPct = r.pct === null ? 'gris' : r.pct === 100 ? 'verde' : enPlazo ? 'ambar' : 'rojo';
  const comp = compMeses === null ? null
    : !rA ? { texto: compMeses.length ? `sin datos de ${nombreComp}` : 'sin mes anterior medido' }
      : enPlazo && !varios ? { texto: `en plazo hasta el día 5 · ${nombreComp} acabó en ${rA.pct ?? '—'} %` }
        : rA.pct !== null && r.pct !== null ? { delta: r.pct - rA.pct, unidad: ' pts', texto: `frente a ${nombreComp} (${rA.pct} %)` } : null;
  cont.append(tiles([
    tile({ icono: 'ok', etiqueta: mios ? 'Mis informes enviados a tiempo' : 'Enviados a tiempo', valor: fmt.pct(r.pct), unidad: `${fmt.num(r.aTiempo)} de ${fmt.num(r.aplican)}`,
      estado: estPct, comparacion: comp, contexto: 'Verde si sale el día 5 incluido · rojo el 6 con aviso a Mili',
      medible: 'hoy', frescura: { fuente: 'Desk', fecha: meta.generado }, ir: 'Ver enviados', alPulsar: () => elegirChip(cont, 'enviados') }),
    tile({ icono: 'clock', etiqueta: 'Pendientes de enviar', valor: fmt.num(r.pend), unidad: `de ${fmt.num(r.aplican)}`,
      estado: r.pend === 0 ? 'verde' : enPlazo ? 'ambar' : 'rojo', contexto: `${fmt.num(r.enCurso)} en curso · ${fmt.num(r.hechos)} hechos · ${fmt.num(r.sinTarea)} sin tarea`,
      medible: 'hoy', frescura: { fuente: 'ClickUp + Desk', fecha: meta.generado }, ir: 'Ver pendientes', alPulsar: () => elegirChip(cont, 'pendientes') }),
    tile({ icono: 'send', etiqueta: 'Hechos sin enviar', valor: fmt.num(r.hechos), unidad: 'tarea cerrada, sin correo',
      estado: r.hechos === 0 ? 'verde' : enPlazo ? 'ambar' : 'rojo', contexto: 'El informe está, falta mandarlo desde Desk',
      medible: 'hoy', frescura: { fuente: 'ClickUp', fecha: meta.generado }, ir: 'Ver cuáles', alPulsar: () => elegirChip(cont, 'hecho') }),
    tile({ icono: 'alert', etiqueta: 'Sin tarea en ClickUp', valor: fmt.num(r.sinTarea), unidad: 'ni tarea ni correo',
      estado: r.sinTarea === 0 ? 'verde' : enPlazo ? 'ambar' : 'rojo', contexto: 'Nadie lo tiene apuntado: crear la tarea del informe',
      medible: 'hoy', frescura: { fuente: 'ClickUp', fecha: meta.generado }, ir: 'Ver cuáles', alPulsar: () => elegirChip(cont, 'sin_tarea') }),
    conCiclo
      ? tile({ icono: 'cal', etiqueta: vencido ? 'Días de retraso' : 'Días para el límite', valor: fmt.num(Math.abs(dias)), unidad: Math.abs(dias) === 1 ? 'día' : 'días',
        estado: vencido ? (rC.pend ? 'rojo' : 'verde') : dias <= 1 && rC.pend ? 'ambar' : 'verde',
        contexto: `Límite: ${diaSemana(limite)}${r.exentos ? ` · ${fmt.num(r.exentos)} exentos (mantenimiento)` : ''}`, medible: 'hoy' })
      : tile({ icono: 'cal', etiqueta: varios ? 'Límite' : 'Límite de ese mes', valor: varios ? 'Día 5' : fDiaRO(limite), unidad: varios ? 'del mes siguiente' : '',
        contexto: `${varios ? 'Cada informe sale como muy tarde el día 5' : `Límite: ${diaSemana(limite)}`}${r.exentos ? ` · ${fmt.num(r.exentos)} exentos (mantenimiento)` : ''}`, medible: 'hoy' }),
  ]));

  // ---- por account (Mili y dirección): quién va retrasado, de un vistazo ----
  if (todo) cont.append(pintarPorAccount(delMes, S, cont, enPlazo));

  // ---- la tabla del periodo ----
  cont.append(pintarTabla(delMes, ctx, S, sel, enPlazoDe, fresco));
}

function botonAvisoMili(ctx, pendientes, mes) {
  const b = h('button', { type: 'button', class: 'bt mini pri', style: { marginLeft: 'auto', minHeight: ALTO_CLIC() }, 'aria-disabled': ctx.soloLectura ? 'true' : null,
    title: ctx.soloLectura ? 'Estás en «ver como»: solo lectura' : 'Deja el aviso en la cola simulada (al desplegar la app, sale por el chat de ClickUp)' }, icono('campana'), 'Avisar a Mili');
  b.addEventListener('click', async () => {
    if (ctx.soloLectura) return;
    try {
      await ctx.accion({ herramienta: 'clickup_chat', tipo: 'aviso_mili', objeto: `informes·${mes}`,
        texto: `Día 6: ${pendientes.length} informes de ${nombreMes(mes)} sin enviar: ${pendientes.map(f => `${f.cliente} (${f.account})`).join(', ')}.`,
        vista_previa: { para: 'mili', canal: 'chat de ClickUp', clientes: pendientes.map(f => f.cliente_id) } });
      b.replaceWith(chipEstado('azul', 'Aviso en la cola (simulado)'));
      avisoFlotante('Aviso a Mili en la cola simulada');
    } catch (e) { avisoFlotante(`No se pudo: ${e.message}`, { icono: 'alert' }); }
  });
  return b;
}

function pintarPorAccount(filas, S, cont, enPlazo) {
  const grupos = new Map();
  for (const f of filas) {
    const k = f.account || 'sin account';
    if (!grupos.has(k)) grupos.set(k, []);
    grupos.get(k).push(f);
  }
  const lista = [...grupos.entries()].map(([acc, fs]) => ({ acc, fs, r: resumenMes(fs, S.hoy) }))
    .filter(x => x.r.aplican)
    .sort((a, b) => b.r.pend - a.r.pend || (a.r.pct ?? 0) - (b.r.pct ?? 0) || a.acc.localeCompare(b.acc, 'es'));
  const TONO = { enviado: 'var(--good)', curso: enPlazo ? 'var(--warn)' : 'var(--bad)', sin: enPlazo ? 'var(--off)' : 'var(--bad)' };
  const caja = h('div', { role: 'list' });
  const pintarFilas = () => caja.replaceChildren(...lista.map(({ acc, r }) => {
    const pct = n => `${(n / r.aplican) * 100}%`;
    const activo = S.filtroAccount === acc;
    const b = h('button', { type: 'button', class: 'bt', role: 'listitem', 'aria-pressed': String(activo),
      'aria-label': `${acc}: ${r.enviados} enviados de ${r.aplican}, ${r.pend} pendientes. Filtrar la tabla`,
      style: { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 'var(--s-2) var(--s-4)', width: '100%', minHeight: 'var(--s-12)', border: '0', borderTop: 'var(--borde-suave)', borderRadius: '0', padding: 'var(--s-2) var(--relleno)', whiteSpace: 'normal', textAlign: 'left', fontWeight: '400' },
      on: { click: () => { S.filtroAccount = S.filtroAccount === acc ? '' : acc; pintarFilas(); S.repintarTabla?.(); cont.querySelector('#inf-tabla')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); } } },
      h('span', { class: 'fila', style: { flex: '1 1 140px', flexWrap: 'nowrap', minWidth: '0', font: 'var(--t-h3)' } }, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(acc)), h('span', { style: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, acc)),
      h('span', { 'aria-hidden': 'true', style: { flex: '999 1 160px', display: 'flex', height: 'var(--s-2)', borderRadius: 'var(--r-full)', overflow: 'hidden', background: 'var(--line-soft)' } },
        h('i', { style: { display: 'block', width: pct(r.enviados), background: TONO.enviado } }),
        h('i', { style: { display: 'block', width: pct(r.hechos + r.enCurso), background: TONO.curso } }),
        h('i', { style: { display: 'block', width: pct(r.sinTarea), background: TONO.sin } })),
      h('span', { class: 'fila', style: { flex: '0 0 auto', justifyContent: 'flex-end' } },
        chipEstado(r.pend ? (enPlazo ? 'ambar' : 'rojo') : 'verde', r.pend ? fmt.plural(r.pend, 'pendiente', 'pendientes') : 'al día'),
        sub(`${fmt.num(r.enviados)} de ${fmt.num(r.aplican)}`)));
    return b;
  }));
  pintarFilas();
  const cuadro = c => h('i', { 'aria-hidden': 'true', style: { width: 'var(--s-3)', height: 'var(--s-3)', borderRadius: 'var(--r-s)', display: 'inline-block', background: c } });
  return panel({ titulo: 'Por account', icono: 'eq', sub: 'Quién va retrasado de un vistazo. Pulsa un account para ver solo sus clientes en la tabla.' },
    caja,
    h('div', { class: 'cuerpo fila', style: { gap: 'var(--s-2) var(--s-4)', ...META, borderTop: 'var(--borde-suave)' } },
      h('span', { class: 'fila', style: { gap: 'var(--s-1)' } }, cuadro(TONO.enviado), 'Enviado'),
      h('span', { class: 'fila', style: { gap: 'var(--s-1)' } }, cuadro(TONO.curso), 'Hecho o en curso, sin enviar'),
      h('span', { class: 'fila', style: { gap: 'var(--s-1)' } }, cuadro(TONO.sin), 'Sin tarea')));
}

// ------------------------------------------------------------------- tabla
function celdaHecho(f) {
  if (!f.tarea) return celda(chipEstado(f.estado === 'exento' || f.estado === 'no_aplica' ? 'gris' : 'ambar', 'Sin tarea'), sub('en ClickUp'));
  return celda(
    chipEstado(f.hecho ? 'verde' : 'ambar', f.hecho ? 'Hecho' : Mayus(f.tarea.estado || 'abierta')),
    f.tarea.url ? enlaceBt(f.tarea.url, 'ext', f.hecho && f.tarea.cerrada_el ? `Cerrada el ${fDiaRO(f.tarea.cerrada_el)}` : 'Abrir en ClickUp', f.tarea.nombre) : null);
}

function celdaEnviado(f, enPlazo) {
  if (f.estado === 'exento') return celda(chipEstado('gris', 'Exento'), sub(f.exento_motivo || 'mantenimiento'));
  if (f.estado === 'no_aplica') return celda(chipEstado('gris', 'No aplica'), sub(f.no_aplica_motivo || ''));
  if (f.estado === 'otra_via') {
    const v = f.otra?.vista_previa ? (typeof f.otra.vista_previa === 'string' ? JSON.parse(f.otra.vista_previa) : f.otra.vista_previa) : {};
    return celda(chipEstado('verde', 'Por otra vía'),
      h('span', { title: 'Marcado a mano: queda en el rastro con quién y cuándo', style: { ...META, overflowWrap: 'anywhere' } }, `${v.motivo || f.otra?.texto || ''} · ${f.otra?.quien || ''}`),
      v.enlace ? enlaceBt(v.enlace, 'link', 'Prueba') : null);
  }
  if (f.enviado) {
    const tarde = f.plazo === 'ambar';
    return celda(
      chipEstado(tarde ? 'ambar' : 'verde', `${tarde ? 'Tarde · ' : ''}${fDiaRO(f.enviado.fecha)}`),
      f.enviado.url ? enlaceBt(f.enviado.url, 'mail', 'Abrir en Desk', f.enviado.asunto || '') : sub(f.enviado.metodo));
  }
  return celda(chipEstado(enPlazo ? 'ambar' : 'rojo', enPlazo ? 'Sin enviar' : 'Sin enviar · aviso a Mili'),
    sub(f.posibles?.length ? `${fmt.plural(f.posibles.length, 'correo', 'correos')} para mirar` : 'ningún correo en Desk'));
}

function botonOtraVia(f, ctx, S) {
  const caja = h('span', { style: { minWidth: '0' } });
  const inicial = () => {
    const b = h('button', { type: 'button', class: 'bt mini', style: { minHeight: ALTO_CLIC() }, 'aria-disabled': ctx.soloLectura ? 'true' : null,
      title: ctx.soloLectura ? 'Estás en «ver como»: solo lectura' : 'Cuenta como enviado, con motivo y sello' }, icono('marcador'), 'Enviado por otra vía');
    b.addEventListener('click', () => { if (!ctx.soloLectura) formulario(); });
    caja.replaceChildren(b);
    return b;
  };
  const formulario = () => {
    const motivo = chipsFiltro({ etiqueta: 'Por dónde salió', opciones: MOTIVOS.map(m => ({ valor: m, texto: m })) });
    const cNota = campoTexto({ etiqueta: 'Detalle', placeholder: 'Obligatorio si es «Otro motivo»' });
    const cEnlace = campoTexto({ etiqueta: 'Prueba', tipo: 'url', placeholder: 'Enlace a la prueba (opcional)' });
    const nota = cNota.querySelector('input'); nota.maxLength = 160;
    const enlace = cEnlace.querySelector('input'); enlace.inputMode = 'url';
    const error = h('span', { class: 'sub', role: 'alert' });
    const guardar = h('button', { type: 'button', class: 'bt mini pri', style: { minHeight: ALTO_CLIC() } }, icono('ok'), 'Guardar');
    const cancelar = h('button', { type: 'button', class: 'bt mini', style: { minHeight: ALTO_CLIC() } }, 'Cancelar');
    cancelar.addEventListener('click', () => inicial().focus());
    guardar.addEventListener('click', async () => {
      const mv = motivo.valor();
      const m = mv === 'Otro motivo' ? nota.value.trim() : `${mv}${nota.value.trim() ? ` · ${nota.value.trim()}` : ''}`;
      if (!m) { error.textContent = 'Escribe el motivo.'; nota.focus(); return; }
      if (enlace.value && !/^https?:\/\//.test(enlace.value)) { error.textContent = 'El enlace debe empezar por https://'; enlace.focus(); return; }
      guardar.disabled = true;
      try {
        await ctx.accion({ herramienta: 'app', tipo: 'enviado_otra_via', objeto: f.id, cliente_id: f.cliente_id, texto: m,
          vista_previa: { motivo: m, enlace: enlace.value || null, cliente: f.cliente, mes: f.mes } });
        S.cola.set(f.id, { tipo: 'enviado_otra_via', texto: m, quien: ctx.real.id, creada: ctx.hoy, vista_previa: { motivo: m, enlace: enlace.value || null } });
        avisoFlotante(`${f.cliente}: marcado como enviado por otra vía (queda en el rastro)`);
        S.rehacer();
      } catch (e) { error.textContent = `No se pudo: ${e.message}`; guardar.disabled = false; }
    });
    const form = h('div', { class: 'pila', role: 'group', 'aria-label': `Enviado por otra vía: ${f.cliente}`,
      style: { gap: 'var(--s-2)', padding: 'var(--s-3)', border: 'var(--borde)', borderRadius: 'var(--r-m)', background: 'var(--card-2)', minWidth: 'min(100%, 260px)', textAlign: 'left' } },
    motivo, cNota, cEnlace, error, h('div', { class: 'fila', style: { justifyContent: 'flex-end' } }, cancelar, guardar));
    form.addEventListener('keydown', e => { if (e.key === 'Escape') { e.stopPropagation(); inicial().focus(); } });
    caja.replaceChildren(form);
    motivo.querySelector('button[aria-pressed="true"]')?.focus();
  };
  inicial();
  return caja;
}

function elegirChip(cont, valor) {
  const b = cont.querySelector(`#inf-chips button[data-v="${valor}"]`);
  if (b && b.getAttribute('aria-pressed') !== 'true') b.click();
  cont.querySelector('#inf-tabla')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function pintarTabla(filas, ctx, S, sel, enPlazoDe, fresco) {
  const varios = sel.length > 1;
  const cuenta = pred => filas.filter(pred).length;
  const opciones = [
    { valor: '', texto: 'Todos', cuenta: filas.length },
    { valor: 'pendientes', texto: 'Pendientes', icono: 'clock', cuenta: cuenta(f => PENDIENTES.has(f.estado)), cuentaEstado: 'rojo' },
    { valor: 'sin_tarea', texto: 'Sin tarea', icono: 'alert', cuenta: cuenta(f => f.estado === 'sin_tarea'), cuentaEstado: 'rojo' },
    { valor: 'en_curso', texto: 'En curso', icono: 'clock', cuenta: cuenta(f => f.estado === 'en_curso') },
    { valor: 'hecho', texto: 'Hechos sin enviar', icono: 'send', cuenta: cuenta(f => f.estado === 'hecho'), cuentaEstado: 'rojo' },
    { valor: 'enviados', texto: 'Enviados', icono: 'ok', cuenta: cuenta(f => f.estado === 'enviado' || f.estado === 'otra_via') },
    { valor: 'exento', texto: 'Exentos y no aplica', icono: 'escudo', cuenta: cuenta(f => f.estado === 'exento' || f.estado === 'no_aplica') },
  ];
  const chips = chipsFiltro({ etiqueta: 'Estado', clave: `${ID}.estado`, opciones, alCambiar: () => repintar() });
  chips.id = 'inf-chips';
  chips.querySelectorAll('button').forEach((b, i) => { if (opciones[i]) b.dataset.v = opciones[i].valor; });
  const caja = h('div', {});
  const quitarAcc = h('button', { type: 'button', class: 'bt mini', style: { minHeight: ALTO_CLIC() }, hidden: true, on: { click: () => { S.filtroAccount = ''; repintar(); document.querySelectorAll('#main [role="listitem"][aria-pressed="true"]').forEach(x => x.setAttribute('aria-pressed', 'false')); } } }, icono('cerrar'), 'Quitar account');
  const comoSeCuenta = h('button', { type: 'button', class: 'bt mini', style: { minHeight: ALTO_CLIC() }, on: { click: () => { const d = document.getElementById('inf-reglas'); if (d) { d.open = true; d.scrollIntoView({ behavior: 'smooth' }); } } } }, icono('info'), 'Cómo se cuenta');
  const repintar = () => {
    chips.querySelectorAll('button').forEach((b, i) => { if (opciones[i]) b.dataset.v = opciones[i].valor; });
    const v = chips.valor();
    let base = filas.filter(f => !v ? true
      : v === 'pendientes' ? PENDIENTES.has(f.estado)
        : v === 'enviados' ? (f.estado === 'enviado' || f.estado === 'otra_via')
          : v === 'exento' ? (f.estado === 'exento' || f.estado === 'no_aplica') : f.estado === v);
    if (S.filtroAccount) base = base.filter(f => (f.account || 'sin account') === S.filtroAccount);
    quitarAcc.hidden = !S.filtroAccount;
    quitarAcc.replaceChildren(icono('cerrar'), `Quitar «${S.filtroAccount}»`);
    base.sort((a, b) => EST[a.estado].orden - EST[b.estado].orden || (b.dias_retraso || 0) - (a.dias_retraso || 0) || a.cliente.localeCompare(b.cliente, 'es') || b.mes.localeCompare(a.mes));
    caja.replaceChildren(tablaDensa({
      filas: base, porPagina: MOVIL() ? 10 : 25,
      buscar: { campos: ['cliente', 'account'], placeholder: 'Buscar cliente o account' },
      alPulsar: f => ctx.navegar(`ficha/${f.cliente_id}`), puedePulsar: f => !!f.cli.detalle,
      columnas: [
        { clave: 'cliente', titulo: 'Cliente', principal: true, celda: f => h('span', { class: 'celda-cli' }, logoCliente(f.cli),
          h('span', { style: { display: 'grid', minWidth: '0' } }, h('span', { style: { overflowWrap: 'anywhere' } }, f.cliente),
            sub(`${f.account_id ? ctx.nombre(f.account_id) : 'sin account'}${varios ? ` · informe de ${nombreMes(f.mes)}` : ''}`, { fontWeight: '500' }))) },
        { clave: 'hecho', titulo: 'Hecho (ClickUp)', valor: f => (f.hecho ? 1 : f.tarea ? 0.5 : 0), celda: celdaHecho },
        { clave: 'estado', titulo: 'Enviado (Desk)', valor: f => EST[f.estado].orden, celda: f => celdaEnviado(f, enPlazoDe(f)) },
        S.D.historico?.estado === 'importado' ? { clave: 'hoja', titulo: 'Hoja de Zoho', valor: f => (f.diferencia ? 0 : 1), celda: f => celdaHoja(f) } : null,
        { clave: 'dias_retraso', titulo: 'Retraso', num: true, celda: f => (f.estado === 'exento' || f.estado === 'no_aplica') ? sub('no aplica') : f.dias_retraso ? h('b', { style: { color: f.plazo === 'rojo' ? 'var(--bad-ink)' : 'var(--warn-ink)' } }, fmt.plural(f.dias_retraso, 'día', 'días')) : (PENDIENTES.has(f.estado) ? 'en plazo' : 'a tiempo') },
        { clave: 'accion', titulo: 'Acción', ordenable: false, celda: f => PENDIENTES.has(f.estado) && ctx.nivel ? botonOtraVia(f, ctx, S) : null },
      ].filter(Boolean),
      etiquetaFila: f => `${f.cliente}: ${EST[f.estado].texto}. Abrir la ficha`,
      vacio: { titulo: 'Nada con este filtro', porque: 'Cambia el estado o quita el filtro de account.', celebrar: chips.valor() === 'pendientes' },
    }));
  };
  S.repintarTabla = repintar;
  repintar();
  return h('div', { id: 'inf-tabla' }, panel({ titulo: varios ? `Informes de ${listaMeses(sel)}` : `Informes de ${nombreMes(sel[0])}`, icono: 'doc',
    sub: 'Lo que pide acción, arriba. Pulsa una fila para abrir la ficha del cliente. «Enviado por otra vía» cuenta como enviado, con motivo y sello en el rastro.',
    acciones: h('div', { class: 'fila' }, frescura(fresco), comoSeCuenta, quitarAcc) },
  h('div', { class: 'cuerpo', style: { paddingBottom: 'var(--s-1)' } }, chips), caja));
}

function celdaHoja(f) {
  if (!f.hoja) return sub('no está en la hoja');
  const ls = [f.hoja.enlace_informe ? enlaceBt(f.hoja.enlace_informe, 'doc', 'Informe') : null,
    f.hoja.enlace_estadisticas ? enlaceBt(f.hoja.enlace_estadisticas, 'grafico', 'Estadísticas') : null].filter(Boolean);
  return celda(
    f.diferencia ? chipEstado('ambar', 'No cuadra') : chipEstado(f.hoja.enviado ? 'verde' : 'gris', f.hoja.enviado ? 'Enviado en la hoja' : 'Sin marcar'),
    f.diferencia ? sub(f.diferencia, { overflowWrap: 'anywhere' }) : null, ls.length ? h('span', { class: 'fila', style: { gap: 'var(--s-1)' } }, ls) : null);
}

// --------------------------------------------------------------- histórico de la hoja
function pintarHistorico(hist, ctx, cuadre) {
  const cols = [
    { clave: 'cliente', titulo: 'Cliente', principal: true, celda: f => h('span', { style: { font: 'var(--t-h3)', overflowWrap: 'anywhere' } }, f.cliente || f.cliente_hoja) },
    { clave: 'mes', titulo: 'Mes', valor: f => f.mes, celda: f => (f.mes ? `${Mayus(nombreMes(f.mes))} ${f.mes.slice(0, 4)}` : sub('sin mes')) },
    { clave: 'enlace_informe', titulo: 'Informe', celda: f => f.enlace_informe ? enlaceBt(f.enlace_informe, 'doc', 'Abrir el informe', `Abrir el informe de ${f.cliente || f.nombre || 'este cliente'}${f.mes ? ` · ${f.mes}` : ''}`) : sub('sin enlace') },
    { clave: 'enlace_estadisticas', titulo: 'Estadísticas', celda: f => f.enlace_estadisticas ? enlaceBt(f.enlace_estadisticas, 'grafico', 'Abrir las estadísticas', `Abrir las estadísticas de ${f.cliente || f.nombre || 'este cliente'}${f.mes ? ` · ${f.mes}` : ''}`) : sub('sin enlace') },
    { clave: 'informado_en_reunion', titulo: 'Informado al cliente', celda: f => f.informado_en_reunion === null || f.informado_en_reunion === undefined ? sub('sin dato') : chipEstado(f.informado_en_reunion ? 'verde' : 'gris', f.informado_en_reunion ? 'Sí' : 'No') },
    { clave: 'enviado', titulo: 'Enviado', celda: f => f.enviado === null || f.enviado === undefined ? sub('sin dato') : chipEstado(f.enviado ? 'verde' : 'gris', f.enviado ? 'Sí' : 'No') },
  ];
  if (hist?.estado === 'importado' && hist.filas?.length) {
    const medidos = new Set(cuadre?.meses || []);   // los meses que ya mide la app van en la tabla de arriba, con su cuadre
    const filas = hist.filas.filter(f => !medidos.has(f.mes)).sort((a, b) => (b.mes || '').localeCompare(a.mes || '') || String(a.cliente).localeCompare(String(b.cliente), 'es'));
    const cuerpo = [];
    if (cuadre) {
      cuerpo.push(h('div', { class: 'cuerpo pila' },
        h('p', { class: 'sub' }, `Cuadre con lo que ve la app (ClickUp y Desk) en ${cuadre.meses.map(nombreMes).join(' y ') || 'los meses en común'}: ${fmt.num(cuadre.coinciden)} de ${fmt.num(cuadre.comparados)} coinciden.`),
        cuadre.diferencias.length ? listaFilas(cuadre.diferencias.map(d => ({ icono: 'alert', estado: 'ambar', texto: `${d.cliente} · ${nombreMes(d.mes)}`, extra: d.diferencia })))
          : vacioLinea('La hoja y la app dicen lo mismo.', { icono: 'ok' })));
    }
    if (hist.sin_emparejar?.length) cuerpo.push(h('div', { class: 'cuerpo' }, avisoParcial(`Filas de la hoja sin cliente reconocido: ${hist.sin_emparejar.join(', ')}. Se ven en la tabla con el nombre de la hoja.`, { titulo: 'Para revisar.' })));
    return panel({ titulo: 'Histórico de la hoja de Zoho', icono: 'hist', sub: `${fmt.num(filas.length)} informes de ${fmt.num(new Set(filas.map(f => f.cliente_hoja)).size)} clientes, de ${nombreMes(filas[filas.length - 1]?.mes || '')} a ${nombreMes(filas[0]?.mes || '')} · leído de la hoja «Informes mensuales» el ${fDiaHoraRO(hist.importado)} · con los enlaces reales de cada celda` },
      ...cuerpo,
      tablaApilable({ columnas: cols, filas, controles: true, porPagina: MOVIL() ? 10 : 25, buscar: { campos: ['cliente', 'cliente_hoja', 'mes'], placeholder: 'Buscar cliente o mes' } }));
  }
  return panel({ titulo: 'Histórico de la hoja de Zoho', icono: 'hist', sub: 'Los meses anteriores, con el formato de la hoja «Informes mensuales»' },
    h('div', { class: 'cuerpo' }, vacioLinea('Todavía sin importar. Se importa por API desde la hoja «Informes mensuales» (solo esa hoja; nunca «Credenciales»).', { icono: 'plug', quien: 'Tomás (lanzar la importación)' })));
}
