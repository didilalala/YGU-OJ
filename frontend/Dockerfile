# 构建前端静态文件，再交给 Nginx 托管；Nginx 配置由 deploy/nginx/default.conf 挂载
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-fund --no-audit
COPY . .
RUN npm run build

FROM nginx:1.30-alpine
COPY --from=build /app/dist /usr/share/nginx/html
