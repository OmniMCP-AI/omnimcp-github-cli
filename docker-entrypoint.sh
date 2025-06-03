#!/bin/sh
set -e

# 启动 Docker 守护进程
echo "Starting Docker daemon..."
dockerd-entrypoint.sh &

# 等待 Docker 守护进程启动
echo "Waiting for Docker daemon to start..."
while ! docker info >/dev/null 2>&1; do
  sleep 1
done
echo "Docker daemon started"

# 执行传入的命令
echo "Starting application..."
exec "$@" 