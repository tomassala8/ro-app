import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { reglas } from './reglas.js';
import type { Nivel, Persona } from './tipos.js';
import { vistaActiva } from './vista.js';

const RANGO: Record<string, number> = { resumen: 1, suyo: 2, todo: 3 };

function objetoJs(texto: string, constantes: Record<string, Record<string, Nivel | null>>): Record<string, Nivel | null> {
  const t = texto.trim();
  const conocida = constantes[t];
  if (conocida) return { ...conocida };
  const out: Record<string, Nivel | null> = {};
  for (const m of t.matchAll(/\.\.\.(\w+)/g)) {
    const nombre = m[1] ?? '';
    Object.assign(out, constantes[nombre] ?? {});
  }
  const re = /['"]?([\w*]+)['"]?\s*:\s*('(?:todo|suyo|resumen)'|"(?:todo|suyo|resumen)"|null)/g;
  for (const m of t.matchAll(re)) {
    const k = m[1] ?? '';
    const v = m[2] ?? '';
    out[k] = v === 'null' ? null : (v.replace(/['"]/g, '') as Nivel);
  }
  return out;
}

function dirModulosPorDefecto(): string {
  return fileURLToPath(new URL('../../../../modulos/', import.meta.url));
}

export function cargarModulos(dir = process.env.RO_MODULOS_DIR ?? dirModulosPorDefecto()): Record<string, Record<string, Nivel | null>> {
  const indice = readFileSync(join(dir, 'indice.js'), 'utf8');
  const constantes: Record<string, Record<string, Nivel | null>> = {};
  for (const m of indice.matchAll(/const (\w+) = (\{[^}]*\});/g)) {
    constantes[m[1] ?? ''] = objetoJs(m[2] ?? '', constantes);
  }
  const modulos: Record<string, Record<string, Nivel | null>> = {};
  for (const m of indice.matchAll(/\{\s*id:\s*'([\w\-]+)'([\s\S]*?)resumen:/g)) {
    const mid = m[1] ?? '';
    const cuerpo = m[2] ?? '';
    const pq = /puestos_que_lo_ven:\s*(\{[^}]*\}|\w+)/.exec(cuerpo);
    const fichero = /fichero:\s*'\.\/([\w\-]+\.js)'/.exec(cuerpo);
    let mapa = pq ? objetoJs(pq[1] ?? '', constantes) : {};
    if (fichero) {
      const ruta = join(dir, fichero[1] ?? '');
      if (existsSync(ruta)) {
        const propio = /puestos_que_lo_ven:\s*(\{[^}]*\})/.exec(readFileSync(ruta, 'utf8'));
        if (propio) mapa = objetoJs(propio[1] ?? '', constantes);
      }
    }
    modulos[mid] = mapa;
  }
  const fueraMapa = reglas().modulos_sin_puesto ?? {};
  for (const [mid, fuera] of Object.entries(fueraMapa)) {
    if (!(mid in modulos)) continue;
    const extra: Record<string, Nivel | null> = {};
    for (const p of fuera) extra[p] = null;
    modulos[mid] = { ...modulos[mid], ...extra };
  }
  return modulos;
}

export function nivelModuloSinVista(persona: Persona, mapa: Record<string, Nivel | null>): Nivel | null {
  let mejor: Nivel | null = null;
  for (const p of persona.puestos ?? []) {
    const n = (p in mapa ? mapa[p] : mapa['*']) ?? null;
    if (n && (!mejor || RANGO[n] > RANGO[mejor])) mejor = n;
  }
  return mejor;
}

export function nivelModulo(persona: Persona, mapa: Record<string, Nivel | null>): Nivel | null {
  let n = nivelModuloSinVista(persona, mapa);
  const activo = vistaActiva();
  if (n && activo && activo.real.id !== persona.id) {
    const n2 = nivelModuloSinVista(activo.real, mapa);
    n = !n2 ? null : RANGO[n] <= RANGO[n2] ? n : n2;
  }
  return n;
}
