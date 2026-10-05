import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "App de RO",
  description: "App interna de Ranking Online",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="es">
      <head>
        <link rel="preload" href="/fuentes_web/montserrat-latin-wght-normal.woff2" as="font" type="font/woff2" crossOrigin="" />
        {/* El sistema de diseño de hoy, tal cual (copiado por scripts/sync-legacy.mjs). Manda sobre el aspecto. */}
        {/* eslint-disable-next-line @next/next/no-css-tags -- a propósito: el CSS de hoy, sin pasar por el empaquetador */}
        <link rel="stylesheet" href="/legacy/estilos.css" />
      </head>
      <body>{children}</body>
    </html>
  );
}
