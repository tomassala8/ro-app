#!/usr/bin/env node
// migracion/pruebas_L-35.mjs · L-35: «Deshacer» al marcar una alerta y al despachar en lote (Alertas).
// Uso: node migracion/pruebas_L-35.mjs --base http://127.0.0.1:8781     (ESCRIBE: solo contra el servidor propio sobre ro_esc)
// Como dirección: (1) «Lo tengo» → aviso con «Deshacer» en < 1 s; Deshacer → la alerta no se escribe en /api/acciones.
// (2) «Lo tengo» sin deshacer → tras el plazo la acción sí está. (3) y (4): lo mismo en lote con 2 alertas («Resueltas»).
import { chromium } from '../v2/tools/capturas/node_modules/playwright/index.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, v) => (x.startsWith('--') ? [...a, [x.slice(2), v[i + 1]?.startsWith('--') || v[i + 1] === undefined ? true : v[i + 1]]] : a), []));
const base = String(args.base || 'http://127.0.0.1:8781').replace(/\/$/, '');
if (!/:8781$/.test(base)) { console.log('✘ L-35: escribe; solo contra el 8781 propio'); process.exit(2); }
const YO = 'tomas', PLAZO = 8000;
const fallos = []; let n = 0;
const ok = (c, t) => { n++; if (!c) fallos.push(t); };
const acciones = async () => (await (await fetch(`${base}/api/acciones?modulo=alertas`, { headers: { 'X-RO-App': '1', 'X-RO-Yo': YO, Accept: 'application/json' } })).json()).acciones || [];
const vista = (x) => { try { return typeof x.vista_previa === 'string' ? JSON.parse(x.vista_previa) : (x.vista_previa || {}); } catch { return {}; } };
const hay = (accs, id) => accs.some((x) => x.objeto === id || String(x.objeto || '').startsWith('lote:') && (vista(x).ids || []).includes(id));
const dormir = (ms) => new Promise((r) => setTimeout(r, ms));

const navegador = await chromium.launch();
try {
  const ctx = await navegador.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'es-ES', timezoneId: 'Europe/Madrid' });
  const p = await ctx.newPage();
  const abrir = async () => {
    await p.goto(`${base}/?yo=${YO}#/alertas`, { waitUntil: 'load', timeout: 45_000 });
    await p.waitForSelector('article[data-alerta]', { timeout: 30_000 });
  };
  await abrir();
  // tarjetas con botón «Lo tengo» (abiertas): se toman 4 ids distintas
  const ids = await p.$$eval('article[data-alerta]', (as) => as.filter((a) => [...a.querySelectorAll('button')].some((b) => /^\s*Lo tengo\s*$/.test(b.textContent || ''))).slice(0, 4).map((a) => a.dataset.alerta));
  ok(ids.length === 4, `hacen falta 4 alertas abiertas con «Lo tengo»; hay ${ids.length}`);
  if (ids.length === 4) {
    const [a1, a2, l1, l2] = ids;
    const loTengo = (id) => p.locator(`article[data-alerta="${id}"] button`, { hasText: /^\s*Lo tengo\s*$/ }).first();
    const deshacer = () => p.locator('.tostada[data-deshacer] button', { hasText: 'Deshacer' });

    // (1) marcar y deshacer
    const t0 = Date.now();
    await loTengo(a1).click();
    await deshacer().waitFor({ timeout: 1500 }).catch(() => {});
    ok(await deshacer().count() === 1 && Date.now() - t0 < 1500, '(1) no sale «Deshacer» en 1 s al marcar «Lo tengo»');
    await deshacer().click().catch(() => {});
    await p.waitForTimeout(400);
    ok(await p.locator(`article[data-alerta="${a1}"] button`, { hasText: /^\s*Lo tengo\s*$/ }).count() >= 1, '(1) tras deshacer, la alerta no vuelve a tener «Lo tengo»');
    await dormir(PLAZO + 1500);
    ok(!hay(await acciones(), a1), '(1) la alerta deshecha se escribió igualmente');

    // (2) marcar sin deshacer
    await loTengo(a2).click();
    await deshacer().waitFor({ timeout: 1500 }).catch(() => {});
    await dormir(PLAZO + 2500);
    ok(hay(await acciones(), a2), '(2) sin deshacer, la acción no llegó a /api/acciones tras el plazo');

    // (3) lote y deshacer
    await abrir();
    for (const id of [l1, l2]) await p.locator(`input[data-sel="${id}"]`).check();
    const t1 = Date.now();
    await p.locator('button', { hasText: /^\s*Resueltas\s*$/ }).first().click();
    await deshacer().waitFor({ timeout: 1500 }).catch(() => {});
    ok(await deshacer().count() === 1 && Date.now() - t1 < 1500, '(3) no sale «Deshacer» en 1 s al despachar en lote');
    await deshacer().click().catch(() => {});
    await p.waitForTimeout(400);
    await dormir(PLAZO + 1500);
    const tras = await acciones();
    ok(!hay(tras, l1) && !hay(tras, l2), '(3) el lote deshecho se escribió igualmente');

    // (4) lote sin deshacer
    for (const id of [l1, l2]) { const c = p.locator(`input[data-sel="${id}"]`); if (await c.count()) await c.check(); }
    await p.locator('button', { hasText: /^\s*Resueltas\s*$/ }).first().click();
    await deshacer().waitFor({ timeout: 1500 }).catch(() => {});
    await dormir(PLAZO + 2500);
    const fin = await acciones();
    ok(hay(fin, l1) && hay(fin, l2), '(4) sin deshacer, el lote no llegó a /api/acciones tras el plazo');
  }
} finally { await navegador.close(); }
console.log(`${fallos.length ? '✘' : '✔'} L-35: ${n} comprobaciones${fallos.length ? ' · ' + fallos.join(' · ') : ''}`);
process.exit(fallos.length ? 1 : 0);
