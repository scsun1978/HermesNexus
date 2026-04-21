# HermesNexus Multi-Stage Production Dockerfile
# 优化的生产环境Docker镜像

# ===================================
# Stage 1: Builder - 构建阶段
# ===================================
FROM python:3.12-slim AS builder

# 设置构建参数
ARG BUILD_DATE
ARG VERSION=1.2.0
ARG VCS_REF

# 设置工作目录
WORKDIR /build

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libc-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt requirements-dev.txt ./

# 安装Python依赖到临时目录
RUN pip install --user --no-cache-dir -r requirements.txt \
    && pip install --user --no-cache-dir -r requirements-dev.txt

# ===================================
# Stage 2: Runtime - 运行时阶段
# ===================================
FROM python:3.12-slim AS runtime

# 获取架构信息
ARG TARGETARCH

# 设置标签信息
LABEL maintainer="HermesNexus Team" \
      org.opencontainers.image.title="HermesNexus Cloud API" \
      org.opencontainers.image.description="分布式边缘设备管理系统 - 云端控制平面" \
      org.opencontainers.image.version="1.2.0" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.vendor="HermesNexus"

# 创建非root用户
RUN groupadd -r hermes && useradd -r -g hermes hermes

# 安装运行时依赖（最小化）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 设置工作目录
WORKDIR /app

# 从构建阶段复制Python包
COPY --from=builder /root/.local /root/.local

# 确保Python能找到已安装的包
ENV PATH=/root/.local/bin:$PATH \
    PYTHONPATH=/root/.local/lib/python3.12/site-packages \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HERMES_HOME=/app \
    HERMES_VERSION=1.2.0

# 复制应用代码
COPY cloud/ ./cloud/
COPY shared/ ./shared/
COPY console/ ./console/

# 创建数据目录并设置权限
RUN mkdir -p /app/data /app/logs /app/temp \
    && chown -R hermes:hermes /app

# 切换到非root用户
USER hermes

# 健康检查（增强版）
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# 暴露端口
EXPOSE 8080

# 启动命令（生产优化）
CMD ["python3", "-m", "uvicorn", "cloud.api.main:app", \
    "--host", "0.0.0.0", \
    "--port", "8080", \
    "--workers", "4", \
    "--worker-class", "uvicorn.workers.UvicornWorker", \
    "--access-log", \
    "--log-level", "info"]