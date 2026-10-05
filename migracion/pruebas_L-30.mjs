#!/usr/bin/env node
// migracion/pruebas_L-30.mjs · L-30: «clientes bien» de Mi día sale de una sola regla (la gravedad de la verdad única).
// Uso: node migracion/pruebas_L-30.mjs --base http://127.0.0.1:8771
// Lee Mi día de una persona de dirección y de un account, saca los números que acompañan a «bien» en la cartera y exige que
// los que hablan de «N bien» coincidan entre sí. Si no encuentra ninguno, falla (la prueba no mide nada). Sin datos reales en el repo.
import { chromium } from '../v2/tools/capturas/node_modules/playwright/index.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, v) => (x.startsWith('--') ? [...a, [x.slice(2), v[i + 1]?.startsWith('--') || v[i + 1] === undefined ? true : v[i + 1]]] : a), []));
const base = String(args.base || 'http://127.0.0.1:8771').replace(/\/$/, '');
const elegir = await (await fetch(`${base}/api/elegir`)).json();
const personas = elegir.personas || [];
const direccion = personas.find((p) => (p.puestos || []).includes('direccion'));
const account = personas.find((p) => (p.puestos || []).includes('account') && !(p.puestos || []).includes('direccion'));
const navegador = await chromium.launch();
const fallos = [];

for (const p of [direccion, account].filter(Boolean)) {
  const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 }, locale: 'es-ES', timezoneId: 'Europe/Madrid', reducedMotion: 'reduce' });
  await ctx.clock.setFixedTime(new Date('2026-10-05T07:30:00+02:00'));
  const pagina = await ctx.newPage();
  try {
    await pagina.goto(`${base}/?yo=${p.id}&hoy=2026-10-05#/mi-dia`, { waitUntil: 'load', timeout: 45_000 });
    await pagina.waitForFunction(() => {
      const m = document.querySelector('#main') || document.body;
      const t = (m.innerText || '').trim();
      if (!t || /(Cargando|Leyendo|Pidiendo)[^\n]*(…|\.\.\.)/.test(t)) return false;
      const w = window.__roEstable || (window.__roEstable = { texto: '', n: 0 });
      if (w.texto !== t) { w.texto = t; w.n = 0; return false; }
      return ++w.n >= 12;
    }, null, { timeout: 20_000, polling: 100 }).catch(() => {});
    const texto = await pagina.evaluate(() => (document.querySelector('#main') || document.body).innerText);
    // «N bien» (chip y motivo de la cartera) y «bien de M» (unidad del tile): el N es el de clientes bien.
    if (args.volcar) console.log(texto.split("\n").filter((l) => /\bbien\b/.test(l)).join("\n"));
    const nBien = [...texto.matchAll(/(\d+)\s+bien\b(?!\s+(de|más))/g)].map((m) => +m[1]);
    const distintos = [...new Set(nBien)];
    console.log(`  · ${p.id}: «N bien» → ${nBien.join(', ') || 'ninguno'}`);
    if (!nBien.length) console.log(`    (sin cartera con «bien» para esta persona: ${texto.slice(0, 120).replace(/\s+/g, ' ')}…)`);
    else if (distintos.length > 1) fallos.push(`${p.id}: Mi día da cifras distintas de «clientes bien»: ${nBien.join(', ')}`);
    p.vistos = nBien.length;
  } finally { await ctx.close(); }
}
await navegador.close();
if (!(direccion?.vistos || account?.vistos)) fallos.push('ninguna de las dos personas mostró «N bien»: la prueba no mide nada');
if (fallos.length) { console.log(`✘ L-30: ${fallos.length} fallos`); fallos.forEach((f) => console.log(`  - ${f}`)); process.exit(1); }
console.log('✔ L-30: una sola cifra de «clientes bien» en Mi día');
