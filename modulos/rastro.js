// modulos/rastro.js · M21 Decisiones y rastro (E0). Cada uno ve lo suyo; Tomás, todo.
// Lee local.db por servir.py: tabla `registro` (imborrable, hora del servidor) y la cola de `acciones` simuladas.

import { h, tablaDensa, chipEstado, estadoVacio, panel, avisoParcial, fmt } from '../componentes.js';

/** «2 oct, 17:12» en hora de Madrid (el servidor guarda UTC). */
const cuando = t => { if (!t) return '—'; const d = new Date(String(t).replace(' ', 'T') + (/[zZ]|[+-]\d\d:?\d\d$/.test(t) ? '' : 'Z')); return Number.isNaN(+d) ? t : d.toLocaleString('es-ES', { timeZone: 'Europe/Madrid', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }).replace('.', ''); };

export default {
  id: 'rastro',
  titulo: 'Decisiones y rastro',
  grupo: 'Sistema',
  puestos_que_lo_ven: { '*': 'suyo', direccion: 'todo' },
  async render(cont, ctx) {
    if (!ctx.servidor) {
      cont.append(estadoVacio({ titulo: 'El rastro vive en el servidor', porque: 'Sin servidor solo hay un rastro de esta pestaña del navegador, que no vale como prueba.', que_hacer: 'Abre la app desde su servidor local (lo arranca Agus).' }));
      return;
    }
    let R;
    try { R = await ctx.api('rastro'); } catch (e) { cont.append(estadoVacio({ titulo: 'No se pudo leer el rastro', porque: e.message })); return; }
    const nombre = Object.fromEntries(ctx.datos.personas.map(p => [p.id, p.alias || p.nombre]));
    cont.append(avisoParcial(R.todo ? 'Ves el rastro de todo el equipo. Nada se borra: desmarcar crea una anulación.' : 'Ves tu propio rastro. Nada se borra: desmarcar crea una anulación.', { tipo: 'info' }));
    const filas = R.registro.map(r => ({ ...r, quien_txt: nombre[r.quien] || r.quien, como_txt: r.como ? nombre[r.como] || r.como : '' }));
    cont.append(panel({ titulo: 'Rastro', icono: 'hist', sub: `${fmt.num(filas.length)} últimas filas · hora de Madrid` }, tablaDensa({
      filas,
      buscar: { campos: ['accion', 'clave', 'quien_txt', 'coleccion', 'datos'], placeholder: 'Buscar' },
      filtros: [{ clave: 'accion', titulo: 'Qué' }, { clave: 'quien_txt', titulo: 'Quién' }, { clave: 'origen', titulo: 'Origen' }],
      orden: { clave: 'id', dir: 'desc' },
      columnas: [
        { clave: 'creada', titulo: 'Cuándo', celda: r => h('span', { style: { whiteSpace: 'nowrap', color: 'var(--mid)' }, title: r.creada }, cuando(r.creada)) },
        { clave: 'quien_txt', titulo: 'Quién', principal: true, celda: r => h('span', {}, r.quien_txt, r.como_txt ? h('span', { class: 'sub' }, ` como ${r.como_txt}`) : null) },
        { clave: 'accion', titulo: 'Qué', celda: r => chipEstado(r.anula_a ? 'gris' : /denegado/.test(r.accion || '') ? 'rojo' : 'azul', r.anula_a ? `anula #${r.anula_a}` : r.accion) },
        { clave: 'coleccion', titulo: 'Dónde' },
        { clave: 'clave', titulo: 'Sobre qué' },
        { clave: 'motivo', titulo: 'Motivo' },
      ],
      vacio: { titulo: 'Aún no hay rastro', porque: 'Cuando alguien use «ver como», «ver datos» de un lead, Ajustes o un botón, sale aquí.' },
    })));
    cont.append(panel({ titulo: 'Acciones en cola (simuladas)', icono: 'send', sub: 'En el prototipo ningún botón llama a una herramienta externa: queda aquí con su vista previa. Se ejecutarán cuando la app se despliegue.' }, tablaDensa({
      filas: R.acciones.map(a => ({ ...a, quien_txt: nombre[a.quien] || a.quien })),
      orden: { clave: 'id', dir: 'desc' },
      columnas: [
        { clave: 'creada', titulo: 'Cuándo', celda: a => h('span', { style: { whiteSpace: 'nowrap', color: 'var(--mid)' }, title: a.creada }, cuando(a.creada)) }, { clave: 'quien_txt', titulo: 'Quién', principal: true },
        { clave: 'herramienta', titulo: 'Herramienta' }, { clave: 'tipo', titulo: 'Qué' }, { clave: 'objeto', titulo: 'Sobre qué' },
        { clave: 'estado', titulo: 'Estado', celda: a => chipEstado(a.estado === 'simulada' ? 'gris' : a.estado === 'ok' ? 'verde' : 'rojo', a.estado) },
        { clave: 'texto', titulo: 'Texto', celda: a => h('span', { class: 'sub' }, (a.texto || '').slice(0, 140)) },
      ],
      vacio: { titulo: 'Ninguna acción en cola', porque: 'Los botones de los módulos dejan aquí lo que harían.', celebrar: false },
    })));
  },
};
