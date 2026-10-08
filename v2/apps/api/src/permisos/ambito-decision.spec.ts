import { conVista, type Contexto, type Crudo, type Persona } from '@ro/permisos';
import { autoridadDecision607, filtroDecisiones, puedeContestar } from './ambito-decision.js';

function persona(id: string, puestos: string[]): Persona {
  return { id, nombre: id, estado: 'activo', activo: true, puestos };
}

const dir = persona('p_dir', ['direccion']);
const proy = persona('p_proy', ['proyectos']);
const acc = persona('p_acc', ['account']);
const ops = persona('p_ops', ['operaciones']);

const lista = [
  { tipo: 'para_tomas', quien: 'p_acc' },
  { tipo: 'para_coti', quien: 'p_dir' },
  { tipo: 'escalada', quien: 'p_proy' },
];

describe('puestos de decisiones', () => {
  it('para_coti la contestan proyectos o dirección; el resto, solo dirección', () => {
    expect(puedeContestar(dir, 'para_tomas')).toBe(true);
    expect(puedeContestar(dir, 'para_coti')).toBe(true);
    expect(puedeContestar(proy, 'para_coti')).toBe(true);
    expect(puedeContestar(proy, 'escalada')).toBe(false);
    expect(puedeContestar(acc, 'para_coti')).toBe(false);
    expect(puedeContestar(ops, 'para_tomas')).toBe(false);
    expect(puedeContestar({}, 'para_tomas')).toBe(false);
  });

  it('dirección y operaciones ven todo; proyectos, las para_coti y las suyas; el resto, las suyas', () => {
    expect(filtroDecisiones(dir, lista)).toEqual(lista);
    expect(filtroDecisiones(ops, lista)).toEqual(lista);
    expect(filtroDecisiones(proy, lista).map((d) => d.tipo)).toEqual(['para_coti', 'escalada']);
    expect(filtroDecisiones(acc, lista).map((d) => d.quien)).toEqual(['p_acc']);
  });

  it('en «ver como», la intersección: dirección mirando un account no conserva dirección', () => {
    const cp = { cartera_ids: new Set<string>() } as Contexto;
    const vistos = conVista({ real: dir, cp }, () => filtroDecisiones(acc, lista));
    expect(vistos.map((d) => d.quien)).toEqual(['p_acc']);
  });

  it('sin la persona en el crudo, no hay autoridad', async () => {
    const r = await autoridadDecision607(
      async () => ({ crudo: { personas: [], clientes: [], asignaciones: [], alarmas: [], meta: {} } as Crudo, firma: 'a' }),
      { id: 'nadie', puestos: ['direccion'] },
      [],
    );
    expect(r).toBeNull();
  });
});
