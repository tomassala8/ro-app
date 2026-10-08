import { ahoraBaseUtc, horaMadrid } from '@ro/compat';

/**
 * avisos.ahora_utc_txt: la hora de Madrid (RO_AVISOS_AHORA o RO_RELOJ, si están) pasada a UTC
 * «AAAA-MM-DD HH:MM:SS». Sin reloj, es el UTC de ahora, como ahoraBaseUtc.
 */
export function madridParedAUtc(pared: string): string {
  const t = pared.replace(' ', 'T');
  const texto = t.length === 16 ? `${t}:00` : t.slice(0, 19);
  let utc = new Date(`${texto}Z`);
  for (let i = 0; i < 3; i++) {
    const mad = horaMadrid(utc, '');
    const delta = Date.parse(`${texto}Z`) - Date.parse(`${mad}Z`);
    if (delta === 0) break;
    utc = new Date(utc.getTime() + delta);
  }
  return ahoraBaseUtc(utc);
}

export function ahoraUtcTxt(ahora = new Date()): string {
  const reloj = process.env.RO_AVISOS_AHORA || process.env.RO_RELOJ;
  if (!reloj) return ahoraBaseUtc(ahora);
  return madridParedAUtc(reloj);
}
