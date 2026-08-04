# Imagen del frontend Next.js.
FROM node:22-slim AS deps

WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund


FROM node:22-slim AS builder

WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# `NEXT_PUBLIC_*` se incrusta en el bundle, así que sólo puede fijarse en build
# time. Por eso **no lleva valor por defecto**: si lo llevara, una imagen
# construida sin pasar el argumento saldría compilada para hablar con el
# `localhost` de quien abre el navegador, y nunca usaría el proxy interno.
# Vacío significa «sin configurar», y entonces el cliente usa rutas relativas.
ARG NEXT_PUBLIC_API_URL=
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build


FROM node:22-slim AS runner

WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Sólo las dependencias de producción llegan a la imagen final.
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund && npm cache clean --force

COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/next.config.mjs ./next.config.mjs

RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=5 \
    CMD curl -fsS http://localhost:3000/ || exit 1

CMD ["npm", "run", "start"]
