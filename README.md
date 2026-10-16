# YGU OJ · 阳光学院在线评测平台

面向程序设计教学的在线评测平台。设计见 [系统设计说明书](./面向程序设计教学的在线评测平台%20·%20系统设计说明书.md)。

## 目录

```
backend/    Django 5.2 + DRF 后端（config 为项目配置，其余为业务应用）
frontend/   Vue 3 + Vite + Element Plus 前端
deploy/     docker-compose.yml、Nginx 配置、部署环境变量
data/       测试数据、日志、备份（不入库）
```

后端应用与设计说明书模块的对应：account(M1)、announcement(M2)、problem(M3/M12)、submission(M4)、
judge(M5)、options(M6)、contest(M7)、classroom(M9/M10)、stats(M11)。
成绩统计应用命名为 `stats` 而非 `statistics`，以免遮蔽 Python 标准库的同名模块。

## 本地开发

依赖：Python 3.11+、Node 22、MySQL 8.4、Redis。

```bash
# 后端
cd backend
python3 -m venv .venv && . .venv/bin/activate   # 本服务器可直接用 /opt/oj/venv
pip install -r requirements.txt
cp .env.example .env                             # 填写密钥与数据库密码
python manage.py migrate
python manage.py createsuperuser                 # 超级用户角色为管理员
python manage.py runserver                       # http://127.0.0.1:8000

# Celery 判题进程（另开终端）
celery -A config worker -l info

# 前端（另开终端），/api 会转发到 8000 端口
cd frontend
npm install
npm run dev                                      # http://localhost:5173，/dev/ui 预览设计令牌与组件
```

## 接口约定

- 统一前缀 `/api/`，管理接口 `/api/admin/`；路径不带结尾斜杠，例如 `/api/auth/login`。
- 响应格式 `{"code": 0, "message": "ok", "data": ...}`，`code` 非 0 表示出错。
  视图直接返回业务数据，外层由 `utils.renderers.UnifiedJSONRenderer` 包装；
  业务错误抛出 `utils.exceptions.BusinessError(message, code=...)`。
- 分页参数 `page`、`page_size`，返回 `{"total": ..., "results": [...]}`。
- 角色权限类见 `utils/permissions.py`。

## 部署

```bash
cd deploy
./init-env.sh                 # 生成 .env 与随机密钥，按需修改 DJANGO_ALLOWED_HOSTS
docker compose up -d --build
docker compose exec backend python manage.py createsuperuser
```

上传后未被题目使用的测试数据需定期清理，可在服务器 crontab 中加入：

```
0 4 * * * cd /path/to/oj/deploy && docker compose exec -T backend python manage.py cleanup_test_cases
```
