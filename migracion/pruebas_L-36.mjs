#!/usr/bin/env node
// migracion/pruebas_L-36.mjs · L-36: «Reabrir» (Gasto de IA) no rompe en «ver como» ni cuando la ruta falla.
// Uso: node migracion/pruebas_L-36.mjs --base http://127.0.0.1:8771     (solo lectura: la escritura se simula en el navegador)
// La pantalla solo enseña «Reabrir» si el motivo de la IA cita la Console; aquí el motivo se cambia en el navegador
// (page.route sobre GET /api/ia/gasto) y la ruta POST /api/ia/gasto/reabrir se contesta con un 500 simulado:
// nada llega al servidor. (1) Tomás «ver como» otra persona: sin botón «Reabrir» activo y sin errores de página.
// (2) Tomás como él mismo: el botón existe, al pulsar con 500 sale el aviso en role="status" y ninguna promesa sin capturar.
import { chromium } from '../v2/tools/capturas/node_modules/playwright/index.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, v) => (x.startsWith('--') ? [...a, [x.slice(2), v[i + 1]?.startsWith('--') || v[i + 1] === undefined ? true : v[i + 1]]] : a), []));
const base = String(args.base || 'http://127.0.0.1:8771').replace(/\/$/, '');
const fallos = []; let n = 0;
const ok = (c, t) => { n++; if (!c) fallos.push(t); };
const REABRIR = /^\s*Reabrir/;
const MOTIVO = 'Límite de la Console alcanzado (simulado en el navegador).';

const real = await (await fetch(`${base}/api/ia/gasto`, { headers: { 'X-RO-App': '1', 'X-RO-Yo': 'tomas', Accept: 'application/json' } })).json();
const elegir = await (await fetch(`${base}/api/elegir`)).json();
const otra = (elegir.personas || []).find((p) => p.id !== 'tomas' && (p.estado || 'activo') === 'activo' && (p.puestos || []).includes('account'))?.id;
ok(!!otra && real?.ok === true, 'hace falta la respuesta real de /api/ia/gasto y una persona account activa');

const navegador = await chromium.launch();
try {
  const abrir = async (como, rutaReabrir) => {
    const ctx = await navegador.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'es-ES', timezoneId: 'Europe/Madrid' });
    const p = await ctx.newPage();
    const errores = [], llamadas = [];
    p.on('pageerror', (e) => errores.push(String(e?.message || e)));
    await p.addInitScript(() => {
      window.__sinCapturar = [];
      addEventListener('unhandledrejection', (e) => window.__sinCapturar.push(String(e.reason?.message || e.reason)));
    });
    await p.route((u) => /\/api\/ia\/gasto$/.test(u.pathname), async (r) => {
      if (r.request().method() !== 'GET') return r.continue();
      const resp = await r.fetch();
      const cuerpo = await resp.json();
      return r.fulfill({ response: resp, json: { ...cuerpo, motivo: MOTIVO } });
    });
    await p.route((u) => /\/api\/ia\/gasto\/reabrir$/.test(u.pathname), (r) => { llamadas.push(r.request().method()); return rutaReabrir(r); });
    await p.goto(`${base}/?yo=tomas${como ? `&como=${como}` : ''}#/gasto-ia`, { waitUntil: 'load', timeout: 45_000 });
    await p.waitForTimeout(3000);
    return { p, ctx, errores, llamadas };
  };

  // (1) «ver como» otra persona
  {
    const { p, ctx, errores, llamadas } = await abrir(otra, (r) => r.fulfill({ status: 500, contentType: 'application/json', body: '{"error":"x"}' }));
    const botones = p.locator('button', { hasText: REABRIR });
    const n1 = await botones.count();
    const activos = n1 ? await botones.evaluateAll((bs) => bs.filter((b) => !b.disabled).length) : 0;
    ok(activos === 0, `(1) «ver como» enseña ${activos} botón(es) «Reabrir» activo(s)`);
    ok(llamadas.length === 0, '(1) «ver como» llamó a reabrir');
    ok(errores.length === 0, `(1) errores de página en «ver como»: ${errores.join(' | ').slice(0, 120)}`);
    ok((await p.evaluate(() => window.__sinCapturar)).length === 0, '(1) promesas sin capturar en «ver como»');
    await ctx.close();
  }

  // (2) la misma persona, la ruta falla con 500
  {
    const { p, ctx, errores, llamadas } = await abrir(null, (r) => r.fulfill({ status: 500, contentType: 'application/json', body: '{"error":"x"}' }));
    const boton = p.locator('button', { hasText: REABRIR }).first();
    ok(await boton.count() === 1, '(2) sin «ver como» no hay botón «Reabrir» con el motivo de la Console');
    if (await boton.count() === 1) {
      ok(await boton.isEnabled(), '(2) el botón «Reabrir» está desactivado para quien puede');
      await boton.click();
      await p.waitForTimeout(1500);
      ok(llamadas.length === 1, `(2) esperaba 1 llamada a reabrir y hubo ${llamadas.length}`);
      const aviso = (await p.locator('[role="status"]').allInnerTexts()).join(' ');
      ok(/No se confirmó la reapertura/.test(aviso), `(2) sin aviso de error en role="status": «${aviso.slice(0, 80)}»`);
      ok(errores.length === 0, `(2) errores de página con el 500: ${errores.join(' | ').slice(0, 120)}`);
      ok((await p.evaluate(() => window.__sinCapturar)).length === 0, '(2) promesas sin capturar con el 500');
    }
    await ctx.close();
  }
} finally { await navegador.close(); }
console.log(`${fallos.length ? '✘' : '✔'} L-36: ${n} comprobaciones${fallos.length ? ' · ' + fallos.join(' · ') : ''}`);
process.exit(fallos.length ? 1 : 0);
