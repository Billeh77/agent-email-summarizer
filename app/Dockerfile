# Stage 1: Install dependencies
FROM node:24-alpine AS deps
RUN corepack enable && corepack prepare pnpm@10.19.0 --activate
WORKDIR /app

# Copy package files for dependency installation
COPY app/package.json app/pnpm-lock.yaml* ./
COPY .env.* ./
COPY app/.npmrc ./

# Install dependencies (mount GitHub token as secret for private packages)
RUN --mount=type=secret,id=github_token \
    GITHUB_TOKEN=$(cat /run/secrets/github_token 2>/dev/null || echo "") \
    pnpm install --frozen-lockfile

# Stage 2: Build the application
FROM node:24-alpine AS builder
RUN corepack enable && corepack prepare pnpm@10.19.0 --activate
WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy source code
COPY app/ .

RUN pnpm run build

# Verify the build output exists
RUN ls -la /app/.output/server/ && test -f /app/.output/server/index.mjs

# Stage 3: Production runtime
FROM node:24-alpine AS runner
WORKDIR /app

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 appuser

# Copy built output from builder
COPY --from=builder --chown=appuser:nodejs /app/.output ./.output
COPY --from=builder --chown=appuser:nodejs /app/.env.* ./

# Set runtime environment variables
ENV NODE_ENV=production
ENV PORT=3001
ENV HOST=0.0.0.0

# Switch to non-root user
USER appuser

# Expose the port
EXPOSE 3001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD wget -q --spider http://localhost:3001/ || exit 1

# Start the server
CMD ["node", ".output/server/index.mjs"]
