import type { NextConfig } from "next";

const API = process.env.RO_API_URL ?? "http://127.0.0.1:4000";

const nextConfig: NextConfig = {
  // El navegador solo habla con Next. /api, /vivo y /logos pasan a Nest con la MISMA ruta que en servir.py,
  // así el front viejo (puente) y las baterías de prueba en Python funcionan sin cambiar ni una URL.
  async rewrites() {
    return {
      beforeFiles: [
        { source: "/api/:ruta*", destination: `${API}/api/:ruta*` },
        { source: "/logos/:ruta*", destination: `${API}/logos/:ruta*` },
        { source: "/vivo", destination: `${API}/vivo` },
      ],
      afterFiles: [],
      // Estrangulador del front: lo que Next aún no tiene como página propia (empezando por «/», el index.html de hoy
      // con su mapa de versiones, CSP y precarga; app.js, modulos/…) pasa a Nest, que lo pasa a servir.py. Así la app
      // nueva enseña EXACTAMENTE el front de hoy desde el minuto 0, y cada pieza en React lo sustituye solo al pasar
      // sus fotos.
      fallback: [{ source: "/:ruta*", destination: `${API}/:ruta*` }],
    };
  },
  output: "standalone",
};

export default nextConfig;
