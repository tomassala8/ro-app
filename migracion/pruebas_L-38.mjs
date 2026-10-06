#!/usr/bin/env node
// migracion/pruebas_L-38.mjs · L-38: «Fase 2» solo lo ve dirección. Solo lectura.
// Un account en `#/bandeja` y `#/mi-dia`: ni «Fase 2» ni «Va a Fase 2» en la pantalla.
// Dirección en `#/bandeja`: el pie «Fase 2 · N indicadores…» sigue ahí.
import { chromium } from '../v2/tools/capturas/node_modules/playwright/index.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, v) => (x.startsWith('--') ? [...a, [x.slice(2), v[i + 1]]] : a), []));
const base = String(args.base || 'http://127.0.0.1:8771').replace(/\/$/, '');
const fallos = [];
let n = 0;
const ok = (c, t) => { n++; if (!c) fallos.push(t); };

const elegir = await (await fetch(`${base}/api/elegir`)).json();
const personas = (elegir.personas || []).filter((p) => (p.estado || 'activo') === 'activo');
const dir = personas.find((p) => (p.puestos || []).includes('direccion'));
const account = personas.find((p) => (p.puestos || []).includes('account') && !(p.puestos || []).includes('direccion'));
ok(!!dir && !!account, 'falta una persona de dirección o un account');

const navegador = await chromium.launch();
async function texto(p, pantalla) {
  const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 }, locale: 'es-ES', timezoneId: 'Europe/Madrid', reducedMotion: 'reduce' });
  await ctx.clock.setFixedTime(new Date('2026-10-05T07:30:00+02:00'));
  const pg = await ctx.newPage();
  try {
    await pg.goto(`${base}/?yo=${p.id}&hoy=2026-10-05#/${pantalla}`, { waitUntil: 'load', timeout: 45_000 });
    await pg.waitForSelector('#main', { timeout: 25_000 }).catch(() => {});
    await pg.waitForTimeout(6000);
    return await pg.evaluate(() => ({ cuerpo: document.body.innerText, resumenes: document.querySelector('#subtitulo')?.textContent || '', pie: !!document.querySelector('details.pie-fase2') }));
  } finally { await ctx.close(); }
}
try {
  if (account) {
    for (const pant of ['bandeja', 'mi-dia']) {
      const t = await texto(account, pant);
      ok(!/Fase 2/i.test(t.cuerpo), `account en ${pant}: aparece «Fase 2»`);
      ok(!/Va a Fase/i.test(t.cuerpo), `account en ${pant}: aparece «Va a Fase 2»`);
      ok(!/\b[WDGCE]-?\d{1,2}\b/.test(t.resumenes), `account en ${pant}: código en el subtítulo`);
    }
    const b = await texto(account, 'bandeja');
    ok(b.pie, 'account en bandeja: el pie de lo que todavía no se mide ha desaparecido (solo debía perder el rótulo «Fase 2»)');
  }
  if (dir) {
    const t = await texto(dir, 'bandeja');
    ok(/Fase 2 ·/.test(t.cuerpo), 'dirección en bandeja: no ve «Fase 2 ·» en el pie');
  }
} finally { await navegador.close(); }
console.log(`${fallos.length ? '✘' : '✔'} navegador L-38: ${n} comprobaciones${fallos.length ? ' · ' + fallos.join(' · ') : ''}`);
process.exit(fallos.length ? 1 : 0);
