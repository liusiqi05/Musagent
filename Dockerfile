# MusAgent Dockerfile — v3.0
# 多阶段构建：前端构建产物由 Nginx 提供，后端用 uvicorn 独立运行
# 最终镜像：node:20-alpine (前端) + python:3.11-slim (后端) + 共享数据卷

# ══════════════════════════════════════════════════════════════════════════════
# Stage 1: 前端构建
# ══════════════════════════════════════════════════════════════════════════════
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
COPY musagent/package*.json ./
RUN npm ci --no-audit --no-fund
COPY musagent/ ./
# Vite 构建（默认 base=/，如果部署到子路径请传 VITE_BASE 环境变量）
RUN npm run build

# ══════════════════════════════════════════════════════════════════════════════
# Stage 2: 后端运行（带静态资源 + 评测数据）
# ══════════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim AS backend

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python 依赖（先拷贝以利用缓存）
COPY back/requirements.txt /app/back/requirements.txt
RUN pip install --no-cache-dir -r /app/back/requirements.txt

# 后端代码
COPY back/ /app/back/

# 前端构建产物放到后端可服务的 static 目录
COPY --from=frontend-builder /app/frontend/dist /app/back/static

# 知识库（前端会兜底检索，但放这里减少前端加载）
COPY musagent/src/data/poems_extracted.json /app/back/data/poems_extracted.json

# Poetry 知识库（如果 poems_extracted.json 在前端被找到则不需要）
RUN mkdir -p /app/back/data /app/back/.cache

# 非 root 用户运行
RUN useradd --create-home --shell /bin/bash musagent
RUN chown -R musagent:musagent /app
USER musagent

WORKDIR /app/back

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

EXPOSE 8000

# 启动命令（生产模式，无 --reload）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
