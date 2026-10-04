import { comprobarEntorno } from './entorno.js';

const BIEN = { DATABASE_URL: 'postgresql://ro:ro@127.0.0.1:5432/ro_app', RO_IDENTIDAD: 'local' };
function falla(env: NodeJS.ProcessEnv): boolean {
  const salir = vi.spyOn(process, 'exit').mockImplementation((() => undefined) as never);
  const error = vi.spyOn(console, 'error').mockImplementation(() => undefined);
  comprobarEntorno(env);
  const r = salir.mock.calls.length > 0;
  salir.mockRestore();
  error.mockRestore();
  return r;
}

describe('entorno al arrancar', () => {
  it('en local, con lo mínimo, arranca', () => expect(falla({ ...BIEN, RO_RELOJ: '2026-10-05T07:30' })).toBe(false));
  it('sin base, no arranca', () => expect(falla({ RO_IDENTIDAD: 'local' })).toBe(true));
  it('en producción, ni identidad local ni reloj fijo', () => {
    const prod = { ...BIEN, RO_ENTORNO: 'produccion', RO_IDENTIDAD: 'access', RO_LEGADO_URL: 'http://ro-legado:10000' };
    expect(falla(prod)).toBe(false);
    expect(falla({ ...prod, RO_IDENTIDAD: 'local' })).toBe(true);
    expect(falla({ ...prod, RO_RELOJ: '2026-10-05T07:30' })).toBe(true);
    expect(falla({ ...prod, RO_LEGADO_URL: undefined })).toBe(true);
  });
  it('HOST solo 127.0.0.1 o 0.0.0.0', () => expect(falla({ ...BIEN, HOST: '192.168.1.20' })).toBe(true));
  it('0.0.0.0 con identidad local solo dentro de un contenedor', () => {
    expect(falla({ ...BIEN, RO_IDENTIDAD: 'local', HOST: '0.0.0.0' })).toBe(true);
    expect(falla({ ...BIEN, RO_IDENTIDAD: 'local', HOST: '0.0.0.0', RO_EN_CONTENEDOR: '1' })).toBe(false);
    expect(falla({ ...BIEN, RO_IDENTIDAD: 'access', HOST: '0.0.0.0' })).toBe(false);
  });
});
