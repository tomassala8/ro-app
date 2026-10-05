import { readFileSync } from 'node:fs';
import { beforeAll, describe, expect, it } from 'vitest';
import {
  BASE,
  enBlanca,
  errorDe,
  hojas,
  leerVec,
  pedir,
  pedirConHost,
  personasPorPuesto,
  vectoresListos,
  type PersonaCruda,
} from './_ayuda.js';

const LISTO = vectoresListos();
if (!LISTO) console.warn('regresión de permisos SALTADA: falta RO_VECTORES');

const TEXTO_VER_COMO = 'Estás en «ver como»: es solo lectura. No se escribe nada.';
const LECTURA_POR_POST = ['/api/ver_dato'];
/**
 * N-25 · Rutas POST que este spec NUNCA llama. Si una no bloqueara «ver como», un POST con `{}` sería una
 * escritura real contra la app de hoy (12:58 del 5-oct: un POST a `/api/recarga` tocó `data/`, 16 avisos y
 * dejó la tubería suelta 33 minutos). Cualquier ruta cuyo nombre contenga uno de estos trozos queda fuera del
 * bucle de 8.2; su guarda se comprueba en 8.2b con el código de la guarda, sin llamarla.
 */
const NO_SE_LLAMAN = [
  '/api/recarga',
  '/api/altas/',
  'recarga',
  'alta',
  'envio',
  'correo',
  'publicar',
  'tuberia',
  'importar',
  'sincron',
  'exportar',
  'llave',
];
function noSeLlama(ruta: string): boolean {
  const r = ruta.toLowerCase();
  return NO_SE_LLAMAN.some((trozo) => r.includes(trozo));
}
const GET_FIJAS = [
  '/api/sesion',
  '/api/indicadores',
  '/api/ajustes',
  '/api/rastro',
  '/api/acciones',
  '/api/recarga',
  '/api/avisos',
  '/api/decisiones',
  '/api/buscar/indice',
  '/api/contadores',
  '/api/perfil',
  '/api/preferencias',
  '/api/opiniones',
  '/api/respuestas_mili',
  '/api/rastro/verificar',
  '/api/salud',
  '/api/ia/cerebro?q=los%20leads%20no%20vienen%20a%20la%20reuni%C3%B3n',
  '/api/ia/cerebro?id=rb_sano_mantener',
];
const SOLO_FORMA = new Set(['/api/rastro', '/api/rastro/verificar', '/api/salud']);
const CLAVES_CUOTA = /(?:^|[_\-.])(?:cuota(?![_\-.]horas(?:$|[_\-.]))|fee|importe|mrr|precio\w*|tarifa(?![_\-.](?:hora|ruta|busqueda)(?:$|[_\-.])))(?:$|[_\-.])/i;
const CLAVES_COBROS = /(?:^|[_\-.])(?:facturas?\w*|facturado\w*|cobrad\w*|impag\w*|pendiente_cobro|revenue|invoice_total)(?:$|[_\-.])/i;
const CLAVES_INVERSION = /(?:^|[_\-.])(?:gasto\w*|coste(?![_\-.]horas(?:$|[_\-.]))\w*|cpl\w*|cpc\w*|cpm\w*|inversion\w*|spend|budget_ads|presupuesto_ads|ad_spend|cost_per_lead|cost_per_click|importe_publicidad)(?:$|[_\-.])/i;
const CLAVES_LEAD = /(?:^|[_\-.])(?:nombre_lead|lead_name|nombre_m|telefono|tel|tel_m|correo_lead|email_lead|lead_email|lead_phone|phone_lead|movil|móvil|whatsapp|telefono_contacto|dni|nif|nie|iban)(?:$|[_\-.])|^email$/i;

interface FilaPermiso {
  ver: Record<string, { ok?: boolean }>;
  cartera: Record<string, string[]>;
  ambito: string;
}

function rutasPost(): string[] {
  const inventario = JSON.parse(
    readFileSync(new URL('../../../../migracion/inventario/rutas_api.json', import.meta.url), 'utf8'),
  ) as { metodo: string; ruta: string }[];
  return inventario.filter((r) => r.metodo === 'POST').map((r) => r.ruta);
}

function rutaProbada(ruta: string): string {
  return ruta.endsWith('/') ? `${ruta}x` : ruta;
}

function ve(fila: FilaPermiso, tipo: string, cid?: string): boolean {
  if (fila.ver[`${tipo}||`]?.ok === true) return true;
  return Boolean(cid && fila.ver[`${tipo}|${cid}|`]?.ok === true);
}

function marcaDe(clave: string): 'cuota' | 'cobros' | 'inversion' | 'lead' | null {
  if (CLAVES_CUOTA.test(clave)) return 'cuota';
  if (CLAVES_COBROS.test(clave)) return 'cobros';
  if (CLAVES_INVERSION.test(clave)) return 'inversion';
  if (CLAVES_LEAD.test(clave)) return 'lead';
  return null;
}

function revisarDinero(obj: unknown, camino: string[], cid: string | undefined, fila: FilaPermiso, malas: string[], l12: string[]): void {
  if (Array.isArray(obj)) {
    obj.forEach((x, i) => revisarDinero(x, [...camino, String(i)], cid, fila, malas, l12));
    return;
  }
  if (!obj || typeof obj !== 'object') return;
  const rec = obj as Record<string, unknown>;
  const aqui = typeof rec.cliente_id === 'string' && rec.cliente_id ? rec.cliente_id : cid;
  for (const [k, v] of Object.entries(rec)) {
    const sig = [...camino, k];
    const marca = marcaDe(k);
    const valorEscalar = v === null || typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean';
    if (marca && valorEscalar && !sig.includes('modulos_puestos')) {
      const tipos = marca === 'lead' ? ['lead', 'mensaje_cliente'] : [marca];
      const ok = tipos.some((tipo) => ve(fila, tipo, aqui));
      if (!ok) {
        const ruta = sig.join('.');
        if (sig.includes('vista_previa')) l12.push(ruta);
        else malas.push(ruta);
      }
    }
    revisarDinero(v, sig, aqui, fila, malas, l12);
  }
}

function carteraDe(fila: FilaPermiso): Set<string> {
  const ids = new Set<string>();
  for (const lista of Object.values(fila.cartera ?? {})) for (const id of lista) ids.add(id);
  return ids;
}

function idsCliente(obj: unknown, out: string[]): void {
  if (Array.isArray(obj)) {
    obj.forEach((x) => idsCliente(x, out));
    return;
  }
  if (!obj || typeof obj !== 'object') return;
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    if (k === 'cliente_id' && typeof v === 'string' && v) out.push(v);
    idsCliente(v, out);
  }
}

function idsDeListaClientes(json: unknown): string[] {
  if (!json || typeof json !== 'object') return [];
  const o = json as Record<string, unknown>;
  const datos = o.datos && typeof o.datos === 'object' ? (o.datos as Record<string, unknown>) : o;
  const lista = (Array.isArray(datos.clientes) ? datos.clientes : Array.isArray(o.clientes) ? o.clientes : []) as { id?: unknown }[];
  return lista.map((c) => c.id).filter((id): id is string => typeof id === 'string');
}

describe.skipIf(!LISTO)('regresión de permisos (anexo punto 8)', () => {
  if (!LISTO) return;
  const permisos = leerVec('permisos.json') as { por_persona: Record<string, FilaPermiso> };
  const crudo = leerVec('crudo.json') as { personas: PersonaCruda[]; clientes: { id: string }[] };
  const porPuesto = personasPorPuesto(crudo);
  const tomas = crudo.personas.find((p) => p.id === 'tomas')?.id;
  const account = crudo.personas.find((p) => p.estado === 'activo' && p.id !== 'tomas' && (p.puestos ?? []).includes('account'))?.id;
  const vistas = [
    ['account', account],
    ['setters', porPuesto.setters],
    ['operaciones', porPuesto.operaciones],
  ] as const;

  beforeAll(async () => {
    const ctrl = new AbortController();
    const plazo = setTimeout(() => ctrl.abort(), 5000);
    try {
      const r = await fetch(`${BASE}/vivo`, { signal: ctrl.signal });
      if (!r.ok) throw new Error('la app nueva no responde en 3000');
    } catch {
      throw new Error('la app nueva no responde en 3000');
    } finally {
      clearTimeout(plazo);
    }
    expect(tomas, 'el vector no tiene a tomas').toBe('tomas');
  });

  it('8.2 toda escritura en «ver como» es 403, salvo ver_dato', async () => {
    expect(account, 'falta un account activo').toBeTruthy();
    // N-25: si una ruta no bloquea «ver como», este POST ya es una escritura real. Se corta en la primera.
    let primeraNoBloqueada: string | null = null;
    for (const ruta of rutasPost()) {
      if (noSeLlama(ruta)) continue; // N-25: su guarda se comprueba en 8.2b, sin llamarla
      const r = await pedir('POST', rutaProbada(ruta), { yo: tomas, como: account, cuerpo: {} });
      const bloqueada = r.status === 403 && errorDe(r.json) === TEXTO_VER_COMO;
      if (LECTURA_POR_POST.includes(ruta)) {
        if (bloqueada) {
          primeraNoBloqueada = `${ruta} (debía dejar pasar «ver como»)`;
          break;
        }
        continue;
      }
      if (!bloqueada) {
        primeraNoBloqueada = ruta;
        break;
      }
    }
    expect(primeraNoBloqueada, 'primera ruta POST que no da 403 en «ver como»').toBeNull();
  }, 600_000);

  it('8.2b las rutas con efecto fuera de la base no se llaman: la guarda de «ver como» es global', () => {
    const sinLlamar = rutasPost().filter(noSeLlama);
    expect(sinLlamar, 'el inventario debe traer al menos /api/recarga entre las que no se llaman').toContain('/api/recarga');
    const raiz = new URL('../../../../', import.meta.url);
    const guarda = readFileSync(new URL('v2/apps/api/src/permisos/permisos.guard.ts', raiz), 'utf8');
    expect(guarda).toContain("const escribe = metodo !== 'GET' && !declaracion.lecturaPorPost;");
    expect(guarda).toContain('if (escribe && req.vista?.como) throw new ForbiddenException(');
    const servir = readFileSync(new URL('servir.py', raiz), 'utf8');
    expect(servir).toContain('if solo_lectura and ruta != "/api/ver_dato":');
    expect(servir).toContain(TEXTO_VER_COMO);
  });

  it('8.3 «ver como» no enseña lo que no verían las dos personas', async () => {
    const malas: string[] = [];
    for (const [puesto, id] of vistas) {
      expect(id, `falta una persona de ${puesto}`).toBeTruthy();
      for (const ruta of GET_FIJAS) {
        const A = await pedir('GET', ruta, { yo: id });
        const B = await pedir('GET', ruta, { yo: tomas, como: id });
        const C = await pedir('GET', ruta, { yo: tomas });
        if (B.status === 200) {
          const base = ruta.split('?')[0] ?? ruta;
          if (base === '/api/indicadores') continue;
          const firma = (json: unknown, soloClaves: boolean) => {
            const m = new Map<string, number>();
            for (const [camino, valor] of hojas(json)) {
              if (enBlanca(camino)) continue;
              const norm = camino.split('.').map((p) => (/^\d+$/.test(p) ? '#' : p)).join('.');
              const clave = soloClaves ? norm : `${norm}\0${JSON.stringify(valor)}`;
              m.set(clave, (m.get(clave) ?? 0) + 1);
            }
            return m;
          };
          const soloClaves = SOLO_FORMA.has(base);
          const enA = firma(A.json, soloClaves);
          const enC = firma(C.json, soloClaves);
          const enB = firma(B.json, soloClaves);
          for (const [clave, n] of enB) {
            if (n > (enA.get(clave) ?? 0) + (enC.get(clave) ?? 0)) malas.push(`${puesto} ${base} ${clave.split('\0')[0]}`);
          }
        }
      }
    }
    expect([...new Set(malas)].sort()).toEqual([]);
  }, 600_000);

  // L-02 (servir.py: `/api/rastro` con `mirando`, `/api/acciones` sin ?modulo=): en «ver como», el rastro es solo
  // el de ESTA inspección y las acciones personales de la persona vista no se leen. Sin 403.
  it('L-02 /api/acciones en «ver como» vacías y /api/rastro solo de esta inspección', async () => {
    expect(account, 'falta un account activo').toBeTruthy();
    const r = await pedir('GET', '/api/rastro', { yo: tomas, como: account });
    expect(r.status).toBe(200);
    const cuerpo = r.json as { todo?: boolean; registro?: { quien?: string; como?: string }[]; acciones?: unknown[] };
    expect(cuerpo.todo).toBe(false);
    expect(cuerpo.acciones).toEqual([]);
    const ajenas = (cuerpo.registro ?? []).filter((f) => !(f.quien === tomas && f.como === account));
    expect(ajenas.length, 'filas del rastro que no son de esta inspección').toBe(0);
    const a = await pedir('GET', '/api/acciones', { yo: tomas, como: account });
    expect(a.status).toBe(200);
    expect(a.json).toEqual({ modulo: null, acciones: [] });
  });
  it.todo('L-50 /api/indicadores en «ver como» trae textos que no están en ninguna de las dos respuestas solas');

  it('8.4 las claves de dinero y de leads solo salen si el puesto las ve', async () => {
    const malas: string[] = [];
    const l12: string[] = [];
    const rutas = ['/api/sesion', '/api/indicadores', '/api/decisiones', '/api/acciones?modulo=mi-dia'];
    for (const [puesto, id] of Object.entries(porPuesto)) {
      const fila = permisos.por_persona[id];
      if (!fila) continue;
      for (const ruta of rutas) {
        const r = await pedir('GET', ruta, { yo: id });
        if (r.status !== 200) continue;
        const estasMalas: string[] = [];
        const estasL12: string[] = [];
        revisarDinero(r.json, [], undefined, fila, estasMalas, estasL12);
        for (const c of estasMalas) malas.push(`${puesto} ${ruta} ${c}`);
        for (const c of estasL12) l12.push(`${puesto} ${ruta} ${c}`);
      }
    }
    expect(l12, 'L-12 importe dentro de vista_previa').toEqual([]);
    expect(malas).toEqual([]);
  }, 600_000);

  it('8.5 un account no recibe un cliente ajeno a su cartera', async () => {
    const ajenos: string[] = [];
    for (const p of crudo.personas) {
      if (p.estado !== 'activo' || !(p.puestos ?? []).includes('account')) continue;
      const fila = permisos.por_persona[p.id];
      if (!fila || fila.ambito === 'todos') continue;
      const cartera = carteraDe(fila);
      const s = await pedir('GET', '/api/sesion', { yo: p.id });
      expect(s.status, 'sesion de account').toBe(200);
      for (const id of idsDeListaClientes(s.json)) if (!cartera.has(id)) ajenos.push('clientes.id');
      const hojasId: string[] = [];
      idsCliente(s.json, hojasId);
      for (const id of hojasId) if (!cartera.has(id)) ajenos.push('cliente_id');
      const ajeno = crudo.clientes.find((c) => !cartera.has(c.id))?.id;
      if (!ajeno) continue;
      const ficha = await pedir('GET', `/api/cliente/${ajeno}`, { yo: p.id });
      if (ficha.status !== 403 && ficha.status !== 404) ajenos.push(`ficha ${ficha.status}`);
      const meta = await pedir('GET', `/api/modulo/paneles/meta/${ajeno}`, { yo: p.id });
      if (meta.status === 200) ajenos.push('L-05 paneles/meta 200');
      else if (meta.status !== 403 && meta.status !== 404) ajenos.push(`meta ${meta.status}`);
      if (!process.env.RO_L11_ABIERTO) {
        const accion = await pedir('POST', '/api/acciones', {
          yo: p.id,
          cuerpo: { tipo: 'traspaso', herramienta: 'app', modulo: 'ficha', objeto: ajeno, texto: 'prueba L-11' },
        });
        if (accion.status === 200 || accion.status === 201) ajenos.push('L-11 acciones escribio');
        else if (accion.status !== 403 && accion.status !== 400) ajenos.push(`accion ${accion.status}`);
      }
    }
    expect(ajenos).toEqual([]);
  }, 600_000);

  it('8.6 HEAD, OPTIONS y un Host ajeno no cuelan datos', async () => {
    expect(tomas).toBe('tomas');
    const head = await pedir('HEAD', '/api/sesion', { yo: tomas });
    expect(head.status).toBe(405);
    const options = await pedir('OPTIONS', '/api/sesion', { yo: tomas });
    expect(options.status).toBe(405);
    expect(errorDe(options.json)).toBe('Método no permitido.');
    const privado = await pedir('HEAD', '/data/_privado/x.json', { yo: tomas });
    expect([405, 404]).toContain(privado.status);
    expect(privado.status).not.toBe(200);
    const host = await pedirConHost('/api/sesion', 'evil.test', tomas ?? '');
    expect(host).toBe(403);
  }, 120_000);
});
