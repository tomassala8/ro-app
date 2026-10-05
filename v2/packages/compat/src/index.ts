/**
 * @ro/compat · lo que Python hace distinto de JavaScript, escrito UNA vez y probado contra Python de verdad.
 *
 * Al pasar servir.py, permisos.py y avisos.py a Nest, estas diferencias no dan error: dan un número, un texto o una
 * huella distintos, y la puerta del contrato (o la cadena del rastro) los cazan de madrugada. Úsalo siempre que el
 * código de Python haga alguna de estas cosas (lista completa en migracion/PROMPTS_CURSOR.md › «Guía de traducción»):
 *
 *   round(x, n)                  → redondear(x, n)        (Python redondea al par: round(2.5) = 2, round(0.125, 2) = 0.12)
 *   json.dumps(v, …)             → jsonComoPython(v, …)   (espacios tras «,» y «:», ensure_ascii, sort_keys, 1.0)
 *   _huella(previa, campos)      → huellaRastro(previa, campos)   (la cadena del rastro: tiene que salir IDÉNTICA)
 *   texto[:n], len(texto)        → cortar(texto, n), longitud(texto)   (Python cuenta caracteres; JS, unidades UTF-16)
 *   a // b, a % b                → divEntera(a, b), modulo(a, b)       (Python redondea hacia abajo; JS, hacia cero)
 *   f"{x:.2f}", f"{x:,.0f}"      → formatoFijo(x, 2), formatoFijo(x, 0, true)   (toFixed redondea distinto)
 *   sorted(textos)               → ordenarComoPython(textos, clave?)  (por punto de código; nunca localeCompare)
 *   ahora_madrid(), hoy()        → horaMadrid(), hoyMadrid()           (Europe/Madrid y RO_RELOJ, como permisos.py)
 *   datetime('now') de la base   → ahoraBaseUtc()                     («AAAA-MM-DD HH:MM:SS» en UTC)
 */
import { createHash } from 'node:crypto';

/** Un número que en Python es float aunque no tenga decimales (12.0). JSON de JS no sabe distinguirlo. */
export class Flotante {
  constructor(readonly valor: number) {}
}
export const flotante = (x: number) => new Flotante(x);

/** repr() de un float de Python: el mismo número de cifras que JS, pero «1.0», «1e+16», «1e-05». */
export function reprFloat(x: number): string {
  if (Number.isNaN(x)) return 'NaN';
  if (!Number.isFinite(x)) return x > 0 ? 'Infinity' : '-Infinity';
  if (x === 0) return Object.is(x, -0) ? '-0.0' : '0.0';
  const [mant, expTxt] = Math.abs(x).toExponential().split('e');
  const exp = Number(expTxt);
  const cifras = mant.replace('.', '');
  const signo = x < 0 ? '-' : '';
  if (exp < -4 || exp >= 16) {
    const m = cifras.length > 1 ? `${cifras[0]}.${cifras.slice(1)}` : cifras;
    return `${signo}${m}e${exp < 0 ? '-' : '+'}${String(Math.abs(exp)).padStart(2, '0')}`;
  }
  if (exp < 0) return `${signo}0.${'0'.repeat(-exp - 1)}${cifras}`;
  const entera = cifras.slice(0, exp + 1).padEnd(exp + 1, '0');
  const decimales = cifras.slice(exp + 1);
  return `${signo}${entera}.${decimales || '0'}`;
}

/** round(x, n) de Python: al par en el empate EXACTO del valor binario (round(2.675, 2) = 2.67, round(0.125, 2) = 0.12). */
export function redondear(x: number, n = 0): number {
  if (!Number.isFinite(x) || !Number.isInteger(n) || n < 0 || n > 12) {
    if (Number.isFinite(x) && n >= 0) return x;
    throw new Error(`redondear: n entre 0 y 12 (recibido ${n})`);
  }
  const exacto = Math.abs(x).toFixed(100);   // expansión decimal exacta del double (sobra para n ≤ 12)
  const [ent, frac] = exacto.split('.');
  const guardo = ent + frac.slice(0, n);
  const resto = frac.slice(n);
  let subir = false;
  if (resto[0] > '5') subir = true;
  else if (resto[0] === '5') subir = /[1-9]/.test(resto.slice(1)) || Number(guardo[guardo.length - 1]) % 2 === 1;
  const txt = (BigInt(guardo) + (subir ? 1n : 0n)).toString().padStart(n + 1, '0');
  const valor = Number(n ? `${txt.slice(0, -n)}.${txt.slice(-n)}` : txt);
  return x < 0 ? -valor : valor;   // -0.0 como Python (round(-0.0001) = -0.0)
}

/** f"{x:.{n}f}" de Python (y con miles=true, f"{x:,.{n}f}"): mismo redondeo al par que format(). */
export function formatoFijo(x: number, n: number, miles = false): string {
  const txt = Math.abs(redondear(x, n)).toFixed(n);
  const [ent, dec] = txt.split('.');
  const conMiles = miles ? ent.replace(/\B(?=(\d{3})+(?!\d))/g, ',') : ent;
  const signo = x < 0 || Object.is(x, -0) ? '-' : '';
  return `${signo}${conMiles}${dec !== undefined ? `.${dec}` : ''}`;
}

function escaparTexto(s: string, ascii: boolean): string {
  let out = '"';
  for (const ch of s) {
    const c = ch.codePointAt(0)!;
    if (ch === '"') out += '\\"';
    else if (ch === '\\') out += '\\\\';
    else if (ch === '\n') out += '\\n';
    else if (ch === '\r') out += '\\r';
    else if (ch === '\t') out += '\\t';
    else if (ch === '\b') out += '\\b';
    else if (ch === '\f') out += '\\f';
    else if (c < 0x20 || (ascii && c > 0x7e)) {
      if (c > 0xffff) {
        const v = c - 0x10000;
        out += `\\u${(0xd800 + (v >> 10)).toString(16).padStart(4, '0')}\\u${(0xdc00 + (v & 0x3ff)).toString(16).padStart(4, '0')}`;
      } else out += `\\u${c.toString(16).padStart(4, '0')}`;
    } else out += ch;
  }
  return out + '"';
}

/** Comparación de textos como Python (por punto de código). */
export function compararComoPython(a: string, b: string): number {
  const x = Array.from(a, (c) => c.codePointAt(0)!);
  const y = Array.from(b, (c) => c.codePointAt(0)!);
  for (let i = 0; i < Math.min(x.length, y.length); i++) if (x[i] !== y[i]) return x[i] - y[i];
  return x.length - y.length;
}

export interface OpcionesJson {
  /** ensure_ascii de Python. Por defecto true, como json.dumps. */
  ensureAscii?: boolean;
  sortKeys?: boolean;
  /** separators de Python. Por defecto (', ', ': '). */
  separadores?: [string, string];
}

/** json.dumps(v, ensure_ascii=…, sort_keys=…, separators=…) byte a byte. Los enteros salen como int; usa flotante() para 12.0. */
export function jsonComoPython(v: unknown, o: OpcionesJson = {}): string {
  const ascii = o.ensureAscii ?? true;
  const [coma, dosPuntos] = o.separadores ?? [', ', ': '];
  const ir = (x: unknown): string => {
    if (x === null || x === undefined) return 'null';
    if (x instanceof Flotante) return reprFloat(x.valor);
    if (typeof x === 'boolean') return x ? 'true' : 'false';
    if (typeof x === 'number') return Number.isInteger(x) && Math.abs(x) < 1e21 ? String(x) : reprFloat(x);
    if (typeof x === 'bigint') return x.toString();
    if (typeof x === 'string') return escaparTexto(x, ascii);
    if (Array.isArray(x)) return `[${x.map(ir).join(coma)}]`;
    if (typeof x === 'object') {
      let claves = Object.keys(x as object);
      if (o.sortKeys) claves = claves.sort(compararComoPython);
      return `{${claves.map((k) => `${escaparTexto(k, ascii)}${dosPuntos}${ir((x as Record<string, unknown>)[k])}`).join(coma)}}`;
    }
    throw new Error(`jsonComoPython: tipo no admitido (${typeof x})`);
  };
  return ir(v);
}

/** servir.py › _huella: sha256(previa + json.dumps(campos, ensure_ascii=False, sort_keys=True)). */
export function huellaRastro(previa: string | null | undefined, campos: unknown[]): string {
  return createHash('sha256')
    .update((previa ?? '') + jsonComoPython(campos, { ensureAscii: false, sortKeys: true }), 'utf8')
    .digest('hex');
}

/** texto[:n] de Python (por caracteres, no parte un emoji). Admite n negativo como Python. */
export function cortar(s: string, n: number): string {
  return Array.from(s).slice(0, n).join('');
}
export const longitud = (s: string) => Array.from(s).length;

/** a // b y a % b de Python (hacia abajo; el resto lleva el signo del divisor). */
export const divEntera = (a: number, b: number) => Math.floor(a / b);
export const modulo = (a: number, b: number) => ((a % b) + b) % b;

/** sorted(lista, key=…) de Python: estable y por punto de código en textos. Las claves pueden ser tuplas (arrays). */
export function ordenarComoPython<T>(lista: readonly T[], clave: (x: T) => unknown = (x) => x, inverso = false): T[] {
  const cmp = (a: unknown, b: unknown): number => {
    if (Array.isArray(a) && Array.isArray(b)) {
      for (let i = 0; i < Math.min(a.length, b.length); i++) {
        const c = cmp(a[i], b[i]);
        if (c) return c;
      }
      return a.length - b.length;
    }
    if (typeof a === 'string' && typeof b === 'string') return compararComoPython(a, b);
    if (typeof a === 'number' && typeof b === 'number') return a - b;
    if (typeof a === 'boolean' && typeof b === 'boolean') return Number(a) - Number(b);
    // Python da TypeError al comparar None o tipos distintos: aquí también, para que no pase en silencio.
    throw new TypeError(`ordenarComoPython: no se pueden comparar ${typeof a} y ${typeof b}`);
  };
  const conClave = lista.map((x, i) => ({ x, k: clave(x), i }));
  conClave.sort((a, b) => (inverso ? cmp(b.k, a.k) : cmp(a.k, b.k)) || a.i - b.i);
  return conClave.map((e) => e.x);
}

const dos = (n: number) => String(n).padStart(2, '0');
function partes(d: Date, zona: string) {
  const p = Object.fromEntries(
    new Intl.DateTimeFormat('en-GB', { timeZone: zona, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' })
      .formatToParts(d)
      .map((x) => [x.type, x.value]),
  );
  return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}:${p.second}`;
}

/** permisos.py › ahora_madrid(): hora de Madrid sin zona («AAAA-MM-DDTHH:MM:SS»). RO_RELOJ la fija (toda la noche). */
export function horaMadrid(ahora: Date = new Date(), reloj = process.env.RO_RELOJ): string {
  if (reloj) {
    const t = reloj.replace(' ', 'T');
    return t.length === 16 ? `${t}:00` : t.slice(0, 19);
  }
  return partes(ahora, 'Europe/Madrid');
}
export const hoyMadrid = (ahora?: Date, reloj?: string) => horaMadrid(ahora, reloj).slice(0, 10);

/** datetime('now') de la base: «AAAA-MM-DD HH:MM:SS» en UTC (no lo fija RO_RELOJ, igual que en SQLite). */
export function ahoraBaseUtc(ahora: Date = new Date()): string {
  return `${ahora.getUTCFullYear()}-${dos(ahora.getUTCMonth() + 1)}-${dos(ahora.getUTCDate())} ${dos(ahora.getUTCHours())}:${dos(ahora.getUTCMinutes())}:${dos(ahora.getUTCSeconds())}`;
}
