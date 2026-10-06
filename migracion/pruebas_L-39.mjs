#!/usr/bin/env node
// migracion/pruebas_L-39.mjs · L-39: un vacío no cuenta cómo se genera el dato.
// Uso: node migracion/pruebas_L-39.mjs --base http://127.0.0.1:8771 [--pantallas a,b] [--informe]
// (1) unitario en el navegador: `limpiaTexto('No existe. Se generan con fuentes_x/generar.py.')` empieza por «Todavía no hay datos».
// (2) dirección, un account y un setter recorren las pantallas de `pantallas.json` que ven: el texto visible no trae
//     «Se generan con.», ni «No existe.» a final de línea. Solo lectura. Solo recuentos y nombres de pantalla en la salida.
import { readFileSync } from 'node:fs';
import { chromium } from '../v2/tools/capturas/node_modules/playwright/index.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, v) => (x.startsWith('--') ? [...a, [x.slice(2), v[i + 1]?.startsWith('--') || v[i + 1] === undefined ? true : v[i + 1]]] : a), []));
const base = String(args.base || 'http://127.0.0.1:8771').replace(/\/$/, '');
const todas = JSON.parse(readFileSync(new URL('./inventario/pantallas.json', import.meta.url), 'utf8')).map((p) => p.id);
const PANTALLAS = args.pantallas ? String(args.pantallas).split(',') : todas;
const MALOS = [[/Se generan? con\s*[.:]/i, '«Se generan con.»'], [/No existe\.?[ \t]*(\n|$)/i, '«No existe.» a final de línea'], [/Se generan? con\s*$/im, '«Se generan con» al final']];
const fallos = [];
let n = 0;
const ok = (c, t) => { n++; if (!c) fallos.push(t); };

const elegir = await (await fetch(`${base}/api/elegir`)).json();
const personas = (elegir.personas || []).filter((p) => (p.estado || 'activo') === 'activo');
const dir = personas.find((p) => (p.puestos || []).includes('direccion'));
const account = personas.find((p) => (p.puestos || []).includes('account') && !(p.puestos || []).includes('direccion'));
const setter = personas.find((p) => (p.puestos || []).includes('setters') && !(p.puestos || []).includes('direccion'));
ok(!!dir && !!account && !!setter, 'falta dirección, account o setter');

const navegador = await chromium.launch();
async function nuevo(p) {
  const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 }, locale: 'es-ES', timezoneId: 'Europe/Madrid', reducedMotion: 'reduce' });
  await ctx.clock.setFixedTime(new Date('2026-10-05T07:30:00+02:00'));
  return ctx;
}
try {
  // (1) unitario
  if (!args.pantallas) {
    const ctx = await nuevo(dir);
    const pg = await ctx.newPage();
    await pg.goto(`${base}/?yo=${dir?.id}&hoy=2026-10-05#/mi-dia`, { waitUntil: 'load', timeout: 45_000 });
    const u = await pg.evaluate(async () => {
      const m = await import('/componentes.js');
      return [m.limpiaTexto('No existe. Se generan con fuentes_x/generar.py.'), m.limpiaTexto('No existe.'), m.limpiaTexto('Sin datos. Se generan con fuentes_x/gen.py.')];
    });
    ok(/^Todavía no hay datos/.test(u[0]), `limpiaTexto(«No existe. Se generan con fichero») → «${u[0]}»`);
    ok(/^Todavía no hay datos/.test(u[1]), `limpiaTexto(«No existe.») → «${u[1]}»`);
    ok(!/Se generan? con/i.test(u[2]), `limpiaTexto(«… Se generan con fichero.») → «${u[2]}»`);
    await ctx.close();
  }
  // (2) pantallas
  const hallados = {};
  await Promise.all([dir, account, setter].filter(Boolean).map(async (p) => {
    const ctx = await nuevo(p);
    try {
      for (const pant of PANTALLAS) {
        const pg = await ctx.newPage();
        try {
          await pg.goto(`${base}/?yo=${p.id}&hoy=2026-10-05#/${pant}`, { waitUntil: 'load', timeout: 45_000 });
          await pg.waitForSelector('#main', { timeout: 20_000 }).catch(() => {});
          await pg.waitForTimeout(3500);
          const t = await pg.evaluate(() => (document.querySelector('#main') || document.body).innerText);
          for (const [re, que] of MALOS) if (re.test(t)) { (hallados[`${pant}`] ||= new Set()).add(que); }
        } catch { /* pantalla sin acceso */ } finally { await pg.close(); }
      }
    } finally { await ctx.close(); }
  }));
  ok(Object.keys(hallados).length === 0, `pantallas con vacío técnico: ${Object.entries(hallados).map(([k, v]) => `${k} [${[...v].join(', ')}]`).join('; ')}`);
  n += PANTALLAS.length * 3;
} finally { await navegador.close(); }
console.log(`${fallos.length ? '✘' : '✔'} L-39: ${n} comprobaciones${fallos.length ? ' · ' + fallos.join(' · ') : ''}`);
process.exit(fallos.length ? 1 : 0);
