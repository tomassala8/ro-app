import { errorDe, leerVec, pedir, personasPorPuesto, vectoresListos } from './_ayuda.js';

interface Persona {
  id: string;
  estado?: string;
  puestos?: string[];
}

const crudo = () => leerVec('crudo.json') as { personas: Persona[] };

function una(puesto: string, sin: string[]): string | undefined {
  return crudo().personas.find((p) => {
    const pu = p.puestos ?? [];
    return p.estado === 'activo' && pu.includes(puesto) && sin.every((s) => !pu.includes(s));
  })?.id;
}

describe.skipIf(!vectoresListos())('ajustes y ver_dato en Nest', () => {
  it('GET /api/ajustes: dirección edita, account no entra, «ver como» no edita', async () => {
    const mapa = personasPorPuesto(crudo());
    const dir = mapa.direccion;
    const acc = una('account', ['direccion', 'operaciones', 'rrhh']);
    const ops = una('operaciones', ['direccion']);
    expect(dir && acc && ops).toBeTruthy();

    const deDir = await pedir('GET', '/api/ajustes', { yo: dir });
    expect(deDir.status).toBe(200);
    expect((deDir.json as { puedeEditar?: boolean }).puedeEditar).toBe(true);

    const deAcc = await pedir('GET', '/api/ajustes', { yo: acc });
    expect(deAcc.status).toBe(403);
    expect(errorDe(deAcc.json)).toBe('Ajustes es de Mili y Tomás (RRHH, en resumen).');

    const comoAcc = await pedir('GET', '/api/ajustes', { yo: dir, como: acc });
    expect(comoAcc.status).toBe(403);
    expect(errorDe(comoAcc.json)).toBe('Ajustes es de Mili y Tomás (RRHH, en resumen).');

    const comoOps = await pedir('GET', '/api/ajustes', { yo: dir, como: ops });
    expect(comoOps.status).toBe(200);
    expect((comoOps.json as { puedeEditar?: boolean }).puedeEditar).toBe(false);
  });

  it('los POST mal formados dan el texto de servir.py y no escriben', async () => {
    const mapa = personasPorPuesto(crudo());
    const dir = mapa.direccion;
    const acc = una('account', ['direccion', 'operaciones', 'rrhh']);
    expect(dir && acc).toBeTruthy();

    const ajeno = await pedir('POST', '/api/ajustes/persona', { yo: acc, cuerpo: { id: dir, cambios: { alias: 'x' } } });
    expect(ajeno.status).toBe(403);
    expect(errorDe(ajeno.json)).toBe('Personas y asignaciones las mantienen Mili y Tomás.');

    const sueldo = await pedir('POST', '/api/ajustes/persona', { yo: dir, cuerpo: { id: dir, cambios: { sueldo: 1 } } });
    expect(sueldo.status).toBe(400);
    expect(errorDe(sueldo.json)).toBe('Los sueldos no se cambian desde Ajustes.');

    const ruta = await pedir('POST', '/api/ajustes/x', { yo: dir, cuerpo: {} });
    expect(ruta.status).toBe(404);
    expect(errorDe(ruta.json)).toBe('No existe esa ruta de Ajustes.');

    const leads = await pedir('POST', '/api/ver_dato', { yo: dir, cuerpo: { almacen: 'leads', ref: 'a', campo: 'b' } });
    expect(leads.status).toBe(400);
    expect(errorDe(leads.json)).toBe('Almacén no válido (debe ser una carpeta _privado/ de data/).');

    const como = await pedir('POST', '/api/ver_dato', {
      yo: dir,
      como: acc,
      cuerpo: { almacen: 'no/_privado/no', ref: 'a', campo: 'b' },
    });
    expect(como.status).toBe(403);
    expect(errorDe(como.json)).toBe('Ese almacén no está en reglas_permisos.json (almacenes_privados): no se abre.');
  });
});
