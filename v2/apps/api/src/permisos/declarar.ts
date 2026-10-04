import { SetMetadata } from '@nestjs/common';

/**
 * Cada ruta de Nest DECLARA su permiso con UNA línea encima del método, y nada más:
 *
 *   @Permiso({ modulo: 'crm', recortar: true })   // entra quien tenga nivel en ese módulo; la respuesta sale recortada
 *   @Permiso({ tipo: 'cliente', escritura: true })
 *   @Publico('comprobación de vida')               // solo para rutas sin datos (/vivo)
 *
 * Una ruta sin ninguna de las dos responde 403 (denegar por defecto) y además rompe la prueba
 * rutas-declaradas.spec.ts. Ningún controlador ni servicio mira puestos ni personas a mano: lo decide
 * el motor (@ro/permisos) a través de la guarda y del recorte de este directorio.
 */
export const CLAVE_PERMISO = 'ro:permiso';
export const CLAVE_PUBLICO = 'ro:publico';

export interface DeclaracionPermiso {
  /** Módulo de modulos/indice.js (nivel_modulo de permisos.py). */
  modulo?: string;
  /** Tipo de dato de reglas_permisos.json (ver() de permisos.py). */
  tipo?: string;
  /** La respuesta pasa por recortar() antes de salir. */
  recortar?: boolean;
  /** Ruta que cambia datos: «ver como» la deniega siempre (es de solo lectura). */
  escritura?: boolean;
}

export const Permiso = (declaracion: DeclaracionPermiso) => SetMetadata(CLAVE_PERMISO, declaracion);
export const Publico = (motivo: string) => SetMetadata(CLAVE_PUBLICO, motivo);
