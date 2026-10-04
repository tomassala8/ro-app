// comparar.mjs · compara las fotos de la app vieja y la nueva, pantalla a pantalla, píxel a píxel.
//   node comparar.mjs ~/RO_MIGRACION/capturas/viejo ~/RO_MIGRACION/capturas/nuevo [--umbral 0.5]
//   [--solo-escritorio] [--pantallas mi-dia,en-rojo]   (para iterar: compara solo eso, como lo que capturó capturar.mjs)
// También falla si la nueva tiene errores de página (_errores.json) que la de hoy no tenía.
// Escribe <nuevo>/_diferencias/*.png (en rojo lo que cambia) y <nuevo>/_informe.md, ordenado de peor a mejor.
// Sale con 1 si alguna pantalla pasa del umbral (% de píxeles distintos) o falta.
import { existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join, relative, resolve } from 'node:path';
import pixelmatch from 'pixelmatch';
import { PNG } from 'pngjs';

const [, , aViejo, aNuevo, ...resto] = process.argv;
if (!aViejo || !aNuevo) { console.error('Uso: node comparar.mjs <viejo> <nuevo> [--umbral 0.5]'); process.exit(2); }
const dir = (p) => resolve(p.replace(/^~/, homedir()));
const viejo = dir(aViejo), nuevo = dir(aNuevo);
const umbral = Number(resto[resto.indexOf('--umbral') + 1]) || 0.5;
const soloEscritorio = resto.includes('--solo-escritorio');
const soloPantallas = resto.includes('--pantallas') ? String(resto[resto.indexOf('--pantallas') + 1]).split(',') : null;
const cuenta = (rel) => (!soloEscritorio || rel.startsWith('escritorio'))
  && (!soloPantallas || soloPantallas.some((p) => rel.endsWith(`/${p}.png`)));

const pngs = (d) => readdirSync(d).flatMap((f) => {
  const p = join(d, f);
  if (f.startsWith('_')) return [];
  return statSync(p).isDirectory() ? pngs(p) : f.endsWith('.png') ? [p] : [];
});

const filas = [];
for (const fv of pngs(viejo)) {
  const rel = relative(viejo, fv);
  if (!cuenta(rel)) continue;
  const fn = join(nuevo, rel);
  if (!existsSync(fn)) { filas.push({ rel, pct: 100, nota: 'falta en la nueva' }); continue; }
  const a = PNG.sync.read(readFileSync(fv));
  const b = PNG.sync.read(readFileSync(fn));
  const ancho = Math.max(a.width, b.width), alto = Math.max(a.height, b.height);
  const lienzo = (img) => { const c = new PNG({ width: ancho, height: alto }); PNG.bitblt(img, c, 0, 0, img.width, img.height, 0, 0); return c; };
  const ca = lienzo(a), cb = lienzo(b), dif = new PNG({ width: ancho, height: alto });
  const distintos = pixelmatch(ca.data, cb.data, dif.data, ancho, alto, { threshold: 0.1 });
  const pct = (100 * distintos) / (ancho * alto);
  const nota = a.height !== b.height ? `alto ${a.height} → ${b.height} px` : '';
  if (pct > 0) {
    const d = join(nuevo, '_diferencias', rel);
    mkdirSync(join(d, '..'), { recursive: true });
    writeFileSync(d, PNG.sync.write(dif));
  }
  filas.push({ rel, pct, nota });
}
filas.sort((x, y) => y.pct - x.pct);
const malas = filas.filter((f) => f.pct > umbral);
// Errores de página: solo cuentan los que la app de hoy NO tenía (misma persona, tamaño, pantalla y mensaje).
const leerErrores = (d) => (existsSync(join(d, '_errores.json')) ? JSON.parse(readFileSync(join(d, '_errores.json'), 'utf8')) : []);
const clave = (e) => [e.persona, e.tamano, e.pantalla ?? String(e.url ?? '').split('#')[1] ?? '', String(e.error).replace(/https?:\/\/[^/\s]+/g, '')].join('|');
const yaEstaban = new Set(leerErrores(viejo).map(clave));
const nErrores = leerErrores(nuevo).filter((e) => !yaEstaban.has(clave(e))).length;
const informe = [
  '# Fotos: app vieja frente a nueva', '',
  `**${filas.length - malas.length} de ${filas.length} pantallas por debajo del ${umbral} % de píxeles distintos.**`, '',
  nErrores ? `**${nErrores} errores de página nuevos** (no estaban en la app de hoy; ver _errores.json): cuentan como fallo.\n` : '',
  '| Pantalla | % distinto | Nota |', '|---|---|---|',
  ...filas.map((f) => `| ${f.pct > umbral ? '✘' : '✔'} \`${f.rel}\` | ${f.pct.toFixed(2)} | ${f.nota} |`),
].join('\n');
writeFileSync(join(nuevo, '_informe.md'), informe + '\n');
console.log(informe.split('\n').slice(0, 30).join('\n'));
process.exit(malas.length || nErrores ? 1 : 0);
