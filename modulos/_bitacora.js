// modulos/_bitacora.js · Ronda U · U3 (3-oct, cambio #11 del 50): la bitácora diaria del trafficker («qué cambio hoy»),
// para leerla fuera de Captación (ficha del cliente, informes). Se escribe en Captación (acción interna bitacora_cuenta,
// herramienta app, con rastro); aquí solo se lee, con las mismas reglas del servidor (/api/acciones?modulo=captacion:
// solo filas de clientes que la persona puede abrir).
//
//   bitacoraCuenta(ctx, clienteId, { dias = 14 }) → [{ dia, hora, texto, quien }] (más nuevo primero; [] sin servidor)
//   panelBitacora(ctx, clienteId, { dias, titulo }) → <section class="panel"> con la lista, o un vacío en una línea

import { h, panel, listaConIcono, vacioLinea, hoyMadrid, sumarDias, fechaCorta } from '../componentes.js';

/** La hora de la cola de acciones viene en UTC («2026-10-03 03:36:12»): día y hora en Madrid. */
const madridDe = t => {
  const s = String(t || '');
  const d = new Date(s.replace(' ', 'T') + (/[zZ]$|[+-]\d\d:?\d\d$/.test(s) ? '' : 'Z'));
  if (!s || Number.isNaN(+d)) return { dia: s.slice(0, 10), hora: s.slice(11, 16) };
  const p = Object.fromEntries(new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Madrid', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
    .formatToParts(d).map(x => [x.type, x.value]));
  return { dia: `${p.year}-${p.month}-${p.day}`, hora: `${p.hour}:${p.minute}` };
};

export async function bitacoraCuenta(ctx, clienteId, { dias = 14 } = {}) {
  if (!(ctx?.servidor && ctx.api) || !clienteId) return [];
  try {
    const r = await ctx.api('acciones?modulo=captacion');
    const desde = sumarDias(ctx.hoy || hoyMadrid(), -dias);
    return (r.acciones || []).filter(a => a.tipo === 'bitacora_cuenta' && a.cliente_id === clienteId && madridDe(a.creada).dia >= desde)
      .sort((x, y) => String(y.creada).localeCompare(String(x.creada)))
      .map(a => ({ ...madridDe(a.creada), texto: a.texto, quien: a.quien }));
  } catch { return []; }
}

export async function panelBitacora(ctx, clienteId, { dias = 14, titulo = 'Publicidad · qué se cambió' } = {}) {
  const l = await bitacoraCuenta(ctx, clienteId, { dias });
  return panel({ titulo, icono: 'editar', sub: `Bitácora del trafficker, últimos ${dias} días. Se apunta en Captación.` },
    h('div', { class: 'cuerpo' }, l.length
      ? listaConIcono(l.slice(0, 8).map(a => ({ icono: 'editar', texto: a.texto, extra: `${ctx.fechas?.esHoy?.(a.dia) ? 'hoy' : fechaCorta(a.dia)} ${a.hora} · ${ctx.nombre ? ctx.nombre(a.quien) : a.quien}` })))
      : vacioLinea('Nada apuntado en la bitácora de publicidad en estos días.', { icono: 'editar' })));
}
