/**
 * contratos_privados.py › sanear. Último recorte de la respuesta: las claves y los
 * enlaces de un contrato solo salen si la persona real y la vista son Tomás.
 */
import { existsSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const RAIZ = fileURLToPath(new URL('../../../../../', import.meta.url));
const CLAVES =
  /^(contratos?|contrato_.+|.+_contratos?|agreements?|documentos?_firmados?|signed_documents?|zoho_sign|contratos_sign|contract(s|_.*)?)$/;
const TIPOS = new Set(['contrato', 'contrato_firmado', 'documento_firmado', 'signed_document', 'agreement', 'contract']);
const URL_RE = /https?:\/\/[^\s<>"\]\[)]+/gi;
const HOSTS_SIGN = new Set([
  'sign.zoho.com',
  'sign.zoho.eu',
  'sign.zoho.in',
  'sign.zoho.com.au',
  'sign.zoho.jp',
  'sign.zoho.ca',
  'sign.zoho.com.cn',
]);
const HOSTS_ZOHO = new Set(['zoho.com', 'www.zoho.com', 'zoho.eu', 'www.zoho.eu']);
const HOSTS_DRIVE = new Set(['docs.google.com', 'drive.google.com']);

type Fila = Record<string, unknown>;
const esFila = (x: unknown): x is Fila => !!x && typeof x === 'object' && !Array.isArray(x);

function norm(s: unknown): string {
  const separado = String(s).replace(/([a-z0-9])([A-Z])/g, '$1_$2');
  let ascii = '';
  for (const ch of separado.normalize('NFKD')) {
    if ((ch.codePointAt(0) ?? 0) <= 127) ascii += ch;
  }
  return ascii
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
}

/** contratos_privados.py › permitido. */
export function contratosSoloTomas(real: { id?: string }, vista: { id?: string }): boolean {
  return real.id === 'tomas' && vista.id === 'tomas';
}

function indicePorDefecto(): string {
  return process.env.RO_CONTRATOS_INDICE || join(RAIZ, 'fuentes_contratos', '_privado', 'indice_documentos.json');
}

let cacheIds: { marca: string; ids: ReadonlySet<string> } | undefined;

/** contratos_privados.py › indice_confirmado. Si el índice no está, no hay ids (no se habilita Sign). */
export function idsContratos(ruta = indicePorDefecto()): ReadonlySet<string> {
  let marca = 'ausente';
  try {
    if (existsSync(ruta)) {
      const st = statSync(ruta);
      marca = `${st.mtimeMs}:${st.size}`;
    }
  } catch {
    marca = 'ausente';
  }
  if (cacheIds?.marca === marca) return cacheIds.ids;
  const ids = new Set<string>();
  try {
    const d = JSON.parse(readFileSync(ruta, 'utf8')) as unknown;
    if (esFila(d)) {
      for (const r of (d.documentos as unknown[]) ?? []) {
        if (!esFila(r) || r.confirmado !== true || r.tipo !== 'contrato_firmado' || !r.fuente) continue;
        if (r.proveedor !== 'google_drive' && r.proveedor !== 'zoho_sign') continue;
        if (typeof r.document_id === 'string' && /^[A-Za-z0-9_-]{10,200}$/.test(r.document_id)) ids.add(r.document_id);
      }
    }
  } catch {
    /* índice ausente o roto: igual que Python, conjunto vacío */
  }
  const fijo = new Set(ids);
  cacheIds = { marca, ids: fijo };
  return fijo;
}

function urlContrato(s: string, ids: ReadonlySet<string>): boolean {
  try {
    const u = new URL(s);
    const host = u.hostname.toLowerCase();
    if (HOSTS_SIGN.has(host)) return true;
    if (HOSTS_ZOHO.has(host) && u.pathname.startsWith('/sign')) return true;
    if (HOSTS_DRIVE.has(host)) {
      const m = /\/(?:d|folders)\/([A-Za-z0-9_-]+)/.exec(u.pathname);
      const doc = m?.[1] ?? u.searchParams.get('id');
      return !!doc && ids.has(doc);
    }
    return false;
  } catch {
    return false;
  }
}

function registro(o: Fila): boolean {
  for (const k of ['tipo', 'type', 'categoria', 'clase']) {
    if (TIPOS.has(norm(o[k] ?? ''))) return true;
  }
  for (const k of ['nombre', 'titulo', 'filename', 'document_name']) {
    const n = norm(o[k] ?? '');
    if (n.startsWith('contrato_de_prestacion') || n.startsWith('contrato_firmado') || n.startsWith('acuerdo_de_colaboracion')) return true;
    if (n === 'contrato' || n === 'contrato_pdf') return true;
  }
  return false;
}

/** contratos_privados.py › sanear. */
export function sanearContratos(o: unknown, ids: ReadonlySet<string> = idsContratos()): unknown {
  if (Array.isArray(o)) return o.filter((v) => !(esFila(v) && registro(v))).map((v) => sanearContratos(v, ids));
  if (esFila(o)) {
    if (registro(o)) return null;
    const out: Fila = {};
    for (const [k, v] of Object.entries(o)) {
      if (CLAVES.test(norm(k))) continue;
      out[k] = sanearContratos(v, ids);
    }
    return out;
  }
  if (typeof o === 'string') {
    const t = o.trim();
    if (new RegExp(`^(?:${URL_RE.source})$`, 'i').test(t) && urlContrato(t, ids)) return null;
    return o.replace(new RegExp(URL_RE.source, 'gi'), (m) => (urlContrato(m, ids) ? '[Documento reservado]' : m));
  }
  return o;
}
