// modulos/indicadores.js · Catálogo de indicadores (E0). Solo Tomás y Mili.
// Los 229 indicadores de puesto (228 de las fichas + «resultados de su cartera» del account, R13) de las fichas G1-G3 y, aparte, los 23 de «Fase 2», con fórmula, umbral
// verde/ámbar/rojo y su origen (la decisión firmada manda), estado de medición, fuente, frecuencia y módulo.
// Los módulos NO se inventan umbrales: usan ctx.indicador(id) y fichaCatalogo().
// Diseño (auditoría 30, N6): sin emojis (los puntos de color son del sistema), filtros de medición y de umbral
// firmado como chips con su cuenta, la tarjeta de muestra ARRIBA de la tabla y 15 filas por página (móvil apilado).

import { h, tablaDensa, chipEstado, chipsFiltro, selloMedible, panel, fichaCatalogo, estadoVacio, rejillaTarjetas, tile } from '../componentes.js';
import { PUESTO } from '../permisos.js';
import { MODULOS } from './indice.js';

const TITULO_MODULO = Object.fromEntries(MODULOS.map(m => [m.id, m.titulo]));

const MED = { hoy: 'Se mide hoy', medias: 'A medias', no: 'Todavía no' };
/** Fuera emojis del texto de las fichas: los colores se dicen con palabras (guía 30, 3.12). */
const sinEmoji = s => (typeof s === 'string' ? s.replace(/🟢/g, 'verde').replace(/🟡/g, 'ámbar').replace(/🔴/g, 'rojo').replace(/✅/g, '✓').replace(/[⭐⚠️]️?/g, '').replace(/\s{2,}/g, ' ').trim() : s);

export default {
  id: 'indicadores',
  titulo: 'Catálogo de indicadores',
  grupo: 'Sistema',
  puestos_que_lo_ven: { direccion: 'todo', operaciones: 'todo' },
  render(cont, ctx) {
    ctx.titulo?.('Catálogo de indicadores', 'Los indicadores de cada puesto con su umbral, de dónde sale y si se miden hoy');
    const todos = ctx.indicadores().map(i => Object.fromEntries(Object.entries(i).map(([k, v]) => [k, sinEmoji(v)])));
    if (!todos.length) {
      cont.append(estadoVacio({ titulo: 'Sin catálogo', porque: 'No se ha podido leer el catálogo de indicadores.', que_hacer: 'Recarga la página; si sigue, avisa a Tomás.' }));
      return;
    }
    const dePuesto = todos.filter(i => !i.fase2);
    const fase2 = todos.filter(i => i.fase2);
    const cuenta = e => dePuesto.filter(i => i.medible === e).length;

    const filas = l => l.map(x => ({
      ...x, puesto_txt: PUESTO[x.puesto]?.nombre || x.puesto, medible_txt: MED[x.medible], modulo_txt: TITULO_MODULO[x.modulo] || '—',
      firmado: x.decision ? (x.regla_firmada ? 'Sí (regla por cliente)' : 'Sí') : 'No',
    }));
    const columnas = [
      { clave: 'nombre', titulo: 'Indicador', principal: true, celda: x => h('span', { class: 'fila', style: { gap: 'var(--s-2)' } }, h('span', {}, x.nombre),
        x.el_que_manda ? chipEstado('verde', 'El que manda', { punto: false }) : x.segundo_de ? chipEstado('gris', 'Segundo', { punto: false }) : null,
        x.prioritario ? chipEstado('azul', 'Prioritario', { punto: false }) : null) },
      { clave: 'puesto_txt', titulo: 'Puesto' },
      { clave: 'umbral', titulo: 'Verde / ámbar / rojo' },
      { clave: 'firmado', titulo: 'Umbral firmado' },
      { clave: 'medible_txt', titulo: 'Medición', celda: x => selloMedible(x.medible, x.medible_porque) },
      { clave: 'frecuencia', titulo: 'Frecuencia' },
      { clave: 'modulo_txt', titulo: 'Pantalla' },
    ];

    // ---- la tarjeta de muestra, arriba (se ve sin bajar 200 filas)
    const vista = h('div', { hidden: true });
    const abrir = x => {
      vista.hidden = false;
      vista.replaceChildren(panel({ titulo: x.nombre, sub: PUESTO[x.puesto]?.nombre || '', acciones: h('button', { type: 'button', class: 'bt', on: { click: () => { vista.replaceChildren(); vista.hidden = true; } } }, 'Cerrar') },
        h('div', { class: 'cuerpo pila' }, h('div', { class: 'rejilla' }, fichaCatalogo(x, { valor: null, unidad: 'ejemplo sin dato' })),
          h('p', { class: 'sub' }, `Fuente: ${x.fuente} · ${x.adelantado}`))));
      vista.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    };

    // ---- cifras: cuántos se miden hoy (la cifra que manda), a medias y todavía no
    cont.append(rejillaTarjetas([
      tile({ icono: 'ok', etiqueta: 'Se miden hoy', valor: cuenta('hoy'), unidad: `de ${dePuesto.length}`, estado: 'verde', contexto: 'Con dato real cada día' }),
      tile({ icono: 'clock', etiqueta: 'A medias', valor: cuenta('medias'), unidad: `de ${dePuesto.length}`, estado: 'ambar', contexto: 'Con dato parcial: se leen como aviso' }),
      tile({ icono: 'hist', etiqueta: 'Todavía no', valor: cuenta('no'), unidad: `de ${dePuesto.length}`, estado: 'gris', contexto: `Y ${fase2.length} de Fase 2, aparte` }),
      tile({ icono: 'target', etiqueta: 'El que manda', valor: dePuesto.filter(i => i.el_que_manda).length, unidad: 'puestos', contexto: 'Cliente primero: el del account, los resultados de su cartera' }),
      tile({ icono: 'check', etiqueta: 'Umbral firmado', valor: todos.filter(i => i.decision).length, unidad: `de ${todos.length}`, contexto: 'El resto, propuesta sin firmar' }),
    ]), vista);

    // ---- tabla con filtros como chips (medición y firma); puesto y pantalla, en el filtro de la tabla
    const zona = h('div');
    const chMed = chipsFiltro({ etiqueta: 'Medición', clave: 'indicadores.med', opciones: [
      { valor: '', texto: 'Todas', cuenta: dePuesto.length },
      ...['hoy', 'medias', 'no'].map(k => ({ valor: k, texto: MED[k], cuenta: cuenta(k) }))], alCambiar: () => pintar() });
    const chFir = chipsFiltro({ etiqueta: 'Umbral', clave: 'indicadores.firma', opciones: [
      { valor: '', texto: 'Todos' }, { valor: 'si', texto: 'Firmado', cuenta: dePuesto.filter(i => i.decision).length }, { valor: 'no', texto: 'Sin firmar', cuenta: dePuesto.filter(i => !i.decision).length }], alCambiar: () => pintar() });
    const pintar = () => {
      const m = chMed.valor(); const f = chFir.valor();
      const l = dePuesto.filter(i => (!m || i.medible === m) && (!f || (f === 'si') === !!i.decision));
      zona.replaceChildren(tablaDensa({
        filas: filas(l), apilable: true, porPagina: 15,
        buscar: { campos: ['nombre', 'formula', 'fuente', 'umbral_origen'], placeholder: 'Buscar indicador, fórmula o fuente' },
        filtros: [{ clave: 'puesto_txt', titulo: 'Puesto' }, { clave: 'modulo_txt', titulo: 'Pantalla' }],
        columnas, alPulsar: abrir, etiquetaFila: x => `${x.nombre}, ${x.puesto_txt}. Ver tarjeta`,
      }));
    };
    pintar();
    cont.append(panel({ titulo: 'Indicadores de puesto', sub: 'Pulsa una fila para ver la tarjeta tal y como sale en los módulos, con «¿Qué es?».' },
      h('div', { class: 'cuerpo pila' }, chMed, chFir), zona));

    cont.append(h('details', { class: 'panel' },
      h('summary', { class: 'fila', style: { padding: 'var(--s-3) var(--relleno)', cursor: 'pointer', minHeight: '44px' } }, h('b', {}, `Fase 2 (aparte) · ${fase2.length}`), h('span', { class: 'sub' }, '· no se construye nada encima hasta que se puedan medir')),
      tablaDensa({ filas: filas(fase2), apilable: true, porPagina: 15, columnas: columnas.filter(c => c.clave !== 'firmado'), alPulsar: abrir, buscar: { campos: ['nombre'], placeholder: 'Buscar' } })));
  },
};
