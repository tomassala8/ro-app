#!/usr/bin/env node
// migracion/pruebas_N-12.mjs · N-12 (parte de pantalla): lee el texto de dos pantallas y del sello del menú.
// Uso:  node migracion/pruebas_N-12.mjs --base http://127.0.0.1:8781 --yo <persona>
// Escribe en la salida un JSON {seo, miDia, menu}; quien la llama (pruebas_N-12.py) juzga. No guarda nada. Sin datos reales.
import { chromium } from '../v2/tools/capturas/node_modules/playwright/index.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, v) => (x.startsWith('--') ? [...a, [x.slice(2), v[i + 1]]] : a), []));
const base = String(args.base || 'http://127.0.0.1:8781').replace(/\/$/, '');
const navegador = await chromium.launch();
async function leer(pantalla) {
  const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 }, locale: 'es-ES', timezoneId: 'Europe/Madrid', reducedMotion: 'reduce' });
  const pagina = await ctx.newPage();
  try {
    await pagina.goto(`${base}/?yo=${args.yo}&hoy=2026-10-05#/${pantalla}`, { waitUntil: 'load', timeout: 45_000 });
    await pagina.waitForTimeout(4500);
    return await pagina.evaluate(() => ({ main: (document.querySelector('#main') || document.body).innerText, menu: document.querySelector('#frescura summary')?.innerText || '' }));
  } finally {
    await ctx.close();
  }
}
const seo = await leer('seo-web');
const miDia = await leer('mi-dia');
await navegador.close();
console.log(JSON.stringify({ seo: seo.main, miDia: miDia.main, menu: seo.menu }));
