import { BASE, leerVec, pedir, vectoresListos } from './_ayuda.js';

// GET /api/sesion ya la atiende Nest: la app nueva (BASE) responde lo mismo que servir.py (el legado, sin Nest delante).
// Una persona de dirección, un account y un setter (regla de seguridad), y «ver como». Datos reales: solo se comparan
// en memoria; los fallos dicen la ruta de la clave, no el valor.
const LEGADO = process.env.RO_LEGADO_E2E ?? 'http://127.0.0.1:8771';

type Obj = Record<string, unknown>;
interface Persona {
  id: string;
  estado?: string;
  puestos?: string[];
}

const esNumero = (x: unknown) => typeof x === 'number';
/** Como contrato.py › diferencias: 12.0 y 12 son el mismo número; «hora» es la del reloj y solo se mira su forma. */
function diferencias(a: unknown, b: unknown, ruta = ''): string[] {
  if (esNumero(a) && esNumero(b)) return Math.abs((a as number) - (b as number)) <= 1e-9 ? [] : [`${ruta}: número`];
  if (typeof a !== typeof b || Array.isArray(a) !== Array.isArray(b) || (a === null) !== (b === null)) return [`${ruta}: tipo`];
  if (Array.isArray(a)) {
    const bb = b as unknown[];
    const out = a.length !== bb.length ? [`${ruta}: largo`] : [];
    a.forEach((x, i) => out.push(...diferencias(x, bb[i], `${ruta}[${i}]`)));
    return out;
  }
  if (a && typeof a === 'object') {
    const ao = a as Obj, bo = b as Obj;
    const out: string[] = [];
    for (const k of new Set([...Object.keys(ao), ...Object.keys(bo)])) {
      if (!(k in ao) || !(k in bo)) out.push(`${ruta}/${k}: falta`);
      else out.push(...diferencias(ao[k], bo[k], `${ruta}/${k}`));
    }
    return out;
  }
  return a === b ? [] : [`${ruta}: valor`];
}

async function sesionDe(base: string, yo?: string, como?: string) {
  const h: Record<string, string> = { Accept: 'application/json' };
  if (yo) h['X-RO-Yo'] = yo;
  if (como) h['X-RO-Como'] = como;
  const r = await fetch(`${base}/api/sesion`, { headers: h });
  const json = (await r.json().catch(() => null)) as Obj | null;
  return { status: r.status, json, etag: r.headers.get('etag') };
}

describe.skipIf(!vectoresListos())('GET /api/sesion en Nest = servir.py', () => {
  const personas = () => ((leerVec('crudo.json') as { personas: Persona[] }).personas ?? []).filter((p) => p.estado === 'activo');
  const dePuesto = (puesto: string) => personas().find((p) => p.id !== 'tomas' && (p.puestos ?? []).includes(puesto))?.id;

  it('sin ETag, como servir.py', async () => {
    const r = await pedir('GET', '/api/sesion', { yo: 'tomas' });
    expect(r.status).toBe(200);
    expect(r.headers.get('etag')).toBeNull();
    expect(r.headers.get('content-type')).toMatch(/^application\/json/);
  });

  it('dirección, account y setter reciben lo mismo que en servir.py', async () => {
    const quienes = ['tomas', dePuesto('account'), dePuesto('setters')];
    expect(quienes.every(Boolean), 'faltan personas de algún puesto en el vector').toBe(true);
    for (const yo of quienes as string[]) {
      const [a, b] = [await sesionDe(LEGADO, yo), await sesionDe(BASE, yo)];
      expect(b.status, yo).toBe(a.status);
      expect(b.json?.hora).toMatch(/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d$/);
      expect(diferencias({ ...a.json, hora: 'H' }, { ...b.json, hora: 'H' }), yo).toEqual([]);
    }
  });

  it('en «ver como» también, y solo lectura', async () => {
    const acc = dePuesto('account')!;
    const [a, b] = [await sesionDe(LEGADO, 'tomas', acc), await sesionDe(BASE, 'tomas', acc)];
    expect(b.status).toBe(200);
    expect(b.json?.soloLectura).toBe(true);
    expect((b.json?.real as Obj | undefined)?.id).toBe('tomas');
    expect((b.json?.persona as Obj | undefined)?.id).toBe(acc);
    expect(diferencias({ ...a.json, hora: 'H' }, { ...b.json, hora: 'H' })).toEqual([]);
  });

  it('sin identidad, con una persona que no existe o «ver como» sin permiso: mismo código y texto', async () => {
    const acc = dePuesto('account')!;
    const casos: [string | undefined, string | undefined][] = [[undefined, undefined], ['nadie-de-prueba', undefined], [acc, 'tomas']];
    for (const [yo, como] of casos) {
      const [a, b] = [await sesionDe(LEGADO, yo, como), await sesionDe(BASE, yo, como)];
      expect([b.status, b.json], `${yo}|${como}`).toEqual([a.status, a.json]);
    }
  });
});
