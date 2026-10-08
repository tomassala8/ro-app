import { createHash } from 'node:crypto';
import { existsSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { HttpException, Injectable } from '@nestjs/common';
import type { VistaConContexto } from '../permisos/motor-ro.js';
import { CatalogoRoto, recortarIndicadores } from '../permisos/importes-indicadores.js';

/** Raíz del repo, igual que crudo.service (cinco niveles por encima de src/indicadores/). */
const RAIZ = fileURLToPath(new URL('../../../../../', import.meta.url));
const INTERNO = 'Error interno (el detalle queda en el registro del servidor).';

type Guardado = { mtimeMs: number; doc: unknown };

/** Copia del fichero por mtime. Cada respuesta muta su propia copia. */
let cache: Guardado | null = null;

function leerCatalogo(): unknown {
  const ruta = process.env.RO_INDICADORES ?? join(RAIZ, 'indicadores.json');
  if (!existsSync(ruta)) throw new HttpException(INTERNO, 500);
  let st;
  try {
    st = statSync(ruta);
  } catch {
    throw new HttpException(INTERNO, 500);
  }
  if (cache && cache.mtimeMs === st.mtimeMs) return structuredClone(cache.doc);
  try {
    const doc = JSON.parse(readFileSync(ruta, 'utf8')) as unknown;
    cache = { mtimeMs: st.mtimeMs, doc };
    return structuredClone(doc);
  } catch {
    throw new HttpException(INTERNO, 500);
  }
}

export interface Catalogo {
  codigo: number;
  cuerpo?: unknown;
  etag: string;
}

@Injectable()
export class IndicadoresService {
  catalogo(vista: VistaConContexto, ifNoneMatch?: string): Catalogo {
    const crudo = leerCatalogo();
    let cat: unknown;
    try {
      cat = recortarIndicadores(vista, crudo);
    } catch (e) {
      if (e instanceof CatalogoRoto) throw new HttpException(INTERNO, 500);
      throw e;
    }
    const cuerpo = JSON.stringify(cat);
    const etag = `"${createHash('sha1').update(cuerpo).digest('hex').slice(0, 24)}"`;
    if ((ifNoneMatch ?? '').trim() === etag) return { codigo: 304, etag };
    return { codigo: 200, cuerpo: cat, etag };
  }
}
