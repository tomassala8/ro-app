// capturar.mjs · foto de cada pantalla, para cada persona, en escritorio y en móvil.
// Se hace dos veces: con la app de hoy (servir.py) y con la nueva (Next). Luego comparar.mjs dice qué cambia.
//
//   node capturar.mjs --base http://127.0.0.1:8770 --modo viejo --salida ~/RO_MIGRACION/capturas/viejo
//   node capturar.mjs --base http://127.0.0.1:3000 --modo nuevo --salida ~/RO_MIGRACION/capturas/nuevo
// Opciones: --personas tomas,mili,lucia (por defecto: las de /api/elegir) · --pantallas mi-dia,en-rojo · --solo-escritorio
//
// ⚠️ Las fotos llevan DATOS REALES: siempre fuera del repositorio.
import { chromium } from 'playwright';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, arr) => {
  if (a.startsWith('--')) acc.push([a.slice(2), arr[i + 1] && !arr[i + 1].startsWith('--') ? arr[i + 1] : true]);
  return acc;
}, []));
const base = (args.base ?? 'http://127.0.0.1:8770').replace(/\/$/, '');
const modo = args.modo ?? 'viejo';
const salida = resolve(String(args.salida ?? `~/RO_MIGRACION/capturas/${modo}`).replace(/^~/, homedir()));
const raiz = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..', '..');

// Pantallas: del inventario (migracion/inventario/pantallas.json), que se rehace la misma noche.
const inventario = join(raiz, 'migracion', 'inventario', 'pantallas.json');
let pantallas = JSON.parse(readFileSync(inventario, 'utf8')).map((p) => p.id);
if (args.pantallas) pantallas = String(args.pantallas).split(',');

// Dirección de cada pantalla. Las dos apps usan la MISMA (#/mi-dia): esta noche no cambia ninguna dirección
// (los enlaces guardados y los fetch relativos «data/…», «api/…» del front de hoy dependen de estar en /).
// --modo rutas: para cuando, otro día, la nueva pase a rutas de verdad (/mi-dia).
const url = (persona, pantalla) => modo === 'rutas'
  ? `${base}/${pantalla}?yo=${persona}`
  : `${base}/?yo=${persona}#/${pantalla}`;

const tamanos = args['solo-escritorio'] ? [['escritorio', 1440, 900]] : [['escritorio', 1440, 900], ['movil', 390, 844]];
// Misma hora en las dos pasadas: los «hace 5 min» y el «hoy» salen iguales.
const HORA_FIJA = new Date(args.hora ?? '2026-10-05T07:30:00+02:00');

async function personas() {
  if (args.personas) return String(args.personas).split(',');
  const r = await fetch(`${base}/api/elegir`);
  if (!r.ok) throw new Error(`/api/elegir respondió ${r.status}: arranca la app en local, sin Cloudflare Access`);
  return (await r.json()).personas.map((p) => p.id);
}

const navegador = await chromium.launch(existsSync('/opt/pw-browsers/chromium') ? { executablePath: '/opt/pw-browsers/chromium' } : {});
const lista = await personas();
const errores = [];
const tiempos = {};   // ms hasta que la pantalla está pintada (lo usa migracion/rendimiento.py)
let n = 0;
for (const [nombreTam, ancho, alto] of tamanos) {
  for (const persona of lista) {
    const ctx = await navegador.newContext({ viewport: { width: ancho, height: alto }, locale: 'es-ES', timezoneId: 'Europe/Madrid', reducedMotion: 'reduce' });
    if (!args["sin-reloj"]) await ctx.clock.setFixedTime(HORA_FIJA);
    const pagina = await ctx.newPage();
    pagina.on('pageerror', (e) => errores.push({ persona, tamano: nombreTam, url: pagina.url(), error: String(e) }));
    for (const pantalla of pantallas) {
      const destino = join(salida, nombreTam, persona);
      mkdirSync(destino, { recursive: true });
      try {
        await pagina.goto('about:blank');   // si no, cambiar solo el #/ no recarga la app vieja
        const t0 = Date.now();
        await pagina.goto(url(persona, pantalla), { waitUntil: 'networkidle', timeout: 45_000 });
        // Espera a que la pantalla deje de decir «Cargando…» (como mucho 15 s; si no, la foto lo enseñará).
        await pagina.waitForFunction(() => !document.body.innerText.includes('Cargando…'), null, { timeout: 15_000 }).catch(() => {});
        tiempos[`${nombreTam}/${persona}/${pantalla}`] = Date.now() - t0;
        await pagina.addStyleTag({ content: '*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}' });
        await pagina.waitForTimeout(400);
        await pagina.screenshot({ path: join(destino, `${pantalla}.png`), fullPage: true });
        n++;
      } catch (e) {
        errores.push({ persona, tamano: nombreTam, pantalla, error: String(e).split('\n')[0] });
      }
    }
    await ctx.close();
  }
}
await navegador.close();
mkdirSync(salida, { recursive: true });
writeFileSync(join(salida, '_errores.json'), JSON.stringify(errores, null, 1));
writeFileSync(join(salida, '_tiempos.json'), JSON.stringify(tiempos, null, 1));
console.log(`${n} fotos en ${salida} · ${errores.length} errores de página (ver _errores.json)`);
