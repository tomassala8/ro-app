import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { METHOD_METADATA } from '@nestjs/common/constants.js';
import { CLAVE_PERMISO, CLAVE_PUBLICO } from './declarar.js';
import { AppModule } from '../app.module.js';

// Las dos reglas que hacen que filtrar por permisos sea fácil y no se olvide nunca:
// 1) toda ruta de Nest declara @Permiso o @Publico; 2) nadie fuera de src/permisos mira puestos a mano.
const SRC = join(import.meta.dirname, '..');

function ficheros(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    return statSync(p).isDirectory() ? ficheros(p) : p.endsWith('.ts') && !p.endsWith('.spec.ts') ? [p] : [];
  });
}

function controladores(): Function[] {
  const vistos = new Set<Function>();
  const visitar = (m: Function) => {
    for (const c of (Reflect.getMetadata('controllers', m) ?? []) as Function[]) vistos.add(c);
    for (const i of (Reflect.getMetadata('imports', m) ?? []) as Function[]) if (typeof i === 'function') visitar(i);
  };
  visitar(AppModule);
  return [...vistos];
}

describe('rutas declaradas', () => {
  it('toda ruta de Nest declara @Permiso o @Publico', () => {
    const sinDeclarar: string[] = [];
    for (const c of controladores()) {
      const deClase = Reflect.getMetadata(CLAVE_PERMISO, c) ?? Reflect.getMetadata(CLAVE_PUBLICO, c);
      for (const nombre of Object.getOwnPropertyNames(c.prototype)) {
        const metodo = c.prototype[nombre];
        if (typeof metodo !== 'function' || Reflect.getMetadata(METHOD_METADATA, metodo) === undefined) continue;
        const declarada = deClase ?? Reflect.getMetadata(CLAVE_PERMISO, metodo) ?? Reflect.getMetadata(CLAVE_PUBLICO, metodo);
        if (!declarada) sinDeclarar.push(`${c.name}.${nombre}`);
      }
    }
    expect(sinDeclarar).toEqual([]);
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
