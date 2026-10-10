# syntax=docker/dockerfile:1

# --- Build stage ---
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies first for better layer caching.
COPY package.json package-lock.json ./
RUN npm ci

# Copy source and build. Vite bakes VITE_* env vars in at build time.
ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_WS_URL=ws://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_WS_URL=$VITE_WS_URL
COPY . .
RUN npm run build

# --- Serve stage ---
FROM nginx:1.27-alpine AS serve

# SPA fallback: serve index.html for client-side routes.
COPY <<'EOF' /etc/nginx/conf.d/default.conf
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Long-cache hashed assets.
    location /assets/ {
        add_header Cache-Control "public, max-age=31536000, immutable";
    }
}
EOF

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
    CMD wget -qO- http://localhost:80/ >/dev/null 2>&1 || exit 1
