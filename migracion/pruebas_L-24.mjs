#!/usr/bin/env node
// migracion/pruebas_L-24.mjs · L-24: entrar sin acceso o con la app caída da un mensaje claro, sin nombres ni órdenes de terminal.
// Uso: node migracion/pruebas_L-24.mjs --base http://127.0.0.1:8771
// (1) una persona que no existe: el título deja de ser «Cargando…» y sale «No tienes acceso» (o, si el servidor la trata
//     como sin sesión, el selector de personas); nunca texto técnico;
// (2) la API de sesión rechaza la conexión: «La app no responde» y sin «Cargando…»;
// (3) en los dos mensajes de error: «operaciones» y ningún nombre de persona.
// Solo lectura. Ningún dato real va al repo ni a la salida.
import { chromium } from '../v2/tools/capturas/node_modules/playwright/index.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, v) => (x.startsWith('--') ? [...a, [x.slice(2), v[i + 1]?.startsWith('--') || v[i + 1] === undefined ? true : v[i + 1]]] : a), []));
const base = String(args.base || 'http://127.0.0.1:8771').replace(/\/$/, '');
const fallos = [];
let comprobados = 0;
const ok = (c, t) => { comprobados++; if (!c) fallos.push(t); };
const TECNICO = /python3|servir\.py|traceback|localhost|127\.0\.0\.1|terminal/i;

const elegir = await (await fetch(`${base}/api/elegir`)).json();
const nombres = [...new Set((elegir.personas || []).flatMap((p) => [p.alias, p.nombre, String(p.nombre || '').split(' ')[0]]).filter((n) => n && String(n).length > 2))];

const navegador = await chromium.launch();
async function entrar(url, preparar) {
  const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 }, locale: 'es-ES', timezoneId: 'Europe/Madrid', reducedMotion: 'reduce' });
  const pagina = await ctx.newPage();
  try {
    if (preparar) await preparar(pagina);
    await pagina.goto(url, { waitUntil: 'load', timeout: 45_000 });
    await pagina.waitForFunction(() => (document.querySelector('#titulo')?.textContent || '').trim() !== 'Cargando…' || document.querySelector('#elegir'),
      null, { timeout: 5_000 }).catch(() => {});
    return await pagina.evaluate(() => ({
      titulo: (document.querySelector('#titulo')?.textContent || '').trim(),
      selector: !!document.querySelector('#elegir'),
      texto: document.body.innerText,
      main: (document.querySelector('#main') || document.body).innerText,
    }));
  } finally { await ctx.close(); }
}
try {
  // (1) persona desconocida
  const a = await entrar(`${base}/?yo=persona_que_no_existe_l24`);
  ok(a.titulo !== 'Cargando…', '(1) el título se queda en «Cargando…»');
  ok(/No tienes acceso/.test(a.texto) || a.selector, `(1) ni «No tienes acceso» ni selector de personas (título «${a.titulo}»)`);
  ok(!TECNICO.test(a.texto), '(1) sale texto técnico');
  ok(!/Cargando…/.test(a.main), '(1) queda «Cargando…» en la pantalla');
  if (/No tienes acceso/.test(a.texto)) {
    ok(/operaciones/i.test(a.main), '(3) el mensaje sin acceso no manda a operaciones');
    ok(!nombres.some((n) => a.main.includes(n)), '(3) el mensaje sin acceso nombra a una persona');
  }
  // (2) la app no responde
  const b = await entrar(`${base}/?yo=persona_que_no_existe_l24`, async (p) => { await p.route('**/api/sesion*', (r) => r.abort('connectionrefused')); });
  ok(/La app no responde/.test(b.texto), `(2) no dice «La app no responde» (título «${b.titulo}»)`);
  ok(b.titulo !== 'Cargando…' && !/Cargando…/.test(b.main), '(2) queda «Cargando…»');
  ok(!TECNICO.test(b.texto), '(2) sale texto técnico');
  ok(/operaciones/i.test(b.main) && !nombres.some((n) => b.main.includes(n)), '(3) el mensaje de caída no manda a operaciones o nombra a una persona');
} finally { await navegador.close(); }
console.log(`${fallos.length ? '✘' : '✔'} L-24: ${comprobados} comprobaciones${fallos.length ? ' · ' + fallos.join(' · ') : ''}`);
process.exit(fallos.length ? 1 : 0);
