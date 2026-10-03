#!/usr/bin/env python3
"""Barrido total de la app de RO (38 · dimensión 2 «Cero errores», método §1). SOLO LEE la app.

Uso:
  python3 despliegue/barrido_total.py --vuelta v0            # todo: 32 personas × rutas × 1440/1024/768/700/560/480/390
  python3 despliegue/barrido_total.py --vuelta v1 --personas lucia,tomas --hilos 4
  python3 despliegue/barrido_total.py --vuelta v0 --solo-informe   # rehace 39_BARRIDO_TOTAL.md desde los JSON
  python3 despliegue/barrido_total.py --vuelta v2 --puerto 9066     # R15a: otro puerto (por defecto 9000) si hay otro barrido
  python3 despliegue/barrido_total.py --borrar-capturas-de v0      # R15a: borra las capturas .jpg de esa vuelta y deja sus JSON

Qué hace:
  1. Copia local.db a una carpeta temporal y arranca SU PROPIO servidor:
       RO_DB=<copia> python3 servir.py --bind 127.0.0.1 --puerto 9000   (lo cierra al acabar; --puerto lo cambia)
  2. Con Playwright sin ventana entra como CADA persona activa (/api/elegir) y recorre cada ruta de su menú,
     sus pestañas (role=tab), sub-rutas del mismo módulo que la pantalla enlaza, 2 fichas propias y 1 ajena,
     cambia el periodo donde hay selector, abre los menús «Más» y los plegables (<details>) principales.
  3. En cada pantalla y ancho (1440, 1024, 768, 700, 390; V3a: 768 y 700 por la tableta y la vista previa a ~706 px): captura .jpg (calidad 70) y comprobaciones automáticas
     (consola, errores de página, 4xx/5xx, textos prohibidos, códigos internos, desborde, letra < 12 px,
     toque < 32 px a 390, desplegables recortados/tapados/sin cerrar (V3a, a cada ancho), imágenes rotas, enlaces vacíos o a rutas que no existen, carga > 1 s, solapes,
     contraste < 4,5:1).
  4. Resultado: capturas/_barrido/<vuelta>/<persona>/<ruta>_<ancho>.jpg, capturas/_barrido/<vuelta>/resultado.json
     y ../39_BARRIDO_TOTAL.md.

No pulsa ninguna acción (solo pestañas, periodo, «Más» y plegables). Nada sale de 127.0.0.1.
Si el disco libre baja de 1,5 GB, para y lo avisa.
"""
import argparse, json, os, re, shutil, signal, subprocess, sys, tempfile, time, urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
RAIZ = APP.parent
PUERTO = int(os.environ.get("RO_BARRIDO_PUERTO") or 9000)   # R15a: --puerto (los procesos hijos lo heredan por el entorno)
BASE = f"http://127.0.0.1:{PUERTO}"


def poner_puerto(n):
    """R15a: cambia el puerto del servidor propio (también en cada proceso de ProcessPoolExecutor, vía initializer)."""
    global PUERTO, BASE
    PUERTO = int(n)
    BASE = f"http://127.0.0.1:{PUERTO}"
    os.environ["RO_BARRIDO_PUERTO"] = str(PUERTO)


def borrar_capturas(vuelta):
    """R15a: libera disco. Borra las capturas (.jpg/.png) de capturas/_barrido/<vuelta>/ y deja resultado.json y los
    _resultado.json de cada persona (así --solo-informe sigue funcionando). Devuelve (ficheros, bytes)."""
    base = APP / "capturas" / "_barrido" / vuelta
    if not base.is_dir() or not re.fullmatch(r"[\w.-]+", vuelta):
        raise SystemExit(f"No existe la vuelta «{vuelta}» en capturas/_barrido/.")
    n = b = 0
    for f in base.rglob("*"):
        if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png"):
            b += f.stat().st_size
            f.unlink()
            n += 1
    for d in sorted((x for x in base.rglob("*") if x.is_dir()), key=lambda x: -len(x.parts)):
        if not any(d.iterdir()):
            d.rmdir()
    return n, b
# V3a: 768 (tableta) y 700 (vista previa del coordinador, ~706 px: ahí se salía el chip rojo de «Lo mío»).
# Ronda U (3-oct): 560 y 480, la franja entre móvil y tableta donde las filas de «Lo mío» se rompían (título reducido a una letra).
ANCHOS = [(1440, 900), (1024, 768), (768, 1024), (700, 900), (560, 900), (480, 900), (390, 844)]
ANCHO_ANCHO, ANCHO_MOVIL = ANCHOS[0], ANCHOS[-1]   # pestañas, periodo, «Más» y plegables: solo 1440 y 390
MIN_LIBRE = 1.5 * 1024 ** 3
MAX_ALTO_CAPTURA = 4000
MAX_PESTANAS = 14
MAX_SUBRUTAS = 3


def libre():
    return shutil.disk_usage(str(APP)).free


# ------------------------------------------------------------------ comprobaciones en la página
# Devuelve una lista de fallos {tipo, detalle, sel, zona} para el estado actual de la pantalla al ancho actual.
MIRAR = r"""
(opts) => {
  window.scrollTo(0, 0);
  const W = innerWidth, fallos = [];
  const add = (tipo, detalle, el, extra) => fallos.push(Object.assign({ tipo, detalle: String(detalle).slice(0, 220), sel: el ? selDe(el) : '', zona: el ? zonaDe(el) : '' }, extra || {}));
  function selDe(el) {
    const p = [];
    for (let e = el, i = 0; e && e.nodeType === 1 && i < 4; e = e.parentElement, i++) {
      let s = e.tagName.toLowerCase();
      if (e.id) { s += '#' + e.id; p.unshift(s); break; }
      const c = [...e.classList].filter(x => !/^(on|activo|abierto)$/.test(x)).slice(0, 2);
      if (c.length) s += '.' + c.join('.');
      p.unshift(s);
    }
    return p.join(' > ');
  }
  function zonaDe(el) {
    if (el.closest('#barra-ctx')) return 'periodo';
    if (el.closest('#main')) return 'main';
    if (el.closest('nav.side')) return 'menu';
    if (el.closest('header.topbar')) return 'cabecera';
    return 'otra';
  }
  const visible = el => {
    if (!el || !el.isConnected) return false;
    if (el.closest('[hidden], [aria-hidden="true"]')) return false;
    const d = el.closest('details:not([open])');
    if (d && !el.closest('summary') && d.contains(el)) { const s = d.querySelector(':scope > summary'); if (!s || !s.contains(el)) return false; }
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || parseFloat(cs.opacity) === 0) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  // fuera de la pantalla en horizontal (menú lateral plegado en móvil, etc.)
  const enPantalla = r => r.right > 0 && r.left < W;

  // ---- elementos con texto propio
  const conTexto = [];
  const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, { acceptNode: n => n.nodeValue.trim() ? 1 : 2 });
  const vistos = new Map();
  for (let n = tw.nextNode(); n; n = tw.nextNode()) {
    const el = n.parentElement;
    if (!el || /^(SCRIPT|STYLE|NOSCRIPT|TEMPLATE|OPTION)$/.test(el.tagName)) continue;
    if (!vistos.has(el)) vistos.set(el, []);
    vistos.get(el).push(n);
  }
  for (const [el, nodos] of vistos) { if (visible(el)) conTexto.push([el, nodos]); }

  // ---- textos prohibidos (texto visible de la página entera)
  const PROHIBIDOS = [
    ['texto_null', /\bnull\b/], ['texto_undefined', /\bundefined\b/], ['texto_NaN', /\bNaN\b/],
    ['texto_importe', /\[importe\]/i], ['texto_Infinity', /\b-?Infinity\b/], ['texto_invalid_date', /Invalid Date/i],
    ['Jessi', /\bJess?i(ca)?\b/], ['texto_object', /\[object \w+\]/],
    ['error_pintado', /No se ha podido pintar|no carga\b|Error: |TypeError|ReferenceError/],
    // V2-E (39b ajuste 4): plural con «1» («1 usuarios», «1 mensajes»…)
    ['plural_1', /(^|[^\d.,])1 (usuarios|mensajes|leads|clics|días|correos|citas|contactos|cambios|subcuentas|tareas|alertas|clientes|horas|piezas)\b/],
  ];
  const INTERNOS = [
    ['fichero', /\b[\w\-]+\.(json|py|sql|db|csv|mjs)\b/], ['fichero_js', /\b[\w\-]+\.js\b/],
    ['privado', /_privado/], ['id_p_', /\bp_[a-z0-9_]{2,}\b/], ['ro_id', /\bRO-\d{2,}\b/],
    ['codigo', /\b(?:D-(?:P-)?[A-Z]{0,4}-?\d+[A-Z0-9]*|[MNEWR]\d{1,2}[ab]?|SP\d{2})\b/],
    // V2-E (39b ajuste 4): enlaces Markdown sin convertir y órdenes de terminal con «--opcion» a la vista
    ['markdown', /\[[^\]]+\]\(https?:\/\//], ['flag_cli', /(^|\s)--[a-z][\w-]{2,}/],
  ];
  for (const [el, nodos] of conTexto) {
    const t = nodos.map(n => n.nodeValue).join(' ');
    if (el.closest('input, textarea, code, pre, kbd')) continue;
    const r = el.getBoundingClientRect();
    if (!enPantalla(r)) continue;
    for (const [tipo, re] of PROHIBIDOS) { const m = t.match(re); if (m) add(tipo, ctxDe(t, m.index, m[0].length), el); }
    for (const [sub, re] of INTERNOS) {
      const m = t.match(re);
      if (!m) continue;
      if (sub === 'ro_id' && el.closest('a')) continue;
      add('codigo_interno', `${sub}: ${ctxDe(t, m.index, m[0].length)}`, el, { sub });
    }
  }
  function ctxDe(t, i, l) { return '«' + t.slice(Math.max(0, i - 35), i + l + 35).replace(/\s+/g, ' ').trim() + '»'; }

  // ---- «—» suelto como cifra principal
  document.querySelectorAll('.cifra-display, .valor-ult, .cifra, .tile .tv, .kpi .v, span.v, .big').forEach(el => {
    if (!visible(el) || el.closest('td, th')) return;
    const t = (el.innerText || '').trim();
    if (/^[—–-]$/.test(t) || /^[—–-]\s*(€|%|h)?$/.test(t)) add('cifra_guion', `cifra principal «${t}»`, el);
  });

  // ---- desborde horizontal
  const sw = document.documentElement.scrollWidth;
  if (sw > W + 1) {
    const culpables = [];
    document.querySelectorAll('body *').forEach(el => {
      if (culpables.length > 400) return;
      const r = el.getBoundingClientRect();
      if (r.right <= W + 1 || r.width === 0) return;
      if (el.closest('nav.side') && !document.querySelector('.app.menu-abierto') && W < 900) return;
      for (let a = el.parentElement; a && a !== document.body; a = a.parentElement) {
        const ox = getComputedStyle(a).overflowX;
        if (ox === 'auto' || ox === 'scroll' || ox === 'hidden' || ox === 'clip') return;
      }
      culpables.push(el);
    });
    const hojas = culpables.filter(el => !culpables.some(o => o !== el && el.contains(o))).slice(0, 3);
    add('desborde', `la página mide ${sw}px en ${W}px` + (hojas.length ? ` · culpable: ${hojas.map(selDe).join(' | ')}` : ''), hojas[0] || null);
  }

  // ---- letra < 12 px
  const peq = new Map();
  for (const [el] of conTexto) {
    const fs = parseFloat(getComputedStyle(el).fontSize);
    if (fs < 11.95 && enPantalla(el.getBoundingClientRect())) {
      const k = selDe(el) + '|' + fs;
      if (!peq.has(k)) peq.set(k, [el, fs, (el.innerText || '').trim().slice(0, 40)]);
    }
  }
  for (const [, [el, fs, t]] of peq) add('texto_pequeno', `${fs}px «${t}»`, el);

  // ---- zonas de toque < 32 px (solo a 390)
  if (W <= 500) {
    const vis = new Set();
    document.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea, summary, [role=tab], [role=button], [role=menuitem], [tabindex="0"]').forEach(el => {
      if (!visible(el)) return;
      let r = el.getBoundingClientRect();
      if (!enPantalla(r)) return;
      // V2-E (39b ajuste 2): una casilla dentro de una etiqueta se pulsa por toda la etiqueta: se mide la etiqueta
      if (el.tagName === 'INPUT' && /checkbox|radio/.test(el.type) && el.closest('label')) {
        const lr = el.closest('label').getBoundingClientRect(); if (lr.width >= 32 && lr.height >= 32) return; r = lr; }
      if (r.width >= 32 && r.height >= 32) return;
      // enlaces dentro de una frase: excepción de WCAG 2.5.8
      if (el.tagName === 'A' && getComputedStyle(el).display === 'inline') {
        const p = el.parentElement; if (p && (p.innerText || '').trim().length > (el.innerText || '').trim().length + 3) return;
      }
      const k = selDe(el) + '|' + Math.round(r.width) + 'x' + Math.round(r.height);
      if (vis.has(k)) return; vis.add(k);
      add('toque_pequeno', `${Math.round(r.width)}×${Math.round(r.height)} px «${((el.innerText || el.getAttribute('aria-label') || el.value || '').trim()).slice(0, 30)}»`, el);
    });
  }

  // ---- imágenes rotas
  document.querySelectorAll('img').forEach(img => {
    if (img.complete && img.naturalWidth === 0 && visible(img)) add('imagen_rota', `img ${(img.getAttribute('src') || '').slice(0, 90)}`, img);
  });

  // ---- enlaces vacíos, sin nombre o a rutas que no existen
  document.querySelectorAll('a, button').forEach(el => {
    if (!visible(el)) return;
    const nombre = ((el.innerText || '').trim() || el.getAttribute('aria-label') || el.getAttribute('title') || (el.querySelector('img[alt]')?.alt) || '').trim();
    if (!nombre) add('enlace_vacio', `${el.tagName.toLowerCase()} sin texto ni etiqueta`, el);
    if (el.tagName === 'A') {
      const href = el.getAttribute('href');
      if (href === null || href === '' || href === '#') add('enlace_vacio', `enlace sin destino «${nombre.slice(0, 40)}» href=${JSON.stringify(href)}`, el);
      else if (href.startsWith('#/')) {
        const id = href.slice(2).split(/[/?]/)[0];
        if (id && !opts.modulos.includes(id)) add('enlace_ruta_inexistente', `${href.slice(0, 80)} «${nombre.slice(0, 40)}»`, el);
      }
    }
  });

  // ---- solapes de texto (cajas de texto que se pisan)
  const cajas = [];
  for (const [el, nodos] of conTexto.slice(0, 1800)) {
    if (el.closest('.menu-flot, [role=tooltip], .velo')) continue;
    // V2-E (39b ajuste 1): una caja por renglón (getClientRects), no la unión de todo el trozo: un <span> en línea que
    // parte en dos renglones ya no «choca» con lo que tiene al lado (183 falsos en v1).
    const rg = document.createRange();
    let rs = [];
    for (const n of nodos) { rg.selectNodeContents(n); for (const b of rg.getClientRects()) if (b.width > 1 && b.height > 1) rs.push({ l: b.left, t: b.top, r: b.right, b: b.bottom }); }
    if (!rs.length) continue;
    for (let a = el, i = 0; a && a !== document.body && i < 8; a = a.parentElement, i++) {
      const cs = getComputedStyle(a);
      if (cs.overflowX !== 'visible' || cs.overflowY !== 'visible') { const ar = a.getBoundingClientRect();
        rs = rs.map(r => ({ l: Math.max(r.l, ar.left), t: Math.max(r.t, ar.top), r: Math.min(r.r, ar.right), b: Math.min(r.b, ar.bottom) })); }
    }
    rs = rs.filter(r => r.r - r.l >= 2 && r.b - r.t >= 2 && r.r >= 0 && r.l <= W);
    if (rs.length) cajas.push([el, rs]);
    // columna estrecha (lo que antes salía como solape en la cabecera de la ficha): < 60 px de ancho y más de 3 renglones a 390
    if (W <= 420 && rs.length > 3 && Math.max(...rs.map(r => r.r)) - Math.min(...rs.map(r => r.l)) < 60 && (el.innerText || '').trim().split(/\s+/).length > 3)
      add('columna_estrecha', `«${(el.innerText || '').trim().slice(0, 40)}» en ${Math.round(Math.max(...rs.map(r => r.r)) - Math.min(...rs.map(r => r.l)))} px · ${rs.length} renglones`, el);
  }
  const solapes = new Set();
  for (let i = 0; i < cajas.length; i++) {
    const [ea, ra] = cajas[i];
    for (let j = i + 1; j < cajas.length; j++) {
      const [eb, rb] = cajas[j];
      if (ea.contains(eb) || eb.contains(ea)) continue;
      let peor = 0;
      for (const a of ra) for (const b of rb) {
        const iw = Math.min(a.r, b.r) - Math.max(a.l, b.l), ih = Math.min(a.b, b.b) - Math.max(a.t, b.t);
        if (iw <= 2 || ih <= 2) continue;
        const area = iw * ih, menor = Math.min((a.r - a.l) * (a.b - a.t), (b.r - b.l) * (b.b - b.t));
        if (area >= 20 && area >= 0.25 * menor) peor = Math.max(peor, area);
      }
      if (!peor) continue;
      const k = selDe(ea) + ' ⟂ ' + selDe(eb);
      if (solapes.has(k)) continue; solapes.add(k);
      add('solape', `«${(ea.innerText || '').trim().slice(0, 30)}» pisa «${(eb.innerText || '').trim().slice(0, 30)}» · ${selDe(eb)}`, ea);
      if (solapes.size > 25) break;
    }
    if (solapes.size > 25) break;
  }

  // ---- contraste < 4,5:1 (3:1 en letra grande)
  const rgb = s => { const m = s.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(/[ ,/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; };
  const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const mezcla = (arriba, abajo) => { const a = arriba[3]; return [arriba[0] * a + abajo[0] * (1 - a), arriba[1] * a + abajo[1] * (1 - a), arriba[2] * a + abajo[2] * (1 - a), 1]; };
  function fondo(el) {
    const capas = [];
    for (let a = el; a; a = a.parentElement) {
      const cs = getComputedStyle(a);
      if (cs.backgroundImage && cs.backgroundImage !== 'none' && !/url\(/.test(cs.backgroundImage) === false) return null;
      if (cs.backgroundImage && /gradient/.test(cs.backgroundImage)) return null;
      const c = rgb(cs.backgroundColor);
      if (c && c[3] > 0) { capas.push(c); if (c[3] >= 1) break; }
    }
    let f = [255, 255, 255, 1];
    for (let i = capas.length - 1; i >= 0; i--) f = mezcla(capas[i], f);
    return f;
  }
  const contr = new Map();
  for (const [el] of conTexto.slice(0, 2500)) {
    const r = el.getBoundingClientRect(); if (!enPantalla(r)) continue;
    if (el.closest('button:disabled, [aria-disabled="true"], input:disabled, select:disabled')) continue;
    const cs = getComputedStyle(el);
    let col = rgb(cs.color); if (!col) continue;
    const bg = fondo(el); if (!bg) continue;
    let op = 1; for (let a = el; a; a = a.parentElement) op *= parseFloat(getComputedStyle(a).opacity) || 1;
    col = mezcla([col[0], col[1], col[2], col[3] * op], bg);
    const L1 = lum(col), L2 = lum(bg), ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const fs = parseFloat(cs.fontSize), grande = fs >= 24 || (fs >= 18.66 && parseInt(cs.fontWeight) >= 700);
    const min = grande ? 3 : 4.5;
    if (ratio < min - 0.01) {
      const k = selDe(el) + '|' + cs.color + '|' + ratio.toFixed(2);
      if (!contr.has(k)) contr.set(k, [el, ratio, (el.innerText || '').trim().slice(0, 30), cs.color]);
    }
  }
  for (const [, [el, ratio, t, c]] of [...contr].slice(0, 40)) add('contraste', `${ratio.toFixed(2)}:1 «${t}» (${c})`, el);

  return { fallos, alto: document.documentElement.scrollHeight, titulo: (document.querySelector('#titulo')?.textContent || '').trim(),
           sinPermiso: /no es de tu puesto|no puedes ver|sin permiso/i.test(document.querySelector('#main')?.innerText || ''),
           vacio: !(document.querySelector('#main')?.innerText || '').trim() };
}
"""

# V3a (Tomás, 3-oct: «el desplegable se queda a medias»): abre cada desplegable de la pantalla (selector de cliente o
# persona, filtros, «Más», periodo, «⋯» con <details>, menú del avatar), mide su caja y lo vuelve a cerrar con Esc.
# Fallos: desplegable_recortado (la caja visible no cabe entera en la ventana, o lo de encima en su caja no es suyo:
# lo corta un overflow o lo tapa otro elemento), desplegable_sin_scroll (más alto que su sitio y sin scroll dentro) y
# desplegable_no_cierra (Esc y pulsar fuera no lo cierran). No pulsa ninguna opción.
MIRAR_DESPLEGABLES = r"""
async (tope) => {
  const esperar = ms => new Promise(r => setTimeout(r, ms));
  const W = document.documentElement.clientWidth, H = innerHeight, fallos = [];
  const SEL_CAPA = '.capa-flot, .menu-flot, .selcli > .pop, #yo-pop';
  const visible = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && !el.hidden && el.checkVisibility(); };
  const abiertas = () => [...document.querySelectorAll(SEL_CAPA)].filter(visible);
  const etq = b => (b.innerText || b.getAttribute('aria-label') || b.title || '').trim().replace(/\s+/g, ' ').slice(0, 60);
  const selDe = el => { const p = []; let x = el; for (let i = 0; i < 3 && x && x !== document.body; i++, x = x.parentElement) p.unshift(x.tagName.toLowerCase() + (x.id ? '#' + x.id : '') + ([...x.classList].slice(0, 2).map(c => '.' + c).join(''))); return p.join(' > '); };
  const disparadores = [...document.querySelectorAll('#main button[aria-haspopup]:not([aria-haspopup="dialog"]), #main .sel-bt, #main details > summary, #yo-btn')]
    .filter(b => !b.disabled && visible(b) && (!b.matches('details > summary') || b.parentElement.querySelector(':scope > .menu-flot')))
    .slice(0, tope || 8);
  for (const b of disparadores) {
    if (!b.isConnected) continue;
    const antes = new Set(abiertas());
    b.scrollIntoView({ block: 'center' }); await esperar(40);
    b.click(); await esperar(260);
    const nuevas = abiertas().filter(x => !antes.has(x));
    const el = nuevas[nuevas.length - 1];
    if (!el) continue;
    const r = el.getBoundingClientRect();
    const fuera = r.left < -0.5 || r.top < -0.5 || r.right > W + 0.5 || r.bottom > H + 0.5;
    let tapados = 0, total = 0;
    for (let a = 1; a <= 4; a++) for (let c = 1; c <= 4; c++) {
      const x = r.left + (r.width * a) / 5, y = r.top + (r.height * c) / 5;
      if (x < 0 || y < 0 || x > W || y > H) continue;
      total++; const t = document.elementFromPoint(x, y); if (!t || !(el === t || el.contains(t))) tapados++;
    }
    if (fuera || tapados) fallos.push({ tipo: 'desplegable_recortado', detalle: `«${etq(b)}» · caja ${Math.round(r.left)},${Math.round(r.top)} ${Math.round(r.width)}×${Math.round(r.height)} en ${W}×${H}${tapados ? ` · ${tapados} de ${total} puntos tapados o cortados` : ''}`, sel: selDe(el), zona: 'otra' });
    const cs = getComputedStyle(el);
    if (el.scrollHeight > el.clientHeight + 2 && !/(auto|scroll)/.test(cs.overflowY) && !el.querySelector('.ls'))
      fallos.push({ tipo: 'desplegable_sin_scroll', detalle: `«${etq(b)}» · ${el.scrollHeight} px de contenido en ${el.clientHeight} px sin scroll`, sel: selDe(el), zona: 'otra' });
    (document.activeElement || document.body).dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }));
    await esperar(140);
    if (el.isConnected && visible(el)) {
      document.body.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true })); document.body.click(); await esperar(140);
      if (b.matches('details > summary')) b.parentElement.open = false;
      if (el.isConnected && visible(el)) fallos.push({ tipo: 'desplegable_no_cierra', detalle: `«${etq(b)}» sigue abierto tras Esc y pulsar fuera`, sel: selDe(el), zona: 'otra' });
    }
  }
  window.scrollTo(0, 0);
  return fallos;
}"""

LISTO = """() => { const m = document.querySelector('#main'); if (!m) return false;
  if (document.querySelector('#titulo')?.textContent === 'Cargando…') return false;
  if (m.querySelector('.esqueleto, [aria-busy="true"]')) return false;
  return (m.innerText || '').trim().length > 0 || m.querySelector('img, svg, canvas, table') !== null; }"""


def slug(s):
    s = re.sub(r"[^\w\-~.]+", "_", s, flags=re.UNICODE).strip("_")
    return s[:110] or "inicio"


# ------------------------------------------------------------------ trabajo por persona (proceso aparte)
def barrer_persona(pid, vuelta, salida_dir, modulos):
    from playwright.sync_api import sync_playwright
    out = Path(salida_dir) / pid
    out.mkdir(parents=True, exist_ok=True)
    estados = []
    aviso_disco = False
    ses = json.loads(urllib.request.urlopen(f"{BASE}/api/sesion?yo={pid}", timeout=30).read())
    clientes = ses["datos"]["clientes"]
    cartera = [c for c in ses["datos"].get("carteraIds", []) if any(x["id"] == c and x.get("detalle") for x in clientes)]
    con_detalle = [c["id"] for c in clientes if c.get("detalle")]
    propios = (cartera or con_detalle)[:2]
    ajenos = [c["id"] for c in clientes if not c.get("detalle")]
    ajeno_visible = False
    if not ajenos:
        ajenos = [c["id"] for c in clientes if c["id"] not in set(ses["datos"].get("carteraIds", []))]
        ajeno_visible = True
    ajeno = ajenos[0] if ajenos else None
    ids_clientes = {c["id"] for c in clientes}

    with sync_playwright() as pw:
        nav = pw.chromium.launch(headless=True)
        ctx = nav.new_context(viewport={"width": 1440, "height": 900}, locale="es-ES", timezone_id="Europe/Madrid")
        pag = ctx.new_page()
        actual = {"ruta": "(entrada)", "esperado403": False}
        consola, red = [], []
        pag.on("console", lambda m: consola.append({"ruta": actual["ruta"], "tipo": m.type, "texto": m.text,
                                                    "url": (m.location or {}).get("url", "")}) if m.type in ("error", "warning") else None)
        pag.on("pageerror", lambda e: consola.append({"ruta": actual["ruta"], "tipo": "pageerror", "texto": str(e)[:400],
                                                      "url": (getattr(e, "stack", "") or "")[:300]}))
        pag.on("response", lambda r: red.append({"ruta": actual["ruta"], "url": r.url, "status": r.status,
                                                 "esperado": actual["esperado403"]}) if r.status >= 400 else None)
        pag.on("requestfailed", lambda r: red.append({"ruta": actual["ruta"], "url": r.url, "status": 0, "fallo": r.failure,
                                                      "esperado": actual["esperado403"]}))

        t0 = time.time()
        pag.goto(f"{BASE}/?yo={pid}#/", wait_until="domcontentloaded")
        try:
            pag.wait_for_function(LISTO, timeout=15000, polling=50)
        except Exception:
            pass
        entrada_ms = int((time.time() - t0) * 1000)
        menu = pag.evaluate("() => [...document.querySelectorAll('#nav a[data-id]')].map(a => a.dataset.id)")
        inicio = pag.evaluate("() => location.hash")

        def esperar_listo(timeout=10000):
            t = time.time()
            try:
                pag.wait_for_function(LISTO, timeout=timeout, polling=40)
                ok = True
            except Exception:
                ok = False
            pag.wait_for_timeout(120)
            return int((time.time() - t) * 1000), ok

        def ir(ruta, esperado403=False):
            actual["ruta"], actual["esperado403"] = ruta, esperado403
            pag.set_viewport_size({"width": 1440, "height": 900})
            t = time.time()
            pag.evaluate("r => { if (location.hash === '#/' + r) { location.hash = '#/__barrido'; } location.hash = '#/' + r; }", ruta)
            ms, ok = esperar_listo()
            return int((time.time() - t) * 1000), ok

        def foto_y_mirar(ruta, etiqueta, carga_ms=None, cargo=True, anchos=ANCHOS, esperado403=False):
            nonlocal aviso_disco
            for ancho, alto in anchos:
                if libre() < MIN_LIBRE:
                    aviso_disco = True
                    return
                pag.set_viewport_size({"width": ancho, "height": alto})
                pag.wait_for_timeout(220)
                n_cons, n_red = len(consola), len(red)
                try:
                    r = pag.evaluate(MIRAR, {"modulos": modulos})
                except Exception as e:
                    r = {"fallos": [{"tipo": "barrido_no_pudo_mirar", "detalle": str(e)[:200], "sel": "", "zona": ""}], "alto": 900, "titulo": "", "sinPermiso": False, "vacio": False}
                nombre = f"{slug(etiqueta)}_{ancho}.jpg"
                ruta_cap = out / nombre
                try:
                    alto_doc = min(int(r.get("alto") or alto), MAX_ALTO_CAPTURA)
                    pag.screenshot(path=str(ruta_cap), type="jpeg", quality=70, full_page=True,
                                   clip={"x": 0, "y": 0, "width": ancho, "height": max(alto_doc, alto)})
                except Exception as e:
                    r["fallos"].append({"tipo": "barrido_sin_captura", "detalle": str(e)[:160], "sel": "", "zona": ""})
                fallos = r["fallos"]
                if cargo and not esperado403 and not r.get("sinPermiso"):   # V3a: desplegables enteros y por encima de todo
                    try:
                        fallos += pag.evaluate(MIRAR_DESPLEGABLES, 8)
                    except Exception as e:
                        fallos.append({"tipo": "barrido_no_pudo_mirar", "detalle": f"desplegables: {str(e)[:160]}", "sel": "", "zona": ""})
                    if pag.evaluate("() => location.hash") != f"#/{ruta}" and not ruta.startswith("__"):
                        pag.evaluate("r => { location.hash = '#/' + r; }", ruta)
                        pag.wait_for_timeout(300)
                if r.get("vacio"):
                    fallos.append({"tipo": "pantalla_vacia", "detalle": "el contenido principal está vacío", "sel": "#main", "zona": "main"})
                if ancho == 1440 and carga_ms is not None:
                    if not cargo:
                        fallos.append({"tipo": "no_termina_de_cargar", "detalle": f"sin contenido útil tras {carga_ms} ms", "sel": "#main", "zona": "main"})
                    elif carga_ms > 1000:
                        fallos.append({"tipo": "carga_lenta", "detalle": f"{carga_ms} ms hasta contenido (local)", "sel": "#main", "zona": "main"})
                estados.append({"persona": pid, "ruta": ruta, "estado": etiqueta, "ancho": ancho, "carga_ms": carga_ms if ancho == 1440 else None,
                                "captura": str(ruta_cap.relative_to(APP)), "titulo": r.get("titulo"), "sinPermiso": r.get("sinPermiso"),
                                "esperado403": esperado403, "fallos": fallos})
            pag.set_viewport_size({"width": 1440, "height": 900})
            pag.wait_for_timeout(120)

        def pestanas(ruta, etq_base):
            """Pulsa cada pestaña (role=tab) de los 2 primeros grupos de pestañas del contenido."""
            grupos = pag.evaluate("""() => [...document.querySelectorAll('#main [role=tablist]')].slice(0, 2).map((tl, i) =>
                ({ i, etiqueta: tl.getAttribute('aria-label') || '', tabs: [...tl.querySelectorAll('[role=tab]')].map(b => (b.innerText || b.getAttribute('aria-label') || '').trim().split('\\n')[0]).filter(Boolean),
                   activa: (tl.querySelector('[role=tab][aria-selected=true]')?.innerText || '').trim().split('\\n')[0],
                   mas: !!tl.parentElement?.querySelector('.menu-mas button, [aria-label="Más pestañas"]') }))""")
            for g in grupos:
                tabs = [t for t in g["tabs"] if t != g["activa"]][:MAX_PESTANAS]
                for t in tabs:
                    if aviso_disco:
                        return
                    hash_antes = pag.evaluate("() => location.hash")
                    ok = pag.evaluate("""([gi, txt]) => { const tl = [...document.querySelectorAll('#main [role=tablist]')][gi]; if (!tl) return false;
                        const b = [...tl.querySelectorAll('[role=tab]')].find(x => (x.innerText || x.getAttribute('aria-label') || '').trim().split('\\n')[0] === txt);
                        if (!b) return false; b.scrollIntoView({block: 'nearest'}); b.click(); return true; }""", [g["i"], t])
                    if not ok:
                        continue
                    actual["ruta"] = f"{ruta} › {t}"
                    ms, cargo = esperar_listo()
                    foto_y_mirar(ruta, f"{etq_base}~t-{t}", carga_ms=ms, cargo=cargo, anchos=[ANCHO_ANCHO, ANCHO_MOVIL])
                    # si la pestaña cambió la ruta, se vuelve a la pantalla base
                    if pag.evaluate("() => location.hash") != hash_antes:
                        pag.evaluate("h => { location.hash = h; }", hash_antes)
                        esperar_listo()
                # pestañas escondidas en «Más (n)»
                if g["mas"]:
                    abierto = pag.evaluate("""gi => { const tl = [...document.querySelectorAll('#main [role=tablist]')][gi]; const b = tl?.parentElement?.querySelector('.menu-mas button, [aria-label="Más pestañas"]');
                        if (!b) return false; b.click(); return true; }""", g["i"])
                    if abierto:
                        pag.wait_for_timeout(250)
                        foto_y_mirar(ruta, f"{etq_base}~mas-pestanas", anchos=[ANCHO_ANCHO])
                        pag.keyboard.press("Escape")

        def periodo(ruta, etq_base):
            hay = pag.evaluate("() => { const b = document.querySelector('#barra-ctx'); return !!b && !b.hidden && !!b.querySelector('.segm button'); }")
            if not hay:
                return
            cambiado = pag.evaluate("""() => { const bs = [...document.querySelectorAll('#barra-ctx .segm:not(.segm-comp) > button')];
                const b = bs.find(x => x.getAttribute('aria-pressed') !== 'true'); if (!b) return null; b.click(); return (b.innerText || '').trim(); }""")
            if cambiado:
                actual["ruta"] = f"{ruta} › periodo {cambiado}"
                ms, cargo = esperar_listo()
                foto_y_mirar(ruta, f"{etq_base}~periodo-{cambiado}", carga_ms=ms, cargo=cargo, anchos=[ANCHO_ANCHO, ANCHO_MOVIL])
            # menú «Más» del periodo
            abierto = pag.evaluate("() => { const b = document.querySelector('#barra-ctx .periodo-mas > button'); if (!b) return false; b.click(); return true; }")
            if abierto:
                pag.wait_for_timeout(250)
                foto_y_mirar(ruta, f"{etq_base}~periodo-mas", anchos=[ANCHO_ANCHO, ANCHO_MOVIL])
                pag.keyboard.press("Escape")
                pag.mouse.click(5, 5)

        def menus_mas(ruta, etq_base):
            n = pag.evaluate("() => [...document.querySelectorAll('#main .menu-mas > button, #main [aria-haspopup=menu]')].filter(b => !b.closest('[role=tablist]') && b.offsetParent).length")
            for i in range(min(n, 2)):
                ok = pag.evaluate("""i => { const b = [...document.querySelectorAll('#main .menu-mas > button, #main [aria-haspopup=menu]')].filter(b => !b.closest('[role=tablist]') && b.offsetParent)[i];
                    if (!b) return false; b.click(); return true; }""", i)
                if ok:
                    pag.wait_for_timeout(250)
                    foto_y_mirar(ruta, f"{etq_base}~mas-{i + 1}", anchos=[ANCHO_ANCHO, ANCHO_MOVIL])
                    pag.keyboard.press("Escape")
                    pag.mouse.click(5, 5)

        def plegables(ruta, etq_base):
            n = pag.evaluate("""() => { const ds = [...document.querySelectorAll('#main details:not([open])')].filter(d => !d.parentElement.closest('details') && d.offsetParent).slice(0, 8);
                ds.forEach(d => d.open = true); return ds.length; }""")
            if n:
                pag.wait_for_timeout(250)
                foto_y_mirar(ruta, f"{etq_base}~plegables", anchos=[ANCHO_ANCHO, ANCHO_MOVIL])

        def pantalla(ruta, esperado403=False, completa=True):
            if aviso_disco:
                return
            ms, cargo = ir(ruta, esperado403)
            etq = ruta.replace("/", "__")
            foto_y_mirar(ruta, etq, carga_ms=ms, cargo=cargo, esperado403=esperado403)
            if not completa:
                return
            subrutas = pag.evaluate("""m => [...new Set([...document.querySelectorAll('#main a[href^="#/' + m + '/"]')].map(a => a.getAttribute('href').slice(2).split('?')[0]))]""", ruta.split("/")[0])
            pestanas(ruta, etq)
            ir(ruta)
            periodo(ruta, etq)
            ir(ruta)
            menus_mas(ruta, etq)
            plegables(ruta, etq)
            return subrutas

        # 1 · cada ruta de su menú, con sus sub-rutas del mismo módulo
        hechas = set()
        for mid in menu:
            # la ficha sin cliente abre la primera propia: se recorre entera en el paso 2
            subs = pantalla(mid, completa=not (mid == 'ficha' and propios)) or []
            hechas.add(mid)
            formas = {}
            for s in subs:
                partes = s.split("/")
                forma = "/".join("{c}" if p in ids_clientes else ("{id}" if re.search(r"\d", p) and len(p) > 6 else p) for p in partes)
                formas.setdefault(forma, s)
            if mid == "ficha":
                continue
            for forma, s in list(formas.items())[:MAX_SUBRUTAS]:
                if s not in hechas:
                    hechas.add(s)
                    pantalla(s)
        # 2 · fichas: 2 propias y 1 ajena
        if "ficha" in menu:
            for c in propios:
                if f"ficha/{c}" not in hechas:
                    pantalla(f"ficha/{c}")
            if ajeno:
                pantalla(f"ficha/{ajeno}", esperado403=not ajeno_visible)
        elif ajeno:
            pantalla(f"ficha/{ajeno}", esperado403=True, completa=False)
        ctx.close()
        nav.close()

    # reparte consola y red por pantalla
    resumen = {"persona": pid, "menu": menu, "inicio": inicio, "entrada_ms": entrada_ms, "propios": propios, "ajeno": ajeno,
               "ajeno_visible_por_puesto": ajeno_visible, "aviso_disco": aviso_disco, "consola": consola, "red": red, "estados": estados}
    (out / "_resultado.json").write_text(json.dumps(resumen, ensure_ascii=False))
    return pid, len(estados), aviso_disco


# ------------------------------------------------------------------ servidor propio
def arrancar_servidor(tmp):
    db = Path(tmp) / "barrido.db"
    shutil.copy2(APP / "local.db", db)
    log = open(Path(tmp) / "servir.log", "w")
    env = dict(os.environ, RO_DB=str(db))
    p = subprocess.Popen([sys.executable, "servir.py", "--bind", "127.0.0.1", "--puerto", str(PUERTO)], cwd=str(APP), env=env,
                         stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(80):
        try:
            urllib.request.urlopen(f"{BASE}/api/elegir", timeout=2)
            return p
        except Exception:
            time.sleep(0.25)
    p.terminate()
    raise SystemExit(f"El servidor no arranca; mira {tmp}/servir.log")


def modulos_existentes():
    txt = (APP / "modulos" / "indice.js").read_text()
    ids = re.findall(r"\{\s*id:\s*'([\w\-]+)'", txt)
    ficheros = dict(re.findall(r"id:\s*'([\w\-]+)'[^}]*?fichero:\s*'\./([\w\-.]+)'", txt, flags=re.S))
    return ids, ficheros


# ------------------------------------------------------------------ dueño probable
def dueno(f, ruta, ficheros):
    mod = ruta.split("/")[0].split(" ")[0]
    fich = f"modulos/{ficheros.get(mod, mod.replace('-', '_') + '.js')}"
    zona = f.get("zona", "")
    sel = f.get("sel", "")
    t = f["tipo"]
    if t in ("consola", "error_pagina"):
        m = re.search(r"(modulos/[\w\-]+\.js|app\.js|componentes\.js|carcasa\.js|datos\.js|permisos\.js)", f.get("url", "") + " " + f["detalle"])
        return m.group(1) if m else fich
    if t == "http":
        u = f["detalle"]
        m = re.search(r"/api/modulo/([\w\-]+)/", u)
        if m:
            return f"{fich} · servir.py/reglas_permisos.json (datos_de_modulo {m.group(1)})"
        if "/api/" in u:
            return f"servir.py ({u.split('/api/')[1].split('?')[0].split(' ')[0]}) · {fich}"
        return fich
    if zona == "periodo":
        return "componentes.js (selector de periodo) · estilos.css"
    if zona in ("menu", "cabecera"):
        return "app.js · index.html · estilos.css (carcasa)"
    if zona == "otra":
        return "app.js · estilos.css (carcasa/flotantes)"
    if re.search(r"\b(pestanas|tiles|tile|chip|fresc|vacio-g|estado-vacio|menu-mas|periodo|tabla|tbl)\b", sel) and t in ("texto_pequeno", "contraste", "toque_pequeno"):
        return f"{fich} · componentes.js/estilos.css"
    return fich


ETIQUETAS = {
    "consola": "Error de consola", "error_pagina": "Error de página (JS sin capturar)", "http": "Respuesta 4xx/5xx inesperada",
    "texto_null": "Texto «null»", "texto_undefined": "Texto «undefined»", "texto_NaN": "Texto «NaN»", "texto_importe": "Texto «[importe]»",
    "texto_Infinity": "Texto «Infinity»", "texto_invalid_date": "Texto «Invalid Date»", "texto_object": "Texto «[object …]»",
    "Jessi": "«Jessi/Jessica» en vez de «Yessica»", "error_pintado": "Error pintado en pantalla", "codigo_interno": "Código interno o nombre de fichero visible",
    "cifra_guion": "«—» suelto como cifra principal", "desborde": "Desborde horizontal", "texto_pequeno": "Letra < 12 px",
    "desplegable_recortado": "Desplegable recortado o tapado", "desplegable_sin_scroll": "Desplegable sin scroll dentro",
    "desplegable_no_cierra": "Desplegable que no se cierra con Esc ni pulsando fuera",
    "toque_pequeno": "Zona de toque < 32 px (390)", "imagen_rota": "Imagen rota", "enlace_vacio": "Enlace/botón vacío o sin destino",
    "enlace_ruta_inexistente": "Enlace a una ruta que no existe", "carga_lenta": "Carga > 1 s hasta contenido", "no_termina_de_cargar": "No termina de cargar (10 s)",
    "solape": "Textos que se pisan", "contraste": "Contraste < 4,5:1", "pantalla_vacia": "Pantalla vacía",
    "barrido_no_pudo_mirar": "El barrido no pudo mirar", "barrido_sin_captura": "Sin captura",
    "plural_1": "Plural con «1» («1 usuarios»)", "columna_estrecha": "Columna de texto estrecha (< 60 px, 390)",
}


# ------------------------------------------------------------------ informe
def informe(vuelta, salida_dir, ficheros, inicio_txt, duracion_s):
    salida_dir = Path(salida_dir)
    personas = []
    for f in sorted(salida_dir.glob("*/_resultado.json")):
        personas.append(json.loads(f.read_text()))
    fallos = []   # planos
    estados_tot = 0
    for p in personas:
        for e in p["estados"]:
            estados_tot += 1
            for f in e["fallos"]:
                fallos.append({**f, "persona": p["persona"], "ruta": e["ruta"], "estado": e["estado"], "ancho": e["ancho"], "captura": e["captura"]})
        # consola y red: una vez por (ruta, texto)
        capt = {}
        for e in p["estados"]:
            capt.setdefault(e["ruta"], e["captura"])
        visto = set()
        for c in p["consola"]:
            base = c["ruta"].split(" › ")[0]
            k = (base, c["texto"][:200], c["tipo"])
            if k in visto:
                continue
            visto.add(k)
            if c["tipo"] == "warning":
                continue
            fallos.append({"tipo": "error_pagina" if c["tipo"] == "pageerror" else "consola", "detalle": c["texto"][:300], "url": c.get("url", ""),
                           "sel": "", "zona": "", "persona": p["persona"], "ruta": c["ruta"], "estado": "", "ancho": 1440, "captura": capt.get(base, "")})
        for r in p["red"]:
            base = r["ruta"].split(" › ")[0]
            if r.get("esperado") and r["status"] in (401, 403, 404):
                continue
            if r["status"] == 0 and ("fonts.g" in r["url"] or "ERR_ABORTED" in str(r.get("fallo"))):
                continue
            k = (base, r["url"], r["status"])
            if k in visto:
                continue
            visto.add(k)
            u = r["url"].replace(BASE, "")
            fallos.append({"tipo": "http", "detalle": f"{r['status'] or 'fallo de red'} {u[:160]}" + (f" ({r.get('fallo')})" if r.get("fallo") else ""),
                           "sel": "", "zona": "", "persona": p["persona"], "ruta": r["ruta"], "estado": "", "ancho": 1440, "captura": capt.get(base, "")})
    for f in fallos:
        f["dueno"] = dueno(f, f["ruta"], ficheros)

    por_tipo = Counter(f["tipo"] for f in fallos)
    capturas = sum(1 for p in personas for e in p["estados"])
    rutas_unicas = {(p["persona"], e["ruta"]) for p in personas for e in p["estados"]}
    cargas = [e["carga_ms"] for p in personas for e in p["estados"] if e.get("carga_ms") is not None]
    aviso_disco = any(p.get("aviso_disco") for p in personas)

    res = {"vuelta": vuelta, "inicio": inicio_txt, "duracion_s": duracion_s, "personas": len(personas), "pantallas_persona_ruta": len(rutas_unicas),
           "estados_capturados": capturas, "fallos_total": len(fallos), "por_tipo": dict(por_tipo.most_common()), "aviso_disco": aviso_disco,
           "carga_ms": {"mediana": sorted(cargas)[len(cargas) // 2] if cargas else None, "max": max(cargas) if cargas else None, "n": len(cargas)},
           "entrada_ms": {p["persona"]: p["entrada_ms"] for p in personas},
           "fallos": fallos,
           "personas_detalle": [{k: p[k] for k in ("persona", "menu", "inicio", "entrada_ms", "propios", "ajeno", "ajeno_visible_por_puesto")} for p in personas]}
    (salida_dir / "resultado.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))

    # ---------- markdown
    L = []
    L.append(f"# 39 · Barrido total de la app · vuelta {vuelta}")
    L.append("")
    L.append(f"**{inicio_txt}** · `30_APP_PROTOTIPO/despliegue/barrido_total.py --vuelta {vuelta}` · servidor propio en 127.0.0.1:{PUERTO} con copia de `local.db` · "
             f"Chromium sin ventana · {duracion_s // 60} min. Solo lee: no se ha editado nada de la app ni se ha pulsado ninguna acción.")
    L.append("")
    if aviso_disco:
        L.append("> ⚠️ **El barrido paró antes de acabar: el disco bajó de 1,5 GB libres.** Las cifras de abajo son parciales.")
        L.append("")
    L.append("## Totales")
    L.append("")
    L.append(f"| | |\n|---|---|\n| Personas recorridas | {len(personas)} |\n| Pantallas (persona × ruta, con sub-rutas y fichas) | {len(rutas_unicas)} |\n"
             f"| Estados capturados (pantalla × pestaña/periodo/menú × ancho) | {capturas} |\n| **Fallos registrados** | **{len(fallos)}** |\n"
             f"| Fallos distintos (tipo + dueño + detalle) | {len({(f['tipo'], f['dueno'], _clave_det(f)) for f in fallos})} |\n"
             f"| Carga hasta contenido (local, 1440) | mediana {res['carga_ms']['mediana']} ms · máx. {res['carga_ms']['max']} ms |\n"
             f"| Capturas | `30_APP_PROTOTIPO/capturas/_barrido/{vuelta}/<persona>/<ruta>_<ancho>.jpg` |\n"
             f"| JSON máquina | `30_APP_PROTOTIPO/capturas/_barrido/{vuelta}/resultado.json` |")
    L.append("")
    L.append("### Fallos por tipo")
    L.append("")
    L.append("| Tipo | Fallos | Personas | Pantallas |\n|---|---:|---:|---:|")
    for t, n in por_tipo.most_common():
        fs = [f for f in fallos if f["tipo"] == t]
        L.append(f"| {ETIQUETAS.get(t, t)} | {n} | {len({f['persona'] for f in fs})} | {len({(f['persona'], f['ruta'].split(' › ')[0]) for f in fs})} |")
    L.append("")
    L.append("### Fallos por dueño probable")
    L.append("")
    L.append("| Fichero dueño | Fallos | Tipos |\n|---|---:|---|")
    por_dueno = defaultdict(list)
    for f in fallos:
        por_dueno[f["dueno"]].append(f)
    for d, fs in sorted(por_dueno.items(), key=lambda x: -len(x[1])):
        L.append(f"| `{d}` | {len(fs)} | {', '.join(f'{ETIQUETAS.get(t, t)} {n}' for t, n in Counter(x['tipo'] for x in fs).most_common(5))} |")
    L.append("")
    L.append("> Cómo leer: «fallo» = una comprobación que no pasa en un estado y un ancho concretos. El mismo defecto de un componente cuenta una vez por pantalla y ancho donde sale; "
             "la lista de abajo los agrupa. Contraste, solapes y toque son detección automática: hay que mirarlos en la captura antes de arreglar. "
             "Los 401/403/404 de la ficha ajena son esperados y no cuentan. La carga se mide en local (no en 4G).")
    L.append("")

    # tabla persona × ruta
    L.append("## Persona × ruta (nº de fallos, sumando anchos, pestañas y estados)")
    L.append("")
    for p in personas:
        cuenta = Counter()
        for f in fallos:
            if f["persona"] == p["persona"]:
                cuenta[f["ruta"].split(" › ")[0]] += 1
        rutas = []
        for e in p["estados"]:
            if e["ruta"] not in rutas:
                rutas.append(e["ruta"])
        tot = sum(cuenta.values())
        L.append(f"<details><summary><b>{p['persona']}</b> · {tot} fallos · {len(rutas)} pantallas · entrada {p['entrada_ms']} ms · inicio {p['inicio']}</summary>")
        L.append("")
        L.append("| Ruta | Fallos | Peores tipos |\n|---|---:|---|")
        for r in rutas:
            tipos = Counter(f["tipo"] for f in fallos if f["persona"] == p["persona"] and f["ruta"].split(" › ")[0] == r)
            L.append(f"| `{r}` | {cuenta.get(r, 0)} | {', '.join(f'{t} {n}' for t, n in tipos.most_common(3))} |")
        L.append("")
        L.append("</details>")
        L.append("")

    # todos los fallos agrupados
    L.append("## Todos los fallos, agrupados por tipo y por dueño")
    L.append("")
    L.append("Cada línea es un fallo distinto (tipo + dueño + detalle normalizado) con cuántas veces sale, en cuántas personas, a qué anchos y hasta 3 capturas de ejemplo.")
    L.append("")
    for t, _ in por_tipo.most_common():
        L.append(f"### {ETIQUETAS.get(t, t)} ({por_tipo[t]})")
        L.append("")
        fs_t = [f for f in fallos if f["tipo"] == t]
        por_d = defaultdict(list)
        for f in fs_t:
            por_d[f["dueno"]].append(f)
        for d, fs in sorted(por_d.items(), key=lambda x: -len(x[1])):
            L.append(f"**`{d}`** · {len(fs)}")
            L.append("")
            grupos = defaultdict(list)
            for f in fs:
                grupos[_clave_det(f) + " ‖ " + (f.get("sel") or "")].append(f)
            for k, g in sorted(grupos.items(), key=lambda x: -len(x[1])):
                anchos = sorted({x["ancho"] for x in g})
                rutas = sorted({x["ruta"].split(" › ")[0] for x in g})
                ej = []
                for x in g:
                    if x["captura"] and x["captura"] not in ej:
                        ej.append(x["captura"])
                    if len(ej) >= 3:
                        break
                det = g[0]["detalle"].replace("|", "\\|")
                sel = (g[0].get("sel") or "").replace("|", "\\|")
                L.append(f"- ×{len(g)} · {len({x['persona'] for x in g})} pers. · {'/'.join(map(str, anchos))} px · {det}"
                         + (f" · `{sel}`" if sel else "")
                         + f" · rutas: {', '.join('`' + r + '`' for r in rutas[:6])}{' …' if len(rutas) > 6 else ''}"
                         + f" · capturas: {', '.join('`' + c.replace('capturas/_barrido/', '') + '`' for c in ej)}")
            L.append("")
    (RAIZ / "39_BARRIDO_TOTAL.md").write_text("\n".join(L))
    return res


def norm(s):
    s = re.sub(r"\d+(\.\d+)?", "#", s or "")
    return s[:160]


def _clave_det(f):
    """V2-E (39b ajuste 3): el toque pequeño se agrupa sin el texto del enlace (53 títulos de tarea = 1 fallo, no 35)."""
    d = norm(f.get("detalle"))
    return re.sub(r"«[^»]*»", "«…»", d) if f.get("tipo") == "toque_pequeno" else d


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vuelta", default="v0")
    ap.add_argument("--personas", default="")
    ap.add_argument("--hilos", type=int, default=6)
    ap.add_argument("--solo-informe", action="store_true")
    ap.add_argument("--puerto", type=int, default=PUERTO, help="puerto del servidor propio en 127.0.0.1 (por defecto 9000)")
    ap.add_argument("--borrar-capturas-de", metavar="VUELTA", default="", help="borra las capturas de esa vuelta (deja sus JSON) y sale")
    a = ap.parse_args()
    if a.borrar_capturas_de:
        antes = libre()
        n, b = borrar_capturas(a.borrar_capturas_de)
        print(f"Borradas {n} capturas de {a.borrar_capturas_de} ({b / 1e9:.2f} GB) · libre {antes / 1e9:.2f} → {libre() / 1e9:.2f} GB · quedan sus resultado.json")
        return
    poner_puerto(a.puerto)
    salida = APP / "capturas" / "_barrido" / a.vuelta
    ids, ficheros = modulos_existentes()
    inicio_txt = datetime.now().strftime("%d-%m-%Y %H:%M")
    if a.solo_informe:
        res = informe(a.vuelta, salida, ficheros, inicio_txt, 0)
        print(json.dumps({k: res[k] for k in ("fallos_total", "por_tipo")}, ensure_ascii=False, indent=1))
        return
    if libre() < MIN_LIBRE:
        raise SystemExit(f"Disco libre {libre() / 1e9:.2f} GB < 1,5 GB: no se arranca.")
    print(f"Disco libre al empezar: {libre() / 1e9:.2f} GB")
    salida.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="barrido_ro_")
    srv = arrancar_servidor(tmp)
    t0 = time.time()
    try:
        personas = [p["id"] for p in json.loads(urllib.request.urlopen(f"{BASE}/api/elegir").read())["personas"]]
        if a.personas:
            quiero = a.personas.split(",")
            personas = [p for p in personas if p in quiero]
        print(f"{len(personas)} personas · {a.hilos} procesos · salida {salida}")
        with ProcessPoolExecutor(max_workers=a.hilos, initializer=poner_puerto, initargs=(PUERTO,)) as ex:
            futs = {ex.submit(barrer_persona, p, a.vuelta, str(salida), ids): p for p in personas}
            for fu in as_completed(futs):
                try:
                    pid, n, disco = fu.result()
                    print(f"  ✓ {pid}: {n} estados · libre {libre() / 1e9:.2f} GB" + (" · ⚠ PARADO POR DISCO" if disco else ""), flush=True)
                except Exception as e:
                    print(f"  ✗ {futs[fu]}: {e}", flush=True)
    finally:
        try:
            os.killpg(srv.pid, signal.SIGTERM)
        except Exception:
            srv.terminate()
        srv.wait(timeout=10)
    dur = int(time.time() - t0)
    res = informe(a.vuelta, salida, ficheros, inicio_txt, dur)
    print(f"\nFallos: {res['fallos_total']} · estados: {res['estados_capturados']} · {dur // 60} min · libre {libre() / 1e9:.2f} GB")
    for t, n in list(res["por_tipo"].items())[:12]:
        print(f"  {n:>6}  {t}")


if __name__ == "__main__":
    main()
