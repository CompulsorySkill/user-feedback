#!/bin/sh
# 启动时把部署前缀 BASE_PATH 注入 index.html：静态资源 URL 与前端路由 base 都跟着走，
# 因此镜像与前缀无关（根部署留空 BASE_PATH）。
set -eu

BASE="${BASE_PATH:-}"
BASE="${BASE%/}"

if [ -n "$BASE" ] && ! printf '%s' "$BASE" | grep -Eq '^(/[A-Za-z0-9._~-]+)*$'; then
  echo "BASE_PATH 非法: '${BASE_PATH}'（应为空或 /segment[/segment]）" >&2
  exit 1
fi

if [ ! -f /srv/index.template.html ]; then
  echo "缺少 /srv/index.template.html，镜像构建不完整" >&2
  exit 1
fi

if [ -z "$BASE" ]; then
  sed 's|__BASE__||g' /srv/index.template.html > /srv/index.html
else
  sed -e "s|__BASE__|$BASE|g" -e "s|=\"/|=\"$BASE/|g" /srv/index.template.html > /srv/index.html
fi

exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
