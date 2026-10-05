#!/usr/bin/env node
// migracion/pruebas_L-32.mjs · L-32: sin account en la verdad única, la ficha lo dice («sin account · para confirmar»), no pinta el de la Cartera.
// Uso: node migracion/pruebas_L-32.mjs --base http://127.0.0.1:8771
// No toca datos: el navegador recibe la verdad real con el primer cliente puesto sin account (`page.route`). Control: con la verdad
// tal cual, ese mismo cliente muestra a su account. Sin datos reales en el repo: solo se miran los textos.
import { chromium } from '../v2/tools/capturas/node_modules/playwright/index.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, v) => (x.startsWith('--') ? [...a, [x.slice(2), v[i + 1]?.startsWith('--') || v[i + 1] === undefined ? true : v[i + 1]]] : a), []));
const base = String(args.base || 'http://127.0.0.1:8771').replace(/\/$/, '');
const elegir = await (await fetch(`${base}/api/elegir`)).json();
const direccion = (elegir.personas || []).find((p) => (p.puestos || []).includes('direccion'));
const navegador = await chromium.launch();
const fallos = [];

async function subtitulo(vaciarAccount) {
  const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 }, locale: 'es-ES', timezoneId: 'Europe/Madrid', reducedMotion: 'reduce' });
  const pagina = await ctx.newPage();
  let id = null;
  await pagina.route('**/api/modulo/verdad/clientes*', async (ruta) => {
    const resp = await ruta.fetch();
    const v = await resp.json();
    const c = (v.clientes || []).find((x) => x.account);   // un cliente que hoy sí tiene account
    id = c?.cliente_id || null;
    if (vaciarAccount && c) {
      c.account = null; c.sin_account = 'sin account';
      const u = (v.comun || []).find((x) => x.id === c.cliente_id);
      if (u) { u.responsable_id = null; u.sin_account = 'sin account'; }
    }
    await ruta.fulfill({ response: resp, json: v });
  });
  try {
    await pagina.goto(`${base}/?yo=${direccion.id}#/ficha`, { waitUntil: 'load', timeout: 45_000 });
    await pagina.waitForTimeout(1500);
    // El primer cliente que abra la ficha puede no ser el de la verdad tocada: se abre ese por id.
    if (id) await pagina.evaluate((x) => { location.hash = `#/ficha/${x}`; }, id);
    await pagina.waitForFunction(() => /Lleva el cliente/.test(document.querySelector('#titulo')?.parentElement?.innerText || document.body.innerText), null, { timeout: 20_000 }).catch(() => {});
    await pagina.waitForTimeout(1500);
    const texto = await pagina.evaluate(() => document.body.innerText);
    return { id, linea: (texto.match(/Lleva el cliente [^\n]*/) || [''])[0] };
  } finally { await ctx.close(); }
}

const real = await subtitulo(false);
const sin = await subtitulo(true);
console.log(`  · control (verdad tal cual): «${real.linea.replace(/Lleva el cliente /, '').slice(0, 20)}…»`);
console.log(`  · sin account en la verdad: «${sin.linea}»`);
if (!real.id) fallos.push('control: no hay ningún cliente con account en la verdad (la prueba no mide nada)');
if (real.linea && /sin account/.test(real.linea)) fallos.push('control: con la verdad tal cual, el cliente sale sin account');
if (!/Lleva el cliente sin account · para confirmar/.test(sin.linea)) fallos.push(`sin account en la verdad: la ficha dice «${sin.linea}» y debía decir «Lleva el cliente sin account · para confirmar»`);
await navegador.close();
if (fallos.length) { console.log(`✘ L-32: ${fallos.length} fallos`); fallos.forEach((f) => console.log(`  - ${f}`)); process.exit(1); }
console.log('✔ L-32: sin account en la verdad, la ficha lo dice');
