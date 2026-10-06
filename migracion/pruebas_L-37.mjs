#!/usr/bin/env node
// migracion/pruebas_L-37.mjs · L-37: la campana y el contador de «Alertas» no se confunden.
// Uso: node migracion/pruebas_L-37.mjs --base http://127.0.0.1:8771
// Con una persona de dirección y una account, en `#/mi-dia`:
//  · `#campana-btn` lleva `aria-label` y `title` que empiezan por «Avisos y menciones» (con cuenta: «…: N nuevos…»);
//  · el número de «Alertas» en el menú (si lo hay) es un entero y dice en su `title` que son alertas «tuyas»;
//  · nada que se llame «Alertas» es la campana, y la campana no se llama «Alertas».
// Solo lectura. Solo se comparan frases y enteros; nada de datos reales a la salida.
import { chromium } from '../v2/tools/capturas/node_modules/playwright/index.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, v) => (x.startsWith('--') ? [...a, [x.slice(2), v[i + 1]?.startsWith('--') || v[i + 1] === undefined ? true : v[i + 1]]] : a), []));
const base = String(args.base || 'http://127.0.0.1:8771').replace(/\/$/, '');
const fallos = [];
let comprobados = 0;
const ok = (c, t) => { comprobados++; if (!c) fallos.push(t); };

const elegir = await (await fetch(`${base}/api/elegir`)).json();
const personas = (elegir.personas || []).filter((p) => (p.estado || 'activo') === 'activo');
const dirigida = personas.find((p) => (p.puestos || []).includes('direccion'));
const account = personas.find((p) => (p.puestos || []).includes('account') && !(p.puestos || []).includes('direccion'));
const elegidas = [dirigida, account].filter(Boolean);
ok(elegidas.length === 2, 'no hay una persona de dirección y un account en /api/elegir');

const navegador = await chromium.launch();
try {
  for (const p of elegidas) {
    const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 }, locale: 'es-ES', timezoneId: 'Europe/Madrid', reducedMotion: 'reduce' });
    await ctx.clock.setFixedTime(new Date('2026-10-05T07:30:00+02:00'));
    const pagina = await ctx.newPage();
    try {
      await pagina.goto(`${base}/?yo=${p.id}&hoy=2026-10-05#/mi-dia`, { waitUntil: 'load', timeout: 45_000 });
      await pagina.waitForSelector('#campana-btn', { timeout: 25_000 }).catch(() => {});
      await pagina.waitForTimeout(3500);
      const r = await pagina.evaluate(() => {
        const b = document.querySelector('#campana-btn');
        const al = document.querySelector('#nav a[href="#/alertas"]');
        const num = al?.querySelector('span.n');
        return {
          hay: !!b, label: b?.getAttribute('aria-label') || '', titulo: b?.getAttribute('title') || '',
          menuAlertas: !!al, numAlertas: num ? num.textContent.trim() : null, tituloNum: num?.getAttribute('title') || '',
          campanaEnAlertas: !!al?.querySelector('#campana-btn'), campanaDiceAlertas: /alertas/i.test(b?.getAttribute('aria-label') || ''),
        };
      });
      const q = `${p.id.replace(/\d+/g, '')}`;
      ok(r.hay, `${q}: no hay campana`);
      ok(/^Avisos y menciones/.test(r.label), `${q}: aria-label de la campana «${r.label.slice(0, 40)}»`);
      ok(/^Avisos y menciones/.test(r.titulo), `${q}: title de la campana «${r.titulo.slice(0, 40)}»`);
      ok(!r.campanaDiceAlertas && !r.campanaEnAlertas, `${q}: la campana se confunde con Alertas`);
      if (r.numAlertas !== null) {
        ok(/^(\d+|99\+)$/.test(r.numAlertas), `${q}: el número de Alertas no es un entero («${r.numAlertas}»)`);
        ok(/alerta/i.test(r.tituloNum) && /tuy/i.test(r.tituloNum), `${q}: el número de Alertas no dice que son «tuyas» («${r.tituloNum.slice(0, 40)}»)`);
      }
      const m = r.label.match(/: (\d+) nuevos/);
      if (m) ok(Number.isInteger(Number(m[1])), `${q}: la cuenta de la campana no es un entero`);
    } finally { await ctx.close(); }
  }
} finally { await navegador.close(); }
console.log(`${fallos.length ? '✘' : '✔'} L-37: ${comprobados} comprobaciones${fallos.length ? ' · ' + fallos.join(' · ') : ''}`);
process.exit(fallos.length ? 1 : 0);
