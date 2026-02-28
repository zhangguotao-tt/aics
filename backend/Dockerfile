# ── 阶段一：构建依赖 ──────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# 安装编译工具（部分 Python 包需要 gcc）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件，利用 Docker 层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── 阶段二：生产镜像 ─────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="DJsummer"
LABEL description="LLM 智能客服系统 - 后端服务"
LABEL version="1.0.0"

# 运行时系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户提升安全性
RUN useradd -m -u 1000 -s /bin/bash appuser

WORKDIR /app

# 从 builder 阶段复制已安装的包
COPY --from=builder /install /usr/local

# 复制应用代码
COPY --chown=appuser:appuser . .

# 创建必要目录
RUN mkdir -p logs data/chroma_db && chown -R appuser:appuser /app

# 切换非 root 用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--loop", "uvloop", \
     "--http", "httptools", \
     "--log-level", "info"]
