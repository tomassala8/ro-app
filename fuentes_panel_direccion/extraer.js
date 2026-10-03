/* fuentes_panel_direccion/extraer.js
 * Se pega al final de una COPIA de panel_v2.html (el panel de resultados v30) y se abre con Chrome sin ventana.
 * No calcula nada: usa el render() del propio panel para cada pestaña y cada periodo, y guarda lo que pinta
 * (HTML limpio, clases con prefijo px-) para que el módulo «Panel de dirección» lo vuelva a pintar con la carcasa
 * de la app. Así cada cifra sale del mismo código que la v30 (paridad por construcción).
 */
(function () {
  const PERIODOS = [
    { id: 'sep', texto: 'Septiembre', preset: 31 },
    { id: 'oct', texto: 'Octubre (en curso)', preset: 30 },
    { id: 'todo', texto: 'Todo desde el 1-ago', preset: 99 },
    { id: 'd14', texto: 'Desde el 14-sep', preset: 0 },
    { id: 'd7', texto: 'Últimos 7 días', preset: 7 },
  ];
  const EMPRESA = ['fres', 'fing', 'cli', 'fgas', 'fcaja', 'emp'];
  const CAPTACION = ['sum', 'pub', 'atr', 'res', 'vent', 'ope'];
  const etiquetas = {};
  document.querySelectorAll('.tabs .tab').forEach(b => { etiquetas[b.id.slice(2)] = b.textContent.trim(); });

  function fijarPeriodo(n) {
    state.custom = false; state.preset = n; state.to = TODAY;
    if (n === 31) { const pf = new Date(MES + 'T12:00:00Z'); pf.setUTCMonth(pf.getUTCMonth() - 1); const f = pf.toISOString().slice(0, 10); state.from = f < MIN_DAY ? MIN_DAY : f; state.to = addDays(MES, -1); return; }
    state.from = n === 30 ? MES : n === 99 ? MIN_DAY : n ? (addDays(TODAY, -(n - 1)) < MIN_DAY ? MIN_DAY : addDays(TODAY, -(n - 1))) : DEF_FROM;
  }

  function limpiar(origen) {
    const n = origen.cloneNode(true);
    n.querySelectorAll('script, input, select, textarea, .filtros, .rfilters, button.linkbtn, .seg').forEach(x => x.remove());
    // botones que quedan: los avisos («Ver la agenda →») pasan a div con la pestaña a la que llevaban; el resto, a texto
    const IR = [['agenda', 'res'], ['de dónde vienen', 'ope'], ['bandeja', 'ope'], ['recuperar', 'vent'], ['Publicidad', 'pub'], ['Clientes', 'cli'], ['Ventas', 'vent']];
    n.querySelectorAll('button').forEach(b => {
      const d = document.createElement('div'); d.className = b.className;
      const t = b.textContent; const ir = IR.find(([k]) => t.includes(k));
      if (ir && b.classList.contains('alert')) d.setAttribute('data-ir', ir[1]);
      d.append(...b.childNodes); b.replaceWith(d);
    });
    n.querySelectorAll('*').forEach(e => {
      [...e.attributes].forEach(a => { if (/^on/i.test(a.name) || a.name === 'tabindex' || a.name === 'role' && e.tagName !== 'svg' || a.name.startsWith('aria-') && e.tagName !== 'svg' || a.name === 'id') e.removeAttribute(a.name); });
      const c = e.getAttribute('class'); if (c) e.setAttribute('class', c.split(/\s+/).filter(Boolean).map(x => 'px-' + x).join(' '));
      if (e.tagName === 'A') { e.setAttribute('target', '_blank'); e.setAttribute('rel', 'noopener'); }
    });
    n.querySelectorAll('details').forEach(d => d.removeAttribute('open'));
    return n.innerHTML.replace(/\s+\n/g, '\n');
  }

  function pintar(tab) { state.tab = tab; render(); return limpiar(document.getElementById('p-' + tab)); }

  const out = { generado: DATA.generated, ventana: DATA.window, fres: DATA.fres || null, etiquetas, periodos: PERIODOS, empresa: {}, captacion: {}, rangos: {},
    pie: (document.getElementById('foot') || {}).innerText || '', ltv_meses: typeof LTV_MESES !== 'undefined' ? LTV_MESES : null };
  state.allAds = true; state.cAll = true; state.mode = 'hecho'; state.capa = 'all';
  EMPRESA.forEach(t => { out.empresa[t] = pintar(t); });
  PERIODOS.forEach(p => {
    fijarPeriodo(p.preset);
    out.rangos[p.id] = { desde: state.from, hasta: state.to };
    out.captacion[p.id] = {};
    CAPTACION.forEach(t => { fijarPeriodo(p.preset); out.captacion[p.id][t] = pintar(t); });
  });
  const pre = document.createElement('pre'); pre.id = 'salida-extraccion'; pre.textContent = JSON.stringify(out);
  document.body.replaceChildren(pre);
})();
