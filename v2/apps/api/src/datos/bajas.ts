/**
 * fuentes_verdad/clientes_activos.py › estado, fila_de_baja, quitar_bajas
 * y la proyección de agregados que esas dos rutas piden al final.
 * El estado sale del fichero publicado, no del disco.
 */

const BAJAS_CONFIRMADAS = new Set(['medalba']);
const TIPOS_ACTIVOS = new Set(['activo', 'recurrente', 'proyecto', 'firmado_sin_ficha']);
const HISTORICO = ['finanzas/', 'informes/', 'informe/', 'dinero_cliente/', 'ventas_ro', 'verdad/estado_clientes', 'verdad/bajas_tareas'];
const CAMPOS_CLIENTE = ['cliente', 'cliente_nombre', 'nombre_cliente', 'cliente_hoja', 'subcuenta', 'nombre_sub', 'carpeta', 'lista', 'cuenta', 'marca', 'empresa', 'organizacion', 'cli'];
const CAMPOS_DOMINIO = ['dominio', 'dominio_cliente'];

type Fila = Record<string, unknown>;
const esFila = (x: unknown): x is Fila => !!x && typeof x === 'object' && !Array.isArray(x);

export interface EstadoBajas {
  ids: Set<string>;
  activos: Set<string>;
  noOperativos: Set<string>;
  exactos: Set<string>;
  nombres: Set<string>;
  compactos: string[];
  rx: RegExp | null;
}

/** clientes_activos.py › norm. */
export function normBaja(s: unknown): string {
  let ascii = '';
  for (const ch of String(s ?? '').normalize('NFKD')) {
    if ((ch.codePointAt(0) ?? 0) <= 127) ascii += ch;
  }
  const base = ascii
    .toLowerCase()
    .replace(/[^a-z0-9&]+/g, ' ')
    .trim()
    .replace(/^\d{3,}\s+/, '');
  return base.replace(/\s+/g, ' ').trim();
}

function escapar(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function construir(doc: unknown): EstadoBajas {
  if (!esFila(doc)) {
    return {
      ids: new Set(BAJAS_CONFIRMADAS),
      activos: new Set(),
      noOperativos: new Set(BAJAS_CONFIRMADAS),
      exactos: new Set(BAJAS_CONFIRMADAS),
      nombres: new Set(BAJAS_CONFIRMADAS),
      compactos: ['medalba'],
      rx: /(?:^| )(medalba)(?: |$)/,
    };
  }
  const frases: string[] = [];
  const exactos = new Set<string>();
  for (const b of (doc.bajas as unknown[]) ?? []) {
    if (!esFila(b)) continue;
    const alias = esFila(b.alias) ? b.alias : {};
    for (const a of (alias.frase as unknown[]) ?? []) frases.push(normBaja(a));
    for (const a of (alias.exacto as unknown[]) ?? []) exactos.add(normBaja(a));
  }
  const unicas: string[] = [];
  const vistas = new Set<string>();
  for (const f of frases) {
    if (f && !vistas.has(f)) {
      vistas.add(f);
      unicas.push(f);
    }
  }
  for (const f of BAJAS_CONFIRMADAS) {
    if (!vistas.has(f)) unicas.push(f);
  }
  unicas.sort((a, b) => b.length - a.length || 0);
  const ids = new Set<string>([...(((doc.bajas_ids as unknown[]) ?? []).filter((x): x is string => typeof x === 'string')), ...BAJAS_CONFIRMADAS]);
  const activos = new Set<string>();
  const noOperativos = new Set<string>(ids);
  const nombres = new Set<string>();
  for (const a of (doc.activos as unknown[]) ?? []) {
    if (!esFila(a) || typeof a.id !== 'string' || !a.id) continue;
    if (TIPOS_ACTIVOS.has(String(a.tipo)) && !ids.has(a.id)) activos.add(a.id);
    else noOperativos.add(a.id);
  }
  for (const a of (doc.activos as unknown[]) ?? []) {
    if (!esFila(a) || typeof a.id !== 'string' || !noOperativos.has(a.id)) continue;
    nombres.add(normBaja(a.nombre));
  }
  for (const cid of noOperativos) nombres.add(normBaja(cid));
  const exactosFin = new Set<string>([...exactos, ...BAJAS_CONFIRMADAS]);
  const compactos = unicas.map((f) => f.replaceAll(' ', '')).filter((f) => f.length >= 6);
  const rx = unicas.length ? new RegExp(`(?:^| )(${unicas.map(escapar).join('|')})(?: |$)`) : null;
  return { ids, activos, noOperativos, exactos: exactosFin, nombres, compactos, rx };
}

const cache = new Map<string, EstadoBajas>();

/** estado() con la marca de la versión vigente, para no rehacer el regex en cada fichero. */
export function estadoClientes(doc: unknown, marca: string): EstadoBajas {
  const previo = cache.get(marca);
  if (previo) return previo;
  const estado = construir(doc);
  cache.set(marca, estado);
  return estado;
}

function esActivoId(cid: unknown, e: EstadoBajas): boolean {
  return typeof cid === 'string' && e.activos.has(cid);
}

function esBajaId(cid: unknown, e: EstadoBajas): boolean {
  return !!cid && typeof cid === 'string' && e.ids.has(cid);
}

function nombraBaja(texto: unknown, e: EstadoBajas, compacto = false): string | null {
  const t = normBaja(texto);
  if (!t) return null;
  if (e.exactos.has(t)) return t;
  if (e.rx) {
    const m = e.rx.exec(t);
    if (m?.[1]) return m[1];
  }
  if (compacto) {
    const tc = t.replaceAll(' ', '');
    return e.compactos.find((c) => tc.includes(c)) ?? null;
  }
  return null;
}

function exactoBaja(v: unknown, e: EstadoBajas): boolean {
  const t = normBaja(v);
  if (!t) return false;
  if (e.exactos.has(t) || esBajaId(v, e)) return true;
  if (!e.rx) return false;
  const m = new RegExp(`^(?:${e.rx.source})$`).exec(t);
  return !!m;
}

/** fila_de_baja. */
export function filaDeBaja(x: unknown, e: EstadoBajas): boolean {
  if (!esFila(x)) return false;
  for (const k of ['cliente_id', 'cid', 'cli']) {
    const v = x[k];
    if (v !== null && v !== undefined && v !== '' && !esActivoId(v, e)) return true;
  }
  for (const k of CAMPOS_CLIENTE) {
    const v = x[k];
    if (typeof v === 'string' && (e.nombres.has(normBaja(v)) || nombraBaja(v, e))) return true;
  }
  for (const k of CAMPOS_DOMINIO) {
    const v = x[k];
    if (typeof v === 'string' && nombraBaja(v, e, true)) return true;
  }
  if (('sub_id' in x || 'loc' in x || 'id' in x) && ['nombre', 'titulo'].some((k) => typeof x[k] === 'string' && exactoBaja(x[k], e))) return true;
  return false;
}

function esHistorico(rel: string | null | undefined): boolean {
  const r = rel == null ? 'None' : String(rel);
  return HISTORICO.some((h) => r.startsWith(h));
}

function paso(o: unknown, e: EstadoBajas): unknown {
  if (Array.isArray(o)) {
    return o.filter((v) => !filaDeBaja(v, e) && !(typeof v === 'string' && (e.noOperativos.has(v) || exactoBaja(v, e)))).map((v) => paso(v, e));
  }
  if (esFila(o)) {
    const out: Fila = {};
    for (const [k, v] of Object.entries(o)) {
      if (e.noOperativos.has(k) || exactoBaja(k, e)) continue;
      out[k] = paso(v, e);
    }
    return out;
  }
  return o;
}

/** quitar_bajas. Los históricos (finanzas, informes, ventas_ro…) salen igual. */
export function quitarBajas(obj: unknown, rel: string, e: EstadoBajas): unknown {
  if (esHistorico(rel)) return obj;
  let out = paso(obj, e);
  if (rel === 'verdad/clientes' && esFila(out) && Array.isArray(out.comun)) {
    out = { ...out, comun: out.comun.filter((r) => esFila(r) && esActivoId(r.id, e)) };
    out = verdadAgregados(out);
  }
  if (rel === 'crm/crm' && esFila(out) && Array.isArray(out.subcuentas)) {
    out = {
      ...out,
      subcuentas: out.subcuentas.filter((r) => esFila(r) && (r.tipo === 'prueba' || r.tipo === 'interna' || esActivoId(r.cliente_id, e))),
    };
    out = crmAgregados(out);
  }
  if (rel === 'mi_trabajo/mi_trabajo') out = miTrabajoAgregados(out);
  return out;
}

function filasOk(doc: Fila, clave: string, identidad: string): Fila[] | null {
  const filas = doc[clave];
  if (!Array.isArray(filas)) return null;
  if (filas.some((f) => !esFila(f) || typeof f[identidad] !== 'string' || !f[identidad])) return null;
  const ids = filas.map((f) => (f as Fila)[identidad]);
  return new Set(ids).size === ids.length ? (filas as Fila[]) : null;
}

function cuenta(filas: Fila[] | null, clave: string, valor = true): number | null {
  if (!filas || filas.some((f) => typeof f[clave] !== 'boolean')) return null;
  return filas.filter((f) => f[clave] === valor).length;
}

function metaAgregados(doc: Fila): Fila {
  return {
    version: '207.1',
    alcance: 'filas_visibles_post_permisos_y_act',
    fuente_generado: doc.generado ?? null,
    datos_hasta: doc.datos_hasta ?? null,
    periodo_certificado: false,
    estado: 'referencia_de_copia',
    limitacion: 'No acredita lectura completa, cartera asignada, salud actual ni conversiones.',
  };
}

/** proyeccion_agregados_activos.py › verdad. */
function verdadAgregados(doc: unknown): unknown {
  if (!esFila(doc)) return doc;
  const out = structuredClone(doc);
  const comun = filasOk(out, 'comun', 'id');
  const detalle = filasOk(out, 'clientes', 'cliente_id');
  if ('resumen' in out) {
    const resumen: Fila = esFila(out.resumen) ? Object.fromEntries(Object.keys(out.resumen).map((k) => [k, null])) : {};
    const conocidos = ['critico', 'atencion', 'bien'];
    const estadoValido = comun !== null && comun.every((f) => conocidos.includes(String(f.gravedad)));
    for (const k of conocidos) resumen[k] = estadoValido ? comun!.filter((f) => f.gravedad === k).length : null;
    resumen.estado_desconocido = comun !== null ? comun.filter((f) => !conocidos.includes(String(f.gravedad))).length : null;
    resumen.nuevos = cuenta(comun, 'nuevo');
    resumen.sin_account = cuenta(comun, 'sin_account');
    resumen.sin_reunion_mes_pasado = cuenta(detalle, 'sin_reunion_mes_pasado');
    resumen.bloqueo_callado = cuenta(detalle, 'bloqueo_callado');
    out.resumen = resumen;
  }
  const visibles = new Set<string>([
    ...(comun ? comun.map((f) => String(f.id)) : []),
    ...(detalle ? detalle.map((f) => String(f.cliente_id)) : []),
  ]);
  if (Array.isArray(out.carteras)) {
    for (const c of out.carteras) {
      if (!esFila(c)) continue;
      for (const [campo, contador] of [
        ['principal', 'n_principal'],
        ['apoyo', 'n_apoyo'],
      ] as const) {
        const ids = c[campo];
        const valido = Array.isArray(ids) && ids.every((i) => typeof i === 'string' && i) && new Set(ids).size === ids.length;
        c[campo] = valido ? (ids as string[]).filter((i) => visibles.has(i)) : [];
        c[contador] = valido && (comun !== null || detalle !== null) ? (c[campo] as string[]).length : null;
      }
      const u = c.universo;
      if (esFila(u)) {
        let fuera = u.fuera;
        if (Array.isArray(fuera) && fuera.every((i) => typeof i === 'string' && i)) {
          fuera = (fuera as string[]).filter((i) => visibles.has(i));
          u.fuera = fuera;
        }
        const principal = Array.isArray(c.principal) ? (c.principal as string[]) : [];
        const valido =
          typeof c.n_principal === 'number' &&
          Array.isArray(fuera) &&
          fuera.every((i) => typeof i === 'string' && i) &&
          new Set(fuera).size === fuera.length &&
          (fuera as string[]).every((i) => principal.includes(i));
        u.dentro = valido ? (c.n_principal as number) - (fuera as string[]).length : null;
        u.texto = valido
          ? `Referencia de la copia: ${String(u.dentro)} de ${String(c.n_principal)} clientes visibles en este universo.`
          : 'Universo pendiente de verificar.';
      }
    }
  }
  out.agregados_cobertura = metaAgregados(doc);
  return out;
}

const CRM_DESCONOCIDOS = [
  'verde', 'ambar', 'rojo', 'pct_verde', 'leads_30d', 'sin_tocar_24h', 'velocidad_pct_1h', 'velocidad_juzgables',
  'despachos_cumplen_garantia', 'despachos_juzgables_garantia', 'asistencia_pct', 'estancados_72h', 'integracion_rota',
  'encendidas_sin_especialista',
];

/** proyeccion_agregados_activos.py › crm. */
function crmAgregados(doc: unknown): unknown {
  if (!esFila(doc)) return doc;
  const out = structuredClone(doc);
  const filas = filasOk(out, 'subcuentas', 'sub_id');
  const clientes = filas ? filas.filter((f) => f.tipo !== 'prueba' && f.tipo !== 'interna') : null;
  const diagnostico = filas ? filas.filter((f) => f.tipo === 'prueba' || f.tipo === 'interna') : null;
  if ('resumen' in out) {
    const r: Fila = esFila(out.resumen) ? Object.fromEntries(Object.keys(out.resumen).map((k) => [k, null])) : {};
    for (const k of CRM_DESCONOCIDOS) r[k] = null;
    r.subcuentas = filas ? filas.length : null;
    r.de_clientes = clientes ? clientes.length : null;
    r.pruebas_e_internas = diagnostico ? diagnostico.length : null;
    r.encendidas = cuenta(clientes, 'encendida');
    r.estado_desconocido = clientes ? clientes.length : null;
    r.citas_30d = { agendadas: null, celebradas: null, no_presentadas: null, sin_estado: null, canceladas: null, futuras: null };
    r.citas_14d = { agendadas: null, celebradas: null, no_presentadas: null, sin_estado: null };
    r.whatsapp = { enviados: null, fallidos: null };
    out.resumen = r;
  }
  if (Array.isArray(out.especialistas)) {
    for (const e of out.especialistas) {
      if (!esFila(e)) continue;
      for (const k of ['clientes', 'encendidas', 'verde', 'ambar', 'rojo', 'gris', 'sin_tocar', 'sin_estado', 'sin_subcuenta']) e[k] = null;
      const asignadas = clientes && typeof e.id === 'string' ? clientes.filter((f) => f.especialista_id === e.id) : null;
      e.subcuentas = asignadas ? asignadas.length : null;
      e.agregados_cobertura = {
        estado: 'parcial',
        alcance: 'subcuentas_visibles',
        cartera_asignada_confirmada: false,
        fuente_generado: doc.generado,
      };
    }
  }
  out.agregados_cobertura = metaAgregados(doc);
  return out;
}

/** mi_trabajo_proyeccion.py › recortar. */
function miTrabajoAgregados(obj: unknown): unknown {
  if (!esFila(obj)) return obj;
  const out: Fila = { ...obj };
  const porId = new Map<string, Fila[]>();
  for (const r of (obj.tareas as unknown[]) ?? []) {
    if (esFila(r) && typeof r.id === 'string' && typeof r.lista_id === 'string' && r.lista_id && 'cli' in r) {
      const lista = porId.get(r.id) ?? [];
      lista.push(r);
      porId.set(r.id, lista);
    }
  }
  const seguros = new Map<string, Fila[]>();
  for (const [tid, filas] of porId) {
    const identidades = new Set(filas.map((r) => `${String(r.cli)}\0${String(r.lista_id)}`));
    const personas = filas.map((r) => r.persona_id);
    if (identidades.size === 1 && personas.every((p) => typeof p === 'string' && p) && new Set(personas).size === personas.length) {
      seguros.set(tid, filas);
    }
  }
  const listas = new Set<string>();
  for (const filas of seguros.values()) for (const r of filas) listas.add(String(r.lista_id));
  for (const clave of ['estados_lista', 'estados_detalle']) {
    if (!(clave in out)) continue;
    out[clave] = esFila(out[clave]) ? Object.fromEntries(Object.entries(out[clave] as Fila).filter(([k]) => listas.has(k))) : {};
  }
  const permitida = (r: unknown): boolean => {
    if (!esFila(r)) return false;
    const filas = typeof r.tarea_id === 'string' ? seguros.get(r.tarea_id) : undefined;
    if (!filas || !filas.some((t) => t.persona_id === r.persona_id)) return false;
    if (r.cliente_id != null && r.cliente_id !== '' && r.cliente_id !== filas[0]?.cli) return false;
    return true;
  };
  for (const clave of ['largas', 'raras_estimacion', 'raras_cliente', 'raras_cliente_n']) {
    if (!(clave in out)) continue;
    out[clave] = Array.isArray(out[clave]) ? (out[clave] as unknown[]).filter(permitida) : [];
  }
  return out;
}
