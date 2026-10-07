// modulos/producto.js · «Dirección de producto» (3-oct, encargo de Tomás para Coti). Su pantalla de inicio (puesto proyectos).
//
// Lo de Coti, y solo lo de Coti (lo operativo — plazos, correos, reuniones, llamadas — es de Mili y NO entra aquí):
//   a) Talleres de la oferta: cada cliente nuevo con firma, límite (alta + 2 días, regla de Clientes nuevos), hecho / agendado /
//      sin agendar, quién lo lleva y días de retraso. Lo que va tarde, arriba y en rojo.
//   b) Semáforo ESTRATÉGICO de todos los clientes (Crítico / Vigilar / Bien) por RESULTADOS frente a su objetivo, con el motivo
//      en una frase.
//   c) Avance hacia el objetivo: barra (hoy frente a objetivo) y tendencia; renovaciones próximas con riesgo.
//   d) Para cada crítico, la recomendación del cerebro de decisiones con su porqué y su fuente.
// Datos: data/verdad/objetivos_clientes.json (fuentes_verdad/generar_objetivos_clientes.py), el único sitio del objetivo de
// cada cliente; recortado por el servidor (cada fila llega solo si la persona ve ese cliente). Sin importes de dinero.

import {
  h, fmt, icono, chipEstado, panel, logoCliente, barraObjetivo, enlaceFuente, vacio, selloMedible, chipsFiltro, tablaDensa,
  frescura, limpiaTexto, minilinea,
} from '../componentes.js';
import { franjaCifras } from './_trabajo.js';

const SEM = {
  critico: { t: 'Crítico', e: 'rojo', o: 0, i: 'fire' },
  vigilar: { t: 'Vigilar', e: 'ambar', o: 1, i: 'ojo' },
  bien: { t: 'Bien', e: 'verde', o: 2, i: 'ok' },
};
const sem = s => SEM[s] || { t: 'Sin dato', e: 'gris', o: 3, i: 'info' };
const CONF = { dicho_por_cliente: ['Dicho por el cliente', 'verde'], apuntado_por_account: ['Apuntado por el account', 'azul'], deducido: ['Deducido: confirmar', 'ambar'] };
const TALLER = { hecho: ['Hecho', 'verde'], agendado: ['Agendado', 'azul'], sin_agendar: ['Sin agendar', 'rojo'], por_confirmar: ['Fecha pasada, sin confirmar', 'ambar'], prevista: ['Pendiente de firma', 'gris'] };
const TEND = { sube: ['sube', 'sube'], baja: ['baja', 'baja'], igual: ['igual', 'derecha'] };
const S = n => `var(--s-${n})`;
const ent = v => fmt.num(v, Number.isInteger(v) ? 0 : 1);

function fuenteDe(f) {
  if (!f) return null;
  const href = f.url || f.href || null;
  const txt = f.texto || f.ruta || 'Fuente';
  return href ? enlaceFuente(href, txt) : h('span', { class: 'fuente-t', title: f.ruta || txt }, `${txt}${f.ruta && f.ruta !== txt ? ` · ${f.ruta.replace(/^\/Users\/[^/]+\//, '~/')}` : ''}`);
}

// ------------------------------------------------------------------ a) talleres
function panelTalleres(talleres, ctx) {
  const reales = talleres.filter(t => t.cliente_id || t.estado === 'prevista');
  const tarde = reales.filter(t => t.tarde).length;
  const pend = reales.filter(t => !t.tarde && (t.estado === 'agendado' || t.estado === 'sin_agendar')).length;
  const hechos = reales.filter(t => t.estado === 'hecho').length;
  const sub = `${fmt.plural(reales.filter(t => t.cliente_id).length, 'cliente nuevo', 'clientes nuevos')}: ${hechos} con el taller hecho, ${pend} por hacer en plazo, ${tarde} tarde. Límite: alta + 2 días (regla de Clientes nuevos).`;
  if (!reales.length) return panel({ titulo: 'Talleres de la oferta', icono: 'rocket', id: 'pr-tall' }, vacio({ titulo: 'Sin clientes nuevos', porque: 'No hay altas en los últimos 90 días.' }));
  const tabla = tablaDensa({
    filas: reales, porPagina: 0, etiqueta: 'Talleres de la oferta',
    columnas: [
      { clave: 'nombre', titulo: 'Cliente', principal: true, celda: t => h('span', { class: 'celda-cli' },
        t.cliente_id ? h('a', { href: `#/ficha/${t.cliente_id}/resumen` }, t.nombre) : t.nombre,
        t.tarde ? chipEstado('rojo', 'Tarde', { punto: false }) : null) },
      { clave: 'estado', titulo: 'Taller', celda: t => { const [tx, e] = TALLER[t.estado] || [t.estado, 'gris']; return h('span', {}, chipEstado(t.tarde && t.estado !== 'hecho' ? 'rojo' : e, tx), t.fecha_taller ? h('small', { class: 'sub', style: { display: 'block' } }, fmt.fechaHora(t.fecha_taller.length > 10 ? t.fecha_taller : `${t.fecha_taller} 12:00`).replace(', 12:00', '')) : null); } },
      { clave: 'firma', titulo: 'Firma', celda: t => fmt.fecha(t.firma) },
      { clave: 'limite', titulo: 'Límite', celda: t => fmt.fecha(t.limite) },
      { clave: 'dias_retraso', titulo: 'Retraso', num: true, celda: t => (t.dias_retraso ? h('b', { style: { color: t.estado === 'hecho' ? 'var(--ambar-t, inherit)' : 'var(--rojo-t, var(--rojo))' } }, fmt.plural(t.dias_retraso, 'día')) : '—') },
      { clave: 'quien', titulo: 'Lo lleva', celda: t => [t.quien || '—', t.account_nombre ? h('small', { class: 'sub', style: { display: 'block' } }, `account: ${t.account_nombre}`) : null] },
      { clave: 'objetivo_pactado', titulo: 'Objetivo', celda: t => (t.cliente_id ? (t.objetivo_pactado ? chipEstado('verde', 'Pactado') : chipEstado('ambar', 'Sin objetivo')) : '—') },
    ],
  });
  return panel({ titulo: 'Talleres de la oferta', icono: 'rocket', id: 'pr-tall', sub,
    pie: h('span', { class: 'sub' }, 'Dato: Clientes nuevos (equipo de arranque, calendario «Taller de la oferta» de RO y ClickUp) · ', enlaceFuente('#/clientes-nuevos', 'Clientes nuevos')) }, tabla);
}

// ------------------------------------------------------------------ b + c) semáforo y avance
function filaCliente(f, ctx, logos) {
  const s = sem(f.semaforo);
  const o = f.objetivo;
  const r = f.resultado || {};
  const logo = logos.get(f.cliente_id);
  const [ct, ce] = CONF[o?.confianza] || [];
  const tend = TEND[r.tendencia];
  const barra = o && r.valor !== null && r.valor !== undefined && r.objetivo_mes
    ? barraObjetivo({ valor: r.valor, objetivo: r.objetivo_mes, etiqueta: o.objetivo_medible || 'Avance', etiquetaValor: 'Hoy', formato: ent })
    : null;
  return h('li', { class: 'pr-cli', 'data-sem': f.semaforo, style: { display: 'grid', gap: S(2), padding: `${S(3)} 0`, borderTop: '1px solid var(--borde)' } },
    h('div', { class: 'fila', style: { justifyContent: 'space-between', gap: S(2), flexWrap: 'wrap' } },
      h('span', { class: 'celda-cli', style: { minWidth: '0' } }, logoCliente({ nombre: f.nombre, logo }),
        h('a', { href: `#/ficha/${f.cliente_id}/resumen` }, h('b', {}, f.nombre)),
        f.nuevo ? chipEstado('azul', 'Nuevo', { punto: false }) : null),
      h('span', { class: 'fila', style: { gap: S(2) } }, chipEstado(s.e, s.t),
        r.pct !== null && r.pct !== undefined ? h('b', { 'aria-label': `${r.pct} % de su objetivo` }, `${r.pct} %`) : null)),
    h('p', { style: { margin: 0 } }, icono(s.i, { clase: 's' }), ' ', limpiaTexto(f.motivo || '')),
    o ? h('p', { class: 'sub', style: { margin: 0 } },
      o.objetivo_cliente ? h('q', {}, limpiaTexto(o.objetivo_cliente)) : null,
      o.objetivo_cliente && o.objetivo_medible ? ' → ' : null,
      o.objetivo_medible ? h('b', {}, o.objetivo_medible) : null,
      o.fecha ? ` · ${fmt.fecha(o.fecha)}` : null) : null,
    barra,
    (r.serie || []).filter(x => x !== null && x !== undefined).length >= 2
      ? h('div', { style: { maxWidth: '260px' } }, minilinea(r.serie, { x: r.serie_meses || [], formato: ent, umbral: r.objetivo_mes || null, etiqueta: `${o?.metrica || 'leads'} por mes` })) : null,
    h('div', { class: 'fila', style: { gap: `${S(1)} ${S(3)}`, flexWrap: 'wrap', fontSize: 'var(--t-xs, 12px)' } },
      r.valor !== null && r.valor !== undefined ? h('span', {}, `Hoy: ${ent(r.valor)} ${r.texto || ''}`) : r.proxy?.valor !== undefined && r.proxy?.valor !== null ? h('span', {}, `Referencia: ${ent(r.proxy.valor)} ${r.proxy.texto || ''}`) : null,
      tend ? h('span', { title: r.tendencia_txt || '' }, icono(tend[1], { clase: 's' }), ` Tendencia: ${tend[0]}`) : null,
      r.medible && r.medible !== 'hoy' ? selloMedible(r.medible, r.medible === 'medias' ? 'Depende de que el despacho marque los cierres en GoHighLevel' : 'La app no mide hoy esta métrica') : null,
      ct ? chipEstado(ce, ct, { punto: false }) : null,
      o ? fuenteDe(o.fuente) : null,
      r.fuente ? enlaceFuente(r.href, r.fuente) : null,
      f.sin_objetivo ? h('span', {}, icono('persona', { clase: 's' }), ` Lo pide: ${f.sin_objetivo.quien_pide_nombre}`) : f.account_nombre ? h('span', {}, `Account: ${f.account_nombre}`) : null),
    r.ultima_lectura && (r.valor === null || r.valor === undefined) ? h('p', { class: 'sub', style: { margin: 0 } }, `Última lectura apuntada: ${limpiaTexto(r.ultima_lectura.texto || '')}${r.ultima_lectura.fecha ? ` (${fmt.fecha(r.ultima_lectura.fecha)})` : ''}`) : null);
}

function panelSemaforo(filas, ctx, logos, estadoFiltro) {
  const lista = h('ul', { class: 'pr-lista', style: { listStyle: 'none', margin: 0, padding: 0 } });
  const pintar = v => {
    const vis = filas.filter(f => !v || v === 'todos' || (v === 'sin_objetivo' ? !f.objetivo : f.semaforo === v));
    lista.replaceChildren(...(vis.length ? vis.map(f => filaCliente(f, ctx, logos)) : [h('li', { class: 'sub', style: { padding: S(3) } }, 'Ningún cliente en este filtro.')]));
  };
  const n = s => filas.filter(f => f.semaforo === s).length;
  const chips = chipsFiltro({ etiqueta: 'Ver', clave: 'producto-sem', valor: estadoFiltro || 'todos',
    opciones: [{ valor: 'todos', texto: `Todos · ${filas.length}` }, { valor: 'critico', texto: `Crítico · ${n('critico')}` }, { valor: 'vigilar', texto: `Vigilar · ${n('vigilar')}` },
      { valor: 'bien', texto: `Bien · ${n('bien')}` }, { valor: 'sin_objetivo', texto: `Sin objetivo · ${filas.filter(f => !f.objetivo).length}` }],
    alCambiar: pintar });
  pintar(chips.valor ? chips.valor() : estadoFiltro || 'todos');
  return panel({ titulo: 'Semáforo estratégico y avance hacia el objetivo', icono: 'target', id: 'pr-sem',
    sub: 'Resultados frente a lo que nos propusimos con cada cliente (leads, citas o clientes). No mira plazos, correos ni reuniones: eso es el semáforo de Operaciones.' },
  chips, lista);
}

// ------------------------------------------------------------------ d) recomendaciones
function panelRecomendaciones(filas) {
  const crit = filas.filter(f => f.semaforo === 'critico' && f.recomendacion);
  if (!crit.length) return null;
  return panel({ titulo: 'Qué haría con cada crítico', icono: 'spark', id: 'pr-rec', sub: 'Recomendación del cerebro de decisiones (diagnóstico del embudo y reglas de RO), con su porqué y su fuente. Lo decide una persona.' },
    h('ol', { class: 'primero', style: { margin: 0, paddingLeft: '1.2em', display: 'grid', gap: S(3) } }, crit.map(f => {
      const r = f.recomendacion;
      return h('li', {},
        h('b', {}, h('a', { href: `#/ficha/${f.cliente_id}/resumen` }, f.nombre), ': ', limpiaTexto(r.que || '')),
        h('p', { class: 'sub', style: { margin: `${S(1)} 0 0` } }, 'Por qué: ', limpiaTexto(r.porque || f.motivo || '')),
        h('p', { class: 'sub', style: { margin: `${S(1)} 0 0`, display: 'flex', gap: S(3), flexWrap: 'wrap' } },
          r.quien ? h('span', {}, `Quién: ${r.quien}`) : null,
          r.regla?.texto ? h('span', {}, `Criterio: ${limpiaTexto(r.regla.texto)}`) : null,
          r.regla?.url ? enlaceFuente(r.regla.url, r.regla.autor ? `Cerebro · ${r.regla.autor}` : 'Cerebro') : null,
          r.fuente?.href ? enlaceFuente(r.fuente.href, r.fuente.texto) : r.fuente?.texto ? h('span', {}, `Dato: ${r.fuente.texto}`) : null));
    })));
}

// ------------------------------------------------------------------ renovaciones y sin objetivo
function panelRenovaciones(renov, filas) {
  const conFecha = filas.filter(f => f.renovacion?.fin).length;
  const cuerpo = renov.length
    ? h('ul', { style: { listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: S(2) } }, renov.map(r => {
      const s = sem(r.riesgo);
      return h('li', { class: 'fila', style: { justifyContent: 'space-between', gap: S(2), flexWrap: 'wrap' } },
        h('span', {}, h('a', { href: `#/ficha/${r.cliente_id}/resumen` }, h('b', {}, r.nombre)), ` · ${r.dias < 0 ? `venció hace ${fmt.plural(-r.dias, 'día')}` : `en ${fmt.plural(r.dias, 'día')}`} (${fmt.fecha(r.fin)})`),
        h('span', { class: 'fila', style: { gap: S(2) } }, chipEstado(s.e, `Riesgo: ${s.t}`), r.fuente ? fuenteDe(r.fuente) : null),
        r.riesgo !== 'bien' ? h('small', { class: 'sub', style: { flexBasis: '100%' } }, limpiaTexto(r.motivo || '')) : null);
    }))
    : h('p', { class: 'sub', style: { margin: 0 } }, `Ninguna renovación conocida en los próximos 90 días. ${conFecha ? `${fmt.plural(conFecha, 'cliente tiene', 'clientes tienen')} fecha de fin apuntada.` : 'La app aún no tiene las fechas de fin de permanencia de los clientes: están en cada acuerdo y en el libro de cartera.'}`);
  return panel({ titulo: 'Renovaciones próximas', icono: 'cal', id: 'pr-ren', sub: 'Fin de permanencia en los próximos 90 días, con el riesgo de su semáforo estratégico.' }, cuerpo);
}

function panelSinObjetivo(res) {
  const pa = res?.sin_objetivo_por_account || {};
  const claves = Object.keys(pa).sort((a, b) => pa[b].length - pa[a].length);
  if (!claves.length) return null;
  return panel({ titulo: 'Sin objetivo del cliente · quién lo pide', icono: 'flag', id: 'pr-sin',
    sub: 'Cada account pide a su cliente el número por el que nos juzga (una métrica, una cifra y una fecha) y lo carga en la ficha.' },
  h('ul', { style: { listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: S(2) } }, claves.map(k => h('li', {},
    h('b', {}, `${k} · ${pa[k].length}`), h('span', { class: 'sub' }, `: ${pa[k].join(', ')}`)))));
}

export default {
  id: 'producto',
  titulo: 'Dirección de producto',
  grupo: 'Clientes',
  puestos_que_lo_ven: { direccion: 'todo', proyectos: 'todo', operaciones: 'resumen' },
  async render(cont, ctx) {
    ctx.titulo?.('Dirección de producto', 'Talleres de la oferta, semáforo estratégico y avance de cada cliente hacia su objetivo');
    cont.replaceChildren(h('p', { class: 'sub' }, 'Cargando…'));
    let d;
    try { d = await ctx.datosModulo('verdad/objetivos_clientes'); } catch (e) { d = null; }
    if (!d?.clientes) {
      cont.replaceChildren(vacio({ titulo: 'Sin datos de objetivos', porque: 'Falta data/verdad/objetivos_clientes.json.', que_hacer: 'Ejecuta python3 fuentes_verdad/generar_objetivos_clientes.py' }));
      return;
    }
    const logos = new Map((ctx.clientes || []).map(c => [c.id, c.logo]));
    const filas = d.clientes;
    const talleres = d.talleres || [];
    const r = d.resumen || {};
    const crit = filas.filter(f => f.semaforo === 'critico').length;
    const tarde = talleres.filter(t => t.tarde).length;
    let semPanel;
    const irA = (id, filtro) => () => {
      if (filtro && semPanel) { const b = [...semPanel.querySelectorAll('.chips-f button')].find(x => x.textContent.toLowerCase().startsWith(filtro)); b?.click(); }
      document.getElementById(id)?.closest('section')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };
    const franja = franjaCifras([
      { etiqueta: 'Talleres tarde', valor: tarde, estado: tarde ? 'rojo' : '', alPulsar: irA('pr-tall') },
      { etiqueta: 'Críticos', valor: crit, estado: crit ? 'rojo' : '', alPulsar: irA('pr-sem', 'crítico') },
      { etiqueta: 'Vigilar', valor: filas.filter(f => f.semaforo === 'vigilar').length, alPulsar: irA('pr-sem', 'vigilar') },
      { etiqueta: 'Bien', valor: filas.filter(f => f.semaforo === 'bien').length, alPulsar: irA('pr-sem', 'bien') },
      { etiqueta: 'Sin objetivo', valor: filas.filter(f => !f.objetivo).length, estado: filas.some(f => !f.objetivo) ? 'rojo' : '', alPulsar: irA('pr-sem', 'sin objetivo') },
    ], { etiqueta: 'Resumen de producto' });
    semPanel = panelSemaforo(filas, ctx, logos);
    const pie = h('p', { class: 'sub', style: { margin: 0 } },
      `Objetivos: ${r.con_objetivo ?? 0} de ${r.clientes ?? filas.length} clientes (${r.por_confianza?.dicho_por_cliente ?? 0} dichos por el cliente, ${r.por_confianza?.apuntado_por_account ?? 0} apuntados por el account, ${r.por_confianza?.deducido ?? 0} deducidos). Un solo sitio: fuentes_verdad/objetivos_clientes.json. `,
      frescura({ fuente: 'Objetivos y resultados', fecha: d.generado }));
    cont.replaceChildren(h('div', { class: 'pila', 'data-producto': '', style: { gap: S(4), minWidth: '0' } },
      franja, panelTalleres(talleres, ctx), semPanel, panelRecomendaciones(filas), panelRenovaciones(d.renovaciones || [], filas), panelSinObjetivo(r), pie));
  },
};
