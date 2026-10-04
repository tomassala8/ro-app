// modulos/_servicios.js · qué servicios tiene ACTIVOS un cliente y qué medida le aplica (Tomás, 3-oct · ../58_FEEDBACK_TOMAS_03OCT.md).
//
// Dos reglas de Tomás que comparten esta pieza:
//   1. Un cliente que no usa el CRM con nosotros no enseña «0 citas · 0 celebradas · 0 ventas» como si fuera un dato: se dice
//      «No usa el CRM con nosotros». Un cliente sin campaña de Meta encendida no cuenta como «fuera de objetivo» ni enseña
//      ceros de publicidad.
//   2. Al abrir un cliente (ficha y paneles) sale primero la vista de sus servicios activos: con publicidad, la publicidad;
//      sin publicidad y con SEO o web, la web; si solo es redes, redes.
//
// No se calcula nada nuevo: se lee lo que ya trae la app (sin importes):
//   · servicios del cliente (data/clientes.json › servicios: publicidad, crm_ghl, seo, mantenimiento, outreach «sí/no»), que
//     llega en ctx.clientes a quien abre su detalle;
//   · la verdad única (campana_activa = campaña de Meta encendida); una silla no prueba contratación;
//   · el uso real del CRM: menos de 5 contactos en toda la historia de la subcuenta = no lo usa (la MISMA regla que
//     fuentes_crm/generar_crm.py › sin_uso).

export const UMBRAL_CRM_SIN_USO = 5;
export const TEXTO_SIN_CRM = 'No usa el CRM con nosotros';
export const TEXTO_SIN_META = 'Sin campaña de Meta encendida';

const si = v => v === true || (typeof v === 'string' && ['sí', 'si'].includes(v.trim().toLowerCase()));
const no = v => v === 'no' || v === false;

/** usoCrm({ servicios, ghl, crmSub }) → 'uso' | 'sin_uso' | 'sin_crm' | null (no se sabe).
 *  crmSub = fila de crm/crm › subcuentas (sin_uso); ghl = fuente «ghl» de la ficha (datos.contactos). */
export function usoCrm({ servicios, ghl, crmSub } = {}) {
  if (crmSub && typeof crmSub.sin_uso === 'boolean') return crmSub.sin_uso ? 'sin_uso' : 'uso';
  const n = ghl?.datos?.contactos;
  if (typeof n === 'number') return n < UMBRAL_CRM_SIN_USO ? 'sin_uso' : 'uso';
  if (no(servicios?.crm_ghl)) return 'sin_crm';
  if (ghl && ghl.estado === 'sin_conectar' && !si(servicios?.crm_ghl)) return 'sin_crm';
  return null;
}
/** ¿Se puede enseñar la cifra del CRM (citas, celebradas, ventas) como un dato? Solo si lo usa (o no se sabe). */
export const crmMedible = estado => estado !== 'sin_uso' && estado !== 'sin_crm';
/** El texto que sustituye a los ceros cuando no aplica. */
export function textoCrm(estado) {
  if (estado === 'sin_uso') return `${TEXTO_SIN_CRM}: su subcuenta de GoHighLevel no tiene contactos (menos de ${UMBRAL_CRM_SIN_USO} en toda su historia).`;
  if (estado === 'sin_crm') return `${TEXTO_SIN_CRM}: no tiene subcuenta de GoHighLevel con nosotros.`;
  return '';
}

/** metaEncendida({ verdad, captacion, meta }) → true | false | null. La verdad única manda (campana_activa). */
export function metaEncendida({ verdad, captacion, meta } = {}) {
  if (typeof verdad?.campana_activa === 'boolean') return verdad.campana_activa;
  if (typeof captacion?.meta_activa === 'boolean') return captacion.meta_activa;
  const camp = meta?.datos?.campanas;
  if (Array.isArray(camp)) return camp.some(x => (x.leads_7d || 0) > 0 || (x.gasto_7d || 0) > 0);
  return null;
}

/** serviciosActivos(ctx, cid, extra) → { publicidad, meta, crm, seo, web, redes, outreach, lista }
 *  extra = { ghl, crmSub, captacion, meta } si la pantalla ya los tiene a mano. */
export function serviciosActivos(ctx, cid, extra = {}) {
  const c = (ctx.clientes || []).find(x => x.id === cid) || {};
  const s = c.servicios || {};
  const v = typeof ctx.verdad === 'function' ? ctx.verdad(cid) : null;
  const meta = metaEncendida({ verdad: v, captacion: extra.captacion, meta: extra.meta });
  const out = {
    meta,
    publicidad: meta === true || (meta === null && si(s.publicidad)),
    crm: usoCrm({ servicios: s, ghl: extra.ghl, crmSub: extra.crmSub }),
    seo: si(s.seo),
    web: si(s.web) || si(s.mantenimiento),
    redes: si(s.redes) || si(s.social_media),
    outreach: si(s.outreach),
  };
  out.lista = ['publicidad', 'seo', 'web', 'redes', 'outreach'].filter(k => out[k]).concat(out.crm === 'uso' ? ['crm'] : []);
  return out;
}

/** Pestaña de entrada de la ficha según los servicios activos (sin «resultados» si no hay publicidad ni CRM en uso). */
export function pestanaFicha(sv, { perfil, orden }) {
  const hay = k => (orden || []).includes(k);
  const conPubli = sv.publicidad || sv.crm === 'uso';
  let p = 'resumen';
  if (conPubli) p = ['publicidad', 'crm'].includes(perfil) ? 'resultados' : 'resumen';
  else if (sv.seo || sv.web) p = 'web';
  else if (sv.redes) p = 'redes';
  if (perfil === 'seo' && (sv.seo || sv.web)) p = 'web';
  if (perfil === 'redes' && sv.redes) p = 'redes';
  return hay(p) ? p : (orden || ['resumen'])[0];
}
/** ¿Tiene sentido esta pestaña para este cliente? (para no reabrir «Resultados» en un cliente sin publicidad ni CRM). */
export function pestanaConSentido(tab, sv) {
  if (tab === 'resultados') return !!(sv.publicidad || sv.crm === 'uso');
  if (tab === 'web') return !!(sv.seo || sv.web);
  if (tab === 'redes') return !!sv.redes;
  return true;
}
/** Orden de herramientas de Paneles con lo que el cliente tiene activo primero. */
export function ordenHerramientas(herrs, sv) {
  const peso = k => {
    if (k === 'meta') return sv.publicidad ? 0 : 9;
    if (k === 'ghl') return sv.crm === 'uso' ? 1 : 9;
    if (k === 'gsc' || k === 'ga4') return sv.publicidad ? 3 : (sv.seo || sv.web ? 0 : 5);
    if (k === 'mc') return sv.redes && !sv.publicidad && !(sv.seo || sv.web) ? 0 : 6;
    return 7;
  };
  return [...herrs].map((k, i) => [k, i]).sort((a, b) => peso(a[0]) - peso(b[0]) || a[1] - b[1]).map(x => x[0]);
}
