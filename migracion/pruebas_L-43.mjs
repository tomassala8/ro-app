#!/usr/bin/env node
// migracion/pruebas_L-43.mjs · L-43: quien no ve la cuota no ve un título que la promete.
// Uso: node migracion/pruebas_L-43.mjs --base http://127.0.0.1:8771 [--volcar]
// Para una persona de cada tipo (trafficker, account, jefa de publicidad, proyectos+account y dirección), en `#/dinero-cliente`:
//   · el enlace del menú y `#titulo` dicen «Horas por cliente» si ninguno de sus puestos ve la cuota, y «Dinero por cliente» si alguno la ve;
//   · quien no ve la cuota no lee «cuota» ni «rentabilidad» en el subtítulo ni en el título.
// Solo lectura. La regla de quién ve la cuota sale de `reglas_permisos.json` (`tipos.cuota`), no de nombres de personas.
import { readFileSync } from 'node:fs';
import { chromium } from '../v2/tools/capturas/node_modules/playwright/index.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, v) => (x.startsWith('--') ? [...a, [x.slice(2), v[i + 1]?.startsWith('--') || v[i + 1] === undefined ? true : v[i + 1]]] : a), []));
const base = String(args.base || 'http://127.0.0.1:8771').replace(/\/$/, '');
const reglas = JSON.parse(readFileSync(new URL('../reglas_permisos.json', import.meta.url), 'utf8'));
const CUOTA = new Set((reglas.tipos?.cuota?.si || []).flatMap((s) => s.puestos || []));
const fallos = [];
let n = 0;
const ok = (c, t) => { n++; if (!c) fallos.push(t); };

const elegir = await (await fetch(`${base}/api/elegir`)).json();
const activas = (elegir.personas || []).filter((p) => (p.estado || 'activo') === 'activo');
const tiene = (p, x) => (p.puestos || []).includes(x);
const sinCuota = (p) => !(p.puestos || []).some((x) => CUOTA.has(x));
const elegidas = [
  ['trafficker', activas.find((p) => tiene(p, 'trafficker') && sinCuota(p))],
  ['account', activas.find((p) => tiene(p, 'account') && sinCuota(p))],
  ['jefa_publicidad', activas.find((p) => tiene(p, 'jefa_publicidad') && sinCuota(p))],
  ['proyectos+account', activas.find((p) => tiene(p, 'proyectos') && tiene(p, 'account'))],
  ['direccion', activas.find((p) => tiene(p, 'direccion'))],
];
for (const [que, p] of elegidas) ok(!!p, `no hay persona de tipo ${que}`);

const navegador = await chromium.launch();
try {
  for (const [que, p] of elegidas.filter(([, p]) => p)) {
    const ve = !sinCuota(p);
    const esperado = ve ? 'Dinero por cliente' : 'Horas por cliente';
    const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 }, locale: 'es-ES', timezoneId: 'Europe/Madrid', reducedMotion: 'reduce' });
    await ctx.clock.setFixedTime(new Date('2026-10-05T07:30:00+02:00'));
    const pg = await ctx.newPage();
    try {
      await pg.goto(`${base}/?yo=${p.id}&hoy=2026-10-05#/dinero-cliente`, { waitUntil: 'load', timeout: 45_000 });
      await pg.waitForSelector('#main', { timeout: 20_000 }).catch(() => {});
      await pg.waitForFunction(() => /clientes ·|clientes asignados|Sin datos/.test(document.querySelector('#subtitulo')?.textContent || '') || document.querySelector('#main')?.innerText.length > 400, null, { timeout: 20_000 }).catch(() => {});
      await pg.waitForTimeout(2500);
      const r = await pg.evaluate(() => ({
        titulo: document.querySelector('#titulo')?.textContent?.trim() || '',
        sub: document.querySelector('#subtitulo')?.textContent?.trim() || '',
        menu: document.querySelector('a[data-id="dinero-cliente"] .nl')?.textContent?.trim() || null,
        pestana: document.title,
      }));
      if (args.volcar) console.log(`${que}: título «${r.titulo}» · menú «${r.menu}» · sub «${r.sub.slice(0, 90)}»`);
      ok(r.titulo === esperado, `${que}: título «${r.titulo}» (esperado «${esperado}»)`);
      ok(r.menu === esperado, `${que}: enlace del menú «${r.menu}» (esperado «${esperado}»)`);
      ok(r.pestana.startsWith(esperado), `${que}: pestaña «${r.pestana}»`);
      if (!ve) ok(!/cuota|rentabilidad/i.test(`${r.titulo} ${r.sub}`), `${que}: el título o el subtítulo hablan de cuota o rentabilidad («${r.sub.slice(0, 80)}»)`);
    } catch (e) { fallos.push(`${que}: no cargó (${String(e).slice(0, 80)})`); } finally { await ctx.close(); }
  }
} finally { await navegador.close(); }
console.log(`${fallos.length ? '✘' : '✔'} L-43: ${n} comprobaciones${fallos.length ? ' · ' + fallos.join(' · ') : ''}`);
process.exit(fallos.length ? 1 : 0);
