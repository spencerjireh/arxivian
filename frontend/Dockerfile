# Base stage - dependencies
FROM node:22-alpine AS base

WORKDIR /app

# Copy dependency files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Expose port
EXPOSE 5173

# Development stage
FROM base AS development

# Copy source code (will be overridden by volume mount in dev)
COPY . .

# Start Vite dev server with hot reload
CMD ["npm", "run", "dev"]

# Builder stage for production
FROM base AS builder

# Copy source code
COPY . .

# Build application
RUN npm run build

# Production stage
FROM nginx:alpine AS production

# Copy custom nginx config for SPA routing and API proxy
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 5173

CMD ["nginx", "-g", "daemon off;"]
