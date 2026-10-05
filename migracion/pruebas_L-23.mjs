#!/usr/bin/env node
// migracion/pruebas_L-23.mjs · L-23: «Avisar al equipo» está activo en la ficha de un cliente que tiene equipo.
// Uso: node migracion/pruebas_L-23.mjs --base http://127.0.0.1:8771
// Para cada account con cartera (hasta 3) y hasta 3 clientes SUYOS con equipo (otra persona activa en alguna silla,
// de `GET /api/sesion › datos.clientes[].equipo`): abre la ficha y exige un botón `[data-avisar]` y ningún
// «Avisar al equipo» apagado (`[aria-disabled=true]`). Control: un cliente suyo SIN equipo → apagado.
// Solo lectura. Solo se cuentan botones; ningún dato real va al repo ni a la salida.
import { chromium } from '../v2/tools/capturas/node_modules/playwright/index.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, v) => (x.startsWith('--') ? [...a, [x.slice(2), v[i + 1]?.startsWith('--') || v[i + 1] === undefined ? true : v[i + 1]]] : a), []));
const base = String(args.base || 'http://127.0.0.1:8771').replace(/\/$/, '');
const pedir = async (ruta, yo) => (await fetch(`${base}${ruta}`, { headers: { 'X-RO-App': '1', 'X-RO-Yo': yo, Accept: 'application/json' } })).json();
const elegir = await (await fetch(`${base}/api/elegir`)).json();
const personas = (elegir.personas || []).filter((p) => (p.estado || 'activo') === 'activo');
const fallos = [];
let comprobados = 0;
const ok = (c, t) => { comprobados++; if (!c) fallos.push(t); };

const cuentas = [];
for (const p of personas) {
  if (!(p.puestos || []).includes('account') || (p.puestos || []).includes('direccion')) continue;
  const s = await pedir('/api/sesion', p.id);
  const cart = new Set(s.datos?.carteraIds || []);
  const propios = (s.datos?.clientes || []).filter((c) => cart.has(c.id));
  const tieneEquipo = (c) => Object.values(c.equipo || {}).some((l) => Array.isArray(l) && l.some((x) => x?.persona_id && x.persona_id !== p.id && personas.some((q) => q.id === x.persona_id)));
  const con = propios.filter(tieneEquipo).slice(0, 3).map((c) => c.id);
  const sin = propios.filter((c) => !tieneEquipo(c)).slice(0, 1).map((c) => c.id);
  if (con.length) cuentas.push({ id: p.id, con, sin });
  if (cuentas.length >= 3) break;
}
ok(cuentas.length > 0, 'ningún account tiene un cliente suyo con equipo: el botón no se puede encender (hallazgo)');

const navegador = await chromium.launch();
async function mirar(persona, cliente) {
  const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 }, locale: 'es-ES', timezoneId: 'Europe/Madrid', reducedMotion: 'reduce' });
  await ctx.clock.setFixedTime(new Date('2026-10-05T07:30:00+02:00'));
  const pagina = await ctx.newPage();
  try {
    await pagina.goto(`${base}/?yo=${persona}&hoy=2026-10-05#/ficha/${cliente}/resumen`, { waitUntil: 'load', timeout: 45_000 });
    await pagina.waitForFunction(() => /Avisar a/.test(document.body.innerText), null, { timeout: 25_000 }).catch(() => {});
    await pagina.waitForTimeout(1500);
    return await pagina.evaluate(() => ({
      activos: document.querySelectorAll('button[data-avisar]').length,
      apagados: [...document.querySelectorAll('[aria-disabled="true"]')].filter((e) => /Avisar al equipo/.test(e.innerText || '')).length,
    }));
  } finally { await ctx.close(); }
}
try {
  for (const c of cuentas) {
    for (const cli of c.con) {
      const r = await mirar(c.id, cli);
      ok(r.activos === 1 && r.apagados === 0, `${c.id}: ficha con equipo → botones activos ${r.activos}, apagados ${r.apagados} (debe ser 1 y 0)`);
    }
    for (const cli of c.sin) {
      const r = await mirar(c.id, cli);
      ok(r.activos === 0 && r.apagados === 1, `${c.id}: ficha sin equipo → activos ${r.activos}, apagados ${r.apagados} (debe ser 0 y 1)`);
    }
  }
} finally { await navegador.close(); }
console.log(`${fallos.length ? '✘' : '✔'} L-23: ${comprobados} comprobaciones${fallos.length ? ' · ' + fallos.join(' · ') : ''}`);
process.exit(fallos.length ? 1 : 0);
