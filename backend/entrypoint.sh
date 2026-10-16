#!/bin/sh
set -e

# 仅 Web 服务负责迁移和收集静态文件，Celery 等进程直接启动
if [ "$1" = "gunicorn" ]; then
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
fi

exec "$@"
