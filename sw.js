// sw.js · ronda 14 (velocidad, auditoría 37). Solo guarda la PÁGINA (index.html, sin datos): la enseña al momento y la
// refresca detrás, para que la sesión salga en el primer viaje y no después de preguntar «¿ha cambiado la página?».
// No toca /api/ (los datos van por persona en datos.js), ni el código (va con su huella y caché de un año), ni nada de fuera.
// Si la página guardada es de otra versión, sus ficheros siguen sirviéndose bien (cada uno con su huella) y la siguiente
// entrada ya usa la nueva. La carcasa borra esta caché al entrar otra persona (datos.js · olvidarTodo).
const CACHE = 'ro-pagina-v1';

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil((async () => {
  for (const k of await caches.keys()) if (k !== CACHE) await caches.delete(k);
  await self.clients.claim();
})()));

self.addEventListener('fetch', e => {
  const r = e.request;
  if (r.method !== 'GET' || r.mode !== 'navigate') return;
  const u = new URL(r.url);
  if (u.origin !== self.location.origin || (u.pathname !== '/' && u.pathname !== '/index.html')) return;
  e.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const red = fetch(r).then(async resp => {
      // Solo una página buena de la propia app (nada de redirecciones de Access ni errores).
      if (resp.ok && resp.status === 200 && resp.type === 'basic') await cache.put(r, resp.clone());
      return resp;
    });
    const guardada = await cache.match(r);
    if (guardada) { e.waitUntil(red.catch(() => {})); return guardada; }
    return red;
  })());
});
