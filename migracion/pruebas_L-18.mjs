#!/usr/bin/env node
// migracion/pruebas_L-18.mjs · L-18: las horas de Madrid no dependen de la zona del navegador.
// Uso: node migracion/pruebas_L-18.mjs --base http://127.0.0.1:8771
// Abre cada pantalla con tres husos (Madrid, Buenos Aires, Makassar), con el reloj fijo, y compara el texto visible:
// tiene que ser idéntico. Sale 0 si lo es. Sin datos reales en el repo: los textos solo se comparan, no se guardan.
import { readFileSync } from 'node:fs';
import { chromium } from '../v2/tools/capturas/node_modules/playwright/index.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, v) => (x.startsWith('--') ? [...a, [x.slice(2), v[i + 1]?.startsWith('--') || v[i + 1] === undefined ? true : v[i + 1]]] : a), []));
const base = String(args.base || 'http://127.0.0.1:8771').replace(/\/$/, '');
const HUSOS = ['Europe/Madrid', 'America/Argentina/Buenos_Aires', 'Asia/Makassar'];
const HORA = new Date('2026-10-05T07:30:00+02:00');
const PANTALLAS = args.pantallas ? String(args.pantallas).split(',') : ['mi-dia', 'alertas', 'bandeja', 'incidencias', 'produccion', 'agenda', 'clientes-nuevos', 'informe-cliente', 'en-rojo'];
const existentes = new Set(JSON.parse(readFileSync(new URL('./inventario/pantallas.json', import.meta.url), 'utf8')).map((p) => p.id));

const fallos = [];
const aviso = (t) => console.log(`  · ${t}`);

const elegir = await (await fetch(`${base}/api/elegir`)).json();
const personas = elegir.personas || [];
const dirigida = personas.find((p) => (p.puestos || []).includes('direccion'));
const account = personas.find((p) => (p.puestos || []).includes('account') && !(p.puestos || []).includes('direccion'));
const elegidas = [dirigida, account].filter(Boolean);
if (elegidas.length < 2) fallos.push('no hay una persona de dirección y un account en /api/elegir');

const navegador = await chromium.launch();

function normalizar(t) {
  return (t || '')
    .replace(/hace \d+ ?(min|h)/g, 'hace N')
    .replace(/[ \t]+/g, ' ')
    .split('\n').map((l) => l.trim()).filter(Boolean);
}

async function leer(persona, pantalla, huso) {
  const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 }, locale: 'es-ES', timezoneId: huso, reducedMotion: 'reduce' });
  await ctx.clock.setFixedTime(HORA);
  const pagina = await ctx.newPage();
  try {
    await pagina.goto(`${base}/?yo=${persona}&hoy=2026-10-05#/${pantalla}`, { waitUntil: 'load', timeout: 45_000 });
    await pagina.waitForFunction(() => {
      const m = document.querySelector('#main') || document.body;
      if (document.querySelector('#titulo')?.textContent === 'Cargando…') return false;
      if (m.querySelector('.esqueleto, [aria-busy="true"]')) return false;
      const texto = (m.innerText || '').trim();
      if (!texto) return false;
      if (/(Cargando|Leyendo|Pidiendo)[^\n]*(…|\.\.\.)/.test(texto)) return false;
      const w = window.__roEstable || (window.__roEstable = { texto: '', n: 0 });
      if (w.texto !== texto) { w.texto = texto; w.n = 0; return false; }
      w.n += 1;
      return w.n >= 12;
    }, null, { timeout: 15_000, polling: 100 }).catch(() => {});
    return normalizar(await pagina.evaluate(() => (document.querySelector('#main') || document.body).innerText));
  } finally {
    await ctx.close();
  }
}

for (const p of elegidas) {
  for (const pantalla of PANTALLAS) {
    if (!existentes.has(pantalla)) { aviso(`${pantalla}: no existe en el inventario, se salta`); continue; }
    // Un huso lento puede leer la pantalla a medio pintar: una diferencia se repite una vez antes de darla por buena.
    let textos = [];
    for (let intento = 1; intento <= 2; intento += 1) {
      textos = [];
      for (const huso of HUSOS) textos.push(await leer(p.id, pantalla, huso));
      if (textos.every((t) => JSON.stringify(t) === JSON.stringify(textos[0]))) break;
    }
    const [m, ...otros] = textos;
    otros.forEach((t, i) => {
      if (JSON.stringify(t) === JSON.stringify(m)) return;
      const dif = [];
      for (let k = 0; k < Math.max(t.length, m.length) && dif.length < 3; k += 1) {
        if (t[k] !== m[k]) dif.push(`Madrid «${(m[k] ?? '').slice(0, 80)}» ≠ ${HUSOS[i + 1]} «${(t[k] ?? '').slice(0, 80)}»`);
      }
      fallos.push(`${pantalla} (${p.id}): ${dif.join(' | ')}`);
    });
    console.log(`  ${textos.every((t) => JSON.stringify(t) === JSON.stringify(m)) ? '✔' : '✘'} ${pantalla} · ${p.id}`);
  }
}
await navegador.close();

// Estática: los ficheros ya arreglados no leen una fecha de los datos con los getters de la zona del navegador.
const ARREGLADOS = ['modulos/mi_dia.js', 'modulos/mi_dia_bloques.js'];
const PENDIENTES = ['modulos/evidencias_kpi.js', 'modulos/dinero_comun.js', 'modulos/nuevos.js', 'modulos/ia_componentes.js', 'modulos/informe.js', 'modulos/informe_revisar.js',
  'modulos/ficha.js', 'modulos/en_rojo.js', 'modulos/ajustes.js', 'modulos/_tarea_ia.js', 'modulos/_gbp_bloques.js', 'modulos/crm.js', 'modulos/seo.js',
  'modulos/primera_semana.js', 'modulos/decisiones.js', 'modulos/captacion.js', 'modulos/asistente_ia.js'];
const LOCAL = /new Date\((iso|t|f|x|s|fecha|hora)[^)]*\)\.get(Hours|Date|Month|Day)\(\)/g;
const cuenta = (f) => (readFileSync(new URL(`../${f}`, import.meta.url), 'utf8').match(LOCAL) || []).length;
for (const f of ARREGLADOS) if (cuenta(f) > 0) fallos.push(`${f}: ${cuenta(f)} lecturas con getters de la zona del navegador`);
const quedan = PENDIENTES.filter((f) => cuenta(f) > 0);
aviso(`consumidores que quedan por pasar a la vara de Madrid (pendiente, ver NOTAS): ${quedan.length ? quedan.map((f) => f.replace('modulos/', '')).join(', ') : 'ninguno'}`);

if (fallos.length) {
  console.log(`✘ L-18: ${fallos.length} diferencias`);
  fallos.forEach((f) => console.log(`  - ${f}`));
  process.exit(1);
}
console.log('✔ L-18: el texto es idéntico en los tres husos');
