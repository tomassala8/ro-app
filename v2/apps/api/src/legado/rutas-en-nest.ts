// Las rutas que YA atiende Nest. Todo lo demás pasa tal cual a la app de hoy (servir.py) por el proxy de legado.
// Regla de la noche: una ruta entra en esta lista SOLO cuando su controlador está hecho y `contrato.py comparar`
// da 0 diferencias para ella (y, si es POST, `contrato_escritura.py` también). Así la app está completa a cada momento.
export type Metodo = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

/** F5.3 tanda 1: ficheros de datos_de_modulo sin claves extra (el resto sigue por el proxy). */
export const MODULOS_EN_NEST: readonly string[] = [
  'ajustes/conexiones',
  'captacion/captacion',
  'decisiones/reloj',
  'en_rojo/atajos',
  'ficha/basica',
  'ficha/portal',
  'finanzas/cuadre_facturacion',
  'finanzas/impagos',
  'finanzas/impagos_clientes',
  'horas/horas',
  'informe/comun',
  'informe/p_2026-06',
  'informe/p_2026-07',
  'informe/p_2026-08',
  'informe/p_2026-09',
  'informe/p_trim',
  'informe/p_u30',
  'informe/paridad',
  'informes/informes',
  'paneles/indice',
  'personas_m20/equipo',
  'produccion/marca',
  'redes/redes',
  'seo/seo',
  'seo/webs',
  'ventas_ro/meta',
  'verdad/equipo',
  'whatsapp/whatsapp',
];

const MODULOS_RE = MODULOS_EN_NEST.length
  ? new RegExp(`^/api/modulo/(${MODULOS_EN_NEST.map((r) => r.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})$`)
  : /^(?!)$/;

export const RUTAS_EN_NEST: ReadonlyArray<readonly [Metodo, RegExp]> = [
  ['GET', /^\/vivo$/],
  ['GET', /^\/api\/sesion$/],
  ['GET', /^\/api\/rastro\/verificar$/],
  ['POST', /^\/api\/rastro$/],
  ['GET', /^\/api\/rastro$/],
  ['GET', MODULOS_RE],
];

export function atiendeNest(metodo: string, ruta: string): boolean {
  return RUTAS_EN_NEST.some(([m, patron]) => m === metodo && patron.test(ruta));
}
