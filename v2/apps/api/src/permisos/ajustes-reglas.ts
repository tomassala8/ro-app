import { horaMadrid } from '@ro/compat';
import { contexto, reglas, ver, type Crudo, type Persona } from '@ro/permisos';

/** servir.py › ahora(), sin RO_RELOJ: hora de pared de Madrid «AAAA-MM-DDTHH:MM:SS». */
export function horaLocalSinZona(ahora: Date = new Date()): string {
  return horaMadrid(ahora, '');
}

const MANDO_DEFECTO = ['direccion', 'finanzas_direccion', 'rrhh', 'operaciones', 'ventas_ro', 'administracion'];

type Fila = Record<string, unknown>;
type CrudoAjustes = Crudo & { para_confirmar?: unknown };

function esFila(x: unknown): x is Fila {
  return !!x && typeof x === 'object' && !Array.isArray(x);
}

function idsPuesto(): Set<string> {
  return new Set(reglas().puestos.map((p) => p.id));
}

/** reglas_permisos.json › puestos_solo_tomas. Lista vacía cae al defecto, como el `or` de Python. */
export function puestosMando(): Set<string> {
  const lista = (reglas() as { puestos_solo_tomas?: string[] }).puestos_solo_tomas;
  return new Set(lista && lista.length ? lista : MANDO_DEFECTO);
}

/** «direccion» en los puestos de ESA persona (la real en Ajustes), no la intersección de «ver como». */
export function esDireccion(persona: { puestos?: readonly string[] } | null | undefined): boolean {
  return (persona?.puestos ?? []).includes('direccion');
}

function distinto(a: unknown, b: unknown): boolean {
  if (Array.isArray(a) || Array.isArray(b)) {
    if (!Array.isArray(a) || !Array.isArray(b) || a.length !== b.length) return true;
    return a.some((x, i) => distinto(x, b[i]));
  }
  return a !== b;
}

function valor(p: Fila, k: string): unknown {
  return p[k] === undefined ? null : p[k];
}

/**
 * servir.py:3670-3684. null si el cambio cabe; si no, [código, texto] en el mismo orden que el fichero.
 * `activo` no cuenta como cambio (lo pone el estado).
 */
export function reglasCambioPersona(
  real: { id: string; puestos?: readonly string[] },
  p: Fila,
  cambios: Fila,
): [number, string] | null {
  const cambia = new Set<string>();
  for (const [k, x] of Object.entries(cambios)) {
    if (k !== 'activo' && distinto(x, valor(p, k))) cambia.add(k);
  }
  if (Array.isArray(cambios.puestos)) {
    const a = new Set(cambios.puestos);
    const b = new Set(Array.isArray(p.puestos) ? p.puestos : []);
    if (a.size === b.size && [...a].every((x) => b.has(x))) cambia.delete('puestos');
  }
  const direccion = esDireccion(real);
  const mando = puestosMando();
  if (cambia.has('puestos') && p.id === real.id) {
    return [403, 'Nadie cambia sus propios puestos: pídeselo a Tomás.'];
  }
  if (cambia.has('puestos') && !direccion) {
    const nuevos = new Set(Array.isArray(cambios.puestos) ? (cambios.puestos as unknown[]) : []);
    const viejos = new Set(Array.isArray(p.puestos) ? (p.puestos as unknown[]) : []);
    const sim = [...nuevos].filter((x) => !viejos.has(x)).concat([...viejos].filter((x) => !nuevos.has(x)));
    if (sim.some((x) => mando.has(String(x)))) {
      return [403, 'Dar o quitar dirección, finanzas de dirección, RRHH, operaciones, ventas de RO o administración solo lo hace Tomás.'];
    }
  }
  const puestosPersona = Array.isArray(p.puestos) ? (p.puestos as string[]) : [];
  if (puestosPersona.includes('direccion') && cambia.size && !direccion) {
    return [403, 'Los datos de una persona de dirección solo los cambia Tomás.'];
  }
  if (puestosPersona.some((x) => mando.has(x)) && cambia.size && !direccion) {
    return [403, 'A una persona con un puesto de mando (operaciones, RRHH, administración, ventas de RO…) solo la cambia Tomás.'];
  }
  if ('estado' in cambios && cambios.estado !== valor(p, 'estado') && (cambios.estado === 'baja' || p.estado === 'baja')) {
    return [400, 'Las bajas y reincorporaciones se gestionan desde Altas y bajas.'];
  }
  return null;
}

/** servir.py:3654-3656. La lista se imprime como Python: ['x', 'y']. null si vale. */
export function errorPuestos(puestos: unknown): string | null {
  if (!Array.isArray(puestos)) throw new TypeError('puestos');
  const ids = idsPuesto();
  const malos = puestos.filter((x) => typeof x !== 'string' || !ids.has(x));
  if (malos.length || puestos.length === 0) {
    const dentro = malos.length ? '[' + malos.map((m) => "'" + String(m) + "'").join(', ') + ']' : 'ninguno';
    return `Puestos no válidos: ${dentro}`;
  }
  return null;
}

function unica(filas: unknown, identidad: unknown): Fila | null {
  if (typeof identidad !== 'string' || !identidad || !Array.isArray(filas)) return null;
  const xs = filas.filter((x) => esFila(x) && x.id === identidad);
  return xs.length === 1 && xs[0] ? xs[0] : null;
}

function fechaOk(v: unknown): boolean {
  if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(v)) return false;
  const [y, m, d] = v.split('-').map(Number) as [number, number, number];
  const dt = new Date(Date.UTC(y, m - 1, d));
  return dt.getUTCFullYear() === y && dt.getUTCMonth() === m - 1 && dt.getUTCDate() === d;
}

function sillasDe(puestos: unknown): string[] {
  const mapa = (reglas() as { sillas_de_puesto?: Record<string, string[]> }).sillas_de_puesto ?? {};
  if (!Array.isArray(puestos)) return [];
  return puestos.flatMap((pu) => (typeof pu === 'string' ? (mapa[pu] ?? []) : []));
}

/**
 * ajustes_validacion_579.asignacion. null si no vale.
 * es_activo_id = el cliente está en el crudo ya limpio (F5.1).
 */
export function validarAsignacion579(crudo: Crudo, b: unknown, hoy: string): Fila | null {
  if (!esFila(b)) return null;
  const op = b.operacion;
  if (op !== 'crear' && op !== 'cerrar' && op !== 'confirmar') return null;
  const p = unica(crudo.personas, b.persona_id);
  const c = unica(crudo.clientes, b.cliente_id);
  if (!p || p.estado !== 'activo' || p.activo === false || !c || c.activo === false || c.estado === 'baja') return null;
  if (typeof c.id !== 'string' || !crudo.clientes.some((x) => x.id === c.id)) return null;
  const roles = p.puestos;
  const ids = idsPuesto();
  if (!Array.isArray(roles) || !roles.length || !roles.every((x) => typeof x === 'string' && ids.has(x)) || new Set(roles).size !== roles.length) {
    return null;
  }
  const silla = b.silla;
  const sillas = (reglas() as { sillas?: string[] }).sillas ?? [];
  const dePuesto = sillasDe(roles);
  if (typeof silla !== 'string' || !sillas.includes(silla) || !dePuesto.includes(silla)) return null;
  for (const key of ['principal', 'suplencia'] as const) {
    if (key in b && typeof b[key] !== 'boolean') return null;
  }
  let principal = 'principal' in b ? b.principal : true;
  const suplencia = 'suplencia' in b ? b.suplencia : false;
  let desde = b.desde;
  let hasta = b.hasta;
  if ((desde !== undefined && desde !== null && !fechaOk(desde)) || (hasta !== undefined && hasta !== null && !fechaOk(hasta))) return null;
  if (op === 'crear') {
    desde = desde || hoy;
    if (!fechaOk(desde) || (suplencia && (!hasta || principal))) return null;
  }
  if (op === 'cerrar') {
    hasta = hasta || hoy;
    if (!fechaOk(hasta)) return null;
  }
  if (desde && hasta && String(hasta) < String(desde)) return null;
  const titular = b.titular_id ?? null;
  if (b.titular_id !== undefined && b.titular_id !== null) {
    const t = unica(crudo.personas, titular);
    if (
      !suplencia ||
      !t ||
      t.id === p.id ||
      t.estado !== 'activo' ||
      t.activo === false ||
      !sillasDe(t.puestos).includes(silla)
    ) {
      return null;
    }
  }
  return {
    cliente_id: c.id,
    persona_id: p.id,
    silla,
    desde: desde ?? null,
    hasta: hasta ?? null,
    principal,
    suplencia,
    titular_id: titular,
  };
}

function identificador(v: unknown): v is string {
  return typeof v === 'string' && /^[\w-]{1,100}$/.test(v);
}

function personaVigente(personas: unknown, pid: unknown): Fila | null {
  if (!identificador(pid) || !Array.isArray(personas)) return null;
  const xs = personas.filter((p) => esFila(p) && p.id === pid);
  const p = xs[0];
  if (xs.length !== 1 || !p || (p.estado !== 'activo' && p.estado !== 'dudoso')) return null;
  if (p.estado === 'activo' && p.activo === false) return null;
  return p;
}

function validarPersona(r: unknown, personas: unknown, dudas: unknown): boolean {
  if (!esFila(r) || Object.keys(r).some((k) => !['tipo', 'duda', 'persona_id', 'cambios', 'nota'].includes(k))) return false;
  if (r.tipo !== 'persona' || !identificador(r.duda)) return false;
  const cambios = r.cambios;
  if (!esFila(cambios) || Object.keys(cambios).join('\0') !== 'estado' && !(Object.keys(cambios).length === 1 && 'estado' in cambios)) return false;
  if (cambios.estado !== 'activo' && cambios.estado !== 'dudoso') return false;
  if ('nota' in r && (typeof r.nota !== 'string' || r.nota.length > 2000)) return false;
  if (!personaVigente(personas, r.persona_id)) return false;
  if (dudas !== undefined) {
    if (!Array.isArray(dudas)) return false;
    const ds = dudas.filter((d) => esFila(d) && d.id === r.duda);
    const d = ds[0];
    if (ds.length !== 1 || !d || d.tipo !== 'persona' || d.persona_id !== r.persona_id) return false;
  }
  return true;
}

/** confirmar_personas_572.validar_lista. */
export function validarLista572(resp: unknown, crudo: CrudoAjustes): boolean {
  const lista = Array.isArray(resp) ? resp : [resp];
  if (!lista.length || lista.length > 100 || !esFila(crudo)) return false;
  const dudas = crudo.para_confirmar;
  if (!Array.isArray(dudas)) return false;
  let did: string | null = null;
  for (const r of lista) {
    if (!esFila(r) || (r.tipo !== 'persona' && r.tipo !== 'nota' && r.tipo !== 'asignacion' && r.tipo !== 'servicio') || !identificador(r.duda)) {
      return false;
    }
    if (did === null) did = r.duda;
    if (r.duda !== did) return false;
    const ds = dudas.filter((d) => esFila(d) && d.id === did);
    const d = ds[0];
    if (ds.length !== 1 || !d) return false;
    if (r.tipo === 'persona') {
      if (!validarPersona(r, crudo.personas, dudas)) return false;
    } else if (r.tipo === 'nota') {
      const claves = Object.keys(r);
      if (claves.some((k) => !['tipo', 'duda', 'nota'].includes(k)) || typeof r.nota !== 'string' || !r.nota.trim() || r.nota.length > 2000) {
        return false;
      }
      if (d.tipo === 'persona' && !personaVigente(crudo.personas, d.persona_id)) return false;
    } else if (d.tipo === 'persona' || 'cambios' in r) {
      return false;
    }
  }
  return true;
}

/** confirmar_personas_572.actor_actual. */
export function actorActual572(crudo: CrudoAjustes, real: { id?: unknown; puestos?: unknown }): boolean {
  try {
    const p = personaVigente(crudo.personas, real.id);
    const roles = real.puestos;
    const ids = idsPuesto();
    if (
      !p ||
      p.estado !== 'activo' ||
      !Array.isArray(roles) ||
      !roles.length ||
      new Set(roles).size !== roles.length ||
      !roles.every((x) => typeof x === 'string' && ids.has(x))
    ) {
      return false;
    }
    const delReal = [...roles].sort();
    const deLaPersona = [...(Array.isArray(p.puestos) ? (p.puestos as string[]) : [])].sort();
    if (delReal.join('\0') !== deLaPersona.join('\0')) return false;
    const persona = { ...(p as unknown as Persona), nombre: typeof p.nombre === 'string' ? p.nombre : '', puestos: deLaPersona };
    return ver(persona, { tipo: 'ajustes_editar' }, contexto(persona, crudo)).ok === true;
  } catch {
    return false;
  }
}

/** confirmar_personas_572.permite_estados. */
export function permiteEstados572(crudo: CrudoAjustes, real: { puestos?: unknown }, resp: unknown): boolean {
  const lista = Array.isArray(resp) ? resp : [resp];
  const mando = puestosMando();
  const puestosReal = Array.isArray(real.puestos) ? (real.puestos as string[]) : [];
  try {
    for (const r of lista) {
      if (!esFila(r) || r.tipo !== 'persona') continue;
      const p = personaVigente(crudo.personas, r.persona_id);
      if (!p) return false;
      const cambios = r.cambios;
      if (!esFila(cambios)) return false;
      const puestos = Array.isArray(p.puestos) ? (p.puestos as string[]) : [];
      if (cambios.estado !== p.estado && puestos.some((x) => mando.has(x)) && !puestosReal.includes('direccion')) return false;
    }
    return true;
  } catch {
    return false;
  }
}

/** `b.get("respuesta") or {}` de Python: lista o dict vacíos también caen. */
export function respuestaOVacio(v: unknown): unknown {
  if (v == null || v === false || v === 0 || v === '') return {};
  if (Array.isArray(v) && v.length === 0) return {};
  if (esFila(v) && Object.keys(v).length === 0) return {};
  return v;
}
