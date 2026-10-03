// _telefono.js · regla común de teléfonos de la app de RO (3-oct-2026). Gemelo de telefono.py (misma lógica,
// la de ~/RO_HERRAMIENTAS/zadarma/normalizar_telefonos.py).
//
// Por qué: Zadarma pone el 34 delante si el número no lleva «+». Un «34 6xx…» sin «+» sale como «34 34 6xx…»
// → número inexistente (26 llamadas fallidas en 90 días).
//
// Regla:
//   · Se guarda con prefijo internacional y sin espacios («+34» + 9 cifras, o «+» y el prefijo del país).
//   · 9 cifras que empiezan por 6/7/8/9 → «+34» delante; «34…» (11 cifras) o «0034…» → «+34…»; «3434…» → un solo 34.
//   · Si no cuadra (cifras de más o de menos, texto, número de relleno) no se guarda y se avisa en llano.
//   · La extensión de centralita va en su campo, nunca dentro del número.
//   · Se ENSEÑA con espacios («+34 6XX XX XX XX»); llamar (sip:/tel:) usa el valor sin espacios; WhatsApp, sin «+».
//
// Uso:
//   import { limpiar, validar, formatear, enlaceTel, enlaceSip, enlaceWa, telefono } from './_telefono.js';
//   limpiar(v)  → { telefono: '+34…' | null, extension: '204' | null, motivo: 'ok' | 'vacio' | 'dudoso', aviso }
//   validar(v)  → igual, pero una extensión dentro del número es un error (campos donde se escribe)
//   telefono(v) → { e164, intl, mostrar, tel, sip, wa, extension } | null   (lo que usan los botones)
// Sin dependencias: lo importa también componentes.js.

const MOVIL_O_FIJO_ES = '6789';
const RX_EXT = /[\s,;/]*(?:\b(?:ext|extensi[oó]n|int|interno|centralita)\b\.?\s*[:.#-]?\s*|\bx\s*|#\s*)(\d{1,6})\s*$/i;
const RX_PERMITIDOS = /^[\d\s.\-+()/]+$/;
const cifras = s => String(s || '').replace(/\D/g, '');

/** Contrato de Zadarma: [nuevo, motivo] · [null, ''] sin cambios · [nuevo, 'cambio'] · [null, 'dudoso']. */
export function normalizar(valor) {
  if (valor == null || String(valor).trim() === '') return [null, ''];
  const crudo = String(valor).trim();
  let conMas = crudo.startsWith('+');
  let d = cifras(crudo);
  if (!d) return [null, 'dudoso'];
  if (d.startsWith('00')) { d = d.slice(2); conMas = true; }
  let nuevo;
  if (d.startsWith('3434') && d.length === 13 && MOVIL_O_FIJO_ES.includes(d[4])) nuevo = '+' + d.slice(2);   // 34 repetido
  else if (d.startsWith('34') && d.length === 11 && MOVIL_O_FIJO_ES.includes(d[2])) nuevo = '+' + d;
  else if (d.length === 9 && MOVIL_O_FIJO_ES.includes(d[0])) nuevo = '+34' + d;                              // nacional sin prefijo
  else if (conMas && d.length >= 8 && d.length <= 15 && !d.startsWith('34')) nuevo = '+' + d;               // extranjero bien puesto
  else return [null, 'dudoso'];
  if (nuevo === '+34600000000') return [null, 'dudoso'];
  return nuevo === crudo ? [null, ''] : [nuevo, 'cambio'];
}

/** '93… ext. 204' → ['93…', '204'] · sin extensión → [valor, null]. */
export function separarExtension(valor) {
  const crudo = String(valor || '').trim();
  const m = RX_EXT.exec(crudo);
  if (m && cifras(crudo.slice(0, m.index)).length >= 8) return [crudo.slice(0, m.index).trim(), m[1]];
  return [crudo, null];
}

/** Por qué no cuadra, en llano. */
function avisoDudoso(crudo) {
  if (!RX_PERMITIDOS.test(crudo)) return 'lleva texto además del número';
  let d = cifras(crudo);
  const conMas = crudo.startsWith('+') || d.startsWith('00');
  if (d.startsWith('00')) d = d.slice(2);
  if (!d) return 'no lleva ninguna cifra';
  if (d.endsWith('600000000') && (d.length === 9 || d.length === 11)) return 'es un número de relleno';
  if (d.startsWith('34') || !conMas) {
    const resto = d.startsWith('34') && d.length > 9 ? d.slice(2) : d;
    if (resto.length < 9) return `le faltan cifras (tiene ${d.length})`;
    if (resto.length > 9) return `le sobran cifras (tiene ${d.length})`;
    return 'no empieza por 6, 7, 8 o 9: no parece un teléfono de España; si es de fuera, ponle «+» y el prefijo del país';
  }
  return d.length < 8 ? `le faltan cifras (tiene ${d.length})` : `le sobran cifras (tiene ${d.length})`;
}

/** { telefono, extension, motivo, aviso }. extensionAparte: una extensión al final se separa a su campo. */
export function limpiar(valor, { extensionAparte = true } = {}) {
  if (valor == null || String(valor).trim() === '') return { telefono: null, extension: null, motivo: 'vacio', aviso: '' };
  const crudo = String(valor).trim();
  const [numero, ext] = separarExtension(crudo);
  if (ext && !extensionAparte) return { telefono: null, extension: null, motivo: 'dudoso', aviso: 'lleva una extensión dentro: escribe el número solo y la extensión en su campo' };
  if (!RX_PERMITIDOS.test(numero)) return { telefono: null, extension: null, motivo: 'dudoso', aviso: avisoDudoso(numero) };
  const [nuevo, motivo] = normalizar(numero);
  if (motivo === 'dudoso') return { telefono: null, extension: null, motivo: 'dudoso', aviso: avisoDudoso(numero) };
  return { telefono: nuevo || numero, extension: ext, motivo: 'ok', aviso: ext ? 'extensión separada' : '' };
}

/** Campos de la app donde se escribe un teléfono: la extensión va en su campo. */
export const validar = valor => limpiar(valor, { extensionAparte: false });

/** '+34…' guardable o null. */
export const e164 = valor => limpiar(valor).telefono;

/** Para leer: '+34 6XX XX XX XX' (España) o '+NNNN…' (fuera, sin trocear). Lo que no cuadra se devuelve tal cual. */
export function formatear(valor) {
  const t = e164(valor);
  if (!t) return String(valor || '');
  const d = t.slice(1);
  if (d.startsWith('34') && d.length === 11) return `+34 ${d.slice(2, 5)} ${d.slice(5, 7)} ${d.slice(7, 9)} ${d.slice(9)}`;
  return '+' + d;          // fuera de España, sin trocear: el prefijo del país puede ser de 1, 2 o 3 cifras
}

export const enlaceTel = valor => { const t = e164(valor); return t ? `tel:${t}` : null; };
/** App de Zadarma: siempre con «+» (sin él, Zadarma antepone el 34 y marca «34 34 …»). */
export const enlaceSip = valor => { const t = e164(valor); return t ? `sip:${t}@sip.zadarma.com` : null; };
/** WhatsApp pide el número internacional sin «+» ni espacios (wa.me/34…). */
export const enlaceWa = valor => { const t = e164(valor); return t ? `https://wa.me/${t.slice(1)}` : null; };

/** Todo lo que necesita un botón, o null si no cuadra. intl = cifras sin «+» (compatibilidad). */
export function telefono(valor) {
  const r = limpiar(valor);
  if (!r.telefono) return null;
  const t = r.telefono;
  return { e164: t, intl: t.slice(1), mostrar: formatear(t), tel: `tel:${t}`, sip: `sip:${t}@sip.zadarma.com`, wa: `https://wa.me/${t.slice(1)}`, extension: r.extension };
}
