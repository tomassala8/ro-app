// modulos/_gbp_bloques.js · Ficha de Google (Google Business Profile) en la app (3-oct-2026). No es un módulo: lo común que
// usan la ficha del cliente (pestaña «Web y SEO») y «SEO, ficha y webs» (pestaña «Ficha de Google» y detalle del cliente).
// Se deja aparte porque ficha.js y seo.js los estaba editando otro carril: las dos líneas de enganche están en
// ../57_GOOGLE_BUSINESS_PROFILE.md (sección «Enganche»).
//
// Datos (solo lectura): ctx.datosModulo('gbp/gbp') ← fuentes_gbp/generar_gbp.py. Filas con cliente_id: el servidor solo
// manda los clientes que la persona abre; «sin_cliente» y las alertas sin cliente, solo con nivel «todo».
// Mientras Google no apruebe el acceso: _meta.estado = 'pendiente_aprobacion' → «Pendiente de aprobación de Google · lo
// hace Tomás: …» con los pasos (enlazados) solo para dirección; al resto, la frase y quién lo hace.
// Acciones: «Proponer respuesta» (POST /api/gbp/borrador: cerebro de reseñas, IA si hay clave; si no, por reglas) y
// «Guardar respuesta» (POST /api/gbp/responder: cola de acciones en SIMULACIÓN; el canal de Google está apagado).
//
//   cargarGbp(ctx)                         → doc de gbp/gbp (o { _meta: { estado: 'pendiente_aprobacion' } })
//   bloqueFichaGoogle(ctx, clienteId)      → <section> «Ficha de Google» de un cliente (se rellena sola): ficha del
//                                            cliente › Web y SEO, y SEO › detalle del cliente
//   pestanaFichaGoogle(z, ctx)             → pinta la pestaña «Ficha de Google» de SEO (todas las fichas que ve la persona)
//   tarjetaResena(ctx, r, { clienteId, cliente, modulo })  → una reseña con «Proponer respuesta»
//
// Diseño: solo componentes y clases comunes (panel, cuerpo, tiles, primero, ia-calidad, campo, bt, chip, sub) y tokens.

import { h, fmt, tile, tiles, panel, vacio, vacioLinea, chipEstado, icono, avisoFlotante, enlaceFuente, tablaApilable, botonConfirmar } from '../componentes.js';

const MES3 = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const fDia = iso => { if (!iso) return '—'; const d = new Date(String(iso).length <= 10 ? `${iso}T12:00:00` : iso); return Number.isNaN(+d) ? '—' : `${d.getDate()}-${MES3[d.getMonth()]}`; };
const estrellas = n => (n ? '★'.repeat(n) + '☆'.repeat(5 - n) : 'sin estrellas');
const hace = horas => (horas === null || horas === undefined ? '' : horas < 48 ? `hace ${Math.round(horas)} h` : `hace ${Math.round(horas / 24)} días`);
const pl = (n, uno, varios) => `${fmt.num(n)} ${n === 1 ? uno : (varios || uno + 's')}`;
const TONO = { rojo: 'rojo', ambar: 'ambar', verde: 'verde' };
const TXT_EST = { rojo: 'Actuar', ambar: 'Vigilar', verde: 'Bien', gris: 'Sin dato' };
export const MODULO_PANTALLA = { 'seo-web': 'seo-web', ficha: 'ficha' };

// =================================================================== datos
export async function cargarGbp(ctx) {
  try { return await ctx.datosModulo('gbp/gbp'); } catch (e) { return { _meta: { estado: 'sin_datos', texto: e.message }, clientes: [], alertas: [] }; }
}
const conectado = d => ['conectado', 'simulado'].includes(d?._meta?.estado);
const esDireccion = ctx => (ctx.puestos || []).some(p => p.id === 'direccion') || (ctx.persona?.puestos || []).includes('direccion');
const puedeResponder = (ctx, cid) => { try { return !!ctx.ver?.({ tipo: 'gbp_responder', cliente_id: cid })?.ok; } catch { return false; } };

// =================================================================== sin acceso: pendiente de aprobación
function avisoPendiente(ctx, meta = {}) {
  const titular = meta.titular || 'Pendiente de aprobación de Google';
  const texto = meta.texto || `${titular} · lo hace Tomás: pedir el acceso a la API de Google Business Profile y, cuando lo aprueben, conectar la cuenta.`;
  if (!esDireccion(ctx)) {
    return vacioLinea(`${texto.split(' · ')[0]}. Cuando Google lo apruebe saldrán aquí las reseñas por responder, las llamadas, las rutas y los clics de la ficha.`,
      { icono: 'clock', quien: 'Tomás' });
  }
  const pasos = (meta.pasos || []).map((p, i) => h('li', { class: 'gris' }, h('span', { class: 'num' }, String(i + 1)),
    h('div', {}, h('div', { class: 'mot' }, p.texto), p.enlace ? h('div', { class: 'det' }, enlaceFuente(p.enlace, 'Google')) : null)));
  const cuenta = meta.cuenta_que_gestiona;
  return h('div', { class: 'cuerpo' },
    vacioLinea(texto, { icono: 'clock', quien: 'Tomás' }),
    pasos.length ? h('ol', { class: 'primero', 'aria-label': 'Pasos para pedir el acceso' }, pasos) : null,
    cuenta ? h('details', { class: 'que-es' }, h('summary', {}, '¿Qué cuenta gestiona hoy las fichas?'),
      h('p', { class: 'sub' }, `Probable: ${cuenta.probable}.`), h('ul', {}, (cuenta.pistas || []).map(x => h('li', { class: 'sub' }, x))),
      h('p', { class: 'sub' }, cuenta.como_confirmar)) : null);
}

// =================================================================== reseña con «Proponer respuesta»
export function tarjetaResena(ctx, r, { clienteId, cliente, modulo = 'seo-web' } = {}) {
  const grave = r.alerta || (!r.respondida && r.estrellas && r.estrellas <= 3 ? 'ambar' : null);
  const li = h('li', { class: grave === 'rojo' ? '' : grave === 'ambar' ? 'ambar' : 'gris' });
  const zona = h('div', { class: 'gbp-borrador' });
  const puede = puedeResponder(ctx, clienteId);
  const proponer = h('button', { type: 'button', class: 'bt mini', disabled: !puede || null,
    title: puede ? 'Borrador con el cerebro de reseñas (no publica nada)' : 'Proponen respuesta SEO/ficha de Google, el account del cliente, el jefe de SEO, operaciones y dirección',
    on: { click: () => pedirBorrador(ctx, r, { zona, clienteId, modulo, boton: proponer }) } }, icono('spark', { clase: 's' }), 'Proponer respuesta');
  li.append(
    h('span', { class: 'num', title: `${r.estrellas || '?'} de 5 estrellas` }, String(r.estrellas || '?')),
    h('div', {},
      h('div', { class: 'mot' }, `${estrellas(r.estrellas)} · ${r.autor || 'Sin nombre'}`, cliente ? h('span', { class: 'sub' }, ` · ${cliente}`) : null),
      h('div', { class: 'det' }, r.texto ? `«${r.texto}»` : 'Sin texto (solo estrellas).'),
      h('div', { class: 'det' }, `${fDia(r.fecha)}${r.respondida ? ` · respondida el ${fDia(r.respuesta?.fecha)}` : ` · sin responder ${hace(r.horas_sin_responder)}`}`),
      r.respondida && r.respuesta?.texto ? h('div', { class: 'det' }, `Respuesta del despacho: «${r.respuesta.texto}»`) : null,
      zona),
    r.respondida ? chipEstado('verde', 'Respondida') : proponer);
  return li;
}

async function pedirBorrador(ctx, r, { zona, clienteId, modulo, boton }) {
  boton.disabled = true;
  zona.replaceChildren(vacioLinea('Pidiendo el borrador…', { icono: 'spark' }));
  let b;
  try {
    b = await ctx.api('gbp/borrador', { metodo: 'POST', cuerpo: { resena_id: r.id } });
  } catch (e) {
    zona.replaceChildren(vacioLinea(`No se ha podido pedir: ${e.message}`, { icono: 'alert' }));
    boton.disabled = false;
    return;
  }
  const ta = h('textarea', { rows: '6', 'aria-label': 'Respuesta a la reseña' });
  ta.value = b.texto || '';
  const c = b.calidad || {};
  const tono = c.nivel === 'lista' ? 'verde' : c.nivel === 'revisar' ? 'ambar' : 'rojo';
  const faltas = [...(c.bloqueos || []), ...(c.faltas || [])];
  const nota = h('div', { class: 'ia-calidad', role: 'note' },
    h('p', { class: 'ia-sub' }, chipEstado(tono, `Calidad ${c.nota ?? '—'}/100${(c.huecos || []).length ? ` · ${pl(c.huecos.length, 'hueco')} por completar` : ''}`), ' ',
      b.origen === 'ia' ? 'Redactado con IA. ' : 'Redactado por reglas (sin IA). ', b.recomendacion || ''),
    faltas.length ? h('details', {}, h('summary', { class: 'ia-sub' }, `Lo que falta (${faltas.length})`), h('ul', { class: 'ia-lista' }, faltas.map(f => h('li', {}, f)))) : null);
  const guardar = botonConfirmar({
    texto: 'Guardar respuesta', pregunta: 'Queda en la cola en simulación: NO se publica en Google. ¿Guardar?', confirmar: 'Guardar',
    soloLectura: ctx.soloLectura,
    alConfirmar: async () => {
      const x = await ctx.api('gbp/responder', { metodo: 'POST', cuerpo: { resena_id: r.id, texto: ta.value, modulo } });
      avisoFlotante('Guardada en la app · sin publicar en Google');
      ctx.rastro?.({ accion: 'evento', objeto: r.id, detalle: 'gbp_respuesta_guardada' });
      return x.texto || 'Guardada (simulada)';
    },
  });
  const copiar = h('button', { type: 'button', class: 'bt mini', on: { click: async () => {
    try { await navigator.clipboard.writeText(ta.value); avisoFlotante('Respuesta copiada'); } catch { avisoFlotante('No se ha podido copiar', { icono: 'alert' }); }
  } } }, icono('copy', { clase: 's' }), 'Copiar');
  zona.replaceChildren(h('div', { class: 'campo' }, ta), nota,
    h('p', { class: 'sub' }, b.aviso || 'Borrador: revísalo con el account y completa los huecos.'),
    h('div', { class: 'acciones' }, guardar, copiar,
      h('a', { class: 'bt mini', href: 'https://business.google.com/reviews', target: '_blank', rel: 'noopener noreferrer' }, icono('ext', { clase: 's' }), 'Abrir en Google')));
  boton.disabled = false;
}

// =================================================================== bloques
function tilesFicha(f) {
  const s = f.rendimiento?.semana || {}, a = f.rendimiento?.semana_anterior || {}, v = f.rendimiento?.variacion_pct || {};
  const comp = k => (v[k] === null || v[k] === undefined ? { texto: 'sin semana anterior' } : { delta: v[k], pct: true, texto: 'frente a la semana anterior' });
  const est = k => (k === 'llamadas' || k === 'rutas') && a[k] >= 8 && v[k] !== null && v[k] <= -30 ? (v[k] <= -60 ? 'rojo' : 'ambar') : '';
  const rs = f.resenas || {};
  return tiles([
    tile({ icono: 'star', etiqueta: 'Valoración', valor: rs.media ? fmt.num(rs.media, 1) : null, unidad: rs.total ? ` · ${pl(rs.total, 'reseña')}` : '',
      estado: rs.media && rs.media < 4 ? 'ambar' : '', contexto: 'Media de Google' }),
    tile({ icono: 'opinion', etiqueta: 'Por responder', valor: rs.sin_responder ?? null, estado: rs.malas_sin_responder ? 'rojo' : rs.sin_responder ? 'ambar' : 'verde',
      contexto: rs.malas_sin_responder ? `${pl(rs.malas_sin_responder, 'mala', 'malas')} (1-3★)` : 'Reseñas sin respuesta' }),
    tile({ icono: 'phone', etiqueta: 'Llamadas', valor: s.llamadas ?? null, estado: est('llamadas'), comparacion: comp('llamadas'), contexto: 'Botón «Llamar» de la ficha, 7 días' }),
    tile({ icono: 'pin', etiqueta: 'Rutas', valor: s.rutas ?? null, estado: est('rutas'), comparacion: comp('rutas'), contexto: 'Cómo llegar, 7 días' }),
    tile({ icono: 'mundo_web', etiqueta: 'Clics a la web', valor: s.clics_web ?? null, comparacion: comp('clics_web'), contexto: '7 días' }),
    tile({ icono: 'ojo', etiqueta: 'Vistas', valor: s.vistas ?? null, comparacion: comp('vistas'), contexto: `Búsqueda ${fmt.num(s.vistas_busqueda || 0)} · Maps ${fmt.num(s.vistas_maps || 0)}` }),
  ]);
}

function cuerpoFicha(ctx, f, { clienteId, cliente, modulo }) {
  const malos = (f.motivos || []).filter(m => !/^Todo en orden/.test(m));
  const porResp = f.resenas?.por_responder || [];
  return h('div', { class: 'cuerpo' },
    h('p', { class: 'sub' }, chipEstado(TONO[f.estado] || 'gris', TXT_EST[f.estado] || 'Sin dato'), ` ${f.nombre}${f.localidad ? ` · ${f.localidad}` : ''}`,
      f.confianza === 'media' ? ' · emparejada por nombre (revisar)' : '', f.maps ? ' · ' : '', f.maps ? enlaceFuente(f.maps, 'Maps') : null),
    malos.length ? h('ul', { class: 'primero' }, malos.map(m => h('li', { class: /suspendida|deshabilitada|1-3★/.test(m) ? '' : 'ambar' },
      h('span', { class: 'num' }, icono('alert', { clase: 's' })), h('div', {}, h('div', { class: 'mot' }, m))))) : null,
    tilesFicha(f),
    f.rendimiento?.nota ? h('p', { class: 'sub' }, `${f.rendimiento.nota} Semana: ${fDia(f.rendimiento.semana?.desde)} a ${fDia(f.rendimiento.semana?.hasta)}.`) : null,
    porResp.length ? h('section', {}, h('h3', {}, `Reseñas por responder (${porResp.length})`),
      h('ul', { class: 'primero' }, porResp.slice(0, 10).map(r => tarjetaResena(ctx, r, { clienteId, cliente, modulo }))))
      : vacioLinea('Ninguna reseña sin responder.', { icono: 'ok' }),
    (f.busquedas?.terminos || []).length ? h('details', { class: 'que-es' }, h('summary', {}, `Cómo la buscan (${f.busquedas.mes || 'último mes'})`),
      h('ul', {}, f.busquedas.terminos.slice(0, 10).map(t => h('li', { class: 'sub' }, `${t.termino}: ${t.veces !== null && t.veces !== undefined ? fmt.num(t.veces) : `menos de ${t.menos_de}`}`)))) : null);
}

/** «Ficha de Google» de un cliente (ficha del cliente › Web y SEO; SEO › detalle). Se rellena sola. */
export function bloqueFichaGoogle(ctx, clienteId, { modulo = 'ficha' } = {}) {
  const cuerpo = h('div', {}, vacioLinea('Cargando la ficha de Google…', { icono: 'pin' }));
  const sec = panel({ titulo: 'Ficha de Google', icono: 'pin', sub: 'Reseñas, llamadas, rutas y clics de su ficha de Google Business Profile (solo lectura).' }, cuerpo);
  (async () => {
    const d = await cargarGbp(ctx);
    if (!conectado(d)) { cuerpo.replaceChildren(avisoPendiente(ctx, d._meta)); return; }
    const c = (d.clientes || []).find(x => x.cliente_id === clienteId);
    if (!c) {
      cuerpo.replaceChildren(vacioLinea('No hay ninguna ficha de Google emparejada con este cliente (por nombre, web o teléfono).',
        { icono: 'pin', quien: 'Jerónimo', que_hacer: 'si tiene ficha, añadirla en fuentes_gbp/emparejar.json o dar acceso a la cuenta que gestiona las fichas' }));
      return;
    }
    const frag = h('div', {}, d._meta.estado === 'simulado' ? vacioLinea('Datos inventados de prueba.', { icono: 'info' }) : null,
      ...c.fichas.map(f => cuerpoFicha(ctx, f, { clienteId, cliente: null, modulo })),
      h('p', { class: 'sub' }, `Google Business Profile · leído ${d._meta.leido || d._meta.generado || '—'}${d._meta.dato_viejo ? ' · dato de la última lectura buena' : ''}`));
    cuerpo.replaceChildren(frag);
  })();
  return sec;
}

/** Pestaña «Ficha de Google» de SEO, ficha y webs: lo de todas las fichas que ve la persona. */
export async function pestanaFichaGoogle(z, ctx) {
  z.replaceChildren(vacioLinea('Cargando las fichas de Google…', { icono: 'pin' }));
  const d = await cargarGbp(ctx);
  if (!conectado(d)) {
    z.replaceChildren(panel({ titulo: 'Ficha de Google', icono: 'pin', sub: 'Reseñas, llamadas, rutas y clics de la ficha de Google de cada cliente.' }, avisoPendiente(ctx, d._meta)));
    return;
  }
  const cl = d.clientes || [];
  const resenas = cl.flatMap(c => c.fichas.flatMap(f => (f.resenas?.por_responder || []).map(r => ({ r, c }))))
    .sort((a, b) => (a.r.estrellas || 5) - (b.r.estrellas || 5) || (b.r.horas_sin_responder || 0) - (a.r.horas_sin_responder || 0));
  const filas = cl.map(c => {
    const f = c.fichas[0] || {}; const s = f.rendimiento?.semana || {}; const v = f.rendimiento?.variacion_pct || {};
    return { id: c.cliente_id, cliente: c.cliente, estado: c.estado, media: f.resenas?.media, por: c.resenas_por_responder, malas: c.resenas_malas_sin_responder,
      llamadas: s.llamadas, v_llam: v.llamadas, rutas: s.rutas, v_rut: v.rutas, motivo: (c.motivos || [])[0] };
  });
  const varTxt = x => (x === null || x === undefined ? '' : ` (${x > 0 ? '+' : ''}${x} %)`);
  z.replaceChildren(
    d._meta.estado === 'simulado' ? vacioLinea('Datos inventados de prueba.', { icono: 'info' }) : null,
    panel({ titulo: `Reseñas por responder (${resenas.length})`, icono: 'opinion', sub: 'Las malas (1-3★) y las más antiguas, primero. «Proponer respuesta» no publica nada.' },
      resenas.length ? h('ul', { class: 'primero' }, resenas.slice(0, 40).map(({ r, c }) => tarjetaResena(ctx, r, { clienteId: c.cliente_id, cliente: c.cliente, modulo: 'seo-web' })))
        : h('div', { class: 'cuerpo' }, vacioLinea('Todas las reseñas están respondidas.', { icono: 'ok' }))),
    panel({ titulo: 'Fichas por cliente', icono: 'pin', sub: 'Semana de los últimos 7 días con dato frente a la anterior (Google da el dato con unos días de retraso).' },
      tablaApilable({ columnas: [
        { titulo: 'Cliente', principal: true, celda: x => h('a', { href: `#/seo-web/${x.id}` }, x.cliente) },
        { titulo: 'Estado', celda: x => chipEstado(TONO[x.estado] || 'gris', TXT_EST[x.estado] || 'Sin dato') },
        { titulo: 'Valoración', num: true, celda: x => (x.media ? fmt.num(x.media, 1) : '—') },
        { titulo: 'Por responder', num: true, celda: x => `${x.por ?? 0}${x.malas ? ` (${x.malas} malas)` : ''}` },
        { titulo: 'Llamadas', num: true, celda: x => `${x.llamadas ?? '—'}${varTxt(x.v_llam)}` },
        { titulo: 'Rutas', num: true, celda: x => `${x.rutas ?? '—'}${varTxt(x.v_rut)}` },
        { titulo: 'Lo primero', celda: x => x.motivo || '' },
      ], filas, vacio: { titulo: 'Ninguna ficha de tus clientes', texto: 'No hay fichas de Google emparejadas con los clientes que llevas.' } })),
    (d.sin_cliente || []).length ? panel({ titulo: `Fichas sin cliente (${d.sin_cliente.length})`, icono: 'alert', sub: 'Fichas que ve la cuenta y no casan con ningún cliente por nombre, web ni teléfono.' },
      h('ul', { class: 'primero' }, d.sin_cliente.map(f => h('li', { class: 'gris' }, h('span', { class: 'num' }, icono('pin', { clase: 's' })),
        h('div', {}, h('div', { class: 'mot' }, f.nombre), h('div', { class: 'det' }, `${f.web || 'sin web'} · ${f.como_emparejar}`)))))) : null,
    h('p', { class: 'sub' }, `Google Business Profile · leído ${d._meta.leido || d._meta.generado || '—'} · ${pl((d.clientes_sin_ficha || []).length, 'cliente')} sin ficha emparejada.`));
}
