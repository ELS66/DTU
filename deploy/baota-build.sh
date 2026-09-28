#!/usr/bin/env bash
set -Eeuo pipefail

# 宝塔 Git 管理在拉取 main 后调用此脚本。当前阶段只构建，不启动服务。
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$repo_dir"

if [[ "$(git branch --show-current)" != "main" ]]; then
  echo "构建中止：当前分支不是 main" >&2
  exit 1
fi

node_bin="${NODE_BIN:-$(command -v node || true)}"
npm_bin="${NPM_BIN:-$(command -v npm || true)}"
if [[ -z "$node_bin" || -z "$npm_bin" || ! -x "$node_bin" || ! -x "$npm_bin" ]]; then
  echo "构建中止：请在宝塔安装 Node.js 22+ 和 npm，并设置 NODE_BIN/NPM_BIN 或 PATH" >&2
  exit 1
fi
export PATH="$(dirname -- "$node_bin"):$PATH"
node_major="$("$node_bin" -p 'Number(process.versions.node.split(".")[0])')"
if (( node_major < 22 || node_major >= 27 )); then
  echo "构建中止：此项目要求 Node.js 22～26，生产环境建议使用 Node.js 24 LTS" >&2
  exit 1
fi
echo "构建提交：$(git rev-parse --short HEAD)"
cd "$repo_dir/backend"
"$npm_bin" ci --no-audit --no-fund
"$npm_bin" test

entry_file="$repo_dir/backend/dist/main.js"
if [[ ! -s "$entry_file" ]]; then
  echo "构建中止：未找到 Node.js 入口：$entry_file" >&2
  exit 1
fi

echo "后端构建成功：$entry_file"
echo "当前仅生成构建产物；数据库迁移、宝塔 Node 项目创建与服务重启须另行配置。"
