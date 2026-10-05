// modulos/gasto_ia.js · Sistema › Gasto de IA (3-oct-2026). Encargo de Tomás: «no quiero una IA con tokens infinitos;
// me da miedo gastar muchísimo». SOLO Tomás (el servidor lo vuelve a comprobar: GET /api/ia/gasto da 403 a cualquier otro
// y en «ver como»). Enseña el gasto del mes y del día, la previsión a fin de mes, por función, por persona y por modelo,
// las últimas llamadas (sin contenido) y los topes, que se cambian aquí con motivo y quedan en el rastro
// (POST /api/ia/gasto/topes). Si la Console de Anthropic corta, «Reabrir» tras subir allí el límite (POST /api/ia/gasto/reabrir).
// Datos en vivo de la base de la app (ia_gasto.py: tablas ia_gasto, ia_topes, ia_lotes).

import { fmt, tile, tiles, panel, vacio, avisoParcial, avisoFlotante, icono, tablaApilable, chipEstado } from '../componentes.js';
import { h } from './personas_comun.js';

const eur = (n, dec = 2) => fmt.eur(n, dec);
const color = pct => (pct === null || pct === undefined ? '' : pct >= 100 ? 'rojo' : pct >= 80 ? 'ambar' : 'verde');
const hora = t => (t ? `${fmt.fecha(t.slice(0, 10))} ${t.slice(11, 16)}` : '—');

function cartel(D) {
  if (!D.llaves.principal) {
    return h('div', { class: 'aviso info', role: 'note', 'data-cartel': 'gasto-ia', style: { padding: '16px 20px', alignItems: 'center', gap: '16px' } },
      h('span', { class: 'ico', 'aria-hidden': 'true' }, icono('candado')),
      h('div', {},
        h('b', { style: { font: 'var(--t-h2)', display: 'block' } }, 'IA sin clave todavía · hoy no se gasta nada'),
        h('p', { style: { margin: '4px 0 0', font: 'var(--t-cuerpo)', maxWidth: '80ch' } },
          'La app va con lo precalculado y las reglas. Cuando crees los dos espacios en la Console con su límite de gasto y pegues las dos claves (bash fuentes_ia/pegar.sh), cada llamada saldrá aquí con su coste y con estos topes.')));
  }
  const reglas = D.modo === 'reglas';
  return h('div', { class: `aviso${reglas ? '' : ' info'}`, role: 'note', 'data-cartel': 'gasto-ia', style: { padding: '16px 20px', alignItems: 'center', gap: '16px' } },
    h('span', { class: 'ico', 'aria-hidden': 'true' }, icono(reglas ? 'alert' : 'escudo')),
    h('div', {},
      h('b', { style: { font: 'var(--t-h2)', display: 'block' } }, reglas ? 'IA en modo reglas · sin coste' : 'IA con tope duro'),
      h('p', { style: { margin: '4px 0 0', font: 'var(--t-cuerpo)', maxWidth: '80ch' } },
        reglas ? D.motivo
          : `Antes de cada llamada se reserva lo peor que puede costar; si no cabe en el tope, no sale. Al ${D.topes.aviso_pct} % te avisa en #avisos-dirección; al 100 % la app pasa sola a reglas y lo dice en pantalla. Encima, el límite de gasto de la Console de Anthropic corta de verdad aunque la app fallara.`)));
}

function resumen(D) {
  const g = D.gasto, t = D.topes;
  return tiles([
    tile({ icono: 'euro', etiqueta: 'Gastado este mes', valor: eur(g.mes), unidad: `de ${eur(t.mes_eur, 0)}`, estado: color(D.pct.mes),
      contexto: `${fmt.num(D.pct.mes ?? 0, 1)} % del tope${g.reservado ? ` · ${eur(g.reservado)} reservado en curso` : ''}` }),
    tile({ icono: 'clock', etiqueta: 'Gastado hoy', valor: eur(g.dia), unidad: `de ${eur(t.dia_eur, 0)}`, estado: color(D.pct.dia),
      contexto: `${fmt.num(D.pct.dia ?? 0, 1)} % del tope del día` }),
    tile({ icono: 'dir', etiqueta: 'Previsión a fin de mes', valor: eur(g.prevision_mes, 0), estado: color(t.mes_eur ? g.prevision_mes / t.mes_eur * 100 : null),
      contexto: `Al ritmo de lo que va de mes (${g.dias_mes} días). Nunca pasará de ${eur(t.mes_eur, 0)}` }),
    tile({ icono: 'key', etiqueta: 'Llaves', valor: D.llaves.principal ? 'Principal' : 'Sin clave', estado: D.llaves.principal ? 'verde' : 'gris',
      contexto: D.llaves.respaldo ? `Respaldo lista · ${eur(D.llaves.respaldo_mes_eur)} de ${eur(t.respaldo_mes_eur, 0)} este mes` : 'Sin llave de respaldo (la pega Tomás con pegar.sh)' }),
  ]);
}

function porFuncion(D) {
  return tablaApilable({
    filas: D.por_funcion, porPagina: 0,
    columnas: [
      { clave: 'nombre', titulo: 'Función', principal: true },
      { clave: 'modelo', titulo: 'Modelo' },
      { clave: 'llamadas', titulo: 'Llamadas', num: true, celda: x => fmt.num(x.llamadas) },
      { clave: 'eur', titulo: 'Gastado', num: true, celda: x => eur(x.eur) },
      { clave: 'tope_mes', titulo: 'Tope del mes', num: true, celda: x => h('span', {}, eur(x.tope_mes, 0), ' ',
        chipEstado(color(x.tope_mes ? x.eur / x.tope_mes * 100 : null) || 'gris', x.tope_mes ? `${fmt.num(x.eur / x.tope_mes * 100, 0)} %` : 'apagada')) },
    ],
  });
}

function porPersona(D) {
  return tablaApilable({
    filas: D.por_persona, porPagina: 0,
    vacio: { titulo: 'Nadie ha gastado este mes', porque: 'Todavía no ha salido ninguna llamada a la IA.', celebrar: true },
    columnas: [
      { clave: 'nombre', titulo: 'Persona', principal: true },
      { clave: 'llamadas', titulo: 'Llamadas', num: true, celda: x => fmt.num(x.llamadas) },
      { clave: 'eur_hoy', titulo: 'Hoy', num: true, celda: x => eur(x.eur_hoy) },
      { clave: 'eur_mes', titulo: 'Este mes', num: true, celda: x => eur(x.eur_mes) },
    ],
  });
}

function ultimas(D) {
  return tablaApilable({
    filas: D.ultimas, porPagina: 20,
    vacio: { titulo: 'Ninguna llamada todavía', porque: 'Cuando alguien pida un borrador, un copiloto o un consejo con IA, saldrá aquí con su coste.' },
    columnas: [
      { clave: 'creada', titulo: 'Cuándo', principal: true, celda: x => hora(x.creada) },
      { clave: 'quien', titulo: 'Quién' },
      { clave: 'tarea', titulo: 'Qué', celda: x => `${x.tarea}${x.objeto ? ` · ${x.objeto}` : ''}${x.lote ? ' · lote' : ''}${x.llave === 'respaldo' ? ' · respaldo' : ''}` },
      { clave: 'salida', titulo: 'Tokens entrada / salida', celda: x => h('span', { title: x.cache_leida ? `${fmt.num(x.cache_leida)} de la entrada salieron de la caché (al 10 %)` : null },
        `${fmt.num(x.entrada + x.cache_escrita + x.cache_leida)} / ${fmt.num(x.salida)}`) },
      { clave: 'eur', titulo: 'Coste', num: true, celda: x => eur(x.eur, 4) },
      { clave: 'ok', titulo: 'Estado', celda: x => (x.ok ? chipEstado('verde', 'Bien')
        : h('span', {}, chipEstado('rojo', 'Falló'), x.motivo ? h('small', { class: 'sub', style: { display: 'block', maxWidth: '32ch' } }, x.motivo.replace(/^(tope_console|caida|error|otro):\s*/, '')) : null)) },
    ],
  });
}

function campo(etq, valor, { min = 0, max = 2000, paso = 1, ayuda } = {}) {
  const i = h('input', { type: 'number', min: String(min), max: String(max), step: String(paso), value: String(valor), inputmode: 'decimal', 'aria-label': etq,
    style: { width: '112px', minHeight: '32px', padding: '4px 8px', border: '1px solid var(--line)', borderRadius: 'var(--r-s)', background: 'var(--card)' } });
  return { i, nodo: h('label', { class: 'pila', style: { gap: '4px' } }, h('span', { class: 'sub' }, etq), i, ayuda ? h('small', { class: 'sub' }, ayuda) : null) };
}

function formTopes(ctx, D, repintar) {
  const t = D.topes;
  const c = {
    mes_eur: campo('Tope del mes (€)', t.mes_eur, { max: 2000, ayuda: 'Por defecto 150 €' }),
    dia_eur: campo('Tope del día (€)', t.dia_eur, { max: 200, ayuda: 'Por defecto 10 €' }),
    aviso_pct: campo('Aviso a Tomás al (%)', t.aviso_pct, { min: 10, max: 99 }),
    persona_dia_eur: campo('Por persona y día (€)', t.persona_dia_eur, { max: 50, paso: 0.5, ayuda: 'Tomás, el doble' }),
    respaldo_mes_eur: campo('Llave de respaldo al mes (€)', t.respaldo_mes_eur, { max: 200 }),
  };
  const f = Object.fromEntries(Object.keys(t.funcion_mes_eur).map(k => [k, campo(`${(D.por_funcion.find(x => x.tarea === k) || {}).nombre || k} al mes (€)`, t.funcion_mes_eur[k])]));
  const activa = h('input', { type: 'checkbox', checked: t.activa !== false });
  const motivo = h('input', { type: 'text', maxlength: '300', placeholder: 'Por qué lo cambias (queda en el rastro)', 'aria-label': 'Motivo del cambio',
    style: { width: '100%', maxWidth: '480px', minHeight: '32px', padding: '4px 8px', border: '1px solid var(--line)', borderRadius: 'var(--r-s)', background: 'var(--card)' } });
  const estado = h('span', { class: 'sub', role: 'status' });
  const guardar = h('button', { type: 'button', class: 'bt pri', on: { click: async () => {
    const valores = Object.fromEntries(Object.entries(c).map(([k, x]) => [k, Number(x.i.value)]));
    valores.funcion_mes_eur = Object.fromEntries(Object.entries(f).map(([k, x]) => [k, Number(x.i.value)]));
    valores.activa = activa.checked;
    guardar.disabled = true; estado.textContent = 'Guardando…';
    try {
      const r = await ctx.api('ia/gasto/topes', { metodo: 'POST', cuerpo: { valores, motivo: motivo.value } });
      avisoFlotante(r.sin_cambios ? 'No había nada que cambiar' : 'Topes guardados (quedan en el rastro)');
      repintar();
    } catch (e) { estado.textContent = e.message; guardar.disabled = false; }
  } } }, icono('ok'), 'Guardar topes');
  return h('div', { class: 'pila', style: { padding: '16px var(--relleno)', gap: '16px' } },
    h('label', { class: 'fila', style: { gap: '8px', alignItems: 'center' } }, activa, h('span', {}, 'IA encendida (si la apagas, todo va por reglas, sin coste)')),
    h('div', { class: 'fila', style: { gap: '16px', flexWrap: 'wrap' } }, Object.values(c).map(x => x.nodo)),
    h('div', { class: 'fila', style: { gap: '16px', flexWrap: 'wrap' } }, Object.values(f).map(x => x.nodo)),
    motivo,
    h('div', { class: 'fila', style: { gap: '12px', alignItems: 'center', flexWrap: 'wrap' } }, guardar, estado));
}

function historial(D) {
  return tablaApilable({
    filas: D.historial_topes, porPagina: 10,
    vacio: { titulo: 'Sin cambios', porque: `Rigen los de por defecto: ${eur(D.topes.mes_eur, 0)} al mes y ${eur(D.topes.dia_eur, 0)} al día.` },
    columnas: [
      { clave: 'creada', titulo: 'Cuándo', principal: true, celda: x => hora(x.creada) },
      { clave: 'quien', titulo: 'Quién' },
      { clave: 'valores', titulo: 'Topes', celda: x => `${eur(x.valores.mes_eur, 0)}/mes · ${eur(x.valores.dia_eur, 0)}/día${x.valores.activa === false ? ' · IA apagada' : ''}` },
      { clave: 'motivo', titulo: 'Motivo', celda: x => x.motivo || '—' },
    ],
  });
}

function precios(D) {
  const P = D.precios;
  return h('div', { class: 'pila', style: { padding: '12px var(--relleno)', gap: '8px' } },
    tablaApilable({
      filas: Object.entries(P.modelos).map(([m, p]) => ({ m, ...p })), porPagina: 0,
      columnas: [
        { clave: 'm', titulo: 'Modelo', principal: true },
        { clave: 'entrada', titulo: 'Entrada', num: true, celda: x => `${fmt.num(x.entrada, 2)} $` },
        { clave: 'cache_leida', titulo: 'Caché leída', num: true, celda: x => `${fmt.num(x.cache_leida, 2)} $` },
        { clave: 'salida', titulo: 'Salida', num: true, celda: x => `${fmt.num(x.salida, 2)} $` },
      ],
    }),
    h('p', { class: 'sub', style: { margin: 0 } }, `Dólares por millón de tokens. En lote, la mitad. Cambio usado: 1 $ = ${fmt.num(D.topes.usd_a_eur, 2)} € (prudente). `,
      h('a', { href: P.fuente, target: '_blank', rel: 'noopener' }, `Ver fuente ↗ (${P.fecha})`)));
}

async function cargar(ctx) {
  try { return await ctx.api('ia/gasto'); } catch (e) { return { error: e.message, status: e.status }; }
}

// La respuesta de Reabrir acredita un registro local, no un cambio en la Console.
function ambitoReabrir601(ctx) {
  if (ctx.vigente?.() !== true || ctx.real?.id !== 'tomas' || ctx.persona?.id !== 'tomas' || ctx.veModulo?.('gasto-ia') !== true) return null;
  const filas = ctx.datos?.personas;
  if (!Array.isArray(filas)) return null;
  const encontrados = filas.filter(p => p?.id === 'tomas');
  if (encontrados.length !== 1) return null;
  const p = encontrados[0], roles = p.puestos;
  if (p.estado !== 'activo' || p.activo === false || !Array.isArray(roles) || !roles.includes('direccion') ||
      roles.some(r => typeof r !== 'string' || !/^[a-z][a-z0-9_-]{0,99}$/.test(r)) || new Set(roles).size !== roles.length) return null;
  const canon = JSON.stringify([...roles].sort());
  if ([ctx.real, ctx.persona].some(x => !Array.isArray(x.puestos) || JSON.stringify([...x.puestos].sort()) !== canon || x.estado !== 'activo' || x.activo === false)) return null;
  return JSON.stringify([p.id, canon, !!ctx.soloLectura, !!ctx.pilotoLectura]);
}

function respuestaReabrir601(r) {
  return !!r && r.ok === true && !r.error && ['ia', 'reglas'].includes(r.modo) &&
    (r.motivo === null || typeof r.motivo === 'string') && r.topes && typeof r.topes === 'object' && !Array.isArray(r.topes) &&
    r.gasto && typeof r.gasto === 'object' && r.llaves && typeof r.llaves === 'object';
}

function controlReabrir601(ctx, raiz, firma, pintar) {
  const estado = h('span', { class: 'sub', role: 'status', 'aria-live': 'polite' });
  let ocupado = false;
  const valido = () => {
    if (ambitoReabrir601(ctx) === firma && !ctx.soloLectura && !ctx.pilotoLectura) return true;
    raiz.replaceChildren();
    return false;
  };
  const boton = h('button', { type: 'button', class: 'bt', disabled: !!ctx.soloLectura || !!ctx.pilotoLectura, on: { click: async () => {
    if (ocupado || !valido()) return;
    ocupado = true; boton.disabled = true; estado.textContent = 'Registrando reapertura…';
    try {
      const r = await ctx.api('ia/gasto/reabrir', { metodo: 'POST', cuerpo: { motivo: 'Límite de la Console subido' } });
      if (!valido()) return;
      if (!respuestaReabrir601(r)) throw new Error('No se confirmó el registro de reapertura. Actualiza el gasto para comprobarlo antes de repetir.');
      // No se deduce actividad del proveedor del ok de una escritura local.
      const texto = r.modo === 'reglas' ? 'Reapertura registrada en la app. La IA sigue en modo reglas.' : 'Reapertura registrada en la app. El límite externo no se ha comprobado aquí.';
      await pintar(texto);
    } catch (e) {
      if (!valido()) return;
      if (e?.status === 401 || e?.status === 403) {
        raiz.replaceChildren(vacio({ icono: 'candado', tono: 'aviso', titulo: 'No se permite reabrir la IA en esta vista', texto: 'Actualiza la vista para comprobar el acceso.' }));
        return;
      }
      estado.textContent = `No se confirmó la reapertura. ${e?.message || 'Actualiza el gasto para comprobar el estado.'}`;
      // Un error de transporte puede ocultar un registro aceptado: sin reenvío automático.
    }
  } } }, icono('recargar'), 'Reabrir (ya he subido el límite en la Console)');
  return h('div', { class: 'fila', style: { gap: '12px', flexWrap: 'wrap' } }, boton, estado);
}

export default {
  id: 'gasto-ia',
  titulo: 'Gasto de IA',
  grupo: 'Sistema',
  puestos_que_lo_ven: { direccion: 'todo' },
  async render(cont, ctx) {
    ctx.titulo?.('Gasto de IA', 'Lo que gasta la IA de la app, con tope duro: mes, día, previsión, por función y por persona');
    const raiz = h('div', { class: 'gasto-ia pila' });
    cont.append(raiz);
    const firma = ambitoReabrir601(ctx);
    let lectura = 0;
    const vigente = () => firma !== null && ambitoReabrir601(ctx) === firma;
    const pintar = async (confirmacion = '') => {
      if (!vigente()) { raiz.replaceChildren(); return; }
      const turno = ++lectura;
      const D = await cargar(ctx);
      if (!vigente()) { raiz.replaceChildren(); return; }
      if (turno !== lectura) return;
      if (D.error) {
        raiz.replaceChildren(vacio({ icono: 'candado', tono: 'aviso', titulo: D.status === 403 ? 'Solo lo ve Tomás' : 'No se pudo leer el gasto de la IA', texto: D.error }));
        return;
      }
      raiz.replaceChildren(...[
        confirmacion ? h('p', { class: 'sub', role: 'status' }, confirmacion) : null,
        cartel(D),
        resumen(D),
        D.motivo && /Console/.test(D.motivo) ? controlReabrir601(ctx, raiz, firma, pintar) : null,
        panel({ titulo: 'Por función', icono: 'spark', sub: 'Modelo barato para clasificar y consejos; el mejor solo para borradores. Cada función tiene su tope del mes.' }, porFuncion(D)),
        panel({ titulo: 'Por persona', icono: 'eq', sub: `Tope por persona: ${eur(D.topes.persona_dia_eur)} al día (Tomás, el doble). «Tubería» = lotes de noche.` }, porPersona(D)),
        panel({ titulo: 'Topes', icono: 'escudo', sub: 'Solo tú los cambias. Cada cambio queda en el rastro con el antes, el después y el motivo.' }, formTopes(ctx, D, pintar)),
        panel({ titulo: 'Últimas llamadas', icono: 'hist', sub: 'Sin contenido: quién, qué, tokens y coste real. Las que fallaron no cobran salida.',
          acciones: h('button', { type: 'button', class: 'bt mini', on: { click: () => pintar() } }, icono('recargar'), 'Actualizar') }, ultimas(D)),
        panel({ titulo: 'Cambios de topes', icono: 'clock' }, historial(D)),
        panel({ titulo: 'Precios que usa la cuenta', icono: 'euro' }, precios(D)),
      ].filter(Boolean));
    };
    await pintar();
  },
};
