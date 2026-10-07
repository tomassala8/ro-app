import { SetMetadata } from '@nestjs/common';

/**
 * Cada ruta de Nest DECLARA su permiso con UNA línea encima del método, y nada más:
 *
 *   @Permiso({ modulo: 'crm' })                    // entra quien tenga nivel en ese módulo; la respuesta SIEMPRE sale recortada
 *   @Permiso({ tipo: 'cliente' })
 *   @Permiso({ modulo: 'ver_dato', lecturaPorPost: 'solo lee: igual que servir.py' })   // POST que «ver como» puede usar
 *   @Permiso({ modulo: 'capturas', sinRecorte: 'binario' })                             // respuesta que no es JSON
 *   @Permiso({ soloIdentidad: 'motivo', sinRecorte: 'motivo' })   // toda persona identificada; el recorte va dentro
 *   @Publico('comprobación de vida')               // solo para rutas sin datos (/vivo)
 *
 * Lo seguro va por defecto (auditoría del 4-oct, parte 2): toda respuesta se recorta salvo `sinRecorte`, todo método
 * que no sea GET es escritura y «ver como» no puede escribir salvo `lecturaPorPost`, y toda petición en «ver como»
 * deja rastro (RASTRO_VER_COMO). Una ruta nueva nace segura aunque quien la escriba no se acuerde de nada.
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
  /** Solo con motivo: la respuesta NO pasa por recortar() (p. ej. 'binario'). Por defecto, todo se recorta. */
  sinRecorte?: string;
  /** Solo con motivo: un POST que solo lee y que «ver como» puede usar (hoy: /api/ver_dato y los /api/ia/* de lectura). */
  lecturaPorPost?: string;
  /** Solo con motivo: la ruta la recibe toda persona identificada (y activa); el recorte va dentro (p. ej. /api/sesion). */
  soloIdentidad?: string;
  /** Texto exacto de servir.py cuando la declaración deniega (si no, el motivo de la matriz). */
  mensaje?: string;
}

export const Permiso = (declaracion: DeclaracionPermiso) => SetMetadata(CLAVE_PERMISO, declaracion);
export const Publico = (motivo: string) => SetMetadata(CLAVE_PUBLICO, motivo);

/**
 * Lo que manda en una ruta: lo del método gana a lo de la clase. Un @Publico en la clase no abre un método que
 * declara @Permiso (y al revés). Lo usan la guarda y la prueba de rutas declaradas, para que no se separen nunca.
 */
export function declaracionDe(metodo: object, clase: object): { publico?: string; permiso?: DeclaracionPermiso } {
  const leer = (clave: string, objetivo: object) => Reflect.getMetadata(clave, objetivo) as unknown;
  for (const objetivo of [metodo, clase]) {
    const publico = leer(CLAVE_PUBLICO, objetivo) as string | undefined;
    const permiso = leer(CLAVE_PERMISO, objetivo) as DeclaracionPermiso | undefined;
    if (permiso) return { permiso };
    if (publico) return { publico };
  }
  return {};
}
