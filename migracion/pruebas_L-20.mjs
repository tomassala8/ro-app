#!/usr/bin/env node
// migracion/pruebas_L-20.mjs · L-20: los rótulos de «mes anterior» salen del «hoy» de Madrid, no de un mes fijo.
// Uso: node migracion/pruebas_L-20.mjs --base http://127.0.0.1:8771
// Con hoy = 3-nov-2026 (`?hoy=`), el mes anterior es octubre: no puede salir ninguno de los rótulos que antes decían «septiembre».
// Control: con hoy = 5-oct-2026 (el día de las fotos) siguen diciendo «septiembre» (el texto no cambia).
// Los rótulos de un dato histórico («muestra manual de septiembre», «Foto del 17 de septiembre», «Cierre de septiembre») se
// ignoran a propósito: son de un periodo acreditado (TRASPASO L20). Sin datos reales: los textos solo se miran, no se guardan.
import { chromium } from '../v2/tools/capturas/node_modules/playwright/index.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, v) => (x.startsWith('--') ? [...a, [x.slice(2), v[i + 1]?.startsWith('--') || v[i + 1] === undefined ? true : v[i + 1]]] : a), []));
const base = String(args.base || 'http://127.0.0.1:8771').replace(/\/$/, '');
const PANTALLAS = ['ficha', 'captacion', 'mi-dia'];   // ficha primero: da el id de cliente que abre la tarjeta de captación
// Rótulos que significan «mes anterior»: con hoy = 3-nov deben decir octubre.
const ROTULOS = [
  [/Inversión gestionada · (\p{L}+)/u, 'Inversión gestionada'],
  [/Ayer \d[\d.,]* · (\p{L}+) /u, 'Ayer … · mes'],
  [/Citas · (?!7 días)(\p{L}+)/u, 'Citas · mes'],
  [/Citas (?!7 días)(\p{L}+):/u, 'Citas mes:'],
  [/Reuniones · (\p{L}+)/u, 'Reuniones · mes'],
];
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];

const fallos = [];
const elegir = await (await fetch(`${base}/api/elegir`)).json();
const personas = elegir.personas || [];
const direccion = personas.find((p) => (p.puestos || []).includes('direccion'));
const account = personas.find((p) => (p.puestos || []).includes('account') && !(p.puestos || []).includes('direccion'));
const navegador = await chromium.launch();

async function leer(persona, ruta, hoy) {
  const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 }, locale: 'es-ES', timezoneId: 'Europe/Madrid', reducedMotion: 'reduce' });
  await ctx.clock.setFixedTime(new Date(`${hoy}T07:30:00+01:00`));
  const pagina = await ctx.newPage();
  try {
    await pagina.goto(`${base}/?yo=${persona}&hoy=${hoy}#/${ruta}`, { waitUntil: 'load', timeout: 45_000 });
    await pagina.waitForFunction(() => {
      const m = document.querySelector('#main') || document.body;
      const texto = (m.innerText || '').trim();
      if (!texto || /(Cargando|Leyendo|Pidiendo)[^\n]*(…|\.\.\.)/.test(texto)) return false;
      const w = window.__roEstable || (window.__roEstable = { texto: '', n: 0 });
      if (w.texto !== texto) { w.texto = texto; w.n = 0; return false; }
      w.n += 1;
      return w.n >= 12;
    }, null, { timeout: 15_000, polling: 100 }).catch(() => {});
    const leerMain = () => pagina.evaluate(() => (document.querySelector('#main') || document.body).innerText);
    let texto = await leerMain();
    // Cada pestaña de la pantalla (los rótulos de mes viven dentro de ellas): se pulsa una a una y se suma su texto.
    const n = await pagina.locator('#main [role=tab]').count();
    for (let i = 0; i < n; i++) {
      try {
        await pagina.locator('#main [role=tab]').nth(i).click({ timeout: 3000 });
        await pagina.waitForTimeout(1200);
        texto += '\n' + await leerMain();
      } catch { /* pestaña que no se deja pulsar: se salta */ }
    }
    const hash = await pagina.evaluate(() => location.hash);
    return { texto, hash };
  } finally { await ctx.close(); }
}

const vistos = { '2026-11-03': new Set(), '2026-10-05': new Set() };
const idsFicha = {};
for (const p of [direccion, account].filter(Boolean)) {
  for (const pantalla of PANTALLAS) {
    for (const hoy of ['2026-11-03', '2026-10-05']) {
      let ruta = pantalla;
      if (pantalla === 'captacion' && idsFicha[`${p.id}|${hoy}`]) ruta = `captacion/${idsFicha[`${p.id}|${hoy}`]}`;
      const { texto, hash } = await leer(p.id, ruta, hoy);
      if (pantalla === 'ficha') idsFicha[`${p.id}|${hoy}`] = (hash.match(/#\/ficha\/([^/?]+)/) || [])[1];
      const esperado = hoy === '2026-11-03' ? 'octubre' : 'septiembre';
      for (const [rx, nombre] of ROTULOS) {
        const m = texto.match(rx);
        if (!m) continue;
        const mes = m[1].toLowerCase();
        if (!MESES.includes(mes)) continue;      // no es un mes («Citas · 7 días» ya se excluye; esto cubre «Citas · semana»)
        vistos[hoy].add(`${nombre}=${mes}`);
        if (mes !== esperado) fallos.push(`${pantalla} (${p.id}, hoy ${hoy}): «${nombre}» dice ${mes}, debía decir ${esperado}`);
      }
      console.log(`  · ${pantalla} · ${p.id} · hoy ${hoy}`);
    }
  }
}
await navegador.close();
for (const hoy of Object.keys(vistos)) console.log(`  rótulos vistos con hoy ${hoy}: ${[...vistos[hoy]].join(', ') || 'ninguno'}`);
// Que la prueba no pase en vacío: con el hoy de las fotos tiene que haberse visto al menos un rótulo de mes anterior.
if (!vistos['2026-10-05'].size) fallos.push('control: con hoy 5-oct no se pintó ningún rótulo de «mes anterior» (la prueba no mide nada)');
if (fallos.length) { console.log(`✘ L-20: ${fallos.length} fallos`); fallos.forEach((f) => console.log(`  - ${f}`)); process.exit(1); }
console.log('✔ L-20: los rótulos de mes anterior siguen a hoy (octubre el 3-nov, septiembre el 5-oct)');
