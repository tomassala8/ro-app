// Copia el front de HOY (raíz del repo) a public/legacy/ para el «puente»: las pantallas que todavía no se han
// rehecho en React se pintan con su módulo original (render(contenedor, ctx)) dentro de la carcasa nueva.
// Se ejecuta solo en predev y prebuild. public/legacy/ no se versiona: la fuente sigue siendo la raíz del repo.
import { cpSync, existsSync, mkdirSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const web = join(dirname(fileURLToPath(import.meta.url)), '..');
const raiz = join(web, '..', '..', '..');
const destino = join(web, 'public', 'legacy');
const FICHEROS = ['estilos.css', 'componentes.js', 'datos.js', 'permisos.js', 'ayudas.js', 'carcasa.js', 'app.js', 'sw.js'];
const CARPETAS = ['modulos', 'fuentes_web'];

rmSync(destino, { recursive: true, force: true });
mkdirSync(destino, { recursive: true });
for (const f of FICHEROS) if (existsSync(join(raiz, f))) cpSync(join(raiz, f), join(destino, f));
for (const c of CARPETAS) if (existsSync(join(raiz, c))) cpSync(join(raiz, c), join(destino, c), { recursive: true });
// Las fuentes también en /fuentes_web (las pide estilos.css con ruta relativa y la carcasa nueva las precarga).
cpSync(join(raiz, 'fuentes_web'), join(web, 'public', 'fuentes_web'), { recursive: true });
console.log(`legacy: front de hoy copiado a ${destino}`);
