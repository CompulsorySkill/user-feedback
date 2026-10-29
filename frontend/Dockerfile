# syntax=docker/dockerfile:1.7

# 构建阶段固定用构建机架构：产物是静态文件，与目标架构无关。
# 否则 arm64 在 amd64 runner 上要通过 QEMU 跑 Node，会偶发
# "qemu: uncaught target signal 4 (Illegal instruction)" 直接崩掉。
FROM --platform=$BUILDPLATFORM node:24-alpine AS build

# 子路径部署时构建期传入，例如 VITE_BASE=/feedback/；默认根路径。
ARG VITE_BASE=/
ENV VITE_BASE=${VITE_BASE}

WORKDIR /app
RUN npm install --global pnpm@11.28.5

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

# 构建期即校验 Caddyfile，避免部署后才发现语法错误；同样在构建平台执行。
FROM --platform=$BUILDPLATFORM caddy:2.11.7-alpine AS validate

COPY Caddyfile /etc/caddy/Caddyfile
RUN caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile

# 目标平台阶段不执行任何 RUN，arm64 只承担拉取基础镜像，不跑 QEMU。
FROM caddy:2.11.7-alpine

COPY --from=validate /etc/caddy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv

EXPOSE 80 443 443/udp
