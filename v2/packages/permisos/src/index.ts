/**
 * @ro/permisos · el motor de permisos de la app, en TypeScript.
 *
 * Es la traducción FIEL de permisos.py (servidor de hoy) y permisos.js (navegador de hoy), que interpretan
 * reglas_permisos.json. La matriz sigue siendo ese JSON: aquí solo vive el intérprete.
 * Lo usan la API (Nest, guardas y recortes) y la web (para pintar el menú), así que hay UN solo motor.
 *
 * Contrato: para cada persona, tipo de dato y objeto, ver() responde lo mismo que permisos.py. Lo comprueba
 * test/paridad.test.ts con los vectores de migracion/vectores_permisos.py (RO_VECTORES=~/RO_MIGRACION/vectores).
 */
export type {
  Alarma,
  Ambito,
  Asignacion,
  Caso,
  Cliente,
  Contexto,
  ContextoParcial,
  Crudo,
  Dato,
  Nivel,
  Persona,
  ReglaTipo,
  Reglas,
  Respuesta,
  Sesion,
} from './tipos.js';

export { cargarReglas, hoyIso, recargarReglas, reglas } from './reglas.js';
export { ambito, cartera, carteraPorSilla } from './cartera.js';
export { clasificarImporte580, fueraImporte580 } from './clasificacion-importes-580.js';
export { enmascarar, enlaceSeguro, importesAQuitar, sinImportes, sinImportesLibre } from './importes.js';
export { cargarModulos, nivelModulo } from './modulos.js';
export { directorio, recortar, soloFilasDe } from './recortar.js';
export { contexto, soloSuCartera, ver } from './ver.js';
export { conVista, mirandoComo, puestosDe, vistaActiva } from './vista.js';
