# Imagen de la web (Next, salida «standalone»). Contexto: la raíz del repo.  docker build -f v2/apps/web/Dockerfile .
FROM node:22-slim AS base
ENV PNPM_HOME=/pnpm PATH=/pnpm:$PATH NEXT_TELEMETRY_DISABLED=1
RUN corepack enable
WORKDIR /repo

FROM base AS build
COPY v2/ v2/
# El puente necesita el front de hoy (scripts/sync-legacy.mjs lo copia a public/legacy en el prebuild)
COPY estilos.css componentes.js datos.js permisos.js ayudas.js carcasa.js app.js sw.js reglas_permisos.json ./
COPY modulos/ modulos/
COPY fuentes_web/ fuentes_web/
WORKDIR /repo/v2
RUN pnpm install --frozen-lockfile && pnpm --filter @ro/web build

FROM base AS final
ENV NODE_ENV=production TZ=Europe/Madrid
WORKDIR /app
COPY --from=build /repo/v2/apps/web/.next/standalone ./
COPY --from=build /repo/v2/apps/web/.next/static ./apps/web/.next/static
COPY --from=build /repo/v2/apps/web/public ./apps/web/public
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
