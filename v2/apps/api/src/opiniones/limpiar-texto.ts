import { cortar, longitud } from '@ro/compat';

/** fuentes_chat_equipo/tapado.py + servir.py › limpiar_texto. •••• es U+2022; … es U+2026. */
const TAPADA = '\u2022\u2022\u2022\u2022 (tapada)';
const W = String.raw`\p{L}\p{N}_`;
const ANTES = `(?<![${W}])`;
const DESPUES = `(?![${W}])`;
const NO_TAPADA = `(?!${TAPADA.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`;

const RX_CREDENCIAL = new RegExp(
  `${ANTES}(usuari[oa]s?|user(?:name)?|login|contrase(?:ñ|n)as?|password|passw(?:or)?d|pass|clave|pwd|pin)` +
    String.raw`(\s*\**\s*[:=][\s|*"'` +
    '`]*)' +
    `(?!\\u2026|\\[correo\\]|\\[teléfono\\]|${TAPADA.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})([^\\s|*\`"'<>]+)`,
  'giu',
);

const RX_CLAVE_CERCA = new RegExp(
  `(contrase[ñn]a|password|passw|${ANTES}pass${DESPUES}|${ANTES}clave${DESPUES}|${ANTES}pwd${DESPUES}|${ANTES}pin${DESPUES})`,
  'iu',
);

const RX_TRAS_DOS_PUNTOS = new RegExp(
  `((?:contrase[ñn]a|password|${ANTES}pass${DESPUES}|${ANTES}clave${DESPUES}|${ANTES}pwd${DESPUES}|usuario|${ANTES}user${DESPUES})[^\\n:]{0,80}?:\\s*)${NO_TAPADA}([^\\s,;)\\]]+)`,
  'giu',
);

const RX_PAR = new RegExp(`(?<![/${W}])([^\\s():/@]{2,}):(?!//)([^\\s()]{3,})`, 'gu');

const RX_CLAVE_ES = new RegExp(
  `${ANTES}(contrase(?:ñ|n)as?|password|passw(?:or)?d|clave|pass|pwd|pin|c[oó]digo de acceso)${DESPUES}` +
    `([^\\.\\n]{0,50}?${ANTES}(?:es|era|será|sería|son|queda|nueva)\\s+)${NO_TAPADA}([^\\s,;)]+)`,
  'giu',
);

const RX_CORREO = new RegExp(`[${W}.+-]+@[${W}-]+(?:\\.[${W}-]+)+`, 'gu');
const RX_TEL = new RegExp(
  `(?<![${W}/])(?:\\+34[\\s.-]?|0034[\\s.-]?)?[6789][0-9]{2}[\\s.-]?[0-9]{3}[\\s.-]?[0-9]{3}(?![${W}/])`,
  'gu',
);
const RX_TEL_LARGO = new RegExp(`(?<![${W}/])\\+[0-9][0-9\\s.-]{8,16}[0-9](?![${W}/])`, 'gu');
const RX_SECRETO_URL = /([?&])(pwd|token|key|password|secret|access_token)=[^&\s)\]]+/giu;

function pareceClave(x: string): boolean {
  return /[0-9]|[!@#$%&*_+=?¿¡]/u.test(x) || (longitud(x) >= 8 && x !== x.toLowerCase() && x !== x.toUpperCase());
}

function aplicarClaveEs(t: string): string {
  return t.replace(new RegExp(RX_CLAVE_ES.source, 'giu'), (_todo, g1: string, g2: string, g3: string) =>
    g1 + g2 + (pareceClave(g3) ? TAPADA : g3),
  );
}

/** tapado.tapar. */
function tapar(t: string): string {
  let s = t.replace(new RegExp(RX_CREDENCIAL.source, 'giu'), (_t, g1: string, g2: string) => g1 + g2 + TAPADA);
  if (new RegExp(RX_CLAVE_CERCA.source, 'iu').test(s)) {
    s = s.replace(new RegExp(RX_TRAS_DOS_PUNTOS.source, 'giu'), (_t, g1: string) => g1 + TAPADA);
    s = s.replace(new RegExp(RX_PAR.source, 'gu'), (todo, g1: string) => (/^\p{Nd}+$/u.test(g1) ? todo : TAPADA));
  }
  return aplicarClaveEs(s);
}

/** tapado.limpiar y la segunda pasada de servir.limpiar_texto. */
export function limpiarTexto(t: unknown, largo = 2000): string {
  let s = String(t ?? '')
    .replace(/\r\n/g, '\n')
    .trim();
  s = s.replace(new RegExp(RX_SECRETO_URL.source, 'giu'), '$1$2=\u2026');
  s = tapar(s);
  s = s.replace(new RegExp(RX_CORREO.source, 'gu'), '[correo]');
  s = s.replace(new RegExp(RX_TEL.source, 'gu'), '[teléfono]');
  s = s.replace(new RegExp(RX_TEL_LARGO.source, 'gu'), '[teléfono]');
  s = cortar(s, largo * 2);
  s = aplicarClaveEs(s);
  return cortar(s, largo);
}

/** servir.py › _txt: colapsa espacios, recorta por caracteres. */
export function txt(x: unknown, n = 140): string {
  const s = x == null ? '' : String(x);
  return cortar(s.replace(/\s+/g, ' ').trim(), n);
}
