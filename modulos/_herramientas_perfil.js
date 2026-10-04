import { h } from '../componentes.js';

// 232: enlaces públicos; esta selección orienta, nunca otorga acceso al proveedor.
const CATALOGO = Object.freeze([
  { id: 'clickup', nombre: 'ClickUp', url: 'https://app.clickup.com/', modulo: 'mi-trabajo' },
  { id: 'chatgpt', nombre: 'ChatGPT', url: 'https://chatgpt.com/' },
  { id: 'claude', nombre: 'Claude', url: 'https://claude.ai/' },
  { id: 'higgsfield', nombre: 'Higgsfield', url: 'https://higgsfield.ai/', puestos: ['direccion', 'operaciones', 'trafficker', 'jefa_publicidad', 'produccion', 'redes'] },
  { id: 'ghl', nombre: 'GoHighLevel', url: 'https://app.gohighlevel.com/', modulo: 'salud-crm' },
  { id: 'meta', nombre: 'Meta Business', url: 'https://business.facebook.com/', modulo: 'captacion' },
  { id: 'googleads', nombre: 'Google Ads', url: 'https://ads.google.com/', puestos: ['direccion','operaciones','account','trafficker','jefa_publicidad'] },
  { id: 'analytics', nombre: 'Analytics', url: 'https://analytics.google.com/', puestos: ['direccion','operaciones','account','trafficker','jefa_publicidad','seo','web','jefa_seo','produccion'] },
  { id: 'searchconsole', nombre: 'Search Console', url: 'https://search.google.com/search-console/', puestos: ['direccion','operaciones','account','seo','web','jefa_seo','produccion'] },
  { id: 'modular', nombre: 'Modular', url: 'https://app.modulards.com/', puestos: ['direccion','operaciones','web','seo','jefa_seo','produccion'] },
  { id: 'drive', nombre: 'Drive', url: 'https://drive.google.com/' },
]);

export function herramientasPerfil(ctx) {
  if (!ctx?.persona?.id || !Array.isArray(ctx.persona.puestos) ||
      (ctx.persona.estado && ctx.persona.estado !== 'activo') || ctx.persona.activo === false) return [];
  return CATALOGO.filter(x => (!x.puestos || x.puestos.some(p => ctx.persona.puestos.includes(p))) &&
    (!x.modulo || typeof ctx.veModulo === 'function' && ctx.veModulo(x.modulo)))
    .map(({ id, nombre, url }) => ({ id, nombre, url }));
}

export function panelHerramientas(ctx, vigente) {
  if (!vigente()) return null;
  const identidad = JSON.stringify([ctx.real?.id || '', ctx.persona?.id || '', ctx.persona?.puestos || []]);
  const puede = id => vigente() && identidad === JSON.stringify([ctx.real?.id || '', ctx.persona?.id || '', ctx.persona?.puestos || []]) &&
    herramientasPerfil(ctx).some(x => x.id === id);
  const enlaces = herramientasPerfil(ctx);
  const principales = enlaces.filter(x => ['clickup','chatgpt','claude','ghl','meta'].includes(x.id));
  const extras = enlaces.filter(x => !principales.includes(x));
  const boton = x => h('a', { class: 'bt', href: x.url, target: '_blank', rel: 'noopener noreferrer', referrerpolicy: 'no-referrer',
    style: { minHeight: '44px', minWidth: '0', whiteSpace: 'normal', borderRadius:'12px' },
    on: { click: e => { if (!puede(x.id)) e.preventDefault(); } } }, x.nombre);
  if (!enlaces.length) return null;
  return h('section', { 'data-mid-herramientas': '', 'aria-label': 'Herramientas de mi perfil', style: { minWidth: '0' } },
    h('nav', { 'aria-label': 'Abrir herramienta externa', style: { display: 'flex', flexWrap: 'wrap', alignItems:'center', gap: 'var(--s-2)' } },
      h('b', {style:{fontSize:'13px',marginRight:'var(--s-2)'}}, 'Mis herramientas'),
      principales.map(boton),
      extras.length ? h('details', {}, h('summary', {style:{minHeight:'44px',display:'flex',alignItems:'center',cursor:'pointer'}},'Más herramientas'),
        h('nav', {'aria-label':'Más herramientas de mi perfil',style:{display:'flex',flexWrap:'wrap',gap:'var(--s-2)',padding:'var(--s-2) 0'}},extras.map(boton))) : null),
    ctx.veModulo?.('ficha') ? h('a', {class:'bt',href:'#/ficha',style:{minHeight:'44px',marginTop:'var(--s-2)'},on:{click:e=>{if(!vigente()||identidad!==JSON.stringify([ctx.real?.id||'',ctx.persona?.id||'',ctx.persona?.puestos||[]])||!ctx.veModulo?.('ficha'))e.preventDefault();}}},'Herramientas y accesos de mis clientes') : null,
    h('details', {}, h('summary', {}, 'Contraseñas y accesos de clientes'),
      h('p', { class: 'sub' }, 'La bóveda de empresa está pendiente de verificar. RO no la desbloquea ni muestra sus claves. Los accesos de cada cliente se consultan desde su ficha autorizada; WordPress no tiene un enlace común para todos los clientes.')));
}
