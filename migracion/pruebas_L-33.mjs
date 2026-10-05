#!/usr/bin/env node
// migracion/pruebas_L-33.mjs · L-33: el tile de reunión de la ficha usa el criterio de la verdad única («sin reunión el mes pasado»),
// con el mismo color que «En rojo» (detalle del cliente), y no el umbral de 30/35 días.
// Uso: node migracion/pruebas_L-33.mjs --base http://127.0.0.1:8771
// No toca datos: el navegador recibe la verdad real, y en el caso inyectado cambia `sin_reunion_mes_pasado` de un cliente (`page.route`).
// Solo se miran estados y textos; ningún dato real va al repo.
import { chromium } from '../v2/tools/capturas/node_modules/playwright/index.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, v) => (x.startsWith('--') ? [...a, [x.slice(2), v[i + 1]?.startsWith('--') || v[i + 1] === undefined ? true : v[i + 1]]] : a), []));
const base = String(args.base || 'http://127.0.0.1:8771').replace(/\/$/, '');
const elegir = await (await fetch(`${base}/api/elegir`)).json();
const direccion = (elegir.personas || []).find((p) => (p.puestos || []).includes('direccion'));
const navegador = await chromium.launch();
const fallos = [];

/** Lee, para un cliente, el tile de reunión de la ficha y el de En rojo. `forzar`: true/false cambia la verdad de ese cliente. */
async function leer(idPedido, forzar) {
  const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 }, locale: 'es-ES', timezoneId: 'Europe/Madrid', reducedMotion: 'reduce' });
  await ctx.clock.setFixedTime(new Date('2026-10-05T07:30:00+02:00'));
  const pagina = await ctx.newPage();
  let elegido = null;
  let final = null;
  await pagina.route('**/api/modulo/verdad/clientes*', async (ruta) => {
    const resp = await ruta.fetch();
    const v = await resp.json();
    const lista = v.clientes || [];
    const c = idPedido ? lista.find((x) => x.cliente_id === idPedido)
      : (lista.find((x) => x.sin_reunion_mes_pasado === true && x.ultima_reunion) || lista.find((x) => x.sin_reunion_mes_pasado === true));
    elegido = c?.cliente_id || null;
    if (c && forzar !== undefined) { c.sin_reunion_mes_pasado = forzar; c.reunion_estado = forzar ? 'sin_reunion' : 'ok'; }
    if (c) final = { sin: c.sin_reunion_mes_pasado === true, ult: !!c.ultima_reunion };
    await ruta.fulfill({ response: resp, json: v });
  });
  const tileDe = (etiqueta) => pagina.evaluate((e) => {
    const t = [...document.querySelectorAll('.tile')].find((x) => (x.innerText || '').includes(e));
    return t ? { clase: t.className, texto: t.innerText.replace(/\s+/g, ' ').trim() } : null;
  }, etiqueta);
  const esperar = (e) => pagina.waitForFunction((x) => [...document.querySelectorAll('.tile')].some((t) => (t.innerText || '').includes(x)), e, { timeout: 25_000 }).catch(() => {});
  try {
    await pagina.goto(`${base}/?yo=${direccion.id}&hoy=2026-10-05#/en-rojo`, { waitUntil: 'load', timeout: 45_000 });
    await pagina.waitForTimeout(1500);
    const id = elegido || idPedido;
    if (!id) return { id: null };
    await pagina.evaluate((x) => { location.hash = `#/en-rojo/${x}`; }, id);
    await esperar('Última reunión');
    const rojo = await tileDe('Última reunión');
    await pagina.evaluate((x) => { location.hash = `#/ficha/${x}/resumen`; }, id);
    await esperar('Días sin reunión');
    await pagina.waitForTimeout(800);
    const ficha = await tileDe('Días sin reunión');
    await pagina.evaluate((x) => { location.hash = `#/ficha/${x}/comunicacion`; }, id);
    await esperar('Reuniones ·');
    await pagina.waitForTimeout(800);
    const fichaReunion = await tileDe('Reuniones ·');
    return { id, rojo, ficha, fichaReunion, final };
  } finally { await ctx.close(); }
}

const color = (t) => (t?.clase || '').split(/\s+/).find((c) => ['rojo', 'ambar', 'verde', 'gris'].includes(c)) || 'neutro';

async function caso(nombre, idPedido, forzar, texto) {
  const r = await leer(idPedido, forzar);
  if (!r.id || !r.rojo || !r.ficha || !r.fichaReunion) { fallos.push(`${nombre}: no se encontró el tile (id ${r.id ? 'sí' : 'no'}, En rojo ${r.rojo ? 'sí' : 'no'}, Resumen ${r.ficha ? 'sí' : 'no'}, pestaña Comunicación ${r.fichaReunion ? 'sí' : 'no'})`); return r; }
  if (args.volcar) console.log(`    [${r.ficha.texto}]`);
  console.log(`  · ${nombre}: En rojo ${color(r.rojo)} · Resumen ${color(r.ficha)} · Comunicación ${color(r.fichaReunion)}`);
  if (color(r.rojo) !== color(r.ficha)) fallos.push(`${nombre}: el Resumen pinta ${color(r.ficha)} y En rojo ${color(r.rojo)}`);
  // En la pestaña Comunicación el valor es el recuento de reuniones (puede ser 0 y aun así pintar): se compara con la verdad, no con En rojo.
  const esperado = r.final.sin ? 'ambar' : r.final.ult ? 'verde' : 'neutro';
  if (color(r.fichaReunion) !== esperado) fallos.push(`${nombre}: la pestaña Comunicación pinta ${color(r.fichaReunion)} y la verdad pide ${esperado}`);
  if (texto && !texto.test(r.ficha.texto)) fallos.push(`${nombre}: el tile de la ficha no dice ${texto}: «${r.ficha.texto.slice(0, 120)}»`);
  if (/rojo > 35 días/.test(r.ficha.texto) && forzar !== false) fallos.push(`${nombre}: la ficha sigue hablando del umbral de 35 días`);
  return r;
}

// 1 · cliente sin reunión el mes pasado en la verdad real.
const a = await caso('sin reunión el mes pasado (real)', null, undefined, /sin reunión el mes pasado/i);
// 2 · el mismo cliente con la verdad cambiada a «con reunión»: los dos sitios vuelven a coincidir (verde).
if (a.id) await caso('con reunión el mes pasado (inyectado)', a.id, false, null);
// 3 · un cliente con reunión en la verdad real, forzado a «sin reunión»: ámbar en los dos.
const b = await (async () => {
  const v = await (await fetch(`${base}/api/modulo/verdad/clientes`, { headers: { 'X-RO-Yo': direccion.id } })).json();
  return (v.clientes || []).find((x) => x.sin_reunion_mes_pasado === false && x.reunion_estado === 'ok' && x.ultima_reunion);
})();
if (b) await caso('sin reunión (inyectado sobre un cliente con reunión)', b.cliente_id, true, /sin reunión el mes pasado/i);
else fallos.push('no hay cliente con reunión en la verdad: el caso inyectado no mide nada');

await navegador.close();
if (fallos.length) { console.log(`✘ L-33: ${fallos.length} fallos`); fallos.forEach((f) => console.log(`  - ${f}`)); process.exit(1); }
console.log('✔ L-33: la ficha y En rojo cuentan igual la reunión');
