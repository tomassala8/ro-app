/** Tipos del motor. Misma forma que los dict de permisos.py (claves en snake_case). */

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
  suplencia?: number | boolean | null;
  titular_id?: string | null;
  desde?: string | null;
  hasta?: string | null;
}

export interface Cliente {
  id: string;
  nombre?: string;
  servicios?: Record<string, string> | null;
  responsable_id?: string | null;
  responsable_texto?: string | null;
  cuota?: unknown;
  cuota_fuente?: unknown;
  publicidad_30d?: unknown;
  [clave: string]: unknown;
}

export interface Dato {
  tipo: string;
  cliente_id?: string;
  persona_id?: string;
  participantes?: string[];
  cliente_nuevo?: unknown;
  [clave: string]: unknown;
}

export interface Respuesta {
  ok: boolean;
  nivel: string;
  motivo?: string;
  desenmascarable?: boolean;
}

export interface Caso {
  identidades?: string[];
  puestos?: string[];
  ambito?: string[];
  cartera?: boolean | string;
  sin_cliente?: boolean;
  propio?: boolean;
  jefe?: boolean;
  participante?: boolean;
  cliente_nuevo?: boolean;
  nivel?: string;
  motivo?: string;
  desenmascarable?: boolean;
}

export interface ReglaTipo {
  nunca?: string;
  no?: string;
  si?: Caso[];
}

export interface Reglas {
  puestos: { id: string; nombre: string; nivel: number; ambito: Ambito; grupo: string }[];
  tipos: Record<string, ReglaTipo>;
  orden_ambitos: string[];
  sillas_de_puesto: Record<string, string[]>;
  sillas_de_equipo?: string[];
  jefe_de_puesto: Record<string, string[]>;
  solo_su_cartera?: { puestos?: string[] };
  modulos_sin_puesto?: Record<string, string[]>;
}

export interface Alarma {
  id?: string;
  cliente_id?: string | null;
  ambito?: string;
  responsable_id?: string | null;
  responsable_texto?: string | null;
  texto?: unknown;
  accion?: unknown;
  enlace?: unknown;
  [clave: string]: unknown;
}

export interface Crudo {
  clientes: Cliente[];
  personas: Persona[];
  asignaciones: Asignacion[];
  logos?: Record<string, string | null>;
  alarmas: Alarma[];
  meta: Record<string, unknown>;
}

export interface Contexto {
  cartera_ids: Set<string>;
  cartera_por_silla: Record<string, Set<string>>;
  personas: Persona[];
  clientes_por_id: Record<string, Cliente>;
}

/** Lo que recibe ver(): a veces llega vacío (sin «ver como» ni cartera). */
export type ContextoParcial = {
  cartera_ids?: Set<string>;
  cartera_por_silla?: Record<string, Set<string>>;
  personas?: Persona[];
  clientes_por_id?: Record<string, Cliente>;
};

export interface Sesion {
  clientes: Record<string, unknown>[];
  alarmas: Record<string, unknown>[];
  carteraIds: string[];
  carteraPorSilla: Record<string, string[]>;
  ambito: string;
  soloSuCartera: boolean;
  personas: Record<string, unknown>[];
  asignaciones: Asignacion[];
  meta: unknown;
}
