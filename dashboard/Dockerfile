# ─────────────────────────────────────────────────────────────────────────────
# AlgoBounty Dashboard — Multi-stage Next.js Docker build
# Stage 1: deps      — install node_modules
# Stage 2: builder   — next build (standalone output)
# Stage 3: runner    — minimal production image
# ─────────────────────────────────────────────────────────────────────────────

ARG NODE_VERSION=22
ARG ALPINE_VERSION=3.21

# ── Stage 1: Install dependencies ─────────────────────────────────────────────
FROM node:${NODE_VERSION}-alpine${ALPINE_VERSION} AS deps

WORKDIR /app

# Install libc compat for native modules on alpine
RUN apk add --no-cache libc6-compat

COPY package.json package-lock.json* ./

# Use ci for reproducible installs
RUN npm ci --prefer-offline

# ── Stage 2: Build ────────────────────────────────────────────────────────────
FROM node:${NODE_VERSION}-alpine${ALPINE_VERSION} AS builder

WORKDIR /app

# Build-time env vars (injected via Cloud Build substitutions or docker --build-arg)
ARG NEXT_PUBLIC_API_URL=""
ARG NEXT_PUBLIC_ALGORAND_NETWORK="testnet"

ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_ALGORAND_NETWORK=${NEXT_PUBLIC_ALGORAND_NETWORK}
# Disable Next.js telemetry during build
ENV NEXT_TELEMETRY_DISABLED=1

# Copy deps from previous stage
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Produce a standalone Next.js build (minimal output)
RUN npm run build

# ── Stage 3: Runner ───────────────────────────────────────────────────────────
FROM node:${NODE_VERSION}-alpine${ALPINE_VERSION} AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
# Cloud Run sets PORT; Next.js standalone server respects this
ENV PORT=8080
ENV HOSTNAME="0.0.0.0"

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy only what's needed for production
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 8080

CMD ["node", "server.js"]
