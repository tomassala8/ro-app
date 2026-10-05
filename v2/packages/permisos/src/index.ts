/**
 * @ro/permisos · el motor de permisos de la app, en TypeScript.
 *
 * Es la traducción FIEL de permisos.py (servidor de hoy) y permisos.js (navegador de hoy), que interpretan
 * reglas_permisos.json. La matriz sigue siendo ese JSON: aquí solo vive el intérprete.
 * Lo usan la API (Nest, guardas y recortes) y la web (para pintar el menú), así que hay UN solo motor.
 *
 * Contrato: para cada persona, tipo de dato y objeto, ver() responde lo mismo que permisos.py. Lo comprueba
 * test/paridad.test.ts con los vectores de migracion/vectores_permisos.py (RO_VECTORES=~/RO_MIGRACION/vectores).
 *
 * Fase 2 del plan (migracion/PLAN_MAESTRO.md): portar aquí, función a función y con el mismo nombre,
 * cartera_por_silla, cartera, ambito, ver (con «ver como» = mínimo de las dos personas), contexto, recortar,
 * nivel_modulo, sin_importes, importes_a_quitar, enlace_seguro.
 */
import { readFileSync } from 'node:fs';

export type Nivel = 'todo' | 'suyo' | 'resumen';
export type Ambito = 'todos' | 'disciplina' | 'cartera' | 'tareas' | 'ninguno';

export interface Persona {
  id: string;
  nombre: string;
  alias?: string | null;
  puestos: string[];
  estado?: 'activo' | 'dudoso' | 'por_incorporar' | 'baja';
  jefe?: string | null;
  [clave: string]: unknown;
}

export interface Asignacion {
  cliente_id: string;
  persona_id: string;
  silla: string;
  principal?: number;
  suplencia?: number;
  titular_id?: string | null;
  desde?: string | null;
  hasta?: string | null;
}

export interface Dato {
  tipo: string;
  cliente_id?: string;
  persona_id?: string;
  [clave: string]: unknown;
}

export interface Respuesta {
  ok: boolean;
  nivel: string;
  motivo?: string;
  desenmascarable?: boolean;
}

export type Reglas = Record<string, unknown> & {
  puestos: { id: string; nombre: string; nivel: number; ambito: Ambito; grupo: string }[];
  tipos: Record<string, unknown>;
};

/** Lee reglas_permisos.json (por defecto, el de la raíz del repositorio). */
export function cargarReglas(ruta = new URL('../../../../reglas_permisos.json', import.meta.url)): Reglas {
  return JSON.parse(readFileSync(ruta, 'utf8')) as Reglas;
}
