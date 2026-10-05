import { clasificarImporte580, fueraImporte580 } from './clasificacion-importes-580.js';
import { py } from './regex-py.js';

const NUM_LETRA =
  String.raw`(?:(?:un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|quince|veinte|veinti[\p{L}\p{N}_]+|treinta|` +
  String.raw`cuarenta|cincuenta|sesenta|setenta|ochenta|noventa|cien|ciento|doscient[oa]s|trescient[oa]s|cuatrocient[oa]s|` +
  String.raw`quinient[oa]s|seiscient[oa]s|setecient[oa]s|ochocient[oa]s|novecient[oa]s|mil|millón|millones|de|y)\s+)*` +
  String.raw`(?:mil|cien|ciento|[\p{L}\p{N}_]+cient[oa]s|millón|millones|veinte|treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa)\s+(?:de\s+)?`;

/** Mismo texto que RE_IMPORTE de permisos.py: (?i:…) envuelve los tres alternativos. */
export const RE_IMPORTE_SRC = py(
  String.raw`(?i:~?\d[\d.,]*(?:\s*[-–]\s*\d[\d.,]*)?\s*(?:k\s*€|€|mil\s+euros?|millones\s+de\s+euros?|euros?\b|eur\b|\$|usd\b)|` +
    String.raw`(?:€|\$|\beur\b)\s*\d[\d.,]*(?:\s*k\b)?|\b` +
    NUM_LETRA +
    String.raw`euros?\b)`,
);

const CONECTOR = py(String.raw`(?:\s*(?:[:=]|\bde\b|\ba\b|\bcon\b|\bpor\b|\ben\b|\bsobre\b))?`);
const COLA = py(String.raw`(?:\s*(?:/\s*(?:mes|día|dia|lead|cita|mes\b)|al mes|cada uno|cada una|por lead|por cita))?`);
const RE_IMPORTE_SIMBOLO = new RegExp(py(String.raw`\d[\d.,]*\s*(?:€|\$)|(?:€|\$)\s*\d[\d.,]*`), 'u');
const CLAVES_TEXTO_LIBRE =
  /^(consultas?|b[uú]squedas?|keywords?|palabras?_?clave|palabras?|t[eé]rminos?(_b[uú]squeda)?|search_?terms?|quer(y|ies)|top_consultas|consultas_.*|busquedas_.*|keywords_.*)$/i;

const QUITAR_TODO = ['cuota', 'inversion', 'cobros', 'dinero_empresa'];
const BORDES = ' ,;:·-\u2013\u2014';

function recortarBordes(s: string, chars: string): string {
  const set = new Set(chars);
  let i = 0;
  let j = s.length;
  while (i < j && set.has(s[i] ?? '')) i += 1;
  while (j > i && set.has(s[j - 1] ?? '')) j -= 1;
  return s.slice(i, j);
}

function reemplazar(texto: string, re: RegExp, fn: (m: RegExpExecArray) => string): string {
  const flags = re.flags.includes('g') ? re.flags : `${re.flags}g`;
  const r = new RegExp(re.source, flags);
  let out = '';
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = r.exec(texto)) !== null) {
    out += texto.slice(last, m.index) + fn(m);
    last = m.index + m[0].length;
    if (m[0].length === 0) r.lastIndex = m.index + 1;
  }
  return out + texto.slice(last);
}

function tipoImporte(texto: string, ini: number, fin: number): string {
  return clasificarImporte580(texto, ini, fin);
}

function fuera(tipo: string, quitar: Set<string>): boolean {
  return fueraImporte580(tipo, quitar);
}

function importesMalos(t: string, quitar: Set<string>): { index: number }[] {
  const re = new RegExp(RE_IMPORTE_SRC, 'gu');
  const malos: { index: number }[] = [];
  let m: RegExpExecArray | null;
  while ((m = re.exec(t)) !== null) {
    if (fuera(tipoImporte(t, m.index, m.index + m[0].length), quitar)) malos.push({ index: m.index });
    if (m[0].length === 0) re.lastIndex = m.index + 1;
  }
  return malos;
}

export function quitarImportesTexto(t: string, quitar: Set<string>): string {
  const malos = importesMalos(t, quitar);
  if (!malos.length) return t;
  let t2 = reemplazar(t, /\s*\([^()]*\)/g, (m) =>
    malos.some((x) => m.index <= x.index && x.index < m.index + m[0].length) ? '' : m[0],
  );
  const trozos = t2.split(/(?<=[.;!?])\s+|\s+·\s+/);
  const con = trozos.map((x) => importesMalos(x, quitar).length > 0);
  if (con.some(Boolean) && !con.every(Boolean)) {
    t2 = trozos.filter((_, i) => !con[i]).join(' ');
  }
  const re3 = new RegExp(`${CONECTOR}\\s*(?<imp>${RE_IMPORTE_SRC})${COLA}`, 'dgu');
  t2 = reemplazar(t2, re3, (m) => {
    const span = m.indices?.groups?.imp;
    if (!span) return m[0];
    return fuera(tipoImporte(m.input, span[0], span[1]), quitar) ? '' : m[0];
  });
  t2 = t2.replace(/\s{2,}/g, ' ');
  t2 = t2.replace(/\s+([,.;:)])/g, '$1');
  t2 = t2.replace(/([(:,])\s*([,.;)])/g, '$2');
  return recortarBordes(t2, BORDES);
}

export function sinImportesLibre(o: unknown, quitar: Set<string> = new Set(QUITAR_TODO)): unknown {
  if (!quitar.size) return o;
  if (Array.isArray(o)) return o.map((x) => sinImportesLibre(x, quitar));
  if (o && typeof o === 'object') {
    return Object.fromEntries(Object.entries(o).map(([k, x]) => [k, sinImportesLibre(x, quitar)]));
  }
  if (typeof o !== 'string' || !RE_IMPORTE_SIMBOLO.test(o)) return o;
  const re = new RegExp(RE_IMPORTE_SIMBOLO.source, 'gu');
  const t = o.replace(re, (coincidencia, offset: number, cadena: string) =>
    fuera(tipoImporte(cadena, offset, offset + coincidencia.length), quitar) ? '' : coincidencia,
  );
  return t.replace(/\s{2,}/g, ' ').trim();
}

export function sinImportes(o: unknown, quitar: Iterable<string> = QUITAR_TODO): unknown {
  const q = quitar instanceof Set ? quitar : new Set(quitar);
  if (!q.size) return o;
  if (Array.isArray(o)) return o.map((x) => sinImportes(x, q));
  if (o && typeof o === 'object') {
    return Object.fromEntries(
      Object.entries(o).map(([k, x]) => [k, CLAVES_TEXTO_LIBRE.test(String(k)) ? sinImportesLibre(x, q) : sinImportes(x, q)]),
    );
  }
  return typeof o === 'string' ? quitarImportesTexto(o, q) : o;
}

export function importesAQuitar(
  veCuota: boolean,
  veInversion: boolean,
  veCobros?: boolean | null,
  veDineroEmpresa?: boolean | null,
): string[] {
  const out: string[] = [];
  if (!veCuota) out.push('cuota');
  if (!veInversion) out.push('inversion');
  if (veCobros === false) out.push('cobros');
  if (veDineroEmpresa === false) out.push('dinero_empresa');
  return out;
}

const ESQUEMAS_OK = /^(https?:\/\/|mailto:|tel:|sip:|#|\/(?!\/)|\.\/|\.\.\/|[\p{L}\p{N}_\-]+\.html)/iu;

export function enlaceSeguro(u: unknown): unknown {
  if (typeof u !== 'string' || !u.trim()) return u;
  const t = u.trim();
  return ESQUEMAS_OK.test(t) ? t : null;
}

export function enmascarar(texto = ''): string {
  const t = texto || '';
  const arroba = t.indexOf('@');
  if (arroba >= 0) return `${t.slice(0, arroba).slice(0, 1)}···@${t.slice(arroba + 1)}`;
  if (t.replace(/\P{Nd}/gu, '').length >= 6) return t.replace(/\p{Nd}(?=(?:\P{Nd}*\p{Nd}){3})/gu, '·');
  return t
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .map((p) => `${p[0] ?? ''}···`)
    .join(' ');
}
