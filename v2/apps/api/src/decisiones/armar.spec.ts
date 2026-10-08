import { armarDecisiones } from './armar.js';

describe('armar decisiones', () => {
  const dir = () => ({ puestos: ['direccion'] });
  const acc = () => ({ puestos: ['account'] });

  it('una fila de tabla sale con id db- y el origen de la app', () => {
    const lista = armarDecisiones(
      [
        {
          id: 4,
          tipo: 'para_tomas',
          quien: 'ana',
          clave: null,
          titulo: 'Titulo',
          problema: 'Problema',
          recomendacion: 'Hazlo',
          cliente_id: null,
          creada: '2026-10-05 10:00:00',
          respuesta: null,
          respondida: null,
          respondida_por: null,
          datos: '{"prueba":"#/x"}',
        },
      ],
      [],
      dir,
    );
    expect(lista).toHaveLength(1);
    expect(lista[0]?.id).toBe('db-4');
    expect(lista[0]?.origen).toBe('Subida desde la app (local.db)');
    expect(lista[0]?.prueba).toBe('#/x');
    expect(lista[0]?.respuesta).toBeNull();
  });

  it('una decision_nueva simulada y un decidir de dirección la contestan; un account no', () => {
    const acciones = [
      {
        id: 2,
        tipo: 'decision_nueva',
        quien: 'ana',
        texto: 'subir',
        cliente_id: null,
        creada: '2026-10-05 11:00:00',
        vista_previa: '{"tipo":"para_tomas","titulo":"T","problema":"P","recomendacion":"R"}',
      },
      {
        id: 3,
        tipo: 'decidir',
        quien: 'dir',
        creada: '2026-10-05 12:00:00',
        vista_previa: '{"decision_id":"acc-2","decision":"Aprobar la recomendación","motivo":null,"delegada_en":null}',
      },
    ];
    const deDir = armarDecisiones([], acciones, (id) => (id === 'dir' ? dir() : acc()));
    expect(deDir[0]?.respondida).toBe('2026-10-05 12:00:00');
    expect(deDir[0]?.simulada).toBe(true);
    const deAcc = armarDecisiones([], acciones, () => acc());
    expect(deAcc[0]?.respondida).toBeNull();
  });
});
