import {
  CLAVES_CUOTA,
  CLAVES_INVERSION,
  conVista,
  enlaceSeguro,
  importesAQuitar,
  puestosDe,
  sinImportes,
  sinImportesLibre,
  soloSuCartera,
  ver,
  vistaActiva,
  type Contexto,
  type Persona,
  type QuitaClave,
} from '@ro/permisos';
import { quitarPara } from '../rastro/rastro-lectura.service.js';
import type { VistaConContexto } from './motor-ro.js';

/**
 * servir.py › recortar_modulo (:1043) y lo que llama (sin_cuota, clientes_ajenos, recorte_vacio,
 * recorte_por_silla, _rama_sin_importes). El mismo orden, bloque a bloque.
 */

type Fila = Record<string, unknown>;
const esFila = (x: unknown): x is Fila => !!x && typeof x === 'object' && !Array.isArray(x);

const CLAVES_DERIVADAS = /^(pautadas|horas_pautadas|horas_presup.*|pct_sep|pct_oct|pct_horas|pct_cuota.*|segmento|valor_vida.*)$/;
const CLAVES_HORAS = /^(pautadas|horas_pautadas|horas_presup.*|pct_sep|pct_oct|pct_horas)$/;
const CONSUMIDAS = ['sep', 'oct', 'horas_mes', 'horas_mes_ant', 'consumidas'];
const CLAVES_RENTABILIDAD = /(?:^|[_\-.])(?:tarifa_hora|vida_meses|en_facturacion|margen[\p{L}\p{N}_]*|rentabilidad[\p{L}\p{N}_]*|coste_eur|agency_(?:profit|margin|cost))(?:$|[_\-.])/iu;
const CLAVES_ENLACE = /^(url|enlace.*|href|web|prueba|link.*|enlaces)$/i;
const CLAVES_TEXTO_LIBRE = /^(consultas?|b[uú]squedas?|keywords?|palabras?_?clave|palabras?|t[eé]rminos?(_b[uú]squeda)?|search_?terms?|quer(y|ies)|top_consultas|consultas_.*|busquedas_.*|keywords_.*)$/i;
const LEAD_NOMBRES = new Set(['nombre', 'name', 'email', 'correo', 'phone']);
const CLAVES_FILA_LEAD = new Set([
  'nombre_lead', 'lead_name', 'telefono', 'tel', 'tel_m', 'nombre_m', 'correo_lead', 'email_lead', 'lead_email',
  'lead_phone', 'enlace_contacto', 'contacto_id', 'lead_id',
]);
const SERIES = new Set(['serie', 'serie_ant', 'serie_anio']);
const META_SI = new Set(['campanas', 'conjuntos', 'gasto', 'cpl', 'actual', 'presupuesto']);
const META_NO = new Set(['clics', 'impresiones_web', 'usuarios']);
const LISTAS_META = new Set(['meta', 'datos', 'meta_ads']);

function textoLista(lista: string | null): string {
  return lista == null ? 'none' : lista.toLowerCase();
}

function esNum(x: unknown): x is number {
  return typeof x === 'number' && !Number.isNaN(x);
}

/** servir.py › sin_cuota. */
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

/** servir.py › _serie_de_meta. */
function serieDeMeta(bloque: Fila): boolean {
  const normal = new Map(Object.entries(bloque).map(([k, v]) => [k.toLowerCase(), v]));
  const ser = normal.get('serie');
  if (Array.isArray(ser) && ser.length && esFila(ser[0])) {
    if (Object.keys(ser[0]).some((k) => k.toLowerCase() === 'meta')) return true;
  }
  const keys = new Set(normal.keys());
  return [...META_SI].some((k) => keys.has(k)) && ![...META_NO].some((k) => keys.has(k));
}

/** servir.py › serie_sin_gasto. */
function serieSinGasto(serie: unknown): unknown {
  if (!Array.isArray(serie)) return serie;
  return serie.map((x) => {
    if (Array.isArray(x) && x.length >= 3 && typeof x[0] === 'string') return [x[0], null, ...x.slice(2)];
    if (esFila(x)) {
      const y: Fila = {};
      for (const [k, w] of Object.entries(x)) {
        if (!CLAVES_INVERSION.quita(k, w)) y[k] = w;
      }
      const metaKey = Object.keys(y).find((k) => k.toLowerCase() === 'meta');
      if (metaKey && Array.isArray(y[metaKey]) && (y[metaKey] as unknown[]).length) {
        const lista = y[metaKey] as unknown[];
        y[metaKey] = [null, ...lista.slice(1)];
      }
      return y;
    }
    return x;
  });
}

/** servir.py › clientes_ajenos. */
function clientesAjenos(cp: Contexto, clientes: { id: string; nombre?: string | null }[]): Set<string> {
  const mios = cp.cartera_ids ?? new Set<string>();
  const out = new Set<string>();
  for (const c of clientes) {
    if (mios.has(c.id)) continue;
    out.add(c.id.toLowerCase());
    if ((c.nombre ?? '').trim()) out.add((c.nombre ?? '').trim().toLowerCase());
  }
  return out;
}

/** servir.py › cliente_de_fila. */
function clienteDeFila(x: Fila, ajeno: Set<string>): boolean {
  for (const k of ['cid', 'cliente', 'cliente_slug']) {
    const v = x[k];
    if (typeof v === 'string' && ajeno.has(v.trim().toLowerCase())) return true;
  }
  const id = x.id;
  return typeof id === 'string' && ajeno.has(id.toLowerCase()) && typeof x.nombre === 'string' && ajeno.has(x.nombre.trim().toLowerCase());
}

/** servir.py › recorte_vacio. */
function recorteVacio(obj: unknown, conf: Fila): unknown {
  const vacio = esFila(conf.vacio_para_puestos) ? conf.vacio_para_puestos : {};
  const deja = new Set<string>(Array.isArray(vacio.deja) ? vacio.deja.filter((x): x is string => typeof x === 'string') : []);
  if (!esFila(obj)) return [];
  const out: Fila = {};
  for (const [k, v] of Object.entries(obj)) {
    if (deja.has(k) || Array.isArray(v)) out[k] = Array.isArray(v) ? [] : v;
  }
  return out;
}

/** Nombre exacto. El cruce difuso de campana_cliente solo lo usa ventas_ro/outreach, que esta noche no entra. */
function clientePorNombre(nombre: unknown, clientes: { id: string; nombre?: string | null }[]): string | null {
  const buscado = String(nombre ?? '').trim().toLowerCase();
  for (const c of clientes) {
    const nom = (c.nombre || c.id).trim().toLowerCase();
    if (nom === buscado) return c.id;
  }
  return null;
}

/** servir.py › recorte_por_silla. */
function recortePorSilla(persona: Persona, cp: Contexto, out: unknown, regla: unknown, clientes: { id: string; nombre?: string | null }[]): unknown {
  if (!esFila(regla) || !esFila(out)) return out;
  const propios = new Set(persona.puestos ?? []);
  const puestos = new Set(Array.isArray(regla.puestos) ? regla.puestos.filter((x): x is string => typeof x === 'string') : []);
  const salvo = new Set(Array.isArray(regla.salvo_puestos) ? regla.salvo_puestos.filter((x): x is string => typeof x === 'string') : []);
  if (![...propios].some((p) => puestos.has(p)) || [...propios].some((p) => salvo.has(p))) return out;
  const silla = typeof regla.silla === 'string' ? regla.silla : '';
  const suyos = cp.cartera_por_silla?.[silla] ?? new Set<string>();
  const copia: Fila = { ...out };
  for (const ruta of (regla.listas as unknown[]) ?? []) {
    if (typeof ruta !== 'string') continue;
    const partes = ruta.split('.');
    let padre: Fila | null = copia;
    for (const k of partes.slice(0, -1)) {
      if (!padre || !esFila(padre[k])) {
        padre = null;
        break;
      }
      padre[k] = { ...(padre[k] as Fila) };
      padre = padre[k] as Fila;
    }
    const ultima = partes.at(-1);
    if (padre && ultima && Array.isArray(padre[ultima])) {
      padre[ultima] = (padre[ultima] as unknown[]).filter((x) => esFila(x) && suyos.has(String(x.cliente_id)));
    }
  }
  for (const clave of (regla.claves_por_nombre as unknown[]) ?? []) {
    if (typeof clave === 'string' && esFila(copia[clave])) {
      const bloque = copia[clave] as Fila;
      const quedo: Fila = {};
      for (const [k, v] of Object.entries(bloque)) {
        const cid = clientePorNombre(k, clientes);
        if (cid && suyos.has(cid)) quedo[k] = v;
      }
      copia[clave] = quedo;
    }
  }
  return copia;
}

/** servir.py › _rama_sin_importes. */
function ramaSinImportes(o: unknown, ruta: string[]): unknown {
  if (!ruta.length) return sinImportes(o);
  if (esFila(o) && ruta[0] && ruta[0] in o) {
    return { ...o, [ruta[0]]: ramaSinImportes(o[ruta[0]], ruta.slice(1)) };
  }
  return o;
}

function claveSetterDe(persona: Persona): string | null {
  const directa = persona.clave_setter;
  if (typeof directa === 'string' && directa) return directa;
  return persona.id.startsWith('setter_') ? persona.id.slice('setter_'.length) : null;
}

function cidTexto(cid: unknown): string | undefined {
  return typeof cid === 'string' && cid ? cid : undefined;
}

/**
 * servir.py › recortar_modulo.
 * `clientes` es el crudo ya limpio de bajas (E.crudo["clientes"]).
 */
export function recortarModulo(
  persona: Persona,
  cp: Contexto,
  obj: unknown,
  nivel: string | null | undefined,
  soloTodo: readonly string[],
  filasLead: readonly unknown[],
  conf: Fila,
  clientes: { id: string; nombre?: string | null }[],
): unknown {
  // servir.py:1050
  if (nivel === 'vacio') return recorteVacio(obj, conf);
  // servir.py:1052
  const puestos = puestosDe(persona);
  const veTodosSetters = ['direccion', 'ventas_ro', 'jefa_crm', 'operaciones'].some((p) => puestos.has(p));
  const miSetter = claveSetterDe(persona);
  const cartera = cp.cartera_ids ?? new Set<string>();
  // servir.py:1058 — en «ver como», la persona real (vistaActiva); si no, no hay segunda persona.
  const realId = vistaActiva()?.real.id;
  const veRentabilidad = ver(persona, { tipo: 'rentabilidad_cliente' }, cp).ok;
  const filasTipo = new Map<string, Fila>();
  for (const f of (conf.filas_solo_tipo as unknown[]) ?? []) {
    if (esFila(f) && typeof f.lista === 'string') filasTipo.set(f.lista, f);
  }
  // servir.py:1065
  const ajeno = soloSuCartera(persona) ? clientesAjenos(cp, clientes) : null;
  const leadNorm = new Set(filasLead.map((x) => String(x).toLowerCase()));

  const cache = new Map<unknown, QuitaClave[]>();
  const cacheP = new Map<unknown, boolean>();

  const vePautadas = (cid: unknown): boolean => {
    if (!cacheP.has(cid)) cacheP.set(cid, !!cid && ver(persona, { tipo: 'horas_pautadas', cliente_id: cidTexto(cid) }, cp).ok);
    return cacheP.get(cid) ?? false;
  };
  const dejaHoras = (k: string, cid: unknown): boolean => (k === 'cuota_horas' || k === 'coste_horas') && vePautadas(cid);
  const quitar = (cid: unknown): QuitaClave[] => {
    if (!cache.has(cid)) cache.set(cid, quitarPara(persona, cp, cidTexto(cid)));
    return cache.get(cid) ?? [];
  };

  // servir.py:1067
  const filaOk = (x: unknown): boolean => {
    if (!esFila(x)) return true;
    if (x.cliente_id && !ver(persona, { tipo: 'cliente_detalle', cliente_id: cidTexto(x.cliente_id) }, cp).ok) return false;
    if (ajeno && !x.cliente_id && clienteDeFila(x, ajeno)) return false;
    if (nivel === 'suyo' && x.cliente_id && !cartera.has(String(x.cliente_id))) return false;
    const tipoPersona = typeof conf.regla_persona === 'string' ? conf.regla_persona : 'horas_persona';
    if (x.persona_id && !ver(persona, { tipo: tipoPersona, persona_id: typeof x.persona_id === 'string' ? x.persona_id : String(x.persona_id) }, cp).ok) return false;
    if (Array.isArray(x.miembros)) {
      const ids = new Set(x.miembros.map((m) => (esFila(m) ? m.pid : m)));
      if (!ids.has(persona.id) || (realId && !ids.has(realId))) return false;
    }
    if ('setter' in x && typeof x.setter === 'string' && !veTodosSetters && x.setter !== miSetter) return false;
    return true;
  };

  // servir.py:1107
  const paso = (o: unknown, cid: unknown, lista: string | null, libre: boolean, leadPrivado: boolean): unknown => {
    libre = libre || !!(lista && CLAVES_TEXTO_LIBRE.test(lista));
    if (esFila(o)) {
      const cidFila = o.cliente_id || o.cid || cid;
      let actual = o;
      const q = quitar(cidFila);
      if (q.includes(CLAVES_CUOTA)) actual = sinCuota(actual, vePautadas(cidFila));
      if (!veRentabilidad) {
        const limpio: Fila = {};
        for (const [k, v] of Object.entries(actual)) {
          if (!CLAVES_RENTABILIDAD.test(k)) limpio[k] = v;
        }
        actual = limpio;
      }
      const sinInv = q.includes(CLAVES_INVERSION) && LISTAS_META.has(textoLista(lista)) && serieDeMeta(actual);
      const out: Fila = {};
      for (const [k, v] of Object.entries(actual)) {
        const quitada = q.some((rx) => rx.quita(k, v));
        if (quitada && !dejaHoras(k, cidFila)) continue;
        if (ajeno && ajeno.has(k.trim().toLowerCase())) continue;
        const leadHijo = leadPrivado || leadNorm.has(k.toLowerCase());
        if (leadHijo && LEAD_NOMBRES.has(k.toLowerCase())) continue;
        const hijo = paso(v, cidFila, k, libre, leadHijo);
        out[k] = sinInv && SERIES.has(k.toLowerCase()) ? serieSinGasto(hijo) : hijo;
      }
      return out;
    }
    if (typeof o === 'string') {
      if (lista && CLAVES_ENLACE.test(lista)) return enlaceSeguro(o);
      const q = quitar(cid);
      if (cid && (q.includes(CLAVES_CUOTA) || q.includes(CLAVES_INVERSION))) {
        const qi = new Set(importesAQuitar(!q.includes(CLAVES_CUOTA), !q.includes(CLAVES_INVERSION)));
        return libre ? sinImportesLibre(o, qi) : sinImportes(o, qi);
      }
      return o;
    }
    if (Array.isArray(o)) {
      let filas: unknown[] = o;
      const ft = lista != null ? filasTipo.get(lista) : undefined;
      if (ft && !ver(persona, { tipo: String(ft.tipo) }, cp).ok) {
        const campo = String(ft.campo);
        const valores = new Set((ft.valores as unknown[]) ?? []);
        filas = filas.filter((x) => !(esFila(x) && valores.has(x[campo])));
      }
      const sinClienteFuera = lista != null && soloTodo.includes(lista) && nivel !== 'todo';
      if (nivel === 'resumen' && leadNorm.has(textoLista(lista))) return [];
      return filas
        .filter((x) => {
          if (!filaOk(x)) return false;
          if (ajeno && typeof x === 'string' && ajeno.has(x.trim().toLowerCase())) return false;
          if (sinClienteFuera && esFila(x) && !x.cliente_id) return false;
          if (nivel === 'resumen' && esFila(x) && Object.keys(x).some((k) => CLAVES_FILA_LEAD.has(k.toLowerCase()))) return false;
          return true;
        })
        .map((x) => paso(x, cid, null, libre, leadPrivado));
    }
    return o;
  };

  let out = paso(obj, null, null, false, false);
  // servir.py:1146
  if (esFila(out)) {
    const claves = esFila(conf.claves_solo_tipo) ? conf.claves_solo_tipo : null;
    if (claves) {
      for (const [clave, tipo] of Object.entries(claves)) {
        if (clave in out && !ver(persona, { tipo: String(tipo) }, cp).ok) delete out[clave];
      }
    }
    if (nivel === 'resumen' && Array.isArray(conf.resumen)) {
      const deja = new Set(conf.resumen.filter((x): x is string => typeof x === 'string'));
      const corto: Fila = {};
      for (const [k, v] of Object.entries(out)) if (deja.has(k)) corto[k] = v;
      out = corto;
    }
  }
  const textos = conf.textos_sin_importes_salvo;
  if (typeof textos === 'string' && !ver(persona, { tipo: textos }, cp).ok) out = sinImportes(out);
  const ramas = esFila(conf.ramas_sin_importes_salvo) ? conf.ramas_sin_importes_salvo : null;
  if (ramas) {
    for (const [ruta, tipo] of Object.entries(ramas)) {
      if (!ver(persona, { tipo: String(tipo) }, cp).ok) out = ramaSinImportes(out, ruta.split('.'));
    }
  }
  if (conf.solo_cartera_silla) out = recortePorSilla(persona, cp, out, conf.solo_cartera_silla, clientes);
  // servir.py:1163
  if (ajeno && (persona.puestos ?? []).includes('account') && !ver(persona, { tipo: 'cuota' }, cp).ok && !conf.textos_del_cliente) {
    out = sinImportes(out);
  }
  return out;
}

/** En «ver como», ver() y puestosDe usan el mínimo de las dos personas. */
function personaDe(p: { id: string; nombre?: unknown; puestos?: string[] }): Persona {
  return { ...(p as Persona), nombre: typeof p.nombre === 'string' ? p.nombre : '', puestos: p.puestos ?? [] };
}

export function recortarModuloConVista(
  vista: VistaConContexto,
  obj: unknown,
  nivel: string | null | undefined,
  conf: Fila,
  clientes: { id: string; nombre?: string | null }[],
): unknown {
  const persona = personaDe(vista.como ?? vista.real);
  const cp = vista.cp;
  if (!cp) return obj;
  const solo = Array.isArray(conf.solo_todo_sin_cliente) ? conf.solo_todo_sin_cliente.filter((x): x is string => typeof x === 'string') : [];
  const leads = Array.isArray(conf.filas_lead) ? conf.filas_lead : [];
  const aplicar = () => recortarModulo(persona, cp, obj, nivel, solo, leads, conf, clientes);
  const real = personaDe(vista.real);
  return vista.como && vista.cpReal ? conVista({ real, cp: vista.cpReal }, aplicar) : aplicar();
}
