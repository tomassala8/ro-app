#!/usr/bin/env node
// migracion/pruebas_L-40.mjs · L-40: «Más» en el menú de escritorio para los 21 puestos.
// Uso: node migracion/pruebas_L-40.mjs --base http://127.0.0.1:8771
// Para UNA persona de cada puesto (la que tiene menos puestos), en escritorio (1440×900) y `#/mi-dia`:
//  · si el menú tiene más de 12 pantallas: entre 8 y 12 fuera de «Más» (`[data-ro-mas]`) y el resto dentro;
//  · si tiene 12 o menos: todas fuera y sin «Más»;
//  · ninguna pantalla se pierde: `nav a[data-id]` total (dentro y fuera de «Más») = el total de antes del cambio (`--grabar` lo guarda en ~/RO_MIGRACION/L-40_menu_antes.json);
//  · la pantalla actual, si está en «Más», deja el `details` abierto;
//  · en móvil (390×844) el menú se agrupa igual que en escritorio (es la misma función; no se añade nada solo de móvil).
// Solo lectura. Solo salen conteos e ids de puestos; nada de datos reales.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { chromium } from '../v2/tools/capturas/node_modules/playwright/index.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, v) => (x.startsWith('--') ? [...a, [x.slice(2), v[i + 1]?.startsWith('--') || v[i + 1] === undefined ? true : v[i + 1]]] : a), []));
const base = String(args.base || 'http://127.0.0.1:8771').replace(/\/$/, '');
// Total de pantallas del menú por puesto ANTES del cambio (`--grabar` lo escribe; después se compara).
const ficheroAntes = path.join(os.homedir(), 'RO_MIGRACION', 'L-40_menu_antes.json');
const antes = !args.grabar && fs.existsSync(ficheroAntes) ? JSON.parse(fs.readFileSync(ficheroAntes, 'utf8')) : null;
const totales = {};
const fallos = [];
let comprobados = 0;
const ok = (c, t) => { comprobados++; if (!c) fallos.push(t); };

const elegir = await (await fetch(`${base}/api/elegir`)).json();
const personas = (elegir.personas || []).filter((p) => (p.estado || 'activo') === 'activo');
const puestos = [...new Set(personas.flatMap((p) => p.puestos || []))].sort();
ok(puestos.length === 21, `hay ${puestos.length} puestos con persona y deberían ser 21`);
const elegida = (puesto) => personas
  .filter((p) => (p.puestos || []).includes(puesto))
  .sort((a, b) => (a.puestos || []).length - (b.puestos || []).length)[0];

const tomarMenu = () => {
  const nav = document.querySelector('#nav');
  const todos = [...(nav?.querySelectorAll('a[data-id]') || [])];
  const mas = nav?.querySelector('[data-ro-mas]');
  const dentro = new Set(mas ? [...mas.querySelectorAll('a[data-id]')] : []);
  return {
    total: todos.length,
    fuera: todos.filter((a) => !dentro.has(a)).length,
    dentro: dentro.size,
    hayMas: !!mas,
    masAbierto: !!mas?.open,
    actualDentro: !!mas?.querySelector('a[aria-current]'),
    ids: todos.map((a) => a.dataset.id),
  };
};

const navegador = await chromium.launch();
const vistos = [];
try {
  for (const puesto of puestos) {
    const p = elegida(puesto);
    if (!p) { console.log(`· ${puesto}: sin persona, se salta`); continue; }
    const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 }, locale: 'es-ES', timezoneId: 'Europe/Madrid', reducedMotion: 'reduce' });
    await ctx.clock.setFixedTime(new Date('2026-10-05T07:30:00+02:00'));
    const pagina = await ctx.newPage();
    let m;
    try {
      await pagina.goto(`${base}/?yo=${p.id}&hoy=2026-10-05#/mi-dia`, { waitUntil: 'load', timeout: 45_000 });
      await pagina.waitForSelector('#nav a[data-id]', { timeout: 25_000 }).catch(() => {});
      await pagina.waitForTimeout(1500);
      m = await pagina.evaluate(tomarMenu);
      vistos.push(`${puesto}:${m.fuera}+${m.dentro}`);
      totales[puesto] = m.total;
      if (antes) ok(antes[puesto] === m.total, `${puesto}: el menú tiene ${m.total} pantallas y antes tenía ${antes[puesto]}`);
      if (m.total > 12) {
        ok(m.hayMas, `${puesto}: ${m.total} pantallas y sin «Más»`);
        ok(m.fuera <= 12 && m.fuera >= 8, `${puesto}: ${m.fuera} pantallas fuera de «Más» (deben ser de 8 a 12)`);
        ok(m.dentro === m.total - m.fuera, `${puesto}: pantallas dentro de «Más» mal contadas`);
      } else {
        ok(!m.hayMas && m.fuera === m.total, `${puesto}: ${m.total} pantallas y debería ir todo fuera, sin «Más»`);
      }
      // La pantalla actual, si cae dentro de «Más», deja el details abierto.
      if (m.hayMas && m.ids.length) {
        const dentroIds = await pagina.evaluate(() => [...document.querySelectorAll('#nav [data-ro-mas] a[data-id]')].map((a) => a.dataset.id));
        if (dentroIds.length) {
          await pagina.evaluate((id) => { location.hash = `#/${id}`; }, dentroIds[0]);
          await pagina.waitForTimeout(1200);
          const a = await pagina.evaluate(tomarMenu);
          ok(a.actualDentro ? a.masAbierto : true, `${puesto}: la pantalla actual está en «Más» y el menú no se abre`);
        }
      }
    } finally { await ctx.close(); }
    // Móvil: el menú no cambia (sin «Más»).
    const movil = await navegador.newContext({ viewport: { width: 390, height: 844 }, locale: 'es-ES', timezoneId: 'Europe/Madrid', reducedMotion: 'reduce' });
    await movil.clock.setFixedTime(new Date('2026-10-05T07:30:00+02:00'));
    const pm = await movil.newPage();
    try {
      await pm.goto(`${base}/?yo=${p.id}&hoy=2026-10-05#/mi-dia`, { waitUntil: 'load', timeout: 45_000 });
      await pm.waitForSelector('#nav a[data-id]', { state: 'attached', timeout: 25_000 }).catch(() => {});
      await pm.waitForTimeout(1000);
      const mm = await pm.evaluate(tomarMenu);
      ok(mm.total === m.total, `${puesto}: en móvil el menú tiene ${mm.total} pantallas y en escritorio ${m.total}`);
      ok(mm.hayMas === m.hayMas && mm.fuera === m.fuera, `${puesto}: el menú de móvil se agrupa distinto que el de escritorio`);
    } finally { await movil.close(); }
  }
} finally { await navegador.close(); }
if (args.grabar) {
  fs.mkdirSync(path.dirname(ficheroAntes), { recursive: true });
  fs.writeFileSync(ficheroAntes, JSON.stringify(totales, null, 1));
  console.log(`· totales por puesto grabados en ${ficheroAntes}`);
} else if (!antes) console.log('· sin totales de antes (~/RO_MIGRACION/L-40_menu_antes.json): no se compara que no se pierda ninguna pantalla');
console.log(`fuera+dentro por puesto: ${vistos.join(' ')}`);
console.log(`${fallos.length ? '✘' : '✔'} L-40: ${comprobados} comprobaciones${fallos.length ? ' · ' + fallos.join(' · ') : ''}`);
process.exit(fallos.length ? 1 : 0);
