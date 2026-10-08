import {
  CLAVES_DINERO_CAPTACION,
  CLAVES_INVERSION,
  DINERO_INVERSION_VALOR,
  conVista,
  importesAQuitar,
  sinImportes,
  ver,
  type Contexto,
  type Persona,
  type QuitaClave,
} from '@ro/permisos';
import type { VistaConContexto } from './motor-ro.js';
import { fuentesSoloContrato, puestosSonSoloContrato } from './puerta-cliente.js';
import { quitarPara, recortarDoc } from '../rastro/rastro-lectura.service.js';

/**
 * servir.py › recortar_ficha (:986-1012) y ficha_sin_importes (:1015-1032).
 * Bloque a bloque, con el mismo orden: primero el recorte, y el filtro de administración dentro.
 */

type Fila = Record<string, unknown>;
const esFila = (x: unknown): x is Fila => !!x && typeof x === 'object' && !Array.isArray(x);

const FUENTES_CON_DINERO = ['meta', 'captacion', 'captacion_ghl', 'google_ads', 'tiktok'] as const;
/** servir.py › CLAVES_LIBRO_CUOTA, sin re.I. */
const CLAVES_LIBRO_CUOTA: QuitaClave = {
  quita(k: string) {
    return /^(meses|ltv.*|vida_meses|cuota.*)$/.test(String(k));
  },
};

const CLAVES_DERIVADAS = /^(pautadas|horas_pautadas|horas_presup.*|pct_sep|pct_oct|pct_horas|pct_cuota.*|segmento|valor_vida.*)$/;
const CLAVES_HORAS = /^(pautadas|horas_pautadas|horas_presup.*|pct_sep|pct_oct|pct_horas)$/;
const CONSUMIDAS = ['sep', 'oct', 'horas_mes', 'horas_mes_ant', 'consumidas'];

function esNum(x: unknown): x is number {
  return typeof x === 'number' && !Number.isNaN(x);
}

/** servir.py › sin_cuota. La misma que recortar-modulo: aquí se copia para no abrir esa función. */
function sinCuota(o: Fila, dejaPautadas: boolean): Fila {
  const pautadas = 'pautadas' in o ? o.pautadas : 'horas_pautadas' in o ? o.horas_pautadas : o.horas_presup_mes;
  if (dejaPautadas) {
    const out: Fila = {};
    for (const [k, v] of Object.entries(o)) {
      if (!CLAVES_DERIVADAS.test(k) || CLAVES_HORAS.test(k)) out[k] = v;
    }
    return out;
  }
  const out: Fila = {};
  for (const [k, v] of Object.entries(o)) {
    if (!CLAVES_DERIVADAS.test(k)) out[k] = v;
  }
  if (esNum(pautadas) && pautadas > 0) {
    const dentro: Fila = {};
    for (const k of CONSUMIDAS) {
      if (esNum(o[k])) dentro[k] = (o[k] as number) <= pautadas;
    }
    out.dentro_de_lo_pautado = dentro;
  }
  return out;
}

/** servir.py › ficha_sin_importes. `fuentes: None` no aplica: el doc ya es objeto o se devuelve tal cual. */
function fichaSinImportes(out: unknown, veCuota: boolean, veInversion: boolean): unknown {
  const quita = importesAQuitar(veCuota, veInversion);
  if (!quita.length || !esFila(out)) return out;
  const deja = new Set<string>();
  if (veCuota) deja.add('libro');
  if (veInversion) for (const f of FUENTES_CON_DINERO) deja.add(f);
  const fuentes = out.fuentes;
  const res: Fila = {};
  for (const [k, x] of Object.entries(out)) {
    res[k] = k === 'fuentes' ? x : sinImportes(x, quita);
  }
  if (esFila(fuentes)) {
    const rec: Fila = {};
    for (const [k, x] of Object.entries(fuentes)) {
      rec[k] = deja.has(k) ? x : sinImportes(x, quita);
    }
    res.fuentes = rec;
  }
  return res;
}

/** servir.py › recortar_ficha. */
export function recortarFicha(persona: Persona, cp: Contexto, cid: string, doc: unknown): unknown {
  const ve = (t: string) => ver(persona, { tipo: t, cliente_id: cid }, cp).ok;
  const out = recortarDoc(doc, quitarPara(persona, cp, cid));
  if (!esFila(out)) return fichaSinImportes(out, ve('cuota'), ve('inversion'));
  const fuentes = esFila(out.fuentes) ? out.fuentes : {};
  // servir.py:995 — administración solo ve las fuentes del contrato. Los puestos se deciden en permisos.
  if (puestosSonSoloContrato(persona.puestos)) {
    const deja = new Set(fuentesSoloContrato());
    const filtradas: Fila = {};
    for (const [k, x] of Object.entries(fuentes)) {
      if (deja.has(k)) filtradas[k] = x;
    }
    out.fuentes = filtradas;
    out.recortada = 'Solo cabecera, cuota, contrato y accesos: lo que hace falta para cobrar.';
    return fichaSinImportes(out, ve('cuota'), ve('inversion'));
  }
  if (!ve('inversion')) {
    for (const fuente of FUENTES_CON_DINERO) {
      if (esFila(fuentes[fuente])) {
        fuentes[fuente] = sinImportes(
          recortarDoc(fuentes[fuente], [CLAVES_DINERO_CAPTACION, DINERO_INVERSION_VALOR, CLAVES_INVERSION]),
        );
      }
    }
  }
  if (!ve('cuota') && esFila(fuentes.libro)) {
    fuentes.libro = recortarDoc(fuentes.libro, [CLAVES_LIBRO_CUOTA]);
  }
  const horas = esFila(fuentes.horas) ? fuentes.horas : null;
  if (!ve('cuota') && horas && esFila(horas.datos)) {
    horas.datos = sinCuota(horas.datos, ve('horas_pautadas'));
  }
  if (!ve('horas_cliente') && esFila(fuentes.horas)) {
    const bloque = fuentes.horas;
    const sinDatos: Fila = {};
    for (const [k, x] of Object.entries(bloque)) {
      if (k !== 'datos') sinDatos[k] = x;
    }
    sinDatos.nota = 'Las horas por cliente las ven quien lo lleva, sus jefas, operaciones y dirección (D-84).';
    fuentes.horas = sinDatos;
  }
  return fichaSinImportes(out, ve('cuota'), ve('inversion'));
}

function personaDe(p: { id: string; nombre?: unknown; puestos?: string[] }): Persona {
  return { ...(p as Persona), nombre: typeof p.nombre === 'string' ? p.nombre : '', puestos: p.puestos ?? [] };
}

/** En «ver como», ver() usa el mínimo de las dos personas, como mirando_como de servir.py. */
export function recortarFichaConVista(vista: VistaConContexto, cid: string, doc: unknown): unknown {
  const persona = personaDe(vista.como ?? vista.real);
  const cp = vista.cp;
  if (!cp) return doc;
  const aplicar = () => recortarFicha(persona, cp, cid, doc);
  const real = personaDe(vista.real);
  return vista.como && vista.cpReal ? conVista({ real, cp: vista.cpReal }, aplicar) : aplicar();
}
