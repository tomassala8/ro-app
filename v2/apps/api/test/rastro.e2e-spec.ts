import { BASE, leerVec, pedir, vectoresListos } from './_ayuda.js';

// Contra la app nueva (BASE = 3000), que ya atiende el rastro. Una fila nav:prueba_f52 es lo que deja hoy un clic.
interface Persona {
  id: string;
  estado?: string;
  puestos?: string[];
}
interface Rastro {
  todo?: boolean;
  registro?: { quien?: string; como?: string | null }[];
}

const personas = () => ((leerVec('crudo.json') as { personas: Persona[] }).personas ?? []).filter((p) => p.estado === 'activo');
const dePuesto = (puesto: string) => personas().find((p) => p.id !== 'tomas' && (p.puestos ?? []).includes(puesto))?.id;

describe.skipIf(!vectoresListos())('rastro en Nest', () => {
  it('verificar: dirección 200, account 403 y desde inválido 400', async () => {
    const acc = dePuesto('account');
    expect(acc, 'falta un account en el vector').toBeTruthy();
    const dir = await pedir('GET', '/api/rastro/verificar', { yo: 'tomas' });
    expect(dir.status).toBe(200);
    expect(dir.json).toMatchObject({ ok: true });
    const ajena = await pedir('GET', '/api/rastro/verificar', { yo: acc });
    expect(ajena.status).toBe(403);
    expect((ajena.json as { error?: string }).error).toBe('Solo dirección.');
    const malo = await pedir('GET', '/api/rastro/verificar?desde=x', { yo: 'tomas' });
    expect(malo.status).toBe(400);
    expect((malo.json as { error?: string }).error).toBe('«desde» es un número de fila o «anotado».');
  });

  it('POST sin la cabecera de la app', async () => {
    const r = await fetch(`${BASE}/api/rastro`, {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-RO-Yo': 'tomas', Origin: 'http://127.0.0.1:3000' },
      body: JSON.stringify({ accion: 'evento' }),
    });
    expect(r.status).toBe(403);
    expect(((await r.json()) as { error?: string }).error).toBe('Falta la cabecera de la app (X-RO-App).');
  });

  it('no anota una acción del servidor, ni «no aplica» sin motivo, ni una pantalla ajena', async () => {
    const servidor = await pedir('POST', '/api/rastro', { yo: 'tomas', cuerpo: { accion: 'ver_como' } });
    expect(servidor.status).toBe(403);
    expect((servidor.json as { error?: string }).error).toBe('Esa acción solo la apunta el servidor.');
    const motivo = await pedir('POST', '/api/rastro', { yo: 'tomas', cuerpo: { accion: 'no_aplica' } });
    expect(motivo.status).toBe(400);
    expect((motivo.json as { error?: string }).error).toBe('«No aplica» necesita un motivo.');
    const setter = dePuesto('setters');
    expect(setter, 'falta un setter en el vector').toBeTruthy();
    const ajena = await pedir('POST', '/api/rastro', { yo: setter, cuerpo: { coleccion: 'finanzas', accion: 'evento' } });
    expect(ajena.status).toBe(403);
    expect((ajena.json as { error?: string }).error).toBe('Desde el navegador solo se apunta en una pantalla que ves.');
  });

  it('en «ver como» el POST es solo lectura', async () => {
    const acc = dePuesto('account')!;
    const r = await pedir('POST', '/api/rastro', { yo: 'tomas', como: acc, cuerpo: { accion: 'evento' } });
    expect(r.status).toBe(403);
    expect((r.json as { error?: string }).error).toBe('Estás en «ver como»: es solo lectura. No se escribe nada.');
  });

  it('GET del account no trae filas de otra persona, y dirección puede anotar', async () => {
    const acc = dePuesto('account')!;
    const alta = await pedir('POST', '/api/rastro', { yo: 'tomas', cuerpo: { accion: 'nav:prueba_f52', modulo: 'app' } });
    expect(alta.status).toBe(200);
    expect(alta.json).toMatchObject({ ok: true });
    const suyo = await pedir('GET', '/api/rastro', { yo: acc });
    expect(suyo.status).toBe(200);
    const cuerpo = suyo.json as Rastro;
    expect((cuerpo.registro ?? []).length).toBeLessThanOrEqual(500);
    if (!cuerpo.todo) {
      for (const f of cuerpo.registro ?? []) {
        expect(f.quien === acc || f.como === acc).toBe(true);
      }
    }
  });

  it('HEAD /api/sesion da 405', async () => {
    const r = await fetch(`${BASE}/api/sesion`, { method: 'HEAD', headers: { 'X-RO-Yo': 'tomas' } });
    expect(r.status).toBe(405);
  });
});
