// modulos/ajustes_avisos.js · Sistema › «Avisos automáticos» (3-oct-2026).
// Encargo de Tomás: «que en el chat de la app estén todas [las automatizaciones] y lo dejemos todo bien»: imputar horas,
// semáforo del lunes, informe mensual, cierre de facturación, resúmenes… Lo que antes se mandaba en ClickUp (a mano o con
// automatizaciones) lo manda ahora la app en sus canales de avisos, solo a quien le hace falta y a su hora.
//
// Qué enseña: cada regla con qué hace, cuándo (en la hora de cada persona o de Madrid), a quién, la condición («solo si hace
// falta»), dónde sale, el botón que lleva y qué pasa si se ignora. Cada jefa cambia las de su departamento (encender/apagar,
// hora, umbrales y horas del escalado); Mili y Tomás, todas. El resto ve «Lo que te llega a ti», sin tocar nada.
// «Cómo quedaría»: los mensajes que mandaría esa regla en su próximo momento, sin publicar nada.
// Ruta #/avisos-automaticos/hecho/<regla>/<persona>/<dia>: «Ya lo he hecho» desde el botón del aviso (para el escalado).
// Servidor: avisos_programados.py (GET /api/avisos_programados, /vista_previa; POST /cambiar, /hecho, /ejecutar).
// En «ver como», solo lectura (el servidor rechaza cualquier cambio). Nada sale de la app.

import { h, fmt, panel, chipEstado, icono, vacio, avisoParcial, avisoFlotante, chipsFiltro, tile, tiles, iniciales } from '../componentes.js';

const NOMBRE_CAMPO = { activa: 'Encendida', hora: 'Hora', escalado_horas: 'Escalado (horas)' };
const campoTxt = c => NOMBRE_CAMPO[c] || (c.startsWith('umbral.') ? 'Umbral' : c);
const valorTxt = v => (v === true ? 'sí' : v === false ? 'no' : v === null || v === undefined ? '—' : String(v).replace('.', ','));

function fila(etiqueta, valor, ico) {
  if (!valor) return null;
  return h('div', { style: ST.fila },
    h('span', { style: ST.et }, ico ? icono(ico, { clase: 's' }) : null, etiqueta),
    h('span', { style: ST.val }, valor));
}

// Sin <style> propio (auditoría 30): estilos en línea y SOLO con tokens de estilos.css.
const ST = {
  lista: { display: 'grid', gap: 'var(--s-4)' },
  regla: { display: 'grid', gap: 'var(--s-3)' },
  cab: { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 'var(--s-2) var(--s-3)' },
  h3: { margin: '0', font: 'var(--t-cuerpo)', fontWeight: '700', color: 'var(--ink)', flex: '1 1 220px', minWidth: '0', overflowWrap: 'anywhere' },
  que: { margin: '0', font: 'var(--t-cuerpo)', color: 'var(--ink)', maxWidth: '80ch' },
  datos: { display: 'grid', gap: 'var(--s-1)' },
  fila: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-1) var(--s-3)', font: 'var(--t-cuerpo)' },
  et: { display: 'inline-flex', alignItems: 'center', gap: 'var(--s-1)', color: 'var(--mid)', font: 'var(--t-meta)', flex: '0 0 160px' },
  val: { color: 'var(--ink)', minWidth: '0', flex: '1 1 260px', overflowWrap: 'anywhere' },
  edit: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-2) var(--s-4)', alignItems: 'flex-end', borderTop: 'var(--borde-suave)', paddingTop: 'var(--s-3)' },
  campo: { display: 'grid', gap: 'var(--s-1)', font: 'var(--t-meta)', color: 'var(--mid)', maxWidth: '320px' },
  ctl: { display: 'flex', gap: 'var(--s-1)', alignItems: 'center' },
  input: { minHeight: 'var(--s-8)', padding: '0 var(--s-2)', border: 'var(--borde-suave)', borderRadius: 'var(--r-s)', font: 'var(--t-cuerpo)', color: 'var(--ink)', background: 'var(--card)', width: '7em' },
  prev: { display: 'grid', gap: 'var(--s-2)', background: 'var(--card-2)', border: 'var(--borde-suave)', borderRadius: 'var(--r-m)', padding: 'var(--s-3)' },
  msg: { display: 'grid', gap: 'var(--s-1)', padding: 'var(--s-2) var(--s-3)', background: 'var(--card)', border: 'var(--borde-suave)', borderRadius: 'var(--r-m)' },
  msgP: { margin: '0', whiteSpace: 'pre-line', font: 'var(--t-cuerpo)', color: 'var(--ink)', overflowWrap: 'anywhere' },
  meta: { font: 'var(--t-meta)', color: 'var(--mid)' },
  botones: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-1)' },
  botonFalso: { display: 'inline-flex', alignItems: 'center', gap: 'var(--s-1)', font: 'var(--t-meta)', border: 'var(--borde-suave)', borderRadius: 'var(--r-s)', padding: '0 var(--s-2)', color: 'var(--accent-ink)', background: 'var(--accent-soft)' },
  pie: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-2) var(--s-4)', font: 'var(--t-meta)', color: 'var(--mid)' },
  inv: { width: '100%', borderCollapse: 'collapse', font: 'var(--t-meta)' },
  celda: { textAlign: 'left', padding: 'var(--s-1) var(--s-2)', borderBottom: 'var(--borde-suave)', verticalAlign: 'top', overflowWrap: 'anywhere' },
  invCaja: { overflowX: 'auto', maxWidth: '100%' },
};

async function hecho(c, ctx) {
  const [, regla, objetivo, dia] = ctx.params;
  ctx.titulo('Avisos automáticos', 'Marcar un aviso como hecho');
  if (ctx.soloLectura) {
    c.replaceChildren(vacio({ icono: 'info', titulo: 'Estás en «ver como»', texto: 'Desde aquí no se marca nada como hecho.' }));
    return;
  }
  try {
    const r = await ctx.api('avisos_programados/hecho', { metodo: 'POST', cuerpo: { regla, objetivo, dia } });
    c.replaceChildren(vacio({ tono: 'celebrar', titulo: r.ya ? 'Ya estaba marcado como hecho' : 'Anotado: hecho',
      texto: 'Ese aviso ya no sube a nadie. Queda en el chat, en su hilo, con tu nombre y la hora.',
      accion: h('a', { class: 'bt', href: '#/chat-equipo' }, icono('derecha'), 'Volver al chat') }));
  } catch (e) {
    c.replaceChildren(vacio({ tono: 'aviso', titulo: 'No se pudo marcar', texto: String(e?.message || 'Inténtalo de nuevo.'),
      accion: h('a', { class: 'bt', href: '#/avisos-automaticos' }, 'Ver los avisos automáticos') }));
  }
}

function vistaPrevia(caja, d) {
  const msgs = (d.envios || []).map(e => h('div', { style: ST.msg },
    h('span', { style: ST.meta }, `#${String(e.canal || '').replace(/^avisos-/, 'avisos-')} · para ${e.para}${e.menciones?.length ? ` · menciona a ${e.menciones.join(', ')}` : ''}${e.escala_a ? ` · si se ignora, sube a ${e.escala_a}` : ''}`),
    h('p', { style: ST.msgP }, e.texto),
    e.botones?.length ? h('div', { style: ST.botones }, e.botones.map(b => h('span', { style: ST.botonFalso }, icono('derecha', { clase: 's' }), b))) : null));
  caja.replaceChildren(h('div', { style: ST.prev, role: 'region', 'aria-label': 'Cómo quedaría' },
    h('b', {}, d.total ? `Así saldría el ${d.cuando}: ${fmt.plural(d.total, 'aviso', 'avisos')}${d.total > msgs.length ? ` (se enseñan ${msgs.length})` : ''}` : (d.sin_dato?.length ? 'Ahora no saldría nada' : `No saldría nada en los próximos días: nadie lo necesita`)),
    d.sin_dato?.length ? avisoParcial(`Sin el dato del día para ${d.sin_dato.join(', ')}: a esas personas no se les avisa hasta que llegue (mejor no avisar que avisar mal).`, { tipo: 'info' }) : null,
    d.error ? avisoParcial(`La regla ha fallado al calcular: ${d.error}`, { tipo: 'parcial' }) : null,
    ...msgs,
    h('small', { class: 'sub' }, 'Es una vista previa: no se ha publicado nada.')));
}

function editor(r, ctx, alGuardar) {
  const guardar = async (campo, valor, boton) => {
    if (boton) boton.disabled = true;
    try {
      const res = await ctx.api('avisos_programados/cambiar', { metodo: 'POST', cuerpo: { id: r.id, campo, valor } });
      avisoFlotante(campo === 'activa' ? (valor ? 'Encendida: vuelve a avisar' : 'Apagada: deja de avisar') : 'Guardado. Cuenta desde la próxima vuelta del reloj.');
      alGuardar(res.regla);
    } catch (e) {
      avisoFlotante(String(e?.message || 'No se pudo guardar'), { icono: 'alert' });
      if (boton) boton.disabled = false;
    }
  };
  const ctl = [];
  const bAct = h('button', { type: 'button', class: r.activa ? 'bt' : 'bt pri', 'aria-pressed': String(r.activa),
    on: { click: () => guardar('activa', !r.activa, bAct) } }, icono(r.activa ? 'cerrar' : 'ok'), r.activa ? 'Apagar' : 'Encender');
  ctl.push(h('div', { style: ST.campo }, h('span', {}, 'Estado'), bAct));
  const hora = h('input', { type: 'time', style: ST.input, value: r.hora || '09:00', 'aria-label': `Hora de «${r.nombre}»` });
  const bHora = h('button', { type: 'button', class: 'bt mini', on: { click: () => guardar('hora', hora.value, bHora) } }, 'Guardar');
  ctl.push(h('label', { style: ST.campo }, h('span', {}, r.zona === 'persona' ? 'Hora (la de cada persona)' : 'Hora (Madrid)'), h('span', { style: ST.ctl }, hora, bHora)));
  for (const u of r.umbrales || []) {
    const inp = h('input', { type: 'number', style: ST.input, value: u.valor, min: u.min, max: u.max, step: u.paso || 1, 'aria-label': u.texto });
    const b = h('button', { type: 'button', class: 'bt mini', on: { click: () => guardar(`umbral.${u.clave}`, Number(inp.value), b) } }, 'Guardar');
    ctl.push(h('label', { style: ST.campo }, h('span', {}, u.texto), h('span', { style: ST.ctl }, inp, u.unidad ? h('span', {}, u.unidad) : null, b)));
  }
  if (r.escalado?.editable !== false) {
    const inp = h('input', { type: 'number', style: ST.input, value: r.escalado?.tras_horas || 0, min: 0, max: 168, step: 1, 'aria-label': 'Horas hasta el escalado' });
    const b = h('button', { type: 'button', class: 'bt mini', on: { click: () => guardar('escalado_horas', Number(inp.value), b) } }, 'Guardar');
    ctl.push(h('label', { style: ST.campo }, h('span', {}, 'Si se ignora, subir a las (0 = nunca)'), h('span', { style: ST.ctl }, inp, h('span', {}, 'h'), b)));
  }
  return h('div', { style: ST.edit }, ...ctl);
}

function tarjeta(r, ctx, S) {
  const caja = h('div');
  const prev = h('div');
  const pintar = () => {
    const bPrev = h('button', { type: 'button', class: 'bt', on: { click: async () => {
      bPrev.disabled = true;
      prev.replaceChildren(h('p', { class: 'sub' }, 'Calculando…'));
      try { vistaPrevia(prev, await ctx.api(`avisos_programados/vista_previa?id=${encodeURIComponent(r.id)}`)); }
      catch (e) { prev.replaceChildren(avisoParcial(String(e?.message || 'No se pudo calcular'), { tipo: 'parcial' })); }
      bPrev.disabled = false;
    } } }, icono('ojo'), 'Ver cómo quedaría');
    const cambios = r.cambios?.length ? h('details', { style: ST.meta },
      h('summary', {}, `Cambios (${r.cambios.length})`),
      h('ul', { style: { margin: 'var(--s-1) 0 0', paddingLeft: 'var(--s-4)', display: 'grid', gap: 'var(--s-1)' } }, r.cambios.map(x => h('li', {}, `${ctx.nombre ? ctx.nombre(x.quien) : x.quien} · ${fmt.fechaHora(x.hora)} · ${campoTxt(x.campo)}: ${valorTxt(x.antes)} → ${valorTxt(x.valor)}`)))) : null;
    caja.replaceChildren(h('article', { class: 'panel', style: { ...ST.regla, padding: 'var(--s-4)' }, id: `regla-${r.id}`, 'data-regla': r.id },
      h('div', { style: ST.cab },
        h('span', { class: `ico-c ${r.activa ? 'verde' : 'gris'}` }, icono(r.icono || 'campana')),
        h('h3', { style: ST.h3 }, r.nombre),
        chipEstado(r.activa ? 'verde' : 'gris', r.activa ? 'Encendida' : 'Apagada'),
        chipEstado('gris', r.departamento_nombre || r.departamento, { punto: false })),
      h('p', { style: ST.que }, r.que_hace),
      h('div', { style: ST.datos },
        fila('Cuándo', r.cuando, 'clock'),
        fila('A quién', r.a_quien, 'persona'),
        fila('Solo si', r.condicion, 'filtro'),
        fila('Dónde sale', r.canal, 'campana'),
        fila('Botón', r.boton, 'derecha'),
        fila('Si se ignora', r.escalado?.tras_horas ? `A las ${r.escalado.tras_horas} h, si el dato dice que sigue sin hacerse: ${r.escalado.texto || 'sube a su jefa'}` : (r.escalado?.texto || 'No sube a nadie'), 'flag'),
        fila('Qué mejora', r.mejora, 'spark'),
        r.apagar_en_origen ? fila('En ClickUp', `Recomendación para Tomás: ${r.apagar_en_origen}`, 'info') : null),
      r.puede_editar && !ctx.soloLectura ? editor(r, ctx, nueva => { Object.assign(r, nueva); pintar(); }) : null,
      h('div', { style: ST.pie },
        r.envios_semana !== null && r.envios_semana !== undefined ? h('span', {}, `Esta semana: ${fmt.plural(r.envios_semana, 'aviso enviado', 'avisos enviados')} · ${fmt.plural(r.escalados_semana || 0, 'escalado', 'escalados')}${r.ultimo_envio ? ` · último el ${fmt.fechaHora(r.ultimo_envio)}` : ''}`) : null,
        r.le_llega && !r.puede_editar ? h('span', {}, 'Te llega a ti cuando hace falta. La cambia la jefa de su departamento, Mili o Tomás.') : null),
      r.puede_editar ? h('div', { style: ST.botones }, bPrev) : null,
      prev,
      cambios));
  };
  pintar();
  return caja;
}

function inventario(inv) {
  if (!inv?.filas?.length) return null;
  const filas = inv.filas;
  return panel({ titulo: `Lo que había en ClickUp y otras herramientas · ${filas.length}`, icono: 'libro',
    sub: 'Inventario de los últimos 90 días (solo lectura). La columna de la derecha es la recomendación para Tomás: nada se ha tocado fuera de la app.' },
  inv.pendientes?.length ? h('div', { style: ST.datos }, h('b', {}, 'Lo que la app todavía no hace (y por qué)'),
    ...inv.pendientes.map(x => fila(x.que, x.porque, 'info'))) : null,
  h('details', {}, h('summary', {}, 'Ver el inventario'),
    h('div', { style: ST.invCaja }, h('table', { style: ST.inv },
      h('thead', {}, h('tr', {}, ['Qué', 'Dónde', 'Cuándo', 'Quién', 'Tipo', 'En la app', 'Apagar fuera'].map(t => h('th', { scope: 'col', style: ST.celda }, t)))),
      h('tbody', {}, filas.map(x => h('tr', {},
        h('td', { style: ST.celda }, x.que || '—'), h('td', { style: ST.celda }, x.canal || '—'), h('td', { style: ST.celda }, [x.frecuencia, x.hora].filter(Boolean).join(' · ') || '—'),
        h('td', { style: ST.celda }, x.quien || '—'), h('td', { style: ST.celda }, x.automatico ? 'automático' : 'a mano'), h('td', { style: ST.celda }, x.regla_app || '—'),
        h('td', { style: ST.celda }, x.apagar_en_origen || '—'))))))));
}

export default {
  id: 'avisos-automaticos',
  titulo: 'Avisos automáticos',
  grupo: 'Sistema',
  puestos_que_lo_ven: { '*': 'suyo', direccion: 'todo', operaciones: 'todo' },
  async render(c, ctx) {
    if (ctx.params[0] === 'hecho') return hecho(c, ctx);
    ctx.titulo('Avisos automáticos', 'Lo que la app recuerda sola en el chat: a quién, cuándo y solo si hace falta');
    c.replaceChildren(h('p', { class: 'sub' }, 'Cargando…'));
    let d;
    try { d = await ctx.api('avisos_programados'); }
    catch (e) {
      c.replaceChildren(vacio({ tono: 'aviso', titulo: 'No se pudieron leer los avisos automáticos', texto: String(e?.message || ''), quien: 'Agus' }));
      return;
    }
    const reglas = d.reglas || [];
    const mias = reglas.filter(r => r.puede_editar);
    const meLlegan = reglas.filter(r => !r.puede_editar);
    const S = { dep: 'todos' };
    const lista = h('div', { style: ST.lista });
    const pintarLista = () => {
      const ver = x => S.dep === 'todos' || x.departamento === S.dep;
      const bloques = [];
      if (mias.length) bloques.push(h('h2', { class: 'sub', style: { margin: 'var(--s-2) 0 0' } }, ctx.soloLectura ? 'Las de su departamento' : 'Las que puedes cambiar'), ...mias.filter(ver).map(r => tarjeta(r, ctx, S)));
      if (meLlegan.length) bloques.push(h('h2', { class: 'sub', style: { margin: 'var(--s-2) 0 0' } }, 'Lo que te llega a ti'), ...meLlegan.filter(ver).map(r => tarjeta(r, ctx, S)));
      if (!reglas.length) bloques.push(vacio({ icono: 'campana', titulo: 'Ningún aviso automático te toca', texto: 'Cuando haya una regla para tu puesto, sale aquí.' }));
      lista.replaceChildren(...bloques);
      if (ctx.params[0]) document.getElementById(`regla-${ctx.params[0]}`)?.scrollIntoView({ block: 'start' });
    };
    const deps = [...new Set(reglas.map(r => r.departamento))];
    const nombreDep = id => (d.departamentos || []).find(x => x.id === id)?.nombre || id;
    const filtros = deps.length > 1 ? chipsFiltro({ etiqueta: 'Departamento', clave: 'avisos-auto-dep',
      opciones: [{ valor: 'todos', texto: 'Todos', cuenta: reglas.length }, ...deps.map(x => ({ valor: x, texto: nombreDep(x), cuenta: reglas.filter(r => r.departamento === x).length }))],
      alCambiar: v => { S.dep = v || 'todos'; pintarLista(); } }) : null;
    if (filtros) S.dep = filtros.valor() || 'todos';
    const act = mias.filter(r => r.activa).length;
    const enviados = mias.reduce((s, r) => s + (r.envios_semana || 0), 0);
    const escalados = mias.reduce((s, r) => s + (r.escalados_semana || 0), 0);
    const bEjec = d.puede_ejecutar ? h('button', { type: 'button', class: 'bt', on: { click: async () => {
      bEjec.disabled = true;
      try {
        const r = await ctx.api('avisos_programados/ejecutar', { metodo: 'POST', cuerpo: {} });
        avisoFlotante(r.publicados || r.escalados ? `Reloj pasado: ${fmt.plural(r.publicados, 'aviso nuevo', 'avisos nuevos')} y ${fmt.plural(r.escalados, 'escalado', 'escalados')}` : 'Reloj pasado: no tocaba nada nuevo');
        window.dispatchEvent(new CustomEvent('ro:avisos'));
      } catch (e) { avisoFlotante(String(e?.message || 'No se pudo'), { icono: 'alert' }); }
      bEjec.disabled = false;
    } } }, icono('clock'), 'Pasar el reloj ahora') : null;
    pintarLista();
    c.replaceChildren(...[
      avisoParcial('Nada sale de la app: los avisos llegan al Chat del equipo (canales de avisos) y a la campana. Cada uno llega solo a quien le hace falta, a su hora, con el botón para hacerlo. Lo que se repetía en ClickUp queda aquí; apagarlo allí lo decide Tomás.', { tipo: 'info', titulo: 'Cómo funciona:' }),
      mias.length ? tiles([
        tile({ icono: 'campana', etiqueta: 'Reglas encendidas', valor: `${act} de ${mias.length}`, estado: act === mias.length ? 'verde' : 'ambar' }),
        tile({ icono: 'chat', etiqueta: 'Avisos esta semana', valor: fmt.num(enviados), estado: 'gris' }),
        tile({ icono: 'flag', etiqueta: 'Subieron a la jefa', valor: fmt.num(escalados), estado: escalados ? 'ambar' : 'verde' }),
      ]) : null,
      h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-2)', alignItems: 'center', justifyContent: 'space-between' } }, filtros, bEjec),
      ctx.soloLectura ? avisoParcial('Estás en «ver como»: ves lo de las dos personas y no se cambia nada.', { tipo: 'info' }) : null,
      lista,
      inventario(d.inventario)].filter(Boolean));
  },
};
