#!/usr/bin/env node
// migracion/pruebas_L-42.mjs · L-42: el Asistente IA no dice «40 correos» ni «del 2-oct» fijos.
// Uso: node migracion/pruebas_L-42.mjs --base http://127.0.0.1:8771 [--volcar]
// (1) Sin tocar nada: el número de borradores del texto es el de los que pinta la pantalla (los de clientes que la persona puede abrir) y no pasa de los de `/api/ia/lista`.
// (2) Con `page.route` devolviendo `borradores: []` y `generado: '2026-10-05 06:00'`: no sale «40 correos», «40 borradores» ni «2-oct»;
//     sí «0 borradores» y «5-oct». Solo lectura. Solo recuentos en la salida.
import { chromium } from '../v2/tools/capturas/node_modules/playwright/index.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, v) => (x.startsWith('--') ? [...a, [x.slice(2), v[i + 1]?.startsWith('--') || v[i + 1] === undefined ? true : v[i + 1]]] : a), []));
const base = String(args.base || 'http://127.0.0.1:8771').replace(/\/$/, '');
const fallos = [];
let n = 0;
const ok = (c, t) => { n++; if (!c) fallos.push(t); };

const elegir = await (await fetch(`${base}/api/elegir`)).json();
const dir = (elegir.personas || []).find((p) => (p.estado || 'activo') === 'activo' && (p.puestos || []).includes('direccion'));
ok(!!dir, 'falta una persona de dirección');

const navegador = await chromium.launch();
async function abrir(inyectar) {
  const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 }, locale: 'es-ES', timezoneId: 'Europe/Madrid', reducedMotion: 'reduce' });
  await ctx.clock.setFixedTime(new Date('2026-10-05T07:30:00+02:00'));
  let real = null;
  if (inyectar) {
    await ctx.route(/\/api\/ia\/lista(\?.*)?$/, async (ruta) => {
      const r = await ruta.fetch();
      let j; try { j = await r.json(); } catch { return ruta.fulfill({ response: r }); }
      return ruta.fulfill({ response: r, json: { ...j, borradores: [], generado: '2026-10-05 06:00' } });
    });
  }
  const pg = await ctx.newPage();
  pg.on('response', async (r) => { if (/\/api\/ia\/lista/.test(r.url()) && !real) { try { real = await r.json(); } catch { /* sin JSON */ } } });
  await pg.goto(`${base}/?yo=${dir?.id}&hoy=2026-10-05#/asistente-ia`, { waitUntil: 'load', timeout: 45_000 });
  await pg.waitForSelector('[data-resumen-asistente]', { timeout: 20_000 }).catch(() => {});
  await pg.waitForTimeout(2500);
  const texto = await pg.evaluate(() => (document.querySelector('#main') || document.body).innerText);
  // Los que se pintan en la pestaña «Borradores de correo» (la pantalla solo enseña los de clientes que esa persona puede abrir).
  await pg.getByRole('tab', { name: /Borradores de correo/ }).click({ timeout: 5000 }).catch(() => pg.getByText(/Borradores de correo/).first().click({ timeout: 5000 }).catch(() => {}));
  await pg.waitForTimeout(800);
  const pintados = await pg.evaluate(() => document.querySelectorAll('nav[aria-label="Correos"] button').length);
  await ctx.close();
  return { texto, real, pintados };
}
try {
  const a = await abrir(false);
  if (args.volcar) console.log('real:', (a.texto.match(/Lista disponible[^\n]*/) || [''])[0], '|', (a.texto.match(/Fecha declarada[^.]*/) || [''])[0]);
  ok(!!a.real, 'real: no llegó la respuesta de /api/ia/lista');
  const m = /(\d+) borradores/.exec(a.texto);
  ok(!!m, 'real: el texto no dice cuántos borradores hay');
  if (m) ok(Number(m[1]) === a.pintados, `real: el texto dice ${m[1]} borradores y la pantalla pinta ${a.pintados}`);
  if (a.real && m) ok(Number(m[1]) <= (a.real.borradores || []).length, `real: el texto dice ${m[1]} y la respuesta solo trae ${(a.real.borradores || []).length}`);
  ok(!/\b40 correos\b/i.test(a.texto) || (a.real?.borradores || []).length === 40, 'real: «40 correos» fijo');

  const b = await abrir(true);
  if (args.volcar) console.log('inyectada:', (b.texto.match(/Lista disponible[^\n]*/) || [''])[0], '|', (b.texto.match(/Fecha declarada[^.]*/) || [''])[0]);
  ok(!/\b40 (correos|borradores)\b/i.test(b.texto), 'inyectada: sale «40 correos/borradores»');
  ok(!/\b2-oct\b/.test((b.texto.match(/Fecha declarada[^\n]*/) || [''])[0]), 'inyectada: la fecha del listado sigue en «2-oct»');
  ok(/\b0 borradores\b/.test(b.texto), 'inyectada: no dice «0 borradores»');
  ok(/Fecha declarada del listado: 5-oct/.test(b.texto), 'inyectada: la fecha del listado no es «5-oct»');
  ok(!/Sin borradores disponibles/.test(a.texto) || (a.real?.borradores || []).length === 0, 'real: dice «Sin borradores» con borradores');
} finally { await navegador.close(); }
console.log(`${fallos.length ? '✘' : '✔'} L-42: ${n} comprobaciones${fallos.length ? ' · ' + fallos.join(' · ') : ''}`);
process.exit(fallos.length ? 1 : 0);
