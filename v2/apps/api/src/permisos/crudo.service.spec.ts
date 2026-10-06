import { existsSync, readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { compararComoPython, jsonComoPython } from '@ro/compat';
import { PrismaService } from '../prisma/prisma.service.js';
import { CrudoService } from './crudo.service.js';

// El vector es S.E.crudo de servir.py tal cual tras cargar() (vectores_permisos.py): la verdad. Datos reales: viven
// en ~/RO_MIGRACION y nunca salen del proceso (los fallos solo dicen el id y la clave, no el valor).
const VECTOR = join(process.env.RO_VECTORES ?? join(homedir(), 'RO_MIGRACION', 'vectores'), 'crudo.json');
const hay = Boolean(process.env.DATABASE_URL) && existsSync(VECTOR);

type Obj = Record<string, unknown>;
// Como == de Python entre dicts: sin mirar el orden de las claves (el vector se graba con sort_keys).
const igual = (a: unknown, b: unknown) => jsonComoPython(a ?? null, { sortKeys: true }) === jsonComoPython(b ?? null, { sortKeys: true });
const ordenar = (filas: Obj[], claves: string[]) =>
  [...filas].sort((a, b) => {
    for (const k of claves) {
      const c = compararComoPython(jsonComoPython(a[k] ?? ''), jsonComoPython(b[k] ?? ''));
      if (c) return c;
    }
    return 0;
  });

/** Qué filas (por id) y qué claves difieren; sin valores. */
function diferencias(nombre: string, a: Obj[], b: Obj[], id: (f: Obj) => string): string[] {
  const out: string[] = [];
  if (a.length !== b.length) out.push(`${nombre}: ${a.length} filas en el vector, ${b.length} en Nest`);
  const porId = new Map(b.map((f) => [id(f), f]));
  for (const fa of a) {
    const fb = porId.get(id(fa));
    if (!fb) {
      out.push(`${nombre}/${id(fa)}: falta en Nest`);
      continue;
    }
    for (const k of new Set([...Object.keys(fa), ...Object.keys(fb)])) {
      if (!(k in fa) || !(k in fb) || !igual(fa[k], fb[k])) out.push(`${nombre}/${id(fa)}.${k}`);
    }
  }
  return out;
}

describe.skipIf(!hay)('CrudoService contra el crudo de servir.py (vectores/crudo.json)', () => {
  let prisma: PrismaService;
  let servicio: CrudoService;
  beforeAll(() => {
    prisma = new PrismaService();
    servicio = new CrudoService(prisma);
  });
  afterAll(() => prisma?.onModuleDestroy());

  it('personas, asignaciones y clientes salen idénticos', async () => {
    const vector = JSON.parse(readFileSync(VECTOR, 'utf8')) as Obj;
    const nest = (await servicio.actual()) as unknown as Obj;
    const difs = [
      ...diferencias('personas', vector.personas as Obj[], nest.personas as Obj[], (f) => String(f.id)),
      ...diferencias(
        'asignaciones',
        ordenar(vector.asignaciones as Obj[], ['cliente_id', 'silla', 'persona_id', 'desde']),
        ordenar(nest.asignaciones as Obj[], ['cliente_id', 'silla', 'persona_id', 'desde']),
        (f) => [f.cliente_id, f.silla, f.persona_id, f.desde].join('|'),
      ),
      ...diferencias('clientes', vector.clientes as Obj[], nest.clientes as Obj[], (f) => String(f.id)),
    ];
    for (const n of ['alarmas', 'logos', 'meta']) {
      if (n in vector && !igual(vector[n], nest[n])) difs.push(n);
    }
    expect(difs).toEqual([]);
  });
});
