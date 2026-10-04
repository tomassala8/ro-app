// Paridad con permisos.py: mismas respuestas para las mismas preguntas.
// Vectores: python3 migracion/vectores_permisos.py (en el Mac, con data/) → RO_VECTORES=~/RO_MIGRACION/vectores pnpm test
// Es la puerta f4 («100 % de los vectores»): se compara vector a vector y cualquier diferencia la pone en rojo.
//
// Contrato del motor (src/index.ts, F4.1): las mismas funciones que permisos.py, con los mismos argumentos y el nombre
// en camelCase como pide PROMPTS_CURSOR.md F4.1 (nivelModulo, carteraPorSilla, mirandoComo; también vale el de Python):
//   ver(persona, dato, cp) · contexto(persona, crudo) · nivel_modulo(persona, mapa) · cartera_por_silla(persona, asignaciones)
//   ambito(persona) · recortar(persona, crudo) · mirando_como(real, crudo, fn): «ver como» explícito; dentro de fn,
//   ver() y nivel_modulo() de otra persona dan el mínimo de las dos (el «with P.mirando_como(…)» de Python).
// Si falta alguna, la prueba falla y dice cuál: sin motor portado, la puerta f4 no puede salir verde.
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import * as motor from '../src/index.js';
import { cargarReglas } from '../src/index.js';

const dir = process.env.RO_VECTORES?.replace(/^~/, process.env.HOME ?? '');
const hay = !!dir && existsSync(join(dir, 'permisos.json'));
if (!hay) {
  console.warn(
    `paridad con permisos.py: SALTADA, no hay vectores (${dir ? join(dir, 'permisos.json') : 'falta RO_VECTORES'}). ` +
      'Sácalos con «python3 migracion/vectores_permisos.py» y pasa RO_VECTORES.',
  );
}

type Fn = (...a: unknown[]) => unknown;
const M = motor as unknown as Record<string, Fn | undefined>;
const NECESARIAS = ['ver', 'contexto', 'nivel_modulo', 'cartera_por_silla', 'ambito', 'recortar', 'mirando_como'];
const camel = (n: string) => n.replace(/_(\w)/g, (_, c: string) => c.toUpperCase());
const fn = (n: string): Fn | undefined => (typeof M[camel(n)] === 'function' ? M[camel(n)] : typeof M[n] === 'function' ? M[n] : undefined);
const MAX_DIFERENCIAS = 20;

const leer = (f: string) => JSON.parse(readFileSync(join(dir!, f), 'utf8'));

// Igual que _res() de vectores_permisos.py: ok, nivel y desenmascarable, solo si no son null/undefined.
function res(r: unknown) {
  const o = (r ?? {}) as Record<string, unknown>;
  const out: Record<string, unknown> = {};
  for (const k of ['ok', 'nivel', 'desenmascarable']) if (o[k] !== undefined && o[k] !== null) out[k] = o[k];
  return out;
}

// Como json.dumps(…, default=sorted) de Python: los conjuntos salen como listas ordenadas.
function normal(v: unknown): unknown {
  if (v instanceof Set) return [...v].map(normal).sort();
  if (v instanceof Map) return normal(Object.fromEntries(v));
  if (Array.isArray(v)) return v.map(normal);
  if (v && typeof v === 'object') {
    return Object.fromEntries(Object.entries(v as Record<string, unknown>).filter(([, x]) => x !== undefined).map(([k, x]) => [k, normal(x)]));
  }
  return v;
}

const igual = (a: unknown, b: unknown) => JSON.stringify(ordenado(a)) === JSON.stringify(ordenado(b));
function ordenado(v: unknown): unknown {
  if (Array.isArray(v)) return v.map(ordenado);
  if (v && typeof v === 'object') {
    return Object.fromEntries(Object.keys(v as object).sort().map((k) => [k, ordenado((v as Record<string, unknown>)[k])]));
  }
  return v;
}

describe('reglas', () => {
  it('reglas_permisos.json se lee y tiene los puestos', () => {
    const r = cargarReglas();
    expect(r.puestos.length).toBeGreaterThan(0);
  });
});

// En local, sin vectores se salta (necesitan data/ del Mac). En CI no: una puerta que no compara nada no es verde.
describe.runIf(!!process.env.CI)('vectores en CI', () => {
  it('hay vectores de permisos.py (RO_VECTORES)', () => {
    expect(hay, `faltan los vectores: ${dir ? join(dir, 'permisos.json') : 'RO_VECTORES sin poner'}`).toBe(true);
  });
});

describe.skipIf(!hay)('paridad con permisos.py', () => {
  it('el motor exporta todas las funciones del contrato', () => {
    expect(NECESARIAS.filter((n) => !fn(n)).map(camel), 'faltan en src/index.ts (F4.1)').toEqual([]);
  });

  it('cada persona activa: módulos, cartera, ámbito, ver, ver como y recorte, vector a vector', async () => {
    const faltan = NECESARIAS.filter((n) => !fn(n)).map(camel);
    if (faltan.length) throw new Error(`Motor sin portar: faltan ${faltan.join(', ')} en src/index.ts. No hay con qué comparar.`);
    const ver = fn('ver')!, contexto = fn('contexto')!, nivelModulo = fn('nivel_modulo')!, carteraPorSilla = fn('cartera_por_silla')!;
    const ambito = fn('ambito')!, recortar = fn('recortar')!, mirandoComo = fn('mirando_como')!;

    const v = leer('permisos.json');
    const crudo = leer('crudo.json');
    const modulos = leer('modulos.json') as Record<string, unknown>;
    const personas = new Map<string, Record<string, unknown>>(crudo.personas.map((p: { id: string }) => [p.id, p]));
    const tomas = personas.get('tomas');
    const ids = Object.keys(v.por_persona);
    expect(ids.length, 'permisos.json sin personas').toBeGreaterThan(0);

    const diferencias: string[] = [];
    let comparados = 0;
    let malos = 0;
    const apuntar = (texto: string) => {
      malos++;
      if (diferencias.length < MAX_DIFERENCIAS) diferencias.push(texto);
    };
    const comparar = (donde: string, esperado: unknown, real: unknown) => {
      comparados++;
      if (!igual(esperado, real)) apuntar(`${donde}: permisos.py ${JSON.stringify(esperado)} · motor nuevo ${JSON.stringify(real)}`);
    };
    const preguntar = (p: Record<string, unknown>, cp: unknown, esperado: Record<string, unknown>, prefijo: string) => {
      for (const [clave, r] of Object.entries(esperado)) {
        const [tipo, cliente, persona] = clave.split('|');
        const dato: Record<string, string> = { tipo };
        if (cliente) dato.cliente_id = cliente;
        if (persona) dato.persona_id = persona;
        comparar(`${prefijo} ver ${clave}`, r, res(ver(p, dato, cp)));
      }
    };
    const niveles = (p: Record<string, unknown>) =>
      Object.fromEntries(Object.entries(modulos).sort(([a], [b]) => (a < b ? -1 : 1)).map(([m, mapa]) => [m, nivelModulo(p, mapa)]));

    for (const id of ids) {
      const fila = v.por_persona[id];
      const p = personas.get(id);
      if (!p) {
        apuntar(`${id}: está en permisos.json y no en crudo.json`);
        continue;
      }
      const cp = contexto(p, crudo);
      comparar(`${id} · modulos`, fila.modulos, normal(niveles(p)));
      comparar(`${id} · cartera`, fila.cartera, normal(carteraPorSilla(p, crudo.asignaciones)));
      comparar(`${id} · ambito`, fila.ambito, ambito(p));
      preguntar(p, cp, fila.ver, id);
      if (fila.ver_como) {
        if (!tomas) apuntar(`${id}: hay ver_como en los vectores y no está «tomas» en crudo.json`);
        else {
          // Se prueba que mirandoComo SÍ llama a la función: si no la llamara, no se compararía nada y saldría verde.
          const antes = comparados;
          await mirandoComo(tomas, crudo, () => {
            preguntar(p, cp, fila.ver_como, `${id} (ver como)`);
            comparar(`${id} (ver como) · modulos`, fila.modulos_ver_como, normal(niveles(p)));
          });
          if (comparados === antes) apuntar(`${id} (ver como): mirandoComo no ejecutó la función, no se comparó nada`);
        }
      }
      const recorte = join(dir!, 'recortes', `${id}.json`);
      if (existsSync(recorte)) comparar(`${id} · recortar`, leer(join('recortes', `${id}.json`)), normal(recortar(p, crudo)));
      else apuntar(`${id}: falta recortes/${id}.json`);
    }

    expect(diferencias, `${malos} diferencia(s) en ${comparados} vectores (se enseñan las ${MAX_DIFERENCIAS} primeras)`).toEqual([]);
  });
});
