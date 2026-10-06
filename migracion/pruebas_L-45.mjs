#!/usr/bin/env node
// migracion/pruebas_L-45.mjs · L-45 (navegador, solo lectura).
// (a) `#/decisiones`: el chip «Para proyectos» no sale a 0 (solo a quien tiene alguna decisión de ese tipo) y sale si la API trae una;
//     ningún chip dice «Para Coti» ni «Para Tomás».
// (b) `#vercomo-sel` (dirección) no repite ningún `value`.
import { chromium } from '../v2/tools/capturas/node_modules/playwright/index.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, v) => (x.startsWith('--') ? [...a, [x.slice(2), v[i + 1]?.startsWith('--') || v[i + 1] === undefined ? true : v[i + 1]]] : a), []));
const base = String(args.base || 'http://127.0.0.1:8771').replace(/\/$/, '');
const fallos = [];
let n = 0;
const ok = (c, t) => { n++; if (!c) fallos.push(t); };

const elegir = await (await fetch(`${base}/api/elegir`)).json();
const activas = (elegir.personas || []).filter((p) => (p.estado || 'activo') === 'activo');
const tiene = (p, x) => (p.puestos || []).includes(x);
const dir = activas.find((p) => tiene(p, 'direccion'));
const proy = activas.find((p) => tiene(p, 'proyectos'));
const account = activas.find((p) => tiene(p, 'account') && !tiene(p, 'direccion') && !tiene(p, 'proyectos'));
const setter = activas.find((p) => tiene(p, 'setters') && !tiene(p, 'direccion'));
ok(!!dir && !!account, 'falta dirección o un account');

const navegador = await chromium.launch();
try {
  for (const [que, p] of [['dirección', dir], ['proyectos', proy], ['account', account], ['setter', setter]].filter(([, p]) => p)) {
    const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 }, locale: 'es-ES', timezoneId: 'Europe/Madrid', reducedMotion: 'reduce' });
    await ctx.clock.setFixedTime(new Date('2026-10-05T07:30:00+02:00'));
    const pg = await ctx.newPage();
    let decis = null;
    pg.on('response', async (r) => { if (/\/api\/decisiones(\?.*)?$/.test(r.url()) && r.request().method() === 'GET') { try { decis = (await r.json()).decisiones || []; } catch { /* sin JSON */ } } });
    try {
      await pg.goto(`${base}/?yo=${p.id}&hoy=2026-10-05#/decisiones`, { waitUntil: 'load', timeout: 45_000 });
      await pg.waitForSelector('#main', { timeout: 20_000 }).catch(() => {});
      await pg.waitForTimeout(3500);
      const r = await pg.evaluate(() => ({
        chips: [...document.querySelectorAll('#main button, #main [role=tab], #main .chip, #main label')].map((e) => (e.textContent || '').trim()).filter((t) => /^Para /.test(t)),
        texto: (document.querySelector('#main') || document.body).innerText,
        opciones: [...document.querySelectorAll('#vercomo-sel option')].map((o) => o.value),
      }));
      if (args.volcar) console.log(`${que}: chips ${JSON.stringify(r.chips)} · decisiones ${decis === null ? 'sin lectura' : decis.length} (para_coti ${decis ? decis.filter((d) => d.tipo === 'para_coti').length : '?'})`);
      ok(!/Para Coti|Para Tomás/.test(r.chips.join('|')), `${que}: un chip nombra a una persona (${r.chips.join(' / ')})`);
      ok(!/Para Coti/.test(r.texto), `${que}: la pantalla dice «Para Coti»`);
      // El chip lleva su cuenta pegada («Para proyectos3»): nunca sale con 0, y sale si la API trae una decisión de ese tipo.
      ok(!r.chips.some((t) => /^Para proyectos0?$/.test(t) && !/[1-9]/.test(t)), `${que}: el chip «Para proyectos» sale a 0 (${r.chips.join(' / ')})`);
      if (decis !== null) {
        const hay = decis.some((d) => d.tipo === 'para_coti');
        if (hay) ok(r.chips.some((t) => /^Para proyectos/.test(t)), `${que}: hay decisiones para proyectos y no sale el chip`);
      } else ok(false, `${que}: no llegó la lista de decisiones`);
      if (p === dir) {
        const rep = r.opciones.filter((v, i) => r.opciones.indexOf(v) !== i);
        ok(r.opciones.length > 1 && rep.length === 0, `desplegable «ver como»: ${r.opciones.length} opciones, repetidas: ${[...new Set(rep)].join(', ')}`);
      }
    } catch (e) { fallos.push(`${que}: no cargó (${String(e).slice(0, 80)})`); } finally { await ctx.close(); }
  }
} finally { await navegador.close(); }
console.log(`${fallos.length ? '✘' : '✔'} navegador L-45: ${n} comprobaciones${fallos.length ? ' · ' + fallos.join(' · ') : ''}`);
process.exit(fallos.length ? 1 : 0);
