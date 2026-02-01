# =============================================================================
# Stage 1: Build
# =============================================================================
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY nurse-dashboard/package*.json ./nurse-dashboard/
COPY security-dashboard/package*.json ./security-dashboard/
COPY admin-dashboard/package*.json ./admin-dashboard/
COPY shared-components/package*.json ./shared-components/

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build all dashboards
RUN npm run build

# =============================================================================
# Stage 2: Production with nginx
# =============================================================================
FROM nginx:alpine AS production

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built assets
COPY --from=builder /app/nurse-dashboard/dist /usr/share/nginx/html/nurse
COPY --from=builder /app/security-dashboard/dist /usr/share/nginx/html/security
COPY --from=builder /app/admin-dashboard/dist /usr/share/nginx/html/admin

# Add security headers
RUN echo 'add_header X-Frame-Options "DENY" always;' >> /etc/nginx/conf.d/security.conf && \
    echo 'add_header X-Content-Type-Options "nosniff" always;' >> /etc/nginx/conf.d/security.conf && \
    echo 'add_header X-XSS-Protection "1; mode=block" always;' >> /etc/nginx/conf.d/security.conf

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:80/health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
