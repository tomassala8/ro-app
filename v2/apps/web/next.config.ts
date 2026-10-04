import type { NextConfig } from "next";

const API = process.env.RO_API_URL ?? "http://127.0.0.1:4000";

const nextConfig: NextConfig = {
  // El navegador solo habla con Next. /api, /vivo y /logos pasan a Nest con la MISMA ruta que en servir.py,
  // así el front viejo (puente) y las baterías de prueba en Python funcionan sin cambiar ni una URL.
  async rewrites() {
    return [
      { source: "/api/:ruta*", destination: `${API}/api/:ruta*` },
      { source: "/logos/:ruta*", destination: `${API}/logos/:ruta*` },
      { source: "/vivo", destination: `${API}/vivo` },
    ];
  },
  output: "standalone",
};

export default nextConfig;
