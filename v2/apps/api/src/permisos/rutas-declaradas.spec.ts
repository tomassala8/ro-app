import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { METHOD_METADATA, PATH_METADATA } from '@nestjs/common/constants.js';
import { RequestMethod } from '@nestjs/common';
import { DiscoveryModule, DiscoveryService, MetadataScanner } from '@nestjs/core';
import { Test } from '@nestjs/testing';
import { declaracionDe } from './declarar.js';
import { AppModule } from '../app.module.js';
import { PrismaService } from '../prisma/prisma.service.js';
import { SaludController } from '../salud/salud.controller.js';

// Las dos reglas que hacen que filtrar por permisos sea fácil y no se olvide nunca:
// 1) toda ruta de Nest declara @Permiso o @Publico; 2) nadie fuera de src/permisos mira puestos a mano.
const SRC = join(import.meta.dirname, '..');

function ficheros(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    return statSync(p).isDirectory() ? ficheros(p) : p.endsWith('.ts') && !p.endsWith('.spec.ts') ? [p] : [];
  });
}

interface Ruta {
  clase: Function;
  nombre: string;
  metodo: Function;
}

// Se arranca el AppModule de verdad (sin base: Prisma de mentira) y Nest dice qué controladores tiene. Así entran
// también los de módulos dinámicos (X.forRoot() con controllers) y los métodos heredados de una clase madre.
async function rutas(): Promise<{ controladores: Function[]; rutas: Ruta[] }> {
  const mod = await Test.createTestingModule({ imports: [AppModule, DiscoveryModule] })
    .overrideProvider(PrismaService)
    .useValue({})
    .compile();
  const controladores = [...new Set(mod.get(DiscoveryService).getControllers().map((w) => w.metatype as Function))];
  const escaner = mod.get(MetadataScanner);
  const lista = controladores.flatMap((clase) =>
    escaner
      .getAllMethodNames(clase.prototype)
      .map((nombre) => ({ clase, nombre, metodo: clase.prototype[nombre] as Function }))
      .filter((r) => typeof r.metodo === 'function' && Reflect.getMetadata(METHOD_METADATA, r.metodo) !== undefined),
  );
  await mod.close();
  return { controladores, rutas: lista };
}

describe('rutas declaradas', () => {
  it('Nest encuentra los controladores (la prueba no puede quedarse en verde por no ver nada)', async () => {
    const { controladores, rutas: lista } = await rutas();
    expect(controladores).toContain(SaludController);
    expect(lista.length).toBeGreaterThan(0);
  });

  it('toda ruta de Nest declara @Permiso o @Publico', async () => {
    const sinDeclarar = (await rutas()).rutas
      .filter((r) => {
        const d = declaracionDe(r.metodo, r.clase);
        return !d.permiso && !d.publico;
      })
      .map((r) => `${r.clase.name}.${r.nombre}`);
    expect(sinDeclarar).toEqual([]);
  });

  // Idea de Twenty (test/integration/endpoint-permissions): la lista entera de rutas con su permiso, guardada en el
  // repositorio. Una ruta nueva o un permiso cambiado cambia este fichero, y el cambio se ve en el diff del commit.
  // Al añadir rutas: `pnpm --filter @ro/api test -u` y revisar el diff de rutas-permisos.txt (nunca sin mirarlo).
  it('la lista de rutas y permisos es la revisada', async () => {
    const lineas = (await rutas()).rutas.map(({ clase, metodo }) => {
      const base = String(Reflect.getMetadata(PATH_METADATA, clase) ?? '').replace(/^\/|\/$/g, '');
      const verbo = RequestMethod[Reflect.getMetadata(METHOD_METADATA, metodo) as number];
      const ruta = [base, String(Reflect.getMetadata(PATH_METADATA, metodo) ?? '').replace(/^\/|\/$/g, '')].filter(Boolean).join('/');
      const { publico, permiso } = declaracionDe(metodo, clase);
      return `${verbo} /${ruta}  →  ${publico ? `público (${publico})` : JSON.stringify(permiso)}`;
    });
    await expect(lineas.sort().join('\n') + '\n').toMatchFileSnapshot('./rutas-permisos.txt');
  });

  it('nadie fuera de src/permisos decide por puestos', () => {
    const PATRON = /\bpuestos?\b\s*(\.|\[|===|!==|==)|\.includes\(\s*['"](direccion|admin)/;
    const culpables = ficheros(SRC)
      .filter((f) => !relative(SRC, f).startsWith('permisos'))
      .filter((f) => PATRON.test(readFileSync(f, 'utf8')))
      .map((f) => relative(SRC, f));
    expect(culpables).toEqual([]);
  });
});
