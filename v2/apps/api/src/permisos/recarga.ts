import { readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Logger } from '@nestjs/common';
import { cargarModulos, recargarReglas } from '@ro/permisos';

/** servir.py › recargar_si_cambian: reglas_permisos.json y el índice de módulos al día sin reiniciar, mirando el disco
 *  como mucho una vez por segundo. Si un fichero está a medio escribir, se sigue con lo de antes. */
const RAIZ = fileURLToPath(new URL('../../../../../', import.meta.url));
const rutaReglas = () => process.env.RO_REGLAS_PERMISOS ?? join(RAIZ, 'reglas_permisos.json');
const dirModulos = () => process.env.RO_MODULOS_DIR ?? join(RAIZ, 'modulos');

const registro = new Logger('recarga');
let mirado = -Infinity;
let marcaReglas: number | undefined;
let marcaModulos: number | undefined;
let modulos: ReturnType<typeof cargarModulos> | undefined;

function marcas(): [number, number] | null {
  try {
    const dir = dirModulos();
    const m = Math.max(...readdirSync(dir).filter((f) => f.endsWith('.js')).map((f) => statSync(join(dir, f)).mtimeMs));
    return [statSync(rutaReglas()).mtimeMs, m];
  } catch {
    return null;
  }
}

export function recargarSiCambian(): void {
  const t = performance.now();
  if (t - mirado < 1000) return;
  mirado = t;
  const m = marcas();
  if (!m) return;
  const [r, mods] = m;
  if (marcaReglas !== undefined && marcaReglas !== r) {
    try {
      recargarReglas();
      registro.log('reglas_permisos.json releído');
    } catch (e) {
      registro.error(String(e));
      return;
    }
  }
  if (marcaModulos !== undefined && marcaModulos !== mods) {
    try {
      modulos = cargarModulos();
      registro.log('índice de módulos releído');
    } catch (e) {
      registro.error(String(e));
    }
  }
  marcaReglas = r;
  marcaModulos = mods;
}

/** Qué módulos ve cada puesto (servir.py › E.modulos), el de la última recarga. */
export function modulosActuales(): ReturnType<typeof cargarModulos> {
  if (!modulos) {
    modulos = cargarModulos();
    recargarSiCambian();
  }
  return modulos;
}
