// Las rutas que YA atiende Nest. Todo lo demás pasa tal cual a la app de hoy (servir.py) por el proxy de legado.
// Regla de la noche: una ruta entra en esta lista SOLO cuando su controlador está hecho y `contrato.py comparar`
// da 0 diferencias para ella (y, si es POST, `contrato_escritura.py` también). Así la app está completa a cada momento.
export type Metodo = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export const RUTAS_EN_NEST: ReadonlyArray<readonly [Metodo, RegExp]> = [
  ['GET', /^\/vivo$/],
  ['GET', /^\/api\/sesion$/],
];

export function atiendeNest(metodo: string, ruta: string): boolean {
  return RUTAS_EN_NEST.some(([m, patron]) => m === metodo && patron.test(ruta));
}
