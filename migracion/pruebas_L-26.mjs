#!/usr/bin/env node
// migracion/pruebas_L-26.mjs · L-26: saneado del panel de dirección con lista blanca (parte de navegador).
// Uso: node migracion/pruebas_L-26.mjs --base http://127.0.0.1:8771
// Importa `parsear` del módulo en el navegador y le pasa HTML hostil. Solo lectura; sin datos reales.
import { chromium } from '../v2/tools/capturas/node_modules/playwright/index.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, v) => (x.startsWith('--') ? [...a, [x.slice(2), v[i + 1]?.startsWith('--') || v[i + 1] === undefined ? true : v[i + 1]]] : a), []));
const base = String(args.base || 'http://127.0.0.1:8771').replace(/\/$/, '');
const fallos = [];
let n = 0;
const ok = (c, t) => { n++; if (!c) fallos.push(t); };

const navegador = await chromium.launch();
try {
  const pagina = await (await navegador.newContext()).newPage();
  await pagina.goto(`${base}/`, { waitUntil: 'load', timeout: 45_000 });
  const r = await pagina.evaluate(async () => {
    const { parsear } = await import('/modulos/panel_direccion.js');
    const sal = (html) => { const d = document.createElement('div'); d.append(parsear(html)); return d.innerHTML; };
    return {
      hostil: sal('<div onclick="x()" style="a"><a href="javascript:alert(1)">x</a><b>ok</b><svg onload="y()"><script>z()</script><foreignObject><div>f</div></foreignObject></svg></div>'),
      desconocida: sal('<marquee><b>dentro</b></marquee><details><summary>s</summary><i>t</i></details>'),
      enlaces: sal('<a href="https://a.es/x">1</a><a href="mailto:a@b.c">2</a><a href="#z">3</a><a href="/r">4</a><a href="data:text/html,x">5</a><a href=" JaVaScRiPt:1">6</a><a href="rel/x">7</a>'),
      img: sal('<img src="javascript:1" onerror="y()"><img src="https://a.es/i.png">'),
      grafico: sal('<svg><path d="M0 0" stroke="red"/><circle cx="1"/><rect x="1"/><line/><text>t</text></svg>'),
    };
  });
  ok(!/onclick|onload|onerror|javascript:/i.test(r.hostil + r.img), 'quedan atributos on… o javascript:');
  ok(/<b>ok<\/b>/.test(r.hostil), 'se pierde <b>ok</b>');
  ok(!/<script|foreignobject/i.test(r.hostil), 'quedan script o foreignObject');
  ok(!/marquee/i.test(r.desconocida) && /<b>dentro<\/b>/.test(r.desconocida), 'la etiqueta desconocida debe quedar sin etiqueta y con su contenido');
  ok(/<details>.*<summary>s<\/summary>.*<\/details>/.test(r.desconocida), 'details/summary del panel deben seguir');
  const hrefs = [...r.enlaces.matchAll(/href="([^"]*)"/g)].map((m) => m[1]);
  ok(hrefs.length === 4 && hrefs.every((h) => /^(https:|mailto:|#|\/)/.test(h)), `enlaces: quedan ${hrefs.length} (deben ser 4 permitidos)`);
  ok(/src="https:\/\/a\.es\/i\.png"/.test(r.img) && !/src="javascript/.test(r.img), 'img: src https debe quedar, javascript no');
  ok(['<path', '<circle', '<rect', '<line', '<text'].every((t) => r.grafico.includes(t)), 'los gráficos SVG del panel deben seguir');
} finally { await navegador.close(); }
console.log(`${fallos.length ? '✘' : '✔'} L-26 (navegador): ${n} comprobaciones${fallos.length ? ' · ' + fallos.join(' · ') : ''}`);
process.exit(fallos.length ? 1 : 0);
