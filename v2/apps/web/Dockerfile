# Imagen de la web (Next, salida «standalone»). Contexto: la raíz del repo.  docker build -f v2/apps/web/Dockerfile .
FROM node:22-slim AS base
ENV PNPM_HOME=/pnpm PATH=/pnpm:$PATH NEXT_TELEMETRY_DISABLED=1
RUN npm install -g pnpm@10.28.0
WORKDIR /repo

FROM base AS build
COPY v2/ v2/
# El puente necesita el front de hoy (scripts/sync-legacy.mjs lo copia a public/legacy en el prebuild)
COPY estilos.css componentes.js datos.js permisos.js ayudas.js carcasa.js app.js sw.js reglas_permisos.json ./
COPY modulos/ modulos/
COPY fuentes_web/ fuentes_web/
WORKDIR /repo/v2
# next.config.ts lee RO_API_URL al construir (los rewrites quedan fijados en la imagen): sin esto apuntarían a 127.0.0.1
ARG RO_API_URL=http://127.0.0.1:4000
ENV RO_API_URL=$RO_API_URL
RUN pnpm install --frozen-lockfile && pnpm --filter @ro/web build

FROM base AS final
ENV NODE_ENV=production TZ=Europe/Madrid
WORKDIR /app
COPY --from=build /repo/v2/apps/web/.next/standalone ./
COPY --from=build /repo/v2/apps/web/.next/static ./apps/web/.next/static
COPY --from=build /repo/v2/apps/web/public ./apps/web/public
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
