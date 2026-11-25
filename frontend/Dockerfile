# AI TradePilot frontend — multi-stage Node build, standalone output, non-root.
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1 NODE_OPTIONS=--max-old-space-size=2048
RUN npm run build

FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
RUN addgroup -S tradepilot && adduser -S tradepilot -G tradepilot
COPY --from=builder /app/public ./public
COPY --from=builder --chown=tradepilot:tradepilot /app/.next/standalone ./
COPY --from=builder --chown=tradepilot:tradepilot /app/.next/static ./.next/static
USER tradepilot
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:3000/ || exit 1
CMD ["node", "server.js"]
