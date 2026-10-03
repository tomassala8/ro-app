// modulos/_legible.js · barrido total v1 (2-oct): textos que vienen de datos o del rastro, en claro para la persona.
// · conTickets(texto): cada «RO-1234» de Zoho Desk sale como enlace a ese correo en la Bandeja (nunca un número suelto).
// · sinCodigos(texto): quita las referencias internas (reglas R13, E2, D-29, SP04, ficheros .json/.py, «_privado», «p_tomas»)
//   y cambia los números de módulo (M12, N3, C2) por su nombre. «Jessi/Jessica» → «Yessica».
// · claveLegible(clave): «ficha/_privado/contactos#gac» → «Contactos de GAC»; «alertas/p_tomas» → «Alertas de Tomás».

import { h } from '../componentes.js';
import { MODULOS } from './indice.js';

const NOMBRE_MOD = Object.fromEntries(MODULOS.filter(m => m.num).map(m => [m.num, m.titulo]));
const NOMBRE_MOD_ID = Object.fromEntries(MODULOS.map(m => [m.id.replace(/-/g, '_'), m.titulo]));
const RE_TICKET = /\bRO-\d{2,}\b/g;

/** Texto con los tickets de Desk convertidos en enlaces a la Bandeja. Devuelve una lista de nodos/cadenas para h(). */
export function conTickets(texto, { boton = false } = {}) {
  const t = String(texto ?? '');
  const out = [];
  let i = 0;
  for (const m of t.matchAll(RE_TICKET)) {
    if (m.index > i) out.push(t.slice(i, m.index));
    out.push(h('a', { href: `#/bandeja/t-${m[0]}`, title: 'Abre este correo en la Bandeja (y desde allí, en Desk)', style: boton ? { display: 'inline-flex', alignItems: 'center', minHeight: 'var(--s-8)' } : null }, m[0]));
    i = m.index + m[0].length;
  }
  if (i < t.length) out.push(t.slice(i));
  return out;
}

/** Quita códigos internos de un texto que lee cualquiera del equipo. */
export function sinCodigos(texto, { nombres = {} } = {}) {
  if (typeof texto !== 'string' || !texto) return texto;
  return texto
    .replace(/\bJess?i(?:ca)?\b/g, 'Yessica')
    .replace(/\b[\w./-]+\.(?:json|py|sql|db|csv|mjs|md|js|xlsx)\b/g, m => (/capas/.test(m) ? 'la tabla de capas' : 'su fichero de datos'))
    .replace(/\s*\((?:regla\s+)?(?:[A-Z]{1,2}-?[A-Z]?\d+[a-z]?(?:\s*[,·/y]\s*)?)+\)/g, '')
    .replace(/\bRegla:\s*(?:D-(?:P-)?[A-Z]{0,4}-?\d+[A-Z0-9]*|[MNEWR]\d{1,2}[ab]?|SP\d{2})(?:\s+de\s+\w+)?\s*:\s*/g, 'Regla: ')
    .replace(/\b(?:por\s+)?la\s+regla\s+(?:D-(?:P-)?[A-Z]{0,4}-?\d+[A-Z0-9]*|[MNEWR]\d{1,2}[ab]?)\b/g, 'por la regla de la casa')
    .replace(/\b([MNC]\d{1,2})[ab]?\b/g, (m, n) => NOMBRE_MOD[n] ? `«${NOMBRE_MOD[n]}»` : '')
    .replace(/\b(?:D-(?:P-)?[A-Z]{0,4}-?\d+[A-Z0-9]*|[EWR]\d{1,2}[ab]?|SP\d{2})\b\s*[·:]?\s*/g, '')
    .replace(/\b_privado\/?/g, '')
    .replace(/\bp_([a-z0-9_]{2,})\b/g, (m, id) => nombres[id] || 'una persona')
    .replace(/\(\s*\)/g, '')
    .replace(/\s{2,}/g, ' ')
    .replace(/^[\s·:,;]+|[\s·,;]+$/g, '')
    .trim();
}

const COLECCION = { contactos: 'Contactos', chat: 'Chat', sueldos: 'Sueldo', leads: 'Lead', alertas: 'Alertas', notas: 'Notas' };

/** «Sobre qué» del rastro, en claro: sin rutas internas, «_privado» ni ids «p_…». */
export function claveLegible(clave, { nombres = {}, clientes = {} } = {}) {
  const c = String(clave ?? '');
  if (!c) return '';
  if (RE_TICKET.test(c)) { RE_TICKET.lastIndex = 0; return c; }
  RE_TICKET.lastIndex = 0;
  const api = c.match(/^\/api\/modulo\/([\w-]+)\/([\w-]+)/);
  if (api) return `Datos de ${NOMBRE_MOD_ID[api[1]] || api[1].replace(/_/g, ' ')}`;
  const priv = c.match(/^([\w-]+)\/_privado\/([\w-]+)(?:#(.+))?$/);
  if (priv) {
    const que = COLECCION[priv[2]] || priv[2].replace(/_/g, ' ');
    const de = priv[3] ? (clientes[priv[3]] || nombres[priv[3]] || (priv[2] === 'leads' ? 'un lead del CRM' : priv[3].replace(/-/g, ' '))) : '';
    return de ? `${que} de ${de} (reservado)` : `${que} (reservado)`;
  }
  if (nombres[c]) return nombres[c];
  if (clientes[c]) return clientes[c];
  const mod = c.match(/^([\w-]+)\/([\w-]+)$/);
  if (mod && NOMBRE_MOD_ID[mod[1]] && !/^p_/.test(mod[2])) return `Datos de ${NOMBRE_MOD_ID[mod[1]]}`;
  const al = c.match(/^([\w-]+)\/p_([\w-]+)$/);
  if (al) return `${COLECCION[al[1]] || al[1]} de ${nombres[al[2]] || 'una persona'}`;
  return sinCodigos(c, { nombres });
}
