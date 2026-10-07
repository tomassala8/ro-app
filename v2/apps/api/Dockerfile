# Imagen de la API (Nest). Contexto: la raíz del repo.  docker build -f v2/apps/api/Dockerfile .
FROM node:22-slim AS base
ENV PNPM_HOME=/pnpm PATH=/pnpm:$PATH
RUN corepack enable
WORKDIR /repo

FROM base AS build
COPY v2/ v2/
COPY reglas_permisos.json ./
WORKDIR /repo/v2
RUN pnpm install --frozen-lockfile
RUN pnpm --filter @ro/api... build && pnpm deploy --filter @ro/api --prod --legacy /out

FROM base AS final
ENV NODE_ENV=production TZ=Europe/Madrid
WORKDIR /app
COPY --from=build /out ./
COPY --from=build /repo/v2/apps/api/dist ./dist
COPY --from=build /repo/reglas_permisos.json /reglas_permisos.json
# Las migraciones se aplican aparte, antes de arrancar: pnpm --filter @ro/db migrate:deploy
# Nunca como root: si alguien consiguiera ejecutar algo dentro, no sería dueño del contenedor.
USER node
EXPOSE 4000
HEALTHCHECK --interval=60s --timeout=5s CMD node -e "fetch('http://127.0.0.1:'+(process.env.PORT||4000)+'/vivo').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node", "dist/main.js"]
