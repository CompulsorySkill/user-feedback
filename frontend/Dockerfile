# syntax=docker/dockerfile:1.7

FROM node:24-alpine AS build

WORKDIR /app
RUN npm install --global pnpm@11.28.5

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

FROM caddy:2.11.7-alpine

COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv

# 构建期即校验 Caddyfile，避免部署后才发现语法错误。
RUN caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile

EXPOSE 80 443 443/udp
