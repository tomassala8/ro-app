/** Traducción de clasificacion_importes_580.py. Misma clasificación, sin IO. */

const MARCAS: readonly [string, RegExp][] = [
  ['dinero_empresa', /\b(?:beneficio\s+(?:de\s+la\s+)?empresa|margen\s+(?:de\s+la\s+)?empresa|coste\s+(?:del?\s+)?equipo|agency\s+(?:profit|margin|cost))\b/iu],
  ['cobros', /\b(?:cobros?|cobrad[oa]s?|impagos?|revenue|invoice\s+total)\b/iu],
  ['cuota', /\b(?:cuotas?|fee|honorarios|mantenimiento|factur\w*|recurrente|mensual|al\s+mes)\b|\/\s*mes\b/iu],
  ['inversion', /\b(?:inversi[oó]n|publicidad|gasto|Meta|Ads|CPL|CPM|coste\s+por\s+(?:lead|cita)|presupuesto\s+(?:ads|publicitario))\b/iu],
  ['regla', /\btecho\b/iu],
];

const FAMILIAS = new Set(['cuota', 'inversion', 'cobros', 'dinero_empresa']);
const CORTES_SRC = String.raw`;|\n|·|(?<=[.!?])\s+(?=[A-Za-zÁÉÍÓÚáéíóú])`;

export function clasificarImporte580(texto: unknown, ini: number, fin: number): string {
  if (
    typeof texto !== 'string' ||
    typeof ini !== 'number' ||
    typeof fin !== 'number' ||
    !Number.isInteger(ini) ||
    !Number.isInteger(fin) ||
    !(0 <= ini && ini < fin && fin <= texto.length)
  ) {
    return 'ambiguo';
  }
  const cortes = [...texto.matchAll(new RegExp(CORTES_SRC, 'g'))];
  const previos = cortes.filter((m) => (m.index ?? 0) + m[0].length <= ini).map((m) => (m.index ?? 0) + m[0].length);
  const siguientes = cortes.filter((m) => (m.index ?? 0) >= fin).map((m) => m.index ?? 0);
  const inicio = previos.length ? Math.max(...previos) : 0;
  const final = siguientes.length ? Math.min(...siguientes) : texto.length;
  const trozo = texto.slice(0, final);
  const candidatos: [number, string][] = [];
  for (const [familia, rx] of MARCAS) {
    const flags = rx.flags.includes('g') ? rx.flags : `${rx.flags}g`;
    const re = new RegExp(rx.source, flags);
    re.lastIndex = inicio;
    let m: RegExpExecArray | null;
    while ((m = re.exec(trozo)) !== null) {
      const mFin = m.index + m[0].length;
      const distancia = mFin <= ini ? ini - mFin : m.index >= fin ? m.index - fin : null;
      if (distancia !== null && distancia <= 40) candidatos.push([distancia, familia]);
      if (m[0].length === 0) re.lastIndex = m.index + 1;
    }
  }
  if (!candidatos.length) return 'ambiguo';
  const minimo = Math.min(...candidatos.map((c) => c[0]));
  const familias = new Set(candidatos.filter((c) => c[0] === minimo).map((c) => c[1]));
  if (familias.size !== 1) return 'ambiguo';
  return [...familias][0] ?? 'ambiguo';
}

export function fueraImporte580(tipo: string, quitar: Set<string>): boolean {
  if (tipo === 'ambiguo') {
    for (const f of FAMILIAS) if (quitar.has(f)) return true;
    return false;
  }
  return quitar.has(tipo) || (tipo === 'regla' && quitar.has('inversion'));
}
