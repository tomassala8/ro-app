import { cortar } from '@ro/compat';
import { puedeContestar } from '../permisos/ambito-decision.js';

type Fila = Record<string, unknown>;

export interface PersonaMinima {
  puestos?: string[];
}

function o(a: unknown, b: unknown): unknown {
  if (a === null || a === undefined || a === false || a === '' || a === 0) return b;
  return a;
}

/** json.loads sin try: un JSON roto es un 500, como en Python. */
function cargar(raw: unknown, vacio: Fila): Fila {
  if (raw == null || raw === '' || raw === 'null') return vacio;
  const v = JSON.parse(String(raw)) as unknown;
  if (!v || typeof v !== 'object' || Array.isArray(v)) throw new Error('JSON de decisión que no es un objeto');
  return v as Fila;
}

function num(v: unknown): number | null {
  if (typeof v === 'bigint') return Number(v);
  if (typeof v === 'number') return v;
  if (typeof v === 'string' && /^-?[0-9]+$/.test(v)) return Number(v);
  return null;
}

/**
 * servir.py › decisiones_para, sin el filtro de puestos (eso es filtroDecisiones).
 * Tabla tipo ≠ para_confirmar, más las acciones decision_nueva y decidir.
 */
export function armarDecisiones(
  tabla: Fila[],
  acciones: Fila[],
  personaDe: (id: string) => PersonaMinima | null,
): Fila[] {
  const lista: Fila[] = [];
  for (const d of tabla) {
    const extra = d.datos ? (JSON.parse(String(d.datos)) as unknown) : {};
    if (d.datos && (extra === null || typeof extra !== 'object' || Array.isArray(extra))) {
      throw new Error('datos de decisión que no es un objeto');
    }
    const id = num(d.id);
    const fila: Fila = {
      id: `db-${id}`,
      clave: d.clave ?? null,
      tipo: d.tipo,
      quien: d.quien,
      persona_id: d.quien,
      titulo: o(d.titulo, cortar(o(d.problema, '') as string, 80)),
      problema: d.problema ?? null,
      recomendacion: d.recomendacion ?? null,
      cliente_id: d.cliente_id ?? null,
      creada: d.creada,
      respuesta: d.respuesta ? JSON.parse(String(d.respuesta)) : null,
      respondida: d.respondida ?? null,
      respondida_por: d.respondida_por ?? null,
      origen: 'Subida desde la app (local.db)',
    };
    if (extra && typeof extra === 'object' && !Array.isArray(extra)) Object.assign(fila, extra);
    lista.push(fila);
  }
  for (const a of acciones) {
    if (a.tipo !== 'decision_nueva') continue;
    const vp = cargar(a.vista_previa, {});
    lista.push({
      id: `acc-${num(a.id)}`,
      clave: `acc-${num(a.id)}`,
      tipo: o(vp.tipo, 'para_tomas'),
      quien: a.quien,
      persona_id: a.quien,
      titulo: o(vp.titulo, a.texto ?? null),
      problema: vp.problema ?? null,
      recomendacion: vp.recomendacion ?? null,
      cliente_id: a.cliente_id ?? null,
      creada: a.creada,
      fecha_limite: vp.fecha ?? null,
      respuesta: null,
      respondida: null,
      respondida_por: null,
      origen: 'Botón «Subir una decisión» · simulado',
      simulada: true,
    });
  }
  for (const a of acciones) {
    if (a.tipo !== 'decidir') continue;
    const vp = cargar(a.vista_previa, {});
    const d = lista.find((x) => x.id === vp.decision_id && !x.respondida);
    const quien = personaDe(String(a.quien ?? '')) ?? {};
    if (d && puedeContestar(quien, String(d.tipo ?? ''))) {
      d.respuesta = { decision: vp.decision ?? null, motivo: vp.motivo ?? null, delegada_en: vp.delegada_en ?? null };
      d.respondida = a.creada;
      d.respondida_por = a.quien;
      d.simulada = true;
    }
  }
  return lista;
}
