#!/usr/bin/env node
// migracion/pruebas_L-41.mjs · L-41: cada llave que falta sale una vez, sin «Falta la llave: Falta la llave» ni órdenes de terminal.
// Uso: node migracion/pruebas_L-41.mjs --base http://127.0.0.1:8771 [--volcar]
// Dirección en `#/mi-dia`, `#/conexiones` (Salud del sistema) y `#/alertas` (solo lectura). Mira el texto visible (`innerText`) y,
// aparte, inyecta con `page.route` una respuesta de conexiones con la llave que falta y la orden de terminal, para
// comprobar el saneado aunque la copia no tenga llaves en falta. Solo recuentos y nombres de pantalla en la salida.
import { chromium } from '../v2/tools/capturas/node_modules/playwright/index.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, v) => (x.startsWith('--') ? [...a, [x.slice(2), v[i + 1]?.startsWith('--') || v[i + 1] === undefined ? true : v[i + 1]]] : a), []));
const base = String(args.base || 'http://127.0.0.1:8771').replace(/\/$/, '');
const PANTALLAS = ['mi-dia', 'conexiones', 'alertas'];
const MALOS = [
  [/Falta la llave:?\s*Falta la llave/i, '«Falta la llave: Falta la llave»'],
  [/security\s+(add|find)-generic-password/i, 'orden de llavero'],
  [/python3\s/i, 'orden «python3 »'],
  [/(^|\s)export\s+[A-Z_]+=/, 'orden «export »'],
];
const fallos = [];
let n = 0;
const ok = (c, t) => { n++; if (!c) fallos.push(t); };

const elegir = await (await fetch(`${base}/api/elegir`)).json();
const personas = (elegir.personas || []).filter((p) => (p.estado || 'activo') === 'activo');
const dir = personas.find((p) => (p.puestos || []).includes('direccion'));
ok(!!dir, 'falta una persona de dirección');

function revisar(texto, donde) {
  for (const [re, que] of MALOS) ok(!re.test(texto), `${donde}: ${que}`);
  // Dos líneas iguales seguidas con «llave».
  const lineas = texto.split('\n').map((l) => l.trim()).filter(Boolean);
  let rep = 0;
  for (let i = 1; i < lineas.length; i++) if (/llave/i.test(lineas[i]) && lineas[i] === lineas[i - 1]) rep++;
  ok(rep === 0, `${donde}: ${rep} línea(s) de llave repetida(s) seguidas`);
}

// Cada conexión (article[data-conexion]) sale una vez y su aviso no repite el titular que ya dice el chip.
function revisarConexiones(filas, donde) {
  const ids = filas.map((f) => f.id);
  const repetidas = ids.filter((id, i) => ids.indexOf(id) !== i);
  ok(repetidas.length === 0, `${donde}: conexión repetida (${[...new Set(repetidas)].join(', ')})`);
  let dup = 0;
  for (const f of filas) {
    const ls = f.texto.split('\n').map((l) => l.trim()).filter(Boolean).filter((l) => /llave/i.test(l));
    for (const l of ls) if (ls.some((m) => m !== l && m.toLowerCase().startsWith(l.toLowerCase()) && l.length >= 8)) dup++;
    if (/Falta la llave:?\s*Falta la llave/i.test(f.texto)) dup++;
  }
  ok(dup === 0, `${donde}: ${dup} conexión(es) que repiten «Falta la llave» (chip y detalle)`);
}

const navegador = await chromium.launch();
try {
  for (const inyectar of [false, true]) {
    const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 }, locale: 'es-ES', timezoneId: 'Europe/Madrid', reducedMotion: 'reduce' });
    await ctx.clock.setFixedTime(new Date('2026-10-05T07:30:00+02:00'));
    const mala = 'Falta la llave: Falta la llave clickup_api_token. Ejecuta: security add-generic-password -a ro -s clickup_api_token -w; luego python3 despliegue/salud_conexiones.py y export RO_X=1';
    if (inyectar) {
      // `/api/vigia` con dos llaves más en falta, con la orden de terminal y el titular repetido.
      await ctx.route(/\/api\/vigia(\?.*)?$/, async (ruta) => {
        const r = await ruta.fetch();
        let j; try { j = await r.json(); } catch { return ruta.fulfill({ response: r }); }
        const molde = (id, nombre) => ({ id, nombre, grupo: 'conexiones', icono: 'plug', color: 'rojo', titular: 'Falta la llave', detalle: mala, que_hacer: 'Tomás: pega la llave con bash ~/RO_HERRAMIENTAS/x/pegar.sh', estado: 'falta_clave', ms: null, ok: false, critica: true, quien: 'Tomás', quien_id: 'tomas', desde: '2026-10-05 06:00', ultima_prueba: '2026-10-05 07:00', cada_min: 10 });
        return ruta.fulfill({ response: r, json: { ...j, filas: [...(j.filas || []), molde('clickup_l41', 'ClickUp (prueba L-41)'), molde('ghl_l41', 'GoHighLevel (prueba L-41)')] } });
      });
    }
    for (const pant of PANTALLAS) {
      const pg = await ctx.newPage();
      try {
        await pg.goto(`${base}/?yo=${dir?.id}&hoy=2026-10-05#/${pant}`, { waitUntil: 'load', timeout: 45_000 });
        await pg.waitForSelector('#main', { timeout: 20_000 }).catch(() => {});
        await pg.waitForTimeout(3500);
        const t = await pg.evaluate(() => (document.querySelector('#main') || document.body).innerText);
        if (args.volcar) console.log(`--- ${inyectar ? 'inyectada' : 'real'} · ${pant}: ${(t.match(/llave/gi) || []).length} menciones`);
        revisar(t, `${inyectar ? 'inyectada' : 'real'} · ${pant}`);
        if (pant === 'conexiones') {
          const filas = await pg.evaluate(() => [...document.querySelectorAll('article[data-conexion]')].map((a) => ({ id: a.getAttribute('data-conexion'), texto: a.innerText })));
          ok(filas.length > 0, `${inyectar ? 'inyectada' : 'real'} · conexiones: ninguna fila pintada`);
          if (inyectar) ok(filas.some((f) => f.id === 'clickup_l41') && filas.some((f) => f.id === 'ghl_l41'), 'inyectada · conexiones: no salen las filas inyectadas');
          revisarConexiones(filas, `${inyectar ? 'inyectada' : 'real'} · conexiones`);
        }
      } catch (e) { fallos.push(`${pant}: no cargó (${String(e).slice(0, 60)})`); } finally { await pg.close(); }
    }
    await ctx.close();
  }
} finally { await navegador.close(); }
console.log(`${fallos.length ? '✘' : '✔'} L-41: ${n} comprobaciones${fallos.length ? ' · ' + fallos.join(' · ') : ''}`);
process.exit(fallos.length ? 1 : 0);
