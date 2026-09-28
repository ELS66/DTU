#!/usr/bin/env bash
set -Eeuo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
bash "$repo_dir/deploy/baota-build.sh"

if [[ "${DTU_PM2_RELOAD:-0}" != "1" ]]; then
  echo "构建完成；PM2 自动重启尚未启用。首次启动及检查方式见 docs/baota-deployment.md。"
  exit 0
fi

pm2_bin="${PM2_BIN:-$(command -v pm2 || true)}"
if [[ -z "$pm2_bin" || ! -x "$pm2_bin" ]]; then
  echo "发布中止：找不到 PM2，请设置 PM2_BIN 为可执行文件路径" >&2
  exit 1
fi

export PATH="$(dirname -- "${NODE_BIN:-$(command -v node)}"):$PATH"
if ! "$pm2_bin" describe dtu-api >/dev/null 2>&1; then
  echo "发布中止：当前用户的 PM2 中没有 dtu-api；先按文档手动启动一次" >&2
  exit 1
fi

"$pm2_bin" reload "$repo_dir/deploy/ecosystem.config.cjs" --update-env

health_url="http://127.0.0.1:${PORT:-7926}/health"
for attempt in {1..10}; do
  if curl --fail --silent --show-error "$health_url" >/dev/null 2>&1; then
    echo "PM2 已重载，健康检查通过：$health_url"
    exit 0
  fi
  sleep 1
done

echo "发布失败：PM2 重载后健康检查未通过：$health_url" >&2
exit 1
