# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
ARG VITE_GATEWAY_URL=http://localhost:8000
ENV VITE_GATEWAY_URL=$VITE_GATEWAY_URL
RUN npm run build

# Serve stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
