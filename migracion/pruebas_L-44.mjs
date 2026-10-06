#!/usr/bin/env node
// migracion/pruebas_L-44.mjs · L-44: los vacíos no desbordan a 390, 640 ni 1366 px.
// Uso: node migracion/pruebas_L-44.mjs --base http://127.0.0.1:8771 [--volcar]
// Un setter y dirección, en `agenda`, `mi-dia`, `incidencias` y `clientes-nuevos`, a 390×844, 640×900 y 1366×768:
//   · `documentElement.scrollWidth <= innerWidth` (sin desborde horizontal);
//   · ningún `.vacio` / `.vacio-g` más ancho que la ventana;
//   · dentro de `#main`, `vacio()`, `estadoVacio()` y `vacioLinea()` con un título de 60 caracteres sin espacios no desbordan.
// Solo lectura. Solo recuentos y nombres de pantalla en la salida.
import { chromium } from '../v2/tools/capturas/node_modules/playwright/index.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, v) => (x.startsWith('--') ? [...a, [x.slice(2), v[i + 1]?.startsWith('--') || v[i + 1] === undefined ? true : v[i + 1]]] : a), []));
const base = String(args.base || 'http://127.0.0.1:8771').replace(/\/$/, '');
const PANTALLAS = ['agenda', 'mi-dia', 'incidencias', 'clientes-nuevos'];
const VISTAS = [[390, 844], [640, 900], [1366, 768]];
const fallos = [];
let n = 0;
const ok = (c, t) => { n++; if (!c) fallos.push(t); };

const elegir = await (await fetch(`${base}/api/elegir`)).json();
const activas = (elegir.personas || []).filter((p) => (p.estado || 'activo') === 'activo');
const dir = activas.find((p) => (p.puestos || []).includes('direccion'));
const setter = activas.find((p) => (p.puestos || []).includes('setters') && !(p.puestos || []).includes('direccion'));
ok(!!dir && !!setter, 'falta dirección o un setter');

const medir = () => {
  const ancho = window.innerWidth;
  const vacios = [...document.querySelectorAll('.vacio, .vacio-g, .vacio-linea')].map((e) => Math.round(e.getBoundingClientRect().width));
  return { scroll: document.documentElement.scrollWidth, ancho, anchoMax: vacios.length ? Math.max(...vacios) : 0, nVacios: vacios.length };
};

const navegador = await chromium.launch();
try {
  for (const [que, p] of [['dirección', dir], ['setter', setter]].filter(([, p]) => p)) {
    for (const [w, h] of VISTAS) {
      const ctx = await navegador.newContext({ viewport: { width: w, height: h }, locale: 'es-ES', timezoneId: 'Europe/Madrid', reducedMotion: 'reduce' });
      await ctx.clock.setFixedTime(new Date('2026-10-05T07:30:00+02:00'));
      const pg = await ctx.newPage();
      try {
        for (const pant of PANTALLAS) {
          try {
            await pg.goto(`${base}/?yo=${p.id}&hoy=2026-10-05#/${pant}`, { waitUntil: 'load', timeout: 45_000 });
            await pg.waitForSelector('#main', { timeout: 20_000 }).catch(() => {});
            await pg.waitForTimeout(3000);
            const m = await pg.evaluate(medir);
            if (args.volcar) console.log(`${que} ${w}px ${pant}: scroll ${m.scroll} · vacíos ${m.nVacios} (máx ${m.anchoMax})`);
            ok(m.scroll <= m.ancho, `${que} ${w}px ${pant}: desborda (${m.scroll} > ${m.ancho})`);
            ok(m.anchoMax <= m.ancho, `${que} ${w}px ${pant}: un vacío mide ${m.anchoMax} > ${m.ancho}`);
          } catch (e) { fallos.push(`${que} ${w}px ${pant}: no cargó (${String(e).slice(0, 60)})`); }
        }
        // Título largo sin espacios en los tres componentes de vacío.
        await pg.goto(`${base}/?yo=${p.id}&hoy=2026-10-05#/mi-dia`, { waitUntil: 'load', timeout: 45_000 });
        await pg.waitForTimeout(2500);
        const largo = await pg.evaluate(async () => {
          const c = await import('/componentes.js');
          const larga = 'A'.repeat(60);
          const caja = document.createElement('div');
          caja.id = 'prueba-l44';
          const piezas = [
            c.vacio({ icono: 'info', titulo: larga, texto: larga + ' ' + larga }),
            c.estadoVacio({ titulo: larga, porque: larga, que_hacer: larga }),
            c.vacioLinea(larga),
          ];
          for (const x of piezas) if (x) caja.append(x);
          (document.querySelector('#main') || document.body).append(caja);
          await new Promise((r) => setTimeout(r, 300));
          return { scroll: document.documentElement.scrollWidth, ancho: window.innerWidth, hijos: piezas.filter(Boolean).length };
        });
        ok(largo.hijos === 3, `${que} ${w}px: faltan componentes de vacío (${largo.hijos} de 3)`);
        ok(largo.scroll <= largo.ancho, `${que} ${w}px: un vacío con título de 60 letras seguidas desborda (${largo.scroll} > ${largo.ancho})`);
      } finally { await ctx.close(); }
    }
  }
} finally { await navegador.close(); }
console.log(`${fallos.length ? '✘' : '✔'} L-44: ${n} comprobaciones${fallos.length ? ' · ' + fallos.join(' · ') : ''}`);
process.exit(fallos.length ? 1 : 0);
