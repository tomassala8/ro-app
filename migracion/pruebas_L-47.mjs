#!/usr/bin/env node
// migracion/pruebas_L-47.mjs · L-47: ⌘K con un Esc, búsqueda por id y alias, catálogo sin «undefined» y tarjetas a 0 sin acción.
// Uso: node migracion/pruebas_L-47.mjs --base http://127.0.0.1:8771 [--volcar]
// Dirección, solo lectura (la paleta solo abre y filtra; no se pulsa ningún resultado):
//   (1) ⌘K / Ctrl+K abre `#paleta`; UN Escape la cierra y el foco vuelve al elemento que lo tenía; con la paleta abierta
//       sobre un diálogo (o el Esc que le sigue) no se cierra nada más (el segundo Esc no actúa);
//   (2) el `id` exacto de una pantalla (`mi-dia`) y el id de una persona dan resultados en `#paleta-lista`;
//   (3) `#/catalogo` no contiene «undefined» ni «[object» en su texto;
//   (4) en seis pantallas con tarjetas (clientes nuevos, incidencias, en rojo, producción, captación y paneles), una tarjeta (`.tile`) con valor 0 que es un `div` (sin href ni alPulsar) no tiene
//       `role=button`, `tabindex` ni puntero «mano». Las tarjetas a 0 que son `button` (filtros «Ver cuáles») no se tocan: filtran
//       a una lista vacía, que es una acción (queda en «Preguntas para Tomás»).
import { chromium } from '../v2/tools/capturas/node_modules/playwright/index.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, v) => (x.startsWith('--') ? [...a, [x.slice(2), v[i + 1]?.startsWith('--') || v[i + 1] === undefined ? true : v[i + 1]]] : a), []));
const base = String(args.base || 'http://127.0.0.1:8771').replace(/\/$/, '');
const fallos = [];
let n = 0;
const ok = (c, t) => { n++; if (!c) fallos.push(t); };

const elegir = await (await fetch(`${base}/api/elegir`)).json();
const activas = (elegir.personas || []).filter((p) => (p.estado || 'activo') === 'activo');
const dir = activas.find((p) => (p.puestos || []).includes('direccion'));
const otra = activas.find((p) => p.id !== dir?.id && (p.puestos || []).includes('account')) || activas.find((p) => p.id !== dir?.id);
ok(!!dir && !!otra, 'falta dirección u otra persona');

const navegador = await chromium.launch();
try {
  const ctx = await navegador.newContext({ viewport: { width: 1366, height: 900 }, locale: 'es-ES', timezoneId: 'Europe/Madrid', reducedMotion: 'reduce' });
  await ctx.clock.setFixedTime(new Date('2026-10-05T07:30:00+02:00'));
  const pg = await ctx.newPage();
  const cargar = async (ruta) => {
    await pg.goto(`${base}/?yo=${dir.id}&hoy=2026-10-05#/${ruta}`, { waitUntil: 'load', timeout: 45_000 });
    await pg.waitForSelector('#main', { timeout: 20_000 }).catch(() => {});
    await pg.waitForTimeout(2500);
  };
  const abierta = () => pg.evaluate(() => { const p = document.querySelector('#paleta'); return !!p && !p.hidden && p.getClientRects().length > 0; });
  try {
    // --- (1) un solo Esc
    await cargar('mi-dia');
    const abrir = async () => {
      for (const tecla of ['Control+K', 'Meta+K']) {
        await pg.keyboard.press(tecla);
        await pg.waitForTimeout(400);
        if (await abierta()) return tecla;
      }
      return null;
    };
    // un elemento enfocable de la carcasa que no sea la paleta: el primero de la cabecera con id o el primer botón visible
    await pg.evaluate(() => {
      const b = [...document.querySelectorAll('header button, nav button, #main button, #main a[href]')].find((x) => x.getClientRects().length && !x.closest('#paleta'));
      if (b) { b.id = b.id || 'foco-l47'; b.focus(); window.__foco47 = b.id; }
    });
    const foco0 = await pg.evaluate(() => document.activeElement?.id || '');
    const tecla = await abrir();
    ok(!!tecla, 'la paleta no se abre ni con Control+K ni con Meta+K');
    if (tecla) {
      ok(await pg.evaluate(() => document.activeElement?.id === 'paleta-q'), '(1) al abrir la paleta el foco no está en su buscador');
      await pg.keyboard.press('Escape');
      await pg.waitForTimeout(400);
      ok(!(await abierta()), '(1) un solo Escape no cierra la paleta');
      const foco1 = await pg.evaluate(() => document.activeElement?.id || '');
      ok(foco0 !== '' && foco1 === foco0, `(1) el foco no vuelve a donde estaba (${foco0 || '—'} → ${foco1 || '—'})`);
      // un segundo Esc no hace nada más (no hay menú ni cajón que se cierre solo): la página sigue en la misma ruta
      const ruta0 = await pg.evaluate(() => location.hash);
      await pg.keyboard.press('Escape');
      await pg.waitForTimeout(300);
      ok((await pg.evaluate(() => location.hash)) === ruta0, '(1) un segundo Escape cambia la ruta');
      // Esc dentro de la paleta no sale por el documento (stopPropagation): un oyente propio no lo ve
      await pg.evaluate(() => { window.__esc47 = 0; document.addEventListener('keydown', (e) => { if (e.key === 'Escape') window.__esc47++; }); });
      await abrir();
      await pg.keyboard.press('Escape');
      await pg.waitForTimeout(300);
      ok((await pg.evaluate(() => window.__esc47)) === 0, '(1) el Escape de la paleta llega también a otros oyentes del documento (cerraría dos cosas)');
      ok(!(await abierta()), '(1) la paleta sigue abierta tras el Escape de la segunda vez');
    }

    // --- (2) búsqueda por id exacto y por id de persona
    await cargar('mi-dia');
    if (await abrir()) {
      const buscar = async (texto) => {
        await pg.fill('#paleta-q', texto);
        await pg.waitForTimeout(600);
        return pg.evaluate(() => [...document.querySelectorAll('#paleta-lista li[role=option]:not(.nada)')].map((li) => li.getAttribute('aria-label') || li.textContent));
      };
      const porId = await buscar('mi-dia');
      if (args.volcar) console.log(`id de pantalla «mi-dia»: ${porId.length} resultados`);
      ok(porId.length > 0 && porId.some((t) => /Pantallas/.test(t)), `(2) «mi-dia» no encuentra la pantalla (${porId.length} resultados)`);
      const porPersona = await buscar(otra.id);
      if (args.volcar) console.log(`id de persona: ${porPersona.length} resultados`);
      ok(porPersona.some((t) => /Personas/.test(t)), `(2) el id de una persona no la encuentra (${porPersona.length} resultados)`);
      await pg.keyboard.press('Escape');
    }

    // --- (3) catálogo
    await cargar('catalogo');
    await pg.waitForTimeout(1000);
    const cat = await pg.evaluate(() => (document.querySelector('#main') || document.body).innerText);
    ok(cat.length > 200, `(3) el catálogo no se pinta (${cat.length} letras)`);
    ok(!/undefined/i.test(cat), '(3) el catálogo contiene «undefined»');
    ok(!/\[object /i.test(cat), '(3) el catálogo contiene «[object …]»');

    // --- (4) tarjetas a 0 sin acción
    let tarjetas0 = 0;
    for (const pant of ['clientes-nuevos', 'incidencias', 'en-rojo', 'produccion', 'captacion', 'paneles']) {
      await cargar(pant);
      const r = await pg.evaluate(() => {
        const malas = []; let ceros = 0, controles = 0;
        for (const t of document.querySelectorAll('#main .tile')) {
          const v = (t.querySelector('.tv')?.textContent || '').trim();
          const esControl = t.tagName === 'A' || t.tagName === 'BUTTON';
          if (esControl) { controles++; if (t.tagName === 'A' && !t.getAttribute('href')) malas.push('enlace sin href'); continue; }
          if (/^0(\D|$)/.test(v)) ceros++;
          const cs = getComputedStyle(t);
          if (t.getAttribute('role') === 'button' || t.hasAttribute('tabindex') || cs.cursor === 'pointer') malas.push(`${t.className.slice(0, 20)} («${v.slice(0, 12)}»)`);
        }
        return { malas, ceros, controles };
      });
      tarjetas0 += r.ceros;
      if (args.volcar) console.log(`${pant}: ${r.ceros} tarjetas a 0 sin acción, ${r.controles} tarjetas con acción`);
      ok(r.malas.length === 0, `(4) ${pant}: tarjetas sin acción que parecen pulsables: ${r.malas.slice(0, 3).join(', ')}`);
    }
    if (args.volcar) console.log(`tarjetas a 0 vistas en total: ${tarjetas0}`);
    ok(tarjetas0 > 0, '(4) ninguna pantalla enseña una tarjeta a 0 sin acción en la copia: la comprobación no vería nada (¿cambió la copia?)');
  } catch (e) { fallos.push(`no cargó (${String(e).slice(0, 140)})`); }
  finally { await ctx.close(); }
} finally { await navegador.close(); }
console.log(`${fallos.length ? '✘' : '✔'} L-47: ${n} comprobaciones${fallos.length ? ' · ' + fallos.join(' · ') : ''}`);
process.exit(fallos.length ? 1 : 0);
