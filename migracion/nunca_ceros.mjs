#!/usr/bin/env node
// migracion/nunca_ceros.mjs · N-10 y PLAN_MAESTRO §2.5: «sin dato no es cero».
// Uso:  node migracion/nunca_ceros.mjs [--linea-base ~/RO_MIGRACION/nunca_ceros.json] [--escribir-base] [--desde-git HEAD]
// Cuenta, por fichero de `modulos/*.js` y `componentes.js`, los `?? 0` y `|| 0` fuera de comentarios (la mayoría son
// índices, bucles o ordenaciones, que no pintan cifras: la línea base los tolera). El número solo puede BAJAR:
//   · sale 1 si algún fichero sube frente a la línea base;
//   · sale 1 si sigue alguno de los puntos nombrados (PUNTOS: la expresión vieja que pintaba un cero donde no había dato).
// La línea base vive FUERA del repo (~/RO_MIGRACION/nunca_ceros.json). Si no existe, se escribe con el estado actual.
// `--desde-git <ref>` cuenta los ficheros tal como estaban en ese commit (para fijar la base antes de arreglar).
import { readFileSync, writeFileSync, existsSync, readdirSync, mkdirSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { homedir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');
const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, v) => (x.startsWith('--') ? [...a, [x.slice(2), v[i + 1]?.startsWith('--') || v[i + 1] === undefined ? true : v[i + 1]]] : a), []));
const BASE = String(args['linea-base'] || join(homedir(), 'RO_MIGRACION', 'nunca_ceros.json')).replace(/^~/, homedir());
const RX = /\?\?\s*0\b|\|\|\s*0\b/g;

// Puntos nombrados: la expresión de antes, por su texto (no por número de línea). Tienen que haber desaparecido.
const PUNTOS = [
  ['modulos/captacion.js', /rojos:\s*Ct\.criticos\.length/, 'Por trafficker: gravedad ausente terminaba en «0 críticos»'],
  ['modulos/captacion.js', /`\$\{x\.cansadas\} \/ \$\{x\.rechazados\}`/, 'Por trafficker: señales y rechazos sin dato se pintaban 0'],
  ['modulos/captacion.js', /s \+ \(c\.anuncios\?\.cansadas \|\| 0\)/, 'Agregado de anuncios cansados con || 0'],
  ['modulos/captacion.js', /s \+ \(c\.leads\?\.\['7d'\] \|\| 0\)/, 'Agregado de leads 7 d con || 0'],
  ['modulos/seo.js', /caidas_ahora \?\? 0/, 'Webs en Modular: «0 caídas ahora» sin dato'],
  ['modulos/seo.js', /con_vulnerabilidad_critica \?\? 0/, 'Webs en Modular: «0 con vulnerabilidad crítica» sin dato'],
  ['modulos/seo.js', /emparejadas \?\? 0/, 'Resumen de Modular: «0 webs» sin dato'],
  ['modulos/seo.js', /dias_sin_copia_buena \?\? 0;/, 'Copia: sin días se pintaba «hoy» en verde'],
  ['modulos/seo.js', /\(f\.visibilidad \|\| \{\}\)\.desaparecen \|\| 0/, 'Ausencias anteriores sin dato se sumaban como 0'],
];

function quitarComentarios(t) {
  return t.replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, ' ')).replace(/(^|[^:'"`\\])\/\/[^\n]*/g, '$1');
}
function leer(f) {
  if (args['desde-git']) {
    try { return execFileSync('git', ['show', `${args['desde-git']}:${f}`], { cwd: RAIZ, encoding: 'utf8', maxBuffer: 1 << 26 }); } catch { return ''; }
  }
  return readFileSync(join(RAIZ, f), 'utf8');
}
const ficheros = [...readdirSync(join(RAIZ, 'modulos')).filter((f) => f.endsWith('.js')).map((f) => `modulos/${f}`), 'componentes.js'].sort();
const cuenta = Object.fromEntries(ficheros.map((f) => [f, (quitarComentarios(leer(f)).match(RX) || []).length]).filter(([, n]) => n > 0));
const total = Object.values(cuenta).reduce((a, b) => a + b, 0);

if (args['escribir-base'] || !existsSync(BASE)) {
  mkdirSync(dirname(BASE), { recursive: true });
  writeFileSync(BASE, JSON.stringify({ total, ficheros: cuenta, desde: args['desde-git'] || 'árbol de trabajo' }, null, 1));
  console.log(`línea base escrita en ${BASE}: ${total} apariciones en ${Object.keys(cuenta).length} ficheros`);
  if (args['escribir-base']) process.exit(0);
}
const base = JSON.parse(readFileSync(BASE, 'utf8'));
const fallos = [];
for (const [f, n] of Object.entries(cuenta)) if (n > (base.ficheros[f] || 0)) fallos.push(`${f}: sube de ${base.ficheros[f] || 0} a ${n}`);
if (!args['desde-git']) {
  for (const [f, rx, que] of PUNTOS) if (rx.test(quitarComentarios(readFileSync(join(RAIZ, f), 'utf8')))) fallos.push(`sigue: ${que} (${f})`);
}
console.log(`«?? 0» y «|| 0» fuera de comentarios: ${total} (línea base ${base.total}; baja ${base.total - total})`);
if (fallos.length) {
  fallos.forEach((x) => console.log(`  ✘ ${x}`));
  process.exit(1);
}
console.log('✔ nunca_ceros: ningún fichero sube y los puntos nombrados ya no pintan ceros');
