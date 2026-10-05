/** `\b` y `\d` con el sentido Unicode de `re` de Python (necesitan la bandera `u`). */
export const B = String.raw`(?:(?<=[\p{L}\p{N}_])(?![\p{L}\p{N}_])|(?<![\p{L}\p{N}_])(?=[\p{L}\p{N}_]))`;

export const py = (src: string): string =>
  src.replaceAll(String.raw`\b`, B).replaceAll(String.raw`\d`, String.raw`\p{Nd}`);
