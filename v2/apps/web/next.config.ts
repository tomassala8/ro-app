import path from "node:path";
import type { NextConfig } from "next";

const API = process.env.RO_API_URL ?? "http://127.0.0.1:4000";
// F6.2: con RO_CARCASA=1 (en el `next build`), «/» enseña la carcasa en React sin cambiar la dirección: las fotos,
// /api/elegir y los fetch relativos del front de hoy siguen funcionando igual. F6.3 la deja encendida por defecto.
const CARCASA = process.env.RO_CARCASA === "1";

const nextConfig: NextConfig = {
  // El navegador solo habla con Next. /api, /vivo y /logos pasan a Nest con la MISMA ruta que en servir.py,
  // así el front viejo (puente) y las baterías de prueba en Python funcionan sin cambiar ni una URL.
  async rewrites() {
    return {
      beforeFiles: [
        { source: "/api/:ruta*", destination: `${API}/api/:ruta*` },
        { source: "/logos/:ruta*", destination: `${API}/logos/:ruta*` },
        { source: "/vivo", destination: `${API}/vivo` },
        ...(CARCASA ? [{ source: "/", destination: "/carcasa" }] : []),
      ],
      afterFiles: [],
      // Estrangulador del front: lo que Next aún no tiene como página propia (empezando por «/», el index.html de hoy
      // con su mapa de versiones, CSP y precarga; app.js, modulos/…) pasa a Nest, que lo pasa a servir.py. Así la app
      // nueva enseña EXACTAMENTE el front de hoy desde el minuto 0, y cada pieza en React lo sustituye solo al pasar
      // sus fotos.
      fallback: [{ source: "/:ruta*", destination: `${API}/:ruta*` }],
    };
  },
  // El proxy de los rewrites corta a los 30 s por defecto; la API espera al legado 60 s (RO_LEGADO_ESPERA_MS).
  // Con 65 s, el 504 con mensaje de la API llega antes que el corte seco de Next.
  experimental: { proxyTimeout: 65_000 },
  output: "standalone",
  // Monorepo pnpm: el trazado de ficheros del standalone parte de la raíz de v2 (donde están node_modules/.pnpm y
  // los paquetes del espacio de trabajo). Así server.js queda en .next/standalone/apps/web, como espera el Dockerfile.
  outputFileTracingRoot: path.join(__dirname, "../.."),
};

export default nextConfig;
