#!/usr/bin/env node
// migracion/pruebas_N-11.mjs · N-11: un hueco en una serie diaria no es un 0.
// Uso:  node migracion/pruebas_N-11.mjs [--base http://127.0.0.1:8771]     (sin --base solo corre la parte de Node)
// (1) Node: `sumarSerie`, `sumarSerieDetalle` y `serieDelPeriodo` de componentes.js con series inventadas.
// (2) Pantalla (con --base): Paneles › Analytics con una serie inventada, completa y con un día quitado (`page.route`):
//     el aviso «Periodo incompleto: falta 1 día de datos» sale solo con el hueco. Sin datos reales.
import { chromium } from '../v2/tools/capturas/node_modules/playwright/index.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, v) => (x.startsWith('--') ? [...a, [x.slice(2), v[i + 1]?.startsWith('--') || v[i + 1] === undefined ? true : v[i + 1]]] : a), []));
const fallos = [];
const ok = (c, t) => { console.log(`  ${c ? '✔' : '✘'} ${t}`); if (!c) fallos.push(t); };
const igual = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// ------------------------------------------------------------------------------------------------ (1) Node
const C = await import('../componentes.js');
const P = { desde: '2026-10-01', hasta: '2026-10-03' };
const hueco = { '2026-10-01': 5, '2026-10-02': null, '2026-10-03': 7 };
const falta = { '2026-10-01': 5, '2026-10-03': 7 };
const completa = { '2026-10-01': 5, '2026-10-02': 0, '2026-10-03': 7 };

ok(igual(C.sumarSerieDetalle(hueco, P), { total: 12, dias: 3, faltan: 1, completo: false }), 'serie con un null: total 12, faltan 1, incompleta');
ok(igual(C.sumarSerieDetalle(falta, P), { total: 12, dias: 3, faltan: 1, completo: false }), 'serie con un día ausente: igual');
ok(igual(C.sumarSerieDetalle(completa, P), { total: 12, dias: 3, faltan: 0, completo: true }), 'serie completa (con un 0 de verdad): faltan 0, completa');
ok(C.sumarSerie(hueco, P) === 12 && C.sumarSerie(completa, P) === 12, 'sumarSerie sigue devolviendo solo el total');
ok(C.sumarSerie({}, P) === null && C.sumarSerie(null, P) === null, 'sin datos, null (no 0)');
const listas = { '2026-10-01': [1, null, 3], '2026-10-02': [2, null, 4], '2026-10-03': null };
ok(igual(C.sumarSerie(listas, P), [3, null, 7]), 'listas: la columna sin ningún dato sale null, no 0');
ok(igual(C.sumarSerieDetalle(listas, P), { total: [3, null, 7], dias: 3, faltan: 1, completo: false }), 'listas: el día sin lista cuenta como falta');
ok(igual(C.sumarSerie({ '2026-10-02': 4 }, P), 4) && C.sumarSerie({ '2026-09-01': 4 }, P) === null, 'fuera del periodo no cuenta');
const y = (s, o) => C.serieDelPeriodo(s, P, null, o).map((p) => p.y);
ok(igual(y(hueco), [5, null, 7]) && igual(y(falta), [5, 0, 7]), 'serieDelPeriodo sin opciones: como siempre (un null sigue null; el día sin filas de una serie de sucesos = 0)');
ok(igual(y(hueco, { huecos: true }), [5, null, 7]) && igual(y(falta, { huecos: true }), [5, null, 7]), 'serieDelPeriodo con huecos: null en el día sin dato');
ok(igual(y(completa, { huecos: true }), [5, 0, 7]), 'con huecos, un 0 de verdad sigue siendo 0');
ok(igual(C.serieDelPeriodo({ '2026-10-01': [1, 2], '2026-10-02': [3, null], '2026-10-03': [5, 6] }, P, 1, { huecos: true }).map((p) => p.y), [2, null, 6]), 'con huecos y columna: null dentro de la lista también es hueco');

// ------------------------------------------------------------------------------------------------ (2) pantalla
if (args.base) {
  const base = String(args.base).replace(/\/$/, '');
  const elegir = await (await fetch(`${base}/api/elegir`)).json();
  const direccion = (elegir.personas || []).find((p) => (p.puestos || []).includes('direccion'))?.id;
  const navegador = await chromium.launch();
  const sintetica = (quitar) => {
    const s = {};
    for (let d = new Date('2026-08-01T12:00:00Z'); d <= new Date('2026-10-02T12:00:00Z'); d = new Date(d.getTime() + 86400000)) {
      const k = d.toISOString().slice(0, 10);
      if (k !== quitar) s[k] = [10, 5, 20, 12, 3, 40, 60, 900];
    }
    return s;
  };
  async function leer(quitar) {
    const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 }, locale: 'es-ES', timezoneId: 'Europe/Madrid', reducedMotion: 'reduce' });
    const pagina = await ctx.newPage();
    try {
      await pagina.route('**/api/modulo/paneles/ga4/*', async (r) => {
        const resp = await r.fetch();
        let j;
        try { j = await resp.json(); } catch { return r.fulfill({ response: resp }); }
        if (j?.filas?.[0]) { j.filas[0].serie = sintetica(quitar); j.filas[0].periodos = undefined; }
        return r.fulfill({ response: resp, json: j });
      });
      await pagina.goto(`${base}/?yo=${direccion}&hoy=2026-10-03#/paneles`, { waitUntil: 'load', timeout: 45_000 });
      await pagina.waitForTimeout(4000);
      await pagina.locator('[role=tab]', { hasText: 'Analytics' }).first().click({ timeout: 15_000 });
      await pagina.waitForTimeout(2500);
      return await pagina.evaluate(() => (document.querySelector('#main') || document.body).innerText);
    } finally {
      await ctx.close();
    }
  }
  const entera = await leer(null);
  const rota = await leer('2026-09-20');
  ok(/por día/.test(entera) && !/Periodo incompleto/.test(entera), 'paneles › Analytics con la serie completa: sin aviso de periodo incompleto');
  ok(/Periodo incompleto: falta 1 día de datos/.test(rota), 'paneles › Analytics con un día quitado: «Periodo incompleto: falta 1 día de datos»');
  await navegador.close();
}

if (fallos.length) { console.log(`✘ N-11: ${fallos.length} fallos`); process.exit(1); }
console.log('✔ N-11');
