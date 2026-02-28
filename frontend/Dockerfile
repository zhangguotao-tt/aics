# ── 阶段一：Node.js 构建 ────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# 复制 package 文件并安装依赖
COPY package*.json ./
RUN npm install --silent

# 复制源代码并构建
COPY . .
RUN npm run build


# ── 阶段二：Nginx 生产镜像 ──────────────────────────────────
FROM nginx:1.25-alpine AS runtime

LABEL maintainer="DJsummer"
LABEL description="LLM 智能客服系统 - 前端服务"
LABEL version="1.0.0"

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制自定义 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1/health.html || exit 1

CMD ["nginx", "-g", "daemon off;"]
