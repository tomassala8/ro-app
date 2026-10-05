// sw.js · La navegación consulta primero la página actual y su mapa de versiones.
// La última página buena solo sirve de respaldo si falla la red; no almacena API, datos ni proveedores.
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
    try { return await red; }
    catch (error) { if (guardada) return guardada; throw error; }
  })());
});
