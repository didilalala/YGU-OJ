#!/bin/sh
# 首次部署前运行：由 .env.example 生成 .env，并填入随机密码和密钥。已存在的 .env 不会被覆盖。
set -e
cd "$(dirname "$0")"

if [ -f .env ]; then
    echo ".env 已存在，未做修改"
    exit 0
fi

secret() { openssl rand -hex "$1"; }

sed -e "s|^MYSQL_ROOT_PASSWORD=.*|MYSQL_ROOT_PASSWORD=$(secret 16)|" \
    -e "s|^MYSQL_PASSWORD=.*|MYSQL_PASSWORD=$(secret 16)|" \
    -e "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=$(secret 32)|" \
    -e "s|^JUDGE_SERVER_TOKEN=.*|JUDGE_SERVER_TOKEN=$(secret 16)|" \
    .env.example > .env
chmod 600 .env

mkdir -p ../data/test_case ../data/log ../data/backup ../data/upload \
         ../data/judge_server/log ../data/judge_server/run

echo "已生成 deploy/.env，请按需修改 DJANGO_ALLOWED_HOSTS 等配置"
