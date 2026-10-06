#!/usr/bin/env node
// migracion/pruebas_L-46.mjs · L-46: las filas pulsables que no son botón se activan con teclado (Enter y Espacio).
// Uso: node migracion/pruebas_L-46.mjs --base http://127.0.0.1:8771 [--volcar]
// Solo lectura (dirección en `#/horas` y `#/chat-equipo`, y una fila de prueba que no toca la base).
//   · Estática: `horas.js` y `chat_equipo.js` sin `h('div'|'tr'|'li'|'span', … on: { click` ni `addEventListener('click'`
//     propios; `filaPulsable` se define una sola vez, en `componentes.js`, y las dos pantallas la importan.
//   · Unitaria (navegador): `filaPulsable` pone `role=button` y `tabindex=0`; Enter y Espacio sobre la fila llaman a `ir`
//     una vez y no mueven la página; sobre un botón de dentro no la activan; el clic en un enlace de dentro tampoco.
//   · Pantalla: en `#/horas` (Todas las personas) y `#/chat-equipo`, todo elemento con puntero «mano» propio (no heredado)
//     que no sea a, button, input, select, summary o label tiene `role=button` y `tabindex=0`; y en la primera fila de
//     Horas, Espacio cambia de pestaña (la acción sí se dispara).
import { readFileSync } from 'node:fs';
import { chromium } from '../v2/tools/capturas/node_modules/playwright/index.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, v) => (x.startsWith('--') ? [...a, [x.slice(2), v[i + 1]?.startsWith('--') || v[i + 1] === undefined ? true : v[i + 1]]] : a), []));
const base = String(args.base || 'http://127.0.0.1:8771').replace(/\/$/, '');
const fallos = [];
let n = 0;
const ok = (c, t) => { n++; if (!c) fallos.push(t); };

// ---------------------------------------------------------------- estática
const leer = (f) => readFileSync(new URL(`../${f}`, import.meta.url), 'utf8');
const horas = leer('modulos/horas.js');
const chat = leer('modulos/chat_equipo.js');
const comp = leer('componentes.js');
for (const [nombre, src] of [['horas.js', horas], ['chat_equipo.js', chat]]) {
  // las propiedades del propio h('div', { … on: { click … } }) (hasta un nivel de llaves dentro, p. ej. `style`), no un botón hijo
  ok(!/h\('(div|tr|li|span)', \{(?:[^{}]|\{[^{}]*\})*on: \{ ?click/.test(src), `${nombre}: queda un h('div'|'tr'|'li'|'span') con on: { click }`);
  ok(!/\.addEventListener\('click'/.test(src), `${nombre}: queda un addEventListener('click') propio (usa filaPulsable)`);
  ok(/import \{[^}]*\bfilaPulsable\b[^}]*\} from '\.\.\/componentes\.js'/.test(src), `${nombre}: no importa filaPulsable de componentes.js`);
  ok(!/^function filaPulsable\b/m.test(src), `${nombre}: define su propia filaPulsable`);
}
ok((comp.match(/export function filaPulsable\b/g) || []).length === 1, 'filaPulsable no está una sola vez exportada en componentes.js');

// ---------------------------------------------------------------- navegador
const elegir = await (await fetch(`${base}/api/elegir`)).json();
const activas = (elegir.personas || []).filter((p) => (p.estado || 'activo') === 'activo');
const dir = activas.find((p) => (p.puestos || []).includes('direccion'));
ok(!!dir, 'falta una persona de dirección');

const sinRol = () => {
  const NATIVOS = new Set(['A', 'BUTTON', 'INPUT', 'SELECT', 'SUMMARY', 'LABEL', 'TEXTAREA', 'OPTION']);
  const raiz = document.querySelector('#main') || document.body;
  const malas = [];
  for (const el of raiz.querySelectorAll('*')) {
    if (NATIVOS.has(el.tagName) || el.closest('a, button, summary, label')) continue;
    // las filas de `tablaDensa`/`tablaApilable` son `tr` con tabindex=0 y ya atienden Enter y Espacio: un role=button las sacaría de la tabla
    if (el.tagName === 'TR' && el.tabIndex === 0) continue;
    const cs = getComputedStyle(el);
    if (cs.cursor !== 'pointer') continue;
    const padre = el.parentElement && getComputedStyle(el.parentElement).cursor;
    if (padre === 'pointer') continue; // heredado de la fila
    if (cs.display === 'none' || !el.getClientRects().length) continue;
    if (el.getAttribute('role') === 'button' && el.tabIndex === 0) continue;
    malas.push(`${el.tagName.toLowerCase()}.${String(el.className || '').slice(0, 24)}[role=${el.getAttribute('role')}][tabindex=${el.getAttribute('tabindex')}]`);
  }
  return malas;
};

const navegador = await chromium.launch();
try {
  const ctx = await navegador.newContext({ viewport: { width: 1366, height: 900 }, locale: 'es-ES', timezoneId: 'Europe/Madrid', reducedMotion: 'reduce' });
  await ctx.clock.setFixedTime(new Date('2026-10-05T07:30:00+02:00'));
  const pg = await ctx.newPage();
  try {
    // --- unitaria
    await pg.goto(`${base}/?yo=${dir.id}&hoy=2026-10-05#/horas`, { waitUntil: 'load', timeout: 45_000 });
    await pg.waitForSelector('#main', { timeout: 20_000 }).catch(() => {});
    await pg.waitForTimeout(2500);
    await pg.evaluate(async () => {
      const c = await import('/componentes.js');
      window.__n46 = { fila: 0, interior: 0, enlace: 0 };
      const boton = document.createElement('button'); boton.type = 'button'; boton.id = 'b46'; boton.textContent = 'dentro';
      const enlace = document.createElement('a'); enlace.id = 'a46'; enlace.href = '#/horas'; enlace.textContent = 'enlace';
      boton.addEventListener('click', () => { window.__n46.interior++; });
      const fila = document.createElement('div'); fila.id = 'f46'; fila.append('Fila ', boton, ' ', enlace);
      c.filaPulsable(fila, () => { window.__n46.fila++; });
      (document.querySelector('#main') || document.body).prepend(fila);
    });
    const attrs = await pg.evaluate(() => { const f = document.getElementById('f46'); return { role: f.getAttribute('role'), tab: f.tabIndex }; });
    ok(attrs.role === 'button' && attrs.tab === 0, `filaPulsable: role=${attrs.role} tabindex=${attrs.tab}`);
    await pg.focus('#f46');
    const y0 = await pg.evaluate(() => window.scrollY);
    await pg.keyboard.press('Space');
    let c = await pg.evaluate(() => window.__n46.fila);
    ok(c === 1, `Espacio sobre la fila: ${c} activaciones (esperaba 1)`);
    ok((await pg.evaluate(() => window.scrollY)) === y0, 'Espacio sobre la fila mueve la página');
    await pg.keyboard.press('Enter');
    c = await pg.evaluate(() => window.__n46.fila);
    ok(c === 2, `Enter sobre la fila: ${c} activaciones en total (esperaba 2)`);
    await pg.focus('#b46');
    await pg.keyboard.press('Space');
    const r = await pg.evaluate(() => window.__n46);
    ok(r.fila === 2, `Espacio sobre el botón de dentro activa la fila (${r.fila})`);
    ok(r.interior === 1, `Espacio sobre el botón de dentro no lo pulsa a él (${r.interior})`);
    await pg.click('#a46');
    ok((await pg.evaluate(() => window.__n46.fila)) === 2, 'el clic en un enlace de dentro activa la fila');

    // --- Horas: filas de «Todas las personas»
    await pg.goto(`${base}/?yo=${dir.id}&hoy=2026-10-05#/horas`, { waitUntil: 'load', timeout: 45_000 });
    await pg.waitForSelector('#main', { timeout: 20_000 }).catch(() => {});
    await pg.waitForTimeout(3000);
    // las listas de la primera pestaña están dentro de un «Qué es…» plegado: se despliega (solo cambia la vista)
    await pg.evaluate(() => document.querySelectorAll('#main details').forEach((d) => { d.open = true; }));
    await pg.waitForTimeout(300);
    const filas = [];
    for (const f of await pg.$$('li[aria-label^="Ver las horas de"]')) if (await f.isVisible()) filas.push(f);
    if (args.volcar) console.log(`horas: ${filas.length} filas pulsables a la vista`);
    ok(filas.length > 0, 'horas: no hay ninguna fila «Ver las horas de …» a la vista (¿cambió la pantalla?)');
    if (filas.length) {
      const f0 = filas[0];
      ok((await f0.getAttribute('role')) === 'button', 'horas: la fila no tiene role=button');
      ok((await f0.getAttribute('tabindex')) === '0', 'horas: la fila no tiene tabindex=0');
      const antes = await pg.evaluate(() => document.querySelector('[role=tab][aria-selected=true]')?.textContent?.trim() || '');
      await f0.focus();
      await pg.keyboard.press('Space');
      await pg.waitForTimeout(700);
      const despues = await pg.evaluate(() => document.querySelector('[role=tab][aria-selected=true]')?.textContent?.trim() || '');
      ok(despues !== antes, `horas: Espacio sobre la fila no cambió de pestaña (${antes} → ${despues})`);
      await pg.goBack().catch(() => {});
    }
    // sin pulsables sin rol, en la pestaña en la que se queda
    const m1 = await pg.evaluate(sinRol);
    ok(m1.length === 0, `horas: ${m1.length} elementos con puntero y sin role=button/tabindex: ${m1.slice(0, 4).join(', ')}`);

    // --- Chat del equipo (lista de canales, búsqueda)
    await pg.goto(`${base}/?yo=${dir.id}&hoy=2026-10-05#/chat-equipo`, { waitUntil: 'load', timeout: 45_000 });
    await pg.waitForSelector('#main', { timeout: 20_000 }).catch(() => {});
    await pg.waitForTimeout(3000);
    const m2 = await pg.evaluate(sinRol);
    ok(m2.length === 0, `chat-equipo: ${m2.length} elementos con puntero y sin role=button/tabindex: ${m2.slice(0, 4).join(', ')}`);
  } catch (e) { fallos.push(`no cargó (${String(e).slice(0, 120)})`); }
  finally { await ctx.close(); }
} finally { await navegador.close(); }
console.log(`${fallos.length ? '✘' : '✔'} L-46: ${n} comprobaciones${fallos.length ? ' · ' + fallos.join(' · ') : ''}`);
process.exit(fallos.length ? 1 : 0);
