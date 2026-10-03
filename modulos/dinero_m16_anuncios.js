// modulos/dinero_m16_anuncios.js · dos bloques que E10 añade a M16 «Ventas de RO» (ventas_ro.js solo los llama):
//   8 · De qué anuncio exacto viene cada conversión (campo «Anuncio de origen» escrito en GHL el 2-oct y pestaña «De qué anuncio»
//       del panel v30). Por anuncio para todos los que ven M16; la lista conversión a conversión, con nombres enmascarados, solo
//       para quien ve M16 entero (servir.py: «conversiones» es solo_todo_sin_cliente y lleva setter «_closer»).
//   9 · Previsión de altas desde el embudo de GHL frente a los huecos de los accounts (cartera ≤ 12, D-07; 21_CARGA_ACCOUNTS_2OCT.md).
// Datos: data/ventas_ro_extra/anuncios.json ← fuentes_dinero/generar_dinero.py.

import { h, fmt, tile, tiles, chipEstado, chipsFiltro, tablaDensa, panel, vacio, icono, barraProgreso, avisoParcial } from '../componentes.js';
import { cargarDatos } from './dinero_comun.js';

const CONF_ESTADO = { 'Seguro': 'verde', 'Muy probable': 'verde', 'Dicho por Tomás': 'azul', 'Probable': 'ambar', 'Uno de dos': 'ambar', 'Sin anuncio': 'gris' };

export async function pintarAnunciosYPrevision(cont, ctx) {
  const { d } = await cargarDatos(ctx, 'ventas_ro_extra/anuncios');
  if (!d) {
    cont.append(panel({ titulo: '8 · De qué anuncio viene cada conversión', icono: 'target' },
      vacio({ icono: 'target', titulo: 'Sin datos de atribución', texto: 'Falta la lectura de qué anuncio trajo cada conversión (pestaña «De qué anuncio» del panel de resultados). La rehace la recarga de la noche.', quien: 'Agus' })));
    return;
  }
  const todo = ctx.nivel === 'todo';
  const r = d.resumen || {};
  const conv = d.conversiones || [];

  // ---------------------------------------------------------------- 8 · por anuncio
  const maxC = Math.max(1, ...(d.por_anuncio || []).map(a => a.conversiones));
  const tablaAnuncios = tablaDensa({ filas: d.por_anuncio || [], apilable: true, columnas: [
    { clave: 'anuncio', titulo: 'Anuncio', principal: true, celda: a => h('span', { class: 'pila', style: { gap: 'var(--s-1)', minWidth: '0' } }, h('b', {}, a.anuncio), a.campana ? h('span', { class: 'sub' }, a.campana) : null) },
    { clave: 'conversiones', titulo: 'Conversiones', num: true, celda: a => h('div', { class: 'pila' }, h('span', {}, `${a.conversiones} · ${a.seguras} seguras`), barraProgreso({ valor: a.conversiones, max: maxC, estado: a.anuncio === 'Sin anuncio medible' ? null : 'verde' })) },
    { clave: 'citas', titulo: 'Con cita', num: true },
    { clave: 'clientes', titulo: 'Clientes', num: true, celda: a => a.clientes ? chipEstado('verde', String(a.clientes)) : '0' }] });
  const cuerpo8 = h('div', { class: 'cuerpo pila' },
    tiles([
      tile({ icono: 'target', etiqueta: 'Conversiones con anuncio medible', valor: r.total - r.sin_anuncio, unidad: `de ${r.total}`, contexto: `${r.seguros} seguras o muy probables · ${r.probables} probables · ${r.dichos} dichas por Tomás`, medible: 'hoy',
        frescura: { fuente: 'Atribución (panel de resultados)', fecha: d.fuente?.hora } }),
      tile({ icono: 'crown', etiqueta: 'Clientes que vienen de un anuncio', valor: r.clientes_de_anuncio, unidad: `de ${r.clientes}`, contexto: 'El resto: bio de Instagram, web, referidos o relaciones', medible: 'hoy' }),
    ]),
    tablaAnuncios,
    h('p', { class: 'fila sub' }, icono('info', { clase: 's' }), `En GHL: ${d.fuente?.campos_ghl}.`,
      todo && d.fuente?.panel ? h('a', { class: 'bt mini', href: d.fuente.panel, target: '_blank', rel: 'noopener' }, 'Abrir la pestaña «De qué anuncio» del panel de resultados') : null));

  // conversión a conversión (solo nivel «todo»: el servidor no manda la lista a los demás)
  if (todo && conv.length) {
    const zona = h('div');
    const ESTADOS = ['Seguro', 'Muy probable', 'Probable', 'Uno de dos', 'Dicho por Tomás', 'Sin anuncio'];
    const pintarL = v => zona.replaceChildren(tablaDensa({ filas: conv.filter(c => !v || (v === 'clientes' ? c.cliente : c.confianza === v)), apilable: true,
      buscar: { placeholder: 'Buscar anuncio o etapa…', campos: ['anuncio', 'etapa', 'campana'] }, orden: { clave: 'alta', dir: 'desc' }, columnas: [
        { clave: 'nombre_m', titulo: 'Contacto', principal: true, celda: c => h('span', { class: 'fila', style: { gap: 'var(--s-2)' } }, h('b', {}, c.nombre_m || 'sin nombre'), c.cliente ? chipEstado('verde', 'cliente') : null) },
        { clave: 'anuncio', titulo: 'Anuncio exacto', celda: c => c.anuncio ? h('span', {}, c.anuncio, h('span', { class: 'sub' }, ` · ${c.conjunto || ''}`)) : h('span', { class: 'dim' }, 'sin anuncio') },
        { clave: 'confianza', titulo: 'Cómo se sabe', celda: c => h('span', { title: c.por_que }, chipEstado(CONF_ESTADO[c.confianza] || 'gris', c.confianza)) },
        { clave: 'etapa', titulo: 'Etapa' },
        { clave: 'alta', titulo: 'Alta', celda: c => fmt.fecha(c.alta) },
        { clave: 'ghl', titulo: '', ordenable: false, celda: c => h('a', { class: 'bt mini', href: c.ghl, target: '_blank', rel: 'noopener' }, icono('ext', { clase: 's' }), 'GHL') }] }));
    const ch = chipsFiltro({ opciones: [{ valor: '', texto: 'Todas', cuenta: conv.length }, { valor: 'clientes', texto: 'Clientes', cuenta: conv.filter(c => c.cliente).length, icono: 'crown' },
      ...ESTADOS.map(e => ({ valor: e, texto: e, cuenta: conv.filter(c => c.confianza === e).length }))], clave: 'ventas-anuncios', etiqueta: 'Ver', alCambiar: pintarL });
    pintarL(ch.valor());
    cuerpo8.append(h('div', { class: 'titulo-seccion' }, icono('users', { clase: 's' }), 'Conversión a conversión'), ch, zona,
      avisoParcial('Nombres enmascarados. El contacto completo, en GoHighLevel.', { tipo: 'info' }));
  }
  cont.append(panel({ titulo: '8 · De qué anuncio exacto viene cada conversión', icono: 'target', sub: 'Conversión = tarjeta en «Ventas RO» o cita de venta. Método del 2-oct: id del anuncio en GHL → etiqueta → hora de alta frente a leads por hora de Meta.' }, cuerpo8));

  // ---------------------------------------------------------------- 9 · previsión de altas frente a huecos
  const p = d.prevision;
  if (!p) return;
  const est = p.altas_esperadas > p.huecos_utiles ? 'rojo' : p.altas_esperadas > p.huecos_utiles * 0.7 ? 'ambar' : 'verde';
  const cuerpo9 = h('div', { class: 'cuerpo pila' },
    tiles([
      tile({ icono: 'rocket', etiqueta: 'Altas que vienen', valor: fmt.num(p.altas_esperadas, 0), unidad: 'en semanas', contexto: `${p.pipeline.contratos} contratos · ${p.pipeline.propuestas} propuestas · ${p.pipeline.citas + p.pipeline.piden_reunion} citas o peticiones`,
        medible: 'medias', medibleDetalle: p.tasas?.texto }),
      tile({ icono: 'eq', etiqueta: 'Huecos útiles en accounts', valor: p.huecos_utiles, unidad: `de ${p.huecos_total}`, estado: est,
        contexto: `Hasta ${p.tope} clientes por account; fuera quien lleva 4 o más arranques a la vez`, medible: 'hoy' }),
    ]),
    avisoParcial(p.texto, { tipo: est === 'verde' ? 'info' : 'parcial', titulo: est === 'rojo' ? 'No cabe.' : est === 'ambar' ? 'Justo.' : 'Cabe.' }));
  if ((p.accounts || []).length) {
    cuerpo9.append(tablaDensa({ filas: p.accounts, apilable: true, orden: { clave: 'huecos', dir: 'desc' }, columnas: [
      { clave: 'nombre', titulo: 'Account', principal: true },
      { clave: 'clientes', titulo: 'Cartera', num: true, celda: a => h('div', { class: 'pila' }, h('span', {}, `${a.clientes} de ${p.tope}`), barraProgreso({ valor: a.clientes, max: p.tope, estado: a.estado })) },
      { clave: 'nuevos', titulo: 'Arranques', num: true },
      { clave: 'huecos', titulo: 'Huecos', num: true, celda: a => chipEstado(a.estado, String(Math.max(0, a.huecos))) },
      { clave: 'nota', titulo: 'Ojo', celda: a => a.nota ? h('span', { class: 'sub' }, a.nota) : '—' }] }));
  } else {
    cuerpo9.append(h('p', { class: 'sub' }, 'El detalle por account lo ven dirección y operaciones.'));
  }
  if ((p.sin_account || []).length) cuerpo9.append(avisoParcial(`Clientes activos sin account: ${p.sin_account.join(', ')}. Restan huecos cuando se asignen (lo decide Mili).`, { titulo: 'Sin account.' }));
  cont.append(panel({ titulo: '9 · Previsión de altas frente a huecos de los accounts', icono: 'cal', sub: 'Embudo de GHL de hoy × tasas de septiembre, frente a la cartera de cada account (tope de 12)' }, cuerpo9));
}
