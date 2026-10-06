import { huellaRastro } from '@ro/compat';
import { PrismaService } from '../prisma/prisma.service.js';
import { RastroService } from './rastro.service.js';

// Solo contra la base de pruebas ro_esc (base-limpia la rehace): nunca ro_app. Sin ella, no corre.
// La cadena con dos escritores a la vez (Nest y servir.py) la prueba migracion/pruebas_rastro_dos_escritores.sh.
const URL = process.env.DATABASE_URL ?? '';
const enEsc = URL.endsWith('/ro_esc');

describe.skipIf(!enEsc)('rastro (servir.py › _registrar) contra ro_esc', () => {
  let prisma: PrismaService;
  let rastro: RastroService;
  beforeAll(() => {
    prisma = new PrismaService();
    rastro = new RastroService(prisma);
  });
  afterAll(() => prisma?.onModuleDestroy());

  it('encadena: la huella previa de una fila es la huella de la anterior, y la huella se recalcula igual', async () => {
    const a = await rastro.registrar(null, { quien: 'p_prueba', coleccion: 'prueba_f51', accion: 'uno', datos: { n: 1 } });
    const b = await rastro.registrar(null, { quien: 'p_prueba', coleccion: 'prueba_f51', accion: 'dos', clave: 'k', como: 'p_otra' });
    expect(b).toBeGreaterThan(a);
    const filas = await prisma.db.$queryRaw<Record<string, unknown>[]>`
      SELECT r.*, h.huella AS guardada FROM registro r JOIN registro_huellas h ON h.id = r.id WHERE r.id IN (${a}, ${b}) ORDER BY r.id`;
    expect(filas).toHaveLength(2);
    const [fa, fb] = filas as [Record<string, unknown>, Record<string, unknown>];
    expect(fb.huella_previa).toBe(fa.guardada);
    for (const f of filas) {
      const h = huellaRastro((f.huella_previa as string | null) ?? null, [
        Number(f.id), f.creada, f.quien, f.como, f.coleccion, f.accion, f.clave, f.datos, f.motivo, f.anula_a, f.origen,
      ]);
      expect(h).toBe(f.guardada);
    }
  });

  it('los datos se guardan como json.dumps(…, ensure_ascii=False) de Python', async () => {
    const id = await rastro.registrar(null, { quien: 'p_prueba', coleccion: 'prueba_f51', datos: { detalle: 'Año de la ñ: «sí»', n: [1, 2.5] } });
    const [f] = await prisma.db.$queryRaw<{ datos: string }[]>`SELECT datos FROM registro WHERE id = ${id}`;
    expect(f?.datos).toBe('{"detalle": "Año de la ñ: «sí»", "n": [1, 2.5]}');
  });
});
